---
name: huawei-cloud-ces-aom-capacity-assessment
description: "Huawei Cloud capacity assessment. Assesses capacity for instances across 21 services (NAT/RDS/ECS/ELB/EIP/CSS/DDS/DWS/DCS/DMS/TaurusDB/GeminiDB/DC/ER/EVS/EFS Turbo/APIG/DRS/VPCEP/Bandwidth/CCE) by comparing peak/valley fluctuations of monitoring data between entry instances and target instances, calculating pressure coefficients to predict festival traffic ceilings, and giving scale-out recommendations. Data collection uses hcloud (KooCLI) CES commands (CCE and other cloud-native metrics go through AOM). Supports four modes: single-instance historical, full historical, single-instance 近一天（t-24）, full 近一天（t-24）. Trigger words: 容量评估、扩容建议、节日保障、压力系数、峰谷值倍数、预计节日上限、容量预测、capacity assessment、要不要扩容、ECS/RDS/CCE 够不够用."
---

# Huawei Cloud Capacity Assessment

Assesses instances in the Excel capacity template: collects monitoring data (hcloud CES; CCE and other cloud-native metrics via hcloud AOM),
computes peak/valley multiples, pressure coefficients, and expected festival ceilings, decides whether business peaks (festival events)
need scale-out, and writes results back to Excel.

## Core division of labor (must follow)

- **The script does all computation, data collection, and Excel read/write**; the model only orchestrates the flow, selects modes, and reports results.
- The model **must not** manually compute peak/valley or pressure coefficients, and **must not** make logic decisions beyond writing Excel cells.
- The model **must not** investigate root causes of collection failures (§9.3); report failure details to the user as-is.

## Prerequisites: script locations and dependencies

```bash
<SKILL_DIR>/scripts/capacity_cli.py        # Unified CLI entry point
<SKILL_DIR>/scripts/requirements.txt       # Dependency: openpyxl
<SKILL_DIR>/references/metrics.json         # 241-metric registry (Chinese name → CES/AOM metric_name + namespace + dimensions + ceiling + unit)
<SKILL_DIR>/references/troubleshooting-dns.md  # DNS troubleshooting when hcloud cannot connect
<SKILL_DIR>/references/region-map.md          # Chinese region name ↔ region code mapping
<SKILL_DIR>/references/cli-installation-guide.md   # hcloud installation/config (required for review)
<SKILL_DIR>/references/iam-policies.md         # IAM permissions (CES/AOM read-only, required for review)
<SKILL_DIR>/references/verification-method.md  # Verification method (required for review)
<SKILL_DIR>/references/acceptance-criteria.md  # Acceptance criteria (required for review)
<SKILL_DIR>/templates/capacity_assessment_template.xlsx      # Template (the Excel template users take and fill in)
<SKILL_DIR>/tests/test_t24_columns.py        # Offline regression tests (t-24 column mapping + DCS type detection)
```

First-time setup: `pip install -r <SKILL_DIR>/scripts/requirements.txt`

> **Placeholders in the commands below must be replaced before running** — they are not literal paths:
> - `<SKILL_DIR>` = the directory that contains this `SKILL.md` (e.g. `skills/monitoring/ces/huawei-cloud-ces-aom-capacity-assessment`).
> - `<xlsx>` = the full path of the workbook you are assessing (copy `templates/capacity_assessment_template.xlsx` to a writable location first, e.g. `/tmp/capacity.xlsx`).
> - `<region>` / `<region-code>` = region code such as `cn-north-4`; `<row>` = row number; `<name>` = the value to check.
>
> Running a command with the angle brackets left in place fails with "script not found" / "file not found".

Offline tests (no cloud credentials needed): `cd <SKILL_DIR> && python3 -m pytest tests -q`

## Step 0: Expand (auto-fill metrics)

The user copies `templates/capacity_assessment_template.xlsx`, fills in region/实例类型/实例ID/入口实例ID
(one row per instance, including entry instances), then runs `expand`.

