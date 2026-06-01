# SWR Governance API Reference Guide

## Overview

This document provides API reference information for Huawei Cloud SWR governance operations using hcloud CLI. All commands follow the standard format: `hcloud SWR <Operation> --param=value --cli-region=<region>`.

## Authentication

### Environment Variables

```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
```

### hcloud CLI Configuration

```bash
# Interactive configuration
hcloud configure

# Verify configuration (safe - does not expose values)
hcloud configure list
```

✅ **Correct**: Use `hcloud configure list` to verify credentials
❌ **Incorrect**: Never use `echo $HUAWEI_CLOUD_AK` to check credentials

## Namespace Permission Operations

### 1. Show Namespace Permissions

```bash
hcloud SWR ShowNamespaceAuth --namespace=pancake --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name (path parameter)
- `--cli-region` (required): Region ID

**Response Example** (verified against actual API):

```json
{
  "id": 3827347,
  "name": "pancake",
  "creator_name": "hwstaff_p00506267",
  "self_auth": {
    "user_id": "05949eb5350010e21f85c017722182de",
    "user_name": "hwstaff_p00506267",
    "auth": 7
  },
  "others_auths": [
    {
      "user_id": "05949eb5350010e21f85c017722182de",
      "user_name": "hwstaff_p00506267",
      "auth": 7
    }
  ]
}
```

**Key Fields**:
- `id`: Namespace numeric ID
- `name`: Namespace name
- `creator_name`: Creator IAM user name
- `self_auth`: Your own permission on this namespace (separate object)
- `others_auths`: Array of other users' permissions
- `auth`: Permission level (7=manage, 3=edit, 1=read)

**⚠️ Important**: `self_auth` is a separate object from `others_auths`. When auditing permissions, check both.

### 2. Create Namespace Permission

```bash
hcloud SWR CreateNamespaceAuth --namespace=pancake --1.auth=7 --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name (path parameter)
- `--[N].auth` (required, body): Permission level (7=manage, 3=edit, 1=read)
- `--[N].user_id` (required, body): IAM user ID (hex string)
- `--[N].user_name` (required, body): IAM user display name
- `--cli-region` (required): Region ID

**⚠️ Array-Style Parameters**: `[N]` is the array index starting from 1. For a single user, use `--1.auth=7 --1.user_id=xxx --1.user_name=xxx`. For multiple users, add `--2.auth=3 --2.user_id=yyy --2.user_name=yyy` etc.

**Auth Values**:
- `7`: Manage — full control (create/delete repos, manage permissions)
- `3`: Edit — push and pull images
- `1`: Read — pull images only

### 3. Update Namespace Permission

```bash
hcloud SWR UpdateNamespaceAuth --namespace=pancake --1.auth=3 --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4
```

**Parameters**: Same as CreateNamespaceAuth. Use to change an existing user's auth level.

### 4. Delete Namespace Permission

```bash
hcloud SWR DeleteNamespaceAuth --namespace=pancake --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name (path parameter)
- `--[N].user_id` (required, body): IAM user ID to revoke
- `--[N].user_name` (required, body): IAM user name to revoke
- `--cli-region` (required): Region ID

⚠️ **Warning**: This removes the user's access to the namespace and ALL repositories under it.

## Repository Permission Operations

### 1. Show Repository Permissions

```bash
hcloud SWR ShowUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name (path parameter)
- `--repository` (required): Repository name (path parameter)
- `--cli-region` (required): Region ID

**Response Example** (verified against actual API):

```json
{
  "id": 3374887,
  "name": "openclaw-sandbox",
  "self_auth": {
    "user_id": "...",
    "user_name": "...",
    "auth": 7
  },
  "others_auths": []
}
```

**Key Fields**: Same structure as namespace auth but with repository `id` and `name`.

### 2. Create Repository Permission

```bash
hcloud SWR CreateUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --1.auth=7 --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4
```

**Parameters**: Same array-style format as CreateNamespaceAuth, plus `--repository`.

### 3. Update Repository Permission

```bash
hcloud SWR UpdateUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --1.auth=3 --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4
```

**Parameters**: Same as CreateUserRepositoryAuth.

### 4. Delete Repository Permission

