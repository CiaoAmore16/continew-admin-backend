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

import cn.dev33.satoken.annotation.SaIgnore;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import top.continew.admin.auth.config.FaceAuthProperties;
import top.continew.admin.auth.model.req.FaceLoginSessionReq;
import top.continew.admin.auth.model.resp.FaceResultResp;
import top.continew.admin.auth.model.resp.FaceSessionResp;
import top.continew.admin.auth.model.resp.FaceStatusResp;
import top.continew.admin.auth.model.resp.LoginResp;
import top.continew.admin.auth.service.FaceAuthService;
import top.continew.admin.common.context.UserContextHolder;
import top.continew.starter.core.util.validation.ValidationUtils;
import top.continew.starter.log.annotation.Log;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import java.io.IOException;

/**
 * 人脸认证 API
 *
 * @author Charles7c
 * @since 5.0.0
 */
@Tag(name = "人脸认证 API")
@Log(module = "人脸登录")
@Validated
@RestController
@RequiredArgsConstructor
@RequestMapping("/auth/face")
public class FaceAuthController {

    private final FaceAuthService faceAuthService;
    private final FaceAuthProperties properties;

    /**
     * 创建人脸登录会话
     *
     * @param req 请求参数
     * @return 会话创建响应
     */
    @SaIgnore
    @Operation(summary = "创建人脸登录会话", description = "创建人脸登录会话")
    @PostMapping("/login/session")
    public FaceSessionResp createLoginSession(@RequestBody @Valid FaceLoginSessionReq req) {
        FaceSessionResp resp = new FaceSessionResp();
        resp.setSessionId(faceAuthService.createLoginSession(req.getClientId()));
        return resp;
    }

    /**
     * 创建人脸注册会话
     *
     * @return 会话创建响应
     */
    @Operation(summary = "创建人脸注册会话", description = "创建人脸注册会话")
    @PostMapping("/register/session")
    public FaceSessionResp createRegisterSession() {
        String username = UserContextHolder.getUsername();
        ValidationUtils.throwIfBlank(username, "未登录，无法注册人脸");
        FaceSessionResp resp = new FaceSessionResp();
        resp.setSessionId(faceAuthService.createRegisterSession(username));
        return resp;
    }

    /**
     * 上传人脸帧
     *
     * @param sessionId 会话 ID
     * @param request   请求对象
     * @return 会话状态
     * @throws IOException 读取请求体失败
     */
    @SaIgnore
    @Log(ignore = true)
    @Operation(summary = "上传人脸帧", description = "上传一帧图像用于活体检测 / 特征采集 / 匹配")
    @PostMapping("/session/{sessionId}/frame")
    public FaceResultResp processFrame(@PathVariable String sessionId, HttpServletRequest request)
        throws IOException {
        // 在请求体进入业务处理 / 转发 Python 前限制单帧大小，避免超大请求体被完整读入内存
        long maxBytes = properties.getMaxFrameBytes();
        ValidationUtils.throwIf(request.getContentLengthLong() > maxBytes, "人脸帧数据过大");
        byte[] frame = request.getInputStream().readNBytes((int) maxBytes + 1);
        ValidationUtils.throwIf(frame.length > maxBytes, "人脸帧数据过大");
        return faceAuthService.processFrame(sessionId, frame);
    }

    /**
     * 查询人脸会话状态
     *
     * @param sessionId 会话 ID
     * @return 会话状态
     */
    @SaIgnore
    @Operation(summary = "查询人脸会话状态", description = "查询人脸会话状态")
    @GetMapping("/session/{sessionId}")
    public FaceResultResp getResult(@PathVariable String sessionId) {
        return faceAuthService.getResult(sessionId);
    }

    /**
     * 完成人脸登录
     *
     * @param sessionId 会话 ID
     * @param request   请求对象
     * @param response  响应对象
     * @return 登录响应
     */
    @SaIgnore
    @Operation(summary = "完成人脸登录", description = "完成人脸登录并签发令牌")
    @PostMapping("/session/{sessionId}/complete")
    public LoginResp complete(@PathVariable String sessionId, HttpServletRequest request,
        HttpServletResponse response) {
        return faceAuthService.complete(sessionId, request, response);
    }

    /**
     * 查询人脸绑定状态
     *
     * @return 人脸绑定状态
     */
    @Operation(summary = "查询人脸绑定状态", description = "查询当前登录用户是否已注册人脸")
    @GetMapping("/status")
    public FaceStatusResp getStatus() {
        String username = UserContextHolder.getUsername();
        ValidationUtils.throwIfBlank(username, "未登录，无法查询人脸状态");
        return faceAuthService.getStatus(username);
    }
}
