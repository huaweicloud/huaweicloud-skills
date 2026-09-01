# IAM Policies

## Summary

This skill does **not** require any IAM credentials or policies.

## Reason

The Huawei Cloud AI Gallery skill search API is a **public, read-only** endpoint. It does not require:

- AK/SK (Access Key / Secret Key)
- IAM tokens or session credentials
- Any form of authentication or authorization

## Security Notes

- The script only performs HTTP GET requests to public endpoints
- No cloud resources are created, modified, or deleted
- No credentials are stored, transmitted, or logged
- The script does not reference any environment variables prefixed with `HUAWEI_`, `HW_`, or `HWC_`

## Network Requirements

| Endpoint | Protocol | Purpose |
|----------|----------|---------|
| `devdata.huaweicloud.com` | HTTPS (443) | Huawei Cloud AI Gallery skills list API |

Ensure the Agent runtime has network access to the above endpoint.
