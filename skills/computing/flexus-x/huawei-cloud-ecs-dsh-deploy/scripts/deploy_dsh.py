#!/usr/bin/env python3
"""
Huawei Cloud ECS Server Creation Skill (DeepSeek Harness / dsh Deployment Edition)
Supports Flexus X Instance, Elastic IP, Security Group Creation, COC-based Deployment
"""

import json
import requests
import urllib3
import subprocess
import time
import os
import sys
import random
import string
from pathlib import Path

urllib3.disable_warnings()

import config
from utils import (
    pprint, send_progress_notification, get_project_id_by_region,
    check_dependencies, check_lock_file,
    create_lock_file, remove_lock_file, show_supported_regions
)
from huawei_cloud_ecs import HuaweiCloudECS
from coc_deploy import deploy_dsh_via_coc, wait_for_uniagent_online


def generate_secure_password(length=12):
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    special = "@#$%^&*"

    password = [
        random.choice(uppercase),
        random.choice(lowercase),
        random.choice(digits),
        random.choice(special)
    ]

    all_chars = uppercase + lowercase + digits + special
    password += [random.choice(all_chars) for _ in range(length - 4)]
    random.shuffle(password)

    return ''.join(password)


def configure_security_group(client, sg_name, vpc_id):
    existing_sg = client.get_security_group_by_name(sg_name)
    if existing_sg:
        sg_id = existing_sg.get("id")
        print(f"✅ Using existing security group: {sg_name} ({sg_id})")
        return sg_id

    sg_id = client.create_security_group(sg_name, vpc_id)
    if not sg_id:
        print("❌ Failed to create security group")
        return None

    client.add_security_group_rule(sg_id, remote_group_id=sg_id,
                                   description="Allow all IPv4 traffic within security group")
    client.add_security_group_rule(sg_id, ip_version="IPv6", remote_group_id=sg_id,
                                   description="Allow all IPv6 traffic within security group")

    print(f"\n✅ Security group created: {sg_name}")
    print(f"   🛡️  No inbound rules added - please manually add rules in console")
    return sg_id


def cleanup_resources(client, server_id, server_name=None):
    """Clean up resources if deployment fails to prevent cost leakage"""
    if not server_id:
        return

    print(f"\n🗑️ Initiating cleanup of failed deployment resources...")

    try:
        print(f"   Deleting server: {server_id} ({server_name})")
        success = client.delete_server(
            server_id=server_id,
            server_name=server_name,
            confirm=False
        )
        if success:
            print(f"   ✅ Server deletion initiated successfully")
        else:
            print(f"   ⚠️ Server deletion may have failed, please check console")
    except Exception as e:
        print(f"   ⚠️ Error during cleanup: {e}")

    print(f"\n⚠️ Important: Resource cleanup may take a few minutes.")
    print(f"   Please verify in Huawei Cloud ECS Console:")
    print(f"   https://console.huaweicloud.com/console/?region={client.region}#/ecs/manager/vmList")


