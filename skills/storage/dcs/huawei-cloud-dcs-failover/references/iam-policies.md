# IAM Policy Description

Minimum permission set required for the DCS master-slave failover drill. **Authorization items verified against Huawei Cloud DCS permission management docs.**

## Required Permissions

| Permission | Description | Required |
|------------|-------------|----------|
| `dcs:instance:list` | List DCS instances | ✅ |
| `dcs:instance:get` | Get DCS instance detail | ✅ |
| `dcs:instance:getNodes` | Get master-slave node info (ShowNodesInformation) | ✅ |
| `dcs:instance:modify` | Execute DCS master-slave failover (ChangeMasterStandby) | ✅ |
| `dcs:backup:list` | List backup records (risk assessment - backup freshness check) | ✅ |
| `ces:metricData:get` | Query CES monitoring metric data | optional |

> 📌 `dcs:instance:modify` is the core permission for failover. The IAM check has two paths:
>
> - **Custom policies**: deep-checked via `GetPolicyV5` `policy_document` — precisely inspects
>   `Statement.Action` for `dcs:instance:modify` with `Allow`/`Deny` effect. This is an exact check.
> - **System policies**: `GetPolicyV5` does not return `policy_document` for system policies, so
>   name-based inference is used. Only precise system policy names are matched:
>   `dcsfullaccess`, `dcssysaccess`, `administratoraccess`. Narrowly scoped system policies
>   (e.g. `TenantAdminReadOnlyAccess`) are **not** matched, avoiding false positives.
>
> Three states: `allow` / `deny` / `unknown` (advisory, non-blocking). When system policy inference
> fires, the matched policy name is printed so the user knows it is inferred, not verified.
> The actual API call (`ChangeMasterStandby`) is the real enforcement — IAM check is advisory only.

## Policy Template

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dcs:instance:modify",
        "dcs:instance:getNodes"
      ],
      "Resource": [
        "dcs:<region>:<domainId>:instance:<instanceId>"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dcs:instance:list",
        "dcs:instance:get",
        "dcs:backup:list",
        "ces:metricData:get"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}
```

Replace `<region>`, `<domainId>`, `<instanceId>` with actual values to narrow the resource scope.

## Configuration Method

1. Create a custom policy in the IAM console, paste the above template
2. Grant the policy to the IAM user/group that will run the drill
3. Verify: `hcloud DCS ListInstances --cli-region=cn-south-1`
