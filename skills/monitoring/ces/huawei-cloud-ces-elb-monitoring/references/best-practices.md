# ELB Monitoring Best Practices

## Overview

This document provides best practices for monitoring Huawei Cloud Elastic Load Balance (ELB) instances
using Cloud Eye Service (CES). Following these practices will help you effectively monitor ELB performance,
identify issues early, and optimize resource utilization.

## Monitoring Strategy

### 1. Understand ELB Types

**Dedicated ELB vs Shared ELB Monitoring Differences:**

| Aspect | Dedicated ELB | Shared ELB |
|--------|---------------|------------|
| **Monitoring Dimensions** | Load Balancer, Listener, Backend Server Group, AZ | Load Balancer, Listener only |
| **HTTP Metrics** | Full HTTP status code monitoring | Basic metrics only |
| **Advanced Features** | Traffic mirroring, backend group metrics | Not available |
| **Cost** | Higher | Lower |
| **Use Case** | Enterprise applications, microservices | Simple web applications, testing |

### 2. Define Monitoring Objectives

**Key Monitoring Objectives:**

- **Availability**: Ensure ELB is accepting and forwarding traffic
- **Performance**: Monitor response times and throughput
- **Capacity**: Track resource utilization against limits
- **Errors**: Detect and alert on error conditions
- **Security**: Monitor for suspicious traffic patterns

## Metric Selection Guidelines

### Essential Metrics for All ELB Types

| Priority | Metric | Description | Alert Threshold |
|----------|--------|-------------|-----------------|
| High | `m1_cps` (Concurrent Connections) | Total concurrent connections | > 80% of limit |
| High | `m2_act_conn` (Active Connections) | Active TCP/UDP connections | > 70% of concurrent |
| High | `m7_in_Bps` (Inbound Bandwidth) | Inbound traffic bandwidth | > 80% of bandwidth limit |
| High | `m8_out_Bps` (Outbound Bandwidth) | Outbound traffic bandwidth | > 80% of bandwidth limit |
| Medium | `m4_ncps` (New Connections/sec) | Connection establishment rate | Sudden spike > 3x baseline |
| Medium | `m9_abnormal_host_count` (Abnormal Hosts) | Unhealthy backend servers | > 0 for critical apps |

### Advanced Metrics for Dedicated ELB

| Priority | Metric | Description | Alert Threshold |
|----------|--------|-------------|-----------------|
| High | `elb_http_5xx` (HTTP 5xx Errors) | Server error rate | > 1% of total requests |
| High | `l7_2xx_ratio` (2xx Ratio) | Successful request ratio | < 95% |
| Medium | `elb_http_4xx` (HTTP 4xx Errors) | Client error rate | > 5% of total requests |
| Medium | `m10_l7_in_Bps` (L7 Inbound BW) | Application layer inbound bandwidth | > 80% of limit |
| Low | `mirror_in_traffic` (Mirror Traffic) | Traffic mirroring bandwidth | Based on analysis needs |

## Alert Configuration

### Critical Alerts (Immediate Action Required)

```bash
# Example: HTTP 5xx error rate > 5%
hcloud CES CreateAlarm \
  --alarm_name="elb-http5xx-critical" \
  --alarm_description="HTTP 5xx error rate exceeds 5%" \
  --metric.namespace="SYS.ELB" \
  --metric.metric_name="elb_http_5xx" \
  --metric.dimensions.1.name="lbaas_instance_id" \
  --metric.dimensions.1.value="<loadbalancer-id>" \
  --condition.comparison_operator=">" \
  --condition.value=5 \
  --condition.unit="%" \
  --condition.count=1 \
  --condition.filter="average" \
  --condition.period=300 \
  --alarm_enabled=true \
  --alarm_level=1 \
  --alarm_action_enabled=true \
  --alarm_actions.1.type="notification" \
  --alarm_actions.1.notificationList.1="urn:smn:<region>:<project-id>:<topic-urn>" \
  --cli-region=<region-id>
```

### Warning Alerts (Investigation Required)

