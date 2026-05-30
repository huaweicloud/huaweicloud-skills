# Deploy Instance with UserData Script Execution

## Application Scenario

Elastic Cloud Server (ECS) is a fundamental computing component composed of CPU, memory, operating system, and cloud disks, providing a reliable, secure, flexible, and efficient computing environment for your applications. ECS service supports multiple instance specifications and operating systems, meeting computing requirements for different scales and scenarios.

UserData script execution is an important function of ECS instances, allowing custom scripts to be automatically executed during instance startup, implementing automated configuration, software installation, service startup, and other operations. This configuration is suitable for scenarios such as automated deployment, environment initialization, and application configuration. This best practice will introduce how to use Terraform to automatically deploy ECS instances with UserData script execution, including network environment creation, security group configuration, key pair creation, instance creation, and script execution.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [ECS Flavors Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)
- [Images Query Data Source (data.huaweicloud\_images\_images)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_images)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [ECS Instance Resource (huaweicloud\_compute\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_instance)
- [Key Pair Resource (huaweicloud\_kps\_keypair)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/kps_keypair)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones.test
    └── huaweicloud_compute_instance.test

data.huaweicloud_compute_flavors.test
    └── huaweicloud_compute_instance.test

data.huaweicloud_images_images.test
    └── huaweicloud_compute_instance.test

huaweicloud_vpc.test
    └── huaweicloud_vpc_subnet.test
        └── huaweicloud_compute_instance.test

huaweicloud_networking_secgroup.test
    └── huaweicloud_compute_instance.test

huaweicloud_kps_keypair.test
    └── huaweicloud_compute_instance.test
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Prerequisite Resource Preparation

This best practice requires creating prerequisite resources such as VPC, subnet, security group, and ECS instance first. Please follow the following steps from the [Deploy Basic Elastic Cloud Server](https://hcbp.gitbook.io/huaweicloud-provider/best-practices/ecs/simple_instance) best practice for preparation:

- **Step 2**: Query availability zones required for ECS instance resource creation through data source
- **Step 3**: Query flavors required for ECS instance resource creation through data source
- **Step 4**: Query images required for ECS instance resource creation through data source
- **Step 5**: Create VPC resource
- **Step 6**: Create VPC subnet resource
- **Step 7**: Create security group resource

After completing the above steps, continue with the subsequent steps of this best practice.

### 3. Create Key Pair

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a key pair resource:

```hcl
variable "keypair_name" {
  description = "Key pair name"
  type        = string
}

variable "keypair_public_key" {
  description = "Public key of the key pair"
  type        = string
  default     = null
}

# Create a key pair resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_kps_keypair" "test" {
  name       = var.keypair_name
  public_key = var.keypair_public_key
}
```

**Parameter Description**:

- **name**: Key pair name, assigned by referencing the input variable keypair\_name
- **public\_key**: Public key content, assigned by referencing the input variable keypair\_public\_key, system automatically generates if null

### 4. Create ECS Instance and Configure UserData

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an ECS instance resource and configure UserData:

```hcl
variable "instance_name" {
  description = "ECS instance name"
  type        = string
}

variable "instance_user_data" {
  description = "UserData script for the ECS instance"
  type        = string
}

variable "security_group_ids" {
  description = "Security group ID list for the ECS instance"
  type        = list(string)
  default     = []
  nullable    = false
}

variable "security_group_names" {
  description = "Security group name list for the ECS instance"
  type        = list(string)
  default     = []
  nullable    = false
}

# Create an ECS instance resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_compute_instance" "test" {
  name               = var.instance_name
  image_id           = var.instance_image_id == "" ? try(data.huaweicloud_images_images.test[0].images[0].id, null) : var.instance_image_id
  flavor_id          = var.instance_flavor_id == "" ? try(data.huaweicloud_compute_flavors.test[0].ids[0], null) : var.instance_flavor_id
  security_group_ids = length(var.security_group_ids) == 0 ? huaweicloud_networking_secgroup.test[*].id : var.security_group_ids
  key_pair           = huaweicloud_kps_keypair.test.name
  availability_zone  = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test[0].names[0], null) : var.availability_zone
  user_data          = var.instance_user_data

  network {
    uuid = huaweicloud_vpc_subnet.test.id
  }

  # If you modify the following fields, please remove the corresponding fields from the lifecycle block
  lifecycle {
    ignore_changes = [
      image_id,
      flavor_id,
      availability_zone
    ]
  }
}
```

**Parameter Description**:

- **name**: Instance name, assigned by referencing the input variable instance\_name
- **image\_id**: Image ID, prioritizes using input variable, uses first result from image list query data source if empty
- **flavor\_id**: Flavor ID, prioritizes using input variable, uses first result from ECS flavor list query data source if empty
- **security\_group\_ids**: Security group ID list, prioritizes using input variable, uses created security group resource ID list if empty
- **key\_pair**: Key pair name, assigned by referencing the key pair resource (huaweicloud\_kps\_keypair.test) name
- **availability\_zone**: Availability zone, prioritizes using input variable, uses first result from availability zone list query data source if empty
- **user\_data**: UserData script, assigned by referencing the input variable instance\_user\_data
- **network.uuid**: Network UUID, assigned by referencing the VPC subnet resource (huaweicloud\_vpc\_subnet.test) ID
- **lifecycle.ignore\_changes**: Lifecycle ignore changes, ignoring changes to image\_id, flavor\_id, and availability\_zone

### 5. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Network configuration
vpc_name    = "tf_test_vpc_with_ecs_instance"
vpc_cidr    = "192.168.0.0/16"
subnet_name = "tf_test_subnet_with_ecs_instance"

# Security group configuration
security_group_names = ["tf_test_seg1_with_ecs_instance", "tf_test_seg2_with_ecs_instance"]

# ECS instance configuration
instance_name        = "tf_test_with_userdata"
keypair_name         = "tf_test_keypair_with_ecs_instance"
instance_user_data   = <<EOF
#!/bin/bash
echo "Hello, World!" > /home/terraform.txt
EOF
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

### 6. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating ECS instances with UserData script execution
4. Run `terraform show` to view the created ECS instance

## Reference Information

- [Huawei Cloud ECS Product Documentation](https://support.huaweicloud.com/ecs/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For ECS Instance with UserData Script Execution](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/ecs/instance-with-userdata)