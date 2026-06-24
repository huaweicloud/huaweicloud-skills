# Validation Workflow

This document describes the detailed validation workflow for Terraform configurations.

## Configure Huawei Cloud Mirror (MUST DO FIRST)

**CRITICAL: Configure Huawei Cloud mirror BEFORE any terraform init attempt.**

The official Terraform registry (registry.terraform.io) and GitHub releases may be slow or unreachable. Always use Huawei Cloud mirror first.

### Mirror URL

`https://mirrors.huaweicloud.com/terraform/`

### Configuration Steps

1. Create `.tfrc` file in the project directory:
   ```
   provider_installation {
     network_mirror {
       url = "https://mirrors.huaweicloud.com/terraform/"
       include = ["registry.terraform.io/huaweicloud/*"]
     }
   }
   ```

2. Set `TF_CLI_CONFIG_FILE` environment variable:
   ```bash
   export TF_CLI_CONFIG_FILE="/path/to/project/.tfrc"
   ```

3. All subsequent terraform commands will use the mirror

**Do NOT skip this step. Do NOT attempt terraform init without mirror configuration.**

### MANDATORY: Every terraform init command MUST include TF_CLI_CONFIG_FILE

**This is a hard rule with no exceptions. Every `terraform init` execution (including `terraform init -upgrade`) MUST be preceded by setting `TF_CLI_CONFIG_FILE`. A bare `terraform init` without the mirror is FORBIDDEN.**

**Correct execution pattern:**
```bash
export TF_CLI_CONFIG_FILE="/path/to/project/.tfrc" && terraform init -upgrade
```

**Forbidden patterns:**
- ❌ `terraform init` (no env var set)
- ❌ `terraform init -upgrade` (no env var set)
- ❌ `cd some-dir && terraform init` (no env var set)

**Before generating any bash command that runs `terraform init`, you MUST verify that `TF_CLI_CONFIG_FILE` is set in that same command. If it is not, the command is invalid and must not be executed.**

## Query Specifications Before Generating Terraform (CRITICAL)

### Query Availability Zones

1. Determine target region
2. Query using Terraform data source or API
3. Present available zones to user
4. User confirms specific zone
5. Use confirmed zone as a variable (NOT as `names[0]`)

### Query ECS Flavors

1. Determine target region and availability zone
2. Query using `huawei-cloud-computing-query` skill: `list_flavors.py --region --availability_zone [--name_prefix]`
3. Select flavor from query results
4. Use exact flavor name in Terraform

### Query Images

1. Determine target region
2. Query using `huawei-cloud-computing-query` skill: `list_images.py --region --imagetype gold [--platform]`
3. Match user's intent to exact image name with version from results
4. Use EXACT image name (including version) in Terraform

### Common name mismatches

| User says | Actual name in Huawei Cloud |
|-----------|----------------------------|
| EulerOS 2.0 | Huawei Cloud EulerOS 2.0 Standard 64 bit |
| Ubuntu 22.04 | Ubuntu 22.04 server 64bit |

### Image version mismatch

| User confirms | Template uses | Result |
|--------------|---------------|--------|
| Ubuntu 22.04 | `os = "Ubuntu"` | Ubuntu 24.04 ❌ |
| Ubuntu 22.04 | `os_version = "Ubuntu 22.04 server 64bit"` | Ubuntu 22.04 ✅ |

### Handle empty query results

```
Workflow:
1. Query specifications using API
2. If empty: Stop, report error, suggest alternatives, ask user to change conditions
3. If not empty: Proceed with recommendation
```

**Use exact names instead of data source queries.**

### Confirm security group rules

```
Workflow:
1. Infer ports from user's goal (Web → 80, 443; SSH → 22; DB → 3306, 5432)
2. Ask user: "需要开放哪些端口？推荐：80、443、22"
3. User confirms specific ports
4. Generate rules for confirmed ports only
```

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
                  ~/.terraform.d/plugins/local-registry/huaweicloud/huaweicloud/
```

**Decision process:**

1. If provider exists in any checked location:
   - Check provider version
   - If version >= 1.90.0 (latest stable): Use existing provider, skip download
   - If version < 1.90.0: Proceed to download latest version
2. If provider not found in any location: Proceed to download

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

## Remote-exec provisioner dependencies

When using `remote-exec` provisioners with password authentication in the generated Terraform configuration, ensure `sshpass` and `expect` are installed on the machine running Terraform.

**Install dependencies (if not already installed):**

```bash
# Debian/Ubuntu
apt-get update && apt-get install -y sshpass expect

# CentOS/RHEL
yum install -y sshpass expect

# Fedora
dnf install -y sshpass expect
```

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
