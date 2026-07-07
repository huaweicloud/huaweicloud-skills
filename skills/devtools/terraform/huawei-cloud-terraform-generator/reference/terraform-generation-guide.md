# Terraform Generation Guide

This document provides detailed guidance for generating Terraform configurations for Huawei Cloud resources.

## File Structure

Generate files in this exact order:

1. `providers.tf`
2. `variables.tf`
3. `main.tf`
4. `terraform.tfvars`
5. `README.md`

**Note:** Do NOT generate:

- `outputs.tf`
- any `output` blocks
- additional `.tf` files beyond the required structure

## providers.tf

`providers.tf` must include:

- a `terraform` block
- `required_providers`
- a `provider "huaweicloud"` block

Use explicit provider version constraints. Always use the latest stable version of the huaweicloud provider.

**Important:** Do NOT configure access_key and secret_key in the provider block. Credentials are read from environment variables (HW_ACCESS_KEY and HW_SECRET_KEY).

**Important:** The provider does not reliably resolve `security_token` from environment variables. The agent **must** read `HW_SECURITY_TOKEN` (or `HUAWEICLOUD_SECURITY_TOKEN`) from environment variables and configure it in the provider block. If the env var is not set, omit `security_token` from the provider block (permanent AK/SK scenario).

Example:

```hcl
terraform {
  required_providers {
    huaweicloud = {
      source  = "huaweicloud/huaweicloud"
      version = ">= 1.90.0"
    }
  }
}

provider "huaweicloud" {
  region         = var.region
  security_token = var.security_token
}
```

## variables.tf

`variables.tf` must include at least:

- region
- security_token

**Note:** Do NOT define `access_key` and `secret_key` variables.

All variables must include:

- description
- type

Example:

```hcl
variable "region" {
  description = "The region of Huawei Cloud"
  type        = string
}
variable "security_token" {
  description = "The security token for temporary credentials (STS). Leave empty for permanent AK/SK."
  type        = string
  sensitive   = true
  default     = ""
}
```

**Huawei Cloud Region and Project Name Mapping:**

| Region Code | Project Name |
|-------------|--------------|
| cn-north-1 | 华北-北京一 |
| cn-north-4 | 华北-北京四 |
| cn-north-9 | 华北-乌兰察布一 |
| cn-east-2 | 华东-上海二 |
| cn-east-3 | 华东-上海一 |
| cn-south-1 | 华南-广州 |
| cn-south-2 | 华南-深圳 |
| cn-southwest-2 | 西南-贵阳一 |
| cn-northeast-1 | 东北-大连 |
| ap-southeast-1 | 中国-香港 |

Use variables only for user-configurable values, such as:

- names
- CIDRs
- tags
- counts
- booleans
- business options
- region

Do not use variables for queryable cloud specifications when Terraform data sources can be used instead.

## main.tf

`main.tf` must contain:

- Terraform data sources at the top
- resources after data sources
- resources in dependency order

The generated resources must match the confirmed scenario and dependency chain.
Prefer implicit dependencies through references. Use depends_on only when necessary.

## terraform.tfvars

Must generate `terraform.tfvars` file (not `terraform.tfvars.example`)

Rules:

- include region
- include all required user-facing values
- reflect the confirmed plan where applicable
- never include access_key and secret_key

**Sensitive Information Handling:**

For all sensitive information (passwords, database credentials, API tokens, etc.), automatically generate random strong passwords:

