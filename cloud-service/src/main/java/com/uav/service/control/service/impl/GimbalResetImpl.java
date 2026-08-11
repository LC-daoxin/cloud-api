package com.uav.service.control.service.impl;

import com.uav.service.control.model.param.DronePayloadParam;

import java.util.Objects;

public class GimbalResetImpl extends PayloadCommandsHandler {
    public GimbalResetImpl(DronePayloadParam param) {
        super(param);
    }

    @Override
    public boolean valid() {
        return Objects.nonNull(param.getResetMode());
    }

    @Override
    public boolean canPublish(String deviceSn) {
        // RC+无人机场景下 OsdDockDrone OSD 缓存不存在，云台复位无需校验 camera OSD，直接放行。
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
