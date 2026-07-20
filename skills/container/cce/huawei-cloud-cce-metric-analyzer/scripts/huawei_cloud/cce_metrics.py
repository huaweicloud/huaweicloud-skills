from .common import *
from . import aom, cce


def _label_selector(*parts: Optional[str]) -> str:
    return ",".join(part for part in parts if part)


def _cluster_label(cluster_id: str) -> str:
    return f'cluster="{cluster_id}"'


def _prom_regex_literal(value: str) -> str:
    import re

    return re.escape(value).replace(r"\.", "[.]")


def _get_aom_instance(region: str, cluster_id: str, ak: Optional[str], sk: Optional[str], project_id: Optional[str]) -> Dict[str, Any]:
    """Resolve the AOM Prometheus instance from the cie-collector addon via hcloud."""
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    list_resp = run_hcloud(
        "CCE",
        "ListAddonInstances",
        region,
        {"cluster_id": cluster_id, "project_id": project_id},
        ak=ak,
        sk=sk,
        project_id=project_id,
    )
    if not list_resp.get("success"):
        return list_resp

    cie_addon_id = None
    for addon in (list_resp.get("data") or {}).get("items", []) or []:
        metadata = addon.get("metadata") or {}
        if metadata.get("name") == "cie-collector":
            cie_addon_id = metadata.get("uid")
            break

    if not cie_addon_id:
        return {"success": False, "error": "cie-collector addon not found in cluster"}

    show_resp = run_hcloud(
        "CCE",
        "ShowAddonInstance",
        region,
        {"id": cie_addon_id, "cluster_id": cluster_id, "project_id": project_id},
        ak=ak,
        sk=sk,
        project_id=project_id,
    )
    if not show_resp.get("success"):
        return show_resp

    detail = show_resp.get("data") or {}
    detail_root = detail.get("addon_instance", detail) if isinstance(detail, dict) else {}
    spec = detail_root.get("spec", {}) or {}

    candidates = []
    custom = spec.get("custom")
    if isinstance(custom, dict):
        candidates.append(("hcloud:cie-collector.spec.custom", custom))

    values = spec.get("values")
    if isinstance(values, dict):
        candidates.append(("hcloud:cie-collector.spec.values", values))
        nested_custom = values.get("custom")
        if isinstance(nested_custom, dict):
            candidates.append(("hcloud:cie-collector.spec.values.custom", nested_custom))

    for source, data in candidates:
        aom_instance_id = data.get("aom_instance_id") or data.get("prom_instance_id") or data.get("aom_id")
        if aom_instance_id:
            return {"success": True, "aom_instance_id": aom_instance_id, "source": source}

    return {"success": False, "error": "aom_instance_id not found in cie-collector addon config"}

def get_cce_pod_metrics_topN(region: str, cluster_id: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, namespace: str = None, label_selector: str = None, top_n: int = 10, hours: int = 1, cpu_query: str = None, memory_query: str = None, disk_query: str = None, node_ip: Optional[str] = None, security_token: Optional[str] = None) -> Dict[str, Any]:
    """获取 CCE 集群 Pod 监控数据

    自动获取 AOM 实例并执行 Pod CPU/内存/磁盘监控查询，返回 Top N 数据。

    Args:
        region: 华为云区域 (如 cn-north-4)
        cluster_id: CCE 集群 ID
        ak: Access Key ID (可选)
        sk: Secret Access Key (可选)
        project_id: Project ID (可选)
        namespace: 命名空间过滤 (可选，默认所有命名空间)
        label_selector: Pod 标签选择器 (可选，格式: "app=nginx,version=v1")
        top_n: 返回 Top N 数据 (默认 10)
        hours: 查询时间范围（小时）(默认 1)
        cpu_query: 自定义 CPU PromQL (可选)
        memory_query: 自定义内存 PromQL (可选)
        disk_query: 自定义磁盘 PromQL (可选)
        node_ip: 节点 IP 过滤 (可选，只返回指定节点上的 Pod)

    Returns:
        Dict with success status and pod metrics data
    """
    # Explicitly assign to ensure node_ip is in scope
    node_ip = node_ip
    import time as time_module

    access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)

    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    # ========== 1. 获取集群名称 ==========
    cluster_name = cluster_id
    try:
        clusters_result = cce.list_cce_clusters(region, ak, sk, project_id)
        if clusters_result.get("success"):
            for c in clusters_result.get("clusters", []):
                if c.get("id") == cluster_id:
                    cluster_name = c.get("name", cluster_id)
                    break
    except Exception:
        pass

    # ========== 2. 如果有 label_selector，先获取符合条件的 Pod 列表 ==========
    pod_filter_list = None  # 用于过滤的 Pod 名称列表
    matched_pods_info = []  # 匹配的 Pod 详细信息

    if label_selector:
        # 解析 label_selector (格式: "app=nginx,version=v1")
        label_filters = {}
        for part in label_selector.split(","):
            part = part.strip()
            if "=" in part:
                key, value = part.split("=", 1)
                label_filters[key.strip()] = value.strip()

        if label_filters:
            # 获取 Pod 列表
            pods_result = cce.get_kubernetes_pods(region, cluster_id, access_key, secret_key, proj_id, namespace)
            if pods_result.get("success"):
                matched_pods = []
                for pod in pods_result.get("pods", []):
                    pod_labels = pod.get("labels", {})
                    pod_name = pod.get("name", "")
                    pod_ns = pod.get("namespace", "")

                    # 检查是否匹配所有 label 条件
                    match = True
                    for key, value in label_filters.items():
                        if pod_labels.get(key) != value:
                            match = False
                            break

                    if match:
                        matched_pods.append(pod_name)
                        matched_pods_info.append({
                            "name": pod_name,
                            "namespace": pod_ns,
                            "labels": pod_labels,
                            "status": pod.get("status"),
                            "node": pod.get("node")
                        })

                if matched_pods:
                    pod_filter_list = matched_pods
                else:
                    # 没有匹配的 Pod，直接返回空结果
                    return {
                        "success": True,
                        "region": region,
                        "cluster_id": cluster_id,
                        "cluster_name": cluster_name,
                        "aom_instance_id": None,
                        "inspection_time": time_module.strftime('%Y-%m-%d %H:%M:%S', time_module.localtime()),
                        "query_params": {
                            "top_n": top_n,
                            "hours": hours,
                            "namespace": namespace,
                            "label_selector": label_selector
                        },
                        "label_filter": {
                            "selector": label_selector,
                            "parsed": label_filters,
                            "matched_count": 0,
                            "matched_pods": []
                        },
                        "promql": {"cpu": None, "memory": None, "disk": None},
                        "metrics": {
                            "cpu_top_n": [],
                            "memory_top_n": [],
                            "disk_top_n": [],
                            "all_pods": []
                        },
                        "summary": {
                            "total_pods": 0,
                            "critical_cpu": 0,
                            "critical_memory": 0,
                            "critical_disk": 0,
                            "warning_cpu": 0,
                            "warning_memory": 0,
                            "warning_disk": 0
                        },
                        "message": f"没有找到匹配 label_selector '{label_selector}' 的 Pod"
                    }

    # ========== 3. 获取 AOM 实例 ==========
    aom_result = _get_aom_instance(region, cluster_id, ak, sk, project_id)
    if not aom_result.get("success"):
        return {
            "success": False,
            "error": aom_result.get("error", "未找到可用的 AOM 实例"),
            "error_type": aom_result.get("error_type"),
            "cluster_id": cluster_id,
            "cluster_name": cluster_name
        }
    aom_instance_id = aom_result.get("aom_instance_id")

    # ========== 4. 构建 PromQL 查询 ==========
    # 构建 Pod 过滤条件
    pod_filter_clause = ""
    if pod_filter_list:
        # 使用正则匹配多个 Pod 名称
        pod_regex = "|".join(pod_filter_list[:100])  # 限制最多 100 个 Pod
        pod_filter_clause = f',pod=~"{pod_regex}"'

    # 构建节点过滤条件
    node_filter_clause = ""
    if node_ip:
        node_filter_clause = f',node="{node_ip}"'
    cluster_filter_clause = f',cluster="{cluster_id}"'

    # 默认 CPU 使用率 PromQL (相对 Limit %)
    if cpu_query is None:
        if namespace:
            cpu_query = f'topk({top_n}, sum by (pod, namespace) (rate(container_cpu_usage_seconds_total{{image!="",namespace="{namespace}"{cluster_filter_clause}{pod_filter_clause}{node_filter_clause}}}[5m])) / on (pod, namespace) group_left sum by (pod, namespace) (kube_pod_container_resource_limits{{resource="cpu",namespace="{namespace}"{cluster_filter_clause}{pod_filter_clause}{node_filter_clause}}}) * 100)'
        else:
            cpu_query = f'topk({top_n}, sum by (pod, namespace) (rate(container_cpu_usage_seconds_total{{image!=""{cluster_filter_clause}{pod_filter_clause}{node_filter_clause}}}[5m])) / on (pod, namespace) group_left sum by (pod, namespace) (kube_pod_container_resource_limits{{resource="cpu"{cluster_filter_clause}{pod_filter_clause}{node_filter_clause}}}) * 100)'

    # 默认内存使用率 PromQL (相对 Limit %)
    if memory_query is None:
        if namespace:
            memory_query = f'topk({top_n}, sum by (pod, namespace) (container_memory_working_set_bytes{{image!="",namespace="{namespace}"{cluster_filter_clause}{pod_filter_clause}{node_filter_clause}}}) / on (pod, namespace) group_left sum by (pod, namespace) (kube_pod_container_resource_limits{{resource="memory",namespace="{namespace}"{cluster_filter_clause}{pod_filter_clause}{node_filter_clause}}}) * 100)'
        else:
            memory_query = f'topk({top_n}, sum by (pod, namespace) (container_memory_working_set_bytes{{image!=""{cluster_filter_clause}{pod_filter_clause}{node_filter_clause}}}) / on (pod, namespace) group_left sum by (pod, namespace) (kube_pod_container_resource_limits{{resource="memory"{cluster_filter_clause}{pod_filter_clause}{node_filter_clause}}}) * 100)'

    # 默认磁盘使用率 PromQL (相对容器文件系统容量 %)
    if disk_query is None:
        if namespace:
            disk_query = f'topk({top_n}, sum by (pod, namespace) (container_fs_usage_bytes{{image!="",namespace="{namespace}"{cluster_filter_clause}{pod_filter_clause}{node_filter_clause}}}) / on (pod, namespace) group_left sum by (pod, namespace) (container_fs_limit_bytes{{image!="",namespace="{namespace}"{cluster_filter_clause}{pod_filter_clause}{node_filter_clause}}}) * 100)'
        else:
            disk_query = f'topk({top_n}, sum by (pod, namespace) (container_fs_usage_bytes{{image!=""{cluster_filter_clause}{pod_filter_clause}{node_filter_clause}}}) / on (pod, namespace) group_left sum by (pod, namespace) (container_fs_limit_bytes{{image!=""{cluster_filter_clause}{pod_filter_clause}{node_filter_clause}}}) * 100)'

    # ========== 5. 执行查询 ==========
    cpu_result = aom.get_aom_prom_metrics_http(region, aom_instance_id, cpu_query, hours=hours, ak=access_key, sk=secret_key, project_id=proj_id, security_token=security_token)
    memory_result = aom.get_aom_prom_metrics_http(region, aom_instance_id, memory_query, hours=hours, ak=access_key, sk=secret_key, project_id=proj_id, security_token=security_token)
    disk_result = aom.get_aom_prom_metrics_http(region, aom_instance_id, disk_query, hours=hours, ak=access_key, sk=secret_key, project_id=proj_id, security_token=security_token)

    # ========== 6. 解析结果 ==========
    def parse_top_metrics(result, value_key):
        metrics = []
        if result.get("success") and result.get("result", {}).get("data", {}).get("result"):
            result_items = result["result"]["data"]["result"]
        else:
            return metrics

        for item in result_items:
            metric = item.get("metric", {})
            values = item.get("values", [])
            if values:
                try:
                    latest_value = float(values[-1][1])
                    metrics.append({
                        "pod": metric.get("pod", "unknown"),
                        "namespace": metric.get("namespace", "unknown"),
                        value_key: round(latest_value, 2),
                        "status": "critical" if latest_value > 80 else "warning" if latest_value > 50 else "normal",
                        "time_series": values  # 保存完整的时序数据
                    })
                except (ValueError, IndexError):
                    pass
        return metrics

    cpu_metrics = parse_top_metrics(cpu_result, "cpu_usage_percent")
    memory_metrics = parse_top_metrics(memory_result, "memory_usage_percent")
    disk_metrics = parse_top_metrics(disk_result, "disk_usage_percent")

    # 按使用率排序
    cpu_metrics.sort(key=lambda x: x["cpu_usage_percent"], reverse=True)
    memory_metrics.sort(key=lambda x: x["memory_usage_percent"], reverse=True)
    disk_metrics.sort(key=lambda x: x["disk_usage_percent"], reverse=True)

    # 合并 CPU、内存和磁盘数据
    pod_metrics_map = {}
    for m in cpu_metrics[:top_n]:
        key = f"{m['namespace']}/{m['pod']}"
        pod_metrics_map[key] = m
    for m in memory_metrics[:top_n]:
        key = f"{m['namespace']}/{m['pod']}"
        if key in pod_metrics_map:
            pod_metrics_map[key]["memory_usage_percent"] = m["memory_usage_percent"]
        else:
            pod_metrics_map[key] = m
    for m in disk_metrics[:top_n]:
        key = f"{m['namespace']}/{m['pod']}"
        if key in pod_metrics_map:
            pod_metrics_map[key]["disk_usage_percent"] = m["disk_usage_percent"]
        else:
            pod_metrics_map[key] = m

    # ========== 7. 返回结果 ==========
    result = {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "cluster_name": cluster_name,
        "aom_instance_id": aom_instance_id,
        "inspection_time": time_module.strftime('%Y-%m-%d %H:%M:%S', time_module.localtime()),
        "query_params": {
            "top_n": top_n,
            "hours": hours,
            "namespace": namespace
        },
        "promql": {
            "cpu": cpu_query,
            "memory": memory_query,
            "disk": disk_query
        },
        "metrics": {
            "cpu_top_n": cpu_metrics[:top_n],
            "memory_top_n": memory_metrics[:top_n],
            "disk_top_n": disk_metrics[:top_n],
            "all_pods": list(pod_metrics_map.values())
        },
        "summary": {
            "total_pods": len(pod_metrics_map),
            "critical_cpu": len([m for m in cpu_metrics if m["status"] == "critical"]),
            "critical_memory": len([m for m in memory_metrics if m["status"] == "critical"]),
            "critical_disk": len([m for m in disk_metrics if m["status"] == "critical"]),
            "warning_cpu": len([m for m in cpu_metrics if m["status"] == "warning"]),
            "warning_memory": len([m for m in memory_metrics if m["status"] == "warning"]),
            "warning_disk": len([m for m in disk_metrics if m["status"] == "warning"])
        }
    }

    # 如果有 label 过滤，添加过滤信息
    if label_selector:
        result["query_params"]["label_selector"] = label_selector
        result["label_filter"] = {
            "selector": label_selector,
            "matched_count": len(matched_pods_info),
            "matched_pods": matched_pods_info[:50]  # 最多返回 50 个 Pod 信息
        }

    return result

