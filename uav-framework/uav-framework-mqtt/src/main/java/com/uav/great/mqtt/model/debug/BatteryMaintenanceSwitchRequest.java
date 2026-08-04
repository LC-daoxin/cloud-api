package com.uav.great.mqtt.model.debug;

import com.uav.great.context.base.BaseModel;
import com.uav.great.mqtt.enums.device.SwitchActionEnum;

import javax.validation.constraints.NotNull;

public class BatteryMaintenanceSwitchRequest extends BaseModel {

    @NotNull
    private SwitchActionEnum action;

    public BatteryMaintenanceSwitchRequest() {
    }

    @Override
    public String toString() {
        return "BatteryMaintenanceSwitchRequest{" +
                "action=" + action +
                '}';
    }

    public SwitchActionEnum getAction() {
        return action;
    }

    public BatteryMaintenanceSwitchRequest setAction(SwitchActionEnum action) {
        this.action = action;
        return this;
    }
}
