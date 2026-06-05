# Deploy Instance with EIP

## Application Scenario

Elastic Cloud Server (ECS) is a fundamental computing component composed of CPU, memory, operating system, and cloud disks, providing a reliable, secure, flexible, and efficient computing environment for your applications. ECS service supports multiple instance specifications and operating systems, meeting computing requirements for different scales and scenarios.

ECS instances with EIP binding are important functions in ECS service. By binding Elastic Public IP (EIP) to ECS instances, instances can directly access the internet and can also be accessed by internet users. This configuration is suitable for scenarios such as web servers, API servers, database servers that require public network access. This best practice will introduce how to use Terraform to automatically deploy ECS instances with EIP binding, including network environment creation, security group configuration, instance creation, and EIP binding.

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
- [Security Group Rule Resource (huaweicloud\_networking\_secgroup\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup_rule)
- [ECS Instance Resource (huaweicloud\_compute\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_instance)
- [EIP Resource (huaweicloud\_vpc\_eip)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_eip)
- [EIP Binding Resource (huaweicloud\_compute\_eip\_associate)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_eip_associate)

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
    ├── huaweicloud_networking_secgroup_rule.test
    └── huaweicloud_compute_instance.test

huaweicloud_vpc_eip.test
    └── huaweicloud_compute_eip_associate.test

huaweicloud_compute_instance.test
    └── huaweicloud_compute_eip_associate.test
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
- **Step 8**: Create ECS instance resource

After completing the above steps, continue with the subsequent steps of this best practice.

### 3. Create Security Group Rules

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create security group rule resources:

```hcl
# Create a security group rule resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_networking_secgroup_rule" "test" {
  security_group_id = huaweicloud_networking_secgroup.test.id
  direction         = "egress"
  ethertype         = "IPv4"
  remote_ip_prefix  = "0.0.0.0/0"
  priority          = 1
}
```

**Parameter Description**:

- **security\_group\_id**: Security group ID, assigned by referencing the security group resource (huaweicloud\_networking\_secgroup.test) ID
- **direction**: Direction, set to "egress" for outbound rules
- **ethertype**: Ethernet type, set to "IPv4" for IPv4 protocol
- **remote\_ip\_prefix**: Remote IP prefix, set to "0.0.0.0/0" to allow access to all IPs
- **priority**: Priority, set to 1 for high priority

### 4. Create EIP

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an EIP resource:

```hcl
variable "associate_eip_address" {
  description = "EIP address to bind to the ECS instance"
  type        = string
  default     = ""
}

variable "eip_type" {
  description = "EIP type"
  type        = string
  default     = "5_bgp"
}

variable "bandwidth_name" {
  description = "EIP bandwidth name"
  type        = string
  default     = ""
}

variable "bandwidth_size" {
  description = "Bandwidth size"
  type        = number
  default     = 5
}

variable "bandwidth_share_type" {
  description = "Bandwidth share type"
  type        = string
  default     = "PER"
}

variable "bandwidth_charge_mode" {
  description = "Bandwidth charge mode"
  type        = string
  default     = "traffic"
}

# Create an EIP resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc_eip" "test" {
  count = var.associate_eip_address == "" ? 1 : 0

  publicip {
    type = var.eip_type
  }

  bandwidth {
    name        = var.bandwidth_name
    size        = var.bandwidth_size
    share_type  = var.bandwidth_share_type
    charge_mode = var.bandwidth_charge_mode
  }

  lifecycle {
    precondition {
      condition     = var.associate_eip_address != "" || var.bandwidth_name != ""
      error_message = "The bandwidth name must be a non-empty string if the EIP address is not provided."
    }
  }
}
```

**Parameter Description**:

- **count**: Resource creation count, used to control whether to create EIP resource, only creates resource when `var.associate_eip_address` is empty
- **publicip.type**: Public IP type, assigned by referencing the input variable eip\_type
- **bandwidth.name**: Bandwidth name, assigned by referencing the input variable bandwidth\_name
- **bandwidth.size**: Bandwidth size, assigned by referencing the input variable bandwidth\_size
- **bandwidth.share\_type**: Bandwidth share type, assigned by referencing the input variable bandwidth\_share\_type
- **bandwidth.charge\_mode**: Bandwidth charge mode, assigned by referencing the input variable bandwidth\_charge\_mode
- **lifecycle.precondition**: Lifecycle precondition, ensuring bandwidth name is not empty

### 5. Bind EIP

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an EIP binding resource:

```hcl
# Create an EIP binding resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_compute_eip_associate" "test" {
  instance_id = huaweicloud_compute_instance.test.id
  public_ip   = var.associate_eip_address == "" ? try(huaweicloud_vpc_eip.test[0].address, null) : var.associate_eip_address
}
```

**Parameter Description**:

- **public\_ip**: Public IP address, prioritizes using input variable, uses EIP resource address if empty
- **instance\_id**: Instance ID, assigned by referencing the ECS instance resource (huaweicloud\_compute\_instance.test) ID

### 6. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Network configuration
vpc_name    = "tf_test_vpc"
vpc_cidr    = "192.168.0.0/16"
subnet_name = "tf_test_subnet"

# Security group configuration
security_group_name = "tf_test_security_group"

# ECS instance configuration
instance_name          = "tf_test_instance"
administrator_password = "YourPasswordInput!"

# EIP configuration
eip_type               = "5_bgp"
bandwidth_name         = "tf_test_bandwidth"
bandwidth_size         = 5
bandwidth_share_type   = "PER"
bandwidth_charge_mode  = "traffic"
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

### 7. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating ECS instances with EIP binding
4. Run `terraform show` to view the created ECS instances with EIP binding

## Reference Information

- [Huawei Cloud ECS Product Documentation](https://support.huaweicloud.com/ecs/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For ECS Instance with EIP](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/ecs/instance-associate-eip)
