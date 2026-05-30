# Deploy Cloud Volume

## Application Scenario

Elastic Volume Service (EVS) is a high-performance, highly reliable, and scalable block storage service provided by Huawei Cloud, providing persistent storage for ECS instances. EVS supports multiple storage types, including SSD, SAS, SATA, etc., meeting storage requirements for different business scenarios.

Cloud volumes are the core resources of the EVS service, providing persistent storage capabilities and supporting multiple storage types and performance configurations. Through cloud volumes, enterprises can provide reliable data storage for ECS instances, supporting advanced functions such as data backup, snapshots, and expansion. Cloud volumes support multiple device types and performance configurations, meeting storage requirements for different application scenarios. This best practice will introduce how to use Terraform to automatically deploy cloud volumes, including availability zone selection, storage type configuration, and performance parameter settings.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)

### Resources

- [Cloud Volume Resource (huaweicloud\_evs\_volume)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/evs_volume)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones.test
    └── huaweicloud_evs_volume.test
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Availability Zone Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the results of which are used to create cloud volumes:

```hcl
# Get all availability zone information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create cloud volumes
data "huaweicloud_availability_zones" "test" {}
```

**Parameter Description**:

- No additional parameters required, the data source will automatically get all availability zone information in the current region

### 3. Create Cloud Volume

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a cloud volume resource:

```hcl
variable "volume_availability_zone" {
  description = "Cloud volume availability zone"
  type        = string
  default     = ""
  nullable    = false
}

variable "volume_name" {
  description = "Cloud volume name"
  type        = string
}

variable "volume_type" {
  description = "Cloud volume type"
  type        = string
  default     = "SSD"
}

variable "voulme_size" {
  description = "Cloud volume size"
  type        = number
  default     = 40
}

variable "volume_description" {
  description = "Cloud volume description"
  type        = string
  default     = ""
}

variable "volume_multiattach" {
  description = "Whether the cloud volume is a shared disk"
  type        = bool
  default     = false
}

variable "volume_iops" {
  description = "Cloud volume IOPS"
  type        = number
  default     = null
}

variable "volume_throughput" {
  description = "Cloud volume throughput"
  type        = number
  default     = null
}

variable "volume_device_type" {
  description = "Cloud volume device type"
  type        = string
  default     = "VBD"
}

variable "enterprise_project_id" {
  description = "Cloud volume enterprise project ID"
  type        = string
  default     = null
}

variable "volume_tags" {
  description = "Cloud volume tags"
  type        = map(string)
  default     = {}
}

variable "charging_mode" {
  description = "Cloud volume charging mode"
  type        = string
  default     = "postPaid"
}

variable "period_unit" {
  description = "Cloud volume charging period unit"
  type        = string
  default     = null
}

variable "period" {
  description = "Cloud volume charging period"
  type        = number
  default     = null
}

variable "auto_renew" {
  description = "Whether the cloud volume auto-renews"
  type        = string
  default     = "false"
}

# Create a cloud volume resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_evs_volume" "test" {
  availability_zone     = var.volume_availability_zone != "" ? var.volume_availability_zone : try(data.huaweicloud_availability_zones.test.names[0], null)
  name                  = var.volume_name
  volume_type           = var.volume_type
  size                  = var.voulme_size
  description           = var.volume_description
  multiattach           = var.volume_multiattach
  iops                  = var.volume_iops
  throughput            = var.volume_throughput
  device_type           = var.volume_device_type
  enterprise_project_id = var.enterprise_project_id
  tags                  = var.volume_tags
  charging_mode         = var.charging_mode
  period_unit           = var.period_unit
  period                = var.period
  auto_renew            = var.auto_renew
}
```

**Parameter Description**:

