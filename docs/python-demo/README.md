# Python Demo 使用指南

本目录包含一套面向开发者和测试人员的独立 Python 脚本，用于验证云平台 API、演示设备控制能力。每个文件均可单独运行，无需了解项目内部结构。

---

## 环境准备

### 方法一：一键运行（推荐）

使用 `run.sh` 脚本，**首次运行时自动创建虚拟环境并安装依赖**，后续无需任何操作：

```bash
cd docs/python-demo
chmod +x run.sh          # 首次执行前赋权
./run.sh demo_01_login.py
```

### 方法二：手动虚拟环境

```bash
cd docs/python-demo

# 创建虚拟环境
python3 -m venv .venv

# 激活（每次新开终端都需要执行）
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行 demo
python3 demo_01_login.py
```

> **不要用 `pip3 install -r requirements.txt` 直接安装**。macOS Homebrew 管理的 Python 是隔离环境，全局安装会报 `externally-managed-environment` 错误，需要虚拟环境隔离。

### 依赖说明

| 包 | 用途 |
|---|---|
| `requests` | HTTP API 调用（所有 demo） |
| `websocket-client` | WebSocket 实时推送（demo_03） |
| `paho-mqtt` | MQTT 订阅/下发（demo_04 / demo_12 / demo_14 / demo_15） |

---

## 第一步：修改配置

**运行任何 demo 前，先编辑 `config.py`**，填入你的服务器地址和设备信息：

```python
# config.py 关键字段

SERVER_IP = "172.20.10.8"   # ← 改为你的服务器 IP

DOCK_SN    = "YOUR_DOCK_SN"   # ← 运行 demo_02 后填入
DRONE_SN   = "YOUR_DRONE_SN"  # ← 运行 demo_02 后填入
PAYLOAD_INDEX = "0-0-0"       # ← 运行 demo_02 后填入
```

---

## Demo 文件说明

### `demo_01_login.py` —— 登录验证

验证服务器是否正常，打印 token 和 MQTT 配置信息。

```bash
./run.sh demo_01_login.py
```

**预期输出：**
```
[✓] 登录成功
    token        : eyJ0eXAi...
    workspace_id : e3dea0f5-...
    mqtt_addr    : tcp://172.20.10.8:1883

[!] Pilot/App 端 MQTT 配置：
    MQTT 地址    : tcp://172.20.10.8:1883
    MQTT 账号    : admin
    MQTT 密码    : admin
```

---

### `demo_02_devices.py` —— 查询设备列表

列出当前工作空间中所有设备的 SN、昵称、类型和在线状态。**运行此 demo 获取 DOCK_SN 和 PAYLOAD_INDEX，填入 `config.py`**。

```bash
./run.sh demo_02_devices.py
```

**预期输出：**
```
[✓] 设备列表 (workspace: ...)
SN                类型   子设备SN              在线
TH7926043417      遥控器 1748FEV3HMP925511143  ✓

[!] 请将以下值填入 config.py：
    DOCK_SN = "TH7926043417"
    DRONE_SN = "1748FEV3HMP925511143"

[!] 直播能力为空（设备未上报 capability）
    PAYLOAD_INDEX 只能从 OSD 数据获取：
    1. 运行 demo_03_websocket_osd.py
    2. 查看推送的 OSD 消息中 payloads[].payload_index 字段
    3. 格式为 "domain-type-subtype"，如 "1-10052-0"
```

---

### `demo_03_websocket_osd.py` -- 实时遥测数据监听

订阅 WebSocket，实时打印飞机位置、高度、电量、速度等遥测数据，以及设备上下线事件。

```bash
./run.sh demo_03_websocket_osd.py
```

