#!/usr/bin/env python3
"""
Environment Preparation Script for JiuwenSwarm Deployment
Verifies Huawei Cloud credentials, checks dependencies, and prepares environment.
This is the first phase in the JiuwenSwarm deployment workflow.
"""

import os
import sys
import logging
from pathlib import Path

os.environ['PYTHONIOENCODING'] = 'utf-8'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    log.error("requests module not installed. Please run: pip install requests")
    sys.exit(1)

try:
    from huaweicloudsdkcore.signer.signer import Signer
    from huaweicloudsdkcore.sdk_request import SdkRequest
except ImportError:
    log.error("huaweicloudsdkcore module not installed. Please run: pip install huaweicloudsdkcore")
    sys.exit(1)

try:
    from huaweicloudsdkcore.auth.credentials import GlobalCredentials
    from huaweicloudsdkcoc.v1.region.coc_region import CocRegion
    from huaweicloudsdkcoc.v1 import CocClient
except ImportError:
    log.error("Huawei Cloud SDK modules not installed. Please run: pip install huaweicloudsdkcoc huaweicloudsdkrms")
    sys.exit(1)

AK = os.getenv("HUAWEICLOUD_SDK_AK")
SK = os.getenv("HUAWEICLOUD_SDK_SK")
REGION = os.getenv("HUAWEICLOUD_REGION", "cn-north-4")

def check_credentials():
    print("\n" + "=" * 60)
    print("  Phase 1: Environment Preparation")
    print("=" * 60)

    if not AK or not SK:
        print("[ERROR] Please set environment variables HUAWEICLOUD_SDK_AK and HUAWEICLOUD_SDK_SK")
        print("\nSet command:")
        print("  Windows: set HUAWEICLOUD_SDK_AK=your_ak && set HUAWEICLOUD_SDK_SK=your_sk && set HUAWEICLOUD_REGION=cn-north-4")
        print("  Linux/Mac: export HUAWEICLOUD_SDK_AK=your_ak && export HUAWEICLOUD_SDK_SK=your_sk && export HUAWEICLOUD_REGION=cn-north-4")
        return False

    print(f"[OK] AK: {AK[:4]}...{AK[-4:]}")
    print(f"[OK] SK: {SK[:4]}...{SK[-4:]}")
    print(f"[OK] Region: {REGION}")
    return True

def check_dependencies():
    print("\n[INFO] Checking dependency modules...")

    modules = {
        'requests': 'requests',
        'huaweicloudsdkcore': 'huaweicloudsdkcore',
        'huaweicloudsdkcoc': 'huaweicloudsdkcoc',
        'huaweicloudsdkrms': 'huaweicloudsdkrms'
    }

    all_ok = True
    for key, module_name in modules.items():
        try:
            __import__(module_name)
            print(f"[OK] {key}")
        except ImportError:
            print(f"[ERROR] {key} not installed. Please run: pip install {module_name}")
            all_ok = False

    return all_ok

def verify_credentials(ak, sk, region):
    print(f"\n[INFO] Verifying Huawei Cloud credentials...")
    print(f"[INFO] Region: {region}")

    try:
        from huaweicloudsdkcore.signer.signer import Signer
        from huaweicloudsdkcore.sdk_request import SdkRequest
        import uuid

        credentials = type('Credentials', (), {'ak': ak, 'sk': sk})()
        signer = Signer(credentials)

        iam_endpoint = f"https://iam.{region}.myhuaweicloud.com/v3/projects"

        request = SdkRequest()
        request.method = "GET"
        request.schema = "https"
        request.host = f"iam.{region}.myhuaweicloud.com"
        request.resource_path = "/v3/projects"
        request.body = ""
        request.header_params = {
            "Content-Type": "application/json",
            "Client-Request-Id": str(uuid.uuid4())
        }
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
            print("[OK] Credentials verification successful!")
            return True
        else:
            print(f"[ERROR] Credentials verification failed: HTTP {resp.status_code}")
            return False

    except Exception as e:
        print(f"[ERROR] Credentials verification exception: {e}")
        return False

def main():
    print("=" * 60)
    print("  JiuwenSwarm Deployment - Environment Preparation")
    print("=" * 60)

    if not check_credentials():
        sys.exit(1)

    if not check_dependencies():
        sys.exit(1)

    if not verify_credentials(AK, SK, REGION):
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  Environment preparation completed!")
    print("=" * 60)
    print("\nNext step: Run create_instance.py to create Flexus L instance")

if __name__ == "__main__":
    main()