- **availability\_zone**: Availability zone, prioritizes using input variable, uses first result from availability zone data source if empty
- **name**: Cloud volume name, assigned by referencing the input variable volume\_name
- **volume\_type**: Cloud volume type, assigned by referencing the input variable volume\_type
- **size**: Cloud volume size, assigned by referencing the input variable voulme\_size
- **description**: Cloud volume description, assigned by referencing the input variable volume\_description
- **multiattach**: Whether it's a shared disk, assigned by referencing the input variable volume\_multiattach
- **iops**: IOPS performance, assigned by referencing the input variable volume\_iops
- **throughput**: Throughput performance, assigned by referencing the input variable volume\_throughput
- **device\_type**: Device type, assigned by referencing the input variable volume\_device\_type
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing the input variable enterprise\_project\_id
- **tags**: Tags, assigned by referencing the input variable volume\_tags
- **charging\_mode**: Charging mode, assigned by referencing the input variable charging\_mode
- **period\_unit**: Charging period unit, assigned by referencing the input variable period\_unit
- **period**: Charging period, assigned by referencing the input variable period
- **auto\_renew**: Auto-renewal, assigned by referencing the input variable auto\_renew

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Cloud volume configuration
volume_name        = "tf_test_vplume"
volume_type        = "SSD"
voulme_size        = 40
volume_description = "terraform test"
volume_device_type = "VBD"
volume_tags        = {
  foo = "bar"
  key = "value"
}
charging_mode      = "postPaid"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="volume_name=my-volume" -var="volume_type=SSD"`
2. Environment variables: `export TF_VAR_volume_name=my-volume`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating cloud volumes
4. Run `terraform show` to view the created cloud volumes

## Reference Information

- [Huawei Cloud EVS Product Documentation](https://support.huaweicloud.com/evs/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For EVS Cloud Volume](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/evs/volume)

# Deploy Disk Snapshot

## Application Scenario

Elastic Volume Service (EVS) is a high-performance, highly reliable, and scalable block storage service provided by Huawei Cloud, providing persistent storage for ECS instances. EVS supports multiple storage types, including SSD, SAS, SATA, etc., meeting storage requirements for different business scenarios.

EVS disk snapshots are an important feature of the EVS service, used to create data backups of cloud volumes at specific points in time. Through disk snapshots, enterprises can protect important data, achieve rapid recovery, and support data migration and backup strategies. Disk snapshots support incremental backup, saving storage space and providing reliable data protection mechanisms. This best practice will introduce how to use Terraform to automatically deploy EVS disk snapshots, including cloud volume creation and snapshot configuration.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)

### Resources

- [Cloud Volume Resource (huaweicloud\_evs\_volume)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/evs_volume)
- [EVS Disk Snapshot Resource (huaweicloud\_evs\_snapshot)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/evs_snapshot)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones.test
    └── huaweicloud_evs_volume.test
        └── huaweicloud_evs_snapshot.test
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Availability Zone Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the results of which are used to create cloud volumes:

```hcl
# Get all availability zone information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create cloud volumes
data "huaweicloud_availability_zones" "test" {}
```

**Parameter Description**:

- No additional parameters required, the data source will automatically get all availability zone information in the current region

### 3. Create Cloud Volume

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a cloud volume resource:

```hcl
variable "volume_availability_zone" {
  description = "Cloud volume availability zone"
  type        = string
  default     = ""
  nullable    = false
}

variable "volume_name" {
  description = "Cloud volume name"
  type        = string
}

variable "volume_type" {
  description = "Cloud volume type"
  type        = string
  default     = "SAS"
}

variable "volume_size" {
  description = "Cloud volume size"
  type        = number
  default     = 20
}

variable "voluem_description" {
  description = "Cloud volume description"
  type        = string
  default     = ""
}

variable "vouleme_multiattach" {
  description = "Whether the cloud volume is a shared disk"
  type        = bool
  default     = false
}

# Create a cloud volume resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_evs_volume" "test" {
  availability_zone = var.volume_availability_zone != "" ? var.volume_availability_zone : try(data.huaweicloud_availability_zones.test.names[0], null)
  name              = var.volume_name
  volume_type       = var.volume_type
  size              = var.volume_size
  description       = var.voluem_description
  multiattach       = var.vouleme_multiattach
}
```

**Parameter Description**:

- **availability\_zone**: Availability zone, prioritizes using input variable, uses first result from availability zone data source if empty
- **name**: Cloud volume name, assigned by referencing the input variable volume\_name
- **volume\_type**: Cloud volume type, assigned by referencing the input variable volume\_type
- **size**: Cloud volume size, assigned by referencing the input variable volume\_size
- **description**: Cloud volume description, assigned by referencing the input variable voluem\_description
- **multiattach**: Whether it's a shared disk, assigned by referencing the input variable vouleme\_multiattach

### 4. Create EVS Disk Snapshot

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an EVS disk snapshot resource:

```hcl
variable "snapshot_name" {
  description = "Snapshot name"
  type        = string
}

