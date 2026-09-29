# IAM Permission Policies

Ensure the IAM user has the **read-only** permissions required to perform CDN traffic analysis.

## Minimum Required Permissions

| Permission | Description |
|------------|-------------|
| `cdn:*:query*` | All CDN query-class actions used by this skill: `ListDomains/v2`, `ShowDomainStats/v2`, `ShowBandwidthCalc` |
| `cdn:configuration:queryDomains` | List CDN domains (`ListDomains/v2`) — listed explicitly alongside the wildcard |
| `cdn:configuration:queryChargeMode` | Query the billing mode (`ShowChargeModes`) — listed explicitly alongside the wildcard |

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
        "cdn:configuration:queryChargeMode"
      ],
      "Resource": "*"
    }
  ]
}
```

## Read-Only Declaration

This skill is strictly read-only. It only invokes CDN query-class operations (the
`cdn:*:query*` scope plus the explicitly listed `cdn:configuration:queryDomains`
and `cdn:configuration:queryChargeMode`) and never requests any create / update /
delete / refresh / ban action. Because no write action is ever requested, no
`Deny` statement is needed.

## Notes

- `scripts/cdn_timestamp.py` is a pure local timestamp calculation and needs no IAM permission
- If using a sub-account, ensure the sub-account has the above permissions
- If permission denied errors occur, contact the account administrator to grant permissions

## Permission-to-Command Mapping

| Command | Required Permission |
|---------|---------------------|
| `hcloud CDN ShowChargeModes` | `cdn:configuration:queryChargeMode` (also covered by `cdn:*:query*`) |
| `hcloud CDN ListDomains/v2` | `cdn:configuration:queryDomains` (also covered by `cdn:*:query*`) |
| `hcloud CDN ShowDomainStats/v2` | `cdn:*:query*` |
| `hcloud CDN ShowBandwidthCalc` | `cdn:*:query*` |
| `python scripts/cdn_timestamp.py` | _(none — local calculation; no IAM scope)_ |
