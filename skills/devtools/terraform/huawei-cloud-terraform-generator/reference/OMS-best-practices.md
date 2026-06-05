# Deploy Object Migration Through Task Group

## Application Scenario

Object Storage Migration Service (OMS) is a one-stop data migration service provided by Huawei Cloud, helping users quickly, securely, and efficiently migrate data from other cloud service providers or local environments to Huawei Cloud Object Storage Service (OBS). OMS service supports multiple data sources, including mainstream cloud storage services such as AWS S3, Alibaba Cloud OSS, Tencent Cloud COS, as well as local file systems.

Task group migration is an important feature of the OMS service, used for batch migration of object storage data. Through task group migration, enterprises can efficiently migrate large amounts of data, supporting incremental synchronization, resumable transfer, data verification, and other functions, ensuring the integrity and consistency of data migration. Task group migration supports advanced features such as bandwidth control, time window settings, failure retry, etc., providing enterprises with reliable data migration solutions. This best practice will introduce how to use Terraform to automatically deploy OMS task group migration tasks, including KMS key creation, OBS bucket configuration, object upload, bucket policy settings, and migration task group creation.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [KMS Key Resource (huaweicloud\_kms\_key)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/kms_key)
- [OBS Bucket Resource (huaweicloud\_obs\_bucket)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket)
- [OBS Bucket Object Resource (huaweicloud\_obs\_bucket\_object)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket_object)
- [OBS Bucket Policy Resource (huaweicloud\_obs\_bucket\_policy)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket_policy)
- [OMS Migration Task Group Resource (huaweicloud\_oms\_migration\_task\_group)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/oms_migration_task_group)

### Resource/Data Source Dependencies

```
huaweicloud_kms_key.test
    └── huaweicloud_obs_bucket.test
        ├── huaweicloud_obs_bucket_object.test
        │   └── huaweicloud_oms_migration_task_group.test
        └── huaweicloud_obs_bucket_policy.test
            └── huaweicloud_oms_migration_task_group.test
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create KMS Key

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a KMS key resource:

```hcl
variable "bucket_encryption" {
  description = "Whether OBS bucket encryption is enabled"
  type        = bool
  default     = true
}

variable "bucket_encryption_key_id" {
  description = "OBS bucket encryption key ID"
  type        = string
  default     = ""
  nullable    = false
}

variable "key_alias" {
  description = "KMS key alias"
  type        = string
  default     = ""
  nullable    = false

  validation {
    condition     = var.key_alias != "" && var.bucket_encryption && var.bucket_encryption_key_id == ""
    error_message = "key_alias must be set when bucket_encryption is true and bucket_encryption_key_id is not set."
  }
}

variable "key_usage" {
  description = "KMS key usage"
  type        = string
  default     = "ENCRYPT_DECRYPT"
}

# Create a KMS key resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_kms_key" "test" {
  count = var.bucket_encryption && var.bucket_encryption_key_id == "" ? 1 : 0

  key_alias = var.key_alias
  key_usage = var.key_usage
}
```

**Parameter Description**:

- **key\_alias**: Key alias, assigned by referencing the input variable key\_alias
- **key\_usage**: Key usage, assigned by referencing the input variable key\_usage
- **count**: Conditional creation, creates when encryption is enabled and key ID is not specified

### 3. Create OBS Bucket

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an OBS bucket resource:

```hcl
variable "bucket_name" {
  description = "OBS bucket name"
  type        = string
}

variable "bucket_storage_class" {
  description = "OBS bucket storage class"
  type        = string
  default     = "STANDARD"
}

variable "bucket_acl" {
  description = "OBS bucket access control list"
  type        = string
  default     = "private"
}

variable "bucket_sse_algorithm" {
  description = "OBS bucket server-side encryption algorithm"
  type        = string
  default     = "kms"
}

variable "bucket_force_destroy" {
  description = "Whether OBS bucket force destroy is enabled"
  type        = bool
  default     = true
}

variable "bucket_tags" {
  description = "OBS bucket tags"
  type        = map(string)
  default     = {}
}

