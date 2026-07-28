"""kubectl-based read-only Kubernetes access for CCE event queries."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

from . import common


_NAMESPACE_PATTERN = re.compile(r"^[a-z0-9](?:[-a-z0-9]*[a-z0-9])?$")


def _parse_json_output(output: str, source: str) -> Dict[str, Any]:
    text = (output or "").strip()
    try:
        return {"success": True, "data": json.loads(text or "{}")}
    except json.JSONDecodeError as exc:
        return {"success": False, "error": f"{source} returned non-JSON output: {exc}"}


def _run_command(cmd: List[str], env: Optional[Dict[str, str]] = None, timeout: int = 60) -> Dict[str, Any]:
    safe_cmd = common.redact_command(cmd)
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, env=env)
    except FileNotFoundError:
        return {"success": False, "error": f"{cmd[0]} not found in PATH", "command": safe_cmd}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"command timed out after {timeout}s", "command": safe_cmd}

    if proc.returncode:
        return {
            "success": False,
            "error": (proc.stderr or proc.stdout or f"command exited with code {proc.returncode}")[:2000],
            "command": safe_cmd,
            "returncode": proc.returncode,
        }

    result = _parse_json_output(proc.stdout, cmd[0])
    result["command"] = safe_cmd
    return result


def _run_hcloud(
    service: str,
    operation: str,
    region: str,
    params: Dict[str, Any],
    ak: Optional[str],
    sk: Optional[str],
    project_id: Optional[str],
) -> Dict[str, Any]:
    access_key, secret_key, resolved_project_id = common.resolve_hcloud_credentials(ak, sk, project_id)
    cmd = [
        "hcloud", service, operation, f"--cli-region={region}", "--cli-output=json",
        "--cli-connect-timeout=10", "--cli-read-timeout=60",
    ]
    if access_key:
        cmd.append(f"--cli-access-key={access_key}")
    if secret_key:
        cmd.append(f"--cli-secret-key={secret_key}")
    if resolved_project_id:
        cmd.append(f"--cli-project-id={resolved_project_id}")
    for key, value in params.items():
        if value is not None:
            cmd.append(f"--{key}={value}")
    return _run_command(cmd)


def _cluster_has_external_access(cluster: Dict[str, Any]) -> bool:
    status = cluster.get("status") or {}
    for condition in status.get("conditions", []) or []:
        if condition.get("type") == "ElasticPublicIP":
            return condition.get("status") not in {"UNBOUND", "False", "", None}
    return any(
        endpoint.get("type") == "External" and endpoint.get("url")
        for endpoint in status.get("endpoints", []) or []
    )


def _prefer_external_context(kubeconfig: Dict[str, Any]) -> None:
    external_name = next(
        (
            item.get("name") for item in kubeconfig.get("clusters", []) or []
            if "external" in item.get("name", "") and "TLS" not in item.get("name", "")
        ),
        None,
    )
    if not external_name:
        return
    for context in kubeconfig.get("contexts", []) or []:
        if (context.get("context") or {}).get("cluster") == external_name:
            kubeconfig["current-context"] = context.get("name")
            return


def _get_events_with_external_kubeconfig(
    region: str, cluster_id: str, args: List[str], ak: Optional[str], sk: Optional[str], project_id: Optional[str]
) -> Dict[str, Any]:
    cluster_result = _run_hcloud("CCE", "ShowCluster", region, {"cluster_id": cluster_id}, ak, sk, project_id)
    if not cluster_result.get("success"):
        return cluster_result
    if not _cluster_has_external_access(cluster_result.get("data") or {}):
        return {"success": False, "error": "cluster has no bound EIP/external endpoint"}

    cert_result = _run_hcloud(
        "CCE", "CreateKubernetesClusterCert", region, {"cluster_id": cluster_id, "duration": 1}, ak, sk, project_id
    )
    if not cert_result.get("success"):
        return cert_result
    kubeconfig = cert_result.get("data") or {}
    if not kubeconfig.get("clusters"):
        return {"success": False, "error": "CreateKubernetesClusterCert returned no kubeconfig clusters"}
    _prefer_external_context(kubeconfig)

    kubeconfig_file = None
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as handle:
            json.dump(kubeconfig, handle)
            kubeconfig_file = handle.name
        result = _run_command(["kubectl", "--kubeconfig", kubeconfig_file, "get", *args, "-o", "json"])
        if result.get("success"):
            result["access_method"] = "kubectl_kubeconfig_external"
        return result
    finally:
        if kubeconfig_file and os.path.exists(kubeconfig_file):
            os.remove(kubeconfig_file)


def _get_events_with_cce_plugin(
    region: str, cluster_id: str, args: List[str], ak: Optional[str], sk: Optional[str], project_id: Optional[str], security_token: Optional[str]
) -> Dict[str, Any]:
    env_ak, env_sk, env_project_id = common.get_credentials()
    access_key = ak or env_ak
    secret_key = sk or env_sk
    resolved_project_id = project_id or env_project_id
    env = os.environ.copy()
    env.update({"CCE_CLUSTER_ID": cluster_id, "CCE_REGION": region, "HW_REGION": region})
    if resolved_project_id:
        env.update({"CCE_PROJECT_ID": resolved_project_id, "HW_PROJECT_ID": resolved_project_id})
    if access_key:
        env.update({"HW_ACCESS_KEY": access_key, "HUAWEICLOUD_SDK_AK": access_key})
    if secret_key:
        env.update({"HW_SECRET_KEY": secret_key, "HUAWEICLOUD_SDK_SK": secret_key})
    if security_token:
        env.update({"HW_SECURITY_TOKEN": security_token, "HUAWEICLOUD_SECURITY_TOKEN": security_token})
    command = ["kubectl", "cce", "--cluster-id", cluster_id, "--region", region]
    if resolved_project_id:
        command.extend(["--project-id", resolved_project_id])
    command.extend(["get", *args, "-o", "json"])
    result = _run_command(command, env=env)
    if result.get("success"):
        result["access_method"] = "kubectl_cce_plugin"
    return result


def get_cce_events_with_kubectl(
    region: str,
    cluster_id: str,
    namespace: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 500,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Read Kubernetes Events through external kubeconfig, then kubectl-cce."""
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}
    if namespace and (len(namespace) > 63 or not _NAMESPACE_PATTERN.fullmatch(namespace)):
        return {
            "success": False,
            "error": "namespace must be a Kubernetes DNS label (lowercase letters, digits, and hyphens; max 63 characters)",
        }

    effective_event_type = event_type or "Warning"
    if effective_event_type not in {"Warning", "Normal", "all"}:
        return {"success": False, "error": "event_type must be Warning, Normal, or all"}

    args = ["events", "-n", namespace] if namespace else ["events", "-A"]
    if effective_event_type != "all":
        args.extend(["--field-selector", f"type={effective_event_type}"])
    external_result = _get_events_with_external_kubeconfig(region, cluster_id, args, ak, sk, project_id)
    if external_result.get("success"):
        result = external_result
    else:
        token = security_token or os.environ.get("HUAWEI_SECURITY_TOKEN") or os.environ.get("HW_SECURITY_TOKEN")
        plugin_result = _get_events_with_cce_plugin(region, cluster_id, args, ak, sk, project_id, token)
        if not plugin_result.get("success"):
            return {
                "success": False,
                "error": "failed to get Kubernetes events via external kubeconfig or kubectl cce plugin",
                "kubeconfig_error": external_result.get("error"),
                "plugin_error": plugin_result.get("error"),
            }
        result = plugin_result

    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "namespace": namespace or "all",
        "event_type": effective_event_type,
        "access_method": result.get("access_method"),
        "items": ((result.get("data") or {}).get("items") or [])[:limit],
    }


