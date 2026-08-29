#!/usr/bin/env python3
"""
Flexus L Instance Creation Script
Creates Huawei Cloud Flexus L instances for JiuwenSwarm deployment.
Handles instance provisioning, resource allocation, and status monitoring.
"""

import os
import sys
import json
import time
import uuid
import argparse
import logging
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path

os.environ['PYTHONIOENCODING'] = 'utf-8'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    log.error("requests module not installed")
    sys.exit(1)

FLEXUS_API_ENDPOINT = "https://hcss.cn-north-4.myhuaweicloud.com/v1/light-instances"

# Supported regions and their display names
SUPPORTED_REGIONS = {
    "cn-north-4": "华北-北京四",
    "cn-east-3": "华东-上海一",
    "cn-south-1": "华南-广州",
    "cn-southwest-2": "西南-贵阳一"
}

# Region prefix mapping: hf. for most regions, ahf. for Guiyang (cn-southwest-2)
REGION_SPEC_PREFIX = {
    "cn-north-4": "hf.",
    "cn-east-3": "hf.",
    "cn-south-1": "hf.",
    "cn-southwest-2": "ahf."
}

sys.path.insert(0, str(Path(__file__).parent))
from utils import get_huaweicloud_credentials, get_project_id_by_region, rms_list_all_resources, masked


def get_flexus_flavors_for_region(region: str):
    """
    Get flexus flavors for a specific region.
    Beijing/Shanghai/Guangzhou use hf. prefix, Guiyang uses ahf. prefix.
    
    Available flavors:
    - 2c-4g-50g: 2 vCPU, 4GB RAM, 50GB disk (hf.large.2.3m.linux / ahf.large.2.3m.linux)
    - 2c-4g-70g: 2 vCPU, 4GB RAM, 70GB disk (hf.medium.1.linux / ahf.medium.1.linux)
    - 4c-8g-180g: 4 vCPU, 8GB RAM, 180GB disk (hf.xlarge.1.linux / ahf.xlarge.1.linux)
    """
    prefix = REGION_SPEC_PREFIX.get(region, "hf.")
    return {
        "2c-4g-50g": f"{prefix}large.2.3m.linux",
        "2c-4g-70g": f"{prefix}medium.1.linux",
        "4c-8g-180g": f"{prefix}xlarge.1.linux"
    }

