"""Special-case tool functions for CCE cluster management.

These functions have real logic beyond a simple hcloud call:
- Multi-call chains (bind EIP, name->UID resolution)
- Password salting + resolve_node_login
- kubectl subprocess (node scheduling)
- SDK fallback (create cluster/nodepool — hcloud metadata defect)
"""

import json
import os
import subprocess
import tempfile
from typing import Any, Dict, Optional

from .hcloud_runner import resolve_credentials, run, run_with_body, kubectl_cce
from .common import resolve_node_login, create_cce_client


# ============================================================
# Cluster: create (hybrid hcloud+SDK), bind EIP (2-call)
# ============================================================

def create_cce_cluster(params: Dict[str, str]) -> Dict[str, Any]:
    """Create CCE cluster. Hybrid: hcloud VPC lookup + SDK creation (hcloud defect)."""
    region = params["region"]
    cluster_name = params["cluster_name"]
    vpc_id = params["vpc_id"]
    subnet_id = params["subnet_id"]
    cluster_version = params.get("cluster_version")  # None = API latest
    cluster_type = params.get("cluster_type", "VirtualMachine")
    container_network_type = params.get("container_network_type", "eni")  # Turbo default
    container_network_cidr = params.get("container_network_cidr")
    service_network_cidr = params.get("service_network_cidr")
    flavor_id = params.get("flavor_id")
    description = params.get("description")
    eni_subnet_id = params.get("eni_subnet_id")

    ctx = resolve_credentials(params.get("ak"), params.get("sk"), params.get("project_id"), region)
    if not ctx.ak or not ctx.sk:
        return {"success": False, "error": "Credentials not provided."}

    # Turbo (eni) default: resolve neutron_subnet_id via hcloud VPC
    neutron_id = None
    if container_network_type == "eni":
        subnet_to_query = eni_subnet_id or subnet_id
        vpc_result = run(ctx, region, "VPC", "ShowSubnet", {"subnet_id": subnet_to_query})
        if vpc_result["success"]:
            neutron_id = vpc_result["data"].get("subnet", {}).get("neutron_subnet_id")
        if not neutron_id:
            return {"success": False, "error": f"Failed to resolve neutron_subnet_id for subnet {subnet_to_query}"}

    # SDK fallback for cluster creation (hcloud defect)
    try:
        from huaweicloudsdkcce.v3 import (
            CreateClusterRequest, Cluster, ClusterMetadata, ClusterSpec,
            ContainerNetwork, HostNetwork, EniNetwork, NetworkSubnet, ServiceNetwork,
        )

        client = create_cce_client(region, ctx.ak, ctx.sk, ctx.project_id, ctx.security_token)

        metadata = ClusterMetadata(name=cluster_name)
        if description:
            metadata.annotations = {"description": description}

        host_network = HostNetwork(vpc=vpc_id, subnet=subnet_id)
        container_network = ContainerNetwork(mode=container_network_type)
        if container_network_cidr:
            container_network.cidr = container_network_cidr

        cluster_spec = ClusterSpec(
            type=cluster_type,
            host_network=host_network,
            container_network=container_network,
        )
        if cluster_version:
            cluster_spec.version = cluster_version
        if flavor_id:
            cluster_spec.flavor = flavor_id
        if neutron_id:
            cluster_spec.eni_network = EniNetwork(subnets=[NetworkSubnet(subnet_id=neutron_id)])
        if service_network_cidr:
            cluster_spec.service_network = ServiceNetwork(i_pv4_cidr=service_network_cidr)

        body = Cluster(kind="Cluster", api_version="v3", metadata=metadata, spec=cluster_spec)
        request = CreateClusterRequest(body=body)
        response = client.create_cluster(request)

        cluster_id = getattr(response.metadata, 'uid', None) if hasattr(response, 'metadata') else None
        return {
            "success": True, "region": region, "action": "create_cce_cluster",
            "cluster_id": cluster_id, "cluster_name": cluster_name,
            "container_network_type": container_network_type,
            "message": "Cluster creation submitted successfully",
        }
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


