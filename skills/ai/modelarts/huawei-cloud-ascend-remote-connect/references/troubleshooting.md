# Troubleshooting Guide

## Overview

This document provides troubleshooting guidance for Huawei Cloud Ascend Remote Connection skill. It covers common connection issues, authentication problems, and command execution failures.

## Connection Issues

### Problem: Connection Failed

**Possible Causes:**
1. Target server IP address is incorrect
2. SSH port is not open (default 22)
3. Firewall blocking SSH access
4. SSH service not running on target server

**Solution:**
```bash
# Check if SSH port is accessible
telnet <host> <port>

# Check SSH service status on target server
systemctl status sshd

# Check firewall rules
iptables -L -n | grep 22
```

### Problem: Authentication Failed

**Possible Causes:**
1. Incorrect username or password
2. Password authentication disabled in SSH config
3. Key-based authentication required

**Solution:**
```bash
# Check SSH configuration on target server
grep -E "^(PasswordAuthentication|ChallengeResponseAuthentication)" /etc/ssh/sshd_config

# Enable password authentication if needed
sed -i 's/^PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
systemctl restart sshd
```

## Command Execution Issues

### Problem: Command Timeout

**Possible Causes:**
1. Command execution takes too long
2. Network latency
3. Target server unresponsive

**Solution:**
```bash
# Check network connectivity
ping <host>

# Try simpler commands first
python3 scripts/main.py --host <host> --command "echo test"
```

### Problem: Permission Denied

**Possible Causes:**
1. Insufficient permissions for the command
2. Need sudo privileges

**Solution:**
```bash
# Use sudo for privileged commands
python3 scripts/main.py --host <host> --command "sudo npu-smi info"
```

## NPU Monitoring Issues

### Problem: npu-smi command not found

**Possible Causes:**
1. NPU driver not installed
2. npu-smi not in PATH

**Solution:**
```bash
# Check if NPU driver is installed
ls /usr/local/Ascend/driver

# Add to PATH
export PATH=$PATH:/usr/local/Ascend/driver/bin
npu-smi info
```

## Security Issues

### Problem: High-risk command blocked

**Description:** The skill blocks dangerous commands for security.

**Solution:**
- For sensitive operations like `rm -rf`, confirm when prompted
- For blocked commands (fork bomb), use alternative approaches

## Logging

**Enable debug logging:**
```bash
python3 scripts/main.py --debug
```

**Check connection pool status:**
```python
from ssh_client import get_pool
pool = get_pool()
print(pool.get_pool_status())
```

## Common Error Codes

| Error Code | Description | Solution |
|------------|-------------|----------|
| connection_failed | Cannot connect to target | Check network, firewall, SSH service |
| authentication_failed | Wrong credentials | Verify username/password |
| timeout | Command execution timeout | Check network latency, simplify command |
| permission_denied | Insufficient permissions | Use sudo or check user privileges |
| rate_limit | Too many concurrent requests | Wait and retry |