# IAM Permission Policies

Ensure the IAM user has the **read-only** permissions required to perform CDN origin diagnosis.

## Minimum Required Permissions

| Permission | Description |
|------------|-------------|
| `cdn:*:query*` | All CDN query-class actions used by this skill: `ListDomains/v2`, `ShowDomainDetailByName`, `ShowDomainFullConfig/v2` |
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

- `cdn:*:query*` covers the domain details query and the origin configuration query (`configs.sources` returned by `ShowDomainFullConfig/v2`)
- The origin connectivity probe (`scripts/origin_probe.py`) is an unauthenticated HTTP/HTTPS network read; it does **not** require any IAM permission and does not call any Huawei Cloud API
- If using a sub-account, ensure the sub-account has the above permissions
- If you encounter a permission-denied error, contact the primary account administrator to grant permissions

## Error Symptoms When Permissions Are Insufficient

| Scenario | Error Code | Prompt |
|----------|------------|--------|
| Missing `cdn:*:query*` | 403 | No permission to query domain details or domain configuration |
| Invalid AK/SK | 401 | Authentication failed |

## Permission-to-Command Mapping

| Command | Required Permission |
|---------|---------------------|
| `hcloud CDN ListDomains/v2` | `cdn:*:query*` (explicitly: `cdn:configuration:queryDomains`) |
| `hcloud CDN ShowDomainDetailByName` | `cdn:*:query*` |
| `hcloud CDN ShowDomainFullConfig/v2` | `cdn:*:query*` |
| `python scripts/origin_probe.py --scheme <scheme> --host <host> --port <port>` | _(none — unauthenticated HTTP/HTTPS read; no IAM scope)_ |
