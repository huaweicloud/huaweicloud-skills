# 华为云 SMS 主机迁移自动化编排（scripts/windows_migration）

> 📦 **2026-09 增补**：新增 **SMS 控制面编排脚本（步骤二~五）**：`sms_task.py` / `core/sms_client.py` /
> `core/target_provider.py` / `run_sms_task.sh`。迁移 Agent 部署（步骤一）与 SMS 控制面任务（步骤二~五）
> 已打通。**所有踩坑与根因沉淀已统一归档至 [`../../references/troubleshooting.md`](../../references/troubleshooting.md)**，尤其 **SMS.0515 磁盘映射**与
> **KooCLI 反斜杠转义** 两节。

通过 WinRM 远程驱动华为云 SMS (Server Migration Service) Agent 在 Windows 源端主机上的
下载、安装、配置、注册全流程。支持单台迁移和 **100 台批量并发迁移**，大文件走 OBS 签名 URL
源端直下（沙箱零带宽）。项目自包含，`proxyopt/` 已内嵌。

支持两条 Agent 配置路线：
- **Py3**（Win Server 2012+，默认）：AutoIt/exe GUI 自动化
- **Py2**（Win Server 2008/Win 7；2003 见兼容矩阵）：C# AttachConsole 控制台状态机

## 架构

```
huawei-cloud-migration-windows-ecs/
├── SKILL.md / README.md / requirements.txt   # 主文档 / 速览 / Python 依赖
├── references/                        # 安全规则、排障与问题处理集（troubleshooting.md 单一来源）、Agent 指南
├── templates/                         # pre/post 迁移检查脚本
└── scripts/windows_migration/         # ★ 迁移引擎
    ├── unified_migrate.py             # 统一入口 CLI（步骤一 Agent 部署；公网/私网、单台/批量）
    ├── sms_task.py                    # SMS 控制面 CLI（步骤二~五：discover/prepare-target/create/start/wait/sync/cutover/cleanup/delete/pipeline）
    ├── preflight_check.py             # 迁移前置环境变量检查
    ├── cleanup_windows.py             # 源端残留清理（任务/进程/目录/注册表；单一来源，幂等）
    ├── cleanup_environment.py         # 环境清理编排（①打通 gost→②清源端→③清代理）
    ├── agent_recover.py               # Agent 官方恢复入口（重建 secrets→重传 exe→重建计划任务→Verify）
    ├── run_migration.sh / run_sms_task.sh   # 运行包装脚本（零硬编码）
    ├── config/                        # migrate.public/private.yaml、env.*.sh.example、hosts.csv.example（占位符，600）
    ├── core/
    │   ├── config.py / callbacks.py / exceptions.py / markers.py / hostinfo.py / ownership.py / obs_signer.py
    │   ├── sms_client.py / target_provider.py / batch_base.py / batch_orchestrator.py / private_batch_orchestrator.py
    │   ├── winrm/                     # detector / keepalive / manager + providers/（huawei/aws/aliyun）
    │   ├── executor/                  # winrm_executor / local_executor / ssh_executor
    │   └── interfaces/                # 抽象接口（executor / cloud_provider / winrm_manager）
    ├── phases/                        # base / winrm / cleanup_source / obs_download / source_download / install_autoit / install_agent / configure / configure_py2 / verify
    ├── scenarios/                     # base / public / private
    ├── proxyopt/                      # 私网跳板机：config/config.yaml + lib/ + scripts/（deploy_jumpbox 等）+ source/Download-Agent.ps1
    ├── scripts/                       # py2/（agent_config.cs/exe）、py3/（exe/au3/gen_secrets）、source_data_disk.py
    └── README.md                      # 引擎详细文档
```

## 两个场景

### 公网迁移（public — 直连模式）

源端 Windows 可直连华为云 OBS。大文件走签名 URL 源端直下，不经沙箱中转。

```
WinRMPhase           直连源端:5985，检测→开启→保活
  → ObsDownloadPhase     大文件: OBS签名URL→源端Invoke-WebRequest直下
                         小文件: WinRM transfer_file
  → InstallAgentPhase    源端静默安装 SMS-Agent
  → [Py3] ConfigurePhase       GUI 自动化配置
         configure_mode=exe    预编译 exe 直传直用（默认，无需 AutoIt，不传 au3）
         configure_mode=autoit 依次尝试 本地exe→目标机编译→au3（需装 AutoIt）
    [Py2] ConfigurePy2Phase    C# AttachConsole + WriteConsoleInput 状态机配置
  → VerifyPhase          日志轮询，5标记检测
```

### 私网迁移（private — 代理模式）

源端 Windows 在内网，通过代理服务器中转。Py3 双模式行为与公网一致：
`configure_mode=exe` 不装 AutoIt、exe 直传；`configure_mode=autoit` 装 AutoIt 后走
编译/au3。详见后文「私网迁移」章节。

### 公网/私网任务创建兼容（仅需改两个参数）

SMS 控制面（`sms_task.py create`）已统一适配公网/私网：**创建任务时只需
`use_public_ip` 与 `migration_ip` 两个参数体现差异**，其余自动推导。

| 模式 | use_public_ip | migration_ip（自动推导） |
|------|---------------|--------------------------|
| 公网 | `true` | = prepare-target 写入的 `eip_address`（目的端 EIP） |
| 私网 | `false` | = prepare-target 写入的 `private_ip`（目的端私有 IP） |

- `migration_ip` 显式指定时优先；留空则自动推导（无需手填）。
- `prepare-target`：私网（`use_public_ip=false`）自动跳过 EIP 创建/绑定；公网按 `use_eip` 决定。
- `target_az` 为**必填**（已移除代码层 `cn-north-4a` 默认，避免在其他区域静默建机）。
- `eip_type` 可配置 EIP 线路类型（默认 `5_bgp`）。

## SMS-Agent 版本支持（Py3 / Py2）

通过 `sms_agent.agent_version` 配置项选择：

| 版本 | 适用系统 | 界面 | 配置方式 | 安装目录 |
|------|---------|------|---------|---------|
| **Py3** (默认) | Win Server 2012/2016/2019/2022/2025, Win 8.1/10/11 | GUI | `configure_sms_agent.exe` 直用（`configure_mode=exe`，默认）或 AutoIt+au3 编译（`configure_mode=autoit`） | `C:\SMS-Agent-Py3` |
| **Py2** | Win Server 2008/Win 7（2003 见兼容矩阵） | CLI | C# `agent_config.exe` AttachConsole 控制台状态机 | `C:\SMS-Agent-Py2` |

