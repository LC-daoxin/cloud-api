package com.uav.api.airsense;

import com.uav.great.context.annotations.CloudSDKVersion;
import com.uav.great.context.enums.version.CloudSDKVersionEnum;
import com.uav.great.mqtt.core.consume.MqttReply;
import com.uav.great.mqtt.constant.ChannelName;
import com.uav.great.mqtt.handle.events.TopicEventsRequest;
import com.uav.great.mqtt.handle.events.TopicEventsResponse;
import com.uav.great.mqtt.model.airsense.AirsenseWarning;
import org.springframework.integration.annotation.ServiceActivator;
import org.springframework.messaging.MessageHeaders;

import java.util.List;

public abstract class AbstractAirsenseService {

    @ServiceActivator(inputChannel = ChannelName.INBOUND_EVENTS_AIRSENSE_WARNING, outputChannel = ChannelName.OUTBOUND_EVENTS)
    @CloudSDKVersion(since = CloudSDKVersionEnum.V1_0_0)
    public TopicEventsResponse<MqttReply> airsenseWarning(TopicEventsRequest<List<AirsenseWarning>> request, MessageHeaders headers) {
        throw new UnsupportedOperationException("airsenseWarning not implemented");
    }

}
