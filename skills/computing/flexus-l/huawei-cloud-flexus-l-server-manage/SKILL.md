---
name: huawei-cloud-flexus-l-server-manage
description: >-
  Manages Huawei Cloud Flexus L server lifecycle: create, renew, and unsubscribe instances.
  Use this skill when the user mentions "Flexus L", "Huawei Cloud lightweight server", "purchase server", "renew", "unsubscribe".
  (中文触发词："购买/创建L实例", "L实例续费", "L实例退订")
tags: [Flexus L, lifecycle management, create, renewal, unsubscribe]
---

# Huawei Cloud Flexus L Instance Lifecycle Management Skill

## Overview

This skill provides core lifecycle management capabilities for Huawei Cloud Flexus L instances:

| Module | Description | Command |
| -------- | ------------- | --------- |
| **Query Regions** | Show available regions | `show-regions` |
| **Query Images** | Show available images | `show-images` |
| **Query Specs** | Show available specs | `show-specs` |
| **Create** | Purchase new Flexus L instances | `create-instance` |
| **Renewal** | Renew existing instances | `renewal` |
| **Unsubscribe** | Cancel instance subscription | `unsubscribe` |

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Flexus L Lifecycle Skill                  │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐              │
│  │  Create  │  │ Renewal  │  │  Unsubscribe │              │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘              │
│       │             │                │                       │
│       └─────────────┴────────────────┘                       │
│                     │                                        │
│       ┌─────────────▼─────────────┐                         │
│       │  flexus_specs_extractor  │                         │
│       └─────────────┬─────────────┘                         │
│                     │                                        │
│              ┌──────▼──────┐                                 │
│              │  HCSS API   │  (Instance Management)          │
│              └──────┬──────┘                                 │
│              ┌──────▼──────┐                                 │
│              │  BSS API    │  (Billing & Subscription)       │
│              └──────┬──────┘                                 │
│              ┌──────▼──────┐                                 │
│              │  IAM API    │  (Project ID)                   │
│              └─────────────┘                                 │
└─────────────────────────────────────────────────────────────┘
```

### Data Source

- **Region, Image, Spec Information**: Dynamically fetched from official documentation, no local config file needed
- **Official Documentation**: https://support.huaweicloud.com/api-flexusl/create_instance_0001.html
- **On-Demand Fetch**: Automatically fetches latest data when executing `show-regions`, `show-images`, `show-specs`, `create-instance`

### Use Cases

1. **Automated Server Provisioning** - Create Flexus L instances for development, testing, or production environments
2. **Cost Optimization** - Renew instances during promotional periods to save costs
3. **Resource Cleanup** - Safely unsubscribe instances when projects end
4. **Multi-Region Deployment** - Create instances across different regions for disaster recovery

### Applicable Scenarios

- Development and testing environment setup
- Production server lifecycle management
- Cost control and budget management
- Project resource cleanup and decommissioning

## Prerequisites

Before using this skill, ensure the following conditions are met:

### 1. Huawei Cloud Account

- Valid Huawei Cloud account
- Account has completed real-name verification
- Account has sufficient balance or bound payment method

### 2. AK/SK Credentials

- Created Huawei Cloud access keys (AK/SK)
- AK/SK has the following permissions:
  - `BSS`: Billing service (order query, renewal, unsubscribe)
  - `HCSS`: Flexus L instance management
  - `IAM`: Project ID query (read-only)
- How to obtain: [Huawei Cloud Console](https://console.huaweicloud.com/) → My Credentials → Access Keys → Create Access Key

### 3. IAM Permissions

| Service | Policy | Required Actions |
| --------- | -------- | ------------------ |
| HCSS | `HCSS FullAccess` | `hcss:lightInstances:*` |
| BSS | `BSS Administrator` | `bss:order:*`, `bss:renewal:*`, `bss:unsubscribe:*` |
| IAM | `IAM ReadOnlyAccess` | `iam:projects:list` |

**Permission Failure Handling:**

| Error | Cause | Solution |
| ------- | ------- | ---------- |
| `403 Forbidden` | Missing policy | Add required IAM policy to user |
| `APIGW.0101` | Service not enabled | Enable Flexus L in target region |
| `BSS.0501` | No access to resource | Verify resource belongs to account |

See [references/permission-guide.md](references/permission-guide.md) for detailed permission setup.

### 4. Runtime Environment

- Python 3.8 or higher
- Required dependencies installed (see Dependencies section below)

### 5. Network Environment

- Able to access Huawei Cloud API endpoints
- Required endpoints:
  - `hcss.cn-north-4.myhuaweicloud.com`
  - `iam.myhuaweicloud.com`
  - `bss.myhuaweicloud.com`
- If using proxy, configure environment variables correctly

## Trigger Rules

Activate this skill when users mention:

**Create related:**

- "Purchase Huawei Cloud server", "Create Flexus instance", "Huawei Cloud lightweight server"
- "hcss instance", "New Flexus L"

**Renewal related:**

- "Renew Flexus L instance", "Flexus renewal", "Renew lightweight server"
- "Huawei Cloud renewal", "renew flexus"

**Unsubscribe related:**

- "Unsubscribe Flexus L instance", "Cancel Flexus instance", "Unsubscribe lightweight server"
- "Huawei Cloud unsubscribe", "cancel subscription flexus"

---

## ⚠️ Conversation Display Guidelines (Important)

**When displaying "Available Specifications" or "Available Images" to users in conversation, you MUST immediately append the following note:**

> **Note**
>
> - Spec codes vary by region and image version. Please refer to the official documentation Appendix 1 (spec codes for each image type) and Appendix 2 (spec details for each code) before purchasing.
> - Official Link: <https://support.huaweicloud.com/api-flexusl/create_instance_0001.html#create_instance_0001__section1881914176434>

**This applies to all conversation scenarios, including dry-run previews.**

---

## Security Notes

**⚠️ AK/SK Security Requirements:**

- AK/SK must be provided by user each time, never saved to any configuration file
- Supports environment variables: `CLOUD_SDK_AK` and `CLOUD_SDK_SK`
- Supports command-line parameters: `--ak` and `--sk`

---

## Core Commands

| Command | Function | Required Params | Optional Params |
|---------|----------|-----------------|-----------------|
| `show-regions` | Show available regions | None | None |
| `show-images` | Show available images | None | `--region` |
| `show-specs` | Show available specs | `--image` | `--region` |
| `create-instance` | Create instance | `--ak`, `--sk` | `--region`, `--image`, `--plan-spec`, `--cpu`, `--memory`, `--period-num`, `--period-type`, `--instance-name`, `--auto-renew`, `--auto-pay`, `--dry-run`, `--confirm` |
| `renewal` | Renew instance | `--ak`, `--sk`, `--resource-ids` | `--period-num`, `--period-type`, `--auto-pay`, `--dry-run`, `--confirm` |
| `unsubscribe` | Unsubscribe instance | `--ak`, `--sk`, `--resource-ids` | `--type`, `--reason`, `--dry-run`, `--confirm` |

---

## Parameter Confirmation

**Required Parameter Validation:**

| Parameter | Description | Validation Rule |
|-----------|-------------|-----------------|
| `--ak` | Huawei Cloud Access Key ID | Non-empty, 20 characters |
| `--sk` | Huawei Cloud Secret Access Key | Non-empty, 40 characters |
| `--resource-ids` | Resource IDs | Non-empty, comma-separated for multiple |
| `--image` | Image name | Format: `name:version`, e.g. `Ubuntu:22.04` |
| `--region` | Region ID | Must be in supported regions list |

**Parameter Relationships:**

| Parameter Group | Description |
|-----------------|-------------|
| `--plan-spec` vs `--cpu/--memory` | Choose one; `--plan-spec` takes priority; if not specified, auto-match based on `--cpu/--memory` |
| `--dry-run` vs `--confirm` | Choose one or neither; `--dry-run` previews only, `--confirm` skips confirmation, neither triggers interactive confirmation |

**Default Values:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--region` | `cn-north-4` | North China - Beijing 4 |
| `--image` | `Ubuntu` | Ubuntu system image |
| `--period-num` | `1` | Purchase/renew for 1 month |
| `--period-type` | `month` | Monthly billing |
| `--type` (unsubscribe) | `1` | Immediate unsubscribe |
| `--auto-renew` | `True` | Enable auto renewal |
| `--auto-pay` | `True` | Auto payment |

