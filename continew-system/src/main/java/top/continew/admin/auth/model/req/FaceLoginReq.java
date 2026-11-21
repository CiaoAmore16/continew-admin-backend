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

package top.continew.admin.auth.model.req;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import jakarta.validation.constraints.NotBlank;
import java.io.Serial;

/**
 * 人脸登录请求参数
 *
 * @author Charles7c
 * @since 5.0.0
 */
@Data
@Schema(description = "人脸登录请求参数")
public class FaceLoginReq extends LoginReq {

    @Serial
    private static final long serialVersionUID = 1L;

    /**
     * 用户名
     */
    @Schema(description = "用户名", example = "zhangsan")
    @NotBlank(message = "用户名不能为空")
    private String username;

    /**
     * 人脸会话 ID
     */
    @Schema(description = "人脸会话 ID", example = "f47ac10b-58cc-4372-a567-0e02b2c3d479")
    @NotBlank(message = "人脸会话 ID 不能为空")
    private String faceSessionId;
}
