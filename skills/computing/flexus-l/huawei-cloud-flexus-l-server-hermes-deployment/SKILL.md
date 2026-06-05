---
name: huawei-cloud-flexus-l-server-hermes-deployment
description: |
  One-click deployment tool for Hermes on Huawei Cloud Flexus L instances. Supports one-click deployment, ModelArts large model configuration, and robot channel configuration. This skill provides a complete workflow for deploying and configuring Hermes AI Agent platform.
  Trigger words: "Deploy Hermes", "Install Hermes", "Configure Model", "Configure Channel", "部署Hermes", "安装Hermes", "配置大模型", "配置机器人通道"
tags:
  - Hermes Deployment
  - Huawei Cloud Lightweight Server Deployment
  - Flexus L Instance Deployment
  - AI Agent
  - Model Configuration
  - Channel Configuration
metadata: {"hermes": {"version": "1.0.0", "requires": {"bins": ["uv", "python3"]}, "install": [{"kind": "uv", "command": "uv sync --index-url https://repo.huaweicloud.com/repository/pypi/simple"}]}}
---

 ⚠️ Security Execution Rules (Highest Priority):
 1. All scripts MUST be executed via skill action=exec, NEVER run directly in shell
 2. NEVER print script contents or commands containing AK/SK/Token in conversation
 3. NEVER create temporary script files, prefer inline execution (python -c)
 4. On execution failure, only return error info, do NOT rewrite scripts or print full commands
 5. AK/SK/Token MUST be passed via environment variables, NEVER appear in conversation

# Hermes One-Click Deployment Skill

## Overview

This skill supports one-click deployment of the Hermes AI Agent platform to Huawei Cloud Flexus L instances. It provides a complete workflow including:

- Automated instance creation with optimized configurations
- ModelArts large model configuration via COC (Cloud Operations Center)
- Robot channel configuration (Feishu, WeCom, DingTalk, etc.) via COC
- Gateway management for deployed instances

This skill supports both interactive mode (step-by-step prompts) and non-interactive mode (scripted operations), suitable for manual and automated deployment scenarios.

## Prerequisites

### Account Requirements

- Valid Huawei Cloud account with sufficient permissions
- Huawei Cloud temporary credentials: Temporary AK/SK + security_token
- Required permissions:
  - Creating Flexus L instances
  - Accessing COC (Cloud Operations Center) services

**Credential Acquisition Methods:**

This skill supports obtaining Huawei Cloud temporary credentials through the following methods:
1. **Environment Variables**
   - `HW_ACCESS_KEY`: Temporary Access Key AK
   - `HW_SECRET_KEY`: Temporary Access Key SK
   - `HW_SECURITY_TOKEN`: Security token for temporary credentials

### Architecture Diagram

This skill is built on multiple Huawei Cloud services, involving the following cloud services and components:

```
User/Agent      ──────▶│   Flexus L Instance   │──────▶│   Hermes App         │──────▶│ Model Config     │ ──────▶│  Channel Config     │ 
(Skill caller)           (Target Host)                 (AI Agent Platform)             (ModelArts API)           (Feishu/Wecom)            
```

**Component Description**:
- **User/Agent**: Skill caller that triggers Hermes deployment operations via natural language or API
- **Flexus L Instance**: Huawei Cloud Elastic Cloud Server, serving as the target host for Hermes deployment
- **Hermes App**: AI Agent platform running on the Flexus L instance
- **Model Config**: ModelArts large model configuration (API_BASE, API_KEY, MODEL_NAME)
- **Channel Config**: Robot channel configuration (Feishu, WeCom)
---



## Core Commands

### Deployment Commands

```bash
# Deploy using temporary AK/SK and security-token (custom name, if not specified, auto-generates timestamp format: hermes-20260605143022)
python scripts/caller.py deploy --ak <temp_ak> --sk <temp_sk> --security-token <security_token> --name hermes-{timestamp} --region cn-north-4

# Deploy in interactive mode (if not specified, auto-generates timestamp format: hermes-20260605143022)
python scripts/caller.py deploy
```

