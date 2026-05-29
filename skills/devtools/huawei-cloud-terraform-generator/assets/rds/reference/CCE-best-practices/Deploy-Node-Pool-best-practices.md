# Deploy Node Pool

## Application Scenario

Cloud Container Engine (CCE) is a high-reliability, high-performance enterprise-grade container management service that supports Kubernetes community native applications and tools. Node pool is a collection used to manage a group of node resources with the same configuration in a CCE cluster. Through node pools, you can uniformly manage node specifications, images, storage, and other configurations, and support automatic scaling functionality. By creating a node pool, you can quickly add compute nodes to a CCE cluster, achieving elastic scaling of container workloads. This best practice will introduce how to use Terraform to automatically deploy a CCE node pool, including querying availability zones and instance flavors, as well as creating VPC, subnet, Elastic IP, CCE cluster, key pair, and node pool.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [Compute Flavors Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Elastic IP Resource (huaweicloud\_vpc\_eip)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_eip)
- [CCE Cluster Resource (huaweicloud\_cce\_cluster)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cce_cluster)
- [Key Pair Resource (huaweicloud\_kps\_keypair)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/kps_keypair)
- [CCE Node Pool Resource (huaweicloud\_cce\_node\_pool)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cce_node_pool)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    ├── huaweicloud_vpc_subnet
    └── data.huaweicloud_compute_flavors
        └── huaweicloud_cce_node_pool

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_cce_cluster
            └── huaweicloud_cce_node_pool

huaweicloud_vpc_eip
    └── huaweicloud_cce_cluster
        └── huaweicloud_cce_node_pool

huaweicloud_kps_keypair
    └── huaweicloud_cce_node_pool
```

## Implementation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration introduction, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://hcbp.gitbook.io/huaweicloud-provider/product-introduction/prepare_before_deploy).

### 2. Query Availability Zones Required for Node Pool Resource Creation Through Data Source

Add the following script to the TF file (such as main.tf) to inform Terraform to perform a data source query, the query results are used to create node pool related resources:

```hcl
# Get all availability zone information in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for creating node pool related resources
data "huaweicloud_availability_zones" "test" {}
```

**Parameter Description**: This data source does not require additional parameters and queries all available availability zone information in the current region by default.

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

# Create VPC resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing network environment for node pool
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

variable "availability_zone" {
  description = "The availability zone where the CCE cluster will be created"
  type        = string
  default     = ""
}

# Create VPC subnet resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing network environment for node pool
resource "huaweicloud_vpc_subnet" "test" {
  count = var.subnet_id == "" ? 1 : 0

  vpc_id            = var.vpc_id != "" ? var.vpc_id : huaweicloud_vpc.test[0].id
  name              = var.subnet_name
  cidr              = var.subnet_cidr != "" ? var.subnet_cidr : cidrsubnet(huaweicloud_vpc.test[0].cidr, 4, 0)
  gateway_ip        = var.subnet_gateway_ip != "" ? var.subnet_gateway_ip : var.subnet_cidr != "" ? cidrhost(var.subnet_cidr, 1) : cidrhost(cidrsubnet(huaweicloud_vpc.test[0].cidr, 4, 0), 1)
  availability_zone = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test.names[0], null)
}
```

**Parameter Description**:

- **count**: The number of resource creations, used to control whether to create VPC subnet resource, only when `var.subnet_id` is empty, the VPC subnet resource is created
- **vpc\_id**: The VPC ID to which the subnet belongs, if the VPC ID is specified, use that value, otherwise assign by referencing the ID of the VPC resource (huaweicloud\_vpc.test\[0])
- **name**: The name of the subnet, assigned by referencing input variable `subnet_name`
- **cidr**: The CIDR block of the subnet, if the subnet CIDR is specified, use that value, otherwise automatically calculate based on the VPC's CIDR block using the `cidrsubnet` function
- **gateway\_ip**: The gateway IP of the subnet, if the gateway IP is specified, use that value, otherwise automatically calculate based on the subnet CIDR or automatically calculated subnet CIDR using the `cidrhost` function
- **availability\_zone**: The availability zone where the subnet is located, if the availability zone is specified, use that value, otherwise use the first availability zone from the availability zone list query data source

### 5. Create Elastic IP Resource (Optional)

Add the following script to the TF file to inform Terraform to create Elastic IP resources (if EIP address is not specified):

