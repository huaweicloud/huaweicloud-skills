---
name: huawei-cloud-migration-windows-ecs
description: |
  华为云 SMS（Server Migration Service）Windows 主机迁移到 ECS 的自动化编排 Skill。
  支持 Windows Server 2008/2008R2/2012/2012R2/2016/2019/2022/2025 及 Win7/8.1/10/11（64位）。
  公网/私网迁移模板与环境变量模板 + 前置任务提醒（未设置 Host_Information/migration_* 时
  明确提示客户先配置环境变量再迁移）；双 CLI（unified_migrate.py 部署 Agent + sms_task.py 目标/迁移任务/同步/割接）+ 环境清理编排：
  KooCLI 7.2.x 实测兼容（BatchStartServers 等效割接、EVS 磁盘校验 fallback、sync/cutover 枚举不支持自动回退）、
  批量迁移主机信息从环境变量 Host_Information（JSON 模板）读取（原 CSV 兼容回退）、
  部署前必清源端（CleanupSourcePhase）、cleanup_environment.py（先打通 gost 再清源端/代理）、
  私网 Squid/gost 代理（CONNECT 仅迁移端口）、资源属主体系（OwnerID 指纹）、71+ 安全规则（含红线 O1-O6）、
  目标编排自动创建数据盘（1:1）、任务名 ≤16 防 SMS.7711。
  触发词：Windows迁移、SMS迁移、迁移Windows服务器、Windows to ECS、migrate Windows、
  Windows server migration、批量迁移、公网迁移、私网迁移、创建目标虚拟机、创建迁移任务、host-migration、清理环境
---

# Huawei Cloud SMS Windows 主机迁移 Skill

## 基本信息

| 项目 | 内容 |
|------|------|
| **name** | `huawei-cloud-migration-windows-ecs` |
| **description** | 华为云 SMS（Server Migration Service）Windows 主机迁移到 ECS 的自动化编排 Skill。支持 Windows Server 2008/2008R2/2012/2012R2/2016/2019/2022/2025 及 Win7/8.1/10/11（64位）。公网/私网迁移模板与环境变量模板 + 前置任务提醒（未设置 `Host_Information`/`migration_*` 时先配置环境变量再迁移）；双 CLI（`unified_migrate.py` 部署 Agent + `sms_task.py` 目标/迁移任务/同步/割接）+ 环境清理编排（`cleanup_environment.py`）；KooCLI 7.2.x 实测兼容（BatchStartServers 等效割接、EVS 磁盘校验 fallback、sync/cutover 枚举不支持时自动回退）；批量主机信息从环境变量 `Host_Information`（JSON 模板）读取（CSV 兼容回退）；部署前必清源端（CleanupSourcePhase）；私网 Squid/gost 代理（CONNECT 仅迁移端口）；资源属主体系（OwnerID 指纹）；71+ 安全规则（含红线 O1-O6）；目标编排自动创建数据盘（1:1）；任务名 ≤16 防 SMS.7711。触发词：Windows迁移、SMS迁移、迁移Windows服务器、Windows to ECS、migrate Windows、Windows server migration、批量迁移、公网迁移、私网迁移、创建目标虚拟机、创建迁移任务、host-migration、清理环境 |

## 迁移基本逻辑

```
Phase A: unified_migrate.py — 清理 + 部署 Agent 并注册源端
  阶段链: WinRMPhase → CleanupSourcePhase(清残留) → InstallAgentPhase → ConfigurePhase → VerifyPhase
Phase B: sms_task.py — 目标编排 → 迁移任务 → 同步 → 割接 → 回收
  子命令: discover / prepare-target / create / start / wait / sync / cutover / cleanup / release / delete
环境清理: cleanup_environment.py — ①打通 gost → ②清源端 → ③清代理
```

- **迁移前必做源端清理**：引擎已固化 `CleanupSourcePhase`（先建 WinRM，私网经 gost，再清残留，最后全新部署 Agent）。
- **Py3 GUI 配置必须在交互会话**：计划任务带 `/it`；无桌面会话（explorer/Session>0）直接快速失败。
- 主机信息不再来自 Excel；批量模式从环境变量 `Host_Information` 读取（见下）。

