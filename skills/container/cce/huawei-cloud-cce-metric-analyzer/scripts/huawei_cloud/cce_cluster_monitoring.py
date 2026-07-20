"""
CCE Cluster Monitoring Aggregation Tool

Aggregates monitoring data from CCE cluster including:
- Pod metrics (CPU, memory TopN)
- Node metrics (CPU, memory, disk TopN)
- ELB metrics (associated with LoadBalancer services)
- NAT Gateway metrics
- EIP metrics (associated with ELB and NAT gateways)

Anomaly detection using uniform 80% threshold for all metrics.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

try:
    from . import cce, cce_metrics, kubectl_client, elb, network
    from .common import get_credentials, get_credentials_with_region, get_security_token
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False
    cce = None
    cce_metrics = None
    kubectl_client = None
    elb = None
    network = None
    get_credentials = None
    get_credentials_with_region = None
    get_security_token = None


ANOMALY_THRESHOLD = 80.0


def _time_str_to_hours(start_time: str, end_time: str) -> int:
    """Calculate hours between two time strings."""
    try:
        start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        delta = end_dt - start_dt
        hours = int(delta.total_seconds() / 3600)
        return max(1, min(hours, 24))
    except:
        return 1


def _parse_percentage_value(value: Any, default: float = 0.0) -> float:
    """Parse percentage value from various formats."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except:
            return default
    return default


def _check_anomaly(value: float, threshold: float = ANOMALY_THRESHOLD) -> bool:
    """Check if value exceeds threshold."""
    return value > threshold


def _is_usage_metric(metric_name: str, metric_data: Dict[str, Any]) -> bool:
    """Only percentage/ratio metrics should be compared with the 80% threshold."""
    unit = str(metric_data.get("unit") or "")
    name = str(metric_data.get("name_cn") or metric_name)
    return unit == "%" or "usage" in metric_name or "ratio" in metric_name or "使用率" in name


def _strip_time_series(value: Any) -> Any:
    """Remove verbose time-series arrays from nested component outputs."""
    if isinstance(value, dict):
        return {key: _strip_time_series(val) for key, val in value.items() if key != "time_series"}
    if isinstance(value, list):
        return [_strip_time_series(item) for item in value]
    return value


