"""
demo_10_livestream.py -- 直播全流程

支持协议：
  url_type=1  RTMP
  url_type=2  RTSP  ← 常用，设备推流到服务器配置的 RTSP 地址
  url_type=3  GB28181

video_id 格式：{drone_sn}/{payload_index}/{video_type}-0
  从 MQTT OSD 的 live_status 中获取

video_quality（仅以下值有效）：
  2=标清  3=高清

video_type（镜头切换，仅 zoom / ir 有效）：
  zoom / ir

RTSP 发布/拉流地址格式（MediaMTX 动态路径）：
  rtsp://{username}:{password}@{server_ip}:{port}/{drone_sn}-{payload_index}

运行：
    python3 demo_10_livestream.py
"""
import sys
import json
import os
import shutil
import subprocess
import time
import requests
import paho.mqtt.client as mqtt
from config import BASE_URL, WEB_USERNAME, WEB_PASSWORD, WEB_FLAG, \
    SERVER_IP, MQTT_HOST, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD


# ── 直播配置 ──────────────────────────────────────────────
URL_TYPE = 2          # 1=RTMP  2=RTSP  3=GB28181
VIDEO_QUALITY = 2     # 默认标清更流畅；可在菜单中切换到 3=高清
# RTSP 服务配置（对应 application.yml 中 livestream.url.rtsp）
RTSP_USERNAME = "admin"
RTSP_PASSWORD = "admin"
RTSP_PORT = 8554
VLC_APP = "/Applications/VLC.app/Contents/MacOS/VLC"


def get_token():
    resp = requests.post(f"{BASE_URL}/manage/api/v1/login",
                         json={"username": WEB_USERNAME, "password": WEB_PASSWORD, "flag": WEB_FLAG},
                         timeout=10)
    return resp.json()["data"]["access_token"]


def get_video_ids_from_mqtt(timeout_sec=8) -> list:
    """通过 MQTT 订阅遥控器 OSD，从 live_status 中提取 video_id 列表"""
    video_ids = []
    done = [False]

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe("thing/product/+/osd")
        else:
            done[0] = True

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
            data = payload.get("data", {})
            # 遥控器 OSD 包含 live_status
            live_status = data.get("live_status")
            if live_status:
                for ls in live_status:
                    vid = ls.get("video_id")
                    vtype = ls.get("video_type", "normal")
                    if vid and vid not in video_ids:
                        video_ids.append(vid)
                        print(f"  发现视频流: {vid}  type={vtype}")
                if video_ids:
                    done[0] = True
                    client.disconnect()
        except Exception:
            pass

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id=f"demo_10_{int(time.time())}")
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
        client.loop_start()
        start = time.time()
        while not done[0] and time.time() - start < timeout_sec:
            time.sleep(0.2)
        client.loop_stop()
        client.disconnect()
    except Exception as e:
        print(f"[!] MQTT 连接失败: {e}")

    return video_ids


def build_rtsp_url(video_id: str) -> str:
    """根据 video_id 构造设备发布到 MediaMTX 的完整 RTSP 地址"""
    # video_id 格式: drone_sn/payload_index/video_type-0
    parts = video_id.split("/")
    drone_sn = parts[0] if len(parts) > 0 else "unknown"
    payload_index = parts[1] if len(parts) > 1 else "0-0-0"
    stream_name = f"{drone_sn}-{payload_index}"
    return f"rtsp://{RTSP_USERNAME}:{RTSP_PASSWORD}@{SERVER_IP}:{RTSP_PORT}/{stream_name}"


