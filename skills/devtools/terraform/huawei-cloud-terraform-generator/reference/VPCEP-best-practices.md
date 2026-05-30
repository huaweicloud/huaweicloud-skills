# Deploy Approval

## Application Scenario

VPC Endpoint (VPCEP) is a VPC internal resource mutual access service provided by Huawei Cloud, supporting the creation of endpoints and endpoint services within VPCs to achieve private network access to VPC resources. Endpoint approval is an important function of VPCEP service, used to approve requests for endpoints to connect to endpoint services. When an endpoint attempts to connect to an endpoint service that requires approval, the service provider needs to approve the connection request to ensure that only authorized endpoints can access service resources. Through endpoint approval, access control and permission management can be achieved, improving the security of service resources. This best practice introduces how to use Terraform to automatically deploy endpoint approvals, including availability zone query, ECS flavor query, image query, VPC, subnet, security group, ECS instance, endpoint service, endpoint, and endpoint approval creation.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [ECS Flavors Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)
- [Image Query Data Source (data.huaweicloud\_images\_image)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_image)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [ECS Instance Resource (huaweicloud\_compute\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_instance)
- [Endpoint Service Resource (huaweicloud\_vpcep\_service)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpcep_service)
- [Endpoint Resource (huaweicloud\_vpcep\_endpoint)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpcep_endpoint)
- [Endpoint Approval Resource (huaweicloud\_vpcep\_approval)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpcep_approval)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── data.huaweicloud_compute_flavors
        └── huaweicloud_compute_instance
            └── huaweicloud_vpcep_service
                └── huaweicloud_vpcep_endpoint
                    └── huaweicloud_vpcep_approval

data.huaweicloud_images_image
    └── huaweicloud_compute_instance
        └── huaweicloud_vpcep_service
            └── huaweicloud_vpcep_endpoint
                └── huaweicloud_vpcep_approval

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_compute_instance
            └── huaweicloud_vpcep_service
                └── huaweicloud_vpcep_endpoint
                    └── huaweicloud_vpcep_approval

huaweicloud_networking_secgroup
    └── huaweicloud_compute_instance
        └── huaweicloud_vpcep_service
            └── huaweicloud_vpcep_endpoint
                └── huaweicloud_vpcep_approval
```

> Note: Endpoint approval depends on endpoint and endpoint service. Endpoint depends on endpoint service, endpoint service depends on ECS instance, and ECS instance depends on VPC, subnet, security group, availability zone, flavor, and image resources. Endpoint approval is used to approve requests for endpoints to connect to endpoint services.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Query Availability Zones

Add the following script to the TF file (such as main.tf) to query availability zones:

```hcl
# Query availability zones data source
data "huaweicloud_availability_zones" "test" {}
```

### 3. Query ECS Flavors

Add the following script to the TF file (such as main.tf) to query ECS flavors:

```hcl
# Query ECS flavors data source
data "huaweicloud_compute_flavors" "test" {
  availability_zone = try(data.huaweicloud_availability_zones.test.names[0], null)
  performance_type  = var.instance_flavor_performance_type
  cpu_core_count    = var.instance_flavor_cpu_core_count
  memory_size       = var.instance_flavor_memory_size
}
```

**Parameter Description**:

- **availability\_zone**: Availability zone name, assigned by referencing the availability zone query data source results
- **performance\_type**: Flavor performance type, assigned by referencing the input variable `instance_flavor_performance_type`
- **cpu\_core\_count**: CPU core count, assigned by referencing the input variable `instance_flavor_cpu_core_count`
- **memory\_size**: Memory size, assigned by referencing the input variable `instance_flavor_memory_size`

### 4. Query Image

Add the following script to the TF file (such as main.tf) to query image:

```hcl
# Query image data source
data "huaweicloud_images_image" "test" {
  name        = var.instance_image_name
  most_recent = var.instance_image_most_recent
}
```

**Parameter Description**:

- **name**: Image name, assigned by referencing the input variable `instance_image_name`
- **most\_recent**: Whether to use the most recent image, assigned by referencing the input variable `instance_image_most_recent`

### 5. Create VPC and Subnet

Add the following script to the TF file (such as main.tf) to create VPC and subnet:

```hcl
# Create VPC resource
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}

