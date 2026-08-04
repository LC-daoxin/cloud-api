package com.uav.service.map.model.param;

import com.uav.service.map.model.dto.FlightAreaContent;
import lombok.Data;

@Data
public class PutFlightAreaParam {

    private String name;

    private FlightAreaContent content;

    private Boolean status;

}
