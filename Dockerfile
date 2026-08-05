# 语法指令，启用 BuildKit cache mount
# syntax=docker/dockerfile:1

# ============ 阶段1：构建 framework ============
FROM maven:3.9-eclipse-temurin-17 AS framework-builder

WORKDIR /build
COPY docker/maven-settings.xml /tmp/maven-settings.xml
COPY uav-framework/ ./uav-framework/

# 固定子模块父版本，解决 ${revision} 无法解析的问题
# -s 指定阿里云镜像配置，--mount=cache 持久化依赖缓存
RUN --mount=type=cache,target=/root/.m2 \
    find uav-framework -name pom.xml -exec sed -i \
    's|<version>${revision}</version>|<version>1.0.0</version>|g' {} + \
    && mvn -s /tmp/maven-settings.xml -f uav-framework/pom.xml clean install -DskipTests -q

# ============ 阶段2：构建主工程 ============
FROM framework-builder AS app-builder

WORKDIR /build
COPY docker/maven-settings.xml /tmp/maven-settings.xml
COPY pom.xml ./
COPY cloud-api/ ./cloud-api/
COPY cloud-service/ ./cloud-service/

RUN --mount=type=cache,target=/root/.m2 \
    sed -i \
    's|<version>${revision}</version>|<version>1.10.0</version>|g' \
    pom.xml cloud-api/pom.xml cloud-service/pom.xml \
    && mvn -s /tmp/maven-settings.xml clean install -DskipTests -q \
    && mvn -s /tmp/maven-settings.xml -f cloud-service/pom.xml clean package spring-boot:repackage -DskipTests -q

# ============ 阶段3：运行时（用已缓存的 jammy，无需 apt-get）============
FROM eclipse-temurin:17-jre-jammy

WORKDIR /app
COPY --from=app-builder /build/cloud-service/target/cloud-service-1.10.0.jar app.jar
RUN mkdir -p /app/logs

EXPOSE 9000

ENV JAVA_OPTS="-Xms256m -Xmx768m -XX:MaxMetaspaceSize=256m -XX:+UseG1GC"

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar --spring.config.additional-location=file:/app/config/application.yml"]
