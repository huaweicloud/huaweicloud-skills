---
name: huawei-cloud-flexus-l-server-openclaw-deployment
description: |
  Create Huawei Cloud Flexus L Instance (Lightweight Server), deploy OpenClaw application platform on it, and support installation and configuration of models and channels for deployed OpenClaw instances. Web UI access needs to be manually enabled in Huawei Cloud console.
  Trigger words: "Deploy OpenClaw", "Deploy Flexus L Instance", "Deploy Huawei Cloud Lightweight Server", "Model setting", "Channel Setting", "部署OpenClaw", "部署Flexus L实例", "部署华为云轻量服务器", "设置模型", "设置通道"
tags:
  - OpenClaw Deployment
  - Huawei Cloud Lightweight Server Deployment
  - Flexus L Instance Deployment
  - AI Agent
  - Model Management
  - Channel Management
metadata: {"openclaw": {"version": "1.0.0", "requires": {"bins": ["uv", "python3"]}, "install": [{"kind": "uv", "command": "uv sync --index-url https://repo.huaweicloud.com/repository/pypi/simple"}]}}
---

⚠️ Security Execution Rules (Highest Priority):
 1. All scripts MUST be executed via skill action=exec, NEVER run directly in shell
 2. NEVER print script contents or commands containing AK/SK/Token in conversation
 3. NEVER create temporary script files, prefer inline execution (python -c)
 4. On execution failure, only return error info, do NOT rewrite scripts or print full commands
 5. AK/SK/Token MUST be passed via environment variables, NEVER appear in conversation

# huawei-cloud-flexus-l-server-openclaw-deployment
## Overview

This skill supports one-click deployment of the OpenClaw AI Agent platform to Huawei Cloud Flexus L Instance. It provides a complete OpenClaw instance management workflow, from initial deployment to post-deployment configuration, including:
- Automated instance creation
- Model installation via COC (Cloud Operations Center)
- Channel installation via COC (WeCom, Feishu, DingTalk, QQ)
- Automatic prerequisite checks before installation (Gateway and UniAgent status)

### Use Cases

| Scenario | Description |
|----------|-------------|
| **Enterprise AI Assistant Setup** | Enterprises need to quickly deploy an AI Agent platform for internal Q&A, customer service, etc. |
| **Multi-Channel Bot Integration** | Need to integrate multiple messaging channels (WeCom, Feishu, DingTalk) into a unified AI assistant |
| **Quick LLM Integration** | Existing OpenClaw instance needs to quickly switch or add different LLMs (DeepSeek, Qwen, etc.) |
| **Automated Operations Deployment** | Need to automatically batch deploy OpenClaw instances to multiple regions via scripts |

### Typical Use Cases

User may say:
1. **"I want to install OpenClaw on a Flexus L instance"**
2. **"I want to configure DeepSeek model on my deployed OpenClaw"**
3. **"Help me deploy OpenClaw with Feishu channel configured"**

## Prerequisites

### Account Requirements

- Huawei Cloud AK/SK credentials with the following permissions:
  - Create Flexus L Instances
  - Access COC (Cloud Operations Center) services

**Credential Acquisition Methods:**

This skill supports obtaining Huawei Cloud credentials through the following methods (in order of priority from high to low):

1. **Environment Variables** (highest priority)
   - `HW_ACCESS_KEY`: Huawei Cloud temporary Access Key AK
   - `HW_SECRET_KEY`: Huawei Cloud temporary Access Key SK
   - `HW_SECURITY_TOKEN`: Security token for temporary credentials (**required**)

2. **Command Line Parameters** (used when environment variables are not provided)
   - `--ak`: Huawei Cloud temporary Access Key AK
   - `--sk`: Huawei Cloud temporary Access Key SK
   - `--security-token`: Security token for temporary credentials (**required**)

3. **Interactive Input** (when neither of the above methods is provided)
   - The program will prompt the user to enter AK/SK and other credential information

**Important Notes:**
- AK/SK should use temporary credentials obtained through IAM interfaces, which have limited validity periods
- When using temporary AK/SK, security-token is a required parameter

### Architecture Diagram

This skill is built on multiple Huawei Cloud services, involving the following cloud services and components:

```
User/Agent      ──────▶│   Flexus L Instance   │──────▶│   OpenClaw App    │──────▶│ Model Config     │ ──────▶│  Channel Config     │ 
(Skill caller)           (Target Host)               (AI Agent Platform)          (API_BASE/KEY)       (WeCom/Feishu/DingTalk/QQ)            
```