**实时输出示例：**
```
[✓] WebSocket 已连接，等待推送数据...

[OSD-无人机] lat=22.543100 lon=113.921300 h=50.0m spd=5.0m/s bat=85% mode=MANUAL
[OSD-遥控器] mode=IDLE
[事件] 设备上线: {...}
[进度] fly_to_point_progress: {"status": "running", "progress": 60}
[!!] Joystick 已失效: reason=4 遥控器夺权（如 B 控触发返航）
     drone_control 不再生效，手动操控不可用
```

按 `Ctrl+C` 退出。

---

### `demo_04_mqtt_osd.py` -- MQTT 原始 OSD 数据监听

通过 MQTT 直接订阅设备 OSD 原始报文，比 demo_03（WebSocket）获取的数据更完整。

```bash
./run.sh demo_04_mqtt_osd.py
```

按 `Ctrl+C` 退出。

---

### `demo_05_gimbal_zoom.py` -- 云台变焦

设置相机变焦倍率（2.0 ～ 200.0）。

**前提条件：**
- `config.py` 中已填入 `DOCK_SN` 和 `PAYLOAD_INDEX`
- 无人机已上线，相机处于 IDLE 状态

**修改变焦倍率**（在文件顶部）：

```python
ZOOM_FACTOR = 5.0   # 改为目标倍率，范围 2.0 ~ 200.0
```

```bash
./run.sh demo_05_gimbal_zoom.py
```

**预期输出：**
```
[✓] 已获取负载控制权
[✓] 变焦成功，当前倍率: 5.0x
```

---

### `demo_06_gimbal_pitch.py` -- 云台方向控制（交互式）

`camera_aim` 是**屏幕坐标指点**接口（不是连续转速控制）：
- `x/y` 为 0.0~1.0 的归一化屏幕坐标，`y=0.0` 指向画面上方（仰角），`y=1.0` 指向画面下方（俯角）
- 同时支持 `gimbal_reset` 直接复位到预设角度

```bash
./run.sh demo_06_gimbal_pitch.py
```

**交互示例：**
```
云台控制指令：
  up      → 指向上方（y=0.0 画面上方）
  down    → 指向下方（y=1.0 画面下方）
  left    → 指向左方（x=0.0 画面左边）
  right   → 指向右方（x=1.0 画面右边）
  center  → 指向画面中心（x=0.5, y=0.5）
  horizon → 云台居中（gimbal_reset mode=0）
  down90  → 云台垂直下射（gimbal_reset mode=1）

输入指令: down
  [✓] 指向下方
```

| 指令 | 效果 | 接口参数 |
|---|---|---|
| `up` | 仰角向上 | x=0.5, y=0.0 |
| `down` | 俯角向下 | x=0.5, y=1.0 |
| `left` | 向左偏转 | x=0.0, y=0.5 |
| `right` | 向右偏转 | x=1.0, y=0.5 |
| `center` | 水平居中 | x=0.5, y=0.5 |
| `horizon` | 云台归位 | gimbal_reset mode=0 |
| `down90` | 垂直下射 | gimbal_reset mode=1 |

---

### `demo_07_camera.py` -- 相机控制

**拍照：**
```bash
./run.sh demo_07_camera.py photo
```

**开始录像：**
```bash
./run.sh demo_07_camera.py rec_start
```

**停止录像：**
```bash
./run.sh demo_07_camera.py rec_stop
```

**执行流程：**
1. 自动抢占负载控制权
2. 切换相机模式（拍照→模式0，录像→模式1）
3. 发送对应指令

---

### `demo_08_fly_to_point.py` -- 飞向目标坐标（飞行中）

**前提：无人机已在空中，处于 MANUAL 模式。**

修改文件顶部的目标坐标：

```python
TARGET_LATITUDE  = 22.5431    # 目标纬度
TARGET_LONGITUDE = 113.9213   # 目标经度
TARGET_HEIGHT    = 50.0       # 目标高度（米）
MAX_SPEED        = 5          # 最大速度 1~15 m/s
```

```bash
./run.sh demo_08_fly_to_point.py
```

脚本按三步执行：

