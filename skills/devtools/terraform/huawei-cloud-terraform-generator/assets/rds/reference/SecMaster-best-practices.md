# Deploy Playbook Rule and Trigger by Event

## Application Scenario

SecMaster is a next-generation cloud native security operations center. Based on years of Huawei Cloud experience in cloud security, it enables integrated and automatic security operations through cloud asset management, security posture management, security information and incident management, security orchestration and automatic response, cloud security overview, simplified cloud security configuration, configurable defense policies, and intelligent and fast threat detection and response. Through SecMaster's security playbook functionality, you can create custom security response processes to achieve automatic identification, analysis, and handling of security events.

This best practice will introduce how to use Terraform to automatically deploy a security playbook rule and trigger it by event, including workspace query, playbook creation, version management, rule configuration, action configuration, approval, and enablement steps. Through the event trigger mechanism, when security events that meet the rule conditions occur, the system will automatically execute corresponding security actions, achieving automated response to security events.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Workspaces Query Data Source (data.huaweicloud\_secmaster\_workspaces)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/secmaster_workspaces)
- [Data Classes Query Data Source (data.huaweicloud\_secmaster\_data\_classes)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/secmaster_data_classes)
- [Workflows Query Data Source (data.huaweicloud\_secmaster\_workflows)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/secmaster_workflows)

### Resources

- [Security Playbook Resource (huaweicloud\_secmaster\_playbook)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/secmaster_playbook)
- [Security Playbook Version Resource (huaweicloud\_secmaster\_playbook\_version)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/secmaster_playbook_version)
- [Security Playbook Rule Resource (huaweicloud\_secmaster\_playbook\_rule)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/secmaster_playbook_rule)
- [Security Playbook Action Resource (huaweicloud\_secmaster\_playbook\_action)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/secmaster_playbook_action)
- [Security Playbook Version Action Resource (huaweicloud\_secmaster\_playbook\_version\_action)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/secmaster_playbook_version_action)
- [Security Playbook Approval Resource (huaweicloud\_secmaster\_playbook\_approval)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/secmaster_playbook_approval)
- [Security Playbook Enable Resource (huaweicloud\_secmaster\_playbook\_enable)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/secmaster_playbook_enable)

### Resource/Data Source Dependencies

```
data.huaweicloud_secmaster_workspaces
    ├── huaweicloud_secmaster_playbook
    ├── huaweicloud_secmaster_playbook_version
    ├── huaweicloud_secmaster_playbook_rule
    ├── huaweicloud_secmaster_playbook_action
    ├── huaweicloud_secmaster_playbook_version_action
    ├── huaweicloud_secmaster_playbook_approval
    ├── huaweicloud_secmaster_playbook_enable
    ├── data.huaweicloud_secmaster_data_classes
    └── data.huaweicloud_secmaster_workflows

data.huaweicloud_secmaster_data_classes
    ├── huaweicloud_secmaster_playbook_version
    └── data.huaweicloud_secmaster_workflows
        └── huaweicloud_secmaster_playbook_action

huaweicloud_secmaster_playbook
    └── huaweicloud_secmaster_playbook_version
        ├── huaweicloud_secmaster_playbook_rule
        ├── huaweicloud_secmaster_playbook_action
        └── huaweicloud_secmaster_playbook_version_action
            └── huaweicloud_secmaster_playbook_approval
                └── huaweicloud_secmaster_playbook_enable

huaweicloud_secmaster_playbook_rule
    └── huaweicloud_secmaster_playbook_action
```

## Implementation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://hcbp.gitbook.io/huaweicloud-provider/product-introduction/prepare_before_deploy) for configuration introduction.

### 2. Query Workspace Information Through Data Source

Add the following script to the TF file (such as main.tf) to instruct Terraform to perform a data source query, the query results are used to create security playbook resources:

```hcl
variable "workspace_id" {
  description = "The ID of the SecMaster workspace"
  type        = string
  default     = ""
}

variable "workspace_name" {
  description = "The name of the SecMaster workspace"
  type        = string
  default     = ""
  nullable    = false

  validation {
    condition     = var.workspace_id != "" || var.workspace_name != ""
    error_message = "At least one of workspace_id and workspace_name must be provided."
  }
}

# Query all workspace information that meets the conditions in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted) for creating security playbook resources
data "huaweicloud_secmaster_workspaces" "test" {
  count = var.workspace_id == "" ? 1 : 0

  name = var.workspace_name
}
```