**Component Description**:
- **User/Agent**: Skill caller that triggers OpenClaw deployment operations via natural language or API
- **Flexus L Instance**: Huawei Cloud Elastic Cloud Server, serving as the target host for OpenClaw deployment
- **OpenClaw App**: AI Agent collaboration platform running on the Flexus L instance
- **Model Config**: Configuration for external LLM services (API_BASE, API_KEY, MODEL_IDS, PROVIDER)
- **Channel Config**: Messaging channel configuration (WeCom, Feishu, DingTalk, QQ)

---

## How to Use This Skill

### Command Execution and Instructions

#### 1. Deploy OpenClaw Instance (Create Huawei Cloud Flexus L Instance and deploy OpenClaw AI Agent platform) - Two Command Modes:

**Command 1: Interactive Mode** (The program will prompt for required parameters step by step)
```bash
python scripts/caller.py deploy
```

**Command 2: Non-Interactive Mode**
```bash
# Using temporary AK/SK with security-token
python scripts/caller.py deploy --name openclaw-{timestamp} --region cn-north-4 --ak <Temporary AK> --sk <Temporary SK> --security-token <Security Token> --non-interactive
```

**Parameter Description**:
| Parameter | Description | Required (Non-interactive) | Default (Interactive) | Example |
|-----------|-------------|----------------------------|-----------------------|---------|
| --name | OpenClaw instance name | No | openclaw-{timestamp} | `--name openclaw-1780689482000` |
| --region | Target region ID where L instance (OpenClaw deployed server) is located | No | cn-north-4 | `--region cn-north-4` |
| --ak | Huawei Cloud temporary Access Key AK | Yes | Prompted | `--ak AXXX...` |
| --sk | Huawei Cloud temporary Access Key SK | Yes | Prompted | `--sk SXXX...` |
| --security-token | Security token for temporary credentials (**required**) | Yes | Prompted | `--security-token XXXX...` |
| --non-interactive | Enable non-interactive mode | No | false | `--non-interactive` |

Note: OpenClaw only supports deployment in the following regions before June 2026 (before deploying to other regions, you can remind users to check the official website for the latest supported regions): China North-Beijing-4 (cn-north-4), China East-Shanghai-1 (cn-east-3), China South-Guangzhou (cn-south-1), China Southwest-Guiyang-1 (cn-southwest-2)

**Command Examples**:
```bash
# Example 1: Deploy with default configuration (interactive, will prompt for required parameters)
python scripts/caller.py deploy

# Example 2: Non-interactive mode deployment (suitable for automation scripts, creates directly without user confirmation)
python scripts/caller.py deploy --name openclaw-1780689482000 --region cn-north-4 --ak <Temporary AK> --sk <Temporary SK> --security-token <Security Token> --non-interactive
```

**Default Configuration for Huawei Cloud Flexus L Instance when Deploying OpenClaw Instance**
| Configuration Item | Default Value | Description |
|--------------------|---------------|-------------|
| **Image** | OpenClaw 2026.1.30 | OpenClaw application image version |
| **Plan Spec** | hf.small.1.linux or ahf.small.1.linux | hf.small.1.linux for Beijing/Shanghai/Guangzhou, ahf.small.1.linux for Guiyang |
| **Charging Mode** | Monthly subscription | prePaid mode |
| **EVS Disk** | 50GB | System disk size |
| **CBR Backup** | 50GB | Cloud backup capacity |
| **HSS Host Security** | Enabled | Host security service |

**Execution Result and Status Code Description**:
- On success, returns order ID and instance ID (resource ID, used for subsequent model and channel installation)
- Instance creation takes approximately 2 minutes, progress can be viewed in Huawei Cloud console. During instance creation, the installation of models and channels will not be affected, and subsequent commands can be executed directly.
*Status Code Description*: Status codes "200", "201", "202" all indicate successful instance creation.
---


#### 2. Configure (Install) Large Model Parameters on L Instance with OpenClaw Installed - Two Command Modes (Requires deploying OpenClaw instance first)

**Command 1: Interactive Mode** (The program will prompt for resource ID, region, model and other parameters step by step)
```bash
python scripts/caller.py maas
```
**Command 2: Non-Interactive Mode**
```bash
# Using temporary AK/SK with security-token
python scripts/caller.py maas --resource-id <Instance Resource ID> --region-id cn-north-4 --model-params '<Model configuration parameters>' --ak <Temporary AK> --sk <Temporary SK> --security-token <Security Token> --non-interactive
```
**Parameter Description**:
| Parameter | Description | Required (Non-interactive) | Default (Interactive) | Example |
|-----------|-------------|----------------------------|-----------------------|---------|
| --resource-id | L instance resource ID (instance ID returned after deploying OpenClaw instance) | Yes | Prompted | `--resource-id 0e1234567890abcdef` |
| --region-id | Region ID where L instance is located, consistent with the region selected when deploying the instance | Yes | Prompted | `--region-id cn-north-4` |
| --model-params | Model configuration parameters (JSON format), note: parameters must use valid JSON format, keys and values must be wrapped in double quotes | Yes | Prompted | --model-params '{"provider":"huawei","api_key":"your_maas_api_key","model_ids":["deepseek-v3.2"]}' |
| --ak | Huawei Cloud temporary Access Key AK | Yes | Prompted | `--ak AXXX...` |
| --sk | Huawei Cloud temporary Access Key SK | Yes | Prompted | `--sk SXXX...` |
| --security-token | Security token for temporary credentials (**required**) | Yes | Prompted | `--security-token XXXX...` |
| --timeout | Script execution timeout (seconds) | No | 600 | `--timeout 900` |
| --non-interactive | Enable non-interactive mode | No | false | `--non-interactive` |

