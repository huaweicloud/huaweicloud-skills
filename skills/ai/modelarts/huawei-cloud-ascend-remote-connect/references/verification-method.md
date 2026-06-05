# Verification Method

## Overview

This document describes how to verify the Huawei Cloud Ascend Remote Connection skill is working correctly.

## Prerequisites

1. Python 3.8+ installed
2. paramiko library installed
3. Target Ascend server with SSH enabled

## Verification Steps

### Step 1: Install Dependencies

```bash
pip3 install --user paramiko cryptography
```

### Step 2: Basic Connection Test

```bash
# Test with command line arguments
python3 scripts/main.py --host <ascend-server-ip> --port 22 --user root --password <password> --command "echo 'Connection successful'"
```

**Expected Output:**
```
Connection successful
```

### Step 3: NPU Status Check

```bash
python3 scripts/main.py --host <ascend-server-ip> --user root --password <password> --command "npu-smi info"
```

**Expected Output:**
- NPU device information
- Device status (Normal)
- Memory usage
- Temperature

### Step 4: Interactive Mode Test

```bash
python3 scripts/main.py
```

Then enter:
```
SSH connect to <ascend-server-ip> port 22 as root with password <password>
```

**Expected:** Connection established successfully

### Step 5: System Command Test

After establishing connection:
```
Check CPU and memory
```

**Expected Output:**
- CPU information
- Memory usage (free -h)

### Step 6: Sensitive Operation Confirmation Test

```
Delete /tmp/test.txt
```

**Expected Output:**
```
⚠️⚠️ High-risk operation: Will delete /tmp/test.txt

Please reply "Confirm" or "Cancel"
```

### Step 7: Connection Pool Test

```python
# Create test script
cat > /tmp/test_pool.py << 'EOF'
from scripts.ssh_client import get_pool, ConnectionInfo

pool = get_pool()
conn_info = ConnectionInfo(host='<host>', port=22, username='root', password='<password>')

# Test connection
result = pool.execute(conn_info, 'npu-smi info')
print(f"Success: {not result.error}")
print(f"Output: {result.stdout[:500]}")

# Check pool status
status = pool.get_pool_status()
print(f"Connections: {status['total_connections']}")
print(f"Max connections: {status['max_connections']}")

pool.close_all()
EOF

python3 /tmp/test_pool.py
```

## Acceptance Criteria

### Must Pass

1. ✅ Connection establishment via command line
2. ✅ Connection establishment via natural language
3. ✅ NPU status monitoring (npu-smi)
4. ✅ Basic system commands execution
5. ✅ Sensitive operation confirmation
6. ✅ Connection pool management
7. ✅ Multi-machine connection support

### Security Checks

1. ✅ Password not printed in logs
2. ✅ High-risk commands blocked
3. ✅ Sensitive operations require confirmation
4. ✅ Password only stored in memory

## Automated Testing

```bash
# Run basic verification
python3 -c "
from scripts.main import run_one_shot
result = run_one_shot('<host>', 22, 'root', '<password>', 'npu-smi info')
assert result == 0, 'NPU check failed'
print('All tests passed!')
"
```

## Troubleshooting Failed Tests

| Test | Failure Reason | Fix |
|------|---------------|-----|
| Connection | SSH port not open | Check firewall, start sshd |
| NPU Check | npu-smi not found | Install NPU driver |
| Permission | No sudo access | Grant sudo privileges |