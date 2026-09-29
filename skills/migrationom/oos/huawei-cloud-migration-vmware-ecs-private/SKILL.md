---
name: huawei-cloud-migration-vmware-ecs-private
description: 在私网环境下将 VMware 虚拟机迁移到华为云 ECS，适用于源端和目的端位于不同网络段、通过 VPN 打通的场景。无公网 IP/EIP、VPN 打通、代理 ECS 部署 squid+GOST+rsync 实现代理/转发/文件同步。触发词：私网迁移、私网环境迁移、VPN迁移、内网迁移、无公网迁移、VMware私网迁移、VMware内网迁移、代理ECS迁移、GOST迁移、private network migration、VPN migration、offline migration
---

# 私网环境 VMware → 华为云 ECS 迁移 Skill

## 概述

在私网环境下将 VMware 虚拟机迁移到华为云 ECS，适用于源端和目的端位于不同网络段、通过 VPN 打通的场景。

**核心特性**：无公网 IP/EIP、VPN 打通、代理 ECS 部署 squid+GOST+rsync 实现代理/转发/文件同步。

| 通道 | 路径 | 说明 |
|------|------|------|
| 控制流代理 | SMS Agent → 云API:443 | 通过 squid HTTP 代理 |
| 数据流转发 | SMS Agent → 目标ECS:22/8899/8900 | 通过 GOST 转发 |
| 管理通道 | 操作端 → 源端SSH:22 | 直接 SSH 管理 |

## 支持范围与限制

> **⚠️ 重要声明：本 Skill 仅支持以下迁移场景，超出范围不支持：**

| 维度 | 支持范围 | 说明 |
|------|----------|------|
| 网络环境 | **仅私网（Private Network）** | 源端与目的端位于不同网络段，通过 VPN 打通；不支持公网直连模式 |
| 操作系统 | **仅 Linux** | 不支持 Windows 主机迁移 |
| CPU 架构 | **仅 x86_64（amd64）** | 不支持 ARM（aarch64/arm64）架构迁移 |
| 源端平台 | VMware 虚拟机 | 通过 SMS Agent 实现块级数据同步 |
| 目标平台 | 华为云 ECS | 自动创建目标 ECS 并执行迁移 |

**不支持 ARM 架构的技术原因**：
- ECS 规格选择：代码主动排除所有 ARM 规格（kc/ac/ai/kai/kx/ki/ah/as/at/sn 前缀），仅匹配 x86 规格
- 目标镜像：镜像映射表仅包含 x86_64 公共镜像 ID，无 ARM 镜像
- rsync 二进制：预编译包仅提供 x86_64 版本（源码编译兜底可适配 ARM，但未正式验证）

## 触发词

私网迁移、私网环境迁移、VPN迁移、内网迁移、无公网迁移、VMware私网迁移、VMware内网迁移、代理ECS迁移、GOST迁移、private network migration、VPN migration、offline migration

## 前置条件

### 网络环境
- 源端 VMware 环境与华为云 VPC 已通过 VPN 打通
- 代理 ECS 可达源端 SSH(22) 和华为云内网 API
- 操作端可通过 SSH 连接代理 ECS

### 源端环境
- VMware 环境已安装 SMS Agent（或可通过代理安装）
- 源端 SSH 可达，已知 root 密码或密钥

### hcloud CLI 与 obsutil 凭证配置
- **hcloud CLI 版本要求**：>= 7.2.2，运行 `hcloud version` 验证，运行 `hcloud configure list` 检查配置
- 如未安装或版本过低，参考安装指南：https://github.com/huaweicloud/huaweicloud-skills/blob/master/skills/bss/billing/huawei-cloud-billing-scout/references/cli-installation-guide.md
- **hcloud 配置永久 AK/SK**：`hcloud configure init`（参考：https://support.huaweicloud.com/usermanual-hcli/hcli_03_002.html）
- **obsutil 凭证配置**（需独立安装 obsutil）：`obsutil config -i=<YourAK> -k=<YourSK> -e=obs.<Region>.myhuaweicloud.com`
  - 常见端点：cn-north-1→obs.cn-north-1.myhuaweicloud.com、cn-north-4→obs.cn-north-4.myhuaweicloud.com、cn-east-3→obs.cn-east-3.myhuaweicloud.com、cn-south-1→obs.cn-south-1.myhuaweicloud.com、cn-southwest-2→obs.cn-southwest-2.myhuaweicloud.com

