#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click Hermes Deployment - Channel Installation Module

Note: This module only supports temporary credentials (temporary AK/SK + security_token).
      Permanent AK/SK credentials are not supported.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.lib import install_channel_remote
from scripts.utils import prompt_for_input, REGION_IDS


def do_install_channel(args):
    """Execute bot channel configuration"""
    print("=" * 60)
    print("        Hermes Bot Channel Configuration")
    print("=" * 60)
    
    non_interactive = args.non_interactive if hasattr(args, 'non_interactive') else False
    
    # Get credentials (from command line parameters)
    ak = args.ak if hasattr(args, 'ak') and args.ak else None
    sk = args.sk if hasattr(args, 'sk') and args.sk else None
    security_token = args.security_token if hasattr(args, 'security_token') and args.security_token else None
    
    # Get parameters
    resource_id = args.resource_id if hasattr(args, 'resource_id') and args.resource_id else None
    region_id = args.region_id if hasattr(args, 'region_id') and args.region_id else None
    bot_platform = args.bot_platform if hasattr(args, 'bot_platform') and args.bot_platform else ""
    feishu_app_id = args.feishu_app_id if hasattr(args, 'feishu_app_id') and args.feishu_app_id else ""
    feishu_app_secret = args.feishu_app_secret if hasattr(args, 'feishu_app_secret') and args.feishu_app_secret else ""
    wecom_bot_id = args.wecom_bot_id if hasattr(args, 'wecom_bot_id') and args.wecom_bot_id else ""
    wecom_secret = args.wecom_secret if hasattr(args, 'wecom_secret') and args.wecom_secret else ""
    timeout = args.timeout if hasattr(args, 'timeout') and args.timeout else 600
    
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
    
    if not bot_platform:
        if non_interactive:
            print("Error: Missing required parameter --bot-platform")
            return
        print("\nAvailable platforms:")
        print("  feishu - Feishu")
        print("  wecom - WeCom")
        bot_platform = prompt_for_input("Bot platform", required=True, choices=["feishu", "wecom"])
    
    # Get platform-specific parameters
    if bot_platform == "feishu":
        if not feishu_app_id:
            if non_interactive:
                print("Error: Missing required parameter --feishu-app-id")
                return
            feishu_app_id = prompt_for_input("Feishu App ID", required=True)
        if not feishu_app_secret:
            if non_interactive:
                print("Error: Missing required parameter --feishu-app-secret")
                return
            feishu_app_secret = prompt_for_input("Feishu App Secret", required=True)
    elif bot_platform == "wecom":
        if not wecom_bot_id:
            if non_interactive:
                print("Error: Missing required parameter --wecom-bot-id")
                return
            wecom_bot_id = prompt_for_input("WeCom Bot ID", required=True)
        if not wecom_secret:
            if non_interactive:
                print("Error: Missing required parameter --wecom-secret")
                return
            wecom_secret = prompt_for_input("WeCom Secret", required=True)
    
    if not timeout:
        timeout = 600
    
    print(f"\nConfiguration:")
    print(f"  Resource ID: {resource_id}")
    print(f"  Region: {region_id}")
    print(f"  Target Platform: {bot_platform}")
    if bot_platform == "feishu":
        print(f"  Feishu App ID: {feishu_app_id}")
        print(f"  Feishu App Secret: {feishu_app_secret[:8]}****")
    elif bot_platform == "wecom":
        print(f"  WeCom Bot ID: {wecom_bot_id}")
        print(f"  WeCom Secret: {wecom_secret[:8]}****")
    print(f"  Timeout: {timeout} seconds")
    
    if not non_interactive:
        confirm = prompt_for_input("Confirm configuration?", required=False, default="y", choices=["y", "n"])
        if confirm.lower() != "y":
            print("\nConfiguration cancelled")
            return
    
    print("\nStarting bot channel configuration...")
    result = install_channel_remote(
        resource_id, region_id, bot_platform,
        feishu_app_id, feishu_app_secret,
        wecom_bot_id, wecom_secret,
        timeout, ak=ak, sk=sk, security_token=security_token, coc_region=region_id
    )
    
    if result.get("ok"):
        print(f"\n✓ {result['text']}")
        if result.get("result"):
            print(f"  Execution ID: {result['result'].get('execute_uuid', 'Unknown')}")
            print(f"  Status: {result['result'].get('status', 'Unknown')}")
            if result['result'].get('output'):
                print(f"  Output: {result['result']['output'][:200]}...")
    else:
        print(f"\n✗ Configuration failed")
        if result.get("error"):
            print(f"  Error Code: {result['error'].get('code')}")
            print(f"  Error Message: {result['error'].get('message')}")