**Parameter Description**:

- **count**: The number of data source queries, used to control whether to query the workspace list, only when `var.workspace_id` is empty, query the workspace list
- **name**: The name of the workspace, assigned by referencing the input variable `workspace_name`

### 3. Create Security Playbook Resource

Add the following script to the TF file to instruct Terraform to create a security playbook resource:

```hcl
variable "playbook_name" {
  description = "The name of the SecMaster playbook"
  type        = string
}

# Create a security playbook resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_secmaster_playbook" "test" {
  workspace_id = var.workspace_id != "" ? var.workspace_id : try(data.huaweicloud_secmaster_workspaces.test[0].workspaces[0].id, null)
  name         = var.playbook_name

  lifecycle {
    ignore_changes = [
      workspace_id
    ]
  }
}
```

**Parameter Description**:

- **workspace\_id**: The workspace ID to which the security playbook belongs, if workspace ID is specified, use that value, otherwise assign based on the return result of the workspace list query data source
- **name**: The name of the security playbook, assigned by referencing the input variable `playbook_name`
- **lifecycle**: Lifecycle configuration block, used to control the lifecycle behavior of resources
  - **ignore\_changes**: Specifies attribute changes to be ignored in subsequent applies, set to ignore changes to `workspace_id`

### 4. Query Data Class Information Through Data Source

Add the following script to the TF file to instruct Terraform to query data class information:

```hcl
# Query all data class information in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted) for creating security playbook version resources
data "huaweicloud_secmaster_data_classes" "test" {
  workspace_id = var.workspace_id != "" ? var.workspace_id : try(data.huaweicloud_secmaster_workspaces.test[0].workspaces[0].id, null)
}
```

**Parameter Description**:

- **workspace\_id**: The workspace ID to which the data class belongs, if workspace ID is specified, use that value, otherwise assign based on the return result of the workspace list query data source

### 5. Create Security Playbook Version Resource

Add the following script to the TF file to instruct Terraform to create a security playbook version resource:

```hcl
# Create a security playbook version resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_secmaster_playbook_version" "test" {
  workspace_id      = var.workspace_id != "" ? var.workspace_id : try(data.huaweicloud_secmaster_workspaces.test[0].workspaces[0].id, null)
  playbook_id       = huaweicloud_secmaster_playbook.test.id
  dataclass_id      = try(data.huaweicloud_secmaster_data_classes.test.data_classes[0].id, null)
  rule_enable       = true
  trigger_type      = "EVENT"
  dataobject_create = true
  action_strategy   = "ASYNC"

  lifecycle {
    ignore_changes = [
      workspace_id,
      dataclass_id
    ]
  }
}
```

**Parameter Description**:

- **workspace\_id**: The workspace ID to which the security playbook version belongs, if workspace ID is specified, use that value, otherwise assign based on the return result of the workspace list query data source
- **playbook\_id**: The playbook ID to which the security playbook version belongs, referencing the ID of the security playbook resource created earlier
- **dataclass\_id**: The data class ID associated with the security playbook version, assigned based on the return result of the data class list query data source
- **rule\_enable**: Whether to enable rules, set to true to enable rule functionality
- **trigger\_type**: Trigger type, set to "EVENT" to trigger by event
- **dataobject\_create**: Whether to create data objects, set to true to create data objects
- **action\_strategy**: Action strategy, set to "ASYNC" to execute actions asynchronously
- **lifecycle**: Lifecycle configuration block, used to control the lifecycle behavior of resources
  - **ignore\_changes**: Specifies attribute changes to be ignored in subsequent applies, set to ignore changes to `workspace_id` and `dataclass_id`

### 6. Create Security Playbook Rule Resource

Add the following script to the TF file to instruct Terraform to create a security playbook rule resource:

```hcl
variable "rule_expression_type" {
  description = "The expression type of the playbook rule"
  type        = string
  default     = "custom"
}

variable "rule_conditions" {
  description = "The condition rule list of the playbook"
  type = list(object({
    name   = string
    detail = string
    data   = list(string)
  }))

  validation {
    condition     = length(var.rule_conditions) >= 2
    error_message = "The length of rule_conditions must be greater than or equal to 2."
  }
}

# Create a security playbook rule resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_secmaster_playbook_rule" "test" {
  workspace_id    = var.workspace_id != "" ? var.workspace_id : try(data.huaweicloud_secmaster_workspaces.test[0].workspaces[0].id, null)
  version_id      = huaweicloud_secmaster_playbook_version.test.id
  expression_type = var.rule_expression_type

  dynamic "conditions" {
    for_each = var.rule_conditions
    content {
      name   = conditions.value.name
      detail = conditions.value.detail
      data   = conditions.value.data
    }
  }

  logics = split(",", join(",AND,", [
    for condition in var.rule_conditions : condition.name
  ])) # Using AND logic to combine conditions

  lifecycle {
    ignore_changes = [
      workspace_id
    ]
  }
}
```

**Parameter Description**:

- **workspace\_id**: The workspace ID to which the security playbook rule belongs, if workspace ID is specified, use that value, otherwise assign based on the return result of the workspace list query data source
- **version\_id**: The version ID to which the security playbook rule belongs, referencing the ID of the security playbook version resource created earlier
- **expression\_type**: The expression type of the rule, assigned by referencing the input variable `rule_expression_type`, default is "custom" indicating custom expression
- **conditions**: Condition configuration block (dynamic block), dynamically created based on the input variable `rule_conditions`
  - **name**: The name of the condition, assigned by referencing the condition configuration in the input variable
  - **detail**: The detailed information of the condition, assigned by referencing the condition configuration in the input variable
  - **data**: The data of the condition, assigned by referencing the condition configuration in the input variable
- **logics**: The logical combination of conditions, using AND logic to combine all conditions together
- **lifecycle**: Lifecycle configuration block, used to control the lifecycle behavior of resources
  - **ignore\_changes**: Specifies attribute changes to be ignored in subsequent applies, set to ignore changes to `workspace_id`

> Note: The length of `rule_conditions` must be greater than or equal to 2, and conditions are combined using AND logic.

### 7. Query Workflow Information Through Data Source

Add the following script to the TF file to instruct Terraform to query workflow information:

```hcl
# Query all workflow information that meets the conditions in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted) for creating security playbook action resources
data "huaweicloud_secmaster_workflows" "test" {
  workspace_id  = var.workspace_id != "" ? var.workspace_id : try(data.huaweicloud_secmaster_workspaces.test[0].workspaces[0].id, null)
  data_class_id = try(data.huaweicloud_secmaster_data_classes.test.data_classes[0].id, null)
}
```

**Parameter Description**:

- **workspace\_id**: The workspace ID to which the workflow belongs, if workspace ID is specified, use that value, otherwise assign based on the return result of the workspace list query data source
- **data\_class\_id**: The data class ID associated with the workflow, assigned based on the return result of the data class list query data source

### 8. Create Security Playbook Action Resource

Add the following script to the TF file to instruct Terraform to create a security playbook action resource:

```hcl
# Create a security playbook action resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_secmaster_playbook_action" "test" {
  workspace_id = var.workspace_id != "" ? var.workspace_id : try(data.huaweicloud_secmaster_workspaces.test[0].workspaces[0].id, null)
  version_id   = huaweicloud_secmaster_playbook_version.test.id
  action_id    = try(data.huaweicloud_secmaster_workflows.test.workflows[0].id, null)
  name         = try(data.huaweicloud_secmaster_workflows.test.workflows[0].name, null)

  lifecycle {
    ignore_changes = [
      workspace_id,
      action_id,
      name
    ]
  }

  depends_on = [
    huaweicloud_secmaster_playbook_rule.test
  ]
}
```

**Parameter Description**:

- **workspace\_id**: The workspace ID to which the security playbook action belongs, if workspace ID is specified, use that value, otherwise assign based on the return result of the workspace list query data source
- **version\_id**: The version ID to which the security playbook action belongs, referencing the ID of the security playbook version resource created earlier
- **action\_id**: The action ID, assigned based on the return result of the workflow list query data source
- **name**: The name of the action, assigned based on the return result of the workflow list query data source
- **lifecycle**: Lifecycle configuration block, used to control the lifecycle behavior of resources
  - **ignore\_changes**: Specifies attribute changes to be ignored in subsequent applies, set to ignore changes to `workspace_id`, `action_id`, and `name`
