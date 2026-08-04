package com.uav.great.mqtt.model.property;


import com.uav.great.context.base.BaseModel;

import javax.validation.Valid;
import javax.validation.constraints.NotNull;

public class DistanceLimitStatusSet extends BaseModel {

    @Valid
    @NotNull
    private DistanceLimitStatusData distanceLimitStatus;

    public DistanceLimitStatusSet() {
    }

    @Override
    public String toString() {
        return "DistanceLimitStatusSet{" +
                "distanceLimitStatus=" + distanceLimitStatus +
                '}';
    }

    public DistanceLimitStatusData getDistanceLimitStatus() {
        return distanceLimitStatus;
    }

    public DistanceLimitStatusSet setDistanceLimitStatus(DistanceLimitStatusData distanceLimitStatus) {
        this.distanceLimitStatus = distanceLimitStatus;
        return this;
    }
}
