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

The feature verification steps below mirror the SKILL workflow Step 0-9 defined in
`SKILL.md`. Step 3 (Risk Disclosure) and Step 9 (Workflow Summary) are presented by
the Agent inside the conversation; they have no script-level command and are not
repeated here. The remaining steps each map to one or more `scripts/` invocations.

### Step 0: Environment Check

| Check | Command | Expected |
|-------|---------|----------|
| Python >= 3.9 | `python3 --version` | Version >= 3.9.x |
| hcloud installed | `hcloud --version` | Version >= 7.2.2 |
| hcloud configured | `hcloud configure list` | Shows valid AK/SK profile |
| RDS API reachable | `hcloud RDS ListApiVersionNew --cli-region=<region> --project_id=<project_id>` | JSON response with no auth/DNS error |

### Step 1: Instance Discovery and Selection

```bash
python3 scripts/list_instances.py
```

**Verify:**
- stdout is a structured JSON array; each entry contains `id`, `name`, `region`,
  `engine`, `engine_version`, `flavor_ref`, `instance_type`, `node_num`,
  `availability_zone`, `volume_type`, `volume_size`, `charge_mode`, `status` and
  `convertible`
- Every printed entry is convertible (MySQL engine, `Single` type, `Normal` state); the
  script already filtered out HA, read-replica, cluster and non-MySQL instances
- The RMS channel is hard-coded to `cn-north-4`; the script takes **no region
  parameter** because the step must cover every single MySQL instance of the account
  (passing `--region` must fail with an unrecognized-argument error)
- Pagination follows `page_info.next_marker` with `limit=200` and drops repeated ids
- The script writes no report file (pure discovery mode)

### Step 2: Availability Zone Discovery and Selection

```bash
python3 scripts/list_azs.py \
  --region <instance_region> \
  --database-name MySQL \
  --version-name <engine_version> \
  --spec-code <flavor_ref> \
  --instance-id <instance_id>
```

**Verify:**
- All four of `--region`, `--database-name`, `--version-name` and `--spec-code` are
  required
- Passing the **single** spec code is accepted: the script detects `instance_mode=single`
  and derives the HA spec (`rds_common.derive_ha_spec_code`), then lists the HA flavor's
  zones
- stdout is a structured JSON array; each entry contains `az_code`, `az_name`,
  `az_status`, `available` and `is_current`
- Availability comes from the HA flavor's `az_status`, never from the ECS zone list
- When no zone is `normal`, the script exits non-zero and prints no JSON
- The script writes no report file (pure discovery mode)

### Step 4: Precondition Check

```bash
python3 scripts/pre_check.py \
  --region cn-north-4 \
  --instance-id <instance_id> \
  --target-az cn-north-4b \
  --output rds_single_to_ha_result_precheck.json
```

**Verify:**
- The report file `rds_single_to_ha_result_precheck.json` exists
- The report is nested under `pre_check`: `pre_check.instance_status`,
  `pre_check.flavor_support`, `pre_check.backup_policy` and `pre_check._all_pass`, with
  empty `conversion` and `verification` sections reserved for later phases
- Checks pass in order: instance `type=Single` + `status=ACTIVE`; the derived HA flavor
  entry exists with the target AZ `az_status` as `normal`; and
  `backup_policy.keep_days > 0`
- `instance_status` carries `volume_type` and `volume_size` (used by the cost assessment),
  and `flavor_support` carries `spec_code` and `ha_spec_code`
- When any condition is unmet, the report contains the failure reason (e.g.
  `ha spec ... not found in ListFlavors`, `target AZ ... not available`,
  `backup policy keep_days is 0`)
- The verdict is `pre_check._all_pass`, **not** the process exit code: the script still
  writes the full report and exits 0 when a check fails, so the exit code only says the
  report was written. A run with `_all_pass=false` is a failed pre-check and terminates
  the workflow

### Step 5: Cost Assessment

```bash
python3 scripts/rds_cost_estimate.py \
  --region <instance_region> \
  --compare-single-ha \
  --spec-code <flavor_support.spec_code> \
  --storage-size-gb <instance_status.volume_size> \
  --storage-type <instance_status.volume_type> \
  --charge-mode <instance_status.charge_mode> \
  --output rds_cost_estimate_result.json
```

**Verify:**
- The report file `rds_cost_estimate_result.json` exists
- `--charge-mode` **is** passed with the instance's actual charge mode: `postPaid`
  populates `on_demand` only (`period_pricing` empty), `prePaid` populates
  `period_pricing` only (`on_demand` null) — the two modes are never populated together
- The `single_price` / `ha_price` / `price_delta` / `ha_multiple` fields are populated
- The reported multiple matches the quoted prices; it is about 2.0 for dedicated and
  Kunpeng flavors but 2.2x–3.2x for general-purpose flavors — it must not be assumed to
  be 2x
- The assessment is read-only; no resource is created
- If a quote fails, the `warnings[]` array records the failure with BSS-channel context
  (`BSS channel cn-north-1, instance region <region>` for channel-layer errors, or the
  parsed `error_code` for business-layer errors); the script does not abort the whole run

### Step 6: Pre-conversion Monitoring Baseline

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

### Step 7: Execute Single-to-HA Conversion

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
  are polled via `ListInstances` until `type=Ha` and `status=ACTIVE` — the first sample
  counts, and an intermediate `MODIFYING INSTANCE TYPE` sample is not required
