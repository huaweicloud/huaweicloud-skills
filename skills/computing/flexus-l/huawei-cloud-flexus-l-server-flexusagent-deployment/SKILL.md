---
name: huawei-cloud-flexus-l-server-flexusagent-deployment
description: >
  Deploy AI Agent development platform (Dify) on Huawei Cloud Flexus L instance, providing deployment operations, password management, MaaS model configuration, and workflow import capabilities.
  Trigger keywords: deploy flexusagent/一键部署Flexus AI Agent开发平台、change password/修改开发平台管理员密码、change dify password/修改dify平台密码、add maas provider/添加MaaS模型供应商、configure maas model/配置MaaS模型、view workflow/查看AI Agent工作流、import workflow/导入AI Agent工作流
tags:
  - Deploy Flexus AI Agent
  - Deploy AI Agent Platform(Dify) On Huawei Cloud Flexus L
  - Change AI Agent Development Platform Admin Password
  - MaaS Model Configuration
  - View FlexusAgent Workflow
  - Workflow Import
metadata: {"flexusagent": {"version": "1.0.0", "requires": {"bins": ["uv", "python3"]}, "install": [{"kind": "uv", "command": "uv sync --index-url https://repo.huaweicloud.com/repository/pypi/simple"}]}}
---

⚠️ **Security Execution Rules (Highest Priority)**:
  1. All scripts MUST be executed via skill action=exec, NEVER run directly in shell
  2. NEVER print script contents or commands containing AK/SK/Token in conversation
  3. NEVER create temporary script files, prefer inline execution (python -c)
  4. On execution failure, only return error info, do NOT rewrite scripts or print full commands
  5. AK/SK/Token MUST be passed via environment variables, NEVER appear in conversation
  6. ⚠️ ABSOLUTELY NEVER expose, log, or print AK/SK/Token values in any form - this is a critical security requirement
  7. When using skill action=exec, credentials are automatically inherited from environment variables (HW_ACCESS_KEY, HW_SECRET_KEY,   HW_SECURITY_TOKEN), no need to pass them as command line arguments

# Huawei Cloud Flexus L Instance FlexusAgent One-Click Deployment Skill (Lite)

## Overview

Deploy AI Agent development platform (Dify) on Huawei Cloud Flexus L instance, providing complete deployment and operation capabilities.

**Core Function Modules**:

| Module | Function | Command |
| -------- | ------------- | --------- |
| **Deploy** | One-click deploy AI Agent development platform on Flexus L instance | `deploy` |
| **Password Change** | Change development platform admin password via COC (**must execute after first deployment**) | `passwd` |
| **MaaS Model Config** | Add Huawei Cloud MaaS model provider, integrate DeepSeek, Qwen models | `maas` |
| **Workflow View** | View list of replicable AI Agent workflow templates | - |
| **Workflow Import** | Quickly import specified workflow to workspace | `import-app-workflow` |

### Architecture

**Core File Structure and Function Description**:

```
scripts/
├── caller.py                 # CLI main entry, command line argument parsing and routing
├── lib.py                    # Core business logic library, includes API calls and data processing
├── deploy.py                 # Deployment module, creates Flexus L instance and FlexusAgent
├── passwd.py                 # Password management module, modifies admin password via COC
├── maas.py                   # MaaS integration module, configures model provider
├── app_workflow_import.py    # Workflow import module, imports preset workflow templates
├── sg_rule.py                # Security group management module, configures network access rules
├── uniagent.py               # UniAgent status query module
└── utils.py                  # Utility function library
```

### Important Notes

**⚠️ All scripts and environment check scripts are in the skill package. Must execute via skill action=exec, do not run directly in shell.**

## Prerequisites

Before using this skill, ensure the following conditions are met:

### 1. Huawei Cloud Account and Credentials

- Valid Huawei Cloud account
- Huawei Cloud AK/SK credentials with the following permissions:
  - Create Flexus L instance
  - Access COC (Cloud Operations Center) service

**Credential Acquisition Methods**:

This skill supports obtaining Huawei Cloud credentials through the following methods (in order of priority from high to low):

**Credential Types**:
- **Long-term AK/SK**: Permanent credentials, no security_token required
- **Temporary AK/SK**: Temporary credentials with limited validity period, security_token required