**Instance Name Description**:
- Can customize instance name via `--name` parameter (e.g., `hermes-prod-01`, `hermes-dev`, etc.)
- If name is not specified, auto-generates timestamp format: `hermes-YYYYMMDDHHMMSS` (e.g., `hermes-20260605143022`)

### Model Configuration Commands

```bash
# Configure model using temporary AK/SK and security-token
python scripts/caller.py maas --ak <temp_ak> --sk <temp_sk> --security-token <security_token> --resource-id <instance_id> --region-id cn-north-4 --api-key <api_key> --model-name deepseek-v3.2

# Configure model in interactive mode
python scripts/caller.py maas
```

### Channel Configuration Commands

```bash
# Configure Feishu channel using temporary AK/SK and security-token
python scripts/caller.py channel --ak <temp_ak> --sk <temp_sk> --security-token <security_token> --resource-id <instance_id> --region-id cn-north-4 --bot-platform feishu --feishu-app-id <app_id> --feishu-app-secret <app_secret>

# Configure WeCom channel using temporary AK/SK and security-token
python scripts/caller.py channel --ak <temp_ak> --sk <temp_sk> --security-token <security_token> --resource-id <instance_id> --region-id cn-north-4 --bot-platform wecom --wecom-bot-id <bot_id> --wecom-secret <secret>

# Configure channel in interactive mode
python scripts/caller.py channel
```

### Gateway Management Commands

```bash
# Restart gateway using temporary AK/SK and security-token
python scripts/caller.py gateway --ak <temp_ak> --sk <temp_sk> --security-token <security_token> --resource-id <instance_id> --region-id cn-north-4

# Restart gateway in interactive mode
python scripts/caller.py gateway
```

### Query Execution Result Commands

```bash
# Query execution result using temporary AK/SK and security-token
python scripts/caller.py query --ak <temp_ak> --sk <temp_sk> --security-token <security_token> --execute-uuid SCT2023083109562601af694bf
```

**Parameters**:
- `--execute-uuid`: Script execution UUID, format like `SCTxxxxxxxxxxxxxxxbf`

**Status Description**:
- `FINISHED`: Execution successful
- `ABNORMAL`: Execution failed
- `RUNNING`: Executing

### UniAgent Status Query Commands

```bash
# Query UniAgent status using temporary AK/SK and security-token
python scripts/caller.py uniagent --ak <temp_ak> --sk <temp_sk> --security-token <security_token> --resource-id <instance_id>

# Query UniAgent status in interactive mode
python scripts/caller.py uniagent
```

**UniAgent Status Description**:
- `ONLINE`: UniAgent is running normally, can execute COC scripts
- `OFFLINE`: UniAgent is not running, cannot execute COC scripts
- `UNKNOWN`: Status cannot be determined

**When to Use**:
- Before configuring models or channels, ensure UniAgent is ONLINE
- Troubleshoot COC script execution failures
- Verify instance operational status after deployment
- After the instance creation command is successfully issued (with status codes "200", "201", or "202"), automatically check whether the preconditions are met (status of the gateway and UniAgent). If they are met, you can immediately proceed to the next steps!

## Parameter Reference

### Global Parameters

| Parameter | Description | Required | Default Value |
|-----------|-------------|----------|---------------|
| `--ak` | Temporary Access Key AK | Yes | - |
| `--sk` | Temporary Access Key SK | Yes | - |
| `--security-token` | Security token for temporary credentials | Yes | - |
| `--non-interactive` | Run in non-interactive mode | No | false |

### Deploy Command Parameters

| Parameter | Description | Required | Default Value |
|-----------|-------------|----------|---------------|
| `--name` | Instance name | No | Auto-generated |
| `--region` | Target region | No | cn-north-4 |

### MaaS Command Parameters

