---
id: huawei-cloud-swr-image-management
name: huawei-cloud-swr-image-management
description: |
  Huawei Cloud SWR (Software Repository for Container) image lifecycle management skill using hcloud CLI.
  Use this skill when the user wants to: (1) manage SWR namespaces (organizations) - create/query/delete, (2) manage image repositories - create/query/update/delete, (3) manage image tags/versions - query/create/delete, (4) obtain docker login credentials for SWR, (5) check SWR quotas and usage limits.
  Trigger: user mentions "SWR image management", "SWR 镜像管理", "container image", "镜像仓库", "SWR 组织", "SWR namespace", "镜像版本", "docker login", "SWR 配额", "SWR tag", "容器镜像", "镜像生命周期", "SWR repository", "SWR 登录", "SWR quota"
tags:
  - swr
  - image-management
  - namespace
  - repository
  - tag
---

# Huawei Cloud SWR Image Management

## Overview

This skill provides lifecycle management capabilities for Huawei Cloud SWR (Software Repository for Container) images using the `hcloud` CLI.

**Architecture**: hcloud CLI → SWR Service API → Namespace/Repository/Tag/Auth/Quota resources

- Create and manage SWR namespaces (organizations)
- Create and manage image repositories with public/private settings
- Query and manage image tags/versions
- Obtain docker login credentials (temporary and long-term)
- Check SWR resource quotas

**Typical Use Cases**:

- "Create a SWR namespace for my project"
- "List all image repositories in namespace 'group-dev'"
- "Query image tags for repository 'nginx' in namespace 'group-dev'"
- "Get docker login command for SWR"
- "Delete an old image tag to clean up storage"
- "Check my SWR quota usage"
- "Create a private repository for my custom image"
- "Update repository description and visibility"

## 工作流

