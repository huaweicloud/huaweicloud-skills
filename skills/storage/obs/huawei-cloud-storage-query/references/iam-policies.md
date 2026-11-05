# IAM Permission Policies - Huawei Cloud Storage Query

IAM permission policies required for this skill.

This skill is a **read-only** storage resource query skill covering EVS (cloud disks),
OBS (object storage), SFS (file systems) and CBR (backups). All operations are query
operations only; no permission to create, modify or delete resources is required.

## Required Permissions Overview

| Service | IAM Action (Legacy v3) | IAM Action (New v5) | Description |
|---------|----------------------|---------------------|-------------|
| EVS | `evs:volumes:list` | `evs:volumes:list` | List cloud disks |
| EVS | `evs:volumes:get` | `evs:volumes:get` | Get cloud disk details |
| EVS | `evs:snapshots:list` | `evs:snapshots:list` | List volume snapshots |
| EVS | `evs:snapshots:get` | `evs:snapshots:get` | Get snapshot details |
| EVS | `evs:quotas:get` | `evs:quotas:get` | Get volume/snapshot quotas |
| EVS | `evs:types:get` | `evs:types:get` | Get volume types |
| EVS | `evs:recycles:get` | `evs:recycles:get` | Get recycle bin information |
| OBS | `obs:bucket:ListAllMyBuckets` | `obs:bucket:listAllMyBuckets` | List buckets |
| OBS | `obs:bucket:GetBucketMetadata` | `obs:bucket:getBucketMetadata` | Get bucket metadata (ACL, policy, tags, notification) |
| OBS | `obs:object:ListObjects` | `obs:object:listObject` | List objects in a bucket |
| OBS | `obs:object:GetObject` | `obs:object:getObject` | Get object metadata/content |
| SFS | `sfsturbo:shares:list` | `sfsturbo:shares:list` | List file systems |
| SFS | `sfsturbo:shares:get` | `sfsturbo:shares:get` | Get file system details |
| SFS | `sfsturbo:tasks:list` | `sfsturbo:tasks:list` | List file system tasks |
| CBR | `cbr:vaults:list` | `cbr:vaults:list` | List backup vaults |
| CBR | `cbr:vaults:get` | `cbr:vaults:get` | Get vault details |
| CBR | `cbr:backups:list` | `cbr:backups:list` | List backups |
| CBR | `cbr:policies:list` | `cbr:policies:list` | List backup policies |
| CBR | `cbr:protectables:list` | `cbr:protectables:list` | List protectable resources |

---

## Minimum Required Policy (JSON)

### New IAM (v5 API - Identity Policy Authorization)

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "evs:volumes:list",
        "evs:volumes:get",
        "evs:snapshots:list",
        "evs:snapshots:get",
        "evs:quotas:get",
        "evs:types:get",
        "evs:recycles:get",
        "obs:bucket:ListAllMyBuckets",
        "obs:bucket:GetBucketMetadata",
        "obs:object:ListObjects",
        "obs:object:GetObject",
        "sfsturbo:shares:list",
        "sfsturbo:shares:get",
        "sfsturbo:tasks:list",
        "cbr:vaults:list",
        "cbr:vaults:get",
        "cbr:backups:list",
        "cbr:policies:list",
        "cbr:protectables:list"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}
```

### Legacy IAM (v3 API - Role and Policy Authorization)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "evs:volumes:list",
        "evs:volumes:get",
        "evs:snapshots:list",
        "evs:snapshots:get",
        "evs:quotas:get",
        "evs:types:get",
        "evs:recycles:get",
        "obs:bucket:ListAllMyBuckets",
        "obs:bucket:GetBucketMetadata",
        "obs:object:ListObjects",
        "obs:object:GetObject",
        "sfsturbo:shares:list",
        "sfsturbo:shares:get",
        "sfsturbo:tasks:list",
        "cbr:vaults:list",
        "cbr:vaults:get",
        "cbr:backups:list",
        "cbr:policies:list",
        "cbr:protectables:list"
      ],
      "Resource": [
        "*"
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
| `EVS ReadOnlyAccess` | EVS read-only permissions | Query cloud disks |
| `OBS ReadOnlyAccess` | OBS read-only permissions | Query buckets/objects |
| `SFS ReadOnlyAccess` | SFS read-only permissions | Query file systems |
| `CBR ReadOnlyAccess` | CBR read-only permissions | Query backups/vaults |

**Recommended combination:** `EVS ReadOnlyAccess` + `OBS ReadOnlyAccess` + `SFS ReadOnlyAccess` + `CBR ReadOnlyAccess`

> **Note:** When project-level read-only policies are unavailable in an account,
> a custom policy containing only the read actions listed above is also acceptable
> and follows the least-privilege principle.

---

## Notes

1. This skill performs query operations only. Do not grant any write permissions
   (`*:create`, `*:delete`, `*:update`) to the calling account unless required by
   other tasks.
2. Some APIs return `403` due to service-level feature restrictions (for example,
   the EVS recycle bin feature must be enabled in the console first). This is not
   an IAM permission problem; see the corresponding `guide.md` notes.