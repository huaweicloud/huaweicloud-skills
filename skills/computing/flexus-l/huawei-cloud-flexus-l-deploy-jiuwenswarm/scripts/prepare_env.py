#!/usr/bin/env python3
"""
Environment Preparation Script for JiuwenSwarm Deployment
Verifies Huawei Cloud credentials, checks dependencies, and prepares environment.
This is the first phase in the JiuwenSwarm deployment workflow.
"""

import os
import sys
import shutil
import logging
from pathlib import Path

os.environ['PYTHONIOENCODING'] = 'utf-8'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

try:
    from huaweicloudsdkcore.auth.credentials import GlobalCredentials
    from huaweicloudsdkcoc.v1.region.coc_region import CocRegion
    from huaweicloudsdkcoc.v1 import CocClient
except ImportError:
    log.error("Huawei Cloud SDK modules not installed. Please run: pip install huaweicloudsdkcoc")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent))
from utils import get_huaweicloud_credentials, hcloud_json

def check_credentials():
    print("\n" + "=" * 60)
    print("  Phase 1: Environment Preparation")
    print("=" * 60)

    try:
        AK, SK, REGION, SECURITY_TOKEN = get_huaweicloud_credentials()
    except ValueError as e:
        print(f"[ERROR] {e}")
        print("\nOption 1 - Configure hcloud (recommended):")
        print("  hcloud configure set --cli-mode=AKSK --cli-region=cn-north-4 --cli-access-key=YOUR_AK --cli-secret-key=YOUR_SK")
        print("\nOption 2 - Set environment variables:")
        print("  Linux/Mac: export HUAWEICLOUD_SDK_AK=your_ak && export HUAWEICLOUD_SDK_SK=your_sk && export HUAWEICLOUD_REGION=cn-north-4")
        print("  Windows: set HUAWEICLOUD_SDK_AK=your_ak && set HUAWEICLOUD_SDK_SK=your_sk && set HUAWEICLOUD_REGION=cn-north-4")
        print("\nFor temporary security credentials (STS token), also set:")
        print("  Linux/Mac: export HUAWEICLOUD_SDK_SECURITY_TOKEN=your_token")
        print("  Windows: set HUAWEICLOUD_SDK_SECURITY_TOKEN=your_token")
        return False, None, None, None, None

    print(f"[OK] AK: {AK[:2]}...{AK[-2:]}")
    print(f"[OK] SK: {SK[:2]}...{SK[-2:]}")
    print(f"[OK] Region: {REGION}")
    return True, AK, SK, REGION, SECURITY_TOKEN

def check_dependencies():
    print("\n[INFO] Checking dependency modules...")

    modules = {
        'requests': 'requests',
        'huaweicloudsdkcore': 'huaweicloudsdkcore',
        'huaweicloudsdkcoc': 'huaweicloudsdkcoc'
    }

    all_ok = True
    for key, module_name in modules.items():
        try:
            __import__(module_name)
            print(f"[OK] {key}")
        except ImportError:
            print(f"[ERROR] {key} not installed. Please run: pip install {module_name}")
            all_ok = False

    # KooCLI (hcloud) is a standalone binary, not a Python package
    if shutil.which("hcloud"):
        print("[OK] hcloud (KooCLI)")
    else:
        print("[ERROR] hcloud (KooCLI) not found in PATH. Please install KooCLI:")
        print("        https://support.huaweicloud.com/usermanual-hcli/hcli_03_001.html")
        all_ok = False

    return all_ok

def verify_credentials(ak, sk, region, security_token=None):
    print(f"\n[INFO] Verifying Huawei Cloud credentials...")
    print(f"[INFO] Region: {region}")

    try:
        # Verify via KooCLI: use `hcloud IAM KeystoneListProjects` to confirm the
        # AK/SK (and STS token, if any) are valid. Credentials are passed through
        # environment variables so they never appear on the command line.
        extra_env = {
            "HUAWEICLOUD_SDK_AK": ak,
            "HUAWEICLOUD_SDK_SK": sk,
            "HUAWEICLOUD_REGION": region,
        }
        if security_token:
            extra_env["HUAWEICLOUD_SDK_SECURITY_TOKEN"] = security_token
        hcloud_json(["IAM", "KeystoneListProjects", "--cli-region=cn-north-4"], extra_env=extra_env)
        print("[OK] Credentials verification successful!")
        return True
    except Exception as e:
        print(f"[ERROR] Credentials verification exception: {e}")
        return False

def main():
    print("=" * 60)
    print("  JiuwenSwarm Deployment - Environment Preparation")
    print("=" * 60)

    credential_result = check_credentials()
    if not credential_result[0]:
        sys.exit(1)
    
    _, AK, SK, REGION, SECURITY_TOKEN = credential_result

    if not check_dependencies():
        sys.exit(1)

    if not verify_credentials(AK, SK, REGION, SECURITY_TOKEN):
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  Environment preparation completed!")
    print("=" * 60)
    print("\nNext step: Run create_instance.py to create Flexus L instance")

if __name__ == "__main__":
    main()