**Recommended**: before assessment, run `expand` to auto-fill 关键指标/云服务维度/云服务维度资源ID for each instance row.
(Users may also manually fill these columns and skip expand; expand is the recommended flow to avoid manual errors.)
The user only needs to fill region/实例类型/实例ID/入口实例ID; the tool looks up all supported metrics
from the registry and expands each row into one row per metric (inserting new rows as needed).

For DMS instances, the tool auto-detects the engine subtype (kafka/rabbitmq/rocketmq) via ShowInstance API
(Kafka/RabbitMQ/RocketMQ), falling back to CES ListMetrics probing.
For GeminiDB instances, the tool auto-detects the engine subtype (cassandra/redis) via GaussDBforNoSQL ListInstances,
falling back to CES ListMetrics probing.
For DCS instances, the tool auto-detects the instance type (single/ha/cluster/proxy) via DCS ShowInstance API,
falling back to CES ListMetrics probing; only metrics matching the detected instance type are expanded.

```bash
python3 <SKILL_DIR>/scripts/capacity_cli.py expand <xlsx>
```

Returns: `{expanded_rows, inserted_rows, total_metrics, subtypes_detected, errors}`.
After expand, report the summary to the user (N rows → M rows, K metrics total), then proceed to Phase 2 (assess-all).
- If `errors` contains only `关键指标 already filled` warnings: all rows already expanded, proceed directly to assessment.
- If `errors` contains subtype detection warnings (e.g. "could not detect DMS subtype"): report to user but proceed — all metrics for that service are expanded as a fallback.
- If `ok: false` with real errors (no rows to expand, all rows failed): report to user and stop.

## Four assessment modes

| Mode | Command | Time range |
|---|---|---|
| Single-instance historical | `assess-row --mode historical --start ... --end ...` | user-specified |
| Full historical | `assess-all --mode historical` | user-specified |
| Single-instance 近一天（t-24） | `assess-row --mode t24` | last 24h (automatic) |
| Full 近一天（t-24） | `assess-all --mode t24` | last 24h (automatic) |

Time parameter format: `YYYY-MM-DD HH:MM:SS` (day windows are split by day automatically, peak=max, valley=min).

## Template and metric explanation (user-facing)

When users ask "what is the template / how do I fill it / which metrics are supported", run:

```bash
python3 <SKILL_DIR>/scripts/capacity_cli.py info
```

This command outputs in one shot: Excel template instructions (including the **template file location**) + the list of supported **instance type abbreviations** (to prevent users filling Chinese full names that fail recognition) + the full supported-metric list grouped by 云服务/云服务维度/关键指标.
- **Show the user the complete output of this command verbatim**; do not paraphrase or trim it.
- The output is user-facing and contains no internal command parameters/paths; the model side should not expose internal details.
- The content already covers three key points, pass them through as-is, no extra additions needed:
  1) **expand flow**: the user only fills region/实例类型/实例ID/入口实例ID; run `expand` to auto-fill 关键指标/云服务维度/云服务维度资源ID
     by looking up all supported metrics from the 241-metric registry (one row per metric, inserting rows as needed).
     For DMS, the tool auto-detects the engine subtype (kafka/rabbitmq/rocketmq);
     for GeminiDB, it auto-detects cassandra/redis;
     for DCS, it auto-detects the instance type (single/ha/cluster/proxy).
  2) "资源上限" is an **optional** column: assessment works without it; when absent, the default ceiling is taken from the registry by 实例类型+关键指标
     (some metrics have a default ceiling, some do not; when absent, the ceiling is left blank and the recommendation outputs "现有数据不支持给出建议"); filling it in when known is recommended.
  3) ECS metric note: current ECS assessment metrics come from physical-machine (host) level collection, less accurate than in-instance collection;
     for more accurate ECS metrics, install the Cloud Eye Agent on that ECS.
- When users ask "which regions are supported / how to fill the region column", refer to `references/region-map.md` (Chinese region name ↔ region code mapping, consistent with `resolve_region` in config.py).

## Pre-assessment validation (must follow before Phase 2)

Before running assess, the model **must** perform these checks and interact with the user accordingly:

1. **入口实例ID + 账号组合校验**: every target row must have 入口实例ID filled, and hcloud must be configured with the collection account's AK/SK (see `references/cli-installation-guide.md`).
   - If 入口实例ID is empty for a row: warn the user that **this row will only perform data collection, no pressure-coefficient prediction**. Ask whether to proceed or fill in the entry instance.
   - If hcloud is not configured (AK/SK missing): stop and guide the user through `references/cli-installation-guide.md` first.

2. **时间窗口校验** (historical mode only):
   - If the user requests historical mode but does not provide --start/--end: **prompt the user to fill in the time window**.
   - If the user still does not provide a time window: inform them that the tool will automatically switch to **近一天（t-24）mode** (collects the last 24 hours), and proceed with `--mode t24`.

3. **入口实例关键指标校验**: for each row that has 入口实例ID filled, check whether the entry instance's corresponding row in Excel has 关键指标 filled.
   - If 关键指标 is empty for the entry row: **do not execute the skill immediately**. First remind the user:
     > "入口实例 {instance_id} 的关键指标未填写。建议先运行 expand 自动填充，或手动填写关键指标。也可以不填写——此时压力系数仍会计算但不可靠（入口实例回退到目标指标），扩容建议将输出'入口实例异常，需人工确认'。"
   - If the user chooses to proceed without filling: the assessment runs normally, 压力系数/预计节日上限 are still computed and written (but unreliable), and the 扩容建议 column outputs **"入口实例异常，需人工确认"** instead of a yes/no recommendation.

4. **Mode-specific output columns**:
   - **Historical mode**: output Excel only shows historical columns (峰谷值倍数/压力系数/预计节日上限/资源上限/单位/扩容建议 + M/D峰值、M/D谷值). 近一天（t-24）columns are **not** created.
   - **近一天（t-24）mode**: output Excel only shows 近一天（t-24）columns (近一天（t-24）峰值/近一天（t-24）谷值/近一天（t-24）峰谷值增长倍数/近一天（t-24）压力系数/近一天（t-24）预计节日上限/近一天（t-24）是否需要扩容). Historical columns are **not** created.
    The workbook template spells these six columns `t-24峰值`/`t-24谷值`/`t-24峰谷值增长倍数`/`t-24压力系数`/`t-24预计节日上限`/`t-24是否需要扩容`; both spellings resolve to the same column, so values are written into the template's own columns and no duplicate column is ever appended.

## Workflow: standard flow

Always start with Phase 0 (expand), then proceed through Phase 1 → Phase 2 → Phase 3 → Phase 4.

### Phase 0: Expand (auto-fill metrics)

```bash
python3 <SKILL_DIR>/scripts/capacity_cli.py expand <capacity_assessment_template.xlsx>
```

Reads each row, determines the service type from 实例类型, for DMS auto-detects the subtype,
for DCS auto-detects the instance type (single/ha/cluster/proxy),
looks up all supported metrics from the 241-metric registry, and expands each row into one row per metric
(filling in 关键指标/云服务维度/云服务维度资源ID, inserting new rows as needed).
- Rows that already have 关键指标 filled are skipped (already expanded).
- For DMS, the tool tries ShowInstance on each service (Kafka/RabbitMQ/RocketMQ) to determine the engine type,
  falling back to CES ListMetrics probing with kafka_instance_id/rabbitmq_instance_id/reliablemq_instance_id.
- For GeminiDB, the tool tries GaussDBforNoSQL ListInstances with datastore_type=cassandra/redis to determine the
  engine type, falling back to CES ListMetrics probing with cassandra_cluster_id/redis_cluster_id.
- For DCS, the tool tries DCS ShowInstance to determine the instance type (single/ha/cluster/proxy),
  falling back to CES ListMetrics probing; only metrics matching the detected type are expanded
  (single/ha→实例 only; cluster→实例+数据节点; proxy→Proxy集群-节点).
