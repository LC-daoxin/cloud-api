"""
demo_12_drc.py —— DRC 指令飞行控制模式

流程：
  1. drc/connect  → 获取 DRC 专用 MQTT 凭证（broker地址/账号/token）
  2. drc/enter    → 让设备进入 DRC 模式，返回 pub/sub Topic
     pub = thing/product/{sn}/drc/down（云→机）
     sub = thing/product/{sn}/drc/up  （机→云）
  3. 通过 MQTT 向 pubTopic 发送飞行控制/急停/紧急降落/心跳指令
  4. drc/exit     → 退出 DRC 模式

DRC 下行指令（thing/product/{sn}/drc/down）：
  | method                | data                          | 说明                        |
  |-----------------------|-------------------------------|-----------------------------|
  | heart_beat            | {seq, timestamp}              | 心跳，必须 1 秒一次         |
  | drone_control         | {seq, x, y, h, w}             | 摇杆飞行控制                |
  | drone_emergency_stop  | {}                            | 急停（立即刹停并悬停）      |
  | drc_emergency_landing | {}                            | 紧急降落（避障+识别二维码） |
  | drc_force_landing     | {}                            | 强制降落（忽略障碍物）      |

DRC 上行消息（thing/product/{sn}/drc/up）：
  | method        | 说明                                              |
  |---------------|---------------------------------------------------|
  | heart_beat    | 原样回显下发的 timestamp，差值即往返时延（ping）   |
  | hsi_info_push | 避障信息，上下左右前后共 16 路雷达距离（hsi）      |

事件通知（thing/product/{sn}/events）：
  joystick_invalid_notify —— Joystick 失效，drone_control 不再生效，无法手动操控
  reason: 0=遥控器失联 1=低电量返航 2=低电量降落 3=靠近限飞区 4=遥控器夺权

前提：
  - 无人机已在空中（elevation > 0），已获取飞行控制权
  - paho-mqtt 已安装：pip install paho-mqtt

运行：
    python3 demo_12_drc.py
"""
import sys
import json
import time
import uuid
import threading
import requests
import paho.mqtt.client as mqtt
from config import (BASE_URL, WEB_USERNAME, WEB_PASSWORD, WEB_FLAG, DOCK_SN, WORKSPACE_ID,
                    MQTT_HOST, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD)


def get_token():
    resp = requests.post(f"{BASE_URL}/manage/api/v1/login",
                         json={"username": WEB_USERNAME, "password": WEB_PASSWORD, "flag": WEB_FLAG},
                         timeout=10)
    return resp.json()["data"]["access_token"]


# joystick_invalid_notify 的 reason 取值
JOYSTICK_INVALID_REASON = {
    0: "遥控器失联",
    1: "低电量返航",
    2: "低电量降落",
    3: "靠近限飞区",
    4: "遥控器夺权（如 B 控触发返航）",
}


def start_side_watcher():
    """
    连主 MQTT Broker 旁路监听两个 Topic：

      thing/product/{sn}/services_reply
        drc_emergency_landing / drc_force_landing 的执行结果走这里返回，
        而不是 drc/up，因此需要一条独立连接
        （DRC 专用连接的 ACL 只放行 drc/up 和 drc/down）。

      thing/product/{sn}/events
        joystick_invalid_notify —— Joystick 失效通知。
        一旦收到，drone_control 将不再生效，无法手动操控。

    注意：events 消息带 need_reply=1，由服务端负责回 events_reply，
    本脚本只旁路观察，不要重复回复。
    """
    reply_topic = f"thing/product/{DOCK_SN}/services_reply"
    events_topic = f"thing/product/{DOCK_SN}/events"

    def _on_connect(client, userdata, flags, rc):
        if rc == 0:
            client.subscribe([(reply_topic, 0), (events_topic, 0)])
            print(f"[✓] 已订阅回复 Topic: {reply_topic}")
            print(f"[✓] 已订阅事件 Topic: {events_topic}")
        else:
            print(f"[!] 旁路监听连接失败 rc={rc}（不影响指令下发）")

    def _on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
            method = payload.get("method", "")
            data = payload.get("data", {}) or {}

            if method == "joystick_invalid_notify":
                reason = data.get("reason")
                desc = JOYSTICK_INVALID_REASON.get(reason, "未知原因")
                print(f"\n[!!] Joystick 已失效: reason={reason} {desc}")
                print("     drone_control 不再生效，手动操控不可用。")
                print("     处理完原因后需重新 drc/enter 才能恢复。")
                return

            result = data.get("result")
            flag = "✓" if result == 0 else "✗"
            print(f"\n[{flag}] services_reply {method} result={result}")
        except Exception:
            pass

    client = mqtt.Client(client_id=f"demo12_watch_{int(time.time())}")
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = _on_connect
    client.on_message = _on_message
    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        client.loop_start()
        return client
    except Exception as e:
        print(f"[!] 旁路监听启动失败: {e}（不影响指令下发）")
        return None


