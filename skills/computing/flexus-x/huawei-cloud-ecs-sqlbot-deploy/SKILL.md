---
name: huawei-cloud-ecs-sqlbot-deploy
description: |
  Purchase Huawei Cloud X Instance server + one-click deploy SQLBot intelligent query application.
  Tech stack: Python 3.8+, Huawei Cloud SDK, COC (Cloud Operations Center) deployment.
  Key capabilities: AK/SK auth, X instance creation, auto security group config, SQLBot auto deployment.
  Use cases: Users who need to quickly deploy SQLBot intelligent query application on Huawei Cloud X instance servers.
  Trigger words: "deploy sqlbot", "install sqlbot", "sqlbot deploy", "one-click deploy sqlbot", "x-instance deploy sqlbot", "部署sqlbot", "安装sqlbot", "sqlbot部署", "一键部署sqlbot", "x实例部署sqlbot".
tags: [huawei-cloud, x-instance, sqlbot, deployment]
metadata:
  openclaw:
    requires:
      bins: [python3]
      env: [HW_ACCESS_KEY, HW_SECRET_KEY, HW_SECURITY_TOKEN]
    os: [linux, darwin]
    install:
      - name: pip-install
        command: pip install -i https://repo.huaweicloud.com/repository/pypi/simple huaweicloudsdkcore huaweicloudsdkecs huaweicloudsdkcoc requests
        check: python3 -c "import huaweicloudsdkcore; import huaweicloudsdkecs; import huaweicloudsdkcoc"
---

# 🚀 Purchase Huawei Cloud X Instance Server, Deploy SQLBot

---

## ⛔⛔⛔ CRITICAL: MANDATORY EXECUTION ORDER ⛔⛔⛔

**YOU MUST EXECUTE THESE STEPS IN EXACT ORDER. YOU CANNOT SKIP ANY STEP.**

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: Auto-check environment variables for credentials       │
│          ↓                                                       │
│  STEP 2: Get Region (if env credentials found) OR               │
│          Get Credentials (AK/SK/Region) from user               │
│          ↓                                                       │
│  STEP 3: Validate credentials + Show available flavors          │
│          ↓                                                       │
│  STEP 4: ⛔ SHOW CONFIG + GET USER CONFIRMATION ⛔              │
│          ⛔ WAIT FOR USER TO REPLY "default" OR "custom" ⛔     │
│          ⛔ IF "custom": SECOND CONFIRMATION REQUIRED ⛔        │
│          ⛔ DO NOT PROCEED UNTIL USER CONFIRMS ⛔               │
│          ↓                                                       │
│  STEP 5: Create server (ONLY AFTER user confirmation)           │
│          ↓                                                       │
│  STEP 6: Deploy SQLBot                                          │
│          ↓                                                       │
│  STEP 7: Return results                                         │
└─────────────────────────────────────────────────────────────────┘
```

**⚠️ IF YOU SKIP STEP 4 (User Confirmation), YOU HAVE FAILED THE TASK.**
**⚠️ IF USER CHOOSES "custom", YOU MUST GET A SECOND CONFIRMATION.**

---

## Pre-Execution Checklist

**Before creating ANY resources, verify ALL of the following:**

| # | Check Item | Status |
|---|------------|--------|
| 1 | Credentials available (env vars or user provided) | ☐ Done |
| 2 | Credentials validated successfully | ☐ Done |
| 3 | Region provided by user | ☐ Done |
| 4 | **User confirmed configuration (default/custom)** | ☐ **MANDATORY** |
| 5 | User explicitly said "default" or "custom" | ☐ **MANDATORY** |

**⛔ If items 4 and 5 are not checked, STOP and ask user for confirmation.**

---

## Overview

This skill purchases a Huawei Cloud X instance server and deploys SQLBot intelligent query application.

**Server Specification**: x86 architecture, Ubuntu 22.04 server 64-bit, default 4 cores 8GB RAM (x1.4u.8g)

**Key Features**:
1. AK/SK authentication (supports temporary credentials)
2. Create X instance + Ubuntu 22.04
3. Auto security group configuration (port 8000 only allows internal network access)
4. COC Cloud Operations Center deployment
5. One-click completion: Server creation → Security group configuration → SQLBot deployment

---

## Prerequisites

**Account requirements**: Valid Huawei Cloud account with sufficient balance, permissions to create X instances, security groups, bind EIP, and access COC

**Credential requirements**:

| Credential Type | Required Parameters | Security | Description |
|-----------------|---------------------|----------|-------------|
| Temporary (Recommended) | AK + SK + Security Token | High | Auto-expires, more secure |
| Permanent | AK + SK | Medium | No expiration, keep secure |

---

## Step-by-Step Execution Guide

### ━━━ STEP 1: Auto-check Credentials (Environment Variables) ━━━

**When user triggers the skill, first automatically get credentials from environment variables without asking user:**

```bash
# Check credentials (prefer temporary credentials)
export HW_ACCESS_KEY
export HW_SECRET_KEY  
export HW_SECURITY_TOKEN
```

**Decision Logic:**

| Credential Status | Next Step |
|-------------------|-----------|
| ✅ HW_ACCESS_KEY + HW_SECRET_KEY + HW_SECURITY_TOKEN exist | Proceed to Step 2 (ask for Region only, use temporary AK/SK authentication) |
| ✅ HW_ACCESS_KEY + HW_SECRET_KEY exist (no Token) | Proceed to Step 2 (ask for Region only, use permanent AK/SK authentication) |
| ❌ Environment variables not found | Prompt user to configure credentials (prefer environment variables), proceed to Step 2 |
| ❌ Authentication failed | Prompt user to check or reconfigure credentials, proceed to Step 2 |

**⚠️ Security Recommendations:**
1. **Prefer temporary credentials**: Higher security level, credentials auto-expire
2. **Environment variable configuration**: Credentials should be configured via environment variables (HW_ACCESS_KEY, HW_SECRET_KEY, HW_SECURITY_TOKEN)
3. **Sensitive information protection**: AK/SK are sensitive information, do NOT input or leak in conversations

---

### ━━━ STEP 2: Get Region or Credentials ━━━

**Case A: Environment credentials DETECTED**
```
OK! I will help you deploy SQLBot on Huawei Cloud X instance.

