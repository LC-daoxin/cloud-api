# UAV Cloud API Linux 构建与部署手册

本文针对当前仓库版本编写，覆盖从空白 Linux 服务器到服务上线、验证、升级和回滚的完整过程。

当前项目基线：

| 项目 | 值 |
|---|---|
| Java | 17 |
| Spring Boot | 2.7.12 |
| 应用版本 | 1.10.0 |
| SDK 模块版本 | 1.0.3 |
| Framework 版本 | 1.0.0 |
| 应用入口 | `com.uav.service.ServiceCloudApiApplication` |
| 默认 HTTP 端口 | `9000` |
| 数据库脚本 | `sql/cloud_api.sql` |

本文以单机部署为例。MySQL、Redis、MQTT Broker 和对象存储可以安装在同一台机器，也可以使用独立的基础设施服务；生产环境更推荐独立部署和备份。

## 1. 部署架构与端口

```text
Web/Pilot 客户端
   │ HTTP / WebSocket
   ▼
UAV Cloud API :9000
   ├── MySQL :3306
   ├── Redis :6379
   ├── MQTT Broker :1883/8883 或实际端口
   └── MinIO/S3/OSS :9100 或云端地址

无人机/遥控器/机巢
   ├── MQTT Broker
   └── 对象存储
```

需要提前规划的网络：

| 方向 | 端口/协议 | 用途 |
|---|---|---|
| 客户端 → 应用 | TCP 9000，或反向代理后的 80/443 | REST API、WebSocket |
| 应用 → MySQL | TCP 3306 | 持久化业务数据 |
| 应用 → Redis | TCP 6379 | 在线设备、任务状态和缓存 |
| 应用/设备 → MQTT | TCP 1883/8883 或自定义端口 | 设备消息与控制命令 |
| 应用/设备 → OSS | HTTP/HTTPS | 航线、媒体、日志和固件文件 |
| 应用 → NTP/DNS | UDP 123、TCP/UDP 53 | 时间和域名解析 |

不要直接将 MySQL、Redis 和 MinIO 管理端口暴露到公网。

## 2. 服务器建议

最低测试环境：

- 2 核 CPU
- 4 GB 内存
- 20 GB 磁盘
- JDK 17

生产起步建议：

- 4 核 CPU
- 8 GB 内存
- 独立数据盘和日志盘
- MySQL、Redis、MQTT 和对象存储有独立监控与备份
- 服务器时区和时间同步正确

检查系统：

```bash
uname -a
timedatectl
df -h
free -h
```

建议统一时区：

```bash
sudo timedatectl set-timezone Asia/Shanghai
sudo timedatectl set-ntp true
```

## 3. 安装 JDK 17、Maven 和基础工具

### 3.1 Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y openjdk-17-jdk maven git curl unzip mysql-client redis-tools netcat-openbsd
```

### 3.2 Rocky Linux/AlmaLinux/CentOS

```bash
sudo dnf install -y java-17-openjdk-devel maven git curl unzip mysql redis nc
```

### 3.3 验证版本

```bash
java -version
javac -version
mvn -version
```

必须确认 Maven 实际使用 Java 17。如果服务器安装了多个 JDK，可设置：

```bash
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk
export PATH="$JAVA_HOME/bin:$PATH"
mvn -version
```

Ubuntu 的实际路径可能是 `/usr/lib/jvm/java-17-openjdk-amd64`，应以本机 `readlink -f "$(command -v java)"` 的结果为准。

## 4. 获取源码

选择固定的 tag 或 commit，不建议在生产服务器直接使用持续变化的开发分支：

```bash
sudo mkdir -p /srv/uav-cloud-src
sudo chown "$USER":"$USER" /srv/uav-cloud-src
git clone <仓库地址> /srv/uav-cloud-src
cd /srv/uav-cloud-src
git checkout <发布标签或提交号>
```

确认项目结构：

```bash
test -f pom.xml
test -f uav-framework/pom.xml
test -f cloud-service/pom.xml
test -f sql/cloud_api.sql
```

## 5. 构建前必须处理的 Maven 父版本问题

当前仓库的子模块使用了下面的父版本：

```xml
<parent>
    <groupId>com.uav.great</groupId>
    <artifactId>uav-framework</artifactId>
    <version>${revision}</version>
