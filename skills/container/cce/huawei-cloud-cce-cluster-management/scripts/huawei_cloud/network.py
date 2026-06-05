from .common import *

def list_vpc_acls(region: str, vpc_id: str = None, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    """List VPC network ACLs (Access Control Lists) using Neutron API"""
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not SDK_AVAILABLE:
        return {
            "success": False,
            "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"
        }

    try:
        client = create_vpc_client(region, access_key, secret_key, proj_id)

        # List firewall groups (ACLs in VPC)
        try:
            request = NeutronListFirewallGroupsRequest()
            response = client.neutron_list_firewall_groups(request)

            acls = []
            if hasattr(response, 'firewall_groups') and response.firewall_groups:
                for acl in response.firewall_groups:
                    acl_info = {
                        "id": acl.id,
                        "name": getattr(acl, 'name', None),
                        "description": getattr(acl, 'description', None),
                        "firewall_policy_id": getattr(acl, 'firewall_policy_id', None),
                        "status": getattr(acl, 'status', None),
                        "admin_state_up": getattr(acl, 'admin_state_up', None),
                        "tags": getattr(acl, 'tags', []),
                        "project_id": getattr(acl, 'project_id', None),
                        "created_at": str(getattr(acl, 'created_at', None)) if getattr(acl, 'created_at', None) else None,
                    }
                    acls.append(acl_info)

            return {
                "success": True,
                "region": region,
                "vpc_id": vpc_id,
                "action": "list_vpc_acls",
                "count": len(acls),
                "acls": acls
            }
        except AttributeError:
            # If neutron API not available, try alternative
            return {
                "success": True,
                "region": region,
                "action": "list_vpc_acls",
                "count": 0,
                "acls": [],
                "note": "VPC ACLs not available or no ACLs configured"
            }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, 'request_id', None)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

