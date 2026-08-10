# Cloud-API 新 Nano 快速部署（Mac 构建镜像）

本文用于在全新的 64 位 Jetson Nano 上部署 Cloud-API。后端镜像在 Apple Silicon Mac 上构建，
再通过局域网或 U 盘传输到 Nano；Nano 只负责加载镜像和运行 Docker Compose，不执行 Maven 编译。

适用仓库：

```text
git@github.com:LC-daoxin/cloud-api.git
```

本文以以下环境为例，实际使用时请替换 Nano 用户名、IP 和目录：

```text
开发机：          Apple Silicon Mac
新 Nano：         jetson@192.168.3.1
Nano 部署目录：   /home/jetson/1_projects/cloud-api
应用镜像：        uav-cloud-api-app:nano1-<Git提交短号>
```

> 本文针对“新机首次部署”。已有数据卷的节点升级还应先备份数据，并阅读第 11 节的升级和回滚说明。

## 1. 部署方案

| 步骤 | 执行位置 | 说明 |
| --- | --- | --- |
| 构建镜像 | Mac | 使用项目 Dockerfile 编译并生成 ARM64 后端镜像 |
| 导出镜像 | Mac | 使用 `docker save` 生成压缩包 |
| 传输 | Mac → Nano | 使用 `scp`、移动硬盘或 U 盘 |
| 克隆仓库 | Nano | 获取 Compose、应用配置、SQL 和迁移脚本 |
| 加载镜像 | Nano | 使用 `docker load`，不在 Nano 上构建 |
| 启动服务 | Nano | 使用 `docker-compose.nano.yml` 启动整套服务 |

Cloud-API 只有一个自定义镜像：

```text
uav-cloud-api-app:<版本>
```

其余服务使用第三方 ARM64 镜像：MySQL、Redis、Mosquitto、MinIO 和 MediaMTX。

## 2. 端口和同机部署检查

`docker-compose.nano.yml` 使用 `network_mode: host`。以下端口直接由 Cloud-API 容器占用，不能通过
Docker 的 `ports` 映射临时改写：

| 服务 | 协议/端口 | 用途 |
| --- | --- | --- |
| Cloud-API | TCP `9000` | HTTP API 和业务 WebSocket |
| Mosquitto | TCP `1883` | MQTT |
| Mosquitto | TCP `9001` | MQTT over WebSocket |
| MySQL | TCP `3306` | 数据库 |
| Redis | TCP `6379` | 缓存 |
| MinIO | TCP `9100` | 对象存储 API |
| MinIO | TCP `9101` | MinIO Console |
| MediaMTX | TCP `8554` | RTSP |
| MediaMTX | TCP `8889` | WebRTC/WHEP HTTP |
| MediaMTX | UDP `8189` | WebRTC 媒体 |

### 2.1 与 YOOX_Cloud_GCS 部署在同一台 Nano

Cloud-API 和 YOOX_Cloud_GCS 的默认配置不能原样同时启动。至少存在以下冲突：

| 端口 | Cloud-API | YOOX_Cloud_GCS 默认用途 |
| --- | --- | --- |
| `9000` | Cloud-API HTTP | Pilot 网关 |
| `1883` | Mosquitto MQTT | EMQX MQTT |
| `8554` | MediaMTX RTSP | MediaMTX RTSP |
| `9001` | MQTT WebSocket | MinIO Console（绑定本机回环地址） |
| `8189/udp` | MediaMTX WebRTC | YOOX MediaMTX RTP/WebRTC |

部署前先在 Nano 上检查：

```bash
sudo ss -lntup | grep -E ':(9000|1883|8554|9001|8189|3306|6379|9100|9101|8889)\b'
docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'
```

本指南后续步骤假定 Cloud-API 独占上表端口。如果同机已经运行 YOOX_Cloud_GCS，必须先完成端口
隔离改造；只修改 `YOOX_PILOT_PORT`、`YOOX_MQTT_PORT` 和 `YOOX_PUBLIC_RTSP_PORT` 仍不够，
还要处理 YOOX 的 `9001` 和 `8189/udp`。端口改造后必须同步修改客户端地址和对外广播地址。

> 不要看到容器处于 `Restarting` 后反复重启。先用 `docker logs <容器名>` 和 `ss` 确认是否为
> `address already in use`。

## 3. 前提条件

### 3.1 Mac