- For metrics requiring 云服务维度资源ID, the tool queries the cloud to discover all available dimension
  resource IDs (e.g. CCE node hostIDs, DMS Kafka broker IDs, POD names) and creates one row per value.
  For services where the dim_resource_id equals the instance_id (e.g. EIP), it is used directly.
  Because CES `ListMetrics --dim.0` matches the **exact** dimension set, node/broker-level metrics (which
  also carry e.g. dcs_cluster_redis_node) are not returned by an instance-filtered query; the tool then
  retries a namespace-wide listing and keeps only metrics attributed to this instance by its instance
  dimension, so single-node/ha instances are unaffected and no other instance's nodes leak in.
  If discovery still finds nothing (hcloud not available, instance stopped, no sub-resources), the instance
  ID is used as a fallback and the `warnings` array says so — warn the user, since node-level metrics then
  collect as instance-level (or fail).

### Phase 1: Read Excel + validate

```bash
python3 <SKILL_DIR>/scripts/capacity_cli.py read-excel <capacity_assessment_template.xlsx>
```

Returns header columns (with base names), data rows, and required-column validation results (region/实例类型/实例ID/入口实例ID).
- After expand, all rows should have 关键指标/云服务维度/云服务维度资源ID filled in.
- Full mode: rows missing required fields are skipped; only complete rows are assessed.
- Single-instance mode: if that row is missing required fields, stop and inform the user.

### Phase 2: Assess

**Single instance**: run on the specified row (collects both target and entry instances, computes, and returns cells to write):

```bash
python3 <SKILL_DIR>/scripts/capacity_cli.py assess-row <xlsx> --row 2 --mode historical \
  --start "2026-07-01 00:00:00" --end "2026-07-14 23:59:59"
# or 近一天（t-24）:
python3 <SKILL_DIR>/scripts/capacity_cli.py assess-row <xlsx> --row 2 --mode t24
```

**Full** (time-consuming, background execution + polling):

```bash
python3 <SKILL_DIR>/scripts/capacity_cli.py assess-all <xlsx> --mode historical \
  --start "..." --end "..." --background
# returns {"background": true, "pid": ..., "progress": "<xlsx>.assess.log", ...}
python3 <SKILL_DIR>/scripts/capacity_cli.py assess-status --progress <xlsx>.assess.log
```

The background task processes rows one by one and writes everything back to Excel when done (no backup files), finally returning
`skipped_rows` (metric mismatch / unsupported service) and `collection_failures` (collection failed) details.

### Phase 3: Write back to Excel

- `assess-row` outputs `updates` that can be written back via `write-excel`, or let the `assess-all` background task write back uniformly.
- Writes **do not create any backup files**: temp file + atomic replace (`os.replace`); on save failure the `.tmp` is cleaned automatically and the original file is untouched.
- Date peak/valley columns (e.g. `7/1峰值`) are auto-inserted after the 【入口实例ID】 column, sorted by time.

```bash
python3 <SKILL_DIR>/scripts/capacity_cli.py write-excel <xlsx> --updates updates.json
```

**Automatic cleanup of temp files and history (built into the script, no manual work):**
- After `assess-all` finishes in the foreground, `<xlsx>.assess.log` and `<xlsx>.assess.log.out` are deleted automatically.
- The progress file of `assess-all --background` is auto-deleted after `assess-status` reads `done`.
- **No backups are kept**: writing to Excel creates no `.bak-*` backup; on save failure `.tmp` is cleaned. The working directory should always contain only the `<xlsx>` itself — no history/temp residue.
- Manual fallback: `python3 <SKILL_DIR>/scripts/capacity_cli.py cleanup <xlsx>`
  (default `--keep 0`, deletes all `.bak-*`/`.assess.log`/`.assess.log.out`/`.tmp`)

### Phase 4: Report

After every assessment, **must** report the following to the user:
1. **Assessment summary**:
   - Full mode: N rows assessed total, M succeeded, K skipped, W collection failures; results written to Excel.
   - Single-instance mode: that row succeeded/failed, plus the key conclusion (expected festival ceiling / scale-out recommendation).
2. **Full path of the Excel file** (from assess-all's excel_path, or the single-instance mode's xlsx path).
3. **Failure details**: report in table format, merging consecutive row numbers of the same service type.
4. **Reporting status hint (only when collection failures exist)**: when the error in `collection_failures` is
   `该时间窗口内无监控数据` or `返回中未找到该指标`, you must explain to the user —
   **the filled-in key indicator itself is correct and supported by Huawei Cloud monitoring**; the failure usually means
   **the cloud service instance does not report data to the monitoring service** (instance stopped / monitoring not enabled / no data points in the window).
   Suggest the user self-check: whether the instance is running, whether cloud monitoring reporting is enabled, and whether data really exists in the window.
   Do not explain this as "the metric was written wrong", and do not show customers technical fields like metric_name.
