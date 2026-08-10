package com.uav.service.control.model.param;

import com.uav.great.mqtt.enums.control.CameraTypeEnum;
import com.uav.great.mqtt.enums.device.CameraModeEnum;
import com.uav.service.control.model.enums.GimbalResetModeEnum;
import lombok.Data;
import org.hibernate.validator.constraints.Range;

import javax.validation.constraints.NotNull;
import javax.validation.constraints.Pattern;

@Data
public class DronePayloadParam {

    @Pattern(regexp = "\\d+-\\d+-\\d+")
    @NotNull
    private String payloadIndex;

    private CameraTypeEnum cameraType;

    @Range(min = 2, max = 200)
    private Float zoomFactor;

    private CameraModeEnum cameraMode;

    private Boolean locked;

    private Double pitchSpeed;

    private Double yawSpeed;

    @Range(min = 0, max = 1)
    private Double x;

    @Range(min = 0, max = 1)
    private Double y;

    private GimbalResetModeEnum resetMode;

    @Range(min = -90, max = 90)
    private Double latitude;

    @Range(min = -180, max = 180)
    private Double longitude;

    @Range(min = 2, max = 10000)
    private Float height;
}
