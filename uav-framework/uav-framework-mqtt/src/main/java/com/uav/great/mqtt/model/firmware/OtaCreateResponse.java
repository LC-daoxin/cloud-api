package com.uav.great.mqtt.model.firmware;

import com.uav.great.mqtt.enums.firmware.OtaProgressStatusEnum;

public class OtaCreateResponse {

    /**
     * Mission status
     **/
    private OtaProgressStatusEnum status;

    public OtaCreateResponse() {
    }

    @Override
    public String toString() {
        return "OtaCreateResponse{" +
                "status=" + status +
                '}';
    }

    public OtaProgressStatusEnum getStatus() {
        return status;
    }

    public OtaCreateResponse setStatus(OtaProgressStatusEnum status) {
        this.status = status;
        return this;
    }
}
