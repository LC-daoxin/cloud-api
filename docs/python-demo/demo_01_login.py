"""
demo_01_login.py -- 登录并获取 access_token

运行：
    python3 demo_01_login.py

分别用 Web 端（admin）和 Pilot/App 端（pilot）账号登录，
打印各自的 token 和接入配置信息。
"""
import requests
from config import BASE_URL, WEB_USERNAME, WEB_PASSWORD, WEB_FLAG, \
    PILOT_USERNAME, PILOT_PASSWORD, PILOT_FLAG, SERVER_IP, SERVER_PORT


def login(username, password, flag, label):
    url = f"{BASE_URL}/manage/api/v1/login"
    payload = {"username": username, "password": password, "flag": flag}

    print(f"\n{'='*60}")
    print(f"[*] {label}")
    print(f"    登录地址: {url}")
    print(f"    账号: {username} (flag={flag})")

    resp = requests.post(url, json=payload, timeout=10)
    data = resp.json()

    if data.get("code") != 0:
        print(f"    [✗] 登录失败: {data.get('message', data)}")
        return None

    d = data["data"]
    token = d["access_token"]
    mqtt_addr = d.get("mqtt_addr", "")

    print(f"    [✓] 登录成功")
    print(f"    token        : {token[:40]}...")
    print(f"    workspace_id : {d['workspace_id']}")
    print(f"    mqtt_addr    : {mqtt_addr}")

    if flag == 1:
        # Web 端配置
        print(f"\n    [Web 端 API 调用配置]")
        print(f"      HTTP 请求头 : x-auth-token: {token[:30]}...")
        print(f"      WebSocket   : ws://{SERVER_IP}:{SERVER_PORT}/api/v1/ws?x-auth-token=<token>")
        print(f"      用途        : curl / Python demo / Web 前端")
    else:
        # Pilot/App 端配置 -- App 配置页直接照抄
        print(f"\n    [Pilot/App 端配置 -- App 配置页直接照抄]")
        print(f"      登录地址     : http://{SERVER_IP}:{SERVER_PORT}/manage/api/v1/login")
        print(f"      账号         : {username}")
        print(f"      密码         : {password}")
        print(f"      MQTT 地址    : mqtt://{SERVER_IP}:1883")
        print(f"      MQTT 账号    : {d.get('mqtt_username', username)}")
        print(f"      MQTT 密码    : {d.get('mqtt_password', password)}")
        print(f"      WebSocket    : ws://{SERVER_IP}:{SERVER_PORT}/api/v1/ws")
        print(f"      (WebSocket 不用手填 token，App 登录后自动追加)")

    return token


if __name__ == "__main__":
    # Web 端（admin）-- 用于 API 调试和 Python demo
    web_token = login(WEB_USERNAME, WEB_PASSWORD, WEB_FLAG, "Web 端登录 (admin)")

    # Pilot/App 端（pilot）-- 用于 Autel Pilot App 接入
    pilot_token = login(PILOT_USERNAME, PILOT_PASSWORD, PILOT_FLAG, "Pilot/App 端登录 (pilot)")

    print(f"\n{'='*60}")
    if web_token:
        print(f"[✓] Web 端登录成功，token 可用于 demo_05 ~ demo_14")
    if pilot_token:
        print(f"[✓] Pilot/App 端登录成功，配置信息可填入 Pilot App")
