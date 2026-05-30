# Huawei Cloud-Specific Best Practices

## Regions and Availability Zones

- Prefer `cn-north-4` as the default region
- Explicitly specify availability zones in multi-AZ deployments for improved availability
- Use variables to manage region and availability zone configurations

```hcl
variable "primary_region" {
  description = "Primary region"
  type        = string
  default     = "cn-north-7"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["cn-north-7a", "cn-north-7b"]
}

resource "huaweicloud_vpc_subnet" "primary" {
  name              = "subnet-primary"
  cidr              = "192.168.1.0/24"
  gateway_ip        = "192.168.1.1"
  vpc_id            = huaweicloud_vpc.main.id
  availability_zone = var.availability_zones[0]
  tags              = local.common_tags
}
```

## Resource Tagging Standards

Huawei Cloud recommends the following standard tags:

```hcl
locals {
  standard_tags = {
    # Business tags
    Environment  = var.environment
    Project      = var.project_name
    Service      = var.service_name
    CostCenter   = var.cost_center

    # Management tags
    ManagedBy    = "Terraform"
    Owner        = var.owner
    CreatedBy    = var.created_by
    UpdatedBy    = var.updated_by

    # Technical tags
    Version      = var.version
    Tier         = var.tier
  }
}

resource "huaweicloud_compute_instance" "web" {
  name  = "web-server"
  image_id = data.huaweicloud_images_image.test.id
  flavor_id = "s6.small.1"
  security_group_ids = [huaweicloud_networking_secgroup.test.id]
  subnet_id = huaweicloud_vpc_subnet.test.id

  tags = local.standard_tags
}
```

## Network Security Group Best Practices

- Configure security group rules using the principle of least privilege
- Explicitly specify port ranges and protocols
- Use CIDR blocks or security group IDs instead of IP addresses (unless necessary)
- Configure separate rules for inbound and outbound traffic

```hcl
# SSH access
resource "huaweicloud_networking_secgroup_rule" "ssh" {
  direction         = "ingress"
  ethertype         = "IPv4"
  port_range_min    = 22
  port_range_max    = 22
  protocol          = "tcp"
  remote_ip_prefix  = var.allowed_ssh_cidr
  security_group_id = huaweicloud_networking_secgroup.web.id
}

# HTTP access
resource "huaweicloud_networking_secgroup_rule" "http" {
  direction         = "ingress"
  ethertype         = "IPv4"
  port_range_min    = 80
  port_range_max    = 80
  protocol          = "tcp"
  remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = huaweicloud_networking_secgroup.web.id
}

# HTTPS access
resource "huaweicloud_networking_secgroup_rule" "https" {
  direction         = "ingress"
  ethertype         = "IPv4"
  port_range_min    = 443
  port_range_max    = 443
  protocol          = "tcp"
  remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = huaweicloud_networking_secgroup.web.id
}

# Outbound traffic (allow all)
resource "huaweicloud_networking_secgroup_rule" "egress_all" {
  direction         = "egress"
  ethertype         = "IPv4"
  remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = huaweicloud_networking_secgroup.web.id
}
```

## Data Disk Configuration

- Configure data disks for ECS instances to separate system and data
- Use appropriate disk types (SAS, SSD)
- Set reasonable disk sizes

```hcl
resource "huaweicloud_compute_instance" "web" {
  name              = "web-server"
  image_id          = data.huaweicloud_images_image.test.id
  flavor_id         = "s6.small.1"
  security_group_ids = [huaweicloud_networking_secgroup.web.id]
  subnet_id         = huaweicloud_vpc_subnet.web.id
  availability_zone = "cn-north-7a"

  # System disk
  system_disk_type = "SAS"
  system_disk_size = 40

  # Data disks
  data_disks {
    type = "SAS"
    size = 100
  }

  data_disks {
    type = "SSD"
    size = 200
  }

  tags = local.standard_tags
}
```
