# Cloud API 全量调用指南

> 适用代码版本：以当前仓库源码为准（2026-08-04 扫描）  
> 默认服务地址：`http://localhost:9000`  
> HTTP 路由总数：76（含 2 个仅用于开发的测试接口）

## 1. 文档范围

本文档覆盖当前项目全部对外 HTTP 路由，并补充 WebSocket 推送的连接与消息格式。HTTP 接口来自两类定义：

1. `cloud-service` 中 Controller 直接声明的路由；
2. Controller 从 `cloud-api` 的 `IHttp*Service` 接口继承的路由。

项目与无人机、遥控器、机巢之间的大量 MQTT Topic 属于设备协议通道，并不是调用方可直接访问的 HTTP API。本文在末尾说明其关系，但不把每个 MQTT `method` 重复列为 REST 接口。

## 2. 调用约定

### 2.1 Base URL 与模块前缀

默认端口来自 `cloud-service/src/main/resources/application.yml`：

```text
http://localhost:9000
```

| 模块 | 路由前缀 |
|---|---|
| 管理、用户、设备、直播 | `/manage/api/v1` |
| 地图、飞行区域 | `/map/api/v1` |
| 媒体 | `/media/api/v1` |
| 航线、飞行任务 | `/wayline/api/v1` |
| 对象存储 | `/storage/api/v1` |
| 设备控制、DRC | `/control/api/v1` |

本文用以下占位符：

```bash
BASE_URL=http://localhost:9000
TOKEN='<登录返回的 token>'
WORKSPACE_ID='<workspace UUID>'
```

### 2.2 鉴权

除下列路由外，所有请求都必须携带请求头 `x-auth-token`：

- `POST /manage/api/v1/login`
- `POST /manage/api/v1/token/refresh`
- `/swagger-ui/**`、`/v3/**`、`/ui/**`
- `/test/**`

调用模板：

```bash
curl -X GET "$BASE_URL/manage/api/v1/users/current" \
  -H "x-auth-token: $TOKEN"
```

缺少或无法解析 token 时，服务返回 HTTP `401`。业务失败通常仍使用统一 JSON 响应，调用方必须同时检查 HTTP 状态码和 JSON `code`。

### 2.3 统一响应

普通接口返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | integer | `0` 成功；非 `0` 失败。通用失败通常为 `-1`，设备/MQTT 错误可能返回协议错误码 |
| `message` | string | `success`、`failed` 或具体错误信息 |
| `data` | any | 业务数据；无数据时成功响应通常为 `""` |

分页接口的 `data` 结构：

```json
{
  "list": [],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total": 0
  }
}
```

下载类接口是例外：媒体文件和航线文件下载会返回 HTTP `302`，跳转到对象存储的临时 URL。

### 2.4 请求格式

- JSON：`Content-Type: application/json`
- 文件上传：`multipart/form-data`
- 时间戳：除特别说明外为 Unix 毫秒
- UUID：工作空间、地图元素、航线、任务等 ID 通常为 UUID 字符串
- 字段名以源码实际 Jackson 映射为准；本文保留 `snake_case` 与 `camelCase` 的真实差异

### 2.5 Swagger

服务成功启动后可访问：

- Swagger UI：`http://localhost:9000/swagger-ui/index.html`
- OpenAPI JSON：`http://localhost:9000/v3/api-docs`

Swagger 是辅助入口；部分继承路由、业务约束和实现状态仍应以本文与源码为准。

## 3. 快速调用流程

### 3.1 登录并取得上下文

```bash
curl -X POST "$BASE_URL/manage/api/v1/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"pilot","password":"pilot123","flag":2}'
```

登录成功后的 `data` 为 `UserDTO`，主要字段为 `user_id`、`username`、`workspace_id`、`user_type`、`mqtt_username`、`mqtt_password`、`access_token`、`mqtt_addr`。后续 HTTP 请求使用 `access_token`。然后建议依次调用：

```bash
curl "$BASE_URL/manage/api/v1/users/current" -H "x-auth-token: $TOKEN"
curl "$BASE_URL/manage/api/v1/workspaces/current" -H "x-auth-token: $TOKEN"
curl "$BASE_URL/manage/api/v1/workspaces/$WORKSPACE_ID/devices/topologies" -H "x-auth-token: $TOKEN"
```

### 3.2 通用 JSON 请求

```bash
curl -X POST "$BASE_URL/<path>" \
  -H "x-auth-token: $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '<JSON body>'
```

### 3.3 文件上传

```bash
curl -X POST "$BASE_URL/<upload-path>" \
  -H "x-auth-token: $TOKEN" \
  -F 'file=@/absolute/path/to/file.kmz'
```

## 4. 管理与身份 API（7 个）

### 4.1 接口清单

