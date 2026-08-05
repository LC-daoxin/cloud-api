"""
demo_04_gimbal_pitch.py —— 云台指向控制（camera_aim 屏幕坐标 + gimbal_reset）

关键说明：
  camera_aim 是「屏幕坐标指点」接口，不是连续转速控制。
  x、y 均为 0.0 ~ 1.0 的归一化屏幕坐标：
    x = 0.0 左边，x = 1.0 右边，x = 0.5 水平居中
    y = 0.0 画面上方（仰角），y = 1.0 画面下方（俯角），y = 0.5 水平
  camera_type: "zoom" | "wide" | "ir"

  gimbal_reset 模式：
    0 = RECENTER       仰仰角居中（水平居中）
    1 = DOWN           直贯下方
    2 = RECENTER_PAN   偏转角居中、仰仰角保持
    3 = PITCH_DOWN     仰仰角居中、值下为水平

运行：
    python3 demo_04_gimbal_pitch.py
"""
import sys
import requests
from config import BASE_URL, WEB_USERNAME, WEB_PASSWORD, WEB_FLAG, DOCK_SN, PAYLOAD_INDEX

if DOCK_SN == "YOUR_DOCK_SN":
    print("[✗] 请先在 config.py 中设置 DOCK_SN，运行 demo_02_devices.py 可查看设备 SN")
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
    if result.get("code") != 0:
        print(f"[✗] 抢占负载控制权失败: {result.get('message','')}\n    请确认机巢和无人机均已上线")
        sys.exit(1)
    print("[✓] 已获取负载控制权")


def camera_aim(token, x: float, y: float, camera_type: str = "zoom", locked: bool = False):
    """
    屏幕坐标指点控制
    x, y: 0.0 ~ 1.0 屏幕归一化坐标
    camera_type: zoom / wide / ir
    locked: True = 锁定跟踪目标点，False = 单次指向
    """
    url = f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/payload/commands"
    body = {
        "cmd": "camera_aim",
        "data": {
            "payload_index": PAYLOAD_INDEX,
            "x": x,
            "y": y,
            "locked": locked,
            "camera_type": camera_type
        }
    }
    resp = requests.post(url,
                         headers={"x-auth-token": token, "Content-Type": "application/json"},
                         json=body,
                         timeout=10)
    return resp.json()


def gimbal_reset(token, mode: int = 0):
    """
    云台复位
    mode: 0=居中  1=向下  2=偏转居中  3=仰角居中
    """
    url = f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/payload/commands"
    body = {
        "cmd": "gimbal_reset",
        "data": {
            "payload_index": PAYLOAD_INDEX,
            "reset_mode": mode
        }
    }
    resp = requests.post(url,
                         headers={"x-auth-token": token, "Content-Type": "application/json"},
                         json=body,
                         timeout=10)
    result = resp.json()
    mode_name = {0: "居中", 1: "向下", 2: "偏转居中", 3: "仰角居中"}.get(mode, str(mode))
    print(f"[{'✓' if result.get('code')==0 else '✗'}] 云台复位({mode_name}): {result.get('message','')}")


if __name__ == "__main__":
    print(f"[*] 目标机巢: {DOCK_SN}")
    print(f"[*] 负载索引: {PAYLOAD_INDEX}\n")

    token = get_token()
    seize_payload_authority(token)

    print("""云台控制指令（camera_aim 屏幕坐标指向）：
  up        → 指向上方（y=0.0 画面上方）
  down      → 指向下方（y=1.0 画面下方）
  left      → 指向左方（x=0.0 画面左边）
  right     → 指向右方（x=1.0 画面右边）
  center    → 指向画面中心（x=0.5, y=0.5）
  horizon   → 云台居中（gimbal_reset mode=0）
  down90    → 云台垂直下射（gimbal_reset mode=1）
  q         → 退出
  自定义: x=<0~1>,y=<0~1>  如 x=0.3,y=0.7
""")

    while True:
        cmd = input("输入指令: ").strip().lower()

        if cmd == "q":
            break
        elif cmd == "up":
            result = camera_aim(token, x=0.5, y=0.0)
            print(f"  [{'✓' if result.get('code')==0 else '✗'}] 指向上方: {result.get('message','')}")
        elif cmd == "down":
            result = camera_aim(token, x=0.5, y=1.0)
            print(f"  [{'✓' if result.get('code')==0 else '✗'}] 指向下方: {result.get('message','')}")
        elif cmd == "left":
            result = camera_aim(token, x=0.0, y=0.5)
            print(f"  [{'✓' if result.get('code')==0 else '✗'}] 指向左方: {result.get('message','')}")
        elif cmd == "right":
            result = camera_aim(token, x=1.0, y=0.5)
            print(f"  [{'✓' if result.get('code')==0 else '✗'}] 指向右方: {result.get('message','')}")
        elif cmd == "center":
            result = camera_aim(token, x=0.5, y=0.5)
            print(f"  [{'✓' if result.get('code')==0 else '✗'}] 指向画面中心: {result.get('message','')}")
        elif cmd == "horizon":
            gimbal_reset(token, mode=0)
        elif cmd == "down90":
            gimbal_reset(token, mode=1)
        elif cmd.startswith("x="):
            try:
                parts = {k: float(v) for k, v in (p.split("=") for p in cmd.split(","))}
                result = camera_aim(token, x=parts["x"], y=parts["y"])
                print(f"  [{'✓' if result.get('code')==0 else '✗'}] 自定义坐标({cmd}): {result.get('message','')}")
            except Exception as e:
                print(f"  格式错误：{e}，示例: x=0.3,y=0.7")
        else:
            print("  未知指令，请输入 up/down/left/right/center/horizon/down90/q")
