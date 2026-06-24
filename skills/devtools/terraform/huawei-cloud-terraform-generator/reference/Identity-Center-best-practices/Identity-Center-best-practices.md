# Deploy Group

## Application Scenario

Identity Center is a unified identity management service provided by Huawei Cloud, supporting unified identity authentication and authorization management across clouds and applications. By creating groups, you can group multiple users for management, uniformly configure permission policies, perform access control, and conduct identity management, improving the efficiency and convenience of identity management. This best practice will introduce how to use Terraform to automatically deploy Identity Center groups, including querying or creating Identity Center instances, registering regions (optional), and creating groups.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Identity Center Instance Data Source (huaweicloud\_identitycenter\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/identitycenter_instance)

### Resources

- [Identity Center Registered Region Resource (huaweicloud\_identitycenter\_registered\_region)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/identitycenter_registered_region)
- [Identity Center Instance Resource (huaweicloud\_identitycenter\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/identitycenter_instance)
- [Identity Center Group Resource (huaweicloud\_identitycenter\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/identitycenter_group)

### Resource/Data Source Dependencies

```
huaweicloud_identitycenter_registered_region
    └── huaweicloud_identitycenter_instance
        └── huaweicloud_identitycenter_group

data.huaweicloud_identitycenter_instance
    └── huaweicloud_identitycenter_group
```

> Note: Identity Center group resource depends on Identity Center instance. If the instance does not exist, you need to create the instance first; if the instance already exists, you can query instance information through data source. When creating an instance, if you need to use it in a specific region, you may need to register the region first.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Identity Center Instance Data Source (Optional)

Add the following script to the TF file (e.g., main.tf) to query Identity Center instance information (when the instance already exists):

```hcl
variable "is_instance_create" {
  description = "Whether to create the identity center instance"
  type        = bool
  default     = true
}

# Get Identity Center instance information in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block), used for creating groups
data "huaweicloud_identitycenter_instance" "test" {
  count = var.is_instance_create ? 0 : 1
}
```

**Parameter Description**:

- **count**: The number of data source creations, used to control whether to execute Identity Center instance query data source, only creates the data source (i.e., executes Identity Center instance query) when `var.is_instance_create` is false

### 3. Create Identity Center Registered Region Resource (Optional)

Add the following script to the TF file (e.g., main.tf) to register region (when instance needs to be created and region needs to be registered):

```hcl
variable "is_region_need_register" {
  description = "Whether to register the region"
  type        = bool
  default     = true
}

variable "region_name" {
  description = "The region where the LTS service is located"
  type        = string
}

# Create Identity Center registered region resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_identitycenter_registered_region" "test" {
  count = var.is_instance_create ? var.is_region_need_register ? 1 : 0 : 0

  region_id = var.region_name
}
```

**Parameter Description**:

- **count**: Number of resource creations, used to control whether to create registered region resource, only creates when instance needs to be created and region needs to be registered
- **region\_id**: Region ID, assigned by referencing input variable region\_name

### 4. Create Identity Center Instance Resource (Optional)

Add the following script to the TF file (e.g., main.tf) to create Identity Center instance (when the instance does not exist):

```hcl
variable "instance_store_id_alias" {
  description = "The alias of the identity center instance"
  type        = string
  default     = ""
}

# Create Identity Center instance resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_identitycenter_instance" "test" {
  count = var.is_instance_create ? 1 : 0

  depends_on = [huaweicloud_identitycenter_registered_region.test]

  alias = var.instance_store_id_alias != "" ? var.instance_store_id_alias : null
}
```

**Parameter Description**:

- **count**: Number of resource creations, used to control whether to create Identity Center instance resource, only creates when `var.is_instance_create` is true
- **depends\_on**: Explicit dependency relationship, ensuring instance is created after registered region resource is created
- **alias**: Instance alias, assigned by referencing input variable instance\_store\_id\_alias, optional parameter, default value is null

### 5. Create Identity Center Group Resource

Add the following script to the TF file (e.g., main.tf) to create Identity Center group:

```hcl
variable "group_name" {
  description = "The name of the identity center group"
  type        = string
}

variable "group_description" {
  description = "The description of the identity center group"
  type        = string
  default     = ""
}

# Create Identity Center group resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_identitycenter_group" "test" {
  identity_store_id = var.is_instance_create ? huaweicloud_identitycenter_instance.test[0].identity_store_id : data.huaweicloud_identitycenter_instance.test[0].identity_store_id
  name              = var.group_name
  description       = var.group_description
}
```

**Parameter Description**:

- **identity\_store\_id**: Identity store ID, assigned by referencing Identity Center instance resource or data source
- **name**: Group name, assigned by referencing input variable group\_name
- **description**: Group description, assigned by referencing input variable group\_description, optional parameter, default value is empty string

> Note: Identity Center group depends on Identity Center instance. If the instance does not exist, you need to create the instance first; if the instance already exists, you can query instance information through data source. When creating an instance, if you need to use it in a specific region, you may need to register the region first.

### 6. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Identity Center Group Configuration
group_name = "tf_test_group"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially:
   - `is_instance_create` can be set to true to create instance, or set to false to use existing instance
   - `is_region_need_register` can be set to true to register region, or set to false to not register region
   - `instance_store_id_alias` can be set to instance alias, optional parameter
   - `group_name` needs to be set to group name
   - `group_description` can be set to group description information, optional parameter
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="group_name=my-group" -var="is_instance_create=true"`
2. Environment variables: `export TF_VAR_group_name=my-group` and `export TF_VAR_is_instance_create=true`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. Identity Center group depends on Identity Center instance. Please ensure the instance exists or is configured to be created.

### 7. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create Identity Center group:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating Identity Center instance (if needed) and group
4. Run `terraform show` to view the details of the created Identity Center group

> Note: Before creating Identity Center group, ensure that Identity Center instance exists. If the instance does not exist, you need to create the instance first. When creating an instance, if you need to use it in a specific region, you may need to register the region first. It is recommended to confirm the status of Identity Center instance before creating group.

## Reference Information

- [Huawei Cloud Identity Center Product Documentation](https://support.huaweicloud.com/identity-center/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Group](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/identity-center/group)

# Deploy Instance Configuration

## Application Scenario

Identity Center is a unified identity management service provided by Huawei Cloud, supporting unified identity authentication and authorization management across clouds and applications. By configuring Identity Center instance SSO configuration, you can set security policies such as Multi-Factor Authentication (MFA) mode, allowed MFA types, no MFA sign-in behavior, no password sign-in behavior, maximum authentication age, etc., improving the security and flexibility of identity authentication. This best practice will introduce how to use Terraform to automatically deploy Identity Center instance configuration, including querying or creating Identity Center instances, registering regions (optional), and configuring SSO configuration.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Identity Center Instance Data Source (huaweicloud\_identitycenter\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/identitycenter_instance)

### Resources

- [Identity Center Registered Region Resource (huaweicloud\_identitycenter\_registered\_region)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/identitycenter_registered_region)
- [Identity Center Instance Resource (huaweicloud\_identitycenter\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/identitycenter_instance)
- [Identity Center SSO Configuration Resource (huaweicloud\_identitycenter\_sso\_configuration)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/identitycenter_sso_configuration)

### Resource/Data Source Dependencies

```
huaweicloud_identitycenter_registered_region
    └── huaweicloud_identitycenter_instance
        └── huaweicloud_identitycenter_sso_configuration

data.huaweicloud_identitycenter_instance
    └── huaweicloud_identitycenter_sso_configuration
```

> Note: Identity Center SSO configuration resource depends on Identity Center instance. If the instance does not exist, you need to create the instance first; if the instance already exists, you can query instance information through data source. When creating an instance, if you need to use it in a specific region, you may need to register the region first.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Identity Center Instance Data Source (Optional)

Add the following script to the TF file (e.g., main.tf) to query Identity Center instance information (when the instance already exists):

```hcl
variable "is_instance_create" {
  description = "Whether to create the identity center instance"
  type        = bool
  default     = true
}

# Get Identity Center instance information in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block), used for configuring SSO configuration
data "huaweicloud_identitycenter_instance" "test" {
  count = var.is_instance_create ? 0 : 1
}
```

**Parameter Description**:

- **count**: The number of data source creations, used to control whether to execute Identity Center instance query data source, only creates the data source (i.e., executes Identity Center instance query) when `var.is_instance_create` is false

### 3. Create Identity Center Registered Region Resource (Optional)

Add the following script to the TF file (e.g., main.tf) to register region (when instance needs to be created and region needs to be registered):

```hcl
variable "is_region_need_register" {
  description = "Whether to register the region"
  type        = bool
  default     = true
}

variable "region_name" {
  description = "The region where the LTS service is located"
  type        = string
}

# Create Identity Center registered region resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_identitycenter_registered_region" "test" {
  count = var.is_instance_create ? var.is_region_need_register ? 1 : 0 : 0

  region_id = var.region_name
}
```

**Parameter Description**:

- **count**: Number of resource creations, used to control whether to create registered region resource, only creates when instance needs to be created and region needs to be registered
- **region\_id**: Region ID, assigned by referencing input variable region\_name

### 4. Create Identity Center Instance Resource (Optional)

Add the following script to the TF file (e.g., main.tf) to create Identity Center instance (when the instance does not exist):

```hcl
variable "instance_store_id_alias" {
  description = "The alias of the identity center instance"
  type        = string
  default     = ""
}

# Create Identity Center instance resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_identitycenter_instance" "test" {
  count = var.is_instance_create ? 1 : 0

  depends_on = [huaweicloud_identitycenter_registered_region.test]

  alias = var.instance_store_id_alias != "" ? var.instance_store_id_alias : null
}
```

**Parameter Description**:

- **count**: Number of resource creations, used to control whether to create Identity Center instance resource, only creates when `var.is_instance_create` is true
- **depends\_on**: Explicit dependency relationship, ensuring instance is created after registered region resource is created
- **alias**: Instance alias, assigned by referencing input variable instance\_store\_id\_alias, optional parameter, default value is null

### 5. Create Identity Center SSO Configuration Resource

Add the following script to the TF file (e.g., main.tf) to create Identity Center SSO configuration:

```hcl
variable "configuration_type" {
  description = "The type of the identity center instance configuration"
  type        = string
  default     = "APP_AUTHENTICATION_CONFIGURATION"
}