- The `conversion` section of `rds_single_to_ha_result.json` contains
  `pre_backup.{pass,skipped,backup_id,backup_status}`, `job_id` (or `order_id`),
  `final_status`, `elapsed_seconds`, `detail` and — on failure — `error` as an
  `{error_code, error_msg}` object; `backup_id` / `backup_status` are nested under
  `pre_backup`, not at the top level of `conversion`
- The script exits 0 only when `final_status` is `Completed` and result verification
  passes; conversion failure, verification failure and hcloud errors write the report and
  exit non-zero. A failed pre-check still exits 0 and is judged by `pre_check._all_pass`
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
  `--confirm` it (re-)starts the conversion and continues polling. A start API error on
  this branch is reported as `final_status=Failed` with
  `conversion.error.{error_code,error_msg}` and exits non-zero
- The state file is deleted automatically only when the conversion completed and
  verification passed; on failure the report is written, the state file is kept for
  another resume attempt, and the script exits non-zero

### Step 8: Result Confirmation and Monitoring Comparison

**Verify (done automatically by convert.py or resume.py and written to the report):**
- `ListInstances` returns `instances[0].type=Ha`, `status=ACTIVE` and a non-empty `ha`
  field
- The master and slave are located by `nodes[].role`; their `availability_zone` values
  are recorded. When they differ, the report marks `az_verified=true`; when they are the
  same AZ (a legitimate Step 2 choice), the report marks `same_az=true`
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
  window as the Step 6 baseline
- The Agent compares each metric against the baseline by the criteria in
  `references/monitoring-comparison.md`: CPU utilization returned to normal, memory/disk
  utilization within normal ranges, IOPS within normal range, connection count roughly
  unchanged, and replication delay is 0 or near 0 (in seconds)
- A missing metric (CES no data or query failure) is recorded truthfully as "no data";
  the Agent does not fabricate a comparison conclusion for that metric

### Step 9: Workflow Summary

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

| Check | Command | Expected |
|-------|---------|----------|
| SKILL.md exists | `test -f SKILL.md && echo OK` | prints `OK` |
| Frontmatter valid | `grep -E '^(name|description|tags):' SKILL.md` | prints three lines (exit 0) |
| No hardcoded credentials | `grep -rEn '(AK[A-Z]* *[:=] *[A-Z0-9]{16,}|secret ?key *[:=])' .` | prints nothing; exit 1 is grep's "no match", which is the **passing** result |
| references/ has required files | `ls references/acceptance-criteria.md references/verification-method.md references/cli-installation-guide.md references/iam-policies.md` | lists all four files |
| Syntax check | `python3 -m py_compile scripts/*.py` | exits 0 with no output |

> Alternation under `grep -E` must be written `(a|b)`. Writing `a\|b` matches a literal pipe and can never fire, which silently turns the check into a no-op.

## 4. Acceptance Gate

Run the full workflow end-to-end against a non-production account. The 10 steps map to
`SKILL.md` Step 0-9:

1. **Step 0** Environment check — Python and hcloud installed, AKSK authentication verified
2. **Step 1** Instance discovered and confirmed — the cross-region list shows only
   convertible single MySQL instances; the instance ID **and its region** are confirmed
   exactly once (trigger-time provision or interactive selection)
3. **Step 2** Target AZ discovered and confirmed — listed from the HA flavor's `az_status`;
   `available=true`; differs from the current AZ by default (cross-AZ DR), same AZ
   allowed; the target AZ is confirmed exactly once
4. **Step 3** Risk disclosure — the complete `references/risks-and-impact.md` content is
   presented before any change operation, without requesting confirmation at this point
5. **Step 4** Precondition check passes — instance `Single` + `ACTIVE`, the derived HA
   flavor exists and supports the target AZ, and the backup policy is enabled; the verdict
   is `pre_check._all_pass` (the exit code only reports that the report was written); a
   failure terminates the workflow before the user is asked to confirm anything
6. **Step 5** Cost assessment — `rds_cost_estimate.py` compare mode quotes single vs HA
   prices in the instance's actual charge mode only (`--charge-mode` from the pre-check
   report; the other mode is never quoted); the comparison, including the actual multiple,
   is presented to the user
7. **Step 6** Pre-conversion monitoring baseline — `rds_monitor.py` 300-second snapshot
   taken before the conversion; missing metrics recorded truthfully
8. **Step 7** Conversion completes — explicit user confirmation obtained; manual backup
   `COMPLETED` (unless `--skip-backup`), `StartInstanceSingleToHaAction` returns `job_id`
   or `order_id`, conversion reaches `Completed`; `resume.py` resumes a killed process
   without re-running the conversion (except the no-job-no-order branch, gated on
   `--confirm`)
9. **Step 8** Result verified — `type=Ha`, `status=ACTIVE`, `ha` non-empty, master/slave
   `ACTIVE`; `az_verified=true` or `same_az=true` recorded; post-conversion monitoring
   snapshot compared against the Step 6 baseline by the six-metric criteria
10. **Step 9** Workflow summary — completion table presented, real artifact paths listed,
    irreversibility and rollback alternatives mentioned, business verification informed
    as a post-workflow user activity, and the complete `references/business-verification.md`
    content presented; the user is not asked whether to run now, defer, or skip
