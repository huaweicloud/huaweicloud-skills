# Migration Runbook

## Quick Checklist

1. Confirm source server is visible in SMS source list and status is connected.
2. Confirm destination image ID exists in target region.
3. Confirm AK/SK permissions for IAM, ECS, VPC, SMS.
4. Confirm target-region VPC quota has free slot if target VPC may be auto-created.
5. Check and clean obsolete source-bound SMS tasks before starting a new migration.
6. Confirm rsync SSH parameters are present in `terraform.tfvars` for fallback (`rsync_source_host/port/user/password`).
7. If post-migration app readiness is required, precheck source app runtime artifacts (example: `/opt/canteen-ordering/venv/bin/python` and `venv/pyvenv.cfg`) before starting migration.
8. When source can only reach Codex VPN, prefer bridge mode (`enable_vpn_bridge=true`). Keep target VPN client bootstrap (`enable_target_vpn_client`) only as an optional fallback mode.
9. Confirm target ECS overwrite risk is accepted.
10. Run Terraform and verify `out/migration_result.json`.
11. For rsync runs, validate target boot/SSH health after sync; if SSH fails, inspect ECS console output before changing network policies.
12. For SMS runs, still validate SSH/TCP-22 and target console output; SMS `MIGRATE_SUCCESS` does not guarantee login readiness.
13. If execution was interrupted, resume from the latest checkpoint JSONs before starting a fresh run.

## Canonical Commands

```bash
cd skills/migrationom/oos/huawei-cloud-mgc-migration-ecs-gcp-to-hw
terraform init
terraform apply -auto-approve
terraform apply -replace=terraform_data.sms_existing_target_batch -auto-approve
cat out/migration_result.json
```

Use `-replace=terraform_data.sms_existing_target_batch` only when a rerun is required but normal apply reports `No changes`.

## tfvars -> Runtime Env Mapping

`main.tf` passes these variables to `scripts/mgc_sms_existing_target_batch.py`:

- `source_access_key` -> `SOURCE_ACCESS_KEY`
- `source_secret_key` -> `SOURCE_SECRET_KEY`
- `source_region` -> `SOURCE_REGION`
- `source_project_id` -> `SOURCE_PROJECT_ID`
- `destination_access_key` -> `DESTINATION_ACCESS_KEY`
- `destination_secret_key` -> `DESTINATION_SECRET_KEY`
- `destination_region` -> `DESTINATION_REGION`
- `destination_region_name` -> `DESTINATION_REGION_NAME`
- `destination_project_id` -> `DESTINATION_PROJECT_ID`
- `source_server_ids` -> `SOURCE_SERVER_IDS` (comma-separated)
- `eip_bandwidth_mbps` -> `EIP_BANDWIDTH_MBPS`
- `security_group_rule_description` -> `SG_RULE_DESCRIPTION`
- `sms_endpoint` -> `SMS_ENDPOINT`
- fixed output path -> `RESULT_PATH=out/migration_result.json`

For single-source migration or rsync fallback, `scripts/mgc_migrate.py` can still be invoked directly with its own env mapping.

## What Success Looks Like

`out/migration_result.json` includes non-empty values for:

- top-level `mode`
- top-level `migration_project_id` (or explicit project-create error)
- per-item `source_sms_server_id`
- per-item `target_vm_id`
- per-item `task_id`
- per-item `task_state`

## Error Handling Matrix

- `SMS.1404`
  - Meaning: task creation hits disk-attachment state mismatch (`available` vs `IN-USE`) during `ATTACH_AGENT_IMAGE`.
  - Action: retry CreateTask without `target_server.disks` mapping and ensure target boot-disk baseline is consistent before recreating task.
  - Evidence pattern: `subtask_info=ATTACH_AGENT_IMAGE-90` + `error_param` containing disk UUID and `available/IN-USE`.

- `SMS.0515`
  - Meaning: source disk metadata changed since last check (`Source disk info changed`).
  - Action: restart source SMS-Agent, refresh source metadata, then recreate/start tasks from the latest checkpoint summary.
  - Prevention: when paused for hours and resumed later, run source precheck and baseline checks before reusing old task context.

