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
import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import top.continew.admin.auth.enums.AuthTypeEnum;
import top.continew.admin.auth.model.req.RegisterReq;
import top.continew.admin.auth.model.resp.LoginResp;
import top.continew.admin.auth.service.AuthTokenService;
import top.continew.admin.common.enums.DisEnableStatusEnum;
import top.continew.admin.common.enums.GenderEnum;
import top.continew.admin.common.enums.RoleCodeEnum;
import top.continew.admin.system.model.entity.DeptDO;
import top.continew.admin.system.model.entity.user.UserDO;
import top.continew.admin.system.model.req.user.UserReq;
import top.continew.admin.system.model.resp.ClientResp;
import top.continew.admin.system.service.ClientService;
import top.continew.admin.system.service.DeptService;
import top.continew.admin.system.service.RoleService;
import top.continew.admin.system.service.UserService;
import top.continew.starter.core.util.validation.ValidationUtils;
import top.continew.starter.extension.tenant.context.TenantContextHolder;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import java.util.Collections;

/**
 * 公开注册 API
 *
 * @author Charles7c
 * @since 5.0.0
 */
@Tag(name = "公开注册 API")
@Validated
@RestController
@RequiredArgsConstructor
@RequestMapping("/auth")
public class RegisterController {

    private final UserService userService;
    private final RoleService roleService;
    private final DeptService deptService;
    private final ClientService clientService;
    private final AuthTokenService authTokenService;

    /**
     * 账号注册
     *
     * @param req      注册信息
     * @param request  请求对象
     * @param response 响应对象
     * @return 登录结果
     */
    @SaIgnore
    @Operation(summary = "账号注册", description = "创建普通用户账号并自动登录")
    @PostMapping("/register")
    public LoginResp register(@RequestBody @Valid RegisterReq req, HttpServletRequest request,
        HttpServletResponse response) {
        // 组装用户创建参数：roleIds / status / deptId 等敏感字段一律由后端固定，不采信前端
        UserReq userReq = new UserReq();
        userReq.setUsername(req.getUsername());
        userReq.setNickname(StrUtil.blankToDefault(req.getNickname(), req.getUsername()));
        userReq.setPassword(req.getPassword());
        userReq.setEmail(req.getEmail());
        userReq.setPhone(req.getPhone());
        userReq.setGender(GenderEnum.UNKNOWN);
        userReq.setStatus(DisEnableStatusEnum.ENABLE);
        userReq.setDeptId(this.resolveDefaultDeptId());
        userReq.setRoleIds(Collections.singletonList(this.resolveGeneralRoleId()));
        // 复用现有创建链路（密码解密 / 加密、唯一性校验、角色分配）
        userService.create(userReq);
        // 注册成功后自动登录：复用统一令牌签发，不经过账号登录的验证码校验
        ClientResp client = clientService.getByClientId(req.getClientId());
        ValidationUtils.throwIf(client == null, "客户端不存在");
        ValidationUtils.throwIf(DisEnableStatusEnum.DISABLE.equals(client.getStatus()), "客户端已禁用");
        ValidationUtils.throwIf(!client.getAuthType().contains(AuthTypeEnum.ACCOUNT.getValue()),
            "该客户端暂未授权 [{}] 认证", AuthTypeEnum.ACCOUNT.getDescription());
        UserDO user = userService.getByUsername(req.getUsername());
        return authTokenService.issue(user, client, TenantContextHolder.getTenantId(), request,
            response);
    }

    private Long resolveDefaultDeptId() {
        DeptDO deptDO = deptService.getOne(new LambdaQueryWrapper<DeptDO>()
            .eq(DeptDO::getIsSystem, true)
            .eq(DeptDO::getParentId, 0));
        ValidationUtils.throwIf(deptDO == null, "未查询到系统内置部门");
        return deptDO.getId();
    }

    private Long resolveGeneralRoleId() {
        Long generalRoleId = roleService.getIdByCode(RoleCodeEnum.GENERAL_USER.getCode());
        ValidationUtils.throwIf(generalRoleId == null, "未查询到普通用户角色");
        return generalRoleId;
    }
}
