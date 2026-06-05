# Verification Method

## Overview

This document describes how to verify the skill is correctly installed and configured.

## Verification Steps

### 1. Verify Python Environment

```bash
python3 --version
# Should output: Python 3.8.x or higher
```

### 2. Verify SDK Installation

```bash
python3 -c "from huaweicloudsdkcore.exceptions import exceptions; print('✅ SDK installed successfully')"
```

### 3. Verify AK/SK Configuration

```bash
env | grep CLOUD_SDK
# Should output:
# CLOUD_SDK_AK=xxx
# CLOUD_SDK_SK=xxx
```

### 4. Verify Connection

```bash
python3 {baseDir}/scripts/query_instances.py list
```

**Success Output:**
```
📋 Querying Flexus L instances...
✅ Query successful, credentials are valid
```

### 5. Verify Instance Query

```bash
python3 {baseDir}/scripts/query_instances.py list
```

**Success Output:**
```
📋 Querying Flexus L instances...
Instance ID     Name         Status    Region
xxx            xxx          Running   cn-north-4
```

## Common Issues

### Issue 1: SDK Import Failed

**Error:** `ModuleNotFoundError: No module named 'huaweicloudsdkcore'`

**Solution:**
```bash
pip3 install -e . --break-system-packages -i https://repo.huaweicloud.com/repository/pypi/simple
```

### Issue 2: Credentials Not Configured

**Error:** `❌ Credentials not detected`

**Solution:**
```bash
export CLOUD_SDK_AK="your_access_key"
export CLOUD_SDK_SK="your_secret_key"
```

### Issue 3: Insufficient Permissions

**Error:** `❌ Insufficient permissions`

**Solution:** Refer to [iam-policies.md](iam-policies.md) to configure permissions

### Issue 4: Region Not Found

**Error:** `❌ Region not found`

**Solution:** Use correct region code, e.g., `cn-north-4`
