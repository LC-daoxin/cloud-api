package com.uav.service.map.model.dto;

import com.uav.great.mqtt.model.map.ElementGeometryType;
import com.uav.great.mqtt.model.map.ElementProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import javax.validation.Valid;
import javax.validation.constraints.NotNull;
@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class FlightAreaContent {

    @NotNull
    @Valid
    private ElementProperty properties;

    @NotNull
    @Valid
    private ElementGeometryType geometry;

}
