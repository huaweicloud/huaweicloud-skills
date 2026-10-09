# Related Commands & API Reference

Quick reference for the two BSS real-name authentication APIs used by this skill.

## API Summary (verified from huaweicloudsdkbss 3.1.214 `_http_info`)

| Operation | SDK method | HTTP method | Resource path |
| ----------- | ----------- | ------------- | --------------- |
| ShowRealNameAuthStatus | `show_real_name_auth_status` | GET | `/v2/customers/real-name-auth-status` |
| ShowRealNameAuthQrCode | `show_real_name_auth_qr_code` | GET | `/v2/customers/real-name-auth-qrcode` |

- **Endpoint**: `https://bss.myhuaweicloud.com` (fixed region `cn-north-1`, SDK `BssRegion.CN_NORTH_1`)
- **Auth**: Customer main-account AK/SK via `GlobalCredentials` (BSS is a global service — do not use `BasicCredentials`)
- **Official docs**:
  - ShowRealNameAuthStatus: https://support.huaweicloud.com/api-oce/mac_00006.html
  - ShowRealNameAuthQrCode: https://support.huaweicloud.com/api-oce/mac_00005.html

## Response Fields

### ShowRealNameAuthStatus

| Field             | Type | Values                  | Meaning                                            |
|-------------------|------|-------------------------|----------------------------------------------------|
| `verified_status` | int  | `-1` / `0` / `1` / `2`  | not verified / under review / rejected / verified  |
| `verified_type`   | int  | `0` / `1` / `null`      | personal / enterprise / null when not verified     |

### ShowRealNameAuthQrCode

| Field         | Type   | Meaning                                                   |
|---------------|--------|-----------------------------------------------------------|
| `qr_code_url` | string | Face real-name auth QR URL; single-use, expires in 10 min |

## Error Codes

| Code | Meaning | Guidance |
| ------ | --------- | ---------- |
| `CBC.0151` | Access denied | Check AK/SK validity |
| `CBC.99007297` | Sub-account has no permission for QR code | Use main-account AK/SK |
| `CBC.0100` | Invalid parameter | Check request parameters |
| `CBC.0999` | Other error | Contact Huawei Cloud support |
| network error | Connection failure | Set `HTTPS_PROXY` |

## Command Quick Reference

```bash
# Query real-name auth status
python3 scripts/show_real_name_auth_status.py

# Get face real-name auth QR code (main account only)
python3 scripts/show_real_name_auth_qr_code.py
```

## Related Skills (deliberately not invoked)

- `huawei-cloud-billing-scout` — customer BSS billing queries (balances, bills, coupons). Complementary, different scope.
- `huawei-cloud-partner-scout` — partner-account (渠道伙伴) billing. Uses partner AK/SK; this skill uses customer AK/SK.

These skills are referenced by name only for disambiguation; this skill never calls into them.