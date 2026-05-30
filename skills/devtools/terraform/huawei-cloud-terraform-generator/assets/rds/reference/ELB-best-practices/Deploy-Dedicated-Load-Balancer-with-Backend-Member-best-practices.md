# Deploy Dedicated Load Balancer with Backend Member

## Application Scenario

Elastic Load Balance (ELB) is a service that automatically distributes access traffic to multiple cloud servers, enabling expansion of application system's external service capabilities and improving application availability. Dedicated Elastic Load Balancer is a high-performance and highly available load balancing service provided by Huawei Cloud, supporting multiple protocols such as TCP, UDP, HTTP, HTTPS, suitable for business scenarios that require high performance and high availability.

By configuring backend server groups and backend members for dedicated load balancers, you can achieve intelligent traffic distribution and load balancing. This best practice will introduce how to use Terraform to automatically deploy a dedicated load balancer with backend members, including VPC, subnet, load balancer, listener, backend server group, health check, security group, security group rules, ECS instance, and backend member creation.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [ECS Flavors Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)
- [IMS Images Query Data Source (data.huaweicloud\_images\_images)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_images)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Dedicated Load Balancer Resource (huaweicloud\_elb\_loadbalancer)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/elb_loadbalancer)
- [Listener Resource (huaweicloud\_elb\_listener)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/elb_listener)
- [Backend Server Group Resource (huaweicloud\_elb\_pool)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/elb_pool)
- [Health Check Resource (huaweicloud\_elb\_monitor)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/elb_monitor)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [Security Group Rule Resource (huaweicloud\_networking\_secgroup\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup_rule)
- [ECS Instance Resource (huaweicloud\_compute\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_instance)
- [Backend Member Resource (huaweicloud\_elb\_member)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/elb_member)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    ├── data.huaweicloud_compute_flavors
    │   └── data.huaweicloud_images_images
    │       └── huaweicloud_compute_instance
    ├── huaweicloud_elb_loadbalancer
    └── huaweicloud_compute_instance

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        ├── huaweicloud_elb_loadbalancer
        ├── huaweicloud_compute_instance
        └── huaweicloud_elb_member

huaweicloud_elb_loadbalancer
    └── huaweicloud_elb_listener
        └── huaweicloud_elb_pool
            ├── huaweicloud_elb_monitor
            └── huaweicloud_elb_member

huaweicloud_networking_secgroup
    ├── huaweicloud_networking_secgroup_rule
    └── huaweicloud_compute_instance
        └── huaweicloud_elb_member
```

## Implementation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration introduction, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://hcbp.gitbook.io/huaweicloud-provider/product-introduction/prepare_before_deploy).

### 2. Query Availability Zones Required for ECS Instance Resource Creation Through Data Source

Add the following script to the TF file (such as main.tf) to instruct Terraform to perform a data source query, the query results are used to create ECS instances:

```hcl
variable "availability_zone" {
  description = "The name of the availability zone to which the resources belong"
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
  description = "The flavor ID of the instance"
  type        = string
  default     = ""
}

variable "instance_flavor_performance_type" {
  description = "The performance type of the instance flavor"
  type        = string
  default     = "normal"
}

variable "instance_flavor_cpu_core_count" {
  description = "The CPU core count of the instance flavor"
  type        = number
  default     = 2
}

variable "instance_flavor_memory_size" {
  description = "The memory size of the instance flavor"
  type        = number
  default     = 4
}

# Query all ECS flavor information that meets specific conditions in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted) for creating ECS instances
data "huaweicloud_compute_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  performance_type  = var.instance_flavor_performance_type
  cpu_core_count    = var.instance_flavor_cpu_core_count
  memory_size       = var.instance_flavor_memory_size
  availability_zone = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test[0].names[0], null)
}
```

**Parameter Description**:

- **count**: The number of data source queries, used to control whether to query instance flavor information, only when `var.instance_flavor_id` is empty, query instance flavor information
- **performance\_type**: The performance type of the flavor, assigned by referencing the input variable `instance_flavor_performance_type`, default is "normal" indicating standard type
- **cpu\_core\_count**: CPU core count, assigned by referencing the input variable `instance_flavor_cpu_core_count`, default is 2 cores
- **memory\_size**: Memory size (GB), assigned by referencing the input variable `instance_flavor_memory_size`, default is 4GB
- **availability\_zone**: The availability zone where the flavor is located, if availability zone is specified, use that value, otherwise use the first availability zone from the availability zone list query data source

### 4. Query Images Required for ECS Instance Resource Creation Through Data Source

Add the following script to the TF file to instruct Terraform to query images that meet the conditions:

```hcl
variable "instance_image_id" {
  description = "The image ID of the instance"
  type        = string
  default     = ""
}

