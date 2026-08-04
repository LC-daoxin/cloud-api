package com.uav.service.manage.service;

import com.uav.great.context.response.HttpResultResponse;
import com.uav.great.mqtt.model.device.VideoId;
import com.uav.service.manage.model.dto.CapacityDeviceDTO;
import com.uav.service.manage.model.dto.LiveTypeDTO;

import java.util.List;

public interface ILiveStreamService {

    List<CapacityDeviceDTO> getLiveCapacity(String workspaceId);

    HttpResultResponse liveStart(LiveTypeDTO liveParam);

    HttpResultResponse liveStop(VideoId videoId);

    HttpResultResponse liveSetQuality(LiveTypeDTO liveParam);

    HttpResultResponse liveLensChange(LiveTypeDTO liveParam);
}
