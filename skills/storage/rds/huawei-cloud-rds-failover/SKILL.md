---
name: huawei-cloud-rds-failover
description: >
  华为云 RDS 主备倒换演练工具。一键式覆盖 prepare（准备检查）→ execute（执行倒换）→ report（生成报告）全流程。
  查询 RDS HA 实例、检查 IAM 权限、安全执行主备倒换、轮询等待完成、收集日志和 CES 监控数据、生成综合 HTML 报告。
  prepare 阶段内置风险评估（复制状态、存储水位、备份兜底、负载、复制延迟等），
  严重风险默认阻止倒换（需 --force 人工确认）。
  支持 MySQL、PostgreSQL、SQL Server、MariaDB、TaurusDB（GaussDB for MySQL）。
  Triggers: RDS主备倒换, 主备倒换演练, failover, RDS故障演练, 主备切换, 倒换实验, rds failover, RDS failover, 高可用演练, 高可用验证, RDS HA切换, 主备互换, RDS switchover, 数据库故障演练, RDS容灾演练。
---

# 华为云 RDS 主备倒换演练

## 概述

本工具用于在华为云上安全地执行 RDS 主备倒换（Failover）演练。通过三阶段流水线完成：

```
prepare（准备检查） → execute（执行倒换） → report（生成报告）
```

- **prepare**：查询 RDS HA 实例、检查 IAM 权限、生成实验配置目录，并执行**风险评估**（详见下文专节）
- **execute**：读取配置、执行主备倒换、轮询等待完成、收集日志和监控数据
- **report**：读取配置和执行结果、生成综合 HTML 报告

支持所有 RDS 引擎：MySQL、PostgreSQL、SQL Server、MariaDB、TaurusDB（GaussDB for MySQL）。

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
| **AK/SK** | 通过 hcloud profile 配置（`hcloud configure init`）。脚本仅检查 AK/SK 环境变量**是否存在**（不读取实际值），实际认证由 hcloud profile 完成 | `hcloud RDS ListInstances --cli-region=cn-north-1` |
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
# 若 prepare 检测出严重风险且已人工评估接受，可加 --force 强制演练（不推荐默认使用）：
#   python3 scripts/execute.py --config-dir experiments --yes --force

