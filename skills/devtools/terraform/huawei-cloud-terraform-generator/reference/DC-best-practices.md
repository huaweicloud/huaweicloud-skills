# Deploy Connect Gateway

## Application Scenario

Direct Connect (DC) is a high-performance, low-latency, secure, and reliable dedicated line access service provided by Huawei Cloud, offering enterprises dedicated network connections from local data centers to Huawei Cloud. Direct Connect service supports multiple access methods, including physical dedicated lines and virtual dedicated lines, meeting network connection requirements for different scales and scenarios.

Connect gateway is a core component in Direct Connect service, used to establish network connections between local data centers and Huawei Cloud. Through connect gateways, you can achieve cross-region, cross-network dedicated line connections, supporting both IPv4 and IPv6 address families, meeting the needs of different network environments. This best practice will introduce how to use Terraform to automatically deploy DC connect gateways, including gateway creation and configuration.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

None

### Resources

- [DC Connect Gateway Resource (huaweicloud\_dc\_connect\_gateway)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dc_connect_gateway)

### Resource/Data Source Dependencies

```
huaweicloud_dc_connect_gateway.test
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create DC Connect Gateway

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a DC connect gateway resource:

```hcl
variable "connect_gateway_name" {
  description = "Connect gateway name"
  type        = string
}

variable "connect_gateway_description" {
  description = "Connect gateway description"
  type        = string
  default     = "Created by Terraform"
}

variable "address_family" {
  description = "Connect gateway address family type"
  type        = string
  default     = "ipv4"
}

# Create a DC connect gateway resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_dc_connect_gateway" "test" {
  name           = var.connect_gateway_name
  description    = var.connect_gateway_description
  address_family = var.address_family
}
```

**Parameter Description**:

- **name**: Connect gateway name, assigned by referencing the input variable connect\_gateway\_name
- **description**: Connect gateway description, assigned by referencing the input variable connect\_gateway\_description
- **address\_family**: Address family type, assigned by referencing the input variable address\_family, supports "ipv4" and "ipv6"

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Connect gateway configuration
connect_gateway_name        = "tf_test_connect_gateway"
connect_gateway_description = "Created by Terraform"
address_family              = "ipv4"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="connect_gateway_name=my-gateway" -var="address_family=ipv4"`
2. Environment variables: `export TF_VAR_connect_gateway_name=my-gateway`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating the DC connect gateway
4. Run `terraform show` to view the details of the created DC connect gateway

## Reference Information

- [Huawei Cloud DC Product Documentation](https://support.huaweicloud.com/dc/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For DC Connect Gateway](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dc/connect-gateway)

# Deploy Global Gateway

## Application Scenario

Direct Connect (DC) is a high-performance, low-latency, secure, and reliable dedicated line access service provided by Huawei Cloud, offering enterprises dedicated network connections from local data centers to Huawei Cloud. Direct Connect service supports multiple access methods, including physical dedicated lines and virtual dedicated lines, meeting network connection requirements for different scales and scenarios.

Global gateway is an advanced component in Direct Connect service, used to establish cross-region, cross-network global dedicated line connections. Through global gateways, you can achieve unified access management for multiple regions and networks, supporting BGP routing protocol, meeting the needs of large enterprises and complex network environments. This best practice will introduce how to use Terraform to automatically deploy DC global gateways, including gateway creation, BGP configuration, and tag management.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

None

### Resources

- [DC Global Gateway Resource (huaweicloud\_dc\_global\_gateway)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dc_global_gateway)

### Resource/Data Source Dependencies

```
huaweicloud_dc_global_gateway.test
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create DC Global Gateway

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a DC global gateway resource:

```hcl
variable "global_gateway_name" {
  description = "Global gateway name"
  type        = string
}

variable "global_gateway_description" {
  description = "Global gateway description"
  type        = string
  default     = "Created by Terraform"
}

variable "address_family" {
  description = "Global gateway IP address family"
  type        = string
  default     = "ipv4"
}

variable "bgp_asn" {
  description = "Global gateway BGP ASN"
  type        = number
}

variable "enterprise_project_id" {
  description = "Enterprise project ID to which the global gateway belongs"
  type        = string
  default     = "0"
}

variable "global_gateway_tags" {
  description = "Global gateway tags"
  type        = map(string)
  default = {
    "Owner" = "terraform"
    "Env"   = "test"
  }
}

# Create a DC global gateway resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_dc_global_gateway" "test" {
  name                  = var.global_gateway_name
  description           = var.global_gateway_description
  address_family        = var.address_family
  bgp_asn               = var.bgp_asn
  enterprise_project_id = var.enterprise_project_id

  tags = var.global_gateway_tags
}
```

**Parameter Description**:

- **name**: Global gateway name, assigned by referencing the input variable global\_gateway\_name
- **description**: Global gateway description, assigned by referencing the input variable global\_gateway\_description
- **address\_family**: IP address family, assigned by referencing the input variable address\_family, supports "ipv4" and "ipv6"
- **bgp\_asn**: BGP ASN, assigned by referencing the input variable bgp\_asn, used for BGP routing protocol configuration
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing the input variable enterprise\_project\_id
- **tags**: Tags, assigned by referencing the input variable global\_gateway\_tags, used for resource classification and management

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Global gateway configuration
global_gateway_name        = "tf_test_global_gateway"
global_gateway_description = "Created by Terraform"
address_family             = "ipv4"
bgp_asn                    = 65000
enterprise_project_id      = "0"

# Tag configuration
global_gateway_tags = {
  "Owner"     = "terraform"
  "Env"       = "test"
  "Project"   = "dc-demo"
  "CostCenter" = "IT"
}
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="global_gateway_name=my-gateway" -var="bgp_asn=65000"`
2. Environment variables: `export TF_VAR_global_gateway_name=my-gateway`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating the DC global gateway
4. Run `terraform show` to view the details of the created DC global gateway

