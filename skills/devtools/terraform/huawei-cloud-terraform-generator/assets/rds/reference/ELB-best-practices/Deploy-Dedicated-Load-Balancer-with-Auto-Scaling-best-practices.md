# Deploy Dedicated Load Balancer with Auto Scaling

## Application Scenario

Elastic Load Balance (ELB) is a service that automatically distributes access traffic to multiple cloud servers, enabling expansion of application system's external service capabilities and improving application availability. Auto Scaling (AS) is a service that automatically adjusts computing resources based on business needs and policies, automatically increasing or decreasing the number of cloud servers based on business load to achieve elastic scaling of resources.

By combining dedicated load balancers with Auto Scaling services, you can achieve automated traffic distribution and elastic resource scaling. When business load increases, the Auto Scaling service will automatically increase cloud server instances and automatically add new instances to the load balancer's backend server group. When business load decreases, the Auto Scaling service will automatically reduce cloud server instances, achieving automatic resource optimization and cost control. This best practice will introduce how to use Terraform to automatically deploy an integrated solution of dedicated load balancer and Auto Scaling, including VPC, subnet, dedicated load balancer, listener, backend server group, Auto Scaling configuration, Auto Scaling group, alarm rules, and scaling policies.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Data Source (huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [ELB Flavors Data Source (huaweicloud\_elb\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/elb_flavors)
- [ECS Flavors Data Source (huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)
- [Images Data Source (huaweicloud\_images\_images)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_images)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [Dedicated Load Balancer Resource (huaweicloud\_elb\_loadbalancer)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/elb_loadbalancer)
- [EIP Resource (huaweicloud\_vpc\_eip)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_eip)
- [EIP Association Resource (huaweicloud\_vpc\_eipv3\_associate)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_eipv3_associate)
- [Listener Resource (huaweicloud\_elb\_listener)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/elb_listener)
- [Backend Server Group Resource (huaweicloud\_elb\_pool)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/elb_pool)
- [Auto Scaling Configuration Resource (huaweicloud\_as\_configuration)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/as_configuration)
- [Auto Scaling Group Resource (huaweicloud\_as\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/as_group)
- [ECS Instance Resource (huaweicloud\_compute\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_instance)
- [Instance Attach to Scaling Group Resource (huaweicloud\_as\_instance\_attach)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/as_instance_attach)
- [Alarm Rule Resource (huaweicloud\_ces\_alarmrule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/ces_alarmrule)
- [Scaling Policy Resource (huaweicloud\_as\_policy)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/as_policy)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    ├── data.huaweicloud_elb_flavors
    │   └── huaweicloud_elb_loadbalancer
    ├── data.huaweicloud_compute_flavors
    │   └── data.huaweicloud_images_images
    │       ├── huaweicloud_as_configuration
    │       └── huaweicloud_compute_instance
    └── huaweicloud_compute_instance

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        ├── huaweicloud_elb_loadbalancer
        ├── huaweicloud_as_group
        └── huaweicloud_compute_instance

huaweicloud_networking_secgroup
    ├── huaweicloud_as_configuration
    └── huaweicloud_compute_instance

huaweicloud_elb_loadbalancer
    ├── huaweicloud_vpc_eipv3_associate
    └── huaweicloud_elb_listener
        └── huaweicloud_elb_pool
            └── huaweicloud_as_group

huaweicloud_vpc_eip
    └── huaweicloud_vpc_eipv3_associate

huaweicloud_as_configuration
    └── huaweicloud_as_group
        ├── huaweicloud_as_instance_attach
        └── huaweicloud_ces_alarmrule
            └── huaweicloud_as_policy
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Data Sources

Add the following script to the TF file (e.g., main.tf) to query availability zone, ELB flavor, ECS flavor, and image information:

```hcl
# Query availability zone information
data "huaweicloud_availability_zones" "test" {
  count = var.availability_zone == "" ? 1 : 0
}

# Query ELB flavor information
data "huaweicloud_elb_flavors" "test" {
  type = "L7"
}

# Query ECS flavor information (only query when flavor_id is not specified)
data "huaweicloud_compute_flavors" "test" {
  count = var.instance_flavor_id == "" ? 1 : 0

  performance_type  = var.instance_flavor_performance_type
  cpu_core_count    = var.instance_flavor_cpu_core_count
  memory_size       = var.instance_flavor_memory_size
  availability_zone = var.availability_zone != "" ? var.availability_zone : try(data.huaweicloud_availability_zones.test[0].names[0], null)
}

# Query image information (only query when image_id is not specified)
data "huaweicloud_images_images" "test" {
  count = var.instance_image_id == "" ? 1 : 0

  flavor_id  = var.instance_flavor_id != "" ? var.instance_flavor_id : try(data.huaweicloud_compute_flavors.test[0].ids[0], null)
  visibility = var.instance_image_visibility
  os         = var.instance_image_os
}
```

**Parameter Description**:

- **type**: ELB flavor type, set to "L7" (Layer 7 load balancing)
- **performance\_type**: ECS flavor performance type, assigned by referencing input variable instance\_flavor\_performance\_type, default value is "normal"
- **cpu\_core\_count**: CPU core count, assigned by referencing input variable instance\_flavor\_cpu\_core\_count, default value is 2
- **memory\_size**: Memory size, assigned by referencing input variable instance\_flavor\_memory\_size, default value is 4 (GB)
- **availability\_zone**: Availability zone, assigned by referencing input variables or availability zones data source
- **flavor\_id**: Flavor ID, assigned by referencing input variables or ECS flavors data source
- **visibility**: Image visibility, assigned by referencing input variable instance\_image\_visibility, default value is "public"
- **os**: Operating system, assigned by referencing input variable instance\_image\_os, default value is "Ubuntu"

### 3. Create Basic Network Resources

Add the following script to the TF file (e.g., main.tf) to create VPC, subnet, and security group:

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
  description = "The gateway IP address of the subnet"
  type        = string
  default     = ""
}

variable "security_group_name" {
  description = "The name of the security group"
  type        = string
}

# Create VPC
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}

# Create subnet
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr != "" ? var.subnet_cidr : cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0)
  gateway_ip = var.subnet_gateway_ip != "" ? var.subnet_gateway_ip : cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1)
}