variable "instance_image_visibility" {
  description = "The visibility of the instance image"
  type        = string
  default     = "public"
}

variable "instance_image_os" {
  description = "The OS of the instance image"
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

# Create a VPC resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted) for deploying Elastic Load Balancer
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: The name of the VPC, assigned by referencing the input variable `vpc_name`
- **cidr**: The CIDR block of the VPC, assigned by referencing the input variable `vpc_cidr`, default is "172.16.0.0/16" block

### 6. Create VPC Subnet Resource

Add the following script to the TF file to instruct Terraform to create a VPC subnet resource (with IPv6 support):

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
  description = "The gateway IP address of the subnet"
  type        = string
  default     = ""
  nullable    = false
}

# Create a VPC subnet resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted) for deploying Elastic Load Balancer
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id      = huaweicloud_vpc.test.id
  name        = var.subnet_name
  cidr        = var.subnet_cidr != "" ? var.subnet_cidr : cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0)
  gateway_ip  = var.subnet_gateway_ip != "" ? var.subnet_gateway_ip : cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1)
  ipv6_enable = true
}
```

**Parameter Description**:

- **vpc\_id**: The ID of the VPC to which the subnet belongs, referencing the ID of the VPC resource created earlier
- **name**: The name of the subnet, assigned by referencing the input variable `subnet_name`
- **cidr**: The CIDR block of the subnet, if subnet CIDR is specified, use that value, otherwise use the cidrsubnet function to divide a subnet segment from the VPC's CIDR block
- **gateway\_ip**: The gateway IP of the subnet, if gateway IP is specified, use that value, otherwise use the cidrhost function to get the first IP address from the subnet segment as the gateway IP
- **ipv6\_enable**: Whether to enable IPv6, set to true to enable IPv6 functionality

### 7. Create Dedicated Load Balancer Resource

Add the following script to the TF file to instruct Terraform to create a dedicated load balancer resource:

```hcl
variable "loadbalancer_name" {
  description = "The name of the loadbalancer"
  type        = string
}

variable "loadbalancer_cross_vpc_backend" {
  description = "Whether to associate backend servers with the load balancer by using their IP addresses"
  type        = bool
  default     = false
}

variable "loadbalancer_description" {
  description = "The description of the loadbalancer"
  type        = string
  default     = null
}

variable "enterprise_project_id" {
  description = "The enterprise project ID"
  type        = string
  default     = null
}

variable "loadbalancer_tags" {
  description = "The tags of the loadbalancer"
  type        = map(string)
  default     = {}
}

# Create a dedicated load balancer resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_elb_loadbalancer" "test" {
  name                  = var.loadbalancer_name
  vpc_id                = huaweicloud_vpc.test.id
  ipv4_subnet_id        = huaweicloud_vpc_subnet.test.ipv4_subnet_id
  ipv6_network_id       = huaweicloud_vpc_subnet.test.id
  availability_zone     = var.availability_zone != "" ? [var.availability_zone] : try(slice(data.huaweicloud_availability_zones.test[0].names, 0, 1), null)
  cross_vpc_backend     = var.loadbalancer_cross_vpc_backend
  description           = var.loadbalancer_description
  enterprise_project_id = var.enterprise_project_id
  tags                  = var.loadbalancer_tags
}
```

**Parameter Description**:

- **name**: The name of the load balancer, assigned by referencing the input variable `loadbalancer_name`
- **vpc\_id**: The ID of the VPC to which the load balancer belongs, referencing the ID of the VPC resource created earlier
- **ipv4\_subnet\_id**: The IPv4 subnet ID of the load balancer, referencing the IPv4 subnet ID of the subnet resource
- **ipv6\_network\_id**: The IPv6 network ID of the load balancer, referencing the ID of the subnet resource (when IPv6 is enabled on the subnet)
- **availability\_zone**: The availability zone list where the load balancer is located, if availability zone is specified, use that value, otherwise use the first availability zone from the availability zone list query data source
- **cross\_vpc\_backend**: Whether to associate backend servers with the load balancer by using their IP addresses, assigned by referencing the input variable `loadbalancer_cross_vpc_backend`, default is false
- **description**: The description of the load balancer, assigned by referencing the input variable `loadbalancer_description`
- **enterprise\_project\_id**: The enterprise project ID to which the load balancer belongs, assigned by referencing the input variable `enterprise_project_id`
- **tags**: The tags of the load balancer, assigned by referencing the input variable `loadbalancer_tags`

### 8. Create Listener Resource

Add the following script to the TF file to instruct Terraform to create a listener resource:

```hcl
variable "listener_name" {
  description = "The name of the listener"
  type        = string
}

