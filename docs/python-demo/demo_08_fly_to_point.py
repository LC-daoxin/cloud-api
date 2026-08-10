"""
demo_08_fly_to_point.py -- 控制无人机飞向指定 GPS 坐标

完整流程：
  1. flight_authority_grab  抢夺飞行控制权
     POST /control/api/v1/devices/{sn}/authority/flight  （无请求体）
     服务端下发 thing/product/{sn}/services，method=flight_authority_grab
     结果在 thing/product/{sn}/services_reply 返回，result=0 成功
  2. fly-to-point           下发飞向目标点
  3. fly_to_point_progress  订阅执行进度，直到终态

进度事件：
  Topic : thing/product/{gateway_sn}/events    Direction: up
  Method: fly_to_point_progress

  | 字段                 | 说明                                     |
  |----------------------|------------------------------------------|
  | fly_to_id            | 本次 flyto 任务唯一标识                  |
  | status               | wayline_progress/ok/failed/cancel        |
  | result               | 返回码，非 0 代表错误                    |
  | way_point_index      | 当前飞往第几个航点                       |
  | remaining_distance   | 距目标点剩余距离（米）                   |
  | remaining_time       | 预计剩余时间（秒）                       |
  | planned_path_points  | 规划轨迹点列表 [{latitude,longitude,height}] |

【说明】本 demo 直接订阅 MQTT events 而不是走 WebSocket，以展示设备上报的原始报文。
       服务端已补齐 FlyToPointProgress 模型并透传全部字段到 WebSocket
       （见 SDKControlService.flyToPointProgress + FlyToPointProgressNotifyDTO），
       该改动需重新构建镜像后生效。

前提：无人机已在空中（已起飞），处于 MANUAL 模式，设备在线。

运行：
    python3 demo_08_fly_to_point.py
"""
import sys
import json
import time
import requests
import paho.mqtt.client as mqtt
from config import (BASE_URL, WEB_USERNAME, WEB_PASSWORD, WEB_FLAG, DOCK_SN,
                    MQTT_HOST, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD)

if DOCK_SN == "YOUR_DOCK_SN":
    print("[✗] 请先在 config.py 中设置 DOCK_SN")
    sys.exit(1)

# ── 目标坐标（修改为实际目标位置）──
TARGET_LATITUDE  = 22.5431
TARGET_LONGITUDE = 113.9213
TARGET_HEIGHT    = 50.0   # 单位：米（海拔高度或相对高度，取决于固件）
MAX_SPEED        = 5      # 1~15 m/s

EVENTS_TOPIC = f"thing/product/{DOCK_SN}/events"
SERVICES_REPLY_TOPIC = f"thing/product/{DOCK_SN}/services_reply"

FLY_TO_STATUS = {
    "wayline_progress": "执行中",
    "wayline_ok":       "执行成功，已飞抵目标点",
    "wayline_failed":   "执行失败",
    "wayline_cancel":   "已取消飞向目标点",
}
FINAL_STATUS = {"wayline_ok", "wayline_failed", "wayline_cancel"}


def get_token():
    resp = requests.post(f"{BASE_URL}/manage/api/v1/login",
                         json={"username": WEB_USERNAME, "password": WEB_PASSWORD, "flag": WEB_FLAG},
                         timeout=10)
    return resp.json()["data"]["access_token"]


def seize_flight_authority(token) -> bool:
    """flight_authority_grab —— 抢夺飞行控制权，飞控类指令的前置条件"""
    url = f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/authority/flight"
    resp = requests.post(url, headers={"x-auth-token": token}, timeout=15)
    result = resp.json()
    if result.get("code") == 0:
        print("[✓] 已抢夺飞行控制权 (flight_authority_grab)")
        return True
    print(f"[✗] 抢夺飞行控制权失败: {result.get('message', result)}")
    return False


