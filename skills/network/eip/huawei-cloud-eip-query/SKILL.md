---
name: huawei-cloud-eip-query
description: |
  Huawei Cloud EIP (Elastic Public IP) query and bandwidth monitoring skill using hcloud CLI (KooCLI).
  Supports listing Elastic Public IPs, viewing EIP details, and querying Cloud Eye (CES) bandwidth
  monitoring data for EIPs: bandwidth usage rate (%), inbound/outbound traffic (Byte), peak/avg
  bandwidth (bit/s), across a configurable time range with aggregation period.
  Use when users need to query EIP resources, check EIP bandwidth utilization, analyze inbound/outbound
  traffic, monitor bandwidth peaks/averages, or troubleshoot EIP bandwidth issues.
  Triggers: "EIP query", "EIP list", "弹性公网IP查询", "EIP带宽监控", "带宽使用率", "流入流量",
  "流出流量", "带宽峰值", "带宽均值", "EIP监控", "带宽监控", "EIP bandwidth", "traffic monitoring",
  "CES metrics", "Cloud Eye metrics"
---

# Huawei Cloud EIP Query and Bandwidth Monitoring

## 1. Overview

### Functional Overview

This skill combines EIP resource query (VPC EIP service) and EIP bandwidth monitoring
(Cloud Eye / CES service) into one workflow. Users can first list and inspect Elastic
Public IPs, then query their real-time or historical bandwidth monitoring data — usage
rate, inbound/outbound traffic, and peak/avg bandwidth — to support daily inspection,
traffic analysis, and fault troubleshooting.

### Architecture Diagram

```text
User Request → hcloud CLI (KooCLI)
    ├── hcloud eip ListPublicips/v2      → EIP resource list
    ├── hcloud eip ShowPublicip/v2       → EIP detail (bandwidth_id, size, status)
    └── hcloud ces ShowMetricData        → Cloud Eye monitoring data (SYS.VPC)
```

### Application Scenarios

- Query EIP resources and their basic attributes (IP, status, bandwidth, type)
- Query EIP bandwidth usage rate (outbound/inbound) as percentage
- Query inbound/outbound traffic volume (Byte) over a time range
- Query bandwidth peak (`filter=max`) and average (`filter=average`) values (bit/s)
- Historical monitoring query with configurable start/end time and aggregation period
- Daily inspection, traffic analysis, capacity planning, fault troubleshooting

### User Scenario Examples

1. **Basic EIP list**: "List all Elastic Public IPs in my account"
2. **EIP detail**: "Show details of EIP 0521f035-..."
3. **Bandwidth usage**: "What is the bandwidth usage rate of EIP X in the last 24 hours?"
4. **Traffic analysis**: "Show inbound/outbound traffic of EIP X for the last 7 days"
5. **Peak/avg bandwidth**: "What is the peak and average bandwidth of EIP X today?"

## 2. Prerequisites

### CLI Installation and Verification

Before starting any operation, install and verify Huawei Cloud CLI (hcloud):

```bash
> **⚠️ Mandatory: every `hcloud` command in this skill MUST be wrapped with `skill-quality-cli run --skill-name huawei-cloud-eip-query -- ` — bare `hcloud` calls are strictly forbidden.**

skill-quality-cli run --skill-name huawei-cloud-eip-query -- hcloud version
```

If not installed, follow the installation guide in `references/cli-installation-guide.md`.

### Configuration Method

> **Credential configuration is the user's responsibility.** This skill does not execute
> any credential configuration commands. Configure credentials in your terminal, then use
> `hcloud configure list` to verify.

Reference configuration command:

```bash
skill-quality-cli run --skill-name huawei-cloud-eip-query -- hcloud configure init
```

### Security Rules

**[MUST]** Before invoking any CLI command, check credential status:

```bash
skill-quality-cli run --skill-name huawei-cloud-eip-query -- hcloud configure list
```

- **NEVER** read, echo, or print AK/SK values
- **NEVER** ask the user to input AK/SK in the conversation or command line
- **ONLY** use `hcloud configure list` to verify credential status

