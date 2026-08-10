"""
demo_05_gimbal_zoom.py -- 云台变焦（camera_focal_length_set）

变焦范围：2.0 ~ 200.0（数字变焦倍率）
运行前确保：
  1. 已在 config.py 填写正确的 DOCK_SN 和 PAYLOAD_INDEX
  2. 无人机已上线且处于 MANUAL 模式
  3. 云台处于 IDLE 状态

运行：
    python3 demo_05_gimbal_zoom.py
"""
import requests
from config import BASE_URL, WEB_USERNAME, WEB_PASSWORD, WEB_FLAG, DOCK_SN, PAYLOAD_INDEX
from demo_common import diagnose

if DOCK_SN == "YOUR_DOCK_SN":
    import sys
    print("[✗] 请先在 config.py 中设置 DOCK_SN，运行 demo_02_devices.py 可查看设备 SN")
    sys.exit(1)

ZOOM_FACTOR = 5.0   # ← 修改此值：2.0 ~ 200.0
CAMERA_TYPE = "zoom"  # ← "zoom" 或 "ir"

def get_token():
    resp = requests.post(f"{BASE_URL}/manage/api/v1/login",
                         json={"username": WEB_USERNAME, "password": WEB_PASSWORD, "flag": WEB_FLAG},
                         timeout=10)
    return resp.json()["data"]["access_token"]

def seize_payload_authority(token):
    """抢占负载控制权（必须先抢权才能控制相机）"""
    url = f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/authority/payload"
    resp = requests.post(url,
                         headers={"x-auth-token": token},
                         json={"payload_index": PAYLOAD_INDEX},
                         timeout=10)
    result = resp.json()
    if result.get("code") == 0:
        print("[✓] 已获取负载控制权")
    else:
        diagnose(token, "抢占负载控制权", result.get("message", str(result)))

def zoom(token, zoom_factor: float):
    """设置变焦倍率"""
    url = f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/payload/commands"
    body = {
        "cmd": "camera_focal_length_set",
        "data": {
            "payload_index": PAYLOAD_INDEX,
            "zoom_factor": zoom_factor,
            "camera_type": CAMERA_TYPE
        }
    }

    print(f"[*] 发送变焦指令: zoom_factor={zoom_factor} camera_type={CAMERA_TYPE}")
    resp = requests.post(url,
                         headers={"x-auth-token": token, "Content-Type": "application/json"},
                         json=body,
                         timeout=15)
    result = resp.json()

    if result.get("code") == 0:
        print(f"[✓] 变焦成功，当前倍率: {zoom_factor}x")
    else:
        diagnose(token, "变焦指令", result.get("message", str(result)), exit_on_error=False)

    return result

if __name__ == "__main__":
    print(f"[*] 目标设备: {DOCK_SN}")
    print(f"[*] 负载索引: {PAYLOAD_INDEX}")
    print(f"[*] 目标焦距: {ZOOM_FACTOR}x")

    token = get_token()
    seize_payload_authority(token)
    zoom(token, ZOOM_FACTOR)
