# Deploy Basic Instance

## Application Scenario

Bare Metal Server (BMS) is a physical server that can be obtained at any time, with high performance and high availability, providing dedicated physical server resources without virtualization overhead, meeting business scenarios with high performance requirements such as high-performance computing, databases, and big data analysis. BMS instances provide complete control over physical servers, support custom operating systems, network configurations, and security policies, and are suitable for application scenarios with strict requirements for performance, security, and compliance. This best practice will introduce how to use Terraform to automatically deploy a basic BMS instance, including the creation of VPC, subnet, security group, and key pair.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [BMS Flavor Query Data Source (data.huaweicloud\_bms\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/bms_flavors)
- [IMS Image Query Data Source (data.huaweicloud\_images\_images)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_images)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [KPS Keypair Resource (huaweicloud\_kps\_keypair)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/kps_keypair)
- [BMS Instance Resource (huaweicloud\_bms\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/bms_instance)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    ├── data.huaweicloud_bms_flavors
    └── huaweicloud_bms_instance

data.huaweicloud_bms_flavors
    └── huaweicloud_bms_instance

data.huaweicloud_images_images
    └── huaweicloud_bms_instance

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_bms_instance

huaweicloud_networking_secgroup
    └── huaweicloud_bms_instance

huaweicloud_kps_keypair
    └── huaweicloud_bms_instance
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Availability Zone Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the query results are used to create BMS instances:

```hcl
variable "availability_zone" {
  description = "The availability zone to which the BMS instance belongs"
  type        = string
  default     = ""
}

# Query all availability zone information in the specified region (defaults to the region specified in the provider block when region parameter is omitted), used to create BMS instances
data "huaweicloud_availability_zones" "test" {
  count = var.availability_zone == "" ? 1 : 0
}
```

**Parameter Description**:

- **count**: The number of data sources to create, used to control whether to execute the availability zone list query data source, only created when `var.availability_zone` is empty (i.e., execute the availability zone list query)

### 3. Create VPC Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC resource:

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

# Create VPC resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted), used to deploy BMS instances
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: The VPC name, assigned by referencing the input variable vpc\_name
- **cidr**: The VPC CIDR block, assigned by referencing the input variable vpc\_cidr, default value is "192.168.0.0/16"

### 4. Create VPC Subnet Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC subnet resource:

```hcl
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

# Create VPC subnet resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted), used to deploy BMS instances
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
}
```

**Parameter Description**:

- **vpc\_id**: The ID of the VPC to which the subnet belongs, referencing the ID of the previously created VPC resource (huaweicloud\_vpc.test)
- **name**: The subnet name, assigned by referencing the input variable subnet\_name
- **cidr**: The subnet CIDR block, assigned by referencing the input variable subnet\_cidr, automatically calculated when the value is an empty string
- **gateway\_ip**: The subnet gateway IP, assigned by referencing the input variable subnet\_gateway\_ip, automatically calculated when the value is an empty string

### 5. Create Security Group Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a security group resource:

```hcl
variable "security_group_name" {
  description = "The name of the security group"
  type        = string
}

# Create security group resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted), used to deploy BMS instances
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: The security group name, assigned by referencing the input variable security\_group\_name
- **delete\_default\_rules**: Whether to delete default rules, set to true

### 6. Query BMS Flavor Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the query results are used to create BMS instances:

```hcl
variable "instance_flavor_id" {
  description = "The flavor ID of the BMS instance"
  type        = string
  default     = ""
}

# Query BMS flavor information that meets specific conditions in the specified region (defaults to the region specified in the provider block when region parameter is omitted), used to create BMS instances
data "huaweicloud_bms_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  cpu_arch         = "aarch64"
  availability_zone = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test[0].names[0], null)
}
```

**Parameter Description**:

- **count**: The number of data sources to create, used to control whether to execute the BMS flavor query data source, only created when `var.instance_flavor_id` is empty (i.e., execute the flavor query)
- **cpu\_arch**: The CPU architecture, set to "aarch64" indicating ARM architecture
- **availability\_zone**: The availability zone, uses the input variable availability\_zone when it is not empty, otherwise assigned based on the return results of the availability zones query data source (data.huaweicloud\_availability\_zones)

### 7. Query BMS Image Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the query results are used to create BMS instances:

```hcl
variable "instance_image_id" {
  description = "The image ID of the BMS instance"
  type        = string
  default     = ""
}

# Query IMS image information that meets specific conditions in the specified region (defaults to the region specified in the provider block when region parameter is omitted), used to create BMS instances
data "huaweicloud_images_images" "test" {
  count = var.instance_image_id == "" ? 1 : 0

  os         = "Huawei Cloud EulerOS"
  image_type = "Ironic"
}
```

**Parameter Description**:

- **count**: The number of data sources to create, used to control whether to execute the image query data source, only created when `var.instance_image_id` is empty (i.e., execute the image query)
- **os**: The operating system type of the image, set to "Huawei Cloud EulerOS" operating system
- **image\_type**: The image type, set to "Ironic" indicating bare metal server image

### 8. Create KPS Keypair Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a KPS keypair resource:

```hcl
variable "keypair_name" {
  description = "The name of the KPS keypair"
  type        = string
}

