# Deploy Shared Load Balancer with Backend Member

## Application Scenario

Elastic Load Balance (ELB) is a service that automatically distributes access traffic to multiple cloud servers, enabling expansion of application system's external service capabilities and improving application availability. Shared Load Balancer is a shared load balancing service provided by Huawei Cloud, supporting multiple protocols such as TCP, UDP, HTTP, HTTPS, suitable for cost-sensitive business scenarios with lower performance requirements.

By configuring backend server groups and backend servers for Shared Load Balancer, intelligent traffic distribution and load balancing can be achieved. Shared Load Balancer supports EIP binding, enabling the load balancer to provide services through the public network. This best practice will introduce how to use Terraform to automatically deploy a Shared Load Balancer with backend members, including VPC, subnet, load balancer, EIP binding, certificate management, listener, backend server group, health check, security group, security group rules, ECS instance, and backend member creation.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [ECS Flavors Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)
- [IMS Images Query Data Source (data.huaweicloud\_images\_images)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_images)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Shared Load Balancer Resource (huaweicloud\_lb\_loadbalancer)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lb_loadbalancer)
- [EIP Resource (huaweicloud\_vpc\_eip)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_eip)
- [EIP Association Resource (huaweicloud\_vpc\_eipv3\_associate)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_eipv3_associate)
- [Load Balancer Certificate Resource (huaweicloud\_lb\_certificate)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lb_certificate)
- [Listener Resource (huaweicloud\_lb\_listener)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lb_listener)
- [Backend Server Group Resource (huaweicloud\_lb\_pool)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lb_pool)
- [Health Check Resource (huaweicloud\_lb\_monitor)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lb_monitor)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [Security Group Rule Resource (huaweicloud\_networking\_secgroup\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup_rule)
- [ECS Instance Resource (huaweicloud\_compute\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_instance)
- [Backend Member Resource (huaweicloud\_lb\_member)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lb_member)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    ├── data.huaweicloud_compute_flavors
    │   └── data.huaweicloud_images_images
    │       └── huaweicloud_compute_instance
    └── huaweicloud_compute_instance

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        ├── huaweicloud_lb_loadbalancer
        ├── huaweicloud_compute_instance
        └── huaweicloud_lb_member

huaweicloud_lb_loadbalancer
    └── huaweicloud_lb_listener
        └── huaweicloud_lb_pool
            ├── huaweicloud_lb_member
            └── huaweicloud_lb_monitor

huaweicloud_vpc_eip
    └── huaweicloud_vpc_eipv3_associate
        └── huaweicloud_lb_loadbalancer

huaweicloud_lb_certificate
    └── huaweicloud_lb_listener

huaweicloud_networking_secgroup
    ├── huaweicloud_networking_secgroup_rule
    └── huaweicloud_compute_instance
        └── huaweicloud_lb_member

huaweicloud_networking_secgroup_rule
    └── huaweicloud_lb_monitor
```

## Implementation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration introduction, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://hcbp.gitbook.io/huaweicloud-provider/product-introduction/prepare_before_deploy).

### 2. Query Availability Zones Required for ECS Instance Resource Creation Through Data Source

Add the following script to the TF file (such as main.tf) to instruct Terraform to perform a data source query, the query results are used to create ECS instances:

```hcl
variable "availability_zone" {
  description = "The availability zone to which the ECS instance belongs"
  type        = string
  default     = ""
  nullable    = false
}

# Query all availability zone information in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted) for creating ECS instances
data "huaweicloud_availability_zones" "test" {
  count = var.availability_zone == "" ? 1 : 0
}
```

**Parameter Description**:

- **count**: The number of data source queries, used to control whether to query the availability zone list, only when `var.availability_zone` is empty, query the availability zone list

### 3. Query Instance Flavors Required for ECS Instance Resource Creation Through Data Source

Add the following script to the TF file to instruct Terraform to query ECS flavors that meet the conditions:

```hcl
variable "instance_flavor_id" {
  description = "The flavor ID of the ECS instance"
  type        = string
  default     = ""
  nullable    = false
}

variable "instance_flavor_performance_type" {
  description = "The performance type of the ECS instance flavor"
  type        = string
  default     = "normal"
}

variable "instance_flavor_cpu_core_count" {
  description = "The CPU core count of the ECS instance flavor"
  type        = number
  default     = 2
}

variable "instance_flavor_memory_size" {
  description = "The memory size of the ECS instance flavor"
  type        = number
  default     = 4
}

# Query all ECS flavor information that meets specific conditions in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted) for creating ECS instances
data "huaweicloud_compute_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  availability_zone = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test[0].names[0], null)
  performance_type  = var.instance_flavor_performance_type
  cpu_core_count    = var.instance_flavor_cpu_core_count
  memory_size       = var.instance_flavor_memory_size
}
```

**Parameter Description**:

- **count**: The number of data source queries, used to control whether to query instance flavor information, only when `var.instance_flavor_id` is empty, query instance flavor information
- **availability\_zone**: The availability zone where the flavor is located, if availability zone is specified, use that value, otherwise use the first availability zone from the availability zone list query data source
- **performance\_type**: The performance type of the flavor, assigned by referencing the input variable `instance_flavor_performance_type`, default is "normal" indicating standard type
- **cpu\_core\_count**: CPU core count, assigned by referencing the input variable `instance_flavor_cpu_core_count`, default is 2 cores
- **memory\_size**: Memory size (GB), assigned by referencing the input variable `instance_flavor_memory_size`, default is 4GB

### 4. Query Images Required for ECS Instance Resource Creation Through Data Source

Add the following script to the TF file to instruct Terraform to query images that meet the conditions:

```hcl
variable "instance_image_id" {
  description = "The image ID of the ECS instance"
  type        = string
  default     = ""
  nullable    = false
}

variable "instance_image_visibility" {
  description = "The visibility of the ECS instance image"
  type        = string
  default     = "public"
}

variable "instance_image_os" {
  description = "The operating system of the ECS instance image"
  type        = string
  default     = "Ubuntu"
}

# Query all IMS image information that meets specific conditions in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted) for creating ECS instances
data "huaweicloud_images_images" "test" {
  count = var.instance_image_id == "" ? 1 : 0

  flavor_id  = var.instance_flavor_id != "" ? var.instance_flavor_id : try(data.huaweicloud_compute_flavors.test[0].ids[0], null)
  visibility = var.instance_image_visibility
  os         = var.instance_image_os
}
```

**Parameter Description**:

- **count**: The number of data source queries, used to control whether to query image information, only when `var.instance_image_id` is empty, query image information
- **flavor\_id**: The flavor ID supported by the image, if instance flavor ID is specified, use that value, otherwise assign based on the return result of the compute flavor list query data source
- **visibility**: The visibility of the image, assigned by referencing the input variable `instance_image_visibility`, default is "public" indicating public image
- **os**: The operating system type of the image, assigned by referencing the input variable `instance_image_os`, default is "Ubuntu" operating system

### 5. Create VPC Resource

Add the following script to the TF file to instruct Terraform to create a VPC resource:

```hcl
variable "vpc_name" {
  description = "The name of the VPC"
  type        = string
}

variable "vpc_cidr" {
  description = "The CIDR block of the VPC"
  type        = string
  default     = "172.16.0.0/16"
}

# Create a VPC resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted) for deploying load balancer
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: The name of the VPC, assigned by referencing the input variable `vpc_name`
- **cidr**: The CIDR block of the VPC, assigned by referencing the input variable `vpc_cidr`, default is "172.16.0.0/16" block

### 6. Create VPC Subnet Resource

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
}

