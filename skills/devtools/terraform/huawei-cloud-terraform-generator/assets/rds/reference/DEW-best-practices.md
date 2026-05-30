# Deploy CSMS Secret

## Application Scenario

Data Encryption Workshop (DEW) CSMS (Cloud Secret Management Service) secret is a secret management function provided by the DEW service, used to securely store and manage sensitive information such as passwords, API keys, certificates, etc. By creating CSMS secrets, you can store sensitive information in the cloud, achieve unified management and secure access to secrets, avoid hardcoding sensitive information in code or configuration files, and improve application security. Automating CSMS secret creation through Terraform can ensure standardized and consistent secret configuration, improving operational efficiency. This best practice will introduce how to use Terraform to automatically create CSMS secrets.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [CSMS Secret Resource (huaweicloud\_csms\_secret)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/csms_secret)

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create CSMS Secret Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a CSMS secret resource:

```hcl
variable "secret_name" {
  description = "The name of the secret"
  type        = string
}

variable "secret_text" {
  description = "The plaintext of a text secret"
  type        = string
  sensitive   = true
}

variable "secret_type" {
  description = "The type of the secret"
  type        = string
  default     = "COMMON"
}

variable "kms_key_id" {
  description = "The ID of the KMS key used to encrypt the secret"
  type        = string
  default     = ""
}

variable "secret_description" {
  description = "The description of the secret"
  type        = string
  default     = ""
}

variable "enterprise_project_id" {
  description = "The ID of the enterprise project to which the secret belongs"
  type        = string
  default     = null
}

variable "secret_tags" {
  description = "The key/value pairs to associate with the secret"
  type        = map(string)
  default     = {}
}

# Create CSMS secret resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_csms_secret" "test" {
  name                  = var.secret_name
  secret_text           = var.secret_text
  secret_type           = var.secret_type
  kms_key_id            = var.kms_key_id != "" ? var.kms_key_id : null
  description           = var.secret_description
  enterprise_project_id = var.enterprise_project_id
  tags                  = var.secret_tags
}
```

**Parameter Description**:

- **name**: The secret name, assigned by referencing the input variable secret\_name
- **secret\_text**: The plaintext of the secret, assigned by referencing the input variable secret\_text
- **secret\_type**: The secret type, assigned by referencing the input variable secret\_type, default value is "COMMON" (common secret)
- **kms\_key\_id**: The KMS key ID used to encrypt the secret, assigned by referencing the input variable kms\_key\_id, optional parameter, default value is null (use default KMS key)
- **description**: The secret description, assigned by referencing the input variable secret\_description, optional parameter, default value is empty string
- **enterprise\_project\_id**: The enterprise project ID to which the secret belongs, assigned by referencing the input variable enterprise\_project\_id, optional parameter, default value is null
- **tags**: The secret tags, assigned by referencing the input variable secret\_tags, optional parameter, default value is empty map

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# CSMS Secret Configuration
secret_name           = "tf_test_secret"
secret_text           = "your_secret_text"
secret_description    = "This is a CSMS secret created by Terraform"
enterprise_project_id = "0"

# Secret Tags Configuration
secret_tags = {
  owner = "terraform"
}
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially `secret_text` needs to be replaced with the actual secret content
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="secret_name=my_secret" -var="secret_text=my_secret_text"`
2. Environment variables: `export TF_VAR_secret_name=my_secret` and `export TF_VAR_secret_text=my_secret_text`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. Since secret\_text contains sensitive information, it is recommended to use environment variables or encrypted variable files for setting.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create a CSMS secret:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the CSMS secret
4. Run `terraform show` to view the details of the created CSMS secret

> Note: After the CSMS secret is created, sensitive information will be encrypted and stored in the cloud, and can be securely accessed through APIs or the console. Secrets support encryption using KMS keys, providing higher security. Secret tags can help you categorize and manage secrets. Please ensure that secret information is properly kept and do not commit sensitive information to version control systems.

## Reference Information

- [Huawei Cloud DEW Product Documentation](https://support.huaweicloud.com/dew/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For CSMS Secret](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dew/csms-secret)

# Deploy Keypair

## Application Scenario

Data Encryption Workshop (DEW) KPS (Key Pair Service) keypair is a key pair management function provided by the DEW service, used to create and manage SSH key pairs, providing secure login authentication for cloud resources such as ECS instances. By creating KPS keypairs, you can generate SSH key pairs, inject public keys into ECS instances, achieve passwordless login, and improve security and convenience. Automating KPS keypair creation through Terraform can ensure standardized and consistent keypair configuration, improving operational efficiency. This best practice will introduce how to use Terraform to automatically create KPS keypairs.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [KPS Keypair Resource (huaweicloud\_kps\_keypair)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/kps_keypair)

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create KPS Keypair Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a KPS keypair resource:

```hcl
variable "keypair_name" {
  description = "The name of the KPS keypair"
  type        = string
}

