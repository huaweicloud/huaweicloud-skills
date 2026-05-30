# Deploy MySQL Single Instance with EIP

## Application Scenario

Huawei Cloud Relational Database Service (RDS) MySQL single instance with EIP binding functionality provides MySQL database services with public network access capabilities, supporting access to database instances from the internet through Elastic IP (EIP). By configuring EIP binding, you can provide public network connectivity for RDS instances, meeting requirements for cross-region access, remote development, data synchronization, and other scenarios.

This best practice is particularly suitable for scenarios that require public network access to MySQL databases, implementing cross-region data synchronization, supporting remote development and testing, such as multi-region application deployment, remote work, third-party system integration, etc. This best practice will introduce how to use Terraform to automatically deploy RDS MySQL single instances with EIP binding, including VPC network, security group, RDS instance, EIP, and EIP binding creation, implementing a complete public network accessible MySQL database solution.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zone Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [RDS Flavor Query Data Source (data.huaweicloud\_rds\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/rds_flavors)
- [Network Port Query Data Source (data.huaweicloud\_networking\_port)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/networking_port)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [Security Group Rule Resource (huaweicloud\_networking\_secgroup\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup_rule)
- [Random Password Resource (random\_password)](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/password)
- [RDS Instance Resource (huaweicloud\_rds\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/rds_instance)
- [Elastic IP Resource (huaweicloud\_vpc\_eip)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_eip)
- [EIP Association Resource (huaweicloud\_vpc\_eip\_associate)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_eip_associate)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    ├── huaweicloud_vpc_subnet
    └── huaweicloud_rds_instance

data.huaweicloud_rds_flavors
    └── huaweicloud_rds_instance

huaweicloud_vpc
    ├── huaweicloud_vpc_subnet
    └── huaweicloud_rds_instance

huaweicloud_vpc_subnet
    ├── huaweicloud_rds_instance
    └── data.huaweicloud_networking_port

huaweicloud_networking_secgroup
    ├── huaweicloud_networking_secgroup_rule
    └── huaweicloud_rds_instance

huaweicloud_networking_secgroup_rule
    └── huaweicloud_rds_instance

random_password
    └── huaweicloud_rds_instance

huaweicloud_rds_instance
    └── data.huaweicloud_networking_port

huaweicloud_vpc_eip
    └── huaweicloud_vpc_eip_associate

data.huaweicloud_networking_port
    └── huaweicloud_vpc_eip_associate
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Prerequisite Resource Preparation

This best practice requires creating prerequisite resources such as VPC, subnet, security group, and RDS instance first. Please prepare according to the following steps in the [Deploy MySQL Single Instance](https://hcbp.gitbook.io/huaweicloud-provider/best-practices/rds/mysql_single_instance) best practice:

- **Step 2**: Create VPC resource
- **Step 3**: Query availability zone information
- **Step 4**: Create VPC subnet
- **Step 5**: Query RDS flavor information
- **Step 6**: Create security group
- **Step 7**: Create security group rules
- **Step 8**: Create random password
- **Step 9**: Create RDS instance

After completing the above steps, continue with the subsequent steps of this best practice.

### 3. Create Elastic IP

Add the following script to the TF file to instruct Terraform to create an Elastic IP resource:

```hcl
variable "associate_eip_address" {
  description = "The EIP address to associate with the RDS instance"
  type        = string
  default     = ""
}

variable "eip_type" {
  description = "The type of the EIP"
  type        = string
  default     = "5_bgp"
}

variable "bandwidth_name" {
  description = "The name for the bandwidth"
  type        = string
  default     = ""

  validation {
    condition     = var.associate_eip_address != "" || var.bandwidth_name != ""
    error_message = "The bandwidth name must be a non-empty string if the EIP address is not provided."
  }
}

variable "bandwidth_size" {
  description = "The size of the bandwidth"
  type        = number
  default     = 5
}

variable "bandwidth_share_type" {
  description = "The share type of the bandwidth"
  type        = string
  default     = "PER"
}

variable "bandwidth_charge_mode" {
  description = "The charge mode of the bandwidth"
  type        = string
  default     = "traffic"
}

# Create an Elastic IP resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
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
}
```

**Parameter Description**:

- **count**: Conditional creation, creates this resource when associate\_eip\_address variable is an empty string
- **publicip**: Public IP configuration block
  - **type**: EIP type, assigned by referencing the input variable eip\_type, default value is "5\_bgp"
- **bandwidth**: Bandwidth configuration block
  - **name**: Bandwidth name, assigned by referencing the input variable bandwidth\_name, default value is empty string
  - **size**: Bandwidth size, assigned by referencing the input variable bandwidth\_size, default value is 5 (Mbps)
  - **share\_type**: Bandwidth sharing type, assigned by referencing the input variable bandwidth\_share\_type, default value is "PER"
  - **charge\_mode**: Bandwidth billing mode, assigned by referencing the input variable bandwidth\_charge\_mode, default value is "traffic"

### 4. Query Network Port Information

Add the following script to the TF file to instruct Terraform to query network port information:

```hcl
# Get all network port information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block) that meets specific conditions, used for EIP binding
data "huaweicloud_networking_port" "test" {
  network_id = huaweicloud_vpc_subnet.test.id
  fixed_ip   = huaweicloud_rds_instance.test.fixed_ip

  depends_on = [
    huaweicloud_rds_instance.test
  ]
}
```

**Parameter Description**:

- **network\_id**: Network ID, referencing the ID of the previously created VPC subnet resource
- **fixed\_ip**: Fixed IP address, referencing the fixed IP of the previously created RDS instance resource
- **depends\_on**: Explicit dependency relationship, ensures RDS instance is created before port query

### 5. Create EIP Association

Add the following script to the TF file to instruct Terraform to create an EIP association resource:

```hcl
# Create an EIP association resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc_eip_associate" "test" {
  public_ip = var.associate_eip_address != "" ? var.associate_eip_address : huaweicloud_vpc_eip.test[0].address
  port_id   = data.huaweicloud_networking_port.test.id
}
```

**Parameter Description**:

- **public\_ip**: Public IP address, prioritizes using associate\_eip\_address variable, uses newly created EIP address if empty
- **port\_id**: Port ID, referencing the ID of the queried network port resource

### 6. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Huawei Cloud authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# VPC network configuration
vpc_name = "tf_test_vpc"

# Subnet configuration
subnet_name = "tf_test_subnet"

# Security group configuration
security_group_name = "tf_test_security_group"

# RDS instance configuration
instance_name = "tf_test_mysql_instance"

# Backup configuration
instance_backup_time_window = "08:00-09:00"
instance_backup_keep_days   = 1

# EIP configuration
bandwidth_name = "tf_test_bandwidth"
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
3. After confirming the resource plan is correct, run `terraform apply` to start creating MySQL single instances with EIP binding
4. Run `terraform show` to view the created MySQL single instance with EIP binding details

## Reference Information

- [Huawei Cloud Relational Database Service Product Documentation](https://support.huaweicloud.com/rds/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For RDS MySQL Single Instance with EIP](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/rds/mysql-instance-associate-eip)
