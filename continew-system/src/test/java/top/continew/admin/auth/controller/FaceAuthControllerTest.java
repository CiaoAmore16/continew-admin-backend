/*
 * Copyright (c) 2022-present Charles7c Authors. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package top.continew.admin.auth.controller;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import cn.hutool.extra.spring.SpringUtil;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.MockedStatic;
import org.springframework.mock.web.MockHttpServletRequest;
import top.continew.admin.auth.config.FaceAuthProperties;
import top.continew.admin.auth.model.resp.FaceResultResp;
import top.continew.admin.auth.service.FaceAuthService;
import top.continew.starter.core.exception.BadRequestException;

/**
 * 人脸认证控制器测试：校验上传人脸帧在进入业务处理前的大小限制。
 *
 * @author Charles7c
 * @since 5.0.0
 */
class FaceAuthControllerTest {

    private FaceAuthService faceAuthService;
    private FaceAuthProperties properties;
    private FaceAuthController controller;

    @BeforeEach
    void setUp() {
        faceAuthService = mock(FaceAuthService.class);
        properties = new FaceAuthProperties();
        controller = new FaceAuthController(faceAuthService, properties);
    }

    @Test
    void processFrameShouldForwardSmallFrame() throws Exception {
        byte[] frame = new byte[] {1, 2, 3};
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setContent(frame);
        FaceResultResp resp = new FaceResultResp();
        when(faceAuthService.processFrame(anyString(), any(byte[].class))).thenReturn(resp);
        try (MockedStatic<SpringUtil> springUtil = mockStatic(SpringUtil.class)) {
            FaceResultResp result = controller.processFrame("sid", request);

            assertSame(resp, result);
            ArgumentCaptor<byte[]> captor = ArgumentCaptor.forClass(byte[].class);
            verify(faceAuthService).processFrame(eq("sid"), captor.capture());
            assertArrayEquals(frame, captor.getValue());
        }
    }

    @Test
    void processFrameShouldRejectOversizedContentLength() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setContent(new byte[(int) properties.getMaxFrameBytes() + 10]);

        try (MockedStatic<SpringUtil> springUtil = mockStatic(SpringUtil.class)) {
            assertThrows(BadRequestException.class, () -> controller.processFrame("sid", request));
        }

        verify(faceAuthService, never()).processFrame(anyString(), any(byte[].class));
    }
}