---

## ⚠️ Mandatory Confirmation Mechanism

**Creation, renewal, and cancellation operations involve actual costs and must be executed only after explicit confirmation from the user!**

Confirmation methods (choose one):

1. **Dialog confirmation**: Reply "confirm" or "yes" in conversation
2. **Command-line confirmation**: Use `--confirm` flag
3. **Dry-run preview**: Use `--dry-run` to preview without executing

**⚠️ Failure Handling Rule:**

When user confirms the preview order and the purchase fails:
- **Only make ONE request** - do not retry automatically
- **Return the failure reason** to the user
- **Guide user to repurchase** - let user decide next steps
- **NEVER change parameters** (region, spec, image, etc.) without user's explicit request

---

## Usage

### Basic Command Format

```bash
python scripts/flexus_lifecycle.py <command> [options] --ak <AK> --sk <SK>
```

### Global Parameters

| Parameter | Description | Required |
| ----------- | ------------- | ---------- |
| `--ak` | Huawei Cloud Access Key ID | Yes |
| `--sk` | Huawei Cloud Secret Access Key | Yes |
| `--region` | Region ID (default: cn-north-4) | No |
| `--dry-run` | Dry run, don't actually execute | No |
| `--confirm` | Force confirmation, skip interactive | No |

---

## Module Details

