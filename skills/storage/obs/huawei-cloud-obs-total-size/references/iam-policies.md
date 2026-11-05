# IAM Policies

## Least-Privilege Policy for OBS Total Size Querying

This skill is read-only and needs permission to list buckets and list objects so it can compute total size. The minimal IAM actions are:

- `obs:bucket:ListAllMyBuckets` — list all buckets under the account
- `obs:bucket:ListBucket` — list objects (with prefix/delimiter) in the bucket
- `obs:object:List` — list objects in the bucket

### Policy JSON

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:ListAllMyBuckets",
        "obs:bucket:ListBucket",
        "obs:object:List"
      ],
      "Resource": [
        "OBS:*:*:bucket:*",
        "OBS:*:*:object:*"
      ]
    }
  ]
}
```

### Alternative: Predefined Role

Huawei Cloud provides the `OBS ReadOnlyAccess` role which grants read-only access to OBS buckets and objects, including bucket/object listing. Use it when fine-grained policy management is not required.

### Notes

- No `obs:bucket:CreateBucket`, `obs:bucket:DeleteBucket`, `obs:object:PutObject`, `obs:object:DeleteObject`, or other write/delete actions are included — this skill never modifies resources.
- The `obsutil` tool itself is configured with AK/SK/endpoint via `~/.obsutilconfig`; the IAM policy above governs what those credentials are allowed to do.