- Model behavior constraints (§9.3): do not inspect log files to diagnose; do not analyze code logic to find bugs;
  do not attempt to fix or bypass exceptions; do not re-run the script to retry; only write script results into Excel and report.

## Key formulas (consistent with skill_overview)

- peak = max of all datapoints.max; valley = min(datapoints.max); filter is always max.
- Historical formula: 峰谷值倍数=目标峰值/目标谷值; 压力系数=目标峰谷值倍数/入口峰谷值倍数
  (multiple entries: entry 峰谷值倍数 is the arithmetic mean of all entries); 预计节日上限=压力系数×峰值×(增长倍数-1)+峰值;
  扩容建议=预计节日上限>资源上限×0.8?"是":"否".
- Target and entry use **common dates** for computation.
- 近一天（t-24）mode: **manually filled values take precedence** — if 近一天（t-24）峰值/近一天（t-24）谷值 already exist in the row, use them directly, no collection.
- Units: raw collected units are auto-converted to the display unit in metrics.json before writing.
- Error wording: historical mode "无法计算"/"现有数据不支持给出建议"; 近一天（t-24）mode "无法预测".
- When multiple entry units are incompatible, 压力系数 outputs "多入口实例，但单位不兼容".

### How the entry instance's metric is determined (since v3.4)

- **The entry instance preferentially uses the key indicator from its own row in Excel**
  (实例类型/关键指标/云服务维度/云服务维度资源ID all come from that row;
  region also prefers the entry row's own region, falling back to the target row's region only when the entry row has none);
  only when the entry instance is not in Excel does it fall back to the target row's same metric.
- Computation only depends on 峰谷值倍数 (**a dimensionless ratio peak/valley**), **so the entry metric need not match the target metric,
  nor the unit**. For example, an ECS row can use ELB's "并发连接数" as the entry reference —
  this is exactly the normal use of entry and target being different instance types.
- **Therefore the entry instance must be filled in as a row in the template** (before `expand`), otherwise its own metric cannot be used.
  After `expand`, both the target and entry instances will have multiple rows (one per metric); the entry collection
  finds the entry instance's row by 实例ID and uses that row's metric.

### Valley = 0 explanation (since v3.4)

- If a day/window's valley = 0 (e.g. idle zero values for concurrent connections, bandwidth, etc.),
  峰谷值倍数 = peak/valley divides by zero, outputs "无法计算" (historical) or "无法预测" (T-24),
  and the recommendation outputs "现有数据不支持给出建议".
- This is a **normal formula-level limitation, not a collection failure, not a wrong metric**;
  the datapoints may contain many non-zero points (an exact 0 merely existing during the trough).

## Metrics and resource ceilings

> **A correct key indicator ≠ data exists (important)**: the key indicators in the template are all official metrics
> supported by Huawei Cloud monitoring — not a mistake. But whether an instance has monitoring data depends on whether the
> **cloud service reports to the monitoring service**: when an instance is stopped / not connected / has no data points,
> the query returns "无监控数据" or "未找到该指标". Such failures are not a wrong metric nor a tool problem;
> guide the user to check the cloud service's reporting status in the report.

