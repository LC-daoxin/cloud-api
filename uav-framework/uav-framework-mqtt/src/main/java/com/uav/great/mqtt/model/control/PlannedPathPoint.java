package com.uav.great.mqtt.model.control;

/**
 * 飞行器上报的规划轨迹点。
 * <p>
 * 与请求参数 {@link Point} 不同：轨迹点是设备上报数据，不做取值校验，
 * 且经纬度精度到小数点后 6 位，Float 有效位数不足，故使用 Double。
 */
public class PlannedPathPoint {

    /**
     * 纬度，WGS84
     */
    private Double latitude;

    /**
     * 经度，WGS84
     */
    private Double longitude;

    /**
     * 椭球高，单位：米
     */
    private Float height;

    public PlannedPathPoint() {
    }

    @Override
    public String toString() {
        return "PlannedPathPoint{" +
                "latitude=" + latitude +
                ", longitude=" + longitude +
                ", height=" + height +
                '}';
    }

    public Double getLatitude() {
        return latitude;
    }

    public PlannedPathPoint setLatitude(Double latitude) {
        this.latitude = latitude;
        return this;
    }

    public Double getLongitude() {
        return longitude;
    }

    public PlannedPathPoint setLongitude(Double longitude) {
        this.longitude = longitude;
        return this;
    }

    public Float getHeight() {
        return height;
    }

    public PlannedPathPoint setHeight(Float height) {
        this.height = height;
        return this;
    }
}
