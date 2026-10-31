# Acceptance Criteria — huawei-cloud-rds-mysql-replica-promotion

> This file is the acceptance gate checklist for this SKILL before release. It is written
> item by item against the 11-step workflow (Step 0-10) in `SKILL.md`, the real CLI
> parameters of the `scripts/` scripts, and the verified command/parameter/field-path
> facts.

## 1. Registration & Routing

- [ ] `SKILL.md` conforms to the GitCode Skill registration spec (YAML frontmatter with
      `name`, `description` containing feature summary + trigger words, `tags`, `version`).
- [ ] Skill directory follows the `huawei-cloud-rds-mysql-replica-promotion` naming convention.
- [ ] `hcloud` CLI dependency correctly declared in Prerequisites section (>= 7.2.2).

## 2. Behavior

- [ ] **Step 0 (Risk disclosure and confirmation)**: presents the **complete content** of
      `references/risks-and-impact.md` — all five sections with their tables and notes
      (Section 1 risk table, Section 2 single-vs-HA capability comparison, Section 3
      impact table with the "Why CPU rises" and "Instance status during the conversion"
      notes, Section 4 cost explanation, Section 5 rollback guidance) — and **MUST**
      obtain explicit user confirmation before proceeding; without confirmation the
      workflow terminates with no cloud operation.
- [ ] **Step 1 (Environment check)**: verifies Python >= 3.9, hcloud >= 7.2.2 and hcloud
      AKSK authentication (a successful JSON response means authenticated; a DNS or
      authentication error means not); terminates with guidance if any check fails.
- [ ] **Step 2 (Region confirmation, optional)**: `--region` is confirmed once as the
      global parameter for every later script. Each parameter value **MUST** be confirmed
      exactly once. When the user already provided it at trigger time, the step is skipped
      entirely (no echo, no confirmation); the region value will be confirmed at Step 5
      (all-provided path) or at the step where it is first used (partial-provided path).
      When not provided, the skill asks the user to provide the region code; the user's
      input **is** the confirmation — **MUST NOT** ask again after input. Once confirmed,
      later steps reference it as-is and **MUST NOT** re-confirm it.
- [ ] **Step 3 (Instance discovery and selection, optional)**: when the user provided the
      instance ID at trigger time, the step is skipped entirely (no echo, no
      confirmation); the instance ID will be confirmed at Step 5 (all-provided path). The
      existence / `Single` / `ACTIVE` check is delegated to the read-only `pre_check.py`
      in Step 5. When not provided, it runs `list_instances.py --region <region>` and
      presents the instances as a table (ID, name, type Single/Ha/Replica, status, billing
      mode). The user's selection **is** the confirmation for the instance ID — **MUST
      NOT** ask again after selection. Each parameter is confirmed exactly once across
      the workflow.
- [ ] **Step 4 (Availability zone discovery and selection, optional)**: when the user
      provided the target AZ at trigger time, the step is skipped entirely (no echo, no
      confirmation); the target AZ will be confirmed at Step 5 (all-provided path).
      Availability is verified by the read-only `pre_check.py` in Step 5. When not
      provided, it runs `list_azs.py --region <region>` and presents the AZs as a table
      (zone ID, availability status). The target AZ **MUST** be available; by default it
      **should differ** from the instance's current AZ (cross-AZ DR) but the **same AZ is
      allowed** (shortest intra-AZ latency, recorded as `same_az=true` in Step 9). The
      user's selection **is** the confirmation for the target AZ — **MUST NOT** ask again
      after selection. Each parameter is confirmed exactly once across the workflow.
