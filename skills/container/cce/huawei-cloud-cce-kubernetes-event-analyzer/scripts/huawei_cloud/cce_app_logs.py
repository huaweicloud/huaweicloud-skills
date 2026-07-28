"""Read CCE Event-to-LTS LogConfig custom resources through kubectl-cce."""

from __future__ import annotations

from typing import Any, Dict, List

from . import kubectl_client


def get_cce_logconfigs_action(params: Dict[str, str]) -> Dict[str, Any]:
    """Return LogConfig resources needed to locate CCE Event LTS streams."""
    region = params.get("region")
    cluster_id = params.get("cluster_id")
    if not region:
        return {"success": False, "error": "region is required"}
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    result = kubectl_client.get_cce_logconfigs_with_cce_plugin(
        region=region,
        cluster_id=cluster_id,
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        security_token=params.get("security_token"),
    )
    if not result.get("success"):
        return result

    logconfigs: List[Dict[str, Any]] = []
    for item in result.get("items") or []:
        metadata = item.get("metadata") or {}
        spec = item.get("spec") or {}
        input_detail = spec.get("inputDetail") or {}
        output_detail = spec.get("outputDetail") or {}
        logconfigs.append(
            {
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
                "input_type": input_detail.get("type"),
                "output_type": output_detail.get("type"),
                "spec": spec,
                "api_version": item.get("apiVersion"),
            }
        )

    return {
        "success": True,
        "cluster_id": cluster_id,
        "access_method": result.get("access_method"),
        "count": len(logconfigs),
        "logconfigs": logconfigs,
    }
