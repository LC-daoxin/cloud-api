package com.uav.great.mqtt.autoconfiguration;

import com.uav.great.context.utils.JwtUtil;
import com.uav.great.mqtt.enums.base.MqttProtocolEnum;
import com.uav.great.mqtt.enums.base.MqttUseEnum;
import com.uav.great.mqtt.property.DrcModeMqttBroker;
import com.uav.great.mqtt.property.MqttClientOptions;
import com.auth0.jwt.algorithms.Algorithm;
import lombok.Data;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.integration.mqtt.core.DefaultMqttPahoClientFactory;
import org.springframework.integration.mqtt.core.MqttPahoClientFactory;
import org.springframework.util.StringUtils;

import java.util.Map;

@Data
@Configuration
@ConfigurationProperties
public class MqttPropertyConfiguration {

    private static Map<MqttUseEnum, MqttClientOptions> mqtt;

    public void setMqtt(Map<MqttUseEnum, MqttClientOptions> mqtt) {
        MqttPropertyConfiguration.mqtt = mqtt;
    }

    static MqttClientOptions getBasicClientOptions() {
        if (!mqtt.containsKey(MqttUseEnum.BASIC)) {
            throw new Error("Please configure the basic mqtt connection parameters first, otherwise application cannot be started.");
        }
        return mqtt.get(MqttUseEnum.BASIC);
    }

    /**
     * 应用自身连接 Broker 使用的地址（容器内部，默认走 compose 服务名）。
     */
    public static String getBasicMqttAddress() {
        return getMqttAddress(getBasicClientOptions(), false);
    }

    /**
     * 返回给外部设备（Pilot App / 遥控器 / 无人机）的对外 Broker 地址。
     * 桥接网络下必须通过 external-host 单独配置宿主机局域网 IP，
     * 否则容器内地址对外部不可达。
     */
    public static String getBasicExternalMqttAddress() {
        return getMqttAddress(getBasicClientOptions(), true);
    }

    private static String getMqttAddress(MqttClientOptions options, boolean external) {
        String host = options.getHost();
        if (external && StringUtils.hasText(options.getExternalHost())) {
            host = options.getExternalHost();
        }
        StringBuilder addr = new StringBuilder()
                .append(options.getProtocol().getProtocolAddr())
                .append(host.trim())
                .append(":")
                .append(options.getPort());
        if ((options.getProtocol() == MqttProtocolEnum.WS || options.getProtocol() == MqttProtocolEnum.WSS)
                && StringUtils.hasText(options.getPath())) {
            addr.append(options.getPath());
        }
        return addr.toString();
    }

    public static DrcModeMqttBroker getMqttBrokerWithDrc(String clientId, String username, Long age, Map<String, ?> map) {
        if (!mqtt.containsKey(MqttUseEnum.DRC)) {
            throw new RuntimeException("Please configure the drc link parameters of mqtt in the backend configuration file first.");
        }
        Algorithm algorithm = JwtUtil.algorithm;

        String token = JwtUtil.createToken(map, age, algorithm, null, null);

        MqttClientOptions drcOptions = mqtt.get(MqttUseEnum.DRC);
        // DRC 地址返回给外部客户端使用；external-host 未单独配置时回退到 host
        String drcHost = drcOptions.getHost();
        if (StringUtils.hasText(drcOptions.getExternalHost())) {
            drcHost = drcOptions.getExternalHost();
        } else if (mqtt.containsKey(MqttUseEnum.BASIC)
                && StringUtils.hasText(mqtt.get(MqttUseEnum.BASIC).getExternalHost())) {
            drcHost = mqtt.get(MqttUseEnum.BASIC).getExternalHost();
        }
        return new DrcModeMqttBroker()
                .setAddress(getMqttAddressWithHost(drcOptions, drcHost))
                .setUsername(username)
                .setClientId(clientId)
                .setExpireTime(System.currentTimeMillis() / 1000 + age)
                .setPassword(token)
                .setEnableTls(false);
    }

    private static String getMqttAddressWithHost(MqttClientOptions options, String host) {
        StringBuilder addr = new StringBuilder()
                .append(options.getProtocol().getProtocolAddr())
                .append(host.trim())
                .append(":")
                .append(options.getPort());
        if ((options.getProtocol() == MqttProtocolEnum.WS || options.getProtocol() == MqttProtocolEnum.WSS)
                && StringUtils.hasText(options.getPath())) {
            addr.append(options.getPath());
        }
        return addr.toString();
    }


    @Bean
    public MqttConnectOptions mqttConnectOptions() {
        MqttClientOptions customizeOptions = getBasicClientOptions();
        MqttConnectOptions mqttConnectOptions = new MqttConnectOptions();
        mqttConnectOptions.setServerURIs(new String[]{getBasicMqttAddress()});
        mqttConnectOptions.setUserName(customizeOptions.getUsername());
        mqttConnectOptions.setPassword(StringUtils.hasText(customizeOptions.getPassword()) ?
                customizeOptions.getPassword().toCharArray() : new char[0]);
        mqttConnectOptions.setAutomaticReconnect(true);
        mqttConnectOptions.setKeepAliveInterval(10);
        return mqttConnectOptions;
    }

    @Bean
    public MqttPahoClientFactory mqttClientFactory() {
        DefaultMqttPahoClientFactory factory = new DefaultMqttPahoClientFactory();
        factory.setConnectionOptions(mqttConnectOptions());
        return factory;
    }
}
