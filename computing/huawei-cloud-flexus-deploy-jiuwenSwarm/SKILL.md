---
name: huawei-cloud-flexus-deploy-jiuwenSwarm
version: "3.3.0"
description: "One-click deployment of JiuwenSwarm multi-Agent collaboration platform on Huawei Cloud Flexus L instances. Usage scenarios: When users need to quickly deploy JiuwenSwarm/JiuwenClaw on Huawei Cloud Flexus L instances, when they need to automatically create cloud instances and deploy AI Agent platforms, when they need to configure model APIs and message channels (Xiaoyi/Feishu/DingTalk). Automatically create instances, deploy applications via COC, configure models and message channels. Trigger keywords: JiuwenSwarm deployment, JiuwenClaw deployment."
tags:
  - JiuwenSwarm
  - JiuwenClaw
  - deployment
  - Huawei Cloud
  - Flexus L Instance
  - AI Agent
  - model management
  - channel management
metadata: {"jiuwenswarm": {"version": "3.3.0", "requires": {"bins": ["python3"]}, "install": [{"kind": "pip", "command": "pip install -r requirements.txt"}]}}
---

## **Important Notes**:
1. All Python files in the `scripts` directory have implemented all functions. **Do not create additional py files**.
2. **Do not modify** the script files in the `scripts` directory.
3. Please operate directly according to the provided code and documentation. No need to check Huawei Cloud official API documentation.
---
# JiuwenSwarm Deployment Skill for Huawei Cloud Flexus L Instance

## Overview

This skill provides a complete automated deployment solution for the JiuwenSwarm (JiuwenClaw) multi-Agent collaboration platform on Huawei Cloud Flexus L instances. It implements full-process automation from environment preparation to message channel configuration through phased scripts.

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

## Trigger Scenarios

| Scenario | Trigger Condition |
|----------|------------------|
| JiuwenSwarm Deployment | User requests to deploy JiuwenSwarm, deploy JiuwenClaw, or deploy AI applications on Flexus L |

**Note**: Only trigger when the user explicitly mentions deploying JiuwenSwarm/JiuwenClaw.

### Typical Use Cases

User may say:

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
1. Read deployment script template (assets/deploy-script-template.sh)
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
   - Direct query: python phase8_query_coc_status.py --uuid <execute_uuid>
   - Detailed output: python phase8_query_coc_status.py --uuid <execute_uuid> --verbose
   - Wait for completion: python phase8_query_coc_status.py --uuid <execute_uuid> --wait
3. Load UUID from JSON file:
   - python phase8_query_coc_status.py --from-file new_instance_info.json
4. Return task status, duration, output results, etc.
```

### COC Task Status Query
```
COC task status query supports the following features:
1. Single query - Query current status of specified UUID task
2. Detailed output - Display script execution output
3. Wait for completion - Continuous polling until task completes or timeout
4. File loading - Read UUID from JSON file saved during deployment

Script location: scripts/phase8_query_coc_status.py

Usage examples:
  # Query single task status
  python phase8_query_coc_status.py --uuid SCT2026052523172601755c2ea

  # Query with detailed output
  python phase8_query_coc_status.py --uuid SCT2026052523172601755c2ea --verbose

  # Wait for task completion
  python phase8_query_coc_status.py --uuid SCT2026052523172601755c2ea --wait

  # Custom wait time and polling interval
  python phase8_query_coc_status.py --uuid SCT2026052523172601755c2ea --wait --timeout 3600 --interval 30

  # Load UUID from JSON file
  python phase8_query_coc_status.py --from-file new_instance_info.json

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
huawei-cloud-flexus-deploy-jiuwenSwarm/
├── SKILL.md                    # Skill documentation
├── requirements.txt            # Python dependency list
├── scripts/                    # Phased deployment scripts
│   ├── utils.py                # Utility functions
│   ├── phase1_prepare_env.py   # Environment preparation
│   ├── phase2_create_instance.py # Create Flexus L instance
│   ├── phase3_install_deps.py  # COC remote dependency installation
│   ├── phase4_deploy_service.py # COC remote service deployment
│   ├── phase5_verify_deployment.py # Verify deployment result
│   ├── phase6_config_model.py  # Model configuration
│   ├── phase7_config_channel.py # Message channel configuration
│   └── phase8_query_coc_status.py # COC task status query
├── assets/                     # Template files
│   ├── deploy-script-template.sh # Deployment script template
│   ├── jiuwenswarm.service.template # systemd service template
│   ├── config-template.yaml    # Configuration template
│   └── env.template            # Environment variable template
└── references/                 # Reference documents
    ├── api-specs.md            # API specifications
    ├── cli-installation-guide.md # CLI installation guide
    ├── deployment-checklist.md # Deployment checklist
    ├── iam-policies.md         # IAM policies
    └── troubleshooting.md      # Troubleshooting guide
