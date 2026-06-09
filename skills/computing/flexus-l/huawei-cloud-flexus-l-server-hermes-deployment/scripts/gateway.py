#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click Hermes Deployment - Gateway Management Module

Note: This module supports both long-term and temporary credentials.
      - Long-term AK/SK: No security_token required
      - Temporary AK/SK: Security token required
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.lib import restart_gateway_remote
from scripts.utils import prompt_for_input, REGION_IDS


def do_restart_gateway(args):
    """Execute Hermes gateway restart
    
    Args:
        args: Command line argument object with the following attributes:
            - resource_id: L instance resource ID (command line arg --resource-id)
            - region_id: Region ID (command line arg --region-id)
            - timeout: Timeout duration (command line arg --timeout)
            - execute_user: Execute user (command line arg --execute-user)
            - ak: Huawei Cloud AK (supports both long-term and temporary AK) (command line arg --ak)
            - sk: Huawei Cloud SK (supports both long-term and temporary SK) (command line arg --sk)
            - security_token: Security token for temporary credentials (optional, only required for temporary AK/SK) (command line arg --security-token)
            - non_interactive: Whether non-interactive mode (command line arg --non-interactive)

    Returns:
        None
    """
    print("=" * 60)
    print("        Hermes Gateway Restart")
    print("=" * 60)
    
    non_interactive = args.non_interactive if hasattr(args, 'non_interactive') else False
    
    # Get credentials (from command line parameters)
    ak = args.ak if hasattr(args, 'ak') and args.ak else None
    sk = args.sk if hasattr(args, 'sk') and args.sk else None
    security_token = args.security_token if hasattr(args, 'security_token') and args.security_token else None

    # If credentials not provided, prompt interactively (skip in non-interactive mode)
    if not ak or not sk:
        print("\nHuawei Cloud credentials not configured, entering interactive configuration...")
        print("Please configure Huawei Cloud credentials:")
        print("  - Long-term AK/SK: No security_token required")
        print("  - Temporary AK/SK: Security token required")
        print("-" * 40)
        ak = prompt_for_input("Huawei Cloud AK (HW_ACCESS_KEY)", required=True)
        sk = prompt_for_input("Huawei Cloud SK (HW_SECRET_KEY)", required=True, hide_input=True)
        security_token = prompt_for_input("Security Token (optional, only for temporary credentials)", required=False)
    
    # Get parameters
    resource_id = args.resource_id if hasattr(args, 'resource_id') and args.resource_id else None
    region_id = args.region_id if hasattr(args, 'region_id') and args.region_id else None
    timeout = args.timeout if hasattr(args, 'timeout') and args.timeout else 120
    
    # Get parameters interactively (skip in non-interactive mode)
    if not resource_id:
        if non_interactive:
            print("Error: Missing required parameter --resource-id")
            return
        resource_id = prompt_for_input("L Instance resource ID", required=True)
    
    if not region_id:
        if non_interactive:
            region_id = "cn-north-4"
        else:
            region_id = prompt_for_input("Region ID", required=False, default="cn-north-4", choices=REGION_IDS)
    
    if not timeout:
        timeout = 120
    
    print(f"\nConfiguration:")
    print(f"  Resource ID: {resource_id}")
    print(f"  Region: {region_id}")
    print(f"  Timeout: {timeout} seconds")
    
    if not non_interactive:
        confirm = prompt_for_input("Confirm gateway restart?", required=False, default="y", choices=["y", "n"])
        if confirm.lower() != "y":
            print("\nOperation cancelled")
            return
    
    print("\nStarting Hermes gateway restart...")
    result = restart_gateway_remote(resource_id, region_id, timeout, ak=ak, sk=sk, security_token=security_token, coc_region=region_id)
    
    if result.get("ok"):
        print(f"\n✓ {result['text']}")
        if result.get("result"):
            print(f"  Execution ID: {result['result'].get('execute_uuid', 'Unknown')}")
            print(f"  Status: {result['result'].get('status', 'Unknown')}")
            if result['result'].get('output'):
                print(f"\n  Execution Output:")
                print(f"  {result['result']['output']}")
            if result['result'].get('error'):
                print(f"\n  Error Message:")
                print(f"  {result['result']['error']}")
    else:
        print(f"\n✗ Restart failed")
        if result.get("error"):
            print(f"  Error Code: {result['error'].get('code')}")
            print(f"  Error Message: {result['error'].get('message')}")
        if result.get("result") and result['result'].get('output'):
            print(f"\n  Execution Output:")
            print(f"  {result['result']['output']}")