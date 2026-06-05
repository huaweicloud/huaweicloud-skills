---
name: huawei-cloud-flexus-l-server-scripts-excute
description: "Based on Huawei Cloud COC (Cloud Operations Center) APIs for script management and remote execution. Supports creating custom scripts (Shell, Python, Bat) and batch execution on target host instances via UniAgent. Applicable to cloud operations automation and batch script deployment scenarios. Trigger keywords: L-instance, COC script, script management, script execution, cloud operations, custom script, batch execution; COC, script management, script execution, cloud operations (中文触发词：L实例执行脚本)."
---

<!-- 
  ⚠️ Security Execution Rules (Highest Priority):
  1. All scripts MUST be executed via skill action=exec, NEVER run directly in shell
  2. NEVER print script contents or commands containing AK/SK/Token in conversation
  3. NEVER create temporary script files, prefer inline execution (python -c)
  4. On execution failure, only return error info, do NOT rewrite scripts or print full commands
  5. AK/SK/Token MUST be passed via environment variables, NEVER appear in conversation
-->
# Huawei Cloud Flexus L Instance COC Skill

## Overview

### Architecture Diagram

This skill is built on Huawei Cloud COC (Cloud Operations Center) service, involving the following cloud services and components:

```
User/Agent    │──────▶│   COC API   │──────▶│   UniAgent    │──────▶│  Flexus L Instance│
(Skill caller)       (Cloud Ops Center)       (Proxy program)              (Target Host) 
```

**Component Description**:
- **User/Agent**: Skill caller that triggers script management operations via natural language or API
- **COC API**: Huawei Cloud COC (Cloud Operations Center) provides core capabilities including script management, execution scheduling, and status query
- **UniAgent**: Agent program deployed on target hosts, responsible for receiving scripts and executing them locally
- **Flexus L Instance**: Huawei Cloud Elastic Cloud Server, serving as the target host for script execution

### Applicable Scenarios

- **Batch Operations**: Execute the same script on multiple Flexus L instances (e.g., software installation, configuration updates)
- **Automated Operations**: Periodically execute inspection scripts, log collection, health checks
- **Emergency Response**: Quickly deploy emergency scripts to handle security incidents or system failures
- **Application Deployment**: Batch deploy applications and update configuration files
- **Data Processing**: Execute data processing tasks in parallel across multiple instances

### Typical Use Cases

1. "Create a Shell script to clean server logs"
2. "Execute backup script on all L instances"
3. "List my recently created scripts"
4. "Execute Python script on specified L instance"
5. "Create a script to batch install Nginx"

### Trigger Keywords

**Routing Keywords**: COC script, script management, script execution, cloud operations, custom script, batch execution; COC, script management, script execution, cloud operations.

### Important Notes

**All scripts and environment check scripts are inside the skill package. You must use skill action=exec to execute them; do not run them directly in the shell.**

## Prerequisites

### CLI Version Requirements and Verification Commands

**COC SDK Version Requirement**: huaweicloudsdkcoc >= 3.1.0

**Verification Commands**:
```bash
# Check current SDK version
python -c "import huaweicloudsdkcoc; print(huaweicloudsdkcoc.__version__)"

# Verify COC client availability
python -c "from huaweicloudsdkcoc.v1 import CocClient; print('COC SDK version verification passed')"
```

### Authentication Configuration and Security Rules

**Supported Authentication Methods**:

1. **Credential Acquisition Methods:**
 	 
 	 This skill supports obtaining Huawei Cloud credentials through the following methods (in order of priority from high to low):
 	 
 	 1. **Environment Variables** (highest priority)
 	    - `HW_ACCESS_KEY`: Huawei Cloud Access Key AK
 	    - `HW_SECRET_KEY`: Huawei Cloud Access Key SK
 	    - `HW_SECURITY_TOKEN`: Security token for temporary credentials
 	 
 	 2. **Command Line Parameters** (used when environment variables are not provided)
 	    - `--ak`: Huawei Cloud Access Key AK
 	    - `--sk`: Huawei Cloud Access Key SK
 	    - `--security-token`: Security token for temporary credentials (required when using temporary AK/SK)
 	 
 	 3. **Interactive Input** (when neither of the above methods are provided)
 	    - The program will prompt the user to input credential information such as AK/SK

