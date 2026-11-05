# Reuse Bundle for Similar Migration Scenarios

## Purpose

Package migration method, process, commands, and output artifacts in one place so future cross-region migrations can reuse a proven path with minimal rework.

## Recommended Execution Sequence

1. Precheck input and source registration in SMS.
2. Pre-migration cleanup: remove obsolete source-bound SMS tasks.
3. Run Terraform migration workflow.
4. If Terraform shows `No changes`, rerun with resource replace.
5. Postcheck target VPC/EIP/security groups.
6. Poll task state until terminal status (`*_SUCCESS` or `*_FAIL`).
7. If SSH/TCP-22 fails, fetch and keep ECS console output before changing more network policy.
8. Archive all run artifacts into `skills/.../bundles/`.

## Canonical Commands

> **Note**: This skill has been optimized for Windows environment. Use PowerShell commands below.

```powershell
# Navigate to the repository root (replace with your actual checkout path)
cd <repo-root>

# Initialize and apply Terraform
terraform init
terraform apply -auto-approve

# If apply returns "No changes", force rerun with:
terraform apply -replace=terraform_data.mgc_region_migration -auto-approve

# View migration result (PowerShell)
Get-Content out\migration_result.json
Get-Content out\precheck_task_cleanup.json
Get-Content out\postcheck_network.json
Get-Content out\task_poll_latest.json

# List console output files (PowerShell)
Get-ChildItem out\target_console_output*.txt -ErrorAction SilentlyContinue
```

## Artifact Manifest

Keep these files after every run:

- `out/migration_result.json`: core migration IDs and network result.
- `out/precheck_task_cleanup.json`: historical task cleanup evidence.
- `out/postcheck_network.json`: target VPC/EIP/SG connectivity verification.
- `out/task_poll_latest.json`: terminal task state timeline.
- `out/target_console_output*.txt`: boot/cloud-init evidence when SSH/TCP-22 postcheck fails.

Optional supporting files:

- `main.tf`
- `variables.tf`
- `scripts/mgc_migrate.py`
- `./SKILL.md`
- `./references/runbook.md`
- `./references/lessons-learned.md`

## Packaging Rule

Store each completed migration under:

- `./bundles/<date>-<source>-to-<target>/`

Each bundle should include:

1. A `README.md` with source/target region, source VM ID, task ID, final state, and key timestamps.
2. The 4 core `out/*.json` artifacts.
3. Any extra evidence needed for postmortem, especially console output for SSH failures (only non-secret information).

## One-Command Bundle Generation

Use the bundled script (PowerShell):

```powershell
# Navigate to the repository root (replace with your actual checkout path)
cd <repo-root>

# Run bundle generation script
.\tools\build_bundle_from_latest_out.ps1 <bundle-name>
```

Example:

```powershell
# Generate bundle for migration from mx2 to santiago
.\tools\build_bundle_from_latest_out.ps1 "2026-04-22-mx2-to-santiago"
```

The script will:
1. Create a bundle directory under `./bundles/`
2. Copy all required JSON artifacts from `out/`
3. Copy reference files (SKILL.md, runbook.md, etc.)
4. Generate a README.md with timestamp
5. Create a `.zip` archive of the bundle