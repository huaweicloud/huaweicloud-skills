# IAM Policies — Huawei Cloud OBS Lifecycle Management

Least-privilege IAM permissions for lifecycle rule management. All policies below use the **least privilege** required for each capability tier. Manage operations require write access to the
lifecycle configuration; Query/Analyze require only read access.

## 1. Query + Analyze Only (R3) — read-only policy

Covers: `huawei_list_obs_lifecycle_rules`, `huawei_get_obs_lifecycle_rule`, `huawei_list_obs_objects`, `huawei_diagnose_obs_lifecycle`, `huawei_analyze_obs_lifecycle_cost`, `huawei_preview_obs_lifecycle`.

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:GetLifecycleConfiguration",
        "obs:bucket:GetBucketLocation",
        "obs:bucket:GetBucketStorage",
        "obs:object:ListObject",
        "obs:bucket:ListAllMyBuckets"
      ],
      "Resource": "*"
    }
  ]
}
```

> `obs:object:ListObject` grants `ListBucket`/`ListBucketVersions` on objects (prefix-restricted via bucket policy if needed).

## 2. Query + Manage (R2/R1) — adds lifecycle write

Covers additionally: `huawei_create_obs_lifecycle_rule`, `huawei_update_obs_lifecycle_rule`, `huawei_delete_obs_lifecycle_rule`.

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:GetLifecycleConfiguration",
        "obs:bucket:PutLifecycleConfiguration",
        "obs:bucket:GetBucketLocation",
        "obs:bucket:GetBucketStorage",
        "obs:object:ListObject",
        "obs:bucket:ListAllMyBuckets"
      ],
      "Resource": "*"
    }
  ]
}
```

## 3. Scoped to a single bucket (recommended production hardening)

Replace `Resource` with the specific bucket ARN to restrict all operations to one bucket:

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:GetLifecycleConfiguration",
        "obs:bucket:PutLifecycleConfiguration",
        "obs:bucket:GetBucketLocation",
        "obs:object:ListObject"
      ],
      "Resource": [
        "obs:*:*:*:bucket:my-bucket",
        "obs:*:*:*:object:my-bucket/*"
      ]
    }
  ]
}
```

## Permissions mapping

| Skill action | IAM action | Resource |
|--------------|-----------|----------|
| list/get lifecycle rules | `obs:bucket:GetLifecycleConfiguration` | bucket |
| create/update/delete lifecycle rule | `obs:bucket:PutLifecycleConfiguration` | bucket |
| list objects | `obs:object:ListObject` | bucket + objects |
| analyze cost (bucket stat) | `obs:bucket:GetBucketStorage`, `obs:bucket:GetBucketLocation` | bucket |
| list buckets | `obs:bucket:ListAllMyBuckets` | account |

## Notes

- Lifecycle configuration management does **not** require object write/delete permissions — the object expiration/transition itself is executed by the OBS service, not by the caller.
- IAM policy syntax follows the Huawei Cloud IAM custom policy (JSON) format; apply via the IAM console or `IAM` APIs.
- For temporary credentials (STS), the same `Action` list applies; the OBS endpoint accepts an `X-Security-Token` (obsutil `-t={token}`).