import random
import time

import cv2
import mediapipe as mp
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from insightface.app import FaceAnalysis

# ==================== 集中配置（阈值统一在此调整） ====================
CONFIG = {
    "det_size": (640, 640),
    "providers": ["CUDAExecutionProvider", "CPUExecutionProvider"],

    # —— 姿态（弧度）—— 均为相对「自然正脸基线」的变化量
    "yaw_turn_threshold": 0.35,       # 转头：|yaw 变化| >= 该值
    "pitch_turn_threshold": 0.30,     # 抬头/低头：|pitch 变化| >= 该值
    "pose_hold_frames": 5,            # 姿态需连续保持的帧数

    # —— 眨眼（EAR 眼睛纵横比）——
    # 睁眼基准 EAR 在基线阶段测得，闭眼/睁眼阈值按比例换算，避免个体差异导致失效
    "blink_close_ratio": 0.35,        # 闭眼阈值 = 睁眼基准 × 该比例
    "blink_open_ratio": 0.60,         # 睁眼阈值 = 睁眼基准 × 该比例
    "ear_close_default": 0.10,        # 基线不可用时的闭眼阈值兜底
    "ear_open_default": 0.15,         # 基线不可用时的睁眼阈值兜底
    "blink_closed_frames": 2,         # 闭眼需连续帧数（防抖）
    "blink_open_frames": 2,           # 睁眼需连续帧数（防抖，避免单帧噪声误判完成）

    # —— 基线 ——
    "baseline_frames": 10,            # 采集自然正脸的帧数

    # —— 每轮挑战 ——
    "actions_per_round": 3,
    "action_timeout": 8.0,            # 单个动作超时（秒）
    "face_lost_timeout": 1.5,         # 无有效人脸超过该秒数判本轮失败

    # 方向符号：相对变化的「正方向」。若实际感知方向相反，把 +1/-1 对调即可。
    "yaw_sign": {"turn_left": 1.0, "turn_right": -1.0},
    "pitch_sign": {"look_up": 1.0, "look_down": -1.0},

    # 中立位门控：pose 动作相应轴需先进入 |变化| < 该值的中立范围才判定
    "pose_neutral_thr": 0.10,
    # 眨眼闭眼超过该时长（秒）重置本次眨眼状态
    "blink_max_closed_sec": 0.5,
}

ACTIONS = ("blink", "turn_left", "turn_right", "look_up", "look_down")
ACTION_TEXT = {
    "blink": "请眨眼",
    "turn_left": "请向左转头",
    "turn_right": "请向右转头",
    "look_up": "请抬头",
    "look_down": "请低头",
}


# ==================== 中文文本绘制 ====================
_FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"
_FONT_CACHE = {}


def _font(size):
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = ImageFont.truetype(_FONT_PATH, size)
        except OSError:
            _FONT_CACHE[size] = ImageFont.load_default()
    return _FONT_CACHE[size]


def draw_text(frame, text, org, size=24, color=(255, 255, 255), stroke=1):
    """用 PIL 绘制中文（解决 OpenCV putText 中文乱码），org 为左上角坐标。"""
    rgb = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(rgb)
    draw.text(org, text, font=_font(size),
              fill=(color[2], color[1], color[0]),
              stroke_width=stroke, stroke_fill=(0, 0, 0))
    frame[:, :, :] = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2BGR)


# ==================== 特征提取 ====================
def measure_pose(face):
    """提取 InsightFace 姿态 [pitch, yaw, roll]；face.pose 原始单位为度，转为弧度返回。"""
    return np.deg2rad(np.asarray(face.pose, dtype=np.float32)) if face.pose is not None else None


def facemesh_ear(mesh_results, image_w, image_h):
    """从 MediaPipe FaceMesh 结果计算左右眼 EAR（像素坐标）。

    使用标准 6 点 EAR，索引为 FaceMesh 官方关键点：
      左眼 [33, 160, 158, 133, 153, 144]（外/内眼角 + 上下眼睑）
      右眼 [362, 385, 387, 263, 373, 380]
    FaceMesh 的 x/y 分别按图宽/图高归一化，需先转回像素坐标，
    否则 EAR 会随图像长宽比漂移。无有效人脸返回 (None, None)。
    """
    if mesh_results.multi_face_landmarks is None:
        return None, None
    lm = mesh_results.multi_face_landmarks[0].landmark

    def _ear(idx):
        q = np.asarray([[lm[i].x * image_w, lm[i].y * image_h] for i in idx],
                       dtype=np.float32)
        vertical = np.linalg.norm(q[1] - q[5]) + np.linalg.norm(q[2] - q[4])
        horizontal = np.linalg.norm(q[0] - q[3])
        return vertical / (2.0 * horizontal + 1e-6)

    return _ear([33, 160, 158, 133, 153, 144]), _ear([362, 385, 387, 263, 373, 380])


