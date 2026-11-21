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

package top.continew.admin.auth.service;

import top.continew.admin.auth.model.resp.FaceResultResp;
import top.continew.admin.auth.model.resp.FaceStatusResp;
import top.continew.admin.auth.model.resp.LoginResp;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * 人脸认证业务接口
 *
 * @author Charles7c
 * @since 5.0.0
 */
public interface FaceAuthService {

    /**
     * 创建人脸登录会话
     *
     * @param clientId 客户端 ID
     * @return 会话 ID
     */
    String createLoginSession(String clientId);

    /**
     * 创建人脸注册会话
     *
     * @param username 用户名
     * @return 会话 ID
     */
    String createRegisterSession(String username);

    /**
     * 处理一帧图像
     *
     * @param sessionId 会话 ID
     * @param frame     图像字节
     * @return 会话状态
     */
    FaceResultResp processFrame(String sessionId, byte[] frame);

    /**
     * 查询会话状态
     *
     * @param sessionId 会话 ID
     * @return 会话状态
     */
    FaceResultResp getResult(String sessionId);

    /**
     * 完成人脸登录（签发令牌）
     *
     * @param sessionId 会话 ID
     * @param request   请求对象
     * @param response  响应对象
     * @return 登录响应
     */
    LoginResp complete(String sessionId, HttpServletRequest request, HttpServletResponse response);

    /**
     * 查询当前用户人脸绑定状态
     *
     * @param username 用户名
     * @return 人脸绑定状态
     */
    FaceStatusResp getStatus(String username);
}
