# IAM Permission Policies

Ensure the IAM user has the **read-only** permissions required to perform CDN DNS resolution diagnosis.

## Minimum Required Permissions

| Permission | Description |
|------------|-------------|
| `cdn:*:query*` | All CDN query-class actions used by this skill: `ListDomains/v2`, `ShowDomainDetailByName`, `ShowIpInfo/v2` |
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
- If permission denied errors occur, contact the primary account administrator to grant permissions
- `ShowIpInfo/v2` (IP attribution) is a query-class CDN read interface and is covered by the `cdn:*:query*` scope — no separate IP-information action is required
- `dns_resolve.py` is a local DNS query probe (A-record resolution via `dnspython`) and does not need IAM permissions; it performs unauthenticated network reads against the system DNS resolver

## Permission-to-Command Mapping

| Command | Required Permission |
|---------|---------------------|
| `hcloud CDN ListDomains/v2` | `cdn:*:query*` (explicitly: `cdn:configuration:queryDomains`) |
| `hcloud CDN ShowDomainDetailByName` | `cdn:*:query*` |
| `hcloud CDN ShowIpInfo/v2` | `cdn:*:query*` |
| `python scripts/dns_resolve.py --domain <domain>` | _(none — local DNS query; no IAM scope)_ |
