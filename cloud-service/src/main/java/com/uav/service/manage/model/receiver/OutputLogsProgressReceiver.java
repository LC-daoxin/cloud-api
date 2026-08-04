package com.uav.service.manage.model.receiver;

import com.uav.great.mqtt.model.log.FileUploadProgressExt;
import lombok.Data;

@Data
public class OutputLogsProgressReceiver {

    private FileUploadProgressExt ext;

    private String status;
}
