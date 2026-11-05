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
- Root cause: `terraform_data` trigger fingerprint did not change from previous successful run (`sms_existing_target_batch` in current repo).
- Corrective action: run `terraform apply -replace=terraform_data.sms_existing_target_batch -auto-approve`.
- Prevention: for deliberate reruns with same tfvars, use `-replace` explicitly.

### `SMS.6603` (source not connected)

- Symptom: task creation/start fails with source connectivity error.
- Root cause: SMS-Agent is not installed, not running, or source not connected in SMS.
- Corrective action: install/start SMS-Agent on source host, verify source is connected, rerun.
- Prevention: perform source connectivity precheck before Terraform apply.

### `SMS.0202` (AK/SK authentication failed)

- Symptom: SMS-Agent `startup.sh` reaches `querying enterprise projects` and returns `SMS.0202: AK/SK authentication failed`.
- Root cause: destination AK/SK is expired, revoked, or incorrect. HTTP 401 on IAM `/v3/projects` confirms the credential is invalid globally.
- Corrective action: obtain new valid AK/SK, verify with IAM list-projects API call before rerunning agent registration.
- Prevention: before SMS-Agent registration, validate AK/SK by calling `GET https://iam.<region>.myhuaweicloud.com/v3/projects`. A 401 means the credential is invalid globally, not region-specific.

### Stale SMS-Agent process (cwd deleted)

- Symptom: `startup.sh` reports `The SMS-Agent is already running` but `/proc/<pid>/cwd` shows `(deleted)` and config files are missing.
- Root cause: a previous agent installation directory was deleted while `linuxmain` processes kept running with stale cwd.
- Corrective action: `sudo pkill -9 -f linuxmain`, re-extract fresh `SMS-Agent.tar.gz`, rerun `sudo ./startup.sh`.
- Prevention: before re-registering, always kill stale `linuxmain` processes and re-extract a fresh agent package.

### Target disk mapping missing disk_id (source/target device name mismatch)

- Symptom: `terraform apply` fails with `Target disk mapping missing disk_id for source disk '/dev/sdb'` during SMS task creation.
- Root cause: external source (GCP/AWS) uses `/dev/sd*` or `/dev/nvme*n*` naming but Huawei target uses `/dev/vd*`. Device-name lookup misses, and only boot disk has `boot_index=0` fallback.
- Corrective action: script now normalizes device names (`/dev/sda` -> `/dev/vda`) and falls back to index-based mapping (BOOT first, then NORMAL by order) when device-name matching fails.
- Prevention: for external-source migrations with multiple disks, normalize device naming between source and target before building disk mapping. Do not assume source and target share the same device prefix.

### Post-SMS SSH unreachable with GCP LABEL= fstab

- Symptom: SMS task is `MIGRATE_SUCCESS` and target ECS is `ACTIVE`, but SSH/TCP-22 times out from all locations.
- Root cause: GCP source fstab uses `LABEL=cloudimg-rootfs` / `LABEL=BOOT` / `LABEL=UEFI` entries. SMS agent regenerates fstab with UUIDs but GRUB retains `root=LABEL=...` or wrong root device, causing boot hang or kernel panic.
- Corrective action: run `PYTHONPATH=. python3 scripts/repair_boot_via_helper.py --target-server-id <id> --target-reset-password '<password>'` to rewrite `root=/dev/vda1` in grub.cfg via helper attach workflow.
- Prevention: for GCP sources with LABEL= fstab entries, expect GRUB root-device repair after SMS migration.

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

### `SMS.1404` (target disk state mismatch)

- Symptom: batch SMS tasks fail at `ATTACH_AGENT_IMAGE-90` with `MIGRATE_FAIL` and `error_param` containing `available` vs `IN-USE`.
- Root cause: target boot-disk mapping state is inconsistent at task creation/start (expected available by SMS validation, but disk is attached/in-use at runtime).
- Corrective action:
  - retry task creation without strict `target_server.disks` mapping when supported by script fallback.
  - repair/rebuild target baseline so expected boot volume attachment state is consistent, then recreate/start task.