> **Py2 agent_config.exe Windows 兼容性矩阵**
>
> | Windows 版本 | 预装 .NET | 部署路径 | 运行 CLR | 状态 |
> |-------------|----------|---------|---------|------|
> | Server 2003 | 1.1 / 2.0 | 源端编译 (v2.0 csc) | CLR 2.0 | ✅ |
> | Server 2008 | 2.0 / 3.0 | 源端编译 (v2.0 csc) | CLR 2.0 | ✅ |
> | Server 2008 R2 / Win 7 | 2.0 / 3.5 | 源端编译 (v2.0 csc) | CLR 2.0 | ✅ |
> | Server 2012 / 2012 R2 | 4.5 / 4.5.1 | 预编译 exe | CLR 4.0 | ✅ |
> | Server 2016 | 4.6.2 | 预编译 exe | CLR 4.0 | ✅ |
> | Server 2019 | 4.7.2 | 预编译 exe | CLR 4.0 | ✅ |
> | Server 2022 | 4.8 | 预编译 exe | CLR 4.0 | ✅ |
>
> Server 2003 为工具层历史兼容，未实测，不建议新迁移。
> | Win 10 / 11 | 4.x | 预编译 exe | CLR 4.0 | ✅ |

### 配置示例

```yaml
# Py3 (默认 — Win Server 2012+)
sms_agent:
  agent_version: "py3"
  configure_mode: "exe"          # exe=纯exe直用(默认) | autoit=AutoIt编译/au3
  agent_exe_name: "SMS-Agent.exe"
  install_dir: "C:\\SMS-Agent-Py3"
  log_file: "C:\\SMS-Agent-Py3\\Logs\\SmsAgent_Info.log"

# Py2 (Win Server 2008/Win7)
sms_agent:
  agent_version: "py2"
  deploy_mode: "precompiled"     # precompiled=预编译exe优先(默认, 失败回退cs编译) | cs=强制源端编译
  agent_exe_name: "agent-start.exe"
  install_dir: "C:\\SMS-Agent-Py2"
  log_file: "C:\\SMS-Agent-Py2\\Logs\\SmsAgent_Info.log"
```

使用 Py2 时，`download.packages.sms_agent`（或 `sms_agent_py2`）的 `obs_uri` 和 `local_name`
需指向 `SMS-Agent-Py2.exe`。两个安装包条目指向同一文件，条目名不影响逻辑。

---

## Py3 配置说明（configure_sms_agent.exe / au3）

Py3 支持两种配置方式，通过 `sms_agent.configure_mode` 选择：

| 模式 | 行为 | AutoIt |
|------|------|--------|
| **`exe`**（默认） | 仅传输并使用预编译 `configure_sms_agent.exe`；**不下载、不安装 AutoIt，也不传 au3** | ❌ 不需要 |
| **`autoit`** | 下载并安装 AutoIt；配置时依次尝试 本地exe → 目标机编译 → au3 兜底 | ✅ 需要 |

脚本位置：`scripts/py3/`（`configure_sms_agent.exe/.au3`、`install_sms_agent.au3`、`compile_au3.au3`）。

### 运行时回退（autoit 模式）

```
本地有 configure_sms_agent.exe → 传到目标机直接用（首选）
  └─ 传输失败 → 重连 WinRM → 目标机用 Aut2Exe 编译 exe（需源端已装 AutoIt）
       └─ 编译失败 → AutoIt3.exe + au3 运行（兜底）
```

### configure_sms_agent.exe / .au3 命令行参数

两个文件接受完全相同的命令行参数（exe 是 au3 的编译产物）：

```
configure_sms_agent.exe <secrets_file> <mode> <proxy_ip> <proxy_port> <log_path> [install_dir]
```

| 位置 | 参数 | 说明 |
|------|------|------|
| 1 | `secrets_file` | base64 编码的密钥文件路径（AK/SK/Domain/EP），读取后自动删除 |
| 2 | `mode` | `direct`（直连）或 `proxy`（代理） |
| 3 | `proxy_ip` | 代理地址（direct 模式传空 `""`） |
| 4 | `proxy_port` | 代理端口（direct 模式传空 `""`） |
| 5 | `log_path` | 日志输出路径 |
| 6 | `install_dir` | 可选，安装目录（默认 `C:\SMS-Agent-Py3`） |

**直连模式示例：**
```bash
C:\auto_agent_opt\configure_sms_agent.exe "C:\auto_agent_opt\.secrets.dat" direct "" "" "C:\auto_agent_opt\configure_log.txt"
```

**代理模式示例：**
```bash
C:\auto_agent_opt\configure_sms_agent.exe "C:\auto_agent_opt\.secrets.dat" proxy "http://192.168.1.100" "3128" "C:\auto_agent_opt\configure_log.txt"
```

**au3 模式示例（回退）：**
```bash
"C:\Program Files (x86)\AutoIt3\AutoIt3.exe" "C:\auto_agent_opt\configure_sms_agent.au3" "C:\auto_agent_opt\.secrets.dat" direct "" "" "C:\auto_agent_opt\configure_log.txt"
```

### secrets 文件格式

`configure_phase.py` 运行时生成 base64 编码的 `key=value` 文本（不经过命令行明文传递）：

```
AK=xxx
SK=xxx
Domain=xxx
EP=xxx
ProxyUser=xxx        # proxy 模式可选
ProxyPass=xxx        # proxy 模式可选
```

可用 `scripts/py3/gen_secrets.py` 手工生成：

```bash
python3 scripts/py3/gen_secrets.py --ak XXX --sk XXX --domain XXX --ep "示例项目" -o /tmp/.secrets.dat
python3 scripts/py3/gen_secrets.py --config config/migrate.yaml -o /tmp/.secrets.dat   # 或从配置读取
```

脚本读取后立即删除该文件，减少敏感数据暴露窗口。

### install_sms_agent.au3 命令行参数

```
AutoIt3.exe install_sms_agent.au3 <installer_path> <install_dir> <log_path>
```

| 位置 | 参数 | 默认值 | 说明 |
|------|------|--------|------|
| 1 | `installer_path` | `C:\SMS-Agent-Py3.exe` | 安装包路径 |
| 2 | `install_dir` | `C:\SMS-Agent-Py3` | 安装目录 |
| 3 | `log_path` | `C:\auto_agent_opt\install_log.txt` | 日志路径 |

