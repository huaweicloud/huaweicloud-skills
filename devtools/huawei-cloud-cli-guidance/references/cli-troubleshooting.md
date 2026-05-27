# KooCLI Error Troubleshooting and FAQ

## Overview
This document provides troubleshooting methods and solutions for common Huawei Cloud KooCLI errors, helping Agents quickly diagnose and resolve issues.

## Error Categories and Solutions

### 1. Installation and Configuration Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `hcloud: command not found` | KooCLI not installed or not in PATH | `sudo mv hcloud /usr/local/bin/` |
| `Permission denied` | No execution permission | `chmod +x /usr/local/bin/hcloud` |
| `hcloud --version` no output | Known bug | Use `hcloud --help` |
| SSL/TLS certificate error | System CA certificates outdated | `apt update && apt install ca-certificates` |
| Connection timeout | Network restrictions/proxy | Check firewall/proxy settings |

### 2. Authentication Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `InvalidAccessKeyId` | AK does not exist or misspelled | Check AK value, reconfigure |
| `SignatureDoesNotMatch` | SK error | Check SK value, reconfigure |
| `TokenIsExpired` | Temporary token expired | Reacquire token |
| `NoPermission` | Insufficient IAM permissions | Contact administrator for authorization |
| `AccountRestricted` | Account restricted | Contact Huawei Cloud support |

**Check authentication status**:
```bash
hcloud configure list
```

**Reconfigure authentication**:
```bash
hcloud configure set
```

### 3. Parameter Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Unsupported service` | Service name misspelled | Ensure service name is **uppercase**: `ECS` not `ecs` |
| `Unsupported operation` | Operation name misspelled | Ensure PascalCase: `ListServersDetails` |
| `parameter is required` | Missing required parameter | View help: `hcloud <SERVICE> <Op> --help` |
| `cli-region is required` | Region not specified | Add `--cli-region=<region>` |
| `Invalid parameter` | Parameter value format error | Refer to parameter-format-en.md |
| `InvalidParameterValue` | Parameter value not in allowed range | Check enumeration values |

**View operation help**:
```bash
hcloud ECS CreateServers --help
```

### 4. Resource Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `404 Not Found` | Resource does not exist | Check ID and region |
| `409 Conflict` | Resource state conflict | Instance may be performing other operations |
| `QuotaExceeded` | Quota exceeded | Apply for quota increase or clean up resources |
| `ResourceNotFound` | Invalid resource ID | Confirm ID is correct, check region |
| `InstanceLocked` | Instance locked | Wait for current operation to complete |

### 5. Network Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused` | API endpoint unreachable | Check network/proxy |
| `Connection timeout` | Network timeout | Check firewall/increase timeout |
| `Too many requests` | Request frequency too high | Reduce request frequency |

## FAQ Common Questions

### Q1: Why doesn't hcloud --version work?
**A**: This is a known issue with KooCLI. Use `hcloud --help` to view version information.

### Q2: When do VPC operations need /v3 suffix?
**A**: Security group related operations need /v3 suffix (ListSecurityGroups/v3, ShowSecurityGroup/v3, etc.), VPC and subnet operations don't need it but can have it (ListVpcs/v3 is also valid). EIP operations also need /v3 suffix. ELB also supports /v3 suffix.

### Q3: Is EIP a sub-service of VPC?
**A**: No. EIP is an independent service, use `hcloud EIP ...` not `hcloud VPC ...`.

### Q4: What is the batch operation parameter format?
**A**: Use `--operation.resource_name.index.field=value` format:
```bash
# Start multiple instances
hcloud ECS NovaStartServers --os-start.servers.1.id=<id1> --os-start.servers.2.id=<id2>

# Delete multiple instances
hcloud ECS DeleteServers --servers.1.id=<id1> --servers.2.id=<id2>
```

### Q5: How to view all parameters for an operation?
**A**: Use `--help`:
```bash
hcloud ECS CreateServers --help
```

### Q6: How to switch regions?
**A**: Specify `--cli-region=<region>` for each command, or set default region:
```bash
hcloud configure set --cli-region=cn-north-4
```

### Q7: How to use multiple profiles?
**A**:
```bash
# Create new profile
hcloud configure set --cli-profile=prod

# Use specified profile
hcloud ECS ListServersDetails --cli-profile=prod --cli-region=cn-north-4
```

### Q8: Use KooCLI or obsutil for OBS object storage?
**A**: Recommended to use obsutil, more complete functionality and better performance.