def list_eip_addresses(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    """List EIP (Elastic IP) addresses in the specified region"""
    # Auto-fetch project_id if not provided
    access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not proj_id:
        return {
            "success": False,
            "error": "Project ID not found. Please provide project_id parameter or ensure the account has access to the region."
        }

    if not SDK_AVAILABLE:
        return {
            "success": False,
            "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"
        }

    try:
        # 使用EIP SDK获取EIP列表
        client = create_eip_client(region, access_key, secret_key, proj_id)

        request = ListPublicipsRequest()
        request.limit = str(limit)

        response = client.list_publicips(request)

        eips = []
        if hasattr(response, 'publicips') and response.publicips:
            for eip in response.publicips:
                eip_info = {
                    "id": eip.id,
                    "ip_address": getattr(eip, 'public_ip_address', None),
                    "type": getattr(eip, 'type', None),
                    "status": getattr(eip, 'status', None),
                    "bandwidth_size": getattr(eip, 'bandwidth_size', None),
                    "bandwidth_share_type": getattr(eip, 'bandwidth_share_type', None),
                    "enterprise_project_id": getattr(eip, 'enterprise_project_id', None),
                }
                if hasattr(eip, 'private_ip_address'):
                    eip_info["private_ip_address"] = getattr(eip, 'private_ip_address', None)
                if hasattr(eip, 'instance_id'):
                    eip_info["instance_id"] = getattr(eip, 'instance_id', None)
                if hasattr(eip, 'instance_type'):
                    eip_info["instance_type"] = getattr(eip, 'instance_type', None)
                if hasattr(eip, 'created_at'):
                    eip_info["created_at"] = str(getattr(eip, 'created_at', None)) if getattr(eip, 'created_at', None) else None
                eips.append(eip_info)

        return {
            "success": True,
            "region": region,
            "action": "list_eip_addresses",
            "count": len(eips),
            "eips": eips
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, 'request_id', None)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

def get_eip_metrics(region: str, eip_id: str, hours: int = 1, period: int = 300, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    """获取指定弹性公网IP（EIP）的监控指标"""
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

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
    
    if not SDK_AVAILABLE:
        return {
            "success": False,
            "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"
        }

    try:
        client = create_ces_client(region, access_key, secret_key, proj_id)
        metrics_result = {}
        metric_names = list(eip_metrics.keys())
        
        for metric_name in metric_names:
            try:
                request = ShowMetricDataRequest()
                request.namespace = "SYS.VPC"
                request.metric_name = metric_name
                request.dim_0 = f"publicip_id,{eip_id}"
                request._from = start_time
                request.to = end_time
                request.period = period
                request.filter = "average"
                
                response = client.show_metric_data(request)
                
                if hasattr(response, 'datapoints') and response.datapoints:
                    # 格式化数据
                    processed_data = []
                    for point in response.datapoints:
                        processed_data.append({
                            "timestamp": point.timestamp,
                            "time": datetime.fromtimestamp(point.timestamp/1000, timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                            "average": round(float(getattr(point, 'average', 0)), 2) if getattr(point, 'average', None) is not None else None,
                            "max": round(float(getattr(point, 'max', 0)), 2) if getattr(point, 'max', None) is not None else None,
                            "min": round(float(getattr(point, 'min', 0)), 2) if getattr(point, 'min', None) is not None else None
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
            except Exception as e:
                metrics_result[metric_name] = {
                    "name_cn": eip_metrics[metric_name],
                    "error": str(e)
                }
        
        return {
            "success": True,
            "region": region,
            "eip_id": eip_id,
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

def list_vpc_networks(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """List VPC networks in the specified region with pagination"""
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not SDK_AVAILABLE:
        return {
            "success": False,
            "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"
        }

    try:
        client = create_vpc_client(region, access_key, secret_key, proj_id)

        request = ListVpcsRequest()
        request.limit = str(limit)
        request.offset = str(offset)

        response = client.list_vpcs(request)

        vpcs = []
        if hasattr(response, 'vpcs') and response.vpcs:
            for vpc in response.vpcs:
                vpc_info = {
                    "id": vpc.id,
                    "name": vpc.name,
                    "cidr": vpc.cidr,
                    "status": vpc.status,
                    "created_at": str(vpc.created_at) if vpc.created_at else None,
                }
                if hasattr(vpc, 'description') and vpc.description:
                    vpc_info["description"] = vpc.description
                vpcs.append(vpc_info)

        return {
            "success": True,
            "region": region,
            "action": "list_vpc",
            "count": len(vpcs),
            "vpcs": vpcs
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, 'request_id', None)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

def list_vpc_subnets(region: str, vpc_id: str = None, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """List VPC subnets in the specified region with pagination
    
    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        vpc_id: Optional VPC ID to filter subnets
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)
        limit: Number of results to return (default: 100)
        offset: Pagination offset (default: 0)

    Returns:
        Dictionary with subnets list
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not SDK_AVAILABLE:
        return {
            "success": False,
            "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"
        }

    try:
        client = create_vpc_client(region, access_key, secret_key, proj_id)

        request = ListSubnetsRequest()
        request.limit = str(limit)
        request.offset = str(offset)
        if vpc_id:
            request.vpc_id = vpc_id

        response = client.list_subnets(request)

        subnets = []
        if hasattr(response, 'subnets') and response.subnets:
            for subnet in response.subnets:
                subnet_info = {
                    "id": subnet.id,
                    "name": subnet.name,
                    "cidr": subnet.cidr,
                    "vpc_id": subnet.vpc_id,
                    "gateway_ip": subnet.gateway_ip,
                    "dns_list": subnet.dns_list,
                    "status": subnet.status,
                    "availability_zone": subnet.availability_zone,
                    "created_at": str(subnet.created_at) if subnet.created_at else None,
                }
                if hasattr(subnet, 'description') and subnet.description:
                    subnet_info["description"] = subnet.description
                subnets.append(subnet_info)

        return {
            "success": True,
            "region": region,
            "action": "list_vpc_subnets",
            "vpc_id": vpc_id or "all",
            "count": len(subnets),
            "subnets": subnets
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, 'request_id', None)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

def list_security_groups(region: str, vpc_id: str = None, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """List security groups in the specified region with pagination"""
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not SDK_AVAILABLE:
        return {
            "success": False,
            "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"
        }

    try:
        client = create_vpc_client(region, access_key, secret_key, proj_id)

        request = ListSecurityGroupsRequest()
        request.limit = str(limit)
        request.offset = str(offset)
        if vpc_id:
            request.vpc_id = vpc_id

        response = client.list_security_groups(request)

        security_groups = []
        if hasattr(response, 'security_groups') and response.security_groups:
            for sg in response.security_groups:
                sg_info = {
                    "id": sg.id,
                    "name": sg.name,
                    "description": getattr(sg, 'description', None),
                    "vpc_id": getattr(sg, 'vpc_id', None),
                    "created_at": str(getattr(sg, 'created_at', None)) if getattr(sg, 'created_at', None) else None,
                    "security_group_rules": []
                }

                # Get security group rules
                if hasattr(sg, 'security_group_rules') and sg.security_group_rules:
                    for rule in sg.security_group_rules:
                        rule_info = {
                            "id": getattr(rule, 'id', None),
                            "direction": getattr(rule, 'direction', None),
                            "ethertype": getattr(rule, 'ethertype', None),
                            "protocol": getattr(rule, 'protocol', None),
                            "port_range_min": getattr(rule, 'port_range_min', None),
                            "port_range_max": getattr(rule, 'port_range_max', None),
                            "remote_ip_prefix": getattr(rule, 'remote_ip_prefix', None),
                            "remote_group_id": getattr(rule, 'remote_group_id', None),
                            "action": getattr(rule, 'action', None),
                            "priority": getattr(rule, 'priority', None),
                            "description": getattr(rule, 'description', None),
                        }
                        sg_info["security_group_rules"].append(rule_info)

                security_groups.append(sg_info)

        return {
            "success": True,
            "region": region,
            "action": "list_security_groups",
            "vpc_id": vpc_id,
            "count": len(security_groups),
            "security_groups": security_groups
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, 'request_id', None)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
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
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

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
    
    if not SDK_AVAILABLE:
        return {
            "success": False,
            "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"
        }

    try:
        client = create_ces_client(region, access_key, secret_key, proj_id)
        metrics_result = {}
        
        for metric_name in metric_names:
            try:
                request = ShowMetricDataRequest()
                request.namespace = "SYS.NAT"
                request.metric_name = metric_name
                request.dim_0 = f"nat_gateway_id,{nat_gateway_id}"
                request._from = start_time
                request.to = end_time
                request.period = period
                request.filter = "average"
                
                response = client.show_metric_data(request)
                
                if hasattr(response, 'datapoints') and response.datapoints:
                    # 格式化数据
                    processed_data = []
                    for point in response.datapoints:
                        processed_data.append({
                            "timestamp": point.timestamp,
                            "time": datetime.fromtimestamp(point.timestamp/1000, timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                            "average": round(float(getattr(point, 'average', 0)), 2) if getattr(point, 'average', None) is not None else None,
                            "max": round(float(getattr(point, 'max', 0)), 2) if getattr(point, 'max', None) is not None else None,
                            "min": round(float(getattr(point, 'min', 0)), 2) if getattr(point, 'min', None) is not None else None
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
            except Exception as e:
                metrics_result[metric_name] = {
                    "name_cn": metric_desc[metric_name],
                    "error": str(e)
                }
        
        return {
            "success": True,
            "region": region,
            "nat_gateway_id": nat_gateway_id,
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
    """List NAT gateways in the specified region
    基于官方API实现：https://support.huaweicloud.com/api-natgateway/nat_api_0002.html
    使用HTTP直接调用，AK/SK签名参考huawei_get_aom_metrics
    
    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        ak: Access Key ID (optional if HUAWEI_AK env is set)
        sk: Secret Access Key (optional if HUAWEI_SK env is set)
        project_id: Project ID (optional if HUAWEI_PROJECT_ID env is set)
        limit: Number of results to return (default: 100)
        offset: Offset for pagination (default: 0)
        id: NAT gateway ID (optional filter)
        name: NAT gateway name (optional filter)
        description: NAT gateway description (optional filter)
        spec: NAT gateway specification (optional filter: 1=small, 2=medium, 3=large, 4=extra-large)
        router_id: Router ID (optional filter)
        internal_network_id: Internal network ID (optional filter)
        status: NAT gateway status (optional filter)
        admin_state_up: Admin state up (optional filter)
        created_at: Creation time (optional filter)

    Returns:
        Dictionary with NAT gateways list
    """
    import hashlib
    import hmac
    import time as time_module
    import urllib.parse
    from urllib.parse import quote, unquote
    import requests
    
    # 获取凭证（包括project_id）
    access_key, secret_key, proj_id = get_credentials_with_region(region, ak, sk, project_id)

    if not access_key or not secret_key or not proj_id:
        return {
            "success": False,
            "error": "Credentials and project_id are required"
        }

    try:
        now = int(time_module.time())
        
        # ========== 构建URL和查询参数 ==========
        base_url = f"https://nat.{region}.myhuaweicloud.com"
        resource_path = f"/v2.0/nat_gateways"
        
        # 查询参数
        query_params = []
        if limit:
            query_params.append(('limit', str(limit)))
        if offset:
            query_params.append(('offset', str(offset)))
        if id:
            query_params.append(('id', id))
        if name:
            query_params.append(('name', name))
        if description:
            query_params.append(('description', description))
        if spec:
            query_params.append(('spec', spec))
        if router_id:
            query_params.append(('router_id', router_id))
        if internal_network_id:
            query_params.append(('internal_network_id', internal_network_id))
        if status:
            query_params.append(('status', status))
        if admin_state_up is not None:
            query_params.append(('admin_state_up', str(admin_state_up).lower()))
        if created_at:
            query_params.append(('created_at', created_at))
        
        # ========== 按SDK方式构建签名 ==========
        timestamp = time_module.strftime('%Y%m%dT%H%M%SZ', time_module.gmtime(now))
        
        # 1. HTTP方法
        http_method = 'GET'
        
        # 2. Canonical URI
        def url_encode(s):
            return quote(s, safe='~')
        
        pattens = unquote(resource_path).split('/')
        uri_parts = []
        for v in pattens:
            uri_parts.append(url_encode(v))
        canonical_uri = "/".join(uri_parts)
        if canonical_uri[-1] != '/':
            canonical_uri = canonical_uri + "/"
        
        # 3. Canonical Query String (排序)
        sorted_params = sorted(query_params, key=lambda x: x[0])
        canonical_querystring = '&'.join(['{}={}'.format(url_encode(k), url_encode(str(v))) for k, v in sorted_params])
        
        # 4. Headers
        host_header = f"nat.{region}.myhuaweicloud.com"
        
        # 签名的headers（按字母顺序）
        signed_headers_list = ['host', 'x-project-id', 'x-sdk-date']
        signed_headers = ';'.join(signed_headers_list)
        
        # Canonical headers (每个header一行，最后有\n)
        canonical_headers = 'host:{}\nx-project-id:{}\nx-sdk-date:{}\n'.format(
            host_header, proj_id, timestamp)
        
        # 5. 空body的hash
        hashed_body = hashlib.sha256(b'').hexdigest()
        
        # 6. 构建Canonical Request
        canonical_request = '{}\n{}\n{}\n{}\n{}\n{}'.format(
            http_method, canonical_uri, canonical_querystring,
            canonical_headers, signed_headers, hashed_body)
        
        # 7. StringToSign (SDK格式：只有3行)
        algorithm = 'SDK-HMAC-SHA256'
        hashed_canonical_request = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
        string_to_sign = '{}\n{}\n{}'.format(algorithm, timestamp, hashed_canonical_request)
        
        # 8. 签名 - 使用hex编码
        signature = hmac.new(
            secret_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).digest().hex()
        
        # 9. Authorization
        authorization = '{} Access={}, SignedHeaders={}, Signature={}'.format(
            algorithm, access_key, signed_headers, signature)
        
        # 10. 构建请求URL
        url_query_string = '&'.join(['{}={}'.format(k, urllib.parse.quote(str(v))) for k, v in query_params]) if query_params else ""
        url = "{}{}".format(base_url, resource_path)
        if url_query_string:
            url += "?{}".format(url_query_string)
        
        # 11. 请求headers
        headers = {
            'Host': host_header,
            'X-Project-Id': proj_id,
            'X-Sdk-Date': timestamp,
            'Authorization': authorization,
        }
        
        # 发送请求
        resp = requests.get(url, headers=headers, verify=False, timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            nat_list = []
            if "nat_gateways" in data:
                for nat in data["nat_gateways"]:
                    nat_info = {
                        "id": nat.get("id"),
                        "tenant_id": nat.get("tenant_id"),
                        "name": nat.get("name"),
                        "description": nat.get("description"),
                        "spec": nat.get("spec"),
                        "router_id": nat.get("router_id"),
                        "internal_network_id": nat.get("internal_network_id"),
                        "status": nat.get("status"),
                        "admin_state_up": nat.get("admin_state_up"),
                        "created_at": nat.get("created_at"),
                    }
                    nat_list.append(nat_info)
            
            return {
                "success": True,
                "region": region,
                "action": "list_nat_gateways",
                "count": len(nat_list),
                "nat_gateways": nat_list
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {resp.status_code}: {resp.text[:500]}",
                "url": url,
                "request_headers": {k: v for k, v in headers.items() if k != 'Authorization'}
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
