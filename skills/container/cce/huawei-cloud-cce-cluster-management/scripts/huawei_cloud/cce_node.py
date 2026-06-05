"""CCE Node management functions."""

from typing import Any, Dict, List, Optional
from .common import (
    get_credentials,
    create_cce_client,
    SDK_AVAILABLE,
    IMPORT_ERROR,
    K8S_AVAILABLE,
    K8S_IMPORT_ERROR,
)
from huaweicloudsdkcore.exceptions.exceptions import ClientRequestException


def list_cce_nodes(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """List nodes in a CCE cluster with pagination"""
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters.",
        }

    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    if not SDK_AVAILABLE:
        return {"success": False, "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"}

    try:
        from huaweicloudsdkcce.v3 import ListNodesRequest

        client = create_cce_client(region, access_key, secret_key, proj_id)

        request = ListNodesRequest()
        request.cluster_id = cluster_id

        response = client.list_nodes(request)

        nodes = []
        if hasattr(response, "items") and response.items:
            for node in response.items:
                node_info = {
                    "id": node.metadata.uid,
                    "name": node.metadata.name,
                    "status": node.status.phase
                    if hasattr(node, "status") and hasattr(node.status, "phase")
                    else "Unknown",
                    "created_at": str(node.metadata.creation_timestamp)
                    if hasattr(node, "metadata") and hasattr(node.metadata, "creation_timestamp")
                    else None,
                    "labels": dict(node.metadata.labels)
                    if hasattr(node.metadata, "labels") and node.metadata.labels
                    else {},
                }
                if hasattr(node, "spec"):
                    node_info["flavor"] = getattr(node.spec, "flavor", None)
                    node_info["server_id"] = getattr(node.status, "server_id", None)
                    node_info["availability_zone"] = getattr(node.spec, "az", None)
                if hasattr(node, "status") and hasattr(node.status, "conditions"):
                    conditions = []
                    for cond in node.status.conditions:
                        conditions.append({
                            "type": cond.type,
                            "status": cond.status,
                            "reason": getattr(cond, "reason", None),
                        })
                    node_info["conditions"] = conditions
                nodes.append(node_info)

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "list_cce_nodes",
            "count": len(nodes),
            "nodes": nodes,
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, "request_id", None),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


def delete_cce_node(
    region: str,
    cluster_id: str,
    node_id: str,
    confirm: bool = False,
    scale_down: bool = True,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Delete a node from CCE cluster

    IMPORTANT: This operation will delete the node and all its pods.
    User confirmation is required before deletion.

    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        cluster_id: CCE cluster ID
        node_id: Node ID to delete
        confirm: Must be set to True to confirm deletion (required)
        scale_down: Whether to scale down pods before deleting (default: True)
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)

    Returns:
        Dictionary with deletion result
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters.",
        }

    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    if not node_id:
        return {"success": False, "error": "node_id is required"}

    if not confirm:
        return {
            "success": False,
            "error": "Deletion not confirmed. To delete the node, please set confirm=true parameter.",
            "warning": f"This operation will delete the node '{node_id}' from cluster '{cluster_id}'. All pods on this node will be terminated. Are you sure?",
            "hint": "Add confirm=true parameter to confirm deletion. Example: delete_cce_node region=cn-north-4 cluster_id=xxx node_id=yyy confirm=true",
        }

    if not SDK_AVAILABLE:
        return {"success": False, "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"}

    try:
        from huaweicloudsdkcce.v3 import DeleteNodeRequest

        client = create_cce_client(region, access_key, secret_key, proj_id)

        request = DeleteNodeRequest()
        request.cluster_id = cluster_id
        request.node_id = node_id
        request.nodepool_scale_down = scale_down

        response = client.delete_node(request)

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "node_id": node_id,
            "action": "delete_cce_node",
            "message": "Node deletion request submitted successfully",
            "scale_down": scale_down,
            "response": response.to_dict() if hasattr(response, "to_dict") else str(response),
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, "request_id", None),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


