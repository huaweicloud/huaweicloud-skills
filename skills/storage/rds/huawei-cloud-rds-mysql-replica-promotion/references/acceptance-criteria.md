# Acceptance Criteria — huawei-cloud-rds-mysql-replica-promotion

> This file is the acceptance gate checklist for this SKILL before release. It is written
> item by item against the 10-step workflow (Step 0-9) in `SKILL.md`, the real CLI
> parameters of the `scripts/` scripts, and the verified command/parameter/field-path
> facts.

## 1. Registration & Routing

- [ ] `SKILL.md` conforms to the GitCode Skill registration spec (YAML frontmatter with
      `name`, `description` containing feature summary + trigger words, `tags`, `version`).
- [ ] Skill directory follows the `huawei-cloud-rds-mysql-replica-promotion` naming convention.
- [ ] `hcloud` CLI dependency correctly declared in Prerequisites section (>= 7.2.2).

## 2. Behavior

- [ ] **Step 0 (Environment check)**: verifies Python >= 3.9, hcloud >= 7.2.2 and hcloud
      AKSK authentication (a successful JSON response means authenticated; a DNS or
      authentication error means not); terminates with guidance if any check fails.
- [ ] **Step 1 (Instance discovery and selection)**: when the user provided the instance ID
      at trigger time, the step is skipped entirely (no echo, no confirmation); the
      existence / `Single` / `ACTIVE` check is delegated to the read-only `pre_check.py`
      in Step 4. When not provided, it runs `list_instances.py` and presents the
      **cross-region** result as a table (ID, name, region, flavor, database version,
      billing mode). The script already filters to convertible single MySQL instances
      (`properties.haMode` Single, `properties.engineName` mysql, `state` Normal), so the
      Agent **MUST NOT** re-filter by type or engine. The script takes **no region
      parameter** — the step must cover every single MySQL instance of the account, so no
      region filter may be applied. The user's selection **is** the confirmation for the
      instance ID **and**
      for its region — **MUST NOT** ask again for either. An empty result terminates the
      workflow with that reason.
- [ ] **Step 2 (Availability zone discovery and selection)**: when the user provided the
      target AZ at trigger time, the step is skipped entirely (no echo, no confirmation);
      its availability is verified by the read-only `pre_check.py` in Step 4. When not
      provided, it runs `list_azs.py --region <instance region> --database-name MySQL
      --version-name <engine_version> --spec-code <flavor_ref> --instance-id <iid>` and
      presents the zones as a table (zone ID, name, status, whether it is the current
      zone). The three query parameters `--database-name`, `--version-name` and
      `--spec-code` are **required**; the spec code may be the single flavor because the
      script derives the HA spec automatically. Availability **MUST** come from the HA
      flavor's `az_status` (`normal`), never from a region-wide ECS zone list, because a
      zone can exist while being `sellout`/`unsupported` for the target flavor. The target
      zone **MUST** be `available=true`; by default it **should differ** from the
      instance's current zone (cross-AZ DR) but the **same zone is allowed** (shortest
      intra-zone latency, recorded as `same_az=true` in Step 8). A non-zero exit because no
      zone is available terminates the workflow with that reason. The user's selection
      **is** the confirmation for the target zone — **MUST NOT** ask again.
- [ ] **Step 3 (Risk disclosure)**: presents the **complete content** of
      `references/risks-and-impact.md` — all five sections with their tables and notes
      (Section 1 risk table, Section 2 single-vs-HA capability comparison, Section 3
      impact table with the "Why CPU rises" and "Instance status during the conversion"
      notes, Section 4 cost explanation, Section 5 rollback guidance) — before any change
      operation. It **MUST NOT** request confirmation at this step, because the user has
      not yet seen the pre-check result or the quoted price; the sole confirmation for the
      irreversible change happens in Step 7.
- [ ] **Step 4 (Precondition check)**: runs `pre_check.py --region <region> --instance-id
      <iid> --target-az <az> --output rds_single_to_ha_result_precheck.json`. Every
      parameter is derived from the earlier steps (`--region` and `--instance-id` from the
      Step 1 selection, `--target-az` from the Step 2 selection), so the Agent **MUST NOT**
      ask the user how to configure the command line and **MUST NOT** re-request any of
      them; when Steps 1/2 were skipped because the user supplied those values at trigger
      time, they are the user's own input and are presented again at the Step 7
      confirmation. The script verifies in order: instance is `Single` + `ACTIVE`, the
      **derived** HA flavor exists and supports the target zone, and automatic backups are
      enabled
      (`backup_policy.keep_days > 0`). The report nests these under `pre_check` with
      `_all_pass`; `instance_status` carries `name`, `availability_zone`, `charge_mode`,
      `volume_type` and `volume_size`, and `flavor_support` carries `spec_code` and
      `ha_spec_code`. The verdict **MUST** be read from `pre_check._all_pass`, **not** from
      the process exit code: the script writes the report and exits 0 even when a check
      fails. Any failure is reported and the workflow terminates **before** the user is
      asked to confirm the change.
