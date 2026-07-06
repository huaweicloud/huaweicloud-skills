#!/usr/bin/env python3
"""
Configuration constants for Huawei Cloud SQLBot Deployment
"""

import os

# ==================== Architecture Requirements ====================
# ⚠️ Important: SQLBot must be deployed on x86_64 architecture servers
# - SQLBot Docker image is built on x86_64
# - ARM64 (aarch64) is not supported
# - Ensure to use x86 architecture X instance flavors (e.g., x1.4u.8g)
REQUIRED_ARCH = "x86_64"
REQUIRED_OS = "Ubuntu 22.04 Server 64-bit"

# Default configuration
DEFAULT_CONFIG = {
    "flavor": None,  # Dynamically select flavor based on region
    "image": "Ubuntu 22.04 server 64bit",  # x86_64 architecture
    "os_version": "22.04",  # Ubuntu version for dynamic image query
    "architecture": "x86_64",  # Must be x86_64
    "availability_zone": None,  # Auto-select availability zone
    "charging_mode": "postPaid",  # Pay-as-you-go
    "eip_bandwidth": 300,
    "eip_charge_mode": "traffic",  # Charged by traffic
    "admin_pass": "Test@123456",
    "sqlbot_ports": [8000]
}

# Region flavor priority mapping (supports multi-flavor priority)
# Format: region: [list of supported X instance types], ordered by priority (highest to lowest)
REGION_FLAVOR_PRIORITY = {
    # Africa-Cairo
    "af-north-1": ["x1"],
    # Africa-Johannesburg
    "af-south-1": ["x1", "x2e"],
    # China-Hong Kong
    "ap-southeast-1": ["x1", "x2e"],
    # Asia Pacific-Bangkok
    "ap-southeast-2": ["x1", "x2e"],
    # Asia Pacific-Singapore
    "ap-southeast-3": ["x1", "x1e", "x2e"],
    # Asia Pacific-Jakarta
    "ap-southeast-4": ["x1", "x2", "x2e"],
    # Asia Pacific-Manila
    "ap-southeast-5": ["x1"],
    # East China-Shanghai I
    "cn-east-3": ["x1", "x1e", "x1i", "x2e"],
    # East China II
    "cn-east-4": ["x1"],
    # East China-Qingdao
    "cn-east-5": ["x1"],
    # North China-Beijing IV
    "cn-north-4": ["x1", "x1e", "x1i", "x2e"],
    # North China-Ulanqab I
    "cn-north-9": ["x1", "x1e", "x1i", "x2e"],
    # South China-Guangzhou
    "cn-south-1": ["x1", "x1e", "x1i", "x2e"],
    # Southwest China-Guiyang I
    "cn-southwest-2": ["x1", "x1e", "x1i", "x2e"],
    # Latin America-Mexico City II
    "la-north-2": ["x0", "x1e", "x2e"],
    # Latin America-Santiago
    "la-south-2": ["x0"],
    # Middle East-Riyadh
    "me-east-1": ["x1"],
    # Latin America-Sao Paulo I
    "sa-brazil-1": ["x1"],
    # Turkey-Istanbul
    "tr-west-1": ["x1", "x2e"],
    # Default: Try X instances first
    "default": ["x1", "x2e", "x1e", "x1i", "x0", "x2"]
}

# Flavor mapping table (fallback solution for generating specific flavor names)
# Only X instance flavors are supported
REGION_FLAVOR_MAP = {
    # Beijing IV: X instance (x1 series)
    "cn-north-4": "x1.4u.8g",
    # South China-Guangzhou: X instance
    "cn-south-1": "x1.4u.8g",
    # Shanghai I: X instance
    "cn-east-3": "x1.4u.8g",
    # East China-Shanghai II: X instance
    "cn-east-2": "x1.4u.8g",
    # Southwest China-Guiyang I: X instance
    "cn-southwest-2": "x1.4u.8g",
    # Asia Pacific-Singapore: X instance
    "ap-southeast-3": "x1e.4u.8g",
    # Asia Pacific-Bangkok: X instance
    "ap-southeast-2": "x1.4u.8g",
    # Africa-Johannesburg: X instance
    "af-south-1": "x1.4u.8g",
    # Default: Try X instance first
    "default": "x1.4u.8g"
}

# Flavor series priority (highest to lowest) - X instances only
FLAVOR_SERIES_PRIORITY = ["x", "x1e", "x2", "x2e", "x1i", "x0"]

# Flavor description mapping - X instances only
FLAVOR_DESCRIPTION = {
    "x1.4u.8g": "X Instance (4vCPU 8GB)",
    "x1e.4u.8g": "X Instance Enhanced (4vCPU 8GB)",
    "x2.4u.8g": "X Instance v2 (4vCPU 8GB)",
    "x2e.4u.8g": "X Instance v2 Enhanced (4vCPU 8GB)",
    "x1i.4u.8g": "X Instance Intel (4vCPU 8GB)",
    "x0.4u.8g": "X Instance Basic (4vCPU 8GB)",
    "kx1.4u.8g": "K Series X Instance (4vCPU 8GB)",
    "default": "Dynamically selected X instance flavor"
}

# Lock file path
LOCK_FILE = "/tmp/sqlbot_deploy.lock"

# OpenClaw Gateway URL (used for sending notification messages)
GATEWAY_URL = os.environ.get("OPENCLAW_GATEWAY_URL", "http://localhost:18789")
GATEWAY_TOKEN = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")

# Feishu notification settings
# User ID for notifications - set via NOTIFY_USER_ID env var or --notify-user-id argument
NOTIFY_USER_ID = os.environ.get("NOTIFY_USER_ID", "")

# Global variable: Whether to enable Feishu notification (enabled by default)
ENABLE_FEISHU_NOTIFY = True

# OBS script URL for SQLBot installation
OBS_SCRIPT_URL = "https://documentation-samples.obs.cn-north-4.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-moudle/quickly_implement_intelligent_data_queries_based_on_sqlbot/userdata/install-sqlbot.sh"

# Region name mapping for display
REGION_NAMES = {
    "af-north-1": "非洲-开罗",
    "af-south-1": "非洲-约翰内斯堡",
    "ap-southeast-1": "中国-香港",
    "ap-southeast-2": "亚太-曼谷",
    "ap-southeast-3": "亚太-新加坡",
    "ap-southeast-4": "亚太-雅加达",
    "ap-southeast-5": "亚太-马尼拉",
    "cn-east-3": "华东-上海一",
    "cn-east-4": "华东二",
    "cn-east-5": "华东-青岛",
    "cn-north-4": "华北-北京四",
    "cn-north-9": "华北-乌兰察布一",
    "cn-south-1": "华南-广州",
    "cn-southwest-2": "西南-贵阳一",
    "la-north-2": "拉美-墨西哥城二",
    "la-south-2": "拉美-圣地亚哥",
    "me-east-1": "中东-利雅得",
    "sa-brazil-1": "拉美-圣保罗一",
    "tr-west-1": "土耳其-伊斯坦布尔",
}