```bash
# Example: Concurrent connections > 80% of limit
hcloud CES CreateAlarm \
  --alarm_name="elb-high-connections-warning" \
  --alarm_description="Concurrent connections > 80% of limit" \
  --metric.namespace="SYS.ELB" \
  --metric.metric_name="m1_cps" \
  --metric.dimensions.1.name="lbaas_instance_id" \
  --metric.dimensions.1.value="<loadbalancer-id>" \
  --condition.comparison_operator=">" \
  --condition.value=<80-percent-of-limit> \
  --condition.unit="Count" \
  --condition.count=3 \
  --condition.filter="average" \
  --condition.period=300 \
  --alarm_enabled=true \
  --alarm_level=2 \
  --alarm_action_enabled=true \
  --alarm_actions.1.type="notification" \
  --alarm_actions.1.notificationList.1="urn:smn:<region>:<project-id>:<topic-urn>" \
  --cli-region=<region-id>
```

### Informational Alerts (Trend Monitoring)

```bash
# Example: Inbound bandwidth > 60% of limit for 1 hour
hcloud CES CreateAlarm \
  --alarm_name="elb-bandwidth-trend" \
  --alarm_description="Inbound bandwidth > 60% for 1 hour" \
  --metric.namespace="SYS.ELB" \
  --metric.metric_name="m7_in_Bps" \
  --metric.dimensions.1.name="lbaas_instance_id" \
  --metric.dimensions.1.value="<loadbalancer-id>" \
  --condition.comparison_operator=">" \
  --condition.value=<60-percent-of-limit> \
  --condition.unit="bit/s" \
  --condition.count=12 \
  --condition.filter="average" \
  --condition.period=300 \
  --alarm_enabled=true \
  --alarm_level=3 \
  --cli-region=<region-id>
```

## Monitoring Frequency Recommendations

### Real-time Monitoring (1-minute intervals)

- **Use Case**: Critical alerts, troubleshooting
- **Metrics**: `m1_cps`, `elb_http_5xx`, `m9_abnormal_host_count`
- **Retention**: 24 hours
- **Cost Impact**: Higher

### Performance Monitoring (5-minute intervals)

- **Use Case**: General performance monitoring, capacity planning
- **Metrics**: `m2_act_conn`, `m7_in_Bps`, `m8_out_Bps`, `l7_2xx_ratio`
- **Retention**: 7 days
- **Cost Impact**: Moderate

### Trend Analysis (1-hour intervals)

- **Use Case**: Long-term trends, reporting
- **Metrics**: All metrics aggregated
- **Retention**: 30 days
- **Cost Impact**: Lower

### Historical Analysis (1-day intervals)

- **Use Case**: Monthly/quarterly reports, compliance
- **Metrics**: Key performance indicators
- **Retention**: 1 year
- **Cost Impact**: Minimal

## Dashboard Configuration

### Recommended Dashboard Layout

**Top Section - Overview:**

1. **Current Status**: Overall health indicator
2. **Key Metrics Summary**: Connections, bandwidth, error rates
3. **Active Alerts**: Critical/warning alerts count

**Middle Section - Performance:**

1. **Connection Metrics**: Concurrent/active connections over time
2. **Traffic Metrics**: Inbound/outbound bandwidth
3. **HTTP Metrics** (Dedicated ELB): Status code distribution

**Bottom Section - Details:**

1. **Listener Performance**: Per-listener metrics
2. **Backend Health** (Dedicated ELB): Backend server status
3. **Error Analysis**: Error patterns and trends

### Dashboard Creation Example

```bash
# Create a comprehensive ELB monitoring dashboard
# Note: Actual dashboard creation may require using console or API
# This is a conceptual example

# 1. Connection metrics widget
# 2. Traffic metrics widget  
# 3. HTTP metrics widget (Dedicated ELB)
# 4. Backend health widget (Dedicated ELB)
# 5. Alert status widget
```

## Capacity Planning

### Connection Capacity Planning

```bash
# Monitor connection trends for capacity planning
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="m1_cps" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="<loadbalancer-id>" \
  --from=$(date -d '30 days ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=86400 \
  --filter="max" \
  --cli-region=<region-id>
```

### Bandwidth Capacity Planning