```bash
hcloud SWR DeleteUserRepositoryAuth --namespace=pancake --repository=openclaw-sandbox --1.user_id=05949eb5350010e21f85c017722182de --1.user_name=hwstaff_p00506267 --cli-region=cn-north-4
```

**Parameters**: `--namespace`, `--repository`, and array-style `--[N].user_id`/`--[N].user_name`.

## Agency Operations

### 1. Check Agency Status

```bash
hcloud SWR CheckAgency --cli-region=cn-north-4
```

**Parameters**:
- `--cli-region` (required): Region ID

**Response Example** (verified against actual API):

```json
{
  "domain_id": "05949eb4190010e40f36c017b62fafa0",
  "is_agency": true
}
```

**Key Fields**:
- `domain_id`: Domain ID (hex string)
- `is_agency`: Whether agency delegation is configured (boolean)

### 2. Create Agency Delegation

```bash
hcloud SWR CreateAgency --cli-region=cn-north-4
```

**Parameters**:
- `--cli-region` (required): Region ID

**Use Case**: Creates SWR agency delegation allowing SWR to access OBS (for image sync) and CCE (for trigger deployments) on your behalf.

## Retention Operations

### 1. List Retention Rules

```bash
hcloud SWR ListRetentions --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name (path parameter)
- `--repository` (required): Repository name (path parameter)
- `--cli-region` (required): Region ID

**Response Example** (verified — empty flat array when no rules):

```json
[]
```

When retention rules exist, returns array of retention rule objects. Response format to be verified with actual API call.

### 2. Create Retention Rule

```bash
# Keep last 10 tags (tag_rule)
hcloud SWR CreateRetention --namespace=pancake --repository=openclaw-sandbox --algorithm=or --rules.1.template=tag_rule --rules.1.params.num=10 --rules.1.tag_selectors.1.kind=label --rules.1.tag_selectors.1.pattern=latest --cli-region=cn-north-4

# Keep tags from last 30 days (date_rule)
hcloud SWR CreateRetention --namespace=pancake --repository=openclaw-sandbox --algorithm=or --rules.1.template=date_rule --rules.1.params.days=30 --rules.1.tag_selectors.1.kind=label --rules.1.tag_selectors.1.pattern=latest --cli-region=cn-north-4

# Multiple rules (OR logic)
hcloud SWR CreateRetention --namespace=pancake --repository=openclaw-sandbox --algorithm=or --rules.1.template=tag_rule --rules.1.params.num=5 --rules.1.tag_selectors.1.kind=label --rules.1.tag_selectors.1.pattern=latest --rules.2.template=date_rule --rules.2.params.days=30 --rules.2.tag_selectors.1.kind=regexp --rules.2.tag_selectors.1.pattern=v\d+ --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name (path parameter)
- `--repository` (required): Repository name (path parameter)
- `--algorithm` (required, body): Fixed value `or` (rules combined with OR logic)
- `--rules.[N].template` (required, body): Rule type — `date_rule` or `tag_rule`
- `--rules.[N].params` (required, body): Rule parameters
  - For `date_rule`: `{"days": "xxx"}` — keep tags within N days
  - For `tag_rule`: `{"num": "xxx"}` — keep N most recent tags
- `--rules.[N].tag_selectors.[N].kind` (required, body): Selector kind — `label` or `regexp`
- `--rules.[N].tag_selectors.[N].pattern` (required, body): Selector pattern — tag name or regex
- `--cli-region` (required): Region ID

**⚠️ Nested Array Parameters**: Retention rules use deeply nested arrays: `--rules.1.tag_selectors.1.kind=label`. Index starts from 1.

### 3. Show Retention Rule Details

