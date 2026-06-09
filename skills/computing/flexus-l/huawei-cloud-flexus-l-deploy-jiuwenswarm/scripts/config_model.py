#!/usr/bin/env python3
"""
JiuwenSwarm Model Configuration Script
Configures AI model parameters (API base, key, model name, provider) for JiuwenSwarm deployment.
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

    script_name = f"jiuwenswarm-config-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    description = f"JiuwenSwarm model configuration on {instance_name}"

    log.info("Creating COC script for model configuration...")
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

def generate_config_script(config):
    api_base = config['api_base']
    api_key = config['api_key']
    model_name = config['model_name']
    model_provider = config['model_provider']
    
    test_script = '''#!/bin/bash
set -e

echo "[INFO] Configuring JiuwenSwarm model..."

CONFIG_DIR="/root/.jiuwenswarm/config"
ENV_FILE="$CONFIG_DIR/.env"

# Ensure config directory exists
mkdir -p "$CONFIG_DIR"

# If config file doesn't exist, create a basic config file
if [ ! -f "$ENV_FILE" ]; then
    echo "[INFO] Config file does not exist, creating new file"
    cat > "$ENV_FILE" << 'EOF'
# JiuwenSwarm Configuration
EOF
fi

# Backup existing config file
BACKUP_FILE="$ENV_FILE.backup.$(date +%Y%m%d%H%M%S)"
cp "$ENV_FILE" "$BACKUP_FILE"
echo "[INFO] Config file backed up: $BACKUP_FILE"

# Define the four parameters to update
API_BASE_VALUE="''' + api_base + '''"
API_KEY_VALUE="''' + api_key + '''"
MODEL_NAME_VALUE="''' + model_name + '''"
MODEL_PROVIDER_VALUE="''' + model_provider + '''"

# Use sed to update or add config parameters while preserving other content
update_param() {
    local key="$1"
    local value="$2"
    local env_file="$3"
    
    if grep -q "^[[:space:]]*$key=" "$env_file"; then
        # Parameter exists, update its value
        sed -i "s|^\s*$key=.*|$key=\"$value\"|" "$env_file"
        echo "[INFO] Updated $key"
    else
        # Parameter doesn't exist, add to end of file
        echo "$key=\"$value\"" >> "$env_file"
        echo "[INFO] Added $key"
    fi
}

# Update the four core parameters
update_param "API_BASE" "$API_BASE_VALUE" "$ENV_FILE"
update_param "API_KEY" "$API_KEY_VALUE" "$ENV_FILE"
update_param "MODEL_NAME" "$MODEL_NAME_VALUE" "$ENV_FILE"
update_param "MODEL_PROVIDER" "$MODEL_PROVIDER_VALUE" "$ENV_FILE"

echo "[INFO] Config file updated:"
echo "-----------------------------------------"
cat "$ENV_FILE"
echo "-----------------------------------------"

chmod 600 "$ENV_FILE"
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
echo "[SUCCESS] Model configuration completed!"
echo "[INFO] ==========================================="
'''
    return test_script

def configure_model_interactive():
    print("="*60)
    print("  JiuwenSwarm Model Configuration")
    print("="*60)
    print("\nPlease provide model configuration information:\n")

    api_base = input("Model API URL (API_BASE): ").strip()
    if not api_base:
        print("[ERROR] API URL cannot be empty")
        return None

    api_key = input("Model API Key (API_KEY): ").strip()
    if not api_key:
        print("[ERROR] API Key cannot be empty")
        return None

    model_name = input("Model Name (MODEL_NAME): ").strip()
    if not model_name:
        print("[ERROR] Model name cannot be empty")
        return None

    model_provider = input("Model Provider (MODEL_PROVIDER): ").strip()
    if not model_provider:
        print("[ERROR] Model provider cannot be empty")
        return None

    print("\n" + "="*60)
    print("  Configuration Confirmation")
    print("="*60)
    print(f"\n  API_BASE: {api_base}")
    print(f"  API_KEY: {'*' * len(api_key) if len(api_key) > 8 else api_key}")
    print(f"  MODEL_NAME: {model_name}")
    print(f"  MODEL_PROVIDER: {model_provider}")

    confirm = input("\nConfirm configuration? (y/n): ").strip().lower()
    if confirm != 'y':
        print("[INFO] Configuration cancelled")
        return None

    return {
        'api_base': api_base,
        'api_key': api_key,
        'model_name': model_name,
        'model_provider': model_provider
    }

def parse_args():
    parser = argparse.ArgumentParser(description='Configure JiuwenSwarm Model Parameters')
    parser.add_argument('--api-base', type=str, help='Model API URL')
    parser.add_argument('--api-key', type=str, help='Model API Key')
    parser.add_argument('--model-name', type=str, help='Model Name')
    parser.add_argument('--model-provider', type=str, help='Model Provider')
    parser.add_argument('--config', type=str, help='JSON configuration file')
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

    config = None
    if args.config:
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
    elif args.api_base and args.api_key and args.model_name and args.model_provider:
        config = {
            'api_base': args.api_base,
            'api_key': args.api_key,
            'model_name': args.model_name,
            'model_provider': args.model_provider
        }
    elif args.interactive:
        config = configure_model_interactive()
    else:
        config = configure_model_interactive()

    if not config:
        return

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
    print("  Phase 6: Configure JiuwenSwarm Model")
    print("="*60)
    print(f"\nTarget Instance:")
    print(f"  Name: {instance_name}")
    print(f"  IP: {public_ip}")
    print(f"\nModel Configuration:")
    print(f"  API_BASE: {config['api_base']}")
    print(f"  MODEL_NAME: {config['model_name']}")
    print(f"  MODEL_PROVIDER: {config['model_provider']}")

    script_content = generate_config_script(config)

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
        print("  [SUCCESS] Model configuration successful!")
    else:
        print("  [ERROR] Model configuration failed")
        sys.exit(1)
    print("="*60)

    print(f"\nWeb Access: http://{public_ip}:5173")
    print("\nNext Steps:")
    print("  1. Restart service to apply configuration:")
    print("     # Method 1: Use pkill to stop and start")
    print("     pkill -f jiuwen")
    print("     source /opt/jiuwenswarm-env/bin/activate && jiuwenswarm-start")
    print("")
    print("     # Method 2: Use systemd restart")
    print("     sudo systemctl restart jiuwenswarm")
    print("")
    print("     # Method 3: Use configuration update script (Recommended)")
    print("     bash /opt/jiuwenswarm-env/configure-and-restart.sh model /root/.jiuwenswarm/config/.env")
    print("")
    print("  2. Check service status: sudo systemctl status jiuwenswarm")
    print("  3. View logs: sudo journalctl -u jiuwenswarm -f")
    print("  4. Verify configuration: curl http://localhost:5173/health")

    result = {
        'config': config,
        'instance_id': instance_id,
        'instance_name': instance_name,
        'public_ip': public_ip,
        'configure_time': datetime.now().isoformat(),
        'success': success
    }

    output_path = Path(__file__).parent / "model_config_result.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n[INFO] Configuration result saved to {output_path}")
    print("\nNext step: Run config_channel.py to configure message channels")

if __name__ == "__main__":
    main()
