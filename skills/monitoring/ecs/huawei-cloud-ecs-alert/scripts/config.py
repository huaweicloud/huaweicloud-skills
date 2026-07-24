#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified auth loader module - supports dual-standard env vars

Compatible with two environment variable standards.
Priority: new standard > old standard > hcloud CLI config

Usage:
    from config import load_credentials, get_hcloud_env_vars

    ak, sk, region, security_token = load_credentials()
    env_vars = get_hcloud_env_vars()
"""

import os
import subprocess
import sys


def load_credentials():
    """Load Huawei Cloud auth from environment variables.

    Returns:
        tuple: (ak, sk, region, security_token)

    Raises:
        SystemExit: exits when no valid auth found
    """
    # 1. Try new standard first
    ak = os.getenv("HW_ACCESS_KEY", "")
    sk = os.getenv("HW_SECRET_KEY", "")
    region = os.getenv("HW_REGION_NAME", "")
    security_token = os.getenv("HW_SECURITY_TOKEN", "")
    
    # 2. If not set, try old standard
    if not ak or not sk:
        ak = ak or os.getenv("HUAWEI_CLOUD_AK", "")
        sk = sk or os.getenv("HUAWEI_CLOUD_SK", "")
        region = region or os.getenv("HUAWEI_CLOUD_REGION", "")
    
    # 3. If still not set, try reading from hcloud CLI config
    if not ak or not sk:
        try:
            result = subprocess.run(
                ["hcloud", "configure", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # Parse hcloud configure list output
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if line.startswith("access_key_id"):
                        ak = line.split("=", 1)[1].strip()
                    elif line.startswith("secret_access_key"):
                        sk = line.split("=", 1)[1].strip()
                    elif line.startswith("region"):
                        if not region:
                            region = line.split("=", 1)[1].strip()
        except Exception:
            pass  # hcloud unavailable or config failed, continue
    
    # Set default region
    if not region:
        region = "cn-north-4"
    
    # Validate auth
    if not ak or not sk:
        print("[FAIL] Error: Authentication not configured", file=sys.stderr)
        print("Please run 'hcloud configure' or set environment variables.", file=sys.stderr)
        print("See SKILL.md for setup instructions.", file=sys.stderr)
        sys.exit(1)
    
    return ak, sk, region, security_token


def get_hcloud_env_vars():
    """Get env var dict for hcloud CLI.

    Returns:
        dict: env vars for hcloud CLI
    """
    ak, sk, region, _ = load_credentials()

    return {
        "HUAWEI_CLOUD_AK": ak,
        "HUAWEI_CLOUD_SK": sk,
        "HUAWEI_CLOUD_REGION": region
    }


def export_hcloud_env():
    """Export hcloud env vars to current process."""
    env_vars = get_hcloud_env_vars()
    for key, value in env_vars.items():
        os.environ[key] = value


if __name__ == "__main__":
    # Test mode: verify auth loading
    print("Testing auth loading...")
    try:
        ak, sk, region, token = load_credentials()
        print("[OK] Auth loaded successfully")
        print(f"   Region: {region}")
        if token:
            print("   STS: set")
        else:
            print("   STS: not set")
    except SystemExit as e:
        print(f"[FAIL] Auth loading failed: {e}")
        sys.exit(e.code)
