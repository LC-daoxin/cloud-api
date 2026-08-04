package com.uav.service.manage.service.impl;

import com.uav.api.config.AbstractConfigService;
import com.uav.great.context.error.CommonErrorEnum;
import com.uav.great.context.utils.SpringBeanUtilsTest;
import com.uav.great.mqtt.core.consume.MqttReply;
import com.uav.great.mqtt.model.config.ProductConfigResponse;
import com.uav.great.mqtt.model.config.RequestsConfigRequest;
import com.uav.great.mqtt.handle.requests.TopicRequestsRequest;
import com.uav.great.mqtt.handle.requests.TopicRequestsResponse;
import com.uav.service.manage.model.dto.ProductConfigDTO;
import com.uav.service.manage.model.enums.CustomizeConfigScopeEnum;
import org.springframework.messaging.MessageHeaders;
import org.springframework.stereotype.Service;

import java.util.Optional;

@Service
public class RequestConfigContext extends AbstractConfigService {

    @Override
    public TopicRequestsResponse<ProductConfigResponse> requestsConfig(TopicRequestsRequest<RequestsConfigRequest> request, MessageHeaders headers) {
        RequestsConfigRequest configReceiver = request.getData();
        Optional<CustomizeConfigScopeEnum> scopeEnumOpt = CustomizeConfigScopeEnum.find(configReceiver.getConfigScope().getScope());
        if (scopeEnumOpt.isEmpty()) {
            return new TopicRequestsResponse().setData(MqttReply.error(CommonErrorEnum.ILLEGAL_ARGUMENT));
        }

        ProductConfigDTO config = (ProductConfigDTO) SpringBeanUtilsTest.getBean(scopeEnumOpt.get().getClazz()).getConfig();
        return new TopicRequestsResponse<ProductConfigResponse>().setData(
                new ProductConfigResponse()
                        .setNtpServerHost(config.getNtpServerHost())
                        .setAppId(config.getAppId())
                        .setAppKey(config.getAppKey())
                        .setAppLicense(config.getAppLicense()));
    }
}
