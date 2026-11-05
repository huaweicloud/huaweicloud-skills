---
name: huawei-cloud-migration-ecs-across-region
description: |
  Execute and troubleshoot single-source Huawei Cloud server migration in this repository via SMS with rsync fallback, orchestrated by Terraform + `scripts/mgc_migrate.py` against the Huawei Cloud SMS/ECS/VPC/IAM REST APIs. Also includes a standalone rsync-based path (`scripts/aws_to_huawei_direct.py`/`aws_to_huawei_rsync.py` via `scripts/run_aws_migration.sh`) for migrating AWS EC2 sources directly into Huawei Cloud.
  Use when the user asks to migrate an ECS instance, an AWS EC2 instance, or an on-prem VMware VM to Huawei Cloud (especially `la-north-2` -> `la-south-2`), run the end-to-end workflow (`terraform init/apply`), validate prerequisites, map `terraform.tfvars` to runtime env vars, inspect `out/migration_result.json`, diagnose post-run SSH/EIP/cloud-init failures, or diagnose SMS/MGC errors such as SMS.6504, SMS.6602, SMS.6603, SMS.6617, SMS.7605, SMS.7703, and SMS.8115.
triggers:
  - "migrate ECS instance to Huawei Cloud"
  - "Huawei Cloud ECS cross-region migration"
  - "Huawei Cloud SMS migration"
  - "Huawei Cloud MGC migration"
  - "cross-region migration"
  - "AWS EC2 migration"
  - "rsync fallback"
  - "cloud-init repair"
  - "跨区域迁移"
  - "AWS 迁移"
  - "MGC/SMS 迁移流程"
  - "迁移排障"
  - "迁移复盘"
tags: [huawei-cloud, migration, sms, mgc, terraform]
---

# MGC Cross-Region Migration

## Overview

This skill runs the single-source Huawei Cloud server migration flow implemented in this repository, from precheck to task startup and result validation. It keeps execution deterministic by following the exact command sequence and error-handling rules already implemented in `scripts/mgc_migrate.py`.

**Architecture**: Terraform (`main.tf`) reads `terraform.tfvars`, maps the values to runtime environment variables, and invokes `scripts/run_migration.sh`, which calls `python3 scripts/mgc_migrate.py`. That script signs and issues HTTPS requests directly against the Huawei Cloud IAM, SMS, ECS, and VPC REST APIs (no KooCLI/`hcloud` involved) to create a migration project, register a migration task, and poll it to completion. Default policy is `SMS` first; when precheck/runtime indicates an incompatible source (for example `SMS.6504`), the script switches to rsync phases (`full_sync -> incremental_sync -> cutover_sync`).

**Applicable scenarios**:
- Migrating a single on-prem VMware VM or another-cloud ECS instance into Huawei Cloud via Terraform + SMS/rsync (`scripts/mgc_migrate.py`).
- Migrating an AWS EC2 instance directly into Huawei Cloud via the standalone rsync path (`scripts/run_aws_migration.sh` + `aws_to_huawei_direct.py`/`aws_to_huawei_rsync.py`), when the source is AWS-specific (EC2 PEM-key auth, AWS CLI/API source discovery) rather than going through SMS.
- Source hosts that SMS cannot handle natively, requiring rsync-based staged migration instead.
- Post-migration troubleshooting: SSH/TCP-22 unreachable, cloud-init failures, stale SMS tasks/quota errors.
- Postmortem/experience-capture requests after a migration run.

**Example user requests**:
- "Migrate this VMware VM in la-north-2 to la-south-2."
- "帮我把这台 AWS EC2 实例迁移到华为云。"
- "terraform apply 报错 SMS.8115，怎么处理？"
- "SMS 显示迁移成功但是 SSH 连不上目标机器，帮我排查。"
- "帮我把这次迁移过程的踩坑记录总结一下。"

## Prerequisites

- **Terraform** `>= 1.5.0` on `PATH`. Verify with `terraform version`.
- **Python** 3.8+ on `PATH` (verify with `python3 --version`). `scripts/mgc_migrate.py` only uses the standard library; the optional VPN-bridge fallback path additionally imports `pexpect`, install it only if that path is used (`pip install pexpect`).
- This skill does **not** use Huawei Cloud KooCLI (`hcloud`). All Huawei Cloud API calls are issued as signed HTTPS requests from `scripts/mgc_migrate.py`; no separate CLI installation is required.
- **Credentials**: set `access_key` / `secret_key` (and `domain_name` if needed) in `terraform.tfvars`. Terraform passes them to the migration script only as local-exec environment variables (`HC_AK` / `HC_SK`); never print them, log them, or paste them into chat. See [references/iam-policies.md](references/iam-policies.md) for the required IAM permissions.
- **Permission failure handling (MUST)**: if any API call fails with a permission/`403` error, open [references/iam-policies.md](references/iam-policies.md), show the user the exact missing permission and the minimal policy JSON, have them grant it in the IAM console, then pause until the user confirms the grant before retrying.

