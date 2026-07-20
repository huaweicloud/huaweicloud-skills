"""kubectl-based Kubernetes data access helpers for CCE clusters."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

from .common import get_credentials, get_security_token, run_hcloud


def _run_json_command(cmd: List[str], env: Optional[Dict[str, str]] = None, timeout: int = 60) -> Dict[str, Any]:
    safe_cmd = [part if "token" not in part.lower() else "***" for part in cmd]
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, env=env)
    except FileNotFoundError:
        return {"success": False, "error": f"{cmd[0]} not found in PATH", "command": safe_cmd}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"command timed out after {timeout}s", "command": safe_cmd}

    if proc.returncode != 0:
        return {
            "success": False,
            "error": (proc.stderr or proc.stdout or f"command exited with code {proc.returncode}")[:2000],
            "command": safe_cmd,
            "returncode": proc.returncode,
        }

    try:
        return {"success": True, "data": json.loads(proc.stdout or "{}"), "command": safe_cmd}
    except json.JSONDecodeError as exc:
        return {"success": False, "error": f"kubectl returned non-JSON output: {exc}", "command": safe_cmd}


def _cluster_has_external_access(cluster: Dict[str, Any]) -> bool:
    status = cluster.get("status") or {}
    for condition in status.get("conditions", []) or []:
        if condition.get("type") == "ElasticPublicIP":
            return condition.get("status") not in {"UNBOUND", "False", "", None}
    for endpoint in status.get("endpoints", []) or []:
        if endpoint.get("type") == "External" and endpoint.get("url"):
            return True
    return False


def _show_cluster(region: str, cluster_id: str, ak: Optional[str], sk: Optional[str], project_id: Optional[str]) -> Dict[str, Any]:
    result = run_hcloud(
        "CCE",
        "ShowCluster",
        region,
        {"cluster_id": cluster_id, "project_id": project_id},
        ak=ak,
        sk=sk,
        project_id=project_id,
    )
    if not result.get("success"):
        return result
    return {"success": True, "cluster": result.get("data") or {}}


def _create_kubeconfig(region: str, cluster_id: str, ak: Optional[str], sk: Optional[str], project_id: Optional[str]) -> Dict[str, Any]:
    result = run_hcloud(
        "CCE",
        "CreateKubernetesClusterCert",
        region,
        {"cluster_id": cluster_id, "duration": 1, "project_id": project_id},
        ak=ak,
        sk=sk,
        project_id=project_id,
    )
    if not result.get("success"):
        return result
    kubeconfig = result.get("data") or {}
    if not kubeconfig.get("clusters"):
        return {"success": False, "error": "CreateKubernetesClusterCert returned no kubeconfig clusters"}
    _prefer_external_context(kubeconfig)
    return {"success": True, "kubeconfig": kubeconfig}


def _prefer_external_context(kubeconfig: Dict[str, Any]) -> None:
    external_cluster_name = None
    for cluster in kubeconfig.get("clusters", []) or []:
        name = cluster.get("name", "")
        if "external" in name and "TLS" not in name:
            external_cluster_name = name
            break
    if not external_cluster_name:
        return
    for context in kubeconfig.get("contexts", []) or []:
        context_data = context.get("context") or {}
        if context_data.get("cluster") == external_cluster_name:
            kubeconfig["current-context"] = context.get("name")
            return


def _kubectl_get_with_kubeconfig(region: str, cluster_id: str, resource_args: List[str], ak: Optional[str], sk: Optional[str], project_id: Optional[str]) -> Dict[str, Any]:
    cluster_result = _show_cluster(region, cluster_id, ak, sk, project_id)
    if not cluster_result.get("success"):
        return cluster_result
    if not _cluster_has_external_access(cluster_result.get("cluster") or {}):
        return {"success": False, "error": "cluster has no bound EIP/external endpoint"}

    kubeconfig_result = _create_kubeconfig(region, cluster_id, ak, sk, project_id)
    if not kubeconfig_result.get("success"):
        return kubeconfig_result

    kubeconfig_file = None
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as handle:
            json.dump(kubeconfig_result["kubeconfig"], handle)
            kubeconfig_file = handle.name
        result = _run_json_command(["kubectl", "--kubeconfig", kubeconfig_file, "get", *resource_args, "-o", "json"])
        if result.get("success"):
            result["access_method"] = "kubectl_kubeconfig_external"
        return result
    finally:
        if kubeconfig_file and os.path.exists(kubeconfig_file):
            os.remove(kubeconfig_file)


def _kubectl_get_with_cce_plugin(region: str, cluster_id: str, resource_args: List[str], ak: Optional[str], sk: Optional[str], project_id: Optional[str], security_token: Optional[str]) -> Dict[str, Any]:
    access_key = ak or os.environ.get("HUAWEI_AK") or os.environ.get("HUAWEICLOUD_SDK_AK") or os.environ.get("HW_ACCESS_KEY")
    secret_key = sk or os.environ.get("HUAWEI_SK") or os.environ.get("HUAWEICLOUD_SDK_SK") or os.environ.get("HW_SECRET_KEY")
    proj_id = project_id or os.environ.get("HUAWEI_PROJECT_ID") or os.environ.get("HUAWEICLOUD_SDK_PROJECT_ID") or os.environ.get("HW_PROJECT_ID")
    env = os.environ.copy()
    env["CCE_CLUSTER_ID"] = cluster_id
    env["CCE_REGION"] = region
    env["HW_REGION"] = region
    if proj_id:
        env["CCE_PROJECT_ID"] = proj_id
        env["HW_PROJECT_ID"] = proj_id
    if access_key:
        env["HW_ACCESS_KEY"] = access_key
        env["HUAWEICLOUD_SDK_AK"] = access_key
    if secret_key:
        env["HW_SECRET_KEY"] = secret_key
        env["HUAWEICLOUD_SDK_SK"] = secret_key
    sec_token = get_security_token(security_token)
    if sec_token:
        env["HW_SECURITY_TOKEN"] = sec_token
        env["HUAWEICLOUD_SECURITY_TOKEN"] = sec_token

    result = _run_json_command(["kubectl", "cce", "--cluster-id", cluster_id, "--region", region, "get", *resource_args, "-o", "json"], env=env)
    if result.get("success"):
        result["access_method"] = "kubectl_cce_plugin"
    return result


def _kubectl_get_resource(
    region: str,
    cluster_id: str,
    resource_args: List[str],
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    profile_ak, profile_sk, profile_project = get_credentials(ak, sk, project_id)
    kubeconfig_result = _kubectl_get_with_kubeconfig(region, cluster_id, resource_args, profile_ak, profile_sk, profile_project)
    if kubeconfig_result.get("success"):
        return kubeconfig_result

    plugin_result = _kubectl_get_with_cce_plugin(region, cluster_id, resource_args, ak, sk, project_id, security_token)
    if plugin_result.get("success"):
        return plugin_result

    return {
        "success": False,
        "error": "failed to get Kubernetes resources via kubectl kubeconfig or kubectl cce plugin",
        "kubeconfig_error": kubeconfig_result.get("error"),
        "plugin_error": plugin_result.get("error"),
    }


def get_cce_services_with_kubectl(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    namespace: Optional[str] = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List Kubernetes Services using kubectl, preferring external kubeconfig access."""
    args = ["svc"]
    args.extend(["-n", namespace] if namespace else ["-A"])
    result = _kubectl_get_resource(region, cluster_id, args, ak, sk, project_id, security_token)
    if not result.get("success"):
        return result
    return _normalize_services(result, region, cluster_id, namespace)


