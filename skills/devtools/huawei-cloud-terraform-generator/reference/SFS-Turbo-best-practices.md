# Deploy Turbo File System

## Application Scenario

Huawei Cloud Scalable File Service (SFS Turbo) file system functionality provides high-performance, highly available file storage services, specifically designed for high-performance computing (HPC), AI/ML workloads, and large-scale data processing scenarios. SFS Turbo supports NFS and CIFS protocols, providing high IOPS, low-latency file access capabilities, meeting the storage requirements of enterprise applications.

This best practice is particularly suitable for scenarios that require high-performance file storage, support large-scale concurrent access, implement data sharing and collaboration, such as HPC clusters, machine learning training, big data analysis, containerized application storage, etc. This best practice will introduce how to use Terraform to automatically deploy SFS Turbo file systems, including VPC network, security group, and SFS Turbo file system creation, implementing a complete file storage solution.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zone Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [SFS Turbo File System Resource (huaweicloud\_sfs\_turbo)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/sfs_turbo)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── huaweicloud_sfs_turbo

huaweicloud_vpc
    ├── huaweicloud_vpc_subnet
    └── huaweicloud_sfs_turbo

huaweicloud_vpc_subnet
    └── huaweicloud_sfs_turbo

huaweicloud_networking_secgroup
    └── huaweicloud_sfs_turbo
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Availability Zone Information

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to query availability zone information:

```hcl
# Get all available availability zone information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create SFS Turbo file systems
data "huaweicloud_availability_zones" "test" {}
```

**Parameter Description**:

- This data source requires no additional parameters and automatically queries all availability zones in the current region

### 3. Create VPC Network

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

# Create a VPC resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: VPC name, assigned by referencing the input variable vpc\_name
- **cidr**: VPC CIDR block, assigned by referencing the input variable vpc\_cidr, default value is "192.168.0.0/16"

### 4. Create VPC Subnet

Add the following script to the TF file to instruct Terraform to create a VPC subnet resource:

```hcl
variable "subnet_name" {
  description = "The name of the subnet"
  type        = string
}

variable "subnet_cidr" {
  description = "The CIDR block of the subnet"
  type        = string
  default     = ""
  nullable    = false
}

variable "subnet_gateway_ip" {
  description = "The gateway IP of the subnet"
  type        = string
  default     = ""
  nullable    = false
}

# Create a VPC subnet resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID that the subnet belongs to, referencing the ID of the previously created VPC resource
- **name**: Subnet name, assigned by referencing the input variable subnet\_name
- **cidr**: Subnet CIDR block, automatically calculated if subnet\_cidr is empty, otherwise uses subnet\_cidr value
- **gateway\_ip**: Subnet gateway IP, automatically calculated if subnet\_gateway\_ip is empty, otherwise uses subnet\_gateway\_ip value

### 5. Create Security Group

Add the following script to the TF file to instruct Terraform to create a security group resource:

```hcl
variable "security_group_name" {
  description = "The name of the security group"
  type        = string
}

# Create a security group resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: Security group name, assigned by referencing the input variable security\_group\_name
- **delete\_default\_rules**: Whether to delete default rules, set to true to delete default security group rules

### 6. Create SFS Turbo File System

Add the following script to the TF file to instruct Terraform to create an SFS Turbo file system resource:

