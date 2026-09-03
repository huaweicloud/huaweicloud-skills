---
name: huawei-cloud-hss-query
description: >-
  Query and manage Huawei Cloud HSS (Host Security Service) for daily security inspection and incident response.
  Covers host assets, vulnerabilities, security baselines, intrusion alerts (trojan/brute-force), login audit logs,
  risk scoring, and alert handling status updates. Read-only queries plus alert status marking — no isolation or
  antivirus actions. Use this skill when the user needs to inspect host security risks, investigate suspected
  intrusion, review vulnerability/baseline reports, or handle security alerts.
  Triggers include: 主机安全, HSS, Host Security Service, 安全巡检, 漏洞查询, 安全基线,
  入侵告警, 木马检测, 暴力破解, 登录审计, 告警处置, 风险诊断, host security inspection,
  vulnerability scan, baseline check, intrusion alert, trojan detection, brute force,
  login audit, alert handling, risk diagnosis, security event response.
tags: [huawei-cloud hss security inspection vulnerability baseline intrusion]
---

# Huawei Cloud HSS Host Security Skill

## Overview

This skill provides AI Agent capabilities for Huawei Cloud HSS (Host Security Service / 主机安全服务),
covering daily security inspection, risk diagnosis, and alert handling. It supports querying host assets,
vulnerabilities, security baselines, intrusion alerts (trojans, brute-force attacks), and login audit logs,
plus updating alert handling status — all via hcloud CLI.

**Scope boundaries:**
- ✅ Query: host assets, vulnerabilities, baselines, intrusion alerts, login audit logs
- ✅ Diagnose: risk scoring, high-risk vulnerability analysis, abnormal login analysis
- ✅ Manage: update alert handling status (mark as handled, ignored, etc.)
- ❌ Does NOT create or delete host resources
- ❌ Does NOT execute isolation, antivirus, or other high-risk actions
- ❌ Does NOT perform real-time blocking or kill processes

## Prerequisites

1. **hcloud CLI** installed and authenticated with valid AK/SK credentials.
   - Installation guide: see `references/cli-installation-guide.md`
   - Verify: `hcloud configure list` shows a valid profile
2. **HSS agent** deployed on target ECS instances (HSS must be enabled in the console)
3. **IAM permissions**: HSS read permissions for query operations, HSS write permissions for alert handling.
   - See `references/iam-policies.md` for least-privilege policy
4. **Region**: HSS is region-specific. Use `--cli-region` to specify the target region (e.g., `{your-region}`)

## Workflow

```
1. Identify target → region, project_id, optional host_id filter
2. Query phase → list assets / vulnerabilities / baselines / alerts / login logs
3. Diagnose phase → risk score, high-risk items, abnormal login patterns
4. Handle phase → update alert handling status (requires user confirmation)
5. Output → structured JSON risk list + readable summary report
```

## Core Commands

### 1. Host Assets (主机资产)

List all protected hosts with agent status, OS type, and risk flags:

```bash
hcloud HSS ListHostStatus --cli-region={region} --project_id={project_id} \
  [--host_id={host_id}] [--host_name={host_name}] [--os_type={linux|windows}] \
  [--agent_status={installed|not_installed|online|offline}] \
  [--has_vul=true] [--has_intrusion=true] [--has_baseline=true] \
  [--asset_value={important|common|test}] [--limit=10] [--offset=0]
```

Show host statistics (total hosts, protected count, risk distribution):

```bash
hcloud HSS ShowHostsStatistics --cli-region={region} --project_id={project_id}
```

Query risk status for specific hosts:

```bash
hcloud HSS ListHostsRisk --cli-region={region} --project_id={project_id} \
  --host_id_list.1={host_id_1} [--host_id_list.2={host_id_2}]
```

### 2. Vulnerabilities (漏洞)

List all vulnerabilities with filtering by type, status, severity:

