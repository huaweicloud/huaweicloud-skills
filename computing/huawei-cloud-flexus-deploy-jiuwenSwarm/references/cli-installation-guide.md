# CLI Installation Guide

## Environment Requirements

| Component | Minimum Version | Description |
|-----------|-----------------|-------------|
| Python | 3.10+ | Script runtime environment |
| pip | 21.0+ | Python package manager |
| Network | - | Access to Huawei Cloud services |

## Installation Steps

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Required packages:

| Package | Version | Purpose |
|---------|---------|---------|
| huaweicloudsdkcore | >=3.1.0 | Huawei Cloud SDK core library |
| huaweicloudsdkcoc | >=3.1.0 | COC Operations Center API |
| huaweicloudsdkrms | >=3.1.0 | Resource Management API |
| requests | >=2.31.0 | HTTP request library |
| pyyaml | >=6.0 | YAML configuration parser |

### 2. Configure Environment Variables

**Windows (PowerShell)**

```powershell
$env:HUAWEICLOUD_SDK_AK="your_access_key"
$env:HUAWEICLOUD_SDK_SK="your_secret_key"
$env:HUAWEICLOUD_REGION="cn-north-4"
```

**Windows (CMD)**

```cmd
set HUAWEICLOUD_SDK_AK=your_access_key
set HUAWEICLOUD_SDK_SK=your_secret_key
set HUAWEICLOUD_REGION=cn-north-4
```

**Linux / macOS**

```bash
export HUAWEICLOUD_SDK_AK="your_access_key"
export HUAWEICLOUD_SDK_SK="your_secret_key"
export HUAWEICLOUD_REGION="cn-north-4"
```

### 3. Verify Installation

```bash
python scripts/phase1_prepare_env.py
```

Sample successful output:

```
============================================================
  Phase 1: Environment Preparation
============================================================
[OK] AK: xxxx....xxxx
[OK] SK: xxxx....xxxx
[OK] Region: cn-north-4
[INFO] Checking dependency modules...
[OK] requests
[OK] huaweicloudsdkcore
[OK] huaweicloudsdkcoc
[OK] huaweicloudsdkrms
```

## Quick Start

### Complete Deployment Flow

```bash
# Phase 1: Environment Preparation
python scripts/phase1_prepare_env.py

# Phase 2: Create Instance (requires customer confirmation)
python scripts/phase2_create_instance.py --name jiuwenswarm --flavor medium

# Phase 3: Install Dependencies (via COC remote execution)
python scripts/phase3_install_deps.py --instance-id <instance_id>

# Phase 4: Deploy Service (via COC remote execution)
python scripts/phase4_deploy_service.py --instance-id <instance_id>

# Phase 5: Verify Deployment
python scripts/phase5_verify_deployment.py --instance-id <instance_id>

# Phase 6: Configure Model
python scripts/phase6_config_model.py --instance-id <instance_id>

# Phase 7: Configure Message Channels
python scripts/phase7_config_channel.py --instance-id <instance_id> --channel xiaoyi
```

### COC Task Status Query

```bash
# Query task status by UUID
python scripts/phase8_query_coc_status.py --uuid <execute_uuid>

# Detailed output
python scripts/phase8_query_coc_status.py --uuid <execute_uuid> --verbose

# Wait for task completion
python scripts/phase8_query_coc_status.py --uuid <execute_uuid> --wait

# Load UUID from JSON file
python scripts/phase8_query_coc_status.py --from-file new_instance_info.json
```

## Script Description

| Script | Function |
|--------|----------|
| phase1_prepare_env.py | Validate credentials and dependencies |
| phase2_create_instance.py | Create Flexus L instance |
| phase3_install_deps.py | Install base dependencies via COC |
| phase4_deploy_service.py | Deploy JiuwenSwarm via COC |
| phase5_verify_deployment.py | Verify deployment result |
| phase6_config_model.py | Configure model parameters |
| phase7_config_channel.py | Configure message channels |
| phase8_query_coc_status.py | Query COC task status |

## FAQs

### Q: "huaweicloudsdkcore module not installed"

```bash
pip install huaweicloudsdkcore huaweicloudsdkcoc huaweicloudsdkrms
```

### Q: "Please set environment variable HUAWEICLOUD_SDK_AK"

Ensure environment variables are set before running scripts. Verify with:

```bash
# Windows
echo %HUAWEICLOUD_SDK_AK%

# Linux/Mac
echo $HUAWEICLOUD_SDK_AK
```

### Q: Credential validation failed

1. Verify AK/SK are correct
2. Verify credentials have appropriate permissions
3. Verify REGION configuration is correct

## Get Help

For detailed parameter information, use `--help`:

```bash
python scripts/phase2_create_instance.py --help
```
