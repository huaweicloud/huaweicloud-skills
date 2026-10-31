# Verification Method

> This file defines the environment, feature and compliance verification procedures of the
> huawei-cloud-rds-mysql-replica-promotion SKILL, and pairs with the acceptance gate in
> `references/acceptance-criteria.md`. All verification commands are written against the
> real CLI parameters of the scripts and the verified command/parameter/field-path facts.

## 1. Environment Verification

Before running the skill, verify that all prerequisites are met:

```bash
# Check Python version (>= 3.9 required)
python3 --version

# Check hcloud CLI availability (>= 7.2.2 required)
hcloud --version

# Check hcloud authentication configuration
hcloud configure list

# Smoke test: query the RDS service API connectivity
hcloud RDS ListApiVersionNew --cli-region=cn-north-4 --project_id=<your_project_id>
```

A successful JSON response for the smoke test means authentication is configured; a DNS
or authentication error means it is not.

> Note: the scripts of this SKILL depend only on the Python standard library (no
> third-party pip packages), so the environment check does not need a pip install step.
> A syntax check via `python3 -m py_compile scripts/*.py` is sufficient.

## 2. Feature Verification

The feature verification steps below mirror the SKILL workflow Step 0-10 defined in
`SKILL.md`. Step 0 (Risk Disclosure) and Step 10 (Workflow Summary) are presented by
the Agent inside the conversation; they have no script-level command and are not
repeated here. Steps 1-9 each map to one or more `scripts/` invocations.

### Step 1: Environment Check

| Check | Command | Expected |
|-------|---------|----------|
| Python >= 3.9 | `python3 --version` | Version >= 3.9.x |
| hcloud installed | `hcloud --version` | Version >= 7.2.2 |
| hcloud configured | `hcloud configure list` | Shows valid AK/SK profile |
| RDS API reachable | `hcloud RDS ListApiVersionNew --cli-region=<region> --project_id=<project_id>` | JSON response with no auth/DNS error |

### Step 2: Region Confirmation

Handled by the Agent in the SKILL workflow: confirm the global `--region` (e.g.
`cn-north-4`). No script-level verification is needed; every later script receives that
region as the required `--region` argument.

### Step 3: Instance Discovery and Selection

```bash
python3 scripts/list_instances.py --region cn-north-4
```

**Verify:**
- stdout is a structured JSON array; each entry contains `id`, `name`, `type`
  (Single/Ha/Replica), `status`, `datastore.version`, `flavor_ref`,
  `availability_zone` and `charge_info.charge_mode`
- The target instance has `type=Single` and `status=ACTIVE` (otherwise the precondition
  check will fail)
- The script writes no report file (pure discovery mode)

### Step 4: Availability Zone Discovery and Selection

```bash
python3 scripts/list_azs.py --region cn-north-4
```

**Verify:**
- stdout is a structured JSON array; each entry contains `zoneName` and
  `zoneState.available`
- The target AZ has `available=true`. By default the target AZ should differ from the
  instance's current AZ (cross-AZ DR), but the same AZ is also allowed (shortest intra-AZ
  latency); the same-AZ case is recorded as `same_az=true` in the Step 9 verification
- The script writes no report file (pure discovery mode)

### Step 5: Precondition Check

```bash
python3 scripts/pre_check.py \
  --region cn-north-4 \
  --instance-id <instance_id> \
  --target-az cn-north-4b \
  --output rds_single_to_ha_result_precheck.json
```

**Verify:**
- The report file `rds_single_to_ha_result_precheck.json` exists
- Checks pass in order: instance `type=Single` + `status=ACTIVE`; the `{flavor_ref}.ha`
  flavor entry exists with the target AZ `az_status` as `normal`; and
  `backup_policy.keep_days > 0`
- When any condition is unmet, the report contains the failure reason (e.g.
  `ha spec ... not found in ListFlavors`, `target AZ ... not available`,
  `backup policy keep_days is 0`)

### Step 6: Cost Assessment

```bash
python3 scripts/rds_cost_estimate.py \
  --region cn-north-4 \
  --compare-single-ha \
  --spec-code <flavor_ref> \
  --storage-size-gb <volume_size> \
  --storage-type <volume_type> \
  --charge-mode <charge_mode> \
  --output rds_cost_estimate_result.json
```

