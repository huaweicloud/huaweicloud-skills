#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click OpenClaw Deployment - Deployment Module
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.lib import create_openclaw_instance
from scripts.utils import print_region_list, prompt_for_input, REGION_IDS, get_region_id_by_name, REGIONS


def do_deploy_openclaw(args):
    """
    Execute OpenClaw instance deployment
    
    Args:
        args: Command line argument object with the following attributes:
            - name: Instance name (command line arg --name)
            - region: Region ID (command line arg --region)
            - ak: Huawei Cloud temporary AK (command line arg --ak)
            - sk: Huawei Cloud temporary SK (command line arg --sk)
            - security_token: Security token for temporary credentials (required) (command line arg --security-token)
            - non_interactive: Whether non-interactive mode (command line arg --non-interactive)
    
    Returns:
        None
    """
    print("=" * 60)
    print("        OpenClaw Instance One-Click Deployment")
    print("=" * 60)
    
    ak = getattr(args, 'ak', None)
    sk = getattr(args, 'sk', None)
    security_token = getattr(args, 'security_token', None)

    if not ak or not sk:
        print("\nHuawei Cloud temporary credentials not configured, entering interactive configuration...")
        print("Please configure Huawei Cloud temporary credentials:")
        print("-" * 40)
        ak = prompt_for_input("Huawei Cloud temporary AK:HW_ACCESS_KEY", required=True)
        sk = prompt_for_input("Huawei Cloud temporary SK:HW_SECRET_KEY", required=True, hide_input=True)
        security_token = prompt_for_input("Huawei Cloud Security Token (required for temporary credentials)", required=True)
    
    instance_name = args.name if hasattr(args, 'name') and args.name else None
    region = args.region if hasattr(args, 'region') and args.region else None
    
    if not instance_name:
        instance_name = prompt_for_input("Instance name (optional, press Enter to auto-generate)", required=False)
    
    if not region:
        print_region_list()
        print("Tip: You can enter region ID (e.g. cn-southwest-2) or Chinese name (e.g. 西南-贵阳一)")
        user_input = prompt_for_input("Target region", required=False, default="cn-north-4")
        region = get_region_id_by_name(user_input)
        
        while region not in REGION_IDS:
            print(f"Error: '{region}' is not a valid region.")
            print_region_list()
            user_input = prompt_for_input("Please re-enter target region", required=False, default="cn-north-4")
            region = get_region_id_by_name(user_input)
    
    region_name = REGIONS.get(region, region)
    
    print(f"\nDeployment configuration:")
    print(f"  Instance name: {instance_name or 'Auto-generated'}")
    print(f"  Target region: {region} ({region_name})")
    
    non_interactive = getattr(args, 'non_interactive', False)
    if not non_interactive:
        confirm = prompt_for_input("Confirm deployment?", required=False, default="y", choices=["y", "n"])
        if confirm.lower() != "y":
            print("\nDeployment cancelled")
            return
    else:
        print("  Non-interactive mode: Auto-confirming")
    
    print("\nStarting to create OpenClaw instance...")
    result = create_openclaw_instance(instance_name, region, ak, sk,security_token)
    
    if result.get("ok"):
        print(f"\n[OK] {result['text']}")
        if result.get("result"):
            print(f"  Order ID: {result['result'].get('order_id', 'Unknown')}")
            print(f"  Instance ID: {result['result'].get('instance_ids', ['Unknown'])[0]}")
        print("\nDeployment completed!")
        print("Tip: Instance creation takes a few minutes, please wait patiently.")
    else:
        print(f"\n[FAIL] Deployment failed")
        if result.get("error"):
            print(f"  Error code: {result['error'].get('code')}")
            print(f"  Error message: {result['error'].get('message')}")
