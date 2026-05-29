terraform {
  required_version = ">= 1.9.0"

  required_providers {
    huaweicloud = {
      source  = "huaweicloud/huaweicloud"
      version = ">= 1.50.0"
    }
  }
}

# Share (owner).
provider "huaweicloud" {
  alias = "owner"

  region     = var.region_name
  access_key = var.access_key
  secret_key = var.secret_key
}

# Other account (principal).
provider "huaweicloud" {
  alias = "principal"

  region     = var.region_name
  access_key = var.principal_access_key
  secret_key = var.principal_secret_key
}