```bash
hcloud SWR ShowRetention --namespace=pancake --repository=openclaw-sandbox --retention_id=<id> --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name
- `--repository` (required): Repository name
- `--retention_id` (required): Retention rule ID
- `--cli-region` (required): Region ID

Response format to be verified with actual API call.

### 4. Update Retention Rule

```bash
hcloud SWR UpdateRetention --namespace=pancake --repository=openclaw-sandbox --retention_id=<id> --algorithm=or --rules.1.template=tag_rule --rules.1.params.num=5 --rules.1.tag_selectors.1.kind=label --rules.1.tag_selectors.1.pattern=latest --cli-region=cn-north-4
```

**Parameters**: Same as CreateRetention plus `--retention_id`.

### 5. Delete Retention Rule

```bash
hcloud SWR DeleteRetention --namespace=pancake --repository=openclaw-sandbox --retention_id=<id> --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name
- `--repository` (required): Repository name
- `--retention_id` (required): Retention rule ID
- `--cli-region` (required): Region ID

### 6. List Retention Execution Histories

```bash
hcloud SWR ListRetentionHistories --namespace=pancake --repository=openclaw-sandbox --retention_id=<id> --cli-region=cn-north-4
```

**Parameters**: Same as ShowRetention.

Response format to be verified with actual API call.

## Shared Download Domain Operations

### 1. List Shared Domains

```bash
hcloud SWR ListRepoDomains --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name (path parameter)
- `--repository` (required): Repository name (path parameter)
- `--cli-region` (required): Region ID

**Response Example** (verified against actual API — flat JSON array):

```json
[
  {
    "namespace": "pancake",
    "repository": "openclaw-sandbox",
    "access_domain": "shijingcheng_test",
    "permit": "read",
    "deadline": "forever",
    "description": "",
    "creator_id": "05949eb5350010e21f85c017722182de",
    "creator_name": "hwstaff_p00506267",
    "created": "2026-04-28T09:18:19.830309Z",
    "updated": "2026-04-28T09:18:19.83031Z",
    "status": true
  }
]
```

**Key Fields**:
- `access_domain`: Shared download domain name
- `permit`: Permission type (`read`)
- `deadline`: Expiration (`forever` or specific date string)
- `description`: Domain description
- `status`: Whether domain is active (boolean)
- `created`/`updated`: Timestamps (**NOT** `created_at`/`updated_at`)

### 2. Create Shared Domain

```bash
hcloud SWR CreateRepoDomains --namespace=pancake --repository=openclaw-sandbox --domain=shared-domain-name --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name (path parameter)
- `--repository` (required): Repository name (path parameter)
- `--domain` (required, body): Shared download domain name
- `--cli-region` (required): Region ID

### 3. Show Shared Domain Details

```bash
hcloud SWR ShowAccessDomain --namespace=pancake --repository=openclaw-sandbox --access_domain=shijingcheng_test --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name
- `--repository` (required): Repository name
- `--access_domain` (required): Domain name (path parameter)
- `--cli-region` (required): Region ID

### 4. Update Shared Domain

```bash
hcloud SWR UpdateRepoDomains --namespace=pancake --repository=openclaw-sandbox --domain=shared-domain-name --permit=read --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name
- `--repository` (required): Repository name
- `--domain` (required): Domain name
- `--permit` (required): Permission type (`read`)
- `--cli-region` (required): Region ID

### 5. Delete Shared Domain