所有路径均通过命令行传入，不硬编码。

### compile_au3.au3 命令行参数

```
AutoIt3.exe compile_au3.au3 <aut2exe_path> <in_au3> <out_exe> <done_marker>
```

用 AutoIt 的 `RunWait(@SW_HIDE)` 调用 Aut2Exe，绕过 GUI 程序在 WinRM 非交互会话中挂起的问题。

---

## Py2 方案详解（C# AttachConsole 控制台状态机）

Py2 的 `agent-start.exe` 是交互式命令行程序（依次提示 AK/SK/域名/企业项目索引）。
由于它内部调用子进程（会重置 stdin）、提示时机不定、首次/非首次行为不同，无法用固定延时
喂输入，因此采用 **C# 程序 AttachConsole 附加到其控制台**，按提示文本（日志驱动）精确喂入。

### agent_config.exe 两种部署方式

通过 `sms_agent.deploy_mode` 选择：

| 模式 | 行为 | 适用 |
|------|------|------|
| **`precompiled`**（默认） | 预编译 exe 优先：源端有 CLR 4.0（Server 2012+）且本地有 `scripts/py2/agent_config.exe` → 直传预编译，零编译开销；预编译缺失/传输失败 → 回退源端 csc 编译 | 通用（默认） |
| **`cs`** | 强制源端编译：跳过预编译直传，直接传输 `.cs` + 源端 `csc.exe` 编译 | 需严格匹配源端 CLR 版本/审计场景 |

> 源端编译 `_find_csc()` 按 `v2.0*` → `v3.5` → `v4*` 搜索，产物 CLR 版本与源端已安装运行时
> 天然一致（Server 2008/Win 7；2003 见兼容矩阵）。公网/私网、单台/批量行为一致。
> 预编译 exe 由 `scripts/py2/agent_config.cs` 编译（C# 2.0 兼容），在任意 Windows + .NET 4.0 环境执行一次：
> `csc.exe /target:winexe /out:agent_config.exe agent_config.cs`。

### agent_config.exe 参数化用法

```
agent_config.exe --ak <AK> --sk <SK> --domain <sms_domain> --ep <EP名称> \
  --agent-exe <agent-start.exe路径> --log <configure_log.txt> \
  --agent-log <SmsAgent_Info.log路径> [--cert <cacert.pem路径>]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `--ak` / `--sk` | 是 | 华为云 AK/SK |
| `--domain` | 是 | SMS 域名（如 `sms.cn-north-4.myhuaweicloud.com`） |
| `--ep` | 是 | 企业项目**名称**（支持中文；运行时解析控制台 EP 列表，EXACT + PREFIX 双重匹配找索引号） |
| `--agent-exe` | 是 | agent-start.exe 完整路径 |
| `--log` | 是 | configure_log.txt 路径（C# 状态机内部日志） |
| `--agent-log` | 是 | SmsAgent_Info.log 路径（注册标记来源） |
| `--cert` | 否 | cacert.pem 路径（TLS 证书，不传则不设 REQUESTS_CA_BUNDLE） |

> EP 列表中文长名在控制台会折行，`ParseEPList()` 只取**行首数字**作为真实索引号。
> 中文 EP 名在英文 OS 上 agent 内部无法解析时会回退注册到 `default`（见注意事项）。

### 自恢复（watchdog）与 TLS

- **watchdog**：部署 PowerShell 脚本 + 计划任务（每 3 分钟），在编排器断开后自动重试注册
  （最多 2 次重启），以 SYSTEM 身份运行，无桌面窗口。
- **TLS 证书**：Py2 agent 的 Python 2.7 运行时默认不信任华为云证书；配置阶段自动定位
  `cacert.pem` 复制到 `C:\SMS-Agent-Py2\cert\` 并注入 `REQUESTS_CA_BUNDLE`。
## 源端清理工具（cleanup_windows.py）

重复迁移前清理源端残留（计划任务、Agent 进程、安装目录、工作目录、下载缓存、注册表卸载项与自启动项、SMSAgentDeploy 服务）。
通过 WinRM 远程执行，幂等可重复运行。

```bash
python3 cleanup_windows.py config/migrate.yaml
```

> 各项清理顺序与细节见「使用方法 → 清理源端环境」表。

---

## 使用方法

### 前置条件

| 依赖 | 用途 | 安装 |
|------|------|------|
| Python 3.10+ | 运行环境 | — |
| Python 依赖（winrm/NTLM/SPNEGO/YAML/SSH 等） | 根目录 `requirements.txt`（单一来源） | `pip install -r ../requirements.txt` |
| obsutil | OBS 下载/签名 | [华为云 OBS 工具](https://support.huaweicloud.com/utiltg-obs/obs_11_0001.html) |
| 代理主机 python3 | 代理主机 HTTP 文件服务（`python3 -m http.server`，CentOS7 自带 3.6） | 代理主机预装 |
| yum/apt | 代理主机自动安装 Squid（deploy_jumpbox 步骤 1.4） | 代理主机预装 |
| gost 二进制 | 代理主机 `gost`（deploy 自动从沙箱 `agent_pkgs/gost` 分发，无则报错） | 随私网部署自动处理 |
| AutoIt v3 | 源端 GUI 自动化（仅 Py3） | 运行时自动安装到源端 |

> Py2 模式 **不需要 AutoIt**。源端 .NET Framework 要求：
> - **Server 2012+**：自带 .NET 4.x，预编译 exe 直接运行，无需额外操作。
> - **Server 2008/Win7（及 2003 历史环境）**：预装 .NET 2.0/3.5（无 4.0），自动回退到源端编译路径，
>   用源端自带的 v2.0 `csc.exe` 编译 `agent_config.cs`（C# 2.0 兼容），无需手动安装 .NET 4.0。
> - **极端情况**（源端完全无 .NET Framework）：需手动安装任意版本 .NET（2.0+ 即可）。

### 快速开始

#### 1. 编辑配置

```bash
cd scripts/windows_migration   # 从包根进入引擎目录
vim config/migrate.yaml          # 填写源端 IP、AK/SK、OBS 等配置
```

关键字段：

```yaml
source:
  host: "192.168.1.100"        # 源端 Windows IP
  username: "Administrator"
  password: "<源端密码>"
  winrm_port: 5985

sms_agent:
  agent_version: "py3"           # py2 = 命令行界面, py3 = 图形界面
  enterprise_project: "Example_Project(示例项目)"  # EP 名称（C# 运行时解析索引）
  ak: "<目标端 AK>"
  sk: "<目标端 SK>"
  domain_id: "sms.cn-north-4.myhuaweicloud.com"

