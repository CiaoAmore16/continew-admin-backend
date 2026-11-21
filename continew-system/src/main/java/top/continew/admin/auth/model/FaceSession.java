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

package top.continew.admin.auth.model;

import lombok.Data;

import java.io.Serial;
import java.io.Serializable;

/**
 * 人脸认证会话（Java 侧 Redis 记录，用于关联 Python 人脸会话与令牌签发）
 *
 * @author Charles7c
 * @since 5.0.0
 */
@Data
public class FaceSession implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    /**
     * Python 人脸会话 ID
     */
    private String sessionId;

    /**
     * 会话类型：login / register
     */
    private String type;

    /**
     * 会话状态：pending / success / failed
     */
    private String status;

    /**
     * 用户名（注册：发起注册的用户；登录：人脸匹配到的账号）
     */
    private String username;

    /**
     * 客户端 ID（登录令牌签发时使用）
     */
    private String clientId;
}