def _component_summary(name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Return compact component metric output and anomaly classification."""
    if not data.get("success"):
        return {
            "name": name,
            "success": False,
            "status": "unknown",
            "error": data.get("error", "query failed"),
        }
    summary = _strip_time_series(data.get("summary", {}))
    status = summary.get("status", "unknown")
    return {
        "name": name,
        "success": True,
        "status": status,
        "summary": summary,
        "metrics": _strip_time_series(data.get("metrics", {})),
    }


def _get_cluster_network(region: str, cluster_id: str, ak: Optional[str], sk: Optional[str], project_id: Optional[str]) -> Dict[str, Any]:
    """Resolve cluster network identifiers used to narrow cloud-resource scope."""
    detail_result = cce.run_hcloud(
        "CCE",
        "ShowCluster",
        region,
        {"cluster_id": cluster_id, "project_id": project_id},
        ak=ak,
        sk=sk,
        project_id=project_id,
    )
    if detail_result.get("success"):
        cluster = (detail_result.get("data") or {}).get("cluster") or detail_result.get("data") or {}
        spec = cluster.get("spec") or {}
        host_network = spec.get("hostNetwork") or spec.get("host_network") or spec.get("network") or {}
        eni_network = spec.get("eniNetwork") or spec.get("eni_network") or {}
        if host_network or eni_network:
            return {
                "vpc_id": host_network.get("vpc") or host_network.get("vpc_id"),
                "subnet_id": host_network.get("subnet") or host_network.get("subnet_id"),
                "eni_subnet_id": eni_network.get("eniSubnetId") or eni_network.get("eni_subnet_id"),
            }

    result = cce.list_cce_clusters(region, ak=ak, sk=sk, project_id=project_id)
    if not result.get("success"):
        return {}
    for cluster in result.get("clusters", []):
        if cluster.get("id") == cluster_id:
            return cluster.get("network") or {}
    return {}


def _get_pod_metrics(region: str, cluster_id: str, hours: int, namespace: str, top_n: int, ak: str, sk: str, project_id: str, security_token: Optional[str] = None) -> Dict[str, Any]:
    """Get Pod metrics with anomaly detection."""
    result = cce_metrics.get_cce_pod_metrics_topN(
        region=region,
        cluster_id=cluster_id,
        ak=ak,
        sk=sk,
        project_id=project_id,
        namespace=namespace,
        top_n=top_n,
        hours=hours,
        security_token=security_token
    )

    if not result.get("success"):
        return {"error": result.get("error", "Failed to get pod metrics"), "items": []}

    items = []
    anomalies = []

    cpu_top = result.get("metrics", {}).get("cpu_top_n", [])
    memory_top = result.get("metrics", {}).get("memory_top_n", [])
    disk_top = result.get("metrics", {}).get("disk_top_n", [])

    cpu_dict = {item.get("pod"): item.get("cpu_usage_percent") for item in cpu_top}
    memory_dict = {item.get("pod"): item.get("memory_usage_percent") for item in memory_top}
    disk_dict = {item.get("pod"): item.get("disk_usage_percent") for item in disk_top}

    all_pods = result.get("metrics", {}).get("all_pods", [])
    seen_pods = set()

    for item in cpu_top:
        pod_name = item.get("pod")
        namespace_val = item.get("namespace", namespace or "default")
        cpu_val = _parse_percentage_value(item.get("cpu_usage_percent"))
        memory_val = _parse_percentage_value(memory_dict.get(pod_name, 0))
        disk_val = _parse_percentage_value(disk_dict.get(pod_name, 0))

        reasons = []
        if _check_anomaly(cpu_val):
            reasons.append(f"cpu_usage_percent > {ANOMALY_THRESHOLD}%")
        if _check_anomaly(memory_val):
            reasons.append(f"memory_usage_percent > {ANOMALY_THRESHOLD}%")
        if _check_anomaly(disk_val):
            reasons.append(f"disk_usage_percent > {ANOMALY_THRESHOLD}%")

        status = "warning" if reasons else "normal"

        items.append({
            "namespace": namespace_val,
            "pod": pod_name,
            "cpu_usage_percent": round(cpu_val, 2),
            "memory_usage_percent": round(memory_val, 2),
            "disk_usage_percent": round(disk_val, 2),
            "status": status,
            "reason": "; ".join(reasons) if reasons else None
        })

        if reasons:
            anomalies.append({
                "type": "pod",
                "name": pod_name,
                "namespace": namespace_val,
                "metrics": {"cpu_usage_percent": round(cpu_val, 2), "memory_usage_percent": round(memory_val, 2), "disk_usage_percent": round(disk_val, 2)}
            })

        seen_pods.add(f"{namespace_val}/{pod_name}")

    for item in memory_top:
        pod_name = item.get("pod")
        namespace_val = item.get("namespace", namespace or "default")
        key = f"{namespace_val}/{pod_name}"

        if key not in seen_pods:
            memory_val = _parse_percentage_value(item.get("memory_usage_percent"))
            disk_val = _parse_percentage_value(disk_dict.get(pod_name, 0))
            reasons = []
            if _check_anomaly(memory_val):
                reasons.append(f"memory_usage_percent > {ANOMALY_THRESHOLD}%")
            if _check_anomaly(disk_val):
                reasons.append(f"disk_usage_percent > {ANOMALY_THRESHOLD}%")

            status = "warning" if reasons else "normal"

            items.append({
                "namespace": namespace_val,
                "pod": pod_name,
                "cpu_usage_percent": round(_parse_percentage_value(cpu_dict.get(pod_name, 0)), 2),
                "memory_usage_percent": round(memory_val, 2),
                "disk_usage_percent": round(disk_val, 2),
                "status": status,
                "reason": "; ".join(reasons) if reasons else None
            })

            if reasons:
                anomalies.append({
                    "type": "pod",
                    "name": pod_name,
                    "namespace": namespace_val,
                    "metrics": {"memory_usage_percent": round(memory_val, 2), "disk_usage_percent": round(disk_val, 2)}
                })

            seen_pods.add(key)

    for item in disk_top:
        pod_name = item.get("pod")
        namespace_val = item.get("namespace", namespace or "default")
        key = f"{namespace_val}/{pod_name}"

        if key not in seen_pods:
            disk_val = _parse_percentage_value(item.get("disk_usage_percent"))
            reasons = []
            if _check_anomaly(disk_val):
                reasons.append(f"disk_usage_percent > {ANOMALY_THRESHOLD}%")

            status = "warning" if reasons else "normal"

            items.append({
                "namespace": namespace_val,
                "pod": pod_name,
                "cpu_usage_percent": round(_parse_percentage_value(cpu_dict.get(pod_name, 0)), 2),
                "memory_usage_percent": round(_parse_percentage_value(memory_dict.get(pod_name, 0)), 2),
                "disk_usage_percent": round(disk_val, 2),
                "status": status,
                "reason": "; ".join(reasons) if reasons else None
            })

            if reasons:
                anomalies.append({
                    "type": "pod",
                    "name": pod_name,
                    "namespace": namespace_val,
                    "metrics": {"disk_usage_percent": round(disk_val, 2)}
                })

    return {"items": items, "anomalies": anomalies}


def _get_node_metrics(region: str, cluster_id: str, hours: int, top_n: int, ak: str, sk: str, project_id: str, security_token: Optional[str] = None) -> Dict[str, Any]:
    """Get Node metrics with anomaly detection."""
    result = cce_metrics.get_cce_node_metrics_topN(
        region=region,
        cluster_id=cluster_id,
        ak=ak,
        sk=sk,
        project_id=project_id,
        top_n=top_n,
        hours=hours,
        security_token=security_token
    )

    if not result.get("success"):
        return {"error": result.get("error", "Failed to get node metrics"), "items": []}

    items = []
    anomalies = []

    cpu_top = result.get("metrics", {}).get("cpu_top_n", [])
    memory_top = result.get("metrics", {}).get("memory_top_n", [])
    disk_top = result.get("metrics", {}).get("disk_top_n", [])

    cpu_dict = {item.get("node_ip"): item.get("cpu_usage_percent") for item in cpu_top}
    memory_dict = {item.get("node_ip"): item.get("memory_usage_percent") for item in memory_top}
    disk_dict = {item.get("node_ip"): item.get("disk_usage_percent") for item in disk_top}

    all_nodes = result.get("metrics", {}).get("all_nodes", [])
    seen_nodes = set()

    for item in cpu_top:
        node_ip = item.get("node_ip")
        cpu_val = _parse_percentage_value(item.get("cpu_usage_percent"))
        memory_val = _parse_percentage_value(memory_dict.get(node_ip, 0))
        disk_val = _parse_percentage_value(disk_dict.get(node_ip, 0))

        reasons = []
        if _check_anomaly(cpu_val):
            reasons.append(f"cpu_usage_percent > {ANOMALY_THRESHOLD}%")
        if _check_anomaly(memory_val):
            reasons.append(f"memory_usage_percent > {ANOMALY_THRESHOLD}%")
        if _check_anomaly(disk_val):
            reasons.append(f"disk_usage_percent > {ANOMALY_THRESHOLD}%")

        status = "warning" if reasons else "normal"

        items.append({
            "node_ip": node_ip,
            "node_name": item.get("node_name", node_ip),
            "cpu_usage_percent": round(cpu_val, 2),
            "memory_usage_percent": round(memory_val, 2),
            "disk_usage_percent": round(disk_val, 2),
            "status": status,
            "reason": "; ".join(reasons) if reasons else None
        })

        if reasons:
            anomalies.append({
                "type": "node",
                "name": node_ip,
                "metrics": {
                    "cpu_usage_percent": round(cpu_val, 2),
                    "memory_usage_percent": round(memory_val, 2),
                    "disk_usage_percent": round(disk_val, 2)
                }
            })

        seen_nodes.add(node_ip)

    for item in memory_top:
        node_ip = item.get("node_ip")
        if node_ip not in seen_nodes:
            memory_val = _parse_percentage_value(item.get("memory_usage_percent"))
            cpu_val = _parse_percentage_value(cpu_dict.get(node_ip, 0))
            disk_val = _parse_percentage_value(disk_dict.get(node_ip, 0))

            reasons = []
            if _check_anomaly(cpu_val):
                reasons.append(f"cpu_usage_percent > {ANOMALY_THRESHOLD}%")
            if _check_anomaly(memory_val):
                reasons.append(f"memory_usage_percent > {ANOMALY_THRESHOLD}%")
            if _check_anomaly(disk_val):
                reasons.append(f"disk_usage_percent > {ANOMALY_THRESHOLD}%")

            status = "warning" if reasons else "normal"

            items.append({
                "node_ip": node_ip,
                "node_name": item.get("node_name", node_ip),
                "cpu_usage_percent": round(cpu_val, 2),
                "memory_usage_percent": round(memory_val, 2),
                "disk_usage_percent": round(disk_val, 2),
                "status": status,
                "reason": "; ".join(reasons) if reasons else None
            })

            if reasons:
                anomalies.append({
                    "type": "node",
                    "name": node_ip,
                    "metrics": {"memory_usage_percent": round(memory_val, 2)}
                })

    return {"items": items, "anomalies": anomalies}


def _get_elb_metrics(region: str, hours: int, ak: str, sk: str, project_id: str, lb_services: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Get ELB metrics for load balancers associated with current cluster services."""
    lb_result = elb.list_elb_loadbalancers(region=region, ak=ak, sk=sk, project_id=project_id)

    if not lb_result.get("success"):
        return []

    service_ips = {
        svc.get("load_balancer_ip")
        for svc in (lb_services or [])
        if svc.get("load_balancer_ip")
    }
    if not service_ips:
        return []

    items = []
    for lb in lb_result.get("loadbalancers", []):
        elb_id = lb.get("id")
        elb_name = lb.get("name", elb_id)
        vip = lb.get("vip_address", "")
        eip = lb.get("eip_address", "")
        if service_ips and vip not in service_ips and eip not in service_ips:
            continue

        metrics_result = elb.get_elb_metrics(
            region=region,
            elb_id=elb_id,
            hours=hours,
            ak=ak,
            sk=sk,
            project_id=project_id
        )

        if not metrics_result.get("success"):
            items.append({
                "elb_id": elb_id,
                "elb_name": elb_name,
                "vip_address": vip,
                "eip": eip,
                "status": "unknown",
                "error": metrics_result.get("error"),
                "metrics": {}
            })
            continue

        metrics = metrics_result.get("metrics", {})
        anomalies = []

        for metric_name, metric_data in metrics.items():
            latest = metric_data.get("latest_value")
            if latest is not None and _is_usage_metric(metric_name, metric_data):
                val = _parse_percentage_value(latest)
                if _check_anomaly(val):
                    anomalies.append(f"{metric_data.get('name_cn', metric_name)} = {val}%")

        status = "warning" if anomalies else "normal"

        parsed_metrics = {}
        for metric_name, metric_data in metrics.items():
            latest = metric_data.get("latest_value")
            if latest is not None:
                parsed_metrics[metric_name] = round(_parse_percentage_value(latest), 2)

        items.append({
            "elb_id": elb_id,
            "elb_name": elb_name,
            "vip_address": vip,
            "eip": eip,
            "status": status,
            "reason": "; ".join(anomalies) if anomalies else None,
            "metrics": parsed_metrics
        })

    return items


def _get_nat_gateway_metrics(region: str, hours: int, ak: str, sk: str, project_id: str, cluster_network: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Get NAT Gateway metrics scoped to the cluster VPC when it can be resolved."""
    nat_result = network.list_nat_gateways(region=region, ak=ak, sk=sk, project_id=project_id)

    if not nat_result.get("success"):
        return []

    cluster_vpc_id = (cluster_network or {}).get("vpc_id")
    if not cluster_vpc_id:
        return []

    items = []
    for nat in nat_result.get("nat_gateways", []):
        nat_id = nat.get("id")
        nat_name = nat.get("name", nat_id)
        if cluster_vpc_id and nat.get("router_id") != cluster_vpc_id:
            continue

        metrics_result = network.get_nat_gateway_metrics(
            region=region,
            nat_gateway_id=nat_id,
            hours=hours,
            ak=ak,
            sk=sk,
            project_id=project_id
        )

        if not metrics_result.get("success"):
            items.append({
                "nat_id": nat_id,
                "nat_name": nat_name,
                "status": "unknown",
                "error": metrics_result.get("error"),
                "metrics": {}
            })
            continue

        metrics = metrics_result.get("metrics", {})
        anomalies = []

        for metric_name, metric_data in metrics.items():
            latest = metric_data.get("latest_value")
            if latest is not None and _is_usage_metric(metric_name, metric_data):
                val = _parse_percentage_value(latest)
                if _check_anomaly(val):
                    anomalies.append(f"{metric_data.get('name_cn', metric_name)} = {val}%")

        status = "warning" if anomalies else "normal"

        parsed_metrics = {}
        for metric_name, metric_data in metrics.items():
            latest = metric_data.get("latest_value")
            if latest is not None:
                parsed_metrics[metric_name] = round(_parse_percentage_value(latest), 2)

        items.append({
            "nat_id": nat_id,
            "nat_name": nat_name,
            "router_id": nat.get("router_id"),
            "status": status,
            "reason": "; ".join(anomalies) if anomalies else None,
            "metrics": parsed_metrics
        })

    return items


def _get_eip_metrics(region: str, hours: int, ak: str, sk: str, project_id: str, elb_metrics: Optional[List[Dict[str, Any]]] = None, nat_metrics: Optional[List[Dict[str, Any]]] = None, lb_services: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Get EIP metrics only for EIPs associated with current cluster ELB/NAT resources."""
    eip_result = network.list_eip_addresses(region=region, ak=ak, sk=sk, project_id=project_id)

    if not eip_result.get("success"):
        return []

    associated_ips = {
        item.get("eip")
        for item in (elb_metrics or [])
        if item.get("eip")
    }
    associated_ips.update(
        svc.get("load_balancer_ip")
        for svc in (lb_services or [])
        if svc.get("load_balancer_ip")
    )
    associated_instance_ids = {
        item.get("elb_id")
        for item in (elb_metrics or [])
        if item.get("elb_id")
    }
    associated_instance_ids.update(
        item.get("nat_id")
        for item in (nat_metrics or [])
        if item.get("nat_id")
    )
    if not associated_ips and not associated_instance_ids:
        return []

    items = []
    for eip in eip_result.get("eips", []):
        eip_id = eip.get("id")
        ip_address = eip.get("ip_address", "")
        instance_type = eip.get("instance_type", "")
        instance_id = eip.get("instance_id", "")
        bandwidth_size = eip.get("bandwidth_size", 0)
        if ip_address not in associated_ips and instance_id not in associated_instance_ids:
            continue

        metrics_result = network.get_eip_metrics(
            region=region,
            eip_id=eip_id,
            hours=hours,
            ak=ak,
            sk=sk,
            project_id=project_id
        )

        if not metrics_result.get("success"):
            items.append({
                "eip_id": eip_id,
                "ip_address": ip_address,
                "status": "unknown",
                "error": metrics_result.get("error"),
                "metrics": {}
            })
            continue

        metrics = metrics_result.get("metrics", {})
        anomalies = []

        for metric_name, metric_data in metrics.items():
            latest = metric_data.get("latest_value")
            if latest is not None and _is_usage_metric(metric_name, metric_data):
                val = _parse_percentage_value(latest)
                if _check_anomaly(val):
                    anomalies.append(f"{metric_data.get('name_cn', metric_name)} = {val}%")

        status = "warning" if anomalies else "normal"

        parsed_metrics = {}
        for metric_name, metric_data in metrics.items():
            latest = metric_data.get("latest_value")
            if latest is not None:
                parsed_metrics[metric_name] = round(_parse_percentage_value(latest), 2)

        linked_to = "unknown"
        if instance_type == "NATGW":
            linked_to = "nat_gateway"
        elif instance_type == "ELB" or instance_id:
            linked_to = "elb"

        items.append({
            "eip_id": eip_id,
            "ip_address": ip_address,
            "bandwidth_size_mbps": bandwidth_size,
            "status": status,
            "reason": "; ".join(anomalies) if anomalies else None,
            "linked_to": linked_to,
            "linked_resource_id": instance_id,
            "metrics": parsed_metrics
        })

    return items


def _get_loadbalancer_services(region: str, cluster_id: str, ak: str, sk: str, project_id: str, security_token: Optional[str] = None) -> Dict[str, Any]:
    """Get LoadBalancer type services in the cluster via kubectl."""
    result = kubectl_client.get_cce_services_with_kubectl(
        region=region,
        cluster_id=cluster_id,
        ak=ak,
        sk=sk,
        project_id=project_id,
        security_token=security_token,
    )
    if not result.get("success"):
        return result

    services = []
    for svc in result.get("services", []):
        if svc.get("type") == "LoadBalancer":
            lb_ip = svc.get("load_balancer_ip", "")
            lb_ingress = svc.get("load_balancer_ingress", [])
            if not lb_ip and lb_ingress:
                lb_ip = lb_ingress[0].get("ip", "") if lb_ingress else ""

            services.append({
                "name": svc.get("name"),
                "namespace": svc.get("namespace"),
                "load_balancer_ip": lb_ip,
                "source": result.get("source", "kubectl"),
            })

    return {"success": True, "services": services, "source": result.get("source", "kubectl")}


def _correlate_elb_with_services(elb_metrics: List[Dict], lb_services: List[Dict]) -> List[Dict]:
    """Correlate ELB metrics with LoadBalancer services via EIP."""
    eip_to_service = {svc.get("load_balancer_ip"): svc for svc in lb_services}

    for elb_item in elb_metrics:
        eip = elb_item.get("eip", "")
        service = eip_to_service.get(eip, {})
        elb_item["associated_service"] = service.get("name", "")
        elb_item["service_namespace"] = service.get("namespace", "")

    return elb_metrics


def analyze_cce_cluster_monitoring(
    region: str,
    cluster_id: str,
    start_time: str,
    end_time: str,
    namespace: Optional[str] = None,
    top_n: int = 10,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Aggregate monitoring data for a CCE cluster.

    Args:
        region: Huawei Cloud region
        cluster_id: CCE cluster ID
        start_time: Start time 'YYYY-MM-DD HH:MM:SS'
        end_time: End time 'YYYY-MM-DD HH:MM:SS'
        namespace: Kubernetes namespace filter (optional)
        top_n: Number of top items to return (default 10)
        ak: Access key (optional)
        sk: Secret key (optional)
        project_id: Project ID (optional)

    Returns:
        Aggregated monitoring data with anomalies
    """
    if not _AVAILABLE:
        return {
            "success": False,
            "error": "Required modules not available"
        }

    hours = _time_str_to_hours(start_time, end_time)
    access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)
    hcloud_ak, hcloud_sk, hcloud_project_id = get_credentials(ak, sk, project_id)
    sec_token = get_security_token(security_token)

    pod_data = _get_pod_metrics(region, cluster_id, hours, namespace, top_n, access_key, secret_key, proj_id, sec_token)
    node_data = _get_node_metrics(region, cluster_id, hours, top_n, access_key, secret_key, proj_id, sec_token)
    coredns_data = cce_metrics.get_cce_coredns_metrics(
        region, cluster_id, access_key, secret_key, proj_id, hours=hours, security_token=sec_token
    )
    nginx_ingress_data = cce_metrics.get_cce_nginx_ingress_metrics(
        region, cluster_id, access_key, secret_key, proj_id, hours=hours, security_token=sec_token
    )
    autoscaler_data = cce_metrics.get_cce_autoscaler_metrics(
        region, cluster_id, access_key, secret_key, proj_id, hours=hours, security_token=sec_token
    )
    cluster_network = _get_cluster_network(region, cluster_id, hcloud_ak, hcloud_sk, hcloud_project_id)
    lb_services_result = _get_loadbalancer_services(region, cluster_id, access_key, secret_key, proj_id, sec_token)
    if not lb_services_result.get("success"):
        return {
            "success": False,
            "error": "failed to get Kubernetes LoadBalancer Services for ELB/EIP association",
            "details": lb_services_result,
            "cluster_id": cluster_id,
            "region": region,
        }
    lb_services = lb_services_result.get("services", [])
    elb_data = _get_elb_metrics(region, hours, hcloud_ak, hcloud_sk, hcloud_project_id, lb_services)
    nat_data = _get_nat_gateway_metrics(region, hours, hcloud_ak, hcloud_sk, hcloud_project_id, cluster_network)
    eip_data = _get_eip_metrics(region, hours, hcloud_ak, hcloud_sk, hcloud_project_id, elb_data, nat_data, lb_services)

    elb_data = _correlate_elb_with_services(elb_data, lb_services)
    component_metrics = {
        "coredns": _component_summary("coredns", coredns_data),
        "nginx_ingress": _component_summary("nginx_ingress", nginx_ingress_data),
        "autoscaler": _component_summary("autoscaler", autoscaler_data),
    }

    all_anomalies = []
    all_anomalies.extend(pod_data.get("anomalies", []))
    all_anomalies.extend(node_data.get("anomalies", []))
    for component_name, component in component_metrics.items():
        if component.get("status") in ("warning", "critical"):
            all_anomalies.append({
                "type": component_name,
                "name": component_name,
                "status": component.get("status"),
                "metrics": component.get("summary", {}),
            })

    for elb_item in elb_data:
        if elb_item.get("status") == "warning":
            all_anomalies.append({
                "type": "elb",
                "name": elb_item.get("elb_name", elb_item.get("elb_id")),
                "metrics": elb_item.get("metrics", {})
            })

    for nat_item in nat_data:
        if nat_item.get("status") == "warning":
            all_anomalies.append({
                "type": "nat_gateway",
                "name": nat_item.get("nat_name", nat_item.get("nat_id")),
                "metrics": nat_item.get("metrics", {})
            })

    for eip_item in eip_data:
        if eip_item.get("status") == "warning":
            all_anomalies.append({
                "type": "eip",
                "name": eip_item.get("ip_address"),
                "metrics": eip_item.get("metrics", {})
            })

    pod_anomaly_count = sum(1 for a in pod_data.get("anomalies", []))
    node_anomaly_count = sum(1 for a in node_data.get("anomalies", []))
    elb_anomaly_count = sum(1 for e in elb_data if e.get("status") == "warning")
    nat_anomaly_count = sum(1 for n in nat_data if n.get("status") == "warning")
    eip_anomaly_count = sum(1 for e in eip_data if e.get("status") == "warning")
    component_anomaly_count = sum(
        1 for item in component_metrics.values()
        if item.get("status") in ("warning", "critical")
    )

    return {
        "success": True,
        "cluster_id": cluster_id,
        "region": region,
        "time_range": {
            "start": start_time,
            "end": end_time,
            "hours": hours
        },
        "summary": {
            "total_pods": len(pod_data.get("items", [])),
            "total_nodes": len(node_data.get("items", [])),
            "total_loadbalancer_services": len(lb_services),
            "total_elb": len(elb_data),
            "total_nat_gateway": len(nat_data),
            "total_eip": len(eip_data),
            "coredns_status": component_metrics["coredns"].get("status"),
            "nginx_ingress_status": component_metrics["nginx_ingress"].get("status"),
            "autoscaler_status": component_metrics["autoscaler"].get("status"),
            "pod_anomaly_count": pod_anomaly_count,
            "node_anomaly_count": node_anomaly_count,
            "elb_anomaly_count": elb_anomaly_count,
            "nat_anomaly_count": nat_anomaly_count,
            "eip_anomaly_count": eip_anomaly_count,
            "component_anomaly_count": component_anomaly_count,
            "total_anomaly_count": len(all_anomalies)
        },
        "pod_metrics": {
            "top_n": top_n,
            "items": pod_data.get("items", [])
        },
        "node_metrics": {
            "top_n": top_n,
            "items": node_data.get("items", [])
        },
        "elb_metrics": elb_data,
        "nat_gateway_metrics": nat_data,
        "eip_metrics": eip_data,
        "loadbalancer_services": lb_services,
        "cluster_network": cluster_network,
        "component_metrics": component_metrics,
        "anomalies": all_anomalies
    }


def cce_cluster_monitoring_aggregation_action(params: Dict[str, str]) -> Dict[str, Any]:
    """
    Action handler for huawei_cce_cluster_monitoring_aggregation tool.

    Expected parameters:
    - region: Huawei Cloud region (required)
    - cluster_id: CCE cluster ID (required)
    - start_time: Start time 'YYYY-MM-DD HH:MM:SS' (required)
    - end_time: End time 'YYYY-MM-DD HH:MM:SS' (required)
    - namespace: Kubernetes namespace (optional)
    - top_n: Number of top items (optional, default 10)
    """
    region = params.get("region")
    cluster_id = params.get("cluster_id")
    start_time = params.get("start_time")
    end_time = params.get("end_time")
    namespace = params.get("namespace")

    try:
        top_n = int(params.get("top_n", 10))
    except (ValueError, TypeError):
        top_n = 10

    if not region:
        return {"success": False, "error": "region is required"}
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}
    if not start_time:
        return {"success": False, "error": "start_time is required"}
    if not end_time:
        return {"success": False, "error": "end_time is required"}

    return analyze_cce_cluster_monitoring(
        region=region,
        cluster_id=cluster_id,
        start_time=start_time,
        end_time=end_time,
        namespace=namespace,
        top_n=top_n,
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        security_token=params.get("security_token")
    )
