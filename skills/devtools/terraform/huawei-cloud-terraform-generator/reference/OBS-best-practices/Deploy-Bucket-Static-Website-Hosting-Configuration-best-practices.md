# Deploy Bucket Static Website Hosting Configuration

## Application Scenario

Object Storage Service (OBS) is a highly available, highly reliable, high-performance, secure, and low-cost object storage service provided by Huawei Cloud. OBS provides massive, secure, highly reliable, and low-cost data storage capabilities, supporting multiple storage types, including standard storage, infrequent access storage, archive storage, etc., meeting storage requirements for different business scenarios.

OBS bucket static website hosting is an important feature of the OBS service, used to configure OBS buckets as static website hosting services. Through static website hosting, enterprises can store static website files (HTML, CSS, JavaScript, images, etc.) in OBS buckets and access them directly through OBS-provided website endpoints. Static website hosting supports custom home pages and error pages, provides complete website access control policies, providing enterprises with simple, economical, and reliable static website hosting solutions. This best practice will introduce how to use Terraform to automatically deploy OBS bucket static website hosting configuration, including KMS key creation, OBS bucket configuration, website configuration, and access policy settings.

## Related Resources/Data Sources

This best practice involves the following main resources and data sources:

### Resources

- [KMS Key Resource (huaweicloud\_kms\_key)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/kms_key)
- [OBS Bucket Resource (huaweicloud\_obs\_bucket)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket)
- [OBS Bucket Policy Resource (huaweicloud\_obs\_bucket\_policy)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket_policy)
- [OBS Bucket Object Resource (huaweicloud\_obs\_bucket\_object)](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket_object)

### Resource/Data Source Dependencies

```
huaweicloud_kms_key.test
    └── huaweicloud_obs_bucket.test
        ├── huaweicloud_obs_bucket_policy.test
        └── huaweicloud_obs_bucket_object.test
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

### 3. Define Local Variables

Add the following script to the TF file (e.g., main.tf) to define local variables for handling website configuration:

```hcl
variable "website_configurations" {
  description = "OBS bucket website configuration"
  type        = map(object({
    file_name = string
    content   = string
  }))

  validation {
    condition     = contains(keys(var.website_configurations), "index") && contains(keys(var.website_configurations), "error")
    error_message = "website_configurations map must contain 'index' and 'error' keys."
  }
}

# Define local variables for handling website configuration
locals {
  website_page_names = [for k, v in var.website_configurations : v.file_name if k == "index" || k == "error"]
  index_page         = lookup(var.website_configurations, "index")
  error_page         = lookup(var.website_configurations, "error")
}
```

**Parameter Description**:

- **website\_configurations**: Website configuration map, must contain index and error page configurations
- **website\_page\_names**: Extract file names for home page and error page
- **index\_page**: Home page configuration
- **error\_page**: Error page configuration

### 4. Create OBS Bucket

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
  tags          = merge(var.bucket_tags, {for k, v in var.website_configurations : k => v.file_name if k == "index" || k == "error"})

  provisioner "local-exec" {
    command = "echo '${lookup(local.index_page, "content")}' >> ${lookup(local.index_page, "file_name")}\necho '${lookup(local.error_page, "content")}' >> ${lookup(local.error_page, "file_name")}"
  }
  provisioner "local-exec" {
    command = "rm ${self.tags.index} ${self.tags.error}"
    when    = destroy
  }

  website {
    index_document = lookup(local.index_page, "file_name")
    error_document = lookup(local.error_page, "file_name")
  }

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
- **tags**: Tags, merge bucket tags and website page file name tags
- **website**: Website configuration, set home page and error page documents
- **provisioner**: Local executor, used to create and delete website page files

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
      "Sid": "AddPerm",
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
- **policy**: Bucket policy, allows all users to perform GetObject operations on bucket objects

### 6. Create OBS Bucket Object

Add the following script to the TF file (e.g., main.tf) to instruct Terraform to create an OBS bucket object resource:

```hcl
# Create an OBS bucket object resource under the specified region (if the region parameter is omitted, it defaults to the region specified in the current provider block)
resource "huaweicloud_obs_bucket_object" "test" {
  count = length(local.website_page_names)

  bucket = huaweicloud_obs_bucket.test.id
  key    = try(local.website_page_names[count.index], null)
  source = abspath(format("./%s", try(local.website_page_names[count.index], null)))
}
```

**Parameter Description**:

- **bucket**: Bucket ID, assigned by referencing the OBS bucket resource (huaweicloud\_obs\_bucket.test) ID
- **key**: Object key name, using website page file name
- **source**: Source file path, using locally created website page file

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

# Website configuration
website_configurations = {
  index = {
    file_name = "index.html"
    content   = <<EOT
<html>
  <head>
    <title>Hello OBS!</title>
    <meta charset="utf-8">
  </head>
  <body>
    <p>Welcome to use OBS static website hosting.</p>
    <p>This is the homepage.</p>
  </body>
</html>
EOT
  }
  error = {
    file_name = "error.html"
    content   = <<EOT
<html>
  <head>
    <title>Hello OBS!</title>
    <meta charset="utf-8">
  </head>
  <body>
    <p>Welcome to use OBS static website hosting.</p>
    <p> This is the 404 error page.</p>
  </body>
</html>
EOT
  }
}
```

**Usage**:

1. Save the above content as `terraform.tfvars` file in the working directory (this file name allows users to automatically import the content of this `tfvars` file when executing terraform commands; for other names, `.auto` needs to be added before tfvars, such as `variables.auto.tfvars`)
2. Modify parameter values as needed
3. When executing `terraform plan` or `terraform apply`, Terraform will automatically read the variable values from this file

In addition to using `terraform.tfvars` file, variable values can also be set in the following ways:

1. Command line parameters: `terraform apply -var="bucket_name=my-bucket" -var="key_alias=my-key"`
2. Environment variables: `export TF_VAR_bucket_name=my-bucket`
3. Custom named variable files: `terraform apply -var-file="custom.tfvars"`

> Note: If the same variable is set in multiple ways, Terraform will use the variable value according to the following priority: command line parameters > variable files > environment variables > default values.

### 8. Initialize and Apply Terraform Configuration

After completing the above script configuration, execute the following steps to create resources:

1. Run `terraform init` to initialize the environment
2. Run `terraform plan` to view the resource creation plan
3. After confirming the resource plan is correct, run `terraform apply` to start creating static website hosting configuration
4. Run `terraform show` to view the created static website hosting configuration

## Reference Information

- [Huawei Cloud OBS Product Documentation](https://support.huaweicloud.com/obs/index.html)
- [Huawei Cloud Provider Documentation](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Best Practice Source Code Reference For OBS Bucket Static Website Hosting Configuration](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/master/examples/obs/bucket-with-website)
