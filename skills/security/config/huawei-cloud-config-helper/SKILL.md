---
name: huawei-cloud-config-helper
description: "Queries Huawei Cloud Config service for global resource inventory, resource configurations, resource schemas, advanced SQL queries, and built-in compliance rules. Read-only. Use this skill when the user needs to query cloud resources, audit configurations, check compliance, inventory assets, analyze resource relationships, or run complex SQL resource queries. Triggers include: Config, 配置审计, 资源查询, 资源审计, 合规规则, 合规检查, 资源盘点, 资源Schema, 高级查询, SQL查询, 云上资产, resource inventory, compliance rule, resource schema, SQL query."
tags:
  - huawei-cloud-config
  - resource-query
  - compliance-rule
  - resource-schema
  - sql-query
---

# Huawei Cloud Config Helper

> **⚠️ Execution Method (Must Read): This skill executes queries via local Python scripts. Using hcloud, curl, or other CLI tools or direct API calls is prohibited.**
>
> - Query scripts are located under the skill directory `scripts/config/`
> - All scripts are inside the skill package. **You must use `skill action=exec` to execute them; do not run them directly in a shell**
> - **All paths are relative to the skill directory, which is the directory where this SKILL.md resides**

## Overview 概述

This skill is a standalone read-only query skill that uses local Python scripts to call the Huawei Cloud Python SDK to query the Config service, providing:

1. 查询资源概览（各服务/类型/区域的资源数量统计）
2. 查询资源 Schema（资源结构定义，含字段名、类型、描述）
3. 按条件通过 SQL 查询资源（高级查询，仅支持 `resources` 表）
4. 查询预置合规规则（Config 内置策略定义）

This skill does NOT handle the following:

1. Creating, modifying, or deleting any resources or compliance rules
2. Guessing or fabricating information that has not been queried

Before writing SQL or analyzing security posture, read the reference docs:

| File | Description |
|:-----|:------------|
| `references/knowledge.md` | 资源类型映射表、Region 映射、各服务安全知识索引 |
| `references/sql-example.json` | SQL 查询示例集合，编写 SQL 前必读 |
| `references/service/config.md` | Config 核心概念 |
| `references/service/vpc.md` | VPC 安全知识 |
| `references/service/iam.md` | IAM 安全知识 |
| `references/service/obs.md` | OBS 安全知识 |
| `references/iam-policies.md` | 最小权限 IAM 策略（Config ReadOnlyAccess） |
| `references/verification-method.md` | 验证方法 |
| `references/acceptance-criteria.md` | 验收标准 |

## Prerequisites 前置条件

**Environment Variables:**

| Variable | Required | Description |
|------|------|------|
| HW_ACCESS_KEY | Yes* | Huawei Cloud AK (preferred; fallback: HUAWEICLOUD_AK; only requires `Config ReadOnlyAccess` permission) |
| HW_SECRET_KEY | Yes* | Huawei Cloud SK (preferred; fallback: HUAWEICLOUD_SK) |
| HW_SECURITY_TOKEN | No | Required when using temporary AK/SK |
| HW_IGNORE_SSL_VERIFICATION | No | Set to `true` to disable TLS certificate verification (only for intranet/proxy with self-signed certificates) |
| PROXY_URL | No | Proxy URL, e.g. `http://user:pass@host:port` (intranet access); falls back to HTTPS_PROXY/HTTP_PROXY |

\* Either `HW_ACCESS_KEY`/`HW_SECRET_KEY` (preferred) or `HUAWEICLOUD_AK`/`HUAWEICLOUD_SK` (fallback) must be set. The scripts check `HW_ACCESS_KEY`/`HW_SECRET_KEY` first, then fall back to `HUAWEICLOUD_AK`/`HUAWEICLOUD_SK`.

**Do not output the values of the above environment variables.**

**Dependencies:** `pip install -r requirements.txt`（huaweicloudsdkcore、huaweicloudsdkconfig、urllib3）

See `references/iam-policies.md` for the least-privilege IAM policy.

## Workflow 工作流

### Prerequisite: Environment Setup 前置步骤

1. Confirm `HW_ACCESS_KEY` / `HW_SECRET_KEY` (or fallback `HUAWEICLOUD_AK` / `HUAWEICLOUD_SK`) are set (without printing values)
2. Install dependencies: `pip install -r requirements.txt`
3. Run the resource summary query first to confirm connectivity

### Scenario 1: 查询资源概览 Resource Summary

1. Read `references/knowledge.md` to map user intent to provider/region
2. Execute:
   ```bash
   skill action=exec: skill://.venv/Scripts/python3.exe skill://scripts/config/query_Config_resource_summary.py [--provider=<provider>] [--region_id=<region_id>]
   ```
   - `--provider`: 可选，只查询某云服务的资源概览（如 `obs`、`vpc`），也支持 `provider.type` 形式（如 `obs.buckets`）
   - `--region_id`: 可选，只查询某区域（如 `cn-north-4` 北京四、`cn-east-3` 上海一、`global` 全局）
3. Verify: output is a JSON array with `provider`、`type`、`region_id`、`cnt` fields

### Scenario 2: 查询资源 Schema Resource Schema

