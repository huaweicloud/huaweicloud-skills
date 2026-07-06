#!/usr/bin/env python3
"""
Huawei Cloud ECS Server Creation Skill (SQLBot Deployment Edition) - Simplified Version
Supports X Instance, Elastic IP, Security Group Auto-configuration, COC-based SQLBot Deployment

Core Principles:
1. Call the create interface only once and wait for response completion
2. Increase timeout to avoid duplicate creation due to timeout
3. Lock file mechanism prevents concurrent execution
4. Simplify logic and focus on core functionality
5. Use COC (Cloud Operations Center) for script deployment instead of SSH

Main entry point for SQLBot deployment on Huawei Cloud X Instance
"""

import json
import requests
import uuid
import urllib3
import subprocess
import time
import os
import sys
from pathlib import Path
from datetime import datetime

urllib3.disable_warnings()

# Import modules
import config
from config import (
    REGION_FLAVOR_PRIORITY, REGION_FLAVOR_MAP, FLAVOR_DESCRIPTION,
    DEFAULT_CONFIG, REQUIRED_ARCH, REQUIRED_OS, OBS_SCRIPT_URL,
    ENABLE_FEISHU_NOTIFY, NOTIFY_USER_ID, LOCK_FILE
)
from utils import (
    pprint, send_progress_notification, get_project_id_by_region,
    check_dependencies, check_lock_file,
    create_lock_file, remove_lock_file, show_supported_regions
)
from huawei_cloud_ecs import HuaweiCloudECS
from coc_deploy import deploy_sqlbot_via_coc, wait_for_uniagent_online, check_uniagent_status


def main():
    """Main function"""

    # ========== Dependency Check ==========
    if not check_dependencies(auto_install=True):
        print("❌ Dependency check failed, cannot continue deployment")
        sys.exit(1)
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Huawei Cloud SQLBot One-Click Deployment Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  1. Deploy SQLBot (simplest):
     python3 deploy_sqlbot.py --ak AK123 --sk SK456 --project-id PROJECT123
  
  2. Deploy to specific region:
     python3 deploy_sqlbot.py --ak AK123 --sk SK456 --project-id PROJECT123 --region cn-east-3
  
  3. List supported regions:
     python3 deploy_sqlbot.py --list-regions
  
  4. Test connection:
     python3 deploy_sqlbot.py --ak AK123 --sk SK456 --project-id PROJECT123 --test

