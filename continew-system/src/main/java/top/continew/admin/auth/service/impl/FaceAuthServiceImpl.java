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

import cn.hutool.core.util.ObjectUtil;
import cn.hutool.core.util.StrUtil;
import cn.hutool.core.util.URLUtil;
import cn.hutool.http.HttpRequest;
import cn.hutool.http.HttpResponse;
import cn.hutool.http.HttpUtil;
import cn.hutool.json.JSONUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import top.continew.admin.auth.config.FaceAuthProperties;
import top.continew.admin.auth.constant.FaceAuthConstants;
import top.continew.admin.auth.enums.AuthTypeEnum;
import top.continew.admin.auth.model.FaceSession;
import top.continew.admin.auth.model.req.FaceLoginReq;
import top.continew.admin.auth.model.resp.FaceResultResp;
import top.continew.admin.auth.model.resp.FaceStatusResp;
import top.continew.admin.auth.model.resp.LoginResp;
import top.continew.admin.auth.service.AuthService;
import top.continew.admin.auth.service.FaceAuthService;
import top.continew.admin.auth.support.FaceSessionStore;
import top.continew.starter.core.exception.BadRequestException;
import top.continew.starter.core.exception.BusinessException;
import top.continew.starter.core.util.validation.ValidationUtils;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.util.HashMap;
import java.util.Map;

/**
 * 人脸认证业务实现
 *
 * @author Charles7c
 * @since 5.0.0
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class FaceAuthServiceImpl implements FaceAuthService {

    private final FaceAuthProperties properties;
    private final FaceSessionStore sessionStore;
    private final AuthService authService;

    @Override
    public String createLoginSession(String clientId) {
        String body = this.execute(HttpUtil.createPost(this.url("/sessions/login")));
        String sessionId = JSONUtil.parseObj(body).getStr("session_id");
        FaceSession session = new FaceSession();
        session.setSessionId(sessionId);
        session.setType(FaceAuthConstants.TYPE_LOGIN);
        session.setStatus(FaceAuthConstants.STATUS_PENDING);
        session.setClientId(clientId);
        sessionStore.save(session, properties.getMaxDuration());
        return sessionId;
    }

    @Override
    public String createRegisterSession(String username) {
        Map<String, Object> param = new HashMap<>(2);
        param.put("username", username);
        String body = this.execute(HttpUtil.createPost(this.url("/sessions/register"))
            .header("Content-Type", "application/json")
            .body(JSONUtil.toJsonStr(param)));
        String sessionId = JSONUtil.parseObj(body).getStr("session_id");
        FaceSession session = new FaceSession();
        session.setSessionId(sessionId);
        session.setType(FaceAuthConstants.TYPE_REGISTER);
        session.setStatus(FaceAuthConstants.STATUS_PENDING);
        session.setUsername(username);
        sessionStore.save(session, properties.getMaxDuration());
        return sessionId;
    }

    @Override
    public FaceResultResp processFrame(String sessionId, byte[] frame) {
        String body = this.execute(HttpUtil
            .createPost(this.url("/sessions/" + sessionId + "/frame"))
            .header("Content-Type", "application/octet-stream")
            .body(frame));
        return JSONUtil.toBean(body, FaceResultResp.class);
    }

    @Override
    public FaceResultResp getResult(String sessionId) {
        String body = this.execute(HttpUtil.createGet(this.url("/sessions/" + sessionId)));
        return JSONUtil.toBean(body, FaceResultResp.class);
    }

    @Override
    public LoginResp complete(String sessionId, HttpServletRequest request,
        HttpServletResponse response) {
        FaceSession session = sessionStore.get(sessionId);
        ValidationUtils.throwIf(ObjectUtil.isNull(session), "人脸会话不存在或已过期");
        ValidationUtils.throwIf(!FaceAuthConstants.TYPE_LOGIN.equals(session.getType()),
            "人脸会话类型无效");
        FaceResultResp snapshot = this.getResult(sessionId);
        ValidationUtils.throwIf(!Boolean.TRUE.equals(snapshot.getDone()), "人脸认证尚未完成");
        ValidationUtils.throwIf(StrUtil.isBlank(snapshot.getAccount()), "人脸认证未匹配到账号");
        // 回填匹配账号，供 FaceLoginHandler 二次校验并原子消费，防止伪造 / 重复签发
        session.setStatus(FaceAuthConstants.STATUS_SUCCESS);
        session.setUsername(snapshot.getAccount());
        sessionStore.save(session, properties.getMaxDuration());
        FaceLoginReq req = new FaceLoginReq();
        req.setAuthType(AuthTypeEnum.FACE);
        req.setClientId(session.getClientId());
        req.setUsername(snapshot.getAccount());
        req.setFaceSessionId(sessionId);
        LoginResp loginResp = authService.login(req, request, response);
        sessionStore.delete(sessionId);
        return loginResp;
    }

    @Override
    public FaceStatusResp getStatus(String username) {
        String body =
            this.execute(HttpUtil.createGet(this.url("/faces/" + URLUtil.encode(username))));
        FaceStatusResp resp = new FaceStatusResp();
        resp.setRegistered(JSONUtil.parseObj(body).getBool("registered"));
        return resp;
    }

    private String url(String path) {
        return properties.getBaseUrl() + path;
    }

    private String execute(HttpRequest request) {
        request.header("X-API-Key", properties.getApiKey());
        request.setConnectionTimeout((int) properties.getConnectTimeout().toMillis());
        request.setReadTimeout((int) properties.getReadTimeout().toMillis());
        try (HttpResponse httpResponse = request.execute()) {
            String body = httpResponse.body();
            if (!httpResponse.isOk()) {
                throw new BadRequestException(this.resolveDetail(body));
            }
            return body;
        } catch (BadRequestException e) {
            throw e;
        } catch (Exception e) {
            log.error("调用人脸服务失败", e);
            throw new BusinessException("无法连接人脸服务，请检查人脸服务是否启动");
        }
    }

    private String resolveDetail(String body) {
        if (StrUtil.isBlank(body)) {
            return "人脸服务调用失败";
        }
        try {
            String detail = JSONUtil.parseObj(body).getStr("detail");
            return StrUtil.blankToDefault(detail, "人脸服务调用失败");
        } catch (Exception e) {
            return "人脸服务调用失败";
        }
    }
}