variable "listener_protocol" {
  description = "The protocol of the listener"
  type        = string
  default     = "TCP"
}

variable "listener_port" {
  description = "The port of the listener"
  type        = number
  default     = 8080
}

variable "listener_server_certificate" {
  description = "The server certificate ID of the listener, required when the listener_protocol is HTTPS, TLS or QUIC"
  type        = string
  default     = null
}

variable "listener_ca_certificate" {
  description = "The CA certificate ID of the listener, only available when the listener_protocol is HTTPS"
  type        = string
  default     = null
}

variable "listener_sni_certificates" {
  description = "The SNI certificates of the listener, only available when the listener_protocol is HTTPS or TLS"
  type        = list(string)
  default     = []
}

variable "listener_sni_match_algo" {
  description = "The SNI match algorithm of the listener"
  type        = string
  default     = null
}

variable "listener_security_policy_id" {
  description = "The security policy ID of the listener, only available when the listener_protocol is HTTPS"
  type        = string
  default     = null
}

variable "listener_http2_enable" {
  description = "Whether to enable HTTP/2, only available when the listener_protocol is HTTPS"
  type        = bool
  default     = null
}

variable "listener_port_ranges" {
  description = "The port ranges of the listener"
  type        = list(object({
    start_port = number
    end_port   = number
  }))
  default  = []
  nullable = false
}

variable "listener_idle_timeout" {
  description = "The idle timeout of the listener"
  type        = number
  default     = 60
}

variable "listener_request_timeout" {
  description = "The request timeout of the listener"
  type        = number
  default     = null
}

variable "listener_response_timeout" {
  description = "The response timeout of the listener"
  type        = number
  default     = null
}

variable "listener_description" {
  description = "The description of the listener"
  type        = string
  default     = null
}

variable "listener_tags" {
  description = "The tags of the listener"
  type        = map(string)
  default     = {}
}

variable "listener_advanced_forwarding_enabled" {
  description = "Whether to enable advanced forwarding"
  type        = bool
  default     = false
}