- **depends\_on**: Explicit dependency relationship, specifying that the security playbook action resource depends on the security playbook rule resource, ensuring that rules are created before actions

### 9. Create Security Playbook Version Action Resource

Add the following script to the TF file to instruct Terraform to create a security playbook version action resource:

```hcl
# Create a security playbook version action resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_secmaster_playbook_version_action" "test" {
  workspace_id = var.workspace_id != "" ? var.workspace_id : try(data.huaweicloud_secmaster_workspaces.test[0].workspaces[0].id, null)
  version_id   = huaweicloud_secmaster_playbook_version.test.id
  status       = "APPROVING"

  depends_on = [huaweicloud_secmaster_playbook_action.test]

  lifecycle {
    ignore_changes = [
      status,
      enabled
    ]
  }
}
```

**Parameter Description**:

- **workspace\_id**: The workspace ID to which the security playbook version action belongs, if workspace ID is specified, use that value, otherwise assign based on the return result of the workspace list query data source
- **version\_id**: The version ID to which the security playbook version action belongs, referencing the ID of the security playbook version resource created earlier
- **status**: The status of the version action, set to "APPROVING" indicating pending approval status
- **depends\_on**: Explicit dependency relationship, specifying that the security playbook version action resource depends on the security playbook action resource, ensuring that actions are created before version actions
- **lifecycle**: Lifecycle configuration block, used to control the lifecycle behavior of resources
  - **ignore\_changes**: Specifies attribute changes to be ignored in subsequent applies, set to ignore changes to `status` and `enabled`

### 10. Create Security Playbook Approval Resource

Add the following script to the TF file to instruct Terraform to create a security playbook approval resource:

```hcl
variable "approval_content" {
  description = "The approval content for the playbook version"
  type        = string
  default     = "Approved for production use"
}

# Create a security playbook approval resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_secmaster_playbook_approval" "test" {
  workspace_id = var.workspace_id != "" ? var.workspace_id : try(data.huaweicloud_secmaster_workspaces.test[0].workspaces[0].id, null)
  version_id   = huaweicloud_secmaster_playbook_version.test.id
  result       = "PASS"
  content      = var.approval_content

  lifecycle {
    ignore_changes = [
      workspace_id
    ]
  }

  depends_on = [
    huaweicloud_secmaster_playbook_version_action.test
  ]
}
```

**Parameter Description**:

- **workspace\_id**: The workspace ID to which the security playbook approval belongs, if workspace ID is specified, use that value, otherwise assign based on the return result of the workspace list query data source
- **version\_id**: The version ID to which the security playbook approval belongs, referencing the ID of the security playbook version resource created earlier
- **result**: The approval result, set to "PASS" indicating approval passed
- **content**: The approval content, assigned by referencing the input variable `approval_content`, default is "Approved for production use"
- **lifecycle**: Lifecycle configuration block, used to control the lifecycle behavior of resources
  - **ignore\_changes**: Specifies attribute changes to be ignored in subsequent applies, set to ignore changes to `workspace_id`
- **depends\_on**: Explicit dependency relationship, specifying that the security playbook approval resource depends on the security playbook version action resource, ensuring that version actions are created before approval

### 11. Create Security Playbook Enable Resource

Add the following script to the TF file to instruct Terraform to create a security playbook enable resource:

```hcl
# Create a security playbook enable resource in the specified region (defaults to the region specified in the current provider block when the region parameter is omitted)
resource "huaweicloud_secmaster_playbook_enable" "test" {
  workspace_id      = var.workspace_id != "" ? var.workspace_id : try(data.huaweicloud_secmaster_workspaces.test[0].workspaces[0].id, null)
  playbook_id       = huaweicloud_secmaster_playbook.test.id
  playbook_name     = huaweicloud_secmaster_playbook.test.name
  active_version_id = huaweicloud_secmaster_playbook_approval.test.id

  lifecycle {
    ignore_changes = [
      workspace_id
    ]
  }
}
```