variable "snapshot_description" {
  description = "Snapshot description"
  type        = string
  default     = ""
}

variable "snapshot_metadata" {
  description = "Snapshot metadata information"
  type        = map(string)
  default     = {}
}

variable "snapshot_force" {
  description = "Force create snapshot flag"
  type        = bool
  default     = false
}

# Create an EVS disk snapshot resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_evs_snapshot" "test" {
  volume_id   = huaweicloud_evs_volume.test.id
  name        = var.snapshot_name
  description = var.snapshot_description
  metadata    = var.snapshot_metadata
  force       = var.snapshot_force
}
```

**Parameter Description**:

- **volume\_id**: Cloud volume ID, assigned by referencing the cloud volume resource (huaweicloud\_evs\_volume.test) ID
- **name**: Snapshot name, assigned by referencing the input variable snapshot\_name
- **description**: Snapshot description, assigned by referencing the input variable snapshot\_description
- **metadata**: Snapshot metadata, assigned by referencing the input variable snapshot\_metadata
- **force**: Force create flag, assigned by referencing the input variable snapshot\_force

### 5. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Cloud volume configuration
volume_name       = "tf_test_volume"
volume_type       = "SAS"
volume_size       = 20
voluem_description = "Test volume created by Terraform"

# Snapshot configuration
snapshot_name     = "tf_test_snapshot"
snapshot_description = "Test snapshot created by Terraform"
snapshot_metadata = {
  test = "terraform"
}
snapshot_force    = false
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="volume_name=my-volume" -var="snapshot_name=my-snapshot"`
2. Environment variables: `export TF_VAR_volume_name=my-volume`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 6. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating disk snapshots
4. Run `terraform show` to view the created disk snapshots

## Reference Information

