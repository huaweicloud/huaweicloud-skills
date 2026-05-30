# Deploy Cross Account Migration with Whole Image

## Application Scenario

Image Management Service (IMS) is an image management service provided by Huawei Cloud, supporting image creation, sharing, copying, and other functions. By migrating whole images across accounts, you can share ECS whole images (including system disks and data disks) from one account to another, achieving cross-account whole machine migration and image sharing. This best practice will introduce how to use Terraform to automatically deploy cross-account migration with whole images, including creating ECS instances, CBR vaults, and whole images in the sharer account, sharing images to the accepter account, accepting shared images in the accepter account, and creating new ECS instances using shared images.

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
- [CBR Vault Resource (huaweicloud\_cbr\_vault)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cbr_vault)
- [ECS Whole Image Resource (huaweicloud\_ims\_ecs\_whole\_image)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/ims_ecs_whole_image)
- [Image Share Resource (huaweicloud\_images\_image\_share)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/images_image_share)
- [Image Share Accepter Resource (huaweicloud\_images\_image\_share\_accepter)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/images_image_share_accepter)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    ├── data.huaweicloud_compute_flavors
    │   └── data.huaweicloud_images_images
    │       └── huaweicloud_compute_instance
    └── huaweicloud_cbr_vault
        └── huaweicloud_ims_ecs_whole_image
            └── huaweicloud_images_image_share
                └── huaweicloud_images_image_share_accepter
                    └── huaweicloud_compute_instance

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_compute_instance

huaweicloud_networking_secgroup
    └── huaweicloud_compute_instance

huaweicloud_cbr_vault (accepter)
    └── huaweicloud_images_image_share_accepter
```

> Note: This best practice involves two accounts: sharer account and accepter account. You need to configure two providers in Terraform configuration, corresponding to the authentication information of the two accounts respectively. Whole images need to be stored in CBR vaults, so both the sharer account and accepter account need to create CBR vaults. After image sharing, the accepter account needs to accept the sharing before it can use the shared image to create new ECS instances.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

> Note: This best practice requires configuring two providers, corresponding to the sharer account and accepter account respectively. In the provider configuration, you need to specify the access\_key and secret\_key of the two accounts separately.

### 2. Query Sharer Account Data Sources

Add the following script to the TF file (e.g., main.tf) to query availability zones, ECS flavors, and image information of the sharer account:

```hcl
variable "region_name" {
  description = "The region where resources will be created"
  type        = string
}

variable "instance_flavor_id" {
  description = "The ID of the ECS instance flavor"
  type        = string
  default     = ""
  nullable    = true
}

variable "instance_flavor_performance_type" {
  description = "The performance type of the ECS instance flavor"
  type        = string
  default     = "normal"
}

variable "instance_flavor_cpu_core_count" {
  description = "The CPU core count of the ECS instance flavor"
  type        = number
  default     = 2
}

variable "instance_flavor_memory_size" {
  description = "The memory size of the ECS instance flavor (GB)"
  type        = number
  default     = 4
}

variable "instance_image_id" {
  description = "The ID of the ECS instance image"
  type        = string
  default     = ""
  nullable    = true
}

variable "instance_image_visibility" {
  description = "The visibility of the ECS instance image"
  type        = string
  default     = "public"
}

variable "instance_image_os" {
  description = "The OS of the ECS instance image"
  type        = string
  default     = "Ubuntu"
}

# Get availability zone information of the sharer account in the specified region, used for creating ECS instances
data "huaweicloud_availability_zones" "test" {
  provider = huaweicloud.sharer
}

# Get ECS flavor information of the sharer account in the specified region, used for creating ECS instances
data "huaweicloud_compute_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  provider = huaweicloud.sharer

  availability_zone = try(data.huaweicloud_availability_zones.test.names[0], null)
  performance_type  = var.instance_flavor_performance_type
  cpu_core_count    = var.instance_flavor_cpu_core_count
  memory_size       = var.instance_flavor_memory_size
}