obs:
  endpoint: "obs.cn-north-1.myhuaweicloud.com"
  ak: "<OBS AK>"
  sk: "<OBS SK>"
  bucket: "<OBS 桶名>"
```

> 仓库中的 `config/migrate.yaml` 是**占位符模板**，不含真实凭据。所有 `<>` 占位符
> 使用前必须替换。**不要在配置文件中提交真实 AK/SK 到 Git。**

#### 2. 清理源端环境（每次迁移前必须先执行）

> **⚠️ 重要：操作顺序是先清理、再迁移。**
>
> 每次运行迁移之前，都必须先执行清理脚本，清除源端上一次迁移残留的 Agent 进程、
> 安装目录、计划任务、注册表项等。如果不清理，残留的 `sms_domain.txt` 会导致
> C# 状态机交互错位（agent 问 "use last time?" 而非直接要 domain），
> 残留的计划任务和进程会干扰新一轮注册，最终导致迁移失败。
>
> 清理脚本通过 WinRM 远程执行，源端无需预装任何东西，沙箱侧运行 Python 即可。
> 清理是幂等的——即使源端已经是干净状态，运行也不会报错。

```bash
python3 cleanup_windows.py config/migrate.yaml
```

清理内容（按顺序）：

| 步骤 | 清理项 | 说明 |
|------|--------|------|
| 1 | 计划任务 | 删除 `ConfigureSMSAgent` / `ConfigureSMSAgentPy2` / `SMSAgentWatchdog` |
| 2 | Agent 进程 | 杀 `agent-start.exe` / `SMSAgentDeploy.exe` / 残留 `cmd.exe` |
| 3 | 安装目录 | 删除 `C:\SMS-Agent-Py2`（或 Py3） |
| 4 | 工作目录 | 删除 `C:\auto_agent_opt` |
| 5 | 注册表 | 清理卸载项、Run/RunOnce 自启动、SMSAgentDeploy 服务 |
| 6 | 验证 | 确认安装目录、工作目录、注册表均已清除 |

#### 3. 执行单台迁移

```bash
# Py2（命令行界面，Win Server 2008/Win7）
python3 unified_migrate.py --scenario public --config config/migrate.yaml

# Py3（图形界面，Win Server 2012+）
# 先在 config/migrate.yaml 中设 agent_version: "py3"
python3 unified_migrate.py --scenario public --config config/migrate.yaml
```

#### 4. 批量迁移（100台，10并发）

```bash
# 编辑主机列表
vim config/hosts.csv

# 批量迁移
python3 unified_migrate.py --scenario public --batch config/hosts.csv --workers 10

# 幂等重跑（已成功的主机自动跳过）
python3 unified_migrate.py --scenario public --batch config/hosts.csv --workers 10
```

#### 5. 私网迁移（文件服务器部署在代理主机）

```bash
# 跳板机一键就绪（可选；Phase1 默认会自动执行同一逻辑）
python3 proxyopt/scripts/deploy_jumpbox.py --config config/migrate.yaml

# 执行私网迁移（proxyopt.skip=false 时 Phase1 自动部署跳板机）
python3 unified_migrate.py --scenario private --config config/migrate.yaml
```

#### 6. 后台运行 + 日志监控（长时间任务）

```bash
# 后台运行
nohup python3 unified_migrate.py --scenario public --config config/migrate.yaml \
  > /tmp/migrate.log 2>&1 &

# 监控进度
tail -f /tmp/migrate.log
```

### 退出码

| 码 | 含义 |
|----|------|
| `0` | 成功 |
| `1` | 失败 |
| `2` | 配置错误 |
| `130` | 用户中断 |

## 验证机制

注册成功通过轮询 `SmsAgent_Info.log` 检测 5 个标记（子串匹配，非正则）：

| 标记 | 子串 | 含义 |
|------|------|------|
| `[0]` | `as/sk` | AK/SK 验证通过 |
| `[1]` | `upload os info` | OS 信息上传成功 |
| `[2]` | `upload source info` | 源端信息上传成功 |
| `[3]` | `schedule task` | 定时任务启动 |
| `[4]` | `heart beat` | 心跳启动 |

判定规则：标记 ≥ 3 → **成功**，标记 < 3 → **失败**。

Py2 和 Py3 使用同一套标记，但 Py2 agent 日志中的文本与 Py3 略有不同，所以用子串匹配
而非固定正则。`configure_py2_phase.py` 的 `_check_registration()` 与 `verify_phase.py`
的 `_check_markers()` 保持一致。

---

## CLI 完整参数

```bash
python3 unified_migrate.py --scenario <public|private> [OPTIONS]
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--scenario` | `public` \| `private` | ✅ | — | 迁移场景 |
| `--config` | path | ❌ | `config/migrate.yaml` | 配置文件路径 |
| `--batch` | path | ❌ | — | 批量主机列表 CSV，指定后启用批量模式 |
| `--workers` | int | ❌ | 配置 `batch.max_workers` | 批量并发线程数 |
| `--json` | flag | ❌ | false | 输出 JSON 到 stdout，日志仅写文件 |
| `--callback` | path | ❌ | — | 回调脚本路径（自定义实现 `build_callbacks()` 的 Python 文件，包内未内置示例） |

---

## 配置文件完整字段

### sms_agent — SMS-Agent 参数

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `agent_version` | str | `py3` | `py3`=GUI, `py2`=CLI+C# 状态机 |
| `configure_mode` | str | `exe` | Py3 配置方式: `exe`=纯exe直用（默认，无需AutoIt）, `autoit`=AutoIt编译/au3 |
| `deploy_mode` | str | `precompiled` | Py2 部署方式: `precompiled`=预编译exe优先（默认，缺失/失败回退cs编译）, `cs`=强制源端csc编译 |
| `agent_exe_name` | str | `SMS-Agent.exe` | py3=`SMS-Agent.exe`, py2=`agent-start.exe` |
| `ak` | str | — | 目标端 AK |
| `sk` | str | — | 目标端 SK |
| `domain_id` | str | — | SMS 域名（如 `sms.cn-north-4.myhuaweicloud.com`） |
| `domain_name` | str | — | SMS 域名（备用字段，通常与 `domain_id` 相同） |
| `enterprise_project` | str | `0` | 企业项目**名称**（C# 运行时解析为索引号） |
| `region` | str | — | 目标区域 |
| `install_dir` | str | — | Agent 安装目录 |
| `log_file` | str | — | SmsAgent_Info.log 路径 |
| `error_log_file` | str | — | SmsAgent_Error.log 路径 |
| `proxy_mode` | bool | false | 是否走代理 |
| `proxy_host` | str | — | 代理地址 |
| `proxy_port` | int | 3128 | 代理端口 |
| `silent_install_args` | str | `/S` | 静默安装参数 |

### source — 源端主机

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `host` | str | — | 源端 Windows IP |
| `username` | str | — | WinRM 用户名 |
| `password` | str | — | WinRM 密码 |
| `winrm_port` | int | 5985 | WinRM 端口 |
| `winrm_transport` | str | `ntlm` | 认证方式 |
| `winrm_use_ssl` | bool | `false` | 是否使用 HTTPS (WinRM 5986) |
| `cloud_provider` | str | `none` | 云厂商 |
| `os_arch` | str | `x64` | 源端架构 |

### obs — OBS 下载通道

| 字段 | 类型 | 说明 |
|------|------|------|
| `endpoint` | str | OBS endpoint |
| `ak` | str | Access Key |
| `sk` | str | Secret Key |
| `bucket` | str | 桶名 |
| `region` | str | 区域 |
| `obsutil_path` | str | obsutil 路径 |

### download.packages — 安装包定义

```yaml
download:
  packages:
    sms_agent:        # 当前版本选择的安装包（py3/py2 二选一指向对应 exe）
      obs_uri: "obs://bucket/path/SMS-Agent-Py3.exe"
      local_name: "SMS-Agent-Py3.exe"
    sms_agent_py2:    # Py2 专用（与 sms_agent 同源，条目名不影响逻辑）
      obs_uri: "obs://bucket/path/SMS-Agent-Py2.exe"
      local_name: "SMS-Agent-Py2.exe"
    autoit:           # Py3 专用
      obs_uri: "obs://bucket/path/autoit-v3-setup.zip"
      local_name: "autoit-v3-setup.zip"