- Apple Silicon（M1/M2/M3/M4），本机架构为 `arm64`。
- Docker Desktop 或 Colima 已安装并启动。
- 已克隆 Cloud-API 仓库。
- 能通过 SSH 登录目标 Nano。

检查环境：

```bash
uname -m
docker version --format '{{.Server.Os}}/{{.Server.Arch}}'
```

预期分别包含：

```text
arm64
linux/arm64
```

### 3.2 Jetson Nano

- 使用 64 位 JetPack/Ubuntu，`uname -m` 输出 `aarch64`。
- Docker Engine 已安装。
- Docker Compose v2 插件已安装，命令为 `docker compose`。
- 固定局域网 IP 已配置。
- 首次拉取第三方镜像时能够访问 Docker Hub；完全离线时参考第 7 节。
- 建议至少预留 10 GB 可用空间。

检查 Nano：

```bash
ssh jetson@192.168.3.1 'uname -m && docker version && docker compose version && df -h /'
```

如果输出 `armv7l`，说明系统为 32 位，不能运行本文构建的 ARM64 镜像。

## 4. 配置私有仓库访问

如果仓库为私有仓库，推荐每台 Nano 使用独立的只读 Deploy Key。

在 Nano 上执行：

```bash
ssh jetson@192.168.3.1
mkdir -p ~/.ssh
chmod 700 ~/.ssh

ssh-keygen \
  -t ed25519 \
  -f ~/.ssh/id_ed25519_cloud_api \
  -N "" \
  -C 'jetson@nano1 cloud-api'

chmod 600 ~/.ssh/id_ed25519_cloud_api
chmod 644 ~/.ssh/id_ed25519_cloud_api.pub
cat ~/.ssh/id_ed25519_cloud_api.pub
```

把公钥添加到 GitHub 仓库：

```text
Settings → Deploy keys → Add deploy key
```

- Title：例如 `cloud-api-nano1`
- Key：粘贴公钥
- 不勾选 `Allow write access`

测试：

```bash
ssh \
  -T \
  -i ~/.ssh/id_ed25519_cloud_api \
  -o IdentitiesOnly=yes \
  git@github.com
```

GitHub 显示 `successfully authenticated` 即表示成功。GitHub 不提供 SSH Shell，因此成功测试也可能返回
退出码 `1`。

## 5. Mac 上构建应用镜像

### 5.1 更新并检查代码

```bash
cd ~/git/yooxplore/Autel/Cloud-API
git pull --ff-only
git status --short
```

构建正式镜像前应确认工作区只包含计划发布的修改。未提交修改也会进入 Docker 构建上下文，容易造成
镜像内容与 Git 提交号不一致。

### 5.2 生成版本号并构建

```bash
export CLOUD_API_VERSION="nano1-$(git rev-parse --short HEAD)"

docker build \
  --platform linux/arm64 \
  -t "uav-cloud-api-app:${CLOUD_API_VERSION}" \
  .
```

Dockerfile 使用 Java 17 构建和运行应用。确认镜像架构：

```bash
docker image inspect \
  "uav-cloud-api-app:${CLOUD_API_VERSION}" \
  --format '{{.Os}}/{{.Architecture}}'
```

预期输出：

```text
linux/arm64
```

### 5.3 准备 Nano 专用环境文件

```bash
cp .env.example .env.nano1
chmod 600 .env.nano1
```

编辑 `.env.nano1`，至少设置：

```dotenv
COMPOSE_PROJECT_NAME=cloud-api
NODE_LAN_IP=192.168.3.1
APP_IMAGE=uav-cloud-api-app:nano1-<Git提交短号>

DB_NAME=cloud_sample
DB_USER=uav_cloud
DB_PASSWORD=<数据库应用账号强密码>
MYSQL_ROOT_PASSWORD=<数据库 root 强密码>

OSS_ACCESS_KEY=<MinIO访问账号>
OSS_SECRET_KEY=<MinIO强密码>

JWT_SECRET=<至少32字节随机值>

RTSP_USERNAME=admin
RTSP_PASSWORD=<RTSP密码>

# 当前 Redis 容器未启用 requirepass，保持为空
REDIS_PASSWORD=
```

生成随机值示例：

```bash
openssl rand -base64 32
```

注意事项：

- `NODE_LAN_IP` 必须是 Nano 的固定局域网 IP，登录接口返回的 MQTT 和对象存储地址依赖它。
- `APP_IMAGE` 必须与刚刚构建的完整镜像名完全一致。
- 不同 Nano 的数据库密码、MinIO 密钥和 `JWT_SECRET` 应分别生成。
- 当前 Compose 中 Redis 没有启用密码，不能只在 `.env` 中填写 `REDIS_PASSWORD`；否则应用会尝试
  对无密码 Redis 执行认证，导致连接失败。