# Create security group
resource "huaweicloud_networking_secgroup" "test" {
  name = var.security_group_name
}
```

### 4. Create Dedicated Load Balancer Resource

Add the following script to the TF file (e.g., main.tf) to create a dedicated load balancer:

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

variable "loadbalancer_force_delete" {
  description = "Whether to force delete the loadbalancer"
  type        = bool
  default     = true
}

# Create dedicated load balancer
resource "huaweicloud_elb_loadbalancer" "test" {
  name                  = var.loadbalancer_name
  vpc_id                = huaweicloud_vpc.test.id
  ipv4_subnet_id        = huaweicloud_vpc_subnet.test.ipv4_subnet_id
  l7_flavor_id          = try(data.huaweicloud_elb_flavors.test.ids[0], null)
  availability_zone     = var.availability_zone != "" ? [var.availability_zone] : try(slice(data.huaweicloud_availability_zones.test[0].names, 0, 1), null)
  cross_vpc_backend     = var.loadbalancer_cross_vpc_backend
  description           = var.loadbalancer_description
  enterprise_project_id = var.enterprise_project_id
  tags                  = var.loadbalancer_tags
  force_delete          = var.loadbalancer_force_delete
}
```

**Parameter Description**:

- **name**: Load balancer name, assigned by referencing input variable loadbalancer\_name
- **vpc\_id**: VPC ID, assigned by referencing the VPC resource
- **ipv4\_subnet\_id**: IPv4 subnet ID, assigned by referencing the subnet resource
- **l7\_flavor\_id**: L7 flavor ID, assigned by referencing the ELB flavors data source
- **availability\_zone**: Availability zone list, assigned by referencing input variables or availability zones data source
- **cross\_vpc\_backend**: Whether to enable cross-VPC backend, assigned by referencing input variable loadbalancer\_cross\_vpc\_backend, default value is false
- **description**: Load balancer description, assigned by referencing input variable loadbalancer\_description, optional parameter
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing input variable enterprise\_project\_id, optional parameter
- **tags**: Tags, assigned by referencing input variable loadbalancer\_tags, optional parameter
- **force\_delete**: Whether to force delete, assigned by referencing input variable loadbalancer\_force\_delete, default value is true

