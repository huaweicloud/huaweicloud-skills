#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click OpenClaw Deployment - Gateway Status Query Module
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.lib import check_gateway_status_remote
from scripts.utils import prompt_for_input, REGION_IDS


def do_check_gateway(args):
    """
    Execute gateway status query
    
    Args:
        args: Command line argument object with the following attributes:
            - resource_id: L instance resource ID
            - region_id: Region ID
            - ak: Huawei Cloud AK (supports both long-term and temporary AK)
            - sk: Huawei Cloud SK (supports both long-term and temporary SK)
            - security_token: Security token for temporary credentials (optional, only required for temporary AK/SK)
    
    Returns:
        None
    """
    print("=" * 60)
    print("        OpenClaw Gateway Status Query")
    print("=" * 60)
    
    ak = getattr(args, 'ak', None)
    sk = getattr(args, 'sk', None)
    security_token = getattr(args, 'security_token', None)
    
    if not ak or not sk:
        print("\nHuawei Cloud credentials not configured, entering interactive configuration...")
        print("Please configure Huawei Cloud credentials:")
        print("  - Long-term AK/SK: No security_token required")
        print("  - Temporary AK/SK: Security token required")
        print("-" * 40)
        ak = prompt_for_input("Huawei Cloud AK (HW_ACCESS_KEY)", required=True)
        sk = prompt_for_input("Huawei Cloud SK (HW_SECRET_KEY)", required=True, hide_input=True)
        security_token = prompt_for_input("Security Token (optional, only for temporary credentials)", required=False)
    
    resource_id = args.resource_id if hasattr(args, 'resource_id') and args.resource_id else None
    region_id = args.region_id if hasattr(args, 'region_id') and args.region_id else None
    
    if not resource_id:
        resource_id = prompt_for_input("L instance resource ID", required=True)
    
    if not region_id:
        region_id = prompt_for_input("Region ID", required=False, default="cn-north-4", choices=REGION_IDS)
    
    print(f"\nQuery configuration:")
    print(f"  Resource ID: {resource_id}")
    print(f"  Region: {region_id}")
    
    print("\nQuerying gateway status...")
    result = check_gateway_status_remote(resource_id, region_id, 600, "root", ak, sk,security_token)
    
    if result.get("ok"):
        print(f"\n[OK] {result['text']}")
        if result.get("result"):
            print(f"  Execution ID: {result['result'].get('execute_uuid', 'Unknown')}")
            print(f"  Status: {result['result'].get('status', 'Unknown')}")
            if result['result'].get('output'):
                print(f"  Output:\n{result['result']['output']}")
    else:
        print(f"\n[FAIL] Query failed")
        if result.get("error"):
            print(f"  Error code: {result['error'].get('code')}")
            print(f"  Error message: {result['error'].get('message')}")