def probe_rtsp(rtsp_url: str, timeout_sec=12) -> bool:
    """用 ffprobe 确认 MediaMTX 路径已收到媒体；未安装时跳过。"""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        print("    [!] 未安装 ffprobe，跳过媒体流探测")
        return False
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-rtsp_transport", "tcp",
             "-show_entries", "stream=codec_name,width,height",
             "-of", "default=noprint_wrappers=1", rtsp_url],
            capture_output=True, text=True, timeout=timeout_sec)
        if result.returncode == 0 and result.stdout.strip():
            print("    [✓] MediaMTX 已收到视频流")
            for line in result.stdout.strip().splitlines():
                print(f"        {line}")
            return True
        detail = result.stderr.strip() or "未发现视频轨道"
        print(f"    [✗] RTSP 路径暂不可播放: {detail}")
    except subprocess.TimeoutExpired:
        print(f"    [✗] {timeout_sec} 秒内未收到 RTSP 视频数据")
    return False


def live_start(token, video_id: str, url_type: int = 2, video_quality: int = 3):
    """开始直播"""
    body = {
        "url_type": url_type,
        "video_id": video_id,
        "video_quality": video_quality,
    }
    if url_type == 2:
        # 关键：把完整 MediaMTX 发布地址下发给设备。旧实现只下发账号、
        # 密码和端口，却在客户端猜测 /live/... 路径，服务端并无该流。
        body["url"] = build_rtsp_url(video_id)
    resp = requests.post(f"{BASE_URL}/manage/api/v1/live/streams/start",
                         headers={"x-auth-token": token, "Content-Type": "application/json"},
                         json=body,
                         timeout=20)
    result = resp.json()
    if result.get("code") == 0:
        print(f"[✓] 直播已开始  video_id={video_id}")
        # 展示 RTSP 拉流地址
        if url_type == 2:
            live_data = result.get("data") or {}
            rtsp_url = live_data.get("url") or build_rtsp_url(video_id)
            print(f"    RTSP 拉流地址: {rtsp_url}")
            print(f"    可用 ffplay 播放: ffplay -rtsp_transport tcp \"{rtsp_url}\"")
            print("    VLC 低延迟播放: "
                  f"open -na VLC --args --rtsp-tcp --network-caching=150 "
                  f"--clock-synchro=0 --clock-jitter=0 \"{rtsp_url}\"")
            print("    正在等待首帧并检查实际媒体流...")
            probe_rtsp(rtsp_url)
        # 也打印接口返回的 URL（如果有）
        live_data = result.get("data") or {}
        api_url = live_data.get("url") if live_data else ""
        if api_url:
            print(f"    接口返回地址: {api_url}")
    else:
        print(f"[✗] 开始直播失败: {result.get('message','')}")
    return result


def ensure_rtsp_live(token, video_id: str) -> str | None:
    """复用现有发布流；没有流时清理设备旧状态并重新启动。"""
    rtsp_url = build_rtsp_url(video_id)
    print("[*] 检查 MediaMTX 中是否已有可复用的视频流...")
    if probe_rtsp(rtsp_url, timeout_sec=4):
        print("[✓] 已有直播流，直接复用")
        return rtsp_url

    print("[*] 清理设备可能遗留的旧直播状态...")
    live_stop(token, video_id)
    time.sleep(1)
    result = live_start(token, video_id, URL_TYPE, VIDEO_QUALITY)
    if result.get("code") != 0:
        return None

    # live_start 已做一次首帧探测；这里再次确认发布者仍在线，避免把
    # 设备的“指令成功”误报成可播放。
    return rtsp_url if probe_rtsp(rtsp_url, timeout_sec=6) else None


