# Deploy Stateless Workload

## Application Scenario

Cloud Container Instance (CCI) stateless workload is a container application deployment method provided by the CCI service, used to deploy and manage stateless container applications. By creating stateless workloads, you can achieve automatic scaling, rolling updates, and fault recovery for containers, improving application availability and reliability. Automating stateless workload creation through Terraform can ensure standardized and consistent container application deployment, improving operational efficiency. This best practice will introduce how to use Terraform to automatically create a CCI stateless workload, including namespace creation.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [CCI Namespace Resource (huaweicloud\_cciv2\_namespace)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cciv2_namespace)
- [CCI Stateless Workload Resource (huaweicloud\_cciv2\_deployment)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cciv2_deployment)

### Resource/Data Source Dependencies

```
huaweicloud_cciv2_namespace
    └── huaweicloud_cciv2_deployment
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create CCI Namespace Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a CCI namespace resource:

```hcl
variable "namespace_name" {
  description = "The name of CCI namespace"
  type        = string
}

# Create CCI namespace resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_cciv2_namespace" "test" {
  name = var.namespace_name
}
```

**Parameter Description**:

- **name**: The namespace name, assigned by referencing the input variable namespace\_name

### 3. Create CCI Stateless Workload Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a CCI stateless workload resource:

```hcl
variable "deployment_name" {
  description = "The name of CCI deployment"
  type        = string
}

variable "instance_type" {
  description = "The instance type of CCI pod"
  type        = string
  default     = "general-computing"
}

variable "container_name" {
  description = "The name of container"
  type        = string
  default     = "c1"
}

variable "container_image" {
  description = "The image of container"
  type        = string
  default     = "alpine:latest"
}

variable "cpu_limit" {
  description = "The CPU limit of container"
  type        = string
  default     = "1"
}

variable "memory_limit" {
  description = "The memory limit of container"
  type        = string
  default     = "2G"
}

variable "image_pull_secret_name" {
  description = "The name of image pull secret"
  type        = string
  default     = "imagepull-secret"
}

# Create CCI stateless workload resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_cciv2_deployment" "test" {
  namespace = huaweicloud_cciv2_namespace.test.name
  name      = var.deployment_name

  selector {
    match_labels = {
      app = "template1"
    }
  }

  template {
    metadata {
      labels = {
        app = "template1"
      }

      annotations = {
        "resource.cci.io/instance-type" = var.instance_type
      }
    }

    spec {
      containers {
        name  = var.container_name
        image = var.container_image

        resources {
          limits = {
            cpu    = var.cpu_limit
            memory = var.memory_limit
          }

          requests = {
            cpu    = var.cpu_limit
            memory = var.memory_limit
          }
        }
      }

      image_pull_secrets {
        name = var.image_pull_secret_name
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template.0.metadata.0.annotations,
    ]
  }
}
```

**Parameter Description**:

- **namespace**: The namespace name, referencing the name of the previously created CCI namespace resource (huaweicloud\_cciv2\_namespace.test)
- **name**: The stateless workload name, assigned by referencing the input variable deployment\_name
- **selector.match\_labels**: The selector match labels, used to match pods, set to app = "template1"
- **template.metadata.labels**: The pod template labels, must match the selector labels, set to app = "template1"
- **template.metadata.annotations**: The pod template annotations, specify the instance type through the resource.cci.io/instance-type annotation, assigned by referencing the input variable instance\_type, default value is "general-computing"
- **template.spec.containers.name**: The container name, assigned by referencing the input variable container\_name, default value is "c1"
- **template.spec.containers.image**: The container image, assigned by referencing the input variable container\_image, default value is "alpine:latest"
- **template.spec.containers.resources.limits.cpu**: The CPU limit, assigned by referencing the input variable cpu\_limit, default value is "1"
- **template.spec.containers.resources.limits.memory**: The memory limit, assigned by referencing the input variable memory\_limit, default value is "2G"
- **template.spec.containers.resources.requests.cpu**: The CPU request, assigned by referencing the input variable cpu\_limit, default value is "1"
- **template.spec.containers.resources.requests.memory**: The memory request, assigned by referencing the input variable memory\_limit, default value is "2G"
- **template.spec.image\_pull\_secrets.name**: The image pull secret name, assigned by referencing the input variable image\_pull\_secret\_name, default value is "imagepull-secret"

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# CCI Stateless Workload Configuration
deployment_name = "tf-test-deployment"
namespace_name  = "tf-test-namespace"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="deployment_name=test-deployment" -var="namespace_name=test-namespace"`
2. Environment variables: `export TF_VAR_deployment_name=test-deployment` and `export TF_VAR_namespace_name=test-namespace`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create a CCI stateless workload:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the CCI stateless workload
4. Run `terraform show` to view the details of the created CCI stateless workload