### 5. Create EIP Resource and Bind to Load Balancer

Add the following script to the TF file (e.g., main.tf) to create an EIP and bind it to the load balancer:

```hcl
variable "eip_type" {
  description = "The type of the EIP"
  type        = string
  default     = "5_bgp"
}

variable "bandwidth_name" {
  description = "The name of the EIP bandwidth"
  type        = string
  default     = "tf_test_eip"
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

# Create EIP
resource "huaweicloud_vpc_eip" "test" {
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

# Bind EIP to load balancer
resource "huaweicloud_vpc_eipv3_associate" "test" {
  publicip_id             = huaweicloud_vpc_eip.test.id
  associate_instance_type = "ELB"
  associate_instance_id   = huaweicloud_elb_loadbalancer.test.id
}
```

**Parameter Description**:

- **publicip.type**: EIP type, assigned by referencing input variable eip\_type, default value is "5\_bgp"
- **bandwidth.name**: Bandwidth name, assigned by referencing input variable bandwidth\_name, default value is "tf\_test\_eip"
- **bandwidth.size**: Bandwidth size, assigned by referencing input variable bandwidth\_size, default value is 5 (Mbps)
- **bandwidth.share\_type**: Bandwidth share type, assigned by referencing input variable bandwidth\_share\_type, default value is "PER"
- **bandwidth.charge\_mode**: Bandwidth charge mode, assigned by referencing input variable bandwidth\_charge\_mode, default value is "traffic"
- **associate\_instance\_type**: Associate instance type, set to "ELB"
- **associate\_instance\_id**: Associate instance ID, assigned by referencing the load balancer resource

### 6. Create Listener Resource

Add the following script to the TF file (e.g., main.tf) to create a listener:

```hcl
variable "listener_name" {
  description = "The name of the listener"
  type        = string
}

variable "listener_protocol" {
  description = "The protocol of the listener"
  type        = string
  default     = "HTTP"
}

variable "listener_port" {
  description = "The port of the listener"
  type        = number
  default     = 8080
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

# Create listener
resource "huaweicloud_elb_listener" "test" {
  loadbalancer_id  = huaweicloud_elb_loadbalancer.test.id
  name             = var.listener_name
  protocol         = var.listener_protocol
  protocol_port    = var.listener_port
  idle_timeout     = var.listener_idle_timeout
  request_timeout  = var.listener_request_timeout
  response_timeout = var.listener_response_timeout
  description      = var.listener_description
  tags             = var.listener_tags
}
```

**Parameter Description**:

- **loadbalancer\_id**: Load balancer ID, assigned by referencing the load balancer resource
- **name**: Listener name, assigned by referencing input variable listener\_name
- **protocol**: Protocol type, assigned by referencing input variable listener\_protocol, default value is "HTTP"
- **protocol\_port**: Listener port, assigned by referencing input variable listener\_port, default value is 8080
- **idle\_timeout**: Idle timeout, assigned by referencing input variable listener\_idle\_timeout, default value is 60 (seconds)
- **request\_timeout**: Request timeout, assigned by referencing input variable listener\_request\_timeout, optional parameter
- **response\_timeout**: Response timeout, assigned by referencing input variable listener\_response\_timeout, optional parameter
- **description**: Listener description, assigned by referencing input variable listener\_description, optional parameter
- **tags**: Tags, assigned by referencing input variable listener\_tags, optional parameter

### 7. Create Backend Server Group Resource

Add the following script to the TF file (e.g., main.tf) to create a backend server group:

```hcl
variable "pool_name" {
  description = "The name of the pool"
  type        = string
  default     = null
}

variable "pool_protocol" {
  description = "The protocol of the pool"
  type        = string
  default     = "HTTP"
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

  type = list(object({
    type        = string
    cookie_name = optional(string, null)
    timeout     = optional(number, null)
  }))

  default  = []
  nullable = false
}

# Create backend server group
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

- **listener\_id**: Listener ID, assigned by referencing the listener resource
- **name**: Backend server group name, assigned by referencing input variable pool\_name, optional parameter
- **protocol**: Protocol type, assigned by referencing input variable pool\_protocol, default value is "HTTP"
- **lb\_method**: Load balancing algorithm, assigned by referencing input variable pool\_method, default value is "ROUND\_ROBIN"
- **any\_port\_enable**: Whether to enable any port, assigned by referencing input variable pool\_any\_port\_enable, default value is false
- **description**: Backend server group description, assigned by referencing input variable pool\_description, optional parameter
- **persistence**: Session persistence configuration, configured through dynamic blocks, optional parameter

### 8. Create Auto Scaling Configuration Resource

Add the following script to the TF file (e.g., main.tf) to create an Auto Scaling configuration:

```hcl
variable "configuration_name" {
  description = "The name of the scaling configuration"
  type        = string
}

variable "configuration_image_id" {
  description = "The image ID of the scaling configuration"
  type        = string
  default     = ""
}

variable "configuration_flavor_id" {
  description = "The flavor ID of the scaling configuration"
  type        = string
  default     = ""
}

variable "configuration_user_data" {
  description = "The user data for the scaling configuration instances"
  type        = string
}

variable "configuration_disks" {
  description = "The disk configurations for the scaling configuration instances"

  type = list(object({
    size        = number
    volume_type = string
    disk_type   = string
  }))

  nullable = false
}

# Create Auto Scaling configuration
resource "huaweicloud_as_configuration" "test" {
  scaling_configuration_name = var.configuration_name

  instance_config {
    image              = var.configuration_image_id != "" ? var.configuration_image_id : try(data.huaweicloud_images_images.test[0].images[0].id, null)
    flavor             = var.configuration_flavor_id != "" ? var.configuration_flavor_id : try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, null)
    security_group_ids = [huaweicloud_networking_secgroup.test.id]
    user_data          = var.configuration_user_data

    dynamic "disk" {
      for_each = var.configuration_disks

      content {
        size        = disk.value["size"]
        volume_type = disk.value["volume_type"]
        disk_type   = disk.value["disk_type"]
      }
    }
  }
}
```

**Parameter Description**:

- **scaling\_configuration\_name**: Scaling configuration name, assigned by referencing input variable configuration\_name
- **instance\_config.image**: Image ID, assigned by referencing input variables or images data source
- **instance\_config.flavor**: Flavor ID, assigned by referencing input variables or ECS flavors data source
- **instance\_config.security\_group\_ids**: Security group ID list, assigned by referencing the security group resource
- **instance\_config.user\_data**: User data, assigned by referencing input variable configuration\_user\_data, used for instance initialization scripts
- **instance\_config.disk**: Disk configuration, configured through dynamic blocks, supports system disk and data disk

### 9. Create Auto Scaling Group Resource

Add the following script to the TF file (e.g., main.tf) to create an Auto Scaling group and associate it with the load balancer:

```hcl
variable "group_name" {
  description = "The name of the AS group"
  type        = string
}

variable "group_desire_instance_number" {
  description = "The desire instance number of the AS group"
  type        = number
  default     = 0
}

variable "group_min_instance_number" {
  description = "The min instance number of the AS group"
  type        = number
  default     = 0
}

variable "group_max_instance_number" {
  description = "The max instance number of the AS group"
  type        = number
  default     = 10
}

variable "group_delete_publicip" {
  description = "Whether to delete the public IP address of the AS group"
  type        = bool
  default     = true
}

variable "group_delete_instances" {
  description = "Whether to delete the instances of the AS group"
  type        = bool
  default     = true
}

