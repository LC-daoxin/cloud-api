package com.uav.great.mqtt.property;

import com.uav.great.mqtt.enums.base.MqttProtocolEnum;
import lombok.Data;


@Data
public class MqttClientOptions {

    private MqttProtocolEnum protocol;

    private String host;

    private Integer port;

    private String username;

    private String password;

    private String clientId;

    private String path;

    private String inboundTopic;

    /**
     * 对外广播主机名：外部设备（Pilot App / 遥控器 / 无人机）访问 Broker 的地址。
     * 桥接网络（如 Docker Desktop for Mac）下容器无法回头访问宿主机 IP，
     * 应用自身连接的 host 与外部设备访问的地址必须分开配置。
     * 未配置（null/空串）时回退为 host。
     */
    private String externalHost;
}
