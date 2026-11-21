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

package top.continew.admin.auth.handler;

import cn.hutool.core.util.ObjectUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import top.continew.admin.auth.AbstractLoginHandler;
import top.continew.admin.auth.constant.FaceAuthConstants;
import top.continew.admin.auth.enums.AuthTypeEnum;
import top.continew.admin.auth.model.FaceSession;
import top.continew.admin.auth.model.req.FaceLoginReq;
import top.continew.admin.auth.model.resp.LoginResp;
import top.continew.admin.auth.support.FaceSessionStore;
import top.continew.admin.system.model.entity.user.UserDO;
import top.continew.admin.system.model.resp.ClientResp;
import top.continew.starter.core.util.validation.ValidationUtils;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * 人脸登录处理器
 *
 * @author Charles7c
 * @since 5.0.0
 */
@Component
@RequiredArgsConstructor
public class FaceLoginHandler extends AbstractLoginHandler<FaceLoginReq> {

    private final FaceSessionStore faceSessionStore;

    @Override
    public LoginResp login(FaceLoginReq req, ClientResp client, HttpServletRequest request,
        HttpServletResponse response) {
        // 二次校验人脸会话（类型、成功态、账号一致），并原子消费防止重复签发令牌
        FaceSession session = faceSessionStore.get(req.getFaceSessionId());
        ValidationUtils.throwIf(ObjectUtil.isNull(session), "人脸会话不存在或已过期");
        ValidationUtils.throwIf(!FaceAuthConstants.TYPE_LOGIN.equals(session.getType()),
            "人脸会话类型无效");
        ValidationUtils.throwIf(!FaceAuthConstants.STATUS_SUCCESS.equals(session.getStatus()),
            "人脸认证尚未成功");
        ValidationUtils.throwIf(!req.getUsername().equals(session.getUsername()),
            "人脸会话与账号不匹配");
        ValidationUtils.throwIf(!faceSessionStore.consume(req.getFaceSessionId()),
            "人脸会话已消费或正在登录");
        UserDO user = userService.getByUsername(req.getUsername());
        ValidationUtils.throwIf(ObjectUtil.isNull(user), "登录用户不存在");
        return super.authenticate(user, client, request, response);
    }

    @Override
    public AuthTypeEnum getAuthType() {
        return AuthTypeEnum.FACE;
    }
}
