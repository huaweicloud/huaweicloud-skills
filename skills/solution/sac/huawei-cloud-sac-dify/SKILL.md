---
name: huawei-cloud-sac-dify
description: |
  "Deploy Dify - an open-source LLM app development platform on Huawei Cloud with ECS via Terraform. Use when the user wants to deploy Dify (or an LLM application development platform) on Huawei Cloud and directly implement it with a Terraform/SAC template.
  Trigger: Dify 一键部署, Dify development, Agentic workflow, build AI App"
---

# Huawei Cloud Dify LLM App development Platform

## Overview

Deploy the "Building a Dify LLM Application Development Platform" SAC solution on Huawei Cloud end-to-end using Terraform.

**Architecture:** VPC + Subnet + Security Group (ICMP/HTTP/HTTPS ingress), one ECS instance, and one EIP (1-300 Mbit/s). Cloud-init installs and starts Dify services on Ubuntu. The template supports both Dify community versions and `flexus-ai-agent` mode (controlled by `dify_version`).

**Tool chain:** Playwright CLI (price/solution metadata extraction) + Python 3.8+ (helper scripts) + Terraform (infrastructure provisioning). No KooCLI; deployment and lifecycle operations are handled through Terraform only.

## Prerequisites

- Python 3.8+, Playwright CLI, Terraform 1.15.4+ — see [CLI Installation Guide](references/cli-installation-guide.md)
- Huawei Cloud AK/SK via environment variables (`HW_ACCESS_KEY`, `HW_SECRET_KEY`); if not set, prompt user to manually edit `<temp_dir>/dify-workdir/terraform.auto.tfvars.json` to fill in AK/SK
- IAM user with sufficient permissions or `rf_admin_trust` agency — see [IAM Policies](references/iam-policies.md)

### Security

- 🚫 Never expose AK/SK in conversation or output
- 🚫 Never ask user to type AK/SK in chat
- ✅ Prefer IAM users over primary account
- ✅ Modification ops (`apply`, `destroy`) require explicit user confirmation

## Core Commands

Placeholder values (see Parameters for per-OS resolution):

| Placeholder | Linux / macOS | Windows |
|-------------|---------------|---------|
| `<python>` | `python3` | `python` |
| `<script_dir>` | `./scripts` | `./scripts` |
| `<temp_dir>` | `/tmp` | `$env:TEMP` |

```bash
# 1. Extract solution info
<python> <script_dir>/extract_sac_deploy_info.py \
  --url "https://www.huaweicloud.com/solution/implementations/building-a-dify-llm-application-development-platform.html" \
  --out <temp_dir>/sac_selected.json

# 2. Download and normalize template
mkdir -p <temp_dir>/dify-workdir
curl -fsSL "https://documentation-samples.obs.cn-north-4.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-moudle/flexus/dify-ecs.tf" \
  -o <temp_dir>/dify-workdir/dify-ecs.tf

<python> <script_dir>/normalize_tf_providers.py <temp_dir>/dify-workdir \
  --region "cn-north-4"

# 3. List variables for review
<python> <script_dir>/list_tf_variables.py <temp_dir>/dify-workdir

# 4. Deploy
terraform init
terraform plan
# ⛔ STOP — Review the plan output above. Do NOT auto-apply.
# Confirm with the user (AskUserQuestion or equivalent) before proceeding.
# Only after explicit user confirmation:
terraform apply

# 5. Verify
terraform state list
terraform output -json

# 6. Cleanup
terraform destroy
# Only after terraform destroy succeeds:
# Linux / macOS
rm -f <temp_dir>/dify-workdir/terraform.auto.tfvars.json
# Windows PowerShell
Remove-Item -Force <temp_dir>/dify-workdir/terraform.auto.tfvars.json
```

## Workflow

### 1. Extract solution info

```bash
<python> <script_dir>/extract_sac_deploy_info.py \
  --url "<solution_detail_page_url>" \
  --out <temp_dir>/sac_selected.json
```

After extraction, **display the results to the user**:

- **Solution name**: `title` field from output JSON
- **Estimated price**: `estimated_price_text` field
- If `title` or `estimated_price_text` is empty, warn the user and suggest manual verification on the solution page

### 2. Download and normalize template

```bash
mkdir -p <temp_dir>/dify-workdir
curl -fsSL "https://documentation-samples.obs.cn-north-4.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-moudle/flexus/dify-ecs.tf" \
  -o <temp_dir>/dify-workdir/dify-ecs.tf

<python> <script_dir>/normalize_tf_providers.py <temp_dir>/dify-workdir \
  --region "cn-north-4"
```

Prefer downloading the template from the explicit Dify Terraform URL above. Use the extracted template candidate only as a fallback if that URL is unavailable.

`normalize_tf_providers.py` writes `<temp_dir>/dify-workdir/terraform.auto.tfvars.json` (including region and other parameters).
If environment variables `HW_ACCESS_KEY`/`HW_SECRET_KEY` are not set, AK/SK fields are left empty.
**Prompt the user to manually edit the file to fill in AK/SK**, then continue to the next step.

### 3. Confirm variables

```bash
<python> <script_dir>/list_tf_variables.py <temp_dir>/dify-workdir
```

Review with user. Block `apply` if sensitive variables are empty/weak.
Partially mask sensitive values such as passwords to avoid leaking them into the LLM context.

