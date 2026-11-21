"""
静默人脸活体检测模型测试（Silent Face Anti-Spoofing / MiniFASNet）。

用途：在摄像头实时画面中测试 MiniFASNetV1SE / MiniFASNetV2 两个 ONNX 活体检测模型，
支持单独测试与同帧对比，并实时显示「原始 logits → softmax 置信度 → 阈值判定」三者的关系。

模型来源与说明（重要，先读）：
- 模型文件 models/MiniFASNetV1SE.onnx / models/MiniFASNetV2.onnx 来自第三方仓库
  yakhyo/face-anti-spoofing 的 GitHub Release（下载与 SHA256 校验见 download_v1se.py）。
  官方 minivision-ai/Silent-Face-Anti-Spoofing 只发布 .pth / MNN，不发布 ONNX，
  因此这里的 ONNX 属于第三方导出，并非官方 minivision 权重。
- 官方 minivision 仓库为 Apache-2.0 许可；本第三方 fork 的许可因网络限制未能核实，
  使用前请自行确认其许可。
- 输入：1x3x80x80，float32，BGR，像素值 0~255（无归一化）。
  预处理：以人脸框中心放大 crop（V2 缩放 2.7、V1SE 缩放 4.0）→ resize 到 80x80。
- 输出：3 个原始 logits（未经 softmax）。类别定义（依据随权重分发的
  onnx_inference_reference.py 及作者 uniface 文档，并经真/照片实测印证）：
      index 0 = Fake（具体攻击类型未确认）
      index 1 = Real（真人）
      index 2 = Fake（具体攻击类型未确认，实测照片命中此类）
  本脚本按 index==1 为真人处理。
- 阈值：P(真人) >= REAL_THRESHOLD 判为真人。该阈值仅为实验参考值，未经安全评估，
  不能作为可靠的安全标准；单张/单帧测试也不足以证明模型安全。

运行：
  .venv-face/Scripts/python.exe test_pad_models.py [--model both|v1se|v2] [--threshold 0.5]
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image, ImageDraw, ImageFont
from insightface.app import FaceAnalysis

SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_DIR = SCRIPT_DIR / "models"
RESULT_FILE = SCRIPT_DIR / "pad_test_results.json"

# 模型配置：crop 缩放系数依据 yakhyo 仓库（V2=2.7，V1SE=4.0）
MODELS = {
    "v1se": {"file": "MiniFASNetV1SE.onnx", "scale": 4.0, "label": "V1SE"},
    "v2": {"file": "MiniFASNetV2.onnx", "scale": 2.7, "label": "V2"},
}

# 3 类输出。真人 = index 1（依据随权重分发的参考实现与作者文档）。
# index 0 / 2 为 Fake，具体攻击类型未确认，不擅自标注为 2D/3D。
CLASS_NAMES = ["Fake(类型未确认)", "Real", "Fake(类型未确认)"]
REAL_INDEX = 1  # 真人对应的输出索引

# 分场景标记（键盘 1/2/3 或 S 切换当前场景）
SCENARIOS = ["真人", "手机静态照片", "手机播放视频"]

# 人脸检测 / PAD 推理执行提供程序（CUDA 优先，回退 CPU）
PROVIDERS = ["CUDAExecutionProvider", "CPUExecutionProvider"]


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


def draw_text(frame, text, org, size=20, color=(255, 255, 255), stroke=1):
    """用 PIL 绘制中文，org 为左上角坐标。"""
    rgb = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(rgb)
    draw.text(org, text, font=_font(size),
              fill=(color[2], color[1], color[0]),
              stroke_width=stroke, stroke_fill=(0, 0, 0))
    frame[:, :, :] = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2BGR)


# ==================== 推理辅助 ====================
def softmax(x):
    """数值稳定的 softmax。"""
    e = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


def crop_face(frame, bbox, scale, size=80):
    """按人脸框中心放大裁剪并预处理为 (1,3,80,80) float32 BGR。

    与 yakhyo 仓库参考实现一致：放大 scale 倍、居中、越界裁剪、resize、HWC->CHW、加 batch。
    不归一化（像素保持 0~255），不转 RGB。
    """
    x1, y1, x2, y2 = map(float, bbox)
    box_w, box_h = x2 - x1, y2 - y1
    if box_w <= 0 or box_h <= 0:
        return None
    h, w = frame.shape[:2]

    s = min((h - 1) / box_h, (w - 1) / box_w, scale)
    new_w, new_h = box_w * s, box_h * s
    cx, cy = x1 + box_w / 2, y1 + box_h / 2

    left = max(0, int(cx - new_w / 2))
    top = max(0, int(cy - new_h / 2))
    right = min(w - 1, int(cx + new_w / 2))
    bottom = min(h - 1, int(cy + new_h / 2))

    crop = frame[top:bottom + 1, left:right + 1]
    if crop.size == 0:
        return None

    face = cv2.resize(crop, (size, size))
    face = face.astype(np.float32)
    face = np.transpose(face, (2, 0, 1))
    face = np.expand_dims(face, axis=0)
    return face


class PADModel:
    """封装一个 MiniFASNet ONNX 活体检测模型。"""

    def __init__(self, key):
        cfg = MODELS[key]
        path = MODEL_DIR / cfg["file"]
        if not path.exists():
            raise FileNotFoundError(
                f"缺少模型 {path}。下载来源：yakhyo/face-anti-spoofing 的 GitHub Release"
                f"（参见 download_v1se.py 的下载与 SHA256 校验），放置到 models/ 目录。"
            )
        self.key = key
        self.label = cfg["label"]
        self.scale = cfg["scale"]
        self.session = ort.InferenceSession(str(path), providers=PROVIDERS)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    def predict(self, frame, bbox):
        """返回 {'logits', 'probs', 'latency_ms'}；裁剪失败返回 None。"""
        tensor = crop_face(frame, bbox, self.scale)
        if tensor is None:
            return None
        t0 = time.perf_counter()
        logits = self.session.run([self.output_name], {self.input_name: tensor})[0][0]
        latency_ms = (time.perf_counter() - t0) * 1000.0
        probs = softmax(logits)
        return {"logits": logits, "probs": probs, "latency_ms": latency_ms}


def decide(probs, threshold):
    """由 softmax 置信度做最终阈值判定。

    返回 (label, real_prob)。区分「置信度」与「阈值判定」：
    real_prob 是模型对真人(index 1)的置信度，label 是叠加阈值后的最终结论。
    """
    real_prob = float(probs[REAL_INDEX])
    label = "真人" if real_prob >= threshold else "疑似攻击"
    return label, real_prob


def new_stat():
    """新建一个统计累加器。"""
    return {"frames": 0, "real": 0, "attack": 0, "real_prob_sum": 0.0, "lat_sum": 0.0}


def record_stat(st, label, real_prob, latency_ms):
    """把一帧判定结果累加到统计字典 st。"""
    st["frames"] += 1
    st["real_prob_sum"] += real_prob
    st["lat_sum"] += latency_ms
    if label == "真人":
        st["real"] += 1
    else:
        st["attack"] += 1


def summarize_stat(st):
    """把统计累加器导出为可读/可序列化结果。"""
    n = st["frames"]
    return {
        "frames": n,
        "real": st["real"],
        "attack": st["attack"],
        "avg_real_prob": round(st["real_prob_sum"] / n, 4) if n else None,
        "avg_latency_ms": round(st["lat_sum"] / n, 2) if n else None,
    }


# ==================== 主流程 ====================
def main():
    parser = argparse.ArgumentParser(description="MiniFASNet 静默活体检测模型测试")
    parser.add_argument("--model", choices=["both", "v1se", "v2"], default="both",
                        help="测试哪个模型：both 对比 / v1se / v2")
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="真人判定阈值 P(真人)>=该值（实验参考值）")
    args = parser.parse_args()

    keys = ["v1se", "v2"] if args.model == "both" else [args.model]

    print("正在加载人脸检测模型 InsightFace ...")
    app = FaceAnalysis(name="buffalo_l", providers=PROVIDERS)
    app.prepare(ctx_id=0, det_size=(640, 640))

    print("正在加载活体检测模型 ...")
    models = {}
    for key in keys:
        models[key] = PADModel(key)
        print(f"  {models[key].label}: 已加载（crop 缩放 {models[key].scale}）")

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("摄像头打开失败")
        return

    print("按 Q / ESC 退出；按 1/2/3 或 S 切换场景。")
    print(f"判定阈值：P(真人) >= {args.threshold}（实验参考值，非安全标准）")
    print("场景: " + " / ".join(f"{i + 1}={s}" for i, s in enumerate(SCENARIOS)) + "\n")

    stats = {key: new_stat() for key in keys}
    scenario_stats = {key: {s: new_stat() for s in SCENARIOS} for key in keys}
    scenario_idx = 0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            faces = app.get(frame)

            scenario_text = f"场景: {SCENARIOS[scenario_idx]}  (1/2/3 或 S 切换)"
            draw_text(frame, scenario_text, (20, 20), size=24, color=(0, 255, 255))

            if len(faces) == 0:
                draw_text(frame, "未检测到人脸", (20, 58), size=24, color=(0, 0, 255))
            elif len(faces) > 1:
                draw_text(frame, "检测到多张人脸，仅处理第一张", (20, 58), size=24, color=(0, 0, 255))
            else:
                face = faces[0]
                x1, y1, x2, y2 = map(int, face.bbox)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                legend = " ".join(f"[{i}]{CLASS_NAMES[i]}" for i in range(3))
                draw_text(frame, f"类别: {legend}", (20, 58), size=18, color=(180, 180, 180))

                y = 88
                for key in keys:
                    m = models[key]
                    res = m.predict(frame, face.bbox)
                    if res is None:
                        continue
                    label, real_prob = decide(res["probs"], args.threshold)

                    record_stat(stats[key], label, real_prob, res["latency_ms"])
                    record_stat(scenario_stats[key][SCENARIOS[scenario_idx]],
                                label, real_prob, res["latency_ms"])

                    color = (0, 255, 0) if label == "真人" else (0, 0, 255)
                    line1 = f"[{m.label}] {label}  P(Real)={real_prob:.2f}  (阈{args.threshold:.2f})"
                    draw_text(frame, line1, (20, y), size=22, color=color)
                    y += 28

                    probs_str = " ".join(f"{p:.2f}" for p in res["probs"])
                    logits_str = " ".join(f"{l:+.2f}" for l in res["logits"])
                    line2 = (f"  softmax[{probs_str}]  logits[{logits_str}]  "
                             f"{res['latency_ms']:.1f}ms")
                    draw_text(frame, line2, (20, y), size=18, color=(200, 200, 200))
                    y += 26

            cv2.imshow("MiniFASNet PAD Test", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break
            if key in (ord("s"), ord("S"), ord(" "), ord("n"), ord("N")):
                scenario_idx = (scenario_idx + 1) % len(SCENARIOS)
                print(f"当前场景: {SCENARIOS[scenario_idx]}")
            elif key in (ord("1"), ord("2"), ord("3")):
                scenario_idx = key - ord("1")
                print(f"当前场景: {SCENARIOS[scenario_idx]}")
    finally:
        cap.release()
        cv2.destroyAllWindows()

    # 汇总并保存结果
    summary = {}
    scenario_summary = {}
    for key in keys:
        summary[key] = {"model": MODELS[key]["label"], **summarize_stat(stats[key])}
        scenario_summary[key] = {
            "model": MODELS[key]["label"],
            "scenarios": {s: summarize_stat(scenario_stats[key][s]) for s in SCENARIOS},
        }

    print("\n===== 测试结果汇总 =====")
    for key in keys:
        s = summary[key]
        print(f"[{s['model']} 总体] 帧数={s['frames']}  真人={s['real']}  攻击={s['attack']}  "
              f"平均P(Real)={s['avg_real_prob']}  平均耗时={s['avg_latency_ms']}ms")
        for sc in SCENARIOS:
            scs = scenario_summary[key]["scenarios"][sc]
            print(f"    {sc}: 帧数={scs['frames']}  真人={scs['real']}  攻击={scs['attack']}  "
                  f"平均P(Real)={scs['avg_real_prob']}  平均耗时={scs['avg_latency_ms']}ms")

    result = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "threshold": args.threshold,
        "note": "阈值与类别映射仅为实验参考，未经安全评估",
        "models": summary,
        "scenarios": scenario_summary,
    }
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到 {RESULT_FILE}")


if __name__ == "__main__":
    main()
