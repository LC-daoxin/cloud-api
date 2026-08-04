package com.uav.service.manage.model.param;

import com.uav.great.mqtt.enums.log.LogModuleEnum;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;
@Data
public class DeviceLogsGetParam {

    @JsonProperty("domain_list")
    List<LogModuleEnum> domainList;
}
