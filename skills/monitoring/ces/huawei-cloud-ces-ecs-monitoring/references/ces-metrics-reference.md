# Huawei Cloud CES Metrics Reference for ECS

## Overview

Cloud Eye Service (CES) provides comprehensive monitoring metrics for Elastic Cloud Server (ECS) instances. This document lists all available metrics, their meanings, and usage guidelines.

## Metric Namespaces

### SYS.ECS - Base Monitoring (No Agent Required)

Basic monitoring metrics collected by the system at the virtualization layer. Available for all ECS instances without additional software installation.

- **Minimum granularity**: 5 minutes (period=300)
- **Collection period**: XEN instances = 4 minutes; KVM/QingTian instances = 5 minutes
- **Note**: Some metrics (`mem_util`, `disk_util_inband`, `network_*_inband`) require UVP VMTools to be installed on the image. QingTian instances do not support `mem_util`.

### AGT.ECS - OS Monitoring (Agent Required)

OS-level monitoring metrics collected by the Telescope agent. Requires the agent to be installed and running on the ECS instance.

- **Minimum granularity**: 1 minute (period=60)
- **Agent installation check**: See `references/troubleshooting-guide.md` (Section 10: Agent-Related Issues) for agent verification steps.

## Choosing the Right Namespace

- **Use SYS.ECS** when:
  - You need basic monitoring without installing additional software
  - You want metrics available immediately for any ECS instance
  - You need network metrics (all network metrics are SYS.ECS)

- **Use AGT.ECS** when:
  - You need OS-level details (process, load average, TCP connections)
  - You need 1-minute granularity (SYS.ECS minimum is 5 minutes)
  - You need disk usage per mount point
  - You need inode usage monitoring
  - The Telescope agent is installed on the instance

### SYS.ECS to AGT.ECS Metric Fallback

When a SYS.ECS metric returns no data (e.g., UVP VMTools not installed on the image), try the corresponding AGT.ECS metric:

| SYS.ECS Metric | AGT.ECS Equivalent | Notes |
|---|---|---|
| `cpu_util` | `cpu_usage` | AGT.ECS provides more CPU detail (idle, user, system, iowait) |
| `mem_util` | `mem_usedPercent` | AGT.ECS also provides `mem_available`, `mem_free` in GB |
| `disk_util_inband` | `disk_usedPercent` | AGT.ECS requires `mount_point` dimension; SYS.ECS does not |
| `disk_read_bytes_rate` | `disk_agt_read_bytes_rate` | AGT.ECS supports per-disk and per-mount-point granularity |
| `disk_write_bytes_rate` | `disk_agt_write_bytes_rate` | Same as above |

> **Note**: Network metrics (`network_incoming_bytes_rate_inband`, `network_outgoing_bytes_rate_inband`, etc.) only exist in SYS.ECS namespace. There is no AGT.ECS equivalent for network metrics.

## SYS.ECS Metrics (Base Monitoring)

### CPU Metrics

#### cpu_util

- **Description**: CPU usage rate (monitored by the system at the physical machine level)
- **Formula**: Single ECS CPU usage / total CPU cores
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`
- **Minimum Period**: 300 (5 minutes)
- **Alarm Thresholds**:
  - Warning: > 80%
  - Critical: > 95%

#### cpu_credit_usage (T6 instances only)

- **Description**: CPU credit consumption rate of a T6 burstable instance. 1 credit = 1 vCPU at 100% for 1 minute
- **Unit**: Credit
- **Range**: >= 0
- **Dimensions**: `instance_id`

#### cpu_credit_balance (T6 instances only)

- **Description**: CPU credit balance of a T6 burstable instance (accumulated since startup)
- **Unit**: Credit
- **Range**: >= 0
- **Dimensions**: `instance_id`

### Memory Metrics

#### mem_util

- **Description**: Memory usage rate (monitored by the system)
- **Formula**: Used memory / Total memory
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`
- **Minimum Period**: 300 (5 minutes)
- **Alarm Thresholds**:
  - Warning: > 85%
  - Critical: > 95%
- **Note**: Requires UVP VMTools installed on the image. QingTian instances do not support this metric.

### Disk Metrics

#### disk_util_inband

