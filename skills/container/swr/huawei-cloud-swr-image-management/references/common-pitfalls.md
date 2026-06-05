# Common Pitfalls & Solutions

This document contains detailed troubleshooting guides for common issues encountered when using the Huawei Cloud SWR Image Management skill.

## Pitfall 1: Invalid Namespace Name Format

**Symptom**: API returns error `400 Bad Request` or `NamespaceNameInvalid`

**Root Cause**: Namespace name violates naming rules

**Naming Rules**:
- Start with lowercase letter
- Followed by lowercase letters, digits, dots (`.`), underscores (`_`), or hyphens (`-`)
- Max 2 consecutive underscores (`__` is allowed, `___` is not)
- Dots, underscores, hyphens cannot be directly connected (e.g., `a._b`, `a.-b` are invalid)
- End with lowercase letter or digit
- Length: 1-64 characters

**Common Mistakes**:
- ❌ `Group-dev` — starts with uppercase
- ❌ `dev___ops` — 3 consecutive underscores
- ❌ `dev.-ops` — dot directly followed by hyphen
- ❌ `dev._ops` — dot directly followed by underscore
- ❌ `dev-` — ends with hyphen
- ❌ Very long names > 64 chars

**Solution**: Always verify namespace names before creation:

```bash
# Verify namespace exists (if checking existing name)
hcloud SWR ShowNamespace --namespace=<your-namespace> --cli-region=cn-north-4
```

## Pitfall 2: Invalid Repository Name Format

**Symptom**: API returns error `400 Bad Request` or `RepoNameInvalid`

**Root Cause**: Repository name violates naming rules

**Naming Rules**:
- Start with lowercase letter or digit
- Followed by lowercase letters, digits, dots (`.`), slashes (`/`), underscores (`_`), or hyphens (`-`)
- Max 2 consecutive underscores
- Dots, slashes, underscores, hyphens cannot be directly connected
- End with lowercase letter or digit
- Length: 1-128 characters

**Common Mistakes**:
- ❌ `MyApp` — starts with uppercase
- ❌ `my-app/` — ends with slash
- ❌ `my.app./v2` — dot directly followed by slash

**Solution**: Use consistent naming conventions, e.g., `my-app`, `backend/api-server`

## Pitfall 3: Deleting Namespace Removes All Repositories

**Symptom**: All repositories and images disappear after namespace deletion

**Root Cause**: `DeleteNamespaces` removes the entire namespace and all resources under it

**Solution**: Before deleting a namespace, always:

1. List all repositories in the namespace:
```bash
hcloud SWR ListReposDetails --namespace=<namespace> --cli-region=cn-north-4
```

2. Confirm with the user that they understand ALL repositories and images will be permanently deleted

3. If repositories need to be preserved, move them to another namespace first (via image sync or re-push)

## Pitfall 4: Cannot Delete Tag Without Namespace and Repository

**Symptom**: `DeleteRepoTag` fails with path parameter errors

**Root Cause**: All tag operations require both `--namespace` and `--repository` parameters

**Solution**: Always specify full path for tag operations:

```bash
# ✅ CORRECT
hcloud SWR DeleteRepoTag --namespace=group-dev --repository=nginx --tag=v1.0 --cli-region=cn-north-4

# ❌ WRONG - missing namespace
hcloud SWR DeleteRepoTag --repository=nginx --tag=v1.0 --cli-region=cn-north-4
```

## Pitfall 5: Retag (CreateRepoTag) Source Tag Does Not Exist

**Symptom**: `CreateRepoTag` returns 404 or validation error

**Root Cause**: The `--source_tag` must reference an existing tag in the same repository

**Solution**: Verify the source tag exists before retagging:

```bash
# Verify source tag exists
hcloud SWR ShowRepoTag --namespace=group-dev --repository=nginx --tag=v1.0 --cli-region=cn-north-4

# Then retag
hcloud SWR CreateRepoTag --namespace=group-dev --repository=nginx --source_tag=v1.0 --destination_tag=v1.0-stable --cli-region=cn-north-4
```

## Pitfall 6: Quota Exceeded When Creating Resources

**Symptom**: `CreateNamespace` or `CreateRepo` returns `403 Quota limit exceeded`

**Root Cause**: SWR has resource limits (namespace count, repository count, tag count)

**Solution**: Check quotas before creating resources:

```bash
hcloud SWR ListQuotas --cli-region=cn-north-4
```

If quota is exceeded, consider:
1. Delete unused namespaces/repositories/tags to free up quota
2. Apply for quota increase through Huawei Cloud support

## Pitfall 7: Docker Login Token Expired

**Symptom**: `docker push` or `docker pull` fails with authentication error

**Root Cause**: Temporary login token (`CreateAuthorizationToken`) expires after 12 hours

**Solution**: For different use cases:

- **Temporary access**: Regenerate token with `CreateAuthorizationToken`
- **CI/CD pipelines**: Use long-term credentials from `CreateSecret` (valid for 1 year)
- **Automated renewal**: Schedule regular token regeneration in your pipeline

```bash
# Regenerate temporary token
hcloud SWR CreateAuthorizationToken --cli-region=cn-north-4

# Get long-term credentials
hcloud SWR CreateSecret --cli-region=cn-north-4
```

## Pitfall 8: Pagination Required for Large Repositories

**Symptom**: Only first 100 tags or repositories are returned

