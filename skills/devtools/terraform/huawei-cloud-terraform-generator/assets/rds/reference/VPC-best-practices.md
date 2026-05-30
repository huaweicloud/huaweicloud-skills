# Deploy Basic Network

## Application Scenario

Virtual Private Cloud (VPC) is a logically isolated network space that users can customize and manage on Huawei Cloud. Through VPC, users can flexibly divide subnets, configure routes and security policies, implementing secure isolation and efficient management of cloud resources. This best practice will introduce how to use Terraform to automatically deploy a basic VPC and its subnets.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)

### Resource/Data Source Dependencies

```
huaweicloud_vpc
    └── huaweicloud_vpc_subnet
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create VPC Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC resource:

```hcl
variable "vpc_name" {
  description = "The VPC name"
  type        = string
}

variable "vpc_cidr" {
  description = "The CIDR block of the VPC"
  type        = string
  default     = "172.16.0.0/16"
}

variable "enterprise_project_id" {
  description = "The ID of the enterprise project to which the VPC belongs"
  type        = string
  default     = null
}

# Create VPC resource
resource "huaweicloud_vpc" "test" {
  name                  = var.vpc_name
  cidr                  = var.vpc_cidr
  enterprise_project_id = var.enterprise_project_id
}
```

**Parameter Description**:

- **name**: VPC name, assigned by referencing the input variable vpc\_name
- **cidr**: VPC CIDR block, assigned by referencing the input variable vpc\_cidr, default value is "172.16.0.0/16"
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing the input variable enterprise\_project\_id, default value is null

### 3. Create VPC Subnet Resource

Add the following script to the TF file to instruct Terraform to create a VPC subnet resource:

```hcl
variable "subnet_name" {
  description = "The subnet name"
  type        = string
}

variable "subnet_cidr" {
  description = "The CIDR block of the subnet"
  type        = string
  default     = "172.16.10.0/24"
}

variable "subnet_gateway" {
  description = "The gateway IP address of the subnet"
  type        = string
  default     = "172.16.10.1"
}

variable "dns_list" {
  description = "The list of DNS server IP addresses"
  type        = list(string)
  default     = null
}

# Create VPC subnet resource
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr
  gateway_ip = var.subnet_gateway
  dns_list   = var.dns_list
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID that the subnet belongs to, referencing the ID of the previously created VPC resource
- **name**: Subnet name, assigned by referencing the input variable subnet\_name
- **cidr**: Subnet CIDR block, assigned by referencing the input variable subnet\_cidr, default value is "172.16.10.0/24"
- **gateway\_ip**: Subnet gateway IP, assigned by referencing the input variable subnet\_gateway, default value is "172.16.10.1"
- **dns\_list**: List of DNS server IP addresses for the subnet, assigned by referencing the input variable dns\_list, default value is null

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Huawei Cloud authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# VPC configuration
vpc_name              = "tf_test_vpc"
vpc_cidr              = "172.16.0.0/16"
enterprise_project_id = null

# Subnet configuration
subnet_name    = "tf_test_subnet"
subnet_cidr    = "172.16.10.0/24"
subnet_gateway = "172.16.10.1"
dns_list       = ["114.114.114.114", "8.8.8.8"]
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="subnet_name=my-subnet"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating VPC and subnets
4. Run `terraform show` to view the created VPC and subnet details

## Reference Information

