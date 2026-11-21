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

package top.continew.admin.auth.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import cn.hutool.http.HttpRequest;
import cn.hutool.http.HttpResponse;
import cn.hutool.http.HttpUtil;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import top.continew.admin.auth.config.FaceAuthProperties;
import top.continew.admin.auth.service.AuthService;
import top.continew.admin.auth.support.FaceSessionStore;

/**
 * 人脸认证业务实现测试：校验调用 Python 服务时同时应用连接超时与读取超时。
 *
 * @author Charles7c
 * @since 5.0.0
 */
class FaceAuthServiceImplTest {

    private FaceAuthProperties properties;
    private FaceSessionStore sessionStore;
    private AuthService authService;
    private FaceAuthServiceImpl service;

    @BeforeEach
    void setUp() {
        properties = new FaceAuthProperties();
        sessionStore = mock(FaceSessionStore.class);
        authService = mock(AuthService.class);
        service = new FaceAuthServiceImpl(properties, sessionStore, authService);
    }

    @Test
    void executeShouldApplyConnectAndReadTimeout() {
        try (MockedStatic<HttpUtil> httpUtil = mockStatic(HttpUtil.class)) {
            HttpRequest httpRequest = mock(HttpRequest.class);
            HttpResponse httpResponse = mock(HttpResponse.class);
            when(httpResponse.isOk()).thenReturn(true);
            when(httpResponse.body()).thenReturn("{\"session_id\":\"s1\"}");
            when(httpRequest.execute()).thenReturn(httpResponse);
            httpUtil.when(() -> HttpUtil.createPost(anyString())).thenReturn(httpRequest);

            String sessionId = service.createLoginSession("client");

            assertEquals("s1", sessionId);
            verify(httpRequest).header("X-API-Key", properties.getApiKey());
            verify(httpRequest)
                .setConnectionTimeout((int) properties.getConnectTimeout().toMillis());
            verify(httpRequest).setReadTimeout((int) properties.getReadTimeout().toMillis());
        }
    }
}