# Create an OBS bucket resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_obs_bucket" "test" {
  bucket        = var.bucket_name
  storage_class = var.bucket_storage_class
  acl           = var.bucket_acl
  encryption    = var.bucket_encryption
  sse_algorithm = var.bucket_encryption ? var.bucket_sse_algorithm : null
  kms_key_id    = var.bucket_encryption ? var.bucket_encryption_key_id != "" ? var.bucket_encryption_key_id : huaweicloud_kms_key.test[0].id : null
  force_destroy = var.bucket_force_destroy
  tags          = var.bucket_tags

  lifecycle {
    ignore_changes = [
      sse_algorithm
    ]
  }
}
```

**Parameter Description**:

- **bucket**: Bucket name, assigned by referencing the input variable bucket\_name
- **storage\_class**: Storage class, assigned by referencing the input variable bucket\_storage\_class
- **acl**: Access control list, assigned by referencing the input variable bucket\_acl
- **encryption**: Whether encryption is enabled, assigned by referencing the input variable bucket\_encryption
- **sse\_algorithm**: Server-side encryption algorithm, uses kms algorithm when encryption is enabled
- **kms\_key\_id**: KMS key ID, prioritizes using input variable, uses created KMS key if empty
- **force\_destroy**: Force destroy, assigned by referencing the input variable bucket\_force\_destroy
- **tags**: Tags, assigned by referencing the input variable bucket\_tags

### 4. Create OBS Bucket Object

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an OBS bucket object resource:

```hcl
variable "object_extension_name" {
  description = "OBS object extension name"
  type        = string
  default     = ".txt"
  nullable    = false
}

variable "object_name" {
  description = "OBS object name"
  type        = string
}

variable "object_upload_content" {
  description = "OBS object upload content"
  type        = string
}

# Create an OBS bucket object resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_obs_bucket_object" "test" {
  bucket       = huaweicloud_obs_bucket.test.id
  key          = var.object_extension_name != "" ? format("%s%s", var.object_name, var.object_extension_name) : var.object_name
  content_type = "application/xml"
  content      = var.object_upload_content
}
```

**Parameter Description**:

- **bucket**: Bucket ID, assigned by referencing the OBS bucket resource (huaweicloud\_obs\_bucket.test) ID
- **key**: Object key name, generated by combining extension name and object name
- **content\_type**: Content type, set to application/xml
- **content**: Object content, assigned by referencing the input variable object\_upload\_content

### 5. Create OBS Bucket Policy

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an OBS bucket policy resource:

```hcl
# Create an OBS bucket policy resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_obs_bucket_policy" "test" {
  bucket = huaweicloud_obs_bucket.test.id
  policy = <<POLICY
{
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {"ID": "*"},
      "Action": ["GetObject"],
      "Resource": "${huaweicloud_obs_bucket.test.id}/*"
    }
  ]
}
POLICY
}
```

**Parameter Description**:

- **bucket**: Bucket ID, assigned by referencing the OBS bucket resource (huaweicloud\_obs\_bucket.test) ID
- **policy**: Bucket policy, allows all users to read objects in the bucket

### 6. Create OMS Migration Task Group

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an OMS migration task group resource:

```hcl
variable "group_action_type" {
  description = "Migration task group action type"
  type        = string
  default     = "stop"
}

variable "group_type" {
  description = "Migration task group type"
  type        = string
  default     = "PREFIX"
}

variable "group_enable_kms" {
  description = "Whether migration task group enables KMS"
  type        = bool
  default     = true
}

variable "group_migrate_since" {
  description = "Migration task group migration start time"
  type        = string
  default     = null
}

variable "group_object_overwrite_mode" {
  description = "Migration task group object overwrite mode"
  type        = string
  default     = "CRC64_COMPARISON_OVERWRITE"
}

variable "group_consistency_check" {
  description = "Migration task group consistency check"
  type        = string
  default     = "crc64"
}

variable "group_enable_requester_pays" {
  description = "Whether migration task group enables requester pays"
  type        = bool
  default     = true
}

variable "group_enable_failed_object_recording" {
  description = "Whether migration task group enables failed object recording"
  type        = bool
  default     = true
}

variable "target_bucket_configuration" {
  description = "Target bucket configuration"
  type        = object({
    region      = optional(string, "")
    bucket      = string
    access_key  = optional(string, "")
    secret_key  = optional(string, "")
  })
}

variable "bandwidth_policy_configurations" {
  description = "Bandwidth policy configuration"
  type        = list(object({
    max_bandwidth = number
    start         = string
    end           = string
  }))
}

