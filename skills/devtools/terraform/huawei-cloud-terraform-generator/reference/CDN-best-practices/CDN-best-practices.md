# Deploy Cache Management

## Application Scenario

Content Delivery Network (CDN) cache management is a cache refresh and preheat function provided by the CDN service, used to manage cached content on CDN nodes. Through cache refresh, you can force CDN nodes to delete specified cached content, ensuring users get the latest resources. Through cache preheat, you can pre-cache popular content to CDN nodes, improving user access speed. Automating CDN cache management through Terraform can ensure standardized and consistent cache operations, improving operational efficiency. This best practice will introduce how to use Terraform to automatically execute CDN cache refresh and preheat operations.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [CDN Cache Refresh Resource (huaweicloud\_cdn\_cache\_refresh)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cdn_cache_refresh)
- [CDN Cache Preheat Resource (huaweicloud\_cdn\_cache\_preheat)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cdn_cache_preheat)

### Resource/Data Source Dependencies

```
huaweicloud_cdn_cache_refresh
    └── huaweicloud_cdn_cache_preheat
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create CDN Cache Refresh Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a CDN cache refresh resource:

```hcl
variable "refresh_file_urls" {
  description = "The list of file URLs that need to be refreshed"
  type        = list(string)
  default     = []
  nullable    = false

  validation {
    condition     = length(var.refresh_file_urls) <= 1000
    error_message = "The refresh_file_urls list can contain up to 1000 URLs."
  }
}

variable "zh_url_encode" {
  description = "Whether to encode Chinese characters in URLs before cache refresh/preheat"
  type        = bool
  default     = false
}

variable "enterprise_project_id" {
  description = "The ID of the enterprise project to which the resource belongs"
  type        = string
  default     = "0"
}

# Create CDN cache refresh resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_cdn_cache_refresh" "test" {
  count = length(var.refresh_file_urls) > 0 ? 1 : 0

  type                  = "file"
  urls                  = var.refresh_file_urls
  mode                  = "all"
  zh_url_encode         = var.zh_url_encode
  enterprise_project_id = var.enterprise_project_id
}
```

**Parameter Description**:

- **count**: Resource creation condition, create resource when refresh\_file\_urls list is not empty
- **type**: Refresh type, set to "file" for file refresh
- **urls**: List of file URLs that need to be refreshed, assigned by referencing the input variable refresh\_file\_urls, supports up to 1000 URLs
- **mode**: Refresh mode, set to "all" to refresh the URL and all content under its directory
- **zh\_url\_encode**: Whether to encode Chinese characters in URLs, assigned by referencing the input variable zh\_url\_encode, default value is false
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing the input variable enterprise\_project\_id, default value is "0"

### 3. Create CDN Cache Preheat Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a CDN cache preheat resource:

```hcl
variable "preheat_urls" {
  description = "The list of URLs that need to be preheated"
  type        = list(string)
  default     = []
  nullable    = false

  validation {
    condition     = length(var.preheat_urls) <= 1000
    error_message = "The preheat_urls list can contain up to 1000 URLs."
  }
}

# Create CDN cache preheat resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_cdn_cache_preheat" "test" {
  count = length(var.preheat_urls) > 0 ? 1 : 0

  urls                  = var.preheat_urls
  zh_url_encode         = var.zh_url_encode
  enterprise_project_id = var.enterprise_project_id

  depends_on = [
    huaweicloud_cdn_cache_refresh.test,
  ]
}
```

**Parameter Description**:

- **count**: Resource creation condition, create resource when preheat\_urls list is not empty
- **urls**: List of URLs that need to be preheated, assigned by referencing the input variable preheat\_urls, supports up to 1000 URLs
- **zh\_url\_encode**: Whether to encode Chinese characters in URLs, assigned by referencing the input variable zh\_url\_encode, default value is false
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing the input variable enterprise\_project\_id, default value is "0"
- **depends\_on**: Explicit dependency relationship, ensuring the cache refresh resource is created before the cache preheat resource

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# CDN Cache Management Configuration
refresh_file_urls = [
  "https://example.com/index.html",
]
preheat_urls = [
  "https://example.com/index.html",
]

zh_url_encode         = false
enterprise_project_id = ""
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="refresh_file_urls=[\"https://example.com/index.html\"]" -var="preheat_urls=[\"https://example.com/index.html\"]"`
2. Environment variables: `export TF_VAR_refresh_file_urls='["https://example.com/index.html"]'` and `export TF_VAR_preheat_urls='["https://example.com/index.html"]'`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to execute CDN cache management operations:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start executing cache refresh and preheat operations
4. Run `terraform show` to view the details of the executed cache management operations

