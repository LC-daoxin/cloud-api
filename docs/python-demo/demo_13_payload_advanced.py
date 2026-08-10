"""
demo_13_payload_advanced.py —— 高级负载控制

包含以下指令（部分指令需要 YOOX Cloud GCS 版本，已标注）：
  camera_screen_drag    ← 画面拖动控制（云台连续转速）[YOOX扩展]
  camera_focal_length_drag ← 连续变焦                [YOOX扩展]
  camera_look_at        ← Look At（GPS 坐标指向）     [YOOX扩展]
  photo_storage_set     ← 照片存储镜头设置             [YOOX扩展]
  video_storage_set     ← 视频存储镜头设置             [YOOX扩展]

Cloud-API 版已支持的指令（无需 YOOX）：
  camera_mode_switch / camera_photo_take / camera_focal_length_set 见 demo_05/07

运行：
    python3 demo_13_payload_advanced.py

注意：本 demo 针对 YOOX Cloud GCS 项目。
      如果当前运行的是原版 Cloud-API，标注 [YOOX] 的指令会返回 404 或方法未找到错误。
"""
import sys
import requests
from config import BASE_URL, WEB_USERNAME, WEB_PASSWORD, WEB_FLAG, DOCK_SN, PAYLOAD_INDEX


def get_token():
    resp = requests.post(f"{BASE_URL}/manage/api/v1/login",
                         json={"username": WEB_USERNAME, "password": WEB_PASSWORD, "flag": WEB_FLAG},
                         timeout=10)
    return resp.json()["data"]["access_token"]


def seize_payload_authority(token):
    url = f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/authority/payload"
    resp = requests.post(url, headers={"x-auth-token": token},
                         json={"payload_index": PAYLOAD_INDEX}, timeout=10)
    result = resp.json()
    if result.get("code") != 0:
        print(f"[✗] 抢占负载控制权失败: {result.get('message','')}")
        sys.exit(1)
    print("[✓] 已获取负载控制权")


def send_payload_cmd(token, cmd: str, extra: dict = None) -> dict:
    url = f"{BASE_URL}/control/api/v1/devices/{DOCK_SN}/payload/commands"
    data = {"payload_index": PAYLOAD_INDEX}
    if extra:
        data.update(extra)
    body = {"cmd": cmd, "data": data}
    resp = requests.post(url,
                         headers={"x-auth-token": token, "Content-Type": "application/json"},
                         json=body, timeout=15)
    result = resp.json()
    ok = result.get("code") == 0
    print(f"[{'✓' if ok else '✗'}] {cmd}: {result.get('message', '')}")
    return result


def camera_screen_drag(token, pitch_speed: float, yaw_speed: float,
                       locked: bool = False):
    """
    [YOOX扩展] 画面拖动控制（云台连续转速）
    pitch_speed: 俯仰速度 -1.0~1.0（正=向下，负=向上）
    yaw_speed:   偏航速度 -1.0~1.0（正=向右，负=向左）
    locked: True=锁定目标跟踪
    """
    return send_payload_cmd(token, "camera_screen_drag", {
        "pitch_speed": pitch_speed,
        "yaw_speed": yaw_speed,
        "locked": locked
    })


def camera_focal_length_drag(token, zoom_type: int, camera_type: str = "zoom"):
    """
    [YOOX扩展] 连续变焦
    zoom_type: 0=停止变焦  1=放大（拉近）  2=缩小（拉远）
    camera_type: zoom / wide / ir
    """
    return send_payload_cmd(token, "camera_focal_length_drag", {
        "zoom_type": zoom_type,
        "camera_type": camera_type
    })


def camera_look_at(token, latitude: float, longitude: float, height: float):
    """
    [YOOX扩展] Look At —— 云台指向 GPS 坐标对应的方向
    latitude:  -90 ~ 90
    longitude: -180 ~ 180
    height:    2 ~ 10000 (米)
    """
    return send_payload_cmd(token, "camera_look_at", {
        "locked": True,
        "latitude": latitude,
        "longitude": longitude,
        "height": height
    })


def photo_storage_set(token, lenses: list):
    """
    [YOOX扩展] 照片存储镜头设置
    lenses: 列表，可选值 current / zoom / wide / ir / NightVision
    示例: ["zoom", "wide"]
    """
    return send_payload_cmd(token, "photo_storage_set", {
        "photo_storage_settings": lenses
    })


def video_storage_set(token, lenses: list):
    """
    [YOOX扩展] 视频存储镜头设置
    lenses: 列表，可选值同上
    """
    return send_payload_cmd(token, "video_storage_set", {
        "video_storage_settings": lenses
    })


if __name__ == "__main__":
    print(f"[*] 目标设备: {DOCK_SN}")
    print(f"[*] 负载索引: {PAYLOAD_INDEX}")
    if DOCK_SN == "YOUR_DOCK_SN":
        print("[✗] 请先在 config.py 中设置 DOCK_SN")
        sys.exit(1)
    print("[!] 注意：标注[YOOX]的指令需要 YOOX Cloud GCS 版本，原版 Cloud-API 不支持\n")

    token = get_token()
    seize_payload_authority(token)

    print("""高级负载控制菜单：
  1. [YOOX] 画面拖动 - 云台向上（pitch=-0.5）
  2. [YOOX] 画面拖动 - 云台向下（pitch=+0.5）
  3. [YOOX] 画面拖动 - 云台向左（yaw=-0.5）
  4. [YOOX] 画面拖动 - 云台向右（yaw=+0.5）
  5. [YOOX] 画面拖动 - 停止（pitch=0, yaw=0）
  6. [YOOX] 连续变焦 - 放大
  7. [YOOX] 连续变焦 - 缩小
  8. [YOOX] 连续变焦 - 停止
  9. [YOOX] Look At   - 输入GPS坐标
  A. [YOOX] 照片存储设置 - zoom+wide
  B. [YOOX] 视频存储设置 - zoom+wide
  q. 退出\n""")

    while True:
        cmd = input("选择操作: ").strip().upper()
        if cmd == "Q":
            break
        elif cmd == "1":
            camera_screen_drag(token, pitch_speed=-0.5, yaw_speed=0)
        elif cmd == "2":
            camera_screen_drag(token, pitch_speed=0.5, yaw_speed=0)
        elif cmd == "3":
            camera_screen_drag(token, pitch_speed=0, yaw_speed=-0.5)
        elif cmd == "4":
            camera_screen_drag(token, pitch_speed=0, yaw_speed=0.5)
        elif cmd == "5":
            camera_screen_drag(token, pitch_speed=0, yaw_speed=0)
        elif cmd == "6":
            camera_focal_length_drag(token, zoom_type=1)
        elif cmd == "7":
            camera_focal_length_drag(token, zoom_type=2)
        elif cmd == "8":
            camera_focal_length_drag(token, zoom_type=0)
        elif cmd == "9":
            lat = float(input("  纬度 (-90~90): "))
            lon = float(input("  经度 (-180~180): "))
            h   = float(input("  高度 (2~10000 米): "))
            camera_look_at(token, lat, lon, h)
        elif cmd == "A":
            photo_storage_set(token, ["zoom", "wide"])
        elif cmd == "B":
            video_storage_set(token, ["zoom", "wide"])
        else:
            print("  未知操作")
