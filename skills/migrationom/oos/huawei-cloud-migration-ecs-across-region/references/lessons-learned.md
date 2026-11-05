# Migration Issues and Lessons Learned

Use this file to summarize migration incidents in a stable structure:

1. Symptom and error code
2. Root cause
3. Corrective action
4. Prevention rule for next run

## Problem Pattern Matrix

### `VPC.0114` (target VPC creation failed)

- Symptom: `terraform apply` fails while creating target VPC (`vpc-migration`) in `la-south-2`.
- Root cause: target-region VPC quota is full (`used == quota`).
- Corrective action: delete one unused VPC or increase VPC quota, then rerun `terraform apply -auto-approve`.
- Prevention: check VPC quota before every apply when VPC may be auto-created.

### `SMS.7703` (task does not exist)

- Symptom: querying a task by ID returns `Task doesn't exist`.
- Root cause: stale `task_id` from historical `out/migration_result.json`.
- Corrective action: use `task_id` from the latest run output, or query current task list by source server.
- Prevention: treat `out/migration_result.json` as historical unless it was generated in the current run.

### `RUNNING` with `progress = null`

- Symptom: task state is `RUNNING`, but progress field is empty.
- Root cause: SMS may omit numeric progress even when migration is active.
- Corrective action: continue polling task `state` and verify target ECS status in parallel.
- Prevention: do not use `progress` as the only health indicator.

### Terraform `No changes` on rerun

- Symptom: `terraform apply -auto-approve` returns `No changes` and does not trigger migration again.
- Root cause: `terraform_data.mgc_region_migration` trigger fingerprint did not change from previous successful run.
- Corrective action: run `terraform apply -replace=terraform_data.mgc_region_migration -auto-approve`.
- Prevention: for deliberate reruns with same tfvars, use `-replace` explicitly.

### `SMS.6603` (source not connected)

- Symptom: task creation/start fails with source connectivity error.
- Root cause: SMS-Agent is not installed, not running, or source not connected in SMS.
- Corrective action: install/start SMS-Agent on source host, verify source is connected, rerun.
- Prevention: perform source connectivity precheck before Terraform apply.

### `SMS.6617` (block migration unsupported)

- Symptom: task creation fails for block migration mode.
- Root cause: source kernel does not support block migration.
- Corrective action: fallback to `MIGRATE_FILE` (already implemented in script retry path).
- Prevention: keep block->file fallback enabled; do not hard-force block mode.

### `SMS.6504` (source OS incompatible with SMS)

- Symptom: SMS source precheck (`OS_VERSION`) returns `ERROR` with `SMS.6504`.
- Root cause: source OS/kernel combination is outside SMS supported range.
- Corrective action: switch to rsync staged migration (`full_sync -> incremental_sync -> cutover_sync`) while keeping target ECS/VPC/EIP provisioning unchanged.
- Prevention: read source check result from API before creating SMS task, and fallback automatically when `SMS.6504` appears.

### `SMS.6602` (public IP mode mismatch)

- Symptom: task creation fails when using public IP mode.
- Root cause: environment/task constraints conflict with current public IP option.
- Corrective action: retry with `use_public_ip=false` (already implemented).
- Prevention: keep adaptive retry logic and report selected mode in execution logs.

### `SMS.7605` (failed/duplicate task residue)

- Symptom: new task creation blocked by existing failed residue task.
- Root cause: historical task residue (including prior successful tasks bound to the same source/target context) still occupied migration binding.
- Corrective action: cleanup old source-bound tasks first, then retry task creation; if still blocked, switch to a fresh target ECS and retry.
- Prevention: precheck existing tasks by source server before task creation, and purge obsolete historical tasks.

### `SMS.8115` (migration project quota exceeded)

- Symptom: creating migration project fails with `The quantity of MigProject must be lower than or equal to 50`.
- Root cause: accumulated historical migration projects reached platform quota (`count=50`).
- Corrective action: delete old migration projects (prefer auto-generated `mgc*` items), then rerun `terraform apply -auto-approve`.
- Prevention: add migration-project quota check/cleanup before each large rerun batch.

