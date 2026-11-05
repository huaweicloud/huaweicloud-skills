# Acceptance Criteria - MGC Cross-Region Migration

Use these pass/fail criteria to judge whether a migration run (or boot repair) produced by this skill is acceptable.

## CLI/Command Format

- ✅ `terraform init` and `terraform apply -auto-approve` are run from the repository root, in that order.
- ✅ `terraform apply -replace=terraform_data.sms_existing_target_batch -auto-approve` is used only when a normal apply reports `No changes` but a rerun is actually required.
- ✅ `scripts/repair_boot_via_helper.py` is invoked with an explicit `--target-server-id` and a strong `--target-reset-password`, never with a blank/weak password.
- ❌ Running the migration scripts directly with hand-typed environment variables instead of letting Terraform map `terraform.tfvars`, which risks drift between declared inputs and actual run.

## Parameter Validation

- ✅ `source_access_key`, `source_secret_key`, `destination_access_key`, `destination_secret_key`, and `source_server_ids` are all set and non-empty before `terraform apply`.
- ✅ Defaults (`source_region=ap-southeast-3`, `destination_region=ap-southeast-3`, `eip_bandwidth_mbps=100`, `sms_endpoint=https://sms.ap-southeast-3.myhuaweicloud.com`) are used unless the user explicitly overrides them.
- ❌ Applying with a `source_server_ids` batch that has not been confirmed to map to valid, reachable destination ECS instances.

## Output Format Validation

- ✅ `out/migration_result.json` contains a top-level `migration_project_id` and a `results[]` array with `source_sms_server_id`, `task_id`, `target_vm_id`, `task_state` per source.
- ✅ When a run is resumed, `out/resume_checkpoint_latest.json` and `out/resume_noagent_restart_summary_latest.json` are consulted before re-creating any target or task.
- ❌ Treating a pre-existing `out/migration_result.json` as evidence of the current run's success without confirming its timestamp is from this run.

## Error Handling Validation

- ✅ Each error code in [SKILL.md § Best Practices](../SKILL.md#best-practices) (`SMS.0515`, `SMS.1404`, `SMS.6504`, `SMS.6602`, `SMS.6603`, `SMS.6617`, `SMS.7605`, `SMS.7703`, `SMS.8115`, `VPC.0114`) is matched to its documented action before any ad hoc manual fix is attempted.
- ✅ SSH/TCP-22 failures and boot panics after a `MIGRATE_SUCCESS` state are treated as a separate acceptance gate, not assumed to be resolved by the migration task's own success status.
- ✅ `repair_boot_via_helper.py`'s temporary helper ECS is confirmed deleted after a successful repair (or manually cleaned up if `--keep-helper` was used or the run was interrupted).

## Security Validation

- ✅ Access-key/secret-key values never appear in command output, logs, or chat transcripts (`grep -rniE "access_key|secret_key" out/` should only match key *names* in JSON structure, never real key values from either account).
- ✅ Destructive/overwrite operations (starting an SMS task that overwrites target ECS data, resetting a target's password, deleting a helper ECS) are confirmed with the user before execution.
- ❌ Hardcoding any access-key/secret-key anywhere other than the user's local `terraform.tfvars`.
