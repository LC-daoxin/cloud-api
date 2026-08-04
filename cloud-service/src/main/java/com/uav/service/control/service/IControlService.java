package com.uav.service.control.service;

import com.uav.great.context.response.HttpResultResponse;
import com.uav.service.control.model.enums.DroneAuthorityEnum;
import com.uav.service.control.model.enums.RemoteDebugMethodEnum;
import com.uav.service.control.model.param.*;

public interface IControlService {

    HttpResultResponse controlDockDebug(String sn, RemoteDebugMethodEnum serviceIdentifier, RemoteDebugParam param);

    HttpResultResponse flyToPoint(String sn, FlyToPointParam param);

    HttpResultResponse flyToPointStop(String sn);

    //    CommonTopicReceiver handleFlyToPointProgress(CommonTopicReceiver receiver, MessageHeaders headers);
    HttpResultResponse takeoffToPoint(String sn, TakeoffToPointParam param);

    HttpResultResponse seizeAuthority(String sn, DroneAuthorityEnum authority, DronePayloadParam param);

    HttpResultResponse payloadCommands(PayloadCommandsParam param) throws Exception;
}
