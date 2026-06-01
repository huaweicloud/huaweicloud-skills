# Common Pitfalls & Solutions

This document contains detailed troubleshooting guides for common issues encountered when using the Huawei Cloud SWR Image Governance skill.

## Pitfall 1: Array-Style Permission Parameters

**Symptom**: `CreateNamespaceAuth` or `CreateUserRepositoryAuth` fails with parameter validation error

**Root Cause**: Permission operations use array-style parameters with index notation `--[N].auth`, `--[N].user_id`, `--[N].user_name` where `[N]` starts from 1 (not 0)

**Common Mistakes**:
- ❌ `--auth=7 --user_id=xxx --user_name=xxx` — missing array index
- ❌ `--0.auth=7 --0.user_id=xxx` — using 0-based index
- ❌ `--auth[0]=7` — wrong bracket syntax

**Solution**: Always use 1-based array index:

```bash
# ✅ CORRECT - Single user with index 1
hcloud SWR CreateNamespaceAuth --namespace=pancake --1.auth=7 --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4

# ✅ CORRECT - Multiple users with sequential indices
hcloud SWR CreateNamespaceAuth --namespace=pancake --1.auth=7 --1.user_id=xxx --1.user_name=user1 --2.auth=3 --2.user_id=yyy --2.user_name=user2 --cli-region=cn-north-4

# ❌ WRONG - Missing array index
hcloud SWR CreateNamespaceAuth --namespace=pancake --auth=7 --user_id=xxx --user_name=user1 --cli-region=cn-north-4
```

## Pitfall 2: Auth Value Confusion (7/3/1, Not 1/2/3)

**Symptom**: User receives unexpected permission level after granting auth

**Root Cause**: SWR auth values use 7/3/1 encoding, NOT a sequential 1/2/3 scale

**Auth Value Mapping**:
- `7` = Manage (full control: create/delete repos, manage permissions)
- `3` = Edit (push and pull images)
- `1` = Read (pull images only)

**Common Mistakes**:
- ❌ `--1.auth=1` when intending "manage" — actually grants "read only"
- ❌ `--1.auth=2` — invalid value, there is no auth level 2

**Solution**: Always use the correct auth values:

| Intent          | Auth Value | Description              |
| --------------- | ---------- | ------------------------ |
| Full control    | `7`        | Manage all resources     |
| Push/pull       | `3`        | Edit (push and pull)     |
| Pull only       | `1`        | Read (pull only)         |

## Pitfall 3: self_auth vs others_auths Confusion

**Symptom**: Permission audit appears incomplete, missing users