def _node_operation(
    region: str,
    cluster_id: str,
    node_name: str,
    operation: str,
    confirm: bool = False,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: str = None,
) -> Dict[str, Any]:
    """Internal helper for CCE node operations (cordon/uncordon/drain/status)

    Args:
        region: Huawei Cloud region
        cluster_id: CCE cluster ID
        node_name: Node name or IP address
        operation: One of 'cordon', 'uncordon', 'drain', 'status'
        confirm: Required for write operations (cordon/uncordon/drain)
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)

    Returns:
        Dictionary with operation result
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {"success": False, "error": "Credentials not provided."}

    if not K8S_AVAILABLE:
        return {"success": False, "error": f"Kubernetes SDK not installed: {K8S_IMPORT_ERROR}"}

    ca_cert_file = client_cert_file = client_key_file = None

    try:
        cce_client = create_cce_client(region, access_key, secret_key, proj_id)
        from huaweicloudsdkcce.v3 import CreateKubernetesClusterCertRequest, ClusterCertDuration

        cert_req = CreateKubernetesClusterCertRequest(cluster_id=cluster_id)
        cert_req.body = ClusterCertDuration(duration=1)
        kubeconfig_data = cce_client.create_kubernetes_cluster_cert(cert_req).to_dict()

        import tempfile
        import os
        import yaml
        import base64
        import kubernetes as k8s
        from kubernetes.client import Configuration, CoreV1Api

        raw_kc = kubeconfig_data.get("kubeconfig") or kubeconfig_data.get("content", "") or kubeconfig_data
        kc = yaml.safe_load(raw_kc) if isinstance(raw_kc, str) and raw_kc else raw_kc
        current_ctx = kc.get("current_context", "")
        ctx_entry = next((c for c in kc.get("contexts", []) if c["name"] == current_ctx), None)
        if not ctx_entry:
            return {"success": False, "error": f"Context '{current_ctx}' not found in kubeconfig"}
        cluster_name = ctx_entry["context"]["cluster"]
        user_name = ctx_entry["context"]["user"]

        cluster_entry = next((c for c in kc.get("clusters", []) if c["name"] == cluster_name), None)
        if not cluster_entry:
            return {"success": False, "error": f"Cluster '{cluster_name}' not found in kubeconfig"}
        cluster_cfg = cluster_entry["cluster"]

        user_entry = next((u for u in kc.get("users", []) if u["name"] == user_name), None)
        if not user_entry:
            return {"success": False, "error": f"User '{user_name}' not found in kubeconfig"}
        user_cfg = user_entry["user"]

        server = cluster_cfg.get("server", "")

        ca_data = cluster_cfg.get("certificate_authority_data")
        if ca_data:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".crt", delete=False) as f:
                f.write(base64.b64decode(ca_data).decode())
                ca_cert_file = f.name

        cert_data = user_cfg.get("client_certificate_data")
        key_data = user_cfg.get("client_key_data")
        if cert_data and key_data:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".crt", delete=False) as f:
                f.write(base64.b64decode(cert_data).decode())
                client_cert_file = f.name
            with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
                f.write(base64.b64decode(key_data).decode())
                client_key_file = f.name

        skip_tls = cluster_cfg.get("insecure_skip_tls_verify", False)

        config = Configuration()
        config.host = server
        config.verify_ssl = not skip_tls
        if ca_cert_file:
            config.ssl_ca_cert = ca_cert_file
        if client_cert_file:
            config.cert_file = client_cert_file
        if client_key_file:
            config.key_file = client_key_file

        api_client = k8s.client.ApiClient(config)
        core_v1 = CoreV1Api(api_client)

        if operation == "status":
            node = core_v1.read_node(node_name)
            conditions = {c.type: c.status for c in node.status.conditions}
            node_labels = dict(node.metadata.labels) if node.metadata.labels else {}
            return {
                "success": True,
                "operation": "status",
                "node": node_name,
                "schedulable": node.spec.unschedulable is None,
                "ready": conditions.get("Ready") == "True",
                "conditions": conditions,
                "os_version": node_labels.get("node.kubernetes.io/os_version", ""),
                "kernel_version": node_labels.get("node.kubernetes.io/kernel_version", ""),
            }
        elif operation == "cordon":
            if not confirm:
                return {
                    "success": False,
                    "requires_confirmation": True,
                    "operation": "cordon",
                    "node": node_name,
                    "error": f"Cordon will mark node {node_name} as unschedulable.",
                    "hint": f"Add confirm=true to confirm. Example: cce_node_cordon region=cn-north-4 cluster_id=xxx node_name=192.168.x.x confirm=true",
                }
            core_v1.patch_node(node_name, {"spec": {"unschedulable": True}})
            return {
                "success": True,
                "operation": "cordon",
                "node": node_name,
                "message": "Node marked as unschedulable",
            }
        elif operation == "uncordon":
            if not confirm:
                return {
                    "success": False,
                    "requires_confirmation": True,
                    "operation": "uncordon",
                    "node": node_name,
                    "error": f"Uncordon will mark node {node_name} as schedulable. New pods may be immediately assigned.",
                    "hint": f"Add confirm=true to confirm. Example: cce_node_uncordon region=cn-north-4 cluster_id=xxx node_name=192.168.x.x confirm=true",
                }
            core_v1.patch_node(node_name, {"spec": {"unschedulable": None}})
            return {
                "success": True,
                "operation": "uncordon",
                "node": node_name,
                "message": "Node marked as schedulable",
            }
        elif operation == "drain":
            if not confirm:
                pods_preview = core_v1.list_pod_for_all_namespaces(
                    field_selector=f"spec.nodeName={node_name}"
                ).items
                affected = [
                    f"{p.metadata.namespace}/{p.metadata.name}"
                    for p in pods_preview
                    if p.metadata.namespace not in ("kube-system", "hss", "monitoring")
                ]
                return {
                    "success": False,
                    "requires_confirmation": True,
                    "operation": "drain",
                    "node": node_name,
                    "affected_pods": affected,
                    "error": f"Drain will delete {len(affected)} non-system pods on node {node_name}.",
                    "hint": f"Add confirm=true to confirm. Example: cce_node_drain region=cn-north-4 cluster_id=xxx node_name=192.168.x.x confirm=true",
                }
            skip_ns = set(["kube-system", "hss", "monitoring"])
            grace = 30
            pods = core_v1.list_pod_for_all_namespaces(
                field_selector=f"spec.nodeName={node_name}"
            ).items
            deleted, skipped = [], []
            for p in pods:
                ns, pname = p.metadata.namespace, p.metadata.name
                if ns in skip_ns:
                    skipped.append(f"{ns}/{pname}")
                    continue
                try:
                    body = k8s.client.V1DeleteOptions(grace_period_seconds=grace)
                    core_v1.delete_namespaced_pod(pname, ns, body=body)
                    deleted.append(f"{ns}/{pname}")
                except Exception as e:
                    skipped.append(f"{ns}/{pname} ({e})"[:100])
            return {
                "success": True,
                "operation": "drain",
                "node": node_name,
                "deleted": deleted,
                "skipped": skipped,
            }
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}
    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, "request_id", None),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
    finally:
        for f in [ca_cert_file, client_cert_file, client_key_file]:
            if f and os.path.exists(f):
                try:
                    os.unlink(f)
                except Exception:
                    pass


def cce_node_cordon(
    region: str,
    cluster_id: str,
    node_name: str,
    confirm: bool = False,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: str = None,
) -> Dict[str, Any]:
    """Mark CCE node as unschedulable (cordon)

    Args:
        region: Huawei Cloud region
        cluster_id: CCE cluster ID
        node_name: Node name or IP address
        confirm: Must be True to confirm the operation
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)

    Returns:
        Dictionary with operation result
    """
    return _node_operation(
        region,
        cluster_id,
        node_name,
        "cordon",
        confirm=confirm,
        ak=ak,
        sk=sk,
        project_id=project_id,
    )


def cce_node_uncordon(
    region: str,
    cluster_id: str,
    node_name: str,
    confirm: bool = False,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: str = None,
) -> Dict[str, Any]:
    """Mark CCE node as schedulable (uncordon)

    Args:
        region: Huawei Cloud region
        cluster_id: CCE cluster ID
        node_name: Node name or IP address
        confirm: Must be True to confirm the operation
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)

    Returns:
        Dictionary with operation result
    """
    return _node_operation(
        region,
        cluster_id,
        node_name,
        "uncordon",
        confirm=confirm,
        ak=ak,
        sk=sk,
        project_id=project_id,
    )


def cce_node_drain(
    region: str,
    cluster_id: str,
    node_name: str,
    confirm: bool = False,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: str = None,
) -> Dict[str, Any]:
    """Drain CCE node (evict all non-system pods)

    Args:
        region: Huawei Cloud region
        cluster_id: CCE cluster ID
        node_name: Node name or IP address
        confirm: Must be True to confirm the operation
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)

    Returns:
        Dictionary with operation result
    """
    return _node_operation(
        region,
        cluster_id,
        node_name,
        "drain",
        confirm=confirm,
        ak=ak,
        sk=sk,
        project_id=project_id,
    )


def cce_node_status(
    region: str,
    cluster_id: str,
    node_name: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: str = None,
) -> Dict[str, Any]:
    """Query CCE node schedulability status

    Args:
        region: Huawei Cloud region
        cluster_id: CCE cluster ID
        node_name: Node name or IP address
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)

    Returns:
        Dictionary with node status (schedulable, ready, conditions)
    """
    return _node_operation(
        region,
        cluster_id,
        node_name,
        "status",
        confirm=True,
        ak=ak,
        sk=sk,
        project_id=project_id,
    )


def create_cce_node(
    region: str,
    cluster_id: str,
    flavor: str,
    availability_zone: str,
    root_volume_size: int = 40,
    root_volume_type: str = "SSD",
    node_count: int = 1,
    os_type: str = "EulerOS 2.9",
    ssh_key: Optional[str] = None,
    password: Optional[str] = None,
    data_volumes: Optional[List[Dict[str, Any]]] = None,
    subnet_id: Optional[str] = None,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create nodes in a CCE cluster

    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        cluster_id: CCE cluster ID
        flavor: Node flavor (e.g., c6.large.2)
        availability_zone: Availability zone (e.g., cn-north-4a)
        root_volume_size: Root volume size in GB (default: 40)
        root_volume_type: Root volume type (default: SSD)
        node_count: Number of nodes to create (default: 1)
        os_type: Operating system type (default: EulerOS 2.9)
        ssh_key: SSH key pair name for login
        password: Password for login (used if ssh_key not provided)
        data_volumes: List of data volume configs [{"size": 100, "type": "SSD"}]
        subnet_id: Subnet ID for the node
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)

    Returns:
        Dictionary with creation result
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters.",
        }

    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    if not flavor:
        return {"success": False, "error": "flavor is required"}

    if not availability_zone:
        return {"success": False, "error": "availability_zone is required"}

    if not SDK_AVAILABLE:
        return {"success": False, "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"}

    try:
        from huaweicloudsdkcce.v3 import (
            CreateNodeRequest,
            CreateNodeRequestBody,
            NodeMetadata,
            NodeSpec,
            Volume,
            Login,
            UserPassword,
            NodeNicSpec,
        )

        client = create_cce_client(region, access_key, secret_key, proj_id)

        root_volume = Volume(size=root_volume_size, volumetype=root_volume_type)

        data_volume_list = []
        if data_volumes:
            for vol in data_volumes:
                data_volume_list.append(
                    Volume(
                        size=vol.get("size", 100),
                        volumetype=vol.get("type", "SSD"),
                    )
                )

        login = None
        if ssh_key:
            login = Login(sshkey=ssh_key)
        elif password:
            login = Login(userPassword=UserPassword(username="root", password=password))

        node_spec = NodeSpec(
            flavor=flavor,
            az=availability_zone,
            os=os_type,
            login=login,
            rootVolume=root_volume,
            dataVolumes=data_volume_list if data_volume_list else None,
            nodeNicSpec=NodeNicSpec(subnetId=subnet_id) if subnet_id else None,
        )

        node_metadata = NodeMetadata(name=f"node-{cluster_id[:8]}")

        request_body = CreateNodeRequestBody(
            metadata=node_metadata,
            spec=node_spec,
            count=node_count,
        )

        request = CreateNodeRequest(cluster_id=cluster_id)
        request.body = request_body

        response = client.create_node(request)

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "create_cce_node",
            "node_count": node_count,
            "flavor": flavor,
            "availability_zone": availability_zone,
            "message": f"Node creation request submitted for {node_count} node(s)",
            "response": response.to_dict() if hasattr(response, "to_dict") else str(response),
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, "request_id", None),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}