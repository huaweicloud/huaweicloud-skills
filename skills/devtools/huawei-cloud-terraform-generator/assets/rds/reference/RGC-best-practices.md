# Deploy Account

## Application Scenario

Resource Governance Center (RGC) is a resource governance service provided by Huawei Cloud, supporting multi-account management, organizational unit management, blueprint configuration, and other functions to help you uniformly manage and govern cloud resources. By creating RGC accounts, new accounts can be created within organizational units, achieving unified account management and governance. This best practice introduces how to use Terraform to automatically deploy RGC accounts, including account basic information, identity store information, and organizational unit information configuration.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [Account Resource (huaweicloud\_rgc\_account)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/rgc_account)

### Resource/Data Source Dependencies

```
huaweicloud_rgc_account
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Create Account

Add the following script to the TF file (such as main.tf) to create an RGC account:

```hcl
variable "account_name" {
  description = "The name of RGC account"
  type        = string
}

variable "account_email" {
  description = "The email of RGC account"
  type        = string
}

variable "account_phone" {
  description = "The phone number of RGC account"
  type        = string
  sensitive   = true
  default     = ""
}

variable "identity_store_user_name" {
  description = "The identity store user name of RGC account"
  type        = string
}

variable "identity_store_email" {
  description = "The identity store email of RGC account"
  type        = string
}

variable "parent_organizational_unit_name" {
  description = "The parent organizational unit name of RGC account"
  type        = string
}

variable "parent_organizational_unit_id" {
  description = "The parent organizational unit ID of RGC account"
  type        = string
}

# Create account resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_rgc_account" "test" {
  name                            = var.account_name
  email                           = var.account_email
  phone                           = var.account_phone
  identity_store_user_name        = var.identity_store_user_name
  identity_store_email            = var.identity_store_email
  parent_organizational_unit_name = var.parent_organizational_unit_name
  parent_organizational_unit_id   = var.parent_organizational_unit_id
}
```

**Parameter Description**:

- **name**: Account name, assigned by referencing the input variable `account_name`
- **email**: Account email, assigned by referencing the input variable `account_email`
- **phone**: Account phone number, assigned by referencing the input variable `account_phone`, optional parameter
- **identity\_store\_user\_name**: Identity store user name, assigned by referencing the input variable `identity_store_user_name`
- **identity\_store\_email**: Identity store email, assigned by referencing the input variable `identity_store_email`
- **parent\_organizational\_unit\_name**: Parent organizational unit name, assigned by referencing the input variable `parent_organizational_unit_name`
- **parent\_organizational\_unit\_id**: Parent organizational unit ID, assigned by referencing the input variable `parent_organizational_unit_id`

> Note: Accounts must belong to an organizational unit, and the parent organizational unit name and ID must be specified. Identity store information is used for account identity authentication and access control.

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Account basic information (Required)
account_name  = "tf-test-account"
account_email = "tf-test-account@terraform.com"
account_phone = "13123456789"

# Identity store information (Required)
identity_store_user_name = "tf-test-account"
identity_store_email     = "tf-test-account@terraform.com"

# Organizational unit information (Required)
parent_organizational_unit_name = "your-org-unit-name"
parent_organizational_unit_id   = "your-org-unit-id"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="account_name=tf-test-account" -var="account_email=tf-test-account@terraform.com"`
2. Environment variables: `export TF_VAR_account_name=tf-test-account`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the account
4. Run `terraform show` to view the created account

## Reference Information

