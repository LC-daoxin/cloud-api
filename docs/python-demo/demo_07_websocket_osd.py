"""
demo_07_websocket_osd.py -- 实时接收飞机遥测数据（OSD）

通过 WebSocket 订阅服务端推送，实时打印：
  - 飞机位置（经纬度、高度）
  - 电量、速度、姿态
  - 机巢/遥控器状态
  - 设备上下线、任务进度、目标识别、DRC 事件

依赖：pip3 install websocket-client

运行：
    python3 demo_07_websocket_osd.py
"""
import json
import requests
import websocket
import threading
import time
from config import BASE_URL, SERVER_IP, SERVER_PORT, WEB_USERNAME, WEB_PASSWORD, WEB_FLAG


def get_token():
    resp = requests.post(f"{BASE_URL}/manage/api/v1/login",
                         json={"username": WEB_USERNAME, "password": WEB_PASSWORD, "flag": WEB_FLAG},
                         timeout=10)
    return resp.json()["data"]["access_token"]


last_msg_time = [0]
msg_count = [0]


def _fmt(val, unit=""):
    """格式化数值，N/A 时返回占位"""
    if val is None or val == "":
        return "N/A"
    if isinstance(val, float):
        return f"{val:.1f}{unit}"
    return f"{val}{unit}"


def on_message(ws, message):
    last_msg_time[0] = time.time()
    msg_count[0] += 1

    try:
        msg = json.loads(message)
        biz_code = msg.get("biz_code", "")
        data = msg.get("data", {})

        if biz_code == "device_osd":
            # 无人机 OSD -- 打印完整数据
            print(f"[无人机 #{msg_count[0]}]")
            print(json.dumps(data, indent=2, ensure_ascii=False))

        elif biz_code == "gateway_osd":
            # 遥控器 OSD -- 打印完整数据
            print(f"[遥控器 #{msg_count[0]}]")
            print(json.dumps(data, indent=2, ensure_ascii=False))

        elif biz_code == "dock_osd":
            # 机巢 OSD -- 打印完整数据
            print(f"[机巢 #{msg_count[0]}]")
            print(json.dumps(data, indent=2, ensure_ascii=False))

        elif biz_code == "device_online":
            print(f"[事件] 设备上线: {json.dumps(data, ensure_ascii=False)}")

        elif biz_code == "device_offline":
            print(f"[事件] 设备离线: {json.dumps(data, ensure_ascii=False)}")

        elif biz_code in ("fly_to_point_progress", "takeoff_to_point_progress", "flighttask_progress"):
            print(f"[进度] {biz_code}: {json.dumps(data, ensure_ascii=False)}")

        elif biz_code == "target_detect_result":
            print(f"[目标识别] {json.dumps(data, ensure_ascii=False)}")

        elif biz_code == "drc_status_notify":
            print(f"[DRC状态] {json.dumps(data, ensure_ascii=False)}")

        elif biz_code == "joystick_invalid_notify":
            print(f"[Joystick无效] {json.dumps(data, ensure_ascii=False)}")

        else:
            print(f"[消息#{msg_count[0]}] biz_code={biz_code}: {json.dumps(data, ensure_ascii=False)}")

    except Exception as e:
        print(f"[原始] {message}")


def on_error(ws, error):
    print(f"[✗] WebSocket 错误: {error}")


def on_close(ws, close_status_code, close_msg):
    print(f"[*] WebSocket 已关闭: {close_status_code} {close_msg}")


def on_open(ws):
    print("[✓] WebSocket 已连接，等待推送数据...\n")

    def _watchdog():
        time.sleep(12)
        if msg_count[0] == 0:
            print("\n[!] 12 秒内未收到任何推送，可能原因：")
            print("    - 设备未完成上线握手（未发送 update_topo）")
            print("    - 设备已离线（Redis 无在线 key）")
            print("    验证: docker exec uav-redis redis-cli keys '*online*'\n")
    threading.Thread(target=_watchdog, daemon=True).start()


if __name__ == "__main__":
    token = get_token()
    ws_url = f"ws://{SERVER_IP}:{SERVER_PORT}/api/v1/ws?x-auth-token={token}"

    print(f"[*] 连接 WebSocket: {ws_url[:60]}...")

    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] 用户中断，关闭连接")
        ws.close()