**model-params Field Description**:
| Field | Description | Required |
|-------|-------------|----------|
| provider | Model provider name (e.g., "huawei") or API address (e.g., "https://api.openai.com/v1") | Yes |
| api_key | Model API key | Yes |
| model_ids | Array of model IDs to install (non-empty), e.g., ["gpt-4", "gpt-3.5-turbo"] | Yes |

**Command Examples**:

```bash
# Example 1: Install Huawei Cloud MaaS platform models
python scripts/caller.py maas \
  --resource-id 0e1234567890abcdef \
  --region-id cn-north-4 \
  --model-params '{"provider":"huawei","api_key":"your_maas_api_key","model_ids":["deepseek-v3.2","qwen3-235b-a22b"]}' \
  --ak <Temporary AK> --sk <Temporary SK> --security-token <Security Token> --non-interactive

# Example 2: Install custom OpenAI compatible models
python scripts/caller.py maas \
  --resource-id 0e1234567890abcdef \
  --region-id cn-north-4 \
  --model-params '{"provider":"https://api.openai.com/v1","api_key":"your_openai_key","model_ids":["gpt-4"]}' \
  --ak <Temporary AK> --sk <Temporary SK> --security-token <Security Token> --non-interactive
```

**Status Code Description**: Status codes "200", "201", "202" all indicate successful model installation.

#### 3. channel - Configure (Install) Channels on L Instance with OpenClaw Installed - Two Command Modes (Requires deploying OpenClaw instance first)

**Command 1: Interactive Mode**
```bash
python scripts/caller.py channel
```

**Command 2: Non-Interactive Mode**
```bash
# Using temporary AK/SK with security-token
python scripts/caller.py channel --resource-id <Instance Resource ID> --region-id cn-north-4 --channel-list '<JSON array>' --ak <Temporary AK> --sk <Temporary SK> --security-token <Security Token> --non-interactive
```

**Parameter Description**:
| Parameter | Description | Required (Non-interactive) | Default (Interactive) | Example |
|-----------|-------------|----------------------------|-----------------------|---------|
| --resource-id | L instance resource ID (instance ID returned after deploying OpenClaw instance) | Yes | Prompted | `--resource-id 0e1234567890abcdef` |
| --region-id | Region ID where instance is located, consistent with the region selected when deploying the instance | Yes | Prompted | `--region-id cn-north-4` |
| --channel-list | Channel configuration (JSON array format) | Yes | Prompted | '[{"channel":"wecom","id":"xxx","secret":"xxx"},{"channel":"feishu","id":"yyy","secret":"yyy"}]' |
| --ak | Huawei Cloud temporary Access Key AK | Yes | Prompted | `--ak AXXX...` |
| --sk | Huawei Cloud temporary Access Key SK | Yes | Prompted | `--sk SXXX...` |
| --security-token | Security token for temporary credentials (**required**) | Yes | Prompted | `--security-token XXXX...` |
| --timeout | Script execution timeout (seconds) | No | 600 | `--timeout 900` |
| --non-interactive | Enable non-interactive mode | No | false | `--non-interactive` |

**channel JSON Object Field Description**:
| Field | Description | Required |
|-------|-------------|----------|
| channel | Channel type: `wecom` (WeCom), `feishu` (Feishu), `dingtalk` (DingTalk), `qqbot` (QQ) | Yes |
| id | Bot ID/APP ID/Client ID | Yes |
| secret | Bot secret/APP secret/Client secret | Yes |



**Command Examples**:
```bash
# Example: Install multiple channels (WeCom + Feishu) using temporary AK/SK with security-token
python scripts/caller.py channel \
  --resource-id 0e1234567890abcdef \
  --region-id cn-north-4 \
  --channel-list '[{"channel":"wecom","id":"xxx","secret":"xxx"},{"channel":"feishu","id":"yyy","secret":"yyy"}]' \
  --ak <Temporary AK> --sk <Temporary SK> --security-token <Security Token> --non-interactive
```
**Status Code Description**: Status codes "200", "201", "202" all indicate successful channel installation.