| 方法 | 路径 | 请求 | 说明 |
|---|---|---|---|
| POST | `/manage/api/v1/login` | JSON `UserLoginDTO` | 登录，免鉴权 |
| POST | `/manage/api/v1/token/refresh` | Header `x-auth-token` | 刷新 token，拦截器层面免鉴权但方法自行校验旧 token |
| GET | `/manage/api/v1/users/current` | 无 | 当前用户信息 |
| PUT | `/manage/api/v1/users/current/password` | JSON `ChangePasswordParam` | 修改当前用户密码 |
| GET | `/manage/api/v1/users/{workspace_id}/users` | Query `page=1&page_size=50` | 工作空间用户分页列表 |
| PUT | `/manage/api/v1/users/{workspace_id}/users/{user_id}` | JSON `UserListDTO` | 更新用户信息 |
| GET | `/manage/api/v1/workspaces/current` | 无 | 当前工作空间信息 |

### 4.2 登录请求

| 字段 | 类型 | 必填 | 说明 |
|---|---:|:---:|---|
| `username` | string | 是 | 用户名 |
| `password` | string | 是 | 密码 |
| `flag` | integer | 是 | 必须与账号类型一致：`1` Web，`2` Pilot |

```bash
curl -X POST "$BASE_URL/manage/api/v1/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"pilot","password":"pilot123","flag":2}'
```

### 4.3 修改当前用户密码

新密码长度为 12–72 位，且必须同时包含大写字母、小写字母、数字和特殊字符。

```bash
curl -X PUT "$BASE_URL/manage/api/v1/users/current/password" \
  -H "x-auth-token: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"old_password":"当前密码","new_password":"Example@Strong2026"}'
```

### 4.4 更新用户请求

`UserListDTO` 可接受字段为 `userId`、`username`、`workspaceName`、`userType`、`mqttUsername`、`mqttPassword`、`createTime`。实际更新时应只提交服务允许修改的字段，例如：

```bash
curl -X PUT "$BASE_URL/manage/api/v1/users/$WORKSPACE_ID/users/<user_id>" \
  -H "x-auth-token: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"mqttUsername":"pilot-mqtt","mqttPassword":"new-password"}'
```

## 5. 设备、拓扑与固件 API（16 个）

### 5.1 接口清单

| 方法 | 路径 | 请求 | 说明 |
|---|---|---|---|
| GET | `/manage/api/v1/workspaces/{workspace_id}/devices/topologies` | 无 | Pilot/前端获取完整设备拓扑 |
| GET | `/manage/api/v1/devices/{workspace_id}/devices` | 无 | Web 端设备拓扑列表；注意路径中 `devices` 出现两次 |
| POST | `/manage/api/v1/devices/{device_sn}/binding` | JSON `DeviceDTO` | 绑定设备 |
| GET | `/manage/api/v1/devices/{workspace_id}/devices/{device_sn}` | 无 | 查询单台设备 |
| GET | `/manage/api/v1/devices/{workspace_id}/devices/bound` | Query `domain&page&page_size` | 分页查询已绑定设备 |
| DELETE | `/manage/api/v1/devices/{device_sn}/unbinding` | 无 | 解绑设备 |
| PUT | `/manage/api/v1/devices/{workspace_id}/devices/{device_sn}` | JSON `DeviceDTO` | 更新设备 |
| POST | `/manage/api/v1/devices/{workspace_id}/devices/ota` | JSON 数组 | 创建 OTA 任务 |
| PUT | `/manage/api/v1/devices/{workspace_id}/devices/{device_sn}/property` | 单字段 JSON | 设置一项设备属性 |
| GET | `/manage/api/v1/workspaces/firmware-release-notes/latest` | Query `device_name`（可重复） | 查询各设备型号的最新固件说明 |
| GET | `/manage/api/v1/workspaces/{workspace_id}/firmwares` | Query `DeviceFirmwareQueryParam` | 固件分页列表 |
| POST | `/manage/api/v1/workspaces/{workspace_id}/firmwares/file/upload` | multipart | 上传固件包 |
| PUT | `/manage/api/v1/workspaces/{workspace_id}/firmwares/{firmware_id}` | JSON | 启用/禁用固件 |
| GET | `/manage/api/v1/devices/{workspace_id}/devices/hms` | Query `DeviceHmsQueryParam` | HMS 告警分页查询 |
| PUT | `/manage/api/v1/devices/{workspace_id}/devices/hms/{device_sn}` | 无 | 将设备 HMS 标记为已读 |
| GET | `/manage/api/v1/devices/{workspace_id}/devices/hms/{device_sn}` | 无 | 获取设备未读 HMS |

### 5.2 绑定与更新设备

`DeviceDTO` 主要字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `deviceSn` | string | 由路径覆盖，无需在 body 重复提交 |
| `deviceName` | string | 设备名称 |
| `workspaceId` | string | 绑定目标工作空间；绑定接口必须确保该值正确 |
| `deviceDesc` | string | 描述 |
| `nickname` | string | 昵称 |
| `controlSource` | enum | 控制来源 |
| `domain`、`type`、`subType` | enum | 设备域、类型和子类型 |
| `childDeviceSn`、`parentSn` | string | 父子设备关系 |

```bash
curl -X POST "$BASE_URL/manage/api/v1/devices/<device_sn>/binding" \
  -H "x-auth-token: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"workspaceId":"'"$WORKSPACE_ID"'","deviceName":"Dock A","nickname":"一号机巢"}'
```

### 5.3 分页查询已绑定设备

```bash
curl "$BASE_URL/manage/api/v1/devices/$WORKSPACE_ID/devices/bound?domain=3&page=1&page_size=50" \
  -H "x-auth-token: $TOKEN"
```

`domain` 对应设备域枚举；不传时查询全部域。

### 5.4 OTA

请求体为数组：

```json
[
  {
    "deviceName": "dock-model",
    "sn": "DOCK_SN",
    "productVersion": "01.02.0300",
    "firmwareUpgradeType": 0
  }
]
```

```bash
curl -X POST "$BASE_URL/manage/api/v1/devices/$WORKSPACE_ID/devices/ota" \
  -H "x-auth-token: $TOKEN" -H 'Content-Type: application/json' \
  -d @ota.json
```

### 5.5 设置设备属性

请求体必须且只能包含一个属性，否则返回参数错误：

```bash
curl -X PUT "$BASE_URL/manage/api/v1/devices/$WORKSPACE_ID/devices/<dock_sn>/property" \
  -H "x-auth-token: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"night_lights_state":1}'
```

属性名称和值必须是目标设备物模型支持的属性。服务会通过 MQTT 同步下发并返回设备应答结果。

### 5.6 固件查询与上传

固件列表 Query：

| 参数 | 类型 | 必填 | 说明 |
|---|---:|:---:|---|
| `device_name` | string | 否 | 设备型号 |
| `product_version` | string | 否 | 固件版本 |
| `status` | boolean | 否 | 启用状态 |
| `page` | long | 是 | 页码 |
| `page_size` | long | 是 | 每页数量 |

固件上传使用 multipart，且文件名必须以 `.uav`（Controller 实际校验的 `FIRMWARE_UAV_FILE_SUFFIX`）结尾：

```bash
curl -X POST "$BASE_URL/manage/api/v1/workspaces/$WORKSPACE_ID/firmwares/file/upload" \
  -H "x-auth-token: $TOKEN" \
  -F 'file=@/absolute/path/firmware.uav' \
  -F 'release_note=稳定性优化' \
  -F 'status=true' \
  -F 'device_name=dock-model'
```

启用/禁用固件：

```json
{"status": true}
```

### 5.7 HMS 查询参数

| 参数 | 类型 | 说明 |
|---|---|---|
| `device_sn` | string，可重复 | 设备 SN 集合 |
| `begin_time`、`end_time` | long | 时间范围（毫秒） |
| `language` | string | 语言 |
| `message` | string | 告警内容筛选 |
| `level` | integer | 告警等级 |
| `update_time` | long | 增量更新时间 |
| `page`、`page_size` | long | 分页参数 |

## 6. 设备日志 API（6 个）

| 方法 | 路径 | 请求 | 说明 |
|---|---|---|---|
| GET | `/manage/api/v1/workspaces/{workspace_id}/devices/{device_sn}/logs-uploaded` | Query | 已上传日志分页列表 |
| GET | `/manage/api/v1/workspaces/{workspace_id}/devices/{device_sn}/logs` | Query `domain_list` | 向设备查询可上传日志 |
| POST | `/manage/api/v1/workspaces/{workspace_id}/devices/{device_sn}/logs` | JSON | 发起日志上传 |
| DELETE | `/manage/api/v1/workspaces/{workspace_id}/devices/{device_sn}/logs` | JSON | 取消设备日志上传 |
| DELETE | `/manage/api/v1/workspaces/{workspace_id}/devices/{device_sn}/logs/{logs_id}` | 无 | 删除日志记录及相关文件 |
| GET | `/manage/api/v1/workspaces/{workspace_id}/logs/{logs_id}/url/{file_id}` | 无 | 获取日志文件临时 URL（URL 字符串封装在统一响应中） |

已上传日志查询参数：`page`、`page_size`、`status`、`begin_time`、`end_time`、`logs_information`。

日志模块枚举：`"0"` 为无人机，`"3"` 为机巢。

查询设备实时日志：

```bash
curl "$BASE_URL/manage/api/v1/workspaces/$WORKSPACE_ID/devices/<device_sn>/logs?domain_list=0&domain_list=3" \
  -H "x-auth-token: $TOKEN"
```

发起上传的 body：

```json
{
  "logsInformation": "现场问题排查",
  "happenTime": 1785772800000,
  "files": [
    {
      "deviceSn": "DEVICE_SN",
      "module": "3",
      "objectKey": "logs/DEVICE_SN/log.zip",
      "list": [
        {"bootIndex": 1, "startTime": 1785772700000, "endTime": 1785772800000, "size": 1048576}
      ]
    }
  ]
}
```

