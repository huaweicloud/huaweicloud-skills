---
name: huawei-cloud-agentarts-obs-diagnosis
description: |
  Observability no-data diagnosis skill for Huawei Cloud AgentArts agent-ops platform.
  Systematically diagnoses missing metrics, logs, and traces/sessions in agent-ops by
  checking subscription metadata, data pipeline (APM/AOM/LTS), query parameters, and
  authentication. Generates root-cause analysis and fix recommendations.
  Triggers include: "AgentArts no data", "metrics no data", "logs no data",
  "traces no data", "session no data", "obs diagnosis", "可观测诊断", "无数据诊断",
  "查不到指标", "查不到日志", "调用链无数据", "agent-ops 无数据"
tags:
  - agentarts
  - observability
  - diagnosis
  - agent-ops
  - no-data
---

# Huawei Cloud AgentArts Observability No-Data Diagnosis

## Overview

This skill systematically diagnoses **missing metrics, logs, and traces/sessions** in
Huawei Cloud AgentArts agent-ops platform. It follows a three-phase diagnostic flow:
subscription metadata check → data pipeline troubleshooting → query parameter validation,
covering three data sources: APM (traces/metrics), AOM (metrics), and LTS (logs).

### Architecture

```
Application (OTel SDK/Collector)
  │
  ├── Traces:  OTEL SDK → APM (OTLP) → deliverConfig → Kafka → agent-ops
  ├── Metrics: Application → AOM (Prometheus) → agent-ops
  └── Logs:    Application → LTS → agent-ops (requires logGroup/logStream metadata)
```

### Data Sources and Metadata

| Data Type | Source | Required Metadata |
|-----------|--------|-------------------|
| Traces/Sessions | APM | `apmBusiness`, `apmToken` |
| Metrics | AOM | `promInstance`, `aomAccessCode` |
| Logs | LTS | `logGroup`, `logStream` |

## Prerequisites

### 1. Huawei Cloud Credentials

```bash
export HUAWEI_ACCESS_KEY="<your-access-key-id>"
read -rs HUAWEI_SECRET_KEY; export HUAWEI_SECRET_KEY
export HUAWEI_REGION="cn-north-4"
```

### 2. hcloud CLI (KooCLI)

Install: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html

### 3. IAM Permissions

See `references/iam-policies.md` for least-privilege policy.

## Workflow

### Step 1: Identify Missing Data Type

Use AskUserQuestion to determine which data type is missing:

| Option | Data Type | Data Source |
|--------|-----------|-------------|
| A | Metrics (metrics) | AOM / APM |
| B | Logs (logs) | LTS |
| C | Traces/Sessions (traces/session) | APM |
| D | All missing | All sources |

Record symptoms: complete vs partial absence, error codes, onset time.

### Step 2: Confirm Environment Context

| Parameter | Default | Description |
|-----------|---------|-------------|
| `region` | `cn-north-4` | Query region (must match ingestion region) |
| `domain_id` | — | IAM domain ID |
| `project_id` | — | Project ID for LTS queries |
| `start_time` / `end_time` | — | Millisecond timestamps (13 digits, NOT 10-digit seconds) |

### Step 3: Check Subscription Metadata (Phase 1 — Always First)

Missing subscription metadata is the **most common root cause** of no-data issues.

**Check APM business and token:**

```bash
hcloud APM ListBusiness --cli-region=cn-north-4
```

If no business exists → APM not subscribed. Create business:
```bash
hcloud APM CreateBusiness --cli-region=cn-north-4 \
  --name="obs-diagnosis-check" \
  --display_name="obs-diagnosis-check" \
  --descp="diagnosis" \
  --cmdb_datasource_type=OTEL
```

Verify business token:
```bash
hcloud APM ShowToken --cli-region=cn-north-4 \
  --x-business-id={business_id}
```

**Check AOM Prometheus instance and access code:**

```bash
hcloud AOM ListPromInstance --cli-region=cn-north-4 --Enterprise-Project-Id=0
hcloud AOM ListAccessCode --cli-region=cn-north-4
```

If no PromInstance → AOM not configured. Create Prometheus instance
(`--prom_type` must be one of `ECS`/`CCE`/`REMOTE_WRITE`/`CLOUD_SERVICE`/`ACROSS_ACCOUNT`;
`--region` header is required and must match `--cli-region`):
```bash
hcloud AOM CreatePromInstance --cli-region=cn-north-4 \
  --prom_name="obs-diagnosis" \
  --prom_type=REMOTE_WRITE \
  --region=cn-north-4
```