```

---

## Installation and Usage

### Environment Preparation
```bash
# Install dependencies
pip install -r requirements.txt

# Configure Huawei Cloud credentials
export HUAWEICLOUD_SDK_AK="your_access_key"
export HUAWEICLOUD_SDK_SK="your_secret_key"
export HUAWEICLOUD_REGION="cn-north-4"
```

### Quick Deployment Flow
```bash
# 1. Environment preparation
python scripts/phase1_prepare_env.py

# 2. Create instance (interactive confirmation)
python scripts/phase2_create_instance.py --name jiuwenSwarm-demo --flavor medium --wait

# 3. Install dependencies
python scripts/phase3_install_deps.py --ip <public_ip>

# 4. Deploy service
python scripts/phase4_deploy_service.py --ip <public_ip>

# 5. Verify deployment
python scripts/phase5_verify_deployment.py --ip <public_ip>

# 6. Configure model
python scripts/phase6_config_model.py --ip <public_ip> --interactive

# 7. Configure message channel
python scripts/phase7_config_channel.py --channel xiaoyi --ip <public_ip> --interactive

# 8. Query COC task status
python scripts/phase8_query_coc_status.py --uuid <execute_uuid> --verbose
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

### phase2_create_instance.py
| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| --name | Instance name | jiuwenSwarm-{timestamp} |
| --flavor | Instance flavor | medium |
| --region | Region (China domestic only: cn-north-4/cn-east-3/cn-south-1/cn-southwest-2) | cn-north-4 |
| --wait | Wait for creation completion | False |
| --timeout | Timeout in seconds | 600 |
| --confirm | Skip confirmation prompt | False |

### phase4_deploy_service.py
| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| --ip | Instance public IP | Required |
| --wait | Wait for deployment completion | True |
| --timeout | Timeout in seconds | 1800 |

### phase6_config_model.py
| Parameter | Description |
|-----------|-------------|
| --api-base | Model API URL |
| --api-key | Model API key |
| --model-name | Model name |
| --model-provider | Model provider |
| --ip | Instance public IP |
| --interactive | Interactive configuration |

### phase7_config_channel.py
| Parameter | Description |
|-----------|-------------|
| --channel | Channel type (xiaoyi/feishu/dingtalk) |
| --ip | Instance public IP |
| --interactive | Interactive configuration |

### phase8_query_coc_status.py
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

```bash
# Environment variable method (recommended)
export HUAWEICLOUD_SDK_AK="your_access_key"
export HUAWEICLOUD_SDK_SK="your_secret_key"
export HUAWEICLOUD_REGION="cn-north-4"
```

---

## Key API Endpoints

| Service | Endpoint | Purpose |
|---------|----------|---------|
| Flexus L | https://hcss.{region}.myhuaweicloud.com/v1/light-instances | Create/query instances |
| IAM | https://iam.{region}.myhuaweicloud.com/v3/projects | Get Project ID |
| RMS | https://rms.{region}.myhuaweicloud.com/v1/resource-manager/domains/{domain_id}/resources | Query resources |
| COC | https://coc.{region}.myhuaweicloud.com | Remote script execution |

**Supported China Domestic Regions**: cn-north-4 (North China-Beijing 4), cn-east-3 (East China-Shanghai 1), cn-south-1 (South China-Guangzhou), cn-southwest-2 (Southwest China-Guiyang 1)

**System Image**: Ubuntu 24.04 LTS only

---

## Troubleshooting

### Instance Creation Failed
- Check if AK/SK are correct
- Confirm sufficient account quota
- Verify region availability

### COC Deployment Unresponsive
- Check if execute_uuid is correct
- Confirm instance status is RUNNING
- Verify COC service permissions

### Web Service Unaccessible
- Check security group rules (port 5173 open)
- Confirm service is started: `systemctl status jiuwenswarm`
- View logs: `journalctl -u jiuwenswarm -f`