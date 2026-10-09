# Verification Method

How to verify the `huawei-cloud-account-onboarding` skill end to end.

## Environment Setup

```bash
pip install huaweicloudsdkbss
# Credentials must exist in the environment (main-account AK/SK):
#   HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK
# Fallback: HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY
# Corporate intranet: export HTTPS_PROXY=http://your-proxy:port
```

Verify credentials are visible to the scripts (prints key names only, never values):

```bash
python3 -c "import os; print('AK set' if os.environ.get('HUAWEICLOUD_SDK_AK') or os.environ.get('HUAWEI_ACCESS_KEY') else 'AK missing'); print('SK set' if os.environ.get('HUAWEICLOUD_SDK_SK') or os.environ.get('HUAWEI_SECRET_KEY') else 'SK missing')"
```

## Functional Test Cases

### TC-01 — Query real-name auth status

```bash
cd <skill-dir>
python3 scripts/show_real_name_auth_status.py
```

**Expected**: exit code `0` and one JSON line:

```json
{"verified_status": 2, "verified_type": 0}
```

- `verified_status` must be one of `-1, 0, 1, 2`.
- `verified_type` must be `0` or `1` (may be `null` when `verified_status == -1`).

### TC-02 — Get face real-name auth QR code

```bash
cd <skill-dir>
python3 scripts/show_real_name_auth_qr_code.py
```

**Expected**: exit code `0` and one JSON line:

```json
{"qr_code_url": "https://auth.huaweicloud.com/authui/thirdLogin?idp=CHNIDP&..."}
```

- `qr_code_url` must start with `https://` and point to a Huawei Cloud auth page.
- If the account is a **sub-account**, the API returns `CBC.99007297` (this API is
  main-account only). The script reports this documented, expected outcome as a
  structured JSON result and **still exits `0`**:

  ```json
  {"qr_code_url": null, "error_code": "CBC.99007297", "message": "...", "hint": "ShowRealNameAuthQrCode is main-account only. Use main-account AK/SK ..."}
  ```

### TC-03 — Missing credentials (negative)

```bash
python3 scripts/show_real_name_auth_status.py --missing-creds-check
```

**Expected**: exit code `0` with a JSON summary confirming the graceful-error
contract — the script exits `2` with a clear `AK/SK not found` message and no
traceback when every credential env var is stripped. This self-test flag exists
so the missing-credential path can be verified even in environments where
credentials are already set.

### TC-04 — Read-only guarantee

Both scripts issue only `GET` requests (`/v2/customers/real-name-auth-status`,
`/v2/customers/real-name-auth-qrcode`). Verify by code review that no Create/Update/Delete methods
are invoked and no identity data (ID number, photos) is ever collected or transmitted.

## Specification Compliance

Run the Huawei Cloud skill specification validator from the repo root:

```bash
BASE_REF=origin/master bash ~/.agents/skills/huawei-cloud-skill-creator/scripts/validate-skill.sh skills/bss/billing/huawei-cloud-account-onboarding
```

All Critical and High checks must pass; WARN-only findings accepted after review.