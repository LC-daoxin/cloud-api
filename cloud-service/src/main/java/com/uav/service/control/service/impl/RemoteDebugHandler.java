package com.uav.service.control.service.impl;

import com.uav.great.context.utils.SpringBeanUtilsTest;
import com.uav.great.mqtt.enums.device.DockModeCodeEnum;
import com.uav.service.manage.service.IDeviceService;

public class RemoteDebugHandler {

    public boolean valid() {
        return true;
    }

    public boolean canPublish(String sn) {
        IDeviceService deviceService = SpringBeanUtilsTest.getBean(IDeviceService.class);
        DockModeCodeEnum dockMode = deviceService.getDockMode(sn);
        return DockModeCodeEnum.REMOTE_DEBUGGING == dockMode;
    }
}
