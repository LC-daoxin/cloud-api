package com.uav.service.manage.service;

import com.uav.great.mqtt.model.log.FileUploadProgressFile;
import com.uav.great.mqtt.model.log.FileUploadStartFile;
import com.uav.service.manage.model.dto.LogsFileDTO;
import com.uav.service.manage.model.dto.LogsFileUploadDTO;

import java.net.URL;
import java.util.List;

public interface ILogsFileService {

    List<LogsFileDTO> getLogsFileInfoByLogsId(String logsId);

    List<LogsFileUploadDTO> getLogsFileByLogsId(String logsId);

    Boolean insertFile(FileUploadStartFile file, String logsId);
    void deleteFileByLogsId(String logsId);

    void updateFile(String logsId, FileUploadProgressFile fileReceiver);

    void updateFileUploadStatus(String logsId, Boolean isUploaded);

    URL getLogsFileUrl(String logsId, String fileId);
}