**Check LTS log groups and streams:**

```bash
hcloud LTS ListLogGroups --cli-region=cn-north-4
hcloud LTS ListLogStreams --cli-region=cn-north-4 --log_group_id={group_id}
```

If no logGroup/logStream → LTS not subscribed for agent-ops.

### Step 4: Diagnose by Data Type (Phase 2 — Pipeline Check)

#### 4A. Metrics No-Data Diagnosis

Check pipeline bottom-up:

1. **Application side**: Is OTEL metrics SDK / Prometheus exporter configured?
2. **AOM side**:
   ```bash
   hcloud AOM ListPromInstance --cli-region=cn-north-4 --Enterprise-Project-Id=0
   hcloud AOM ListAccessCode --cli-region=cn-north-4
   hcloud AOM ListMetadataAomPromGet --cli-region=cn-north-4
   ```
   - Prometheus instance valid?
   - Access code valid?
   - Endpoint reachable?
3. **Query side**: Use Prometheus query to verify data exists:
   ```bash
   hcloud AOM ListInstantQueryAomPromGet --cli-region=cn-north-4 \
     --query="up" \
     --prom_instance_id={prom_id}
   ```
4. **agent-ops filter**: Check metric_name matches (`resource_tokens`, `model_tokens`,
   `session_tokens`, `trace_tokens`), filter labels match (`gen_ai_resource_type`,
   `resource_id`, `model_id`).

#### 4B. Logs No-Data Diagnosis

1. **Application side**: Is ICAgent / OTEL logs exporter configured?
2. **LTS side**:
   ```bash
   hcloud LTS ListLogGroups --cli-region=cn-north-4
   hcloud LTS ListLogStreams --cli-region=cn-north-4 --log_group_id={group_id}
   hcloud LTS ListLogs --cli-region=cn-north-4 \
     --log_group_id={group_id} \
     --log_stream_id={stream_id} \
     --start_time=1720000000000 \
     --end_time=1720600000000
   ```
3. **Query parameters**: Check `agentRunId`, `agentId`, `traceId`, `logType`,
   keyword syntax (LTS query language).
4. **Error codes**:
   - `LTS.2446` → Unsupported query syntax — fix keyword syntax
   - `403` → Permission denied — check agency token (`ops_admin_trust`)

#### 4C. Traces/Sessions No-Data Diagnosis

1. **Application side**:
   ```bash
   hcloud APM SearchAgent --cli-region=cn-north-4 --x-business-id={business_id}
   ```
   Is OTEL SDK configured with correct endpoint and token?
2. **APM deliverConfig**:
   - Is `deliver_otel_trace=true` in deliverConfig?
   - Is Kafka reachable (bootstrap-servers, SASL_SSL, topic exists)?
3. **APM data verification**:
   ```bash
   hcloud APM SearchTransaction --cli-region=cn-north-4 \
     --x-business-id={business_id} \
     --start_time=1720000000000 \
     --end_time=1720600000000
   ```
4. **agent-ops query side** (API only — not in KooCLI):
   ```bash
   curl -X POST ${AGENT_OPS_ENDPOINT}/v1/ops/observation/traces \
     -H "Authorization: Bearer ${IAM_TOKEN}" \
     -H "Content-Type: application/json" \
     -d '{"start_time": 1720000000000, "end_time": 1720600000000}'
   ```

### Step 5: Common Checks (All Data Types)

1. **Timestamp format**: Must be 13-digit milliseconds (10-digit seconds → no data)
2. **Region consistency**: Ingestion region must match query region
3. **Authentication**: IAM token / AppCode valid? 401 → expired, 403 → insufficient permission. `${IAM_TOKEN}` 需在运行期由 IAM token / AppCode 获取后替换（见上 Step 4 agent-ops 查询命令）；未替换则为占位符，照抄请求必返回 401。
4. **Permission check**:
   ```bash
   hcloud IAM ListPoliciesV5 --cli-region=cn-north-4
   ```

### Step 6: Generate Diagnostic Report

See `references/diagnostic-report-template.md` for the report format.

## Core Commands

