# Deploy Group Policies Associate

## Application Scenario

Identity and Access Management (IAM) is a basic identity authentication and access management service provided by Huawei Cloud, providing core functions such as identity management, permission management, and access control for Huawei Cloud users. By associating policies with user groups, you can uniformly grant permissions to users in the group, achieving permission management based on user groups. This best practice will introduce how to use Terraform to automatically deploy IAM user group and policy associations, including querying IAM policies, creating user groups, and associating policies with user groups.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [IAM Policies Data Source (huaweicloud\_identityv5\_policies)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/identityv5_policies)

### Resources

- [IAM User Group Resource (huaweicloud\_identityv5\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/identityv5_group)
- [IAM Policy Group Attach Resource (huaweicloud\_identityv5\_policy\_group\_attach)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/identityv5_policy_group_attach)

### Resource/Data Source Dependencies

```
data.huaweicloud_identityv5_policies
    └── huaweicloud_identityv5_policy_group_attach

huaweicloud_identityv5_group
    └── huaweicloud_identityv5_policy_group_attach
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Query IAM Policies Data Source

Add the following script to the TF file (e.g., main.tf) to query IAM policy information:

```hcl
variable "policy_type" {
  description = "The type of the policy"
  type        = string
  default     = "system"
}

variable "policy_names" {
  description = "The name list of policies to be associated with the user group"
  type        = list(string)
}

# Get all IAM policy information in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block), used for associating with user groups
data "huaweicloud_identityv5_policies" "test" {
  policy_type = var.policy_type
}

# Filter policy list by policy name
locals {
  filtered_policies = [for policy in data.huaweicloud_identityv5_policies.test.policies : policy if contains(var.policy_names, policy.policy_name)]
}
```

**Parameter Description**:

- **policy\_type**: Policy type, assigned by referencing input variable policy\_type, default value is "system" (system policy)
- **policy\_names**: Policy name list, assigned by referencing input variable policy\_names, used to filter policies that need to be associated
- **locals.filtered\_policies**: Filtered policy list based on policy names, used for subsequent association with user groups

### 3. Create IAM User Group Resource

Add the following script to the TF file (e.g., main.tf) to create an IAM user group:

```hcl
variable "group_name" {
  description = "The name of the user group"
  type        = string
}

variable "group_description" {
  description = "The description of the user group"
  type        = string
  default     = ""
}

# Create IAM user group resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_identityv5_group" "test" {
  group_name  = var.group_name
  description = var.group_description
}
```

**Parameter Description**:

- **group\_name**: User group name, assigned by referencing input variable group\_name
- **description**: User group description, assigned by referencing input variable group\_description, optional parameter, default value is empty string

### 4. Create IAM Policy Group Attach Resource

Add the following script to the TF file (e.g., main.tf) to associate policies with user groups:

```hcl
# Create IAM policy group attach resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_identityv5_policy_group_attach" "test" {
  count = length(local.filtered_policies)

  policy_id = try(local.filtered_policies[count.index].policy_id, null)
  group_id  = huaweicloud_identityv5_group.test.id
}
```

**Parameter Description**:

- **count**: Number of resource creations, dynamically creates attach resources based on the length of the filtered policy list
- **policy\_id**: Policy ID, assigned by referencing the filtered policy list
- **group\_id**: User group ID, assigned by referencing the user group resource

> Note: The policy group attach resource uses the count parameter to dynamically create multiple attach resources based on the filtered policy list. Ensure that the policies in the policy name list exist in IAM, otherwise the filtered policy list may be empty, resulting in failure to create associations.

### 5. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# IAM User Group Configuration
group_name        = "tf_test_group"
group_description = "Test user group"

# IAM Policy Configuration
policy_type  = "system"
policy_names = [
  "ModelArtsFullAccessPolicy",
  "SCMReadOnlyPolicy"
]
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially:
   - `group_name` needs to be set to user group name
   - `group_description` can be set to user group description information, optional parameter
   - `policy_type` can be set to "system" (system policy) or other policy types
   - `policy_names` needs to be set to the list of policy names to be associated, ensuring these policies exist in IAM
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="group_name=my-group" -var='policy_names=["Policy1","Policy2"]'`
2. Environment variables: `export TF_VAR_group_name=my-group` and `export TF_VAR_policy_names='["Policy1","Policy2"]'`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. Ensure that the policies in the policy name list exist in IAM, otherwise the filtered policy list may be empty, resulting in failure to create associations.

