package com.uav.service.manage.controller;

import com.uav.api.tsa.IHttpTsaService;
import com.uav.great.context.response.HttpResultResponse;
import com.uav.great.mqtt.model.tsa.TopologyList;
import com.uav.great.mqtt.model.tsa.TopologyResponse;
import com.uav.service.manage.service.ITopologyService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.RestController;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.util.List;

@RestController
public class TopologyController implements IHttpTsaService {

    @Autowired
    private ITopologyService topologyService;


    @Override
    public HttpResultResponse<TopologyResponse> obtainDeviceTopologyList(String workspaceId, HttpServletRequest req, HttpServletResponse rsp) {
        List<TopologyList> topologyList = topologyService.getDeviceTopology(workspaceId);
        return HttpResultResponse.success(new TopologyResponse().setList(topologyList));
    }
}
