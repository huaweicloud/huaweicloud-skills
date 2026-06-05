# Deploy Automated Resource Share Invitation Processing

## Application Scenario

Resource Access Manager (RAM) is a resource sharing service provided by Huawei Cloud, supporting cross-account resource sharing and management to help you achieve unified resource management and access control. Through automated resource share invitation processing, you can batch query pending resource share invitations and automatically accept or reject these invitations, improving the efficiency and convenience of resource sharing management. This best practice introduces how to use Terraform to automatically process resource share invitations, including querying pending invitations and batch accepting or rejecting invitations.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Resource Share Invitations Query Data Source (data.huaweicloud\_ram\_resource\_share\_invitations)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/ram_resource_share_invitations)

### Resources

- [Resource Share Accepter Resource (huaweicloud\_ram\_resource\_share\_accepter)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/ram_resource_share_accepter)

### Resource/Data Source Dependencies

```
data.huaweicloud_ram_resource_share_invitations
    └── huaweicloud_ram_resource_share_accepter
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Query Pending Resource Share Invitations

Add the following script to the TF file (such as main.tf) to query pending resource share invitations:

```hcl
variable "resource_share_ids" {
  description = "List of resource share IDs to query invitations for"
  type        = list(string)
  default     = []
}

# Query pending invitations for specified resource share ID list
data "huaweicloud_ram_resource_share_invitations" "test" {
  resource_share_ids = var.resource_share_ids
  status             = "pending"
}
```

**Parameter Description**:

- **resource\_share\_ids**: Resource share ID list, assigned by referencing the input variable `resource_share_ids`, used to specify the resource shares to query
- **status**: Invitation status, set to `pending` to query pending invitations

### 3. Process Resource Share Invitations

Add the following script to the TF file (such as main.tf) to process resource share invitations:

```hcl
variable "action" {
  description = "The action to perform on invitations"
  type        = string
  default     = "reject"

  validation {
    condition     = contains(["accept", "reject"], var.action)
    error_message = "The action must be either 'accept' or 'reject'."
  }
}

# Batch process invitations: accept or reject
resource "huaweicloud_ram_resource_share_accepter" "test" {
  count = length(data.huaweicloud_ram_resource_share_invitations.test.resource_share_invitations)

  resource_share_invitation_id = data.huaweicloud_ram_resource_share_invitations.test.resource_share_invitations[count.index].id
  action                       = var.action
}
```

**Parameter Description**:

- **count**: Resource count, dynamically creates resources based on the number of pending invitations queried
- **resource\_share\_invitation\_id**: Resource share invitation ID, assigned by referencing the invitation ID in the data source query results
- **action**: Processing action, assigned by referencing the input variable `action`. Optional values are `accept` (accept) or `reject` (reject), default is `reject`

> Note: Through the `count` parameter, resources can be dynamically created based on the number of invitations queried, achieving batch processing. The processing action can be accept or reject, configured according to actual needs.

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Resource share ID list (Required)
resource_share_ids = [
  "resource-share-id-1",
  "resource-share-id-2"
]

# Processing action (Optional, default is reject)
action = "accept"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="resource_share_ids=['resource-share-id-1','resource-share-id-2']" -var="action=accept"`
2. Environment variables: `export TF_VAR_resource_share_ids='["resource-share-id-1","resource-share-id-2"]'`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to process resource share invitations:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource processing plan
3. After confirming that the resource plan is correct, run `terraform apply` to start processing resource share invitations
4. Run `terraform show` to view the processed invitations

## Reference Information