- [Huawei Cloud RGC Product Documentation](https://support.huaweicloud.com/rgc/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Account](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/rgc/account)

# Deploy Account Enroll

## Application Scenario

Resource Governance Center (RGC) is a resource governance service provided by Huawei Cloud, supporting multi-account management, organizational unit management, blueprint configuration, and other functions to help you uniformly manage and govern cloud resources. Through the account enrollment function, accounts can be enrolled into organizational units and configured with blueprints to achieve automated resource deployment and management. This best practice introduces how to use Terraform to automatically deploy RGC account enrollment, including creating organizational units (optional) and account enrollment (with blueprint configuration).

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [Organizational Unit Resource (huaweicloud\_rgc\_organizational\_unit)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/rgc_organizational_unit)
- [Account Enrollment Resource (huaweicloud\_rgc\_account\_enroll)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/rgc_account_enroll)

### Resource/Data Source Dependencies

```
huaweicloud_rgc_organizational_unit
    └── huaweicloud_rgc_account_enroll
```

> Note: Creating an organizational unit is optional. If `create_organizational_unit` is `false`, the existing `parent_organizational_unit_id` will be used. Account enrollment requires specifying a parent organizational unit ID, which can reference a newly created organizational unit ID or use an existing organizational unit ID.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Create Organizational Unit (Optional)

Add the following script to the TF file (such as main.tf) to create an organizational unit (optional):

```hcl
variable "organizational_unit_name" {
  description = "The name of the organizational unit to be created (required if create_organizational_unit is true)"
  type        = string
  default     = ""
}

variable "parent_organizational_unit_id" {
  description = "The ID of the parent organizational unit. Required for account enrollment and OU creation"
  type        = string
}

variable "create_organizational_unit" {
  description = "Whether to create a new organizational unit. If false, use existing parent_organizational_unit_id"
  type        = bool
  default     = true
}

# Create organizational unit resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_rgc_organizational_unit" "test" {
  count = var.create_organizational_unit ? 1 : 0

  organizational_unit_name      = var.organizational_unit_name
  parent_organizational_unit_id = var.parent_organizational_unit_id
}
```

**Parameter Description**:

- **count**: The number of resources to create, used to control whether to create an organizational unit. The organizational unit is only created when `var.create_organizational_unit` is `true`
- **organizational\_unit\_name**: The name of the organizational unit, assigned by referencing the input variable `organizational_unit_name`
- **parent\_organizational\_unit\_id**: The ID of the parent organizational unit, assigned by referencing the input variable `parent_organizational_unit_id`

### 3. Create Account Enrollment

Add the following script to the TF file (such as main.tf) to create account enrollment (with blueprint configuration):

```hcl
variable "blueprint_managed_account_id" {
  description = "The ID of the account to be enrolled with blueprint configuration"
  type        = string
}

variable "blueprint_product_id" {
  description = "The ID of the blueprint product"
  type        = string
}

variable "blueprint_product_version" {
  description = "The version of the blueprint product"
  type        = string
}

variable "blueprint_variables" {
  description = "The variables for the blueprint configuration (JSON string format)"
  type        = string
}

variable "is_blueprint_has_multi_account_resource" {
  description = "Whether the blueprint has multi-account resources"
  type        = bool
}

# Create account enrollment resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_rgc_account_enroll" "test" {
  managed_account_id            = var.blueprint_managed_account_id
  parent_organizational_unit_id = var.create_organizational_unit ? huaweicloud_rgc_organizational_unit.test[0].organizational_unit_id : var.parent_organizational_unit_id

  blueprint {
    blueprint_product_id                    = var.blueprint_product_id
    blueprint_product_version               = var.blueprint_product_version
    variables                               = var.blueprint_variables
    is_blueprint_has_multi_account_resource = var.is_blueprint_has_multi_account_resource
  }
}
```

**Parameter Description**:

- **managed\_account\_id**: The ID of the account to be enrolled, assigned by referencing the input variable `blueprint_managed_account_id`
- **parent\_organizational\_unit\_id**: The ID of the parent organizational unit. If an organizational unit is created, it references the newly created organizational unit ID; otherwise, it uses the existing organizational unit ID
- **blueprint**: Blueprint configuration block, containing the following parameters:
  - **blueprint\_product\_id**: Blueprint product ID, assigned by referencing the input variable `blueprint_product_id`
  - **blueprint\_product\_version**: Blueprint product version, assigned by referencing the input variable `blueprint_product_version`
  - **variables**: Blueprint variables, assigned by referencing the input variable `blueprint_variables`, must be in JSON string format
  - **is\_blueprint\_has\_multi\_account\_resource**: Whether the blueprint contains multi-account resources, assigned by referencing the input variable `is_blueprint_has_multi_account_resource`

> Note: Blueprint variables must be in JSON string format, for example: `"{\"environment\":\"production\",\"region\":\"cn-north-4\"}"`. If the blueprint contains multi-account resources, set `is_blueprint_has_multi_account_resource` to `true`.

### 4. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Parent organizational unit ID (Required)
# Required for both account enrollment and OU creation
# Replace with your actual parent organizational unit ID
parent_organizational_unit_id = "ou-xxxxxxxxxxxxx"

# Account ID to be enrolled (Required)
# Replace with your actual account ID
blueprint_managed_account_id = "account-xxxxxxxxxxxxx"

# Blueprint product configuration (Required)
# Replace with your actual blueprint product ID and version
blueprint_product_id      = "blueprint-xxxxxxxxxxxxx"
blueprint_product_version = "1.0.0"

# Blueprint variables (Required)
# Customize these variables according to your blueprint requirements
blueprint_variables = "{\"environment\":\"production\",\"region\":\"cn-north-4\"}"

# Whether the blueprint has multi-account resources (Required)
is_blueprint_has_multi_account_resource = false
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="parent_organizational_unit_id=ou-xxxxxxxxxxxxx" -var="blueprint_managed_account_id=account-xxxxxxxxxxxxx"`
2. Environment variables: `export TF_VAR_parent_organizational_unit_id=ou-xxxxxxxxxxxxx`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 5. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating account enrollment
4. Run `terraform show` to view the created account enrollment

## Reference Information

- [Huawei Cloud RGC Product Documentation](https://support.huaweicloud.com/rgc/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Account Enrollment](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/rgc/account-enroll)

# Deploy Template

## Application Scenario

Resource Governance Center (RGC) is a resource governance service provided by Huawei Cloud, supporting multi-account management, organizational unit management, blueprint configuration, and other functions to help you uniformly manage and govern cloud resources. By creating RGC templates, deployment blueprints for resources can be defined, achieving automated resource deployment and management. Templates can be predefined templates or customized templates. Predefined templates are provided by Huawei Cloud, while customized templates can be configured according to actual needs. This best practice introduces how to use Terraform to automatically deploy RGC templates, including the creation of predefined templates and customized templates.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [Template Resource (huaweicloud\_rgc\_template)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/rgc_template)

### Resource/Data Source Dependencies

```
huaweicloud_rgc_template
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Create Template

Add the following script to the TF file (such as main.tf) to create an RGC template:

```hcl
variable "template_name" {
  description = "The name of the template"
  type        = string
}

variable "template_type" {
  description = "The type of the template"
  type        = string
  default     = "predefined"
}

variable "template_description" {
  description = "The description of the customized template"
  type        = string
  default     = null
}

variable "template_body" {
  description = "The content of the customized template"
  type        = string
  default     = null
}

# Create template resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_rgc_template" "test" {
  template_name        = var.template_name
  template_type        = var.template_type
  template_description = var.template_description
  template_body        = var.template_body
}
```

**Parameter Description**:

- **template\_name**: Template name, assigned by referencing the input variable `template_name`
- **template\_type**: Template type, assigned by referencing the input variable `template_type`. Optional values include `predefined` (predefined template) and `customized` (customized template), default is `predefined`
- **template\_description**: Description of the customized template, assigned by referencing the input variable `template_description`. Only valid when `template_type` is `customized`, optional parameter
- **template\_body**: Content of the customized template, assigned by referencing the input variable `template_body`. Only valid when `template_type` is `customized`, optional parameter

> Note: Predefined templates are provided by Huawei Cloud. When creating, only the template name and type need to be specified. Customized templates require template description and template content. Template content is usually blueprint configuration in JSON format.

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Template basic information (Required)
template_name = "tf_test_template"
template_type = "predefined"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

If creating a customized template, you can add the following content to the `terraform.tfvars` file:

```hcl
# Customized template configuration
template_name        = "tf_test_customized_template"
template_type        = "customized"
template_description = "This is a customized template for resource deployment"
template_body        = jsonencode({
  version = "1.0"
  resources = {
    # Template content configuration
  }
})
```

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="template_name=tf_test_template" -var="template_type=predefined"`
2. Environment variables: `export TF_VAR_template_name=tf_test_template`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the template
4. Run `terraform show` to view the created template

## Reference Information

- [Huawei Cloud RGC Product Documentation](https://support.huaweicloud.com/rgc/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Template](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/rgc/template)