```bash
# Monitor bandwidth trends for capacity planning
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="m7_in_Bps" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="<loadbalancer-id>" \
  --metrics.2.namespace="SYS.ELB" \
  --metrics.2.metric_name="m8_out_Bps" \
  --metrics.2.dimensions.1.name="lbaas_instance_id" \
  --metrics.2.dimensions.1.value="<loadbalancer-id>" \
  --from=$(date -d '30 days ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=86400 \
  --filter="max" \
  --cli-region=<region-id>
```

### Capacity Planning Guidelines

1. **Peak Usage Analysis**: Identify 95th percentile usage
2. **Growth Trends**: Calculate monthly growth rate
3. **Buffer Planning**: Add 20-30% buffer for unexpected spikes
4. **Seasonal Patterns**: Account for seasonal variations
5. **Event Planning**: Plan for marketing events or product launches

## Troubleshooting Scenarios

### Scenario 1: High Error Rate

**Symptoms**: High HTTP 5xx error rate
**Investigation Steps:**

1. **Check backend server health:**

   ```bash
   hcloud CES BatchListMetricData \
     --metrics.1.namespace="SYS.ELB" \
     --metrics.1.metric_name="m9_abnormal_host_count" \
     --metrics.1.dimensions.1.name="lbaas_instance_id" \
     --metrics.1.dimensions.1.value="<loadbalancer-id>" \
     --from=$(date -d '1 hour ago' +%s)000 \
     --to=$(date +%s)000 \
     --period=60 \
     --filter="average" \
     --cli-region=<region-id>
   ```

2. **Check listener-specific errors:**

   ```bash
   hcloud CES BatchListMetricData \
     --metrics.1.namespace="SYS.ELB" \
     --metrics.1.metric_name="elb_http_5xx" \
     --metrics.1.dimensions.1.name="lbaas_instance_id" \
     --metrics.1.dimensions.1.value="<loadbalancer-id>" \
     --metrics.1.dimensions.2.name="lbaas_listener_id" \
     --metrics.1.dimensions.2.value="<listener-id>" \
     --from=$(date -d '1 hour ago' +%s)000 \
     --to=$(date +%s)000 \
     --period=60 \
     --filter="sum" \
     --cli-region=<region-id>
   ```

3. **Check connection metrics:**

   ```bash
   hcloud CES BatchListMetricData \
     --metrics.1.namespace="SYS.ELB" \
     --metrics.1.metric_name="m1_cps" \
     --metrics.1.dimensions.1.name="lbaas_instance_id" \
     --metrics.1.dimensions.1.value="<loadbalancer-id>" \
     --from=$(date -d '1 hour ago' +%s)000 \
     --to=$(date +%s)000 \
     --period=60 \
     --filter="average" \
     --cli-region=<region-id>
   ```

### Scenario 2: Performance Degradation

**Symptoms**: Slow response times, timeouts
**Investigation Steps:**

1. **Check bandwidth utilization:**

   ```bash
   hcloud CES BatchListMetricData \
     --metrics.1.namespace="SYS.ELB" \
     --metrics.1.metric_name="m7_in_Bps" \
     --metrics.1.dimensions.1.name="lbaas_instance_id" \
     --metrics.1.dimensions.1.value="<loadbalancer-id>" \
     --metrics.2.namespace="SYS.ELB" \
     --metrics.2.metric_name="m8_out_Bps" \
     --metrics.2.dimensions.1.name="lbaas_instance_id" \
     --metrics.2.dimensions.1.value="<loadbalancer-id>" \
     --from=$(date -d '1 hour ago' +%s)000 \
     --to=$(date +%s)000 \
     --period=60 \
     --filter="average" \
     --cli-region=<region-id>
   ```

2. **Check connection queue:**

   ```bash
   hcloud CES BatchListMetricData \
     --metrics.1.namespace="SYS.ELB" \
     --metrics.1.metric_name="m3_inact_conn" \
     --metrics.1.dimensions.1.name="lbaas_instance_id" \
     --metrics.1.dimensions.1.value="<loadbalancer-id>" \
     --from=$(date -d '1 hour ago' +%s)000 \
     --to=$(date +%s)000 \
     --period=60 \
     --filter="average" \
     --cli-region=<region-id>
   ```

### Scenario 3: Traffic Spike

**Symptoms**: Sudden increase in traffic
**Investigation Steps:**

