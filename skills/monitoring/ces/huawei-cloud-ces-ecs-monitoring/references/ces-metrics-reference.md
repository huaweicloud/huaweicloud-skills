# Huawei Cloud CES Metrics Reference for ECS

## Overview

Cloud Eye Service (CES) provides comprehensive monitoring metrics for Elastic Cloud Server (ECS) instances. This document lists all available metrics, their meanings, and usage guidelines.

## Metric Namespace

All ECS metrics are under the namespace: `SYS.ECS`

## CPU Metrics

### cpu_usage

- **Description**: CPU utilization percentage
- **Unit**: Percent (%)
- **Range**: 0-100
- **Collection Granularity**: 5 minutes
- **Alarm Thresholds**:
  - Warning: > 80%
  - Critical: > 90%
- **Usage**:

  ```bash
  hcloud CES ShowMetricData \
    --namespace="SYS.ECS" \
    --metric_name="cpu_usage" \
    --dim.0="instance_id,i-12345678"
  ```

### cpu_util

- **Description**: CPU utilization (alias for cpu_usage)
- **Unit**: Percent (%)
- **Note**: Same as cpu_usage, provided for compatibility

### cpu_idle_time

- **Description**: CPU idle time
- **Unit**: Percentage (%)
- **Note**: Lower values indicate higher CPU utilization

## Memory Metrics

### mem_usage

- **Description**: Memory utilization percentage
- **Unit**: Percent (%)
- **Range**: 0-100
- **Collection Granularity**: 5 minutes
- **Alarm Thresholds**:
  - Warning: > 85%
  - Critical: > 95%
- **Usage**:

  ```bash
  hcloud CES ShowMetricData \
    --namespace="SYS.ECS" \
    --metric_name="mem_usage" \
    --dim.0="instance_id,i-12345678"
  ```

### mem_used

- **Description**: Used memory
- **Unit**: Megabytes (MB)
- **Usage**: Track absolute memory consumption

### mem_free

- **Description**: Free memory
- **Unit**: Megabytes (MB)
- **Usage**: Monitor available memory

### mem_used_percent

- **Description**: Memory usage percentage (alternative)
- **Unit**: Percent (%)
- **Note**: Similar to mem_usage

## Disk Metrics

### disk_read_bytes_rate

- **Description**: Disk read rate
- **Unit**: Bytes per second (B/s)
- **Collection Granularity**: 5 minutes
- **Usage**: Monitor disk read performance
- **Typical Values**:
  - HDD: 50-150 MB/s
  - SSD: 200-500 MB/s
  - Ultra-high performance: 1+ GB/s

### disk_write_bytes_rate

- **Description**: Disk write rate
- **Unit**: Bytes per second (B/s)
- **Collection Granularity**: 5 minutes
- **Usage**: Monitor disk write performance

### disk_read_requests_rate

- **Description**: Disk read IOPS (Input/Output Operations Per Second)
- **Unit**: Count per second
- **Usage**: Monitor disk read operations
- **Typical Values**:
  - HDD: 50-150 IOPS
  - SSD: 3,000-20,000 IOPS
  - Ultra-high performance: 50,000+ IOPS

### disk_write_requests_rate

- **Description**: Disk write IOPS
- **Unit**: Count per second
- **Usage**: Monitor disk write operations

### disk_used_percent

- **Description**: Disk usage percentage
- **Unit**: Percent (%)
- **Collection Granularity**: 5 minutes
- **Alarm Thresholds**:
  - Warning: > 80%
  - Critical: > 90%
- **Usage**:

  ```bash
  hcloud CES ShowMetricData \
    --namespace="SYS.ECS" \
    --metric_name="disk_used_percent" \
    --dim.0="instance_id,i-12345678,mount_point,/"
  ```

### disk_read_time

- **Description**: Disk read time
- **Unit**: Milliseconds (ms)
- **Usage**: Monitor disk read latency

### disk_write_time

- **Description**: Disk write time
- **Unit**: Milliseconds (ms)
- **Usage**: Monitor disk write latency

## Network Metrics

### network_incoming_bytes_rate

- **Description**: Network inbound rate
- **Unit**: Bytes per second (B/s)
- **Collection Granularity**: 5 minutes
- **Usage**: Monitor incoming network traffic
- **Conversion**: 1 MB/s = 8 Mbps

### network_outgoing_bytes_rate

- **Description**: Network outbound rate
- **Unit**: Bytes per second (B/s)
- **Collection Granularity**: 5 minutes
- **Usage**: Monitor outgoing network traffic

### network_incoming_packets_rate

- **Description**: Inbound packets per second
- **Unit**: Count per second
- **Usage**: Monitor network packet reception rate

### network_outgoing_packets_rate

- **Description**: Outbound packets per second
- **Unit**: Count per second
- **Usage**: Monitor network packet transmission rate

### network_incoming_errors_rate

- **Description**: Inbound error packets rate
- **Unit**: Count per second
- **Usage**: Monitor network reception errors
- **Alarm Threshold**: > 0 (any errors should be investigated)

### network_outgoing_errors_rate

- **Description**: Outbound error packets rate
- **Unit**: Count per second
- **Usage**: Monitor network transmission errors
- **Alarm Threshold**: > 0

## System Metrics

### load_average1

- **Description**: 1-minute load average
- **Unit**: Load average (system load)
- **Collection Granularity**: 5 minutes
- **Interpretation**:
  - < CPU cores: Normal
  - = CPU cores: Fully loaded
  - > CPU cores: Overloaded
- **Usage**:

  ```bash
  hcloud CES ShowMetricData \
    --namespace="SYS.ECS" \
    --metric_name="load_average1" \
    --dim.0="instance_id,i-12345678"
  ```

### load_average5

