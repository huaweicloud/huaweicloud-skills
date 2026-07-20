from .common import *

def list_elb_loadbalancers(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, limit: int = 100, marker: str = None) -> Dict[str, Any]:
    """List ELB load balancers in the specified region using hcloud."""
    result = run_hcloud(
        "ELB",
        "ListLoadBalancers",
        region,
        {"limit": limit, "marker": marker, "project_id": project_id},
        ak=ak,
        sk=sk,
        project_id=project_id,
    )
    if not result.get("success"):
        return result

    data = result.get("data") or {}
    loadbalancers = []
    for lb in data.get("loadbalancers", []) or []:
        guaranteed = lb.get("guaranteed")
        provider = lb.get("provider")
        lb_type = lb.get("type")
        l4_flavor_id = lb.get("l4_flavor_id")
        l7_flavor_id = lb.get("l7_flavor_id")
        eips = lb.get("eips") or lb.get("publicips") or []
        eip_address = ""
        eip_info = None
        if eips:
            first_eip = eips[0] or {}
            eip_address = first_eip.get("eip_address") or first_eip.get("public_ip_address") or ""
            eip_info = {
                "eip": eip_address,
                "eip_id": first_eip.get("eip_id") or first_eip.get("id"),
            }

        is_dedicated = (
            guaranteed is True or
            (provider and "vlb" in str(provider).lower()) or
            (lb_type and str(lb_type).lower() == "dedicated") or
            l4_flavor_id is not None or
            l7_flavor_id is not None
        )
        loadbalancers.append({
            "id": lb.get("id"),
            "name": lb.get("name"),
            "type": lb_type,
            "elb_type": "独享型" if is_dedicated else "共享型",
            "guaranteed": guaranteed,
            "provider": provider,
            "l4_flavor_id": l4_flavor_id,
            "l7_flavor_id": l7_flavor_id,
            "provisioning_status": lb.get("provisioning_status"),
            "operating_status": lb.get("operating_status"),
            "vpc_id": lb.get("vpc_id"),
            "vip_address": lb.get("vip_address"),
            "vip_port_id": lb.get("vip_port_id"),
            "eip_address": eip_address,
            "eip_info": eip_info,
            "created_at": lb.get("created_at"),
            "updated_at": lb.get("updated_at"),
        })

    response = {
        "success": True,
        "region": region,
        "action": "list_elb_loadbalancers",
        "source": "hcloud",
        "count": len(loadbalancers),
        "loadbalancers": loadbalancers,
    }
    if data.get("page_info"):
        response["page_info"] = data["page_info"]
    return response


def list_elb_listeners(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, limit: int = 200, marker: str = None) -> Dict[str, Any]:
    """List ELB listeners in the specified region using hcloud."""
    result = run_hcloud(
        "ELB",
        "ListListeners",
        region,
        {"limit": limit, "marker": marker, "project_id": project_id},
        ak=ak,
        sk=sk,
        project_id=project_id,
    )
    if not result.get("success"):
        return result

    data = result.get("data") or {}
    listeners = []
    for listener in data.get("listeners", []) or []:
        lb_ids = []
        for lb_ref in listener.get("loadbalancers", []) or []:
            lb_id = lb_ref.get("id") if isinstance(lb_ref, dict) else lb_ref
            if lb_id:
                lb_ids.append(lb_id)
        if listener.get("loadbalancer_id"):
            lb_ids.append(listener.get("loadbalancer_id"))

        listeners.append({
            "id": listener.get("id"),
            "name": listener.get("name"),
            "description": listener.get("description") or "",
            "protocol": listener.get("protocol"),
            "protocol_port": listener.get("protocol_port"),
            "loadbalancer_ids": sorted(set(lb_ids)),
        })

    response = {
        "success": True,
        "region": region,
        "action": "list_elb_listeners",
        "source": "hcloud",
        "count": len(listeners),
        "listeners": listeners,
    }
    if data.get("page_info"):
        response["page_info"] = data["page_info"]
    return response