### 🚨 AK/SK 凭证配置（最高优先级强制规则）

> **AI 违反以下任何一条即为严重错误，应立即停止并重新执行配置流程**：
> 1. 学习完本 skill 后，**第一件事**必须是向用户提示配置永久 AK/SK，**绝不允许跳过、延后或自行判断**
> 2. **AI 严禁自行检查凭证缓存（`~/.migration_skill/.cred_cache`）、hcloud 配置等已有状态并假设配置已完成** — 即使发现已有缓存，也必须先询问用户由用户选择
> 3. **AI 严禁代替用户决策** — 不能自行选择使用缓存、跳过验证、假设凭证有效
> 4. **只有用户明确确认**（如"使用已有缓存"、"我已配置完成"或已设置环境变量）后，才能进入下一步
> 5. 任何绕过此环节直接执行后续操作的行为均为严重错误

**配置流程**（用户确认配置后执行）：
1. 用户设置环境变量：`export migration_Access_Key='你的AK'`、`export migration_Secret_Access_Key='你的SK'`、`export HW_ACCESS_KEY='你的永久AK'`、`export HW_SECRET_KEY='你的永久SK'`，以及 Excel 中 `${...}` 占位符引用的环境变量（如 `export migration_password='主机密码'`）
2. AI 从环境变量读取 AK/SK 并调用 `verify_credentials()` 验证（hcloud IAM KeystoneListAuthDomains 只读 API，超时 30 秒）
3. 验证通过 → AES-256-GCM 加密缓存到 `~/.migration_skill/.cred_cache`（权限 600）；验证失败 → 提示重新设置（最多重试 3 次）
4. 检测临时凭证：HST 前缀→拒绝（临时凭证），HPUA 前缀→放行（永久凭证）

**安全规范**：
- **环境变量获取**：AK/SK 通过环境变量读取，不经过命令行明文
- **本地缓存**：AES-256-GCM 加密缓存，权限 600
- **禁止临时凭证**：HST 前缀临时凭证全面禁止（包括中间操作），永久凭证验证通过后清除临时环境变量
- **变更检测**：AK/SK 变更时提示用户确认 (yes/no)，确认后联动重新配置 hcloud CLI、SMS Agent、obsutil
- **脱敏显示**：日志中 AK 脱敏（如 `HPUA****YPQY`），SK 完全隐藏
- **信息安全**：AK/SK 仅脱敏显示，禁止明文输出；禁止上传到非业务存储或公网
- **禁止操作**：临时凭证用于任何操作、命令行明文 AK/SK、IAM 创建/删除 AK/SK
- **主机密码**：Sheet1 密码列支持通用占位符 `${env_var_name}`（如 `${migration_password}`），从环境变量读取；明文值直接使用（向后兼容）；Sheet2 代理密码保持 Excel 直接读取，不走环境变量

## Excel 输入文件结构

迁移任务通过 Excel 文件（`.xlsx`）批量配置，2 个 Sheet 页：

### Sheet1: 主机信息（源端主机，每行一个迁移任务）

| 列 | 字段 | 说明 | 必填 |
|----|------|------|------|
| A | 主机名 | 源端 VM 名称 | ✅ |
| B | 内网IP | 源端 VMware VM IP | ✅ |
| C | 端口号 | SSH 端口（默认 22） | ❌ |
| D | 用户名 | SSH 用户名（默认 root） | ✅ |
| E | 密码 | SSH 密码（支持 `${env_var_name}` 占位符或明文） | ✅ |
| F | region_id | 华为云区域 ID | ✅ |
| G | region_name | 区域名称 | ❌ |
| H | project_id | 项目 ID | ✅ |
| I | project_name | 项目名称 | ❌ |
| J | os_type | OS 类型（默认 Linux） | ❌ |
| K | use_public_ip | 是否使用公网 IP（FALSE=私网模式） | ❌ |
| L | target_image_id | 目标镜像 ID（空=与源端一致） | ❌ |
| M | target_AZ | 可用区（空=随机） | ❌ |

### Sheet2: 代理主机信息（跳板机）