</parent>
```

在同一个 Maven Reactor 中编译时可以解析；安装到 `~/.m2` 后，子模块 POM 可能仍保留 `${revision}`。主工程再次消费这些 artifact 时，会错误查找：

```text
com.uav.great:uav-framework:pom:${revision}
```

因此，正式构建前需要固定所有子模块的父版本。

### 5.1 Framework 子模块

修改以下文件中 `<parent>` 内的版本：

```text
uav-framework/uav-framework-context/pom.xml
uav-framework/uav-framework-db/pom.xml
uav-framework/uav-framework-mqtt/pom.xml
uav-framework/uav-framework-redis/pom.xml
uav-framework/uav-framework-storage/pom.xml
uav-framework/uav-framework-web/pom.xml
uav-framework/uav-framework-websocket/pom.xml
```

统一改为：

```xml
<parent>
    <groupId>com.uav.great</groupId>
    <artifactId>uav-framework</artifactId>
    <version>1.0.0</version>
    <relativePath>../pom.xml</relativePath>
</parent>
```

只固定 `<parent>` 的版本；模块自身的 `<version>${revision}</version>` 可以保留。

### 5.2 Cloud 子模块

修改 `cloud-api/pom.xml` 和 `cloud-service/pom.xml` 的父版本：

```xml
<parent>
    <groupId>com.uav</groupId>
    <artifactId>uav-cloud-api</artifactId>
    <version>1.10.0</version>
    <relativePath>../pom.xml</relativePath>
</parent>
```

长期需要由 CI 动态控制版本时，可以引入 `flatten-maven-plugin`；当前部署最稳妥的方式是固定子模块的父版本。

## 6. 构建项目

### 6.1 安装 framework

项目根 POM 不包含 `uav-framework`，因此必须先单独安装：

```bash
cd /srv/uav-cloud-src
mvn -f uav-framework/pom.xml clean install -DskipTests
```

确认本地 Maven 仓库已经产生 framework artifact：

```bash
test -f "$HOME/.m2/repository/com/uav/great/context/uav-framework-context/1.0.0/uav-framework-context-1.0.0.jar"
test -f "$HOME/.m2/repository/com/uav/great/mqtt/uav-framework-mqtt/1.0.0/uav-framework-mqtt-1.0.0.jar"
```

### 6.2 构建并安装主工程

```bash
mvn clean install -DskipTests
```

### 6.3 生成可执行 Spring Boot JAR

当前 POM 没有显式绑定 `spring-boot:repackage` 到 `package` 生命周期。为确保产物可以用 `java -jar` 启动，再执行：

```bash
mvn -f cloud-service/pom.xml clean package spring-boot:repackage -DskipTests
```

预期产物：

```text
cloud-service/target/cloud-service-1.10.0.jar
```

检查 JAR：

```bash
test -s cloud-service/target/cloud-service-1.10.0.jar
unzip -p cloud-service/target/cloud-service-1.10.0.jar META-INF/MANIFEST.MF
```

Manifest 应包含类似内容：

```text
Main-Class: org.springframework.boot.loader.JarLauncher
Start-Class: com.uav.service.ServiceCloudApiApplication
```

记录校验和，便于发布和回滚核对：

```bash
sha256sum cloud-service/target/cloud-service-1.10.0.jar
```

## 7. 准备 MySQL

项目 SQL 脚本会创建 `cloud_sample` 数据库，但源码中的示例 YAML 使用 `cloud_service`。本手册统一使用 `cloud_sample`。

### 7.1 创建数据库账号

登录 MySQL：

```bash
mysql -h <MYSQL_HOST> -P 3306 -u root -p
```

执行：

```sql
CREATE DATABASE IF NOT EXISTS cloud_sample
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'uav_cloud'@'%' IDENTIFIED BY '替换为强密码';
GRANT ALL PRIVILEGES ON cloud_sample.* TO 'uav_cloud'@'%';
FLUSH PRIVILEGES;
```

如果应用和 MySQL 在同一台服务器，建议把账号来源从 `%` 限制为 `localhost`。如果是独立服务器，应限制为应用服务器网段。

### 7.2 导入表结构和初始化数据

```bash
mysql -h <MYSQL_HOST> -P 3306 -u uav_cloud -p < sql/cloud_api.sql
```

验证：

```bash
mysql -h <MYSQL_HOST> -P 3306 -u uav_cloud -p \
  -e "USE cloud_sample; SHOW TABLES;"