def drc_connect(token) -> dict:
    """步骤1：获取 DRC 专用 MQTT 连接凭证"""
    body = {"client_id": "", "expire_sec": 3600}
    resp = requests.post(
        f"{BASE_URL}/control/api/v1/workspaces/{WORKSPACE_ID}/drc/connect",
        headers={"x-auth-token": token, "Content-Type": "application/json"},
        json=body,
        timeout=10)
    result = resp.json()
    if result.get("code") != 0:
        print(f"[✗] DRC 连接凭证获取失败: {result}")
        return {}
    broker = result["data"]
    print(f"[✓] DRC MQTT 凭证获取成功")
    print(f"    broker  : {broker.get('address')}")
    print(f"    clientId: {broker.get('client_id')}")
    return broker


def drc_enter(token, client_id: str) -> dict:
    """步骤2：让设备进入 DRC 模式，获取 pub/sub Topic"""
    body = {"dock_sn": DOCK_SN, "client_id": client_id}
    resp = requests.post(
        f"{BASE_URL}/control/api/v1/workspaces/{WORKSPACE_ID}/drc/enter",
        headers={"x-auth-token": token, "Content-Type": "application/json"},
        json=body,
        timeout=20)
    result = resp.json()
    if result.get("code") != 0:
        print(f"[✗] 进入 DRC 模式失败: {result}")
        return {}
    acl = result["data"]
    print(f"[✓] 已进入 DRC 模式")
    print(f"    pubTopic: {acl.get('pub', [])}")
    print(f"    subTopic: {acl.get('sub', [])}")
    return acl


def drc_exit(token, client_id: str):
    """步骤4：退出 DRC 模式"""
    body = {"dock_sn": DOCK_SN, "client_id": client_id}
    resp = requests.post(
        f"{BASE_URL}/control/api/v1/workspaces/{WORKSPACE_ID}/drc/exit",
        headers={"x-auth-token": token, "Content-Type": "application/json"},
        json=body,
        timeout=15)
    result = resp.json()
    print(f"[{'✓' if result.get('code')==0 else '✗'}] 退出 DRC 模式: {result.get('message','')}")


def build_drc_msg(method: str, data: dict = None) -> str:
    """构造 DRC MQTT 消息"""
    msg = {
        "tid": str(uuid.uuid4()).replace("-", "")[:16],
        "bid": str(uuid.uuid4()).replace("-", "")[:16],
        "timestamp": int(time.time() * 1000),
        "method": method,
        "data": data or {}
    }
    return json.dumps(msg)


