---
id: huawei-cloud-swr-image-governance
name: huawei-cloud-swr-image-governance
description: |
  Huawei Cloud SWR (Software Repository for Container) image governance skill using hcloud CLI.
  Use this skill when the user wants to: (1) manage SWR namespace permissions - grant/query/modify/revoke, (2) manage repository permissions - grant/query/modify/revoke, (3) manage image retention rules - create/list/update/delete, (4) manage shared download domains - create/list/update/delete, (5) manage image sharing - list shared repos/query feature gates, (6) check SWR agency status and create agency delegation, (7) list repo accessories and references.
  Trigger: user mentions "SWR image governance", "SWR 镜像治理", "SWR 权限管理", "SWR retention", "SWR 保留策略", "SWR 共享域名", "SWR 共享镜像", "SWR 委托", "SWR agency", "namespace permissions", "repository permissions", "镜像权限", "保留规则", "共享下载", "镜像分享"
tags: [swr, image-governance, permissions, retention, sharing]
version: 1.0.0
---

# Huawei Cloud SWR Image Governance

## Overview

This skill provides governance capabilities for Huawei Cloud SWR (Software Repository for Container) using the `hcloud` CLI, covering permissions, retention policies, sharing, and agency delegation.

**Architecture**: hcloud CLI → SWR Service API → Permission/Retention/Domain/Share/Agency resources

**Related Skills**:
- `huawei-cloud-swr-image-management` - Image lifecycle management (namespace, repo, tag, auth, quota)
- `huawei-cloud-swr-image-automation` - Image automation ops (sync, triggers, domains)
- `huawei-cloud-swr-enterprise-instance` - Enterprise instance management

**Capabilities**:
- Grant, query, modify, and revoke namespace-level permissions
- Grant, query, modify, and revoke repository-level permissions
- Create and manage image retention rules for automated cleanup
- Create and manage shared download domains for cross-organization access
- List shared repositories and check sharing feature gates
- Check and create agency delegation for SWR operations
- List repository accessories and references

**Typical Use Cases**:

- "Grant edit permission on namespace 'group-dev' to user 'dev-team'"
- "List all users with access to namespace 'group-dev'"
- "Set up a retention rule to keep only the last 10 tags in repository 'nginx'"
- "Create a shared download domain for repository 'my-app'"
- "List all shared repositories"
- "Check if image sharing feature is enabled"
- "Check agency delegation status for SWR"
- "Revoke a user's permission on a repository"

## Prerequisites

### 1. hcloud CLI Requirements (MANDATORY)

- hcloud CLI installed (version >= 7.2.2)
- Run `hcloud version` to verify installation
- First-time usage: `printf "y\n" | hcloud version` to accept privacy statement

### 2. Credential Configuration

hcloud CLI supports two credential modes via environment variables, automatically detected at runtime:

**Mode A — Long-term AK/SK** (permanent access):
```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
export HUAWEI_CLOUD_REGION=cn-north-4
```

**Mode B — Temporary AK/SK + SecurityToken** (recommended for temporary or delegated access):
```bash
export HUAWEI_CLOUD_AK=<your-temp-ak>
export HUAWEI_CLOUD_SK=<your-temp-sk>
export HUAWEI_CLOUD_SECURITY_TOKEN=<your-security-token>
export HUAWEI_CLOUD_REGION=cn-north-4
```

> When `HUAWEI_CLOUD_SECURITY_TOKEN` is present, hcloud CLI automatically uses temporary credential authentication. When only AK/SK are set, it uses long-term credential authentication.

- **Security Rules**:
  - 🚫 Never expose AK/SK/SecurityToken values in code, conversation, or commands
  - 🚫 Never use `echo $HUAWEI_CLOUD_AK` or `echo $HUAWEI_CLOUD_SK` to check credentials
  - ✅ Use environment variables: `HUAWEI_CLOUD_AK`, `HUAWEI_CLOUD_SK`, `HUAWEI_CLOUD_REGION`, `HUAWEI_CLOUD_SECURITY_TOKEN`
  - ✅ Prefer IAM users over root account for cloud operations
  - ✅ Enable MFA for sensitive operations

