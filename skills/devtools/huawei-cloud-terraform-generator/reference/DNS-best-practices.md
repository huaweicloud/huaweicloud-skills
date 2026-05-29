# Deploy Custom Line

## Application Scenario

Domain Name Service (DNS) is a highly available, high-performance domain name resolution service provided by Huawei Cloud, supporting both public and private domain name resolution. DNS service provides intelligent resolution, load balancing, health check, and other functions, helping users achieve intelligent scheduling and failover of domain names.

Custom lines are advanced features in DNS service that allow users to create custom resolution lines based on specific IP address segments, achieving more fine-grained traffic scheduling and resolution control. Through custom lines, enterprises can provide different resolution results for different user groups based on factors such as user geographic location, network operator, IP address segment, etc., implementing intelligent resolution and load balancing. This best practice will introduce how to use Terraform to automatically deploy DNS custom lines, including line creation and IP address segment configuration.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [DNS Custom Line Resource (huaweicloud\_dns\_custom\_line)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dns_custom_line)

### Resource/Data Source Dependencies

```
No dependencies
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create DNS Custom Line

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a DNS custom line resource:

```hcl
variable "dns_custom_line_name" {
  description = "Custom line name"
  type        = string
}

variable "dns_custom_line_ip_segments" {
  description = "IP address segments"
  type        = list(string)
}

# Create a DNS custom line resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_dns_custom_line" "test" {
  name        = var.dns_custom_line_name
  ip_segments = var.dns_custom_line_ip_segments
}
```

**Parameter Description**:

- **name**: Custom line name, assigned by referencing the input variable dns\_custom\_line\_name
- **ip\_segments**: IP address segment list, assigned by referencing the input variable dns\_custom\_line\_ip\_segments

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# DNS custom line configuration
dns_custom_line_name        = "your_custom_line_name"
dns_custom_line_ip_segments = ["100.100.100.102-100.100.100.102", "100.100.100.101-100.100.100.101"]
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="dns_custom_line_name=my-line" -var="dns_custom_line_ip_segments=[\"192.168.1.1-192.168.1.10\"]"`
2. Environment variables: `export TF_VAR_dns_custom_line_name=my-line`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating the DNS custom line
4. Run `terraform show` to view the details of the created DNS custom line

## Reference Information

- [Huawei Cloud DNS Product Documentation](https://support.huaweicloud.com/dns/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For DNS Custom Line](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dns/custom-line)

# Deploy Endpoint

## Application Scenario

Domain Name Service (DNS) is a highly available, high-performance domain name resolution service provided by Huawei Cloud, supporting both public and private domain name resolution. DNS service provides intelligent resolution, load balancing, health check, and other functions, helping users achieve intelligent scheduling and failover of domain names.

DNS endpoints are network access points in DNS service, used to provide DNS resolution services in VPC networks. Through endpoints, enterprises can deploy DNS services in private networks, implementing internal domain name resolution, private DNS forwarding, and other functions. Endpoints support both inbound and outbound directions, meeting DNS resolution requirements for different scenarios. This best practice will introduce how to use Terraform to automatically deploy DNS endpoints, including VPC creation, subnet configuration, and endpoint deployment.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [VPC Resource (huaweicloud\_vpc)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc)
- [VPC Subnet Resource (huaweicloud\_vpc\_subnet)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_subnet)
- [DNS Endpoint Resource (huaweicloud\_dns\_endpoint)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dns_endpoint)

### Resource/Data Source Dependencies

```
huaweicloud_vpc.test
    └── huaweicloud_vpc_subnet.test
        └── huaweicloud_dns_endpoint.test
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

### 3. Create VPC Subnet

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a VPC subnet resource:

```hcl
variable "subnet_name" {
  description = "Subnet name"
  type        = string
}

variable "subnet_cidr" {
  description = "Subnet CIDR block"
  type        = string
  default     = ""
}

variable "subnet_gateway_ip" {
  description = "Subnet gateway IP"
  type        = string
  default     = ""
}

# Create a VPC subnet resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
}
```

**Parameter Description**:

- **vpc\_id**: VPC ID, assigned by referencing the VPC resource (huaweicloud\_vpc.test) ID
- **name**: Subnet name, assigned by referencing the input variable subnet\_name
- **cidr**: Subnet CIDR block, prioritizes using input variable, automatically calculated if empty
- **gateway\_ip**: Gateway IP, prioritizes using input variable, automatically calculated if empty

### 4. Create DNS Endpoint

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a DNS endpoint resource:

```hcl
variable "dns_endpoint_name" {
  description = "DNS endpoint name"
  type        = string
}