def get_cce_resource_with_kubectl(
    region: str,
    cluster_id: str,
    resource: str,
    name: str,
    namespace: Optional[str] = None,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Read one Kubernetes resource through external kubeconfig or kubectl-cce."""
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}
    if not resource or not name:
        return {"success": False, "error": "resource and name are required"}
    if namespace and (len(namespace) > 63 or not _NAMESPACE_PATTERN.fullmatch(namespace)):
        return {
            "success": False,
            "error": "namespace must be a Kubernetes DNS label (lowercase letters, digits, and hyphens; max 63 characters)",
        }

    args = [resource, name]
    if namespace:
        args.extend(["-n", namespace])
    external_result = _get_events_with_external_kubeconfig(region, cluster_id, args, ak, sk, project_id)
    if external_result.get("success"):
        result = external_result
    else:
        token = security_token or os.environ.get("HUAWEI_SECURITY_TOKEN") or os.environ.get("HW_SECURITY_TOKEN")
        plugin_result = _get_events_with_cce_plugin(region, cluster_id, args, ak, sk, project_id, token)
        if not plugin_result.get("success"):
            return {
                "success": False,
                "error": f"failed to get Kubernetes resource {resource}/{name}",
                "kubeconfig_error": external_result.get("error"),
                "plugin_error": plugin_result.get("error"),
            }
        result = plugin_result
    return {
        "success": True,
        "access_method": result.get("access_method"),
        "item": result.get("data") or {},
    }


def get_cce_logconfigs_with_cce_plugin(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Read LogConfig CRs through the kubectl-cce plugin."""
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    token = security_token or os.environ.get("HUAWEI_SECURITY_TOKEN") or os.environ.get("HW_SECURITY_TOKEN")
    result = _get_events_with_cce_plugin(
        region,
        cluster_id,
        ["logconfigs.logging.openvessel.io", "-A"],
        ak,
        sk,
        project_id,
        token,
    )
    if not result.get("success"):
        return {
            "success": False,
            "error": "failed to get LogConfigs through kubectl cce plugin",
            "plugin_error": result.get("error"),
        }
    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "access_method": result.get("access_method"),
        "items": (result.get("data") or {}).get("items") or [],
    }
