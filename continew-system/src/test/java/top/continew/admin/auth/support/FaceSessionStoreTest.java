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

package top.continew.admin.auth.support;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mockStatic;

import cn.hutool.extra.spring.SpringUtil;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import top.continew.admin.auth.config.FaceAuthProperties;
import top.continew.admin.auth.constant.FaceAuthConstants;
import top.continew.starter.cache.redisson.util.RedisUtils;

import java.time.Duration;

/**
 * 人脸会话存储测试：校验消费标记 TTL 不短于会话 TTL（含余量），防止令牌签发后进程崩溃导致重复签发。
 *
 * @author Charles7c
 * @since 5.0.0
 */
class FaceSessionStoreTest {

    @Test
    void consumeShouldSetTtlNotShorterThanMaxDuration() {
        FaceAuthProperties properties = new FaceAuthProperties();
        FaceSessionStore store = new FaceSessionStore(properties);
        try (MockedStatic<SpringUtil> springUtil = mockStatic(SpringUtil.class);
            MockedStatic<RedisUtils> redisUtils = mockStatic(RedisUtils.class)) {
            redisUtils
                .when(() -> RedisUtils.setIfAbsent(anyString(), any(), any(Duration.class)))
                .thenReturn(true);

            boolean consumed = store.consume("sid-1");

            assertTrue(consumed);
            redisUtils.verify(() -> RedisUtils.setIfAbsent(
                FaceAuthConstants.CONSUME_KEY_PREFIX + "sid-1", "1",
                properties.getMaxDuration().plusSeconds(30)));
        }
    }
}
