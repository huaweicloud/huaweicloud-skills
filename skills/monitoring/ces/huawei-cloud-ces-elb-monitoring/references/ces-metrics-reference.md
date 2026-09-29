# CES Metrics Reference for ELB Monitoring

## Overview

This document provides a comprehensive reference of Cloud Eye Service (CES) metrics available
for Elastic Load Balance (ELB) monitoring. The metrics are categorized by ELB type
(Dedicated vs Shared) and monitoring dimension.

## Namespace

All ELB metrics use the namespace: **`SYS.ELB`**

## Metric Dimensions

ELB metrics support multiple dimensions for granular monitoring:

### Dimension Hierarchy

1. **Load Balancer Level** (`lbaas_instance_id`)
   - Top-level metrics for the entire ELB instance
   - Available for both Dedicated and Shared ELB

2. **Listener Level** (`lbaas_listener_id`)
   - Protocol-specific metrics
   - Available for both Dedicated and Shared ELB

3. **Backend Server Group Level** (`lbaas_pool_id`)
   - Backend server health and performance metrics
   - **Dedicated ELB only**

4. **Availability Zone Level** (`lbaas_az`)
   - AZ-specific traffic distribution
   - **Dedicated ELB only**

## Common Metrics (Both Dedicated and Shared ELB)

### Connection Metrics

| Metric ID | Metric Name | Description | Unit | Monitoring Period | Dimensions |
|-----------|-------------|-------------|------|-------------------|------------|
| `m1_cps` | Concurrent Connections | Number of concurrent TCP/UDP connections | Count | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `m2_act_conn` | Active Connections | Number of active TCP/UDP connections | Count | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `m3_inact_conn` | Inactive Connections | Number of inactive TCP/UDP connections | Count | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `m4_ncps` | New Connections Per Second | Rate of new connections established | Count/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |

### Traffic Metrics

| Metric ID | Metric Name | Description | Unit | Monitoring Period | Dimensions |
|-----------|-------------|-------------|------|-------------------|------------|
| `m5_in_packets` | Inbound Packet Rate | Rate of inbound packets | Count/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `m6_out_packets` | Outbound Packet Rate | Rate of outbound packets | Count/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `m7_in_Bps` | Inbound Bandwidth | Inbound traffic bandwidth | bit/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `m8_out_Bps` | Outbound Bandwidth | Outbound traffic bandwidth | bit/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |

### Error Metrics

| Metric ID | Metric Name | Description | Unit | Monitoring Period | Dimensions |
|-----------|-------------|-------------|------|-------------------|------------|
| `m9_abnormal_host_count` | Abnormal Host Count | Number of abnormal backend servers | Count | 1 minute | `lbaas_instance_id`<br>`lbaas_pool_id` |

## Dedicated ELB Only Metrics

### HTTP/HTTPS Metrics

| Metric ID | Metric Name | Description | Unit | Monitoring Period | Dimensions |
|-----------|-------------|-------------|------|-------------------|------------|
| `m10_l7_in_Bps` | L7 Inbound Bandwidth | Layer 7 inbound bandwidth | bit/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `m11_l7_out_Bps` | L7 Outbound Bandwidth | Layer 7 outbound bandwidth | bit/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `m12_l7_in_pps` | L7 Inbound Packet Rate | Layer 7 inbound packet rate | Count/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `m13_l7_out_pps` | L7 Outbound Packet Rate | Layer 7 outbound packet rate | Count/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `m14_l7_qps` | L7 Query Per Second | Layer 7 queries per second | Count/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |

### HTTP Status Code Metrics

| Metric ID | Metric Name | Description | Unit | Monitoring Period | Dimensions |
|-----------|-------------|-------------|------|-------------------|------------|
| `elb_http_2xx` | HTTP 2xx Status Codes | Count of HTTP 2xx responses | Count/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `elb_http_3xx` | HTTP 3xx Status Codes | Count of HTTP 3xx responses | Count/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `elb_http_4xx` | HTTP 4xx Status Codes | Count of HTTP 4xx responses | Count/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `elb_http_5xx` | HTTP 5xx Status Codes | Count of HTTP 5xx responses | Count/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `elb_http_404` | HTTP 404 Status Codes | Count of HTTP 404 responses | Count/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `elb_http_502` | HTTP 502 Status Codes | Count of HTTP 502 responses | Count/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `elb_http_503` | HTTP 503 Status Codes | Count of HTTP 503 responses | Count/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `elb_http_504` | HTTP 504 Status Codes | Count of HTTP 504 responses | Count/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |

### HTTP Request Ratio Metrics

| Metric ID | Metric Name | Description | Unit | Monitoring Period | Dimensions |
|-----------|-------------|-------------|------|-------------------|------------|
| `l7_2xx_ratio` | L7 2xx Request Ratio | Ratio of HTTP 2xx responses | % | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `l7_4xx_ratio` | L7 4xx Request Ratio | Ratio of HTTP 4xx responses | % | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `l7_5xx_ratio` | L7 5xx Request Ratio | Ratio of HTTP 5xx responses | % | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |

### Traffic Mirroring Metrics

| Metric ID | Metric Name | Description | Unit | Monitoring Period | Dimensions |
|-----------|-------------|-------------|------|-------------------|------------|
| `mirror_in_traffic` | Inbound Traffic Mirror Bandwidth | Bandwidth of inbound traffic mirroring | bit/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `mirror_out_traffic` | Outbound Traffic Mirror Bandwidth | Bandwidth of outbound traffic mirroring | bit/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `mirror_in_packets` | Inbound Traffic Mirror Packet Rate | Packet rate of inbound traffic mirroring | Count/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `mirror_out_packets` | Outbound Traffic Mirror Packet Rate | Packet rate of outbound traffic mirroring | Count/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |

### Backend Server Group Metrics

| Metric ID | Metric Name | Description | Unit | Monitoring Period | Dimensions |
|-----------|-------------|-------------|------|-------------------|------------|
| `m1e_server_connections` | Server Connections | Number of connections to backend servers | Count | 1 minute | `lbaas_instance_id`<br>`lbaas_pool_id` |
| `m1f_lvs_connections` | LVS Connections | Number of LVS connections | Count | 1 minute | `lbaas_instance_id`<br>`lbaas_pool_id` |

### Client Connection Metrics

| Metric ID | Metric Name | Description | Unit | Monitoring Period | Dimensions |
|-----------|-------------|-------------|------|-------------------|------------|
| `m21_client_rtt` | Client Round-Trip Time | Client connection round-trip time | ms | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |

### Network Traffic Metrics

| Metric ID | Metric Name | Description | Unit | Monitoring Period | Dimensions |
|-----------|-------------|-------------|------|-------------------|------------|
| `m22_in_traffic` | Inbound Traffic | Total inbound traffic | Byte | 1 minute | `lbaas_instance_id` |
| `m23_out_traffic` | Outbound Traffic | Total outbound traffic | Byte | 1 minute | `lbaas_instance_id` |
| `m26_in_packets` | Inbound Packets | Total inbound packets | Count | 1 minute | `lbaas_instance_id` |
| `m27_out_packets` | Outbound Packets | Total outbound packets | Count | 1 minute | `lbaas_instance_id` |

## Protocol-Specific Metrics

### TCP Protocol Metrics

| Metric ID | Metric Name | Description | Unit | Monitoring Period | Dimensions |
|-----------|-------------|-------------|------|-------------------|------------|
| `tcp_connections` | TCP Connections | Number of TCP connections | Count | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `tcp_new_connections` | TCP New Connections | Rate of new TCP connections | Count/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |

### UDP Protocol Metrics

| Metric ID | Metric Name | Description | Unit | Monitoring Period | Dimensions |
|-----------|-------------|-------------|------|-------------------|------------|
| `udp_connections` | UDP Connections | Number of UDP connections | Count | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |
| `udp_new_connections` | UDP New Connections | Rate of new UDP connections | Count/s | 1 minute | `lbaas_instance_id`<br>`lbaas_listener_id` |

## Metric Aggregation Methods

CES supports the following aggregation methods for metrics:

| Aggregation Method | Description | Use Case |
|-------------------|-------------|----------|
| `average` | Average value over the period | General monitoring, trend analysis |
| `max` | Maximum value over the period | Peak load analysis, capacity planning |
| `min` | Minimum value over the period | Baseline performance analysis |
| `sum` | Sum of values over the period | Total traffic/connections analysis |
| `variance` | Variance over the period | Stability analysis, anomaly detection |

## Monitoring Periods

| Period (seconds) | Description | Use Case |
|------------------|-------------|----------|
| `60` | 1 minute | Real-time monitoring, alerting |
| `300` | 5 minutes | Default monitoring, general analysis |
| `900` | 15 minutes | Performance trend analysis |
| `3600` | 1 hour | Daily trend analysis |
| `86400` | 1 day | Long-term trend analysis |

## ELB Type Comparison

### Dedicated ELB Metrics Availability

| Metric Category | Available | Notes |
|----------------|-----------|-------|
| Connection Metrics | ✅ | Full support |
| Traffic Metrics | ✅ | Full support |
| HTTP/HTTPS Metrics | ✅ | Full support for L7 protocols |
| HTTP Status Codes | ✅ | Detailed status code monitoring |
| Traffic Mirroring | ✅ | Advanced feature |
| Backend Server Group | ✅ | Per-pool monitoring |
| Availability Zone | ✅ | AZ-level monitoring |

### Shared ELB Metrics Availability

| Metric Category | Available | Notes |
|----------------|-----------|-------|
| Connection Metrics | ✅ | Basic connection metrics only |
| Traffic Metrics | ✅ | Basic traffic metrics only |
| HTTP/HTTPS Metrics | ❌ | Not available |
| HTTP Status Codes | ❌ | Not available |
| Traffic Mirroring | ❌ | Not available |
| Backend Server Group | ❌ | Not available |
| Availability Zone | ❌ | Not available |

## Common Monitoring Scenarios

### Scenario 1: Basic Health Check

