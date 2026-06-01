# Task: Image Sharing

## Overview

SWR image sharing allows repositories to be shared across organizations and users. This task covers listing shared repositories, querying sharing feature gates, checking global feature gates, checking agency status, creating agency delegation, and listing repository accessories and references.

## Operations Catalog

| Operation          | Method | Description              | Key Parameters                                  |
| ------------------ | ------ | ------------------------ | ----------------------------------------------- |
| `ListSharedReposDetails` | GET | 获取共享镜像仓库列表   | (no required params beyond region)              |
| `ListSharedRepoDetails` | GET  | 获取共享镜像仓库详情列表 | (no required params beyond region)            |
| `ShowShareFeatureGates` | GET  | 获取共享特性开关       | (no required params beyond region)              |
| `ListGlobalFeatureGates` | GET | 获取全局特性开关       | (no required params beyond region)              |
| `CheckAgency`     | GET    | 查询委托状态             | (no required params beyond region)              |
| `CreateAgency`    | POST   | 创建委托                 | (no required params beyond region)              |
| `ListRepoAccessories` | GET | 获取镜像仓库附件列表   | `--namespace`, `--repository`                   |
| `ListReferences`  | GET    | 获取镜像仓库引用列表     | `--namespace`, `--repository`                   |

## Workflows

### W1: List Shared Repositories

```bash
# List all shared repositories
hcloud SWR ListSharedReposDetails --cli-region=cn-north-4
```

**Response**: Returns flat array of repository objects with same fields as `ListReposDetails` (name, category, description, size, is_public, num_images, num_download, created_at, updated_at, path, internal_path, domain_name, namespace, tags, status, total_range).

```bash
# List shared repository details
hcloud SWR ListSharedRepoDetails --cli-region=cn-north-4
```

### W2: Check Sharing Feature Gates

```bash
hcloud SWR ShowShareFeatureGates --cli-region=cn-north-4
```

**Output Fields** (verified against actual API):

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
- `enable_experience`: Whether shared image experience is enabled
- `enable_image_scan`: Whether security scanning is enabled
- `enable_image_sync`: Whether cross-region sync is enabled
- `enable_cosign_signature`: Whether Cosign signature verification is enabled
- `enable_authorization_token`: Whether authorization token is enabled
- `enable_cci_service`: Whether CCI service integration is enabled
- `enable_pipeline`: Whether pipeline feature is enabled

### W3: Check Global Feature Gates

```bash
hcloud SWR ListGlobalFeatureGates --cli-region=cn-north-4
```

**Output Fields** (verified against actual API):

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
- `enableUserDefObs`: Whether custom OBS bucket for image sync is enabled
- `enableEnterprise`: Whether enterprise edition features are enabled
- `cerAvailable`: Whether CER is available
- `enableIntranetAccessSwitch`: Whether intranet access toggle is available
- `enableOBSEncryptUserKmsKey`: Whether OBS encryption with user KMS key is enabled

### W4: Check Agency Delegation

```bash
# Check if agency delegation is configured
hcloud SWR CheckAgency --cli-region=cn-north-4
```

**Output Fields** (verified against actual API):

```json
{
  "domain_id": "05949eb4190010e40f36c017b62fafa0",
  "is_agency": true
}
```

- `is_agency`: Whether agency delegation is configured (boolean)
- `domain_id`: Domain ID (hex string)

**Use Cases**:
- Before setting up image sync, verify agency is configured
- Before creating CCE triggers, verify agency is configured
- Troubleshoot agency-related feature failures

### W5: Create Agency Delegation

```bash
# Create agency delegation for SWR
hcloud SWR CreateAgency --cli-region=cn-north-4
```

**When to create agency**:
- `CheckAgency` returns `is_agency: false`
- You need to use image sync (requires OBS access)
- You need to create CCE triggers (requires CCE access)

**Post-creation Verification**:

```bash
hcloud SWR CheckAgency --cli-region=cn-north-4
```

Expected: `is_agency` should now be `true`.

### W6: List Repository Accessories

```bash
hcloud SWR ListRepoAccessories --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4
```

**Output Fields** (verified against actual API):

```json
{
  "total": 0,
  "accessories": null
}
```

- `total`: Total count of accessories
- `accessories`: Array of accessory objects (null when empty)

### W7: List Repository References

```bash
hcloud SWR ListReferences --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4
```

## Common Scenarios

### S1: Pre-Deployment Feature Check

Before deploying features that depend on SWR capabilities:

```bash
# Check sharing features
hcloud SWR ShowShareFeatureGates --cli-region=cn-north-4

# Check global features
hcloud SWR ListGlobalFeatureGates --cli-region=cn-north-4

# Check agency
hcloud SWR CheckAgency --cli-region=cn-north-4
```

### S2: Setup for Image Sync

Before configuring cross-region image sync:

```bash
# 1. Check if image sync feature is enabled
hcloud SWR ShowShareFeatureGates --cli-region=cn-north-4
# Verify enable_image_sync is true

# 2. Check if OBS feature is enabled
hcloud SWR ListGlobalFeatureGates --cli-region=cn-north-4
# Verify enableUserDefObs is true

# 3. Check and configure agency
hcloud SWR CheckAgency --cli-region=cn-north-4
# If is_agency is false:
hcloud SWR CreateAgency --cli-region=cn-north-4
```

### S3: Audit Shared Image Inventory

Review all shared repositories across the organization:

```bash
# List all shared repositories
hcloud SWR ListSharedReposDetails --cli-region=cn-north-4

# For specific shared repos, check accessories and references
hcloud SWR ListRepoAccessories --namespace=<ns> --repository=<repo> --cli-region=cn-north-4
hcloud SWR ListReferences --namespace=<ns> --repository=<repo> --cli-region=cn-north-4
```