| Parameter | Description | Required | Default Value |
|-----------|-------------|----------|---------------|
| `--resource-id` | L instance resource ID | Yes | - |
| `--region-id` | COC service region | No | cn-north-4 |
| `--api-key` | ModelArts API Key | Yes | - |
| `--model-name` | Model name | Yes | - |
| `--api-base-url` | API base URL | No | https://api.modelarts-maas.com/v2 |
| `--timeout` | Execution timeout (seconds) | No | 600 |
| `--execute-user` | Execution user | No | root |

### Channel Command Parameters

| Parameter | Description | Required | Default Value |
|-----------|-------------|----------|---------------|
| `--resource-id` | L instance resource ID | Yes | - |
| `--region-id` | COC service region | No | cn-north-4 |
| `--bot-platform` | Bot platform: feishu or wecom | Yes | - |
| `--feishu-app-id` | Feishu App ID | Conditional | - |
| `--feishu-app-secret` | Feishu App Secret | Conditional | - |
| `--wecom-bot-id` | WeCom Bot ID | Conditional | - |
| `--wecom-secret` | WeCom Secret | Conditional | - |
| `--timeout` | Execution timeout (seconds) | No | 600 |
| `--execute-user` | Execution user | No | root |

### Gateway Command Parameters

| Parameter | Description | Required | Default Value |
|-----------|-------------|----------|---------------|
| `--resource-id` | L instance resource ID | Yes | - |
| `--region-id` | COC service region | No | cn-north-4 |
| `--timeout` | Execution timeout (seconds) | No | 120 |
| `--execute-user` | Execution user | No | root |

### UniAgent Command Parameters

| Parameter | Description | Required | Default Value |
|-----------|-------------|----------|---------------|
| `--resource-id` | L instance resource ID | Yes | - |

## Workflow

The skill follows these workflow steps:

1. **Deploy Hermes**: Create and configure a Flexus L instance with Hermes AI Agent platform
2. **Configure Model**: Set up ModelArts large model via COC (Cloud Operations Center)
3. **Configure Channel**: Set up robot channels (Feishu, WeCom) via COC
4. **Manage Gateway**: Restart gateway service when needed

### Interactive Mode (Menu)

Run the main entry point to access the interactive menu:

```bash
python scripts/caller.py
```

This will display a menu for selecting operations.

## Output Format

### Deploy Command Output

