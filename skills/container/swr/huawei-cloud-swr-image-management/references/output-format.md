# SWR Output Format Reference

This document describes the JSON response formats for SWR API commands.

## Output Format

### Namespace List

```json
{
  "namespaces": [
    {
      "id": 3827347,
      "name": "group-dev",
      "creator_name": "user-name",
      "auth": 7,
      "access_user_count": 1,
      "repo_count": 2
    }
  ]
}
```

### Repository List

Response is a flat JSON array (not wrapped in an object):

```json
[
  {
    "name": "nginx",
    "category": "app_server",
    "description": "Nginx web server",
    "size": 268435456,
    "is_public": true,
    "num_images": 5,
    "num_download": 120,
    "path": "swr.cn-north-4.myhuaweicloud.com/group-dev/nginx",
    "internal_path": "swr.cn-north-4.myhuaweicloud.com/group-dev/nginx",
    "namespace": "group-dev",
    "domain_name": "user-name",
    "tags": ["v1.0", "v1.1", "latest"],
    "created_at": "2026-04-15T10:30:00Z",
    "updated_at": "2026-05-20T14:20:00Z",
    "logo": "",
    "url": "",
    "status": false,
    "total_range": 2
  }
]
```

**Note**: `num_images` is the tag count (not `tag_count`). `tags` is an array of tag name strings included directly in the repository listing.

### Tag List

Response is a flat JSON array (not wrapped in an object):

```json
[
  {
    "id": 32962315,
    "repo_id": 3374895,
    "Tag": "v1.0",
    "image_id": "f47c82866a20...",
    "digest": "sha256:c8cede14b121...",
    "schema": 2,
    "size": 134217728,
    "path": "swr.cn-north-4.myhuaweicloud.com/group-dev/nginx:v1.0",
    "internal_path": "swr.cn-north-4.myhuaweicloud.com/group-dev/nginx:v1.0",
    "is_trusted": false,
    "created": "2026-04-15T10:30:00Z",
    "updated": "2026-05-20T14:20:00Z",
    "domain_id": "xxx",
    "scanned": false,
    "tag_type": 0
  }
]
```

**Note**: Tag name field is `Tag` (capital T), timestamps use `created`/`updated` (not `created_at`/`updated_at`).

### Tag Detail (ShowRepoTag)

Response is a single JSON object (not an array):

```json
{
  "id": 32962315,
  "repo_id": 3374895,
  "tag": "v1.0",
  "image_id": "f47c82866a20...",
  "manifest": "{\"schemaVersion\":2,...}",
  "digest": "sha256:c8cede14b121...",
  "schema": 2,
  "size": 134217728,
  "path": "swr.cn-north-4.myhuaweicloud.com/group-dev/nginx:v1.0",
  "internal_path": "swr.cn-north-4.myhuaweicloud.com/group-dev/nginx:v1.0",
  "is_trusted": false,
  "created": "2026-04-15T10:30:00Z",
  "updated": "2026-05-20T14:20:00Z",
  "domain_id": "xxx",
  "tag_type": 0
}
```

**Note**: `ShowRepoTag` returns `"tag"` (lowercase), while `ListRepositoryTags` returns `"Tag"` (capital T). Both use `created`/`updated` timestamps. `ShowRepoTag` also includes `manifest` and `digest` fields not present in list responses.

### Show Repository Details

```json
{
  "id": 3374887,
  "ns_id": 3827347,
  "name": "nginx",
  "category": "other",
  "creator_id": "05949eb5...",
  "creator_name": "user-name",
  "num_images": 17,
  "num_download": 35,
  "is_public": false,
  "path": "swr.cn-north-4.myhuaweicloud.com/group-dev/nginx",
  "created": "2026-03-26T07:42:40Z",
  "updated": "2026-05-06T09:22:11Z",
  "domain_id": "05949eb4...",
  "priority": 0
}
```

**Note**: ShowRepository uses `created`/`updated` and `num_images` — **different** from ListReposDetails which uses `created_at`/`updated_at`.

### Auth Token Response

```json
{
  "auths": {
    "swr.cn-north-4.myhuaweicloud.com": {
      "auth": "base64-encoded-username:password"
    }
  }
}
```

**Note**: The `auth` field is base64-encoded. Decode it to get docker login credentials. This is a Docker config format, NOT a header+body response.

### Quota List

```json
{
  "quotas": [
    {
      "quota_key": "namespace",
      "quota_limit": 5,
      "used": 1,
      "unit": ""
    }
  ]
}
```

**Note**: Quotas are returned as an **array of objects** with `quota_key`/`quota_limit`/`used`/`unit` fields, not flat key-value pairs like `namespace_limit`/`namespace_used`.
