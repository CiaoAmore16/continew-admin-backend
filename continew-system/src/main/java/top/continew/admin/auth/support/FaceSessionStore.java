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

import cn.hutool.json.JSONUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import top.continew.admin.auth.config.FaceAuthProperties;
import top.continew.admin.auth.constant.FaceAuthConstants;
import top.continew.admin.auth.model.FaceSession;
import top.continew.starter.cache.redisson.util.RedisUtils;

import java.time.Duration;

/**
 * 人脸认证会话存储（Redis）
 *
 * @author Charles7c
 * @since 5.0.0
 */
@Component
@RequiredArgsConstructor
public class FaceSessionStore {

    private final FaceAuthProperties properties;

    /**
     * 保存会话
     *
     * @param session 会话信息
     * @param ttl     过期时间
     */
    public void save(FaceSession session, Duration ttl) {
        RedisUtils.set(this.key(session.getSessionId()), JSONUtil.toJsonStr(session), ttl);
    }

    /**
     * 获取会话
     *
     * @param sessionId 会话 ID
     * @return 会话信息，不存在时为 null
     */
    public FaceSession get(String sessionId) {
        String json = RedisUtils.get(this.key(sessionId));
        return json == null ? null : JSONUtil.toBean(json, FaceSession.class);
    }

    /**
     * 原子消费会话（SETNX），防止重复签发令牌
     *
     * @param sessionId 会话 ID
     * @return true：首次消费成功；false：已消费或正在登录
     */
    public boolean consume(String sessionId) {
        // 消费标记 TTL 必须不短于会话 TTL（加少量余量），确保令牌签发后即使进程崩溃，
        // 消费标记仍持续阻断同一会话的重复认证，避免重复签发令牌
        return RedisUtils.setIfAbsent(this.consumeKey(sessionId), "1", properties.getMaxDuration()
            .plusSeconds(30));
    }

    /**
     * 删除会话及消费标记
     *
     * @param sessionId 会话 ID
     */
    public void delete(String sessionId) {
        RedisUtils.delete(this.key(sessionId));
        RedisUtils.delete(this.consumeKey(sessionId));
    }

    private String key(String sessionId) {
        return FaceAuthConstants.SESSION_KEY_PREFIX + sessionId;
    }

    private String consumeKey(String sessionId) {
        return FaceAuthConstants.CONSUME_KEY_PREFIX + sessionId;
    }
}
