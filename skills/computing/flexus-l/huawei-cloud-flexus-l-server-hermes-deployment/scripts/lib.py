#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click Hermes Deployment Core Module
Includes:
1. L Instance creation functionality
2. COC script management (create script, execute script, query script)
3. ModelArts large model configuration
4. Bot channel configuration

Note: This module only supports temporary credentials (temporary AK/SK + security_token).
      Permanent AK/SK credentials are not supported.
"""

import json
import os
import logging
import requests
import uuid
from datetime import datetime
from urllib.parse import urlparse
from typing import Any, Optional, List, Dict

from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkcoc.v1.region.coc_region import CocRegion
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkcoc.v1 import *
from huaweicloudsdkcoc.v1.model.script_execute_model import ScriptExecuteModel
from huaweicloudsdkcoc.v1.model.script_execute_param import ScriptExecuteParam
from huaweicloudsdkcoc.v1.model.execute_instances_batch_info import ExecuteInstancesBatchInfo
from huaweicloudsdkcoc.v1.model.execute_resource_instance import ExecuteResourceInstance
from huaweicloudsdkcoc.v1.model.script_properties_model import ScriptPropertiesModel
from huaweicloudsdkcoc.v1.model.add_script_model import AddScriptModel

logger = logging.getLogger(__name__)

# Constants definition
VALID_SCRIPT_TYPES = ["SHELL", "PYTHON", "BAT"]
VALID_RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"]
VALID_ROTATION_STRATEGIES = ["CONTINUE", "STOP"]

# Default configuration
DEFAULT_BASE_URL = "https://api.modelarts-maas.com/v2"
DEFAULT_CONFIG_PATH = "/home/hermes/.hermes/config.yaml"
DEFAULT_ENV_PATH = "/home/hermes/.hermes/.env"

class Credentials:
    """Credentials for Huawei Cloud temporary access"""
    def __init__(self, ak, sk, security_token):
        self.ak = ak
        self.sk = sk
        self.security_token = security_token


def get_credentials(ak, sk, region=None):
    """Get Huawei Cloud credentials (parameter passing)"""
    if not ak or not sk:
        raise ValueError("ak and sk are required parameters")
    if not region:
        region = "cn-north-4"
    return ak, sk, region


def get_project_id_by_region(ak: str, sk: str, security_token: str, region: str) -> Optional[str]:
    """
    Get Project ID for specified region via AK/SK
    
    Args:
        ak: Huawei Cloud temporary AK
        sk: Huawei Cloud temporary SK
        security_token: Security token for temporary credentials (required)
        region: Target region, e.g. cn-north-4, cn-southwest-2
    
    Returns:
        Project ID string, or None if failed
    """
    if not ak or not sk or not security_token:
        print("Error: Credentials not configured")
        return None
    
    iam_endpoint = f"https://iam.{region}.myhuaweicloud.com/v3/projects"
    
    try:
        from huaweicloudsdkcore.signer.signer import Signer
        from huaweicloudsdkcore.sdk_request import SdkRequest
        
        credentials = Credentials(ak, sk, security_token)
        signer = Signer(credentials)
        
        request = SdkRequest()
        request.method = "GET"
        request.schema = "https"
        request.host = f"iam.{region}.myhuaweicloud.com"
        request.resource_path = "/v3/projects"
        request.body = ""
        request.header_params = {
            "Content-Type": "application/json",
            "Client-Request-Id": str(uuid.uuid4()),
            "X-Security-Token": security_token
        }
        
        request.query_params = []
        
        signed_request = signer.sign(request)
        
        headers = {}
        for key, value in signed_request.header_params.items():
            if isinstance(value, bytes):
                headers[key] = value.decode('iso-8859-1')
            else:
                headers[key] = str(value)
        
        print(f"Getting Project ID - Request URL: {iam_endpoint}")
        
        resp = requests.get(iam_endpoint, headers=headers, timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            projects = data.get('projects', [])
            if projects:
                for project in projects:
                    project_name = project.get('name', '')
                    if project_name == region:
                        return project.get('id')
                return projects[0].get('id')
            else:
                print("Error: Project not found")
                return None
        else:
            print(f"Failed to get Project ID - Status code: {resp.status_code}, Response: {resp.text}")
            return None
            
    except ImportError as e:
        print(f"SDK import failed: {str(e)}")
        return None
    except Exception as e:
        print(f"Error getting Project ID: {str(e)}")
        return None


def create_hermes_instance(ak, sk, security_token, instance_name=None, region=None):
    """
    Create Huawei Cloud Flexus L Instance dedicated for Hermes
    
    Parameters:
        ak: Huawei Cloud temporary AK
        sk: Huawei Cloud temporary SK
        security_token: Security token for temporary credentials (required)
        instance_name: Instance name, optional, auto-generated as hermes-timestamp if not specified
        region: Target region, optional, default cn-north-4 if not specified
    
    Returns:
        dict: Result dictionary containing ok, text, result, error fields
    """
    if not ak or not sk or not security_token:
        return {
            "ok": False,
            "text": "Credentials not configured",
            "result": None,
            "error": {
                "code": "CONFIG_ERROR",
                "message": "ak, sk and security_token are required parameters"
            }
        }
    
    target_region = region if region else "cn-north-4"
    
    project_id = get_project_id_by_region(ak, sk, security_token, target_region)
    if not project_id:
        return {
            "ok": False,
            "text": "Failed to get Project ID",
            "result": None,
            "error": {
                "code": "PROJECT_ID_ERROR",
                "message": f"Failed to get Project ID for region {target_region}, please check credentials"
            }
        }
    
    if not instance_name:
        instance_name = f"hermes-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    endpoint = "https://hcss.cn-north-4.myhuaweicloud.com/v1/light-instances"
    
    if target_region == "cn-southwest-2":
        plan_spec = "ahf.small.1.linux"
    else:
        plan_spec = "hf.small.1.linux"
    
    request_body = {
        "instance_name": instance_name,
        "plan_spec": plan_spec,
        "image_ref": {
            "image_name": "Hermes",
            "image_version": "0.9.0"
        },
        "region": target_region,
        "charging_mode": "prePaid",
        "period_type": "month",
        "period_num": 1,
        "purchase_quantity": 1,
        "description": "Hermes one-click deployment",
        "is_auto_renew": True,
        "is_auto_pay": True,
        "extra_resources": [
            {"type": "evs", "size": 50},
            {"type": "cbr", "size": 50},
            {"type": "hss"}
        ]
    }
    
    try:
        from huaweicloudsdkcore.signer.signer import Signer
        from huaweicloudsdkcore.sdk_request import SdkRequest
        
        credentials = Credentials(ak, sk, security_token)
        signer = Signer(credentials)
        
        parsed_url = urlparse(endpoint)
        body_str = json.dumps(request_body, ensure_ascii=False, separators=(',', ':'))
        
        request = SdkRequest()
        request.method = "POST"
        request.schema = parsed_url.scheme
        request.host = parsed_url.hostname
        request.resource_path = parsed_url.path
        request.body = body_str
        request.header_params = {
            "X-Project-Id": project_id,
            "Content-Type": "application/json",
            "Client-Request-Id": str(uuid.uuid4())
        }
        
        if security_token:
            request.header_params["X-Security-Token"] = security_token
        
        request.query_params = []
        
        signed_request = signer.sign(request)
        
        headers = {}
        for key, value in signed_request.header_params.items():
            if isinstance(value, bytes):
                headers[key] = value.decode('iso-8859-1')
            else:
                headers[key] = str(value)
        
        # Send instance creation request
        print(f"  Sending instance creation request...")
        
        resp = requests.request(
            "POST",
            endpoint,
            headers=headers,
            data=body_str.encode('utf-8'),
            verify=True
        )
        
        # Output HTTP status code immediately to let user know request is processed
        print(f"  HTTP Status Code: {resp.status_code}")
        
        if resp.status_code in [200, 201, 202]:
            print(f"  ✓ Instance creation request submitted successfully")
        else:
            print(f"  ✗ Request failed: {resp.reason}")
        
        if resp.status_code in [200, 201, 202]:
            response_data = resp.json()
            return {
                "ok": True,
                "text": f"Instance creation request submitted, Instance ID: {response_data.get('instance_id', 'unknown')}",
                "result": response_data,
                "error": None
            }
        else:
            return {
                "ok": False,
                "text": f"Instance creation failed: {resp.reason}",
                "result": None,
                "error": {
                    "code": str(resp.status_code),
                    "message": resp.text
                }
            }
    
    except ImportError as e:
        return {
            "ok": False,
            "text": "SDK import failed",
            "result": None,
            "error": {
                "code": "SDK_ERROR",
                "message": f"Please install huaweicloudsdkcore: {str(e)}"
            }
        }
    except Exception as e:
        return {
            "ok": False,
            "text": f"Error occurred while creating instance: {str(e)}",
            "result": None,
            "error": {
                "code": "UNKNOWN_ERROR",
                "message": str(e)
            }
        }


# Hermes script templates
HERMES_SCRIPT_TEMPLATES = {
    "install_maas": {
        "name": "Hermes-MaaS-Model-Install",
        "type": "SHELL",
        "description": "Configure ModelArts large model on Hermes instance",
        "risk_level": "MEDIUM",
        "content": '''#!/bin/bash
# Hermes ModelArts Large Model Configuration Script

API_KEY='${api_key}'
MODEL_NAME='${model_name}'
API_BASE_URL='${api_base_url}'
CONFIG_PATH='/home/hermes/.hermes/config.yaml'

echo "=== Hermes ModelArts Large Model Configuration ==="
echo "API Key: ${API_KEY:0:8}****"
echo "Model Name: $MODEL_NAME"
echo "API Base URL: $API_BASE_URL"
echo "Config File: $CONFIG_PATH"

# Check and install yq (YAML version of jq)
if ! command -v yq &> /dev/null; then
    echo ""
    echo "Installing yq..."
    # Try package manager installation
    if command -v apt-get &> /dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y -qq yq 2>/dev/null
    elif command -v yum &> /dev/null; then
        sudo yum install -y -q yq 2>/dev/null
    fi
    
    # If package manager installation failed, download binary directly
    if ! command -v yq &> /dev/null; then
        echo "Package manager installation failed, trying direct download..."
        if command -v curl &> /dev/null; then
            sudo curl -sL https://github.com/mikefarah/yq/releases/download/v4.35.1/yq_linux_amd64 -o /usr/local/bin/yq
        else
            sudo wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/download/v4.35.1/yq_linux_amd64
        fi
        sudo chmod +x /usr/local/bin/yq
    fi
    
    if command -v yq &> /dev/null; then
        echo "yq installed successfully"
    else
        echo "Error: Failed to install yq, please install manually!"
        exit 1
    fi
fi

# Create config directory if not exists
mkdir -p /home/hermes/.hermes

# Create default config if config file doesn't exist
if [ ! -f "$CONFIG_PATH" ]; then
    echo "Config file not found, creating default config..."
    cat > "$CONFIG_PATH" << 'EOFCONFIG'
model:
  default: ""
  base_url: ""
  api_key: ""
  provider: custom
EOFCONFIG
fi

# Update config using Python script (compatible with all environments)
echo ""
echo "Starting configuration update..."

python3 -c "
import yaml
import sys

config_path = '$CONFIG_PATH'
model_name = '$MODEL_NAME'
api_base_url = '$API_BASE_URL'
api_key = '$API_KEY'

with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

if 'model' not in config:
    config['model'] = {}

config['model']['default'] = model_name
config['model']['base_url'] = api_base_url
config['model']['api_key'] = api_key
config['model']['provider'] = 'custom'

with open(config_path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

print('  Updated model.default:', model_name)
print('  Updated model.base_url:', api_base_url)
print('  Updated model.api_key:', api_key[:8] + '****')
"

echo ""
echo "Configuration update completed!"

# Verify configuration
echo ""
echo "Configuration verification:"
echo "  model.default: $(grep "^  default:" "$CONFIG_PATH" | sed 's/  default: //')"
echo "  model.base_url: $(grep "^  base_url:" "$CONFIG_PATH" | sed 's/  base_url: //')"
echo "  model.api_key: $(grep "^  api_key:" "$CONFIG_PATH" | sed 's/  api_key: //' | cut -c1-8)****"

echo ""
echo "=== Configuration Completed ==="
echo ""
echo "Tip: Configuration updated, please restart Hermes service manually to apply changes"
echo "   Recommended: hermes start or systemctl restart hermes"
'''
    },
    "install_channel": {
        "name": "Hermes-Channel-Install",
        "type": "SHELL",
        "description": "Configure bot channels on Hermes instance (Feishu/WeCom)",
        "risk_level": "MEDIUM",
        "content": '''#!/bin/bash
# Hermes Bot Channel Configuration Script
BOT_PLATFORM='${bot_platform}'
FEISHU_APP_ID='${feishu_app_id}'
FEISHU_APP_SECRET='${feishu_app_secret}'
WECOM_BOT_ID='${wecom_bot_id}'
WECOM_SECRET='${wecom_secret}'
ENV_PATH='/home/hermes/.hermes/.env'

echo "⚙️  Configuring bot channel..."
echo " - Target Platform: $BOT_PLATFORM"

# Set environment variable function
set_env_variable() {
    local env_file="$1"
    local key="$2"
    local value="$3"
    
    if grep -q "^[#]\\?[[:space:]]*$key=" "$env_file"; then
        sed -i.bak "s/^[#]\\?[[:space:]]*$key=.*/$key=$value/" "$env_file"
        rm -f "$env_file.bak"
    else
        echo "" >> "$env_file"
        echo "# Auto injected by setup script" >> "$env_file"
        echo "$key=$value" >> "$env_file"
    fi
}

# Configure based on platform type
if [ "$BOT_PLATFORM" = "feishu" ]; then
    echo "Configuring Feishu channel..."
    set_env_variable "$ENV_PATH" "FEISHU_APP_ID" "$FEISHU_APP_ID"
    set_env_variable "$ENV_PATH" "FEISHU_APP_SECRET" "$FEISHU_APP_SECRET"
    set_env_variable "$ENV_PATH" "FEISHU_DOMAIN" "feishu"
    set_env_variable "$ENV_PATH" "FEISHU_CONNECTION_MODE" "websocket"
    set_env_variable "$ENV_PATH" "FEISHU_ALLOW_ALL_USERS" "true"
    set_env_variable "$ENV_PATH" "FEISHU_ALLOWED_USERS" ""
    set_env_variable "$ENV_PATH" "FEISHU_GROUP_POLICY" "open"
    set_env_variable "$ENV_PATH" "GATEWAY_ALLOW_ALL_USERS" "true"
    echo "✅ Feishu configuration written successfully"

elif [ "$BOT_PLATFORM" = "wecom" ]; then
    echo "Configuring WeCom channel..."
    set_env_variable "$ENV_PATH" "WECOM_BOT_ID" "$WECOM_BOT_ID"
    set_env_variable "$ENV_PATH" "WECOM_SECRET" "$WECOM_SECRET"
    set_env_variable "$ENV_PATH" "GATEWAY_ALLOW_ALL_USERS" "true"
    echo "✅ WeCom configuration written successfully"
fi

echo "✅ $ENV_PATH updated successfully!"
echo ""
echo "Tip: Configuration updated, please restart Hermes service manually to apply changes"
echo "   Recommended: hermes start or systemctl restart hermes"
'''
    },
    "restart_gateway": {
        "name": "Hermes-Gateway-Restart",
        "type": "SHELL",
        "description": "Restart Hermes gateway service",
        "risk_level": "LOW",
        "content": '''#!/bin/bash
# Hermes Gateway Restart Script

echo "=== Hermes Gateway Restart ==="

# Switch to hermes user and execute restart command
su - hermes -c "hermes gateway restart"

if [ $? -eq 0 ]; then
    echo "✓ Hermes gateway restarted successfully"
else
    echo "✗ Hermes gateway restart failed"
    exit 1
fi
'''
    }
}


def install_maas_models_remote(
    resource_id: str,
    region_id: str,
    api_key: str = "",
    model_name: str = "",
    api_base_url: str = "https://api.modelarts-maas.com/v2",
    timeout: int = 600,
    execute_user: str = "root",
    ak: str = "",
    sk: str = "",
    security_token: str = None,
    coc_region: str = None
) -> dict[str, Any]:
    """
    Configure ModelArts large model on remote L instance via COC
    
    Parameters:
        resource_id: L Instance resource ID
        region_id: L Instance region
        api_key: ModelArts API Key
        model_name: Large model name (e.g.: deepseek-v3.2, qwen-plus, glm-4)
        api_base_url: API Base URL, default: https://api.modelarts-maas.com/v2
        timeout: Execution timeout in seconds, default 600
        execute_user: Execute user, default root
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials (optional)
        coc_region: COC region (optional, default cn-north-4)
    
    Returns:
        {
            "ok": True,
            "text": "Script execution started: SCT2023083109562601af694bf",
            "result": {...},
            "error": None
        }
    """
    if not ak or not sk:
        return {
            "ok": False,
            "text": "Credentials not configured",
            "result": None,
            "error": {
                "code": "CONFIG_ERROR",
                "message": "ak and sk are required parameters"
            }
        }
    
    import time
    script_info = HERMES_SCRIPT_TEMPLATES["install_maas"]
    
    # Replace variables in template
    content = script_info["content"]
    content = content.replace("${api_key}", api_key if api_key else "")
    content = content.replace("${model_name}", model_name if model_name else "")
    content = content.replace("${api_base_url}", api_base_url if api_base_url else "https://api.modelarts-maas.com/v2")
    
    create_result = create_script(
        name=f"{script_info['name']}-{int(time.time())}",
        script_type=script_info["type"],
        content=content,
        description=script_info["description"],
        ak=ak,
        sk=sk,
        security_token=security_token,
        region=coc_region,
        risk_level=script_info["risk_level"]
    )
    
    if not create_result.get("ok"):
        return create_result
    
    script_uuid = create_result.get("result", {}).get("script_uuid")
    
    if not script_uuid:
        # Compatible with older response format
        result_data = create_result.get("result")
        if hasattr(result_data, 'data'):
            script_uuid = result_data.data
    
    target_instances = [{
        "resource_id": resource_id,
        "region_id": region_id,
        "provider": "HCSS",
        "type": "L-INSTANCE"
    }]
    
    execute_result = execute_script(
        script_uuid=script_uuid,
        execute_user=execute_user,
        timeout=timeout,
        success_rate=100.0,
        target_instances=target_instances,
        ak=ak,
        sk=sk,
        security_token=security_token,
        region=coc_region,
        rotation_strategy="CONTINUE"
    )
    
    return execute_result


def install_channel_remote(
    resource_id: str,
    region_id: str,
    bot_platform: str = "",
    feishu_app_id: str = "",
    feishu_app_secret: str = "",
    wecom_bot_id: str = "",
    wecom_secret: str = "",
    timeout: int = 600,
    execute_user: str = "root",
    ak: str = "",
    sk: str = "",
    security_token: str = None,
    coc_region: str = None
) -> dict[str, Any]:
    """
    Configure bot channel on remote L instance via COC
    
    Parameters:
        resource_id: L Instance resource ID
        region_id: L Instance region
        bot_platform: Bot platform: feishu or wecom
        feishu_app_id: Feishu App ID (required when feishu platform is selected)
        feishu_app_secret: Feishu App Secret (required when feishu platform is selected)
        wecom_bot_id: WeCom Bot ID (required when wecom platform is selected)
        wecom_secret: WeCom Secret (required when wecom platform is selected)
        timeout: Execution timeout in seconds, default 600
        execute_user: Execute user, default root
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials (optional)
        coc_region: COC region (optional, default cn-north-4)
    
    Returns:
        {
            "ok": True,
            "text": "Script execution started: SCT2023083109562601af694bf",
            "result": {...},
            "error": None
        }
    """
    if not ak or not sk:
        return {
            "ok": False,
            "text": "Credentials not configured",
            "result": None,
            "error": {
                "code": "CONFIG_ERROR",
                "message": "ak and sk are required parameters"
            }
        }
    
    import time
    script_info = HERMES_SCRIPT_TEMPLATES["install_channel"]
    
    # Replace variables in template
    content = script_info["content"]
    content = content.replace("${bot_platform}", bot_platform if bot_platform else "")
    content = content.replace("${feishu_app_id}", feishu_app_id if feishu_app_id else "")
    content = content.replace("${feishu_app_secret}", feishu_app_secret if feishu_app_secret else "")
    content = content.replace("${wecom_bot_id}", wecom_bot_id if wecom_bot_id else "")
    content = content.replace("${wecom_secret}", wecom_secret if wecom_secret else "")
    
    create_result = create_script(
        name=f"{script_info['name']}-{int(time.time())}",
        script_type=script_info["type"],
        content=content,
        description=script_info["description"],
        ak=ak,
        sk=sk,
        security_token=security_token,
        region=coc_region,
        risk_level=script_info["risk_level"]
    )
    
    if not create_result.get("ok"):
        return create_result
    
    script_uuid = create_result.get("result", {}).get("script_uuid")
    
    if not script_uuid:
        # Compatible with older response format
        result_data = create_result.get("result")
        if hasattr(result_data, 'data'):
            script_uuid = result_data.data
    
    target_instances = [{
        "resource_id": resource_id,
        "region_id": region_id,
        "provider": "HCSS",
        "type": "L-INSTANCE"
    }]
    
    execute_result = execute_script(
        script_uuid=script_uuid,
        execute_user=execute_user,
        timeout=timeout,
        success_rate=100.0,
        target_instances=target_instances,
        ak=ak,
        sk=sk,
        security_token=security_token,
        region=coc_region,
        rotation_strategy="CONTINUE"
    )
    
    return execute_result


def restart_gateway_remote(
    resource_id: str,
    region_id: str,
    timeout: int = 120,
    execute_user: str = "root",
    ak: str = "",
    sk: str = "",
    security_token: str = None,
    coc_region: str = None
) -> dict[str, Any]:
    """
    Restart Hermes gateway on remote L instance via COC
    
    Parameters:
        resource_id: L Instance resource ID
        region_id: L Instance region
        timeout: Execution timeout in seconds, default 120
        execute_user: Execute user, default root
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials (optional)
        coc_region: COC region (optional, default cn-north-4)
    
    Returns:
        {
            "ok": True,
            "text": "Script execution started: SCT2023083109562601af694bf",
            "result": {...},
            "error": None
        }
    """
    if not ak or not sk:
        return {
            "ok": False,
            "text": "Credentials not configured",
            "result": None,
            "error": {
                "code": "CONFIG_ERROR",
                "message": "ak and sk are required parameters"
            }
        }
    
    import time
    script_info = HERMES_SCRIPT_TEMPLATES["restart_gateway"]
    
    create_result = create_script(
        name=f"{script_info['name']}-{int(time.time())}",
        script_type=script_info["type"],
        content=script_info["content"],
        description=script_info["description"],
        ak=ak,
        sk=sk,
        security_token=security_token,
        region=coc_region,
        risk_level=script_info["risk_level"]
    )
    
    if not create_result.get("ok"):
        return create_result
    
    script_uuid = create_result.get("result", {}).get("script_uuid")
    
    if not script_uuid:
        result_data = create_result.get("result")
        if hasattr(result_data, 'data'):
            script_uuid = result_data.data
    
    target_instances = [{
        "resource_id": resource_id,
        "region_id": region_id,
        "provider": "HCSS",
        "type": "L-INSTANCE"
    }]
    
    execute_result = execute_script(
        script_uuid=script_uuid,
        execute_user=execute_user,
        timeout=timeout,
        success_rate=100.0,
        target_instances=target_instances,
        ak=ak,
        sk=sk,
        security_token=security_token,
        region=coc_region,
        rotation_strategy="CONTINUE"
    )
    
    return execute_result

def get_valid_coc_regions() -> list[str]:
    """Dynamically get COC service supported regions from SDK"""
    from huaweicloudsdkcoc.v1.region.coc_region import CocRegion
    return list(CocRegion.static_fields.keys())


def get_config(ak, sk, region=None) -> tuple[str, str, str]:
    """Get AK/SK and region information (parameter passing)"""
    if not ak:
        raise ValueError("ak is required parameter")
    if not sk:
        raise ValueError("sk is required parameter")
    
    # COC region: Use passed region first, default to cn-north-4 if not provided
    # Note: COC region is different from target instance region, COC service only supports limited regions
    if not region:
        region = "cn-north-4"
    
    valid_regions = get_valid_coc_regions()
    if region not in valid_regions:
        raise ValueError(f"COC region must be one of {valid_regions}. Note: COC region is different from target instance region. Target instance region is specified by --region-id parameter")

    return ak, sk, region


def get_client(ak, sk, security_token, region=None) -> CocClient:
    """Create and return COC client (parameter passing)
    
    Args:
        ak: Huawei Cloud temporary AK
        sk: Huawei Cloud temporary SK
        security_token: Security token for temporary credentials (required)
        region: COC region (optional, default cn-north-4)
    """
    _, _, coc_region = get_config(ak, sk, region)
    
    credentials = GlobalCredentials(ak, sk).with_security_token(security_token)

    client = CocClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(CocRegion.value_of(coc_region)) \
        .build()

    return client


def create_script(
    name: str,
    script_type: str,
    content: str,
    description: str,
    ak: str,
    sk: str,
    security_token: str = None,
    region: str = None,
    risk_level: str = "LOW",
    version: str = "1.0.0",
    script_params: Optional[List[Dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Create custom script in COC"""
    if not name:
        return _error("INPUT_ERROR", "name is required")
    if script_type not in VALID_SCRIPT_TYPES:
        return _error("INPUT_ERROR", f"script_type must be one of {VALID_SCRIPT_TYPES}")
    if not content:
        return _error("INPUT_ERROR", "content is required")
    if not description:
        return _error("INPUT_ERROR", "description is required")
    if risk_level not in VALID_RISK_LEVELS:
        return _error("INPUT_ERROR", f"risk_level must be one of {VALID_RISK_LEVELS}")
    if not ak or not sk:
        return _error("CONFIG_ERROR", "ak and sk are required")

    try:
        client = get_client(ak, sk, security_token, region)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        print(f"  Creating script: {name}")
        
        request = CreateScriptRequest()
        properties = ScriptPropertiesModel(
            risk_level=risk_level,
            version=version
        )
        request.body = AddScriptModel(
            name=name,
            type=script_type,
            content=content,
            description=description,
            properties=properties
        )

        response = client.create_script(request)
        
        script_uuid = ""
        if hasattr(response, 'data'):
            script_uuid = response.data
        elif hasattr(response, 'script_uuid'):
            script_uuid = response.script_uuid
        else:
            script_uuid = str(response)

        print(f"  ✓ Script created successfully: {script_uuid}")
        
        return {
            "ok": True,
            "text": f"Script created successfully: {script_uuid}",
            "result": {"script_uuid": script_uuid},
            "error": None,
        }

    except exceptions.ClientRequestException as e:
        return _error("API_ERROR", f"{e.error_code}: {e.error_msg}")
    except Exception as e:
        return _error("UNKNOWN_ERROR", str(e))


