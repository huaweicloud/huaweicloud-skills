---
name: huawei-cloud-flexus-l-deploy-jiuwenswarm
description: "One-click deployment of JiuwenSwarm multi-Agent collaboration platform on Huawei Cloud Flexus L instances. Usage scenarios: When users need to quickly deploy JiuwenSwarm/JiuwenClaw on Huawei Cloud Flexus L instances, when they need to automatically create cloud instances and deploy AI Agent platforms, when they need to configure model APIs and message channels (Xiaoyi/Feishu/DingTalk). Automatically create instances, deploy applications via COC, configure models and message channels. Trigger keywords: JiuwenSwarm deployment, JiuwenClaw deployment, 九问Swarm部署, 九问Claw部署, 一键部署JiuwenSwarm, AI智能体平台部署, 部署九问Swarm, 部署九问Claw,云服务器部署AI平台."
version: 1.0.0
tags:
  - JiuwenSwarm
  - JiuwenClaw
  - AI Agent
metadata: {"jiuwenswarm": {"requires": {"bins": ["python3"]}, "install": [{"kind": "pip", "command": "pip install -r requirements.txt"}]}}
---

## **Important Notes**:
1. All Python files in the `scripts` directory have implemented all functions. **Do not create additional py files**.
2. **Do not modify** the script files in the `scripts` directory.
3. Please operate directly according to the provided code and documentation. No need to check Huawei Cloud official API documentation.
---

## security Execution Rules (Highest Priority):
1. All scripts MUST be executed via skill action=exec, NEVER run directly in shell
2. NEVER print script contents or commands containing AK/SK/Token in conversation
3. NEVER create temporary script files, prefer inline execution (python -c)
4. On execution failure, only return error info, do NOT rewrite scripts or print full commansds
5. AK/SK/Token MUST be passed via environment variables, NEVER appear in conversation
6. NEVER interactively collect Huawei Cloud credentials from users. Credentials MUST be obtained only through:
   - Temporary Security Credentials (STS Token) via environment variables
   - Permanent credentials via environment variables
---

# JiuwenSwarm Deployment Skill for Huawei Cloud Flexus L Instance

## Overview

This skill provides a complete automated deployment solution for the JiuwenSwarm (JiuwenClaw) multi-Agent collaboration platform on Huawei Cloud Flexus L instances. It implements full-process automation from environment preparation to message channel configuration through phased scripts.

---

## Prerequisites

Before using this skill, the following prerequisites must be met:

### 1. Huawei Cloud Account Requirements
- A valid Huawei Cloud account with active subscription
- Sufficient balance or billing method configured
- Flexus L instance quota available in the target region (cn-north-4)

### 2. IAM Credentials
- Huawei Cloud Access Key (AK) and Secret Key (SK) with appropriate permissions
- **Temporary Security Credentials (STS Token)**: Supports temporary security credentials. When `HUAWEICLOUD_SDK_SECURITY_TOKEN` environment variable is set along with AK/SK, the skill will use temporary credentials for authentication. 
- Required IAM permissions:
  - `hcss:lightInstance:create` - Create Flexus L instances
  - `hcss:lightInstance:list` - Query instance information
  - `rms:resource:list` - Query resource information
  - `coc:execution:create` - Execute COC scripts
  - `coc:execution:list` - Query COC task status
  - `iam:project:list` - Get project information

### 3. Environment Requirements
- Python 3.8+ installed with pip
- Required Python packages:
  - `requests` - HTTP client
  - `huaweicloudsdkcore` - Huawei Cloud SDK core
  - `huaweicloudsdkcoc` - COC service SDK
  - `huaweicloudsdkrms` - RMS service SDK
  - `huaweicloudsdkiam` - IAM service SDK

### 4. Network Requirements
- Internet access to Huawei Cloud APIs
- Security group rules allowing outbound HTTP/HTTPS traffic (ports 80, 443)
- For web access: Port 5173 needs to be opened in security group after deployment

### 5. Resource Requirements
- Flexus L instance with minimum specifications:
  - Flavor: medium (2 vCPUs, 4GB RAM) or higher
  - System disk: 40GB or larger
  - Network: Public IP required

