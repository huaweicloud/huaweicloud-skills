# KooCLI Installation & Configuration Guide

This skill executes via the **huaweicloudsdkbss Python SDK**, not via hcloud CLI commands. The
reason: as of **KooCLI 7.2.12** (latest checked 2026-09-11), hcloud reports
`Unsupported service: BSS` — the BSS service is not present in the CLI's service metadata
(`~/.hcloud/metaRepo/services_en.json`, 150 services, BSS absent). This guide explains how to
install/update hcloud so you can confirm this for yourself, and how to install the SDK used by
this skill.

## 1. Install / Upgrade KooCLI (hcloud)

```bash
# Install (Linux x86_64/ARM64)
# Download the official installer and verify its SHA256 checksum before executing
# (pinned checksum below; do not pipe remote scripts directly into bash).
curl -fsSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o /tmp/hcloud_install.sh
echo "cd2c99bf92861ee5760c72e07bfa51f46d990d3e0e8411f12d69e32f1981cdf2  /tmp/hcloud_install.sh" | sha256sum -c - || { echo "installer checksum mismatch — aborting"; exit 1; }
bash /tmp/hcloud_install.sh

# Or upgrade an existing installation
hcloud update
```

Verify the version and check whether BSS is supported:

```bash
hcloud version
hcloud BSS ShowRealNameAuthStatus --help
# If you see "[USE_ERROR]Unsupported service: BSS", the CLI does not support BSS in your version.
```

## 2. Configure hcloud AK/SK (for general Huawei Cloud CLI use)

```bash
hcloud configure set --cli-profile=default --cli-mode=AKSK \
  --cli-access-key=<YOUR_AK> --cli-secret-key=<YOUR_SK> --cli-region=cn-north-1
```

> `--cli-lang=cn` is required by some BSS-facing tools; set it with
> `hcloud configure set --cli-lang=cn` if needed.

## 3. Install the Python SDK used by this skill

```bash
pip install huaweicloudsdkbss
```

Verify the exact API paths this skill relies on (must match the SDK source, never inferred):

```bash
python3 - <<'PY'
from huaweicloudsdkbss.v2 import (
    BssClient,
    ShowRealNameAuthStatusRequest,
    ShowRealNameAuthQrCodeRequest,
)

for req in (ShowRealNameAuthStatusRequest(), ShowRealNameAuthQrCodeRequest()):
    if isinstance(req, ShowRealNameAuthStatusRequest):
        info = BssClient._show_real_name_auth_status_http_info(req)
    else:
        info = BssClient._show_real_name_auth_qr_code_http_info(req)
    # resource_path values below come straight from the SDK source (authoritative)
    print(info["method"], info["resource_path"])
PY
```

Expected output (the REST paths this skill relies on):

```text
GET /v2/customers/real-name-auth-status
GET /v2/customers/real-name-auth-qrcode
```

## 4. Set environment credentials (used by the skill scripts)

```bash
export HUAWEICLOUD_SDK_AK=<YOUR_AK>      # main-account Access Key
export HUAWEICLOUD_SDK_SK=<YOUR_SK>      # main-account Secret Key
# Corporate intranet proxy, if required:
export HTTPS_PROXY=http://your-proxy:port
```

## 5. Troubleshooting

| Symptom | Cause / fix |
| --------- | ------------- |
| `Unsupported service: BSS` | hcloud metadata lacks BSS in this version; use the SDK scripts (this skill's default mode) |
| `CBC.0151` | AK/SK invalid or insufficient permission — check credentials |
| `CBC.99007297` | Sub-account calling QR API — switch to main-account AK/SK |
| Network timeout | Corporate proxy required — set `HTTPS_PROXY` |