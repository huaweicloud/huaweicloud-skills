---
name: huawei-cloud-mgc-migration-ecs-gcp-to-hw
description: |
  Execute and troubleshoot Huawei Cloud server migration in this repository. Supports both the current batch existing-target SMS workflow (`terraform apply` + `scripts/mgc_sms_existing_target_batch.py`) and the single-source SMS/rsync workflow (`scripts/mgc_migrate.py`), orchestrated by Terraform against the Huawei Cloud SMS/ECS/VPC/EVS/IAM REST APIs.
  Use when the user asks to migrate ECS/on-prem VMware/external GCP/AWS sources, run migration in `ap-southeast-3`/`la-*`, resume after pause from `out/resume_checkpoint_latest.json`, monitor tasks in `out/task_poll_latest.json`, repair a broken boot disk with `scripts/repair_boot_via_helper.py`, or diagnose SMS/MGC errors such as SMS.0202, SMS.1404, SMS.0515, SMS.6504, SMS.6602, SMS.6603, SMS.6617, SMS.7605, SMS.7703, SMS.8115, stale SMS-Agent process, or missing `disk_id` in target disk mapping.
  Trigger words: migrate, migration, SMS, MGC, batch migration, boot repair, GRUB repair, 跨区域迁移, MGC/SMS 迁移流程, 批量迁移恢复, 迁移排障.
tags: [huawei-cloud, migration, sms, mgc, terraform]
---

# MGC Cross-Region Migration

## Overview

This skill runs the migration flow implemented in this repository, from precheck to task startup and result validation, keeping execution deterministic by following the exact command sequence and error-handling rules already implemented in the migration scripts.

**Architecture**: Terraform (`main.tf`) reads `terraform.tfvars`, maps the values to runtime environment variables, and invokes `scripts/run_migration.sh`, which currently calls `python3 scripts/mgc_sms_existing_target_batch.py` (batch existing-target SMS migration). That script signs and issues HTTPS requests directly against the Huawei Cloud IAM, SMS, ECS, VPC, and EVS REST APIs (no KooCLI/`hcloud` involved) to create migration projects, register migration tasks against pre-existing target servers, and poll them to completion. `scripts/mgc_migrate.py` remains available for the single-source SMS/rsync workflow, and `scripts/repair_boot_via_helper.py` performs post-migration boot-disk/SSH repair via a temporary helper ECS. Default policy is `SMS` first; when precheck/runtime indicates an incompatible source (for example `SMS.6504`), single-source runs switch to rsync phases (`full_sync -> incremental_sync -> cutover_sync`).

**Applicable scenarios**:
- Batch-migrating multiple sources to pre-existing target ECS instances matched by fixed IP.
- Migrating a single on-prem VMware VM, or an external GCP/AWS instance, into Huawei Cloud.
- Resuming a paused/interrupted batch run from checkpoint files.
- Repairing a target ECS that fails to boot or accept SSH after migration.
- Postmortem/experience-capture requests after a migration run.

**Example user requests**:
- "帮我批量迁移这几台 GCP 实例到已有的目标机器上。"
- "terraform apply 报错 SMS.1404，target disk 提示 IN-USE，怎么处理？"
- "迁移之后目标机器起不来，GRUB 报 Cannot open root device，帮我修。"
- "上次批量迁移中断了，帮我从 checkpoint 继续。"

**Relationship to `huawei-cloud-sms-host-migrator`**: that skill is a general, interactive SMS-console/API assistant for ad-hoc host migrations from any source (IDC, Alibaba Cloud, Tencent Cloud, AWS) to Huawei Cloud. This skill is narrower and automation-first: it drives the exact same SMS APIs through a fixed Terraform + Python pipeline (`main.tf` -> `scripts/run_migration.sh` -> `mgc_sms_existing_target_batch.py`/`mgc_migrate.py`) to get deterministic, repeatable batch runs, with built-in rsync/VPN-bridge fallback and boot-disk/SSH repair (`repair_boot_via_helper.py`) that `huawei-cloud-sms-host-migrator` does not provide. Prefer this skill when the user already has (or wants) a Terraform-driven, scriptable, resumable migration pipeline; prefer `huawei-cloud-sms-host-migrator` for one-off, console-guided migrations.

## Prerequisites