def bind_cce_cluster_eip(params: Dict[str, str]) -> Dict[str, Any]:
    """Bind EIP to cluster. Dynamic: auto-find or create EIP if eip_id not provided.

    Flow:
      1. If eip_id provided → use it directly
      2. If not → ListPublicips, find unbound (status=DOWN only) → use first
      3. If none unbound → CreatePublicip (traffic billing, 5Mbps) → use new
      4. UpdateClusterEip (bind)
      5. If bind fails (VPC.0510 FloatingipInUse) and EIP was reused → create new EIP and retry
      6. ShowCluster → extract External endpoint URL
    """
    region = params["region"]
    cluster_id = params["cluster_id"]
    eip_id = params.get("eip_id")
    eip_name = params.get("eip_name", "cce-skill-auto-eip")
    bandwidth_size = params.get("bandwidth_size", "5")
    charge_mode = params.get("charge_mode", "traffic")
    eip_type = params.get("eip_type", "5_bgp")

    ctx = resolve_credentials(params.get("ak"), params.get("sk"), params.get("project_id"), region)
    if not ctx.ak or not ctx.sk:
        return {"success": False, "error": "Credentials not provided."}

    eip_created = False
    eip_address = None

    # Step 1: Resolve EIP if not provided
    if not eip_id:
        # Try to find an unbound EIP (status=DOWN only; port_id=None with status=ACTIVE
        # may still be occupied — see issue #186)
        list_result = run(ctx, region, "EIP", "ListPublicips", {})
        if list_result.get("success"):
            publicips = list_result.get("data", {}).get("publicips", [])
            # NOTE: iterates over already-fetched EIP list (single ListPublicips call above); not N+1
            for eip in publicips:
                if eip.get("status") == "DOWN":
                    eip_id = eip.get("id")
                    eip_address = eip.get("public_ip_address")
                    break

        if not eip_id:
            # No unbound EIP found — create a new one via hcloud --param=value
            create_result = run(ctx, region, "EIP", "CreatePublicip", {
                "publicip.type": eip_type,
                "publicip.ip_version": "4",
                "bandwidth.name": eip_name,
                "bandwidth.size": str(bandwidth_size),
                "bandwidth.share_type": "PER",
                "bandwidth.charge_mode": charge_mode,
            })
            if not create_result.get("success"):
                return create_result
            created = create_result.get("data", {})
            eip_id = created.get("publicip", {}).get("id") or created.get("id")
            eip_address = created.get("publicip", {}).get("public_ip_address") or created.get("public_ip_address")
            eip_created = True

    # Step 2: Bind EIP to cluster
    result = run(ctx, region, "CCE", "UpdateClusterEip", {
        "cluster_id": cluster_id, "spec.action": "bind", "spec.spec.id": eip_id,
    })
    if not result["success"]:
        # If binding failed with FloatingipInUse and we reused an existing EIP,
        # fall back to creating a new EIP and retry (issue #186)
        if not eip_created:
            create_result = run(ctx, region, "EIP", "CreatePublicip", {
                "publicip.type": eip_type,
                "publicip.ip_version": "4",
                "bandwidth.name": eip_name,
                "bandwidth.size": str(bandwidth_size),
                "bandwidth.share_type": "PER",
                "bandwidth.charge_mode": charge_mode,
            })
            if create_result.get("success"):
                created = create_result.get("data", {})
                new_eip_id = created.get("publicip", {}).get("id") or created.get("id")
                new_eip_address = created.get("publicip", {}).get("public_ip_address") or created.get("public_ip_address")
                retry_result = run(ctx, region, "CCE", "UpdateClusterEip", {
                    "cluster_id": cluster_id, "spec.action": "bind", "spec.spec.id": new_eip_id,
                })
                if retry_result["success"]:
                    eip_id = new_eip_id
                    eip_address = new_eip_address
                    eip_created = True
                    result = retry_result
                else:
                    # Clean up the newly created EIP
                    run(ctx, region, "EIP", "DeletePublicip", {"publicip_id": new_eip_id})
                    return retry_result
            else:
                return create_result
        else:
            # Clean up newly created EIP if binding failed
            run(ctx, region, "EIP", "DeletePublicip", {"publicip_id": eip_id})
            return result

    # Step 3: Query cluster for public endpoint
    show = run(ctx, region, "CCE", "ShowCluster", {"cluster_id": cluster_id})
    public_url = None
    if show["success"]:
        # NOTE: iterates over already-fetched cluster endpoints (single ShowCluster call above); not N+1
        for ep in show["data"].get("status", {}).get("endpoints", []):
            if ep.get("type") == "External":
                public_url = ep.get("url")
                break

    out = {
        "success": True, "region": region, "cluster_id": cluster_id,
        "action": "bind_cce_cluster_eip", "eip_id": eip_id,
        "eip_created": eip_created,
        "message": "EIP bound successfully" + (" (newly created)" if eip_created else " (existing)"),
    }
    if eip_address:
        out["eip_address"] = eip_address
    if public_url:
        out["public_endpoint"] = public_url
    return out