1. **抢夺飞行控制权** `flight_authority_grab`
2. **下发飞行指令** `POST .../jobs/fly-to-point`
3. **订阅进度** 直到任务进入终态

**输出示例：**
```
[✓] 已抢夺飞行控制权 (flight_authority_grab)
[✓] 已订阅 thing/product/TH7926043417/events
[*] 飞向坐标: lat=22.5431, lon=113.9213, h=50.0m, 速度=5m/s
[✓] 飞向目标点指令已下发

[轨迹] 规划航点 4 个
    #0 lat=22.5431 lon=113.9213 h=50.0
    #1 lat=22.544 lon=113.922 h=50.0
    ... 其余 1 个已省略
[飞行中] 航点#0  剩余 812.4 m  预计 163.5 s
[飞行中] 航点#1  剩余 204.1 m  预计 41.0 s

[✓] 执行成功，已飞抵目标点  result=0  fly_to_id=abc-123
```

#### 飞行控制权抢夺 `flight_authority_grab`

飞控类指令（fly-to-point、takeoff-to-point 等）的**前置条件**。没有控制权时指令会被设备拒绝。

| 项 | 值 |
|---|---|
| HTTP | `POST /control/api/v1/devices/{sn}/authority/flight`（无请求体） |
| 下发 Topic | `thing/product/{gateway_sn}/services` |
| Method | `flight_authority_grab`，`data` 为 `{}` |
| 回复 Topic | `thing/product/{gateway_sn}/services_reply` |
| 回复 Data | `{ "result": int }`，非 0 代表错误 |

脚本菜单里的 `auth` 选项可单独抢权，不下发飞行指令。

> 负载控制权是另一套接口 `POST .../authority/payload`（需要 `payload_index`），见 demo_05/07/13。

#### 执行进度 `fly_to_point_progress`

| 项 | 值 |
|---|---|
| Topic | `thing/product/{gateway_sn}/events` |
| Direction | up（机 → 云） |
| Method | `fly_to_point_progress` |

| 字段 | 类型 | 说明 |
|---|---|---|
| `fly_to_id` | text | 本次 flyto 任务唯一标识 |
| `status` | enum | 见下表 |
| `result` | int | 返回码，非 0 代表错误 |
| `way_point_index` | int | 当前飞往第几个航点 |
| `remaining_distance` | float | 距目标点剩余距离（米） |
| `remaining_time` | float | 预计剩余时间（秒） |
| `planned_path_points` | array | 规划轨迹点 `[{latitude, longitude, height}]` |

`status` 取值：

| 值 | 含义 |
|---|---|
| `wayline_progress` | 执行中 |
| `wayline_ok` | 执行成功，已飞抵目标点 |
| `wayline_failed` | 执行失败 |
| `wayline_cancel` | 已取消飞向目标点 |

> **WebSocket 还是 MQTT？**
>
> 服务端已补齐 `FlyToPointProgress` 模型（新增 `remainingDistance` / `remainingTime` /
> `plannedPathPoints`），并通过 `FlyToPointProgressNotifyDTO` 将 `fly_to_id` / `status` /
> `way_point_index` / `remaining_distance` / `remaining_time` / `planned_path_points`
> 完整透传到 WebSocket（见 `SDKControlService.flyToPointProgress`）。该改动需**重新构建镜像**后生效。
>
> 本 demo 仍直连 MQTT 订阅 `events`，目的是展示设备上报的原始报文格式。

`planned_path_points` 每帧都会带，脚本只在首次收到时展开，避免刷屏。

---

### `demo_09_dock_control.py` -- 设备远程控制（菜单式）

交互菜单控制设备（返航、重启等）。接口为 `POST /control/api/v1/devices/{sn}/jobs/{method}`，请求体 `{}`。

```bash
./run.sh demo_09_dock_control.py
```

