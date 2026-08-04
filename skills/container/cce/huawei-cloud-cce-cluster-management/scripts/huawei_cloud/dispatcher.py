"""CLI dispatch for CCE cluster management skill.

Data-driven architecture: 14 simple tools defined as a mapping table,
12 special tools routed to special_ops functions. No per-tool Python wrappers.
"""

import json
import os
from typing import Any, Dict, Optional

from .hcloud_runner import resolve_credentials, run
from . import special_ops


# ============================================================
# Simple tools: data-driven, no Python function per tool
# Format: tool_name -> (service, operation, required_params, confirm_required)
# ============================================================

SIMPLE_TOOLS = {
    # VPC
    "huawei_list_vpc":         ("VPC", "ListVpcs",   ("region",), False),
    "huawei_list_vpc_subnets": ("VPC", "ListSubnets", ("region",), False),

    # EIP
    "huawei_list_eips":        ("EIP", "ListPublicips",  ("region",), False),
    "huawei_delete_eip":       ("EIP", "DeletePublicip", ("region", "publicip_id"), True),

    # Cluster (query + lifecycle, excluding create/bind which need special logic)
    "huawei_list_cce_clusters":      ("CCE", "ListClusters",                ("region",), False),
    "huawei_delete_cce_cluster":     ("CCE", "DeleteCluster",              ("region", "cluster_id"), True),
    "huawei_hibernate_cce_cluster":  ("CCE", "HibernateCluster",           ("region", "cluster_id"), True),
    "huawei_awake_cce_cluster":      ("CCE", "AwakeCluster",               ("region", "cluster_id"), False),

    # Node (query + delete, excluding create + kubectl ops)
    "huawei_list_cce_nodes":    ("CCE", "ListNodes",   ("region", "cluster_id"), False),
    "huawei_delete_cce_node":   ("CCE", "DeleteNode",  ("region", "cluster_id", "node_id"), True),
    "huawei_get_cce_nodes":     ("CCE", "ListNodes",   ("region", "cluster_id"), False),

    # Nodepool (list only, excluding create/resize/delete which need name->UID)
    "huawei_list_cce_nodepools": ("CCE", "ListNodePools", ("region", "cluster_id"), False),

    # Addon (query + delete, excluding install/update which need special logic)
    "huawei_list_cce_addons":       ("CCE", "ListAddonInstances",  ("region", "cluster_id"), False),
    "huawei_get_cce_addon_detail":  ("CCE", "ShowAddonInstance",   ("region", "cluster_id", "addon_id"), False),
    "huawei_uninstall_cce_addon":   ("CCE", "DeleteAddonInstance", ("region", "cluster_id", "addon_id"), True),
}


# ============================================================
# Special tools: routed to special_ops functions
# Format: tool_name -> (handler, required_params)
# ============================================================

SPECIAL_TOOLS = {
    # Cluster: create (hybrid SDK), bind/unbind EIP, kubeconfig
    "huawei_create_cce_cluster":    (special_ops.create_cce_cluster,    ("region", "cluster_name", "vpc_id", "subnet_id")),
    "huawei_bind_cce_cluster_eip":  (special_ops.bind_cce_cluster_eip,  ("region", "cluster_id")),
    "huawei_unbind_cce_cluster_eip": (special_ops.unbind_cce_cluster_eip, ("region", "cluster_id")),
    "huawei_get_cce_kubeconfig":     (special_ops.get_cce_kubeconfig,    ("region", "cluster_id")),

    # Node: create (resolve_node_login), kubectl ops
    "huawei_create_cce_node":       (special_ops.create_cce_node,       ("region", "cluster_id", "flavor", "availability_zone", "root_volume_size", "root_volume_type")),
    "huawei_cce_node_cordon":       (special_ops.cce_node_cordon,       ("region", "cluster_id", "node_name")),
    "huawei_cce_node_uncordon":     (special_ops.cce_node_uncordon,     ("region", "cluster_id", "node_name")),
    "huawei_cce_node_drain":        (special_ops.cce_node_drain,        ("region", "cluster_id", "node_name")),
    "huawei_cce_node_status":       (special_ops.cce_node_status,       ("region", "cluster_id", "node_name")),

    # Nodepool: create (SDK), resize/delete (name->UID)
    "huawei_create_cce_nodepool":   (special_ops.create_node_pool,      ("region", "cluster_id", "nodepool_name", "flavor", "availability_zone", "root_volume_size", "root_volume_type")),
    "huawei_resize_cce_nodepool":   (special_ops.resize_node_pool,      ("region", "cluster_id", "nodepool_id", "node_count")),
    "huawei_delete_cce_nodepool":   (special_ops.delete_node_pool,      ("region", "cluster_id", "nodepool_id")),

    # Addon: install/update (hcloud --param=value)
    "huawei_install_cce_addon":     (special_ops.install_cce_addon,     ("region", "cluster_id", "addon_template_name")),
    "huawei_update_cce_addon":      (special_ops.update_cce_addon,      ("region", "cluster_id", "addon_id", "addon_template_name")),
}