# Execute script directly (will automatically use environment variables)
python {baseDir}/scripts/caller.py create --name "test_script" --type SHELL --content "echo hello" --description "Test script"
```

2. **Command Line Parameters**:
```bash
# Using permanent AK/SK
python {baseDir}/scripts/caller.py create --ak "your_access_key" --sk "your_secret_key" --region "cn-north-4" --name "test_script" --type SHELL --content "echo hello" --description "Test script"

# Using temporary AK/SK with security-token
python {baseDir}/scripts/caller.py create --ak "temporary_ak" --sk "temporary_sk" --security-token "your_security_token" --region "cn-north-4" --name "test_script" --type SHELL --content "echo hello" --description "Test script"
```

3. **Interactive Input** (Testing):
```bash
python {baseDir}/scripts/caller.py create
# Will prompt for AK/SK/region
```

**Authentication Parameter Description**:

| Parameter | Description | Required | Default | Example |
|-----------|-------------|----------|---------|---------|
| --ak | Huawei Cloud Access Key AK (can be temporary AK) | Yes* | Prompted | `--ak AXXX...` |
| --sk | Huawei Cloud Access Key SK (can be temporary SK) | Yes* | Prompted | `--sk SXXX...` |
| --security-token | Security token for temporary credentials (required when using temporary AK/SK) | No | Prompted | `--security-token XXXX...` |
| --region | COC Service Region | No | cn-north-4 | `--region cn-north-4` |

**Note**: Parameters marked with * can be provided via environment variables (`HW_ACCESS_KEY`, `HW_SECRET_KEY`, `HW_SECURITY_TOKEN`, `HW_REGION`). If environment variables are set, they take priority over command line parameters.

**Authentication Priority**:
1. First check environment variables: `HW_ACCESS_KEY`, `HW_SECRET_KEY`, `HW_SECURITY_TOKEN`, `HW_REGION`
2. If all required environment variables are set, use them directly
3. If environment variables are not set, use command line parameters
4. If neither is provided, prompt for interactive input

**Security Rules**:
- **No Hardcoded Credentials**: Never embed AK/SK directly in code or configuration files
- **Principle of Least Privilege**: Grant only the minimum permissions required
- **Regular Key Rotation**: Rotate AK/SK every 90 days
- **Enable Key Rotation Alerts**: Set up expiration reminders in Huawei Cloud Console

### IAM Permissions List

This skill requires the following IAM permissions. For detailed information, refer to [IAM Policies Documentation](references/iam-policies.md):

| Permission Category | Permission Name | Description |
|---------------------|-----------------|-------------|
| Script Management | `coc:script:create` | Create script |
| Script Management | `coc:script:list` | List scripts |
| Script Management | `coc:script:get` | Get script details |
| Script Management | `coc:script:update` | Update script |
| Script Management | `coc:script:delete` | Delete script |
| Execution Management | `coc:execution:create` | Create execution task |
| Execution Management | `coc:execution:list` | List execution tasks |
| Execution Management | `coc:execution:get` | Get execution details |
| Instance Management | `coc:instance:list` | List target instances |

### Permission Failure Handling Flow

**Insufficient Permission Error Handling**:

1. **Error Identification**:
```bash
# Typical error message
error: AccessDenied
message: You do not have permission to perform this action.
```

2. **Troubleshooting Steps**:
   - Verify AK/SK configuration
   - Confirm user has required COC permissions
   - Validate region configuration
   - Check if IAM policy is active

3. **Resolution**:
   - Contact administrator for required permissions
   - Confirm IAM policy is properly attached to user/role
   - Wait for policy to take effect (typically 5-10 minutes)

4. **Verification**:
```bash
# Re-execute to verify permissions
python {baseDir}/scripts/caller.py list
```

## Core Commands

### Script Management Commands

**Create Script**:
```bash
# Using permanent AK/SK
python {baseDir}/scripts/caller.py create --ak "your_ak" --sk "your_sk" --name "backup_script" --type SHELL --content "echo 'Backup completed'" --description "Data backup script"