### 6. Configuration Requirements
- Model API credentials (API_BASE, API_KEY) for LLM integration (required for Phase 6)
- Message channel credentials (Xiaoyi/Feishu/DingTalk) if channel configuration is needed (required for Phase 7)

---

### Architecture Diagram

This skill is built on multiple Huawei Cloud services, involving the following cloud services and components:

```
User/Agent      ──────▶│   Flexus L Instance   │──────▶│   JiuwenSwarm App    │──────▶│ Model Config     │ ──────▶│  Channel Config     │ 
(Skill caller)           (Target Host)                 (Multi-Agent Platform)           (API_BASE/KEY)            (Xiaoyi/Feishu/Dingtalk)            
```

**Component Description**:
- **User/Agent**: Skill caller that triggers JiuwenSwarm deployment operations via natural language or API
- **Flexus L Instance**: Huawei Cloud Elastic Cloud Server, serving as the target host for JiuwenSwarm deployment
- **JiuwenSwarm App**: Multi-agent collaboration platform running on the Flexus L instance
- **Model Config**: Configuration for external LLM services (API_BASE, API_KEY, MODEL_NAME, MODEL_PROVIDER)
- **Channel Config**: Messaging channel configuration (Huawei Xiaoyi, Feishu, Dingtalk)
---

## Skill Responsibilities

### Core Functions
1. **Flexus L Instance Creation** - Call Flexus L API to create instances, supporting parameters like instance name, flavor (medium/large), image version, etc.
2. **Instance Status Query** - Query instance status, public IP, instance ID via RMS API
3. **COC Remote Deployment** - Use Huawei Cloud COC (Cloud Operations Center) to remotely execute deployment scripts on instances
4. **COC Task Status Query** - Query deployment task execution status and results via COC API
5. **System Service Configuration** - Configure systemd service for auto-start on boot
6. **Model Configuration** - Configure API_BASE, API_KEY, MODEL_NAME, MODEL_PROVIDER
7. **Message Channel Configuration** - Support three message channels: Xiaoyi, Feishu, DingTalk

### Execution Flow
```
Phase 1: Environment Preparation → Phase 2: Create Instance → Phase 3: Install Dependencies → COC Status Query → Phase 4: Deploy Service → COC Status Query → Phase 5: Verify Deployment → Phase 6: Model Configuration → Phase 7: Message Channel Configuration
```

---

### Typical Use Cases

User may say:

**English Examples:**
1. **"Help me deploy JiuwenSwarm to Huawei Cloud"**
2. **"I want to install JiuwenClaw on Flexus L instance"**
3. **"How to add Feishu bot to my JiuwenSwarm?"**
4. **"I want to configure JiuwenSwarm to use custom model"**
5. **"Help me deploy JiuwenSwarm with one click and configure Xiaoyi channel"**

---

## ⚠️ Important: Customer Confirmation Required

**Before executing any cloud resource creation operations, explicit customer consent must be obtained!**

### Scenarios Requiring Confirmation
| Operation | Confirmation Required |
|-----------|----------------------|
| Create new Flexus L instance | **Required** |
| Deploy application on existing instance | **Required** |
| Modify cloud resource configuration | **Required** |

### Confirmation Template
```
============================================================
⚠️ Cloud Resource Creation Confirmation
============================================================
Operation to be executed: Create new Flexus L instance

Instance Specifications:
  - Name: {instance_name}
  - Flavor: {flavor}
  - Region: {region}
  - Estimated Cost: ~100 RMB/month (actual price subject to Huawei Cloud pricing)

Resources will be created immediately after confirmation.
Please reply "confirm" or "agree" to continue.
============================================================
```
---

## Execution Steps

### Phase 1: Environment Preparation
```
1. Verify Huawei Cloud credentials (AK/SK)
2. Set environment variable: PYTHONIOENCODING=utf-8
3. Check dependency modules: requests, huaweicloudsdkcore, huaweicloudsdkcoc, huaweicloudsdkrms
4. Validate credential validity (via IAM API)
```

