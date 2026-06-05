---
name: huawei-cloud-flexus-l-server-ops
description: "Based on Huawei Cloud Flexus L API for instance management and operations. Supports querying instance list and details, querying traffic packages, batch start/stop/reboot instances, resetting passwords,    and modifying instance information. Suitable for daily operations, lifecycle management, configuration changes, traffic monitoring, and other scenarios for Flexus L instances. Triggers: Flexus L, Huawei Cloud ops, query instance, start, stop, reboot, reset password, modify info, check traffic, traffic package (中文触发词: L实例运维，查询L实例，L实例开机，L实例关机，L实例重启，L实例重置密码，查询L实例流量包)."
---

⚠️ Security Execution Rules (Highest Priority):
  1. All scripts MUST be executed via skill action=exec, NEVER run directly in shell
  2. NEVER print script contents or commands containing AK/SK/Token in conversation
  3. NEVER create temporary script files, prefer inline execution (python -c)
  4. On execution failure, only return error info, do NOT rewrite scripts or print full commands
  5. AK/SK/Token MUST be passed via environment variables, NEVER appear in conversation
  6. NEVER interactively collect Huawei Cloud credentials from users. Credentials MUST be obtained only through:
   - Temporary Security Credentials (STS Token) via environment variables
   - Permanent credentials via environment variables

# Huawei Cloud Flexus L Instance Operations

## Overview

This skill provides complete operational capabilities for Huawei Cloud Flexus L instances,
covering instance lifecycle management, configuration modification, monitoring queries,
and other core scenarios.

### Architecture

```
OpenClaw Agent → Flexus L Ops Skill → Huawei Cloud SDK → Huawei Cloud Services
                     │                      │                    │
                     │                      │                    ├─ Flexus L (instance/lifecycle/password)
                     │                      │                    └─ BSS (traffic query)
                     │                      │
                     └─ scripts/            └─ huaweicloudsdk{core,ecs,bss,config}
```

**Core Components:**
- **Flexus L Service**: Elastic Cloud Server, provides instance management, lifecycle control, password reset, etc.
- **BSS Service**: Business Support System, provides traffic package usage query
- **Python SDK**: Official Huawei Cloud SDK, encapsulates API call logic
- **Operation Scripts**: 6 independent scripts, each corresponding to one operation

### Applicable Scenarios

**Typical Problem Scenarios:**
1. **Instance Status View**: Need to quickly view the running status of all Flexus L instances under the account
2. **Batch Operations**: Need to perform start, stop, reboot operations on multiple servers
3. **Configuration Modification**: Need to modify instance name, description, hostname, and other basic information
4. **Password Management**: Need to reset instance login password
5. **Traffic Monitoring**: Need to view traffic package remaining amount and usage

**Trigger Keywords:**

| English Keyword | Chinese Keyword |
|----------------|----------------|
| Flexus L | Flexus L |
| Huawei Cloud Ops | 华为云运维 |
| Query Instance | 查询实例 |
| Start/Stop/Reboot | 开机/关机/重启 |
| Reset Password | 重置密码 |
| Update Info | 修改信息 |
| Query Traffic | 查流量 |
| Traffic Package | 流量包 |
| List All Servers | 查所有服务器 |
| My Servers | 我的服务器有哪些 |
| List All Instances | 列出所有实例 |

## Prerequisites

### 1. Python Environment and dependencies

- Python >= 3.8
- huaweicloudsdkcore >= 3.0.0
- huaweicloudsdkecs >= 3.0.0
- huaweicloudsdkbss >= 3.0.0
- huaweicloudsdkconfig >= 3.0.0
- requests >= 2.31.0

### 2. Install Huawei Cloud SDK

```bash
pip3 install huaweicloudsdkcore huaweicloudsdkecs huaweicloudsdkconfig huaweicloudsdkbss \
  -i https://repo.huaweicloud.com/repository/pypi/simple
```

## ⚠️ Important: Script Usage Rules

**Different operations MUST use the corresponding script. Do NOT use other scripts' commands.**

