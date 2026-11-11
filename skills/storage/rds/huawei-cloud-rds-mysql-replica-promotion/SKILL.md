---
name: huawei-cloud-rds-mysql-replica-promotion
description: |
  Huawei Cloud RDS for MySQL risk reduction skill that converts a single instance to a primary/standby (HA) instance via the hcloud CLI.
  Use this skill when the user wants to convert a Huawei Cloud RDS for MySQL single instance to a primary/standby (HA) instance, upgrade database high availability, or eliminate single-point-of-failure risk.
  Trigger: User mentions "单机转主备", "高可用升级", "single to HA", "convert to primary/standby"
tags: [ huawei-cloud, rds, high-availability ]
version: 1.1.0
license: MIT
---

# Huawei Cloud RDS Single-to-HA Conversion

## Overview

Use the `hcloud` (KooCLI) command-line tool to convert a Huawei Cloud RDS for MySQL single instance to a primary/standby (HA) instance.

## Prerequisites

- Python >= 3.9
- hcloud >= 7.2.2 with AKSK authentication configured (`hcloud configure init`)
- The target RDS for MySQL instance **MUST** currently be a `Single` instance in `ACTIVE` state

## Workflow

Copy the checklist below and track progress:

```markdown
- [ ] Step 0: Environment Check
- [ ] Step 1: Instance Discovery and Selection
- [ ] Step 2: Availability Zone Discovery and Selection
- [ ] Step 3: Risk Disclosure
- [ ] Step 4: Precondition Check
- [ ] Step 5: Cost Assessment
- [ ] Step 6: Pre-conversion Monitoring Baseline
- [ ] Step 7: Conversion Confirmation and Execution
- [ ] Step 8: Result Confirmation and Monitoring Comparison
- [ ] Step 9: Workflow Summary
```

**Step 0: Environment Check**

* **MUST** check whether the Python programming language is installed
* **MUST** check whether the hcloud command-line tool is installed
* **MUST** check whether the hcloud command-line tool has authentication configured
  * A successful JSON response indicates authentication is configured; a DNS or authentication error indicates it is not configured
* If any check fails, **MUST** report the missing items and fix instructions to the user and terminate the workflow

**Step 1: Instance Discovery and Selection**

* Branch first on what the user already provided when triggering the skill:
  * **Instance ID already provided by the user** (fully explicit): this step is skipped entirely — do **NOT** echo the instance ID or request confirmation. The instance's existence, `Single` type and `ACTIVE` status are verified by the read-only pre-check in Step 4; if that check fails, the workflow terminates with the reason.
  * **Not provided**: follow the discovery flow below
* For the discovery flow:
  * Run the [list_instances.py](scripts/list_instances.py) script to list the account's convertible single MySQL instances **across all regions**
    * The script prints the instances as structured JSON (fields include: `id`, `name`, `region`, `engine`, `engine_version`, `flavor_ref`, `instance_type`, `node_num`, `availability_zone`, `volume_type`, `volume_size`, `charge_mode`, `status`, `convertible`)
  * **MUST** present the instances to the user in **table** form (formatted by the Agent from the JSON output), including at least: instance ID, instance name, region, flavor, database version, and billing mode
  * **MUST** present the instance table to the user and ask them to select the target instance ID to convert
  * The user's selection **is** the confirmation for the instance ID **and** for the region — **MUST NOT** ask the user to confirm either again
  * If the script prints an empty array, **MUST** report that no convertible single MySQL instance exists in the account and terminate the workflow
* Record the selected instance's `region`, `flavor_ref`, `engine_version`, and `availability_zone` for later steps

**Step 2: Availability Zone Discovery and Selection**

* Branch first on what the user already provided when triggering the skill:
  * **Target AZ already provided by the user** (fully explicit): this step is skipped entirely — do **NOT** echo the target AZ or request confirmation. Its availability is verified by the read-only pre-check in Step 4.
  * **Not provided**: follow the discovery flow below