**Root Cause**: `ShowNamespaceAuth` and `ShowUserRepositoryAuth` return `self_auth` (your own permission) as a separate object from `others_auths` (other users' permissions)

**Solution**: When auditing permissions, check both objects:

```json
{
  "self_auth": {
    "user_id": "...",
    "user_name": "...",
    "auth": 7
  },
  "others_auths": [
    {
      "user_id": "...",
      "user_name": "...",
      "auth": 7
    }
  ]
}
```

- `self_auth`: Your permission level (always present)
- `others_auths`: Other users' permissions (may be empty array `[]`)
- To get complete access list, combine both

## Pitfall 4: Domain Timestamp Field Names (created/updated, NOT created_at/updated_at)

**Symptom**: Parsing `created_at` or `updated_at` from `ListRepoDomains` response fails

**Root Cause**: `ListRepoDomains` uses `created` and `updated` fields, NOT `created_at` and `updated_at`

**Solution**: Use the correct field names:

```json
{
  "created": "2026-04-28T09:18:19.830309Z",
  "updated": "2026-04-28T09:18:19.83031Z"
}
```

| Operation          | Timestamp Fields          |
| ------------------ | ------------------------- |
| `ListRepoDomains`  | `created`/`updated` (**NOT** `created_at`/`updated_at`) |
| `ShowAccessDomain` | `created`/`updated`       |

## Pitfall 5: Nested Array Parameters for Retention Rules

**Symptom**: `CreateRetention` fails with parameter validation error

**Root Cause**: Retention rules use deeply nested array parameters: `--rules.[N].tag_selectors.[N].kind`

**Common Mistakes**:
- ❌ `--rules.tag_selectors.kind=label` — missing both array indices
- ❌ `--rules.1.tag_selectors.kind=label` — missing inner array index
- ❌ `--rules.1.tag_selectors.0.kind=label` — using 0-based inner index

**Solution**: Use 1-based indices for both outer and inner arrays:

```bash
# ✅ CORRECT - Proper nested array format
hcloud SWR CreateRetention --namespace=pancake --repository=openclaw-sandbox \
  --algorithm=or \
  --rules.1.template=tag_rule \
  --rules.1.params.num=10 \
  --rules.1.tag_selectors.1.kind=label \
  --rules.1.tag_selectors.1.pattern=latest \
  --cli-region=cn-north-4

# ❌ WRONG - Missing inner index
hcloud SWR CreateRetention --namespace=pancake --repository=openclaw-sandbox \
  --algorithm=or \
  --rules.1.template=tag_rule \
  --rules.1.params.num=10 \
  --rules.1.tag_selectors.kind=label \
  --cli-region=cn-north-4
```

## Pitfall 6: Retention params Format (String Values, Not Numbers)

**Symptom**: `CreateRetention` fails because `params` expects string values

**Root Cause**: The `--rules.[N].params` parameter expects string values for `days` and `num`, not numeric integers

**Solution**: Use string values in params:

```bash
# ✅ CORRECT - String values
--rules.1.params.num=10
--rules.1.params.days=30

# Note: hcloud CLI accepts numeric-looking strings; the API expects string format
```

## Pitfall 7: Agency Not Configured Before Using Sync/Trigger Features

**Symptom**: Image sync or CCE trigger features fail with agency-related errors

**Root Cause**: SWR agency delegation must be configured before features like image sync (to OBS) and CCE trigger deployments can work

**Solution**: Check and configure agency before using dependent features:

```bash
# Check agency status first
hcloud SWR CheckAgency --cli-region=cn-north-4

# If is_agency is false, create the delegation
hcloud SWR CreateAgency --cli-region=cn-north-4

# Then verify
hcloud SWR CheckAgency --cli-region=cn-north-4
```

## Pitfall 8: Namespace Permission Affects ALL Repositories Under It

**Symptom**: Granting namespace manage permission unintentionally gives full control of all repositories

**Root Cause**: Namespace-level permissions apply to ALL repositories under that namespace. Repository-level permissions are more granular.

**Solution**: Choose the right permission scope:

- **Namespace permission**: When the user needs access to all repositories under the namespace
- **Repository permission**: When the user only needs access to specific repositories

```bash
# For broad access (all repos in namespace)
hcloud SWR CreateNamespaceAuth --namespace=pancake --1.auth=3 --1.user_id=xxx --1.user_name=dev-user --cli-region=cn-north-4

# For granular access (specific repo only)
hcloud SWR CreateUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --1.auth=3 --1.user_id=xxx --1.user_name=dev-user --cli-region=cn-north-4
```

## Pitfall 9: Deleting Namespace Permission Removes Repository Access

**Symptom**: After revoking namespace permission, user also loses repository access under that namespace

**Root Cause**: Namespace permission is the foundation for repository access. Removing namespace access can cascade to repository access loss.

**Solution**: Before revoking namespace permissions, check if the user has separate repository-level permissions that should be preserved:

```bash
# Check repository-level permissions for the user
hcloud SWR ShowUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4
```

## Pitfall 10: Empty Retention List Returns Flat Empty Array

**Symptom**: Attempting to parse `ListRetentions` response as an object with a wrapper key fails

**Root Cause**: When no retention rules exist, `ListRetentions` returns a flat empty array `[]`, not an object like `{"retentions": []}`

**Solution**: Handle both empty array and populated array cases:

```json
// Empty result (no rules)
[]

// When rules exist, format to be verified with actual API call
```

## Pitfall 11: ListRepoAccessories Returns Object with Null Field

**Symptom**: Accessing `accessories` as a guaranteed array fails when it's null

**Root Cause**: `ListRepoAccessories` returns `{"total": 0, "accessories": null}` when no accessories exist, not an empty array

**Solution**: Handle null `accessories` field:

```json
{
  "total": 0,
  "accessories": null
}
```

Always check `total` first, and treat `accessories` as nullable.

## Common Error Response Reference

| Error Code          | HTTP Status | Description                  | Recommended Action                    |
| ------------------- | ----------- | ---------------------------- | ------------------------------------- |
| `SWR.001`           | 400         | Invalid parameter            | Check parameter format and rules      |
| `SWR.002`           | 404         | Resource not found           | Verify resource exists first          |
| `SWR.003`           | 409         | Resource already exists      | Use Show operation to check           |
| `SWR.004`           | 403         | Permission denied            | Check IAM policies                    |
| `SWR.005`           | 403         | Quota exceeded               | Check quotas, clean up or apply       |
| `SWR.006`           | 401         | Authentication failed        | Regenerate login credentials          |
| `SWR.007`           | 429         | Too many requests            | Add delay, reduce request rate        |