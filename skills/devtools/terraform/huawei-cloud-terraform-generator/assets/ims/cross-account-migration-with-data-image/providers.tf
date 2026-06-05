terraform {
  required_version = ">= 1.9.0"

  required_providers {
    huaweicloud = {
      source  = "huaweicloud/huaweicloud"
      version = ">= 1.50.0"
    }
  }
}

# Provider for sharer
provider "huaweicloud" {
  alias      = "sharer"
  region     = var.region_name
  access_key = var.access_key
  secret_key = var.secret_key
}

# Provider for accepter
provider "huaweicloud" {
  alias      = "accepter"
  region     = var.region_name
  access_key = var.accepter_access_key
  secret_key = var.accepter_secret_key
}