### Phase 2: Create Flexus L Instance
```
⚠️ The following steps can only be executed after obtaining customer confirmation!

1. Display instance configuration information to customer (name, flavor, region, estimated cost)
2. Wait for customer confirmation (reply "confirm" or "agree")
3. After confirmation, execute:
   - Get Project ID (via IAM API)
   - Call Flexus L create API
   - Save order_id for subsequent queries
   - Wait for instance creation to complete (poll RMS API)
   - Get instance information: instance_id, public_ip, ecs_instance_id
```

### Phase 3: COC Remote Dependency Installation
```
Based on instance information from Phase 2: instance_id, public_ip, ecs_instance_id, execute:
1. Execute dependency installation script via COC
2. Install base tools: git, curl, vim, wget, net-tools, etc.
3. Check Python and Node.js environment
4. Wait for deployment to complete. Note: script execution takes approximately 8 minutes. Please be patient. Only retry if script execution errors occur.
```

### Phase 4: COC Remote JiuwenSwarm Service Deployment
```
1. Read deployment script template (assets/deploy_script_template.sh)
2. Execute complete deployment script on instance via COC
3. Install JiuwenSwarm and related dependencies
4. Configure systemd service
5. Start JiuwenSwarm service
6. Wait for deployment to complete. Note: script execution takes approximately 15 minutes. Please be patient. Only retry if script execution errors occur.
```

### Phase 5: Verify Deployment Result
```
1. Query COC deployment task status
2. Verify port 5173 listening
3. Check service health status
4. Output web access URL
```

### Phase 6: Model Configuration
```
1. Interactively collect model configuration information:
   - API_BASE: Model API URL
   - API_KEY: Model API key
   - MODEL_NAME: Model name
   - MODEL_PROVIDER: Model provider
2. Generate configuration script (COC remote execution):
   - Backup original .env file
   - Update only four core parameters (API_BASE, API_KEY, MODEL_NAME, MODEL_PROVIDER)
   - Keep other configuration parameters unchanged
   - Set file permission to 600
3. Restart JiuwenSwarm service
```

### Phase 7: Message Channel Configuration
```
1. Select channel type: xiaoyi / feishu / dingtalk
2. Collect configuration information based on channel type:
   - xiaoyi: AK, SK, Agent ID
   - feishu: App ID, App Secret
   - dingtalk: Client ID, Client Secret, Allow From
3. Generate configuration script (COC remote execution):
   - Backup original config.yaml file
   - Update only key configuration fields for specified channel, keep other configurations unchanged
   - Xiaoyi: Update only ak, sk, agent_id, enabled
   - Feishu: Update only app_id, app_secret, enabled
   - DingTalk: Update only client_id, client_secret, allow_from, enabled
   - Set file permission to 644
4. Restart JiuwenSwarm service
```

### COC Remote Script Execution Status Query
```
1. Query task status by COC execution UUID
2. Support three query methods:
   - Direct query: python query_coc_status.py --uuid <execute_uuid>
   - Detailed output: python query_coc_status.py --uuid <execute_uuid> --verbose
   - Wait for completion: pythonquery_coc_status.py --uuid <execute_uuid> --wait
3. Load UUID from JSON file:
   - python query_coc_status.py --from-file new_instance_info.json
4. Return task status, duration, output results, etc.
```

### COC Task Status Query
```
COC task status query supports the following features:
1. Single query - Query current status of specified UUID task
2. Detailed output - Display script execution output
3. Wait for completion - Continuous polling until task completes or timeout
4. File loading - Read UUID from JSON file saved during deployment

Script location: scripts/query_coc_status.py

Usage examples:
  # Query single task status
  python query_coc_status.py --uuid SCT20250101000000000000000

  # Query with detailed output
  python query_coc_status.py --uuid SCT20250101000000000000000 --verbose

  # Wait for task completion
  python query_coc_status.py --uuid SCT20250101000000000000000 --wait

  # Custom wait time and polling interval
  python query_coc_status.py --uuid SCT20250101000000000000000 --wait --timeout 3600 --interval 30

  # Load UUID from JSON file
  python query_coc_status.py --from-file new_instance_info.json

COC Task Status Description:
| Status | Description |
|--------|-------------|
| READY | Ready |
| PROCESSING | Running, waiting required |
| FINISHED | Completed successfully |
| ABNORMAL | Execution abnormal, failed |
| CANCELED | Canceled |
```

---

## Output Standards

