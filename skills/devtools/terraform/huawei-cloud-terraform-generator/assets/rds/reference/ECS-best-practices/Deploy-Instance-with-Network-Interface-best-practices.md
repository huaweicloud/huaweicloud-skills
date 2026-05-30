# Deploy Instance with Network Interface

## Application Scenario

Elastic Cloud Server (ECS) is a fundamental computing component composed of CPU, memory, operating system, and cloud disks. After an Elastic Cloud Server is successfully created, you can use it in the cloud just like using your own local PC or physical server. Huawei Cloud provides various types of Elastic Cloud Servers to meet different usage scenarios. A network interface is a connection point between an ECS instance and a network. An ECS instance can attach multiple network interfaces to achieve multi-NIC functionality. By attaching additional network interfaces to ECS instances, you can achieve network isolation, load balancing, high availability, and other requirements. Before creating, you need to confirm the specification type, image type, disk type, and other parameters of the Elastic Cloud Server according to the actual application scenario, and select appropriate network parameters and security group rules. This best practice will introduce how to use Terraform to automatically deploy an ECS instance with attached network interface, including VPC, multiple subnets, security group, ECS instance, and network interface attachment creation.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [ECS Flavors Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)
- [IMS Images Query Data Source (data.huaweicloud\_images\_images)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_images)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [ECS Instance Resource (huaweicloud\_compute\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_instance)
- [Network Interface Attachment Resource (huaweicloud\_compute\_interface\_attach)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_interface_attach)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    ├── data.huaweicloud_compute_flavors
    │   └── data.huaweicloud_images_images
    │       └── huaweicloud_compute_instance
    └── huaweicloud_compute_interface_attach

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        ├── huaweicloud_compute_instance
        └── huaweicloud_compute_interface_attach

huaweicloud_networking_secgroup
    └── huaweicloud_compute_instance
        └── huaweicloud_compute_interface_attach
```

## Implementation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration introduction, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://hcbp.gitbook.io/huaweicloud-provider/product-introduction/prepare_before_deploy).

### 2. Query Availability Zones Required for ECS Instance Resource Creation Through Data Source

Add the following script to the TF file (such as main.tf) to instruct Terraform to perform a data source query, the query results are used to create ECS instances:

```hcl
variable "availability_zone" {
  description = "The availability zone to which the ECS instance belongs"
  type        = string
  default     = ""
  nullable    = false
}

# Query all availability zone information in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted) for creating ECS instances
data "huaweicloud_availability_zones" "test" {
  count = var.availability_zone == "" ? 1 : 0
}
```

**Parameter Description**:

- **count**: The number of data source queries, used to control whether to query the availability zone list, only when `var.availability_zone` is empty, query the availability zone list

### 3. Query Instance Flavors Required for ECS Instance Resource Creation Through Data Source

Add the following script to the TF file to instruct Terraform to query ECS flavors that meet the conditions:

```hcl
variable "instance_flavor_id" {
  description = "The flavor ID of the ECS instance"
  type        = string
  default     = ""
  nullable    = false
}

variable "instance_performance_type" {
  description = "The performance type of the ECS instance flavor"
  type        = string
  default     = "normal"
}

variable "instance_cpu_core_count" {
  description = "The number of CPU cores of the ECS instance"
  type        = number
  default     = 2
}

variable "instance_memory_size" {
  description = "The memory size in GB of the ECS instance"
  type        = number
  default     = 4
}

# Query all ECS flavor information that meets specific conditions in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted) for creating ECS instances
data "huaweicloud_compute_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  availability_zone = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test[0].names[0], null)
  performance_type  = var.instance_performance_type
  cpu_core_count    = var.instance_cpu_core_count
  memory_size       = var.instance_memory_size
}
```

**Parameter Description**:

- **count**: The number of data source queries, used to control whether to query instance flavor information, only when `var.instance_flavor_id` is empty, query instance flavor information
- **availability\_zone**: The availability zone where the flavor is located, if availability zone is specified, use that value, otherwise use the first availability zone from the availability zone list query data source
- **performance\_type**: The performance type of the flavor, assigned by referencing the input variable `instance_performance_type`, default is "normal" indicating standard type
- **cpu\_core\_count**: CPU core count, assigned by referencing the input variable `instance_cpu_core_count`, default is 2 cores
- **memory\_size**: Memory size (GB), assigned by referencing the input variable `instance_memory_size`, default is 4GB

### 4. Query Images Required for ECS Instance Resource Creation Through Data Source

Add the following script to the TF file to instruct Terraform to query images that meet the conditions:

```hcl
variable "instance_image_id" {
  description = "The image ID of the ECS instance"
  type        = string
  default     = ""
  nullable    = false
}

variable "instance_image_visibility" {
  description = "The visibility of the ECS instance image"
  type        = string
  default     = "public"
}

variable "instance_image_os" {
  description = "The operating system of the ECS instance image"
  type        = string
  default     = "Ubuntu"
}

# Query all IMS image information that meets specific conditions in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted) for creating ECS instances
data "huaweicloud_images_images" "test" {
  count = var.instance_image_id == "" ? 1 : 0

  flavor_id  = var.instance_flavor_id != "" ? var.instance_flavor_id : try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, null)
  visibility = var.instance_image_visibility
  os         = var.instance_image_os
}
```

**Parameter Description**:

- **count**: The number of data source queries, used to control whether to query image information, only when `var.instance_image_id` is empty, query image information
- **flavor\_id**: The flavor ID supported by the image, if instance flavor ID is specified, use that value, otherwise assign based on the return result of the compute flavor list query data source
- **visibility**: The visibility of the image, assigned by referencing the input variable `instance_image_visibility`, default is "public" indicating public image
- **os**: The operating system type of the image, assigned by referencing the input variable `instance_image_os`, default is "Ubuntu" operating system

### 5. Create VPC Resource

Add the following script to the TF file to instruct Terraform to create a VPC resource:

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

# Create a VPC resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted) for deploying ECS instances
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: The name of the VPC, assigned by referencing the input variable `vpc_name`
- **cidr**: The CIDR block of the VPC, assigned by referencing the input variable `vpc_cidr`, default is "192.168.0.0/16" block

### 6. Create VPC Subnet Resources

Add the following script to the TF file to instruct Terraform to create multiple VPC subnet resources (at least 2 subnets are required, one for the primary network and one for the attached network interface):

```hcl
variable "subnet_configurations" {
  description = "The list of subnet configurations for ECS instance."
  type = list(object({
    subnet_name       = string
    subnet_cidr       = optional(string)
    subnet_gateway_ip = optional(string)
  }))
}

# Create multiple VPC subnet resources in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted) for deploying ECS instances
resource "huaweicloud_vpc_subnet" "test" {
  count = length(var.subnet_configurations)

  vpc_id     = huaweicloud_vpc.test.id
  name       = lookup(var.subnet_configurations[count.index], "subnet_name", null)
  cidr       = try(coalesce(lookup(var.subnet_configurations[count.index], "subnet_cidr", null), cidrsubnet(huaweicloud_vpc.test.cidr, 8, count.index)), null)
  gateway_ip = try(coalesce(lookup(var.subnet_configurations[count.index], "subnet_gateway_ip", null), cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, count.index), 1)), null)
}
```

**Parameter Description**:

- **count**: The number of resource creations, dynamically creating subnet resources based on the length of the input variable `subnet_configurations`
- **vpc\_id**: The ID of the VPC to which the subnet belongs, referencing the ID of the VPC resource created earlier
- **name**: The name of the subnet, obtained from the input variable `subnet_configurations`
- **cidr**: The CIDR block of the subnet, if subnet CIDR is specified in the configuration, use that value, otherwise use the cidrsubnet function to divide a subnet segment from the VPC's CIDR block
- **gateway\_ip**: The gateway IP of the subnet, if gateway IP is specified in the configuration, use that value, otherwise use the cidrhost function to get the first IP address from the subnet segment as the gateway IP

> Note: This best practice requires creating at least 2 subnets. The first subnet is used for the ECS instance's primary network, and the second subnet is used for the attached network interface. If `attached_network_id` is not provided, `subnet_configurations` must contain at least 2 elements.

### 7. Create Security Group Resource

Add the following script to the TF file to instruct Terraform to create a security group resource:

```hcl
variable "security_group_name" {
  description = "The name of the security group"
  type        = string
}

# Create a security group resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted) for deploying ECS instances
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: The name of the security group, assigned by referencing the input variable `security_group_name`
- **delete\_default\_rules**: Whether to delete default rules, set to true to delete default rules

### 8. Create ECS Instance Resource

Add the following script to the TF file to instruct Terraform to create an ECS instance resource:

```hcl
variable "instance_name" {
  description = "The name of the ECS instance"
  type        = string
}

variable "instance_admin_password" {
  description = "The login password of the ECS instance"
  type        = string
  sensitive   = true
}

# Create an ECS instance resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_compute_instance" "test" {
  name               = var.instance_name
  image_id           = var.instance_image_id != "" ? var.instance_image_id : try(data.huaweicloud_images_images.test[0].images[0].id, null)
  flavor_id          = var.instance_flavor_id != "" ? var.instance_flavor_id : try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, null)
  security_group_ids = [huaweicloud_networking_secgroup.test.id]
  availability_zone  = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test[0].names[0], null)
  admin_pass         = var.instance_admin_password

  network {
    uuid = try(huaweicloud_vpc_subnet.test[0].id, null)
  }

  # When using huaweicloud_compute_interface_attach, if the security group is not specified, the default security group will be automatically added to the ECS instance.
  lifecycle {
    ignore_changes = [
      security_group_ids
    ]
  }
}
```

**Parameter Description**:

- **name**: The name of the ECS instance, assigned by referencing the input variable `instance_name`
- **image\_id**: The image ID used by the ECS instance, if image ID is specified, use that value, otherwise assign based on the return result of the image list query data source
- **flavor\_id**: The flavor ID used by the ECS instance, if instance flavor ID is specified, use that value, otherwise assign based on the return result of the compute flavor list query data source
- **security\_group\_ids**: The list of security group IDs associated with the ECS instance, using the ID of the created security group resource
- **availability\_zone**: The availability zone where the ECS instance is located, if availability zone is specified, use that value, otherwise use the first availability zone from the availability zone list query data source
- **admin\_pass**: The administrator password of the ECS instance, assigned by referencing the input variable `instance_admin_password`
- **network**: Network configuration block, specifying the primary network to which the ECS instance connects
  - **uuid**: The unique identifier of the network, using the ID of the first subnet resource
- **lifecycle**: Lifecycle configuration block, used to control the lifecycle behavior of resources
  - **ignore\_changes**: Specifies attribute changes to be ignored in subsequent applies, set to ignore changes to `security_group_ids`, because when using `huaweicloud_compute_interface_attach`, if the security group is not specified, the system will automatically add the default security group to the ECS instance

### 9. Create Network Interface Attachment Resource

Add the following script to the TF file to instruct Terraform to create a network interface attachment resource:

```hcl
variable "attached_network_id" {
  description = "The ID of the network to which the ECS instance to be attached"
  type        = string
  default     = ""
  nullable    = false

  validation {
    condition     = var.attached_network_id != "" || length(var.subnet_configurations) == 2
    error_message = "When attached_network_id is not provided, subnet_configurations must have exactly 2 elements."
  }
}

variable "attached_interface_fixed_ip" {
  description = "The fixed IP address of the ECS instance to be attached"
  type        = string
  default     = null
}

variable "attached_security_group_ids" {
  description = "The list of security group IDs of the ECS instance to be attached"
  type        = list(string)
  default     = null
}

# Create a network interface attachment resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_compute_interface_attach" "test" {
  instance_id        = huaweicloud_compute_instance.test.id
  network_id         = var.attached_network_id != "" ? var.attached_network_id : try(huaweicloud_vpc_subnet.test[1].id, null)
  fixed_ip           = var.attached_interface_fixed_ip
  security_group_ids = var.attached_security_group_ids
}
```

**Parameter Description**:

- **instance\_id**: The ECS instance ID to which the network interface is attached, referencing the ID of the ECS instance resource created earlier
- **network\_id**: The network ID to be attached, if `attached_network_id` is specified, use that value, otherwise use the ID of the second subnet resource
- **fixed\_ip**: The fixed IP address of the network interface, assigned by referencing the input variable `attached_interface_fixed_ip`, if not specified, it will be automatically assigned by the system
- **security\_group\_ids**: The list of security group IDs for the network interface, assigned by referencing the input variable `attached_security_group_ids`, if not specified, the default security group will be used

> Note: When using `huaweicloud_compute_interface_attach`, if the security group is not specified, the system will automatically add the default security group to the ECS instance. Therefore, the `lifecycle.ignore_changes` is configured in the ECS instance resource to ignore changes to `security_group_ids` to avoid configuration conflicts caused by automatically adding the default security group.

### 10. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content, and these input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time it is executed.

Create a `terraform.tfvars` file in the working directory, with example content as follows:

```hcl
# Network resource configuration
vpc_name              = "tf_test_vpc"
subnet_configurations = [
  {
    subnet_name = "tf_test_main"
  },
  {
    subnet_name = "tf_test_standby"
  },
]

# Security group configuration
security_group_name     = "tf_test_security_group"

# ECS instance configuration
instance_name           = "tf_test_instace"
instance_admin_password = "YourPassword!"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content in this `tfvars` file when executing terraform commands, other names need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="instance_name=my-instance"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 11. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the ECS instance with attached network interface
4. Run `terraform show` to view the created ECS instance with attached network interface details

## Reference Information

- [Huawei Cloud ECS Product Documentation](https://support.huaweicloud.com/ecs/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For ECS Instance with Network Interface](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/ecs/attached-interface)