```hcl
variable "turbo_name" {
  description = "The name of the SFS Turbo file system"
  type        = string
  default     = ""
}

variable "turbo_size" {
  description = "The capacity of the SFS Turbo file system"
  type        = number
  default     = 1228
}

variable "turbo_share_proto" {
  description = "The protocol of the SFS Turbo file system"
  type        = string
  default     = "NFS"
}

variable "turbo_share_type" {
  description = "The type of the SFS Turbo file system"
  type        = string
  default     = "STANDARD"
}

variable "turbo_hpc_bandwidth" {
  description = "The bandwidth specification of the SFS Turbo file system"
  type        = string
  default     = ""
}

variable "turbo_tags" {
  description = "The tags of the SFS Turbo file system"
  type        = map(string)
  default     = {}
}

variable "turbo_backup_id" {
  description = "The ID of the backup"
  type        = string
  default     = ""
}

variable "enterprise_project_id" {
  description = "The enterprise project ID of the SFS Turbo file system"
  type        = string
  default     = null
}

variable "charging_mode" {
  description = "The charging mode of the SFS Turbo file system"
  type        = string
  default     = "postPaid"
}

variable "period_unit" {
  description = "The period unit of the SFS Turbo file system"
  type        = string
  default     = null
}

variable "period" {
  description = "The period of the SFS Turbo file system"
  type        = number
  default     = null
}

variable "auto_renew" {
  description = "The auto renew of the SFS Turbo file system"
  type        = string
  default     = "false"
}

# Create an SFS Turbo file system resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_sfs_turbo" "test" {
  vpc_id                = huaweicloud_vpc.test.id
  subnet_id             = huaweicloud_vpc_subnet.test.id
  security_group_id     = huaweicloud_networking_secgroup.test.id
  availability_zone     = try(data.huaweicloud_availability_zones.test.names[0], null)
  name                  = var.turbo_name
  size                  = var.turbo_size
  share_proto           = var.turbo_share_proto
  share_type            = var.turbo_share_type
  hpc_bandwidth         = var.turbo_hpc_bandwidth
  tags                  = var.turbo_tags
  backup_id             = var.turbo_backup_id
  enterprise_project_id = var.enterprise_project_id
  charging_mode         = var.charging_mode
  period_unit           = var.period_unit
  period                = var.period
  auto_renew            = var.auto_renew

  # If you want to change some of the following parameters, you need to remove the corresponding fields from "lifecycle.ignore_changes".
  lifecycle {
    ignore_changes = [
      availability_zone,
    ]
  }
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID, referencing the ID of the previously created VPC resource
- **subnet\_id**: Subnet ID, referencing the ID of the previously created VPC subnet resource
- **security\_group\_id**: Security group ID, referencing the ID of the previously created security group resource
- **availability\_zone**: Availability zone, using the first queried availability zone
- **name**: SFS Turbo file system name, assigned by referencing the input variable turbo\_name, default value is empty string
- **size**: File system capacity, assigned by referencing the input variable turbo\_size, default value is 1228 (GB)
- **share\_proto**: Sharing protocol, assigned by referencing the input variable turbo\_share\_proto, default value is "NFS"
- **share\_type**: Sharing type, assigned by referencing the input variable turbo\_share\_type, default value is "STANDARD"
- **hpc\_bandwidth**: HPC bandwidth specification, assigned by referencing the input variable turbo\_hpc\_bandwidth, default value is empty string
- **tags**: File system tags, assigned by referencing the input variable turbo\_tags, default value is empty map
- **backup\_id**: Backup ID, assigned by referencing the input variable turbo\_backup\_id, default value is empty string
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing the input variable enterprise\_project\_id, default value is null
- **charging\_mode**: Billing mode, assigned by referencing the input variable charging\_mode, default value is "postPaid"
- **period\_unit**: Billing period unit, assigned by referencing the input variable period\_unit, default value is null
- **period**: Billing period, assigned by referencing the input variable period, default value is null
- **auto\_renew**: Whether to auto-renew, assigned by referencing the input variable auto\_renew, default value is "false"
- **lifecycle.ignore\_changes**: Lifecycle management, ignores changes to availability\_zone

### 7. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Huawei Cloud authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# VPC network configuration
vpc_name = "tf_test_turbo"

# Subnet configuration
subnet_name = "tf_test_turbo"

# Security group configuration
security_group_name = "tf_test_turbo"

# SFS Turbo file system configuration
turbo_name          = "tf_test_turbo_demo"
turbo_share_type    = "HPC"
turbo_hpc_bandwidth = "40M"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="turbo_name=my-turbo"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 8. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating file systems
4. Run `terraform show` to view the created file system details

## Reference Information

- [Huawei Cloud Scalable File Service Product Documentation](https://support.huaweicloud.com/sfsturbo/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For SFS Turbo File System](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/sfs-turbo/turbo-file-system)

# Deploy OBS Target Configuration

## Application Scenario

Huawei Cloud Scalable File Service (SFS Turbo) OBS target configuration functionality allows users to automatically export data from SFS Turbo file systems to OBS object storage, implementing data backup, archiving, and long-term storage. By configuring OBS targets, you can achieve automated management of file system data, cost optimization, and data flow across storage services.

This best practice is particularly suitable for scenarios that require backing up SFS Turbo data to OBS, implementing data archiving, building hybrid storage architectures, such as HPC data processing, machine learning model storage, big data analysis result preservation, etc. This best practice will introduce how to use Terraform to automatically deploy SFS Turbo OBS target configuration, including VPC network, security group, OBS storage bucket, SFS Turbo file system, and OBS target configuration creation, implementing a complete file storage and object storage integration solution.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zone Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [OBS Storage Bucket Resource (huaweicloud\_obs\_bucket)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket)
- [SFS Turbo File System Resource (huaweicloud\_sfs\_turbo)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/sfs_turbo)
- [SFS Turbo OBS Target Resource (huaweicloud\_sfs\_turbo\_obs\_target)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/sfs_turbo_obs_target)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── huaweicloud_sfs_turbo

huaweicloud_vpc
    ├── huaweicloud_vpc_subnet
    ├── huaweicloud_sfs_turbo
    └── huaweicloud_sfs_turbo_obs_target

huaweicloud_vpc_subnet
    └── huaweicloud_sfs_turbo

huaweicloud_networking_secgroup
    └── huaweicloud_sfs_turbo

huaweicloud_obs_bucket
    └── huaweicloud_sfs_turbo_obs_target

huaweicloud_sfs_turbo
    └── huaweicloud_sfs_turbo_obs_target
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Availability Zone Information

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to query availability zone information:

```hcl
# Get all available availability zone information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create SFS Turbo file systems
data "huaweicloud_availability_zones" "test" {}
```

**Parameter Description**:

- This data source requires no additional parameters and automatically queries all availability zones in the current region

### 3. Create VPC Network

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

# Create a VPC resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: VPC name, assigned by referencing the input variable vpc\_name
- **cidr**: VPC CIDR block, assigned by referencing the input variable vpc\_cidr, default value is "192.168.0.0/16"

### 4. Create VPC Subnet

Add the following script to the TF file to instruct Terraform to create a VPC subnet resource:

```hcl
variable "subnet_name" {
  description = "The name of the subnet"
  type        = string
}

variable "subnet_cidr" {
  description = "The CIDR block of the subnet"
  type        = string
  default     = ""
  nullable    = false
}

variable "subnet_gateway_ip" {
  description = "The gateway IP of the subnet"
  type        = string
  default     = ""
  nullable    = false
}

# Create a VPC subnet resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID that the subnet belongs to, referencing the ID of the previously created VPC resource
- **name**: Subnet name, assigned by referencing the input variable subnet\_name
- **cidr**: Subnet CIDR block, automatically calculated if subnet\_cidr is empty, otherwise uses subnet\_cidr value
- **gateway\_ip**: Subnet gateway IP, automatically calculated if subnet\_gateway\_ip is empty, otherwise uses subnet\_gateway\_ip value

### 5. Create Security Group

Add the following script to the TF file to instruct Terraform to create a security group resource:

```hcl
variable "security_group_name" {
  description = "The name of the security group"
  type        = string
}

# Create a security group resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: Security group name, assigned by referencing the input variable security\_group\_name
- **delete\_default\_rules**: Whether to delete default rules, set to true to delete default security group rules

### 6. Create OBS Storage Bucket

Add the following script to the TF file to instruct Terraform to create an OBS storage bucket resource:

```hcl
variable "target_bucket_name" {
  description = "The name of the OBS bucket"
  type        = string
  default     = ""
}

# Create an OBS storage bucket resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_obs_bucket" "test" {
  bucket        = var.target_bucket_name
  acl           = "private"
  force_destroy = true
}
```

**Parameter Description**:

- **bucket**: OBS storage bucket name, assigned by referencing the input variable target\_bucket\_name
- **acl**: Bucket ACL policy, set to "private" for private access
- **force\_destroy**: Whether to force delete the bucket, set to true to allow deletion of non-empty buckets

### 7. Create SFS Turbo File System

Add the following script to the TF file to instruct Terraform to create an SFS Turbo file system resource:

```hcl
variable "turbo_name" {
  description = "The name of the SFS Turbo file system"
  type        = string
  default     = ""
}

variable "turbo_size" {
  description = "The capacity of the SFS Turbo file system"
  type        = number
  default     = 1228
}

variable "turbo_share_proto" {
  description = "The protocol of the SFS Turbo file system"
  type        = string
  default     = "NFS"
}

variable "turbo_share_type" {
  description = "The type of the SFS Turbo file system"
  type        = string
  default     = "HPC"
}

variable "turbo_hpc_bandwidth" {
  description = "The bandwidth specification of the SFS Turbo file system"
  type        = string
  default     = "40M"
}

