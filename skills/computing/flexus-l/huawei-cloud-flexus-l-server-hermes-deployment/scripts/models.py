#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click Hermes Deployment - Model Installation Module
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.lib import install_maas_models_remote, DEFAULT_BASE_URL
from scripts.utils import prompt_for_input, REGION_IDS


def do_install_maas(args):
    """Execute ModelArts large model configuration"""
    print("=" * 60)
    print("        Hermes ModelArts Large Model Configuration")
    print("=" * 60)
    
    non_interactive = args.non_interactive if hasattr(args, 'non_interactive') else False
    
    # Get credentials (from command line parameters)
    ak = args.ak if hasattr(args, 'ak') and args.ak else None
    sk = args.sk if hasattr(args, 'sk') and args.sk else None
    security_token = args.security_token if hasattr(args, 'security_token') and args.security_token else None
    
    # Get parameters
    resource_id = args.resource_id if hasattr(args, 'resource_id') and args.resource_id else None
    region_id = args.region_id if hasattr(args, 'region_id') and args.region_id else None
    api_key = args.api_key if hasattr(args, 'api_key') and args.api_key else ""
    model_name = args.model_name if hasattr(args, 'model_name') and args.model_name else ""
    api_base_url = args.api_base_url if hasattr(args, 'api_base_url') and args.api_base_url else DEFAULT_BASE_URL
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
    
    if not api_key:
        if non_interactive:
            print("Error: Missing required parameter --api-key")
            return
        api_key = prompt_for_input("ModelArts API Key", required=True)
    
    if not model_name:
        if non_interactive:
            print("Error: Missing required parameter --model-name")
            return
        print("\nAvailable model examples:")
        print("  deepseek-v3.2, qwen-plus, glm-4")
        model_name = prompt_for_input("Large model name", required=True)
    
    if not api_base_url:
        api_base_url = DEFAULT_BASE_URL
    
    if not timeout:
        timeout = 600
    
    print(f"\nConfiguration:")
    print(f"  Resource ID: {resource_id}")
    print(f"  Region: {region_id}")
    print(f"  API Key: {api_key[:8]}****")
    print(f"  Model Name: {model_name}")
    print(f"  API Base URL: {api_base_url}")
    print(f"  Timeout: {timeout} seconds")
    
    if not non_interactive:
        confirm = prompt_for_input("Confirm configuration?", required=False, default="y", choices=["y", "n"])
        if confirm.lower() != "y":
            print("\nConfiguration cancelled")
            return
    
    print("\nStarting ModelArts large model configuration...")
    result = install_maas_models_remote(resource_id, region_id, api_key, model_name, api_base_url, timeout, ak=ak, sk=sk, security_token=security_token, coc_region=region_id)
    
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
        print(f"\n✗ Configuration failed")
        if result.get("error"):
            print(f"  Error Code: {result['error'].get('code')}")
            print(f"  Error Message: {result['error'].get('message')}")
        if result.get("result") and result['result'].get('output'):
            print(f"\n  Execution Output:")
            print(f"  {result['result']['output']}")