variable "configuration_mfa_mode" {
  description = "The mfa mode of the identity center instance configuration"
  type        = string
  default     = null

  validation {
    condition     = contains(["ALWAYS_ON", "CONTEXT_AWARE", "DISABLED"], var.configuration_mfa_mode)
    error_message = "The valid values of the mfa mode are: ALWAYS_ON, CONTEXT_AWARE, DISABLED"
  }
}

variable "configuration_allowed_mfa_types" {
  description = "The allowed mfa types of the identity center instance configuration"
  type        = list(string)
  default     = null

  validation {
    condition     = contains(["TOTP", "WEBAUTHN_SECURITY_KEY"], var.configuration_allowed_mfa_types)
    error_message = "The valid values of the allowed mfa types are: TOTP, WEBAUTHN_SECURITY_KEY"
  }
}

variable "configuration_no_mfa_signin_behavior" {
  description = "The no mfa signin behavior of the identity center instance configuration"
  type        = string
  default     = null

  validation {
    condition     = contains(["ALLOWED_WITH_ENROLLMENT", "ALLOWED", "EMAIL_OTP", "BLOCKED"], var.configuration_no_mfa_signin_behavior)
    error_message = "The valid values of the no mfa signin behavior are: ALLOWED_WITH_ENROLLMENT, ALLOWED, EMAIL_OTP, BLOCKED"
  }
}