- Mosquitto 当前允许匿名连接；登录接口返回的 MQTT 用户名和密码不是 Broker 的强制认证规则。
- `.env.nano1` 包含敏感信息，不要提交到 Git。

检查环境文件是否被忽略：

```bash
git check-ignore .env.nano1
```

确认 Compose 能解析配置：

```bash
docker compose \
  -f docker-compose.nano.yml \
  --env-file .env.nano1 \
  config --quiet
```

## 6. 导出并传输应用镜像

### 6.1 导出

```bash
docker save \
  "uav-cloud-api-app:${CLOUD_API_VERSION}" \
  -o "/tmp/cloud-api-${CLOUD_API_VERSION}.tar"

gzip -f "/tmp/cloud-api-${CLOUD_API_VERSION}.tar"
ls -lh "/tmp/cloud-api-${CLOUD_API_VERSION}.tar.gz"
```

### 6.2 传输到 Nano

```bash
scp \
  "/tmp/cloud-api-${CLOUD_API_VERSION}.tar.gz" \
  jetson@192.168.3.1:/tmp/

scp .env.nano1 jetson@192.168.3.1:/tmp/.env.cloud-api
```

局域网速度较慢时，可以通过 U 盘传输镜像包。

## 7. 完全离线时准备第三方镜像

Nano 能联网时跳过本节。完全离线时，在 ARM64 Mac 上拉取并导出以下镜像：

```bash
docker pull --platform linux/arm64 mysql:8.0
docker pull --platform linux/arm64 redis:7-alpine
docker pull --platform linux/arm64 eclipse-mosquitto:2
docker pull --platform linux/arm64 minio/minio:latest
docker pull --platform linux/arm64 bluenviron/mediamtx:1.19.3

docker save \
  mysql:8.0 \
  redis:7-alpine \
  eclipse-mosquitto:2 \
  minio/minio:latest \
  bluenviron/mediamtx:1.19.3 \
  -o /tmp/cloud-api-thirdparty-arm64.tar

gzip -f /tmp/cloud-api-thirdparty-arm64.tar
scp /tmp/cloud-api-thirdparty-arm64.tar.gz jetson@192.168.3.1:/tmp/
```

Nano 上加载：

```bash
gunzip -c /tmp/cloud-api-thirdparty-arm64.tar.gz | docker load
```

> `mysql:8.0`、`redis:7-alpine`、`eclipse-mosquitto:2` 和 `minio/minio:latest` 是浮动标签。
> 正式交付时建议在验证完成后记录镜像 digest，避免不同时间部署得到不同内容。

## 8. Nano 上克隆仓库和加载镜像

### 8.1 克隆仓库

```bash
ssh jetson@192.168.3.1
mkdir -p /home/jetson/1_projects
cd /home/jetson/1_projects

GIT_SSH_COMMAND='ssh -i /home/jetson/.ssh/id_ed25519_cloud_api -o IdentitiesOnly=yes' \
  git clone \
  git@github.com:LC-daoxin/cloud-api.git \
  cloud-api

cd /home/jetson/1_projects/cloud-api
git config core.sshCommand \
  'ssh -i /home/jetson/.ssh/id_ed25519_cloud_api -o IdentitiesOnly=yes'

git remote -v
git branch --show-current
git log -1 --oneline
git status --short
```

### 8.2 加载应用镜像

```bash
gunzip -c /tmp/cloud-api-nano1-<Git提交短号>.tar.gz | docker load

docker image ls \
  --format '{{.Repository}}:{{.Tag}}  {{.Size}}' \
  | grep uav-cloud-api-app
```

### 8.3 安装环境文件

```bash
cp -p /tmp/.env.cloud-api /home/jetson/1_projects/cloud-api/.env
chmod 600 /home/jetson/1_projects/cloud-api/.env

cd /home/jetson/1_projects/cloud-api
git check-ignore .env
grep -E '^(COMPOSE_PROJECT_NAME|NODE_LAN_IP|APP_IMAGE)=' .env
```

`git check-ignore .env` 必须输出 `.env`。如果没有输出，先修复忽略规则再继续。

## 9. Nano 上预检和启动

### 9.1 预检

