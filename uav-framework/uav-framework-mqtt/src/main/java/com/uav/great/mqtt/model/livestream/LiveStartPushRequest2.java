package com.uav.great.mqtt.model.livestream;

import com.uav.great.context.base.BaseModel;
import com.uav.great.mqtt.enums.livestream.UrlTypeEnum;
import com.uav.great.mqtt.enums.livestream.VideoQualityEnum;
import lombok.Data;

@Data
public class LiveStartPushRequest2 extends BaseModel {
    private UrlTypeEnum urlType;
    private String url;
    private String videoId;
    private VideoQualityEnum videoQuality;
}