If no valid configuration exists, STOP and ask the user to configure credentials in their terminal.

### IAM Permission Requirements

This skill is read-only. Required permissions:

- `vpc:publicIps:list` - List EIPs
- `vpc:publicIps:get` - Get EIP details
- `ces:metrics:list` - List Cloud Eye metrics
- `ces:metricData:get` - Get Cloud Eye metric data

Detailed policies: `references/iam-policies.md`

### Permission Failure Handling

If an operation fails with a permission error, guide the user to `references/iam-policies.md`
and help them configure the required custom IAM policy.

## 3. KooCLI Command Format Standard

```bash
skill-quality-cli run --skill-name huawei-cloud-eip-query -- hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]
```

| Item | Description | Example |
| ------ | ------------- | --------- |
| Service | EIP for VPC EIP; CES for Cloud Eye | `EIP`, `CES` |
| Operation | PascalCase (optional version suffix) | `ListPublicips/v2`, `ShowMetricData` |
| Region | `--cli-region=<value>` always required | `--cli-region=cn-north-4` |
| Parameters | `--key=value` simple; `--dim.0=key,value` indexed for CES dims | `--publicip_id=xxx` |

## 4. Core Workflow

### Step 1: List EIPs

```bash
skill-quality-cli run --skill-name huawei-cloud-eip-query -- hcloud eip ListPublicips/v2 --cli-region={region} --limit={limit}
```

Returned fields include `id`, `public_ip_address`, `status`, `type`, `bandwidth_id`,
`bandwidth_name`, `bandwidth_size`. Use the `id` as `publicip_id` for the next steps.

### Step 2: Show EIP Detail (optional)

```bash
skill-quality-cli run --skill-name huawei-cloud-eip-query -- hcloud eip ShowPublicip/v2 --cli-region={region} --publicip_id={publicip_id}
```

Returns full EIP detail including `bandwidth_id`, `bandwidth_size`, `bandwidth_share_type`,
`create_time`, `enterprise_project_id`.

### Step 3: List Available Metrics (optional)

```bash
skill-quality-cli run --skill-name huawei-cloud-eip-query -- hcloud ces ListMetrics --cli-region={region} --namespace=SYS.VPC
```

EIP monitoring metrics are under namespace `SYS.VPC`, dimensioned by `publicip_id`
(shared bandwidth: `bandwidth_id`):

| Metric | Description | Unit |
| -------- | ------------- | ------ |
| `upstream_bandwidth` | Outbound bandwidth | bit/s |
| `downstream_bandwidth` | Inbound bandwidth | bit/s |
| `upstream_bandwidth_usage` | Outbound bandwidth usage rate | % |
| `downstream_bandwidth_usage` | Inbound bandwidth usage rate | % |
| `up_stream` | Outbound traffic | Byte |
| `down_stream` | Inbound traffic | Byte |

### Step 4: Query Bandwidth Monitoring Data

```bash
skill-quality-cli run --skill-name huawei-cloud-eip-query -- hcloud ces ShowMetricData \
  --cli-region={region} \
  --namespace=SYS.VPC \
  --metric_name={metric_name} \
  --dim.0=publicip_id,{publicip_id} \
  --from={from_ms} \
  --to={to_ms} \
  --period={period} \
  --filter={filter}
```

**Or use the bundled script (recommended)**, which runs the above command, aggregates
peak/avg, and formats output:

```bash
skill-quality-cli run --skill-name huawei-cloud-eip-query -- python3 scripts/eip_query.py list --limit {limit} --region {region}
skill-quality-cli run --skill-name huawei-cloud-eip-query -- python3 scripts/eip_query.py metric --publicip_id {publicip_id} --metric upstream_bandwidth_usage --filter average --period 300 --region {region}
```

Typical queries per feature point:

### 1) Bandwidth usage rate (%)

```bash
skill-quality-cli run --skill-name huawei-cloud-eip-query -- hcloud ces ShowMetricData --cli-region=cn-north-4 --namespace=SYS.VPC \
  --metric_name=upstream_bandwidth_usage \
  --dim.0=publicip_id,{publicip_id} \
  --from=$(date -d '-24 hours' +%s)000 --to=$(date +%s)000 \
  --period=300 --filter=average
```

