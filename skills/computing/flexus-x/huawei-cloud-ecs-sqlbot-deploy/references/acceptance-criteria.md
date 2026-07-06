# 验收标准

## 概述

本文档定义本技能的验收标准，用于判断部署是否成功。

## 功能验收标准

### 1. ECS 实例创建

| 验收项 | 标准 | 验证方法 |
|--------|------|----------|
| 实例状态 | ACTIVE | 查询 ECS 状态 |
| 规格正确 | x1.4u.8g 或用户指定规格 | 查询实例详情 |
| 镜像正确 | Ubuntu 22.04 | 查询镜像信息 |
| 系统盘 | 40G 高IO | 查询磁盘信息 |

### 2. 网络配置

| 验收项 | 标准 | 验证方法 |
|--------|------|----------|
| EIP 绑定 | 已绑定且有公网 IP | 查询 EIP 状态 |
| 安全组 | sg-sqlbot 已创建 | 查询安全组列表 |
| 端口规则 | 8000 已开放 | 查询安全组规则 |

### 3. SQLBot 部署

| 验收项 | 标准 | 验证方法 |
|--------|------|----------|
| 服务状态 | 运行中 | 访问健康检查接口 |
| API 端口 | 8000 可访问 | curl http://ip:8000 |
| 登录验证 | admin/SQLBot@123456 可登录 | 测试登录接口 |

## 性能验收标准

| 验收项 | 标准 |
|--------|------|
| 部署时间 | < 15 分钟 |
| API 响应时间 | < 3 秒 |
| 页面加载时间 | < 5 秒 |

## 安全验收标准

| 验收项 | 标准 | 验证方法 |
|--------|------|----------|
| COC 部署验证 | UniAgent 在线且脚本执行成功 | 检查 COC 执行结果 |
| SQLBot 端口开放 | 8000 允许所有 IP | 检查安全组规则 |
| 无硬编码凭证 | 代码中无 AK/SK | 代码审查 |
| 密码复杂度 | 符合密码策略 | 检查默认密码 |

## 验收测试用例

### 测试用例 1：默认配置部署

**前置条件**：
- 有效的 AK/SK
- 项目 ID 和区域信息

**步骤**：

✅ **正确示例**：
```bash
# Execute deployment with default config
python3 deploy_sqlbot.py \
  --ak AKEXAMPLE123456 \
  --sk SKEXAMPLE789012 \
  --project-id PROJECT123456 \
  --region cn-north-4
```

**预期结果**：
- 所有验收项通过
- SQLBot 可正常访问和使用

### 测试用例 2：自定义配置部署

**前置条件**：
- 有效的 AK/SK
- 自定义服务器规格

**步骤**：

✅ **正确示例**：
```bash
# Execute deployment with custom config
python3 deploy_sqlbot.py \
  --ak AKEXAMPLE123456 \
  --sk SKEXAMPLE789012 \
  --project-id PROJECT123456 \
  --region cn-north-4 \
  --flavor x1.8u.16g \
  --name my-sqlbot-server
```

**预期结果**：
- 服务器规格符合自定义配置
- SQLBot 可正常访问和使用

### 测试用例 3：部署失败回滚

**前置条件**：
- 无效的 AK/SK（模拟认证失败）

**步骤**：

❌ **错误示例**：
```bash
# Invalid credentials - should fail gracefully
python3 deploy_sqlbot.py \
  --ak INVALID_AK \
  --sk INVALID_SK \
  --project-id PROJECT123456 \
  --region cn-north-4
```

**预期结果**：
- 返回明确的错误信息
- 无资源残留（或已清理）

## 验收报告模板

```markdown
# Acceptance Report

## Basic Information
- Skill Name: huawei-cloud-ecs-sqlbot-deploy
- Test Time: 2026-05-22 15:30:00
- Tester: TestUser

## Acceptance Results
| Item | Result | Notes |
|------|--------|-------|
| ECS Instance Creation | PASS | |
| Network Configuration | PASS | |
| SQLBot Deployment | PASS | |
| Performance Test | PASS | |
| Security Check | PASS | |

## Summary
- Passed: 5 items
- Failed: 0 items
- Conclusion: PASSED
```