```

脚本包含演示用户，登录密码使用 BCrypt 哈希保存。演示账号只能用于首次联调，生产上线前仍必须修改默认密码。Docker Compose 会在应用启动前执行 `sql/migrations/001_bcrypt_user_passwords.sql`，将已有数据卷中的默认明文密码升级为 BCrypt；其他遗留明文账号会在首次成功登录后自动升级。

## 8. 准备 Redis

确认网络连通：

```bash
nc -vz <REDIS_HOST> 6379
redis-cli -h <REDIS_HOST> -p 6379 -a '<REDIS_PASSWORD>' ping
```

预期返回：

```text
PONG
```

生产建议：

- 启用密码或 ACL。
- 只允许应用服务器访问。
- 根据任务恢复要求配置 AOF/RDB。
- 禁止公网直连。
- 不要随意执行 `FLUSHALL`，设备在线态和航线调度依赖 Redis。

## 9. 准备 MQTT Broker

项目通过 MQTT 与设备通信。可以使用已有 EMQX 或其他兼容 MQTT 的 Broker。

需要为服务端创建独立账号，并允许它订阅/发布至少这些 Topic 范围：

```text
sys/product/#
thing/product/#
```

初始订阅配置为：

```text
sys/product/+/status
thing/product/+/requests
thing/product/+/state
```

设备上线后，服务还会动态订阅 OSD、events、services reply 和 property reply 等 Topic，因此 ACL 不能只放行三个初始 Topic。

测试 TCP 连通性：

```bash
nc -vz <MQTT_HOST> <MQTT_PORT>
```

如果使用 TLS/WSS，需要同时配置证书、域名和反向代理。DRC 是独立连接，只有使用低时延远程控制时才需要配置 `mqtt.DRC`。

## 10. 准备对象存储

项目支持：

- MinIO
- Amazon S3
- 阿里云 OSS

对象存储用于航线、媒体、日志、固件和飞行区域文件。需要提前：

1. 创建 bucket，例如 `uav-store`。
2. 创建专用 access key/secret key。
3. 授予该 bucket 所需的读写和临时凭证权限。
4. 确保应用和设备都能访问 endpoint。
5. 正确配置跨域规则和预签名 URL 的外部可达地址。

应用默认端口是 `9000`，示例 MinIO endpoint 也是 `127.0.0.1:9000`。同机部署时会冲突，本手册假设 MinIO API 使用 `9100`：

```text
http://127.0.0.1:9100
```

测试：

```bash
curl -I http://<MINIO_HOST>:9100/minio/health/live
```

## 11. 创建外部生产配置

不要直接把生产密码写入仓库。创建部署目录：

```bash
sudo mkdir -p /etc/uav-cloud
sudo install -m 600 cloud-service/src/main/resources/application.yml \
  /etc/uav-cloud/application.yml
```

编辑 `/etc/uav-cloud/application.yml`，至少修改以下配置：

```yaml
server:
  port: 9000

spring:
  application:
    name: cloud-service
  datasource:
    druid:
      type: com.alibaba.druid.pool.DruidDataSource
      driver-class-name: com.mysql.cj.jdbc.Driver
      url: jdbc:mysql://MYSQL_HOST:3306/cloud_sample?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai
      username: uav_cloud
      password: REPLACE_ME
      initial-size: 10
      min-idle: 10
      max-active: 20
      max-wait: 60000
  redis:
    host: REDIS_HOST
    port: 6379
    database: 0
    password: REPLACE_ME