def unbind_cce_cluster_eip(params: Dict[str, str]) -> Dict[str, Any]:
    """Unbind EIP from cluster via UpdateClusterEip with spec.action=unbind."""
    region = params["region"]
    cluster_id = params["cluster_id"]

    ctx = resolve_credentials(params.get("ak"), params.get("sk"), params.get("project_id"), region)
    if not ctx.ak or not ctx.sk:
        return {"success": False, "error": "Credentials not provided."}

    # Use run_with_body to include spec.spec empty object (required by API to avoid 500)
    body = {
        "spec": {
            "action": "unbind",
            "spec": {}
        }
    }
    result = run_with_body(ctx, region, "CCE", "UpdateClusterEip", body,
                           path_params={"cluster_id": cluster_id})
    if result.get("success"):
        result["action"] = "unbind_cce_cluster_eip"
        result["region"] = region
        result["cluster_id"] = cluster_id
        result["message"] = "EIP unbound successfully"
    return result


def get_cce_kubeconfig(params: Dict[str, str]) -> Dict[str, Any]:
    """Get cluster kubeconfig via CreateKubernetesClusterCert.

    The API requires duration (integer days, 1-1827) or expire_at.
    Defaults to 30 days if not provided.
    """
    region = params["region"]
    cluster_id = params["cluster_id"]
    duration = params.get("duration", "30")

    ctx = resolve_credentials(params.get("ak"), params.get("sk"), params.get("project_id"), region)
    if not ctx.ak or not ctx.sk:
        return {"success": False, "error": "Credentials not provided."}

    result = run(ctx, region, "CCE", "CreateKubernetesClusterCert", {
        "cluster_id": cluster_id, "duration": str(duration),
    })
    if result.get("success"):
        result["action"] = "get_cce_kubeconfig"
        result["region"] = region
        result["cluster_id"] = cluster_id
    return result


# ============================================================
# Node: create (hcloud + resolve_node_login), kubectl ops
# ============================================================

