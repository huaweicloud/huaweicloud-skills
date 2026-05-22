---
name: terraform-installer
description: |
  Terraform 环境安装助手，跨平台支持 Linux 和 Windows。
  
  **触发场景**:
  - 用户说"安装 Terraform"、"初始化 Terraform 环境"、"设置 Terraform"
  - 用户说"安装华为云 Terraform Provider"
  - 在华为云 IaC 任务中检测到 Terraform 未安装
  - 用户需要配置 Terraform 离线安装环境
  
  **支持平台**: Linux (Ubuntu/Debian/RHEL/CentOS), Windows
  **默认安装**: 最新稳定版 Terraform 1.15.2 + HuaweiCloud Provider 1.81.0（华为云镜像）
---

# Terraform 环境安装助手

跨平台安装 Terraform 客户端，**默认使用华为云镜像**（避免 GitHub 网络问题）。

## 平台支持

| 平台 | 安装方式 | 说明 |
|------|----------|------|
| **Linux (Debian/Ubuntu)** | APT → Binary | 优先 APT，失败则二进制 |
| **Linux (RHEL/CentOS)** | Binary | 直接二进制下载 |
| **Windows** | Binary | 直接二进制下载（跳过包管理器检测） |

### Windows 特殊说明

**为什么不用包管理器？**
- Scoop/Chocolatey 检测超时慢
- Binary 直接下载 HashiCorp Releases 更快可靠

**Provider 安装方式**
- 使用 `filesystem_mirror`（本地文件镜像）
- 从华为云镜像下载 zip，解压到本地
- 配置 `terraform.rc` 指向本地目录

**不支持的方式**
- ❌ `direct` (Registry → GitHub)：GitHub 超时
- ❌ `network_mirror`：华为云镜像目录结构不兼容

## 快速使用

### 基础安装

```bash
# 自动安装（默认华为云镜像）
python scripts/install_terraform.py

# 安装 + 初始化
python scripts/install_terraform.py --init

# 安装 + 测试
python scripts/install_terraform.py --test
```

### 指定安装方式

```bash
# Linux: 使用 APT
python scripts/install_terraform.py --method apt

# Windows: 使用 Chocolatey（需要管理员权限）
python scripts/install_terraform.py --method choco

# Windows: 使用 Scoop（用户级安装，无需管理员）
python scripts/install_terraform.py --method scoop

# 通用: 二进制下载
python scripts/install_terraform.py --method binary
```

### 网络好的情况

```bash
# 使用官方源（需要网络畅通）
python scripts/install_terraform.py --no-mirror
```

### 其他操作

```bash
# 指定版本
python scripts/install_terraform.py --version 1.15.2

# 仅检查状态
python scripts/install_terraform.py --check

# 卸载
python scripts/install_terraform.py --uninstall
```

## 安装流程

### Linux

1. 检测系统类型和包管理器
2. Debian/Ubuntu: 尝试 APT 安装
3. RHEL/CentOS: 直接二进制下载
4. 配置华为云镜像
5. 验证 `terraform version`

### Windows

1. 检测管理员权限
2. 尝试包管理器安装:
   - **Scoop**（用户级，推荐）
   - **Chocolatey**（系统级，需要管理员）
3. 失败则二进制下载到:
   - 管理员: `C:\Program Files\Terraform\`
   - 普通用户: `%LOCALAPPDATA%\Terraform\`
4. 自动添加到 PATH 环境变量
5. 配置华为云镜像
6. 验证 `terraform version`

## 镜像源策略

| 资源 | 来源 | 说明 |
|------|------|------|
| Terraform 本体 | HashiCorp Releases | 官方源 |
| Provider | 华为云镜像（默认） | 避免 GitHub 网络问题 |

华为云镜像: `https://mirrors.huaweicloud.com/terraform/`

## 脚本参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--method` | 安装方式 | auto |
| `--version` | Terraform 版本 | 最新稳定版 |
| `--init` | 安装后运行 terraform init | false |
| `--test` | 安装后测试 Provider | false |
| `--mirror` | 使用华为云镜像 | **true（默认）** |
| `--no-mirror` | 禁用镜像，用官方源 | false |
| `--check` | 仅检查安装状态 | false |
| `--uninstall` | 卸载 Terraform | false |

## Windows 特殊说明

### PATH 配置

脚本会自动添加安装目录到 PATH：
- 管理员权限 → 系统级 PATH
- 普通用户 → 用户级 PATH

**需要重新打开终端**使 PATH 生效。

### 包管理器

| 工具 | 安装命令 | 权限要求 |
|------|----------|----------|
| **Scoop** | `scoop install terraform` | 无需管理员 |
| **Chocolatey** | `choco install terraform -y` | 需要管理员 |

如果没有安装包管理器，脚本会自动使用二进制下载方式。

## 故障排查

### 问题 1: Windows PATH 未生效

**解决**: 重新打开终端（PowerShell/CMD）

### 问题 2: 权限不足

```
[ERROR] 权限不足，请使用管理员权限运行
```

**解决**:
- Windows: 右键 → 以管理员身份运行
- Linux: `sudo python3 install_terraform.py`

### 问题 3: 网络超时

**解决**: 默认使用华为云镜像，不应出现此问题

## 相关资源

- [Terraform 官方文档](https://developer.hashicorp.com/terraform/docs)
- [HuaweiCloud Provider 文档](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [华为云镜像站](https://mirrors.huaweicloud.com/terraform/)