variable "keypair_scope" {
  description = "The scope of the KPS keypair"
  type        = string
  default     = "user"
}

variable "keypair_user_id" {
  description = "The user ID to which the KPS keypair belongs"
  type        = string
  default     = ""
}

variable "keypair_encryption_type" {
  description = "The encryption mode of the KPS keypair"
  type        = string
  default     = "kms"
}

variable "kms_key_id" {
  description = "The ID of the KMS key"
  type        = string
  default     = ""
}

variable "kms_key_name" {
  description = "The name of the KMS key"
  type        = string
  default     = ""

  validation {
    condition     = var.keypair_encryption_type != "kms" || (var.kms_key_id != "" || var.kms_key_name != "")
    error_message = "At least one of kms_key_id and kms_key_name must be provided when keypair_encryption_type set to kms"
  }
}

variable "keypair_description" {
  description = "The description of the KPS keypair"
  type        = string
  default     = ""
}

# Create KPS keypair resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_kps_keypair" "test" {
  name            = var.keypair_name
  scope           = var.keypair_scope
  user_id         = var.keypair_user_id != "" ? var.keypair_user_id : null
  encryption_type = var.keypair_encryption_type
  kms_key_id      = var.kms_key_id != "" ? var.kms_key_id : null
  kms_key_name    = var.kms_key_name != "" ? var.kms_key_name : null
  description     = var.keypair_description
}
```

**Parameter Description**:

- **name**: The keypair name, assigned by referencing the input variable keypair\_name
- **scope**: The keypair scope, assigned by referencing the input variable keypair\_scope, default value is "user" (user-level)
- **user\_id**: The user ID to which the keypair belongs, assigned by referencing the input variable keypair\_user\_id, optional parameter, default value is null
- **encryption\_type**: The keypair encryption mode, assigned by referencing the input variable keypair\_encryption\_type, default value is "kms" (use KMS encryption), valid values: default (default encryption), kms (KMS encryption)
- **kms\_key\_id**: The KMS key ID, assigned by referencing the input variable kms\_key\_id, when encryption\_type is "kms", at least one of kms\_key\_id and kms\_key\_name must be provided, optional parameter, default value is null
- **kms\_key\_name**: The KMS key name, assigned by referencing the input variable kms\_key\_name, when encryption\_type is "kms", at least one of kms\_key\_id and kms\_key\_name must be provided, optional parameter, default value is null
- **description**: The keypair description, assigned by referencing the input variable keypair\_description, optional parameter, default value is empty string

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# KPS Keypair Configuration
keypair_name        = "tf_test_keypair"
kms_key_id          = "your_kms_key_id"
keypair_description = "This is a KPS keypair created by Terraform"
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs, especially `kms_key_id` needs to be replaced with the actual KMS key ID (when encryption\_type is "kms")
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="keypair_name=my_keypair" -var="kms_key_id=my_kms_key_id"`
2. Environment variables: `export TF_VAR_keypair_name=my_keypair` and `export TF_VAR_kms_key_id=my_kms_key_id`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values. When encryption\_type is set to "kms", at least one of kms\_key\_id and kms\_key\_name must be provided.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create a KPS keypair:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the KPS keypair
4. Run `terraform show` to view the details of the created KPS keypair

> Note: After the KPS keypair is created, the public key can be injected into ECS instances to achieve passwordless login. Keypairs support encryption using KMS keys, providing higher security. The keypair creation process takes about 5 minutes. Please ensure that private key information is properly kept and do not commit private keys to version control systems.

## Reference Information