```

### 私网关键配置段（文件服务器部署在代理主机）

`proxy_server` — 代理主机（Squid/gost/HTTP/文件服务均部署于此）：

```yaml
proxy_server:
  host: "203.0.113.10"       # 代理主机公网 IP（沙箱 SSH 管理入口）
  ssh_port: 22
  ssh_username: "root"
  ssh_password: "<代理主机密码>"
  squid_port: 3128           # Squid 正向代理（SMS-Agent 出口 + 文件缓存）
  gost_listen_port: 15985    # gost WinRM 转发监听（→ source.host:winrm_port）
  http_server_port: 8080     # 文件服务端口（serve /data/downloads，源端同网段可达）

sandbox_host: "10.0.1.75"    # 源端视角的文件服务地址（代理主机内网 IP；留空则用 proxy_server.host）
```

`proxyopt` — 私网分发配置：

```yaml
proxyopt:
  base_dir: "/path/to/huawei-cloud-migration-windows-ecs/scripts/windows_migration/proxyopt"
  config_file: "/path/to/huawei-cloud-migration-windows-ecs/scripts/windows_migration/proxyopt/config/config.yaml"
  skip: false                # false=Phase1 自动部署跳板机（默认）；true=跳板机已手动就绪，跳过 Phase1
```

> 运行时由 `deploy_jumpbox._proxyopt_config_path()` 从 migrate.yaml 注入 OBS 桶、
> `sandbox.precache_host`（=sandbox_host）、`gost.forward_rules`（15985→源端:5985）等，
> `proxyopt/config/config.yaml` 不再硬编码任何 IP。

### 顶层字段与其他配置段

| 字段/段 | 说明 |
|---------|------|
| `scenario` | `public`=公网直连 \| `private`=私网代理（默认 `public`） |
| `sandbox_host` | 源端视角的文件服务地址（私网专用；通常为代理主机内网 IP，留空则用 `proxy_server.host`） |
| `source_base_dir` | 源端工作根目录（默认 `C:\auto_agent_opt`，所有迁移文件基础路径） |
| `batch` | 批量配置（CSV 路径、并发数、状态文件） |
| `winrm_keepalive` | WinRM 心跳保活（间隔、最大失败数、自动重连） |
| `timeout` | 各阶段超时（秒） |
| `retry_policy` | 各阶段重试策略（次数、退避、可重试错误模式） |
| `logging` | 日志级别、目录、文件名 |
| `autoit` | AutoIt 配置（Py3 专用） |

---

## 批量迁移

```
沙箱 (1台)                        源端 (N台)
┌──────────────────┐             ┌──────────────────┐
│ BatchOrchestrator │──WinRM──→  │ host-001 下载+安装+配置 │
│ ThreadPool(N=10)  │──WinRM──→  │ host-002 下载+安装+配置 │
│ 1个签名URL复用    │──WinRM──→  │ host-003 下载+安装+配置 │
└──────────────────┘             └──────────────────┘
```

- **1 个签名 URL，N 台复用** — 沙箱生成一次，100 台各自从 OBS 直下
- **线程池并发** — `ThreadPoolExecutor(max_workers=10)`
- **幂等重跑** — 状态持久化 `batch_state.json`，已成功主机自动跳过

### hosts.csv 格式

```csv
host,username,password,winrm_port
192.168.1.100,Administrator,<密码>,5985
192.168.1.101,Administrator,<密码>,5985
```

### 私网批量（private + --batch）

私网批量走 `PrivateBatchOrchestrator`：经代理主机 gost **多端口转发**
（每台源端分配 `gost_listen_port + i`），源端安装包经 Squid 从代理主机 HTTP 下载。

```bash
# Phase1 自动部署跳板机（proxyopt.skip=false）并并发迁移
python3 unified_migrate.py --scenario private --batch config/hosts.csv --workers 10

