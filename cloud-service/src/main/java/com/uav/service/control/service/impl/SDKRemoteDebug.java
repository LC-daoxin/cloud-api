package com.uav.service.control.service.impl;

import com.uav.api.debug.AbstractDebugService;
import com.uav.great.mqtt.model.debug.RemoteDebugProgress;
import com.uav.great.websocket.enums.UserTypeEnum;
import com.uav.great.websocket.service.IWebSocketMessageService;
import com.uav.great.mqtt.core.EventsReceiver;
import com.uav.service.manage.model.dto.DeviceDTO;
import com.uav.service.manage.service.IDeviceRedisService;
import com.uav.great.mqtt.core.consume.MqttReply;
import com.uav.great.mqtt.handle.events.EventsDataRequest;
import com.uav.great.mqtt.handle.events.TopicEventsRequest;
import com.uav.great.mqtt.handle.events.TopicEventsResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.MessageHeaders;
import org.springframework.stereotype.Service;

import java.util.Optional;

@Service
@Slf4j
public class SDKRemoteDebug extends AbstractDebugService {

    @Autowired
    private IWebSocketMessageService webSocketMessageService;

    @Autowired
    private IDeviceRedisService deviceRedisService;

    @Override
    public TopicEventsResponse<MqttReply> remoteDebugProgress(TopicEventsRequest<EventsDataRequest<RemoteDebugProgress>> request, MessageHeaders headers) {
        String sn = request.getGateway();

        EventsReceiver<RemoteDebugProgress> eventsReceiver = new EventsReceiver<RemoteDebugProgress>()
                .setOutput(request.getData().getOutput()).setResult(request.getData().getResult());
        eventsReceiver.setBid(request.getBid());
        eventsReceiver.setSn(sn);

        log.info("SN: {}, {} ===> Control progress: {}", sn, request.getMethod(), eventsReceiver.getOutput().getProgress());

        if (!eventsReceiver.getResult().isSuccess()) {
            log.error("SN: {}, {} ===> Error: {}", sn, request.getMethod(), eventsReceiver.getResult());
        }

        Optional<DeviceDTO> deviceOpt = deviceRedisService.getDeviceOnline(sn);

        if (deviceOpt.isEmpty()) {
            throw new RuntimeException("The device is offline.");
        }

        DeviceDTO device = deviceOpt.get();
        webSocketMessageService.sendBatch(device.getWorkspaceId(), UserTypeEnum.WEB.getVal(),
                request.getMethod(), eventsReceiver);

        return new TopicEventsResponse<MqttReply>().setData(MqttReply.success());
    }
}
