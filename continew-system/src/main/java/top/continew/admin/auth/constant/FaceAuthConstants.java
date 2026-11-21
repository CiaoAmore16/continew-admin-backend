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

package top.continew.admin.auth.constant;

import top.continew.starter.core.constant.StringConstants;

/**
 * 人脸认证常量
 *
 * @author Charles7c
 * @since 5.0.0
 */
public final class FaceAuthConstants {

    /**
     * 分隔符
     */
    public static final String DELIMITER = StringConstants.COLON;

    /**
     * 人脸会话 Redis 键前缀
     */
    public static final String SESSION_KEY_PREFIX = "face:auth:session" + DELIMITER;

    /**
     * 人脸会话消费标记 Redis 键前缀（防止重复签发令牌）
     */
    public static final String CONSUME_KEY_PREFIX = "face:auth:consume" + DELIMITER;

    /**
     * 会话类型：登录
     */
    public static final String TYPE_LOGIN = "login";

    /**
     * 会话类型：注册
     */
    public static final String TYPE_REGISTER = "register";

    /**
     * 会话状态：进行中
     */
    public static final String STATUS_PENDING = "pending";

    /**
     * 会话状态：成功
     */
    public static final String STATUS_SUCCESS = "success";

    /**
     * 会话状态：失败
     */
    public static final String STATUS_FAILED = "failed";

    private FaceAuthConstants() {
    }
}
