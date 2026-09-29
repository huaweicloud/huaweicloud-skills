# Huawei Cloud CLI Commands for ELB Monitoring

## Overview

This document provides detailed command references for Huawei Cloud CLI (hcloud) commands used in the ELB monitoring skill.

## Basic Command Structure

```bash
hcloud <service> <command> [options] [parameters]
```

## ELB Commands

### List ELB Instances

```bash
# List all ELB instances
hcloud ELB ListLoadBalancers --cli-region=<region-id> --limit=50

# List ELB instances with filters
hcloud ELB ListLoadBalancers --cli-region=<region-id> --name.1=<name-pattern>
```

### Get ELB Instance Details

```bash
# Get ELB instance details
hcloud ELB ShowLoadBalancer --loadbalancer_id=<loadbalancer-id> --cli-region=<region-id>

# Get ELB instance specifications
hcloud ELB ShowLoadBalancer --loadbalancer_id=<loadbalancer-id> --cli-region=<region-id> | grep -i "type\|spec"
```

### List ELB Listeners

```bash
# List all listeners for an ELB
hcloud ELB ListListeners --loadbalancer_id.1=<loadbalancer-id> --cli-region=<region-id>

# List specific type of listeners
hcloud ELB ListListeners --loadbalancer_id.1=<loadbalancer-id> --protocol.1=<HTTP/HTTPS/TCP/UDP> --cli-region=<region-id>
```

### List Backend Server Groups (Dedicated ELB only)

```bash
# List backend server groups
hcloud ELB ListPools --loadbalancer_id.1=<loadbalancer-id> --cli-region=<region-id>

# Get backend server group details
hcloud ELB ShowPool --pool_id=<pool-id> --cli-region=<region-id>
```

### List Backend Servers

```bash
# List backend servers in a pool
hcloud ELB ListMembers --pool_id=<pool-id> --cli-region=<region-id>
```

## CES (Cloud Eye Service) Commands

### List Available ELB Metrics

```bash
# List all metrics for ELB namespace
hcloud CES ListMetrics \
  --namespace="SYS.ELB" \
  --cli-region=<region-id>

# List metrics for specific ELB instance
hcloud CES ListMetrics \
  --namespace="SYS.ELB" \
  --dim.0="lbaas_instance_id,<loadbalancer-id>" \
  --cli-region=<region-id>
```

### Query ELB Metric Data

#### Basic Connection Metrics (Both Dedicated and Shared ELB)

```bash
# Query concurrent connections
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="m1_cps" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="<loadbalancer-id>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=<region-id>

# Query active connections
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="m2_act_conn" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="<loadbalancer-id>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=<region-id>

# Query inbound bandwidth
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="m7_in_Bps" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="<loadbalancer-id>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=<region-id>
```

#### Listener-Level Metrics (Both Dedicated and Shared ELB)

```bash
# Query listener-level concurrent connections
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="m1_cps" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="<loadbalancer-id>" \
  --metrics.1.dimensions.2.name="lbaas_listener_id" \
  --metrics.1.dimensions.2.value="<listener-id>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=<region-id>
```

#### HTTP Metrics (Dedicated ELB only)

```bash
# Query HTTP 5xx errors for a listener
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="elb_http_5xx" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="<loadbalancer-id>" \
  --metrics.1.dimensions.2.name="lbaas_listener_id" \
  --metrics.1.dimensions.2.value="<listener-id>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="sum" \
  --cli-region=<region-id>

# Query HTTP 2xx request ratio
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="l7_2xx_ratio" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="<loadbalancer-id>" \
  --metrics.1.dimensions.2.name="lbaas_listener_id" \
  --metrics.1.dimensions.2.value="<listener-id>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=<region-id>
```

#### Backend Server Group Metrics (Dedicated ELB only)

```bash
# Query backend server group health status
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="m9_abnormal_host_count" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="<loadbalancer-id>" \
  --metrics.1.dimensions.2.name="lbaas_pool_id" \
  --metrics.1.dimensions.2.value="<pool-id>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=<region-id>
```