- [Huawei Cloud DEW Product Documentation](https://support.huaweicloud.com/dew/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For Keypair](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dew/kps-keypair)

# Deploy KMS Key

## Application Scenario

Data Encryption Workshop (DEW) KMS (Key Management Service) key is a key management function provided by the DEW service, used to create and manage encryption keys, providing encryption protection for cloud data and applications. By creating KMS keys, you can generate and manage keys for data encryption, support multiple encryption algorithms and key types, achieve encrypted storage and transmission of data, and ensure data security. Automating KMS key creation through Terraform can ensure standardized and consistent key configuration, improving operational efficiency. This best practice will introduce how to use Terraform to automatically create KMS keys.

## Related Resources/Data Sources

This best practice involves the following main resources:

### Resources

- [KMS Key Resource (huaweicloud\_kms\_key)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/kms_key)

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create KMS Key Resource

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a KMS key resource:

```hcl
variable "key_name" {
  description = "The alias name of the KMS key"
  type        = string
}

variable "key_algorithm" {
  description = "The generation algorithm of the KMS key"
  type        = string
  default     = "AES_256"
}

variable "key_usage" {
  description = "The usage of the KMS key"
  type        = string
  default     = "ENCRYPT_DECRYPT"
}

variable "key_source" {
  description = "The source of the KMS key"
  type        = string
  default     = "kms"
}

variable "key_description" {
  description = "The description of the KMS key"
  type        = string
  default     = ""
}

variable "enterprise_project_id" {
  description = "The ID of the enterprise project to which the KMS key belongs"
  type        = string
  default     = null
}

variable "key_tags" {
  description = "The key/value pairs to associate with the KMS key"
  type        = map(string)
  default     = {}
}

variable "key_schedule_time" {
  description = "The number of days after which the KMS key is scheduled to be deleted"
  type        = string
  default     = "7"
}

# Create KMS key resource in the specified region (defaults to the region specified in the provider block when region parameter is omitted)
resource "huaweicloud_kms_key" "test" {
  key_alias             = var.key_name
  key_algorithm         = var.key_algorithm
  key_usage             = var.key_usage
  origin                = var.key_source
  key_description       = var.key_description
  enterprise_project_id = var.enterprise_project_id
  tags                  = var.key_tags
  pending_days          = var.key_schedule_time
}
```

**Parameter Description**:

- **key\_alias**: The key alias, assigned by referencing the input variable key\_name
- **key\_algorithm**: The key generation algorithm, assigned by referencing the input variable key\_algorithm, default value is "AES\_256" (AES-256 algorithm)
- **key\_usage**: The key usage, assigned by referencing the input variable key\_usage, default value is "ENCRYPT\_DECRYPT" (encrypt and decrypt)
- **origin**: The key source, assigned by referencing the input variable key\_source, default value is "kms" (generated by KMS)
- **key\_description**: The key description, assigned by referencing the input variable key\_description, optional parameter, default value is empty string
- **enterprise\_project\_id**: The enterprise project ID to which the key belongs, assigned by referencing the input variable enterprise\_project\_id, optional parameter, default value is null
- **tags**: The key tags, assigned by referencing the input variable key\_tags, optional parameter, default value is empty map
- **pending\_days**: The number of days after which the key is scheduled to be deleted, assigned by referencing the input variable key\_schedule\_time, default value is "7" (delete after 7 days)

### 3. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources use input variables to assign configuration content. These input parameters need to be manually entered during subsequent deployment. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# KMS Key Configuration
key_name        = "tf_test_kms_key"
key_description = "This is a KMS key created by Terraform"

# Key Tags Configuration
key_tags = {
  owner = "terraform"
}
```

**Usage**:

1. Save the above content as a `terraform.tfvars` file in the working directory (this filename allows users to automatically import the content of this `tfvars` file when executing terraform commands. For other naming, you need to add `.auto` before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values according to actual needs
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values in this file

In addition to using the `terraform.tfvars` file, you can also set variable values in the following ways:

1. Command line parameters: `terraform apply -var="key_name=my_kms_key" -var="key_algorithm=AES_256"`
2. Environment variables: `export TF_VAR_key_name=my_kms_key` and `export TF_VAR_key_algorithm=AES_256`
3. Custom named variable file: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set through multiple methods, Terraform will use variable values according to the following priority: command line parameters > variable file > environment variables > default values.

### 4. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create a KMS key:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming that the resource plan is correct, run `terraform apply` to start creating the KMS key
4. Run `terraform show` to view the details of the created KMS key

> Note: After the KMS key is created, it can be used to encrypt and decrypt data. Keys support multiple encryption algorithms, such as AES\_256, SM4, etc. Keys support scheduled deletion function, allowing keys to be automatically deleted after a specified number of days. Key tags can help you categorize and manage keys. Please ensure that key information is properly kept and do not commit sensitive information to version control systems.

## Reference Information

- [Huawei Cloud DEW Product Documentation](https://support.huaweicloud.com/dew/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For KMS Key](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/dew/kms-key)
