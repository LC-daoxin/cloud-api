package com.uav.great.mqtt.handle.services;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

class TopicServicesRequestTest {

    private final ObjectMapper mapper = new ObjectMapper();

    @Test
    void serializesRcDeviceListAtTopLevel() throws Exception {
        TopicServicesRequest<Object> request = new TopicServicesRequest<>();
        request.setMethod("flight_authority_grab");
        request.setDeviceList(List.of(Map.of("sn", "DRONE-SN")));

        JsonNode json = mapper.readTree(mapper.writeValueAsString(request));

        assertEquals("DRONE-SN", json.path("device_list").path(0).path("sn").asText());
    }

    @Test
    void omitsDeviceListForNonRcRequest() throws Exception {
        TopicServicesRequest<Object> request = new TopicServicesRequest<>();
        request.setMethod("flight_authority_grab");

        JsonNode json = mapper.readTree(mapper.writeValueAsString(request));

        assertFalse(json.has("device_list"));
    }
}
