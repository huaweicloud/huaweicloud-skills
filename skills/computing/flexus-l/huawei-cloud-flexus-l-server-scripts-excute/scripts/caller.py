#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud COC Script Management CLI Tool

Manages COC scripts using Huawei Cloud SDK, supporting script creation and execution.

Parameters:
    --ak: Huawei Cloud Access Key (required)
    --sk: Huawei Cloud Secret Key (required)
    --region: Region (default: cn-north-4)

Commands:
    create  - Create custom script (standalone flow)
    execute - Execute script (standalone flow)
    show    - View script details
    list    - List scripts

Each command has its own interactive flow
"""

import argparse
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.lib import create_script, execute_script, get_script_detail, list_scripts, get_script_job_batch

# Huawei Cloud global region mapping (for target instance region selection)
REGIONS = {
    # China mainland regions
    "cn-north-4": "North China - Beijing 4",
    "cn-north-9": "North China - Ulanqab 1",
    "cn-east-3": "East China - Shanghai 1",
    "cn-south-1": "South China - Guangzhou",
    "cn-south-4": "South China - Guangzhou (Friendly User Env)",
    "cn-southwest-2": "Southwest China - Guiyang 1",
    "cn-east-5": "East China - Qingdao",
    "cn-east-4": "East China 2",
    "cn-north-11": "North China - Ulanqab 201",
    "cn-north-12": "North China - Ulanqab 202",
    # International regions
    "ap-southeast-1": "Hong Kong, China",
    "ap-southeast-2": "Asia Pacific - Bangkok",
    "ap-southeast-3": "Asia Pacific - Singapore",
    "ap-southeast-4": "Asia Pacific - Jakarta",
    "ap-southeast-5": "Asia Pacific - Manila",
    "af-south-1": "Africa - Johannesburg",
    "af-north-1": "Africa - Cairo",
    "la-north-2": "Latin America - Mexico City 2",
    "sa-brazil-1": "Latin America - Sao Paulo 1",
    "la-south-2": "Latin America - Santiago",
    "tr-west-1": "Turkey - Istanbul",
    "me-east-1": "Middle East - Riyadh",
}

# Get all region IDs (for target instance regions)
REGION_IDS = list(REGIONS.keys())

# Dynamically get COC service supported regions from SDK
def get_coc_service_regions():
    """
    Dynamically get COC service supported regions and their name mapping from SDK.
    
    Returns:
        dict, key is region ID, value is region name
    """
    from huaweicloudsdkcoc.v1.region.coc_region import CocRegion
    
    # Region ID to name mapping
    region_name_map = {
        "cn-north-4": "North China - Beijing 4 (default)",
        "ap-southeast-3": "Asia Pacific - Singapore",
        "eu-west-101": "Europe - Frankfurt",
    }
    
    # Dynamically get regions defined in SDK
    sdk_regions = CocRegion.static_fields.keys()
    
    # Return dict containing only SDK supported regions
    return {region: region_name_map.get(region, region) for region in sdk_regions}


# Get COC service region IDs list
def get_coc_service_region_ids():
    """Get list of region IDs supported by COC service"""
    return list(get_coc_service_regions().keys())


def print_region_list():
    """
    Print Huawei Cloud global region list (for target instance region selection)
    """
    print("\nHuawei Cloud Global Regions (Target Instance Regions):")
    print("-" * 55)
    print(f"{'Region ID':<20} {'Region Name':<25}")
    print("-" * 55)
    
    # Print China mainland regions
    print("\n[China Mainland Regions]")
    for region_id, name in REGIONS.items():
        if region_id.startswith("cn-"):
            print(f"{region_id:<20} {name:<25}")
    
    # Print international regions
    print("\n[International Regions]")
    for region_id, name in REGIONS.items():
        if not region_id.startswith("cn-"):
            print(f"{region_id:<20} {name:<25}")
    print("-" * 55)


def print_coc_service_region_list():
    """
    Print COC service supported regions (dynamically fetched from SDK)
    """
    coc_regions = get_coc_service_regions()
    print("\nCOC Service Supported Regions:")
    print("-" * 40)
    print(f"{'Region ID':<20} {'Region Name':<20}")
    print("-" * 40)
    for region_id, name in coc_regions.items():
        print(f"{region_id:<20} {name:<20}")
    print("-" * 40)


def prompt_for_region(prompt, required=False, default="cn-north-4", is_coc_service=False):
    """
    Interactive prompt for user to select region, displays region list
    
    Args:
        prompt: Prompt message
        required: Whether it's required
        default: Default value
        is_coc_service: Whether it's COC service region selection (dynamically fetched from SDK)
    """
    if is_coc_service:
        regions = get_coc_service_regions()
        region_ids = get_coc_service_region_ids()
        print_func = print_coc_service_region_list
    else:
        regions = REGIONS
        region_ids = REGION_IDS
        print_func = print_region_list
    
    while True:
        # Display region list
        print_func()
        
        if default:
            display_prompt = f"\n{prompt} (default: {default} [{regions.get(default, '')}]) (enter 'list' to view list): "
        else:
            display_prompt = f"\n{prompt} (enter 'list' to view list): "
        
        user_input = input(display_prompt).strip()
        
        if user_input.lower() == 'list':
            continue
        
        if user_input:
            # Check if valid region ID
            if user_input in region_ids:
                return user_input
            # Try to find by name
            for region_id, name in regions.items():
                if user_input == name:
                    return region_id
            print(f"\nError: '{user_input}' is not a valid region ID or name. Please enter a valid region.")
            continue
        elif default:
            return default
        elif not required:
            return None
        else:
            print("Error: This parameter is required")


def prompt_for_input(prompt, required=True, default=None, choices=None, hide_input=False):
    """
    Interactive prompt for user input.
    """
    while True:
        if default:
            display_prompt = f"{prompt} (default: {default}): "
        elif choices:
            display_prompt = f"{prompt} ({'/'.join(choices)}): "
        else:
            display_prompt = f"{prompt}: "

        if hide_input:
            try:
                from getpass import getpass
                user_input = getpass(display_prompt).strip()
            except ImportError:
                user_input = input(display_prompt).strip()
        else:
            user_input = input(display_prompt).strip()

        if user_input:
            if choices and user_input not in choices:
                print(f"Error: Please select one of the following options: {', '.join(choices)}")
                continue
            return user_input
        elif default:
            return default
        elif not required:
            return None
        else:
            print("Error: This parameter is required")


def setup_credentials_interactive():
    """
    Interactively set up AK/SK credentials (called only when needed)
    
    Returns:
        tuple: (ak, sk, region)
    """
    print("\nPlease configure Huawei Cloud credentials:")
    print("-" * 40)
    
    ak = prompt_for_input("Huawei Cloud AK", required=True)
    sk = prompt_for_input("Huawei Cloud SK", required=True, hide_input=True)
    region = prompt_for_region("Enter COC service region ID", required=False, default="cn-north-4", is_coc_service=True)
    
    print(f"\n✓ Credentials configured successfully")
    print(f"  AK: {ak[:4]}...{ak[-4:]}")
    print(f"  SK: {'*' * len(sk)}")
    print(f"  Region: {region} ({get_coc_service_regions().get(region, REGIONS.get(region, ''))})")
    
    return ak, sk, region


def do_create_script(args):
    """
    Standalone flow for creating a script
    """
    print("=" * 60)
    print("Create Custom Script")
    print("=" * 60)
    
    # Get credential parameters
    ak = args.ak
    sk = args.sk
    region = args.region or "cn-north-4"
    
    # If credentials not provided, prompt interactively
    if not ak or not sk:
        print("\nPlease provide Huawei Cloud credentials:")
        ak, sk, region = setup_credentials_interactive()
    
    print("\nPlease provide script information:")
    
    # Get parameters for script creation
    name = args.name or prompt_for_input("Script name", required=True)
    script_type = args.type or prompt_for_input(
        "Script type", required=True, choices=['SHELL', 'PYTHON', 'BAT']
    )
    content = args.content or prompt_for_input("Script content", required=True)
    description = args.description or prompt_for_input("Script description", required=True)
    risk_level = args.risk_level or prompt_for_input(
        "Risk level", required=False, default='LOW', choices=['LOW', 'MEDIUM', 'HIGH']
    )
    version = args.version or prompt_for_input("Script version", required=False, default='1.0.0')
    
    print("\n" + "=" * 60)
    print("Creating script...")
    
    try:
        result = create_script(
            name=name,
            script_type=script_type,
            content=content,
            description=description,
            ak=ak,
            sk=sk,
            region=region,
            risk_level=risk_level,
            version=version
        )
        
        if result.get("ok"):
            print("\n✓ Script created successfully!")
            print(f"  {result['text']}")
            print("\nNote: This skill only supports script execution on L instances. When executing, only provide the L instance resource ID (resource_id).")
        else:
            print(f"\n✗ Creation failed: {result.get('error', {}).get('message')}")
            print("\nNote: Please check if the script content format is correct, or contact administrator for assistance.")
                
    except Exception as e:
        print(f"\n✗ Error occurred: {str(e)}")
        print("\nNote: Please check if the script content format is correct, or contact administrator for assistance.")


def do_execute_script(args):
    """
    Standalone flow for executing a script
    
    Required parameters:
    - resource_id: Resource ID of target L instance
    - region_id: Region where the target L instance is located
    
    Optional parameters:
    - script_uuid: Script UUID (uses most recently created script by default)
    - execute_user: Execution user (default: root)
    - timeout: Timeout in seconds (default: 300)
    - success_rate: Success rate threshold (default: 1)
    - rotation_strategy: Rotation strategy (default: CONTINUE)
    """
    print("=" * 60)
    print("Execute Script")
    print("=" * 60)
    
    # Get credential parameters
    ak = args.ak
    sk = args.sk
    region = args.region or "cn-north-4"
    
    # If credentials not provided, prompt interactively
    if not ak or not sk:
        print("\nPlease provide Huawei Cloud credentials:")
        ak, sk, region = setup_credentials_interactive()
    
    # Get target instance information (L instance only, required)
    print("\nPlease provide target L instance information (required):")
    
    resource_id = prompt_for_input("L instance resource ID (resource_id)", required=True)
    region_id = prompt_for_region("L instance region (region_id)", required=True)
    
    # Get execution parameters (optional, press Enter for defaults)
    print("\nPlease provide execution information (optional, press Enter for defaults):")
    
    script_uuid = args.script_uuid or prompt_for_input("Script UUID", required=False, default='')
    execute_user = args.execute_user or prompt_for_input("Execution user", required=False, default='root')
    
    # If script UUID is empty, try to get the most recently created script
    if not script_uuid:
        print("\nGetting most recently created script...")
        try:
            list_result = list_scripts(ak, sk, region, limit=1)
            if list_result.get("ok") and list_result.get("result"):
                scripts = list_result.get("result", {}).get("scripts", [])
                if scripts:
                    script_uuid = scripts[0].get("script_uuid", "")
                    script_name = scripts[0].get("name", "")
                    print(f"  Using most recently created script: {script_name} ({script_uuid})")
        except Exception as e:
            print(f"  Failed to get script list: {str(e)}")
    
    # If still no script UUID, prompt user
    if not script_uuid:
        script_uuid = prompt_for_input("Script UUID", required=True)
    timeout = args.timeout if args.timeout else int(prompt_for_input(
        "Timeout (seconds, 5-1800)", required=False, default='300'
    ))
    success_rate = args.success_rate if args.success_rate else float(prompt_for_input(
        "Success rate (supports one decimal place, e.g., 1 or 100)", required=False, default='1'
    ))
    
    target_instances = [{
        "resource_id": resource_id,
        "region_id": region_id,
        "provider": "HCSS",
        "type": "L-INSTANCE"
    }]
    
    rotation_strategy = args.rotation_strategy or prompt_for_input(
        "Rotation strategy", required=False, default='CONTINUE', choices=['CONTINUE', 'PAUSE']
    )
    
    print("\n" + "=" * 60)
    print("Executing script...")
    
    try:
        result = execute_script(
            script_uuid=script_uuid,
            execute_user=execute_user,
            timeout=timeout,
            success_rate=success_rate,
            target_instances=target_instances,
            ak=ak,
            sk=sk,
            region=region,
            rotation_strategy=rotation_strategy
        )
        
        if result.get("ok"):
            print("\n✓ Script executed successfully!")
            print(f"  {result['text']}")
        else:
            print(f"\n✗ Execution failed: {result.get('error', {}).get('message')}")
            print("\nNote: This skill only supports script execution on L instances. Please verify the L instance server ID and region before running.")
                
    except Exception as e:
        print(f"\n✗ Error occurred: {str(e)}")
        print("\nNote: This skill only supports script execution on L instances. Please verify the L instance server ID and region before running.")


def do_show_script(args):
    """
    Standalone flow for viewing script details
    """
    print("=" * 60)
    print("View Script Details")
    print("=" * 60)
    
    # Get credential parameters
    ak = args.ak
    sk = args.sk
    region = args.region or "cn-north-4"
    
    # If credentials not provided, prompt interactively
    if not ak or not sk:
        print("\nPlease provide Huawei Cloud credentials:")
        ak, sk, region = setup_credentials_interactive()
    
    print("\nPlease provide script information:")
    
    script_uuid = args.script_uuid or prompt_for_input("Script UUID", required=True)
    
    print("\n" + "=" * 60)
    print("Getting script details...")
    
    try:
        result = get_script_detail(script_uuid, ak, sk, region)
        
        if result.get("ok"):
            print("\n✓ Script details retrieved successfully!")
            script_data = result.get("result", {})
            print("\nScript Details:")
            print("-" * 40)
            print(f"Script UUID: {script_data.get('script_uuid', '')}")
            print(f"Script Name: {script_data.get('name', '')}")
            print(f"Script Type: {script_data.get('type', '')}")
            print(f"Risk Level: {script_data.get('risk_level', '')}")
            print(f"Version: {script_data.get('version', '')}")
            print(f"Description: {script_data.get('description', '')}")
            print(f"Created Time: {script_data.get('create_time', '')}")
            print("\nScript Content:")
            print("-" * 40)
            print(script_data.get('content', ''))
            print("-" * 40)
        else:
            print(f"\n✗ Failed to retrieve: {result.get('error', {}).get('message')}")
                
    except Exception as e:
        print(f"\n✗ Error occurred: {str(e)}")


def do_list_scripts(args):
    """
    Standalone flow for listing scripts
    """
    print("=" * 60)
    print("List Scripts")
    print("=" * 60)
    
    # Get credential parameters
    ak = args.ak
    sk = args.sk
    region = args.region or "cn-north-4"
    
    # If credentials not provided, prompt interactively
    if not ak or not sk:
        print("\nPlease provide Huawei Cloud credentials:")
        ak, sk, region = setup_credentials_interactive()
    
    page = args.page if args.page else int(prompt_for_input("Page number", required=False, default='1'))
    size = args.size if args.size else int(prompt_for_input("Page size", required=False, default='10'))
    
    print("\n" + "=" * 60)
    print("Getting script list...")
    
    try:
        result = list_scripts(ak, sk, region, page, size)
        
        if result.get("ok"):
            print(f"\n✓ Script list retrieved successfully!")
            data = result.get("result", {})
            scripts = data.get("scripts", [])
            total = data.get("total", 0)
            
            print(f"\nFound {total} scripts (Page {page}, {size} per page):")
            print("-" * 80)
            print(f"{'No.':<6} {'Script UUID':<30} {'Name':<20} {'Type':<10} {'Risk Level':<10}")
            print("-" * 80)
            
            for i, script in enumerate(scripts, start=(page-1)*size+1):
                print(f"{i:<6} {script.get('script_uuid', '')[:20]:<30} {script.get('name', ''):<20} {script.get('type', ''):<10} {script.get('risk_level', ''):<10}")
            
            print("-" * 80)
        else:
            print(f"\n✗ Failed to retrieve: {result.get('error', {}).get('message')}")
                
    except Exception as e:
        print(f"\n✗ Error occurred: {str(e)}")


def do_query_execution(args):
    """
    Standalone flow for querying script execution result
    """
    print("=" * 60)
    print("Query Script Execution Result")
    print("=" * 60)
    
    # Get credential parameters
    ak = args.ak
    sk = args.sk
    region = args.region or "cn-north-4"
    
    # If credentials not provided, prompt interactively
    if not ak or not sk:
        print("\nPlease provide Huawei Cloud credentials:")
        ak, sk, region = setup_credentials_interactive()
    
    print("\nPlease provide execution information:")
    
    execute_uuid = args.execute_uuid or prompt_for_input("Execute UUID (format: SCTxxxxxxxxxxxxxxx)", required=True)
    
    print("\n" + "=" * 60)
    print("Querying execution result...")
    
    try:
        result = get_script_job_batch(execute_uuid, ak, sk)
        
        data = result.get("data", {})
        if data:
            print("\n[OK] Execution result retrieved successfully!")
            
            print("\nExecution Details:")
            print("-" * 40)
            print(f"Execute UUID: {execute_uuid}")
            print(f"Batch Index: {data.get('batch_index', 'N/A')}")
            print(f"Total Instances: {data.get('total_instances', 'N/A')}")
            
            instances = data.get("execute_instances", [])
            if instances:
                print("\nInstance Execution Results:")
                print("-" * 40)
                for inst in instances:
                    status = inst.get("status", "UNKNOWN")
                    print(f"\nStatus: {status}")
                    print(f"Instance ID: {inst.get('id', 'N/A')}")
                    print(f"Command UUID: {inst.get('cmd_uuid', 'N/A')}")
                    print(f"Execution Time: {inst.get('execute_costs', 'N/A')}ms")
                    
                    target = inst.get("target_instance", {})
                    print(f"\nTarget Instance:")
                    print(f"  Resource ID: {target.get('resource_id', 'N/A')}")
                    print(f"  Region: {target.get('region_id', 'N/A')}")
                    print(f"  Provider: {target.get('provider', 'N/A')}")
                    
                    message = inst.get("message", "")
                    if message:
                        print(f"\nScript Output:")
                        print("-" * 40)
                        print(message)
                        print("-" * 40)
            
                # Status summary
                status_summary = ", ".join([inst.get("status", "UNKNOWN") for inst in instances])
                print(f"\nStatus Summary: {status_summary}")
                
                # Check if all instances finished successfully
                all_finished = all(inst.get("status") == "FINISHED" for inst in instances)
                if all_finished:
                    print("\n[OK] All instances executed successfully!")
                else:
                    print("\n[WARNING] Some instances may have failed or are still running.")
            else:
                print("\nNo execution instances found.")
        else:
            print(f"\n[FAIL] Failed to retrieve: {result.get('error', {}).get('message', 'Unknown error')}")
                
    except Exception as e:
        print(f"\n[FAIL] Error occurred: {str(e)}")


def main():
    parser = argparse.ArgumentParser(
        description="Huawei Cloud COC Script Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create script
  python {baseDir}/scripts/caller.py create --ak "your_ak" --sk "your_sk" --name "test_script" --type SHELL --content "echo 'Hello'" --description "test"

  # Execute script
  python {baseDir}/scripts/caller.py execute --ak "your_ak" --sk "your_sk" --script-uuid "SC20231025..." --execute-user root

  # View script details
  python {baseDir}/scripts/caller.py show --ak "your_ak" --sk "your_sk" --script-uuid "SC20231025..."

  # List scripts
  python {baseDir}/scripts/caller.py list --ak "your_ak" --sk "your_sk" --page 1 --size 10

  # Query execution result
  python {baseDir}/scripts/caller.py query --ak "your_ak" --sk "your_sk" --execute-uuid "SCT20231025..."

Configuration:
  Use --ak and --sk parameters to pass Huawei Cloud credentials
  If not provided, will prompt interactively when needed
        """,
    )
    
    # Global parameters (shared by all commands)
    parser.add_argument('--ak', help='Huawei Cloud Access Key')
    parser.add_argument('--sk', help='Huawei Cloud Secret Key')
    parser.add_argument('--region', default='cn-north-4', help='COC service region (default: cn-north-4)')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # create command
    create_parser = subparsers.add_parser('create', help='Create custom script')
    create_parser.add_argument('--name', help='Script name')
    create_parser.add_argument('--type', choices=['SHELL', 'PYTHON', 'BAT'], help='Script type')
    create_parser.add_argument('--content', help='Script content')
    create_parser.add_argument('--description', help='Script description')
    create_parser.add_argument('--risk-level', choices=['LOW', 'MEDIUM', 'HIGH'], help='Risk level')
    create_parser.add_argument('--version', help='Script version')

    # execute command
    execute_parser = subparsers.add_parser('execute', help='Execute script')
    execute_parser.add_argument('--script-uuid', help='Script UUID')
    execute_parser.add_argument('--execute-user', help='Execution user')
    execute_parser.add_argument('--timeout', type=int, help='Timeout in seconds')
    execute_parser.add_argument('--success-rate', type=float, help='Success rate threshold (1-100)')
    execute_parser.add_argument('--rotation-strategy', choices=['CONTINUE', 'PAUSE'], help='Rotation strategy')

    # show command
    show_parser = subparsers.add_parser('show', help='View script details')
    show_parser.add_argument('--script-uuid', help='Script UUID')

    # list command
    list_parser = subparsers.add_parser('list', help='List scripts')
    list_parser.add_argument('--page', type=int, help='Page number')
    list_parser.add_argument('--size', type=int, help='Page size')

    # query command
    query_parser = subparsers.add_parser('query', help='Query script execution result')
    query_parser.add_argument('--execute-uuid', help='Execute UUID')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == 'create':
            do_create_script(args)
        elif args.command == 'execute':
            do_execute_script(args)
        elif args.command == 'show':
            do_show_script(args)
        elif args.command == 'list':
            do_list_scripts(args)
        elif args.command == 'query':
            do_query_execution(args)

    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user")
        sys.exit(0)


if __name__ == '__main__':
    main()