| Command | Purpose | Mode |
|---------|---------|------|
| `hcloud APM ListBusiness --cli-region=cn-north-4` | List APM businesses | CLI |
| `hcloud APM ShowBusinessDetail --cli-region=cn-north-4` | Show business details | CLI |
| `hcloud APM ShowToken --cli-region=cn-north-4` | Get business token | CLI |
| `hcloud APM ShowAccessPoint --cli-region=cn-north-4` | Get access point | CLI |
| `hcloud APM SearchAgent --cli-region=cn-north-4` | Search agents | CLI |
| `hcloud APM SearchTransaction --cli-region=cn-north-4` | Search transactions (traces) | CLI |
| `hcloud APM ShowSpanSearch --cli-region=cn-north-4` | Search spans | CLI |
| `hcloud APM ListOpenRegion --cli-region=cn-north-4` | List open regions | CLI |
| `hcloud AOM ListPromInstance --cli-region=cn-north-4 --Enterprise-Project-Id=0` | List Prometheus instances | CLI |
| `hcloud AOM ListAccessCode --cli-region=cn-north-4` | List access codes | CLI |
| `hcloud AOM ListInstantQueryAomPromGet --cli-region=cn-north-4` | Instant Prometheus query | CLI |
| `hcloud AOM ListRangeQueryAomPromGet --cli-region=cn-north-4` | Range Prometheus query | CLI |
| `hcloud AOM ListMetadataAomPromGet --cli-region=cn-north-4` | List Prometheus metadata | CLI |
| `hcloud LTS ListLogGroups --cli-region=cn-north-4` | List log groups | CLI |
| `hcloud LTS ListLogStreams --cli-region=cn-north-4` | List log streams | CLI |
| `hcloud LTS ListLogs --cli-region=cn-north-4` | List logs | CLI |
| `hcloud IAM ListPoliciesV5 --cli-region=cn-north-4` | List IAM policies | CLI |
| `POST {AGENT_OPS_ENDPOINT}/v1/ops/observation/traces` | Query traces in agent-ops | API |
| `POST {AGENT_OPS_ENDPOINT}/v1/ops/observation/metrics/trend` | Query metric trends | API |

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `region` | Yes | Query region | `cn-north-4` |
| `business_id` | Yes (traces) | APM business ID | From ListBusiness |
| `prom_instance_id` | Yes (metrics) | AOM Prometheus instance ID | From ListPromInstance |
| `log_group_id` | Yes (logs) | LTS log group ID | From ListLogGroups |
| `log_stream_id` | Yes (logs) | LTS log stream ID | From ListLogStreams |
| `start_time` | Yes | Start time (ms timestamp) | `1720000000000` |
| `end_time` | Yes | End time (ms timestamp) | `1720600000000` |
| `metric_name` | No (metrics) | Metric name to query | `resource_tokens` |
| `keywords` | No (logs) | LTS keyword search | `error AND timeout` |
| `trace_id` | No (traces) | Trace ID filter | — |

## KooCLI Command Format Standard

```bash
hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | KooCLI Service name (uppercase) | `APM`, `AOM`, `LTS`, `IAM` |
| Operation name | PascalCase | `ListBusiness`, `ShowToken` |
| Region parameter | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--business_id=xxx` |

## Reference Documents

- `references/iam-policies.md` — Least-privilege IAM policies
- `references/cli-installation-guide.md` — hcloud CLI installation guide
- `references/verification-method.md` — Verification methods and API status
- `references/dataflow-diagram.md` — Mermaid data flow and diagnostic flow
- `references/acceptance-criteria.md` — Acceptance criteria for diagnosis
- `references/diagnostic-report-template.md` — Diagnostic report template

## Edge Cases

| Scenario | Handling |
|----------|---------|
| All data types missing | Check subscription status first, then network connectivity |
| Partial data missing (some apps) | Check agent deployment, service.name mapping |
| LTS.2446 error | Fix keyword syntax (escaping, quotes, operators) |
| 403 error (non-claw) | Check IAM tenant permissions and subscription status |
| 403 error (claw) | Check agency (`ops_admin_trust`) and STS configuration |
| RESOURCE_NOT_EXIST | Resource records missing — confirm `CreateClawTenantRelation` |
| Metadata missing | Subscribe first (`SubscribeOpsObservation`) |
| Timestamp 10 digits | Convert to 13-digit milliseconds |
| Region mismatch | Use same region for ingestion and query |

## Notes

- **Priority order**: Subscription metadata → data pipeline → query parameters → permissions
- **Most common root cause**: Missing subscription metadata (apmBusiness, promInstance, logGroup)
- **Timestamp pitfall**: 10-digit seconds instead of 13-digit milliseconds
- **Credential security**: Never hardcode AK/SK. Read from env vars or CLI profile.
- **Least privilege**: See `references/iam-policies.md` for required permissions.
