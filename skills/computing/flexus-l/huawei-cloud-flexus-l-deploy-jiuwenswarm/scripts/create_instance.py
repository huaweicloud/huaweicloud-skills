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

sys.path.insert(0, str(Path(__file__).parent))
from utils import get_huaweicloud_credentials


def get_project_id_by_region(ak: str, sk: str, security_token: Optional[str], region: str) -> Optional[str]:
    """Get Project ID for a specified region"""
    iam_endpoint = "https://iam.myhuaweicloud.com/v3/projects"
    
    try:
        from huaweicloudsdkcore.signer.signer import Signer
        from huaweicloudsdkcore.sdk_request import SdkRequest
        from huaweicloudsdkcore.auth.credentials import BasicCredentials, GlobalCredentials

        if security_token:
            credentials = BasicCredentials(ak, sk).with_security_token(security_token)
        else:
            credentials = BasicCredentials(ak, sk)
        signer = Signer(credentials)
        
        request = SdkRequest()
        request.method = "GET"
        request.schema = "https"
        request.host = "iam.myhuaweicloud.com"
        request.resource_path = "/v3/projects"
        request.body = ""
        request.header_params = {
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
        return None
    except Exception as e:
        print(f"Failed to get Project ID: {e}")
        return None

def get_flexus_flavors_for_region(region: str):
    return {
        "small": "hf.small.1.linux",
        "medium": "hf.medium.1.linux",
        "large": "hf.large.1.linux",
        "xlarge": "hf.xlarge.1.linux",
        "2xlarge": "hf.2xlarge.1.linux"
    }

def create_flexus_l_instance(ak, sk, security_token, project_id, region, instance_name, flavor="medium", wait=True, timeout=600):
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
        "is_auto_pay": True,
        "extra_resources": [
            {"type": "evs", "size": 50},
            {"type": "cbr", "size": 50},
            {"type": "hss"}
        ]
    }

    if not project_id:
        project_id = get_project_id_by_region(ak, sk, security_token, region)
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

    parsed_url = urlparse(FLEXUS_API_ENDPOINT)
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
    request.query_params = []

    signed_request = signer.sign(request)

    headers = {}
    for key, value in signed_request.header_params.items():
        if isinstance(value, bytes):
            headers[key] = value.decode('iso-8859-1')
        else:
            headers[key] = str(value)
    
    # Manually add X-Security-Token header for temporary credentials (not automatically added by SDK signing)
    if security_token:
        headers["X-Security-Token"] = security_token

    resp = requests.post(FLEXUS_API_ENDPOINT, headers=headers, data=body_str, timeout=30)

    if resp.status_code in [200, 201, 202]:
        result = resp.json()
        order_id = result.get('order_id')
        log.info(f"Instance creation request submitted, Order ID: {order_id}")
        return order_id
    else:
        log.error(f"Instance creation failed: HTTP {resp.status_code}, {resp.text}")
        return None

def query_instance_status(ak, sk, security_token, region, resource_id):
    from huaweicloudsdkcore.auth.credentials import GlobalCredentials
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
        rid = getattr(r, 'id', '') or getattr(r, 'resource_id', '')
        if rid == resource_id:
            props = getattr(r, 'properties', None)
            if props:
                return props.get('status', 'UNKNOWN')
            return 'UNKNOWN'

    return None

def get_instance_info(ak, sk, security_token, region, resource_id):
    from huaweicloudsdkcore.auth.credentials import GlobalCredentials
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
        rid = getattr(r, 'id', '') or getattr(r, 'resource_id', '')
        if rid == resource_id:
            name = getattr(r, 'name', '') or getattr(r, 'resource_name', '')
            instance_id = rid
            props = getattr(r, 'properties', None)

            public_ip = None
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