**Parameter Description**:

- **workspace\_id**: The workspace ID to which the security playbook enable belongs, if workspace ID is specified, use that value, otherwise assign based on the return result of the workspace list query data source
- **playbook\_id**: The playbook ID to be enabled, referencing the ID of the security playbook resource created earlier
- **playbook\_name**: The playbook name to be enabled, referencing the name of the security playbook resource created earlier
- **active\_version\_id**: The version ID to be activated, referencing the ID of the security playbook approval resource created earlier
- **lifecycle**: Lifecycle configuration block, used to control the lifecycle behavior of resources
  - **ignore\_changes**: Specifies attribute changes to be ignored in subsequent applies, set to ignore changes to `workspace_id`

### 12. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content, and these input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time it is executed.

Create a `terraform.tfvars` file in the working directory, with example content as follows:

```hcl
# Workspace configuration
workspace_name   = "tf_test_workspace"
playbook_name    = "tf_test_playbook"

# Rule configuration
rule_conditions  = [
  {
    name = "condition1",
    detail = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    data = [
      "environment.domain_id",
      "==",
      "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    ]
  },
  {
    name = "condition2",
    detail = "cn-xxx-x",
    data = [
      "environment.region_id",
      "==",
      "cn-xxx-x",
    ]
  }
]

# Approval configuration
approval_content = "Approved for production use"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content in this `tfvars` file when executing terraform commands, other names need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="workspace_name=my-workspace" -var="playbook_name=my-playbook"`
2. Environment variables: `export TF_VAR_workspace_name=my-workspace`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 13. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the security playbook rule and trigger it by event
4. Run `terraform show` to view the created security playbook rule details

## Reference Information

- [Huawei Cloud SecMaster Product Documentation](https://support.huaweicloud.com/intl/en-us/secmaster/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For SecMaster Playbook Rule and Trigger by Event](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/secmaster/playbook/custom-rule-and-trigger-by-event)

# Deploy Workspace

## Application Scenario

Security Master (SecMaster) is a security situation awareness and security operations platform provided by Huawei Cloud, supporting unified management, analysis, and response of security events, helping you achieve automation and intelligence in security operations. Workspace is a fundamental resource of SecMaster, used to isolate and manage security resources for different business scenarios. By creating workspaces, independent security operations environments can be created under specified projects, achieving unified management and isolation of security resources. This best practice introduces how to use Terraform to automatically deploy workspaces, including workspace basic information, project configuration, enterprise project configuration, and tag configuration.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [Workspace Resource (huaweicloud\_secmaster\_workspace)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/secmaster_workspace)

### Resource/Data Source Dependencies

```
huaweicloud_secmaster_workspace
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Create Workspace

Add the following script to the TF file (such as main.tf) to create a workspace:

```hcl
variable "workspace_name" {
  description = "The name of the workspace"
  type        = string
}

variable "workspace_project_name" {
  description = "The name of the project to in which to create the workspace"
  type        = string
}

variable "workspace_description" {
  description = "The description of the workspace"
  type        = string
  default     = ""
}

variable "enterprise_project_id" {
  description = "The ID of the enterprise project to which the workspace belongs"
  type        = string
  default     = null
}

variable "workspace_tags" {
  description = "The key/value pairs to associate with the workspace"
  type        = map(string)
  default     = {}
}

# Create workspace resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_secmaster_workspace" "test" {
  name                  = var.workspace_name
  project_name          = var.workspace_project_name
  description           = var.workspace_description
  enterprise_project_id = var.enterprise_project_id
  tags                  = var.workspace_tags
}
```

**Parameter Description**:

- **name**: Workspace name, assigned by referencing the input variable `workspace_name`
- **project\_name**: Project name, assigned by referencing the input variable `workspace_project_name`, used to specify the project in which to create the workspace
- **description**: Workspace description, assigned by referencing the input variable `workspace_description`, optional parameter
- **enterprise\_project\_id**: Enterprise project ID, assigned by referencing the input variable `enterprise_project_id`, used to specify the enterprise project to which the workspace belongs, optional parameter
- **tags**: Tags, assigned by referencing the input variable `workspace_tags`, used to add key-value pair tags to the workspace, optional parameter

> Note: Workspaces must be created under specified projects. Enterprise project IDs are used to achieve unified management and isolation of resources. If not specified, the default enterprise project is used. Tags can be used for resource classification and management.

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Workspace basic information (Required)
workspace_name         = "tf_test_workspace"
workspace_project_name = "cn-north-4"
workspace_description  = "This is a SecMaster workspace created by Terraform"

# Enterprise project configuration (Optional)
enterprise_project_id = "0"

# Tag configuration (Optional)
workspace_tags = {
  owner = "terraform"
}
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="workspace_name=tf_test_workspace" -var="workspace_project_name=cn-north-4"`
2. Environment variables: `export TF_VAR_workspace_name=tf_test_workspace`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the workspace
4. Run `terraform show` to view the created workspace

