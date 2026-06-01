"""CCE Cluster management functions."""

import hashlib
import hmac
import time as time_module
import urllib.parse
from urllib.parse import quote, unquote
from typing import Any, Dict, List, Optional
import requests

from huaweicloudsdkcce.v3 import (
    CreateClusterRequest,
    DeleteClusterRequest,
    ListClustersRequest,
    ShowClusterRequest,
    HibernateClusterRequest,
    AwakeClusterRequest,
    Cluster,
    ClusterMetadata,
    ClusterSpec,
    ContainerNetwork,
    HostNetwork,
    ServiceNetwork,
    EniNetwork,
    NetworkSubnet,
)
from huaweicloudsdkcce.v3.region.cce_region import CceRegion
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.exceptions.exceptions import ClientRequestException
from huaweicloudsdkvpc.v2 import ShowSubnetRequest
from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion
from .common import (
    get_credentials,
    get_credentials_with_region,
    create_cce_client,
    SDK_AVAILABLE,
    IMPORT_ERROR,
    _register_cert_file,
    _safe_delete_file,
)


def _resolve_neutron_subnet_id(region: str, vpc_subnet_id: str, ak: str, sk: str, project_id: Optional[str] = None) -> Optional[str]:
    """Resolve the Neutron subnet UUID from a VPC subnet UUID.

    CCE Turbo (ENI) clusters require the Neutron subnet UUID in the
    eniNetwork.subnets[].subnetID field, while HostNetwork.subnet uses
    the VPC subnet UUID. This helper queries the VPC API to obtain the
    neutron_subnet_id for a given VPC subnet.

    Args:
        region: Huawei Cloud region
        vpc_subnet_id: VPC subnet UUID (e.g., b8a2c56a-...)
        ak: Access Key
        sk: Secret Key
        project_id: Project ID (optional, will be resolved from region if not provided)

    Returns:
        Neutron subnet UUID string, or None if lookup fails
    """
    try:
        # Resolve project ID from region if not provided
        access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)
        if not proj_id:
            return None
        from huaweicloudsdkvpc.v2 import VpcClient
        creds = BasicCredentials(ak=access_key, sk=secret_key, project_id=proj_id)
        vpc_client = VpcClient.new_builder() \
            .with_credentials(creds) \
            .with_endpoint(f'vpc.{region}.myhuaweicloud.com') \
            .build()
        req = ShowSubnetRequest(subnet_id=vpc_subnet_id)
        resp = vpc_client.show_subnet(req)
        if hasattr(resp, 'subnet') and hasattr(resp.subnet, 'neutron_subnet_id'):
            return resp.subnet.neutron_subnet_id
    except Exception:
        pass
    return None


def list_cce_clusters(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """List CCE clusters in the specified region with pagination"""
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not SDK_AVAILABLE:
        return {
            "success": False,
            "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"
        }

    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)

        request = ListClustersRequest()

        response = client.list_clusters(request)

        clusters = []
        if hasattr(response, 'items') and response.items:
            for cluster in response.items:
                cluster_info = {
                    "id": cluster.metadata.uid,
                    "name": cluster.metadata.name,
                    "status": cluster.status.phase if hasattr(cluster, 'status') and hasattr(cluster.status, 'phase') else 'Unknown',
                    "type": cluster.spec.type if hasattr(cluster, 'spec') and hasattr(cluster.spec, 'type') else 'Unknown',
                    "version": cluster.spec.version if hasattr(cluster, 'spec') and hasattr(cluster.spec, 'version') else 'Unknown',
                    "created_at": str(cluster.metadata.creation_timestamp) if hasattr(cluster, 'metadata') and hasattr(cluster.metadata, 'creation_timestamp') else None,
                }
                if hasattr(cluster, 'spec') and hasattr(cluster.spec, 'network'):
                    cluster_info["network"] = {
                        "vpc_id": getattr(cluster.spec.network, 'vpc_id', None),
                        "subnet_id": getattr(cluster.spec.network, 'subnet_id', None),
                    }
                if hasattr(cluster, 'spec') and hasattr(cluster.spec, 'node'):
                    cluster_info["node_config"] = {
                        "flavor": getattr(cluster.spec.node, 'flavor', None),
                        "count": getattr(cluster.spec.node, 'initial_node_count', None),
                    }
                clusters.append(cluster_info)

        return {
            "success": True,
            "region": region,
            "action": "list_cce_clusters",
            "count": len(clusters),
            "clusters": clusters
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, 'request_id', None)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