def show_confirmation(instance_name, flavor, region):
    flavor_display = {
        "small": "small (1 vCPU, 2GB RAM)",
        "medium": "medium (2 vCPU, 4GB RAM)",
        "large": "large (4 vCPU, 8GB RAM)",
        "xlarge": "xlarge (8 vCPU, 16GB RAM)",
        "2xlarge": "2xlarge (16 vCPU, 32GB RAM)"
    }

    print("\n" + "=" * 60)
    print("  ⚠️ Cloud Resource Creation Confirmation")
    print("=" * 60)
    print(f"\nOperation to perform: Create new Flexus L Instance\n")
    print("Instance Specification:")
    print(f"  - Name: {instance_name}")
    print(f"  - Flavor: {flavor_display.get(flavor, flavor)}")
    print(f"  - Region: {region}")
    print(f"  - Estimated Cost: ~100 CNY/month (actual price subject to Huawei Cloud pricing)\n")
    print("Resources will be created immediately after confirmation.")
    print("=" * 60)
    print("\nPlease enter 'confirm' or 'yes' to continue:")
    print("> ", end="")

    response = input().strip().lower()
    return response in ['confirm', 'yes', 'ok', 'y']

def parse_args():
    parser = argparse.ArgumentParser(description='Create Flexus L Instance')
    parser.add_argument('--name', type=str, default=f"jiuwenSwarm-{datetime.now().strftime('%Y%m%d%H%M%S')}", help='Instance name')
    parser.add_argument('--flavor', type=str, default='medium', choices=['small', 'medium', 'large', 'xlarge', '2xlarge'], help='Instance flavor')
    parser.add_argument('--region', type=str, default='cn-north-4', help='Region (cn-north-4 only)')
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

    # Validate region - only cn-north-4 is supported
    if args.region != 'cn-north-4':
        print(f"[ERROR] Only cn-north-4 region is supported, current region: {args.region}")
        print("[INFO] Please use --region cn-north-4 or use the default value")
        sys.exit(1)

    if SECURITY_TOKEN:
        print(f"[INFO] Using temporary security credentials (STS token)")

    if not args.confirm:
        if not show_confirmation(args.name, args.flavor, args.region):
            print("\n[INFO] User cancelled operation")
            sys.exit(0)

    print(f"\n[INFO] Starting to create Flexus L instance...")
    print(f"[INFO] Instance name: {args.name}")
    print(f"[INFO] Flavor: {args.flavor}")
    print(f"[INFO] Region: {args.region}")

    project_id = get_project_id_by_region(AK, SK, SECURITY_TOKEN, args.region)
    if not project_id:
        print("[ERROR] Failed to get Project ID")
        sys.exit(1)
    print(f"[INFO] Project ID: {project_id}")

    order_id = create_flexus_l_instance(AK, SK, SECURITY_TOKEN, project_id, args.region, args.name, args.flavor, args.wait, args.timeout)
    if not order_id:
        print("[ERROR] Instance creation request failed")
        sys.exit(1)

    print(f"[INFO] Order ID: {order_id}")

    result_file = Path(__file__).parent / "instance_order.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({'order_id': order_id, 'instance_name': args.name, 'flavor': args.flavor, 'region': args.region}, f, indent=2)
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
                from huaweicloudsdkcore.auth.credentials import GlobalCredentials, BasicCredentials
                from huaweicloudsdkrms.v1 import RmsClient
                from huaweicloudsdkrms.v1.region.rms_region import RmsRegion
                from huaweicloudsdkrms.v1 import model

                if SECURITY_TOKEN:
                    credentials = GlobalCredentials(AK, SK).with_security_token(SECURITY_TOKEN)
                else:
                    credentials = GlobalCredentials(AK, SK)
                
                client = RmsClient.new_builder() \
                    .with_credentials(credentials) \
                    .with_region(RmsRegion.value_of(args.region)) \
                    .build()

                request = model.ListAllResourcesRequest()
                request.region_id = args.region
                request.type = "hcss.l-instance"
                request.limit = 200

                response = client.list_all_resources(request)
                resources = response.resources if hasattr(response, 'resources') else []

                for r in resources:
                    name = getattr(r, 'name', '') or getattr(r, 'resource_name', '')
                    if name == args.name:
                        resource_id = getattr(r, 'id', '') or getattr(r, 'resource_id', '')
                        props = getattr(r, 'properties', None)
                        status = props.get('status') if props else 'UNKNOWN'
                        print(f"[{elapsed}s] Instance status: {status}")

                        if status == 'RUNNING':
                            print("\n[SUCCESS] Instance created successfully!")
                            instance_info = get_instance_info(AK, SK, SECURITY_TOKEN, args.region, resource_id)
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

    print("\n[INFO] Instance creation request submitted, use RMS API to query instance status")
    print("Next step: Run install_deps.py for COC remote dependency installation")

if __name__ == "__main__":
    main()
