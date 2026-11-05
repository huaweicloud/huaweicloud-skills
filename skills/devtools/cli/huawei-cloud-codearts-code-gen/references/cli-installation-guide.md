# CLI Installation Guide（CodeArts CLI 安装与配置指南）

> 本文件覆盖 `codearts` CLI 的三平台安装、PATH 设置、AK/SK 配置与清理、权限配置、连通性验证与常见问题。
> 口径与 `SKILL.md`、`scripts/*.sh`、`scripts/*.ps1` **完全一致**：退出码 `0 / 2 / 10 / 20 / 30 / 40 / 50`，wrapper 额外使用 `1 / 10 / 30 / 40 / 50 / 60`。
> ⚠️ 本 skill **不使用 `hcloud` / KooCLI**：它调用的是 `codearts` CLI 与本地脚本，`codearts` **没有 `--cli-region` 参数**，也不使用 `HUAWEICLOUD_SDK_*` 凭据体系。KooCLI 语法只在本仓库的 `## KooCLI Command Format Standard` 章节中作为规范说明。

---

## 1. 安装总览

`codearts` 是**运行时从华为云 OBS 下载安装的外部二进制**，不随本 skill 仓库分发。安装由 `scripts/setup.sh`（Linux / macOS / Git Bash）或 `scripts/setup.ps1`（Windows PowerShell）自动完成。

| 项 | Linux / macOS / Git Bash | Windows PowerShell |
|----|--------------------------|--------------------|
| 安装脚本 URL | `https://cnnorth4-cloudide-marketplace.obs.cn-north-4.myhuaweicloud.com/codearts/cli_tui/install_script/install.sh` | `https://cnnorth4-cloudide-marketplace.obs.cn-north-4.myhuaweicloud.com/codearts/cli_tui/install_script/install.ps1` |
| 可执行文件路径 | `~/.codeartsdoer/installers/codearts` | `%USERPROFILE%\.codeartsdoer\installers\codearts.cmd` |
| 自动安装入口 | `bash scripts/setup.sh` | `powershell -ExecutionPolicy Bypass -File scripts/setup.ps1` |
| 下载重试 | 3 次（可用 `CODEARTS_SETUP_MAX_RETRY` 调整） | 3 次（同上） |
| 下载工具 | `curl` 优先，其次 `wget`；两者都没有 → `exit 30` `dependency_missing` | `Invoke-WebRequest`（`-UseBasicParsing`，超时 30s） |

安装流程（两步都成功才算就绪）：

1. 检查可执行文件是否已存在；存在则直接跳过安装；
2. 不存在则下载并执行安装脚本，随后**再次校验**可执行文件是否存在（校验失败 → `exit 30` `install_verify_failed`）。

**安装失败的退出码与 `type`**（stdout 输出单个 JSON）：

| `type` | 触发条件 |
|--------|---------|
| `dependency_missing` | Linux/macOS 上 `curl` 与 `wget` 都不存在 |
| `download_failed` | 安装脚本下载失败（已重试 3 次） |
| `install_failed` | 安装脚本执行失败 |
| `install_verify_failed` | 安装脚本执行后仍找不到可执行文件 |
| `unsupported_os` | Windows 上用 `setup.sh`（提示改用 PowerShell），或系统无法识别 |

> 安装脚本的输出被重定向到 **stderr**，以保证 stdout 始终只有一个 JSON 对象。

---

## 2. 三平台安装 / PATH 设置

### 2.1 Linux / macOS（含 Windows Git Bash）

```bash
# 方式一：由本 skill 自动安装（推荐）
bash scripts/setup.sh

# 方式二：手动安装（等价，curl 或 wget 任一）
curl -fsSL https://cnnorth4-cloudide-marketplace.obs.cn-north-4.myhuaweicloud.com/codearts/cli_tui/install_script/install.sh | sh

# 校验
ls -l "$HOME/.codeartsdoer/installers/codearts"
"$HOME/.codeartsdoer/installers/codearts" --version
```

PATH 只在**需要直接调用 `codearts` 二进制**时才要手动设置（使用 `scripts/codearts_run.sh` 时 wrapper 内部自己定位，无需手工设置）：

```bash
export PATH="$HOME/.codeartsdoer/installers:$PATH"
```

写入 `~/.bashrc` 以便长期生效（本 skill **不使用**原地编辑工具，改动 `~/.bashrc` 请用编辑器手工添加该行）：

```bash
echo 'export PATH="$HOME/.codeartsdoer/installers:$PATH"' >> ~/.bashrc
```

macOS 提示：本 skill 的脚本兼容 macOS 自带的 **bash 3.2**（不使用 bash 4 专有语法）；`~/.bashrc` 的改写采用「过滤到临时文件 + 原子替换 + `mkdir` 目录锁」，不依赖 GNU 专有工具，也不存在 BSD/GNU 的 `sed` 原地编辑差异。

### 2.2 Windows PowerShell（5.1+）

```powershell
# 方式一：由本 skill 自动安装（推荐）
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

# 方式二：手动安装
irm https://cnnorth4-cloudide-marketplace.obs.cn-north-4.myhuaweicloud.com/codearts/cli_tui/install_script/install.ps1 | iex

# 校验
Test-Path "$env:USERPROFILE\.codeartsdoer\installers\codearts.cmd"
```

PATH 设置：

```powershell
$env:PATH = "$env:USERPROFILE\.codeartsdoer\installers;$env:PATH"
```

要在当前用户中长期生效（写入用户级环境变量，**不是** Machine 级）：

```powershell
$p = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($p -notlike "*\.codeartsdoer\installers*") {
  [Environment]::SetEnvironmentVariable("PATH", "$env:USERPROFILE\.codeartsdoer\installers;$p", "User")
}
```

### 2.3 指定自定义 CLI 路径（三平台通用）

wrapper 与验证脚本都支持用 `CODEARTS_CLI_BIN` 覆盖 CLI 位置（优先级最高）：

```bash
export CODEARTS_CLI_BIN="/opt/codearts/codearts"   # Linux / macOS / Git Bash
```

```powershell
$env:CODEARTS_CLI_BIN = "D:\tools\codearts\codearts.cmd"   # Windows
```

定位顺序：`CODEARTS_CLI_BIN` → `$HOME/.codeartsdoer/installers/codearts`；找不到 → `{"status":"error","code":30,"type":"cli_not_installed"}`，`exit 30`。
若文件存在但丢了可执行位且首行是 shebang，wrapper 会用 `sh` 运行它；否则同样按 `cli_not_installed` 报错。

---

## 3. AK/SK 配置与清理

### 3.1 配置（保存）

```bash
bash scripts/setup.sh --save-aksk <AK> <SK>
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 --save-aksk <AK> <SK>
```

- Linux / macOS：写入 `~/.bashrc` 中的 `export CODEARTS_CLI_AK=...` / `export CODEARTS_CLI_SK=...`（新建文件 `chmod 600`；已存在则保留原权限位）；
- Windows：写入**当前用户**的用户级环境变量（默认 `User` 作用域）；
- 参数校验失败（缺 SK、AK/SK 为空、缺少选项值）→ `{"status":"error","code":2,"type":"invalid_arguments"}` 或 `"type":"empty_credentials"`，`exit 2`，并且**不会**写坏配置文件；
- 取不到 `~/.bashrc` 目录锁（默认等待 10×0.2s=2s，可由 `CODEARTS_SETUP_LOCK_RETRY` / `CODEARTS_SETUP_LOCK_SLEEP` 调整）→ `type: "lock_timeout"`，`exit 2`。

临时使用而不保存（不写任何文件）：

```bash
bash scripts/setup.sh --ak <AK> --sk <SK>
```

### 3.2 清理（删除）

```bash
# Linux / macOS / Git Bash
bash scripts/setup.sh --clear-aksk
```

```powershell
# Windows PowerShell（-ClearAksk 与 --clear-aksk 等价）
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -ClearAksk
```

成功的输出（stdout 单个 JSON，`exit 0`）：

```json
{"status":"cleared","code":0,"message":"AK/SK removed from ~/.bashrc"}
```

