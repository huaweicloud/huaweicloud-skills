# IAM Permission Notes

This skill requires **read-only** permission on the Huawei Cloud account, covering two data backends:
- `hcloud CES` queries Cloud Eye monitoring data (`ListMetrics` / `BatchListMetricData`) — the vast majority of metrics;
- `hcloud AOM` queries Application Operations Management data (`ListSample` / `ListSeries` / `ListMetricItems` / `ListMetadataAomPromGet` / `ListLabelValuesAomPromGet`) — CCE and other cloud-native metrics (entries in metrics.json with `"backend": "aom"`).

The skill never creates, modifies, or deletes any resource.

## Recommended: system-managed policies

Grant the collection account the built-in **`CES ReadOnlyAccess`** (Cloud Eye read-only) + **`AOM ReadOnlyAccess`** (Application Operations Management read-only); that covers all collection operations.

## Minimal custom policy (example)

For least privilege, refer to the following Action list (actual actions available in the IAM console take precedence):

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ces:listMetrics",
        "ces:batchListMetricData",
        "aom:metric:list",
        "aom:metric:get"
      ],
      "Resource": ["*"]
    }
  ]
}
```

> Notes:
> - `ces:BatchListMetricData` is the core API CES uses to collect peak/valley values; `ces:ListMetrics` is used by the connectivity self-check (`smoke`).
> - The AOM monitoring query APIs (ListSample/ListSeries/ListMetricItems, etc.) all require
>   `aom:metric:list` (which depends on `aom:metric:get`); accounts have it by default; IAM users need it granted in a custom policy.

## Permissions NOT needed

- No management permissions for ECS/RDS/ELB/CCE resources (the skill only queries monitoring data by instance ID; it does not operate clusters/nodes/PODs);
- No billing, IAM administration, or enterprise-project permissions;
- For diagnosing region permission errors only: the console may show messages like `The IAM user is forbidden in the currently selected region`,
  meaning the account lacks the corresponding read-only permission in that region; grant it in IAM.