# Get image information of the sharer account in the specified region, used for creating ECS instances
data "huaweicloud_images_images" "test" {
  count = var.instance_image_id == "" ? 1 : 0

  provider = huaweicloud.sharer

  flavor_id  = var.instance_flavor_id != "" ? var.instance_flavor_id : try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, null)
  visibility = var.instance_image_visibility
  os         = var.instance_image_os
}
```

**Parameter Description**:

- **provider**: Specify to use the sharer account provider (huaweicloud.sharer)
- Other parameter descriptions are the same as regular ECS instance creation

### 3. Create Sharer Account Network Resources

Add the following script to the TF file (e.g., main.tf) to create VPC, subnet, and security group of the sharer account:

```hcl
variable "vpc_name" {
  description = "The name of the VPC in sharer account"
  type        = string
}

variable "vpc_cidr" {
  description = "The CIDR block of the VPC in sharer account"
  type        = string
  default     = "192.168.0.0/16"
}

variable "subnet_name" {
  description = "The name of the VPC subnet in sharer account"
  type        = string
}

variable "subnet_cidr" {
  description = "The CIDR block of the VPC subnet in sharer account"
  type        = string
  default     = ""
  nullable    = true
}

variable "subnet_gateway_ip" {
  description = "The gateway IP of the VPC subnet in sharer account"
  type        = string
  default     = ""
  nullable    = true
}

variable "security_group_name" {
  description = "The name of the security group in sharer account"
  type        = string
}

# Create VPC resource of the sharer account in the specified region
resource "huaweicloud_vpc" "test" {
  provider = huaweicloud.sharer

  name = var.vpc_name
  cidr = var.vpc_cidr
}

# Create VPC subnet resource of the sharer account in the specified region
resource "huaweicloud_vpc_subnet" "test" {
  provider = huaweicloud.sharer

  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr != "" ? var.subnet_cidr : cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0)
  gateway_ip = var.subnet_gateway_ip != "" ? var.subnet_gateway_ip : cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1)
}

