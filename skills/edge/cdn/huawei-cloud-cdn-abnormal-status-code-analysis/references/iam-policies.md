# IAM Permission Policies

Ensure the IAM user has the **read-only** permissions required to perform CDN
abnormal status-code diagnosis. This skill is read-only end to end; it never
requires write/delete permissions.

## Minimum Required Permissions

| Permission | Description |
|------------|-------------|
| `cdn:*:query*` | All CDN query-class actions used by this skill: `ListDomains/v2`, `ShowDomainStats/v2`, `ShowBandwidthCalc`, the Top-N family, `ListDomainClientStats`, `ShowDomainFullConfig/v2`, `ShowIpInfo/v2`, `ListBanUrl`, `ListAccessControlTask`, and the refresh/preheat task queries |
| `cdn:configuration:queryDomains` | List CDN domains (`ListDomains/v2`) — listed explicitly alongside the wildcard |
| `cdn:log:*` | CDN access-log query and download scope (`ShowLogs/v2` plus the log file download used by log forensics) |

## Policy Example

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cdn:*:query*",
        "cdn:configuration:queryDomains",
        "cdn:log:*"
      ],
      "Resource": "*"
    }
  ]
}
```

## Read-Only Declaration

This skill is strictly read-only. It only invokes CDN query-class operations (the
`cdn:*:query*` scope plus `cdn:configuration:queryDomains`) and the log
query/download scope (`cdn:log:*`); it never requests any create / update /
delete / refresh / ban action. Because no write action is ever requested, no
`Deny` statement is needed.

## Special Notes

- `ListBanUrl` / `ListAccessControlTask` require a separate 工单 (support
  ticket) whitelist ("not in the whitelist" / `CDN.0004`); they are still
  query-class GET operations, not write ops. If blocked, record the error and
  proceed; do **not** attempt to bypass.
- The Python log helper `scripts/fetch_cdn_log.py` performs an unauthenticated
  read-only HTTP download of a presigned CDN log link returned by
  `ShowLogs/v2`; it does **not** need IAM and accepts no credentials.
- If a query returns `CDN.0004` (permission / not in whitelist) or a 403, ask the
  account administrator to grant the three read-only actions above. **Never**
  request or elevate to a write action.

## Permission-to-Command Mapping

| Command | Required Permission |
|---------|---------------------|
| `hcloud CDN ListDomains/v2` | `cdn:configuration:queryDomains` (also covered by `cdn:*:query*`) |
| `hcloud CDN ShowDomainStats/v2` | `cdn:*:query*` |
| `hcloud CDN ShowBandwidthCalc` | `cdn:*:query*` |
| `hcloud CDN ListCdnDomainTop*` / `ListDomainClientStats` | `cdn:*:query*` |
| `hcloud CDN ShowDomainFullConfig/v2` / `ShowIpInfo/v2` | `cdn:*:query*` |
| `hcloud CDN ShowLogs/v2` | `cdn:log:*` |
| `python scripts/fetch_cdn_log.py --url <link>` | _(none — unauthenticated download of a presigned link; no IAM scope)_ |
