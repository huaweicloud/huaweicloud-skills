# Task: Quota Management

## Overview

SWR has resource quotas that limit the number of namespaces, repositories, and image tags you can create. This task covers checking quota usage and limits.

## Operations Catalog

| Operation    | Method | Description              | Key Parameters                    |
| ------------ | ------ | ------------------------ | --------------------------------- |
| `ListQuotas` | GET    | 获取配额信息             | `--project_id`                    |

## Workflows

### W1: Check Quota Usage

```bash
hcloud SWR ListQuotas --cli-region=cn-north-4
```

**Response Structure** (verified against actual API - array of quota objects):

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

**Output Fields**:
- `quota_key`: Resource type identifier (`namespace`, `repo`, `tag`, etc.)
- `quota_limit`: Maximum allowed for this resource type
- `used`: Current usage count
- `unit`: Unit of measurement (typically empty string for count-based quotas)
- Response is an **array of quota objects** (not flat key-value pairs like `namespace_limit`/`namespace_used`)

### W2: Check Quota Before Creating Resources

Before creating namespaces, repositories, or tags, verify quota availability:

```bash
# Check quotas
hcloud SWR ListQuotas --cli-region=cn-north-4

# If namespace quota is near limit, consider cleanup:
# - List all namespaces
hcloud SWR ListNamespaces --cli-region=cn-north-4

# - Delete unused namespaces (CAUTION: removes all repos under them)
hcloud SWR DeleteNamespaces --namespace=unused-ns --cli-region=cn-north-4
```

### W3: Storage Management via Tag Cleanup

When tag quota is near limit, clean up old tags:

```bash
# 1. Check current tag quota
hcloud SWR ListQuotas --cli-region=cn-north-4

# 2. Find repositories with most tags (order_column uses "tag_count", response field is "num_images")
hcloud SWR ListReposDetails --order_column=tag_count --order_type=desc --cli-region=cn-north-4

# 3. For repositories with many tags, list and delete old ones
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --order_column=updated_at --order_type=asc --cli-region=cn-north-4

# 4. Delete old tags
hcloud SWR DeleteRepoTag --namespace=group-dev --repository=nginx --tag=v0.1-beta --cli-region=cn-north-4
```

## Default Quota Limits (Reference)

| Resource     | Default Limit | Notes                          |
| ------------ | ------------- | ------------------------------ |
| Namespaces   | 100           | Per project                    |
| Repositories | 5000          | Per project, across all namespaces |
| Tags         | 50000         | Per project, across all repositories |

**Note**: Default limits may vary by region and project configuration. Always use `ListQuotas` to check actual limits.

## Common Scenarios

### S1: Quota Audit for Resource Planning

Regularly audit quota usage for resource planning:

```bash
# Check quotas
hcloud SWR ListQuotas --cli-region=cn-north-4

# List namespace count
hcloud SWR ListNamespaces --cli-region=cn-north-4

# List repository count by namespace
hcloud SWR ListReposDetails --limit=1000 --cli-region=cn-north-4

# Calculate tag usage per namespace
# For each namespace:
hcloud SWR ListReposDetails --namespace=group-dev --cli-region=cn-north-4
# Then for each repo:
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --cli-region=cn-north-4
```

### S2: Apply for Quota Increase

If quotas are insufficient:

1. Document current usage with `ListQuotas`
2. Calculate required increase based on project needs
3. Contact Huawei Cloud support to apply for quota increase
4. Provide justification: project name, expected growth, timeline