variable "dns_endpoint_direction" {
  description = "DNS endpoint direction"
  type        = string
  default     = "inbound"
}

# Create a DNS endpoint resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_dns_endpoint" "test" {
  name      = var.dns_endpoint_name
  direction = var.dns_endpoint_direction

  ip_addresses {
    subnet_id = huaweicloud_vpc_subnet.test.id
  }

  ip_addresses {
    subnet_id = huaweicloud_vpc_subnet.test.id
  }
}
```

**Parameter Description**:

- **name**: Endpoint name, assigned by referencing the input variable dns\_endpoint\_name
- **direction**: Endpoint direction, assigned by referencing the input variable dns\_endpoint\_direction, defaults to "inbound"
- **ip\_addresses.subnet\_id**: IP address subnet ID, assigned by referencing the VPC subnet resource (huaweicloud\_vpc\_subnet.test) ID

### 5. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# Network configuration
vpc_name    = "tf_test_dns_endpoint"
subnet_name = "tf_test_dns_endpoint"

# DNS endpoint configuration
dns_endpoint_name = "tf_test_dns_endpoint"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="vpc_name=my-vpc" -var="dns_endpoint_name=my-endpoint"`
2. Environment variables: `export TF_VAR_vpc_name=my-vpc`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 6. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating the DNS endpoint
4. Run `terraform show` to view the details of the created DNS endpoint

## Reference Information

