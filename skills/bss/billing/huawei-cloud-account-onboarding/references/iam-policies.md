# IAM Policies — BSS Real-Name Authentication Read-Only

This skill performs exactly two read-only BSS operations on the customer account. Grant the
**least privilege** required: only query permissions, no write actions.

## Recommended Policy JSON

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bss:realNameAuth:view"
      ],
      "Resource": ["*"]
    }
  ]
}
```

> **Note on action names**: the exact IAM action strings for BSS real-name authentication queries
> (`ShowRealNameAuthStatus` / `ShowRealNameAuthQrCode`) are granted through the BSS read-only
> permission set. If the exact action token above is not recognized by your IAM console, use the
> built-in **"BSS ReadOnlyAccess"** (客户运营能力只读权限) system policy instead — it covers both
> real-name auth queries and all other read-only BSS operations without granting any write ability.

## Alternative: Use System Policy

The simplest least-privilege approach is attaching the built-in read-only system policy:

| Policy | Scope | Suitable |
| -------- | ------- | ---------- |
| `BSS ReadOnlyAccess` | All BSS read-only APIs incl. real-name auth queries | ✅ Recommended |
| `BSS Administrator` | Full BSS access — **too broad, do not use** | ❌ |
| `CBC Operator` / partner policies | Partner-account operations — wrong account type | ❌ |

## Security Rules

- **Credentials**: AK/SK are read from environment variables (`HUAWEICLOUD_SDK_AK` /
  `HUAWEICLOUD_SDK_SK`) at runtime. Never hardcode credentials in scripts, docs, or config.
- **Account type**: use customer (non-partner) credentials. Partner-account AK/SK will not work
  with these two customer APIs.
- **Main account only**: `ShowRealNameAuthQrCode` requires main-account permissions; sub-account
  calls return `CBC.99007297`. The script treats this documented outcome as expected: it prints a
  structured JSON result (`error_code: "CBC.99007297"`) and exits `0` instead of crashing, so the
  agent can guide the user to switch to main-account AK/SK.
- **No write permission is required or granted** — the two operations are strictly `GET` (Show).