| 列 | 字段 | 说明 | 必填 |
|----|------|------|------|
| A | 主机名称 | 代理 ECS 名称 | ✅ |
| B | 公网IP | 代理 ECS 公网 IP | ✅ |
| C | 私网IP | 代理 ECS 私网 IP | ✅ |
| D | 端口 | SSH 端口（默认 22） | ❌ |
| E | 用户名 | SSH 用户名（默认 root） | ✅ |
| F | 密码 | SSH 密码（Excel 直接读取） | ✅ |

**密码占位符规则**：Sheet1 密码列支持通用 `${env_var_name}` 占位符，扫描所有字段值，从环境变量解析替换；运行前自动校验全部占位符环境变量已配置，缺失则报错退出；Sheet2 代理密码不走占位符解析。

## 迁移流程

### 1. 准备阶段
1. 配置 AK/SK（见前置条件，🚨 必须首先执行）
2. 准备 Excel 迁移任务文件
3. 验证 VPN 连通性

### 2. 代理 ECS 部署
1. 创建代理 ECS（需公网 IP 或通过 NAT 网关访问外网）
2. 部署 squid 代理（控制流代理，端口 3128）
3. 部署 GOST 转发（数据流转发，端口 8899/8900）
4. 部署 rsync（文件同步）

### 3. 批量迁移执行
```bash
# 首次运行 (设置环境变量后，自动读取并缓存)
export migration_Access_Key='你的AK'
export migration_Secret_Access_Key='你的SK'
export migration_password='主机密码'  # Excel 中 ${migration_password} 占位符引用

python scripts/batch_migrate.py tasks.xlsx \
  --proxy-ip <代理ECS_IP> --proxy-user root --proxy-password <代理密码>

# 后续使用 (本地加密缓存，无需再次设置环境变量)
python scripts/batch_migrate.py tasks.xlsx --cred-cache \
  --proxy-ip <代理ECS_IP> --proxy-user root --proxy-password <代理密码>
```

流程：读取 Excel → 生成迁移任务列表 → 对每个任务执行 `migrate_worker.py` → 记录结果并输出汇总报告

### 4. 单机迁移流程（migrate_worker.py）
1. **校验目标 ECS 名称**：检查 target_name 是否符合命名规则
2. **防重复检查**：按所属权标签查找已有目标 ECS
   - 找到 ACTIVE/STOPPED 的 ECS → 直接复用
   - 找到异常状态的 ECS → 提示用户确认后删除重建
   - 未找到 → 创建新 ECS
3. **创建目标 ECS**：调用 `ecs_ops.create_target_ecs()`，校验命名规则、创建 ECS、打所属权标签
4. **配置代理转发**：在代理 ECS 上配置 GOST 转发规则
5. **安装 SMS Agent**：通过代理在源端安装 SMS Agent
6. **执行迁移**：启动 SMS 迁移任务
7. **验证迁移**：检查目标 ECS 状态

## 所属权管理与防重复创建

### 所属权标签
通过 ECS 标签实现资源所属权管理：

| 标签键 | 标签值 | 说明 |
|--------|--------|------|
| `migration-skill` | `vmware-ecs-private` | 标识由本 skill 创建 |
| `source-ip` | 源端 IP | 溯源标识 |
| `source-name` | 源端 VM 名称 | 溯源标识 |
| `migration-time` | 时间戳 | 迁移时间记录 |

### 防重复创建逻辑
1. 按 `migration-skill=vmware-ecs-private` + `source-ip=<源IP>` 标签查找已有 ECS
2. 找到且状态为 ACTIVE/STOPPED → 复用，跳过创建
3. 找到且状态为 ERROR/其他 → 提示用户确认后删除重建
4. 未找到 → 创建新 ECS 并打标签

### 权限校验
- 删除/停止/重启 ECS 前，校验 `migration-skill` 标签
- 非本 skill 创建的 ECS，拒绝操作并抛出 `PermissionError`
- 只能操作带自己所属权标签的 ECS

## 文件结构

