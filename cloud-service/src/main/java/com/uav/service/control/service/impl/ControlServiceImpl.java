package com.uav.service.control.service.impl;


import com.uav.api.control.AbstractControlService;

import com.uav.api.debug.AbstractDebugService;

import com.uav.great.context.exception.CloudSDKErrorEnum;
import com.uav.great.context.response.HttpResultResponse;
import com.uav.great.context.enums.version.GatewayManager;
import com.uav.great.context.enums.version.GatewayTypeEnum;
import com.uav.great.mqtt.enums.debug.DebugMethodEnum;
import com.uav.great.mqtt.enums.device.DockModeCodeEnum;
import com.uav.great.mqtt.enums.device.DroneModeCodeEnum;
import com.uav.great.mqtt.enums.control.PayloadControlMethodEnum;
import com.uav.great.mqtt.model.control.CameraLookAtRequest;
import com.uav.great.mqtt.model.control.CameraScreenDragRequest;
import com.uav.great.mqtt.model.control.FlyToPointRequest;
import com.uav.great.mqtt.model.control.PayloadAuthorityGrabRequest;
import com.uav.great.mqtt.model.control.TakeoffToPointRequest;
import com.uav.great.mqtt.model.device.PayloadIndex;
import com.uav.great.websocket.service.IWebSocketMessageService;
import com.uav.great.mqtt.handle.services.ServicesReplyData;
import com.uav.great.mqtt.handle.services.TopicServicesResponse;
import com.uav.great.mqtt.core.SDKManager;
import com.uav.service.control.model.enums.DroneAuthorityEnum;
import com.uav.service.control.model.enums.RemoteDebugMethodEnum;
import com.uav.service.control.model.param.*;
import com.uav.service.control.service.IControlService;
import com.uav.service.manage.model.dto.DeviceDTO;
import com.uav.service.manage.service.IDevicePayloadService;
import com.uav.service.manage.service.IDeviceRedisService;
import com.uav.service.manage.service.IDeviceService;
import com.uav.api.wayline.AbstractWaylineService;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Service;

import com.uav.great.mqtt.enums.control.ControlSourceEnum;
import com.uav.service.manage.model.dto.DevicePayloadReceiver;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;

@Service
@Slf4j
public class ControlServiceImpl implements IControlService {

    @Autowired
    private IWebSocketMessageService webSocketMessageService;

    @Autowired
    private IDeviceService deviceService;

    @Autowired
    private IDeviceRedisService deviceRedisService;

    @Autowired
    private ObjectMapper mapper;

    @Autowired
    private IDevicePayloadService devicePayloadService;

    @Autowired
    private AbstractControlService abstractControlService;

    @Autowired
    private AbstractDebugService abstractDebugService;

    @Autowired
    @Qualifier("SDKWaylineService")
    private AbstractWaylineService abstractWaylineService;

    private RemoteDebugHandler checkDebugCondition(String sn, RemoteDebugParam param, RemoteDebugMethodEnum controlMethodEnum) {
        RemoteDebugHandler handler = Objects.nonNull(controlMethodEnum.getClazz()) ?
                mapper.convertValue(Objects.nonNull(param) ? param : new Object(), controlMethodEnum.getClazz())
                : new RemoteDebugHandler();
        if (!handler.canPublish(sn)) {
            throw new RuntimeException("The current state of the dock does not support this function.");
        }
        return handler;
    }

    @Override
    public HttpResultResponse controlDockDebug(String sn, RemoteDebugMethodEnum controlMethodEnum, RemoteDebugParam param) {
        DebugMethodEnum methodEnum = controlMethodEnum.getDebugMethodEnum();
        RemoteDebugHandler data = checkDebugCondition(sn, param, controlMethodEnum);
        GatewayManager gateway = SDKManager.getDeviceSDK(sn);

        boolean isExist = deviceRedisService.checkDeviceOnline(sn);
        if (!isExist) {
            return HttpResultResponse.error("The dock is offline.");
        }
        TopicServicesResponse response;
        switch (controlMethodEnum) {
            case RETURN_HOME:
                response = isRc(gateway)
                        ? abstractWaylineService.returnHomeRc(gateway)
                        : abstractWaylineService.returnHome(gateway);
                break;
            case RETURN_HOME_CANCEL:
                response = isRc(gateway)
                        ? abstractWaylineService.returnHomeCancelRc(gateway)
                        : abstractWaylineService.returnHomeCancel(gateway);
                break;
            default:
                response = abstractDebugService.remoteDebug(gateway, methodEnum,
                        Objects.nonNull(methodEnum.getClazz()) ? mapper.convertValue(data, methodEnum.getClazz()) : null);
        }
        ServicesReplyData serviceReply = (ServicesReplyData) response.getData();
        if (!serviceReply.getResult().isSuccess()) {
            return HttpResultResponse.error(serviceReply.getResult());
        }
        return HttpResultResponse.success();
    }

