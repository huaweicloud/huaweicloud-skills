#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click FlexusAgent Deployment - UniAgent Status Query Module
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
            - ak: Huawei Cloud AK
            - sk: Huawei Cloud SK
            - security_token: Huawei Cloud Security Token
    
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
        print("\nHuawei Cloud credentials not configured, entering interactive configuration...")
        print("Please configure Huawei Cloud credentials:")
        print("-" * 40)
        ak = prompt_for_input("Huawei Cloud AK", required=True)
        sk = prompt_for_input("Huawei Cloud SK", required=True, hide_input=True)
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
                print("\n" + "=" * 60)
                print("Instance details:")
                print("=" * 60)
                for resource in resources:
                    properties = resource.get('properties', {})
                    print(f"  Resource ID:       {resource.get('resource_id', 'Unknown')}")
                    print(f"  Instance name:     {properties.get('host_name', 'Unknown')}")
                    print(f"  UniAgent status: {resource.get('agent_status', 'Unknown')}")
                    print(f"  Floating IP:       {properties.get('floating_ip', 'Unknown')}")
                    print(f"  Region:         {properties.get('region_id', 'Unknown')}")
                    print("=" * 60)
                    
                    # Provide Web UI access instructions
                    floating_ip = properties.get('floating_ip', '')
                    if floating_ip and floating_ip != 'Unknown':
                        print(f"\n🌐 Web UI access URL: http://{floating_ip}:80")
                        print("📧 Default account: super@dify.com")
                        print("\n⚠️ Please change the default password in time!")
            else:
                print("\n⚠️ Instance information not found, please verify resource ID")
    else:
        print(f"\n[FAIL] Query failed")
        if result.get("error"):
            print(f"  Error code: {result['error'].get('code')}")
            print(f"  Error message: {result['error'].get('message')}")
