package com.uav.great.mqtt.handle.drc;

import com.uav.great.context.enums.version.GatewayManager;
import com.uav.great.mqtt.core.subscribe.IMqttTopicService;
import com.uav.great.mqtt.constant.TopicConst;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;

@Component
public class DrcUpSubscribe {

    @Resource
    private IMqttTopicService topicService;

    public void subscribe(GatewayManager gateway) {
        String drc = TopicConst.THING_MODEL_PRE + TopicConst.PRODUCT + "%s" + TopicConst.DRC + TopicConst.UP;
        topicService.subscribe(String.format(drc, gateway.getGatewaySn()));
    }
}
