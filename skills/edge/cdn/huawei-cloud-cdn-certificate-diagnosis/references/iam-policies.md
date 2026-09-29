# IAM Permission Policies

Ensure the IAM user has the **read-only** permissions required to perform CDN certificate diagnosis.

## Minimum Required Permissions

| Permission | Description |
|------------|-------------|
| `cdn:*:query*` | All CDN query-class actions used by this skill: `ListDomains/v2`, `ShowDomainDetailByName`, `ShowCertificatesHttpsInfo/v2` |
| `cdn:configuration:queryDomains` | List CDN domains (`ListDomains/v2`) — listed explicitly alongside the wildcard |

## Policy Example

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cdn:*:query*",
        "cdn:configuration:queryDomains"
      ],
      "Resource": "*"
    }
  ]
}
```

## Read-Only Declaration

This skill is strictly read-only. It only invokes CDN query-class operations (the
`cdn:*:query*` scope plus `cdn:configuration:queryDomains`) and never requests any
create / update / delete / refresh / ban action. Because no write action is ever
requested, no `Deny` statement is needed.

## Notes

- When using a sub-account, ensure the sub-account has the above permissions
- If you encounter a permission-denied error, contact the primary account administrator to grant permissions
- `scripts/cert_probe.py` performs an unauthenticated TLS read against `<domain>:443`; `scripts/cert_expiry_check.py` is a pure local calculation. Neither calls a
  Huawei Cloud API, so neither needs any IAM permission
- **IAM scope unchanged from the previous (curl-based) version** of this skill — only the wording was updated to reflect the Python probe script

## Permission-to-Command Mapping

| Command | Required Permission |
|---------|---------------------|
| `hcloud CDN ListDomains/v2` | `cdn:*:query*` (explicitly: `cdn:configuration:queryDomains`) |
| `hcloud CDN ShowDomainDetailByName` | `cdn:*:query*` |
| `hcloud CDN ShowCertificatesHttpsInfo/v2` | `cdn:*:query*` |
| `python scripts/cert_probe.py --domain <domain> --timeout 10` | _(none — unauthenticated TLS read; no IAM scope)_ |
| `python scripts/cert_expiry_check.py --expiration_time <ms>` | _(none — pure local calculation; no IAM scope)_ |
