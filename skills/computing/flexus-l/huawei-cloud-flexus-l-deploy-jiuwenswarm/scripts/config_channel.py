#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JiuwenSwarm Message Channel Configuration Script
Configures Xiaoyi, Feishu, or DingTalk message channels for JiuwenSwarm deployment.
Uses Huawei Cloud COC (Cloud Operation Center) to execute configuration commands on target instances.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

os.environ['PYTHONIOENCODING'] = 'utf-8'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

EXECUTION_TIMEOUT = 300

CHANNEL_TYPES = ['xiaoyi', 'feishu', 'dingtalk']

# Import utility modules
sys.path.insert(0, str(Path(__file__).parent))
try:
    from utils import (
        get_huaweicloud_credentials,
        get_coc_client,
        coc_query_execution,
        print_header,
        print_success,
        print_error,
        print_warning,
        print_info
    )
except ImportError as e:
    log.error(f"Failed to import utility modules: {e}")
    log.error("Please ensure utils.py exists")
    sys.exit(1)

def query_instance_by_ip(public_ip, ak, sk, region, security_token=None):
    from huaweicloudsdkcore.auth.credentials import GlobalCredentials, BasicCredentials
    from huaweicloudsdkrms.v1 import RmsClient
    from huaweicloudsdkrms.v1.region.rms_region import RmsRegion

    # RMS requires GlobalCredentials
    if security_token:
        credentials = GlobalCredentials(ak, sk).with_security_token(security_token)
    else:
        credentials = GlobalCredentials(ak, sk)
    
    client = RmsClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(RmsRegion.value_of(region)) \
        .build()

    from huaweicloudsdkrms.v1 import model
    request = model.ListAllResourcesRequest()
    request.region_id = region
    request.type = "hcss.l-instance"
    request.limit = 200

    response = client.list_all_resources(request)
    resources = response.resources if hasattr(response, 'resources') else []

    for r in resources:
        name = getattr(r, 'name', '') or getattr(r, 'resource_name', '')
        instance_id = getattr(r, 'id', '') or getattr(r, 'resource_id', '')
        props = getattr(r, 'properties', None)

        ip = None
        ecs_instance_id = None

        if props:
            resources_list = props.get('resources', [])
            for res in resources_list:
                if isinstance(res, dict):
                    attrs = res.get('resource_attributes', [])
                    for attr in attrs:
                        if isinstance(attr, dict):
                            key = attr.get('key')
                            value = attr.get('value')
                            if key == 'public_ip_address':
                                ip = value
                            if key == 'associate_instance_id':
                                ecs_instance_id = value

        if ip == public_ip:
            return {
                'instance_name': name,
                'instance_id': instance_id,
                'ecs_instance_id': ecs_instance_id,
                'public_ip': ip,
                'region': region,
                'status': props.get('status') if props else 'UNKNOWN'
            }

    return None