```
huawei-cloud-migration-vmware-ecs-private/
├── SKILL.md                                    # Skill 文档
├── README.md                                   # 使用说明文档
├── scripts/
│   ├── batch_migrate.py                        # 批量迁移入口 (1634行)
│   ├── migrate_worker.py                       # 单机迁移逻辑 (1540行)
│   ├── step_tracker.py                         # 步骤追踪器 (250行, 耗时/阻塞/问题)
│   ├── ecs_ops.py                              # ECS 操作封装 (1303行)
│   ├── excel_reader.py                         # Excel 读取解析 (525行, 2 Sheet)
│   ├── ownership_utils.py                      # 所属权标签管理 (217行)
│   ├── hcloud_wrapper.py                       # hcloud CLI 封装/脱敏日志 (1102行)
│   ├── credential_manager.py                   # AK/SK 凭证管理 (775行, 环境变量+AES缓存)
│   ├── proxy_ecs_ops.py                        # 代理 ECS 部署 (680行)
│   ├── gost_ops.py                             # GOST 转发配置 (889行)
│   ├── squid_ops.py                            # squid 代理配置 (367行)
│   ├── sms_ops.py                              # SMS 迁移任务操作 (508行)
│   ├── sms_agent_push.py                       # SMS Agent 安装/推送 (1541行)
│   ├── ssh_utils.py                            # SSH 远程操作封装 (670行)
│   ├── network_ops.py                          # 网络资源操作 (899行)
│   ├── safety_checker.py                       # 安全检查 (433行)
│   ├── skill_logger.py                         # 日志管理 (263行)
│   ├── retry_utils.py                          # 重试工具 (186行)
│   ├── report.py                               # 迁移报告生成 (344行, 含步骤追踪)
│   ├── error_reporter.py                       # 错误报告 (161行)
│   ├── post_migration_verify.py                # 迁移后验证 (1065行)
│   ├── smoke_test_server_id.py                 # 冒烟测试 (272行)
│   ├── task_name_utils.py                      # 任务名称工具 (128行)
│   ├── vpn_check.py                            # VPN 连通性检查 (347行)
│   └── agent_state_check.sh                    # Agent 状态检查脚本 (299行)
└── templates/
    ├── generate_template.py                    # Excel 模板生成脚本
    ├── 私网迁移源主机Linux相关信息1.0.xlsx      # Excel 模板示例文件
    └── 迁移网络设计图.png                       # 迁移网络架构设计图
```

## 使用方法

### 快速开始
1. **配置 AK/SK（🚨 必须首先执行）**：设置环境变量 `migration_Access_Key`、`migration_Secret_Access_Key`、`HW_ACCESS_KEY`、`HW_SECRET_KEY`，以及 Excel 中 `${...}` 占位符引用的环境变量。配置 hcloud CLI（`hcloud configure init`）和 obsutil（`obsutil config -i=<AK> -k=<SK> -e=obs.<Region>.myhuaweicloud.com`，需独立安装 obsutil）。AI 验证通过后缓存。**必须收到用户明确确认后才能继续**
2. 准备 Excel 任务文件（参考模板，2 Sheet 页；Sheet1 密码列可填 `${env_var_name}` 占位符或明文）
3. 部署代理 ECS 并安装 squid+GOST+rsync
4. 执行批量迁移：`python scripts/batch_migrate.py tasks.xlsx --proxy-ip <IP> --proxy-user root --proxy-password <代理密码>`
5. 后续使用缓存：加 `--cred-cache` 参数
6. 后台运行（推荐）：加 `-b` 参数，进程通过 nohup 后台运行，终端关闭不会被杀死。日志→`migration.log`，PID→`migration.pid`，查看进度：`tail -f migration.log`

### 命令参数

