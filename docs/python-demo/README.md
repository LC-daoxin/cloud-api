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
| `websocket-client` | WebSocket 实时推送（demo_07） |

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
    1. 运行 demo_07_websocket_osd.py
    2. 查看推送的 OSD 消息中 payloads[].payload_index 字段
    3. 格式为 "domain-type-subtype"，如 "1-10052-0"
```

---

### `demo_03_gimbal_zoom.py` —— 云台变焦

设置相机变焦倍率（2.0 ～ 200.0）。

**前提条件：**
- `config.py` 中已填入 `DOCK_SN` 和 `PAYLOAD_INDEX`
- 无人机已上线，相机处于 IDLE 状态

**修改变焦倍率**（在文件顶部）：

```python
ZOOM_FACTOR = 5.0   # 改为目标倍率，范围 2.0 ~ 200.0
```

```bash
./run.sh demo_03_gimbal_zoom.py
```

**预期输出：**
```
[✓] 已获取负载控制权
[✓] 变焦成功，当前倍率: 5.0x
```

---

### `demo_04_gimbal_pitch.py` —— 云台方向控制（交互式）

`camera_aim` 是**屏幕坐标指点**接口（不是连续转速控制）：
- `x/y` 为 0.0~1.0 的归一化屏幕坐标，`y=0.0` 指向画面上方（仰角），`y=1.0` 指向画面下方（俯角）
- 同时支持 `gimbal_reset` 直接复位到预设角度

```bash
./run.sh demo_04_gimbal_pitch.py
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
  自定义  → x=0.3,y=0.7

输入指令: down
  [✓] 指向下方

输入指令: x=0.2,y=0.8
  [✓] 自定义坐标
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

### `demo_05_camera.py` —— 相机控制

**拍照：**
```bash
./run.sh demo_05_camera.py photo
```

**开始录像：**
```bash
./run.sh demo_05_camera.py rec_start
```

**停止录像：**
```bash
./run.sh demo_05_camera.py rec_stop
```

**执行流程：**
1. 自动抢占负载控制权
2. 切换相机模式（拍照→模式0，录像→模式1）
3. 发送对应指令

---

### `demo_06_fly_to_point.py` —— 飞向目标坐标（飞行中）

**前提：无人机已在空中，处于 MANUAL 模式。**

修改文件顶部的目标坐标：

```python
TARGET_LATITUDE  = 22.5431    # 目标纬度
TARGET_LONGITUDE = 113.9213   # 目标经度
TARGET_HEIGHT    = 50.0       # 目标高度（米）
MAX_SPEED        = 5          # 最大速度 1~15 m/s
```

```bash
./run.sh demo_06_fly_to_point.py
```

飞行进度通过 WebSocket 实时推送（bizCode: `fly_to_point_progress`），可同时运行 `demo_07` 监听。

---

### `demo_07_websocket_osd.py` —— 实时遥测数据监听

订阅 WebSocket，实时打印飞机位置、高度、电量、速度等遥测数据，以及设备上下线事件。

```bash
./run.sh demo_07_websocket_osd.py
```

**实时输出示例：**
```
[✓] WebSocket 已连接，等待推送数据...

[OSD-无人机] lat=22.543100 lon=113.921300 h=50.0m spd=5.0m/s bat=85% mode=MANUAL
[OSD-机巢]   mode=IDLE cover=closed
[事件] 设备上线: {...}
[进度] fly_to_point_progress: {"status": "running", "progress": 60}
```

按 `Ctrl+C` 退出。

---

### `demo_08_dock_control.py` —— 机巢远程控制（菜单式）

交互菜单控制机巢硬件。

```bash
./run.sh demo_08_dock_control.py
```

```
机巢控制菜单：
   1. 开舱盖
   2. 关舱盖
   3. 开无人机电源
   4. 关无人机电源
   5. 执行返航
   6. 取消返航
   7. 重启机巢
   8. 开始充电
   ...
选择操作编号: 1
[✓] 开舱盖 成功
```

---

### `demo_09_takeoff_to_point.py` —— 机巢起飞到目标坐标

**前提：无人机在机巢内，机巢处于 IDLE 状态。**

修改文件顶部参数：

