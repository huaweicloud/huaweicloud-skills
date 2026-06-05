# Huawei Cloud CLI Commands for ECS Monitoring

## Overview

This document provides detailed command references for Huawei Cloud CLI (hcloud) commands used in the ECS monitoring skill.

## Basic Command Structure

```bash
hcloud <service> <command> [options] [parameters]
```

## ECS Commands

### List ECS Instances

```bash
# Basic listing
hcloud ECS NovaListServers --cli-region=<region-id> --limit=50

```

### Get ECS Instance Details

```bash
# Get basic information
hcloud ECS NovaShowServer --server_id=<instance-id> --cli-region=<region-id>

```

### List ECS Flavors

```bash
# List all flavors
hcloud ECS NovaListFlavors --cli-region=<region-id>

```

## CES (Cloud Eye Service) Commands

### List Available Metrics

```bash
# List all metrics for ECS namespace
hcloud CES ListMetrics \
  --namespace="SYS.ECS" \
  --cli-region=<region-id>

# List metrics for specific instance
hcloud CES ListMetrics \
  --namespace="SYS.ECS" \
  --dim.0="instance_id,<instance-id>" \
  --cli-region=<region-id>

```

### Get Metric Data

```bash
#Basic metric data query： Query CPU usage
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-id>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=<region-id>

#Basic metric data query： Query memory usage
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="mem_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-id>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=<region-id>

# Query multiple metrics simultaneously
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-id>" \
  --metrics.2.namespace="SYS.ECS" \
  --metrics.2.metric_name="mem_util" \
  --metrics.2.dimensions.1.name="instance_id" \
  --metrics.2.dimensions.1.value="<instance-id>" \
  --metrics.3.namespace="SYS.ECS" \
  --metrics.3.metric_name="disk_read_bytes_rate" \
  --metrics.3.dimensions.1.name="instance_id" \
  --metrics.3.dimensions.1.value="<instance-id>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=<region-id>

```

### List Alarms

```bash
# List all alarms
hcloud CES ListAlarms --cli-region=<region-id>

```

### Get Alarm Details

```bash
hcloud CES ShowAlarm <alarm-id> --cli-region=<region-id>

```

## Time Format Specifications

### Mandatory Format Requirements

Both from and to must be 13-digit numeric millisecond timestamps, and the value of from must be less than to.

### period Collection Cycle Enumeration (Unit: Second)

-1: Real-time monitoring data
-60: 1-minute granularity, one data point per minute
-300: 5-minute granularity, one data point every 5 minutes
-1200: 20-minute granularity, one data point every 20 minutes
-3600: 1-hour granularity, one data point per hour
-14400: 4-hour granularity, one data point every 4 hours
-86400: 1-day granularity, one data point per day

### Maximum Query Range & Overtime Rules for Each Cycle

If the query time range exceeds the maximum allowed duration, the interface will automatically adjust the start time from forward.
-period="1" : Maximum range: 436001000 milliseconds
-period="300" : Maximum range: 2436001000 milliseconds
-period="1200" : Maximum range: 32436001000 milliseconds
-period="3600" : Maximum range: 102436001000 milliseconds
-period="14400": Maximum range: 302436001000 milliseconds
-period="86400": Maximum range: 1802436001000 milliseconds

### Common Relative Time (Millisecond Timestamp Format)

```bash
# Last 1 hour
--from=$(date -d '1 hour ago' +%s)000 \
--to=$(date +%s)000

# Last 6 hours
--from=$(date -d '6 hours ago' +%s)000 \
--to=$(date +%s)000

# Last 24 hours
--from=$(date -d '24 hours ago' +%s)000 \
--to=$(date +%s)000

# Last 7 days
--from=$(date -d '7 days ago' +%s)000 \
--to=$(date +%s)000

# Today from 00:00 to current time
--from=$(date -d "$(date +%Y-%m-%d) 00:00:00" +%s)000 \
--to=$(date +%s)000

# Full time range of yesterday
--from=$(date -d "yesterday 00:00:00" +%s)000 \
--to=$(date -d "yesterday 23:59:59" +%s)000
```

### Fixed Time Range (Fill in millisecond timestamps directly)

```bash
# Specific date and time
--from="1716988800000" \
--to="1716992400000"

# From the 1st day of current month to current time
--from=$(date -d "$(date +%Y-%m-01) 00:00:00" +%s)000 \
--to=$(date +%s)000
```

## Common Query Patterns

### 1. Basic Monitoring Dashboard

```bash
#!/bin/bash

# Get instance list
INSTANCES=$(hcloud ECS NovaListServers --cli-region=<region-id> --limit=50 )

# For each instance, get key metrics
for INSTANCE_ID in $(echo $INSTANCES | jq -r '.servers[].id'); do
  echo "=== Instance: $INSTANCE_ID ==="
  
  # CPU usage (correct format)
  hcloud CES BatchListMetricData \
    --metrics.1.namespace="SYS.ECS" \
    --metrics.1.metric_name="cpu_util" \
    --metrics.1.dimensions.1.name="instance_id" \
    --metrics.1.dimensions.1.value="$INSTANCE_ID" \
    --from=$(date -d '1 hour ago' +%s)000 \
    --to=$(date +%s)000 \
    --period="300" \
    --filter="average" \
    --cli-region=<region-id>
  
  # Memory usage (correct format)
  hcloud CES BatchListMetricData \
    --metrics.1.namespace="SYS.ECS" \
    --metrics.1.metric_name="mem_util" \
    --metrics.1.dimensions.1.name="instance_id" \
    --metrics.1.dimensions.1.value="$INSTANCE_ID" \
    --from=$(date -d '1 hour ago' +%s)000 \
    --to=$(date +%s)000 \
    --period="300" \
    --filter="average" \
    --cli-region=<region-id>
  
  echo ""
done
```

