#!/usr/bin/env python3
"""
Huawei Cloud SDK Wrapper
Query resources and monitoring data from Huawei Cloud
"""

import sys
import json
import os
import base64
import yaml
import uuid
import warnings
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

# Suppress matplotlib warnings
warnings.filterwarnings('ignore')

# Import matplotlib for plotting
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    PLOT_ERROR = "matplotlib not installed"

try:
    from huaweicloudsdkcore.auth.credentials import GlobalCredentials, BasicCredentials
    from huaweicloudsdkcore.client import Client
    from huaweicloudsdkcore.exceptions.exceptions import ClientRequestException
    from huaweicloudsdkecs.v2 import *
    from huaweicloudsdkvpc.v2 import *
    from huaweicloudsdkces.v1 import *
    from huaweicloudsdkcce.v3 import *
    from huaweicloudsdkevs.v2 import *
    from huaweicloudsdkeip.v2 import *
    from huaweicloudsdkelb.v2 import *  # ELB v2 for listeners
    from huaweicloudsdkelb.v3 import *  # ELB v3 for loadbalancers
    from huaweicloudsdkiam.v3 import *  # IAM for project info

    # AOM for application monitoring
    try:
        from huaweicloudsdkaom.v2 import AomClient, ShowMetricsDataRequest
        AOM_AVAILABLE = True
    except ImportError as e:
        AOM_AVAILABLE = False
        AOM_IMPORT_ERROR = str(e)

    import kubernetes
    from kubernetes import client as k8s_client
    K8S_AVAILABLE = True
    SDK_AVAILABLE = True
    IMPORT_ERROR = None
except ImportError as e:
    SDK_AVAILABLE = False
    K8S_AVAILABLE = False
    IMPORT_ERROR = str(e)
    K8S_IMPORT_ERROR = str(e)
    from huaweicloudsdkcore.auth.credentials import GlobalCredentials, BasicCredentials
    from huaweicloudsdkcore.client import Client
    from huaweicloudsdkcore.exceptions.exceptions import ClientRequestException
    from huaweicloudsdkecs.v2 import *
    from huaweicloudsdkvpc.v2 import *
    from huaweicloudsdkces.v1 import *
    from huaweicloudsdkcce.v3 import *
    import kubernetes
    from kubernetes import client as k8s_client
    K8S_AVAILABLE = True  # Kubernetes still available
    from huaweicloudsdkcore.exceptions.exceptions import ClientRequestException
    from huaweicloudsdkecs.v2 import *
    from huaweicloudsdkvpc.v2 import *
    from huaweicloudsdkces.v1 import *
    from huaweicloudsdkcce.v3 import *
    SDK_AVAILABLE = True
except ImportError as e:
    SDK_AVAILABLE = False
    IMPORT_ERROR = str(e)


# Region to project ID mapping (common regions)
# NOTE: Please set HUAWEI_PROJECT_ID environment variable or pass project_id parameter
# Do not hardcode project IDs in code
PROJECT_IDS = {
    # "cn-north-4": "your-project-id-here",
    # Add your project IDs here or use environment variables
}

# ============================================================
# 安全约束 (Security Constraints)
# ============================================================
# 1. ❌ 禁止将任何认证信息（AK/SK/Token/Certificate）保存到文件系统
# 2. ❌ 禁止将AK/SK保存到长期内存、缓存或持久化存储
# 3. ✅ AK/SK仅在当前请求调用栈中存在，调用结束自动释放
# 4. ✅ 仅非敏感的项目ID缓存在进程内存中（从不写入磁盘）
# 5. ✅ 所有临时证书文件在使用后必须立即删除
# 6. ✅ 禁止在日志、响应或错误信息中泄露AK/SK等敏感信息
# 7. ✅ 从不向任何第三方服务器发送认证信息
# ============================================================

# Project ID cache - auto-populated from IAM (只缓存project_id，不缓存密钥)
_PROJECT_ID_CACHE = {}

# 临时证书文件追踪（用于清理）
_TEMP_CERT_FILES = set()


def _cleanup_cert_files():
    """清理所有临时证书文件"""
    import os
    global _TEMP_CERT_FILES
    for filepath in list(_TEMP_CERT_FILES):
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
    _TEMP_CERT_FILES.clear()


