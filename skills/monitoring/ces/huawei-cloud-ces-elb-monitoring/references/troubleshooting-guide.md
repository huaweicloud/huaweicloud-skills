# ELB Monitoring Troubleshooting Guide

## Overview

This guide provides troubleshooting procedures for common issues encountered when using the Huawei Cloud ELB Monitoring skill.

## Quick Diagnosis Flowchart

```
Issue Reported
    ↓
CLI Command Fails? → Yes → Check CLI Installation & Configuration
    ↓ No
Permission Error? → Yes → Check IAM Policies
    ↓ No
No Data Returned? → Yes → Check ELB Status & Time Range
    ↓ No
Wrong Data? → Yes → Check Parameters & Dimensions
    ↓ No
Performance Issue? → Yes → Check Network & Rate Limits
```

## Category 1: CLI and Configuration Issues

### 1.1 CLI Not Installed

**Symptoms:**

- `hcloud: command not found`
- `bash: hcloud: No such file or directory`

**Diagnosis:**

```bash
which hcloud
# Expected: /usr/local/bin/hcloud or similar path
```

**Solution:**

```bash
# Install Huawei Cloud CLI
# See references/cli-installation-guide.md for detailed instructions

# One-click installation (recommended, all platforms)
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh

# Or install manually on Linux (AMD 64-bit)
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-amd64.tar.gz"
tar -zxvf huaweicloud-cli-linux-amd64.tar.gz
sudo mv hcloud /usr/local/bin/

# Or install manually on macOS (Intel)
curl -LO "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-mac-amd64.tar.gz"
tar -zxvf huaweicloud-cli-mac-amd64.tar.gz
sudo mv hcloud /usr/local/bin/

# Verify
hcloud version
```

### 1.2 CLI Version Outdated

**Symptoms:**

- Commands fail with `unknown command`
- Unexpected API behavior

**Diagnosis:**

```bash 
hcloud version
# Compare with latest version at https://support.huaweicloud.com/devg-hcloudcli/hcloudcli_01_0001.html
```

**Solution:**

```bash
# Update CLI
# Use built-in update command (recommended)
hcloud update

# Or reinstall latest version
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh -y
```

### 1.3 Configuration Missing or Invalid

**Symptoms:**

- `No configuration found`
- `InvalidAccessKeyId`
- `SignatureDoesNotMatch`

**Diagnosis:**

```bash
hcloud configure list
# Check if AK/SK and region are properly configured
```

**Solution:**

> **Credential configuration is the user's responsibility.** Please configure credentials in your terminal, then use `hcloud configure list` to verify.

Reference configuration commands:

```bash
# Reinitialize configuration
hcloud configure init

# Or set values individually
hcloud configure set --cli-access-key=<your-ak>
hcloud configure set --cli-secret-key=<your-sk>
hcloud configure set --cli-region=cn-north-4
```

### 1.4 Region Configuration Error

**Symptoms:**

- `The requested region is not available`
- `Endpoint not found for region`

**Diagnosis:**

```bash
# List available regions
hcloud IAM ListRegions
```

**Solution:**

> **Region configuration is the user's responsibility.** Please set the correct region in your terminal, then use `hcloud configure list` to verify.

Reference configuration command:

```bash
# Set correct region
hcloud configure set --cli-region=cn-north-4
```

## Category 2: Permission Issues

### 2.1 Insufficient ELB Permissions

**Symptoms:**

- `Access denied` when listing ELB instances
- `User does not have permission to access resource`

**Diagnosis:**

```bash
# Test ELB permissions
hcloud ELB ListLoadBalancers --cli-region=<region-id> --limit=1
```

**Solution:**

1. Check IAM policies: `references/iam-policies.md`
2. Attach required policy:
   - `ELB ReadOnlyAccess` (minimum)
   - Or custom policy with `elb:loadbalancers:list`, `elb:loadbalancers:get`

### 2.2 Insufficient CES Permissions

**Symptoms:**

- `Access denied` when querying metrics
- `User does not have permission to access CES`

**Diagnosis:**

```bash
# Test CES permissions
hcloud CES ListMetrics --namespace="SYS.ELB" --cli-region=<region-id> --limit=1
```

**Solution:**

1. Attach `CES ReadOnlyAccess` policy
2. Or custom policy with `ces:metrics:list`, `ces:metricData:get`

### 2.3 Cross-Account Permission Issues