### Q9: Does Ubuntu 22.04 instance allow root SSH by default?
**A**: Yes. Huawei Cloud Ubuntu 22.04 public images default to PermitRootLogin=yes, PasswordAuthentication=yes. Custom images may differ.

### Q10: Can instance types as7/ac7 still be used?
**A**: No. as7/ac7 series are deprecated, use ac8/as8 series (e.g., ac8.large.2).

### Q11: How to specify port range for security group rules?
**A**: Use multiport parameter to specify single port or port range:
```bash
# Single port
--security_group_rule.multiport=22

# Port range
--security_group_rule.multiport=8000-9000
```

**Note**: Earlier API versions may use port_range_min and port_range_max, but currently multiport is recommended.

### Q13: How to get image ID and flavor ID required for ECS creation?
**A**: Use the following commands to query available resources:

```bash
# Query available images
hcloud ECS ListImages/v2 --cli-region=cn-north-4 --cli-output=json

# Query available flavors
hcloud ECS ListFlavors/v2 --cli-region=cn-north-4 --cli-output=json

# Query available VPCs
hcloud VPC ListVpcs/v3 --cli-region=cn-north-4 --cli-output=json

# Query available subnets
hcloud VPC ListSubnets/v3 --cli-region=cn-north-4 --cli-output=json
```

### Q14: What is the CES monitoring timestamp format?
**A**: Unix timestamp (seconds) × 1000 (milliseconds):
```bash
# Last 1 hour
--from=$(date -d '1 hour ago' +%s)000 --to=$(date +%s)000
```

### Q13: How to get VNC remote console?
**A**:
```bash
hcloud ECS ShowServerRemoteConsole \
  --server_id=<id> \
  --remote_console.protocol=vnc \
  --remote_console.type=novnc \
  --cli-region=<region>
# Open the returned URL in browser
```

## Debugging Tips

### 1. View Detailed Logs
```bash
hcloud ECS ListServersDetails --cli-region=cn-north-4 --cli-debug=true
```

### 2. View API Requests
```bash
# Output raw HTTP request and response
hcloud ECS ShowServer --server_id=<id> --cli-region=cn-north-4 --cli-output=raw
```

### 3. JSON Output Processing
```bash
# Process JSON output with jq
hcloud ECS ListServersDetails --cli-region=cn-north-4 --cli-output json | jq '.servers[] | {id: .id, name: .name, status: .status}'

# Or process with Python
hcloud ECS ListServersDetails --cli-region=cn-north-4 --cli-output json | python3 -c "
import sys, json
data = json.load(sys.stdin)
for s in data.get('servers', []):
    print(f\"{s['id'][:12]}  {s['name']:20s}  {s['status']}\")
"
```

### 4. Retry Mechanism
```bash
# For intermittent errors, can retry
for i in 1 2 3; do
  result=$(hcloud ECS ShowServer --server_id=<id> --cli-region=cn-north-4 2>&1)
  if echo "$result" | grep -q "id"; then
    echo "$result"
    break
  fi
  echo "Retry $i..."
  sleep 2
done
```

### 5. Verify Command Format
```bash
# First check help to confirm parameters
hcloud <SERVICE> <OPERATION> --help

# Then execute command
hcloud <SERVICE> <OPERATION> --param1=value1 --param2=value2 --cli-region=cn-north-4 --cli-output=json
```

## Error Troubleshooting Process

### Step 1: Check Basic Configuration
```bash
# Check KooCLI version
hcloud --help

# Check authentication configuration
hcloud configure list

# Check network connection
ping cn-north-4.myhuaweicloud.com
```

### Step 2: Check Command Syntax
```bash
# View service list
hcloud help

# View specific service operations
hcloud <SERVICE> help

# View specific operation parameters
hcloud <SERVICE> <OPERATION> --help
```

### Step 3: Enable Debug Mode
```bash
# Enable detailed logs
hcloud <SERVICE> <OPERATION> --cli-debug=true --cli-region=cn-north-4

# View raw requests
hcloud <SERVICE> <OPERATION> --cli-output=raw --cli-region=cn-north-4
```

### Step 4: Check Permissions and Resources
```bash
# Check IAM permissions
hcloud IAM KeystoneListPermissions --cli-region=cn-north-4

# Check if resource exists
hcloud <SERVICE> Show<Resource> --id=<resource-id> --cli-region=cn-north-4
```

### Step 5: Contact Support
If the above steps cannot resolve the issue:
1. Collect error information and debug logs
2. Check Huawei Cloud service status page