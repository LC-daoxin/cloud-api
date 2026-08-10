"""
demo_11_livestream.py -- 直播全流程

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
    python3 demo_11_livestream.py
"""
import sys
import json
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


def get_token():
    resp = requests.post(f"{BASE_URL}/manage/api/v1/login",
                         json={"username": WEB_USERNAME, "password": WEB_PASSWORD, "flag": WEB_FLAG},
                         timeout=10)
    return resp.json()["data"]["access_token"]


def get_video_ids_from_mqtt(timeout_sec=8) -> list:
    """通过 MQTT 订阅遥控器 OSD，从 live_status 中提取 video_id 列表。

    注意：这里只是枚举设备上报过的镜头通道（video_id），
    不代表 status==1（正在推流）；是否真的有流请用 probe_rtsp 判断。"""
    video_ids = []
    seen = set()
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
                    status = ls.get("status")
                    if vid and vid not in seen:
                        seen.add(vid)
                        video_ids.append(vid)
                        state = "设备自报推流中" if status == 1 else "未推流"
                        print(f"  发现镜头通道: {vid}  type={vtype}  status={status}({state})")
                if video_ids:
                    done[0] = True
                    client.disconnect()
        except Exception:
            pass

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id=f"demo_11_{int(time.time())}")
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


def build_rtsp_playback_url(video_id: str) -> str:
    """不带账号密码的拉流地址（展示/播放提示用，避免在终端泄露凭据）"""
    parts = video_id.split("/")
    drone_sn = parts[0] if len(parts) > 0 else "unknown"
    payload_index = parts[1] if len(parts) > 1 else "0-0-0"
    return f"rtsp://{SERVER_IP}:{RTSP_PORT}/{drone_sn}-{payload_index}"


def parse_video_type(video_id: str) -> str:
    """从 video_id（如 drone_sn/payload_index/zoom-0）中解析出当前镜头类型。"""
    parts = video_id.split("/")
    if len(parts) < 3:
        return "normal"
    return parts[2].split("-")[0] or "normal"


def resolve_alternate_lens(desired_lens: str) -> str:
    """与前端 CockpitView.vue 的双传感器兜底策略一致：zoom<->ir 互为唤醒镜头。"""
    if desired_lens == "zoom":
        return "ir"
    if desired_lens == "ir":
        return "zoom"
    return "ir"


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


def live_start(token, video_id: str, url_type: int = 2, video_quality: int = 3,
               video_type: str | None = None):
    """开始直播

    video_type 默认从 video_id 中解析当前镜头并显式下发，避免设备沿用上一次
    会话残留的镜头（例如恢复流程临时切到红外后未正确切回，导致新会话仍是红外）。
    """
    if video_type is None:
        video_type = parse_video_type(video_id)
    body = {
        "url_type": url_type,
        "video_id": video_id,
        "video_quality": video_quality,
    }
    if video_type in ("zoom", "ir"):
        body["video_type"] = video_type
    if url_type == 2:
        # 关键：把完整 MediaMTX 发布地址下发给设备。旧实现只下发账号、
        # 密码和端口，却在客户端猜测 /live/... 路径，服务端并无该流。
        body["url"] = build_rtsp_url(video_id)
    # 服务端等待设备 MQTT 应答最坏情况可达 3次×20秒=60秒（见 AbstractLivestreamService.DEFAULT_TIMEOUT ＋
    # MqttGatewayPublish.DEFAULT_RETRY_COUNT），这里要盖过那个时长，否则会先于服务端报出 ReadTimeout
    resp = requests.post(f"{BASE_URL}/manage/api/v1/live/streams/start",
                         headers={"x-auth-token": token, "Content-Type": "application/json"},
                         json=body,
                         timeout=65)
    result = resp.json()
    if result.get("code") == 0:
        print(f"[✓] 直播已开始  video_id={video_id}")
        # 展示 RTSP 拉流地址
        if url_type == 2:
            live_data = result.get("data") or {}
            rtsp_url = live_data.get("url") or build_rtsp_url(video_id)
            playback_url = build_rtsp_playback_url(video_id)
            print(f"    RTSP 拉流地址: {rtsp_url}")
            print(f"    可用 ffplay 播放: ffplay -rtsp_transport tcp -fflags nobuffer+discardcorrupt "
                  f"-flags low_delay -avioflags direct -probesize 32 -sync ext -framedrop "
                  f"-vf setpts=0 \"{playback_url}\"")
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


