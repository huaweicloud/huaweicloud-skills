# hcloud CLI 安装配置指南

> 当生成的子 Skill 用户首次使用或 CLI 未安装时读取此文件。

## 安装 hcloud CLI

```bash
# pip 安装（推荐）
pip install hcloud

# 验证安装
hcloud --version
```

## 认证配置

凭据通过环境变量读取：

```bash
# 使用 CLI 前设置必需的环境变量
#   HUAWEI_ACCESS_KEY - 您的访问密钥 ID
#   HUAWEI_SECRET_KEY - 您的秘密访问密钥
export HUAWEI_REGION="cn-north-4"
```

> **安全提醒：** 不要在脚本中硬编码 AK/SK。使用环境变量或 IAM 角色。禁止通过 CLI 配置命令传入明文凭据。

## 获取 AK/SK

1. 登录华为云控制台
2. 进入「统一身份认证服务」→「我的凭证」
3. 点击「新增访问密钥」

## 验证配置

```bash
hcloud IAM ListUsers --cli-region=cn-north-4
```

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| `command not found: hcloud` | 检查 PATH，或重新安装 |
| `Authentication failed` | 检查 AK/SK 是否正确 |
| `Permission denied` | 检查 IAM 权限策略 |
| `Region not found` | 使用有效区域，如 cn-north-4 |