- [Huawei Cloud DNS Product Documentation](https://support.huaweicloud.com/dns/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For DNS Endpoint](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dns/endpoint)

# Deploy Public Zone

## Application Scenario

Domain Name Service (DNS) is a highly available, high-performance domain name resolution service provided by Huawei Cloud, supporting both public and private domain name resolution. DNS service provides intelligent resolution, load balancing, health check, and other functions, helping users achieve intelligent scheduling and failover of domain names.

Public zones are core functions in DNS service, used to manage internet-facing domain name resolution. Through public zones, enterprises can manage their website domains, API domains, mail server domains, etc., implementing domain name to IP address mapping. Public zones support multiple record types, including A records, AAAA records, CNAME records, MX records, etc., meeting resolution requirements for different application scenarios. This best practice will introduce how to use Terraform to automatically deploy DNS public zones, including domain creation, TTL configuration, DNSSEC settings, and router association.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [DNS Public Zone Resource (huaweicloud\_dns\_zone)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dns_zone)

### Resource/Data Source Dependencies

```
No dependencies
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create DNS Public Zone

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a DNS public zone resource:

```hcl
variable "dns_public_zone_name" {
  description = "Domain name"
  type        = string
}

variable "dns_public_zone_email" {
  description = "Administrator email address for managing the domain"
  type        = string
  default     = ""
}

variable "dns_public_zone_type" {
  description = "Domain type"
  type        = string
  default     = "public"
}

variable "dns_public_zone_description" {
  description = "Domain description"
  type        = string
}

variable "dns_public_zone_ttl" {
  description = "Time to live (TTL) of the domain"
  type        = number
  default     = 300
}

variable "dns_public_zone_enterprise_project_id" {
  description = "Enterprise project ID that the domain belongs to"
  type        = string
  default     = ""
}

variable "dns_public_zone_status" {
  description = "Domain status"
  type        = string
  default     = "ENABLE"
}

variable "dns_public_zone_dnssec" {
  description = "Whether to enable DNSSEC for the public domain"
  type        = string
  default     = "DISABLE"
}

variable "dns_public_zone_router" {
  description = "List of routers associated with the domain"
  type = list(object({
    router_id     = string
    router_region = string
  }))
  default = []
}

# Create a DNS public zone resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_dns_zone" "test" {
  name                  = var.dns_public_zone_name
  email                 = var.dns_public_zone_email
  zone_type             = var.dns_public_zone_type
  description           = var.dns_public_zone_description
  ttl                   = var.dns_public_zone_ttl
  enterprise_project_id = var.dns_public_zone_enterprise_project_id
  status                = var.dns_public_zone_status
  dnssec                = var.dns_public_zone_dnssec

  dynamic "router" {
    for_each = var.dns_public_zone_router
    content {
      router_id     = router.value.router_id
      router_region = router.value.router_region
    }
  }
}
```

**Parameter Description**:

- **name**: Domain name, assigned by referencing the input variable dns\_public\_zone\_name
- **email**: Administrator email address for managing the domain, assigned by referencing the input variable dns\_public\_zone\_email
- **zone\_type**: Domain type, assigned by referencing the input variable dns\_public\_zone\_type, defaults to "public"
- **description**: Domain description, assigned by referencing the input variable dns\_public\_zone\_description
- **ttl**: Time to live (TTL) of the domain, assigned by referencing the input variable dns\_public\_zone\_ttl, defaults to 300 seconds
- **enterprise\_project\_id**: Enterprise project ID that the domain belongs to, assigned by referencing the input variable dns\_public\_zone\_enterprise\_project\_id
- **status**: Domain status, assigned by referencing the input variable dns\_public\_zone\_status, defaults to "ENABLE"
- **dnssec**: Whether to enable DNSSEC for the public domain, assigned by referencing the input variable dns\_public\_zone\_dnssec, defaults to "DISABLE"
- **router.router\_id**: Router ID, assigned by referencing the router\_id field in the router list
- **router.router\_region**: Router region, assigned by referencing the router\_region field in the router list

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `.tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# DNS public zone configuration
dns_public_zone_name        = "tftest.yourname.com"
dns_public_zone_description = "tf_test_zone_desc"
dns_public_zone_ttl         = 3000
dns_public_zone_dnssec      = "ENABLE"
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="dns_public_zone_name=example.com" -var="dns_public_zone_description=My Domain"`
2. Environment variables: `export TF_VAR_dns_public_zone_name=example.com`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating the DNS public zone
4. Run `terraform show` to view the details of the created DNS public zone

## Reference Information

- [Huawei Cloud DNS Product Documentation](https://support.huaweicloud.com/dns/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For DNS Public Zone](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dns/zone)

# Deploy Public Zone Cross Accounts

## Application Scenario

Domain Name Service (DNS) is a highly available, high-performance domain name resolution service provided by Huawei Cloud, supporting both public and private domain name resolution. DNS service provides intelligent resolution, load balancing, health check, and other functions, helping users achieve intelligent scheduling and failover of domain names.

Cross-account public zone creation is an advanced feature in DNS service that allows one account (master account) to authorize another account (target account) to create and manage subdomains under the master account's domain. This feature is particularly useful in multi-account scenarios, such as when an organization needs to delegate subdomain management to different departments or teams while maintaining centralized control over the main domain. Through cross-account authorization, enterprises can implement hierarchical domain management, improve operational efficiency, and enhance security isolation between different accounts. This best practice will introduce how to use Terraform to automatically deploy cross-account public zone creation, including domain authorization, recordset creation, authorization verification, and subdomain zone creation.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [DNS Zones Query Data Source (data.huaweicloud\_dns\_zones)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/dns_zones)

### Resources

- [DNS Zone Authorization Resource (huaweicloud\_dns\_zone\_authorization)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dns_zone_authorization)
- [DNS Recordset Resource (huaweicloud\_dns\_recordset)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dns_recordset)
- [DNS Zone Authorization Verify Resource (huaweicloud\_dns\_zone\_authorization\_verify)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dns_zone_authorization_verify)
- [DNS Public Zone Resource (huaweicloud\_dns\_zone)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/dns_zone)

### Resource/Data Source Dependencies

```
data.huaweicloud_dns_zones.test
    └── huaweicloud_dns_zone_authorization.test

