# Deploy Cloud Domain

## Application Scenario

Huawei Cloud Web Application Firewall (WAF) Cloud Mode is a Web security protection service based on shared resources that can provide Web attack protection for specified domains. By configuring WAF cloud mode domains, you can provide protection capabilities for your websites against various common Web attacks such as SQL injection, XSS cross-site scripting, web Trojan uploads, command injection, malicious crawlers, and CC attacks. WAF cloud mode domains support flexible origin server configuration, SSL certificate management, custom error pages, timeout settings, and traffic marking, meeting the security protection needs of different business scenarios. This best practice introduces how to use Terraform to automatically deploy a WAF cloud mode domain, including creating WAF cloud instances and domain configuration.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [WAF Cloud Instance Resource (huaweicloud\_waf\_cloud\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/waf_cloud_instance)
- [WAF Domain Resource (huaweicloud\_waf\_domain)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/waf_domain)

### Resource/Data Source Dependencies

```
huaweicloud_waf_cloud_instance
    └── huaweicloud_waf_domain
```

> Note: WAF domain depends on WAF cloud instance. Before creating a WAF domain, you need to create a WAF cloud instance first. WAF cloud instance provides basic security protection capabilities, and WAF domain is a specific protection domain configured on the basis of the cloud instance.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Create WAF Cloud Instance

Add the following script to the TF file (such as main.tf) to create a WAF cloud instance:

```hcl
resource "huaweicloud_waf_cloud_instance" "test" {
  resource_spec_code = var.cloud_instance_resource_spec_code

  dynamic "bandwidth_expack_product" {
    for_each = var.cloud_instance_bandwidth_expack_product

    content {
      resource_size = bandwidth_expack_product.value["resource_size"]
    }
  }

  dynamic "domain_expack_product" {
    for_each = var.cloud_instance_domain_expack_product

    content {
      resource_size = domain_expack_product.value["resource_size"]
    }
  }

  dynamic "rule_expack_product" {
    for_each = var.cloud_instance_rule_expack_product

    content {
      resource_size = rule_expack_product.value["resource_size"]
    }
  }

  charging_mode         = var.cloud_instance_charging_mode
  period_unit           = var.cloud_instance_period_unit
  period                = var.cloud_instance_period
  auto_renew            = var.cloud_instance_auto_renew
  enterprise_project_id = var.enterprise_project_id
}
```

**Parameter Description**:

- **resource\_spec\_code**: Resource specification code, assigned by referencing the input variable `cloud_instance_resource_spec_code`, such as "detection" (detection mode) or "premium" (premium edition)
- **bandwidth\_expack\_product**: Bandwidth expansion package configuration, creates bandwidth expansion packages through dynamic block `dynamic "bandwidth_expack_product"` based on input variable `cloud_instance_bandwidth_expack_product`
  - **resource\_size**: Resource size, assigned by referencing the `resource_size` in the input variable
- **domain\_expack\_product**: Domain expansion package configuration, creates domain expansion packages through dynamic block `dynamic "domain_expack_product"` based on input variable `cloud_instance_domain_expack_product`
  - **resource\_size**: Resource size, assigned by referencing the `resource_size` in the input variable
- **rule\_expack\_product**: Rule expansion package configuration, creates rule expansion packages through dynamic block `dynamic "rule_expack_product"` based on input variable `cloud_instance_rule_expack_product`
  - **resource\_size**: Resource size, assigned by referencing the `resource_size` in the input variable
- **charging\_mode**: Billing mode, assigned by referencing the input variable `cloud_instance_charging_mode`, such as "prePaid" (prepaid) or "postPaid" (pay-per-use)
- **period\_unit**: Subscription period unit, assigned by referencing the input variable `cloud_instance_period_unit`, such as "month" or "year"
- **period**: Subscription period, assigned by referencing the input variable `cloud_instance_period`
- **auto\_renew**: Whether to enable auto-renewal, assigned by referencing the input variable `cloud_instance_auto_renew`, such as "true" or "false"
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing the input variable `enterprise_project_id`, default is "0" indicating the default enterprise project

### 3. Create WAF Domain

Add the following script to the TF file (such as main.tf) to create a WAF domain:

```hcl
resource "huaweicloud_waf_domain" "test" {
  domain                = var.cloud_domain
  certificate_id        = var.cloud_certificate_id
  certificate_name      = var.cloud_certificate_name
  proxy                 = var.cloud_proxy
  enterprise_project_id = var.enterprise_project_id
  description           = var.cloud_description
  website_name          = var.cloud_website_name
  protect_status        = var.cloud_protect_status
  forward_header_map    = var.cloud_forward_header_map

  dynamic "custom_page" {
    for_each = var.cloud_custom_page

    content {
      http_return_code = custom_page.value["http_return_code"]
      block_page_type  = custom_page.value["block_page_type"]
      page_content     = custom_page.value["page_content"]
    }
  }

  dynamic "timeout_settings" {
    for_each = var.cloud_timeout_settings

    content {
      connection_timeout = timeout_settings.value["connection_timeout"]
      read_timeout       = timeout_settings.value["read_timeout"]
      write_timeout      = timeout_settings.value["write_timeout"]
    }
  }

  dynamic "traffic_mark" {
    for_each = var.cloud_traffic_mark

    content {
      ip_tags     = traffic_mark.value["ip_tags"]
      session_tag = traffic_mark.value["session_tag"]
      user_tag    = traffic_mark.value["user_tag"]
    }
  }

  dynamic "server" {
    for_each = var.cloud_server

    content {
      client_protocol = server.value["client_protocol"]
      server_protocol = server.value["server_protocol"]
      address         = server.value["address"]
      port            = server.value["port"]
      type            = server.value["type"]
      weight          = server.value["weight"]
    }
  }

  depends_on = [
    huaweicloud_waf_cloud_instance.test
  ]
}
```

**Parameter Description**:

- **domain**: Domain name to be protected, assigned by referencing the input variable `cloud_domain`
- **certificate\_id**: SSL certificate ID, assigned by referencing the input variable `cloud_certificate_id`, used for HTTPS access
- **certificate\_name**: SSL certificate name, assigned by referencing the input variable `cloud_certificate_name`
- **proxy**: Whether to enable proxy, assigned by referencing the input variable `cloud_proxy`, true means enable proxy, false means disable proxy
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing the input variable `enterprise_project_id`, default is "0" indicating the default enterprise project
- **description**: Domain description, assigned by referencing the input variable `cloud_description`
- **website\_name**: Website name, assigned by referencing the input variable `cloud_website_name`
- **protect\_status**: Protection status, assigned by referencing the input variable `cloud_protect_status`, 0 means disable protection, 1 means enable protection
- **forward\_header\_map**: Field forwarding configuration, assigned by referencing the input variable `cloud_forward_header_map`, used for custom request header forwarding
- **custom\_page**: Custom error page configuration, creates custom error pages through dynamic block `dynamic "custom_page"` based on input variable `cloud_custom_page`
  - **http\_return\_code**: HTTP return code, assigned by referencing the `http_return_code` in the input variable
  - **block\_page\_type**: Block page type, assigned by referencing the `block_page_type` in the input variable
  - **page\_content**: Page content, assigned by referencing the `page_content` in the input variable
- **timeout\_settings**: Timeout settings configuration, creates timeout settings through dynamic block `dynamic "timeout_settings"` based on input variable `cloud_timeout_settings`
  - **connection\_timeout**: Connection timeout, assigned by referencing the `connection_timeout` in the input variable
  - **read\_timeout**: Read timeout, assigned by referencing the `read_timeout` in the input variable
  - **write\_timeout**: Write timeout, assigned by referencing the `write_timeout` in the input variable
- **traffic\_mark**: Traffic marking configuration, creates traffic marking through dynamic block `dynamic "traffic_mark"` based on input variable `cloud_traffic_mark`
  - **ip\_tags**: IP tag list, assigned by referencing the `ip_tags` in the input variable
  - **session\_tag**: Session tag, assigned by referencing the `session_tag` in the input variable
  - **user\_tag**: User tag, assigned by referencing the `user_tag` in the input variable
- **server**: Origin server configuration list, creates origin server configurations through dynamic block `dynamic "server"` based on input variable `cloud_server`
  - **client\_protocol**: Client protocol, assigned by referencing the `client_protocol` in the input variable, such as "HTTP" or "HTTPS"
  - **server\_protocol**: Server protocol, assigned by referencing the `server_protocol` in the input variable, such as "HTTP" or "HTTPS"
  - **address**: Origin server address, assigned by referencing the `address` in the input variable, can be an IP address or domain name
  - **port**: Origin server port, assigned by referencing the `port` in the input variable
  - **type**: Origin server type, assigned by referencing the `type` in the input variable, such as "ipv4" or "ipv6"
  - **weight**: Origin server weight, assigned by referencing the `weight` in the input variable, used for load balancing
- **depends\_on**: Explicit dependency relationship, ensures that WAF cloud instance is created before WAF domain

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# WAF cloud instance configuration (Required)
cloud_instance_resource_spec_code = "detection"
cloud_instance_charging_mode      = "prePaid"
cloud_instance_period_unit        = "month"
cloud_instance_period             = 1

# WAF domain configuration (Required)
cloud_domain = "demo-example-test.huawei.com"

# Origin server configuration (Required)
cloud_server = [
  {
    client_protocol = "HTTP"
    server_protocol = "HTTP"
    address         = "119.8.0.17"
    port            = 8080
    type            = "ipv4"
    weight          = 1
  }
]
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="cloud_domain=demo-example-test.huawei.com"`
2. Environment variables: `export TF_VAR_cloud_domain=demo-example-test.huawei.com`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating WAF cloud mode domain and related resources
4. Run `terraform show` to view the created WAF cloud mode domain

## Reference Information

- [Huawei Cloud WAF Product Documentation](https://support.huaweicloud.com/intl/en-us/waf/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Cloud Domain](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/waf/cloud-domain)

# Deploy Professional Edition Domain

## Application Scenario

Huawei Cloud Web Application Firewall (WAF) Professional Edition Domain is a Web security protection service based on dedicated resources that can provide Web attack protection for specified domains. By configuring WAF Professional Edition Domain, you can provide your website with protection capabilities against various common Web attacks such as SQL injection, XSS cross-site scripting, web trojan upload, command injection, and more. This best practice will introduce how to use Terraform to automatically deploy a WAF Professional Edition Domain, including creating WAF Professional Edition instances, WAF policies, and domain configurations.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zone List Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [Compute Flavor List Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [WAF Professional Edition Instance Resource (huaweicloud\_waf\_dedicated\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/waf_dedicated_instance)
- [WAF Policy Resource (huaweicloud\_waf\_policy)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/waf_policy)
- [WAF Professional Edition Domain Resource (huaweicloud\_waf\_dedicated\_domain)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/waf_dedicated_domain)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    ├── huaweicloud_vpc_subnet
    ├── data.huaweicloud_compute_flavors
    └── huaweicloud_waf_dedicated_instance

data.huaweicloud_compute_flavors
    └── huaweicloud_waf_dedicated_instance

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        ├── huaweicloud_waf_dedicated_instance
        └── huaweicloud_waf_dedicated_domain

huaweicloud_networking_secgroup
    └── huaweicloud_waf_dedicated_instance

huaweicloud_waf_dedicated_instance
    └── huaweicloud_waf_policy
        └── huaweicloud_waf_dedicated_domain
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Prerequisite Resource Preparation

This best practice requires creating prerequisite resources such as VPC, subnets, security groups, and WAF Professional Edition instances first. Please follow the following steps in the "Deploy WAF Professional Edition Instance" best practice for preparation:

- **Step 2**: Create VPC resource
- **Step 3**: Query availability zones required for WAF instance resource creation through data sources
- **Step 4**: Create VPC subnet resource
- **Step 5**: Query compute flavors required for WAF instance resource creation through data sources
- **Step 6**: Create security group resource
- **Step 7**: Create WAF Professional Edition instance resource

After completing the above steps, continue with the subsequent steps of this best practice.

### 3. Create WAF Policy Resource

Add the following script to the TF file to instruct Terraform to create a WAF policy resource:

```hcl
variable "policy_name" {
  description = "The WAF policy name"
  type        = string
}

variable "policy_level" {
  description = "The WAF policy level"
  type        = number
  default     = 1
}

# Create a WAF policy resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to configure protection rules for WAF Professional Edition Domain
resource "huaweicloud_waf_policy" "test" {
  name  = var.policy_name
  level = var.policy_level

  depends_on = [
    huaweicloud_waf_dedicated_instance.test
  ]
}
```

**Parameter Description**:

- **name**: WAF policy name, assigned by referencing the input variable policy\_name
- **level**: WAF policy protection level, assigned by referencing the input variable policy\_level, default value is 1
- **depends\_on**: Resource dependency relationship, ensuring WAF Professional Edition instance has been created

### 4. Create WAF Professional Edition Domain Resource

Add the following script to the TF file to instruct Terraform to create a WAF Professional Edition Domain resource:

```hcl
variable "dedicated_mode_domain_name" {
  description = "The WAF dedicated mode domain name"
  type        = string
}

variable "dedicated_domain_client_protocol" {
  description = "The client protocol of the WAF dedicated domain"
  type        = string
  default     = "HTTP"
}

variable "dedicated_domain_server_protocol" {
  description = "The server protocol of the WAF dedicated domain"
  type        = string
  default     = "HTTP"
}

variable "dedicated_domain_address" {
  description = "The address of the WAF dedicated domain"
  type        = string
  default     = "192.168.0.14"
}

variable "dedicated_domain_port" {
  description = "The port of the WAF dedicated domain"
  type        = number
  default     = 8080
}

variable "dedicated_domain_type" {
  description = "The type of the WAF dedicated domain"
  type        = string
  default     = "ipv4"
}

# Create a WAF Professional Edition Domain resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_waf_dedicated_domain" "test" {
  domain      = var.dedicated_mode_domain_name
  policy_id   = huaweicloud_waf_policy.test.id
  keep_policy = true

  server {
    client_protocol = var.dedicated_domain_client_protocol
    server_protocol = var.dedicated_domain_server_protocol
    address         = var.dedicated_domain_address == "" ? cidrhost(huaweicloud_vpc_subnet.test.cidr, 4) : var.dedicated_domain_address
    port            = var.dedicated_domain_port
    type            = var.dedicated_domain_type
    vpc_id          = huaweicloud_vpc.test.id
  }
}
```

**Parameter Description**:

- **domain**: WAF Professional Edition Domain name, assigned by referencing the input variable dedicated\_mode\_domain\_name
- **policy\_id**: WAF policy ID, referencing the ID of the previously created WAF policy resource
- **keep\_policy**: Whether to keep the policy, set to true to keep the policy
- **server**: Server configuration block
  - **client\_protocol**: Client protocol, assigned by referencing the input variable dedicated\_domain\_client\_protocol, default value is "HTTP"
  - **server\_protocol**: Server protocol, assigned by referencing the input variable dedicated\_domain\_server\_protocol, default value is "HTTP"
  - **address**: Server address, if dedicated\_domain\_address is empty, uses cidrhost function to get the 4th IP address from the subnet segment, otherwise uses the specified dedicated\_domain\_address
  - **port**: Server port, assigned by referencing the input variable dedicated\_domain\_port, default value is 8080
  - **type**: Server type, assigned by referencing the input variable dedicated\_domain\_type, default value is "ipv4"
  - **vpc\_id**: VPC ID, referencing the ID of the previously created VPC resource

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

# WAF Professional Edition instance configuration
dedicated_instance_name               = "tf_test_waf_instance"
dedicated_instance_specification_code = "waf.instance.professional"
dedicated_instance_performance_type   = "normal"
dedicated_instance_cpu_core_count     = 4
dedicated_instance_memory_size        = 8

# Security group configuration
security_group_name = "tf_test_security_group"

# WAF policy configuration
policy_name = "tf_test_waf_policy"
policy_level = 1

# WAF Professional Edition Domain configuration
dedicated_mode_domain_name = "www.example.com"
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
3. After confirming the resource plan is correct, run `terraform apply` to start creating WAF Professional Edition Domain
4. Run `terraform show` to view the created WAF Professional Edition Domain details

## Reference Information

- [Huawei Cloud WAF Product Documentation](https://support.huaweicloud.com/waf/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For WAF Professional Edition Domain](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/waf/dedicated-domain)

# Deploy Professional Edition Instance

## Application Scenario

Huawei Cloud Web Application Firewall (WAF) Professional Edition is a Web security protection service based on dedicated resources that can effectively defend against various common Web attacks such as SQL injection, XSS cross-site scripting, web trojan upload, command injection, and more. WAF Professional Edition instances provide dedicated resources, offering more customized Web security protection for enterprises, suitable for scenarios with high-performance requirements for Web application security protection and strict requirements for compliance and data isolation. This best practice will introduce how to use Terraform to automatically deploy a WAF Professional Edition instance.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Availability Zone List Query Data Source (data.huaweicloud\_availability\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/availability_zones)
- [Compute Flavor List Query Data Source (data.huaweicloud\_compute\_flavors)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/compute_flavors)

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [Security Group Resource (huaweicloud\_networking\_secgroup)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/networking_secgroup)
- [WAF Professional Edition Instance Resource (huaweicloud\_waf\_dedicated\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/waf_dedicated_instance)

### Resource/Data Source Dependencies

```
data.huaweicloud_availability_zones
    ├── huaweicloud_vpc_subnet
    ├── data.huaweicloud_compute_flavors
    └── huaweicloud_waf_dedicated_instance