## 源端关键约束

| 约束项 | 要求 |
|--------|------|
| 文件系统 / 磁盘 | **NTFS、基本磁盘**；≤23 块；系统卷必须在磁盘 1 |
| 分区空间 | 分区>600MB→可用≥320MB；<600MB→可用≥40MB |
| CPU / 内存 | CPU<80%；内存>256MB（迁移期间） |
| Agent 版本 | Server 2012+ → **Py3 GUI**（AutoIt/exe 自动化）；2008/2008R2/7 → **Py2 CLI** |
| 禁止 | RAID / BitLocker / 动态磁盘 / 共享文件系统 / ZRAM / AD / 多节点数据库 |
| 网络端口 | 22 / 8899 / 8900 / 443（源端→SMS）；5985/5986 WinRM；目标端 SG 仅放行迁移端口 |

## 迁移主机信息来源（Host_Information 环境变量）

**批量迁移主机信息从环境变量 `Host_Information`（JSON 数组模板）读取**，不再读取 Excel/CSV。
模板（中文键/英文键均可；数组可含源端主机与代理主机两类对象；可多条源端 + 一条代理）：

```bash
export Host_Information='[
  {
    "主机名": "xxxx", "公网IP": "xxxx", "内网IP": "xxxx", "端口号": "5985",
    "用户名": "xxxx", "密码": "xxxx",
    "region_id": "xxxx", "region_name": "xxxx",
    "project_id": "xxxx", "project_name": "xxxx",
    "os_type": "WINDOWS", "use_public_ip": "false"
  },
  {
    "代理主机名": "xxxx", "公网IP": "xxxx", "内网IP": "xxxx", "端口号": "22",
    "用户名": "xxxx", "密码": "xxxx",
    "region_id": "xxxx", "region_name": "xxxx"
  }
]'
```

- 源端对象：`主机名 / 公网IP / 内网IP / 端口号(WinRM) / 用户名 / 密码 / region_id / region_name / project_id / project_name / os_type / use_public_ip`。
- 代理对象（仅私网）：`代理主机名 / 公网IP / 内网IP / 端口号(SSH) / 用户名 / 密码 / region_id / region_name`。
- 公网批量：`host` 取公网IP；私网批量：`host` 取内网IP，gost 转发目标用内网IP，代理连接信息取代理对象（回退 `config.proxy_server`）。
- 旧 `config/hosts.csv` 保留为兼容回退；显式传 CSV 路径时仍按 CSV 执行。

## 前置任务：环境变量检查（必做）

**AI/助手行为约定（本 skill 触发后、执行任何迁移动作前）**：
1. 先检查 `migration_Access_Key / migration_Secret_Access_Key / migration_password / migration_domain / Host_Information` 是否已设置；
2. 未设置 → **立即提醒客户先配置环境变量**，并给出下方模板/脚本；未配置前不开始任何迁移编排；
3. `unified_migrate.py` 启动时会自动拦截（`preflight_check.py` 独立检查），`--skip-preflight` 为逃生口（仅当所有参数已内嵌 migrate.yaml 时使用）。

执行任何迁移（公网/私网、单台/批量）**前**，必须先确认迁移所需环境变量已设置。
如果客户尚未设置，**必须先提醒客户配置环境变量，再继续迁移**；未配置前不得直接执行迁移编排。

**环境变量模板已内置**（`scripts/windows_migration/config/`，占位符形式，权限 600）：
- `env.public.sh.example` —— 公网环境变量模板（用法：`cp env.public.sh.example env.public.sh` → 填值 → `source`）
- `env.private.sh.example` —— 私网环境变量模板（源端+代理两条 Host_Information 对象；用法同上）
- 用法：`cp env.public.sh.example env.public.sh` → 填入真实值 → `source env.public.sh`

```bash
# 云侧凭证（必设）
export migration_Access_Key="<ak>"                       # 永久凭证
export migration_Secret_Access_Key="<sk>"
export migration_password="<windows-admin-password>"     # Windows 源端 Administrator 密码
export migration_domain="<云账号domain>"                  # IAM 账号 domain
# 主机信息（批量必设；单台模式可从 migrate.yaml source 段读取，仍建议设置）
export Host_Information='[ ... ]'                        # JSON 数组主机信息，见上节模板
```

