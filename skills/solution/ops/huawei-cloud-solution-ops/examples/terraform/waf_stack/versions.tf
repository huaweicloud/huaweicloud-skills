terraform {
  required_version = ">= 1.6.0"

  required_providers {
    huaweicloud = {
      source  = "huaweicloud/huaweicloud"
      version = ">= 1.36.0, < 2.0.0"
    }
  }
}
