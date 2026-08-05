"""
demo_11_drc.py —— DRC 指令飞行控制模式

流程：
  1. drc/connect  → 获取 DRC 专用 MQTT 凭证（broker地址/账号/token）
  2. drc/enter    → 让设备进入 DRC 模式，返回 pub/sub Topic
  3. 通过 MQTT 向 pubTopic 发送飞行控制/急停/心跳指令
  4. drc/exit     → 退出 DRC 模式

前提：
  - 无人机已在空中（elevation > 0），已获取飞行控制权
  - paho-mqtt 已安装：pip install paho-mqtt

运行：
    python3 demo_11_drc.py
"""
import sys
import json
import time
import uuid
import threading
import requests
import paho.mqtt.client as mqtt
from config import BASE_URL, WEB_USERNAME, WEB_PASSWORD, WEB_FLAG, DOCK_SN, WORKSPACE_ID


def get_token():
    resp = requests.post(f"{BASE_URL}/manage/api/v1/login",
                         json={"username": WEB_USERNAME, "password": WEB_PASSWORD, "flag": WEB_FLAG},
                         timeout=10)
    return resp.json()["data"]["access_token"]


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

    def __init__(self, broker: dict, acl: dict):
        self.broker = broker
        self.pub_topic = acl.get("pub", [[]])[0] if acl.get("pub") else None
        self.sub_topic = acl.get("sub", [[]])[0] if acl.get("sub") else None
        self.client = None
        self._running = True

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
            data = json.loads(msg.payload)
            method = data.get("method", "")
            print(f"[DRC↑] {method}: {json.dumps(data.get('data', {}), ensure_ascii=False)}")
        except Exception:
            pass

    def publish(self, method: str, data: dict = None):
        if not self.pub_topic:
            print("[!] 无 pub topic")
            return
        payload = build_drc_msg(method, data)
        self.client.publish(self.pub_topic, payload)
        print(f"[DRC↓] 发送 {method}")

    def heartbeat(self):
        """发送心跳（每 1 秒一次，保持 DRC 连接）"""
        self.publish("heart_beat", {"seq": int(time.time())})

    def emergency_stop(self):
        """无人机急停"""
        self.publish("drone_emergency_stop")
        print("[!] 已发送急停指令")

    def joystick(self, x: float = 0, y: float = 0, z: float = 0, w: float = 0):
        """
        飞行控制摇杆
        x: 横向（正=右，负=左）
        y: 纵向（正=前，负=后）
        z: 升降（正=上，负=下）
        w: 偏航（正=顺时针，负=逆时针）
        范围均为 -100 ~ 100
        """
        self.publish("joystick_action", {
            "action": {"x": x, "y": y, "z": z, "w": w}
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
    print(f"[*] 机巢 SN: {DOCK_SN}")
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

    print("\nDRC 指令（摇杆值范围 -100 ~ 100）：")
    print("  stop      → 急停")
    print("  up <n>    → 上升 n（z=n）")
    print("  down <n>  → 下降 n（z=-n）")
    print("  fwd <n>   → 前进 n（y=n）")
    print("  back <n>  → 后退 n（y=-n）")
    print("  left <n>  → 向左 n（x=-n）")
    print("  right <n> → 向右 n（x=n）")
    print("  yaw <n>   → 偏航 n（w=n）")
    print("  hover     → 悬停（全零）")
    print("  q         → 退出 DRC 模式\n")

    try:
        while True:
            cmd = input("DRC指令: ").strip().lower().split()
            if not cmd:
                continue
            action = cmd[0]
            val = float(cmd[1]) if len(cmd) > 1 else 30

            if action == "q":
                break
            elif action == "stop":
                session.emergency_stop()
            elif action == "hover":
                session.joystick()
            elif action == "up":
                session.joystick(z=val)
            elif action == "down":
                session.joystick(z=-val)
            elif action == "fwd":
                session.joystick(y=val)
            elif action == "back":
                session.joystick(y=-val)
            elif action == "left":
                session.joystick(x=-val)
            elif action == "right":
                session.joystick(x=val)
            elif action == "yaw":
                session.joystick(w=val)
            else:
                print("  未知指令")
    finally:
        session.disconnect()
        drc_exit(token, client_id)