### Success Output Template
```
============================================================
  JiuwenSwarm COC Deployment - Complete
============================================================

Target Instance:
  Name: {instance_name}
  ID: {instance_id}
  IP: {public_ip}

COC Execution:
  Execute UUID: {execute_uuid}
  Status: FINISHED

Deployment Result:
  Web Access: http://{public_ip}:5173
  Submit Time: {submit_time}

============================================================
[SUCCESS] Deployment task completed!
============================================================
```

### Error Output Template
```
============================================================
[ERROR] Deployment Failed
============================================================

Error: {error_message}

Suggestions:
  1. Check Huawei Cloud credentials
  2. Verify instance status
  3. Check deployment logs

============================================================
```

### COC Task Status Description
| Status | Description |
|--------|-------------|
| PROCESSING | Running, waiting required |
| FINISHED | Completed successfully |
| ABNORMAL | Execution abnormal, failed |
| CANCELED | Canceled |

---

## Directory Structure

```
huawei-cloud-flexus-l-deploy-jiuwenSwarm/
├── SKILL.md                    # Skill documentation
├── requirements.txt            # Python dependency list
├── scripts/                    # Phased deployment scripts
│   ├── utils.py                # Utility functions
│   ├── prepare_env.py   # Environment preparation
│   ├── create_instance.py # Create Flexus L instance
│   ├── install_deps.py  # COC remote dependency installation
│   ├── deploy_service.py # COC remote service deployment
│   ├── verify_deployment.py # Verify deployment result
│   ├── config_model.py  # Model configuration
│   ├── config_channel.py # Message channel configuration
│   └── query_coc_status.py # COC task status query
├── assets/                     # Template files
│   ├── deploy_script_template.sh # Deployment script template
│   ├── jiuwenswarm.service.template # systemd service template
│   ├── config_template.yaml    # Configuration template
│   └── env.template            # Environment variable template
└── references/                 # Reference documents
    ├── api_specs.md            # API specifications
    ├── deployment_checklist.md # Deployment checklist
    ├── iam_policies.md         # IAM policies
    └── troubleshooting.md      # Troubleshooting guide
```

---

## Installation and Usage

### Environment Preparation
```bash
# Install dependencies
pip install -r requirements.txt

# Configure Huawei Cloud credentials (Recommended: temporary security credentials - STS Token)
# export HUAWEICLOUD_SDK_AK=<your-temp-access-key>
# export HUAWEICLOUD_SDK_SK=<your-temp-secret-key>
# export HUAWEICLOUD_SDK_SECURITY_TOKEN=<your-security-token>
# export HUAWEICLOUD_REGION="cn-north-4"

# OR use permanent credentials (not recommended)
# export HUAWEICLOUD_SDK_AK=<your-access-key>
# export HUAWEICLOUD_SDK_SK=<your-secret-key>
# export HUAWEICLOUD_REGION="cn-north-4"
```

### Quick Deployment Flow
```bash
# 1. Environment preparation
python scripts/prepare_env.py

# 2. Create instance (interactive confirmation)
python scripts/create_instance.py --name jiuwenSwarm-<timestamp> --flavor medium --wait

# 3. Install dependencies
python scripts/install_deps.py --ip <public_ip>

# 4. Deploy service
python scripts/deploy_service.py --ip <public_ip>

# 5. Verify deployment
python scripts/verify_deployment.py --ip <public_ip>

# 6. Configure model
python scripts/config_model.py --ip <public_ip> --interactive

# 7. Configure message channel
python scripts/config_channel.py --channel xiaoyi --ip <public_ip> --interactive

# 8. Query COC task status
python scripts/query_coc_status.py --uuid <execute_uuid> --verbose
```

---

### Web UI Access
Web UI access requires manual security group configuration in Huawei Cloud Console:
1. Login to Huawei Cloud Flexus Application Server L Instance Console
   - 🔗 Console URL: https://console.huaweicloud.com/smb/?/resource/list
2. Find your JiuwenSwarm instance in the instance list
3. Click instance name to enter details page
4. Find "Security" or "Network" options in left menu
5. Configure security group rules to open port 5173
**Access URL**: `http://<instance_public_ip>:5173`
**Security Warning**: After opening the port, JiuwenSwarm Web interface will be accessible. Please evaluate security risks before enabling. It is recommended to open temporarily only when needed and close after use.
---

