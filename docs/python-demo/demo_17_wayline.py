"""
demo_17_wayline.py -- 航线任务全流程（下发 / 执行 / 暂停 / 恢复 / 取消 / 进度上报）

对应 Autel Cloud API「航线管理」：
  下发任务   flighttask_prepare    Topic: thing/product/{gateway_sn}/services  down
  执行任务   flighttask_execute    （立即任务由服务端在 prepare 后自动下发 execute）
  航线暂停   flighttask_pause
  航线恢复   flighttask_recovery
  取消任务   flighttask_undo
  上报进度   flighttask_progress   Topic: thing/product/{gateway_sn}/events    up

REST 封装（cloud-service）：
  列航线库   GET    /wayline/api/v1/workspaces/{workspace}/waylines
  下发+执行  POST   /wayline/api/v1/workspaces/{workspace}/flight-tasks   （立即任务）
  暂停/恢复  PUT    /wayline/api/v1/workspaces/{workspace}/jobs/{job_id}  body={"status":0|1}
             status=0 暂停(flighttask_pause)，status=1 恢复(flighttask_recovery)
  取消任务   DELETE /wayline/api/v1/workspaces/{workspace}/jobs?job_id={job_id}
  任务列表   GET    /wayline/api/v1/workspaces/{workspace}/jobs

进度事件 flighttask_progress 字段：
  | 字段                    | 说明                                              |
  |-------------------------|---------------------------------------------------|
  | status                  | sent/in_progress/paused/ok/failed/canceled/...    |
  | progress.current_step   | 执行步骤枚举                                       |
  | progress.percent        | 当前步骤进度百分比 0~100                            |
  | ext.current_waypoint_index | 当前执行到的航点序号（从 0 开始）               |
  | ext.media_count         | 本次任务已产生的媒体文件数                          |
  | ext.flight_id           | 航线任务唯一 ID                                    |

【RC 网关注意】遥控器（REMOTER_CONTROL 域）作为网关时，服务端会自动为
flighttask_prepare/execute/undo/pause/recovery 补上 device_list 显式寻址无人机 SN，
否则遥控器静默丢弃指令、永不回复（211001）。分流逻辑在 FlightTaskServiceImpl 中按
网关域自动完成，demo 无需关心。

前提：航线库中已有 KMZ 航线文件（可在 Web 控制台「航线任务」页上传），
      config.py 的 DOCK_SN 为执行网关（机巢或遥控器）SN、WORKSPACE_ID 正确。

运行：
    python3 demo_17_wayline.py            # 交互菜单：下发/暂停/恢复/取消/查看
"""
import sys
import json
import time
import threading
import requests
from config import (BASE_URL, WEB_USERNAME, WEB_PASSWORD, WEB_FLAG,
                    DOCK_SN, WORKSPACE_ID, MQTT_HOST, MQTT_PORT,
                    MQTT_USERNAME, MQTT_PASSWORD)

if DOCK_SN == "YOUR_DOCK_SN":
    print("[✗] 请先在 config.py 中设置 DOCK_SN")
    sys.exit(1)

EVENTS_TOPIC = f"thing/product/{DOCK_SN}/events"
FLIGHTTASK_STATUS = {
    "sent": "已下发", "in_progress": "执行中", "paused": "暂停",
    "ok": "执行成功", "failed": "失败", "canceled": "取消或终止",
    "partially_done": "部分完成", "rejected": "拒绝", "timeout": "超时",
    "pending": "开始执行",
}
FINAL_STATUS = {"ok", "failed", "canceled", "partially_done", "rejected", "timeout"}


def get_token():
    resp = requests.post(f"{BASE_URL}/manage/api/v1/login",
                         json={"username": WEB_USERNAME, "password": WEB_PASSWORD, "flag": WEB_FLAG},
                         timeout=10)
    return resp.json()["data"]["access_token"]


def _headers(token):
    return {"x-auth-token": token, "Content-Type": "application/json"}