```bash
hcloud HSS ListVulnerabilities --cli-region={region} --project_id={project_id} \
  [--vul_id={vul_id}] [--vul_name={vul_name}] [--cve_id={cve_id}] \
  [--type={linux_vul|windows_vul|web_cms|app_vul|urgent_vul}] \
  [--status={vul_status}] [--handle_status={handle_status}] \
  [--repair_priority={critical|high|medium|low}] \
  [--asset_value={important|common|test}] [--limit=10] [--offset=0]
```

List vulnerabilities on a specific host:

```bash
hcloud HSS ListHostVuls --cli-region={region} --project_id={project_id} \
  --host_id={host_id} [--type={linux_vul|windows_vul|web_cms|app_vul|urgent_vul}] \
  [--limit=10] [--offset=0]
```

List hosts affected by a specific vulnerability:

```bash
hcloud HSS ListVulHosts --cli-region={region} --project_id={project_id} \
  --type={linux_vul|windows_vul|web_cms|app_vul|urgent_vul} --vul_id={vul_id} \
  [--limit=10] [--offset=0]
```

Show vulnerability details (choose by type):

```bash
# Linux vulnerability
hcloud HSS ShowLinuxVulDetail --cli-region={region} --project_id={project_id} \
  --vul_id={vul_id} --limit=10 --offset=0

# Windows vulnerability
hcloud HSS ShowWindowsVulDetail --cli-region={region} --project_id={project_id} \
  --vul_id={vul_id} --limit=10 --offset=0

# Web-CMS vulnerability
hcloud HSS ShowCmsVulDetail --cli-region={region} --project_id={project_id} \
  --vul_id={vul_id} --limit=10 --offset=0
```

Show vulnerability statistics:

```bash
hcloud HSS ShowVulStatics --cli-region={region} --project_id={project_id}
```

### 3. Security Baselines (安全基线)

Show baseline check overview (last check time, check stats, pass rate, top risks):

```bash
hcloud HSS ShowBaselineOverview --cli-region={region} --project_id={project_id}
```

Show baseline statistics:

```bash
hcloud HSS ShowBaselineStatistic --cli-region={region} --project_id={project_id}
```

List hosts affected by a specific baseline check rule:

```bash
hcloud HSS ListHostCheckRules --cli-region={region} --project_id={project_id} \
  --check_name={check_name} --standard={cn_standard|hw_standard} --host_id={host_id} \
  [--check_rule_name={rule_name}] [--limit=10] [--offset=0]
```

> ⚠️ `--standard` 为必填参数。

Show security check report for a specific host:

```bash
hcloud HSS ShowSecurityCheckHostReport --cli-region={region} --project_id={project_id} \
  --host_id={host_id} --scan_time={scan_time_ms}
```

> ⚠️ `--scan_time` 为必填参数（毫秒级时间戳）。

Show risk configuration detail:

```bash
hcloud HSS ShowRiskConfigDetail --cli-region={region} --project_id={project_id} \
  --check_name={check_name} --standard={cn_standard|hw_standard} \
  [--host_id={host_id}]
```

> ⚠️ `--standard` 为必填参数（`cn_standard`=等保合规标准，`hw_standard`=云安全实践标准）。

### 4. Intrusion Alerts — Trojan & Malware (木马/恶意软件告警)

Query alert event history with filtering by event type, severity, handling status:

```bash
hcloud HSS ListEventHandleHistory --cli-region={region} --project_id={project_id} \
  [--event_type={event_type}] [--event_class_ids.1={event_class_id}] \
  [--severity={critical|high|medium|low}] [--handle_status={handled|unhandled}] \
  [--host_ip={ip}] [--host_name={name}] [--attack_tag={tag}] \
  [--asset_value={important|common|test}] [--limit=10] [--offset=0]
```

**Common event_class_ids for malware:**

| event_class_id | Description |
|----------------|-------------|
| `av_1002` | Virus (病毒) |
| `av_1003` | Worm (蠕虫) |
| `av_1004` | Trojan (木马) |
| `av_1005` | Botnet (僵尸网络) |
| `av_1006` | Backdoor (后门) |
| `av_1010` | Rootkit |
| `av_1011` | Ransomware (勒索软件) |
| `av_1015` | Webshell |
| `av_1016` | Mining software (挖矿软件) |

