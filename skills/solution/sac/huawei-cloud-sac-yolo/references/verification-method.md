# Verification Method

Success verification criteria for each workflow step.

## Step 1: Collect Inputs

| Check | Method |
| ------- | -------- |
| Region provided | `region` is non-empty and equals `cn-north-4` |
| AK/SK provided | `access_key` and `secret_key` are non-empty |
| ECS password provided | `ecs_password` non-empty, 8-26 chars, mixed |

## Step 2: Solution Info and Price Confirmation

| Check | Method |
| ------- | -------- |
| Extract script succeeds | `extract_sac_deploy_info.py` exits 0 |
| Output JSON valid | Output has `title`, `price_text`, `url` |
| Price non-empty | `estimated_price_text` is non-empty |
| Deploy confirmation | User replied "confirm deploy" |

## Step 3: Download Template + Normalize + Write AK/SK

| Check | Method |
| ------- | -------- |
| Template downloaded | `.tf` file exists in `<workdir>`, non-empty |
| Provider sources normalized | `normalize_tf_providers.py` exits 0 |
| Credentials file exists | `terraform.auto.tfvars.json` has keys |
| Credentials file not tracked | `terraform.auto.tfvars.json` not in git |

## Step 4: Confirm Terraform Variables

| Check | Method |
| ------- | -------- |
| Variable list succeeds | `list_tf_variables.py` exits 0 |
| Sensitive variables set | `ecs_password` meets complexity rules |
| AK/SK variables set | `access_key`, `secret_key`, `region` set |
| User confirmed | User reviewed and confirmed overrides |

## Step 5: Terraform Deploy

| Check | Method |
| ------- | -------- |
| terraform init | `terraform init` exits 0; `.terraform/` exists |
| terraform plan | `terraform plan` exits 0; shows resources |
| terraform apply | `terraform apply` exits 0; state has resources |
| Outputs available | `terraform output -json` has `access_instructions` |