## Workflow

1. Confirm prerequisites before running any write operation.
2. Prepare Terraform inputs in `terraform.tfvars`.
3. Before migration, precheck and cleanup old source-bound SMS tasks if they can occupy the same source VM.
4. Execute Terraform so it calls `scripts/run_migration.sh` and `python scripts/mgc_migrate.py`.
5. Verify `out/migration_result.json`; if method is rsync, also verify `out/rsync_execution.json`.
6. Run postcheck for `vpc-migration`, EIP binding, source/target security-group connectivity, and SSH/TCP-22 reachability.
7. If SSH/TCP-22 fails after SMS or rsync reports success, inspect ECS console output before making more network changes.
8. Troubleshoot by matching error codes and postcheck symptoms to the runbook.
9. Summarize recurring issues with the lessons reference when the user asks for postmortem/experience capture.

## Core Commands

Validate preconditions, then inspect the key files before execution:

- `main.tf`, `variables.tf`, `terraform.tfvars`

Run the migration:

```bash
terraform init
terraform apply -auto-approve
```

If apply returns `No changes` for `terraform_data.mgc_region_migration` (same run fingerprint), force one execution:

```bash
terraform apply -replace=terraform_data.mgc_region_migration -auto-approve
```

Terraform's local-exec maps tfvars into runtime env vars and calls:

- `scripts/run_migration.sh`
- `python scripts/mgc_migrate.py`

Core API chain executed by the script:

1. `POST /v3/privacy-agreements`
2. `POST /v3/migprojects`
3. `GET /v3/sources`
4. `POST /v1.1/{project_id}/cloudservers`
5. `POST /v3/tasks`
6. `POST /v3/tasks/{task_id}/action` (`start`)

## Parameter Confirmation

Confirm these `terraform.tfvars` values with the user before applying (defaults shown are used unless the user requests changes):

| Parameter | Required | Default | Notes |
|---|---|---|---|
| `access_key` / `secret_key` | Yes | — | Never echo or hardcode; see Prerequisites |
| `source_server_id` | Yes | — | Must already be registered/connected in SMS |
| `target_image_id` | Yes | — | Must exist in `target_region` |
| `source_region` | No | `la-north-2` | |
| `target_region` | No | `la-south-2` | |
| `target_vpc_name` | No | `vpc-migration` | Confirm target-region VPC quota before creation |
| `sms_endpoint` | No | `https://sms.ap-southeast-3.myhuaweicloud.com` | |
| `preferred_migration_method` | No | `sms` | Falls back to rsync automatically on `SMS.6504` |
| `rsync_source_host/port/user/password` | Conditional | — | Required only for rsync fallback |
| `target_rsync_ssh_key` | Conditional | — | Path on the source host to an operator-provisioned private key already trusted by the target; required for rsync fallback |

Confirm with the user before running: source server ID, target image ID, and that overwriting existing data on the target ECS is accepted (SMS migration side effect).

## Output Format

Check the result artifact:

```bash
cat out/migration_result.json
```

Ensure the JSON includes at least:

- `migproject_id`
- `task_id`
- `source_sms_server_id`
- `target_server_id`
- `task_state`

If `task_state` is not terminal or the user asks for deeper diagnosis, use the troubleshooting guidance in [references/runbook.md](references/runbook.md). Treat existing `out/migration_result.json` as historical unless it was just generated in the current run.

For a complete run package, also keep:

- `out/precheck_task_cleanup.json`
- `out/postcheck_network.json`
- `out/task_poll_latest.json`
- `out/precheck_source_checks.json`
- `out/rsync_execution.json` (when fallback path is used)
- `out/target_console_output*.txt` (when SSH/TCP-22 postcheck fails)

## Verification Method

Run the three verification tiers in [references/verification-method.md](references/verification-method.md) before treating a migration as done: installation verification (Terraform/Python present), configuration verification (credentials resolve without printing secrets), and functional verification (`out/migration_result.json` reaches a terminal `task_state` and SSH/TCP-22 postcheck passes).

## Best Practices

Apply existing built-in fallbacks before manual changes:

- If task creation returns `SMS.6617`, allow fallback from `MIGRATE_BLOCK` to `MIGRATE_FILE`.
- If source check returns `SMS.6504`, skip SMS task creation and switch to rsync staged migration.
- If task creation returns `SMS.6602`, allow retry with `use_public_ip=false`.
- If task creation returns `SMS.7605`, allow cleanup of failed task and retry.
- If `SMS.7605` persists even after retry/new target ECS, check and delete historical tasks bound to the same source (including old `MIGRATE_SUCCESS` tasks), then retry.
- If `SMS.6603` appears, stop and require SMS-Agent installation/start on source host.
- If migration project creation returns `SMS.8115`, clean old migration projects (prefer auto-generated `mgc*` projects) to bring total count below 50, then rerun `terraform apply`.
- If VPC creation fails with `VPC.0114` (quota exceeded), stop and free quota first (delete unused VPC or increase quota), then rerun `terraform apply`.
- If task query returns `SMS.7703` (`Task doesn't exist`), do not trust stale `task_id`; query live task list by source and continue with the current task.
- If task is `RUNNING` but `progress` is null, keep polling task `state` and verify target ECS status in parallel.
- If task is `MIGRATE_SUCCESS` and target ECS is `ACTIVE` but SSH/TCP-22 is `closed_or_timeout`, inspect `out/postcheck_network.json` and ECS console output before adding more SG rules.
- If console output contains cloud-init `Failed loading yaml blob` or another YAML parse error, treat target user-data bootstrap as invalid; recreate the target, then rerun postcheck. user-data carries only SSH-config-independent bootstrap (network reachability and the optional VPN client).
- If console output shows only `Starting OpenSSH server daemon...` without a clear started service and `ci-info: no authorized ssh keys fingerprints found`, verify network reachability and the operator-provisioned key trust on the target from VNC/serial console; this skill never writes `authorized_keys`, edits `sshd_config`, or restarts `sshd`.

Do not invent alternative API sequences unless the user explicitly asks to modify migration logic. Prefer read-only/`Describe`/`List`/`Show` calls when only diagnosing, and require explicit user confirmation before any operation that overwrites or restarts the target ECS.

### Migration Problem and Experience Summary

When the user asks for "迁移过程的问题总结", "经验复盘", "踩坑记录", or "postmortem", load [references/lessons-learned.md](references/lessons-learned.md) and report in this order:

1. Symptom and code (`VPC.0114`, `SMS.7703`, `SMS.6603`, `SSH closed_or_timeout`, etc.).
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

- Never echo, log, or hardcode `access_key`/`secret_key`; they must only flow through `terraform.tfvars` -> Terraform local-exec env vars.
- SMS migration overwrites data on the target ECS; always get explicit user confirmation before `terraform apply`.
- This skill is currently exercised on Windows paths/PowerShell in some environments and bash/git-bash in others; confirm the user's shell before pasting commands verbatim.
- Known limitation: `SMS.7703` can surface from stale historical `out/migration_result.json`; always re-query the live task list by source rather than trusting a cached `task_id`.
- `target_admin_password` (-> `TARGET_ADMIN_PASSWORD`) has no built-in default; it must be set explicitly to a strong password before running `mgc_migrate.py` or the AWS-source scripts. In `mgc_migrate.py` and the AWS-source scripts it is used only as the create-instance API `adminPass`; user-data never enables password SSH login, edits `sshd_config`, or restarts `sshd` on the target.
- The rsync fallback authenticates to the target only with an operator-provisioned SSH key: set `TARGET_RSYNC_SSH_KEY` to the private key path on the source host, and have operations trust its public half on the target (or pre-establish source-to-target passwordless SSH). The AWS-source scripts (`aws_to_huawei_direct.py`/`aws_to_huawei_rsync.py`) use the same model: `rsync` runs on the source host and pushes to the target over `ssh -i`, so each transfer has exactly one remote side and the key must exist on the source host. If the key is missing or denied, the script stops with manual guidance instead of modifying the target. The rsync fallback never writes `authorized_keys`, changes `sshd_config`, or restarts `sshd`.
- `ENABLE_VPN_BRIDGE=true` requires `local_vpc_id`/`LOCAL_VPC_ID` to be set explicitly (the bridge host's own VPC ID is no longer auto-detected via the cloud metadata endpoint).

**Relationship to `huawei-cloud-sms-host-migrator`**: that skill is a general, interactive SMS-console/API assistant for ad-hoc host migrations from any source (IDC, Alibaba Cloud, Tencent Cloud, AWS) to Huawei Cloud. This skill is narrower and automation-first: it drives the same underlying APIs (SMS for most sources, direct rsync for AWS EC2) through a fixed Terraform + Python pipeline (`main.tf` -> `scripts/run_migration.sh` -> `mgc_migrate.py`, or `scripts/run_aws_migration.sh` -> `aws_to_huawei_direct.py`/`aws_to_huawei_rsync.py`) for deterministic, single-source runs with built-in rsync/VPN-bridge fallback that `huawei-cloud-sms-host-migrator` does not provide. Prefer this skill when the user already has (or wants) a Terraform-driven, scriptable migration pipeline for a single source; prefer `huawei-cloud-sms-host-migrator` for one-off, console-guided migrations.
