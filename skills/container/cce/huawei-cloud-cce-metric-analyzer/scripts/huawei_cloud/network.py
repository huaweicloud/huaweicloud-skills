from .common import *

def list_eip_addresses(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    """List EIP (Elastic IP) addresses in the specified region using hcloud."""
    result = run_hcloud(
        "EIP",
        "ListPublicips/v3",
        region,
        {"limit": limit, "project_id": project_id},
        ak=ak,
        sk=sk,
        project_id=project_id,
    )
    if not result.get("success"):
        return result

    data = result.get("data") or {}
    eips = []
    for eip in data.get("publicips", []) or []:
        bandwidth = eip.get("bandwidth") or {}
        eips.append({
            "id": eip.get("id"),
            "ip_address": eip.get("public_ip_address"),
            "type": eip.get("type"),
            "status": eip.get("status"),
            "bandwidth_id": bandwidth.get("id"),
            "bandwidth_size": bandwidth.get("size"),
            "bandwidth_share_type": bandwidth.get("share_type"),
            "enterprise_project_id": eip.get("enterprise_project_id"),
            "instance_id": eip.get("associate_instance_id"),
            "instance_type": eip.get("associate_instance_type"),
            "created_at": eip.get("created_at"),
            "updated_at": eip.get("updated_at"),
        })

    return {
        "success": True,
        "region": region,
        "action": "list_eip_addresses",
        "source": "hcloud",
        "count": len(eips),
        "eips": eips
    }

def get_eip_metrics(region: str, eip_id: str, hours: int = 1, period: int = 300, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    """获取指定弹性公网IP（EIP）的监控指标"""
    _, _, proj_id = get_credentials(ak, sk, project_id)

    if not eip_id:
        return {
            "success": False,
            "error": "eip_id是必填参数"
        }

    # 校验采样周期
    valid_periods = [300, 1200, 3600]
    if period not in valid_periods:
        period = 300

    # 计算时间范围
    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_time = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp() * 1000)

    # EIP监控指标定义（华为云官方标准指标）
    eip_metrics = {
        "upstream_bandwidth": "出网带宽（bit/s）",
        "downstream_bandwidth": "入网带宽（bit/s）",
        "upstream_bandwidth_usage": "出网带宽使用率（%）",
        "downstream_bandwidth_usage": "入网带宽使用率（%）",
        "upstream_traffic": "出网流量（Byte）",
        "downstream_traffic": "入网流量（Byte）",
        "upstream_packet_rate": "出包速率（个/秒）",
        "downstream_packet_rate": "入包速率（个/秒）",
        "packet_loss_rate": "丢包率（%）"
    }

    try:
        metrics_result = {}
        metric_names = list(eip_metrics.keys())

        for metric_name in metric_names:
            try:
                metric_result = hcloud_show_metric_data(
                    region,
                    "SYS.VPC",
                    metric_name,
                    f"publicip_id,{eip_id}",
                    start_time,
                    end_time,
                    period,
                    "average",
                    ak,
                    sk,
                    proj_id,
                )
                if metric_result.get("success") and metric_result.get("datapoints"):
                    # 格式化数据
                    processed_data = []
                    for point in metric_result["datapoints"]:
                        processed_data.append({
                            "timestamp": point.get("timestamp"),
                            "time": datetime.fromtimestamp(point.get("timestamp")/1000, timezone.utc).strftime('%Y-%m-%d %H:%M:%S') if point.get("timestamp") else None,
                            "average": round(float(point.get("average")), 2) if point.get("average") is not None else None,
                            "max": round(float(point.get("max")), 2) if point.get("max") is not None else None,
                            "min": round(float(point.get("min")), 2) if point.get("min") is not None else None
                        })

                    # 计算最新值
                    latest_value = processed_data[-1]["average"] if processed_data else None

                    metrics_result[metric_name] = {
                        "name_cn": eip_metrics[metric_name],
                        "latest_value": latest_value,
                        "unit": eip_metrics[metric_name].split("（")[1].rstrip("）") if "（" in eip_metrics[metric_name] else "",
                        "time_series": processed_data
                    }
                else:
                    metrics_result[metric_name] = {
                        "name_cn": eip_metrics[metric_name],
                        "latest_value": None,
                        "unit": eip_metrics[metric_name].split("（")[1].rstrip("）") if "（" in eip_metrics[metric_name] else "",
                        "note": "No data available"
                    }
                    if not metric_result.get("success"):
                        metrics_result[metric_name]["error"] = metric_result.get("error")
            except Exception as e:
                metrics_result[metric_name] = {
                    "name_cn": eip_metrics[metric_name],
                    "error": str(e)
                }

        return {
            "success": True,
            "region": region,
            "eip_id": eip_id,
            "source": "hcloud",
            "query_params": {
                "hours": hours,
                "period": period
            },
            "metrics": metrics_result
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"查询EIP监控失败: {str(e)}"
        }

def get_nat_gateway_metrics(region: str, nat_gateway_id: str, hours: int = 1, period: int = 300, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    """获取指定NAT网关的监控指标（带宽、连接数、丢包率等）

    基于官方文档: https://support.huaweicloud.com/usermanual-natgateway/nat_ces_0002.html

    支持的指标:
    - SNAT连接数、SNAT连接数使用率
    - 入/出方向带宽、带宽使用率
    - 入/出方向PPS、入/出方向流量
    - 入/出方向TCP/UDP带宽
    - 各类型丢包数（SNAT连接超限、PPS超限、EIP端口分配超限）
    """
    _, _, proj_id = get_credentials(ak, sk, project_id)

    if not nat_gateway_id:
        return {
            "success": False,
            "error": "nat_gateway_id是必填参数"
        }

    # 校验采样周期
    valid_periods = [300, 1200, 3600]
    if period not in valid_periods:
        period = 300

    # 计算时间范围
    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_time = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp() * 1000)

    # 要查询的指标列表 (基于官方文档: https://support.huaweicloud.com/usermanual-natgateway/nat_ces_0002.html)
    # 公网NAT网关支持的监控指标
    metric_names = [
        "snat_connection",                      # SNAT连接数
        "inbound_bandwidth",                    # 入方向带宽 (bit/s)
        "outbound_bandwidth",                   # 出方向带宽 (bit/s)
        "inbound_pps",                          # 入方向PPS (个/秒)
        "outbound_pps",                         # 出方向PPS (个/秒)
        "inbound_traffic",                      # 入方向流量 (Byte)
        "outbound_traffic",                     # 出方向流量 (Byte)
        "snat_connection_ratio",                 # SNAT连接数使用率 (%)
        "inbound_bandwidth_ratio",               # 入方向带宽使用率 (%)
        "outbound_bandwidth_ratio",              # 出方向带宽使用率 (%)
        "total_inbound_udp_bandwidth",          # 入方向UDP总带宽 (bit/s)
        "total_outbound_udp_bandwidth",         # 出方向UDP总带宽 (bit/s)
        "total_inbound_tcp_bandwidth",          # 入方向TCP总带宽 (bit/s)
        "total_outbound_tcp_bandwidth",         # 出方向TCP总带宽 (bit/s)
        "packets_drop_count_snat_connection_beyond",  # 丢包数(SNAT连接超限)
        "packets_drop_count_pps_beyond",        # 丢包数(PPS超限)
        "packets_drop_count_eip_port_alloc_beyond"   # 丢包数(EIP端口分配超限)
    ]

    # 指标对应的中文描述
    metric_desc = {
        "snat_connection": "SNAT连接数（个）",
        "inbound_bandwidth": "入方向带宽（bit/s）",
        "outbound_bandwidth": "出方向带宽（bit/s）",
        "inbound_pps": "入方向PPS（个/秒）",
        "outbound_pps": "出方向PPS（个/秒）",
        "inbound_traffic": "入方向流量（Byte）",
        "outbound_traffic": "出方向流量（Byte）",
        "snat_connection_ratio": "SNAT连接数使用率（%）",
        "inbound_bandwidth_ratio": "入方向带宽使用率（%）",
        "outbound_bandwidth_ratio": "出方向带宽使用率（%）",
        "total_inbound_udp_bandwidth": "入方向UDP总带宽（bit/s）",
        "total_outbound_udp_bandwidth": "出方向UDP总带宽（bit/s）",
        "total_inbound_tcp_bandwidth": "入方向TCP总带宽（bit/s）",
        "total_outbound_tcp_bandwidth": "出方向TCP总带宽（bit/s）",
        "packets_drop_count_snat_connection_beyond": "丢包数（SNAT连接超限）（个）",
        "packets_drop_count_pps_beyond": "丢包数（PPS超限）（个）",
        "packets_drop_count_eip_port_alloc_beyond": "丢包数（EIP端口分配超限）（个）"
    }

    try:
        metrics_result = {}

        for metric_name in metric_names:
            try:
                metric_result = hcloud_show_metric_data(
                    region,
                    "SYS.NAT",
                    metric_name,
                    f"nat_gateway_id,{nat_gateway_id}",
                    start_time,
                    end_time,
                    period,
                    "average",
                    ak,
                    sk,
                    proj_id,
                )
                if metric_result.get("success") and metric_result.get("datapoints"):
                    # 格式化数据
                    processed_data = []
                    for point in metric_result["datapoints"]:
                        processed_data.append({
                            "timestamp": point.get("timestamp"),
                            "time": datetime.fromtimestamp(point.get("timestamp")/1000, timezone.utc).strftime('%Y-%m-%d %H:%M:%S') if point.get("timestamp") else None,
                            "average": round(float(point.get("average")), 2) if point.get("average") is not None else None,
                            "max": round(float(point.get("max")), 2) if point.get("max") is not None else None,
                            "min": round(float(point.get("min")), 2) if point.get("min") is not None else None
                        })

                    # 计算最新值
                    latest_value = processed_data[-1]["average"] if processed_data else None

                    metrics_result[metric_name] = {
                        "name_cn": metric_desc[metric_name],
                        "latest_value": latest_value,
                        "unit": metric_desc[metric_name].split("（")[1].rstrip("）") if "（" in metric_desc[metric_name] else "",
                        "time_series": processed_data
                    }
                else:
                    metrics_result[metric_name] = {
                        "name_cn": metric_desc[metric_name],
                        "latest_value": None,
                        "unit": metric_desc[metric_name].split("（")[1].rstrip("）") if "（" in metric_desc[metric_name] else "",
                        "note": "No data available"
                    }
                    if not metric_result.get("success"):
                        metrics_result[metric_name]["error"] = metric_result.get("error")
            except Exception as e:
                metrics_result[metric_name] = {
                    "name_cn": metric_desc[metric_name],
                    "error": str(e)
                }

        return {
            "success": True,
            "region": region,
            "nat_gateway_id": nat_gateway_id,
            "source": "hcloud",
            "query_params": {
                "hours": hours,
                "period": period
            },
            "metrics": metrics_result
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"查询NAT网关监控失败: {str(e)}"
        }

def list_nat_gateways(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, limit: int = 100, offset: int = 0, id: str = None, name: str = None, description: str = None, spec: str = None, router_id: str = None, internal_network_id: str = None, status: str = None, admin_state_up: bool = None, created_at: str = None) -> Dict[str, Any]:
    """List NAT gateways in the specified region using hcloud."""
    params = {
        "limit": limit,
        "id": id,
        "name": name,
        "description": description,
        "router_id": router_id,
        "internal_network_id": internal_network_id,
        "admin_state_up": admin_state_up,
        "created_at": created_at,
        "project_id": project_id,
    }
    if offset:
        params["marker"] = offset
    if spec:
        params["spec.1"] = spec
    if status:
        params["status.1"] = status

    result = run_hcloud(
        "NAT",
        "ListNatGateways",
        region,
        params,
        ak=ak,
        sk=sk,
        project_id=project_id,
    )
    if not result.get("success"):
        return result

    data = result.get("data") or {}
    nat_gateways = data.get("nat_gateways", []) or []
    return {
        "success": True,
        "region": region,
        "action": "list_nat_gateways",
        "source": "hcloud",
        "count": len(nat_gateways),
        "nat_gateways": nat_gateways,
        "total_count": data.get("total_count", len(nat_gateways)),
    }
