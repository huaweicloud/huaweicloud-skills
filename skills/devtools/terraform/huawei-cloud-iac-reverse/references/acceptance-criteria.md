# Acceptance Criteria

## Definition of Done

The skill is considered successful when the following criteria are met:

| # | Criteria | Verification |
|---|----------|--------------|
| 1 | All resources in the target region are discovered via RMS | `query_all_resources.sh` returns a non-empty `resources` array |
| 2 | Resources are analyzed in dependency order (network → storage → compute → database → auxiliary) | Phase 2 analysis table populated |
| 3 | Terraform HCL is generated for all top-level resources | One `.tf` per layer; sub-resources excluded |
| 4 | Generated code passes `terraform validate` | `validate_terraform.sh` exits 0 |
| 5 | `terraform plan` runs without provider schema errors | Plan output shows resources to create |
| 6 | Gap analysis compares generated code with the original inventory | `compare_resources.sh` outputs coverage ratio |
| 7 | No AK/SK hardcoded in `.tf`, scripts, or documentation | grep for credential patterns returns nothing |
| 8 | `terraform apply` is only run after explicit user confirmation | Workflow documents confirmation step |

## Edge Cases

| Scenario | Expected behavior |
|----------|-------------------|
| Region has zero resources | Skill reports "no resources found" and exits gracefully |
| RMS API not authorized | Clear error message pointing to `references/iam-policies.md` |
| Provider schema mismatch | Error documented in generated code comments; fix applied iteratively |
| Resource has properties unsupported by provider | Property recorded as a gap in the analysis report |
| Auto-created sub-resources (CCE/DB nodes) | Explicitly excluded and reported as "correctly excluded" |

## Release Gate

- All files pass `validate-skill.sh` with no FAIL items
- `references/iam-policies.md` exists and grants least-privilege read access
- SKILL.md <= 500 lines; total files <= 30; total size <= 40 MB