**Verify:**
- The report file `rds_cost_estimate_result.json` exists
- The `single_price` / `ha_price` / `price_delta` / `ha_multiple` fields are populated;
  the HA multiple is about 2.0
- The `query_params.charge_mode` matches the instance's actual charge mode from the Step
  5 pre-check report (`postPaid` quotes only on-demand, `prePaid` only monthly/yearly)
- The assessment is read-only; no resource is created
- If a quote fails, the `warnings[]` array records the failure with BSS-channel context
  (`BSS channel cn-north-1, instance region <region>` for channel-layer errors, or the
  parsed `error_code` for business-layer errors); the script does not abort the whole run

### Step 7: Pre-conversion Monitoring Baseline

```bash
python3 scripts/rds_monitor.py \
  --region cn-north-4 \
  --instance-id <instance_id> \
  --output rds_monitor_baseline.json
```

**Verify:**
- The report file `rds_monitor_baseline.json` exists
- The `metadata.snapshot_window` is 300 seconds (the default, covering one full CES
  5-minute collection cycle)
- The `instances[0].metrics` section reports CPU utilization, memory utilization, disk
  utilization, IOPS, connection usage, and replication delay (null for the single
  instance, since there is no standby to replicate to)
- If CES has no data or the query fails, the metric is recorded truthfully as `null`
  with a warning; the script does not block the conversion

### Step 8: Execute Single-to-HA Conversion

```bash
python3 scripts/convert.py \
  --region cn-north-4 \
  --instance-id <instance_id> \
  --target-az cn-north-4b \
  [--skip-backup] \
  --output rds_single_to_ha_result.json
```

**Verify (done automatically by the script):**
- Unless `--skip-backup` is given, a manual backup is created first (`CreateManualBackup`)
  and polled until `COMPLETED` (`ListBackups` polls `backup.status`); with `--skip-backup`
  the report records `pre_backup.skipped=true` and the state is persisted directly in the
  `job` phase without a `backup_id`
- The conversion is then started (`StartInstanceSingleToHaAction`) and returns a
  `job_id` (postPaid) or `order_id` (prePaid); `ListJobInfo` polls `job.status` until
  `Completed` (the criterion is `job.status`, not `process == "100%"`); prePaid instances
  are polled via `ListInstances` instance state instead
- The `conversion` section of `rds_single_to_ha_result.json` contains `backup_id`,
  `job_id` (or `order_id`), `pre_backup.pass` and `final_status`
- Prepaid (prePaid) instances automatically carry `--single_to_ha.is_auto_pay=true` to
  pay the price difference
- After the report is written successfully, the state file is deleted

**Resume verification (after the process is killed by a shell/session timeout):**

```bash
python3 scripts/resume.py \
  --region cn-north-4 \
  --instance-id <instance_id> \
  [--target-az cn-north-4b] \
  [--confirm] \
  --output rds_single_to_ha_result.json
```

**Verify:**
- The `backup_id` / `job_id` (or `order_id`) persisted in `<output>.state.json`
  (`rds_single_to_ha_result.json.state.json`) is used to continue polling; the conversion
  is **not** restarted when the state has a `job_id` or `order_id`
- When the state file is missing, stale (beyond the max poll time) or its
  `instance_id`/`region` mismatches the command line, the script refuses to resume and
  gives the reason
- `--target-az` is needed only when the conversion job was not yet started (state
  `phase=backup`); it is optional when `phase=job`
- When the state file has neither `job_id` nor `order_id` (the original `convert.py` was
  killed before the `StartInstanceSingleToHaAction` response was captured), `resume.py`
  would have to (re-)start the irreversible conversion. In that case it gates the
  (re-)start on `--confirm`: without `--confirm` it writes a `conversion.refused=true`
  report and exits non-zero without calling `StartInstanceSingleToHaAction`; with
  `--confirm` it (re-)starts the conversion and continues polling
- The state file is deleted automatically after the report is written successfully

### Step 9: Result Confirmation and Monitoring Comparison

**Verify (done automatically by convert.py or resume.py and written to the report):**
- `ListInstances` returns `instances[0].type=Ha`, `status=ACTIVE` and a non-empty `ha`
  field
- The master and slave are located by `nodes[].role`; their `availability_zone` values
  are recorded. When they differ, the report marks `az_verified=true`; when they are the
  same AZ (a legitimate Step 4 choice), the report marks `same_az=true`