- [Huawei Cloud EVS Product Documentation](https://support.huaweicloud.com/evs/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For EVS Disk Snapshot](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/evs/snapshot)

# Deploy Disk Snapshot Group

## Application Scenario

Elastic Volume Service (EVS) is a high-performance, highly reliable, and scalable block storage service provided by Huawei Cloud, providing persistent storage for ECS instances. EVS supports multiple storage types, including SSD, SAS, SATA, etc., meeting storage requirements for different business scenarios.

EVS disk snapshot groups are an important feature of the EVS service, used to create consistent snapshot backups of multiple cloud volumes. Through disk snapshot groups, enterprises can ensure data consistency of multiple related cloud volumes at specific points in time, which is very important for scenarios such as database clusters and distributed applications that require data consistency. This best practice will introduce how to use Terraform to automatically deploy EVS disk snapshot groups, including ECS instance creation, cloud volume creation, mounting, and disk snapshot group configuration.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [ECS Flavor List Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)
- [Image List Query Data Source (data.huaweicloud\_images\_images)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_images)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [ECS Instance Resource (huaweicloud\_compute\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_instance)
- [Cloud Volume Resource (huaweicloud\_evs\_volume)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/evs_volume)
- [Cloud Volume Mount Resource (huaweicloud\_compute\_volume\_attach)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_volume_attach)
- [EVS Disk Snapshot Group Resource (huaweicloud\_evs\_snapshot\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/evs_snapshot_group)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones.test
    ├── data.huaweicloud_compute_flavors.test
    ├── huaweicloud_vpc_subnet.test
    └── huaweicloud_compute_instance.test

data.huaweicloud_compute_flavors.test
    ├── data.huaweicloud_images_images.test
    └── huaweicloud_compute_instance.test

data.huaweicloud_images_images.test
    └── huaweicloud_compute_instance.test

huaweicloud_vpc.test
    └── huaweicloud_vpc_subnet.test

huaweicloud_vpc_subnet.test
    └── huaweicloud_compute_instance.test

huaweicloud_networking_secgroup.test
    └── huaweicloud_compute_instance.test

huaweicloud_compute_instance.test
    └── huaweicloud_compute_volume_attach.test

huaweicloud_evs_volume.test
    └── huaweicloud_compute_volume_attach.test

huaweicloud_compute_volume_attach.test
    └── huaweicloud_evs_snapshot_group.test
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Availability Zone Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the results of which are used to create ECS instances and cloud volumes:

```hcl
# Get all availability zone information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create ECS instances and cloud volumes
data "huaweicloud_availability_zones" "test" {}
```

**Parameter Description**:

- No additional parameters required, the data source will automatically get all availability zone information in the current region

### 3. Query ECS Flavor Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the results of which are used to create ECS instances:

```hcl
variable "instance_flavor_id" {
  description = "ECS instance flavor ID, if not specified, will use the first available flavor matching the conditions"
  type        = string
  default     = ""
}

variable "availability_zone" {
  description = "ECS instance creation availability zone, if not specified, will use the first availability zone"
  type        = string
  default     = ""
}

variable "instance_flavor_performance_type" {
  description = "ECS instance flavor performance type, used to query available flavors when instance_flavor_id is not specified"
  type        = string
  default     = "normal"
}

variable "instance_flavor_cpu_core_count" {
  description = "ECS instance flavor CPU core count, used to query available flavors when instance_flavor_id is not specified"
  type        = number
  default     = 0
}

variable "instance_flavor_memory_size" {
  description = "ECS instance flavor memory size (GB), used to query available flavors when instance_flavor_id is not specified"
  type        = number
  default     = 0
}

# Get all ECS flavor information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create ECS instances
data "huaweicloud_compute_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  availability_zone = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test.names[0], null) : var.availability_zone
  performance_type  = var.instance_flavor_performance_type
  cpu_core_count    = var.instance_flavor_cpu_core_count
  memory_size       = var.instance_flavor_memory_size
}
```

**Parameter Description**:

- **availability\_zone**: Availability zone, prioritizes using input variable, uses first result from availability zone data source if empty
- **performance\_type**: Performance type, assigned by referencing the input variable instance\_flavor\_performance\_type
- **cpu\_core\_count**: CPU core count, assigned by referencing the input variable instance\_flavor\_cpu\_core\_count
- **memory\_size**: Memory size, assigned by referencing the input variable instance\_flavor\_memory\_size

### 4. Query Image Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the results of which are used to create ECS instances:

```hcl
variable "instance_image_id" {
  description = "ECS instance image ID, if not specified, will use the first available image matching the conditions"
  type        = string
  default     = ""
}

variable "instance_image_os_type" {
  description = "ECS instance image operating system type, used to query available images when instance_image_id is not specified"
  type        = string
  default     = "Ubuntu"
}

variable "instance_image_visibility" {
  description = "ECS instance image visibility, used to query available images when instance_image_id is not specified"
  type        = string
  default     = "public"
}

# Get all image information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create ECS instances
data "huaweicloud_images_images" "test" {
  count = var.instance_image_id == "" ? 1 : 0

  flavor_id  = var.instance_flavor_id == "" ? try(data.huaweicloud_compute_flavors.test[0].ids[0], "") : var.instance_flavor_id
  os         = var.instance_image_os_type
  visibility = var.instance_image_visibility
}
```

**Parameter Description**:

- **flavor\_id**: Flavor ID, prioritizes using input variable, uses first result from ECS flavor data source if empty
- **os**: Operating system type, assigned by referencing the input variable instance\_image\_os\_type
- **visibility**: Visibility, assigned by referencing the input variable instance\_image\_visibility

### 5. Create VPC

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC resource:

```hcl
variable "vpc_name" {
  description = "VPC name"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
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
- **cidr**: VPC CIDR block, assigned by referencing the input variable vpc\_cidr

### 6. Create VPC Subnet

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC subnet resource:

```hcl
variable "subnet_name" {
  description = "VPC subnet name"
  type        = string
}

variable "subnet_cidr" {
  description = "VPC subnet CIDR block, if not specified, will calculate subnet cidr within existing CIDR address block"
  type        = string
  default     = ""
}

variable "subnet_gateway_ip" {
  description = "VPC subnet gateway IP, if not specified, will calculate gateway IP within existing CIDR address block"
  type        = string
  default     = ""
}

# Create a VPC subnet resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id            = huaweicloud_vpc.test.id
  name              = var.subnet_name
  cidr              = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip        = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
  availability_zone = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test.names[0], null) : var.availability_zone
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID, assigned by referencing the VPC resource (huaweicloud\_vpc.test) ID
- **name**: Subnet name, assigned by referencing the input variable subnet\_name
- **cidr**: Subnet CIDR block, prioritizes using input variable, calculates using cidrsubnet function if empty
- **gateway\_ip**: Gateway IP, prioritizes using input variable, calculates using cidrhost function if empty
- **availability\_zone**: Availability zone, prioritizes using input variable, uses first result from availability zone data source if empty

### 7. Create Security Group

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a security group resource:

```hcl
variable "secgroup_name" {
  description = "Security group name"
  type        = string
}

# Create a security group resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.secgroup_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: Security group name, assigned by referencing the input variable secgroup\_name
- **delete\_default\_rules**: Delete default rules, set to true

### 8. Create ECS Instance

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an ECS instance resource:

```hcl
variable "ecs_instance_name" {
  description = "ECS instance name"
  type        = string
}

variable "key_pair_name" {
  description = "ECS login key pair name"
  type        = string
  default     = ""
}

variable "system_disk_type" {
  description = "System disk type"
  type        = string
  default     = "SAS"
}

variable "system_disk_size" {
  description = "System disk size (GB)"
  type        = number
  default     = 40
}

# Create an ECS instance resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_compute_instance" "test" {
  name              = var.ecs_instance_name
  availability_zone = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test.names[0], null) : var.availability_zone
  flavor_id         = var.instance_flavor_id == "" ? try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, "") : var.instance_flavor_id
  image_id          = var.instance_image_id == "" ? try(data.huaweicloud_images_images.test[0].images[0].id, "") : var.instance_image_id
  security_groups   = [huaweicloud_networking_secgroup.test.name]
  key_pair          = var.key_pair_name
  system_disk_type  = var.system_disk_type
  system_disk_size  = var.system_disk_size

  network {
    uuid = huaweicloud_vpc_subnet.test.id
  }
}
```

**Parameter Description**:

- **name**: Instance name, assigned by referencing the input variable ecs\_instance\_name
- **availability\_zone**: Availability zone, prioritizes using input variable, uses first result from availability zone data source if empty
- **flavor\_id**: Flavor ID, prioritizes using input variable, uses first result from ECS flavor data source if empty
- **image\_id**: Image ID, prioritizes using input variable, uses first result from image data source if empty
- **security\_groups**: Security group list, referencing security group resource
- **key\_pair**: Key pair name, assigned by referencing the input variable key\_pair\_name
- **system\_disk\_type**: System disk type, assigned by referencing the input variable system\_disk\_type
- **system\_disk\_size**: System disk size, assigned by referencing the input variable system\_disk\_size

### 9. Create Cloud Volumes

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create cloud volume resources:

```hcl
variable "volume_configuration" {
  description = "List of cloud volume configurations to mount to ECS instance"
  type = list(object({
    name        = string
    size        = number
    volume_type = string
    device_type = string
  }))
  default = []
}