```hcl
variable "eip_address" {
  description = "The EIP address of the CCE cluster"
  type        = string
  default     = ""
}

variable "eip_type" {
  description = "The type of the EIP"
  type        = string
  default     = "5_bgp"
}

variable "bandwidth_name" {
  description = "The name of the bandwidth"
  type        = string
  default     = ""
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

# Create Elastic IP resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing public network access capability for node pool
resource "huaweicloud_vpc_eip" "test" {
  count = var.eip_address == "" ? 1 : 0

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

- **count**: The number of resource creations, used to control whether to create Elastic IP resource, only when `var.eip_address` is empty, the Elastic IP resource is created
- **publicip**: Public IP configuration block
  - **type**: Public IP type, assigned by referencing input variable `eip_type`, default is "5\_bgp" for full dynamic BGP
- **bandwidth**: Bandwidth configuration block
  - **name**: The name of the bandwidth, assigned by referencing input variable `bandwidth_name`
  - **size**: Bandwidth size (Mbps), assigned by referencing input variable `bandwidth_size`, default is 5
  - **share\_type**: Bandwidth share type, assigned by referencing input variable `bandwidth_share_type`, default is "PER" for dedicated
  - **charge\_mode**: Bandwidth charge mode, assigned by referencing input variable `bandwidth_charge_mode`, default is "traffic" for pay-per-traffic

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
  default     = "overlay_l2"
}

# Create CCE cluster resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for deploying and managing containerized applications
resource "huaweicloud_cce_cluster" "test" {
  name                   = var.cluster_name
  flavor_id              = var.cluster_flavor_id
  cluster_version        = var.cluster_version
  cluster_type           = var.cluster_type
  container_network_type = var.container_network_type
  vpc_id                 = var.vpc_id != "" ? var.vpc_id : huaweicloud_vpc.test[0].id
  subnet_id              = var.subnet_id != "" ? var.subnet_id : huaweicloud_vpc_subnet.test[0].id
  eip                    = var.eip_address != "" ? var.eip_address : huaweicloud_vpc_eip.test[0].address
}
```

**Parameter Description**:

- **name**: The name of the CCE cluster, assigned by referencing input variable `cluster_name`
- **flavor\_id**: The flavor ID of the CCE cluster, assigned by referencing input variable `cluster_flavor_id`, default is "cce.s1.small" for small cluster
- **cluster\_version**: The version of the CCE cluster, assigned by referencing input variable `cluster_version`, if null, the latest version will be used
- **cluster\_type**: The type of the CCE cluster, assigned by referencing input variable `cluster_type`, default is "VirtualMachine" for virtual machine type
- **container\_network\_type**: Container network type, assigned by referencing input variable `container_network_type`, default is "overlay\_l2" for L2 network
- **vpc\_id**: VPC ID, if the VPC ID is specified, use that value, otherwise assign by referencing the ID of the VPC resource (huaweicloud\_vpc.test\[0])
- **subnet\_id**: Subnet ID, if the subnet ID is specified, use that value, otherwise assign by referencing the ID of the VPC subnet resource (huaweicloud\_vpc\_subnet.test\[0])
- **eip**: Elastic IP address, if the EIP address is specified, use that value, otherwise assign by referencing the address of the Elastic IP resource (huaweicloud\_vpc\_eip.test\[0])

### 7. Query Instance Flavors Required for Node Pool Resource Creation Through Data Source

Add the following script to the TF file to inform Terraform to query instance flavors that meet the conditions:

```hcl
variable "node_performance_type" {
  description = "The performance type of the node"
  type        = string
  default     = "general"
}

variable "node_cpu_core_count" {
  description = "The CPU core count of the node"
  type        = number
  default     = 4
}

variable "node_memory_size" {
  description = "The memory size of the node"
  type        = number
  default     = 8
}

# Get all instance flavor information that meets specific conditions in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for creating node pool related resources
data "huaweicloud_compute_flavors" "test" {
  performance_type  = var.node_performance_type
  cpu_core_count    = var.node_cpu_core_count
  memory_size       = var.node_memory_size
  availability_zone = try(data.huaweicloud_availability_zones.test.names[0], null)
}
```

**Parameter Description**:

- **performance\_type**: Performance type, assigned through input variable `node_performance_type`, default is "general" for general purpose
- **cpu\_core\_count**: CPU core count, assigned through input variable `node_cpu_core_count`, default is 4 cores
- **memory\_size**: Memory size (GB), assigned through input variable `node_memory_size`, default is 8GB
- **availability\_zone**: The availability zone where the instance flavor is located, using the first availability zone from the availability zone list query data source

### 8. Create Key Pair Resource

Add the following script to the TF file to inform Terraform to create key pair resources:

```hcl
variable "keypair_name" {
  description = "The name of the keypair"
  type        = string
}

# Create key pair resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for accessing nodes in the node pool
resource "huaweicloud_kps_keypair" "test" {
  name = var.keypair_name
}
```

**Parameter Description**:

- **name**: The name of the key pair, assigned by referencing input variable `keypair_name`

### 9. Create CCE Node Pool Resource

Add the following script to the TF file to inform Terraform to create CCE node pool resources:

```hcl
variable "node_pool_type" {
  description = "The type of the node pool"
  type        = string
  default     = "vm"
}

variable "node_pool_name" {
  description = "The name of the node pool"
  type        = string
}

variable "node_pool_os_type" {
  description = "The OS type of the node pool"
  type        = string
  default     = "EulerOS 2.9"
}

variable "node_pool_initial_node_count" {
  description = "The initial node count of the node pool"
  type        = number
  default     = 2
}

variable "node_pool_min_node_count" {
  description = "The minimum node count of the node pool"
  type        = number
  default     = 2
}

variable "node_pool_max_node_count" {
  description = "The maximum node count of the node pool"
  type        = number
  default     = 10
}

variable "node_pool_scale_down_cooldown_time" {
  description = "The scale down cooldown time of the node pool"
  type        = number
  default     = 10
}

variable "node_pool_priority" {
  description = "The priority of the node pool"
  type        = number
  default     = 1
}

variable "node_pool_tags" {
  description = "The tags of the node pool"
  type        = map(string)
  default     = {}
}

variable "root_volume_type" {
  description = "The type of the root volume"
  type        = string
  default     = "SATA"
}

variable "root_volume_size" {
  description = "The size of the root volume"
  type        = number
  default     = 40
}

variable "data_volumes_configuration" {
  description = "The configuration of the data volumes"
  type = list(object({
    volumetype     = string
    size           = number
    count          = number
    kms_key_id     = optional(string, null)
    extend_params  = optional(map(string), null)
    virtual_spaces = optional(list(object({
      name            = string
      size            = string
      lvm_lv_type     = optional(string, null)
      lvm_path        = optional(string, null)
      runtime_lv_type = optional(string, null)
    })), [])
  }))

  default = [
    {
      volumetype = "SSD"
      size       = 100
      count      = 1
    }
  ]

  validation {
    condition     = length(var.data_volumes_configuration) > 0
    error_message = "At least one data volume must be provided."
  }
}

locals {
  flattened_data_volumes                                 = flatten([for v in var.data_volumes_configuration : [for i in range(v.count) : {
    volumetype    = v.volumetype
    size          = v.size
    kms_key_id    = v.kms_key_id
    extend_params = v.extend_params
  }]])
  default_data_volumes_configuration_with_virtual_spaces = [for v in slice(var.data_volumes_configuration, 0, 1) : v if length(v.virtual_spaces) > 0]
  user_data_volumes_configuration_with_virtual_spaces    = [for i, v in  [for v in slice(var.data_volumes_configuration, 1, length(var.data_volumes_configuration)) : v if length(v.virtual_spaces) > 0] : {
    select_name    = "user${i+1}"
    volumetype     = v.volumetype
    size           = v.size
    count          = v.count
    kms_key_id     = v.kms_key_id
    extend_params  = v.extend_params
    virtual_spaces = v.virtual_spaces
  }]
}

# Create CCE node pool resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for managing nodes in the cluster
resource "huaweicloud_cce_node_pool" "test" {
  cluster_id               = huaweicloud_cce_cluster.test.id
  type                     = var.node_pool_type
  name                     = var.node_pool_name
  flavor_id                = try(data.huaweicloud_compute_flavors.test.flavors[0].id, null)
  availability_zone        = try(data.huaweicloud_availability_zones.test.names[0], null)
  os                       = var.node_pool_os_type
  initial_node_count       = var.node_pool_initial_node_count
  min_node_count           = var.node_pool_min_node_count
  max_node_count           = var.node_pool_max_node_count
  scale_down_cooldown_time = var.node_pool_scale_down_cooldown_time
  priority                 = var.node_pool_priority
  key_pair                 = huaweicloud_kps_keypair.test.name
  tags                     = var.node_pool_tags

  root_volume {
    volumetype = var.root_volume_type
    size       = var.root_volume_size
  }

  dynamic "data_volumes" {
    for_each = local.flattened_data_volumes

    content {
      volumetype    = data_volumes.value.volumetype
      size          = data_volumes.value.size
      kms_key_id    = data_volumes.value.kms_key_id
      extend_params = data_volumes.value.extend_params
    }
  }

  dynamic "storage" {
    for_each = length(local.default_data_volumes_configuration_with_virtual_spaces) + length(local.user_data_volumes_configuration_with_virtual_spaces) > 0 ? [1] : []

    content {
      # Default selector which is used to select the data volumes that used by CCE
      dynamic "selectors" {
        for_each = local.default_data_volumes_configuration_with_virtual_spaces

        content {
          name                           = "cceUse"
          type                           = "evs"
          match_label_volume_type        = selectors.value.volumetype
          match_label_size               = selectors.value.size
          match_label_count              = selectors.value.count
          match_label_metadata_encrypted = selectors.value.kms_key_id != "" && selectors.value.kms_key_id != null ? "1" : "0"
          match_label_metadata_cmkid     = selectors.value.kms_key_id != "" ? selectors.value.kms_key_id : null
        }
      }

      # User data selector which is used to select the data volumes that used by user
      dynamic "selectors" {
        for_each = local.user_data_volumes_configuration_with_virtual_spaces

        content {
          name                           = selectors.value.select_name
          type                           = "evs"
          match_label_volume_type        = selectors.value.volumetype
          match_label_size               = selectors.value.size
          match_label_count              = selectors.value.count
          match_label_metadata_encrypted = selectors.value.kms_key_id != "" && selectors.value.kms_key_id != null ? "1" : "0"
          match_label_metadata_cmkid     = selectors.value.kms_key_id != "" ? selectors.value.kms_key_id : null
        }
      }

      # Default group which is used to group the data volumes that used by CCE
      dynamic "groups" {
        for_each = local.default_data_volumes_configuration_with_virtual_spaces

        content {
          name           = "vgpaas"
          cce_managed    = true
          selector_names = ["cceUse"]

          dynamic "virtual_spaces" {
            for_each = groups.value.virtual_spaces

            content {
              name            = virtual_spaces.value.name
              size            = virtual_spaces.value.size
              lvm_lv_type     = virtual_spaces.value.lvm_lv_type
              lvm_path        = virtual_spaces.value.lvm_path
              runtime_lv_type = virtual_spaces.value.runtime_lv_type
            }
          }
        }
      }

      # User data group which is used to group the data volumes that used by user
      dynamic "groups" {
        for_each = local.user_data_volumes_configuration_with_virtual_spaces

        content {
          name           = "vg${groups.value.select_name}"
          selector_names = [groups.value.select_name]

          dynamic "virtual_spaces" {
            for_each = groups.value.virtual_spaces

            content {
              name            = virtual_spaces.value.name
              size            = virtual_spaces.value.size
              lvm_lv_type     = virtual_spaces.value.lvm_lv_type
              lvm_path        = virtual_spaces.value.lvm_path
              runtime_lv_type = virtual_spaces.value.runtime_lv_type
            }
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [
      flavor_id,
      availability_zone,
      initial_node_count
    ]
  }

  depends_on = [
    huaweicloud_kps_keypair.test
  ]
}
```