def get_cce_pod_metrics(region: str, cluster_id: str, pod_name: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, namespace: str = None, hours: int = 1, cpu_query: str = None, memory_query: str = None, disk_query: str = None, security_token: Optional[str] = None) -> Dict[str, Any]:
    """获取指定CCE Pod的CPU、内存、磁盘使用率监控时序数据

    Args:
        region: 华为云区域 (如 cn-north-4)
        cluster_id: CCE 集群 ID
        pod_name: Pod名称
        ak: Access Key ID (可选)
        sk: Secret Access Key (可选)
        project_id: Project ID (可选)
        namespace: 命名空间（可选，默认所有命名空间）
        hours: 查询时间范围（小时）(默认 1)
        cpu_query: 自定义 CPU PromQL (可选)
        memory_query: 自定义内存 PromQL (可选)
        disk_query: 自定义磁盘 PromQL (可选)

    Returns:
        Dict with success status and specified pod metrics time series data
    """
    import time as time_module

    access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)

    if not cluster_id or not pod_name:
        return {"success": False, "error": "cluster_id and pod_name are required"}

    # ========== 1. 获取集群名称 ==========
    cluster_name = cluster_id
    try:
        clusters_result = cce.list_cce_clusters(region, ak, sk, project_id)
        if clusters_result.get("success"):
            for c in clusters_result.get("clusters", []):
                if c.get("id") == cluster_id:
                    cluster_name = c.get("name", cluster_id)
                    break
    except Exception:
        pass

    # ========== 2. 获取 AOM 实例 ==========
    aom_result = _get_aom_instance(region, cluster_id, ak, sk, project_id)
    if not aom_result.get("success"):
        return {
            "success": False,
            "error": aom_result.get("error", "未找到可用的 AOM 实例"),
            "error_type": aom_result.get("error_type"),
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "pod_name": pod_name,
            "namespace": namespace
        }
    aom_instance_id = aom_result.get("aom_instance_id")

    # ========== 3. 构建 PromQL 查询（筛选指定Pod） ==========
    pod_filter = f',pod="{pod_name}"'
    namespace_filter = f',namespace="{namespace}"' if namespace else ""
    cluster_filter = f',cluster="{cluster_id}"'

    # 默认 CPU 使用率 PromQL (相对 Limit %)
    if cpu_query is None:
        cpu_query = f'sum by (pod, namespace) (rate(container_cpu_usage_seconds_total{{image!=""{cluster_filter}{namespace_filter}{pod_filter}}}[5m])) / on (pod, namespace) group_left sum by (pod, namespace) (kube_pod_container_resource_limits{{resource="cpu"{cluster_filter}{namespace_filter}{pod_filter}}}) * 100'

    # 默认内存使用率 PromQL (相对 Limit %)
    if memory_query is None:
        memory_query = f'sum by (pod, namespace) (container_memory_working_set_bytes{{image!=""{cluster_filter}{namespace_filter}{pod_filter}}}) / on (pod, namespace) group_left sum by (pod, namespace) (kube_pod_container_resource_limits{{resource="memory"{cluster_filter}{namespace_filter}{pod_filter}}}) * 100'

    # 默认磁盘使用率 PromQL (相对容器文件系统容量 %)
    if disk_query is None:
        disk_query = f'sum by (pod, namespace) (container_fs_usage_bytes{{image!=""{cluster_filter}{namespace_filter}{pod_filter}}}) / on (pod, namespace) group_left sum by (pod, namespace) (container_fs_limit_bytes{{image!=""{cluster_filter}{namespace_filter}{pod_filter}}}) * 100'

    # ========== 4. 执行查询 ==========
    cpu_result = aom.get_aom_prom_metrics_http(region, aom_instance_id, cpu_query, hours=hours, ak=access_key, sk=secret_key, project_id=proj_id, security_token=security_token)
    memory_result = aom.get_aom_prom_metrics_http(region, aom_instance_id, memory_query, hours=hours, ak=access_key, sk=secret_key, project_id=proj_id, security_token=security_token)
    disk_result = aom.get_aom_prom_metrics_http(region, aom_instance_id, disk_query, hours=hours, ak=access_key, sk=secret_key, project_id=proj_id, security_token=security_token)

    # ========== 5. 解析结果 ==========
    def parse_metric_result(result, metric_name):
        """解析监控结果，返回时序数据"""
        if result.get("success") and result.get("result", {}).get("data", {}).get("result"):
            for item in result["result"]["data"]["result"]:
                values = item.get("values", [])
                if values:
                    time_series = []
                    for ts, val in values:
                        try:
                            time_series.append({
                                "timestamp": int(ts),
                                "time": time_module.strftime('%Y-%m-%d %H:%M:%S', time_module.localtime(int(ts))),
                                "value": round(float(val), 2)
                            })
                        except (ValueError, IndexError):
                            pass
                    if time_series:
                        latest_value = time_series[-1]["value"]
                        return {
                            metric_name: latest_value,
                            "status": "critical" if latest_value > 80 else "warning" if latest_value > 50 else "normal",
                            "time_series": time_series
                        }
        return None

    cpu_data = parse_metric_result(cpu_result, "cpu_usage_percent")
    memory_data = parse_metric_result(memory_result, "memory_usage_percent")
    disk_data = parse_metric_result(disk_result, "disk_usage_percent")

    # ========== 6. 返回结果 ==========
    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "cluster_name": cluster_name,
        "pod_name": pod_name,
        "namespace": namespace,
        "aom_instance_id": aom_instance_id,
        "query_time": time_module.strftime('%Y-%m-%d %H:%M:%S', time_module.localtime()),
        "query_params": {
            "hours": hours
        },
        "promql": {
            "cpu": cpu_query,
            "memory": memory_query,
            "disk": disk_query
        },
        "metrics": {
            "cpu": cpu_data,
            "memory": memory_data,
            "disk": disk_data
        }
    }