variable "group_force_delete" {
  description = "Whether to force delete the AS group"
  type        = bool
  default     = true
}

# Create Auto Scaling group
resource "huaweicloud_as_group" "test" {
  scaling_group_name       = var.group_name
  scaling_configuration_id = huaweicloud_as_configuration.test.id
  desire_instance_number   = var.group_desire_instance_number
  min_instance_number      = var.group_min_instance_number
  max_instance_number      = var.group_max_instance_number
  vpc_id                   = huaweicloud_vpc.test.id
  delete_publicip          = var.group_delete_publicip
  delete_instances         = var.group_delete_instances
  force_delete             = var.group_force_delete

  networks {
    id = huaweicloud_vpc_subnet.test.id
  }

  lbaas_listeners {
    pool_id       = huaweicloud_elb_pool.test.id
    protocol_port = huaweicloud_elb_listener.test.protocol_port
  }

  lifecycle {
    ignore_changes = [
      # When instances are auto-scaled, the desire instance number will be changed.
      desire_instance_number,
    ]
  }
}
```

**Parameter Description**:

- **scaling\_group\_name**: Scaling group name, assigned by referencing input variable group\_name
- **scaling\_configuration\_id**: Scaling configuration ID, assigned by referencing the Auto Scaling configuration resource
- **desire\_instance\_number**: Desired instance number, assigned by referencing input variable group\_desire\_instance\_number, default value is 0
- **min\_instance\_number**: Minimum instance number, assigned by referencing input variable group\_min\_instance\_number, default value is 0
- **max\_instance\_number**: Maximum instance number, assigned by referencing input variable group\_max\_instance\_number, default value is 10
- **vpc\_id**: VPC ID, assigned by referencing the VPC resource
- **delete\_publicip**: Whether to delete public IP when deleting, assigned by referencing input variable group\_delete\_publicip, default value is true
- **delete\_instances**: Whether to delete instances when deleting, assigned by referencing input variable group\_delete\_instances, default value is true
- **force\_delete**: Whether to force delete, assigned by referencing input variable group\_force\_delete, default value is true
- **networks.id**: Network subnet ID, assigned by referencing the subnet resource
- **lbaas\_listeners.pool\_id**: Backend server group ID, assigned by referencing the backend server group resource
- **lbaas\_listeners.protocol\_port**: Listener port, assigned by referencing the listener resource

> Note: Through the `lbaas_listeners` configuration, the Auto Scaling group will automatically add newly created instances to the specified load balancer backend server group. Through `lifecycle.ignore_changes`, Terraform can be prevented from modifying `desire_instance_number` in subsequent updates, as this value will automatically change with Auto Scaling.

### 10. Create ECS Instance and Attach to Scaling Group

Add the following script to the TF file (e.g., main.tf) to create an ECS instance and attach it to the Auto Scaling group:

```hcl
variable "instance_name" {
  description = "The name of the ECS instance"
  type        = string
}

variable "instance_flavor_id" {
  description = "The flavor ID of the instance"
  type        = string
  default     = ""
}

variable "instance_image_id" {
  description = "The image ID of the instance"
  type        = string
  default     = ""
}

variable "availability_zone" {
  description = "The name of the availability zone to which the resources belong"
  type        = string
  default     = ""
}

# Create ECS instance
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
      availability_zone,
    ]
  }
}

# Attach ECS instance to Auto Scaling group
resource "huaweicloud_as_instance_attach" "test" {
  scaling_group_id = huaweicloud_as_group.test.id
  instance_id      = huaweicloud_compute_instance.test.id
}
```

**Parameter Description**:

- **name**: ECS instance name, assigned by referencing input variable instance\_name
- **image\_id**: Image ID, assigned by referencing input variables or images data source
- **flavor\_id**: Flavor ID, assigned by referencing input variables or ECS flavors data source
- **availability\_zone**: Availability zone, assigned by referencing input variables or availability zones data source
- **security\_groups**: Security group list, assigned by referencing the security group resource
- **network.uuid**: Network subnet ID, assigned by referencing the subnet resource
- **scaling\_group\_id**: Scaling group ID, assigned by referencing the Auto Scaling group resource
- **instance\_id**: Instance ID, assigned by referencing the ECS instance resource

### 11. Create Alarm Rule Resource

Add the following script to the TF file (e.g., main.tf) to create an alarm rule:

```hcl
variable "alarm_rule_name" {
  description = "The name of the CES alarm rule"
  type        = string
}