**Symptoms:**

- `Assume role failed`
- `Cross-account access denied`

**Solution:**

1. Verify agency configuration in target account
2. Check agency permissions include required ELB and CES policies
3. Verify source account AK/SK has `iam:agencies:assumeRole` permission

## Category 3: Metric Query Issues

### 3.1 No Metric Data Returned

**Symptoms:**

- Query returns empty `datapoints` array
- No monitoring data available

**Diagnosis Steps:**

1. **Check ELB Instance Status:**

   ```bash
   hcloud ELB ShowLoadBalancer --loadbalancer_id=<elb-id> --cli-region=<region-id>
   # Verify provisioning_status is "ACTIVE"
   ```

2. **Check if Traffic Exists:**

   ```bash
   # Query with a wider time range
   hcloud CES BatchListMetricData \
     --metrics.1.namespace="SYS.ELB" \
     --metrics.1.metric_name="m1_cps" \
     --metrics.1.dimensions.1.name="lbaas_instance_id" \
     --metrics.1.dimensions.1.value="<elb-id>" \
     --from=$(date -d '24 hours ago' +%s)000 \
     --to=$(date +%s)000 \
     --period=3600 \
     --filter="average" \
     --cli-region=<region-id>
   ```

3. **Check Metric Availability:**

   ```bash
   hcloud CES ListMetrics \
     --namespace="SYS.ELB" \
     --dim.0="lbaas_instance_id,<elb-id>" \
     --cli-region=<region-id>
   ```

**Common Causes and Solutions:**

| Cause | Solution |
|-------|----------|
| ELB instance not running | Start the ELB instance |
| No traffic through ELB | Generate test traffic |
| Time range too recent | Wait 1-2 minutes for data collection |
| Wrong metric name | Verify metric name in `references/ces-metrics-reference.md` |
| Wrong dimension value | Verify ELB instance ID |
| New ELB instance | Wait 3-5 minutes for initial data |

### 3.2 HTTP Metrics Not Available

**Symptoms:**

- `elb_http_*` metrics return no data
- `l7_*_ratio` metrics not found

**Diagnosis:**

```bash
# Check if ELB is Shared type (HTTP metrics only for Dedicated)
hcloud ELB ShowLoadBalancer --loadbalancer_id=<elb-id> --cli-region=<region-id>
# Check "guaranteed" field: true = Dedicated, false = Shared
```

**Solution:**

- **Shared ELB**: HTTP metrics are not available. Use basic metrics only (`m1_cps`, `m2_act_conn`, etc.)
- **Dedicated ELB without HTTP listener**: Add HTTP/HTTPS listener to enable HTTP metrics
- **Dedicated ELB with HTTP listener**: Verify listener protocol is HTTP/HTTPS/QUIC/GRPC

### 3.3 Backend Server Group Metrics Not Available

**Symptoms:**

- Backend server group metrics return no data
- `m9_abnormal_host_count` not available for pool dimension

**Diagnosis:**

```bash
# Check if backend server groups exist
hcloud ELB ListPools --loadbalancer_id.1=<elb-id> --cli-region=<region-id>
```

**Solution:**

- Backend server group metrics are **Dedicated ELB only**
- Verify backend server groups are configured
- Ensure pool has backend servers attached

### 3.4 Invalid Dimension Error

**Symptoms:**

- `Invalid dimension`
- `Dimension not found`

**Diagnosis:**

```bash
# List available dimensions for the metric
hcloud CES ListMetrics \
  --namespace="SYS.ELB" \
  --metric_name="m1_cps" \
  --cli-region=<region-id>
```

**Common Dimension Errors:**

| Wrong | Correct | Description |
|-------|---------|-------------|
| `instance_id` | `lbaas_instance_id` | ELB instance dimension |
| `listener_id` | `lbaas_listener_id` | Listener dimension |
| `pool_id` | `lbaas_pool_id` | Backend server group dimension |
| `az` | `lbaas_az` | Availability zone dimension |

### 3.5 Time Range Issues

**Symptoms:**

- No data for specified time range
- `Invalid time range`

**Common Causes:**

| Cause | Solution |
|-------|----------|
| Start time after end time | Swap `--from` and `--to` values |
| Time range too large | Reduce time range or increase period |
| Future time specified | Use past timestamps only |
| Timestamp format wrong | Use Unix timestamp in milliseconds |
| Data not yet collected | Wait 1-2 minutes and retry |

