# KooCLI (hcloud) Installation & Configuration Guide

> 本文件适用于首次使用 KooCLI (华为云命令行工具) 的用户或需要重新配置认证的场景。
> KooCLI 是华为云官方提供的 Go 二进制 CLI 工具，**不是** Python PyPI 包，请勿使用 `pip install` 安装。

## 安装 KooCLI

从华为云官方下载适配操作系统的二进制包：

| 操作系统 | 下载地址 |
|----------|----------|
| Windows 64位 | [KooCLI-windows-amd64.zip](https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-windows-amd64.zip) |
| Linux AMD 64位 | [KooCLI-linux-amd64.tar.gz](https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-amd64.tar.gz) |
| Linux ARM 64位 | [KooCLI-linux-arm64.tar.gz](https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-arm64.tar.gz) |
| macOS AMD 64位 | [KooCLI-mac-amd64.tar.gz](https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-mac-amd64.tar.gz) |
| macOS ARM 64位 | [KooCLI-mac-arm64.tar.gz](https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-mac-arm64.tar.gz) |

安装步骤：

1. 下载对应系统的压缩包
2. 解压得到 `hcloud`（Linux/macOS）或 `hcloud.exe`（Windows）
3. 将可执行文件所在目录添加到系统 PATH 环境变量
4. 验证安装：

```bash
hcloud version
```

## 认证配置

CLI 从环境变量读取认证信息：

```bash
# 设置必要的环境变量
# ⚠️ NEVER commit real keys. Use a secrets manager or .env file.
export HUAWEI_ACCESS_KEY="your-access-key-id"
export HUAWEI_SECRET_KEY="your-secret-access-key"
export HUAWEI_REGION="cn-north-4"
```

> **安全提醒：** 禁止在脚本中硬编码 AK/SK。使用环境变量或 IAM 角色。
> 不要通过 CLI 配置命令传递明文凭证。

## 获取 AK/SK

1. 登录华为云控制台
2. 进入"身份与访问管理" → "我的凭证"
3. 点击"新增访问密钥"

## 验证配置

```bash
# 查看已配置的认证信息
hcloud configure list

# 测试 API 调用
hcloud IAM ListUsers --cli-region=cn-north-4 --limit=1
```

## 查看可用服务

```bash
# 查看所有支持的服务
hcloud --help

# 查看某个服务的所有操作
hcloud ECS --help
```

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| `command not found: hcloud` | 检查 PATH 是否包含 KooCLI 所在目录，或重新下载安装 |
| `Authentication failed` | 确认 AK/SK 正确 |
| `Permission denied` | 检查 IAM 权限策略 |
| `Region not found` | 使用有效的区域，如 `cn-north-4` |
| `Unsupported method` | 某些国际站账号不支持 AK/SK 认证，需使用 X-Auth-Token |
