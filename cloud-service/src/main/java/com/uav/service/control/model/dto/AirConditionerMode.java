package com.uav.service.control.model.dto;

import com.uav.great.mqtt.enums.device.AirConditionerStateEnum;
import com.uav.service.control.service.impl.RemoteDebugHandler;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

@EqualsAndHashCode(callSuper = true)
@Data
@AllArgsConstructor
@NoArgsConstructor
public class AirConditionerMode extends RemoteDebugHandler {

    private AirConditionerStateEnum action;
}
