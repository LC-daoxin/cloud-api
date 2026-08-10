"""
demo_10_takeoff_to_point.py -- 一键起飞并飞向指定坐标

前提：无人机已连接且在线（遥控器作为地面站上云），无人机处于可起飞状态。
     服务端会自动抢占飞行控制权。

运行：
    python3 demo_10_takeoff_to_point.py
"""
import requests
from config import BASE_URL, WEB_USERNAME, WEB_PASSWORD, WEB_FLAG, DOCK_SN

if DOCK_SN == "YOUR_DOCK_SN":
    import sys
    print("[✗] 请先在 config.py 中设置 DOCK_SN")
    sys.exit(1)

# ── 目标坐标和飞行参数（按实际情况修改）──
TARGET_LATITUDE        = 22.5431
TARGET_LONGITUDE       = 113.9213
TARGET_HEIGHT          = 50.0    # 目标飞行高度（米）
SECURITY_TAKEOFF_HEIGHT = 20.0  # 安全起飞高度（米），起飞后先爬升到此高度再水平飞
RTH_ALTITUDE           = 100.0  # 返航高度（米）
MAX_SPEED              = 5.0    # 飞行速度 1~15 m/s

def get_token():
    resp = requests.post(f"{BASE_URL}/manage/api/v1/login",
                         json={"username": WEB_USERNAME, "password": WEB_PASSWORD, "flag": WEB_FLAG},
                         timeout=10)
    return resp.json()["data"]["access_token"]

def takeoff_to_point(token):
    url = f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/jobs/takeoff-to-point"
    body = {
        "target_latitude":         TARGET_LATITUDE,
        "target_longitude":        TARGET_LONGITUDE,
        "target_height":           TARGET_HEIGHT,
        "security_takeoff_height": SECURITY_TAKEOFF_HEIGHT,
        "rth_altitude":            RTH_ALTITUDE,
        "rc_lost_action":          0,   # 0=返航, 1=悬停, 2=降落
        "exit_wayline_when_rc_lost": 0, # 0=继续, 1=退出
        "max_speed":               MAX_SPEED
    }

    print(f"[*] 起飞目标: lat={TARGET_LATITUDE}, lon={TARGET_LONGITUDE}, h={TARGET_HEIGHT}m")
    resp = requests.post(url,
                         headers={"x-auth-token": token, "Content-Type": "application/json"},
                         json=body,
                         timeout=30)
    result = resp.json()

    if result.get("code") == 0:
        print("[✓] 起飞指令已下发！")
        print("    飞行进度通过 WebSocket 推送: bizCode=takeoff_to_point_progress")
        print("    可运行 demo_03_websocket_osd.py 实时查看进度")
    else:
        print(f"[✗] 起飞失败: {result}")

if __name__ == "__main__":
    print(f"[*] 目标设备: {DOCK_SN}")
    confirm = input(f"\n即将一键起飞并飞向 ({TARGET_LATITUDE}, {TARGET_LONGITUDE})，确认? (yes/n): ")

    if confirm.lower() == "yes":
        token = get_token()
        takeoff_to_point(token)
    else:
        print("[*] 已取消")