1. **Generate strong passwords** for each sensitive field:
   - 16 characters minimum length
   - Contains uppercase letters (A-Z), lowercase letters (a-z), digits (0-9), special characters (!@#$%^&*)
   - Use cryptographically secure random generation

2. **Write to terraform.tfvars**:
   - Include the generated passwords in terraform.tfvars
   - Use descriptive variable names (e.g., `db_password`, `admin_password`, `api_token`)

3. **Inform the user**:
   - Display all generated passwords and credentials to the user
   - Remind user they can edit terraform.tfvars with their own values if needed

**Example terraform.tfvars with generated passwords:**

```hcl
region = "cn-north-4"

# Generated strong passwords - you can change these if needed
db_password    = "Kx9#mP2$vL7@nQ4!"
admin_password = "Rt5^wY8*bF3#zC6@"
api_token      = "Hj2&mN9$kB5!pV8#"
```

**Strong password generation example (Python):**

```python
import secrets
import string

chars = string.ascii_letters + string.digits + '!@#$%^&*'
password = ''.join(secrets.choice(chars) for _ in range(16))
```

## README.md

README.md must include:

- scenario summary
- prerequisites
- file descriptions
- usage steps
- variable descriptions
- validation commands
- reminder not to commit secrets
- instructions for running terraform apply
- note that AK/SK should be configured via environment variables (HW_ACCESS_KEY, HW_SECRET_KEY) without providing setup examples
- note that all sensitive information (passwords, database credentials, API tokens, etc.) are automatically set to random strong passwords in terraform.tfvars
- display of all generated passwords and credentials
- reminder that user can edit terraform.tfvars with their own values if needed

## Use reliable resource information during planning

Recommended specifications, models, prices, and reusable resource facts must come from:

- explicit user input
- a reliable resource information lookup channel

They must not be fabricated.

This applies to values such as:

- availability zones
- images
- compute flavors
- RDS flavors
- cluster versions
- existing resource names or IDs
- pricing

Reliable query results are used to help determine and confirm the right resource plan before Terraform generation.

## Query before using specifications (CRITICAL)

**CRITICAL: Always query available specifications from the target region before using them in Terraform.**

### Availability Zones

**Problem:** Availability zone names vary by region. Using `names[0]` always picks the first zone, which may not be what the user wants.

**Solution:** Query availability zones and let user confirm, then use as a variable.

```
Workflow:
1. User selects region (e.g., cn-north-4)
2. Query: data.huaweicloud_availability_zones or API
3. Present available zones: cn-north-4a, cn-north-4b, cn-north-4c
4. User confirms one (e.g., cn-north-4a)
5. Use as variable in Terraform
```

**Terraform usage:**
```hcl
# ❌ Wrong: Always use first zone
availability_zone = data.huaweicloud_availability_zones.test.names[0]

# ✅ Correct: Use variable from user confirmation
variable "availability_zone" {
  description = "The availability zone for resources"
  type        = string
}

resource "huaweicloud_compute_instance" "main" {
  availability_zone = var.availability_zone
}
```

### ECS Flavors

**Problem:** Flavor availability varies by region. Using hardcoded flavor names will cause failures.

**Solution:** Query flavors using `huawei-cloud-computing-query` skill before proposing to user.

```
Workflow:
1. User selects region (e.g., cn-north-4)
2. Query: list_flavors.py --region cn-north-4 --availability_zone cn-north-4a
3. Select flavor from query results (NOT from hardcoded defaults)
4. Use exact flavor name in Terraform
```

**Terraform usage:**
```hcl
# Option A: Use flavor_name directly (recommended for simplicity)
resource "huaweicloud_compute_instance" "main" {
  flavor_name = "s6.small.1"  # Must be from query result
}

# Option B: Use data source with filter criteria (e.g., performance_type, cpu_core_count, memory_size)
data "huaweicloud_compute_flavors" "selected" {
  availability_zone = var.availability_zone
  performance_type  = "normal"
  cpu_core_count    = 2
  memory_size       = 4
}
```

### Images

**Problem 1:** Image names must match EXACTLY. User may say "EulerOS 2.0" but actual name is "Huawei Cloud EulerOS 2.0 Standard 64 bit".

**Problem 2:** Image version mismatch. User may say "Ubuntu 22.04" but if only `os = "Ubuntu"` is used, any Ubuntu version (16.04, 18.04, 20.04, 22.04, 24.04) may be returned.

**Solution:** Query images using `huawei-cloud-computing-query` skill and match user's intent to exact name with version.

```
Workflow:
1. User says "use Ubuntu 22.04"
2. Query: list_images.py --region cn-north-4 --imagetype gold --platform Ubuntu
3. Find matching image with correct version from results:
   - Ubuntu 24.04 server 64bit
   - Ubuntu 22.04 server 64bit  ← Match this
   - Ubuntu 20.04 server 64bit
4. Use EXACT name in Terraform
```

**Image version mismatch example:**
| User confirms | Template uses | Result returned | Actual installed |
|--------------|---------------|-----------------|------------------|
| Ubuntu 22.04 | `os = "Ubuntu"` | Ubuntu 24.04 | Ubuntu 24.04 ❌ |
| Ubuntu 22.04 | `os_version = "Ubuntu 22.04 server 64bit"` | Ubuntu 22.04 | Ubuntu 22.04 ✅ |

**Terraform usage:**
```hcl
# ❌ Wrong: No version specified, may return any Ubuntu version
data "huaweicloud_images_images" "selected" {
  os = "Ubuntu"  # Could return 16.04, 18.04, 20.04, 22.04, or 24.04
}

# ✅ Correct: Use exact image name
data "huaweicloud_images_image" "selected" {
  name        = "Ubuntu 22.04 server 64bit"  # EXACT match with version
  most_recent = true
}

# ✅ Correct: Use os_version field (more stable)
data "huaweicloud_images_images" "selected" {
  os_version = "Ubuntu 22.04 server 64bit"  # Version included
  visibility = "public"
  imagetype  = "gold"
  most_recent = true
}

resource "huaweicloud_compute_instance" "main" {
  image_id = data.huaweicloud_images_image.selected.id
}
```

### Forbidden practices

- ❌ Using `data.huaweicloud_availability_zones.test.names[0]` to always pick first zone
- ❌ Using hardcoded flavor names like `s6.small.1` without querying
- ❌ Using image names like "EulerOS 2.0" without exact match
- ❌ Using `os = "Ubuntu"` without version (may return wrong version)
- ❌ Guessing specifications based on other regions
- ❌ Using user input directly without validation against query results
- ❌ Proceeding if query returns empty results

## Handle empty query results (CRITICAL)

**If query returns empty results, immediately report error and ask user to change conditions.**

```
Workflow:
1. Query specifications using API
2. If empty: Stop, report error, suggest alternatives, ask user to change conditions
3. If not empty: Proceed with recommendation
```

**Use exact names instead of data source queries:**
```hcl
# ❌ Wrong
flavor_id = data.huaweicloud_compute_flavors.test[0].flavors[0].id

# ✅ Correct
flavor_name = var.flavor_name  # "s6.small.1" from pre-validated query
```

## Security group rules (CRITICAL)

**Generate rules based on user-confirmed ports, NOT hardcoded defaults.**

```
Workflow:
1. Infer ports from user's goal (Web → 80, 443; SSH → 22; DB → 3306, 5432)
2. Ask user to confirm: "需要开放哪些端口？推荐：80、443、22"
3. Generate rules for confirmed ports only
```

**Forbidden:**
- ❌ Using only egress rule without ingress rules
- ❌ Using hardcoded default ports without asking user
- ❌ Generating rules that don't match user confirmation

## Use Terraform data sources in generated code when supported

When the Terraform provider supports resolving specifications or existing resources through data
sources, prefer using Terraform data sources in the generated configuration instead of hardcoding
final values.

Typical examples include:

- availability zones
- images
- compute flavors
- RDS flavors
- cluster versions
- existing resources referenced by names or filters

In other words:

- reliable query channels help determine the right candidate values during planning
- Terraform data sources help resolve or validate those values during Terraform execution

## Variables vs data sources

Use variables for:

- resource names
- CIDR blocks
- tags
- booleans
- counts
- business options
- region
- credentials
- user-provided preferences
- filter conditions used to narrow down lookups

Do not expose final cloud specification values as plain variables when they can be resolved through Terraform data sources.

Examples of values that should usually be resolved through data sources when supported:

- flavor IDs
- image IDs
- availability zones
- DB flavor IDs
- cluster versions

When the user explicitly chooses a specification, use that choice as a confirmed input or as a
filter condition where appropriate, and still prefer resolving the final resource fact through a
Terraform data source.

## Data source usage rules

When using Terraform data sources:

1. place them at the top of `main.tf`
2. use clear names such as `available` or `selected`
3. use variables only as filters when needed
4. reference resolved values from resources
5. do not silently replace empty results with guessed values
6. resource names used in data source filters must match exactly - no partial matches or approximations

**Critical: Exact Resource Name Matching**
When using data sources to query resources by name (such as images, flavors, or existing resources), the resource name must match **exactly** with the actual resource name in Huawei Cloud:

- Case-sensitive matching
- No partial matches
- No wildcard approximations
- Must be the complete, precise name as it exists in the cloud

This applies to:

- `data "huaweicloud_images_image"` - `name` must match the exact image name
- `data "huaweicloud_compute_flavors"` - flavor names must be exact
- `data "huaweicloud_rds_flavors"` - DB flavor names must be exact
- Any other data source that queries by resource name

Example:

```hcl
data "huaweicloud_availability_zones" "available" {}

data "huaweicloud_images_image" "selected" {
  # The image name must match exactly with the actual image name in Huawei Cloud
  name        = var.image_name
  most_recent = true
}

data "huaweicloud_compute_flavors" "available" {
  availability_zone = data.huaweicloud_availability_zones.available.names[0]
}

resource "huaweicloud_compute_instance" "main" {
  name              = var.ecs_name
  admin_pass        = var.ecs_password
  flavor_id         = data.huaweicloud_compute_flavors.available.flavors[0].id
  image_id          = data.huaweicloud_images_image.selected.id
  availability_zone = data.huaweicloud_availability_zones.available.names[0]
}
```
