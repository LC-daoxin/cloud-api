package com.uav.service.storage.service.impl;

import com.uav.api.media.AbstractMediaService;
import com.uav.great.mqtt.core.consume.MqttReply;
import com.uav.great.mqtt.model.media.StorageConfigGet;
import com.uav.great.mqtt.model.storage.StsCredentialsResponse;
import com.uav.great.mqtt.handle.requests.TopicRequestsRequest;
import com.uav.great.mqtt.handle.requests.TopicRequestsResponse;
import com.uav.great.oss.model.OssConfiguration;
import com.uav.great.oss.service.impl.OssServiceContext;
import com.uav.service.storage.service.IStorageService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.MessageHeaders;
import org.springframework.stereotype.Service;


@Service
public class StorageServiceImpl extends AbstractMediaService implements IStorageService {

    @Autowired
    private OssServiceContext ossService;

    @Override
    public StsCredentialsResponse getSTSCredentials() {
        return new StsCredentialsResponse()
                // endpoint 随凭据下发给外部设备，用于直传/下载，必须使用对外端点
                .setEndpoint(OssConfiguration.publicEndpoint())
                .setBucket(OssConfiguration.bucket)
                .setCredentials(ossService.getCredentials())
                .setProvider(OssConfiguration.provider)
                .setObjectKeyPrefix(OssConfiguration.objectDirPrefix)
                .setRegion(OssConfiguration.region);
    }

    @Override
    public TopicRequestsResponse<MqttReply<StsCredentialsResponse>> storageConfigGet(TopicRequestsRequest<StorageConfigGet> response, MessageHeaders headers) {
        return new TopicRequestsResponse<MqttReply<StsCredentialsResponse>>().setData(MqttReply.success(getSTSCredentials()));
    }
}