variable "alarm_rule_conditions" {
  description = "The conditions of the CES alarm rule"

  type = list(object({
    period              = number
    filter              = string
    comparison_operator = string
    value               = number
    unit                = string
    count               = number
    alarm_level         = number
    metric_name         = string
  }))

  nullable = false
}

# Create alarm rule
resource "huaweicloud_ces_alarmrule" "test" {
  alarm_name = var.alarm_rule_name

  metric {
    namespace = "SYS.AS"

    dimensions {
      name  = "AutoScalingGroup"
      value = huaweicloud_as_group.test.id
    }
  }

  dynamic "condition" {
    for_each = var.alarm_rule_conditions

    content {
      period              = condition.value["period"]
      filter              = condition.value["filter"]
      comparison_operator = condition.value["comparison_operator"]
      value               = condition.value["value"]
      unit                = condition.value["unit"]
      count               = condition.value["count"]
      alarm_level         = condition.value["alarm_level"]
      metric_name         = condition.value["metric_name"]
    }
  }

  alarm_actions {
    type              = "autoscaling"
    notification_list = []
  }
}
```

**Parameter Description**:

- **alarm\_name**: Alarm rule name, assigned by referencing input variable alarm\_rule\_name
- **metric.namespace**: Namespace, set to "SYS.AS" (Auto Scaling service)
- **metric.dimensions.name**: Dimension name, set to "AutoScalingGroup"
- **metric.dimensions.value**: Dimension value, assigned by referencing the Auto Scaling group resource
- **condition.period**: Statistical period, assigned by referencing input variables
- **condition.filter**: Filter condition, assigned by referencing input variables, such as "max" (maximum value)
- **condition.comparison\_operator**: Comparison operator, assigned by referencing input variables, such as ">" (greater than)
- **condition.value**: Threshold, assigned by referencing input variables
- **condition.unit**: Unit, assigned by referencing input variables, such as "%" (percentage)
- **condition.count**: Consecutive trigger count, assigned by referencing input variables
- **condition.alarm\_level**: Alarm level, assigned by referencing input variables
- **condition.metric\_name**: Metric name, assigned by referencing input variables, such as "cpu\_util" (CPU utilization)
- **alarm\_actions.type**: Alarm action type, set to "autoscaling"
- **alarm\_actions.notification\_list**: Notification list, set to empty array

### 12. Create Scaling Policy Resource

Add the following script to the TF file (e.g., main.tf) to create a scaling policy:

```hcl
variable "policy_name" {
  description = "The name of the AS policy"
  type        = string
}

variable "policy_cool_down_time" {
  description = "The cool down time of the AS policy"
  type        = number
  default     = 900
}

variable "policy_operation" {
  description = "The operation of the AS policy"
  type        = string
  default     = "ADD"
}

variable "policy_instance_number" {
  description = "The instance number of the AS policy"
  type        = number
  default     = 1
}

