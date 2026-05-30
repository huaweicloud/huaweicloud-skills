# Deploy Standard Cluster

## Application Scenario

Cloud Container Engine (CCE) is a high-reliability, high-performance enterprise-grade container management service that supports Kubernetes community native applications and tools. Standard cluster is a cluster type provided by CCE, suitable for enterprise production environments, supporting complete Kubernetes functionality, providing high availability and scalability. By creating a Standard cluster, you can quickly deploy and manage containerized applications, implement microservices architecture and DevOps practices. This best practice will introduce how to use Terraform to automatically deploy a CCE Standard cluster, including querying availability zones, as well as creating VPC, subnet, Elastic IP, and CCE cluster.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Elastic IP Resource (huaweicloud\_vpc\_eip)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_eip)
- [CCE Cluster Resource (huaweicloud\_cce\_cluster)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cce_cluster)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── huaweicloud_vpc_subnet

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_cce_cluster

huaweicloud_vpc_eip
    └── huaweicloud_cce_cluster
```

## Implementation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration introduction, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://hcbp.gitbook.io/huaweicloud-provider/product-introduction/prepare_before_deploy).

### 2. Query Availability Zones Required for Standard Cluster Resource Creation Through Data Source

Add the following script to the TF file (such as main.tf) to inform Terraform to perform a data source query, the query results are used to create Standard cluster related resources:

```hcl
# Get all availability zone information in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for creating Standard cluster related resources
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

# Create VPC resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing network environment for Standard cluster
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

# Create VPC subnet resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing network environment for Standard cluster
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

# Create Elastic IP resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing public network access capability for Standard cluster
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
  name                   = var.cluster_name
  flavor_id              = var.cluster_flavor_id
  cluster_version        = var.cluster_version
  cluster_type           = var.cluster_type
  container_network_type = var.container_network_type
  vpc_id                 = var.vpc_id != "" ? var.vpc_id : huaweicloud_vpc.test[0].id
  subnet_id              = var.subnet_id != "" ? var.subnet_id : huaweicloud_vpc_subnet.test[0].id
  eip                    = var.eip_address != "" ? var.eip_address : huaweicloud_vpc_eip.test[0].address
  description            = var.cluster_description
  tags                   = var.cluster_tags
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
- **description**: Cluster description information, assigned by referencing input variable `cluster_description`
- **tags**: Cluster tags, assigned by referencing input variable `cluster_tags`, used for resource classification and management

> Note: The `cluster_version` parameter is optional. If set to null, the system will automatically use the latest available version. Setting `cluster_type` to "VirtualMachine" means using virtual machine nodes, or it can be set to "BareMetal" to use bare metal nodes.

### 7. Preset Input Parameters Required for Resource Deployment

In this practice, some resources and data sources use input variables to assign configuration content, and these input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory, example content is as follows:

```hcl
vpc_name            = "tf_test_vpc"
subnet_name         = "tf_test_subnet"
bandwidth_name      = "tf_test_bandwidth"
bandwidth_size      = 5
cluster_name        = "tf-test-cluster"
cluster_description = "Created by terraform script"
cluster_tags        = {
  owner = "terraform"
}
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

### 8. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating Standard cluster
4. Run `terraform show` to view the created Standard cluster

## Reference Information

- [Huawei Cloud CCE Product Documentation](https://support.huaweicloud.com/cce/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For CCE Standard Cluster](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/cce/standard-cluster)

# Deploy Turbo Cluster

## Application Scenario

Cloud Container Engine (CCE) is a high-reliability, high-performance enterprise-grade container management service that supports Kubernetes community native applications and tools. Turbo cluster is a high-performance cluster type provided by CCE, using ENI (Elastic Network Interface) network mode, providing higher network performance and lower latency, suitable for production environments with high network performance requirements. By creating a Turbo cluster, you can quickly deploy and manage high-performance containerized applications, implement microservices architecture and DevOps practices. This best practice will introduce how to use Terraform to automatically deploy a CCE Turbo cluster, including querying availability zones, as well as creating VPC, subnet, ENI subnet, Elastic IP, and CCE cluster.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Elastic IP Resource (huaweicloud\_vpc\_eip)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_eip)
- [CCE Cluster Resource (huaweicloud\_cce\_cluster)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cce_cluster)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── huaweicloud_vpc_subnet

huaweicloud_vpc
    ├── huaweicloud_vpc_subnet
    │   └── huaweicloud_cce_cluster
    └── huaweicloud_vpc_subnet (ENI subnet)
        └── huaweicloud_cce_cluster

huaweicloud_vpc_eip
    └── huaweicloud_cce_cluster
```

## Implementation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration introduction, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://hcbp.gitbook.io/huaweicloud-provider/product-introduction/prepare_before_deploy).

### 2. Query Availability Zones Required for Turbo Cluster Resource Creation Through Data Source

Add the following script to the TF file (such as main.tf) to inform Terraform to perform a data source query, the query results are used to create Turbo cluster related resources:

```hcl
# Get all availability zone information in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for creating Turbo cluster related resources
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

# Create VPC resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing network environment for Turbo cluster
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

# Create VPC subnet resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing network environment for Turbo cluster
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

# Create ENI subnet resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing ENI network environment for Turbo cluster
resource "huaweicloud_vpc_subnet" "eni" {
  count = var.eni_ipv4_subnet_id == "" ? 1 : 0

  vpc_id            = var.vpc_id != "" ? var.vpc_id : huaweicloud_vpc.test[0].id
  name              = var.eni_subnet_name
  cidr              = var.eni_subnet_cidr != "" ? var.eni_subnet_cidr : cidrsubnet(huaweicloud_vpc.test[0].cidr, 4, 1)
  gateway_ip        = var.subnet_gateway_ip != "" ? var.subnet_gateway_ip : var.eni_subnet_cidr != "" ? cidrhost(var.eni_subnet_cidr, 1) : cidrhost(cidrsubnet(huaweicloud_vpc.test[0].cidr, 4, 1), 1)
  availability_zone = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test.names[0], null)
}
```