**Time Range Verification:**

```bash
# Verify current timestamp
echo "Current time: $(date)"
echo "Current timestamp (ms): $(date +%s)000"
echo "1 hour ago (ms): $(date -d '-1 hour' +%s)000"

# Test with known valid time range
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="m1_cps" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="<elb-id>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=<region-id>
```

## Category 4: Performance Issues

### 4.1 Slow Query Response

**Symptoms:**

- Queries take > 10 seconds
- Timeout errors

**Diagnosis:**

```bash
# Measure query time
time hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="m1_cps" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="<elb-id>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=<region-id>
```

**Solutions:**

1. Reduce time range
2. Increase period (use 300s instead of 60s)
3. Query fewer metrics at once
4. Use `--query` parameter to filter results
5. Check network latency

### 4.2 Rate Limiting

**Symptoms:**

- `Throttling`
- `Too many requests`
- `Request rate exceeded`

**Solution:**

```bash
# Implement retry with exponential backoff
retry_count=0
max_retries=5
base_delay=2

while [ $retry_count -lt $max_retries ]; do
    result=$(hcloud CES BatchListMetricData ... 2>&1)
    
    if echo "$result" | grep -q "Throttling"; then
        delay=$((base_delay * 2 ** retry_count))
        echo "Rate limited, retrying in $delay seconds..."
        sleep $delay
        retry_count=$((retry_count + 1))
    else
        echo "$result"
        break
    fi
done
```

### 4.3 Network Connectivity Issues

**Symptoms:**

- `Connection timeout`
- `Network error`
- `Could not resolve host`

**Diagnosis:**

```bash
# Test connectivity to Huawei Cloud API
curl -I https://elb.cn-north-4.myhuaweicloud.com
curl -I https://ces.cn-north-4.myhuaweicloud.com

# Check DNS resolution
nslookup elb.cn-north-4.myhuaweicloud.com
```

**Solutions:**

1. Check network connectivity
2. Verify proxy settings if behind corporate proxy
3. Check firewall rules
4. Verify DNS resolution

## Category 5: Data Interpretation Issues

### 5.1 Unexpected Metric Values

**Symptoms:**

- Metric values seem too high or too low
- Negative values for non-negative metrics

**Diagnosis:**

```bash
# Query with multiple aggregation methods for comparison
for filter in average max min; do
  echo "Filter: $filter"
  hcloud CES BatchListMetricData \
    --metrics.1.namespace="SYS.ELB" \
    --metrics.1.metric_name="m1_cps" \
    --metrics.1.dimensions.1.name="lbaas_instance_id" \
    --metrics.1.dimensions.1.value="<elb-id>" \
    --from=$(date -d '-1 hour' +%s)000 \
    --to=$(date +%s)000 \
    --period=300 \
    --filter=$filter \
    --cli-region=<region-id> \
    --cli-query="datapoints[-1]" \
    --cli-output=json
done
```

**Common Value Issues:**

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| Zero values | No traffic during period | Verify traffic is flowing |
| Very high values | Traffic spike or DDoS | Investigate traffic source |
| Negative values | Data collection error | Contact Huawei Cloud support |
| Missing data points | Monitoring gap | Check ELB status during gap |

### 5.2 Unit Confusion

**Common Unit Issues:**

| Metric | Unit | Common Mistake |
|--------|------|----------------|
| `m7_in_Bps` | bit/s | Confusing with Byte/s (divide by 8) |
| `m5_in_packets` | Count/s | Confusing with total count |
| `m1_cps` | Count | Confusing with connections per second |
| `l7_*_ratio` | % | Already percentage, don't multiply by 100 |

## Category 6: ELB Type-Specific Issues

### 6.1 Dedicated ELB Issues

### Issue: HTTP metrics return empty for Dedicated ELB**

**Diagnosis:**

1. Verify listener protocol is HTTP/HTTPS/QUIC/GRPC
2. Check if traffic is flowing through HTTP listener
3. Verify metric name is correct

**Solution:**

```bash
# List listeners and check protocols
hcloud ELB ListListeners --loadbalancer_id.1=<elb-id> --cli-region=<region-id>

# Query HTTP metrics for specific listener
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="elb_http_5xx" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="<elb-id>" \
  --metrics.1.dimensions.2.name="lbaas_listener_id" \
  --metrics.1.dimensions.2.value="<listener-id>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=<region-id>
```