def get_cce_pods_with_kubectl(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    namespace: Optional[str] = None,
    labels: Optional[str] = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    args = ["pods"]
    args.extend(["-n", namespace] if namespace else ["-A"])
    if labels:
        args.extend(["-l", labels])
    result = _kubectl_get_resource(region, cluster_id, args, ak, sk, project_id, security_token)
    if not result.get("success"):
        return result
    return _normalize_pods(result, region, cluster_id, namespace)


def get_cce_ingresses_with_kubectl(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    namespace: Optional[str] = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    args = ["ingress"]
    args.extend(["-n", namespace] if namespace else ["-A"])
    result = _kubectl_get_resource(region, cluster_id, args, ak, sk, project_id, security_token)
    if not result.get("success"):
        return result
    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "action": "get_cce_ingresses_with_kubectl",
        "source": result.get("access_method", "kubectl"),
        "items": (result.get("data") or {}).get("items", []),
    }


def get_cce_secret_with_kubectl(
    region: str,
    cluster_id: str,
    namespace: str,
    name: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    result = _kubectl_get_resource(region, cluster_id, ["secret", name, "-n", namespace], ak, sk, project_id, security_token)
    if not result.get("success"):
        return result
    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "namespace": namespace,
        "name": name,
        "source": result.get("access_method", "kubectl"),
        "secret": result.get("data") or {},
    }


def _normalize_services(result: Dict[str, Any], region: str, cluster_id: str, namespace: Optional[str]) -> Dict[str, Any]:
    services = []
    for svc in (result.get("data") or {}).get("items", []) or []:
        metadata = svc.get("metadata") or {}
        spec = svc.get("spec") or {}
        status = svc.get("status") or {}
        ingress = ((status.get("loadBalancer") or {}).get("ingress") or [])
        services.append({
            "name": metadata.get("name"),
            "namespace": metadata.get("namespace"),
            "type": spec.get("type"),
            "cluster_ip": spec.get("clusterIP"),
            "external_ips": spec.get("externalIPs") or [],
            "load_balancer_ip": spec.get("loadBalancerIP"),
            "load_balancer_ingress": [
                {"ip": item.get("ip"), "hostname": item.get("hostname")}
                for item in ingress
            ],
        })

    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "action": "get_cce_services_with_kubectl",
        "source": result.get("access_method", "kubectl"),
        "namespace": namespace or "all",
        "count": len(services),
        "services": services,
    }


def _normalize_pods(result: Dict[str, Any], region: str, cluster_id: str, namespace: Optional[str]) -> Dict[str, Any]:
    pods = []
    for pod in (result.get("data") or {}).get("items", []) or []:
        metadata = pod.get("metadata") or {}
        spec = pod.get("spec") or {}
        status = pod.get("status") or {}
        pods.append({
            "name": metadata.get("name"),
            "namespace": metadata.get("namespace"),
            "status": status.get("phase"),
            "node": spec.get("nodeName"),
            "ip": status.get("podIP"),
            "created": metadata.get("creationTimestamp"),
            "labels": metadata.get("labels") or {},
        })

    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "action": "get_kubernetes_pods",
        "source": result.get("access_method", "kubectl"),
        "namespace": namespace or "all",
        "count": len(pods),
        "pods": pods,
    }
