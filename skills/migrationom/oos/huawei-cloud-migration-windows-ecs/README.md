# SMS Windows 主机迁移到华为云 ECS — Skill 速览

> 自动化 Windows 源端 → 华为云 ECS。底层 SMS + WinRM + MIGRATE_BLOCK。
> 公网/私网 migrate.yaml 与环境变量模板已内置（`config/migrate.public.yaml`、`config/migrate.private.yaml`、`config/env.public.sh.example`、`config/env.private.sh.example`）；迁移前必须提醒客户配置环境变量（`preflight_check.py` 自检）。
> 批量迁移主机信息从环境变量 Host_Information（JSON 模板）读取（原 CSV 兼容回退）；部署前必清源端 + 环境清理编排 + 私网 Squid/CONNECT 修复 + 数据盘自动 1:1 + 任务名/标签参数修复。
> **主文档：`SKILL.md`；详细引擎文档：`scripts/windows_migration/README.md`。**

## 支持的 Windows 版本

| 操作系统 | Agent | 界面 |
|----------|-------|------|
| Server 2012+ / 2016 / 2019 / 2022 / 2025 | Python3 Agent | GUI（exe/AutoIt 自动化） |
| Server 2008 / 2008R2 / Win7 | Python2 Agent | CLI（命令行配置） |
| Win 8.1 / 10 / 11（64位） | Python3/Python2 | GUI/CLI |

源端约束：**NTFS、基本磁盘、磁盘≤23、CPU<80%、内存>256MB、系统卷在磁盘1**；
GPT 目标盘 +1GB；禁止 RAID / BitLocker / 动态磁盘 / AD / 多节点数据库。

## 前置

```bash
pip install -r requirements.txt   # Python 依赖（单一来源：requirements.txt）
hcloud --version && which obsutil

# AK/SK 进入 config/migrate.yaml（obs.ak/sk、sms_agent.ak/sk）；或环境变量注入
export migration_Access_Key="<ak>"  migration_Secret_Access_Key="<sk>"
export migration_password="<windows-admin-password>"
export migration_domain="<云账号domain>"   # IAM 账号 domain（仅前置检查；引擎实际端点取 migrate.yaml sms_agent.domain_id）
```

源端开启 WinRM（管理员 PowerShell）：`Enable-PSRemoting -Force; winrm quickconfig -transport:http; Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force; netsh advfirewall firewall add rule name="WinRM-HTTP" dir=in action=allow protocol=TCP localport=5985`

## 快速开始

```bash
cd scripts/windows_migration/

# Phase A（自动含源端清理）
python3 unified_migrate.py --scenario public  --config config/migrate.yaml   # 公网直连
python3 unified_migrate.py --scenario private --config config/migrate.yaml   # 私网代理
python3 unified_migrate.py --scenario public  --batch config/hosts.csv --workers 10  # 批量

# Phase B
python3 sms_task.py discover
python3 sms_task.py prepare-target --dry-run && python3 sms_task.py prepare-target --yes
python3 sms_task.py create --yes --name <短任务名>
python3 sms_task.py start --yes && python3 sms_task.py wait --target-state SYNCING --timeout 14400
python3 sms_task.py sync --yes && python3 sms_task.py cutover --yes
python3 sms_task.py cleanup --yes && python3 sms_task.py release --resource-type eip|sg --resource-id <id> --yes

# 环境清理（源端 + 代理；先打通 gost 再清源端）
python3 cleanup_environment.py --config config/migrate.yaml [--yes]
```

退出码：`0`=成功 `1`=失败 `2`=配置错误 `130`=中断。变更类操作默认交互确认（`--yes` 跳过）。

## 关键能力

- **公网/私网双场景**：public=OBS 签名 URL 直下；private=proxyopt 跳板机（OBS→HTTP→Squid→源端 + gost WinRM 转发）
- **部署前必清源端**（`CleanupSourcePhase`）：WinRM 建立后清理旧 Agent/残留再全新部署，杜绝"假成功/安装跳过"
- **环境清理编排**：`cleanup_environment.py` ①打通 gost → ②清源端 → ③清代理，顺序即依赖
- **目标端编排**：**优先复用源端 VPC/子网**（源端-代理-目标同网），新建 VPC/子网**默认禁止网段重叠**（相等/包含/被包含即报错，仅明确告知/ER 特殊组网可 `allow_cidr_overlap=true`）；规格/镜像自动匹配、**数据盘按源端 1:1 自动创建挂载**、安全组最小权限、EIP 空闲复用属主优先
- **磁盘映射**：系统盘↔系统盘、数据盘容量升序配对（防 SMS.0515/9001/6033）
- **任务名固化**：≤16 字符、禁连续双下划线（防 SMS.7711）
- **批量 100 台**：10 并发、阶段级重试、幂等重跑
- **错误不静默**：SMS.xxxx/Ecs.xxxx 直接抛异常

## 安全与属主（详见 SKILL.md）

- 71 条安全规则 + 红线 O1-O6（属主资源全权、非属主只读、删除必确认、禁 0.0.0.0/0）
- OwnerID 指纹：`owner_id = base32(HMAC(migration_ak, SALT||project_id))[:8]`；Tags/名称/会话清单三重判定

## 目录结构

```
scripts/windows_migration/          # ★ 唯一迁移执行引擎
├── unified_migrate.py              # Phase A：Agent 部署（清理→安装→配置→验证）
├── sms_task.py                     # Phase B：控制面编排（discover→prepare→create→…→release）
├── preflight_check.py              # 迁移前置环境变量检查
├── cleanup_environment.py          # 环境清理编排（gost→源端→代理）
├── cleanup_windows.py              # 源端清理命令（单一来源，幂等）
├── agent_recover.py                # Agent 官方恢复入口
├── run_migration.sh / run_sms_task.sh
├── config/                         # migrate.public/private.yaml + env.*.sh.example 模板（占位符）
├── core/  phases/  scenarios/  proxyopt/  scripts/py3|py2/
└── README.md                       # 引擎详细文档
references/                         # 安全规则/流程/排障/Agent 指南
templates/                          # pre/post 迁移检查脚本
```

## 故障排查速查

- 问题处理集与排障（统一归档）：`references/troubleshooting.md`

- WinRM 连不上：5985 放通、`Enable-PSRemoting`、TrustedHosts
- Agent 注册失败：查 `C:\SMS-Agent-Py3\Logs\SmsAgent_Error.log`；出口 8899/8900/443
- 私网复制失败：查代理 Squid `access.log` 是否 `TCP_DENIED`（CONNECT 仅放行 22/8899/8900/443）
- SMS.7711：任务名 → 短名 （`--name`，≤16/无 `__`）
- SMS.0515/9001/6033：磁盘映射 → 引擎自动 1:1 + prepare-target 自动补数据盘
- 迁移后蓝屏：目标镜像引导与源端一致、virtio 驱动（`references/troubleshooting.md`）

## 许可证

许可证：Apache-2.0。