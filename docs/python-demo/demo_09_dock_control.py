"""
demo_09_dock_control.py -- 设备远程控制（返航、重启等）

接口：POST /control/api/v1/devices/{sn}/jobs/{method}，请求体为 {}

其中 5/6 为一键返航与取消返航，无论是否有机巢都可用；
开舱盖/充电/推杆/补光灯等仅在机巢场景下有效。
更完整的应急处置（急停/紧急降落/强制降落）见 demo_15_emergency.py。

运行：
    python3 demo_09_dock_control.py

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
    "5":  ("return_home",          "一键返航（飞行器飞回返航点）"),
    "6":  ("return_home_cancel",   "取消返航（原地悬停）"),
    "7":  ("device_reboot",        "重启设备"),
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

    # 返航会真实改变飞行器航迹，先确认
    if method == "return_home":
        if input("  [!] 确认一键返航？输入 YES 确认: ").strip() != "YES":
            print("  已取消")
            return

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
    print(f"[*] 目标设备: {DOCK_SN}\n")
    token = get_token()

    print("设备控制菜单：")
    for k, (method, desc) in COMMANDS.items():
        print(f"  {k:>2}. {desc}")
    print("   q. 退出\n")

    while True:
        cmd = input("选择操作编号: ").strip()
        if cmd == "q":
            break
        send_dock_command(token, cmd)
        print()
