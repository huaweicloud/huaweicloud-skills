# IAM Permission Policies - Huawei Cloud OBS Object Storage Statistics

IAM permission policies required for this skill.

## Required Permissions Overview

| Operation | IAM Action (Legacy v3) | IAM Action (New v5) | Description |
|-----------|----------------------|---------------------|-------------|
| List buckets | `obs:bucket:ListAllMyBuckets` | `obs:bucket:listAllMyBuckets` | List all buckets in the current account |
| Get bucket storage info | `obs:bucket:GetBucketStorageInfo` | `obs:bucket:getBucketStorageInfo` | Get bucket capacity and object count |
| Get bucket attributes | `obs:bucket:GetBucketMetadata` | `obs:bucket:getBucketMetadata` | Get bucket metadata |
| List objects | `obs:bucket:ListBucket` | `obs:bucket:listBucket` | List objects in bucket |
| Query CES metrics | `ces:metric:get` | `ces:metric:get` | Query CES monitoring metrics |

---

## Minimum Required Policy (JSON)

### Legacy IAM (v3 API - Role and Policy Authorization)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:ListAllMyBuckets",
        "obs:bucket:GetBucketStorageInfo",
        "obs:bucket:GetBucketMetadata",
        "obs:bucket:ListBucket",
        "ces:metric:get"
      ]
    }
  ]
}
```

### New IAM (v5 API - Identity Policy Authorization)

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:listAllMyBuckets",
        "obs:bucket:getBucketStorageInfo",
        "obs:bucket:getBucketMetadata",
        "obs:bucket:listBucket",
        "ces:metric:get"
      ],
      "Resource": [
        "OBS:*:*:bucket:*",
        "CES:*:*:metric:*"
      ]
    }
  ]
}
```

---

## Resource-Level Policy (Recommended)

Restrict to specific buckets for enhanced security:

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:listAllMyBuckets",
        "obs:bucket:getBucketStorageInfo",
        "obs:bucket:getBucketMetadata",
        "obs:bucket:listBucket"
      ],
      "Resource": [
        "OBS:*:*:bucket:<BucketName>",
        "OBS:*:*:object:<BucketName>/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ces:metric:get"
      ],
      "Resource": [
        "CES:*:*:metric:*"
      ]
    }
  ]
}
```

---

## Read-Only Policy

For viewing bucket info and monitoring data only (no upload allowed):

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:listAllMyBuckets",
        "obs:bucket:getBucketStorageInfo",
        "obs:bucket:getBucketMetadata",
        "obs:bucket:listBucket",
        "ces:metric:get"
      ],
      "Resource": [
        "OBS:*:*:bucket:*",
        "CES:*:*:metric:*"
      ]
    }
  ]
}
```

---

## System Policies

Use Huawei Cloud pre-built system policies for simplified authorization:

| System Policy | Included Permissions | Use Case |
|--------------|---------------------|----------|
| `OBS ReadOnlyAccess` | Bucket and object read-only | ✅ Recommended for this skill |
| `OBS Administrator` | Full OBS permissions | ⚠️ Overly permissive, not recommended |
| `CES ReadOnlyAccess` | CES read-only | View monitoring metrics |

**Recommended combination:** `OBS ReadOnlyAccess` + `CES ReadOnlyAccess`

> **⚠️ OBS ReadOnlyAccess notes**
>
> OBS ReadOnlyAccess includes bucket and object read-only permissions, which aligns with this skill's statistics-only scope.
> This skill does not support upload or delete operations.

---

## Bucket Policy Authorization

In addition to IAM policies, you can also authorize via Bucket Policy:

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"ID": ["<IAMUserId>"]},
      "Action": [
        "obs:bucket:ListBucket",
        "obs:bucket:GetBucketStorageInfo"
      ],
      "Resource": [
        "my-bucket",
        "my-bucket/*"
      ]
    }
  ]
}
```

---

## Policy Best Practices

1. **Least privilege principle**: Grant only the minimum required permissions; prefer resource-level policies
2. **Read-only access**: This skill only queries bucket info and monitoring data; policies should not include write or delete permissions
3. **OBS ReadOnlyAccess recommended**: Among system policies, OBS ReadOnlyAccess best matches this skill's requirements
4. **CES data access**: Querying monitoring metrics requires CES ReadOnlyAccess
5. **Regular review**: Periodically review IAM policies to ensure no excess permissions

---

## References

- [OBS IAM Authorization](https://support.huaweicloud.com/perms-cfg-obs/obs_40_0001.html)
- [Creating IAM Custom Policies](https://support.huaweicloud.com/usermanual-iam/iam_01_0605.html)
- [OBS Bucket Policy Configuration](https://support.huaweicloud.com/usermanual-obs/obs_03_0123.html)
- [CES IAM Authorization](https://support.huaweicloud.com/api-ces/ces_03_0046.html)