**⚠️ Important Security Notes**:

- Never commit credentials to version control
- Use IAM users with minimal required permissions
- Enable MFA for sensitive operations
- Rotate AK/SK regularly

### 3. IAM Permission Requirements

| API Action                       | Permission        | Purpose                                |
| -------------------------------- | ----------------- | -------------------------------------- |
| `swr:namespace:auth:create`      | Create NS auth    | Grant namespace permissions            |
| `swr:namespace:auth:get`         | Get NS auth       | Query namespace permissions            |
| `swr:namespace:auth:update`      | Update NS auth    | Modify namespace permissions           |
| `swr:namespace:auth:delete`      | Delete NS auth    | Revoke namespace permissions           |
| `swr:repository:auth:create`     | Create repo auth  | Grant repository permissions           |
| `swr:repository:auth:get`        | Get repo auth     | Query repository permissions           |
| `swr:repository:auth:update`     | Update repo auth  | Modify repository permissions          |
| `swr:repository:auth:delete`     | Delete repo auth  | Revoke repository permissions          |
| `swr:retention:create`           | Create retention  | Create retention rules                 |
| `swr:retention:list`             | List retention    | List retention rules                   |
| `swr:retention:get`              | Get retention     | View retention rule details            |
| `swr:retention:update`           | Update retention  | Modify retention rules                 |
| `swr:retention:delete`           | Delete retention  | Remove retention rules                 |
| `swr:domain:create`              | Create domain     | Create shared download domains         |
| `swr:domain:list`                | List domains      | List shared download domains           |
| `swr:domain:get`                 | Get domain        | View domain details                    |
| `swr:domain:update`              | Update domain     | Modify domain settings                 |
| `swr:domain:delete`              | Delete domain     | Remove shared download domains         |
| `swr:share:list`                 | List shared repos | List shared repositories               |
| `swr:share:get`                  | Get shared repo   | View shared repository details         |
| `swr:share:feature:get`          | Get share feature | Check sharing feature gates            |
| `swr:global:feature:get`         | Get global feature| Check global feature gates             |
| `swr:agency:check`               | Check agency      | Check agency delegation status         |
| `swr:agency:create`              | Create agency     | Create agency delegation               |
| `swr:accessory:list`             | List accessories  | List repository accessories            |
| `swr:reference:list`             | List references   | List repository references             |

See [IAM Permission Policies](references/iam-policies.md) for complete policy JSON.

**Permission Failure Handling**:

1. When any command fails due to permission errors, read `references/iam-policies.md`
2. Display the required permission list and policy JSON to the user
3. Guide the user to create a custom policy in the IAM console and grant authorization
4. Pause execution and wait for user confirmation that permissions have been granted

## Core Commands

### 1. Namespace Permissions

See [Task: Namespace Permissions](references/task-namespace-permissions.md) for detailed workflows.

```bash
# Show namespace permissions (who has access and their auth levels)
hcloud SWR ShowNamespaceAuth --namespace=pancake --cli-region=cn-north-4

# Grant namespace permission to a user
hcloud SWR CreateNamespaceAuth --namespace=pancake --1.auth=7 --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4

# Update namespace permission for a user
hcloud SWR UpdateNamespaceAuth --namespace=pancake --1.auth=3 --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4

# Revoke namespace permission for a user
hcloud SWR DeleteNamespaceAuth --namespace=pancake --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4
```

**Auth Values**: `7` = manage (full control), `3` = edit (push/pull), `1` = read (pull only)

**⚠️ Array-Style Parameters**: Permission operations use `--[N].auth`, `--[N].user_id`, `--[N].user_name` format where `[N]` is the array index (starting from 1). For a single user, use `--1.auth=7 --1.user_id=xxx --1.user_name=xxx`. See [Common Pitfalls](references/common-pitfalls.md) for details.

### 2. Repository Permissions

See [Task: Repository Permissions](references/task-repository-permissions.md) for detailed workflows.

