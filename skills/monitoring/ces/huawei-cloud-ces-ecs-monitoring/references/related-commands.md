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
hcloud ECS NovaShowServer --server_id=<instance-uuid> --cli-region=<region-id>

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
  --dim.0="instance_id,<instance-uuid>" \
  --cli-region=<region-id>

```

### Query Metric Data (BatchListMetricData - Recommended)

> **Note**: `BatchListMetricData` is the recommended command for querying metric data. It supports querying multiple metrics in a single request. Each `--metrics.N.metric_name` must contain exactly ONE metric name (no comma-separated values).

```bash
# Query CPU usage (SYS.ECS - base monitoring)
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-uuid>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=<region-id>

# Query memory usage (SYS.ECS - base monitoring)
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="mem_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-uuid>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=<region-id>

# Query multiple metrics simultaneously (each as a separate metrics entry)
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-uuid>" \
  --metrics.2.namespace="SYS.ECS" \
  --metrics.2.metric_name="mem_util" \
  --metrics.2.dimensions.1.name="instance_id" \
  --metrics.2.dimensions.1.value="<instance-uuid>" \
  --metrics.3.namespace="SYS.ECS" \
  --metrics.3.metric_name="disk_read_bytes_rate" \
  --metrics.3.dimensions.1.name="instance_id" \
  --metrics.3.dimensions.1.value="<instance-uuid>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=<region-id>

```

### Query Single Metric Data (ShowMetricData - Alternative)

> **Note**: `ShowMetricData` only supports querying a single metric at a time. For multiple metrics, use `BatchListMetricData` instead.

```bash
# Query single metric
hcloud CES ShowMetricData \
  --namespace="SYS.ECS" \
  --metric_name="cpu_util" \
  --dim.0="instance_id,<instance-uuid>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=<region-id>

```

### Query AGT.ECS Metrics (Agent Required)

> **Note**: AGT.ECS metrics require the Telescope agent to be installed on the ECS instance. The minimum period for AGT.ECS is 60 (1 minute).

```bash
# Query agent CPU usage (AGT.ECS)
hcloud CES BatchListMetricData \
  --metrics.1.namespace="AGT.ECS" \
  --metrics.1.metric_name="cpu_usage" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-uuid>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=60 \
  --filter="average" \
  --cli-region=<region-id>

# Query disk usage per mount point (AGT.ECS - requires mount_point dimension)
hcloud CES BatchListMetricData \
  --metrics.1.namespace="AGT.ECS" \
  --metrics.1.metric_name="disk_usedPercent" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-uuid>" \
  --metrics.1.dimensions.2.name="mount_point" \
  --metrics.1.dimensions.2.value="<mount-point-hash>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=60 \
  --filter="average" \
  --cli-region=<region-id>

```

### Namespace Fallback Strategy (SYS.ECS → AGT.ECS)

When a SYS.ECS metric query returns no data, try the corresponding AGT.ECS metric. See `references/ces-metrics-reference.md` for the complete fallback mapping table and `references/troubleshooting-guide.md` for detailed troubleshooting steps.

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

- 1: Real-time monitoring data
- 60: 1-minute granularity, one data point per minute (AGT.ECS only)
- 300: 5-minute granularity, one data point every 5 minutes
- 1200: 20-minute granularity, one data point every 20 minutes
- 3600: 1-hour granularity, one data point per hour
- 14400: 4-hour granularity, one data point every 4 hours
- 86400: 1-day granularity, one data point per day

> **Important**: period=60 (1-minute) is only available for AGT.ECS metrics. SYS.ECS metrics have a minimum period of 300 (5 minutes).

### Maximum Query Range & Overtime Rules for Each Cycle

If the query time range exceeds the maximum allowed duration, the interface will automatically adjust the start time from forward.

- period="1": Maximum range: 436001000 milliseconds
- period="60": Maximum range: 43200100 milliseconds
- period="300": Maximum range: 2436001000 milliseconds
- period="1200": Maximum range: 32436001000 milliseconds
- period="3600": Maximum range: 102436001000 milliseconds
- period="14400": Maximum range: 302436001000 milliseconds
- period="86400": Maximum range: 1802436001000 milliseconds

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

REGION="<region-id>"

# Get instance list
INSTANCES=$(hcloud ECS NovaListServers --cli-region=$REGION --limit=50)

# For each instance, get key metrics
for INSTANCE_ID in $(echo $INSTANCES | jq -r '.servers[].id'); do
  echo "=== Instance: $INSTANCE_ID ==="

  # CPU and Memory usage (SYS.ECS)
  hcloud CES BatchListMetricData \
    --metrics.1.namespace="SYS.ECS" \
    --metrics.1.metric_name="cpu_util" \
    --metrics.1.dimensions.1.name="instance_id" \
    --metrics.1.dimensions.1.value="$INSTANCE_ID" \
    --metrics.2.namespace="SYS.ECS" \
    --metrics.2.metric_name="mem_util" \
    --metrics.2.dimensions.1.name="instance_id" \
    --metrics.2.dimensions.1.value="$INSTANCE_ID" \
    --from=$(date -d '1 hour ago' +%s)000 \
    --to=$(date +%s)000 \
    --period="300" \
    --filter="average" \
    --cli-region=$REGION

  echo ""
done
```