def _select_external_cluster(kubeconfig_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Select the public cluster endpoint first, then fall back to the first cluster entry."""
    for cluster in kubeconfig_data.get('clusters', []):
        cluster_name = cluster.get('name', '')
        if 'external' in cluster_name and 'TLS' not in cluster_name:
            return cluster

    clusters = kubeconfig_data.get('clusters', [])
    return clusters[0] if clusters else None


def _get_kubeconfig_user_data(kubeconfig_data: Dict[str, Any]) -> Dict[str, Any]:
    """Return the default kubeconfig user payload when present."""
    for user_entry in kubeconfig_data.get('users', []):
        if user_entry.get('name') == 'user':
            return user_entry.get('user', {})
    return {}


def _configure_k8s_client_certificate_files(
    configuration: Any,
    kubeconfig_data: Dict[str, Any],
    cert_file_path: str,
    key_file_path: str,
) -> tuple[Optional[str], Optional[str]]:
    """Write client cert/key files from kubeconfig data and attach them to the Kubernetes config."""
    user_data = _get_kubeconfig_user_data(kubeconfig_data)
    cert_file = None
    key_file = None

    if user_data.get('client_certificate_data'):
        cert_file = cert_file_path
        with open(cert_file, 'wb') as cert_handle:
            cert_handle.write(base64.b64decode(user_data['client_certificate_data']))
        configuration.cert_file = cert_file
        _register_cert_file(cert_file)

    if user_data.get('client_key_data'):
        key_file = key_file_path
        with open(key_file, 'wb') as key_handle:
            key_handle.write(base64.b64decode(user_data['client_key_data']))
        configuration.key_file = key_file
        _register_cert_file(key_file)

    return cert_file, key_file


def _cleanup_cert_pair(cert_file: Optional[str], key_file: Optional[str]) -> None:
    """Delete paired temporary certificate files when present."""
    _safe_delete_file(cert_file)
    _safe_delete_file(key_file)


# 危险操作确认存储（用于二次确认）
# 格式: {operation_key: {'timestamp': xxx, 'params': {...}}}
_DANGEROUS_OP_CONFIRMATIONS = {}

# 确认有效期（秒）
_CONFIRMATION_TTL = 60


def _generate_op_key(operation: str, cluster_id: str, namespace: str, name: str) -> str:
    """生成操作唯一标识"""
    return f"{operation}:{cluster_id}:{namespace}:{name}"


def _check_confirmation(operation: str, cluster_id: str, namespace: str, name: str) -> dict:
    """检查是否有有效的确认请求
    
    Returns:
        dict: {'confirmed': bool, 'message': str, 'remaining_seconds': int}
    """
    import time
    global _DANGEROUS_OP_CONFIRMATIONS
    
    op_key = _generate_op_key(operation, cluster_id, namespace, name)
    
    if op_key in _DANGEROUS_OP_CONFIRMATIONS:
        record = _DANGEROUS_OP_CONFIRMATIONS[op_key]
        elapsed = time.time() - record['timestamp']
        
        if elapsed <= _CONFIRMATION_TTL:
            remaining = int(_CONFIRMATION_TTL - elapsed)
            return {
                'confirmed': True,
                'message': f"确认有效，剩余 {remaining} 秒",
                'remaining_seconds': remaining
            }
    
    return {
        'confirmed': False,
        'message': "需要二次确认",
        'remaining_seconds': 0
    }


def _record_confirmation_request(operation: str, cluster_id: str, namespace: str, name: str, params: dict):
    """记录确认请求"""
    import time
    global _DANGEROUS_OP_CONFIRMATIONS
    
    op_key = _generate_op_key(operation, cluster_id, namespace, name)
    _DANGEROUS_OP_CONFIRMATIONS[op_key] = {
        'timestamp': time.time(),
        'params': params
    }


def _clear_confirmation(operation: str, cluster_id: str, namespace: str, name: str):
    """清除确认记录"""
    global _DANGEROUS_OP_CONFIRMATIONS
    op_key = _generate_op_key(operation, cluster_id, namespace, name)
    _DANGEROUS_OP_CONFIRMATIONS.pop(op_key, None)


# Supported Regions
# 华为云支持的区域列表
SUPPORTED_REGIONS = {
    # ===== 中国大陆主要Region =====
    "cn-north-4": {"name": "华北-北京四", "description": "核心区域，推荐"},
    "cn-north-1": {"name": "华北-北京一", "description": "早期区域"},
    "cn-north-9": {"name": "华北-乌兰察布一", "description": "数据中心"},
    "cn-east-3": {"name": "华东-上海一", "description": "华东核心"},
    "cn-east-2": {"name": "华东-上海二", "description": "核心区域"},
    "cn-south-1": {"name": "华南-广州", "description": "华南核心"},
    "cn-southwest-2": {"name": "西南-贵阳一", "description": "骨干数据中心"},
    "cn-west-3": {"name": "西北-西安一", "description": "西北区域"},
    
    # ===== 中国香港及国际区域 =====
    "ap-southeast-1": {"name": "中国香港", "description": "适合亚太业务"},
    "ap-southeast-2": {"name": "亚太-曼谷", "description": "泰国节点"},
    "ap-southeast-3": {"name": "亚太-新加坡", "description": "东南亚核心"},
    "ap-southeast-4": {"name": "亚太-雅加达", "description": "印尼节点"},
    "af-south-1": {"name": "非洲-约翰内斯堡", "description": "南非节点"},
    "la-south-2": {"name": "拉美-圣地亚哥", "description": "智利节点"},
    "la-north-2": {"name": "拉美-墨西哥城", "description": "墨西哥节点"},
    "eu-west-0": {"name": "欧洲-巴黎", "description": "欧洲节点"},
    "ap-northeast-1": {"name": "亚太-东京", "description": "日本节点"},
}







def main():
    """Main entry point for the script"""
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "Missing action parameter"
        }))
        sys.exit(1)

    action = sys.argv[1]
    params = _parse_cli_params(sys.argv[2:])

    modular_result = _dispatch_modular_action(action, params)
    if modular_result is not None:
        print(json.dumps(modular_result, indent=2, ensure_ascii=False))
        return

    _exit_error(f"Unknown action: {action}")


def _dispatch_modular_action(action: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Attempt modular dispatch first and fall back to legacy dispatch when needed."""
    try:
        # Ensure local huawei_cloud package is importable
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        from huawei_cloud.dispatcher import dispatch_action, is_registered_action
    except Exception as exc:
        return {
            "success": False,
            "error": "Modular dispatcher unavailable",
            "error_type": type(exc).__name__,
        }

    if not is_registered_action(action):
        return None

    return dispatch_action(action, params)


def _parse_cli_params(args: List[str]) -> Dict[str, str]:
    """Parse key=value CLI arguments into a parameter mapping."""
    params: Dict[str, str] = {}
    for arg in args:
        if "=" not in arg:
            continue
        key, value = arg.split("=", 1)
        params[key] = value
    return params


def _coerce_int(value: Optional[str], default: int) -> int:
    """Return an integer value or the provided default when parsing fails."""
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _coerce_bool(value: Optional[str], default: bool = False) -> bool:
    """Return a CLI-style boolean, defaulting when the parameter is omitted."""
    if value is None:
        return default
    return value.lower() == "true"


def _exit_error(message: str, exit_code: int = 1) -> None:
    """Print a structured CLI error and exit."""
    print(json.dumps({"success": False, "error": message}))
    sys.exit(exit_code)


def _apply_modular_compat_aliases() -> None:
    """Rebind legacy duplicate helpers to modular implementations."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    # from huawei_cloud import aom as _aom_mod  # Pruned
    # from huawei_cloud import cce as _cce_mod  # Pruned
    from huawei_cloud import common as _common_mod
    # from huawei_cloud import ecs as _ecs_mod  # Pruned
    # from huawei_cloud import elb as _elb_mod  # Pruned
    # from huawei_cloud import identity as _identity_mod  # Pruned
    # from huawei_cloud import cce_metrics as _metrics_mod  # Pruned
    from huawei_cloud import network as _network_mod
    # from huawei_cloud import storage as _storage_mod  # Pruned
    # from huawei_cloud import cce_inspection as _inspection_mod  # Pruned

    globals().update({
        "_register_cert_file": _common_mod._register_cert_file,
        "_safe_delete_file": _common_mod._safe_delete_file,
    # "cce_cluster_inspection": _inspection_mod.cce_cluster_inspection,  # Pruned
        "create_aom_client": _common_mod.create_aom_client,
        "create_cce_client": _common_mod.create_cce_client,
        "create_ces_client": _common_mod.create_ces_client,
        "create_ecs_client": _common_mod.create_ecs_client,
        "create_eip_client": _common_mod.create_eip_client,
        "create_elb_client": _common_mod.create_elb_client,
        "create_evs_client": _common_mod.create_evs_client,
        "create_iam_client": _common_mod.create_iam_client,
        "create_vpc_client": _common_mod.create_vpc_client,
    # "delete_cce_cluster": _cce_mod.delete_cce_cluster,  # Pruned
    # "delete_cce_node": _cce_mod.delete_cce_node,  # Pruned
    # "delete_cce_workload": _cce_mod.delete_cce_workload,  # Pruned
    # "generate_inspection_html_report": _inspection_mod.generate_inspection_html_report,  # Pruned
        "generate_monitoring_chart": _common_mod.generate_monitoring_chart,
    # "get_aom_prom_metrics_http": _aom_mod.get_aom_prom_metrics_http,  # Pruned
    # "get_cce_kubeconfig": _cce_mod.get_cce_kubeconfig,  # Pruned
    # "get_cce_addon_detail": _cce_mod.get_cce_addon_detail,  # Pruned
    # "get_cce_node_metrics": _metrics_mod.get_cce_node_metrics,  # Pruned
    # "get_cce_node_metrics_topN": _metrics_mod.get_cce_node_metrics_topN,  # Pruned
    # "get_cce_nodes": _cce_mod.get_cce_nodes,  # Pruned
    # "get_cce_pod_metrics": _metrics_mod.get_cce_pod_metrics,  # Pruned
    # "get_cce_pod_metrics_topN": _metrics_mod.get_cce_pod_metrics_topN,  # Pruned
        "get_credentials": _common_mod.get_credentials,
        "get_credentials_with_region": _common_mod.get_credentials_with_region,
    # "get_ecs_metrics": _ecs_mod.get_ecs_metrics,  # Pruned
    # "get_ecs_metrics_with_chart": _ecs_mod.get_ecs_metrics_with_chart,  # Pruned
        "get_eip_metrics": _network_mod.get_eip_metrics,
    # "get_elb_metrics": _elb_mod.get_elb_metrics,  # Pruned
    # "get_evs_metrics": _storage_mod.get_evs_metrics,  # Pruned
    # "get_kubernetes_deployments": _cce_mod.get_kubernetes_deployments,  # Pruned
    # "get_kubernetes_events": _cce_mod.get_kubernetes_events,  # Pruned
    # "get_kubernetes_ingresses": _cce_mod.get_kubernetes_ingresses,  # Pruned
    # "get_kubernetes_namespaces": _cce_mod.get_kubernetes_namespaces,  # Pruned
    # "get_kubernetes_nodes": _cce_mod.get_kubernetes_nodes,  # Pruned
    # "get_kubernetes_pods": _cce_mod.get_kubernetes_pods,  # Pruned
    # "get_kubernetes_pvcs": _cce_mod.get_kubernetes_pvcs,  # Pruned
    # "get_kubernetes_pvs": _cce_mod.get_kubernetes_pvs,  # Pruned
    # "get_kubernetes_services": _cce_mod.get_kubernetes_services,  # Pruned
        "get_nat_gateway_metrics": _network_mod.get_nat_gateway_metrics,
    # "get_project_by_region": _identity_mod.get_project_by_region,  # Pruned
        "get_project_id_for_region": _common_mod.get_project_id_for_region,
    # "list_aom_action_rules": _aom_mod.list_aom_action_rules,  # Pruned
    # "list_aom_alarm_rules": _aom_mod.list_aom_alarm_rules,  # Pruned
    # "list_aom_alerts": _aom_mod.list_aom_alerts,  # Pruned
    # "list_aom_current_alarms": _aom_mod.list_aom_current_alarms,  # Pruned
    # "list_aom_instances": _aom_mod.list_aom_instances,  # Pruned
    # "list_aom_mute_rules": _aom_mod.list_aom_mute_rules,  # Pruned
    # "list_cce_addons": _cce_mod.list_cce_addons,  # Pruned
    # "list_cce_cluster_nodes": _cce_mod.list_cce_cluster_nodes,  # Pruned
    # "list_cce_clusters": _cce_mod.list_cce_clusters,  # Pruned
    # "list_cce_configmaps": _cce_mod.list_cce_configmaps,  # Pruned
    # "list_cce_node_pools": _cce_mod.list_cce_node_pools,  # Pruned
    # "list_ecs_flavors": _ecs_mod.list_ecs_flavors,  # Pruned
    # "list_ecs_instances": _ecs_mod.list_ecs_instances,  # Pruned
        "list_eip_addresses": _network_mod.list_eip_addresses,
    # "list_elb_listeners": _elb_mod.list_elb_listeners,  # Pruned
    # "list_elb_loadbalancers": _elb_mod.list_elb_loadbalancers,  # Pruned
    # "list_evs_volumes": _storage_mod.list_evs_volumes,  # Pruned
    # "list_projects": _identity_mod.list_projects,  # Pruned
        "list_security_groups": _network_mod.list_security_groups,
    # "list_supported_regions": _identity_mod.list_supported_regions,  # Pruned
        "list_vpc_acls": _network_mod.list_vpc_acls,
        "list_vpc_networks": _network_mod.list_vpc_networks,
        "list_vpc_subnets": _network_mod.list_vpc_subnets,
    # "resize_node_pool": _cce_mod.resize_node_pool,  # Pruned
    # "scale_cce_workload": _cce_mod.scale_cce_workload,  # Pruned
    })


_apply_modular_compat_aliases()


if __name__ == "__main__":
    main()
