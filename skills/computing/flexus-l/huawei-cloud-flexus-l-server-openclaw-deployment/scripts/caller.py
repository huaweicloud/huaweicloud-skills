#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click OpenClaw Deployment - Main Entry (Simplified Version)
"""

import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.utils import REGION_IDS
from scripts.deploy import do_deploy_openclaw
from scripts.models import do_install_maas
from scripts.channels import do_install_channel


CONSOLE_URL = "https://console.huaweicloud.com/smb/?/resource/list"


def show_main_menu():
    """Display main menu for user to select operation type"""
    print("=" * 60)
    print("          OpenClaw One-Click Deployment Tool (Simplified)")
    print("=" * 60)
    print("Please select an operation:")
    print("")
    print("  1. One-click deploy OpenClaw to Huawei Cloud Flexus L instance")
    print("  2. Add models to existing OpenClaw instance")
    print("  3. Add channels to existing OpenClaw instance")
    print("  4. View OpenClaw Web UI access instructions")
    print("  0. Exit")
    print("")
    print("=" * 60)
    
    while True:
        try:
            choice = input("Please enter your choice (0-4): ")
            choice = int(choice)
            if choice in [0, 1, 2, 3, 4]:
                return choice
            else:
                print("Invalid input, please enter a number between 0-4")
        except ValueError:
            print("Invalid input, please enter a number")


def show_webui_info():
    """Display Web UI access instructions"""
    print("=" * 60)
    print("          OpenClaw Web UI Access Instructions")
    print("=" * 60)
    print("")
    print("Web UI access requires manual security group configuration in Huawei Cloud console.")
    print("")
    print("Steps:")
    print("1. Login to Huawei Cloud Flexus Application Server L instance console")
    print(f"   🔗 Console URL: {CONSOLE_URL}")
    print("")
    print("2. Find your OpenClaw instance in the instance list")
    print("")
    print("3. Click the instance name to view details")
    print("")
    print('4. Find "Security" or "Network" option in the left menu')
    print("")
    print("5. Configure security group rules to open port 18789")
    print("")
    print("Access URL: http://<instance-public-ip>:18789")
    print("")
    print("=" * 60)
    print("Security Note: Once the port is opened, OpenClaw Web UI will be accessible. Please evaluate security risks before proceeding.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Huawei Cloud Flexus L Instance One-Click OpenClaw Deployment (Simplified Version)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (show menu for selection)
  python scripts/caller.py

  # Create OpenClaw instance
  python scripts/caller.py deploy --name my-openclaw --region cn-north-4 --ak <AK> --sk <SK>

  # Install models on remote L instance via COC
  python scripts/caller.py maas --resource-id <instance_id> --region-id cn-north-4 --model-params <json> --ak <AK> --sk <SK>

  # Install channels on remote L instance via COC
  python scripts/caller.py channel --resource-id <instance_id> --region-id cn-north-4 --channel-list <json> --ak <AK> --sk <SK>
        """,
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    deploy_parser = subparsers.add_parser('deploy', help='Deploy OpenClaw instance')
    deploy_parser.add_argument('--name', help='Instance name (optional, auto-generated if not provided)')
    deploy_parser.add_argument('--region', choices=REGION_IDS, help='Region ID (optional, default cn-north-4)')
    deploy_parser.add_argument('--ak', help='Huawei Cloud AK (optional, will prompt for input if not provided)')
    deploy_parser.add_argument('--sk', help='Huawei Cloud SK (optional, will prompt for input if not provided)')
    deploy_parser.add_argument('--non-interactive', action='store_true', help='Non-interactive mode, execute without confirmation')

    maas_parser = subparsers.add_parser('maas', help='Install models on remote L instance via COC')
    maas_parser.add_argument('--resource-id', help='L instance resource ID (required)')
    maas_parser.add_argument('--region-id', choices=REGION_IDS, help='Region ID (optional, default cn-north-4)')
    maas_parser.add_argument('--model-params', help='Model parameters JSON (optional)')
    maas_parser.add_argument('--timeout', type=int, help='Timeout in seconds (optional, default 600)')
    maas_parser.add_argument('--execute-user', default='root', help='Execute user (optional, default root)')
    maas_parser.add_argument('--ak', help='Huawei Cloud AK (optional, will prompt for input if not provided)')
    maas_parser.add_argument('--sk', help='Huawei Cloud SK (optional, will prompt for input if not provided)')
    maas_parser.add_argument('--non-interactive', action='store_true', help='Non-interactive mode, execute without confirmation')

    channel_parser = subparsers.add_parser('channel', help='Install channels on remote L instance via COC')
    channel_parser.add_argument('--resource-id', help='L instance resource ID (required)')
    channel_parser.add_argument('--region-id', choices=REGION_IDS, help='Region ID (optional, default cn-north-4)')
    channel_parser.add_argument('--channel-list', help='Channel list JSON (optional)')
    channel_parser.add_argument('--timeout', type=int, help='Timeout in seconds (optional, default 600)')
    channel_parser.add_argument('--execute-user', default='root', help='Execute user (optional, default root)')
    channel_parser.add_argument('--ak', help='Huawei Cloud AK (optional, will prompt for input if not provided)')
    channel_parser.add_argument('--sk', help='Huawei Cloud SK (optional, will prompt for input if not provided)')
    channel_parser.add_argument('--non-interactive', action='store_true', help='Non-interactive mode, execute without confirmation')

    args = parser.parse_args()

    try:
        if args.command == 'maas':
            do_install_maas(args)
        elif args.command == 'channel':
            do_install_channel(args)
        elif args.command == 'deploy':
            do_deploy_openclaw(args)
        else:
            choice = show_main_menu()
            if choice == 0:
                print("Exit program")
                sys.exit(0)
            elif choice == 1:
                args.command = 'deploy'
                do_deploy_openclaw(args)
            elif choice == 2:
                args.command = 'maas'
                do_install_maas(args)
            elif choice == 3:
                args.command = 'channel'
                do_install_channel(args)
            elif choice == 4:
                show_webui_info()
    except KeyboardInterrupt:
        print("\n\nUser interrupted operation")
        sys.exit(0)


if __name__ == '__main__':
    main()
