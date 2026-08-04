package com.uav.great.mqtt.model.property;

import com.uav.great.context.base.BaseModel;
import com.uav.great.mqtt.model.device.ObstacleAvoidance;

import javax.validation.Valid;
import javax.validation.constraints.NotNull;

public class ObstacleAvoidanceSet extends BaseModel {

    @Valid
    @NotNull
    private ObstacleAvoidance obstacleAvoidance;

    public ObstacleAvoidanceSet() {
    }

    @Override
    public String toString() {
        return "ObstacleAvoidanceSet{" +
                "obstacleAvoidance=" + obstacleAvoidance +
                '}';
    }

    public ObstacleAvoidance getObstacleAvoidance() {
        return obstacleAvoidance;
    }

    public ObstacleAvoidanceSet setObstacleAvoidance(ObstacleAvoidance obstacleAvoidance) {
        this.obstacleAvoidance = obstacleAvoidance;
        return this;
    }
}