class DrcSession:
    """封装 DRC MQTT 连接和基础控制指令"""

    HSI_WARN_MM = 5000       # 障碍物近于此距离时告警（毫米）
    HSI_WARN_INTERVAL = 2.0  # 告警限频，避免刷屏（秒）

    def __init__(self, broker: dict, acl: dict):
        self.broker = broker
        self.pub_topic = acl.get("pub", [[]])[0] if acl.get("pub") else None
        self.sub_topic = acl.get("sub", [[]])[0] if acl.get("sub") else None
        self.client = None
        self._running = True
        self._seq = 0
        self.last_hsi = {}       # 最近一次 hsi_info_push 完整数据
        self.last_rtt_ms = None  # 最近一次心跳往返时延
        self._last_hsi_warn = 0.0

    def next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def connect(self) -> bool:
        addr = self.broker.get("address", "")  # 格式: tcp://host:port 或 ws://...
        # 解析地址
        addr = addr.replace("tcp://", "").replace("ws://", "")
        host, port = addr.rsplit(":", 1)
        port = int(port.split("/")[0])

        client_id = self.broker.get("client_id", f"drc_{int(time.time())}")
        username = self.broker.get("username", "")
        password = self.broker.get("password", "")  # JWT token

        self.client = mqtt.Client(client_id=client_id)
        if username:
            self.client.username_pw_set(username, password)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        try:
            self.client.connect(host, port, keepalive=30)
            self.client.loop_start()
            time.sleep(1)
            return True
        except Exception as e:
            print(f"[✗] DRC MQTT 连接失败: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[✓] DRC MQTT 已连接")
            if self.sub_topic:
                client.subscribe(self.sub_topic)
                print(f"    已订阅: {self.sub_topic}")
        else:
            print(f"[✗] DRC MQTT 连接失败 rc={rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
            method = payload.get("method", "")
            data = payload.get("data", {}) or {}

            if method == "heart_beat":
                # 设备原样回显下发时的 timestamp，差值即为往返时延
                sent = data.get("timestamp")
                if isinstance(sent, (int, float)):
                    self.last_rtt_ms = int(time.time() * 1000) - int(sent)
                return

            if method == "hsi_info_push":
                self._handle_hsi(data)
                return

            print(f"[DRC↑] {method}: {json.dumps(data, ensure_ascii=False)}")
        except Exception:
            pass

    def _handle_hsi(self, data: dict):
        """避障信息上报：频率很高，只缓存快照，逼近障碍物时才限频告警"""
        self.last_hsi = data
        if not data.get("radar_enable"):
            return
        nearest = min((v for v in self._hsi_distances(data).values() if v > 0), default=None)
        if nearest is None or nearest >= self.HSI_WARN_MM:
            return
        now = time.time()
        if now - self._last_hsi_warn < self.HSI_WARN_INTERVAL:
            return
        self._last_hsi_warn = now
        print(f"\n[避障] 最近障碍物 {nearest / 1000:.2f} m，输入 hsi 查看各方向详情")

    @staticmethod
    def _hsi_distances(data: dict) -> dict:
        """取出所有 *_distance 字段（单位毫米）"""
        return {k: v for k, v in data.items()
                if k.endswith("_distance") and isinstance(v, (int, float))}

    def print_hsi(self):
        """打印最近一次避障快照，按方向分组"""
        if not self.last_hsi:
            print("  尚未收到 hsi_info_push（设备未上报或未进入 DRC 模式）")
            return
        d = self.last_hsi
        print(f"\n避障信息（radar_enable={'开' if d.get('radar_enable') else '关'}，单位米）")
        groups = [
            ("前 front", ["front1_distance", "front2_distance", "front3_distance", "front4_distance"]),
            ("后 rear",  ["rear1_distance", "rear2_distance", "rear3_distance", "rear4_distance"]),
            ("左 left",  ["left1_distance", "left2_distance", "left3_distance"]),
            ("右 right", ["right1_distance", "right2_distance", "right3_distance"]),
            ("上 up",    ["up_distance"]),
            ("下 down",  ["down_distance"]),
        ]
        for label, keys in groups:
            vals = [f"{d.get(k, 0) / 1000:.2f}" for k in keys if k in d]
            print(f"  {label:10s} {'  '.join(vals) if vals else '无数据'}")
        print()

    def publish(self, method: str, data: dict = None):
        if not self.pub_topic:
            print("[!] 无 pub topic")
            return
        payload = build_drc_msg(method, data)
        self.client.publish(self.pub_topic, payload)
        print(f"[DRC↓] 发送 {method}")

    def heartbeat(self):
        """发送心跳（每 1 秒一次，保持 DRC 连接）"""
        self.publish("heart_beat", {
            "seq": self.next_seq(),
            "timestamp": int(time.time() * 1000),
        })

    def emergency_stop(self):
        """急停：无人机立即刹停并原地悬停，不降落"""
        self.publish("drone_emergency_stop", {})
        print("[!] 已发送急停指令 drone_emergency_stop（原地悬停）")

    def emergency_landing(self):
        """
        紧急降落 drc_emergency_landing
        会自动避障，并识别二维码降落点后降落。
        注意：不要与 drc_force_landing 混用。
        """
        self.publish("drc_emergency_landing", {})
        print("[!] 已发送紧急降落指令 drc_emergency_landing（避障 + 二维码识别降落）")
        print("    回复将出现在 thing/product/{sn}/services_reply，result=0 表示成功")

    def force_landing(self):
        """
        强制降落 drc_force_landing
        不考虑障碍物，原地直接下降。
        注意：不要与 drc_emergency_landing 混用。
        """
        self.publish("drc_force_landing", {})
        print("[!] 已发送强制降落指令 drc_force_landing（忽略障碍物，直接下降）")
        print("    回复将出现在 thing/product/{sn}/services_reply，result=0 表示成功")

    def joystick(self, x: float = 0, y: float = 0, h: float = 0, w: float = 0):
        """
        飞行控制摇杆 drone_control
        x: 前后速度 m/s，范围 -17 ~ 17（正=前，负=后）
        y: 左右速度 m/s，范围 -17 ~ 17（正=右，负=左）
        h: 升降速度 m/s，范围 -4  ~ 5 （正=上，负=下）
        w: 偏航角速度 度/s，范围 -90 ~ 90（正=顺时针，负=逆时针）
        """
        self.publish("drone_control", {
            "seq": self.next_seq(),
            "x": x, "y": y, "h": h, "w": w,
        })

    def start_heartbeat_loop(self):
        """后台线程每秒发送心跳"""
        def _loop():
            while self._running:
                self.heartbeat()
                time.sleep(1)
        t = threading.Thread(target=_loop, daemon=True)
        t.start()

    def disconnect(self):
        self._running = False
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()


if __name__ == "__main__":
    print(f"[*] 设备 SN: {DOCK_SN}")
    print(f"[*] Workspace: {WORKSPACE_ID}\n")
    if DOCK_SN == "YOUR_DOCK_SN":
        print("[✗] 请先在 config.py 中设置 DOCK_SN，运行 demo_02_devices.py 可查看设备 SN")
        sys.exit(1)
    print("[!] 警告：DRC 模式会让无人机进入云端直接飞行控制，确认无人机已在空中后继续\n")

    token = get_token()

    # 步骤 1：获取 DRC MQTT 凭证
    broker = drc_connect(token)
    if not broker:
        sys.exit(1)

    client_id = broker.get("client_id", "")

    # 步骤 2：设备进入 DRC 模式
    acl = drc_enter(token, client_id)
    if not acl:
        sys.exit(1)

    # 步骤 3：连接 DRC MQTT 并发送指令
    session = DrcSession(broker, acl)
    if not session.connect():
        sys.exit(1)

    # 后台自动发送心跳（必须保持连接不断）
    session.start_heartbeat_loop()

    # 旁路监听 services_reply（降落指令结果）和 events（Joystick 失效通知）
    watch_client = start_side_watcher()

    print("\nDRC 飞行指令（速度单位 m/s，偏航单位 度/s）：")
    print("  fwd <n>   → 前进 n     （x=n，   -17~17）")
    print("  back <n>  → 后退 n     （x=-n，  -17~17）")
    print("  right <n> → 向右 n     （y=n，   -17~17）")
    print("  left <n>  → 向左 n     （y=-n，  -17~17）")
    print("  up <n>    → 上升 n     （h=n，    -4~5）")
    print("  down <n>  → 下降 n     （h=-n，   -4~5）")
    print("  yaw <n>   → 偏航 n     （w=n，  -90~90）")
    print("  hover     → 悬停（全零）")
    print("\n应急指令（互斥，请勿混用降落类指令）：")
    print("  stop      → 急停       drone_emergency_stop  原地刹停悬停，不降落")
    print("  land      → 紧急降落   drc_emergency_landing 会避障并识别二维码降落")
    print("  fland     → 强制降落   drc_force_landing     不考虑障碍物直接下降")
    print("\n状态查询：")
    print("  hsi       → 查看最近一次避障信息 hsi_info_push（六向障碍物距离）")
    print("  ping      → 查看心跳往返时延")
    print("\n  q         → 退出 DRC 模式\n")

    try:
        while True:
            cmd = input("DRC指令: ").strip().lower().split()
            if not cmd:
                continue
            action = cmd[0]
            val = float(cmd[1]) if len(cmd) > 1 else 3

            if action == "q":
                break
            elif action == "hsi":
                session.print_hsi()
            elif action == "ping":
                rtt = session.last_rtt_ms
                print(f"  心跳往返时延: {rtt} ms" if rtt is not None else "  尚未收到心跳回包")
            elif action == "stop":
                session.emergency_stop()
            elif action == "land":
                if input("  [!] 确认紧急降落（避障+二维码识别）？输入 YES: ").strip() == "YES":
                    session.emergency_landing()
            elif action == "fland":
                if input("  [!!] 确认强制降落（忽略障碍物）？输入 YES: ").strip() == "YES":
                    session.force_landing()
            elif action == "hover":
                session.joystick()
            elif action == "up":
                session.joystick(h=val)
            elif action == "down":
                session.joystick(h=-val)
            elif action == "fwd":
                session.joystick(x=val)
            elif action == "back":
                session.joystick(x=-val)
            elif action == "left":
                session.joystick(y=-val)
            elif action == "right":
                session.joystick(y=val)
            elif action == "yaw":
                session.joystick(w=val)
            else:
                print("  未知指令")
    finally:
        session.disconnect()
        if watch_client:
            watch_client.loop_stop()
            watch_client.disconnect()
        drc_exit(token, client_id)