### 6. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create IAM user group and policy associations:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating IAM user group and policy associations
4. Run `terraform show` to view the details of the created IAM user group and policy associations

> Note: After the policy group attach is created, users in the user group will receive the permissions granted by the associated policies. Ensure that policy names are correct, otherwise the filtered policy list may be empty, resulting in failure to create associations. It is recommended to query the available policy list in IAM before creating associations to confirm that policy names are correct.

## Reference Information

- [Huawei Cloud IAM Product Documentation](https://support.huaweicloud.com/iam/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Group Policies Associate](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/iam/v5/group-policies-associate)

# Deploy Password Policy

## Application Scenario

Identity and Access Management (IAM) is a basic identity authentication and access management service provided by Huawei Cloud, providing core functions such as identity management, permission management, and access control for Huawei Cloud users. By configuring password policies, you can set security policies such as password complexity requirements, validity periods, reuse rules, etc., improving account security and meeting enterprise-level security compliance requirements. This best practice will introduce how to use Terraform to automatically deploy IAM password policies, including configuration of security policies such as password length, character combination, validity period, reuse rules, etc.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [IAM Password Policy Resource (huaweicloud\_identityv5\_password\_policy)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/identityv5_password_policy)

### Resource/Data Source Dependencies

```
huaweicloud_identityv5_password_policy
```

> Note: IAM password policy resource is a global resource used to configure password security policies for IAM accounts. After password policy is configured, it will apply to all IAM users.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create IAM Password Policy Resource

Add the following script to the TF file (e.g., main.tf) to create IAM password policy:

```hcl
variable "policy_max_consecutive_identical_chars" {
  description = "The maximum number of times that a character is allowed to consecutively present in a password"
  type        = number

  validation {
    condition     = var.policy_max_consecutive_identical_chars >= 0 && var.policy_max_consecutive_identical_chars <= 32
    error_message = "The valid value of the maximum number of times that a character is allowed to consecutively present in a password is range from 0 to 32"
  }
}

variable "policy_min_password_age" {
  description = "The minimum period (minutes) after which users are allowed to make a password change"
  type        = number

  validation {
    condition     = var.policy_min_password_age >= 0 && var.policy_min_password_age <= 1440
    error_message = "The valid value of the minimum period (minutes) after which users are allowed to make a password change is range from 0 to 1440"
  }
}

variable "policy_min_password_length" {
  description = "The minimum number of characters that a password must contain"
  type        = number

  validation {
    condition     = var.policy_min_password_length >= 8 && var.policy_min_password_length <= 32
    error_message = "The valid value of the minimum number of characters that a password must contain is range from 8 to 32"
  }
}

variable "policy_password_reuse_prevention" {
  description = "The password reuse prevention feature of the identity center's password policy indicates whether to prohibit the use of the same password as the previous one"
  type        = number
  default     = 3

  validation {
    condition     = var.policy_password_reuse_prevention >= 0 && var.policy_password_reuse_prevention <= 24
    error_message = "The valid value of the password reuse prevention feature of the identity center's password policy is range from 0 to 24"
  }
}

variable "policy_password_not_username_or_invert" {
  description = "Whether the password can be the username or the username spelled backwards"
  type        = bool
  default     = false
}

variable "policy_password_validity_period" {
  description = "The password validity period (days)"
  type        = number
  default     = 7

  validation {
    condition     = var.policy_password_validity_period >= 0 && var.policy_password_validity_period <= 180
    error_message = "The valid value of the password validity period (days) is range from 0 to 180"
  }
}

variable "policy_password_char_combination" {
  description = "The minimum number of character types that a password must contain"
  type        = number

  validation {
    condition     = var.policy_password_char_combination >= 2 && var.policy_password_char_combination <= 4
    error_message = "The valid value of the minimum number of character types that a password must contain is range from 2 to 4"
  }
}

variable "policy_allow_user_to_change_password" {
  description = "Whether IAM users are allowed to change their own passwords"
  type        = bool
  default     = true
}

# Create IAM password policy resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_identityv5_password_policy" "test" {
  maximum_consecutive_identical_chars = var.policy_max_consecutive_identical_chars
  minimum_password_age                = var.policy_min_password_age
  minimum_password_length             = var.policy_min_password_length
  password_reuse_prevention           = var.policy_password_reuse_prevention
  password_not_username_or_invert     = var.policy_password_not_username_or_invert
  password_validity_period            = var.policy_password_validity_period
  password_char_combination           = var.policy_password_char_combination
  allow_user_to_change_password       = var.policy_allow_user_to_change_password
}
```

**Parameter Description**:

- **maximum\_consecutive\_identical\_chars**: Maximum number of times that a character is allowed to consecutively present in a password, assigned by referencing input variable policy\_max\_consecutive\_identical\_chars, valid range is 0-32
- **minimum\_password\_age**: Minimum password age (minutes), assigned by referencing input variable policy\_min\_password\_age, valid range is 0-1440
- **minimum\_password\_length**: Minimum password length, assigned by referencing input variable policy\_min\_password\_length, valid range is 8-32
- **password\_reuse\_prevention**: Password reuse prevention, assigned by referencing input variable policy\_password\_reuse\_prevention, valid range is 0-24, default value is 3
- **password\_not\_username\_or\_invert**: Password cannot be username or username spelled backwards, assigned by referencing input variable policy\_password\_not\_username\_or\_invert, default value is false
- **password\_validity\_period**: Password validity period (days), assigned by referencing input variable policy\_password\_validity\_period, valid range is 0-180, default value is 7
- **password\_char\_combination**: Minimum number of character types that a password must contain, assigned by referencing input variable policy\_password\_char\_combination, valid range is 2-4
- **allow\_user\_to\_change\_password**: Whether IAM users are allowed to change their own passwords, assigned by referencing input variable policy\_allow\_user\_to\_change\_password, default value is true

> Note: IAM password policy is a global resource, and after configuration, it will apply to all IAM users. Password policy parameters all have value range restrictions. Please configure reasonably according to actual security requirements. It is recommended to follow the principle of least privilege and set reasonable password complexity requirements to improve account security.

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# IAM Password Policy Configuration
policy_max_consecutive_identical_chars = 2
policy_min_password_age                = 60
policy_min_password_length             = 8
policy_password_char_combination       = 2
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially:
   - `policy_max_consecutive_identical_chars` can be set to the maximum number of times that a character is allowed to consecutively present in a password, recommended to set to 2 or smaller
   - `policy_min_password_age` can be set to the minimum password age (minutes), recommended to set to 60 minutes or longer
   - `policy_min_password_length` can be set to the minimum password length, recommended to set to 8 or longer
   - `policy_password_reuse_prevention` can be set to password reuse prevention, recommended to set to 3 or larger
   - `policy_password_not_username_or_invert` can be set to true to prohibit password from being username or username spelled backwards
   - `policy_password_validity_period` can be set to password validity period (days), recommended to set to 30-90 days
   - `policy_password_char_combination` can be set to the minimum number of character types that a password must contain, recommended to set to 2 or larger
   - `policy_allow_user_to_change_password` can be set to true to allow IAM users to change their own passwords
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="policy_min_password_length=12" -var="policy_password_char_combination=3"`
2. Environment variables: `export TF_VAR_policy_min_password_length=12` and `export TF_VAR_policy_password_char_combination=3`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. After IAM password policy is configured, it will apply to all IAM users. Please configure password policy parameters reasonably according to actual security requirements.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create IAM password policy:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating IAM password policy
4. Run `terraform show` to view the details of the created IAM password policy

> Note: IAM password policy is a global resource, and after configuration, it will apply to all IAM users. Password policy parameters all have value range restrictions. Please ensure parameter values are within the valid range. It is recommended to understand the current password usage of IAM users before configuring password policy to avoid overly strict policies that prevent users from normal use.

## Reference Information

- [Huawei Cloud IAM Product Documentation](https://support.huaweicloud.com/iam/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Password Policy](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/iam/v5/password-policy)

# Deploy Users Authorized Through Group

## Application Scenario

Identity and Access Management (IAM) is a fundamental identity authentication and access management service provided by Huawei Cloud, achieving fine-grained permission control through flexible combinations of users, user groups, roles, and policies. Authorizing users through user groups is a common permission management approach that can simplify permission management processes and improve management efficiency.

This best practice will introduce how to use Terraform to automatically deploy IAM roles, user groups, and users, and authorize users through user groups. Through this approach, you can implement group-based permission management. When you need to grant the same permissions to multiple users, you only need to add users to the corresponding user group, and they will automatically inherit the user group's permissions without needing to configure permissions for each user individually.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [IAM Role Query Data Source (data.huaweicloud\_identity\_role)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/identity_role)
- [IAM Project Query Data Source (data.huaweicloud\_identity\_projects)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/identity_projects)

### Resources

- [IAM Role Resource (huaweicloud\_identity\_role)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/identity_role)
- [IAM User Group Resource (huaweicloud\_identity\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/identity_group)
- [IAM Role Assignment Resource (huaweicloud\_identity\_role\_assignment)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/identity_role_assignment)
- [Random Password Resource (random\_password)](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/password)
- [IAM User Resource (huaweicloud\_identity\_user)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/identity_user)
- [IAM User Group Membership Resource (huaweicloud\_identity\_group\_membership)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/identity_group_membership)

### Resource/Data Source Dependencies

```
data.huaweicloud_identity_role.test
    └── huaweicloud_identity_role_assignment.test

huaweicloud_identity_role.test
    └── huaweicloud_identity_role_assignment.test

data.huaweicloud_identity_projects.test
    └── huaweicloud_identity_role_assignment.test

huaweicloud_identity_group.test
    ├── huaweicloud_identity_role_assignment.test
    └── huaweicloud_identity_group_membership.test

random_password.test
    └── huaweicloud_identity_user.test

huaweicloud_identity_user.test
    └── huaweicloud_identity_group_membership.test
```

## Implementation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://hcbp.gitbook.io/huaweicloud-provider/product-introduction/prepare_before_deploy) for configuration introduction.

### 2. Query IAM Role Information Through Data Source

Add the following script to the TF file (such as main.tf) to instruct Terraform to perform a data source query, the query results are used to create IAM role assignment resources:

```hcl
variable "role_id" {
  description = "The ID of the IAM role"
  type        = string
  default     = ""
  nullable    = false
}

variable "role_policy" {
  description = "The policy of the IAM role"
  type        = string
  default     = ""
  nullable    = false
}

variable "role_name" {
  description = "The name of the IAM role"
  type        = string
  default     = ""
  nullable    = false

  validation {
    condition     = !(var.role_name == "" && var.role_id == "")
    error_message = "The role_name must be provided when role_id is not provided."
  }
}

# Query IAM role information that meets the conditions in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block), used to create IAM role assignment resources
data "huaweicloud_identity_role" "test" {
  count = var.role_id == "" && var.role_policy == "" ? 1 : 0

  name = var.role_name
}
```

**Parameter Description**:

- **count**: The number of data sources to create, used to control whether to execute the IAM role query data source. The data source is only created (i.e., IAM role query is executed) when `var.role_id` is empty and `var.role_policy` is empty
- **name**: The name of the IAM role, assigned by referencing the input variable `role_name`

### 3. Create IAM Role Resource

Add the following script to the TF file to instruct Terraform to create IAM role resources:

```hcl
variable "role_type" {
  description = "The type of the IAM role"
  type        = string
  default     = "XA"
}

variable "role_description" {
  description = "The description of the IAM role"
  type        = string
  default     = ""

  validation {
    condition     = !(var.role_description == "" && var.role_policy != "")
    error_message = "The role_description must be provided when role_policy is provided."
  }
}

# Create IAM role resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_identity_role" "test" {
  count = var.role_id == "" && var.role_policy != "" ? 1 : 0

  name        = var.role_name
  type        = var.role_type
  description = var.role_description
  policy      = var.role_policy
}
```

**Parameter Description**:

- **count**: The number of resources to create, used to control whether to create IAM role resources. Resources are only created when `var.role_id` is empty and `var.role_policy` is not empty
- **name**: The name of the IAM role, assigned by referencing the input variable `role_name`
- **type**: The type of the IAM role, assigned by referencing the input variable `role_type`, default is "XA" indicating a custom role
- **description**: The description of the IAM role, assigned by referencing the input variable `role_description`
- **policy**: The policy of the IAM role, assigned by referencing the input variable `role_policy`, the policy is a JSON format string

### 4. Create IAM User Group Resource

Add the following script to the TF file to instruct Terraform to create IAM user group resources:

```hcl
variable "group_id" {
  description = "The ID of the IAM group"
  type        = string
  default     = ""
  nullable    = false
}

