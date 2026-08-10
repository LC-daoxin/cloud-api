package com.uav.great.mqtt.handle.services;


import com.uav.great.mqtt.core.CommonTopicRequest;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

public class TopicServicesRequest<T> extends CommonTopicRequest<T> {

    private String method;

    // RC 网关把无人机作为子设备管理，需通过 device_list 显式寻址无人机 SN；
    // 非 RC 场景为 null 时不序列化，避免多发空字段。
    @JsonInclude(JsonInclude.Include.NON_NULL)
    @JsonProperty("device_list")
    private List<Map<String, String>> deviceList;

    public TopicServicesRequest() {
    }

    @Override
    public String toString() {
        return "TopicServicesRequest{" +
                "method='" + method + '\'' +
                ", tid='" + tid + '\'' +
                ", bid='" + bid + '\'' +
                ", timestamp=" + timestamp +
                ", deviceList=" + deviceList +
                ", data=" + data +
                '}';
    }

    public String getMethod() {
        return method;
    }

    public TopicServicesRequest<T> setMethod(String method) {
        this.method = method;
        return this;
    }

    public List<Map<String, String>> getDeviceList() {
        return deviceList;
    }

    public TopicServicesRequest<T> setDeviceList(List<Map<String, String>> deviceList) {
        this.deviceList = deviceList;
        return this;
    }

    public String getTid() {
        return tid;
    }

    public TopicServicesRequest<T> setTid(String tid) {
        this.tid = tid;
        return this;
    }

    public String getBid() {
        return bid;
    }

    public TopicServicesRequest<T> setBid(String bid) {
        this.bid = bid;
        return this;
    }

    public Long getTimestamp() {
        return timestamp;
    }

    public TopicServicesRequest<T> setTimestamp(Long timestamp) {
        this.timestamp = timestamp;
        return this;
    }

    public T getData() {
        return data;
    }

    public TopicServicesRequest<T> setData(T data) {
        this.data = data;
        return this;
    }

}