Features:
  ✅ Auto-select best flavor (4-core 8GB X instance)
  ✅ Auto-create security group and network
  ✅ Auto-deploy latest SQLBot version
  ✅ Support 19 Huawei Cloud regions
  ✅ Auto-retry other flavors when sold out
        """
    )
    
    # Huawei Cloud authentication parameters (must provide, not saved to file)
    parser.add_argument('--ak', type=str, default=os.environ.get('HW_ACCESS_KEY'), help='Huawei Cloud Access Key (AK). Can also be set via HW_ACCESS_KEY environment variable')
    parser.add_argument('--sk', type=str, default=os.environ.get('HW_SECRET_KEY'), help='Huawei Cloud Secret Key (SK). Can also be set via HW_SECRET_KEY environment variable')
    parser.add_argument('--security-token', type=str, default=os.environ.get('HW_SECURITY_TOKEN'), help='Huawei Cloud Security Token (for temporary credentials). Can also be set via HW_SECURITY_TOKEN environment variable')
    parser.add_argument('--project-id', type=str, help='Huawei Cloud Project ID (optional, auto-fetched if not provided)')
    parser.add_argument('--region', type=str, default='cn-north-4', help='Region (default: cn-north-4), use --list-regions to see supported regions')
    
    parser.add_argument('--test', action='store_true', help='Test AK/SK connection')
    parser.add_argument('--list-regions', '-l', action='store_true', help='Show supported regions')
    
    # Server creation parameters
    parser.add_argument('--name', type=str, help='Server name (default: x-SQLBot-YYYYMMDDHHMM)')
    parser.add_argument('--flavor', type=str, default='x1.4u.8g', help='Flavor (default: x1.4u.8g)')
    parser.add_argument('--image', type=str, help='Image ID')
    parser.add_argument('--zone', type=str, help='Availability zone')
    parser.add_argument('--random-zone', action='store_true', help='Randomly select availability zone')
    parser.add_argument('--on-demand', action='store_true', help='Use pay-as-you-go billing')
    parser.add_argument('--charging-mode', choices=['prePaid', 'postPaid'], default='postPaid',
                        help='Billing mode: prePaid (monthly) or postPaid (pay-as-you-go), default is postPaid')
    parser.add_argument('--no-eip', action='store_true', help='Do not create elastic IP')
    parser.add_argument('--bandwidth', type=int, default=300, help='EIP bandwidth (default: 300M)')
    parser.add_argument('--password', type=str, help='Server password')
    parser.add_argument('--volume-size', type=int, default=80, help='System disk size (GB) (default: 80)')
    
    # Individual operations
    parser.add_argument('--server-id', type=str, help='Server ID')
    
    # Force options
    parser.add_argument('--force', action='store_true', help='Force execution (ignore lock file check)')
    
    # Notification options
    parser.add_argument('--notify', action='store_true', help='Enable Feishu real-time notification')
    parser.add_argument('--notify-user-id', type=str, help='Feishu user ID (for sending notifications)')
    
    # Network options
    parser.add_argument('--local-ip', type=str, help='Manually specify local public IP (for security group configuration)')
    
    args = parser.parse_args()
    
    # Enable Feishu notification
    # Use notify-user-id if provided
    if args.notify_user_id:
        config.NOTIFY_USER_ID = args.notify_user_id
        config.ENABLE_FEISHU_NOTIFY = True
        pprint(f"✅ Feishu notification enabled, user ID: {config.NOTIFY_USER_ID}")
    elif args.notify:
        config.ENABLE_FEISHU_NOTIFY = True
        if config.NOTIFY_USER_ID:
            pass  # Use user ID from environment variable
        else:
            pprint("⚠️ Notification enabled but no user ID configured, notifications will not be sent")
            config.ENABLE_FEISHU_NOTIFY = False
    else:
        # Auto-enable notification if NOTIFY_USER_ID is set from environment
        if config.NOTIFY_USER_ID:
            config.ENABLE_FEISHU_NOTIFY = True
            pprint(f"✅ Feishu notification auto-enabled (user ID from env: {config.NOTIFY_USER_ID})")
        else:
            config.ENABLE_FEISHU_NOTIFY = False
    
    # Generate default server name
    if not args.name:
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        args.name = f"x-SQLBot-{timestamp}"
    
    # Check lock file (prevent concurrent execution)
    if not args.force and not args.test:
        if not check_lock_file():
            sys.exit(1)
    
    # Get AK/SK directly from parameters (not saved to file)
    ak = args.ak
    sk = args.sk
    region = args.region
    
    # Validate required parameters
    if not ak or not sk:
        print("❌ Error: AK and SK must be provided")
        print("   Use --ak, --sk parameters, or set HW_ACCESS_KEY and HW_SECRET_KEY environment variables")
        if args.security_token:
            print("   Note: Security Token is provided but AK/SK are missing")
        return
    
    # Auto-fetch or use user-provided Project ID
    if args.project_id:
        project_id = args.project_id
        print("🔐 Using user-provided Project ID")
    else:
        print("🔐 Auto-fetching Project ID...")
        project_id = get_project_id_by_region(ak, sk, region, security_token=args.security_token)
        if not project_id:
            print("❌ Error: Failed to auto-fetch Project ID")
            print("   Please check if AK/SK is correct, or provide --project-id parameter manually")
            return
    
    print(f"✅ Authentication verified successfully")
    print(f"   Region: {region}")
    print(f"   Project ID: {project_id[:8]}...")  # Show first 8 chars only for security
    
    client = HuaweiCloudECS(ak, sk, project_id, region, security_token=args.security_token)
    
    # Test connection
    if args.test:
        client.test_connection()
        return
        
    # Validate connection
    if not client.test_connection():
        return
    
    # Note about flavor availability
    print("\n" + "=" * 50)
    print("💡 Note: Server flavor availability varies by region.")
    print("🔗 For details, see: https://www.huaweicloud.com/pricing/calculator.html#/hecs")
    print("=" * 50)
        
    # Get network configuration
    network = client.get_default_network()
    print(f"\n📡 Network configuration:")
    print(f"  Subnet: {network.get('subnet_name')}")
    print(f"  VPC ID: {network.get('vpc_id')}")
    print(f"  Availability zone: {network.get('availability_zone')}")
    
    # Availability zone selection logic
    if args.random_zone:
        # Randomly select availability zone
        zone = client.get_random_available_zone()
    elif args.zone:
        # User specified availability zone
        zone = args.zone
    else:
        # No zone specified, let system auto-select (omit availability_zone parameter)
        zone = None
        # Don't display zone info (system auto-selects)
    
    # ========== SQLBot Deployment Process ==========
    print("\n" + "=" * 50)
    print("🚀 Starting SQLBot deployment process")
    print("=" * 50)
    
    # ⚠️ Architecture requirements notice
    print("\n" + "⚠️ " * 10)
    print("🖥️ Server architecture requirements:")
    print("   Architecture: x86_64 (AMD64)")
    print("   OS: Ubuntu 22.04 Server 64-bit")
    print("   Minimum: 4 vCPU 8GB RAM")
    print("⚠️ " * 10)
    print("\n💡 Why x86_64?")
    print("   - SQLBot Docker image is built for x86_64 architecture")
    print("   - ARM64 (aarch64) servers are not supported")
    print("   - Ensure Huawei Cloud X instance flavor is x86 (e.g., x1.4u.8g)")
    print("")
    
    # Create lock file
    create_lock_file()
    
    try:
        print("\n📋 Preparing to create server...")
        print(f"Server name: {args.name}")
        # Get flavor description
        flavor_id, flavor_desc = client.get_default_flavor(args.flavor)
        print(f"Flavor: {flavor_id} ({flavor_desc})")
        if zone:
            print(f"Availability zone: {zone}")
        print(f"Billing mode: {'Pay-as-you-go' if args.on_demand else 'Monthly'}")
        print(f"Elastic IP: {'Yes' if not args.no_eip else 'No'}")
        if not args.no_eip:
            print(f"EIP bandwidth: {args.bandwidth}M")
        
        # Simple confirmation (optional, can be commented out)
        # confirm = input("\nContinue creating server? (y/N): ")
        # if confirm.lower() != 'y':
        #     print("Creation cancelled")
        #     return
        
        # 1. Create security group
        # Security group name includes timestamp suffix, matching server name
        sg_timestamp = datetime.now().strftime("%Y%m%d%H%M")
        sg_name = f"sg-sqlbot-{sg_timestamp}"
        
        # Check if security group exists
        existing_sg = client.get_security_group_by_name(sg_name)
        if existing_sg:
            sg_id = existing_sg.get("id")
            print(f"✅ Using existing security group: {sg_name} ({sg_id})")
        else:
            sg_id = client.create_security_group(sg_name, network.get("vpc_id"))
        
        if sg_id:
            # 2. Add port rules
            print(f"\n🔐 Adding port access rules...")
            
            # SQLBot port: Allow internal network (192.168.0.0/16)
            client.add_security_group_rule(
                sg_id,
                port_range_min=8000,
                port_range_max=8000,
                remote_ip_prefix="192.168.0.0/16",
                description="SQLBot Web port"
            )
            print(f"   ✅ SQLBot (8000): Allow internal network")
            
            print(f"✅ Security group configured: {sg_name}")
        else:
            print("❌ Security group creation failed, aborting deployment")
            return
        
        # 4. Create server (with new security group)
        print("\n" + "=" * 50)
        print("🚀 Starting server creation...")
        print("=" * 50)
        
        # Output complete configuration
        print("\n📋 Deployment configuration:")
        print(f"  Server name: {args.name}")
        print(f"  Flavor: {args.flavor}")
        print(f"  Image: Ubuntu 22.04 Server 64bit (x86_64)")
        print(f"  System disk: {args.volume_size}GB")
        print(f"  Billing mode: {'Monthly' if args.charging_mode == 'prePaid' else 'Pay-as-you-go'}")
        print(f"  Elastic IP: {args.bandwidth}M bandwidth, pay-by-traffic")
        print(f"  Region: {args.region}")
        print()
        print("💰 Price calculator: https://www.huaweicloud.com/pricing/calculator.html#/hecs")
        print()
        
        print("⚠️ Important notes:")
        print("1. Server creation may take 3-5 minutes")
        print("2. Do not run this command multiple times")
        print("3. If timeout occurs, check Huawei Cloud ECS console for status")
        print("=" * 50)
        
        # 🔔 Notify user: Starting server creation
        zone_info = f"Zone: {zone}\n" if zone else ""
        send_progress_notification(
            "Starting server creation",
            f"Server name: {args.name}\n"
            f"Flavor: {args.flavor}\n"
            f"Region: {args.region}\n"
            f"{zone_info}"
            f"Estimated 3-5 minutes, please wait...",
            "info"
        )
        
        # Get image ID (if not provided)
        image_id = args.image
        if not image_id:
            print("\n🔍 Auto-fetching Ubuntu 22.04 image ID...")
            image_result = client.get_ubuntu_image_id("22.04")
            if not image_result:
                print("❌ Failed to get image ID, aborting")
                return
            # Handle return value (may be tuple or string)
            if isinstance(image_result, tuple):
                image_id = image_result[0]
            else:
                image_id = image_result
            print(f"✅ Image ID: {image_id}")
        
        # Select creation method based on billing mode
        charging_mode = args.charging_mode if hasattr(args, 'charging_mode') else ("postPaid" if args.on_demand else "prePaid")
        
        if charging_mode == "prePaid":
            result = client.create_prepaid_server_with_sdk(
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
            )
        else:
            result = client.create_postpaid_server_with_sdk(
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
            )
        
        if not result:
            print("❌ Server creation failed, aborting")
            return
            
        server_id = result["server_id"]
        admin_pass = result["admin_pass"]
        
        print(f"\n✅ Server creation request submitted")
        print(f"Server ID: {server_id}")
        print(f"Waiting for server to be ready...")
        
        # 🔔 Notify user: Server creation request submitted, waiting
        send_progress_notification(
            "⏳ Server creation in progress",
            f"Server ID: {server_id}\n"
            f"Server name: {args.name}\n"
            f"Waiting for server to be ready...\n"
            f"This usually takes 1-3 minutes.",
            "info"
        )
        
        # 5. Wait for server to become active
        detail = client.wait_server_active(server_id)
        if not detail:
            print(f"❌ Server failed to start")
            print(f"Please check Huawei Cloud ECS console for status")
            return
        
        # 5.5 Bind security group (ensure it takes effect)
        if sg_id:
            client.bind_security_group_to_server(server_id, sg_id, sg_name)
            # Wait a few seconds for security group to take effect
            time.sleep(5)
            
        public_ip = detail.get("public_ip") or result.get("public_ip")
        private_ip = detail.get("private_ip")
        
        # ========== Key progress feedback ==========
        print("\n" + "=" * 60)
        print("✅ Server purchased successfully!")
        print("=" * 60)
        print(f"📋 Server information:")
        print(f"  Name: {detail.get('name')}")
        print(f"  ID: {server_id}")
        print(f"  Public IP: {public_ip}")
        print(f"  Private IP: {private_ip}")
        print("\n" + "⚠️ " * 15)
        print("🔑 Server initial password (keep it secure):")
        print(f"   {admin_pass}")
        print("⚠️ " * 15)
        print("\n💡 Tips:")
        print("  1. Recommended to change password immediately after login")
        print("  2. If password is forgotten, reset via Huawei Cloud ECS console")
        
        # 🔔 Notify user: Server purchase complete
        send_progress_notification(
            "✅ Server purchased successfully",
            f"Server name: {detail.get('name')}\n"
            f"Public IP: {public_ip}\n"
            f"Private IP: {private_ip}\n\n"
            f"🔑 Initial password: {admin_pass}\n\n"
            f"⚠️ Keep this password secure, recommended to change after login\n\n"
            f"Starting SQLBot deployment via COC...",
            "success"
        )
        
        # 6. COC-based SQLBot Deployment
        if server_id:
            print("\n" + "=" * 50)
            print("☁️ Starting COC deployment...")
            print("=" * 50)
            sys.stdout.flush()
            # 🔔 Notify user: Starting COC deployment
            send_progress_notification(
                "☁️ Starting COC deployment",
                f"Deploying SQLBot via Cloud Operations Center...\n"
                f"This may take 5-10 minutes, please wait.",
                "info"
            )
            
            print(f"\n📦 Deploying SQLBot via COC (Cloud Operations Center)")
            print(f"   Server ID: {server_id}")
            print(f"   Region: {region}")
            print(f"⏳ This may take several minutes, please wait...")
            sys.stdout.flush()
            
            # Wait for UniAgent to be online for COC
            print(f"\n⏳ Checking UniAgent status...")
            sys.stdout.flush()
            
            uniagent_result = wait_for_uniagent_online(
                resource_id=server_id,
                ak=ak,
                sk=sk,
                security_token=args.security_token,
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
            
            # Deploy SQLBot using COC
            coc_result = deploy_sqlbot_via_coc(
                    resource_id=server_id,
                    region_id=region,
                    public_ip=public_ip,
                    ak=ak,
                    sk=sk,
                    security_token=args.security_token,
                    coc_region="cn-north-4",
                    timeout=600,
                    execute_user="root"
                )
            
            if coc_result.get("ok"):
                print("\n" + "=" * 60)
                print("🎉 SQLBot deployed successfully via COC!")
                print("=" * 60)
                print(f"\n🌐 SQLBot Web Service: http://{public_ip}:8000")
                print("\n" + "-" * 60)
                print("📋 Summary:")
                print("-" * 60)
                print(f"\n🖥️ Server information:")
                print(f"   Name: {detail.get('name')}")
                print(f"   ID: {server_id}")
                print(f"   Public IP: {public_ip}")
                print(f"   Private IP: {private_ip}")
                print(f"   X Instance password: {admin_pass}")
                print(f"\n🔐 SQLBot login:")
                print(f"   Web URL: http://{public_ip}:8000")
                print(f"   Username: admin")
                print(f"   Password: SQLBot@123456")
                print("\n" + "-" * 60)
                print("💡 Tips:")
                print("  1. Service will be fully ready in about 5 minutes")
                print("  2. Keep the X instance password and SQLBot login secure")
                print("  3. Recommended to change passwords after first login")
                sys.stdout.flush()
                
                # 🔔 Notify user: SQLBot deployment successful
                send_progress_notification(
                    "🎉 SQLBot deployed successfully!",
                    f"🌐 SQLBot Web Service: http://{public_ip}:8000\n\n"
                    f"🖥️ Server info:\n"
                    f"  Name: {detail.get('name')}\n"
                    f"  Public IP: {public_ip}\n"
                    f"  X Instance password: {admin_pass}\n\n"
                    f"🔐 SQLBot login:\n"
                    f"  Web URL: http://{public_ip}:8000\n"
                    f"  Username: admin\n"
                    f"  Password: SQLBot@123456\n\n"
                    f"💡 Note: Service will be ready in about 5 minutes",
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
                    f"Please check Huawei Cloud ECS console for details.",
                    "error"
                )
            
            # Final output
            print("\n" + "=" * 50)
            print("✅ Deployment complete")
            print("=" * 50)
            print(f"Server: {detail.get('name')}")
            print(f"Public IP: {public_ip}")
            print(f"Password: {admin_pass}")
            print(f"SQLBot Web Service: http://{public_ip}:8000")
            print(f"\n🔗 Huawei Cloud ECS Console: https://console.huaweicloud.com/console/?region={region}#/ecs/manager/vmList")
            sys.stdout.flush()
            
        else:
            print("\n⚠️ No server ID, skipping SQLBot deployment")
            print(f"\n📋 Server information:")
            print(f"  Name: {detail.get('name')}")
            print(f"  Private IP: {private_ip}")
            print(f"  Password: {admin_pass}")
            sys.stdout.flush()
            
    finally:
        remove_lock_file()


if __name__ == "__main__":
    import sys
    
    # Check for --list-regions argument
    if "--list-regions" in sys.argv or "-l" in sys.argv:
        show_supported_regions()
        sys.exit(0)
    
    main()
