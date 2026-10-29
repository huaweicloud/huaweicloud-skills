#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import importlib
import subprocess
import shutil
from pathlib import Path


MIN_PYTHON_VERSION = (3, 10)

IMPORT_NAME_MAP = {
    "python-dotenv": "dotenv",
}


def _get_import_name(pkg_name):
    return IMPORT_NAME_MAP.get(pkg_name, pkg_name.replace("-", "_"))


def check_python_version():
    current = sys.version_info[:3]
    if current[:2] < MIN_PYTHON_VERSION:
        print(f"[FAIL] Python version {sys.version} < {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}")
        return False
    print(f"[OK] Python version: {sys.version}")
    return True


def check_dependencies():
    req_file = Path(__file__).resolve().parent.parent / "requirements.txt"
    if not req_file.exists():
        print(f"[FAIL] requirements.txt not found: {req_file}")
        return False

    with open(req_file, "r", encoding="utf-8") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not requirements:
        print("[OK] No dependencies in requirements.txt")
        return True

    missing = []
    for req in requirements:
        pkg_name = req.split("==")[0].split(">=")[0].split("<=")[0].split(">")[0].split("<")[0].strip()
        try:
            importlib.import_module(_get_import_name(pkg_name))
        except ImportError:
            missing.append(req)

    if missing:
        print(f"[FAIL] Missing dependencies: {', '.join(missing)}")
        print(f"  Run: pip install -r {req_file}")
        return False

    print(f"[OK] All dependencies installed ({len(requirements)} packages)")
    return True


def check_hcloud_cli():
    """检查 hcloud CLI 是否可用且凭据已配置"""
    hcloud_path = shutil.which("hcloud")
    if not hcloud_path:
        print("[FAIL] hcloud CLI not found in PATH")
        print("  Please install hcloud CLI: https://support.huaweicloud.com/cli/"
              "usermanual-hcli/hcli_01_0001.html")
        return False

    print(f"[OK] hcloud CLI found: {hcloud_path}")

    # 检查凭据是否已配置
    try:
        result = subprocess.run(["hcloud", "configure", "list"],
                                capture_output=True, text=True, timeout=10)
        if result.returncode != 0 or not result.stdout.strip():
            print("[WARN] hcloud credentials not configured")
            print("  Run: hcloud configure set")
            print("  Or set HW_ACCESS_KEY / HW_SECRET_KEY environment variables")
            return False
        print("[OK] hcloud credentials configured")
        return True
    except Exception as e:
        print(f"[WARN] Could not verify hcloud credentials: {e}")
        print("  If commands fail later, run: hcloud configure set")
        return True

def main():
    print("=== Environment Check ===")
    all_ok = True

    if not check_python_version():
        all_ok = False

    if not check_dependencies():
        all_ok = False

    if not check_hcloud_cli():
        all_ok = False

    print("========================")
    if all_ok:
        print("Environment check PASSED")
    else:
        print("Environment check FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