- [ ] **Step 5 (Cost assessment)**: runs `rds_cost_estimate.py --region <region>
      --compare-single-ha --spec-code <flavor_support.spec_code> --storage-size-gb
      <instance_status.volume_size> --storage-type <instance_status.volume_type>
      --charge-mode <instance_status.charge_mode> --output rds_cost_estimate_result.json`.
      **MUST** pass `--charge-mode` with the instance's actual charge mode: an instance has
      exactly one billing mode, so the assessment quotes only that mode and **MUST NOT**
      present the other one. Running without `--charge-mode` (which quotes both) is
      forbidden. The script derives the HA spec from the single spec, quotes both specs for
      compute and storage, and reports `single_price`, `ha_price`, `price_delta`,
      `ha_multiple`. The multiple is **not** a fixed 2x: verified quotes are about 2.0x for
      dedicated and Kunpeng flavors and 2.2x–3.2x for general-purpose flavors, so the
      report value **MUST** be presented as-is. Storage type and size **MUST** come from
      the pre-check report, never from the RMS discovery output (which reports
      `ULTRAHIGH` where ListInstances reports `CLOUDSSD`). The on-demand price is the true
      on-demand quote matching the console page. The assessment is read-only; no resource
      is created. The Agent presents the comparison in table form and continues; the final
      explicit confirmation for the conversion itself happens in Step 7.
- [ ] **Step 6 (Pre-conversion monitoring baseline)**: runs `rds_monitor.py --region
      <region> --instance-id <iid> --output rds_monitor_baseline.json` with the default
      300-second window. The script reports CPU/memory/disk utilization, IOPS, connection
      usage and replication delay (null for the single instance). If CES has no data or
      the script fails, the metric is recorded truthfully as "no data" and the workflow
      continues; the Step 8 comparison will mark the missing metrics accordingly.
- [ ] **Step 7 (Conversion confirmation and execution)**: the step is irreversible and
      raises the cost by the multiple quoted in Step 5, so the skill **MUST** obtain
      explicit user confirmation before
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
- [ ] **Step 8 (Result confirmation and monitoring comparison)**: verifies the instance is
      now `type=Ha`, `status=ACTIVE`, the `ha` field is non-empty and the primary/standby
      nodes are `ACTIVE` (located by `role`, not by index). Different AZs are marked
      `az_verified=true`; the same AZ is accepted and marked `same_az=true`. The primary
      AZ and standby AZ (and the same-AZ flag when applicable) are presented to the user.
      The Agent then runs `rds_monitor.py --region <region> --instance-id <iid> --output
      rds_monitor_after.json` (same default 300-second window) and compares each metric
      against the Step 6 baseline by the criteria in
      `references/monitoring-comparison.md`: CPU returned to normal, memory/disk
      utilization within normal ranges, IOPS within normal range, connection count roughly
      unchanged, and replication delay 0 or near 0. Missing metrics are recorded truthfully
      as "no data" and never fabricated.
- [ ] **Step 9 (Workflow summary)**: presents a completion table with sequence number,
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
- [ ] **Parameter confirmation**: each parameter value (instance ID, region, target AZ) is
      confirmed exactly once across the workflow. The instance selection in Step 1 confirms
      the instance ID **and** its region; the AZ selection in Step 2 confirms the target
      zone. Step 4 **MUST NOT** ask the user how to configure the command line or re-request
      any of these values — it derives them from Steps 1/2 and runs directly. Values the
      user supplied at trigger time are their own explicit input and are presented again at
      the Step 7 confirmation. Step 7 retains the sole explicit confirmation for the
      irreversible conversion.

## 3. Output Artifacts

- [ ] **Discovery output** (`list_instances.py` / `list_azs.py`): structured JSON to stdout
      (instances: `id`, `name`, `region`, `engine`, `engine_version`, `flavor_ref`,
      `instance_type`, `node_num`, `availability_zone`, `volume_type`, `volume_size`,
      `charge_mode`, `status`, `convertible`; zones: `az_code`, `az_name`, `az_status`,
      `available`, `is_current`). No report files written.
- [ ] **Precheck report** (`rds_single_to_ha_result_precheck.json`): `metadata` plus a
      `pre_check` section holding `instance_status`, `flavor_support`, `backup_policy` and
      `_all_pass`, with empty `conversion`/`verification` sections reserved; a failing check
      reports the reason. `instance_status` includes `name`, `availability_zone`,
      `charge_mode`, `volume_type`, `volume_size`; `flavor_support` includes `spec_code`
      and `ha_spec_code`.