# Create cloud volume resources under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_evs_volume" "test" {
  count = length(var.volume_configuration)

  availability_zone = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test.names[0], null) : var.availability_zone
  volume_type       = var.volume_configuration[count.index].volume_type
  name              = var.volume_configuration[count.index].name
  size              = var.volume_configuration[count.index].size
  device_type       = var.volume_configuration[count.index].device_type
}
```

**Parameter Description**:

- **availability\_zone**: Availability zone, prioritizes using input variable, uses first result from availability zone data source if empty
- **volume\_type**: Cloud volume type, assigned by referencing the volume\_type in input variable volume\_configuration
- **name**: Cloud volume name, assigned by referencing the name in input variable volume\_configuration
- **size**: Cloud volume size, assigned by referencing the size in input variable volume\_configuration
- **device\_type**: Device type, assigned by referencing the device\_type in input variable volume\_configuration

### 10. Mount Cloud Volumes

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create cloud volume mount resources:

```hcl
# Create cloud volume mount resources under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_compute_volume_attach" "test" {
  count = length(var.volume_configuration)

  instance_id = huaweicloud_compute_instance.test.id
  volume_id   = huaweicloud_evs_volume.test[count.index].id
}
```

**Parameter Description**:

- **instance\_id**: ECS instance ID, assigned by referencing the ECS instance resource (huaweicloud\_compute\_instance.test) ID
- **volume\_id**: Cloud volume ID, assigned by referencing the cloud volume resource (huaweicloud\_evs\_volume.test) ID

### 11. Create EVS Disk Snapshot Group

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an EVS disk snapshot group resource:

```hcl
variable "instant_access" {
  description = "Whether to enable disk snapshot group instant access"
  type        = bool
  default     = false
}

