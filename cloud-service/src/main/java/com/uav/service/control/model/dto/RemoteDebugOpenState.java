package com.uav.service.control.model.dto;

import com.uav.great.context.utils.SpringBeanUtilsTest;
import com.uav.great.mqtt.enums.device.DockModeCodeEnum;
import com.uav.service.control.service.impl.RemoteDebugHandler;
import com.uav.service.manage.service.IDeviceService;
import lombok.Data;
import lombok.EqualsAndHashCode;
@EqualsAndHashCode(callSuper = true)
@Data
public class RemoteDebugOpenState extends RemoteDebugHandler {

    @Override
    public boolean canPublish(String sn) {
        IDeviceService deviceService = SpringBeanUtilsTest.getBean(IDeviceService.class);
        DockModeCodeEnum dockMode = deviceService.getDockMode(sn);
        return DockModeCodeEnum.IDLE == dockMode;
    }
}