- **Terraform** `>= 1.5.0` on `PATH`. Verify with `terraform version`.
- **Python** 3.8+ on `PATH` (verify with `python3 --version`). The core migration/repair paths use only the standard library plus mutual imports between `mgc_sms_existing_target_batch.py` and `mgc_migrate.py`. Optional paths need extra packages, which are **not** bundled:
  - `pexpect` — required only for the rsync fallback SSH path (`scripts/mgc_migrate.py`); install with `pip install pexpect` when rsync fallback may be used.
  - `boto3` — required only when profiling an AWS source instance's security groups (`scripts/mgc_migrate.py`); install with `pip install boto3` when migrating from AWS.
  - The SMS-only batch flow needs neither package.
- This skill does **not** use Huawei Cloud KooCLI (`hcloud`). All Huawei Cloud API calls are issued as signed HTTPS requests from `scripts/*.py`; no separate CLI installation is required.
- **Credentials**: set `source_access_key`/`source_secret_key` and `destination_access_key`/`destination_secret_key` in `terraform.tfvars`. Terraform passes them to the migration script only as local-exec environment variables; never print them, log them, or paste them into chat. See [references/iam-policies.md](references/iam-policies.md) for the required IAM permissions.
- **Permission failure handling (MUST)**: if any API call fails with a permission/`403` error, open [references/iam-policies.md](references/iam-policies.md), show the user the exact missing permission and the minimal policy JSON, have them grant it in the IAM console, then pause until the user confirms the grant before retrying.

## Workflow

1. Confirm prerequisites before running any write operation.
2. Prepare Terraform inputs in `terraform.tfvars`.
3. Before migration, precheck and cleanup old source-bound SMS tasks if they can occupy the same source VM.
4. Execute Terraform so it calls `scripts/run_migration.sh` and `scripts/mgc_sms_existing_target_batch.py`.
5. Verify `out/migration_result.json`; for batch mode verify every `results[]` item has `source_sms_server_id`, `task_id`, and `task_state`.
6. Run postcheck for `vpc-migration`, EIP binding, source/target security-group connectivity, and SSH/TCP-22 reachability.
7. If SSH/TCP-22 fails after SMS or rsync reports success, inspect ECS console output before making more network changes.
8. If run was paused/restarted, continue from `out/resume_checkpoint_latest.json`, `out/resume_noagent_restart_summary_latest.json`, and `out/task_poll_latest.json`.
9. Troubleshoot by matching error codes and postcheck symptoms to the runbook.
10. Summarize recurring issues with the lessons reference when the user asks for postmortem/experience capture.

## Core Commands

Validate preconditions, then inspect the key files before execution:

- `main.tf`, `variables.tf`, `terraform.tfvars`

Run the migration:

```bash
terraform init
terraform apply -auto-approve
```

If apply returns `No changes` for `terraform_data.sms_existing_target_batch` (same run fingerprint), force one execution:

```bash
terraform apply -replace=terraform_data.sms_existing_target_batch -auto-approve
```

Terraform's local-exec maps tfvars into runtime env vars and calls:

- `scripts/run_migration.sh`
- `python3 scripts/mgc_sms_existing_target_batch.py`

Core API chain executed by the script:

1. `POST /v3/privacy-agreements`
2. `POST /v3/migprojects`
3. `GET /v3/sources`
4. `POST /v1.1/{project_id}/cloudservers`
5. `POST /v3/tasks`
6. `POST /v3/tasks/{task_id}/action` (`start`)

Boot/SSH repair (run only after diagnosing a boot or SSH regression per Best Practices):

```bash
PYTHONPATH=. python3 scripts/repair_boot_via_helper.py --target-server-id <target_id> --target-reset-password '<StrongPassword>'
```

## Parameter Confirmation

Confirm these `terraform.tfvars` values with the user before applying (defaults shown are used unless the user requests changes):

| Parameter | Required | Default | Notes |
|---|---|---|---|
| `source_access_key` / `source_secret_key` | Yes | — | Never echo or hardcode; see Prerequisites |
| `destination_access_key` / `destination_secret_key` | Yes | — | Never echo or hardcode; see Prerequisites |
| `source_server_ids` | Yes | — | Batch list; mapped to destination ECS by fixed IP |
| `target_image_id` | Conditional | — | Required only if target ECS must be recreated in resume flow |
| `source_region` | No | `ap-southeast-3` | |
| `destination_region` | No | `ap-southeast-3` | |
| `source_network_cidr` | Conditional | — | Source network CIDR for VPN bridge routes; required when `enable_vpn_bridge=true` and `source_private_ip` is empty (no hard-coded fallback) |
| `eip_bandwidth_mbps` | No | `100` | |
| `sms_endpoint` | No | `https://sms.ap-southeast-3.myhuaweicloud.com` | |

