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

sys.path.insert(0, str(Path(__file__).parent))
from utils import get_huaweicloud_credentials

def check_credentials():
    print("\n" + "=" * 60)
    print("  Phase 1: Environment Preparation")
    print("=" * 60)

    try:
        AK, SK, REGION, SECURITY_TOKEN = get_huaweicloud_credentials()
    except ValueError as e:
        print(f"[ERROR] {e}")
        print("\nSet command:")
        print("  Windows: set HUAWEICLOUD_SDK_AK=your_ak && set HUAWEICLOUD_SDK_SK=your_sk && set HUAWEICLOUD_REGION=cn-north-4")
        print("  Linux/Mac: export HUAWEICLOUD_SDK_AK=your_ak && export HUAWEICLOUD_SDK_SK=your_sk && export HUAWEICLOUD_REGION=cn-north-4")
        print("\nFor temporary security credentials (STS token), also set:")
        print("  Windows: set HUAWEICLOUD_SDK_SECURITY_TOKEN=your_token")
        print("  Linux/Mac: export HUAWEICLOUD_SDK_SECURITY_TOKEN=your_token")
        return False, None, None, None, None

    print(f"[OK] AK: {AK[:4]}...{AK[-4:]}")
    print(f"[OK] SK: {SK[:4]}...{SK[-4:]}")
    print(f"[OK] Region: {REGION}")
    if SECURITY_TOKEN:
        print(f"[OK] Using temporary security credentials (STS token)")
    return True, AK, SK, REGION, SECURITY_TOKEN

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

def verify_credentials(ak, sk, region, security_token=None):
    print(f"\n[INFO] Verifying Huawei Cloud credentials...")
    print(f"[INFO] Region: {region}")

    try:
        from huaweicloudsdkcore.signer.signer import Signer
        from huaweicloudsdkcore.sdk_request import SdkRequest
        from huaweicloudsdkcore.auth.credentials import BasicCredentials
        import uuid

        # 使用SDK原生凭据，原生支持security_token
        credentials = BasicCredentials(ak, sk)
        if security_token:
            credentials.with_security_token(security_token)

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
        
        # 临时凭据手动补充X-Security-Token请求头（原生SDK签名后不会自动加，需主动注入）
        if security_token:
            headers["X-Security-Token"] = security_token

        resp = requests.get(iam_endpoint, headers=headers, timeout=30)

        if resp.status_code == 200:
            print("[OK] Credentials verification successful!")
            return True
        else:
            print(f"[ERROR] Credentials verification failed: HTTP {resp.status_code}, Resp:{resp.text}")
            return False

    except Exception as e:
        print(f"[ERROR] Credentials verification exception: {e}")
        import traceback
        traceback.print_exc()
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