- [Huawei Cloud RAM Product Documentation](https://support.huaweicloud.com/ram/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Automated Resource Share Invitation Processing](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/ram/automated-resource-share-invitation-processing)

# Deploy Cross-Account Resource Share

## Application Scenario

Resource Access Manager (RAM) is a resource sharing service provided by Huawei Cloud, supporting cross-account resource sharing and management to help you achieve unified resource management and access control. Through cross-account resource sharing, network resources such as VPCs, subnets, and security groups, as well as computing and storage resources such as ECS and RDS, can be shared with other accounts or organizations, achieving unified resource management and access control. This best practice introduces how to use Terraform to automatically deploy cross-account resource sharing, including resource share instance creation, principal configuration, resource URN configuration, and permission configuration.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [Resource Share Resource (huaweicloud\_ram\_resource\_share)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/ram_resource_share)

### Resource/Data Source Dependencies

```
huaweicloud_ram_resource_share
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Create Resource Share

Add the following script to the TF file (such as main.tf) to create a resource share:

```hcl
variable "resource_share_name" {
  description = "The name of the resource share"
  type        = string
}

variable "description" {
  description = "The description of the resource share"
  type        = string
  default     = ""
}

variable "principals" {
  description = "The list of one or more principals (account IDs or organization IDs) to share resources with"
  type        = list(string)
}

variable "resource_urns" {
  description = "The list of URNs of one or more resources to be shared. If not specified, URNs will be automatically generated from created resources (VPC, subnet, security group)"
  type        = set(string)
  default     = []
}

variable "permission_ids" {
  description = "The list of RAM permissions associated with the resource share"
  type        = list(string)
  default     = []
}

variable "allow_external_principals" {
  description = "Whether resources can be shared with any accounts outside the organization"
  type        = bool
  default     = false
}

# Create resource share resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_ram_resource_share" "test" {
  name                      = var.resource_share_name
  description               = var.description
  principals                = var.principals
  resource_urns             = var.resource_urns
  permission_ids            = var.permission_ids
  allow_external_principals = var.allow_external_principals
}
```

**Parameter Description**:

- **name**: Resource share name, assigned by referencing the input variable `resource_share_name`
- **description**: Resource share description, assigned by referencing the input variable `description`, optional parameter
- **principals**: Principal list, assigned by referencing the input variable `principals`, used to specify the list of account IDs or organization IDs to share resources with
- **resource\_urns**: Resource URN list, assigned by referencing the input variable `resource_urns`, used to specify the list of resource URNs to be shared, optional parameter
- **permission\_ids**: Permission ID list, assigned by referencing the input variable `permission_ids`, used to specify the list of RAM permissions associated with the resource share, optional parameter
- **allow\_external\_principals**: Whether resources can be shared with any accounts outside the organization, assigned by referencing the input variable `allow_external_principals`, default is `false`

> Note: Resource URN is the unique identifier of a resource, in the format `resource_type:region:account_id:resource_type:resource_id`. If resource URNs are not specified, the system will automatically generate them based on created resources (VPC, subnet, security group, etc.). Principals can be account IDs or organization IDs, used to specify the recipients of shared resources.

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Resource share basic information (Required)
resource_share_name = "cross-account-vpc-share"
description         = "Share VPC resources with other accounts in the organization"

# Principals: Account IDs or Organization IDs to share resources with (Required)
# Should be replaced with real account IDs
principals = [
  "01234567890123456789012345678901",
  "98765432109876543210987654321098"
]

# The list of URNs of one or more resources to be shared (Optional)
# Should be replaced with real resource URNs
resource_urns = [
  "vpc:cn-north-4:8f06724e5c6f41f59d3e2f3ad897bb4d:subnet:5de72eeb-7977-4602-8186-8766982d9bcc"
]

# The list of RAM permissions associated with the resource share (Optional)
# Should be replaced with real permission IDs
permission_ids = [
  "f5153698-ca8b-4b3c-a839-13ff71f67885"
]
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="resource_share_name=cross-account-vpc-share" -var="principals=['01234567890123456789012345678901']"`
2. Environment variables: `export TF_VAR_resource_share_name=cross-account-vpc-share`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the resource share
4. Run `terraform show` to view the created resource share

## Reference Information