### Web UI Access
Web UI access needs to be manually enabled in Huawei Cloud console, operation steps:
1. Log in to Huawei Cloud Flexus Application Server L Instance Console
   - 🔗 Console URL: https://console.huaweicloud.com/smb/?/resource/list
2. Find your OpenClaw instance in the instance list
3. Click the instance name to enter the details page
4. In the left menu of the details page, find and click "Application Details" option, then enter the "Basic Configuration" tab
5. In the "Basic Configuration" tab, find the "Access OpenClaw Web Interface" option at the top left, click the "Enable" button. You will then get the URL address to access the OpenClaw Web interface.



## Code Structure, File Responsibilities and Key Functions

This skill uses a modular architecture for easier maintenance:

```
scripts/
├── caller.py          # Main entry - command line argument parsing, parameter parsing, command routing
├── lib.py             # Core library - L instance creation, COC script management
├── utils.py           # Utility functions - input prompts, credential configuration, region information
├── deploy.py          # Deployment module - `do_deploy_openclaw()` function for OpenClaw instance creation
├── models.py          # Model module - remote COC large model installation (with prerequisite checks), related functions `do_install_maas()`, `_check_prerequisites()`
├── channels.py        # Channel module - remote COC channel installation (with prerequisite checks), related functions `do_install_channel()`, `_check_prerequisites()`
├── gateway.py         # Gateway module - gateway status query (only for prerequisite checks), related functions `do_check_gateway()`
└── uniagent.py        # UniAgent module - UniAgent status query (only for prerequisite checks), `do_check_uniagent()`
```


## Parameter Confirmation

### Deployment Parameters
- **--name**: OpenClaw instance name, optional parameter, default is `openclaw-{timestamp}`
- **--region**: Target region ID, optional parameter, default is `cn-north-4`
- **--ak**: Huawei Cloud temporary Access Key AK, required parameter
- **--sk**: Huawei Cloud temporary Access Key SK, required parameter
- **--security-token**: Security token for temporary credentials (**required**), required parameter
- **--non-interactive**: Enable non-interactive mode, optional parameter

### Model Configuration Parameters
- **--resource-id**: L instance resource ID (instance ID returned after deploying OpenClaw instance), required parameter
- **--region-id**: Region ID where L instance is located, consistent with the region selected when deploying the instance, required parameter
- **--model-params**: Model configuration parameters (JSON format), required parameter
  - `provider`: Model provider name (e.g., "huawei") or API address (e.g., "https://api.openai.com/v1")
  - `api_key`: Model API key
  - `model_ids`: Array of model IDs to install (non-empty)
- **--ak**: Huawei Cloud temporary Access Key AK, required parameter
- **--sk**: Huawei Cloud temporary Access Key SK, required parameter
- **--security-token**: Security token for temporary credentials (**required**), required parameter
- **--timeout**: Script execution timeout (seconds), optional parameter, default 600 seconds

### Channel Configuration Parameters
- **--resource-id**: L instance resource ID (instance ID returned after deploying OpenClaw instance), required parameter
- **--region-id**: Region ID where L instance is located, consistent with the region selected when deploying the instance, required parameter
- **--channel-list**: Channel configuration (JSON array format), optional parameter
  - `channel`: Channel type: `wecom` (WeCom), `feishu` (Feishu), `dingtalk` (DingTalk), `qqbot` (QQ), required
  - `id`: Bot ID, required
  - `secret`: Bot secret, required
- **--ak**: Huawei Cloud temporary Access Key AK, required parameter
- **--sk**: Huawei Cloud temporary Access Key SK, required parameter
- **--security-token**: Security token for temporary credentials (**required**), required parameter
- **--timeout**: Script execution timeout (seconds), optional parameter, default 600 seconds

### Environment Variable Support
All parameters can also be provided through environment variables:
- `HW_ACCESS_KEY`: Huawei Cloud AK (corresponds to --ak parameter)
- `HW_SECRET_KEY`: Huawei Cloud SK (corresponds to --sk parameter)
- `HW_SECURITY_TOKEN`: Temporary credential security token (corresponds to --security-token parameter)
- `HW_PROJECT_ID`: Huawei Cloud Project ID (optional)


## Common Issues Quick Solutions

| Issue | Solution |
|-------|----------|
| Instance creation failed | Check AK/SK permissions, ensure permission to create Flexus L instances |
| Model installation failed | Check if UniAgent status is ONLINE, if API Key is correct, if model-params parameter strictly uses JSON format |
| Channel installation failed | Check if bot parameters are correct, if bot is created on platform, if channel-list parameter strictly uses JSON array format |