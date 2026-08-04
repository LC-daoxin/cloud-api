package com.uav.great.mqtt.model.debug;


import com.uav.great.context.base.BaseModel;
import com.uav.great.mqtt.enums.debug.AirConditionerModeSwitchActionEnum;

import javax.validation.constraints.NotNull;

public class AirConditionerModeSwitchRequest extends BaseModel {

    @NotNull
    private AirConditionerModeSwitchActionEnum action;

    public AirConditionerModeSwitchRequest() {
    }

    @Override
    public String toString() {
        return "AirConditionerModeSwitchRequest{" +
                "action=" + action +
                '}';
    }

    public AirConditionerModeSwitchActionEnum getAction() {
        return action;
    }

    public AirConditionerModeSwitchRequest setAction(AirConditionerModeSwitchActionEnum action) {
        this.action = action;
        return this;
    }
}