def load_instance_info():
    info_file = Path(__file__).parent / "new_instance_info.json"
    if info_file.exists():
        with open(info_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def create_and_execute_command(client, command, instance_id, instance_name, region):
    from huaweicloudsdkcoc.v1.model.create_script_request import CreateScriptRequest
    from huaweicloudsdkcoc.v1.model.add_script_model import AddScriptModel
    from huaweicloudsdkcoc.v1.model.script_properties_model import ScriptPropertiesModel
    from huaweicloudsdkcoc.v1.model.execute_script_request import ExecuteScriptRequest
    from huaweicloudsdkcoc.v1.model.script_execute_model import ScriptExecuteModel
    from huaweicloudsdkcoc.v1.model.execute_instances_batch_info import ExecuteInstancesBatchInfo
    from huaweicloudsdkcoc.v1.model.execute_resource_instance import ExecuteResourceInstance
    from huaweicloudsdkcoc.v1.model.script_execute_param import ScriptExecuteParam
    from huaweicloudsdkcore.exceptions import exceptions

    script_name = f"jiuwenswarm-channel-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    description = f"JiuwenSwarm channel configuration on {instance_name}"

    log.info("Creating COC script for channel configuration...")
    request = CreateScriptRequest()
    properties = ScriptPropertiesModel(risk_level="LOW", version="1.0.0")
    request.body = AddScriptModel(
        name=script_name,
        type="SHELL",
        content=command,
        description=description,
        properties=properties
    )

    try:
        response = client.create_script(request)
        script_uuid = response.data if hasattr(response, 'data') else str(response)
        log.info(f"[OK] Script created: {script_uuid}")
    except exceptions.ClientRequestException as e:
        log.error(f"Script creation failed: {e.error_code}: {e.error_msg}")
        return None, None

    log.info("Executing command on target instance...")

    execute_request = ExecuteScriptRequest()
    execute_request.script_uuid = script_uuid

    execute_param = ScriptExecuteParam(timeout=EXECUTION_TIMEOUT, success_rate=100, execute_user="root")

    instance = ExecuteResourceInstance(
        resource_id=instance_id,
        region_id=region,
        provider="HCSS",
        type="L-INSTANCE"
    )

    execute_request.body = ScriptExecuteModel(
        execute_batches=[ExecuteInstancesBatchInfo(
            batch_index=1,
            target_instances=[instance],
            rotation_strategy="CONTINUE"
        )],
        execute_param=execute_param
    )

    try:
        execute_response = client.execute_script(execute_request)
        execute_uuid = execute_response.data if hasattr(execute_response, 'data') else str(execute_response)
        log.info(f"[OK] Execution submitted: {execute_uuid}")
        return execute_uuid, script_uuid
    except exceptions.ClientRequestException as e:
        log.error(f"Script execution failed: {e.error_code}: {e.error_msg}")
        return None, None

def wait_for_completion(client, execute_uuid, timeout=300, interval=10):
    """Wait for command execution to complete - using Huawei Cloud COC GetScriptJobInfo API"""
    import time
    
    print_info(f"\nWaiting for command execution...")
    print_info(f"Timeout: {timeout}s, Polling Interval: {interval}s")

    start_time = datetime.now()

    while True:
        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed > timeout:
            print_error(f"Command execution timeout ({timeout}s)")
            return False

        try:
            # Query status using Huawei Cloud COC GetScriptJobInfo API
            result = coc_query_execution(execute_uuid)
            
            if not result.get("ok"):
                error_info = result.get("error", {})
                print_warning(f"Status query failed: {error_info.get('message', 'Unknown error')}")
                time.sleep(interval)
                continue
            
            job_info = result.get("result", {})
            status = job_info.get('status', 'UNKNOWN')
            
            # Task status mapping
            STATUS_MAP = {
                'READY': 'Preparing',
                'PROCESSING': 'Processing',
                'FINISHED': 'Completed',
                'ABNORMAL': 'Abnormal',
                'CANCELED': 'Canceled'
            }
            status_display = STATUS_MAP.get(status, status)
            
            print(f"  Status: {status} ({status_display}) (Elapsed: {int(elapsed)}s)", end='\r')

            # According to Huawei Cloud COC API, script execution ends when status is ABNORMAL, CANCELED, or FINISHED
            if status == 'FINISHED':
                success_count = job_info.get('success_count', 0)
                fail_count = job_info.get('fail_count', 0)
                print(f"\n[OK] Command execution completed. Success: {success_count}, Failed: {fail_count}")
                return success_count > 0

            elif status in ['ABNORMAL', 'CANCELED']:
                error_msg = job_info.get('error', job_info.get('error_message', 'Unknown error'))
                print(f"\n[ERROR] Command execution failed! Status: {status} ({status_display})")
                if error_msg:
                    print_error(f"Error Message: {error_msg}")
                return False

        except Exception as e:
            print(f"\n[WARN] Error checking status: {e}")

        time.sleep(interval)

    return False

def generate_xiaoyi_script(config):
    """Generate Xiaoyi channel configuration script"""
    ak, sk, agent_id = config
    
    script = f"""#!/bin/bash
set -e

echo "[INFO] Configuring Xiaoyi channel..."

CONFIG_DIR="/root/.jiuwenswarm/config"
CONFIG_FILE="$CONFIG_DIR/config.yaml"

if [ ! -d "$CONFIG_DIR" ]; then
    echo "[ERROR] Config directory not found: $CONFIG_DIR"
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "[WARN] Config file not found, creating new one..."
    cat > "$CONFIG_FILE" << 'EOF'
channels:
  xiaoyi:
    enabled: false
  feishu:
    enabled: false
  dingtalk:
    enabled: false
EOF
fi

echo "[INFO] Backup existing config file..."
cp "$CONFIG_FILE" "$CONFIG_FILE.backup.$(date +%Y%m%d%H%M%S)"

echo "[INFO] Updating Xiaoyi configuration..."

python3 << 'PYEOF'
import yaml
import os

config_file = "/root/.jiuwenswarm/config/config.yaml"

# Read existing configuration
with open(config_file, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f) or {{}}

# Ensure channels section exists
if 'channels' not in config:
    config['channels'] = {{}}

# Ensure xiaoyi configuration section exists
if 'xiaoyi' not in config['channels']:
    config['channels']['xiaoyi'] = {{}}

# Update only specified fields, keep other fields unchanged
xiaoyi_config = config['channels']['xiaoyi']

# Update Xiaoyi configuration
xiaoyi_config['ak'] = '{ak}'
xiaoyi_config['sk'] = '{sk}'
xiaoyi_config['agent_id'] = '{agent_id}'
xiaoyi_config['enabled'] = True

# Write updated configuration
with open(config_file, 'w', encoding='utf-8') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

print("[OK] Xiaoyi configuration updated - only specific fields modified")
PYEOF

chmod 644 "$CONFIG_FILE"
echo "[OK] Configuration file permissions set"

echo ""
echo "[INFO] ==========================================="
echo "[INFO] Stop JiuwenSwarm Service"
echo "[INFO] ==========================================="

if systemctl is-active --quiet jiuwenswarm; then
    echo "[INFO] Stopping jiuwenswarm service..."
    systemctl stop jiuwenswarm
    echo "[OK] jiuwenswarm service stopped"
else
    echo "[WARN] jiuwenswarm service is not running"
fi

echo ""
echo "[INFO] Waiting 3 seconds..."
sleep 3

echo ""
echo "[INFO] ==========================================="
echo "[INFO] Restart JiuwenSwarm Service"
echo "[INFO] ==========================================="

echo "[INFO] Starting jiuwenswarm service..."
systemctl start jiuwenswarm

echo "[INFO] Waiting for service to start..."
sleep 5

if systemctl is-active --quiet jiuwenswarm; then
    echo "[OK] jiuwenswarm service started successfully"
    systemctl status jiuwenswarm --no-pager
else
    echo "[ERROR] Failed to start jiuwenswarm service"
    systemctl status jiuwenswarm --no-pager
    exit 1
fi

echo ""
echo "[INFO] ==========================================="
echo "[SUCCESS] Xiaoyi channel configuration completed"
echo "[INFO] ==========================================="
"""
    return script

def generate_feishu_script(config):
    """Generate Feishu channel configuration script"""
    app_id, app_secret = config
    
    script = f"""#!/bin/bash
set -e

echo "[INFO] Configuring Feishu channel..."

CONFIG_DIR="/root/.jiuwenswarm/config"
CONFIG_FILE="$CONFIG_DIR/config.yaml"

if [ ! -d "$CONFIG_DIR" ]; then
    echo "[ERROR] Config directory not found: $CONFIG_DIR"
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "[WARN] Config file not found, creating new one..."
    cat > "$CONFIG_FILE" << 'EOF'
channels:
  xiaoyi:
    enabled: false
  feishu:
    enabled: false
  dingtalk:
    enabled: false
EOF
fi

echo "[INFO] Backup existing config file..."
cp "$CONFIG_FILE" "$CONFIG_FILE.backup.$(date +%Y%m%d%H%M%S)"

echo "[INFO] Updating Feishu configuration..."

python3 << 'PYEOF'
import yaml
import os

config_file = "/root/.jiuwenswarm/config/config.yaml"

# Read existing configuration
with open(config_file, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f) or {{}}

# Ensure channels section exists
if 'channels' not in config:
    config['channels'] = {{}}

# Ensure feishu configuration section exists
if 'feishu' not in config['channels']:
    config['channels']['feishu'] = {{}}

# Update only specified fields, keep other fields unchanged
feishu_config = config['channels']['feishu']

# Update Feishu configuration
feishu_config['app_id'] = '{app_id}'
feishu_config['app_secret'] = '{app_secret}'
feishu_config['enabled'] = True

# Write updated configuration
with open(config_file, 'w', encoding='utf-8') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

print("[OK] Feishu configuration updated - only specific fields modified")
PYEOF

chmod 644 "$CONFIG_FILE"
echo "[OK] Configuration file permissions set"

echo ""
echo "[INFO] ==========================================="
echo "[INFO] Stopping JiuwenSwarm Service"
echo "[INFO] ==========================================="

if systemctl is-active --quiet jiuwenswarm; then
    echo "[INFO] Stopping jiuwenswarm service..."
    systemctl stop jiuwenswarm
    echo "[OK] jiuwenswarm service stopped"
else
    echo "[WARN] jiuwenswarm service is not running"
fi

echo ""
echo "[INFO] Waiting 3 seconds..."
sleep 3

echo ""
echo "[INFO] ==========================================="
echo "[INFO] Restarting JiuwenSwarm Service"
echo "[INFO] ==========================================="

echo "[INFO] Starting jiuwenswarm service..."
systemctl start jiuwenswarm

echo "[INFO] Waiting for service to start..."
sleep 5

if systemctl is-active --quiet jiuwenswarm; then
    echo "[OK] jiuwenswarm service started successfully"
    systemctl status jiuwenswarm --no-pager
else
    echo "[ERROR] Failed to start jiuwenswarm service"
    systemctl status jiuwenswarm --no-pager
    exit 1
fi

echo ""
echo "[INFO] ==========================================="
echo "[SUCCESS] Feishu channel configuration completed"
echo "[INFO] ==========================================="
"""
    return script

def generate_dingtalk_script(config):
    """Generate DingTalk channel configuration script"""
    client_id, client_secret, allow_from = config
    
    script = f"""#!/bin/bash
set -e

echo "[INFO] Configuring DingTalk channel..."

CONFIG_DIR="/root/.jiuwenswarm/config"
CONFIG_FILE="$CONFIG_DIR/config.yaml"

if [ ! -d "$CONFIG_DIR" ]; then
    echo "[ERROR] Config directory not found: $CONFIG_DIR"
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "[WARN] Config file not found, creating new one..."
    cat > "$CONFIG_FILE" << 'EOF'
channels:
  xiaoyi:
    enabled: false
  feishu:
    enabled: false
  dingtalk:
    enabled: false
EOF
fi

echo "[INFO] Backup existing config file..."
cp "$CONFIG_FILE" "$CONFIG_FILE.backup.$(date +%Y%m%d%H%M%S)"

echo "[INFO] Updating DingTalk configuration..."

python3 << 'PYEOF'
import yaml
import os

config_file = "/root/.jiuwenswarm/config/config.yaml"

# Read existing configuration
with open(config_file, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f) or {{}}

# Ensure channels section exists
if 'channels' not in config:
    config['channels'] = {{}}

# Ensure dingtalk configuration section exists
if 'dingtalk' not in config['channels']:
    config['channels']['dingtalk'] = {{}}

# Update only specified fields, keep other fields unchanged
dingtalk_config = config['channels']['dingtalk']

# Update DingTalk configuration
dingtalk_config['client_id'] = '{client_id}'
dingtalk_config['client_secret'] = '{client_secret}'
dingtalk_config['allow_from'] = '{allow_from}'
dingtalk_config['enabled'] = True

# Write updated configuration
with open(config_file, 'w', encoding='utf-8') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

print("[OK] DingTalk configuration updated - only specific fields modified")
PYEOF

chmod 644 "$CONFIG_FILE"
echo "[OK] Configuration file permissions set"

echo ""
echo "[INFO] ==========================================="
echo "[INFO] Stopping JiuwenSwarm Service"
echo "[INFO] ==========================================="

if systemctl is-active --quiet jiuwenswarm; then
    echo "[INFO] Stopping jiuwenswarm service..."
    systemctl stop jiuwenswarm
    echo "[OK] jiuwenswarm service stopped"
else
    echo "[WARN] jiuwenswarm service is not running"
fi

echo ""
echo "[INFO] Waiting 3 seconds..."
sleep 3

echo ""
echo "[INFO] ==========================================="
echo "[INFO] Restarting JiuwenSwarm Service"
echo "[INFO] ==========================================="

echo "[INFO] Starting jiuwenswarm service..."
systemctl start jiuwenswarm

echo "[INFO] Waiting for service to start..."
sleep 5

if systemctl is-active --quiet jiuwenswarm; then
    echo "[OK] jiuwenswarm service started successfully"
    systemctl status jiuwenswarm --no-pager
else
    echo "[ERROR] Failed to start jiuwenswarm service"
    systemctl status jiuwenswarm --no-pager
    exit 1
fi

echo ""
echo "[INFO] ==========================================="
echo "[SUCCESS] DingTalk channel configuration completed"
echo "[INFO] ==========================================="
"""
    return script

def configure_channel_interactive():
    print("="*60)
    print("  JiuwenSwarm Message Channel Configuration")
    print("="*60)
    print("\nPlease select channel type:")
    print("  1. xiaoyi - Xiaoyi")
    print("  2. feishu - Feishu")
    print("  3. dingtalk - DingTalk")

    while True:
        choice = input("\nEnter your choice (1/2/3): ").strip()
        if choice == '1':
            channel_type = 'xiaoyi'
            break
        elif choice == '2':
            channel_type = 'feishu'
            break
        elif choice == '3':
            channel_type = 'dingtalk'
            break
        else:
            print("[ERROR] Invalid choice, please enter 1, 2, or 3")

    print(f"\n--- {channel_type} Channel Configuration ---")

    if channel_type == 'xiaoyi':
        ak = input("Xiaoyi AK: ").strip()
        if not ak:
            print("[ERROR] AK cannot be empty")
            return None
        sk = input("Xiaoyi SK: ").strip()
        if not sk:
            print("[ERROR] SK cannot be empty")
            return None
        agent_id = input("Xiaoyi Agent ID: ").strip()
        if not agent_id:
            print("[ERROR] Agent ID cannot be empty")
            return None

        print("\n" + "="*60)
        print("  Configuration Confirmation")
        print("="*60)
        print(f"\n  Channel Type: Xiaoyi")
        print(f"  AK: {ak}")
        print(f"  SK: {'*' * len(sk) if len(sk) > 8 else sk}")
        print(f"  Agent ID: {agent_id}")

        confirm = input("\nConfirm configuration? (y/n): ").strip().lower()
        if confirm != 'y':
            print("[INFO] Configuration cancelled")
            return None

        return {
            'channel_type': channel_type,
            'config': (ak, sk, agent_id)
        }

    elif channel_type == 'feishu':
        app_id = input("Feishu App ID: ").strip()
        if not app_id:
            print("[ERROR] App ID cannot be empty")
            return None
        app_secret = input("Feishu App Secret: ").strip()
        if not app_secret:
            print("[ERROR] App Secret cannot be empty")
            return None

        print("\n" + "="*60)
        print("  Configuration Confirmation")
        print("="*60)
        print(f"\n  Channel Type: Feishu")
        print(f"  App ID: {app_id}")
        print(f"  App Secret: {'*' * len(app_secret) if len(app_secret) > 8 else app_secret}")

        confirm = input("\nConfirm configuration? (y/n): ").strip().lower()
        if confirm != 'y':
            print("[INFO] Configuration cancelled")
            return None

        return {
            'channel_type': channel_type,
            'config': (app_id, app_secret)
        }

    elif channel_type == 'dingtalk':
        client_id = input("DingTalk Client ID: ").strip()
        if not client_id:
            print("[ERROR] Client ID cannot be empty")
            return None
        client_secret = input("DingTalk Client Secret: ").strip()
        if not client_secret:
            print("[ERROR] Client Secret cannot be empty")
            return None
        allow_from = input("DingTalk Allow From: ").strip()
        if not allow_from:
            print("[ERROR] Allow From cannot be empty")
            return None

        print("\n" + "="*60)
        print("  Configuration Confirmation")
        print("="*60)
        print(f"\n  Channel Type: DingTalk")
        print(f"  Client ID: {client_id}")
        print(f"  Client Secret: {'*' * len(client_secret) if len(client_secret) > 8 else client_secret}")
        print(f"  Allow From: {allow_from}")

        confirm = input("\nConfirm configuration? (y/n): ").strip().lower()
        if confirm != 'y':
            print("[INFO] Configuration cancelled")
            return None

        return {
            'channel_type': channel_type,
            'config': (client_id, client_secret, allow_from)
        }

def parse_args():
    parser = argparse.ArgumentParser(description='Configure JiuwenSwarm Message Channels')
    parser.add_argument('--channel', type=str, required=True, choices=CHANNEL_TYPES, help='Channel type: xiaoyi/feishu/dingtalk')
    parser.add_argument('--xiaoyi-ak', type=str, help='Xiaoyi AK')
    parser.add_argument('--xiaoyi-sk', type=str, help='Xiaoyi SK')
    parser.add_argument('--xiaoyi-agent-id', type=str, help='Xiaoyi Agent ID')
    parser.add_argument('--feishu-app-id', type=str, help='Feishu App ID')
    parser.add_argument('--feishu-app-secret', type=str, help='Feishu App Secret')
    parser.add_argument('--dingtalk-client-id', type=str, help='DingTalk Client ID')
    parser.add_argument('--dingtalk-client-secret', type=str, help='DingTalk Client Secret')
    parser.add_argument('--dingtalk-allow-from', type=str, help='DingTalk Allow From')
    parser.add_argument('--instance-id', type=str, help='Instance RMS resource ID')
    parser.add_argument('--ip', type=str, help='Instance public IP address')
    parser.add_argument('--interactive', action='store_true', help='Interactive configuration mode')
    return parser.parse_args()

def main():
    args = parse_args()

    try:
        AK, SK, REGION, SECURITY_TOKEN = get_huaweicloud_credentials()
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    if SECURITY_TOKEN:
        print(f"[INFO] Using temporary security credentials (STS token)")

    # Get configuration
    config_result = None
    if args.interactive:
        config_result = configure_channel_interactive()
    else:
        channel_type = args.channel
        config = None

        if channel_type == 'xiaoyi':
            if args.xiaoyi_ak and args.xiaoyi_sk and args.xiaoyi_agent_id:
                config = (args.xiaoyi_ak, args.xiaoyi_sk, args.xiaoyi_agent_id)
        elif channel_type == 'feishu':
            if args.feishu_app_id and args.feishu_app_secret:
                config = (args.feishu_app_id, args.feishu_app_secret)
        elif channel_type == 'dingtalk':
            if args.dingtalk_client_id and args.dingtalk_client_secret and args.dingtalk_allow_from:
                config = (args.dingtalk_client_id, args.dingtalk_client_secret, args.dingtalk_allow_from)

        if config:
            config_result = {
                'channel_type': channel_type,
                'config': config
            }

    if not config_result:
        print("[ERROR] Invalid configuration parameters")
        sys.exit(1)

    channel_type = config_result['channel_type']
    channel_config = config_result['config']

    # Get instance info
    instance_info = None
    if args.instance_id:
        instance_info = {'instance_id': args.instance_id, 'public_ip': args.ip, 'instance_name': 'Unknown'}
    elif args.ip:
        print(f"[INFO] Querying instance info by public IP: {args.ip}")
        instance_info = query_instance_by_ip(args.ip, AK, SK, REGION, SECURITY_TOKEN)
        if not instance_info:
            print(f"[ERROR] Cannot find instance with public IP: {args.ip}")
            return
    else:
        instance_info = load_instance_info()
        if not instance_info:
            print("[ERROR] Cannot get instance info")
            print("Please provide instance info via:")
            print("  Method 1: --ip <public_ip>")
            print("  Method 2: --instance-id <RMS_resource_id>")
            return

    instance_id = instance_info.get('instance_id')
    instance_name = instance_info.get('instance_name', 'Unknown')
    public_ip = instance_info.get('public_ip')

    if not instance_id:
        print("[ERROR] Missing instance_id")
        return

    print("\n" + "="*60)
    print("  Phase 7: Message Channel Configuration")
    print("="*60)
    print(f"\nTarget Instance:")
    print(f"  Name: {instance_name}")
    print(f"  IP: {public_ip}")
    print(f"\nChannel Configuration:")
    print(f"  Channel Type: {channel_type}")

    # Generate configuration script
    if channel_type == 'xiaoyi':
        script_content = generate_xiaoyi_script(channel_config)
    elif channel_type == 'feishu':
        script_content = generate_feishu_script(channel_config)
    elif channel_type == 'dingtalk':
        script_content = generate_dingtalk_script(channel_config)
    else:
        print("[ERROR] Invalid channel type")
        return

    client = get_coc_client()
    print("\n[INFO] Creating COC client... [OK]")

    execute_uuid, script_uuid = create_and_execute_command(
        client, script_content, instance_id, instance_name, REGION
    )

    if not execute_uuid:
        print("\n[ERROR] Failed to submit configuration command")
        return

    print("\n" + "="*60)
    print("  Configuration Progress")
    print("="*60)

    success = wait_for_completion(client, execute_uuid)

    print("\n" + "="*60)
    if success:
        print("  [SUCCESS] Message channel configuration completed")
    else:
        print("  [ERROR] Message channel configuration failed")
        sys.exit(1)
    print("="*60)

    print(f"\nWeb Access: http://{public_ip}:5173")
    print("\nNext Steps:")
    print("  1. Check service status: sudo systemctl status jiuwenswarm")
    print("  2. View logs: sudo journalctl -u jiuwenswarm -f")
    print("  3. Verify configuration: curl http://localhost:5173/health")

    result = {
        'channel_type': channel_type,
        'channel_config': {k: '***' for k in ['ak', 'sk', 'app_secret', 'client_secret']} if isinstance(channel_config, tuple) else '***',
        'instance_id': instance_id,
        'instance_name': instance_name,
        'public_ip': public_ip,
        'configure_time': datetime.now().isoformat(),
        'success': success
    }

    output_path = Path(__file__).parent / "channel_config_result.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n[INFO] Configuration result saved to {output_path}")

if __name__ == "__main__":
    main()
