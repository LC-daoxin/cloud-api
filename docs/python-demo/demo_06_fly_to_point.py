"""
demo_06_fly_to_point.py —— 控制无人机飞向指定 GPS 坐标

前提：无人机已在空中（已起飞），处于 MANUAL 模式。
     机巢需在线且云端有飞行控制权。

运行：
    python3 demo_06_fly_to_point.py
"""
import requests
from config import BASE_URL, WEB_USERNAME, WEB_PASSWORD, WEB_FLAG, DOCK_SN

if DOCK_SN == "YOUR_DOCK_SN":
    import sys
    print("[✗] 请先在 config.py 中设置 DOCK_SN")
    sys.exit(1)

# ── 目标坐标（修改为实际目标位置）──
TARGET_LATITUDE  = 22.5431
TARGET_LONGITUDE = 113.9213
TARGET_HEIGHT    = 50.0   # 单位：米（海拔高度或相对高度，取决于固件）
MAX_SPEED        = 5      # 1~15 m/s

def get_token():
    resp = requests.post(f"{BASE_URL}/manage/api/v1/login",
                         json={"username": WEB_USERNAME, "password": WEB_PASSWORD, "flag": WEB_FLAG},
                         timeout=10)
    return resp.json()["data"]["access_token"]

def fly_to_point(token):
    url = f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/jobs/fly-to-point"
    body = {
        "max_speed": MAX_SPEED,
        "points": [
            {
                "latitude": TARGET_LATITUDE,
                "longitude": TARGET_LONGITUDE,
                "height": TARGET_HEIGHT
            }
        ]
    }

    print(f"[*] 飞向坐标: lat={TARGET_LATITUDE}, lon={TARGET_LONGITUDE}, h={TARGET_HEIGHT}m")
    resp = requests.post(url,
                         headers={"x-auth-token": token, "Content-Type": "application/json"},
                         json=body,
                         timeout=20)
    result = resp.json()

    if result.get("code") == 0:
        print("[✓] 飞向目标点指令已下发，飞行进度通过 WebSocket 推送")
        print("    bizCode: fly_to_point_progress")
    else:
        print(f"[✗] 失败: {result}")

def stop_fly_to_point(token):
    """取消飞向目标点"""
    url = f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/jobs/fly-to-point"
    resp = requests.delete(url,
                           headers={"x-auth-token": token},
                           timeout=10)
    print(f"[✓] 已发送停止指令: {resp.json()}")

if __name__ == "__main__":
    print(f"[*] 目标机巢: {DOCK_SN}")
    token = get_token()

    action = input("输入 go=飞向目标点 / stop=停止 / q=退出: ").strip()
    if action == "go":
        fly_to_point(token)
    elif action == "stop":
        stop_fly_to_point(token)
