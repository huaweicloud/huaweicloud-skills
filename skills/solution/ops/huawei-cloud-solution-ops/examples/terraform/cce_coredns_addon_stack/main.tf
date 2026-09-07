data "huaweicloud_cce_clusters" "selected" {
  count = var.cluster_id == "" ? 1 : 0

  name = var.cluster_name
}

locals {
  selected_cluster_id = var.cluster_id != "" ? var.cluster_id : try(data.huaweicloud_cce_clusters.selected[0].clusters[0].id, null)
}

data "huaweicloud_cce_addon_template" "coredns" {
  cluster_id = local.selected_cluster_id
  name       = "coredns"
  version    = var.addon_version
}

resource "huaweicloud_cce_addon" "coredns" {
  cluster_id    = local.selected_cluster_id
  template_name = "coredns"
  version       = var.addon_version

  values {
    basic_json  = jsonencode(jsondecode(data.huaweicloud_cce_addon_template.coredns.spec).basic)
    custom_json = jsonencode(merge(jsondecode(data.huaweicloud_cce_addon_template.coredns.spec).parameters.custom, var.custom_overrides))
    flavor_json = jsonencode(jsondecode(data.huaweicloud_cce_addon_template.coredns.spec).parameters.flavor1)
  }

  lifecycle {
    precondition {
      condition     = local.selected_cluster_id != null
      error_message = "No CCE cluster was selected. Set cluster_id or a cluster_name that resolves to one cluster."
    }
  }
}