**Parameter Description**:

- **cluster\_id**: CCE cluster ID, assigned by referencing the ID of the CCE cluster resource (huaweicloud\_cce\_cluster.test)
- **type**: The type of the node pool, assigned by referencing input variable `node_pool_type`, default is "vm" for virtual machine type
- **name**: The name of the node pool, assigned by referencing input variable `node_pool_name`
- **flavor\_id**: Node flavor ID, assigned by using the first flavor ID from the instance flavor list query data source
- **availability\_zone**: The availability zone where the nodes are located, assigned by using the first availability zone from the availability zone list query data source
- **os**: The operating system type of the nodes, assigned by referencing input variable `node_pool_os_type`, default is "EulerOS 2.9"
- **initial\_node\_count**: Initial node count, assigned by referencing input variable `node_pool_initial_node_count`, default is 2
- **min\_node\_count**: Minimum node count, assigned by referencing input variable `node_pool_min_node_count`, default is 2
- **max\_node\_count**: Maximum node count, assigned by referencing input variable `node_pool_max_node_count`, default is 10
- **scale\_down\_cooldown\_time**: Scale down cooldown time (minutes), assigned by referencing input variable `node_pool_scale_down_cooldown_time`, default is 10 minutes
- **priority**: The priority of the node pool, assigned by referencing input variable `node_pool_priority`, default is 1, higher values indicate higher priority
- **key\_pair**: Key pair name, assigned by referencing the name of the key pair resource (huaweicloud\_kps\_keypair.test)
- **tags**: Node pool tags, assigned by referencing input variable `node_pool_tags`, used for resource classification and management
- **root\_volume**: Root volume configuration block
  - **volumetype**: Root volume type, assigned by referencing input variable `root_volume_type`, default is "SATA"
  - **size**: Root volume size (GB), assigned by referencing input variable `root_volume_size`, default is 40GB
