# Huawei Cloud ECS Monitoring Best Practices

## Overview

This document provides best practices for monitoring Huawei Cloud ECS instances using Cloud Eye Service (CES). Following these practices ensures effective monitoring, optimal performance, and cost efficiency.

## Monitoring Strategy

### 1. Define Monitoring Objectives

- **Availability**: Ensure instances are running and accessible
- **Performance**: Monitor resource utilization and response times
- **Capacity**: Track resource usage trends for scaling decisions
- **Cost**: Optimize resource allocation to control costs
- **Security**: Monitor for suspicious activities and anomalies

### 2. Establish Baseline Metrics

```bash
# Collect baseline SYS.ECS metrics during normal operation
# Run for at least 7 days to establish patterns
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
  --metrics.4.namespace="SYS.ECS" \
  --metrics.4.metric_name="disk_write_bytes_rate" \
  --metrics.4.dimensions.1.name="instance_id" \
  --metrics.4.dimensions.1.value="<instance-uuid>" \
  --from=$(date -d '7 days ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=3600 \
  --filter=average \
  --cli-region=<region-id>
```

## Metric Selection Guidelines

### Namespace Fallback Strategy

When a SYS.ECS metric returns no data, try the corresponding AGT.ECS metric. See `references/ces-metrics-reference.md` for the complete fallback mapping table.

### Essential Metrics - SYS.ECS (No Agent Required)

```
# CPU and Memory
cpu_util
mem_util

# Disk
disk_util_inband
disk_read_bytes_rate
disk_write_bytes_rate

# Network
network_incoming_bytes_rate_inband
network_outgoing_bytes_rate_inband
```

### Essential Metrics - AGT.ECS (Agent Required)

```
# CPU and Memory (OS-level)
cpu_usage
mem_usedPercent

# Disk (per mount point)
disk_usedPercent

# System
load_average1
net_tcp_total
```

### Performance Metrics - AGT.ECS (For Performance-Sensitive Applications)

```
# Disk IOPS and Latency
disk_agt_read_requests_rate
disk_agt_write_requests_rate
disk_readTime
disk_writeTime

# Network Card
net_bitRecv
net_bitSent
net_errin
net_errout
```

### Capacity Metrics - AGT.ECS (For Capacity Planning)

```
# Disk Space (per mount point)
disk_usedPercent
disk_inodesUsedPercent

# Memory (GB)
mem_available
mem_free

# Process
proc_total_count
proc_zombie_count
```

## Alerting Strategy

### 1. Critical Alerts (Immediate Action Required)

```bash
# CPU > 95% for 5 minutes (SYS.ECS)
- Metric: cpu_util
- Namespace: SYS.ECS
- Threshold: > 95%
- Duration: 5 minutes
- Action: Auto-scale or investigate immediately

# Memory > 95% for 5 minutes (SYS.ECS)
- Metric: mem_util
- Namespace: SYS.ECS
- Threshold: > 95%
- Duration: 5 minutes
- Action: Investigate memory leak or scale

# Disk > 95% for 15 minutes (AGT.ECS)
- Metric: disk_usedPercent
- Namespace: AGT.ECS
- Threshold: > 95%
- Duration: 15 minutes
- Action: Clean up or expand disk
```

### 2. Warning Alerts (Investigation Required)

```bash
# CPU > 80% for 15 minutes (SYS.ECS)
- Metric: cpu_util
- Namespace: SYS.ECS
- Threshold: > 80%
- Duration: 15 minutes
- Action: Monitor and plan scaling

# Memory > 85% for 15 minutes (SYS.ECS)
- Metric: mem_util
- Namespace: SYS.ECS
- Threshold: > 85%
- Duration: 15 minutes
- Action: Optimize or add memory

# Disk > 85% for 1 hour (AGT.ECS)
- Metric: disk_usedPercent
- Namespace: AGT.ECS
- Threshold: > 85%
- Duration: 1 hour
- Action: Plan disk expansion
```

