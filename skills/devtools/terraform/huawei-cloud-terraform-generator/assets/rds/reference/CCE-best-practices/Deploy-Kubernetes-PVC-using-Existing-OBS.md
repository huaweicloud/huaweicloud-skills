# Deploy Kubernetes PVC using Existing OBS

## Application Scenario

Cloud Container Engine (CCE) is a high-reliability, high-performance enterprise-grade container management service that supports Kubernetes community native applications and tools. Persistent Volume Claim (PVC) is an abstract interface in Kubernetes for requesting storage resources, allowing Pods to request storage resources declaratively without caring about the specific implementation of the underlying storage. Object Storage Service (OBS) is a highly available, highly reliable, high-performance, secure, and low-cost object storage service provided by Huawei Cloud, which can serve as a persistent storage backend for Kubernetes clusters.

By using OBS buckets as persistent storage for Kubernetes, you can provide scalable and highly available storage solutions for container applications. This approach is particularly suitable for application scenarios that require shared storage, large-capacity storage, or cross-availability zone data replication. This best practice will introduce how to use Terraform to automatically deploy a complete solution for managing PVC with OBS, including querying availability zones and instance flavors, as well as creating infrastructure such as VPC, subnet, Elastic IP, CCE cluster, node, OBS bucket, and Kubernetes Secret, Persistent Volume, Persistent Volume Claim, and Deployment.

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
- [CCE Node Resource (huaweicloud\_cce\_node)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cce_node)
- [OBS Bucket Resource (huaweicloud\_obs\_bucket)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket)
- [Kubernetes Secret Resource (kubernetes\_secret)](https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs/resources/secret)
- [Kubernetes Persistent Volume Resource (kubernetes\_persistent\_volume)](https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs/resources/persistent_volume)
- [Kubernetes Persistent Volume Claim Resource (kubernetes\_persistent\_volume\_claim)](https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs/resources/persistent_volume_claim)
- [Kubernetes Deployment Resource (kubernetes\_deployment)](https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs/resources/deployment)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    ├── huaweicloud_vpc_subnet
    └── data.huaweicloud_compute_flavors
        └── huaweicloud_cce_node

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_cce_cluster
            └── huaweicloud_cce_node
                └── kubernetes_deployment

huaweicloud_vpc_eip
    └── huaweicloud_cce_cluster
        └── huaweicloud_cce_node
            └── kubernetes_deployment

huaweicloud_kps_keypair
    └── huaweicloud_cce_node
        └── kubernetes_deployment

huaweicloud_obs_bucket
    └── kubernetes_persistent_volume
        └── kubernetes_persistent_volume_claim
            └── kubernetes_deployment

kubernetes_secret
    ├── kubernetes_persistent_volume
    └── kubernetes_persistent_volume_claim
```

## Implementation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration introduction, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://hcbp.gitbook.io/huaweicloud-provider/product-introduction/prepare_before_deploy).

### 2. Configure Kubernetes Provider

Since this best practice requires using the Kubernetes provider to create Kubernetes resources, you need to configure the Kubernetes provider in the providers.tf file. Add the following script to the providers.tf file:

```hcl
terraform {
  required_version = ">= 1.9.0"

  required_providers {
    ...
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 1.6.2"
    }
  }
}

variable "eip_address" {
  description = "The EIP address of the CCE cluster"
  type        = string
  default     = ""
}

