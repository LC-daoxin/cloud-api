"""
demo_15_emergency.py -- 应急处置指令（返航 / 急停 / 紧急降落 / 强制降落）

把飞行安全相关的指令集中在一个 demo 里，出事时能一键触发，不用先去翻别的脚本。

指令来源分两类：

【HTTP 通道】走 POST /control/api/v1/devices/{sn}/jobs/{method}
  - return_home         一键返航，无人机按返航高度飞回返航点
  - return_home_cancel  取消返航，无人机原地悬停

【MQTT 通道】直接下发到 thing/product/{gateway_sn}/drc/down
  - drone_emergency_stop   急停：立即刹停并原地悬停，不降落
  - drc_emergency_landing  紧急降落：会自动避障，并识别二维码降落点后降落
  - drc_force_landing      强制降落：不考虑障碍物，原地直接下降

  回复统一在 thing/product/{gateway_sn}/services_reply
  回复体 data.result == 0 表示成功，非 0 表示失败。

【重要】drc_emergency_landing 与 drc_force_landing 是两套独立逻辑，
       一次应急处置中只能选其一，不要混用，否则降落行为不可预期。

前提：
  - 无人机在空中且在线
  - MQTT 下发前，设备需已进入 DRC 模式（可先运行 demo_12_drc.py，
    或本脚本菜单里的 "e" 选项进入 DRC 模式）
  - paho-mqtt 已安装：pip install paho-mqtt

运行：
    python3 demo_15_emergency.py
"""
import sys
import json
import time
import uuid
import requests
import paho.mqtt.client as mqtt
from config import (BASE_URL, WEB_USERNAME, WEB_PASSWORD, WEB_FLAG, DOCK_SN, WORKSPACE_ID,
                    MQTT_HOST, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD)

DRC_DOWN_TOPIC = f"thing/product/{DOCK_SN}/drc/down"
SERVICES_REPLY_TOPIC = f"thing/product/{DOCK_SN}/services_reply"
EVENTS_TOPIC = f"thing/product/{DOCK_SN}/events"

# joystick_invalid_notify 的 reason 取值
JOYSTICK_INVALID_REASON = {
    0: "遥控器失联",
    1: "低电量返航",
    2: "低电量降落",
    3: "靠近限飞区",
    4: "遥控器夺权（如 B 控触发返航）",
}


def get_token():
    resp = requests.post(f"{BASE_URL}/manage/api/v1/login",
                         json={"username": WEB_USERNAME, "password": WEB_PASSWORD, "flag": WEB_FLAG},
                         timeout=10)
    return resp.json()["data"]["access_token"]


# ── HTTP 通道：返航 ────────────────────────────────────────────────
def send_job(token, method: str):
    """POST /control/api/v1/devices/{sn}/jobs/{method}"""
    resp = requests.post(
        f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/jobs/{method}",
        headers={"x-auth-token": token, "Content-Type": "application/json"},
        json={},
        timeout=20)
    result = resp.json()
    ok = result.get("code") == 0
    print(f"[{'✓' if ok else '✗'}] {method}: code={result.get('code')} {result.get('message', '')}")
    return ok


