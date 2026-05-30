# Deploy Instance

## Application Scenario

Enterprise Switch (ESW) is a high-performance, highly available enterprise-grade network switching service provided by Huawei Cloud, supporting large Layer 2 network interconnection and achieving Layer 2 network connections across availability zones. By deploying ESW instances, you can create Enterprise Switch instances, configure primary and standby availability zones and tunnel information, achieving Layer 2 network interconnection capabilities across availability zones. This best practice will introduce how to use Terraform to automatically deploy ESW instances, including VPC, subnet, and ESW instance creation.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [ESW Flavors Data Source (huaweicloud\_esw\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/esw_flavors)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [ESW Instance Resource (huaweicloud\_esw\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/esw_instance)

### Resource/Data Source Dependencies

```
data.huaweicloud_esw_flavors
    └── huaweicloud_esw_instance

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_esw_instance
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query ESW Flavors Data Source

Add the following script to the TF file (e.g., main.tf) to query ESW flavor information:

```hcl
# Query ESW flavor information
data "huaweicloud_esw_flavors" "test" {}
```

**Parameter Description**:

- This data source requires no parameters and will automatically query available ESW flavor information in the current region

### 3. Create VPC Resource

Add the following script to the TF file (e.g., main.tf) to create a VPC:

```hcl
variable "vpc_name" {
  description = "The name of the VPC"
  type        = string
}

variable "vpc_cidr" {
  description = "The CIDR block of the VPC"
  type        = string
  default     = "192.168.0.0/16"
}

# Create VPC
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: VPC name, assigned by referencing input variable vpc\_name
- **cidr**: VPC CIDR block, assigned by referencing input variable vpc\_cidr, default value is "192.168.0.0/16"

### 4. Create VPC Subnet Resource

Add the following script to the TF file (e.g., main.tf) to create a VPC subnet:

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

# Create VPC subnet
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID, assigned by referencing the VPC resource
- **name**: Subnet name, assigned by referencing input variable subnet\_name
- **cidr**: Subnet CIDR block, assigned by referencing input variables or automatic calculation
- **gateway\_ip**: Subnet gateway IP, assigned by referencing input variables or automatic calculation

### 5. Create ESW Instance Resource

Add the following script to the TF file (e.g., main.tf) to create an ESW instance:

```hcl
variable "esw_instance_name" {
  description = "The name of the instance"
  type        = string
  default     = ""
}

variable "esw_instance_ha_mode" {
  description = "The HA mode of the instance"
  type        = string
  default     = ""
}

variable "esw_instance_description" {
  description = "The description of the instance"
  type        = string
  default     = ""
}

variable "esw_instance_tunnel_ip" {
  description = "The tunnel IP of the instance"
  type        = string
  default     = "192.168.0.192"
}

# Create ESW instance
resource "huaweicloud_esw_instance" "test" {
  name        = var.esw_instance_name
  flavor_ref  = try(data.huaweicloud_esw_flavors.test.flavors[0].name, "")
  ha_mode     = var.esw_instance_ha_mode
  description = var.esw_instance_description

  availability_zones {
    primary = try(data.huaweicloud_esw_flavors.test.flavors.0.available_zones[0], "")
    standby = try(data.huaweicloud_esw_flavors.test.flavors.0.available_zones[1], "")
  }

  tunnel_info {
    vpc_id       = huaweicloud_vpc.test.id
    virsubnet_id = huaweicloud_vpc_subnet.test.id
    tunnel_ip    = var.esw_instance_tunnel_ip
  }

  charge_infos {
    charge_mode = "postPaid"
  }
}
```

**Parameter Description**:

- **name**: ESW instance name, assigned by referencing input variable esw\_instance\_name
- **flavor\_ref**: Flavor reference, assigned by referencing ESW flavors data source
- **ha\_mode**: High availability mode, assigned by referencing input variable esw\_instance\_ha\_mode, optional parameter
- **description**: Instance description, assigned by referencing input variable esw\_instance\_description, optional parameter
- **availability\_zones.primary**: Primary availability zone, assigned by referencing ESW flavors data source
- **availability\_zones.standby**: Standby availability zone, assigned by referencing ESW flavors data source
- **tunnel\_info.vpc\_id**: Tunnel VPC ID, assigned by referencing the VPC resource
- **tunnel\_info.virsubnet\_id**: Tunnel virtual subnet ID, assigned by referencing the subnet resource
- **tunnel\_info.tunnel\_ip**: Tunnel IP, assigned by referencing input variable esw\_instance\_tunnel\_ip, default value is "192.168.0.192"
- **charge\_infos.charge\_mode**: Charge mode, set to "postPaid" (pay-per-use)

### 6. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# VPC and Subnet Configuration
vpc_name    = "tf_test_esw_instance"
vpc_cidr    = "192.168.0.0/16"
subnet_name = "tf_test_esw_instance"

# ESW Instance Configuration
esw_instance_name    = "tf_test_esw_instance"
esw_instance_ha_mode = "ha"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially:
   - `esw_instance_ha_mode` can be set to "ha" (high availability mode) or other modes
   - `esw_instance_tunnel_ip` needs to be set to tunnel IP address, ensuring it is in the same network segment as the subnet CIDR
   - `esw_instance_description` can be set to instance description information, optional parameter
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="esw_instance_name=my_instance" -var="vpc_name=my_vpc"`
2. Environment variables: `export TF_VAR_esw_instance_name=my_instance` and `export TF_VAR_vpc_name=my_vpc`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. ESW instances need to configure primary and standby availability zones to ensure high availability. Tunnel IP needs to be in the same network segment as the subnet CIDR.

### 7. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create ESW instances:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating VPC, subnet, and ESW instance
4. Run `terraform show` to view the details of the created ESW instance

> Note: After the ESW instance is created, you need to wait for the instance status to become available before continuing to create ESW connections and other subsequent resources. Ensure that VPC and subnet are correctly created and tunnel IP is configured correctly, in the same network segment as the subnet CIDR.

## Reference Information

- [Huawei Cloud ESW Product Documentation](https://support.huaweicloud.com/esw/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Instance](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/esw/instance)

# Deploy Connection

## Application Scenario

Enterprise Switch (ESW) is a high-performance, highly available enterprise-grade network switching service provided by Huawei Cloud, supporting large Layer 2 network interconnection and achieving Layer 2 network connections across availability zones. Through ESW connections, you can connect VPC subnets with ESW instances to achieve Layer 2 network interconnection across availability zones. This best practice will introduce how to use Terraform to automatically deploy ESW connections, including VPC, subnet, ESW instance, and ESW connection creation.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [ESW Flavors Data Source (huaweicloud\_esw\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/esw_flavors)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [ESW Instance Resource (huaweicloud\_esw\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/esw_instance)
- [ESW Connection Resource (huaweicloud\_esw\_connection)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/esw_connection)

### Resource/Data Source Dependencies

```
data.huaweicloud_esw_flavors
    └── huaweicloud_esw_instance

huaweicloud_vpc
    ├── huaweicloud_vpc_subnet
    │   ├── huaweicloud_esw_instance
    │   └── huaweicloud_esw_connection
    └── huaweicloud_esw_instance

huaweicloud_esw_instance
    └── huaweicloud_esw_connection
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query ESW Flavors Data Source

Add the following script to the TF file (e.g., main.tf) to query ESW flavor information:

```hcl
# Query ESW flavor information
data "huaweicloud_esw_flavors" "test" {}
```

**Parameter Description**:

- This data source requires no parameters and will automatically query available ESW flavor information in the current region

### 3. Create VPC Resource

Add the following script to the TF file (e.g., main.tf) to create a VPC:

```hcl
variable "vpc_name" {
  description = "The name of the VPC"
  type        = string
}

variable "vpc_cidr" {
  description = "The CIDR block of the VPC"
  type        = string
  default     = "192.168.0.0/16"
}

# Create VPC
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: VPC name, assigned by referencing input variable vpc\_name
- **cidr**: VPC CIDR block, assigned by referencing input variable vpc\_cidr, default value is "192.168.0.0/16"

### 4. Create VPC Subnet Resources

Add the following script to the TF file (e.g., main.tf) to create multiple VPC subnets (this practice requires 2 subnets):

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

# Create VPC subnets (create 2 subnets)
resource "huaweicloud_vpc_subnet" "test" {
  count = 2

  vpc_id     = huaweicloud_vpc.test.id
  name       = format("%s-%d", var.subnet_name, count.index)
  cidr       = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
}
```

**Parameter Description**:

- **count**: Creation count, set to 2, creating 2 subnets
- **vpc\_id**: VPC ID, assigned by referencing the VPC resource
- **name**: Subnet name, assigned by referencing input variable subnet\_name and count index, format is "subnet\_name-0" and "subnet\_name-1"
- **cidr**: Subnet CIDR block, assigned by referencing input variables or automatic calculation
- **gateway\_ip**: Subnet gateway IP, assigned by referencing input variables or automatic calculation

### 5. Create ESW Instance Resource

Add the following script to the TF file (e.g., main.tf) to create an ESW instance:

```hcl
variable "esw_instance_name" {
  description = "The name of the instance"
  type        = string
  default     = ""
}

variable "esw_instance_ha_mode" {
  description = "The HA mode of the instance"
  type        = string
  default     = ""
}

variable "esw_instance_description" {
  description = "The description of the instance"
  type        = string
  default     = ""
}

variable "esw_instance_tunnel_ip" {
  description = "The tunnel IP of the instance"
  type        = string
  default     = "192.168.0.192"
}

# Create ESW instance
resource "huaweicloud_esw_instance" "test" {
  name        = var.esw_instance_name
  flavor_ref  = try(data.huaweicloud_esw_flavors.test.flavors[0].name, "")
  ha_mode     = var.esw_instance_ha_mode
  description = var.esw_instance_description

  availability_zones {
    primary = try(data.huaweicloud_esw_flavors.test.flavors.0.available_zones[0], "")
    standby = try(data.huaweicloud_esw_flavors.test.flavors.0.available_zones[1], "")
  }

  tunnel_info {
    vpc_id       = huaweicloud_vpc.test.id
    virsubnet_id = huaweicloud_vpc_subnet.test[0].id
    tunnel_ip    = var.esw_instance_tunnel_ip
  }

  charge_infos {
    charge_mode = "postPaid"
  }
}
```

**Parameter Description**:

- **name**: ESW instance name, assigned by referencing input variable esw\_instance\_name
- **flavor\_ref**: Flavor reference, assigned by referencing ESW flavors data source
- **ha\_mode**: High availability mode, assigned by referencing input variable esw\_instance\_ha\_mode, optional parameter
- **description**: Instance description, assigned by referencing input variable esw\_instance\_description, optional parameter
- **availability\_zones.primary**: Primary availability zone, assigned by referencing ESW flavors data source
- **availability\_zones.standby**: Standby availability zone, assigned by referencing ESW flavors data source
- **tunnel\_info.vpc\_id**: Tunnel VPC ID, assigned by referencing the VPC resource
- **tunnel\_info.virsubnet\_id**: Tunnel virtual subnet ID, assigned by referencing the first subnet resource
- **tunnel\_info.tunnel\_ip**: Tunnel IP, assigned by referencing input variable esw\_instance\_tunnel\_ip, default value is "192.168.0.192"
- **charge\_infos.charge\_mode**: Charge mode, set to "postPaid" (pay-per-use)

### 6. Create ESW Connection Resource

Add the following script to the TF file (e.g., main.tf) to create an ESW connection:

```hcl
variable "esw_connection_name" {
  description = "The name of the connection"
  type        = string
  default     = ""
}

variable "esw_connection_fixed_ips" {
  description = "The fixed IP IP of the connection"
  type        = list(string)
  default     = []
}

variable "esw_connection_segmentation_id" {
  description = "The segmentation ID of the connection"
  type        = number
  default     = 10000
}

# Create ESW connection
resource "huaweicloud_esw_connection" "test" {
  instance_id  = huaweicloud_esw_instance.test.id
  name         = var.esw_connection_name
  vpc_id       = huaweicloud_vpc.test.id
  virsubnet_id = huaweicloud_vpc_subnet.test[1].id
  fixed_ips    = var.esw_connection_fixed_ips

  remote_infos {
    segmentation_id = var.esw_connection_segmentation_id
    tunnel_ip       = huaweicloud_esw_instance.test.tunnel_info[0].tunnel_ip
    tunnel_port     = huaweicloud_esw_instance.test.tunnel_info[0].tunnel_port
  }
}
```

**Parameter Description**:

- **instance\_id**: ESW instance ID, assigned by referencing the ESW instance resource
- **name**: Connection name, assigned by referencing input variable esw\_connection\_name, optional parameter
- **vpc\_id**: VPC ID, assigned by referencing the VPC resource
- **virsubnet\_id**: Virtual subnet ID, assigned by referencing the second subnet resource
- **fixed\_ips**: Fixed IP list, assigned by referencing input variable esw\_connection\_fixed\_ips, optional parameter
- **remote\_infos.segmentation\_id**: Segmentation ID, assigned by referencing input variable esw\_connection\_segmentation\_id, default value is 10000
- **remote\_infos.tunnel\_ip**: Tunnel IP, assigned by referencing the ESW instance's tunnel IP
- **remote\_infos.tunnel\_port**: Tunnel port, assigned by referencing the ESW instance's tunnel port

### 7. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# VPC and Subnet Configuration
vpc_name    = "tf_test_esw_connection"
vpc_cidr    = "192.168.0.0/16"
subnet_name = "tf_test_esw_connection"

# ESW Instance Configuration
esw_instance_name    = "tf_test_esw_connection"
esw_instance_ha_mode = "ha"

# ESW Connection Configuration
esw_connection_name            = "tf_test_esw_connection"
esw_connection_segmentation_id = 9999
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially:
   - `esw_instance_ha_mode` can be set to "ha" (high availability mode) or other modes
   - `esw_connection_segmentation_id` needs to be set to segmentation ID for network segmentation identification
   - `esw_connection_fixed_ips` can be set to fixed IP list for the connection, optional parameter
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="esw_instance_name=my_instance" -var="vpc_name=my_vpc"`
2. Environment variables: `export TF_VAR_esw_instance_name=my_instance` and `export TF_VAR_vpc_name=my_vpc`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. ESW instances need to configure primary and standby availability zones to ensure high availability. ESW connections need to configure remote information, including segmentation ID, tunnel IP, and tunnel port.

### 8. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create ESW connections:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating VPC, subnet, ESW instance, and ESW connection
4. Run `terraform show` to view the details of the created ESW connection

> Note: After the ESW instance is created, you need to wait for the instance status to become available before continuing to create ESW connections. Ensure that VPC and subnets are correctly created and subnet CIDR is configured correctly. After the ESW connection is created, Layer 2 network interconnection across availability zones can be achieved.

## Reference Information

- [Huawei Cloud ESW Product Documentation](https://support.huaweicloud.com/esw/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Connection](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/esw/connection)

# Deploy Connection with Virtual Port Binding

## Application Scenario

Enterprise Switch (ESW) is a high-performance, highly available enterprise-grade network switching service provided by Huawei Cloud, supporting large Layer 2 network interconnection and achieving Layer 2 network connections across availability zones. Through ESW connection with virtual port binding, you can bind ESW connections with VPC subnet private IPs to achieve flexible configuration and management of network resources. This best practice will introduce how to use Terraform to automatically deploy ESW connection with virtual port binding, including VPC, subnet, ESW instance, ESW connection, VPC subnet private IP, and connection virtual port binding creation.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [ESW Flavors Data Source (huaweicloud\_esw\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/esw_flavors)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [ESW Instance Resource (huaweicloud\_esw\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/esw_instance)
- [ESW Connection Resource (huaweicloud\_esw\_connection)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/esw_connection)
- [VPC Subnet Private IP Resource (huaweicloud\_vpc\_subnet\_private\_ip)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet_private_ip)
- [ESW Connection Virtual Port Binding Resource (huaweicloud\_esw\_connection\_vport\_bind)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/esw_connection_vport_bind)

### Resource/Data Source Dependencies

```
data.huaweicloud_esw_flavors
    └── huaweicloud_esw_instance

huaweicloud_vpc
    ├── huaweicloud_vpc_subnet
    │   ├── huaweicloud_esw_instance
    │   ├── huaweicloud_esw_connection
    │   └── huaweicloud_vpc_subnet_private_ip
    │       └── huaweicloud_esw_connection_vport_bind
    └── huaweicloud_esw_instance

huaweicloud_esw_instance
    └── huaweicloud_esw_connection
        └── huaweicloud_esw_connection_vport_bind
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query ESW Flavors Data Source

Add the following script to the TF file (e.g., main.tf) to query ESW flavor information:

```hcl
# Query ESW flavor information
data "huaweicloud_esw_flavors" "test" {}
```

**Parameter Description**:

- This data source requires no parameters and will automatically query available ESW flavor information in the current region

### 3. Create VPC Resource

Add the following script to the TF file (e.g., main.tf) to create a VPC:

```hcl
variable "vpc_name" {
  description = "The name of the VPC"
  type        = string
}

variable "vpc_cidr" {
  description = "The CIDR block of the VPC"
  type        = string
  default     = "192.168.0.0/16"
}

# Create VPC
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: VPC name, assigned by referencing input variable vpc\_name
- **cidr**: VPC CIDR block, assigned by referencing input variable vpc\_cidr, default value is "192.168.0.0/16"

### 4. Create VPC Subnet Resources

Add the following script to the TF file (e.g., main.tf) to create multiple VPC subnets (this practice requires 2 subnets):

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

# Create VPC subnets (create 2 subnets)
resource "huaweicloud_vpc_subnet" "test" {
  count = 2

  vpc_id     = huaweicloud_vpc.test.id
  name       = format("%s-%d", var.subnet_name, count.index)
  cidr       = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
}
```

**Parameter Description**:

- **count**: Creation count, set to 2, creating 2 subnets
- **vpc\_id**: VPC ID, assigned by referencing the VPC resource
- **name**: Subnet name, assigned by referencing input variable subnet\_name and count index, format is "subnet\_name-0" and "subnet\_name-1"
- **cidr**: Subnet CIDR block, assigned by referencing input variables or automatic calculation
- **gateway\_ip**: Subnet gateway IP, assigned by referencing input variables or automatic calculation

### 5. Create ESW Instance Resource

Add the following script to the TF file (e.g., main.tf) to create an ESW instance:

```hcl
variable "esw_instance_name" {
  description = "The name of the instance"
  type        = string
  default     = ""
}

variable "esw_instance_ha_mode" {
  description = "The HA mode of the instance"
  type        = string
  default     = ""
}

variable "esw_instance_description" {
  description = "The description of the instance"
  type        = string
  default     = ""
}

variable "esw_instance_tunnel_ip" {
  description = "The tunnel IP of the instance"
  type        = string
  default     = "192.168.0.192"
}

# Create ESW instance
resource "huaweicloud_esw_instance" "test" {
  name        = var.esw_instance_name
  flavor_ref  = try(data.huaweicloud_esw_flavors.test.flavors[0].name, "")
  ha_mode     = var.esw_instance_ha_mode
  description = var.esw_instance_description

  availability_zones {
    primary = try(data.huaweicloud_esw_flavors.test.flavors.0.available_zones[0], "")
    standby = try(data.huaweicloud_esw_flavors.test.flavors.0.available_zones[1], "")
  }

  tunnel_info {
    vpc_id       = huaweicloud_vpc.test.id
    virsubnet_id = huaweicloud_vpc_subnet.test[0].id
    tunnel_ip    = var.esw_instance_tunnel_ip
  }

  charge_infos {
    charge_mode = "postPaid"
  }
}
```

**Parameter Description**:

- **name**: ESW instance name, assigned by referencing input variable esw\_instance\_name
- **flavor\_ref**: Flavor reference, assigned by referencing ESW flavors data source
- **ha\_mode**: High availability mode, assigned by referencing input variable esw\_instance\_ha\_mode, optional parameter
- **description**: Instance description, assigned by referencing input variable esw\_instance\_description, optional parameter
- **availability\_zones.primary**: Primary availability zone, assigned by referencing ESW flavors data source
- **availability\_zones.standby**: Standby availability zone, assigned by referencing ESW flavors data source
- **tunnel\_info.vpc\_id**: Tunnel VPC ID, assigned by referencing the VPC resource
- **tunnel\_info.virsubnet\_id**: Tunnel virtual subnet ID, assigned by referencing the first subnet resource
- **tunnel\_info.tunnel\_ip**: Tunnel IP, assigned by referencing input variable esw\_instance\_tunnel\_ip, default value is "192.168.0.192"
- **charge\_infos.charge\_mode**: Charge mode, set to "postPaid" (pay-per-use)

### 6. Create ESW Connection Resource

Add the following script to the TF file (e.g., main.tf) to create an ESW connection:

```hcl
variable "esw_connection_name" {
  description = "The name of the connection"
  type        = string
  default     = ""
}

variable "esw_connection_fixed_ips" {
  description = "The fixed IP IP of the connection"
  type        = list(string)
  default     = []
}

variable "esw_connection_segmentation_id" {
  description = "The segmentation ID of the connection"
  type        = number
  default     = 10000
}

# Create ESW connection
resource "huaweicloud_esw_connection" "test" {
  instance_id  = huaweicloud_esw_instance.test.id
  name         = var.esw_connection_name
  vpc_id       = huaweicloud_vpc.test.id
  virsubnet_id = huaweicloud_vpc_subnet.test[1].id
  fixed_ips    = var.esw_connection_fixed_ips

  remote_infos {
    segmentation_id = var.esw_connection_segmentation_id
    tunnel_ip       = huaweicloud_esw_instance.test.tunnel_info[0].tunnel_ip
    tunnel_port     = huaweicloud_esw_instance.test.tunnel_info[0].tunnel_port
  }
}
```

**Parameter Description**:

- **instance\_id**: ESW instance ID, assigned by referencing the ESW instance resource
- **name**: Connection name, assigned by referencing input variable esw\_connection\_name, optional parameter
- **vpc\_id**: VPC ID, assigned by referencing the VPC resource
- **virsubnet\_id**: Virtual subnet ID, assigned by referencing the second subnet resource
- **fixed\_ips**: Fixed IP list, assigned by referencing input variable esw\_connection\_fixed\_ips, optional parameter
- **remote\_infos.segmentation\_id**: Segmentation ID, assigned by referencing input variable esw\_connection\_segmentation\_id, default value is 10000
- **remote\_infos.tunnel\_ip**: Tunnel IP, assigned by referencing the ESW instance's tunnel IP
- **remote\_infos.tunnel\_port**: Tunnel port, assigned by referencing the ESW instance's tunnel port

### 7. Create VPC Subnet Private IP Resource

Add the following script to the TF file (e.g., main.tf) to create a VPC subnet private IP:

```hcl
# Create VPC subnet private IP
resource "huaweicloud_vpc_subnet_private_ip" "test" {
  subnet_id    = huaweicloud_vpc_subnet.test[1].id
  device_owner = "neutron:VIP_PORT"
}
```

**Parameter Description**:

- **subnet\_id**: Subnet ID, assigned by referencing the second subnet resource
- **device\_owner**: Device owner, set to "neutron:VIP\_PORT" (virtual IP port)

### 8. Create ESW Connection Virtual Port Binding Resource

Add the following script to the TF file (e.g., main.tf) to create ESW connection with virtual port binding:

```hcl
# Create ESW connection virtual port binding
resource "huaweicloud_esw_connection_vport_bind" "test" {
  connection_id = huaweicloud_esw_connection.test.id
  port_id       = huaweicloud_vpc_subnet_private_ip.test.id
}
```

**Parameter Description**:

- **connection\_id**: Connection ID, assigned by referencing the ESW connection resource
- **port\_id**: Port ID, assigned by referencing the VPC subnet private IP resource

### 9. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# VPC and Subnet Configuration
vpc_name    = "tf_test_esw_connection_cport_bind"
vpc_cidr    = "192.168.0.0/16"
subnet_name = "tf_test_esw_connection_cport_bind"

# ESW Instance Configuration
esw_instance_name    = "tf_test_esw_connection_cport_bind"
esw_instance_ha_mode = "ha"

# ESW Connection Configuration
esw_connection_name            = "tf_test_esw_connection_cport_bind"
esw_connection_segmentation_id = 9999
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially:
   - `esw_instance_ha_mode` can be set to "ha" (high availability mode) or other modes
   - `esw_connection_segmentation_id` needs to be set to segmentation ID for network segmentation identification
   - `esw_connection_fixed_ips` can be set to fixed IP list for the connection, optional parameter
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="esw_instance_name=my_instance" -var="vpc_name=my_vpc"`
2. Environment variables: `export TF_VAR_esw_instance_name=my_instance` and `export TF_VAR_vpc_name=my_vpc`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. ESW instances need to configure primary and standby availability zones to ensure high availability. ESW connections need to configure remote information, including segmentation ID, tunnel IP, and tunnel port.

### 10. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create ESW connection with virtual port binding:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating VPC, subnet, ESW instance, ESW connection, VPC subnet private IP, and connection virtual port binding
4. Run `terraform show` to view the details of the created connection virtual port binding

> Note: After the ESW instance is created, you need to wait for the instance status to become available before continuing to create ESW connections. After the ESW connection is created, you can create connection virtual port binding. Ensure that VPC and subnets are correctly created and subnet CIDR is configured correctly.

## Reference Information

- [Huawei Cloud ESW Product Documentation](https://support.huaweicloud.com/esw/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Connection with Virtual Port Binding](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/esw/connection-vport-bind)
