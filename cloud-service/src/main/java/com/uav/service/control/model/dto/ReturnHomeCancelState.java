package com.uav.service.control.model.dto;

import com.uav.great.context.utils.SpringBeanUtilsTest;
import com.uav.great.mqtt.enums.device.DroneModeCodeEnum;
import com.uav.great.mqtt.model.device.OsdDockDrone;
import com.uav.service.control.service.impl.RemoteDebugHandler;
import com.uav.service.manage.model.dto.DeviceDTO;
import com.uav.service.manage.service.IDeviceRedisService;


public class ReturnHomeCancelState extends RemoteDebugHandler {

    @Override
    public boolean canPublish(String sn) {
        IDeviceRedisService deviceRedisService = SpringBeanUtilsTest.getBean(IDeviceRedisService.class);
        return deviceRedisService.getDeviceOnline(sn)
                .map(DeviceDTO::getChildDeviceSn)
                .flatMap(deviceSn -> deviceRedisService.getDeviceOsd(deviceSn, OsdDockDrone.class))
                .map(osd -> DroneModeCodeEnum.RETURN_AUTO == osd.getModeCode())
                .orElse(false);
    }

}
