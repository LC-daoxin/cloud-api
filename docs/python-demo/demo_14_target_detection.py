"""
demo_14_target_detection.py -- 目标识别（AI 检测）

[YOOX Cloud GCS 专用接口]
原版 Cloud-API 不包含此接口，会返回 404。

接口：
  POST /control/api/v1/devices/{sn}/target-detection    开启
  DELETE /control/api/v1/devices/{sn}/target-detection  关闭

参数说明：
  ai_lens_type:    0=可见光  1=红外
  scene_type:      0=通用（目前仅支持0）
  target_type_list: 目标类型列表
    0=person（人）
    1=car（车）
    2=boat（船）

识别结果：
  通过 WebSocket bizCode=target_detect_result 推送
  可用 demo_03_websocket_osd.py 接收（已自动显示未知 bizCode 的原始数据）

运行：
    python3 demo_14_target_detection.py
"""
import sys
import requests
from config import BASE_URL, WEB_USERNAME, WEB_PASSWORD, WEB_FLAG, DOCK_SN

# ── 目标识别配置 ──────────────────────────────────────────
AI_LENS_TYPE = 0         # 0=可见光  1=红外
SCENE_TYPE = 0           # 目前只支持 0
TARGET_TYPES = [0, 1]    # 0=人  1=车  2=船


def get_token():
    resp = requests.post(f"{BASE_URL}/manage/api/v1/login",
                         json={"username": WEB_USERNAME, "password": WEB_PASSWORD, "flag": WEB_FLAG},
                         timeout=10)
    return resp.json()["data"]["access_token"]


def open_target_detection(token):
    """开启目标识别"""
    url = f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/target-detection"
    body = {
        "ai_lens_type": AI_LENS_TYPE,
        "scene_type": SCENE_TYPE,
        "target_type_list": TARGET_TYPES
    }
    resp = requests.post(url,
                         headers={"x-auth-token": token, "Content-Type": "application/json"},
                         json=body, timeout=15)
    result = resp.json()
    if result.get("code") == 0:
        print(f"[✓] 目标识别已开启  lens={AI_LENS_TYPE} targets={TARGET_TYPES}")
        print("    识别结果通过 WebSocket 推送（bizCode: target_detect_result）")
        print("    可运行 demo_03_websocket_osd.py 实时接收")
    else:
        print(f"[✗] 开启失败: {result}")
        if resp.status_code == 404:
            print("    [!] 404 表示当前运行的是原版 Cloud-API，此接口需要 YOOX Cloud GCS 版本")
    return result


def close_target_detection(token):
    """关闭目标识别"""
    url = f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/target-detection"
    resp = requests.delete(url, headers={"x-auth-token": token}, timeout=15)
    result = resp.json()
    print(f"[{'✓' if result.get('code')==0 else '✗'}] 目标识别已关闭: {result.get('message','')}")
    return result


if __name__ == "__main__":
    print(f"[*] 目标设备: {DOCK_SN}")
    if DOCK_SN == "YOUR_DOCK_SN":
        print("[✗] 请先在 config.py 中设置 DOCK_SN")
        sys.exit(1)
    print(f"[!] 本 demo 需要 YOOX Cloud GCS 版本（原版 Cloud-API 无此接口）\n")

    token = get_token()

    print("操作菜单：")
    print("  1. 开启目标识别")
    print("  2. 关闭目标识别")
    print("  q. 退出\n")

    while True:
        cmd = input("选择: ").strip()
        if cmd == "q":
            break
        elif cmd == "1":
            open_target_detection(token)
        elif cmd == "2":
            close_target_detection(token)
        else:
            print("  未知操作")