- **data\_volumes**: Data volume configuration block, creates multiple data volume configurations through dynamic block (dynamic block) based on local variable `flattened_data_volumes`
  - **volumetype**: Data volume type, assigned through `volumetype` in local variable `flattened_data_volumes`
  - **size**: Data volume size (GB), assigned through `size` in local variable `flattened_data_volumes`
  - **kms\_key\_id**: KMS key ID, assigned through `kms_key_id` in local variable `flattened_data_volumes`, used for data volume encryption
  - **extend\_params**: Extended parameters, assigned through `extend_params` in local variable `flattened_data_volumes`
- **storage**: Storage configuration block, used to configure selectors, groups, and virtual spaces for data volumes, only created when data volume configuration includes virtual spaces
  - **selectors**: Selector configuration block, used to select data volumes that meet conditions
    - **name**: Selector name, "cceUse" for CCE-used data volumes, "user1", "user2", etc. for user data volumes
    - **type**: Selector type, set to "evs" for cloud volumes
    - **match\_label\_volume\_type**: Match label - volume type, assigned through `volumetype` in data volume configuration
    - **match\_label\_size**: Match label - size, assigned through `size` in data volume configuration
    - **match\_label\_count**: Match label - count, assigned through `count` in data volume configuration
    - **match\_label\_metadata\_encrypted**: Match label - encryption identifier, "1" if KMS key is configured, otherwise "0"
    - **match\_label\_metadata\_cmkid**: Match label - KMS key ID, use this value if KMS key is configured, otherwise null
  - **groups**: Group configuration block, used to group data volumes and configure virtual spaces
    - **name**: Group name, "vgpaas" for CCE-used data volumes, "vguser1", "vguser2", etc. for user data volumes
    - **cce\_managed**: Whether managed by CCE, true for CCE-used data volumes, false for user data volumes
    - **selector\_names**: Selector name list, references corresponding selector names
    - **virtual\_spaces**: Virtual space configuration block, creates virtual spaces through dynamic block based on `virtual_spaces` in data volume configuration
      - **name**: Virtual space name, such as "kubernetes", "runtime", "user", etc.
      - **size**: Virtual space size, can be a percentage (e.g., "10%") or fixed size
      - **lvm\_lv\_type**: LVM logical volume type, e.g., "linear" for linear volume
      - **lvm\_path**: LVM path, used to specify mount path, e.g., "/workspace"
      - **runtime\_lv\_type**: Runtime logical volume type

> Note: The `lifecycle` block with `ignore_changes` is used to ignore changes to certain fields, avoiding unnecessary resource recreation after node pool creation due to changes in these fields. `depends_on` is used to ensure the key pair resource is created before the node pool.

### 10. Preset Input Parameters Required for Resource Deployment

In this practice, some resources and data sources use input variables to assign configuration content, and these input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory, example content is as follows:

```hcl
vpc_name              = "tf_test_vpc"
subnet_name           = "tf_test_subnet"
bandwidth_name        = "tf_test_bandwidth"
bandwidth_size        = 5
cluster_name          = "tf-test-cluster"
node_performance_type = "computingv3"
keypair_name          = "tf_test_keypair"
node_pool_name        = "tf-test-node-pool"
node_pool_tags        = {
  "owner" = "terraform"
}

root_volume_size           = 40
root_volume_type           = "SSD"
data_volumes_configuration = [
  {
    volumetype     = "SSD"
    size           = 100
    count          = 2
    virtual_spaces = [
      {
        name        = "kubernetes"
        size        = "10%"
        lvm_lv_type = "linear"
      },
      {
        name = "runtime"
        size = "90%"
      }
    ]
  },
  {
    volumetype     = "SSD"
    size           = 100
    count          = 1
    virtual_spaces = [
      {
        name        = "user"
        size        = "100%"
        lvm_lv_type = "linear"
        lvm_path    = "/workspace"
      }
    ]
  }
]
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

### 11. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating node pool
4. Run `terraform show` to view the created node pool

## Reference Information

- [Huawei Cloud CCE Product Documentation](https://support.huaweicloud.com/cce/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For CCE Node Pool](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/cce/node-pool)