# Create VPC subnet resource
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
}
```

**Parameter Description**:

- **name**: VPC name, assigned by referencing the input variable `vpc_name`
- **cidr**: VPC CIDR block, assigned by referencing the input variable `vpc_cidr`
- **vpc\_id**: VPC ID to which the subnet belongs, assigned by referencing the VPC resource ID
- **cidr**: Subnet CIDR block, automatically calculated if the input variable is empty, otherwise uses the input variable value
- **gateway\_ip**: Subnet gateway IP address, automatically calculated if the input variable is empty, otherwise uses the input variable value

### 6. Create Security Group

Add the following script to the TF file (such as main.tf) to create security group:

```hcl
# Create security group resource
resource "huaweicloud_networking_secgroup" "test" {
  name = var.security_group_name
}
```

**Parameter Description**:

- **name**: Security group name, assigned by referencing the input variable `security_group_name`

### 7. Create ECS Instance

Add the following script to the TF file (such as main.tf) to create ECS instance:

```hcl
# Create ECS instance resource
resource "huaweicloud_compute_instance" "test" {
  name               = var.instance_name
  image_id           = data.huaweicloud_images_image.test.id
  flavor_id          = var.instance_flavor_id == "" ? try(data.huaweicloud_compute_flavors.test.ids[0], "") : var.instance_flavor_id
  security_group_ids = [huaweicloud_networking_secgroup.test.id]
  availability_zone  = try(data.huaweicloud_availability_zones.test.names[0], null)

  network {
    uuid = huaweicloud_vpc_subnet.test.id
  }
}
```

**Parameter Description**:

- **name**: ECS instance name, assigned by referencing the input variable `instance_name`
- **image\_id**: Image ID, assigned by referencing the image query data source ID
- **flavor\_id**: Flavor ID, uses the flavor query data source result if the input variable is empty, otherwise uses the input variable value
- **security\_group\_ids**: Security group ID list, assigned by referencing the security group resource ID
- **availability\_zone**: Availability zone name, assigned by referencing the availability zone query data source results
- **network**: Network configuration, assigned by referencing the subnet resource ID

### 8. Create Endpoint Service

Add the following script to the TF file (such as main.tf) to create endpoint service:

```hcl
# Create endpoint service resource
resource "huaweicloud_vpcep_service" "test" {
  name        = var.endpoint_service_name
  server_type = var.endpoint_service_type
  vpc_id      = huaweicloud_vpc.test.id
  port_id     = huaweicloud_compute_instance.test.network[0].port

  dynamic "port_mapping" {
    for_each = var.endpoint_service_port_mapping

    content {
      service_port  = port_mapping.value.service_port
      terminal_port = port_mapping.value.terminal_port
    }
  }
}
```

**Parameter Description**:

- **name**: Endpoint service name, assigned by referencing the input variable `endpoint_service_name`
- **server\_type**: Server type, assigned by referencing the input variable `endpoint_service_type`
- **vpc\_id**: VPC ID to which the endpoint service belongs, assigned by referencing the VPC resource ID
- **port\_id**: Port ID, assigned by referencing the network port ID of the ECS instance
- **port\_mapping**: Port mapping list, creates port mappings through dynamic block `dynamic "port_mapping"` based on input variable `endpoint_service_port_mapping`
  - **service\_port**: Service port, assigned by referencing the `service_port` in the input variable
  - **terminal\_port**: Terminal port, assigned by referencing the `terminal_port` in the input variable

### 9. Create Endpoint

Add the following script to the TF file (such as main.tf) to create endpoint:

```hcl
# Create endpoint resource
resource "huaweicloud_vpcep_endpoint" "test" {
  service_id = huaweicloud_vpcep_service.test.id
  vpc_id     = huaweicloud_vpc.test.id
  network_id = huaweicloud_vpc_subnet.test.id
}
```

**Parameter Description**:

- **service\_id**: Endpoint service ID, assigned by referencing the endpoint service resource ID
- **vpc\_id**: VPC ID to which the endpoint belongs, assigned by referencing the VPC resource ID
- **network\_id**: Subnet ID to which the endpoint belongs, assigned by referencing the subnet resource ID

### 10. Create Endpoint Approval

Add the following script to the TF file (such as main.tf) to create endpoint approval:

```hcl
# Create endpoint approval resource
resource "huaweicloud_vpcep_approval" "test" {
  service_id = huaweicloud_vpcep_service.test.id
  endpoints  = [huaweicloud_vpcep_endpoint.test.id]
}
```

**Parameter Description**:

- **service\_id**: Endpoint service ID, assigned by referencing the endpoint service resource ID
- **endpoints**: Endpoint ID list, assigned by referencing the endpoint resource ID, used to specify endpoints that need approval

> Note: Endpoint approval is used to approve requests for endpoints to connect to endpoint services. When an endpoint attempts to connect to an endpoint service that requires approval, the service provider needs to approve the connection request through approval operations to allow or reject the connection request, ensuring that only authorized endpoints can access service resources.

### 11. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# VPC and subnet configuration (Required)
vpc_name   = "tf_test_vpc"
vpc_cidr   = "192.168.0.0/16"
subnet_name = "tf_test_subnet"

# Security group configuration (Required)
security_group_name = "tf_test_security_group"

# ECS instance configuration (Required)
instance_name = "tf_test_instance"

# Endpoint service configuration (Required)
endpoint_service_name = "tf-test-service"
endpoint_service_port_mapping = [
  {
    service_port  = 8080
    terminal_port = 80
  }
]
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="vpc_name=tf_test_vpc"`
2. Environment variables: `export TF_VAR_vpc_name=tf_test_vpc`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 12. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating endpoint approval and related resources
4. Run `terraform show` to view the created endpoint approval