> Note: The stateless workload must be created within an existing namespace. The selector labels must match the pod template labels. If you need to use image pull secrets, please create them beforehand.

## Reference Information

- [Huawei Cloud CCI Product Documentation](https://support.huaweicloud.com/cci/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Stateless Workload](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/cci/deployment)

# Deploy Network

## Application Scenario

Cloud Container Instance (CCI) network is a network configuration function provided by the CCI service, used to provide network connectivity for container applications. By creating a CCI network, you can connect container applications to VPC networks, achieving interconnection between containers and other cloud resources. Automating CCI network creation through Terraform can ensure standardized and consistent network configuration, improving operational efficiency. This best practice will introduce how to use Terraform to automatically create a CCI network, including the creation of VPC, subnet, security group, and namespace.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [CCI Namespace Resource (huaweicloud\_cciv2\_namespace)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cciv2_namespace)
- [CCI Network Resource (huaweicloud\_cciv2\_network)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cciv2_network)

### Resource/Data Source Dependencies

```
huaweicloud_networking_secgroup
    └── huaweicloud_cciv2_network

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_cciv2_network

huaweicloud_cciv2_namespace
    └── huaweicloud_cciv2_network
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create Security Group Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a security group resource:

```hcl
variable "security_group_name" {
  description = "The name of the security group"
  type        = string
  default     = "tf-test-secgroup"
}

# Create security group resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: The security group name, assigned by referencing the input variable security\_group\_name, default value is "tf-test-secgroup"
- **delete\_default\_rules**: Whether to delete default rules, set to true

### 3. Create VPC Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC resource:

```hcl
variable "vpc_name" {
  description = "The name of the VPC"
  type        = string
  default     = "tf-test-vpc"
}

variable "vpc_cidr" {
  description = "The CIDR block of the VPC"
  type        = string
  default     = "192.168.0.0/16"
}

# Create VPC resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: The VPC name, assigned by referencing the input variable vpc\_name, default value is "tf-test-vpc"
- **cidr**: The VPC CIDR block, assigned by referencing the input variable vpc\_cidr, default value is "192.168.0.0/16"

### 4. Create VPC Subnet Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC subnet resource:

```hcl
variable "subnet_name" {
  description = "The name of the subnet"
  type        = string
  default     = "tf-test-subnet"
}

variable "subnet_cidr" {
  description = "The CIDR block of the subnet"
  type        = string
  default     = "192.168.0.0/24"
}

variable "subnet_gateway_ip" {
  description = "The gateway IP of the subnet"
  type        = string
  default     = "192.168.0.1"
}

# Create VPC subnet resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip
}
```

**Parameter Description**:

- **vpc\_id**: The ID of the VPC to which the subnet belongs, referencing the ID of the previously created VPC resource (huaweicloud\_vpc.test)
- **name**: The subnet name, assigned by referencing the input variable subnet\_name, default value is "tf-test-subnet"
- **cidr**: The subnet CIDR block, assigned by referencing the input variable subnet\_cidr, default value is "192.168.0.0/24"
- **gateway\_ip**: The subnet gateway IP, assigned by referencing the input variable subnet\_gateway\_ip, default value is "192.168.0.1"

### 5. Create CCI Namespace Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a CCI namespace resource:

```hcl
variable "namespace_name" {
  description = "The name of the CCI namespace"
  type        = string
}

