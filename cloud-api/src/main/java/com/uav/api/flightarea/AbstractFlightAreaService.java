package com.uav.api.flightarea;

import com.uav.great.context.annotations.CloudSDKVersion;
import com.uav.great.context.enums.version.CloudSDKVersionEnum;
import com.uav.great.context.enums.version.GatewayManager;
import com.uav.great.context.enums.version.GatewayTypeEnum;
import com.uav.great.mqtt.core.consume.MqttReply;
import com.uav.great.mqtt.constant.ChannelName;
import com.uav.great.mqtt.enums.flightarea.FlightAreaMethodEnum;
import com.uav.great.mqtt.handle.events.TopicEventsRequest;
import com.uav.great.mqtt.handle.events.TopicEventsResponse;
import com.uav.great.mqtt.model.flightarea.FlightAreasDroneLocation;
import com.uav.great.mqtt.model.flightarea.FlightAreasGetRequest;
import com.uav.great.mqtt.model.flightarea.FlightAreasGetResponse;
import com.uav.great.mqtt.model.flightarea.FlightAreasSyncProgress;
import com.uav.great.mqtt.handle.requests.TopicRequestsRequest;
import com.uav.great.mqtt.handle.requests.TopicRequestsResponse;
import com.uav.great.mqtt.handle.services.ServicesPublish;
import com.uav.great.mqtt.handle.services.ServicesReplyData;
import com.uav.great.mqtt.handle.services.TopicServicesResponse;
import org.springframework.integration.annotation.ServiceActivator;
import org.springframework.messaging.MessageHeaders;

import javax.annotation.Resource;


public abstract class AbstractFlightAreaService {

    @Resource
    private ServicesPublish servicesPublish;

    @CloudSDKVersion(since = CloudSDKVersionEnum.V1_0_0, exclude = GatewayTypeEnum.RC, include = {GatewayTypeEnum.DOCK, GatewayTypeEnum.DOCK2})
    public TopicServicesResponse<ServicesReplyData> flightAreasUpdate(GatewayManager gateway) {
        return servicesPublish.publish(
                gateway.getGatewaySn(),
                FlightAreaMethodEnum.FLIGHT_AREAS_UPDATE.getMethod());
    }

    @ServiceActivator(inputChannel = ChannelName.INBOUND_EVENTS_FLIGHT_AREAS_SYNC_PROGRESS, outputChannel = ChannelName.OUTBOUND_EVENTS)
    @CloudSDKVersion(since = CloudSDKVersionEnum.V1_0_0)
    public TopicEventsResponse<MqttReply> flightAreasSyncProgress(TopicEventsRequest<FlightAreasSyncProgress> request, MessageHeaders headers) {
        throw new UnsupportedOperationException("flightAreasSyncProgress not implemented");
    }

    @ServiceActivator(inputChannel = ChannelName.INBOUND_EVENTS_FLIGHT_AREAS_DRONE_LOCATION, outputChannel = ChannelName.OUTBOUND_EVENTS)
    @CloudSDKVersion(since = CloudSDKVersionEnum.V1_0_0)
    public TopicEventsResponse<MqttReply> flightAreasDroneLocation(TopicEventsRequest<FlightAreasDroneLocation> request, MessageHeaders headers) {
        throw new UnsupportedOperationException("flightAreasDroneLocation not implemented");
    }

    @ServiceActivator(inputChannel = ChannelName.INBOUND_REQUESTS_FLIGHT_AREAS_GET, outputChannel = ChannelName.OUTBOUND_REQUESTS)
    @CloudSDKVersion(since = CloudSDKVersionEnum.V1_0_0)
    public TopicRequestsResponse<MqttReply<FlightAreasGetResponse>> flightAreasGet(TopicRequestsRequest<FlightAreasGetRequest> request, MessageHeaders headers) {
        throw new UnsupportedOperationException("flightAreasGet not implemented");
    }
}