- **Description**: Disk usage rate (monitored by the system)
- **Formula**: Used disk capacity / Total disk capacity
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`
- **Minimum Period**: 300 (5 minutes)
- **Alarm Thresholds**:
  - Warning: > 80%
  - Critical: > 90%
- **Note**: Requires UVP VMTools installed on the image.

#### disk_read_bytes_rate

- **Description**: Disk read bandwidth
- **Formula**: Sum of read bytes / measurement period
- **Unit**: B/s
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 300 (5 minutes)
- **Typical Values**:
  - HDD: 50-150 MB/s
  - SSD: 200-500 MB/s
  - Ultra-high performance: 1+ GB/s

#### disk_write_bytes_rate

- **Description**: Disk write bandwidth
- **Formula**: Sum of written bytes / measurement period
- **Unit**: B/s
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 300 (5 minutes)

#### disk_read_requests_rate

- **Description**: Disk read IOPS (Input/Output Operations Per Second)
- **Unit**: Request/s
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 300 (5 minutes)
- **Typical Values**:
  - HDD: 50-150 IOPS
  - SSD: 3,000-20,000 IOPS
  - Ultra-high performance: 50,000+ IOPS

#### disk_write_requests_rate

- **Description**: Disk write IOPS
- **Unit**: Request/s
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 300 (5 minutes)

### Network Metrics

#### network_incoming_bytes_rate_inband

- **Description**: In-band network incoming rate (bytes received per second from within the ECS)
- **Unit**: B/s
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 300 (5 minutes)
- **Note**: Requires UVP VMTools. Not available with SRIOV.

#### network_outgoing_bytes_rate_inband

- **Description**: In-band network outgoing rate (bytes sent per second from within the ECS)
- **Unit**: B/s
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 300 (5 minutes)
- **Note**: Requires UVP VMTools. Not available with SRIOV.

#### network_incoming_bytes_aggregate_rate

- **Description**: Out-of-band network incoming rate (bytes received per second from virtualization layer)
- **Unit**: B/s
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 300 (5 minutes)
- **Note**: Not available with SRIOV.

#### network_outgoing_bytes_aggregate_rate

- **Description**: Out-of-band network outgoing rate (bytes sent per second from virtualization layer)
- **Unit**: B/s
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 300 (5 minutes)
- **Note**: Not available with SRIOV.

#### network_vm_connections

- **Description**: Total used TCP and UDP connections
- **Unit**: Count
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 300 (5 minutes)

#### network_vm_bandwidth_in

- **Description**: VM inbound bandwidth (total bytes received per second, public + internal)
- **Unit**: B/s
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 300 (5 minutes)

#### network_vm_bandwidth_out

- **Description**: VM outbound bandwidth (total bytes sent per second, public + internal)
- **Unit**: B/s
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 300 (5 minutes)

#### network_vm_pps_in

- **Description**: VM inbound PPS (total packets received per second, public + internal)
- **Unit**: Packet/s
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 300 (5 minutes)

#### network_vm_pps_out

- **Description**: VM outbound PPS (total packets sent per second, public + internal)
- **Unit**: Packet/s
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 300 (5 minutes)

#### network_vm_newconnections

- **Description**: VM new connections rate (TCP, UDP, ICMP)
- **Unit**: connect/s
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 300 (5 minutes)

## AGT.ECS Metrics (OS Monitoring - Agent Required)

### CPU Metrics

#### cpu_usage

- **Description**: CPU usage rate (monitored by the agent)
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)
- **Alarm Thresholds**:
  - Warning: > 80%
  - Critical: > 95%

#### cpu_usage_idle

- **Description**: CPU idle time ratio
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### cpu_usage_user

- **Description**: User space CPU usage rate
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### cpu_usage_system

- **Description**: Kernel space CPU usage rate
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### cpu_usage_iowait

- **Description**: CPU I/O wait time ratio
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### cpu_usage_other

- **Description**: Other CPU usage rate
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### cpu_usage_nice

- **Description**: Nice process CPU usage rate
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### cpu_usage_irq

- **Description**: CPU interrupt time ratio
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### cpu_usage_softirq

- **Description**: CPU soft interrupt time ratio
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

### CPU Load Metrics

> **Note**: Windows does not support CPU load metrics.

#### load_average1

- **Description**: 1-minute single-core average load
- **Unit**: (none)
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)
- **Interpretation**:
  - < CPU cores: Normal
  - = CPU cores: Fully loaded
  - > CPU cores: Overloaded

#### load_average5

- **Description**: 5-minute single-core average load
- **Unit**: (none)
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### load_average15

- **Description**: 15-minute single-core average load
- **Unit**: (none)
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

### Memory Metrics

#### mem_usedPercent

- **Description**: Memory usage rate (monitored by the agent)
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)
- **Alarm Thresholds**:
  - Warning: > 85%
  - Critical: > 95%

#### mem_available

- **Description**: Available memory
- **Unit**: GB
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### mem_free

- **Description**: Free memory
- **Unit**: GB
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### mem_buffers

- **Description**: Buffer memory occupancy
- **Unit**: GB
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### mem_cached

- **Description**: Cache memory occupancy
- **Unit**: GB
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### total_open_files

- **Description**: Total file handles
- **Unit**: Count
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

### Disk Space Metrics

> **Note**: The `mount_point` dimension value is a hash identifier (e.g., `6666cd76f96956469e7be39d750cc7d9`), obtainable via the CES "query host monitoring dimension metric information" API, NOT the actual path like `/`.

#### disk_usedPercent

- **Description**: Disk usage rate (monitored by the agent)
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`, `mount_point`
- **Minimum Period**: 60 (1 minute)
- **Alarm Thresholds**:
  - Warning: > 80%
  - Critical: > 90%

