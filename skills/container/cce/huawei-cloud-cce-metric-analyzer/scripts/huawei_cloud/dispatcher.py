"""CLI dispatch helpers for the CCE metric analyzer."""

from __future__ import annotations

from typing import Any, Callable, Dict

from . import cce_cluster_monitoring, cce_metrics, ecs, elb, network


Handler = Callable[[Dict[str, str]], Dict[str, Any]]


def _require(params: Dict[str, str], *keys: str) -> str | None:
    missing = [key for key in keys if not params.get(key)]
    if missing:
        return f"{', '.join(missing)} are required" if len(missing) > 1 else f"{missing[0]} is required"
    return None


def _to_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _metric_action(handler: Callable[..., Dict[str, Any]], *args: Any) -> Dict[str, Any]:
    result = handler(*args)
    if isinstance(result, dict) and result.get("success") is False:
        result.setdefault("hint", "Check hcloud configuration, IAM permissions, region, and resource identifiers.")
    return result


def _get_ecs_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return ecs.get_ecs_metrics(
        params["region"],
        params["instance_id"],
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
    )


def _get_elb_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return elb.get_elb_metrics(
        params["region"],
        params["elb_id"],
        _to_int(params.get("hours"), 1),
        _to_int(params.get("period"), 300),
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
    )


def _get_eip_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return network.get_eip_metrics(
        params["region"],
        params["eip_id"],
        _to_int(params.get("hours"), 1),
        _to_int(params.get("period"), 300),
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
    )


def _get_nat_metrics(params: Dict[str, str]) -> Dict[str, Any]:
    return network.get_nat_gateway_metrics(
        params["region"],
        params["nat_gateway_id"],
        _to_int(params.get("hours"), 1),
        _to_int(params.get("period"), 300),
        params.get("ak"),
        params.get("sk"),
        params.get("project_id"),
    )


def _cce_cluster_monitoring_aggregation(params: Dict[str, str]) -> Dict[str, Any]:
    return cce_cluster_monitoring.cce_cluster_monitoring_aggregation_action(params)


