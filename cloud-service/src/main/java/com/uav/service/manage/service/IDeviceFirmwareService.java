package com.uav.service.manage.service;

import com.uav.great.context.page.PaginationData;
import com.uav.great.mqtt.model.firmware.OtaCreateDevice;
import com.uav.service.manage.model.dto.DeviceFirmwareDTO;
import com.uav.service.manage.model.dto.DeviceFirmwareNoteDTO;
import com.uav.service.manage.model.dto.DeviceFirmwareUpgradeDTO;
import com.uav.service.manage.model.param.DeviceFirmwareQueryParam;
import com.uav.service.manage.model.param.DeviceFirmwareUploadParam;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Optional;

public interface IDeviceFirmwareService {

    Optional<DeviceFirmwareDTO> getFirmware(String workspaceId, String deviceName, String version);

    Optional<DeviceFirmwareNoteDTO> getLatestFirmwareReleaseNote(String deviceName);

    List<OtaCreateDevice> getDeviceOtaFirmware(String workspaceId, List<DeviceFirmwareUpgradeDTO> upgradeDTOS);

    PaginationData<DeviceFirmwareDTO> getAllFirmwarePagination(String workspaceId, DeviceFirmwareQueryParam param);

    Boolean checkFileExist(String workspaceId, String fileMd5);

    void importFirmwareFile(String workspaceId, String creator, DeviceFirmwareUploadParam param, MultipartFile file);

    void saveFirmwareInfo(DeviceFirmwareDTO firmware, List<String> deviceNames);

    void updateFirmwareInfo(DeviceFirmwareDTO firmware);
}