- `SMS.6504`
  - Meaning: source OS precheck incompatible with SMS.
  - Action: script switches to rsync fallback (`full_sync -> incremental_sync -> cutover_sync`).

- `SMS.6603`
  - Meaning: source server is not connected to SMS.
  - Action: install/start SMS-Agent on source server, then rerun.

- `SMS.0202`
  - Meaning: AK/SK authentication failed during SMS-Agent registration.
  - Action: validate AK/SK by calling `GET https://iam.<region>.myhuaweicloud.com/v3/projects`. If 401, obtain new valid AK/SK before rerunning agent registration.
  - Prevention: verify AK/SK globally before agent registration; a 401 means invalid globally, not region-specific.

- Stale SMS-Agent process (cwd deleted)
  - Meaning: `startup.sh` reports agent already running but `/proc/<pid>/cwd` shows `(deleted)`.
  - Action: `sudo pkill -9 -f linuxmain`, re-extract fresh `SMS-Agent.tar.gz`, rerun `sudo ./startup.sh`.
  - Prevention: kill stale processes and re-extract fresh agent before re-registering.

- Target disk mapping missing disk_id
  - Meaning: `terraform apply` fails with `Target disk mapping missing disk_id for source disk '/dev/sdb'`.
  - Action: script now normalizes device names (`/dev/sda` -> `/dev/vda`) and falls back to index-based mapping. If still failing, verify target ECS has enough data disks attached.
  - Prevention: for external-source multi-disk migrations, ensure device naming is normalized between source and target.

- Post-SMS SSH unreachable with GCP LABEL= fstab
  - Meaning: SMS `MIGRATE_SUCCESS` and ECS `ACTIVE` but SSH/TCP-22 times out.
  - Action: run `PYTHONPATH=. python3 scripts/repair_boot_via_helper.py --target-server-id <id> --target-reset-password '<password>'` to rewrite GRUB `root=/dev/vda1`.
  - Prevention: for GCP sources with LABEL= fstab entries, expect GRUB root-device repair after SMS migration.

- `SMS.6602`
  - Meaning: task creation cannot use current public IP mode.
  - Action: let script retry with `use_public_ip=false`.

- `SMS.6617`
  - Meaning: source kernel does not support block migration.
  - Action: let script fallback to `MIGRATE_FILE`.

- `SMS.7605`
  - Meaning: duplicate/failed task residue affects task creation.
  - Action: let script cleanup failed task and retry; if still `SMS.7605`, delete historical tasks bound to the same source (including old successful tasks), then retry with a fresh target ECS.

- `SMS.8115`
  - Meaning: migration-project quota reached (max 50).
  - Action: delete old migration projects (prefer auto-generated `mgc*` projects), then rerun `terraform apply -auto-approve`.
  - Helper: `python3 scripts/mgc_cleanup_migprojects.py` (dry-run) / `python3 scripts/mgc_cleanup_migprojects.py --apply`.
  - Limitation: the default project (`isdefault=true`) cannot be deleted via the API (`HTTP 400 SMS.7303`); set another project as default in the SMS/MgC console first.

- `VPC.0114`
  - Meaning: target-region VPC/router quota exceeded when creating target VPC.
  - Action: release one unused VPC or increase quota, then rerun `terraform apply -auto-approve`.

- `SMS.7703`
  - Meaning: queried `task_id` does not exist (often from stale historical output file).
  - Action: do not use old `task_id`; get latest task from current run output or list tasks by source server and pick the active one.

- `RUNNING` with progress greater than 100
  - Meaning: SMS migrate speed/progress fields are not strict completion indicators.
  - Action: keep monitoring by task `state` and subtask stage until terminal status.
  - Prevention: do not declare success before `all_terminal=true` in monitor summary.