data.huaweicloud_compute_flavors
    └── huaweicloud_waf_dedicated_instance

huaweicloud_vpc
    └── huaweicloud_vpc_subnet
        └── huaweicloud_waf_dedicated_instance

huaweicloud_networking_secgroup
    └── huaweicloud_waf_dedicated_instance
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
  default     = "192.168.0.0/16"
}

# Create a VPC resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to deploy WAF Professional Edition instances
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}
```

**Parameter Description**:

- **name**: VPC name, assigned by referencing the input variable vpc\_name
- **cidr**: VPC CIDR block, assigned by referencing the input variable vpc\_cidr, default value is "192.168.0.0/16"

### 3. Query Availability Zones Required for WAF Instance Resource Creation Through Data Source

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to perform a data source query, the results of which are used to create WAF Professional Edition instances:

```hcl
variable "availability_zone" {
  description = "The availability zone to which the dedicated instance belongs"
  type        = string
  default     = ""
}

# Get all availability zone information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to create WAF Professional Edition instances
data "huaweicloud_availability_zones" "test" {
  count = var.availability_zone == "" ? 1 : 0
}
```

**Parameter Description**:

- **count**: Creation count of the data source, used to control whether to execute the availability zone list query data source, only creates the data source when `var.availability_zone` is empty (i.e., executes availability zone list query)

### 4. Create VPC Subnet Resource

Add the following script to the TF file to instruct Terraform to create a VPC subnet resource:

```hcl
variable "subnet_name" {
  description = "The subnet name"
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

# Create a VPC subnet resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to deploy WAF Professional Edition instances
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id            = huaweicloud_vpc.test.id
  name              = var.subnet_name
  cidr              = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip        = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
  availability_zone = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test[0].names[0], null) : var.availability_zone
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID that the subnet belongs to, referencing the ID of the previously created VPC resource
- **name**: Subnet name, assigned by referencing the input variable subnet\_name
- **cidr**: Subnet CIDR block, if subnet\_cidr is empty, uses cidrsubnet function to divide a subnet segment from the VPC's CIDR block, otherwise uses the specified subnet\_cidr
- **gateway\_ip**: Subnet gateway IP, if subnet\_gateway\_ip is empty, uses cidrhost function to get the first IP address from the subnet segment as gateway IP, otherwise uses the specified subnet\_gateway\_ip
- **availability\_zone**: Availability zone where the subnet is located, if availability\_zone is empty, uses the first availability zone from the availability zone list query data source, otherwise uses the specified availability\_zone

