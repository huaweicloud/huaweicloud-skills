resource "huaweicloud_swr_organization" "this" {
  name = var.organization_name
}

resource "huaweicloud_swr_repository" "this" {
  organization = huaweicloud_swr_organization.this.name
  name         = var.repository_name
  category     = var.repository_category
}
