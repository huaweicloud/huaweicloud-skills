#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click FlexusAgent Deployment - Import Dify App Workflow Module
"""

import os
import sys
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.lib import import_app_workflow_remote, query_uniagent_status
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


def _fetch_available_workflows():
    """
    Fetch available workflows from OBS
    
    Returns:
        dict: Workflow list or None on failure
    """
    import time
    
    print("\nFetching available workflows...")
    url = f"https://flexus-config-cn-north-4-product.obs.cn-north-4.myhuaweicloud.com/stable/dify/dify-templates/national/index.json?timestamp={int(time.time())}"
    
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            print(f"  [FAIL] Failed to fetch workflow list: HTTP {resp.status_code}")
            return None
        
        data = resp.json()
        print(f"  [OK] Found {data.get('total', 0)} workflows")
        return data
        
    except Exception as e:
        print(f"  [FAIL] Failed to fetch workflow list: {str(e)}")
        return None


def _display_workflow_list(workflow_data):
    """
    Display workflow list for user selection
    
    Args:
        workflow_data: Workflow data from API
    
    Returns:
        dict: Selected workflow or None
    """
    workflows = workflow_data.get("list", [])
    
    if not workflows:
        print("\nNo workflows available")
        return None
    
    print("\n" + "=" * 60)
    print("Available Dify Workflows")
    print("=" * 60)
    
    for idx, workflow in enumerate(workflows, 1):
        title = workflow.get("title", "Untitled")
        desc = workflow.get("desc", "")
        categories = workflow.get("categoryList", [])
        category_names = [cat.get("category", "") for cat in categories]
        
        print(f"\n{idx}. {title}")
        if desc:
            print(f"   Description: {desc}")
        if category_names:
            print(f"   Categories: {', '.join(category_names)}")
    
    print("\n" + "=" * 60)
    
    while True:
        try:
            choice = input(f"\nSelect workflow (1-{len(workflows)}): ").strip()
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(workflows):
                return workflows[choice_idx]
            else:
                print(f"Invalid choice, please enter a number between 1 and {len(workflows)}")
        except ValueError:
            print("Invalid input, please enter a number")


def do_import_app_workflow(args):
    """Import Dify app workflow to FlexusAgent instance"""
    print("=" * 60)
    print("        Import Dify App Workflow")
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
    flexusagent_email = args.flexusagent_email if hasattr(args, 'flexusagent_email') and args.flexusagent_email else None
    flexusagent_password = args.flexusagent_password if hasattr(args, 'flexusagent_password') and args.flexusagent_password else None
    app_workflow_id = args.app_workflow_id if hasattr(args, 'app_workflow_id') and args.app_workflow_id else None
    timeout = args.timeout if hasattr(args, 'timeout') and args.timeout else 600
    execute_user = "root"
    non_interactive = args.non_interactive if hasattr(args, 'non_interactive') else False
    
    if not resource_id:
        resource_id = prompt_for_input("L Instance Resource ID", required=True)
    
    if not region_id:
        region_id = prompt_for_input("Region ID", required=False, default="cn-north-4", choices=REGION_IDS)
    
    if not flexusagent_email:
        flexusagent_email = prompt_for_input("FlexusAgent Admin Email", required=True)
    
    if not flexusagent_password:
        print("\nFlexusAgent admin password")
        flexusagent_password = prompt_for_input("FlexusAgent Admin Password", required=True)
    
    if not app_workflow_id:
        workflow_data = _fetch_available_workflows()
        if not workflow_data:
            app_workflow_id = prompt_for_input("Workflow ID (e.g., Bid_Writing_And_Templated_Adaptation)", required=True)
        else:
            selected_workflow = _display_workflow_list(workflow_data)
            if selected_workflow:
                app_workflow_id = selected_workflow.get("id")
                print(f"\n[OK] Selected workflow: {selected_workflow.get('title')} (ID: {app_workflow_id})")
            else:
                app_workflow_id = prompt_for_input("Workflow ID", required=True)
    
    if not timeout:
        timeout = int(prompt_for_input("Timeout (seconds)", required=False, default="600"))
    
    print("\n" + "-" * 40)
    print("Import Configuration:")
    print(f"  Resource ID: {resource_id}")
    print(f"  Region: {region_id}")
    print(f"  Admin Email: {flexusagent_email}")
    print(f"  Admin Password: {'*' * len(flexusagent_password)}")
    print(f"  Workflow ID: {app_workflow_id}")
    print(f"  Timeout: {timeout} seconds")
    print("-" * 40)
    
    if not non_interactive:
        confirm = prompt_for_input("Confirm import?", required=False, default="y", choices=["y", "n"])
        if confirm.lower() != "y":
            print("\nImport cancelled")
            return
    
    print("\nChecking prerequisites...")
    if not _check_prerequisites(resource_id, region_id, ak, sk, security_token):
        print("\nPrerequisite check failed, please resolve and try again")
        return
    
    print("\nImporting Dify app workflow...")
    result = import_app_workflow_remote(
        resource_id, region_id, flexusagent_email, flexusagent_password,
        app_workflow_id, timeout, execute_user, ak, sk, security_token
    )
    
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
