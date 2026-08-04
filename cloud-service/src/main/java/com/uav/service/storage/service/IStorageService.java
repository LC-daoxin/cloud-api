package com.uav.service.storage.service;


import com.uav.great.mqtt.model.storage.StsCredentialsResponse;

public interface IStorageService {

    StsCredentialsResponse getSTSCredentials();

}
