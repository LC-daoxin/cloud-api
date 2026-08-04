package com.uav.great.mqtt.model.device;

import com.uav.great.mqtt.enums.control.CommanderFlightModeEnum;
import com.fasterxml.jackson.annotation.JsonProperty;

public class DockDroneCurrentCommanderFlightMode {

    @JsonProperty("current_commander_flight_mode")
    private CommanderFlightModeEnum currentCommanderFlightMode;

    public DockDroneCurrentCommanderFlightMode() {
    }

    @Override
    public String toString() {
        return "DockDroneCurrentCommanderFlightMode{" +
                "currentCommanderFlightMode=" + currentCommanderFlightMode +
                '}';
    }

    public CommanderFlightModeEnum getCurrentCommanderFlightMode() {
        return currentCommanderFlightMode;
    }

    public DockDroneCurrentCommanderFlightMode setCurrentCommanderFlightMode(CommanderFlightModeEnum currentCommanderFlightMode) {
        this.currentCommanderFlightMode = currentCommanderFlightMode;
        return this;
    }
}
