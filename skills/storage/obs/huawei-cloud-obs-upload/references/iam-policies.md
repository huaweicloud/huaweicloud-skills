# IAM Permission Policies - Huawei Cloud OBS Object Storage Management

IAM permission policies required by this skill.

## Required Permissions Overview

| Operation | IAM Action (Legacy v3) | IAM Action (New v5) | Description |
|-----------|----------------------|---------------------|-------------|
| List buckets | `obs:bucket:ListAllMyBuckets` | `obs:bucket:listAllMyBuckets` | List all buckets for the current account |
| Get bucket storage info | `obs:bucket:GetBucketStorageInfo` | `obs:bucket:getBucketStorageInfo` | Get bucket capacity and object count |
| Get bucket metadata | `obs:bucket:GetBucketMetadata` | `obs:bucket:getBucketMetadata` | Get bucket metadata |
| Upload object | `obs:object:PutObject` | `obs:object:putObject` | Upload object to bucket |
| List objects | `obs:bucket:ListBucket` | `obs:bucket:listBucket` | List objects in bucket |

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
        "obs:object:PutObject",
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
        "obs:object:putObject",
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

Restrict to specific buckets for improved security:

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
        "obs:object:putObject",
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

Only view bucket information and monitoring data (no upload allowed):

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

You can use Huawei Cloud preset system policies to simplify authorization:

| System Policy | Included Permissions | Applicable Scenario |
|--------------|---------------------|---------------------|
| `OBS OperateAccess` | Bucket and object read/write (no delete) | ✅ Recommended for this skill |
| `OBS ReadOnlyAccess` | Bucket and object read-only | View-only scenarios |
| `OBS Administrator` | Full OBS permissions | ⚠️ Overly permissive, not recommended |
| `CES ReadOnlyAccess` | CES read-only permissions | View monitoring metrics |

**Recommended combination:** `OBS OperateAccess` + `CES ReadOnlyAccess`

> **⚠️ OBS OperateAccess note**
>
> OBS OperateAccess includes bucket and object read/write permissions but **does not include delete permissions**,
> which aligns with this skill's "no delete" security constraint. Recommended for use.

---

## Bucket Policy Authorization

In addition to IAM policies, you can also authorize via bucket policies:

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"ID": ["<IAMUserId>"]},
      "Action": [
        "obs:bucket:ListBucket",
        "obs:bucket:GetBucketStorageInfo",
        "obs:object:PutObject"
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
2. **No delete permissions**: This skill prohibits delete operations; policies should not include delete permissions
3. **Recommend OBS OperateAccess**: Among system policies, OBS OperateAccess best matches this skill's requirements
4. **CES data access**: Querying monitoring metrics requires CES ReadOnlyAccess
5. **Regular review**: Periodically review IAM policies to ensure no excessive permissions

---

## Official Documentation

- [OBS IAM Authorization](https://support.huaweicloud.com/perms-cfg-obs/obs_40_0001.html)
- [Create IAM Custom Policy](https://support.huaweicloud.com/usermanual-iam/iam_01_0605.html)
- [OBS Bucket Policy Configuration](https://support.huaweicloud.com/usermanual-obs/obs_03_0123.html)
- [CES IAM Authorization](https://support.huaweicloud.com/api-ces/ces_03_0046.html)