- [ ] **Step 5 (Precondition check)**: runs `pre_check.py --region <region> --instance-id
      <iid> --target-az <az> --output rds_single_to_ha_result_precheck.json`. Confirmation
      is conditional on the parameter source: **all-provided path** (all three from trigger
      time) — **MUST** echo all three values and request user confirmation before running
      (this is the sole confirmation point); **interactive path** (one or more from
      Steps 2/3/4 discovery) — run directly without re-confirming (parameters were already
      confirmed by the user's input/selection). The script verifies in order: instance is
      `Single` + `ACTIVE`, flavor supports HA (`{flavor_ref}.ha` entry with the target AZ
      `normal`), and automatic backups are enabled (`backup_policy.keep_days > 0`). The
      `instance_status` entry carries `name`, `availability_zone`, `volume_type`,
      `volume_size` and `charge_mode` for Step 6 display. Any failure is reported and the
      workflow terminates.
- [ ] **Step 6 (Cost assessment)**: runs `rds_cost_estimate.py --region <region>
      --compare-single-ha --spec-code <flavor_ref> --storage-size-gb <volume_size>
      --storage-type <volume_type> --charge-mode <charge_mode> --output
      rds_cost_estimate_result.json`. The script derives the HA spec from the single spec,
      quotes both specs for compute and storage filtered to the instance's charge mode,
      and reports `single_price`, `ha_price`, `price_delta`, `ha_multiple` (about 2.0).
      The on-demand price is the true on-demand quote matching the console page. The
      assessment is read-only; no resource is created. The Agent presents the comparison
      to the user in table form and continues; the final explicit confirmation for the
      conversion itself still happens in Step 8.
- [ ] **Step 7 (Pre-conversion monitoring baseline)**: runs `rds_monitor.py --region
      <region> --instance-id <iid> --output rds_monitor_baseline.json` with the default
      300-second window. The script reports CPU/memory/disk utilization, IOPS, connection
      usage and replication delay (null for the single instance). If CES has no data or
      the script fails, the metric is recorded truthfully as "no data" and the workflow
      continues; the Step 9 comparison will mark the missing metrics accordingly.
- [ ] **Step 8 (Execute single-to-HA conversion)**: the step is irreversible (roughly
      doubles the cost), so the skill **MUST** obtain explicit user confirmation before
      running `convert.py --region <region> --instance-id <iid> --target-az <az>
      [--skip-backup] --output rds_single_to_ha_result.json`. The script creates and
      waits for a manual backup first by default (no skip by default), or skips it with
      `--skip-backup` (report records `pre_backup.skipped=true`, state persists directly
      in the `job` phase without a `backup_id`); then it converts and blocks until it
      finishes. When the process is killed by a shell/session timeout, `resume.py` resumes
      from `<output>.state.json` and never reruns the conversion when the state has a
      `job_id` or `order_id`; when the state has neither (the original `convert.py` was
      killed before the `StartInstanceSingleToHaAction` response was captured), `resume.py`
      gates the (re-)start on `--confirm` and the Agent **MUST** obtain explicit user
      confirmation before passing `--confirm`. When the task fails, the failure reason is
      presented and retrying with a different `--target-az` is suggested (a failed
      conversion does not affect the instance).
- [ ] **Step 9 (Result confirmation and monitoring comparison)**: verifies the instance is
      now `type=Ha`, `status=ACTIVE`, the `ha` field is non-empty and the primary/standby
      nodes are `ACTIVE` (located by `role`, not by index). Different AZs are marked
      `az_verified=true`; the same AZ is accepted and marked `same_az=true`. The primary
      AZ and standby AZ (and the same-AZ flag when applicable) are presented to the user.
      The Agent then runs `rds_monitor.py --region <region> --instance-id <iid> --output
      rds_monitor_after.json` (same default 300-second window) and compares each metric
      against the Step 7 baseline by the SOP v3 section 7.3 criteria: CPU returned to
      normal, memory/disk utilization within normal ranges, IOPS within normal range,
      connection count roughly unchanged, and replication delay 0 or near 0. Missing
      metrics are recorded truthfully as "no data" and never fabricated.
- [ ] **Step 10 (Workflow summary)**: presents a completion table with sequence number,
      step, status and remarks; records that business verification was **informed** to the
      user as a post-workflow, user-driven activity (no executed/skipped status row — the
      SKILL cannot know the outcome at summary time); lists the full absolute paths of the
      report files that **actually exist** (fabricating artifacts is **MUST NOT**);
      mentions the irreversibility and the rollback alternatives (Option A: DRS migration
      to a new single instance; Option B: restore a backup or mysqldump export/import to a
      new single instance); reads `references/business-verification.md` and presents its
      **complete content** to the user; informs the user that business verification is a
      post-workflow, user-driven activity the SKILL cannot execute via hcloud; and does
      **NOT** ask whether to run now, defer, or skip.
- [ ] **Parameter confirmation**: each parameter value (region, instance ID, target AZ) is
      confirmed exactly once across the workflow. Trigger-time provision is confirmed at
      Step 5 (all-provided path). Interactive input/selection in Steps 2/3/4 **is** the
      confirmation — Step 5 runs directly without re-confirming. Step 8 retains its
      explicit confirmation for the irreversible conversion.

## 3. Output Artifacts

- [ ] **Discovery output** (`list_instances.py` / `list_azs.py`): structured JSON to stdout
      (instances: `id`, `name`, `type`, `status`, `datastore.version`, `flavor_ref`,
      `availability_zone`, `charge_info.charge_mode`; zones: `zoneName`,
      `zoneState.available`). No report files written.
- [ ] **Precheck report** (`rds_single_to_ha_result_precheck.json`): `metadata` plus the
      pass/fail result of each precondition; a failing check reports the reason. The
      `instance_status` entry includes `name`, `availability_zone`, `volume_type`,
      `volume_size`, `charge_mode`.
- [ ] **Cost estimate report** (`rds_cost_estimate_result.json`): `metadata`,
      `query_params` (including `compare_single_ha=true` and `charge_mode`),
      `single_price`, `ha_price`, `price_delta`, `ha_multiple`, `scope_note` (storage
      included when quoted), and `warnings[]` (per-quote failures isolated without aborting
      the run, with BSS-channel context on channel-layer errors).
- [ ] **Monitoring baseline report** (`rds_monitor_baseline.json`): `metadata` (including
      `snapshot_window`), `instances[]` with `metrics` for CPU/memory/disk/IOPS/connection
      usage and replication delay (null for the single instance), and `warnings[]`.
- [ ] **Conversion report** (`rds_single_to_ha_result.json`): `metadata`, `pre_check`,
      `conversion` and `verification` sections; the conversion section records the
      `pre_backup` (with `skipped=true` when `--skip-backup`), `backup_id`, the
      pre-backup pass/status, the `job_id` (or `order_id` for prepaid) and the final job
      status.
- [ ] **Recovery state file** (`<output>.state.json`): persists `instance_id`, `region`,
      `project_id`, `phase` (`backup` / `job`), `backup_id`, `job_id` (or `order_id`) and
      timestamps so a killed process can resume; with `--skip-backup` the state is written
      directly in the `job` phase without a `backup_id`; deleted after the report is
      written successfully.
- [ ] **Post-conversion monitoring report** (`rds_monitor_after.json`): same structure as
      the baseline report; the Agent compares its `instances[0].metrics` against the
      baseline by the SOP v3 section 7.3 criteria and presents the comparison to the user.
- [ ] **Verification detail** in the conversion report: `instance_type`, `instance_status`,
      `ha`, `primary_az`, `standby_az` and either `az_verified` (different AZs) or
      `same_az` (same AZ), so the primary/standby AZ distribution is auditable.

## 4. Structure & Compliance

- [ ] `references/acceptance-criteria.md` present — this file.
- [ ] `references/verification-method.md` present — environment and feature verification.
- [ ] `references/cli-installation-guide.md` present — hcloud CLI setup instructions.
- [ ] `references/iam-policies.md` present — AK/SK authentication and required permissions.
- [ ] `references/risks-and-impact.md` present — risk disclosure content.
- [ ] `references/business-verification.md` present — business verification procedures.
- [ ] `references/cost-estimation.md` present — cost assessment script behavior and pricing facts.
- [ ] `references/backup-time.md` present — backup runtime expectation sources.
- [ ] `references/monitoring-comparison.md` present — monitoring script behavior and comparison criteria.
- [ ] All filenames in `references/` use kebab-case.
- [ ] `SKILL.md` contains required sections: Overview, Workflow, Prerequisites, References.
- [ ] No hardcoded credentials in any file.
- [ ] All file extensions in the allowlist (.md, .py, .txt).
- [ ] `SKILL.md` documents the 11-step workflow (Step 0-10) and maps each step to its
      script. Each script's module docstring cites the same step number as `SKILL.md`.
- [ ] No deliverable file under `references/` or `scripts/` references `tests/`,
      `requirements.txt`, `README.md`, or any other file outside the deliverable set
      (SKILL.md, assets/, references/, scripts/, templates/).
- [ ] `references/cli-installation-guide.md` enumerates all 8 delivered scripts
      (`rds_common.py`, `list_instances.py`, `list_azs.py`, `pre_check.py`, `convert.py`,
      `resume.py`, `rds_cost_estimate.py`, `rds_monitor.py`).

## 5. Test Result Summary

| Capability | Steps | Expected | Result |
|------------|-------|----------|--------|
| Risk disclosure | 0 | Risks/impact presented, confirmation obtained | - |
| Environment check | 1 | Python/hcloud installed and authenticated | - |
| Region confirmation | 2 | Global `--region` confirmed once (optional) | - |
| Instance discovery | 3 | JSON list, table presented, ID confirmed (optional) | - |
| AZ discovery | 4 | JSON list, table presented, AZ confirmed (optional, same-AZ allowed) | - |
| Precondition check | 5 | Precheck report with pass/fail per condition | - |
| Cost assessment | 6 | single/HA prices, delta, multiple (~2.0), charge-mode filter | - |
| Monitoring baseline | 7 | 300s snapshot, single-instance replication delay null | - |
| Backup creation | 8 | Manual backup created and COMPLETED (default) | - |
| Skip backup | 8 | `--skip-backup` skips backup, `pre_backup.skipped=true` | - |
| Conversion | 8 | `job_id` or `order_id` returned, final status Completed | - |
| Resume recovery (polling) | 8 | Killed process resumes from state, never reruns conversion | - |
| Resume recovery (re-start) | 8 | No-job-no-order branch gated on `--confirm`; without it writes refused report | - |
| Result verification | 9 | `type=Ha`, ACTIVE, `az_verified` or `same_az` recorded | - |
| Monitoring comparison | 9 | 300s snapshot compared to Step 7 baseline by 6-metric criteria | - |
| Business verification | Step 10 notice | Informed in summary; user-reported results recorded in conversation, not as a step status | - |
| Summary | 10 | Completion table + real artifact paths + rollback note + "informed" note + complete business-verification content | - |
