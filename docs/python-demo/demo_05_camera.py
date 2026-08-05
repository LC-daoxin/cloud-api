"""
demo_05_camera.py —— 拍照 / 开始录像 / 停止录像

运行：
    python3 demo_05_camera.py photo       # 拍一张照片
    python3 demo_05_camera.py rec_start   # 开始录像
    python3 demo_05_camera.py rec_stop    # 停止录像
"""
import sys
import requests
from config import BASE_URL, WEB_USERNAME, WEB_PASSWORD, WEB_FLAG, DOCK_SN, PAYLOAD_INDEX

if DOCK_SN == "YOUR_DOCK_SN":
    print("[✗] 请先在 config.py 中设置 DOCK_SN")
    sys.exit(1)

def get_token():
    resp = requests.post(f"{BASE_URL}/manage/api/v1/login",
                         json={"username": WEB_USERNAME, "password": WEB_PASSWORD, "flag": WEB_FLAG},
                         timeout=10)
    return resp.json()["data"]["access_token"]

def seize_payload_authority(token):
    url = f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/authority/payload"
    resp = requests.post(url,
                         headers={"x-auth-token": token},
                         json={"payload_index": PAYLOAD_INDEX},
                         timeout=10)
    result = resp.json()
    print(f"[{'✓' if result.get('code')==0 else '!'}] 抢占负载控制权")

def send_payload_cmd(token, cmd: str, extra: dict = None):
    url = f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/payload/commands"
    data = {"payload_index": PAYLOAD_INDEX}
    if extra:
        data.update(extra)
    body = {"cmd": cmd, "data": data}

    print(f"[*] 发送指令: {cmd}")
    resp = requests.post(url,
                         headers={"x-auth-token": token, "Content-Type": "application/json"},
                         json=body,
                         timeout=15)
    result = resp.json()

    ok = result.get("code") == 0
    print(f"[{'✓' if ok else '✗'}] {result.get('message', result)}")
    return result

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "photo"

    print(f"[*] 目标机巢: {DOCK_SN}  负载: {PAYLOAD_INDEX}")
    token = get_token()
    seize_payload_authority(token)

    if action == "photo":
        # 拍照前切换到拍照模式
        send_payload_cmd(token, "camera_mode_switch", {"camera_mode": 0})  # 0=拍照模式
        send_payload_cmd(token, "camera_photo_take")

    elif action == "rec_start":
        # 录像前切换到录像模式
        send_payload_cmd(token, "camera_mode_switch", {"camera_mode": 1})  # 1=录像模式
        send_payload_cmd(token, "camera_recording_start")

    elif action == "rec_stop":
        send_payload_cmd(token, "camera_recording_stop")

    else:
        print(f"未知操作: {action}")
        print("用法: python3 demo_05_camera.py [photo|rec_start|rec_stop]")
