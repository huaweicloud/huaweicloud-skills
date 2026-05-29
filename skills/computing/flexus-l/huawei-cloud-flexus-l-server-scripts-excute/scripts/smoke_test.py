#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud COC Skill Smoke Test

Usage:
    python smoke_test.py --ak "your_ak" --sk "your_sk" [--region "cn-north-4"]
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.lib import create_script, execute_script, list_scripts, get_script_detail


def test_credentials(ak, sk, region):
    """Test credential configuration."""
    print(f"AK: {'✓' if ak else '✗'}")
    print(f"SK: {'✓' if sk else '✗'}")
    print(f"Region: {region}")

    if not ak or not sk:
        print("\nError: Please provide --ak and --sk parameters")
        return False

    return True


def test_create_script(ak, sk, region):
    """Test script creation functionality."""
    print("\nTest: Create Script")
    print("-" * 40)

    import time
    timestamp = str(int(time.time()))[-6:]
    result = create_script(
        name=f"test_script_{timestamp}",
        script_type="SHELL",
        content="echo 'Hello from COC SDK'",
        description="Test script",
        ak=ak,
        sk=sk,
        region=region,
        risk_level="LOW",
        version="1.0.0"
    )

    print(f"Result: {result['text']}")
    if result.get("ok"):
        print("✓ Script created successfully")
        return result.get("text", "").split(":")[-1].strip()
    else:
        print(f"✗ Failed to create script: {result.get('error', {}).get('message')}")
        return None


def test_list_scripts(ak, sk, region):
    """Test script listing functionality."""
    print("\nTest: List Scripts")
    print("-" * 40)

    result = list_scripts(ak, sk, region, page=1, limit=5)

    if result.get("ok"):
        data = result.get("result", {})
        scripts = data.get("scripts", [])
        total = data.get("total", 0)
        print(f"✓ Successfully retrieved {total} scripts")
        if scripts:
            print(f"Latest script: {scripts[0].get('name', '')}")
        return True
    else:
        print(f"✗ Failed to list scripts: {result.get('error', {}).get('message')}")
        return False


def test_execute_script(ak, sk, region, script_uuid):
    """Test script execution functionality."""
    print("\nTest: Execute Script")
    print("-" * 40)

    target_instances = [
        {
            "resource_id": "your_l_instance_resource_id",
            "region_id": "cn-north-4",
            "provider": "HCSS",
            "type": "L-INSTANCE"
        }
    ]

    result = execute_script(
        script_uuid=script_uuid,
        execute_user="root",
        timeout=60,
        success_rate=100,
        target_instances=target_instances,
        ak=ak,
        sk=sk,
        region=region
    )

    if result.get("ok"):
        print("✓ Script executed successfully")
        return True
    else:
        print(f"Note: {result.get('error', {}).get('message')}")
        print("(Requires real target instance information to complete execution test)")
        return False


def main():
    parser = argparse.ArgumentParser(description="Huawei Cloud COC Skill Smoke Test")
    parser.add_argument('--ak', required=True, help='Huawei Cloud Access Key')
    parser.add_argument('--sk', required=True, help='Huawei Cloud Secret Key')
    parser.add_argument('--region', default='cn-north-4', help='COC service region')
    args = parser.parse_args()

    print("=" * 60)
    print("Huawei Cloud COC Skill Smoke Test")
    print("=" * 60)

    ak = args.ak
    sk = args.sk
    region = args.region

    # Test credentials
    if not test_credentials(ak, sk, region):
        return

    # Test list scripts
    test_list_scripts(ak, sk, region)

    # Test create script
    script_uuid = test_create_script(ak, sk, region)
    if not script_uuid:
        return

    # Test execute script (requires real instance, skipped by default)
    # test_execute_script(ak, sk, region, script_uuid)

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
    print(f"\nCreated script UUID: {script_uuid}")
    print("\nNote: Script execution requires real target instance information")


if __name__ == "__main__":
    main()