```
设备控制菜单：
   1. 开舱盖
   2. 关舱盖
   3. 开无人机电源
   4. 关无人机电源
   5. 一键返航（飞行器飞回返航点）
   6. 取消返航（原地悬停）
   7. 重启设备
   8. 开始充电
   ...
选择操作编号: 5
  [!] 确认一键返航？输入 YES 确认: YES
[✓] 一键返航（飞行器飞回返航点） 成功
```

> 注：部分操作（如开舱盖、充电）仅适用于机巢场景；遥控器作为地面站上云时，返航、重启等指令仍可用。
> 一键返航会真实改变航迹，脚本内置了 `YES` 二次确认。
> 急停 / 紧急降落 / 强制降落等其他应急手段见 `demo_15_emergency.py`。

---

### `demo_10_takeoff_to_point.py` -- 一键起飞到目标坐标

**前提：无人机已连接且在线（遥控器作为地面站上云），无人机处于可起飞状态。**

修改文件顶部参数：

```python
TARGET_LATITUDE         = 22.5431
TARGET_LONGITUDE        = 113.9213
TARGET_HEIGHT           = 50.0     # 目标高度（米）
SECURITY_TAKEOFF_HEIGHT = 20.0    # 安全起飞高度（米）
RTH_ALTITUDE            = 100.0   # 返航高度（米）
```

```bash
./run.sh demo_10_takeoff_to_point.py
```

执行前需要输入 `yes` 确认，防止误操作。

---

### `demo_11_livestream.py` -- 直播全流程

开始直播、切换清晰度、切换镜头、停止直播。

```bash
./run.sh demo_11_livestream.py
```

> **操作6：无流强制恢复**
>
> 实测中 `live_start` 经常出现指令应答成功、但 MediaMTX 一直收不到推流的情况
> （设备内部 `live_status` 卡在"已在直播"，见前文排查记录）。菜单 `6` 走这个流程：
>
> 1. 调用 `live_start` 开始直播
> 2. 等待 3 秒探测流
> 3. 无流则 `live_switch_lens` 切到 `ir`，等待 1 秒
> 4. 再切回 `zoom`，等待 10 秒后再次探测流
>
> 通过强制切镜头触发设备重新建立推流连接，绕开卡死的内部状态位。

---

### `demo_12_drc.py` -- DRC 指令飞行

**前提：无人机已在空中，且已获取飞行控制权。**

流程：`drc/connect` → `drc/enter` → MQTT 下发指令 → `drc/exit`。
`drc/enter` 返回的 Topic 为：

| 方向 | Topic |
|---|---|
| pub（云 → 机） | `thing/product/{sn}/drc/down` |
| sub（机 → 云） | `thing/product/{sn}/drc/up` |

DRC 下行指令：

| method | data | 说明 |
|---|---|---|
| `heart_beat` | `{seq, timestamp}` | 心跳，必须 1 秒一次，否则设备会退出 DRC |
| `drone_control` | `{seq, x, y, h, w}` | 摇杆飞行控制 |
| `drone_emergency_stop` | `{}` | 急停：立即刹停并原地悬停，不降落 |
| `drc_emergency_landing` | `{}` | 紧急降落：避障 + 识别二维码降落 |
| `drc_force_landing` | `{}` | 强制降落：忽略障碍物直接下降 |

`drone_control` 参数范围：

| 参数 | 含义 | 单位 | 范围 |
|---|---|---|---|
| `x` | 前后速度（正=前） | m/s | -17 ~ 17 |
| `y` | 左右速度（正=右） | m/s | -17 ~ 17 |
| `h` | 升降速度（正=上） | m/s | -4 ~ 5 |
| `w` | 偏航角速度（正=顺时针） | 度/s | -90 ~ 90 |

DRC 上行消息（`thing/product/{sn}/drc/up`）：