#### disk_free

- **Description**: Free disk space
- **Unit**: GB
- **Range**: >= 0
- **Dimensions**: `instance_id`, `mount_point`
- **Minimum Period**: 60 (1 minute)

#### disk_total

- **Description**: Total disk space
- **Unit**: GB
- **Range**: >= 0
- **Dimensions**: `instance_id`, `mount_point`
- **Minimum Period**: 60 (1 minute)

#### disk_used

- **Description**: Used disk space
- **Unit**: GB
- **Range**: >= 0
- **Dimensions**: `instance_id`, `mount_point`
- **Minimum Period**: 60 (1 minute)

### Disk I/O Metrics

> **Note**: Disk I/O metrics support two dimension combinations: `instance_id,disk` or `instance_id,mount_point`. The `disk` dimension value is the disk identifier (e.g., `vda`, `vdb`).

#### disk_agt_read_bytes_rate

- **Description**: Disk read rate (monitored by the agent)
- **Unit**: B/s
- **Range**: >= 0
- **Dimensions**: `instance_id`,`disk` or `instance_id`,`mount_point`
- **Minimum Period**: 60 (1 minute)

#### disk_agt_write_bytes_rate

- **Description**: Disk write rate (monitored by the agent)
- **Unit**: B/s
- **Range**: >= 0
- **Dimensions**: `instance_id`,`disk` or `instance_id`,`mount_point`
- **Minimum Period**: 60 (1 minute)

#### disk_agt_read_requests_rate

- **Description**: Disk read operation rate (IOPS)
- **Unit**: Request/s
- **Range**: >= 0
- **Dimensions**: `instance_id`,`disk` or `instance_id`,`mount_point`
- **Minimum Period**: 60 (1 minute)

#### disk_agt_write_requests_rate

- **Description**: Disk write operation rate (IOPS)
- **Unit**: Request/s
- **Range**: >= 0
- **Dimensions**: `instance_id`,`disk` or `instance_id`,`mount_point`
- **Minimum Period**: 60 (1 minute)

#### disk_readTime

- **Description**: Read operation average latency
- **Unit**: ms/Count
- **Range**: >= 0
- **Dimensions**: `instance_id`,`disk` or `instance_id`,`mount_point`
- **Minimum Period**: 60 (1 minute)

#### disk_writeTime

- **Description**: Write operation average latency
- **Unit**: ms/Count
- **Range**: >= 0
- **Dimensions**: `instance_id`,`disk` or `instance_id`,`mount_point`
- **Minimum Period**: 60 (1 minute)

#### disk_ioUtils

- **Description**: Disk I/O usage rate
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`,`disk` or `instance_id`,`mount_point`
- **Minimum Period**: 60 (1 minute)

#### disk_queue_length

- **Description**: Average disk queue length
- **Unit**: Count
- **Range**: >= 0
- **Dimensions**: `instance_id`,`disk` or `instance_id`,`mount_point`
- **Minimum Period**: 60 (1 minute)

#### disk_device_used_percent

- **Description**: Block device usage rate
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`,`disk`
- **Minimum Period**: 60 (1 minute)

