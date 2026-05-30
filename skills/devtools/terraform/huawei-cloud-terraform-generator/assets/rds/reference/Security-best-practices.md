# Security Best Practices

Apply security hardening when generating code:

- Enable static encryption by default
- Configure private networks where applicable
- Apply the principle of least privilege to security groups
- Enable logging and monitoring
- Never hardcode credentials or keys
- Mark sensitive outputs with `sensitive = true`

## Example: Secure OBS Bucket

```hcl
# Create OBS bucket
resource "huaweicloud_obs_bucket" "data" {
  bucket = "my-tf-test-bucket"
  acl    = "private"

  tags = {
    Environment = "Test"
    ManagedBy   = "Terraform"
  }
}

# Enable versioning
resource "huaweicloud_obs_bucket" "versioning" {
  bucket     = "my-tf-versioning-bucket"
  acl        = "private"
  versioning = true

  tags = {
    Environment = "Test"
    ManagedBy   = "Terraform"
  }
}

# Enable server-side encryption
resource "huaweicloud_obs_bucket" "encryption" {
  bucket        = "my-tf-encryption-bucket"
  storage_class = "STANDARD"
  acl           = "private"
  encryption    = true

  tags = {
    Environment = "Test"
    ManagedBy   = "Terraform"
  }
}

# Configure lifecycle rules
resource "huaweicloud_obs_bucket" "lifecycle" {
  bucket     = "my-tf-lifecycle-bucket"
  acl        = "private"
  versioning = true

  lifecycle_rule {
    name    = "log"
    prefix  = "log/"
    enabled = true

    expiration {
      days = 365
    }
    transition {
      days          = 60
      storage_class = "WARM"
    }
    transition {
      days          = 180
      storage_class = "COLD"
    }
    abort_incomplete_multipart_upload {
      days = 360
    }
  }

  lifecycle_rule {
    name    = "tmp"
    enabled = true

    noncurrent_version_expiration {
      days = 180
    }
    noncurrent_version_transition {
      days          = 30
      storage_class = "WARM"
    }
    noncurrent_version_transition {
      days          = 60
      storage_class = "COLD"
    }
  }

  tags = {
    Environment = "Test"
    ManagedBy   = "Terraform"
  }
}

# Configure bucket access policy
variable "bucket_name" {
  description = "OBS bucket name"
  type        = string
}

variable "account1_id" {
  description = "Account 1 ID"
  type        = string
}

variable "account2_id" {
  description = "Account 2 ID"
  type        = string
}

resource "huaweicloud_obs_bucket" "acl_test" {
  bucket = var.bucket_name
  acl    = "private"
}

resource "huaweicloud_obs_bucket_acl" "test" {
  bucket = huaweicloud_obs_bucket.acl_test.id

  owner_permission {
    access_to_bucket = ["READ", "WRITE"]
    access_to_acl    = ["READ_ACP", "WRITE_ACP"]
  }

  account_permission {
    access_to_bucket = ["READ", "WRITE"]
    access_to_acl    = ["READ_ACP", "WRITE_ACP"]
    account_id       = var.account1_id
  }

  account_permission {
    access_to_bucket = ["READ"]
    access_to_acl    = ["READ_ACP", "WRITE_ACP"]
    account_id       = var.account2_id
  }

  public_permission {
    access_to_bucket = ["READ", "WRITE"]
  }

  log_delivery_user_permission {
    access_to_bucket = ["READ", "WRITE"]
    access_to_acl    = ["READ_ACP", "WRITE_ACP"]
  }
}
```