取消上传的 body：

```json
{"moduleList":["3"],"status":"cancel"}
```

## 7. 直播 API（5 个）

| 方法 | 路径 | 请求 | 说明 |
|---|---|---|---|
| GET | `/manage/api/v1/live/capacity` | 无 | 查询当前工作空间可直播的视频源 |
| POST | `/manage/api/v1/live/streams/start` | JSON `LiveTypeDTO` | 开始直播 |
| POST | `/manage/api/v1/live/streams/stop` | JSON `LiveTypeDTO` | 停止直播，只使用 `video_id` |
| POST | `/manage/api/v1/live/streams/update` | JSON `LiveTypeDTO` | 修改直播画质 |
| POST | `/manage/api/v1/live/streams/switch` | JSON `LiveTypeDTO` | 切换镜头 |

`LiveTypeDTO`：

| 字段 | 类型/取值 | 说明 |
|---|---|---|
| `url_type` | `0` Agora、`1` RTMP、`2` RTSP、`3` GB28181、`4` WHIP | 推流方式 |
| `video_id` | string | 格式为 `{droneSn}/{payloadIndex}/{videoType}-0`，例如 `SN/89-0-7/normal-0` |
| `video_quality` | `0` 自动、`1` 流畅、`2` 标清、`3` 高清、`4` 超清 | 画质 |
| `videoType` | `zoom`、`wide`、`ir` | 切换后的镜头类型；注意该字段是 camelCase |

开始 RTMP 直播：

```bash
curl -X POST "$BASE_URL/manage/api/v1/live/streams/start" \
  -H "x-auth-token: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"url_type":1,"video_id":"DRONE_SN/89-0-7/normal-0","video_quality":0}'
```

直播 URL、账号和通道参数来自 `application.yml` 的 `livestream.url.*` 配置。

## 8. 地图与飞行区域 API（11 个）

### 8.1 接口清单

| 方法 | 路径 | 请求 | 说明 |
|---|---|---|---|
| GET | `/map/api/v1/workspaces/{workspace_id}/device-status` | 无 | 查询设备飞行区域同步/数据状态 |
| GET | `/map/api/v1/workspaces/{workspace_id}/flight-areas` | 无 | 飞行区域列表 |
| POST | `/map/api/v1/workspaces/{workspace_id}/flight-area` | JSON | 创建飞行区域 |
| DELETE | `/map/api/v1/workspaces/{workspace_id}/flight-area/{area_id}` | 无 | 删除飞行区域 |
| PUT | `/map/api/v1/workspaces/{workspace_id}/flight-area/{area_id}` | JSON | 更新飞行区域 |
| POST | `/map/api/v1/workspaces/{workspace_id}/flight-area/sync` | JSON | 向设备同步飞行区域 |
| GET | `/map/api/v1/workspaces/{workspace_id}/element-groups` | Query `group_id`,`is_distributed` | 查询地图元素组 |
| POST | `/map/api/v1/workspaces/{workspace_id}/element-groups/{group_id}/elements` | JSON | 创建地图元素 |
| DELETE | `/map/api/v1/workspaces/{workspace_id}/element-groups/{group_id}/elements` | 无 | 删除组内全部元素 |
| PUT | `/map/api/v1/workspaces/{workspace_id}/elements/{element_id}` | JSON | 更新地图元素 |
| DELETE | `/map/api/v1/workspaces/{workspace_id}/elements/{element_id}` | 无 | 删除单个地图元素 |

### 8.2 飞行区域请求

创建请求：

```json
{
  "id": "11111111-1111-1111-1111-111111111111",
  "name": "测试限飞区",
  "type": "nfz",
  "content": {
    "properties": {"color": "#FF0000", "clampToGround": true},
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[116.30,39.90],[116.31,39.90],[116.31,39.91],[116.30,39.90]]]
    }
  }
}
```

`type`：`dfence` 为电子围栏，`nfz` 为禁飞区。`geometry.type` 支持 `Circle`、`Point`、`LineString`、`Polygon`，坐标顺序遵循 GeoJSON：经度在前、纬度在后。

更新请求可提交 `name`、`content`、`status`。同步请求：

```json
{"device_sn":["DOCK_SN_1","DOCK_SN_2"]}
```

### 8.3 地图元素请求

创建元素：

```json
{
  "id": "22222222-2222-2222-2222-222222222222",
  "name": "巡检点 A",
  "resource": {
    "type": 0,
    "content": {
      "type": "Feature",
      "properties": {"color":"#2D8CF0","clampToGround":true},
      "geometry": {"type":"Point","coordinates":[116.30,39.90,50.0]}
    }
  }
}
```

`resource.type`：`0` Point、`1` LineString、`2` Polygon。`resource.user_name` 由服务端根据 token 中的用户名覆盖，无需客户端传入。

更新元素：

```json
{
  "name": "巡检点 A-更新",
  "content": {
    "type": "Feature",
    "properties": {"color":"#00AAFF","clampToGround":true},
    "geometry": {"type":"Point","coordinates":[116.31,39.91,50.0]}
  }
}
```