# Create an SFS Turbo file system resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_sfs_turbo" "test" {
  vpc_id            = huaweicloud_vpc.test.id
  subnet_id         = huaweicloud_vpc_subnet.test.id
  security_group_id = huaweicloud_networking_secgroup.test.id
  availability_zone = try(data.huaweicloud_availability_zones.test.names[0], null)
  name              = var.turbo_name
  size              = var.turbo_size
  share_proto       = var.turbo_share_proto
  share_type        = var.turbo_share_type
  hpc_bandwidth     = var.turbo_hpc_bandwidth
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID, referencing the ID of the previously created VPC resource
- **subnet\_id**: Subnet ID, referencing the ID of the previously created VPC subnet resource
- **security\_group\_id**: Security group ID, referencing the ID of the previously created security group resource
- **availability\_zone**: Availability zone, using the first queried availability zone
- **name**: SFS Turbo file system name, assigned by referencing the input variable turbo\_name, default value is empty string
- **size**: File system capacity, assigned by referencing the input variable turbo\_size, default value is 1228 (GB)
- **share\_proto**: Sharing protocol, assigned by referencing the input variable turbo\_share\_proto, default value is "NFS"
- **share\_type**: Sharing type, assigned by referencing the input variable turbo\_share\_type, default value is "HPC"
- **hpc\_bandwidth**: HPC bandwidth specification, assigned by referencing the input variable turbo\_hpc\_bandwidth, default value is "40M"

### 8. Create SFS Turbo OBS Target Configuration

Add the following script to the TF file to instruct Terraform to create an SFS Turbo OBS target resource:

```hcl
variable "target_file_path" {
  description = "The linkage directory name of the OBS target"
  type        = string
  default     = "testDir"
}

variable "target_obs_endpoint" {
  description = "The domain name of the region where the OBS bucket located"
  type        = string
  default     = "obs.cn-north-4.myhuaweicloud.com"
}

variable "target_events" {
  description = "The type of the data automatically exported to the OBS bucket"
  type        = list(string)
  default     = []
}

variable "target_prefix" {
  description = "The prefix to be matched in the storage backend"
  type        = string
  default     = ""
}

variable "target_suffix" {
  description = "The suffix to be matched in the storage backend"
  type        = string
  default     = ""
}

variable "target_file_mode" {
  description = "The permissions on the imported file"
  type        = string
  default     = ""
}

variable "target_dir_mode" {
  description = "The permissions on the imported directory"
  type        = string
  default     = ""
}

variable "target_uid" {
  description = "The ID of the user who owns the imported object"
  type        = number
  default     = 0
}

variable "target_gid" {
  description = "The ID of the user group to which the imported object belongs"
  type        = number
  default     = 0
}

# Create an SFS Turbo OBS target resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_sfs_turbo_obs_target" "test" {
  share_id         = huaweicloud_sfs_turbo.test.id
  file_system_path = var.target_file_path

  obs {
    bucket   = huaweicloud_obs_bucket.test.id
    endpoint = var.target_obs_endpoint

    policy {
      auto_export_policy {
        events = var.target_events
        prefix = var.target_prefix
        suffix = var.target_suffix
      }
    }

    attributes {
      file_mode = var.target_file_mode
      dir_mode  = var.target_dir_mode
      uid       = var.target_uid
      gid       = var.target_gid
    }
  }
}
```

**Parameter Description**:

- **share\_id**: SFS Turbo file system ID, referencing the ID of the previously created SFS Turbo file system resource
- **file\_system\_path**: OBS target linkage directory name, assigned by referencing the input variable target\_file\_path, default value is "testDir"
- **obs**: OBS configuration block
  - **bucket**: OBS storage bucket ID, referencing the ID of the previously created OBS storage bucket resource
  - **endpoint**: Domain name of the region where the OBS bucket is located, assigned by referencing the input variable target\_obs\_endpoint, default value is "obs.cn-north-4.myhuaweicloud.com"
  - **policy**: Policy configuration block
    - **auto\_export\_policy**: Auto-export policy configuration block
      - **events**: Type of data automatically exported to OBS bucket, assigned by referencing the input variable target\_events, default value is empty list
      - **prefix**: Prefix to be matched in the storage backend, assigned by referencing the input variable target\_prefix, default value is empty string
      - **suffix**: Suffix to be matched in the storage backend, assigned by referencing the input variable target\_suffix, default value is empty string
  - **attributes**: Attributes configuration block
    - **file\_mode**: Permissions on the imported file, assigned by referencing the input variable target\_file\_mode, default value is empty string
    - **dir\_mode**: Permissions on the imported directory, assigned by referencing the input variable target\_dir\_mode, default value is empty string
    - **uid**: ID of the user who owns the imported object, assigned by referencing the input variable target\_uid, default value is 0
    - **gid**: ID of the user group to which the imported object belongs, assigned by referencing the input variable target\_gid, default value is 0