1. **Environment Variables (Default)** (highest priority)
   - `HW_ACCESS_KEY`: Huawei Cloud Access Key AK
   - `HW_SECRET_KEY`: Huawei Cloud Access Key SK
   - `HW_SECURITY_TOKEN`: Security token (optional, only required for temporary credentials)

2. **Command-line Arguments** (used when environment variables are not set)
   - `--ak`: Huawei Cloud Access Key AK
   - `--sk`: Huawei Cloud Access Key SK
   - `--security-token`: Security token (optional, only required for temporary credentials)

3. **Interactive Input** (when neither of the above is provided)
   - Program will prompt user to enter AK/SK and other credential information

**Important Notes**:
- Long-term AK/SK: Permanent credentials that never expire, no security_token needed
- Temporary AK/SK: Obtained through IAM interface with limited validity period, must provide security_token

### 2. IAM Permissions

| Service | Policy | Required Operations |
| --------- | -------- | ------------------ |
| HCSS | `HCSS FullAccess` | `hcss:lightInstances:*` |
| COC | `COC FullAccess` | `coc:commands:*` |
| IAM | `IAM ReadOnlyAccess` | `iam:projects:list` |
| VPC | `VPC FullAccess` | `vpc:securityGroups:*` |

**Permission Failure Handling**:

| Error | Cause | Solution |
| ------- | ------- | ---------- |
| `403 Forbidden` | Missing policy | Add required IAM policy for user |
| `APIGW.0101` | Service not enabled | Enable Flexus L service in target region |

---

## Security Instructions

**⚠️ Credential Security Requirements (Critical):**
- Credentials must be handled securely, never displayed in conversation
- Skill will automatically use pre-configured credentials

**⚠️ Absolute Security Rules:**
1. **Never print, log, or display credential values in any form**
2. **Never include credentials in error messages or debug output**
3. **Never store credentials in files or configurations**
4. **Never transmit credentials through insecure channels**
5. **When using sensitive parameters, must mask them in any output**

---

## ⚠️ Mandatory Confirmation Mechanism

**Deployment operations involve actual costs, require explicit confirmation!**

Confirmation Methods:
1. **Conversation Confirmation**: Reply "confirm" or "yes" in conversation
2. **Command Line Confirmation**: Use `--non-interactive` flag

**Failure Handling**:
- Only initiate one request, no automatic retry
- Return failure reason to user
- Guide user to re-deploy, let user decide next operation
- Never change parameters without user's explicit request

---

## Core Commands and Workflow

### 1️⃣ Deploy AI Agent Development Platform on Flexus L Instance

**⚠️ Cost Reminder**: Deploying Flexus L instance will incur costs, ensure account has sufficient balance. **Deployment requires explicit user confirmation.**

**Deployment Notes**:
- Automatically create Huawei Cloud Flexus L instance and deploy AI Agent development platform
- Default account: `super@dify.com`
- **⚠️ Must change admin password immediately after first deployment**

```bash
# Interactive mode
python scripts/caller.py deploy

# Non-interactive mode
python scripts/caller.py deploy \
  --name FlexusAgent-{timestamp} \
  --region cn-north-4 \
  --spec hf.xlarge.1.linux \
  --ak <AK> \  # Long-term AK or temporary AK
  --sk <SK> \  # Long-term SK or temporary SK
  --security-token <security-token> \
  --non-interactive
```

**Command Parameters**:

| Parameter | Description | Required | Default | Notes |
| ----------- | ------------- | ---------- | --------- |------ |
| `--name` | Instance name | No | `FlexusAgent-{timestamp}` | - |
| `--region` | Deployment target region ID | Yes | Prompt for input | - |
| `--spec` | Instance spec | Yes | Prompt for input | - |
| `--ak` | Huawei Cloud Access Key AK | Yes | From env vars or prompt | Supports both long-term and temporary AK |
| `--sk` | Huawei Cloud Access Key SK | Yes | From env vars or prompt | Supports both long-term and temporary SK |
| `--security-token` | Security token | No | From env vars or prompt | **Only required for temporary credentials**, not needed for long-term credentials |
| `--non-interactive` | Run in non-interactive mode | No | false | - |

**Available Regions**:

| Region ID | Region Name |
| ----------- | ------------- |
| cn-north-4 | North China-Beijing 4 |
| cn-east-3 | East China-Shanghai 1 |
| cn-south-1 | South China-Guangzhou |
| cn-southwest-2 | Southwest China-Guiyang 1 |

Currently only the above regions are supported. For other regions, users can be reminded to check the console at https://console.huaweicloud.com/smb/#/create/hecs-light or the official introduction page at https://support.huaweicloud.com/api-flexusl/create_instance_0001.html.

**Spec Selection Logic**:
You can list the Huawei Cloud L instance official spec introduction page at https://support.huaweicloud.com/productdesc-flexusl/pd_01_0003.html, let the user select an appropriate spec, then execute deployment. Note: The minimum requirement for agent images is 2U2G. For bid writing agent, it is recommended to use the 4U16G spec.

**Default Configuration**:
- **Image**: FlexusAgent 1.7.1
- **Billing**: Yearly/Monthly (prepaid)
- **EVS Disk**: 50GB
- **CBR Backup**: 50GB
- **HSS Host Security**: Enabled
- **Web UI**: `http://<public-ip>:80`

> **Important**: Project ID is automatically obtained through IAM API.

---

**📢 Post-Deployment Action Reminder**:

After step 1️⃣ deployment completes, **ask user whether to execute the following subsequent operations**. After each step completes, ask user whether to continue with remaining steps.

| Step | Operation | Required | Description |
|------|------|----------|------|
| **2️⃣** | Change admin password and get instance details | ⚠️ **Required** | First query instance details (floating IP, resource ID), then change password |
| **3️⃣** | Integrate MaaS model | Optional | Add Huawei Cloud MaaS model provider (DeepSeek, Qwen, etc.) |
| **4️⃣** | View workflow list | Optional | View importable AI Agent workflow templates |
| **5️⃣** | Import workflow | Optional | Import preset workflow templates to instance |

**Execution Order Recommendation**:
1. After deployment completes, **immediately ask user whether to change password (step 2)**
2. After user agrees, AI Agent automatically executes: query instance details → change password → return access information
3. After password change, ask user whether to integrate MaaS model (step 3)
4. If quick AI application deployment is needed, guide user to view and import workflows (steps 4, 5)

---

### 2️⃣ Change Admin Password and Get Instance Details (Required)

**⚠️ Important Note**: This step includes two auto-executed sub-steps: First query instance details to get floating IP and resource ID, then change admin password.

**Change Password & Query Instance Details**

```bash
# Interactive mode
python scripts/caller.py passwd
python scripts/caller.py query-instance --instance-id <instance-id-from-step1>

# Non-interactive mode - Change password & Query instance details
- Query instance details
python scripts/caller.py passwd \
  --resource-id <instance-id-from-step1>        # Required: L instance resource ID
  --region-id <instance-region>               # Required: Instance region (e.g., cn-north-4)
  --admin-password <new-admin-password>            # Required: New admin password
  --ak <AK>                            # Required: Huawei Cloud Access Key AK or temporary AK
  --sk <SK>                            # Required: Huawei Cloud Access Key SK or temporary SK
  --security-token <security-token>               # No: Security token (required when using temporary AK/SK credentials)
  --non-interactive                        # Optional: Non-interactive mode

- Query instance details
python scripts/caller.py query-instance \
  --instance-id <instance-id-from-step1>        # Required: Instance resource ID
  --ak <AK>                            # Required: Huawei Cloud Access Key AK or temporary AK
  --sk <SK>                            # Required: Huawei Cloud Access Key SK or temporary SK
  --security-token <security-token>               # Required: Security token (only required for temporary credentials)
```

**Return Information**:
- Resource ID (resource_id) - Used for password change command
- Floating IP (floating_ip) - Used for Web UI access address
- Instance name, UniAgent status, Fixed IP, Region, etc.

> **Must Execute After First Deployment**: Must set password after first deployment, otherwise cannot login to Web UI.
> **Mandatory Constraint**: After changing password, reply: `"Web UI: http://<public-ip>:80; Login email: super@dify.com, Password: <new-password>"`

---

### 3️⃣ Integrate MaaS Model (Optional)