def execute_script(
    script_uuid: str,
    execute_user: str,
    timeout: int,
    success_rate: float,
    target_instances: List[Dict[str, str]],
    ak: str,
    sk: str,
    security_token: str = None,
    region: str = None,
    rotation_strategy: str = "CONTINUE",
    wait_for_completion: bool = False,
) -> dict[str, Any]:
    """
    Execute custom script on target instances
    
    Parameters:
        script_uuid: Script UUID to execute
        execute_user: User to execute script (e.g. root)
        timeout: Execution timeout in seconds (5 < timeout < 1800)
        success_rate: Success rate (supports one decimal place, e.g. 1 or 100)
        target_instances: List of target instances, each containing:
            - resource_id: Instance ID (required)
            - region_id: Server region (required)
            - provider: Resource provider (not required for ECS, default "HCSS" for L Instance)
            - type: Resource type (not required for ECS, default "L-INSTANCE" for L Instance)
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials (optional)
        region: COC region (optional, default cn-north-4)
        rotation_strategy: Rotation strategy (CONTINUE/STOP), default CONTINUE
        wait_for_completion: Whether to wait for completion and get logs, default True

    Returns:
        {
            "ok": True,
            "text": "Script execution successful: SCT2023083109562601af694bf",
            "result": { 
                "execute_uuid": "SCT2023083109562601af694bf",
                "status": "FINISHED",
                "output": "Script execution output log...",
                "error": "Error message (if any)"
            },
            "error": None
        }
    """
    if not script_uuid:
        return _error("INPUT_ERROR", "script_uuid is required")
    if not execute_user:
        return _error("INPUT_ERROR", "execute_user is required")
    if timeout <= 5 or timeout >= 1800:
        return _error("INPUT_ERROR", "timeout must be between 5 and 1800 seconds")
    if success_rate < 0 or success_rate > 100:
        return _error("INPUT_ERROR", "success_rate must be between 0 and 100")
    if not target_instances or not isinstance(target_instances, list):
        return _error("INPUT_ERROR", "target_instances is required")
    if rotation_strategy not in VALID_ROTATION_STRATEGIES:
        return _error("INPUT_ERROR", f"rotation_strategy must be one of {VALID_ROTATION_STRATEGIES}")
    if not ak or not sk:
        return _error("CONFIG_ERROR", "ak and sk are required")

    try:
        client = get_client(ak, sk, security_token, region)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        import time
        request = ExecuteScriptRequest()
        request.script_uuid = script_uuid

        execute_param = ScriptExecuteParam(
            timeout=timeout,
            success_rate=success_rate,
            execute_user=execute_user
        )

        listTargetInstancesExecuteBatches = []
        for instance_info in target_instances:
            instance_kwargs = {
                "resource_id": instance_info.get("resource_id", ""),
                "region_id": instance_info.get("region_id", "cn-north-4")
            }
            
            provider = instance_info.get("provider")
            instance_type = instance_info.get("type")
            if provider:
                instance_kwargs["provider"] = provider
            if instance_type:
                instance_kwargs["type"] = instance_type
            
            instance = ExecuteResourceInstance(**instance_kwargs)
            listTargetInstancesExecuteBatches.append(instance)

        listExecuteBatchesbody = [
            ExecuteInstancesBatchInfo(
                batch_index=1,
                target_instances=listTargetInstancesExecuteBatches,
                rotation_strategy=rotation_strategy
            )
        ]

        request.body = ScriptExecuteModel(
            execute_batches=listExecuteBatchesbody,
            execute_param=execute_param
        )

        # Execute script API call
        response = client.execute_script(request)
        
        execute_uuid = ""
        if hasattr(response, 'data'):
            execute_uuid = response.data
        elif hasattr(response, 'execute_uuid'):
            execute_uuid = response.execute_uuid
        else:
            execute_uuid = str(response)

        # Output execution UUID immediately after API call success to notify user request is submitted
        print(f"\n✓ Script execution request submitted")
        print(f"  Execution ID: {execute_uuid}")

        if not wait_for_completion:
            return {
                "ok": True,
                "text": f"Script execution started: {execute_uuid}",
                "result": {"execute_uuid": execute_uuid},
                "error": None,
            }

        print(f"  Waiting for script execution to complete...")

        max_wait_time = timeout + 60
        wait_interval = 5
        elapsed_time = 0
        last_status = ""
        
        while elapsed_time < max_wait_time:
            query_result = coc_query_execution(execute_uuid, ak, sk, security_token, region)
            
            data = query_result.get("data", {})
            if not data:
                # Query failed, output error message and continue waiting
                error_msg = query_result.get("error", {}).get("message", "query failed")
                print(f"  Failed to query status: {error_msg}, retrying...")
                time.sleep(wait_interval)
                elapsed_time += wait_interval
                continue
            
            # Extract status and output from new format
            instances = data.get("execute_instances", [])
            if instances:
                status = instances[0].get("status", "")
                output = instances[0].get("message", "")
                error = output if status == "ABNORMAL" else ""
            else:
                status = data.get("status", "")
                output = data.get("message", "")
                error = output if status == "ABNORMAL" else ""
            
            # Output progress when status changes
            if status != last_status:
                last_status = status
                print(f"  Execution status: {status}")
            
            # Output heartbeat every 30 seconds to keep user informed
            if elapsed_time % 30 == 0:
                print(f"  Waiting... ({elapsed_time}/{max_wait_time} seconds)")
            
            if status in ["SUCCESS", "FAILED", "TIMEOUT", "CANCELLED", "FINISHED", "ABNORMAL"]:
                result_data = {
                    "execute_uuid": execute_uuid,
                    "status": status,
                    "output": output,
                    "error": error
                }
                
                if status == "FINISHED":
                    print(f"  Execution completed: SUCCESS")
                    return {
                        "ok": True,
                        "text": f"Script execution successful: {execute_uuid}",
                        "result": result_data,
                        "error": None,
                    }
                else:
                    print(f"  Execution completed: {status}")
                    error_msg = f"Script execution failed, status: {status}"
                    if error:
                        error_msg += f", error: {error}"
                    if output:
                        error_msg += f", output: {output}"
                    return {
                        "ok": False,
                        "text": error_msg,
                        "result": result_data,
                        "error": {"code": "EXECUTE_FAILED", "message": error_msg}
                    }
            
            time.sleep(wait_interval)
            elapsed_time += wait_interval

        print(f"  Execution timeout (waiting exceeded {max_wait_time} seconds)")
        return {
            "ok": False,
            "text": f"Script execution timeout (waiting exceeded {max_wait_time} seconds)",
            "result": {"execute_uuid": execute_uuid},
            "error": {"code": "TIMEOUT", "message": "Script execution timeout"}
        }

    except exceptions.ClientRequestException as e:
        return _error("API_ERROR", f"{e.error_code}: {e.error_msg}")
    except Exception as e:
        return _error("UNKNOWN_ERROR", str(e))


