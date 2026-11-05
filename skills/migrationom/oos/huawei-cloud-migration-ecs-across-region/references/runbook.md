# Migration Runbook

## Quick Checklist

1. Confirm source server is visible in SMS source list and status is connected.
2. Confirm destination image ID exists in target region.
3. Confirm AK/SK permissions for IAM, ECS, VPC, SMS.
4. Confirm target-region VPC quota has free slot if target VPC may be auto-created.
5. Check and clean obsolete source-bound SMS tasks before starting a new migration.
6. Confirm rsync SSH parameters are present in `terraform.tfvars` for fallback (`rsync_source_host/port/user/password`). For the target leg, have operations pre-place a private key on the source host and set `target_rsync_ssh_key` (`TARGET_RSYNC_SSH_KEY`); its public half must already be trusted on the target. The same key model applies to the AWS standalone path (`scripts/run_aws_migration.sh`): it reads `target_rsync_ssh_key` from `terraform.tfvars`, runs `rsync` on the AWS source host, and pushes to the target over `ssh -i` (never remote-to-remote).
7. When source can only reach Codex VPN, prefer bridge mode (`enable_vpn_bridge=true`). Keep target VPN client bootstrap (`enable_target_vpn_client`) only as an optional fallback mode.
8. Confirm target ECS overwrite risk is accepted.
9. Run Terraform and verify `out/migration_result.json`.
10. For rsync runs, validate target boot/SSH health after sync; if SSH fails, inspect ECS console output before changing network policies.
11. For SMS runs, still validate SSH/TCP-22 and target console output; SMS `MIGRATE_SUCCESS` does not guarantee login readiness.

## Canonical Commands

> **Note**: This skill has been optimized for Windows environment. Use the PowerShell commands below.

```powershell
# Navigate to the repository root (replace with your actual checkout path)
cd <repo-root>

# Initialize Terraform
terraform init

# Apply migration
terraform apply -auto-approve

# If apply returns "No changes", force rerun with:
terraform apply -replace=terraform_data.mgc_region_migration -auto-approve

# View migration result (PowerShell)
Get-Content out\migration_result.json

# Or in git-bash, you can still use cat:
# cat out/migration_result.json
```

Use `-replace=terraform_data.mgc_region_migration` only when a rerun is required but normal apply reports `No changes`.

## tfvars -> Runtime Env Mapping

`main.tf` passes these variables to `scripts/mgc_migrate.py`:

- `access_key` -> `HC_AK`
- `secret_key` -> `HC_SK`
- `source_server_id` -> `SOURCE_SERVER_ID`
- `source_region` -> `SOURCE_REGION`
- `target_region` -> `TARGET_REGION`
- `target_region_name` -> `TARGET_REGION_NAME`
- `target_vpc_name` -> `TARGET_VPC_NAME`
- `target_image_id` -> `TARGET_IMAGE_ID`
- `target_server_name` -> `TARGET_SERVER_NAME`
- `eip_bandwidth_mbps` -> `EIP_BANDWIDTH_MBPS`
- `root_volume_type` -> `ROOT_VOLUME_TYPE`
- `data_volume_type` -> `DATA_VOLUME_TYPE`
- `sms_endpoint` -> `SMS_ENDPOINT`
- `preferred_migration_method` -> `PREFERRED_MIGRATION_METHOD`
- `enable_rsync_fallback` -> `ENABLE_RSYNC_FALLBACK`
- `source_private_ip` -> `SOURCE_PRIVATE_IP`
- `extra_peer_ips` -> `EXTRA_PEER_IPS`
- `rsync_source_host` -> `RSYNC_SOURCE_HOST`
- `rsync_source_port` -> `RSYNC_SOURCE_PORT`
- `rsync_source_user` -> `RSYNC_SOURCE_USER`
- `rsync_source_password` -> `RSYNC_SOURCE_PASSWORD`
- `rsync_target_host` -> `RSYNC_TARGET_HOST`
- `rsync_target_port` -> `RSYNC_TARGET_PORT`
- `rsync_target_user` -> `RSYNC_TARGET_USER`
- `target_rsync_ssh_key` -> `TARGET_RSYNC_SSH_KEY` (path on the source host to an operator-provisioned private key already trusted by the target)
- `rsync_source_paths` -> `RSYNC_SOURCE_PATHS`
- `rsync_staging_dir` -> `RSYNC_STAGING_DIR`
- `rsync_incremental_rounds` -> `RSYNC_INCREMENTAL_ROUNDS`
- `rsync_timeout_sec` -> `RSYNC_TIMEOUT_SEC`
- `rsync_excludes` -> `RSYNC_EXCLUDES`
- `rsync_cutover_stop_cmd` -> `RSYNC_CUTOVER_STOP_CMD`
- `rsync_cutover_start_cmd` -> `RSYNC_CUTOVER_START_CMD`
- `rsync_target_finalize_cmd` -> `RSYNC_TARGET_FINALIZE_CMD`
- fixed output path -> `RESULT_PATH=out/migration_result.json`