def create_cce_node(params: Dict[str, str]) -> Dict[str, Any]:
    """Create node via hcloud --param=value."""
    region = params["region"]
    cluster_id = params["cluster_id"]
    flavor = params["flavor"]
    availability_zone = params["availability_zone"]
    root_volume_size = int(params.get("root_volume_size", 40))
    root_volume_type = params.get("root_volume_type", "SSD")
    node_count = int(params.get("node_count", 1))
    os_type = params.get("os_type", "Huawei Cloud EulerOS 2.0")
    ssh_key = params.get("ssh_key")
    password = params.get("password")
    data_volumes = json.loads(params["data_volumes"]) if params.get("data_volumes") else None
    subnet_id = params.get("subnet_id")

    ctx = resolve_credentials(params.get("ak"), params.get("sk"), params.get("project_id"), region)
    if not ctx.ak or not ctx.sk:
        return {"success": False, "error": "Credentials not provided."}

    login_config, was_auto = resolve_node_login(ssh_key, password)

    hcloud_params = {
        "cluster_id": cluster_id,
        "apiVersion": "v3",
        "kind": "Node",
        "metadata.name": f"node-{cluster_id[:8]}",
        "spec.flavor": flavor,
        "spec.az": availability_zone,
        "spec.os": os_type,
        "spec.count": str(node_count),
        "spec.rootVolume.size": str(root_volume_size),
        "spec.rootVolume.volumetype": root_volume_type,
    }
    if "sshKey" in login_config:
        hcloud_params["spec.login.sshKey"] = login_config["sshKey"]
    elif "userPassword" in login_config:
        hcloud_params["spec.login.userPassword.username"] = login_config["userPassword"]["username"]
        hcloud_params["spec.login.userPassword.password"] = login_config["userPassword"]["password"]
    if data_volumes:
        # NOTE: iterates over local data_volumes list to build hcloud params; no API call in loop
        for i, dv in enumerate(data_volumes):
            hcloud_params[f"spec.dataVolumes.{i+1}.size"] = str(dv.get("size", 100))
            hcloud_params[f"spec.dataVolumes.{i+1}.volumetype"] = dv.get("type", "SSD")
    if subnet_id:
        hcloud_params["spec.nodeNicSpec.primaryNic.subnetId"] = subnet_id

    result = run(ctx, region, "CCE", "CreateNode", hcloud_params)
    if not result["success"]:
        return result

    msg = f"Node creation submitted for {node_count} node(s)"
    if was_auto:
        msg += ". Node login password was auto-generated. To access the node, reset the password via CCE console or ECS API."
    return {
        "success": True, "region": region, "cluster_id": cluster_id,
        "action": "create_cce_node", "node_count": node_count, "message": msg,
    }


def _node_operation(params: Dict[str, str], operation: str) -> Dict[str, Any]:
    """Node scheduling operations via kubectl cce plugin (no EIP needed).

    Uses kubectl-cce to connect through the CCE API Gateway with AK/SK credentials.
    Requires kubectl + kubectl-cce plugin (install via huawei-cloud-kubectl-cce-installer skill).
    """
    region = params["region"]
    cluster_id = params["cluster_id"]
    node_name = params["node_name"]
    confirm = params.get("confirm", "").lower() == "true"

    # kubectl-cce node operations don't need project_id — skip fetching to avoid
    # unnecessary credential exposure (R5: _fetch_project_id would expose AK/SK in ps aux)
    ctx = resolve_credentials(params.get("ak"), params.get("sk"), params.get("project_id"), region,
                              fetch_project_id=False)
    if not ctx.ak or not ctx.sk:
        return {"success": False, "error": "Credentials not provided."}

    # cordon/uncordon/drain: check confirm BEFORE making API calls
    if operation in ("cordon", "uncordon", "drain") and not confirm:
        affected_pods = []
        if operation == "drain":
            # Preview pods that would be evicted
            pods_resp = kubectl_cce(ctx, region, cluster_id, [
                "get", "pods", "--field-selector", f"spec.nodeName={node_name}",
                "-o", "json",
            ])
            if pods_resp.get("success") and "data" in pods_resp:
                for p in pods_resp["data"].get("items", []):
                    ns = p["metadata"]["namespace"]
                    affected_pods.append(f"{ns}/{p['metadata']['name']}")
        return {"success": False, "requires_confirmation": True, "operation": operation,
                "node": node_name, "affected_pods": affected_pods,
                "hint": "Add confirm=true to confirm"}

    try:
        if operation == "status":
            resp = kubectl_cce(ctx, region, cluster_id, [
                "get", "node", node_name, "-o", "json",
            ])
            if not resp["success"]:
                return resp
            node = resp["data"]
            unschedulable = node.get("spec", {}).get("unschedulable", False)
            conditions = {c["type"]: c["status"] for c in node.get("status", {}).get("conditions", [])}
            return {
                "success": True, "operation": "status", "node": node_name,
                "schedulable": not unschedulable,
                "ready": conditions.get("Ready") == "True",
                "conditions": conditions,
            }

        elif operation == "cordon":
            resp = kubectl_cce(ctx, region, cluster_id, ["cordon", node_name])
            if not resp["success"]:
                return resp
            return {"success": True, "operation": "cordon", "node": node_name, "message": "Node cordoned"}

        elif operation == "uncordon":
            resp = kubectl_cce(ctx, region, cluster_id, ["uncordon", node_name])
            if not resp["success"]:
                return resp
            return {"success": True, "operation": "uncordon", "node": node_name, "message": "Node uncordoned"}

        elif operation == "drain":
            # kubectl drain handles cordon + eviction + PDB + DaemonSet skip natively
            resp = kubectl_cce(ctx, region, cluster_id, [
                "drain", node_name,
                "--ignore-daemonsets",
                "--delete-emptydir-data",
                "--grace-period=30",
                "--timeout=120s",
            ])
            if not resp["success"]:
                # Check if it's a PDB-related error
                err = resp.get("error", "")
                if "PodDisruptionBudget" in err or "PDB" in err:
                    return {
                        "success": False, "operation": "drain", "node": node_name,
                        "error": err,
                        "warning": "Drain blocked by PodDisruptionBudget. Wait for protected workloads or scale them down.",
                    }
                return resp
            return {
                "success": True, "operation": "drain", "node": node_name,
                "message": f"Node {node_name} drained successfully (cordoned + evicted all evictable pods)",
            }

        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