### 5. Query Compute Flavors Required for WAF Instance Resource Creation Through Data Source

Add the following script to the TF file to instruct Terraform to query compute flavors that meet the conditions:

```hcl
variable "dedicated_instance_flavor_id" {
  description = "The flavor ID of the dedicated instance"
  type        = string
  default     = ""
}

variable "dedicated_instance_performance_type" {
  description = "The performance type of the dedicated instance"
  type        = string
  default     = "normal"
}

variable "dedicated_instance_cpu_core_count" {
  description = "The number of the dedicated instance CPU cores"
  type        = number
  default     = 4
}

variable "dedicated_instance_memory_size" {
  description = "The memory size of the dedicated instance"
  type        = number
  default     = 8
}

# Get all compute flavor information under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block) that meets specific conditions, used to create WAF Professional Edition instances
data "huaweicloud_compute_flavors" "test" {
  count = var.dedicated_instance_flavor_id == "" ? 1 : 0

  availability_zone = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test[0].names[0], null) : var.availability_zone
  performance_type  = var.dedicated_instance_performance_type
  cpu_core_count    = var.dedicated_instance_cpu_core_count
  memory_size       = var.dedicated_instance_memory_size
}
```

**Parameter Description**:

- **count**: Creation count of the data source, used to control whether to execute the compute flavor list query data source, only creates the data source when `var.dedicated_instance_flavor_id` is empty
- **availability\_zone**: Availability zone where the compute flavor is located, if availability\_zone is empty, uses the first availability zone from the availability zone list query data source, otherwise uses the specified availability\_zone
- **performance\_type**: Performance type, assigned by referencing the input variable dedicated\_instance\_performance\_type, default value is "normal"
- **cpu\_core\_count**: CPU core count, assigned by referencing the input variable dedicated\_instance\_cpu\_core\_count, default value is 4
- **memory\_size**: Memory size (GB), assigned by referencing the input variable dedicated\_instance\_memory\_size, default value is 8