### 3. Informational Alerts (Trend Monitoring)

```bash
# Network errors > 0 (AGT.ECS)
- Metric: net_errin, net_errout
- Namespace: AGT.ECS
- Threshold: > 0
- Duration: 5 minutes
- Action: Investigate network issues

# Load average > CPU cores (AGT.ECS)
- Metric: load_average1
- Namespace: AGT.ECS
- Threshold: > (CPU cores)
- Duration: 15 minutes
- Action: Check for process issues

# Zombie processes > 0 (AGT.ECS)
- Metric: proc_zombie_count
- Namespace: AGT.ECS
- Threshold: > 0
- Duration: 5 minutes
- Action: Investigate zombie processes
```

## Monitoring Frequency Recommendations

### Real-Time Monitoring (High Frequency)

```bash
# For critical production instances
# SYS.ECS: minimum period is 300 (5 minutes)
--period "300"

# AGT.ECS: minimum period is 60 (1 minute)
--period "60"
# Retention: 2 days
# Use for: Immediate alerting, troubleshooting
```

### Operational Monitoring (Standard)

```bash
# For most production instances
--period "300"  # 5-minute intervals
# Retention: 15 days
# Use for: Daily operations, performance analysis
```

### Trend Analysis (Low Frequency)

```bash
# For capacity planning and cost analysis
--period "3600"  # 1-hour intervals
# Retention: 30 days
--period "86400"  # 1-day intervals
# Retention: 1 year
```

## Cost Optimization

### 1. Selective Monitoring

```bash
# Monitor only necessary metrics
# Avoid monitoring all metrics for all instances

# Production instances: Full monitoring
# Development instances: Essential metrics only
# Test instances: Minimal monitoring
```

### 2. Appropriate Aggregation

```bash
# Use appropriate periods based on need
# SYS.ECS: minimum 5-minute (300)
# AGT.ECS: minimum 1-minute (60)
# Daily ops: 5-minute (300)
# Trends: 1-hour (3600)
```

### 3. Data Retention Policy

```bash
# Real-time data: Keep for 2-7 days
# Daily aggregates: Keep for 30 days
# Monthly aggregates: Keep for 1 year
# Export to OBS for long-term storage
```

### 4. Instance Tagging for Cost Allocation

```bash
# Tag instances by environment, team, project
hcloud ECS TagServer <instance-uuid> \
  --tags "Environment=Production,Team=Backend,Project=ECommerce" \
  --cli-region <region-id>
```

## Performance Optimization

### 1. Efficient Query Patterns

```bash
# Batch multiple metrics in single query (more efficient)
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-uuid>" \
  --metrics.2.namespace="SYS.ECS" \
  --metrics.2.metric_name="mem_util" \
  --metrics.2.dimensions.1.name="instance_id" \
  --metrics.2.dimensions.1.value="<instance-uuid>" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter=average \
  --cli-region <region-id>

# Instead of separate queries for each metric
```

### 2. Cache Frequently Used Data

```bash
# Cache instance list (valid for 5 minutes)
INSTANCE_CACHE_FILE="/tmp/ecs_instances_$(date +%Y%m%d%H%M).json"
if [ ! -f "$INSTANCE_CACHE_FILE" ] || [ "$(find "$INSTANCE_CACHE_FILE" -mmin +5)" ]; then
  hcloud ECS NovaListServers --cli-region=<region-id> > "$INSTANCE_CACHE_FILE"
fi
```

### 3. Use Appropriate Time Ranges

```bash
# For real-time monitoring: Last 1 hour
--from=$(date -d '1 hour ago' +%s)000
--to=$(date +%s)000

# For daily review: Last 24 hours
--from=$(date -d '24 hours ago' +%s)000
--to=$(date +%s)000

# For weekly review: Last 7 days
--from=$(date -d '7 days ago' +%s)000
--to=$(date +%s)000
```