def get_cce_nodes(region: str, cluster_id: str, node_name: Optional[str] = None, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    """Get detailed information about CCE cluster nodes
    
    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        cluster_id: CCE cluster ID
        node_name: Node name (optional, if not provided, returns all nodes)
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)

    Returns:
        Dictionary with node details
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not cluster_id:
        return {
            "success": False,
            "error": "cluster_id is required"
        }

    if not SDK_AVAILABLE:
        return {
            "success": False,
            "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"
        }

    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)

        request = ListNodesRequest()
        request.cluster_id = cluster_id

        response = client.list_nodes(request)

        nodes = []
        if hasattr(response, 'items') and response.items:
            for node in response.items:
                if node_name and node.metadata.name != node_name:
                    continue
                
                node_info = {
                    "id": node.metadata.uid,
                    "name": node.metadata.name,
                    "status": node.status.phase if hasattr(node, 'status') and hasattr(node.status, 'phase') else 'Unknown',
                    "created_at": str(node.metadata.creation_timestamp) if hasattr(node, 'metadata') and hasattr(node.metadata, 'creation_timestamp') else None,
                }
                if hasattr(node, 'spec'):
                    node_info["flavor"] = getattr(node.spec, 'flavor', None)
                    node_info["server_id"] = getattr(node.status, 'server_id', None)
                    node_info["availability_zone"] = getattr(node.spec, 'az', None)
                if hasattr(node, 'status') and hasattr(node.status, 'conditions'):
                    conditions = []
                    for cond in node.status.conditions:
                        conditions.append({
                            "type": cond.type,
                            "status": cond.status,
                            "reason": getattr(cond, 'reason', None),
                            "message": getattr(cond, 'message', None),
                        })
                    node_info["conditions"] = conditions
                if hasattr(node, 'status'):
                    node_info["allocatable"] = getattr(node.status, 'allocatable', None)
                    node_info["capacity"] = getattr(node.status, 'capacity', None)
                nodes.append(node_info)

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "get_cce_nodes",
            "node_name": node_name,
            "count": len(nodes),
            "nodes": nodes
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, 'request_id', None)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


def get_cce_kubeconfig(region: str, cluster_id: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, duration: int = 30) -> Dict[str, Any]:
    """Get kubeconfig for a CCE cluster

    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        cluster_id: CCE cluster ID
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)
        duration: Certificate validity duration in days (default: 30)

    Returns:
        Dictionary with kubeconfig content
    """
    access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not proj_id:
        return {
            "success": False,
            "error": "Project ID not found. Please provide project_id parameter."
        }

    if not cluster_id:
        return {
            "success": False,
            "error": "cluster_id is required"
        }

    if not SDK_AVAILABLE:
        return {
            "success": False,
            "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"
        }

    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)
        
        cert_duration = ClusterCertDuration(duration=duration)
        request = CreateKubernetesClusterCertRequest(cluster_id=cluster_id)
        request.body = cert_duration
        
        response = client.create_kubernetes_cluster_cert(request)
        
        result = {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "get_cce_kubeconfig",
            "duration_days": duration,
        }
        
        if hasattr(response, 'to_dict'):
            resp_dict = response.to_dict()
            
            result["kubeconfig"] = resp_dict
            
            if 'clusters' in resp_dict:
                result["cluster_endpoints"] = []
                for cluster in resp_dict['clusters']:
                    endpoint_info = {
                        "name": cluster.get('name'),
                        "server": cluster.get('cluster', {}).get('server')
                    }
                    result["cluster_endpoints"].append(endpoint_info)
            
            if 'current_context' in resp_dict:
                result["current_context"] = resp_dict['current_context']
            
            import yaml
            result["kubeconfig_yaml"] = yaml.dump(resp_dict, default_flow_style=False, allow_unicode=True)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


def delete_cce_cluster(region: str, cluster_id: str, confirm: bool = False, delete_evs: bool = False, delete_net: bool = False, delete_obs: bool = False, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    """Delete a CCE cluster

    IMPORTANT: This operation will delete the cluster and all its resources.
    User confirmation is required before deletion.

    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        cluster_id: CCE cluster ID to delete
        confirm: Must be set to True to confirm deletion (required)
        delete_evs: Whether to delete associated EVS volumes (default: False)
        delete_net: Whether to delete associated network resources (default: False)
        delete_obs: Whether to delete associated OBS buckets (default: False)
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
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not cluster_id:
        return {
            "success": False,
            "error": "cluster_id is required"
        }

    if not confirm:
        return {
            "success": False,
            "error": "Deletion not confirmed. To delete the cluster, please set confirm=true parameter.",
            "warning": "This operation will delete the cluster and all its resources (nodes, workloads, etc.). Are you sure you want to delete this cluster?",
            "hint": "Add confirm=true parameter to confirm deletion. Example: delete_cce_cluster region=cn-north-4 cluster_id=xxx confirm=true"
        }

    if not SDK_AVAILABLE:
        return {
            "success": False,
            "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"
        }

    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)

        request = DeleteClusterRequest()
        request.cluster_id = cluster_id
        request.delete_evs = delete_evs
        request.delete_net = delete_net
        request.delete_obs = delete_obs

        response = client.delete_cluster(request)

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "delete_cce_cluster",
            "message": f"Cluster deletion request submitted successfully",
            "delete_evs": delete_evs,
            "delete_net": delete_net,
            "delete_obs": delete_obs,
            "response": response.to_dict() if hasattr(response, 'to_dict') else str(response)
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, 'request_id', None)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