# Create KPS keypair resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted), used for SSH login to BMS instances
resource "huaweicloud_kps_keypair" "test" {
  name = var.keypair_name
}
```

**Parameter Description**:

- **name**: The keypair name, assigned by referencing the input variable keypair\_name

### 9. Create BMS Instance Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a BMS instance resource:

```hcl
variable "instance_name" {
  description = "The name of the BMS instance"
  type        = string
}

variable "instance_user_id" {
  description = "The user ID of the BMS instance"
  type        = string
}

variable "enterprise_project_id" {
  description = "The ID of the enterprise project to which the BMS instance belongs"
  type        = string
  default     = null
}

variable "instance_tags" {
  description = "The key/value pairs to associate with the BMS instance"
  type        = map(string)
  default     = {}
}

variable "charging_mode" {
  description = "The charging mode of the BMS instance"
  type        = string
  default     = "prePaid"
}

variable "period_unit" {
  description = "The period unit of the BMS instance"
  type        = string
  default     = "month"
}

variable "period" {
  description = "The period of the BMS instance"
  type        = number
  default     = 1
}

variable "auto_renew" {
  description = "The auto renew of the BMS instance"
  type        = string
  default     = "false"
}

# Create BMS instance resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_bms_instance" "test" {
  name                  = var.instance_name
  user_id               = var.instance_user_id
  availability_zone     = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test[0].names[0], null)
  vpc_id                = huaweicloud_vpc.test.id
  flavor_id             = var.instance_flavor_id != "" ? var.instance_flavor_id : try(data.huaweicloud_bms_flavors.test[0].flavors[0].id, null)
  image_id              = var.instance_image_id != "" ? var.instance_image_id : try(data.huaweicloud_images_images.test[0].images[0].id, null)
  security_groups       = [huaweicloud_networking_secgroup.test.id]
  key_pair              = huaweicloud_kps_keypair.test.name
  enterprise_project_id = var.enterprise_project_id
  tags                  = var.instance_tags
  charging_mode         = var.charging_mode
  period_unit           = var.period_unit
  period                = var.period
  auto_renew            = var.auto_renew

  nics {
    subnet_id = huaweicloud_vpc_subnet.test.id
  }

  lifecycle {
    ignore_changes = [
      availability_zone,
      flavor_id,
      image_id,
    ]
  }
}
```

**Parameter Description**:

- **name**: The BMS instance name, assigned by referencing the input variable instance\_name
- **user\_id**: The BMS instance user ID, assigned by referencing the input variable instance\_user\_id
- **availability\_zone**: The availability zone, uses the input variable availability\_zone when it is not empty, otherwise assigned based on the return results of the availability zones query data source (data.huaweicloud\_availability\_zones)
- **vpc\_id**: The VPC ID, referencing the ID of the previously created VPC resource (huaweicloud\_vpc.test)
- **flavor\_id**: The flavor ID, uses the input variable instance\_flavor\_id when it is not empty, otherwise assigned based on the return results of the BMS flavor query data source (data.huaweicloud\_bms\_flavors)
- **image\_id**: The image ID, uses the input variable instance\_image\_id when it is not empty, otherwise assigned based on the return results of the image query data source (data.huaweicloud\_images\_images)
- **security\_groups**: The security group ID list, referencing the ID of the previously created security group resource (huaweicloud\_networking\_secgroup.test)
- **key\_pair**: The keypair name, referencing the name of the previously created KPS keypair resource (huaweicloud\_kps\_keypair.test)
- **enterprise\_project\_id**: The enterprise project ID, assigned by referencing the input variable enterprise\_project\_id, default value is null
- **tags**: The tag key-value pairs, assigned by referencing the input variable instance\_tags, default value is an empty object
- **charging\_mode**: The billing mode, assigned by referencing the input variable charging\_mode, default value is "prePaid"
- **period\_unit**: The billing period unit, assigned by referencing the input variable period\_unit, default value is "month"
- **period**: The billing period, assigned by referencing the input variable period, default value is 1
- **auto\_renew**: Whether to enable auto renewal, assigned by referencing the input variable auto\_renew, default value is "false"
- **nics.subnet\_id**: The subnet ID to which the NIC belongs, referencing the ID of the previously created VPC subnet resource (huaweicloud\_vpc\_subnet.test)

### 10. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# VPC Configuration
vpc_name    = "tf_test_bms_vpc"
vpc_cidr    = "192.168.0.0/16"
subnet_name = "tf_test_bms_subnet"

# Security Group Configuration
security_group_name = "tf_test_bms_security_group"

# KPS Keypair Configuration
keypair_name = "tf_test_kps_keypair"

# BMS Instance Configuration
instance_name    = "tf_test_bms_instance"
instance_user_id = "your_user_id"
enterprise_project_id = "0"
instance_tags = {
  owner = "terraform"
}
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=test-vpc" -var="instance_name=test-instance"`
2. Environment variables: `export TF_VAR_vpc_name=test-vpc`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 11. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the BMS instance
4. Run `terraform show` to view the details of the created BMS instance

