# Deploy Script

## Application Scenario

Cloud Operations Center (COC) is a one-stop operation and maintenance management platform provided by Huawei Cloud, offering enterprises a unified operation and maintenance management entry point. COC helps enterprises achieve automated operation and maintenance and intelligent management through script management, task scheduling, monitoring and alerting, improving operation and maintenance efficiency and quality.

Script management is one of the core functions of COC service, supporting the creation, management, and execution of various operation and maintenance scripts, including Shell scripts, Python scripts, PowerShell scripts, etc. Through script management, you can achieve version control, parameter management, risk level assessment, and other functions for operation and maintenance scripts, laying the foundation for subsequent script execution and task scheduling. This best practice will introduce how to use Terraform to automatically deploy COC scripts, including script creation and parameter configuration.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

None

### Resources

- [COC Script Resource (huaweicloud\_coc\_script)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/coc_script)

### Resource/Data Source Dependencies

```
huaweicloud_coc_script.test
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create COC Script

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a COC script resource:

```hcl
variable "script_name" {
  description = "Script name"
  type        = string
}

variable "script_description" {
  description = "Script description"
  type        = string
}

variable "script_risk_level" {
  description = "Script risk level"
  type        = string
}

variable "script_version" {
  description = "Script version"
  type        = string
}

variable "script_type" {
  description = "Script type"
  type        = string
}

variable "script_content" {
  description = "Script content"
  type        = string
}

variable "script_parameters" {
  description = "Script parameter list"
  type = list(object({
    name        = string
    value       = string
    description = string
    sensitive   = optional(bool)
  }))

  nullable = false
}

# Create a COC script resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_coc_script" "test" {
  name        = var.script_name
  description = var.script_description
  risk_level  = var.script_risk_level
  version     = var.script_version
  type        = var.script_type
  content     = var.script_content

  dynamic "parameters" {
    for_each = var.script_parameters

    content {
      name        = parameters.value.name
      value       = parameters.value.value
      description = parameters.value.description
      sensitive   = parameters.value.sensitive
    }
  }
}
```

**Parameter Description**:

- **name**: Script name, assigned by referencing the input variable script\_name
- **description**: Script description, assigned by referencing the input variable script\_description
- **risk\_level**: Script risk level, assigned by referencing the input variable script\_risk\_level
- **version**: Script version, assigned by referencing the input variable script\_version
- **type**: Script type, assigned by referencing the input variable script\_type
- **content**: Script content, assigned by referencing the input variable script\_content
- **parameters.name**: Parameter name, assigned by referencing the name field in the script parameter list
- **parameters.value**: Parameter value, assigned by referencing the value field in the script parameter list
- **parameters.description**: Parameter description, assigned by referencing the description field in the script parameter list
- **parameters.sensitive**: Whether the parameter is sensitive, assigned by referencing the sensitive field in the script parameter list

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Script configuration
script_name        = "tf_coc_script"
script_description = "Created by terraform script"
script_risk_level  = "LOW"
script_version     = "1.0.0"
script_type        = "SHELL"
script_content     = <<EOF
#! /bin/bash
echo "hello world!"
EOF

# Script parameter configuration
script_parameters = [
  {
    name        = "name"
    value       = "world"
    description = "the first parameter"
  },
  {
    name        = "company"
    value       = "Huawei"
    description = "the second parameter"
    sensitive   = true
  }
]
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="script_name=my-script" -var="script_type=SHELL"`
2. Environment variables: `export TF_VAR_script_name=my-script`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating the COC script
4. Run `terraform show` to view the details of the created COC script

## Reference Information