### 0️⃣ Query Functions

**Show available regions:**

```bash
python scripts/flexus_lifecycle.py show-regions
```

**Show available images for a region:**

```bash
python scripts/flexus_lifecycle.py --region cn-north-4 show-images
```

**Show available specs for an image:**

```bash
python scripts/flexus_lifecycle.py --region cn-north-4 show-specs --image Ubuntu
```

---

### 1️⃣ Create Instance (create-instance)

Purchase new Flexus L instances, supports Windows/Linux.

#### Method 1: Auto-match Spec (Recommended)

```bash
# Auto-match spec based on CPU and memory
python scripts/flexus_lifecycle.py create-instance \
  --ak <AK> --sk <SK> \
  --region cn-north-4 \
  --image Ubuntu \
  --cpu 2 \
  --memory 4
```

#### Method 2: Specify Spec

```bash
python scripts/flexus_lifecycle.py create-instance \
  --ak <AK> --sk <SK> \
  --region cn-north-4 \
  --image Ubuntu \
  --plan-spec hf.medium.1.linux
```

#### Method 3: Use Default Spec

```bash
# Use first available spec from config
python scripts/flexus_lifecycle.py create-instance \
  --ak <AK> --sk <SK> \
  --region cn-north-4 \
  --image Ubuntu
```

**Create Parameters:**

| Parameter | Description | Default |
| ----------- | ------------- | --------- |
| `--image` | Image name | Ubuntu |
| `--plan-spec` | Instance specification | Auto-match or config default |
| `--cpu` | CPU cores (for auto-match) | - |
| `--memory` | Memory GB (for auto-match) | - |
| `--period-num` | Purchase duration (months) | 1 |
| `--period-type` | Period type (month/year) | month |
| `--instance-name` | Instance name | Auto-generated |
| `--auto-renew` | Auto renewal | True |
| `--auto-pay` | Auto payment | True |

**Available Specifications Reference:**

See [references/image-specs-guide.md](references/image-specs-guide.md) for detailed specs.

---

### 2️⃣ Renewal Instance (renewal)

Renew existing Flexus L instances.

```bash
# Preview renewal (recommended)
python scripts/flexus_lifecycle.py renewal \
  --resource-ids <resource-id> \
  --period-num 1 \
  --period-type month \
  --dry-run \
  --ak <AK> --sk <SK>

# Confirm renewal
python scripts/flexus_lifecycle.py renewal \
  --resource-ids <resource-id> \
  --period-num 6 \
  --period-type month \
  --confirm \
  --ak <AK> --sk <SK>

# Renew multiple instances
python scripts/flexus_lifecycle.py renewal \
  --resource-ids id1,id2,id3 \
  --period-num 1 \
  --period-type year \
  --confirm \
  --ak <AK> --sk <SK>
```

**Renewal Parameters:**

| Parameter | Description | Default |
| ----------- | ------------- | --------- |
| `--resource-ids` | Resource IDs (comma-separated) | Required |
| `--period-num` | Renewal period count | 1 |
| `--period-type` | Period type (month/year) | month |
| `--auto-pay` | Auto payment | True |

---

### 3️⃣ Unsubscribe Instance (unsubscribe)

Cancel Flexus L instance subscription.