jwt:
  issuer: UAV
  subject: CloudApi
  secret: REPLACE_WITH_A_LONG_RANDOM_SECRET
  age: 86400

mqtt:
  BASIC:
    protocol: MQTT
    host: MQTT_HOST
    port: 1883
    username: uav_cloud_service
    password: REPLACE_ME
    client-id: uav_cloud_service_prod
    path:

cloud-sdk:
  mqtt:
    inbound-topic: sys/product/+/status,thing/product/+/requests,thing/product/+/state

oss:
  enable: true
  provider: minio
  endpoint: http://MINIO_HOST:9100
  access-key: REPLACE_ME
  secret-key: REPLACE_ME
  bucket: uav-store
  expire: 3600
  region:
  object-dir-prefix: wayline

cloud-api:
  app:
    id: REPLACE_ME
    key: REPLACE_ME
    license: REPLACE_ME

logging:
  level:
    com.uav: info
  file:
    name: logs/cloud-service.log
```

必须继续保留原始 `application.yml` 中的 `url.*` 和需要使用的 `livestream.*` 配置。最安全的方式是复制完整文件后逐项替换，而不是只保存上面的片段。

检查敏感字段是否仍是示例值：

```bash
sudo grep -nE 'xx|REPLACE_ME|Please enter|CloudApiSample' /etc/uav-cloud/application.yml
```

生产配置中不应残留这些占位值。

## 12. 安装应用文件

创建低权限运行用户：

```bash
sudo useradd --system --home-dir /opt/uav-cloud --shell /usr/sbin/nologin uav-cloud
```

如果用户已经存在，该命令会提示错误，可以忽略并继续。

创建目录：

```bash
sudo mkdir -p /opt/uav-cloud/releases/1.10.0
sudo mkdir -p /var/log/uav-cloud
sudo install -m 640 cloud-service/target/cloud-service-1.10.0.jar \
  /opt/uav-cloud/releases/1.10.0/cloud-service.jar
sudo ln -sfn /opt/uav-cloud/releases/1.10.0 /opt/uav-cloud/current
sudo chown -R uav-cloud:uav-cloud /opt/uav-cloud /var/log/uav-cloud
sudo chown root:uav-cloud /etc/uav-cloud/application.yml
sudo chmod 640 /etc/uav-cloud/application.yml
```

发布目录采用版本化结构，便于升级和回滚：

```text
/opt/uav-cloud/
├── current -> /opt/uav-cloud/releases/1.10.0
└── releases/
    └── 1.10.0/
        └── cloud-service.jar
```

## 13. 启动前手工测试

先以前台方式运行，能最快看到配置问题：

```bash
cd /opt/uav-cloud/current
sudo -u uav-cloud /usr/bin/java \
  -Xms512m -Xmx2g \
  -jar cloud-service.jar \
  --spring.config.additional-location=file:/etc/uav-cloud/application.yml
```

重点检查：

- 没有 `UnsupportedClassVersionError`。
- MySQL、Redis、MQTT 和 OSS 没有连接异常。
- 日志出现 Spring Boot 启动完成信息。
- TCP 9000 开始监听。

按 `Ctrl+C` 停止手工进程，然后再配置 systemd。

## 14. 安装 systemd 服务

创建 `/etc/systemd/system/uav-cloud.service`：

```ini
[Unit]
Description=UAV Cloud API Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=uav-cloud
Group=uav-cloud
WorkingDirectory=/opt/uav-cloud/current
ExecStart=/usr/bin/java -Xms512m -Xmx2g -jar /opt/uav-cloud/current/cloud-service.jar --spring.config.additional-location=file:/etc/uav-cloud/application.yml
SuccessExitStatus=143
Restart=on-failure
RestartSec=10
TimeoutStopSec=30
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
```

如果 `java` 不在 `/usr/bin/java`，使用 `command -v java` 获取真实路径并修改 `ExecStart`。

加载并启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable uav-cloud
sudo systemctl start uav-cloud
sudo systemctl status uav-cloud --no-pager
```

查看实时日志：

```bash
sudo journalctl -u uav-cloud -f
```

查看最近 200 行：