huaweicloud_dns_zone_authorization.test
    ├── huaweicloud_dns_recordset.test
    └── huaweicloud_dns_zone_authorization_verify.test

huaweicloud_dns_recordset.test
    └── huaweicloud_dns_zone_authorization_verify.test

huaweicloud_dns_zone_authorization_verify.test
    └── huaweicloud_dns_zone.test
```

## Implementation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://hcbp.gitbook.io/huaweicloud-provider/product-introduction/prepare_before_deploy) for configuration introduction.

> Note: This best practice involves cross-account operations, requiring configuration of two providers: one for the master account (domain\_master) and one for the target account. The master account provider is used to query the main domain and create recordsets, while the target account provider is used to create the subdomain zone.

### 2. Configure Providers for Cross-Account Operations

Add the following script to the TF file (such as main.tf) to configure providers for both the master account and target account:

```hcl
# Configure provider for master account (domain owner)
provider "huaweicloud" {
  alias     = "domain_master"
  region    = var.region_name
  access_key = var.access_key
  secret_key = var.secret_key
}

# Configure provider for target account (subdomain creator)
provider "huaweicloud" {
  alias     = "domain_target"
  region    = var.region_name
  access_key = var.target_account_access_key
  secret_key = var.target_account_secret_key
}
```

**Parameter Description**:

- **alias**: Provider alias, used to distinguish between master account and target account providers
- **region**: The region where resources are located, assigned by referencing the input variable `region_name`
- **access\_key**: The access key for authentication, using `var.access_key` for master account and `var.target_account_access_key` for target account
- **secret\_key**: The secret key for authentication, using `var.secret_key` for master account and `var.target_account_secret_key` for target account

> Note: The master account provider is used to query the main domain and create recordsets for authorization verification. The target account provider is used to create the subdomain zone after authorization is verified.

### 3. Query DNS Zones Information Through Data Source

Add the following script to the TF file (such as main.tf) to instruct Terraform to perform a data source query, the query results are used to create DNS zone authorization resources:

```hcl
variable "main_domain_name" {
  description = "The name of the main domain"
  type        = string
}

# Query DNS zones information that meets the conditions in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block), used to create DNS zone authorization resources
data "huaweicloud_dns_zones" "test" {
  provider = huaweicloud.domain_master

  name        = var.main_domain_name
  zone_type   = "public"
  search_mode = "equal"
}
```

**Parameter Description**:

- **provider**: The provider alias, specified as `huaweicloud.domain_master` to use the master account provider
- **name**: The name of the DNS zone, assigned by referencing the input variable `main_domain_name`
- **zone\_type**: The type of the DNS zone, set to "public" to query public zones
- **search\_mode**: The search mode, set to "equal" to perform exact match search

### 4. Create DNS Zone Authorization Resource

Add the following script to the TF file to instruct Terraform to create DNS zone authorization resources:

```hcl
variable "sub_domain_prefix" {
  description = "The prefix of the sub-domain"
  type        = string
}

# Create DNS zone authorization resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_dns_zone_authorization" "test" {
  depends_on = [data.huaweicloud_dns_zones.test]

  zone_name = format("%s.%s", var.sub_domain_prefix, try(data.huaweicloud_dns_zones.test.zones[0].name, "master_domain_not_found"))
}
```

**Parameter Description**:

- **depends\_on**: Explicit dependency declaration, ensuring that the data source query completes before creating the authorization resource
- **zone\_name**: The name of the zone to be authorized, constructed using the `format` function to combine the subdomain prefix with the main domain name

> Note: The zone authorization resource is created in the target account context, allowing the target account to manage the subdomain under the main domain.

### 5. Create DNS Recordset Resource

Add the following script to the TF file to instruct Terraform to create DNS recordset resources for authorization verification:

```hcl
variable "recordset_type" {
  description = "The type of the recordset"
  type        = string
  default     = "TXT"
}