> Note: All URLs must belong to domains that are already configured in CDN. Cache refresh operations typically complete within a few minutes. Cache preheat operations may take longer depending on the number of URLs. Chinese URL encoding is useful when URLs contain Chinese characters. Enterprise project ID is required when using sub-account.

## Reference Information

- [Huawei Cloud CDN Product Documentation](https://support.huaweicloud.com/cdn/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Cache Management](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/cdn/cache-management)

# Deploy HTTPS and Cache Domain

## Application Scenario

Content Delivery Network (CDN) domain is a domain acceleration configuration function provided by the CDN service, used to provide content acceleration services for websites, downloads, videos and other businesses. By configuring a CDN domain, you can distribute origin server content to global edge nodes, improving user access speed. By configuring HTTPS, you can ensure the security of data transmission. By configuring cache rules, you can optimize cache policies and improve cache hit rates. Automating CDN domain creation through Terraform can ensure standardized and consistent domain configuration, improving operational efficiency. This best practice will introduce how to use Terraform to automatically create a CDN domain, including HTTPS and cache rule configuration.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [CDN Domain Resource (huaweicloud\_cdn\_domain)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cdn_domain)

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create CDN Domain Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a CDN domain resource:

```hcl
variable "domain_name" {
  description = "The name of the CDN domain to be accelerated"
  type        = string
}

variable "domain_type" {
  description = "The business type of the domain"
  type        = string
  default     = "web"

  validation {
    condition     = contains(["web", "download", "video", "wholeSite"], var.domain_type)
    error_message = "The domain_type must be one of: web, download, video, wholeSite."
  }
}

variable "service_area" {
  description = "The area covered by the acceleration service"
  type        = string
  default     = "mainland_china"

  validation {
    condition     = contains(["mainland_china", "outside_mainland_china", "global"], var.service_area)
    error_message = "The service_area must be one of: mainland_china, outside_mainland_china, global."
  }
}

variable "origin_server" {
  description = "The origin server address (IP address or domain name)"
  type        = string
}

variable "origin_type" {
  description = "The origin server type"
  type        = string
  default     = "ipaddr"

  validation {
    condition     = contains(["ipaddr", "domain", "obs_bucket"], var.origin_type)
    error_message = "The origin_type must be one of: ipaddr, domain, obs_bucket."
  }
}

variable "http_port" {
  description = "The HTTP port of the origin server"
  type        = number
  default     = 80
}

variable "https_port" {
  description = "The HTTPS port of the origin server"
  type        = number
  default     = 443
}

variable "origin_protocol" {
  description = "The protocol used to retrieve data from the origin server"
  type        = string
  default     = "http"

  validation {
    condition     = contains(["http", "https", "follow"], var.origin_protocol)
    error_message = "The origin_protocol must be one of: http, https, follow."
  }
}

variable "ipv6_enable" {
  description = "Whether to enable IPv6"
  type        = bool
  default     = false
}

variable "range_based_retrieval_enabled" {
  description = "Whether to enable range-based retrieval"
  type        = bool
  default     = false
}

variable "domain_description" {
  description = "The description of the CDN domain"
  type        = string
  default     = ""
}

variable "https_enabled" {
  description = "Whether to enable HTTPS"
  type        = bool
  default     = false
}

variable "certificate_name" {
  description = "The name of the SSL certificate (required when https_enabled is true)"
  type        = string
  default     = ""
  nullable    = false
}

variable "certificate_source" {
  description = "The source of the SSL certificate (required when https_enabled is true)"
  type        = string
  default     = "0"
  nullable    = false

  validation {
    condition     = contains(["0", "2"], var.certificate_source)
    error_message = "The certificate_source must be one of: 0, 2."
  }
}

variable "certificate_body_path" {
  description = "The file path to the SSL certificate (required when https_enabled is true and using custom certificate)"
  type        = string
  default     = ""
  sensitive   = false
  nullable    = false
}

variable "private_key_path" {
  description = "The file path to the private key (required when https_enabled is true and using custom certificate)"
  type        = string
  default     = ""
  sensitive   = false
  nullable    = false
}

variable "http2_enabled" {
  description = "Whether to enable HTTP/2 (only valid when https_enabled is true)"
  type        = bool
  default     = false
}

variable "ocsp_stapling_status" {
  description = "The OCSP stapling status (only valid when https_enabled is true)"
  type        = string
  default     = "off"

  validation {
    condition     = contains(["on", "off"], var.ocsp_stapling_status)
    error_message = "The ocsp_stapling_status must be one of: on, off."
  }
}

variable "cache_rules" {
  description = "The cache rules configuration"
  type        = list(object({
    rule_type           = string
    content             = string
    ttl                 = number
    ttl_type            = string
    priority            = number
    url_parameter_type  = optional(string)
    url_parameter_value = optional(string)
  }))
  default     = []
}

variable "domain_tags" {
  description = "The tags of the CDN domain"
  type        = map(string)
  default     = {}
}

# Create CDN domain resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_cdn_domain" "test" {
  name         = var.domain_name
  type         = var.domain_type
  service_area = var.service_area

  sources {
    origin      = var.origin_server
    origin_type = var.origin_type
    active      = 1
    http_port   = var.http_port
    https_port  = var.https_port
  }

  configs {
    origin_protocol               = var.origin_protocol
    ipv6_enable                   = var.ipv6_enable
    range_based_retrieval_enabled = var.range_based_retrieval_enabled
    description                   = var.domain_description

    dynamic "https_settings" {
      for_each = var.https_enabled ? [1] : []

      content {
        certificate_name     = var.https_enabled ? var.certificate_name : null
        certificate_source   = var.https_enabled ? var.certificate_source : null
        certificate_body     = var.https_enabled && var.certificate_body_path != "" ? file(var.certificate_body_path) : null
        private_key          = var.https_enabled && var.private_key_path != "" ? file(var.private_key_path) : null
        https_enabled        = var.https_enabled
        http2_enabled        = var.http2_enabled
        ocsp_stapling_status = var.ocsp_stapling_status
      }
    }
  }

  dynamic "cache_settings" {
    for_each = length(var.cache_rules) > 0 ? [var.cache_rules] : []

    content {
      dynamic "rules" {
        for_each = cache_settings.value

        content {
          rule_type           = rules.value.rule_type
          ttl                 = rules.value.ttl
          ttl_type            = rules.value.ttl_type
          priority            = rules.value.priority
          content             = rules.value.content
          url_parameter_type  = lookup(rules.value, "url_parameter_type", null)
          url_parameter_value = lookup(rules.value, "url_parameter_value", null)
        }
      }
    }
  }

  tags = var.domain_tags
}
```

**Parameter Description**:

- **name**: The accelerated domain name, assigned by referencing the input variable domain\_name
- **type**: The domain business type, assigned by referencing the input variable domain\_type, valid values: web (website acceleration), download (file download acceleration), video (on-demand acceleration), wholeSite (full-site acceleration), default value is "web"
- **service\_area**: The service coverage area, assigned by referencing the input variable service\_area, valid values: mainland\_china (mainland China), outside\_mainland\_china (outside mainland China), global (global), default value is "mainland\_china"
- **sources.origin**: The origin server address, assigned by referencing the input variable origin\_server, can be an IP address or domain name
- **sources.origin\_type**: The origin server type, assigned by referencing the input variable origin\_type, valid values: ipaddr (IP address), domain (domain name), obs\_bucket (OBS bucket domain), default value is "ipaddr"
- **sources.active**: The primary/standby status, set to 1 for primary origin server
- **sources.http\_port**: The origin server HTTP port, assigned by referencing the input variable http\_port, default value is 80
- **sources.https\_port**: The origin server HTTPS port, assigned by referencing the input variable https\_port, default value is 443
- **configs.origin\_protocol**: The origin protocol, assigned by referencing the input variable origin\_protocol, valid values: http, https, follow (follow), default value is "http"
- **configs.ipv6\_enable**: Whether to enable IPv6, assigned by referencing the input variable ipv6\_enable, default value is false
- **configs.range\_based\_retrieval\_enabled**: Whether to enable Range-based retrieval, assigned by referencing the input variable range\_based\_retrieval\_enabled, default value is false
- **configs.description**: The domain description, assigned by referencing the input variable domain\_description, default value is empty string
- **configs.https\_settings.certificate\_name**: The certificate name, assigned by referencing the input variable certificate\_name when https\_enabled is true
- **configs.https\_settings.certificate\_source**: The certificate source, assigned by referencing the input variable certificate\_source when https\_enabled is true, valid values: 0 (Huawei Cloud managed certificate), 2 (custom certificate), default value is "0"
- **configs.https\_settings.certificate\_body**: The certificate content, read from certificate\_body\_path file using file function when https\_enabled is true and using custom certificate
- **configs.https\_settings.private\_key**: The private key content, read from private\_key\_path file using file function when https\_enabled is true and using custom certificate
- **configs.https\_settings.https\_enabled**: Whether to enable HTTPS, assigned by referencing the input variable https\_enabled, default value is false
- **configs.https\_settings.http2\_enabled**: Whether to enable HTTP/2, assigned by referencing the input variable http2\_enabled, only valid when https\_enabled is true, default value is false
- **configs.https\_settings.ocsp\_stapling\_status**: The OCSP stapling status, assigned by referencing the input variable ocsp\_stapling\_status, only valid when https\_enabled is true, valid values: on (enabled), off (disabled), default value is "off"
- **cache\_settings.rules.rule\_type**: The cache rule type, valid values: all (all files), file\_extension (file extension), catalog (directory), full\_path (full path), home\_page (homepage)
- **cache\_settings.rules.content**: The cache rule matching content, set different matching content according to rule\_type
- **cache\_settings.rules.ttl**: The cache time, in the unit specified by ttl\_type, maximum cache time is 365 days
- **cache\_settings.rules.ttl\_type**: The cache time unit, valid values: s (second), m (minute), h (hour), d (day)
- **cache\_settings.rules.priority**: The cache rule priority, larger value indicates higher priority, value range is 1-100, weight values must be unique
- **cache\_settings.rules.url\_parameter\_type**: The URL parameter type, valid values: del\_params (ignore specified URL parameters), reserve\_params (retain specified URL parameters), ignore\_url\_params (ignore all URL parameters), full\_url (retain all URL parameters), default value is "full\_url"
- **cache\_settings.rules.url\_parameter\_value**: The URL parameter values, multiple parameters separated by commas, up to 10 parameters can be set, required when url\_parameter\_type is del\_params or reserve\_params
- **tags**: The domain tags, assigned by referencing the input variable domain\_tags, default value is empty map

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Domain Configuration
domain_name                   = "example.com"
domain_type                   = "web"
service_area                  = "outside_mainland_china"
origin_protocol               = "https"
origin_type                   = "domain"
origin_server                 = "hostaddress"
http_port                     = 80
https_port                    = 443
ipv6_enable                   = false
range_based_retrieval_enabled = false
domain_description            = "CDN domain for example.com"

# HTTPS Configuration
https_enabled                 = true
certificate_name              = "terraform_test_cert"
certificate_source            = "0"
certificate_body_path         = "/path/to/your/certificate.crt"
private_key_path              = "/path/to/your/private.key"
http2_enabled                 = true
ocsp_stapling_status          = "on"

# Cache Rules Configuration
cache_rules = [
  {
    rule_type          = "all"
    content            = ""
    ttl                = 2592000
    ttl_type           = "s"
    priority           = 1
    url_parameter_type = "full_url"
  },
  {
    rule_type          = "file_extension"
    content            = ".php;.jsp;.asp;.aspx"
    ttl                = 2592000
    ttl_type           = "s"
    priority           = 2
    url_parameter_type = "full_url"
  }
]

domain_tags = {
  Environment = "production"
  Project     = "cdn-example"
}
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="domain_name=example.com" -var="origin_server=192.168.1.100"`
2. Environment variables: `export TF_VAR_domain_name=example.com` and `export TF_VAR_origin_server=192.168.1.100`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create a CDN domain:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the CDN domain
4. Run `terraform show` to view the details of the created CDN domain

> Note: CDN domain creation may take a few minutes to complete. Before updating the domain configuration, please ensure that the status value is **online**. The service area cannot be changed between mainland China and outside mainland China. SSL certificate files should be kept secure and never committed to version control. Cache rules are processed in priority order (smaller number = higher priority). Domain names must be unique within your Huawei Cloud account.

## Reference Information

- [Huawei Cloud CDN Product Documentation](https://support.huaweicloud.com/cdn/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For HTTPS and Cache Domain](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/cdn/domain-with-https-and-cache)

# Deploy Rule Engine

## Application Scenario

Content Delivery Network (CDN) rule engine is a flexible rule configuration function provided by the CDN service, used to execute corresponding actions based on different request conditions, achieving fine-grained CDN acceleration control. By configuring the rule engine, you can match requests based on conditions such as path, parameters, request headers, etc., and execute various actions such as cache rules, access control, URL rewriting, flexible origin, etc., to meet the acceleration needs of different business scenarios. Automating CDN rule engine configuration through Terraform can ensure standardized and consistent rule configuration, improving operational efficiency. This best practice will introduce how to use Terraform to automatically configure CDN rule engine rules.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [CDN Rule Engine Rule Resource (huaweicloud\_cdn\_rule\_engine\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/cdn_rule_engine_rule)

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create CDN Rule Engine Rule Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a CDN rule engine rule resource:

```hcl
variable "domain_name" {
  description = "The accelerated domain name to which the rule engine rule belongs"
  type        = string
}

variable "rule_name" {
  description = "The name of the rule engine rule"
  type        = string
}

variable "rule_status" {
  description = "Whether to enable the rule engine rule"
  type        = string
  default     = "on"

  validation {
    condition     = contains(["on", "off"], var.rule_status)
    error_message = "The rule_status must be one of: on, off."
  }
}

variable "rule_priority" {
  description = "The priority of the rule engine rule"
  type        = number
  default     = 1
}

variable "conditions" {
  description = "The trigger conditions of the rule engine rule, in JSON format"
  type        = string
  default     = ""
}

variable "cache_rule" {
  description = "The cache rule configuration"
  type = object({
    ttl           = number
    ttl_unit      = string
    follow_origin = optional(string)
    force_cache   = optional(string)
  })
  default = null
}

variable "access_control" {
  description = "The access control configuration"
  type = object({
    type = string
  })
  default = null
}

variable "http_response_headers" {
  description = "The list of HTTP response header configurations"
  type = list(object({
    name   = string
    value  = string
    action = string
  }))
  default = []
}

variable "browser_cache_rule" {
  description = "The browser cache rule configuration"
  type = object({
    cache_type = string
  })
  default = null
}

variable "request_url_rewrite" {
  description = "The access URL rewrite configuration"
  type = object({
    execution_mode = string
    redirect_url   = string
  })
  default = null
}

variable "flexible_origins" {
  description = "The list of flexible origin configurations"
  type = list(object({
    sources_type      = string
    ip_or_domain      = string
    priority          = number
    weight            = number
    http_port         = optional(number)
    https_port        = optional(number)
    origin_protocol   = optional(string)
    host_name         = optional(string)
    obs_bucket_type   = optional(string)
    bucket_access_key = optional(string)
    bucket_secret_key = optional(string)
    bucket_region     = optional(string)
    bucket_name       = optional(string)
  }))
  default = []
}

variable "origin_request_headers" {
  description = "The list of origin request header configurations"
  type = list(object({
    action = string
    name   = string
    value  = optional(string)
  }))
  default = []
}

variable "origin_request_url_rewrite" {
  description = "The origin request URL rewrite configuration"
  type = object({
    rewrite_type = string
    target_url   = string
  })
  default = null
}

variable "origin_range" {
  description = "The origin range configuration"
  type = object({
    status = string
  })
  default = null
}

variable "request_limit_rule" {
  description = "The request rate limit configuration"
  type = object({
    limit_rate_after = number
    limit_rate_value = number
  })
  default = null
}

variable "error_code_cache" {
  description = "The list of error code cache configurations"
  type = list(object({
    code = number
    ttl  = number
  }))
  default = []
}

# Create CDN rule engine rule resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_cdn_rule_engine_rule" "test" {
  domain_name = var.domain_name
  name        = var.rule_name
  status      = var.rule_status
  priority    = var.rule_priority
  conditions  = var.conditions != "" ? var.conditions : null

  dynamic "actions" {
    for_each = var.cache_rule != null ? [var.cache_rule] : []

    content {
      cache_rule {
        ttl           = actions.value.ttl
        ttl_unit      = actions.value.ttl_unit
        follow_origin = lookup(actions.value, "follow_origin", null)
        force_cache   = lookup(actions.value, "force_cache", null)
      }
    }
  }

  dynamic "actions" {
    for_each = var.access_control != null ? [var.access_control] : []

    content {
      access_control {
        type = actions.value.type
      }
    }
  }

  dynamic "actions" {
    for_each = length(var.http_response_headers) > 0 ? var.http_response_headers : []

    content {
      http_response_header {
        name   = actions.value.name
        value  = actions.value.value
        action = actions.value.action
      }
    }
  }

  dynamic "actions" {
    for_each = var.browser_cache_rule != null ? [var.browser_cache_rule] : []

    content {
      browser_cache_rule {
        cache_type = actions.value.cache_type
      }
    }
  }

  dynamic "actions" {
    for_each = var.request_url_rewrite != null ? [var.request_url_rewrite] : []

    content {
      request_url_rewrite {
        execution_mode = actions.value.execution_mode
        redirect_url   = actions.value.redirect_url
      }
    }
  }

  dynamic "actions" {
    for_each = length(var.flexible_origins) > 0 ? var.flexible_origins : []

    content {
      flexible_origin {
        sources_type      = actions.value.sources_type
        ip_or_domain      = actions.value.ip_or_domain
        priority          = actions.value.priority
        weight            = actions.value.weight
        http_port         = lookup(actions.value, "http_port", null)
        https_port        = lookup(actions.value, "https_port", null)
        origin_protocol   = lookup(actions.value, "origin_protocol", null)
        host_name         = lookup(actions.value, "host_name", null)
        obs_bucket_type   = lookup(actions.value, "obs_bucket_type", null)
        bucket_access_key = lookup(actions.value, "bucket_access_key", null)
        bucket_secret_key = lookup(actions.value, "bucket_secret_key", null)
        bucket_region     = lookup(actions.value, "bucket_region", null)
        bucket_name       = lookup(actions.value, "bucket_name", null)
      }
    }
  }

  dynamic "actions" {
    for_each = length(var.origin_request_headers) > 0 ? var.origin_request_headers : []

    content {
      origin_request_header {
        action = actions.value.action
        name   = actions.value.name
        value  = lookup(actions.value, "value", null)
      }
    }
  }

  dynamic "actions" {
    for_each = var.origin_request_url_rewrite != null ? [var.origin_request_url_rewrite] : []

    content {
      origin_request_url_rewrite {
        rewrite_type = actions.value.rewrite_type
        target_url   = actions.value.target_url
      }
    }
  }

  dynamic "actions" {
    for_each = var.origin_range != null ? [var.origin_range] : []

    content {
      origin_range {
        status = actions.value.status
      }
    }
  }

  dynamic "actions" {
    for_each = var.request_limit_rule != null ? [var.request_limit_rule] : []

    content {
      request_limit_rule {
        limit_rate_after = actions.value.limit_rate_after
        limit_rate_value = actions.value.limit_rate_value
      }
    }
  }

  dynamic "actions" {
    for_each = length(var.error_code_cache) > 0 ? var.error_code_cache : []

    content {
      error_code_cache {
        code = actions.value.code
        ttl  = actions.value.ttl
      }
    }
  }

  lifecycle {
    ignore_changes = [
      conditions,
    ]
  }
}
```

**Parameter Description**:

- **domain\_name**: The accelerated domain name to which the rule belongs, assigned by referencing the input variable domain\_name
- **name**: The rule name, assigned by referencing the input variable rule\_name, length is 1-50 characters
- **status**: Whether to enable the rule, assigned by referencing the input variable rule\_status, valid values: on (enabled), off (disabled), default value is "on"
- **priority**: The rule priority, assigned by referencing the input variable rule\_priority, value range is 1-100, default value is 1
- **conditions**: The rule trigger conditions, assigned by referencing the input variable conditions, JSON format string, default value is empty string
- **actions.cache\_rule**: Cache rule action, configured when cache\_rule is not null
  - **ttl**: Cache time
  - **ttl\_unit**: Cache time unit
  - **follow\_origin**: Whether to follow origin server
  - **force\_cache**: Whether to force cache
- **actions.access\_control**: Access control action, configured when access\_control is not null
  - **type**: Access control type
- **actions.http\_response\_header**: HTTP response header action, configured when http\_response\_headers list is not empty
  - **name**: Response header name
  - **value**: Response header value
  - **action**: Action type
- **actions.browser\_cache\_rule**: Browser cache rule action, configured when browser\_cache\_rule is not null
  - **cache\_type**: Cache type
- **actions.request\_url\_rewrite**: Request URL rewrite action, configured when request\_url\_rewrite is not null
  - **execution\_mode**: Execution mode
  - **redirect\_url**: Redirect URL
- **actions.flexible\_origin**: Flexible origin action, configured when flexible\_origins list is not empty
  - **sources\_type**: Origin server type
  - **ip\_or\_domain**: IP address or domain name
  - **priority**: Priority
  - **weight**: Weight
  - **http\_port**: HTTP port
  - **https\_port**: HTTPS port
  - **origin\_protocol**: Origin protocol
  - **host\_name**: Origin Host
  - **obs\_bucket\_type**: OBS bucket type
  - **bucket\_access\_key**: OBS bucket access key
  - **bucket\_secret\_key**: OBS bucket secret key
  - **bucket\_region**: OBS bucket region
  - **bucket\_name**: OBS bucket name
- **actions.origin\_request\_header**: Origin request header action, configured when origin\_request\_headers list is not empty
  - **action**: Action type
  - **name**: Request header name
  - **value**: Request header value
- **actions.origin\_request\_url\_rewrite**: Origin request URL rewrite action, configured when origin\_request\_url\_rewrite is not null
  - **rewrite\_type**: Rewrite type
  - **target\_url**: Target URL
- **actions.origin\_range**: Origin Range action, configured when origin\_range is not null
  - **status**: Status
- **actions.request\_limit\_rule**: Request rate limit action, configured when request\_limit\_rule is not null
  - **limit\_rate\_after**: Rate limit start value
  - **limit\_rate\_value**: Rate limit value
- **actions.error\_code\_cache**: Error code cache action, configured when error\_code\_cache list is not empty
  - **code**: Error code
  - **ttl**: Cache time

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Rule Engine Rule Configuration
domain_name   = "example.com"
rule_name     = "test-rule-engine"
rule_status   = "on"
rule_priority = 1

# Conditions Configuration (JSON format)
conditions = <<-JSON
{
  "match": {
    "logic": "and",
    "criteria": [
      {
        "match_target_type": "path",
        "match_type": "contains",
        "match_pattern": ["/api/"],
        "negate": false,
        "case_sensitive": true
      }
    ]
  }
}
JSON

# Origin Request URL Rewrite
origin_request_url_rewrite = {
  rewrite_type = "simple"
  target_url   = "/api/v2"
}

# Cache Rule Configuration
cache_rule = {
  ttl           = 10
  ttl_unit      = "m"
  follow_origin = "min_ttl"
  force_cache   = "off"
}

# Access Control Configuration
access_control = {
  type = "trust"
}

# Browser Cache Rule
browser_cache_rule = {
  cache_type = "follow_origin"
}

# Request URL Rewrite
request_url_rewrite = {
  execution_mode = "break"
  redirect_url   = "/new-path"
}

# Origin Range
origin_range = {
  status = "on"
}

# Request Limit Rule
request_limit_rule = {
  limit_rate_after = 2
  limit_rate_value = 1048576
}

# Origin Request Headers
origin_request_headers = [
  {
    action = "set"
    name   = "X-Real-IP"
    value  = "$realip_from_header"
  }
]

# Flexible Origins
flexible_origins = [
  {
    sources_type    = "domain"
    ip_or_domain    = "target.domain.com"
    priority        = 1
    weight          = 10
    http_port       = 80
    https_port      = 443
    origin_protocol = "follow"
    host_name       = "target.domain.com"
  }
]

# HTTP Response Headers
http_response_headers = [
  {
    name   = "Access-Control-Allow-Origin"
    value  = "*"
    action = "set"
  }
]

# Error Code Cache
error_code_cache = [
  {
    code = 400
    ttl  = 60
  }
]
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="domain_name=example.com" -var="rule_name=test-rule"`
2. Environment variables: `export TF_VAR_domain_name=example.com` and `export TF_VAR_rule_name=test-rule`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create a CDN rule engine rule:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the rule engine rule
4. Run `terraform show` to view the details of the created rule engine rule

> Note: Rule engine rules are processed in priority order. Each action type must be declared in a separate actions block. Conditions are specified in JSON format and must follow the API specification. Domain names cannot be updated after creation. Rule priority must be unique within the same domain. Flexible origin configurations support multiple origin types: ipaddr, domain, obs\_bucket, third\_bucket. Error code caching can help reduce origin server load for frequently occurring errors.

## Reference Information

- [Huawei Cloud CDN Product Documentation](https://support.huaweicloud.com/cdn/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Rule Engine](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/cdn/rule-engine)