```bash
cd /home/jetson/1_projects/cloud-api

test "$(uname -m)" = "aarch64"
test -f docker-compose.nano.yml
test -f docker/config/application.yml
test -f docker/mediamtx.yml
test -f docker/mosquitto/mosquitto.conf
test -f sql/cloud_api.sql
test -f sql/migrations/001_bcrypt_user_passwords.sql

docker image inspect "$(sed -n 's/^APP_IMAGE=//p' .env)" \
  --format '{{.Os}}/{{.Architecture}}'

docker compose \
  -f docker-compose.nano.yml \
  --env-file .env \
  config --quiet

sudo ss -lntup | grep -E ':(9000|1883|8554|9001|8189|3306|6379|9100|9101|8889)\b' || true
```

如果端口已被其他项目占用，停止部署并先完成端口隔离。

Nano 可联网时预拉取第三方镜像：

```bash
docker compose \
  -f docker-compose.nano.yml \
  --env-file .env \
  pull mediamtx mysql account-migration redis mqtt minio
```

### 9.2 启动

```bash
docker compose \
  -f docker-compose.nano.yml \
  --env-file .env \
  up -d --remove-orphans --wait --wait-timeout 300
```

查看状态：

```bash
docker compose \
  -f docker-compose.nano.yml \
  --env-file .env \
  ps -a
```

预期结果：

- `uav-mysql`、`uav-redis` 和 `uav-cloud-app` 为 `healthy`。
- `uav-mqtt`、`uav-minio`、`uav-mediamtx` 为运行状态。
- `account-migration` 为 `Exited (0)`；它是一次性数据库迁移任务，不应长期运行。

查看日志：

```bash
docker compose \
  -f docker-compose.nano.yml \
  --env-file .env \
  logs --tail=200 app account-migration mysql mqtt minio mediamtx
```

## 10. 首次启动和验证

### 10.1 数据库初始化与账号迁移

全新数据卷首次启动时，MySQL 自动执行 `sql/cloud_api.sql` 建表并写入初始化数据。随后
`account-migration` 执行 `sql/migrations/001_bcrypt_user_passwords.sql`，保证登录密码字段和 BCrypt
格式与 YOOX_Cloud_GCS 一致。

已有数据卷启动时：

- 默认 `admin`、`pilot` 明文密码会转换成对应的 BCrypt 哈希。
- 其他遗留明文账号首次成功登录后自动升级为 BCrypt。
- 迁移不会删除业务数据。

查看迁移结果状态：

```bash
docker compose \
  -f docker-compose.nano.yml \
  --env-file .env \
  logs account-migration

docker compose \
  -f docker-compose.nano.yml \
  --env-file .env \
  ps -a account-migration
```

### 10.2 HTTP 登录验证

初始化登录账号与 YOOX_Cloud_GCS 保持一致：

| 用途 | 用户名 | 初始密码 | `flag` |
| --- | --- | --- | --- |
| Web/API 调试 | `admin` | `Yoox@123456` | `1` |
| Pilot/App | `pilot` | `pilot123` | `2` |

这些是数据库业务账号，不由 `.env` 管理。初始密码只用于首次联调，完成验证后应修改。

先检查接口端口：

```bash
curl -sS -o /dev/null -w '%{http_code}\n' \
  http://127.0.0.1:9000/manage/api/v1/login
```

再使用 Web 账号执行真实登录：

```bash
curl -sS \
  -X POST \
  http://127.0.0.1:9000/manage/api/v1/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<Web登录密码>","flag":1}'
```

响应的业务 `code` 应为 `0`，并包含 `access_token`、`workspace_id` 和 `mqtt_addr`。

修改当前账号密码使用：

```bash
curl -sS \
  -X PUT \
  http://127.0.0.1:9000/manage/api/v1/users/current/password \
  -H 'Content-Type: application/json' \
  -H 'x-auth-token: <当前账号token>' \
  -d '{"old_password":"<当前密码>","new_password":"<新的强密码>"}'
```

新密码必须为 12–72 位，并包含大写字母、小写字母、数字和特殊字符。如果要求 Cloud-API 与
YOOX_Cloud_GCS 继续使用相同登录密码，需要分别登录两个系统并各调用一次修改密码接口；不能把
一个系统的 token 用到另一个系统。

### 10.3 Python Demo 验证

在运行 Demo 的电脑上修改 `docs/python-demo/config.py`：

```python
SERVER_IP = "192.168.3.1"
SERVER_PORT = 9000
```

然后执行：

```bash
cd docs/python-demo
python3 demo_01_login.py
```