- [Huawei Cloud RAM Product Documentation](https://support.huaweicloud.com/ram/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Cross-Account Resource Share](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/ram/cross-account-resource-share)

# Deploy Fine-Grained Permission Management

## Application Scenario

Resource Access Manager (RAM) is a resource sharing service provided by Huawei Cloud, supporting cross-account resource sharing and management to help you achieve unified resource management and access control. Through fine-grained permission management, precise permission control can be configured for resource sharing, achieving more flexible and secure resource sharing. By querying available permissions and associating them with resource shares, the usage scope and operation permissions of shared resources can be precisely controlled. This best practice introduces how to use Terraform to automatically deploy fine-grained permission management, including querying available permissions and associating permissions with resource shares.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Resource Permissions Query Data Source (data.huaweicloud\_ram\_resource\_permissions)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/ram_resource_permissions)

### Resources

- [Resource Share Permission Resource (huaweicloud\_ram\_resource\_share\_permission)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/ram_resource_share_permission)

### Resource/Data Source Dependencies

```
data.huaweicloud_ram_resource_permissions
    └── huaweicloud_ram_resource_share_permission
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Query Available Resource Permissions

Add the following script to the TF file (such as main.tf) to query available resource permissions:

```hcl
variable "query_resource_type" {
  description = "The resource type for querying available permissions"
  type        = string
  default     = ""
}

variable "query_permission_type" {
  description = "The type of the permission to query"
  type        = string
  default     = "ALL"
}

variable "query_permission_name" {
  description = "The name of the permission to query"
  type        = string
  default     = ""
}

# Query available resource permissions
data "huaweicloud_ram_resource_permissions" "test" {
  resource_type   = var.query_resource_type != "" ? var.query_resource_type : null
  permission_type = var.query_permission_type
  name            = var.query_permission_name != "" ? var.query_permission_name : null
}
```

**Parameter Description**:

- **resource\_type**: Resource type, assigned by referencing the input variable `query_resource_type`, used to specify the resource type for querying permissions, optional parameter
- **permission\_type**: Permission type, assigned by referencing the input variable `query_permission_type`. Optional values include `ALL` (all), `SYSTEM` (system permissions), `CUSTOM` (custom permissions), default is `ALL`
- **name**: Permission name, assigned by referencing the input variable `query_permission_name`, used to filter permissions by name, optional parameter

> Note: By setting different query conditions, a list of permissions that meet the requirements can be filtered. If the resource type is not specified, permissions for all resource types will be queried.

### 3. Associate Permissions with Resource Share

Add the following script to the TF file (such as main.tf) to associate permissions with a resource share:

```hcl
variable "resource_share_id" {
  description = "The ID of the RAM resource share"
  type        = string
}

variable "permission_replace" {
  description = "Whether to replace existing permissions when associating a new permission"
  type        = bool
  default     = false
}

# Batch associate queried permissions with resource share
resource "huaweicloud_ram_resource_share_permission" "test" {
  count = length(data.huaweicloud_ram_resource_permissions.test.permissions)

  resource_share_id = var.resource_share_id
  permission_id     = data.huaweicloud_ram_resource_permissions.test.permissions[count.index].id
  replace           = var.permission_replace
}
```

**Parameter Description**:

- **count**: Resource count, dynamically creates resources based on the number of permissions queried
- **resource\_share\_id**: Resource share ID, assigned by referencing the input variable `resource_share_id`, used to specify the resource share to associate permissions with
- **permission\_id**: Permission ID, assigned by referencing the permission ID in the data source query results
- **replace**: Whether to replace existing permissions, assigned by referencing the input variable `permission_replace`. When associating a new permission, whether to replace existing permissions, default is `false`

> Note: Through the `count` parameter, resources can be dynamically created based on the number of permissions queried, achieving batch permission association. If `replace` is `true`, existing permissions of the resource share will be replaced when associating a new permission; if `false`, new permissions will be appended.

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Permission query configuration (Optional)
query_resource_type = "vpc:subnets"

# Resource share ID (Required)
resource_share_id = "your-resource-share-id"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="query_resource_type=vpc:subnets" -var="resource_share_id=your-resource-share-id"`
2. Environment variables: `export TF_VAR_resource_share_id=your-resource-share-id`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start associating permissions with the resource share
4. Run `terraform show` to view the associated permissions

## Reference Information

- [Huawei Cloud RAM Product Documentation](https://support.huaweicloud.com/ram/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Fine-Grained Permission Management](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/ram/fine-grained-permission-management)
