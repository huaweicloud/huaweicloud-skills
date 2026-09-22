---
name: huawei-cloud-rds-failover
description: >
  华为云 RDS 主备倒换演练工具。一键式覆盖 prepare（准备检查）→ execute（执行倒换）→ report（生成报告）全流程。
  查询 RDS HA 实例、检查 IAM 权限、安全执行主备倒换、轮询等待完成、收集日志和 CES 监控数据、生成综合 HTML 报告。
  支持 MySQL、PostgreSQL、SQL Server、MariaDB。
  Triggers: RDS主备倒换, 主备倒换演练, failover, RDS故障演练, 主备切换, 倒换实验, rds failover, RDS failover, 高可用演练, 高可用验证, RDS HA切换, 主备互换, RDS switchover, 数据库故障演练, RDS容灾演练。
---

# 华为云 RDS 主备倒换演练

## 概述

本工具用于在华为云上安全地执行 RDS 主备倒换（Failover）演练。通过三阶段流水线完成：

```
prepare（准备检查） → execute（执行倒换） → report（生成报告）
```

- **prepare**：查询 RDS HA 实例、检查 IAM 权限、生成实验配置目录
- **execute**：读取配置、执行主备倒换、轮询等待完成、收集日志和监控数据
- **report**：读取配置和执行结果、生成综合 HTML 报告

支持所有 RDS 引擎：MySQL、PostgreSQL、SQL Server、MariaDB。

## 触发词/触发条件

当用户需要执行 RDS 主备倒换、主备切换、故障演练、failover 实验时触发本 skill。

**触发词**：RDS主备倒换、主备倒换演练、failover、RDS故障演练、主备切换、倒换实验、rds failover、RDS failover、高可用演练、高可用验证、RDS HA切换、主备互换、RDS switchover、数据库故障演练、RDS容灾演练

**触发条件**：
- 用户提到 RDS 主备倒换或 failover 操作
- 用户需要对 HA 类型 RDS 实例执行主备切换
- 用户需要 RDS 故障演练或高可用验证
- 用户需要对 RDS 实例做主备互换或 switchover
- 用户需要验证 RDS 高可用容灾能力

## 前置条件

| 条件 | 说明 | 验证方式 |
|------|------|---------|
| **hcloud CLI** | 已安装并完成认证（KooCLI ≥ 3.0.0） | `hcloud version` |
| **AK/SK** | 通过 hcloud profile 配置（`hcloud configure init`）。环境变量 HUAWEICLOUD_SDK_AK/SK 仅用于脚本建议性检查，不参与 hcloud 实际认证 | `hcloud RDS ListInstances --cli-region=cn-north-1` |
| **Python 3.8+** | 运行脚本 | `python3 --version` |
| **HA 类型 RDS 实例** | 目标区域内至少存在一个主备实例 | hcloud CLI 查看 |
| **实例状态为 ACTIVE** | 倒换前实例必须处于运行状态 | prepare 阶段自动检查 |

## 配置

共享配置文件 `config/config.json`：

```json
{
  "region": "<华为云区域ID>",
  "instance_id": "<目标RDS实例ID>"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `region` | 是 | 华为云区域 ID（如 cn-north-1、cn-north-4） |
| `instance_id` | 是 | 目标 RDS 实例 ID（HA 类型，32位十六进制 + in01 后缀） |

> ⚠️ **运行前必须修改 `config/config.json`**：将 `region` 和 `instance_id` 替换为您自己的华为云区域和 RDS 实例 ID。默认占位符值无法运行，直接使用他人的实例 ID 可能导致对非预期实例执行主备倒换。

## 快速开始

### 一键完整流程

```bash
# 预演（不实际执行倒换）
python3 scripts/run.py

# 实际执行完整流水线
python3 scripts/run.py --yes
```

### 分阶段执行

```bash
# 1. 准备检查
python3 scripts/run.py --phase prepare
# 或直接运行
python3 scripts/prepare.py

# 2. 执行倒换（需人工确认）
python3 scripts/run.py --phase execute --yes
# 或直接运行
python3 scripts/execute.py --config-dir experiments --yes