def hibernate_cce_cluster(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Hibernate a CCE cluster (pause billing + workloads)

    Puts the cluster into hibernated state. Billing for control plane is paused.
    Workloads are stopped. Use awake_cce_cluster to resume.

    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        cluster_id: CCE cluster ID
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)
        confirm: Must be True to confirm the operation

    Returns:
        Dictionary with result
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    if not SDK_AVAILABLE:
        return {"success": False, "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"}

    if not confirm:
        return {
            "success": False,
            "requires_confirmation": True,
            "operation": "hibernate_cce_cluster",
            "cluster_id": cluster_id,
            "error": f"Hibernate will pause cluster {cluster_id} and stop all workloads. Billing for control plane is paused.",
            "hint": f"Add confirm=true to confirm. Example: huawei_hibernate_cce_cluster region=cn-north-4 cluster_id=xxx confirm=true"
        }

    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)
        request = HibernateClusterRequest()
        request.cluster_id = cluster_id
        response = client.hibernate_cluster(request)

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "hibernate_cce_cluster",
            "message": "Cluster hibernation request submitted successfully",
            "status_code": response.status_code if hasattr(response, "status_code") else None,
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, "request_id", None),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }


def awake_cce_cluster(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Awake a hibernated CCE cluster (resume billing + workloads)

    Wakes up a previously hibernated cluster. Billing for control plane resumes
    and workloads will be restarted.

    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        cluster_id: CCE cluster ID
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)
        confirm: Must be True to confirm the operation

    Returns:
        Dictionary with result
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    if not SDK_AVAILABLE:
        return {"success": False, "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"}

    if not confirm:
        return {
            "success": False,
            "requires_confirmation": True,
            "operation": "awake_cce_cluster",
            "cluster_id": cluster_id,
            "error": f"Awake will resume cluster {cluster_id}. Control plane billing resumes and workloads restart.",
            "hint": f"Add confirm=true to confirm. Example: huawei_awake_cce_cluster region=cn-north-4 cluster_id=xxx confirm=true"
        }

    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)
        request = AwakeClusterRequest()
        request.cluster_id = cluster_id
        response = client.awake_cluster(request)

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "awake_cce_cluster",
            "message": "Cluster awake request submitted successfully",
            "status_code": response.status_code if hasattr(response, "status_code") else None,
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, "request_id", None),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }


def bind_cce_cluster_eip(
    region: str,
    cluster_id: str,
    eip_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Bind an EIP to a CCE cluster master node for public API access

    Associates an existing Elastic IP with the cluster's control plane,
    enabling public access to the Kubernetes API server.

    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        cluster_id: CCE cluster ID
        eip_id: EIP resource ID to bind (use huawei_list_eip to find available EIPs)
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)

    Returns:
        Dictionary with result including the public endpoint URL
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    if not eip_id:
        return {"success": False, "error": "eip_id is required"}

    if not SDK_AVAILABLE:
        return {"success": False, "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"}

    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)

        spec_spec = MasterEIPRequestSpecSpec(id=eip_id)
        spec = MasterEIPRequestSpec(action="bind", spec=spec_spec)
        body = MasterEIPRequest(spec=spec)
        request = UpdateClusterEipRequest(cluster_id=cluster_id, body=body)

        client.update_cluster_eip(request)

        resp = client.show_cluster(ShowClusterRequest(cluster_id=cluster_id))
        public_url = None
        if hasattr(resp, 'status') and hasattr(resp.status, 'endpoints'):
            for ep in resp.status.endpoints:
                if ep.type == "External":
                    public_url = ep.url
                    break

        result = {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "bind_cce_cluster_eip",
            "eip_id": eip_id,
            "message": "EIP bound to cluster master successfully",
        }
        if public_url:
            result["public_endpoint"] = public_url

        return result

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, "request_id", None),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }


def unbind_cce_cluster_eip(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Unbind the EIP from a CCE cluster master node

    Removes the Elastic IP association from the cluster's control plane,
    disabling public access to the Kubernetes API server.

    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        cluster_id: CCE cluster ID
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)

    Returns:
        Dictionary with result
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    if not SDK_AVAILABLE:
        return {"success": False, "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"}

    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)

        spec = MasterEIPRequestSpec(action="unbind")
        body = MasterEIPRequest(spec=spec)
        request = UpdateClusterEipRequest(cluster_id=cluster_id, body=body)

        client.update_cluster_eip(request)

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "unbind_cce_cluster_eip",
            "message": "EIP unbound from cluster master successfully",
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, "request_id", None),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }


def create_cce_cluster(
    region: str,
    cluster_name: str,
    vpc_id: str,
    subnet_id: str,
    cluster_version: Optional[str] = None,
    cluster_type: str = "VirtualMachine",
    container_network_type: str = "overlay_l2",
    container_network_cidr: Optional[str] = None,
    service_network_cidr: Optional[str] = None,
    flavor_id: Optional[str] = None,
    description: Optional[str] = None,
    eni_subnet_id: Optional[str] = None,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new CCE cluster

    Creates a Cloud Container Engine cluster with specified configuration.
    If cluster_version is not specified, CCE will use the latest supported version.

    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        cluster_name: Name of the cluster to create
        vpc_id: VPC ID where the cluster will be created
        subnet_id: Subnet ID for the cluster
        cluster_version: Kubernetes version (optional, defaults to latest if not specified)
        cluster_type: Cluster type (default: "VirtualMachine", use "VirtualMachine" + eni network for Turbo)
        container_network_type: Container network type (default: "overlay_l2", use "eni" for Turbo clusters)
        container_network_cidr: Container network CIDR (optional, e.g., "172.16.0.0/16")
        service_network_cidr: Service network CIDR (optional, e.g., "10.247.0.0/16")
        flavor_id: Cluster flavor ID (optional, determines control plane specs)
        description: Cluster description (optional)
        eni_subnet_id: ENI subnet ID for Turbo clusters (required when container_network_type="eni")
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)

    Returns:
        Dictionary with cluster creation result
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not cluster_name:
        return {"success": False, "error": "cluster_name is required"}

    if not vpc_id:
        return {"success": False, "error": "vpc_id is required"}

    if not subnet_id:
        return {"success": False, "error": "subnet_id is required"}

    if not SDK_AVAILABLE:
        return {"success": False, "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"}

    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)

        cluster_metadata = ClusterMetadata(name=cluster_name)
        if description:
            cluster_metadata.annotations = {"description": description}

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
            cluster_spec.flavor_id = flavor_id

        # Set eni_network for Turbo clusters (container_network_type="eni")
        # IMPORTANT: CCE Turbo (ENI) clusters require the **Neutron subnet UUID**
        # in eniNetwork.subnets[].subnetID, NOT the VPC subnet UUID.
        # The HostNetwork.subnet field uses the VPC subnet UUID, but the ENI
        # subnet validation checks against Neutron subnet IDs. If the VPC
        # subnet ID is provided, we automatically resolve its Neutron UUID.
        if container_network_type == "eni":
            eni_net_subnet_id = eni_subnet_id or subnet_id
            # If eni_net_subnet_id looks like a VPC subnet UUID (not a Neutron one),
            # resolve the Neutron subnet UUID via the VPC API.
            neutron_id = _resolve_neutron_subnet_id(
                region, eni_net_subnet_id, access_key, secret_key, proj_id
            )
            if neutron_id:
                cluster_spec.eni_network = EniNetwork(
                    subnets=[NetworkSubnet(subnet_id=neutron_id)]
                )
            else:
                # Fallback: use the provided ID directly (may be a Neutron UUID already)
                cluster_spec.eni_network = EniNetwork(
                    subnets=[NetworkSubnet(subnet_id=eni_net_subnet_id)]
                )

        if service_network_cidr:
            cluster_spec.service_network = ServiceNetwork(i_pv4_cidr=service_network_cidr)

        cluster_body = Cluster(
            kind="Cluster",
            api_version="v3",
            metadata=cluster_metadata,
            spec=cluster_spec,
        )

        request = CreateClusterRequest(body=cluster_body)

        response = client.create_cluster(request)

        cluster_id = None
        cluster_name_result = cluster_name
        actual_version = cluster_version or "latest (API default)"
        if hasattr(response, 'metadata'):
            cluster_id = getattr(response.metadata, 'uid', None)
            cluster_name_result = getattr(response.metadata, 'name', cluster_name)
        if hasattr(response, 'spec') and hasattr(response.spec, 'version'):
            actual_version = response.spec.version

        return {
            "success": True,
            "region": region,
            "action": "create_cce_cluster",
            "cluster_id": cluster_id,
            "cluster_name": cluster_name_result,
            "cluster_version": actual_version,
            "cluster_type": cluster_type,
            "vpc_id": vpc_id,
            "subnet_id": subnet_id,
            "container_network_type": container_network_type,
            "container_network_cidr": container_network_cidr,
            "service_network_cidr": service_network_cidr,
            "flavor_id": flavor_id,
            "message": "Cluster creation request submitted successfully",
            "response": response.to_dict() if hasattr(response, 'to_dict') else str(response),
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, "request_id", None),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }