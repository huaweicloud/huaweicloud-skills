---
name: huawei-cloud-sac-new-api
description: |
  Deploy NewAPI LLM Gateway on Huawei Cloud via Terraform.
  Use when deploying a unified LLM API gateway for multi-model management,
  load balancing, and key rotation.
  Trigger: deploy NewAPI, NewAPI gateway, LLM gateway, 部署NewAPI, NewAPI网关, LLM网关
---

# Huawei Cloud NewAPI LLM Gateway

## Overview

Deploy the "Building a NewAPI LLM Gateway" solution end-to-end
on Huawei Cloud. The platform provides a NewAPI-based LLM API gateway
for unified management and forwarding of multiple large model API requests,
supporting load balancing, key rotation, and usage statistics.

**Architecture:** ECS (Ubuntu 22.04) and VPC and Subnet and Security Group
(SSH port 22 and NewAPI Web port 3000) and EIP and EVS
(system disk). Cloud-init installs Docker and launches the
NewAPI gateway container.

**Tool chain:** Playwright CLI (solution info extraction) + Python 3.10+
(helper scripts) + Terraform 1.5+ (declarative deployment).
No KooCLI — all resource operations through Terraform.

## Prerequisites

- Python 3.10+, Playwright CLI, Terraform 1.5+ — see [CLI Installation Guide](references/cli-installation-guide.md)
- Huawei Cloud AK/SK via environment variables (`HW_ACCESS_KEY`, `HW_SECRET_KEY`); if not set, prompt user to manually edit `terraform.auto.tfvars.json` to fill in AK/SK — **⛔ never read or display this file in conversation context**
- IAM user with sufficient permissions — see [IAM Policies](references/iam-policies.md)

### Security

- 🚫 Never expose AK/SK in conversation or output
- 🚫 Never ask user to type AK/SK in chat
- 🚫 Never read or display `terraform.auto.tfvars.json` in conversation context (contains AK/SK)
- ✅ Prefer IAM users over primary account
- ✅ Modification ops (`apply`, `destroy`) require explicit user confirmation

## Core Commands

Placeholder values (see Parameters for per-OS resolution):

| Placeholder                  | Linux / macOS        | Windows PowerShell | Windows CMD       |
| ---------------------------- | -------------------- | ------------------ | ----------------- |
| `<python>`                   | `python3`            | `python`           | `python`          |
| `<script_dir>`               | `./scripts`          | `./scripts`        | `scripts`         |
| `<temp_dir>`                 | `/tmp`               | `$env:TEMP`        | `%TEMP%`          |
| `<region>`                   | `cn-north-4`         | `cn-north-4`       | `cn-north-4`      |
| `<workdir>`                  | `newapi-workdir`     | `newapi-workdir`   | `newapi-workdir`  |
| `<solution_detail_page_url>` | (see Notes below)    | (same)             | (same)            |
| `<tf_template_url>`          | (see Notes below)    | (same)             | (same)            |

> `<solution_detail_page_url>` =
> `https://www.huaweicloud.com/solution/implementations/building-a-newapi-llm-gateway.html`
>
> `<tf_template_url>` =
> `https://documentation-samples.obs.cn-north-4.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-moudle/building-a-newapi-llm-gateway/building-a-newapi-llm-gateway.tf.json`

```bash
# 1. Extract solution info
<python> <script_dir>/extract_sac_deploy_info.py \
  --url "<solution_detail_page_url>" \
  --out <temp_dir>/sac_selected.json

# 2. Download and normalize template
<python> <script_dir>/download_tf_template_file.py \
  --url "<tf_template_url>" \
  --out-dir <temp_dir>/<workdir>

<python> <script_dir>/normalize_tf_providers.py <temp_dir>/<workdir> \
  --region "<region>"

# 3. List variables for review
<python> <script_dir>/list_tf_variables.py <temp_dir>/<workdir>

# 4. Deploy
terraform -chdir=<temp_dir>/<workdir> init
terraform -chdir=<temp_dir>/<workdir> plan
# ⛔ STOP — Review the plan output above. Do NOT auto-apply.
# Confirm with the user (AskUserQuestion or equivalent) before proceeding.
# Only after explicit user confirmation:
terraform -chdir=<temp_dir>/<workdir> apply

# 5. Verify
terraform -chdir=<temp_dir>/<workdir> state list
terraform -chdir=<temp_dir>/<workdir> output -json

# 6. Cleanup
terraform -chdir=<temp_dir>/<workdir> destroy
python -c "import os; f='<temp_dir>/<workdir>/terraform.auto.tfvars.json'; os.path.exists(f) and os.remove(f)"
```

## Workflow

### 1. Extract solution info

After running the Core Commands step 1, **display the results to the user**:

- **Solution name**: `title` field from output JSON
- **Estimated price**: `estimated_price_text` field
- **Deploy links**: list each `text` and `url` from
  `deploy_links` array
- If `title` or `estimated_price_text` is empty, warn the user
  and suggest manual verification on the solution page

### 2. Download and normalize template

`normalize_tf_providers.py` writes `terraform.auto.tfvars.json` (including region
and other parameters). If environment variables `HW_ACCESS_KEY`/`HW_SECRET_KEY`
are not set, AK/SK fields are left empty. **Tell the user the file path and
prompt them to manually edit it to fill in AK/SK. ⛔ Never read or display
the file contents in conversation context.** Then continue to the next step.

### 3. Confirm variables

Review with user. Block `apply` if sensitive variables are empty/weak.

### 4. Deploy

⛔ **STOP** — Before running `terraform apply`, review the `terraform plan`
output and confirm with the user (AskUserQuestion or equivalent).
Do NOT auto-apply. Only proceed after explicit user confirmation.

### 5. Verify

See [Verification Method](references/verification-method.md) and [Acceptance Criteria](references/acceptance-criteria.md).

### 6. Cleanup

## Parameters

| Parameter | Required | Default | Constraint |
| ---------- | -------- | ------- | ---------- |
| `region` | Yes | `cn-north-4` | Only supported region |
| AK/SK | Yes | — | Env vars `HW_ACCESS_KEY`/`HW_SECRET_KEY`; if absent, prompt user to edit tfvars.json (⛔ never read tfvars.json in context) |
| `ecs_password` | Yes | — | 8-26 chars, mixed case + digit + special |
| `ecs_flavor` | No | `x1.8u.16g` | ECS flavor ID |
| `system_disk_size` | No | 100 | 40-1024 GB |
| `bandwidth_size` | No | 300 | EIP bandwidth in Mbit/s |
| `charging_unit` | No | `month` | `month` or `year` |
| `charging_period` | No | 1 | — |

## Post-Deploy Output

- `terraform output -json` — includes `access_instructions` with NewAPI gateway URL
- NewAPI Web UI: `http://<EIP>:3000` (allow ~10 min for cloud-init)
- Verify: `ssh root@<EIP> "docker ps"` shows NewAPI container running

## Output Format

`terraform output -json` returns JSON with the following key fields:

```json
{
  "access_instructions": { "value": "http://<EIP>:3000" },
  "ecs_eip":             { "value": "<Elastic IP>" },
  "ecs_id":              { "value": "<ECS Instance ID>" },
  "vpc_id":              { "value": "<VPC ID>" }
}
```

All script outputs are in JSON format: `extract_sac_deploy_info.py` outputs
solution info JSON, `list_tf_variables.py` outputs variable list JSON.

## Verification

Verify deployment results step by step:

1. **Template extraction** — Check `<temp_dir>/sac_selected.json` contains
   `solution_name`, `price` fields
2. **Template download** — Confirm `.tf` files exist under `<temp_dir>/newapi-workdir`
   and `terraform validate` passes
3. **Variable confirmation** — Sensitive variables (AK/SK, password) are not
   empty in `list_tf_variables.py` output; user confirmed overrides
4. **Deployment** — `terraform plan` shows no errors; user confirmed deployment; after `apply`,
   `terraform state list` shows all expected resources
5. **Service reachability** — Wait 10-15 min for cloud-init, then
   `curl -s http://<EIP>:3000` returns 200
6. **Container** — `ssh root@<EIP> "docker ps"` shows NewAPI container running

See [Verification Method](references/verification-method.md) and
[Acceptance Criteria](references/acceptance-criteria.md) for details.

## Best Practices

- Always `terraform plan` before `apply`
- Start with `charging_unit=month`; switch to `year` after validation
- Allow 10-15 min post-deploy for cloud-init
- Monitor NewAPI dashboard for API usage and key rotation status

## Reference Documents

| Document | Description |
| -------- | ----------- |
| [CLI Installation Guide](references/cli-installation-guide.md) | Install Python, Playwright CLI, Terraform |
| [IAM Policies](references/iam-policies.md) | Permissions, agency setup, failure handling |
| [Verification Method](references/verification-method.md) | Step-by-step verification per workflow step |
| [Acceptance Criteria](references/acceptance-criteria.md) | Full deployment acceptance checklist |
| [Related Commands](references/related-commands.md) | Terraform, scripts, remote access reference |

## Notes

- Only `cn-north-4` region supported
- `terraform.auto.tfvars.json` is sensitive — never commit to VCS; never read or display in conversation context
- `normalize_tf_providers.py` writes region to tfvars; AK/SK left empty if env vars not set, user must fill manually
- Tool chain: Playwright CLI + Python + Terraform — no KooCLI
