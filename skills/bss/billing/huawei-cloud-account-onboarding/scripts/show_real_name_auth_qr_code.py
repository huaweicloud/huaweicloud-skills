#!/usr/bin/env python3
"""Get Huawei Cloud face real-name authentication QR code URL (BSS ShowRealNameAuthQrCode).

Read-only. Requires customer MAIN-account AK/SK in environment variables:
  HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK (fallback: HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY)

Output: {"qr_code_url": str}
  QR code is single-use and auto-expires 10 minutes after issuance.
  ShowRealNameAuthQrCode is MAIN-account only: a sub-account call returns
  CBC.99007297, which is a documented, expected outcome (not a crash). The
  script reports it as a structured JSON result with qr_code_url=null and
  exits 0, so the agent can tell the user to use main-account AK/SK.
  Other errors still exit non-zero with a clear message.
"""
import json
import os
import sys

from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient, ShowRealNameAuthQrCodeRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion


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


def main():
    client = (
        BssClient.new_builder()
        .with_credentials(get_credentials())
        .with_region(BssRegion.CN_NORTH_1)
        .build()
    )
    try:
        resp = client.show_real_name_auth_qr_code(ShowRealNameAuthQrCodeRequest())
    except Exception as e:
        code = getattr(e, "error_code", None) or type(e).__name__
        if code == "CBC.99007297":
            # Documented, expected operational outcome: this API is
            # main-account only. Return a structured result (exit 0) so the
            # agent can act on it — tell the user to use main-account AK/SK —
            # instead of surfacing an opaque failure.
            print(json.dumps({
                "qr_code_url": None,
                "error_code": code,
                "message": str(e),
                "hint": "ShowRealNameAuthQrCode is main-account only. "
                        "Use main-account AK/SK (a sub-account gets CBC.99007297).",
            }))
            sys.exit(0)
        sys.stderr.write(f"ERROR: {code}: {e}\n")
        sys.exit(1)
    print(json.dumps({"qr_code_url": resp.qr_code_url}))


if __name__ == "__main__":
    main()