### 2) Inbound/outbound traffic (Byte)

```bash
skill-quality-cli run --skill-name huawei-cloud-eip-query -- hcloud ces ShowMetricData --cli-region=cn-north-4 --namespace=SYS.VPC \
  --metric_name=down_stream \
  --dim.0=publicip_id,{publicip_id} \
  --from=$(date -d '-24 hours' +%s)000 --to=$(date +%s)000 \
  --period=3600 --filter=sum
```

### 3) Peak/avg bandwidth (bit/s)

```bash
# Peak
skill-quality-cli run --skill-name huawei-cloud-eip-query -- hcloud ces ShowMetricData --cli-region=cn-north-4 --namespace=SYS.VPC \
  --metric_name=upstream_bandwidth \
  --dim.0=publicip_id,{publicip_id} \
  --from=$(date -d '-24 hours' +%s)000 --to=$(date +%s)000 \
  --period=300 --filter=max

# Average
skill-quality-cli run --skill-name huawei-cloud-eip-query -- hcloud ces ShowMetricData --cli-region=cn-north-4 --namespace=SYS.VPC \
  --metric_name=downstream_bandwidth \
  --dim.0=publicip_id,{publicip_id} \
  --from=$(date -d '-24 hours' +%s)000 --to=$(date +%s)000 \
  --period=300 --filter=average
```

### 4) Time-range query with aggregation period

Use `--from` and `--to` (Unix milliseconds) plus `--period` (1/60/300/1200/3600/14400/86400
seconds). Set `--from` at least one aggregation period earlier than `now`.

### Step 5: Format Results

Present monitoring data as a compact table: metric name, points count, peak, average,
and unit. Flag anomalies (e.g., usage rate > 80%) and suggest next steps.

## 5. Core Commands

| Command | Purpose | Backend |
| --------- | --------- | --------- |
| `python3 scripts/eip_query.py list` | List EIPs | hcloud CLI |
| `python3 scripts/eip_query.py show --publicip_id {id}` | EIP detail | hcloud CLI |
| `python3 scripts/eip_query.py metric --publicip_id {id}` | EIP bandwidth monitoring | hcloud CLI |
| `python3 scripts/eip_query.py metric --bandwidth_id {id}` | Shared-bandwidth monitoring | hcloud CLI |

### EIP List

```bash
skill-quality-cli run --skill-name huawei-cloud-eip-query -- python3 scripts/eip_query.py list --region cn-north-4 --limit 50
```

| Parameter | Required | Description |
| ----------- | ---------- | ------------- |
| `--region` | No | Region (default cn-north-4) |
| `--limit` | No | Max records |
| `--json` | No | Raw JSON output |

### EIP Detail

```bash
skill-quality-cli run --skill-name huawei-cloud-eip-query -- python3 scripts/eip_query.py show --publicip_id 0521f035-c5b1-4c97-9491-7378696e522b --region cn-north-4
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--publicip_id` | Yes | EIP resource id |

### Bandwidth Monitoring

```bash
skill-quality-cli run --skill-name huawei-cloud-eip-query -- python3 scripts/eip_query.py metric --publicip_id {publicip_id} \
  --metric upstream_bandwidth_usage --filter average --period 300 \
  --from {from_ms} --to {to_ms} --region cn-north-4
```

| Parameter | Required | Description |
| ----------- | ---------- | ------------- |
| `--publicip_id` | Yes* | EIP id (dimension `publicip_id`) |
| `--bandwidth_id` | Yes* | Bandwidth id (dimension `bandwidth_id`; use when EIP uses shared bandwidth) |
| `--metric`/`-m` | No | Metric name, repeatable; default all six EIP metrics |
| `--filter` | No | average/variance/min/max/sum (default average; max=peak) |
| `--period` | No | 1/60/300/1200/3600/14400/86400 s (default 300) |
| `--from` | No | Start time, Unix ms (default now - 1h) |
| `--to` | No | End time, Unix ms (default now) |
| `--region` | No | Region (default cn-north-4) |
| `--json` | No | Raw JSON output |