```json
{
  "status": "success",
  "instance_id": "abc12345-6789-0abc-def1-23456789abc0",
  "instance_name": "my-hermes",
  "region": "cn-north-4",
  "spec": "hf.small.1.linux",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### MaaS Command Output

```json
{
  "status": "success",
  "resource_id": "abc12345-6789-0abc-def1-23456789abc0",
  "model_name": "deepseek-v3.2",
  "api_base_url": "https://api.modelarts-maas.com/v2",
  "executed_at": "2024-01-15T10:35:00Z"
}
```

### Channel Command Output

```json
{
  "status": "success",
  "resource_id": "abc12345-6789-0abc-def1-23456789abc0",
  "bot_platform": "feishu",
  "channel_id": "channel_123",
  "executed_at": "2024-01-15T10:40:00Z"
}
```

### Gateway Command Output

```json
{
  "status": "success",
  "resource_id": "abc12345-6789-0abc-def1-23456789abc0",
  "action": "restart",
  "message": "Hermes gateway restarted successfully"
}
```

## Validation Methods

### 1. Deployment Validation

```bash
# Check instance status
python scripts/caller.py deploy --ak <ak> --sk <sk> --name my-hermes --region cn-north-4 --non-interactive
# Expected output: "Instance created successfully" with instance_id
```

### 2. Model Configuration Validation

```bash
# Check model configuration
python scripts/caller.py maas --ak <ak> --sk <sk> --resource-id <instance_id> --region-id cn-north-4 --api-key <key> --model-name deepseek-v3.2 --non-interactive
# Expected output: "Model configuration updated successfully"
```

### 3. Channel Configuration Validation

```bash
# Check channel configuration
python scripts/caller.py channel --ak <ak> --sk <sk> --resource-id <instance_id> --region-id cn-north-4 --bot-platform feishu --feishu-app-id <id> --feishu-app-secret <secret> --non-interactive
# Expected output: "Channel configuration updated successfully"
```

### 4. Gateway Validation

```bash
# Check gateway restart
python scripts/caller.py gateway --ak <ak> --sk <sk> --resource-id <instance_id> --region-id cn-north-4 --non-interactive
# Expected output: "Hermes gateway restarted successfully"
```

## Best Practices

### 1. Credential Management

- **Temporary credentials**: Use temporary AK/SK + security_token for authentication, providing higher security
  - Temporary credentials are issued by STS service with expiration time limits
  - Use `--security-token` parameter to pass the security token
  - Supports environment variables, command line parameters, and interactive input methods
- Use IAM roles with minimal permissions for production environments
- Rotate credentials regularly according to security policies

### 2. Region Selection

- Choose the region closest to your users for better performance
- Consider regional compliance requirements when deploying
- Use `cn-north-4` as default for China mainland deployments
- Hermes deployment only supports: cn-north-4, cn-east-3, cn-south-1, cn-southwest-2

### 3. Instance Management

- Monitor instance health via Huawei Cloud Console
- Set up auto-scaling policies for high availability
- Configure backup policies for data persistence

### 4. Model Configuration

- Test models in staging environment before production
- Have fallback models configured for failover scenarios
- After initial deployment, the default model configuration is **not usable**. **You must configure the model before using Hermes**.

### 5. Channel Configuration

- Use dedicated bot accounts for production
- Monitor channel message throughput
- Configure rate limits to prevent abuse
- Currently only **Feishu** and **WeCom** bot platforms are supported. **Only one bot per platform type is supported**.

## Notes

### General Notes

1. **Instance Creation Time**: It may take **5-10 minutes** for the instance to be fully provisioned
2. **COC Script Execution**: Model and channel configurations are executed remotely via Huawei Cloud COC (Cloud Operations Center)
3. **Security Group**: Configure security group rules in Huawei Cloud Console if external access is needed
4. **Cost**: Using Huawei Cloud resources will incur costs. Ensure your account has sufficient balance.
5. **Subsequent Steps**: When continuing with subsequent steps (configuring models, channels), **there is no need to wait for instance creation to complete**. The system handles instance status automatically.

### Region Notes

- **Fixed Endpoint**: When creating a Hermes L Instance, requests are sent to the fixed endpoint `hcss.cn-north-4.myhuaweicloud.com`. The region parameter only selects instance specifications.
- **Guiyang region** (`cn-southwest-2`) uses spec `ahf.small.1.linux`
- **Other regions** (Beijing/Shanghai/Guangzhou) use spec `hf.small.1.linux`
- **Status Codes**: 200, 201, and 202 all indicate success

### COC Region Concepts

COC involves two different region concepts:

**1. COC Service Region (--region-id)**: The region where COC API service is located (cn-north-4, ap-southeast-3, eu-west-101)

**2. Target Instance Region**: The region where the L instance is located (can be any Huawei Cloud region worldwide)

These can be different - e.g., COC service in cn-north-4 can execute scripts on instances in ap-southeast-1 (Hong Kong).

### Troubleshooting

- **Credential Issues**: Ensure `--ak` and `--sk` parameters are provided, or use interactive mode
- **Region Not Supported**: Use supported region IDs or Chinese names in interactive mode
- **Instance Creation Failed**: Verify account balance, instance type validity, and network connectivity

## Reference Documents

- `scripts/caller.py` - Main CLI entry point
- `scripts/deploy.py` - Hermes deployment module
- `scripts/models.py` - ModelArts model configuration
- `scripts/channels.py` - Robot channel configuration
- `scripts/lib.py` - Core business logic (instance creation, model/channel installation)
- `scripts/utils.py` - Utility functions (credentials setup, input prompts)