variable "group_name" {
  description = "The name of the IAM group"
  type        = string
  default     = ""
  nullable    = false

  validation {
    condition     = !(var.group_name == "" && var.group_id == "")
    error_message = "The group_name must be provided when group_id is not provided."
  }
}

variable "group_description" {
  description = "The description of the IAM group"
  type        = string
  default     = ""
}

# Create IAM user group resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_identity_group" "test" {
  count = var.group_id == "" ? 1 : 0

  name        = var.group_name
  description = var.group_description
}
```

**Parameter Description**:

- **count**: The number of resources to create, used to control whether to create IAM user group resources. Resources are only created when `var.group_id` is empty
- **name**: The name of the IAM user group, assigned by referencing the input variable `group_name`
- **description**: The description of the IAM user group, assigned by referencing the input variable `group_description`

### 5. Query IAM Project Information Through Data Source

Add the following script to the TF file to instruct Terraform to perform a data source query, the query results are used to create IAM role assignment resources:

```hcl
variable "authorized_project_id" {
  description = "The ID of the IAM project"
  type        = string
  default     = ""
  nullable    = false
}

variable "authorized_project_name" {
  description = "The name of the IAM project"
  type        = string
  default     = ""
  nullable    = true

  validation {
    condition     = !(var.authorized_project_name == "" && var.authorized_project_id == "")
    error_message = "The authorized_project_name must be provided when authorized_project_id is not provided."
  }
}