variable "subnet_gateway_ip" {
  description = "The gateway IP of the subnet"
  type        = string
  default     = ""
}

variable "subnet_dns_list" {
  description = "The DNS list of the subnet"
  type        = list(string)
  default     = null
}

# Create a VPC subnet resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted) for deploying load balancer
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr != "" ? var.subnet_cidr : cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0)
  gateway_ip = var.subnet_gateway_ip != "" ? var.subnet_gateway_ip : cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1)
  dns_list   = var.subnet_dns_list
}
```

**Parameter Description**:

- **vpc\_id**: The ID of the VPC to which the subnet belongs, referencing the ID of the VPC resource created earlier
- **name**: The name of the subnet, assigned by referencing the input variable `subnet_name`
- **cidr**: The CIDR block of the subnet, if subnet CIDR is specified, use that value, otherwise use the cidrsubnet function to divide a subnet segment from the VPC's CIDR block
- **gateway\_ip**: The gateway IP of the subnet, if gateway IP is specified, use that value, otherwise use the cidrhost function to get the first IP address from the subnet segment as the gateway IP
- **dns\_list**: The DNS server list of the subnet, assigned by referencing the input variable `subnet_dns_list`

### 7. Create Shared Load Balancer Resource

Add the following script to the TF file to instruct Terraform to create a Shared Load Balancer resource:

```hcl
variable "loadbalancer_name" {
  description = "The name of the load balancer"
  type        = string
}

