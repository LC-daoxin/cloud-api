package com.uav.great.oss.service.impl;

import com.uav.great.context.enums.oss.OssTypeEnum;
import com.uav.great.context.model.CredentialsToken;
import com.uav.great.oss.model.OssConfiguration;
import com.uav.great.oss.service.IOssService;
import io.minio.*;
import io.minio.credentials.AssumeRoleProvider;
import io.minio.credentials.Credentials;
import io.minio.errors.*;
import io.minio.http.Method;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.URL;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.util.Objects;

@Service
@Slf4j
public class MinIOServiceImpl implements IOssService {

    private MinioClient client;

    /**
     * 对外预览客户端：预签名 URL 会下发给外部设备/Pilot App，
     * 其 host 必须使用 external-endpoint（配置未设置时与内部 endpoint 相同）。
     */
    private MinioClient externalClient;

    @Override
    public OssTypeEnum getOssType() {
        return OssTypeEnum.MINIO;
    }

    @Override
    public CredentialsToken getCredentials() {
        try {
            AssumeRoleProvider provider = new AssumeRoleProvider(OssConfiguration.endpoint, OssConfiguration.accessKey,
                    OssConfiguration.secretKey, Math.toIntExact(OssConfiguration.expire),
                    null, OssConfiguration.region, null, null, null, null);
            Credentials credential = provider.fetch();
            return new CredentialsToken(credential.accessKey(), credential.secretKey(), credential.sessionToken(), OssConfiguration.expire);
        } catch (NoSuchAlgorithmException e) {
            log.debug("Failed to obtain sts.");
            e.printStackTrace();
        }
        return null;
    }

    @Override
    public URL getObjectUrl(String bucket, String objectKey) {
        try {
            // 预签名 URL 下发给外部设备访问，host 使用对外端点（externalClient）
            return new URL(
                    externalClient.getPresignedObjectUrl(
                                    GetPresignedObjectUrlArgs.builder()
                                            .method(Method.GET)
                                            .bucket(bucket)
                                            .object(objectKey)
                                            .expiry(Math.toIntExact(OssConfiguration.expire))
                                            .build()));
        } catch (ErrorResponseException | InsufficientDataException | InternalException |
                InvalidKeyException | InvalidResponseException | IOException |
                NoSuchAlgorithmException | XmlParserException | ServerException e) {
            throw new RuntimeException("The file does not exist on the OssConfiguration.");
        }
    }

    @Override
    public Boolean deleteObject(String bucket, String objectKey) {
        try {
            client.removeObject(RemoveObjectArgs.builder().bucket(bucket).object(objectKey).build());
        } catch (MinioException | NoSuchAlgorithmException | IOException | InvalidKeyException e) {
            log.error("Failed to delete file.");
            e.printStackTrace();
            return false;
        }
        return true;
    }

    @Override
    public InputStream getObject(String bucket, String objectKey) {
        try {
            GetObjectResponse object = client.getObject(GetObjectArgs.builder().bucket(bucket).object(objectKey).build());
            return new ByteArrayInputStream(object.readAllBytes());
        } catch (ErrorResponseException | InsufficientDataException | InternalException | InvalidKeyException | InvalidResponseException | IOException | NoSuchAlgorithmException | ServerException | XmlParserException e) {
            e.printStackTrace();
        }
        return InputStream.nullInputStream();
    }

    @Override
    public void putObject(String bucket, String objectKey, InputStream input) {
        try {
            client.statObject(StatObjectArgs.builder().bucket(bucket).object(objectKey).build());
            throw new RuntimeException("The filename already exists.");
        } catch (MinioException | InvalidKeyException | IOException | NoSuchAlgorithmException e) {
            log.info("The file does not exist, start uploading.");
            try {
                ObjectWriteResponse response = client.putObject(
                        PutObjectArgs.builder().bucket(bucket).object(objectKey).stream(input, input.available(), 0).build());
                log.info("Upload FlighttaskCreateFile: {}", response.etag());
            } catch (MinioException | IOException | InvalidKeyException | NoSuchAlgorithmException ex) {
                log.error("Failed to upload FlighttaskCreateFile {}.", objectKey);
                ex.printStackTrace();
            }
        }
    }

    public void createClient() {
        if (Objects.nonNull(this.client)) {
            return;
        }
        // 内部读写客户端：走容器网络可访问的 endpoint（默认 compose 服务名）
        this.client = MinioClient.builder()
                .endpoint(OssConfiguration.endpoint)
                .credentials(OssConfiguration.accessKey, OssConfiguration.secretKey)
                //.region(OssConfiguration.region)
                .build();
        // 预签名 URL 客户端：对外端点，未配置 external-endpoint 时与内部端点相同（复用同一实例即可）
        String externalEndpoint = OssConfiguration.publicEndpoint();
        if (externalEndpoint.equals(OssConfiguration.endpoint)) {
            this.externalClient = this.client;
        } else {
            this.externalClient = MinioClient.builder()
                    .endpoint(externalEndpoint)
                    .credentials(OssConfiguration.accessKey, OssConfiguration.secretKey)
                    .build();
        }
    }
}