# Create a listener resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_elb_listener" "test" {
  loadbalancer_id    = huaweicloud_elb_loadbalancer.test.id
  name               = var.listener_name
  protocol           = var.listener_protocol
  protocol_port      = var.listener_port
  server_certificate = var.listener_server_certificate
  ca_certificate     = var.listener_ca_certificate
  sni_certificate    = var.listener_sni_certificates
  sni_match_algo     = var.listener_sni_match_algo
  security_policy_id = var.listener_security_policy_id
  http2_enable       = var.listener_http2_enable

  dynamic "port_ranges" {
    for_each = var.listener_port_ranges

    content {
      start_port = port_ranges.value["start_port"]
      end_port   = port_ranges.value["end_port"]
    }
  }

  idle_timeout                = var.listener_idle_timeout
  request_timeout             = var.listener_request_timeout
  response_timeout            = var.listener_response_timeout
  description                 = var.listener_description
  tags                        = var.listener_tags
  advanced_forwarding_enabled = var.listener_advanced_forwarding_enabled
}
```

**Parameter Description**:

- **loadbalancer\_id**: The load balancer ID to which the listener belongs, referencing the ID of the load balancer resource created earlier
- **name**: The name of the listener, assigned by referencing the input variable `listener_name`
- **protocol**: The protocol of the listener, assigned by referencing the input variable `listener_protocol`, default is "TCP"
- **protocol\_port**: The port of the listener, assigned by referencing the input variable `listener_port`, default is 8080
- **server\_certificate**: The server certificate ID of the listener, required when the protocol is HTTPS, TLS or QUIC, assigned by referencing the input variable `listener_server_certificate`
- **ca\_certificate**: The CA certificate ID of the listener, only available when the protocol is HTTPS, assigned by referencing the input variable `listener_ca_certificate`
- **sni\_certificate**: The SNI certificate list of the listener, only available when the protocol is HTTPS or TLS, assigned by referencing the input variable `listener_sni_certificates`
- **sni\_match\_algo**: The SNI match algorithm of the listener, assigned by referencing the input variable `listener_sni_match_algo`
- **security\_policy\_id**: The security policy ID of the listener, only available when the protocol is HTTPS, assigned by referencing the input variable `listener_security_policy_id`
- **http2\_enable**: Whether to enable HTTP/2, only available when the protocol is HTTPS, assigned by referencing the input variable `listener_http2_enable`
- **port\_ranges**: The port range list of the listener (dynamic block), dynamically created based on the input variable `listener_port_ranges`
  - **start\_port**: Start port, assigned by referencing the port range configuration in the input variable
  - **end\_port**: End port, assigned by referencing the port range configuration in the input variable
- **idle\_timeout**: The idle timeout of the listener (seconds), assigned by referencing the input variable `listener_idle_timeout`, default is 60 seconds
- **request\_timeout**: The request timeout of the listener (seconds), assigned by referencing the input variable `listener_request_timeout`
- **response\_timeout**: The response timeout of the listener (seconds), assigned by referencing the input variable `listener_response_timeout`
- **description**: The description of the listener, assigned by referencing the input variable `listener_description`
- **tags**: The tags of the listener, assigned by referencing the input variable `listener_tags`
- **advanced\_forwarding\_enabled**: Whether to enable advanced forwarding, assigned by referencing the input variable `listener_advanced_forwarding_enabled`, default is false

### 9. Create Backend Server Group Resource

Add the following script to the TF file to instruct Terraform to create a backend server group resource:

```hcl
variable "pool_name" {
  description = "The name of the pool"
  type        = string
  default     = null
}

variable "pool_protocol" {
  description = "The protocol of the pool"
  type        = string
  default     = "TCP"
}

variable "pool_method" {
  description = "The load balancing method of the pool"
  type        = string
  default     = "ROUND_ROBIN"
}

variable "pool_any_port_enable" {
  description = "Whether to enable any port for the pool"
  type        = bool
  default     = false
}

variable "pool_description" {
  description = "The description of the pool"
  type        = string
  default     = null
}

variable "pool_persistences" {
  description = "The persistence configurations for the pool"
  type        = list(object({
    type        = string
    cookie_name = optional(string, null)
    timeout     = optional(number, null)
  }))
  default  = []
  nullable = false
}

