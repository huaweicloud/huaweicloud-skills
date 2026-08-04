"""Common Huawei Cloud helpers shared by service modules."""

from __future__ import annotations

import base64
import os
import re
import secrets
import string
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

from huaweicloudsdkcore.auth.credentials import GlobalCredentials, BasicCredentials
from huaweicloudsdkcce.v3 import *
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

CCE_ENDPOINTS = {
    "cn-north-4": "cce.cn-north-4.myhuaweicloud.com", "cn-north-1": "cce.cn-north-1.myhuaweicloud.com", "cn-north-9": "cce.cn-north-9.myhuaweicloud.com",
    "cn-east-3": "cce.cn-east-3.myhuaweicloud.com", "cn-east-2": "cce.cn-east-2.myhuaweicloud.com", "cn-south-1": "cce.cn-south-1.myhuaweicloud.com",
    "cn-southwest-2": "cce.cn-southwest-2.myhuaweicloud.com", "cn-west-3": "cce.cn-west-3.myhuaweicloud.com", "ap-southeast-1": "cce.ap-southeast-1.myhuaweicloud.com",
    "ap-southeast-2": "cce.ap-southeast-2.myhuaweicloud.com", "ap-southeast-3": "cce.ap-southeast-3.myhuaweicloud.com", "ap-southeast-4": "cce.ap-southeast-4.myhuaweicloud.com",
    "af-south-1": "cce.af-south-1.myhuaweicloud.com", "la-south-2": "cce.la-south-2.myhuaweicloud.com", "la-north-2": "cce.la-north-2.myhuaweicloud.com",
    "eu-west-0": "cce.eu-west-0.myhuaweicloud.com", "ap-northeast-1": "cce.ap-northeast-1.myhuaweicloud.com",
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

def create_cce_client(region: str, ak: str, sk: str, project_id: str = None, security_token: str = None):
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

    if security_token:
        credentials = credentials.with_security_token(security_token)

    # Use public CCE endpoint
    endpoint = CCE_ENDPOINTS.get(region, f"cce.{region}.myhuaweicloud.com")

    return CceClient.new_builder() \
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

def generate_random_password(length: int = 16) -> str:
    """Generate a random password with >=3 character categories."""
    upper = string.ascii_uppercase
    lower = string.ascii_lowercase
    digits = string.digits
    special = '!@#$%^&*()-_=+[]{}:,.?'
    all_chars = upper + lower + digits + special
    while True:
        pw = ''.join(secrets.choice(all_chars) for _ in range(length))
        cats = sum([
            bool(re.search(r'[A-Z]', pw)),
            bool(re.search(r'[a-z]', pw)),
            bool(re.search(r'[0-9]', pw)),
            bool(re.search(r'[!@#$%^&*()\-_=+\[\]{}:,.?]', pw)),
        ])
        if cats >= 3:
            return pw

def salt_password(password: str) -> str:
    """SHA-512 crypt + base64 encode, per CCE API requirement."""
    try:
        from passlib.hash import sha512_crypt
        hashed = sha512_crypt.using(rounds=5000).hash(password)
    except ImportError:
        import crypt
        salt = '$6$' + ''.join(secrets.choice(string.ascii_letters + string.digits + './') for _ in range(16))
        hashed = crypt.crypt(password, salt)
    return base64.b64encode(hashed.encode('utf-8')).decode('utf-8')

def resolve_node_login(ssh_key=None, password=None):
    """
    Returns (login_config_dict, was_auto_generated).
    Priority: ssh_key > password param > CCE_NODE_PASSWORD env > auto-generate.
    The raw auto-generated password is NEVER returned in tool responses.
    """
    if ssh_key:
        return {'sshKey': ssh_key}, False

    raw_password = password or os.environ.get('CCE_NODE_PASSWORD')
    was_auto = False
    if not raw_password:
        raw_password = generate_random_password()
        was_auto = True

    salted = salt_password(raw_password)
    return {'userPassword': {'username': 'root', 'password': salted}}, was_auto