- `references/metrics.json`: 241 metrics across 21 services,
  keyed by Chinese metric name (with service prefix, e.g. "ECS CPU使用率"); prefix-less aliases (e.g. "CPU利用率" in the template) are also accepted.
  ECS/EVS/Bandwidth/EIP/ELB/DC/DCS/RDS/VPCEP/CCE etc. have been verified as collectible; the rest are organized per Huawei Cloud
  monitoring metric lists, dimensions follow the official lists, not yet verified one by one; correct them with real collections if anomalies occur.
  3 items are still unregistered (official metric_name not public):
  TaurusDB 数据盘使用率 (note: "TaurusDB 磁盘使用率" IS registered, they are different),
  GeminiDB Redis 节点带宽利用率 ("节点入/出带宽利用率" is registered, only the direction-less aggregate is not),
  VPCEP 终端节点每秒新建连接数.
  Rows filling these metrics are marked skipped (metric_mismatch), and the service's supported-metric list is returned for the user to correct.

  **CCE metric note (8 supported, collected via AOM)**: CCE monitoring metrics have no official public metric_name in CES;
  the skill collects them via `hcloud AOM ListSample` (entries in metrics.json carry `"backend": "aom"`), no extra Agent needed.
  All 8 AOM metric_names verified on an account with a real CCE cluster (pre-rename names, as used in ListSample input):
  - Cluster dimension (3): CCE CPU利用率=`cpuUsage`、CCE内存利用率=`memUsedRate`、CCE磁盘使用率=`diskUsedRate`(PAAS.AGGR)
  - Node/master dimension (3): CCE节点CPU利用率/CCE master节点CPU使用率=`cpuUsage`、CCE节点磁盘使用率=`diskUsedRate`(PAAS.NODE)
  - POD dimension (2): CCE POD CPU利用率=`cpuUsage`、CCE POD物理内存使用率=`memUsage`(PAAS.CONTAINER)
  How to fill (auto-filled by `expand`):
  - Cluster-dimension metrics: 【实例ID】= cluster ID, 【云服务维度资源ID】not required.
  - Node/master/POD-dimension metrics: 【实例ID】= cluster ID, 【云服务维度资源ID】= node ID (hostID)/master node ID/POD name (podName).
  - `expand` auto-discovers node hostIDs via AOM ListSeries / CCE ShowClusterNodes, and POD names via AOM ListSeries,
    creating one row per discovered value. If discovery fails, the cluster ID is used as a fallback.
- Each metric in `references/metrics.json` has `ceiling` (resource ceiling) and `unit` fields, used as the **default ceiling**.
- The "资源上限" column in the template is **optional** (assess_row prefers the Excel user-entered value, falling back to the registry only when absent):
  - User filled: the filled value is used and participates normally in recommendation logic.
  - User empty, registry has a default ceiling: use the registry default.
  - User empty, registry has no default (ceiling=null, 133 of 241 metrics): "资源上限" is left blank during assessment,
    recommendation outputs "现有数据不支持给出建议".
- **ECS metric note (already in `info` output, user-facing)**: current ECS assessment metrics come from physical-machine (host) level collection,
  less accurate than in-instance collection; install the Cloud Eye Agent on that ECS for more accurate metrics.

## When hcloud cannot connect (important)

CES metric collection is invoked by the script as `hcloud CES BatchListMetricData --cli-region=<region>`,
CCE and other cloud-native metrics (backend=aom) as `hcloud AOM ListSample --cli-region=<region>`;
`<region>` is the region code (parsed from the --region parameter of capacity_cli.py, e.g. cn-north-4).
If network/timeout errors occur:

1. Self-check first: `python3 <SKILL_DIR>/scripts/capacity_cli.py smoke --region <region-code>`
   (smoke probes **both CES and AOM** backends and reports which one failed)
2. On failure → **troubleshoot DNS first**, do not modify code:
   ```bash
   getent hosts ces.<region-code>.myhuaweicloud.com
   getent hosts aom.<region-code>.myhuaweicloud.com
   ```
   If it resolves to an intranet IP like `100.125.x.x` → look up the public IP with a public DNS and write it into /etc/hosts
   (see `references/troubleshooting-dns.md`, includes verified steps and real public-IP tests; AOM is diagnosed the same as CES, just replace the domain with AOM.).
3. After fixing DNS, re-run the original command.

> Also note: even with DNS OK, some regions may report
> `The IAM user is forbidden in the currently selected region` due to missing IAM permissions; such errors go into
> the `collection_failures` details (the row is written with an "无法计算/无法预测" placeholder), reported by the model to the user as-is;
> they are not script issues to fix.

## Core Commands (lower-level, optional)

- `collect`: single-metric collection, `--t24` or `--start/--end`, `--region` (code).
  Debug peak/valley of a specific instance metric directly.