| method | 说明 | 脚本中的体现 |
|---|---|---|
| `heart_beat` | 设备原样回显下发的 `timestamp`，差值即往返时延 | `ping` 指令 |
| `hsi_info_push` | 避障信息，上/下/前4/后4/左3/右3 共 16 路雷达距离（毫米） | `hsi` 指令 |

> `hsi_info_push` 上报频率很高，脚本只缓存快照，仅在最近障碍物 < 5 m 时限频告警（最快 2 秒一次），
> 避免刷屏淡化其他输出；随时输入 `hsi` 可查看完整六向距离。

```bash
./run.sh demo_12_drc.py
```

**交互指令：**
```
DRC 飞行指令（速度单位 m/s，偏航单位 度/s）：
  fwd <n>   → 前进 n     （x=n，   -17~17）
  back <n>  → 后退 n     （x=-n，  -17~17）
  right <n> → 向右 n     （y=n，   -17~17）
  left <n>  → 向左 n     （y=-n，  -17~17）
  up <n>    → 上升 n     （h=n，    -4~5）
  down <n>  → 下降 n     （h=-n，   -4~5）
  yaw <n>   → 偏航 n     （w=n，  -90~90）
  hover     → 悬停（全零）

应急指令（互斥，请勿混用降落类指令）：
  stop      → 急停       drone_emergency_stop
  land      → 紧急降落   drc_emergency_landing
  fland     → 强制降落   drc_force_landing

状态查询：
  hsi       → 查看最近一次避障信息（六向障碍物距离）
  ping      → 查看心跳往返时延

  q         → 退出 DRC 模式
```

> 降落类指令的执行结果在 `thing/product/{sn}/services_reply` 返回，
> 脚本会额外建一条到主 MQTT Broker 的连接来监听（DRC 专用连接的 ACL 只放行 `drc/up`、`drc/down`）。

---

### Joystick 失效通知

`joystick_invalid_notify` 是 **DRC 手动操控不可用**的根因。一旦收到，`drone_control` 就不再生效。

| 项 | 值 |
|---|---|
| Topic | `thing/product/{gateway_sn}/events` |
| Direction | up（机 → 云） |
| Method | `joystick_invalid_notify` |
| Data | `{ "reason": int }` |

`reason` 取值：

| 值 | 含义 |
|:---:|---|
| 0 | 遥控器失联 |
| 1 | 低电量返航 |
| 2 | 低电量降落 |
| 3 | 靠近限飞区 |
| 4 | 遥控器夺权（如 B 控触发了返航） |

**在三个 demo 里都有体现：**

| 脚本 | 通道 | 行为 |
|---|---|---|
| `demo_03_websocket_osd.py` | WebSocket bizCode | 服务端转发后打印中文 reason |
| `demo_12_drc.py` | MQTT `events` | 旁路监听，失效时醒目告警 |
| `demo_15_emergency.py` | MQTT `events` | 失效时提示改用返航 / 降落类指令 |

报文带 `need_reply: 1`，由**服务端**负责回 `events_reply`；demo 只旁路观察，不重复回复。

---

### `demo_13_payload_advanced.py` -- 高级负载控制（YOOX 扩展）

菜单式操作，包含 **Look At**（云台指向指定 GPS 坐标）、画面拖动、连续变焦、存储镜头设置。

```bash
./run.sh demo_13_payload_advanced.py
```

```
  1-5. 画面拖动    camera_screen_drag
  6-8. 连续变焦    camera_focal_length_drag
  9.   Look At     camera_look_at        ← 输入经纬度 + 高度，云台自动指向该点
  A.   照片存储设置 photo_storage_set
  B.   视频存储设置 video_storage_set
```

Look At 参数：`locked`（是否锁定机头与云台相对关系）、`latitude`（-90~90）、`longitude`（-180~180）、`height`（2~10000 米）。

---

### `demo_14_target_detection.py` -- 目标识别（YOOX 扩展）

开启/关闭目标识别，并接收识别结果。

```bash
./run.sh demo_14_target_detection.py
```

---