```bash
# Show repository permissions
hcloud SWR ShowUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4

# Grant repository permission to a user
hcloud SWR CreateUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --1.auth=7 --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4

# Update repository permission for a user
hcloud SWR UpdateUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --1.auth=3 --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4

# Revoke repository permission for a user
hcloud SWR DeleteUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4
```

**Auth Values**: Same as namespace permissions: `7` = manage, `3` = edit, `1` = read

### 3. Agency Delegation

```bash
# Check if agency delegation is enabled
hcloud SWR CheckAgency --cli-region=cn-north-4

# Create agency delegation for SWR
hcloud SWR CreateAgency --cli-region=cn-north-4
```

**Use Cases**:
- Agency delegation allows SWR to access other services (OBS, CCE) on your behalf
- Required for features like image sync to OBS and CCE trigger deployments
- `CheckAgency` returns whether agency is already configured; `CreateAgency` sets up the delegation

### 4. Retention Rules

See [Task: Retention Management](references/task-retention-management.md) for detailed workflows.

```bash
# List retention rules for a repository
hcloud SWR ListRetentions --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4

# Create a retention rule (keep last 10 tags)
hcloud SWR CreateRetention --namespace=pancake --repository=openclaw-sandbox --algorithm=or --rules.1.template=tag_rule --rules.1.params.num=10 --rules.1.tag_selectors.1.kind=label --rules.1.tag_selectors.1.pattern=latest --cli-region=cn-north-4

# Create a retention rule (keep tags from last 30 days)
hcloud SWR CreateRetention --namespace=pancake --repository=openclaw-sandbox --algorithm=or --rules.1.template=date_rule --rules.1.params.days=30 --rules.1.tag_selectors.1.kind=label --rules.1.tag_selectors.1.pattern=latest --cli-region=cn-north-4

# Show retention rule details
hcloud SWR ShowRetention --namespace=pancake --repository=openclaw-sandbox --retention_id=<id> --cli-region=cn-north-4

# Update a retention rule
hcloud SWR UpdateRetention --namespace=pancake --repository=openclaw-sandbox --retention_id=<id> --algorithm=or --rules.1.template=tag_rule --rules.1.params.num=5 --rules.1.tag_selectors.1.kind=label --rules.1.tag_selectors.1.pattern=latest --cli-region=cn-north-4

# Delete a retention rule
hcloud SWR DeleteRetention --namespace=pancake --repository=openclaw-sandbox --retention_id=<id> --cli-region=cn-north-4

# List retention execution histories
hcloud SWR ListRetentionHistories --namespace=pancake --repository=openclaw-sandbox --retention_id=<id> --cli-region=cn-north-4
```

**Retention Rule Templates**:
- `tag_rule`: Keep a specified number of the most recent tags (`params.num`)
- `date_rule`: Keep tags created within a specified number of days (`params.days`)

**Tag Selector Kinds**:
- `label`: Exact tag name match (e.g., `latest`, `v1.0`)
- `regexp`: Regex pattern match (e.g., `v\d+\.\d+\.\d+`)

**Algorithm**: `or` means rules are combined with OR logic (a tag is retained if it matches ANY rule)

### 5. Shared Download Domains

See [Task: Shared Domains](references/task-shared-domains.md) for detailed workflows.

```bash
# List shared download domains for a repository
hcloud SWR ListRepoDomains --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4

# Create a shared download domain
hcloud SWR CreateRepoDomains --namespace=pancake --repository=openclaw-sandbox --domain=shared-domain-name --cli-region=cn-north-4

# Show shared domain details
hcloud SWR ShowAccessDomain --namespace=pancake --repository=openclaw-sandbox --access_domain=shared-domain-name --cli-region=cn-north-4

# Update a shared download domain
hcloud SWR UpdateRepoDomains --namespace=pancake --repository=openclaw-sandbox --domain=shared-domain-name --permit=read --cli-region=cn-north-4

# Delete a shared download domain
hcloud SWR DeleteRepoDomains --namespace=pancake --repository=openclaw-sandbox --access_domain=shared-domain-name --cli-region=cn-north-4
```