### 9. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Huawei Cloud authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# VPC network configuration
vpc_name = "tf_test_tareget"

# Subnet configuration
subnet_name = "tf_test_target"

# Security group configuration
security_group_name = "tf_test_target"

# OBS storage bucket configuration
target_bucket_name = "tf-test-target"

# SFS Turbo file system configuration
turbo_name = "tf_test_target_demo"

# OBS target configuration
target_obs_endpoint = "obs.cn-north-4.myhuaweicloud.com"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="turbo_name=my-turbo"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 10. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating OBS target configuration
4. Run `terraform show` to view the created OBS target configuration details

## Reference Information

- [Huawei Cloud Scalable File Service Product Documentation](https://support.huaweicloud.com/sfsturbo/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For SFS Turbo OBS Target Configuration](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/sfs-turbo/obs-target)

# Deploy Permission Rule

## Application Scenario

Huawei Cloud Scalable File Service (SFS Turbo) permission rule functionality allows users to configure access control rules for SFS Turbo file systems, defining which IP addresses or network segments can access the file system and the permission levels for access. By configuring permission rules, you can implement secure access control, network isolation, and permission management for file systems.

This best practice is particularly suitable for scenarios that require controlling SFS Turbo file system access permissions, implementing network security isolation, managing multi-user access, such as multi-tenant environments, security-sensitive applications, enterprise file sharing, etc. This best practice will introduce how to use Terraform to automatically deploy SFS Turbo permission rules, including VPC network, security group, SFS Turbo file system, and permission rule creation, implementing a complete file system access control solution.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zone Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [SFS Turbo File System Resource (huaweicloud\_sfs\_turbo)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/sfs_turbo)
- [SFS Turbo Permission Rule Resource (huaweicloud\_sfs\_turbo\_perm\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/sfs_turbo_perm_rule)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── huaweicloud_sfs_turbo

huaweicloud_vpc
    ├── huaweicloud_vpc_subnet
    └── huaweicloud_sfs_turbo

huaweicloud_vpc_subnet
    └── huaweicloud_sfs_turbo

huaweicloud_networking_secgroup
    └── huaweicloud_sfs_turbo

huaweicloud_sfs_turbo
    └── huaweicloud_sfs_turbo_perm_rule
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Availability Zone Information

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to query availability zone information:

```hcl
# Get all available availability zone information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create SFS Turbo file systems
data "huaweicloud_availability_zones" "test" {}
```

**Parameter Description**:

- This data source requires no additional parameters and automatically queries all availability zones in the current region

### 3. Create VPC Network

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

# Create a VPC resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: VPC name, assigned by referencing the input variable vpc\_name
- **cidr**: VPC CIDR block, assigned by referencing the input variable vpc\_cidr, default value is "192.168.0.0/16"

### 4. Create VPC Subnet

Add the following script to the TF file to instruct Terraform to create a VPC subnet resource:

```hcl
variable "subnet_name" {
  description = "The name of the subnet"
  type        = string
}

variable "subnet_cidr" {
  description = "The CIDR block of the subnet"
  type        = string
  default     = ""
  nullable    = false
}

variable "subnet_gateway_ip" {
  description = "The gateway IP of the subnet"
  type        = string
  default     = ""
  nullable    = false
}

# Create a VPC subnet resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID that the subnet belongs to, referencing the ID of the previously created VPC resource
- **name**: Subnet name, assigned by referencing the input variable subnet\_name
- **cidr**: Subnet CIDR block, automatically calculated if subnet\_cidr is empty, otherwise uses subnet\_cidr value
- **gateway\_ip**: Subnet gateway IP, automatically calculated if subnet\_gateway\_ip is empty, otherwise uses subnet\_gateway\_ip value

### 5. Create Security Group

Add the following script to the TF file to instruct Terraform to create a security group resource:

```hcl
variable "security_group_name" {
  description = "The name of the security group"
  type        = string
}

# Create a security group resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: Security group name, assigned by referencing the input variable security\_group\_name
- **delete\_default\_rules**: Whether to delete default rules, set to true to delete default security group rules

### 6. Create SFS Turbo File System

Add the following script to the TF file to instruct Terraform to create an SFS Turbo file system resource:

```hcl
variable "turbo_availability_zone" {
  description = "The availability zone to which the SFS Turbo belongs"
  type        = string
  default     = ""
  nullable    = false
}

variable "turbo_name" {
  description = "The name of the SFS Turbo file system"
  type        = string
}

variable "turbo_size" {
  description = "The capacity of the SFS Turbo file system"
  type        = number
  default     = 500
}

variable "turbo_share_proto" {
  description = "The protocol of the SFS Turbo file system"
  type        = string
  default     = "NFS"
}

variable "turbo_share_type" {
  description = "The type of the SFS Turbo file system"
  type        = string
  default     = "STANDARD"
}

variable "turbo_hpc_bandwidth" {
  description = "The bandwidth specification of the SFS Turbo file system"
  type        = string
  default     = ""
}

# Create an SFS Turbo file system resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_sfs_turbo" "test" {
  vpc_id            = huaweicloud_vpc.test.id
  subnet_id         = huaweicloud_vpc_subnet.test.id
  security_group_id = huaweicloud_networking_secgroup.test.id
  availability_zone = var.turbo_availability_zone != "" ? var.turbo_availability_zone : try(data.huaweicloud_availability_zones.test.names[0], null)
  name              = var.turbo_name
  size              = var.turbo_size
  share_proto       = var.turbo_share_proto
  share_type        = var.turbo_share_type
  hpc_bandwidth     = var.turbo_hpc_bandwidth
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID, referencing the ID of the previously created VPC resource
- **subnet\_id**: Subnet ID, referencing the ID of the previously created VPC subnet resource
- **security\_group\_id**: Security group ID, referencing the ID of the previously created security group resource
- **availability\_zone**: Availability zone, prioritizes using turbo\_availability\_zone variable, uses the first queried availability zone if empty
- **name**: SFS Turbo file system name, assigned by referencing the input variable turbo\_name
- **size**: File system capacity, assigned by referencing the input variable turbo\_size, default value is 500 (GB)
- **share\_proto**: Sharing protocol, assigned by referencing the input variable turbo\_share\_proto, default value is "NFS"
- **share\_type**: Sharing type, assigned by referencing the input variable turbo\_share\_type, default value is "STANDARD"
- **hpc\_bandwidth**: HPC bandwidth specification, assigned by referencing the input variable turbo\_hpc\_bandwidth, default value is empty string

### 7. Create SFS Turbo Permission Rules

Add the following script to the TF file to instruct Terraform to create an SFS Turbo permission rule resource:

```hcl
variable "rule_ip_cidr" {
  description = "The IP address or network segment of the authorized object"
  type        = string
  default     = "192.168.0.0/16"
}

variable "rule_rw_type" {
  description = "The read and write permissions for the authorized object"
  type        = string
  default     = "rw"
}

variable "rule_user_type" {
  description = "The access permissions of the system users of the authorized object to the file system"
  type        = string
  default     = "no_root_squash"
}

# Create an SFS Turbo permission rule resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_sfs_turbo_perm_rule" "test" {
  share_id  = huaweicloud_sfs_turbo.test.id
  ip_cidr   = var.rule_ip_cidr
  rw_type   = var.rule_rw_type
  user_type = var.rule_user_type
}
```

**Parameter Description**:

- **share\_id**: SFS Turbo file system ID, referencing the ID of the previously created SFS Turbo file system resource
- **ip\_cidr**: IP address or network segment of the authorized object, assigned by referencing the input variable rule\_ip\_cidr, default value is "192.168.0.0/16"
- **rw\_type**: Read and write permissions for the authorized object, assigned by referencing the input variable rule\_rw\_type, default value is "rw" (read-write permissions)
- **user\_type**: Access permissions of the system users of the authorized object to the file system, assigned by referencing the input variable rule\_user\_type, default value is "no\_root\_squash" (no root user restrictions)

### 8. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Huawei Cloud authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# VPC network configuration
vpc_name = "tf_test_perm_rule"

# Subnet configuration
subnet_name = "tf_test_perm_rule"

# Security group configuration
security_group_name = "tf_test_perm_rule"

# SFS Turbo file system configuration
turbo_name = "tf_test_perm_rule_demo"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="turbo_name=my-turbo"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 9. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating permission rules
4. Run `terraform show` to view the created permission rule details

## Reference Information

- [Huawei Cloud Scalable File Service Product Documentation](https://support.huaweicloud.com/sfsturbo/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For SFS Turbo Permission Rule](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/sfs-turbo/permission-rule)
