#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click FlexusAgent Deployment CLI Tool - Main Entry (Lite Version)
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.utils import REGION_IDS
from scripts.deploy import do_deploy_flexusagent
from scripts.passwd import do_change_flexusagent_admin_password
from scripts.maas import do_install_maas
from scripts.sg_rule import do_set_security_group_rule
from scripts.app_workflow_import import do_import_app_workflow
from scripts.uniagent import do_check_uniagent

CONSOLE_URL = "https://console.huaweicloud.com/smb/?/resource/list"


def show_main_menu():
    """Display main menu for user to select operation type"""
    print("=" * 60)
    print("          FlexusAgent One-Click Deployment Tool (Lite)")
    print("=" * 60)
    print("Please select the operation you want to perform:")
    print("")
    print("  1. Deploy FlexusAgent to Huawei Cloud Flexus L Instance")
    print("  2. Change admin password for existing FlexusAgent instance")
    print("  3. Add models to existing FlexusAgent instance")
    print("  4. View FlexusAgent Web UI access instructions")
    print("  5. Import Dify app workflow to FlexusAgent instance")
    print("  0. Exit")
    print("")
    print("=" * 60)

    while True:
        try:
            choice = input("Please enter your choice (0-5): ")
            choice = int(choice)
            if choice in [0, 1, 2, 3, 4, 5]:
                return choice
            else:
                print("Invalid input. Please enter a number between 0 and 5")
        except ValueError:
            print("Invalid input. Please enter a number")