# 已手动就绪时跳过 Phase1
python3 unified_migrate.py --scenario private --batch config/hosts.csv --workers 10
# （此时 migrate.yaml 中 proxyopt.skip: true）
```

> 私网批量状态文件为 `batch_state_private.json`；`PrivateBatchOrchestrator` 在
> `proxyopt.skip=false` 时自动在代理主机拉起 gost 多端口转发，`skip=true` 时假设已手动配置。

---

## 私网迁移（private — 代理模式）

> **架构（2026-09 调整）**：私网文件服务器**部署在代理主机**（`/data/downloads`，
> HTTP 8080），源端同网段/经 Squid 直达，**不依赖沙箱入站**。Phase1 由
> `deploy_jumpbox.py` 一键完成，全部步骤幂等可重复执行。
> 私网任务创建与公网仅差两个参数：`use_public_ip: false` + `migration_ip` 留空
> （create 自动取目的端私有 IP）；`prepare-target` 私网时不会创建 EIP。

```
Phase 1: 跳板机一键就绪（deploy_jumpbox.deploy，自动/手动均可）
  1.1 沙箱     OBS 下载安装包           → proxyopt/downloads/
  1.2 代理主机 同步文件                 → /data/downloads（download.packages.sms_agent 指向的安装包，Py2/Py3 均可；configure_sms_agent.exe 仅 Py3 同步）
  1.3 代理主机 HTTP 8080 文件服务       → 源端同网段直达，不依赖沙箱入站
  1.4 代理主机 Squid 3128               → 热加载部署（默认仅放行 RFC1918 内网；规避 CentOS7 systemctl restart 阻塞）
  1.5 代理主机 gost 15985→源端:5985     → systemd 托管（重启自动恢复）
  1.6 沙箱     preCache 经 Squid 抓代理主机 8080（404 自动跳过）

Phase 2: Agent 部署配置（经 gost 连接源端）
  2.1  WinRMPhase          经 gost 转发 代理:15985→源端:5985
  2.2  源端下载安装包       WinRM 触发 Download-Agent.ps1，经 Squid 代理从代理主机 HTTP 下载（-DownloadDir 由配置传入，默认 C:\auto_agent_opt\downloads）
  2.3  InstallAgentPhase   静默安装（[Py3] 前有 InstallAutoItPhase）
  2.4  ConfigurePhase/ConfigurePy2Phase  配置（proxy 模式；Py3 exe 优先经 HTTP 秒级分发）
  2.5  VerifyPhase         日志轮询
```

**自动执行**（默认 `proxyopt.skip: false`，Phase1 自动部署）：

```bash
python3 unified_migrate.py --scenario private --config config/migrate.yaml
```

**手动就绪**（跳板机已部署，跳过 Phase1）：

```bash
python3 proxyopt/scripts/deploy_jumpbox.py --config config/migrate.yaml   # 一键就绪
# 确认无误后，将 migrate.yaml 中 proxyopt.skip 置为 true 再执行迁移
python3 unified_migrate.py --scenario private --config config/migrate.yaml
```

> `deploy_jumpbox.py` 同时是 private_scenario Phase1 的部署引擎；支持
> `--skip-upload`（仅检查文件同步）、`--verify-only`（仅验证端口与回源链路）。

---

## 源端文件布局

迁移过程中在源端 Windows 上创建的文件：

### Py3

```
C:\MigrationAgent\
  └── SMS-Agent-Py3.exe          # 下载的安装包

C:\SMS-Agent-Py3\                # 安装目录
  ├── SMS-Agent.exe              # Agent 主程序
  └── Logs\
      ├── SmsAgent_Info.log      # 信息日志（验证标记来源）
      └── SmsAgent_Error.log     # 错误日志

C:\auto_agent_opt\               # 工作目录
  ├── configure_sms_agent.exe    # 预编译配置程序（exe 模式，首选）
  ├── configure_sms_agent.au3    # AutoIt 配置脚本（au3 模式）
  ├── .secrets.dat               # base64 敏感参数文件（读取后删除）
  ├── run_configure.bat          # schtasks 启动脚本
  ├── configure_log.txt          # 配置日志（CONFIG_COMPLETE 完成标记）
  └── [compile_au3.au3 / compile.bat]   # 目标机编译临时文件
```

### Py2

```
C:\MigrationAgent\
  └── SMS-Agent-Py2.exe          # 下载的安装包

C:\SMS-Agent-Py2\                # 安装目录
  ├── agent-start.exe            # Agent 主程序
  ├── config\
  │   └── error.cfg              # 错误配置
  ├── cert\
  │   └── cacert.pem             # TLS 证书（从 Cloudbase-Init 复制）
  └── Logs\
      ├── SmsAgent_Info.log      # 信息日志（验证标记来源）
      └── SmsAgent_Error.log     # 错误日志

C:\auto_agent_opt\               # 工作目录
  ├── agent_config.exe           # 预编译参数化 exe（winexe, 命令行参数驱动）
  ├── configure_log.txt          # C# 状态机内部日志（Attached/DONE/State 转换）
  ├── watchdog.ps1               # 自恢复脚本
  └── watchdog.log               # watchdog 运行日志
```

### configure_log.txt（Py2 状态机内部日志）

记录 agent_config.exe 每一步动作：`Attached to best PID`（成功附加）、`State X->Y`（状态流转）、
`ParseEPList`（EP 匹配结果）、`markers=5/5`（注册标记）、`===== DONE =====`（完成）。

---

## Python API

### 单台迁移

```python
from core.config import ConfigLoader
from scenarios.public_scenario import PublicScenario

config = ConfigLoader.load("config/migrate.yaml")
scenario = PublicScenario(config)
result = scenario.run()

if result.success:
    print(f"成功，耗时 {result.total_duration:.1f}s")
else:
    print(result.summary())
```

### 批量迁移

```python
from core.config import ConfigLoader
from core.batch_orchestrator import BatchOrchestrator

