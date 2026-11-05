# Migration Skill Summary

## Scope

- Skill path: `skills/huawei-cloud-migration-ecs-across-region`
- Objective: migrate workloads to Huawei Cloud with Terraform + `scripts/mgc_migrate.py`.
- Proven path 1: SMS migration when source precheck is clean.
- Proven path 2: automatic rsync fallback over VPN bridge when SMS source precheck returns `SMS.6504`.
- Always separate migration-task success from operational acceptance: validate target ECS status, EIP, SG peer rules, SSH/TCP-22, and console output.

## Canonical Process

1. Validate source registration/permissions/target image/quota.
2. Populate `terraform.tfvars` with migration, network, and optional VPN/rsync parameters.
3. Run `terraform init` then `terraform apply -auto-approve`.
4. If apply reports `No changes`, force rerun with:
   - `terraform apply -replace=terraform_data.mgc_region_migration -auto-approve`
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

- Auto creates/reuses target VPC/subnet and target ECS.
- Auto binds a dedicated EIP, normally `100 Mbps`.
- Auto adds source/target SG reachability rules for source and configured extra peers.
- Auto switches from SMS to rsync when source precheck returns `SMS.6504`.
- Supports VPN bridge routing through OpenVPN + VPC peering for rsync fallback.
- Treats rsync return code `23/24` as non-fatal partial/vanished-file warnings.
- Polls task `state`; do not require non-null `progress` or `end_date` to recognize terminal success.

## Operational Rules Distilled

- Clean old source-bound SMS tasks before creating a new migration task.
- Clean old auto-generated migration projects when `SMS.8115` reports the 50-project quota.
- Use `-replace=terraform_data.mgc_region_migration` for deliberate reruns with unchanged inputs.
- Treat `progress=null` and `end_date=null` as acceptable if task `state` is terminal success.
- Keep `/etc/fstab` excluded from rsync fallback unless a disk-mount remap is explicitly prepared.
- Validate generated cloud-init YAML before target creation; bad user-data can leave SSH unreachable even after SMS success.

## Evidence Files

- `out/migration_result.json`
- `out/precheck_source_checks.json`
- `out/precheck_task_cleanup.json`
- `out/task_poll_latest.json`
- `out/postcheck_network.json`
- `out/rsync_execution.json` when fallback is used
- `out/target_console_output*.txt` when SSH/TCP-22 postcheck fails