variable "recordset_ttl" {
  description = "The time to live (TTL) of the recordset"
  type        = number
  default     = 300
}

# Create DNS recordset resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block), used for authorization verification
resource "huaweicloud_dns_recordset" "test" {
  provider = huaweicloud.domain_master

  zone_id = try(data.huaweicloud_dns_zones.test.zones[0].id, null)
  name    = format("%s.%s", try(huaweicloud_dns_zone_authorization.test.record[0].host, "host_not_found"), try(data.huaweicloud_dns_zones.test.zones[0].name, "master_domain_not_found"))
  type    = var.recordset_type
  ttl     = var.recordset_ttl
  records = ["\"${huaweicloud_dns_zone_authorization.test.record[0].value}\""]

  provisioner "local-exec" {
    command = "sleep 10"
  }
}
```

**Parameter Description**:

- **provider**: The provider alias, specified as `huaweicloud.domain_master` to use the master account provider
- **zone\_id**: The ID of the DNS zone, obtained from the queried DNS zones data source
- **name**: The name of the recordset, constructed using the `format` function to combine the host from authorization resource with the main domain name
- **type**: The type of the recordset, assigned by referencing the input variable `recordset_type`, default is "TXT"
- **ttl**: The time to live of the recordset, assigned by referencing the input variable `recordset_ttl`, default is 300 seconds
- **records**: The record values, obtained from the authorization resource, wrapped in quotes for TXT records
- **provisioner**: A local-exec provisioner that waits 10 seconds after creating the recordset to ensure DNS propagation

> Note: The recordset is created in the master account to verify the authorization. The provisioner ensures sufficient time for DNS propagation before proceeding to verification.

### 6. Create DNS Zone Authorization Verify Resource

Add the following script to the TF file to instruct Terraform to create DNS zone authorization verification resources:

```hcl
# Create DNS zone authorization verify resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block), used to verify the authorization
resource "huaweicloud_dns_zone_authorization_verify" "test" {
  depends_on = [huaweicloud_dns_recordset.test]

  authorization_id = huaweicloud_dns_zone_authorization.test.id
}
```

**Parameter Description**:

- **depends\_on**: Explicit dependency declaration, ensuring that the recordset is created before verifying the authorization
- **authorization\_id**: The ID of the DNS zone authorization resource, referenced from the authorization resource created earlier

> Note: The authorization verification checks whether the TXT record created in the master account matches the expected value. Only after successful verification can the target account create the subdomain zone.

### 7. Create DNS Public Zone Resource

Add the following script to the TF file to instruct Terraform to create DNS public zone resources:

```hcl
# Create DNS public zone resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_dns_zone" "test" {
  depends_on = [huaweicloud_dns_zone_authorization_verify.test]

  name      = format("%s.%s", var.sub_domain_prefix, try(data.huaweicloud_dns_zones.test.zones[0].name, "master_domain_not_found"))
  zone_type = "public"
}
```

**Parameter Description**:

- **depends\_on**: Explicit dependency declaration, ensuring that the authorization is verified before creating the zone
- **name**: The name of the DNS zone, constructed using the `format` function to combine the subdomain prefix with the main domain name
- **zone\_type**: The type of the DNS zone, set to "public" to create a public zone

> Note: The DNS zone is created in the target account context after successful authorization verification. The zone name must match the authorized subdomain name.

### 8. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Target account authentication configuration
target_account_access_key = "access_key_of_target_account"
target_account_secret_key = "secret_key_of_target_account"

# DNS domain configuration
main_domain_name  = "domain_name_of_target_account"
sub_domain_prefix = "dev"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command line parameters: `terraform apply -var="main_domain_name=example.com" -var="sub_domain_prefix=dev"`
2. Environment variables: `export TF_VAR_main_domain_name=example.com`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 9. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating DNS zone authorization, recordset, authorization verification, and public zone
4. Run `terraform show` to view the created DNS resource details

## Reference Information

- [Huawei Cloud DNS Product Documentation](https://support.huaweicloud.com/intl/en-us/dns/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For DNS Public Zone Cross Accounts](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dns/public-zone-cross-accounts)
