# Deploy Cross Account Migration with Data Image

## Application Scenario

Image Management Service (IMS) is an image management service provided by Huawei Cloud, supporting image creation, sharing, copying, and other functions. By migrating data images across accounts, you can share data disk images from one account to another, achieving cross-account data migration and image sharing. This best practice will introduce how to use Terraform to automatically deploy cross-account migration with data images, including creating ECS instances, data disks, and data images in the sharer account, sharing images to the accepter account, accepting shared images in the accepter account, and creating data disks using shared images.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Data Source (huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [ECS Flavors Data Source (huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)
- [Images Data Source (huaweicloud\_images\_images)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_images)
- [Projects Data Source (huaweicloud\_identity\_auth\_projects)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/identity_auth_projects)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [ECS Instance Resource (huaweicloud\_compute\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_instance)
- [EVS Volume Resource (huaweicloud\_evs\_volume)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/evs_volume)
- [Data Disk Image Resource (huaweicloud\_ims\_evs\_data\_image)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/ims_evs_data_image)
- [Image Share Resource (huaweicloud\_images\_image\_share)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/images_image_share)
- [Image Share Accepter Resource (huaweicloud\_images\_image\_share\_accepter)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/images_image_share_accepter)
- [EVS Volume V3 Resource (huaweicloud\_evsv3\_volume)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/evsv3_volume)
- [Volume Attach Resource (huaweicloud\_compute\_volume\_attach)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_volume_attach)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    ├── data.huaweicloud_compute_flavors
    │   └── data.huaweicloud_images_images
    │       └── huaweicloud_compute_instance
    └── huaweicloud_evs_volume
        └── huaweicloud_ims_evs_data_image
            └── huaweicloud_images_image_share
                └── huaweicloud_images_image_share_accepter
                    └── huaweicloud_evsv3_volume
                        └── huaweicloud_compute_volume_attach

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_compute_instance

huaweicloud_networking_secgroup
    └── huaweicloud_compute_instance

data.huaweicloud_identity_auth_projects
    └── huaweicloud_images_image_share
```

> Note: This best practice involves two accounts: sharer account and accepter account. You need to configure two providers in Terraform configuration, corresponding to the authentication information of the two accounts respectively. After image sharing, the accepter account needs to accept the sharing before it can use the shared image.

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

# Get availability zone information of the sharer account in the specified region, used for creating ECS instances and data disks
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
  description = "The name of the VPC"
  type        = string
}

variable "vpc_cidr" {
  description = "The CIDR block of the VPC"
  type        = string
  default     = "192.168.0.0/16"
}

variable "enterprise_project_id" {
  description = "The ID of the enterprise project"
  type        = string
  default     = null
}

variable "subnet_name" {
  description = "The name of the VPC subnet"
  type        = string
}

variable "subnet_cidr" {
  description = "The CIDR block of the VPC subnet"
  type        = string
  default     = ""
  nullable    = true
}

variable "subnet_gateway_ip" {
  description = "The gateway IP of the VPC subnet"
  type        = string
  default     = ""
  nullable    = true
}

variable "security_group_name" {
  description = "The name of the security group"
  type        = string
}

# Create VPC resource of the sharer account in the specified region
resource "huaweicloud_vpc" "test" {
  provider = huaweicloud.sharer

  name                  = var.vpc_name
  cidr                  = var.vpc_cidr
  enterprise_project_id = var.enterprise_project_id
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

  name                  = var.security_group_name
  delete_default_rules  = true
  enterprise_project_id = var.enterprise_project_id
}
```

**Parameter Description**:

- **provider**: Specify to use the sharer account provider (huaweicloud.sharer)
- Other parameter descriptions are the same as regular VPC, subnet, and security group creation

### 4. Create Sharer Account ECS Instance and Data Disk

Add the following script to the TF file (e.g., main.tf) to create ECS instance and data disk of the sharer account:

```hcl
variable "instance_name" {
  description = "The name of the ECS instance to be created"
  type        = string
}

variable "administrator_password" {
  description = "The password of the administrator for the ECS instance"
  type        = string
  sensitive   = true
}

variable "data_volume_name" {
  description = "The name of the data volume to be created and attached to ECS instance"
  type        = string
}

variable "data_volume_type" {
  description = "The type of the data volume"
  type        = string
  default     = "SAS"
}

variable "data_volume_size" {
  description = "The size of the data volume in GB"
  type        = number
  default     = 10
}

# Create ECS instance resource of the sharer account in the specified region
resource "huaweicloud_compute_instance" "test" {
  provider = huaweicloud.sharer

  name                        = var.instance_name
  availability_zone           = try(data.huaweicloud_availability_zones.test.names[0], null)
  flavor_id                   = var.instance_flavor_id != "" ? var.instance_flavor_id : try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, null)
  image_id                    = var.instance_image_id != "" ? var.instance_image_id : try(data.huaweicloud_images_images.test[0].images[0].id, null)
  security_group_ids          = [huaweicloud_networking_secgroup.test.id]
  admin_pass                  = var.administrator_password
  delete_disks_on_termination = true
  enterprise_project_id       = var.enterprise_project_id

  network {
    uuid = huaweicloud_vpc_subnet.test.id
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

# Create data disk resource of the sharer account in the specified region
resource "huaweicloud_evs_volume" "test" {
  provider = huaweicloud.sharer

  name              = var.data_volume_name
  server_id         = huaweicloud_compute_instance.test.id
  availability_zone = try(data.huaweicloud_availability_zones.test.names[0], null)
  volume_type       = var.data_volume_type
  size              = var.data_volume_size
}
```

**Parameter Description**:

- **provider**: Specify to use the sharer account provider (huaweicloud.sharer)
- **server\_id**: ECS instance ID to which the data disk is attached, assigned by referencing the ECS instance resource
- Other parameter descriptions are the same as regular ECS instance and data disk creation

### 5. Create Data Disk Image

Add the following script to the TF file (e.g., main.tf) to create a data image from the data disk:

```hcl
variable "data_image_name" {
  description = "The name of the data disk image to be created"
  type        = string
}

variable "data_image_description" {
  description = "The description of the data disk image"
  type        = string
  default     = ""
}

# Create data disk image resource of the sharer account in the specified region
resource "huaweicloud_ims_evs_data_image" "test" {
  provider = huaweicloud.sharer

  name                  = var.data_image_name
  volume_id             = huaweicloud_evs_volume.test.id
  description           = var.data_image_description
  enterprise_project_id = var.enterprise_project_id
}
```

**Parameter Description**:

- **provider**: Specify to use the sharer account provider (huaweicloud.sharer)
- **name**: Data image name, assigned by referencing input variable data\_image\_name
- **volume\_id**: Data disk ID, assigned by referencing the data disk resource
- **description**: Data image description, assigned by referencing input variable data\_image\_description, optional parameter
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing input variable enterprise\_project\_id, optional parameter

> Note: Data disk image creation requires creating from an existing data disk. Ensure that the data disk has been created and contains the data that needs to be migrated.

### 6. Share Image to Accepter Account

Add the following script to the TF file (e.g., main.tf) to share the image to the accepter account:

```hcl
# Get project information of the accepter account in the specified region, used for image sharing
data "huaweicloud_identity_auth_projects" "test" {
  provider = huaweicloud.accepter
}

locals {
  accepter_project_ids = [for project in data.huaweicloud_identity_auth_projects.test.projects : project.id if project.name == var.region_name]
}

# Create image share resource of the sharer account in the specified region
resource "huaweicloud_images_image_share" "test" {
  provider = huaweicloud.sharer

  source_image_id    = huaweicloud_ims_evs_data_image.test.id
  target_project_ids = local.accepter_project_ids
}
```

**Parameter Description**:

- **provider**: Specify to use the sharer account provider (huaweicloud.sharer)
- **source\_image\_id**: Source image ID, assigned by referencing the data disk image resource
- **target\_project\_ids**: Target project ID list, assigned by querying project information of the accepter account

> Note: Image sharing requires specifying the project ID of the accepter account. By querying project information of the accepter account, you can obtain the project ID corresponding to the region.

### 7. Accepter Account Accepts Shared Image

Add the following script to the TF file (e.g., main.tf) to accept the shared image in the accepter account:

```hcl
# Create image share accepter resource of the accepter account in the specified region
resource "huaweicloud_images_image_share_accepter" "test" {
  provider = huaweicloud.accepter

  image_id = huaweicloud_ims_evs_data_image.test.id

  depends_on = [huaweicloud_images_image_share.test]
}
```

**Parameter Description**:

- **provider**: Specify to use the accepter account provider (huaweicloud.accepter)
- **image\_id**: Shared image ID, assigned by referencing the data disk image resource
- **depends\_on**: Explicit dependency relationship, ensuring to accept sharing after image sharing is created

> Note: The accepter account needs to accept the shared image before it can use it. After accepting the shared image, you can create data disks using the shared image in the accepter account.

### 8. Create Accepter Account Resources (Optional)

Add the following script to the TF file (e.g., main.tf) to create ECS instance and data disk using shared image in the accepter account:

```hcl
variable "accepter_vpc_name" {
  description = "The name of the VPC in accepter account"
  type        = string
}

variable "accepter_vpc_cidr" {
  description = "The CIDR block of the VPC in accepter account"
  type        = string
  default     = "192.168.0.0/16"
}

variable "accepter_subnet_name" {
  description = "The name of the VPC subnet in accepter account"
  type        = string
}

variable "accepter_security_group_name" {
  description = "The name of the security group in accepter account"
  type        = string
}

variable "accepter_instance_flavor_id" {
  description = "The ID of the ECS instance flavor in accepter account"
  type        = string
  default     = ""
  nullable    = true
}

variable "accepter_instance_image_id" {
  description = "The ID of the ECS instance image in accepter account"
  type        = string
  default     = ""
  nullable    = true
}

variable "accepter_instance_name" {
  description = "The name of the ECS instance to be created in accepter account (optional, for creating new instance)"
  type        = string
}

variable "accepter_data_volume_name" {
  description = "The name of the data volume to be created from shared image in accepter account"
  type        = string
}

variable "accepter_data_volume_type" {
  description = "The type of the data volume in accepter account"
  type        = string
  default     = "SAS"
}

variable "accepter_data_volume_size" {
  description = "The size of the data volume in accepter account in GB"
  type        = number
  default     = 20
}

# Get availability zone information of the accepter account in the specified region
data "huaweicloud_availability_zones" "accepter" {
  provider = huaweicloud.accepter
}

# Create VPC resource of the accepter account in the specified region
resource "huaweicloud_vpc" "accepter" {
  provider = huaweicloud.accepter

  name = var.accepter_vpc_name
  cidr = var.accepter_vpc_cidr
}

# Create VPC subnet resource of the accepter account in the specified region
resource "huaweicloud_vpc_subnet" "accepter" {
  provider = huaweicloud.accepter

  vpc_id     = huaweicloud_vpc.accepter.id
  name       = var.accepter_subnet_name
  cidr       = cidrsubnet(huaweicloud_vpc.accepter.cidr, 8, 0)
  gateway_ip = cidrhost(cidrsubnet(huaweicloud_vpc.accepter.cidr, 8, 0), 1)
}

# Create security group resource of the accepter account in the specified region
resource "huaweicloud_networking_secgroup" "accepter" {
  provider = huaweicloud.accepter

  name                 = var.accepter_security_group_name
  delete_default_rules = true
}

# Get ECS flavor information of the accepter account in the specified region
data "huaweicloud_compute_flavors" "accepter" {
  count = var.accepter_instance_flavor_id == "" ? 1 : 0

  provider = huaweicloud.accepter

  availability_zone = try(data.huaweicloud_availability_zones.accepter.names[0], null)
  performance_type  = var.instance_flavor_performance_type
  cpu_core_count    = var.instance_flavor_cpu_core_count
  memory_size       = var.instance_flavor_memory_size
}

# Get image information of the accepter account in the specified region
data "huaweicloud_images_images" "accepter" {
  count = var.accepter_instance_image_id == "" ? 1 : 0

  provider = huaweicloud.accepter

  flavor_id  = var.accepter_instance_flavor_id != "" ? var.accepter_instance_flavor_id : try(data.huaweicloud_compute_flavors.accepter[0].flavors[0].id, null)
  visibility = var.instance_image_visibility
  os         = var.instance_image_os
}

# Create ECS instance resource of the accepter account in the specified region
resource "huaweicloud_compute_instance" "accepter" {
  provider = huaweicloud.accepter

  name                        = var.accepter_instance_name
  availability_zone           = try(data.huaweicloud_availability_zones.accepter.names[0], null)
  flavor_id                   = var.accepter_instance_flavor_id != "" ? var.accepter_instance_flavor_id : try(data.huaweicloud_compute_flavors.accepter[0].flavors[0].id, null)
  image_id                    = var.accepter_instance_image_id != "" ? var.accepter_instance_image_id : try(data.huaweicloud_images_images.accepter[0].images[0].id, null)
  security_group_ids          = [huaweicloud_networking_secgroup.accepter.id]
  admin_pass                  = var.administrator_password
  delete_disks_on_termination = true

  network {
    uuid = huaweicloud_vpc_subnet.accepter.id
  }

  depends_on = [huaweicloud_images_image_share_accepter.test]

  lifecycle {
    ignore_changes = [
      availability_zone,
      flavor_id,
      image_id,
      admin_pass,
    ]
  }
}

# Create data disk resource of the accepter account in the specified region (using shared image)
resource "huaweicloud_evsv3_volume" "accepter" {
  provider = huaweicloud.accepter

  name              = var.accepter_data_volume_name
  availability_zone = try(data.huaweicloud_availability_zones.accepter.names[0], null)
  volume_type       = var.accepter_data_volume_type
  size              = var.accepter_data_volume_size
  image_id          = huaweicloud_images_image_share_accepter.test.image_id
}

# Create volume attach resource of the accepter account in the specified region
resource "huaweicloud_compute_volume_attach" "accepter" {
  provider = huaweicloud.accepter

  instance_id = huaweicloud_compute_instance.accepter.id
  volume_id   = huaweicloud_evsv3_volume.accepter.id
}
```

**Parameter Description**:

- **provider**: Specify to use the accepter account provider (huaweicloud.accepter)
- **image\_id**: Data disk image ID, assigned by referencing the image share accepter resource, used to create data disk using shared image
- **depends\_on**: Explicit dependency relationship, ensuring to create ECS instance and data disk after accepting shared image
- Other parameter descriptions are the same as regular ECS instance and data disk creation

> Note: The accepter account can create data disks using shared images. When creating data disks, specify the image\_id parameter to use the shared image. After the data disk is created, it can be attached to ECS instances for use.

### 9. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication Variables
region_name = "cn-north-4"

# Sharer Account Variables
access_key = "your_sharer_access_key"
secret_key = "your_sharer_secret_key"

# Accepter Account Variables
accepter_access_key = "your_accepter_access_key"
accepter_secret_key = "your_accepter_secret_key"

# Sharer Account Resource Configuration
vpc_name                     = "tf_test_whole_image_vpc"
subnet_name                  = "tf_test_whole_image_subnet"
security_group_name          = "tf_test_whole_image_sg"
instance_name                = "tf_test_whole_image_ecs"
administrator_password       = "YourPassword@12!"
data_volume_name             = "tf_test_data_volume"
data_image_name              = "tf_test_data_image"

# Accepter Account Resource Configuration
accepter_vpc_name            = "tf_test_accepter_vpc"
accepter_subnet_name         = "tf_test_accepter_subnet"
accepter_security_group_name = "tf_test_accepter_sg"
accepter_instance_name       = "tf_test_accepter_instance"
accepter_data_volume_name    = "tf_test_accepter_data_volume"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially:
   - `region_name` needs to be set to the region where resources are located
   - `access_key` and `secret_key` need to be set to the authentication information of the sharer account
   - `accepter_access_key` and `accepter_secret_key` need to be set to the authentication information of the accepter account
   - Resource names, network configuration, and other parameters of the sharer account and accepter account need to be set according to actual requirements
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="region_name=cn-north-4" -var="vpc_name=my-vpc"`
2. Environment variables: `export TF_VAR_region_name=cn-north-4` and `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. This best practice requires configuring authentication information for two accounts. Please ensure that the access\_key and secret\_key of both accounts are correctly configured.

### 10. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create cross-account migration with data image:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating resources of the sharer account and accepter account
4. Run `terraform show` to view the details of the created cross-account migration with data image

> Note: Cross-account migration with data image requires authentication information for two accounts. Please ensure that the provider configuration of both accounts is correct. After image sharing, the accepter account needs to accept the sharing before it can use the shared image. Data disk image creation requires creating from an existing data disk. Ensure that the data disk has been created and contains the data that needs to be migrated.

## Reference Information

- [Huawei Cloud IMS Product Documentation](https://support.huaweicloud.com/ims/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Cross Account Migration with Data Image](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/ims/cross-account-migration-with-data-image)