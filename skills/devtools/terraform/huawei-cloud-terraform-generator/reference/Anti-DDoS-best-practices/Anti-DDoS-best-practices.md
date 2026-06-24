# Deploy Basic Protection

## Application Scenario

Anti-DDoS (Anti-Distributed Denial of Service) is a distributed denial-of-service attack protection service provided by Huawei Cloud, which can effectively protect public IPs from DDoS attacks and ensure stable business operations. Anti-DDoS Basic Protection provides free DDoS attack protection capabilities for Huawei Cloud users. When a DDoS attack is detected, the system will automatically start traffic cleaning, filter out attack traffic, and only forward normal traffic to the origin server.

This best practice will introduce how to use Terraform to automatically deploy Anti-DDoS Basic Protection, including creating Elastic IP (EIP), Simple Message Notification (SMN) topics and subscriptions, and configuring Anti-DDoS Basic Protection.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [Elastic IP Resource (huaweicloud\_vpc\_eip)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/vpc_eip)
- [Simple Message Notification Topic Resource (huaweicloud\_smn\_topic)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/smn_topic)
- [Simple Message Notification Subscription Resource (huaweicloud\_smn\_subscription)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/smn_subscription)
- [Anti-DDoS Basic Protection Resource (huaweicloud\_antiddos\_basic)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/antiddos_basic)

### Resource/Data Source Dependencies

```
huaweicloud_vpc_eip
    └── huaweicloud_antiddos_basic

huaweicloud_smn_topic
    ├── huaweicloud_smn_subscription
    └── huaweicloud_antiddos_basic
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create Elastic IP Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an Elastic IP resource:

```hcl
variable "vpc_eip_publicip_type" {
  description = "The EIP type"
  type        = string
}

variable "vpc_eip_bandwidth_share_type" {
  description = "The bandwidth share type"
  type        = string
}

variable "vpc_eip_bandwidth_name" {
  description = "The bandwidth name"
  type        = string
  default     = null
}

variable "vpc_eip_bandwidth_size" {
  description = "The bandwidth size"
  type        = number
  default     = null
}

variable "vpc_eip_bandwidth_charge_mode" {
  description = "The bandwidth charge mode"
  type        = string
  default     = null
}

# Create Elastic IP resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_vpc_eip" "test" {
  publicip {
    type = var.vpc_eip_publicip_type
  }

  bandwidth {
    share_type  = var.vpc_eip_bandwidth_share_type
    name        = var.vpc_eip_bandwidth_name
    size        = var.vpc_eip_bandwidth_size
    charge_mode = var.vpc_eip_bandwidth_charge_mode
  }
}
```

**Parameter Description**:

- **publicip.type**: The type of Elastic IP, assigned by referencing the input variable vpc\_eip\_publicip\_type
- **bandwidth.share\_type**: The bandwidth sharing type, assigned by referencing the input variable vpc\_eip\_bandwidth\_share\_type
- **bandwidth.name**: The bandwidth name, assigned by referencing the input variable vpc\_eip\_bandwidth\_name, default value is null
- **bandwidth.size**: The bandwidth size, assigned by referencing the input variable vpc\_eip\_bandwidth\_size, default value is null
- **bandwidth.charge\_mode**: The bandwidth billing mode, assigned by referencing the input variable vpc\_eip\_bandwidth\_charge\_mode, default value is null

### 3. Create Simple Message Notification Topic Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a Simple Message Notification topic resource:

```hcl
variable "smn_topic_name" {
  description = "The name of the topic to be created"
  type        = string
}

variable "smn_topic_display_name" {
  description = "The topic display name"
  type        = string
  default     = null
}

# Create Simple Message Notification topic resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_smn_topic" "test" {
  name         = var.smn_topic_name
  display_name = var.smn_topic_display_name
}
```

**Parameter Description**:

- **name**: The topic name, assigned by referencing the input variable smn\_topic\_name
- **display\_name**: The topic display name, assigned by referencing the input variable smn\_topic\_display\_name, default value is null

### 4. Create Simple Message Notification Subscription Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a Simple Message Notification subscription resource:

```hcl
variable "smn_subscription_endpoint" {
  description = "The message endpoint"
  type        = string
}

variable "smn_subscription_protocol" {
  description = "The protocol of the message endpoint"
  type        = string
}

variable "smn_subscription_remark" {
  description = "The remark information"
  type        = string
  default     = null
}