```bash
sudo journalctl -u uav-cloud -n 200 --no-pager
```

## 15. 防火墙与反向代理

如果客户端直接访问应用，需要只对可信网段开放 9000。

使用 firewalld：

```bash
sudo firewall-cmd --permanent --add-port=9000/tcp
sudo firewall-cmd --reload
```

使用 UFW：

```bash
sudo ufw allow from <可信网段> to any port 9000 proto tcp
```

生产环境更推荐用 Nginx/负载均衡器终止 HTTPS，并将 HTTP 和 WebSocket 都转发到 `127.0.0.1:9000`。WebSocket 端点是：

```text
/api/v1/ws?x-auth-token=<JWT>
```

Nginx location 至少需要传递 Upgrade 头：

```nginx
location / {
    proxy_pass http://127.0.0.1:9000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 300s;
}
```

## 16. 上线验证

### 16.1 进程和端口

```bash
systemctl is-active uav-cloud
ss -lntp | grep ':9000'
```

### 16.2 登录接口

SQL 脚本包含本地演示账号，可用于首次验证：

```bash
curl -sS -X POST http://127.0.0.1:9000/manage/api/v1/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Yoox@123456","flag":1}'
```

成功响应应包含 access token。随后使用返回的 token：

```bash
curl -sS http://127.0.0.1:9000/manage/api/v1/workspaces/current \
  -H 'x-auth-token: <ACCESS_TOKEN>'
```

### 16.3 外部依赖

```bash
nc -vz <MYSQL_HOST> 3306
nc -vz <REDIS_HOST> 6379
nc -vz <MQTT_HOST> <MQTT_PORT>
curl -I http://<MINIO_HOST>:9100/minio/health/live
```

### 16.4 设备链路

设备接入后确认：

1. 服务日志收到 `sys/product/{sn}/status`。
2. Redis 出现设备在线 key。
3. 服务动态订阅设备的 state、OSD、events、requests 等 Topic。
4. WebSocket 客户端收到设备上线和 OSD 消息。
5. HTTP 控制请求能收到 MQTT reply，而不是超时。

## 17. 升级流程

假设升级版本为 `1.10.1`：

```bash
sudo mkdir -p /opt/uav-cloud/releases/1.10.1
sudo install -m 640 cloud-service-1.10.1.jar \
  /opt/uav-cloud/releases/1.10.1/cloud-service.jar
sudo chown -R uav-cloud:uav-cloud /opt/uav-cloud/releases/1.10.1
```

升级前：

1. 备份 MySQL。
2. 保存当前配置和 JAR 校验和。
3. 确认没有即将执行的关键航线任务。
4. 检查新版本数据库变更脚本。

切换：

```bash
sudo systemctl stop uav-cloud
sudo ln -sfn /opt/uav-cloud/releases/1.10.1 /opt/uav-cloud/current
sudo systemctl start uav-cloud
sudo systemctl status uav-cloud --no-pager
```

完成登录、WebSocket、MQTT 和设备在线验证后再结束维护窗口。

## 18. 回滚流程

如果新版本启动或业务验证失败：

```bash
sudo systemctl stop uav-cloud
sudo ln -sfn /opt/uav-cloud/releases/1.10.0 /opt/uav-cloud/current
sudo systemctl start uav-cloud
sudo systemctl status uav-cloud --no-pager
```

如果升级包含不兼容数据库变更，还必须使用对应的数据库回滚脚本或恢复备份。仅切换旧 JAR 不一定足够。

## 19. 备份建议

至少备份：

- MySQL `cloud_sample` 数据库。
- `/etc/uav-cloud/application.yml`，加密保存。
- 对象存储 bucket。
- 每个已发布版本的 JAR 和 SHA-256。
- MQTT Broker 账号、ACL 和证书配置。
- Redis 持久化数据；是否恢复 Redis 需结合任务状态评估。

MySQL 示例：

```bash
mysqldump -h <MYSQL_HOST> -u uav_cloud -p \
  --single-transaction --routines --triggers cloud_sample \
  > cloud_sample_$(date +%Y%m%d_%H%M%S).sql
```

