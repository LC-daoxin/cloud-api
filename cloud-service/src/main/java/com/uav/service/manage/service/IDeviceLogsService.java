package com.uav.service.manage.service;

import com.uav.great.context.response.HttpResultResponse;
import com.uav.great.context.page.PaginationData;
import com.uav.great.mqtt.enums.log.LogModuleEnum;
import com.uav.great.mqtt.model.log.FileUploadUpdateRequest;
import com.uav.service.manage.model.dto.DeviceLogsDTO;
import com.uav.service.manage.model.param.DeviceLogsCreateParam;
import com.uav.service.manage.model.param.DeviceLogsQueryParam;

import java.net.URL;
import java.util.List;

public interface IDeviceLogsService {

    PaginationData<DeviceLogsDTO> getUploadedLogs(String deviceSn, DeviceLogsQueryParam param);

    HttpResultResponse getRealTimeLogs(String deviceSn, List<LogModuleEnum> domainList);

    String insertDeviceLogs(String bid, String username, String deviceSn, DeviceLogsCreateParam param);

    HttpResultResponse pushFileUpload(String username, String deviceSn, DeviceLogsCreateParam param);

    HttpResultResponse pushUpdateFile(String deviceSn, FileUploadUpdateRequest param);

    void deleteLogs(String deviceSn, String logsId);

    void updateLogsStatus(String logsId, Integer value);

    URL getLogsFileUrl(String logsId, String fileId);
}