# Create security group resource of the sharer account in the specified region
resource "huaweicloud_networking_secgroup" "test" {
  provider = huaweicloud.sharer

  name                 = var.security_group_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **provider**: Specify to use the sharer account provider (huaweicloud.sharer)
- Other parameter descriptions are the same as regular VPC, subnet, and security group creation

### 4. Create Sharer Account ECS Instance

Add the following script to the TF file (e.g., main.tf) to create ECS instance of the sharer account:

```hcl
variable "instance_name" {
  description = "The name of the ECS instance to be created in sharer account"
  type        = string
}

variable "administrator_password" {
  description = "The password of the administrator for the ECS instance"
  type        = string
  sensitive   = true
}

variable "instance_data_disks" {
  description = "The data disks of the ECS instance"
  type        = list(object({
    type = string
    size = number
  }))

  default  = []
  nullable = true
}

# Create ECS instance resource of the sharer account in the specified region
resource "huaweicloud_compute_instance" "test" {
  provider = huaweicloud.sharer

  name               = var.instance_name
  availability_zone  = try(data.huaweicloud_availability_zones.test.names[0], null)
  flavor_id          = var.instance_flavor_id != "" ? var.instance_flavor_id : try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, null)
  image_id           = var.instance_image_id != "" ? var.instance_image_id : try(data.huaweicloud_images_images.test[0].images[0].id, null)
  security_group_ids = [huaweicloud_networking_secgroup.test.id]
  admin_pass         = var.administrator_password

  network {
    uuid = huaweicloud_vpc_subnet.test.id
  }

  delete_disks_on_termination = true

  dynamic "data_disks" {
    for_each = var.instance_data_disks

    content {
      type = data_disks.value.type
      size = data_disks.value.size
    }
  }

  lifecycle {
    ignore_changes = [
      availability_zone,
      flavor_id,
      image_id,
      admin_pass,
    ]
  }
}
```

**Parameter Description**:

- **provider**: Specify to use the sharer account provider (huaweicloud.sharer)
- **data\_disks**: Data disk configuration, assigned by referencing input variable instance\_data\_disks, supporting dynamic creation of multiple data disks
- Other parameter descriptions are the same as regular ECS instance creation

### 5. Create CBR Vault

Add the following script to the TF file (e.g., main.tf) to create CBR vault:

```hcl
variable "vault_name" {
  description = "The name of the CBR vault in sharer account"
  type        = string
}

variable "vault_type" {
  description = "The type of the CBR vault"
  type        = string
  default     = "server"
}

variable "vault_consistent_level" {
  description = "The consistent level of the CBR vault"
  type        = string
  default     = "crash_consistent"
}

variable "vault_protection_type" {
  description = "The protection type of the CBR vault"
  type        = string
  default     = "backup"
}

variable "vault_size" {
  description = "The size of the CBR vault in GB"
  type        = number
  default     = 200
}

# Create CBR vault resource of the sharer account in the specified region
resource "huaweicloud_cbr_vault" "test" {
  provider = huaweicloud.sharer

  name             = var.vault_name
  type             = var.vault_type
  consistent_level = var.vault_consistent_level
  protection_type  = var.vault_protection_type
  size             = var.vault_size
}
```

**Parameter Description**:

- **provider**: Specify to use the sharer account provider (huaweicloud.sharer)
- **name**: Vault name, assigned by referencing input variable vault\_name
- **type**: Vault type, assigned by referencing input variable vault\_type, default value is "server"
- **consistent\_level**: Consistency level, assigned by referencing input variable vault\_consistent\_level, default value is "crash\_consistent"
- **protection\_type**: Protection type, assigned by referencing input variable vault\_protection\_type, default value is "backup"
- **size**: Vault capacity (GB), assigned by referencing input variable vault\_size, default value is 200

> Note: Whole images need to be stored in CBR vaults, so you need to create a CBR vault first. The vault capacity needs to be set reasonably according to the disk size of the ECS instance. It is recommended to reserve sufficient space.

### 6. Create ECS Whole Image

Add the following script to the TF file (e.g., main.tf) to create a whole image from ECS instance:

```hcl
variable "whole_image_name" {
  description = "The name of the whole image to be created"
  type        = string
}

variable "whole_image_description" {
  description = "The description of the whole image"
  type        = string
  default     = ""
}

# Create ECS whole image resource of the sharer account in the specified region
resource "huaweicloud_ims_ecs_whole_image" "test" {
  provider = huaweicloud.sharer

  name        = var.whole_image_name
  instance_id = huaweicloud_compute_instance.test.id
  vault_id    = huaweicloud_cbr_vault.test.id
  description = var.whole_image_description
}
```

**Parameter Description**:

- **provider**: Specify to use the sharer account provider (huaweicloud.sharer)
- **name**: Whole image name, assigned by referencing input variable whole\_image\_name
- **instance\_id**: ECS instance ID, assigned by referencing the ECS instance resource
- **vault\_id**: CBR vault ID, assigned by referencing the CBR vault resource
- **description**: Whole image description, assigned by referencing input variable whole\_image\_description, optional parameter

> Note: Whole image creation requires creating from an existing ECS instance, including system disk and data disks. The whole image will be stored in the specified CBR vault. The creation process may take a long time, please be patient.

### 7. Share Image to Accepter Account

Add the following script to the TF file (e.g., main.tf) to share the image to the accepter account:

```hcl
variable "accepter_project_ids" {
  description = "The project IDs of accepter account for image sharing"
  type        = list(string)
}

# Create image share resource of the sharer account in the specified region
resource "huaweicloud_images_image_share" "test" {
  provider = huaweicloud.sharer

  source_image_id    = huaweicloud_ims_ecs_whole_image.test.id
  target_project_ids = var.accepter_project_ids
}
```

**Parameter Description**:

- **provider**: Specify to use the sharer account provider (huaweicloud.sharer)
- **source\_image\_id**: Source image ID, assigned by referencing the whole image resource
- **target\_project\_ids**: Target project ID list, assigned by referencing input variable accepter\_project\_ids

> Note: Image sharing requires specifying the project ID of the accepter account. You can obtain the project ID corresponding to the region by querying project information of the accepter account.

### 8. Accepter Account Accepts Shared Image

Add the following script to the TF file (e.g., main.tf) to accept the shared image in the accepter account:

```hcl
variable "accepter_vault_name" {
  description = "The name of the CBR vault in accepter account"
  type        = string
}

variable "accepter_vault_type" {
  description = "The type of the CBR vault in accepter account"
  type        = string
  default     = "server"
}

variable "accepter_vault_consistent_level" {
  description = "The consistent level of the CBR vault in accepter account"
  type        = string
  default     = "crash_consistent"
}

variable "accepter_vault_protection_type" {
  description = "The protection type of the CBR vault in accepter account"
  type        = string
  default     = "backup"
}

variable "accepter_vault_size" {
  description = "The size of the CBR vault in accepter account in GB"
  type        = number
  default     = 200
}

# Create CBR vault resource of the accepter account in the specified region
resource "huaweicloud_cbr_vault" "accepter" {
  provider = huaweicloud.accepter

  name             = var.accepter_vault_name
  type             = var.accepter_vault_type
  consistent_level = var.accepter_vault_consistent_level
  protection_type  = var.accepter_vault_protection_type
  size             = var.accepter_vault_size
}

# Create image share accepter resource of the accepter account in the specified region
resource "huaweicloud_images_image_share_accepter" "accepter" {
  provider = huaweicloud.accepter

  image_id = huaweicloud_ims_ecs_whole_image.test.id
  vault_id = huaweicloud_cbr_vault.accepter.id

  depends_on = [huaweicloud_images_image_share.test]
}
```

**Parameter Description**:

- **provider**: Specify to use the accepter account provider (huaweicloud.accepter)
- **image\_id**: Shared image ID, assigned by referencing the whole image resource
- **vault\_id**: CBR vault ID, assigned by referencing the accepter account CBR vault resource
- **depends\_on**: Explicit dependency relationship, ensuring to accept sharing after image sharing is created

> Note: The accepter account needs to create a CBR vault to store the accepted shared image. After accepting the shared image, you can create new ECS instances using the shared image in the accepter account.

### 9. Create Accepter Account ECS Instance (Optional)

Add the following script to the TF file (e.g., main.tf) to create a new ECS instance using shared image in the accepter account:

```hcl
variable "accepter_instance_name" {
  description = "The name of the new ECS instance to be created in accepter account"
  type        = string
}

# Get availability zone information of the accepter account in the specified region
data "huaweicloud_availability_zones" "accepter" {
  provider = huaweicloud.accepter
}

# Get ECS flavor information of the accepter account in the specified region
data "huaweicloud_compute_flavors" "accepter" {
  provider = huaweicloud.accepter

  availability_zone = try(data.huaweicloud_availability_zones.accepter.names[0], null)
  performance_type  = var.instance_flavor_performance_type
  cpu_core_count    = var.instance_flavor_cpu_core_count
  memory_size       = var.instance_flavor_memory_size
}

# Create VPC resource of the accepter account in the specified region
resource "huaweicloud_vpc" "accepter" {
  provider = huaweicloud.accepter

  name = var.vpc_name
  cidr = var.vpc_cidr
}

# Create VPC subnet resource of the accepter account in the specified region
resource "huaweicloud_vpc_subnet" "accepter" {
  provider = huaweicloud.accepter

  vpc_id     = huaweicloud_vpc.accepter.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.accepter.cidr, 8, 0) : var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.accepter.cidr, 8, 0), 1) : var.subnet_gateway_ip
}

# Create security group resource of the accepter account in the specified region
resource "huaweicloud_networking_secgroup" "accepter" {
  provider = huaweicloud.accepter

  name                 = var.security_group_name
  delete_default_rules = true
}

# Create ECS instance resource of the accepter account in the specified region (using shared image)
resource "huaweicloud_compute_instance" "accepter" {
  provider = huaweicloud.accepter

  depends_on = [huaweicloud_images_image_share_accepter.accepter]

  name               = var.accepter_instance_name
  availability_zone  = try(data.huaweicloud_availability_zones.accepter.names[0], null)
  flavor_id          = try(data.huaweicloud_compute_flavors.accepter.flavors[0].id, null)
  image_id           = huaweicloud_images_image_share_accepter.accepter.image_id
  security_group_ids = [huaweicloud_networking_secgroup.accepter.id]
  admin_pass         = var.administrator_password

  network {
    uuid = huaweicloud_vpc_subnet.accepter.id
  }

  lifecycle {
    ignore_changes = [
      availability_zone,
      flavor_id,
      image_id,
      admin_pass,
    ]
  }
}
```

**Parameter Description**:

- **provider**: Specify to use the accepter account provider (huaweicloud.accepter)
- **image\_id**: Image ID, assigned by referencing the image share accepter resource, used to create ECS instance using shared image
- **depends\_on**: Explicit dependency relationship, ensuring to create ECS instance after accepting shared image
- Other parameter descriptions are the same as regular ECS instance creation

> Note: The accepter account can create new ECS instances using shared images. When creating ECS instances, specify the image\_id parameter to use the shared image. ECS instances created using shared images will include the system disk and data disk contents of the original ECS instance.

### 10. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication Variables
region_name = "cn-north-4"

# Sharer Account Variables
access_key = "Your_sharer_access_key"
secret_key = "Your_sharer_secret_key"

# Accepter Account Variables
accepter_access_key = "Your_accepter_access_key"
accepter_secret_key = "Your_accepter_secret_key"

# Sharer Account Resource Configuration
vpc_name               = "tf_test_whole_image_vpc"
subnet_name            = "tf_test_whole_image_subnet"
security_group_name    = "tf_test_whole_image_sg"
instance_name          = "tf_test_whole_image_ecs"
administrator_password = "YourPassword@12!"
instance_data_disks    = [
  {
    size = 10
    type = "SAS"
  }
]

vault_name             = "tf_test_sharer_vault"
whole_image_name       = "tf_test_whole_image"
accepter_project_ids   = ["your_accepter_project_id"]

# Accepter Account Resource Configuration
accepter_vault_name    = "tf_test_accepter_vault"
accepter_instance_name = "tf_test_accepter_instance"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially:
   - `region_name` needs to be set to the region where resources are located
   - `access_key` and `secret_key` need to be set to the authentication information of the sharer account
   - `accepter_access_key` and `accepter_secret_key` need to be set to the authentication information of the accepter account
   - `accepter_project_ids` needs to be set to the project ID list of the accepter account
   - Resource names, network configuration, and other parameters of the sharer account and accepter account need to be set according to actual requirements
   - `instance_data_disks` can configure data disks for ECS instances, supporting multiple data disks
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="region_name=cn-north-4" -var="vpc_name=my-vpc"`
2. Environment variables: `export TF_VAR_region_name=cn-north-4` and `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. This best practice requires configuring authentication information for two accounts. Please ensure that the access\_key and secret\_key of both accounts are correctly configured. Whole image creation may take a long time, please be patient.

### 11. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create cross-account migration with whole image:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating resources of the sharer account and accepter account
4. Run `terraform show` to view the details of the created cross-account migration with whole image

> Note: Cross-account migration with whole image requires authentication information for two accounts. Please ensure that the provider configuration of both accounts is correct. Whole image creation may take a long time, please be patient. After image sharing, the accepter account needs to accept the sharing before it can use the shared image. ECS instances created using shared images will include the system disk and data disk contents of the original ECS instance.

## Reference Information

- [Huawei Cloud IMS Product Documentation](https://support.huaweicloud.com/ims/index.html)
- [Huawei Cloud CBR Product Documentation](https://support.huaweicloud.com/cbr/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Cross Account Migration with Whole Image](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/ims/cross-account-migration-with-whole-image)
