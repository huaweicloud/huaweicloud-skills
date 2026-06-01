---
name: huawei-cloud-sac-yolo
description: |
  "Deploy YOLO training platform on Huawei Cloud with GPU ECS via Terraform. Use when building or managing a YOLO GPU training environment.
  Trigger: deploy YOLO, YOLO training, GPU training, 部署YOLO, YOLO训练, GPU训练, 视觉模型训练"
---

# Huawei Cloud YOLO Training Platform

## Overview

Deploy the "Quickly Build YOLO Visual Model Training Platform" solution end-to-end
on Huawei Cloud. The platform provides GPU-accelerated ECS for YOLO model training,
with full infrastructure provisioning via Terraform.

**Architecture:** ECS (GPU, P2s/Pi2) and VPC and Subnet and Security Group
(ICMP/SSH/HTTP) and EIP (300 Mbit/s) and EVS (100 GB system + 500 GB data)
and CBR (backup vault + policy). Cloud-init installs Docker and launches the
YOLO container on GPU.

**Tool chain:** Playwright CLI (solution info extraction) + Python 3.8+
(helper scripts) + Terraform 1.15.4+ (declarative deployment).
No KooCLI — all resource operations through Terraform.

## Prerequisites

- Python 3.8+, Playwright CLI, Terraform 1.15.4+ — see [CLI Installation Guide](references/cli-installation-guide.md)
- Huawei Cloud AK/SK via environment variables (`HW_ACCESS_KEY`, `HW_SECRET_KEY`); if not set, prompt user to manually edit `terraform.auto.tfvars.json` to fill in AK/SK
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
  --url "https://www.huaweicloud.com/solution/implementations/quickly-build-a-yolo-training-platform.html" \
  --out <temp_dir>/sac_selected.json

# 2. Download and normalize template
<python> <script_dir>/download_tf_template_file.py \
  --url "https://documentation-samples.obs.cn-north-4.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-moudle/quickly-build-a-yolo-training-platform/quickly-build-a-yolo-training-platform.tf" \
  --out-dir <temp_dir>/yolo-workdir

<python> <script_dir>/normalize_tf_providers.py <temp_dir>/yolo-workdir \
  --region "cn-north-4"

# 3. List variables for review
<python> <script_dir>/list_tf_variables.py <temp_dir>/yolo-workdir

# 4. Deploy
terraform init
terraform plan
# ⛔ STOP — Review the plan output above. Do NOT auto-apply.
# Confirm with the user (AskUserQuestion or equivalent) before proceeding.
# Only after explicit user confirmation:
terraform apply

# 5. Add YOLO UI security group rule
# Prompt user to manually add an ingress rule for TCP port 8001
# via Huawei Cloud console (VPC > Security Groups > Add Rule).
# Use restricted CIDR — do NOT open to all addresses.
# Wait for user confirmation before continuing.

# 6. Verify
terraform state list
terraform output -json

# 7. Cleanup
terraform destroy
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
- **Deploy links**: list each `text` and `url` from
  `deploy_links` array
- If `title` or `estimated_price_text` is empty, warn the user
  and suggest manual verification on the solution page

### 2. Download and normalize template

```bash
<python> <script_dir>/download_tf_template_file.py \
  --url "<tf_template_url>" \
  --out-dir <temp_dir>/yolo-workdir

<python> <script_dir>/normalize_tf_providers.py <temp_dir>/yolo-workdir \
  --region "cn-north-4"
```

`normalize_tf_providers.py` writes `terraform.auto.tfvars.json` (including region and other parameters).
If environment variables `HW_ACCESS_KEY`/`HW_SECRET_KEY` are not set, AK/SK fields are left empty.
**Prompt the user to manually edit the file to fill in AK/SK**, then continue to the next step.

### 3. Confirm variables

```bash
<python> <script_dir>/list_tf_variables.py <temp_dir>/yolo-workdir
```

Review with user. Block `apply` if sensitive variables are empty/weak.

### 4. Deploy

⛔ **STOP** — Before running `terraform apply`, review the `terraform plan`
output and confirm with the user (AskUserQuestion or equivalent).
Do NOT auto-apply. Only proceed after explicit user confirmation.

### 5. Add YOLO UI security group rule

The Terraform template does not include an ingress rule for TCP port 8001,
which is required for the YOLO training platform web UI. After deployment,
**prompt the user to manually add an ingress rule for TCP port 8001** via
Huawei Cloud console (VPC > Security Groups > Add Rule).
Use your own IP or a restricted CIDR — **do NOT open to all addresses**.

### 6. Verify

See [Verification Method](references/verification-method.md) and [Acceptance Criteria](references/acceptance-criteria.md).

### 7. Cleanup

## Parameters

| Parameter | Required | Default | Constraint |
| ---------- | -------- | ------- | ---------- |
| `region` | Yes | `cn-north-4` | Only supported region |
| AK/SK | Yes | — | Env vars `HW_ACCESS_KEY`/`HW_SECRET_KEY`; if absent, prompt user to edit tfvars.json |
| `ecs_password` | Yes | — | 8-26 chars, mixed case + digit + special |
| `ecs_flavor` | No | `p2s.2xlarge.8` | — |
| `system_disk_size` | No | 100 | 40-1024 GB |
| `data_disk_size` | No | 500 | 40-1024 GB |
| `bandwidth_size` | No | 300 | 1-300 Mbit/s |
| `charging_unit` | No | `month` | `month` or `year` |
| `charging_period` | No | 1 | — |

## Post-Deploy Output

- `terraform output -json` — includes `access_instructions` with YOLO platform URL
- YOLO UI: `http://<EIP>:8001` (allow ~10 min for cloud-init)
- Verify: `ssh root@<EIP> "docker ps"` and `ssh root@<EIP> "nvidia-smi"`

## Output Format

`terraform output -json` returns JSON with the following key fields:

```json
{
  "access_instructions": { "value": "http://<EIP>:8001" },
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
2. **Template download** — Confirm `.tf` files exist under `<temp_dir>/yolo-workdir`
   and `terraform validate` passes
3. **Variable confirmation** — Sensitive variables (AK/SK, password) are not
   empty in `list_tf_variables.py` output
4. **Deployment** — `terraform plan` shows no errors; user confirmed deployment; after `apply`,
   `terraform state list` shows all expected resources
5. **Service reachability** — Wait 10-15 min for cloud-init, then
   `curl -s http://<EIP>:8001` returns 200
6. **GPU** — `ssh root@<EIP> "nvidia-smi"` shows GPU device,
   `ssh root@<EIP> "docker ps"` shows YOLO container running

See [Verification Method](references/verification-method.md) and
[Acceptance Criteria](references/acceptance-criteria.md) for details.

## Best Practices

- Always `terraform plan` before `apply`
- Start with `charging_unit=month`; switch to `year` after validation
- Allow 10-15 min post-deploy for cloud-init
- Monitor GPU via `nvidia-smi`; adjust `ecs_flavor` if underutilized

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
- `terraform.auto.tfvars.json` is sensitive — never commit to VCS
- `normalize_tf_providers.py` writes region to tfvars; AK/SK left empty if env vars not set, user must fill manually
- Tool chain: Playwright CLI + Python + Terraform — no KooCLI