ACTION_SPECS: Dict[str, tuple[tuple[str, ...], Handler]] = {
    "huawei_get_cce_pod_metrics_topN": (
        ("region", "cluster_id"),
        lambda params: _metric_action(
            cce_metrics.get_cce_pod_metrics_topN,
            params["region"],
            params["cluster_id"],
            params.get("ak"),
            params.get("sk"),
            params.get("project_id"),
            params.get("namespace"),
            params.get("label_selector"),
            _to_int(params.get("top_n"), 10),
            _to_int(params.get("hours"), 1),
            params.get("cpu_query"),
            params.get("memory_query"),
            params.get("disk_query"),
            params.get("node_ip"),
            params.get("security_token"),
        ),
    ),
    "huawei_get_cce_pod_metrics": (
        ("region", "cluster_id", "pod_name"),
        lambda params: _metric_action(
            cce_metrics.get_cce_pod_metrics,
            params["region"],
            params["cluster_id"],
            params["pod_name"],
            params.get("ak"),
            params.get("sk"),
            params.get("project_id"),
            params.get("namespace"),
            _to_int(params.get("hours"), 1),
            params.get("cpu_query"),
            params.get("memory_query"),
            params.get("disk_query"),
            params.get("security_token"),
        ),
    ),
    "huawei_get_cce_node_metrics_topN": (
        ("region", "cluster_id"),
        lambda params: _metric_action(
            cce_metrics.get_cce_node_metrics_topN,
            params["region"],
            params["cluster_id"],
            params.get("ak"),
            params.get("sk"),
            params.get("project_id"),
            _to_int(params.get("top_n"), 10),
            _to_int(params.get("hours"), 1),
            params.get("cpu_query"),
            params.get("memory_query"),
            params.get("disk_query"),
            params.get("security_token"),
        ),
    ),
    "huawei_get_cce_node_metrics": (
        ("region", "cluster_id", "node_ip"),
        lambda params: _metric_action(
            cce_metrics.get_cce_node_metrics,
            params["region"],
            params["cluster_id"],
            params["node_ip"],
            params.get("ak"),
            params.get("sk"),
            params.get("project_id"),
            _to_int(params.get("hours"), 1),
            params.get("cpu_query"),
            params.get("memory_query"),
            params.get("disk_query"),
            params.get("security_token"),
        ),
    ),
    "huawei_get_cce_node_gpu_metrics": (
        ("region", "cluster_id", "node_ip"),
        lambda params: _metric_action(
            cce_metrics.get_cce_node_gpu_metrics,
            params["region"],
            params["cluster_id"],
            params["node_ip"],
            params.get("ak"),
            params.get("sk"),
            params.get("project_id"),
            _to_int(params.get("hours"), 1),
            params.get("gpu_selector"),
            params.get("utilization_query"),
            params.get("memory_utilization_query"),
            params.get("memory_used_query"),
            params.get("memory_total_query"),
            params.get("memory_free_query"),
            params.get("temperature_query"),
            params.get("power_usage_query"),
            params.get("schedule_policy_query"),
            params.get("xgpu_memory_total_query"),
            params.get("xgpu_memory_used_query"),
            params.get("xgpu_core_total_query"),
            params.get("xgpu_core_used_query"),
            params.get("xgpu_device_health_query"),
            params.get("security_token"),
        ),
    ),
    "huawei_get_cce_pod_gpu_metrics": (
        ("region", "cluster_id", "pod_name"),
        lambda params: _metric_action(
            cce_metrics.get_cce_pod_gpu_metrics,
            params["region"],
            params["cluster_id"],
            params["pod_name"],
            params.get("ak"),
            params.get("sk"),
            params.get("project_id"),
            params.get("namespace"),
            _to_int(params.get("hours"), 1),
            params.get("gpu_selector"),
            params.get("utilization_query"),
            params.get("memory_utilization_query"),
            params.get("memory_used_query"),
            params.get("memory_total_query"),
            params.get("memory_free_query"),
            params.get("schedule_policy_query"),
            params.get("xgpu_memory_total_query"),
            params.get("xgpu_memory_used_query"),
            params.get("xgpu_core_total_query"),
            params.get("xgpu_core_used_query"),
            params.get("xgpu_device_health_query"),
            params.get("security_token"),
        ),
    ),
    "huawei_get_cce_coredns_metrics": (
        ("region", "cluster_id"),
        lambda params: _metric_action(
            cce_metrics.get_cce_coredns_metrics,
            params["region"],
            params["cluster_id"],
            params.get("ak"),
            params.get("sk"),
            params.get("project_id"),
            params.get("namespace", "kube-system"),
            params.get("pod_regex", ".*coredns.*"),
            _to_int(params.get("hours"), 1),
            params.get("qps_query"),
            params.get("error_rate_query"),
            params.get("nxdomain_rate_query"),
            params.get("latency_p95_query"),
            params.get("cpu_query"),
            params.get("memory_query"),
            params.get("replicas_query"),
            params.get("security_token"),
        ),
    ),
    "huawei_get_cce_nginx_ingress_metrics": (
        ("region", "cluster_id"),
        lambda params: _metric_action(
            cce_metrics.get_cce_nginx_ingress_metrics,
            params["region"],
            params["cluster_id"],
            params.get("ak"),
            params.get("sk"),
            params.get("project_id"),
            params.get("namespace", "kube-system"),
            params.get("pod_regex", ".*nginx.*ingress.*|.*ingress.*nginx.*"),
            params.get("ingress_namespace"),
            _to_int(params.get("hours"), 1),
            _to_int(params.get("cert_expire_warning_days"), 30),
            _to_bool(params.get("check_certificates"), True),
            params.get("qps_query"),
            params.get("http_4xx_query"),
            params.get("http_5xx_query"),
            params.get("success_rate_query"),
            params.get("latency_p95_query"),
            params.get("active_connections_query"),
            params.get("cpu_query"),
            params.get("memory_query"),
            params.get("security_token"),
        ),
    ),
    "huawei_get_cce_autoscaler_metrics": (
        ("region", "cluster_id"),
        lambda params: _metric_action(
            cce_metrics.get_cce_autoscaler_metrics,
            params["region"],
            params["cluster_id"],
            params.get("ak"),
            params.get("sk"),
            params.get("project_id"),
            params.get("namespace", "kube-system"),
            params.get("pod_regex", ".*cluster.*autoscaler.*|.*autoscaler.*"),
            params.get("hpa_namespace"),
            _to_int(params.get("hours"), 1),
            _to_bool(params.get("include_hpa"), True),
            params.get("unschedulable_pods_query"),
            params.get("nodes_count_query"),
            params.get("scale_up_query"),
            params.get("scale_down_query"),
            params.get("errors_query"),
            params.get("node_groups_query"),
            params.get("hpa_current_replicas_query"),
            params.get("hpa_desired_replicas_query"),
            params.get("cpu_query"),
            params.get("memory_query"),
            params.get("security_token"),
        ),
    ),
    "huawei_get_cce_apiserver_metrics": (
        ("region", "cluster_id"),
        lambda params: _metric_action(
            cce_metrics.get_cce_apiserver_metrics,
            params["region"],
            params["cluster_id"],
            params.get("ak"),
            params.get("sk"),
            params.get("project_id"),
            params.get("namespace", "kube-system"),
            params.get("pod_regex", ".*kube-apiserver.*|.*apiserver.*"),
            _to_int(params.get("hours"), 1),
            params.get("security_token"),
            params.get("metric_selector"),
        ),
    ),
    "huawei_get_cce_etcd_metrics": (
        ("region", "cluster_id"),
        lambda params: _metric_action(
            cce_metrics.get_cce_etcd_metrics,
            params["region"],
            params["cluster_id"],
            params.get("ak"),
            params.get("sk"),
            params.get("project_id"),
            params.get("namespace", "kube-system"),
            params.get("pod_regex", ".*etcd.*"),
            _to_int(params.get("hours"), 1),
            params.get("security_token"),
            params.get("metric_selector"),
        ),
    ),
    "huawei_get_cce_controller_manager_metrics": (
        ("region", "cluster_id"),
        lambda params: _metric_action(
            cce_metrics.get_cce_controller_manager_metrics,
            params["region"],
            params["cluster_id"],
            params.get("ak"),
            params.get("sk"),
            params.get("project_id"),
            params.get("namespace", "kube-system"),
            params.get("pod_regex", ".*kube-controller-manager.*|.*controller-manager.*"),
            _to_int(params.get("hours"), 1),
            params.get("security_token"),
            params.get("metric_selector"),
        ),
    ),
    "huawei_get_cce_scheduler_metrics": (
        ("region", "cluster_id"),
        lambda params: _metric_action(
            cce_metrics.get_cce_scheduler_metrics,
            params["region"],
            params["cluster_id"],
            params.get("ak"),
            params.get("sk"),
            params.get("project_id"),
            params.get("namespace", "kube-system"),
            params.get("pod_regex", ".*kube-scheduler.*|.*scheduler.*"),
            _to_int(params.get("hours"), 1),
            params.get("security_token"),
            params.get("metric_selector"),
        ),
    ),
    "huawei_get_ecs_metrics": (("region", "instance_id"), _get_ecs_metrics),
    "huawei_get_elb_metrics": (("region", "elb_id"), _get_elb_metrics),
    "huawei_get_eip_metrics": (("region", "eip_id"), _get_eip_metrics),
    "huawei_get_nat_gateway_metrics": (("region", "nat_gateway_id"), _get_nat_metrics),
    "huawei_cce_cluster_monitoring_aggregation": (
        ("region", "cluster_id", "start_time", "end_time"),
        _cce_cluster_monitoring_aggregation,
    ),
}


def is_registered_action(action: str) -> bool:
    return action in ACTION_SPECS


def dispatch_action(action: str, params: Dict[str, str]) -> Dict[str, Any]:
    required, handler = ACTION_SPECS[action]
    error = _require(params, *required)
    if error:
        return {"success": False, "error": error}
    return handler(params)