- **Description**: 5-minute load average
- **Unit**: Load average
- **Usage**: Medium-term load trend

### load_average15

- **Description**: 15-minute load average
- **Unit**: Load average
- **Usage**: Long-term load trend

### proc_rate

- **Description**: Process creation rate
- **Unit**: Count per second
- **Usage**: Monitor process creation activity

### disk_inodes_used_percent

- **Description**: Inode usage percentage
- **Unit**: Percent (%)
- **Collection Granularity**: 5 minutes
- **Alarm Thresholds**:
  - Warning: > 80%
  - Critical: > 90%
- **Note**: Important for systems with many small files

### tcp_connections

- **Description**: TCP connections count
- **Unit**: Count
- **Usage**: Monitor network connection load

### udp_connections

- **Description**: UDP connections count
- **Unit**: Count
- **Usage**: Monitor UDP connection load

## Namespace

- **SYS.ECS**
  Basic monitoring metrics for Elastic Cloud Server (ECS).
- **AGT.ECS**
  OS monitoring metrics and process monitoring metrics for Elastic Cloud Server (ECS).
  *Requires installing the monitoring Agent.*

## Metric Dimensions

### Required Dimensions

Most ECS metrics require these dimensions:

- `instance_id`: The ECS instance ID
- Additional dimensions for specific metrics:
  - `mount_point`: For disk metrics (e.g., `/`, `/data`)
  - `device`: For disk metrics (e.g., `vda`, `vdb`)
  - `nic`: For network metrics (e.g., `eth0`, `eth1`)

### Example with Dimensions

```bash
# Disk metric with mount point
hcloud CES ShowMetricData \
  --namespace="SYS.ECS" \
  --metric_name="disk_used_percent" \
  --dim.0="instance_id,i-12345678,mount_point,/"

# Network metric with NIC
hcloud CES ShowMetricData \
  --namespace="SYS.ECS" \
  --metric_name="network_incoming_bytes_rate" \
  --dim.0="instance_id,i-12345678,nic,eth0"
```

## Common Monitoring Scenarios

### 1. Performance Baseline

```bash
# Get baseline metrics for last 24 hours
hcloud CES ShowMetricData \
  --namespace="SYS.ECS" \
  --metric_name="cpu_usage" \
  --dim.0="instance_id,i-12345678" \
  --from=$(date -d '24 hours ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter=average
```

### 2. Troubleshooting High CPU

```bash
# Check CPU usage with process count
hcloud CES ShowMetricData \
  --namespace="SYS.ECS" \
  --metric_name="cpu_usage,proc_rate" \
  --dim.0="instance_id,i-12345678" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter=average
```

### 3. Disk Performance Analysis

```bash
# Analyze disk IO patterns
hcloud CES ShowMetricData \
  --namespace="SYS.ECS" \
  --metric_name="disk_read_bytes_rate,disk_write_bytes_rate,disk_read_requests_rate,disk_write_requests_rate" \
  --dim.0="instance_id,i-12345678,device,vda" \
  --from=$(date -d '6 hours ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter=average
```

### 4. Network Bottleneck Detection

```bash
# Monitor network performance
hcloud CES ShowMetricData \
  --namespace="SYS.ECS" \
  --metric_name="network_incoming_bytes_rate,network_outgoing_bytes_rate,network_incoming_packets_rate,network_outgoing_packets_rate" \
  --dim.0="instance_id,i-12345678,nic,eth0" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=60 \
  --filter=average
```

### 5. Batch Query Multiple Metrics

```bash
# Query multiple metrics at once using BatchListMetricData
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_usage" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="i-12345678" \
  --metrics.2.namespace="SYS.ECS" \
  --metrics.2.metric_name="mem_usage" \
  --metrics.2.dimensions.1.name="instance_id" \
  --metrics.2.dimensions.1.value="i-12345678" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter=average
```

### 6. List Available Metrics

```bash
# List all available metrics for ECS namespace
hcloud CES ListMetrics \
  --namespace="SYS.ECS" \
  --cli-region=cn-north-4

# List metrics for specific instance
hcloud CES ListMetrics \
  --namespace="SYS.ECS" \
  --dim.0="instance_id,i-12345678" \
  --cli-region=cn-north-4
```

## Best Practices

### 1. Metric Selection

- **Always monitor**: cpu_usage, mem_usage, disk_used_percent
- **Performance monitoring**: Add disk and network metrics
- **Troubleshooting**: Include load averages and process rates

### 2. Alerting Thresholds

- **CPU**: Warning > 80%, Critical > 90%
- **Memory**: Warning > 85%, Critical > 95%
- **Disk**: Warning > 80%, Critical > 90%
- **Disk Inodes**: Warning > 80%, Critical > 90%
- **Network Errors**: Critical > 0

### 3. Data Retention

- **Real-time**: 5-minute granularity, 2 days retention
- **Short-term**: 1-hour granularity, 15 days retention
- **Long-term**: 1-day granularity, 1 year retention

### 4. Cost Optimization

- Monitor only necessary metrics
- Use appropriate aggregation periods
- Clean up unused custom metrics
- Consider data export for long-term storage

## Limitations

1. **Minimum granularity**: 1 minute for most metrics
2. **Maximum data points**: 1440 per query
3. **Retention period**: Varies by metric type
4. **Custom metrics**: Limited to 100 metrics per namespace
5. **Query frequency**: Avoid excessive queries to prevent throttling

## References

- [Huawei Cloud CES Documentation](https://support.huaweicloud.com/usermanual-ecs/ecs_03_1001.html)
- [ECS Monitoring Metrics](https://support.huaweicloud.com/intl/en-us/usermanual-ecs/ecs_03_1001.html)
- [CES API Reference](https://support.huaweicloud.com/intl/zh-cn/api-ces/zh-cn_topic_0171212514.html)