创建、更新或删除元素成功后，服务会通过 WebSocket 向同工作空间推送刷新通知。

## 9. 媒体与对象存储 API（7 个）

| 方法 | 路径 | 请求 | 说明 |
|---|---|---|---|
| GET | `/media/api/v1/files/{workspace_id}/files` | Query `page=1&page_size=10` | 媒体文件分页列表 |
| GET | `/media/api/v1/files/{workspace_id}/file/{file_id}/url` | 无 | 302 跳转到媒体临时下载 URL |
| POST | `/media/api/v1/workspaces/{workspace_id}/fast-upload` | JSON | 根据完整指纹判断是否可秒传 |
| POST | `/media/api/v1/workspaces/{workspace_id}/upload-callback` | JSON | 单个媒体上传完成回调 |
| POST | `/media/api/v1/workspaces/{workspace_id}/files/tiny-fingerprints` | JSON | 批量查询已存在的小指纹 |
| POST | `/media/api/v1/workspaces/{workspace_id}/group-upload-callback` | JSON | 文件组上传进度回调；当前实现直接返回 `null`，不可用于生产 |
| POST | `/storage/api/v1/workspaces/{workspace_id}/sts` | 无 | 获取对象存储临时凭证 |

### 9.1 推荐上传流程

1. 调用 STS 接口获取临时凭证；
2. 可先调用秒传或小指纹查询；
3. 客户端直传文件到配置的 OSS/MinIO/S3；
4. 调用 `upload-callback` 将元数据登记到业务库。

STS：

```bash
curl -X POST "$BASE_URL/storage/api/v1/workspaces/$WORKSPACE_ID/sts" \
  -H "x-auth-token: $TOKEN"
```

### 9.2 秒传

```json
{
  "ext": {
    "drone_model_key": "0-67-0",
    "is_original": true,
    "payload_model_key": "1-53-0",
    "tinny_fingerprint": "tiny_fp",
    "sn": "DRONE_SN"
  },
  "fingerprint": "FULL_MD5_OR_PROTOCOL_FINGERPRINT",
  "name": "DJI_0001.JPG",
  "path": "DJI_20260804_Waypoint1"
}
```

指纹已存在时返回成功；不存在时当前实现返回 `code=-1` 和 `"<fingerprint>don't exist."`。

### 9.3 小指纹查询

```json
{"tiny_fingerprints":["tiny_fp_1","tiny_fp_2"]}
```

返回 `data.tiny_fingerprints`，只包含已存在的值。

### 9.4 单文件上传回调

```json
{
  "ext": {
    "drone_model_key": "0-67-0",
    "file_group_id": "33333333-3333-3333-3333-333333333333",
    "is_original": true,
    "payload_model_key": "1-53-0",
    "tinny_fingerprint": "tiny_fp",
    "sn": "DRONE_SN"
  },
  "fingerprint": "full_fp",
  "name": "DJI_0001.JPG",
  "path": "mission-folder",
  "object_key": "media/DJI_0001.JPG",
  "sub_file_type": 0,
  "metadata": {
    "absolute_altitude": 120.5,
    "created_time": "2026-08-04T12:00:00+08:00",
    "gimbal_yaw_degree": -4.3,
    "shoot_position": {"lat":39.90,"lng":116.30},
    "relative_altitude": 80.0
  }
}
```

成功时返回 `data` 为写入的 `object_key`。

文件组进度 body 为：

```json
{"file_group_id":"<uuid>","file_count":20,"file_uploaded_count":10}
```

但该路由目前尚未实现，应避免调用或先补齐实现。

## 10. 航线与飞行任务 API（13 个）

### 10.1 航线文件（8 个）

| 方法 | 路径 | 请求 | 说明 |
|---|---|---|---|
| GET | `/wayline/api/v1/workspaces/{workspace_id}/waylines` | Query | 航线分页列表 |
| GET | `/wayline/api/v1/workspaces/{workspace_id}/waylines/{wayline_id}/url` | 无 | 302 跳转到 KMZ 临时下载 URL |
| GET | `/wayline/api/v1/workspaces/{workspace_id}/waylines/duplicate-names` | Query `name`（可重复） | 返回已存在的名称 |
| POST | `/wayline/api/v1/workspaces/{workspace_id}/upload-callback` | JSON | 对象存储上传完成回调 |
| POST | `/wayline/api/v1/workspaces/{workspace_id}/favorites` | Query `id`（可重复） | 批量收藏 |
| DELETE | `/wayline/api/v1/workspaces/{workspace_id}/favorites` | Query `id`（可重复） | 批量取消收藏 |
| DELETE | `/wayline/api/v1/workspaces/{workspace_id}/waylines/{wayline_id}` | 无 | 删除航线 |
| POST | `/wayline/api/v1/workspaces/{workspace_id}/waylines/file/upload` | multipart `file` | 服务端直接上传 KMZ；方法实际使用 token 中的 workspace，路径变量未绑定 |

