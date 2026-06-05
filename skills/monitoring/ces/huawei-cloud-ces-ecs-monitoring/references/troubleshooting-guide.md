# Huawei Cloud ECS Monitoring Troubleshooting Guide

## Overview

This guide provides troubleshooting steps for common issues encountered when using the Huawei Cloud ECS monitoring skill. Follow these steps to diagnose and resolve problems.

## Common Issues and Solutions

### 1. Authentication and Authorization Issues

#### Issue: "Invalid credentials" or "Access denied"

```bash
# Symptom: hcloud commands fail with authentication errors
hcloud ECS ListServers --cli-region=cn-north-1
# Error: InvalidAccessKeyId: The Access Key ID is invalid
```

**Solution:**

```bash
# Step 1: Check current configuration
hcloud configure list

# Step 2: Verify credentials are valid
# If configuration is empty or incorrect:
hcloud configure init
# Follow prompts to enter:
# - Access Key ID
# - Secret Access Key  
# - Region
# - Output format (json recommended)

# Step 3: Test authentication
hcloud IAM ShowUser
# Should return user information without errors

# Step 4: Check IAM permissions
# Ensure the user has required permissions:
# - ecs:cloudServers:list
# - ces:metrics:list
# - ces:metricData:get
```

#### Issue: "Insufficient permissions"

```bash
# Symptom: Specific operations fail with permission errors
hcloud CES ListMetrics --namespace=SYS.ECS --cli-region=cn-north-1
# Error: User does not have permission to perform this operation
```

**Solution:**

```bash
# Step 1: Check required permissions
# Refer to references/iam-policies.md for required permissions

# Step 2: Contact administrator to add missing permissions
# Required permissions for basic monitoring:
# - ecs:cloudServers:list
# - ecs:cloudServers:get
# - ces:metrics:list
# - ces:metricData:get

# Step 3: Test with minimal permissions first
# Start with read-only permissions, then add as needed
```

### 2. CLI Installation and Configuration Issues

#### Issue: "Command not found: hcloud"

```bash
# Symptom: hcloud command is not available
hcloud --version
# bash: hcloud: command not found
```

**Solution:**

**Step 1: Install Huawei Cloud CLI**
Refer to the detailed installation guide: `references/cli-installation-guide.md`

Quick installation for Linux/macOS:

```bash
# Download and install
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-amd64.tar.gz
tar -xzf hcloudcli-linux-amd64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

For Windows and other platforms, see the complete installation guide.

#### Step 2: Verify installation

```bash
hcloud --version
# Should show version information (>= 3.2.0 recommended)
```

#### Step 3: Add to PATH if needed

- Linux/macOS: Ensure `/usr/local/bin` or installation directory is in PATH
- Windows: Add installation directory to system PATH environment variable

**Windows:** Ensure installation directory is in PATH

```

#### Issue: "Outdated CLI version"
```bash
# Symptom: Commands fail with version errors
hcloud --version
# Version: 1.0.0 (but newer features require 1.2.0+)
```

**Solution:**

**Step 1: Update Huawei Cloud CLI**
Refer to the installation guide for update instructions: `references/cli-installation-guide.md`

Quick update for Linux/macOS:

```bash
# Download latest version
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-amd64.tar.gz
tar -xzf hcloudcli-linux-amd64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/

# Verify update
hcloud --version
```

For Windows and other platforms, see the complete installation guide.

#### Step 2: Verify update

hcloud --version

Should show latest version

```

### 3. Instance Not Found Issues

#### Issue: "Instance not found"
```bash
# Symptom: Cannot find specified instance
hcloud ECS ShowServerDetails i-invalid-id --cli-region=cn-north-1
# Error: Instance not found
```

**Solution:**

```bash
# Step 1: List all instances to verify ID
hcloud ECS ListServers --cli-region=cn-north-1 --output=table

# Step 2: Check region
# Ensure you're using the correct region
hcloud ECS ListRegions
# List available regions

# Step 3: Verify instance status
hcloud ECS ShowServerDetails <correct-instance-id> --cli-region=<correct-region>
# Check if instance exists and is active

**Step 4:** Check project/account
**Ensure you're in the correct project/account**
hcloud configure list
# Check project_id configuration
```

### 4. No Metric Data Issues

#### Issue: "No metric data available"

```bash
# Symptom: Metric queries return empty results
hcloud CES ShowMetricData \
  --namespace=SYS.ECS \
  --metric_name=cpu_usage \
  --dim.0="instance_id,i-12345678" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --cli-region=cn-north-1
