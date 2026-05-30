# Deploy Organization

## Application Scenario

Software Repository for Container (SWR) is a container image hosting service provided by Huawei Cloud, supporting storage, management, and distribution of Docker images, helping you achieve rapid deployment and continuous integration of container applications. Organizations are fundamental resources of SWR service, used to manage and organize container image repositories. By creating organizations, multiple image repositories can be created under the organization, achieving classified management and permission control of images. This best practice introduces how to use Terraform to automatically deploy organizations, including organization basic information configuration.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [Organization Resource (huaweicloud\_swr\_organization)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/swr_organization)

### Resource/Data Source Dependencies

```
huaweicloud_swr_organization
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Create Organization

Add the following script to the TF file (such as main.tf) to create an organization:

```hcl
variable "organization_name" {
  description = "The organization name"
  type        = string
}

# Create organization resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_swr_organization" "test" {
  name = var.organization_name
}
```

**Parameter Description**:

- **name**: Organization name, assigned by referencing the input variable `organization_name`

> Note: Organization names must be unique in SWR service, used to identify and manage container image repositories. After creating an organization, image repositories can be created under that organization.

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Organization configuration (Required)
organization_name = "tf_test_swr_organization_name"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="organization_name=tf_test_swr_organization_name"`
2. Environment variables: `export TF_VAR_organization_name=tf_test_swr_organization_name`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the organization
4. Run `terraform show` to view the created organization

## Reference Information