## Reference Information

- [Huawei Cloud DC Product Documentation](https://support.huaweicloud.com/dc/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For DC Global Gateway](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dc/global-gateway)

# Deploy Hosted Connect

## Application Scenario

Direct Connect (DC) is a high-performance, low-latency, secure, and reliable dedicated line access service provided by Huawei Cloud, offering enterprises dedicated network connections from local data centers to Huawei Cloud. Direct Connect service supports multiple access methods, including physical dedicated lines and virtual dedicated lines, meeting network connection requirements for different scales and scenarios.

Hosted connect is a type of connection in Direct Connect service that allows creating virtual connections on existing operational connections, enabling multi-tenant sharing of physical dedicated line resources. Through hosted connects, you can reduce dedicated line costs, improve resource utilization, and meet network connection requirements for small and medium enterprises and multi-tenant scenarios. This best practice will introduce how to use Terraform to automatically deploy DC hosted connects, including connection creation, bandwidth configuration, and VLAN allocation.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

None

### Resources

- [DC Hosted Connect Resource (huaweicloud\_dc\_hosted\_connect)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dc_hosted_connect)

### Resource/Data Source Dependencies

```
huaweicloud_dc_hosted_connect.test
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create DC Hosted Connect

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a DC hosted connect resource:

```hcl
variable "hosted_connect_name" {
  description = "Hosted connect name"
  type        = string
}

variable "hosted_connect_description" {
  description = "Hosted connect description"
  type        = string
  default     = "Created by Terraform"
}

variable "bandwidth" {
  description = "Hosted connect bandwidth size (Mbit/s)"
  type        = number
}

variable "hosting_id" {
  description = "Operational connection ID on which the hosted connect is based"
  type        = string
}

variable "vlan" {
  description = "VLAN assigned to the hosted connect"
  type        = number
}

variable "resource_tenant_id" {
  description = "Tenant ID to which the hosted connect belongs"
  type        = string
}

variable "peer_location" {
  description = "Location of the local facility at the other end of the connection"
  type        = string
  default     = ""
}

# Create a DC hosted connect resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_dc_hosted_connect" "test" {
  name               = var.hosted_connect_name
  description        = var.hosted_connect_description
  bandwidth          = var.bandwidth
  hosting_id         = var.hosting_id
  vlan               = var.vlan
  resource_tenant_id = var.resource_tenant_id
  peer_location      = var.peer_location
}
```

**Parameter Description**:

- **name**: Hosted connect name, assigned by referencing the input variable hosted\_connect\_name
- **description**: Hosted connect description, assigned by referencing the input variable hosted\_connect\_description
- **bandwidth**: Bandwidth size, assigned by referencing the input variable bandwidth, unit is Mbit/s
- **hosting\_id**: Operational connection ID, assigned by referencing the input variable hosting\_id, specifies the operational connection on which the hosted connect is based
- **vlan**: VLAN ID, assigned by referencing the input variable vlan, used for network isolation
- **resource\_tenant\_id**: Tenant ID, assigned by referencing the input variable resource\_tenant\_id, specifies the tenant to which the hosted connect belongs
- **peer\_location**: Peer location, assigned by referencing the input variable peer\_location, describes the location of the local facility at the other end of the connection

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Hosted connect configuration
hosted_connect_name        = "tf_test_hosted_connect"
hosted_connect_description = "Created by Terraform"
bandwidth                  = 100
hosting_id                 = "tf_test_hosting_id"
vlan                       = 100
resource_tenant_id         = "tf_test_resource_tenant_id"
peer_location              = "Beijing Data Center"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="hosted_connect_name=my-connect" -var="bandwidth=100"`
2. Environment variables: `export TF_VAR_hosted_connect_name=my-connect`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating the DC hosted connect
4. Run `terraform show` to view the details of the created DC hosted connect