\* Exactly one of `--publicip_id` / `--bandwidth_id` is required.

## 6. Parameter Confirmation

### hcloud ces ShowMetricData

| Parameter | Required | Description |
| ----------- | ---------- | ------------- |
| `--cli-region` | Yes (auto) | Region, agent fills automatically |
| `--namespace` | Yes | `SYS.VPC` for EIP metrics |
| `--metric_name` | Yes | `upstream_bandwidth_usage`, `downstream_bandwidth`, `up_stream`, etc. |
| `--dim.0` | Yes | `publicip_id,{id}` or `bandwidth_id,{id}` |
| `--from` | Yes | Start time, Unix ms |
| `--to` | Yes | End time, Unix ms |
| `--period` | Yes | 1/60/300/1200/3600/14400/86400 s |
| `--filter` | Yes | average/variance/min/max/sum |
| `--project_id` | Optional | Project ID; falls back to profile |

### hcloud eip ListPublicips/v2

| Parameter | Required | Description |
| ----------- | ---------- | ------------- |
| `--cli-region` | Yes (auto) | Region |
| `--limit` | No | Max records |
| `--marker` | No | Pagination marker |
| `--id.[N]`, `--public_ip_address.[N]`, `--port_id.[N]` | No | Filters |
| `--enterprise_project_id` | No | Enterprise project filter |
| `--ip_version` | No | IP version filter |
| `--project_id` | No | Project ID |

### hcloud eip ShowPublicip/v2

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes (auto) | Region |
| `--publicip_id` | Yes | EIP resource id |

## 7. Verification Method

Skill verification and testing are described in `references/verification-method.md`, including
environment checks, permission checks, and per-command functional verification.

## 8. Best Practices

1. **From list to metrics**: always start with `list` to obtain a valid `publicip_id`.
2. **Peak/avg**: use `filter=max` for peak and `filter=average` for average bandwidth.
3. **Time ranges**: use appropriate `--period` per range — 300s for last 24h, 3600s for 7 days.
4. **Set `--from` one period early**: Cloud Eye aggregates to the period start; querying within
   a single period window can return empty results.
5. **Shared bandwidth**: if the EIP is inside a shared bandwidth, dimension by `bandwidth_id`.
6. **Read-only**: this skill never mutates EIP or bandwidth resources.
7. **Alert thresholds**: usage rate > 80% sustained suggests bandwidth upgrade analysis.

## 9. Reference Documents

- `references/cli-installation-guide.md` - hcloud CLI installation and configuration
- `references/iam-policies.md` - Required IAM permissions and policy JSON
- `references/eip-metrics-reference.md` - EIP CES metrics detail
- `references/dataflow-diagram.md` - Mermaid data flow diagram
- `references/verification-method.md` - Verification method
- `references/acceptance-criteria.md` - Acceptance criteria

## 10. Notes

### Security Notes

- Credentials must never be hardcoded or printed; use `hcloud configure` or environment
  variables set outside the skill.
- This skill is **read-only**. It never changes EIP, bandwidth, or monitoring configuration.

### Limitations

- Monitoring data has limited retention (typically up to a few months depending on period).
- Newly created EIPs may take several minutes to start reporting metrics.
- Metric timestamps use Unix milliseconds (UTC).
- Shared-bandwidth EIPs report metrics under the `bandwidth_id` dimension; using the wrong
  dimension returns no data.

### Common Pitfalls

| Symptom | Cause | Fix |
| --------- | ------- | ----- |
| Empty datapoints | `from`/`to` inside one aggregation period | set `from` ≥ one period earlier |
| Permission error | Missing `ces:metricData:get` / `vpc:publicIps:list` | see `references/iam-policies.md` |
| No data for EIP | Wrong dimension (publicip_id vs bandwidth_id) | check EIP `bandwidth_share_type` |
| Wrong naming | Metric typo | run `ListMetrics --namespace=SYS.VPC` |
