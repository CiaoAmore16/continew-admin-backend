
import cv2
import numpy as np
import onnxruntime as ort
from insightface.app import FaceAnalysis

print("========== 人脸模型初始化 ==========")

print("NumPy:", np.__version__)
print("OpenCV:", cv2.__version__)
print("ONNX Runtime:", ort.__version__)
print("可用推理设备:", ort.get_available_providers())

# 优先使用 GPU，CPU 作为备用
providers = [
    "CUDAExecutionProvider",
    "CPUExecutionProvider"
]

print("\n正在加载 buffalo_l 模型...")

app = FaceAnalysis(
    name="buffalo_l",
    providers=providers
)

app.prepare(
    ctx_id=0,
    det_size=(640, 640)
)

print("\n========== 模型加载成功 ==========")

for name, model in app.models.items():
    print(f"模型名称: {name}")
    print(f"模型类型: {type(model).__name__}")
    print(f"模型输入尺寸: {getattr(model, 'input_size', None)}")

print("\n人脸识别模型已经准备就绪！")