## Security Monitoring

### 1. Unauthorized Access Detection

```bash
# Monitor SSH login attempts
# (Requires custom metric from OS monitoring agent)
```

### 2. Resource Abuse Detection

```bash
# High CPU with network traffic (possible mining)
# Monitor pattern: cpu_util > 90% AND network_outgoing_bytes_rate_inband > 10MB/s

# High disk IO with low CPU (possible data exfiltration)
# Monitor pattern: disk_write_bytes_rate > 50MB/s AND cpu_util < 20%
```

### 3. Configuration Drift Detection

```bash
# Monitor for unexpected instance state changes
# Track: instance status, security group changes, image changes
```

## Automation and Integration

### 1. Automated Health Checks

```bash
#!/bin/bash
# Daily health check script

INSTANCE_ID="$1"
REGION="$2"

# Check CPU (SYS.ECS)
CPU_USAGE=$(hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="$INSTANCE_ID" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter=average \
  --cli-region "$REGION" \
  --output json | jq '.metrics[0].datapoints[-1].average')

if (( $(echo "$CPU_USAGE > 80" | bc -l) )); then
  echo "WARNING: High CPU usage: $CPU_USAGE%"
  # Send alert
fi

# Similar checks for memory, disk, network...
```

### 2. Integration with Notification Services

```bash
# Integrate with SMN (Simple Message Notification) for alerts
# Use webhooks for integration with external systems
# Schedule regular reports via email
```

### 3. Automated Scaling Triggers

```bash
# Monitor metrics and trigger auto-scaling
# Example: Scale out when CPU > 70% for 10 minutes
# Example: Scale in when CPU < 30% for 30 minutes
```

## Reporting and Visualization

### 1. Daily Summary Report

```bash
#!/bin/bash
# Generate daily monitoring report

generate_daily_report() {
  INSTANCE_ID="$1"
  REGION="$2"
  REPORT_DATE="$(date +%Y-%m-%d)"

  echo "=== Daily Monitoring Report ==="
  echo "Instance: $INSTANCE_ID"
  echo "Date: $REPORT_DATE"
  echo "Region: $REGION"
  echo ""

  # Get metrics for yesterday
  START_TIME=$(date -d 'yesterday 00:00:00' +%s)000
  END_TIME=$(date -d 'yesterday 23:59:59' +%s)000

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
    --period=3600 \
    --filter=average \
    --cli-region "$REGION"
}
```

### 2. Performance Trend Analysis

```bash
#!/bin/bash
# Analyze weekly performance trends

analyze_weekly_trends() {
  INSTANCE_ID="$1"
  REGION="$2"

  echo "=== Weekly Performance Trends ==="
  echo "Instance: $INSTANCE_ID"
  echo "Period: Last 7 days"
  echo ""

  for DAY in {0..6}; do
    DAY_DATE="$(date -d "$DAY days ago" +%Y-%m-%d)"
    START_TIME=$(date -d "$DAY days ago 00:00:00" +%s)000
    END_TIME=$(date -d "$DAY days ago 23:59:59" +%s)000
    echo "Date: $DAY_DATE"

    hcloud CES BatchListMetricData \
      --metrics.1.namespace="SYS.ECS" \
      --metrics.1.metric_name="cpu_util" \
      --metrics.1.dimensions.1.name="instance_id" \
      --metrics.1.dimensions.1.value="$INSTANCE_ID" \
      --from="$START_TIME" \
      --to="$END_TIME" \
      --period=3600 \
      --filter=average \
      --cli-region "$REGION"
    echo ""
  done
}
```

## References

- [Huawei Cloud CES Best Practices](https://support.huaweicloud.com/bestpractice-ces/ces_14_0055.html)
- [ECS Performance Optimization](https://support.huaweicloud.com/usermanual-ecs/ecs_03_1001.html)
