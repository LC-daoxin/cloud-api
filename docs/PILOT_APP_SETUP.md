# Pilot / App 接入配置说明

本文档面向无人机飞手和集成测试人员，说明如何将 Autel Pilot App 或自定义 App 接入本云平台。

---

## 1. 前提条件

| 项目 | 要求 |
|---|---|
| 云平台服务 | 正常运行，Docker 容器全部健康 |
| 网络 | 遥控器 / 手机与服务器在**同一局域网**，或通过公网可达 |
| Pilot App | Autel Pilot 或兼容本 Cloud API 协议的 App |

验证服务是否正常：

```bash
curl -sS http://<服务器IP>:9000/manage/api/v1/login \
  -X POST -H 'Content-Type: application/json' \
  -d '{"username":"pilot","password":"pilot123","flag":2}'
# 返回 "code":0 说明服务正常
```

---

## 2. 账号说明

系统内置两套账号，用途严格区分：

| 账号 | 密码 | 类型 (`flag`) | 使用场景 |
|---|---|---|---|
| `adminPC` | `adminPC` | `1` = Web 端 | 管理平台、API 调试、Python 脚本 |
| `pilot` | `pilot123` | `2` = Pilot/App 端 | **遥控器上的 Pilot App 接入** |

> **Pilot App 必须使用 `pilot` 账号（flag=2），使用 `adminPC` 会返回 `The account type does not match.` 错误。**

账号信息存储于数据库 `manage_user` 表，如需修改密码：

```sql
UPDATE manage_user SET password = '新密码' WHERE username = 'pilot';
```

---

## 3. Pilot App 配置页填写

以下地址假设服务器局域网 IP 为 `172.20.10.8`，**按实际 IP 替换**。

### 3.1 必填字段一览

| 配置项 | 填写值 | 备注 |
|---|---|---|
| **云服务器地址 / 登录地址** | `http://172.20.10.8:9000/manage/api/v1/login` | 完整登录接口路径 |
| **账号** | `pilot` | ⚠️ 不能填 `admin` 或 `adminPC` |
| **密码** | `pilot123` | 初始密码，生产环境应修改 |
| **WebSocket 地址** | `ws://172.20.10.8:9000/api/v1/ws` | ⚠️ 不要在此处手动添加 token |
| **MQTT 地址** | `mqtt://172.20.10.8:1883` | TCP 明文连接 |
| **MQTT 账号** | `pilot` | 登录成功后接口返回 `mqtt_username` |
| **MQTT 密码** | `pilot123` | 登录成功后接口返回 `mqtt_password` |

### 3.2 字段说明

**云服务器地址/登录地址**
App 启动后会向此接口发送 POST 请求完成认证，格式固定为：
```
http://<服务器IP>:9000/manage/api/v1/login
```

**WebSocket 地址**
App 填入基础地址即可，**无需手动拼接 token**。App 登录成功获取 token 后，会自动将其追加为 URL 参数再发起连接：
```
ws://172.20.10.8:9000/api/v1/ws?x-auth-token=<登录后自动获取>
```

**MQTT 地址/账号/密码**
- 地址格式：`mqtt://IP:1883`（TCP 明文）或 `ws://IP:9001/mqtt`（WebSocket）
- App 中填写的 MQTT 账号密码，须与数据库 `mqtt_username`/`mqtt_password` 字段一致
- 登录接口返回值中的 `mqtt_username`/`mqtt_password` 即为 App 应使用的 MQTT 凭证