## What Success Looks Like

`out/migration_result.json` includes non-empty values for:

- `source_project_id`
- `target_project_id`
- `source_sms_server_id`
- `target_server_id`
- `migproject_id`
- `task_id`
- `task_state`
- `migration_method`

## Error Handling Matrix

- `SMS.6504`
  - Meaning: source OS precheck incompatible with SMS.
  - Action: script switches to rsync fallback (`full_sync -> incremental_sync -> cutover_sync`).

- `SMS.6603`
  - Meaning: source server is not connected to SMS.
  - Action: install/start SMS-Agent on source server, then rerun.

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

- `VPC.0114`
  - Meaning: target-region VPC/router quota exceeded when creating target VPC.
  - Action: release one unused VPC or increase quota, then rerun `terraform apply -auto-approve`.

- `SMS.7703`
  - Meaning: queried `task_id` does not exist (often from stale historical output file).
  - Action: do not use old `task_id`; get latest task from current run output or list tasks by source server and pick the active one.

- `rsync target SSH key missing or denied`
  - Meaning: the rsync fallback could not authenticate to the target with the operator-provided key.
  - Action: have operations place the private key on the source host and set `TARGET_RSYNC_SSH_KEY`, and trust its public half on the target (or pre-establish source-to-target passwordless SSH). Alternatively use the MGC/SMS console migration path.
  - Prevention: do not rely on the migration script to create keys or modify target SSH configuration; the rsync target-auth path never writes `authorized_keys`, changes `sshd_config`, or restarts `sshd`.

- `SSH reset/closed/timed out after rsync`
  - Meaning: target ECS may not have reached normal boot state even when cloud status is `ACTIVE`.
  - Action: fetch ECS console output and check for emergency mode/systemd dependency failures (commonly stale `/etc/fstab` UUID entries), repair `/etc/fstab` via VNC/serial shell, reboot, then re-test SSH.
  - Prevention: keep `/etc/fstab` in rsync exclude list unless explicit disk-mount migration remap is prepared.

- `SSH closed_or_timeout after SMS success`
  - Meaning: SMS task can be terminal-success while target SSH is not reachable.
  - Action: check `out/postcheck_network.json` for EIP/SG/peer evidence, then inspect `out/target_console_output*.txt`.
  - If console output contains cloud-init `Failed loading yaml blob` or another YAML parse error, treat target user-data bootstrap as invalid: recreate the target and retest. user-data carries only SSH-config-independent bootstrap (network reachability and the optional VPN client).
  - Never repair target SSH access by editing `sshd_config`, enabling password/root login, or restarting `sshd`; rely on the operator-provisioned key model and fix network reachability instead.
  - Prevention: validate generated cloud-init YAML before target ECS creation, and archive console output whenever TCP/22 postcheck fails.

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
5. If `progress` is null but `state` is `RUNNING`, continue polling until terminal state.

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