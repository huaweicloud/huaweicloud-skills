#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click FlexusAgent Deployment - Deployment Module
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.lib import create_flexusagent_instance
from scripts.utils import print_region_list, prompt_for_input, REGION_IDS, get_region_id_by_name, REGIONS
from scripts.sg_rule import do_set_security_group_rule


def do_deploy_flexusagent(args):
    """
    Deploy FlexusAgent instance
    
    Parameters:
        args: Command line argument object with the following attributes:
            - name: Instance name (--name)
            - region: Region ID (--region) - required
            - spec: Instance spec (--spec) - required, must be one of: hf.xlarge.1.linux, ahf.xlarge.1.linux, hf.xlarge.3.linux, ahf.xlarge.3.linux
            - ak: Huawei Cloud AK (--ak)
            - sk: Huawei Cloud SK (--sk)
            - security_token: Security token for temporary credentials (--security-token)
            - non_interactive: Non-interactive mode flag (--non-interactive)
    
    Returns:
        None
    """
    print("=" * 60)
    print("        FlexusAgent One-Click Deployment")
    print("=" * 60)
    
    # Get credentials (from args first, then from environment variables)
    ak = getattr(args, 'ak', None) or os.environ.get('HW_ACCESS_KEY')
    sk = getattr(args, 'sk', None) or os.environ.get('HW_SECRET_KEY')
    security_token = getattr(args, 'security_token', None) or os.environ.get('HW_SECURITY_TOKEN', None)
    
    if not ak or not sk:
        print("\nHuawei Cloud credentials not configured, entering interactive configuration...")
        print("Please configure Huawei Cloud credentials:")
        print("-" * 40)
        raise ValueError("Huawei Cloud credentials not configured.")
    
    # Get parameters
    instance_name = args.name if hasattr(args, 'name') and args.name else None
    region = args.region if hasattr(args, 'region') and args.region else None
    spec = args.spec if hasattr(args, 'spec') and args.spec else None

    # If parameters not provided via command line, get interactively
    if not instance_name:
        instance_name = prompt_for_input("Instance name (optional, auto-generated if empty)", required=False)

    # Region is required - must be provided by user
    if not region:
        print_region_list()
        print("Tip: You can enter region ID (e.g. cn-southwest-2) or region name")
        user_input = prompt_for_input("Target region", required=True)
        # Convert user input to standard region ID
        region = get_region_id_by_name(user_input)

        # Validate region
        while region not in REGION_IDS:
            print(f"Error: '{region}' is not a valid region.")
            print_region_list()
            user_input = prompt_for_input("Please re-enter target region", required=True)
            region = get_region_id_by_name(user_input)

    # Get region name for display
    region_name = REGIONS.get(region, region)

    # Get available specs based on region and let user choose
    if region == "cn-southwest-2":
        available_specs = ["ahf.xlarge.1.linux", "ahf.xlarge.3.linux"]
    else:
        available_specs = ["hf.xlarge.1.linux", "hf.xlarge.3.linux"]

    # If spec not provided via command line, prompt user to choose
    if not spec:
        print(f"\nAvailable instance specs for region {region} ({region_name}):")
        for i, s in enumerate(available_specs, 1):
            print(f"  {i}. {s}")
        print(f"Tip: You must select one of the above specs")
        user_input = prompt_for_input("Select instance spec", required=True)
        # Validate spec
        while user_input not in available_specs:
            print(f"Error: '{user_input}' is not a valid spec for this region.")
            print(f"Available specs: {', '.join(available_specs)}")
            user_input = prompt_for_input("Please re-enter spec", required=True)
        spec = user_input

    print(f"\nDeployment Configuration:")
    print(f"  Instance Name: {instance_name or 'Auto-generated'}")
    print(f"  Target Region: {region} ({region_name})")
    print(f"  Instance Spec: {spec}")

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
    print("\nCreating FlexusAgent instance...")
    result = create_flexusagent_instance(instance_name, region, ak, sk, security_token, spec)

    if result.get("ok"):
        print(f"\n✓ {result['text']}")
        if result.get("result"):
            instance_ids = result['result'].get('instance_ids', [])
            instance_id = instance_ids[0] if instance_ids else 'Unknown'
            order_id = result['result'].get('order_id', 'Unknown')
            print(f"  Instance ID: {instance_id}")
        
        # Prompt user to view instance information
        print("\n" + "=" * 60)
        print("✅ Instance created successfully!")
        print("=" * 60)
        print(f"  Instance ID: {instance_id}")
        print(f"  Region:      {region}")
        print("=" * 60)
        print("\n📌 Instance is initializing (estimated 2 minutes), please check via:")
        print("  1. Huawei Cloud Console: https://console.huaweicloud.com/smb/?/resource/list")


        
        # Set security group rules
        try:
            do_set_security_group_rule(ak, sk, region, security_token)
        except Exception as e:
            print(f"\n[ERROR] {e}")
    else:
        print(f"\n[FAIL] Deployment failed")
        if result.get("error"):
            print(f"  Error Code: {result['error'].get('code')}")
            print(f"  Error Message: {result['error'].get('message')}")
