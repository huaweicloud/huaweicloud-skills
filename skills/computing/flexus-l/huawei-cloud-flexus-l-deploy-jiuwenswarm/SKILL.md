---
name: huawei-cloud-flexus-l-deploy-jiuwenswarm
description: "One-click deployment of JiuwenSwarm multi-Agent collaboration platform on Huawei Cloud Flexus L instances. Usage scenarios: When users need to quickly deploy JiuwenSwarm/JiuwenClaw on Huawei Cloud Flexus L instances, when they need to automatically create cloud instances and deploy AI Agent platforms, when they need to configure model APIs and message channels (Xiaoyi/Feishu/DingTalk). Automatically create instances, deploy applications via COC, configure models and message channels. Trigger keywords: JiuwenSwarm deployment, JiuwenClaw deployment, 九问Swarm部署, 九问Claw部署, 一键部署JiuwenSwarm, AI智能体平台部署, 部署九问Swarm, 部署九问Claw,云服务器部署AI平台."
version: 1.0.0
tags:
  - JiuwenSwarm
  - JiuwenClaw
  - AI Agent
metadata: {"jiuwenswarm": {"requires": {"bins": ["python3", "hcloud"]}, "install": [{"kind": "pip", "command": "pip install -r requirements.txt"}]}}
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
5. AK/SK/Token MUST be passed via environment variables or hcloud config, NEVER appear in conversation
6. NEVER interactively collect Huawei Cloud credentials from users. Credentials MUST be obtained only through:
   - hcloud CLI config file (~/.hcloud/config.json) — primary source, auto-detected
   - Temporary Security Credentials (STS Token) via environment variables — fallback
   - Permanent credentials via environment variables — fallback
---

# JiuwenSwarm Deployment Skill for Huawei Cloud Flexus L Instance

## Overview

This skill provides a complete automated deployment solution for the JiuwenSwarm (JiuwenClaw) multi-Agent collaboration platform on Huawei Cloud Flexus L instances. It implements full-process automation from environment preparation to message channel configuration through phased scripts.

---

## Prerequisites

### 1. Huawei Cloud Account Requirements
- A valid Huawei Cloud account with active subscription
- Sufficient balance or billing method configured
- Flexus L instance quota available in target region (cn-north-4/cn-east-3/cn-south-1/cn-southwest-2)

### 2. IAM Credentials
- Huawei Cloud Access Key (AK) and Secret Key (SK) with appropriate permissions
- **Temporary Security Credentials (STS Token)**: Supports temporary security credentials. When `HUAWEICLOUD_SDK_SECURITY_TOKEN` environment variable is set along with AK/SK, the skill will use temporary credentials for authentication.
- Required IAM permissions: see [references/iam-policies.md](references/iam-policies.md)

### 3. Environment Requirements
- Python 3.8+ installed with pip
- It is recommended to use a Python virtual environment to avoid system package conflicts:
  ```bash
  python3 -m venv .venv && source .venv/bin/activate
  ```
  If you cannot use a virtual environment, you may need to add `--break-system-packages` when running pip on some newer Linux distributions.
- Required Python packages: `requests`, `huaweicloudsdkcore`, `huaweicloudsdkcoc`
- KooCLI (`hcloud`) must be installed and available in PATH (used for IAM/RMS queries, see [references/api-specs.md](references/api-specs.md))

### 4. Network Requirements
- Internet access to Huawei Cloud APIs
- Security group rules allowing outbound HTTP/HTTPS traffic (ports 80, 443)
- For web access: Port 5173 needs to be opened in security group after deployment

### 5. Resource Requirements
- Flexus L instance with minimum specifications:
  - Flavor: 2c-4g-50g (2 vCPUs, 4GB RAM, 50GB disk) or higher
  - Network: Public IP required
- Supported flavors:
  - 2c-4g-50g (2 vCPU 4GB 50GB) - ~60 CNY/month
  - 2c-4g-70g (2 vCPU 4GB 70GB) - ~100 CNY/month
  - 4c-8g-180g (4 vCPU 8GB 180GB) - ~170 CNY/month

### 6. Configuration Requirements
- Model API credentials (API_BASE, API_KEY) for LLM integration (required for Phase 6)
- Message channel credentials (Xiaoyi/Feishu/DingTalk) if channel configuration is needed (required for Phase 7)

---