- [Huawei Cloud COC Product Documentation](https://support.huaweicloud.com/coc/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For COC Script](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/coc/script)

# Deploy Script Execution

## Application Scenario

Cloud Operations Center (COC) is a one-stop operation and maintenance management platform provided by Huawei Cloud, offering enterprises a unified operation and maintenance management entry point. COC helps enterprises achieve automated operation and maintenance and intelligent management through script management, task scheduling, monitoring and alerting, improving operation and maintenance efficiency and quality.

Script execution is one of the core functions of COC service, supporting the execution of various operation and maintenance scripts on ECS instances, including Shell scripts, Python scripts, PowerShell scripts, etc. Through script execution, you can achieve automated deployment, system configuration, monitoring checks, and other operation and maintenance tasks. This best practice will introduce how to use Terraform to automatically deploy COC script execution, including the complete process of creating ECS instances, installing UniAgent, creating scripts, and executing scripts.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [ECS Flavor List Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)
- [IMS Image List Query Data Source (data.huaweicloud\_images\_images)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_images)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [ECS Instance Resource (huaweicloud\_compute\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_instance)
- [COC Script Resource (huaweicloud\_coc\_script)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/coc_script)
- [COC Script Execution Resource (huaweicloud\_coc\_script\_execute)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/coc_script_execute)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones.test
    └── huaweicloud_vpc_subnet.test
        └── huaweicloud_compute_instance.test
            └── huaweicloud_coc_script_execute.test

data.huaweicloud_compute_flavors.test
    └── huaweicloud_compute_instance.test

data.huaweicloud_images_images.test
    └── huaweicloud_compute_instance.test

huaweicloud_vpc.test
    └── huaweicloud_vpc_subnet.test

huaweicloud_networking_secgroup.test
    └── huaweicloud_compute_instance.test

huaweicloud_coc_script.test
    └── huaweicloud_coc_script_execute.test
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Availability Zones Required for ECS Instance Resource Creation via Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the result of which will be used to create the ECS instance:

```hcl
variable "availability_zone" {
  description = "Availability zone information for the ECS instance"
  type        = string
  default     = ""
}

# Get all availability zone information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create the ECS instance
data "huaweicloud_availability_zones" "test" {
  count = var.availability_zone == "" ? 1 : 0
}
```

**Parameter Description**:

- **count**: Number of data source instances, used to control whether to execute the availability zone list query data source, only creates the data source when `var.availability_zone` is empty

### 3. Query ECS Instance Flavor Information via Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the result of which will be used to create the ECS instance:

```hcl
variable "instance_flavor_id" {
  description = "ECS instance flavor ID, if not specified, will use the first available flavor that meets the criteria"
  type        = string
  default     = ""
}

variable "instance_flavor_performance_type" {
  description = "ECS instance flavor performance type, used to query available flavors when instance_flavor_id is not specified"
  type        = string
  default     = "normal"
}

variable "instance_flavor_cpu_core_count" {
  description = "ECS instance flavor CPU core count, used to query available flavors when instance_flavor_id is not specified"
  type        = number
  default     = 4
}

variable "instance_flavor_memory_size" {
  description = "ECS instance flavor memory size (GB), used to query available flavors when instance_flavor_id is not specified"
  type        = number
  default     = 8
}

# Get all ECS flavor information that meets the criteria under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create the ECS instance
data "huaweicloud_compute_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  availability_zone = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test[0].names[0], "") : var.availability_zone
  performance_type  = var.instance_flavor_performance_type
  cpu_core_count    = var.instance_flavor_cpu_core_count
  memory_size       = var.instance_flavor_memory_size
}
```

**Parameter Description**:

- **count**: Number of data source instances, used to control whether to execute the ECS flavor list query data source, only creates the data source when `var.instance_flavor_id` is empty
- **availability\_zone**: Availability zone, prioritizes input variable, uses the first result from availability zone list query data source if empty
- **performance\_type**: Performance type, used to filter ECS flavors
- **cpu\_core\_count**: CPU core count, used to filter ECS flavors
- **memory\_size**: Memory size, used to filter ECS flavors

### 4. Query ECS Instance Image Information via Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the result of which will be used to create the ECS instance:

```hcl
variable "instance_image_id" {
  description = "ECS instance image ID, if not specified, will use the first available image that meets the criteria"
  type        = string
  default     = ""
}

variable "instance_image_os_type" {
  description = "ECS instance image operating system type, used to query available images when instance_image_id is not specified"
  type        = string
  default     = "Ubuntu"
}

variable "instance_image_visibility" {
  description = "ECS instance image visibility, used to query available images when instance_image_id is not specified"
  type        = string
  default     = "public"
}

# Get all image information that meets the criteria under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create the ECS instance
data "huaweicloud_images_images" "test" {
  count = var.instance_image_id == "" ? 1 : 0

  flavor_id  = var.instance_flavor_id == "" ? try(data.huaweicloud_compute_flavors.test[0].ids[0], "") : var.instance_flavor_id
  os         = var.instance_image_os_type
  visibility = var.instance_image_visibility
}
```

**Parameter Description**:

- **count**: Number of data source instances, used to control whether to execute the image list query data source, only creates the data source when `var.instance_image_id` is empty
- **flavor\_id**: Flavor ID, prioritizes input variable, uses the first result from ECS flavor list query data source if empty
- **os**: Operating system type, used to filter images
- **visibility**: Visibility, used to filter images

### 5. Create VPC

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC resource:

```hcl
variable "vpc_name" {
  description = "VPC name"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "192.168.0.0/16"
}

# Create a VPC resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: VPC name, assigned by referencing the input variable vpc\_name
- **cidr**: VPC CIDR block, assigned by referencing the input variable vpc\_cidr

### 6. Create VPC Subnet

Add the following script to the TF file to instruct Terraform to create a VPC subnet resource:

```hcl
variable "subnet_name" {
  description = "Subnet name"
  type        = string
}

variable "subnet_cidr" {
  description = "Subnet CIDR block, if not specified, will calculate a subnet CIDR within the existing CIDR address block"
  type        = string
  default     = ""
}

variable "subnet_gateway_ip" {
  description = "Subnet gateway IP, if not specified, will calculate a gateway IP within the existing CIDR address block"
  type        = string
  default     = ""
}

# Create a VPC subnet resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id            = huaweicloud_vpc.test.id
  name              = var.subnet_name
  cidr              = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip        = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
  availability_zone = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test[0].names[0], null) : var.availability_zone
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID, assigned by referencing the VPC resource (huaweicloud\_vpc.test) ID
- **name**: Subnet name, assigned by referencing the input variable subnet\_name
- **cidr**: Subnet CIDR block, prioritizes input variable, calculates using cidrsubnet function if empty
- **gateway\_ip**: Gateway IP, prioritizes input variable, calculates using cidrhost function if empty
- **availability\_zone**: Availability zone, prioritizes input variable, uses the first result from availability zone list query data source if empty

### 7. Create Security Group

Add the following script to the TF file to instruct Terraform to create a security group resource:

```hcl
variable "security_group_name" {
  description = "Security group name"
  type        = string
}

# Create a security group resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_networking_secgroup" "test" {
  name = var.security_group_name
}
```

**Parameter Description**:

- **name**: Security group name, assigned by referencing the input variable security\_group\_name

> Note: Default security group rules cannot be deleted, otherwise UniAgent installation will fail.

### 8. Create ECS Instance and Install UniAgent

Add the following script to the TF file to instruct Terraform to create an ECS instance resource:

```hcl
variable "instance_name" {
  description = "ECS instance name"
  type        = string
}

variable "instance_user_data" {
  description = "ECS instance user data, used to install UniAgent"
  type        = string
}

# Create an ECS instance resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_compute_instance" "test" {
  name               = var.instance_name
  availability_zone  = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test[0].names[0], "") : var.availability_zone
  flavor_id          = var.instance_flavor_id == "" ? try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, "") : var.instance_flavor_id
  image_id           = var.instance_image_id == "" ? try(data.huaweicloud_images_images.test[0].images[0].id, "") : var.instance_image_id
  security_group_ids = [huaweicloud_networking_secgroup.test.id]
  user_data          = var.instance_user_data

  network {
    uuid = huaweicloud_vpc_subnet.test.id
  }
}
```

**Parameter Description**:

- **name**: ECS instance name, assigned by referencing the input variable instance\_name
- **availability\_zone**: Availability zone, prioritizes input variable, uses the first result from availability zone list query data source if empty
- **flavor\_id**: Flavor ID, prioritizes input variable, uses the first result from ECS flavor list query data source if empty
- **image\_id**: Image ID, prioritizes input variable, uses the first result from image list query data source if empty
- **security\_group\_ids**: Security group ID list, assigned by referencing the security group resource (huaweicloud\_networking\_secgroup.test) ID
- **user\_data**: User data, assigned by referencing the input variable instance\_user\_data, used to install UniAgent
- **network.uuid**: Network ID, assigned by referencing the VPC subnet resource (huaweicloud\_vpc\_subnet.test) ID

### 9. Create COC Script

Add the following script to the TF file to instruct Terraform to create a COC script resource:

```hcl
variable "script_name" {
  description = "Script name"
  type        = string
}

variable "script_description" {
  description = "Script description"
  type        = string
}

variable "script_risk_level" {
  description = "Script risk level"
  type        = string
}

variable "script_version" {
  description = "Script version"
  type        = string
}

variable "script_type" {
  description = "Script type"
  type        = string
}

variable "script_content" {
  description = "Script content"
  type        = string
}

variable "script_parameters" {
  description = "Script parameter list"
  type = list(object({
    name        = string
    value       = string
    description = string
    sensitive   = optional(bool)
  }))

  nullable = false
}

# Create a COC script resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_coc_script" "test" {
  name        = var.script_name
  description = var.script_description
  risk_level  = var.script_risk_level
  version     = var.script_version
  type        = var.script_type
  content     = var.script_content

  dynamic "parameters" {
    for_each = var.script_parameters

    content {
      name        = parameters.value.name
      value       = parameters.value.value
      description = parameters.value.description
      sensitive   = parameters.value.sensitive
    }
  }
}
```

**Parameter Description**:

- **name**: Script name, assigned by referencing the input variable script\_name
- **description**: Script description, assigned by referencing the input variable script\_description
- **risk\_level**: Script risk level, assigned by referencing the input variable script\_risk\_level
- **version**: Script version, assigned by referencing the input variable script\_version
- **type**: Script type, assigned by referencing the input variable script\_type
- **content**: Script content, assigned by referencing the input variable script\_content
- **parameters.name**: Parameter name, assigned by referencing the name field in the script parameter list
- **parameters.value**: Parameter value, assigned by referencing the value field in the script parameter list
- **parameters.description**: Parameter description, assigned by referencing the description field in the script parameter list
- **parameters.sensitive**: Whether the parameter is sensitive, assigned by referencing the sensitive field in the script parameter list

### 10. Create COC Script Execution

Add the following script to the TF file to instruct Terraform to create a COC script execution resource:

```hcl
variable "script_execute_timeout" {
  description = "Script execution timeout (seconds)"
  type        = number
}

variable "script_execute_execute_user" {
  description = "Script execution user"
  type        = string
}

variable "script_execute_parameters" {
  description = "Script execution parameter list"
  type = list(object({
    name  = string
    value = string
  }))

  nullable = false
}

# Create a COC script execution resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_coc_script_execute" "test" {
  script_id    = huaweicloud_coc_script.test.id
  instance_id  = huaweicloud_compute_instance.test.id
  timeout      = var.script_execute_timeout
  execute_user = var.script_execute_execute_user

  dynamic "parameters" {
    for_each = var.script_execute_parameters

    content {
      name  = parameters.value.name
      value = parameters.value.value
    }
  }
}
```

**Parameter Description**:

- **script\_id**: Script ID, assigned by referencing the COC script resource (huaweicloud\_coc\_script.test) ID
- **instance\_id**: Instance ID, assigned by referencing the ECS instance resource (huaweicloud\_compute\_instance.test) ID
- **timeout**: Execution timeout, assigned by referencing the input variable script\_execute\_timeout
- **execute\_user**: Execution user, assigned by referencing the input variable script\_execute\_execute\_user
- **parameters.name**: Parameter name, assigned by referencing the name field in the script execution parameter list
- **parameters.value**: Parameter value, assigned by referencing the value field in the script execution parameter list

### 11. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Network configuration
vpc_name            = "tf_test_coc_script_execute_vpc"
subnet_name         = "tf_test_coc_script_execute_subnet"
security_group_name = "tf_test_coc_script_execute_secgroup"

# ECS instance configuration
instance_name      = "tf_test_coc_script_execute"
instance_user_data = "your_user_data" # Please replace with your actual command for installing icagent

# Script configuration
script_name         = "tf_coc_script_execute"
script_description  = "Created by terraform script"
script_risk_level   = "LOW"
script_version      = "1.0.0"
script_type         = "SHELL"
script_content      = <<EOF
#! /bin/bash
echo "hello world!"
EOF

# Script parameter configuration
script_parameters = [
  {
    name        = "name"
    value       = "world"
    description = "the parameter"
  }
]

# Script execution configuration
script_execute_timeout      = 600
script_execute_execute_user = "root"
script_execute_parameters = [
  {
    name  = "name"
    value = "somebody"
  }
]
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="subnet_name=my-subnet"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 12. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating the COC script execution
4. Run `terraform show` to view the details of the created COC script execution

## Reference Information

- [Huawei Cloud COC Product Documentation](https://support.huaweicloud.com/coc/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For COC script execution](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/coc/script-execution)

# Deploy Script Order Execution

## Application Scenario

Cloud Operations Center (COC) is a one-stop operation and maintenance management platform provided by Huawei Cloud, offering enterprises a unified operation and maintenance management entry point. COC helps enterprises achieve automated operation and maintenance and intelligent management through script management, task scheduling, monitoring and alerting, improving operation and maintenance efficiency and quality.

Script order execution is one of the core functions of COC service, supporting the execution of various operation and maintenance scripts on ECS instances, including Shell scripts, Python scripts, etc. Through script order execution, you can achieve batch operation and maintenance operations, automated deployment, system configuration, and other tasks. This best practice will introduce how to use Terraform to automatically deploy COC script order execution, including the complete process of creating ECS instances, installing UniAgent, creating scripts, executing scripts, and order operations.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [ECS Flavor List Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)
- [IMS Image List Query Data Source (data.huaweicloud\_images\_images)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_images)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [ECS Instance Resource (huaweicloud\_compute\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_instance)
- [COC Script Resource (huaweicloud\_coc\_script)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/coc_script)
- [COC Script Execution Resource (huaweicloud\_coc\_script\_execute)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/coc_script_execute)
- [COC Script Order Operation Resource (huaweicloud\_coc\_script\_order\_operation)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/coc_script_order_operation)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones.test
    └── huaweicloud_vpc_subnet.test
        └── huaweicloud_compute_instance.test
            └── huaweicloud_coc_script_execute.test
                └── huaweicloud_coc_script_order_operation.test

data.huaweicloud_compute_flavors.test
    └── huaweicloud_compute_instance.test

data.huaweicloud_images_images.test
    └── huaweicloud_compute_instance.test

huaweicloud_vpc.test
    └── huaweicloud_vpc_subnet.test

huaweicloud_networking_secgroup.test
    └── huaweicloud_compute_instance.test

huaweicloud_coc_script.test
    └── huaweicloud_coc_script_execute.test
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Availability Zones Required for ECS Instance Resource Creation via Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the result of which will be used to create the ECS instance:

```hcl
variable "availability_zone" {
  description = "Availability zone information for the ECS instance"
  type        = string
  default     = ""
}

# Get all availability zone information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create the ECS instance
data "huaweicloud_availability_zones" "test" {
  count = var.availability_zone == "" ? 1 : 0
}
```

**Parameter Description**:

- **count**: Number of data source instances, used to control whether to execute the availability zone list query data source, only creates the data source when `var.availability_zone` is empty

### 3. Query ECS Instance Flavor Information via Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the result of which will be used to create the ECS instance:

```hcl
variable "instance_flavor_id" {
  description = "ECS instance flavor ID, if not specified, will use the first available flavor that meets the criteria"
  type        = string
  default     = ""
}

variable "instance_flavor_performance_type" {
  description = "ECS instance flavor performance type, used to query available flavors when instance_flavor_id is not specified"
  type        = string
  default     = "normal"
}

variable "instance_flavor_cpu_core_count" {
  description = "ECS instance flavor CPU core count, used to query available flavors when instance_flavor_id is not specified"
  type        = number
  default     = 2
}

variable "instance_flavor_memory_size" {
  description = "ECS instance flavor memory size (GB), used to query available flavors when instance_flavor_id is not specified"
  type        = number
  default     = 4
}

# Get all ECS flavor information that meets the criteria under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create the ECS instance
data "huaweicloud_compute_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  availability_zone = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test[0].names[0], null) : var.availability_zone
  performance_type  = var.instance_flavor_performance_type
  cpu_core_count    = var.instance_flavor_cpu_core_count
  memory_size       = var.instance_flavor_memory_size
}
```

**Parameter Description**:

- **count**: Number of data source instances, used to control whether to execute the ECS flavor list query data source, only creates the data source when `var.instance_flavor_id` is empty
- **availability\_zone**: Availability zone, prioritizes input variable, uses the first result from availability zone list query data source if empty
- **performance\_type**: Performance type, used to filter ECS flavors
- **cpu\_core\_count**: CPU core count, used to filter ECS flavors
- **memory\_size**: Memory size, used to filter ECS flavors

### 4. Query ECS Instance Image Information via Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the result of which will be used to create the ECS instance:

```hcl
variable "instance_image_id" {
  description = "ECS instance image ID, if not specified, will use the first available image that meets the criteria"
  type        = string
  default     = ""
}

variable "instance_image_os_type" {
  description = "ECS instance image operating system type, used to query available images when instance_image_id is not specified"
  type        = string
  default     = "Ubuntu"
}

variable "instance_image_visibility" {
  description = "ECS instance image visibility, used to query available images when instance_image_id is not specified"
  type        = string
  default     = "public"
}

# Get all image information that meets the criteria under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create the ECS instance
data "huaweicloud_images_images" "test" {
  count = var.instance_image_id == "" ? 1 : 0

  flavor_id  = var.instance_flavor_id == "" ? try(data.huaweicloud_compute_flavors.test[0].ids[0], "") : var.instance_flavor_id
  os         = var.instance_image_os_type
  visibility = var.instance_image_visibility
}
```

**Parameter Description**:

- **count**: Number of data source instances, used to control whether to execute the image list query data source, only creates the data source when `var.instance_image_id` is empty
- **flavor\_id**: Flavor ID, prioritizes input variable, uses the first result from ECS flavor list query data source if empty
- **os**: Operating system type, used to filter images
- **visibility**: Visibility, used to filter images

### 5. Create VPC

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC resource:

```hcl
variable "vpc_name" {
  description = "VPC name"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "192.168.0.0/16"
}

# Create a VPC resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: VPC name, assigned by referencing the input variable vpc\_name
- **cidr**: VPC CIDR block, assigned by referencing the input variable vpc\_cidr

### 6. Create VPC Subnet

Add the following script to the TF file to instruct Terraform to create a VPC subnet resource:

```hcl
variable "subnet_name" {
  description = "Subnet name"
  type        = string
}

variable "subnet_cidr" {
  description = "Subnet CIDR block, if not specified, will calculate a subnet CIDR within the existing CIDR address block"
  type        = string
  default     = ""
}

variable "subnet_gateway_ip" {
  description = "Subnet gateway IP, if not specified, will calculate a gateway IP within the existing CIDR address block"
  type        = string
  default     = ""
}

# Create a VPC subnet resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id            = huaweicloud_vpc.test.id
  name              = var.subnet_name
  cidr              = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip        = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
  availability_zone = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test[0].names[0], null) : var.availability_zone
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID, assigned by referencing the VPC resource (huaweicloud\_vpc.test) ID
- **name**: Subnet name, assigned by referencing the input variable subnet\_name
- **cidr**: Subnet CIDR block, prioritizes input variable, calculates using cidrsubnet function if empty
- **gateway\_ip**: Gateway IP, prioritizes input variable, calculates using cidrhost function if empty
- **availability\_zone**: Availability zone, prioritizes input variable, uses the first result from availability zone list query data source if empty

### 7. Create Security Group

Add the following script to the TF file to instruct Terraform to create a security group resource:

```hcl
variable "security_group_name" {
  description = "Security group name"
  type        = string
}

# Create a security group resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_networking_secgroup" "test" {
  name = var.security_group_name
}
```

**Parameter Description**:

- **name**: Security group name, assigned by referencing the input variable security\_group\_name

> Note: Default security group rules cannot be deleted, otherwise UniAgent installation will fail.

### 8. Create ECS Instance and Install UniAgent

Add the following script to the TF file to instruct Terraform to create an ECS instance resource:

```hcl
variable "instance_name" {
  description = "ECS instance name"
  type        = string
}

variable "instance_user_data" {
  description = "ECS instance user data, used to install UniAgent"
  type        = string
}

# Create an ECS instance resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_compute_instance" "test" {
  name               = var.instance_name
  availability_zone  = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test[0].names[0], null) : var.availability_zone
  flavor_id          = var.instance_flavor_id == "" ? try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, "") : var.instance_flavor_id
  image_id           = var.instance_image_id == "" ? try(data.huaweicloud_images_images.test[0].images[0].id, "") : var.instance_image_id
  security_group_ids = [huaweicloud_networking_secgroup.test.id]
  user_data          = var.instance_user_data

  network {
    uuid = huaweicloud_vpc_subnet.test.id
  }
}
```

**Parameter Description**:

- **name**: ECS instance name, assigned by referencing the input variable instance\_name
- **availability\_zone**: Availability zone, prioritizes input variable, uses the first result from availability zone list query data source if empty
- **flavor\_id**: Flavor ID, prioritizes input variable, uses the first result from ECS flavor list query data source if empty
- **image\_id**: Image ID, prioritizes input variable, uses the first result from image list query data source if empty
- **security\_group\_ids**: Security group ID list, assigned by referencing the security group resource (huaweicloud\_networking\_secgroup.test) ID
- **user\_data**: User data, assigned by referencing the input variable instance\_user\_data, used to install UniAgent
- **network.uuid**: Network ID, assigned by referencing the VPC subnet resource (huaweicloud\_vpc\_subnet.test) ID

### 9. Create COC Script

Add the following script to the TF file to instruct Terraform to create a COC script resource:

```hcl
variable "script_name" {
  description = "Script name"
  type        = string
}

variable "script_description" {
  description = "Script description"
  type        = string
}

variable "script_risk_level" {
  description = "Script risk level"
  type        = string
}

variable "script_version" {
  description = "Script version"
  type        = string
}

variable "script_type" {
  description = "Script type"
  type        = string
}

variable "script_content" {
  description = "Script content"
  type        = string
}

variable "script_parameters" {
  description = "Script parameter list"
  type = list(object({
    name        = string
    value       = string
    description = string
    sensitive   = optional(bool)
  }))
}

# Create a COC script resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_coc_script" "test" {
  name        = var.script_name
  description = var.script_description
  risk_level  = var.script_risk_level
  version     = var.script_version
  type        = var.script_type
  content     = var.script_content

  dynamic "parameters" {
    for_each = var.script_parameters

    content {
      name        = parameters.value.name
      value       = parameters.value.value
      description = parameters.value.description
      sensitive   = parameters.value.sensitive
    }
  }
}
```

**Parameter Description**:

- **name**: Script name, assigned by referencing the input variable script\_name
- **description**: Script description, assigned by referencing the input variable script\_description
- **risk\_level**: Script risk level, assigned by referencing the input variable script\_risk\_level
- **version**: Script version, assigned by referencing the input variable script\_version
- **type**: Script type, assigned by referencing the input variable script\_type
- **content**: Script content, assigned by referencing the input variable script\_content
- **parameters.name**: Parameter name, assigned by referencing the name field in the script parameter list
- **parameters.value**: Parameter value, assigned by referencing the value field in the script parameter list
- **parameters.description**: Parameter description, assigned by referencing the description field in the script parameter list
- **parameters.sensitive**: Whether the parameter is sensitive, assigned by referencing the sensitive field in the script parameter list

### 10. Create COC Script Execution

Add the following script to the TF file to instruct Terraform to create a COC script execution resource:

```hcl
variable "script_execute_timeout" {
  description = "Script execution timeout (seconds)"
  type        = number
}

variable "script_execute_user" {
  description = "Script execution user"
  type        = string
}

variable "script_execute_parameters" {
  description = "Script execution parameter list"
  type = list(object({
    name  = string
    value = string
  }))
}

# Create a COC script execution resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_coc_script_execute" "test" {
  script_id    = huaweicloud_coc_script.test.id
  instance_id  = huaweicloud_compute_instance.test.id
  timeout      = var.script_execute_timeout
  execute_user = var.script_execute_user

  dynamic "parameters" {
    for_each = var.script_execute_parameters

    content {
      name  = parameters.value.name
      value = parameters.value.value
    }
  }

  timeouts {
    create = "1m"
  }
}
```

**Parameter Description**:

- **script\_id**: Script ID, assigned by referencing the COC script resource (huaweicloud\_coc\_script.test) ID
- **instance\_id**: Instance ID, assigned by referencing the ECS instance resource (huaweicloud\_compute\_instance.test) ID
- **timeout**: Execution timeout, assigned by referencing the input variable script\_execute\_timeout
- **execute\_user**: Execution user, assigned by referencing the input variable script\_execute\_user
- **parameters.name**: Parameter name, assigned by referencing the name field in the script execution parameter list
- **parameters.value**: Parameter value, assigned by referencing the value field in the script execution parameter list
- **timeouts.create**: Creation timeout, set to 1 minute

### 11. Create COC Script Order Operation

Add the following script to the TF file to instruct Terraform to create a COC script order operation resource:

```hcl
variable "script_order_operation_batch_index" {
  description = "Script order operation batch index"
  type        = number
}

variable "script_order_operation_instance_id" {
  description = "Script order operation instance ID"
  type        = number
}

variable "script_order_operation_type" {
  description = "Script order operation type"
  type        = string
  default     = "CANCEL_ORDER"
}

# Create a COC script order operation resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_coc_script_order_operation" "test" {
  execute_uuid   = huaweicloud_coc_script_execute.test.id
  batch_index    = var.script_order_operation_batch_index
  instance_id    = var.script_order_operation_instance_id
  operation_type = var.script_order_operation_type
}
```

**Parameter Description**:

- **execute\_uuid**: Execution UUID, assigned by referencing the COC script execution resource (huaweicloud\_coc\_script\_execute.test) ID
- **batch\_index**: Batch index, assigned by referencing the input variable script\_order\_operation\_batch\_index
- **instance\_id**: Instance ID, assigned by referencing the input variable script\_order\_operation\_instance\_id
- **operation\_type**: Operation type, assigned by referencing the input variable script\_order\_operation\_type

### 12. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Network configuration
vpc_name            = "tf_test_coc_order_vpc"
subnet_name         = "tf_test_coc_order_subnet"
security_group_name = "tf_test_coc_order_secgroup"

# ECS instance configuration
instance_name      = "tf_test_coc_order_instance"
instance_user_data = "your_user_data" # Please replace with your actual command for installing icagent

# Script configuration
script_name        = "tf_script_order_demo"
script_description = "Created by terraform script"
script_risk_level  = "LOW"
script_version     = "1.0.0"
script_type        = "SHELL"
script_content     = <<EOF
#! /bin/bash
echo "hello $${name}!"
sleep 2m
EOF

# Script parameter configuration
script_parameters = [
  {
    name        = "name"
    value       = "world"
    description = "the parameter"
  },
  {
    name        = "company"
    value       = "Terraform"
    description = "the second parameter"
    sensitive   = true
  }
]

# Script execution configuration
script_execute_timeout = 600
script_execute_user    = "root"
script_execute_parameters = [
  {
    name  = "name"
    value = "somebody"
  }
]

# Script order operation configuration
script_order_operation_batch_index = 1
script_order_operation_instance_id = 1
script_order_operation_type        = "CANCEL_ORDER"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="subnet_name=my-subnet"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 13. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating the COC script order execution
4. Run `terraform show` to view the details of the created COC script order execution

## Reference Information

- [Huawei Cloud COC Product Documentation](https://support.huaweicloud.com/coc/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For COC Script Order Execution](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/coc/script-order-execution)