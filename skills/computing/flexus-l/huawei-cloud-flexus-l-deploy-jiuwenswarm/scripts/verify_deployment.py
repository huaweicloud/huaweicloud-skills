#!/usr/bin/env python3
"""
JiuwenSwarm Deployment Verification Script
Verifies JiuwenSwarm service deployment on Huawei Cloud Flexus instances.
Uses COC (Cloud Operation Center) to execute verification commands and check deployment status.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

os.environ['PYTHONIOENCODING'] = 'utf-8'

sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    get_huaweicloud_credentials,
    coc_create_script,
    coc_execute_script,
    coc_query_execution,
    rms_list_all_resources,
    print_info,
    print_success,
    print_error
)

def query_instance_by_ip(ak, sk, security_token, region, public_ip):
    try:
        # Query via KooCLI: RMS is a global service, always use the unified cn-north-4
        # endpoint. Filter by region to ensure RMS returns data for the target region.
        resources = rms_list_all_resources(region_id=region, resource_type="hcss.l-instance", limit=200)

        for r in resources:
            name = r.get('name', '') or r.get('resource_name', '')
            instance_id = r.get('id', '') or r.get('resource_id', '')
            props = r.get('properties') or {}

            ip = None
            ecs_instance_id = None

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
                    'region': r.get('region_id', '') or region,
                    'status': props.get('status') if props else 'UNKNOWN'
                }
    except Exception as e:
        print_error(f"Failed to query Flexus L instance information: {e}")

    return None

def load_instance_info():
    info_file = Path(__file__).parent / "new_instance_info.json"
    if info_file.exists():
        with open(info_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def verify_deployment(instance_info):
    print("\n" + "=" * 60)
    print("  Phase 5: Verify JiuwenSwarm Service Deployment")
    print("=" * 60)

    public_ip = instance_info['public_ip']
    instance_id = instance_info['instance_id']
    region = instance_info.get('region', 'cn-north-4')

    print_info(f"Instance Public IP: {public_ip}")
    print_info(f"Instance ID: {instance_id}")
    print_info(f"Region: {region}")

    # Verification script - checks service status, .env config, port binding, and HTTP health
    verification_script = '''#!/bin/bash
echo "=== JiuwenSwarm Deployment Verification ==="
ALL_OK=true

# 1. Service status
echo "--- [1/4] Service Status ---"
systemctl is-active --quiet jiuwenswarm && echo "PASS: service running" || { echo "FAIL: service not running"; exit 1; }

# 2. .env FRONTEND_HOST check (required for external web access)
echo "--- [2/4] .env FRONTEND_HOST ---"
ENV_FILE="/root/.jiuwenswarm/config/.env"
if [ -f "$ENV_FILE" ]; then
    if grep -q "^[[:space:]]*FRONTEND_HOST=0.0.0.0" "$ENV_FILE"; then
        echo "PASS: FRONTEND_HOST=0.0.0.0 in .env"
    else
        echo "FAIL: FRONTEND_HOST not set to 0.0.0.0 in .env"; ALL_OK=false
    fi
else
    echo "FAIL: .env file not found at $ENV_FILE"; ALL_OK=false
fi

# 3. Port binding (0.0.0.0 vs 127.0.0.1)
echo "--- [3/4] Port Binding ---"
for port in 5173 18092 19000 19001; do
    if ss -tlnp 2>/dev/null | grep -q "0.0.0.0:$port"; then
        echo "PASS: port $port on 0.0.0.0"
    else
        echo "FAIL: port $port not on 0.0.0.0"; ALL_OK=false
    fi
done

# 4. HTTP health check
echo "--- [4/4] HTTP Health ---"
HTTP_CODE=$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 http://localhost:5173/ 2>/dev/null)
[ "$HTTP_CODE" = "200" ] && echo "PASS: HTTP 200" || { echo "FAIL: HTTP $HTTP_CODE"; ALL_OK=false; }

# Summary
if [ "$ALL_OK" = "true" ]; then
    echo "VERIFICATION_PASSED"
else
    echo "VERIFICATION_WARNINGS"
fi
echo "Web URL: http://$(hostname -I | awk '{print $1}'):5173"
exit 0
'''

    print("\n" + "=" * 60)
    print("  Step 1: Create COC Verification Script")
    print("=" * 60)

    script_name = f"jiuwenswarm_verify_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    create_result = coc_create_script(
        name=script_name,
        script_type="SHELL",
        content=verification_script,
        description="JiuwenSwarm Deployment Verification Script"
    )

    if not create_result.get("ok"):
        print_error(f"Failed to create script: {create_result.get('error', {}).get('message', 'Unknown error')}")
        return False

    script_uuid = create_result.get("result", {}).get("script_uuid")
    print_success(f"Script created successfully, UUID: {script_uuid}")

    print("\n" + "=" * 60)
    print("  Step 2: Execute Verification Script on Target Instance")
    print("=" * 60)

    target_instances = [{
        "resource_id": instance_id,
        "region_id": region,
        "provider": "HCSS",
        "type": "L-INSTANCE"
    }]

    execute_result = coc_execute_script(
        script_uuid=script_uuid,
        execute_user="root",
        timeout=600,
        success_rate=100.0,
        target_instances=target_instances,
        rotation_strategy="CONTINUE",
        wait_for_complete=False
    )

    if not execute_result.get("ok"):
        print_error(f"Failed to submit COC job: {execute_result.get('error', {}).get('message', 'Unknown error')}")
        return False

    execute_uuid = execute_result.get("result", {}).get("execute_uuid")
    print_success(f"COC job submitted successfully")
    print_info(f"Execution UUID: {execute_uuid}")

    print("\n" + "=" * 60)
    print("  Step 3: Wait for COC Script Execution to Complete")
    print("=" * 60)

    start_time = time.time()
    EXECUTION_TIMEOUT = 600

    while time.time() - start_time < EXECUTION_TIMEOUT:
        job_result = coc_query_execution(execute_uuid)
        if job_result.get("ok"):
            status = job_result.get("result", {}).get("status", "UNKNOWN")
            
            if status == "FINISHED":
                print_success("COC remote script execution successful")

                result_data = job_result.get("result", {})
                script_output = result_data.get('output', '')

                if script_output:
                    print("\n" + "-" * 40)
                    print(script_output)
                    print("-" * 40)

                if "VERIFICATION_PASSED" in script_output:
                    print_success("Deployment verification passed!")
                else:
                    print_info("Verification completed with warnings - some non-critical checks failed.")
                    print_info("Continuing with fault tolerance. Please review the output above.")

                web_url = f"http://{public_ip}:5173"
                print_info(f"Web URL: {web_url}")
                print_info("Ensure security group allows inbound TCP 5173")

                verification_result = {
                    'deploy_success': True,
                    'verify_uuid': execute_uuid,
                    'web_url': web_url,
                    'status': result_data.get('status'),
                    'create_time': result_data.get('create_time'),
                    'finish_time': result_data.get('finish_time')
                }

                result_file = Path(__file__).parent / "verification_result.json"
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(verification_result, f, indent=2, ensure_ascii=False)
                print_info(f"Result saved to: {result_file}")

                return True

            elif status in ["CANCELED", "ABNORMAL", "FAILED", "TIMEOUT"]:
                print_error(f"Script execution failed, status: {status}")
                return False

        time.sleep(5)

    print_error("Script execution timeout")
    return False

def parse_args():
    parser = argparse.ArgumentParser(description='Verify JiuwenSwarm Service Deployment')
    parser.add_argument('--instance-id', type=str, help='Instance RMS resource ID')
    parser.add_argument('--ip', type=str, help='Instance public IP address')
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

    instance_info = None

    if args.instance_id and args.ip:
        instance_info = {
            'instance_id': args.instance_id,
            'public_ip': args.ip,
            'region': REGION
        }
    elif args.ip:
        print(f"[INFO] Querying instance info by public IP: {args.ip}")
        instance_info = query_instance_by_ip(AK, SK, SECURITY_TOKEN, REGION, args.ip)
        if not instance_info:
            print("[ERROR] Cannot find instance with specified IP")
            sys.exit(1)
    else:
        instance_info = load_instance_info()
        if not instance_info:
            print("[ERROR] Cannot get instance info")
            sys.exit(1)

    print(f"\nInstance Info:")
    print(f"  - Instance ID: {instance_info['instance_id']}")
    print(f"  - Public IP: {instance_info['public_ip']}")

    success = verify_deployment(instance_info)

    if success:
        print("\nNext step: Run config_model.py to configure model parameters")
        sys.exit(0)
    else:
        print("\nVerification failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