### Architecture Diagram

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
1. **Flexus L Instance Creation** - Call Flexus L API to create instances, supporting parameters like instance name, flavor, region, etc.
2. **Instance Status Query** - Query instance status, public IP, instance ID via KooCLI (`hcloud RMS ListAllResources`)
3. **COC Remote Deployment** - Use Huawei Cloud COC (Cloud Operations Center) to remotely execute deployment scripts on instances
4. **COC Task Status Query** - Query deployment task execution status and results via COC API
5. **System Service Configuration** - Configure systemd service for auto-start on boot
6. **Model Configuration** - Configure API_BASE, API_KEY, MODEL_NAME, MODEL_PROVIDER
7. **Message Channel Configuration** - Support three message channels: Xiaoyi, Feishu, DingTalk

### Typical Use Cases

**English Examples:**
1. **"Help me deploy JiuwenSwarm to Huawei Cloud"**
2. **"I want to install JiuwenClaw on Flexus L instance"**
3. **"How to add Feishu bot to my JiuwenSwarm?"**
4. **"I want to configure JiuwenSwarm to use custom model"**
5. **"Help me deploy JiuwenSwarm with one click and configure Xiaoyi channel"**

---

## 工作流

This skill executes deployment in 7 phases. Each phase must complete before the next begins.

### Phase 1: Environment Preparation
1. Verify Huawei Cloud credentials (AK/SK)
2. Set environment variable: `PYTHONIOENCODING=utf-8`
3. Check dependency modules: requests, huaweicloudsdkcore, huaweicloudsdkcoc, and KooCLI (`hcloud`)
4. Validate credential validity (via KooCLI `hcloud IAM KeystoneListProjects`)

### Phase 2: Create Flexus L Instance
> ⚠️ **Requires customer confirmation before execution!**
1. If `--region` parameter not provided, interactively prompt user to select a region from supported options
2. Display instance configuration to customer (name, flavor, region, estimated cost)
3. Wait for customer confirmation (reply "confirm" or "agree")
4. After confirmation: Get Project ID (KooCLI) → Call Flexus L create API → Save order_id → Poll RMS via KooCLI for completion (polls every **30 seconds**, defaults to **600s/10 minutes** timeout, configurable via `--timeout`) → Get instance_id, public_ip, ecs_instance_id

### Phase 3: COC Remote Dependency Installation
1. Execute dependency installation script via COC
2. Install base tools: git, curl, vim, wget, net-tools, etc.
3. Check Python and Node.js environment
4. Wait for completion (~8 minutes). Only retry if script execution errors occur.

### Phase 4: COC Remote JiuwenSwarm Service Deployment
1. Read deployment script template (assets/deploy_script_template.sh)
2. Execute complete deployment script on instance via COC
3. Install JiuwenSwarm, configure systemd service, start service
4. Wait for completion (~15 minutes). Only retry if script execution errors occur.

### Phase 5: Verify Deployment Result
1. Query COC deployment task status
2. Verify `jiuwenswarm` service is running (`systemctl is-active`)
3. Verify `.env` has `FRONTEND_HOST=0.0.0.0`
4. Verify all ports bound to 0.0.0.0: 5173, 18092, 19000, 19001
5. Check service health (`curl localhost:5173` returns 200)
6. Output web access URL: `http://{public_ip}:5173`
7. Remind user to configure security group for external access

### Phase 6: Model Configuration
1. Interactively collect: API_BASE, API_KEY, MODEL_NAME, MODEL_PROVIDER
2. Generate COC remote execution script: backup `.env`, update 4 core parameters, set permission 600
3. Restart JiuwenSwarm service

### Phase 7: Message Channel Configuration
1. Select channel type: xiaoyi / feishu / dingtalk
2. Collect configuration based on channel type:
   - xiaoyi: AK, SK, Agent ID
   - feishu: App ID, App Secret
   - dingtalk: Client ID, Client Secret, Allow From
3. Generate COC remote execution script: backup `config.yaml`, update channel fields, set permission 644
4. Restart JiuwenSwarm service

### COC Task Status Query
Query COC execution status by UUID. Supports single query, verbose output, wait-for-completion, and file loading. See [references/verification-method.md](references/verification-method.md) for details.

| Status | Description |
|--------|-------------|
| READY | Ready |
| PROCESSING | Running, waiting required |
| FINISHED | Completed successfully |
| ABNORMAL | Execution abnormal, failed |
| CANCELED | Canceled |

---

## 核心命令

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt
```

**Credential configuration (choose one):**

Option A — hcloud CLI config (recommended, no env vars needed):
```bash
hcloud configure set --cli-mode=AKSK --cli-region=cn-north-4 \
  --cli-access-key=<your-ak> --cli-secret-key=<your-sk>