def get_cce_coredns_metrics(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    namespace: str = "kube-system",
    pod_regex: str = ".*coredns.*",
    hours: int = 1,
    qps_query: str = None,
    error_rate_query: str = None,
    nxdomain_rate_query: str = None,
    latency_p95_query: str = None,
    cpu_query: str = None,
    memory_query: str = None,
    replicas_query: str = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Query key CoreDNS metrics from the CCE cluster AOM Prometheus instance."""
    import time as time_module

    access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    cluster_name = cluster_id
    try:
        clusters_result = cce.list_cce_clusters(region, ak, sk, project_id)
        if clusters_result.get("success"):
            for cluster in clusters_result.get("clusters", []):
                if cluster.get("id") == cluster_id:
                    cluster_name = cluster.get("name", cluster_id)
                    break
    except Exception:
        pass

    aom_result = _get_aom_instance(region, cluster_id, ak, sk, project_id)
    if not aom_result.get("success"):
        return {
            "success": False,
            "error": aom_result.get("error", "AOM instance not found"),
            "error_type": aom_result.get("error_type"),
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
        }
    aom_instance_id = aom_result.get("aom_instance_id")

    selector = _label_selector(_cluster_label(cluster_id), f'namespace="{namespace}"', f'pod=~"{pod_regex}"')
    dns_selector = selector
    if qps_query is None:
        qps_query = f"sum(rate(coredns_dns_requests_total{{{dns_selector}}}[5m]))"
    if error_rate_query is None:
        error_rate_query = (
            f"sum(rate(coredns_dns_responses_total{{{dns_selector},rcode!~\"NOERROR|NXDOMAIN\"}}[5m])) "
            f"/ sum(rate(coredns_dns_responses_total{{{dns_selector}}}[5m])) * 100"
        )
    if nxdomain_rate_query is None:
        nxdomain_rate_query = (
            f"sum(rate(coredns_dns_responses_total{{{dns_selector},rcode=\"NXDOMAIN\"}}[5m])) "
            f"/ sum(rate(coredns_dns_responses_total{{{dns_selector}}}[5m])) * 100"
        )
    if latency_p95_query is None:
        latency_p95_query = (
            f"histogram_quantile(0.95, sum by (le) "
            f"(rate(coredns_dns_request_duration_seconds_bucket{{{dns_selector}}}[5m]))) * 1000"
        )
    if cpu_query is None:
        cpu_query = (
            f"sum by (pod, namespace) "
            f"(rate(container_cpu_usage_seconds_total{{image!=\"\",{selector}}}[5m]))"
        )
    if memory_query is None:
        memory_query = (
            f"sum by (pod, namespace) "
            f"(container_memory_working_set_bytes{{image!=\"\",{selector}}})"
        )
    if replicas_query is None:
        replicas_query = f"count(kube_pod_info{{{selector}}})"

    queries = {
        "qps": qps_query,
        "error_rate": error_rate_query,
        "nxdomain_rate": nxdomain_rate_query,
        "latency_p95": latency_p95_query,
        "cpu": cpu_query,
        "memory": memory_query,
        "replicas": replicas_query,
    }
    query_results = {
        name: aom.get_aom_prom_metrics_http(
            region,
            aom_instance_id,
            query,
            hours=hours,
            ak=access_key,
            sk=secret_key,
            project_id=proj_id,
            security_token=security_token,
        )
        for name, query in queries.items()
    }

    failed_queries = {
        name: result.get("error", "AOM query failed")
        for name, result in query_results.items()
        if not result.get("success")
    }
    if failed_queries:
        return {
            "success": False,
            "error": "AOM Prometheus query failed",
            "failed_queries": failed_queries,
            "region": region,
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "aom_instance_id": aom_instance_id,
            "promql": queries,
        }

    def _series_from_values(values):
        import math

        series = []
        for ts, val in values or []:
            try:
                timestamp = int(float(ts))
                value = float(val)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(value):
                continue
            series.append({
                "timestamp": timestamp,
                "time": time_module.strftime("%Y-%m-%d %H:%M:%S", time_module.localtime(timestamp)),
                "value": round(value, 4),
            })
        return series

    def _parse_scalar(result, value_key):
        items = result.get("result", {}).get("data", {}).get("result") or []
        for item in items:
            series = _series_from_values(item.get("values"))
            if series:
                return {value_key: series[-1]["value"], "time_series": series}
        return {value_key: None, "time_series": []}

    def _parse_pod_vector(result, value_key):
        items = result.get("result", {}).get("data", {}).get("result") or []
        parsed = []
        for item in items:
            metric = item.get("metric") or {}
            series = _series_from_values(item.get("values"))
            if not series:
                continue
            parsed.append({
                "pod": metric.get("pod", "unknown"),
                "namespace": metric.get("namespace", namespace),
                value_key: series[-1]["value"],
                "time_series": series,
            })
        parsed.sort(key=lambda item: item.get(value_key) or 0, reverse=True)
        return parsed

    qps = _parse_scalar(query_results["qps"], "qps")
    error_rate = _parse_scalar(query_results["error_rate"], "error_rate_percent")
    nxdomain_rate = _parse_scalar(query_results["nxdomain_rate"], "nxdomain_rate_percent")
    latency_p95 = _parse_scalar(query_results["latency_p95"], "latency_p95_ms")
    replicas = _parse_scalar(query_results["replicas"], "replicas")
    cpu_by_pod = _parse_pod_vector(query_results["cpu"], "cpu_cores")
    memory_by_pod = _parse_pod_vector(query_results["memory"], "memory_working_set_bytes")

    latest_error_rate = error_rate.get("error_rate_percent")
    latest_latency = latency_p95.get("latency_p95_ms")
    status = "normal"
    if (latest_error_rate is not None and latest_error_rate > 5) or (latest_latency is not None and latest_latency > 1000):
        status = "critical"
    elif (latest_error_rate is not None and latest_error_rate > 1) or (latest_latency is not None and latest_latency > 200):
        status = "warning"

    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "cluster_name": cluster_name,
        "namespace": namespace,
        "pod_regex": pod_regex,
        "aom_instance_id": aom_instance_id,
        "query_time": time_module.strftime("%Y-%m-%d %H:%M:%S", time_module.localtime()),
        "query_params": {"hours": hours},
        "promql": queries,
        "metrics": {
            "qps": qps,
            "error_rate": error_rate,
            "nxdomain_rate": nxdomain_rate,
            "latency_p95": latency_p95,
            "replicas": replicas,
            "cpu_by_pod": cpu_by_pod,
            "memory_by_pod": memory_by_pod,
        },
        "summary": {
            "status": status,
            "qps": qps.get("qps"),
            "error_rate_percent": latest_error_rate,
            "nxdomain_rate_percent": nxdomain_rate.get("nxdomain_rate_percent"),
            "latency_p95_ms": latest_latency,
            "replicas": replicas.get("replicas"),
            "observed_cpu_pods": len(cpu_by_pod),
            "observed_memory_pods": len(memory_by_pod),
        },
    }

def get_cce_nginx_ingress_metrics(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    namespace: Optional[str] = "kube-system",
    pod_regex: str = ".*nginx.*ingress.*|.*ingress.*nginx.*",
    ingress_namespace: Optional[str] = None,
    hours: int = 1,
    cert_expire_warning_days: int = 30,
    check_certificates: bool = True,
    qps_query: str = None,
    http_4xx_query: str = None,
    http_5xx_query: str = None,
    success_rate_query: str = None,
    latency_p95_query: str = None,
    active_connections_query: str = None,
    cpu_query: str = None,
    memory_query: str = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Query nginx-ingress request-processing metrics and Ingress TLS certificate status."""
    import time as time_module

    access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    cluster_name = cluster_id
    try:
        clusters_result = cce.list_cce_clusters(region, ak, sk, project_id)
        if clusters_result.get("success"):
            for cluster in clusters_result.get("clusters", []):
                if cluster.get("id") == cluster_id:
                    cluster_name = cluster.get("name", cluster_id)
                    break
    except Exception:
        pass

    aom_result = _get_aom_instance(region, cluster_id, ak, sk, project_id)
    if not aom_result.get("success"):
        return {
            "success": False,
            "error": aom_result.get("error", "AOM instance not found"),
            "error_type": aom_result.get("error_type"),
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
        }
    aom_instance_id = aom_result.get("aom_instance_id")

    selector_parts = [_cluster_label(cluster_id)]
    if namespace:
        selector_parts.append(f'namespace="{namespace}"')
    if pod_regex:
        selector_parts.append(f'pod=~"{pod_regex}"')
    selector = ",".join(selector_parts)
    container_selector = ",".join(["image!=\"\""] + selector_parts)

    def _with_selector(extra: str = "") -> str:
        labels = ",".join(part for part in [selector, extra] if part)
        return "{" + labels + "}"

    http_4xx_label = 'status=~"4.."'
    http_5xx_label = 'status=~"5.."'
    non_5xx_label = 'status!~"5.."'
    active_state_label = 'state="active"'

    if qps_query is None:
        qps_query = (
            f"sum(rate(nginx_ingress_controller_requests{_with_selector()}[5m])) "
            f"or sum(rate(nginx_ingress_controller_nginx_process_requests_total{_with_selector()}[5m]))"
        )
    if http_4xx_query is None:
        http_4xx_query = f"sum(rate(nginx_ingress_controller_requests{_with_selector(http_4xx_label)}[5m]))"
    if http_5xx_query is None:
        http_5xx_query = f"sum(rate(nginx_ingress_controller_requests{_with_selector(http_5xx_label)}[5m]))"
    if success_rate_query is None:
        success_rate_query = (
            f"sum(rate(nginx_ingress_controller_requests{_with_selector(non_5xx_label)}[5m])) "
            f"/ sum(rate(nginx_ingress_controller_requests{_with_selector()}[5m])) * 100"
        )
    if latency_p95_query is None:
        latency_p95_query = (
            f"histogram_quantile(0.95, sum by (le) "
            f"(rate(nginx_ingress_controller_request_duration_seconds_bucket{_with_selector()}[5m]))) * 1000"
        )
    if active_connections_query is None:
        active_connections_query = (
            f"sum(nginx_ingress_controller_nginx_process_connections{_with_selector(active_state_label)})"
        )
    if cpu_query is None:
        cpu_query = (
            f"sum by (pod, namespace) "
            f"(rate(container_cpu_usage_seconds_total{{{container_selector}}}[5m]))"
        )
    if memory_query is None:
        memory_query = (
            f"sum by (pod, namespace) "
            f"(container_memory_working_set_bytes{{{container_selector}}})"
        )

    queries = {
        "qps": qps_query,
        "http_4xx": http_4xx_query,
        "http_5xx": http_5xx_query,
        "success_rate": success_rate_query,
        "latency_p95": latency_p95_query,
        "active_connections": active_connections_query,
        "cpu": cpu_query,
        "memory": memory_query,
    }
    query_results = {
        name: aom.get_aom_prom_metrics_http(
            region,
            aom_instance_id,
            query,
            hours=hours,
            ak=access_key,
            sk=secret_key,
            project_id=proj_id,
            security_token=security_token,
        )
        for name, query in queries.items()
    }

    failed_queries = {
        name: result.get("error", "AOM query failed")
        for name, result in query_results.items()
        if not result.get("success")
    }
    if failed_queries:
        return {
            "success": False,
            "error": "AOM Prometheus query failed",
            "failed_queries": failed_queries,
            "region": region,
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "aom_instance_id": aom_instance_id,
            "promql": queries,
        }

    def _series_from_values(values):
        import math

        series = []
        for ts, val in values or []:
            try:
                timestamp = int(float(ts))
                value = float(val)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(value):
                continue
            series.append({
                "timestamp": timestamp,
                "time": time_module.strftime("%Y-%m-%d %H:%M:%S", time_module.localtime(timestamp)),
                "value": round(value, 4),
            })
        return series

    def _parse_scalar(result, value_key):
        items = result.get("result", {}).get("data", {}).get("result") or []
        for item in items:
            series = _series_from_values(item.get("values"))
            if series:
                return {value_key: series[-1]["value"], "time_series": series}
        return {value_key: None, "time_series": []}

    def _parse_pod_vector(result, value_key):
        items = result.get("result", {}).get("data", {}).get("result") or []
        parsed = []
        for item in items:
            metric = item.get("metric") or {}
            series = _series_from_values(item.get("values"))
            if not series:
                continue
            parsed.append({
                "pod": metric.get("pod", "unknown"),
                "namespace": metric.get("namespace", namespace or "unknown"),
                value_key: series[-1]["value"],
                "time_series": series,
            })
        parsed.sort(key=lambda item: item.get(value_key) or 0, reverse=True)
        return parsed

    qps = _parse_scalar(query_results["qps"], "qps")
    http_4xx = _parse_scalar(query_results["http_4xx"], "http_4xx_qps")
    http_5xx = _parse_scalar(query_results["http_5xx"], "http_5xx_qps")
    success_rate = _parse_scalar(query_results["success_rate"], "success_rate_percent")
    latency_p95 = _parse_scalar(query_results["latency_p95"], "latency_p95_ms")
    active_connections = _parse_scalar(query_results["active_connections"], "active_connections")
    cpu_by_pod = _parse_pod_vector(query_results["cpu"], "cpu_cores")
    memory_by_pod = _parse_pod_vector(query_results["memory"], "memory_working_set_bytes")

    certificate_check = {"success": False, "skipped": True, "reason": "disabled"}
    if check_certificates:
        certificate_check = cce.get_ingress_tls_certificates(
            region,
            cluster_id,
            access_key,
            secret_key,
            proj_id,
            ingress_namespace,
            cert_expire_warning_days,
        )

    latest_5xx = http_5xx.get("http_5xx_qps")
    latest_success_rate = success_rate.get("success_rate_percent")
    latest_latency = latency_p95.get("latency_p95_ms")
    expired_count = certificate_check.get("expired_count", 0) if certificate_check.get("success") else 0
    expiring_soon_count = certificate_check.get("expiring_soon_count", 0) if certificate_check.get("success") else 0

    status = "normal"
    if (
        (latest_5xx is not None and latest_5xx > 0)
        or (latest_success_rate is not None and latest_success_rate < 99)
        or expired_count > 0
    ):
        status = "critical"
    elif (
        (latest_latency is not None and latest_latency > 1000)
        or (latest_success_rate is not None and latest_success_rate < 99.9)
        or expiring_soon_count > 0
    ):
        status = "warning"

    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "cluster_name": cluster_name,
        "namespace": namespace or "all",
        "pod_regex": pod_regex,
        "ingress_namespace": ingress_namespace or "all",
        "aom_instance_id": aom_instance_id,
        "query_time": time_module.strftime("%Y-%m-%d %H:%M:%S", time_module.localtime()),
        "query_params": {
            "hours": hours,
            "cert_expire_warning_days": cert_expire_warning_days,
            "check_certificates": check_certificates,
        },
        "promql": queries,
        "metrics": {
            "qps": qps,
            "http_4xx": http_4xx,
            "http_5xx": http_5xx,
            "success_rate": success_rate,
            "latency_p95": latency_p95,
            "active_connections": active_connections,
            "cpu_by_pod": cpu_by_pod,
            "memory_by_pod": memory_by_pod,
        },
        "certificate_check": certificate_check,
        "summary": {
            "status": status,
            "qps": qps.get("qps"),
            "http_4xx_qps": http_4xx.get("http_4xx_qps"),
            "http_5xx_qps": latest_5xx,
            "success_rate_percent": latest_success_rate,
            "latency_p95_ms": latest_latency,
            "active_connections": active_connections.get("active_connections"),
            "observed_cpu_pods": len(cpu_by_pod),
            "observed_memory_pods": len(memory_by_pod),
            "expired_certificate_count": expired_count,
            "expiring_soon_certificate_count": expiring_soon_count,
        },
    }

