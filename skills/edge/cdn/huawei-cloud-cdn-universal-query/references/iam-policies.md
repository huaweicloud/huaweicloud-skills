# IAM Permission Policies

Ensure the IAM user has the **read-only** permissions required to perform CDN query operations.

## Minimum Required Permissions

| Permission | Description |
|------------|-------------|
| `cdn:*:query*` | All CDN query-class actions used by this skill (the 45 GET APIs: domain / configuration / statistics / template / rule / tag / refresh-task queries) |
| `cdn:configuration:queryDomains` | List CDN domains (`ListDomains/v2`) — listed explicitly alongside the wildcard |
| `cdn:configuration:queryChargeMode` | Query the billing mode (`ShowChargeModes`) — listed explicitly alongside the wildcard |
| `cdn:log:*` | CDN log query and download scope (`ShowLogs/v2` plus log file download) |
| `cdn:statistics:downloadExcel` | Statistics Excel export (`DownloadStatisticsExcel`, `DownloadRegionCarrierExcel`) |

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
        "cdn:configuration:queryChargeMode",
        "cdn:log:*",
        "cdn:statistics:downloadExcel"
      ],
      "Resource": "*"
    }
  ]
}
```

## Read-Only Declaration

This skill is strictly read-only with respect to CDN configuration. It only invokes
query-class operations (the `cdn:*:query*` scope), the log query/download scope
(`cdn:log:*`), and the statistics Excel export (`cdn:statistics:downloadExcel`); it
never requests any create / update / delete / refresh / ban action. Because no
configuration-changing action is ever requested, no `Deny` statement is needed.

## Notes

- `cdn:*:query*` covers all 45 GET APIs used by this skill — no create/update/delete permission is needed
- `cdn:log:*` and `cdn:statistics:downloadExcel` are listed separately because their action names do not start with `query`
- If using a sub-account, ensure the sub-account has the above permissions
- If permission denied errors occur, contact the account administrator to grant permissions
