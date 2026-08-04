package com.uav.api.config;


import com.uav.great.mqtt.constant.ChannelName;
import com.uav.great.mqtt.model.config.ProductConfigResponse;
import com.uav.great.mqtt.model.config.RequestsConfigRequest;
import com.uav.great.mqtt.handle.requests.TopicRequestsRequest;
import com.uav.great.mqtt.handle.requests.TopicRequestsResponse;
import org.springframework.integration.annotation.ServiceActivator;
import org.springframework.messaging.MessageHeaders;

public abstract class AbstractConfigService {

    @ServiceActivator(inputChannel = ChannelName.INBOUND_REQUESTS_CONFIG, outputChannel = ChannelName.OUTBOUND_REQUESTS)
    public TopicRequestsResponse<ProductConfigResponse> requestsConfig(TopicRequestsRequest<RequestsConfigRequest> request, MessageHeaders headers) {
        throw new UnsupportedOperationException("requestsConfig not implemented");
    }

}