1. **Parse user request** — identify the SWR operation (namespace, repository, tag, auth, quota)
2. **Verify prerequisites** — check hcloud CLI installation and credential configuration
3. **Confirm parameters** — display the operation, target resources, and parameters to the user for confirmation
4. **Execute read operations** — for query operations (Show, List), run hcloud CLI directly
5. **Confirm write operations** — for write operations (Create, Update, Delete), prompt user confirmation before execution (see [参数确认](#参数确认))
6. **Parse and format output** — extract relevant fields, format as table or structured output
7. **Report results** — present results with context (e.g., namespace created, repository visibility changed)
8. **Suggest next actions** — recommend related operations (e.g., after creating namespace, suggest creating a repository)

### 参数确认

> **All write operations (Create, Update, Delete) require explicit user confirmation before execution.**

Before executing any write operation, the skill must:

1. Display the exact hcloud command to be executed
2. Show the target resource (namespace, repository, tag, etc.)
3. Show the change to be applied (create, delete, visibility change)
4. Wait for user confirmation ("yes" / "确认") before proceeding
5. If user declines, abort the operation and return to step 1

**Write operations requiring confirmation**:

| Operation | Command | Risk Level | Description |
|-----------|---------|------------|-------------|
| Create namespace | `CreateNamespace` | Medium | Creates a new SWR namespace (consumes quota) |
| Create repository | `CreateRepo` | Medium | Creates a new image repository |
| Update repository | `UpdateRepo` | Medium | Changes repository visibility (public/private) |
| Delete namespace | `DeleteNamespaces` | High | Deletes namespace AND all repos/images under it |
| Delete repository | `DeleteRepo` | High | Deletes repository AND all image tags permanently |
| Delete tag | `DeleteRepoTag` | High | Deletes image tag permanently (irreversible) |

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
| `swr:namespace:create`           | Create namespace  | Create SWR organizations               |
| `swr:namespace:list`             | List namespaces   | Query all namespaces                   |
| `swr:namespace:get`              | Get namespace     | View individual namespace information  |
| `swr:namespace:delete`           | Delete namespace  | Remove organizations                   |
| `swr:repository:create`          | Create repo       | Create image repositories              |
| `swr:repository:list`            | List repos        | Query image repositories               |
| `swr:repository:get`             | Get repo          | View repository details                |
| `swr:repository:update`          | Update repo       | Modify repository properties           |
| `swr:repository:delete`          | Delete repo       | Remove image repositories              |
| `swr:tag:list`                   | List tags         | Query image tags/versions              |
| `swr:tag:get`                    | Get tag           | View specific tag details              |
| `swr:tag:create`                 | Create tag        | Create image tag                       |
| `swr:tag:delete`                 | Delete tag        | Remove image tag                       |
| `swr:login:get`                  | Get login token   | Obtain docker login credentials        |
| `swr:quota:get`                  | Get quota         | Check resource quotas                  |

See [IAM Permission Policies](references/iam-policies.md) for complete policy JSON.

**Permission Failure Handling**:

1. When any command fails due to permission errors, read `references/iam-policies.md`
2. Display the required permission list and policy JSON to the user
3. Guide the user to create a custom policy in the IAM console and grant authorization
4. Pause execution and wait for user confirmation that permissions have been granted

## KooCLI命令格式标准

All commands follow the standard hcloud KooCLI format:

```bash
hcloud SWR <Operation> --param1=value1 --param2=value2 --cli-region=<region>
```

**Key conventions**:

- Service name: `SWR` (uppercase, matches KooCLI Services listing)
- Operation name: PascalCase (e.g., `ShowNamespace`, `CreateRepo`, `ListRepoTags`)
- Region parameter: `--cli-region=<value>` (default: `cn-north-4`, or `HUAWEI_CLOUD_REGION` env var)
- Output format: `--cli-output=json` (for agent processing)
- JMESPath filtering: `--cli-query="<expression>"` (to reduce output)
- Object-type parameters: JSON string format `--key={subkey:value}`

**Example — read operation**:

```bash
hcloud SWR ShowNamespace --namespace=pancake --cli-region=cn-north-4 --cli-output=json
```

**Example — write operation (requires user confirmation)**:

```bash
# Step 1: Display command and parameters for user confirmation
# Step 2: After user confirms, execute:
hcloud SWR CreateNamespace --namespace=my-project --cli-region=cn-north-4
```

## Core Commands

### 1. Namespace (Organization) Management

See [Task: Namespace Management](references/task-namespace-management.md) for detailed workflows.

```bash
# List all namespaces
hcloud SWR ListNamespaces --cli-region=cn-north-4

# List namespaces with filter
hcloud SWR ListNamespaces --filter="namespace::group-dev|mode::visible" --cli-region=cn-north-4

# Show namespace details
hcloud SWR ShowNamespace --namespace=group-dev --cli-region=cn-north-4

# Create a namespace
hcloud SWR CreateNamespace --namespace=group-dev --cli-region=cn-north-4

# Delete a namespace (CAUTION: removes all repos under it)
hcloud SWR DeleteNamespaces --namespace=group-dev --cli-region=cn-north-4
```

**Namespace Naming Rules**:
- Start with lowercase letter
- Followed by lowercase letters, digits, dots, underscores, or hyphens
- Max 2 consecutive underscores
- Dots, underscores, hyphens cannot be directly connected
- End with lowercase letter or digit
- Length: 1-64 characters

### 2. Repository (Image Repository) Management

See [Task: Repository Management](references/task-repository-management.md) for detailed workflows.

```bash
# List all repositories
hcloud SWR ListReposDetails --cli-region=cn-north-4

# List repositories in a namespace
hcloud SWR ListReposDetails --namespace=group-dev --cli-region=cn-north-4

# List repositories with pagination and sorting
hcloud SWR ListReposDetails --namespace=group-dev --limit=20 --offset=0 --order_column=updated_time --order_type=desc --cli-region=cn-north-4

# List repositories by category
hcloud SWR ListReposDetails --category=database --cli-region=cn-north-4

# Show repository details
hcloud SWR ShowRepository --namespace=group-dev --repository=nginx --cli-region=cn-north-4

# Create a repository
hcloud SWR CreateRepo --namespace=group-dev --repository=my-app --is_public=false --category=other --description="Custom app image" --cli-region=cn-north-4

# Update repository (change visibility, description, category)
hcloud SWR UpdateRepo --namespace=group-dev --repository=my-app --is_public=true --description="Updated description" --cli-region=cn-north-4

# Delete a repository (CAUTION: removes all image tags)
hcloud SWR DeleteRepo --namespace=group-dev --repository=my-app --cli-region=cn-north-4
```

**Repository Naming Rules**:
- Start with lowercase letter or digit
- Followed by lowercase letters, digits, dots, slashes, underscores, or hyphens
- Max 2 consecutive underscores
- Dots, slashes, underscores, hyphens cannot be directly connected
- End with lowercase letter or digit
- Length: 1-128 characters

**Repository Categories**: `app_server`, `linux`, `framework_app`, `database`, `lang`, `other`, `windows`, `arm`

### 3. Image Tag (Version) Management

See [Task: Tag Management](references/task-tag-management.md) for detailed workflows.

```bash
# List all tags in a repository
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --cli-region=cn-north-4

# List tags with pagination and sorting
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --limit=50 --offset=0 --order_column=updated_at --order_type=desc --cli-region=cn-north-4

# Search for a specific tag
hcloud SWR ListRepositoryTags --namespace=group-dev --repository=nginx --filter="tag::v1.0" --cli-region=cn-north-4

# Show tag details (image digest, size, create time)
hcloud SWR ShowRepoTag --namespace=group-dev --repository=nginx --tag=v1.0 --cli-region=cn-north-4

# Create a tag (retag existing image)
hcloud SWR CreateRepoTag --namespace=group-dev --repository=nginx --source_tag=v1.0 --destination_tag=v1.0-stable --override=false --cli-region=cn-north-4

# Delete a tag (CAUTION: removes the image version permanently)
hcloud SWR DeleteRepoTag --namespace=group-dev --repository=nginx --tag=v1.0-old --cli-region=cn-north-4
```

### 4. Docker Login & Authentication

See [Task: Auth Management](references/task-auth-management.md) for detailed workflows.

```bash
# Get temporary docker login credentials (valid for 12 hours)
hcloud SWR CreateAuthorizationToken --cli-region=cn-north-4

# Get long-term docker login credentials (valid for 1 year)
hcloud SWR CreateSecret --cli-region=cn-north-4
```

**Response Format** (verified against actual API):

The response returns a Docker auth config object:

```json
{
  "auths": {
    "swr.cn-north-4.myhuaweicloud.com": {
      "auth": "base64-encoded-auth-token"
    }
  }
}
```

- `auths`: Docker config auth object, registry host as key
- `auth`: Base64-encoded `username:password` string

**Docker Login Command**:

```bash
# Decode auth field: echo <auth_value> | base64 -d → username:password
docker login -u <decoded_username> -p <decoded_password> swr.cn-north-4.myhuaweicloud.com
```

### 5. Quota Management

See [Task: Quota Management](references/task-quota-management.md) for detailed workflows.

```bash
# Check SWR quotas
hcloud SWR ListQuotas --cli-region=cn-north-4
```

## Parameter Reference

See [Parameter Reference](references/parameter-reference.md) for detailed parameter tables and valid values per command.


## Output Format

See [Output Format Reference](references/output-format.md) for JSON response formats of all SWR API commands.


## Verification

See [Verification Method](references/verification-method.md) for step-by-step verification.

## Best Practices

1. **Namespace Organization**: Use descriptive namespace names following team/project naming (e.g., `team-backend`, `proj-ai`)
2. **Repository Visibility**: Set `is_public=false` for internal images; only set `is_public=true` for images intended for public sharing
3. **Tag Naming Convention**: Use semantic versioning (e.g., `v1.0`, `v1.0-stable`, `latest`) and avoid ambiguous tags
4. **Regular Cleanup**: Periodically delete outdated tags to manage storage quotas
5. **Retag Instead of Re-push**: Use `CreateRepoTag` to create version aliases rather than pushing the same image multiple times
6. **Long-term Login for CI/CD**: Use `CreateSecret` for automation pipelines; use `CreateAuthorizationToken` for temporary access
7. **Delete with Caution**: Deleting a namespace removes ALL repositories under it; deleting a repository removes ALL tags

## Reference Documents

| Document                                               | Description                              |
| ------------------------------------------------------ | ---------------------------------------- |
| [SWR API Guide](references/swr-api-guide.md)           | hcloud SWR API reference                 |
| [Parameter Reference](references/parameter-reference.md) | Parameter tables and region IDs        |
| [Output Format](references/output-format.md)           | JSON response formats                    |
| [IAM Permission Policies](references/iam-policies.md)  | Required permissions and policy JSON     |
| [Verification Method](references/verification-method.md) | Step-by-step verification              |
| [Common Pitfalls](references/common-pitfalls.md)       | Troubleshooting guides                   |
| [Task: Namespace Management](references/task-namespace-management.md) | Namespace workflows   |
| [Task: Repository Management](references/task-repository-management.md) | Repository workflows  |
| [Task: Tag Management](references/task-tag-management.md) | Tag workflows                        |
| [Task: Auth Management](references/task-auth-management.md) | Login credential workflows          |
| [Task: Quota Management](references/task-quota-management.md) | Quota check workflows             |
| [CLI Installation Guide](references/cli-installation-guide.md) | hcloud install, config, verify   |
| [Acceptance Criteria](references/acceptance-criteria.md) | Correct/error pattern comparison  |

## Unsupported Operations

This skill manages SWR namespaces, repositories, tags, auth credentials, and quotas via the hcloud CLI. The following operations are **not supported** by this skill:

### Push/Pull Images (docker CLI operations)

This skill provides docker login credentials via `CreateAuthorizationToken` or `CreateSecret`, but does **not** execute `docker push` or `docker pull`. After obtaining credentials, use docker CLI directly:

```bash
# Step 1: Get login credentials from this skill
hcloud SWR CreateAuthorizationToken --cli-region=cn-north-4
# Decode the auth field to get username:password

# Step 2: Login and push/pull with docker CLI
docker login -u <user> -p <pass> swr.cn-north-4.myhuaweicloud.com
docker push swr.cn-north-4.myhuaweicloud.com/<namespace>/<repo>:<tag>
docker pull swr.cn-north-4.myhuaweicloud.com/<namespace>/<repo>:<tag>
```

### Image Security Scanning

Image security scanning is **not provided** by this skill. It strongly depends on Huawei Cloud HSS (Host Security Service) and requires an enterprise SWR instance. The `StartManualScanning` API is only available in enterprise SWR instances, not in basic SWR. This skill covers basic SWR management only and does not include image scanning capabilities.


### Build History

The SWR API does not provide build history commands. Image build functionality is available only in the SWR Web Console. Use the Huawei Cloud console at `https://console.huawei.com/swr` to view build history.

### External Image Import

The SWR API does not provide an image import operation. To import an external image (e.g., from Docker Hub):

```bash
# Step 1: Pull the external image
docker pull docker.io/library/nginx:latest

# Step 2: Get SWR login credentials from this skill
hcloud SWR CreateAuthorizationToken --cli-region=cn-north-4

# Step 3: Tag and push to SWR
docker tag docker.io/library/nginx:latest swr.cn-north-4.myhuaweicloud.com/<namespace>/nginx:latest
docker push swr.cn-north-4.myhuaweicloud.com/<namespace>/nginx:latest
```

## Write Operation Return Values

See [Verification Method](references/verification-method.md) for write operation return values and post-write verification steps.

## Pagination Parameter Scope

See [SWR API Guide](references/swr-api-guide.md) for pagination parameter scope details.

## Notes

- **Namespace deletion is irreversible** — removes all repositories and images under it
- **Repository deletion is irreversible** — removes all image tags permanently
- **Tag deletion is irreversible** — the image version cannot be recovered
- **AK/SK must never be hardcoded** — credentials should only be obtained via environment variables
- **hcloud CLI is the only supported method** — all operations use `hcloud SWR <Operation>` format
- **Pagination required for large datasets** — use `--limit` and `--offset` for repositories and tags listing

## Common Pitfalls

See [Common Pitfalls & Solutions](references/common-pitfalls.md) for detailed troubleshooting guides.

**Quick Reference**:

| Pitfall                     | Symptom                         | Quick Fix                                    |
| --------------------------- | ------------------------------- | -------------------------------------------- |
| Invalid namespace name      | 400 Bad Request                 | Follow naming rules: lowercase, 1-64 chars   |
| Namespace not found         | 404 Not Found                   | Verify namespace exists with `ShowNamespace`  |
| Repo already exists         | 409 Conflict                    | Use `ShowRepository` to check first           |
| Tag digest mismatch         | Retag fails                     | Verify `source_tag` exists with `ShowRepoTag` |
| Quota exceeded              | 403 Quota limit                 | Check quotas with `ListQuotas`                |
| Auth token expired          | Docker login fails              | Regenerate with `CreateAuthorizationToken`    |
| `Tag` field name            | Tag query returns unexpected structure | Use `Tag` (capital T) not `name`              |
| `num_images` not `tag_count`| Repo listing field mismatch    | Response uses `num_images`; `--order_column` uses `tag_count` |