class FlyToProgressWatcher:
    """订阅 events，解析 fly_to_point_progress 完整字段"""

    def __init__(self):
        self.client = mqtt.Client(client_id=f"demo08_flyto_{int(time.time())}")
        if MQTT_USERNAME:
            self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.finished = False
        self._path_printed = False

    def connect(self) -> bool:
        try:
            self.client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            self.client.loop_start()
            time.sleep(1)
            return True
        except Exception as e:
            print(f"[✗] MQTT 连接失败: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe([(EVENTS_TOPIC, 0), (SERVICES_REPLY_TOPIC, 0)])
            print(f"[✓] 已订阅 {EVENTS_TOPIC}")
        else:
            print(f"[✗] MQTT 连接失败 rc={rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
            method = payload.get("method", "")
            data = payload.get("data", {}) or {}

            if method == "flight_authority_grab":
                result = data.get("result")
                print(f"[{'✓' if result == 0 else '✗'}] flight_authority_grab 回复 result={result}")
                return

            if method == "fly_to_point_progress":
                self._print_progress(data)
        except Exception as e:
            print(f"[!] 解析异常: {e}")

    def _print_progress(self, data: dict):
        status = data.get("status", "")
        desc = FLY_TO_STATUS.get(status, status or "未知状态")
        result = data.get("result", 0)
        idx = data.get("way_point_index")
        dist = data.get("remaining_distance")
        remain_t = data.get("remaining_time")

        # 轨迹点只在首次收到时展开，后续每帧都带会刷屏
        points = data.get("planned_path_points") or []
        if points and not self._path_printed:
            self._path_printed = True
            print(f"\n[轨迹] 规划航点 {len(points)} 个")
            for i, p in enumerate(points[:3]):
                print(f"    #{i} lat={p.get('latitude')} lon={p.get('longitude')} h={p.get('height')}")
            if len(points) > 3:
                print(f"    ... 其余 {len(points) - 3} 个已省略")

        if status == "wayline_progress":
            parts = [f"航点#{idx}" if idx is not None else ""]
            if isinstance(dist, (int, float)):
                parts.append(f"剩余 {dist:.1f} m")
            if isinstance(remain_t, (int, float)):
                parts.append(f"预计 {remain_t:.1f} s")
            print(f"[飞行中] {'  '.join(p for p in parts if p)}")
            return

        flag = "✓" if status == "wayline_ok" else "✗"
        print(f"\n[{flag}] {desc}  result={result}  fly_to_id={data.get('fly_to_id', 'N/A')}")
        if status in FINAL_STATUS:
            self.finished = True

    def wait(self, timeout: int = 300):
        """阻塞等待任务进入终态"""
        print(f"[*] 等待执行结果（最长 {timeout}s，Ctrl+C 中断）...\n")
        deadline = time.time() + timeout
        try:
            while not self.finished and time.time() < deadline:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[*] 已中断监听")
            return
        if not self.finished:
            print(f"\n[!] {timeout}s 内未收到终态事件")
            print("    可能设备未上报 events，或飞行仍在继续")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()


def fly_to_point(token) -> bool:
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

    print(f"[*] 飞向坐标: lat={TARGET_LATITUDE}, lon={TARGET_LONGITUDE}, h={TARGET_HEIGHT}m, 速度={MAX_SPEED}m/s")
    resp = requests.post(url,
                         headers={"x-auth-token": token, "Content-Type": "application/json"},
                         json=body,
                         timeout=20)
    result = resp.json()

    if result.get("code") == 0:
        print("[✓] 飞向目标点指令已下发")
        return True
    print(f"[✗] 失败: {result}")
    return False


def stop_fly_to_point(token):
    """取消飞向目标点，设备会上报 status=wayline_cancel"""
    url = f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/jobs/fly-to-point"
    resp = requests.delete(url, headers={"x-auth-token": token}, timeout=10)
    result = resp.json()
    print(f"[{'✓' if result.get('code') == 0 else '✗'}] 停止指令: {result.get('message', result)}")


if __name__ == "__main__":
    print(f"[*] 目标设备: {DOCK_SN}")
    token = get_token()

    action = input("输入 go=飞向目标点 / stop=停止 / auth=仅抢夺飞行控制权 / q=退出: ").strip()

    if action == "auth":
        seize_flight_authority(token)

    elif action == "go":
        if not seize_flight_authority(token):
            sys.exit(1)
        watcher = FlyToProgressWatcher()
        if not watcher.connect():
            sys.exit(1)
        try:
            if fly_to_point(token):
                watcher.wait()
        finally:
            watcher.disconnect()

    elif action == "stop":
        watcher = FlyToProgressWatcher()
        watcher.connect()
        try:
            stop_fly_to_point(token)
            time.sleep(3)
        finally:
            watcher.disconnect()
