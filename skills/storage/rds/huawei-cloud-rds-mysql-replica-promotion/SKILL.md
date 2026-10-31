---
name: huawei-cloud-rds-mysql-replica-promotion
description: |
  Huawei Cloud RDS for MySQL risk reduction skill that converts a single instance to a primary/standby (HA) instance via the hcloud CLI.
  Use this skill when the user wants to convert a Huawei Cloud RDS for MySQL single instance to a primary/standby (HA) instance, upgrade database high availability, or eliminate single-point-of-failure risk.
  Trigger: User mentions "单机转主备", "高可用升级", "single to HA", "convert to primary/standby"
tags: [ huawei-cloud, rds, high-availability ]
version: 1.0.0
license: MIT
---

# Huawei Cloud RDS Single-to-HA Conversion

## Overview

Use the `hcloud` (KooCLI) command-line tool to convert a Huawei Cloud RDS for MySQL single instance to a primary/standby (HA) instance, with strict precondition checks, an optional pre-conversion manual backup, conversion task polling, and result verification. This conversion is **irreversible**, so the workflow requires explicit user confirmation before executing the change step, and presents the risks and impact of the conversion up front.

## Prerequisites

- Python >= 3.9
- hcloud >= 7.2.2 with AKSK authentication configured (`hcloud configure init`)
- The target RDS for MySQL instance **MUST** currently be a `Single` instance in `ACTIVE` state

## Workflow

Copy the checklist below and track progress:

```markdown
- [ ] Step 0: Risk Disclosure and Confirmation
- [ ] Step 1: Environment Check
- [ ] Step 2: Region Confirmation (optional)
- [ ] Step 3: Instance Discovery and Selection (optional)
- [ ] Step 4: Availability Zone Discovery and Selection (optional)
- [ ] Step 5: Precondition Check
- [ ] Step 6: Cost Assessment
- [ ] Step 7: Pre-conversion Monitoring Baseline
- [ ] Step 8: Execute Single-to-HA Conversion
- [ ] Step 9: Result Confirmation and Monitoring Comparison
- [ ] Step 10: Workflow Summary
```

**Step 0: Risk Disclosure and Confirmation**

* **MUST** read [risks-and-impact.md](references/risks-and-impact.md) and present its **complete content** to the user — do **NOT** summarize or omit any section, table, or note. The section-coverage checklist below mirrors the document's structure; every item **MUST** be presented:
  * Section 1: Inherent Risks of a Single-Instance Deployment (the R-001..R-005 risk table)
  * Section 2: Capability Comparison: Single vs Primary/Standby (the comparison table)
  * Section 3: Operational Impact of Converting to Primary/Standby (the impact table, the "Why CPU rises" note, and the "Instance status during the conversion" note)
  * Section 4: Cost Explanation (the billing modes table, the prepaid price-difference calculation, and the other costs note)
  * Section 5: Rollback Guidance
* **MUST** ask the user to explicitly confirm after presenting the complete risk disclosure
* If the user does not confirm or chooses to exit, **MUST** terminate the workflow without any cloud operation
* The risk disclosure is informational; it does not replace the final explicit confirmation in Step 8

**Step 1: Environment Check**

* **MUST** check whether the Python programming language is installed
* **MUST** check whether the hcloud command-line tool is installed
* **MUST** check whether the hcloud command-line tool has authentication configured
  * A successful JSON response indicates authentication is configured; a DNS or authentication error indicates it is not configured
* If any check fails, **MUST** report the missing items and fix instructions to the user and terminate the workflow

**Step 2: Region Confirmation (optional)**

The `--region` is a **global** parameter used by every script in the workflow (Steps 3-9). Each parameter value in the workflow **MUST** be confirmed exactly once and **MUST NOT** be re-confirmed.

* Branch first on what the user already provided when triggering the skill:
  * **Region already provided by the user** (fully explicit): this step is skipped entirely — do **NOT** echo the region or request confirmation; the region value will be confirmed at Step 5 (all-provided path) or at the step where it is first used (partial-provided path)
  * **Not provided**: this step is **required** — **MUST** ask the user to provide the region code (e.g. `cn-north-4`) and explain that it is required by every script in the workflow; the user's input **is** the confirmation for this parameter — **MUST NOT** ask the user to confirm again after input
* Record the value as `--region` for all subsequent script invocations
* Once `--region` is confirmed (via trigger-time provision or interactive input), later steps **MUST** reference it as-is and **MUST NOT** re-confirm it