| Operation | Must Use Script | Correct Command | ❌ Wrong Command |
|-----------|-----------------|-----------------|------------------|
| Query Flexus L instances | `query_instances.py` | `query_instances.py list` | ~~`password_unified.py list`~~ |
| Query instance details | `query_instances.py` | `query_instances.py detail -i <ID>` | ~~`lifecycle.py list`~~ |
| Start/Stop/Reboot | `lifecycle.py` | `lifecycle.py stop --instance-id <ID>` | ~~`query_instances.py stop`~~ |
| Reset password | `password_unified.py` | `password_unified.py reset --instance-id <ID> --password <pwd>` | ~~`lifecycle.py reset`~~ |
| Modify server info | `update_server.py` | `update_server.py --instance-id <ID> --name <name>` | ~~`query_instances.py update`~~ |

### Operation Feedback Requirement

**After any lifecycle operation (start/stop/reboot), MUST query and report the final status to user.**

Example feedback format:
```
✅ Operation completed
Instance: your-instance-name
Status: Running
Public IP: <IP>
```

This ensures the user knows the operation has completed successfully.

## Scripts Description

### Functional Scripts (4 scripts)

| Script | Function | Commands |
|--------|----------|----------|
| **query_instances.py** | Instance query tool ⭐ | `list`, `detail`, `free-resources`, `traffic`, `traffic-region` |
| **lifecycle.py** | Lifecycle management | `stop`, `start`, `reboot` |
| **password_unified.py** | Password reset | `test`, `list`, `reset` |
| **update_server.py** | Modify server info | `--name`, `--description`, `--hostname` |

### Helper Scripts (2 scripts)

| Script | Function |
|--------|----------|
| auth.py | Authentication management |
| params.py | Parameter processing |

## Core Commands