- [ ] **Cost estimate report** (`rds_cost_estimate_result.json`): `metadata`,
      `query_params` (including `compare_single_ha=true` and `charge_mode`),
      `single_price`, `ha_price`, `price_delta`, `ha_multiple`, `scope_note` (storage
      included when quoted), and `warnings[]` (per-quote failures isolated without aborting
      the run, with BSS-channel context on channel-layer errors). Only the instance's
      actual charge mode is populated: `postPaid` fills `on_demand` with `period_pricing`
      empty, `prePaid` fills `period_pricing` with `on_demand` null — never both.
- [ ] **Monitoring baseline report** (`rds_monitor_baseline.json`): `metadata` (including
      `snapshot_window`), `instances[]` with `metrics` for CPU/memory/disk/IOPS/connection
      usage and replication delay (null for the single instance), and `warnings[]`.
- [ ] **Conversion report** (`rds_single_to_ha_result.json`): `metadata`, `pre_check`,
      `conversion` and `verification` sections; the conversion section records
      `pre_backup.{pass,skipped,backup_id,backup_status}` (`skipped=true` when
      `--skip-backup`), the `job_id` (or `order_id` for prepaid), `final_status`,
      `elapsed_seconds`, `detail` and — on failure — `error` as an
      `{error_code, error_msg}` object. `backup_id` / `backup_status` are nested under
      `pre_backup`, not at the top level of `conversion`. The script exits 0 only when
      `final_status` is `Completed` and result verification passes; conversion failure,
      verification failure and hcloud errors exit non-zero.
- [ ] **Recovery state file** (`<output>.state.json`): persists `instance_id`, `region`,
      `project_id`, `phase` (`backup` / `job`), `backup_id`, `job_id` (or `order_id`) and
      timestamps so a killed process can resume; with `--skip-backup` the state is written
      directly in the `job` phase without a `backup_id`; deleted after the report is
      written successfully.
- [ ] **Post-conversion monitoring report** (`rds_monitor_after.json`): same structure as
      the baseline report; the Agent compares its `instances[0].metrics` against the
      baseline by the criteria in `references/monitoring-comparison.md` and presents the
      comparison to the user.
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
- [ ] `SKILL.md` documents the 10-step workflow (Step 0-9) and maps each step to its
      script. **When** a script's module docstring cites a step number, that number matches
      the step `SKILL.md` assigns to the script; a docstring that describes its role
      without citing a step number is not a defect (`rds_common.py`,
      `rds_cost_estimate.py` and `rds_monitor.py` currently cite none).
- [ ] Every command printed in `references/` runs as written and produces the documented
      result. Under `grep -E`, alternation is written `(a|b)`, never `a\|b` (which matches
      a literal pipe and can never fire).
- [ ] No deliverable file under `references/` or `scripts/` references `tests/`,
      `requirements.txt`, `README.md`, or any other file outside the deliverable set
      (SKILL.md, assets/, references/, scripts/, templates/).
- [ ] `references/cli-installation-guide.md` enumerates all 8 delivered scripts
      (`rds_common.py`, `list_instances.py`, `list_azs.py`, `pre_check.py`, `convert.py`,
      `resume.py`, `rds_cost_estimate.py`, `rds_monitor.py`).

## 5. Test Result Summary

| Capability | Steps | Expected | Result |
|------------|-------|----------|--------|
| Environment check | 0 | Python/hcloud installed and authenticated | - |
| Instance discovery | 1 | Cross-region JSON of convertible single MySQL instances, table presented, ID and region confirmed (optional) | - |
| AZ discovery | 2 | HA-flavor `az_status` JSON, table presented, AZ confirmed (optional, same-AZ allowed) | - |
| Risk disclosure | 3 | Complete risks/impact content presented before any change; no confirmation requested here | - |
| Precondition check | 4 | Precheck report with pass/fail per condition, run before the change confirmation | - |
| Cost assessment | 5 | single/HA prices in the instance's actual charge mode only, delta, actual multiple | - |
| Monitoring baseline | 6 | 300s snapshot, single-instance replication delay null | - |
| Backup creation | 7 | Manual backup created and COMPLETED (default) | - |
| Skip backup | 7 | `--skip-backup` skips backup, `pre_backup.skipped=true` | - |
| Conversion | 7 | `job_id` or `order_id` returned, final status Completed | - |
| Resume recovery (polling) | 7 | Killed process resumes from state, never reruns conversion | - |
| Resume recovery (re-start) | 7 | No-job-no-order branch gated on `--confirm`; without it writes refused report | - |
| Result verification | 8 | `type=Ha`, ACTIVE, `az_verified` or `same_az` recorded | - |
| Monitoring comparison | 8 | 300s snapshot compared to Step 6 baseline by 6-metric criteria | - |
| Business verification | Step 9 notice | Informed in summary; user-reported results recorded in conversation, not as a step status | - |
| Summary | 9 | Completion table + real artifact paths + rollback note + "informed" note + complete business-verification content | - |