# Create a Shared Load Balancer resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_lb_loadbalancer" "test" {
  name          = var.loadbalancer_name
  vip_subnet_id = huaweicloud_vpc_subnet.test.ipv4_subnet_id
}
```

**Parameter Description**:

- **name**: The name of the load balancer, assigned by referencing the input variable `loadbalancer_name`
- **vip\_subnet\_id**: The virtual IP subnet ID of the load balancer, referencing the IPv4 subnet ID of the subnet resource

### 8. Create EIP Resource (Optional)

Add the following script to the TF file to instruct Terraform to create an EIP resource (if EIP binding is required for the load balancer):

```hcl
variable "is_associate_eip" {
  description = "Whether to associate an EIP with the load balancer"
  type        = bool
  default     = false
}

variable "eip_address" {
  description = "The address of the EIP"
  type        = string
  default     = ""
  nullable    = false
}

variable "bandwidth_name" {
  description = "The name of the EIP bandwidth"
  type        = string
  default     = ""
  nullable    = false

  validation {
    condition     = !var.is_associate_eip || (var.eip_address != "" || var.bandwidth_name != "")
    error_message = "The bandwidth name must be provided if the EIP address is not provided."
  }
}

variable "bandwidth_size" {
  description = "The bandwidth size of the EIP in Mbps"
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

# Create an EIP resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_vpc_eip" "test" {
  count = var.is_associate_eip && var.eip_address == "" ? 1 : 0

  publicip {
    type = "5_bgp"
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

- **count**: The number of resource creations, used to control whether to create an EIP resource, only when EIP binding is required and EIP address is not provided, create an EIP resource
- **publicip**: Public IP configuration block
  - **type**: EIP type, set to "5\_bgp" indicating full dynamic BGP
- **bandwidth**: Bandwidth configuration block
  - **name**: The name of the bandwidth, assigned by referencing the input variable `bandwidth_name`
  - **size**: The size of the bandwidth (Mbps), assigned by referencing the input variable `bandwidth_size`, default is 5Mbps
  - **share\_type**: The share type of the bandwidth, assigned by referencing the input variable `bandwidth_share_type`, default is "PER" indicating dedicated
  - **charge\_mode**: The charge mode of the bandwidth, assigned by referencing the input variable `bandwidth_charge_mode`, default is "traffic" indicating pay-per-traffic

### 9. Associate EIP with Load Balancer (Optional)

Add the following script to the TF file to instruct Terraform to associate an EIP with the load balancer:

```hcl
# Create an EIP association resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_vpc_eipv3_associate" "test" {
  count = var.is_associate_eip ? 1 : 0

  publicip_id             = var.eip_address != "" ? var.eip_address : huaweicloud_vpc_eip.test[0].id
  associate_instance_type = "ELB"
  associate_instance_id   = huaweicloud_lb_loadbalancer.test.id
}
```

**Parameter Description**:

- **count**: The number of resource creations, used to control whether to create an EIP association resource, only when EIP binding is required, create the resource
- **publicip\_id**: The EIP ID, if EIP address is specified, use that value, otherwise use the ID of the created EIP resource
- **associate\_instance\_type**: The type of the associated instance, set to "ELB" indicating Elastic Load Balancer
- **associate\_instance\_id**: The ID of the associated instance, referencing the ID of the load balancer resource created earlier

### 10. Create Load Balancer Certificate Resource (Optional)

Add the following script to the TF file to instruct Terraform to create a load balancer certificate resource (when the listener protocol is TERMINATED\_HTTPS and certificate ID is not provided):

```hcl
variable "listener_protocol" {
  description = "The protocol of the listener"
  type        = string
  default     = "UDP"
}

variable "listener_default_tls_container_ref" {
  description = "The ID of the server certificate"
  type        = string
  default     = ""
}

variable "listener_server_certificate_name" {
  description = "The name of the server certificate"
  type        = string
  default     = ""

  validation {
    condition     = var.listener_protocol != "TERMINATED_HTTPS" || var.listener_default_tls_container_ref != "" || var.listener_server_certificate_name != ""
    error_message = "listener_server_certificate_name must be provided if listener_protocol is TERMINATED_HTTPS and listener_default_tls_container_ref is not provided"
  }
}

variable "listener_server_certificate_private_key" {
  description = "The private key of the server certificate"
  type        = string
  sensitive   = true
  default     = ""

  validation {
    condition     = var.listener_server_certificate_name == "" || var.listener_server_certificate_private_key != ""
    error_message = "listener_server_certificate_private_key must be provided if listener_server_certificate_name is provided"
  }
}

variable "listener_server_certificate_certificate" {
  description = "The content of the server certificate"
  type        = string
  sensitive   = true
  default     = ""

  validation {
    condition     = var.listener_server_certificate_name == "" || var.listener_server_certificate_certificate != ""
    error_message = "listener_server_certificate_certificate must be provided if listener_server_certificate_name is provided"
  }
}

# Create a load balancer certificate resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_lb_certificate" "test" {
  count = var.listener_protocol == "TERMINATED_HTTPS" && var.listener_default_tls_container_ref == "" ? 1 : 0

  name        = var.listener_server_certificate_name
  private_key = var.listener_server_certificate_private_key
  certificate = var.listener_server_certificate_certificate
}
```

**Parameter Description**:

- **count**: The number of resource creations, used to control whether to create a certificate resource, only when the listener protocol is TERMINATED\_HTTPS and certificate ID is not provided, create the certificate resource
- **name**: The name of the certificate, assigned by referencing the input variable `listener_server_certificate_name`
- **private\_key**: The private key of the certificate, assigned by referencing the input variable `listener_server_certificate_private_key`
- **certificate**: The content of the certificate, assigned by referencing the input variable `listener_server_certificate_certificate`

### 11. Create Listener Resource

Add the following script to the TF file to instruct Terraform to create a listener resource:

```hcl
variable "listener_name" {
  description = "The name of the listener"
  type        = string
}

variable "listener_port" {
  description = "The port of the listener"
  type        = number
  default     = 80
}

variable "listener_description" {
  description = "The description of the listener"
  type        = string
  default     = ""
}

variable "listener_tags" {
  description = "The tags of the listener"
  type        = map(string)
  default     = {}
}

variable "listener_http2_enable" {
  description = "The HTTP/2 enable of the listener, only valid when listener_protocol is TERMINATED_HTTPS"
  type        = bool
  default     = false
}

variable "listener_client_ca_tls_container_ref" {
  description = "The ID of the CA certificate of the listener, only valid when listener_protocol is TERMINATED_HTTPS"
  type        = string
  default     = null
}

variable "listener_sni_container_refs" {
  description = "The ID list of the SNI certificates of the listener, only valid when listener_protocol is TERMINATED_HTTPS"
  type        = list(string)
  default     = null
}

variable "listener_tls_ciphers_policy" {
  description = "The TLS ciphers policy of the listener, only valid when listener_protocol is TERMINATED_HTTPS"
  type        = string
  default     = null
}

variable "listener_insert_headers" {
  description = "The insert headers of the listener, only valid when listener_protocol is TERMINATED_HTTPS"
  type = object({
    x_forwarded_elb_ip = optional(string, null)
    x_forwarded_host   = optional(string, null)
  })
  default  = {}
  nullable = false
}

# Create a listener resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_lb_listener" "test" {
  loadbalancer_id             = huaweicloud_lb_loadbalancer.test.id
  name                        = var.listener_name
  protocol                    = var.listener_protocol
  protocol_port               = var.listener_port
  description                 = var.listener_description
  tags                        = var.listener_tags
  http2_enable                = var.listener_http2_enable
  default_tls_container_ref   = var.listener_default_tls_container_ref != "" ? var.listener_default_tls_container_ref : try(huaweicloud_lb_certificate.test[0].id, null)
  client_ca_tls_container_ref = var.listener_client_ca_tls_container_ref
  sni_container_refs          = var.listener_sni_container_refs
  tls_ciphers_policy          = var.listener_tls_ciphers_policy

  dynamic "insert_headers" {
    for_each = length(var.listener_insert_headers) > 0 ? [var.listener_insert_headers] : []

    content {
      x_forwarded_elb_ip = insert_headers.value["x_forwarded_elb_ip"]
      x_forwarded_host   = insert_headers.value["x_forwarded_host"]
    }
  }
}
```

**Parameter Description**:

- **loadbalancer\_id**: The load balancer ID to which the listener belongs, referencing the ID of the load balancer resource created earlier
- **name**: The name of the listener, assigned by referencing the input variable `listener_name`
- **protocol**: The protocol of the listener, assigned by referencing the input variable `listener_protocol`, default is "UDP"
- **protocol\_port**: The port of the listener, assigned by referencing the input variable `listener_port`, default is 80
- **description**: The description of the listener, assigned by referencing the input variable `listener_description`
- **tags**: The tags of the listener, assigned by referencing the input variable `listener_tags`
- **http2\_enable**: Whether to enable HTTP/2, only valid when protocol is TERMINATED\_HTTPS, assigned by referencing the input variable `listener_http2_enable`, default is false
- **default\_tls\_container\_ref**: The server certificate ID, if certificate ID is specified, use that value, otherwise use the ID of the created certificate resource
- **client\_ca\_tls\_container\_ref**: The CA certificate ID, only valid when protocol is TERMINATED\_HTTPS, assigned by referencing the input variable `listener_client_ca_tls_container_ref`
- **sni\_container\_refs**: The SNI certificate ID list, only valid when protocol is TERMINATED\_HTTPS, assigned by referencing the input variable `listener_sni_container_refs`
- **tls\_ciphers\_policy**: The TLS ciphers policy, only valid when protocol is TERMINATED\_HTTPS, assigned by referencing the input variable `listener_tls_ciphers_policy`
- **insert\_headers**: Insert headers configuration block (dynamic block), dynamically created based on the input variable `listener_insert_headers`
  - **x\_forwarded\_elb\_ip**: Whether to insert X-Forwarded-ELB-IP header, assigned by referencing the insert headers configuration in the input variable
  - **x\_forwarded\_host**: Whether to insert X-Forwarded-Host header, assigned by referencing the insert headers configuration in the input variable

### 12. Create Backend Server Group Resource

Add the following script to the TF file to instruct Terraform to create a backend server group resource:

```hcl
variable "pool_name" {
  description = "The name of the backend server group"
  type        = string
  default     = ""
}

variable "pool_protocol" {
  description = "The protocol of the backend server group"
  type        = string
  default     = "UDP"
}

variable "pool_method" {
  description = "The load balancing algorithm of the backend server group"
  type        = string
  default     = "ROUND_ROBIN"
}

variable "pool_description" {
  description = "The description of the backend server group"
  type        = string
  default     = ""
}

variable "pool_persistence" {
  description = "The persistence of the backend server group"
  type = object({
    type        = string
    cookie_name = optional(string, null)
    timeout     = optional(number, null)
  })
  default = null
}

# Create a backend server group resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_lb_pool" "test" {
  listener_id = huaweicloud_lb_listener.test.id
  name        = var.pool_name
  protocol    = var.pool_protocol
  lb_method   = var.pool_method
  description = var.pool_description

  dynamic "persistence" {
    for_each = var.pool_persistence != null ? [var.pool_persistence] : []

    content {
      type        = persistence.value["type"]
      cookie_name = persistence.value["cookie_name"]
      timeout     = persistence.value["timeout"]
    }
  }
}
```

**Parameter Description**:

- **listener\_id**: The listener ID to which the backend server group belongs, referencing the ID of the listener resource created earlier
- **name**: The name of the backend server group, assigned by referencing the input variable `pool_name`
- **protocol**: The protocol of the backend server group, assigned by referencing the input variable `pool_protocol`, default is "UDP"
- **lb\_method**: The load balancing algorithm of the backend server group, assigned by referencing the input variable `pool_method`, default is "ROUND\_ROBIN" indicating round-robin algorithm
- **description**: The description of the backend server group, assigned by referencing the input variable `pool_description`
- **persistence**: Session persistence configuration block (dynamic block), dynamically created based on the input variable `pool_persistence`
  - **type**: Session persistence type, assigned by referencing the session persistence configuration in the input variable
  - **cookie\_name**: Cookie name, assigned by referencing the session persistence configuration in the input variable
  - **timeout**: Session persistence timeout, assigned by referencing the session persistence configuration in the input variable

### 13. Create Security Group Resource

Add the following script to the TF file to instruct Terraform to create a security group resource:

```hcl
variable "security_group_name" {
  description = "The name of the security group"
  type        = string
}

# Create a security group resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted) for deploying ECS instances
resource "huaweicloud_networking_secgroup" "test" {
  name = var.security_group_name
}
```

**Parameter Description**:

- **name**: The name of the security group, assigned by referencing the input variable `security_group_name`

### 14. Create ECS Instance Resource

Add the following script to the TF file to instruct Terraform to create an ECS instance resource:

```hcl
variable "instance_name" {
  description = "The name of the ECS instance"
  type        = string
}

# Create an ECS instance resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_compute_instance" "test" {
  name              = var.instance_name
  image_id          = var.instance_image_id != "" ? var.instance_image_id : try(data.huaweicloud_images_images.test[0].images[0].id, null)
  flavor_id         = var.instance_flavor_id != "" ? var.instance_flavor_id : try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, null)
  availability_zone = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test[0].names[0], null)
  security_groups   = [huaweicloud_networking_secgroup.test.name]

  network {
    uuid = huaweicloud_vpc_subnet.test.id
  }

  # Prevents resource changes when data source query results change.
  lifecycle {
    ignore_changes = [
      flavor_id,
      image_id,
      availability_zone,
    ]
  }
}
```

**Parameter Description**:

- **name**: The name of the ECS instance, assigned by referencing the input variable `instance_name`
- **image\_id**: The image ID used by the ECS instance, if image ID is specified, use that value, otherwise assign based on the return result of the image list query data source
- **flavor\_id**: The flavor ID used by the ECS instance, if instance flavor ID is specified, use that value, otherwise assign based on the return result of the compute flavor list query data source
- **availability\_zone**: The availability zone where the ECS instance is located, if availability zone is specified, use that value, otherwise use the first availability zone from the availability zone list query data source
- **security\_groups**: The list of security group names associated with the ECS instance, using the name of the created security group resource
- **network**: Network configuration block, specifying the network to which the ECS instance connects
  - **uuid**: The unique identifier of the network, using the ID of the subnet resource created earlier
- **lifecycle**: Lifecycle configuration block, used to control the lifecycle behavior of resources
  - **ignore\_changes**: Specifies attribute changes to be ignored in subsequent applies, set to ignore changes to `flavor_id`, `image_id`, and `availability_zone`

> Note: The subnet ID must belong to the VPC of the load balancer.

### 15. Create Backend Member Resource

Add the following script to the TF file to instruct Terraform to create a backend member resource:

```hcl
variable "member_protocol_port" {
  description = "The protocol port of the backend server"
  type        = number
  default     = 80
}

variable "member_weight" {
  description = "The weight of the backend server"
  type        = number
  default     = 1
}

# Create a backend member resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_lb_member" "test" {
  pool_id       = huaweicloud_lb_pool.test.id
  address       = huaweicloud_compute_instance.test.access_ip_v4
  protocol_port = var.member_protocol_port
  weight        = var.member_weight
  subnet_id     = huaweicloud_vpc_subnet.test.ipv4_subnet_id
}
```

**Parameter Description**:

- **pool\_id**: The backend server group ID to which the backend member belongs, referencing the ID of the backend server group resource created earlier
- **address**: The IP address of the backend member, referencing the IPv4 access address of the ECS instance resource
- **protocol\_port**: The port of the backend member, assigned by referencing the input variable `member_protocol_port`, default is 80
- **weight**: The weight of the backend member, assigned by referencing the input variable `member_weight`, default is 1
- **subnet\_id**: The subnet ID where the backend member is located, referencing the IPv4 subnet ID of the subnet resource

### 16. Create Security Group Rule Resource

Add the following script to the TF file to instruct Terraform to create a security group rule resource:

```hcl
variable "health_check_port" {
  description = "The port for health checks"
  type        = number
  default     = null
}

variable "security_group_rule_remote_ip_prefix" {
  description = "The remote IP prefix of the security group rule"
  type        = string
  default     = "100.125.0.0/16"
}

# Create a security group rule resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_networking_secgroup_rule" "test" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  ports             = var.health_check_port != null ? join(",", distinct([var.health_check_port, var.member_protocol_port])) : var.member_protocol_port
  remote_ip_prefix  = var.security_group_rule_remote_ip_prefix
  security_group_id = huaweicloud_networking_secgroup.test.id
}
```

**Parameter Description**:

- **direction**: Direction, set to "ingress" indicating ingress rule
- **ethertype**: Ethernet type, set to "IPv4" indicating IPv4 protocol
- **protocol**: Protocol type, set to "tcp" indicating TCP protocol
- **ports**: Port range, if health check port is specified, include both health check port and backend server port, otherwise only include backend server port
- **remote\_ip\_prefix**: Remote IP prefix, assigned by referencing the input variable `security_group_rule_remote_ip_prefix`, default is "100.125.0.0/16" indicating traffic from ELB service network segment is allowed
- **security\_group\_id**: Security group ID, referencing the ID of the security group resource created earlier

### 17. Create Health Check Resource

Add the following script to the TF file to instruct Terraform to create a health check resource:

```hcl
variable "health_check_name" {
  description = "The name of the health check"
  type        = string
  default     = "health_check"
}

variable "health_check_type" {
  description = "The type of the health check"
  type        = string
  default     = "UDP_CONNECT"
}

variable "health_check_delay" {
  description = "The delay between health checks in seconds"
  type        = number
  default     = 10
}

variable "health_check_timeout" {
  description = "The timeout for health checks in seconds"
  type        = number
  default     = 5
}

variable "health_check_max_retries" {
  description = "The maximum number of retries for health checks"
  type        = number
  default     = 3
}

variable "health_check_url_path" {
  description = "The URL path for the health check"
  type        = string
  default     = null
}

variable "health_check_http_method" {
  description = "The HTTP method for the health check"
  type        = string
  default     = null
}

variable "health_check_expected_codes" {
  description = "The expected HTTP status codes for the health check"
  type        = string
  default     = null
}

variable "health_check_domain_name" {
  description = "The domain name for the health check"
  type        = string
  default     = null
}

# Create a health check resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_lb_monitor" "test" {
  pool_id        = huaweicloud_lb_pool.test.id
  name           = var.health_check_name
  type           = var.health_check_type
  delay          = var.health_check_delay
  timeout        = var.health_check_timeout
  max_retries    = var.health_check_max_retries
  port           = var.health_check_port
  url_path       = var.health_check_url_path
  http_method    = var.health_check_http_method
  expected_codes = var.health_check_expected_codes
  domain_name    = var.health_check_domain_name

  depends_on = [huaweicloud_networking_secgroup_rule.test]
}
```

**Parameter Description**:

- **pool\_id**: The backend server group ID to which the health check belongs, referencing the ID of the backend server group resource created earlier
- **name**: The name of the health check, assigned by referencing the input variable `health_check_name`, default is "health\_check"
- **type**: The type of the health check, assigned by referencing the input variable `health_check_type`, default is "UDP\_CONNECT"
- **delay**: The delay between health checks (seconds), assigned by referencing the input variable `health_check_delay`, default is 10 seconds
- **timeout**: The timeout for health checks (seconds), assigned by referencing the input variable `health_check_timeout`, default is 5 seconds
- **max\_retries**: The maximum number of retries for health checks, assigned by referencing the input variable `health_check_max_retries`, default is 3 times
- **port**: The port for health checks, assigned by referencing the input variable `health_check_port`
- **url\_path**: The URL path for health checks, assigned by referencing the input variable `health_check_url_path`
- **http\_method**: The HTTP method for health checks, assigned by referencing the input variable `health_check_http_method`
- **expected\_codes**: The expected HTTP status codes for health checks, assigned by referencing the input variable `health_check_expected_codes`
- **domain\_name**: The domain name for health checks, assigned by referencing the input variable `health_check_domain_name`
- **depends\_on**: Explicit dependency relationship, specifying that the health check resource depends on the security group rule resource, ensuring that security group rules are created before health checks

> Note: The health check resource needs to be created after the security group rule is created, so `depends_on` is used to explicitly declare the dependency relationship.

### 18. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content, and these input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time it is executed.

Create a `terraform.tfvars` file in the working directory, with example content as follows:

```hcl
# Network resource configuration
vpc_name                    = "tf_test_vpc"
subnet_name                 = "tf_test_subnet"
loadbalancer_name           = "tf_test_loadbalancer"
is_associate_eip            = true
bandwidth_name              = "tf_test_eip_bandwidth"

# Listener configuration
listener_name               = "tf_test_listener"
listener_protocol           = "HTTP"

# Backend server group configuration
pool_name                   = "tf_test_server_group"
pool_protocol               = "HTTP"

# Security group configuration
security_group_name         = "tf_test_security_group"

# ECS instance configuration
instance_name               = "tf_test_ecs_instance"

# Health check configuration
health_check_type           = "HTTP"
health_check_expected_codes = "200-202"
health_check_url_path       = "/"
health_check_http_method    = "GET"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content in this `tfvars` file when executing terraform commands, other names need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="loadbalancer_name=my-loadbalancer"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 19. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the Shared Load Balancer with backend members
4. Run `terraform show` to view the created Shared Load Balancer with backend members details

## Reference Information

- [Huawei Cloud Elastic Load Balance Product Documentation](https://support.huaweicloud.com/elb/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For ELB Shared Load Balancer with Backend Member](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/elb/shared-loadbalancer-with-full-configuration)