### 2. Performance Troubleshooting

```bash
#!/bin/bash

INSTANCE_ID="i-1234567890abcdef0"
REGION="cn-north-1"
START_TIME=$(date -d '1 hour ago' +%s)000
END_TIME=$(date +%s)000

echo "Performance Analysis for $INSTANCE_ID"
echo "Time Range: $START_TIME to $END_TIME"
echo ""

# Get all key metrics
METRICS="cpu_util,mem_util,disk_read_bytes_rate,disk_write_bytes_rate,network_incoming_bytes_rate_inband,network_outgoing_bytes_rate"

hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="$METRICS" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="$INSTANCE_ID" \
  --from="$START_TIME" \
  --to="$END_TIME" \
  --period="300" \
  --filter="average,max" \
  --cli-region="$REGION"
```

### 3. Historical Trend Analysis

```bash
#!/bin/bash

INSTANCE_ID="i-1234567890abcdef0"
REGION="cn-north-1"

# Daily averages for last 7 days
for DAYS_AGO in {0..6}; do
  START_TIME=$(date -d "$DAYS_AGO days ago 00:00:00" +%s)000
  END_TIME=$(date -d "$DAYS_AGO days ago 23:59:59" +%s)000
  
  echo "=== $(date -d "$DAYS_AGO days ago" +%Y-%m-%d) ==="
  
  hcloud CES BatchListMetricData \
    --metrics.1.namespace="SYS.ECS" \
    --metrics.1.metric_name="cpu_util,mem_util" \
    --metrics.1.dimensions.1.name="instance_id" \
    --metrics.1.dimensions.1.value="$INSTANCE_ID" \
    --from="$START_TIME" \
    --to="$END_TIME" \
    --period="3600" \
    --filter="average" \
    --cli-region="$REGION" | tail -1
done
```

## Error Handling Examples

### Check Command Success

```bash
if hcloud ECS ListServers --cli-region=<region-id> > /dev/null 2>&1; then
  echo "Command succeeded"
else
  echo "Command failed with error: $?"
  # Handle error
fi
```

### Handle Empty Results

```bash
METRIC_DATA=$(hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="$INSTANCE_ID" \
  --from="$START_TIME" \
  --period="300" \
  --filter="average" \
  --to="$END_TIME" \
  --cli-region="$REGION")

if [ "$(echo "$METRIC_DATA" | jq '.datapoints | length')" -eq "0" ]; then
  echo "No metric data found for the specified time range"
else
  echo "Found metric data"
  # Process data
fi
```

## Performance Tips

### 1. Batch Queries

```bash
# Query multiple metrics at once (more efficient)
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util,mem_util,disk_read_bytes_rate,disk_write_bytes_rate" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="$INSTANCE_ID" \
  --cli-region="$REGION"
```

### 2. Appropriate Time Ranges

- Use 5-minute periods for real-time monitoring
- Use 1-hour periods for daily trends
- Use 1-day periods for monthly trends

### 3. Limit Data Points

```bash
# Limit to last 100 data points
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="$INSTANCE_ID" \
  --from=$(date -d '24 hours ago' +%s)000 \
  --to=$(date +%s)000 \
  --period="300" \
  --filter="average" \
  --limit=100 \
  --cli-region="$REGION"
```

### 4. Cache Results

```bash
# Cache instance list
if [ ! -f "/tmp/instances.json" ] || [ "$(find /tmp/instances.json -mmin +5)" ]; then
  hcloud ECS ListServers --cli-region="$REGION" > /tmp/instances.json
fi

INSTANCES=$(cat /tmp/instances.json)
```

## Common Errors and Solutions

### 1. "Invalid access key"

```bash
# Check credentials
hcloud configure list

# Reconfigure if needed
hcloud configure init
```

### 2. "No such metric"

```bash
# List available metrics first
hcloud CES ListMetrics \
  --namespace="SYS.ECS" \
  --dim.0="instance_id,$INSTANCE_ID" \
  --cli-region="$REGION"
```

### 3. "Invalid time range"

```bash
# Ensure time format is correct
# Use ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
# Example: 2024-01-20T10:30:00Z
```

### 4. "Too many data points"

```bash
# Increase period or reduce time range
--period="3600"  # 1-hour intervals instead of 5-minute
--from="$(date -d '6 hours ago' +%s)000"  # Shorter range
```

## References

- [Huawei Cloud CLI Documentation](https://support.huaweicloud.com/function-hcli/index.html)
- [ECS API Reference](https://support.huaweicloud.com/intl/zh-cn/api-ecs/ecs_01_0008.html)
- [CES API Reference](https://support.huaweicloud.com/intl/zh-cn/api-ces/zh-cn_topic_0171212514.html)
- [jq Documentation](https://stedolan.github.io/jq/) (for JSON processing)