def get_cce_autoscaler_metrics(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    namespace: Optional[str] = "kube-system",
    pod_regex: str = ".*cluster.*autoscaler.*|.*autoscaler.*",
    hpa_namespace: Optional[str] = None,
    hours: int = 1,
    include_hpa: bool = True,
    unschedulable_pods_query: str = None,
    nodes_count_query: str = None,
    scale_up_query: str = None,
    scale_down_query: str = None,
    errors_query: str = None,
    node_groups_query: str = None,
    hpa_current_replicas_query: str = None,
    hpa_desired_replicas_query: str = None,
    cpu_query: str = None,
    memory_query: str = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Query Cluster Autoscaler and HPA metrics from the CCE cluster AOM Prometheus instance."""
    import time as time_module

    access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    cluster_name = cluster_id
    try:
        clusters_result = cce.list_cce_clusters(region, ak, sk, project_id)
        if clusters_result.get("success"):
            for cluster in clusters_result.get("clusters", []):
                if cluster.get("id") == cluster_id:
                    cluster_name = cluster.get("name", cluster_id)
                    break
    except Exception:
        pass

    aom_result = _get_aom_instance(region, cluster_id, ak, sk, project_id)
    if not aom_result.get("success"):
        return {
            "success": False,
            "error": aom_result.get("error", "AOM instance not found"),
            "error_type": aom_result.get("error_type"),
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
        }
    aom_instance_id = aom_result.get("aom_instance_id")

    selector_parts = [_cluster_label(cluster_id)]
    if namespace:
        selector_parts.append(f'namespace="{namespace}"')
    if pod_regex:
        selector_parts.append(f'pod=~"{pod_regex}"')
    selector = ",".join(selector_parts)
    container_selector = ",".join(["image!=\"\""] + selector_parts)
    hpa_selector = _label_selector(_cluster_label(cluster_id), f'namespace="{hpa_namespace}"' if hpa_namespace else "")

    def _selector(labels: str = "") -> str:
        merged = ",".join(part for part in [selector, labels] if part)
        return "{" + merged + "}"

    def _hpa_selector() -> str:
        return "{" + hpa_selector + "}" if hpa_selector else ""

    if unschedulable_pods_query is None:
        unschedulable_pods_query = f"sum(cluster_autoscaler_unschedulable_pods_count{_selector()})"
    if nodes_count_query is None:
        nodes_count_query = f"sum by (state) (cluster_autoscaler_nodes_count{_selector()})"
    if scale_up_query is None:
        scale_up_query = f"sum(increase(cluster_autoscaler_scaled_up_nodes_total{_selector()}[1h]))"
    if scale_down_query is None:
        scale_down_query = f"sum(increase(cluster_autoscaler_scaled_down_nodes_total{_selector()}[1h]))"
    if errors_query is None:
        errors_query = f"sum(increase(cluster_autoscaler_errors_total{_selector()}[1h]))"
    if node_groups_query is None:
        node_groups_query = f"sum(cluster_autoscaler_node_groups_count{_selector()})"
    if hpa_current_replicas_query is None:
        hpa_current_replicas_query = (
            f"sum by (namespace, horizontalpodautoscaler) "
            f"(kube_horizontalpodautoscaler_status_current_replicas{_hpa_selector()})"
        )
    if hpa_desired_replicas_query is None:
        hpa_desired_replicas_query = (
            f"sum by (namespace, horizontalpodautoscaler) "
            f"(kube_horizontalpodautoscaler_status_desired_replicas{_hpa_selector()})"
        )
    if cpu_query is None:
        cpu_query = (
            f"sum by (pod, namespace) "
            f"(rate(container_cpu_usage_seconds_total{{{container_selector}}}[5m]))"
        )
    if memory_query is None:
        memory_query = (
            f"sum by (pod, namespace) "
            f"(container_memory_working_set_bytes{{{container_selector}}})"
        )

    queries = {
        "unschedulable_pods": unschedulable_pods_query,
        "nodes_count": nodes_count_query,
        "scale_up": scale_up_query,
        "scale_down": scale_down_query,
        "errors": errors_query,
        "node_groups": node_groups_query,
        "cpu": cpu_query,
        "memory": memory_query,
    }
    if include_hpa:
        queries["hpa_current_replicas"] = hpa_current_replicas_query
        queries["hpa_desired_replicas"] = hpa_desired_replicas_query

    query_results = {
        name: aom.get_aom_prom_metrics_http(
            region,
            aom_instance_id,
            query,
            hours=hours,
            ak=access_key,
            sk=secret_key,
            project_id=proj_id,
            security_token=security_token,
        )
        for name, query in queries.items()
    }

    failed_queries = {
        name: result.get("error", "AOM query failed")
        for name, result in query_results.items()
        if not result.get("success")
    }
    if failed_queries:
        return {
            "success": False,
            "error": "AOM Prometheus query failed",
            "failed_queries": failed_queries,
            "region": region,
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "aom_instance_id": aom_instance_id,
            "promql": queries,
        }

    def _series_from_values(values):
        import math

        series = []
        for ts, val in values or []:
            try:
                timestamp = int(float(ts))
                value = float(val)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(value):
                continue
            series.append({
                "timestamp": timestamp,
                "time": time_module.strftime("%Y-%m-%d %H:%M:%S", time_module.localtime(timestamp)),
                "value": round(value, 4),
            })
        return series

    def _parse_scalar(result, value_key):
        items = result.get("result", {}).get("data", {}).get("result") or []
        for item in items:
            series = _series_from_values(item.get("values"))
            if series:
                return {value_key: series[-1]["value"], "time_series": series}
        return {value_key: None, "time_series": []}

    def _parse_labeled_vector(result, value_key, labels):
        items = result.get("result", {}).get("data", {}).get("result") or []
        parsed = []
        for item in items:
            metric = item.get("metric") or {}
            series = _series_from_values(item.get("values"))
            if not series:
                continue
            row = {label: metric.get(label, "unknown") for label in labels}
            row[value_key] = series[-1]["value"]
            row["time_series"] = series
            parsed.append(row)
        parsed.sort(key=lambda item: item.get(value_key) or 0, reverse=True)
        return parsed

    unschedulable_pods = _parse_scalar(query_results["unschedulable_pods"], "unschedulable_pods")
    scale_up = _parse_scalar(query_results["scale_up"], "scaled_up_nodes")
    scale_down = _parse_scalar(query_results["scale_down"], "scaled_down_nodes")
    errors = _parse_scalar(query_results["errors"], "errors")
    node_groups = _parse_scalar(query_results["node_groups"], "node_groups")
    nodes_count = _parse_labeled_vector(query_results["nodes_count"], "nodes", ["state"])
    cpu_by_pod = _parse_labeled_vector(query_results["cpu"], "cpu_cores", ["namespace", "pod"])
    memory_by_pod = _parse_labeled_vector(query_results["memory"], "memory_working_set_bytes", ["namespace", "pod"])

    hpa_current = []
    hpa_desired = []
    hpa_status = []
    if include_hpa:
        hpa_current = _parse_labeled_vector(
            query_results["hpa_current_replicas"],
            "current_replicas",
            ["namespace", "horizontalpodautoscaler"],
        )
        hpa_desired = _parse_labeled_vector(
            query_results["hpa_desired_replicas"],
            "desired_replicas",
            ["namespace", "horizontalpodautoscaler"],
        )
        desired_map = {
            (item.get("namespace"), item.get("horizontalpodautoscaler")): item.get("desired_replicas")
            for item in hpa_desired
        }
        for item in hpa_current:
            key = (item.get("namespace"), item.get("horizontalpodautoscaler"))
            desired = desired_map.get(key)
            current = item.get("current_replicas")
            hpa_status.append({
                "namespace": key[0],
                "horizontalpodautoscaler": key[1],
                "current_replicas": current,
                "desired_replicas": desired,
                "replica_gap": round((desired or 0) - (current or 0), 4) if desired is not None and current is not None else None,
            })

    latest_unschedulable = unschedulable_pods.get("unschedulable_pods")
    latest_errors = errors.get("errors")
    latest_scaled_up = scale_up.get("scaled_up_nodes")
    latest_scaled_down = scale_down.get("scaled_down_nodes")
    hpa_gap_count = len([item for item in hpa_status if item.get("replica_gap") not in (None, 0)])

    status = "normal"
    if (latest_errors is not None and latest_errors > 0) or (latest_unschedulable is not None and latest_unschedulable > 0):
        status = "critical"
    elif (latest_scaled_up is not None and latest_scaled_up > 0) or (latest_scaled_down is not None and latest_scaled_down > 0) or hpa_gap_count > 0:
        status = "warning"

    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "cluster_name": cluster_name,
        "namespace": namespace or "all",
        "pod_regex": pod_regex,
        "hpa_namespace": hpa_namespace or "all",
        "aom_instance_id": aom_instance_id,
        "query_time": time_module.strftime("%Y-%m-%d %H:%M:%S", time_module.localtime()),
        "query_params": {"hours": hours, "include_hpa": include_hpa},
        "promql": queries,
        "metrics": {
            "unschedulable_pods": unschedulable_pods,
            "nodes_count": nodes_count,
            "scale_up": scale_up,
            "scale_down": scale_down,
            "errors": errors,
            "node_groups": node_groups,
            "cpu_by_pod": cpu_by_pod,
            "memory_by_pod": memory_by_pod,
            "hpa_current_replicas": hpa_current,
            "hpa_desired_replicas": hpa_desired,
            "hpa_status": hpa_status,
        },
        "summary": {
            "status": status,
            "unschedulable_pods": latest_unschedulable,
            "scaled_up_nodes": latest_scaled_up,
            "scaled_down_nodes": latest_scaled_down,
            "errors": latest_errors,
            "node_groups": node_groups.get("node_groups"),
            "node_state_count": nodes_count,
            "observed_autoscaler_pods": len(cpu_by_pod),
            "hpa_count": len(hpa_status),
            "hpa_replica_gap_count": hpa_gap_count,
        },
    }

def _get_cce_control_plane_metrics(
    region: str,
    cluster_id: str,
    component: str,
    default_namespace: Optional[str],
    default_pod_regex: str,
    queries: Dict[str, str],
    vector_labels: Dict[str, list],
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    namespace: Optional[str] = None,
    pod_regex: Optional[str] = None,
    hours: int = 1,
    security_token: Optional[str] = None,
    metric_selector: Optional[str] = None,
) -> Dict[str, Any]:
    """Shared AOM Prometheus query path for Kubernetes control-plane components."""
    import time as time_module

    access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    cluster_name = cluster_id
    try:
        clusters_result = cce.list_cce_clusters(region, ak, sk, project_id)
        if clusters_result.get("success"):
            for cluster in clusters_result.get("clusters", []):
                if cluster.get("id") == cluster_id:
                    cluster_name = cluster.get("name", cluster_id)
                    break
    except Exception:
        pass

    aom_result = _get_aom_instance(region, cluster_id, ak, sk, project_id)
    if not aom_result.get("success"):
        return {
            "success": False,
            "error": aom_result.get("error", "AOM instance not found"),
            "error_type": aom_result.get("error_type"),
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
        }
    aom_instance_id = aom_result.get("aom_instance_id")

    namespace = default_namespace if namespace is None else namespace
    pod_regex = pod_regex or default_pod_regex
    if metric_selector is not None:
        selector = metric_selector
    else:
        selector_parts = []
        if namespace:
            selector_parts.append(f'namespace="{namespace}"')
        if pod_regex:
            selector_parts.append(f'pod=~"{pod_regex}"')
        selector = ",".join(selector_parts)
    container_selector = ",".join(["image!=\"\""] + ([selector] if metric_selector is not None and selector else selector_parts))

    def _selector(extra: str = "") -> str:
        labels = ",".join(part for part in [selector, extra] if part)
        return "{" + labels + "}"

    rendered_queries = {}
    replacements = {
        "{selector}": _selector(),
        "{selector_5xx}": _selector('status=~"5.."'),
        "{selector_non_watch_connect}": _selector('verb!~"WATCH|CONNECT"'),
        "{container_selector}": container_selector,
    }
    for name, query in queries.items():
        rendered = query
        for placeholder, value in replacements.items():
            rendered = rendered.replace(placeholder, value)
        rendered_queries[name] = rendered

    query_results = {
        name: aom.get_aom_prom_metrics_http(
            region,
            aom_instance_id,
            query,
            hours=hours,
            ak=access_key,
            sk=secret_key,
            project_id=proj_id,
            security_token=security_token,
        )
        for name, query in rendered_queries.items()
    }

    failed_queries = {
        name: result.get("error", "AOM query failed")
        for name, result in query_results.items()
        if not result.get("success")
    }
    if failed_queries:
        return {
            "success": False,
            "error": "AOM Prometheus query failed",
            "failed_queries": failed_queries,
            "region": region,
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "aom_instance_id": aom_instance_id,
            "promql": rendered_queries,
        }

    def _series_from_values(values):
        import math

        series = []
        for ts, val in values or []:
            try:
                timestamp = int(float(ts))
                value = float(val)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(value):
                continue
            series.append({
                "timestamp": timestamp,
                "time": time_module.strftime("%Y-%m-%d %H:%M:%S", time_module.localtime(timestamp)),
                "value": round(value, 4),
            })
        return series

    def _parse_scalar(result, value_key):
        items = result.get("result", {}).get("data", {}).get("result") or []
        for item in items:
            series = _series_from_values(item.get("values"))
            if series:
                return {value_key: series[-1]["value"], "time_series": series}
        return {value_key: None, "time_series": []}

    def _parse_vector(result, value_key, labels):
        parsed = []
        items = result.get("result", {}).get("data", {}).get("result") or []
        for item in items:
            metric = item.get("metric") or {}
            series = _series_from_values(item.get("values"))
            if not series:
                continue
            row = {label: metric.get(label, "unknown") for label in labels}
            row[value_key] = series[-1]["value"]
            row["time_series"] = series
            parsed.append(row)
        parsed.sort(key=lambda item: item.get(value_key) or 0, reverse=True)
        return parsed

    metrics = {}
    for name, result in query_results.items():
        if name in vector_labels:
            metrics[name] = _parse_vector(result, name, vector_labels[name])
        else:
            metrics[name] = _parse_scalar(result, name)

    summary = {"status": "normal"}
    scalar_values = {
        name: value.get(name)
        for name, value in metrics.items()
        if isinstance(value, dict)
    }
    if (
        any((value or 0) > 0 for key, value in scalar_values.items() if key in {"errors", "error_rate_percent", "leader_changes", "failed_proposals"})
        or (scalar_values.get("has_leader") is not None and scalar_values.get("has_leader") < 1)
    ):
        summary["status"] = "critical"
    elif (
        any((value or 0) > 0 for key, value in scalar_values.items() if key in {"queue_depth", "pending_pods"})
        or any((value or 0) > 1000 for key, value in scalar_values.items() if key.endswith("_p95_ms"))
    ):
        summary["status"] = "warning"
    summary.update(scalar_values)

    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "cluster_name": cluster_name,
        "component": component,
        "namespace": namespace or "all",
        "pod_regex": pod_regex,
        "metric_selector": selector,
        "aom_instance_id": aom_instance_id,
        "query_time": time_module.strftime("%Y-%m-%d %H:%M:%S", time_module.localtime()),
        "query_params": {"hours": hours},
        "promql": rendered_queries,
        "metrics": metrics,
        "summary": summary,
    }


def get_cce_apiserver_metrics(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    namespace: Optional[str] = "kube-system",
    pod_regex: str = ".*kube-apiserver.*|.*apiserver.*",
    hours: int = 1,
    security_token: Optional[str] = None,
    metric_selector: Optional[str] = None,
) -> Dict[str, Any]:
    metric_selector = metric_selector or f'cluster="{cluster_id}",component="apiserver"'
    queries = {
        "qps": "sum(rate(apiserver_request_total{selector}[5m]))",
        "error_rate_percent": "sum(rate(apiserver_request_total{selector_5xx}[5m])) / sum(rate(apiserver_request_total{selector}[5m])) * 100",
        "latency_p95_ms": "histogram_quantile(0.95, sum by (le) (rate(apiserver_request_duration_seconds_bucket{selector_non_watch_connect}[5m]))) * 1000",
        "latency_p95_by_verb_ms": "histogram_quantile(0.95, sum by (verb, le) (rate(apiserver_request_duration_seconds_bucket{selector}[5m]))) * 1000",
        "inflight_requests": "sum(apiserver_current_inflight_requests{selector})",
    }
    return _get_cce_control_plane_metrics(
        region, cluster_id, "apiserver", None, "", queries,
        {"latency_p95_by_verb_ms": ["verb"]},
        ak, sk, project_id, None, None, hours, security_token, metric_selector,
    )


def get_cce_etcd_metrics(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    namespace: Optional[str] = None,
    pod_regex: str = "",
    hours: int = 1,
    security_token: Optional[str] = None,
    metric_selector: Optional[str] = None,
) -> Dict[str, Any]:
    metric_selector = metric_selector or f'cluster="{cluster_id}"'
    queries = {
        "has_leader": "max(etcd_server_has_leader{selector})",
        "leader_changes": "sum(increase(etcd_server_leader_changes_seen_total{selector}[1h]))",
        "failed_proposals": "sum(increase(etcd_server_proposals_failed_total{selector}[1h]))",
        "db_size_bytes": "max(etcd_mvcc_db_total_size_in_bytes{selector} or etcd_debugging_mvcc_db_total_size_in_bytes{selector})",
        "wal_fsync_p95_ms": "histogram_quantile(0.95, sum by (le) (rate(etcd_disk_wal_fsync_duration_seconds_bucket{selector}[5m]))) * 1000",
        "backend_commit_p95_ms": "histogram_quantile(0.95, sum by (le) (rate(etcd_disk_backend_commit_duration_seconds_bucket{selector}[5m]))) * 1000",
    }
    return _get_cce_control_plane_metrics(
        region, cluster_id, "etcd", None, "", queries,
        {},
        ak, sk, project_id, None, None, hours, security_token, metric_selector,
    )


def get_cce_controller_manager_metrics(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    namespace: Optional[str] = "kube-system",
    pod_regex: str = ".*kube-controller-manager.*|.*controller-manager.*",
    hours: int = 1,
    security_token: Optional[str] = None,
    metric_selector: Optional[str] = None,
) -> Dict[str, Any]:
    metric_selector = metric_selector or f'cluster="{cluster_id}"'
    queries = {
        "queue_depth": "sum(workqueue_depth{selector})",
        "retries": "sum(rate(workqueue_retries_total{selector}[5m]))",
        "adds": "sum(rate(workqueue_adds_total{selector}[5m]))",
        "queue_depth_by_name": "sum by (name) (workqueue_depth{selector})",
        "retries_by_name": "sum by (name) (rate(workqueue_retries_total{selector}[5m]))",
        "adds_by_name": "sum by (name) (rate(workqueue_adds_total{selector}[5m]))",
        "queue_latency_p95_ms": "histogram_quantile(0.95, sum by (le) (rate(workqueue_queue_duration_seconds_bucket{selector}[5m]))) * 1000",
        "work_duration_p95_ms": "histogram_quantile(0.95, sum by (le) (rate(workqueue_work_duration_seconds_bucket{selector}[5m]))) * 1000",
        "queue_latency_p95_by_name_ms": "histogram_quantile(0.95, sum by (name, le) (rate(workqueue_queue_duration_seconds_bucket{selector}[5m]))) * 1000",
        "work_duration_p95_by_name_ms": "histogram_quantile(0.95, sum by (name, le) (rate(workqueue_work_duration_seconds_bucket{selector}[5m]))) * 1000",
    }
    return _get_cce_control_plane_metrics(
        region, cluster_id, "controller-manager", None, "", queries,
        {
            "queue_depth_by_name": ["name"],
            "retries_by_name": ["name"],
            "adds_by_name": ["name"],
            "queue_latency_p95_by_name_ms": ["name"],
            "work_duration_p95_by_name_ms": ["name"],
        },
        ak, sk, project_id, None, None, hours, security_token, metric_selector,
    )


def get_cce_scheduler_metrics(
    region: str,
    cluster_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    namespace: Optional[str] = "kube-system",
    pod_regex: str = ".*kube-scheduler.*|.*scheduler.*",
    hours: int = 1,
    security_token: Optional[str] = None,
    metric_selector: Optional[str] = None,
) -> Dict[str, Any]:
    metric_selector = metric_selector or f'cluster="{cluster_id}"'
    queries = {
        "scheduling_attempts": "sum(rate(scheduler_schedule_attempts_total{selector}[5m]))",
        "attempts_by_result": "sum by (result) (rate(scheduler_schedule_attempts_total{selector}[5m]))",
        "attempts_by_profile_result": "sum by (profile, result) (rate(scheduler_schedule_attempts_total{selector}[5m]))",
        "pending_pods": "sum(scheduler_pending_pods{selector})",
        "pending_pods_by_queue": "sum by (queue) (scheduler_pending_pods{selector})",
        "scheduling_latency_p95_ms": "histogram_quantile(0.95, sum by (le) (rate(scheduler_scheduling_attempt_duration_seconds_bucket{selector}[5m]))) * 1000",
        "scheduling_latency_p95_by_result_ms": "histogram_quantile(0.95, sum by (result, le) (rate(scheduler_scheduling_attempt_duration_seconds_bucket{selector}[5m]))) * 1000",
        "scheduling_latency_p95_by_profile_result_ms": "histogram_quantile(0.95, sum by (profile, result, le) (rate(scheduler_scheduling_attempt_duration_seconds_bucket{selector}[5m]))) * 1000",
        "queue_incoming_pods": "sum(rate(scheduler_queue_incoming_pods_total{selector}[5m]))",
        "queue_incoming_pods_by_queue": "sum by (queue) (rate(scheduler_queue_incoming_pods_total{selector}[5m]))",
    }
    return _get_cce_control_plane_metrics(
        region, cluster_id, "scheduler", None, "", queries,
        {
            "attempts_by_result": ["result"],
            "attempts_by_profile_result": ["profile", "result"],
            "pending_pods_by_queue": ["queue"],
            "scheduling_latency_p95_by_result_ms": ["result"],
            "scheduling_latency_p95_by_profile_result_ms": ["profile", "result"],
            "queue_incoming_pods_by_queue": ["queue"],
        },
        ak, sk, project_id, None, None, hours, security_token, metric_selector,
    )

def get_cce_node_gpu_metrics(
    region: str,
    cluster_id: str,
    node_ip: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    hours: int = 1,
    gpu_selector: Optional[str] = None,
    utilization_query: str = None,
    memory_utilization_query: str = None,
    memory_used_query: str = None,
    memory_total_query: str = None,
    memory_free_query: str = None,
    temperature_query: str = None,
    power_usage_query: str = None,
    schedule_policy_query: str = None,
    xgpu_memory_total_query: str = None,
    xgpu_memory_used_query: str = None,
    xgpu_core_total_query: str = None,
    xgpu_core_used_query: str = None,
    xgpu_device_health_query: str = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Query NVIDIA GPU and xGPU metrics for a single CCE node."""
    import time as time_module

    access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}
    if not node_ip:
        return {"success": False, "error": "node_ip is required"}

    cluster_name = cluster_id
    node_name = node_ip
    try:
        clusters_result = cce.list_cce_clusters(region, ak, sk, project_id)
        if clusters_result.get("success"):
            for cluster in clusters_result.get("clusters", []):
                if cluster.get("id") == cluster_id:
                    cluster_name = cluster.get("name", cluster_id)
                    break
    except Exception:
        pass

    aom_result = _get_aom_instance(region, cluster_id, ak, sk, project_id)
    if not aom_result.get("success"):
        return {
            "success": False,
            "error": aom_result.get("error", "AOM instance not found"),
            "error_type": aom_result.get("error_type"),
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
        }
    aom_instance_id = aom_result.get("aom_instance_id")

    if gpu_selector is None:
        node_regex = "|".join(_prom_regex_literal(value) for value in sorted({node_ip, node_name}) if value)
        gpu_selector = _label_selector(_cluster_label(cluster_id), f'node=~"{node_regex}"')
    selector = "{" + gpu_selector + "}" if gpu_selector else ""

    if utilization_query is None:
        utilization_query = f"cce_gpu_utilization{selector}"
    if memory_utilization_query is None:
        memory_utilization_query = f"cce_gpu_memory_utilization{selector}"
    if memory_used_query is None:
        memory_used_query = f"cce_gpu_memory_used{selector}"
    if memory_total_query is None:
        memory_total_query = f"cce_gpu_memory_total{selector}"
    if memory_free_query is None:
        memory_free_query = f"cce_gpu_memory_free{selector}"
    if temperature_query is None:
        temperature_query = f"cce_gpu_temperature{selector}"
    if power_usage_query is None:
        power_usage_query = f"cce_gpu_power_usage{selector}"
    if schedule_policy_query is None:
        schedule_policy_query = f"gpu_schedule_policy{selector}"
    if xgpu_memory_total_query is None:
        xgpu_memory_total_query = f"xgpu_memory_total{selector}"
    if xgpu_memory_used_query is None:
        xgpu_memory_used_query = f"xgpu_memory_used{selector}"
    if xgpu_core_total_query is None:
        xgpu_core_total_query = f"xgpu_core_percentage_total{selector}"
    if xgpu_core_used_query is None:
        xgpu_core_used_query = f"xgpu_core_percentage_used{selector}"
    if xgpu_device_health_query is None:
        xgpu_device_health_query = f"xgpu_device_health{selector}"

    queries = {
        "gpu_utilization": utilization_query,
        "gpu_memory_utilization": memory_utilization_query,
        "gpu_memory_used": memory_used_query,
        "gpu_memory_total": memory_total_query,
        "gpu_memory_free": memory_free_query,
        "gpu_temperature": temperature_query,
        "gpu_power_usage": power_usage_query,
        "gpu_schedule_policy": schedule_policy_query,
        "xgpu_memory_total": xgpu_memory_total_query,
        "xgpu_memory_used": xgpu_memory_used_query,
        "xgpu_core_total": xgpu_core_total_query,
        "xgpu_core_used": xgpu_core_used_query,
        "xgpu_device_health": xgpu_device_health_query,
    }
    query_results = {
        name: aom.get_aom_prom_metrics_http(
            region,
            aom_instance_id,
            query,
            hours=hours,
            ak=access_key,
            sk=secret_key,
            project_id=proj_id,
            security_token=security_token,
        )
        for name, query in queries.items()
    }

    failed_queries = {
        name: result.get("error", "AOM query failed")
        for name, result in query_results.items()
        if not result.get("success")
    }
    if failed_queries:
        return {
            "success": False,
            "error": "AOM Prometheus query failed",
            "failed_queries": failed_queries,
            "region": region,
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "node_ip": node_ip,
            "node_name": node_name,
            "aom_instance_id": aom_instance_id,
            "promql": queries,
        }

    def _series_from_values(values):
        import math

        series = []
        for ts, val in values or []:
            try:
                timestamp = int(float(ts))
                value = float(val)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(value):
                continue
            series.append({
                "timestamp": timestamp,
                "time": time_module.strftime("%Y-%m-%d %H:%M:%S", time_module.localtime(timestamp)),
                "value": round(value, 4),
            })
        return series

    def _parse_vector(result, value_key):
        items = result.get("result", {}).get("data", {}).get("result") or []
        parsed = []
        for item in items:
            metric = item.get("metric") or {}
            series = _series_from_values(item.get("values"))
            if not series:
                continue
            parsed.append({
                "labels": metric,
                value_key: series[-1]["value"],
                "time_series": series,
            })
        parsed.sort(key=lambda item: item.get(value_key) or 0, reverse=True)
        return parsed

    metrics = {name: _parse_vector(result, name) for name, result in query_results.items()}

    def _latest_values(name):
        return [item.get(name) for item in metrics.get(name, []) if item.get(name) is not None]

    def _max_value(name):
        values = _latest_values(name)
        return max(values) if values else None

    def _sum_value(name):
        values = _latest_values(name)
        return round(sum(values), 4) if values else None

    schedule_policy_values = _latest_values("gpu_schedule_policy")
    xgpu_metric_count = sum(len(metrics.get(name, [])) for name in [
        "xgpu_memory_total",
        "xgpu_memory_used",
        "xgpu_core_total",
        "xgpu_core_used",
        "xgpu_device_health",
    ])
    xgpu_detected = xgpu_metric_count > 0 or any(value in (0, 1) for value in schedule_policy_values)
    unhealthy_xgpu_count = len([value for value in _latest_values("xgpu_device_health") if value == 1])
    gpu_card_count = max(len(metrics.get("gpu_utilization", [])), len(metrics.get("gpu_memory_total", [])))

    status = "normal"
    if unhealthy_xgpu_count > 0 or (_max_value("gpu_temperature") is not None and _max_value("gpu_temperature") >= 85):
        status = "critical"
    elif (_max_value("gpu_utilization") is not None and _max_value("gpu_utilization") >= 90) or (
        _max_value("gpu_memory_utilization") is not None and _max_value("gpu_memory_utilization") >= 90
    ):
        status = "warning"

    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "cluster_name": cluster_name,
        "node_ip": node_ip,
        "node_name": node_name,
        "gpu_selector": gpu_selector,
        "aom_instance_id": aom_instance_id,
        "query_time": time_module.strftime("%Y-%m-%d %H:%M:%S", time_module.localtime()),
        "query_params": {"hours": hours},
        "promql": queries,
        "metrics": metrics,
        "summary": {
            "status": status,
            "is_gpu_node": gpu_card_count > 0,
            "gpu_card_count": gpu_card_count,
            "max_gpu_utilization_percent": _max_value("gpu_utilization"),
            "max_gpu_memory_utilization_percent": _max_value("gpu_memory_utilization"),
            "gpu_memory_total_bytes": _sum_value("gpu_memory_total"),
            "gpu_memory_used_bytes": _sum_value("gpu_memory_used"),
            "max_gpu_temperature": _max_value("gpu_temperature"),
            "max_gpu_power_usage_milliwatt": _max_value("gpu_power_usage"),
            "xgpu_detected": xgpu_detected,
            "xgpu_metric_count": xgpu_metric_count,
            "unhealthy_xgpu_count": unhealthy_xgpu_count,
            "gpu_schedule_policy_values": schedule_policy_values,
        },
    }

