# CLI Installation Guide — KooCLI (hcloud)

本 skill 的核心部署操作默认使用 Python 脚本(`scripts/`)与 curl。KooCLI(hcloud)为**可选替代方式**，用于执行通用的查询/管理命令（如 `hcloud ModelArts ListWorkspace` 查询工作空间、`hcloud obs ls` 查询桶）。**ModelArts 推理服务(InferService)相关操作 hcloud 不支持**(见 `SKILL.md`「KooCLI 命令格式标准」)，创建/查询/扩缩容请统一使用 `scripts/create_infer_service.py`（REST 方式）。本指南覆盖 KooCLI 的安装、凭据配置、验证与故障排查。

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

> 注: 环境变量仅对 API 模式生效。`hcloud obs` 子命令走 obsutil 模式，还需 AK/SK/endpoint 配置文件（见 §3 的 `hcloud obs config`）。

### 方式 3: 非交互式配置（只写非敏感项）

```bash
# 凭据仍由方式 2 的 HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK 环境变量提供（不落盘）
# 这里只非交互写入 profile 与 region
hcloud configure set --cli-profile=default --region=cn-north-4
```

> **⚠️ 安全提示**: **不要**把 AK/SK 作为命令行参数传给 `hcloud configure set --access-key-id=... --secret-access-key=...`——凭据会明文写入配置文件，并留在 shell 历史中。请用方式 2 的环境变量（进程内生效、不写盘；见上方已导出的 `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK`），或方式 1 的 `hcloud configure init` 交互式录入。

### 多环境配置

```bash
# 创建开发环境配置
hcloud configure init --cli-profile dev

# 创建生产环境配置
hcloud configure init --cli-profile prod

# 查看所有配置
hcloud configure list

# 使用指定配置（示例: 查询工作空间）
hcloud ModelArts ListWorkspace --cli-profile=dev --cli-region=cn-north-4 --project_id="${PROJECT_ID}"
```

---

## 3. 验证安装

以下命令按顺序执行即可完成安装与凭据验证（先准备 `REGION` / `PROJECT_ID` 两个 shell 变量）：

```bash
# 变量准备
# REGION: 区域 ID
export REGION=cn-north-4
# PROJECT_ID: 32 位项目 UUID（不是项目名称/区域名）
# 取值来源: 华为云控制台「我的凭证 → API 凭证 → 项目列表」中的「项目 ID」列
export PROJECT_ID=0123456789abcdef0123456789abcdef   # 替换为你的实际项目 UUID

# 1) 检查版本
hcloud version
# 预期输出: Current KooCLI version: 7.x.x

# 2) 确认凭据配置已生效（列出所有 profile）
hcloud configure list

# 3) 验证 ModelArts 认证（列出工作空间）
#    注意: 操作名是 ListWorkspace（无复数 s），写 ListWorkspaces 会报「不支持的operation」
hcloud ModelArts ListWorkspace --cli-region="${REGION}" --project_id="${PROJECT_ID}"

# 4) 验证 OBS 认证（obsutil 模式，需 AK/SK/endpoint；AK/SK 取自 §2 任一配置方式）
hcloud obs config -i="${HUAWEICLOUD_SDK_AK:?请先设置 AK}" -k="${HUAWEICLOUD_SDK_SK:?请先设置 SK}" -e="obs.${REGION}.myhuaweicloud.com"
hcloud obs ls
```

> **创建/管理推理服务不通过 CLI**: `hcloud` 不支持 ModelArts InferService 相关操作，请使用 `python3 scripts/create_infer_service.py --help`（REST 方式，见 `SKILL.md` 步骤 4.3）。

---

## 4. 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `hcloud: command not found` | 未安装或不在 PATH 中 | 重新安装或将 hcloud 路径加入 PATH |
| `authentication failed` | 凭据无效或已过期 | 重新执行 `hcloud configure` |
| `insufficient permissions` | IAM 权限不足 | 添加所需 IAM 策略（见 `references/iam-policies.md`） |
| `region not found` | 区域 ID 不正确 | 使用正确的区域 ID（如 cn-north-4） |
| `connection timeout` | 网络问题或代理配置 | 检查网络连接，必要时配置代理 |
| `Warn: Please set ak, sk and endpoint in the configuration file!` | `hcloud obs` 走 obsutil 模式，未配置 AK/SK/endpoint | 先执行 `hcloud obs config -i="${HUAWEICLOUD_SDK_AK}" -k="${HUAWEICLOUD_SDK_SK}" -e="obs.${REGION}.myhuaweicloud.com"` |
| `[USE_ERROR]不支持的 operation` | 操作名或服务名拼写错误（如 `ListWorkspaces`；ModelArts 实际为 `ListWorkspace`），或该操作 hcloud 未提供 | 用 `hcloud <Service> <Operation> --help` 核对操作名；ModelArts 推理服务(InferService)相关操作 hcloud 不支持，改用 `scripts/create_infer_service.py`。**注意: 这种操作名错误时 KooCLI 退出码仍为 0**，只在 stderr 打印 `[USE_ERROR]...`，脚本化判定必须检查 stderr（如 `out=$(hcloud ... 2>&1)` 后 `grep USE_ERROR`），不能只看 `$?` |
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
