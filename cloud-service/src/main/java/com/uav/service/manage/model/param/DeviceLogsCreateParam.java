package com.uav.service.manage.model.param;

import com.uav.great.mqtt.model.log.FileUploadStartFile;
import lombok.Data;

import java.util.List;

@Data
public class DeviceLogsCreateParam {

    private String logsInformation;

    private Long happenTime;

    private List<FileUploadStartFile> files;
}