def get_cce_pod_gpu_metrics(
    region: str,
    cluster_id: str,
    pod_name: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    namespace: str = None,
    hours: int = 1,
    gpu_selector: Optional[str] = None,
    utilization_query: str = None,
    memory_utilization_query: str = None,
    memory_used_query: str = None,
    memory_total_query: str = None,
    memory_free_query: str = None,
    schedule_policy_query: str = None,
    xgpu_memory_total_query: str = None,
    xgpu_memory_used_query: str = None,
    xgpu_core_total_query: str = None,
    xgpu_core_used_query: str = None,
    xgpu_device_health_query: str = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Query GPU and xGPU metrics for a single CCE Pod."""
    import time as time_module

    access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)
    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}
    if not pod_name:
        return {"success": False, "error": "pod_name is required"}

    cluster_name = cluster_id
    try:
        clusters_result = cce.list_cce_clusters(region, ak, sk, project_id)
        if clusters_result.get("success"):
            for cluster in clusters_result.get("clusters", []):
                if cluster.get("id") == cluster_id:
                    cluster_name = cluster.get("name", cluster_id)
                    break
    except Exception:
        pass

    aom_result = _get_aom_instance(region, cluster_id, ak, sk, project_id)
    if not aom_result.get("success"):
        return {
            "success": False,
            "error": aom_result.get("error", "AOM instance not found"),
            "error_type": aom_result.get("error_type"),
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "pod_name": pod_name,
            "namespace": namespace,
        }
    aom_instance_id = aom_result.get("aom_instance_id")

    if gpu_selector is None:
        selector_parts = [_cluster_label(cluster_id), f'pod="{pod_name}"']
        if namespace:
            selector_parts.append(f'namespace="{namespace}"')
        gpu_selector = ",".join(selector_parts)
    selector = "{" + gpu_selector + "}" if gpu_selector else ""

    if utilization_query is None:
        utilization_query = f"cce_gpu_utilization{selector}"
    if memory_utilization_query is None:
        memory_utilization_query = f"cce_gpu_memory_utilization{selector}"
    if memory_used_query is None:
        memory_used_query = f"cce_gpu_memory_used{selector}"
    if memory_total_query is None:
        memory_total_query = f"cce_gpu_memory_total{selector}"
    if memory_free_query is None:
        memory_free_query = f"cce_gpu_memory_free{selector}"
    if schedule_policy_query is None:
        schedule_policy_query = f"gpu_schedule_policy{selector}"
    if xgpu_memory_total_query is None:
        xgpu_memory_total_query = f"xgpu_memory_total{selector}"
    if xgpu_memory_used_query is None:
        xgpu_memory_used_query = f"xgpu_memory_used{selector}"
    if xgpu_core_total_query is None:
        xgpu_core_total_query = f"xgpu_core_percentage_total{selector}"
    if xgpu_core_used_query is None:
        xgpu_core_used_query = f"xgpu_core_percentage_used{selector}"
    if xgpu_device_health_query is None:
        xgpu_device_health_query = f"xgpu_device_health{selector}"

    queries = {
        "gpu_utilization": utilization_query,
        "gpu_memory_utilization": memory_utilization_query,
        "gpu_memory_used": memory_used_query,
        "gpu_memory_total": memory_total_query,
        "gpu_memory_free": memory_free_query,
        "gpu_schedule_policy": schedule_policy_query,
        "xgpu_memory_total": xgpu_memory_total_query,
        "xgpu_memory_used": xgpu_memory_used_query,
        "xgpu_core_total": xgpu_core_total_query,
        "xgpu_core_used": xgpu_core_used_query,
        "xgpu_device_health": xgpu_device_health_query,
    }
    query_results = {
        name: aom.get_aom_prom_metrics_http(
            region,
            aom_instance_id,
            query,
            hours=hours,
            ak=access_key,
            sk=secret_key,
            project_id=proj_id,
            security_token=security_token,
        )
        for name, query in queries.items()
    }

    failed_queries = {
        name: result.get("error", "AOM query failed")
        for name, result in query_results.items()
        if not result.get("success")
    }
    if failed_queries:
        return {
            "success": False,
            "error": "AOM Prometheus query failed",
            "failed_queries": failed_queries,
            "region": region,
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "pod_name": pod_name,
            "namespace": namespace,
            "aom_instance_id": aom_instance_id,
            "promql": queries,
        }

    def _series_from_values(values):
        import math

        series = []
        for ts, val in values or []:
            try:
                timestamp = int(float(ts))
                value = float(val)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(value):
                continue
            series.append({
                "timestamp": timestamp,
                "time": time_module.strftime("%Y-%m-%d %H:%M:%S", time_module.localtime(timestamp)),
                "value": round(value, 4),
            })
        return series

    def _parse_vector(result, value_key):
        items = result.get("result", {}).get("data", {}).get("result") or []
        parsed = []
        for item in items:
            metric = item.get("metric") or {}
            series = _series_from_values(item.get("values"))
            if not series:
                continue
            parsed.append({
                "labels": metric,
                value_key: series[-1]["value"],
                "time_series": series,
            })
        parsed.sort(key=lambda item: item.get(value_key) or 0, reverse=True)
        return parsed

    metrics = {name: _parse_vector(result, name) for name, result in query_results.items()}

    def _latest_values(name):
        return [item.get(name) for item in metrics.get(name, []) if item.get(name) is not None]

    def _max_value(name):
        values = _latest_values(name)
        return max(values) if values else None

    def _sum_value(name):
        values = _latest_values(name)
        return round(sum(values), 4) if values else None

    schedule_policy_values = _latest_values("gpu_schedule_policy")
    xgpu_metric_count = sum(len(metrics.get(name, [])) for name in [
        "xgpu_memory_total",
        "xgpu_memory_used",
        "xgpu_core_total",
        "xgpu_core_used",
        "xgpu_device_health",
    ])
    xgpu_detected = xgpu_metric_count > 0 or any(value in (0, 1) for value in schedule_policy_values)
    unhealthy_xgpu_count = len([value for value in _latest_values("xgpu_device_health") if value == 1])
    gpu_device_count = max(len(metrics.get("gpu_utilization", [])), len(metrics.get("gpu_memory_total", [])))

    status = "normal"
    if unhealthy_xgpu_count > 0:
        status = "critical"
    elif (_max_value("gpu_utilization") is not None and _max_value("gpu_utilization") >= 90) or (
        _max_value("gpu_memory_utilization") is not None and _max_value("gpu_memory_utilization") >= 90
    ):
        status = "warning"

    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "cluster_name": cluster_name,
        "pod_name": pod_name,
        "namespace": namespace,
        "gpu_selector": gpu_selector,
        "aom_instance_id": aom_instance_id,
        "query_time": time_module.strftime("%Y-%m-%d %H:%M:%S", time_module.localtime()),
        "query_params": {"hours": hours},
        "promql": queries,
        "metrics": metrics,
        "summary": {
            "status": status,
            "is_gpu_pod": gpu_device_count > 0 or xgpu_metric_count > 0,
            "gpu_device_count": gpu_device_count,
            "max_gpu_utilization_percent": _max_value("gpu_utilization"),
            "max_gpu_memory_utilization_percent": _max_value("gpu_memory_utilization"),
            "gpu_memory_total_bytes": _sum_value("gpu_memory_total"),
            "gpu_memory_used_bytes": _sum_value("gpu_memory_used"),
            "xgpu_detected": xgpu_detected,
            "xgpu_metric_count": xgpu_metric_count,
            "unhealthy_xgpu_count": unhealthy_xgpu_count,
            "gpu_schedule_policy_values": schedule_policy_values,
        },
    }

def get_cce_node_metrics_topN(region: str, cluster_id: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, top_n: int = 10, hours: int = 1, cpu_query: str = None, memory_query: str = None, disk_query: str = None, security_token: Optional[str] = None) -> Dict[str, Any]:
    """获取 CCE 集群节点监控数据

    自动获取 AOM 实例并执行节点 CPU/内存/磁盘监控查询，返回 Top N 数据。

    Args:
        region: 华为云区域 (如 cn-north-4)
        cluster_id: CCE 集群 ID
        ak: Access Key ID (可选)
        sk: Secret Access Key (可选)
        project_id: Project ID (可选)
        top_n: 返回 Top N 数据 (默认 10)
        hours: 查询时间范围（小时）(默认 1)
        cpu_query: 自定义 CPU PromQL (可选)
        memory_query: 自定义内存 PromQL (可选)
        disk_query: 自定义磁盘 PromQL (可选)

    Returns:
        Dict with success status and node metrics data
    """
    import time as time_module

    access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)

    if not cluster_id:
        return {"success": False, "error": "cluster_id is required"}

    # ========== 1. 获取集群名称 ==========
    cluster_name = cluster_id
    try:
        clusters_result = cce.list_cce_clusters(region, ak, sk, project_id)
        if clusters_result.get("success"):
            for c in clusters_result.get("clusters", []):
                if c.get("id") == cluster_id:
                    cluster_name = c.get("name", cluster_id)
                    break
    except Exception:
        pass

    # ========== 2. 获取节点信息映射 ==========
    node_info_map = {}  # best-effort CCE node metadata, no Kubernetes API required
    cce_nodes_result = cce.list_cce_cluster_nodes(region, cluster_id, ak, sk, project_id)
    if cce_nodes_result.get("success"):
        for cce_node in cce_nodes_result.get("nodes", []):
            cce_node_name = cce_node.get("name", "")
            if cce_node_name:
                node_info_map[cce_node_name] = {
                    "name": cce_node_name,
                    "cce_name": cce_node_name,
                    "id": cce_node.get("id", ""),
                    "flavor": cce_node.get("flavor", ""),
                    "cce_status": cce_node.get("status", ""),
                }

    # ========== 3. 获取 AOM 实例 ==========
    aom_result = _get_aom_instance(region, cluster_id, ak, sk, project_id)
    if not aom_result.get("success"):
        return {
            "success": False,
            "error": aom_result.get("error", "未找到可用的 AOM 实例"),
            "error_type": aom_result.get("error_type"),
            "cluster_id": cluster_id,
            "cluster_name": cluster_name
        }
    aom_instance_id = aom_result.get("aom_instance_id")

    # ========== 4. 构建 PromQL 查询 ==========
    # 默认 CPU 使用率 PromQL
    if cpu_query is None:
        cpu_query = f"topk({top_n}, 100 - (avg by (instance) (irate(node_cpu_seconds_total{{mode='idle',cluster='{cluster_id}',cluster_name='{cluster_name}'}}[5m])) * 100))"

    # 默认内存使用率 PromQL
    if memory_query is None:
        memory_query = f"topk({top_n}, avg by (instance) ((1 - node_memory_MemAvailable_bytes{{cluster='{cluster_id}',cluster_name='{cluster_name}'}} / node_memory_MemTotal_bytes{{cluster='{cluster_id}',cluster_name='{cluster_name}'}})) * 100)"

    # 默认磁盘使用率 PromQL
    if disk_query is None:
        disk_query = f"topk({top_n}, avg by (instance) ((1 - node_filesystem_avail_bytes{{mountpoint='/',fstype!~'tmpfs|fuse.lxcfs',cluster='{cluster_id}',cluster_name='{cluster_name}'}} / node_filesystem_size_bytes{{mountpoint='/',fstype!~'tmpfs|fuse.lxcfs',cluster='{cluster_id}',cluster_name='{cluster_name}'}})) * 100)"

    # ========== 5. 执行查询 ==========
    cpu_result = aom.get_aom_prom_metrics_http(region, aom_instance_id, cpu_query, hours=hours, ak=access_key, sk=secret_key, project_id=proj_id, security_token=security_token)
    memory_result = aom.get_aom_prom_metrics_http(region, aom_instance_id, memory_query, hours=hours, ak=access_key, sk=secret_key, project_id=proj_id, security_token=security_token)
    disk_result = aom.get_aom_prom_metrics_http(region, aom_instance_id, disk_query, hours=hours, ak=access_key, sk=secret_key, project_id=proj_id, security_token=security_token)
    failed_queries = {
        name: result.get("error", "AOM query failed")
        for name, result in {"cpu": cpu_result, "memory": memory_result, "disk": disk_result}.items()
        if not result.get("success")
    }
    if failed_queries:
        return {
            "success": False,
            "error": "AOM Prometheus query failed",
            "failed_queries": failed_queries,
            "region": region,
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "aom_instance_id": aom_instance_id,
            "promql": {
                "cpu": cpu_query,
                "memory": memory_query,
                "disk": disk_query,
            },
        }

    # ========== 6. 解析结果 ==========
    def parse_node_result(result, metric_name):
        """解析节点监控结果"""
        metrics = []
        if result.get("success") and result.get("result", {}).get("data", {}).get("result"):
            for item in result["result"]["data"]["result"]:
                metric = item.get("metric", {})
                values = item.get("values", [])
                if values:
                    try:
                        latest_value = float(values[-1][1])
                        instance = metric.get("instance", "unknown")
                        # 提取 IP 地址
                        instance_ip = instance.split(":")[0] if ":" in instance else instance

                        # 获取节点信息，优先使用 hcloud CCE 节点列表做 best-effort 匹配
                        node_info = node_info_map.get(instance_ip, {})
                        if not node_info:
                            for cce_node_name, cce_node_info in node_info_map.items():
                                if instance_ip in cce_node_name or cce_node_name.endswith(instance_ip.replace(".", "")):
                                    node_info = cce_node_info
                                    break
                        # 优先使用节点名称，否则使用 IP
                        node_name = node_info.get("name", instance_ip)

                        metrics.append({
                            "instance": instance,
                            "node_ip": instance_ip,
                            "node_name": node_name,
                            "node_id": node_info.get("id", ""),
                            "flavor": node_info.get("flavor", ""),
                            metric_name: round(latest_value, 2),
                            "status": "critical" if latest_value > 80 else "warning" if latest_value > 50 else "normal",
                            "time_series": values  # 保存完整的时序数据
                        })
                    except (ValueError, IndexError):
                        pass
        return metrics

    cpu_metrics = parse_node_result(cpu_result, "cpu_usage_percent")
    memory_metrics = parse_node_result(memory_result, "memory_usage_percent")
    disk_metrics = parse_node_result(disk_result, "disk_usage_percent")

    # 按使用率排序
    cpu_metrics.sort(key=lambda x: x["cpu_usage_percent"], reverse=True)
    memory_metrics.sort(key=lambda x: x["memory_usage_percent"], reverse=True)
    disk_metrics.sort(key=lambda x: x["disk_usage_percent"], reverse=True)

    # 合并所有节点的监控数据
    all_nodes_map = {}
    for m in cpu_metrics:
        key = m["node_ip"]
        all_nodes_map[key] = m
    for m in memory_metrics:
        key = m["node_ip"]
        if key in all_nodes_map:
            all_nodes_map[key]["memory_usage_percent"] = m["memory_usage_percent"]
            all_nodes_map[key]["status"] = "critical" if m["memory_usage_percent"] > 80 else "warning" if m["memory_usage_percent"] > 50 else all_nodes_map[key]["status"]
        else:
            all_nodes_map[key] = m
    for m in disk_metrics:
        key = m["node_ip"]
        if key in all_nodes_map:
            all_nodes_map[key]["disk_usage_percent"] = m["disk_usage_percent"]
            if m["disk_usage_percent"] > 80:
                all_nodes_map[key]["status"] = "critical"
            elif m["disk_usage_percent"] > 50 and all_nodes_map[key]["status"] == "normal":
                all_nodes_map[key]["status"] = "warning"
        else:
            all_nodes_map[key] = m

    # ========== 7. 返回结果 ==========
    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "cluster_name": cluster_name,
        "aom_instance_id": aom_instance_id,
        "inspection_time": time_module.strftime('%Y-%m-%d %H:%M:%S', time_module.localtime()),
        "query_params": {
            "top_n": top_n,
            "hours": hours
        },
        "promql": {
            "cpu": cpu_query,
            "memory": memory_query,
            "disk": disk_query
        },
        "metrics": {
            "cpu_top_n": cpu_metrics[:top_n],
            "memory_top_n": memory_metrics[:top_n],
            "disk_top_n": disk_metrics[:top_n],
            "all_nodes": list(all_nodes_map.values())
        },
        "summary": {
            "total_nodes": len(all_nodes_map),
            "critical_cpu": len([m for m in cpu_metrics if m["status"] == "critical"]),
            "critical_memory": len([m for m in memory_metrics if m["status"] == "critical"]),
            "critical_disk": len([m for m in disk_metrics if m["status"] == "critical"]),
            "warning_cpu": len([m for m in cpu_metrics if m["status"] == "warning"]),
            "warning_memory": len([m for m in memory_metrics if m["status"] == "warning"]),
            "warning_disk": len([m for m in disk_metrics if m["status"] == "warning"])
        }
    }

def get_cce_node_metrics(region: str, cluster_id: str, node_ip: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, hours: int = 1, cpu_query: str = None, memory_query: str = None, disk_query: str = None, security_token: Optional[str] = None) -> Dict[str, Any]:
    """获取指定CCE节点的CPU、内存、磁盘使用率监控时序数据

    Args:
        region: 华为云区域 (如 cn-north-4)
        cluster_id: CCE 集群 ID
        node_ip: 节点IP地址
        ak: Access Key ID (可选)
        sk: Secret Access Key (可选)
        project_id: Project ID (可选)
        hours: 查询时间范围（小时）(默认 1)
        cpu_query: 自定义 CPU PromQL (可选)
        memory_query: 自定义内存 PromQL (可选)
        disk_query: 自定义磁盘 PromQL (可选)

    Returns:
        Dict with success status and specified node metrics time series data
    """
    import time as time_module

    access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)

    if not cluster_id or not node_ip:
        return {"success": False, "error": "cluster_id and node_ip are required"}

    # ========== 1. 获取集群名称 ==========
    cluster_name = cluster_id
    try:
        clusters_result = cce.list_cce_clusters(region, ak, sk, project_id)
        if clusters_result.get("success"):
            for c in clusters_result.get("clusters", []):
                if c.get("id") == cluster_id:
                    cluster_name = c.get("name", cluster_id)
                    break
    except Exception:
        pass

    # ========== 2. 获取节点信息 ==========
    node_info = {}
    cce_nodes_result = cce.list_cce_cluster_nodes(region, cluster_id, ak, sk, project_id)
    if cce_nodes_result.get("success"):
        for cce_node in cce_nodes_result.get("nodes", []):
            cce_node_name = cce_node.get("name", "")
            if node_ip in cce_node_name or cce_node_name.endswith(node_ip.replace(".", "")):
                node_info["cce_name"] = cce_node_name
                node_info["id"] = cce_node.get("id", "")
                node_info["flavor"] = cce_node.get("flavor", "")
                node_info["cce_status"] = cce_node.get("status", "")
                break

    # ========== 3. 获取 AOM 实例 ==========
    aom_result = _get_aom_instance(region, cluster_id, ak, sk, project_id)
    if not aom_result.get("success"):
        return {
            "success": False,
            "error": aom_result.get("error", "未找到可用的 AOM 实例"),
            "error_type": aom_result.get("error_type"),
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "node_ip": node_ip
        }
    aom_instance_id = aom_result.get("aom_instance_id")

    # ========== 4. 构建 PromQL 查询（筛选指定节点IP） ==========
    # 默认 CPU 使用率 PromQL
    if cpu_query is None:
        cpu_query = f"100 - (avg by (instance) (irate(node_cpu_seconds_total{{mode='idle',cluster='{cluster_id}',cluster_name='{cluster_name}',instance=~'{node_ip}.*'}}[5m])) * 100)"

    # 默认内存使用率 PromQL
    if memory_query is None:
        memory_query = f"avg by (instance) ((1 - node_memory_MemAvailable_bytes{{cluster='{cluster_id}',cluster_name='{cluster_name}',instance=~'{node_ip}.*'}} / node_memory_MemTotal_bytes{{cluster='{cluster_id}',cluster_name='{cluster_name}',instance=~'{node_ip}.*'}})) * 100"

    # 默认磁盘使用率 PromQL
    if disk_query is None:
        disk_query = f"avg by (instance) ((1 - node_filesystem_avail_bytes{{mountpoint='/',fstype!~'tmpfs|fuse.lxcfs',cluster='{cluster_id}',cluster_name='{cluster_name}',instance=~'{node_ip}.*'}} / node_filesystem_size_bytes{{mountpoint='/',fstype!~'tmpfs|fuse.lxcfs',cluster='{cluster_id}',cluster_name='{cluster_name}',instance=~'{node_ip}.*'}})) * 100"

    # ========== 5. 执行查询 ==========
    cpu_result = aom.get_aom_prom_metrics_http(region, aom_instance_id, cpu_query, hours=hours, ak=access_key, sk=secret_key, project_id=proj_id, security_token=security_token)
    memory_result = aom.get_aom_prom_metrics_http(region, aom_instance_id, memory_query, hours=hours, ak=access_key, sk=secret_key, project_id=proj_id, security_token=security_token)
    disk_result = aom.get_aom_prom_metrics_http(region, aom_instance_id, disk_query, hours=hours, ak=access_key, sk=secret_key, project_id=proj_id, security_token=security_token)
    failed_queries = {
        name: result.get("error", "AOM query failed")
        for name, result in {"cpu": cpu_result, "memory": memory_result, "disk": disk_result}.items()
        if not result.get("success")
    }
    if failed_queries:
        return {
            "success": False,
            "error": "AOM Prometheus query failed",
            "failed_queries": failed_queries,
            "region": region,
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "node_ip": node_ip,
            "aom_instance_id": aom_instance_id,
            "promql": {
                "cpu": cpu_query,
                "memory": memory_query,
                "disk": disk_query,
            },
        }

    # ========== 6. 解析结果 ==========
    def parse_metric_result(result, metric_name):
        """解析监控结果，返回时序数据"""
        if result.get("success") and result.get("result", {}).get("data", {}).get("result"):
            for item in result["result"]["data"]["result"]:
                values = item.get("values", [])
                if values:
                    time_series = []
                    for ts, val in values:
                        try:
                            time_series.append({
                                "timestamp": int(ts),
                                "time": time_module.strftime('%Y-%m-%d %H:%M:%S', time_module.localtime(int(ts))),
                                "value": round(float(val), 2)
                            })
                        except (ValueError, IndexError):
                            pass
                    if time_series:
                        latest_value = time_series[-1]["value"]
                        return {
                            metric_name: latest_value,
                            "status": "critical" if latest_value > 80 else "warning" if latest_value > 50 else "normal",
                            "time_series": time_series
                        }
        return None

    cpu_data = parse_metric_result(cpu_result, "cpu_usage_percent")
    memory_data = parse_metric_result(memory_result, "memory_usage_percent")
    disk_data = parse_metric_result(disk_result, "disk_usage_percent")

    # ========== 7. 返回结果 ==========
    return {
        "success": True,
        "region": region,
        "cluster_id": cluster_id,
        "cluster_name": cluster_name,
        "node_ip": node_ip,
        "node_info": node_info,
        "aom_instance_id": aom_instance_id,
        "query_time": time_module.strftime('%Y-%m-%d %H:%M:%S', time_module.localtime()),
        "query_params": {
            "hours": hours
        },
        "promql": {
            "cpu": cpu_query,
            "memory": memory_query,
            "disk": disk_query
        },
        "metrics": {
            "cpu": cpu_data,
            "memory": memory_data,
            "disk": disk_data
        }
    }