- Prevention:
  - when resuming old runs, verify target VM/disk baseline before reusing historical task context.
  - avoid using stale target IDs and stale disk mapping after long pauses/restarts.

### `SMS.0515` (source disk info changed)

- Symptom: rebuild diagnosis reports `current_blocker=source_side_sms_0515`.
- Root cause: source-side disk metadata changed after pause/restart window, and SMS source state no longer matches previous task context.
- Corrective action: restart source SMS-Agent, refresh source metadata/precheck, then recreate and restart migration tasks from the latest checkpoint.
- Prevention: for paused runs (hours), always run source-side health/precheck again before resume.

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

### SSH `closed_or_timeout` after SMS success

- Symptom: SMS task reaches `MIGRATE_SUCCESS` and target ECS is `ACTIVE`, but `out/postcheck_network.json` reports `source_to_target_eip_22` and/or `direct_to_target_eip_22` as `closed_or_timeout`.
- Root cause: do not assume this is only a VPC/SG problem. In the 2026-05-19 local run, ECS console output showed cloud-init rejected target user-data with `Failed loading yaml blob` and `unknown escape character 's'` near `PasswordAuthentication\s`, so SSH password/root-login/firewall bootstrap commands could be skipped.
- Corrective action:
  - archive `out/target_console_output*.txt` with the JSON artifacts.
  - fix target user-data generation (`build_linux_ssh_user_data_b64`) to emit valid cloud-init YAML, or repair sshd/firewall/root auth from VNC/serial console.
  - recreate/reboot the target and rerun SSH/TCP-22 postcheck.
- Prevention:
  - validate generated cloud-init YAML before target ECS creation.
  - after SMS success, treat login readiness as a separate postcheck from task state and ECS `ACTIVE`.
  - once EIP and expected peer SG rules are present, inspect console output before repeatedly adding network rules.

### `status=203/EXEC` / `Python venv not found` after migration

- Symptom: target `canteen-ordering.service` fails with `Control process exited ... status=203/EXEC`, and restart script reports `Python venv not found: /opt/canteen-ordering/venv/bin/python`.
- Root cause: source app directory already had incomplete venv layout before migration (only `venv/lib/pythonX/site-packages`, missing `venv/bin/*` and `pyvenv.cfg`). SMS `MIGRATE_FILE` copied this drift as-is, so target booted with the same broken runtime path.
- Corrective action:
  - rebuild source venv to standard layout (`python3 -m venv /opt/canteen-ordering/venv` + `pip install -r requirements.txt`);
  - resync/re-migrate runtime files (or copy fixed venv to target);
  - restart target service and verify both `http://127.0.0.1:8000/health` and `http://127.0.0.1/health`.
- Prevention:
  - before creating SMS/rsync task, run source-side runtime artifact precheck for required files:
    - `/opt/canteen-ordering/venv/bin/python`
    - `/opt/canteen-ordering/venv/pyvenv.cfg`
  - if precheck fails, repair source artifacts first; do not rely on migration stage to recreate app runtime.

### Kernel panic `root=/dev/vdb1` after SMS success

- Symptom: SMS task is already `MIGRATE_SUCCESS` and ECS is `ACTIVE`, but SSH is still unavailable; console shows `Cannot open root device "/dev/vdb1"` and `Kernel panic - not syncing`.
- Root cause: boot cmdline/grub config on migrated disk still points to stale source-side root device (`/dev/vdb1`), while target boot disk is attached as `/dev/vda`.
- Corrective action:
  - attach target boot volume to a helper ECS and patch root parameters in `/etc/default/grub*` and `/boot/grub/grub.cfg` from `/dev/vdb*` to `/dev/vda*` or correct root UUID.
  - regenerate grub config (`update-grub` or `grub-mkconfig`) and reattach/reboot target.
  - run password/SSH recovery and perform direct SSH login verification.
- Prevention:
  - after SMS `MIGRATE_SUCCESS`, always run network postcheck plus console boot check.
  - if 22/TCP remains closed while EIP+SG look correct, inspect/repair root-device boot args before adding more network rules.

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
