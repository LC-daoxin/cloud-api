"""
demo_16_look_at.py -- 负载控制 Look At（云台对准指定 GPS 目标点）

完整流程：
  1. payload_authority_grab  抢夺负载控制权（Look At 的前置条件）
     POST /control/api/v1/devices/{sn}/authority/payload  body={"payload_index": ...}
  2. camera_look_at          让云台/相机对准目标经纬高
     POST /control/api/v1/devices/{sn}/payload/commands
     body={"cmd": "camera_look_at", "data": {payload_index, locked, latitude, longitude, height}}

指令下行报文（服务端拼装后发往设备）：
  Topic : thing/product/{gateway_sn}/services    Direction: down
  Method: camera_look_at
  Data  : { payload_index, locked, latitude, longitude, height }  # height 为椭球高

  | 字段      | 说明                                   |
  |-----------|----------------------------------------|
  | payload_index | 相机负载索引，例如 53-0-0         |
  | locked    | true=机身与云台一起转向，false=仅云台转动 |
  | latitude  | 目标点纬度，-90~90，精度小数点后 6 位   |
  | longitude | 目标点经度，-180~180，精度小数点后 6 位 |
  | height    | 目标点高度（椭球高），2~10000 m         |

【RC 网关注意】遥控器（REMOTER_CONTROL 域）把无人机作为子设备管理，服务端会自动
补上 device_list 显式寻址无人机 SN，否则遥控器会静默丢弃指令、永不回复，
云端表现为 211001「No message reply received.」超时。此逻辑已在 cloud-service
的 payloadCommands 中按网关域自动分流，demo 无需关心。

前提：无人机已在空中、负载在线，config.py 中的 PAYLOAD_INDEX 为实际相机枚举值。

运行：
    python3 demo_16_look_at.py                       # 使用脚本内默认目标点
    python3 demo_16_look_at.py 22.5431 113.9213 50   # 纬度 经度 高度(米)
"""
import sys
import requests
from config import (BASE_URL, WEB_USERNAME, WEB_PASSWORD, WEB_FLAG,
                    DOCK_SN, PAYLOAD_INDEX)

if DOCK_SN == "YOUR_DOCK_SN":
    print("[✗] 请先在 config.py 中设置 DOCK_SN")
    sys.exit(1)

# ── 默认目标坐标（可用命令行参数覆盖）──
TARGET_LATITUDE = 22.5431
TARGET_LONGITUDE = 113.9213
TARGET_HEIGHT = 50.0   # 椭球高，单位米


def get_token():
    resp = requests.post(f"{BASE_URL}/manage/api/v1/login",
                         json={"username": WEB_USERNAME, "password": WEB_PASSWORD, "flag": WEB_FLAG},
                         timeout=10)
    return resp.json()["data"]["access_token"]


def seize_payload_authority(token) -> bool:
    """payload_authority_grab —— Look At / 变焦 / 拍录等负载指令的前置条件"""
    url = f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/authority/payload"
    resp = requests.post(url,
                         headers={"x-auth-token": token},
                         json={"payload_index": PAYLOAD_INDEX},
                         timeout=15)
    result = resp.json()
    if result.get("code") == 0:
        print(f"[✓] 已抢夺负载控制权 (payload_authority_grab) 负载={PAYLOAD_INDEX}")
        return True
    print(f"[✗] 抢夺负载控制权失败: {result.get('message', result)}")
    return False


def camera_look_at(token, latitude: float, longitude: float, height: float) -> bool:
    url = f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/payload/commands"
    body = {
        "cmd": "camera_look_at",
        "data": {
            "payload_index": PAYLOAD_INDEX,
            "locked": True,
            "latitude": round(latitude, 6),
            "longitude": round(longitude, 6),
            "height": round(height, 1),
        },
    }
    print(f"[*] 发送 camera_look_at → ({latitude}, {longitude}, {height} m)")
    resp = requests.post(url,
                         headers={"x-auth-token": token, "Content-Type": "application/json"},
                         json=body,
                         timeout=15)
    result = resp.json()
    ok = result.get("code") == 0
    print(f"[{'✓' if ok else '✗'}] {result.get('message', result)}")
    return ok


if __name__ == "__main__":
    if len(sys.argv) >= 4:
        TARGET_LATITUDE = float(sys.argv[1])
        TARGET_LONGITUDE = float(sys.argv[2])
        TARGET_HEIGHT = float(sys.argv[3])

    print(f"[*] 目标设备: {DOCK_SN}  负载: {PAYLOAD_INDEX}")
    token = get_token()
    if not seize_payload_authority(token):
        sys.exit(1)
    camera_look_at(token, TARGET_LATITUDE, TARGET_LONGITUDE, TARGET_HEIGHT)