**Step 3: Instance Discovery and Selection (optional)**

* Branch first on what the user already provided when triggering the skill:
  * **Instance ID already provided by the user** (fully explicit): this step is skipped entirely — do **NOT** echo the instance ID or request confirmation; the instance ID will be confirmed at Step 5 (all-provided path). The verification that the instance exists with `type=Single` and `status=ACTIVE` is done by the read-only `pre_check.py` in Step 5 before any change; if that check fails, the workflow terminates with the reason.
  * **Not provided**: follow the discovery flow below (list instances, present the table, ask the user to select)
* For the discovery flow:
  * Run the [list_instances.py](scripts/list_instances.py) script with `--region <region>` (confirmed in Step 2) to list all MySQL instances in the region
    * The script prints instances as structured JSON (fields include: `id`, `name`, `type` Single/Ha/Replica, `status`, `datastore.version`, `flavor_ref`, `availability_zone`, `charge_info.charge_mode`)
  * **MUST** present the instances to the user in **table** form (formatted by the Agent from the JSON output), including at least: instance ID, instance name, instance type (Single/Ha/Replica, i.e., whether it is single-node), status, and billing mode
  * **MUST** present the instance table to the user and ask them to select the target instance ID to convert
  * The user's selection **is** the confirmation for the instance ID — **MUST NOT** ask the user to confirm again after selection
* Each parameter value **MUST** be confirmed exactly once across the workflow; the `--region` (global, confirmed in Step 2) is referenced as-is

**Step 4: Availability Zone Discovery and Selection (optional)**

* Branch first on what the user already provided when triggering the skill:
  * **Target AZ already provided by the user** (fully explicit): this step is skipped entirely — do **NOT** echo the target AZ or request confirmation; the target AZ will be confirmed at Step 5 (all-provided path). The verification that the target AZ is available is done by the read-only `pre_check.py` in Step 5 before any change; if that check fails, the workflow terminates with the reason.
  * **Not provided**: follow the discovery flow below (list AZs, present the table, ask the user to select)
* For the discovery flow:
  * Run the [list_azs.py](scripts/list_azs.py) script with `--region <region>` (confirmed in Step 2) to list all availability zones in the region
    * The script prints availability zones as structured JSON (fields include: `zoneName`, `zoneState.available`)
  * **MUST** present the availability zones to the user in **table** form (formatted by the Agent from the JSON output), including availability zone IDs and their availability status
  * **MUST** present the availability zone table to the user and explain: the target availability zone for the standby node **MUST be available**; by default the standby zone **should differ** from the instance's current availability zone (cross-AZ disaster recovery, as recommended), but choosing the **same AZ as the current one is allowed** (shortest intra-AZ latency) — the choice is the user's
  * The user's selection **is** the confirmation for the target AZ — **MUST NOT** ask the user to confirm again after selection
* Each parameter value **MUST** be confirmed exactly once across the workflow; the `--region` (global, confirmed in Step 2) is referenced as-is

**Step 5: Precondition Check**

Call the [pre_check.py](scripts/pre_check.py) script to verify all preconditions, as follows:

* Ask the user how to configure the command-line parameters:
  * **MUST** list the command-line parameter details, including: parameter name, required/optional, default value, parameter description, etc.
  * **MUST** have the user provide `--instance-id` (confirmed in Step 3) and `--target-az` (confirmed in Step 4); the `--region` (confirmed in Step 2) is referenced as-is
  * Confirmation rule (each parameter confirmed exactly once):
    * **All-provided path** (all three parameters were provided at trigger time): **MUST** echo the three confirmed values (`--region`, `--instance-id`, `--target-az`) and request user confirmation before running `pre_check.py` — this is the sole confirmation point for these parameters on this path
    * **Interactive path** (one or more parameters were obtained via Steps 2/3/4 discovery): run `pre_check.py` directly — the parameters were already confirmed by the user's input/selection in Steps 2/3/4; **MUST NOT** re-echo and request confirmation
* Run the [pre_check.py](scripts/pre_check.py) script with `--region <region>`, `--instance-id <iid>`, `--target-az <az>`, and `--output rds_single_to_ha_result_precheck.json`
* The script verifies in order: the instance is `Single` and `ACTIVE`, the flavor supports HA and the target availability zone is available, and automatic backups are enabled
* The report's `instance_status` entry carries the instance name, current availability zone, and charge mode; use them for the Step 8 display
* If any check fails, the script reports the reason and writes a report; **MUST** present the failure information to the user and terminate the workflow