### `demo_15_emergency.py` -- 应急处置（返航 / 急停 / 紧急降落 / 强制降落）

把飞行安全相关的指令集中在一个脚本里，紧急情况下一键触发。

```bash
./run.sh demo_15_emergency.py
```

```
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
```

**通道说明：**

| 指令 | 通道 | 地址 | 是否需要 DRC 模式 |
|---|---|---|:---:|
| `return_home` | HTTP | `POST /control/api/v1/devices/{sn}/jobs/return_home` | 否 |
| `return_home_cancel` | HTTP | `POST /control/api/v1/devices/{sn}/jobs/return_home_cancel` | 否 |
| `drone_emergency_stop` | MQTT | `thing/product/{sn}/drc/down` | 是 |
| `drc_emergency_landing` | MQTT | `thing/product/{sn}/drc/down` | 是 |
| `drc_force_landing` | MQTT | `thing/product/{sn}/drc/down` | 是 |

MQTT 指令下发格式（`data` 均为 `{}`）：

```json
{
  "tid": "...",
  "bid": "...",
  "timestamp": 1730000000000,
  "method": "drc_emergency_landing",
  "data": {}
}
```

回复在 `thing/product/{sn}/services_reply`，`method` 与下发一致，`data.result == 0` 表示成功，非 0 表示失败。

脚本同时订阅 `thing/product/{sn}/events`，收到 `joystick_invalid_notify` 时会提醒手动操控已不可用。

> **紧急降落 vs 强制降落**
>
> | | `drc_emergency_landing` | `drc_force_landing` |
> |---|---|---|
> | 避障 | 会避障 | 不避障 |
> | 降落点 | 识别二维码降落点 | 原地垂直下降 |
> | 适用 | 常规应急降落 | 避障失效/必须立即落地 |
>
> **两者是独立逻辑，同一次处置中只能选其一，不要混用**，否则降落行为不可预期。
>
> 急停 `drone_emergency_stop` 只刹停悬停，**不会降落**，通常用于先稳住飞机再决定后续动作。

---

## 推荐执行顺序

```
1. demo_01  验证服务可达，拿到 token
2. demo_02  获取设备 SN 和 payload_index，填入 config.py
3. demo_03  开一个单独终端实时监听 WebSocket 推送（全程保持）
4. demo_04  MQTT 原始 OSD 监听（可选，数据更完整）
5. demo_09  通过菜单执行返航、重启等设备控制
6. demo_10  一键起飞到目标点（或由飞手手动起飞）
7. demo_05  调整变焦
8. demo_06  控制云台方向
9. demo_07  拍照或录像
10. demo_08 飞向另一坐标
11. demo_11 直播推流
12. demo_12 DRC 指令飞行（摇杆控制）
13. demo_13 Look At / 画面拖动等高级负载控制
14. demo_14 目标识别
15. demo_16 Look At（GPS 指向，独立脚本）
16. demo_17 航线任务全流程（下发/执行/暂停/恢复/取消/进度上报）

全程备用：demo_15 应急处置（返航 / 急停 / 紧急降落 / 强制降落）
```

---

## 常见错误

| 错误信息 | 原因 | 解决方法 |
|---|---|---|
| `ModuleNotFoundError: No module named 'requests'` | 未激活虚拟环境或未安装依赖 | 改用 `./run.sh` 或先 `source .venv/bin/activate` |
| `externally-managed-environment` | 直接用系统 pip 安装 | 必须用 `python3 -m venv .venv` 建虚拟环境 |
| `Connection refused` | 服务未启动或 IP 填错 | 检查 Docker 容器状态和 `config.py` 中的 `SERVER_IP` |
| `invalid username` | 账号不存在 | 默认账号为 `admin`（Web）或 `pilot`（App） |
| `The account type does not match.` | flag 和账号类型不符 | admin 用 flag=1，pilot 用 flag=2 |
| `The dock is offline` | 设备未上线 | 检查设备 MQTT 连接，确认设备 SN 填写正确 |
| `The current state does not support this function` | 设备状态不满足 | 查看 demo_03 的 OSD 确认当前 mode_code |