快速自检（缺任一个即为未配置）：

```bash
env | grep -E '^(migration_Access_Key|migration_Secret_Access_Key|migration_password|migration_domain|Host_Information)=' >/dev/null && echo "环境变量已配置" || echo "缺少环境变量，请先配置"
```

未设置时的标准提醒（供 AI/助手对客户输出）：

> 请先配置迁移环境变量：`migration_Access_Key`、`migration_Secret_Access_Key`、`migration_password`、`migration_domain` 以及 `Host_Information`（JSON 数组主机信息）。未配置前不会开始任何迁移动作。

## 迁移目标模板：公网 / 私网

所有运行时参数（场景、源端、代理、OBS、SMS 任务、目标端编排）由 `config/migrate.yaml` 注入，
切换公网/私网只需改 `migrate.yaml` 关键项 + `Host_Information` 模板，引擎代码零改动。

**migrate.yaml 模板已内置**（`scripts/windows_migration/config/`，占位符形式，权限 600）：
- `migrate.public.yaml`  —— 公网模板（proxy_mode=false、use_eip=true、放行源端公网IP/32）
- `migrate.private.yaml` —— 私网模板（proxy_mode=true+gost、use_eip=false、放行源端内网IP/32）
- 用法：`cp migrate.public.yaml migrate.yaml`（或直接 `--config config/migrate.public.yaml`）→ 替换真实值

### 目标一：公网迁移（public）

- 适用：源端 Windows 可直连华为云 OBS/SMS（有公网 IP / 可路由出网）。
- 目标端：自动创建 VPC/子网/安全组（最小权限）/ECS/EIP（use_eip=true）。

`config/migrate.yaml` 关键项：

```yaml
scenario: public                  # public=公网直连
source:
  host: "<源端公网IP>"             # 公网直连用公网IP
  username: "Administrator"
  winrm_port: 5985
sms_agent:
  proxy_mode: false               # 公网不走代理
proxy_server:
  host: ""                        # 公网留空
proxyopt:
  skip: true
sms_task:
  use_public_ip: true             # 公网迁移
  sg_source_cidrs: ["<源端公网IP>/32"]   # 【红线】仅放行源端公网IP/32
  use_eip: true                   # 绑定 EIP
```

`Host_Information` 模板（公网：只含源端对象，`use_public_ip="true"`）：

```bash
export Host_Information='[
  {
    "主机名": "win-src-1", "公网IP": "<源端公网IP>", "内网IP": "<源端内网IP>",
    "端口号": "5985", "用户名": "Administrator", "密码": "<密码>",
    "region_id": "cn-north-4", "region_name": "华北-北京四",
    "os_type": "WINDOWS", "use_public_ip": "true"
  }
]'
```

执行：

```bash
cd scripts/windows_migration/
python3 unified_migrate.py --scenario public --batch env --workers 10
```

### 目标二：私网迁移（private）

- 适用：源端不能直连华为云，需经跳板机（Squid/gost 代理）转发；任务层用内网 IP。
- 目标端：自动创建 VPC/子网/安全组/ECS（use_eip=false，不绑 EIP）。

`config/migrate.yaml` 关键项：

```yaml
scenario: private                 # private=私网代理
source:
  host: "<源端内网IP>"             # 私网用内网IP（gost 转发目标）
  username: "Administrator"
  winrm_port: 5985
sms_agent:
  proxy_mode: true                # 私网走 gost+Squid
proxy_server:
  host: "<跳板机公网IP>"
  ssh_port: 22
  ssh_username: "root"
  ssh_password: "<跳板机密码>"
  squid_port: 3128
  gost_listen_port: 15985
proxyopt:
  skip: false
sms_task:
  use_public_ip: false            # 私网迁移
  sg_source_cidrs: ["<源端内网IP>/32"]   # 【红线】私网放行源端内网IP/32，否则 ATTACH_AGENT_IMAGE 失败
  use_eip: false                  # 私网不绑 EIP
```

`Host_Information` 模板（私网：源端对象 + 代理对象）：

