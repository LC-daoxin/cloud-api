package com.uav.service.control.model.dto;

import com.uav.great.mqtt.enums.control.FlyToStatusEnum;
import com.uav.great.mqtt.model.control.PlannedPathPoint;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 飞至指定点进度通知。
 * <p>
 * 在 {@link ResultNotifyDTO} 的 sn/result/message 基础上，透传设备上报的完整进度数据，
 * 供前端展示剩余距离、剩余时间与规划轨迹。
 */
@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class FlyToPointProgressNotifyDTO {

    private Integer result;

    private String message;

    private String sn;

    /**
     * 飞行任务唯一标识
     */
    private String flyToId;

    /**
     * 任务执行状态
     */
    private FlyToStatusEnum status;

    /**
     * 当前执行到的航点序号
     */
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
}