# Create a backend server group resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_elb_pool" "test" {
  listener_id     = huaweicloud_elb_listener.test.id
  name            = var.pool_name
  protocol        = var.pool_protocol
  lb_method       = var.pool_method
  any_port_enable = var.pool_any_port_enable
  description     = var.pool_description

  dynamic "persistence" {
    for_each = var.pool_persistences

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
- **protocol**: The protocol of the backend server group, assigned by referencing the input variable `pool_protocol`, default is "TCP"
- **lb\_method**: The load balancing algorithm of the backend server group, assigned by referencing the input variable `pool_method`, default is "ROUND\_ROBIN" indicating round-robin algorithm
- **any\_port\_enable**: Whether to enable any port, assigned by referencing the input variable `pool_any_port_enable`, default is false
- **description**: The description of the backend server group, assigned by referencing the input variable `pool_description`
- **persistence**: Session persistence configuration block (dynamic block), dynamically created based on the input variable `pool_persistences`
  - **type**: Session persistence type, assigned by referencing the session persistence configuration in the input variable
  - **cookie\_name**: Cookie name, assigned by referencing the session persistence configuration in the input variable
  - **timeout**: Session persistence timeout, assigned by referencing the session persistence configuration in the input variable

### 10. Create Health Check Resource

Add the following script to the TF file to instruct Terraform to create a health check resource:

```hcl
variable "health_check_protocol" {
  description = "The protocol of the health check"
  type        = string
  default     = "TCP"
}

variable "health_check_interval" {
  description = "The interval of the health check"
  type        = number
  default     = 20
}

variable "health_check_timeout" {
  description = "The timeout of the health check"
  type        = number
  default     = 15
}

variable "health_check_max_retries" {
  description = "The maximum retries of the health check"
  type        = number
  default     = 10
}

variable "health_check_port" {
  description = "The port of the health check"
  type        = number
  default     = null
}

variable "health_check_url_path" {
  description = "The URL path of the health check"
  type        = string
  default     = null
}

variable "health_check_status_code" {
  description = "The status code of the health check"
  type        = string
  default     = null
}

variable "health_check_http_method" {
  description = "The HTTP method of the health check"
  type        = string
  default     = null
}

variable "health_check_domain_name" {
  description = "The domain name of the health check"
  type        = string
  default     = null
}

# Create a health check resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_elb_monitor" "test" {
  pool_id     = huaweicloud_elb_pool.test.id
  protocol    = var.health_check_protocol
  interval    = var.health_check_interval
  timeout     = var.health_check_timeout
  max_retries = var.health_check_max_retries
  port        = var.health_check_port
  url_path    = var.health_check_url_path
  status_code = var.health_check_status_code
  http_method = var.health_check_http_method
  domain_name = var.health_check_domain_name
}
```

**Parameter Description**:

- **pool\_id**: The backend server group ID to which the health check belongs, referencing the ID of the backend server group resource created earlier
- **protocol**: The protocol of the health check, assigned by referencing the input variable `health_check_protocol`, default is "TCP"
- **interval**: The interval of the health check (seconds), assigned by referencing the input variable `health_check_interval`, default is 20 seconds
- **timeout**: The timeout of the health check (seconds), assigned by referencing the input variable `health_check_timeout`, default is 15 seconds
- **max\_retries**: The maximum retries of the health check, assigned by referencing the input variable `health_check_max_retries`, default is 10 times
- **port**: The port of the health check, assigned by referencing the input variable `health_check_port`
- **url\_path**: The URL path of the health check, assigned by referencing the input variable `health_check_url_path`
- **status\_code**: The status code of the health check, assigned by referencing the input variable `health_check_status_code`
- **http\_method**: The HTTP method of the health check, assigned by referencing the input variable `health_check_http_method`
- **domain\_name**: The domain name of the health check, assigned by referencing the input variable `health_check_domain_name`

### 11. Create Security Group Resource

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

### 12. Create Security Group Rule Resources

Add the following script to the TF file to instruct Terraform to create security group rule resources:

```hcl
variable "member_protocol_port" {
  description = "The port of the member"
  type        = number
  default     = 8080
}

# Create security group rule resources in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_networking_secgroup_rule" "test" {
  security_group_id = huaweicloud_networking_secgroup.test.id
  ethertype         = "IPv4"
  direction         = "ingress"
  protocol          = var.pool_protocol == "UDP" ? "udp" : "tcp"
  # The backend server port and check health port.
  ports             = var.health_check_port != null ? join(",", distinct([var.health_check_port, var.member_protocol_port])) : var.member_protocol_port
  # The CIDR to which the ELB backend subnet belongs.
  remote_ip_prefix  = huaweicloud_vpc_subnet.test.cidr
}

# When the protocol is UDP, IPv4 ICMP rules need to be created
resource "huaweicloud_networking_secgroup_rule" "in_v4_icmp" {
  count = var.pool_protocol == "UDP" ? 1 : 0

  security_group_id = huaweicloud_networking_secgroup.test.id
  ethertype         = "IPv4"
  direction         = "ingress"
  protocol          = "icmp"
  remote_ip_prefix  = huaweicloud_vpc_subnet.test.cidr
}

# When the protocol is UDP, IPv6 ICMP rules need to be created
resource "huaweicloud_networking_secgroup_rule" "in_v6_icmp" {
  count = var.pool_protocol == "UDP" ? 1 : 0

  security_group_id = huaweicloud_networking_secgroup.test.id
  ethertype         = "IPv6"
  direction         = "ingress"
  protocol          = "icmp"
  remote_ip_prefix  = huaweicloud_vpc_subnet.test.ipv6_cidr
}

# When the protocol is UDP, IPv6 UDP rules need to be created
resource "huaweicloud_networking_secgroup_rule" "in_v6" {
  count = var.pool_protocol == "UDP" ? 1 : 0

  security_group_id = huaweicloud_networking_secgroup.test.id
  ethertype         = "IPv6"
  direction         = "ingress"
  protocol          = "udp"
  # The backend server port and check health port.
  ports             = var.health_check_port != null ? join(",", distinct([var.health_check_port, var.member_protocol_port])) : var.member_protocol_port
  # The CIDR to which the ELB backend subnet belongs.
  remote_ip_prefix  = huaweicloud_vpc_subnet.test.ipv6_cidr
}
```

**Parameter Description**:

- **security\_group\_id**: The security group ID, referencing the ID of the security group resource created earlier
- **ethertype**: The ethernet type, set to "IPv4" or "IPv6"
- **direction**: The direction, set to "ingress" indicating inbound rules
- **protocol**: The protocol type, dynamically set based on the backend server group protocol, if the protocol is UDP, use "udp", otherwise use "tcp"
- **ports**: The port range, if the health check port is specified, includes both the health check port and the backend server port, otherwise only includes the backend server port
- **remote\_ip\_prefix**: The remote IP prefix, set to the CIDR block of the subnet, allowing traffic from the ELB backend subnet
- **count**: The number of resource creations, used to control whether to create IPv4 ICMP, IPv6 ICMP, and IPv6 UDP rules, only when the protocol is UDP, create these rules

> Note: When the backend server group protocol is UDP, IPv4 ICMP, IPv6 ICMP, and IPv6 UDP rules need to be created to support UDP protocol health checks and traffic forwarding.

### 13. Create ECS Instance Resource

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

  lifecycle {
    ignore_changes = [
      flavor_id,
      image_id,
      availability_zone
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

### 14. Create Backend Member Resource

Add the following script to the TF file to instruct Terraform to create a backend member resource:

```hcl
variable "member_weight" {
  description = "The weight of the member"
  type        = number
  default     = 1
}

# Create a backend member resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_elb_member" "test" {
  pool_id       = huaweicloud_elb_pool.test.id
  address       = huaweicloud_compute_instance.test.access_ip_v4
  protocol_port  = var.member_protocol_port
  weight        = var.member_weight
  subnet_id     = huaweicloud_vpc_subnet.test.ipv4_subnet_id
}
```

**Parameter Description**:

- **pool\_id**: The backend server group ID to which the backend member belongs, referencing the ID of the backend server group resource created earlier
- **address**: The IP address of the backend member, referencing the IPv4 access address of the ECS instance resource
- **protocol\_port**: The port of the backend member, assigned by referencing the input variable `member_protocol_port`, default is 8080
- **weight**: The weight of the backend member, assigned by referencing the input variable `member_weight`, default is 1
- **subnet\_id**: The subnet ID where the backend member is located, referencing the IPv4 subnet ID of the subnet resource

> Note: The IP address of the backend member must be in the same VPC as the load balancer, and the port of the backend member must match the port of the listener.

### 15. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content, and these input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time it is executed.

Create a `terraform.tfvars` file in the working directory, with example content as follows:

```hcl
# Network resource configuration
vpc_name                       = "tf_test_vpc"
subnet_name                    = "tf_test_subnet"
security_group_name            = "tf_test_security_group"

# ECS instance configuration
instance_name                  = "tf_test_instance"

# Load balancer configuration
loadbalancer_name              = "tf_test_dedicated_loadbalancer"
loadbalancer_cross_vpc_backend = true

# Listener configuration
listener_name                  = "tf_test_dedicated_listener"

# Backend server group configuration
pool_name                      = "tf_test_dedicated_pool"
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

### 16. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the dedicated load balancer with backend members
4. Run `terraform show` to view the created dedicated load balancer with backend members details

## Reference Information

- [Huawei Cloud Elastic Load Balance Product Documentation](https://support.huaweicloud.com/elb/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For ELB Dedicated Load Balancer with Backend Member](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/elb/dedicated-loadbalancer-with-full-configuration)