## Reference Information

- [Huawei Cloud VPCEP Product Documentation](https://support.huaweicloud.com/intl/en-us/vpcep/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Endpoint Approval](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/vpcep/approval)

# Deploy Endpoint

## Application Scenario

VPC Endpoint (VPCEP) is a VPC internal resource mutual access service provided by Huawei Cloud, supporting the creation of endpoints and endpoint services within VPCs to achieve private network access to VPC resources. Endpoint is a core function of VPCEP service, used to create endpoints within VPCs, connecting to endpoint services, achieving cross-VPC private network access. Through endpoints, endpoint services published in other VPCs can be accessed, achieving secure private network communication, avoiding public network access, improving access security and stability. This best practice introduces how to use Terraform to automatically deploy endpoints, including availability zone query, ECS flavor query, image query, VPC, subnet, security group, ECS instance, endpoint service, and endpoint creation.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [ECS Flavors Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)
- [Image Query Data Source (data.huaweicloud\_images\_image)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_image)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [ECS Instance Resource (huaweicloud\_compute\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_instance)
- [Endpoint Service Resource (huaweicloud\_vpcep\_service)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpcep_service)
- [Endpoint Resource (huaweicloud\_vpcep\_endpoint)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpcep_endpoint)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── data.huaweicloud_compute_flavors
        └── huaweicloud_compute_instance
            └── huaweicloud_vpcep_service
                └── huaweicloud_vpcep_endpoint

data.huaweicloud_images_image
    └── huaweicloud_compute_instance
        └── huaweicloud_vpcep_service
            └── huaweicloud_vpcep_endpoint

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_compute_instance
            └── huaweicloud_vpcep_service
                └── huaweicloud_vpcep_endpoint

huaweicloud_networking_secgroup
    └── huaweicloud_compute_instance
        └── huaweicloud_vpcep_service
            └── huaweicloud_vpcep_endpoint
```

> Note: Endpoint depends on endpoint service, endpoint service depends on ECS instance, and ECS instance depends on VPC, subnet, security group, availability zone, flavor, and image resources. Endpoint connects to endpoint service through association, achieving cross-VPC private network access.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Query Availability Zones

Add the following script to the TF file (such as main.tf) to query availability zones:

```hcl
# Query availability zones data source
data "huaweicloud_availability_zones" "test" {}
```

### 3. Query ECS Flavors

Add the following script to the TF file (such as main.tf) to query ECS flavors:

```hcl
# Query ECS flavors data source
data "huaweicloud_compute_flavors" "test" {
  availability_zone = try(data.huaweicloud_availability_zones.test.names[0], null)
  performance_type  = var.instance_flavor_performance_type
  cpu_core_count    = var.instance_flavor_cpu_core_count
  memory_size       = var.instance_flavor_memory_size
}
```

**Parameter Description**:

- **availability\_zone**: Availability zone name, assigned by referencing the availability zone query data source results
- **performance\_type**: Flavor performance type, assigned by referencing the input variable `instance_flavor_performance_type`
- **cpu\_core\_count**: CPU core count, assigned by referencing the input variable `instance_flavor_cpu_core_count`
- **memory\_size**: Memory size, assigned by referencing the input variable `instance_flavor_memory_size`

### 4. Query Image

Add the following script to the TF file (such as main.tf) to query image:

```hcl
# Query image data source
data "huaweicloud_images_image" "test" {
  name        = var.instance_image_name
  most_recent = var.instance_image_most_recent
}
```

**Parameter Description**:

- **name**: Image name, assigned by referencing the input variable `instance_image_name`
- **most\_recent**: Whether to use the most recent image, assigned by referencing the input variable `instance_image_most_recent`

### 5. Create VPC and Subnet

Add the following script to the TF file (such as main.tf) to create VPC and subnet:

```hcl
# Create VPC resource
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}

# Create VPC subnet resource
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
}
```

**Parameter Description**:

- **name**: VPC name, assigned by referencing the input variable `vpc_name`
- **cidr**: VPC CIDR block, assigned by referencing the input variable `vpc_cidr`
- **vpc\_id**: VPC ID to which the subnet belongs, assigned by referencing the VPC resource ID
- **cidr**: Subnet CIDR block, automatically calculated if the input variable is empty, otherwise uses the input variable value
- **gateway\_ip**: Subnet gateway IP address, automatically calculated if the input variable is empty, otherwise uses the input variable value

### 6. Create Security Group

Add the following script to the TF file (such as main.tf) to create security group:

```hcl
# Create security group resource
resource "huaweicloud_networking_secgroup" "test" {
  name = var.security_group_name
}
```

**Parameter Description**:

- **name**: Security group name, assigned by referencing the input variable `security_group_name`

### 7. Create ECS Instance

Add the following script to the TF file (such as main.tf) to create ECS instance:

```hcl
# Create ECS instance resource
resource "huaweicloud_compute_instance" "test" {
  name               = var.instance_name
  image_id           = data.huaweicloud_images_image.test.id
  flavor_id          = var.instance_flavor_id == "" ? try(data.huaweicloud_compute_flavors.test.ids[0], "") : var.instance_flavor_id
  security_group_ids = [huaweicloud_networking_secgroup.test.id]
  availability_zone  = try(data.huaweicloud_availability_zones.test.names[0], null)

  network {
    uuid = huaweicloud_vpc_subnet.test.id
  }
}
```

**Parameter Description**:

- **name**: ECS instance name, assigned by referencing the input variable `instance_name`
- **image\_id**: Image ID, assigned by referencing the image query data source ID
- **flavor\_id**: Flavor ID, uses the flavor query data source result if the input variable is empty, otherwise uses the input variable value
- **security\_group\_ids**: Security group ID list, assigned by referencing the security group resource ID
- **availability\_zone**: Availability zone name, assigned by referencing the availability zone query data source results
- **network**: Network configuration, assigned by referencing the subnet resource ID

### 8. Create Endpoint Service

Add the following script to the TF file (such as main.tf) to create endpoint service:

```hcl
# Create endpoint service resource
resource "huaweicloud_vpcep_service" "test" {
  name        = var.endpoint_service_name
  server_type = var.endpoint_service_type
  vpc_id      = huaweicloud_vpc.test.id
  port_id     = huaweicloud_compute_instance.test.network[0].port

  dynamic "port_mapping" {
    for_each = var.endpoint_service_port_mapping

    content {
      service_port  = port_mapping.value.service_port
      terminal_port = port_mapping.value.terminal_port
    }
  }
}
```

**Parameter Description**:

- **name**: Endpoint service name, assigned by referencing the input variable `endpoint_service_name`
- **server\_type**: Server type, assigned by referencing the input variable `endpoint_service_type`
- **vpc\_id**: VPC ID to which the endpoint service belongs, assigned by referencing the VPC resource ID
- **port\_id**: Port ID, assigned by referencing the network port ID of the ECS instance
- **port\_mapping**: Port mapping list, creates port mappings through dynamic block `dynamic "port_mapping"` based on input variable `endpoint_service_port_mapping`
  - **service\_port**: Service port, assigned by referencing the `service_port` in the input variable
  - **terminal\_port**: Terminal port, assigned by referencing the `terminal_port` in the input variable

### 9. Create Endpoint

Add the following script to the TF file (such as main.tf) to create endpoint:

```hcl
# Create endpoint resource
resource "huaweicloud_vpcep_endpoint" "test" {
  service_id = huaweicloud_vpcep_service.test.id
  vpc_id     = huaweicloud_vpc.test.id
  network_id = huaweicloud_vpc_subnet.test.id
}
```

**Parameter Description**:

- **service\_id**: Endpoint service ID, assigned by referencing the endpoint service resource ID
- **vpc\_id**: VPC ID to which the endpoint belongs, assigned by referencing the VPC resource ID
- **network\_id**: Subnet ID to which the endpoint belongs, assigned by referencing the subnet resource ID

> Note: Endpoint is used to connect to endpoint service, achieving cross-VPC private network access. After creating an endpoint, service resources provided by the endpoint service can be accessed through the endpoint.

### 10. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# VPC and subnet configuration (Required)
vpc_name   = "tf_test_vpc"
vpc_cidr   = "192.168.0.0/16"
subnet_name = "tf_test_subnet"

# Security group configuration (Required)
security_group_name = "tf_test_security_group"

# ECS instance configuration (Required)
instance_name = "tf_test_instance"

# Endpoint service configuration (Required)
endpoint_service_name = "tf-test-service"
endpoint_service_port_mapping = [
  {
    service_port  = 8080
    terminal_port = 80
  }
]
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="vpc_name=tf_test_vpc"`
2. Environment variables: `export TF_VAR_vpc_name=tf_test_vpc`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 11. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating endpoint and related resources
4. Run `terraform show` to view the created endpoint

