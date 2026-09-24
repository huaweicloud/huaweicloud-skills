# Verification Method

## Overview

This skill's output is validated through a four-step chain:

1. **Terraform formatting** — `terraform fmt -recursive`
2. **Terraform init** — `terraform init -upgrade` (downloads Huawei Cloud provider)
3. **Terraform validate** — `terraform validate` (syntax + provider schema check)
4. **Terraform plan** — `terraform plan -no-color` (dry-run, never applies)

## Steps

### 1. Query all resources (RMS)

```bash
bash scripts/query_all_resources.sh {region}
```

Verify:
- The output JSON file exists and contains a `resources` array
- The resource count matches the expected environment inventory
- The summary groups resources by `provider.type`

### 2. Generate Terraform code

Follow the `## Workflow` phases in SKILL.md:
- Layer ordering: network → storage → compute → CCE → database → cache/MQ → auxiliary
- Top-level resources only; auto-created sub-resources excluded

### 3. Validate the generated project

```bash
bash scripts/validate_terraform.sh {project_dir}
```

Verify:
- `terraform fmt` reports no diffs
- `terraform init` completes and the provider plugin downloads
- `terraform validate` returns "Success! The configuration is valid"
- `terraform plan` runs without schema errors

### 4. Compare against inventory

```bash
bash scripts/compare_resources.sh {plan_file} {rms_json_file}
```

Verify:
- Coverage ratio is reported
- Auto-created resources (CCE nodes, DB nodes, EVS volumes, HSS agents) are listed as correctly excluded
- Remaining gaps are documented and explained (provider limitations)

## Success Criteria

| Check | Pass condition |
|-------|----------------|
| `terraform fmt` | No output (already formatted) |
| `terraform init` | Provider download succeeds |
| `terraform validate` | Configuration is valid |
| `terraform plan` | No schema/argument errors |
| Coverage report | Coverage % computed, gaps documented |

## Notes

- `terraform apply` is **never** executed by this skill without explicit user confirmation.
- Credentials come from `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` environment variables.