# 3. 生成报告
python3 scripts/run.py --phase report
# 或直接运行
python3 scripts/report.py --config-dir experiments
```

## 三阶段说明

### 阶段一：prepare（准备检查）

查询 RDS 资源和用户权限，生成完整配置目录。

- 查询区域内所有 RDS 实例，筛选 HA 类型
- 检查 IAM 权限（AK/SK 配置、RDS 读写权限）
- 生成配置文件（experiment.json、iam_policy.json、monitoring.json）
- 运行 15 项准备检查，生成 HTML + Markdown 准备报告

**输出**：`experiments/` 目录下的配置文件和准备报告

### 阶段二：execute（执行倒换）

⚠️ **变更操作** — 主备倒换会实际切换主备角色。

- 加载配置，预检查（实例存在、HA 类型、ACTIVE 状态、IAM 权限）
- 调用 `hcloud RDS StartFailover` 执行主备倒换
- 每 5 秒轮询实例状态，等待主备角色交换完成（超时 120 秒）
- 收集倒换期间的 RDS 错误日志、慢 SQL 日志和 CES 监控指标
- 保存执行结果到 `execution_result.json`

**参数**：`--yes` 表示实际执行（默认预演，不做变更）

### 阶段三：report（生成报告）

读取配置和执行结果，生成综合 HTML 报告。

报告包含：结果横幅、实例信息、安全检查、IAM 权限、主备拓扑变化、倒换时间线、CES 监控指标、错误日志、慢 SQL 日志、告警规则状态。

**输出**：`report/failover_report_YYYYMMDD_HHMMSS.html`（独立 HTML，浏览器直接打开）

## CES 监控指标

倒换期间自动收集 8 个 CES 指标（命名空间 SYS.RDS）：

| 脚本逻辑名 | 华为云实际指标名 | 说明 | 单位 |
|------------|-----------------|------|------|
| rds_cpu_util | rds001_cpu_util | CPU 使用率 | % |
| rds_mem_util | rds002_mem_util | 内存使用率 | % |
| rds_disk_util | rds039_disk_util | 磁盘使用率 | % |
| rds_connections_count | rds006_conn_count | 当前连接数 | count |
| rds_in_flow | rds004_bytes_in | 网络输入流量 | Bytes/s |
| rds_out_flow | rds005_bytes_out | 网络输出流量 | Bytes/s |
| rds_iops | rds003_iops | IOPS | count/s |
| rds_replication_delay | rds073_replication_delay | 主备复制延迟 | s |

## IAM 权限要求

| 权限 | 说明 | 必需 |
|------|------|------|
| `rds:instance:list` | 查询 RDS 实例列表 | ✅ |
| `rds:instance:failover` | 执行 RDS 主备倒换 | ✅ |
| `rds:log:listErrorLogs` | 查询 RDS 错误日志 | 可选 |
| `rds:log:listSlowLogs` | 查询 RDS 慢 SQL 日志 | 可选 |
| `ces:alarm:list` | 查询 CES 告警规则 | 可选 |
| `ces:metricData:get` | 查询 CES 监控指标数据 | 可选 |

## 目录结构

```
huawei-cloud-rds-failover/
├── SKILL.md                          # 本文件
├── config/
│   └── config.json                   # 共享配置（region + instance_id）
├── scripts/
│   ├── config.py                     # 配置加载模块
│   ├── prepare.py                    # 阶段一：准备检查
│   ├── execute.py                    # 阶段二：执行倒换
│   ├── report.py                     # 阶段三：生成报告
│   └── run.py                        # 统一入口（一键全流程）
├── references/
│   ├── cli-installation-guide.md     # hcloud CLI 安装与认证指南
│   ├── iam-policies.md               # IAM 权限策略说明
│   ├── acceptance-criteria.md        # 验收标准
│   └── verification-method.md       # 验证方法
├── experiments/                      # 生成的配置目录
│   ├── experiment.json
│   ├── iam_policy.json
│   ├── monitoring.json
│   ├── execution_result.json
│   ├── readiness_report.html
│   └── readiness_report.md
└── report/                           # 生成的 HTML 报告
    └── failover_report_YYYYMMDD_HHMMSS.html
```

## 参考文档

| 文档 | 说明 |
|------|------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | hcloud CLI 安装与认证配置指南 |
| [references/iam-policies.md](references/iam-policies.md) | IAM 权限策略模板与配置说明 |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | 功能验收标准与检查清单 |
| [references/verification-method.md](references/verification-method.md) | 环境与功能验证方法、端到端验证流程 |
| [华为云 RDS 产品文档](https://support.huaweicloud.com/productdesc-rds/zh-cn_topic_dashboard.html) | RDS 关系型数据库服务产品介绍 |
| [RDS API 参考 — StartFailover](https://support.huaweicloud.com/api-rds/rds_05_0013.html) | 主备倒换 API 接口说明 |
| [CES 监控指标 — RDS](https://support.huaweicloud.com/usermanual-rds-mysql/rds_06_0001.html) | RDS CES 监控指标列表 |
