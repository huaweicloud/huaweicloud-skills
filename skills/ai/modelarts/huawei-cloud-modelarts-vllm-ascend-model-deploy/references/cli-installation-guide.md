# CLI Installation Guide — KooCLI (hcloud)

本 skill 的核心部署操作默认使用 Python 脚本(`scripts/`)与 curl。KooCLI(hcloud)为**可选替代方式**，用于以 CLI 命令执行同等操作（如 `hcloud ModelArts CreateInferService`）。本指南覆盖 KooCLI 的安装、凭据配置、验证与故障排查。

## 目录

- [1. 安装 KooCLI](#1-安装-koocli)
- [2. 凭据配置](#2-凭据配置)
- [3. 验证安装](#3-验证安装)
- [4. 故障排查](#4-故障排查)
- [5. 安全最佳实践](#5-安全最佳实践)

---

## 1. 安装 KooCLI

### 版本要求

- **最低版本**: 不低于最新大版本的前一个大版本（如当前 7.x.x，则不低于 6.x.x）
- **最新版本**: 参见 https://support.huaweicloud.com/wtsnew-hcli/index.html
- **验证命令**: `hcloud version`
- **更新命令**: `hcloud update`

### 一键安装（所有平台）

```bash
# 交互式安装
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh

# 非交互式安装（跳过确认）
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh -y
```

### Linux

```bash
# 检测架构
echo $HOSTTYPE   # x86_64 或 aarch64

# x86_64
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-amd64.tar.gz"
tar -zxvf huaweicloud-cli-linux-amd64.tar.gz
sudo mv hcloud /usr/local/bin/

# ARM64
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-arm64.tar.gz"
tar -zxvf huaweicloud-cli-linux-arm64.tar.gz
sudo mv hcloud /usr/local/bin/
```

### macOS

```bash
# Intel (AMD64)
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-mac-amd64.tar.gz"
tar -zxvf huaweicloud-cli-mac-amd64.tar.gz
sudo mv hcloud /usr/local/bin/

# Apple Silicon (ARM64)
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-mac-arm64.tar.gz"
tar -zxvf huaweicloud-cli-mac-arm64.tar.gz
sudo mv hcloud /usr/local/bin/
```

### Windows

1. 下载: https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-windows-amd64.zip
2. 解压获取 `hcloud.exe`
3. 将 `hcloud.exe` 所在目录加入 PATH

---

## 2. 凭据配置

### 方式 1: 交互式配置（推荐）

```bash
hcloud configure
# 按提示输入:
# - Region (如 cn-north-4)
# - AK (Access Key ID)
# - SK (Access Key Secret)
```

### 方式 2: 环境变量

```bash
export HUAWEICLOUD_SDK_AK=<your-access-key-id>
export HUAWEICLOUD_SDK_SK=<your-access-key-secret>
```

### 方式 3: 非交互式配置

```bash
hcloud configure set --cli-profile=default --region=cn-north-4 --access-key-id=<AK> --secret-access-key=<SK>
```

> **⚠️ 安全警告**: 方式 3 会在命令历史中暴露 AK/SK，仅在安全环境中使用。

### 多环境配置

```bash
# 创建开发环境配置
hcloud configure init --cli-profile dev

# 创建生产环境配置
hcloud configure init --cli-profile prod

# 查看所有配置
hcloud configure list

# 使用指定配置
hcloud ModelArts CreateInferService --cli-profile=dev --cli-region=cn-north-4 ...
```

---

## 3. 验证安装

```bash
# 检查版本
hcloud version
# 预期输出: Current KooCLI version: 7.x.x

# 检查帮助
hcloud --help

# 测试认证（列出 OBS 桶）
hcloud obs ls

# 测试 ModelArts 服务（列出工作空间）
hcloud ModelArts ListWorkspaces --cli-region=cn-north-4 --project_id=<PROJECT_ID>
```

---

## 4. 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `hcloud: command not found` | 未安装或不在 PATH 中 | 重新安装或将 hcloud 路径加入 PATH |
| `authentication failed` | 凭据无效或已过期 | 重新执行 `hcloud configure` |
| `insufficient permissions` | IAM 权限不足 | 添加所需 IAM 策略（见 `references/iam-policies.md`） |
| `region not found` | 区域 ID 不正确 | 使用正确的区域 ID（如 cn-north-4） |
| `connection timeout` | 网络问题或代理配置 | 检查网络连接，必要时配置代理 |
| `param error` | CLI 参数格式错误 | 回退到本 skill 的 Python 脚本方式（见 SKILL.md 步骤 4.3） |

---

## 5. 安全最佳实践

1. **不要在对话中直接提供 AK/SK** — 使用交互式配置或环境变量
2. **定期轮换 AK/SK** — 建议每 90 天
3. **使用 IAM 临时凭据** — 优先使用 IAM 委托或临时凭据
4. **最小权限原则** — 仅授予所需最小权限（见 `references/iam-policies.md`）
5. **配置文件权限** — 确保 `~/.hcloud/` 目录权限为 600

---

## 参考

- [KooCLI 安装指南](https://support.huaweicloud.com/cli/cli_hcloud_install.html)
- [KooCLI 配置指南](https://support.huaweicloud.com/cli/cli_hcloud_configure.html)
- [KooCLI 命令参考](https://support.huaweicloud.com/cli/cli_hcloud_command_list.html)
- [ModelArts API 参考](https://support.huaweicloud.com/api-modelarts/api-modelarts-000000.html)
