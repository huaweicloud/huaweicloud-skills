# Deploy Host Group

## Application Scenario

Host Security Service (HSS) is a host security protection service provided by Huawei Cloud, offering asset management, vulnerability management, intrusion detection, baseline checks, and other functions to help you comprehensively protect the security of cloud hosts. By creating HSS host groups, you can group multiple hosts for management, uniformly configure security policies, perform security checks, and conduct security operations, improving the efficiency and convenience of host security management. This best practice will introduce how to use Terraform to automatically deploy HSS host groups, including VPC, subnet, security group, ECS instance (with HSS agent), and HSS host group creation.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Data Source (huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [ECS Flavors Data Source (huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)
- [Images Data Source (huaweicloud\_images\_images)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_images)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [ECS Instance Resource (huaweicloud\_compute\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_instance)
- [HSS Host Group Resource (huaweicloud\_hss\_host\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/hss_host_group)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── data.huaweicloud_compute_flavors
        └── data.huaweicloud_images_images
            └── huaweicloud_compute_instance

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_compute_instance

huaweicloud_networking_secgroup
    └── huaweicloud_compute_instance
        └── huaweicloud_hss_host_group
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Availability Zones Data Source

Add the following script to the TF file (e.g., main.tf) to query availability zone information:

```hcl
variable "availability_zone" {
  description = "The availability zone to which the ECS instance and network belong"
  type        = string
  default     = ""
}

# Get all availability zone information in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block), used for creating ECS instance resources
data "huaweicloud_availability_zones" "test" {
  count = var.availability_zone == "" ? 1 : 0
}
```

**Parameter Description**:

- **count**: The number of data source creations, used to control whether to execute the availability zone list query data source, only creates the data source (i.e., executes the availability zone list query) when `var.availability_zone` is empty

### 3. Query ECS Flavors Data Source

Add the following script to the TF file (e.g., main.tf) to query ECS flavor information:

```hcl
variable "instance_flavor_id" {
  description = "The flavor ID of the ECS instance"
  type        = string
  default     = ""
}

variable "instance_flavor_performance_type" {
  description = "The performance type of the ECS instance flavor"
  type        = string
  default     = "normal"
}

variable "instance_flavor_cpu_core_count" {
  description = "The number of the ECS instance flavor CPU cores"
  type        = number
  default     = 2
}

variable "instance_flavor_memory_size" {
  description = "The number of the ECS instance flavor memories"
  type        = number
  default     = 4
}

# Get all ECS flavor information in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block), used for creating ECS instance resources
data "huaweicloud_compute_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  availability_zone = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test[0].names[0], null)
  performance_type  = var.instance_flavor_performance_type
  cpu_core_count    = var.instance_flavor_cpu_core_count
  memory_size       = var.instance_flavor_memory_size
}
```

**Parameter Description**:

- **count**: The number of data source creations, used to control whether to execute the ECS flavor list query data source, only creates the data source (i.e., executes the ECS flavor list query) when `var.instance_flavor_id` is empty
- **availability\_zone**: Availability zone, assigned by referencing input variables or availability zone data source
- **performance\_type**: Performance type, assigned by referencing input variable instance\_flavor\_performance\_type, default value is "normal"
- **cpu\_core\_count**: Number of CPU cores, assigned by referencing input variable instance\_flavor\_cpu\_core\_count, default value is 2
- **memory\_size**: Memory size (GB), assigned by referencing input variable instance\_flavor\_memory\_size, default value is 4

### 4. Query Images Data Source

Add the following script to the TF file (e.g., main.tf) to query image information:

```hcl
variable "instance_image_id" {
  description = "The image ID of the ECS instance"
  type        = string
  default     = ""
}

variable "instance_image_os_type" {
  description = "The OS type of the ECS instance flavor"
  type        = string
  default     = "Ubuntu"
}

variable "instance_image_visibility" {
  description = "The visibility of the ECS instance flavor"
  type        = string
  default     = "public"
}

# Get all image information in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block), used for creating ECS instance resources
data "huaweicloud_images_images" "test" {
  count = var.instance_image_id == "" ? 1 : 0

  flavor_id  = var.instance_flavor_id != "" ? var.instance_flavor_id : try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, null)
  os         = var.instance_image_os_type
  visibility = var.instance_image_visibility
}
```

**Parameter Description**:

- **count**: The number of data source creations, used to control whether to execute the image list query data source, only creates the data source (i.e., executes the image list query) when `var.instance_image_id` is empty
- **flavor\_id**: Flavor ID, assigned by referencing input variables or ECS flavor data source
- **os**: Operating system type, assigned by referencing input variable instance\_image\_os\_type, default value is "Ubuntu"
- **visibility**: Image visibility, assigned by referencing input variable instance\_image\_visibility, default value is "public"

### 5. Create VPC Resource

Add the following script to the TF file (e.g., main.tf) to create a VPC:

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

# Create VPC resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: VPC name, assigned by referencing input variable vpc\_name
- **cidr**: VPC CIDR block, assigned by referencing input variable vpc\_cidr, default value is "192.168.0.0/16"

### 6. Create VPC Subnet Resource

Add the following script to the TF file (e.g., main.tf) to create a VPC subnet:

```hcl
variable "subnet_name" {
  description = "The name of the subnet"
  type        = string
}

variable "subnet_cidr" {
  description = "The CIDR block of the subnet"
  type        = string
  default     = "192.168.0.0/24"
}

variable "subnet_gateway_ip" {
  description = "The gateway IP of the subnet"
  type        = string
  default     = ""
}

# Create VPC subnet resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr != "" ? var.subnet_cidr : cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0)
  gateway_ip = var.subnet_gateway_ip != "" ? var.subnet_gateway_ip : cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1)
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID, assigned by referencing the VPC resource
- **name**: Subnet name, assigned by referencing input variable subnet\_name
- **cidr**: Subnet CIDR block, assigned by referencing input variables or automatic calculation
- **gateway\_ip**: Subnet gateway IP, assigned by referencing input variables or automatic calculation

### 7. Create Security Group Resource

Add the following script to the TF file (e.g., main.tf) to create a security group:

```hcl
variable "security_group_name" {
  description = "The name of the security group"
  type        = string
}

# Create security group resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: Security group name, assigned by referencing input variable security\_group\_name
- **delete\_default\_rules**: Whether to delete default rules, set to true to delete default rules

### 8. Create ECS Instance Resource

Add the following script to the TF file (e.g., main.tf) to create an ECS instance:

```hcl
variable "ecs_instance_name" {
  type        = string
  description = "The name of the ECS instance"
}

# Create ECS instance resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_compute_instance" "test" {
  name               = var.ecs_instance_name
  image_id           = var.instance_image_id != "" ? var.instance_image_id : try(data.huaweicloud_images_images.test[0].images[0].id, null)
  flavor_id          = var.instance_flavor_id != "" ? var.instance_flavor_id : try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, null)
  availability_zone  = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test[0].names[0], null)
  security_group_ids = [huaweicloud_networking_secgroup.test.id]
  agent_list         = "hss"

  network {
    uuid = huaweicloud_vpc_subnet.test.id
  }
}
```

**Parameter Description**:

- **name**: ECS instance name, assigned by referencing input variable ecs\_instance\_name
- **image\_id**: Image ID, assigned by referencing input variables or image data source
- **flavor\_id**: Flavor ID, assigned by referencing input variables or ECS flavor data source
- **availability\_zone**: Availability zone, assigned by referencing input variables or availability zone data source
- **security\_group\_ids**: Security group ID list, assigned by referencing the security group resource
- **agent\_list**: Agent list, set to "hss" to install HSS agent
- **network.uuid**: Network subnet ID, assigned by referencing the VPC subnet resource

> Note: ECS instances need to configure `agent_list = "hss"` to install HSS agent, which is a prerequisite for creating HSS host groups. After the ECS instance is created, you need to wait for the HSS agent installation to complete before adding the instance to the HSS host group.

### 9. Create HSS Host Group Resource

Add the following script to the TF file (e.g., main.tf) to create an HSS host group:

```hcl
variable "host_group_name" {
  type        = string
  description = "The name of the HSS host group"
}

# Create HSS host group resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_hss_host_group" "test" {
  name     = var.host_group_name
  host_ids = [huaweicloud_compute_instance.test.id]
}
```

**Parameter Description**:

- **name**: HSS host group name, assigned by referencing input variable host\_group\_name
- **host\_ids**: Host ID list, assigned by referencing the ECS instance resource

> Note: HSS host groups need to include ECS instances that have HSS agent installed. Ensure that the ECS instance has been created and the HSS agent installation is complete before adding the instance to the host group.

### 10. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# VPC and Subnet Configuration
vpc_name            = "tf_test_hss_host_group_vpc"
vpc_cidr            = "192.168.0.0/16"
subnet_name         = "tf_test_hss_host_group_subnet"
subnet_cidr         = "192.168.0.0/24"

# Security Group Configuration
security_group_name = "tf_test_hss_host_group_secgroup"

# ECS Instance Configuration
ecs_instance_name    = "tf_test_hss_host_group_ecs_instance"

# HSS Host Group Configuration
host_group_name      = "tf_test_hss_host_group"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially:
   - `availability_zone` can be set to availability zone, if empty, it will be automatically queried
   - `instance_flavor_id` can be set to ECS flavor ID, if empty, it will be automatically queried based on CPU and memory parameters
   - `instance_image_id` can be set to image ID, if empty, it will be automatically queried based on operating system type
   - `instance_flavor_performance_type`, `instance_flavor_cpu_core_count`, `instance_flavor_memory_size` can be set to ECS flavor parameters
   - `instance_image_os_type`, `instance_image_visibility` can be set to image parameters
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="host_group_name=my-host-group"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc` and `export TF_VAR_host_group_name=my-host-group`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. ECS instances need to configure `agent_list = "hss"` to install HSS agent, which is a prerequisite for creating HSS host groups.

### 11. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create HSS host groups:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating VPC, subnet, security group, ECS instance, and HSS host group
4. Run `terraform show` to view the details of the created HSS host group

> Note: After the ECS instance is created, you need to wait for the HSS agent installation to complete before adding the instance to the HSS host group. If the instance has not completed HSS agent installation, host group creation may fail. It is recommended to confirm the HSS agent status of the ECS instance before creating the host group.

## Reference Information

- [Huawei Cloud HSS Product Documentation](https://support.huaweicloud.com/hss/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Host Group](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/hss/host-group)

# Deploy Host Protection

## Application Scenario

Host Security Service (HSS) is a host security protection service provided by Huawei Cloud, offering asset management, vulnerability management, intrusion detection, baseline checks, and other functions to help you comprehensively protect the security of cloud hosts. By enabling HSS protection for existing hosts, you can provide comprehensive security protection capabilities for cloud hosts, including real-time monitoring, threat detection, vulnerability scanning, baseline checks, and other functions, ensuring host security. This best practice will introduce how to use Terraform to automatically deploy HSS host protection, enabling pay-per-use HSS protection services for existing hosts.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [HSS Host Protection Resource (huaweicloud\_hss\_host\_protection)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/hss_host_protection)

### Resource/Data Source Dependencies

```
huaweicloud_hss_host_protection
```

> Note: HSS host protection resource depends on an existing host (ECS instance), which needs to have HSS agent installed. The host ID is specified through input variables.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create HSS Host Protection Resource

Add the following script to the TF file (e.g., main.tf) to create HSS host protection:

```hcl
variable "host_id" {
  description = "The host ID for the host protection"
  type        = string
}

variable "protection_version" {
  description = "The protection version enabled by the host"
  type        = string
}

variable "is_wait_host_available" {
  description = "Whether to wait for the host agent status to become online"
  type        = bool
  default     = false
}

variable "enterprise_project_id" {
  description = "The ID of the enterprise project to which the host protection belongs"
  type        = string
  default     = null
}

# Create HSS host protection resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_hss_host_protection" "test" {
  host_id                = var.host_id
  version                = var.protection_version
  charging_mode          = "postPaid"
  is_wait_host_available = var.is_wait_host_available
  enterprise_project_id  = var.enterprise_project_id
}
```

**Parameter Description**:

- **host\_id**: Host ID, assigned by referencing input variable host\_id, must be an existing ECS instance ID with HSS agent installed
- **version**: Protection version, assigned by referencing input variable protection\_version, for example "hss.version.enterprise" represents enterprise edition
- **charging\_mode**: Charge mode, set to "postPaid" to indicate pay-per-use
- **is\_wait\_host\_available**: Whether to wait for the host agent status to become online, assigned by referencing input variable is\_wait\_host\_available, default value is false
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing input variable enterprise\_project\_id, optional parameter, default value is null

> Note: HSS host protection depends on an existing host, which must have HSS agent installed. If the host has not installed HSS agent, you need to install HSS agent for the ECS instance first (can be achieved by configuring `agent_list = "hss"` when creating the ECS instance). The protection version parameter needs to be selected according to actual requirements, common versions include basic edition, enterprise edition, etc.

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# HSS Host Protection Configuration
host_id            = "your_host_id"
protection_version = "hss.version.enterprise"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially:
   - `host_id` needs to be set to an existing ECS instance ID with HSS agent installed
   - `protection_version` can be set to "hss.version.enterprise" (enterprise edition) or other supported protection versions
   - `is_wait_host_available` can be set to true, indicating to wait for the host agent status to become online before creating protection
   - `enterprise_project_id` can be set to enterprise project ID, can be omitted if not needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="host_id=your_host_id" -var="protection_version=hss.version.enterprise"`
2. Environment variables: `export TF_VAR_host_id=your_host_id` and `export TF_VAR_protection_version=hss.version.enterprise`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. Ensure that the ECS instance corresponding to the specified host ID has HSS agent installed, otherwise protection creation may fail.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create HSS host protection:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating HSS host protection
4. Run `terraform show` to view the details of the created HSS host protection

> Note: Before creating HSS host protection, ensure that the specified host has HSS agent installed. If the host has not installed HSS agent, you need to install HSS agent for the ECS instance first. If `is_wait_host_available = true` is set, Terraform will wait for the host agent status to become online before creating protection, which may take some time.

## Reference Information

- [Huawei Cloud HSS Product Documentation](https://support.huaweicloud.com/hss/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Host Protection](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/hss/postpaid-host-protection)

# Deploy Quota

## Application Scenario

Host Security Service (HSS) is a host security protection service provided by Huawei Cloud, offering asset management, vulnerability management, intrusion detection, baseline checks, and other functions to help you comprehensively protect the security of cloud hosts. By purchasing HSS quotas, you can provide prepaid security protection services for cloud hosts, including real-time monitoring, threat detection, vulnerability scanning, baseline checks, and other functions, ensuring host security. This best practice will introduce how to use Terraform to automatically deploy HSS quotas, purchase prepaid HSS protection quotas, and provide continuous security protection capabilities for cloud hosts.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [HSS Quota Resource (huaweicloud\_hss\_quota)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/hss_quota)

### Resource/Data Source Dependencies

```
huaweicloud_hss_quota
```

> Note: HSS quota resource is an independent resource used to purchase HSS protection quotas. After purchasing quotas, you can assign quotas to hosts that need protection.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create HSS Quota Resource

Add the following script to the TF file (e.g., main.tf) to create HSS quota:

```hcl
variable "quota_version" {
  description = "The protection quota version"
  type        = string
}

variable "period_unit" {
  description = "The charging period unit of the quota"
  type        = string
}

variable "period" {
  description = "The charging period of the quota"
  type        = number
}

variable "is_auto_renew" {
  description = "Whether auto-renew is enabled"
  type        = bool
  default     = false
}

variable "enterprise_project_id" {
  description = "The enterprise project ID to which the HSS quota belongs"
  type        = string
  default     = null
}

variable "quota_tags" {
  description = "The key/value pairs to associate with the HSS quota"
  type        = map(string)
  default     = null
}

# Create HSS quota resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_hss_quota" "test" {
  version               = var.quota_version
  period_unit           = var.period_unit
  period                = var.period
  auto_renew            = var.is_auto_renew
  enterprise_project_id = var.enterprise_project_id
  tags                  = var.quota_tags
}
```

**Parameter Description**:

- **version**: Protection quota version, assigned by referencing input variable quota\_version, for example "hss.version.enterprise" represents enterprise edition
- **period\_unit**: Charge period unit, assigned by referencing input variable period\_unit, optional values are "month" or "year"
- **period**: Charge period, assigned by referencing input variable period, represents the purchase duration, for example 1 represents 1 month or 1 year
- **auto\_renew**: Whether auto-renewal is enabled, assigned by referencing input variable is\_auto\_renew, default value is false
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing input variable enterprise\_project\_id, optional parameter, default value is null
- **tags**: Quota tags, assigned by referencing input variable quota\_tags, optional parameter, default value is null

> Note: HSS quota uses prepaid billing mode, requiring specification of charge period unit and period. After purchasing quotas, you can assign quotas to hosts that need protection. The quota version needs to be selected according to actual requirements, common versions include basic edition, enterprise edition, etc.

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# HSS Quota Configuration
quota_version         = "hss.version.enterprise"
period_unit           = "month"
period                = 1
is_auto_renew         = false
enterprise_project_id = "0"
quota_tags            = {
  foo = "bar"
  key = "value"
}
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially:
   - `quota_version` can be set to "hss.version.enterprise" (enterprise edition) or other supported quota versions
   - `period_unit` can be set to "month" or "year"
   - `period` can be set to the purchase duration, for example 1 represents 1 month or 1 year
   - `is_auto_renew` can be set to true to enable auto-renewal
   - `enterprise_project_id` can be set to enterprise project ID, can be omitted or set to "0" if not needed
   - `quota_tags` can be set to quota tags for resource classification and management, can be omitted if not needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="quota_version=hss.version.enterprise" -var="period_unit=month" -var="period=1"`
2. Environment variables: `export TF_VAR_quota_version=hss.version.enterprise` and `export TF_VAR_period_unit=month`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. HSS quota uses prepaid billing mode, and charges will be incurred after purchase. Please select the appropriate quota version and purchase duration according to actual requirements.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create HSS quota:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating HSS quota
4. Run `terraform show` to view the details of the created HSS quota

> Note: Charges will be incurred after HSS quota creation. Please ensure sufficient account balance. After purchasing quotas, you can assign quotas to hosts that need protection. If auto-renewal is enabled, quotas will be automatically renewed before expiration.

## Reference Information

- [Huawei Cloud HSS Product Documentation](https://support.huaweicloud.com/hss/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Quota](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/hss/prepaid-quota)