### 6.2 Shared ELB Issues

### Issue: Trying to access Dedicated ELB-only metrics**

**Symptoms:**

- `Metric not found` for `elb_http_*` or `l7_*_ratio`
- Empty results for backend server group metrics

**Solution:**

- Shared ELB only supports basic metrics
- Use `m1_cps`, `m2_act_conn`, `m3_inact_conn`, `m4_ncps`, `m5_in_packets`, `m6_out_packets`, `m7_in_Bps`, `m8_out_Bps`
- See `references/ces-metrics-reference.md` for Shared ELB available metrics

## Category 7: Alarm Issues

### 7.1 Alarm Creation Failure

**Symptoms:**

- `Create alarm failed`
- `Invalid alarm configuration`

**Diagnosis:**

```bash
# Verify alarm parameters
hcloud CES CreateAlarm --help
```

**Common Issues:**

1. Invalid metric name or namespace
2. Missing required parameters
3. Invalid threshold value
4. Notification topic not found

### 7.2 Alarm Not Triggering

**Symptoms:**

- Metric exceeds threshold but no alarm notification

**Diagnosis:**

```bash
# Check alarm status
hcloud CES ShowAlarm --alarm_id=<alarm-id> --cli-region=<region-id>
```

**Common Causes:**

1. Alarm is disabled
2. Condition count not met (e.g., need 3 consecutive breaches)
3. Notification channel not configured
4. Alarm period doesn't match monitoring period

## Error Code Reference

| Error Code | Description | Solution |
|------------|-------------|----------|
| `ELB.1003` | Load balancer does not exist | Verify the ELB ID is correct |
| `ELB.2011` | Listener does not exist | Verify the listener ID |
| `ELB.1020` | Invalid load balancer ID | Enter a valid ELB ID |
| `ELB.1001` | Invalid parameter | Enter valid parameters |
| `ELB.8903` | Insufficient account permissions | Contact administrator to grant required IAM permissions |
| `ELB.9802` | Authorization failed | Check if the account has permission for this operation |
| `ELB.8906` | Internal error | Contact technical support |
| `ces.0001` | Request content cannot be empty | Add correct request content |
| `ces.0003` | Project ID is empty or incorrect | Add or use the correct project ID |
| `ces.0015` | Authentication failed or no valid auth info | Check AK/SK or token is correct |
| `ces.0016` | Requested resource does not exist | Confirm the requested resource exists |
| `ces.0017` | Auth info error or insufficient permissions | Check AK/SK and IAM permissions |
| `ces.0007` | Internal error | Contact technical support |
| `IAM.0001` | Authentication failed | Verify authentication credentials |
| `IAM.0002` | Request unauthorized | Verify IAM policy authorization |
| `IAM.0066` | Token expired | Use a valid non-expired token |
| `IAM.1105` | AK has expired | Recreate the access key |

## Escalation Procedures

### Level 1: Self-Service

1. Check this troubleshooting guide
2. Review `references/ces-metrics-reference.md`
3. Verify configuration with `hcloud configure list`

### Level 2: Community Support

1. Search Huawei Cloud community forums
2. Check Stack Overflow for similar issues
3. Review Huawei Cloud documentation

### Level 3: Huawei Cloud Support

1. Collect diagnostic information:

   ```bash
   # System info
   hcloud version
   hcloud configure list
   
   # Error details
   hcloud --debug <failing-command>
   ```

2. Create support ticket with:
   - Error message and code
   - CLI version
   - Region and resource IDs
   - Steps to reproduce

## Prevention Checklist

- [ ] CLI installed and up-to-date
- [ ] Credentials configured and valid
- [ ] IAM permissions properly set
- [ ] Correct region specified
- [ ] Valid ELB instance IDs
- [ ] Correct metric names and namespaces
- [ ] Proper dimension names and values
- [ ] Valid time ranges
- [ ] Network connectivity verified
- [ ] Rate limits respected

## References

- [Huawei Cloud CLI Troubleshooting](https://support.huaweicloud.com/hcli_faq/hcli_10.html)
- [CES Error Codes](https://support.huaweicloud.com/api-ces/ErrorCode.html)
- [ELB Error Codes](https://support.huaweicloud.com/api-elb/ErrorCode.html)
- [IAM Error Codes](https://support.huaweicloud.com/api-iam/iam_02_0006.html)