def _items(data):
    """兼容分页返回：data 可能是 list 或 {list:[...]} / {records:[...]}"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("list") or data.get("records") or []
    return []


def list_waylines(token):
    url = (f"{BASE_URL}/wayline/api/v1/workspaces/{WORKSPACE_ID}/waylines"
           f"?page=1&page_size=50&order_by=update_time%20desc")
    resp = requests.get(url, headers=_headers(token), timeout=15)
    return _items(resp.json().get("data"))


def list_jobs(token):
    url = f"{BASE_URL}/wayline/api/v1/workspaces/{WORKSPACE_ID}/jobs?page=1&page_size=50"
    resp = requests.get(url, headers=_headers(token), timeout=15)
    return _items(resp.json().get("data"))


def create_job(token, wayline: dict) -> bool:
    """下发并立即执行（flighttask_prepare + flighttask_execute）"""
    url = f"{BASE_URL}/wayline/api/v1/workspaces/{WORKSPACE_ID}/flight-tasks"
    body = {
        "name": f"{wayline.get('name', 'wayline')}-demo-{int(time.time())}",
        "file_id": wayline["id"],
        "dock_sn": DOCK_SN,
        "wayline_type": (wayline.get("template_types") or [0])[0],
        "task_type": 0,               # 0=立即任务，服务端 prepare 后自动 execute
        "rth_altitude": 100,          # 返航高度 20~1500 m
        "out_of_control_action": 0,   # 0=返航 1=悬停 2=降落
        "min_battery_capacity": 50,
        "min_storage_capacity": 0,
        "wayline_precision_type": 0,  # 0=GPS 1=RTK
        "barrier_switch_state": 1,    # 1=打开避障
        "takeoff_altitude": 100,
        "first_waypoint_speed": 10,
        "return_speed": 10,
        "media_upload_method": 0,     # 0=落地上传 1=边飞边传
        "alternate_land_point": {"is_configured": 0},
    }
    print(f"[*] 下发航线任务: {body['name']} （航线={wayline.get('name')}）")
    resp = requests.post(url, headers=_headers(token), json=body, timeout=30)
    result = resp.json()
    ok = result.get("code") == 0
    print(f"[{'✓' if ok else '✗'}] {result.get('message', result)}")
    return ok


def change_job(token, job_id: str, status: int) -> bool:
    """status=0 暂停(flighttask_pause)，status=1 恢复(flighttask_recovery)"""
    url = f"{BASE_URL}/wayline/api/v1/workspaces/{WORKSPACE_ID}/jobs/{job_id}"
    resp = requests.put(url, headers=_headers(token), json={"status": status}, timeout=15)
    result = resp.json()
    ok = result.get("code") == 0
    action = "暂停" if status == 0 else "恢复"
    print(f"[{'✓' if ok else '✗'}] {action}任务: {result.get('message', result)}")
    return ok


def cancel_job(token, job_id: str) -> bool:
    """flighttask_undo —— 取消任务"""
    url = (f"{BASE_URL}/wayline/api/v1/workspaces/{WORKSPACE_ID}/jobs"
           f"?job_id={requests.utils.quote(job_id)}")
    resp = requests.delete(url, headers=_headers(token), timeout=15)
    result = resp.json()
    ok = result.get("code") == 0
    print(f"[{'✓' if ok else '✗'}] 取消任务: {result.get('message', result)}")
    return ok


class ProgressWatcher(threading.Thread):
    """后台订阅 events，打印 flighttask_progress 进度事件"""

    def __init__(self):
        super().__init__(daemon=True)
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            self.client = None
            return
        self.client = mqtt.Client(client_id=f"demo17_wayline_{int(time.time())}")
        if MQTT_USERNAME:
            self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def run(self):
        if self.client is None:
            print("[!] 未安装 paho-mqtt，跳过进度订阅（pip install paho-mqtt 可开启）")
            return
        try:
            self.client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            self.client.loop_forever()
        except Exception as e:
            print(f"[!] MQTT 连接失败，跳过进度订阅: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(EVENTS_TOPIC)
            print(f"[✓] 已订阅进度事件 {EVENTS_TOPIC}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
        except Exception:
            return
        if payload.get("method") != "flighttask_progress":
            return
        output = (payload.get("data") or {}).get("output") or payload.get("data") or {}
        status = output.get("status", "")
        progress = output.get("progress") or {}
        ext = output.get("ext") or {}
        label = FLIGHTTASK_STATUS.get(status, status)
        print(f"  ↳ 进度 status={label} step={progress.get('current_step')} "
              f"percent={progress.get('percent')} waypoint={ext.get('current_waypoint_index')}")
        if status in FINAL_STATUS:
            print(f"[✓] 航线任务终态: {label}")


def _pick(prompt, items, render):
    if not items:
        return None
    for i, it in enumerate(items):
        print(f"  {i}. {render(it)}")
    raw = input(prompt).strip()
    if not raw.isdigit() or int(raw) >= len(items):
        return None
    return items[int(raw)]


if __name__ == "__main__":
    print(f"[*] 目标网关: {DOCK_SN}  工作空间: {WORKSPACE_ID}")
    token = get_token()

    ProgressWatcher().start()
    time.sleep(1)

    while True:
        print("\n航线任务菜单：")
        print("  1. 下发并立即执行（从航线库选择 KMZ）")
        print("  2. 暂停任务")
        print("  3. 恢复任务")
        print("  4. 取消任务")
        print("  5. 查看任务列表")
        print("  0. 退出")
        choice = input("选择> ").strip()

        if choice == "1":
            waylines = list_waylines(token)
            if not waylines:
                print("[!] 航线库为空，请先在 Web 控制台上传 KMZ 航线")
                continue
            wl = _pick("选择航线序号> ", waylines,
                       lambda w: f"{w.get('name')} ({w.get('drone_model_key', '—')})")
            if wl:
                create_job(token, wl)
        elif choice in ("2", "3", "4"):
            jobs = [j for j in list_jobs(token) if j.get("status") in (1, 2, 6)]
            if not jobs:
                print("[!] 没有可操作的任务（待执行/进行中/已暂停）")
                continue
            job = _pick("选择任务序号> ", jobs,
                        lambda j: f"{j.get('job_name')} 状态={j.get('status')}")
            if not job:
                continue
            jid = job["job_id"]
            if choice == "2":
                change_job(token, jid, 0)
            elif choice == "3":
                change_job(token, jid, 1)
            else:
                cancel_job(token, jid)
        elif choice == "5":
            for j in list_jobs(token):
                print(f"  - {j.get('job_name')} | 状态={j.get('status')} "
                      f"| 进度={j.get('progress', 0)}% | id={j.get('job_id')}")
        elif choice == "0":
            break
        else:
            print("[!] 无效选择")