**Root Cause**: Default `limit` is 100 for `ListReposDetails` and 100 for `ListRepositoryTags`

**Solution**: Use pagination parameters for large datasets:

```bash
# First page
hcloud SWR ListReposDetails --namespace=group-dev --limit=100 --offset=0 --cli-region=cn-north-4

# Second page
hcloud SWR ListReposDetails --namespace=group-dev --limit=100 --offset=100 --cli-region=cn-north-4

# Continue until all results are retrieved
```

## Pitfall 9: filter vs Direct Parameters Conflict

**Symptom**: `ListReposDetails` returns unexpected results when both `--filter` and `--namespace/--name/--category` are used

**Root Cause**: If both `--filter` and direct parameters (`--namespace`, `--name`, `--category`) are used, the direct parameters will be ignored and `--filter` takes precedence

**Solution**: Use either `--filter` OR direct parameters, not both:

```bash
# ✅ CORRECT - Use direct parameters
hcloud SWR ListReposDetails --namespace=group-dev --name=nginx --cli-region=cn-north-4

# ✅ CORRECT - Use filter for complex queries
hcloud SWR ListReposDetails --filter="namespace::group-dev|name::nginx|limit::20|offset::0" --cli-region=cn-north-4

# ❌ WRONG - Mixing both
hcloud SWR ListReposDetails --namespace=group-dev --filter="namespace::other-ns" --cli-region=cn-north-4
```

## Pitfall 10: --offset and --limit Must Be Used Together

**Symptom**: Pagination parameters are ignored when used individually

**Root Cause**: `--offset` and `--limit` must always be paired; using one without the other has no effect

**Solution**: Always use both pagination parameters:

```bash
# ✅ CORRECT
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --limit=50 --offset=0 --cli-region=cn-north-4

# ❌ WRONG - missing offset
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --limit=50 --cli-region=cn-north-4
```

## Pitfall 11: Tag Field Name is `Tag` (Capital T), Not `name`

**Symptom**: Tag listing query returns unexpected field structure, scripts that reference `name` field fail

**Root Cause**: The tag name field in `ListRepositoryTags` and `ShowRepoTag` response uses `Tag` (capital T), not lowercase `name`

**Solution**: Always use `Tag` (capital T) when parsing tag list responses:

```bash
# ✅ CORRECT - Use capital T
Tag: "v1.0"

# ❌ WRONG - lowercase name does not exist in response
name: "v1.0"
```

## Pitfall 12: Repository `num_images` vs `tag_count`

**Symptom**: Repository listing field `tag_count` not found, confusion between parameter name and response field name

**Root Cause**: The tag count field in repository listing and detail response is `num_images`, but the `--order_column` parameter value for sorting by tag count is `tag_count`. These are different!

**Solution**: Use `num_images` for the response field, but `tag_count` for the sort parameter:

```bash
# ✅ CORRECT - Response field is "num_images"
"num_images": 5

# ❌ WRONG - "tag_count" does not exist as a response field
"tag_count": 5

# ✅ CORRECT - order_column parameter uses "tag_count"
hcloud SWR ListReposDetails --order_column=tag_count --order_type=desc --cli-region=cn-north-4

# ❌ WRONG - order_column "num_images" causes error (SVCSTG.SWR.4001096)
hcloud SWR ListReposDetails --order_column=num_images --order_type=desc --cli-region=cn-north-4
```

## Pitfall 13: Timestamp Field Names Vary Between APIs

**Symptom**: Parsing `created_at`/`updated_at` from `ShowRepository` or tag listing fails

**Root Cause**: Different SWR API operations use different timestamp field names:
- `ListReposDetails`: uses `created_at` / `updated_at`
- `ShowRepository`: uses `created` / `updated` (**different!**)
- `ListRepositoryTags`: uses `created` / `updated`
- `ShowRepoTag`: uses `created` / `updated`

**Solution**: Check which API operation you're using and use the correct timestamp field names:

| Operation          | Timestamp Fields       |
| ------------------ | ---------------------- |
| `ListReposDetails` | `created_at`/`updated_at` |
| `ShowRepository`   | `created`/`updated` (**different**) |
| `ListRepositoryTags` | `created`/`updated` |
| `ShowRepoTag`      | `created`/`updated` |

## Pitfall 14: CreateAuthorizationToken Returns Docker Auth Config, Not Header+Body

**Symptom**: Looking for `X-Swr-Dockerlogin` header or `host` body field — they don't exist

**Root Cause**: `CreateAuthorizationToken` returns a Docker config auth object format, not separate header and body fields as documented in some older references

**Solution**: Parse the response as a Docker auth config:

```json
{
  "auths": {
    "swr.cn-north-4.myhuaweicloud.com": {
      "auth": "base64-encoded-username:password"
    }
  }
}
```

Decode the `auth` field to get username and password for docker login.

## Pitfall 15: ListQuotas Returns Array of Objects, Not Flat Key-Value

**Symptom**: Trying to access `namespace_limit` or `namespace_used` fields — they don't exist

**Root Cause**: `ListQuotas` returns an array of quota objects with `quota_key`/`quota_limit`/`used`/`unit` fields, not flat key-value pairs

**Solution**: Parse the quotas as an array and look up by `quota_key`:

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

To find namespace quota, filter the array where `quota_key == "namespace"`.

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