# Create CCI namespace resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_cciv2_namespace" "test" {
  name = var.namespace_name
}
```

**Parameter Description**:

- **name**: The namespace name, assigned by referencing the input variable namespace\_name

### 6. Create CCI Network Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a CCI network resource:

```hcl
variable "network_name" {
  description = "The name of the CCI network"
  type        = string
}

variable "warm_pool_size" {
  description = "The size of the warm pool for the network"
  type        = string
  default     = "10"
}

variable "warm_pool_recycle_interval" {
  description = "The recycle interval of the warm pool in hours"
  type        = string
  default     = "2"
}

# Create CCI network resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_cciv2_network" "test" {
  depends_on = [huaweicloud_cciv2_namespace.test]

  namespace = huaweicloud_cciv2_namespace.test.name
  name      = var.network_name

  annotations = {
    "yangtse.io/project-id"                 = huaweicloud_cciv2_namespace.test.annotations["tenant.kubernetes.io/project-id"]
    "yangtse.io/domain-id"                  = huaweicloud_cciv2_namespace.test.annotations["tenant.kubernetes.io/domain-id"]
    "yangtse.io/warm-pool-size"             = var.warm_pool_size
    "yangtse.io/warm-pool-recycle-interval" = var.warm_pool_recycle_interval
  }

  subnets {
    subnet_id = huaweicloud_vpc_subnet.test.ipv4_subnet_id
  }

  security_group_ids = [huaweicloud_networking_secgroup.test.id]
}
```

**Parameter Description**:

- **depends\_on**: Explicit dependency relationship, ensuring the namespace resource is created before the network resource
- **namespace**: The namespace name, referencing the name of the previously created CCI namespace resource (huaweicloud\_cciv2\_namespace.test)
- **name**: The network name, assigned by referencing the input variable network\_name
- **annotations.yangtse.io/project-id**: The project ID annotation, automatically inherited from the namespace annotations
- **annotations.yangtse.io/domain-id**: The domain ID annotation, automatically inherited from the namespace annotations
- **annotations.yangtse.io/warm-pool-size**: The warm pool size annotation, assigned by referencing the input variable warm\_pool\_size, default value is "10"
- **annotations.yangtse.io/warm-pool-recycle-interval**: The warm pool recycle interval annotation (in hours), assigned by referencing the input variable warm\_pool\_recycle\_interval, default value is "2"
- **subnets.subnet\_id**: The subnet ID, referencing the IPv4 subnet ID of the previously created VPC subnet resource (huaweicloud\_vpc\_subnet.test)
- **security\_group\_ids**: The security group ID list, referencing the ID of the previously created security group resource (huaweicloud\_networking\_secgroup.test)

### 7. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# CCI Network Configuration
network_name   = "tf-test-network"
namespace_name = "tf-test-namespace"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="network_name=test-network" -var="namespace_name=test-namespace"`
2. Environment variables: `export TF_VAR_network_name=test-network` and `export TF_VAR_namespace_name=test-namespace`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 8. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create a CCI network:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the CCI network
4. Run `terraform show` to view the details of the created CCI network

> Note: The network must be associated with at least one subnet. The warm pool configuration helps reduce pod startup time by pre-allocating resources. Network names must be unique within the namespace. The annotations yangtse.io/project-id and yangtse.io/domain-id are automatically inherited from the namespace.

## Reference Information

- [Huawei Cloud CCI Product Documentation](https://support.huaweicloud.com/cci/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Network](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/cci/network)

# Deploy Service

## Application Scenario

Cloud Container Instance (CCI) service is a service discovery and load balancing function provided by the CCI service, used to provide a unified access entry for container applications. By creating a CCI service, you can expose container applications to external access, achieving service load balancing and traffic distribution. Automating CCI service creation through Terraform can ensure standardized and consistent service configuration, improving operational efficiency. This best practice will introduce how to use Terraform to automatically create a CCI service, including the creation of VPC, subnet, security group, namespace, and ELB load balancer.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zones Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)