Confirm with the user before running: the exact `source_server_ids` batch, and that overwriting existing data on the matched target ECS instances is accepted (SMS migration side effect).

## Output Format

Check the result artifact:

```bash
cat out/migration_result.json
```

For batch mode, ensure the JSON includes at least:

- top-level `migration_project_id` (or creation error details)
- `results[]` with per-source `source_sms_server_id`
- per-source `task_id`
- per-source `target_vm_id`
- per-source `task_state`

If any per-source `task_state` is not terminal or the user asks for deeper diagnosis, use the troubleshooting guidance in [references/runbook.md](references/runbook.md). Treat existing `out/migration_result.json` as historical unless it was just generated in the current run.

For a complete run package, also keep:

- `out/precheck_task_cleanup.json`
- `out/task_poll_latest.json`
- `out/precheck_source_checks.json`
- `out/task_poll_retry_latest.json` (when prior round failed and retried)
- `out/resume_checkpoint_latest.json` (when paused/resumed)
- `out/resume_noagent_restart_summary_latest.json` (when recreated target/tasks from checkpoint)
- `out/monitor_checkpoint_latest.json` (when monitoring continues after restart)
- `out/postcheck_network.json`
- `out/rsync_execution.json` (when fallback path is used)
- `out/target_console_output*.txt` (when SSH/TCP-22 postcheck fails)

## Verification Method

Run the three verification tiers in [references/verification-method.md](references/verification-method.md) before treating a migration as done: installation verification (Terraform/Python present), configuration verification (credentials resolve without printing secrets), and functional verification (every `results[]` entry reaches a terminal `task_state` and SSH/TCP-22 postcheck passes).

## Best Practices

Apply existing built-in fallbacks before manual changes:

- If task creation returns `SMS.6617`, allow fallback from `MIGRATE_BLOCK` to `MIGRATE_FILE`.
- If source check returns `SMS.6504`, skip SMS task creation and switch to rsync staged migration.
- If task creation returns `SMS.1404` with `error_param` containing `available` vs `IN-USE`, retry without explicit `target_server.disks` mapping and/or repair target boot-disk attachment baseline before recreating task.
- If task creation returns `SMS.6602`, allow retry with `use_public_ip=false`.
- If task creation returns `SMS.7605`, allow cleanup of failed task and retry.
- If `SMS.7605` persists even after retry/new target ECS, check and delete historical tasks bound to the same source (including old `MIGRATE_SUCCESS` tasks), then retry.
- If `SMS.6603` appears, stop and require SMS-Agent installation/start on source host.
- If diagnosis returns `SMS.0515` (`Source disk info changed`), restart source SMS-Agent, refresh source disk info, then recreate/start target task from the latest checkpoint summary.
- If migration project creation returns `SMS.8115`, clean old migration projects to bring total count below 50, then rerun `terraform apply`:
  - `python3 scripts/mgc_cleanup_migprojects.py` (dry-run list) then `python3 scripts/mgc_cleanup_migprojects.py --apply` (delete auto-generated `mgc*` projects).
  - The account default project (`isdefault=true`) cannot be deleted via the API: DELETE returns `HTTP 400 SMS.7303`. Set another migration project as the account default in the SMS/MgC console first, then delete the old default.
- If VPC creation fails with `VPC.0114` (quota exceeded), stop and free quota first (delete unused VPC or increase quota), then rerun `terraform apply`.
- If task query returns `SMS.7703` (`Task doesn't exist`), do not trust stale `task_id`; query live task list by source and continue with the current task.
- If task is `RUNNING` but `progress` is null, keep polling by task `state` and verify target ECS status in parallel.
- If task is `RUNNING` with progress over 100 in `MIGRATE_LINUX_FILE-*`, keep polling until terminal state; do not mark success before `all_terminal=true`.
- If task is `MIGRATE_SUCCESS` and target ECS is `ACTIVE` but SSH/TCP-22 is `closed_or_timeout`, inspect `out/postcheck_network.json` and ECS console output before adding more SG rules.
- If target ECS has boot panic (`VFS: Cannot open root device "/dev/vdb1"`/`unknown-block(0,0)`) or SSH auth regression after migration, use one deterministic repair path:
  - `PYTHONPATH=. python3 scripts/repair_boot_via_helper.py --target-server-id <target_id> --target-reset-password '<StrongPassword>'`
  - This script includes fixed root-device rewrite (`root=/dev/vda1`), SSH password-login hardening (`PermitRootLogin yes`, `PasswordAuthentication yes`, `ssh_pwauth: true`), and offline root password write (`chpasswd`).
  - The script also auto-cleans stale `boot-repair-*` helpers before/after run, and auto-deletes the current helper after success (use `--keep-helper` only when explicitly needed).
