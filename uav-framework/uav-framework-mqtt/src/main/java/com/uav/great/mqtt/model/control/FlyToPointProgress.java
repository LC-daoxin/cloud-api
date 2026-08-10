package com.uav.great.mqtt.model.control;

import com.uav.great.mqtt.enums.wayline.WaylineErrorCodeEnum;
import com.uav.great.mqtt.enums.control.FlyToStatusEnum;

import java.util.List;

public class FlyToPointProgress {

    private WaylineErrorCodeEnum result;

    private FlyToStatusEnum status;

    private String flyToId;

    private Integer wayPointIndex;

    /**
     * 剩余任务距离，单位：米
     */
    private Float remainingDistance;

    /**
     * 剩余任务时间，单位：秒
     */
    private Float remainingTime;

    /**
     * 规划的轨迹点列表
     */
    private List<PlannedPathPoint> plannedPathPoints;

    public FlyToPointProgress() {
    }

    @Override
    public String toString() {
        return "FlyToPointProgress{" +
                "result=" + result +
                ", status=" + status +
                ", flyToId='" + flyToId + '\'' +
                ", wayPointIndex=" + wayPointIndex +
                ", remainingDistance=" + remainingDistance +
                ", remainingTime=" + remainingTime +
                ", plannedPathPoints=" + plannedPathPoints +
                '}';
    }

    public WaylineErrorCodeEnum getResult() {
        return result;
    }

    public FlyToPointProgress setResult(WaylineErrorCodeEnum result) {
        this.result = result;
        return this;
    }

    public FlyToStatusEnum getStatus() {
        return status;
    }

    public FlyToPointProgress setStatus(FlyToStatusEnum status) {
        this.status = status;
        return this;
    }

    public String getFlyToId() {
        return flyToId;
    }

    public FlyToPointProgress setFlyToId(String flyToId) {
        this.flyToId = flyToId;
        return this;
    }

    public Integer getWayPointIndex() {
        return wayPointIndex;
    }

    public FlyToPointProgress setWayPointIndex(Integer wayPointIndex) {
        this.wayPointIndex = wayPointIndex;
        return this;
    }

    public Float getRemainingDistance() {
        return remainingDistance;
    }

    public FlyToPointProgress setRemainingDistance(Float remainingDistance) {
        this.remainingDistance = remainingDistance;
        return this;
    }

    public Float getRemainingTime() {
        return remainingTime;
    }

    public FlyToPointProgress setRemainingTime(Float remainingTime) {
        this.remainingTime = remainingTime;
        return this;
    }

    public List<PlannedPathPoint> getPlannedPathPoints() {
        return plannedPathPoints;
    }

    public FlyToPointProgress setPlannedPathPoints(List<PlannedPathPoint> plannedPathPoints) {
        this.plannedPathPoints = plannedPathPoints;
        return this;
    }
}