def coc_query_execution(execute_uuid: str, ak: str = None, sk: str = None, security_token: str = None, region: str = None) -> dict[str, Any]:
    """
    Query script execution status by execute UUID.
    
    API: GET /v1/job/script/orders/{execute_uuid}/batches/1
    
    Parameters:
        execute_uuid: Execution UUID (format: SCT2023083109562601af694bf)
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials (optional)
        region: COC region (optional, default cn-north-4)
    
    Returns:
        {
            "data": {
                "batch_index": 1,
                "total_instances": 1,
                "execute_instances": [{
                    "id": 40304358,
                    "cmd_uuid": "xxx",
                    "job_sign": null,
                    "status": "FINISHED",  # or "ABNORMAL", "RUNNING", etc.
                    "message": "Execution log...",
                    "gmt_created": 1779934038727,
                    "gmt_finished": 1779934107670,
                    "execute_costs": 68943,
                    "target_instance": {
                        "resource_id": "xxx",
                        "agent_sn": "xxx",
                        "agent_status": null,
                        "agent_version": "1.1.8",
                        "region_id": "cn-north-4",
                        "project_id": null,
                        "properties": {
                            "host_name": "dify-test-001",
                            "fixed_ip": null,
                            "floating_ip": null,
                            "region_id": "cn-north-4",
                            "zone_id": null,
                            "application": null,
                            "group": null,
                            "project_id": null
                        },
                        "custom_attributes": null,
                        "provider": "hcss",
                        "type": "l-instance"
                    }
                }]
            }
        }
    """
    if not execute_uuid:
        return _error("INPUT_ERROR", "execute_uuid is required")
    if not ak or not sk:
        return _error("CONFIG_ERROR", "ak and sk are required")

    # 固定参数
    batch_index = 1
    limit = 50
    if not region:
        region = "cn-north-4"

    try:
        client = get_client(ak, sk, security_token, region)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        from huaweicloudsdkcoc.v1 import GetScriptJobBatchRequest
        
        request = GetScriptJobBatchRequest()
        request.batch_index = batch_index
        request.execute_uuid = execute_uuid
        request.limit = limit
        
        response = client.get_script_job_batch(request)
        
        result_dict = {}
        if hasattr(response, 'data') and response.data is not None:
            data = response.data
            if hasattr(data, 'batch_index'):
                result_dict['batch_index'] = data.batch_index
            if hasattr(data, 'total_instances'):
                result_dict['total_instances'] = data.total_instances
            if hasattr(data, 'execute_instances') and data.execute_instances:
                instances = []
                for instance in data.execute_instances:
                    instance_dict = {}
                    if hasattr(instance, 'id'):
                        instance_dict['id'] = instance.id
                    if hasattr(instance, 'cmd_uuid'):
                        instance_dict['cmd_uuid'] = instance.cmd_uuid
                    if hasattr(instance, 'status'):
                        instance_dict['status'] = instance.status
                    if hasattr(instance, 'message'):
                        instance_dict['message'] = instance.message
                    if hasattr(instance, 'execute_costs'):
                        instance_dict['execute_costs'] = instance.execute_costs
                    if hasattr(instance, 'gmt_created'):
                        instance_dict['gmt_created'] = instance.gmt_created
                    if hasattr(instance, 'gmt_finished'):
                        instance_dict['gmt_finished'] = instance.gmt_finished
                    if hasattr(instance, 'target_instance') and instance.target_instance:
                        target = instance.target_instance
                        target_dict = {}
                        if hasattr(target, 'resource_id'):
                            target_dict['resource_id'] = target.resource_id
                        if hasattr(target, 'agent_sn'):
                            target_dict['agent_sn'] = target.agent_sn
                        if hasattr(target, 'agent_status'):
                            target_dict['agent_status'] = target.agent_status
                        if hasattr(target, 'agent_version'):
                            target_dict['agent_version'] = target.agent_version
                        if hasattr(target, 'region_id'):
                            target_dict['region_id'] = target.region_id
                        if hasattr(target, 'project_id'):
                            target_dict['project_id'] = target.project_id
                        if hasattr(target, 'properties') and target.properties:
                            props = target.properties
                            props_dict = {}
                            if hasattr(props, 'host_name'):
                                props_dict['host_name'] = props.host_name
                            if hasattr(props, 'fixed_ip'):
                                props_dict['fixed_ip'] = props.fixed_ip
                            if hasattr(props, 'floating_ip'):
                                props_dict['floating_ip'] = props.floating_ip
                            if hasattr(props, 'region_id'):
                                props_dict['region_id'] = props.region_id
                            if hasattr(props, 'zone_id'):
                                props_dict['zone_id'] = props.zone_id
                            if hasattr(props, 'application'):
                                props_dict['application'] = props.application
                            if hasattr(props, 'group'):
                                props_dict['group'] = props.group
                            if hasattr(props, 'project_id'):
                                props_dict['project_id'] = props.project_id
                            target_dict['properties'] = props_dict
                        if hasattr(target, 'custom_attributes'):
                            target_dict['custom_attributes'] = target.custom_attributes
                        if hasattr(target, 'provider'):
                            target_dict['provider'] = target.provider
                        if hasattr(target, 'type'):
                            target_dict['type'] = target.type
                        instance_dict['target_instance'] = target_dict
                    if hasattr(instance, 'job_sign'):
                        instance_dict['job_sign'] = instance.job_sign
                    instances.append(instance_dict)
                result_dict['execute_instances'] = instances
        else:
            result_dict['status'] = 'UNKNOWN'
            result_dict['message'] = 'Execution record not found or empty'

        return {
            "data": result_dict
        }

    except exceptions.ClientRequestException as e:
        return _error("API_ERROR", f"{e.error_code}: {e.error_msg}")
    except Exception as e:
        return _error("UNKNOWN_ERROR", str(e))