Windows 的 `-ClearAksk` 同时清理用户级环境变量与 `.bashrc` 中的同名行（若存在）。

### 3.3 安全提醒（必须原样告知用户）

- AK/SK 以**明文**存放在环境变量 / `~/.bashrc` 中；
- 请勿向他人泄露 AK/SK，以免凭据被非授权使用，造成资源盗用或资金损失；
- AK/SK 只保存在本地 AI Shell 环境变量中，**不会上传**到任何外部服务；可以手工清理，或等环境资源回收时自动释放；
- 生成任务完成后，Agent 必须提醒用户凭据仍在本机，并主动询问是否删除。

### 3.4 环境变量清单

| 变量 | 作用 | 默认值 |
|------|------|--------|
| `CODEARTS_CLI_AK` / `CODEARTS_CLI_SK` | 运行时凭据（wrapper 优先读环境变量，其次读 `~/.bashrc`） | 无 |
| `CODEARTS_CLI_BIN` | 指定 `codearts` 可执行文件路径 | `$HOME/.codeartsdoer/installers/codearts` |
| `CODEARTS_SETUP_MAX_RETRY` | 下载 / 连通性重试次数（测试钩子） | `3` |
| `CODEARTS_SETUP_RETRY_DELAY` | 重试间隔秒数（测试钩子） | `5` |
| `CODEARTS_SETUP_LOCK_RETRY` / `CODEARTS_SETUP_LOCK_SLEEP` | 目录锁重试次数 / 间隔（测试钩子） | `10` / `0.2` |
| `CODEARTS_SETUP_LOCK_STALE` | 陈旧锁目录判定秒数（测试钩子） | `30` |
| `CODEARTS_CLI_ENV_SCOPE` | PowerShell 侧写入作用域：`User`（默认）/ `Process`（**仅测试用**） | `User` |
| `CODEARTS_BASHRC_PATH` | PowerShell 侧 `.bashrc` 路径覆盖（测试钩子） | `%USERPROFILE%\.bashrc` |

> 所有 `*_SETUP_*` / `*_ENV_SCOPE` / `*_BASHRC_PATH` 变量都是**测试钩子**，正常运行不需要设置。

---

## 4. 权限配置

CLI 需要文件读写权限才能生成代码。Agent 必须先取得用户**显式同意**，再执行：

```bash
bash scripts/permission.sh --agree /workspace
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts\permission.ps1 --agree /workspace
```

- `--agree` 后跟目录 → 权限限制在该目录（生成 `"pattern": "<workspace>/*"`）；
- `--agree` 不带目录 → 全局权限（`"pattern": "*"`），**不推荐**；
- 交互式（无 `--agree`）在非 TTY 环境下直接 `exit 1` 并提示 `Usage: permission.sh --agree [workspace]`；
- 权限文件路径：`~/.codeartsdoer/cli-data/storage/permission/global.json`（Windows：`%USERPROFILE%\.codeartsdoer\cli-data\storage\permission\global.json`）；
- 写入采用「同目录临时文件 + 原子 `mv`」，不会留下被截断的 JSON；
- stdout 输出为机器可读的 `PERMISSION_CONFIGURED` 加一行文件绝对路径（**不是 JSON**，这是有意保留的既有接口）。

判定「已配置」的条件：`global.json` 中存在 `permission` 为 `edit` 且 `permission` 为 `write`、且两者 `action` 均为 `allow` 的记录；判定使用真正的 JSON 解析，紧凑与 pretty 写法结果一致。未配置 → `scripts/setup.sh` 输出 `{"status":"need_consent","code":20,"type":"permission_required",...}` 并 `exit 20`。

---

## 5. 连通性验证与代码生成

```bash
# 用 wrapper 验证凭据与连通性（推荐）
bash scripts/codearts_run.sh models

# 生成代码（任务描述是最后一个位置参数；-f / --file 可重复）
bash scripts/codearts_run.sh run --format json -m "provider/model" "task description"
bash scripts/codearts_run.sh run --format json -m "provider/model" -f ./existing.py "add docstrings"
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts\codearts_run.ps1 models
powershell -ExecutionPolicy Bypass -File scripts\codearts_run.ps1 run --format json -m "provider/model" -f .\existing.py "add docstrings"
```