variable "configuration_no_password_signin_behavior" {
  description = "The no password signin behavior of the identity center instance configuration"
  type        = string
  default     = null

  validation {
    condition     = contains(["BLOCKED"], var.configuration_no_password_signin_behavior)
    error_message = "The valid value of the no password signin behavior is: BLOCKED"
  }
}

variable "configuration_max_authentication_age" {
  description = "The max authentication age of the identity center instance configuration"
  type        = string
  default     = null
}

# Create Identity Center SSO configuration resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_identitycenter_sso_configuration" "test" {
  instance_id                 = var.is_instance_create ? huaweicloud_identitycenter_instance.test[0].identity_store_id : data.huaweicloud_identitycenter_instance.test[0].identity_store_id
  configuration_type          = var.configuration_type
  mfa_mode                    = var.configuration_mfa_mode
  allowed_mfa_types           = var.configuration_allowed_mfa_types
  no_mfa_signin_behavior      = var.configuration_no_mfa_signin_behavior
  no_password_signin_behavior = var.configuration_no_password_signin_behavior
  max_authentication_age      = var.configuration_max_authentication_age
}
```

**Parameter Description**:

- **instance\_id**: Instance ID, assigned by referencing Identity Center instance resource or data source
- **configuration\_type**: Configuration type, assigned by referencing input variable configuration\_type, default value is "APP\_AUTHENTICATION\_CONFIGURATION"
- **mfa\_mode**: MFA mode, assigned by referencing input variable configuration\_mfa\_mode, optional values are "ALWAYS\_ON" (always on), "CONTEXT\_AWARE" (context-aware), "DISABLED" (disabled), optional parameter, default value is null
- **allowed\_mfa\_types**: Allowed MFA types list, assigned by referencing input variable configuration\_allowed\_mfa\_types, optional values are "TOTP" (Time-based One-Time Password), "WEBAUTHN\_SECURITY\_KEY" (WebAuthn security key), optional parameter, default value is null
- **no\_mfa\_signin\_behavior**: No MFA sign-in behavior, assigned by referencing input variable configuration\_no\_mfa\_signin\_behavior, optional values are "ALLOWED\_WITH\_ENROLLMENT" (allowed but requires enrollment), "ALLOWED" (allowed), "EMAIL\_OTP" (email OTP), "BLOCKED" (blocked), optional parameter, default value is null
- **no\_password\_signin\_behavior**: No password sign-in behavior, assigned by referencing input variable configuration\_no\_password\_signin\_behavior, optional value is "BLOCKED" (blocked), optional parameter, default value is null
- **max\_authentication\_age**: Maximum authentication age, assigned by referencing input variable configuration\_max\_authentication\_age, uses ISO 8601 duration format (e.g., "PT12H" represents 12 hours), optional parameter, default value is null

> Note: Identity Center SSO configuration depends on Identity Center instance. If the instance does not exist, you need to create the instance first; if the instance already exists, you can query instance information through data source. Parameters such as MFA mode, allowed MFA types, no MFA sign-in behavior, etc., need to be configured reasonably according to actual security requirements. It is recommended to follow the principle of least privilege and improve the security of identity authentication.

### 6. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Identity Center SSO Configuration
configuration_mfa_mode                    = "CONTEXT_AWARE"
configuration_allowed_mfa_types           = ["TOTP"]
configuration_no_mfa_signin_behavior      = "ALLOWED_WITH_ENROLLMENT"
configuration_no_password_signin_behavior = "BLOCKED"
configuration_max_authentication_age      = "PT12H"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially:
   - `is_instance_create` can be set to true to create instance, or set to false to use existing instance
   - `is_region_need_register` can be set to true to register region, or set to false to not register region
   - `instance_store_id_alias` can be set to instance alias, optional parameter
   - `configuration_type` can be set to configuration type, default value is "APP\_AUTHENTICATION\_CONFIGURATION"
   - `configuration_mfa_mode` can be set to MFA mode, recommended to set to "CONTEXT\_AWARE" or "ALWAYS\_ON" to improve security
   - `configuration_allowed_mfa_types` can be set to allowed MFA types list, recommended to include "TOTP" or "WEBAUTHN\_SECURITY\_KEY"
   - `configuration_no_mfa_signin_behavior` can be set to no MFA sign-in behavior, recommended to set to "ALLOWED\_WITH\_ENROLLMENT" or "BLOCKED"
   - `configuration_no_password_signin_behavior` can be set to no password sign-in behavior, recommended to set to "BLOCKED" to improve security
   - `configuration_max_authentication_age` can be set to maximum authentication age, uses ISO 8601 duration format
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="configuration_mfa_mode=ALWAYS_ON" -var='configuration_allowed_mfa_types=["TOTP"]'`
2. Environment variables: `export TF_VAR_configuration_mfa_mode=ALWAYS_ON` and `export TF_VAR_configuration_allowed_mfa_types='["TOTP"]'`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. Identity Center SSO configuration depends on Identity Center instance. Please ensure the instance exists or is configured to be created. Parameters such as MFA mode, allowed MFA types, no MFA sign-in behavior, etc., need to be configured reasonably according to actual security requirements.

