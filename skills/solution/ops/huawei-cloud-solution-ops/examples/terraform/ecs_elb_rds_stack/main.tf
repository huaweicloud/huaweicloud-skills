data "huaweicloud_availability_zones" "current" {}

data "huaweicloud_compute_flavors" "ecs" {
  availability_zone = data.huaweicloud_availability_zones.current.names[0]
  performance_type  = var.instance_flavor_performance_type
  cpu_core_count    = var.instance_flavor_cpu_core_count
  memory_size       = var.instance_flavor_memory_size
}

data "huaweicloud_images_image" "ecs" {
  name        = var.image_name
  visibility  = var.image_visibility
  most_recent = true
}

data "huaweicloud_rds_flavors" "db" {
  count = var.rds_flavor == "" ? 1 : 0

  db_type           = var.rds_db_type
  db_version        = var.rds_db_version
  instance_mode     = var.rds_instance_mode
  group_type        = var.rds_flavor_group_type
  vcpus             = var.rds_flavor_vcpus
  memory            = var.rds_flavor_memory
  availability_zone = data.huaweicloud_availability_zones.current.names[0]
}

locals {
  selected_ecs_flavor = try(data.huaweicloud_compute_flavors.ecs.flavors[0].id, null)
  selected_rds_flavor = var.rds_flavor != "" ? var.rds_flavor : try(data.huaweicloud_rds_flavors.db[0].flavors[0].name, null)
}

resource "huaweicloud_vpc" "this" {
  name = var.vpc_name
  cidr = var.vpc_cidr

  tags = var.tags
}

resource "huaweicloud_vpc_subnet" "this" {
  vpc_id     = huaweicloud_vpc.this.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip
  dns_list   = var.subnet_dns_list
}

resource "huaweicloud_networking_secgroup" "web" {
  name                 = var.web_security_group_name
  delete_default_rules = true
}

resource "huaweicloud_networking_secgroup_rule" "web_ingress" {
  security_group_id = huaweicloud_networking_secgroup.web.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  ports             = tostring(var.web_port)
  remote_ip_prefix  = var.web_ingress_cidr
}

resource "huaweicloud_networking_secgroup_rule" "web_egress" {
  security_group_id = huaweicloud_networking_secgroup.web.id
  direction         = "egress"
  ethertype         = "IPv4"
  remote_ip_prefix  = "0.0.0.0/0"
}

resource "huaweicloud_networking_secgroup" "db" {
  name                 = var.db_security_group_name
  delete_default_rules = true
}

resource "huaweicloud_networking_secgroup_rule" "db_ingress" {
  security_group_id = huaweicloud_networking_secgroup.db.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  ports             = tostring(var.rds_port)
  remote_ip_prefix  = var.subnet_cidr
}

resource "huaweicloud_compute_instance" "web" {
  name               = var.instance_name
  image_id           = data.huaweicloud_images_image.ecs.id
  flavor_id          = local.selected_ecs_flavor
  availability_zone  = data.huaweicloud_availability_zones.current.names[0]
  security_group_ids = [huaweicloud_networking_secgroup.web.id]
  system_disk_type   = var.system_disk_type
  system_disk_size   = var.system_disk_size
  admin_pass         = var.admin_password
  user_data          = var.user_data

  network {
    uuid = huaweicloud_vpc_subnet.this.id
  }

  lifecycle {
    precondition {
      condition     = local.selected_ecs_flavor != null
      error_message = "No ECS flavor matched the requested filters."
    }
  }
}

resource "huaweicloud_rds_instance" "db" {
  name              = var.rds_name
  flavor            = local.selected_rds_flavor
  vpc_id            = huaweicloud_vpc.this.id
  subnet_id         = huaweicloud_vpc_subnet.this.id
  security_group_id = huaweicloud_networking_secgroup.db.id
  availability_zone = [data.huaweicloud_availability_zones.current.names[0]]

  db {
    type     = var.rds_db_type
    version  = var.rds_db_version
    port     = var.rds_port
    password = var.rds_password
  }

  volume {
    type = var.rds_volume_type
    size = var.rds_volume_size
  }

  backup_strategy {
    start_time = var.rds_backup_start_time
    keep_days  = var.rds_backup_keep_days
  }

  lifecycle {
    precondition {
      condition     = local.selected_rds_flavor != null
      error_message = "No RDS flavor matched the requested filters."
    }
  }
}

resource "huaweicloud_lb_loadbalancer" "web" {
  name          = var.loadbalancer_name
  vip_subnet_id = huaweicloud_vpc_subnet.this.ipv4_subnet_id

  tags = var.tags
}

resource "huaweicloud_vpc_eip" "web" {
  count = var.create_eip ? 1 : 0

  publicip {
    type = "5_bgp"
  }

  bandwidth {
    name        = var.bandwidth_name
    size        = var.bandwidth_size
    share_type  = "PER"
    charge_mode = "traffic"
  }

  tags = var.tags
}

resource "huaweicloud_vpc_eipv3_associate" "web" {
  count = var.create_eip ? 1 : 0

  publicip_id             = huaweicloud_vpc_eip.web[0].id
  associate_instance_type = "ELB"
  associate_instance_id   = huaweicloud_lb_loadbalancer.web.id
}

resource "huaweicloud_lb_listener" "web" {
  loadbalancer_id = huaweicloud_lb_loadbalancer.web.id
  name            = var.listener_name
  protocol        = "HTTP"
  protocol_port   = var.listener_port
}

resource "huaweicloud_lb_pool" "web" {
  listener_id = huaweicloud_lb_listener.web.id
  name        = var.pool_name
  protocol    = "HTTP"
  lb_method   = "ROUND_ROBIN"
}

resource "huaweicloud_lb_member" "web" {
  pool_id       = huaweicloud_lb_pool.web.id
  address       = huaweicloud_compute_instance.web.access_ip_v4
  protocol_port = var.web_port
  subnet_id     = huaweicloud_vpc_subnet.this.ipv4_subnet_id
  weight        = 1
}

resource "huaweicloud_lb_monitor" "web" {
  pool_id        = huaweicloud_lb_pool.web.id
  type           = "HTTP"
  delay          = 5
  timeout        = 3
  max_retries    = 3
  url_path       = var.monitor_url_path
  expected_codes = "200-399"
}
