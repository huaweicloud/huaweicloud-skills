"""Common Huawei Cloud helpers shared by service modules."""

from __future__ import annotations

import base64
import os
import sys
import uuid
import warnings
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import yaml

warnings.filterwarnings("ignore")

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import kubernetes
    from kubernetes import client as k8s_client

    K8S_AVAILABLE = True
    K8S_IMPORT_ERROR = None
except ImportError as exc:
    kubernetes = None
    k8s_client = None
    K8S_AVAILABLE = False
    K8S_IMPORT_ERROR = str(exc)

try:
    from huaweicloudsdkaom.v2 import AomClient, ShowMetricsDataRequest

    AOM_AVAILABLE = True
    AOM_IMPORT_ERROR = None
except ImportError as exc:
    AomClient = None
    ShowMetricsDataRequest = None
    AOM_AVAILABLE = False
    AOM_IMPORT_ERROR = str(exc)

from huaweicloudsdkcore.auth.credentials import GlobalCredentials, BasicCredentials
from huaweicloudsdkecs.v2 import *
from huaweicloudsdkvpc.v2 import *
from huaweicloudsdkces.v1 import *
from huaweicloudsdkcce.v3 import *
from huaweicloudsdkevs.v2 import *
from huaweicloudsdkeip.v2 import *
from huaweicloudsdkelb.v2 import *
from huaweicloudsdkelb.v3 import *
from huaweicloudsdkiam.v3 import *

PROJECT_IDS = {}
_PROJECT_ID_CACHE = {}
SDK_AVAILABLE = True
IMPORT_ERROR = None
_TEMP_CERT_FILES = set()