# Configure Kubernetes provider for creating Kubernetes resources
provider "kubernetes" {
  host                   = "https://%{ if var.eip_address != "" }${var.eip_address}:5443%{ else }${huaweicloud_vpc_eip.test[0].address}:5443%{ endif }"
  cluster_ca_certificate = base64decode(huaweicloud_cce_cluster.test.certificate_clusters[0].certificate_authority_data)
  client_certificate     = base64decode(huaweicloud_cce_cluster.test.certificate_users[0].client_certificate_data)
  client_key             = base64decode(huaweicloud_cce_cluster.test.certificate_users[0].client_key_data)
}
```

**Parameter Description**:

- **host**: The address of the Kubernetes API server, if the EIP address is specified, use that value, otherwise reference the address of the Elastic IP resource (huaweicloud\_vpc\_eip.test\[0]), port is 5443
- **cluster\_ca\_certificate**: Cluster CA certificate, obtained and decoded from the certificate information of the CCE cluster resource (huaweicloud\_cce\_cluster.test)
- **client\_certificate**: Client certificate, obtained and decoded from the certificate information of the CCE cluster resource (huaweicloud\_cce\_cluster.test)
- **client\_key**: Client key, obtained and decoded from the certificate information of the CCE cluster resource (huaweicloud\_cce\_cluster.test)

> Note: The Kubernetes provider needs to access the CCE cluster's API server, so it needs to configure the correct cluster address and certificate information. This information can be obtained from the CCE cluster resource.

### 3. Query Availability Zones Required for PVC Resource Creation Through Data Source

Add the following script to the TF file (such as main.tf) to inform Terraform to perform a data source query, the query results are used to create PVC related resources:

```hcl
variable "availability_zone" {
  description = "The availability zone where the resources will be created"
  type        = string
  default     = ""
  nullable    = false
}

# Get all availability zone information in the specified region (when the region parameter is omitted, it defaults to the region specified in the current provider block), used for creating PVC related resources
data "huaweicloud_availability_zones" "test" {
  count = var.availability_zone == "" ? 1 : 0
}
```

**Parameter Description**:

- **count**: The number of data source creations, used to control whether to execute the availability zone list query data source, only when `var.availability_zone` is empty, create the data source (i.e., execute the availability zone list query)

### 4. Create VPC Resource (Optional)

Add the following script to the TF file to inform Terraform to create a VPC resource (if VPC ID and subnet ID are not specified):

```hcl
variable "vpc_id" {
  description = "The ID of the VPC"
  type        = string
  default     = ""
  nullable    = false
}