1. Identify the resource type in `provider.type` format (e.g. `obs.buckets`, `ecs.cloudservers`, `iam.users`, `vpc.securityGroups`)
2. Execute:
   ```bash
   skill action=exec: skill://.venv/Scripts/python3.exe skill://scripts/config/query_Config_resource_schema.py --resource_type=<provider.type>
   ```
3. Use the returned field names/types to prepare SQL in Scenario 3

### Scenario 3: 按条件 SQL 查询资源 SQL Resource Query

1. Query the resource Schema first (Scenario 2) to confirm available fields
2. Read `references/sql-example.json` for query patterns
3. Execute:
   ```bash
   skill action=exec: skill://.venv/Scripts/python3.exe skill://scripts/config/query_Config_resource_by_sql.py --sql="<SQL>"
   ```
   - SQL 只能查询 `resources` 表；支持标准 SELECT/WHERE/GROUP BY/ORDER BY，数组函数（`transform`/`filter`/`any_match`/`contains`），日期函数（`date_diff`/`date_parse`）
   - SQL 语句用双引号包裹，内部字符串用单引号
   - 示例：`--sql="select id, name, provider, type, properties from resources where region_id = 'cn-north-4'"`
4. If the result is empty, run Scenario 1 first to confirm the actual resource distribution
5. Common top-level fields (`name`, `created`, `updated`, `tag`, `project_id`) are collected by Config uniformly and do NOT appear in `properties`/Schema — do not treat them as missing fields

### Scenario 4: 查询预置合规规则 Built-in Compliance Rules

1. Execute:
   ```bash
   skill action=exec: skill://.venv/Scripts/python3.exe skill://scripts/config/query_Config_builtin_rule.py [--keyword=<keyword>] [--limit=<n>]
   ```
   - `--keyword`: 过滤关键词，对规则名称、描述及 keywords 做忽略大小写的子串匹配（如 `obs`、`vpc`）
   - `--limit`: 限制返回数量，默认 20
2. Map rules to security dimensions (加密静态数据、保护配置、强制执行最低权限、限制网络访问等，完整维度见 `references/knowledge.md`)
3. Analyze resource compliance by combining rule conditions with SQL queries from Scenario 3

## Core Commands 核心命令

All commands are executed via `skill action=exec` with the skill venv Python:

```bash
# Windows
skill://.venv/Scripts/python3.exe skill://scripts/config/<script>.py [OPTIONS]
# Linux / macOS
skill://.venv/bin/python3 skill://scripts/config/<script>.py [OPTIONS]
```

| Script | Purpose | Key Options |
|--------|---------|-------------|
| `query_Config_resource_summary.py` | 资源概览统计 | `--provider`, `--region_id` |
| `query_Config_resource_schema.py` | 资源 Schema 查询 | `--resource_type` (required) |
| `query_Config_resource_by_sql.py` | SQL 高级查询 | `--sql` (required) |
| `query_Config_builtin_rule.py` | 预置合规规则查询 | `--keyword`, `--limit` |

Output: JSON (UTF-8, `ensure_ascii=False`). Empty results print `没有找到数据` and exit with code 0; failures print the error and exit with code 1.

## Parameter Confirmation 参数确认

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--cli-region` | No | CLI/SDK 区域标识，SDK 默认 `cn-north-4`（Config 为全局服务，固定使用该 endpoint） | `cn-north-4` |
| `--provider` | No (Scenario 1) | 云服务标识，支持 `provider.type` 形式 | `obs`, `obs.buckets` |
| `--region_id` | No (Scenario 1) | 资源所在区域，`global` 表示全局资源 | `cn-north-4`, `global` |
| `--resource_type` | Yes (Scenario 2) | 资源类型标识，格式 `provider.type`，区分大小写 | `vpc.securityGroups` |
| `--sql` | Yes (Scenario 3) | 高级查询 SQL，双引号包裹、内部单引号 | `select id, name from resources where provider = 'ecs'` |
| `--keyword` | No (Scenario 4) | 合规规则过滤关键词，忽略大小写的子串匹配（名称/描述/keywords） | `obs` |
| `--limit` | No (Scenario 4) | 返回数量限制，默认 20 | `10` |

## Reference Documents 参考文档

- [Knowledge Base](references/knowledge.md) — 资源类型映射表、Region 映射、各服务安全知识索引
- [SQL Examples](references/sql-example.json) — SQL 查询示例集合
- [Config Concepts](references/service/config.md) — Config 核心概念
- [VPC Security](references/service/vpc.md) — VPC 安全知识
- [IAM Security](references/service/iam.md) — IAM 安全知识
- [OBS Security](references/service/obs.md) — OBS 安全知识
- [IAM Policies](references/iam-policies.md) — Least-privilege credential model
- [Verification Method](references/verification-method.md) — Verification method details
- [Acceptance Criteria](references/acceptance-criteria.md) — Acceptance criteria

## Notes

1. This skill only provides read-only query capabilities; it does not perform any write operations
2. 严禁在日志、控制台输出 AK/SK 等敏感信息；AK 仅需 `Config ReadOnlyAccess` 最小权限
3. All scripts must be executed via `skill action=exec`; do not run them directly in a shell
4. SQL 资源类型名称区分大小写（如 `securityGroups`），先查 Schema 确认
5. 大结果集缓存到本地文件，避免重复请求