📋 Process Overview:
1. ✅ Environment credentials detected → User only needs to provide region
2. ⛔ Confirm configuration with you ⛔
3. Create server
4. Deploy SQLBot

⏱️ Estimated time: 10-15 minutes

Please provide:
- **Region**: Optional, default cn-north-4 (Beijing 4)
  ⚠️ If not provided, will use default region: cn-north-4
```

**Case B: Environment credentials NOT DETECTED**
```
❌ Environment credentials not detected

Please configure Huawei Cloud credentials (see "How to Get AK/SK" section).

📋 Process Overview:
1. ❌ Environment credentials not detected → User needs to provide credentials + region
2. ⛔ Confirm configuration with you ⛔
3. Create server
4. Deploy SQLBot

⏱️ Estimated time: 10-15 minutes

Please provide:
- **Access Key (AK)**: Required
- **Secret Key (SK)**: Required
- **Security Token**: Required for temporary credentials, not needed for permanent
- **Region**: Optional, default cn-north-4 (Beijing 4)
```

**Note:** We prioritize getting credentials from environment variables and NEVER ask users to input AK/SK directly. However, if users actively provide credentials through other means (e.g., conversation input, configuration file), we still support parsing.

**Include the regions table and AK/SK instructions (see below).**

**Then WAIT for user to provide information.**

---

### ━━━ STEP 3: Validate Credentials ━━━

After receiving region/credentials:
1. Validate credentials authentication
2. **Display configuration to user**

**Display the following note:**

```
💡 Note: Server flavor availability varies by region.
🔗 For details, see: https://www.huaweicloud.com/pricing/calculator.html#/hecs
```

**After successful validation, proceed to Step 4: User Confirmation.**

---

### ━━━ STEP 4: USER CONFIRMATION (⛔ MANDATORY) ━━━

**⛔ THIS STEP IS MANDATORY. YOU CANNOT SKIP IT. ⛔**

**Display the configuration and ask for confirmation** (see "Parameter Confirmation" section):

**⚠️ Note: Must display the server name so user knows what name will be used for the server.**

**⛔ STOP AND WAIT for user to reply "default" or "custom".**

**⛔ DO NOT proceed to Step 5 until user confirms.**

**⛔ DO NOT create any resources before user confirmation.**

**If user says "custom":** 
1. Ask which items they want to customize
2. Update configuration based on user input
3. **⛔ SECOND CONFIRMATION REQUIRED ⛔** - Display the updated configuration and ask user to confirm again (see "Parameter Confirmation" section)
4. Wait for user to reply "confirm" or "modify"
5. Only after second confirmation, proceed to Step 5

**If user says "default":** Proceed to Step 5.

---

### ━━━ STEP 5: Create Server ━━━

**Only execute this step AFTER user confirms configuration.**

Notify user: "⏳ Creating server..."

1. Create security group sg-sqlbot-YYYYMMDDHHMM
2. Create X instance with confirmed configuration
3. Bind EIP
4. Wait for server to be ready

Notify user: "✅ Server created!"

---

### ━━━ STEP 6: Deploy SQLBot ━━━

Notify user: "⏳ Deploying SQLBot via COC..."

1. Create installation script in Cloud Operations Center (COC)
2. Execute script on target instance via COC
3. Wait for deployment to complete and verify results

Notify user: "✅ SQLBot deployed via COC!"

---

### ━━━ STEP 7: Return Results ━━━

**MUST provide ALL of the following:**

```
🎉 SQLBot Deployment Complete!