def show_webui_info():
    """Display Web UI access instructions"""
    print("=" * 60)
    print("          FlexusAgent Web UI Access Instructions")
    print("=" * 60)
    print("")
    print("Access URL: http://<Instance Public IP>:80")
    print("")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="One-Click Deployment of FlexusAgent to Huawei Cloud Flexus L Instance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (shows menu)
  python scripts/caller.py

  # Deploy FlexusAgent instance (credentials auto-fetched from env vars HW_ACCESS_KEY, HW_SECRET_KEY, HW_SECURITY_TOKEN)
  python scripts/caller.py deploy --name my-flexusagent --region cn-north-4 --spec hf.xlarge.1.linux

  # Integrate Huawei Cloud ModelArts MaaS models
  python scripts/caller.py maas --flexusagent-base-url http://<IP>:80 --flexusagent-email <email> --flexusagent-password <password> --maas-api-key <API_KEY>

  # Change admin password on remote L instance via COC (credentials auto-fetched from env vars)
  python scripts/caller.py passwd --resource-id <instance_id> --region-id cn-north-4 --admin-password <string>
  
  # Import Dify app workflow to FlexusAgent instance
  python scripts/caller.py import-app-workflow --resource-id <instance_id> --region-id cn-north-4 --flexusagent-email <email> --flexusagent-password <password> --app-workflow-id <workflow_id>
  
  # Query instance details (including floating IP)
  python scripts/caller.py query-instance --instance-id <instance_id>
        """,
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    deploy_parser = subparsers.add_parser('deploy', help='Deploy FlexusAgent instance')
    deploy_parser.add_argument('--name', help='Instance name (optional, auto-generated if not provided)')
    deploy_parser.add_argument('--region', choices=REGION_IDS, help='Region ID')
    deploy_parser.add_argument('--spec', choices=['hf.xlarge.1.linux', 'ahf.xlarge.1.linux', 'hf.xlarge.3.linux', 'ahf.xlarge.3.linux'], 
                               help='Instance spec (required, must be one of: hf.xlarge.1.linux, ahf.xlarge.1.linux, hf.xlarge.3.linux, ahf.xlarge.3.linux)')
    deploy_parser.add_argument('--ak', help='Huawei Cloud AK (optional, default from env HW_ACCESS_KEY)')
    deploy_parser.add_argument('--sk', help='Huawei Cloud SK (optional, default from env HW_SECRET_KEY)')
    deploy_parser.add_argument('--security-token', help='Huawei Cloud security token (required for temp credentials)')
    deploy_parser.add_argument('--non-interactive', action='store_true', help='Non-interactive mode')

    passwd_parser = subparsers.add_parser('passwd', help='Change FlexusAgent admin password')
    passwd_parser.add_argument('--resource-id', help='L Instance Resource ID')
    passwd_parser.add_argument('--region-id', choices=REGION_IDS, help='Region ID')
    passwd_parser.add_argument('--admin-password', help='New admin password')
    passwd_parser.add_argument('--timeout', type=int, default=600, help='Timeout in seconds')
    passwd_parser.add_argument('--execute-user', default='root', help='Execute user (optional, default root)')
    passwd_parser.add_argument('--ak', help='Huawei Cloud AK')
    passwd_parser.add_argument('--sk', help='Huawei Cloud SK')
    passwd_parser.add_argument('--security-token', help='Huawei Cloud security token (required for temp credentials)')
    passwd_parser.add_argument('--non-interactive', action='store_true', help='Non-interactive mode')

    maas_parser = subparsers.add_parser('maas', help='Integrate Huawei Cloud ModelArts MaaS models')
    maas_parser.add_argument('--flexusagent-base-url', type=str, help='FlexusAgent Web UI URL')
    maas_parser.add_argument('--flexusagent-email', type=str, help='FlexusAgent admin email')
    maas_parser.add_argument('--flexusagent-password', type=str, help='FlexusAgent admin password')
    maas_parser.add_argument('--maas-api-key', type=str, help='ModelArts MaaS API Key')
    maas_parser.add_argument('--non-interactive', action='store_true', help='Non-interactive mode, execute without confirmation')

    import_workflow_parser = subparsers.add_parser('import-app-workflow', help='Import Dify app workflow to FlexusAgent instance')
    import_workflow_parser.add_argument('--resource-id', help='L Instance Resource ID')
    import_workflow_parser.add_argument('--region-id', choices=REGION_IDS, help='Region ID')
    import_workflow_parser.add_argument('--flexusagent-email', type=str, help='FlexusAgent admin email')
    import_workflow_parser.add_argument('--flexusagent-password', type=str, help='FlexusAgent admin password')
    import_workflow_parser.add_argument('--app-workflow-id', type=str, help='Dify app workflow ID (e.g., Bid_Writing_And_Templated_Adaptation)')
    import_workflow_parser.add_argument('--timeout', type=int, default=600, help='Timeout in seconds')
    import_workflow_parser.add_argument('--ak', help='Huawei Cloud AK')
    import_workflow_parser.add_argument('--sk', help='Huawei Cloud SK')
    import_workflow_parser.add_argument('--security-token', help='Huawei Cloud security token (required for temp credentials)')
    import_workflow_parser.add_argument('--non-interactive', action='store_true', help='Non-interactive mode')

    query_parser = subparsers.add_parser('query-instance', help='Query FlexusAgent instance details')
    query_parser.add_argument('--instance-id', help='Instance ID (resource_id)', required=True)
    query_parser.add_argument('--ak', help='Huawei Cloud AK')
    query_parser.add_argument('--sk', help='Huawei Cloud SK')
    query_parser.add_argument('--security-token', help='Huawei Cloud security token (required for temp credentials)')

    args = parser.parse_args()

    try:
        if args.command == 'deploy':
            do_deploy_flexusagent(args)
        elif args.command == 'passwd':
            do_change_flexusagent_admin_password(args)
        elif args.command == 'maas':
            do_install_maas(args)
        elif args.command == 'import-app-workflow':
            do_import_app_workflow(args)
        elif args.command == 'query-instance':
            # Construct args object to adapt to do_check_uniagent
            args.resource_id = args.instance_id
            do_check_uniagent(args)
        else:
            choice = show_main_menu()
            if choice == 0:
                print("Exiting program")
                sys.exit(0)
            elif choice == 1:
                args.command = 'deploy'
                do_deploy_flexusagent(args)
            elif choice == 2:
                args.command = 'passwd'
                do_change_flexusagent_admin_password(args)
            elif choice == 3:
                args.command = 'maas'
                do_install_maas(args)
            elif choice == 4:
                show_webui_info()
            elif choice == 5:
                args.command = 'import-app-workflow'
                do_import_app_workflow(args)
    except ValueError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nUser interrupted operation")
        sys.exit(0)


if __name__ == '__main__':
    main()
