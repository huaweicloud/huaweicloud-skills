# IAM Permission Policies - Huawei Cloud OBS Directory Count

IAM permission policies required for this skill. This skill is **read-only** — it only
lists buckets and objects to count directories, so its IAM needs are minimal.

## Required Permissions Overview

| Operation | IAM Action (Legacy v3) | IAM Action (New v5) | Description |
|-----------|------------------------|---------------------|-------------|
| List buckets | `obs:bucket:ListAllMyBuckets` | `obs:bucket:listAllMyBuckets` | List buckets in the current account |
| List objects | `obs:bucket:ListBucket` | `obs:bucket:listBucket` | List objects/directories in a bucket |
| Get bucket attributes | `obs:bucket:GetBucketMetadata` | `obs:bucket:getBucketMetadata` | Read bucket metadata |

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
        "obs:bucket:ListBucket",
        "obs:bucket:GetBucketMetadata"
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
        "obs:bucket:listBucket",
        "obs:bucket:getBucketMetadata"
      ],
      "Resource": [
        "OBS:*:*:bucket:*",
        "OBS:*:*:object:*"
      ]
    }
  ]
}
```

---

## Resource-Level Policy (Recommended)

Restrict to the specific buckets the user needs to inspect:

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:listAllMyBuckets",
        "obs:bucket:getBucketMetadata",
        "obs:bucket:listBucket"
      ],
      "Resource": [
        "OBS:*:*:bucket:<BucketName>",
        "OBS:*:*:object:<BucketName>/*"
      ]
    }
  ]
}
```

---

## System Policy

| System Policy | Included Permissions | Use Case |
|---------------|----------------------|----------|
| `OBS ReadOnlyAccess` | Bucket and object read-only | ✅ Recommended for this skill |
| `OBS Administrator` | Full OBS permissions | ⚠️ Overly permissive, not recommended |

**Recommended:** attach `OBS ReadOnlyAccess` to the IAM user/role used with this skill.

---

## Policy Best Practices

1. **Least privilege**: grant only the read actions above; this skill never writes.
2. **Read-only only**: never grant `obs:bucket:PutBucket`, `obs:object:PutObject`,
   `obs:object:DeleteObject`, `obs:bucket:DeleteBucket` or any `rm`/write permission.
3. **Resource-level scope** where possible: restrict to the buckets actually inspected.
4. **Regular review**: periodically confirm the credential has no excess permissions.

---

## References

- [OBS IAM Authorization](https://support.huaweicloud.com/perms-cfg-obs/obs_40_0001.html)
- [Creating IAM Custom Policies](https://support.huaweicloud.com/usermanual-iam/iam_01_0605.html)
- [OBS Bucket Policy Configuration](https://support.huaweicloud.com/usermanual-obs/obs_03_0123.html)