## Reference Information

- [Huawei Cloud DC Product Documentation](https://support.huaweicloud.com/dc/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For DC Hosted Connect](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dc/hosted_connect)

# Deploy Virtual Interface

## Application Scenario

Direct Connect (DC) is a high-performance, low-latency, secure, and reliable dedicated line access service provided by Huawei Cloud, offering enterprises dedicated network connections from local data centers to Huawei Cloud. Direct Connect service supports multiple access methods, including physical dedicated lines and virtual dedicated lines, meeting network connection requirements for different scales and scenarios.

Virtual interface is a core component in Direct Connect service, used to establish logical connections between dedicated lines and VPCs. Through virtual interfaces, you can achieve routing and forwarding of dedicated line traffic, supporting both static routing and BGP dynamic routing, meeting the needs of different network architectures. This best practice will introduce how to use Terraform to automatically deploy DC virtual interfaces, including VPC creation, virtual gateway creation, and virtual interface configuration.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

None

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [DC Virtual Gateway Resource (huaweicloud\_dc\_virtual\_gateway)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dc_virtual_gateway)
- [DC Virtual Interface Resource (huaweicloud\_dc\_virtual\_interface)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dc_virtual_interface)

### Resource/Data Source Dependencies

```
huaweicloud_vpc.test
    └── huaweicloud_dc_virtual_gateway.test
        └── huaweicloud_dc_virtual_interface.test
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create VPC

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC resource:

```hcl
variable "vpc_name" {
  description = "VPC name"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "192.168.0.0/16"
}

# Create a VPC resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: VPC name, assigned by referencing the input variable vpc\_name
- **cidr**: VPC CIDR block, assigned by referencing the input variable vpc\_cidr

### 3. Create DC Virtual Gateway

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a DC virtual gateway resource:

```hcl
variable "virtual_gateway_name" {
  description = "Virtual gateway name"
  type        = string
}

# Create a DC virtual gateway resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_dc_virtual_gateway" "test" {
  vpc_id = huaweicloud_vpc.test.id
  name   = var.virtual_gateway_name

  local_ep_group = [
    huaweicloud_vpc.test.cidr,
  ]
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID, assigned by referencing the VPC resource (huaweicloud\_vpc.test) ID
- **name**: Virtual gateway name, assigned by referencing the input variable virtual\_gateway\_name
- **local\_ep\_group**: Local endpoint group, assigned by referencing the VPC resource (huaweicloud\_vpc.test) CIDR

### 4. Create DC Virtual Interface

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a DC virtual interface resource:

```hcl
variable "direct_connect_id" {
  description = "Direct connect connection ID associated with the virtual interface"
  type        = string
}

variable "virtual_interface_name" {
  description = "Virtual interface name"
  type        = string
}

variable "virtual_interface_description" {
  description = "Virtual interface description"
  type        = string
  default     = "Created by Terraform"
}

variable "virtual_interface_type" {
  description = "Virtual interface type"
  type        = string
  default     = "private"
}

variable "route_mode" {
  description = "Virtual interface routing mode"
  type        = string
  default     = "static"
}

variable "vlan" {
  description = "Customer-side VLAN"
  type        = number
}

variable "bandwidth" {
  description = "Virtual interface inbound bandwidth size"
  type        = number
}

variable "remote_ep_group" {
  description = "Remote subnet CIDR list"
  type        = list(string)
}

variable "address_family" {
  description = "Virtual interface address family type"
  type        = string
  default     = "ipv4"
}

variable "local_gateway_v4_ip" {
  description = "Cloud-side virtual interface IPv4 address"
  type        = string
}

variable "remote_gateway_v4_ip" {
  description = "Customer-side virtual interface IPv4 address"
  type        = string
}

variable "enable_bfd" {
  description = "Whether to enable Bidirectional Forwarding Detection (BFD) function"
  type        = bool
  default     = false
}

variable "enable_nqa" {
  description = "Whether to enable Network Quality Analysis (NQA) function"
  type        = bool
  default     = false
}

variable "virtual_interface_tags" {
  description = "Virtual interface tags"
  type        = map(string)
  default = {
    "Owner" = "terraform"
    "Env"   = "test"
  }
}

# Create a DC virtual interface resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_dc_virtual_interface" "test" {
  direct_connect_id = var.direct_connect_id
  vgw_id            = huaweicloud_dc_virtual_gateway.test.id
  name              = var.virtual_interface_name
  description       = var.virtual_interface_description
  type              = var.virtual_interface_type
  route_mode        = var.route_mode
  vlan              = var.vlan
  bandwidth         = var.bandwidth

  remote_ep_group = var.remote_ep_group

  address_family       = var.address_family
  local_gateway_v4_ip  = var.local_gateway_v4_ip
  remote_gateway_v4_ip = var.remote_gateway_v4_ip

  enable_bfd = var.enable_bfd
  enable_nqa = var.enable_nqa

  tags = var.virtual_interface_tags
}
```

**Parameter Description**:

- **direct\_connect\_id**: Direct connect connection ID, assigned by referencing the input variable direct\_connect\_id
- **vgw\_id**: Virtual gateway ID, assigned by referencing the DC virtual gateway resource (huaweicloud\_dc\_virtual\_gateway.test) ID
- **name**: Virtual interface name, assigned by referencing the input variable virtual\_interface\_name
- **description**: Virtual interface description, assigned by referencing the input variable virtual\_interface\_description
- **type**: Virtual interface type, assigned by referencing the input variable virtual\_interface\_type, supports "private" and "public"
- **route\_mode**: Routing mode, assigned by referencing the input variable route\_mode, supports "static" and "bgp"
- **vlan**: Customer-side VLAN, assigned by referencing the input variable vlan
- **bandwidth**: Inbound bandwidth size, assigned by referencing the input variable bandwidth
- **remote\_ep\_group**: Remote subnet CIDR list, assigned by referencing the input variable remote\_ep\_group
- **address\_family**: Address family type, assigned by referencing the input variable address\_family, supports "ipv4" and "ipv6"
- **local\_gateway\_v4\_ip**: Cloud-side IPv4 address, assigned by referencing the input variable local\_gateway\_v4\_ip
- **remote\_gateway\_v4\_ip**: Customer-side IPv4 address, assigned by referencing the input variable remote\_gateway\_v4\_ip
- **enable\_bfd**: Whether to enable BFD function, assigned by referencing the input variable enable\_bfd
- **enable\_nqa**: Whether to enable NQA function, assigned by referencing the input variable enable\_nqa
- **tags**: Tags, assigned by referencing the input variable virtual\_interface\_tags

### 5. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# VPC configuration
vpc_name = "tf_test_vpc"
vpc_cidr = "192.168.0.0/16"

# Virtual gateway configuration
virtual_gateway_name = "tf_test_virtual_gateway"

# Virtual interface configuration
virtual_interface_name        = "tf_test_virtual_interface"
virtual_interface_description = "Created by Terraform"
virtual_interface_type        = "private"
route_mode                    = "static"
direct_connect_id             = "f50a0a20-7214-4614-b2f8-830994186934"
vlan                          = 100
bandwidth                     = 100
remote_ep_group               = ["10.10.10.0/30"]
address_family                = "ipv4"
local_gateway_v4_ip           = "10.10.10.1/30"
remote_gateway_v4_ip          = "10.10.10.2/30"
enable_bfd                    = false
enable_nqa                    = false

# Tag configuration
virtual_interface_tags = {
  "Owner"      = "terraform"
  "Env"        = "test"
  "Project"    = "dc-demo"
  "CostCenter" = "IT"
}
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="virtual_interface_name=my-interface"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 6. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating the DC virtual interface
4. Run `terraform show` to view the details of the created DC virtual interface

## Reference Information

- [Huawei Cloud DC Product Documentation](https://support.huaweicloud.com/dc/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For DC Virtual Interface](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dc/virtual-interface)