# 3. 生成报告
python3 scripts/run.py --phase report
# 或直接运行
python3 scripts/report.py --config-dir experiments
```

## 三阶段说明

### 阶段一：prepare（准备检查）

查询 RDS 资源和用户权限，生成完整配置目录，并完成**风险评估**。

- 查询区域内所有 RDS 实例（marker 分页拉取，上限 50 页/5000 条），筛选 HA 类型
- 检查 IAM 权限（hcloud 认证就绪性、RDS 读写权限）
- 生成配置文件（experiment.json、iam_policy.json、monitoring.json）
- 运行 15 项准备检查，生成 HTML + Markdown 准备报告
- **风险评估**（三步流水线）：
  - **检测**：只读探测主备复制状态、复制延迟（CES）、存储水位、备份新鲜度、近24h错误日志、CPU/内存/磁盘/连接数负载、复制模式/切换策略/max_connections
  - **定级**：按阈值逐项定级（提示/未知/预警/严重），汇总总体风险等级（低/中/阻止）并给出操作建议
  - **拦截**：结果写入 `risk_assessment.json` 并嵌入准备报告；execute 阶段读取该文件，存在严重项时默认阻止倒换（需 `--force` 人工确认）

**输出**：`experiments/` 目录下的配置文件和准备报告（含 `risk_assessment.json`）

### 阶段二：execute（执行倒换）

⚠️ **变更操作** — 主备倒换会实际切换主备角色。

- 加载配置，预检查（实例存在、HA 类型、ACTIVE 状态、IAM 权限）
- 读取 `risk_assessment.json` 展示风险评估结果；存在严重风险项且未加 `--force` 时**阻止倒换**
- **校验风险评估与实例一致**：`risk_assessment.json` 的 region/instance_id 与 config.json 不一致时默认阻止（防"换实例拿旧评估放行"）
- **执行前实时复核**：倒换前立即复核主备复制状态与复制延迟（prepare 快照可能过期），发现严重异常默认阻止
- 调用 `hcloud RDS StartFailover` 执行主备倒换
- 每 5 秒轮询实例状态，等待主备角色交换完成（超时 120 秒）
- 收集倒换期间的 RDS 错误日志、慢 SQL 日志和 CES 监控指标
- 保存执行结果到 `execution_result.json`

**参数**：`--yes` 表示实际执行（默认预演，不做变更）

### 阶段三：report（生成报告）

读取配置和执行结果，生成综合 HTML 报告。

报告包含：结果横幅、实例信息、安全检查、IAM 权限、主备拓扑变化、倒换时间线、CES 监控指标、错误日志、慢 SQL 日志、告警规则状态。

> 🔒 **HTML 编码要求（防存储型 XSS）**：报告中所有来自云 API 的外部数据（实例名称、错误日志、慢 SQL、告警信息、风险检测项等）在插入 HTML 前必须经过 `html.escape` 实体编码。若云 API 返回的日志或实例名称包含恶意 HTML/JS，未编码直接插入会在浏览器中执行，造成存储型 XSS。`scripts/report.py` 和 `scripts/prepare.py`（准备报告）均已通过 `esc()` / `_esc()` 函数对所有外部数据执行 HTML 转义。

**输出**：`report/failover_report_YYYYMMDD_HHMMSS.html`（独立 HTML，浏览器直接打开）

## 风险评估

prepare 阶段在 15 项准备检查之外，额外执行风险评估，帮助降低主备倒换演练出现异常的风险。
评估分三步：**检测 → 定级 → 拦截**。

### 检测项（只读实时探测）

| 维度 | 数据来源（只读接口） | 指标 |
|------|---------------------|------|
| 实例健康 | `RDS ListInstances` | 实例状态是否 ACTIVE |
| 主备复制 | `RDS ShowReplicationStatus` | 复制状态 normal / abnormal |
| 复制延迟 | `CES ShowMetricData` rds073 | 近1小时延迟均值 |
| 存储水位 | `RDS ShowStorageUsedSpace` + `ListInstances volume.size` | 使用率 % |
| 备份兜底 | `RDS ListBackups` | 最近成功备份时间、近7天失败任务 |
| 错误信号 | `RDS ListErrorLogs` | 近24h ERROR 级条数 |
| 负载 | `CES ShowMetricData` rds001/002/039/006 | CPU/内存/磁盘/连接数均值 |
| 配置 | `ListInstances` + `RDS ShowInstanceConfiguration` | 复制模式、切换策略、max_connections、持久化参数 |

### 定级规则（阈值分级）

每项检测按阈值映射为四级：🟢 提示（info）/ ⚪ 未知（unknown）/ 🟠 预警（warning）/ 🔴 严重（critical）。
任一严重项 → 总体风险 **阻止（blocked）**；存在预警或未知项 → **中（medium）**；否则 → **低（low）**。
阈值表与业务含义见 [references/risk-model.md](references/risk-model.md)。

### 拦截机制

1. **控制台**：prepare / execute 阶段醒目输出总体等级与每项预警的影响和建议
2. **报告**：风险章节嵌入 `readiness_report.html` / `readiness_report.md`
3. **执行拦截**：`execute` 阶段读取 `risk_assessment.json`，若存在严重项（且未加 `--force`）**默认拒绝执行倒换**，需人工确认后强制演练
4. **防张冠李戴**：风险评估与待倒换实例不一致时拒绝放行；**防快照过期**：执行前实时复核复制状态与复制延迟

> ⚠️ **数据缺失不误判、但不自动放行**：某接口不可用（如引擎不支持、无权限、CES 无数据）时，该项标记为"未知（unknown）"并附说明，不会凭空产生严重风险；但未知项会使总体风险升至"中"，提示人工确认后再执行。
> ⚠️ **强制演练有代价**：`--force` 只用于你已人工评估并接受风险的情形；严重项（如复制异常、磁盘写满、无备份）通常在倒换时确实会出问题。

## CES 监控指标

倒换期间自动收集 8 个 CES 指标（命名空间 SYS.RDS）：

| 脚本逻辑名 | MySQL/MariaDB/TaurusDB | PostgreSQL | SQL Server | 说明 | 单位 |
|------------|------------------------|------------|------------|------|------|
| rds_cpu_util | rds001_cpu_util | rds001_cpu_util | rds001_cpu_util | CPU 使用率 | % |
| rds_mem_util | rds002_mem_util | rds002_mem_util | rds002_mem_util | 内存使用率 | % |
| rds_disk_util | rds039_disk_util | rds039_disk_util | rds039_disk_util | 磁盘使用率 | % |
| rds_connections_count | rds006_conn_count | rds042_database_connections | rds054_db_connections_in_use | 当前连接数 | count |
| rds_in_flow | rds004_bytes_in | rds004_bytes_in | rds004_bytes_in | 网络输入流量 | Bytes/s |
| rds_out_flow | rds005_bytes_out | rds005_bytes_out | rds005_bytes_out | 网络输出流量 | Bytes/s |
| rds_iops | rds003_iops | rds003_iops | rds003_iops | IOPS | count/s |
| rds_replication_delay | rds073_replication_delay | rds046_replication_lag | rds077_replication_delay | 主备复制延迟 | s |

> 指标名按引擎自适应（由 `ces_config.py` `ENGINE_CES_CONFIG` 驱动），上表与代码保持同步。
> MySQL/MariaDB/TaurusDB 共用同一套指标名；PostgreSQL 和 SQL Server 的连接数与复制延迟指标名不同。

## IAM 权限要求

> 授权项已对照华为云 [身份策略授权参考](https://support.huaweicloud.com/api-rds/rds_10_0008.html) 逐一核实。
> 「别名」列的授权项是同一权限的替代写法——策略中写主名或别名任意一个即可，无需同时授予。

| 权限 | 说明 | 资源类型 | 必需 |
|------|------|----------|------|
| `rds:instance:listAll` | 查询 RDS 实例列表 + 存储空间（ListInstances / ShowStorageUsedSpace）；别名 `rds:instance:list` | `-` | ✅ |
| `rds:instance:getReplicaStatus` | 查询主备复制状态（ShowReplicationStatus）；别名 `rds:instance:list` | `instance` | ✅ |
| `rds:instance:getParameter` | 查询实例参数配置（ShowInstanceConfiguration）；别名 `rds:param:list` | `instance` | ✅ |
| `rds:backup:list` | 查询 RDS 备份列表（ListBackups，风险评估·备份新鲜度检查） | `-` | ✅ |
| `rds:instance:switchover` | 执行 RDS 主备倒换（StartFailover） | `instance` | ✅ |
| `rds:log:getErrorLogs` | 查询 RDS 错误日志（ListErrorLogs）；别名 `rds:log:list` | `instance` | 可选 |
| `rds:log:getSlowLogs` | 查询 RDS 慢 SQL 日志（ListSlowLogs）；别名 `rds:log:list` | `instance` | 可选 |
| `ces:alarms:list` | 查询 CES 告警规则 | `-` | 可选 |
| `ces:metricData:get` | 查询 CES 监控指标数据 | `-` | 可选 |

> 📌 完整 IAM 策略模板（含 Resource URN 范围限定）见 [references/iam-policies.md](references/iam-policies.md)。
> 风险评估依赖 `rds:instance:getReplicaStatus`、`rds:instance:getParameter`、`rds:backup:list` 等查询复制状态、存储水位、参数配置与备份新鲜度；缺少对应权限会导致检查降级为"未知"。

## 目录结构

```
huawei-cloud-rds-failover/
├── SKILL.md                          # 本文件
├── config/
│   └── config.json                   # 共享配置（region + instance_id）
├── scripts/
│   ├── config.py                     # 配置加载模块
│   ├── prepare.py                    # 阶段一：准备检查（含风险评估接入）
│   ├── risk.py                       # 风险评估核心模块
│   ├── ces_config.py                 # CES 监控维度/指标按引擎适配（MySQL/PostgreSQL/SQLServer/MariaDB/TaurusDB）
│   ├── execute.py                    # 阶段二：执行倒换（含风险拦截 --force）
│   ├── report.py                     # 阶段三：生成报告
│   └── run.py                        # 统一入口（一键全流程）
├── references/
│   ├── cli-installation-guide.md     # hcloud CLI 安装与认证指南
│   ├── iam-policies.md               # IAM 权限策略说明
│   ├── acceptance-criteria.md        # 验收标准
│   ├── verification-method.md       # 验证方法
│   └── risk-model.md                 # 风险阈值表与业务含义
├── experiments/                      # 生成的配置目录
│   ├── experiment.json
│   ├── iam_policy.json
│   ├── monitoring.json
│   ├── execution_result.json
│   ├── risk_assessment.json
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
| [references/risk-model.md](references/risk-model.md) | 风险评估阈值表与业务含义（风险模型） |
| [华为云 RDS 产品文档](https://support.huaweicloud.com/productdesc-rds/zh-cn_topic_dashboard.html) | RDS 关系型数据库服务产品介绍 |
| [RDS API 参考 — StartFailover](https://support.huaweicloud.com/api-rds/rds_05_0013.html) | 主备倒换 API 接口说明 |
| [CES 监控指标 — RDS](https://support.huaweicloud.com/usermanual-rds-mysql/rds_06_0001.html) | RDS CES 监控指标列表 |
