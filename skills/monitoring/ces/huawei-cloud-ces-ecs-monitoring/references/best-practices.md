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
# Collect baseline metrics during normal operation
# Run for at least 7 days to establish patterns
hcloud CES ShowMetricData \
  --namespace "SYS.ECS" \
  --metric_name "cpu_usage,mem_usage,disk_read_bytes_rate,disk_write_bytes_rate,network_incoming_bytes_rate,network_outgoing_bytes_rate" \
  --dim.0 "instance_id,<instance-id>" \
  --from $(date -d '7 days ago' +%s)000 \
  --to $(date +%s)000 \
  --period 3600 \
  --filter average \
  --cli-region <region-id>
```

## Metric Selection Guidelines

### Essential Metrics (Always Monitor)

```bash
# CPU and Memory
cpu_usage
mem_usage

# Disk
disk_used_percent
disk_read_bytes_rate
disk_write_bytes_rate

# Network
network_incoming_bytes_rate
network_outgoing_bytes_rate

# System
load_average1
```

### Performance Metrics (For Performance-Sensitive Applications)

```bash
# Disk IOPS
disk_read_requests_rate
disk_write_requests_rate

# Disk Latency
disk_read_time
disk_write_time

# Network Packets
network_incoming_packets_rate
network_outgoing_packets_rate

# Network Errors
network_incoming_errors_rate
network_outgoing_errors_rate
```

### Capacity Metrics (For Capacity Planning)

```bash
# Disk Space
disk_used_percent
disk_inodes_used_percent

# Memory
mem_used
mem_free

# Process
proc_rate
```

## Alerting Strategy

### 1. Critical Alerts (Immediate Action Required)

```bash
# CPU > 95% for 5 minutes
- Metric: cpu_usage
- Threshold: > 95%
- Duration: 5 minutes
- Action: Auto-scale or investigate immediately

# Memory > 95% for 5 minutes
- Metric: mem_usage
- Threshold: > 95%
- Duration: 5 minutes
- Action: Investigate memory leak or scale

# Disk > 95% for 15 minutes
- Metric: disk_used_percent
- Threshold: > 95%
- Duration: 15 minutes
- Action: Clean up or expand disk
```

### 2. Warning Alerts (Investigation Required)

```bash
# CPU > 80% for 15 minutes
- Metric: cpu_usage
- Threshold: > 80%
- Duration: 15 minutes
- Action: Monitor and plan scaling

# Memory > 85% for 15 minutes
- Metric: mem_usage
- Threshold: > 85%
- Duration: 15 minutes
- Action: Optimize or add memory

# Disk > 85% for 1 hour
- Metric: disk_used_percent
- Threshold: > 85%
- Duration: 1 hour
- Action: Plan disk expansion
```

### 3. Informational Alerts (Trend Monitoring)

```bash
# Network errors > 0
- Metric: network_incoming_errors_rate, network_outgoing_errors_rate
- Threshold: > 0
- Duration: 5 minutes
- Action: Investigate network issues

# Load average > CPU cores
- Metric: load_average1
- Threshold: > (CPU cores)
- Duration: 15 minutes
- Action: Check for process issues
```

## Monitoring Frequency Recommendations

### Real-Time Monitoring (High Frequency)

```bash
# For critical production instances
--period "60"  # 1-minute intervals
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
# Real-time: 1-minute (higher cost)
# Daily ops: 5-minute (balanced cost)
# Trends: 1-hour (lower cost)
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
hcloud ECS TagServer <instance-id> \
  --tags "Environment=Production,Team=Backend,Project=ECommerce" \
  --cli-region <region-id>
```

## Performance Optimization

### 1. Efficient Query Patterns

```bash
# Batch multiple metrics in single query
hcloud CES ShowMetricData \
  --namespace "SYS.ECS" \
  --metric_name "cpu_usage,mem_usage,disk_read_bytes_rate,disk_write_bytes_rate" \
  --dim.0 "instance_id,<instance-id>" \
  --cli-region <region-id>

# Instead of separate queries for each metric
```

### 2. Cache Frequently Used Data

```bash
# Cache instance list (valid for 5 minutes)
INSTANCE_CACHE_FILE="/tmp/ecs_instances_$(date +%Y%m%d%H%M).json"
if [ ! -f "$INSTANCE_CACHE_FILE" ] || [ "$(find "$INSTANCE_CACHE_FILE" -mmin +5)" ]; then
  hcloud ECS NovaListServers --cli-region=<region-id> --output json > \"$INSTANCE_CACHE_FILE\"
fi
```

### 3. Use Appropriate Time Ranges

```bash
# For real-time monitoring: Last 1 hour
--from "$(date -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)"

# For daily review: Last 24 hours
--from "$(date -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)"

# For weekly review: Last 7 days
--from "$(date -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)"
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
# Monitor pattern: cpu_usage > 90% AND network_outgoing_bytes_rate > 10MB/s

# High disk IO with low CPU (possible data exfiltration)
# Monitor pattern: disk_write_bytes_rate > 50MB/s AND cpu_usage < 20%
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

  # Check CPU
  CPU_USAGE=$(hcloud CES ShowMetricData \
    --namespace "SYS.ECS" \
    --metric_name "cpu_usage" \
    --dim.0 "instance_id,$INSTANCE_ID" \
    --from $(date -d '1 hour ago' +%s)000 \
    --to $(date +%s)000 \
    --period 300 \
    --filter average \
    --cli-region "$REGION" \
    --output json | jq '.datapoints[-1].average')

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
  START_TIME="$(date -d 'yesterday' +%Y-%m-%d)T00:00:00Z"
  END_TIME="$(date -d 'yesterday' +%Y-%m-%d)T23:59:59Z"
  
  METRICS="cpu_usage,mem_usage,disk_used_percent,network_incoming_bytes_rate,network_outgoing_bytes_rate"
  
  hcloud CES ShowMetricData \
    --namespace "SYS.ECS" \
    --metric_name "$METRICS" \
    --dim.0 "instance_id,$INSTANCE_ID" \
    --from $(date -d 'yesterday' +%s)000 \
    --to $(date +%s)000 \
    --period 3600 \
    --filter average \
    --cli-region "$REGION" \
    --output table
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
    echo "Date: $DAY_DATE"
    
    hcloud CES ShowMetricData \
      --namespace "SYS.ECS" \
      --metric_name "cpu_usage" \
      --dim.0 "instance_id,$INSTANCE_ID" \
      --from $(date -d "$DAY days ago" +%s)000 \
      --to $(date +%s)000 \
      --period 3600 \
      --filter average \
      --cli-region "$REGION" \
      --output json | jq -r '.datapoints[] | "\(.timestamp | strftime("%H:%M")): \(.average)%"' | head -5
    echo ""
  done
}
```

## References

- [Huawei Cloud CES Best Practices](https://support.huaweicloud.com/bestpractice-ces/ces_14_0055.html)
- [ECS Performance Optimization](https://support.huaweicloud.com/intl/zh-cn/usermanual-ecs/ecs_03_1001.html)