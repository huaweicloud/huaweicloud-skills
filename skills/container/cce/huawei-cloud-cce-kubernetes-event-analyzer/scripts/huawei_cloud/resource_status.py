"""Current-state checks for Kubernetes resources referenced by Events."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, Optional

from . import kubectl_client


_RESOURCE_MAP = {
    "pod": ("pods", True),
    "node": ("nodes", False),
    "deployment": ("deployments.apps", True),
    "statefulset": ("statefulsets.apps", True),
    "daemonset": ("daemonsets.apps", True),
    "replicaset": ("replicasets.apps", True),
    "job": ("jobs.batch", True),
    "cronjob": ("cronjobs.batch", True),
    "persistentvolumeclaim": ("persistentvolumeclaims", True),
    "persistentvolume": ("persistentvolumes", False),
    "service": ("services", True),
}


def _conditions(item: Dict[str, Any]) -> Dict[str, str]:
    return {
        str(condition.get("type")): str(condition.get("status"))
        for condition in ((item.get("status") or {}).get("conditions") or [])
        if isinstance(condition, dict) and condition.get("type")
    }


def _count(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _status(item: Dict[str, Any], kind: str) -> tuple[str, str]:
    spec = item.get("spec") or {}
    status = item.get("status") or {}
    conditions = _conditions(item)
    if kind == "pod":
        phase = status.get("phase")
        if phase == "Succeeded":
            return "normal", "Pod completed successfully"
        if phase == "Running" and conditions.get("Ready") == "True":
            return "normal", "Pod is Running and Ready"
        if phase in {"Pending", "Failed", "Unknown"} or conditions.get("Ready") == "False":
            return "abnormal", f"Pod phase is {phase or 'Unknown'}"
        return "unknown", f"Pod phase is {phase or 'Unknown'}"
    if kind == "node":
        pressure = ("MemoryPressure", "DiskPressure", "PIDPressure")
        if conditions.get("Ready") == "True" and all(conditions.get(name) != "True" for name in pressure):
            return "normal", "Node is Ready without resource pressure"
        if conditions.get("Ready") == "False":
            return "abnormal", "Node is not Ready"
        return "unknown", "Node readiness is not reported"
    if kind in {"deployment", "replicaset"}:
        desired = _count(spec.get("replicas", 1))
        available = _count(status.get("availableReplicas", status.get("readyReplicas", 0)))
        return ("normal", "All desired replicas are available") if available >= desired else (
            "abnormal", f"Available replicas {available}/{desired}"
        )
    if kind == "statefulset":
        desired = _count(spec.get("replicas", 1))
        ready = _count(status.get("readyReplicas"))
        return ("normal", "All desired replicas are Ready") if ready >= desired else (
            "abnormal", f"Ready replicas {ready}/{desired}"
        )
    if kind == "daemonset":
        desired = _count(status.get("desiredNumberScheduled"))
        ready = _count(status.get("numberReady"))
        if desired == 0:
            return "normal", "No Pods are currently scheduled"
        return ("normal", "All scheduled Pods are Ready") if ready >= desired else (
            "abnormal", f"Ready Pods {ready}/{desired}"
        )
    if kind == "job":
        if conditions.get("Complete") == "True":
            return "normal", "Job completed successfully"
        if conditions.get("Failed") == "True":
            return "abnormal", "Job has failed"
        return "unknown", "Job is still active or has no terminal condition"
    if kind == "persistentvolumeclaim":
        phase = status.get("phase")
        return ("normal", "PVC is Bound") if phase == "Bound" else ("abnormal", f"PVC phase is {phase or 'Unknown'}")
    return "unknown", "No health rule is defined for this resource kind"


def check_event_resource_statuses(
    events: Iterable[Dict[str, Any]],
    region: str,
    cluster_id: str,
    max_resources: int,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Check the current state of distinct resources referenced by Event records."""
    seen = set()
    results = []
    for event in events:
        involved = event.get("involved_object") or event.get("involvedObject") or {}
        if not isinstance(involved, dict):
            continue
        kind = str(involved.get("kind") or "")
        name = str(involved.get("name") or "")
        namespace = involved.get("namespace") or event.get("namespace")
        key = (kind.lower(), str(namespace or ""), name)
        if not kind or not name or key in seen:
            continue
        seen.add(key)
        if len(results) >= max_resources:
            break
        mapping = _RESOURCE_MAP.get(kind.lower())
        base = {"kind": kind, "name": name, "namespace": namespace}
        if not mapping:
            results.append({**base, "state": "unsupported", "message": "Resource kind is not supported for status checks"})
            continue
        resource, namespaced = mapping
        if namespaced and not namespace:
            results.append({**base, "state": "query_failed", "message": "Event does not include the resource namespace"})
            continue
        lookup = kubectl_client.get_cce_resource_with_kubectl(
            region=region,
            cluster_id=cluster_id,
            resource=resource,
            name=name,
            namespace=str(namespace) if namespaced and namespace else None,
            ak=ak,
            sk=sk,
            project_id=project_id,
            security_token=security_token,
        )
        if not lookup.get("success"):
            error = lookup.get("plugin_error") or lookup.get("error") or "resource query failed"
            state = "not_found" if "NotFound" in error or "not found" in error.lower() else "query_failed"
            results.append({**base, "state": state, "message": error[:500]})
            continue
        state, message = _status(lookup.get("item") or {}, kind.lower())
        results.append({**base, "state": state, "message": message, "access_method": lookup.get("access_method")})
    counts = Counter(item["state"] for item in results)
    return {"checked": len(results), "summary": dict(counts), "resources": results}