重点检查：

- Web 和 Pilot 两种账号都能登录。
- `mqtt_addr` 为 `tcp://192.168.3.1:1883`，不能是 `mqtt`、`localhost` 或 `127.0.0.1`。
- 返回的 `workspace_id` 与初始化工作空间一致。
- 后续 Demo 使用刚获得的 token，不要复用另一个项目签发的 token。

Cloud-API 与 YOOX_Cloud_GCS 的用户名和登录密码可以保持一致，但 JWT 独立签发，因此两边 token
不能互换。

### 10.4 网络服务验证

在局域网另一台机器上执行：

```bash
nc -zv 192.168.3.1 9000
nc -zv 192.168.3.1 1883
nc -zv 192.168.3.1 9001
nc -zv 192.168.3.1 8554
nc -zv 192.168.3.1 9100
nc -zv 192.168.3.1 8889

curl -fsS http://192.168.3.1:9100/minio/health/live
```

### 10.5 真机验收

1. Web/Python 客户端可以登录并刷新 token。
2. Pilot App 使用 `flag=2` 的 Pilot 账号登录。
3. 遥控器和无人机通过 MQTT 自动注册并保持在线。
4. OSD 数据持续到达。
5. 图片、日志和航线文件能够写入 MinIO。
6. RTSP 推流和 WebRTC 播放正常。
7. 云台、相机、航线及飞行控制命令仅在安全条件下验证。

## 11. 日常更新

### 11.1 Mac 侧

每次发布使用新 tag，便于确认版本和回滚：

```bash
cd ~/git/yooxplore/Autel/Cloud-API
git pull --ff-only

export CLOUD_API_VERSION="nano1-$(git rev-parse --short HEAD)"

docker build \
  --platform linux/arm64 \
  -t "uav-cloud-api-app:${CLOUD_API_VERSION}" \
  .

docker save \
  "uav-cloud-api-app:${CLOUD_API_VERSION}" \
  -o "/tmp/cloud-api-${CLOUD_API_VERSION}.tar"

gzip -f "/tmp/cloud-api-${CLOUD_API_VERSION}.tar"
scp "/tmp/cloud-api-${CLOUD_API_VERSION}.tar.gz" jetson@192.168.3.1:/tmp/
```

同步更新 `.env.nano1` 中的 `APP_IMAGE`，再传输：

```bash
scp .env.nano1 jetson@192.168.3.1:/tmp/.env.cloud-api
```

### 11.2 Nano 侧

先备份数据库：

```bash
cd /home/jetson/1_projects/cloud-api
mkdir -p backups

set -a
. ./.env
set +a

docker exec \
  -e MYSQL_PWD="$MYSQL_ROOT_PASSWORD" \
  uav-mysql \
  mysqldump -uroot --single-transaction "$DB_NAME" \
  > "backups/cloud-api-$(date +%Y%m%d-%H%M%S).sql"
```

然后更新：

```bash
git pull --ff-only
gunzip -c /tmp/cloud-api-nano1-<新提交短号>.tar.gz | docker load
cp -p /tmp/.env.cloud-api .env
chmod 600 .env

docker compose \
  -f docker-compose.nano.yml \
  --env-file .env \
  config --quiet

docker compose \
  -f docker-compose.nano.yml \
  --env-file .env \
  up -d --remove-orphans --wait --wait-timeout 300
```

重复第 10 节的登录和网络验证。

> 升级 BCrypt 版本时，必须同时更新应用镜像、Compose 文件和 SQL 迁移文件。不要先单独执行密码迁移
> 再运行不支持 BCrypt 的旧镜像。

## 12. 回滚

### 12.1 普通应用版本回滚

如果数据库结构没有发生不兼容变化，把 `.env` 中的 `APP_IMAGE` 改回旧 tag：

```bash
nano .env

docker compose \
  -f docker-compose.nano.yml \
  --env-file .env \
  up -d --wait --wait-timeout 300
```

### 12.2 BCrypt 迁移后的特殊注意事项

密码迁移后，早期只支持明文密码的 Cloud-API 镜像不能直接验证 BCrypt。如果必须回滚到这类旧镜像，
应同时恢复迁移前的数据库备份。不要为了回滚把哈希批量改成固定明文密码。

恢复数据库属于高风险操作，应先停止应用并确认备份文件、数据库名和目标节点均正确。

## 13. 停止、清理和数据保护

普通停止：

