
import cv2
import json
import time
import numpy as np
from pathlib import Path
from insightface.app import FaceAnalysis
# 人脸重复检测阈值（初始测试值，后续需要校准）
DUPLICATE_THRESHOLD = 0.45


def find_duplicate_face(new_embedding, database):
    """检测新的人脸特征是否与已有账号重复"""
    best_name = None
    best_similarity = -1.0

    for name, info in database.items():
        old_embedding = np.asarray(
            info["embedding"], dtype=np.float32
        )

        similarity = float(np.dot(new_embedding, old_embedding))

        if similarity > best_similarity:
            best_similarity = similarity
            best_name = name

    if best_similarity >= DUPLICATE_THRESHOLD:
        return best_name, best_similarity

    return None, best_similarity

# 初始化模型
print("正在加载人脸识别模型...")

app = FaceAnalysis(
    name="buffalo_l",
    providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
)
app.prepare(ctx_id=0, det_size=(640, 640))

# 注册信息
username = input("\n请输入注册账号：").strip()

if not username:
    print("账号不能为空")
    raise SystemExit

# 本地特征数据库
db_dir = Path("data")
db_dir.mkdir(exist_ok=True)
db_file = db_dir / "face_db.json"

if db_file.exists():
    database = json.loads(db_file.read_text(encoding="utf-8"))
else:
    database = {}

if username in database:
    print("该账号已经注册过人脸，请勿重复注册")
    raise SystemExit

# 打开摄像头
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("摄像头打开失败")
    raise SystemExit

print("\n请正对摄像头，保持光线充足。")
print("程序将自动采集10次有效人脸特征。")

features = []
last_capture = 0

while len(features) < 10:
    ret, frame = cap.read()

    if not ret:
        print("摄像头读取失败")
        break

    faces = app.get(frame)

    # 仅采集检测到一张人脸的画面
    if len(faces) == 1:
        face = faces[0]
        now = time.time()

        if now - last_capture >= 0.3:
            features.append(face.normed_embedding.copy())
            last_capture = now

        x1, y1, x2, y2 = map(int, face.bbox)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    elif len(faces) > 1:
        cv2.putText(
            frame, "Only one face allowed",
            (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
            0.7, (0, 0, 255), 2
        )

    progress = f"Collected: {len(features)}/10"
    cv2.putText(
        frame, progress, (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8, (0, 255, 255), 2
    )

    cv2.imshow("Face Registration", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        print("用户取消注册")
        break

cap.release()
cv2.destroyAllWindows()

if len(features) != 10:
    print("有效特征不足10个，本次不保存")
    raise SystemExit

# 融合特征并归一化
embedding = np.mean(features, axis=0)
embedding = embedding / np.linalg.norm(embedding)

# 检查是否与已有账号的人脸重复
duplicate_name, duplicate_similarity = find_duplicate_face(
    embedding, database
)

if duplicate_name is not None:
    print("\n========== 注册失败 ==========")
    print(f"该人脸已经注册过，关联账号：{duplicate_name}")
    print(f"人脸相似度：{duplicate_similarity:.4f}")
    print("请勿使用同一张人脸重复注册。")
    raise SystemExit
# 保存特征
database[username] = {
    "embedding": embedding.tolist(),
    "dimension": int(len(embedding)),
    "sample_count": len(features),
    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
}

db_file.write_text(
    json.dumps(database, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("\n========== 注册成功 ==========")
print("账号：", username)
print("特征维度：", len(embedding))
print("采集次数：", len(features))
print("保存位置：", db_file.resolve())