# Query IAM project information that meets the conditions in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block), used to create IAM role assignment resources
data "huaweicloud_identity_projects" "test" {
  count = var.authorized_project_id == "" ? 1 : 0

  name = var.authorized_project_name
}
```

**Parameter Description**:

- **count**: The number of data sources to create, used to control whether to execute the IAM project query data source. The data source is only created (i.e., IAM project query is executed) when `var.authorized_project_id` is empty
- **name**: The name of the IAM project, assigned by referencing the input variable `authorized_project_name`

### 6. Create IAM Role Assignment Resource

Add the following script to the TF file to instruct Terraform to create IAM role assignment resources:

```hcl
variable "authorized_domain_id" {
  description = "The ID of the IAM domain"
  type        = string
  default     = ""
  nullable    = false
}

# Create IAM role assignment resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_identity_role_assignment" "test" {
  group_id   = var.group_id != "" ? var.group_id : huaweicloud_identity_group.test[0].id
  role_id    = var.role_id != "" ? var.role_id : var.role_policy != "" ? huaweicloud_identity_role.test[0].id : try(data.huaweicloud_identity_role.test[0].id, "NOT_FOUND")
  domain_id  = var.authorized_domain_id != "" ? var.authorized_domain_id : null
  project_id = var.authorized_domain_id == "" ? var.authorized_project_id != "" ? var.authorized_project_id : try(data.huaweicloud_identity_projects.test[0].projects[0].id, "NOT_FOUND") : null
}
```

**Parameter Description**:

- **group\_id**: The ID of the IAM user group. If `var.group_id` is specified, use that value; otherwise, reference the ID of the IAM user group resource created earlier
- **role\_id**: The ID of the IAM role. Based on variable configuration, choose to use `var.role_id`, the created IAM role resource ID, or the queried IAM role data source ID
- **domain\_id**: The ID of the IAM domain. If `var.authorized_domain_id` is specified, use that value; otherwise, it is null, indicating authorization at the project level
- **project\_id**: The ID of the IAM project. When `var.authorized_domain_id` is empty, if `var.authorized_project_id` is specified, use that value; otherwise, use the queried IAM project data source ID. When `var.authorized_domain_id` is not empty, this parameter is null, indicating authorization at the domain level

> Note: IAM role assignment supports authorization at the domain level or project level. When `domain_id` is specified, it indicates authorization at the domain level; when `project_id` is specified, it indicates authorization at the project level. The two cannot be specified simultaneously.

### 7. Create Random Password Resource

Add the following script to the TF file to instruct Terraform to create random password resources (automatically generated when users do not specify a password):

```hcl
# Create random password resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block), used to generate random passwords for users who have not specified a password
resource "random_password" "test" {
  count = length([for v in var.users_configuration : true if v.password == "" || v.password == null]) > 0 ? 1 : 0

  length           = 16
  special          = true
  override_special = "_%@"
}
```

**Parameter Description**:

- **count**: The number of resources to create, used to control whether to create random password resources. Resources are only created when there are users who have not specified a password
- **length**: The length of the password, set to 16 characters
- **special**: Whether to include special characters, set to true to include special characters
- **override\_special**: The special character set, set to "\_%@" indicating that the password can include underscore, percent sign, and @ symbol

### 8. Create IAM User Resource

Add the following script to the TF file to instruct Terraform to create IAM user resources:

```hcl
variable "users_configuration" {
  description = "The configuration of the IAM users"
  type        = list(object({
    name     = string
    password = optional(string, "")
  }))
  nullable    = false
}

