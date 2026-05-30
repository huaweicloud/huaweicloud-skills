# Deploy Cloud Application Policy Group

## Application Scenario

Huawei Cloud Cloud Desktop (Workspace) is a cloud computing-based desktop virtualization service that provides enterprise users with secure and convenient cloud office solutions. Cloud application policy groups are an important component of the Workspace service's cloud application functionality, used to configure unified management policies for cloud application groups, including client behavior control, session management, security policies, etc.

Through cloud application policy groups, enterprises can achieve fine-grained management and security control of cloud applications, including policy configurations such as automatic reconnection interval, session persistence time, and screen capture prohibition. Policy groups support priority-based application and can set different policies for different application groups or all application groups, meeting diverse enterprise management needs. This best practice will introduce how to use Terraform to automatically deploy Workspace cloud application policy groups, including cloud application server group creation, cloud application group creation, and policy group configuration.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Workspace Service Query Data Source (data.huaweicloud\_workspace\_service)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/workspace_service)

### Resources

- [Workspace Application Server Group Resource (huaweicloud\_workspace\_app\_server\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/workspace_app_server_group)
- [Workspace Application Group Resource (huaweicloud\_workspace\_app\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/workspace_app_group)
- [Workspace Application Policy Group Resource (huaweicloud\_workspace\_app\_policy\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/workspace_app_policy_group)

### Resource/Data Source Dependencies

```
data.huaweicloud_workspace_service.test
    └── huaweicloud_workspace_app_server_group.test
        └── huaweicloud_workspace_app_group.test
            └── huaweicloud_workspace_app_policy_group.test
```

## Implementation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://hcbp.gitbook.io/huaweicloud-provider/product-introduction/prepare_before_deploy) for configuration introduction.

### 2. Query Workspace Service Information Through Data Source

Add the following script to the TF file (such as main.tf) to instruct Terraform to perform a data source query, the query results are used to create cloud application server groups:

```hcl
# Query all Workspace service information in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block), used to create cloud application server groups
data "huaweicloud_workspace_service" "test" {}
```

**Parameter Description**:

- This data source requires no additional parameters and automatically queries Workspace service information in the current region

### 3. Create Workspace Cloud Application Server Group

Add the following script to the TF file (such as main.tf) to instruct Terraform to create cloud application server group resources:

```hcl
variable "app_server_group_name" {
  description = "The name of the APP server group"
  type        = string
}

variable "app_server_group_app_type" {
  description = "The application type of the APP server group"
  type        = string
  default     = "SESSION_DESKTOP_APP"
}

variable "app_server_group_os_type" {
  description = "The operating system type of the APP server group"
  type        = string
  default     = "Windows"
}

variable "app_server_group_flavor_id" {
  description = "The flavor ID of the APP server group"
  type        = string
}

variable "app_server_group_image_id" {
  description = "The image ID of the APP server group"
  type        = string
}

variable "app_server_group_image_product_id" {
  description = "The image product ID of the APP server group"
  type        = string
}

variable "app_server_group_system_disk_type" {
  description = "The system disk type of the APP server group"
  type        = string
  default     = "SAS"
}

variable "app_server_group_system_disk_size" {
  description = "The system disk size of the APP server group in GB"
  type        = number
  default     = 80

  validation {
    condition     = var.app_server_group_system_disk_size >= 40 && var.app_server_group_system_disk_size <= 2048
    error_message = "The system disk size must be between 40 and 2048 GB."
  }
}

# Create Workspace cloud application server group resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_workspace_app_server_group" "test" {
  name             = var.app_server_group_name
  app_type         = var.app_server_group_app_type
  os_type          = var.app_server_group_os_type
  flavor_id        = var.app_server_group_flavor_id
  image_type       = "gold"
  image_id         = var.app_server_group_image_id
  image_product_id = var.app_server_group_image_product_id
  vpc_id           = data.huaweicloud_workspace_service.test.vpc_id
  subnet_id        = try(data.huaweicloud_workspace_service.test.network_ids[0], null)
  system_disk_type = var.app_server_group_system_disk_type
  system_disk_size = var.app_server_group_system_disk_size
  is_vdi           = true
}
```

**Parameter Description**:

- **name**: Cloud application server group name, assigned by referencing the input variable `app_server_group_name`
- **app\_type**: Application type, assigned by referencing the input variable `app_server_group_app_type`, default is "SESSION\_DESKTOP\_APP"
- **os\_type**: Operating system type, assigned by referencing the input variable `app_server_group_os_type`, default is "Windows"
- **flavor\_id**: Flavor ID, assigned by referencing the input variable `app_server_group_flavor_id`
- **image\_type**: Image type, fixed as "gold" (golden image)
- **image\_id**: Image ID, assigned by referencing the input variable `app_server_group_image_id`
- **image\_product\_id**: Image product ID, assigned by referencing the input variable `app_server_group_image_product_id`
- **vpc\_id**: VPC ID, assigned based on the return results of the Workspace service query data source (data.huaweicloud\_workspace\_service)
- **subnet\_id**: Subnet ID, assigned based on the return results of the Workspace service query data source (data.huaweicloud\_workspace\_service)
- **system\_disk\_type**: System disk type, assigned by referencing the input variable `app_server_group_system_disk_type`, default is "SAS"
- **system\_disk\_size**: System disk size, assigned by referencing the input variable `app_server_group_system_disk_size`, default is 80GB
- **is\_vdi**: Whether it is VDI mode, fixed as true

### 4. Create Workspace Cloud Application Group

Add the following script to the TF file to instruct Terraform to create cloud application group resources:

```hcl
variable "app_group_name" {
  description = "The name of the APP group"
  type        = string
}

# Create Workspace cloud application group resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_workspace_app_group" "test" {
  depends_on = [huaweicloud_workspace_app_server_group.test]

  server_group_id = huaweicloud_workspace_app_server_group.test.id
  name            = var.app_group_name
  type            = "SESSION_DESKTOP_APP"
  description     = "Created APP group by Terraform"
}
```

**Parameter Description**:

- **depends\_on**: Explicit dependency declaration, ensuring that the cloud application server group is created before creating the cloud application group
- **server\_group\_id**: The ID of the cloud application server group, referencing the ID of the cloud application server group resource created earlier
- **name**: Cloud application group name, assigned by referencing the input variable `app_group_name`
- **type**: Cloud application group type, fixed as "SESSION\_DESKTOP\_APP" indicating a session desktop application group
- **description**: Cloud application group description, fixed as "Created APP group by Terraform"

### 5. Create Workspace Cloud Application Policy Group

Add the following script to the TF file to instruct Terraform to create cloud application policy group resources:

```hcl
variable "policy_group_name" {
  description = "The name of the policy group"
  type        = string
}

variable "policy_group_priority" {
  description = "The priority of the policy group"
  type        = number
  default     = 1
}

variable "policy_group_description" {
  description = "The description of the policy group"
  type        = string
  default     = "Created APP policy group by Terraform"
}

variable "target_type" {
  description = "The type of target for the policy group"
  type        = string
  default     = "APPGROUP"

  validation {
    condition     = contains(["APPGROUP", "ALL"], var.target_type)
    error_message = "The target_type must be either 'APPGROUP' or 'ALL'."
  }
}

variable "automatic_reconnection_interval" {
  description = "The automatic reconnection interval in minutes"
  type        = number
  default     = 10

  validation {
    condition     = var.automatic_reconnection_interval >= 1 && var.automatic_reconnection_interval <= 60
    error_message = "The automatic_reconnection_interval must be between 1 and 60 minutes."
  }
}

variable "session_persistence_time" {
  description = "The session persistence time in minutes"
  type        = number
  default     = 120

  validation {
    condition     = var.session_persistence_time >= 1 && var.session_persistence_time <= 1440
    error_message = "The session_persistence_time must be between 1 and 1440 minutes."
  }
}

variable "forbid_screen_capture" {
  description = "Whether to forbid screen capture"
  type        = bool
  default     = true
}

# Create Workspace cloud application policy group resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_workspace_app_policy_group" "test" {
  depends_on = [huaweicloud_workspace_app_group.test]

  name        = var.policy_group_name
  priority    = var.policy_group_priority
  description = var.policy_group_description

  targets {
    id   = var.target_type == "APPGROUP" ? huaweicloud_workspace_app_group.test.id : "default-apply-all-targets"
    name = var.target_type == "APPGROUP" ? huaweicloud_workspace_app_group.test.name : "All-Targets"
    type = var.target_type
  }

  policies = jsonencode({
    "client": {
      "automatic_reconnection_interval": var.automatic_reconnection_interval,
      "session_persistence_time":        var.session_persistence_time,
      "forbid_screen_capture":           var.forbid_screen_capture
    }
  })
}
```

**Parameter Description**:

- **depends\_on**: Explicit dependency declaration, ensuring that the cloud application group is created before creating the policy group
- **name**: Policy group name, assigned by referencing the input variable `policy_group_name`
- **priority**: Policy group priority, assigned by referencing the input variable `policy_group_priority`, default is 1, smaller values indicate higher priority
- **description**: Policy group description, assigned by referencing the input variable `policy_group_description`, default is "Created APP policy group by Terraform"
- **targets**: Policy group target configuration block
  - **id**: Target ID, if target type is "APPGROUP" then use the cloud application group ID, otherwise use "default-apply-all-targets" to indicate applying to all targets
  - **name**: Target name, if target type is "APPGROUP" then use the cloud application group name, otherwise use "All-Targets"
  - **type**: Target type, assigned by referencing the input variable `target_type`, default is "APPGROUP" indicating applying to specified application group, "ALL" indicating applying to all targets
- **policies**: Policy configuration, using jsonencode function to encode policy configuration as JSON string
  - **client.automatic\_reconnection\_interval**: Client automatic reconnection interval (minutes), assigned by referencing the input variable `automatic_reconnection_interval`, default is 10 minutes
  - **client.session\_persistence\_time**: Session persistence time (minutes), assigned by referencing the input variable `session_persistence_time`, default is 120 minutes
  - **client.forbid\_screen\_capture**: Whether to forbid screen capture, assigned by referencing the input variable `forbid_screen_capture`, default is true

> Note: Policy groups support priority-based application. When multiple policy groups are applied to the same target, policy groups with higher priority will override those with lower priority. Policy configuration uses JSON format and can be converted from HCL objects to JSON strings using the jsonencode function.

### 6. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Cloud application server group configuration
app_server_group_name             = "tf_test_server_group"
app_server_group_app_type         = "SESSION_DESKTOP_APP"
app_server_group_os_type          = "Windows"
app_server_group_flavor_id        = "workspace.appstream.general.xlarge.4"
app_server_group_image_id         = "2ac7b1fb-b198-422b-a45f-61ea285cb6e7"
app_server_group_image_product_id = "OFFI886188719633408000"
app_server_group_system_disk_type = "SAS"
app_server_group_system_disk_size = 80

# Cloud application group configuration
app_group_name = "tf_test_app_group"

# Policy group configuration
policy_group_name = "tf_test_policy_group"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command line parameters: `terraform apply -var="app_server_group_name=my-server-group" -var="app_group_name=my-app-group"`
2. Environment variables: `export TF_VAR_app_server_group_name=my-server-group`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 7. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating cloud application server groups, cloud application groups, and cloud application policy groups
4. Run `terraform show` to view the created cloud application policy group details

## Reference Information

- [Huawei Cloud Workspace Product Documentation](https://support.huaweicloud.com/intl/en-us/workspace/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Workspace Cloud Application Policy Group](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/workspace/app/policy_group)

# Deploy Cloud Application Policy Group Scaling Policy

## Application Scenario

Huawei Cloud Cloud Desktop (Workspace) is a cloud computing-based desktop virtualization service that provides enterprise users with secure and convenient cloud office solutions. Cloud application policy group scaling policies are an important component of the Workspace service's cloud application functionality, used to configure automatic scaling policies for cloud application server groups, automatically adjusting the number of server instances based on session usage to achieve elastic resource expansion and cost optimization.

Through cloud application policy group scaling policies, enterprises can automatically adjust the number of instances in cloud application server groups based on actual business load. When session usage exceeds the threshold, the system automatically scales out, and when session idle time reaches the set value, the system automatically scales in. This automatic scaling mechanism helps enterprises achieve on-demand resource allocation, improve resource utilization, reduce operating costs, and ensure user access experience. This best practice will introduce how to use Terraform to automatically deploy Workspace cloud application policy group scaling policies, including cloud application server group creation, cloud application group creation, policy group configuration, and scaling policy configuration.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Workspace Service Query Data Source (data.huaweicloud\_workspace\_service)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/workspace_service)

### Resources

- [Workspace Application Server Group Resource (huaweicloud\_workspace\_app\_server\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/workspace_app_server_group)
- [Workspace Application Group Resource (huaweicloud\_workspace\_app\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/workspace_app_group)
- [Workspace Application Policy Group Resource (huaweicloud\_workspace\_app\_policy\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/workspace_app_policy_group)
- [Workspace Application Server Group Scaling Policy Resource (huaweicloud\_workspace\_app\_server\_group\_scaling\_policy)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/workspace_app_server_group_scaling_policy)

### Resource/Data Source Dependencies

```
data.huaweicloud_workspace_service.test
    └── huaweicloud_workspace_app_server_group.test
        ├── huaweicloud_workspace_app_group.test
        │   └── huaweicloud_workspace_app_policy_group.test
        └── huaweicloud_workspace_app_server_group_scaling_policy.test
```

## Implementation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://hcbp.gitbook.io/huaweicloud-provider/product-introduction/prepare_before_deploy) for configuration introduction.

### 2. Query Workspace Service Information Through Data Source

Add the following script to the TF file (such as main.tf) to instruct Terraform to perform a data source query, the query results are used to create cloud application server groups:

```hcl
# Query all Workspace service information in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block), used to create cloud application server groups
data "huaweicloud_workspace_service" "test" {}
```

**Parameter Description**:

- This data source requires no additional parameters and automatically queries Workspace service information in the current region

### 3. Create Workspace Cloud Application Server Group

Add the following script to the TF file (such as main.tf) to instruct Terraform to create cloud application server group resources:

```hcl
variable "app_server_group_name" {
  description = "The name of the APP server group"
  type        = string
}

variable "app_server_group_app_type" {
  description = "The application type of the APP server group"
  type        = string
  default     = "SESSION_DESKTOP_APP"
}

variable "app_server_group_os_type" {
  description = "The operating system type of the APP server group"
  type        = string
  default     = "Windows"
}

variable "app_server_group_flavor_id" {
  description = "The flavor ID of the APP server group"
  type        = string
}

variable "app_server_group_image_id" {
  description = "The image ID of the APP server group"
  type        = string
}

variable "app_server_group_image_product_id" {
  description = "The image product ID of the APP server group"
  type        = string
}

variable "app_server_group_system_disk_type" {
  description = "The system disk type of the APP server group"
  type        = string
  default     = "SAS"
}

variable "app_server_group_system_disk_size" {
  description = "The system disk size of the APP server group in GB"
  type        = number
  default     = 80

  validation {
    condition     = var.app_server_group_system_disk_size >= 40 && var.app_server_group_system_disk_size <= 2048
    error_message = "The system disk size must be between 40 and 2048 GB."
  }
}

# Create Workspace cloud application server group resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_workspace_app_server_group" "test" {
  name             = var.app_server_group_name
  app_type         = var.app_server_group_app_type
  os_type          = var.app_server_group_os_type
  flavor_id        = var.app_server_group_flavor_id
  image_type       = "gold"
  image_id         = var.app_server_group_image_id
  image_product_id = var.app_server_group_image_product_id
  vpc_id           = data.huaweicloud_workspace_service.test.vpc_id
  subnet_id        = try(data.huaweicloud_workspace_service.test.network_ids[0], null)
  system_disk_type = var.app_server_group_system_disk_type
  system_disk_size = var.app_server_group_system_disk_size
  is_vdi           = true
}
```

**Parameter Description**:

- **name**: Cloud application server group name, assigned by referencing the input variable `app_server_group_name`
- **app\_type**: Application type, assigned by referencing the input variable `app_server_group_app_type`, default is "SESSION\_DESKTOP\_APP"
- **os\_type**: Operating system type, assigned by referencing the input variable `app_server_group_os_type`, default is "Windows"
- **flavor\_id**: Flavor ID, assigned by referencing the input variable `app_server_group_flavor_id`
- **image\_type**: Image type, fixed as "gold" (golden image)
- **image\_id**: Image ID, assigned by referencing the input variable `app_server_group_image_id`
- **image\_product\_id**: Image product ID, assigned by referencing the input variable `app_server_group_image_product_id`
- **vpc\_id**: VPC ID, assigned based on the return results of the Workspace service query data source (data.huaweicloud\_workspace\_service)
- **subnet\_id**: Subnet ID, assigned based on the return results of the Workspace service query data source (data.huaweicloud\_workspace\_service)
- **system\_disk\_type**: System disk type, assigned by referencing the input variable `app_server_group_system_disk_type`, default is "SAS"
- **system\_disk\_size**: System disk size, assigned by referencing the input variable `app_server_group_system_disk_size`, default is 80GB
- **is\_vdi**: Whether it is VDI mode, fixed as true

### 4. Create Workspace Cloud Application Group

Add the following script to the TF file to instruct Terraform to create cloud application group resources:

```hcl
variable "app_group_name" {
  description = "The name of the APP group"
  type        = string
}

# Create Workspace cloud application group resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_workspace_app_group" "test" {
  depends_on = [huaweicloud_workspace_app_server_group.test]

  server_group_id = huaweicloud_workspace_app_server_group.test.id
  name            = var.app_group_name
  type            = "SESSION_DESKTOP_APP"
  description     = "Created APP group by Terraform"
}
```

**Parameter Description**:

- **depends\_on**: Explicit dependency declaration, ensuring that the cloud application server group is created before creating the cloud application group
- **server\_group\_id**: The ID of the cloud application server group, referencing the ID of the cloud application server group resource created earlier
- **name**: Cloud application group name, assigned by referencing the input variable `app_group_name`
- **type**: Cloud application group type, fixed as "SESSION\_DESKTOP\_APP" indicating a session desktop application group
- **description**: Cloud application group description, fixed as "Created APP group by Terraform"

### 5. Create Workspace Cloud Application Policy Group

Add the following script to the TF file to instruct Terraform to create cloud application policy group resources:

```hcl
variable "policy_group_name" {
  description = "The name of the policy group"
  type        = string
}

variable "policy_group_priority" {
  description = "The priority of the policy group"
  type        = number
  default     = 1
}

variable "policy_group_description" {
  description = "The description of the policy group"
  type        = string
  default     = "Created APP policy group by Terraform"
}

variable "target_type" {
  description = "The type of target for the policy group"
  type        = string
  default     = "APPGROUP"

  validation {
    condition     = contains(["APPGROUP", "ALL"], var.target_type)
    error_message = "The target_type must be either 'APPGROUP' or 'ALL'."
  }
}

variable "automatic_reconnection_interval" {
  description = "The automatic reconnection interval in minutes"
  type        = number
  default     = 10

  validation {
    condition     = var.automatic_reconnection_interval >= 1 && var.automatic_reconnection_interval <= 60
    error_message = "The automatic_reconnection_interval must be between 1 and 60 minutes."
  }
}

variable "session_persistence_time" {
  description = "The session persistence time in minutes"
  type        = number
  default     = 120

  validation {
    condition     = var.session_persistence_time >= 1 && var.session_persistence_time <= 1440
    error_message = "The session_persistence_time must be between 1 and 1440 minutes."
  }
}

variable "forbid_screen_capture" {
  description = "Whether to forbid screen capture"
  type        = bool
  default     = true
}

# Create Workspace cloud application policy group resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_workspace_app_policy_group" "test" {
  depends_on = [huaweicloud_workspace_app_group.test]

  name        = var.policy_group_name
  priority    = var.policy_group_priority
  description = var.policy_group_description

  targets {
    id   = var.target_type == "APPGROUP" ? huaweicloud_workspace_app_group.test.id : "default-apply-all-targets"
    name = var.target_type == "APPGROUP" ? huaweicloud_workspace_app_group.test.name : "All-Targets"
    type = var.target_type
  }

  policies = jsonencode({
    "client": {
      "automatic_reconnection_interval": var.automatic_reconnection_interval,
      "session_persistence_time":        var.session_persistence_time,
      "forbid_screen_capture":           var.forbid_screen_capture
    }
  })
}
```

**Parameter Description**:

- **depends\_on**: Explicit dependency declaration, ensuring that the cloud application group is created before creating the policy group
- **name**: Policy group name, assigned by referencing the input variable `policy_group_name`
- **priority**: Policy group priority, assigned by referencing the input variable `policy_group_priority`, default is 1, smaller values indicate higher priority
- **description**: Policy group description, assigned by referencing the input variable `policy_group_description`, default is "Created APP policy group by Terraform"
- **targets**: Policy group target configuration block
  - **id**: Target ID, if target type is "APPGROUP" then use the cloud application group ID, otherwise use "default-apply-all-targets" to indicate applying to all targets
  - **name**: Target name, if target type is "APPGROUP" then use the cloud application group name, otherwise use "All-Targets"
  - **type**: Target type, assigned by referencing the input variable `target_type`, default is "APPGROUP" indicating applying to specified application group, "ALL" indicating applying to all targets
- **policies**: Policy configuration, using jsonencode function to encode policy configuration as JSON string
  - **client.automatic\_reconnection\_interval**: Client automatic reconnection interval (minutes), assigned by referencing the input variable `automatic_reconnection_interval`, default is 10 minutes
  - **client.session\_persistence\_time**: Session persistence time (minutes), assigned by referencing the input variable `session_persistence_time`, default is 120 minutes
  - **client.forbid\_screen\_capture**: Whether to forbid screen capture, assigned by referencing the input variable `forbid_screen_capture`, default is true

### 6. Create Workspace Cloud Application Server Group Scaling Policy

Add the following script to the TF file to instruct Terraform to create cloud application server group scaling policy resources:

```hcl
variable "max_scaling_amount" {
  description = "The maximum number of instances that can be scaled out"
  type        = number

  validation {
    condition     = var.max_scaling_amount >= 1 && var.max_scaling_amount <= 100
    error_message = "The max_scaling_amount must be between 1 and 100."
  }
}

variable "single_expansion_count" {
  description = "The number of instances to scale out in a single scaling operation"
  type        = number

  validation {
    condition     = var.single_expansion_count >= 1 && var.single_expansion_count <= 10
    error_message = "The single_expansion_count must be between 1 and 10."
  }
}

variable "session_usage_threshold" {
  description = "The session usage threshold percentage"
  type        = number
  default     = 80

  validation {
    condition     = var.session_usage_threshold >= 1 && var.session_usage_threshold <= 100
    error_message = "The session_usage_threshold must be between 1 and 100."
  }
}

variable "shrink_after_session_idle_minutes" {
  description = "The number of minutes to wait before shrinking idle instances"
  type        = number
  default     = 30

  validation {
    condition     = var.shrink_after_session_idle_minutes >= 1 && var.shrink_after_session_idle_minutes <= 1440
    error_message = "The shrink_after_session_idle_minutes must be between 1 and 1440 minutes."
  }
}

# Create Workspace cloud application server group scaling policy resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_workspace_app_server_group_scaling_policy" "test" {
  depends_on = [huaweicloud_workspace_app_server_group.test]

  server_group_id        = huaweicloud_workspace_app_server_group.test.id
  max_scaling_amount     = var.max_scaling_amount
  single_expansion_count = var.single_expansion_count

  scaling_policy_by_session {
    session_usage_threshold           = var.session_usage_threshold
    shrink_after_session_idle_minutes = var.shrink_after_session_idle_minutes
  }
}
```

**Parameter Description**:

- **depends\_on**: Explicit dependency declaration, ensuring that the cloud application server group is created before creating the scaling policy
- **server\_group\_id**: The ID of the cloud application server group, referencing the ID of the cloud application server group resource created earlier
- **max\_scaling\_amount**: The maximum number of instances that can be scaled out, assigned by referencing the input variable `max_scaling_amount`, valid range is 1 to 100
- **single\_expansion\_count**: The number of instances to scale out in a single scaling operation, assigned by referencing the input variable `single_expansion_count`, valid range is 1 to 10
- **scaling\_policy\_by\_session**: Scaling policy configuration block based on sessions
  - **session\_usage\_threshold**: Session usage threshold (percentage), assigned by referencing the input variable `session_usage_threshold`, default is 80%. When session usage exceeds this threshold, scaling out is triggered
  - **shrink\_after\_session\_idle\_minutes**: The number of minutes to wait before shrinking idle instances, assigned by referencing the input variable `shrink_after_session_idle_minutes`, default is 30 minutes. When session idle time reaches this value, scaling in is triggered

> Note: The scaling policy automatically adjusts based on session usage. When session usage exceeds the threshold, the system automatically scales out instances; when session idle time reaches the set value, the system automatically scales in instances. This enables elastic resource expansion and cost optimization.

### 7. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Cloud application server group configuration
app_server_group_name             = "tf_test_server_group"
app_server_group_flavor_id        = "workspace.appstream.general.xlarge.4"
app_server_group_image_id         = "2ac7b1fb-b198-422b-a45f-61ea285cb6e7"
app_server_group_image_product_id = "OFFI886188719633408000"

# Cloud application group configuration
app_group_name = "tf_test_app_group"

# Policy group configuration
policy_group_name = "tf_test_policy_group"

# Scaling policy configuration
max_scaling_amount     = 10
single_expansion_count = 2
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command line parameters: `terraform apply -var="app_server_group_name=my-server-group" -var="max_scaling_amount=10"`
2. Environment variables: `export TF_VAR_app_server_group_name=my-server-group`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 8. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating cloud application server groups, cloud application groups, cloud application policy groups, and scaling policies
4. Run `terraform show` to view the created cloud application policy group scaling policy details

## Reference Information

- [Huawei Cloud Workspace Product Documentation](https://support.huaweicloud.com/intl/en-us/workspace/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Workspace Cloud Application Policy Group Scaling Policy](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/workspace/app/policy_group_scaling_policy)

# Deploy Cloud Application Server Group

## Application Scenario

Huawei Cloud Cloud Desktop (Workspace) is a cloud computing-based desktop virtualization service that provides enterprise users with secure and convenient cloud office solutions. Cloud application server groups are an important component of the Workspace service, used to host various applications and provide users with a unified application access experience.

Through cloud application server groups, enterprises can achieve centralized application deployment, unified management, and security control. Users can access cloud applications through various terminal devices without installing and maintaining software locally. This best practice will introduce how to use Terraform to automatically deploy Workspace cloud application server groups.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Workspace Service Query Data Source (data.huaweicloud\_workspace\_service)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/workspace_service)

### Resources

- [Workspace Application Server Group Resource (huaweicloud\_workspace\_app\_server\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/workspace_app_server_group)

### Resource/Data Source Dependencies

```
data.huaweicloud_workspace_service.test
    └── huaweicloud_workspace_app_server_group.test
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Workspace Service Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the results of which are used to create cloud application server groups:

```hcl
# Get all Workspace service information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create cloud application server groups
data "huaweicloud_workspace_service" "test" {}
```

**Parameter Description**:

- This data source requires no additional parameters and automatically queries Workspace service information in the current region

### 3. Create Workspace Cloud Application Server Group

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a cloud application server group resource:

```hcl
# Create a Workspace cloud application server group resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_workspace_app_server_group" "test" {
  name             = var.app_server_group_name
  app_type         = var.app_server_group_app_type
  os_type          = var.app_server_group_os_type
  flavor_id        = var.app_server_group_flavor_id
  image_type       = "gold"
  image_id         = var.app_server_group_image_id
  image_product_id = var.app_server_group_image_product_id
  vpc_id           = data.huaweicloud_workspace_service.test.vpc_id
  subnet_id        = try(data.huaweicloud_workspace_service.test.network_ids[0], null)
  system_disk_type = var.app_server_group_system_disk_type
  system_disk_size = var.app_server_group_system_disk_size
  is_vdi           = true
}
```

**Parameter Description**:

- **name**: Cloud application server group name, assigned by referencing the input variable app\_server\_group\_name
- **app\_type**: Application type, assigned by referencing the input variable app\_server\_group\_app\_type, default is "SESSION\_DESKTOP\_APP"
- **os\_type**: Operating system type, assigned by referencing the input variable app\_server\_group\_os\_type, default is "Windows"
- **flavor\_id**: Flavor ID, assigned by referencing the input variable app\_server\_group\_flavor\_id
- **image\_type**: Image type, fixed as "gold" (golden image)
- **image\_id**: Image ID, assigned by referencing the input variable app\_server\_group\_image\_id
- **image\_product\_id**: Image product ID, assigned by referencing the input variable app\_server\_group\_image\_product\_id
- **vpc\_id**: VPC ID, assigned based on the return results of the Workspace service query data source (data.huaweicloud\_workspace\_service)
- **subnet\_id**: Subnet ID, assigned based on the return results of the Workspace service query data source (data.huaweicloud\_workspace\_service)
- **system\_disk\_type**: System disk type, assigned by referencing the input variable app\_server\_group\_system\_disk\_type, default is "SAS"
- **system\_disk\_size**: System disk size, assigned by referencing the input variable app\_server\_group\_system\_disk\_size, default is 80GB
- **is\_vdi**: Whether it is VDI mode, fixed as true

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Cloud application server group basic information
app_server_group_name             = "tf_test_server_group"
app_server_group_app_type         = "SESSION_DESKTOP_APP"
app_server_group_os_type          = "Windows"
app_server_group_flavor_id        = "workspace.appstream.general.xlarge.4"
app_server_group_image_id         = "2ac7b1fb-b198-422b-a45f-61ea285cb6e7"
app_server_group_image_product_id = "OFFI886188719633408000"
app_server_group_system_disk_type = "SAS"
app_server_group_system_disk_size = 80
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="app_server_group_name=my-server-group" -var="app_server_group_flavor_id=workspace.appstream.general.xlarge.4"`
2. Environment variables: `export TF_VAR_app_server_group_name=my-server-group`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating cloud application server groups
4. Run `terraform show` to view the created cloud application server group

## Reference Information

- [Huawei Cloud Workspace Product Documentation](https://support.huaweicloud.com/workspace/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Workspace Cloud Application Server Group](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/workspace/app/server_group)

# Deploy Pay-per-Use Cloud Desktop

## Application Scenario

Huawei Cloud Cloud Desktop (Workspace) is a cloud computing-based desktop virtualization service that provides enterprise users with secure and convenient cloud office solutions. Cloud desktop provides remote desktop access capabilities, allowing users to access their cloud office environment anytime, anywhere through various terminal devices, while centrally managing data and applications to improve security and work efficiency. The pay-per-use billing mode allows enterprises to pay flexibly based on actual usage without prepaying large amounts of funds, suitable for temporary projects or scenarios with fluctuating usage. This best practice will introduce how to use Terraform to automatically deploy pay-per-use cloud desktop instances.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zone List Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [Cloud Desktop Flavor List Query Data Source (data.huaweicloud\_workspace\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/workspace_flavors)
- [IMS Image List Query Data Source (data.huaweicloud\_images\_images)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_images)
- [Cloud Desktop Service Query Data Source (data.huaweicloud\_workspace\_service)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/workspace_service)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Cloud Desktop Service Resource (huaweicloud\_workspace\_service)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/workspace_service)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [Security Group Rule Resource (huaweicloud\_networking\_secgroup\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup_rule)
- [Cloud Desktop User Resource (huaweicloud\_workspace\_user)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/workspace_user)
- [Cloud Desktop Instance Resource (huaweicloud\_workspace\_desktop)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/workspace_desktop)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── data.huaweicloud_workspace_flavors
        └── huaweicloud_workspace_desktop

data.huaweicloud_images_images
    └── huaweicloud_workspace_desktop

data.huaweicloud_workspace_service
    ├── huaweicloud_vpc
    ├── huaweicloud_vpc_subnet
    ├── huaweicloud_workspace_service
    ├── huaweicloud_networking_secgroup
    ├── huaweicloud_networking_secgroup_rule
    └── huaweicloud_workspace_desktop

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_workspace_service

huaweicloud_networking_secgroup
    ├── huaweicloud_networking_secgroup_rule
    └── huaweicloud_workspace_desktop

huaweicloud_workspace_service
    └── huaweicloud_workspace_desktop

huaweicloud_workspace_user
    └── huaweicloud_workspace_desktop
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Availability Zones Required for Cloud Desktop Instance Resource Creation Through Data Source (data.huaweicloud\_availability\_zones)

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the results of which are used to create cloud desktop instances:

```hcl
variable "availability_zone" {
  description = "The availability zone to which the cloud desktop flavor and network belong"
  type        = string
  default     = ""
}

# Get all availability zone information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create cloud desktop instances
data "huaweicloud_availability_zones" "test" {
  count = var.availability_zone == "" ? 1 : 0
}
```

**Parameter Description**:

- **count**: Creation count of the data source, used to control whether to execute the availability zone list query data source, only creates the data source when `var.availability_zone` is empty (i.e., executes availability zone list query)

### 3. Query Cloud Desktop Flavors Required for Cloud Desktop Instance Resource Creation Through Data Source (data.huaweicloud\_workspace\_flavors)

Add the following script to the TF file to instruct Terraform to query cloud desktop flavors that meet the conditions:

```hcl
variable "desktop_flavor_id" {
  description = "The flavor ID of the cloud desktop"
  type        = string
  default     = ""
}

variable "desktop_flavor_os_type" {
  description = "The OS type of the cloud desktop flavor"
  type        = string
  default     = "Windows"
}

variable "desktop_flavor_cpu_core_number" {
  description = "The number of the cloud desktop flavor CPU cores"
  type        = number
  default     = 4
}

variable "desktop_flavor_memory_size" {
  description = "The number of the cloud desktop flavor memories"
  type        = number
  default     = 8
}

# Get all cloud desktop flavor information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block) that meets specific conditions, used to create cloud desktop instances
data "huaweicloud_workspace_flavors" "test" {
  count = var.desktop_flavor_id == "" ? 1 : 0

  os_type           = var.desktop_flavor_os_type
  vcpus             = var.desktop_flavor_cpu_core_number
  memory            = var.desktop_flavor_memory_size
  availability_zone = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test[0].names[0], null) : var.availability_zone
}
```

**Parameter Description**:

- **count**: Creation count of the data source, used to control whether to execute the cloud desktop flavor list query data source, only creates the data source when `var.desktop_flavor_id` is empty (i.e., executes cloud desktop flavor list query)
- **os\_type**: Operating system type, optional values: Windows, Linux
- **vcpus**: CPU core count, used to filter flavors
- **memory**: Memory size (GB), used to filter flavors
- **availability\_zone**: Availability zone where the flavor is located, prioritizes using the availability zone specified in input variables, uses the first availability zone from data source query if not specified

### 4. Query Cloud Desktop Images Required for Cloud Desktop Instance Resource Creation Through Data Source (data.huaweicloud\_images\_images)

Add the following script to the TF file to instruct Terraform to query cloud desktop images that meet the conditions:

```hcl
variable "desktop_image_id" {
  description = "The specified image ID that the cloud desktop used"
  type        = string
  default     = ""
}

variable "desktop_image_os_type" {
  description = "The OS type of the cloud desktop image"
  type        = string
  default     = "Windows"
}

variable "desktop_image_visibility" {
  description = "The visibility of the cloud desktop image"
  type        = string
  default     = "market"
}

# Get all cloud desktop image information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block) that meets specific conditions, used to create cloud desktop instances
data "huaweicloud_images_images" "test" {
  count = var.desktop_image_id == "" ? 1 : 0

  name_regex = "WORKSPACE"
  os         = var.desktop_image_os_type
  visibility = var.desktop_image_visibility
}
```

**Parameter Description**:

- **count**: Creation count of the data source, used to control whether to execute the image list query data source, only creates the data source when `var.desktop_image_id` is empty (i.e., executes image list query)
- **name\_regex**: Regular expression for image names, used to filter cloud desktop related images
- **os**: Operating system type, used to filter images
- **visibility**: Image visibility, market indicates cloud market images

### 5. Query Cloud Desktop Service Status Through Data Source (data.huaweicloud\_workspace\_service)

Add the following script to the TF file to instruct Terraform to query the current cloud desktop service status:

```hcl
# Get cloud desktop service status information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to determine whether to create related network resources
data "huaweicloud_workspace_service" "test" {}
```

**Parameter Description**: This data source is used to query the current cloud desktop service status. If the service status is "CLOSED", VPC, subnet, security group, and other network resources need to be created; if the service is already enabled, existing network resources can be reused.

### 6. Create VPC Resource (huaweicloud\_vpc)

Add the following script to the TF file to instruct Terraform to conditionally create VPC resources based on cloud desktop service status:

```hcl
variable "vpc_name" {
  description = "The VPC name"
  type        = string
}

variable "vpc_cidr" {
  description = "The CIDR block of the VPC"
  type        = string
}

# Create a VPC resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block) conditionally based on cloud desktop service status, used to deploy cloud desktop instances
resource "huaweicloud_vpc" "test" {
  count = data.huaweicloud_workspace_service.test.status == "CLOSED" ? 1 : 0

  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **count**: Creation count of the resource, only creates VPC resource when cloud desktop service status is "CLOSED"
- **name**: VPC name, assigned by referencing the input variable vpc\_name
- **cidr**: VPC CIDR block, assigned by referencing the input variable vpc\_cidr

### 7. Create VPC Subnet Resource (huaweicloud\_vpc\_subnet)

Add the following script to the TF file to instruct Terraform to conditionally create VPC subnet resources based on cloud desktop service status:

```hcl
variable "subnet_name" {
  description = "The subnet name"
  type        = string
}

variable "subnet_cidr" {
  description = "The CIDR block of the subnet"
  type        = string
  default     = ""
}

variable "subnet_gateway_ip" {
  description = "The gateway IP of the subnet"
  type        = string
  default     = ""
}

# Create a VPC subnet resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block) conditionally based on cloud desktop service status, used to deploy cloud desktop instances
resource "huaweicloud_vpc_subnet" "test" {
  count = data.huaweicloud_workspace_service.test.status == "CLOSED" ? 1 : 0

  vpc_id     = try(huaweicloud_vpc.test[0].id, null)
  name       = var.subnet_name
  cidr       = var.subnet_cidr == "" ? cidrsubnet(try(huaweicloud_vpc.test[0].cidr, "192.168.0.0/16"), 8, 0) : var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(try(huaweicloud_vpc.test[0].cidr, "192.168.0.0/16"), 8, 0), 1) : var.subnet_gateway_ip
}
```

**Parameter Description**:

- **count**: Creation count of the resource, only creates subnet resource when cloud desktop service status is "CLOSED"
- **vpc\_id**: VPC ID that the subnet belongs to, referencing the ID of the previously created VPC resource
- **name**: Subnet name, assigned by referencing the input variable subnet\_name
- **cidr**: Subnet CIDR block, uses cidrsubnet function to divide a subnet segment from VPC's CIDR block if not specified
- **gateway\_ip**: Subnet gateway IP, uses cidrhost function to get the first IP address from subnet segment as gateway IP if not specified

### 8. Create Cloud Desktop Service (huaweicloud\_workspace\_service)

Add the following script to the TF file to instruct Terraform to conditionally create cloud desktop service resources based on cloud desktop service status:

```hcl
# Create a cloud desktop service resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block) conditionally based on cloud desktop service status, used to deploy cloud desktop instances
resource "huaweicloud_workspace_service" "test" {
  count = data.huaweicloud_workspace_service.test.status == "CLOSED" ? 1 : 0

  access_mode = "INTERNET"
  vpc_id      = try(huaweicloud_vpc.test[0].id, null)
  network_ids = [
    try(huaweicloud_vpc_subnet.test[0].id, null),
  ]
}
```

**Parameter Description**:

- **count**: Creation count of the resource, only creates cloud desktop service resource when cloud desktop service status is "CLOSED"
- **access\_mode**: Access mode, using INTERNET indicates access through public network
- **vpc\_id**: VPC ID, referencing the ID of the previously created VPC resource
- **network\_ids**: Network ID list, referencing the ID of the previously created subnet resource

### 9. Create Security Group Resource (huaweicloud\_networking\_secgroup)

Add the following script to the TF file to instruct Terraform to conditionally create security group resources based on cloud desktop service status:

```hcl
variable "security_group_name" {
  description = "The security group name"
  type        = string
}

# Create a security group resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block) conditionally based on cloud desktop service status, used to deploy cloud desktop instances
resource "huaweicloud_networking_secgroup" "test" {
  count = data.huaweicloud_workspace_service.test.status == "CLOSED" ? 1 : 0

  name                 = var.security_group_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **count**: Creation count of the resource, only creates security group resource when cloud desktop service status is "CLOSED"
- **name**: Security group name, assigned by referencing the input variable security\_group\_name
- **delete\_default\_rules**: Whether to delete default rules, set to true to delete default rules

### 10. Create Security Group Rule Resource (huaweicloud\_networking\_secgroup\_rule)

Add the following script to the TF file to instruct Terraform to conditionally create security group rule resources based on cloud desktop service status:

```hcl
# Create a security group rule resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block) conditionally based on cloud desktop service status, used to deploy cloud desktop instances
resource "huaweicloud_networking_secgroup_rule" "test" {
  count = data.huaweicloud_workspace_service.test.status == "CLOSED" ? 1 : 0

  security_group_id = try(huaweicloud_networking_secgroup.test[0].id, null)
  direction         = "egress"
  ethertype         = "IPv4"
  remote_ip_prefix  = "0.0.0.0/0"
  priority          = 1
}
```

**Parameter Description**:

- **count**: Creation count of the resource, only creates security group rule resource when cloud desktop service status is "CLOSED"
- **security\_group\_id**: Security group ID, referencing the ID of the previously created security group resource
- **direction**: Rule direction, egress indicates outbound traffic
- **ethertype**: IP protocol version, IPv4 indicates IPv4 protocol
- **remote\_ip\_prefix**: Remote IP address, 0.0.0.0/0 indicates allowing all IP addresses
- **priority**: Rule priority, smaller values have higher priority

### 11. Create Cloud Desktop User (huaweicloud\_workspace\_user)

Add the following script to the TF file to instruct Terraform to create a cloud desktop user resource:

```hcl
variable "desktop_user_name" {
  description = "The user name that the cloud desktop used"
  type        = string
}

variable "desktop_user_email" {
  description = "The email address that the user used"
  type        = string
}

# Create a cloud desktop user resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to deploy cloud desktop instances
resource "huaweicloud_workspace_user" "test" {
  depends_on = [huaweicloud_workspace_service.test]

  name  = var.desktop_user_name
  email = var.desktop_user_email

  account_expires            = "0"
  password_never_expires     = false
  enable_change_password     = true
  next_login_change_password = true
  disabled                   = false
}
```

**Parameter Description**:

- **name**: Username, assigned by referencing the input variable desktop\_user\_name
- **email**: User email, assigned by referencing the input variable desktop\_user\_email
- **account\_expires**: Account expiration time, set to "0" indicates never expires
- **password\_never\_expires**: Whether password never expires, set to false indicates password has expiration time
- **enable\_change\_password**: Whether to allow password change, set to true indicates allowing password change
- **next\_login\_change\_password**: Whether to change password on next login, set to true indicates password change required on next login
- **disabled**: Whether to disable user, set to false indicates user is not disabled

### 12. Create Cloud Desktop Instance (huaweicloud\_workspace\_desktop)

Add the following script to the TF file to instruct Terraform to create a cloud desktop instance resource:

```hcl
variable "cloud_desktop_name" {
  description = "The cloud desktop name"
  type        = string
}

variable "desktop_user_group_name" {
  description = "The name of the user group that cloud desktop used"
  type        = string
  default     = "users"
}

variable "desktop_root_volume_type" {
  description = "The storage type of system disk"
  type        = string
  default     = "SSD"
}

variable "desktop_root_volume_size" {
  description = "The storage capacity of system disk"
  type        = number
  default     = 100
}

variable "desktop_data_volumes" {
  description = "The storage configuration of data disks"
  type = list(object({
    type = string
    size = number
  }))
  default = [
    {
      type = "SSD",
      size = 100,
    },
  ]
}

# Create a cloud desktop instance resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_workspace_desktop" "test" {
  depends_on = [huaweicloud_workspace_user.test]

  flavor_id         = var.desktop_flavor_id == "" ? try([for o in data.huaweicloud_workspace_flavors.test[0].flavors: o.id if !strcontains(lower(o.description), "flexus")][0], null) : var.desktop_flavor_id
  image_type        = var.desktop_image_visibility
  image_id          = var.desktop_image_id == "" ? try(data.huaweicloud_images_images.test[0].images[0].id, null) : var.desktop_image_id
  availability_zone = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test[0].names[0], null) : var.availability_zone
  vpc_id            = data.huaweicloud_workspace_service.test.status != "CLOSED" ? data.huaweicloud_workspace_service.test.vpc_id : try(huaweicloud_vpc.test[0].id, null)
  security_groups   = data.huaweicloud_workspace_service.test.status != "CLOSED" ? concat(
    data.huaweicloud_workspace_service.test.desktop_security_group[*].id,
    data.huaweicloud_workspace_service.test.infrastructure_security_group[*].id,
    try(huaweicloud_networking_secgroup.test[0].id, []),
  ) : concat(
    try(huaweicloud_workspace_service.test[0].desktop_security_group[*].id, []),
    try(huaweicloud_workspace_service.test[0].infrastructure_security_group[*].id, []),
    try(huaweicloud_networking_secgroup.test[0].id, []),
  )

  dynamic "nic" {
    for_each = data.huaweicloud_workspace_service.test.status != "CLOSED" ? data.huaweicloud_workspace_service.test.network_ids : try([huaweicloud_vpc_subnet.test[0].id], [])

    content {
      network_id = nic.value
    }
  }

  name       = var.cloud_desktop_name
  user_name  = huaweicloud_workspace_user.test.name
  user_email = huaweicloud_workspace_user.test.email
  user_group = var.desktop_user_group_name

  root_volume {
    type = var.desktop_root_volume_type
    size = var.desktop_root_volume_size
  }

  dynamic "data_volume" {
    for_each = var.desktop_data_volumes

    content {
      type = data_volume.value["type"]
      size = data_volume.value["size"]
    }
  }

  lifecycle {
    ignore_changes = [
      flavor_id,
      image_id,
      availability_zone,
    ]
  }
}
```

**Parameter Description**:

- **flavor\_id**: Cloud desktop flavor ID, prioritizes using the flavor specified in input variables, uses the first non-flexus flavor from data source query if not specified
- **image\_type**: Image type, assigned by referencing the input variable desktop\_image\_visibility
- **image\_id**: Image ID, prioritizes using the image specified in input variables, uses the first image from data source query if not specified
- **availability\_zone**: Availability zone, prioritizes using the availability zone specified in input variables, uses the first availability zone from data source query if not specified
- **vpc\_id**: VPC ID, uses existing VPC or newly created VPC based on cloud desktop service status
- **security\_groups**: Security group ID list, uses different security group configurations based on cloud desktop service status
- **nic**: Network interface configuration block (dynamic block), uses different network configurations based on cloud desktop service status
  - **network\_id**: Unique identifier of the network, uses existing network or newly created subnet based on service status
- **name**: Cloud desktop name, assigned by referencing the input variable cloud\_desktop\_name
- **user\_name**: Username, referencing the name of the previously created cloud desktop user resource
- **user\_email**: User email, referencing the email of the previously created cloud desktop user resource
- **user\_group**: User group name, assigned by referencing the input variable desktop\_user\_group\_name, default is "users"
- **root\_volume**: System disk configuration block
  - **type**: Disk type, assigned by referencing the input variable desktop\_root\_volume\_type, default is SSD
  - **size**: Disk size, assigned by referencing the input variable desktop\_root\_volume\_size, default is 100GB
- **data\_volume**: Data disk configuration block (dynamic block)
  - **type**: Disk type, assigned by referencing the type value in the input variable desktop\_data\_volumes
  - **size**: Disk size, assigned by referencing the size value in the input variable desktop\_data\_volumes
- **lifecycle**: Lifecycle management, ignores changes to flavor, image, and availability zone to avoid instance recreation

### 13. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following content:

```hcl
vpc_name            = "tf_test_vpc"
vpc_cidr            = "192.168.0.0/16"
subnet_name         = "tf_test_subnet"
security_group_name = "tf_test_security_group"
desktop_user_name   = "tf_test_user"
desktop_user_email  = "test@example.com"
cloud_desktop_name  = "tf-test-desktop"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

> For variables not specified in the `terraform.tfvars` file, Terraform will use the default values defined in the code or prompt the user for input during execution.

### 14. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating cloud desktop instances
4. Run `terraform show` to view the created cloud desktop instance details

## Reference Information

- [Huawei Cloud Workspace Product Documentation](https://support.huaweicloud.com/workspace/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Workspace Cloud Desktop Best Practice Source Code Reference](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/workspace/desktop)
