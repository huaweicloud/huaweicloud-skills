# Acceptance Criteria - MGC Cross-Region Migration

Use these pass/fail criteria to judge whether a migration run produced by this skill is acceptable.

## CLI/Command Format

- ✅ `terraform init` and `terraform apply -auto-approve` are run from the repository root, in that order.
- ✅ `terraform apply -replace=terraform_data.mgc_region_migration -auto-approve` is used only when a normal apply reports `No changes` but a rerun is actually required.
- ❌ Running `python scripts/mgc_migrate.py` directly with hand-typed environment variables instead of letting Terraform map `terraform.tfvars`, which risks drift between declared inputs and actual run.

## Parameter Validation

- ✅ `access_key`, `secret_key`, `source_server_id`, `target_image_id` are all set and non-empty before `terraform apply`.
- ✅ Defaults (`source_region=la-north-2`, `target_region=la-south-2`, `target_vpc_name=vpc-migration`, `sms_endpoint=https://sms.ap-southeast-3.myhuaweicloud.com`) are used unless the user explicitly overrides them.
- ❌ Applying with a `target_image_id` that has not been confirmed to exist in `target_region`.

## Output Format Validation

- ✅ `out/migration_result.json` contains non-empty `migproject_id`, `task_id`, `source_sms_server_id`, `target_server_id`, `task_state`.
- ✅ When the rsync fallback path runs, `out/rsync_execution.json` is also present and reports a phase (`full_sync`/`incremental_sync`/`cutover_sync`).
- ❌ Treating a pre-existing `out/migration_result.json` as evidence of the current run's success without confirming its timestamp is from this run.

## Error Handling Validation

- ✅ Each error code in [SKILL.md § Best Practices](../SKILL.md#best-practices) (`SMS.6504`, `SMS.6602`, `SMS.6603`, `SMS.6617`, `SMS.7605`, `SMS.7703`, `SMS.8115`, `VPC.0114`) is matched to its documented action before any ad hoc manual fix is attempted.
- ✅ SSH/TCP-22 failures after a `MIGRATE_SUCCESS`/rsync-complete state are treated as a separate acceptance gate, not assumed to be resolved by the migration task's own success status.

## Security Validation

- ✅ `access_key`/`secret_key` never appear in command output, logs, or chat transcripts (`grep -rniE "access_key|secret_key" out/` should only match key *names* in JSON structure, never real key values from the account).
- ✅ Destructive/overwrite operations (starting an SMS task that overwrites target ECS data) are confirmed with the user before `terraform apply`.
- ❌ Hardcoding `access_key`/`secret_key` anywhere other than the user's local `terraform.tfvars`.
