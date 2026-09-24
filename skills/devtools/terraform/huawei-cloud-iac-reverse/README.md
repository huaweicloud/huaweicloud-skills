# Huawei Cloud IaC Reverse Engineering Skill

Reverse-engineer existing Huawei Cloud resources into deployable Terraform IaC code.

## What It Does

1. **Discover** all resources via RMS (配置审计) API — single call gets everything
2. **Analyze** in batches by service layer (network → storage → compute → database → auxiliary)
3. **Synthesize** Terraform HCL configurations from the analyzed topology
4. **Validate** with `terraform fmt` → `validate` → `plan`
5. **Compare** generated code against original inventory to identify gaps

## Usage

```bash
# 1. Query all resources
./scripts/query_all_resources.sh sa-brazil-1

# 2. Generate Terraform code (manual, guided by SKILL.md workflow)

# 3. Validate
./scripts/validate_terraform.sh /path/to/terraform/project

# 4. Compare against original inventory
./scripts/compare_resources.sh /tmp/tf_plan.txt /tmp/rms_resources_sa-brazil-1.json
```

## Prerequisites

- `hcloud` CLI (KooCLI) configured with AK/SK
- Terraform >= 1.90.0
- Huawei Cloud provider (auto-downloaded via mirror)
- `HUAWEI_ACCESS_KEY` and `HUAWEI_SECRET_KEY` environment variables

## Key Design Decisions

- **Never `terraform apply` without user confirmation** — this skill only generates and validates
- **AK/SK never in `.tf` files** — use env vars or provider profile
- **Auto-created sub-resources excluded** — CCE nodes, DB nodes, EVS volumes managed by parents
- **Provider limitations documented** — properties not supported by TF provider are noted in comments

## Reference Documents

- `references/iam-policies.md` — Least-privilege IAM policies
- `references/cli-installation-guide.md` — KooCLI installation and credential configuration
- `references/verification-method.md` — Verification method details
- `references/acceptance-criteria.md` — Acceptance criteria
- `references/dataflow-diagram.md` — Data flow diagram