航线列表参数：

| 参数 | 必填 | 说明 |
|---|:---:|---|
| `order_by` | 是 | `name/update_time/create_time` 加 `asc/desc`，例如 `update_time desc` |
| `page`、`page_size` | 否 | 默认 1、10 |
| `favorited` | 否 | 是否收藏 |
| `template_type` | 否 | 可重复；`0` 航点、`1` 二维建图、`2` 三维建图、`3` 带状建图 |
| `action_type` | 否 | AI 巡检动作类型 |
| `drone_model_keys` | 否 | 无人机物模型键集合 |
| `payload_model_key` | 否 | 负载物模型键集合；注意字段是单数 key |
| `key` | 否 | 名称关键词 |

```bash
curl --get "$BASE_URL/wayline/api/v1/workspaces/$WORKSPACE_ID/waylines" \
  -H "x-auth-token: $TOKEN" \
  --data-urlencode 'order_by=update_time desc' \
  --data 'page=1' --data 'page_size=10'
```

服务端直传 KMZ：

```bash
curl -X POST "$BASE_URL/wayline/api/v1/workspaces/$WORKSPACE_ID/waylines/file/upload" \
  -H "x-auth-token: $TOKEN" \
  -F 'file=@/absolute/path/mission.kmz'
```

对象存储上传回调：

```json
{
  "object_key": "wayline/mission.kmz",
  "name": "mission",
  "metadata": {
    "drone_model_key": "0-67-0",
    "payload_model_keys": ["1-53-0"],
    "template_types": [0]
  }
}
```

### 10.2 飞行任务（5 个）

| 方法 | 路径 | 请求 | 说明 |
|---|---|---|---|
| POST | `/wayline/api/v1/workspaces/{workspace_id}/flight-tasks` | JSON `CreateJobParam` | 创建并发布飞行任务 |
| GET | `/wayline/api/v1/workspaces/{workspace_id}/jobs` | Query `page&page_size` | 任务分页列表 |
| DELETE | `/wayline/api/v1/workspaces/{workspace_id}/jobs` | Query `job_id`（可重复） | 批量取消任务 |
| POST | `/wayline/api/v1/workspaces/{workspace_id}/jobs/{job_id}/media-highest` | 无 | 将该任务媒体设为最高上传优先级 |
| PUT | `/wayline/api/v1/workspaces/{workspace_id}/jobs/{job_id}` | JSON | 暂停/恢复任务 |

创建任务：

```json
{
  "name": "园区日常巡检",
  "fileId": "WAYLINE_FILE_ID",
  "dockSn": "DOCK_SN",
  "waylineType": 0,
  "taskType": 0,
  "rthAltitude": 100,
  "outOfControlAction": 0,
  "minBatteryCapacity": 60,
  "minStorageCapacity": 1024,
  "taskDays": [],
  "taskPeriods": []
}
```

| 字段 | 必填 | 约束/说明 |
|---|:---:|---|
| `name`、`fileId`、`dockSn` | 是 | 非空字符串 |
| `waylineType` | 是 | `0` 航点、`1` 二维、`2` 三维、`3` 带状 |
| `taskType` | 是 | `0` 立即、`1` 定时、`2` 条件 |
| `rthAltitude` | 是 | 20–500 m |
| `outOfControlAction` | 是 | `0` 返航、`1` 悬停、`2` 降落 |
| `minBatteryCapacity` | 否 | 50–90 |
| `minStorageCapacity` | 否 | 最低存储容量 |
| `taskDays` | 条件任务相关 | 日期/天的毫秒时间值列表 |
| `taskPeriods` | 条件任务相关 | 每日时间段列表 |

暂停/恢复：

```json
{"status":0}
```

`status=0` 暂停，`status=1` 恢复。

## 11. 设备控制 API（7 个）

| 方法 | 路径 | 请求 | 说明 |
|---|---|---|---|
| POST | `/control/api/v1/devices/{sn}/jobs/{service_identifier}` | 可选 JSON | 机巢远程调试/维护命令 |
| POST | `/control/api/v1/devices/{sn}/jobs/fly-to-point` | JSON | 已起飞状态下飞向目标点 |
| DELETE | `/control/api/v1/devices/{sn}/jobs/fly-to-point` | 无 | 停止 Fly-to-point |
| POST | `/control/api/v1/devices/{sn}/jobs/takeoff-to-point` | JSON | 起飞并飞向目标点 |
| POST | `/control/api/v1/devices/{sn}/authority/flight` | 无 | 抢占飞行控制权 |
| POST | `/control/api/v1/devices/{sn}/authority/payload` | JSON `DronePayloadParam` | 抢占负载控制权 |
| POST | `/control/api/v1/devices/{sn}/payload/commands` | JSON | 发送相机/云台命令 |

这些接口会同步等待 MQTT 设备应答；设备离线、控制权冲突或超时都会导致业务失败。