#### Multiple Metrics Query

```bash
# Query multiple metrics at once
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="m1_cps" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="<loadbalancer-id>" \
  --metrics.2.namespace="SYS.ELB" \
  --metrics.2.metric_name="m2_act_conn" \
  --metrics.2.dimensions.1.name="lbaas_instance_id" \
  --metrics.2.dimensions.1.value="<loadbalancer-id>" \
  --metrics.3.namespace="SYS.ELB" \
  --metrics.3.metric_name="m7_in_Bps" \
  --metrics.3.dimensions.1.name="lbaas_instance_id" \
  --metrics.3.dimensions.1.value="<loadbalancer-id>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=<region-id>
```

### Query Historical Data

```bash
# Query data for last 24 hours
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="m1_cps" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="<loadbalancer-id>" \
  --from=$(date -d '24 hours ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=3600 \
  --filter="average" \
  --cli-region=<region-id>

# Query data for last 7 days with daily aggregation
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="m1_cps" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="<loadbalancer-id>" \
  --from=$(date -d '7 days ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=86400 \
  --filter="average" \
  --cli-region=<region-id>
```

## Alarm Management Commands

### List Alarms

```bash
# List all alarms
hcloud CES ListAlarms --cli-region=<region-id>

### List Alarm Templates

```bash
# List alarm templates
hcloud CES ListAlarmTemplates --cli-region=<region-id>

# List ELB-specific alarm templates
hcloud CES ListAlarmTemplates --namespace="SYS.ELB" --cli-region=<region-id>
```


## Utility Commands

### Get Current Timestamp

```bash
# Get current timestamp in milliseconds
date +%s000

# Get timestamp 1 hour ago
date -d '-1 hour' +%s000

# Get timestamp 24 hours ago
date -d '24 hours ago' +%s000

# Get timestamp 7 days ago
date -d '7 days ago' +%s000
```

### Format JSON Output

```bash
# Format JSON output for better readability
hcloud ELB ListLoadBalancers --cli-region=<region-id> --limit=5 | python3 -m json.tool

# Or use jq if available
hcloud ELB ListLoadBalancers --cli-region=<region-id> --limit=5 | jq '.'
```

## Common Parameter Examples

### Region IDs

```bash
# Common region IDs
--cli-region=cn-north-4        # Beijing-4
--cli-region=cn-east-3         # Shanghai-3
--cli-region=cn-south-1        # Guangzhou-1
--cli-region=ap-southeast-1    # Hong Kong
```

### Time Range Examples

```bash
# Last 1 hour (default)
--from=$(date -d '-1 hour' +%s)000 --to=$(date +%s)000

# Last 6 hours
--from=$(date -d '-6 hours' +%s)000 --to=$(date +%s)000

# Last 24 hours
--from=$(date -d '24 hours ago' +%s)000 --to=$(date +%s)000

# Last 7 days
--from=$(date -d '7 days ago' +%s)000 --to=$(date +%s)000

# Specific time range (2024-01-01 00:00:00 to 2024-01-02 00:00:00)
--from=1704067200000 --to=1704153600000
```

### Period Examples

```bash
--period=60      # 1 minute granularity
--period=300     # 5 minutes granularity (default)
--period=1200    # 20 minutes granularity
--period=3600    # 1 hour granularity
--period=86400   # 1 day granularity
```

## Error Handling Examples

### Check Command Syntax

```bash
# Get help for ELB commands
hcloud ELB --help

# Get help for specific ELB command
hcloud ELB ListLoadBalancers --help

# Get help for CES commands
hcloud CES --help

# Get help for specific CES command
hcloud CES BatchListMetricData --help
```

### Handle Permission Errors

```bash
# If permission error occurs, check IAM policies
echo "Permission denied. Please check IAM policies in references/iam-policies.md"
```

### Handle Resource Not Found

```bash
# If ELB not found
echo "Load balancer not found. Please check the loadbalancer-id and region."
```

### Handle Invalid Parameters

```bash
# If invalid parameters
echo "Invalid parameters. Please check command syntax with --help flag."
```
