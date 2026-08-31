#!/usr/bin/env python3
"""
Configuration constants for Huawei Cloud Flexus X + DeepSeek Harness (dsh) Deployment
"""

import os
import tempfile

REQUIRED_ARCH = "x86_64"
REQUIRED_OS = "Ubuntu 22.04 Server 64-bit"

DEFAULT_CONFIG = {
    "flavor": "x1.2u.4g",
    "image": "Ubuntu 22.04 server 64bit",
    "os_version": "22.04",
    "architecture": "x86_64",
    "availability_zone": None,
    "charging_mode": "postPaid",
    "eip_bandwidth": 100,
    "eip_charge_mode": "traffic",
    "admin_pass": None,
    "system_disk_size": 40
}

# DeepSeek Harness (dsh) defaults
DSH_DEFAULT_PORT = 3080

REGION_FLAVOR_PRIORITY = {
    "cn-north-4": ["x1", "x1e", "x1i", "x2e"],
    "cn-north-9": ["x1", "x1e", "x1i", "x2e"],
    "cn-east-3": ["x1", "x1e", "x1i", "x2e"],
    "cn-east-4": ["x1"],
    "cn-east-5": ["x1"],
    "cn-south-1": ["x1", "x1e", "x1i", "x2e"],
    "cn-southwest-2": ["x1", "x1e", "x1i", "x2e"],
    "ap-southeast-1": ["x1", "x2e"],
    "ap-southeast-2": ["x1", "x2e"],
    "ap-southeast-3": ["x1", "x1e", "x2e"],
    "ap-southeast-4": ["x1", "x2", "x2e"],
    "ap-southeast-5": ["x1"],
    "me-east-1": ["x1"],
    "af-north-1": ["x1"],
    "af-south-1": ["x1", "x2e"],
    "tr-west-1": ["x1", "x2e"],
    "la-north-2": ["x0", "x1e", "x2e"],
    "sa-brazil-1": ["x1"],
    "la-south-2": ["x0"],
    "default": ["x1", "x2e", "x1e", "x1i", "x0", "x2"]
}

REGION_FLAVOR_MAP = {
    "cn-north-4": "x1.2u.4g",
    "cn-north-9": "x1.2u.4g",
    "cn-east-3": "x1.2u.4g",
    "cn-east-4": "x1.2u.4g",
    "cn-east-5": "x1.2u.4g",
    "cn-south-1": "x1.2u.4g",
    "cn-southwest-2": "x1.2u.4g",
    "ap-southeast-1": "x1.2u.4g",
    "ap-southeast-2": "x1.2u.4g",
    "ap-southeast-3": "x1e.2u.4g",
    "ap-southeast-4": "x1.2u.4g",
    "ap-southeast-5": "x1.2u.4g",
    "me-east-1": "x1.2u.4g",
    "af-north-1": "x1.2u.4g",
    "af-south-1": "x1.2u.4g",
    "tr-west-1": "x1.2u.4g",
    "la-north-2": "x1.2u.4g",
    "sa-brazil-1": "x1.2u.4g",
    "la-south-2": "x0.2u.4g",
    "default": "x1.2u.4g"
}

FLAVOR_DESCRIPTION = {
    "x1.2u.4g": "Flexus X Instance (2vCPU 4GB)",
    "x1e.2u.4g": "Flexus X Instance Enhanced (2vCPU 4GB)",
    "x2.2u.4g": "Flexus X Instance v2 (2vCPU 4GB)",
    "x2e.2u.4g": "Flexus X Instance v2 Enhanced (2vCPU 4GB)",
    "x1i.2u.4g": "Flexus X Instance Intel (2vCPU 4GB)",
    "x0.2u.4g": "Flexus X Instance Basic (2vCPU 4GB)",
    "x1.4u.8g": "Flexus X Instance (4vCPU 8GB)",
    "x1e.4u.8g": "Flexus X Instance Enhanced (4vCPU 8GB)",
    "x2.4u.8g": "Flexus X Instance v2 (4vCPU 8GB)",
    "x2e.4u.8g": "Flexus X Instance v2 Enhanced (4vCPU 8GB)",
    "x1i.4u.8g": "Flexus X Instance Intel (4vCPU 8GB)",
    "x0.4u.8g": "Flexus X Instance Basic (4vCPU 8GB)",
    "x1.8u.16g": "Flexus X Instance (8vCPU 16GB)",
    "x1e.8u.16g": "Flexus X Instance Enhanced (8vCPU 16GB)",
    "x2.8u.16g": "Flexus X Instance v2 (8vCPU 16GB)",
    "x2e.8u.16g": "Flexus X Instance v2 Enhanced (8vCPU 16GB)",
    "kx1.4u.8g": "K Series Flexus X Instance (4vCPU 8GB)",
    "default": "Dynamically selected Flexus X instance flavor"
}

LOCK_FILE = os.path.join(tempfile.gettempdir(), "dsh_deploy.lock")

NOTIFY_USER_ID = os.environ.get("NOTIFY_USER_ID", "")
ENABLE_FEISHU_NOTIFY = False

REGION_NAMES = {
    "cn-north-4": "华北-北京四",
    "cn-north-9": "华北-乌兰察布一",
    "cn-east-3": "华东-上海一",
    "cn-east-4": "华东二",
    "cn-east-5": "华东-青岛",
    "cn-south-1": "华南-广州",
    "cn-southwest-2": "西南-贵阳一",
    "ap-southeast-1": "中国-香港",
    "ap-southeast-2": "亚太-曼谷",
    "ap-southeast-3": "亚太-新加坡",
    "ap-southeast-4": "亚太-雅加达",
    "ap-southeast-5": "亚太-马尼拉",
    "me-east-1": "中东-利雅得",
    "af-north-1": "非洲-开罗",
    "af-south-1": "非洲-约翰内斯堡",
    "tr-west-1": "土耳其-伊斯坦布尔",
    "la-north-2": "拉美-墨西哥城二",
    "sa-brazil-1": "拉美-圣保罗一",
    "la-south-2": "拉美-圣地亚哥",
}