```bash
export Host_Information='[
  {
    "主机名": "win-src-1", "公网IP": "<源端公网IP>", "内网IP": "<源端内网IP>",
    "端口号": "5985", "用户名": "Administrator", "密码": "<密码>",
    "region_id": "cn-north-4", "region_name": "华北-北京四",
    "os_type": "WINDOWS", "use_public_ip": "false"
  },
  {
    "代理主机名": "jump-1", "公网IP": "<跳板机公网IP>", "内网IP": "<跳板机内网IP>",
    "端口号": "22", "用户名": "root", "密码": "<跳板机密码>",
    "region_id": "cn-north-4", "region_name": "华北-北京四"
  }
]'
```

执行：

```bash
cd scripts/windows_migration/
python3 unified_migrate.py --scenario private --batch env --workers 10
# 迁移结束清理（源端 + 代理；先打通 gost 再清源端）
python3 cleanup_environment.py --config config/migrate.yaml --yes
```

## 快速开始（双 CLI）

```bash
cd scripts/windows_migration/

# Phase A（自动含源端清理）
python3 unified_migrate.py --scenario public  --config config/migrate.yaml --json   # 公网直连
python3 unified_migrate.py --scenario private --config config/migrate.yaml          # 私网代理

# 批量（环境变量 Host_Information 已 export；CSV 兼容：--batch config/hosts.csv）
python3 unified_migrate.py --scenario public  --batch env --workers 10
python3 unified_migrate.py --scenario private --batch env --workers 10
# 未传 --batch 但已设置 Host_Information 时，自动进入批量模式

# Phase B（每个变更子命令可用 --yes 免确认；破坏性命令需属主）
python3 sms_task.py discover --config config/migrate.yaml
python3 sms_task.py prepare-target --config config/migrate.yaml
python3 sms_task.py create --yes && python3 sms_task.py start --yes
python3 sms_task.py wait --config config/migrate.yaml        # 短分段轮询至 SUCCESS
# 同步/割接（KooCLI 7.2.x 兼容）：
#   sync（默认 syncing）→ 枚举不支持时自动回退跳过（任务已 MIGRATE_SUCCESS 无需增量同步）
#   cutover（官方 cutover）→ 枚举不支持时自动回退 = “启动目的端 ECS”（BatchStartServers，等效割接）
python3 sms_task.py sync --yes && python3 sms_task.py cutover --yes
python3 sms_task.py cleanup --yes && python3 sms_task.py release --resource-type <eip|sg> --resource-id <id> --yes

# 环境清理（源端 + 代理；先打通 gost 再清源端）
python3 cleanup_environment.py --config config/migrate.yaml --yes
```

## Agent 重启与双向检查（私网场景实测）

- **禁止**以 SYSTEM / 普通后台进程直接启动 `C:\SMS-Agent-Py3\SMS-Agent.exe`：无交互桌面会“假死”（进程在、日志停写、控制台永远看不到源端）。
- **禁止手动 `schtasks /run /tn ConfigureSMSAgent`**：ConfigurePhase 写入的 `.secrets.dat` 是一次性文件（AutoIt/exe 读取后自动删除）；手动 /run 时 secrets 已消失 → 日志出现 `invalid AK or SK` → 实际未注册。执行 exe 的 bat 已加 secrets 缺失前置守卫。
- **正确重启方式：重跑官方恢复入口**（重建 secrets 并回读校验 → 重传 exe → 重建计划任务 → 自动 Verify；私网走 gost+Squid）：
  ```bash
  python3 agent_recover.py --scenario private --config config/migrate.yaml   # 私网
  python3 agent_recover.py --scenario public  --config config/migrate.yaml   # 公网
  ```
  退出码 0 = 恢复成功；重新注册后 `source_id` 变化，以控制台最新返回为准。

**双向检查（两步都过 ⇒ Agent 启动成功）**：
- 方向1（源端进程+心跳）：`Get-Process SMS-Agent` 有进程；Info 日志最近写入 <5min 且 Error 日志无新增失败。（启动期 `HwDiskMon.sys PermissionError` 为已知无害项）
- 方向2（控制台注册）：`hcloud SMS ListServers --cli-region=<region>`：count≥1、目标 IP 存在、`connected=true`、`state=waiting`、checks 全 OK。