```bash
docker compose \
  -f docker-compose.nano.yml \
  --env-file .env \
  down
```

查看磁盘占用：

```bash
docker system df
df -h /
```

清理未被使用的悬空镜像：

```bash
docker image prune -f
```

以下命令会删除数据库、对象存储和其他持久化数据，日常停机和升级时禁止使用：

```text
docker compose down -v
```

手动删除旧应用镜像前，先确认没有容器引用它：

```bash
docker image ls --format '{{.Repository}}:{{.Tag}}  {{.ID}}  {{.Size}}' \
  | grep uav-cloud-api-app
```

## 14. 常见问题

### 14.1 `APP_IMAGE` 与加载的镜像不一致

现象：Compose 提示找不到镜像，或者尝试从不存在的仓库拉取。

```bash
grep '^APP_IMAGE=' .env
docker image ls --format '{{.Repository}}:{{.Tag}}' | grep uav-cloud-api-app
```

两者必须完全一致。

### 14.2 容器提示 `address already in use`

```bash
sudo ss -lntup
docker ps --format 'table {{.Names}}\t{{.Ports}}'
```

如果同机运行 YOOX_Cloud_GCS，按第 2.1 节完成全部冲突端口隔离。

### 14.3 应用无法连接 Redis

当前 Nano Compose 的 Redis 未启用密码。确认：

```bash
grep '^REDIS_PASSWORD=' .env
```

应为空值。若要启用 Redis 密码，必须同时修改 Redis 启动参数、健康检查和应用配置，不能只改 `.env`。

### 14.4 登录一直失败

检查账号类型：

- Web 管理账号使用 `flag=1`。
- Pilot/App 账号使用 `flag=2`。

检查迁移任务：

```bash
docker compose \
  -f docker-compose.nano.yml \
  --env-file .env \
  ps -a account-migration

docker compose \
  -f docker-compose.nano.yml \
  --env-file .env \
  logs account-migration app
```

如果刚从明文版本升级，确认新应用镜像和迁移脚本来自同一次发布。

### 14.5 登录成功但 `mqtt_addr` 错误

```bash
grep '^NODE_LAN_IP=' .env
docker compose \
  -f docker-compose.nano.yml \
  --env-file .env \
  exec app env | grep '^BROKER_'
```

`BROKER_HOST` 应等于 Nano 的固定局域网 IP。

### 14.6 `account-migration` 显示 `Exited (0)`

这是正常状态。它是一次性迁移任务，成功执行后退出。非零退出码才需要检查日志。

### 14.7 Nano 拉取镜像失败

确认 DNS、系统时间和 Docker Hub 网络连接；完全离线时按照第 7 节在 Mac 上导出第三方镜像。

### 14.8 `no space left on device`

```bash
df -h /
docker system df
docker image prune -f
```

不要使用 `docker compose down -v` 清空间。

### 14.9 Intel Mac 或 x86_64 构建机

使用 Buildx 跨架构构建：

```bash
docker buildx build \
  --platform linux/arm64 \
  --load \
  -t "uav-cloud-api-app:${CLOUD_API_VERSION}" \
  .
```

跨架构构建速度明显慢于 Apple Silicon 原生构建。

## 15. 完成标准

满足以下条件后才算部署完成：

- Nano 为 `aarch64` 64 位系统。
- GitHub 私有仓库只读认证通过。
- Cloud-API ARM64 镜像已成功加载。
- `.env` 权限为 `600` 且被 Git 忽略。
- `NODE_LAN_IP` 和 `APP_IMAGE` 正确。
- Compose 配置检查通过。
- 所有长期运行容器正常，`account-migration` 为 `Exited (0)`。
- Web 和 Pilot 两种账号都能登录。
- 登录返回的 `mqtt_addr` 指向当前 Nano。
- MQTT、MinIO、RTSP 和 WebRTC 端口验证通过。
- 与 YOOX_Cloud_GCS 同机部署时，所有冲突端口已经完成隔离。
- 已完成数据库备份和版本回滚记录。

## 16. 相关文档

- [4 节点 Jetson Nano 部署手册](JETSON_NANO_DEPLOYMENT.md)
- [Linux 部署手册](LINUX_DEPLOYMENT.md)
- [Pilot App 配置](PILOT_APP_SETUP.md)
- [API 调用指南](API_CALL_GUIDE.md)
- [Docker save](https://docs.docker.com/reference/cli/docker/image/save/)
- [Docker load](https://docs.docker.com/reference/cli/docker/image/load/)