### Resources

- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [CCI Namespace Resource (huaweicloud\_cciv2\_namespace)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cciv2_namespace)
- [ELB Load Balancer Resource (huaweicloud\_elb\_loadbalancer)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/elb_loadbalancer)
- [CCI Service Resource (huaweicloud\_cciv2\_service)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cciv2_service)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    └── huaweicloud_elb_loadbalancer

huaweicloud_networking_secgroup
    └── huaweicloud_cciv2_service

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        ├── huaweicloud_elb_loadbalancer
        └── huaweicloud_cciv2_service

huaweicloud_cciv2_namespace
    ├── huaweicloud_elb_loadbalancer
    └── huaweicloud_cciv2_service

huaweicloud_elb_loadbalancer
    └── huaweicloud_cciv2_service
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Availability Zone Information Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the query results of which are used to create an ELB load balancer:

```hcl
# Get all availability zone information in the specified region (defaults to the region specified in the provider block when region parameter is omitted), used to create ELB load balancer
data "huaweicloud_availability_zones" "test" {}
```

**Parameter Description**: This data source does not require additional parameters and queries all available availability zone information in the current region by default.

### 3. Create Security Group Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a security group resource:

```hcl
variable "security_group_name" {
  description = "The name of security group"
  type        = string
  default     = "tf-test-secgroup"
}

# Create security group resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: The security group name, assigned by referencing the input variable security\_group\_name, default value is "tf-test-secgroup"
- **delete\_default\_rules**: Whether to delete default rules, set to true

### 4. Create VPC Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC resource:

```hcl
variable "vpc_name" {
  description = "The name of VPC"
  type        = string
  default     = "tf-test-vpc"
}

variable "vpc_cidr" {
  description = "The CIDR block of VPC"
  type        = string
  default     = "192.168.0.0/16"
}

# Create VPC resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: The VPC name, assigned by referencing the input variable vpc\_name, default value is "tf-test-vpc"
- **cidr**: The VPC CIDR block, assigned by referencing the input variable vpc\_cidr, default value is "192.168.0.0/16"

### 5. Create VPC Subnet Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC subnet resource:

```hcl
variable "subnet_name" {
  description = "The name of subnet"
  type        = string
  default     = "tf-test-subnet"
}

variable "subnet_cidr" {
  description = "The CIDR block of subnet"
  type        = string
  default     = "192.168.0.0/24"
}

variable "subnet_gateway_ip" {
  description = "The gateway IP of subnet"
  type        = string
  default     = "192.168.0.1"
}

# Create VPC subnet resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip
}
```

**Parameter Description**:

- **vpc\_id**: The ID of the VPC to which the subnet belongs, referencing the ID of the previously created VPC resource (huaweicloud\_vpc.test)
- **name**: The subnet name, assigned by referencing the input variable subnet\_name, default value is "tf-test-subnet"
- **cidr**: The subnet CIDR block, assigned by referencing the input variable subnet\_cidr, default value is "192.168.0.0/24"
- **gateway\_ip**: The subnet gateway IP, assigned by referencing the input variable subnet\_gateway\_ip, default value is "192.168.0.1"

### 6. Create CCI Namespace Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a CCI namespace resource:

```hcl
variable "namespace_name" {
  description = "The name of CCI namespace"
  type        = string
}

# Create CCI namespace resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_cciv2_namespace" "test" {
  name = var.namespace_name
}
```

**Parameter Description**:

- **name**: The namespace name, assigned by referencing the input variable namespace\_name

### 7. Create ELB Load Balancer Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an ELB load balancer resource:

```hcl
variable "elb_name" {
  description = "The name of ELB load balancer"
  type        = string
}

# Create ELB load balancer resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_elb_loadbalancer" "test" {
  depends_on = [huaweicloud_cciv2_namespace.test]

  name              = var.elb_name
  cross_vpc_backend = true
  vpc_id            = huaweicloud_vpc.test.id
  ipv4_subnet_id    = huaweicloud_vpc_subnet.test.ipv4_subnet_id

  availability_zone = [
    try(data.huaweicloud_availability_zones.test.names[1], "")
  ]
}
```

**Parameter Description**:

- **depends\_on**: Explicit dependency relationship, ensuring the namespace resource is created before the ELB load balancer resource
- **name**: The load balancer name, assigned by referencing the input variable elb\_name
- **cross\_vpc\_backend**: Whether to support cross-VPC backend, set to true
- **vpc\_id**: The VPC ID, referencing the ID of the previously created VPC resource (huaweicloud\_vpc.test)
- **ipv4\_subnet\_id**: The IPv4 subnet ID, referencing the IPv4 subnet ID of the previously created VPC subnet resource (huaweicloud\_vpc\_subnet.test)
- **availability\_zone**: The availability zone list, assigned based on the query results of the availability zone list data source (data.huaweicloud\_availability\_zones), using the second availability zone

### 8. Create CCI Service Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a CCI service resource:

```hcl
variable "service_name" {
  description = "The name of CCI service"
  type        = string
}

variable "selector_app" {
  description = "The app label of selector"
  type        = string
  default     = "test1"
}

variable "service_type" {
  description = "The type of service"
  type        = string
  default     = "LoadBalancer"
}

# Create CCI service resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_cciv2_service" "test" {
  depends_on = [huaweicloud_elb_loadbalancer.test]

  namespace = huaweicloud_cciv2_namespace.test.name
  name      = var.service_name

  annotations = {
    "kubernetes.io/elb.class" = "elb"
    "kubernetes.io/elb.id"    = huaweicloud_elb_loadbalancer.test.id
  }

  ports {
    name         = "test"
    app_protocol = "TCP"
    protocol     = "TCP"
    port         = 87
    target_port  = 65529
  }

  selector = {
    app = var.selector_app
  }

  type = var.service_type

  lifecycle {
    ignore_changes = [
      annotations,
    ]
  }
}
```

**Parameter Description**:

- **depends\_on**: Explicit dependency relationship, ensuring the ELB load balancer resource is created before the CCI service resource
- **namespace**: The namespace name, referencing the name of the previously created CCI namespace resource (huaweicloud\_cciv2\_namespace.test)
- **name**: The service name, assigned by referencing the input variable service\_name
- **annotations.kubernetes.io/elb.class**: The ELB type annotation, set to "elb"
- **annotations.kubernetes.io/elb.id**: The ELB ID annotation, referencing the ID of the previously created ELB load balancer resource (huaweicloud\_elb\_loadbalancer.test)
- **ports.name**: The port name, set to "test"
- **ports.app\_protocol**: The application protocol, set to "TCP"
- **ports.protocol**: The protocol type, set to "TCP"
- **ports.port**: The service port, set to 87
- **ports.target\_port**: The target port, set to 65529
- **selector.app**: The selector application label, assigned by referencing the input variable selector\_app, default value is "test1"
- **type**: The service type, assigned by referencing the input variable service\_type, default value is "LoadBalancer"

### 9. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# CCI Service Configuration
elb_name       = "tf-test-elb"
service_name   = "tf-test-service"
namespace_name = "tf-test-namespace"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="service_name=test-service" -var="namespace_name=test-namespace"`
2. Environment variables: `export TF_VAR_service_name=test-service` and `export TF_VAR_namespace_name=test-namespace`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 10. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create a CCI service:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the CCI service
4. Run `terraform show` to view the details of the created CCI service

> Note: The service must be created in an existing namespace. The selector label must match the Pod label. The ELB load balancer must be created in advance.

## Reference Information

- [Huawei Cloud CCI Product Documentation](https://support.huaweicloud.com/cci/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Service](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/cci/service)
