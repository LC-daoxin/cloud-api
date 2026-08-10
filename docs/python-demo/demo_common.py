"""
demo_common.py -- 各 demo 共享的错误诊断工具

当控制指令报错时（尤其是「设备未注册」「设备离线」这类难以定位的问题），
统一给出可操作的诊断信息：
  1. 解释服务端错误码的常见原因
  2. 列出工作空间内实际已注册的网关设备及其在线状态，与 config.py 中的
     DOCK_SN 对照，帮助判断 SN 是否过期/写错

用法：
    from demo_common import diagnose

    result = resp.json()
    if result.get("code") != 0:
        # 抢权等前置步骤失败：退出程序
        diagnose(token, "抢占负载控制权", result.get("message", ""))
        # 单条指令失败：不退出，只打印诊断
        diagnose(token, "发送变焦指令", result.get("message", ""), exit_on_error=False)
"""
import sys
import subprocess
import requests
from config import BASE_URL, DOCK_SN, WORKSPACE_ID


def check_online_via_redis(sn: str) -> bool:
    """通过 docker exec redis-cli 查询设备在线 key（与 demo_02 保持一致）"""
    cmd = ["docker", "exec", "uav-redis", "redis-cli", "exists", f"online:{sn}"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return r.stdout.strip() == "1"
    except Exception:
        return False


def fetch_gateway_devices(token):
    """查询当前工作空间中已注册的网关设备（遥控器/机巢）。

    返回 [(device_sn, child_device_sn, is_online), ...]
    """
    url = f"{BASE_URL}/manage/api/v1/devices/{WORKSPACE_ID}/devices"
    try:
        resp = requests.get(url, headers={"x-auth-token": token}, timeout=10)
        devices = resp.json().get("data", [])
    except Exception:
        return []
    result = []
    for d in devices:
        if d.get("domain") not in (2, 3):  # 只关心网关：遥控器/机巢
            continue
        sn = d.get("device_sn", "")
        result.append((sn, d.get("child_device_sn", ""), check_online_via_redis(sn)))
    return result


def diagnose(token, action, server_msg, exit_on_error=True):
    """报错时给出可操作的诊断信息，并列出当前实际注册/在线的设备供对照。

    :param exit_on_error: True 时打印诊断后 sys.exit(1)（前置步骤失败）；
                          False 时打印后返回 False（单条指令失败，可继续）。
    """
    code_hint = ""
    msg_low = (server_msg or "").lower()
    if "not registered" in msg_low or "210001" in str(server_msg):
        code_hint = ("    [原因] 服务端没有这个设备的注册记录。通常是 config.py 里的 SN 已过期\n"
                     "           （数据库重建/换过设备后旧 SN 失效），而不是设备没连上。")
    elif "211001" in str(server_msg) or "no message reply" in msg_low:
        code_hint = ("    [原因] 指令已下发但设备没有回复（211001）。检查：\n"
                     "           1) 无人机是否在遥控器下处于可控制状态\n"
                     "           2) 是否已先抢占对应的控制权\n"
                     "           3) RC 网关场景 device_list 寻址是否正常")
    elif "offline" in msg_low:
        code_hint = "    [原因] 设备离线。请确认遥控器/Pilot App 已连接云端，或检查 MQTT 连通性。"
    elif "payload" in msg_low and ("index" in msg_low or "authority" in msg_low):
        code_hint = ("    [原因] 负载索引可能不对。运行 demo_02_devices.py 查看实际的 PAYLOAD_INDEX，\n"
                     "           并把 config.py 里的 PAYLOAD_INDEX 更新为 cameras_list[].index 的值。")

    print(f"\n[✗] {action} 失败")
    print(f"    服务端返回: {server_msg}")
    if code_hint:
        print(code_hint)

    print(f"\n    [诊断] 当前 config.py 使用的设备: DOCK_SN = {DOCK_SN}")
    print(f"    [诊断] 工作空间 {WORKSPACE_ID} 内实际已注册的网关设备：")
    found_current = False
    for sn, drone, online in fetch_gateway_devices(token):
        flag = "← 当前使用" if sn == DOCK_SN else ""
        state = "✓ 在线" if online else "○ 离线"
        print(f"      - {sn}  子设备: {drone or '(无)'}  [{state}]  {flag}")
        if sn == DOCK_SN:
            found_current = True
    if not found_current:
        print("      （当前 DOCK_SN 不在列表里 → 说明 SN 错误/已过期，请改用上面列表中的 SN）")
    print("\n    提示：运行 demo_02_devices.py 可一键获取最新的 DOCK_SN / PAYLOAD_INDEX")

    if exit_on_error:
        sys.exit(1)
    return False