variable "snapshot_group_name" {
  description = "Disk snapshot group name"
  type        = string
  default     = ""
}

variable "snapshot_group_description" {
  description = "Disk snapshot group description"
  type        = string
  default     = "Created by Terraform"
}

variable "enterprise_project_id" {
  description = "Disk snapshot group enterprise project ID"
  type        = string
  default     = "0"
}

variable "incremental" {
  description = "Whether to create incremental snapshots"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Key-value pairs associated with disk snapshot group"
  type        = map(string)
  default = {
    environment = "test"
    created_by  = "terraform"
  }
}

# Create an EVS disk snapshot group resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_evs_snapshot_group" "test" {
  depends_on = [huaweicloud_compute_volume_attach.test]

  server_id             = huaweicloud_compute_instance.test.id
  volume_ids            = length(huaweicloud_evs_volume.test) > 0 ? try([for v in huaweicloud_evs_volume.test : v.id], null) : null
  instant_access        = var.instant_access
  name                  = var.snapshot_group_name
  description           = var.snapshot_group_description
  enterprise_project_id = var.enterprise_project_id
  incremental           = var.incremental
  tags                  = var.tags
}
```

**Parameter Description**:

- **server\_id**: ECS instance ID, assigned by referencing the ECS instance resource (huaweicloud\_compute\_instance.test) ID
- **volume\_ids**: Cloud volume ID list, assigned by referencing the cloud volume resource list
- **instant\_access**: Instant access, assigned by referencing the input variable instant\_access
- **name**: Disk snapshot group name, assigned by referencing the input variable snapshot\_group\_name
- **description**: Disk snapshot group description, assigned by referencing the input variable snapshot\_group\_description
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing the input variable enterprise\_project\_id
- **incremental**: Incremental snapshot, assigned by referencing the input variable incremental
- **tags**: Tags, assigned by referencing the input variable tags

### 12. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Network configuration
vpc_name    = "evs-test-vpc"
vpc_cidr    = "192.168.0.0/16"
subnet_name = "evs-test-subnet"
secgroup_name = "evs-test-sg"

# ECS instance configuration
ecs_instance_name = "evs-test-ecs"

# Cloud volume configuration
volume_configuration = [
  {
    name        = "evs-test-volume1"
    size        = 50
    volume_type = "SSD"
    device_type = "VBD"
  },
  {
    name        = "evs-test-volume2"
    size        = 100
    volume_type = "SAS"
    device_type = "SCSI"
  }
]
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="ecs_instance_name=my-ecs"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 13. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating disk snapshot groups
4. Run `terraform show` to view the created disk snapshot groups

## Reference Information

- [Huawei Cloud EVS Product Documentation](https://support.huaweicloud.com/evs/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For EVS Disk Snapshot Group](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/evs/snapshot-group)