| 参数 | 说明 | 必填 |
|------|------|------|
| `excel` | Excel 任务文件路径 (2 Sheet 页) | ✅ |
| `--cred-cache` | 使用本地加密缓存中的凭证 | 缓存模式 |
| `--region` | 华为云 region（默认 cn-north-4） | ❌ |
| `--project-id` | 华为云 project ID | ❌ |
| `--proxy-ip` | 代理 ECS IP（覆盖 Excel Sheet2） | ✅ |
| `--proxy-port` | 代理 ECS SSH 端口（默认 22） | ❌ |
| `--proxy-user` | 代理 ECS SSH 用户（默认 root） | ✅ |
| `--proxy-pass` | 代理 ECS SSH 密码 | ✅ |
| `--vpc-id` | 已有 VPC ID（不传则自动创建） | ❌ |
| `--subnet-id` | 已有子网 ID（不传则自动创建） | ❌ |
| `--sg-id` | 已有安全组 ID（不传则自动创建） | ❌ |
| `--max-workers` | 最大并发数（默认 20，支持 100 台并发） | ❌ |
| `--max-workers-prepare` | Phase A 准备阶段并发数 | ❌ |
| `--max-workers-migrate` | Phase B 迁移阶段并发数 | ❌ |
| `--max-retries` | 最大重试次数（默认 2） | ❌ |
| `--retry-delay` | 重试间隔秒数（默认 10） | ❌ |
| `--task-timeout` | 单任务超时秒数（默认 10800=3小时） | ❌ |
| `--security-token` | 临时凭证安全令牌（HST 前缀 AK 必须提供） | ❌ |
| `--dry-run` | 仅校验不执行 | ❌ |
| `--deep-verify` | 深度验证模式 | ❌ |
| `--force-update` | 强制更新 Agent | ❌ |
| `--output` | 结果输出路径（默认 migration-results.json） | ❌ |
| `--log-dir` | 日志目录（默认 /var/log/migration-private） | ❌ |
| `--rsync-binary` | rsync 二进制路径 | ❌ |
| `--background`, `-b` | 后台运行 (nohup) | ❌ |
| `--log-file` | 后台运行日志文件（默认 migration.log） | ❌ |
| `--pid-file` | 后台运行 PID 文件（默认 migration.pid） | ❌ |

**环境变量**（首次运行必须设置）:

| 环境变量 | 说明 |
|----------|------|
| `migration_Access_Key` | 永久 AK（HPUA 前缀） |
| `migration_Secret_Access_Key` | 永久 SK |
| `HW_ACCESS_KEY` | 华为云永久 AK（供 hcloud/obsutil 凭证配置使用） |
| `HW_SECRET_KEY` | 华为云永久 SK（供 hcloud/obsutil 凭证配置使用） |
| `${...}` 占位符变量 | Excel 中任意 `${env_var_name}` 占位符引用的环境变量，运行前自动校验全部已配置 |

## 安全组规则

迁移所需的安全组规则（自动创建或使用已有安全组）：

| 方向 | 协议 | 端口 | 源/目的 | 说明 |
|------|------|------|---------|------|
| 入方向 | TCP | 22 | 0.0.0.0/0 | SSH 管理 |
| 入方向 | TCP | 8899 | 0.0.0.0/0 | GOST 数据通道 |
| 入方向 | TCP | 8900 | 0.0.0.0/0 | GOST 数据通道 |
| 入方向 | TCP | 3128 | 0.0.0.0/0 | squid 代理 |

## 故障排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| SSH 连接超时 | VPN 未打通 / 安全组未放行 | 检查 VPN 连通性、安全组规则 |
| hcloud 认证失败 | AK/SK 无效或临时凭证 | 重新设置永久 AK/SK 环境变量，运行验证 |
| SMS Agent 安装失败 | 代理不通 / 源端 SSH 不可达 | 检查代理 ECS squid/GOST 配置、源端 SSH |
| GOST 转发失败 | 端口冲突 / 防火墙 | 检查 8899/8900 端口占用、防火墙规则 |
| 目标 ECS 创建失败 | 配额不足 / 镜像无效 | 检查 ECS 配额、镜像 ID |
| 迁移任务超时 | 大磁盘 / 网络带宽不足 | 调整 `--task-timeout`，检查网络带宽 |
| 凭证缓存损坏 | 缓存文件被篡改 | 删除 `~/.migration_skill/.cred_cache`，重新设置环境变量 |
| 密码占位符未解析 | 环境变量未设置 | 检查 Excel 中 `${...}` 占位符对应的环境变量是否已 export |

## 日志

- **日志目录**：`/var/log/migration-private/`（可通过 `--log-dir` 修改）
- **后台运行**：`tail -f migration.log` 查看进度，`cat migration.pid` 获取 PID
- **结果文件**：`migration-results.json`（可通过 `--output` 修改）
- **AK 脱敏**：日志中 AK 显示为 `HPUA****YPQY` 格式，SK 完全隐藏