### 6. Create Security Group Resource

Add the following script to the TF file to instruct Terraform to create a security group resource:

```hcl
variable "security_group_name" {
  description = "The security group name"
  type        = string
}

# Create a security group resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block), used to deploy WAF Professional Edition instances
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}
```

**Parameter Description**:

- **name**: Security group name, assigned by referencing the input variable security\_group\_name
- **delete\_default\_rules**: Whether to delete default rules, set to true to delete default rules

### 7. Create WAF Professional Edition Instance Resource

Add the following script to the TF file to instruct Terraform to create a WAF Professional Edition instance resource:

```hcl
variable "dedicated_instance_name" {
  description = "The WAF dedicated instance name"
  type        = string
}

variable "dedicated_instance_specification_code" {
  description = "The specification code of the dedicated instance"
  type        = string
  default     = "waf.instance.professional"
}

# Create a WAF Professional Edition instance resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_waf_dedicated_instance" "test" {
  name               = var.dedicated_instance_name
  specification_code = var.dedicated_instance_specification_code
  vpc_id             = huaweicloud_vpc.test.id
  subnet_id          = huaweicloud_vpc_subnet.test.id
  available_zone     = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test[0].names[0], null) : var.availability_zone
  ecs_flavor         = var.dedicated_instance_flavor_id == "" ? data.huaweicloud_compute_flavors.test[0].ids[0] : var.dedicated_instance_flavor_id

  security_group = [
    huaweicloud_networking_secgroup.test.id
  ]
}
```