def get_script_detail(script_uuid: str, ak: str, sk: str, security_token: str = None, region: str = None) -> dict[str, Any]:
    """Get script details"""
    if not script_uuid:
        return _error("INPUT_ERROR", "script_uuid is required")
    if not ak or not sk:
        return _error("CONFIG_ERROR", "ak and sk are required")

    try:
        client = get_client(ak, sk, security_token, region)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        request = GetScriptRequest()
        request.script_uuid = script_uuid
        
        response = client.get_script(request)
        
        script_data = {}
        if hasattr(response, 'data'):
            data = response.data
            script_data = {
                "script_uuid": data.script_uuid if hasattr(data, 'script_uuid') else "",
                "name": data.name if hasattr(data, 'name') else "",
                "type": data.type if hasattr(data, 'type') else "",
                "content": data.content if hasattr(data, 'content') else "",
                "description": data.description if hasattr(data, 'description') else "",
                "risk_level": data.risk_level if hasattr(data, 'risk_level') else "",
                "version": data.version if hasattr(data, 'version') else "",
                "create_time": data.create_time if hasattr(data, 'create_time') else ""
            }

        return {
            "ok": True,
            "text": "Script details retrieved",
            "result": script_data,
            "error": None,
        }

    except exceptions.ClientRequestException as e:
        return _error("API_ERROR", f"{e.error_code}: {e.error_msg}")
    except Exception as e:
        return _error("UNKNOWN_ERROR", str(e))


def list_scripts(ak: str, sk: str, security_token: str = None, region: str = None, page: int = 1, limit: int = 10) -> dict[str, Any]:
    """List scripts"""
    if not ak or not sk:
        return _error("CONFIG_ERROR", "ak and sk are required")
    
    try:
        client = get_client(ak, sk, security_token, region)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        request = ListScriptsRequest()
        request.page = page
        request.limit = limit
        
        response = client.list_scripts(request)
        
        scripts = []
        total = 0
        if hasattr(response, 'data'):
            data = response.data
            if hasattr(data, 'data'):
                for script in data.data:
                    risk_level = ""
                    version = ""
                    if hasattr(script, 'properties') and script.properties:
                        props = script.properties
                        risk_level = props.risk_level if hasattr(props, 'risk_level') else ""
                        version = props.version if hasattr(props, 'version') else ""
                    
                    scripts.append({
                        "script_uuid": script.script_uuid if hasattr(script, 'script_uuid') else "",
                        "name": script.name if hasattr(script, 'name') else "",
                        "type": script.type if hasattr(script, 'type') else "",
                        "description": script.description if hasattr(script, 'description') else "",
                        "risk_level": risk_level,
                        "version": version,
                        "create_time": script.gmt_created if hasattr(script, 'gmt_created') else ""
                    })
            if hasattr(data, 'total'):
                total = data.total

        return {
            "ok": True,
            "text": f"Found {total} scripts",
            "result": {
                "scripts": scripts,
                "total": total
            },
            "error": None,
        }

    except exceptions.ClientRequestException as e:
        return _error("API_ERROR", f"{e.error_code}: {e.error_msg}")
    except Exception as e:
        return _error("UNKNOWN_ERROR", str(e))


