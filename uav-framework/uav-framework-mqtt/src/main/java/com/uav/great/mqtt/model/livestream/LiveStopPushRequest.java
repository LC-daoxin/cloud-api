package com.uav.great.mqtt.model.livestream;

import com.uav.great.context.base.BaseModel;
import com.uav.great.mqtt.model.device.VideoId;

import javax.validation.constraints.NotNull;

public class LiveStopPushRequest extends BaseModel {

    /**
     * The format is #{uav_sn}/#{camera_id}/#{video_index},
     * drone serial number/payload and mounted location enumeration value/payload lens numbering
     */
    @NotNull
    private VideoId videoId;

    public LiveStopPushRequest() {
    }

    @Override
    public String toString() {
        return "LiveStopPushRequest{" +
                "videoId=" + videoId +
                '}';
    }

    public VideoId getVideoId() {
        return videoId;
    }

    public LiveStopPushRequest setVideoId(VideoId videoId) {
        this.videoId = videoId;
        return this;
    }
}