    private void checkFlyToCondition(String dockSn) {
        // TODO 设备固件版本不兼容情况
        Optional<DeviceDTO> dockOpt = deviceRedisService.getDeviceOnline(dockSn);
        if (dockOpt.isEmpty()) {
            throw new RuntimeException("The dock is offline, please restart the dock.");
        }

        DroneModeCodeEnum deviceMode = deviceService.getDeviceMode(dockOpt.get().getChildDeviceSn());
        if (DroneModeCodeEnum.MANUAL != deviceMode) {
            throw new RuntimeException("The current state of the drone does not support this function, please try again later.");
        }

        HttpResultResponse result = seizeAuthority(dockSn, DroneAuthorityEnum.FLIGHT, null);
        if (HttpResultResponse.CODE_SUCCESS != result.getCode()) {
            throw new IllegalArgumentException(result.getMessage());
        }
    }

    @Override
    public HttpResultResponse flyToPoint(String sn, FlyToPointParam param) {
        checkFlyToCondition(sn);

        param.setFlyToId(UUID.randomUUID().toString());
        GatewayManager gateway = SDKManager.getDeviceSDK(sn);
        FlyToPointRequest request = mapper.convertValue(param, FlyToPointRequest.class);
        TopicServicesResponse<ServicesReplyData> response = isRc(gateway)
                ? abstractControlService.flyToPointRc(gateway, request)
                : abstractControlService.flyToPoint(gateway, request);
        ServicesReplyData reply = response.getData();
        return reply.getResult().isSuccess() ?
                HttpResultResponse.success()
                : HttpResultResponse.error("Flying to the target point failed. " + reply.getResult());
    }

    @Override
    public HttpResultResponse flyToPointStop(String sn) {
        GatewayManager gateway = SDKManager.getDeviceSDK(sn);
        TopicServicesResponse<ServicesReplyData> response = isRc(gateway)
                ? abstractControlService.flyToPointStopRc(gateway)
                : abstractControlService.flyToPointStop(gateway);
        ServicesReplyData reply = response.getData();

        return reply.getResult().isSuccess() ?
                HttpResultResponse.success()
                : HttpResultResponse.error("The drone flying to the target point failed to stop. " + reply.getResult());
    }

    private void checkTakeoffCondition(String dockSn) {
        Optional<DeviceDTO> dockOpt = deviceRedisService.getDeviceOnline(dockSn);
        if (dockOpt.isEmpty()) {
            throw new RuntimeException("The current state does not support takeoff.");
        }
        GatewayManager gateway = SDKManager.getDeviceSDK(dockSn);
        boolean ready = isRc(gateway)
                ? DroneModeCodeEnum.IDLE == deviceService.getDeviceMode(dockOpt.get().getChildDeviceSn())
                : DockModeCodeEnum.IDLE == deviceService.getDockMode(dockSn);
        if (!ready) {
            throw new RuntimeException("The current state does not support takeoff.");
        }

        HttpResultResponse result = seizeAuthority(dockSn, DroneAuthorityEnum.FLIGHT, null);
        if (HttpResultResponse.CODE_SUCCESS != result.getCode()) {
            throw new IllegalArgumentException(result.getMessage());
        }

    }

    @Override
    public HttpResultResponse takeoffToPoint(String sn, TakeoffToPointParam param) {
        checkTakeoffCondition(sn);

        param.setFlightId(UUID.randomUUID().toString());
        GatewayManager gateway = SDKManager.getDeviceSDK(sn);
        TakeoffToPointRequest request = mapper.convertValue(param, TakeoffToPointRequest.class);
        TopicServicesResponse<ServicesReplyData> response = isRc(gateway)
                ? abstractControlService.takeoffToPointRc(gateway, request)
                : abstractControlService.takeoffToPoint(gateway, request);
        ServicesReplyData reply = response.getData();
        return reply.getResult().isSuccess() ?
                HttpResultResponse.success()
                : HttpResultResponse.error("The drone failed to take off. " + reply.getResult());
    }