variable "vpc_name" {
  description = "The name of the VPC"
  type        = string
  default     = ""
  nullable    = false

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

# Create VPC resource in the specified region (when the region parameter is omitted, it defaults to the region specified in the current provider block), used for providing network environment for PVC
resource "huaweicloud_vpc" "test" {
  count = var.vpc_id == "" && var.subnet_id == "" ? 1 : 0

  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **count**: The number of resource creations, used to control whether to create VPC resource, only when both `var.vpc_id` and `var.subnet_id` are empty, create VPC resource
- **name**: The name of the VPC, assigned by referencing the input variable `vpc_name`
- **cidr**: The CIDR block of the VPC, assigned by referencing the input variable `vpc_cidr`, default is "192.168.0.0/16"

### 5. Create VPC Subnet Resource (Optional)

Add the following script to the TF file to inform Terraform to create a VPC subnet resource (if subnet ID is not specified):

```hcl
variable "subnet_id" {
  description = "The ID of the subnet"
  type        = string
  default     = ""
  nullable    = false
}

variable "subnet_name" {
  description = "The name of the subnet"
  type        = string
  default     = ""
  nullable    = false

  validation {
    condition     = var.subnet_id == "" || var.subnet_name == ""
    error_message = "subnet_name must be provided if subnet_id is not provided."
  }
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

# Create VPC subnet resource in the specified region (when the region parameter is omitted, it defaults to the region specified in the current provider block), used for providing network environment for PVC
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

- **count**: The number of resource creations, used to control whether to create VPC subnet resource, only when `var.subnet_id` is empty, create VPC subnet resource
- **vpc\_id**: The VPC ID to which the subnet belongs, if VPC ID is specified, use that value, otherwise reference the ID of the VPC resource (huaweicloud\_vpc.test\[0]) for assignment
- **name**: The name of the subnet, assigned by referencing the input variable `subnet_name`
- **cidr**: The CIDR block of the subnet, if subnet CIDR is specified, use that value, otherwise automatically calculate based on the VPC's CIDR block through the `cidrsubnet` function
- **gateway\_ip**: The gateway IP of the subnet, if gateway IP is specified, use that value, otherwise automatically calculate based on subnet CIDR or automatically calculated subnet CIDR through the `cidrhost` function
- **availability\_zone**: The availability zone where the subnet is located, if availability zone is specified, use that value, otherwise use the first availability zone from the availability zone list query data source

### 6. Create Elastic IP Resource (Optional)

Add the following script to the TF file to inform Terraform to create an Elastic IP resource (if EIP address is not specified):

```hcl
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

# Create Elastic IP resource in the specified region (when the region parameter is omitted, it defaults to the region specified in the current provider block), used for providing public network access capability for PVC
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

- **count**: The number of resource creations, used to control whether to create Elastic IP resource, only when `var.eip_address` is empty, create Elastic IP resource
- **publicip**: Public IP configuration block
  - **type**: Public IP type, assigned by referencing the input variable `eip_type`, default is "5\_bgp" indicating full dynamic BGP
- **bandwidth**: Bandwidth configuration block
  - **name**: The name of the bandwidth, assigned by referencing the input variable `bandwidth_name`
  - **size**: Bandwidth size (Mbps), assigned by referencing the input variable `bandwidth_size`, default is 5
  - **share\_type**: Bandwidth sharing type, assigned by referencing the input variable `bandwidth_share_type`, default is "PER" indicating dedicated
  - **charge\_mode**: Bandwidth billing mode, assigned by referencing the input variable `bandwidth_charge_mode`, default is "traffic" indicating pay-per-traffic

### 7. Create CCE Cluster Resource

Add the following script to the TF file to inform Terraform to create a CCE cluster resource:

```hcl
variable "cluster_name" {
  description = "The name of the CCE cluster"
  type        = string
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

variable "authentication_mode" {
  description = "The mode of the CCE cluster"
  type        = string
  default     = "rbac"
}

variable "delete_all_resources_on_terminal" {
  description = "Whether to delete all resources on terminal"
  type        = bool
  default     = true
}

variable "enterprise_project_id" {
  description = "The enterprise project ID of the CCE cluster"
  type        = string
  default     = "0"
}

variable "eip_address" {
  description = "The EIP address of the CCE cluster"
  type        = string
  default     = ""
  nullable    = false
}

# Create CCE cluster resource in the specified region (when the region parameter is omitted, it defaults to the region specified in the current provider block), used for deploying and managing containerized applications
resource "huaweicloud_cce_cluster" "test" {
  name                   = var.cluster_name
  flavor_id              = var.cluster_flavor_id
  cluster_version        = var.cluster_version
  cluster_type           = var.cluster_type
  container_network_type = var.container_network_type
  vpc_id                 = var.vpc_id != "" ? var.vpc_id : huaweicloud_vpc.test[0].id
  subnet_id              = var.subnet_id != "" ? var.subnet_id : huaweicloud_vpc_subnet.test[0].id
  eip                    = var.eip_address != "" ? var.eip_address : huaweicloud_vpc_eip.test[0].address
  authentication_mode    = var.authentication_mode
  delete_all             = var.delete_all_resources_on_terminal ? "true" : "false"
  enterprise_project_id  = var.enterprise_project_id
}
```

**Parameter Description**:

- **name**: The name of the CCE cluster, assigned by referencing the input variable `cluster_name`
- **flavor\_id**: The flavor ID of the CCE cluster, assigned by referencing the input variable `cluster_flavor_id`, default is "cce.s1.small" indicating small-scale cluster
- **cluster\_version**: The version of the CCE cluster, assigned by referencing the input variable `cluster_version`, if null, use the latest version
- **cluster\_type**: The type of the CCE cluster, assigned by referencing the input variable `cluster_type`, default is "VirtualMachine" indicating virtual machine type
- **container\_network\_type**: Container network type, assigned by referencing the input variable `container_network_type`, default is "overlay\_l2" indicating L2 network
- **vpc\_id**: VPC ID, if VPC ID is specified, use that value, otherwise reference the ID of the VPC resource (huaweicloud\_vpc.test\[0]) for assignment
- **subnet\_id**: Subnet ID, if subnet ID is specified, use that value, otherwise reference the ID of the VPC subnet resource (huaweicloud\_vpc\_subnet.test\[0]) for assignment
- **eip**: Elastic public IP address, if EIP address is specified, use that value, otherwise reference the address of the Elastic IP resource (huaweicloud\_vpc\_eip.test\[0]) for assignment
- **authentication\_mode**: Cluster authentication mode, assigned by referencing the input variable `authentication_mode`, default is "rbac" indicating role-based access control
- **delete\_all**: Whether to delete all resources on termination, assigned by referencing the input variable `delete_all_resources_on_terminal`, default is "true" indicating delete all resources
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing the input variable `enterprise_project_id`, default is "0" indicating default enterprise project

### 8. Query Instance Flavors Required for Node Resource Creation Through Data Source

Add the following script to the TF file to inform Terraform to query instance flavors that meet the conditions:

```hcl
variable "node_flavor_id" {
  description = "The flavor ID of the node"
  type        = string
  default     = ""
  nullable    = false
}

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

# Get all instance flavor information that meets specific conditions in the specified region (when the region parameter is omitted, it defaults to the region specified in the current provider block), used for creating PVC related resources
data "huaweicloud_compute_flavors" "test" {
  count = var.node_flavor_id == "" ? 1 : 0

  performance_type  = var.node_performance_type
  cpu_core_count    = var.node_cpu_core_count
  memory_size       = var.node_memory_size
  availability_zone = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test[0].names[0], null)
}
```

**Parameter Description**:

- **count**: The number of data source queries, used to control whether to query instance flavor information, only when `var.node_flavor_id` is empty, query instance flavor information
- **performance\_type**: Performance type, assigned by referencing the input variable `node_performance_type`, default is "general" indicating general-purpose
- **cpu\_core\_count**: CPU core count, assigned by referencing the input variable `node_cpu_core_count`, default is 4 cores
- **memory\_size**: Memory size (GB), assigned by referencing the input variable `node_memory_size`, default is 8GB
- **availability\_zone**: The availability zone where the instance flavor is located, if availability zone is specified, use that value, otherwise use the first availability zone from the availability zone list query data source

### 9. Create Key Pair Resource

Add the following script to the TF file to inform Terraform to create a key pair resource:

```hcl
variable "keypair_name" {
  description = "The name of the keypair"
  type        = string
}

# Create key pair resource in the specified region (when the region parameter is omitted, it defaults to the region specified in the current provider block), used for accessing nodes
resource "huaweicloud_kps_keypair" "test" {
  name = var.keypair_name
}
```

**Parameter Description**:

- **name**: The name of the key pair, assigned by referencing the input variable `keypair_name`

### 10. Create CCE Node Resource

Add the following script to the TF file to inform Terraform to create a CCE node resource:

```hcl
variable "node_name" {
  description = "The name of the node"
  type        = string
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
    volumetype = string
    size       = number
  }))

  default  = []
  nullable = false
}

# Create CCE node resource in the specified region (when the region parameter is omitted, it defaults to the region specified in the current provider block), used for providing computing capability for the cluster
resource "huaweicloud_cce_node" "test" {
  cluster_id        = huaweicloud_cce_cluster.test.id
  name              = var.node_name
  flavor_id         = var.node_flavor_id != "" ? var.node_flavor_id : try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, null)
  availability_zone = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test[0].names[0], null)
  key_pair          = huaweicloud_kps_keypair.test.name

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
}
```

**Parameter Description**:

- **cluster\_id**: The CCE cluster ID to which the node belongs, assigned by referencing the ID of the CCE cluster resource (huaweicloud\_cce\_cluster.test)
- **name**: The name of the node, assigned by referencing the input variable `node_name`
- **flavor\_id**: The flavor ID of the node, if node flavor ID is specified, use that value, otherwise assign based on the return result of the compute flavor list query data source
- **availability\_zone**: The availability zone where the node is located, if availability zone is specified, use that value, otherwise use the first availability zone from the availability zone list query data source
- **key\_pair**: The key pair name used by the node, assigned by referencing the name of the key pair resource (huaweicloud\_kps\_keypair.test)
- **root\_volume**: Root volume configuration block
  - **volumetype**: Root volume type, assigned by referencing the input variable `root_volume_type`, default is "SATA"
  - **size**: Root volume size (GB), assigned by referencing the input variable `root_volume_size`, default is 40GB
- **data\_volumes**: Data volume configuration block (dynamic block), dynamically created based on the input variable `data_volumes_configuration`
  - **volumetype**: Data volume type, assigned by referencing the data volume configuration in the input variable
  - **size**: Data volume size (GB), assigned by referencing the data volume configuration in the input variable

### 11. Create OBS Bucket Resource

Add the following script to the TF file to inform Terraform to create an OBS bucket resource:

```hcl
variable "bucket_name" {
  description = "The name of the OBS bucket"
  type        = string
}

variable "bucket_multi_az" {
  description = "Whether to enable multi-AZ for the OBS bucket"
  type        = bool
  default     = true
}

# Create OBS bucket resource in the specified region (when the region parameter is omitted, it defaults to the region specified in the current provider block), used as the backend for Kubernetes persistent storage
resource "huaweicloud_obs_bucket" "test" {
  bucket   = var.bucket_name
  multi_az = var.bucket_multi_az
}
```

**Parameter Description**:

- **bucket**: The name of the OBS bucket, assigned by referencing the input variable `bucket_name`
- **multi\_az**: Whether to enable multi-availability zone, assigned by referencing the input variable `bucket_multi_az`, default is true indicating multi-availability zone enabled

### 12. Create Kubernetes Secret Resource

Add the following script to the TF file to inform Terraform to create a Kubernetes Secret resource:

```hcl
variable "secret_name" {
  description = "The name of the Kubernetes secret"
  type        = string
}

variable "namespace_name" {
  description = "The name of the CCE namespace"
  type        = string
  default     = "default"
}

variable "secret_labels" {
  description = "The labels of the Kubernetes secret"
  type        = map(string)
  default     = {
    "secret.kubernetes.io/used-by" = "csi"
  }
}

variable "secret_data" {
  description = "The data of the Kubernetes secret"
  type        = map(string)
  sensitive   = true
}

variable "secret_type" {
  description = "The type of the Kubernetes secret"
  type        = string
  default     = "cfe/secure-opaque"
}

# Create Kubernetes Secret resource for storing OBS access credentials
resource "kubernetes_secret" "test" {
  metadata {
    name      = var.secret_name
    namespace = var.namespace_name
    labels    = var.secret_labels
  }

  data = var.secret_data
  type = var.secret_type

  # For `data` parameters, input value is not consistent with the state value, so we need to ignore the changes
  lifecycle {
    ignore_changes = [data]
  }
}
```

**Parameter Description**:

- **metadata**: Metadata configuration block
  - **name**: The name of the Secret, assigned by referencing the input variable `secret_name`
  - **namespace**: The namespace where the Secret is located, assigned by referencing the input variable `namespace_name`, default is "default"
  - **labels**: The labels of the Secret, assigned by referencing the input variable `secret_labels`, default includes "secret.kubernetes.io/used-by" label
- **data**: The data of the Secret, assigned by referencing the input variable `secret_data`, containing OBS access key and secret key
- **type**: The type of the Secret, assigned by referencing the input variable `secret_type`, default is "cfe/secure-opaque"
- **lifecycle**: Lifecycle configuration block, used to ignore changes to the `data` parameter, because Secret data may be modified externally

### 13. Create Kubernetes Persistent Volume Resource

Add the following script to the TF file to inform Terraform to create a Kubernetes Persistent Volume resource:

```hcl
variable "pv_name" {
  description = "The name of the persistent volume"
  type        = string
}

variable "pv_csi_provisioner_identity" {
  description = "The identity of the CSI provisioner"
  type        = string
  default     = "everest-csi-provisioner"
}

variable "pv_access_modes" {
  description = "The access modes of the persistent volume"
  type        = list(string)
  default     = ["ReadWriteMany"]
}

variable "pv_storage" {
  description = "The storage of the persistent volume"
  type        = string
  default     = "1Gi"
}

variable "pv_driver" {
  description = "The driver of the persistent volume"
  type        = string
  default     = "obs.csi.everest.io"
}

variable "pv_fstype" {
  description = "The instance type of the persistent volume"
  type        = string
  default     = "s3fs"
}

variable "pv_obs_volume_type" {
  description = "The type of the OBS volume of the persistent volume"
  type        = string
  default     = "standard"
}

variable "pv_reclaim_policy" {
  description = "The reclaim policy of the persistent volume"
  type        = string
  default     = "Retain"
}

variable "pv_storage_class_name" {
  description = "The name of the storage class of the persistent volume"
  type        = string
  default     = "csi-obs"
}

variable "region_name" {
  description = "The region where the resources are located"
  type        = string
}

variable "enterprise_project_id" {
  description = "The enterprise project ID"
  type        = string
  default     = "0"
}

# Create Kubernetes Persistent Volume resource for defining OBS storage volume
resource "kubernetes_persistent_volume" "test" {
  metadata {
    name = var.pv_name

    annotations = {
      "pv.kubernetes.io/provisioned-by" = var.pv_csi_provisioner_identity
    }
  }

  spec {
    access_modes = var.pv_access_modes

    capacity = {
      storage = var.pv_storage
    }

    persistent_volume_source {
      csi {
        driver        = var.pv_driver
        fs_type       = var.pv_fstype
        volume_handle = huaweicloud_obs_bucket.test.bucket

        volume_attributes = {
          "storage.kubernetes.io/csiProvisionerIdentity" = var.pv_csi_provisioner_identity
          "everest.io/obs-volume-type"                   = var.pv_obs_volume_type
          "everest.io/region"                            = var.region_name
          "everest.io/enterprise-project-id"             = var.enterprise_project_id
        }

        node_publish_secret_ref {
          name      = kubernetes_secret.test.metadata[0].name
          namespace = var.namespace_name
        }
      }
    }

    persistent_volume_reclaim_policy = var.pv_reclaim_policy
    storage_class_name               = var.pv_storage_class_name
  }
}
```

**Parameter Description**:

- **metadata**: Metadata configuration block
  - **name**: The name of the Persistent Volume, assigned by referencing the input variable `pv_name`
  - **annotations**: Annotations, containing CSI provisioner identity
- **spec**: Specification configuration block
  - **access\_modes**: Access mode list, assigned by referencing the input variable `pv_access_modes`, default is \["ReadWriteMany"] indicating multi-node read-write
  - **capacity**: Capacity configuration block
    - **storage**: Storage size, assigned by referencing the input variable `pv_storage`, default is "1Gi"
  - **persistent\_volume\_source**: Persistent volume source configuration block
    - **csi**: CSI configuration block
      - **driver**: CSI driver, assigned by referencing the input variable `pv_driver`, default is "obs.csi.everest.io"
      - **fs\_type**: File system type, assigned by referencing the input variable `pv_fstype`, default is "s3fs"
      - **volume\_handle**: Volume handle, assigned by referencing the bucket name of the OBS bucket resource (huaweicloud\_obs\_bucket.test)
      - **volume\_attributes**: Volume attributes, containing CSI provisioner identity, OBS volume type, region, and enterprise project ID
      - **node\_publish\_secret\_ref**: Node publish secret reference configuration block, referencing the name and namespace of the Kubernetes Secret resource (kubernetes\_secret.test)
  - **persistent\_volume\_reclaim\_policy**: Reclaim policy, assigned by referencing the input variable `pv_reclaim_policy`, default is "Retain" indicating retain
  - **storage\_class\_name**: Storage class name, assigned by referencing the input variable `pv_storage_class_name`, default is "csi-obs"

### 14. Create Kubernetes Persistent Volume Claim Resource

Add the following script to the TF file to inform Terraform to create a Kubernetes Persistent Volume Claim resource:

```hcl
variable "pvc_name" {
  description = "The name of the persistent volume claim"
  type        = string
}

# Create Kubernetes Persistent Volume Claim resource for requesting Persistent Volume
resource "kubernetes_persistent_volume_claim" "test" {
  metadata {
    name      = var.pvc_name
    namespace = var.namespace_name

    annotations = {
      "volume.beta.kubernetes.io/storage-provisioner"    = var.pv_csi_provisioner_identity
      "everest.io/obs-volume-type"                       = var.pv_obs_volume_type
      "csi.storage.k8s.io/fstype"                        = var.pv_fstype
      "csi.storage.k8s.io/node-publish-secret-name"      = kubernetes_secret.test.metadata[0].name
      "csi.storage.k8s.io/node-publish-secret-namespace" = var.namespace_name
      "everest.io/enterprise-project-id"                 = var.enterprise_project_id
    }
  }

  spec {
    access_modes = var.pv_access_modes

    resources {
      requests = {
        storage = var.pv_storage
      }
    }

    storage_class_name = var.pv_storage_class_name
    volume_name        = kubernetes_persistent_volume.test.metadata.0.name
  }
}
```

**Parameter Description**:

- **metadata**: Metadata configuration block
  - **name**: The name of the Persistent Volume Claim, assigned by referencing the input variable `pvc_name`
  - **namespace**: The namespace where the Persistent Volume Claim is located, assigned by referencing the input variable `namespace_name`
  - **annotations**: Annotations, containing storage provisioner, OBS volume type, file system type, Secret reference, and enterprise project ID
- **spec**: Specification configuration block
  - **access\_modes**: Access mode list, assigned by referencing the input variable `pv_access_modes`
  - **resources**: Resource request configuration block
    - **requests**: Resource requests, containing storage size request
      - **storage**: Storage size, assigned by referencing the input variable `pv_storage`
  - **storage\_class\_name**: Storage class name, assigned by referencing the input variable `pv_storage_class_name`
  - **volume\_name**: Volume name, assigned by referencing the name of the Kubernetes Persistent Volume resource (kubernetes\_persistent\_volume.test)

### 15. Create Kubernetes Deployment Resource

Add the following script to the TF file to inform Terraform to create a Kubernetes Deployment resource:

```hcl
variable "deployment_name" {
  description = "The name of the deployment"
  type        = string
}

variable "deployment_replicas" {
  description = "The number of pods for the deployment"
  type        = number
  default     = 2
}

variable "deployment_containers" {
  description = "The container list for the deployment"
  type = list(object({
    name          = string
    image         = string
    volume_mounts = list(object({
      mount_path = string
    }))
  }))
  nullable = false
}

variable "deployment_volume_name" {
  description = "The name of the volume of the deployment"
  type        = string
  default     = "pvc-obs-volume"
}

variable "deployment_image_pull_secrets" {
  description = "The image pull secrets of the deployment"
  type = list(object({
    name = string
  }))

  default = [
    {
      name = "default-secret"
    }
  ]
  nullable = false
}

# Create Kubernetes Deployment resource for deploying applications using PVC
resource "kubernetes_deployment" "test" {
  metadata {
    name      = var.deployment_name
    namespace = var.namespace_name
  }

  spec {
    replicas = var.deployment_replicas

    selector {
      match_labels = {
        app = var.deployment_name
      }
    }

    template {
      metadata {
        labels = {
          app = var.deployment_name
        }
      }

      spec {
        dynamic "container" {
          for_each = var.deployment_containers

          content {
            name  = container.value.name
            image = container.value.image

            dynamic "volume_mount" {
              for_each = container.value.volume_mounts

              content {
                name       = var.deployment_volume_name
                mount_path = volume_mount.value.mount_path
              }
            }
          }
        }

        dynamic "image_pull_secrets" {
          for_each = var.deployment_image_pull_secrets

          content {
            name = image_pull_secrets.value.name
          }
        }

        volume {
          name = var.deployment_volume_name

          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.test.metadata[0].name
          }
        }
      }
    }
  }

  depends_on = [huaweicloud_cce_node.test]
}
```

**Parameter Description**:

- **metadata**: Metadata configuration block
  - **name**: The name of the Deployment, assigned by referencing the input variable `deployment_name`
  - **namespace**: The namespace where the Deployment is located, assigned by referencing the input variable `namespace_name`
- **spec**: Specification configuration block
  - **replicas**: Pod replica count, assigned by referencing the input variable `deployment_replicas`, default is 2
  - **selector**: Selector configuration block, used for selecting Pods
    - **match\_labels**: Match labels, containing application name label
  - **template**: Pod template configuration block
    - **metadata**: Pod metadata configuration block
      - **labels**: Pod labels, containing application name label
    - **spec**: Pod specification configuration block
      - **container**: Container configuration block (dynamic block), dynamically created based on the input variable `deployment_containers`
        - **name**: Container name, assigned by referencing the container configuration in the input variable
        - **image**: Container image, assigned by referencing the container configuration in the input variable
        - **volume\_mount**: Volume mount configuration block (dynamic block), dynamically created based on the container volume mount configuration in the input variable
          - **name**: Volume name, assigned by referencing the input variable `deployment_volume_name`, default is "pvc-obs-volume"
          - **mount\_path**: Mount path, assigned by referencing the volume mount configuration in the input variable
      - **image\_pull\_secrets**: Image pull secrets configuration block (dynamic block), dynamically created based on the input variable `deployment_image_pull_secrets`
        - **name**: Secret name, assigned by referencing the image pull secrets configuration in the input variable
      - **volume**: Volume configuration block
        - **name**: Volume name, assigned by referencing the input variable `deployment_volume_name`
        - **persistent\_volume\_claim**: Persistent volume claim configuration block
          - **claim\_name**: Claim name, assigned by referencing the name of the Kubernetes Persistent Volume Claim resource (kubernetes\_persistent\_volume\_claim.test)
- **depends\_on**: Explicit dependency, ensuring that the CCE node resource is created before creating the Deployment

### 16. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content, and these input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time it is executed.

Create a `terraform.tfvars` file in the working directory, with example content as follows:

```hcl
# Network resource configuration
vpc_name       = "tf_test_vpc"
subnet_name    = "tf_test_subnet"
bandwidth_name = "tf_test_bandwidth"
bandwidth_size = 5

# CCE cluster configuration
cluster_name          = "tf-test-cluster"
node_performance_type  = "computingv3"
keypair_name          = "tf_test_keypair"
node_name             = "tf-test-node"
root_volume_size      = 40
root_volume_type      = "SSD"
data_volumes_configuration = [
  {
    volumetype = "SSD"
    size       = 100
  }
]

# OBS and Kubernetes resource configuration
secret_name = "tf-test-secret"
secret_data = {
  "access.key" = "your_access_key"
  "secret.key" = "your_secret_key"
}

bucket_name           = "tf-test-bucket"
pv_name               = "tf-test-pv-obs"
pvc_name              = "tf-test-pvc-obs"
deployment_name       = "tf-test-deployment"
deployment_containers = [
  {
    name          = "container-1"
    image         = "nginx:latest"
    volume_mounts = [
      {
        mount_path = "/data"
      }
    ]
  }
]
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content in this `tfvars` file when executing terraform commands, other names need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="subnet_name=my-subnet"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 17. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the complete solution for managing PVC with OBS
4. Run `terraform show` to view the created complete solution for managing PVC with OBS

## Reference Information

- [Huawei Cloud CCE Product Documentation](https://support.huaweicloud.com/cce/index.html)
- [Huawei Cloud OBS Product Documentation](https://support.huaweicloud.com/obs/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Kubernetes Provider Documentation](https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs)
- [Best Practice Source Code Reference For CCE Kubernetes PVC using Existing OBS](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/cce/kubenetes/pvc-with-existing-obs-bucket)