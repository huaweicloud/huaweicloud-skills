# Deploy Alarm Template

## Application Scenario

Cloud Eye Service (CES) alarm template is an alarm rule template function provided by the CES service, used to quickly create and manage alarm rules. By configuring alarm templates, you can define unified alarm policies, including monitoring metrics, alarm thresholds, alarm levels, etc., and then quickly create multiple alarm rules based on templates, improving the efficiency and consistency of alarm configuration. Automating CES alarm template creation through Terraform can ensure standardized and standardized alarm configuration, simplifying operational management. This best practice will introduce how to use Terraform to automatically create CES alarm templates.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [CES Alarm Template Resource (huaweicloud\_ces\_alarm\_template)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/ces_alarm_template)

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create CES Alarm Template Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a CES alarm template resource:

```hcl
variable "alarm_template_name" {
  description = "The name of the alarm template"
  type        = string
}

variable "alarm_template_description" {
  description = "The description of the alarm template"
  type        = string
  default     = ""
}

variable "alarm_template_policies" {
  description = "The policy list of the CES alarm template"
  type = list(object({
    namespace           = string
    metric_name         = string
    period              = number
    filter              = string
    comparison_operator = string
    count               = number
    suppress_duration   = number
    value               = number
    alarm_level         = number
    unit                = string
    dimension_name      = string
    hierarchical_value = list(object({
      critical = number
      major    = number
      minor    = number
      info     = number
    }))
  }))
  default = []
}

# Create CES alarm template resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_ces_alarm_template" "test" {
  name        = var.alarm_template_name
  description = var.alarm_template_description

  dynamic "policies" {
    for_each = var.alarm_template_policies

    content {
      namespace           = policies.value.namespace
      metric_name         = policies.value.metric_name
      period              = policies.value.period
      filter              = policies.value.filter
      comparison_operator = policies.value.comparison_operator
      count               = policies.value.count
      suppress_duration   = policies.value.suppress_duration
      value               = policies.value.value
      alarm_level         = policies.value.alarm_level
      unit                = policies.value.unit
      dimension_name      = policies.value.dimension_name
      hierarchical_value {
        critical = policies.value.hierarchical_value[0].critical
        major    = policies.value.hierarchical_value[0].major
        minor    = policies.value.hierarchical_value[0].minor
        info     = policies.value.hierarchical_value[0].info
      }
    }
  }
}
```

**Parameter Description**:

- **name**: The alarm template name, assigned by referencing the input variable alarm\_template\_name
- **description**: The alarm template description, assigned by referencing the input variable alarm\_template\_description, optional parameter, default value is empty string
- **policies**: The alarm policy list, assigned by referencing the input variable alarm\_template\_policies, each policy contains the following parameters:
  - **namespace**: Service namespace, such as SYS.APIG, SYS.ECS, etc.
  - **metric\_name**: Alarm metric name
  - **period**: Alarm condition judgment period, unit is minutes
  - **filter**: Data aggregation method, such as average (average value), max (maximum value), min (minimum value), etc.
  - **comparison\_operator**: Comparison condition for alarm threshold, such as >, >=, <, <=, =, etc.
  - **count**: Number of consecutive alarm triggering times
  - **suppress\_duration**: Alarm suppression cycle, unit is seconds
  - **value**: Alarm threshold
  - **alarm\_level**: Alarm level, 1-4 represent critical, major, minor, info respectively
  - **unit**: Unit string of alarm threshold
  - **dimension\_name**: Resource dimension name
  - **hierarchical\_value**: Multi-level alarm threshold configuration, contains the following fields:
    - **critical**: Threshold for critical level
    - **major**: Threshold for major level
    - **minor**: Threshold for minor level
    - **info**: Threshold for info level

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Alarm Template Configuration
alarm_template_name        = "tf_test_alarm_template"
alarm_template_description = "Test alarm template for APIG service"