1. **Identify traffic pattern:**

   ```bash
   hcloud CES BatchListMetricData \
     --metrics.1.namespace="SYS.ELB" \
     --metrics.1.metric_name="m5_in_packets" \
     --metrics.1.dimensions.1.name="lbaas_instance_id" \
     --metrics.1.dimensions.1.value="<loadbalancer-id>" \
     --from=$(date -d '24 hours ago' +%s)000 \
     --to=$(date +%s)000 \
     --period=300 \
     --filter="average" \
     --cli-region=<region-id>
   ```

2. **Check if it's legitimate traffic:**
   - Compare with historical patterns
   - Check for marketing campaigns or events
   - Verify backend server capacity

## Performance Optimization

### 1. Connection Pool Optimization

**Monitor connection metrics:**

- `m1_cps` (Concurrent Connections): Keep below 80% of limit
- `m2_act_conn` (Active Connections): Optimize based on application needs
- `m3_inact_conn` (Inactive Connections): Adjust connection timeout settings

### 2. Bandwidth Optimization

**Monitor traffic patterns:**

- Identify peak usage times
- Plan for bandwidth upgrades before reaching limits
- Consider traffic shaping for predictable workloads

### 3. Backend Server Optimization

**For Dedicated ELB:**

- Monitor backend server health metrics
- Implement auto-scaling based on `m9_abnormal_host_count`
- Optimize health check intervals

### 4. Listener Configuration Optimization

**Monitor per-listener metrics:**

- Identify underperforming listeners
- Optimize listener configuration based on traffic patterns
- Consider protocol-specific optimizations

## Security Monitoring

### 1. DDoS Detection

**Monitor for unusual patterns:**

- Sudden spikes in `m5_in_packets` or `m6_out_packets`
- Unusual geographic traffic patterns
- High rate of connection attempts (`m4_ncps`)

### 2. Attack Pattern Detection

**Monitor HTTP attack patterns:**

- High rate of HTTP 4xx errors (`elb_http_4xx`)
- Unusual HTTP methods or user agents
- Suspicious URL patterns

### 3. Access Pattern Monitoring

**Establish baselines:**

- Normal connection patterns
- Expected traffic volumes
- Typical error rates

## Cost Optimization

### 1. Right-sizing ELB Instances

**Monitor utilization patterns:**

- Connection utilization (`m1_cps` / ELB limit)
- Bandwidth utilization (`m7_in_Bps` / bandwidth limit)
- Consider downgrading if consistently below 30% utilization

### 2. Monitoring Cost Optimization

**Optimize monitoring configuration:**

- Use appropriate monitoring intervals
- Disable unused metrics
- Aggregate data for long-term storage
- Use alarms instead of continuous monitoring where possible

### 3. Resource Cleanup

**Regularly review:**

- Unused ELB instances
- Idle listeners
- Unattached backend server groups

## Compliance and Reporting

### 1. SLA Monitoring

**Track availability metrics:**

- Uptime percentage
- Error rate compliance
- Response time compliance

### 2. Audit Trail

**Maintain monitoring history:**

- Store metrics for compliance periods
- Document alert responses
- Maintain change logs

### 3. Reporting

**Generate regular reports:**

- Weekly performance reports
- Monthly capacity planning reports
- Quarterly compliance reports

## Automation and Integration

### 1. Automated Remediation

### Example: Auto-scale backend servers**

```bash
# Monitor backend health and trigger scaling
# Pseudo-code example
if abnormal_host_count > threshold:
    trigger_auto_scaling()
    send_notification("Backend scaling triggered")
```

### 2. Integration with CI/CD

**Monitor deployment impact:**

- Baseline metrics before deployment
- Monitor during deployment
- Verify post-deployment performance

### 3. ChatOps Integration

**Send alerts to collaboration tools:**

- Slack/Teams notifications for critical alerts
- Automated incident creation
- Team collaboration on incident response

## Continuous Improvement

### 1. Regular Review Process

**Monthly reviews:**

- Review alert effectiveness
- Adjust thresholds based on trends
- Update monitoring strategy

### 2. Performance Benchmarking

**Compare against benchmarks:**

- Industry standards
- Historical performance
- Business requirements

### 3. Training and Documentation

**Maintain knowledge base:**

- Monitoring runbooks
- Troubleshooting guides
- Team training materials
