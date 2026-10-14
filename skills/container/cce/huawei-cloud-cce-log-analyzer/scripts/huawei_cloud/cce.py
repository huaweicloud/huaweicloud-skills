"""CCE helpers used by the log analyzer."""

from __future__ import annotations

from typing import Any, Dict, Optional

from . import kubectl_client


def get_pod_logs(
    region: str,
    cluster_id: str,
    pod_name: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    namespace: str = "default",
    container: Optional[str] = None,
    previous: bool = False,
    tail_lines: int = 1000,
    security_token: Optional[str] = None,
    explicit_cli_credentials: bool = False,
) -> Dict[str, Any]:
    """Read Pod stdout/stderr through kubectl or the kubectl-cce plugin."""
    result = kubectl_client.get_pod_logs(
        region, cluster_id, pod_name, namespace, container, previous, tail_lines, ak, sk, project_id,
        security_token, explicit_cli_credentials,
    )
    if not result.get("success"):
        return result
    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "action": "get_pod_logs",
        "pod_name": pod_name,
        "namespace": namespace,
        "container": container,
        "tail_lines": tail_lines,
        "previous": previous,
        "access_method": result.get("access_method"),
        "logs": result.get("logs", ""),
    }