> Note: The creation of the BMS instance takes about 30 minutes, please be patient.

## Reference Information

- [Huawei Cloud BMS Product Documentation](https://support.huaweicloud.com/bms/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Basic Instance](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/bms/bms-instance)

# Deploy Reset Instance Password

## Application Scenario

Bare Metal Server (BMS) instance password reset is an important operation and maintenance function provided by the BMS service. When you forget the instance password or need to regularly change the password, you can quickly recover or update the instance login password through the password reset function. Automating password reset operations through Terraform can ensure standardized and secure password management, avoiding security risks that may arise from manual operations. This best practice will introduce how to use Terraform to automatically reset the password of a BMS instance.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [BMS Instance Password Reset Resource (huaweicloud\_bms\_instance\_password\_reset)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/bms_instance_password_reset)

### Resource/Data Source Dependencies

```
huaweicloud_bms_instance_password_reset
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create BMS Instance Password Reset Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a BMS instance password reset resource:

```hcl
variable "bms_instance_id" {
  description = "The ID of the BMS instance"
  type        = string
}

variable "bms_instance_new_password" {
  description = "The new password of the BMS instance"
  type        = string
  sensitive   = true
}

# Create BMS instance password reset resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_bms_instance_password_reset" "test" {
  server_id    = var.bms_instance_id
  new_password = var.bms_instance_new_password
}
```

**Parameter Description**:

- **server\_id**: The BMS instance ID, assigned by referencing the input variable bms\_instance\_id
- **new\_password**: The new password of the BMS instance, assigned by referencing the input variable bms\_instance\_new\_password, which is marked as sensitive information

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, the resource uses input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# BMS Instance Password Reset Configuration
bms_instance_id           = "your_bms_instance_id"
bms_instance_new_password = "your_new_password"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="bms_instance_id=your-instance-id" -var="bms_instance_new_password=your-password"`
2. Environment variables: `export TF_VAR_bms_instance_id=your-instance-id` and `export TF_VAR_bms_instance_new_password=your-password`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to reset the BMS instance password:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start resetting the BMS instance password
4. Run `terraform show` to view the details of the created BMS instance password reset resource

> Note: Destroying this module will not clear the corresponding request record, but will only remove the resource information from the tf state file.

## Reference Information

- [Huawei Cloud BMS Product Documentation](https://support.huaweicloud.com/bms/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Reset Instance Password](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/bms/bms-reset-password)

# Deploy Attach Volume

## Application Scenario

Bare Metal Server (BMS) volume attachment is an important storage expansion function provided by the BMS service. When you need to expand the storage capacity of a BMS instance, you can increase the instance's storage space by attaching a cloud disk. Automating volume attachment operations through Terraform can ensure standardized and consistent storage resource management, improving operational efficiency. This best practice will introduce how to use Terraform to automatically attach a cloud disk to a BMS instance.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [BMS Instance Volume Attachment Resource (huaweicloud\_bms\_volume\_attach)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/bms_volume_attach)

### Resource/Data Source Dependencies

```
huaweicloud_bms_volume_attach
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create BMS Instance Volume Attachment Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a BMS instance volume attachment resource:

```hcl
variable "server_id" {
  description = "The BMS instance ID"
  type        = string
}

variable "volume_id" {
  description = "The ID of the disk to be attached to a BMS instance"
  type        = string
}

variable "device" {
  description = "The mount point"
  type        = string
  default     = null
}

# Create BMS instance volume attachment resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_bms_volume_attach" "test" {
  server_id = var.server_id
  volume_id = var.volume_id
  device    = var.device
}
```

**Parameter Description**:

- **server\_id**: The BMS instance ID, assigned by referencing the input variable server\_id
- **volume\_id**: The ID of the cloud disk to be attached to the BMS instance, assigned by referencing the input variable volume\_id
- **device**: The mount point, such as /dev/sda, /dev/sdb, etc., assigned by referencing the input variable device, default value is null (system automatically assigns)

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, the resource uses input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# BMS Instance Volume Attachment Configuration
server_id = "your_bms_server_id"
volume_id = "your_evs_volume_id"
device    = "/dev/sdb"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="server_id=your-server-id" -var="volume_id=your-volume-id" -var="device=/dev/sdb"`
2. Environment variables: `export TF_VAR_server_id=your-server-id` and `export TF_VAR_volume_id=your-volume-id` and `export TF_VAR_device=/dev/sdb`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to attach a cloud disk to a BMS instance:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start attaching the cloud disk to the BMS instance
4. Run `terraform show` to view the details of the created BMS instance volume attachment resource

> Note: Destroying this resource will detach the volume from the BMS instance.

## Reference Information

- [Huawei Cloud BMS Product Documentation](https://support.huaweicloud.com/bms/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Attach Volume](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/bms/volume-attach)