**Parameter Description**:

- **count**: The number of resource creations, used to control whether to create ENI subnet resource, only when `var.eni_ipv4_subnet_id` is empty, the ENI subnet resource is created
- **vpc\_id**: The VPC ID to which the ENI subnet belongs, if the VPC ID is specified, use that value, otherwise assign by referencing the ID of the VPC resource (huaweicloud\_vpc.test\[0])
- **name**: The name of the ENI subnet, assigned by referencing input variable `eni_subnet_name`
- **cidr**: The CIDR block of the ENI subnet, if the ENI subnet CIDR is specified, use that value, otherwise automatically calculate based on the VPC's CIDR block using the `cidrsubnet` function (using a different subnet index to avoid conflicts with the regular subnet)
- **gateway\_ip**: The gateway IP of the ENI subnet, if the gateway IP is specified, use that value, otherwise automatically calculate based on the ENI subnet CIDR or automatically calculated ENI subnet CIDR using the `cidrhost` function
- **availability\_zone**: The availability zone where the ENI subnet is located, if the availability zone is specified, use that value, otherwise use the first availability zone from the availability zone list query data source

> Note: ENI subnet is a unique network configuration for Turbo clusters, used to provide high-performance network connections. The ENI subnet must be in the same VPC as the regular subnet, but must use a different CIDR block to avoid IP address conflicts.

### 6. Create Elastic IP Resource (Optional)

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

# Create Elastic IP resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for providing public network access capability for Turbo cluster
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

### 7. Create CCE Cluster Resource

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

# Create CCE cluster resource in the specified region (defaults to inheriting the region specified in the current provider block when region parameter is missing) for deploying and managing high-performance containerized applications
resource "huaweicloud_cce_cluster" "test" {
  name                   = var.cluster_name
  flavor_id              = var.cluster_flavor_id
  cluster_version        = var.cluster_version
  cluster_type           = var.cluster_type
  container_network_type = var.container_network_type
  vpc_id                 = var.vpc_id != "" ? var.vpc_id : huaweicloud_vpc.test[0].id
  subnet_id              = var.subnet_id != "" ? var.subnet_id : huaweicloud_vpc_subnet.test[0].id
  eni_subnet_id          = var.eni_ipv4_subnet_id != "" ? var.eni_ipv4_subnet_id : huaweicloud_vpc_subnet.eni[0].ipv4_subnet_id
  eip                    = var.eip_address != "" ? var.eip_address : huaweicloud_vpc_eip.test[0].address
  description            = var.cluster_description
  tags                   = var.cluster_tags
}
```

**Parameter Description**:

- **name**: The name of the CCE cluster, assigned by referencing input variable `cluster_name`
- **flavor\_id**: The flavor ID of the CCE cluster, assigned by referencing input variable `cluster_flavor_id`, default is "cce.s1.small" for small cluster
- **cluster\_version**: The version of the CCE cluster, assigned by referencing input variable `cluster_version`, if null, the latest version will be used
- **cluster\_type**: The type of the CCE cluster, assigned by referencing input variable `cluster_type`, default is "VirtualMachine" for virtual machine type
- **container\_network\_type**: Container network type, assigned by referencing input variable `container_network_type`, default is "eni" for ENI network mode (Turbo clusters must use ENI network)
- **vpc\_id**: VPC ID, if the VPC ID is specified, use that value, otherwise assign by referencing the ID of the VPC resource (huaweicloud\_vpc.test\[0])
- **subnet\_id**: Subnet ID, if the subnet ID is specified, use that value, otherwise assign by referencing the ID of the VPC subnet resource (huaweicloud\_vpc\_subnet.test\[0])
- **eni\_subnet\_id**: ENI subnet ID, if the ENI subnet ID is specified, use that value, otherwise assign by referencing the IPv4 subnet ID of the ENI subnet resource (huaweicloud\_vpc\_subnet.eni\[0])
- **eip**: Elastic IP address, if the EIP address is specified, use that value, otherwise assign by referencing the address of the Elastic IP resource (huaweicloud\_vpc\_eip.test\[0])
- **description**: Cluster description information, assigned by referencing input variable `cluster_description`
- **tags**: Cluster tags, assigned by referencing input variable `cluster_tags`, used for resource classification and management

> Note: Turbo clusters must use ENI network mode (`container_network_type` set to "eni"), which is the main difference between Turbo clusters and Standard clusters. ENI network mode provides higher network performance and lower latency, suitable for production environments with high network performance requirements. The `eni_subnet_id` parameter is a unique configuration for Turbo clusters and must specify an independent ENI subnet.

### 8. Preset Input Parameters Required for Resource Deployment

In this practice, some resources and data sources use input variables to assign configuration content, and these input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory, example content is as follows:

```hcl
vpc_name            = "tf_test_vpc"
subnet_name         = "tf_test_subnet"
eni_subnet_name     = "tf_test_eni_subnet"
bandwidth_name      = "tf_test_bandwidth"
bandwidth_size      = 5
cluster_name        = "tf-test-cluster"
cluster_description = "Created by terraform script"
cluster_tags        = {
  owner = "terraform"
}
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

### 9. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating Turbo cluster
4. Run `terraform show` to view the created Turbo cluster

## Reference Information

- [Huawei Cloud CCE Product Documentation](https://support.huaweicloud.com/cce/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For CCE Turbo Cluster](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/cce/turbo-cluster)