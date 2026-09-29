# IAM Permission Policies

Ensure the IAM user has the **read-only** permissions required to perform CDN domain ownership verification diagnosis.

## Minimum Required Permissions

| Permission | Description |
|------------|-------------|
| `cdn:*:query*` | All CDN query-class actions used by this skill: `ListDomains/v2`, `ShowVerifyDomainOwnerInfo` |
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
- If permission denied errors occur, contact the account administrator to grant permissions
- DNS TXT probes via `scripts/dns_txt_probe.py` and HTTP file probes via `scripts/file_probe.py` are unauthenticated network reads and **do not need IAM**; the only IAM-scoped operations are the `hcloud CDN Show*` queries above. (This rewording replaces the former note about `dig` not needing IAM; the IAM scope is unchanged.)

## Permission-to-Command Mapping

| Command | Required Permission |
|---------|---------------------|
| `hcloud CDN ListDomains/v2` | `cdn:*:query*` (explicitly: `cdn:configuration:queryDomains`) |
| `hcloud CDN ShowVerifyDomainOwnerInfo` | `cdn:*:query*` |
| `python scripts/dns_txt_probe.py --name <dns_query_name>` | _(none — unauthenticated DNS read; no IAM scope)_ |
| `python scripts/file_probe.py --url <file_verify_url>` | _(none — unauthenticated HTTP read; no IAM scope)_ |