### 2. Performance Troubleshooting

```bash
#!/bin/bash

INSTANCE_ID="<instance-uuid>"
REGION="<region-id>"
START_TIME=$(date -d '1 hour ago' +%s)000
END_TIME=$(date +%s)000

echo "Performance Analysis for $INSTANCE_ID"
echo "Time Range: $START_TIME to $END_TIME"
echo ""

# Get all key SYS.ECS metrics
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="$INSTANCE_ID" \
  --metrics.2.namespace="SYS.ECS" \
  --metrics.2.metric_name="mem_util" \
  --metrics.2.dimensions.1.name="instance_id" \
  --metrics.2.dimensions.1.value="$INSTANCE_ID" \
  --metrics.3.namespace="SYS.ECS" \
  --metrics.3.metric_name="disk_read_bytes_rate" \
  --metrics.3.dimensions.1.name="instance_id" \
  --metrics.3.dimensions.1.value="$INSTANCE_ID" \
  --metrics.4.namespace="SYS.ECS" \
  --metrics.4.metric_name="disk_write_bytes_rate" \
  --metrics.4.dimensions.1.name="instance_id" \
  --metrics.4.dimensions.1.value="$INSTANCE_ID" \
  --metrics.5.namespace="SYS.ECS" \
  --metrics.5.metric_name="network_incoming_bytes_rate_inband" \
  --metrics.5.dimensions.1.name="instance_id" \
  --metrics.5.dimensions.1.value="$INSTANCE_ID" \
  --metrics.6.namespace="SYS.ECS" \
  --metrics.6.metric_name="network_outgoing_bytes_rate_inband" \
  --metrics.6.dimensions.1.name="instance_id" \
  --metrics.6.dimensions.1.value="$INSTANCE_ID" \
  --from="$START_TIME" \
  --to="$END_TIME" \
  --period="300" \
  --filter="average" \
  --cli-region="$REGION"
```

### 3. Historical Trend Analysis

```bash
#!/bin/bash

INSTANCE_ID="<instance-uuid>"
REGION="<region-id>"

# Daily averages for last 7 days
for DAYS_AGO in {0..6}; do
  START_TIME=$(date -d "$DAYS_AGO days ago 00:00:00" +%s)000
  END_TIME=$(date -d "$DAYS_AGO days ago 23:59:59" +%s)000

  echo "=== $(date -d "$DAYS_AGO days ago" +%Y-%m-%d) ==="

  hcloud CES BatchListMetricData \
    --metrics.1.namespace="SYS.ECS" \
    --metrics.1.metric_name="cpu_util" \
    --metrics.1.dimensions.1.name="instance_id" \
    --metrics.1.dimensions.1.value="$INSTANCE_ID" \
    --metrics.2.namespace="SYS.ECS" \
    --metrics.2.metric_name="mem_util" \
    --metrics.2.dimensions.1.name="instance_id" \
    --metrics.2.dimensions.1.value="$INSTANCE_ID" \
    --from="$START_TIME" \
    --to="$END_TIME" \
    --period="3600" \
    --filter="average" \
    --cli-region="$REGION"
done
```

## Error Handling Examples

### Check Command Success

```bash
if hcloud ECS NovaListServers --cli-region=<region-id> > /dev/null 2>&1; then
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
  --to="$END_TIME" \
  --period="300" \
  --filter="average" \
  --cli-region="$REGION")

if [ "$(echo "$METRIC_DATA" | jq '.metrics[0].datapoints | length')" -eq "0" ]; then
  echo "No metric data found for the specified time range"
else
  echo "Found metric data"
  # Process data
fi
```

## Performance Tips

For performance optimization tips (batch queries, caching, appropriate time ranges), see `references/best-practices.md`.

## Common Errors and Solutions

For common errors and solutions, see `references/troubleshooting-guide.md`.

## References

- [Huawei Cloud CLI Documentation](https://support.huaweicloud.com/function-hcli/index.html)
- [ECS API Reference](https://support.huaweicloud.com/api-ecs/ecs_01_0008.html)
- [CES API Reference](https://support.huaweicloud.com/api-ces/ces_03_0041.html)
- [jq Documentation](https://stedolan.github.io/jq/) (for JSON processing)
