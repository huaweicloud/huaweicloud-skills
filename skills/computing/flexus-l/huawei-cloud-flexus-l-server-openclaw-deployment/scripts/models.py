#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click OpenClaw Deployment - Model Installation Module
"""
import json
import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.lib import install_maas_models_remote, install_maas_models_local, query_uniagent_status, check_gateway_status_remote
from scripts.utils import prompt_for_input, REGION_IDS


def _check_prerequisites(resource_id, region_id, ak, sk, security_token):
    """
    Check prerequisites (UniAgent status)
    
    Args:
        resource_id: L instance resource ID
        region_id: Region ID
        ak: Huawei Cloud AK (supports both long-term and temporary AK)
        sk: Huawei Cloud SK (supports both long-term and temporary SK)
        security_token: Security token for temporary credentials (optional, only required for temporary AK/SK)
    
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

def do_install_maas(args):
    """
    Execute model installation
    
    Args:
        args: Command line argument object with the following attributes:
            - resource_id: L instance resource ID (command line arg --resource-id)
            - region_id: Region ID (command line arg --region-id)
            - model_params: Model parameters JSON (command line arg --model-params), must use valid JSON format with double quotes for keys and values
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
    print("        OpenClaw Model Installation")
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
    model_params = args.model_params if hasattr(args, 'model_params') and args.model_params else ""
    timeout = args.timeout if hasattr(args, 'timeout') and args.timeout else 600
    non_interactive = args.non_interactive if hasattr(args, 'non_interactive') else False
    
    if not resource_id:
        resource_id = prompt_for_input("L instance resource ID", required=True)
    
    if not region_id:
        region_id = prompt_for_input("Region ID", required=False, default="cn-north-4", choices=REGION_IDS)
    
    if not model_params:
        print("\nModel parameters format example:")
        print('  {"provider":"huawei","api_key":"your_api_key","model_ids":["model1","model2"]}')
        model_params = prompt_for_input("Model parameters JSON (optional, press Enter to skip)", required=False)
    
    def normalize_json_string(input_str):
        """
        Convert non-standard JSON string (no quotes/single quotes) to standard double-quoted JSON format
        
        Args:
            input_str: Input JSON string, can be non-standard format without quotes
        
        Returns:
            str: Standard JSON string with double quotes
        
        Examples:
            Input: {provider:huawei,api_key:your_maas_api_key,model_ids:[deepseek-v3.2]}
            Output: {"provider":"huawei","api_key":"your_maas_api_key","model_ids":["deepseek-v3.2"]}
        """
        if not input_str or input_str.strip() == "":
            return ""
        
        raw_str = input_str.strip()
        
        try:
            parsed = json.loads(raw_str)
            return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            processed = re.sub(r'([{,])\s*([a-zA-Z0-9_]+)\s*:', r'\1"\2":', raw_str)
            processed = re.sub(r':\s*([a-zA-Z0-9_\-\.]+)\s*([,}\]])', r':"\1"\2', processed)
            processed = re.sub(r'\[\s*([a-zA-Z0-9_\-\.]+)\s*\]', r'["\1"]', processed)
            
            try:
                parsed = json.loads(processed)
                return json.dumps(parsed, ensure_ascii=False)
            except json.JSONDecodeError as e:
                print(f"\n[WARNING] Model parameters JSON format cannot be auto-fixed: {e}")
                print(f"  Original parameters: {input_str}")
                print(f"  Attempted fix: {processed}")
                raise SystemExit("Please provide valid JSON format parameters (keys and values must be wrapped in double quotes)")
    
    if model_params:
        model_params = normalize_json_string(model_params)
    
    if not timeout:
        timeout = int(prompt_for_input("Timeout (seconds)", required=False, default="600"))
    
    print(f"\nInstallation configuration:")
    print(f"  Resource ID: {resource_id}")
    print(f"  Region: {region_id}")
    print(f"  Model parameters: {model_params or 'Default'}")
    print(f"  Timeout: {timeout} seconds")
    
    if not non_interactive:
        confirm = prompt_for_input("Confirm installation?", required=False, default="y", choices=["y", "n"])
        if confirm.lower() != "y":
            print("\nInstallation cancelled")
            return
    
    print("\nChecking prerequisites...")
    if not _check_prerequisites(resource_id, region_id, ak, sk, security_token):
        print("\nPrerequisite check failed, please resolve and retry")
        return
    
    print("\nStarting model installation...")
    result = install_maas_models_remote(resource_id, region_id, model_params, timeout, "root", ak, sk, security_token)
    
    if result.get("ok"):
        print(f"\n[OK] {result['text']}")
        if result.get("result"):
            print(f"  Execution ID: {result['result'].get('execute_uuid', 'Unknown')}")
            print(f"  Status: {result['result'].get('status', 'Unknown')}")
            if result['result'].get('output'):
                print(f"  Output: {result['result']['output'][:200]}...")
    else:
        print(f"\n[FAIL] Installation failed")
        if result.get("error"):
            print(f"  Error code: {result['error'].get('code')}")
            print(f"  Error message: {result['error'].get('message')}")