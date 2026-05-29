# Deploy Batch Associate Tags

## Application Scenario

Tag Management Service (TMS) is a tag management service provided by Huawei Cloud, supporting adding, modifying, and deleting tags for cloud resources, helping you achieve resource classification management and cost analysis. Through batch tag association, tags can be added to multiple cloud resources in batch, improving tag management efficiency. Batch tag association supports adding the same tags to different types of resources (such as ECS, VPC, RDS, etc.) in batch, achieving unified classification and identification of resources. This best practice introduces how to use Terraform to automatically deploy batch tag association, including querying project lists and batch associating tags.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Projects List Query Data Source (data.huaweicloud\_identity\_projects)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/identity_projects)

### Resources

- [Resource Tags Resource (huaweicloud\_tms\_resource\_tags)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/tms_resource_tags)

### Resource/Data Source Dependencies

```
data.huaweicloud_identity_projects
    └── huaweicloud_tms_resource_tags
```

> Note: Resource tags need to specify project ID to determine the scope of tags. Project information in the current region can be obtained by querying the projects list data source.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Query Projects List

Add the following script to the TF file (such as main.tf) to query the projects list:

```hcl
variable "region_name" {
  description = "The region where the LTS service is located"
  type        = string
}

# Query projects list data source
data "huaweicloud_identity_projects" "test" {
  name = var.region_name
}

# Get exact matching project ID through local values
locals {
  exact_project_id = try([for v in data.huaweicloud_identity_projects.test.projects : v.id if v.name == var.region_name][0], null)
}
```

**Parameter Description**:

- **name**: Project name, assigned by referencing the input variable `region_name`, used to filter projects
- **exact\_project\_id**: Exact matching project ID, filtered from the projects list through local values `locals` to get the project ID with matching name

> Note: The projects list is used to obtain project IDs. Project IDs need to be referenced when batch associating tags later to determine the scope of tags.

### 3. Batch Associate Tags

Add the following script to the TF file (such as main.tf) to batch associate tags:

```hcl
variable "associated_resources_configuration" {
  description = "The configuration of the associated resources"
  type        = list(object({
    type = string
    id   = string
  }))
}

variable "resource_tags" {
  description = "The tags of the resources"
  type        = map(string)
}

# Create resource tags resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_tms_resource_tags" "test" {
  project_id = local.exact_project_id

  dynamic "resources" {
    for_each = var.associated_resources_configuration

    content {
      resource_type = resources.value.type
      resource_id   = resources.value.id
    }
  }

  tags = var.resource_tags
}
```

**Parameter Description**:

- **project\_id**: Project ID, assigned by referencing the local value `exact_project_id`, used to determine the scope of tags
- **resources**: Associated resource list, creates multiple resource configurations through dynamic block `dynamic "resources"` based on input variable `associated_resources_configuration`
  - **resource\_type**: Resource type, assigned by referencing the `type` in the input variable, supports multiple resource types such as `dcs`, `ecs`, `vpc`
  - **resource\_id**: Resource ID, assigned by referencing the `id` in the input variable
- **tags**: Tag key-value pairs, assigned by referencing the input variable `resource_tags`, format is `map(string)`

> Note: Batch tag association can add the same tags to multiple resources of different types in batch. Resource types and resource IDs need to match, ensuring resources exist. Tag key-value pairs can contain multiple tags for resource classification and identification.

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Associated resources configuration (Required)
associated_resources_configuration = [
  {
    type = "dcs"
    id   = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  }
]

# Resource tags configuration (Required)
resource_tags = {
  foo   = "bar"
  owner = "terraform"
}
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="associated_resources_configuration=[{type=\"dcs\",id=\"xxx\"}]" -var="resource_tags={foo=\"bar\"}"`
2. Environment variables: `export TF_VAR_resource_tags='{"foo":"bar","owner":"terraform"}'`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start batch associating tags
4. Run `terraform show` to view the associated tags

## Reference Information

- [Huawei Cloud TMS Product Documentation](https://support.huaweicloud.com/tms/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Batch Associate Tags](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/tms/batch-associate-tags)

# Deploy Preset Tags

## Application Scenario

Tag Management Service (TMS) is a tag management service provided by Huawei Cloud, supporting adding, modifying, and deleting tags for cloud resources, helping you achieve resource classification management and cost analysis. Preset tags are important functions of TMS service, used to create reusable tag templates, achieving standardized tag management. By creating preset tags, commonly used tag key-value pairs can be defined, and these preset tags can be automatically applied when creating resources later, improving tag management efficiency and consistency. This best practice introduces how to use Terraform to automatically deploy preset tags, including preset tag creation and configuration.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [Preset Tags Resource (huaweicloud\_tms\_tags)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/tms_tags)

### Resource/Data Source Dependencies

```
huaweicloud_tms_tags
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Create Preset Tags

Add the following script to the TF file (such as main.tf) to create preset tags:

```hcl
variable "preset_tags" {
  description = "The preset tags to be applied to the resource"
  type        = list(object({
    key   = string
    value = string
  }))
}

# Create preset tags resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_tms_tags" "test" {
  dynamic "tags" {
    for_each = var.preset_tags

    content {
      key   = tags.value.key
      value = tags.value.value
    }
  }
}
```

**Parameter Description**:

- **tags**: Tag list, creates multiple tags through dynamic block `dynamic "tags"` based on input variable `preset_tags`
  - **key**: Tag key, assigned by referencing the `key` in the input variable
  - **value**: Tag value, assigned by referencing the `value` in the input variable

> Note: Preset tags are used to create reusable tag templates, supporting creating multiple tag key-value pairs. After creating preset tags, these tags can be automatically applied when creating resources later, achieving standardized tag management.

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Preset tags configuration (Required)
preset_tags = [
  {
    key   = "foo"
    value = "bar"
  },
  {
    key   = "owner"
    value = "terraform"
  }
]
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="preset_tags=[{key=\"foo\",value=\"bar\"}]"`
2. Environment variables: `export TF_VAR_preset_tags='[{"key":"foo","value":"bar"}]'`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating preset tags
4. Run `terraform show` to view the created preset tags

## Reference Information

- [Huawei Cloud TMS Product Documentation](https://support.huaweicloud.com/tms/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Preset Tags](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/tms/preset-tags)

# Deploy Query Resource Types

## Application Scenario

Tag Management Service (TMS) is a tag management service provided by Huawei Cloud, supporting adding, modifying, and deleting tags for cloud resources, helping you achieve resource classification management and cost analysis. Resource type query is an important function of TMS service, used to query cloud resource types that support tag management. By querying resource types, service names and resource type lists that support tag management can be obtained, providing basic information for subsequent tag management operations. This best practice introduces how to use Terraform to automatically deploy resource type queries, including exact matching and fuzzy matching of service names, fuzzy matching of resource type names, and other query methods.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Resource Types Query Data Source (data.huaweicloud\_tms\_resource\_types)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/tms_resource_types)

### Resource/Data Source Dependencies

```
data.huaweicloud_tms_resource_types
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Query Resource Types

Add the following script to the TF file (such as main.tf) to query resource types:

```hcl
variable "exact_service_name" {
  description = "The exact service name to filter"
  type        = string
  default     = ""
}

variable "fuzzy_service_name" {
  description = "The fuzzy service name to filter"
  type        = string
  default     = ""
}

variable "fuzzy_resource_type_name" {
  description = "The fuzzy resource type name to filter"
  type        = string
  default     = ""
}

# Query resource types data source
data "huaweicloud_tms_resource_types" "test" {
  service_name = var.exact_service_name != "" ? var.exact_service_name : null
}

# Perform fuzzy matching and filtering through local values
locals {
  # All service names registered on TMS service (using fuzzy matching based on user-specified service name)
  regex_matched_service_names = distinct(var.fuzzy_service_name != "" ? [
    for v in data.huaweicloud_tms_resource_types.test.types[*].service_name : v if length(regexall(var.fuzzy_service_name, v)) > 0
  ] : data.huaweicloud_tms_resource_types.test.types[*].service_name)

  # All resource types (object including the resource type name and the service name to which the resource type
  # belongs) registered on TMS service (using fuzzy matching based on user-specified service name)
  regex_matched_resource_types_by_only_fuzzy_service_name = var.fuzzy_service_name != "" ? [
    for v in data.huaweicloud_tms_resource_types.test.types : v if length(regexall(var.fuzzy_service_name, v.service_name)) > 0
  ] : data.huaweicloud_tms_resource_types.test.types

  # All resource types (object including the resource type name and the service name to which the resource type
  # belongs) registered on TMS service (using fuzzy matching based on user-specified service name or resource type name)
  regex_matched_resource_types = var.fuzzy_resource_type_name != "" ? [
    for v in local.regex_matched_resource_types_by_only_fuzzy_service_name : v if length(regexall(var.fuzzy_resource_type_name, v.name)) > 0
  ] : local.regex_matched_resource_types_by_only_fuzzy_service_name
}
```

**Parameter Description**:

- **service\_name**: Service name, assigned by referencing the input variable `exact_service_name`, used for exact matching of service names, optional parameter
- **regex\_matched\_service\_names**: Service name list through fuzzy matching using local values `locals`. When `fuzzy_service_name` is not empty, fuzzy matching is performed; otherwise, all service names are returned
- **regex\_matched\_resource\_types\_by\_only\_fuzzy\_service\_name**: Resource type list through fuzzy matching based on service names using local values `locals`. When `fuzzy_service_name` is not empty, fuzzy matching is performed; otherwise, all resource types are returned
- **regex\_matched\_resource\_types**: Resource type list through fuzzy matching based on service names or resource type names using local values `locals`. When `fuzzy_resource_type_name` is not empty, fuzzy matching is performed; otherwise, results based on service name matching are returned

> Note: Resource type query supports both exact matching and fuzzy matching. Exact matching specifies service names through the `service_name` parameter, and fuzzy matching uses regular expressions through local values. Query results include service names and resource type names, which can be used for subsequent tag management operations.

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Fuzzy match service name (Optional)
fuzzy_service_name = "ccm"

# Fuzzy match resource type name (Optional)
fuzzy_resource_type_name = "certificate"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="fuzzy_service_name=ccm" -var="fuzzy_resource_type_name=certificate"`
2. Environment variables: `export TF_VAR_fuzzy_service_name=ccm`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to query resource types:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the query plan
3. Run `terraform apply` to execute the query operation
4. Run `terraform show` to view query results, or use `terraform output` to output local value results

## Reference Information

- [Huawei Cloud TMS Product Documentation](https://support.huaweicloud.com/tms/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Query Resource Types](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/tms/query-resource-types)
