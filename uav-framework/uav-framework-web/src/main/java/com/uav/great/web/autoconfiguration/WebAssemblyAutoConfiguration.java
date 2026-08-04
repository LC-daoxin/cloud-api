package com.uav.great.web.autoconfiguration;

import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.ComponentScan;

import javax.annotation.PostConstruct;

@Slf4j
@ComponentScan("com.uav.great.web")
public class WebAssemblyAutoConfiguration {
    @PostConstruct
    public void init() {
        log.info("【web】 assembly load");
    }

}
