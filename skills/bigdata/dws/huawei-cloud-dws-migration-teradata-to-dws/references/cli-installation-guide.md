# CLI Installation Guide - Teradata to DWS Migration

本 skill 的核心迁移工具链为 Python 脚本（`pre_migration_check.py`、`migrate_schema.py`、`migrate_data.py`、`validate_migration.py` 等），数据迁移本身不依赖 hcloud 命令。但在以下辅助场景需要使用华为云 KooCLI（`hcloud`）：

- 查询 DWS 集群列表与连接信息（确认集群状态、版本、连接端点）
- 查看 OBS 桶列表与对象（配合 `--method obs` 迁移前确认桶可用）

## Table of Contents

- [hcloud (KooCLI) Installation](#hcloud-kocli-installation)
- [Credential Configuration](#credential-configuration)
- [Verify Installation](#verify-installation)
- [Standard Command Format](#standard-command-format)
- [DWS / OBS Related Commands](#dws--obs-related-commands)
- [Troubleshooting](#troubleshooting)

---

## hcloud (KooCLI) Installation

### Linux (ARM64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-arm64.tar.gz
tar -xzf hcloudcli-linux-arm64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

### Linux (x86_64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-amd64.tar.gz
tar -xzf hcloudcli-linux-amd64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

### macOS

```bash
# Install via Homebrew
brew install hcloudcli

# Or download directly
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-macos-amd64.tar.gz
tar -xzf hcloudcli-macos-amd64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

### Windows

```powershell
Invoke-WebRequest -Uri "https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-windows-amd64.zip" -OutFile "hcloudcli.zip"
Expand-Archive hcloudcli.zip
# Add hcloud.exe to PATH
```

---

## Credential Configuration

### Method 1: Interactive configuration (recommended)

```bash
hcloud configure
# Enter as prompted:
# - Region (e.g., cn-south-1)
# - AK (Access Key ID)
# - SK (Access Key Secret)
```

### Method 2: Environment variables

```bash
export HUAWEICLOUD_SDK_AK=<access-key-id>
export HUAWEICLOUD_SDK_SK=<access-key-secret>
```

### Method 3: Non-interactive configuration

```bash
hcloud configure set --cli-profile=default --cli-mode=AKSK --cli-region=<region> --cli-access-key=<access-key-id> --cli-secret-key=<access-key-secret>
```

> **安全提示**：请通过安全凭据管理工具或环境变量注入实际密钥，勿在脚本/文档中提交真实 AK/SK。

---

## Verify Installation

```bash
hcloud version
# Expected: version number displayed

hcloud configure list
# Expected: current profile, region and credential status displayed
```

---

## Standard Command Format

所有 hcloud 命令统一使用 `--cli-region` 指定区域：

```bash
hcloud <Service> <Operation> --cli-region=<region> --<param1>=<value1> --<param2>=<value2> ...
```

**参数规范**：

| 参数 | 说明 | 示例 |
|------|------|------|
| `--cli-region` | 区域 ID，必填 | `cn-south-1`、`cn-north-4` |
| `--project_id` | 项目 ID | 通过 IAM 查询 |

> **注意**：DWS `ListClusters` 仅支持 `--cli-region`、`--project_id`、`--enterprise_project_id`，**不支持** `--offset`/`--limit` 分页参数，请勿携带（否则报 `[USE_ERROR]不正确的参数:offset`）。

**项目 ID 查询**：

```bash
hcloud IAM KeystoneListProjects --cli-region=<region>
```

---

## DWS / OBS Related Commands

```bash
# 查询 DWS 集群列表（获取 cluster_id、连接端点）
hcloud DWS ListClusters --cli-region=<region> --project_id=<project-id>

# 查询 DWS 集群详情
hcloud DWS ListClusterDetails --cli-region=<region> --project_id=<project-id> --cluster_id=<cluster-id>

# 查询 OBS 桶列表
# 注意：hcloud OBS 为 obsutil 透传命令，不存在 `ListBuckets` 子命令（会报 `Error: No such command`），
# 请使用 obsutil 风格语法（区域/凭证由 obsutil 配置或环境变量提供）：
hcloud obs ls
```

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `Auth failed` / 401 | 未配置或配置了失效的 AK/SK | 重新执行 `hcloud configure` |
| `403 Forbidden` | IAM 权限不足 | 参考 `references/iam-policies.md` 授予对应权限 |
| `disconnect` / network error | 无法访问华为云 API 端点 | 检查网络、代理与 DNS |
| `unrecognized cli-region` | 区域 ID 拼写错误 | 使用标准区域 ID，如 `cn-north-4` |