**Step 6: Cost Assessment**

* Assess the cost increase of converting the single instance to HA, based on the single instance flavor, storage, and billing mode from the Step 5 pre-check report (`instance_status.flavor_ref`, `instance_status.volume_type`, `instance_status.volume_size`, `instance_status.charge_mode`):
  * Run the [rds_cost_estimate.py](scripts/rds_cost_estimate.py) script in **compare mode** with `--region <region>`, `--compare-single-ha`, `--spec-code <flavor_ref>`, `--storage-size-gb <volume_size>`, `--storage-type <volume_type>`, `--charge-mode <charge_mode>` (from the Step 5 pre-check report's `instance_status.charge_mode`; `postPaid` quotes only on-demand prices, `prePaid` only monthly/yearly prices), and `--output rds_cost_estimate_result.json`
  * The script derives the corresponding HA spec from the single spec (x86 appends `.ha`; ARM replaces `.single` with `.ha`), quotes both specs for compute and storage filtered to the instance's charge mode, and reports the single price, HA price, price delta, and the HA multiple (about 2x)
  * The on-demand price is a **true on-demand quote** (matching the console page price); the storage volume is quoted per spec and is higher for HA than for single (about +60% monthly/yearly, +10% on-demand) — state this scope to the user
* **MUST** present the comparison result to the user in **table** form; present only the price lines that actually carry values in the report (on-demand table when `on_demand` is non-null, monthly/yearly table when `period_pricing` is non-empty) and note the charge-mode filter
* The assessment is read-only; it never creates any resource
* BSS quoting goes through the **global BSS channel** (`--cli-region=cn-north-1`); the real instance region is carried in `product_infos.N.region` and does **not** affect the quote. If the CLI raises a "region not supported" type error on a non-`cn-north-1` region, that is a **BSS channel-layer issue**, not a quote-business error — see [cost-estimation.md](references/cost-estimation.md) for the failure-mode interpretation
* Present the result and continue; the final explicit confirmation for the conversion itself still happens in Step 8

**Step 7: Pre-conversion Monitoring Baseline**

* Run the [rds_monitor.py](scripts/rds_monitor.py) script to capture a monitoring baseline of the instance before conversion:
  * Run with `--region <region>`, `--instance-id <iid>`, and `--output rds_monitor_baseline.json`
  * The script uses a 300-second default window (covering one full 5-minute CES collection cycle) and reports CPU utilization, memory utilization, disk utilization, IOPS, connection usage, and replication delay (null for the single instance)
* **MUST** present the baseline snapshot to the user; note that it is taken from the single instance before conversion
* If the baseline cannot be captured (CES has no data or the script fails), record it truthfully as "no data" and continue; the comparison in Step 9 will mark the missing metrics accordingly

**Step 8: Execute Single-to-HA Conversion**

This step is **irreversible** (it changes the cloud instance from `Single` to `Ha` and roughly doubles the cost). It requires explicit **user confirmation**.

* Present the confirmed parameters to the user: `--instance-id`, `--target-az` (may be the same AZ as the current one, chosen by the user in Step 4), and the instance billing mode (from the Step 5 pre-check report)
* Present the conversion impact and cost information (see [risks-and-impact.md](references/risks-and-impact.md)): irreversibility, roughly doubled cost, storage capacity doubling with storage cost rising, brief CPU rise, backup storage cost
* Billing mode explanation: for prepaid (prePaid) instances, the script automatically carries `is_auto_pay=true` and Huawei Cloud auto-charges the price difference from the account — ensure the account balance is sufficient; pay-per-use (postPaid) instances do not need this price-difference payment
* **MUST** obtain explicit user confirmation before running the conversion command; if the user does not confirm, **MUST NOT** continue
* Backup handling (ask the user, default is to back up):
  * **MUST** explain to the user: by default the conversion performs a pre-conversion manual backup first; the manual backup occupies backup storage on the cloud and incurs backup storage cost after the free quota
  * **MUST** tell the user how long one backup roughly takes before asking whether to keep it, sourced in this order:
    * Latest automatic backup duration: query `ListBackups --backup_type=auto` and use the first record's `begin_time`/`end_time` difference (the API returns records `begin_time`-descending; a full backup of the same instance takes a similar time)
    * If no automatic backup exists, use the latest manual backup record's duration the same way
    * If no backup record exists at all, estimate from the storage size (GB) × 1024 / 100 MB/s and label it conservative ("actual usually shorter")
  * Ask the user whether to keep the manual backup. If the user chooses **not to back up**, run with `--skip-backup` to convert directly (the automatic backup policy still applies and is recommended as a fallback); if the user keeps the backup, run without `--skip-backup` (same as the current default behavior)
* Run the [convert.py](scripts/convert.py) script with `--region <region>`, `--instance-id <iid>`, `--target-az <az>`, `[--skip-backup]`, and `--output rds_single_to_ha_result.json`
  * The script performs the pre-conversion manual backup first (unless `--skip-backup` is given), then performs the conversion and blocks until it finishes (typically about 10 minutes total)
  * The script persists the conversion status (`backup_id` / `job_id`, or `order_id` for prepaid instances) to `<output>.state.json` so that processes killed by shell/session timeout can be resumed
  * When the backup is skipped, the state is persisted directly in the `job` phase without a `backup_id`
  * **MUST** judge the conversion result from the report's `conversion.final_status` (and the non-empty `conversion`/`verification` sections), **NOT** from the process exit code — the script reports failure details in the report even when it exits 0
  * For prepaid (prePaid) instances, the API returns an `order_id` (BSS order) instead of a `job_id`; the script polls the **instance state** (`MODIFYING INSTANCE TYPE` → `type=Ha` + `status=ACTIVE`) instead of the job, so there is no percentage progress — the conversion finishes in about 10 minutes and the result is judged by the same `conversion.final_status`
* **MUST NOT** pipe the long-running scripts (`convert.py`, `resume.py`) through `| tail -N` (e.g. `2>&1 | tail -60`): the scripts stream their progress logs to stderr in real time, while `tail` buffers until EOF, so when the process is killed by a shell/session timeout before EOF all logs are swallowed and the shell tool reports empty stdout/stderr/exit output. Run the command directly to see live progress; if output truncation is wanted, redirect stderr to a log file (`2> run.log`) and read it afterwards, or pipe through `tee` to stream live to both file and console. Empty shell output is a display-layer artifact, **NOT** evidence of failure — judge the outcome from the report as specified above
* If the process is killed due to shell/session timeout during conversion, use [resume.py](scripts/resume.py) to **resume** instead of rerunning:
  * Run the [resume.py](scripts/resume.py) script with `--region <region>`, `--instance-id <iid>`, `[--target-az <az>]`, and `--output rds_single_to_ha_result.json`
  * The script reads `<output>.state.json`, continues polling the existing backup/task (a persisted `order_id` is polled via the instance state), and writes a full report; it **never reruns** the conversion
  * If the state file is missing, stale, or mismatched, the script refuses to resume and gives the reason
  * **Special case — resume must (re-)start the conversion**: if the state file has **neither** `job_id` **nor** `order_id` (the original `convert.py` was killed after calling `StartInstanceSingleToHaAction` but before its response was captured), `resume.py` would have to (re-)issue the irreversible `StartInstanceSingleToHaAction` to continue. In that case:
    * The script gates the (re-)start on a `--confirm` flag; without `--confirm` it writes a `conversion.refused=true` report and exits non-zero, **without** calling `StartInstanceSingleToHaAction`
    * **MUST** first disclose to the user that this resume path will (re-)start the irreversible single-to-HA conversion, obtain explicit user confirmation, and only then invoke `resume.py` with `--confirm`; without confirmation **MUST NOT** pass `--confirm`
    * The pure-polling resume paths (state file already has `job_id` or `order_id`) do **not** need `--confirm` and do not (re-)issue the conversion
* If the task fails, present the failure reason to the user and suggest retrying with a different `--target-az`; a failed conversion does not affect the instance

**Step 9: Result Confirmation and Monitoring Comparison**

* The script verifies that the instance is now `type=Ha`, `status=ACTIVE`, the `ha` field is non-empty, and the primary/standby nodes are `ACTIVE`
* The primary/standby availability zones are recorded: when they are in **different** AZs the report marks `az_verified=true`; when they are in the **same** AZ the report marks `same_az=true` (a legitimate choice made in Step 4)
* Present the verification result to the user (primary availability zone, standby availability zone, and whether they are in the same AZ)
* **MUST** run the [rds_monitor.py](scripts/rds_monitor.py) script to capture a post-conversion monitoring snapshot and compare it with the Step 7 baseline:
  * Run with `--region <region>`, `--instance-id <iid>`, and `--output rds_monitor_after.json` (same default 300-second window)
  * Compare each metric against the baseline using the SOP v3 section 7.3 criteria: CPU utilization returned to normal, memory/disk utilization within normal ranges, IOPS within normal range, connection count roughly unchanged, and replication delay is 0 or near 0 (in seconds)
* **MUST** present the comparison result (before/after values per metric and pass status per criterion) to the user in **table** form
* If a metric is missing in either snapshot (CES no data or query failure), record it truthfully as "no data"; **MUST NOT** fabricate a comparison conclusion for that metric
* If any metric fails its criterion (e.g. CPU not settled, delay clearly above 0), record it truthfully, flag it to the user, and note it in the Step 10 summary

**Step 10: Workflow Summary**

* **MUST** present the completion status of each workflow step in **table** form, with the header **including**: sequence number, step, status, remarks
* **MUST** record that business verification was **informed** to the user as a post-workflow, user-driven activity — the summary must not report an executed/skipped status for it, since the SKILL cannot know the outcome at summary time
* **MUST** include the cost assessment result (single/HA prices, delta, multiple, or failure reason) and the monitoring comparison result (before/after values per metric, criterion pass status or missing metrics) in the summary
* **MUST** list the full absolute paths of the report files that **actually exist** after the run, and **MUST NOT** fabricate artifacts
* **MUST** mention the **irreversibility** of the conversion and rollback alternatives:
  * Option A (recommended): migrate data to a new single instance via DRS
  * Option B: restore a backup, or use mysqldump to export/import to a new single instance
  * Recommend performing during a business low-peak period; the standby node roughly doubles the instance cost
* **MUST** read [business-verification.md](references/business-verification.md) and present its **complete content** to the user — do **NOT** summarize or omit any section, table, or note. The section-coverage checklist below mirrors the document's structure; every item **MUST** be presented:
  * Section 1: Verify the Change Result (Console Status)
  * Section 2: Verify Primary/Standby Replication Status (SHOW SLAVE STATUS)
  * Section 3: Verify Monitoring Metrics
  * Section 4: Verify Data Consistency
  * Section 5: Business Connectivity Verification (network, database connection, and application-level checks)
  * Section 6: High Availability Verification (optional; requires the user's explicit decision)
* **MUST** inform the user that business verification is a post-workflow, user-driven activity the SKILL cannot execute via hcloud, and record any user-reported results truthfully in the conversation — do **NOT** ask the user whether to run now, defer, or skip; the SKILL cannot obtain verification results through hcloud, and user-reported results are recorded in the conversation, not in report files

## References

- [Risks and Impact](references/risks-and-impact.md) — Local reference: single-instance risks, conversion impact, and cost explanation
- [Business Verification](references/business-verification.md) — Local reference: post-conversion business verification procedures
- [Cost Estimation](references/cost-estimation.md) — Local reference: cost assessment script behavior, pricing APIs, and the single/HA comparison mode
- [Backup Time](references/backup-time.md) — Local reference: backup runtime expectation sources and the conservative storage-based estimate
- [Monitoring Comparison](references/monitoring-comparison.md) — Local reference: monitoring script behavior, metric criteria, and the before/after comparison method
- [Huawei Cloud RDS API: Single-to-HA](https://support.huaweicloud.com/api-rds/rds_01_0103.html)
- [Huawei Cloud KooCLI Installation](https://support.huaweicloud.com/qs-hcli/hcli_02.html)
- [KooCLI Usage Guide](https://support.huaweicloud.com/usermanual-hcli/hcli_05_01.html)
- [Huawei Cloud RDS User Guide (Single-to-HA)](https://support.huaweicloud.com/usermanual-rds-mysql/rds_05_0023.html)
- [Acceptance Criteria](references/acceptance-criteria.md) — Local reference: acceptance gate checklist
- [Verification Method](references/verification-method.md) — Local reference: environment and feature verification procedures
- [CLI Installation Guide](references/cli-installation-guide.md) — Local reference: hcloud CLI setup steps
- [IAM Authentication Guide](references/iam-policies.md) — Local reference: AK/SK and region configuration
