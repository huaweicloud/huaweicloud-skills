#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click OpenClaw Deployment - Channel Installation Module
"""
import json
import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.lib import install_channel_remote, install_channel_local, query_uniagent_status
from scripts.utils import prompt_for_input, REGION_IDS


def _check_prerequisites(resource_id, region_id, ak, sk, security_token):
    """
    Check prerequisites (UniAgent status)
    
    Args:
        resource_id: L instance resource ID
        region_id: Region ID
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials (optional)
    
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


def do_install_channel(args):
    """
    Execute channel installation
    
    Args:
        args: Command line argument object with the following attributes:
            - resource_id: L instance resource ID (command line arg --resource-id)
            - region_id: Region ID (command line arg --region-id)
            - channel_list: Channel configuration JSON (command line arg --channel-list)
            - timeout: Timeout duration (command line arg --timeout)
            - execute_user: Execute user (command line arg --execute-user)
            - ak: Huawei Cloud AK (can be temporary AK) (command line arg --ak)
            - sk: Huawei Cloud SK (can be temporary SK) (command line arg --sk)
            - security_token: Security token for temporary credentials (command line arg --security-token)
            - non_interactive: Whether non-interactive mode (command line arg --non-interactive)
    
    Returns:
        None
    """
    print("=" * 60)
    print("        OpenClaw Channel Installation")
    print("=" * 60)
    
    ak = getattr(args, 'ak', None)
    sk = getattr(args, 'sk', None)
    security_token = getattr(args, 'security_token', None)

    
    if not ak or not sk:
        print("\nHuawei Cloud credentials not configured, entering interactive configuration...")
        print("Please configure Huawei Cloud credentials:")
        print("-" * 40)
        ak = prompt_for_input("Huawei Cloud AK:HW_ACCESS_KEY", required=True)
        sk = prompt_for_input("Huawei Cloud SK:HW_SECRET_KEY", required=True, hide_input=True)
    
    resource_id = args.resource_id if hasattr(args, 'resource_id') and args.resource_id else None
    region_id = args.region_id if hasattr(args, 'region_id') and args.region_id else None
    channel_list = args.channel_list if hasattr(args, 'channel_list') and args.channel_list else ""
    timeout = args.timeout if hasattr(args, 'timeout') and args.timeout else 600
    non_interactive = args.non_interactive if hasattr(args, 'non_interactive') else False
    
    if not resource_id:
        resource_id = prompt_for_input("L instance resource ID", required=True)
    
    if not region_id:
        region_id = prompt_for_input("Region ID", required=False, default="cn-north-4", choices=REGION_IDS)
    
    if not channel_list:
        print("\nChannel list format example:")
        print('  [{"channel":"wecom","id":"xxx","secret":"xxx"}]')
        print("\nChannel JSON object fields:")
        print("  - channel: Channel type (required): 'wecom', 'feishu', 'dingtalk', 'qqbot'")
        print("  - id: Bot ID/APP ID/Client ID (required)")
        print("  - secret: Bot secret/APP secret/Client secret (required)")
        channel_list = prompt_for_input("Channel configuration JSON (optional, press Enter to skip)", required=False)
    
    def normalize_json_string(input_str):
        """
        Automatically convert non-standard JSON (no quotes/single quotes) to standard double-quoted JSON
        
        Args:
            input_str: Input JSON string, can be non-standard format without quotes
        
        Returns:
            str: Standard JSON string with double quotes
        
        Examples:
            Input: [{key:val}, {key:val}]
            Output: [{"key":"val"}, {"key":"val"}]
        """
        if not input_str or input_str.strip() == "":
            return ""
        
        raw_str = input_str.strip()
        
        try:
            # 如果已经是标准JSON，直接格式化返回
            parsed = json.loads(raw_str)
            return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            # 修复非标准JSON：自动添加双引号
            processed = re.sub(r'([{\[,])\s*([a-zA-Z0-9_]+)\s*:', r'\1"\2":', raw_str)
            processed = re.sub(r':\s*([a-zA-Z0-9_\-\.]+)\s*([,}\]])', r':"\1"\2', processed)
            
            # 验证修复后的结果
            try:
                parsed = json.loads(processed)
                return json.dumps(parsed, ensure_ascii=False)
            except json.JSONDecodeError as e:
                print(f"\n[ERROR] Channel list JSON format invalid: {e}")
                print(f"Input: {input_str}")
                raise SystemExit("Please provide valid JSON with DOUBLE quotes.")
    
    if channel_list:
        channel_list = normalize_json_string(channel_list)
    
    if not timeout:
        timeout = int(prompt_for_input("Timeout (seconds)", required=False, default="600"))
    
    print(f"\nInstallation configuration:")
    print(f"  Resource ID: {resource_id}")
    print(f"  Region: {region_id}")
    print(f"  Channel list: {channel_list or 'Default'}")
    print(f"  Timeout: {timeout} seconds")
    
    if not non_interactive:
        confirm = prompt_for_input("Confirm installation?", required=False, default="y", choices=["y", "n"])
        if confirm.lower() != "y":
            print("\nInstallation cancelled")
            return
    
    print("\nChecking prerequisites...")
    if not _check_prerequisites(resource_id, region_id, ak, sk, security_token):
        print("\nPrerequisite check failed. Please resolve issues and retry")
        return
    
    print("\nStarting channel installation...")
    result = install_channel_remote(resource_id, region_id, channel_list, timeout, "root", ak, sk, security_token)
    
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