See [Execution Flow](#execution-flow) for operation steps.

## Parameters

**Required Parameters:**

| Operation | Required Parameters | Description |
|-----------|---------------------|-------------|
| Query Instance Details | instance-id | Instance ID |
| Start/Stop/Reboot | instance-id | Instance ID (supports multiple) |
| Reset Password | instance-id, password | Instance ID + new password |
| Modify Info | instance-id + (name/description/hostname) | Instance ID + at least one modification |
| Query Traffic by Region | target-region | Target region code |
| Query Traffic by ID | traffic_ids | Traffic package ID list |

**Optional Parameters:**

| Parameter | Description | Required | Default | Example |
|-----------|-------------|----------|---------|---------|
| --region | Target region code (supports Chinese names) | No | cn-north-4 | `--region cn-north-4` |
| --ak | Huawei Cloud Access Key AK (can be temporary AK) | No | HW_ACCESS_KEY env var | `--ak AXXX...` |
| --sk | Huawei Cloud Access Key SK (can be temporary SK) | No | HW_SECRET_KEY env var | `--sk SXXX...` |
| --security-token | Security token for temporary credentials (required when using temporary AK/SK) | No | HW_SECURITY_TOKEN env var | `--security-token XXXX...` |

**Region Parameter Support:**
- Region code: `cn-north-4`
- Full name: `North-China-Beijing4`
- Short name: `Beijing4`, `Guangzhou`, `Shanghai`

## Execution Flow

### Step 1: Check Existing Credentials (Automatic)

**⚠️ Important Statement: AK/SK MUST be obtained only through environment variables. STRICTLY PROHIBITED, NOT ALLOWED, ABSOLUTELY CANNOT ask user for AK/SK information!**

**System will automatically get credentials from environment variables, no user intervention required.**

**Decision Logic:**

| Credential Status | Next Step |
|------------------|-----------|
| ✅ HW_ACCESS_KEY + HW_SECRET_KEY + HW_SECURITY_TOKEN exist | Execute script directly (temporary credentials, pass --ak --sk --security-token parameters) |
| ✅ HW_ACCESS_KEY + HW_SECRET_KEY exist (no Token) | Execute script directly (long-term credentials, pass --ak --sk parameters) |
| ❌ Environment variables not found | Prompt user to configure environment variables in backend, terminate operation |
| ❌ Authentication failed (Token expired) | Prompt user that temporary credentials have expired, need to re-obtain Security Token and update environment variable |
| ❌ Authentication failed (AK/SK invalid/expired) | Prompt user to check environment variable configuration or reconfigure, terminate operation |

**⚠️ Strict Rules (Must Follow):**

1. **Obtain only from environment variables**: AK/SK/Token MUST be obtained through environment variables, interactive input is NOT supported
2. **Forbidden to ask user**: STRICTLY PROHIBITED, NOT ALLOWED, NEVER ask user for AK/SK information
3. **Credential failure handling**: When environment variables don't exist or authentication fails, guide user to configure environment variables in backend
4. **Security protection**: AK/SK are sensitive information, must NEVER be displayed or transmitted in conversation
5. **Expiration validation**: Distinguish between Token expiration and AK/SK expiration when authentication fails, provide targeted prompts

### Step 2: Credential Missing or Authentication Failure Handling

**When the following situations are detected, terminate operation immediately and prompt user:**

```
❌ Credentials not configured or authentication failed

Please go to the backend to configure environment variables:

Environment variables to configure:
- HW_ACCESS_KEY: Huawei Cloud Access Key AK
- HW_SECRET_KEY: Huawei Cloud Secret Access Key SK
- HW_SECURITY_TOKEN: (Optional) Temporary credential token

⚠️ Important: AK/SK are sensitive information, DO NOT disclose in conversation!
```

### Step 3: Select Operation

**After credentials are verified, ask user what operation to perform:**

### Step 4: Execute Operation

**⚠️ Instance Validation (When user provides instance ID/name):**

```bash
python3 {baseDir}/scripts/query_instances.py free-resources --ak "$HW_ACCESS_KEY" --sk "$HW_SECRET_KEY" [--security-token "$HW_SECURITY_TOKEN"]
```

- ✅ Found in list → Proceed with operation
- ❌ Not found → Tell user: "This is NOT a Flexus L instance. This skill only supports Flexus L instances." Then refer to [Finding Server ID](#finding-server-id) section for guidance.

**⚠️ Important Notes:**

**1. Instance Type Confirmation:**
Before executing any operation, remind user that this skill only supports Flexus L instances

**2. Server ID Guidance:**
If user hasn't specified a server ID to operate on, guide user to query all instances or specific server

#### 4.1 List Instances

**Query all instances across regions:**
```bash
python3 {baseDir}/scripts/query_instances.py list --ak "$HW_ACCESS_KEY" --sk "$HW_SECRET_KEY" [--security-token "$HW_SECURITY_TOKEN"]
```

**Query instances in specific region:**
```bash
python3 {baseDir}/scripts/query_instances.py list --region cn-north-4 --ak "$HW_ACCESS_KEY" --sk "$HW_SECRET_KEY" [--security-token "$HW_SECURITY_TOKEN"]
```

#### 4.2 Query Instance Details

**Required Parameters:**
- Instance ID (required)
- Region code (optional, default cn-north-4)

```bash
python3 {baseDir}/scripts/query_instances.py detail --instance-id <ID> --region cn-north-4 --ak "$HW_ACCESS_KEY" --sk "$HW_SECRET_KEY" [--security-token "$HW_SECURITY_TOKEN"]
```

**⚠️ Error Handling:** If query fails with "server not found" and user didn't specify region, tell user to check region, instance type, and ID.

#### 4.3 Batch Start

**Required Parameters:**
- Instance ID (required, supports multiple)
- Region code (optional, default cn-north-4)

```bash
python3 {baseDir}/scripts/lifecycle.py start --instance-id <ID1> --instance-id <ID2> --region cn-north-4 --ak "$HW_ACCESS_KEY" --sk "$HW_SECRET_KEY" [--security-token "$HW_SECURITY_TOKEN"]
```

#### 4.4 Batch Stop

**⚠️ Dangerous Operation: Must Confirm Twice**

**🔒 Instance Type Restriction: This operation ONLY supports Flexus L instances, NOT all ECS instances. Must verify instance type before execution.**

**Required Parameters:**
- Instance ID (required, supports multiple)
- Region code (optional, default cn-north-4)

**Must confirm twice before execution:**
- Tell user the consequences of stopping (service interruption, data loss risk)
- If stopping the server currently running OpenClaw, must warn additionally (conversation interruption, need manual restart)
- Only execute after user replies "confirm stop"

```bash
python3 {baseDir}/scripts/lifecycle.py stop --instance-id <ID1> --instance-id <ID2> --region cn-north-4 --ak "$HW_ACCESS_KEY" --sk "$HW_SECRET_KEY" [--security-token "$HW_SECURITY_TOKEN"]
```

#### 4.5 Batch Reboot

**⚠️ Dangerous Operation: Must Confirm Twice**

**🔒 Instance Type Restriction: This operation ONLY supports Flexus L instances, NOT all ECS instances. Must verify instance type before execution.**

**Required Parameters:**
- Instance ID (required, supports multiple)
- Region code (optional, default cn-north-4)
- Reboot type (optional): SOFT (normal reboot, default) or HARD (forced reboot)

**Must confirm twice before execution:**
- Tell user the consequences of rebooting (brief service interruption, memory data loss)
- If rebooting the server currently running OpenClaw, must warn additionally (brief conversation interruption, auto recovery)
- Only execute after user replies "confirm reboot"

```bash
python3 {baseDir}/scripts/lifecycle.py reboot --instance-id <ID1> --instance-id <ID2> --region cn-north-4 --ak "$HW_ACCESS_KEY" --sk "$HW_SECRET_KEY" [--security-token "$HW_SECURITY_TOKEN"]
```

#### 4.6 Reset Password

**Required Parameters:**
- Instance ID (required)
- New password (required)
  - Length 8-26 characters
  - Must contain at least 3 of: uppercase, lowercase, numbers, special characters
  - Cannot contain username or reversed username
  - Cannot contain 3 or more consecutive identical characters
- Region code (optional, default cn-north-4)

**⚠️ Important: After resetting password, the instance MUST be rebooted for the new password to take effect.**

**Must confirm with user before reboot:**
- Inform user that password reset is successful
- Warn user about consequences: brief service interruption, memory data loss
- If rebooting the server currently running OpenClaw, must warn additionally (brief conversation interruption, auto recovery)
- Only execute reboot after user replies "confirm reboot"

```bash
python3 {baseDir}/scripts/password_unified.py reset --instance-id <ID> --password <new_password> --region cn-north-4 --ak "$HW_ACCESS_KEY" --sk "$HW_SECRET_KEY" [--security-token "$HW_SECURITY_TOKEN"]
```
**Reboot Command:**
```bash
python3 {baseDir}/scripts/lifecycle.py reboot --instance-id <ID> --region cn-north-4 --ak "$HW_ACCESS_KEY" --sk "$HW_SECRET_KEY" [--security-token "$HW_SECURITY_TOKEN"]
```

#### 4.7 Modify Instance Information

**Required Parameters:**
- Instance ID (required)
- Region code (optional, default cn-north-4)
- Modification parameters (at least one):
  - name: Instance name (1-64 characters, supports Chinese, letters, numbers, _-, .)
  - description: Description (0-85 characters, cannot contain <>)
  - hostname: Hostname (1-64 characters)

```bash
python3 {baseDir}/scripts/update_server.py --instance-id <ID> --name "new_name" --region cn-north-4 --ak "$HW_ACCESS_KEY" --sk "$HW_SECRET_KEY" [--security-token "$HW_SECURITY_TOKEN"]
```

#### 4.8 Query Traffic Package

**Option 1: Query by Traffic Package ID**

**Required Parameters:**
- Traffic package ID (required)

**⚠️ Special Note: Traffic package query uses Beijing-1 region (cn-north-1) by default, traffic package ID can be from any region**

```bash
python3 {baseDir}/scripts/query_instances.py traffic <traffic_id_1> <traffic_id_2> --ak "$HW_ACCESS_KEY" --sk "$HW_SECRET_KEY" [--security-token "$HW_SECURITY_TOKEN"]
```

**Option 2: Query by Region ⭐ Recommended**

**Required Parameters:**
- Target region (required)

```bash
python3 {baseDir}/scripts/query_instances.py traffic-region --target-region cn-east-3 --ak "$HW_ACCESS_KEY" --sk "$HW_SECRET_KEY" [--security-token "$HW_SECURITY_TOKEN"]
```

### Finding Server ID

**If user asks "how to find server ID" or "don't know server ID", first provide console lookup steps:**

```
You can find server ID through the following ways:

Option 1: Via Huawei Cloud Console
1. Login to Huawei Cloud Console
2. Go to Flexus Application Server L instance list
3. Click instance name to enter details page
4. In basic information, click "Cloud Host VM"
5. View cloud host ID in cloud host information
6. Click copy button after ID to quickly copy

Help Document: https://support.huaweicloud.com/intl/zh-cn/flexusl_faq/faq_01_0003.html
```

**Then append the following, offer automatic query option:**

```
Option 2: I can also help query all servers under your account

Would you like me to list all instances under your account? I can query directly for you.
```

**If user agrees, execute list all instances:**

```bash
python3 {baseDir}/scripts/query_instances.py list --ak "$HW_ACCESS_KEY" --sk "$HW_SECRET_KEY" [--security-token "$HW_SECURITY_TOKEN"]
```

## Region Support

### Common Region Codes

| Region Code | Region Name |
|-------------|-------------|
| cn-north-4 | North China-Beijing 4 |
| cn-north-1 | North China-Beijing 1 |
| cn-south-1 | South China-Guangzhou |
| cn-east-3 | East China-Shanghai 1 |
| ap-southeast-1 | China-Hong Kong |
| ap-southeast-2 | Asia Pacific-Singapore |

### Region Name Conversion

This skill supports automatic region name conversion, can use Chinese names or English codes:

```bash
# Use region code
python3 {baseDir}/scripts/query_instances.py list --region cn-north-4 --ak "$HW_ACCESS_KEY" --sk "$HW_SECRET_KEY" [--security-token "$HW_SECURITY_TOKEN"]

# Use region name (auto-convert)
python3 {baseDir}/scripts/query_instances.py list --region "North-China-Beijing4" --ak "$HW_ACCESS_KEY" --sk "$HW_SECRET_KEY" [--security-token "$HW_SECURITY_TOKEN"]
python3 {baseDir}/scripts/query_instances.py list --region "Beijing4" --ak "$HW_ACCESS_KEY" --sk "$HW_SECRET_KEY" [--security-token "$HW_SECURITY_TOKEN"]
python3 {baseDir}/scripts/query_instances.py list --region "Guangzhou" --ak "$HW_ACCESS_KEY" --sk "$HW_SECRET_KEY" [--security-token "$HW_SECURITY_TOKEN"]
```

### Traffic Package Query Special Note

**⚠️ Traffic package query uses Beijing-1 region (cn-north-1) by default**

- Traffic package query does not support --region parameter
- Traffic package ID can be from any region
- Automatically uses Beijing-1 region for query

## Notes

- Instance ID is the cloud host ID corresponding to Flexus L instance
- Region defaults to cn-north-4 (Beijing 4)
- **AK/SK Security Requirements**:
  - ✅ Must be stored via environment variables (HW_ACCESS_KEY, HW_SECRET_KEY, HW_SECURITY_TOKEN)
  - ❌ Do not store in any configuration files
- **Stop/Reboot Security Requirements**:
  - ✅ **Must confirm twice** - No direct execution without user confirmation
  - ✅ **Must be Flexus L instances only** - Cannot operate on all ECS instances, must verify instance type
  - ✅ Must inform operation consequences
  - ✅ If current server, must give additional warning
  - ❌ **Never execute batch operations on all ECS instances** - Only Flexus L instances are supported

## References

### Skill Reference Documents

This skill includes the following reference documents:

- [IAM Policies](references/iam-policies.md) - Detailed IAM permission configuration
- [Verification Method](references/verification-method.md) - Skill verification method

### Huawei Cloud Official Documentation

- [Flexus Application Server L Instance Documentation](https://support.huaweicloud.com/intl/zh-cn/flexusl_faq/faq_01_0003.html)