### 7. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create Identity Center instance configuration:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating Identity Center instance (if needed) and SSO configuration
4. Run `terraform show` to view the details of the created Identity Center SSO configuration

> Note: Before creating Identity Center SSO configuration, ensure that Identity Center instance exists. If the instance does not exist, you need to create the instance first. When creating an instance, if you need to use it in a specific region, you may need to register the region first. It is recommended to confirm the status of Identity Center instance before creating SSO configuration and configure parameters such as MFA mode, allowed MFA types, no MFA sign-in behavior, etc., reasonably according to actual security requirements.

## Reference Information

- [Huawei Cloud Identity Center Product Documentation](https://support.huaweicloud.com/identity-center/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Instance Configuration](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/identity-center/instance-configuration)

# Deploy Password Policy

## Application Scenario

Identity Center is a unified identity management service provided by Huawei Cloud, supporting unified identity authentication and authorization management across clouds and applications. By configuring Identity Center password policies, you can set security policies such as maximum password validity period, minimum length, reuse prevention, character requirements, etc., improving account security and meeting enterprise-level security compliance requirements. This best practice will introduce how to use Terraform to automatically deploy Identity Center password policies, including querying or creating Identity Center instances, registering regions (optional), and configuring password policies.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Identity Center Instance Data Source (huaweicloud\_identitycenter\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/identitycenter_instance)

### Resources

- [Identity Center Registered Region Resource (huaweicloud\_identitycenter\_registered\_region)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/identitycenter_registered_region)
- [Identity Center Instance Resource (huaweicloud\_identitycenter\_instance)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/identitycenter_instance)
- [Identity Center Password Policy Resource (huaweicloud\_identitycenter\_password\_policy)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/identitycenter_password_policy)

### Resource/Data Source Dependencies

```
huaweicloud_identitycenter_registered_region
    └── huaweicloud_identitycenter_instance
        └── huaweicloud_identitycenter_password_policy

data.huaweicloud_identitycenter_instance
    └── huaweicloud_identitycenter_password_policy
```

> Note: Identity Center password policy resource depends on Identity Center instance. If the instance does not exist, you need to create the instance first; if the instance already exists, you can query instance information through data source. When creating an instance, if you need to use it in a specific region, you may need to register the region first.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query Identity Center Instance Data Source (Optional)

Add the following script to the TF file (e.g., main.tf) to query Identity Center instance information (when the instance already exists):

```hcl
variable "is_instance_create" {
  description = "Whether to create the identity center instance"
  type        = bool
  default     = true
}

# Get Identity Center instance information in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block), used for configuring password policy
data "huaweicloud_identitycenter_instance" "test" {
  count = var.is_instance_create ? 0 : 1
}
```

**Parameter Description**:

- **count**: The number of data source creations, used to control whether to execute Identity Center instance query data source, only creates the data source (i.e., executes Identity Center instance query) when `var.is_instance_create` is false

### 3. Create Identity Center Registered Region Resource (Optional)

Add the following script to the TF file (e.g., main.tf) to register region (when instance needs to be created and region needs to be registered):

```hcl
variable "is_region_need_register" {
  description = "Whether to register the region"
  type        = bool
  default     = true
}

variable "region_name" {
  description = "The region where the LTS service is located"
  type        = string
}

# Create Identity Center registered region resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_identitycenter_registered_region" "test" {
  count = var.is_instance_create ? var.is_region_need_register ? 1 : 0 : 0

  region_id = var.region_name
}
```

**Parameter Description**:

- **count**: Number of resource creations, used to control whether to create registered region resource, only creates when instance needs to be created and region needs to be registered
- **region\_id**: Region ID, assigned by referencing input variable region\_name

### 4. Create Identity Center Instance Resource (Optional)

Add the following script to the TF file (e.g., main.tf) to create Identity Center instance (when the instance does not exist):

```hcl
variable "instance_store_id_alias" {
  description = "The alias of the identity center instance"
  type        = string
  default     = ""
}

# Create Identity Center instance resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_identitycenter_instance" "test" {
  count = var.is_instance_create ? 1 : 0

  depends_on = [huaweicloud_identitycenter_registered_region.test]

  alias = var.instance_store_id_alias != "" ? var.instance_store_id_alias : null
}
```

**Parameter Description**:

- **count**: Number of resource creations, used to control whether to create Identity Center instance resource, only creates when `var.is_instance_create` is true
- **depends\_on**: Explicit dependency relationship, ensuring instance is created after registered region resource is created
- **alias**: Instance alias, assigned by referencing input variable instance\_store\_id\_alias, optional parameter, default value is null

### 5. Create Identity Center Password Policy Resource

Add the following script to the TF file (e.g., main.tf) to create Identity Center password policy:

```hcl
variable "policy_max_password_age" {
  description = "The max password age of the identity center password policy, unit in days"
  type        = number
  default     = 10

  validation {
    condition     = var.policy_max_password_age >= 1 && var.policy_max_password_age <= 1095
    error_message = "The valid value of the max password age is range from 1 to 1095"
  }
}

variable "policy_minimum_password_length" {
  description = "The minimum password length of the identity center password policy"
  type        = number
  default     = 10
}

variable "policy_password_reuse_prevention" {
  description = "The password reuse prevention feature of the identity center's password policy indicates whether to prohibit the use of the same password as the previous one"
  type        = bool
  default     = true
}

variable "policy_require_uppercase_characters" {
  description = "The require uppercase characters of the identity center password policy"
  type        = bool
  default     = true
}

variable "policy_require_lowercase_characters" {
  description = "The require lowercase characters of the identity center password policy"
  type        = bool
  default     = true
}

variable "policy_require_numbers" {
  description = "The require numbers of the identity center password policy"
  type        = bool
  default     = true
}

variable "policy_require_symbols" {
  description = "The require symbols of the identity center password policy"
  type        = bool
  default     = true
}

# Create Identity Center password policy resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_identitycenter_password_policy" "test" {
  identity_store_id            = var.is_instance_create ? huaweicloud_identitycenter_instance.test[0].identity_store_id : data.huaweicloud_identitycenter_instance.test[0].identity_store_id
  max_password_age             = var.policy_max_password_age
  minimum_password_length      = var.policy_minimum_password_length
  password_reuse_prevention    = var.policy_password_reuse_prevention ? 1 : null
  require_uppercase_characters = var.policy_require_uppercase_characters
  require_lowercase_characters = var.policy_require_lowercase_characters
  require_numbers              = var.policy_require_numbers
  require_symbols              = var.policy_require_symbols
}
```

**Parameter Description**:

- **identity\_store\_id**: Identity store ID, assigned by referencing Identity Center instance resource or data source
- **max\_password\_age**: Maximum password validity period (days), assigned by referencing input variable policy\_max\_password\_age, valid range is 1-1095, default value is 10
- **minimum\_password\_length**: Minimum password length, assigned by referencing input variable policy\_minimum\_password\_length, default value is 10
- **password\_reuse\_prevention**: Password reuse prevention, assigned by referencing input variable policy\_password\_reuse\_prevention, set to 1 to enable, set to null to disable, default value is 1 (enabled)
- **require\_uppercase\_characters**: Whether to require uppercase characters, assigned by referencing input variable policy\_require\_uppercase\_characters, default value is true
- **require\_lowercase\_characters**: Whether to require lowercase characters, assigned by referencing input variable policy\_require\_lowercase\_characters, default value is true
- **require\_numbers**: Whether to require numbers, assigned by referencing input variable policy\_require\_numbers, default value is true
- **require\_symbols**: Whether to require symbols, assigned by referencing input variable policy\_require\_symbols, default value is true

> Note: Identity Center password policy depends on Identity Center instance. If the instance does not exist, you need to create the instance first; if the instance already exists, you can query instance information through data source. Password policy parameters need to be configured reasonably according to actual security requirements. It is recommended to follow the principle of least privilege and set reasonable password complexity requirements to improve account security.

### 6. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Identity Center Password Policy Configuration
# The policy defines a minimum password length of 8 characters, allows uppercase and lowercase letters, numbers,
# and special characters, and a password validity period of 30 days.
policy_max_password_age        = 30
policy_minimum_password_length = 8
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially:
   - `is_instance_create` can be set to true to create instance, or set to false to use existing instance
   - `is_region_need_register` can be set to true to register region, or set to false to not register region
   - `instance_store_id_alias` can be set to instance alias, optional parameter
   - `policy_max_password_age` can be set to maximum password validity period (days), recommended to set to 30-90 days
   - `policy_minimum_password_length` can be set to minimum password length, recommended to set to 8 or longer
   - `policy_password_reuse_prevention` can be set to true to enable password reuse prevention, or set to false to disable
   - `policy_require_uppercase_characters` can be set to true to require uppercase characters, or set to false to not require
   - `policy_require_lowercase_characters` can be set to true to require lowercase characters, or set to false to not require
   - `policy_require_numbers` can be set to true to require numbers, or set to false to not require
   - `policy_require_symbols` can be set to true to require symbols, or set to false to not require
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="policy_minimum_password_length=12" -var="policy_max_password_age=90"`
2. Environment variables: `export TF_VAR_policy_minimum_password_length=12` and `export TF_VAR_policy_max_password_age=90`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. Identity Center password policy depends on Identity Center instance. Please ensure the instance exists or is configured to be created. Password policy parameters need to be configured reasonably according to actual security requirements. It is recommended to follow the principle of least privilege.

### 7. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create Identity Center password policy:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating Identity Center instance (if needed) and password policy
4. Run `terraform show` to view the details of the created Identity Center password policy

> Note: Before creating Identity Center password policy, ensure that Identity Center instance exists. If the instance does not exist, you need to create the instance first. When creating an instance, if you need to use it in a specific region, you may need to register the region first. It is recommended to confirm the status of Identity Center instance before creating password policy and configure password policy parameters reasonably according to actual security requirements.

## Reference Information

- [Huawei Cloud Identity Center Product Documentation](https://support.huaweicloud.com/identity-center/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Password Policy](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/identity-center/password-policy)
