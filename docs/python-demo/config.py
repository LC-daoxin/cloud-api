"""
统一配置文件 —— 运行任何 demo 前先修改这里
"""

# ── 服务器地址 ─────────────────────────────────────────
# 将下面的 IP 改为 Mac 的局域网 IP（同一局域网内其他设备需填此地址）
SERVER_IP = "172.20.10.8"
SERVER_PORT = 9000

BASE_URL = f"http://{SERVER_IP}:{SERVER_PORT}"

# ── HTTP 登录账号 ──────────────────────────────────────
# flag=1: Web 端账号；flag=2: Pilot 遥控器账号
WEB_USERNAME = "adminPC"
WEB_PASSWORD = "adminPC"
WEB_FLAG = 1

PILOT_USERNAME = "pilot"
PILOT_PASSWORD = "pilot123"
PILOT_FLAG = 2

# ── MQTT 连接（App/Pilot 端填写）─────────────────────────
MQTT_HOST = SERVER_IP        # 同局域网填 Mac IP
MQTT_PORT = 1883             # TCP 明文
MQTT_WS_PORT = 9001          # WebSocket 协议（ws://IP:9001/mqtt）
# Mosquitto 当前允许匿名，填任意字符串即可；也可使用 SQL 中的账号
MQTT_USERNAME = "admin"      # 对应 adminPC 用户的 mqtt_username
MQTT_PASSWORD = "admin"      # 对应 adminPC 用户的 mqtt_password

# ── WebSocket 地址 ─────────────────────────────────────
# token 通过登录接口获取，填入后连接
WS_URL = f"ws://{SERVER_IP}:{SERVER_PORT}/api/v1/ws"

# ── 设备 SN（运行 demo_02_devices.py 后填入）────────────
DOCK_SN = "TH7926043417"    # 遥控器 SN，控制接口的 {sn} 路径参数
DRONE_SN = "1748FEV3HMP925511143"  # 无人机 SN

# ── 负载索引（从直播能力接口或 OSD 中获取）──────────────
# 格式：payload 的 domain-type-subtype，从 OSD cameras[].camera_index 获取
PAYLOAD_INDEX = "10806-0-0"  # 从 OSD 数据中获取的实际值

# ── 工作空间 ID（登录后从 token 解析，或查看 demo_01）──
WORKSPACE_ID = "e3dea0f5-37f2-4d79-ae58-490af3228069"  # SQL 初始化数据