wrapper 的退出码契约：成功 `0`；失败时 stdout **有且只有一个** JSON 对象，其余日志走 stderr 并带 `[codearts_run]` 前缀。失败码：`1` `cli_failed`、`10` `aksk_required`、`30` `cli_not_installed`、`40` `network_failed`、`50` `auth_failed`、`60` `output_contract_violation`（含 `-f` 附件的 `attachment_failed`）。**失败时绝不会 `exit 0`。**

`-m` 必须是从 `codearts models` 输出中逐字复制的完整 `provider/model`（例如 `huaweicloud-maas/GLM-5.1`）；短名会被原样转发并导致请求失败。

---

## 6. 常见问题排查

| 现象 / 错误码 | 原因 | 处理 |
|---------------|------|------|
| `30 download_failed` | 网络不可达 / 代理问题 | 检查网络与代理；或按第 2 节手动安装后重试 |
| `30 dependency_missing` | `curl`、`wget` 都不存在 | 安装其一：`apt install curl` / `yum install curl` |
| `30 unsupported_os` | 用 `setup.sh` 跑在 Windows 上 | 改用 `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1` |
| `30 cli_not_installed`（wrapper） | CLI 不在默认路径 | 跑一次 `setup.sh`，或设置 `CODEARTS_CLI_BIN` |
| `10 aksk_required` | 环境变量与 `~/.bashrc` 都没有凭据 | 执行 `bash scripts/setup.sh --save-aksk <AK> <SK>` |
| `50 auth_failed` | AK/SK 无效 / 过期 / 无权限 | 到 IAM 控制台核对并重新生成访问密钥，再重新保存 |
| `40 network_failed` | 连通性检查重试后仍失败 | 检查网络、代理、DNS；确认区域可访问 |
| `20 permission_required` | 权限未配置或权限不足 | 取得用户同意后执行 `bash scripts/permission.sh --agree /workspace` |
| `2 lock_timeout` | `~/.bashrc.lock` 目录陈旧（上次异常退出） | 确认无其它写入进程后删除该锁目录：`rmdir ~/.bashrc.lock` |
| `2 invalid_arguments` / `empty_credentials` | 选项缺值 / AK 或 SK 为空 | 按提示补齐：`--save-aksk <AK> <SK>` |
| `60 output_contract_violation` | CLI 退出 0 但 stdout 为空或不是合法 JSONL | 检查 CLI 版本与网络；`--format json` 下每一非空行必须是合法 JSON |
| `60 attachment_failed` | `-f` 指向不存在 / 非普通文件 / 不可读 / 空文件 | 改用存在的非空普通文件；任务描述必须作为最后一个参数 |
| 中文乱码 | 控制台代码页问题，与文件编码无关 | 核对文件内容用编辑器/读取工具；必要时 `export PYTHONIOENCODING=utf-8` |
| `.ps1` 无法执行 | 执行策略限制 | 使用 `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 ...` |

---

## 7. 与 KooCLI（`hcloud`）的区别

| 维度 | 本 skill（`codearts`） | KooCLI（`hcloud`） |
|------|----------------------|-------------------|
| 命令形式 | `codearts <subcommand> [--key=value] [--file <f>]... "<task>"` | `hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]` |
| 区域参数 | **没有** `--cli-region` | 必须有 `--cli-region=<region>` |
| 凭据 | `CODEARTS_CLI_AK` / `CODEARTS_CLI_SK` | `HUAWEICLOUD_SDK_*` 或 CLI profile |
| 安装位置 | `~/.codeartsdoer/installers` | 由 KooCLI 自身安装器管理 |
| 本 skill 是否调用 | **是**（经 wrapper） | **否**（仅作规范说明） |

KooCLI 标准语法（本节仅作规范说明，本 skill 不执行）：

```bash
hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]
# 示例（PascalCase 操作名 + 区域参数）
hcloud IAM ListPoliciesV5 --cli-region=cn-north-4
```
