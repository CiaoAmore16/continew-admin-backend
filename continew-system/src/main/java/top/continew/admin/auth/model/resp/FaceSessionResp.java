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

package top.continew.admin.auth.model.resp;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serial;
import java.io.Serializable;

/**
 * 人脸会话创建响应参数
 *
 * @author Charles7c
 * @since 5.0.0
 */
@Data
@Schema(description = "人脸会话创建响应参数")
public class FaceSessionResp implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    /**
     * 人脸会话 ID
     */
    @Schema(description = "人脸会话 ID", example = "f47ac10b-58cc-4372-a567-0e02b2c3d479")
    private String sessionId;
}