### File System Metrics

> **Note**: Windows does not support file system metrics.

#### disk_fs_rwstate

- **Description**: File system read/write state
- **Unit**: (none)
- **Range**: 0 = read-write, 1 = read-only
- **Dimensions**: `instance_id`, `mount_point`
- **Minimum Period**: 60 (1 minute)

#### disk_inodesTotal

- **Description**: Inode space size
- **Unit**: Count
- **Range**: >= 0
- **Dimensions**: `instance_id`, `mount_point`
- **Minimum Period**: 60 (1 minute)

#### disk_inodesUsed

- **Description**: Inode used space
- **Unit**: Count
- **Range**: >= 0
- **Dimensions**: `instance_id`, `mount_point`
- **Minimum Period**: 60 (1 minute)

#### disk_inodesUsedPercent

- **Description**: Inode usage ratio
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`, `mount_point`
- **Minimum Period**: 60 (1 minute)
- **Alarm Thresholds**:
  - Warning: > 80%
  - Critical: > 90%

### Network Card Metrics

#### net_bitRecv

- **Description**: NIC inbound bandwidth
- **Unit**: bit/s
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### net_bitSent

- **Description**: NIC outbound bandwidth
- **Unit**: bit/s
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### net_packetRecv

- **Description**: NIC packet receive rate
- **Unit**: Counts/s
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### net_packetSent

- **Description**: NIC packet send rate
- **Unit**: Counts/s
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### net_errin

- **Description**: Receive error packet rate
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)
- **Alarm Threshold**: > 0 (any errors should be investigated)

#### net_errout

- **Description**: Send error packet rate
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)
- **Alarm Threshold**: > 0

#### net_dropin

- **Description**: Receive drop packet rate
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### net_dropout

- **Description**: Send drop packet rate
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

### TCP Connection Metrics

#### net_tcp_total

- **Description**: Total TCP connections
- **Unit**: Count
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### net_tcp_established

- **Description**: TCP connections in ESTABLISHED state
- **Unit**: Count
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### net_tcp_time_wait

- **Description**: TCP connections in TIME_WAIT state
- **Unit**: Count
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### net_tcp_close_wait

- **Description**: TCP connections in CLOSE_WAIT state
- **Unit**: Count
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### net_tcp_retrans

- **Description**: TCP retransmission rate
- **Unit**: %
- **Range**: 0-100
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

### Process Metrics

#### proc_running_count

- **Description**: Running process count
- **Unit**: Count
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### proc_idle_count

- **Description**: Idle process count
- **Unit**: Count
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### proc_zombie_count

- **Description**: Zombie process count
- **Unit**: Count
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)
- **Alarm Threshold**: > 0 (any zombie processes should be investigated)

#### proc_blocked_count

- **Description**: Blocked process count
- **Unit**: Count
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

#### proc_total_count

- **Description**: System process count
- **Unit**: Count
- **Range**: >= 0
- **Dimensions**: `instance_id`
- **Minimum Period**: 60 (1 minute)

## Metric Dimensions

### Dimension Format

**For ShowMetricData (GET API)**: Use separate `--dim.N` parameters:

```bash
# Single dimension
--dim.0="instance_id,<uuid>"

# Two dimensions (separate entries, NOT comma-concatenated)
--dim.0="instance_id,<uuid>" --dim.1="mount_point,<hash>"
```

**For BatchListMetricData (POST API)**: Use indexed name/value pairs:

```bash
# Single dimension
--metrics.1.dimensions.1.name="instance_id"
--metrics.1.dimensions.1.value="<uuid>"

# Two dimensions
--metrics.1.dimensions.1.name="instance_id"
--metrics.1.dimensions.1.value="<uuid>"
--metrics.1.dimensions.2.name="mount_point"
--metrics.1.dimensions.2.value="<hash>"
```

### Instance ID Format

The `instance_id` value is the ECS UUID (e.g., `3d65c1ac-9a9f-4c5f-a054-35184a087bb2`), NOT the `i-xxxxxxxx` format.

### mount_point Format (AGT.ECS)

The `mount_point` value is a hash identifier (e.g., `6666cd76f96956469e7be39d750cc7d9`), NOT the actual mount path like `/`. Obtain the hash value via the CES "query host monitoring dimension metric information" API.

### disk Dimension (AGT.ECS)

The `disk` dimension value is the disk identifier (e.g., `vda`, `vdb`).

## Common Monitoring Scenarios

### 1. Performance Baseline (SYS.ECS)

```bash
# Get baseline CPU and memory metrics for last 24 hours
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-uuid>" \
  --metrics.2.namespace="SYS.ECS" \
  --metrics.2.metric_name="mem_util" \
  --metrics.2.dimensions.1.name="instance_id" \
  --metrics.2.dimensions.1.value="<instance-uuid>" \
  --from=$(date -d '24 hours ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=3600 \
  --filter=average \
  --cli-region=<region-id>