* For the discovery flow:
  * Run the [list_azs.py](scripts/list_azs.py) script with `--region <selected instance region>`, `--database-name MySQL`, `--version-name <selected instance engine_version>`, `--spec-code <selected instance flavor_ref>`, and `--instance-id <selected instance id>`
    * The script prints the zones as structured JSON (fields include: `az_code`, `az_name`, `az_status`, `available`, `is_current`)
    * Availability is flavor-scoped: a zone may exist yet still be `sellout` or `unsupported` for the target HA flavor. The `available` flag is the only authority — **MUST NOT** substitute a region-wide zone list
  * **MUST** present the availability zones to the user in **table** form, including the zone ID, its name, its status, and whether it is the instance's current zone
  * **MUST** explain to the user: the standby zone **MUST** be available (`available=true`); by default it **should differ** from the instance's current zone (cross-AZ disaster recovery, as recommended), but choosing the **same zone as the current one is allowed** (shortest intra-zone latency) — the choice is the user's
  * The user's selection **is** the confirmation for the target AZ — **MUST NOT** ask the user to confirm again after selection
  * If the script exits non-zero because no zone is available for the flavor, **MUST** present that reason to the user and terminate the workflow; **MUST NOT** fabricate a zone list
* Each parameter value **MUST** be confirmed exactly once across the workflow

**Step 3: Risk Disclosure**

* **MUST** read [risks-and-impact.md](references/risks-and-impact.md) and present its **complete content** to the user — do **NOT** summarize or omit any section, table, or note. The section-coverage checklist below mirrors the document's structure; every item **MUST** be presented:
  * Section 1: Inherent Risks of a Single-Instance Deployment (the R-001..R-005 risk table)
  * Section 2: Capability Comparison: Single vs Primary/Standby (the comparison table)
  * Section 3: Operational Impact of Converting to Primary/Standby (the impact table, the "Why CPU rises" note, and the "Instance status during the conversion" note)
  * Section 4: Cost Explanation (the billing modes table, the prepaid price-difference calculation, and the other costs note)
  * Section 5: Rollback Guidance
* The disclosure is informational and read-only. It **MUST** happen before any change operation, and it does **NOT** replace the final explicit confirmation in Step 7
* **MUST NOT** request a confirmation at this step: the user has not yet seen the quoted price or the precondition result. Present the disclosure and continue to Step 4

**Step 4: Precondition Check**

Verify all preconditions before any change:

* Run the [pre_check.py](scripts/pre_check.py) script with `--region <selected instance region>`, `--instance-id <selected instance id>`, `--target-az <selected target AZ>`, and `--output rds_single_to_ha_result_precheck.json`
* Every value comes from the earlier steps, so the Agent **MUST NOT** ask the user how to configure the command line; when Steps 1 and 2 were skipped because the user supplied those values at trigger time, they are presented again at the Step 7 confirmation
* The script verifies in order: the instance is `Single` and `ACTIVE`, the derived HA flavor exists and the target availability zone is available for it, and automatic backups are enabled
* The report's `instance_status` entry carries the instance name, current availability zone, charge mode, storage type, and storage size; the `flavor_support` entry carries the authoritative single and HA spec codes. **MUST** source the Step 5 cost assessment and the Step 7 display from these values — **MUST NOT** source storage type or size from the Step 1 discovery output, which reports a different storage-type vocabulary
* **MUST** judge the verdict from the report's `pre_check._all_pass`, **NOT** from the process exit code — the script still writes the full report and exits 0 when a check fails, so the exit code only means the report was written
* If any check fails, the script reports the reason and writes a report; **MUST** present the failure information to the user and terminate the workflow

**Step 5: Cost Assessment**