# Create IAM user resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block)
resource "huaweicloud_identity_user" "test" {
  count = length(var.users_configuration)

  name     = lookup(var.users_configuration[count.index], "name", null)
  password = lookup(var.users_configuration[count.index], "password", null) != "" ? lookup(var.users_configuration[count.index], "password", null) : random_password.test[count.index].result
}
```

**Parameter Description**:

- **count**: The number of resources to create, creating the corresponding number of IAM user resources based on the length of the `var.users_configuration` list
- **name**: The name of the IAM user, obtained from the name field of the corresponding user in the `var.users_configuration` list
- **password**: The password of the IAM user. If a password is specified in the user configuration, use that password; otherwise, use the password generated by the random password resource

### 9. Create IAM User Group Membership Resource

Add the following script to the TF file to instruct Terraform to create IAM user group membership resources:

```hcl
# Create IAM user group membership resource in the specified region (when the region parameter is omitted, it defaults to inheriting the region specified in the current provider block), adding users to the user group
resource "huaweicloud_identity_group_membership" "test" {
  group = var.group_id != "" ? var.group_id : huaweicloud_identity_group.test[0].id
  users = huaweicloud_identity_user.test[*].id
}
```

**Parameter Description**:

- **group**: The ID of the IAM user group. If `var.group_id` is specified, use that value; otherwise, reference the ID of the IAM user group resource created earlier
- **users**: The list of IAM user IDs, referencing the IDs of all IAM user resources created earlier, using the `[*]` syntax to get the IDs of all user resources

### 10. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# IAM role configuration
role_name        = "tf_test_role"
role_policy      = <<EOT
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:*:*"
      ]
    },
    {
      "Effect": "Deny",
      "Action": [
        "obs:object:DeleteObjectVersion",
        "obs:object:DeleteAccessLabel",
        "obs:bucket:DeleteDirectColdAccessConfiguration",
        "obs:object:AbortMultipartUpload",
        "obs:bucket:DeleteBucketWebsite",
        "obs:object:DeleteObject",
        "obs:bucket:DeleteBucketPolicy",
        "obs:bucket:DeleteBucketCustomDomainConfiguration",
        "obs:object:RestoreObject",
        "obs:bucket:DeleteBucket",
        "obs:object:ModifyObjectMetaData",
        "obs:bucket:DeleteBucketInventoryConfiguration",
        "obs:bucket:DeleteReplicationConfiguration",
        "obs:bucket:DeleteBucketTagging"
      ]
    }
  ]
}
EOT
role_description = "Created by Terraform"

# IAM user group configuration
group_name = "tf_test_group"

# IAM project configuration
authorized_project_name = "cn-north-4"

# IAM user configuration
users_configuration = [
  {
    name = "tf_test_user"
  }
]
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command line parameters: `terraform apply -var="role_name=my-role" -var="group_name=my-group"`
2. Environment variables: `export TF_VAR_role_name=my-role`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 11. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating IAM roles, user groups, and users, and authorize users through user groups
4. Run `terraform show` to view the created IAM resource details

## Reference Information

- [Huawei Cloud IAM Product Documentation](https://support.huaweicloud.com/intl/en-us/iam/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For IAM Users Authorized Through Group](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/iam/users-authorized-through-group)
