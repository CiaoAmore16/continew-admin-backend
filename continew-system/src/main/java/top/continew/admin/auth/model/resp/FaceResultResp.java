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
 * 人脸会话状态响应参数
 *
 * @author Charles7c
 * @since 5.0.0
 */
@Data
@Schema(description = "人脸会话状态响应参数")
public class FaceResultResp implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    /**
     * 会话模式
     */
    @Schema(description = "会话模式", example = "login")
    private String mode;

    /**
     * 会话阶段
     */
    @Schema(description = "会话阶段", example = "matching")
    private String phase;

    /**
     * 是否完成
     */
    @Schema(description = "是否完成", example = "true")
    private Boolean done;

    /**
     * 结果描述
     */
    @Schema(description = "结果描述", example = "登录成功：zhangsan")
    private String result;

    /**
     * 当前动作提示
     */
    @Schema(description = "当前动作提示", example = "请正对摄像头（基线 3/10）")
    private String action;

    /**
     * 登录成功时匹配到的账号，其余情况为空
     */
    @Schema(description = "匹配账号", example = "zhangsan")
    private String account;
}