* Assess the cost increase of converting the single instance to HA, based on the Step 4 pre-check report. Every parameter is derived, so the Agent **MUST NOT** ask the user how to configure the command line:
  * Run the [rds_cost_estimate.py](scripts/rds_cost_estimate.py) script in **compare mode** with `--region <region>`, `--compare-single-ha`, `--spec-code <flavor_support.spec_code>`, `--storage-size-gb <instance_status.volume_size>`, `--storage-type <instance_status.volume_type>`, `--charge-mode <instance_status.charge_mode>`, and `--output rds_cost_estimate_result.json`
  * **MUST** pass `--charge-mode` with the instance's actual charge mode from the Step 4 pre-check report. An instance has exactly **one** billing mode, so the assessment **MUST** quote only that mode — `postPaid` quotes on-demand prices only, `prePaid` quotes monthly/yearly prices only. **MUST NOT** present both modes in the same assessment, and **MUST NOT** run the script without `--charge-mode` (which would quote both)
  * The script derives the corresponding HA spec from the single spec, quotes both specs for compute and storage in the instance's charge mode, and reports the single price, HA price, price delta, and the HA multiple
  * The price multiple is **not a fixed 2x**: verified quotes show about 2.0x for dedicated and ARM flavors, but 2.2x–3.2x for general-purpose flavors (the smaller the flavor, the higher the multiple). **MUST** present the multiple actually returned in the report and **MUST NOT** state a fixed "about 2x" figure
  * The on-demand price is a **true on-demand quote** (matching the console page price); the storage volume is quoted per spec and is higher for HA than for single
  * If a quote line is missing, report it truthfully as a warning; **MUST NOT** fabricate a price
* **MUST** present the comparison result to the user in **table** form: one table for the instance's actual charge mode (on-demand when `postPaid`, monthly/yearly when `prePaid`), carrying the single price, the HA price, the delta, and the multiple for the compute and storage components that actually carry values in the report. **MUST NOT** render a table for the other, non-applicable charge mode
* **MUST** state the instance's billing mode (from the Step 4 pre-check report) and explain what the change means for it:
  * `prePaid` (yearly/monthly): the price difference is charged automatically at conversion; the account balance **MUST** be sufficient
  * `postPaid` (pay-per-use): no price-difference payment is required
* The assessment is read-only; it never creates any resource
* BSS quoting goes through the **global BSS channel**; the real instance region is carried in the quote request and does **not** affect the result. If the CLI raises a "region not supported" type error, that is a **BSS channel-layer issue**, not a quote-business error — see [cost-estimation.md](references/cost-estimation.md) for the failure-mode interpretation
* Present the result and continue; the final explicit confirmation for the conversion itself still happens in Step 7

**Step 6: Pre-conversion Monitoring Baseline**

* Run the [rds_monitor.py](scripts/rds_monitor.py) script to capture a monitoring baseline of the instance before conversion:
  * Run with `--region <region>`, `--instance-id <iid>`, and `--output rds_monitor_baseline.json`
  * The script uses a 300-second default window (covering one full 5-minute CES collection cycle) and reports CPU utilization, memory utilization, disk utilization, IOPS, connection usage, and replication delay (null for the single instance)
* **MUST** present the baseline snapshot to the user; note that it is taken from the single instance before conversion
* If the baseline cannot be captured (CES has no data or the script fails), record it truthfully as "no data" and continue; the comparison in Step 8 will mark the missing metrics accordingly

**Step 7: Conversion Confirmation and Execution**

This step is **irreversible** (it changes the cloud instance from `Single` to `Ha` and raises the cost by the multiple quoted in Step 5). It requires explicit **user confirmation**.