```python
TARGET_LATITUDE         = 22.5431
TARGET_LONGITUDE        = 113.9213
TARGET_HEIGHT           = 50.0     # 目标高度（米）
SECURITY_TAKEOFF_HEIGHT = 20.0    # 安全起飞高度（米）
RTH_ALTITUDE            = 100.0   # 返航高度（米）
```

```bash
./run.sh demo_09_takeoff_to_point.py
```

执行前需要输入 `yes` 确认，防止误操作。

---

## 推荐执行顺序

```
1. demo_01  验证服务可达，拿到 token
2. demo_02  获取设备 SN 和 payload_index，填入 config.py
3. demo_07  开一个单独终端实时监听推送（全程保持）
4. demo_08  通过菜单开舱盖、开飞机电源
5. demo_09  起飞到目标点（或由飞手手动起飞）
6. demo_03  调整变焦
7. demo_04  控制云台方向
8. demo_05  拍照或录像
9. demo_06  飞向另一坐标
```

---

## 常见错误

| 错误信息 | 原因 | 解决方法 |
|---|---|---|
| `ModuleNotFoundError: No module named 'requests'` | 未激活虚拟环境或未安装依赖 | 改用 `./run.sh` 或先 `source .venv/bin/activate` |
| `externally-managed-environment` | 直接用系统 pip 安装 | 必须用 `python3 -m venv .venv` 建虚拟环境 |
| `Connection refused` | 服务未启动或 IP 填错 | 检查 Docker 容器状态和 `config.py` 中的 `SERVER_IP` |
| `invalid username` | 账号不存在 | 默认账号为 `adminPC`（Web）或 `pilot`（App） |
| `The account type does not match.` | flag 和账号类型不符 | adminPC 用 flag=1，pilot 用 flag=2 |
| `The dock is offline` | 机巢未上线 | 检查机巢 MQTT 连接，确认设备 SN 填写正确 |
| `The current state does not support this function` | 设备状态不满足 | 查看 demo_07 的 OSD 确认当前 mode_code |

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
├── demo_03_gimbal_zoom.py         # 云台变焦（camera_focal_length_set）
├── demo_04_gimbal_pitch.py        # 云台方向（camera_aim 屏幕坐标 + gimbal_reset）
├── demo_05_camera.py              # 拍照/录像（photo_take / recording）
├── demo_06_fly_to_point.py        # 飞向目标点（fly-to-point，飞行中）
├── demo_07_websocket_osd.py       # 实时遥测监听（OSD/进度/目标识别/DRC事件）
├── demo_08_dock_control.py        # 机巢控制菜单（舱盖/返航/充电等）
├── demo_09_takeoff_to_point.py    # 机巢起飞到目标点
├── demo_10_livestream.py          # 直播全流程（开始/停止/清晰度/切镜头）
├── demo_11_drc.py                 # DRC 指令飞行（连接→进入→MQTT摇杆→退出）
│
├── ── YOOX Cloud GCS 扩展接口 ──
├── demo_12_payload_advanced.py    # 画面拖动/连续变焦/Look At/存储设置
└── demo_13_target_detection.py    # 目标识别（开启/关闭/结果接收）
```

### Cloud-API vs YOOX Cloud GCS 接口对比

| 功能 | 指令/接口 | Cloud-API | YOOX |
|---|---|:---:|:---:|
| 变焦（精确值） | `camera_focal_length_set` | ✅ | ✅ |
| 画面拖动（连续转速） | `camera_screen_drag` | ❌ | ✅ |
| 连续变焦（放大/缩小/停止） | `camera_focal_length_drag` | ❌ | ✅ |
| 屏幕坐标指点 | `camera_aim` | ✅ | ✅ |
| Look At（GPS指向） | `camera_look_at` | ❌ | ✅ |
| 照片存储镜头设置 | `photo_storage_set` | ❌ | ✅ |
| 视频存储镜头设置 | `video_storage_set` | ❌ | ✅ |
| 目标识别开启/关闭 | `POST/DELETE .../target-detection` | ❌ | ✅ |
| DRC 指令飞行 | `drc/connect` + `drc/enter` + MQTT | ✅ | ✅ |
| 直播全流程 | `/live/streams/*` | ✅ | ✅ |
