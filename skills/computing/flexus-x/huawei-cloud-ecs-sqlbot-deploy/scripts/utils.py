#!/usr/bin/env python3
"""
Utility functions for Huawei Cloud SQLBot Deployment
"""

import json
import requests
import uuid
import urllib3
import subprocess
import time
import os
import sys
from datetime import datetime
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.signer.signer import Signer
from huaweicloudsdkcore.sdk_request import SdkRequest
from typing import Optional

urllib3.disable_warnings()

# Import configuration module (use config.X directly to get runtime updates)
import config


def check_dependencies(auto_install=True):
    """Check and install dependencies

    Args:
        auto_install: Whether to automatically install missing dependencies

    Returns:
        bool: Whether all dependencies are satisfied
    """
    import shutil
    import subprocess
    
    missing_bins = []
    missing_modules = []
    
    # Check required binary tools
    required_bins = ['python3']
    for bin_name in required_bins:
        if not shutil.which(bin_name):
            missing_bins.append(bin_name)
    
    # Check required Python modules
    required_modules = ['huaweicloudsdkcore', 'requests']
    for module_name in required_modules:
        try:
            __import__(module_name)
        except ImportError:
            missing_modules.append(module_name)
    
    # If all dependencies are satisfied
    if not missing_bins and not missing_modules:
        print("✅ Dependency check passed")
        return True
    
    # Some dependencies are missing
    print("\n" + "=" * 60)
    print("⚠️  Dependency check failed, missing the following dependencies:")
    print("=" * 60)
    
    if missing_bins:
        print("\n🔧 Missing system tools:")
        for bin_name in missing_bins:
            print(f"   - {bin_name}")
    
    if missing_modules:
        print("\n📦 Missing Python modules:")
        for module_name in missing_modules:
            print(f"   - {module_name}")
    
    if not auto_install:
        print("\n❌ Please manually install missing dependencies and retry")
        return False
    
    # Auto install
    print("\n" + "=" * 60)
    print("🔄 Starting automatic installation of missing dependencies...")
    print("=" * 60)
    
    # Send notification: Starting dependency installation
    missing_list = []
    if missing_bins:
        missing_list.extend([f"System tools: {b}" for b in missing_bins])
    if missing_modules:
        missing_list.extend([f"Python modules: {m}" for m in missing_modules])
    
    send_progress_notification(
        "Starting dependency installation",
        f"Installing missing dependencies:\n" + "\n".join([f"- {item}" for item in missing_list]),
        "info"
    )
    
    install_success = True
    
    # Install Python modules
    if missing_modules:
        print("\n📦 Installing Python modules...")
        modules_to_install = []
        if 'huaweicloudsdkcore' in missing_modules:
            modules_to_install.append('huaweicloudsdkcore')
        if 'requests' in missing_modules:
            modules_to_install.append('requests')
        
        try:
            pip_cmd = [
                'pip', 'install', '--break-system-packages',
                '-i', 'https://repo.huaweicloud.com/repository/pypi/simple'
            ] + modules_to_install
            
            result = subprocess.run(
                pip_cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                print(f"✅ Python modules installed successfully: {', '.join(modules_to_install)}")
            else:
                print(f"❌ Python module installation failed: {result.stderr}")
                install_success = False
        except Exception as e:
            print(f"❌ Python module installation exception: {e}")
            install_success = False
    
    if install_success:
        print("\n✅ All dependencies installed successfully")
        # Send notification: Dependency installation completed
        send_progress_notification(
            "Dependency installation completed",
            "All dependencies have been installed successfully, ready to start deployment",
            "success"
        )
        return True
    else:
        print("\n❌ Some dependencies failed to install, please install manually and retry")
        # Send notification: Dependency installation failed
        send_progress_notification(
            "Dependency installation failed",
            "Some dependencies failed to install, please install manually and retry",
            "error"
        )
        return False


def get_project_id_by_region(ak: str, sk: str, region: str, security_token: Optional[str] = None) -> Optional[str]:
    """Auto-fetch Project ID for specified region using AK, SK and Region

    Args:
        ak: Huawei Cloud Access Key
        sk: Huawei Cloud Secret Key
        region: Region code, e.g. 'cn-north-4'
        security_token: Security Token for temporary credentials (optional)

    Returns:
        Project ID, returns None if fetch fails
    """
    print(f"\n🔍 Auto-fetching Project ID (Region: {region})...")
    iam_endpoint = "https://iam.myhuaweicloud.com/v3/projects"
    
    try:
        # Support both temporary and permanent credentials
        if security_token:
            credentials = BasicCredentials(ak, sk).with_security_token(security_token)
        else:
            credentials = BasicCredentials(ak, sk)
        signer = Signer(credentials)
        
        request = SdkRequest()
        request.method = "GET"
        request.schema = "https"
        request.host = "iam.myhuaweicloud.com"
        request.resource_path = "/v3/projects"
        request.body = ""
        request.header_params = {
            "Content-Type": "application/json",
            "Client-Request-Id": str(uuid.uuid4())
        }
        # Add X-Security-Token BEFORE signing so it's included in signature
        if security_token:
            request.header_params["X-Security-Token"] = security_token
        request.query_params = []
        
        signed_request = signer.sign(request)
        
        headers = {}
        for key, value in signed_request.header_params.items():
            if isinstance(value, bytes):
                headers[key] = value.decode('iso-8859-1')
            else:
                headers[key] = str(value)
        
        resp = requests.get(iam_endpoint, headers=headers, timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            projects = data.get('projects', [])
            if projects:
                # Priority: find matching region
                for project in projects:
                    project_name = project.get('name', '')
                    if project_name == region:
                        project_id = project.get('id')
                        print(f"✅ Project ID fetched successfully: {project_id}")
                        return project_id
                # If no exact match found, return the first project
                project_id = projects[0].get('id')
                print(f"✅ Project ID fetched successfully: {project_id} (using default project)")
                return project_id
        print(f"❌ Failed to fetch Project ID: HTTP {resp.status_code}")
        print(f"Response: {resp.text[:200]}")
        return None
    except Exception as e:
        print(f"❌ Exception while fetching Project ID: {e}")
        return None


def pprint(*args, **kwargs):
    """print + flush to ensure real-time output"""
    print(*args, **kwargs)
    sys.stdout.flush()


def send_progress_notification(title, message, status="info"):
    """Send progress notification to user"""
    # Build message content
    emoji = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "📢"
    }.get(status, "📢")
    
    # Always print notification content (ensure real-time output)
    pprint(f"\n{'='*50}")
    pprint(f"{emoji} [{title}]")
    pprint(f"{'='*50}")
    pprint(message)
    pprint(f"{'='*50}\n")
    
    # Send Feishu notification directly
    if config.ENABLE_FEISHU_NOTIFY and config.NOTIFY_USER_ID:
        try:
            content = f"{emoji} **{title}**\n\n{message}"
            
            # Use openclaw message send command to send notification
            # Run in background to avoid blocking
            result = subprocess.run(
                [
                    "openclaw", "message", "send",
                    "--channel", "feishu",
                    "--target", f"user:{config.NOTIFY_USER_ID}",
                    "--message", content
                ],
                capture_output=True,
                text=True,
                timeout=60  # Increased timeout
            )
            
            if result.returncode == 0:
                pprint(f"✅ Feishu notification sent: {title}")
            else:
                # Print full error for debugging
                pprint(f"⚠️ Feishu notification failed (code {result.returncode})")
                if result.stderr:
                    pprint(f"   stderr: {result.stderr[:200]}")
                if result.stdout:
                    pprint(f"   stdout: {result.stdout[:200]}")
                
        except subprocess.TimeoutExpired:
            pprint(f"⚠️ Feishu notification timeout (60s)")
        except FileNotFoundError:
            pprint(f"⚠️ openclaw CLI not available, skipping notification")
        except Exception as e:
            pprint(f"⚠️ Feishu notification exception: {type(e).__name__}: {e}")
    else:
        pprint(f"ℹ️  Feishu notification disabled (ENABLE_FEISHU_NOTIFY={config.ENABLE_FEISHU_NOTIFY}, NOTIFY_USER_ID={config.NOTIFY_USER_ID})")


def check_lock_file():
    """Check lock file to prevent concurrent execution"""
    if os.path.exists(config.LOCK_FILE):
        # Check if lock file has expired (more than 30 minutes)
        lock_time = os.path.getmtime(config.LOCK_FILE)
        lock_age = int(time.time() - lock_time)
        
        if lock_age < 1800:  # 30 minutes
            print(f"\n" + "=" * 60)
            print(f"❌ Deployment in progress detected!")
            print(f"=" * 60)
            print(f"Lock file: {config.LOCK_FILE}")
            print(f"Locked for: {lock_age} seconds")
            print(f"Expires in: {1800 - lock_age} seconds")
            print(f"\n⚠️ Important notes:")
            print(f"1. Do not run multiple deployment tasks")
            print(f"2. If no deployment is running, delete the lock file")
            print(f"3. Or use --force flag to override (not recommended)")
            print(f"=" * 60)
            
            # Show lock file content
            try:
                with open(config.LOCK_FILE, 'r') as f:
                    content = f.read()
                    print(f"\nLock file content:\n{content}")
            except:
                pass
                
            return False
        else:
            print(f"⚠️ Lock file expired ({lock_age}s), deleting and continuing")
            os.remove(config.LOCK_FILE)
    return True


def create_lock_file():
    """Create lock file"""
    import socket
    hostname = socket.gethostname()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(config.LOCK_FILE, 'w') as f:
        f.write(f"SQLBot Deployment Lock\n")
        f.write(f"Created: {timestamp}\n")
        f.write(f"Hostname: {hostname}\n")
        f.write(f"PID: {os.getpid()}\n")
        f.write(f"Warning: Do not run multiple deployment tasks!\n")
        f.write(f"Delete this file if no deployment is running\n")
    print(f"🔒 Lock file created: {config.LOCK_FILE}")
    print(f"⚠️ Warning: Lock file created, do not run deployment again")


def remove_lock_file():
    """Remove lock file"""
    if os.path.exists(config.LOCK_FILE):
        os.remove(config.LOCK_FILE)
        print(f"🔓 Lock file removed: {config.LOCK_FILE}")


def show_supported_regions():
    """Show supported regions and flavors"""
    print("\n" + "=" * 80)
    print("📋 Huawei Cloud SQLBot Deployment - Supported Regions and X Instance Types")
    print("=" * 80)
    print("| Region Code | Region Name | Supported X Instance Types (Priority Order) |")
    print("|-------------|-------------|-------------------------------------------|")
    
    for region_code, types in config.REGION_FLAVOR_PRIORITY.items():
        if region_code == "default":
            continue
        region_name = config.REGION_NAMES.get(region_code, region_code)
        print(f"| {region_code:12} | {region_name:20} | {', '.join(types):28} |")
    
    print("\n" + "=" * 80)
    print("📌 Smart Flavor Selection Features:")
    print("  ✅ Priority Selection: Script auto-selects best X instance type by region")
    print("  ✅ Auto Fallback: Automatically try next option if preferred flavor is sold out")
    print("  ✅ Multiple Retries: Up to 3 different flavors until success")
    print("  ✅ 4U8G Compatible: Always select 4-core 8GB memory configuration")
    print("  ✅ Backward Compatible: Users can still specify --flavor parameter manually")
    print("=" * 80)