List host protection history:

```bash
hcloud HSS ListHostProtectHistoryInfo --cli-region={region} --project_id={project_id} \
  --start_time={start_time_ms} --end_time={end_time_ms} [--limit=10] [--offset=0] \
  [--host_id={host_id}] [--file_path={path}]
```

> ⚠️ **`--start_time` / `--end_time` 为必填参数**（毫秒级时间戳，相差不超过 30 天）；`--host_id` 可选。

List antivirus-protected hosts:

```bash
# List antivirus-protected hosts (scan_type: quick/full; start_type: now/period)
hcloud HSS ListAntiVirusHost --cli-region={region} --project_id={project_id} \
  --limit=10 --offset=0 --scan_type={quick|full} --start_type={now|period} \
  [--host_id={host_id}] [--policy_id={policy_id}]
```

> ⚠️ **`--limit` / `--offset` / `--scan_type` / `--start_type` 为必填参数**。
> `--scan_type` 枚举：`quick`（快速扫描）/ `full`（全盘扫描）；`--start_type` 枚举：`now`（立即启动）/ `period`（周期启动）。其他值（如 `all`/`manual`/`auto`）会被 API 静默忽略并返回空结果。

### 5. Intrusion Alerts — Brute Force (暴力破解告警)

Query brute-force attack events (login_0001 = attempt, login_0002 = success):

```bash
hcloud HSS ListEventHandleHistory --cli-region={region} --project_id={project_id} \
  --event_class_ids.1=login_0001 --event_class_ids.2=login_0002 \
  [--severity={critical|high|medium|low}] [--handle_status={handled|unhandled}] \
  [--host_ip={ip}] [--limit=10] [--offset=0]
```

List weak password detection results:

```bash
hcloud HSS ListWeakPasswordUsers --cli-region={region} --project_id={project_id} \
  [--host_id={host_id}] [--limit=10] [--offset=0]
```

### 6. Login Audit Logs (登录审计日志)

Query common login IPs:

```bash
hcloud HSS ListLoginCommonIp --cli-region={region} --project_id={project_id} \
  [--ip_addr={ip}]
```

Query common login locations:

```bash
hcloud HSS ListLoginCommonLocation --cli-region={region} --project_id={project_id} \
  [--area_code={area_code}]
```

> ⚠️ 这两个操作仅支持 `--ip_addr` / `--area_code` 过滤器（实测 `--host_id`/`--limit`/`--offset` 不支持），不可加分页参数。

### 7. Risk Diagnosis (风险诊断)

Query overall risk score:

```bash
hcloud HSS ShowRiskScore --cli-region={region} --project_id={project_id}
```

Query risk status for specific hosts:

```bash
hcloud HSS ListHostsRisk --cli-region={region} --project_id={project_id} \
  --host_id_list.1={host_id_1}
```

### 8. Update Alert Handling Status (告警处置) — ⚠️ Mutating, Requires Confirmation

Handle alert events (mark as handled, ignored, etc.):

```bash
hcloud HSS ChangeEvent --cli-region={region} --project_id={project_id} \
  --operate_event_list.1.event_class_id={event_class_id} \
  --operate_event_list.1.event_id={event_id} \
  --operate_event_list.1.event_type={event_type} \
  --operate_event_list.1.occur_time={occur_time_ms} \
  --operate_type={operate_type}
```

> ⚠️ `--operate_type` 是**顶层参数**（不属于 operate_event_list 数组内）；数组中 `event_class_id`/`event_id`/`event_type`/`occur_time` 均必填。

