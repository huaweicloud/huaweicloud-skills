# Deploy Basic Instance

## Application Scenario

Elastic Cloud Server (ECS) is a fundamental computing component composed of CPU, memory, operating system, and cloud disks. After an Elastic Cloud Server is successfully created, you can use it in the cloud just like using your own local PC or physical server. Huawei Cloud provides various types of Elastic Cloud Servers to meet different usage scenarios. Before creating, you need to confirm the specification type, image type, disk type, and other parameters of the Elastic Cloud Server according to the actual application scenario, and select appropriate network parameters and security group rules. This best practice will introduce how to use Terraform to automatically deploy a basic ECS instance, including VPC, subnet, and security group creation.

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
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Availability Zones Required for ECS Instance Resource Creation Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the query results are used to create ECS instances:

```hcl
# Get all availability zone information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create ECS instances
data "huaweicloud_availability_zones" "test" {}
```

**Parameter Description**: This data source requires no additional parameters and queries all available availability zone information in the current region by default.

### 3. Query Flavors Required for ECS Instance Resource Creation Through Data Source

Add the following script to the TF file to instruct Terraform to query ECS flavors that meet the conditions:

```hcl
# Get all ECS flavor information that meets specific conditions under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create ECS instances
data "huaweicloud_compute_flavors" "test" {
  availability_zone = data.huaweicloud_availability_zones.test.names[0]
  performance_type  = "normal"
  cpu_core_count    = 2
  memory_size       = 4
}
```

**Parameter Description**:

- **availability\_zone**: Availability zone where the flavor is located, using the first availability zone from the previously queried availability zone data source
- **performance\_type**: Flavor type, set to "normal" for standard type
- **cpu\_core\_count**: CPU core count, set to 2 cores
- **memory\_size**: Memory size (GB), set to 4GB

### 4. Query Images Required for ECS Instance Resource Creation Through Data Source

Add the following script to the TF file to instruct Terraform to query images that meet the conditions:

```hcl
# Get all IMS image information that meets specific conditions under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create ECS instances
data "huaweicloud_images_images" "test" {
  flavor_id  = try(data.huaweicloud_compute_flavors.test.flavors[0].id, "")
  visibility = "public"
  os         = "Ubuntu"
}
```

**Parameter Description**:

- **flavor\_id**: Flavor ID supported by the image, using the first flavor ID from the previously queried flavor data source, using empty string if flavor data source query fails
- **visibility**: Image visibility, set to "public" for public images
- **os**: Operating system type of the image, set to "Ubuntu" operating system

### 5. Create VPC Resource

Add the following script to the TF file to instruct Terraform to create a VPC resource:

```hcl
variable "vpc_name" {
  description = "The name of the VPC"
  type        = string
}

# Create a VPC resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to deploy ECS instances
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = "192.168.0.0/16"
}
```

**Parameter Description**:

- **name**: VPC name, assigned by referencing the input variable vpc\_name
- **cidr**: VPC CIDR block, set to "192.168.0.0/16" network segment

### 6. Create VPC Subnet Resource

Add the following script to the TF file to instruct Terraform to create a VPC subnet resource:

```hcl
variable "subnet_name" {
  description = "The name of the subnet"
  type        = string
}

# Create a VPC subnet resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to deploy ECS instances
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0)
  gateway_ip = cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1)
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID that the subnet belongs to, referencing the ID of the VPC resource created earlier
- **name**: Subnet name, assigned by referencing the input variable subnet\_name
- **cidr**: Subnet CIDR block, using cidrsubnet function to divide a subnet segment from the VPC's CIDR block
- **gateway\_ip**: Subnet gateway IP, using cidrhost function to get the first IP address from the subnet segment as the gateway IP

### 7. Create Security Group Resource

Add the following script to the TF file to instruct Terraform to create a security group resource:

```hcl
variable "security_group_name" {
  description = "The name of the security group"
  type        = string
}

# Create a security group resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to deploy ECS instances
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: Security group name, assigned by referencing the input variable security\_group\_name
- **delete\_default\_rules**: Whether to delete default rules, set to true to delete default rules

### 8. Create ECS Instance Resource

Add the following script to the TF file to instruct Terraform to create an ECS instance resource:

```hcl
variable "instance_name" {
  description = "The name of the ECS instance"
  type        = string
}

variable "administrator_password" {
  description = "The password of the administrator"
  type        = string
}

# Create an ECS instance resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_compute_instance" "basic" {
  name               = var.instance_name
  availability_zone  = data.huaweicloud_availability_zones.test.names[0]
  flavor_id          = try(data.huaweicloud_compute_flavors.test.flavors[0].id, "")
  image_id           = try(data.huaweicloud_images_images.test.images[0].id, "")
  security_group_ids = [
    huaweicloud_networking_secgroup.test.id
  ]

  network {
    uuid = huaweicloud_vpc_subnet.test.id
  }
  
  admin_pass = var.administrator_password

  lifecycle {
    ignore_changes = [
      admin_pass,
    ]
  }
}
```

**Parameter Description**:

- **name**: ECS instance name, assigned by referencing the input variable instance\_name
- **availability\_zone**: Availability zone where the ECS instance is located, using the first availability zone from the previously queried availability zone data source
- **flavor\_id**: Flavor ID used by the ECS instance, using the first flavor ID from the previously queried flavor data source, using empty string if flavor data source query fails
- **image\_id**: Image ID used by the ECS instance, using the first image ID from the previously queried image data source, using empty string if image data source query fails
- **security\_group\_ids**: List of security group IDs associated with the ECS instance, using the ID of the security group resource created earlier
- **network**: Network configuration block, specifying the network that the ECS instance connects to
  - **uuid**: Network unique identifier, using the ID of the subnet resource created earlier
- **admin\_pass**: Administrator password of the ECS instance, assigned by referencing the input variable administrator\_password
- **lifecycle**: Lifecycle configuration block, used to control resource lifecycle behavior
  - **ignore\_changes**: Specify attribute changes to ignore in subsequent applications, set to ignore admin\_pass changes

### 9. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Huawei Cloud authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# VPC configuration
vpc_name = "tf_test_vpc"

# Subnet configuration
subnet_name = "tf_test_subnet"

# Security group configuration
security_group_name = "tf_test_secgroup"

# ECS instance configuration
instance_name = "tf_test_instance"
administrator_password = "YourPassword123!"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="instance_name=my-instance"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 10. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating the ECS instance
4. Run `terraform show` to view the details of the created ECS instance

## Reference Information

- [Huawei Cloud ECS Product Documentation](https://support.huaweicloud.com/ecs/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For ECS Basic Instance](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/ecs/basic)