### 6. Image Sharing

See [Task: Image Sharing](references/task-image-sharing.md) for detailed workflows.

```bash
# List shared repositories I have shared (self) or received (thirdparty)
# --center is REQUIRED: "self" = repos I shared to others, "thirdparty" = repos shared to me
hcloud SWR ListSharedReposDetails --center=self --cli-region=cn-north-4

# List shared repository details (--shared_by is REQUIRED: self|thirdparty)
hcloud SWR ListSharedRepoDetails --shared_by=self --cli-region=cn-north-4

# Check sharing feature gates
hcloud SWR ShowShareFeatureGates --cli-region=cn-north-4

# Check global feature gates
hcloud SWR ListGlobalFeatureGates --cli-region=cn-north-4
```

### 7. Repository Accessories & References

```bash
# List repository accessories
hcloud SWR ListRepoAccessories --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4

# List repository references
hcloud SWR ListReferences --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4
```

## Parameter Reference

### Common Parameters

| Parameter       | Required/Optional | Description                   | Default                              |
| --------------- | ----------------- | ----------------------------- | ------------------------------------ |
| `--cli-region`  | Required          | Huawei Cloud region ID        | Config value or `HUAWEI_CLOUD_REGION` |
| `--namespace`   | Context-dependent | SWR namespace (organization)  | N/A                                  |
| `--repository`  | Context-dependent | Image repository name         | N/A                                  |

### Permission Parameters

| Parameter       | Required | Description            | Constraints                                    |
| --------------- | -------- | ---------------------- | ---------------------------------------------- |
| `--namespace`   | Yes      | Namespace name         | Must exist                                     |
| `--repository`  | Yes      | Repository name (repo-level only) | Must exist                           |
| `--[N].auth`    | Yes      | Permission level       | 7=manage, 3=edit, 1=read                       |
| `--[N].user_id` | Yes      | IAM user ID            | Hex string (e.g., `05949eb5350010e21f85c017722182de`) |
| `--[N].user_name` | Yes   | IAM user name          | IAM user display name                          |

**⚠️ Array Index Format**: `[N]` starts from 1 (not 0). For granting permission to a single user, use `--1.auth=7 --1.user_id=xxx --1.user_name=xxx`. For multiple users, use `--1.auth=7 --1.user_id=xxx --1.user_name=xxx --2.auth=3 --2.user_id=yyy --2.user_name=yyy`.

### Retention Parameters

| Parameter                     | Required | Description              | Constraints                                  |
| ----------------------------- | -------- | ------------------------ | -------------------------------------------- |
| `--namespace`                 | Yes      | Namespace name           | Must exist                                   |
| `--repository`                | Yes      | Repository name          | Must exist                                   |
| `--retention_id`              | Yes      | Retention rule ID (for show/update/delete) | Numeric ID           |
| `--algorithm`                 | Yes      | Rule combination logic   | Fixed value `or`                             |
| `--rules.[N].template`        | Yes      | Rule template type       | `date_rule` or `tag_rule`                    |
| `--rules.[N].params`          | Yes      | Rule parameters          | `days` for date_rule, `num` for tag_rule     |
| `--rules.[N].tag_selectors.[N].kind` | Yes | Selector kind    | `label` or `regexp`                          |
| `--rules.[N].tag_selectors.[N].pattern` | Yes | Selector pattern | Tag name or regex                            |

### Domain Parameters

| Parameter       | Required | Description            | Constraints                                    |
| --------------- | -------- | ---------------------- | ---------------------------------------------- |
| `--namespace`   | Yes      | Namespace name         | Must exist                                     |
| `--repository`  | Yes      | Repository name        | Must exist                                     |
| `--domain`      | Yes (create) | Shared domain name | Domain identifier                              |
| `--access_domain` | Yes (show/delete) | Domain name   | Same as domain                                 |
| `--permit`      | Yes (update) | Permission type   | `read`                                         |

## Output Format