## Reference Information

- [Huawei Cloud SecMaster Product Documentation](https://support.huaweicloud.com/secmaster/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Workspace](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/secmaster/workspace)

# Deploy Workflow Version

## Application Scenario

Security Master (SecMaster) is a security situation awareness and security operations platform provided by Huawei Cloud, supporting unified management, analysis, and response of security events, helping you achieve automation and intelligence in security operations. Through workflow version functionality, different versions can be created for workflows, achieving workflow version management and iterative updates. Workflow versions include Base64-encoded workflow topology diagrams and parameter configurations, supporting JSON-format task flow definitions. This best practice introduces how to use Terraform to automatically deploy workflow versions, including workspace query, workflow query, and workflow version creation.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Data Sources

- [Workspace Query Data Source (data.huaweicloud\_secmaster\_workspaces)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/secmaster_workspaces)
- [Workflow Query Data Source (data.huaweicloud\_secmaster\_workflows)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/data-sources/secmaster_workflows)

### Resources

- [Workflow Version Resource (huaweicloud\_secmaster\_workflow\_version)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/secmaster_workflow_version)

### Resource/Data Source Dependencies

```
data.huaweicloud_secmaster_workspaces
    └── data.huaweicloud_secmaster_workflows
        └── huaweicloud_secmaster_workflow_version
```

> Note: Workspace and workflow queries are optional. If `workspace_id` and `workflow_id` are provided, these IDs are used directly; otherwise, the corresponding IDs are queried by name.

## Operation Steps

### 1. Script Preparation

Prepare the TF file (such as main.tf) for writing the current best practice script in the specified workspace, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. For configuration details, refer to the introduction in [Preparation Before Deploying Huawei Cloud Resources](https://github.com/chnsz/hcbp-demo/blob/master/docs/introductions/prepare_before_deploy.md).

### 2. Query Workspace (Optional)

Add the following script to the TF file (such as main.tf) to query workspace (optional):

```hcl
variable "workspace_id" {
  description = "The ID of the workspace"
  type        = string
  default     = ""
  nullable    = false
}

variable "workspace_name" {
  description = "The name of the workspace"
  type        = string
  default     = ""
  nullable    = false

  validation {
    condition     = var.workspace_id != "" || var.workspace_name != ""
    error_message = "At least one of workspace_id and workspace_name must be provided."
  }
}

# Query workspace (query by name when workspace_id is empty)
data "huaweicloud_secmaster_workspaces" "test" {
  count = var.workspace_id == "" ? 1 : 0

  name = var.workspace_name
}
```

**Parameter Description**:

- **count**: Data source count, creates data source for query when `workspace_id` is empty
- **name**: Workspace name, assigned by referencing the input variable `workspace_name`

> Note: If `workspace_id` is provided, workspace query is not needed; if only `workspace_name` is provided, workspace ID needs to be queried through data source.

### 3. Query Workflow (Optional)

Add the following script to the TF file (such as main.tf) to query workflow (optional):

```hcl
variable "workflow_id" {
  description = "The ID of the workflow"
  type        = string
  default     = ""
  nullable    = false
}

variable "workflow_name" {
  description = "The name of the workflow"
  type        = string
}

# Query workflow (query by name when workflow_id is empty)
data "huaweicloud_secmaster_workflows" "test" {
  count = var.workflow_id == "" ? 1 : 0

  workspace_id = var.workspace_id != "" ? var.workspace_id : try(data.huaweicloud_secmaster_workspaces.test[0].workspaces[0].id, null)
  name         = var.workflow_name
}
```

**Parameter Description**:

- **count**: Data source count, creates data source for query when `workflow_id` is empty
- **workspace\_id**: Workspace ID, prioritizes the input `workspace_id`, uses queried workspace ID if empty
- **name**: Workflow name, assigned by referencing the input variable `workflow_name`

> Note: If `workflow_id` is provided, workflow query is not needed; if only `workflow_name` is provided, workflow ID needs to be queried through data source.

### 4. Create Workflow Version

Add the following script to the TF file (such as main.tf) to create workflow version:

```hcl
variable "workflow_version_taskflow" {
  description = "The Base64 encoded of the workflow topology diagram"
  type        = string
}

variable "workflow_version_taskconfig" {
  description = "The parameters configuration of the workflow topology diagram"
  type        = string
}

variable "workflow_version_taskflow_type" {
  description = "The taskflow type of the workflow"
  type        = string
  default     = "JSON"
}

variable "workflow_version_aop_type" {
  description = "The aop type of the workflow"
  type        = string
  default     = "NORMAL"
}

variable "workflow_version_description" {
  description = "The description of the workflow version"
  type        = string
  default     = ""
}

# Create workflow version resource in the specified region (defaults to the region specified in the current provider block when region parameter is omitted)
resource "huaweicloud_secmaster_workflow_version" "test" {
  workspace_id  = var.workspace_id != "" ? var.workspace_id : try(data.huaweicloud_secmaster_workspaces.test[0].workspaces[0].id, null)
  workflow_id    = var.workflow_id != "" ? var.workflow_id : try(data.huaweicloud_secmaster_workflows.test[0].workflows[0].id, null)
  name           = var.workflow_name
  taskflow       = var.workflow_version_taskflow
  taskconfig     = var.workflow_version_taskconfig
  taskflow_type  = var.workflow_version_taskflow_type
  aop_type       = var.workflow_version_aop_type
  description    = var.workflow_version_description
}
```

**Parameter Description**:

- **workspace\_id**: Workspace ID, prioritizes the input `workspace_id`, uses queried workspace ID if empty
- **workflow\_id**: Workflow ID, prioritizes the input `workflow_id`, uses queried workflow ID if empty
- **name**: Workflow name, assigned by referencing the input variable `workflow_name`
- **taskflow**: Base64-encoded workflow topology diagram, assigned by referencing the input variable `workflow_version_taskflow`
- **taskconfig**: Parameter configuration of the workflow topology diagram, assigned by referencing the input variable `workflow_version_taskconfig`
- **taskflow\_type**: Task flow type, assigned by referencing the input variable `workflow_version_taskflow_type`, default is `JSON`
- **aop\_type**: AOP type, assigned by referencing the input variable `workflow_version_aop_type`, default is `NORMAL`
- **description**: Workflow version description, assigned by referencing the input variable `workflow_version_description`, optional parameter

> Note: Workflow topology diagrams need to be provided in Base64-encoded format. Task flow types are usually in JSON format, and AOP types default to NORMAL.

### 5. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. Terraform also provides a method to preset these configurations through `tfvars` files, which can avoid repeated input each time.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Workspace and workflow information (Required)
workspace_name = "tf_test_workspace"
workflow_name  = "tf_test_workflow"

# Workflow version configuration (Required)
workflow_version_taskflow    = "your_workflow_taskflow"
workflow_version_taskconfig  = "your_workflow_taskconfig"
workflow_version_description = "This is a workflow version created by Terraform"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows Terraform to automatically import the variable values in this `tfvars` file when executing terraform commands. For other names, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values through the following methods:

1. Command-line parameters: `terraform apply -var="workspace_name=tf_test_workspace" -var="workflow_name=tf_test_workflow"`
2. Environment variables: `export TF_VAR_workspace_name=tf_test_workspace`
3. Custom-named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command-line parameters > variable files > environment variables > default values.

### 6. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the workflow version
4. Run `terraform show` to view the created workflow version

## Reference Information

- [Huawei Cloud SecMaster Product Documentation](https://support.huaweicloud.com/secmaster/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Workflow Version](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/secmaster/workflow-version)
