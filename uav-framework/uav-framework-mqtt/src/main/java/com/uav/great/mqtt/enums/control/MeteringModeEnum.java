package com.uav.great.mqtt.enums.control;

import com.uav.great.context.exception.CloudSDKException;
import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

import java.util.Arrays;

public enum MeteringModeEnum {

    DISABLE(0),

    SPOT(1),

    AREA(2),

    ;

    private final int mode;

    MeteringModeEnum(int mode) {
        this.mode = mode;
    }

    @JsonValue
    public int getMode() {
        return mode;
    }

    @JsonCreator
    public static MeteringModeEnum find(int mode) {
        return Arrays.stream(values()).filter(modeEnum -> modeEnum.mode == mode).findAny()
            .orElseThrow(() -> new CloudSDKException(MeteringModeEnum.class, mode));
    }

}