# Create Simple Message Notification subscription resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_smn_subscription" "test" {
  topic_urn = huaweicloud_smn_topic.test.id
  endpoint  = var.smn_subscription_endpoint
  protocol  = var.smn_subscription_protocol
  remark    = var.smn_subscription_remark
}
```

**Parameter Description**:

- **topic\_urn**: The URN of the topic, referencing the ID of the previously created Simple Message Notification topic resource (huaweicloud\_smn\_topic.test)
- **endpoint**: The message receiving endpoint address, assigned by referencing the input variable smn\_subscription\_endpoint
- **protocol**: The protocol of the message receiving endpoint, assigned by referencing the input variable smn\_subscription\_protocol
- **remark**: The remark information, assigned by referencing the input variable smn\_subscription\_remark, default value is null

### 5. Create Anti-DDoS Basic Protection Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an Anti-DDoS Basic Protection resource:

```hcl
variable "antiddos_traffic_threshold" {
  description = "The traffic cleaning threshold in Mbps"
  type        = number
}

# Create Anti-DDoS Basic Protection resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_antiddos_basic" "test" {
  traffic_threshold = var.antiddos_traffic_threshold
  eip_id            = huaweicloud_vpc_eip.test.id
  topic_urn         = huaweicloud_smn_topic.test.id
}
```

**Parameter Description**:

- **traffic\_threshold**: The traffic cleaning threshold (unit: Mbps), assigned by referencing the input variable antiddos\_traffic\_threshold
- **eip\_id**: The ID of the Elastic IP to be protected, referencing the ID of the previously created Elastic IP resource (huaweicloud\_vpc\_eip.test)
- **topic\_urn**: The URN of the Simple Message Notification topic, referencing the ID of the previously created Simple Message Notification topic resource (huaweicloud\_smn\_topic.test)

### 6. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Elastic IP Configuration
vpc_eip_publicip_type         = "5_bgp"
vpc_eip_bandwidth_share_type  = "PER"
vpc_eip_bandwidth_name        = "test-antiddos-basic-name"
vpc_eip_bandwidth_size        = 5
vpc_eip_bandwidth_charge_mode = "traffic"

# Simple Message Notification Topic Configuration
smn_topic_name         = "test-antiddos-basic-name"
smn_topic_display_name = "The display name of topic test-antiddos-basic-name"

# Simple Message Notification Subscription Configuration
smn_subscription_endpoint = "mailtest@gmail.com"
smn_subscription_protocol = "email"
smn_subscription_remark   = "test remark"

# Anti-DDoS Basic Protection Configuration
antiddos_traffic_threshold = 200
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="vpc_eip_publicip_type=5_bgp" -var="smn_topic_name=test-topic"`
2. Environment variables: `export TF_VAR_vpc_eip_publicip_type=5_bgp`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 7. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating Anti-DDoS Basic Protection
4. Run `terraform show` to view the details of the created Anti-DDoS Basic Protection

## Reference Information

- [Huawei Cloud Anti-DDoS Product Documentation](https://support.huaweicloud.com/antiddos/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Anti-DDoS Basic Protection](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/antiddos/basic)

# Deploy Default Protection Policy

## Application Scenario

Anti-DDoS (Anti-Distributed Denial of Service) is a distributed denial-of-service attack protection service provided by Huawei Cloud, which can effectively protect public IPs from DDoS attacks and ensure stable business operations. The Anti-DDoS default protection policy is a global protection policy that applies to all EIPs in the account. When a DDoS attack is detected, the system will automatically start traffic cleaning based on the configured traffic threshold, filter out attack traffic, and only forward normal traffic to the origin server.

This best practice will introduce how to use Terraform to automatically deploy an Anti-DDoS default protection policy, which provides a unified protection configuration for all EIPs in your account.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [Anti-DDoS Default Protection Policy Resource (huaweicloud\_antiddos\_default\_protection\_policy)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/antiddos_default_protection_policy)

### Resource/Data Source Dependencies

```
huaweicloud_antiddos_default_protection_policy
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create Anti-DDoS Default Protection Policy Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an Anti-DDoS default protection policy resource:

```hcl
variable "antiddos_traffic_threshold" {
  description = "The traffic cleaning threshold in Mbps"
  type        = number
}

# Create Anti-DDoS default protection policy resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_antiddos_default_protection_policy" "test" {
  traffic_threshold = var.antiddos_traffic_threshold
}
```

**Parameter Description**:

- **traffic\_threshold**: The traffic cleaning threshold (unit: Mbps), assigned by referencing the input variable antiddos\_traffic\_threshold. When the inbound traffic of an EIP exceeds this threshold, the system will automatically start traffic cleaning.

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, the resource uses input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Anti-DDoS Default Protection Policy Configuration
antiddos_traffic_threshold = 200
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="antiddos_traffic_threshold=200"`
2. Environment variables: `export TF_VAR_antiddos_traffic_threshold=200`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the Anti-DDoS default protection policy
4. Run `terraform show` to view the details of the created Anti-DDoS default protection policy

## Reference Information