def main():
    if not check_dependencies(auto_install=True):
        print("❌ Dependency check failed, cannot continue deployment")
        sys.exit(1)

    import argparse
    parser = argparse.ArgumentParser(
        description='Huawei Cloud DeepSeek Harness (dsh) One-Click Deployment Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Usage examples:
        1. Deploy DeepSeek Harness (default):
            python3 deploy_dsh.py --ak AK123 --sk SK456 --project-id PROJECT123

        2. Deploy to specific region:
            python3 deploy_dsh.py --ak AK123 --sk SK456 --project-id PROJECT123 --region cn-east-3

        3. Deploy with custom dsh port and API key:
            python3 deploy_dsh.py --ak AK123 --sk SK456 --project-id PROJECT123 --dsh-port 3080 --api-key sk-xxxx

        4. List supported regions:
            python3 deploy_dsh.py --list-regions

        5. Test connection:
            python3 deploy_dsh.py --ak AK123 --sk SK456 --project-id PROJECT123 --test

        6. List servers:
            python3 deploy_dsh.py --ak AK123 --sk SK456 --region cn-north-4 --list-servers

        7. Delete server:
            python3 deploy_dsh.py --ak AK123 --sk SK456 --region cn-north-4 --delete <server_id>
            python3 deploy_dsh.py --ak AK123 --sk SK456 --region cn-north-4 --delete <server_name>

        8. Check deployment status:
            python3 deploy_dsh.py --ak AK123 --sk SK456 --region cn-north-4 --status <server_id_or_name>

        Features:
        ✅ Auto-select best flavor (2-core 4GB Flexus X instance)
        ✅ Auto-create security group and network
        ✅ Auto-deploy DeepSeek Harness (dsh) via COC (Node.js 22 + systemd + Nginx)
        ✅ Support 19 Huawei Cloud regions
        ✅ Server management: list, status and delete
        ⚠️ No automatic retry - single request only
        """
    )

    parser.add_argument('--ak', type=str, default=os.environ.get('HW_ACCESS_KEY'),
                        help='Huawei Cloud Access Key (AK)')
    parser.add_argument('--sk', type=str, default=os.environ.get('HW_SECRET_KEY'),
                        help='Huawei Cloud Secret Key (SK)')
    parser.add_argument('--security-token', type=str, default=os.environ.get('HW_SECURITY_TOKEN'),
                        help='Security Token for temporary credentials')
    parser.add_argument('--project-id', type=str, help='Huawei Cloud Project ID (optional)')
    parser.add_argument('--region', type=str, default='cn-north-4', help='Region (default: cn-north-4)')

    parser.add_argument('--test', action='store_true', help='Test AK/SK connection')
    parser.add_argument('--list-regions', '-l', action='store_true', help='Show supported regions')

    parser.add_argument('--name', type=str, help='Server name (default: x-dsh-YYYYMMDDHHMM)')
    parser.add_argument('--flavor', type=str, default='x1.2u.4g', help='Flavor (default: x1.2u.4g)')
    parser.add_argument('--image', type=str, help='Image ID')
    parser.add_argument('--zone', type=str, help='Availability zone')
    parser.add_argument('--random-zone', action='store_true', help='Randomly select availability zone')
    parser.add_argument('--charging-mode', choices=['prePaid', 'postPaid'], default='postPaid',
                        help='Billing mode: prePaid (monthly) or postPaid (pay-as-you-go)')
    parser.add_argument('--no-eip', action='store_true', help='Do not create elastic IP')
    parser.add_argument('--bandwidth', type=int, default=100, help='EIP bandwidth (default: 100M)')
    parser.add_argument('--password', type=str, help='Server password')
    parser.add_argument('--volume-size', type=int, default=40, help='System disk size (GB)')

    parser.add_argument('--delete', type=str, metavar='SERVER_ID_OR_NAME',
                        help='Delete server by ID or name')
    parser.add_argument('--list-servers', action='store_true',
                        help='List all servers in the region')
    parser.add_argument('--force-delete', action='store_true',
                        help='Force delete without confirmation')

    parser.add_argument('--status', type=str, metavar='SERVER_ID_OR_NAME',
                        help='Check deployment status of a server')

    parser.add_argument('--notify', action='store_true', help='Enable Feishu notification')
    parser.add_argument('--notify-user-id', type=str, help='Feishu user ID')

    parser.add_argument('--coc-region', type=str, default='cn-north-4',
                        help='COC service region (default: cn-north-4)')
    parser.add_argument('--coc-timeout', type=int, default=1800,
                        help='COC script execution timeout in seconds (default: 1800)')
    parser.add_argument('--execute-user', type=str, default='root',
                        help='User to execute COC script (default: root)')

    parser.add_argument('--dsh-port', type=int, default=config.DSH_DEFAULT_PORT,
                        help=f'dsh listening port (default: {config.DSH_DEFAULT_PORT}, loopback only)')
    parser.add_argument('--api-key', type=str,
                        help='DEEPSEEK_API_KEY to pre-seed into the dsh service (optional)')

    parser.add_argument('--auto-confirm', action='store_true',
                        help='Skip interactive confirmation (use with caution!)')

    args = parser.parse_args()

    if args.notify_user_id:
        config.NOTIFY_USER_ID = args.notify_user_id
        config.ENABLE_FEISHU_NOTIFY = True
        pprint(f"✅ Feishu notification enabled, user ID: {config.NOTIFY_USER_ID}")
    elif args.notify:
        config.ENABLE_FEISHU_NOTIFY = True
        if not config.NOTIFY_USER_ID:
            pprint("⚠️ Notification enabled but no user ID configured")
            config.ENABLE_FEISHU_NOTIFY = False
    else:
        config.ENABLE_FEISHU_NOTIFY = False

    if not args.test:
        if not check_lock_file():
            sys.exit(1)

    ak, sk, region = args.ak, args.sk, args.region
    security_token = args.security_token

    if not ak or not sk:
        print("❌ Error: AK and SK parameters must be provided")
        return

    project_id = args.project_id or get_project_id_by_region(ak, sk, region, security_token)
    if not project_id:
        print("❌ Error: Failed to get Project ID")
        return

    print(f"✅ Authentication verified successfully")
    print(f"   Region: {region}")
    print(f"   Project ID: {project_id[:8]}...")

    client = HuaweiCloudECS(ak, sk, project_id, region, security_token)

    if args.test:
        client.test_connection()
        return

    if args.list_servers:
        print("\n" + "=" * 60)
        print("📋 Servers in region: " + region)
        print("=" * 60)
        servers = client.list_servers()
        if servers:
            print("\n| ID | Name | Status | Flavor | Public IP |")
            print("|----|------|--------|--------|-----------|")
            for s in servers:
                print(f"| {s['id'][:8]}... | {s['name']} | {s['status']} | {s.get('flavor', 'N/A')} | {s.get('public_ip', 'N/A')} |")
        else:
            print("No servers found")
        return

    if args.status:
        print("\n" + "=" * 60)
        print("🔍 Checking deployment status")
        print("=" * 60)

        server_id = args.status
        if '-' not in args.status:
            servers = client.list_servers(name_filter=args.status)
            if not servers:
                print(f"❌ Server not found: {args.status}")
                return
            server_id = servers[0]['id']
            print(f"✅ Found server: {servers[0]['name']} ({server_id})")

        status_info = client.get_deployment_status(server_id)

        print("\n📊 Deployment Status:")
        print("-" * 40)
        print(f"  Server Name: {status_info.get('server_name', 'N/A')}")
        print(f"  Server Status: {status_info.get('server_status', 'N/A')}")
        print(f"  Public IP: {status_info.get('public_ip', 'N/A')}")
        print(f"  Private IP: {status_info.get('private_ip', 'N/A')}")
        print(f"  Flavor: {status_info.get('flavor', 'N/A')}")
        print()
        print("📦 Service Status:")
        print("-" * 40)

        services = status_info.get('services', {})
        dsh = services.get('dsh', {})

        if dsh.get('healthy'):
            print(f"  ✅ dsh: Healthy (HTTP 200 via public check)")
        elif status_info.get('public_ip'):
            print(f"  ⚠️ dsh: not exposed publicly (by design - loopback only)")
            print(f"     Verify via SSH tunnel on your machine:")
            print(f"     ssh -L 3080:127.0.0.1:3080 root@{status_info.get('public_ip')} -> http://127.0.0.1:3080")
        else:
            print(f"  ⚠️ dsh: Unable to check (no public IP)")

        print()
        print("=" * 60)

        if not dsh.get('healthy') and status_info.get('public_ip'):
            print("\n💡 Suggestions:")
            print(f"  - Establish SSH tunnel locally and open http://127.0.0.1:3080:")
            print(f"    ssh -L 3080:127.0.0.1:3080 root@{status_info.get('public_ip')}")
            print(f"  - Check dsh service (via Huawei Cloud COC/ECS Console):")
            print(f"    systemctl status dsh")
            print(f"    journalctl -u dsh -n 50")
            print(f"  - Check dsh loopback port (via Huawei Cloud COC/ECS Console):")
            print(f"    curl http://127.0.0.1:3080")

        return

    if args.delete:
        print("\n" + "=" * 60)
        print("🗑️ Deleting server")
        print("=" * 60)
        success = client.delete_server(
            server_id=args.delete if '-' in args.delete else None,
            server_name=args.delete if '-' not in args.delete else None,
            confirm=not args.force_delete
        )
        if success:
            print("\n✅ Server deletion completed")
        else:
            print("\n❌ Server deletion failed")
        return

    if not client.test_connection():
        return

    print("\n" + "=" * 50)
    print("💡 Note: Server flavor availability varies by region.")
    print("🔗 For details, see: https://www.huaweicloud.com/pricing/calculator.html#/hecs")
    print("=" * 50)

    if not args.name:
        timestamp = time.strftime("%Y%m%d%H%M")
        args.name = f"x-dsh-{timestamp}"

    network = client.get_default_network()
    print(f"\n📡 Network configuration:")
    print(f"  Subnet: {network.get('subnet_name')}")
    print(f"  VPC ID: {network.get('vpc_id')}")
    print(f"  Availability zone: {network.get('availability_zone')}")

    zone = None
    if args.random_zone:
        zone = client.get_random_available_zone()
    elif args.zone:
        zone = args.zone

    if not args.password:
        args.password = generate_secure_password(12)
        print(f"\n🔑 Auto-generated server password: {args.password}")

    print("\n" + "=" * 50)
    print("🚀 Starting DeepSeek Harness (dsh) deployment process")
    print("=" * 50)

    print("\n" + "⚠️ " * 10)
    print("🖥️ Server architecture requirements:")
    print("   Architecture: x86_64 (AMD64)")
    print("   OS: Ubuntu 22.04 Server 64-bit")
    print("   Minimum: x1.2u.4g (2vCPUs 4GiB), x1.4u.8g or higher recommended")
    print("⚠️ " * 10)

    create_lock_file()

    server_id = None

    try:
        print(f"\n📋 Preparing to create server...")
        print(f"Server name: {args.name}")
        flavor_id, flavor_desc = client.get_default_flavor(args.flavor)
        print(f"Flavor: {flavor_id} ({flavor_desc})")
        if zone:
            print(f"Availability zone: {zone}")
        print(f"Billing mode: {'Pay-as-you-go' if args.charging_mode == 'postPaid' else 'Monthly'}")
        print(f"Elastic IP: {'Yes' if not args.no_eip else 'No'}")
        if not args.no_eip:
            print(f"EIP bandwidth: {args.bandwidth}M")

        print("\n🛡️  [SECURITY] Creating empty security group...")
        print("   No inbound rules will be added automatically.")
        print("   You need to manually add security group rules after deployment.\n")

        sg_id = configure_security_group(client, "sg-dsh", network.get("vpc_id"))
        if not sg_id:
            print("❌ Security group creation failed, aborting deployment")
            return

        print(f"   ✅ Security group ready: sg-dsh (no inbound rules)")
        print(f"   📝 After deployment, add rules manually in Huawei Cloud Console\n")

        print("\n" + "=" * 50)
        print("⚠️  IMPORTANT: Confirm server creation")
        print("=" * 50)

        print("\n📋 Deployment configuration:")
        print(f"  Server name: {args.name}")
        print(f"  Flavor: {args.flavor}")
        print(f"  Image: Ubuntu 22.04 Server 64bit (x86_64)")
        print(f"  System disk: {args.volume_size}GB")
        print(f"  Billing mode: {'Monthly' if args.charging_mode == 'prePaid' else 'Pay-as-you-go'}")
        if args.no_eip:
            print(f"  Elastic IP: Not created")
        else:
            print(f"  Elastic IP: {args.bandwidth}M bandwidth, pay-by-traffic")
        print(f"  Region: {args.region}")
        print(f"  dsh port (loopback): {args.dsh_port}")
        print()
        print("💰 Price calculator: https://www.huaweicloud.com/pricing/calculator.html#/hecs")
        print()
        print("⚠️ Important notes:")
        print("  1. This will create paid resources on Huawei Cloud")
        print("  2. Server creation may take 3-5 minutes")
        print("  3. Do not run this command multiple times")
        print("  4. If timeout occurs, check Huawei Cloud ECS console")
        print("  5. No automatic retry will be attempted")
        print("=" * 50)

        print("\n" + "⚠️ " * 10)
        print("⚠️  IMPORTANT: This will create a Huawei Cloud Flexus X instance and incur charges!")
        print("⚠️  You MUST confirm before proceeding!")
        print("⚠️ " * 10)

        if not args.auto_confirm:
            while True:
                confirm = input("\n⚠️ Confirm server creation? This will incur charges. (yes/no/CONFIRM): ").strip().lower()
                if confirm in ['yes', 'y', 'confirm']:
                    print("✅ User confirmed, proceeding with deployment...")
                    break
                elif confirm in ['no', 'n']:
                    print("\n❌ Operation cancelled by user")
                    return
                else:
                    print("❌ Invalid input, please enter 'yes', 'no' or 'CONFIRM'")
        else:
            print("⚠️ Auto-confirm enabled, proceeding with deployment...")

        zone_info = f"Zone: {zone}\n" if zone else ""
        send_progress_notification(
            "Starting server creation",
            f"Server name: {args.name}\nFlavor: {args.flavor}\nRegion: {args.region}\n{zone_info}Estimated 3-5 minutes",
            "info"
        )

        image_id = args.image
        if not image_id:
            print("\n🔍 Auto-fetching Ubuntu 22.04 image ID...")
            image_result = client.get_ubuntu_image_id("22.04")
            if not image_result:
                print("❌ Failed to get image ID, aborting")
                return
            image_id = image_result[0] if isinstance(image_result, tuple) else image_result
            print(f"✅ Image ID: {image_id}")

        result = client.create_server(
            server_name=args.name,
            flavor_id=flavor_id,
            image_id=image_id,
            volume_size=args.volume_size,
            vpc_id=network.get("vpc_id"),
            subnet_id=network.get("subnet_id"),
            security_group_id=sg_id,
            admin_pass=args.password,
            availability_zone=zone,
            eip_bandwidth=args.bandwidth,
            charging_mode=args.charging_mode,
            create_eip=not args.no_eip,
        )

        if not result:
            print("❌ Server creation failed, aborting")
            return

        server_id = result["server_id"]
        admin_pass = result["admin_pass"]

        print(f"\n✅ Server creation request submitted")
        print(f"Server ID: {server_id}")
        print(f"Waiting for server to be ready... (up to 10 minutes)")

        send_progress_notification(
            "⏳ Server creation in progress",
            f"Server ID: {server_id}\nServer name: {args.name}\nWaiting for server to be ready...",
            "info"
        )

        detail = client.wait_server_active(server_id, timeout=600)
        if not detail:
            print(f"\n❌ Server status check timed out")
            print(f"⚠️ Server may still be creating. Please check Huawei Cloud ECS console:")
            print(f"   https://console.huaweicloud.com/console/?region={args.region}#/ecs/manager/vmList")
            print(f"   Server ID: {server_id}")
            print(f"   🔑 Server password: {admin_pass}")
            print(f"\n💡 If server was created successfully, check Huawei Cloud ECS Console")
            print(f"   and manually configure DeepSeek Harness on the server.")
            send_progress_notification(
                "⚠️ Server creation timeout",
                f"Server ID: {server_id}\nStatus check timed out after 10 minutes.",
                "warning"
            )
            return

        public_ip = detail.get("public_ip") or result.get("public_ip")
        private_ip = detail.get("private_ip")

        print("\n" + "=" * 60)
        print("✅ Server purchased successfully!")
        print("=" * 60)
        print(f"📋 Server information:")
        print(f"  Name: {detail.get('name')}")
        print(f"  ID: {server_id}")
        print(f"  Public IP: {public_ip}")
        print(f"  Private IP: {private_ip}")
        print("\n" + "⚠️ " * 15)
        print(f"🔑 Server initial password: {admin_pass}")
        print("⚠️ " * 15)
        print("\n💡 Tips:")
        print("  1. This is the SSH login password for the server")
        print("  2. Recommended to change password immediately after login")
        print("  3. If password is forgotten, reset via Huawei Cloud ECS console")

        send_progress_notification(
            "✅ Server purchased successfully",
            f"Server name: {detail.get('name')}\nPublic IP: {public_ip}\nPrivate IP: {private_ip}\n\nStarting COC deployment...",
            "success"
        )

        if server_id:
            print("\n" + "=" * 50)
            print("☁️ Starting COC deployment...")
            print("=" * 50)
            sys.stdout.flush()

            send_progress_notification(
                "☁️ Starting COC deployment",
                f"Deploying DeepSeek Harness (dsh) via Cloud Operations Center...\nThis may take 5-10 minutes, please wait.",
                "info"
            )

            print(f"\n📦 Deploying dsh via COC (Cloud Operations Center)")
            print(f"   Server ID: {server_id}")
            print(f"   Region: {region}")
            print(f"   dsh port: {args.dsh_port}")
            if args.api_key:
                print(f"   DEEPSEEK_API_KEY: pre-seeded (hidden)")
            print(f"⏳ This may take several minutes, please wait...")
            sys.stdout.flush()

            print(f"\n⏳ Checking UniAgent status...")
            sys.stdout.flush()

            uniagent_result = wait_for_uniagent_online(
                resource_id=server_id,
                ak=ak,
                sk=sk,
                security_token=security_token,
                max_wait_seconds=300,
                check_interval=10
            )

            if not uniagent_result.get("ok"):
                print(f"\n⚠️ UniAgent not ready: {uniagent_result.get('error')}")
                print(f"   Proceeding with COC deployment anyway...")
                sys.stdout.flush()
            else:
                print(f"   ✅ UniAgent ready in {uniagent_result.get('elapsed_seconds')}s")
                sys.stdout.flush()

            coc_result = deploy_dsh_via_coc(
                resource_id=server_id,
                region_id=region,
                ak=ak,
                sk=sk,
                security_token=security_token,
                coc_region=args.coc_region,
                timeout=args.coc_timeout,
                execute_user=args.execute_user,
                dsh_port=args.dsh_port,
                api_key=args.api_key
            )

            if coc_result.get("ok"):
                # Parse deployment info from COC output
                coc_output = coc_result.get("result", {}).get("output", "") or ""
                dsh_port = str(args.dsh_port)
                dsh_version = ""
                node_version = ""

                if coc_output and "### DEPLOYMENT_INFO_START ###" in coc_output:
                    import re
                    info_match = re.search(r'### DEPLOYMENT_INFO_START ###(.*?)### DEPLOYMENT_INFO_END ###', coc_output, re.DOTALL)
                    if info_match:
                        info_block = info_match.group(1)
                        port_match = re.search(r'DSH_PORT=(\S+)', info_block)
                        version_match = re.search(r'DSH_VERSION=(\S+)', info_block)
                        node_match = re.search(r'NODE_VERSION=(\S+)', info_block)
                        if port_match:
                            dsh_port = port_match.group(1)
                        if version_match:
                            dsh_version = version_match.group(1)
                        if node_match:
                            node_version = node_match.group(1)

                print("\n" + "=" * 60)
                print("🎉 DeepSeek Harness (dsh) deployed successfully via COC!")
                print("=" * 60)

                print(f"\n{'='*60}")
                print(f"🌐 SSH TUNNEL COMMAND (copy & paste to access Web UI):")
                print(f"{'='*60}")
                print(f"  ssh -L {dsh_port}:127.0.0.1:{dsh_port} root@{public_ip}")
                print(f"{'='*60}")
                print(f"  After running: enter password '{admin_pass}', keep window open")
                print(f"  Then open browser: http://127.0.0.1:{dsh_port}")
                print(f"{'='*60}")
                if dsh_version:
                    print(f"📦 dsh CLI version: {dsh_version}")
                if node_version:
                    print(f"📦 Node.js version: {node_version}")

                print("\n" + "-" * 60)
                print("📋 Summary:")
                print("-" * 60)
                print(f"\n🖥️ Server information:")
                print(f"   Name: {detail.get('name')}")
                print(f"   ID: {server_id}")
                print(f"   Public IP: {public_ip}")
                print(f"   Private IP: {private_ip}")
                print(f"   Flexus X Instance password: {admin_pass}")

                print(f"\n📦 Installed Components:")
                print(f"   - Node.js 22 LTS")
                print(f"   - @deepseek-ai/dsh (systemd service 'dsh', port {dsh_port})")
                print(f"   - Nginx reverse proxy (80 -> 127.0.0.1:{dsh_port}, loopback only)")

                print(f"\n🛡️  Security Group Policy:")
                print(f"   All server ports are BLOCKED - add rules in console")
                print(f"   Go to Huawei Cloud Console -> ECS -> Security Groups -> sg-dsh")
                print(f"   Add ONE inbound rule: TCP port 22 from your IP /32 (for SSH tunnel)")

                print(f"\n📝  Next steps:")
                print(f"  1. Add security group rule (TCP 22, your IP /32) in Huawei Cloud Console")
                print(f"  2. On your local machine, establish SSH tunnel (PowerShell / macOS Terminal):")
                print(f"     ssh -L {dsh_port}:127.0.0.1:{dsh_port} root@{public_ip}")
                print(f"  3. Open Web UI in browser: http://127.0.0.1:{dsh_port}")
                print(f"  4. In the Web UI: Settings -> Models, enter your DeepSeek API key and save")
                print(f"  5. Choose a workspace directory, then start a session")

                print(f"\n🔧 dsh Notes:")
                print(f"   - dsh web binds to 127.0.0.1:{dsh_port} only (by design)")
                print(f"   - Remote access goes through SSH tunnel (port 22 only, no public 80/3080)")
                print(f"   - Update CLI: sudo npm install -g @deepseek-ai/dsh && sudo systemctl restart dsh")
                print(f"   - View logs: journalctl -u dsh -f")
                sys.stdout.flush()

                api_key_info = ""
                if args.api_key:
                    api_key_info = "\n🔑 DEEPSEEK_API_KEY pre-seeded into the service (systemd drop-in)"

                send_progress_notification(
                    "🎉 DeepSeek Harness (dsh) deployed successfully!",
                    f"🌐 SSH TUNNEL COMMAND (copy & paste to access Web UI):\n"
                    f"  ssh -L {dsh_port}:127.0.0.1:{dsh_port} root@{public_ip}\n"
                    f"  Then open browser: http://127.0.0.1:{dsh_port}\n"
                    f"🖥️ Server info:\n"
                    f"  Name: {detail.get('name')}\n"
                    f"  Public IP: {public_ip}\n"
                    f"{api_key_info}\n"
                    f"  ⚠️ SECURITY: Add security group rule MANUALLY in console\n"
                    f"  Rule needed: TCP 22 from your IP /32 (SSH tunnel)\n\n"
                    f"💡 Next: open Web UI -> Settings -> Models -> enter DeepSeek API key",
                    "success"
                )
            else:
                coc_error = coc_result.get("error", {})
                error_message = coc_error.get("message", "Unknown error")
                print(f"\n❌ COC deployment failed: {error_message}")
                sys.stdout.flush()
                send_progress_notification(
                    "❌ COC deployment failed",
                    f"Deployment failed via COC.\n"
                    f"Server: {detail.get('name')}\n"
                    f"Error: {error_message}\n\n"
                    f"Please try manual deployment:\n"
                    f"SSH: ssh root@{public_ip}",
                    "error"
                )

            print("\n" + "=" * 50)
            print("✅ Deployment complete")
            print("=" * 50)
            print(f"Server: {detail.get('name')}")
            print(f"Public IP: {public_ip}")
            print(f"SSH: ssh root@{public_ip}")
            print(f"Password: {admin_pass}")
            print(f"\n🛡️  Security: Empty security group - NO inbound rules")
            print(f"   Add security group rule MANUALLY in Huawei Cloud Console")
            print(f"   Security group: sg-dsh | Allow TCP 22 from your IP /32 (SSH tunnel)")
            print(f"\n{'='*50}")
            print(f"🌐 SSH TUNNEL COMMAND (copy & paste):")
            print(f"  ssh -L 3080:127.0.0.1:3080 root@{public_ip}")
            print(f"{'='*50}")
            print(f"\n🔗 Huawei Cloud ECS Console: https://console.huaweicloud.com/console/?region={region}#/ecs/manager/vmList")
            sys.stdout.flush()
        else:
            print("\n⚠️ No server ID, skipping deployment")
            print(f"\n📋 Server information:")
            print(f"  Name: {detail.get('name')}")
            print(f"  Private IP: {private_ip}")
            print(f"  Password: {admin_pass}")
            sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n❌ Deployment cancelled by user")
        cleanup_resources(client, server_id, args.name)
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        cleanup_resources(client, server_id, args.name)
    finally:
        remove_lock_file()


if __name__ == "__main__":
    if "--list-regions" in sys.argv or "-l" in sys.argv:
        show_supported_regions()
        sys.exit(0)

    main()