def get_hermes_script_content() -> str:
    """Get built-in Hermes configuration script content"""
    script_content = """#!/bin/bash


# ==================== Default Configuration ====================
DEFAULT_BASE_URL="https://api.modelarts-maas.com/v2"
DEFAULT_CONFIG_PATH="/home/hermes/.hermes/config.yaml"
DEFAULT_ENV_PATH="/home/hermes/.hermes/.env"


# ==================== Display Help Information ====================
show_usage() {
    echo "Hermes Configuration Tool (Feishu/WeCom compatible)"
    echo ""
    echo "Usage: $0 --api_key <API_KEY> --model_name <MODEL_NAME> --bot_platform <feishu|wecom> [options]"
    echo ""
    echo "Required parameters:"
    echo "  --api_key           Large model API Key"
    echo "  --model_name        Large model name (e.g.: deepseek-v3.2, qwen-plus, glm-4)"
    echo "  --bot_platform      Bot platform: feishu or wecom"
    echo ""
    echo "Optional parameters:"
    echo "  --api_base_url      API Base URL (default: $DEFAULT_BASE_URL)"
    echo "  --feishu_app_id     Feishu App ID"
    echo "  --feishu_app_secret Feishu App Secret"
    echo "  --wecom_bot_id      WeCom Bot ID"
    echo "  --wecom_secret      WeCom Secret"
    echo "  --config_path       config.yaml path (default: $DEFAULT_CONFIG_PATH)"
    echo "  --env_path          .env file path (default: $DEFAULT_ENV_PATH)"
    echo ""
}


# ==================== Initialize Variables ====================
API_KEY="${api_key}"
MODEL_NAME="${model_name}"
API_BASE_URL="$DEFAULT_BASE_URL"
BOT_PLATFORM="${bot_platform}"
FEISHU_APP_ID="${feishu_app_id}"
FEISHU_APP_SECRET="${feishu_app_secret}"
WECOM_BOT_ID="${wecom_bot_id}"
WECOM_SECRET="${wecom_secret}"
CONFIG_PATH="$DEFAULT_CONFIG_PATH"
ENV_PATH="$DEFAULT_ENV_PATH"


# ==================== Parse Parameters ====================
while [ $# -gt 0 ]
do
    case "$1" in
        --api_key)
            API_KEY="$2"
            shift
            ;;
        --model_name)
            MODEL_NAME="$2"
            shift
            ;;
        --api_base_url)
            API_BASE_URL="$2"
            shift
            ;;
        --bot_platform)
            BOT_PLATFORM="$2"
            shift
            ;;
        --feishu_app_id)
            FEISHU_APP_ID="$2"
            shift
            ;;
        --feishu_app_secret)
            FEISHU_APP_SECRET="$2"
            shift
            ;;
        --wecom_bot_id)
            WECOM_BOT_ID="$2"
            shift
            ;;
        --wecom_secret)
            WECOM_SECRET="$2"
            shift
            ;;
        --config_path)
            CONFIG_PATH="$2"
            shift
            ;;
        --env_path)
            ENV_PATH="$2"
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Error: Unknown parameter $1"
            show_usage
            exit 1
            ;;
    esac
    shift
done


# ==================== Validate Parameters ====================
if [ -z "$API_KEY" ]; then
    echo "❌ Error: --api_key parameter is required"
    show_usage
    exit 1
fi


if [ -z "$MODEL_NAME" ]; then
    echo "❌ Error: --model_name parameter is required"
    show_usage
    exit 1
fi


if [ -z "$BOT_PLATFORM" ]; then
    echo "❌ Error: --bot_platform parameter is required"
    show_usage
    exit 1
fi


if [ "$BOT_PLATFORM" != "feishu" ] && [ "$BOT_PLATFORM" != "wecom" ]; then
    echo "❌ Error: --bot_platform must be 'feishu' or 'wecom'"
    show_usage
    exit 1
fi


if [ "$BOT_PLATFORM" = "feishu" ]; then
    if [ -z "$FEISHU_APP_ID" ] || [ -z "$FEISHU_APP_SECRET" ]; then
        echo "❌ Error: When selecting Feishu, --feishu_app_id and --feishu_app_secret are required"
        show_usage
        exit 1
    fi
fi


if [ "$BOT_PLATFORM" = "wecom" ]; then
    if [ -z "$WECOM_BOT_ID" ] || [ -z "$WECOM_SECRET" ]; then
        echo "❌ Error: When selecting WeCom, --wecom_bot_id and --wecom_secret are required"
        show_usage
        exit 1
    fi
fi


# ==================== Validate Files ====================
if [ ! -f "$CONFIG_PATH" ]; then
    echo "❌ Cannot find $CONFIG_PATH, please check the path!"
    exit 1
fi


if [ ! -f "$ENV_PATH" ]; then
    echo "❌ Cannot find $ENV_PATH, please check the path!"
    exit 1
fi


# ==================== Helper Functions ====================
set_env_variable() {
    local env_file="$1"
    local key="$2"
    local value="$3"
    
    if grep -q "^[#]\\?[[:space:]]*$key=" "$env_file"; then
        sed -i.bak "s/^[#]\\?[[:space:]]*$key=.*/$key=$value/" "$env_file"
        rm -f "$env_file.bak"
    else
        echo "" >> "$env_file"
        echo "# Auto injected by setup script" >> "$env_file"
        echo "$key=$value" >> "$env_file"
    fi
}


# ==================== Update config.yaml ====================
update_config_yaml() {
    echo "⚙️  Updating $CONFIG_PATH ..."
    
    # Use Python script to modify config file
    python3 -c "
import yaml

config_path = '$CONFIG_PATH'
model_name = '$MODEL_NAME'
api_base_url = '$API_BASE_URL'
api_key = '$API_KEY'

with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

if 'model' not in config:
    config['model'] = {}

config['model']['default'] = model_name
config['model']['base_url'] = api_base_url
config['model']['api_key'] = api_key
config['model']['provider'] = 'custom'

if 'custom_providers' in config:
    del config['custom_providers']

provider_host = api_base_url.replace('https://', '').replace('http://', '').split('/')[0]
provider_name = provider_host[0].upper() + provider_host[1:] if provider_host else 'Custom'

config['custom_providers'] = [{
    'name': provider_name,
    'base_url': api_base_url,
    'api_key': api_key,
    'model': model_name
}]

with open(config_path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

print('✅ config.yaml updated successfully!')
"
}


# ==================== Update .env File ====================
update_env_file() {
    echo "⚙️  Updating $ENV_PATH ..."
    
    if [ "$BOT_PLATFORM" = "feishu" ]; then
        set_env_variable "$ENV_PATH" "FEISHU_APP_ID" "$FEISHU_APP_ID"
        set_env_variable "$ENV_PATH" "FEISHU_APP_SECRET" "$FEISHU_APP_SECRET"
        set_env_variable "$ENV_PATH" "FEISHU_DOMAIN" "feishu"
        set_env_variable "$ENV_PATH" "FEISHU_CONNECTION_MODE" "websocket"
        set_env_variable "$ENV_PATH" "FEISHU_ALLOW_ALL_USERS" "true"
        set_env_variable "$ENV_PATH" "FEISHU_ALLOWED_USERS" ""
        set_env_variable "$ENV_PATH" "FEISHU_GROUP_POLICY" "open"
        set_env_variable "$ENV_PATH" "GATEWAY_ALLOW_ALL_USERS" "true"
        echo "✅ Feishu configuration written successfully."
    
    elif [ "$BOT_PLATFORM" = "wecom" ]; then
        set_env_variable "$ENV_PATH" "WECOM_BOT_ID" "$WECOM_BOT_ID"
        set_env_variable "$ENV_PATH" "WECOM_SECRET" "$WECOM_SECRET"
        set_env_variable "$ENV_PATH" "GATEWAY_ALLOW_ALL_USERS" "true"
        echo "✅ WeCom configuration written successfully."
    fi
    
    echo "✅ $ENV_PATH updated successfully!"
}


# ==================== Main Function ====================
main() {
    echo "🚀 Starting Hermes configuration update..."
    echo " - Target Model: $MODEL_NAME"
    echo " - API Base URL: $API_BASE_URL"
    echo " - Target Platform: $BOT_PLATFORM"
    
    update_config_yaml
    update_env_file
    
    echo ""
    echo "🎉 Hermes configuration completed successfully!"
}


main "$@"
"""
    return script_content