def open_vlc(rtsp_url: str) -> bool:
    """启动独立 VLC 实例，确保 TCP 参数不会被已有 VLC 进程忽略。"""
    if not os.path.isfile(VLC_APP):
        print(f"[✗] 未找到 VLC: {VLC_APP}")
        return False
    subprocess.Popen([VLC_APP, "--rtsp-tcp", "--network-caching=150",
                      "--clock-synchro=0", "--clock-jitter=0",
                      "--no-video-title-show", rtsp_url],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    print(f"[✓] 已启动 VLC: {rtsp_url}")
    return True


def live_stop(token, video_id: str):
    """停止直播"""
    body = {"video_id": video_id}
    resp = requests.post(f"{BASE_URL}/manage/api/v1/live/streams/stop",
                         headers={"x-auth-token": token, "Content-Type": "application/json"},
                         json=body,
                         timeout=15)
    result = resp.json()
    print(f"[{'✓' if result.get('code')==0 else '✗'}] 停止直播: {result.get('message','')}")
    return result


def live_set_quality(token, video_id: str, video_quality: int):
    """切换清晰度  仅 2=标清  3=高清 有效"""
    body = {"video_id": video_id, "video_quality": video_quality}
    resp = requests.post(f"{BASE_URL}/manage/api/v1/live/streams/update",
                         headers={"x-auth-token": token, "Content-Type": "application/json"},
                         json=body,
                         timeout=15)
    result = resp.json()
    quality_map = {2: "标清", 3: "高清"}
    print(f"[{'✓' if result.get('code')==0 else '✗'}] 切换清晰度->{quality_map.get(video_quality, video_quality)}: {result.get('message','')}")
    return result


def live_switch_lens(token, video_id: str, video_type: str):
    """切换镜头  仅 zoom / ir 有效"""
    body = {"video_id": video_id, "video_type": video_type}
    resp = requests.post(f"{BASE_URL}/manage/api/v1/live/streams/switch",
                         headers={"x-auth-token": token, "Content-Type": "application/json"},
                         json=body,
                         timeout=15)
    result = resp.json()
    print(f"[{'✓' if result.get('code')==0 else '✗'}] 切换镜头->{video_type}: {result.get('message','')}")
    return result


if __name__ == "__main__":
    token = get_token()

    # 1. 从 MQTT OSD 获取 video_id（直播能力接口 camerasList 为空时走此路径）
    print("[*] 从 MQTT OSD 获取视频流...")
    video_ids = get_video_ids_from_mqtt()

    if not video_ids:
        # 回退到直播能力接口
        print("[*] MQTT 未获取到，尝试直播能力接口...")
        resp = requests.get(f"{BASE_URL}/manage/api/v1/live/capacity",
                            headers={"x-auth-token": token}, timeout=10)
        for dev in resp.json().get("data", []):
            for cam in dev.get("camerasList", []):
                vid = f"{dev.get('sn')}/{cam.get('payload_index')}/normal-0"
                video_ids.append(vid)

    if not video_ids:
        print("[✗] 没有可用的视频流，请确认无人机已上线")
        sys.exit(0)

    print(f"\n[✓] 可用视频流 ({len(video_ids)} 个):")
    for i, vid in enumerate(video_ids):
        rtsp = build_rtsp_url(vid)
        print(f"  [{i}] {vid}")
        print(f"      RTSP: {rtsp}")

    # 选择视频流
    selected = video_ids[0]
    if len(video_ids) > 1:
        idx = input(f"\n选择视频流编号 [0-{len(video_ids)-1}] (默认0): ").strip()
        if idx.isdigit() and int(idx) < len(video_ids):
            selected = video_ids[int(idx)]

    print(f"\n[*] 使用 video_id: {selected}")
    print(f"[*] RTSP 地址: {build_rtsp_url(selected)}")

    print("\n操作菜单：")
    print("  1. 开始直播")
    print("  2. 停止直播")
    print("  3. 切换清晰度（2=标清 3=高清）")
    print("  4. 切换镜头（zoom/ir）")
    print("  5. 启动直播并用低延迟 VLC 播放")
    print("  q. 退出\n")

    while True:
        cmd = input("输入操作: ").strip()
        if cmd == "q":
            break
        elif cmd == "1":
            ensure_rtsp_live(token, selected)
        elif cmd == "2":
            live_stop(token, selected)
        elif cmd == "3":
            q = input("  清晰度(2=标清 3=高清): ").strip()
            live_set_quality(token, selected, int(q))
        elif cmd == "4":
            lens = input("  镜头类型(zoom/ir): ").strip()
            live_switch_lens(token, selected, lens)
        elif cmd == "5":
            rtsp_url = ensure_rtsp_live(token, selected)
            if rtsp_url:
                open_vlc(rtsp_url)
        else:
            print("  未知操作")