# Alarm Policy Configuration
alarm_template_policies = [
  {
    namespace           = "SYS.APIG"
    dimension_name      = "api_id"
    metric_name         = "req_count_2xx"
    period              = 1
    filter              = "average"
    comparison_operator = ">"
    value               = 10
    unit                = "times/minute"
    count               = 3
    alarm_level         = 2
    suppress_duration   = 300
    hierarchical_value = [
      {
        critical = 12
        major    = 10
        minor    = 8
        info     = 4
      }
    ]
  }
]
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="alarm_template_name=my_template" -var="alarm_template_description=My description"`
2. Environment variables: `export TF_VAR_alarm_template_name=my_template` and `export TF_VAR_alarm_template_description=My description`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create a CES alarm template:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the alarm template
4. Run `terraform show` to view the details of the created alarm template

> Note: After the alarm template is created, multiple alarm rules can be quickly created based on this template. The hierarchical\_value in the alarm policy is used to configure multi-level alarm thresholds, and different thresholds can be set according to different alarm levels. Alarm levels 1-4 represent critical, major, minor, and info respectively, and you can choose the appropriate alarm level according to business needs.

## Reference Information

- [Huawei Cloud CES Product Documentation](https://support.huaweicloud.com/ces/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Alarm Template](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/ces/alarm-template)

# Deploy Dashboard

## Application Scenario

Cloud Eye Service (CES) dashboard is a monitoring data visualization function provided by the CES service, used to centrally display multiple monitoring metrics and resource status. By configuring dashboards, you can create custom monitoring views, centrally display multiple monitoring metrics in the form of charts, tables, etc., making it convenient for operation personnel to quickly understand the overall running status of cloud resources. Automating CES dashboard creation through Terraform can ensure standardized and consistent monitoring view configuration, improving operational efficiency. This best practice will introduce how to use Terraform to automatically create CES dashboards.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [CES Dashboard Resource (huaweicloud\_ces\_dashboard)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/ces_dashboard)

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create CES Dashboard Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a CES dashboard resource:

```hcl
variable "dashboard_name" {
  description = "The name of the alarm dashboard"
  type        = string
}

variable "dashboard_row_widget_num" {
  description = "The monitoring view display mode"
  type        = number
}

variable "dashboard_extend_info" {
  description = "The information about the extension"
  type = list(object({
    filter                  = string
    period                  = string
    display_time            = number
    refresh_time            = number
    from                    = number
    to                      = number
    screen_color            = string
    enable_screen_auto_play = bool
    time_interval           = number
    enable_legend           = bool
    full_screen_widget_num  = number
  }))
  default = []
}

variable "dashboard_id" {
  description = "The copied dashboard ID"
  type        = string
  default     = null
}

variable "enterprise_project_id" {
  description = "The enterprise project ID of the dashboard"
  type        = string
  default     = null
}

variable "is_favorite" {
  description = "Whether the dashboard is favorite"
  type        = bool
  default     = false
}

# Create CES dashboard resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_ces_dashboard" "test" {
  name           = var.dashboard_name
  row_widget_num = var.dashboard_row_widget_num

  dynamic "extend_info" {
    for_each = length(var.dashboard_extend_info) > 0 ? var.dashboard_extend_info : []

    content {
      filter                  = extend_info.value.filter
      period                  = extend_info.value.period
      display_time            = extend_info.value.display_time
      refresh_time            = extend_info.value.refresh_time
      from                    = extend_info.value.from
      to                      = extend_info.value.to
      screen_color            = extend_info.value.screen_color
      enable_screen_auto_play = extend_info.value.enable_screen_auto_play
      time_interval           = extend_info.value.time_interval
      enable_legend           = extend_info.value.enable_legend
      full_screen_widget_num  = extend_info.value.full_screen_widget_num
    }
  }

  dashboard_id         = var.dashboard_id
  enterprise_project_id = var.enterprise_project_id
  is_favorite         = var.is_favorite
}
```

**Parameter Description**:

- **name**: The dashboard name, assigned by referencing the input variable dashboard\_name
- **row\_widget\_num**: The monitoring view display mode, assigned by referencing the input variable dashboard\_row\_widget\_num
- **extend\_info**: The extension information list, assigned by referencing the input variable dashboard\_extend\_info, optional parameter, default value is empty list, each extension information contains the following parameters:
  - **filter**: Metric aggregation method
  - **period**: Metric aggregation period
  - **display\_time**: Display time
  - **refresh\_time**: Refresh time
  - **from**: Start time
  - **to**: End time
  - **screen\_color**: Monitoring screen background color
  - **enable\_screen\_auto\_play**: Whether to enable monitoring screen automatic switching
  - **time\_interval**: Monitoring screen automatic switching time interval
  - **enable\_legend**: Whether to enable legend
  - **full\_screen\_widget\_num**: Number of large screen display views
- **dashboard\_id**: The copied dashboard ID, assigned by referencing the input variable dashboard\_id, optional parameter, default value is null
- **enterprise\_project\_id**: The enterprise project ID of the dashboard, assigned by referencing the input variable enterprise\_project\_id, optional parameter, default value is null
- **is\_favorite**: Whether the dashboard is favorite, assigned by referencing the input variable is\_favorite, optional parameter, default value is false

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Dashboard Configuration
dashboard_name        = "tf_test_ces_dashboard"
dashboard_row_widget_num = 2

# Extension Information Configuration
dashboard_extend_info = [
  {
    filter                  = "average"
    period                  = "1"
    display_time            = 3600
    refresh_time            = 60
    from                    = 0
    to                      = 3600
    screen_color            = "#000000"
    enable_screen_auto_play = true
    time_interval           = 30
    enable_legend           = true
    full_screen_widget_num   = 4
  }
]

# Optional Configuration
# dashboard_id         = "existing_dashboard_id"
# enterprise_project_id = "enterprise_project_id"
# is_favorite          = true
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="dashboard_name=my_dashboard" -var="dashboard_row_widget_num=2"`
2. Environment variables: `export TF_VAR_dashboard_name=my_dashboard` and `export TF_VAR_dashboard_row_widget_num=2`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create a CES dashboard:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the dashboard
4. Run `terraform show` to view the details of the created dashboard

