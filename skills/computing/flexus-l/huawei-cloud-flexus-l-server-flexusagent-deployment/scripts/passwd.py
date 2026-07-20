#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click FlexusAgent Deployment - Change Admin Password Module
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.lib import change_flexusagent_admin_password, query_uniagent_status
from scripts.utils import prompt_for_input, REGION_IDS


def _check_prerequisites(resource_id, region_id, ak, sk, security_token=None):
    """
    Check prerequisites (UniAgent status)
    
    Args:
        resource_id: L instance resource ID
        region_id: Region ID
        ak: Huawei Cloud AK
        sk: Huawei Cloud SK
        security_token: Security token for temporary credentials
    
    Returns:
        bool: True if check passed, False if check failed
    """
    print("\nChecking UniAgent status...")
    result = query_uniagent_status(resource_id, ak, sk, security_token)
    
    if not result.get("ok"):
        print(f"  [FAIL] UniAgent status check failed: {result.get('error', {}).get('message', 'Unknown error')}")
        return False

    data = result.get("result", {})
    resources = data.get("data", [])

    if not resources:
        print("  [FAIL] Instance information not found")
        return False

    for resource in resources:
        agent_state = resource.get("agent_state", "")
        if agent_state == "ONLINE":
            print("  [OK] UniAgent status: ONLINE")
            return True
        else:
            print(f"  [FAIL] UniAgent status: {agent_state}")
            print("    Please ensure UniAgent is started and online")
            return False

    return False


def do_change_flexusagent_admin_password(args):
    """Change FlexusAgent admin user password"""
    print("=" * 60)
    print("        Change FlexusAgent Admin Password")
    print("=" * 60)

    ak = getattr(args, 'ak', None) or os.environ.get('HW_ACCESS_KEY')
    sk = getattr(args, 'sk', None) or os.environ.get('HW_SECRET_KEY')
    security_token = getattr(args, 'security_token', None) or os.environ.get('HW_SECURITY_TOKEN', None)

    if not ak or not sk:
        print("\nHuawei Cloud credentials not configured, entering interactive configuration...")
        print("Please configure Huawei Cloud credentials:")
        print("-" * 40)
        raise ValueError("Huawei Cloud credentials not configured.")
    
    resource_id = args.resource_id if hasattr(args, 'resource_id') and args.resource_id else None
    region_id = args.region_id if hasattr(args, 'region_id') and args.region_id else None
    admin_password = args.admin_password if hasattr(args, 'admin_password') and args.admin_password else ""
    timeout = args.timeout if hasattr(args, 'timeout') and args.timeout else 600
    execute_user = "root"
    non_interactive = args.non_interactive if hasattr(args, 'non_interactive') else False

    # Get parameters interactively
    if not resource_id:
        resource_id = prompt_for_input("L Instance Resource ID", required=True)

    if not region_id:
        region_id = prompt_for_input("Region ID", required=False, default="cn-north-4", choices=REGION_IDS)

    if not admin_password:
        print("\nNew FlexusAgent admin password")
        admin_password = prompt_for_input("New FlexusAgent admin password (required)", required=True)

    if not timeout:
        timeout = int(prompt_for_input("Timeout (seconds)", required=False, default="600"))

    print(f"  Resource ID: {resource_id}")
    print(f"  Region: {region_id}")
    print(f"  Admin Password: {admin_password}")
    print(f"  Timeout: {timeout} seconds")

    if not non_interactive:
        confirm = prompt_for_input("Confirm change?", required=False, default="y", choices=["y", "n"])
        if confirm.lower() != "y":
            print("\nChange cancelled")
            return

    print("\nChecking prerequisites...")
    if not _check_prerequisites(resource_id, region_id, ak, sk, security_token):
        print("\nPrerequisite check failed, please resolve and try again")
        return

    print("\nChanging FlexusAgent admin password...")
    result = change_flexusagent_admin_password(resource_id, region_id, admin_password, timeout, execute_user, ak, sk, security_token)

    if result.get("ok"):
        print(f"\n✓ {result['text']}")
        if result.get("result"):
            print(f"  Execution ID: {result['result'].get('execute_uuid', 'Unknown')}")
            print(f"  Status: {result['result'].get('status', 'Unknown')}")
            if result['result'].get('output'):
                print(f"  Output: {result['result']['output'][:200]}...")
    else:
        print(f"\n✗ Operation failed")
        if result.get("error"):
            print(f"  Error Code: {result['error'].get('code')}")
            print(f"  Error Message: {result['error'].get('message')}")