# Returns empty datapoints array
```

**Solution:**

```bash
# Step 1: Check if instance is running
INSTANCE_STATUS=$(hcloud ECS ShowServerDetails i-12345678 --cli-region=cn-north-1 --output=json | jq -r '.server.status')
echo "Instance status: $INSTANCE_STATUS"
# Should be "ACTIVE" for metrics collection

# Step 2: Check if CES agent is installed
# For Linux instances:
# SSH to instance and check:
# systemctl status telescoped
# or
# ps aux | grep telescoped

# Step 3: Check available metrics
hcloud CES ListMetrics \
  --namespace=SYS.ECS \
  --dim.0="instance_id,i-12345678" \
  --cli-region=cn-north-1
# Should list available metrics for the instance

# Step 4: Verify time range
# Ensure time range is valid and instance was running during that time
echo "Time range: $(date -d '1 hour ago' +%s)000 to $(date +%s)000"

# Step 5: Check metric name spelling
# Common metric names:
# - cpu_usage (not cpu_utilization)
# - mem_usage (not memory_usage)
# - disk_used_percent (not disk_usage)

# Step 6: Try different metric
hcloud CES ShowMetricData \
  --namespace=SYS.ECS \
  --metric_name=mem_usage \
  --dim.0="instance_id,i-12345678" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --cli-region=cn-north-1
```

#### Issue: "Metric not found"

```bash
# Symptom: Specific metric not available
hcloud CES ShowMetricData \
  --namespace=SYS.ECS \
  --metric_name=non_existent_metric \
  --dim.0="instance_id,i-12345678" \
  --cli-region=cn-north-1
# Error: Metric not found
```

**Solution:**

```bash
# Step 1: List all available metrics
hcloud CES ListMetrics \
  --namespace=SYS.ECS \
  --dim.0="instance_id,i-12345678" \
  --cli-region=cn-north-1 \
  --output=json | jq -r '.metrics[].metric_name' | sort

# Step 2: Use correct metric name
# Common ECS metrics:
# - cpu_usage
# - mem_usage
# - disk_read_bytes_rate
# - disk_write_bytes_rate
# - network_incoming_bytes_rate
# - network_outgoing_bytes_rate
# - disk_used_percent
# - load_average1

# Step 3: Check namespace
# ECS metrics are in "SYS.ECS" namespace
# Custom metrics may be in different namespaces
```

### 5. Time Range Issues

#### Issue: "Invalid time range" or "Time range too large"

```bash
# Symptom: Time range errors
hcloud CES ShowMetricData \
  --namespace=SYS.ECS \
  --metric_name=cpu_usage \
  --dim.0="instance_id,i-12345678" \
  --from=2023-01-01T00:00:00Z \
  --to=$(date +%s)000 \
  --period=60 \
  --cli-region=cn-north-1
# Error: Time range too large or invalid
```

**Solution:**

```bash
# Step 1: Reduce time range
# Maximum data points per query is 1440
# Calculate: (end_time - start_time) / period <= 1440

# Example: 30 days with 1-hour period = 720 data points (OK)
# Example: 7 days with 5-minute period = 2016 data points (Too many)

# Step 2: Increase period
# Use larger period for longer time ranges
--period=300   # 5 minutes
--period=3600  # 1 hour
--period=86400 # 1 day

# Step 3: Split into multiple queries
# For 30 days with 5-minute period:
# Query 1: Days 1-15
# Query 2: Days 16-30

# Step 4: Use valid time format
# ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
# Example: 2024-01-20T10:30:00Z
```

### 6. Network and Connectivity Issues

#### Issue: "Network error" or "Timeout"

```bash
# Symptom: Connection failures or timeouts
hcloud ECS ListServers --cli-region=cn-north-1
# Error: Network error or timeout
```

**Solution:**

```bash
# Step 1: Check network connectivity
ping console.huaweicloud.com
# Should respond without packet loss

# Step 2: Check proxy settings
echo $HTTP_PROXY
echo $HTTPS_PROXY
# If using proxy, ensure it's configured correctly

# Step 3: Increase timeout
hcloud ECS ListServers --cli-region=cn-north-1 --timeout=60
# Default timeout is 30 seconds

# Step 4: Check DNS resolution
nslookup console.huaweicloud.com
# Should resolve to Huawei Cloud IP addresses

# Step 5: Try different region
hcloud ECS ListServers --cli-region=ap-southeast-1
# Test if issue is region-specific
```

### 7. Data Format and Parsing Issues

#### Issue: "Invalid JSON response" or "Parsing error"

```bash
# Symptom: CLI returns malformed JSON
hcloud ECS ListServers --cli-region=cn-north-1 --output=json
# Error: Invalid JSON or parsing error
```

**Solution:**

```bash
# Step 1: Use text output for debugging
hcloud ECS ListServers --cli-region=cn-north-1 --output=text
# Check if command works with text output