### SSH `connection reset/closed/timed out` after rsync cutover

- Symptom: source VM cannot SSH target private IP; errors include `kex_exchange_identification`, `Connection closed`, or timeout.
- Root cause: target ECS booted into emergency mode because migrated `/etc/fstab` contains stale source-disk UUID mounts.
- Corrective action:
  - read ECS console output (`os-getConsoleOutput`) and confirm missing UUID dependency failure.
  - enter VNC/serial emergency shell and repair `/etc/fstab` (remove/fix invalid UUID entries or mark `nofail`).
  - reboot target and re-validate source->target SSH.
- Prevention:
  - exclude `/etc/fstab` in rsync excludes by default.
  - add post-rsync boot-health check before declaring migration complete.

### rsync target SSH key missing or denied

- Symptom: rsync fallback stops with a message asking for `TARGET_RSYNC_SSH_KEY`, or target SSH reports `permission denied (publickey)`.
- Root cause: the target leg now uses only an operator-provisioned key; the script no longer injects a key or loosens target sshd settings.
- Corrective action:
  - have operations place the private key on the source host and set `TARGET_RSYNC_SSH_KEY` to its path.
  - trust the matching public key on the target, or pre-establish source-to-target passwordless SSH.
  - alternatively use the MGC/SMS console migration path.
- Prevention:
  - provision the key and target trust before starting the rsync fallback.
  - never expect the rsync target-auth path to write `authorized_keys`, change `sshd_config`, or restart `sshd`.

### AWS standalone rsync: `The source and destination cannot both be remote`

- Symptom: `aws_to_huawei_direct.py` / `aws_to_huawei_rsync.py` fail at the first sync phase with `The source and destination cannot both be remote.`
- Root cause: rsync does not support remote-to-remote transfers; an earlier version passed both `source_user@source_host:/` and `target_user@target_host:/`.
- Corrective action:
  - run rsync on the AWS source host and push to the target (`/` -> `target_user@target_host:/`), so only the target side is remote.
  - authenticate the target leg with the operator-provisioned `TARGET_RSYNC_SSH_KEY` (`ssh -i` + `BatchMode=yes`).
- Prevention:
  - keep exactly one remote side in every rsync invocation; the AWS path reads `target_rsync_ssh_key` from `terraform.tfvars` like the mgc fallback.

### SSH `closed_or_timeout` after SMS success

- Symptom: SMS task reaches `MIGRATE_SUCCESS` and target ECS is `ACTIVE`, but `out/postcheck_network.json` reports `source_to_target_eip_22` and/or `direct_to_target_eip_22` as `closed_or_timeout`.
- Root cause: do not assume this is only a VPC/SG problem. In the 2026-05-19 local run, ECS console output showed cloud-init rejected target user-data with `Failed loading yaml blob` and `unknown escape character 's'`, so the user-data bootstrap commands could be skipped.
- Corrective action:
  - archive `out/target_console_output*.txt` with the JSON artifacts.
  - fix target user-data generation (`build_linux_ssh_user_data_b64`) to emit valid cloud-init YAML; user-data carries only SSH-config-independent bootstrap (network reachability and the optional VPN client).
  - verify network reachability and the operator-provisioned key trust from VNC/serial console; never edit `sshd_config`, enable password/root login, or restart `sshd` as a repair step.
  - recreate/reboot the target and rerun SSH/TCP-22 postcheck.
- Prevention:
  - validate generated cloud-init YAML before target ECS creation.
  - after SMS success, treat login readiness as a separate postcheck from task state and ECS `ACTIVE`.
  - once EIP and expected peer SG rules are present, inspect console output before repeatedly adding network rules.

## Reusable Postmortem Template

Use this compact template in user-facing summaries:

```text
[Issue]
Symptom:
Root cause:
Action taken:
Prevention:
Evidence (file/log/timestamp):
```