def get_elb_metrics(region: str, elb_id: str, hours: int = 1, period: int = 300, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    """获取指定ELB负载均衡的监控指标（自动识别ELB类型，查询对应的四层/七层指标）"""
    _, _, proj_id = get_credentials(ak, sk, project_id)

    if not elb_id:
        return {
            "success": False,
            "error": "elb_id是必填参数"
        }

    # 校验采样周期
    valid_periods = [300, 1200, 3600]
    if period not in valid_periods:
        period = 300

    # 计算时间范围
    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_time = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp() * 1000)

    # ========== 第一步：查询ELB基本信息，判断支持的协议类型 ==========
    try:
        elb_result = run_hcloud(
            "ELB",
            "ShowLoadBalancer",
            region,
            {"loadbalancer_id": elb_id, "project_id": project_id},
            ak=ak,
            sk=sk,
            project_id=project_id,
        )
        if not elb_result.get("success"):
            raise RuntimeError(elb_result.get("error", "failed to query ELB details"))
        elb_info = (elb_result.get("data") or {}).get("loadbalancer") or {}

        elb_name = elb_info.get('name', '')
        elb_type = elb_info.get('l4_flavor_id') and elb_info.get('l7_flavor_id') and "四七层共享型" or \
                   elb_info.get('l4_flavor_id') and "四层独享型" or \
                   elb_info.get('l7_flavor_id') and "七层独享型" or "未知类型"
        support_l4 = bool(elb_info.get('l4_flavor_id'))
        support_l7 = bool(elb_info.get('l7_flavor_id'))

    except Exception as e:
        # 查询ELB信息失败，默认同时查询四七层指标
        support_l4 = True
        support_l7 = True
        elb_name = ""
        elb_type = "未知类型（默认同时查询四七层）"

    # ========== 第二步：根据ELB类型确定要查询的指标 ==========
    # 四层指标定义（华为云官方标准指标）
    l4_metrics = {
        "m1_cps": "并发连接数（个）",
        "m2_act_conn": "活跃连接数（个）",
        "m3_inact_conn": "非活跃连接数（个）",
        "m4_ncps": "新建连接数（次/秒）",
        "m5_in_pps": "流入数据包速率（个/秒）",
        "m6_out_pps": "流出数据包速率（个/秒）",
        "m7_in_Bps": "网络流入速率（Byte/秒）",
        "m8_out_Bps": "网络流出速率（Byte/秒）",
        "m22_in_bandwidth": "入网带宽（bit/秒）",
        "m23_out_bandwidth": "出网带宽（bit/秒）",
        "l4_con_usage": "四层并发连接使用率（%）",
        "l4_in_bps_usage": "四层入带宽使用率（%）",
        "l4_out_bps_usage": "四层出带宽使用率（%）",
        "l4_ncps_usage": "四层新建连接数使用率（%）",
        "m9_abnormal_servers": "异常后端服务器数（个）",
        "ma_normal_servers": "正常后端服务器数（个）",
        "dropped_connections": "丢弃连接速率（次/秒）",
        "dropped_packets": "丢弃数据包速率（个/秒）",
        "dropped_traffic": "丢弃带宽（bit/秒）"
    }

    # 七层指标定义（华为云官方标准指标）
    l7_metrics = {
        "mb_l7_qps": "7层查询速率（QPS，次/秒）",
        "mc_l7_http_2xx": "7层2XX响应状态码速率（个/秒）",
        "md_l7_http_3xx": "7层3XX响应状态码速率（个/秒）",
        "me_l7_http_4xx": "7层4XX响应状态码速率（个/秒）",
        "mf_l7_http_5xx": "7层5XX响应状态码速率（个/秒）",
        "m11_l7_http_404": "7层404响应状态码速率（个/秒）",
        "m12_l7_http_499": "7层499响应状态码速率（个/秒）",
        "m13_l7_http_502": "7层502响应状态码速率（个/秒）",
        "m14_l7_rt": "7层平均响应时间（ms）",
        "m1c_l7_rt_max": "7层最大响应时间（ms）",
        "m1d_l7_rt_min": "7层最小响应时间（ms）",
        "m17_l7_upstream_rt": "7层后端平均响应时间（ms）",
        "l7_con_usage": "7层并发连接使用率（%）",
        "l7_in_bps_usage": "7层入带宽使用率（%）",
        "l7_out_bps_usage": "7层出带宽使用率（%）",
        "l7_ncps_usage": "7层新建连接数使用率（%）",
        "l7_qps_usage": "7层QPS使用率（%）",
        "l7_2xx_ratio": "7层2XX响应占比（%）",
        "l7_4xx_ratio": "7层4XX响应占比（%）",
        "l7_5xx_ratio": "7层5XX响应占比（%）"
    }

    # 动态组合要查询的指标
    metric_desc = {}
    if support_l4:
        metric_desc.update(l4_metrics)
    if support_l7:
        metric_desc.update(l7_metrics)

    if not metric_desc:
        return {
            "success": False,
            "error": "未识别到ELB支持的指标类型"
        }

    try:
        metrics_result = {}

        for metric_name in metric_desc.keys():
            try:
                metric_result = hcloud_show_metric_data(
                    region,
                    "SYS.ELB",
                    metric_name,
                    f"lbaas_instance_id,{elb_id}",
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
            "elb_id": elb_id,
            "source": "hcloud",
            "elb_name": elb_name,
            "elb_type": elb_type,
            "support_protocol": {
                "layer4": support_l4,
                "layer7": support_l7
            },
            "query_params": {
                "hours": hours,
                "period": period
            },
            "metrics": metrics_result
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"查询ELB监控失败: {str(e)}"
        }