## Script Parameter Description

### create_instance.py
| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| --name | Instance name | jiuwenSwarm-{timestamp} |
| --flavor | Instance flavor | medium |
| --region | Region (cn-north-4 only) | cn-north-4 |
| --wait | Wait for creation completion | False |
| --timeout | Timeout in seconds | 600 |
| --confirm | Skip confirmation prompt | False |

### deploy_service.py
| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| --ip | Instance public IP | Required |
| --wait | Wait for deployment completion | True |
| --timeout | Timeout in seconds | 1800 |

### config_model.py
| Parameter | Description |
|-----------|-------------|
| --api-base | Model API URL |
| --api-key | Model API key |
| --model-name | Model name |
| --model-provider | Model provider |
| --ip | Instance public IP |
| --interactive | Interactive configuration |

### config_channel.py
| Parameter | Description |
|-----------|-------------|
| --channel | Channel type (xiaoyi/feishu/dingtalk) |
| --ip | Instance public IP |
| --interactive | Interactive configuration |

### query_coc_status.py
| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| --uuid, -u | COC execution UUID | Required |
| --from-file, -f | Read UUID from JSON file | - |
| --key, -k | UUID key name in JSON file | execute_uuid |
| --verbose, -v | Show detailed output | False |
| --wait, -w | Wait for task completion | False |
| --timeout, -t | Wait timeout in seconds | 1800 |
| --interval, -i | Polling interval in seconds | 60 |

---

## Huawei Cloud Credential Configuration

**Recommended: Use temporary security credentials (STS Token) by default. Please use this method first.**

### Temporary Security Credentials (STS Token) - Recommended (Default)
The skill supports temporary security credentials. Temporary credentials require an additional `HUAWEICLOUD_SDK_SECURITY_TOKEN` environment variable.

| Environment Variable | Description | Required |
|---------------------|-------------|----------|
| `HUAWEICLOUD_SDK_AK` | Temporary Access Key | Yes |
| `HUAWEICLOUD_SDK_SK` | Temporary Secret Key | Yes |
| `HUAWEICLOUD_SDK_SECURITY_TOKEN` | Security Token | Yes |
| `HUAWEICLOUD_REGION` | Huawei Cloud Region (default: cn-north-4) | Yes |

### Permanent Credentials
Credentials must be set via environment variables before running the skill.

| Environment Variable | Description | Required |
|---------------------|-------------|----------|
| `HUAWEICLOUD_SDK_AK` | Huawei Cloud Access Key | Yes |
| `HUAWEICLOUD_SDK_SK` | Huawei Cloud Secret Key | Yes |
| `HUAWEICLOUD_REGION` | Huawei Cloud Region (default: cn-north-4) | Yes |

**Credential Concept**:
- **Temporary credentials (Default)**: AK + SK + SECURITY_TOKEN + REGION (STS token is added to permanent credentials)
- **Permanent credentials**: AK + SK + REGION

**Reference**: https://support.huaweicloud.com/iam_faq/iam_01_0620.html

---

## Key API Endpoints

| Service | Endpoint | Purpose |
|---------|----------|---------|
| Flexus L | https://hcss.{region}.myhuaweicloud.com/v1/light-instances | Create/query instances |
| IAM | https://iam.{region}.myhuaweicloud.com/v3/projects | Get Project ID |
| RMS | https://rms.{region}.myhuaweicloud.com/v1/resource-manager/domains/{domain_id}/resources | Query resources |
| COC | https://coc.{region}.myhuaweicloud.com | Remote script execution |

**Supported Region**: cn-north-4 only (China North 4)

**System Image**: Ubuntu 24.04 LTS only

---

## Troubleshooting

### Instance Creation Failed
- Check if AK/SK are correct
- Confirm sufficient account quota
- Ensure using cn-north-4 region

### COC Deployment Unresponsive
- Check if execute_uuid is correct
- Confirm instance status is RUNNING
- Verify COC service permissions

### Web Service Unaccessible
- Check security group rules (port 5173 open)
- Confirm service is started: `systemctl status jiuwenswarm`
- View logs: `journalctl -u jiuwenswarm -f`
