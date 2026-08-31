#!/usr/bin/env python3
"""
Utility functions for Huawei Cloud Flexus X + DeepSeek Harness (dsh) Deployment
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

import config


def check_dependencies(auto_install=True):
    import shutil
    import subprocess

    missing_bins = []
    missing_modules = []

    required_bins = ['python3']
    for bin_name in required_bins:
        if not shutil.which(bin_name):
            missing_bins.append(bin_name)

    required_modules = ['huaweicloudsdkcore', 'huaweicloudsdkecs', 'huaweicloudsdkcoc', 'requests']
    for module_name in required_modules:
        try:
            import importlib
            importlib.import_module(module_name)
        except ImportError:
            missing_modules.append(module_name)

    if not missing_bins and not missing_modules:
        print("✅ Dependency check passed")
        return True

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

    print("\n" + "=" * 60)
    print("🔄 Starting automatic installation of missing dependencies...")
    print("=" * 60)

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

    if missing_modules:
        print("\n📦 Installing Python modules...")
        modules_to_install = []
        for mod in ['huaweicloudsdkcore', 'huaweicloudsdkecs', 'huaweicloudsdkcoc', 'requests']:
            if mod in missing_modules:
                modules_to_install.append(mod)

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
        send_progress_notification(
            "Dependency installation completed",
            "All dependencies have been installed successfully, ready to start deployment",
            "success"
        )
        return True
    else:
        print("\n❌ Some dependencies failed to install, please install manually and retry")
        send_progress_notification(
            "Dependency installation failed",
            "Some dependencies failed to install, please install manually and retry",
            "error"
        )
        return False


def get_project_id_by_region(ak: str, sk: str, region: str, security_token: str = None) -> Optional[str]:
    print(f"\n🔍 Auto-fetching Project ID (Region: {region})...")
    iam_endpoint = "https://iam.myhuaweicloud.com/v3/projects"

    try:
        credentials = BasicCredentials(ak, sk)
        if security_token:
            credentials = credentials.with_security_token(security_token)
        signer = Signer(credentials)

        request = SdkRequest()
        request.method = "GET"
        request.schema = "https"
        request.host = "iam.myhuaweicloud.com"
        request.resource_path = "/v3/projects"
        request.body = ""
        header_params = {
            "Content-Type": "application/json",
            "Client-Request-Id": str(uuid.uuid4())
        }
        if security_token:
            header_params["X-Security-Token"] = security_token
        request.header_params = header_params
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
                for project in projects:
                    project_name = project.get('name', '')
                    if project_name == region:
                        project_id = project.get('id')
                        print(f"✅ Project ID fetched successfully: {project_id}")
                        return project_id
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
    print(*args, **kwargs)
    sys.stdout.flush()


def send_progress_notification(title, message, status="info"):
    emoji = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "📢"
    }.get(status, "📢")

    pprint(f"\n{'='*50}")
    pprint(f"{emoji} [{title}]")
    pprint(f"{'='*50}")
    pprint(message)
    pprint(f"{'='*50}\n")

    if config.ENABLE_FEISHU_NOTIFY and config.NOTIFY_USER_ID:
        try:
            content = f"{emoji} **{title}**\n\n{message}"

            result = subprocess.run(
                [
                    "openclaw", "message", "send",
                    "--channel", "feishu",
                    "--target", f"user:{config.NOTIFY_USER_ID}",
                    "--message", content
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                pprint(f"✅ Feishu notification sent: {title}")
            else:
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


def get_local_public_ip():
    print("\n🌐 Getting local public IP...")

    ip_services = [
        ("https://ifconfig.me", "ifconfig.me"),
        ("https://ip.sb", "ip.sb"),
        ("https://ipinfo.io/ip", "ipinfo.io"),
        ("https://api.ipify.org", "ipify.org"),
        ("https://icanhazip.com", "icanhazip.com"),
    ]

    for url, service_name in ip_services:
        try:
            resp = requests.get(url, timeout=10)
            ip = resp.text.strip()
            import socket
            socket.inet_aton(ip)
            print(f"✅ Local public IP: {ip} (via {service_name})")
            return ip
        except Exception as e:
            print(f"  Failed to try {service_name}: {e}")
            continue

    print(f"❌ All IP services failed")
    return None


def check_lock_file():
    if os.path.exists(config.LOCK_FILE):
        lock_time = os.path.getmtime(config.LOCK_FILE)
        lock_age = int(time.time() - lock_time)

        if lock_age < 1800:
            print(f"\n" + "=" * 60)
            print(f"❌ Deployment in progress detected!")
            print(f"=" * 60)
            print(f"Lock file: {config.LOCK_FILE}")
            print(f"Locked for: {lock_age} seconds")
            print(f"Expires in: {1800 - lock_age} seconds")
            print(f"\n⚠️ Important notes:")
            print(f"1. ❌ RUNNING MULTIPLE DEPLOYMENTS WILL CREATE DUPLICATE SERVERS")
            print(f"2. ❌ THIS WILL INCUR DOUBLE CHARGES - ABSOLUTELY NOT ALLOWED")
            print(f"3. If no deployment is running, manually delete the lock file:")
            print(f"   Windows: del \"{config.LOCK_FILE}\"")
            print(f"   Linux/Mac: rm \"{config.LOCK_FILE}\"")
            print(f"4. Lock file expires automatically after 30 minutes")
            print(f"=" * 60)

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
    import socket
    hostname = socket.gethostname()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(config.LOCK_FILE, 'w') as f:
        f.write(f"DeepSeek Harness (dsh) Deployment Lock\n")
        f.write(f"Created: {timestamp}\n")
        f.write(f"Hostname: {hostname}\n")
        f.write(f"PID: {os.getpid()}\n")
        f.write(f"Warning: Do not run multiple deployment tasks!\n")
        f.write(f"Delete this file if no deployment is running\n")
    print(f"🔒 Lock file created: {config.LOCK_FILE}")
    print(f"⚠️ Warning: Lock file created, do not run deployment again")


def remove_lock_file():
    if os.path.exists(config.LOCK_FILE):
        os.remove(config.LOCK_FILE)
        print(f"🔓 Lock file removed: {config.LOCK_FILE}")


def show_supported_regions():
    print("\n" + "=" * 80)
    print("📋 Huawei Cloud Flexus X + dsh Deployment - Supported Regions and Flexus X Instance Types")
    print("=" * 80)
    print("| Region Code | Region Name | Supported Flexus X Instance Types (Priority Order) |")
    print("|-------------|-------------|-------------------------------------------|")

    for region_code, types in config.REGION_FLAVOR_PRIORITY.items():
        if region_code == "default":
            continue
        region_name = config.REGION_NAMES.get(region_code, region_code)
        print(f"| {region_code:12} | {region_name:20} | {', '.join(types):28} |")

    print("\n" + "=" * 80)
    print("📌 Flavor Selection Features:")
    print("  ✅ Region-based Selection: Script auto-selects Flexus X instance type by region")
    print("  ✅ Default 2U4G: Uses x1.2u.4g (2-core 4GB) as default configuration")
    print("  ✅ Manual Override: Users can specify --flavor parameter manually")
    print("  ⚠️ Single Request: No automatic retry if flavor is sold out")
    print("=" * 80)