```bash
hcloud SWR DeleteRepoDomains --namespace=pancake --repository=openclaw-sandbox --access_domain=shared-domain-name --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name
- `--repository` (required): Repository name
- `--access_domain` (required): Domain name
- `--cli-region` (required): Region ID

## Image Sharing Operations

### 1. List Shared Repositories

```bash
hcloud SWR ListSharedReposDetails --cli-region=cn-north-4
```

**Parameters**:
- `--cli-region` (required): Region ID

**Response**: Returns flat array of repository objects with same fields as `ListReposDetails` (name, category, description, size, is_public, num_images, num_download, created_at, updated_at, path, internal_path, domain_name, namespace, tags, status, total_range).

### 2. List Shared Repository Details

```bash
hcloud SWR ListSharedRepoDetails --cli-region=cn-north-4
```

**Parameters**:
- `--cli-region` (required): Region ID

### 3. Show Share Feature Gates

```bash
hcloud SWR ShowShareFeatureGates --cli-region=cn-north-4
```

**Parameters**:
- `--cli-region` (required): Region ID

**Response Example** (verified against actual API):

```json
{
  "enable_experience": true,
  "enable_hss_service": true,
  "enable_image_scan": true,
  "enable_sm3": false,
  "enable_image_sync": true,
  "enable_cci_service": true,
  "enable_image_label": false,
  "enable_pipeline": true,
  "enable_authorization_token": true,
  "enable_resource": true,
  "enable_list_v3": true,
  "enable_image_quota": false,
  "enable_cosign_signature": true,
  "enable_enterprise_edition_link": false,
  "enable_customize_validity_period": true,
  "swr_util_download_url": ""
}
```

**Key Feature Gates**:
- `enable_experience`: Shared image experience enabled
- `enable_image_scan`: Security scanning enabled
- `enable_image_sync`: Cross-region sync enabled
- `enable_cosign_signature`: Cosign signature verification enabled
- `enable_authorization_token`: Authorization token enabled
- `enable_cci_service`: CCI service integration enabled

### 4. List Global Feature Gates

```bash
hcloud SWR ListGlobalFeatureGates --cli-region=cn-north-4
```

**Parameters**:
- `--cli-region` (required): Region ID

**Response Example** (verified against actual API):

```json
{
  "enableUserDefObs": true,
  "enableEnterprise": true,
  "cerAvailable": true,
  "enableIntranetAccessSwitch": true,
  "enableOBSEncryptUserKmsKey": true
}
```

**Key Feature Gates**:
- `enableUserDefObs`: Custom OBS bucket for image sync
- `enableEnterprise`: Enterprise edition features
- `enableIntranetAccessSwitch`: Intranet access control
- `enableOBSEncryptUserKmsKey`: OBS encryption with user KMS key

## Repository Accessory & Reference Operations

### 1. List Repository Accessories

```bash
hcloud SWR ListRepoAccessories --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name
- `--repository` (required): Repository name
- `--cli-region` (required): Region ID

**Response Example** (verified against actual API):

```json
{
  "total": 0,
  "accessories": null
}
```

**Key Fields**:
- `total`: Total count of accessories
- `accessories`: Array of accessory objects (null when empty)

### 2. List Repository References

```bash
hcloud SWR ListReferences --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name
- `--repository` (required): Repository name
- `--cli-region` (required): Region ID

## Common Region IDs

| Region Name                    | Region ID        |
| ------------------------------ | ---------------- |
| North China - Beijing 4        | `cn-north-4`     |
| North China - Beijing 1        | `cn-north-1`     |
| East China - Shanghai 1        | `cn-east-3`      |
| East China - Shanghai 2        | `cn-east-2`      |
| South China - Guangzhou        | `cn-south-1`     |
| South China - Shenzhen         | `cn-south-4`     |
| Southwest China - Guiyang 1    | `cn-southwest-2` |
| Asia Pacific - Bangkok         | `ap-southeast-2` |
| Asia Pacific - Singapore       | `ap-southeast-1` |
| Asia Pacific - Hong Kong       | `ap-southeast-3` |
| Europe - Paris                 | `eu-west-0`      |

## Common Errors

| Error                   | Cause                       | Solution                                        |
| ----------------------- | --------------------------- | ------------------------------------------------ |
| `InvalidAccessKeyId`    | Invalid AK/SK               | Check credential configuration via `hcloud configure list` |
| `NamespaceNotFound`     | Namespace does not exist    | Verify namespace name with `ShowNamespace`       |
| `RepositoryNotFound`    | Repository does not exist   | Verify repository name with `ShowRepository`     |
| `PermissionDenied`      | Insufficient IAM permission | Check IAM policies and grant required permissions |
| `AuthValueInvalid`      | Wrong auth value            | Use 7/3/1 (manage/edit/read), not 1/2/3         |
| `RetentionRuleInvalid`  | Wrong rule format           | Check nested array param format                  |
| `DomainNotFound`        | Domain does not exist       | Verify domain name with `ShowAccessDomain`       |
| `RequestLimitExceeded`  | Too many requests           | Add delay between batch requests                  |

## Related Documentation

- [Huawei Cloud SWR Documentation](https://support.huaweicloud.com/swr/index.html)
- [hcloud CLI Documentation](https://support.huaweicloud.com/cli/index.html)
- [Huawei Cloud API Explorer](https://apiexplorer.developer.huaweicloud.com/)