**Parameter Description**:

- **name**: WAF Professional Edition instance name, assigned by referencing the input variable dedicated\_instance\_name
- **specification\_code**: WAF Professional Edition instance specification code, assigned by referencing the input variable dedicated\_instance\_specification\_code, default value is "waf.instance.professional"
- **vpc\_id**: VPC ID where the WAF Professional Edition instance is located, referencing the ID of the previously created VPC resource
- **subnet\_id**: Subnet ID where the WAF Professional Edition instance is located, referencing the ID of the previously created subnet resource
- **available\_zone**: Availability zone where the WAF Professional Edition instance is located, if availability\_zone is empty, uses the first availability zone from the availability zone list query data source, otherwise uses the specified availability\_zone
- **ecs\_flavor**: Compute flavor used by the WAF Professional Edition instance, if dedicated\_instance\_flavor\_id is empty, uses the first flavor from the compute flavor list query data source, otherwise uses the specified dedicated\_instance\_flavor\_id
- **security\_group**: Security group ID list used by the WAF Professional Edition instance, referencing the ID of the previously created security group resource

### 8. Preset Input Parameters Required for Resource Deployment (Optional)

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

# WAF Professional Edition instance configuration
dedicated_instance_name               = "tf_test_waf_dedicated_instance"
dedicated_instance_specification_code = "waf.instance.professional"
dedicated_instance_performance_type   = "normal"
dedicated_instance_cpu_core_count     = 4
dedicated_instance_memory_size        = 8

# Security group configuration
security_group_name = "tf_test_secgroup"
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

### 9. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating WAF Professional Edition instances
4. Run `terraform show` to view the created WAF Professional Edition instance details

## Reference Information

- [Huawei Cloud WAF Product Documentation](https://support.huaweicloud.com/waf/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For WAF Professional Edition Instance](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/waf/dedicated-instance)