# Using temporary AK/SK with security-token
python {baseDir}/scripts/caller.py create --ak "temporary_ak" --sk "temporary_sk" --security-token "your_security_token" --name "backup_script" --type SHELL --content "echo 'Backup completed'" --description "Data backup script"
```

**View Script Details**:
```bash
# Using permanent AK/SK
python {baseDir}/scripts/caller.py show --ak "your_ak" --sk "your_sk" --script-uuid "SC202xxxxxxxx13701c4a8a62"

# Using temporary AK/SK with security-token
python {baseDir}/scripts/caller.py show --ak "temporary_ak" --sk "temporary_sk" --security-token "your_security_token" --script-uuid "SC202xxxxxxxx13701c4a8a62"
```

**List Scripts**:
```bash
# Using permanent AK/SK
python {baseDir}/scripts/caller.py list --ak "your_ak" --sk "your_sk" --page 1 --size 10

# Using temporary AK/SK with security-token
python {baseDir}/scripts/caller.py list --ak "temporary_ak" --sk "temporary_sk" --security-token "your_security_token" --page 1 --size 10
```

### Script Execution Commands

**Execute Script**:
```bash
# Using permanent AK/SK
python {baseDir}/scripts/caller.py execute --ak "your_ak" --sk "your_sk" --script-uuid "SC202xxxxxxxx13701c4a8a62" --execute-user root --timeout 300

# Using temporary AK/SK with security-token
python {baseDir}/scripts/caller.py execute --ak "temporary_ak" --sk "temporary_sk" --security-token "your_security_token" --script-uuid "SC202xxxxxxxx13701c4a8a62" --execute-user root --timeout 300
```

**Interactive Execution**: `python {baseDir}/scripts/caller.py execute --ak "your_ak" --sk "your_sk"`

**Query Execution Result**:
```bash
# Using permanent AK/SK
python {baseDir}/scripts/caller.py query --ak "your_ak" --sk "your_sk" --execute-uuid "SCT202xxxxxxxx01af694bf"

# Using temporary AK/SK with security-token
python {baseDir}/scripts/caller.py query --ak "temporary_ak" --sk "temporary_sk" --security-token "your_security_token" --execute-uuid "SCT202xxxxxxxx01af694bf"
```

## Parameter Reference

### Global Parameters (All Commands)

| Parameter | Description | Required | Default | Example |
|-----------|-------------|----------|---------|---------|
| --ak | Huawei Cloud Access Key AK (can be temporary AK) | Yes* | Prompted | `--ak AXXX...` |
| --sk | Huawei Cloud Access Key SK (can be temporary SK) | Yes* | Prompted | `--sk SXXX...` |
| --security-token | Security token for temporary credentials (required when using temporary AK/SK) | No | Prompted | `--security-token XXXX...` |
| --region | COC Service Region | No | cn-north-4 | `--region cn-north-4` |

**Note**: Parameters marked with * can be provided via environment variables:
- `HW_ACCESS_KEY` - Huawei Cloud Access Key
- `HW_SECRET_KEY` - Huawei Cloud Secret Key
- `HW_SECURITY_TOKEN` - Temporary security token (optional)
- `HW_REGION` - COC Service Region

If environment variables are set, they take priority over command line parameters.

### create Command Parameters

| Parameter | Description | Required | Default |
|-----------|-------------|----------|---------|
| --name | Script name | Yes | - |
| --type | Script type (SHELL/PYTHON/BAT) | Yes | - |
| --content | Script content | Yes | - |
| --description | Script description | Yes | - |
| --risk-level | Risk level (LOW/MEDIUM/HIGH) | No | LOW |
| --version | Script version | No | 1.0.0 |

### execute Command Parameters

| Parameter | Description | Required | Default |
|-----------|-------------|----------|---------|
| --script-uuid | Script UUID | No | Most recent script |
| --execute-user | Execute user | No | root |
| --timeout | Timeout in seconds (5-1800) | No | 300 |
| --success-rate | Success rate (0.01-100) | No | 1 |
| --rotation-strategy | Rotation strategy (CONTINUE/PAUSE) | No | CONTINUE |

### show Command Parameters

| Parameter | Description | Required | Default |
|-----------|-------------|----------|---------|
| --script-uuid | Script UUID | Yes | - |

### list Command Parameters

| Parameter | Description | Required | Default |
|-----------|-------------|----------|---------|
| --page | Page number | No | 1 |
| --size | Page size | No | 10 |

### query Command Parameters

| Parameter | Description | Required | Default |
|-----------|-------------|----------|---------|
| --execute-uuid | Execution task UUID | Yes | - |

### SDK Installation

Before creating or executing scripts for the first time, ensure the Huawei Cloud COC SDK dependencies are installed. Run from the skill directory (`skills/coc`):

```bash
pip install -r {baseDir}/requirements.txt
```

**Installation Notes**:
- Installation may take a few minutes, please be patient
- After successful installation, you can call the Python code in the `scripts` directory for script creation and execution
- Use the following mirrors to install the SDK (second pip mirror, preferred):
  ```bash
  pip install -r {baseDir}/requirements.txt -i https://pypi.org/project/huaweicloudsdkcoc/
  ```
  or
  ```bash
  pip install -r {baseDir}/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
  ```

**Installation Verification**:
```bash
python -c "from huaweicloudsdkcoc.v1 import CocClient; print('SDK installed successfully!')"
```

## Workflow

### Basic Workflow

1. **Create a script** (using environment variables):
```bash
# Set environment variables first
export HW_ACCESS_KEY="your_ak"
export HW_SECRET_KEY="your_sk"
export HW_SECURITY_TOKEN="your_token"  # Optional

