#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click Hermes Deployment - Deployment Module

Note: This module only supports temporary credentials (temporary AK/SK + security_token).
      Permanent AK/SK credentials are not supported.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.lib import create_hermes_instance
from scripts.utils import print_region_list, prompt_for_input, REGION_IDS, get_region_id_by_name, REGIONS


def do_deploy_hermes(args):
    """Execute Hermes instance deployment"""
    print("=" * 60)
    print("        Hermes Instance One-Click Deployment")
    print("=" * 60)
    
    non_interactive = getattr(args, 'non_interactive', False)
    
    # Get credentials (from command line parameters)
    ak = args.ak if hasattr(args, 'ak') and args.ak else None
    sk = args.sk if hasattr(args, 'sk') and args.sk else None
    security_token = args.security_token if hasattr(args, 'security_token') and args.security_token else None
    
    # Get parameters
    instance_name = getattr(args, 'name', None)
    region = getattr(args, 'region', None)

    # If instance_name not provided via CLI, prompt interactively (skip in non-interactive mode)
    # Note: If still None after this block, lib.py will auto-generate timestamp format (hermes-YYYYMMDDHHMMSS)
    if not instance_name and not non_interactive:
        instance_name = prompt_for_input("Instance name (optional, press Enter for auto-generate)", required=False)

    if not region:
        if non_interactive:
            region = "cn-north-4"
        else:
            print_region_list()
            print("Tip: You can enter region ID (e.g. cn-southwest-2) or Chinese name (e.g. Southwest-Guiyang)")
            user_input = prompt_for_input("Target region", required=False, default="cn-north-4")
            # Convert user input to standard region ID (supports Chinese names)
            region = get_region_id_by_name(user_input)
            
            # Validate region
            while region not in REGION_IDS:
                print(f"Error: '{region}' is not a valid region.")
                print_region_list()
                user_input = prompt_for_input("Please re-enter target region", required=False, default="cn-north-4")
                region = get_region_id_by_name(user_input)
    
    # Get region display name
    region_name = REGIONS.get(region, region)
    
    print(f"\nDeployment Configuration:")
    print(f"  Instance Name: {instance_name or 'Auto-generated'}")
    print(f"  Target Region: {region} ({region_name})")
    
    # Confirm deployment (skip in non-interactive mode)
    non_interactive = getattr(args, 'non_interactive', False)
    if not non_interactive:
        confirm = prompt_for_input("Confirm deployment?", required=False, default="y", choices=["y", "n"])
        if confirm.lower() != "y":
            print("\nDeployment cancelled")
            return
    else:
        print("  Non-interactive mode: Auto-confirm")
    
    # Execute deployment
    print("\nStarting Hermes instance creation...")
    result = create_hermes_instance(ak, sk, security_token, instance_name, region)
    
    if result.get("ok"):
        print(f"\n✓ {result['text']}")
        if result.get("result"):
            print(f"  Order ID: {result['result'].get('order_id', 'Unknown')}")
            print(f"  Instance ID: {result['result'].get('instance_ids', ['Unknown'])[0]}")
        print("\nDeployment completed!")
        print("Tip: Instance creation may take several minutes, please wait patiently.")
    else:
        print(f"\n✗ Deployment failed")
        if result.get("error"):
            print(f"  Error Code: {result['error'].get('code')}")
            print(f"  Error Message: {result['error'].get('message')}")