📋 Server Information:
- Name: x-SQLBot-YYYYMMDDHHMM
- Public IP: X.X.X.X
- Private IP: 192.168.X.X

🔐 Access Information:
- Server Password: Test@123456 ⚠️ Change immediately!
- SQLBot URL: http://X.X.X.X:8000 (Note: Please allow your accessing machine IP to access port 8000 in the security group before accessing)
- SQLBot Username: admin
- SQLBot Password: SQLBot@123456

🔗 Huawei Cloud Console: https://console.huaweicloud.com/console/?region={region}#/ecs/manager/vmList

⚠️ Security Reminders:
1. Change server password immediately after login
2. Change SQLBot admin password after login
3. Release server when done to save costs
```

---

## Supported Regions (19 regions)

| Region Name | Region Code |
|-------------|-------------|
| North China - Beijing 4 | cn-north-4 |
| East China - Shanghai 1 | cn-east-3 |
| South China - Guangzhou | cn-south-1 |
| Southwest China - Guiyang 1 | cn-southwest-2 |
| East China 2 | cn-east-4 |
| East China - Qingdao | cn-east-5 |
| North China - Ulanqab 1 | cn-north-9 |
| China - Hong Kong | ap-southeast-1 |
| Asia Pacific - Bangkok | ap-southeast-2 |
| Asia Pacific - Singapore | ap-southeast-3 |
| Asia Pacific - Jakarta | ap-southeast-4 |
| Asia Pacific - Manila | ap-southeast-5 |
| Africa - Cairo | af-north-1 |
| Africa - Johannesburg | af-south-1 |
| Latin America - Mexico City 2 | la-north-2 |
| Latin America - Santiago | la-south-2 |
| Latin America - Sao Paulo 1 | sa-brazil-1 |
| Middle East - Riyadh | me-east-1 |
| Turkey - Istanbul | tr-west-1 |

---

## How to Get AK/SK

### Method 1: Temporary Credentials (Recommended 🔒)

**Pros**:
- ✅ Auto-expires, higher security
- ✅ Suitable for temporary deployment tasks
- ✅ Limited impact even if leaked

**Steps**:
1. Login to Huawei Cloud API Explorer: https://console.huaweicloud.com/apiexplorer/#/openapi/IAM/debug?api=CreateTemporaryAccessKeyByToken&version=v3
2. Click "Show Required Fields Only" → Fill in "Token" in the body
3. Click "Debug" to get credentials
4. Copy AK, SK and Security Token

**⚠️ Note**: Temporary credentials have expiration time (default 15 minutes to 1 hour), use promptly.

---

### Method 2: Permanent Credentials

**Pros**:
- ✅ Long-term valid, no frequent refresh needed
- ✅ Suitable for automation scripts and CI/CD

**Steps**:
1. Login to Huawei Cloud Console: https://console.huaweicloud.com/
2. Click avatar (top right) → My Credentials
3. Select Access Keys from left menu
4. Click Create Access Key
5. Download CSV file (contains AK and SK)

**⚠️ Note**: Permanent credentials never expire, keep secure! Do not upload CSV file to code repositories.

---

### Credential Type Comparison

| Type | Parameters | Security | Validity | Use Cases |
|------|------------|----------|----------|-----------|
| Temporary | AK + SK + Security Token | High | Auto-expires | Temporary deployment, one-time tasks |
| Permanent | AK + SK | Medium | Never expires | Automation scripts, CI/CD |

**Security Recommendation**: Prefer temporary credentials for deployment tasks.

---

## Default Configuration

| Item | Default Value |
|------|---------------|
| Server Name | x-SQLBot-YYYYMMDDHHMM |
| Flavor | x1.4u.8g (4U8G, x86_64) |
| Image | Ubuntu 22.04 Server 64-bit |
| System Disk | 80GB High IO |
| Billing Mode | On-demand |
| Security Group | sg-sqlbot-YYYYMMDDHHMM (newly created) |
| EIP Bandwidth | 300M |
| EIP Billing | Pay by traffic |
| Server Password | Test@123456 |
| SQLBot Username | admin |
| SQLBot Password | SQLBot@123456 |
| Open Ports | 8000 (internal network only) |

---

## Cost Reference

**Default config (4U8G, on-demand)**:
- Server: ~0.47 CNY/hour
- Traffic: ~0.8 CNY/GB

**Price Calculator**: https://www.huaweicloud.com/pricing/calculator.html#/hecs

---

## Core Commands

| Command/Option | Function | Description |
|----------------|----------|-------------|
| `(no option)` | **Deploy** | Purchase X instance and deploy SQLBot intelligent query application |
| `--list-regions` / `-l` | Show available regions | Display all supported regions and X instance types |
| `--test` | Test connection | Validate AK/SK credentials |

**Common Parameters:** `--ak`, `--sk`, `--region`, `--flavor`, `--charging-mode`

**Default Values**: See "Default Configuration" section

---

## Parameter Confirmation

> ⛔ **MANDATORY**: User confirmation is required before deployment. No resources can be created without confirmation.

### Confirmation Flow

1. **Display configuration**: List server name, region, flavor, image, system disk, billing mode, EIP, etc.
2. **Wait for user response**: User must explicitly reply `"default"` (use default config) or `"custom"` (customize config)
3. **Second confirmation (if needed)**: If user chooses `"custom"`, display updated config and request confirmation again

### Parameters to Confirm

**Customizable parameters**: Server Name, Region, Flavor, Image, System Disk, Billing Mode, EIP Bandwidth (default values see "Default Configuration" section)

### Confirmation Template

```
📋 Server Configuration:

| Item | Value |
|------|-------|
| Server Name | x-SQLBot-YYYYMMDDHHMM (auto-generated) |
| Region | {user-provided region} |
| Flavor | x1.4u.8g (4 cores 8GB) |
| Image | Ubuntu 22.04 Server 64-bit |
| System Disk | 80GB |
| Billing Mode | On-demand (pay-as-you-go) |
| EIP | 300M bandwidth, pay-by-traffic |

💰 Price Calculator: https://www.huaweicloud.com/pricing/calculator.html#/hecs

⛔ Please confirm: Use "default" configuration or "custom" configuration?
```

### Second Confirmation for Custom Configuration

If user chooses `"custom"`, display updated configuration and request second confirmation:

```
📋 Updated Server Configuration:

| Item | Value |
|------|-------|
| Server Name | {custom name} |
| Region | {custom region} |
| Flavor | {custom flavor} |
| Image | {custom image} |
| System Disk | {custom size}GB |
| Billing Mode | {custom mode} |
| EIP | {custom bandwidth}M bandwidth, pay-by-traffic |

⛔ Please confirm: Is the above configuration correct? Reply "confirm" to proceed or "modify" to change.
```

## Script Usage

### Option 1: Using command line parameters
```bash
python3 scripts/deploy_sqlbot.py \
  --ak YOUR_AK \
  --sk YOUR_SK \
  --security-token YOUR_SECURITY_TOKEN \
  --region cn-north-4 \
  --notify-user-id <feishu_user_id>
```

### Option 2: Using environment variables (Recommended for temporary credentials)
```bash
export HW_ACCESS_KEY="your-temp-ak"
export HW_SECRET_KEY="your-temp-sk"
export HW_SECURITY_TOKEN="your-security-token"

python3 scripts/deploy_sqlbot.py --region cn-north-4  --notify-user-id <feishu_user_id>
```

**Parameters**:
- `--ak`: Access Key (can also be set via HW_ACCESS_KEY environment variable)
- `--sk`: Secret Key (can also be set via HW_SECRET_KEY environment variable)
- `--security-token`: Security Token for temporary credentials (can also be set via HW_SECURITY_TOKEN environment variable)
- `--region`: Region code (default: cn-north-4, Beijing 4)
- `--flavor`: Server flavor (default: x1.4u.8g)
- `--volume-size`: System disk size (default: 80GB)
- `--bandwidth`: EIP bandwidth (default: 300M)
- `--charging-mode`: postPaid (on-demand) or prePaid (monthly)

---

## ⚠️ Common Mistakes to Avoid

| Mistake | Correct Behavior |
|---------|------------------|
| Creating server without user confirmation | **ALWAYS get confirmation first** |
| Assuming user wants default config | **ASK explicitly: "default" or "custom"?** |
| Skipping the confirmation step | **This step is MANDATORY, not optional** |
| Proceeding after showing config | **WAIT for user to reply before proceeding** |

---

## References

- [Acceptance Criteria](references/acceptance-criteria.md) - Deployment verification standards
- [CLI Installation Guide](references/cli-installation-guide.md) - Command line usage guide
- [IAM Policies](references/iam-policies.md) - Permission configuration
- [Verification Method](references/verification-method.md) - Skill verification
- [X Instance Documentation](https://support.huaweicloud.com/productdesc-flexusx/pd_01_0002.html) - X Instance product documentation
- [AK/SK Authentication](https://support.huaweicloud.com/api-iam/iam_01_0001.html) - IAM authentication guide