备份文件中可能包含用户、设备和任务信息，必须限制权限并加密传输。

## 20. 常见故障排查

| 现象 | 常见原因 | 处理 |
|---|---|---|
| `uav-framework:pom:${revision}` 无法解析 | 子模块父版本仍是 `${revision}` | 按第 5 节固定父版本并重新 `install` |
| `UnsupportedClassVersionError` | 运行 JDK 低于 17 | 切换到 JDK 17 |
| Lombok 的 `log` 字段无法生成 | 使用过新的 JDK 或注解处理异常 | 确认 Maven 使用 JDK 17 |
| `no main manifest attribute` | JAR 未执行 Spring Boot repackage | 执行第 6.3 节命令 |
| MySQL `Unknown database` | SQL 创建 `cloud_sample`，配置使用其他库名 | 统一数据库名 |
| 应用端口启动失败 | 应用和 MinIO 同占 9000 | 修改 MinIO endpoint 或应用端口 |
| 登录一直 401 | 请求头错误或 JWT 配置变化 | 登录接口不带 token；后续使用 `x-auth-token` |
| MQTT 控制请求超时 | Topic ACL、设备离线、Broker 不通或 reply 未回到本实例 | 检查 Broker ACL、动态订阅和 `tid`/`bid` |
| 设备频繁离线 | Redis TTL 未刷新、OSD/状态消息中断、服务器时间异常 | 检查 Redis、MQTT 和时间同步 |
| 文件上传失败 | endpoint 对设备不可达、bucket/权限/CORS 错误 | 检查预签名 URL、凭证和外部地址 |
| 航线任务重启后异常 | Redis 数据丢失或多实例重复调度 | 检查持久化、任务 key 和调度策略 |

## 21. 生产上线检查表

- [ ] Maven 和运行时均使用 JDK 17。
- [ ] 已固定子模块父 POM 版本或配置 flatten 插件。
- [ ] Framework 与主工程构建成功。
- [ ] JAR Manifest 包含 Spring Boot Launcher 和正确 Start-Class。
- [ ] 数据库名统一为 `cloud_sample` 或统一的自定义名称。
- [ ] MySQL、Redis、MQTT 和 OSS 均通过连通性测试。
- [ ] 应用与 MinIO 没有端口冲突。
- [ ] 所有 `xx`、`REPLACE_ME` 和默认密钥均已替换。
- [ ] JWT secret 已改为足够长的随机值。
- [ ] MQTT/DRC 示例密码已经替换。
- [ ] SQL 演示账号密码已修改。
- [ ] `/etc/uav-cloud/application.yml` 权限不高于 `640`。
- [ ] 9000 未直接暴露到不可信公网，或已配置 HTTPS 反向代理。
- [ ] WebSocket Upgrade 转发正常。
- [ ] systemd 已设置开机启动和失败重启。
- [ ] MySQL、OSS 和配置文件已有备份。
- [ ] 已实际验证设备上线、OSD、控制 reply 和文件上传。

## 22. 最短部署命令摘要

完成 POM 修复和基础设施配置后，核心命令是：

```bash
cd /srv/uav-cloud-src

mvn -f uav-framework/pom.xml clean install -DskipTests
mvn clean install -DskipTests
mvn -f cloud-service/pom.xml clean package spring-boot:repackage -DskipTests

mysql -h <MYSQL_HOST> -u uav_cloud -p < sql/cloud_api.sql

sudo mkdir -p /opt/uav-cloud/releases/1.10.0 /etc/uav-cloud
sudo install -m 640 cloud-service/target/cloud-service-1.10.0.jar \
  /opt/uav-cloud/releases/1.10.0/cloud-service.jar
sudo ln -sfn /opt/uav-cloud/releases/1.10.0 /opt/uav-cloud/current

sudo systemctl daemon-reload
sudo systemctl enable --now uav-cloud
sudo journalctl -u uav-cloud -f
```

部署完成不应只以“进程已启动”为标准。MySQL、Redis、MQTT、OSS、WebSocket 和真实设备链路全部验证通过，才算完成上线。
