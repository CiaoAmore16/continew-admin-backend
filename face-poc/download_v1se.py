
import hashlib
import json
import urllib.request
from pathlib import Path

API_URL = (
    "https://api.github.com/repos/"
    "yakhyo/face-anti-spoofing/releases/tags/weights"
)

ASSET_NAME = "MiniFASNetV1SE.onnx"
EXPECTED_SHA256 = (
    "ebab7f90c7833fbccd46d3a555410e78"
    "d969db5438e169b6524be444862b3676"
)

MODEL_DIR = Path("models")
MODEL_PATH = MODEL_DIR / ASSET_NAME
TEMP_PATH = MODEL_DIR / (ASSET_NAME + ".download")

def request(url, headers=None):
    req_headers = {
        "User-Agent": "face-poc-model-downloader",
    }
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, headers=req_headers)
    return urllib.request.urlopen(req, timeout=60)

def main():
    MODEL_DIR.mkdir(exist_ok=True)

    if MODEL_PATH.exists():
        print("目标模型文件已经存在，为避免覆盖，停止下载：")
        print(MODEL_PATH)
        return

    print("正在查询 GitHub Release...")
    with request(API_URL) as response:
        release = json.loads(response.read().decode("utf-8"))

    asset = next(
        (item for item in release["assets"]
         if item["name"] == ASSET_NAME),
        None
    )

    if asset is None:
        raise RuntimeError("Release 中没有找到 V1SE ONNX 模型")

    asset_id = asset["id"]
    asset_url = (
        "https://api.github.com/repos/"
        "yakhyo/face-anti-spoofing/releases/assets/"
        + str(asset_id)
    )

    print("找到模型:", ASSET_NAME)
    print("Asset ID:", asset_id)
    print("文件大小:", asset["size"], "bytes")
    print("开始下载...")

    try:
        with request(
            asset_url,
            {"Accept": "application/octet-stream"}
        ) as response:
            with open(TEMP_PATH, "wb") as output:
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    output.write(chunk)

        actual_size = TEMP_PATH.stat().st_size
        actual_hash = hashlib.sha256(
            TEMP_PATH.read_bytes()
        ).hexdigest()

        print("实际文件大小:", actual_size)
        print("SHA256:", actual_hash)

        if actual_hash.lower() != EXPECTED_SHA256.lower():
            raise RuntimeError("SHA256 校验失败，模型文件不可信")

        TEMP_PATH.replace(MODEL_PATH)

        print("\n模型下载并校验成功！")
        print("保存位置:", MODEL_PATH.resolve())

    finally:
        if TEMP_PATH.exists():
            TEMP_PATH.unlink()

if __name__ == "__main__":
    main()
