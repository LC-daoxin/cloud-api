package com.uav.service.manage.service;


import com.uav.great.mqtt.model.tsa.TopologyList;

import java.util.List;
import java.util.Optional;

public interface ITopologyService {

    List<TopologyList> getDeviceTopology(String workspaceId);

    Optional<TopologyList> getDeviceTopologyByGatewaySn(String gatewaySn);
}
