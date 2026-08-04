package com.uav.great.mqtt.model.property;

import com.uav.great.context.base.BaseModel;
import com.uav.great.mqtt.enums.control.CommanderModeLostActionEnum;
import com.fasterxml.jackson.annotation.JsonProperty;

import javax.validation.constraints.NotNull;

public class DockDroneCommanderModeLostAction extends BaseModel {

    @JsonProperty("commander_mode_lost_action")
    @NotNull
    private CommanderModeLostActionEnum commanderModeLostAction;

    public DockDroneCommanderModeLostAction() {
    }

    @Override
    public String toString() {
        return "DockDroneCommanderModeLostAction{" +
                "commanderModeLostAction=" + commanderModeLostAction +
                '}';
    }

    public CommanderModeLostActionEnum getCommanderModeLostAction() {
        return commanderModeLostAction;
    }

    public DockDroneCommanderModeLostAction setCommanderModeLostAction(CommanderModeLostActionEnum commanderModeLostAction) {
        this.commanderModeLostAction = commanderModeLostAction;
        return this;
    }
}