def live_stop(token, video_id: str):
    """停止直播"""
    body = {"video_id": video_id}
    resp = requests.post(f"{BASE_URL}/manage/api/v1/live/streams/stop",
                         headers={"x-auth-token": token, "Content-Type": "application/json"},
                         json=body,
                         timeout=65)
    result = resp.json()
    print(f"[{'✓' if result.get('code')==0 else '✗'}] 停止直播: {result.get('message','')}")
    return result


def live_set_quality(token, video_id: str, video_quality: int):
    """切换清晰度  仅 2=标清  3=高清 有效"""
    body = {"video_id": video_id, "video_quality": video_quality}
    resp = requests.post(f"{BASE_URL}/manage/api/v1/live/streams/update",
                         headers={"x-auth-token": token, "Content-Type": "application/json"},
                         json=body,
                         timeout=65)
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
                         timeout=65)
    result = resp.json()
    print(f"[{'✓' if result.get('code')==0 else '✗'}] 切换镜头->{video_type}: {result.get('message','')}")
    return result


def live_start_recover_by_lens_switch(token, video_id: str) -> str | None:
    """开始直播后经常出现设备指令应答成功、却始终不推流的情况——EVO Max 固件缺陷：
    RTSP 轨道已宣告但编码器未真正开始产生媒体包，直到镜头被“碰一下”才会吐首帧。

    与前端 CockpitView.vue 的 recoverVideoEncoder 保持一致的判定/延迟节奏：
    等待 4 秒判断首帧是否到达；未到达则临时切到备用镜头触发编码器重建，
    等 1.8 秒后切回目标镜头，再等 1.2 秒让编码器吐出目标镜头的首帧；
    若切回目标镜头失败，会补发一次纠正指令，避免设备停留在临时镜头上。"""
    rtsp_url = build_rtsp_url(video_id)
    desired_lens = parse_video_type(video_id)
    alternate_lens = resolve_alternate_lens(desired_lens)

    live_start(token, video_id, URL_TYPE, VIDEO_QUALITY, video_type=desired_lens)

    print("[*] 等待 4 秒检查是否已产生首帧...")
    time.sleep(4)
    if probe_rtsp(rtsp_url, timeout_sec=3):
        print("[✓] 已检测到推流")
        return rtsp_url

    print(f"[*] 未检测到推流，临时切到 {alternate_lens} 触发编码器重建...")
    switched_to_alternate = live_switch_lens(token, video_id, alternate_lens).get("code") == 0
    time.sleep(1.8)
    print(f"[*] 切回目标镜头 {desired_lens}...")
    switch_back = live_switch_lens(token, video_id, desired_lens)
    if switch_back.get("code") != 0 and switched_to_alternate:
        # 切回失败但设备已经移动到临时镜头——补发一次纠正指令，避免画面停留在红外上
        print(f"[!] 切回 {desired_lens} 失败，补发一次纠正指令...")
        live_switch_lens(token, video_id, desired_lens)
    time.sleep(1.2)

    if probe_rtsp(rtsp_url, timeout_sec=6):
        print("[✓] 切换镜头后已恢复推流")
        return rtsp_url

    print("[✗] 切换镜头后仍未恢复推流")
    return None


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

    print(f"\n[✓] 可发起直播的镜头通道 ({len(video_ids)} 个，仅表示存在该 video_id，不代表当前正在推流):")
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
    print("  6. 开始直播，若4秒无首帧则临时切镜头强制恢复（与前端 CockpitView 逻辑一致）")
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
        elif cmd == "6":
            live_start_recover_by_lens_switch(token, selected)
        else:
            print("  未知操作")