def create_flexus_l_instance(ak, sk, security_token, project_id, region, instance_name, flavor="2c-4g-50g", wait=True, timeout=600):
    flavors = get_flexus_flavors_for_region(region)
    flavor_ref = flavors.get(flavor)
    if not flavor_ref:
        raise ValueError(f"Unsupported flavor: {flavor}")

    request_body = {
        "instance_name": instance_name,
        "plan_spec": flavor_ref,
        "image_ref": {
            "image_name": "Ubuntu",
            "image_version": "24.04"
        },
        "region": region,
        "charging_mode": "prePaid",
        "period_type": "month",
        "period_num": 1,
        "purchase_quantity": 1,
        "description": f"JiuwenSwarm deployment - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "is_auto_renew": True,
        "is_auto_pay": True
    }

    if not project_id:
        project_id = get_project_id_by_region(region)
        if not project_id:
            raise ValueError(f"Failed to get Project ID for region {region}")

    from huaweicloudsdkcore.signer.signer import Signer
    from huaweicloudsdkcore.sdk_request import SdkRequest
    from huaweicloudsdkcore.auth.credentials import GlobalCredentials, BasicCredentials

    # Use AK/SK direct signature to call Flexus L API, add X-Project-Id header to identify project
    credentials = BasicCredentials(ak, sk, project_id)
    if security_token:
        credentials = credentials.with_security_token(security_token)

    signer = Signer(credentials)

    endpoint = FLEXUS_API_ENDPOINT
    parsed_url = urlparse(endpoint)
    body_str = json.dumps(request_body, ensure_ascii=False, separators=(',', ':'))

    request = SdkRequest()
    request.method = "POST"
    request.schema = parsed_url.scheme
    request.host = parsed_url.hostname
    request.resource_path = parsed_url.path
    request.body = body_str
    request.header_params = {
        "Content-Type": "application/json",
        "Client-Request-Id": str(uuid.uuid4()),
        "X-Id": "/v1/light-instances",
        "X-Project-Id": project_id
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

    resp = requests.post(endpoint, headers=headers, data=body_str, timeout=30)

    if resp.status_code in [200, 201, 202]:
        result = resp.json()
        order_id = result.get('order_id')
        log.info(f"Instance creation request submitted, Order ID: {order_id}")
        return order_id
    else:
        log.error(f"Instance creation failed: HTTP {resp.status_code}, {resp.text}")
        return None

def query_instance_status(region, resource_id):
    # Query via KooCLI: RMS is a global service, always use the unified cn-north-4
    # endpoint and filter resources of the target region via the region_id parameter.
    resources = rms_list_all_resources(region_id=region, resource_type="hcss.l-instance", limit=200)

    for r in resources:
        rid = r.get('id', '') or r.get('resource_id', '')
        if rid == resource_id:
            props = r.get('properties') or {}
            return props.get('status', 'UNKNOWN')

    return None

def get_instance_info(region, resource_id):
    # Query via KooCLI: RMS is a global service, always use the unified cn-north-4
    # endpoint and filter resources of the target region via the region_id parameter.
    resources = rms_list_all_resources(region_id=region, resource_type="hcss.l-instance", limit=200)

    for r in resources:
        rid = r.get('id', '') or r.get('resource_id', '')
        if rid == resource_id:
            name = r.get('name', '') or r.get('resource_name', '')
            instance_id = rid
            props = r.get('properties') or {}

            public_ip = None
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
                                public_ip = value
                            if key == 'associate_instance_id':
                                ecs_instance_id = value

            return {
                'instance_name': name,
                'instance_id': instance_id,
                'ecs_instance_id': ecs_instance_id,
                'public_ip': public_ip,
                'region': region,
                'status': props.get('status') if props else 'UNKNOWN'
            }

    return None

def interactive_select_region():
    """Interactive region selection menu"""
    print("\n" + "=" * 60)
    print("  Select Region to Create Instance")
    print("=" * 60)
    print("\nAvailable regions:")
    region_list = list(SUPPORTED_REGIONS.items())
    for idx, (code, name) in enumerate(region_list, 1):
        print(f"  {idx}. {name} ({code})")
    print(f"  {len(region_list) + 1}. Use environment variable HUAWEICLOUD_REGION default")

    while True:
        try:
            choice = input(f"\nEnter your choice (1-{len(region_list) + 1}): ").strip()
            if not choice:
                print("[INFO] Using default region from environment variable")
                return None
            idx = int(choice)
            if 1 <= idx <= len(region_list):
                selected = region_list[idx - 1][0]
                print(f"[INFO] Selected region: {region_list[idx - 1][1]} ({selected})")
                return selected
            elif idx == len(region_list) + 1:
                print("[INFO] Using default region from environment variable")
                return None
            else:
                print(f"[ERROR] Invalid choice, please enter 1-{len(region_list) + 1}")
        except ValueError:
            print(f"[ERROR] Invalid input, please enter a number (1-{len(region_list) + 1})")

def show_confirmation(instance_name, flavor, region):
    flavor_display = {
        "2c-4g-50g": "2 vCPU 4GB 50GB",
        "2c-4g-70g": "2 vCPU 4GB 70GB",
        "4c-8g-180g": "4 vCPU 8GB 180GB"
    }

    flavor_cost = {
        "2c-4g-50g": "Estimated 60 CNY/month",
        "2c-4g-70g": "Estimated 100 CNY/month",
        "4c-8g-180g": "Estimated 170 CNY/month"
    }

    region_display = SUPPORTED_REGIONS.get(region, region)

    print("\n" + "=" * 60)
    print("  ⚠️ Cloud Resource Creation Confirmation")
    print("=" * 60)
    print(f"\nOperation to perform: Create new Flexus L Instance\n")
    print("Instance Specification:")
    print(f"  - Name: {instance_name}")
    print(f"  - Flavor: {flavor_display.get(flavor, flavor)}")
    print(f"  - Region: {region_display} ({region})")
    print(f"  - Estimated Cost: {flavor_cost.get(flavor, 'Estimated 60 CNY/month')}, actual price subject to Huawei Cloud official website\n")
    print("Resources will be created immediately after confirmation.")
    print("=" * 60)
    print("\nPlease enter 'confirm' or 'yes' to continue:")
    print("> ", end="")

    response = input().strip().lower()
    return response in ['confirm', 'yes', 'ok', 'y']

def parse_args():
    parser = argparse.ArgumentParser(description='Create Flexus L Instance')
    parser.add_argument('--name', type=str, default=f"jiuwenSwarm-{datetime.now().strftime('%Y%m%d%H%M%S')}", help='Instance name')
    parser.add_argument('--flavor', type=str, default='2c-4g-50g', choices=['2c-4g-50g', '2c-4g-70g', '4c-8g-180g'], help='Instance flavor (2c-4g-50g: ~60 CNY/month, 2c-4g-70g: ~100 CNY/month, 4c-8g-180g: ~170 CNY/month)')
    parser.add_argument('--region', type=str, default=None, choices=list(SUPPORTED_REGIONS.keys()), help='Region to create instance in. If not specified, interactive selection will be shown.')
    parser.add_argument('--wait', action='store_true', help='Wait for instance creation to complete')
    parser.add_argument('--timeout', type=int, default=600, help='Timeout in seconds')
    parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompt')
    return parser.parse_args()

def main():
    args = parse_args()

    print("\n" + "=" * 60)
    print("  Phase 2: Create Flexus L Instance")
    print("=" * 60)

    try:
        AK, SK, REGION, SECURITY_TOKEN = get_huaweicloud_credentials()
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    # Interactive region selection if --region not provided
    target_region = args.region
    if target_region is None:
        selected = interactive_select_region()
        if selected is not None:
            target_region = selected
        else:
            # Use environment variable default
            target_region = REGION
            print(f"[INFO] Using environment default region: {target_region}")

    # Validate region - check if it's in supported regions
    if target_region not in SUPPORTED_REGIONS:
        print(f"[ERROR] Unsupported region: {target_region}")
        print(f"[INFO] Supported regions: {', '.join(SUPPORTED_REGIONS.keys())}")
        sys.exit(1)

    if not args.confirm:
        if not show_confirmation(args.name, args.flavor, target_region):
            print("\n[INFO] User cancelled operation")
            sys.exit(0)

    print(f"\n[INFO] Starting to create Flexus L instance...")
    print(f"[INFO] Instance name: {args.name}")
    print(f"[INFO] Flavor: {args.flavor}")
    print(f"[INFO] Region: {target_region}")

    project_id = get_project_id_by_region(target_region)
    if not project_id:
        print("[ERROR] Failed to get Project ID")
        sys.exit(1)
    print(f"[INFO] Project ID: {project_id}")

    order_id = create_flexus_l_instance(AK, SK, SECURITY_TOKEN, project_id, target_region, args.name, args.flavor, args.wait, args.timeout)
    if not order_id:
        print("[ERROR] Instance creation request failed")
        sys.exit(1)

    print(f"[INFO] Order ID: {order_id}")

    result_file = Path(__file__).parent / "instance_order.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({'order_id': order_id, 'instance_name': args.name, 'flavor': args.flavor, 'region': target_region}, f, indent=2)
    print(f"[INFO] Order information saved to: {result_file}")

    if args.wait:
        print(f"\n[INFO] Waiting for instance creation to complete (timeout: {args.timeout} seconds)...")

        elapsed = 0
        interval = 30
        resource_id = None

        while elapsed < args.timeout:
            time.sleep(interval)
            elapsed += interval

            try:
                resources = rms_list_all_resources(region_id=target_region, resource_type="hcss.l-instance", limit=200)

                for r in resources:
                    name = r.get('name', '') or r.get('resource_name', '')
                    if name == args.name:
                        resource_id = r.get('id', '') or r.get('resource_id', '')
                        props = r.get('properties') or {}
                        status = props.get('status', 'UNKNOWN')
                        print(f"[{elapsed}s] Instance status: {status}")

                        if status == 'RUNNING':
                            print("\n[SUCCESS] Instance created successfully!")
                            instance_info = get_instance_info(target_region, resource_id)
                            if instance_info:
                                info_file = Path(__file__).parent / "new_instance_info.json"
                                with open(info_file, 'w', encoding='utf-8') as f:
                                    json.dump(instance_info, f, indent=2, ensure_ascii=False)
                                print(f"[INFO] Instance information saved to: {info_file}")
                                print(f"\nInstance Information:")
                                print(f"  - Instance ID: {instance_info['instance_id']}")
                                print(f"  - Public IP: {instance_info['public_ip']}")
                                print(f"  - ECS Instance ID: {instance_info['ecs_instance_id']}")
                            print("\nNext step: Run install_deps.py for COC remote dependency installation")
                            sys.exit(0)
                        break

            except Exception as e:
                print(f"[WARN] Error querying instance status: {e}")

        print("[ERROR] Instance creation timeout")
        sys.exit(1)

    print("\n[INFO] Instance creation request submitted, use RMS CLI (hcloud RMS ListAllResources) to query instance status")
    print("Next step: Run install_deps.py for COC remote dependency installation")

if __name__ == "__main__":
    main()