    @Override
    public HttpResultResponse seizeAuthority(String sn, DroneAuthorityEnum authority, DronePayloadParam param) {
        GatewayManager gateway = SDKManager.getDeviceSDK(sn);
        TopicServicesResponse<ServicesReplyData> response;
        switch (authority) {
            case FLIGHT:
                if (deviceService.checkAuthorityFlight(sn)) {
                    return HttpResultResponse.success();
                }
                response = isRc(gateway)
                        ? abstractControlService.flightAuthorityGrabRc(gateway)
                        : abstractControlService.flightAuthorityGrab(gateway);
                break;
            case PAYLOAD:
                if (checkPayloadAuthority(sn, param.getPayloadIndex())) {
                    return HttpResultResponse.success();
                }
                PayloadAuthorityGrabRequest request = new PayloadAuthorityGrabRequest()
                        .setPayloadIndex(new PayloadIndex(param.getPayloadIndex()));
                response = isRc(gateway)
                        ? abstractControlService.payloadAuthorityGrabRc(gateway, request)
                        : abstractControlService.payloadAuthorityGrab(gateway, request);
                break;
            default:
                return HttpResultResponse.error(CloudSDKErrorEnum.INVALID_PARAMETER);
        }

        ServicesReplyData serviceReply = response.getData();
        if (!serviceReply.getResult().isSuccess()) {
            return HttpResultResponse.error(serviceReply.getResult());
        }
        // RC 기기는 payload_authority_grab 후 control_source 상태 메시지를 보내지 않아
        // DB/Redis가 갱신되지 않는 문제 해결: grab 성공 시 직접 A로 업데이트한다.
        if (DroneAuthorityEnum.PAYLOAD == authority) {
            deviceRedisService.getDeviceOnline(sn).map(DeviceDTO::getChildDeviceSn)
                    .flatMap(deviceRedisService::getDeviceOnline)
                    .ifPresent(drone -> devicePayloadService.updatePayloadControl(drone,
                            List.of(DevicePayloadReceiver.builder()
                                    .payloadIndex(new PayloadIndex(param.getPayloadIndex()))
                                    .controlSource(ControlSourceEnum.A)
                                    .deviceSn(drone.getDeviceSn())
                                    .sn(drone.getDeviceSn() + "-" +
                                            new PayloadIndex(param.getPayloadIndex()).getPosition().getPosition())
                                    .build())));
        }
        return HttpResultResponse.success();
    }

    private Boolean checkPayloadAuthority(String sn, String payloadIndex) {
        Optional<DeviceDTO> dockOpt = deviceRedisService.getDeviceOnline(sn);
        if (dockOpt.isEmpty()) {
            throw new RuntimeException("The dock is offline, please restart the dock.");
        }
        return devicePayloadService.checkAuthorityPayload(dockOpt.get().getChildDeviceSn(), payloadIndex);
    }

    @Override
    public HttpResultResponse payloadCommands(PayloadCommandsParam param) throws Exception {
        param.getCmd().getClazz()
                .getDeclaredConstructor(DronePayloadParam.class)
                .newInstance(param.getData())
                .checkCondition(param.getSn());

        GatewayManager gateway = SDKManager.getDeviceSDK(param.getSn());
        PayloadControlMethodEnum command = param.getCmd().getCmd();
        TopicServicesResponse<ServicesReplyData> response;
        if (isRc(gateway) && PayloadControlMethodEnum.CAMERA_LOOK_AT == command) {
            response = abstractControlService.cameraLookAtRc(
                    gateway, mapper.convertValue(param.getData(), CameraLookAtRequest.class));
        } else if (isRc(gateway) && PayloadControlMethodEnum.CAMERA_SCREEN_DRAG == command) {
            // RC 网关下负载指令需 device_list 寻址无人机，否则指令被静默丢弃（211001）。
            response = abstractControlService.cameraScreenDragRc(
                    gateway, mapper.convertValue(param.getData(), CameraScreenDragRequest.class));
        } else {
            response = abstractControlService.payloadControl(
                    gateway, command, mapper.convertValue(param.getData(), command.getClazz()));
        }

        ServicesReplyData serviceReply = response.getData();
        return serviceReply.getResult().isSuccess() ?
                HttpResultResponse.success()
                : HttpResultResponse.error(serviceReply.getResult());
    }

    private boolean isRc(GatewayManager gateway) {
        return GatewayTypeEnum.RC == gateway.getType();
    }
}