### 3.3 登录接口完整响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "username": "pilot",
    "user_id": "be7c6c3d-afe9-4be4-b9eb-c55066c0914e",
    "workspace_id": "e3dea0f5-37f2-4d79-ae58-490af3228069",
    "user_type": 2,
    "mqtt_username": "pilot",
    "mqtt_password": "pilot123",
    "mqtt_addr": "tcp://172.20.10.8:1883",
    "access_token": "eyJ0eXAi..."
  }
}
```

App 会从此响应中取出：
- `access_token` → 后续所有 HTTP 请求的鉴权 Header：`x-auth-token: <token>`
- `access_token` → WebSocket 连接 URL 参数
- `mqtt_addr` + `mqtt_username` + `mqtt_password` → MQTT 连接

---

## 4. 端口说明

| 服务 | 端口 | 用途 |
|---|---|---|
| HTTP / WebSocket | `9000` | 所有 REST API + WebSocket 推送 |
| MQTT TCP | `1883` | 设备与云平台双向消息通信 |
| MQTT WebSocket | `9001` | 通过 WebSocket 协议连接 MQTT（DRC 低时延控制用） |
| MinIO 对象存储 | `9100` | 航线、媒体、固件、日志文件存取 |
| MinIO 控制台 | `9101` | 存储后台管理页面（内部使用） |

> 确保以上端口在网络防火墙上对 App 设备开放。

---

## 5. 连接流程

```
Pilot App 启动
    │
    ├─ 1. POST /manage/api/v1/login
    │       body: {username, password, flag:2}
    │       → 获取 access_token、mqtt_addr、mqtt_username/password
    │
    ├─ 2. 连接 WebSocket
    │       ws://IP:9000/api/v1/ws?x-auth-token=<token>
    │       → 接收设备拓扑、OSD 遥测、任务进度等推送
    │
    ├─ 3. 连接 MQTT Broker
    │       mqtt://IP:1883，账号 pilot/pilot123
    │       → 设备消息上行/下行通道
    │
    └─ 4. GET /manage/api/v1/workspaces/{workspace_id}/devices/topologies
            → 首次拉取当前在线设备拓扑
```

---

## 6. 常见问题

### Q1：连接时显示"账号类型不匹配"
**原因**：填写了 `adminPC` 账号（Web 端账号），Pilot App 必须用 `flag=2` 的 pilot 账号。
**解决**：账号改为 `pilot`，密码 `pilot123`。

### Q2：MQTT 连接失败，HTTP 连接成功
**原因**：MQTT 地址填写错误，或填了 `mqtt` 容器名（外部网络无法解析）。
**解决**：MQTT 地址填服务器的**局域网 IP**：`mqtt://172.20.10.8:1883`。

### Q3：WebSocket 连接失败
**原因**：
- WebSocket 地址填错（多了 `/api/v1/ws?x-auth-token=<token>` 中的 token）
- 或网络防火墙拦截了 9000 端口的 WebSocket Upgrade 请求
**解决**：WebSocket 地址只填 `ws://172.20.10.8:9000/api/v1/ws`，token 由 App 自动追加。

### Q4：设备绑定后没有出现在 App 地图上
**原因**：设备 SN 未绑定到工作空间，或设备 MQTT 通道未正常上线。
**解决**：
1. 确认设备通过 MQTT 发送了 `sys/product/{sn}/status` 上线消息
2. 检查云平台日志是否收到 `update_topo` 事件
3. 通过 API 确认设备绑定状态：`GET /manage/api/v1/devices/{workspace_id}/devices`

### Q5：App 填写了正确配置但仍然连接失败
逐项排查：

```bash
# 1. 验证 HTTP 服务是否可达
curl http://172.20.10.8:9000/manage/api/v1/login \
  -X POST -H 'Content-Type: application/json' \
  -d '{"username":"pilot","password":"pilot123","flag":2}'

# 2. 验证 MQTT 端口是否可达（需安装 mosquitto-clients）
mosquitto_pub -h 172.20.10.8 -p 1883 -t test -m ping

# 3. 验证所有容器健康
docker compose ps
```

---

## 7. 工作空间绑定码

设备首次接入需要工作空间绑定码（Bind Code），默认初始化值为 `qwe`。

| 字段 | 值 |
|---|---|
| 工作空间名称 | Test Group One |
| 工作空间 ID | `e3dea0f5-37f2-4d79-ae58-490af3228069` |
| 绑定码 | `qwe` |

> 生产环境部署前应修改绑定码，防止未授权设备接入：
> ```sql
> UPDATE manage_workspace SET bind_code = '新绑定码' WHERE id = 1;
> ```

---

## 8. 安全提示

以下为本 Demo 环境的已知安全问题，**生产环境上线前必须处理**：

| 风险项 | 说明 | 处理方式 |
|---|---|---|
| 密码明文存储 | 数据库中密码未加密 | 改造登录逻辑，引入密码哈希（如 BCrypt）|
| 弱 JWT Secret | 当前 secret 为固定字符串 | 修改 `jwt.secret` 为足够长的随机值 |
| MQTT 匿名访问 | Mosquitto 当前允许匿名 | 关闭匿名，启用密码文件或 ACL |
| 绑定码过弱 | 默认绑定码为 `qwe` | 修改为强随机字符串 |
| WebSocket 跨域 | 当前允许任意 Origin | 限制可信 Origin |
