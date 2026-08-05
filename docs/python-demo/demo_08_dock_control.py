"""
demo_08_dock_control.py —— 机巢远程控制（开关舱盖、返航、重启等）

运行：
    python3 demo_08_dock_control.py

根据菜单选择操作。
"""
import requests
from config import BASE_URL, WEB_USERNAME, WEB_PASSWORD, WEB_FLAG, DOCK_SN

if DOCK_SN == "YOUR_DOCK_SN":
    import sys
    print("[✗] 请先在 config.py 中设置 DOCK_SN")
    sys.exit(1)

COMMANDS = {
    "1":  ("cover_open",           "开舱盖"),
    "2":  ("cover_close",          "关舱盖"),
    "3":  ("drone_open",           "开无人机电源"),
    "4":  ("drone_close",          "关无人机电源"),
    "5":  ("return_home",          "执行返航"),
    "6":  ("return_home_cancel",   "取消返航"),
    "7":  ("device_reboot",        "重启机巢"),
    "8":  ("charge_open",          "开始充电"),
    "9":  ("charge_close",         "停止充电"),
    "10": ("putter_open",          "推杆伸出"),
    "11": ("putter_close",         "推杆收回"),
    "12": ("supplement_light_open",  "开补光灯"),
    "13": ("supplement_light_close", "关补光灯"),
    "14": ("debug_mode_open",      "进入调试模式"),
    "15": ("debug_mode_close",     "退出调试模式"),
}

def get_token():
    resp = requests.post(f"{BASE_URL}/manage/api/v1/login",
                         json={"username": WEB_USERNAME, "password": WEB_PASSWORD, "flag": WEB_FLAG},
                         timeout=10)
    return resp.json()["data"]["access_token"]

def send_dock_command(token, cmd_id: str):
    if cmd_id not in COMMANDS:
        print(f"[!] 无效指令编号: {cmd_id}")
        return

    method, desc = COMMANDS[cmd_id]
    url = f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/jobs/{method}"

    print(f"[*] 发送指令: {desc} ({method})")
    resp = requests.post(url,
                         headers={"x-auth-token": token, "Content-Type": "application/json"},
                         json={},
                         timeout=15)
    result = resp.json()

    if result.get("code") == 0:
        print(f"[✓] {desc} 成功")
    else:
        print(f"[✗] {desc} 失败: {result}")

if __name__ == "__main__":
    print(f"[*] 目标机巢: {DOCK_SN}\n")
    token = get_token()

    print("机巢控制菜单：")
    for k, (method, desc) in COMMANDS.items():
        print(f"  {k:>2}. {desc}")
    print("   q. 退出\n")

    while True:
        cmd = input("选择操作编号: ").strip()
        if cmd == "q":
            break
        send_dock_command(token, cmd)
        print()
