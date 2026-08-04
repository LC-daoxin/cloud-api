package com.uav.great.mqtt.model.control;


import com.uav.great.mqtt.enums.device.CameraModeEnum;

public class PhotoTakeProgressExt {

    private CameraModeEnum cameraMode;

    public PhotoTakeProgressExt() {
    }

    @Override
    public String toString() {
        return "PhotoTakeProgressExt{" +
                "cameraMode=" + cameraMode +
                '}';
    }

    public CameraModeEnum getCameraMode() {
        return cameraMode;
    }

    public PhotoTakeProgressExt setCameraMode(CameraModeEnum cameraMode) {
        this.cameraMode = cameraMode;
        return this;
    }
}
