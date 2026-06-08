# Huawei Cloud ECS Monitoring Troubleshooting Guide

## Overview

This guide provides troubleshooting steps for common issues encountered when using the Huawei Cloud ECS monitoring skill. Follow these steps to diagnose and resolve problems.

## Common Issues and Solutions

### 1. Authentication and Authorization Issues

#### Issue: "Invalid credentials" or "Access denied"

```bash
# Symptom: hcloud commands fail with authentication errors
hcloud ECS NovaListServers --cli-region=<region-id>
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
# See references/iam-policies.md for the complete list of required permissions
```

#### Issue: "Insufficient permissions"

```bash
# Symptom: Specific operations fail with permission errors
hcloud CES ListMetrics --namespace=SYS.ECS --cli-region=<region-id>
# Error: User does not have permission to perform this operation
```

**Solution:**

```bash
# Step 1: Check required permissions
# Refer to references/iam-policies.md for required permissions

# Step 2: Contact administrator to add missing permissions
# See references/iam-policies.md for the complete list of required permissions

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
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-amd64.tar.gz"
tar -zxvf huaweicloud-cli-linux-amd64.tar.gz
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
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-amd64.tar.gz"
tar -zxvf huaweicloud-cli-linux-amd64.tar.gz
sudo mv hcloud /usr/local/bin/

# Verify update
hcloud --version
```

For Windows and other platforms, see the complete installation guide.

#### Step 2: Verify update

```bash
hcloud --version
# Should show latest version
```

### 3. Instance Not Found Issues

#### Issue: "Instance not found"

```bash
# Symptom: Cannot find specified instance
hcloud ECS NovaShowServer --server_id=<invalid-uuid> --cli-region=<region-id>
# Error: Instance not found
```

**Solution:**

```bash
# Step 1: List all instances to verify ID
hcloud ECS NovaListServers --cli-region=<region-id>

# Step 2: Check region
# Ensure you're using the correct region

# Step 3: Verify instance status
hcloud ECS NovaShowServer --server_id=<instance-uuid> --cli-region=<region-id>
# Check if instance exists and is active

# Step 4: Check project/account
# Ensure you're in the correct project/account
hcloud configure list
# Check project_id configuration
```

### 4. No Metric Data Issues

#### Issue: "No metric data available"

```bash
# Symptom: Metric queries return empty results
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-uuid>" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=<region-id>
# Returns empty datapoints array
```

**Solution:**

```bash
# Step 1: Check if instance is running
# Instance must be in ACTIVE state for metrics collection

# Step 2: Check if CES agent is installed (for AGT.ECS metrics)
# For Linux instances:
# SSH to instance and check:
# systemctl status telescoped
# or
# ps aux | grep telescoped

# Step 3: Check available metrics
hcloud CES ListMetrics \
  --namespace=SYS.ECS \
  --dim.0="instance_id,<instance-uuid>" \
  --cli-region=<region-id>
# Should list available metrics for the instance

# Step 4: Verify time range
# Ensure time range is valid and instance was running during that time
echo "Time range: $(date -d '1 hour ago' +%s)000 to $(date +%s)000"

# Step 5: Check metric name spelling
# Common SYS.ECS metric names:
# - cpu_util (NOT cpu_usage - that is AGT.ECS)
# - mem_util (NOT mem_usage)
# - disk_util_inband (NOT disk_used_percent)
# - network_incoming_bytes_rate_inband (NOT network_incoming_bytes_rate)

# Step 6: Check namespace
# SYS.ECS: Base monitoring (no agent required, 5-min period)
# AGT.ECS: OS monitoring (agent required, 1-min period)

# Step 7: Try AGT.ECS fallback
# If SYS.ECS metric returns no data, try the AGT.ECS equivalent:
# cpu_util (SYS.ECS) → cpu_usage (AGT.ECS)
# mem_util (SYS.ECS) → mem_usedPercent (AGT.ECS)
# disk_util_inband (SYS.ECS) → disk_usedPercent (AGT.ECS)
hcloud CES BatchListMetricData \
  --metrics.1.namespace="AGT.ECS" \
  --metrics.1.metric_name="cpu_usage" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-uuid>" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=60 \
  --filter="average" \
  --cli-region=<region-id>
```

#### Issue: "Metric not found"

```bash
# Symptom: Specific metric not available
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="non_existent_metric" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-uuid>" \
  --cli-region=<region-id>
# Error: Metric not found
```

**Solution:**

```bash
# Step 1: List all available metrics
hcloud CES ListMetrics \
  --namespace=SYS.ECS \
  --dim.0="instance_id,<instance-uuid>" \
  --cli-region=<region-id>

# Step 2: Use correct metric name
# Common SYS.ECS metrics (base monitoring, no agent):
# - cpu_util
# - mem_util
# - disk_util_inband
# - disk_read_bytes_rate
# - disk_write_bytes_rate
# - network_incoming_bytes_rate_inband
# - network_outgoing_bytes_rate_inband

# Common AGT.ECS metrics (OS monitoring, agent required):
# - cpu_usage
# - mem_usedPercent
# - disk_usedPercent
# - load_average1
# - net_tcp_total

# Step 3: Check namespace
# If querying AGT.ECS metrics, ensure:
# - Namespace is set to "AGT.ECS"
# - Telescope agent is installed on the instance
# - Period is at least 60 (1 minute)
```

### 5. Time Range Issues

#### Issue: "Invalid time range" or "Time range too large"

```bash
# Symptom: Time range errors
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-uuid>" \
  --from=1234567890 \
  --to=$(date +%s)000 \
  --period=300 \
  --cli-region=<region-id>
# Error: Time range too large or invalid
```

**Solution:**