- [Huawei Cloud Anti-DDoS Product Documentation](https://support.huaweicloud.com/antiddos/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Anti-DDoS Default Protection Policy](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/antiddos/default-protection-policy)

# Deploy LTS Configuration

## Application Scenario

Anti-DDoS (Anti-Distributed Denial of Service) is a distributed denial-of-service attack protection service provided by Huawei Cloud, which can effectively protect public IPs from DDoS attacks and ensure stable business operations. By configuring the integration between Anti-DDoS and Log Tank Service (LTS), Anti-DDoS attack logs can be transmitted to LTS in real-time, facilitating log analysis, auditing, and monitoring. LTS configuration helps users centrally manage and analyze Anti-DDoS protection logs, enabling timely detection and response to security threats.

This best practice will introduce how to use Terraform to automatically deploy Anti-DDoS LTS configuration, including creating LTS log groups, log streams, and configuring the integration between Anti-DDoS and LTS.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [Log Tank Service Log Group Resource (huaweicloud\_lts\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lts_group)
- [Log Tank Service Log Stream Resource (huaweicloud\_lts\_stream)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lts_stream)
- [Anti-DDoS LTS Configuration Resource (huaweicloud\_antiddos\_lts\_config)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/antiddos_lts_config)

### Resource/Data Source Dependencies

```
huaweicloud_lts_group
    └── huaweicloud_lts_stream
        └── huaweicloud_antiddos_lts_config
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create Log Tank Service Log Group Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a Log Tank Service log group resource:

```hcl
variable "lts_group_name" {
  description = "The name of the LTS group"
  type        = string
}

variable "lts_ttl_in_days" {
  description = "The log expiration time(days)"
  type        = number
}

variable "enterprise_project_id" {
  description = "The enterprise project ID"
  type        = string
  default     = null
}

# Create Log Tank Service log group resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_lts_group" "test" {
  group_name            = var.lts_group_name
  ttl_in_days           = var.lts_ttl_in_days
  enterprise_project_id = var.enterprise_project_id
}
```

**Parameter Description**:

- **group\_name**: The log group name, assigned by referencing the input variable lts\_group\_name
- **ttl\_in\_days**: The log retention time (unit: days), assigned by referencing the input variable lts\_ttl\_in\_days
- **enterprise\_project\_id**: The enterprise project ID, assigned by referencing the input variable enterprise\_project\_id, default value is null

### 3. Create Log Tank Service Log Stream Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a Log Tank Service log stream resource:

```hcl
variable "lts_stream_name" {
  description = "The name of the LTS stream"
  type        = string
}

variable "lts_is_favorite" {
  description = "Whether to favorite the log stream"
  type        = bool
  default     = false
}

# Create Log Tank Service log stream resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_lts_stream" "test" {
  group_id              = huaweicloud_lts_group.test.id
  stream_name           = var.lts_stream_name
  is_favorite           = var.lts_is_favorite
  enterprise_project_id = var.enterprise_project_id
}
```

**Parameter Description**:

- **group\_id**: The log group ID, referencing the ID of the previously created Log Tank Service log group resource (huaweicloud\_lts\_group.test)
- **stream\_name**: The log stream name, assigned by referencing the input variable lts\_stream\_name
- **is\_favorite**: Whether to favorite the log stream, assigned by referencing the input variable lts\_is\_favorite, default value is false
- **enterprise\_project\_id**: The enterprise project ID, assigned by referencing the input variable enterprise\_project\_id, default value is null

### 4. Create Anti-DDoS LTS Configuration Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an Anti-DDoS LTS configuration resource:

```hcl
# Create Anti-DDoS LTS configuration resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_antiddos_lts_config" "test" {
  lts_group_id          = huaweicloud_lts_group.test.id
  lts_attack_stream_id  = huaweicloud_lts_stream.test.id
  enterprise_project_id = var.enterprise_project_id
}
```

**Parameter Description**:

- **lts\_group\_id**: The LTS log group ID, referencing the ID of the previously created Log Tank Service log group resource (huaweicloud\_lts\_group.test)
- **lts\_attack\_stream\_id**: The LTS attack log stream ID, referencing the ID of the previously created Log Tank Service log stream resource (huaweicloud\_lts\_stream.test)
- **enterprise\_project\_id**: The enterprise project ID, assigned by referencing the input variable enterprise\_project\_id, default value is null

### 5. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Log Tank Service Log Group Configuration
lts_group_name  = "test-lts-group-name"
lts_ttl_in_days = 7

# Log Tank Service Log Stream Configuration
lts_stream_name = "test-lts-stream-name"
lts_is_favorite = true

# Enterprise Project Configuration
enterprise_project_id = "0"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="lts_group_name=test-group" -var="lts_stream_name=test-stream"`
2. Environment variables: `export TF_VAR_lts_group_name=test-group`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 6. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the Anti-DDoS LTS configuration
4. Run `terraform show` to view the details of the created Anti-DDoS LTS configuration

## Reference Information

- [Huawei Cloud Anti-DDoS Product Documentation](https://support.huaweicloud.com/antiddos/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Anti-DDoS LTS Configuration](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/antiddos/lts-config)