## 安全规则与属主体系

> 完整 71 条见 `references/safety-rules.md`；核心红线如下 12 条 + 属主红线。

| # | 规则 |
|---|------|
| 1 | 禁止在源端执行破坏性操作（快照/关机/磁盘修改） |
| 2 | 禁止弱密码（目标 admin_pass 满足复杂度） |
| 3 | 禁止跳过 syncing 校验（必须等复制完成） |
| 4 | 禁止手动创建 ECS（必须经本 skill 编排） |
| 5 | 禁止安全组 0.0.0.0/0 全放通（仅放行迁移所需端口） |
| 6 | AK/SK 不落盘、不输出、不入日志、不入库 |
| 7 | WinRM 优先 HTTPS(5986)，HTTP(5985) 仅内网 |
| 8 | Windows 使用 MIGRATE_BLOCK，不使用 MIGRATE_FILE |
| 9 | 源端必须 NTFS、基本磁盘、磁盘≤23、CPU<80%、内存>256MB、系统卷在磁盘1 |
| 10 | 2012+ Py3 GUI Agent；2008/7 Py2 CLI Agent |
| 11 | GPT 分区目标盘 +1GB；禁止 RAID/BitLocker/AD/多节点数据库 |
| 12 | 任务名 ≤16 字符 + 字符集校验（SMS.7711） |

**资源属主红线（OwnerID 指纹）**：
```
owner_id = base32(HMAC(migration_ak, SALT || project_id))[:8]
is_owned = Tag(owner_id)==derived 或 名称含 derived 或 config/owned_resources.json 精确 ID
```
- O1 非属主资源禁止任何更改/删除，仅只读复用；O2 非属主 SG 禁加规则
- O3 删除类操作必须**属主 + 用户显式确认**；O4 安全组 0.0.0.0/0 一律拒绝；O5 非属主 ECS 不得 stop/start；O6 凭据不落盘、日志打码

**防资源浪费**：VPC/子网稳定名复用、安全组规则指纹归并（N台→1个 SG）、EIP 空闲复用属主优先、`release` 用后即还。

## 目录结构

```
huawei-cloud-migration-windows-ecs/
├── SKILL.md / README.md               # 主文档与速览
├── requirements.txt                   # Python 依赖清单
├── scripts/windows_migration/         # ★ 唯一迁移执行引擎
│   ├── unified_migrate.py             # Phase A：Agent 部署编排（public/private/批量，主机信息取 Host_Information）
│   ├── sms_task.py                    # Phase B：控制面编排（discover→prepare→create→start→…→release）
│   ├── preflight_check.py             # 迁移前置环境变量检查（unified_migrate 启动自动拦截）
│   ├── cleanup_environment.py         # 环境清理编排（①gost→②源端→③代理）
│   ├── cleanup_windows.py             # 源端残留清理命令清单（单一来源，幂等）
│   ├── agent_recover.py               # Agent 官方恢复入口（WinRM→ConfigurePhase→VerifyPhase）
│   ├── run_migration.sh / run_sms_task.sh   # 运行包装脚本
│   ├── config/                        # migrate.public/private.yaml + env.*.sh.example 模板（占位符，600）
│   ├── core/                          # config/hostinfo/ownership/sms_client/target_provider/winrm/executor
│   ├── phases/                        # 10 阶段（含 cleanup_source_phase 部署前必清）
│   ├── scenarios/                     # public/private 场景编排
│   ├── proxyopt/                      # 私网跳板机：Squid/gost/HTTP/precache（config 驱动）
│   └── scripts/py3|py2/               # configure exe/au3、Py2 CLI 配置工具
├── references/                        # 安全规则/流程/排障/Agent 指南（问题统一归档 troubleshooting.md）
└── templates/                         # pre/post 迁移检查脚本
```

## 参考文档

- 安全规则清单：`references/safety-rules.md`（71 条）
- 流程详解：`references/migration-workflow.md`；故障排查与问题处理集（统一归档）：`references/troubleshooting.md`
- Windows Agent 安装/自动化：`references/sms-agent-guide.md`、`references/sms-agent-automation-guide.md`