# Create an OMS migration task group resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_oms_migration_task_group" "test" {
  depends_on = [
    huaweicloud_obs_bucket_object.test,
    huaweicloud_obs_bucket_policy.test
  ]

  action                         = var.group_action_type
  type                           = var.group_type
  enable_kms                     = var.group_enable_kms
  migrate_since                  = var.group_migrate_since
  object_overwrite_mode          = var.group_object_overwrite_mode
  consistency_check              = var.group_consistency_check
  enable_requester_pays          = var.group_enable_requester_pays
  enable_failed_object_recording = var.group_enable_failed_object_recording

  source_object {
    data_source = "HuaweiCloud"
    region      = huaweicloud_obs_bucket.test.region
    bucket      = huaweicloud_obs_bucket.test.id
    access_key  = var.access_key
    secret_key  = var.secret_key
    object      = [var.object_name]
  }

  destination_object {
    region     = var.target_bucket_configuration.region != "" ? var.target_bucket_configuration.region : huaweicloud_obs_bucket.test.region
    bucket     = var.target_bucket_configuration.bucket
    access_key = var.target_bucket_configuration.access_key != "" ? var.target_bucket_configuration.access_key : var.access_key
    secret_key = var.target_bucket_configuration.secret_key != "" ? var.target_bucket_configuration.secret_key : var.secret_key
  }

  dynamic "bandwidth_policy" {
    for_each = var.bandwidth_policy_configurations

    content {
      max_bandwidth = bandwidth_policy.value["max_bandwidth"]
      start         = bandwidth_policy.value["start"]
      end           = bandwidth_policy.value["end"]
    }
  }
}
```

**Parameter Description**:

- **action**: Action type, assigned by referencing the input variable group\_action\_type
- **type**: Task group type, assigned by referencing the input variable group\_type
- **enable\_kms**: Whether KMS is enabled, assigned by referencing the input variable group\_enable\_kms
- **migrate\_since**: Migration start time, assigned by referencing the input variable group\_migrate\_since
- **object\_overwrite\_mode**: Object overwrite mode, assigned by referencing the input variable group\_object\_overwrite\_mode
- **consistency\_check**: Consistency check, assigned by referencing the input variable group\_consistency\_check
- **enable\_requester\_pays**: Whether requester pays is enabled, assigned by referencing the input variable group\_enable\_requester\_pays
- **enable\_failed\_object\_recording**: Whether failed object recording is enabled, assigned by referencing the input variable group\_enable\_failed\_object\_recording
- **source\_object**: Source object configuration, includes data source, region, bucket, access key, and object list
- **destination\_object**: Destination object configuration, includes region, bucket, and access key
- **bandwidth\_policy**: Bandwidth policy, dynamically creates bandwidth control configuration

### 7. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# KMS key configuration
key_alias   = "tf-test-obs-key"
key_usage   = "ENCRYPT_DECRYPT"

# OBS bucket configuration
bucket_name        = "tf-test-obs-bucket"
bucket_storage_class = "STANDARD"
bucket_acl         = "private"
bucket_encryption  = true
bucket_sse_algorithm = "kms"
bucket_force_destroy = true
bucket_tags        = {
  environment = "test"
  created_by  = "terraform"
}

# OBS object configuration
object_extension_name = ".txt"
object_name           = "tf-test-obs-object"
object_upload_content = <<EOT
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
EOT

# Migration task group configuration
group_action_type = "stop"
group_type = "PREFIX"
group_enable_kms = true
group_migrate_since = null
group_object_overwrite_mode = "CRC64_COMPARISON_OVERWRITE"
group_consistency_check = "crc64"
group_enable_requester_pays = true
group_enable_failed_object_recording = true

# Target bucket configuration
target_bucket_configuration = {
  bucket = "tf-test-obs-bucket-target"
}

# Bandwidth policy configuration
bandwidth_policy_configurations = [
  {
    max_bandwidth = 1
    start         = "03:00"
    end           = "04:00"
  }
]
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="bucket_name=my-bucket" -var="object_name=my-object"`
2. Environment variables: `export TF_VAR_bucket_name=my-bucket`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 8. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating migration task groups
4. Run `terraform show` to view the created migration task groups

## Reference Information

