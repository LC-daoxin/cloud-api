package com.uav.service.control.service.impl;

import com.uav.service.control.model.param.DronePayloadParam;

import java.util.Objects;

public class CameraScreenDragImpl extends PayloadCommandsHandler {

    public CameraScreenDragImpl(DronePayloadParam param) {
        super(param);
    }

    @Override
    public boolean valid() {
        return Objects.nonNull(param.getLocked())
                && Objects.nonNull(param.getPitchSpeed())
                && Objects.nonNull(param.getYawSpeed());
    }

    @Override
    public boolean canPublish(String deviceSn) {
        // RC+无人机场景下 OsdDockDrone OSD 缓存不存在，与 GimbalResetImpl 一致直接放行。
        try {
            return super.canPublish(deviceSn);
        } catch (RuntimeException e) {
            if (e.getMessage() != null && (e.getMessage().contains("offline") ||
                    e.getMessage().contains("camera"))) {
                return true;
            }
            throw e;
        }
    }
}