---

## 文件结构

```
docs/python-demo/
├── config.py                      # ← 必须先修改这个
├── run.sh                         # 一键运行脚本（自动管理 venv）
├── requirements.txt               # 依赖声明（requests / websocket-client / paho-mqtt）
├── .venv/                         # 虚拟环境（自动创建，已 gitignore）
│
├── ── Cloud-API 通用（原版可用） ──
├── demo_01_login.py               # 登录验证
├── demo_02_devices.py             # 设备列表和直播能力
├── demo_03_websocket_osd.py       # 实时遥测监听（OSD/进度/目标识别/DRC事件）
├── demo_04_mqtt_osd.py            # MQTT 原始 OSD 数据监听（比 WebSocket 更完整）
├── demo_05_gimbal_zoom.py         # 云台变焦（camera_focal_length_set）
├── demo_06_gimbal_pitch.py        # 云台方向（camera_aim 屏幕坐标 + gimbal_reset）
├── demo_07_camera.py              # 拍照/录像（photo_take / recording）
├── demo_08_fly_to_point.py        # 飞向目标点（抢控制权 + 完整进度监听）
├── demo_09_dock_control.py        # 设备控制菜单（返航/重启等）
├── demo_10_takeoff_to_point.py    # 一键起飞到目标点
├── demo_11_livestream.py          # 直播全流程（开始/停止/清晰度/切镜头）
├── demo_12_drc.py                 # DRC 指令飞行（连接->进入->MQTT摇杆/应急->退出）
├── demo_15_emergency.py           # 应急处置（返航/急停/紧急降落/强制降落）
├── demo_16_look_at.py             # 负载 Look At（抢负载控制权 + camera_look_at）
├── demo_17_wayline.py             # 航线任务全流程（下发/执行/暂停/恢复/取消/进度）
│
├── ── YOOX Cloud GCS 扩展接口 ──
├── demo_13_payload_advanced.py    # 画面拖动/连续变焦/Look At/存储设置
└── demo_14_target_detection.py    # 目标识别（开启/关闭/结果接收）
```

### Cloud-API vs YOOX Cloud GCS 接口对比

| 功能 | 指令/接口 | Cloud-API | YOOX |
|---|---|:---:|:---:|
| 变焦（精确值） | `camera_focal_length_set` | ✅ | ✅ |
| 画面拖动（连续转速） | `camera_screen_drag` | ❌ | ✅ |
| 连续变焦（放大/缩小/停止） | `camera_focal_length_drag` | ❌ | ✅ |
| 屏幕坐标指点 | `camera_aim` | ✅ | ✅ |
| Look At（GPS指向） | `camera_look_at` | ✅ | ✅ |
| 照片存储镜头设置 | `photo_storage_set` | ❌ | ✅ |
| 视频存储镜头设置 | `video_storage_set` | ❌ | ✅ |
| 目标识别开启/关闭 | `POST/DELETE .../target-detection` | ❌ | ✅ |
| DRC 指令飞行 | `drc/connect` + `drc/enter` + MQTT | ✅ | ✅ |
| 飞行控制权抢夺 | `flight_authority_grab` | ✅ | ✅ |
| 负载控制权抢夺 | `POST .../authority/payload` | ✅ | ✅ |
| 一键返航 / 取消返航 | `jobs/return_home(_cancel)` | ✅ | ✅ |
| 急停（刹停悬停） | `drone_emergency_stop` | ✅ | ✅ |
| 紧急降落（避障+二维码） | `drc_emergency_landing` | ❌ | ✅ |
| 强制降落（不避障） | `drc_force_landing` | ❌ | ✅ |
| 直播全流程 | `/live/streams/*` | ✅ | ✅ |