def _error(code: str, message: str) -> dict:
    """Create error response"""
    return {
        "ok": False,
        "text": "",
        "result": None,
        "error": {"code": code, "message": message},
    }


def query_uniagent_status(
    resource_id: str,
    ak: str,
    sk: str,
    security_token: str = None
) -> dict[str, Any]:
    """
    Query L instance UniAgent status via COC API

    Args:
        resource_id: L instance resource ID
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials (optional)

    Returns:
        {
            "ok": True,
            "text": "Query successful",
            "result": {...},
            "error": None
        }
    """
    if not resource_id:
        return _error("INPUT_ERROR", "resource_id parameter is required")
    
    if not ak or not sk:
        return _error("CONFIG_ERROR", "Please provide AK and SK parameters")
    
    region = os.environ.get("HUAWEICLOUD_REGION", "cn-north-4")
    
    try:
        from huaweicloudsdkcore.auth.credentials import GlobalCredentials
        from huaweicloudsdkcore.signer.signer import Signer
        from huaweicloudsdkcore.sdk_request import SdkRequest
        from urllib.parse import urlparse
        
        credentials = Credentials(ak, sk, security_token)
        signer = Signer(credentials)
        
        endpoint = "https://coc.myhuaweicloud.com/v1/resources"
        
        query_params = {
            "resource_id_list": resource_id,
            "limit": "100",
            "provider": "hcss",
            "type": "l-instance"
        }
        
        url_with_params = endpoint + "?" + "&".join([f"{k}={v}" for k, v in query_params.items()])
        parsed_url = urlparse(url_with_params)
        
        request = SdkRequest()
        request.method = "GET"
        request.schema = parsed_url.scheme
        request.host = parsed_url.hostname
        request.resource_path = parsed_url.path
        request.query_params = [[k, v] for k, v in query_params.items()]
        request.header_params = {
            "Content-Type": "application/json",
            "Client-Request-Id": str(uuid.uuid4())
        }
        
        if security_token:
            request.header_params["X-Security-Token"] = security_token
        
        signed_request = signer.sign(request)
        
        headers = {}
        for key, value in signed_request.header_params.items():
            if isinstance(value, bytes):
                headers[key] = value.decode('iso-8859-1')
            else:
                headers[key] = str(value)
        
        print(f"Request URL: {url_with_params}")
        print(f"Request headers: {headers}")
        
        resp = requests.request(
            "GET",
            url_with_params,
            headers=headers,
            verify=True
        )
        
        print(f"Response status code: {resp.status_code}")
        print(f"Response content: {resp.text}")
        
        if resp.status_code in [200, 202]:
            response_data = resp.json()
            return {
                "ok": True,
                "text": "UniAgent status query successful",
                "result": response_data,
                "error": None
            }
        else:
            return {
                "ok": False,
                "text": f"Query failed: {resp.reason}",
                "result": None,
                "error": {
                    "code": str(resp.status_code),
                    "message": resp.text
                }
            }
    
    except ImportError as e:
        return _error("SDK_ERROR", f"Please install huaweicloudsdkcore: {str(e)}")
    except Exception as e:
        error_msg = str(e)
        return _error("UNKNOWN_ERROR", error_msg)
