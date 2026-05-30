# Deploy Node Partition

## Application Scenario

Cloud Container Engine (CCE) is a high-reliability, high-performance enterprise-grade container management service that supports Kubernetes community native applications and tools. Node partition is a resource isolation mechanism provided by CCE, used to assign nodes in a cluster to different partitions, achieving physical and logical isolation of resources. By creating node partitions, you can deploy nodes to specified edge sites or regions, meeting the requirements of edge computing, hybrid cloud, and other scenarios. This best practice will introduce how to use Terraform to automatically deploy a CCE node partition, including querying availability zones and instance flavors, as well as creating VPC, subnet, ENI subnet, CCE cluster, node partition, node, and node pool.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [Compute Flavors Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [CCE Cluster Resource (huaweicloud\_cce\_cluster)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cce_cluster)
- [CCE Node Partition Resource (huaweicloud\_cce\_partition)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cce_partition)
- [CCE Node Resource (huaweicloud\_cce\_node)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cce_node)
- [CCE Node Pool Resource (huaweicloud\_cce\_node\_pool)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cce_node_pool)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    ├── huaweicloud_vpc_subnet
    ├── huaweicloud_vpc_subnet (ENI subnet)
    └── data.huaweicloud_compute_flavors
        ├── huaweicloud_cce_node
        └── huaweicloud_cce_node_pool

huaweicloud_vpc
    ├── huaweicloud_vpc_subnet
    │   └── huaweicloud_cce_cluster
    └── huaweicloud_vpc_subnet (ENI subnet)
        └── huaweicloud_cce_partition
            ├── huaweicloud_cce_node
            └── huaweicloud_cce_node_pool

huaweicloud_cce_cluster
    └── huaweicloud_cce_partition
        ├── huaweicloud_cce_node
        └── huaweicloud_cce_node_pool
```

## Implementation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration introduction, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://hcbp.gitbook.io/huaweicloud-provider/product-introduction/prepare_before_deploy).

### 2. Query Availability Zones Required for Node Partition Resource Creation Through Data Source

Add the following script to the TF file (such as main.tf) to inform Terraform to perform a data source query, the query results are used to create node partition related resources:

```hcl
variable "availability_zone" {
  description = "The availability zone where the CCE cluster will be created"
  type        = string
  default     = ""
}

# Get all availability zone information in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for creating node partition related resources
data "huaweicloud_availability_zones" "test" {
  count = var.availability_zone == "" ? 1 : 0
}
```

**Parameter Description**:

- **count**: The number of data source queries, used to control whether to query availability zone information, only when `var.availability_zone` is empty, the availability zone information is queried

### 3. Create VPC Resource (Optional)

Add the following script to the TF file to inform Terraform to create VPC resources (if VPC ID is not specified):

```hcl
variable "vpc_id" {
  description = "The ID of the VPC"
  type        = string
  default     = ""
}

variable "vpc_name" {
  description = "The name of the VPC"
  type        = string
  default     = ""

  validation {
    condition     = var.vpc_id != "" || var.vpc_name != ""
    error_message = "vpc_name must be provided if vpc_id is not provided."
  }
}

variable "vpc_cidr" {
  description = "The CIDR block of the VPC"
  type        = string
  default     = "192.168.0.0/16"
}

# Create VPC resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing network environment for node partition
resource "huaweicloud_vpc" "test" {
  count = var.vpc_id == "" && var.subnet_id == "" ? 1 : 0

  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **count**: The number of resource creations, used to control whether to create VPC resource, only when both `var.vpc_id` and `var.subnet_id` are empty, the VPC resource is created
- **name**: The name of the VPC, assigned by referencing input variable `vpc_name`
- **cidr**: The CIDR block of the VPC, assigned by referencing input variable `vpc_cidr`, default is "192.168.0.0/16"

### 4. Create VPC Subnet Resource (Optional)

Add the following script to the TF file to inform Terraform to create VPC subnet resources (if subnet ID is not specified):

```hcl
variable "subnet_id" {
  description = "The ID of the subnet"
  type        = string
  default     = ""
}

variable "subnet_name" {
  description = "The name of the subnet"
  type        = string
  default     = ""

  validation {
    condition     = var.subnet_id == "" || var.subnet_name == ""
    error_message = "subnet_name must be provided if subnet_id is not provided."
  }
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

# Create VPC subnet resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing network environment for node partition
resource "huaweicloud_vpc_subnet" "test" {
  count = var.subnet_id == "" ? 1 : 0

  vpc_id            = var.vpc_id != "" ? var.vpc_id : huaweicloud_vpc.test[0].id
  name              = var.subnet_name
  cidr              = var.subnet_cidr != "" ? var.subnet_cidr : cidrsubnet(huaweicloud_vpc.test[0].cidr, 4, 0)
  gateway_ip        = var.subnet_gateway_ip != "" ? var.subnet_gateway_ip : var.subnet_cidr != "" ? cidrhost(var.subnet_cidr, 1) : cidrhost(cidrsubnet(huaweicloud_vpc.test[0].cidr, 4, 0), 1)
  availability_zone = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test[0].names[0], null)
}
```

**Parameter Description**:

- **count**: The number of resource creations, used to control whether to create VPC subnet resource, only when `var.subnet_id` is empty, the VPC subnet resource is created
- **vpc\_id**: The VPC ID to which the subnet belongs, if the VPC ID is specified, use that value, otherwise assign by referencing the ID of the VPC resource (huaweicloud\_vpc.test\[0])
- **name**: The name of the subnet, assigned by referencing input variable `subnet_name`
- **cidr**: The CIDR block of the subnet, if the subnet CIDR is specified, use that value, otherwise automatically calculate based on the VPC's CIDR block using the `cidrsubnet` function
- **gateway\_ip**: The gateway IP of the subnet, if the gateway IP is specified, use that value, otherwise automatically calculate based on the subnet CIDR or automatically calculated subnet CIDR using the `cidrhost` function
- **availability\_zone**: The availability zone where the subnet is located, if the availability zone is specified, use that value, otherwise use the first availability zone from the availability zone list query data source

### 5. Create ENI Subnet Resource (Optional)

Add the following script to the TF file to inform Terraform to create ENI subnet resources (if ENI subnet ID is not specified):

```hcl
variable "eni_ipv4_subnet_id" {
  description = "The ID of the ENI subnet"
  type        = string
  default     = ""
}

variable "eni_subnet_name" {
  description = "The name of the ENI subnet"
  type        = string
  default     = ""

  validation {
    condition     = var.eni_ipv4_subnet_id == "" || var.eni_subnet_name == ""
    error_message = "eni_subnet_name must be provided if eni_ipv4_subnet_id is not provided."
  }
}

variable "eni_subnet_cidr" {
  description = "The CIDR block of the ENI subnet"
  type        = string
  default     = ""
}

# Create ENI subnet resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing ENI network environment for node partition
resource "huaweicloud_vpc_subnet" "eni" {
  count = var.eni_ipv4_subnet_id == "" ? 1 : 0

  vpc_id            = var.vpc_id != "" ? var.vpc_id : huaweicloud_vpc.test[0].id
  name              = var.eni_subnet_name
  cidr              = var.eni_subnet_cidr != "" ? var.eni_subnet_cidr : cidrsubnet(huaweicloud_vpc.test[0].cidr, 4, 1)
  gateway_ip        = var.subnet_gateway_ip != "" ? var.subnet_gateway_ip : var.eni_subnet_cidr != "" ? cidrhost(var.eni_subnet_cidr, 1) : cidrhost(cidrsubnet(huaweicloud_vpc.test[0].cidr, 4, 1), 1)
  availability_zone = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test[0].names[0], null)
}
```

**Parameter Description**:

- **count**: The number of resource creations, used to control whether to create ENI subnet resource, only when `var.eni_ipv4_subnet_id` is empty, the ENI subnet resource is created
- **vpc\_id**: The VPC ID to which the ENI subnet belongs, if the VPC ID is specified, use that value, otherwise assign by referencing the ID of the VPC resource (huaweicloud\_vpc.test\[0])
- **name**: The name of the ENI subnet, assigned by referencing input variable `eni_subnet_name`
- **cidr**: The CIDR block of the ENI subnet, if the ENI subnet CIDR is specified, use that value, otherwise automatically calculate based on the VPC's CIDR block using the `cidrsubnet` function (using a different subnet index to avoid conflicts with the regular subnet)
- **gateway\_ip**: The gateway IP of the ENI subnet, if the gateway IP is specified, use that value, otherwise automatically calculate based on the ENI subnet CIDR or automatically calculated ENI subnet CIDR using the `cidrhost` function
- **availability\_zone**: The availability zone where the ENI subnet is located, if the availability zone is specified, use that value, otherwise use the first availability zone from the availability zone list query data source

> Note: ENI subnet is a required network configuration for node partitions, used to provide high-performance network connections. The ENI subnet must be in the same VPC as the regular subnet, but must use a different CIDR block to avoid IP address conflicts.

### 6. Create CCE Cluster Resource

Add the following script to the TF file to inform Terraform to create CCE cluster resources:

```hcl
variable "cluster_name" {
  description = "The name of the CCE cluster"
  type        = string
  default     = ""
}

variable "cluster_flavor_id" {
  description = "The flavor ID of the CCE cluster"
  type        = string
  default     = "cce.s1.small"
}

variable "cluster_version" {
  description = "The version of the CCE cluster"
  type        = string
  default     = null
  nullable    = true
}

variable "cluster_type" {
  description = "The type of the CCE cluster"
  type        = string
  default     = "VirtualMachine"
}

variable "container_network_type" {
  description = "The type of container network"
  type        = string
  default     = "eni"
}

variable "cluster_description" {
  description = "The description of the CCE cluster"
  type        = string
  default     = ""
}

variable "cluster_tags" {
  description = "The tags of the CCE cluster"
  type        = map(string)
  default     = {}
}

# Create CCE cluster resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for deploying and managing containerized applications
resource "huaweicloud_cce_cluster" "test" {
  name                         = var.cluster_name
  flavor_id                    = var.cluster_flavor_id
  cluster_version              = var.cluster_version
  cluster_type                 = var.cluster_type
  container_network_type       = var.container_network_type
  vpc_id                       = var.vpc_id != "" ? var.vpc_id : huaweicloud_vpc.test[0].id
  enable_distribute_management = true
  subnet_id                    = var.subnet_id != "" ? var.subnet_id : huaweicloud_vpc_subnet.test[0].id
  eni_subnet_id                = var.eni_ipv4_subnet_id != "" ? var.eni_ipv4_subnet_id : huaweicloud_vpc_subnet.eni[0].ipv4_subnet_id
  description                  = var.cluster_description
  tags                         = var.cluster_tags
}
```

**Parameter Description**:

- **name**: The name of the CCE cluster, assigned by referencing input variable `cluster_name`
- **flavor\_id**: The flavor ID of the CCE cluster, assigned by referencing input variable `cluster_flavor_id`, default is "cce.s1.small" for small cluster
- **cluster\_version**: The version of the CCE cluster, assigned by referencing input variable `cluster_version`, if null, the latest version will be used
- **cluster\_type**: The type of the CCE cluster, assigned by referencing input variable `cluster_type`, default is "VirtualMachine" for virtual machine type
- **container\_network\_type**: Container network type, assigned by referencing input variable `container_network_type`, default is "eni" for ENI network mode (node partitions must use ENI network)
- **vpc\_id**: VPC ID, if the VPC ID is specified, use that value, otherwise assign by referencing the ID of the VPC resource (huaweicloud\_vpc.test\[0])
- **enable\_distribute\_management**: Whether to enable distributed management, set to true, which is a prerequisite for node partition functionality
- **subnet\_id**: Subnet ID, if the subnet ID is specified, use that value, otherwise assign by referencing the ID of the VPC subnet resource (huaweicloud\_vpc\_subnet.test\[0])
- **eni\_subnet\_id**: ENI subnet ID, if the ENI subnet ID is specified, use that value, otherwise assign by referencing the IPv4 subnet ID of the ENI subnet resource (huaweicloud\_vpc\_subnet.eni\[0])
- **description**: Cluster description information, assigned by referencing input variable `cluster_description`
- **tags**: Cluster tags, assigned by referencing input variable `cluster_tags`, used for resource classification and management

> Note: Node partition functionality requires the cluster to enable distributed management (`enable_distribute_management` set to true), and must use ENI network mode (`container_network_type` set to "eni").

### 7. Query Instance Flavors Required for Node Partition Resource Creation Through Data Source

Add the following script to the TF file to inform Terraform to query instance flavors that meet the conditions:

```hcl
variable "node_flavor_id" {
  description = "The flavor ID of the node"
  type        = string
  default     = ""
}

variable "node_flavor_performance_type" {
  description = "The performance type of the node"
  type        = string
  default     = "normal"
}

variable "node_flavor_cpu_core_count" {
  description = "The CPU core count of the node"
  type        = number
  default     = 2
}

variable "node_flavor_memory_size" {
  description = "The memory size of the node"
  type        = number
  default     = 4
}

# Get all instance flavor information that meets specific conditions in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for creating node partition related resources
data "huaweicloud_compute_flavors" "test" {
  count = var.node_flavor_id == "" ? 1 : 0

  performance_type  = var.node_flavor_performance_type
  cpu_core_count    = var.node_flavor_cpu_core_count
  memory_size       = var.node_flavor_memory_size
  availability_zone = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test[0].names[0], null)
}
```

**Parameter Description**:

- **count**: The number of data source queries, used to control whether to query instance flavor information, only when `var.node_flavor_id` is empty, the instance flavor information is queried
- **performance\_type**: Performance type, assigned through input variable `node_flavor_performance_type`, default is "normal" for general purpose
- **cpu\_core\_count**: CPU core count, assigned through input variable `node_flavor_cpu_core_count`, default is 2 cores
- **memory\_size**: Memory size (GB), assigned through input variable `node_flavor_memory_size`, default is 4GB
- **availability\_zone**: The availability zone where the instance flavor is located, if the availability zone is specified, use that value, otherwise use the first availability zone from the availability zone list query data source

### 8. Create CCE Node Partition Resource

Add the following script to the TF file to inform Terraform to create CCE node partition resources:

```hcl
variable "node_partition" {
  description = "The name or ID of the node partition"
  type        = string
  default     = ""

  validation {
    condition     = var.node_partition != "" || var.partition_name != ""
    error_message = "partition_name must be provided if node_partition is not provided."
  }
}

variable "partition_name" {
  description = "The name of the node partition"
  type        = string
  default     = ""
}

variable "partition_category" {
  description = "The category of the node partition"
  type        = string
  default     = "IES"
}

variable "partition_public_border_group" {
  description = "The public border group of the node partition"
  type        = string
  default     = ""

  validation {
    condition     = var.node_partition == "" || var.partition_public_border_group == ""
    error_message = "partition_public_border_group must be provided if node_partition is not provided."
  }
}

# Create CCE node partition resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for assigning nodes to specified partitions
resource "huaweicloud_cce_partition" "test" {
  count = var.node_partition == "" ? 1 : 0

  cluster_id           = huaweicloud_cce_cluster.test.id
  name                 = var.partition_name
  category             = var.partition_category
  public_border_group  = var.partition_public_border_group
  partition_subnet_id  = huaweicloud_vpc_subnet.eni[0].id
  container_subnet_ids = [huaweicloud_vpc_subnet.eni[0].ipv4_subnet_id]
}
```

**Parameter Description**:

- **count**: The number of resource creations, used to control whether to create node partition resource, only when `var.node_partition` is empty, the node partition resource is created
- **cluster\_id**: CCE cluster ID, assigned by referencing the ID of the CCE cluster resource (huaweicloud\_cce\_cluster.test)
- **name**: The name of the node partition, assigned by referencing input variable `partition_name`
- **category**: The category of the node partition, assigned by referencing input variable `partition_category`, default is "IES" for Intelligent Edge Site
- **public\_border\_group**: The public border group of the node partition, assigned by referencing input variable `partition_public_border_group`, used to specify the location of the edge site
- **partition\_subnet\_id**: Partition subnet ID, assigned by referencing the ID of the ENI subnet resource (huaweicloud\_vpc\_subnet.eni\[0])
- **container\_subnet\_ids**: Container subnet ID list, assigned by referencing the IPv4 subnet ID list of the ENI subnet resource (huaweicloud\_vpc\_subnet.eni\[0])

> Note: Node partition is used to assign nodes to specified edge sites or regions. If a node partition already exists, you can specify the partition ID through the `node_partition` variable without creating a new partition.

### 9. Create CCE Node Resource (Optional)

Add the following script to the TF file to inform Terraform to create CCE node resources:

```hcl
variable "node_name" {
  description = "The name of the node"
  type        = string
}

variable "node_password" {
  description = "The root password to login node"
  type        = string
  sensitive   = true
}

variable "root_volume_type" {
  description = "The type of the root volume"
  type        = string
  default     = "SSD"
}

variable "root_volume_size" {
  description = "The size of the root volume"
  type        = number
  default     = 40
}

variable "data_volumes_configuration" {
  description = "The configuration of the data volumes"
  type = list(object({
    volumetype = string
    size       = number
  }))

  default = []
}

# Create CCE node resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing compute capacity to the cluster
resource "huaweicloud_cce_node" "test" {
  cluster_id        = huaweicloud_cce_cluster.test.id
  name              = var.node_name
  flavor_id         = var.node_flavor_id != "" ? var.node_flavor_id : try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, null)
  availability_zone = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test[0].names[0], null)
  password          = var.node_password
  partition         = var.node_partition != "" ? var.node_partition : huaweicloud_cce_partition.test[0].id

  root_volume {
    volumetype = var.root_volume_type
    size       = var.root_volume_size
  }

  dynamic "data_volumes" {
    for_each = var.data_volumes_configuration

    content {
      volumetype = data_volumes.value.volumetype
      size       = data_volumes.value.size
    }
  }

  lifecycle {
    ignore_changes = [
      flavor_id,
      availability_zone,
    ]
  }
}
```

**Parameter Description**:

- **cluster\_id**: CCE cluster ID, assigned by referencing the ID of the CCE cluster resource (huaweicloud\_cce\_cluster.test)
- **name**: The name of the node, assigned by referencing input variable `node_name`
- **flavor\_id**: Node flavor ID, if the node flavor ID is specified, use that value, otherwise assign by using the first flavor ID from the instance flavor list query data source
- **availability\_zone**: The availability zone where the node is located, if the availability zone is specified, use that value, otherwise assign by using the first availability zone from the availability zone list query data source
- **password**: The root password of the node, assigned by referencing input variable `node_password`, used for SSH login to the node
- **partition**: The partition to which the node belongs, if the node partition ID is specified, use that value, otherwise assign by referencing the ID of the node partition resource (huaweicloud\_cce\_partition.test\[0])
- **root\_volume**: Root volume configuration block
  - **volumetype**: Root volume type, assigned by referencing input variable `root_volume_type`, default is "SSD"
  - **size**: Root volume size (GB), assigned by referencing input variable `root_volume_size`, default is 40GB
- **data\_volumes**: Data volume configuration block, creates multiple data volume configurations through dynamic block (dynamic block) based on input variable `data_volumes_configuration`
  - **volumetype**: Data volume type, assigned through `volumetype` in input variable `data_volumes_configuration`
  - **size**: Data volume size (GB), assigned through `size` in input variable `data_volumes_configuration`
- **lifecycle**: Lifecycle configuration block, used to ignore changes to certain fields, avoiding unnecessary resource recreation after node creation due to changes in these fields

> Note: Nodes must specify the partition to which they belong, configured through the `partition` parameter. Node partitions are used to deploy nodes to specified edge sites or regions.

### 10. Create CCE Node Pool Resource (Optional)

Add the following script to the TF file to inform Terraform to create CCE node pool resources:

```hcl
variable "node_pool_name" {
  description = "The name of the node pool"
  type        = string
  default     = ""
}

variable "node_pool_os_type" {
  description = "The OS type of the node pool"
  type        = string
  default     = "EulerOS 2.9"
}

variable "node_pool_initial_node_count" {
  description = "The initial number of nodes in the node pool"
  type        = number
  default     = 1
}

variable "node_pool_password" {
  description = "The root password to login node"
  type        = string
  sensitive   = true
  default     = ""

  validation {
    condition     = var.node_pool_name != "" || var.node_pool_password != ""
    error_message = "node_pool_password must be provided if node_pool_name is not provided."
  }
}

# Create CCE node pool resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for managing nodes in the cluster
resource "huaweicloud_cce_node_pool" "test" {
  count = var.node_pool_name != "" ? 1 : 0

  cluster_id         = huaweicloud_cce_cluster.test.id
  name               = var.node_pool_name
  os                 = var.node_pool_os_type
  flavor_id          = var.node_flavor_id != "" ? var.node_flavor_id : try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, null)
  initial_node_count = var.node_pool_initial_node_count
  availability_zone  = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test[0].names[0], null)
  password           = var.node_pool_password
  type               = "vm"
  partition          = var.node_partition != "" ? var.node_partition : huaweicloud_cce_partition.test[0].id

  root_volume {
    volumetype = var.root_volume_type
    size       = var.root_volume_size
  }

  dynamic "data_volumes" {
    for_each = var.data_volumes_configuration

    content {
      volumetype = data_volumes.value.volumetype
      size       = data_volumes.value.size
    }
  }

  lifecycle {
    ignore_changes = [
      flavor_id,
      availability_zone,
    ]
  }
}
```

**Parameter Description**:

- **count**: The number of resource creations, used to control whether to create node pool resource, only when `var.node_pool_name` is not empty, the node pool resource is created
- **cluster\_id**: CCE cluster ID, assigned by referencing the ID of the CCE cluster resource (huaweicloud\_cce\_cluster.test)
- **name**: The name of the node pool, assigned by referencing input variable `node_pool_name`
- **os**: The operating system type of the nodes, assigned by referencing input variable `node_pool_os_type`, default is "EulerOS 2.9"
- **flavor\_id**: Node flavor ID, if the node flavor ID is specified, use that value, otherwise assign by using the first flavor ID from the instance flavor list query data source
- **initial\_node\_count**: Initial node count, assigned by referencing input variable `node_pool_initial_node_count`, default is 1
- **availability\_zone**: The availability zone where the nodes are located, if the availability zone is specified, use that value, otherwise assign by using the first availability zone from the availability zone list query data source
- **password**: The root password of the nodes, assigned by referencing input variable `node_pool_password`, used for SSH login to the nodes
- **type**: The type of the node pool, set to "vm" for virtual machine type
- **partition**: The partition to which the node pool belongs, if the node partition ID is specified, use that value, otherwise assign by referencing the ID of the node partition resource (huaweicloud\_cce\_partition.test\[0])
- **root\_volume**: Root volume configuration block
  - **volumetype**: Root volume type, assigned by referencing input variable `root_volume_type`, default is "SSD"
  - **size**: Root volume size (GB), assigned by referencing input variable `root_volume_size`, default is 40GB
- **data\_volumes**: Data volume configuration block, creates multiple data volume configurations through dynamic block (dynamic block) based on input variable `data_volumes_configuration`
  - **volumetype**: Data volume type, assigned through `volumetype` in input variable `data_volumes_configuration`
  - **size**: Data volume size (GB), assigned through `size` in input variable `data_volumes_configuration`
- **lifecycle**: Lifecycle configuration block, used to ignore changes to certain fields, avoiding unnecessary resource recreation after node pool creation due to changes in these fields

> Note: Node pools must specify the partition to which they belong, configured through the `partition` parameter. All nodes in the node pool will be deployed to the specified partition.

### 11. Preset Input Parameters Required for Resource Deployment

In this practice, some resources and data sources use input variables to assign configuration content, and these input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory, example content is as follows:

```hcl
vpc_name                     = "tf_test_vpc"
subnet_name                  = "tf_test_subnet"
eni_subnet_name              = "tf_test_eni_subnet"
cluster_name                 = "tf-test-cluster"
node_partition               = "center"
node_flavor_id               = "c7n.large.2"
node_flavor_performance_type = "computingv3"
node_name                    = "tf-test-node"
node_password                = "your_node_password"
data_volumes_configuration   = [
  {
    volumetype = "SSD"
    size       = 100
  }
]

node_pool_password = "your_node_pool_password"
node_pool_name     = "tf-test-node-pool"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content in the `tfvars` file when executing terraform commands, other naming requires adding `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify the parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="subnet_name=my-subnet"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 12. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating node partition
4. Run `terraform show` to view the created node partition

## Reference Information

- [Huawei Cloud CCE Product Documentation](https://support.huaweicloud.com/cce/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For CCE Node Partition](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/cce/node-partition)