config = ConfigLoader.load("config/migrate.yaml")
orchestrator = BatchOrchestrator(
    config=config,
    hosts_csv="config/hosts.csv",
    max_workers=10,
)
result = orchestrator.run()
print(result.summary())
```

### JSON 输出（CLI）

```bash
python3 unified_migrate.py --scenario public --config config/migrate.yaml --json
```

```json
{
  "exit_code": 0,
  "mode": "single",
  "scenario": "公网迁移(直连模式)",
  "success": true,
  "total_duration": 82.3,
  "phases": [
    {"name": "WinRMPhase", "status": "success", "duration": 0.3, "detail": "", "error": ""},
    {"name": "ConfigurePy2Phase", "status": "success", "duration": 69.0, "detail": "markers 5/5", "error": ""}
  ]
}
```

---

## 异常层级

```
MigrationError              # 基类
├── ConfigError             # 配置加载/校验失败（不可重试）
├── WinRMError              # WinRM 连接/认证/执行失败
├── DownloadError           # OBS/HTTP 下载失败
├── InstallError            # 安装失败
├── ConfigureError          # 配置失败
└── VerifyError             # 注册验证失败
```

---

## 设计原则

1. **零硬编码** — 所有参数通过 `config/migrate.yaml` 注入
2. **日志驱动** — C# 状态机所有状态转移通过轮询控制台缓冲区/日志文本触发，非固定延时
3. **自恢复** — watchdog 在编排器断开后仍能自动恢复注册失败（max 2 次重启）
4. **幂等重跑** — 批量模式状态持久化，重复迁移先清理再跑
5. **沙箱零带宽** — 公网场景大文件走 OBS 签名 URL 源端直下；私网场景文件服务部署在代理主机（/data/downloads + HTTP 8080），源端经 Squid 缓存下载，沙箱不经手大文件传输
6. **预编译参数化 exe** — `agent_config.exe`（Py2）与 `configure_sms_agent.exe`（Py3）编译一次即可复用，AK/SK/Domain/EP 等通过命令行参数动态注入

---

## 注意事项（已知限制）

1. **英文 OS + 中文企业项目名（Py2）→ 自动注册到 default**
   SMS-Agent（Python 2 内部）在英文 Windows 上无法解析 API 返回的中文 EP 名，会跳过
   EP 选择并注册到 `default`。工具层面无法修复：注册后请在控制台/SMS API 手动调整
   企业项目归属，或改用 Py3 方案。（`agent_config.cs` 已做缓解：非中文 OS 遇中文 EP 名时
   主动预置 `default` 并记录日志，避免状态机错乱。）

2. **迁移前必须先执行清理**
   残留的 `sms_domain.txt` 会让 Py2 交互错位（agent 问 "use last time?"），残留进程/
   计划任务会干扰新注册。每次迁移前先运行 `python3 cleanup_windows.py config/migrate.yaml`。

> Py3 的 AutoIt 依赖、沙箱运行依赖等见上文对应章节，此处不再重复。

---
## SMS 控制面编排（步骤二~五）

## 功能定位

步骤一（源端部署 Agent）由既有 `unified_migrate.py` 完成；本新增模块负责 **SMS 控制面**（创建迁移任务、启动全量复制、监控、同步、割接、清理资源），即官方最佳实践「创建Windows主机迁移任务」的步骤二~五。

## 新增文件

| 文件 | 职责 | 对应既有模式 |
|------|------|------|
| `core/sms_client.py` | hcloud CLI 包装（AK/SK 经环境变量注入，不落盘；project_id 自动发现） | `core/obs_signer.py` |
| `core/target_provider.py` | 目标端基础设施编排（VPC/子网/安全组/镜像/规格/ECS/EIP） | — |
| `sms_task.py` | SMS 控制面 CLI：discover/ecs-list/templates/prepare-target/create/start/status/wait/sync/cutover/cleanup/delete/pipeline | `unified_migrate.py` |
| `run_sms_task.sh` | 薄包装（无凭据，可编排） | `run_migration.sh` |
| `config/target_state.json` | prepare-target 运行时产物（勿提交版本库），create 自动读取 | `batch_state.json` |

## 使用（Windows / 已有服务器模式优先）

```bash
# 步骤二前：发现源端 / 目的端候选（只读）
./run_sms_task.sh discover
./run_sms_task.sh ecs-list
./run_sms_task.sh templates

# 目标端自动创建（VPC/子网/安全组最小权限/ECS/EIP）
./run_sms_task.sh prepare-target --dry-run --json   # 只出计划
./run_sms_task.sh prepare-target --yes              # 实际创建（生产变更）

# 步骤二：创建迁移任务（幂等保护 + 磁盘映射校验）
./run_sms_task.sh create --yes

# 步骤三：全量复制 + 监控
./run_sms_task.sh start --yes
./run_sms_task.sh wait --target-state SYNCING --timeout 14400

# 步骤四：增量同步 / 启动目的端（割接）
./run_sms_task.sh sync --yes
./run_sms_task.sh cutover --yes

# 步骤五：清理快照资源（不可逆）
./run_sms_task.sh cleanup --yes

# 可编排一条链
./run_sms_task.sh pipeline --steps discover,create,start,wait --yes
```

退出码与 `unified_migrate.py` 一致：`0` 成功 / `1` 失败 / `2` 配置错误。所有变更操作需 `--yes` 或交互确认。

## 配置（migrate.yaml `sms_task:` 段要点）

- `target_mode: existing | new`：已有服务器 / 创建新服务器；**已有服务器优先**（目标 ECS 由 `prepare-target` 自动创建）
- `target_vm_id`：目的端 ECS ID（prepare-target 自动写入 target_state.json，create 自动读取；显式指定优先）
- `use_public_ip + migration_ip`：**公网/私网唯一差异**。`migration_ip` 留空自动推导——公网取 `eip_address`、私网取 `private_ip`（均来自 prepare-target 写入的 target_state.json；显式指定优先）
- `target_az`：**必填**可用区（已移除代码层默认）；`target_mode` 默认 `existing`（已有服务器优先）
- `eip_type`：EIP 线路类型（默认 `5_bgp` 动态BGP）
- `sg_source_cidrs`：**安全红线**，仅放行最小来源；代码硬校验任何 `0.0.0.0/0` 直接拒绝
- `sg_ports`：默认 `22,8899,8900`（SMS 迁移端口）
- `eip_id`：指定复用 EIP；为空则优先空闲未绑定（status=DOWN），无则创建
- `target_flavor_id / target_image_id`：空则按源端上报规格/镜像版本自动匹配（排除 ARM 规格）
- `source_server_id`：账号内有多个源端时必须显式指定

## 磁盘映射规则（防 SMS.0515 底线）

1. 磁盘数必须 1:1（系统盘↔系统盘、数据盘↔数据盘），不匹配直接拒绝创建
2. 磁盘块取自源端 `init_target_server.disks`（SMS 归一化建议形态）
3. 必须带 `physical_volumes`（含 `uuid`），否则运行期 SMS.0515
4. `uuid` 用源端装饰格式 `\\?\Volume{...}\`，KooCLI 传参需**反斜杠翻倍**（见 `../../references/troubleshooting.md` 2.1/2.2）

## 正式示例：创建迁移任务（含 SMS.0515 注释）

> **示例说明**：以下资源 ID/IP 均为匿名示例值，非真实租户资源；使用时替换为实际 ID。

> 以下为**本次实测跑通**的完整示例：Windows Server 2022 / 单系统盘 / 已有服务器模式 / 持续同步。
> 照此填配置即可复用；重点看**磁盘块**注释，这是 SMS.0515 的高发区。

### 场景

| 项 | 值 |
|---|---|
| 源端 | `windows-demo`，source_server_id=`890b2a87-f72e-4414-a539-d3baebadd71b`（WINDOWS2022_64BIT，单盘 40GB，2 个物理卷） |
| 目的端 | ECS `adf0951f-dcbb-46ab-b904-26a9c7e0b407`，系统卷 `86cd0cc3-e4c3-41fe-a619-fdc85074afbb`（40GB） |
| EIP | `1.2.3.4`（公网迁移） |
| 模式 | `existing`（已有服务器）；**默认 `syncing=false` + `is_need_consistency_check=true` → 7 子任务完整工作流** |

### 配置（config/migrate.yaml 的 sms_task 段）

```yaml
sms_task:
  region: "cn-north-4"
  os_type: "WINDOWS"
  migration_type: "MIGRATE_BLOCK"
  task_name: "migrate_win_demo"     # ⚠️ 用短规范名，长名易触发 SMS.7711
  target_mode: "existing"               # existing=已有服务器（优先）
  target_vm_id: "adf0951f-dcbb-46ab-b904-26a9c7e0b407"   # prepare-target 或手动填
  migration_ip: "1.2.3.4"        # 目的端 EIP（公网迁移必填）
  use_public_ip: true
  source_server_id: "890b2a87-f72e-4414-a539-d3baebadd71b"  # 账号内多源端时必须显式指定
  auto_start: false                     # 先创建再人工确认 start
  syncing: false                        # 默认 False → 完整 6 子任务工作流（推荐）
  is_need_consistency_check: true           # 开启 → 第 7 子任务 CHECK_CONSISTENCY；最终 7 子任务
  sg_source_cidrs: ["198.51.100.10/32"]   # 【红线】仅源端 IP，禁止 0.0.0.0/0
  sg_ports: [22, 8899, 8900]
  eip_id: "93f650ac-32ac-462f-a7bb-191b0f91dced"   # 优先复用指定 EIP