See [Output Format](references/output-format.md) for detailed response format examples (NamespaceAuth, RepositoryAuth, RepoDomains, CheckAgency, ShareFeatureGates, GlobalFeatureGates, Retentions, RepoAccessories, ListSharedReposDetails).

**Key Format Notes**:
- `auth`: Permission value (7=manage, 3=edit, 1=read)
- `self_auth` vs `others_auths`: Check both when auditing permissions
- `ListRepoDomains`: Uses `created/updated` (NOT `created_at/updated_at`)
- `ListRetentions`: Returns flat array (empty `[]` when no rules)
- `ListRepoAccessories`: Uses `total` + `accessories` (null when empty)

## Verification

See [Verification Method](references/verification-method.md) for step-by-step verification.

## Best Practices

1. **Least Privilege**: Grant the minimum auth level needed — `1` (read) for pull-only, `3` (edit) for push/pull, `7` (manage) for full control
2. **Namespace vs Repository Permissions**: Namespace permissions apply to ALL repositories under it; repository permissions are granular per-repo
3. **Retention Rules**: Use `tag_rule` (keep N most recent) for most cases; `date_rule` (keep tags within N days) for time-based cleanup
4. **Retention Tag Selectors**: Use `label` kind with `latest` pattern to protect important tags from retention cleanup
5. **Shared Domains**: Use `deadline=forever` for stable internal sharing; set specific deadlines for temporary cross-team access
6. **Agency Delegation**: Check agency status before configuring image sync or CCE triggers — these require agency to be enabled
7. **Audit Permissions Regularly**: Use `ShowNamespaceAuth` and `ShowUserRepositoryAuth` to periodically review who has access

## Reference Documents

| Document                                               | Description                              |
| ------------------------------------------------------ | ---------------------------------------- |
| [SWR Governance API Guide](references/swr-governance-api-guide.md) | hcloud SWR governance API reference |
| [Output Format](references/output-format.md) | Response format examples (verified) |
| [IAM Permission Policies](references/iam-policies.md)  | Required permissions and policy JSON     |
| [Verification Method](references/verification-method.md) | Step-by-step verification              |
| [Common Pitfalls](references/common-pitfalls.md)       | Troubleshooting guides                   |
| [Task: Namespace Permissions](references/task-namespace-permissions.md) | Namespace permission workflows |
| [Task: Repository Permissions](references/task-repository-permissions.md) | Repository permission workflows |
| [Task: Retention Management](references/task-retention-management.md) | Retention rule workflows |
| [Task: Shared Domains](references/task-shared-domains.md) | Shared domain workflows |
| [Task: Image Sharing](references/task-image-sharing.md) | Image sharing workflows |

## Notes

- **Permission changes are immediate** — no delay between granting and availability
- **Revoke with caution** — removing manage auth (7) prevents the user from administering the namespace/repository
- **Retention rules execute automatically** — tags matching the rule conditions will be deleted during execution
- **AK/SK must never be hardcoded** — credentials should only be obtained via environment variables
- **hcloud CLI is the only supported method** — all operations use `hcloud SWR <Operation>` format
- **ListRepoDomains timestamps use `created/updated`** — NOT `created_at/updated_at`

## Common Pitfalls

See [Common Pitfalls & Solutions](references/common-pitfalls.md) for detailed troubleshooting guides.

**Quick Reference**:

| Pitfall                     | Symptom                         | Quick Fix                                    |
| --------------------------- | ------------------------------- | -------------------------------------------- |
| Array-style params          | Permission grant fails          | Use `--1.auth=7 --1.user_id=xxx` (index from 1, not 0) |
| Auth value wrong            | User has unexpected access      | 7=manage, 3=edit, 1=read (not 1/2/3)        |
| self_auth vs others_auths   | Missing user in audit           | Check both `self_auth` and `others_auths`    |
| Domain timestamp fields     | Parsing `created_at` fails      | Use `created`/`updated` (not `created_at`)   |
| Retention rule format       | CreateRetention fails           | Nested array params: `--rules.1.tag_selectors.1.kind` |
| Agency not configured       | Image sync/CCE trigger fails    | Run `CheckAgency` then `CreateAgency`        |