# Step 2: Check for special characters
# Some instance names or metadata may contain special characters
# Use jq with raw output
hcloud ECS ListServers --cli-region=cn-north-1 --output=json | jq -r '.'

# Step 3: Update CLI version
# Older versions may have JSON parsing issues
hcloud --version
# Update to latest version if needed

# Step 4: Check for API changes
# Huawei Cloud APIs may change - check documentation
# https://support.huaweicloud.com/intl/en-us/api-ecs/
```

#### Issue: "jq command not found"

```bash
# Symptom: JSON parsing fails due to missing jq
hcloud ECS ListServers --cli-region=cn-north-1 --output=json | jq '.servers[].name'
# bash: jq: command not found
```

**Solution:**

```bash
# Step 1: Install jq
# Ubuntu/Debian:
sudo apt-get install jq

# CentOS/RHEL:
sudo yum install jq

# macOS:
brew install jq

# Windows:
# Download from https://stedolan.github.io/jq/download/

# Step 2: Use alternative parsing if jq not available
# Use grep/sed/awk for simple extraction
hcloud ECS ListServers --cli-region=cn-north-1 --output=json | grep -o '"name":"[^"]*"' | cut -d'"' -f4

# Step 3: Use Python for complex parsing
hcloud ECS ListServers --cli-region=cn-north-1 --output=json | python3 -c "import sys,json; data=json.load(sys.stdin); [print(s['name']) for s in data['servers']]"
```

### 8. Performance Issues

#### Issue: "Slow response" or "High latency"

```bash
# Symptom: Queries take too long
time hcloud CES ShowMetricData ...  # Takes > 30 seconds
```

**Solution:**

```bash
# Step 1: Reduce time range
# Shorter time ranges are faster
--from=$(date -d '1 hour ago\' +%s)000
# Instead of
--from=$(date -d '7 days ago\' +%s)000

# Step 2: Increase period
# Larger periods return fewer data points
--period=3600  # 1 hour intervals
# Instead of
--period=60    # 1 minute intervals

# Step 3: Query fewer metrics
# Query 2-3 metrics at a time instead of 10+
--metric_name=cpu_usage,mem_usage
# Instead of
--metric_name=cpu_usage,mem_usage,disk_read_bytes_rate,disk_write_bytes_rate,network_incoming_bytes_rate,network_outgoing_bytes_rate,load_average1,proc_rate,disk_used_percent,disk_inodes_used_percent

# Step 4: Use appropriate region endpoint
# Ensure you're using the closest region
hcloud configure set region <closest-region>

# Step 5: Cache results
# Cache instance list and other static data
INSTANCE_CACHE="/tmp/instances_$(date +%Y%m%d%H).json"
if [ ! -f "$INSTANCE_CACHE" ]; then
  hcloud ECS ListServers --cli-region=cn-north-1 --output=json > "$INSTANCE_CACHE"
fi
```

### 9. Dimension and Filter Issues

#### Issue: "Invalid dimension" or "Dimension not found"

```bash
# Symptom: Dimension errors in metric queries
hcloud CES ShowMetricData \
  --namespace=SYS.ECS \
  --metric_name=disk_used_percent \
  --dim.0="instance_id,i-12345678" \
  --cli-region=cn-north-1
# Error: Dimension mount_point is required for disk metrics
```

**Solution:**

```bash
# Step 1: Check required dimensions for each metric
# Disk metrics require mount_point or device dimension
hcloud CES ShowMetricData \
  --namespace=SYS.ECS \
  --metric_name=disk_used_percent \
  --dim.0="instance_id,i-12345678,mount_point,/" \
  --cli-region=cn-north-1

# Network metrics may require nic dimension
hcloud CES ShowMetricData \
  --namespace=SYS.ECS \
  --metric_name=network_incoming_bytes_rate \
  --dim.0="instance_id,i-12345678,nic,eth0" \
  --cli-region=cn-north-1

# Step 2: List available dimensions
hcloud CES ListMetrics \
  --namespace=SYS.ECS \
  --dim.0="instance_id,i-12345678" \
  --cli-region=cn-north-1 \
  --output=json | jq -r '.metrics[] | .metric_name + ": " + (.dimensions | map(.name + "=" + .value) | join(", "))'

# Step 3: Use correct dimension format
# Format: "key1,value1,key2,value2"
--dim.0="instance_id,i-12345678,mount_point,/",device,vda
```