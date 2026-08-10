package com.uav.service.control.service.impl;

import com.uav.service.control.model.param.DronePayloadParam;

import java.util.Objects;

public class CameraLookAtImpl extends PayloadCommandsHandler {

    public CameraLookAtImpl(DronePayloadParam param) {
        super(param);
    }

    @Override
    public boolean valid() {
        return Objects.nonNull(param.getLocked())
                && Objects.nonNull(param.getLatitude())
                && Objects.nonNull(param.getLongitude())
                && Objects.nonNull(param.getHeight());
    }
}