**operate_type values for ChangeEvent:**
- `mark_as_handled` — Mark as handled (标记已处理)
- `ignore` — Ignore (忽略)
- `add_to_alarm_whitelist` — Add to alarm whitelist (加入告警白名单)
- `add_to_login_whitelist` — Add to login whitelist (加入登录白名单)
- `unhandle` — Restore to unhandled (恢复未处理)
- `do_not_ignore` — Cancel ignore (取消忽略)
- `remove_from_alarm_whitelist` — Remove from alarm whitelist (删除告警白名单)
- `remove_from_login_whitelist` — Remove from login whitelist (删除登录白名单)

> ⚠️ ⛔ `isolate_and_kill`（隔离查杀）、`do_not_isolate_or_kill` 虽为 API 支持值，但**本技能明确不执行隔离/杀毒等高危动作**，AI 不得使用。

Update vulnerability handling status:

```bash
hcloud HSS ChangeVulStatus --cli-region={region} --project_id={project_id} \
  --operate_type={ignore|not_ignore|immediate_repair|manual_repair|verify|add_to_whitelist} \
  --data_list.1.vul_id={vul_id} --host_data_list.1.host_id={host_id}
```

> ⚠️ 漏洞与主机通过 `--data_list.[N].vul_id` + `--host_data_list.[N].host_id` 关联传递（**没有顶层 `--vul_id`/`--host_id` 参数**）。

**⚠️ Both ChangeEvent and ChangeVulStatus are mutating operations. Always prompt the user for confirmation before executing.**

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--cli-region` | Yes | Target region | `{your-region}` |
| `--project_id` | Yes | Project ID (auto-detected if omitted) | Auto from CLI profile |
| `--host_id` | No | Filter by host ID | `xxxxxxxx-xxxx-xxxx` |
| `--severity` | No | Risk severity filter | `critical`, `high`, `medium`, `low` |
| `--type` | No | Vulnerability type | `linux_vul`, `windows_vul`, `web_cms` |
| `--repair_priority` | No | Vulnerability repair priority | `critical`, `high`, `medium`, `low` |
| `--handle_status` | No | Alert handling status filter | `handled`, `unhandled` |
| `--event_class_ids.N` | No | Event class ID filter (indexed) | `av_1004` (trojan) |
| `--limit` | No | Page size (default 10) | `10` |
| `--offset` | No | Page offset (default 0) | `0` |
| `--enterprise_project_id` | No | Enterprise project filter | `0` for default |
| `--asset_value` | No | Asset importance filter | `important`, `common`, `test` |

## Output Format

All commands return JSON by default. For inspection reports, the skill aggregates multiple query results into a structured risk summary:

```json
{
  "inspection_time": "2026-08-28T10:00:00Z",
  "region": "{region}",
  "host_summary": { "total": 10, "protected": 8, "at_risk": 3 },
  "vulnerabilities": { "critical": 2, "high": 5, "medium": 12, "low": 8 },
  "baselines": { "pass_rate": "85%", "failed_rules": 7 },
  "alerts": { "unhandled_trojan": 1, "unhandled_brute_force": 3 },
  "risk_score": 72,
  "recommendations": ["Fix 2 critical vulnerabilities on host xxx", "Handle 1 unhandled trojan alert"]
}
```

## Reference Documents

- `references/cli-installation-guide.md` — hcloud CLI installation and authentication
- `references/iam-policies.md` — Least-privilege IAM policies for HSS
- `references/verification-method.md` — Verification and testing methods
- `references/dataflow-diagram.md` — Data flow diagram
- `references/acceptance-criteria.md` — Acceptance criteria
- `references/hss-event-class-reference.md` — HSS event class ID reference

## KooCLI Command Format Standard

```bash
hcloud HSS ListHostStatus --cli-region={region} --project_id={project_id} [--key=value ...]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | `HSS` (exact KooCLI service name) | `HSS` |
| Operation name | PascalCase | `ListHostStatus`, `ShowVulStatics`, `ChangeEvent` |
| Region parameter | `--cli-region=<value>` | `--cli-region={region}` |
| Simple parameter | `--key=value` | `--host_id=xxx` |
| Indexed parameter | `--key.1=value1` | `--host_id_list.1=xxx` |