```bash
# Interactive mode
python scripts/caller.py maas

# Non-interactive mode
python scripts/caller.py maas \
  --flexusagent-base-url http://<public-ip>:80    # Required: FlexusAgent Web UI URL
  --flexusagent-email <email>                  # Required: FlexusAgent admin email
  --flexusagent-password <password>               # Required: FlexusAgent admin password
  --maas-api-key <api-key>                    # Required: ModelArts MaaS API key
  --non-interactive                           # Optional: Non-interactive mode
```

**Note**: Automatically install `langgenius/maas` plugin and configure credentials. Default includes DeepSeek, Qwen, etc. models. This step operates via HTTP API, does not require AK/SK credentials.

---

### 4️⃣ View FlexusAgent Workflow List (Optional)

**Purpose**: View preset FlexusAgent workflow templates for quick AI application deployment.

**Access Method**: Get workflow list through OBS

```bash
# Request URL (timestamp parameter to avoid cache)
curl "https://flexus-config-cn-north-4-product.obs.cn-north-4.myhuaweicloud.com/stable/dify/dify-templates/national/index.json?timestamp=$(date +%s)"
```

**Response Format Example**:

```json
{
  "total": 15,
  "categories": [
    {
      "code": "Smart_Bid",
      "name": "Smart Bid"
    }
  ],
  "list": [
    {
      "id": "Bid_Writing_And_Templated_Adaptation",
      "title": "Bid Writing and Templatized Adaptation Agent",
      "desc": "Intelligent bid document analysis, intelligent bid writing and adaptation, supports open bid and sealed bid types, conversational bid document generation, word document output.",
      "categoryList": [
        {
          "category": "Smart Bid",
          "categoryCode": "Smart_Bid"
        }
      ]
    }
  ]
}
```

---

### 5️⃣ Import Workflow to Instance (Optional)

**Purpose**: Import preset workflow templates to instance for quick AI application deployment.

**Usage**:

```bash
# Interactive mode (recommended, can select workflow from list)
python scripts/caller.py import-app-workflow

# Non-interactive mode - Import workflow
python scripts/caller.py import-app-workflow \
  --resource-id <instance-resource-id>                # Required: L instance resource ID
  --region-id cn-north-4                    # Required: L instance region ID
  --flexusagent-email super@dify.com        # Required: FlexusAgent admin email
  --flexusagent-password <password>              # Required: FlexusAgent admin password
  --app-workflow-id Bid_Writing_And_Templated_Adaptation  # Required: Workflow ID
  --ak <AK>                                 # Required: Huawei Cloud Access Key AK or temporary AK
  --sk <SK>                                 # Required: Huawei Cloud Access Key SK or temporary SK
  --security-token <security-token>                # No: Security token (required when using temporary AK/SK credentials)
  --timeout 600                             # Optional: Execution timeout (seconds), default 600
  --non-interactive                         # Optional: Non-interactive mode
```

**Prerequisites**:
- UniAgent status must be ONLINE
- Admin email and password correct

**Execution Result Verification**:

Remind user to access FlexusAgent Web UI (http://<public-ip>:80/apps) to view application list and confirm workflow has been successfully imported.

---
  
## Parameter Confirmation

‌‌Before executing any command, the command's parameters must be confirmed.

---

## Error Handling

| Error Code | Description | Solution |
| ------------ | ------------- | ---------- |
| `401 Unauthorized` | Invalid AK/SK | Verify AK/SK |
| `403 Forbidden` | Permission denied | Add required IAM policy |
| `APIGW.0101` | Service not enabled | Enable service in target region |
| `APIGW.0301` | Signature verification failed | Check SK |
| `COC.0001` | COC service unavailable | Check COC service region |
| `400 Bad Request` | Invalid parameters | Check spec/image compatibility |

---

**Notes:**
- Flexus instance deployment takes **2~5 minutes**
- Success status codes: `200`, `201`, `202`
- Each deployment creates **one** instance only

---

## Reference Documents
| Document | Description |
|---|---|
|[Flexus L Instance Purchase Guide](https://support.huaweicloud.com/api-flexusl/create_instance_0001.html)| Purchasing a FlexusL Instance|
| [iam-policies.md](references/iam-policies.md) | IAM permission policies |
| [verification-method.md](references/verification-method.md) | Verification steps |