> Note: After the dashboard is created, you can further configure it in the CES console, adding monitoring metrics and charts. By setting extend\_info, you can configure the display parameters of the monitoring screen, including automatic switching, refresh time, etc. The dashboard supports favorite function, making it convenient to quickly access commonly used monitoring views.

## Reference Information

- [Huawei Cloud CES Product Documentation](https://support.huaweicloud.com/ces/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Dashboard](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/ces/dashboard)

# Deploy Resource Group

## Application Scenario

Cloud Eye Service (CES) resource group is a resource grouping management function provided by the CES service, used to group multiple cloud resources according to business needs. By configuring resource groups, you can organize related cloud resources (such as ECS instances, RDS instances, etc.) together for unified monitoring, alarm and operation management, improving the efficiency and convenience of resource management. Automating CES resource group creation through Terraform can ensure standardized and consistent resource grouping configuration, simplifying operational management. This best practice will introduce how to use Terraform to automatically create CES resource groups.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Data Sources

- [Availability Zones Data Source (huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [ECS Flavors Data Source (huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [ECS Instance Resource (huaweicloud\_compute\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_instance)
- [CES Resource Group Resource (huaweicloud\_ces\_resource\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/ces_resource_group)

## Resource Dependencies

In this best practice, the following dependencies exist between resources:

1. **CES Resource Group** depends on cloud resources such as **ECS Instance**, which need to be created first before they can be added to the resource group
2. **ECS Instance** depends on **VPC Subnet** and **Security Group**, which need to be created first
3. **VPC Subnet** depends on **VPC**, which needs to be created first
4. **ECS Instance** depends on **Availability Zones Data Source** and **ECS Flavors Data Source** to obtain availability zone and flavor information

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Data Sources

Add the following script to the TF file (e.g., main.tf) to query availability zone and ECS flavor information:

```hcl
# Query availability zone information
data "huaweicloud_availability_zones" "test" {}

# Query ECS flavor information
data "huaweicloud_compute_flavors" "test" {
  availability_zone = try(data.huaweicloud_availability_zones.test.names[0], null)
  performance_type  = var.ecs_flavor_performance_type
  cpu_core_count    = var.ecs_flavor_cpu_core_count
  memory_size       = var.ecs_flavor_memory_size
}
```

**Parameter Description**:

- **availability\_zone**: Availability zone name, obtained by referencing the availability zones data source
- **performance\_type**: ECS flavor performance type, assigned by referencing the input variable ecs\_flavor\_performance\_type, default value is "normal"
- **cpu\_core\_count**: ECS flavor CPU core count, assigned by referencing the input variable ecs\_flavor\_cpu\_core\_count, default value is 2
- **memory\_size**: ECS flavor memory size, assigned by referencing the input variable ecs\_flavor\_memory\_size, default value is 4

### 3. Create Basic Resources

Add the following script to the TF file (e.g., main.tf) to create VPC, subnet, security group and ECS instance:

```hcl
variable "vpc_name" {
  description = "The name of the VPC"
  type        = string
}

variable "vpc_cidr" {
  description = "The CIDR block of the VPC"
  type        = string
  default     = "192.168.0.0/16"
}

variable "subnet_name" {
  description = "The name of the subnet"
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

variable "security_group_name" {
  description = "The security group name"
  type        = string
  default     = "sg-dnat-backend"
}

variable "ecs_instance_name" {
  description = "The name of the ECS instance"
  type        = string
  default     = ""
}

variable "ecs_image_id" {
  description = "The ID of the ECS image"
  type        = string
  default     = ""
}

variable "ecs_flavor_performance_type" {
  description = "The performance type of the ECS instance flavor"
  type        = string
  default     = "normal"
}

variable "ecs_flavor_cpu_core_count" {
  description = "The CPU core count of the ECS instance flavor"
  type        = number
  default     = 2
}

variable "ecs_flavor_memory_size" {
  description = "The memory size of the ECS instance flavor"
  type        = number
  default     = 4
}

# Create VPC
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}

# Create subnet
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
}

# Create security group
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}

# Create ECS instance
resource "huaweicloud_compute_instance" "test" {
  name               = var.ecs_instance_name
  image_id           = var.ecs_image_id
  flavor_id          = try(data.huaweicloud_compute_flavors.test.ids[0], null)
  security_group_ids = [huaweicloud_networking_secgroup.test.id]
  availability_zone  = try(data.huaweicloud_availability_zones.test.names[0], null)

  network {
    uuid = huaweicloud_vpc_subnet.test.id
  }
}
```

### 4. Create CES Resource Group Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a CES resource group resource:

```hcl
variable "resource_group_name" {
  description = "The name of the resource group"
  type        = string
}

variable "resource_group_resources" {
  description = "The resource list of the CES resource group"
  type = list(object({
    namespace  = string
    dimensions = list(object({
      name  = string
      value = string
    }))
  }))
  default = []
}

# Create CES resource group resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_ces_resource_group" "test" {
  name = var.resource_group_name

  dynamic "resources" {
    for_each = var.resource_group_resources

    content {
      namespace = resources.value.namespace
      dimensions {
        name  = resources.value.dimensions[0].name
        value = resources.value.dimensions[0].value
      }
    }
  }
}
```

**Parameter Description**:

- **name**: The resource group name, assigned by referencing the input variable resource\_group\_name
- **resources**: The resource list, assigned by referencing the input variable resource\_group\_resources, optional parameter, default value is empty list, each resource contains the following parameters:
  - **namespace**: Service namespace, such as SYS.ECS, SYS.RDS, etc.
  - **dimensions**: Resource dimension list, each dimension contains the following fields:
    - **name**: Dimension name, such as instance\_id, rds\_instance\_id, etc.
    - **value**: Dimension value, such as ECS instance ID, RDS instance ID, etc.

### 5. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# VPC and Subnet Configuration
vpc_name    = "tf_test_ces_resource_group"
vpc_cidr    = "192.168.0.0/16"
subnet_name = "tf_test_ces_resource_group"

# Security Group Configuration
security_group_name = "tf_test_ces_resource_group"

# ECS Instance Configuration
ecs_instance_name = "tf_test_ces_resource_group"
ecs_image_id      = "your_image_id"

# Resource Group Configuration
resource_group_name = "tf_test_ces_resource_group"

# Resource Group Resources Configuration (Example: Add ECS instance to resource group)
resource_group_resources = [
  {
    namespace = "SYS.ECS"
    dimensions = [
      {
        name  = "instance_id"
        value = huaweicloud_compute_instance.test.id
      }
    ]
  }
]
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially `ecs_image_id` needs to be replaced with the actual image ID
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="resource_group_name=my_group" -var="vpc_name=my_vpc"`
2. Environment variables: `export TF_VAR_resource_group_name=my_group` and `export TF_VAR_vpc_name=my_vpc`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 6. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create a CES resource group:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the resource group and related resources
4. Run `terraform show` to view the details of the created resource group

> Note: After the resource group is created, multiple cloud resources can be added to the resource group for unified management. Resource groups support resource filtering by namespace and dimensions, allowing flexible organization and management of cloud resources. After the resource group is created, you can further configure it in the CES console, such as creating alarm rules, viewing monitoring data, etc.

## Reference Information

- [Huawei Cloud CES Product Documentation](https://support.huaweicloud.com/ces/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Resource Group](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/ces/resource-group)
