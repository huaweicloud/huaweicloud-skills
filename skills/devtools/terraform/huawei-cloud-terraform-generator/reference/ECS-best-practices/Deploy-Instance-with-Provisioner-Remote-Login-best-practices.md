# Deploy Instance with Provisioner Remote Login

## Application Scenario

Elastic Cloud Server (ECS) is a fundamental computing component composed of CPU, memory, operating system, and cloud disks, providing a reliable, secure, flexible, and efficient computing environment for your applications. ECS service supports multiple instance specifications and operating systems, meeting computing requirements for different scales and scenarios.

ECS instances with provisioner remote login are advanced functions in ECS service. Through Terraform's provisioner mechanism, remote commands can be automatically executed after ECS instance creation, implementing automated instance configuration and initialization. This configuration is suitable for scenarios such as automated deployment, configuration management, and application installation. This best practice will introduce how to use Terraform to automatically deploy ECS instances with provisioner remote login, including key pair creation, network environment configuration, EIP binding, and remote command execution.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [ECS Flavors Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)
- [Images Query Data Source (data.huaweicloud\_images\_images)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_images)

### Resources

- [Key Pair Resource (huaweicloud\_kps\_keypair)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/kps_keypair)
- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [Security Group Rule Resource (huaweicloud\_networking\_secgroup\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup_rule)
- [EIP Resource (huaweicloud\_vpc\_eip)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_eip)
- [ECS Instance Resource (huaweicloud\_compute\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_instance)
- [EIP Binding Resource (huaweicloud\_compute\_eip\_associate)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_eip_associate)
- [Null Resource (null\_resource)](https://registry.terraform.io/providers/hashicorp/null/latest/docs/resources/resource)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones.test
    └── huaweicloud_compute_instance.test

data.huaweicloud_compute_flavors.test
    └── huaweicloud_compute_instance.test

data.huaweicloud_images_images.test
    └── huaweicloud_compute_instance.test

huaweicloud_kps_keypair.test
    └── huaweicloud_compute_instance.test

huaweicloud_vpc.test
    └── huaweicloud_vpc_subnet.test
        └── huaweicloud_compute_instance.test

huaweicloud_networking_secgroup.test
    ├── huaweicloud_networking_secgroup_rule.test
    └── huaweicloud_compute_instance.test

huaweicloud_vpc_eip.test
    └── huaweicloud_compute_eip_associate.test
        └── null_resource.test

huaweicloud_compute_instance.test
    └── huaweicloud_compute_eip_associate.test
        └── null_resource.test
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Prerequisite Resource Preparation

This best practice requires creating prerequisite resources such as VPC, subnet, and security group first. Please follow the following steps from the [Deploy Basic Elastic Cloud Server](https://hcbp.gitbook.io/huaweicloud-provider/best-practices/ecs/simple_instance) best practice for preparation:

- **Step 2**: Query availability zones required for ECS instance resource creation through data source
- **Step 3**: Query flavors required for ECS instance resource creation through data source
- **Step 4**: Query images required for ECS instance resource creation through data source
- **Step 5**: Create VPC resource
- **Step 6**: Create VPC subnet resource
- **Step 7**: Create security group resource

After completing the above steps, continue with the subsequent steps of this best practice.

### 3. Create Key Pair

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a key pair resource:

```hcl
variable "keypair_name" {
  description = "SSH key pair name"
  type        = string
}

variable "private_key_path" {
  description = "Private key file path"
  type        = string
}

# Create a key pair resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_kps_keypair" "test" {
  name     = var.keypair_name
  key_file = var.private_key_path
}
```

**Parameter Description**:

- **name**: Key pair name, assigned by referencing the input variable keypair\_name
- **key\_file**: Private key file path, assigned by referencing the input variable private\_key\_path

### 4. Create Security Group Rules

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create security group rule resources:

```hcl
variable "security_group_name" {
  description = "Security group name"
  type        = string
  default     = ""
}

# Create a security group rule resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_networking_secgroup_rule" "test" {
  count = var.security_group_name != "" ? 1 : 0

  security_group_id = huaweicloud_networking_secgroup.test[0].id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = "22"
  port_range_max    = "22"
  remote_ip_prefix  = "0.0.0.0/0"
}
```

**Parameter Description**:

- **count**: Resource creation count, used to control whether to create security group rule resource, only creates resource when `var.security_group_name` is not empty
- **security\_group\_id**: Security group ID, assigned by referencing the security group resource (huaweicloud\_networking\_secgroup.test\[0]) ID
- **direction**: Direction, set to "ingress" for inbound rules
- **ethertype**: Ethernet type, set to "IPv4" for IPv4 protocol
- **protocol**: Protocol, set to "tcp" for TCP protocol
- **port\_range\_min**: Port range minimum value, set to "22" for SSH port
- **port\_range\_max**: Port range maximum value, set to "22" for SSH port
- **remote\_ip\_prefix**: Remote IP prefix, set to "0.0.0.0/0" to allow all IP access

### 5. Create EIP

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an EIP resource:

```hcl
variable "associate_eip_address" {
  description = "EIP address to bind to the ECS instance"
  type        = string
  default     = ""
}

variable "eip_type" {
  description = "EIP type"
  type        = string
  default     = "5_bgp"
}

variable "bandwidth_name" {
  description = "EIP bandwidth name"
  type        = string
  default     = ""
}

variable "bandwidth_size" {
  description = "Bandwidth size"
  type        = number
  default     = 5
}

variable "bandwidth_share_type" {
  description = "Bandwidth share type"
  type        = string
  default     = "PER"
}

variable "bandwidth_charge_mode" {
  description = "Bandwidth charge mode"
  type        = string
  default     = "traffic"
}

# Create an EIP resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc_eip" "test" {
  count = var.associate_eip_address == "" ? 1 : 0

  publicip {
    type = var.eip_type
  }

  bandwidth {
    name        = var.bandwidth_name
    size        = var.bandwidth_size
    share_type  = var.bandwidth_share_type
    charge_mode = var.bandwidth_charge_mode
  }

  lifecycle {
    precondition {
      condition     = var.associate_eip_address != "" || var.bandwidth_name != ""
      error_message = "The bandwidth name must be a non-empty string if the EIP address is not provided."
    }
  }
}
```

**Parameter Description**:

- **count**: Resource creation count, used to control whether to create EIP resource, only creates resource when `var.associate_eip_address` is empty
- **publicip.type**: Public IP type, assigned by referencing the input variable eip\_type
- **bandwidth.name**: Bandwidth name, assigned by referencing the input variable bandwidth\_name
- **bandwidth.size**: Bandwidth size, assigned by referencing the input variable bandwidth\_size
- **bandwidth.share\_type**: Bandwidth share type, assigned by referencing the input variable bandwidth\_share\_type
- **bandwidth.charge\_mode**: Bandwidth charge mode, assigned by referencing the input variable bandwidth\_charge\_mode
- **lifecycle.precondition**: Lifecycle precondition, ensuring bandwidth name is not empty

### 6. Create ECS Instance

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an ECS instance resource:

```hcl
variable "instance_name" {
  description = "ECS instance name"
  type        = string
}

variable "instance_user_data" {
  description = "ECS instance user data script"
  type        = string
  default     = ""
}

variable "instance_system_disk_type" {
  description = "ECS instance system disk type"
  type        = string
  default     = "SSD"
}

variable "instance_system_disk_size" {
  description = "ECS instance system disk size (GB)"
  type        = number
  default     = 40
}

variable "security_group_ids" {
  description = "ECS instance security group ID list"
  type        = list(string)
  default     = []
  nullable    = false
}

# Create an ECS instance resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_compute_instance" "test" {
  name               = var.instance_name
  image_id           = var.instance_image_id == "" ? try(data.huaweicloud_images_images.test[0].images[0].id, null) : var.instance_image_id
  flavor_id          = var.instance_flavor_id == "" ? try(data.huaweicloud_compute_flavors.test[0].flavors[0].id, null) : var.instance_flavor_id
  availability_zone  = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test[0].names[0], null) : var.availability_zone
  key_pair           = huaweicloud_kps_keypair.test.name
  user_data          = var.instance_user_data
  system_disk_type   = var.instance_system_disk_type
  system_disk_size   = var.instance_system_disk_size
  security_group_ids = length(var.security_group_ids) == 0 ? huaweicloud_networking_secgroup.test[*].id : var.security_group_ids

  network {
    uuid = huaweicloud_vpc_subnet.test.id
  }

  lifecycle {
    precondition {
      condition     = length(var.security_group_ids) != 0 || var.security_group_name != ""
      error_message = "The security_group_ids must be a non-empty list if the security_group_name is not provided."
    }
  }
}
```

**Parameter Description**:

- **name**: Instance name, assigned by referencing the input variable instance\_name
- **image\_id**: Image ID, prioritizes using input variable, uses first result from image list query data source if empty
- **flavor\_id**: Flavor ID, prioritizes using input variable, uses first result from ECS flavor list query data source if empty
- **availability\_zone**: Availability zone, prioritizes using input variable, uses first result from availability zone list query data source if empty
- **key\_pair**: Key pair name, assigned by referencing the key pair resource (huaweicloud\_kps\_keypair.test) name
- **user\_data**: User data script, assigned by referencing the input variable instance\_user\_data
- **system\_disk\_type**: System disk type, assigned by referencing the input variable instance\_system\_disk\_type
- **system\_disk\_size**: System disk size, assigned by referencing the input variable instance\_system\_disk\_size
- **security\_group\_ids**: Security group ID list, prioritizes using input variable, uses security group resource list if empty
- **network.uuid**: Network UUID, assigned by referencing the VPC subnet resource (huaweicloud\_vpc\_subnet.test) ID
- **lifecycle.precondition**: Lifecycle precondition, ensuring security group configuration is correct

### 7. Bind EIP

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an EIP binding resource:

```hcl
# Create an EIP binding resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_compute_eip_associate" "test" {
  public_ip   = var.associate_eip_address == "" ? huaweicloud_vpc_eip.test[0].address : var.associate_eip_address
  instance_id = huaweicloud_compute_instance.test.id
}
```

**Parameter Description**:

- **public\_ip**: Public IP address, prioritizes using input variable, uses EIP resource address if empty
- **instance\_id**: Instance ID, assigned by referencing the ECS instance resource (huaweicloud\_compute\_instance.test) ID

### 8. Create Provisioner Remote Execution

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a provisioner remote execution resource:

```hcl
variable "instance_remote_exec_inline" {
  description = "Remote execution inline script"
  type        = list(string)
  nullable    = false
}

# Create a provisioner remote execution resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "null_resource" "test" {
  depends_on = [huaweicloud_compute_eip_associate.test]

  provisioner "remote-exec" {
    connection {
      user        = "root"
      private_key = file(var.private_key_path)
      host        = huaweicloud_compute_eip_associate.test.public_ip
    }

    inline = var.instance_remote_exec_inline
  }
}
```

**Parameter Description**:

- **depends\_on**: Dependency relationship, ensuring execution after EIP binding is completed
- **provisioner.remote-exec**: Remote execution provisioner
- **connection.user**: Connection user, set to "root"
- **connection.private\_key**: Private key file, assigned by referencing the input variable private\_key\_path
- **connection.host**: Connection host, using the public IP of the EIP binding resource
- **inline**: Inline script, assigned by referencing the input variable instance\_remote\_exec\_inline

### 9. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Network configuration
vpc_name    = "tf_test-vpc"
subnet_name = "tf_test-subnet"

# Security group configuration
security_group_name = "tf_test-security-group"

# Key pair configuration
keypair_name     = "tf_test-keypair"
private_key_path = "./id_rsa"

# EIP configuration
bandwidth_name = "tf_test_for_instance"

# ECS instance configuration
instance_name = "tf_test_instance_provisioner"
instance_user_data = <<EOF
#!/bin/bash
echo "Hello, World!" > /home/test.txt
EOF

# Remote execution configuration
instance_remote_exec_inline = [
  "cat /home/test.txt"
]
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="instance_name=my-instance"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 10. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating ECS instances with provisioner remote login
4. Run `terraform show` to view the created ECS instances with provisioner remote login

## Reference Information

- [Huawei Cloud ECS Product Documentation](https://support.huaweicloud.com/ecs/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For ECS Instance with Provisioner Remote Login](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/ecs/instance-provisioners)