# Execute command (will automatically use environment variables)
python {baseDir}/scripts/caller.py create --name "test_script" --type SHELL --content "echo hello" --description "Test script"
```

Or using command line parameters:
```bash
python {baseDir}/scripts/caller.py create --ak "your_ak" --sk "your_sk" --name "test_script" --type SHELL --content "echo hello" --description "Test script"
```

2. **Execute a script**:
```bash
python {baseDir}/scripts/caller.py execute --ak "your_ak" --sk "your_sk" --script-uuid "SC202xxxxxxxx13701c4a8a62" --execute-user root --timeout 300 --success-rate 100
```

> **Tip**: Refer to the "Parameter Reference" section for complete parameter documentation.

### Interactive Mode

When executing scripts, the following information will be requested interactively (L-instance only):

**Required Parameters**:
- L-instance resource ID (resource_id)
- L-instance region (region_id)

**Optional Parameters** (press Enter to use default values):
- Script UUID (default uses the most recently created script)
- Execute user (default root)
- Timeout (default 300 seconds)
- Success rate (default 1)
- Rotation strategy (default CONTINUE)

## Output Format

### List Scripts Output

```
Found 25 scripts (Page 1, 10 per page):
--------------------------------------------------------------------------------
No.    Script UUID                    Name                 Type        Risk Level
--------------------------------------------------------------------------------
1       SC202xxxxxxxx13701c4a8a62     backup_script        SHELL       LOW
2       SC202xxxxxxxx10302201d5b9e78     deploy_script        SHELL       HIGH
3       SC202xxxxxxxx13701c4a8a62     monitor_script       PYTHON      MEDIUM
--------------------------------------------------------------------------------
```

### JSON Output Format

**Create Script Success Response**:
```json
{
  "ok": true,
  "text": "Script created successfully: SC202xxxxxxxx13701c4a8a62",
  "result": {
    "data": "SC202xxxxxxxx13701c4a8a62"
  },
  "error": null
}
```

**Execute Script Success Response**:
```json
{
  "ok": true,
  "text": "Script execution started: SCT202xxxxxxxx01af694bf",
  "result": {
    "data": "SCT202xxxxxxxx01af694bf"
  },
  "error": null
}
```

**Query Execution Result Response**:
```json
{
  "data": {
    "batch_index": 1,
    "total_instances": 1,
    "execute_instances": [
      {
        "id": 40304358,
        "cmd_uuid": "2exxxxxxxxxxxxxx6b5",
        "job_sign": null,
        "target_instance": {
          "resource_id": "6axxxxxxxxxxxxxxx9e",
          "agent_sn": "e5xxxxxxxxxxxxxxxxxx77",
          "agent_status": null,
          "agent_version": "1.1.8",
          "region_id": "cn-north-4",
          "project_id": null,
          "properties": {
            "host_name": "dify-test-001",
            "fixed_ip": null,
            "floating_ip": null,
            "region_id": "cn-north-4",
            "zone_id": null,
            "application": null,
            "group": null,
            "project_id": null
          },
          "custom_attributes": null,
          "provider": "hcss",
          "type": "l-instance"
        },
        "gmt_created": 1779934038727,
        "gmt_finished": 1779934107670,
        "execute_costs": 68943,
        "status": "ABNORMAL",
        "message": "Reading package lists...\nWARNING: apt does not have a stable CLI interface. Use with caution in scripts.\n\n\nBuilding dependency tree...\nReading state information...\nexpect is already the newest version (5.45.4-2build1).\n\n[SYSTEM INFO] script job execute timeout."
      }
    ]
  }
}
```

**Status Description**:
- `FINISHED` - Execution successful
- `ABNORMAL` - Execution failed
- `PROCESSING`/`READY` - In progress

## Validation Methods

### 1. SDK Installation Verification
```bash
python -c "from huaweicloudsdkcoc.v1 import CocClient; print('SDK installed successfully!')"
```

### 2. Create Script Verification
```bash
python {baseDir}/scripts/caller.py create --ak "your_ak" --sk "your_sk" --name "test_script" --type SHELL --content "echo hello" --description "Test script" --non-interactive
# Expected output: Script UUID returned
```

### 3. Execute Script Verification
```bash
python {baseDir}/scripts/caller.py execute --ak "your_ak" --sk "your_sk" --script-uuid "SC202xxxxxxxx13701c4a8a62" --execute-user root --timeout 300 --non-interactive
# Expected output: Execution task ID returned
```

### 4. Smoke Test
```bash
python {baseDir}/scripts/smoke_test.py
# This will test the configuration and optional API connectivity
```

## Notes

### General Notes
- **Script execution required parameters** - Need to provide L-instance resource_id and region_id
- **Script UUID auto-retrieval** - If not specified, will automatically use the most recently created script
- **Script type must match** - SHELL/PYTHON/BAT
- **Risk level must be set correctly** - LOW/MEDIUM/HIGH
- **Execution results need polling** - Execute API returns task ID, need to query execution status separately

## Best Practices
### Script Management Best Practices

1. **Script Reusability**: Create generic scripts with configurable parameters for maximum reusability
2. **Error Handling**: Always include error handling and logging in your scripts
3. **Idempotency**: Design scripts to be idempotent (can be safely run multiple times)
4. **Script Versioning**: Maintain version control for important scripts
5. **Resource Tagging**: Use consistent naming conventions and tags for scripts

### Execution Best Practices

1. **Test First**: Always test scripts on a single L-instance before batch execution
2. **Risk Assessment**: Set appropriate risk levels for scripts (LOW/MEDIUM/HIGH)
3. **Scheduling**: Use scheduled execution for periodic tasks
4. **Monitoring**: Monitor execution results and set up alerts for failures

### Region Concepts

COC involves two different region concepts:

**1. COC Service Region** (API endpoint region):
- cn-north-4 (China North-Beijing-4, default)
- ap-southeast-3 (APAC-Singapore)
- eu-west-101 (Europe-Frankfurt)

**2. Target Instance Region** (where the L-instance is located):
- Can be any Huawei Cloud global region
- Interactive input supports both region ID and region name

> **Important**: COC service region and target instance region can be different.

### Error Handling

**Authentication Failed (403)**:
```
error: Authentication failed
```
- AK/SK is invalid, reconfigure with correct credentials

**API Quota Exceeded (429)**:
```
error: API quota exceeded
```
- API quota exhausted, wait or upgrade

**Parameter Error (400)**:
```
error: Invalid parameter
```
- Check if request parameters are correct

### Security Notes

- **AK/SK Security**: AK/SK are important credentials for accessing Huawei Cloud APIs. Please keep them safe and do not share them with others.
- **Credential Obtaining**: Log in to Huawei Cloud Management Console → My Credentials → Access Keys → New Access Key

## Reference Documentation

- [IAM Policy Configuration](references/iam-policies.md)
- [Project Dependencies Configuration](scripts/pyproject.toml)