```bash
# Preview unsubscribe (recommended)
python scripts/flexus_lifecycle.py unsubscribe \
  --resource-ids <resource-id> \
  --dry-run \
  --ak <AK> --sk <SK>

# Immediate unsubscribe (type 1)
python scripts/flexus_lifecycle.py unsubscribe \
  --resource-ids <resource-id> \
  --type 1 \
  --confirm \
  --ak <AK> --sk <SK>

# Expiry unsubscribe (type 2)
python scripts/flexus_lifecycle.py unsubscribe \
  --resource-ids <resource-id> \
  --type 2 \
  --confirm \
  --ak <AK> --sk <SK>

# Batch unsubscribe
python scripts/flexus_lifecycle.py unsubscribe \
  --resource-ids id1,id2,id3 \
  --type 1 \
  --reason "Project ended" \
  --confirm \
  --ak <AK> --sk <SK>
```

**Unsubscribe Parameters:**

| Parameter | Description | Default |
| ----------- | ------------- | --------- |
| `--resource-ids` | Resource IDs (comma-separated) | Required |
| `--type` | Unsubscribe type (1=immediate, 2=expiry) | 1 |
| `--reason` | Unsubscribe reason | None |

**Unsubscribe Types:**

| Type | Description | Effect |
| ------ | ------------- | -------- |
| 1 | Unsubscribe resource and renewed periods | Resource stops immediately, pro-rated refund |
| 2 | Only unsubscribe renewed periods | Resource continues until expiry |

---

## Available Regions

> **⚠️ Note**: Flexus L instances currently support only the following regions:

| Region ID | Region Name | Spec Prefix |
| ----------- | ------------- | ------------- |
| cn-north-4 | North China - Beijing 4 | `hf.*` |
| cn-east-3 | East China - Shanghai 1 | `hf.*` |
| cn-south-1 | South China - Guangzhou | `hf.*` |
| cn-southwest-2 | Southwest China - Guiyang 1 | `ahf.*` |
| ap-southeast-1 | Hong Kong, China | `hf.*` |
| ap-southeast-3 | Asia Pacific - Singapore | `hf.*` |

---

## Dependencies

### Python Dependencies

Install via pip:

```bash
pip install requests huaweicloudsdkcore huaweicloudsdkbss
```

Or use pyproject.toml:

```bash
cd scripts
pip install -e .
```

### pyproject.toml

```toml
[project]
name = "flexus-lifecycle"
version = "1.0.0"
dependencies = [
    "requests>=2.28.0",
    "huaweicloudsdkcore>=3.0.0",
    "huaweicloudsdkbss>=3.0.0",
]
```

---

## File Structure

```
skills/huawei-cloud-flexus-l-server-manage/
├── SKILL.md                    # This file
├── scripts/
│   ├── flexus_lifecycle.py     # Main lifecycle script
│   ├── flexus_specs_extractor.py  # Dynamic specs fetcher
│   └── pyproject.toml          # Dependencies
└── references/
    ├── api-reference.md        # API reference
    ├── iam-policies.md         # IAM policies
    ├── image-specs-guide.md    # Image specs guide
    ├── permission-guide.md     # Permission setup
    └── troubleshooting.md      # Troubleshooting
```

---

## Error Handling

### Common Errors

| Error Code | Description | Solution |
| ------------ | ------------- | ---------- |
| `401 Unauthorized` | Invalid AK/SK | Verify AK/SK is correct and active |
| `403 Forbidden` | Permission denied | Add required IAM policies |
| `APIGW.0101` | API not found | Check service is enabled in region |
| `APIGW.0301` | Signature verification failed | Check SK is correct |
| `BSS.0501` | Resource not found | Verify resource ID is correct |
| `BSS.0502` | Resource state invalid | Check resource status |
| `400 Bad Request` | Invalid parameters | Check spec/image compatibility |

See [references/troubleshooting.md](references/troubleshooting.md) for detailed error handling.

---

## References

- [API Reference](references/api-reference.md)
- [IAM Policies](references/iam-policies.md)
- [Image Specs Guide](references/image-specs-guide.md)
- [Permission Guide](references/permission-guide.md)
- [Troubleshooting](references/troubleshooting.md)

### External References

- [Flexus L Instance Purchase Guide](https://support.huaweicloud.com/api-flexusl/create_instance_0001.html) - Official API Documentation
- [AK/SK Authentication](https://support.huaweicloud.com/api-iam/iam_01_0001.html) - IAM Authentication Guide
- [Huawei Cloud Console](https://console.huaweicloud.com/) - Resource Management Console

---