```

### 创建命令

```bash
./run_sms_task.sh create --yes --json
# 期望输出含 task_id、磁盘映射摘要；磁盘数不匹配会直接拒绝（防 0515）
./run_sms_task.sh start --yes --json      # 确认无误后再复制
./run_sms_task.sh wait --target-state SYNCING --timeout 14400
```

### 内部实际提交的 target_server 磁盘结构（v3/tasks 语义）

```jsonc
"target_server": {
  "vm_id": "adf0951f-dcbb-46ab-b904-26a9c7e0b407",
  "name": "migrate-ecs-windows-demo-20260920092956",
  "disks": [{
    "name": "Disk 0",                     // 源端磁盘名
    "disk_id": "86cd0cc3-e4c3-41fe-a619-fdc85074afbb", // ← 目的端 EVS 系统卷 ID（系统盘对系统盘）
    "size": 42949672960,                  // 字节（40GB）
    "used_size": 42947575808,             // 字节，取自 init_target_server
    "device_use": "OS",                   // ⚠️ 用 init_target_server 归一化值 OS，不要写 BOOT
    "physical_volumes": [                 // ⚠️⚠️ SMS.0515 高发区：必须带，不能省
      {
        "name": "(Reserved)",
        "device_use": "BOOT",
        "size": 104857600,                // 字节
        "used_size": 30396416,
        "file_system": "NTFS",
        "index": 1,
        "uuid": "\\?\\Volume{7f936e68-0000-0000-0000-100000000000}\\"  // 见下方"反斜杠翻倍"注释
      },
      {
        "name": "C:\\",                  // 盘符带反斜杠，同样要翻倍
        "device_use": "OS",
        "size": 42842718208,
        "used_size": 16860303360,
        "file_system": "NTFS",
        "index": 2,
        "uuid": "\\?\\Volume{7f936e68-0000-0000-0000-500600000000}\\"
      }
    ]
  }]
}
```

**传入 hcloud 时（KooCLI 反斜杠转义）**：上述 `uuid` 在命令行里必须写成
`--target_server.disks.1.physical_volumes.1.uuid='\\\\?\\Volume{7f936e68-0000-0000-0000-100000000000}\\\\'`
即**每个反斜杠翻倍**。CLI（`sms_task.py`）的 `_escape_hcloud` 已自动处理；直连 hcloud 时必须自己翻倍，否则 **SMS.9001**。

### SMS.0515 排障速查（务必先看）

> 磁盘物理卷问题（0515/9001/6033/7711）完整问题→修复统一归档于 [`../../references/troubleshooting.md`](../../references/troubleshooting.md) 2.1~2.4；此处只保留配置要点：
> - `target_server.disks[].physical_volumes` 必须完整携带（uuid 用源端装饰格式、KooCLI 传参反斜杠翻倍）；
> - 磁盘数 1:1（系统盘↔系统盘、数据盘↔数据盘），不匹配拒绝创建；
> - 失败时读源端 `C:\SMS-Agent-Py3\Logs\SmsAgent_Info.log` 尾部确认 `target_vols_map` 是否为空。

---
## 问题处理集

> 全部“问题 → 修复”与排障步骤统一归档至 [`../../references/troubleshooting.md`](../../references/troubleshooting.md)（单一来源），此处不再重复记录。

## 环境清理编排（cleanup_environment.py）

清理范围：**源端主机 + 代理主机**。顺序由网络依赖决定：

```
① 打通网络：确保代理 gost WinRM 映射就绪（private 必做；不存在则自动部署）
② 清理源端：WinRM 经 gost 清迁移残留（复用 cleanup_windows 命令清单，单一来源）
③ 清理代理：停 gost/Squid/HTTP 8080、删 /data/downloads 部署产物（幂等，不卸载系统包）
```

```bash
python3 cleanup_environment.py --config config/migrate.yaml          # 交互确认
python3 cleanup_environment.py --config config/migrate.yaml --yes    # 免确认
python3 cleanup_environment.py --config ... --skip-source            # 只清代理
python3 cleanup_environment.py --config ... --skip-proxy             # 只清源端
```

> 为什么先打通网络再清源端：私网下清源端必须经 gost → WinRM(15985→source:5985)。
> 旧流程（run_migration.sh 先清理再迁移）在私网下因 gost 未建立而必然失败，本编排修正该顺序。
> 破坏性说明：②会删除源端 SMS-Agent 安装目录/注册表；③会停止代理上的 Squid/gost 服务并删部署产物。