# Params that are internal (not passed to hcloud)
_INTERNAL_PARAMS = {"region", "ak", "sk", "confirm", "_action"}

# User-facing param names that need renaming for hcloud
_PARAM_RENAME = {"addon_id": "id"}


def _check_required(params: Dict[str, str], required: tuple) -> Optional[str]:
    """Return error message if required params are missing, else None."""
    missing = [k for k in required if not params.get(k)]
    if missing:
        return f"{', '.join(missing)} are required" if len(missing) > 1 else f"{missing[0]} is required"
    return None


def _handle_simple(params: Dict[str, str], service: str, operation: str,
                   required: tuple, confirm_required: bool) -> Dict[str, Any]:
    """Generic handler for simple hcloud tools."""
    region = params.get("region") or os.environ.get("HW_REGION_NAME")
    if not region:
        return {"success": False, "error": "region is required"}

    ctx = resolve_credentials(params.get("ak"), params.get("sk"), params.get("project_id"), region)
    if not ctx.ak or not ctx.sk:
        return {"success": False, "error": "Credentials not provided. Set HW_ACCESS_KEY and HW_SECRET_KEY."}

    if confirm_required and params.get("confirm", "").lower() != "true":
        return {
            "success": False,
            "requires_confirmation": True,
            "error": "Confirmation required. Add confirm=true to proceed.",
            "hint": f"Add confirm=true parameter to confirm this operation.",
        }

    # Build hcloud params (exclude internal params, rename mapped params)
    hcloud_params = {}
    for k, v in params.items():
        if k in _INTERNAL_PARAMS or v is None:
            continue
        hcloud_name = _PARAM_RENAME.get(k, k)
        hcloud_params[hcloud_name] = v
    # Always include project_id from resolved credentials (needed for path-based APIs)
    if ctx.project_id:
        hcloud_params.setdefault("project_id", ctx.project_id)

    result = run(ctx, region, service, operation, hcloud_params)
    if result.get("success"):
        result["action"] = params.get("_action", "")
        result["region"] = region
    return result


def is_registered_action(action: str) -> bool:
    """Check if an action name is registered."""
    return action in SIMPLE_TOOLS or action in SPECIAL_TOOLS


def dispatch_action(action: str, params: Dict[str, str]) -> Dict[str, Any]:
    """Dispatch an action to the appropriate handler."""
    params = dict(params)  # copy to avoid mutation
    params["_action"] = action

    if action in SIMPLE_TOOLS:
        service, operation, required, confirm_required = SIMPLE_TOOLS[action]
        error = _check_required(params, required)
        if error:
            return {"success": False, "error": error}
        return _handle_simple(params, service, operation, required, confirm_required)

    if action in SPECIAL_TOOLS:
        handler, required = SPECIAL_TOOLS[action]
        error = _check_required(params, required)
        if error:
            return {"success": False, "error": error}
        return handler(params)

    return {"success": False, "error": f"Unknown action: {action}"}