# ==================== 动作判定 ====================
def new_state():
    return {"hold": 0, "blink_phase": 0, "pose_armed": False, "closed_start": None}


def check_action(action, pose_rel, ear, st, close_thr, open_thr):
    """返回 True 表示该动作已连续满足要求（完成）。"""
    if action == "blink":
        if ear is None:
            st["hold"] = 0
            st["blink_phase"] = 0
            st["closed_start"] = None
            return False
        now = time.time()
        if st["blink_phase"] == 0:
            # 等待闭眼：min(左右 EAR) 低于闭眼阈值（迟滞下限），连续多帧确认
            if ear < close_thr:
                st["hold"] += 1
            else:
                st["hold"] = 0
            if st["hold"] >= CONFIG["blink_closed_frames"]:
                st["blink_phase"] = 1
                st["hold"] = 0
                st["closed_start"] = now
            return False
        # 等待睁眼：min(左右 EAR) 高于睁眼阈值（双眼均恢复睁开），连续多帧确认
        if ear > open_thr:
            st["hold"] += 1
        else:
            st["hold"] = 0
        # 闭眼超过上限时长（照片/持续闭眼）→ 重置本次眨眼
        if st["closed_start"] is not None and \
                now - st["closed_start"] > CONFIG["blink_max_closed_sec"]:
            st["blink_phase"] = 0
            st["hold"] = 0
            st["closed_start"] = None
            return False
        return st["hold"] >= CONFIG["blink_open_frames"]

    if action in ("turn_left", "turn_right"):
        axis = 1
        value = pose_rel[1] * CONFIG["yaw_sign"][action]
        threshold = CONFIG["yaw_turn_threshold"]
    else:  # look_up / look_down
        axis = 0
        value = pose_rel[0] * CONFIG["pitch_sign"][action]
        threshold = CONFIG["pitch_turn_threshold"]

    # 中立位门控：相应轴先进入中立范围，才允许开始计数判定
    if not st["pose_armed"]:
        if abs(pose_rel[axis]) < CONFIG["pose_neutral_thr"]:
            st["pose_armed"] = True
            st["hold"] = 0
        return False

    if value >= threshold:
        st["hold"] += 1
    else:
        st["hold"] = 0
    return st["hold"] >= CONFIG["pose_hold_frames"]


# ==================== 一轮挑战 ====================
def new_round():
    return {
        "phase": "baseline",
        "baseline": [],
        "baseline_pose": None,
        "blink_close_thr": CONFIG["ear_close_default"],
        "blink_open_thr": CONFIG["ear_open_default"],
        "actions": random.sample(ACTIONS, CONFIG["actions_per_round"]),
        "done": [],
        "current": None,
        "st": new_state(),
        "action_start": 0.0,
        "lost_since": None,
        "result": "",
    }


def step_round(r, faces, left_ear, right_ear):
    """推进一轮；返回 'ok' / 'success' / 'fail'。"""
    now = time.time()

    if r["phase"] == "baseline":
        if len(faces) == 1:
            pose = measure_pose(faces[0])
            if pose is not None and left_ear is not None and right_ear is not None:
                r["baseline"].append((pose, left_ear, right_ear))
        else:
            r["baseline"].clear()
        if len(r["baseline"]) >= CONFIG["baseline_frames"]:
            poses = np.stack([s[0] for s in r["baseline"]])
            left_ears = [s[1] for s in r["baseline"]]
            right_ears = [s[2] for s in r["baseline"]]
            r["baseline_pose"] = poses.mean(axis=0)
            # 左右眼睁眼 EAR 分别取稳健中位数，避免单帧异常拉偏基线；
            # 眨眼判定用 min(左右)，故睁眼基准取两眼较小者。
            left_open_ref = float(np.median(left_ears))
            right_open_ref = float(np.median(right_ears))
            open_ref = min(left_open_ref, right_open_ref)
            r["blink_close_thr"] = max(open_ref * CONFIG["blink_close_ratio"],
                                       CONFIG["ear_close_default"])
            r["blink_open_thr"] = max(open_ref * CONFIG["blink_open_ratio"],
                                       CONFIG["ear_open_default"])
            r["phase"] = "challenge"
            r["current"] = r["actions"][0]
            r["st"] = new_state()
            r["action_start"] = now
            r["lost_since"] = None
        return "ok"

    if r["phase"] in ("success", "fail"):
        return r["phase"]

    # challenge
    if len(faces) == 1:
        r["lost_since"] = None
        face = faces[0]
        pose = measure_pose(face)
        pose_rel = pose - r["baseline_pose"] if pose is not None else None

        action = r["current"]
        if action == "blink":
            # 闭眼/睁眼均以双眼 EAR 最小值判定，任一眼缺失则本帧不判定
            ear = (min(left_ear, right_ear)
                   if (left_ear is not None and right_ear is not None) else None)
            can_judge = ear is not None
        else:
            # pose 动作只依赖姿态，不再依赖 FaceMesh EAR
            ear = None
            can_judge = pose_rel is not None

        if can_judge:
            if check_action(action, pose_rel, ear, r["st"],
                            r["blink_close_thr"], r["blink_open_thr"]):
                r["done"].append(action)
                if len(r["done"]) >= len(r["actions"]):
                    r["phase"] = "success"
                    r["result"] = "挑战成功"
                    return "success"
                r["current"] = r["actions"][len(r["done"])]
                r["st"] = new_state()
                r["action_start"] = now

        if now - r["action_start"] > CONFIG["action_timeout"]:
            r["phase"] = "fail"
            r["result"] = "本轮失败：动作超时"
            return "fail"
    else:
        if r["lost_since"] is None:
            r["lost_since"] = now
        elif now - r["lost_since"] > CONFIG["face_lost_timeout"]:
            r["phase"] = "fail"
            r["result"] = "本轮失败：人脸丢失"
            return "fail"

    return "ok"