def cce_node_cordon(params: Dict[str, str]) -> Dict[str, Any]:
    return _node_operation(params, "cordon")

def cce_node_uncordon(params: Dict[str, str]) -> Dict[str, Any]:
    return _node_operation(params, "uncordon")

def cce_node_drain(params: Dict[str, str]) -> Dict[str, Any]:
    return _node_operation(params, "drain")

def cce_node_status(params: Dict[str, str]) -> Dict[str, Any]:
    return _node_operation(params, "status")


# ============================================================
# Nodepool: create (SDK), resize/delete (name->UID)
# ============================================================

def create_node_pool(params: Dict[str, str]) -> Dict[str, Any]:
    """Create node pool via SDK (hcloud defect). Uses resolve_node_login."""
    region = params["region"]
    cluster_id = params["cluster_id"]
    nodepool_name = params["nodepool_name"]
    flavor = params["flavor"]
    availability_zone = params["availability_zone"]
    root_volume_size = int(params["root_volume_size"])
    root_volume_type = params["root_volume_type"]
    initial_node_count = int(params.get("initial_node_count", 1))
    os_type = params.get("os_type", "Huawei Cloud EulerOS 2.0")
    ssh_key = params.get("ssh_key")
    password = params.get("password")
    data_volumes = json.loads(params["data_volumes"]) if params.get("data_volumes") else None
    subnet_id = params.get("subnet_id")
    autoscaling_enabled = params.get("autoscaling_enabled", "false").lower() == "true"
    min_node_count = int(params.get("min_node_count", 0)) if autoscaling_enabled else None
    max_node_count = int(params.get("max_node_count", 0)) if autoscaling_enabled else None

    ctx = resolve_credentials(params.get("ak"), params.get("sk"), params.get("project_id"), region)
    if not ctx.ak or not ctx.sk:
        return {"success": False, "error": "Credentials not provided."}

    login_config, was_auto = resolve_node_login(ssh_key, password)

    try:
        from huaweicloudsdkcce.v3 import (
            CreateNodePoolRequest, NodePool, NodePoolMetadata, NodePoolSpec,
            NodeSpec, Volume, Login, UserPassword, NodeNicSpec, NodePoolNodeAutoscaling,
        )

        client = create_cce_client(region, ctx.ak, ctx.sk, ctx.project_id, ctx.security_token)

        # Build login from resolve_node_login output
        login = Login()
        if "sshKey" in login_config:
            login.ssh_key = login_config["sshKey"]
        elif "userPassword" in login_config:
            login.user_password = UserPassword(
                username=login_config["userPassword"]["username"],
                password=login_config["userPassword"]["password"],
            )

        root_volume = Volume(size=root_volume_size, volumetype=root_volume_type)
        node_spec = NodeSpec(flavor=flavor, az=availability_zone, os=os_type,
                             root_volume=root_volume, login=login)
        if data_volumes:
            node_spec.data_volumes = [
                Volume(size=dv.get("size", 100), volumetype=dv.get("type", "SSD")) for dv in data_volumes
            ]
        if subnet_id:
            node_spec.node_nic_spec = NodeNicSpec(primary_nic={"subnetId": subnet_id})

        spec = NodePoolSpec(initial_node_count=initial_node_count, node_template=node_spec)
        if autoscaling_enabled:
            spec.autoscaling = NodePoolNodeAutoscaling(
                enable=True, min_node_count=min_node_count, max_node_count=max_node_count,
            )

        body = NodePool(kind="NodePool", api_version="v3",
                        metadata=NodePoolMetadata(name=nodepool_name), spec=spec)
        request = CreateNodePoolRequest(cluster_id=cluster_id)
        request.body = body
        response = client.create_node_pool(request)

        msg = f"Node pool '{nodepool_name}' creation submitted"
        if was_auto:
            msg += ". Node login password was auto-generated. To access nodes, reset the password via CCE console or ECS API."
        return {
            "success": True, "region": region, "cluster_id": cluster_id,
            "action": "create_node_pool", "nodepool_name": nodepool_name, "message": msg,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


def resize_node_pool(params: Dict[str, str]) -> Dict[str, Any]:
    """Resize node pool. name->UID resolution via ListNodePools, then ScaleNodePool."""
    region = params["region"]
    cluster_id = params["cluster_id"]
    nodepool_id = params["nodepool_id"]  # could be name or UID
    node_count = int(params["node_count"])
    confirm = params.get("confirm", "").lower() == "true"

    ctx = resolve_credentials(params.get("ak"), params.get("sk"), params.get("project_id"), region)
    if not ctx.ak or not ctx.sk:
        return {"success": False, "error": "Credentials not provided."}

    if not confirm:
        return {"success": False, "requires_confirmation": True, "operation": "resize_nodepool",
                "nodepool_id": nodepool_id, "target_node_count": node_count,
                "hint": "Add confirm=true to confirm"}

    # Resolve name->UID
    list_result = run(ctx, region, "CCE", "ListNodePools", {"cluster_id": cluster_id})
    if not list_result["success"]:
        return list_result

    uid = None
    # NOTE: iterates over already-fetched ListNodePools result; not N+1
    for np in list_result["data"].get("items", []):
        np_id = np.get("metadata", {}).get("uid", "")
        np_name = np.get("metadata", {}).get("name", "")
        if nodepool_id in (np_id, np_name):
            uid = np_id
            break
    if not uid:
        uid = nodepool_id  # fallback: assume it's already a UID

    result = run(ctx, region, "CCE", "ScaleNodePool", {
        "cluster_id": cluster_id, "nodepool_id": uid,
        "apiVersion": "v3", "kind": "NodePool",
        "spec.desiredNodeCount": str(node_count),
        "spec.scaleGroups.1": "default",
    })
    if not result["success"]:
        return result
    return {
        "success": True, "region": region, "cluster_id": cluster_id,
        "action": "resize_node_pool", "nodepool_id": nodepool_id,
        "target_node_count": node_count, "message": "Node pool resize submitted",
    }


def delete_node_pool(params: Dict[str, str]) -> Dict[str, Any]:
    """Delete node pool. name->UID resolution, then DeleteNodePool."""
    region = params["region"]
    cluster_id = params["cluster_id"]
    nodepool_id = params["nodepool_id"]
    confirm = params.get("confirm", "").lower() == "true"

    ctx = resolve_credentials(params.get("ak"), params.get("sk"), params.get("project_id"), region)
    if not ctx.ak or not ctx.sk:
        return {"success": False, "error": "Credentials not provided."}

    if not confirm:
        return {"success": False, "requires_confirmation": True, "operation": "delete_node_pool",
                "nodepool_id": nodepool_id,
                "hint": "Add confirm=true to confirm"}

    # Resolve name->UID
    list_result = run(ctx, region, "CCE", "ListNodePools", {"cluster_id": cluster_id})
    if not list_result["success"]:
        return list_result

    uid = None
    # NOTE: iterates over already-fetched ListNodePools result; not N+1
    for np in list_result["data"].get("items", []):
        np_id = np.get("metadata", {}).get("uid", "")
        np_name = np.get("metadata", {}).get("name", "")
        if nodepool_id in (np_id, np_name):
            uid = np_id
            break
    if not uid:
        uid = nodepool_id

    result = run(ctx, region, "CCE", "DeleteNodePool", {
        "cluster_id": cluster_id, "nodepool_id": uid,
    })
    if not result["success"]:
        return result
    return {
        "success": True, "region": region, "cluster_id": cluster_id,
        "action": "delete_node_pool", "nodepool_id": nodepool_id,
        "message": "Node pool deletion submitted",
    }


# ============================================================
# Addon: install/update (hcloud --param=value)
# ============================================================

def install_cce_addon(params: Dict[str, str]) -> Dict[str, Any]:
    """Install addon via hcloud --cli-jsonInput (annotation keys contain '/')."""
    region = params["region"]
    cluster_id = params["cluster_id"]
    addon_template_name = params["addon_template_name"]
    addon_version = params.get("addon_version")
    values = json.loads(params["values"]) if params.get("values") else {}

    ctx = resolve_credentials(params.get("ak"), params.get("sk"), params.get("project_id"), region)
    if not ctx.ak or not ctx.sk:
        return {"success": False, "error": "Credentials not provided."}

    body = {
        "kind": "Addon",
        "apiVersion": "v3",
        "metadata": {"annotations": {"addon.install/type": "install"}},
        "spec": {
            "clusterID": cluster_id,
            "addonTemplateName": addon_template_name,
        },
    }
    if addon_version:
        body["spec"]["version"] = addon_version
    if values:
        body["spec"]["values"] = values

    result = run_with_body(ctx, region, "CCE", "CreateAddonInstance", body)
    if not result["success"]:
        return result
    return {
        "success": True, "region": region, "cluster_id": cluster_id,
        "action": "install_cce_addon",
        "addon_template_name": addon_template_name,
        "message": f"Addon {addon_template_name} installation submitted",
    }


def update_cce_addon(params: Dict[str, str]) -> Dict[str, Any]:
    """Update addon via hcloud --cli-jsonInput (annotation keys contain '/')."""
    region = params["region"]
    cluster_id = params["cluster_id"]
    addon_id = params["addon_id"]
    addon_template_name = params.get("addon_template_name")
    addon_version = params.get("addon_version")
    values = json.loads(params["values"]) if params.get("values") else {}

    ctx = resolve_credentials(params.get("ak"), params.get("sk"), params.get("project_id"), region)
    if not ctx.ak or not ctx.sk:
        return {"success": False, "error": "Credentials not provided."}

    body = {
        "kind": "Addon",
        "apiVersion": "v3",
        "metadata": {"annotations": {"addon.upgrade/type": "upgrade"}},
        "spec": {
            "clusterID": cluster_id,
        },
    }
    if addon_template_name:
        body["spec"]["addonTemplateName"] = addon_template_name
    if addon_version:
        body["spec"]["version"] = addon_version
    else:
        # Auto-fetch current addon version to avoid CCE.03500001 (version is required for UpdateAddonInstance)
        show_result = run(ctx, region, "CCE", "ShowAddonInstance", {
            "cluster_id": cluster_id, "id": addon_id,
        })
        if show_result.get("success"):
            current_version = show_result["data"].get("spec", {}).get("version")
            if current_version:
                body["spec"]["version"] = current_version
            else:
                return {"success": False, "error": "Could not determine current addon version. Please provide addon_version explicitly."}
        else:
            return {"success": False, "error": f"Failed to query addon version: {show_result.get('error', 'unknown')}"}
    if values:
        body["spec"]["values"] = values

    result = run_with_body(ctx, region, "CCE", "UpdateAddonInstance", body,
                           path_params={"id": addon_id})
    if not result["success"]:
        return result
    return {
        "success": True, "region": region, "cluster_id": cluster_id,
        "action": "update_cce_addon", "addon_id": addon_id,
        "message": f"Addon {addon_id} update submitted",
    }