- If console output contains cloud-init `Failed loading yaml blob` or `unknown escape character 's'` near `PasswordAuthentication\s`, treat target user-data bootstrap as invalid; fix `build_linux_ssh_user_data_b64`/target creation user-data quoting, recreate or repair the target, then rerun postcheck.
- If console output shows only `Starting OpenSSH server daemon...` without a clear started service and `ci-info: no authorized ssh keys fingerprints found`, validate sshd/firewall/root auth from VNC/serial console or rebuild with valid cloud-init.

Do not invent alternative API sequences unless the user explicitly asks to modify migration logic. Prefer read-only/`Describe`/`List`/`Show` calls when only diagnosing, and require explicit user confirmation before any operation that overwrites or restarts a target ECS, or resets its password.

### Migration Problem and Experience Summary

When the user asks for "迁移过程的问题总结", "经验复盘", "踩坑记录", or "postmortem", load [references/lessons-learned.md](references/lessons-learned.md) and report in this order:

1. Symptom and code (`VPC.0114`, `SMS.1404`, `SMS.0515`, `SMS.7703`, `SMS.6603`, `SSH closed_or_timeout`, etc.).
2. Root cause validated from logs/output.
3. Corrective action already proven in this repo.
4. Preventive rule to apply before next run.
5. Concrete timestamps from latest result JSON (for example `task_started_at_cn`, `task_finished_at_cn`) to avoid stale-history confusion.

## References

- [references/iam-policies.md](references/iam-policies.md) — required IAM permissions and minimal policy JSON.
- [references/verification-method.md](references/verification-method.md) — installation/configuration/functional verification steps.
- [references/acceptance-criteria.md](references/acceptance-criteria.md) — pass/fail criteria for a migration run.
- [references/runbook.md](references/runbook.md) — command-level execution checklist, tfvars-to-env mapping, error-code-oriented diagnosis steps, post-run verification checklist.
- [references/lessons-learned.md](references/lessons-learned.md) — structured migration issue summary (`symptom -> root cause -> action -> prevention`) and reusable troubleshooting experience.
- [references/reuse-bundle.md](references/reuse-bundle.md) — packaged migration assets/manifest and reusable command sequence for future similar migrations.
- [references/migration-skill-summary.md](references/migration-skill-summary.md) — concise end-to-end summary of this skill and the latest validated run facts.

## Notes

- Never echo, log, or hardcode `source_access_key`/`source_secret_key`/`destination_access_key`/`destination_secret_key`; they must only flow through `terraform.tfvars` -> Terraform local-exec env vars.
- SMS migration overwrites data on the target ECS; always get explicit user confirmation before `terraform apply` or `repair_boot_via_helper.py --target-reset-password`.
- `repair_boot_via_helper.py` creates a temporary helper ECS attached to the target's boot volume; confirm it is auto-deleted after success, and clean it up manually if a run is interrupted.
- Known limitation: `SMS.7703` can surface from stale historical `out/migration_result.json`; always re-query the live task list by source rather than trusting a cached `task_id`.
- `TARGET_ADMIN_PASSWORD` has no built-in default; it must be set explicitly to a strong password before running `mgc_migrate.py`/`mgc_sms_existing_target_batch.py`/the AWS-source scripts.
- If `mgc_migrate.py`'s rsync fallback needs to recover from a target SSH auth failure, it temporarily injects a migration-only SSH key and loosens the target's `PasswordAuthentication`/`PermitRootLogin`; this now requires explicit `CONFIRM_TARGET_SSH_BOOTSTRAP=yes` and is reverted automatically (key removed, `sshd_config` restored) once the migration finishes.
- `ENABLE_VPN_BRIDGE=true` requires `LOCAL_VPC_ID` to be set explicitly (the bridge host's own VPC ID is no longer auto-detected via the cloud metadata endpoint).
- `ENABLE_VPN_BRIDGE=true` also requires `source_network_cidr` (or `source_private_ip` as an IPv4/CIDR). If both are empty the script raises an explicit error instead of silently using a hard-coded network.
- The account's default SMS migration project (`isdefault=true`) cannot be deleted via the API (`SMS.7303`); to remove it, first set another project as default in the SMS/MgC console. `scripts/mgc_cleanup_migprojects.py` reports and skips default projects automatically.
- Optional dependencies: `pexpect` is needed only for the rsync fallback and `boto3` only for AWS-source security-group profiling; the SMS-only flow runs on the standard library alone.
