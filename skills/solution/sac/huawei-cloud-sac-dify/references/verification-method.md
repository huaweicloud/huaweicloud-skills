# Verification Method

Success verification criteria for each workflow step.

## Step 1: Collect Inputs

| Check | Method |
| ------- | -------- |
| Primary region provided | `region_id` is non-empty and in the allowed region list |
| Provider region consistency | `normalize_tf_providers.py --region` uses the same value as `region_id` |
| AK/SK provided | `access_key` and `secret_key` are non-empty (env or local tfvars) |
| ECS password provided | `ecs_password` is non-empty and meets complexity constraints |

## Step 2: Solution Info and Price Confirmation

| Check | Method |
| ------- | -------- |
| Extract script succeeds | `extract_sac_deploy_info.py` exits 0 |
| Output JSON valid | Output has `title`, `estimated_price_text`, `url` |
| Price non-empty | `estimated_price_text` is non-empty |
| Deploy confirmation | User explicitly confirms deploy after price review |

## Step 3: Download Template + Normalize + Write AK/SK

| Check | Method |
| ------- | -------- |
| Preferred template downloaded | Download first from `https://documentation-samples.obs.cn-north-4.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-moudle/flexus/dify-ecs.tf`; resulting `.tf` or `.tf.json` file exists in `<workdir>`, non-empty |
| Provider sources normalized | `normalize_tf_providers.py` exits 0 |
| Credentials file exists | `<workdir>/terraform.auto.tfvars.json` exists with credential keys |
| Credentials file not tracked | `<workdir>/terraform.auto.tfvars.json` is not committed to git |

## Step 4: Confirm Terraform Variables

| Check | Method |
| ------- | -------- |
| Variable list succeeds | `list_tf_variables.py` exits 0 |
| Sensitive values masked | sensitive defaults are partially masked in output |
| Required sensitive variables set | `ecs_password`, `access_key`, `secret_key` are set before apply |
| User confirmed | User reviewed values and confirmed deploy |

## Step 5: Terraform Deploy

| Check | Method |
| ------- | -------- |
| terraform init | `terraform init` exits 0; `.terraform/` exists |
| terraform plan | `terraform plan` exits 0; shows planned resources |
| terraform apply | `terraform apply` exits 0; state has expected resources |
| Outputs available | `terraform output -json` includes `access_instructions` |
| Service reachable | `http://<EIP>` is reachable after cloud-init warm-up |

## Step 6: Terraform Destroy and Local Cleanup

| Check | Method |
| ------- | -------- |
| terraform destroy | `terraform destroy` exits 0; managed resources are removed |
| tfvars removed after destroy | `<workdir>/terraform.auto.tfvars.json` no longer exists after successful destroy |
| Failed destroy preserves tfvars | If destroy fails, keep `<workdir>/terraform.auto.tfvars.json` for retry |
