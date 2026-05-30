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
  region = var.region
}
```

## variables.tf

`variables.tf` must include at least:

- region

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
```

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
- never include real credentials in examples
- never include access_key and secret_key

**Sensitive information handling:**
For non-AK/SK sensitive fields (passwords, tokens, database credentials, etc.):

- Use placeholder values (e.g., "CHANGE_ME", "YOUR_PASSWORD_HERE", "REQUIRED")
- Add comments instructing user to replace with actual values
- Example: `db_password = "CHANGE_ME"  # Replace with your actual database password`

Remind user to review and update terraform.tfvars before running terraform apply.

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
- instructions to review and update terraform.tfvars with actual values for non-AK/SK sensitive fields (passwords, tokens, etc.)

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