* Present the confirmed parameters to the user: `--instance-id`, `--target-az` (may be the same zone as the current one, chosen by the user in Step 2), and the instance billing mode (from the Step 4 pre-check report)
* Present the conversion impact and cost information (see [risks-and-impact.md](references/risks-and-impact.md)): irreversibility, the cost increase actually quoted in Step 5, storage capacity doubling with storage cost rising, brief CPU rise, backup storage cost
* Billing mode explanation: for prepaid (prePaid) instances, the script automatically carries `is_auto_pay=true` and Huawei Cloud auto-charges the price difference from the account — ensure the account balance is sufficient; pay-per-use (postPaid) instances do not need this price-difference payment
* **MUST** obtain explicit user confirmation before running the conversion command; if the user does not confirm, **MUST NOT** continue
* Backup handling (ask the user, default is to back up):
  * **MUST** explain to the user: by default the conversion performs a pre-conversion manual backup first; the manual backup occupies backup storage on the cloud and incurs backup storage cost after the free quota
  * **MUST** tell the user how long one backup roughly takes before asking whether to keep it. The complete command is `hcloud RDS ListBackups`; before running it, the Agent **MUST**:
    * Run `hcloud RDS ListBackups --help` first and read the help text, rather than assuming the parameter names
    * Derive the required parameters from the workflow context — the instance is the one selected in Step 1 (`--instance_id`), the region is that instance's region (`--cli-region`), and the project id is the one the pre-check already resolved (`--project_id`)
    * Query the automatic backups of that instance (`--backup_type=auto`) and use the first record's `begin_time`/`end_time` difference (the API returns records `begin_time`-descending; a full backup of the same instance takes a similar time)
    * If no automatic backup exists, query the manual backups the same way and use the latest record's duration
    * If no backup record exists at all, estimate from the storage size (GB) × 1024 / 100 MB/s and label it conservative ("actual usually shorter")
  * Ask the user whether to keep the manual backup. If the user chooses **not to back up**, run with `--skip-backup` to convert directly (the automatic backup policy still applies and is recommended as a fallback); if the user keeps the backup, run without `--skip-backup` (same as the current default behavior)
* Run the [convert.py](scripts/convert.py) script with `--region <region>`, `--instance-id <iid>`, `--target-az <az>`, `[--skip-backup]`, and `--output rds_single_to_ha_result.json`
  * The script performs the pre-conversion manual backup first (unless `--skip-backup` is given), then performs the conversion and blocks until it finishes (typically about 10 minutes, longer for large data volumes)
  * The script persists the conversion status (`backup_id` / `job_id`, or `order_id` for prepaid instances) to `<output>.state.json` so that processes killed by shell/session timeout can be resumed
  * When the backup is skipped, the state is persisted directly in the `job` phase without a `backup_id`
  * **MUST** judge the conversion result from the report's `conversion.final_status` (and the non-empty `conversion`/`verification` sections), **NOT** from the process exit code — on failure the report carries `conversion.error.{error_code,error_msg}` and `conversion.detail`, and the script exits non-zero; the report remains the authoritative verdict
  * For prepaid (prePaid) instances, the API returns an `order_id` (BSS order) instead of a `job_id`; the script polls the **instance state** until `type=Ha` + `status=ACTIVE` instead of the job, so there is no percentage progress — `MODIFYING INSTANCE TYPE` may or may not be observed and does not gate completion; the conversion finishes in about 10 minutes and the result is judged by the same `conversion.final_status`