- [Huawei Cloud VPC Product Documentation](https://support.huaweicloud.com/vpc/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For VPC Basic Network](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/vpc/basic)

# Deploy Peering Connection

## Application Scenario

VPC Peering is used to implement private network connectivity between two Virtual Private Clouds (VPCs), suitable for multi-VPC networking, cross-business system communication, and other scenarios. Through VPC Peering, users can achieve secure, low-latency internal network communication between different VPCs, meeting resource access requirements in enterprise multi-network environments. This best practice will introduce how to use Terraform to automatically deploy two VPCs and their subnets, and establish VPC Peering connections and routes.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zone List Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [VPC Peering Connection Resource (huaweicloud\_vpc\_peering\_connection)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_peering_connection)
- [VPC Route Resource (huaweicloud\_vpc\_route)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_route)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
    └── huaweicloud_vpc_peering_connection
        └── huaweicloud_vpc_route
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Availability Zone Information

Add the following script to the TF file (e.g., main.tf) to query availability zone information (not directly used in this practice, but recommended to keep for future expansion):

```hcl
data "huaweicloud_availability_zones" "test" {}
```

**Parameter Description**:

- This data source requires no configuration parameters and will automatically obtain all availability zone information in the current region.

### 3. Create VPC and Subnet Resources

Add the following script to the TF file to instruct Terraform to batch create VPCs and their subnets:

```hcl
variable "vpc_configurations" {
  description = "The list of VPC configurations for peering connection"
  type = list(object({
    vpc_name              = string
    vpc_cidr              = string
    subnet_name           = string
    enterprise_project_id = optional(string, null)
  }))
  validation {
    condition     = length(var.vpc_configurations) == 2
    error_message = "Exactly 2 VPC configurations are required for peering connection."
  }
}

# Create VPC resources
resource "huaweicloud_vpc" "test" {
  count = length(var.vpc_configurations)
  name                  = lookup(var.vpc_configurations[count.index], "vpc_name", null)
  cidr                  = lookup(var.vpc_configurations[count.index], "vpc_cidr", null)
  enterprise_project_id = lookup(var.vpc_configurations[count.index], "enterprise_project_id", null)
}

# Create VPC subnet resources
resource "huaweicloud_vpc_subnet" "test" {
  count = length(var.vpc_configurations)
  vpc_id     = huaweicloud_vpc.test[count.index].id
  name       = lookup(var.vpc_configurations[count.index], "subnet_name", null)
  cidr       = try(cidrsubnet(lookup(var.vpc_configurations[count.index], "vpc_cidr", null), 6, 32), null)
  gateway_ip = try(cidrhost(cidrsubnet(lookup(var.vpc_configurations[count.index], "vpc_cidr", null), 6, 32), 1), null)
}
```

**Parameter Description**:

- **vpc\_configurations**: List of VPC and subnet configurations, requires exactly 2 sets of configurations
- **name/cidr/enterprise\_project\_id**: VPC name, CIDR block, enterprise project ID, assigned through vpc\_configurations respectively
- **subnet\_name/cidr/gateway\_ip**: Subnet name, CIDR block, gateway IP, assigned through vpc\_configurations and calculation functions respectively

### 4. Create VPC Peering Connection

Add the following script to the TF file to instruct Terraform to create a VPC Peering connection:

```hcl
variable "peering_connection_name" {
  description = "The name of the VPC peering connection"
  type        = string
}

# Create VPC Peering connection
resource "huaweicloud_vpc_peering_connection" "test" {
  count = length(var.vpc_configurations) == 2 ? 1 : 0
  name        = var.peering_connection_name
  vpc_id      = try(huaweicloud_vpc.test[0].id, null) # source VPC
  peer_vpc_id = try(huaweicloud_vpc.test[1].id, null) # target VPC
}
```

**Parameter Description**:

- **name**: Peering connection name, assigned through input variable peering\_connection\_name
- **vpc\_id/peer\_vpc\_id**: Source VPC and target VPC IDs, referencing the previously created VPC resources respectively

### 5. Configure VPC Peering Routes

Add the following script to the TF file to instruct Terraform to configure Peering routes for each VPC:

```hcl
# Configure VPC Peering routes
resource "huaweicloud_vpc_route" "test" {
  count = length(var.vpc_configurations)
  vpc_id      = huaweicloud_vpc.test[count.index].id
  destination = try(cidrsubnet(lookup(var.vpc_configurations[count.index], "vpc_cidr", null), 6, 33), null)
  type        = "peering"
  nexthop     = try(huaweicloud_vpc_peering_connection.test[0].id, null)
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID that the route belongs to, referencing the previously created VPC resource
- **destination**: CIDR block of the peer VPC, automatically calculated
- **type**: Route type, fixed as "peering"
- **nexthop**: Next hop, referencing the ID of the previously created VPC Peering connection

### 6. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Huawei Cloud authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# VPC Peering configuration
vpc_configurations = [
  {
    vpc_name    = "tf_test_source_vpc"
    vpc_cidr    = "192.168.0.0/18"
    subnet_name = "tf_test_source_subnet"
  },
  {
    vpc_name    = "tf_test_target_vpc"
    vpc_cidr    = "192.168.128.0/18"
    subnet_name = "tf_test_target_subnet"
  }
]
peering_connection_name = "tf_test_peering"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="peering_connection_name=my-peering"`
2. Environment variables: `export TF_VAR_peering_connection_name=my-peering`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 7. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating VPC Peering connections and related resources
4. Run `terraform show` to view the created VPC Peering connection and route details

## Reference Information

- [Huawei Cloud VPC Product Documentation](https://support.huaweicloud.com/vpc/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For VPC Peering Connection](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/vpc/peering)

# Deploy Security Group

## Application Scenario

Security Group is a virtual firewall in Huawei Cloud VPC used to control network access. By configuring security group rules, you can precisely control network access permissions for cloud servers, databases, and other resources. Security groups support both inbound and outbound rule configurations, effectively protecting the security of cloud resources. This best practice will introduce how to use Terraform to automatically deploy security groups and their rule configurations.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [Security Group Rule Resource (huaweicloud\_networking\_secgroup\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup_rule)

### Resource/Data Source Dependencies

```
huaweicloud_networking_secgroup
    └── huaweicloud_networking_secgroup_rule
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create Security Group Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a security group resource:

```hcl
variable "security_group_name" {
  description = "The name of the security group."
  type        = string
}

# Create security group resource
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: Security group name, assigned by referencing the input variable security\_group\_name
- **delete\_default\_rules**: Whether to delete default rules, set to true to delete default rules

### 3. Create Security Group Rule Resources

Add the following script to the TF file to instruct Terraform to batch create security group rules:

```hcl
variable "security_group_rule_configurations" {
  description = "The list of security group rule configurations. Each item is a map with keys: direction, ethertype, protocol, ports, remote_ip_prefix."
  type = list(object({
    direction        = optional(string, "ingress")
    ethertype        = optional(string, "IPv4")
    protocol         = optional(string, null)
    ports            = optional(string, null)
    remote_ip_prefix = optional(string, "0.0.0.0/0")
  }))
  nullable = false
}

# Create security group rule resources
resource "huaweicloud_networking_secgroup_rule" "test" {
  count = length(var.security_group_rule_configurations)

  direction         = lookup(var.security_group_rule_configurations[count.index], "direction", "ingress")
  ethertype         = lookup(var.security_group_rule_configurations[count.index], "ethertype", "IPv4")
  protocol          = lookup(var.security_group_rule_configurations[count.index], "protocol", null)
  ports             = lookup(var.security_group_rule_configurations[count.index], "ports", null)
  remote_ip_prefix  = lookup(var.security_group_rule_configurations[count.index], "remote_ip_prefix", "0.0.0.0/0")
  security_group_id = huaweicloud_networking_secgroup.test.id
}
```

**Parameter Description**:

- **direction**: Rule direction, assigned by referencing the input variable security\_group\_rule\_configurations, default value is "ingress"
- **ethertype**: Ethernet type, assigned by referencing the input variable security\_group\_rule\_configurations, default value is "IPv4"
- **protocol**: Protocol type, assigned by referencing the input variable security\_group\_rule\_configurations, default value is null
- **ports**: Port range, assigned by referencing the input variable security\_group\_rule\_configurations, default value is null. **Note: When using port_range_min and port_range_max parameters, port_range_min must be greater than 0**
- **remote\_ip\_prefix**: Remote IP address range, assigned by referencing the input variable security\_group\_rule\_configurations, default value is "0.0.0.0/0"
- **security\_group\_id**: Security group ID, referencing the ID of the previously created security group resource

**Important Constraints**:

- **port_range_min**: The minimum port number in the range. **This value must be greater than 0**. Port 0 is reserved and cannot be used in security group rules.
- **port_range_max**: The maximum port number in the range. Must be greater than or equal to port_range_min.

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Huawei Cloud authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Security group configuration
security_group_name = "tf_test_security_group"
security_group_rule_configurations = [
  # Allow all IPv4 ingress traffic of the ICMP protocol
  {
    direction        = "ingress"
    ethertype        = "IPv4"
    protocol         = "icmp"
    ports            = null
    remote_ip_prefix = "0.0.0.0/0"
  },
  # Allow some ports for IPv4 ingress traffic of the TCP protocol
  {
    direction        = "ingress"
    ethertype        = "IPv4"
    protocol         = "tcp"
    ports            = "22-23,443,3389,30100-30130"
    remote_ip_prefix = "0.0.0.0/0"
  },
  # Allow all IPv4 egress traffic
  {
    direction        = "egress"
    ethertype        = "IPv4"
    remote_ip_prefix = "0.0.0.0/0"
  },
  # Allow all IPv6 egress traffic
  {
    direction        = "egress"
    ethertype        = "IPv6"
    remote_ip_prefix = "::/0"
  }
]
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="security_group_name=my-security-group"`
2. Environment variables: `export TF_VAR_security_group_name=my-security-group`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating security groups and rules
4. Run `terraform show` to view the created security group and rule details

## Reference Information

- [Huawei Cloud VPC Product Documentation](https://support.huaweicloud.com/vpc/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For VPC Security Group](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/vpc/security-group)

# Deploy VIP and Associate Instance

## Application Scenario

Virtual IP (VIP) is a network technology in Huawei Cloud VPC used to achieve high availability, which can bind a virtual IP address to multiple ECS instances, implementing load balancing and failover. Through VIP association, high availability deployment of business can be achieved. When an ECS instance fails, traffic can automatically switch to other healthy instances. This best practice will introduce how to use Terraform to automatically deploy VIP associations, including creating ECS instances, VIP resources, and their association configurations.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zone List Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [ECS Flavor List Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)
- [IMS Image List Query Data Source (data.huaweicloud\_images\_images)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_images)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [Security Group Rule Resource (huaweicloud\_networking\_secgroup\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup_rule)
- [ECS Instance Resource (huaweicloud\_compute\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_instance)
- [VIP Resource (huaweicloud\_networking\_vip)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_vip)
- [VIP Association Resource (huaweicloud\_networking\_vip\_associate)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_vip_associate)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    ├── data.huaweicloud_compute_flavors
    │   └── data.huaweicloud_images_images
    │       └── huaweicloud_compute_instance
    └── huaweicloud_compute_instance

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        ├── huaweicloud_compute_instance
        └── huaweicloud_networking_vip
            └── huaweicloud_networking_vip_associate

huaweicloud_networking_secgroup
    ├── huaweicloud_networking_secgroup_rule
    └── huaweicloud_compute_instance

huaweicloud_compute_instance
    └── huaweicloud_networking_vip_associate
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Prerequisite Resource Preparation

This best practice requires creating prerequisite resources such as VPC, subnets, security groups, and ECS instances first. Please follow the following steps in the "Deploy Basic Elastic Cloud Server" best practice for preparation:

- **Step 2**: Query availability zones required for ECS instance resource creation through data sources
- **Step 3**: Query flavors required for ECS instance resource creation through data sources
- **Step 4**: Query images required for ECS instance resource creation through data sources
- **Step 5**: Create VPC resource
- **Step 6**: Create VPC subnet resource
- **Step 7**: Create security group resource
- **Step 8**: Create ECS instance

After completing the above steps, continue with the subsequent steps of this best practice.

### 3. Create VIP Resource

Add the following script to the TF file to instruct Terraform to create a VIP resource:

```hcl
# Create VIP resource
resource "huaweicloud_networking_vip" "test" {
  network_id = huaweicloud_vpc_subnet.test.id
}
```

**Parameter Description**:

- **network\_id**: Network ID that the VIP belongs to, referencing the ID of the previously created subnet resource

### 4. Create VIP Association Resource

Add the following script to the TF file to instruct Terraform to create a VIP association resource:

```hcl
# Create VIP association resource
resource "huaweicloud_networking_vip_associate" "test" {
  vip_id   = huaweicloud_networking_vip.test.id
  port_ids = try([
    huaweicloud_compute_instance.test.network[0].port
  ], [])
}
```

**Parameter Description**:

- **vip\_id**: VIP ID, referencing the ID of the previously created VIP resource
- **port\_ids**: List of port IDs to associate, using try function to get the network port ID of the ECS instance, using empty list if retrieval fails

### 5. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Huawei Cloud authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# VPC configuration
vpc_name = "tf_test_vpc"
vpc_cidr = "192.168.0.0/16"

# Subnet configuration
subnet_name = "tf_test_subnet"

# Security group configuration
security_group_name = "tf_test_security_group"

# ECS instance configuration
instance_name          = "tf_test_instance"
administrator_password = "YourPasswordInput!"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="subnet_name=my-subnet"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 6. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating VIP associations
4. Run `terraform show` to view the created VIP association details

## Reference Information

- [Huawei Cloud VPC Product Documentation](https://support.huaweicloud.com/vpc/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For VPC VIP and Associate Instance](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/vpc/vip)