SUPPORTED_REGIONS = {
    "cn-north-4": {"name": "华北-北京四", "description": "核心区域，推荐"},
    "cn-north-1": {"name": "华北-北京一", "description": "早期区域"},
    "cn-north-9": {"name": "华北-乌兰察布一", "description": "数据中心"},
    "cn-east-3": {"name": "华东-上海一", "description": "华东核心"},
    "cn-east-2": {"name": "华东-上海二", "description": "核心区域"},
    "cn-south-1": {"name": "华南-广州", "description": "华南核心"},
    "cn-southwest-2": {"name": "西南-贵阳一", "description": "骨干数据中心"},
    "cn-west-3": {"name": "西北-西安一", "description": "西北区域"},
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

ECS_ENDPOINTS = {
    "cn-north-4": "ecs.cn-north-4.myhuaweicloud.com", "cn-north-1": "ecs.cn-north-1.myhuaweicloud.com", "cn-north-9": "ecs.cn-north-9.myhuaweicloud.com",
    "cn-east-3": "ecs.cn-east-3.myhuaweicloud.com", "cn-east-2": "ecs.cn-east-2.myhuaweicloud.com", "cn-south-1": "ecs.cn-south-1.myhuaweicloud.com",
    "cn-southwest-2": "ecs.cn-southwest-2.myhuaweicloud.com", "cn-west-3": "ecs.cn-west-3.myhuaweicloud.com", "ap-southeast-1": "ecs.ap-southeast-1.myhuaweicloud.com",
    "ap-southeast-2": "ecs.ap-southeast-2.myhuaweicloud.com", "ap-southeast-3": "ecs.ap-southeast-3.myhuaweicloud.com", "ap-southeast-4": "ecs.ap-southeast-4.myhuaweicloud.com",
    "af-south-1": "ecs.af-south-1.myhuaweicloud.com", "la-south-2": "ecs.la-south-2.myhuaweicloud.com", "la-north-2": "ecs.la-north-2.myhuaweicloud.com",
    "eu-west-0": "ecs.eu-west-0.myhuaweicloud.com", "ap-northeast-1": "ecs.ap-northeast-1.myhuaweicloud.com",
}
VPC_ENDPOINTS = {
    "cn-north-4": "vpc.cn-north-4.myhuaweicloud.com", "cn-north-1": "vpc.cn-north-1.myhuaweicloud.com", "cn-north-9": "vpc.cn-north-9.myhuaweicloud.com",
    "cn-east-3": "vpc.cn-east-3.myhuaweicloud.com", "cn-east-2": "vpc.cn-east-2.myhuaweicloud.com", "cn-south-1": "vpc.cn-south-1.myhuaweicloud.com",
    "cn-southwest-2": "vpc.cn-southwest-2.myhuaweicloud.com", "cn-west-3": "vpc.cn-west-3.myhuaweicloud.com", "ap-southeast-1": "vpc.ap-southeast-1.myhuaweicloud.com",
    "ap-southeast-2": "vpc.ap-southeast-2.myhuaweicloud.com", "ap-southeast-3": "vpc.ap-southeast-3.myhuaweicloud.com", "ap-southeast-4": "vpc.ap-southeast-4.myhuaweicloud.com",
    "af-south-1": "vpc.af-south-1.myhuaweicloud.com", "la-south-2": "vpc.la-south-2.myhuaweicloud.com", "la-north-2": "vpc.la-north-2.myhuaweicloud.com",
    "eu-west-0": "vpc.eu-west-0.myhuaweicloud.com", "ap-northeast-1": "vpc.ap-northeast-1.myhuaweicloud.com",
}
CES_ENDPOINTS = {
    "cn-north-4": "ces.cn-north-4.myhuaweicloud.com", "cn-north-1": "ces.cn-north-1.myhuaweicloud.com", "cn-north-9": "ces.cn-north-9.myhuaweicloud.com",
    "cn-east-3": "ces.cn-east-3.myhuaweicloud.com", "cn-east-2": "ces.cn-east-2.myhuaweicloud.com", "cn-south-1": "ces.cn-south-1.myhuaweicloud.com",
    "cn-southwest-2": "ces.cn-southwest-2.myhuaweicloud.com", "cn-west-3": "ces.cn-west-3.myhuaweicloud.com", "ap-southeast-1": "ces.ap-southeast-1.myhuaweicloud.com",
    "ap-southeast-2": "ces.ap-southeast-2.myhuaweicloud.com", "ap-southeast-3": "ces.ap-southeast-3.myhuaweicloud.com", "ap-southeast-4": "ces.ap-southeast-4.myhuaweicloud.com",
    "af-south-1": "ces.af-south-1.myhuaweicloud.com", "la-south-2": "ces.la-south-2.myhuaweicloud.com", "la-north-2": "ces.la-north-2.myhuaweicloud.com",
    "eu-west-0": "ces.eu-west-0.myhuaweicloud.com", "ap-northeast-1": "ces.ap-northeast-1.myhuaweicloud.com",
}
CCE_ENDPOINTS = {
    "cn-north-4": "cce.cn-north-4.myhuaweicloud.com", "cn-north-1": "cce.cn-north-1.myhuaweicloud.com", "cn-north-9": "cce.cn-north-9.myhuaweicloud.com",
    "cn-east-3": "cce.cn-east-3.myhuaweicloud.com", "cn-east-2": "cce.cn-east-2.myhuaweicloud.com", "cn-south-1": "cce.cn-south-1.myhuaweicloud.com",
    "cn-southwest-2": "cce.cn-southwest-2.myhuaweicloud.com", "cn-west-3": "cce.cn-west-3.myhuaweicloud.com", "ap-southeast-1": "cce.ap-southeast-1.myhuaweicloud.com",
    "ap-southeast-2": "cce.ap-southeast-2.myhuaweicloud.com", "ap-southeast-3": "cce.ap-southeast-3.myhuaweicloud.com", "ap-southeast-4": "cce.ap-southeast-4.myhuaweicloud.com",
    "af-south-1": "cce.af-south-1.myhuaweicloud.com", "la-south-2": "cce.la-south-2.myhuaweicloud.com", "la-north-2": "cce.la-north-2.myhuaweicloud.com",
    "eu-west-0": "cce.eu-west-0.myhuaweicloud.com", "ap-northeast-1": "cce.ap-northeast-1.myhuaweicloud.com",
}
EVS_ENDPOINTS = {
    "cn-north-4": "evs.cn-north-4.myhuaweicloud.com", "cn-north-1": "evs.cn-north-1.myhuaweicloud.com", "cn-north-9": "evs.cn-north-9.myhuaweicloud.com",
    "cn-east-3": "evs.cn-east-3.myhuaweicloud.com", "cn-east-2": "evs.cn-east-2.myhuaweicloud.com", "cn-south-1": "evs.cn-south-1.myhuaweicloud.com",
    "cn-southwest-2": "evs.cn-southwest-2.myhuaweicloud.com", "cn-west-3": "evs.cn-west-3.myhuaweicloud.com", "ap-southeast-1": "evs.ap-southeast-1.myhuaweicloud.com",
    "ap-southeast-2": "evs.ap-southeast-2.myhuaweicloud.com", "ap-southeast-3": "evs.ap-southeast-3.myhuaweicloud.com", "ap-southeast-4": "evs.ap-southeast-4.myhuaweicloud.com",
    "af-south-1": "evs.af-south-1.myhuaweicloud.com", "la-south-2": "evs.la-south-2.myhuaweicloud.com", "la-north-2": "evs.la-north-2.myhuaweicloud.com",
    "eu-west-0": "evs.eu-west-0.myhuaweicloud.com", "ap-northeast-1": "evs.ap-northeast-1.myhuaweicloud.com",
}
EIP_ENDPOINTS = VPC_ENDPOINTS
ELB_ENDPOINTS = {
    "cn-north-4": "elb.cn-north-4.myhuaweicloud.com", "cn-north-1": "elb.cn-north-1.myhuaweicloud.com", "cn-north-9": "elb.cn-north-9.myhuaweicloud.com",
    "cn-east-3": "elb.cn-east-3.myhuaweicloud.com", "cn-east-2": "elb.cn-east-2.myhuaweicloud.com", "cn-south-1": "elb.cn-south-1.myhuaweicloud.com",
    "cn-southwest-2": "elb.cn-southwest-2.myhuaweicloud.com", "cn-west-3": "elb.cn-west-3.myhuaweicloud.com", "ap-southeast-1": "elb.ap-southeast-1.myhuaweicloud.com",
    "ap-southeast-2": "elb.ap-southeast-2.myhuaweicloud.com", "ap-southeast-3": "elb.ap-southeast-3.myhuaweicloud.com", "ap-southeast-4": "elb.ap-southeast-4.myhuaweicloud.com",
    "af-south-1": "elb.af-south-1.myhuaweicloud.com", "la-south-2": "elb.la-south-2.myhuaweicloud.com", "la-north-2": "elb.la-north-2.myhuaweicloud.com",
    "eu-west-0": "elb.eu-west-0.myhuaweicloud.com", "ap-northeast-1": "elb.ap-northeast-1.myhuaweicloud.com",
}
IAM_ENDPOINT = "iam.myhuaweicloud.com"


def _register_cert_file(filepath: Optional[str]) -> None:
    if filepath:
        _TEMP_CERT_FILES.add(filepath)


def _safe_delete_file(filepath: Optional[str]) -> None:
    if not filepath:
        return
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    finally:
        _TEMP_CERT_FILES.discard(filepath)

def generate_monitoring_chart(metrics_data: Dict[str, Any], resource_name: str, chart_type: str = "ecs") -> Optional[str]:
    """Generate monitoring chart from metrics data

    Args:
        metrics_data: Dictionary containing metrics with datapoints
        resource_name: Name of the resource being monitored
        chart_type: Type of chart - 'ecs', 'evs', 'elb', or 'eip'

    Returns:
        Path to the generated chart image file, or None if failed
    """
    if not MATPLOTLIB_AVAILABLE:
        return None

    try:
        # Generate unique filename
        filename = f"/tmp/{resource_name}_{chart_type}_monitoring_{uuid.uuid4().hex[:8]}.png"

        # Extract time series data
        fig, axes = plt.subplots(2, 1, figsize=(12, 10))
        fig.suptitle(f'{resource_name} Monitoring ({chart_type.upper()})', fontsize=14, fontweight='bold')

        # Process metrics based on chart type
        all_times = []
        all_values_1 = []
        all_values_2 = []
        label_1 = ""
        label_2 = ""

        metrics = metrics_data.get('metrics', {})

        if chart_type == "ecs":
            # CPU utilization
            cpu_data = metrics.get('cpu_util', {})
            if cpu_data.get('datapoints'):
                for dp in cpu_data['datapoints']:
                    all_times.append(datetime.fromtimestamp(dp['timestamp']/1000, timezone.utc))
                    all_values_1.append(dp.get('average', 0))
                label_1 = 'CPU Usage (%)'

            # Disk I/O
            disk_read = metrics.get('disk_read_bytes_rate', {})
            if disk_read.get('datapoints'):
                for dp in disk_read['datapoints']:
                    all_times.append(datetime.fromtimestamp(dp['timestamp']/1000, timezone.utc))
                    all_values_2.append(dp.get('average', 0) / 1024)  # Convert to KB/s
                label_2 = 'Disk Read (KB/s)'

        elif chart_type == "evs":
            # Read/Write IOPS
            read_iops = metrics.get('disk_read_iops', {})
            if read_iops.get('datapoints'):
                for dp in read_iops['datapoints']:
                    all_times.append(datetime.fromtimestamp(dp['timestamp']/1000, timezone.utc))
                    all_values_1.append(dp.get('average', 0))
                label_1 = 'Read IOPS'

            write_iops = metrics.get('disk_write_iops', {})
            if write_iops.get('datapoints'):
                for dp in write_iops['datapoints']:
                    all_times.append(datetime.fromtimestamp(dp['timestamp']/1000, timezone.utc))
                    all_values_2.append(dp.get('average', 0))
                label_2 = 'Write IOPS'

        elif chart_type == "elb":
            # Connections
            conns = metrics.get('connection_count', {})
            if conns.get('datapoints'):
                for dp in conns['datapoints']:
                    all_times.append(datetime.fromtimestamp(dp['timestamp']/1000, timezone.utc))
                    all_values_1.append(dp.get('average', 0))
                label_1 = 'Connections'

            # QPS
            qps = metrics.get('qps', {})
            if qps.get('datapoints'):
                for dp in qps['datapoints']:
                    all_times.append(datetime.fromtimestamp(dp['timestamp']/1000, timezone.utc))
                    all_values_2.append(dp.get('average', 0))
                label_2 = 'QPS'

        elif chart_type == "eip":
            # Bandwidth
            bandwidth = metrics.get('bandwidth', {})
            if bandwidth.get('datapoints'):
                for dp in bandwidth['datapoints']:
                    all_times.append(datetime.fromtimestamp(dp['timestamp']/1000, timezone.utc))
                    all_values_1.append(dp.get('average', 0) / 1024 / 1024)  # Convert to Mbps
                label_1 = 'Bandwidth (Mbps)'

            # Traffic
            traffic = metrics.get('total_streaming_connections', {})
            if traffic.get('datapoints'):
                for dp in traffic['datapoints']:
                    all_times.append(datetime.fromtimestamp(dp['timestamp']/1000, timezone.utc))
                    all_values_2.append(dp.get('average', 0))
                label_2 = 'Connections'

        # Plot first chart
        ax1 = axes[0]
        if all_times and all_values_1:
            ax1.plot(all_times[:len(all_values_1)], all_values_1, 'b-o', linewidth=2, markersize=4, label=label_1)
            ax1.fill_between(all_times[:len(all_values_1)], all_values_1, alpha=0.3)
        ax1.set_ylabel(label_1, fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper right')
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

        # Plot second chart
        ax2 = axes[1]
        if all_times and all_values_2:
            # Align times with values
            time_len = min(len(all_times), len(all_values_2))
            ax2.plot(all_times[:time_len], all_values_2[:time_len], 'r-o', linewidth=2, markersize=4, label=label_2)
            ax2.fill_between(all_times[:time_len], all_values_2[:time_len], alpha=0.3, color='red')
        ax2.set_ylabel(label_2, fontsize=10)
        ax2.set_xlabel('Time', fontsize=10)
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper right')
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()

        return filename

    except Exception as e:
        print(f"Error generating chart: {e}", file=sys.stderr)
        return None

def get_credentials(ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> tuple:
    """Get credentials from params or environment variables
    
    Supports multiple env var naming conventions:
    - HUAWEI_AK / HUAWEI_SK / HUAWEI_PROJECT_ID (project custom)
    - HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK / HUAWEICLOUD_SDK_PROJECT_ID (SDK official)
    - HW_ACCESS_KEY / HW_SECRET_KEY / HW_REGION_NAME (Terraform/CLI style)
    """
    access_key = ak or os.environ.get("HUAWEI_AK") or os.environ.get("HUAWEICLOUD_SDK_AK") or os.environ.get("HW_ACCESS_KEY")
    secret_key = sk or os.environ.get("HUAWEI_SK") or os.environ.get("HUAWEICLOUD_SDK_SK") or os.environ.get("HW_SECRET_KEY")
    proj_id = project_id or os.environ.get("HUAWEI_PROJECT_ID") or os.environ.get("HUAWEICLOUD_SDK_PROJECT_ID")
    return access_key, secret_key, proj_id

def get_project_id_for_region(region: str, ak: Optional[str] = None, sk: Optional[str] = None) -> Optional[str]:
    """Get project ID for a specific region, auto-fetch from IAM if not cached
    
    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
    
    Returns:
        Project ID string or None if not found
    """
    global _PROJECT_ID_CACHE
    
    # Check cache first
    if region in _PROJECT_ID_CACHE:
        return _PROJECT_ID_CACHE[region]
    
    # Get credentials
    access_key, secret_key, _ = get_credentials(ak, sk, None)
    if not access_key or not secret_key:
        return None
    
    # Fetch from IAM
    try:
        from huaweicloudsdkiam.v3 import KeystoneListProjectsRequest
        
        client = create_iam_client(access_key, secret_key)
        request = KeystoneListProjectsRequest()
        request.name = region  # Filter by region name
        
        response = client.keystone_list_projects(request)
        
        if hasattr(response, 'projects') and response.projects:
            for project in response.projects:
                if project.name == region:
                    proj_id = project.id
                    # Cache it
                    _PROJECT_ID_CACHE[region] = proj_id
                    return proj_id
        
        # If not found with filter, try to get all and filter
        request2 = KeystoneListProjectsRequest()
        response2 = client.keystone_list_projects(request2)
        
        if hasattr(response2, 'projects') and response2.projects:
            for project in response2.projects:
                if project.name:
                    _PROJECT_ID_CACHE[project.name] = project.id
            
            return _PROJECT_ID_CACHE.get(region)
        
    except Exception as e:
        # Silently fail, return None
        pass
    
    return None

def get_credentials_with_region(region: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> tuple:
    """Get credentials with automatic project_id lookup for region
    
    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional, will auto-fetch if not provided)
    
    Returns:
        Tuple of (access_key, secret_key, project_id)
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)
    
    # If no project_id provided, try to get it for the region
    if not proj_id and region and access_key and secret_key:
        proj_id = get_project_id_for_region(region, access_key, secret_key)
    
    return access_key, secret_key, proj_id

def create_ecs_client(region: str, ak: str, sk: str, project_id: str = None):
    """Create ECS client"""
    # Auto-fetch project_id if not provided
    if not project_id:
        project_id = get_project_id_for_region(region, ak, sk)
    
    if project_id:
        credentials = BasicCredentials(ak=ak, sk=sk, project_id=project_id)
    else:
        credentials = BasicCredentials(ak=ak, sk=sk)

    endpoint = ECS_ENDPOINTS.get(region, f"ecs.{region}.myhuaweicloud.com")
    return EcsClient.new_builder() \
        .with_credentials(credentials) \
        .with_endpoint(endpoint) \
        .build()

def create_vpc_client(region: str, ak: str, sk: str, project_id: str = None):
    """Create VPC client"""
    # Auto-fetch project_id if not provided
    if not project_id:
        project_id = get_project_id_for_region(region, ak, sk)
    
    if project_id:
        credentials = BasicCredentials(ak=ak, sk=sk, project_id=project_id)
    else:
        credentials = BasicCredentials(ak=ak, sk=sk)

    endpoint = VPC_ENDPOINTS.get(region, f"vpc.{region}.myhuaweicloud.com")
    return VpcClient.new_builder() \
        .with_credentials(credentials) \
        .with_endpoint(endpoint) \
        .build()

def create_ces_client(region: str, ak: str, sk: str, project_id: str = None):
    """Create CES (Cloud Eye Service) client"""
    # Auto-fetch project_id if not provided
    if not project_id:
        project_id = get_project_id_for_region(region, ak, sk)
    
    if project_id:
        credentials = BasicCredentials(ak=ak, sk=sk, project_id=project_id)
    else:
        credentials = BasicCredentials(ak=ak, sk=sk)

    endpoint = CES_ENDPOINTS.get(region, f"ces.{region}.myhuaweicloud.com")
    return CesClient.new_builder() \
        .with_credentials(credentials) \
        .with_endpoint(endpoint) \
        .build()

def create_aom_client(region: str, ak: str, sk: str, project_id: str = None):
    """Create AOM (Application Operations Management) client"""
    # Auto-fetch project_id if not provided
    if not project_id:
        project_id = get_project_id_for_region(region, ak, sk)
    
    if project_id:
        credentials = BasicCredentials(ak=ak, sk=sk, project_id=project_id)
    else:
        credentials = BasicCredentials(ak=ak, sk=sk)

    endpoint = f"aom.{region}.myhuaweicloud.com"
    return AomClient.new_builder() \
        .with_credentials(credentials) \
        .with_endpoint(endpoint) \
        .build()

def create_cce_client(region: str, ak: str, sk: str, project_id: str = None):
    """Create CCE (Cloud Container Engine) client

    Note: Using public CCE endpoint.
    """
    # Auto-fetch project_id if not provided
    if not project_id:
        project_id = get_project_id_for_region(region, ak, sk)
    
    if project_id:
        credentials = BasicCredentials(ak=ak, sk=sk, project_id=project_id)
    else:
        credentials = BasicCredentials(ak=ak, sk=sk)

    # Use public CCE endpoint
    endpoint = CCE_ENDPOINTS.get(region, f"cce.{region}.myhuaweicloud.com")

    return CceClient.new_builder() \
        .with_credentials(credentials) \
        .with_endpoint(endpoint) \
        .build()

def create_evs_client(region: str, ak: str, sk: str, project_id: str = None):
    """Create EVS (Elastic Volume Service) client"""
    # Auto-fetch project_id if not provided
    if not project_id:
        project_id = get_project_id_for_region(region, ak, sk)
    
    if project_id:
        credentials = BasicCredentials(ak=ak, sk=sk, project_id=project_id)
    else:
        credentials = BasicCredentials(ak=ak, sk=sk)

    endpoint = EVS_ENDPOINTS.get(region, f"evs.{region}.myhuaweicloud.com")
    return EvsClient.new_builder() \
        .with_credentials(credentials) \
        .with_endpoint(endpoint) \
        .build()

def create_eip_client(region: str, ak: str, sk: str, project_id: str = None):
    """Create EIP (Elastic IP) client"""
    # Auto-fetch project_id if not provided
    if not project_id:
        project_id = get_project_id_for_region(region, ak, sk)
    
    if project_id:
        credentials = BasicCredentials(ak=ak, sk=sk, project_id=project_id)
    else:
        credentials = BasicCredentials(ak=ak, sk=sk)

    endpoint = EIP_ENDPOINTS.get(region, f"vpc.{region}.myhuaweicloud.com")
    return EipClient.new_builder() \
        .with_credentials(credentials) \
        .with_endpoint(endpoint) \
        .build()

def create_elb_client(region: str, ak: str, sk: str, project_id: str = None):
    """Create ELB (Elastic Load Balance) client"""
    # Auto-fetch project_id if not provided
    if not project_id:
        project_id = get_project_id_for_region(region, ak, sk)
    
    if project_id:
        credentials = BasicCredentials(ak=ak, sk=sk, project_id=project_id)
    else:
        credentials = BasicCredentials(ak=ak, sk=sk)

    endpoint = ELB_ENDPOINTS.get(region, f"elb.{region}.myhuaweicloud.com")
    return ElbClient.new_builder() \
        .with_credentials(credentials) \
        .with_endpoint(endpoint) \
        .build()

def create_iam_client(ak: str, sk: str):
    """Create IAM (Identity and Access Management) client

    IAM is a global service, so it doesn't require region-specific endpoint.
    Uses GlobalCredentials for IAM operations.
    """
    from huaweicloudsdkiam.v3 import IamClient
    credentials = GlobalCredentials(ak=ak, sk=sk)
    return IamClient.new_builder() \
        .with_credentials(credentials) \
        .with_endpoint(IAM_ENDPOINT) \
        .build()