# For STS token: also add --cli-security-token=<your-token>
```

Option B — Environment variables:
```bash
export HUAWEICLOUD_SDK_AK=<your-access-key>
export HUAWEICLOUD_SDK_SK=<your-secret-key>
export HUAWEICLOUD_SDK_SECURITY_TOKEN=<your-security-token>  # STS only
export HUAWEICLOUD_REGION="cn-north-4"
```

### Deployment Commands
```bash
# 1. Environment preparation
python scripts/prepare_env.py

# 2. Create instance (interactive confirmation)
python scripts/create_instance.py --name jiuwenSwarm-<timestamp> --flavor 2c-4g-50g --wait

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

### COC Status Query Commands
```bash
# Query single task status
python scripts/query_coc_status.py --uuid <execute_uuid>

# Wait for task completion with custom timeout
python scripts/query_coc_status.py --uuid <execute_uuid> --wait --timeout 3600 --interval 30

# Load UUID from JSON file
python scripts/query_coc_status.py --from-file new_instance_info.json
```

---

## 参数确认

### ⚠️ Customer Confirmation Required

**Before executing any cloud resource creation operations, explicit customer consent must be obtained!**

| Operation | Confirmation Required |
|-----------|----------------------|
| Create new Flexus L instance | **Required** |
| Deploy application on existing instance | **Required** |
| Modify cloud resource configuration | **Required** |

**Confirmation Template**:
```
============================================================
⚠️ Cloud Resource Creation Confirmation
============================================================
Operation to be executed: Create new Flexus L instance

Instance Specifications:
  - Name: {instance_name}
  - Flavor: {flavor} (2c-4g-50g ~60 CNY/month / 2c-4g-70g ~100 CNY/month / 4c-8g-180g ~170 CNY/month)
  - Region: {region}
  - Estimated Cost: Calculated based on selected flavor

Resources will be created immediately after confirmation.
Please reply "confirm" or "agree" to continue.
============================================================
```

### User-Configurable Parameters

#### create_instance.py
| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| --name | Instance name | jiuwenSwarm-{timestamp} |
| --flavor | Instance flavor (2c-4g-50g / 2c-4g-70g / 4c-8g-180g) | 2c-4g-50g |
| `--region` | Region (cn-north-4/cn-east-3/cn-south-1/cn-southwest-2). If not specified, interactive selection will be shown. | (Interactive) |
| `--wait` | Wait for creation completion (polls RMS every **30s** for instance status) | False |
| --timeout | Maximum time to wait in seconds when `--wait` is used | 600 (10 minutes) |
| --confirm | Skip confirmation prompt | False |

#### deploy_service.py
| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| --ip | Instance public IP | Required |
| --wait | Wait for deployment completion | True |
| --timeout | Timeout in seconds | 1800 |

#### config_model.py
| Parameter | Description |
|-----------|-------------|
| --api-base | Model API URL |
| --api-key | Model API key |
| --model-name | Model name |
| --model-provider | Model provider |
| --ip | Instance public IP |
| --interactive | Interactive configuration |

#### config_channel.py
| Parameter | Description |
|-----------|-------------|
| --channel | Channel type (xiaoyi/feishu/dingtalk) |
| --ip | Instance public IP |
| --interactive | Interactive configuration |

#### query_coc_status.py
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

## Directory Structure

```
huawei-cloud-flexus-l-deploy-jiuwenswarm/
├── SKILL.md                    # Skill documentation
├── requirements.txt            # Python dependency list
├── scripts/                    # Phased deployment scripts
│   ├── utils.py                # Utility functions
│   ├── prepare_env.py          # Environment preparation
│   ├── create_instance.py      # Create Flexus L instance
│   ├── install_deps.py         # COC remote dependency installation
│   ├── deploy_service.py       # COC remote service deployment
│   ├── verify_deployment.py    # Verify deployment result
│   ├── config_model.py         # Model configuration
│   ├── config_channel.py       # Message channel configuration
│   └── query_coc_status.py     # COC task status query
├── assets/                     # Template files
│   ├── deploy_script_template.sh # Deployment script template
│   ├── jiuwenswarm.service.template # systemd service template
│   ├── config_template.yaml    # Configuration template
│   └── env_template.env        # Environment variable template
└── references/                 # Reference documents
    ├── api-specs.md            # API specifications
    ├── deployment-checklist.md # Deployment checklist
    ├── iam-policies.md         # IAM policies
    ├── verification-method.md  # Verification methods
    ├── acceptance-criteria.md  # Acceptance criteria
    └── troubleshooting.md      # Troubleshooting guide
```

---

## Web UI Access

Web UI access requires two conditions:
1. **Service bound to 0.0.0.0** (configured via `.env` `FRONTEND_HOST=0.0.0.0`)
2. **Security group allows port 5173** (configured in Huawei Cloud Console)

#### .env Configuration (Service-side)
The `.env` file at `/root/.jiuwenswarm/config/.env` must use the correct variable names:

| .env Variable        | Purpose              | Required Value |
| :------------------- | :------------------- | :------------- |
| `FRONTEND_HOST`      | Frontend HTTP bind   | `0.0.0.0`      |
| `FRONTEND_PORT`      | Frontend HTTP port   | `5173`         |
| `WEB_HOST`           | WebChannel bind      | `0.0.0.0`      |
| `AGENT_SERVER_HOST`  | AgentServer bind     | `0.0.0.0`      |
| `GATEWAY_HOST`       | Gateway bind         | `0.0.0.0`      |

#### Security Group Configuration (Cloud-side)
1. Login to [Flexus L Console](https://console.huaweicloud.com/smb/?/resource/list)
2. Find your JiuwenSwarm instance → instance details → Security/Network
3. Configure security group rules to open port 5173 (TCP inbound)

**Access URL**: `http://<instance_public_ip>:5173`
**Security Warning**: After opening the port, JiuwenSwarm Web interface will be accessible. Please evaluate security risks before enabling. It is recommended to open temporarily only when needed and close after use.

---

## Huawei Cloud Credential Configuration

**Credential priority: hcloud config file → environment variables.**

### Option 1: hcloud CLI Config File (Recommended)
Credentials are read from `~/.hcloud/config.json`. If encryption is enabled (`authEncrypt=true`), the script automatically disables it to read plaintext values.

```bash
# Permanent credentials
hcloud configure set --cli-mode=AKSK --cli-region=cn-north-4 \
  --cli-access-key=<AK> --cli-secret-key=<SK>

# Temporary credentials (STS Token)
hcloud configure set --cli-mode=AKSK --cli-region=cn-north-4 \
  --cli-access-key=<AK> --cli-secret-key=<SK> --cli-security-token=<TOKEN>
```

No environment variables needed — the script reads directly from the config file.

### Option 2: Environment Variables (Fallback)
| Environment Variable | Description | Required |
|---------------------|-------------|----------|
| `HUAWEICLOUD_SDK_AK` | Access Key (permanent or temporary) | Yes |
| `HUAWEICLOUD_SDK_SK` | Secret Key (permanent or temporary) | Yes |
| `HUAWEICLOUD_SDK_SECURITY_TOKEN` | Security Token (STS only) | No |
| `HUAWEICLOUD_REGION` | Huawei Cloud Region (default: cn-north-4) | No |

**Reference**: https://support.huaweicloud.com/iam_faq/iam_01_0620.html

---

## Key API Endpoints

| Service | Endpoint | Purpose |
|---------|----------|---------|
| Flexus L | https://hcss.{region}.myhuaweicloud.com/v1/light-instances | Create/query instances |
| IAM | KooCLI: `hcloud IAM KeystoneListProjects --cli-region=<region> [--name=<region>]` | Get Project ID / domain ID (global service, hcloud auto-resolves domain ID with valid credentials) |
| RMS | KooCLI: `hcloud RMS ListAllResources --cli-region=cn-north-4 --cli-domain-id=<domain_id> [--region_id=<region>] [--type=hcss.l-instance]` | Query resources (global service: always use unified cn-north-4 endpoint, filter by target region via `region_id` param) |
| COC | https://coc.myhuaweicloud.com/v1/job/scripts/{script_uuid} | Remote script execution (global service: SDK client always uses cn-north-4 endpoint, each target instance's region is carried in the request body) |

**Supported Regions**: cn-north-4 (North Beijing 4), cn-east-3 (East Shanghai 1), cn-south-1 (South Guangzhou), cn-southwest-2 (Southwest Guiyang 1)

**System Image**: Ubuntu 24.04 LTS

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
  Port Binding: 0.0.0.0:5173 (verified)
  Submit Time: {submit_time}

NOTE: Huawei Cloud security group must allow inbound TCP 5173
      for external web access. Configure at:
      https://console.huaweicloud.com/smb/?/resource/list

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

---

## 参考文档

The following reference documents provide detailed information for this skill:

| Document | Description |
|----------|-------------|
| [references/api-specs.md](references/api-specs.md) | API specifications for Huawei Cloud services (Flexus L, IAM, RMS, COC) |
| [references/iam-policies.md](references/iam-policies.md) | IAM permission policies and policy JSON for deployment |
| [references/deployment-checklist.md](references/deployment-checklist.md) | Pre/post deployment checklist for all phases |
| [references/verification-method.md](references/verification-method.md) | Verification methods and acceptance testing procedures |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria and sign-off requirements |
| [references/troubleshooting.md](references/troubleshooting.md) | Troubleshooting guide for common deployment issues |

