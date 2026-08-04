package com.uav.service.manage.service;

import com.uav.great.context.page.PaginationData;
import com.uav.service.manage.model.dto.DeviceHmsDTO;
import com.uav.service.manage.model.param.DeviceHmsQueryParam;

public interface IDeviceHmsService {

    PaginationData<DeviceHmsDTO> getDeviceHmsByParam(DeviceHmsQueryParam param);
    void updateUnreadHms(String deviceSn);
}
