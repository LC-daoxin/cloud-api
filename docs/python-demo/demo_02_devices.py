"""
demo_02_devices.py -- 查询在线设备列表，获取遥控器/无人机 SN 和负载索引

运行：
    python3 demo_02_devices.py

输出结果中把 dock_sn / drone_sn / payload_index 填入 config.py。
"""
import requests
import json
from config import BASE_URL, WEB_USERNAME, WEB_PASSWORD, WEB_FLAG, WORKSPACE_ID, SERVER_IP
from demo_common import check_online_via_redis


def get_token():
    resp = requests.post(f"{BASE_URL}/manage/api/v1/login",
                         json={"username": WEB_USERNAME, "password": WEB_PASSWORD, "flag": WEB_FLAG},
                         timeout=10)
    return resp.json()["data"]["access_token"]


def get_devices(token):
    headers = {"x-auth-token": token}
    domain_map = {0: "无人机", 1: "负载", 2: "遥控器", 3: "机巢"}

    # 设备拓扑
    url = f"{BASE_URL}/manage/api/v1/devices/{WORKSPACE_ID}/devices"
    resp = requests.get(url, headers=headers, timeout=10)
    devices = resp.json().get("data", [])

    print(f"\n[✓] 设备列表 (workspace: {WORKSPACE_ID})")
    print(f"{'SN':<32} {'类型':<8} {'子设备SN':<24} {'在线'}")
    print("-" * 80)

    dock_sn = None
    drone_sn = None
    for d in devices:
        sn = d.get("device_sn", "")
        domain = domain_map.get(d.get("domain"), str(d.get("domain")))
        child = d.get("child_device_sn", "") or ""
        # 真正在线状态：查 Redis online:{sn} key（应用侧 60 秒无心跳刷新即过期）
        is_online = check_online_via_redis(sn)
        online_str = "✓ 在线" if is_online else "○ 离线"
        print(f"{sn:<32} {domain:<8} {child:<24} {online_str}")

        # 遥控器/机巢的 child_device_sn 就是无人机 SN
        if child and d.get("domain") in (2, 3):
            drone_sn = child
            # 如果是机巢(domain=3)，dock_sn 就是它自己
            if d.get("domain") == 3:
                dock_sn = sn
            # 如果是遥控器(domain=2)，dock_sn 暂时等于遥控器 SN（后续用直播能力补）
            elif d.get("domain") == 2 and not dock_sn:
                dock_sn = sn

    if not devices:
        print("  (无设备)")
        return

    print(f"\n[!] 请将以下值填入 config.py：")
    if dock_sn:
        print(f"    DOCK_SN = \"{dock_sn}\"")
    if drone_sn:
        print(f"    DRONE_SN = \"{drone_sn}\"")
    else:
        print(f"    DRONE_SN = \"(暂无子设备，设备上线后自动获取)\"")

    # 检查是否有设备在线
    any_online = any(check_online_via_redis(d.get("device_sn", "")) for d in devices)
    if not any_online:
        print(f"\n[!] 当前无设备在线（Redis 无在线 key）")
        print(f"    设备需要通过 MQTT 发送 status/update_topo 才能上线")
        print(f"    请在 Pilot App 中重新连接云服务")
        print(f"    验证命令: docker exec uav-redis redis-cli keys '*online*'")

    # 直播能力
    live_url = f"{BASE_URL}/manage/api/v1/live/capacity"
    live_resp = requests.get(live_url, headers=headers, timeout=10)
    live_data = live_resp.json().get("data", [])

    if live_data:
        print(f"\n[✓] 在线设备直播能力（可获取 payload_index）")
        for dev in live_data:
            print(f"\n  设备 SN: {dev.get('sn')}")
            # 兼容两种字段格式：cameras_list（Cloud-API 实际返回）/ camerasList（旧格式）
            cameras = dev.get("cameras_list") or dev.get("camerasList") or []
            for cam in cameras:
                # Cloud-API 返回 index；旧版本返回 payload_index
                index = cam.get("index") or cam.get("payload_index")
                name = cam.get("name") or cam.get("camera_type", "")
                # 镜头列表在 videos_list[].type
                videos = cam.get("videos_list") or cam.get("videosList") or []
                lens = [v.get("type") for v in videos if v.get("type")]
                lens_str = f" 镜头: {','.join(lens)}" if lens else ""
                print(f"    摄像头: {index} | {name}{lens_str}")
                print(f"    -> 填入 config.py PAYLOAD_INDEX = \"{index}\"")
    else:
        print(f"\n[!] 直播能力为空（设备未上报 capability）")
        print(f"    PAYLOAD_INDEX 只能从 OSD 数据获取：")
        print(f"    1. 运行 demo_03_websocket_osd.py")
        print(f"    2. 查看推送的 OSD 消息中 payloads[].payload_index 字段")
        print("    3. 格式为 'domain-type-subtype'，如 '1-10052-0'")


if __name__ == "__main__":
    token = get_token()
    get_devices(token)
