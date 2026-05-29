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

```bash
┌─────────────────────────────────────────────────────────────┐
│                    Flexus L Lifecycle Skill                  │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐              │
│  │  Create  │  │ Renewal  │  │  Unsubscribe │              │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘              │
│       │             │                │                       │
│       └─────────────┴────────────────┘                       │
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
| `show-images` | Show available images | None | `--region`, `--type` |
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
| `--image` | `Ubuntu:22.04` | Ubuntu 22.04 system image |
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
# Show all images
python scripts/flexus_lifecycle.py show-images --region cn-north-4

# Show only system images
python scripts/flexus_lifecycle.py show-images --region cn-north-4 --type system

# Show only app images
python scripts/flexus_lifecycle.py show-images --region cn-north-4 --type app
```

**Show available specs for an image:**

```bash
python scripts/flexus_lifecycle.py show-specs --region cn-north-4 --image Ubuntu:22.04
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
  --image Ubuntu:22.04 \
  --cpu 2 \
  --memory 4
```

#### Method 2: Specify Spec

```bash
python scripts/flexus_lifecycle.py create-instance \
  --ak <AK> --sk <SK> \
  --region cn-north-4 \
  --image Ubuntu:22.04 \
  --plan-spec hf.medium.1.linux
```

#### Method 3: Use Default Spec

```bash
# Use first available spec from config
python scripts/flexus_lifecycle.py create-instance \
  --ak <AK> --sk <SK> \
  --region cn-north-4 \
  --image Ubuntu:22.04
```

**Create Parameters:**

| Parameter | Description | Default |
| ----------- | ------------- | --------- |
| `--image` | Image (format: name:version) | Ubuntu:22.04 |
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

## File Structure

```bash
huawei-cloud-flexus-l-server-manage/
├── SKILL.md                    # English skill documentation
├── references/                 # Reference documentation
│   ├── api-reference.md        # English API reference
│   ├── iam-policies.md         # IAM policy definitions
│   ├── image-specs-guide.md    # System image specs reference
│   ├── permission-guide.md     # Permission setup guide
│   └── troubleshooting.md     # Troubleshooting guide
└── scripts/                    # Executable scripts and configs
    ├── config.json             # Region mapping config
    ├── flexus_lifecycle.py     # Unified lifecycle management script
    ├── image_specs.json        # System image specs config
    └── pyproject.toml          # Python dependencies config
```

### image_specs.json Configuration

The image specs config file contains:

```json
{
  "spec_definitions": {
    // Appendix 2: Spec details for each code
    "hf.small.1.linux": {"vcpu": 2, "memory": 2, "disk": 40, "os": "linux"},
    "hf.medium.1.linux": {"vcpu": 2, "memory": 4, "disk": 70, "os": "linux"},
    // ...
  },
  "regions": {
    "cn-north-4": {
      "system_images": {
        // Appendix 1: Spec codes for each image type
        "Ubuntu": {
          "22.04": ["hf.small.1.linux", "hf.medium.1.linux", ...]
        }
      }
    }
  }
}
```

**Update Config:** Sync this file when official documentation updates.

---

## Dependencies

- Python 3.8+
- huaweicloudsdkcore >= 3.1.0
- huaweicloudsdkbss >= 3.1.0
- requests >= 2.31.0

### Install Huawei Cloud SDK

**⚠️ Must use Huawei Cloud mirror for faster installation:**

```bash
pip install -i https://repo.huaweicloud.com/repository/pypi/simple huaweicloudsdkcore huaweicloudsdkbss requests
```

---

## Important Warnings

1. **Cost Warning**: Creating instances incurs costs, unsubscribing may involve refunds
2. **Data Loss Risk**: Instance data may be unrecoverable after unsubscribe
3. **Irreversible Operation**: Unsubscribe cannot be undone
4. **Credential Security**: Never save AK/SK to configuration files

---

## Error Handling

| Error Code | Description | Suggestion |
| ------------ | ------------- | ------------ |
| 401 | Authentication failed | Check if AK/SK is correct |
| 403 | Permission denied | Check Flexus L service permissions |
| 404 | Resource not found | Check resource ID |
| HCSS.14000001 | Spec code mismatch | Check spec prefix matches region (Guiyang 1 uses ahf.*) |
| BSS.0501 | Resource not found or not owned | Verify resource ID |
| BSS.0502 | Resource state not operable | Check resource state |

---

## References

This skill includes the following reference documents in the `references/` directory:

| Document | Description |
| ---------- | ------------- |
| [api-reference.md](references/api-reference.md) | Huawei Cloud API Reference (English) |
| [api-reference-cn.md](references/api-reference-cn.md) | Huawei Cloud API Reference (Chinese) |
| [iam-policies.md](references/iam-policies.md) | IAM Permissions and Policy Configuration |
| [permission-guide.md](references/permission-guide.md) | IAM Permission Configuration Guide |
| [troubleshooting.md](references/troubleshooting.md) | Troubleshooting Guide |
| [image-specs-guide.md](references/image-specs-guide.md) | System Image Specs Reference |

### External References

- [Flexus L Instance Purchase Guide](https://support.huaweicloud.com/api-flexusl/create_instance_0001.html) - Official API Documentation
- [AK/SK Authentication](https://support.huaweicloud.com/api-iam/iam_01_0001.html) - IAM Authentication Guide
- [Huawei Cloud Console](https://console.huaweicloud.com/) - Resource Management Console

---
