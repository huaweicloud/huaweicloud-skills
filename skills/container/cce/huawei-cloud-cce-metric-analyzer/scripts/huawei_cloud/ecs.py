from .common import *


def check_ecs_instance_exists(region: str, instance_id: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> tuple:
    """Verify the ECS instance exists via ShowServer before querying CES metrics.

    Returns (exists: bool, error_detail: Optional[str]). When the hcloud call
    itself fails (non-zero exit) the instance is treated as not verifiable and
    the error detail is returned so callers can report a clear reason.
    """
    try:
        result = run_hcloud(
            "ECS",
            "ShowServer",
            region,
            {"server_id": instance_id, "project_id": project_id},
            ak=ak,
            sk=sk,
            project_id=project_id,
        )
    except Exception as e:
        return False, f"查询ECS实例失败: {e}"

    result = normalize_hcloud_result(result)
    if not result.get("success"):
        error = result.get("error", "查询ECS实例失败")
        return False, error

    return True, None


def get_ecs_metrics(region: str, instance_id: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    """Get monitoring metrics for a specific ECS instance."""
    _, _, proj_id = get_credentials(ak, sk, project_id)

    if not instance_id:
        return {
            "success": False,
            "error": "instance_id is required"
        }

    exists, exist_error = check_ecs_instance_exists(region, instance_id, ak, sk)
    if not exists:
        return {
            "success": False,
            "region": region,
            "instance_id": instance_id,
            "source": "hcloud",
            "error": "ECS 实例不存在或资源 ID 错误" if is_resource_not_found_error(exist_error) else f"查询ECS实例失败: {exist_error}",
            "detail": exist_error if is_resource_not_found_error(exist_error) else None,
        }

    try:
        end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_time = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp() * 1000)

        metrics_to_query = [
            "cpu_util",
            "mem_util",
            "disk_util",
            "network_incoming_bytes_rate",
            "network_outgoing_bytes_rate",
            "disk_read_bytes_rate",
            "disk_write_bytes_rate",
        ]

        all_metrics = {}
        metric_errors = {}

        for metric_name in metrics_to_query:
            try:
                metric_result = hcloud_show_metric_data(
                    region,
                    "SYS.ECS",
                    metric_name,
                    f"instance_id,{instance_id}",
                    start_time,
                    end_time,
                    300,
                    "average",
                    ak,
                    sk,
                    proj_id,
                )
                if metric_result.get("success") and metric_result.get("datapoints"):
                    datapoints = []
                    for dp in metric_result["datapoints"]:
                        datapoints.append({
                            "timestamp": dp.get("timestamp"),
                            "average": dp.get("average"),
                            "min": dp.get("min"),
                            "max": dp.get("max"),
                            "unit": dp.get("unit", "")
                        })
                    latest = datapoints[-1] if datapoints else None
                    all_metrics[metric_name] = {
                        "datapoints": datapoints,
                        "latest_value": latest.get("average") if latest else None,
                        "unit": latest.get("unit", "") if latest else ""
                    }
                else:
                    if not metric_result.get("success"):
                        metric_errors[metric_name] = metric_result.get("error", "hcloud metric query failed")
                    all_metrics[metric_name] = {
                        "datapoints": [],
                        "note": "No data available",
                        **({"error": metric_result.get("error")} if not metric_result.get("success") else {}),
                    }

            except Exception as e:
                metric_errors[metric_name] = str(e)
                all_metrics[metric_name] = {"error": str(e)}

        has_datapoints = any(item.get("datapoints") for item in all_metrics.values() if isinstance(item, dict))
        response = {
            "success": not metric_errors or has_datapoints,
            "region": region,
            "instance_id": instance_id,
            "source": "hcloud",
            "time_range": {
                "start": datetime.fromtimestamp(start_time / 1000, tz=timezone.utc).isoformat(),
                "end": datetime.fromtimestamp(end_time / 1000, tz=timezone.utc).isoformat(),
                "period": "5min"
            },
            "metrics": all_metrics
        }
        if metric_errors:
            response["metric_errors"] = metric_errors
            if not has_datapoints:
                response["error"] = "All ECS metric queries failed"
        return response

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