### 11.1 远程调试命令

`service_identifier` 支持：

```text
debug_mode_open, debug_mode_close,
supplement_light_open, supplement_light_close,
return_home, return_home_cancel,
device_reboot, drone_open, drone_close,
drone_format, device_format,
cover_open, cover_close, putter_open, putter_close,
charge_open, charge_close,
battery_maintenance_switch, alarm_state_switch,
battery_store_mode_switch, sdr_workmode_switch,
air_conditioner_mode_switch
```

无需参数的命令可省略 body；开关类命令使用：

```json
{"action":1}
```

其中 `action` 为必填整数，具体值由目标命令对应的设备协议定义。

### 11.2 Fly-to-point

```json
{
  "flyToId": "client-generated-id",
  "maxSpeed": 8,
  "points": [{"latitude":39.90,"longitude":116.30,"height":100.0}]
}
```

- `maxSpeed`：1–15 m/s；
- `points`：至少 1 个；部分机型只支持单点；
- 纬度 `-90..90`，经度 `-180..180`，WGS84 高度 `2..10000`。

### 11.3 Takeoff-to-point

```json
{
  "flightId": "client-generated-id",
  "targetLongitude": 116.30,
  "targetLatitude": 39.90,
  "targetHeight": 100.0,
  "securityTakeoffHeight": 30.0,
  "rthAltitude": 100.0,
  "rcLostAction": 0,
  "exitWaylineWhenRcLost": 0,
  "maxSpeed": 8.0,
  "rthMode": 0,
  "commanderModeLostAction": 0,
  "commanderFlightMode": 0,
  "commanderFlightHeight": 100.0
}
```

高度和速度约束由 DTO 校验：目标高度 `2..10000`，安全起飞高度和返航高度 `2..1500`，速度 `1..15`，指挥飞行高度 `2..3000`。枚举值必须与所接设备的协议版本匹配。

### 11.4 负载控制权与命令

`DronePayloadParam`：

| 字段 | 约束/说明 |
|---|---|
| `payloadIndex` | 必填，格式 `数字-数字-数字`，例如 `89-0-7` |
| `cameraType` | 相机类型枚举 |
| `zoomFactor` | 2–200 |
| `cameraMode` | 相机模式枚举 |
| `locked` | 是否锁定 |
| `pitchSpeed`、`yawSpeed` | 云台速度 |
| `x`、`y` | 画面归一化坐标，0–1 |
| `resetMode` | 云台复位模式 |

发送负载命令：

```json
{
  "cmd": "camera_photo_take",
  "data": {"payloadIndex":"89-0-7"}
}
```

当前实现支持：`camera_mode_switch`、`camera_photo_take`、`camera_recording_start`、`camera_recording_stop`、`camera_aim`、`camera_focal_length_set`、`gimbal_reset`。不同命令只读取 `data` 中相关字段。

## 12. DRC API（3 个）

| 方法 | 路径 | 请求 | 说明 |
|---|---|---|---|
| POST | `/control/api/v1/workspaces/{workspace_id}/drc/connect` | JSON | 为用户取得 DRC MQTT 连接信息 |
| POST | `/control/api/v1/workspaces/{workspace_id}/drc/enter` | JSON | 设备进入 DRC 模式并取得 ACL |
| POST | `/control/api/v1/workspaces/{workspace_id}/drc/exit` | JSON | 退出 DRC 模式 |

连接请求：

```json
{"clientId":"web-drc-client-001","expireSec":3600}
```

进入/退出 DRC：

```json
{
  "clientId":"web-drc-client-001",
  "dockSn":"DOCK_SN",
  "expireSec":3600,
  "deviceInfo":{"osdFrequency":10,"hsiFrequency":1}
}
```

约束：`clientId`、`dockSn` 非空；`expireSec` 1800–86400 秒；`osdFrequency`、`hsiFrequency` 1–30 Hz。调用顺序通常为 `connect` → 客户端连接返回的 DRC Broker → `enter` → 控制 → `exit`。

## 13. 测试 API（2 个，不应暴露到生产）

| 方法 | 路径 | 鉴权 | 行为/风险 |
|---|---|---|---|
| POST | `/test/test1` | 免鉴权 | 向硬编码 Topic `thing/product/SN1000001/state` 发布“你好” |
| POST | `/test/test2` | 免鉴权 | 向硬编码设备 SN 和 RTMP 地址下发直播命令，并等待最多 20 秒 |

这两个接口没有业务参数且包含硬编码环境值。生产部署应删除 Controller、增加环境开关，或至少从 MVC 免鉴权列表中移除 `/test/**`。

## 14. WebSocket 推送

### 14.1 连接

WebSocket/STOMP 握手端点：

```text
ws://localhost:9000/api/v1/ws?x-auth-token=<JWT>
```

注意：与 HTTP 不同，WebSocket token 放在查询参数 `x-auth-token` 中。握手会校验 token，并将连接身份设置为：