# ==================== 绘制 ====================
def draw_hud(frame, r, faces, left_ear, right_ear):
    h = frame.shape[0]

    if len(faces) == 1:
        x1, y1, x2, y2 = map(int, faces[0].bbox)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    if r["phase"] == "baseline":
        text = f"请正对摄像头，保持自然正脸 {len(r['baseline'])}/{CONFIG['baseline_frames']}"
        color = (0, 255, 255)
    elif r["phase"] == "challenge":
        total = len(r["actions"])
        done = len(r["done"])
        text = f"[{done}/{total}] {ACTION_TEXT[r['current']]}"
        color = (0, 255, 255)
    else:
        text = r["result"] + "  （按 R 重新开始 / Q 退出）"
        color = (0, 255, 0) if r["phase"] == "success" else (0, 0, 255)

    draw_text(frame, text, (20, 20), size=28, color=color)

    # 实时指标
    if r["phase"] == "challenge" and len(faces) == 1:
        pose = measure_pose(faces[0])
        if pose is not None:
            pr = pose - r["baseline_pose"]
            draw_text(frame, f"yaw {pr[1]:+.2f}  pitch {pr[0]:+.2f}",
                      (20, 58), size=20, color=(255, 255, 255))
        if left_ear is not None and right_ear is not None:
            ear_min = min(left_ear, right_ear)
            draw_text(frame, f"左眼EAR {left_ear:.2f}  右眼EAR {right_ear:.2f}",
                      (20, 84), size=20, color=(255, 255, 255))
            if r["current"] == "blink":
                if ear_min < r["blink_close_thr"]:
                    eye_state = "闭眼"
                elif ear_min > r["blink_open_thr"]:
                    eye_state = "睁眼"
                else:
                    eye_state = "中间态"
                phase = r["st"]["blink_phase"]
                if phase == 0:
                    status = f"状态:{eye_state} 待闭眼 [{r['st']['hold']}/{CONFIG['blink_closed_frames']}]"
                else:
                    status = f"状态:{eye_state} 待睁眼 [{r['st']['hold']}/{CONFIG['blink_open_frames']}]"
                draw_text(frame, status, (20, 110), size=20, color=(0, 255, 255))
                draw_text(frame, f"阈值 闭眼{r['blink_close_thr']:.2f} / 睁眼{r['blink_open_thr']:.2f}",
                          (20, 136), size=20, color=(0, 255, 255))

    if len(faces) == 0:
        draw_text(frame, "未检测到人脸，请调整位置", (20, h - 44), size=24, color=(0, 0, 255))
    elif len(faces) > 1:
        draw_text(frame, "检测到多张人脸，仅允许一张", (20, h - 44), size=24, color=(0, 0, 255))


# ==================== 主流程 ====================
def main():
    print("正在加载人脸模型...")
    app = FaceAnalysis(name="buffalo_l", providers=CONFIG["providers"])
    app.prepare(ctx_id=0, det_size=CONFIG["det_size"])

    face_mesh = mp.solutions.face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1)

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("摄像头打开失败")
        face_mesh.close()
        return

    print("人脸随机动作活体检测：按 R 开始一轮，Q / ESC 退出")

    r = new_round()  # 初始即进入基线采集

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            # InsightFace 处理 BGR，MediaPipe 处理 RGB，两者基于同一摄像头帧
            faces = app.get(frame)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mesh_results = face_mesh.process(rgb)
            left_ear, right_ear = facemesh_ear(mesh_results, frame.shape[1], frame.shape[0])

            if r["phase"] in ("success", "fail"):
                # 结果已出：等待用户按键
                pass
            else:
                step_round(r, faces, left_ear, right_ear)

            draw_hud(frame, r, faces, left_ear, right_ear)
            cv2.imshow("Random Action Liveness", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break
            if key in (ord("r"), ord("R")) and r["phase"] in ("success", "fail"):
                r = new_round()
    finally:
        face_mesh.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
