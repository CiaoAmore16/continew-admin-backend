import cv2
import json
import numpy as np
from pathlib import Path
from insightface.app import FaceAnalysis

# ===== 可调参数 =====
SIMILARITY_THRESHOLD = 0.4   # 余弦相似度阈值，>= 判为同一人
STABLE_FRAMES = 5            # 连续稳定帧数，达到后才确认登录
DB_PATH = Path("data") / "face_db.json"

# ===== 加载模型 =====
print("正在加载人脸识别模型...")
app = FaceAnalysis(
    name="buffalo_l",
    providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
)
app.prepare(ctx_id=0, det_size=(640, 640))

# ===== 加载人脸库 =====
if not DB_PATH.exists():
    print("人脸库不存在，请先运行 register_face.py 注册")
    raise SystemExit

database = json.loads(DB_PATH.read_text(encoding="utf-8"))
if not database:
    print("人脸库为空，请先注册")
    raise SystemExit

db_vectors = {
    name: np.asarray(info["embedding"], dtype=np.float32)
    for name, info in database.items()
}


def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


# ===== 打开摄像头 =====
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not cap.isOpened():
    print("摄像头打开失败")
    raise SystemExit

print(f"人脸登录测试：正对摄像头，按 Q 退出（阈值={SIMILARITY_THRESHOLD}，稳定帧={STABLE_FRAMES}）")

pending_name = None
pending_count = 0
login_done = False
confirmed_name = None
confirmed_sim = 0.0
fail_reported = False

while True:
    ret, frame = cap.read()
    if not ret:
        print("摄像头读取失败")
        break

    faces = app.get(frame)

    if len(faces) == 0:
        pending_name = None
        pending_count = 0
        fail_reported = False
        cv2.putText(frame, "No face - please adjust position", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    elif len(faces) > 1:
        pending_name = None
        pending_count = 0
        fail_reported = False
        cv2.putText(frame, "Multiple faces - login rejected", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    else:
        face = faces[0]
        embedding = face.normed_embedding

        # 找最匹配账号
        best_name, best_sim = None, -1.0
        for name, vec in db_vectors.items():
            sim = cosine(embedding, vec)
            if sim > best_sim:
                best_sim = sim
                best_name = name

        if best_sim >= SIMILARITY_THRESHOLD:
            # 连续同账号才累计，换人则清零重算
            if best_name == pending_name:
                pending_count += 1
            else:
                pending_name = best_name
                pending_count = 1

            if pending_count >= STABLE_FRAMES and not login_done:
                confirmed_name = best_name
                confirmed_sim = best_sim
                login_done = True
                fail_reported = False
                print("\n========== 登录成功 ==========")
                print(f"账号：{confirmed_name}")
                print(f"相似度：{confirmed_sim:.4f}")
                break
        else:
            pending_name = None
            pending_count = 0
            if not login_done and not fail_reported:
                print(f"\n登录失败：未匹配到已注册账号（最高相似度 {best_sim:.4f} < {SIMILARITY_THRESHOLD}）")
                fail_reported = True

        # 画框 + 状态
        x1, y1, x2, y2 = map(int, face.bbox)
        color = (0, 255, 0) if login_done else (0, 255, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        if login_done:
            label = f"Logged in: {confirmed_name} ({confirmed_sim:.3f})"
        elif best_sim >= SIMILARITY_THRESHOLD:
            label = f"{best_name} {best_sim:.3f} [{pending_count}/{STABLE_FRAMES}]"
        else:
            label = f"Stranger {best_sim:.3f}"
        cv2.putText(frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    cv2.imshow("Face Login", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
