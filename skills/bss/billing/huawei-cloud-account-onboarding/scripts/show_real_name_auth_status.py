#!/usr/bin/env python3
"""Query Huawei Cloud real-name authentication status (BSS ShowRealNameAuthStatus).

Read-only. Requires customer main-account AK/SK in environment variables:
  HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK (fallback: HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY)

Output: {"verified_status": int, "verified_type": int|None}
  verified_status: -1 not verified, 0 under review, 1 rejected, 2 verified
  verified_type:   0 personal, 1 enterprise (None when not verified)

Optional self-test flag:
  --missing-creds-check  Re-run this script with all AK/SK env vars stripped
                         and verify the graceful-error contract: exit 2, a
                         clear "AK/SK not found" message, and no traceback.
                         Prints a JSON summary and exits 0 when the behavior
                         matches, 1 otherwise.
"""
import json
import os
import subprocess
import sys

from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient, ShowRealNameAuthStatusRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

# All credential env vars this skill honors (see get_credentials).
CRED_ENV_KEYS = (
    "HUAWEICLOUD_SDK_AK",
    "HUAWEICLOUD_SDK_SK",
    "HUAWEI_ACCESS_KEY",
    "HUAWEI_SECRET_KEY",
)


def get_credentials():
    ak = os.environ.get("HUAWEICLOUD_SDK_AK") or os.environ.get("HUAWEI_ACCESS_KEY")
    sk = os.environ.get("HUAWEICLOUD_SDK_SK") or os.environ.get("HUAWEI_SECRET_KEY")
    if not ak or not sk:
        sys.stderr.write(
            "ERROR: AK/SK not found. Set HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK "
            "(or HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY) in the environment.\n"
        )
        sys.exit(2)
    return GlobalCredentials(ak, sk)


def verify_missing_credentials():
    """Self-test the graceful missing-credential error path.

    Runs this same script in a subprocess with every AK/SK env var stripped and
    verifies the documented contract: exit code 2, a clear "AK/SK not found"
    message, and no traceback. Exits 0 when the behavior matches, 1 otherwise.
    """
    clean_env = {k: v for k, v in os.environ.items() if k not in CRED_ENV_KEYS}
    r = subprocess.run(
        [sys.executable, os.path.abspath(__file__)],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=60,
    )
    combined = (r.stdout or "") + (r.stderr or "")
    ok = r.returncode == 2 and "AK/SK not found" in combined and "Traceback" not in combined
    print(json.dumps({
        "missing_credentials_behavior": "ok" if ok else "unexpected",
        "expected": {"exit_code": 2, "message_contains": "AK/SK not found", "no_traceback": True},
        "actual": {"exit_code": r.returncode, "output": combined.strip()},
    }))
    return 0 if ok else 1


def main():
    if "--missing-creds-check" in sys.argv:
        sys.exit(verify_missing_credentials())
    client = (
        BssClient.new_builder()
        .with_credentials(get_credentials())
        .with_region(BssRegion.CN_NORTH_1)
        .build()
    )
    try:
        resp = client.show_real_name_auth_status(ShowRealNameAuthStatusRequest())
    except Exception as e:
        code = getattr(e, "error_code", None) or type(e).__name__
        sys.stderr.write(f"ERROR: {code}: {e}\n")
        sys.exit(1)
    print(json.dumps({"verified_status": resp.verified_status, "verified_type": resp.verified_type}))


if __name__ == "__main__":
    main()