### 4. Deploy

⛔ **STOP** — Before running `terraform apply`, review the `terraform plan` output and confirm with the user (AskUserQuestion or equivalent).
Do NOT auto-apply. Only proceed after explicit user confirmation.

### 5. Verify

See [Verification Method](references/verification-method.md) and [Acceptance Criteria](references/acceptance-criteria.md).

### 6. Cleanup

Run `terraform destroy` to remove managed resources.
Delete `<temp_dir>/dify-workdir/terraform.auto.tfvars.json` only after `terraform destroy` succeeds, so failed destroy attempts can still reuse the existing credentials file for retry.

Linux / macOS:

```bash
rm -f <temp_dir>/dify-workdir/terraform.auto.tfvars.json
```

Windows PowerShell:

```powershell
Remove-Item -Force <temp_dir>/dify-workdir/terraform.auto.tfvars.json
```

## Parameters

| Parameter | Required | Default | Constraint |
| ---------- | -------- | ------- | ---------- |
| `access_key` | Yes | `<NO_DEFAULT>` | From env `HW_ACCESS_KEY` or local `<temp_dir>/dify-workdir/terraform.auto.tfvars.json`; never print in chat |
| `secret_key` | Yes | `<NO_DEFAULT>` | From env `HW_SECRET_KEY` or local `<temp_dir>/dify-workdir/terraform.auto.tfvars.json`; never print in chat |
| `solution_name` | No | `dify-ecs-demo` | 4-24 chars, lowercase letter/digit/hyphen, must start with lowercase letter |
| `region_id` | Yes | `cn-north-4` | Primary region parameter. Allowed: `cn-north-4`,`cn-southwest-2`,`cn-north-12`,`ap-southeast-3`,`cn-east-3`,`cn-north-9`,`cn-south-2`,`cn-south-1`,`tr-west-1`,`cn-south-4`,`ap-southeast-1`,`cn-north-2`,`cn-north-1`,`cn-east-4`. Keep `normalize_tf_providers.py --region` consistent with this value |
| `dify_version` | No | `1.11.4` | Allowed: `1.11.4`,`1.8.1`,`1.6.0`,`1.4.1`,`1.1.3`,`0.15.8`,`flexus-ai-agent` |
| `ecs_flavor` | No | `t6.xlarge.2` | ECS/Flexus flavor format must match template regex validation |
| `ecs_password` | Yes | `""` | 8-26 chars, includes at least 3 of uppercase/lowercase/digit/special |
| `dify_admin_password` | Conditional | `""` | Effective when `dify_version=flexus-ai-agent`; 8-26 chars and includes letters and digits |
| `system_disk_size` | No | `100` | 40-1024 (GB) |
| `bandwidth_size` | No | `300` | 1-300 (Mbit/s) |
| `charging_mode` | No | `postPaid` | `postPaid` or `prePaid` |
| `charging_unit` | Conditional | `month` | Required when `charging_mode=prePaid`; `month` or `year` |
| `charging_period` | Conditional | `1` | Required when `charging_mode=prePaid`; month: 1-9, year: 1-3 |

## Post-Deploy Output

- `terraform output -json` — includes `access_instructions` with Dify platform URL
- Dify UI: `http://<EIP>` (allow ~10 min for cloud-init)

## Output Format

All script outputs are in JSON format: `extract_sac_deploy_info.py` outputs solution info JSON, `list_tf_variables.py` outputs variable list JSON.

## Verification

Verify deployment results step by step:

1. **Template extraction** — Check `<temp_dir>/sac_selected.json` contains `solution_name`, `price` fields
2. **Template download** — Confirm `.tf` files exist under `<temp_dir>/sac-workdir` and `terraform validate` passes
3. **Variable confirmation** — Sensitive variables (AK/SK, password) are not empty in `list_tf_variables.py` output
4. **Deployment** — `terraform plan` shows no errors; user confirmed deployment; after `apply`, `terraform state list` shows all expected resources
5. **Service reachability** — Wait 10-15 min for cloud-init, then`curl -s http://<EIP>` returns 200

See [Verification Method](references/verification-method.md) and [Acceptance Criteria](references/acceptance-criteria.md) for details.

## Best Practices

- Always `terraform plan` before `apply`
- Start with `charging_unit=month`; switch to `year` after validation
- Allow 10-15 min post-deploy for cloud-init

## Reference Documents

| Document | Description |
| -------- | ----------- |
| [CLI Installation Guide](references/cli-installation-guide.md) | Install Python, Playwright CLI, Terraform |
| [IAM Policies](references/iam-policies.md) | Permissions, agency setup, failure handling |
| [Verification Method](references/verification-method.md) | Step-by-step verification per workflow step |
| [Acceptance Criteria](references/acceptance-criteria.md) | Full deployment acceptance checklist |
| [Related Commands](references/related-commands.md) | Terraform, scripts, remote access reference |

## Notes

- `<temp_dir>/dify-workdir/terraform.auto.tfvars.json` is sensitive — never commit to VCS
- Delete `<temp_dir>/dify-workdir/terraform.auto.tfvars.json` after a successful `terraform destroy` to avoid leaving credentials on disk
- `normalize_tf_providers.py` writes region to tfvars; AK/SK left empty if env vars not set, user must fill manually
- Tool chain: Playwright CLI + Python + Terraform — no KooCLI