## Reference Information

- [Huawei Cloud VPCEP Product Documentation](https://support.huaweicloud.com/intl/en-us/vpcep/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Endpoint](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/vpcep/endpoint)

# Deploy Service

## Application Scenario

VPC Endpoint (VPCEP) is a VPC internal resource mutual access service provided by Huawei Cloud, supporting the creation of endpoints and endpoint services within VPCs to achieve private network access to VPC resources. Endpoint service is a core function of VPCEP service, used to publish service resources within VPCs (such as ECS, ELB, etc.) as endpoint services for other VPCs to access through endpoints. Through endpoint services, cross-VPC private network access can be achieved, avoiding public network access, improving access security and stability. This best practice introduces how to use Terraform to automatically deploy endpoint services, including availability zone query, ECS flavor query, image query, VPC, subnet, security group, ECS instance, and endpoint service creation.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [ECS Flavors Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)
- [Image Query Data Source (data.huaweicloud\_images\_image)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/images_image)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [ECS Instance Resource (huaweicloud\_compute\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/compute_instance)
- [Endpoint Service Resource (huaweicloud\_vpcep\_service)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpcep_service)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── data.huaweicloud_compute_flavors
        └── huaweicloud_compute_instance
            └── huaweicloud_vpcep_service

data.huaweicloud_images_image
    └── huaweicloud_compute_instance
        └── huaweicloud_vpcep_service

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_compute_instance
            └── huaweicloud_vpcep_service

huaweicloud_networking_secgroup
    └── huaweicloud_compute_instance
        └── huaweicloud_vpcep_service
```

> Note: Endpoint service depends on ECS instance, and ECS instance depends on VPC, subnet, security group, availability zone, flavor, and image resources. Endpoint service is associated through the network port ID of the ECS instance.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Query Availability Zones

Add the following script to the TF file (such as main.tf) to query availability zones:

```hcl
# Query availability zones data source
data "huaweicloud_availability_zones" "test" {}
```

### 3. Query ECS Flavors

Add the following script to the TF file (such as main.tf) to query ECS flavors:

```hcl
# Query ECS flavors data source
data "huaweicloud_compute_flavors" "test" {
  availability_zone = try(data.huaweicloud_availability_zones.test.names[0], null)
  performance_type  = var.instance_flavor_performance_type
  cpu_core_count    = var.instance_flavor_cpu_core_count
  memory_size       = var.instance_flavor_memory_size
}
```

**Parameter Description**:

- **availability\_zone**: Availability zone name, assigned by referencing the availability zone query data source results
- **performance\_type**: Flavor performance type, assigned by referencing the input variable `instance_flavor_performance_type`
- **cpu\_core\_count**: CPU core count, assigned by referencing the input variable `instance_flavor_cpu_core_count`
- **memory\_size**: Memory size, assigned by referencing the input variable `instance_flavor_memory_size`

### 4. Query Image

Add the following script to the TF file (such as main.tf) to query image:

```hcl
# Query image data source
data "huaweicloud_images_image" "test" {
  name        = var.instance_image_name
  most_recent = var.instance_image_most_recent
}
```

**Parameter Description**:

- **name**: Image name, assigned by referencing the input variable `instance_image_name`
- **most\_recent**: Whether to use the most recent image, assigned by referencing the input variable `instance_image_most_recent`

### 5. Create VPC and Subnet

Add the following script to the TF file (such as main.tf) to create VPC and subnet:

```hcl
# Create VPC resource
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}

# Create VPC subnet resource
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
}
```

**Parameter Description**:

- **name**: VPC name, assigned by referencing the input variable `vpc_name`
- **cidr**: VPC CIDR block, assigned by referencing the input variable `vpc_cidr`
- **vpc\_id**: VPC ID to which the subnet belongs, assigned by referencing the VPC resource ID
- **cidr**: Subnet CIDR block, automatically calculated if the input variable is empty, otherwise uses the input variable value
- **gateway\_ip**: Subnet gateway IP address, automatically calculated if the input variable is empty, otherwise uses the input variable value

### 6. Create Security Group

Add the following script to the TF file (such as main.tf) to create security group:

```hcl
# Create security group resource
resource "huaweicloud_networking_secgroup" "test" {
  name = var.security_group_name
}
```

**Parameter Description**:

- **name**: Security group name, assigned by referencing the input variable `security_group_name`

### 7. Create ECS Instance

Add the following script to the TF file (such as main.tf) to create ECS instance:

```hcl
# Create ECS instance resource
resource "huaweicloud_compute_instance" "test" {
  name               = var.instance_name
  image_id           = data.huaweicloud_images_image.test.id
  flavor_id          = var.instance_flavor_id == "" ? try(data.huaweicloud_compute_flavors.test.ids[0], "") : var.instance_flavor_id
  security_group_ids = [huaweicloud_networking_secgroup.test.id]
  availability_zone  = try(data.huaweicloud_availability_zones.test.names[0], null)

  network {
    uuid = huaweicloud_vpc_subnet.test.id
  }
}
```

**Parameter Description**:

- **name**: ECS instance name, assigned by referencing the input variable `instance_name`
- **image\_id**: Image ID, assigned by referencing the image query data source ID
- **flavor\_id**: Flavor ID, uses the flavor query data source result if the input variable is empty, otherwise uses the input variable value
- **security\_group\_ids**: Security group ID list, assigned by referencing the security group resource ID
- **availability\_zone**: Availability zone name, assigned by referencing the availability zone query data source results
- **network**: Network configuration, assigned by referencing the subnet resource ID

### 8. Create Endpoint Service

Add the following script to the TF file (such as main.tf) to create endpoint service:

```hcl
# Create endpoint service resource
resource "huaweicloud_vpcep_service" "test" {
  name        = var.endpoint_service_name
  server_type = var.endpoint_service_type
  vpc_id      = huaweicloud_vpc.test.id
  port_id     = huaweicloud_compute_instance.test.network[0].port

  dynamic "port_mapping" {
    for_each = var.endpoint_service_port_mapping

    content {
      service_port  = port_mapping.value.service_port
      terminal_port = port_mapping.value.terminal_port
    }
  }
}
```

**Parameter Description**:

- **name**: Endpoint service name, assigned by referencing the input variable `endpoint_service_name`
- **server\_type**: Server type, assigned by referencing the input variable `endpoint_service_type`
- **vpc\_id**: VPC ID to which the endpoint service belongs, assigned by referencing the VPC resource ID
- **port\_id**: Port ID, assigned by referencing the network port ID of the ECS instance
- **port\_mapping**: Port mapping list, creates port mappings through dynamic block `dynamic "port_mapping"` based on input variable `endpoint_service_port_mapping`
  - **service\_port**: Service port, assigned by referencing the `service_port` in the input variable
  - **terminal\_port**: Terminal port, assigned by referencing the `terminal_port` in the input variable

> Note: Endpoint service needs to be associated with the network port of the ECS instance. Port mapping is used to configure the correspondence between service ports and terminal ports, achieving port forwarding functionality.

### 9. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# VPC and subnet configuration (Required)
vpc_name   = "tf_test_vpc"
vpc_cidr   = "192.168.0.0/16"
subnet_name = "tf_test_subnet"

# Security group configuration (Required)
security_group_name = "tf_test_security_group"

# ECS instance configuration (Required)
instance_name = "tf_test_instance"

# Endpoint service configuration (Required)
endpoint_service_name = "tf-test-service"
endpoint_service_port_mapping = [
  {
    service_port  = 8080
    terminal_port = 80
  }
]
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="vpc_name=tf_test_vpc"`
2. Environment variables: `export TF_VAR_vpc_name=tf_test_vpc`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 10. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating endpoint service and related resources
4. Run `terraform show` to view the created endpoint service

## Reference Information

- [Huawei Cloud VPCEP Product Documentation](https://support.huaweicloud.com/intl/en-us/vpcep/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Endpoint Service](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/vpcep/service)
