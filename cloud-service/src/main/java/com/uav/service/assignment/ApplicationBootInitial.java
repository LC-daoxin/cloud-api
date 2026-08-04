package com.uav.service.assignment;

import com.uav.great.context.enums.device.DeviceDomainEnum;
import com.uav.great.mqtt.core.SDKManager;
import com.uav.great.redis.RedisConst;
import com.uav.great.redis.RedisOpsUtils;
import com.uav.service.manage.model.dto.DeviceDTO;
import com.uav.service.manage.service.IDeviceRedisService;
import com.uav.service.manage.service.IDeviceService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.Optional;

@Component
public class ApplicationBootInitial implements CommandLineRunner {

    @Autowired
    private IDeviceService deviceService;

    @Autowired
    private IDeviceRedisService deviceRedisService;

    @Override
    public void run(String... args) throws Exception {
        int start = RedisConst.DEVICE_ONLINE_PREFIX.length();
        RedisOpsUtils.getAllKeys(RedisConst.DEVICE_ONLINE_PREFIX + "*")
                .stream()
                .map(key -> key.substring(start))
                .map(deviceRedisService::getDeviceOnline)
                .map(Optional::get)
                .filter(device -> DeviceDomainEnum.DRONE != device.getDomain())
                .forEach(device -> deviceService.subDeviceOnlineSubscribeTopic(
                        SDKManager.registerDevice(device.getDeviceSn(), device.getChildDeviceSn(), device.getDomain(),
                                device.getType(), device.getSubType(), device.getThingVersion(),
                                deviceRedisService.getDeviceOnline(device.getChildDeviceSn()).map(DeviceDTO::getThingVersion).orElse(null))));

    }
}