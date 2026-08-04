package com.uav.service.map.service.impl;

import com.uav.great.context.error.CommonErrorEnum;
import com.uav.great.context.enums.device.DeviceDomainEnum;
import com.uav.service.manage.model.dto.DeviceDTO;
import com.uav.service.manage.model.param.DeviceQueryParam;
import com.uav.service.manage.service.IDeviceRedisService;
import com.uav.service.manage.service.IDeviceService;
import com.uav.service.map.model.dto.DeviceDataStatusDTO;
import com.uav.service.map.model.dto.DeviceFlightAreaDTO;
import com.uav.service.map.service.IDeviceDataService;
import com.uav.service.map.service.IDeviceFlightAreaService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.stream.Collectors;


@Service
public class DeviceDataServiceImpl implements IDeviceDataService {

    @Autowired
    private IDeviceService deviceService;

    @Autowired
    private IDeviceRedisService deviceRedisService;

    @Autowired
    private IDeviceFlightAreaService deviceFlightAreaService;

    @Override
    public List<DeviceDataStatusDTO> getDevicesDataStatus(String workspaceId) {
        List<DeviceDTO> devices = deviceService.getDevicesByParams(DeviceQueryParam.builder()
                .domains(List.of(DeviceDomainEnum.DOCK.getDomain())).workspaceId(workspaceId).build());
        if (CollectionUtils.isEmpty(devices)) {
            throw new RuntimeException(CommonErrorEnum.ILLEGAL_ARGUMENT.getMessage());
        }
        return devices.stream().map(device -> DeviceDataStatusDTO.builder()
                        .deviceName(device.getDeviceName())
                        .deviceSn(device.getDeviceSn())
                        .nickname(device.getNickname())
                        .online(deviceRedisService.checkDeviceOnline(device.getDeviceSn()))
                        .flightAreaStatus(getDeviceStatus(workspaceId, device.getDeviceSn()).orElse(null))
                        .build())
                .filter(device -> Objects.nonNull(device.getFlightAreaStatus()))
                .collect(Collectors.toList());
    }

    @Override
    public Optional<DeviceFlightAreaDTO> getDeviceStatus(String workspaceId, String deviceSn) {
        return deviceFlightAreaService.getDeviceFlightAreaByDevice(workspaceId, deviceSn)
                .map(area -> DeviceFlightAreaDTO.builder().syncStatus(area.getSyncStatus()).syncCode(area.getSyncCode()).syncMsg(area.getSyncMsg()).build());
    }
}
