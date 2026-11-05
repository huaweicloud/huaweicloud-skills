# Migration Skill Summary

## Scope

- Skill path: `skills/huawei-cloud-mgc-migration-ecs-gcp-to-hw`
- Objective: migrate workloads to Huawei Cloud with Terraform + repository migration scripts.
- Current Terraform entrypoint: `scripts/mgc_sms_existing_target_batch.py` (batch existing-target SMS flow).
- Secondary path: `scripts/mgc_migrate.py` (single-source SMS/rsync flow).
- Proven path 1: SMS migration when source precheck is clean.
- Proven path 2: automatic rsync fallback over VPN bridge when SMS source precheck returns `SMS.6504`.
- Always separate migration-task success from operational acceptance: validate target ECS status, EIP, SG peer rules, SSH/TCP-22, and console output.

## Canonical Process

1. Validate source registration/permissions/target image/quota.
2. Populate `terraform.tfvars` with migration, network, and optional VPN/rsync parameters.
3. Run `terraform init` then `terraform apply -auto-approve`.
4. If apply reports `No changes`, force rerun with:
   - `terraform apply -replace=terraform_data.sms_existing_target_batch -auto-approve`
5. Confirm run output from:
   - `out/migration_result.json`
   - `out/precheck_source_checks.json`
   - `out/precheck_task_cleanup.json`
   - `out/task_poll_latest.json`
   - `out/rsync_execution.json` when fallback is used
6. Validate postcheck:
   - VPC name is `vpc-migration`
   - target ECS is `ACTIVE`
   - EIP exists with expected bandwidth
   - security-group connectivity rules are present for expected peers
   - SSH/TCP-22 is reachable, or console output explains why it is not

## Proven Automation Behaviors

- Auto creates/reuses target VPC/subnet and target ECS (single-source flow).
- Supports batch mapping from source ECS IDs to existing destination ECS by fixed IP (existing-target batch flow).
- Auto binds a dedicated EIP, normally `100 Mbps`.
- Auto adds source/target SG reachability rules for source and configured extra peers.
- Auto switches from SMS to rsync when source precheck returns `SMS.6504`.
- Retries CreateTask without strict disks mapping on `SMS.1404` in single-source flow.
- Supports VPN bridge routing through OpenVPN + VPC peering for rsync fallback.
- Treats rsync return code `23/24` as non-fatal partial/vanished-file warnings.
- Polls task `state`; do not require non-null `progress` or `end_date` to recognize terminal success.

## Operational Rules Distilled

- Clean old source-bound SMS tasks before creating a new migration task.
- Clean old auto-generated migration projects when `SMS.8115` reports the 50-project quota.
- Use `-replace` with the actual `terraform_data` resource for deliberate reruns with unchanged inputs.
- In this repo's current batch flow, use `-replace=terraform_data.sms_existing_target_batch`.
- Treat `progress=null` and `end_date=null` as acceptable if task `state` is terminal success.
- Treat `SMS.1404` as a target-disk baseline issue first, not only as transient API failure.
- When diagnosis reports `SMS.0515`, restart source SMS-Agent and refresh source metadata before recreating tasks.
- When a paused run is resumed, verify checkpoint baseline (`target exists`, `orig disk exists`) before reusing historical task IDs.
- Keep `/etc/fstab` excluded from rsync fallback unless a disk-mount remap is explicitly prepared.
- Validate generated cloud-init YAML before target creation; bad user-data can leave SSH unreachable even after SMS success.
- If SMS is `MIGRATE_SUCCESS` but SSH still fails and console shows `root=/dev/vdb1`/kernel panic, repair grub/root device mapping (`/dev/vda` or correct root UUID) via helper attach workflow before changing SG/VPC rules.
- For external-source migrations with multiple disks, normalize device naming between source (`/dev/sd*`, `/dev/nvme*n*`) and target (`/dev/vd*`) before building disk mapping.
- Before SMS-Agent registration, validate AK/SK by calling IAM list-projects API. A 401 means the credential is invalid globally.
- Before re-registering SMS-Agent, kill stale `linuxmain` processes and re-extract a fresh agent package; do not reuse a partially-deleted agent directory.
- For GCP sources with `LABEL=` fstab entries, expect GRUB root-device repair after SMS migration.

## Evidence Files

- `out/migration_result.json`
- `out/precheck_source_checks.json`
- `out/precheck_task_cleanup.json`
- `out/task_poll_latest.json`
- `out/task_poll_retry_latest.json` (when failed round exists)
- `out/resume_checkpoint_latest.json` (when resumed after interruption)
- `out/resume_noagent_restart_summary_latest.json` (when recreated targets/tasks)
- `out/monitor_checkpoint_latest.json`
- `out/rebuild_diagnosis_latest.json`
- `out/postcheck_network.json`
- `out/rsync_execution.json` when fallback is used
- `out/target_console_output*.txt` when SSH/TCP-22 postcheck fails
- `out/target_boot_diagnosis_latest.json` when task is successful but boot behavior is suspect
- `out/target_access_recovery_latest.json` after password reset/reboot recovery
- `out/target_boot_repair_latest.json`
- `out/target_root_param_fix_latest.json`
- `out/target_grubcfg_fix_latest.json`
- `out/target_rootdev_fix_latest.json`
- `out/target_sshpass_fix_latest.json`