```bash
# Monitor concurrent connections and error rate
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="m1_cps" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="lb-12345678" \
  --metrics.2.namespace="SYS.ELB" \
  --metrics.2.metric_name="m9_abnormal_host_count" \
  --metrics.2.dimensions.1.name="lbaas_instance_id" \
  --metrics.2.dimensions.1.value="lb-12345678" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=cn-north-4
```

### Scenario 2: HTTP Performance Monitoring (Dedicated ELB)

```bash
# Monitor HTTP status codes and request ratio
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="elb_http_5xx" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="lb-12345678" \
  --metrics.1.dimensions.2.name="lbaas_listener_id" \
  --metrics.1.dimensions.2.value="listener-12345678" \
  --metrics.2.namespace="SYS.ELB" \
  --metrics.2.metric_name="l7_2xx_ratio" \
  --metrics.2.dimensions.1.name="lbaas_instance_id" \
  --metrics.2.dimensions.1.value="lb-12345678" \
  --metrics.2.dimensions.2.name="lbaas_listener_id" \
  --metrics.2.dimensions.2.value="listener-12345678" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=cn-north-4
```

### Scenario 3: Traffic Analysis

```bash
# Monitor inbound/outbound traffic
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="m7_in_Bps" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="lb-12345678" \
  --metrics.2.namespace="SYS.ELB" \
  --metrics.2.metric_name="m8_out_Bps" \
  --metrics.2.dimensions.1.name="lbaas_instance_id" \
  --metrics.2.dimensions.1.value="lb-12345678" \
  --from=$(date -d '-24 hours' +%s)000 \
  --to=$(date +%s)000 \
  --period=3600 \
  --filter="average" \
  --cli-region=cn-north-4
```

## Metric Threshold Recommendations

### Connection Metrics

- **Concurrent Connections (`m1_cps`)**: Warning > 80% of ELB specification limit
- **Active Connections (`m2_act_conn`)**: Warning > 70% of concurrent connections
- **New Connections Per Second (`m4_ncps`)**: Alert if sudden spike > 3x baseline

### Traffic Metrics

- **Inbound/Outbound Bandwidth**: Warning > 80% of bandwidth limit
- **Packet Rate**: Monitor for abnormal spikes indicating DDoS attacks

### HTTP Metrics (Dedicated ELB)

- **HTTP 5xx Error Rate**: Warning > 1%, Critical > 5%
- **HTTP 2xx Ratio**: Warning < 95%, Critical < 90%
- **HTTP 4xx Ratio**: Warning > 5%, Critical > 10%

### Backend Health

- **Abnormal Host Count (`m9_abnormal_host_count`)**: Warning > 0, Critical > 20% of backend servers

## Troubleshooting Common Issues

### Issue 1: No Metrics Available

**Symptoms**: Query returns empty data or "metric not found"
**Possible Causes**:

1. ELB instance not in running state
2. No traffic passing through ELB during monitoring period
3. Insufficient IAM permissions
4. Wrong namespace or metric name

**Solutions**:

1. Check ELB instance status: `hcloud ELB ShowLoadBalancer`
2. Verify traffic is flowing through ELB
3. Check IAM permissions: `references/iam-policies.md`
4. Verify metric name and namespace

### Issue 2: Permission Denied

**Symptoms**: "Access denied" or "Insufficient permissions" errors
**Solutions**:

1. Verify IAM policy attachment
2. Check if user has required permissions
3. Use `hcloud configure list` to verify credentials

### Issue 3: Invalid Dimensions

**Symptoms**: "Invalid dimension" or "Dimension not found" errors
**Solutions**:

1. Verify ELB instance ID exists
2. Check listener ID for listener-level metrics
3. Ensure correct dimension names (e.g., `lbaas_instance_id`, not `instance_id`)

### Issue 4: Time Range Issues

**Symptoms**: No data returned for specified time range
**Solutions**:

1. Check if ELB was created after start time
2. Verify time format (Unix timestamp in milliseconds)
3. Ensure end time is after start time

## Best Practices

### 1. Metric Selection

- Start with basic metrics: `m1_cps`, `m2_act_conn`, `m7_in_Bps`, `m8_out_Bps`
- Add HTTP metrics for web applications (Dedicated ELB only)
- Monitor backend health: `m9_abnormal_host_count`

### 2. Monitoring Frequency

- Real-time monitoring: 1-minute period
- Performance analysis: 5-minute period
- Trend analysis: 1-hour or 1-day period

### 3. Alert Configuration

- Set alerts for critical metrics (5xx errors, high connection count)
- Use appropriate thresholds based on ELB specification
- Configure notification channels (email, SMS, webhook)

### 4. Data Retention

- Real-time data: 24 hours
- Aggregated data (5-minute): 7 days
- Aggregated data (1-hour): 30 days
- Aggregated data (1-day): 1 year

## References

- Huawei Cloud official documentation(Dedicated ELB): <https://support.huaweicloud.com/usermanual-elb/elb_ug_jk_0001.html>
- Huawei Cloud official documentation(Shared ELB): <https://support.huaweicloud.com/usermanual-elb/elb_ug_sjk_0001.html>
