#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click OpenClaw Deployment - UniAgent Status Query Module
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.lib import query_uniagent_status
from scripts.utils import prompt_for_input


def do_check_uniagent(args):
    """
    Execute UniAgent status query
    
    Args:
        args: Command line argument object with the following attributes:
            - resource_id: L instance resource ID
            - ak: Huawei Cloud temporary AK
            - sk: Huawei Cloud temporary SK
            - security_token: Security token for temporary credentials (required)
    
    Returns:
        None
    """
    print("=" * 60)
    print("        UniAgent Status Query")
    print("=" * 60)
    
    ak = getattr(args, 'ak', None)
    sk = getattr(args, 'sk', None)
    security_token = getattr(args, 'security_token', None)

    if not ak or not sk:
        print("\nHuawei Cloud temporary credentials not configured, entering interactive configuration...")
        print("Please configure Huawei Cloud temporary credentials:")
        print("-" * 40)
        ak = prompt_for_input("Huawei Cloud temporary AK", required=True)
        sk = prompt_for_input("Huawei Cloud temporary SK", required=True, hide_input=True)
        security_token = prompt_for_input("Huawei Cloud Security Token (required for temporary credentials)", required=True)
    
    resource_id = args.resource_id if hasattr(args, 'resource_id') and args.resource_id else None
    
    if not resource_id:
        resource_id = prompt_for_input("L instance resource ID", required=True)
    
    print(f"\nQuery configuration:")
    print(f"  Resource ID: {resource_id}")
    
    print("\nQuerying UniAgent status...")
    result = query_uniagent_status(resource_id, ak, sk, security_token)
    
    if result.get("ok"):
        print(f"\n[OK] {result['text']}")
        if result.get("result"):
            data = result['result']
            resources = data.get("data", [])
            if resources:
                for resource in resources:
                    print(f"  Resource ID: {resource.get('resource_id', 'Unknown')}")
                    print(f"  UniAgent status: {resource.get('agent_state', 'Unknown')}")
                    print(f"  Instance name: {resource.get('name', 'Unknown')}")
    else:
        print(f"\n[FAIL] Query failed")
        if result.get("error"):
            print(f"  Error code: {result['error'].get('code')}")
            print(f"  Error message: {result['error'].get('message')}")