- `calculate`: pure computation, input JSON `{"mode":"historical","target":{peak,valley,unit},
  "entrances":[{peak,valley,unit}],"ceiling":100,"growth":1.5}`, outputs all metrics.

## Parameter Confirmation

All parameters are confirmed from the user's request or from the workbook itself; do not invent values.

| Parameter | Required for | Description |
|-----------|--------------|-------------|
| `xlsx` (positional) | expand / read-excel / assess-row / assess-all / write-excel / cleanup | Path to the workbook. Copy `templates/capacity_assessment_template.xlsx` to a writable location first. |
| `--region` | collect / smoke | Region code (`cn-north-4`, `cn-east-3`, …). Rows carry Chinese region names, which `references/region-map.md` maps to codes. |
| `--row` | assess-row | Excel row number of the instance to assess. |
| `--mode` | assess-row / assess-all | `historical` (explicit `--start`/`--end`) or `t24` (近一天（t-24）). |
| `--start` / `--end` | historical mode | Time window, `YYYY-MM-DD` (regional timezone, UTC+8 for cn-*). |
| `--period` | collect / assess-* | Sampling period in seconds (default 300). |
| `--updates` | write-excel | JSON file produced by `assess-all` (or hand-written updates). |
| `--progress` | assess-status | Progress log path; defaults to `<xlsx>.assess.log` in `assess-all`. |
| `--background` | assess-all | Run in background and poll with `assess-status`. |
| `--sheet` | all workbook commands | Sheet name (default: the template's `保障重点实例_容量管理模板`). |
| `--hcloud` / `HCLOUD` | all collection commands | Path to the KooCLI executable (default `hcloud` on `PATH`). |
| `--metrics` | all commands | Override `references/metrics.json`. |
| `--endpoint` | all collection commands | Override the CES endpoint (proxy/private-link scenarios). |

## Template structure quick reference

- Sheet name: `保障重点实例_容量管理模板`
- Required columns (user fills): region、实例类型、实例ID、入口实例ID
- **Auto-filled by `expand`**: 关键指标、云服务维度、云服务维度资源ID
  (the user no longer needs to fill these; run `expand` to auto-populate them based on the 241-metric registry)
- **The entry instance should also be filled as a row in the template** (with its own 实例类型);
  entry collection prefers that row's metric; an entry absent from the template can only fall back to the target's metric.
- Output columns (matched by header name, missing columns auto-created):
  Historical: 峰谷值倍数/压力系数/预计节日上限/资源上限/单位/扩容建议 + M/D峰值、M/D谷值
  近一天（t-24）: 近一天（t-24）峰值/近一天（t-24）谷值/近一天（t-24）峰谷值增长倍数/近一天（t-24）压力系数/近一天（t-24）预计节日上限/近一天（t-24）是否需要扩容
- Optional but useful: 活动增长倍数 (default 1.0)
- **Optional column: 资源上限** (assessment works without it, more accurate with it) — when absent the tool takes the default ceiling
  from the registry by 实例类型+关键指标; some metrics have defaults, some do not (when neither exists, "资源上限" stays blank
  and the recommendation outputs "现有数据不支持给出建议").
  Fill in the ceiling when known; assess_row prefers the filled value.

## References

| File | Contents |
|------|----------|
| `references/metrics.json` | 241-metric registry: Chinese name → CES/AOM `metric_name` + namespace + dimensions + default ceiling + unit |
| `references/region-map.md` | Chinese region name ↔ region code mapping |
| `references/troubleshooting-dns.md` | DNS troubleshooting when `hcloud` cannot reach CES/AOM |
| `references/cli-installation-guide.md` | `hcloud` (KooCLI) installation and profile configuration |
| `references/iam-policies.md` | Read-only IAM permissions required for CES/AOM |
| `references/verification-method.md` | How the skill is verified (offline tests + live smoke) |
| `references/acceptance-criteria.md` | Acceptance criteria |
| `templates/capacity_assessment_template.xlsx` | The Excel template users copy and fill in |
| `tests/test_t24_columns.py` | Offline regression tests (t-24 column mapping, DCS instance-type detection, JSON null payloads) |