```

### 2. Troubleshooting High CPU (AGT.ECS - Agent Required)

```bash
# Check CPU usage with load average
hcloud CES BatchListMetricData \
  --metrics.1.namespace="AGT.ECS" \
  --metrics.1.metric_name="cpu_usage" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-uuid>" \
  --metrics.2.namespace="AGT.ECS" \
  --metrics.2.metric_name="load_average1" \
  --metrics.2.dimensions.1.name="instance_id" \
  --metrics.2.dimensions.1.value="<instance-uuid>" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=60 \
  --filter=average \
  --cli-region=<region-id>
```

### 3. Disk Performance Analysis (SYS.ECS)

```bash
# Analyze disk IO patterns
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="disk_read_bytes_rate" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-uuid>" \
  --metrics.2.namespace="SYS.ECS" \
  --metrics.2.metric_name="disk_write_bytes_rate" \
  --metrics.2.dimensions.1.name="instance_id" \
  --metrics.2.dimensions.1.value="<instance-uuid>" \
  --metrics.3.namespace="SYS.ECS" \
  --metrics.3.metric_name="disk_read_requests_rate" \
  --metrics.3.dimensions.1.name="instance_id" \
  --metrics.3.dimensions.1.value="<instance-uuid>" \
  --metrics.4.namespace="SYS.ECS" \
  --metrics.4.metric_name="disk_write_requests_rate" \
  --metrics.4.dimensions.1.name="instance_id" \
  --metrics.4.dimensions.1.value="<instance-uuid>" \
  --from=$(date -d '6 hours ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter=average \
  --cli-region=<region-id>
```

### 4. Network Bottleneck Detection (SYS.ECS)

```bash
# Monitor network performance
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="network_incoming_bytes_rate_inband" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-uuid>" \
  --metrics.2.namespace="SYS.ECS" \
  --metrics.2.metric_name="network_outgoing_bytes_rate_inband" \
  --metrics.2.dimensions.1.name="instance_id" \
  --metrics.2.dimensions.1.value="<instance-uuid>" \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter=average \
  --cli-region=<region-id>
```

### 5. Disk Usage Monitoring (AGT.ECS - Agent Required)

```bash
# Check disk usage per mount point
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
  --filter=average \
  --cli-region=<region-id>
```

### 6. List Available Metrics

```bash
# List all available metrics for ECS namespace
hcloud CES ListMetrics \
  --namespace="SYS.ECS" \
  --cli-region=<region-id>

# List metrics for specific instance
hcloud CES ListMetrics \
  --namespace="SYS.ECS" \
  --dim.0="instance_id,<instance-uuid>" \
  --cli-region=<region-id>
```

## Alerting Thresholds Summary

For alerting thresholds and strategy details, see `references/best-practices.md`.

## Best Practices

For metric selection guidelines, data retention policies, and cost optimization, see `references/best-practices.md`.

## Limitations

1. **SYS.ECS minimum granularity**: 5 minutes (period=300)
2. **AGT.ECS minimum granularity**: 1 minute (period=60)
3. **Maximum data points**: 1440 per query
4. **Retention period**: Varies by metric type
5. **Query frequency**: 500 calls/minute for ShowMetricData/BatchListMetricData; 300 calls/minute for ListMetrics
6. **Batch query limit**: Max 500 metrics per BatchListMetricData request
7. **Dimensions**: Max 4 dimensions per metric

## References

- [Huawei Cloud CES Documentation](https://support.huaweicloud.com/usermanual-ecs/ecs_03_1001.html)
- [ECS Monitoring Metrics](https://support.huaweicloud.com/intl/en-us/usermanual-ecs/ecs_03_1001.html)
- [CES API Reference](https://support.huaweicloud.com/api-ces/ces_03_0041.html)
