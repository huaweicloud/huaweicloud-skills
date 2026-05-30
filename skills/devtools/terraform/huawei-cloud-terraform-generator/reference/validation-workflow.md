# Validation Workflow

This document describes the detailed validation workflow for Terraform configurations.

## Ensure Terraform is available

Before running validation, check whether Terraform is available in the current environment.

### Step 1: Check for Terraform binary

- Check if Terraform is available in the current PATH
- If found, verify with `terraform version` and proceed to provider check
- If not found, proceed to installation

### Step 2: Install Terraform if needed

- Install Terraform using an OS-appropriate method:
  - Prefer native package managers when available
  - Otherwise download and install the official Terraform binary
- Verify installation with `terraform version`
- If installation fails, abort and inform user about Terraform installation issue

## Check local provider cache version

Before downloading from remote, check if local provider cache exists and is up-to-date.

**Check locations:**

```
Project-local:    .terraform/providers/registry.terraform.io/huaweicloud/huaweicloud/
Global cache:     ~/.terraform.d/providers/registry.terraform.io/huaweicloud/huaweicloud/
                  ~/.terraform.d/plugins/registry.terraform.io/huaweicloud/huaweicloud/
```

**Decision process:**

1. If provider exists in any checked location:
   - Check provider version
   - If version >= 1.90.0 (latest stable): Use existing provider, skip download
   - If version < 1.90.0: Proceed to download latest version
2. If provider not found in any location: Proceed to download

## Download provider from Huawei Cloud mirror

Attempt to download the latest (ensure the downloaded provider version >= 1.90.0) huaweicloud provider from the Huawei Cloud mirror.

**Mirror URL:** `https://mirrors.huaweicloud.com/terraform/`

Configure Terraform CLI to use Huawei Cloud mirror:

- Write a `.tfrc` file with network_mirror pointing to the mirror URL
- Set `TF_CLI_CONFIG_FILE` environment variable to the `.tfrc` file path

Example `.tfrc` configuration:

```
provider_installation {
  network_mirror {
    url = "https://mirrors.huaweicloud.com/terraform/"
    include = ["registry.terraform.io/huaweicloud/*"]
  }
}
```

**Success:** Provider downloaded successfully → Proceed to validation
**Failure:** Download failed or mirror unreachable → Handle failure

## Handle provider download failure

If provider download from Huawei Cloud mirror failed or provider is unavailable:

**Abort the task with the following message:**

```
Failed to download Terraform provider from Huawei Cloud mirror.

Possible causes:
1. Network connectivity issue - Unable to reach https://mirrors.huaweicloud.com/terraform/
2. Firewall or proxy blocking the connection
3. Huawei Cloud mirror is temporarily unavailable

Please check your network configuration and try again.
You may need to:
- Verify internet connectivity
- Check firewall/proxy settings
- Contact your network administrator
```

**Do not:**

- Attempt to download from upstream Terraform registry as fallback
- Continue with validation without a valid provider
- Proceed with terraform apply

**Stop execution and wait for user to resolve the network issue before retrying.**

## Validation order

After Terraform configuration files are generated, execute validation in this order:

```
terraform fmt -recursive
terraform init
terraform validate
terraform plan
```

**Prerequisites for validation:**

- Terraform files must be generated first
- Provider must be available (either from local cache or successful download)
- Provider version must be >= 1.90.0
- `.terraform.lock.hcl` must be consistent with the installed provider

Do not stop after formatting or syntax validation if `terraform plan` has not succeeded yet.

## Authentication handling

Do not read or inspect credential-related environment variables or the actual values in terraform.tfvars.

If `terraform plan` fails because of authentication:

- explain that authentication failed
- remind the user to verify their credentials in terraform.tfvars
- ask the user to confirm when credentials are corrected
- re-run validation after confirmation

## Repair loop

If any validation step fails:

1. inspect the exact error
2. determine the real cause
3. fix the generated Terraform or the required runtime configuration
4. rerun the validation sequence

Typical causes include:

- missing provider configuration
- undeclared variables
- invalid resource arguments
- incorrect data source filters
- unsupported attributes
- missing dependencies
- authentication failures
- network issues

Repeat until `terraform plan` succeeds or the exact blocker is clearly identified.

## Cleanup

After validation, remove temporary or intermediate files that are no longer needed, while keeping the actual deliverables.

Keep:

- .tf files
- .tfvars
- README.md
- .terraform.lock.hcl
- .tfrc (if created for mirror configuration)

Do not keep unnecessary temporary artifacts generated during the preparation or validation process.
