"""Minimal CCE helpers required by metric queries."""

from __future__ import annotations

import base64
import ssl
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .common import (
    _safe_delete_file,
    run_hcloud,
)
from . import kubectl_client


def list_cce_clusters(
    region: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """List CCE clusters via hcloud."""
    result = run_hcloud(
        "CCE",
        "ListClusters",
        region,
        {"project_id": project_id},
        ak=ak,
        sk=sk,
        project_id=project_id,
    )
    if not result.get("success"):
        return result

    clusters = []
    for cluster in (result.get("data") or {}).get("items", []) or []:
        metadata = cluster.get("metadata") or {}
        spec = cluster.get("spec") or {}
        status = cluster.get("status") or {}
        network = spec.get("network") or {}
        item = {
            "id": metadata.get("uid"),
            "name": metadata.get("name"),
            "status": status.get("phase", "Unknown"),
            "type": spec.get("type", "Unknown"),
            "version": spec.get("version", "Unknown"),
            "created_at": metadata.get("creationTimestamp") or metadata.get("creation_timestamp"),
        }
        if network:
            item["network"] = {
                "vpc_id": network.get("vpc") or network.get("vpc_id"),
                "subnet_id": network.get("subnet") or network.get("subnet_id"),
            }
        clusters.append(item)

    return {
        "success": True,
        "region": region,
        "action": "list_cce_clusters",
        "source": "hcloud",
        "count": len(clusters),
        "clusters": clusters[offset:offset + limit],
    }


def list_cce_cluster_nodes(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """List CCE cluster nodes via hcloud."""
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    result = run_hcloud(
        "CCE",
        "ListNodes",
        region,
        {"cluster_id": cluster_id, "project_id": project_id},
        ak=ak,
        sk=sk,
        project_id=project_id,
    )
    if not result.get("success"):
        return result

    nodes = []
    for node in (result.get("data") or {}).get("items", []) or []:
        metadata = node.get("metadata") or {}
        spec = node.get("spec") or {}
        status = node.get("status") or {}
        nodes.append({
            "id": metadata.get("uid"),
            "name": metadata.get("name"),
            "status": status.get("phase", "Unknown"),
            "flavor": spec.get("flavor"),
            "availability_zone": spec.get("az"),
        })

    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "action": "list_cce_cluster_nodes",
        "source": "hcloud",
        "count": len(nodes),
        "nodes": nodes[offset:offset + limit],
    }


def get_kubernetes_pods(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    namespace: Optional[str] = None,
    labels: Optional[str] = None,
) -> Dict[str, Any]:
    """List Kubernetes pods through kubectl for optional label-based metric filtering."""
    return kubectl_client.get_cce_pods_with_kubectl(
        region=region,
        cluster_id=cluster_id,
        ak=ak,
        sk=sk,
        project_id=project_id,
        namespace=namespace,
        labels=labels,
    )


def _decode_tls_certificate(pem_data: bytes) -> Dict[str, Any]:
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".crt") as handle:
            temp_file = handle.name
            handle.write(pem_data)

        cert = ssl._ssl._test_decode_cert(temp_file)
        not_after_raw = cert.get("notAfter")
        expires_at = None
        days_remaining = None
        if not_after_raw:
            expires_at = datetime.strptime(not_after_raw, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            days_remaining = int((expires_at - datetime.now(timezone.utc)).total_seconds() // 86400)

        def _flatten_name(items):
            values = []
            for item in items or []:
                for key, value in item:
                    values.append(f"{key}={value}")
            return ", ".join(values)

        return {
            "not_after": expires_at.isoformat() if expires_at else None,
            "days_remaining": days_remaining,
            "subject": _flatten_name(cert.get("subject")),
            "issuer": _flatten_name(cert.get("issuer")),
            "serial_number": cert.get("serialNumber"),
        }
    finally:
        _safe_delete_file(temp_file)


def get_ingress_tls_certificates(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    namespace: Optional[str] = None,
    warning_days: int = 30,
) -> Dict[str, Any]:
    """List Ingress TLS certificates through kubectl and calculate expiration status."""
    ingress_result = kubectl_client.get_cce_ingresses_with_kubectl(
        region=region,
        cluster_id=cluster_id,
        ak=ak,
        sk=sk,
        project_id=project_id,
        namespace=namespace,
    )
    if not ingress_result.get("success"):
        return ingress_result

    secret_hosts: Dict[tuple[str, str], set[str]] = {}
    for ingress in ingress_result.get("items", []):
        metadata = ingress.get("metadata") or {}
        ingress_namespace = metadata.get("namespace")
        for tls in ((ingress.get("spec") or {}).get("tls") or []):
            secret_name = tls.get("secretName")
            if not secret_name:
                continue
            key = (ingress_namespace, secret_name)
            secret_hosts.setdefault(key, set()).update(tls.get("hosts") or [])

    certificates: List[Dict[str, Any]] = []
    expired_count = 0
    expiring_soon_count = 0
    for (secret_namespace, secret_name), hosts in sorted(secret_hosts.items()):
        item = {
            "namespace": secret_namespace,
            "secret_name": secret_name,
            "hosts": sorted(hosts),
            "status": "unknown",
        }
        try:
            secret_result = kubectl_client.get_cce_secret_with_kubectl(
                region=region,
                cluster_id=cluster_id,
                namespace=secret_namespace,
                name=secret_name,
                ak=ak,
                sk=sk,
                project_id=project_id,
            )
            if not secret_result.get("success"):
                item["error"] = secret_result.get("error", "failed to get secret")
            else:
                crt_b64 = (((secret_result.get("secret") or {}).get("data") or {}).get("tls.crt"))
                if not crt_b64:
                    item["error"] = "tls.crt not found in secret"
                else:
                    cert_info = _decode_tls_certificate(base64.b64decode(crt_b64))
                    item.update(cert_info)
                    days_remaining = cert_info.get("days_remaining")
                    if days_remaining is None:
                        item["status"] = "unknown"
                    elif days_remaining < 0:
                        item["status"] = "expired"
                        expired_count += 1
                    elif days_remaining <= warning_days:
                        item["status"] = "expiring_soon"
                        expiring_soon_count += 1
                    else:
                        item["status"] = "valid"
        except Exception as exc:
            item["error"] = str(exc)
            item["error_type"] = type(exc).__name__
        certificates.append(item)

    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "action": "get_ingress_tls_certificates",
        "source": ingress_result.get("source", "kubectl"),
        "namespace": namespace or "all",
        "warning_days": warning_days,
        "total_tls_secrets": len(certificates),
        "expired_count": expired_count,
        "expiring_soon_count": expiring_soon_count,
        "certificates": certificates,
    }
