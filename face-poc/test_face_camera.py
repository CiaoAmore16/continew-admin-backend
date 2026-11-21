
import cv2
import numpy as np
from insightface.app import FaceAnalysis

print("正在初始化人脸识别模型...")

app = FaceAnalysis(
    name="buffalo_l",
    providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
)
app.prepare(ctx_id=0, det_size=(640, 640))

print("\n模型执行设备：")
for name, model in app.models.items():
    print(name, model.session.get_providers())

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("摄像头打开失败，请检查摄像头是否被其他程序占用。")
    raise SystemExit

print("\n摄像头已启动，请正对摄像头。")
print("按 Q 键退出。")

while True:
    ret, frame = cap.read()
    if not ret:
        print("读取摄像头画面失败")
        break

    faces = app.get(frame)

    for face in faces:
        x1, y1, x2, y2 = map(int, face.bbox)

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        feature = face.normed_embedding
        cv2.putText(
            frame,
            f"Face | Feature: {len(feature)}D",
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )

    cv2.putText(
        frame,
        f"Detected faces: {len(faces)}",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 255),
        2
    )

    cv2.imshow("InsightFace GPU Test", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("测试结束")