- [Huawei Cloud OMS Product Documentation](https://support.huaweicloud.com/oms/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For OMS Object Migration Through Task Group](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/oms/migrate-objects-by-group)

# Deploy Object Migration Through Task

## Application Scenario

Object Storage Migration Service (OMS) is a one-stop data migration service provided by Huawei Cloud, helping users quickly, securely, and efficiently migrate data from other cloud service providers or local environments to Huawei Cloud Object Storage Service (OBS). OMS service supports multiple data sources, including mainstream cloud storage services such as AWS S3, Alibaba Cloud OSS, Tencent Cloud COS, as well as local file systems.

Task migration is the core functionality of the OMS service, used to execute single or batch object storage data migration tasks. Through task migration, enterprises can precisely control the migration process, supporting incremental synchronization, resumable transfer, data verification, and other functions, ensuring the integrity and consistency of data migration. Task migration supports advanced features such as bandwidth control, time window settings, failure retry, etc., providing enterprises with reliable data migration solutions. This best practice will introduce how to use Terraform to automatically deploy OMS task migration, including KMS key creation, OBS bucket configuration, object upload, bucket policy settings, and migration task creation.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [KMS Key Resource (huaweicloud\_kms\_key)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/kms_key)
- [OBS Bucket Resource (huaweicloud\_obs\_bucket)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket)
- [OBS Bucket Object Resource (huaweicloud\_obs\_bucket\_object)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket_object)
- [OBS Bucket Policy Resource (huaweicloud\_obs\_bucket\_policy)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket_policy)
- [OMS Migration Task Resource (huaweicloud\_oms\_migration\_task)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/oms_migration_task)

### Resource/Data Source Dependencies

```
huaweicloud_kms_key.test
    └── huaweicloud_obs_bucket.test
        ├── huaweicloud_obs_bucket_object.test
        │   └── huaweicloud_oms_migration_task.test
        └── huaweicloud_obs_bucket_policy.test
            └── huaweicloud_oms_migration_task.test
```

## Operation Steps

### 1. Script Preparation

Prepare the TF file (e.g., main.tf) in the specified workspace for writing the current best practice script, ensuring that it (or other TF files in the same directory) contains the provider version declaration and Huawei Cloud authentication information required for deploying resources. Refer to the "Preparation Before Deploying Huawei Cloud Resources" document for configuration introduction.

### 2. Create KMS Key

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create a KMS key resource:

```hcl
variable "bucket_encryption" {
  description = "Whether OBS bucket encryption is enabled"
  type        = bool
  default     = true
}

variable "bucket_encryption_key_id" {
  description = "OBS bucket encryption key ID"
  type        = string
  default     = ""
  nullable    = false
}

variable "key_alias" {
  description = "KMS key alias"
  type        = string
  default     = ""
  nullable    = false

  validation {
    condition     = var.key_alias != "" && var.bucket_encryption && var.bucket_encryption_key_id == ""
    error_message = "key_alias must be set when bucket_encryption is true and bucket_encryption_key_id is not set."
  }
}

variable "key_usage" {
  description = "KMS key usage"
  type        = string
  default     = "ENCRYPT_DECRYPT"
}

# Create a KMS key resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_kms_key" "test" {
  count = var.bucket_encryption && var.bucket_encryption_key_id == "" ? 1 : 0

  key_alias = var.key_alias
  key_usage = var.key_usage
}
```

**Parameter Description**:

- **key\_alias**: Key alias, assigned by referencing the input variable key\_alias
- **key\_usage**: Key usage, assigned by referencing the input variable key\_usage
- **count**: Conditional creation, creates when encryption is enabled and key ID is not specified

### 3. Create OBS Bucket

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an OBS bucket resource:

```hcl
variable "bucket_name" {
  description = "OBS bucket name"
  type        = string
}

variable "bucket_storage_class" {
  description = "OBS bucket storage class"
  type        = string
  default     = "STANDARD"
}

variable "bucket_acl" {
  description = "OBS bucket access control list"
  type        = string
  default     = "private"
}

variable "bucket_sse_algorithm" {
  description = "OBS bucket server-side encryption algorithm"
  type        = string
  default     = "kms"
}

variable "bucket_force_destroy" {
  description = "Whether OBS bucket force destroy is enabled"
  type        = bool
  default     = true
}

variable "bucket_tags" {
  description = "OBS bucket tags"
  type        = map(string)
  default     = {}
}

# Create an OBS bucket resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_obs_bucket" "test" {
  bucket        = var.bucket_name
  storage_class = var.bucket_storage_class
  acl           = var.bucket_acl
  encryption    = var.bucket_encryption
  sse_algorithm = var.bucket_encryption ? var.bucket_sse_algorithm : null
  kms_key_id    = var.bucket_encryption ? var.bucket_encryption_key_id != "" ? var.bucket_encryption_key_id : huaweicloud_kms_key.test[0].id : null
  force_destroy = var.bucket_force_destroy
  tags          = var.bucket_tags

  lifecycle {
    ignore_changes = [
      sse_algorithm
    ]
  }
}
```

**Parameter Description**:

- **bucket**: Bucket name, assigned by referencing the input variable bucket\_name
- **storage\_class**: Storage class, assigned by referencing the input variable bucket\_storage\_class
- **acl**: Access control list, assigned by referencing the input variable bucket\_acl
- **encryption**: Whether encryption is enabled, assigned by referencing the input variable bucket\_encryption
- **sse\_algorithm**: Server-side encryption algorithm, uses kms algorithm when encryption is enabled
- **kms\_key\_id**: KMS key ID, prioritizes using input variable, uses created KMS key if empty
- **force\_destroy**: Force destroy, assigned by referencing the input variable bucket\_force\_destroy
- **tags**: Tags, assigned by referencing the input variable bucket\_tags

### 4. Create OBS Bucket Object

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an OBS bucket object resource:

```hcl
variable "object_extension_name" {
  description = "OBS object extension name"
  type        = string
  default     = ".txt"
  nullable    = false
}

variable "object_name" {
  description = "OBS object name"
  type        = string
}

variable "object_upload_content" {
  description = "OBS object upload content"
  type        = string
}

# Create an OBS bucket object resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_obs_bucket_object" "test" {
  bucket       = huaweicloud_obs_bucket.test.id
  key          = var.object_extension_name != "" ? format("%s%s", var.object_name, var.object_extension_name) : var.object_name
  content_type = "application/xml"
  content      = var.object_upload_content
}
```

**Parameter Description**:

- **bucket**: Bucket ID, assigned by referencing the OBS bucket resource (huaweicloud\_obs\_bucket.test) ID
- **key**: Object key name, generated by combining extension name and object name
- **content\_type**: Content type, set to application/xml
- **content**: Object content, assigned by referencing the input variable object\_upload\_content

### 5. Create OBS Bucket Policy

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an OBS bucket policy resource:

```hcl
# Create an OBS bucket policy resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_obs_bucket_policy" "test" {
  bucket = huaweicloud_obs_bucket.test.id
  policy = <<POLICY
{
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {"ID": "*"},
      "Action": ["GetObject"],
      "Resource": "${huaweicloud_obs_bucket.test.id}/*"
    }
  ]
}
POLICY
}
```

**Parameter Description**:

- **bucket**: Bucket ID, assigned by referencing the OBS bucket resource (huaweicloud\_obs\_bucket.test) ID
- **policy**: Bucket policy, allows all users to read objects in the bucket

### 6. Create OMS Migration Task

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an OMS migration task resource:

```hcl
variable "task_is_start" {
  description = "Whether to start migration task"
  type        = bool
  default     = true
}

variable "task_type" {
  description = "Migration task type"
  type        = string
  default     = "prefix"
}

variable "task_enable_kms" {
  description = "Whether migration task enables KMS"
  type        = bool
  default     = true
}

variable "task_migrate_since" {
  description = "Migration task migration start time"
  type        = string
  default     = null
}

variable "task_object_overwrite_mode" {
  description = "Migration task object overwrite mode"
  type        = string
  default     = "CRC64_COMPARISON_OVERWRITE"
}

variable "task_consistency_check" {
  description = "Migration task consistency check"
  type        = string
  default     = "crc64"
}

variable "task_enable_requester_pays" {
  description = "Whether migration task enables requester pays"
  type        = bool
  default     = true
}

variable "task_enable_failed_object_recording" {
  description = "Whether migration task enables failed object recording"
  type        = bool
  default     = true
}

variable "target_bucket_configuration" {
  description = "Target bucket configuration"
  type        = object({
    region      = optional(string, "")
    bucket      = string
    access_key  = optional(string, "")
    secret_key  = optional(string, "")
  })
}

variable "bandwidth_policy_configurations" {
  description = "Bandwidth policy configuration"
  type        = list(object({
    max_bandwidth = number
    start         = string
    end           = string
  }))
}

# Create an OMS migration task resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_oms_migration_task" "test" {
  depends_on = [
    huaweicloud_obs_bucket_object.test,
    huaweicloud_obs_bucket_policy.test
  ]

  start_task                     = var.task_is_start
  type                           = var.task_type
  enable_kms                     = var.task_enable_kms
  migrate_since                  = var.task_migrate_since
  object_overwrite_mode          = var.task_object_overwrite_mode
  consistency_check              = var.task_consistency_check
  enable_requester_pays          = var.task_enable_requester_pays
  enable_failed_object_recording = var.task_enable_failed_object_recording

  source_object {
    data_source = "HuaweiCloud"
    region      = huaweicloud_obs_bucket.test.region
    bucket      = huaweicloud_obs_bucket.test.id
    access_key  = var.access_key
    secret_key  = var.secret_key
    object      = [var.object_name]
  }

  destination_object {
    region     = var.target_bucket_configuration.region != "" ? var.target_bucket_configuration.region : huaweicloud_obs_bucket.test.region
    bucket     = var.target_bucket_configuration.bucket
    access_key = var.target_bucket_configuration.access_key != "" ? var.target_bucket_configuration.access_key : var.access_key
    secret_key = var.target_bucket_configuration.secret_key != "" ? var.target_bucket_configuration.secret_key : var.secret_key
  }

  dynamic "bandwidth_policy" {
    for_each = var.bandwidth_policy_configurations

    content {
      max_bandwidth = bandwidth_policy.value["max_bandwidth"]
      start         = bandwidth_policy.value["start"]
      end           = bandwidth_policy.value["end"]
    }
  }
}
```

**Parameter Description**:

- **start\_task**: Whether to start task, assigned by referencing the input variable task\_is\_start
- **type**: Task type, assigned by referencing the input variable task\_type
- **enable\_kms**: Whether KMS is enabled, assigned by referencing the input variable task\_enable\_kms
- **migrate\_since**: Migration start time, assigned by referencing the input variable task\_migrate\_since
- **object\_overwrite\_mode**: Object overwrite mode, assigned by referencing the input variable task\_object\_overwrite\_mode
- **consistency\_check**: Consistency check, assigned by referencing the input variable task\_consistency\_check
- **enable\_requester\_pays**: Whether requester pays is enabled, assigned by referencing the input variable task\_enable\_requester\_pays
- **enable\_failed\_object\_recording**: Whether failed object recording is enabled, assigned by referencing the input variable task\_enable\_failed\_object\_recording
- **source\_object**: Source object configuration, includes data source, region, bucket, access key, and object list
- **destination\_object**: Destination object configuration, includes region, bucket, and access key
- **bandwidth\_policy**: Bandwidth policy, dynamically creates bandwidth control configuration

### 7. Preset Input Parameters Required for Resource Deployment (Optional)

In this practice, some resources and data sources use input variables to assign values to configuration content. These input parameters need to be manually entered during subsequent deployments. At the same time, Terraform provides a method to preset these configurations through `tfvars` files, which can avoid repeated input during each execution.

Create a `terraform.tfvars` file in the working directory with the following example content:

```hcl
# Authentication information
region_name = "cn-north-4"
access_key  = "your-access-key"
secret_key  = "your-secret-key"

# KMS key configuration
key_alias   = "tf-test-obs-key"
key_usage   = "ENCRYPT_DECRYPT"

# OBS bucket configuration
bucket_name        = "tf-test-obs-bucket"
bucket_storage_class = "STANDARD"
bucket_acl         = "private"
bucket_encryption  = true
bucket_sse_algorithm = "kms"
bucket_force_destroy = true
bucket_tags        = {
  environment = "test"
  created_by  = "terraform"
}

# OBS object configuration
object_extension_name = ".txt"
object_name           = "tf-test-obs-object"
object_upload_content = <<EOT
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
EOT

# Migration task configuration
task_is_start = true
task_type = "prefix"
task_enable_kms = true
task_migrate_since = null
task_object_overwrite_mode = "CRC64_COMPARISON_OVERWRITE"
task_consistency_check = "crc64"
task_enable_requester_pays = true
task_enable_failed_object_recording = true

# Target bucket configuration
target_bucket_configuration = {
  bucket = "tf-test-obs-bucket-target"
}

# Bandwidth policy configuration
bandwidth_policy_configurations = [
  {
    max_bandwidth = 1
    start         = "03:00"
    end           = "04:00"
  }
]
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="bucket_name=my-bucket" -var="object_name=my-object"`
2. Environment variables: `export TF_VAR_bucket_name=my-bucket`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 8. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating migration tasks
4. Run `terraform show` to view the created migration tasks

## Reference Information

- [Huawei Cloud OMS Product Documentation](https://support.huaweicloud.com/oms/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For OMS Object Migration Through Task](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/oms/migrate-objects-by-task)