- The `verification` section of the report contains `instance_type`,
  `instance_status`, `ha`, `primary_az`, `standby_az`, and either `az_verified` or
  `same_az`

**Post-conversion monitoring comparison (run by the Agent):**

```bash
python3 scripts/rds_monitor.py \
  --region cn-north-4 \
  --instance-id <instance_id> \
  --output rds_monitor_after.json
```

**Verify:**
- The report file `rds_monitor_after.json` exists with the same 300-second default
  window as the Step 7 baseline
- The Agent compares each metric against the baseline by the SOP v3 section 7.3 criteria:
  CPU utilization returned to normal, memory/disk utilization within normal ranges, IOPS
  within normal range, connection count roughly unchanged, and replication delay is 0 or
  near 0 (in seconds)
- A missing metric (CES no data or query failure) is recorded truthfully as "no data";
  the Agent does not fabricate a comparison conclusion for that metric

### Step 10: Workflow Summary

Handled by the Agent in the SKILL workflow: a completion table with sequence number,
step, status and remarks is presented to the user. The summary lists the full absolute
paths of the report files that actually exist (the Agent does not fabricate artifacts),
mentions the irreversibility and the rollback alternatives (DRS migration to a new single
instance, or backup restore / mysqldump export-import to a new single instance), and
informs the user that business verification is a post-workflow, user-driven activity the
SKILL cannot execute via hcloud. The Agent then reads `references/business-verification.md`
and presents its complete content to the user; it does **not** ask whether to run now,
defer, or skip. No script-level command is needed for this step.

## 3. Compliance Checks (Local, Offline)

| Check | Command |
|-------|---------|
| SKILL.md exists | `test -f SKILL.md && echo OK` |
| Frontmatter valid | `grep -E '^(name\|description\|tags):' SKILL.md` |
| No hardcoded credentials | `grep -rEn '(AK[A-Z]* *[:=] *[A-Z0-9]{16,}\|secret ?key *[:=])' .` |
| references/ has required files | `ls references/acceptance-criteria.md references/verification-method.md references/cli-installation-guide.md references/iam-policies.md` |
| Syntax check | `python3 -m py_compile scripts/*.py` |

## 4. Acceptance Gate

Run the full workflow end-to-end against a non-production account. The 11 steps map to
`SKILL.md` Step 0-10:

1. **Step 0** Risk disclosure — the complete `references/risks-and-impact.md` content is
   presented; explicit user confirmation is obtained before any cloud operation
2. **Step 1** Environment check — Python and hcloud installed, AKSK authentication verified
3. **Step 2** Region confirmed — global `--region` confirmed once and referenced as-is
   by every later script
4. **Step 3** Instance discovered and confirmed — `Single` + `ACTIVE`; the instance ID is
   confirmed exactly once (trigger-time provision or interactive selection)
5. **Step 4** Target AZ discovered and confirmed — available; differs from the current AZ
   by default (cross-AZ DR), same AZ allowed; the target AZ is confirmed exactly once
6. **Step 5** Precondition check passes — instance, flavor/HA support and backup policy
   all verified
7. **Step 6** Cost assessment — `rds_cost_estimate.py` compare mode quotes single vs HA
   prices filtered by the instance charge mode; the comparison is presented to the user
8. **Step 7** Pre-conversion monitoring baseline — `rds_monitor.py` 300-second snapshot
   taken before the conversion; missing metrics recorded truthfully
9. **Step 8** Conversion completes — manual backup `COMPLETED` (unless `--skip-backup`),
   `StartInstanceSingleToHaAction` returns `job_id` or `order_id`, conversion reaches
   `Completed`; `resume.py` resumes a killed process without re-running the conversion
   (except the no-job-no-order branch, gated on `--confirm`)
10. **Step 9** Result verified — `type=Ha`, `status=ACTIVE`, `ha` non-empty, master/slave
    `ACTIVE`; `az_verified=true` or `same_az=true` recorded; post-conversion monitoring
    snapshot compared against the Step 7 baseline by the six-metric criteria
11. **Step 10** Workflow summary — completion table presented, real artifact paths listed,
    irreversibility and rollback alternatives mentioned, business verification informed
    as a post-workflow user activity, and the complete `references/business-verification.md`
    content presented; the user is not asked whether to run now, defer, or skip