* **MUST NOT** pipe the long-running scripts (`convert.py`, `resume.py`) through `| tail -N` (e.g. `2>&1 | tail -60`): the scripts stream their progress logs to stderr in real time, while `tail` buffers until EOF, so when the process is killed by a shell/session timeout before EOF all logs are swallowed and the shell tool reports empty stdout/stderr/exit output. Run the command directly to see live progress; if output truncation is wanted, redirect stderr to a log file (`2> run.log`) and read it afterwards, or pipe through `tee` to stream live to both file and console. Empty shell output is a display-layer artifact, **NOT** evidence of failure — judge the outcome from the report as specified above
* If the process is killed due to shell/session timeout during conversion, use [resume.py](scripts/resume.py) to **resume** instead of rerunning:
  * Run the [resume.py](scripts/resume.py) script with `--region <region>`, `--instance-id <iid>`, `[--target-az <az>]`, and `--output rds_single_to_ha_result.json`
  * The script reads `<output>.state.json`, continues polling the existing backup/task (a persisted `order_id` is polled via the instance state), and writes a full report; it **never reruns** the conversion. It exits non-zero when the conversion or verification fails and keeps the state file for another resume attempt
  * If the state file is missing, stale, or mismatched, the script refuses to resume and gives the reason
  * **Special case — resume must (re-)start the conversion**: if the state file has **neither** `job_id` **nor** `order_id` (the original `convert.py` was killed after calling `StartInstanceSingleToHaAction` but before its response was captured), `resume.py` would have to (re-)issue the irreversible `StartInstanceSingleToHaAction` to continue. In that case:
    * The script gates the (re-)start on a `--confirm` flag; without `--confirm` it writes a `conversion.refused=true` report and exits non-zero, **without** calling `StartInstanceSingleToHaAction`
    * **MUST** first disclose to the user that this resume path will (re-)start the irreversible single-to-HA conversion, obtain explicit user confirmation, and only then invoke `resume.py` with `--confirm`; without confirmation **MUST NOT** pass `--confirm`
    * The pure-polling resume paths (state file already has `job_id` or `order_id`) do **not** need `--confirm` and do not (re-)issue the conversion
* If the task fails, present the failure reason to the user and suggest retrying with a different `--target-az`; a failed conversion does not affect the instance

**Step 8: Result Confirmation and Monitoring Comparison**

* The script verifies that the instance is now `type=Ha`, `status=ACTIVE`, the `ha` field is non-empty, and the primary/standby nodes are `ACTIVE`
* The primary/standby availability zones are recorded: when they are in **different** zones the report marks `az_verified=true`; when they are in the **same** zone the report marks `same_az=true` (a legitimate choice made in Step 2)
* Present the verification result to the user (primary availability zone, standby availability zone, and whether they are in the same zone)
* **MUST** run the [rds_monitor.py](scripts/rds_monitor.py) script to capture a post-conversion monitoring snapshot and compare it with the Step 6 baseline:
  * Run with `--region <region>`, `--instance-id <iid>`, and `--output rds_monitor_after.json` (same default 300-second window)
  * Compare each metric against the baseline using the criteria in [monitoring-comparison.md](references/monitoring-comparison.md): CPU utilization returned to normal, memory/disk utilization within normal ranges, IOPS within normal range, connection count roughly unchanged, and replication delay is 0 or near 0 (in seconds)
* **MUST** present the comparison result (before/after values per metric and pass status per criterion) to the user in **table** form
* If a metric is missing in either snapshot (CES no data or query failure), record it truthfully as "no data"; **MUST NOT** fabricate a comparison conclusion for that metric
* If any metric fails its criterion (e.g. CPU not settled, delay clearly above 0), record it truthfully, flag it to the user, and note it in the Step 9 summary

**Step 9: Workflow Summary**

* **MUST** present the completion status of each workflow step in **table** form, with the header **including**: sequence number, step, status, remarks
* **MUST** record that business verification was **informed** to the user as a post-workflow, user-driven activity — the summary must not report an executed/skipped status for it, since the SKILL cannot know the outcome at summary time
* **MUST** include the cost assessment result (single/HA prices, delta, multiple, or failure reason) and the monitoring comparison result (before/after values per metric, criterion pass status or missing metrics) in the summary
* **MUST** list the full absolute paths of the report files that **actually exist** after the run, and **MUST NOT** fabricate artifacts
* **MUST** mention the **irreversibility** of the conversion and rollback alternatives:
  * Option A (recommended): migrate data to a new single instance via DRS
  * Option B: restore a backup, or use mysqldump to export/import to a new single instance
  * Recommend performing during a business low-peak period; the standby node raises the instance cost by the multiple quoted in Step 5
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