```bash
# Step 1: Use correct time format
# See references/related-commands.md (Time Format Specifications section) for
# detailed format requirements, period enumeration, and common time range examples

# Step 2: Reduce time range
# Maximum data points per query is 1440
# Calculate: (end_time - start_time) / period <= 1440

# Step 3: Increase period
# Use larger period for longer time ranges
--period=300   # 5 minutes
--period=3600  # 1 hour
--period=86400 # 1 day

# Step 4: Split into multiple queries
# For 30 days with 5-minute period:
# Query 1: Days 1-15
# Query 2: Days 16-30
```

### 6. Network and Connectivity Issues

#### Issue: "Network error" or "Timeout"

```bash
# Symptom: Connection failures or timeouts
hcloud ECS NovaListServers --cli-region=<region-id>
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
hcloud ECS NovaListServers --cli-region=<region-id> --timeout=60
# Default timeout is 30 seconds

# Step 4: Check DNS resolution
nslookup console.huaweicloud.com
# Should resolve to Huawei Cloud IP addresses

# Step 5: Try different region
hcloud ECS NovaListServers --cli-region=<other-region-id>
# Test if issue is region-specific
```

### 7. Data Format and Parsing Issues

#### Issue: "Invalid JSON response" or "Parsing error"

```bash
# Symptom: CLI returns malformed JSON
hcloud ECS NovaListServers --cli-region=<region-id> --output=json
# Error: Invalid JSON or parsing error
```

**Solution:**

```bash
# Step 1: Use text output for debugging
hcloud ECS NovaListServers --cli-region=<region-id> --output=text
# Check if command works with text output

# Step 2: Check for special characters
# Some instance names or metadata may contain special characters
# Use jq with raw output
hcloud ECS NovaListServers --cli-region=<region-id> --output=json | jq -r '.'

# Step 3: Update CLI version
# Older versions may have JSON parsing issues
hcloud --version
# Update to latest version if needed

# Step 4: Check for API changes
# Huawei Cloud APIs may change - check documentation
# https://support.huaweicloud.com/api-ecs/
```

#### Issue: "jq command not found"

```bash
# Symptom: JSON parsing fails due to missing jq
hcloud ECS NovaListServers --cli-region=<region-id> --output=json | jq '.servers[].name'
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
hcloud ECS NovaListServers --cli-region=<region-id> --output=json | grep -o '"name":"[^"]*"' | cut -d'"' -f4

# Step 3: Use Python for complex parsing
hcloud ECS NovaListServers --cli-region=<region-id> --output=json | python3 -c "import sys,json; data=json.load(sys.stdin); [print(s['name']) for s in data['servers']]"
```

### 8. Performance Issues

#### Issue: "Slow response" or "High latency"

```bash
# Symptom: Queries take too long
time hcloud CES BatchListMetricData ...  # Takes > 30 seconds
```

**Solution:**

```bash
# Step 1: Reduce time range
# Shorter time ranges are faster
--from=$(date -d '1 hour ago' +%s)000
# Instead of
--from=$(date -d '7 days ago' +%s)000

# Step 2: Increase period
# Larger periods return fewer data points
--period=3600  # 1 hour intervals
# Instead of
--period=300   # 5 minute intervals

# Step 3: Query fewer metrics per request
# Batch 5-6 metrics at a time instead of 10+

# Step 4: Use appropriate region endpoint
# Ensure you're using the closest region

# Step 5: Cache results
# Cache instance list and other static data
INSTANCE_CACHE="/tmp/instances_$(date +%Y%m%d%H).json"
if [ ! -f "$INSTANCE_CACHE" ]; then
  hcloud ECS NovaListServers --cli-region=<region-id> --output=json > "$INSTANCE_CACHE"
fi
```

### 9. Dimension and Filter Issues

#### Issue: "Invalid dimension" or "Dimension not found"

```bash
# Symptom: Dimension errors in metric queries
hcloud CES BatchListMetricData \
  --metrics.1.namespace="AGT.ECS" \
  --metrics.1.metric_name="disk_usedPercent" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-uuid>" \
  --cli-region=<region-id>
# Error: Dimension mount_point is required for disk metrics
```

**Solution:**

```bash
# Step 1: Check required dimensions for each metric
# AGT.ECS disk metrics require mount_point dimension
hcloud CES BatchListMetricData \
  --metrics.1.namespace="AGT.ECS" \
  --metrics.1.metric_name="disk_usedPercent" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-uuid>" \
  --metrics.1.dimensions.2.name="mount_point" \
  --metrics.1.dimensions.2.value="<mount-point-hash>" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=60 \
  --filter="average" \
  --cli-region=<region-id>

# Step 2: List available dimensions
hcloud CES ListMetrics \
  --namespace="AGT.ECS" \
  --dim.0="instance_id,<instance-uuid>" \
  --cli-region=<region-id>

# Step 3: Use correct dimension format
# See references/ces-metrics-reference.md (Metric Dimensions section) for
# dimension format details and mount_point hash value explanation
```

### 10. Agent-Related Issues (AGT.ECS Metrics)

#### Issue: "AGT.ECS metrics return no data"

```bash
# Symptom: AGT.ECS metric queries return empty results
# while SYS.ECS metrics work fine
```

**Solution:**

```bash
# Step 1: Verify the Telescope agent is installed
# SSH to the instance and check:
systemctl status telescoped   # Linux
# or check "telescoped" service in Services Manager (Windows)

# Step 2: If agent is not installed, install it
# Follow Huawei Cloud documentation for agent installation:
# https://support.huaweicloud.com/usermanual-ces/ces_01_0019.html

# Step 3: Verify agent is running
ps aux | grep telescoped

# Step 4: Check agent version (should be latest)
# Older agent versions may not support all metrics

# Step 5: Wait for data collection
# Agent metrics may take 1-2 minutes to appear after installation
```