- [Huawei Cloud SWR Product Documentation](https://support.huaweicloud.com/swr/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Organization](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/swr/organization)

# Deploy Retention Policy

## Application Scenario

Software Repository for Container (SWR) is a container image hosting service provided by Huawei Cloud, supporting storage, management, and distribution of Docker images, helping you achieve rapid deployment and continuous integration of container applications. Image retention policies are important functions of SWR service, used to automatically clean up expired image versions and control storage space of image repositories. By configuring retention policies, the number of images to retain or retention days can be set, and tag selectors can be used to filter images that need to be retained, achieving automated image management and storage optimization. This best practice introduces how to use Terraform to automatically deploy retention policies, including creating organizations, creating image repositories, and configuring image retention policies.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [Organization Resource (huaweicloud\_swr\_organization)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/swr_organization)
- [Repository Resource (huaweicloud\_swr\_repository)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/swr_repository)
- [Image Retention Policy Resource (huaweicloud\_swr\_image\_retention\_policy)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/swr_image_retention_policy)

### Resource/Data Source Dependencies

```
huaweicloud_swr_organization
    └── huaweicloud_swr_repository
        └── huaweicloud_swr_image_retention_policy
```

> Note: Image retention policies must belong to a repository of an organization, so the organization and repository need to be created first. Retention policies are associated with the corresponding repository by referencing the organization name and repository name.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Create Organization

Add the following script to the TF file (such as main.tf) to create an organization:

```hcl
variable "organization_name" {
  description = "The organization name"
  type        = string
}

# Create organization resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_swr_organization" "test" {
  name = var.organization_name
}
```

**Parameter Description**:

- **name**: Organization name, assigned by referencing the input variable `organization_name`

> Note: Organization names must be unique in SWR service, used to identify and manage container image repositories.

### 3. Create Repository

Add the following script to the TF file (such as main.tf) to create a repository:

```hcl
variable "repository_name" {
  description = "The repository name"
  type        = string
}

variable "category" {
  description = "The category"
  type        = string
  default     = "linux"
}

# Create repository resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_swr_repository" "test" {
  organization = huaweicloud_swr_organization.test.name
  name         = var.repository_name
  category     = var.category
}
```

**Parameter Description**:

- **organization**: Organization name, assigned by referencing the organization resource name
- **name**: Repository name, assigned by referencing the input variable `repository_name`
- **category**: Repository category, assigned by referencing the input variable `category`, default is `linux`, optional parameter

> Note: Repository names must be unique within the organization. After creating a repository, retention policies can be configured for that repository.

### 4. Configure Image Retention Policy

Add the following script to the TF file (such as main.tf) to configure an image retention policy:

```hcl
variable "policy_type" {
  description = "The policy type"
  type        = string
}

variable "policy_number" {
  description = "The policy number"
  type        = number
}

variable "tag_selectors_configuration" {
  description = "The configuration of the tag selectors"
  type        = list(object({
    kind    = string
    pattern = number
  }))

  default = []
}

# Create image retention policy resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_swr_image_retention_policy" "test" {
  organization = huaweicloud_swr_organization.test.name
  repository   = huaweicloud_swr_repository.test.name
  type         = var.policy_type
  number       = var.policy_number

  dynamic "tag_selectors" {
    for_each = var.tag_selectors_configuration

    content {
      kind    = tag_selectors.value.kind
      pattern = tag_selectors.value.pattern
    }
  }
}
```

**Parameter Description**:

- **organization**: Organization name, assigned by referencing the organization resource name
- **repository**: Repository name, assigned by referencing the repository resource name
- **type**: Policy type, assigned by referencing the input variable `policy_type`, supports `date_rule` (by date rule) and `tag_rule` (by tag rule)
- **number**: Retention count or days, assigned by referencing the input variable `policy_number`. Depending on the policy type, it represents the number of images to retain or retention days
- **tag\_selectors**: Tag selector list, creates multiple tag selectors through dynamic block `dynamic "tag_selectors"` based on input variable `tag_selectors_configuration`, optional parameter
  - **kind**: Selector type, supports `label` (tag), etc.
  - **pattern**: Match pattern, used to filter images that need to be retained

> Note: Retention policies are used to automatically clean up expired image versions. When policy type is `date_rule`, `number` represents retention days; when policy type is `tag_rule`, `number` represents the number of images to retain. Tag selectors are used to filter images that need to be retained, and can perform exact matching based on tag patterns.

### 5. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Organization configuration (Required)
organization_name = "tf_test_swr_organization_name"

# Repository configuration (Required)
repository_name = "tf_test_swr_repository_name"

# Retention policy configuration (Required)
policy_type = "date_rule"
policy_number = 30

# Tag selector configuration (Optional)
tag_selectors_configuration = [
  {
    kind    = "label"
    pattern = 1.1
  }
]
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="organization_name=tf_test_swr_organization_name" -var="repository_name=tf_test_swr_repository_name"`
2. Environment variables: `export TF_VAR_organization_name=tf_test_swr_organization_name`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 6. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating organization, repository, and image retention policy
4. Run `terraform show` to view the created image retention policy

## Reference Information

- [Huawei Cloud SWR Product Documentation](https://support.huaweicloud.com/swr/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Retention Policy](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/swr/retention-policy)

# Deploy Repository

## Application Scenario

Software Repository for Container (SWR) is a container image hosting service provided by Huawei Cloud, supporting storage, management, and distribution of Docker images, helping you achieve rapid deployment and continuous integration of container applications. Image repositories are core resources of SWR service, used to store and manage container images. By creating image repositories, image repositories can be created under specified organizations, configuring repository types and categories, achieving centralized management and version control of images. This best practice introduces how to use Terraform to automatically deploy image repositories, including creating organizations and creating image repositories.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [Organization Resource (huaweicloud\_swr\_organization)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/swr_organization)
- [Repository Resource (huaweicloud\_swr\_repository)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/swr_repository)

### Resource/Data Source Dependencies

```
huaweicloud_swr_organization
    └── huaweicloud_swr_repository
```

> Note: Image repositories must belong to an organization, so the organization needs to be created first. Image repositories are associated with the corresponding organization by referencing the organization name.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Create Organization

Add the following script to the TF file (such as main.tf) to create an organization:

```hcl
variable "organization_name" {
  description = "The organization name"
  type        = string
}

# Create organization resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_swr_organization" "test" {
  name = var.organization_name
}
```

**Parameter Description**:

- **name**: Organization name, assigned by referencing the input variable `organization_name`

> Note: Organization names must be unique in SWR service, used to identify and manage container image repositories. After creating an organization, image repositories can be created under that organization.

### 3. Create Repository

Add the following script to the TF file (such as main.tf) to create a repository:

```hcl
variable "repository_name" {
  description = "The repository name"
  type        = string
}

variable "category" {
  description = "The category"
  type        = string
  default     = "linux"
}

# Create repository resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_swr_repository" "test" {
  organization = huaweicloud_swr_organization.test.name
  name         = var.repository_name
  category     = var.category
}
```

**Parameter Description**:

- **organization**: Organization name, assigned by referencing the organization resource name
- **name**: Repository name, assigned by referencing the input variable `repository_name`
- **category**: Repository category, assigned by referencing the input variable `category`, default is `linux`, optional parameter

> Note: Repository names must be unique within the organization. Repository categories are used to identify image types, supporting types such as `linux` and `windows`. After creating a repository, container images can be stored by pushing images to that repository.

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Organization configuration (Required)
organization_name = "tf_test_swr_organization_name"

# Repository configuration (Required)
repository_name = "tf_test_swr_repository_name"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="organization_name=tf_test_swr_organization_name" -var="repository_name=tf_test_swr_repository_name"`
2. Environment variables: `export TF_VAR_organization_name=tf_test_swr_organization_name`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating organization and repository
4. Run `terraform show` to view the created repository

## Reference Information

- [Huawei Cloud SWR Product Documentation](https://support.huaweicloud.com/swr/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Repository](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/swr/repository)