```text
{workspaceId}/{userType}/{userId}
```

服务端主要通过已有会话直接推送，当前代码未声明供客户端订阅的自定义 STOMP topic；客户端应按所用 STOMP/WebSocket 库处理端点收到的文本帧。

### 14.2 消息格式

```json
{
  "biz_code": "device_online",
  "version": "1.0",
  "timestamp": 1785772800000,
  "data": {}
}
```

`biz_code` 可能包括：

```text
device_online, device_offline, device_update_topo, device_osd,
gateway_osd, dock_osd, device_hms,
map_element_create, map_element_update, map_element_delete, map_group_refresh,
flighttask_progress, ota_progress,
file_upload_callback, fileupload_progress,
device_reboot, drone_open, drone_close, device_check,
drone_format, device_format, cover_open, cover_close,
putter_open, putter_close, charge_open, charge_close,
highest_priority_upload_flighttask_media,
control_source_change, fly_to_point_progress, takeoff_to_point_progress,
drc_status_notify, joystick_invalid_notify,
flight_areas_sync_progress, flight_areas_drone_location, flight_areas_update
```

收到拓扑或地图刷新类消息后，应重新调用对应 GET 接口获取权威完整状态；进度类消息可以直接驱动前端状态展示。

## 15. MQTT 与 HTTP 的关系

调用方发起设备控制、直播、日志、航线或飞行区域同步 HTTP 请求后，服务端通常会：

1. 校验 JWT、工作空间和设备状态；
2. 将请求转换为设备协议 DTO；
3. 通过 MQTT `services` 或 `property/set` Topic 下发；
4. 使用 `tid`/`bid` 等待设备回复；
5. 将同步结果返回 HTTP；
6. 将后续异步进度通过 WebSocket 推给客户端。

因此 HTTP 返回成功只代表当前同步步骤成功；飞行任务、OTA、日志上传等长流程必须继续监听 WebSocket 进度和最终状态。

## 16. 常见错误与排查

| 现象 | 原因 | 排查建议 |
|---|---|---|
| HTTP 401 且无 JSON body | 缺少/无效 `x-auth-token` | 重新登录，确认 HTTP Header；WebSocket 则用 Query 参数 |
| `code=-1` | 业务失败 | 查看 `message` 和 `logs/cloud-service.log` |
| 参数校验失败 | 必填字段、范围、UUID 或枚举不合法 | 对照本文请求模型；注意真实字段名大小写 |
| 控制接口超时 | 设备离线、MQTT 不通或设备未回复 | 检查设备拓扑、Broker、动态订阅和服务日志 |
| 下载拿到 302 | 正常行为 | curl 使用 `-L` 跟随跳转，或读取 `Location` |
| 上传成功但列表无记录 | 未调用对应 `upload-callback` | 完成直传后登记对象键和元数据 |
| 工作空间不一致 | 路径 ID、token claim 和 body 中 workspace 不一致 | 统一使用当前用户所属 workspace |
| `group-upload-callback` 无响应体 | 当前实现返回 `null` | 先实现该方法再用于生产 |
| Swagger 中缺少业务细节 | 注解定义不完整或路由来自接口继承 | 以本文和 Controller/DTO 源码为准 |

下载示例：

```bash
curl -L "$BASE_URL/media/api/v1/files/$WORKSPACE_ID/file/<file_id>/url" \
  -H "x-auth-token: $TOKEN" -o media.bin
```

## 17. 生产调用检查清单

- 已修改 `application.yml` 中数据库、Redis、MQTT、OSS、Cloud API License 和直播配置；
- 登录接口返回的 token 能访问 `/users/current`；
- 请求中的 workspace 与 token claim 一致；
- 设备已上线、已绑定，并出现在拓扑接口中；
- 文件上传严格执行“STS → 对象存储 → callback”；
- 长任务同时监听 WebSocket；
- 客户端检查 HTTP 状态码与 JSON `code`；
- 生产环境禁用 `/test/**`；
- 不使用尚未实现的 `group-upload-callback`；
- 下载客户端能处理 302 临时 URL 和 URL 过期。

## 18. 源码索引

| 内容 | 位置 |
|---|---|
| 所有业务 Controller | `cloud-service/src/main/java/com/uav/service/**/controller` |
| 继承式 HTTP 路由 | `cloud-api/src/main/java/com/uav/api/**/IHttp*Service.java` |
| JWT 拦截器 | `uav-framework/uav-framework-context/.../AuthInterceptor.java` |
| 鉴权排除规则 | `uav-framework/uav-framework-context/.../GlobalMVCConfigurer.java` |
| 统一响应/分页 | `uav-framework/uav-framework-context/.../response`、`.../page` |
| WebSocket 配置 | `uav-framework/uav-framework-websocket/.../WebSocketConfiguration.java` |
| WebSocket 业务码 | `uav-framework/uav-framework-websocket/.../BizCodeEnum.java` |
| URL 前缀和端口 | `cloud-service/src/main/resources/application.yml` |