- `SSH reset/closed/timed out after rsync`
  - Meaning: target ECS may not have reached normal boot state even when cloud status is `ACTIVE`.
  - Action: fetch ECS console output and check for emergency mode/systemd dependency failures (commonly stale `/etc/fstab` UUID entries), repair `/etc/fstab` via VNC/serial shell, reboot, then re-test SSH.
  - Prevention: keep `/etc/fstab` in rsync exclude list unless explicit disk-mount migration remap is prepared.

- `SSH closed_or_timeout after SMS success`
  - Meaning: SMS task can be terminal-success while target SSH is not reachable.
  - Action: check `out/postcheck_network.json` for EIP/SG/peer evidence, then inspect `out/target_console_output*.txt`.
  - If console output contains cloud-init `Failed loading yaml blob` or `unknown escape character 's'` near `PasswordAuthentication\s`, fix target user-data generation (`build_linux_ssh_user_data_b64`) or repair sshd/firewall/root auth from console, then recreate/reboot and retest.
  - Prevention: validate generated cloud-init YAML before target ECS creation, and archive console output whenever TCP/22 postcheck fails.

- `status=203/EXEC` or `Python venv not found` after migration
  - Meaning: application runtime path exists in unit/script, but executable artifact is missing on target.
  - Typical evidence: `systemd` shows `canteen-ordering.service ... status=203/EXEC` or restart script reports `Python venv not found: /opt/canteen-ordering/venv/bin/python`.
  - Root cause pattern: source app directory already had incomplete venv (for example only `venv/lib/pythonX/site-packages` without `venv/bin` and `pyvenv.cfg`), and file migration copied this drift as-is.
  - Action: rebuild source venv to standard layout (`python3 -m venv ...` + `pip install -r requirements.txt`), then resync/re-migrate and restart target service.
  - Prevention: add source-side precheck for required runtime files before creating SMS/rsync task.

## If Terraform Apply Fails

1. Read stderr from local-exec (`scripts/run_migration.sh`).
2. Confirm required env vars are not empty.
3. Check VPC quota in target region (common blocker for `vpc-migration` creation).
4. Re-check region names and image ID.
5. Check SMS migration-project quota; if `SMS.8115`, clean old migration projects first.
6. Re-run `terraform apply -auto-approve` after fixing input.
7. Keep previous failure output for comparison; do not delete diagnostics blindly.

## If Task Starts But Progress Is Unclear

1. Use `task_id` from `out/migration_result.json`.
2. Query SMS task detail through API or existing script helper path.
3. Check source connectivity and target ECS status in parallel.
4. Report both current task state and latest blocking signal.
5. If `progress` is null or greater than 100 while `state` is `RUNNING`, continue polling until terminal state.

## If Run Was Paused/Interrupted

1. Read `out/resume_checkpoint_latest.json` to confirm whether original target VM/disk context is still valid.
2. If checkpoint shows deleted targets or missing original volumes (`HTTP 404 itemNotFound`), do not reuse old target IDs.
3. Read `out/rebuild_diagnosis_latest.json`; if blocker is `SMS.0515`, restart source SMS-Agent first.
4. Recreate/restart tasks and write `out/resume_noagent_restart_summary_latest.json`.
5. Continue monitor loop and keep writing `out/task_poll_latest.json` and `out/monitor_checkpoint_latest.json`.

## Output Packaging Checklist

After each migration run, archive these files together:

1. `out/migration_result.json`
2. `out/precheck_source_checks.json`
3. `out/rsync_execution.json` (if fallback happened)
4. `out/precheck_task_cleanup.json`
5. `out/postcheck_network.json`
6. `out/task_poll_latest.json`
7. `out/target_console_output*.txt` when SSH/TCP-22 postcheck fails
8. `./references/runbook.md`
9. `./references/lessons-learned.md`

Store bundle under:

- `./bundles/<date>-<scenario>/`

## Related Reference

- For reusable problem/experience summaries, load [lessons-learned.md](lessons-learned.md).
- For packaged migration assets and manifest, load [reuse-bundle.md](reuse-bundle.md).