# ── MQTT 通道：DRC 应急指令 ────────────────────────────────────────
class DrcDownSender:
    """直连主 MQTT Broker，向 drc/down 下发应急指令，并在 services_reply 收结果"""

    def __init__(self):
        self.client = mqtt.Client(client_id=f"demo15_emg_{int(time.time())}")
        if MQTT_USERNAME:
            self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

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
            print(f"[✓] MQTT 已连接 {MQTT_HOST}:{MQTT_PORT}")
            client.subscribe([(SERVICES_REPLY_TOPIC, 0), (EVENTS_TOPIC, 0)])
            print(f"[✓] 已订阅回复 Topic: {SERVICES_REPLY_TOPIC}")
            print(f"[✓] 已订阅事件 Topic: {EVENTS_TOPIC}")
        else:
            print(f"[✗] MQTT 连接失败 rc={rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
            method = payload.get("method", "")
            data = payload.get("data", {}) or {}

            # Joystick 失效后 drone_control 不再生效，只能靠返航/降落类指令处置
            if method == "joystick_invalid_notify":
                reason = data.get("reason")
                desc = JOYSTICK_INVALID_REASON.get(reason, "未知原因")
                print(f"\n[!!] Joystick 已失效: reason={reason} {desc}")
                print("     手动操控不可用，请改用返航 / 紧急降落 / 强制降落处置")
                return

            result = data.get("result")
            if result == 0:
                print(f"\n[✓] {method} 执行成功 (result=0)")
            else:
                print(f"\n[✗] {method} 执行失败 result={result}")
                print(f"    完整回复: {json.dumps(payload, ensure_ascii=False)}")
        except Exception as e:
            print(f"[!] 回复解析异常: {e}")

    def publish(self, method: str, data: dict = None):
        payload = json.dumps({
            "tid": str(uuid.uuid4()).replace("-", "")[:16],
            "bid": str(uuid.uuid4()).replace("-", "")[:16],
            "timestamp": int(time.time() * 1000),
            "method": method,
            "data": data if data is not None else {},
        })
        self.client.publish(DRC_DOWN_TOPIC, payload)
        print(f"[↓] {DRC_DOWN_TOPIC}  method={method}")

    def emergency_stop(self):
        """急停：立即刹停并原地悬停，不降落"""
        self.publish("drone_emergency_stop", {})

    def emergency_landing(self):
        """紧急降落：会避障，并识别二维码降落点后降落"""
        self.publish("drc_emergency_landing", {})

    def force_landing(self):
        """强制降落：不考虑障碍物，原地直接下降"""
        self.publish("drc_force_landing", {})

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()


# ── 可选：进入 / 退出 DRC 模式 ─────────────────────────────────────
def drc_enter(token) -> str:
    """让设备进入 DRC 模式，返回 client_id；MQTT 应急指令生效的前提"""
    resp = requests.post(
        f"{BASE_URL}/control/api/v1/workspaces/{WORKSPACE_ID}/drc/connect",
        headers={"x-auth-token": token, "Content-Type": "application/json"},
        json={"client_id": "", "expire_sec": 3600},
        timeout=10)
    result = resp.json()
    if result.get("code") != 0:
        print(f"[✗] DRC 凭证获取失败: {result}")
        return ""
    client_id = result["data"].get("client_id", "")

    resp = requests.post(
        f"{BASE_URL}/control/api/v1/workspaces/{WORKSPACE_ID}/drc/enter",
        headers={"x-auth-token": token, "Content-Type": "application/json"},
        json={"dock_sn": DOCK_SN, "client_id": client_id},
        timeout=20)
    result = resp.json()
    if result.get("code") != 0:
        print(f"[✗] 进入 DRC 模式失败: {result}")
        return ""
    print(f"[✓] 已进入 DRC 模式, client_id={client_id}")
    return client_id


def drc_exit(token, client_id: str):
    resp = requests.post(
        f"{BASE_URL}/control/api/v1/workspaces/{WORKSPACE_ID}/drc/exit",
        headers={"x-auth-token": token, "Content-Type": "application/json"},
        json={"dock_sn": DOCK_SN, "client_id": client_id},
        timeout=15)
    result = resp.json()
    print(f"[{'✓' if result.get('code') == 0 else '✗'}] 退出 DRC 模式: {result.get('message', '')}")


def confirm(text: str) -> bool:
    return input(f"  [!] {text} 输入 YES 确认: ").strip() == "YES"


if __name__ == "__main__":
    print(f"[*] 设备 SN: {DOCK_SN}")
    print(f"[*] Workspace: {WORKSPACE_ID}\n")
    if DOCK_SN == "YOUR_DOCK_SN":
        print("[✗] 请先在 config.py 中设置 DOCK_SN，运行 demo_02_devices.py 可查看设备 SN")
        sys.exit(1)

    print("[!] 本 demo 会真实操控飞行器，请确认现场安全后再执行\n")

    token = get_token()
    sender = DrcDownSender()
    if not sender.connect():
        sys.exit(1)

    drc_client_id = ""

    print("""
应急处置菜单：
  --- HTTP 通道（无需 DRC 模式）---
  1. 一键返航      return_home
  2. 取消返航      return_home_cancel

  --- MQTT 通道（需先进入 DRC 模式，见 e）---
  3. 急停          drone_emergency_stop   立即刹停并原地悬停，不降落
  4. 紧急降落      drc_emergency_landing  避障 + 识别二维码降落
  5. 强制降落      drc_force_landing      忽略障碍物直接下降

  --- 辅助 ---
  e. 进入 DRC 模式
  x. 退出 DRC 模式
  q. 退出

  注意：4 和 5 是两套独立逻辑，同一次处置中只能选其一，不要混用。
""")

    try:
        while True:
            cmd = input("选择操作: ").strip().lower()
            if cmd == "q":
                break
            elif cmd == "1":
                if confirm("确认一键返航？"):
                    send_job(token, "return_home")
            elif cmd == "2":
                send_job(token, "return_home_cancel")
            elif cmd == "3":
                if confirm("确认急停？无人机将立即刹停并原地悬停。"):
                    sender.emergency_stop()
            elif cmd == "4":
                if confirm("确认紧急降落？无人机将避障并识别二维码后降落。"):
                    sender.emergency_landing()
            elif cmd == "5":
                if confirm("确认强制降落？无人机将忽略障碍物直接下降！"):
                    sender.force_landing()
            elif cmd == "e":
                drc_client_id = drc_enter(token)
            elif cmd == "x":
                if drc_client_id:
                    drc_exit(token, drc_client_id)
                    drc_client_id = ""
                else:
                    print("  当前没有由本脚本建立的 DRC 会话")
            else:
                print("  未知操作")
            time.sleep(0.5)
    finally:
        if drc_client_id:
            drc_exit(token, drc_client_id)
        sender.disconnect()
        print("[*] 已断开")
