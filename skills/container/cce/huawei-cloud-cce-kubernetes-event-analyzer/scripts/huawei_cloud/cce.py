"""CCE helpers used by the current Kubernetes Event query."""

from __future__ import annotations

from typing import Any, Dict, Optional

from . import kubectl_client


def get_kubernetes_events(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
    namespace: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 500,
) -> Dict[str, Any]:
    """Read and normalize CCE Events through the kubectl access strategy."""
    effective_event_type = event_type or "Warning"
    result = kubectl_client.get_cce_events_with_kubectl(
        region=region,
        cluster_id=cluster_id,
        namespace=namespace,
        event_type=effective_event_type,
        limit=limit,
        ak=ak,
        sk=sk,
        project_id=project_id,
        security_token=security_token,
    )
    if not result.get("success"):
        return result

    events = []
    for item in result.get("items") or []:
        metadata = item.get("metadata") or {}
        involved_object = item.get("involvedObject") or {}
        series = item.get("series") or {}
        events.append(
            {
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
                "type": item.get("type"),
                "reason": item.get("reason"),
                "message": item.get("message"),
                "first_timestamp": item.get("firstTimestamp") or item.get("eventTime") or metadata.get("creationTimestamp"),
                "last_timestamp": item.get("lastTimestamp") or series.get("lastObservedTime") or item.get("eventTime"),
                "count": item.get("count") or series.get("count") or 1,
                "involved_object": {
                    "kind": involved_object.get("kind"),
                    "name": involved_object.get("name"),
                    "namespace": involved_object.get("namespace"),
                }
                if involved_object
                else None,
            }
        )

    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "action": "get_cce_events",
        "namespace": namespace or "all",
        "event_type": effective_event_type,
        "access_method": result.get("access_method"),
        "count": len(events),
        "limit": limit,
        "events": events,
    }