# Create scaling policy
resource "huaweicloud_as_policy" "test" {
  scaling_policy_name = var.policy_name
  scaling_policy_type = "ALARM"
  scaling_group_id    = huaweicloud_as_group.test.id
  alarm_id            = huaweicloud_ces_alarmrule.test.id
  cool_down_time      = var.policy_cool_down_time

  scaling_policy_action {
    operation       = var.policy_operation
    instance_number = var.policy_instance_number
  }
}
```

**Parameter Description**:

- **scaling\_policy\_name**: Scaling policy name, assigned by referencing input variable policy\_name
- **scaling\_policy\_type**: Scaling policy type, set to "ALARM" (alarm policy)
- **scaling\_group\_id**: Scaling group ID, assigned by referencing the Auto Scaling group resource
- **alarm\_id**: Alarm rule ID, assigned by referencing the alarm rule resource
- **cool\_down\_time**: Cool down time, assigned by referencing input variable policy\_cool\_down\_time, default value is 900 (seconds)
- **scaling\_policy\_action.operation**: Operation type, assigned by referencing input variable policy\_operation, default value is "ADD" (add instances)
- **scaling\_policy\_action.instance\_number**: Instance number, assigned by referencing input variable policy\_instance\_number, default value is 1

### 13. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# VPC and Subnet Configuration
vpc_name    = "tf_test_vpc"
vpc_cidr    = "172.16.0.0/16"
subnet_name = "tf_test_subnet"

# Security Group Configuration
security_group_name = "tf_test_security_group"

# Load Balancer Configuration
loadbalancer_name              = "tf_test_dedicated_loadbalancer"
loadbalancer_cross_vpc_backend = true

# Listener Configuration
listener_name = "tf_test_dedicated_listener"

# Backend Server Group Configuration
pool_name = "tf_test_dedicated_pool"

# Auto Scaling Configuration
configuration_name = "tf_test_as_configuration"
configuration_user_data = <<EOT
#! /bin/bash
echo 'root:$6$V6azyeLwcD3CHlpY$BN3VVq18fmCkj66B4zdHLWevqcxlig' | chpasswd -e
EOT

configuration_disks = [
  {
    size        = 40
    volume_type = "SSD"
    disk_type   = "SYS"
  }
]

# Auto Scaling Group Configuration
group_name = "tf_test_as_group"

# ECS Instance Configuration
instance_name = "tf_test_instance"

# Alarm Rule Configuration
alarm_rule_name = "tf_test_alarm_rule2"
alarm_rule_conditions = [
  {
    alarm_level         = 2
    period              = 300
    filter              = "max"
    comparison_operator = ">"
    value               = 80
    unit                = "%"
    count               = 1
    metric_name         = "cpu_util"
  }
]

# Scaling Policy Configuration
policy_name = "tf_test_as_policy"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially:
   - `configuration_user_data` needs to be set to instance initialization scripts for configuring the initial state of instances
   - `configuration_disks` needs to configure disk information, including system disk and data disk
   - `alarm_rule_conditions` needs to configure alarm conditions, such as triggering an alarm when CPU utilization exceeds 80%
   - `policy_operation` can be set to "ADD" (add instances) or "REMOVE" (remove instances)
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="group_name=my_group" -var="loadbalancer_name=my_lb"`
2. Environment variables: `export TF_VAR_group_name=my_group` and `export TF_VAR_loadbalancer_name=my_lb`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. After the Auto Scaling group is associated with the load balancer, the Auto Scaling service will automatically add newly created instances to the load balancer's backend server group. After alarm rules and scaling policies are configured, when monitoring metrics reach the threshold, the Auto Scaling service will automatically execute scaling operations.

### 14. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create an integrated solution of dedicated load balancer and Auto Scaling:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating VPC, subnet, load balancer, Auto Scaling group, alarm rules, and scaling policies
4. Run `terraform show` to view the details of the created Auto Scaling group

> Note: After the Auto Scaling group is created, it will automatically create or adjust the number of instances according to the configuration. When alarm rules are triggered, scaling policies will automatically execute to increase or decrease the number of instances. Newly created instances will be automatically added to the load balancer's backend server group, achieving automated traffic distribution and elastic resource scaling. Through `lifecycle.ignore_changes`, Terraform can be prevented from modifying parameters that will automatically change (such as `desire_instance_number`) in subsequent updates.

## Reference Information

- [Huawei Cloud Elastic Load Balance Product Documentation](https://support.huaweicloud.com/elb/index.html)
- [Huawei Cloud Auto Scaling Product Documentation](https://support.huaweicloud.com/as/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Dedicated Load Balancer with Auto Scaling](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/elb/dedicated-loadbalancer-with-as)