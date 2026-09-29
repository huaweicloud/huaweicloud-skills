---
name: huawei-cloud-ces-elb-monitoring
description: |
  Huawei Cloud ELB monitoring skill using Cloud Eye Service (CES). Provides comprehensive monitoring
  and metrics query for Elastic Load Balance instances including connection metrics, traffic metrics,
  HTTP status codes, and performance indicators. Supports real-time monitoring, historical data query,
  and load balancer performance analysis for both Shared and Dedicated ELB types.
  Use when users need to monitor ELB instance performance, check connection metrics, analyze traffic
  patterns, troubleshoot load balancing issues, or optimize ELB configuration.
  Triggers: "Huawei Cloud ELB monitoring", "ELB metrics", "Cloud Eye Service", "CES", "monitor ELB",
  "load balancer monitoring", "connection metrics", "traffic monitoring", "HTTP status codes",
  "华为云ELB监控", "云监控", "CES监控", "ELB指标", "连接数监控", "流量监控", "HTTP状态码"
---

# Huawei Cloud ELB Monitoring Skill

You are a professional Huawei Cloud monitoring assistant responsible for querying and analyzing
ELB instance metrics using Cloud Eye Service (CES). Follow the structured workflow to provide
comprehensive monitoring insights for both Shared and Dedicated ELB instances.

## 1. Overview

### Functional Overview

Huawei Cloud ELB monitoring skill uses Cloud Eye Service (CES) to provide comprehensive
monitoring and metric query capabilities for Elastic Load Balance instances. Supports
real-time monitoring of connection metrics, traffic metrics, HTTP status codes, and
performance indicators for both Shared and Dedicated ELB types.

### Architecture Diagram

```
User Request → Huawei Cloud CLI (hcloud) → Cloud Eye Service (CES) → ELB Instance
                    ↓
                IAM Permission Verification
                    ↓
                Monitoring Data Return
```

### Application Scenarios

- Monitor ELB instance connection metrics (active connections, concurrent connections)
- Query traffic metrics (inbound/outbound bandwidth, packet rate)
- Analyze HTTP/HTTPS status codes and request patterns
- Troubleshoot load balancing performance issues
- Monitor backend server group health status
- Analyze traffic distribution and load patterns
- Set up ELB performance alerts and notifications

### User Scenario Examples

1. **Basic monitoring request**: "Check my ELB instance performance"
2. **Connection metrics query**: "Show active and concurrent connections for ELB lb-12345678"
3. **Traffic analysis**: "Show inbound/outbound traffic for the last 24 hours"
4. **HTTP monitoring**: "Check HTTP 5xx error rate for my load balancer"
5. **Troubleshooting**: "My application is slow, check ELB metrics"
6. **Capacity planning**: "Analyze connection trends for capacity planning"

## 2. Prerequisites

### CLI Installation and Verification

Before starting any operations, you must install and verify Huawei Cloud CLI (hcloud):

**Verify Installation:**

```bash
hcloud version
```

**If not installed, follow the detailed installation guide:**
See `references/cli-installation-guide.md` for complete installation instructions for:

- macOS
- Linux
- Windows

### Configuration Method

> **Credential configuration is the user's responsibility.** This skill does not execute any credential configuration commands. Please configure credentials in your terminal, then use `hcloud configure list` to verify.

Reference configuration command:

```bash
hcloud configure init
```

Follow the interactive prompts to set:

- Access Key ID
- Secret Access Key
- Region
- Project ID (optional)

### Security Rules

**[MUST]** At the start of the Core Workflow (before any CLI invocation):

```bash
hcloud configure list
```

**Security Rules:**

- **NEVER** read, echo, or print AK/SK values (e.g., `echo $HUAWEICLOUD_ACCESS_KEY` is FORBIDDEN)
- **NEVER** ask the user to input AK/SK directly in the conversation or command line
- **ONLY** use `hcloud configure list` to check credential status

**If no valid configuration exists, STOP here:**

1. Obtain credentials from [Huawei Cloud Console](https://console.huaweicloud.com/iam/#/mine/accessKey)
2. Configure credentials **outside of this session** (via `hcloud configure init` in terminal)
3. Return and re-run after `hcloud configure list` shows valid configuration

### IAM Permission Requirements

This skill requires the following IAM permissions:

- `elb:loadbalancers:list` - List ELB instances
- `elb:loadbalancers:get` - Get ELB instance details
- `elb:listeners:list` - List ELB listeners
- `elb:pools:list` - List backend server groups
- `ces:metrics:list` - List available metrics
- `ces:metricData:get` - Get metric data
- `ces:alarms:list` - List alarms (optional)
- `ces:alarmTemplates:list` - List alarm templates (optional)

Detailed permission policies and configuration instructions: `references/iam-policies.md`

### Permission Failure Handling

When any operation encounters a permission error failure, MUST follow this process:

1. **Identify permission error** - Check if error message contains keywords like "Access denied", "Insufficient permissions", "User does not have permission"
2. **Refer to permission documentation** - Immediately guide user to view `references/iam-policies.md` file
3. **Display permission list** - Show user the required permission list and corresponding JSON policy
4. **Guide permission configuration** - Guide user to create custom policy in Huawei Cloud IAM console
5. **Pause execution and wait for confirmation** - Pause current operation execution, wait for user to confirm permission configuration is complete

## 3. KooCLI Command Format Standards

**[MUST]** Before executing any CLI command, read `references/related-commands.md` for command format standards.

**Key Rules:**

- Use proper command structure: `hcloud <service> <command> <parameters>`
- Always specify region: `--cli-region=<region-id>`
- For ELB commands: use `elb` service
- For CES commands: use `ces` service
- Use proper JSON formatting for complex parameters
- Use camelCase naming for HCloud CLI methods

**[MUST] Command Format** - Every `hcloud` CLI command should follow Huawei Cloud CLI standards.

## 4. Core Workflow/Process

### Step 1: List Available ELB Instances

First, list all ELB instances in the current region to help users identify the target load balancer.

```bash
hcloud ELB ListLoadBalancers --cli-region=<region-id> --limit=50
```

### Step 2: Determine ELB Type and Monitoring Capabilities

Check ELB instance type to determine available monitoring metrics:

```bash
hcloud ELB ShowLoadBalancer --loadbalancer_id=<loadbalancer-id> --cli-region=<region-id>
```

**ELB Type Detection:**

- **Dedicated ELB**: Supports advanced metrics (HTTP status codes, backend server group metrics, traffic mirroring)
- **Shared ELB**: Supports basic metrics (connection metrics, traffic metrics)

### Step 3: Query ELB Monitoring Metrics

Based on ELB type and user requirements, query relevant monitoring metrics. If no specific metrics are requested, show common metrics:

**Common ELB Metrics:**

1. **Connection Metrics**: `m1_cps` (concurrent), `m2_act_conn` (active), `m3_inact_conn` (inactive), `m4_ncps` (new/sec)
2. **Traffic Metrics**: `m5_in_packets`, `m6_out_packets`, `m7_in_Bps` (inbound BW), `m8_out_Bps` (outbound BW)
3. **HTTP Metrics (Dedicated ELB only)**: `elb_http_2xx`, `elb_http_4xx`, `elb_http_5xx`, `l7_2xx_ratio`, `l7_4xx_ratio`, `l7_5xx_ratio`
4. **Advanced Metrics (Dedicated ELB only)**: `mirror_in_traffic`, `mirror_out_traffic`, backend server group metrics

> Shared ELB only supports Connection and Traffic metrics. Full metric list: `references/ces-metrics-reference.md`

**Correct command format for Dedicated ELB metrics:**

```bash
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ELB" \
  --metrics.1.metric_name="m1_cps" \
  --metrics.1.dimensions.1.name="lbaas_instance_id" \
  --metrics.1.dimensions.1.value="<loadbalancer-id>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=cn-north-4
```

**For HTTP status code metrics (Dedicated ELB only):**

```bash
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
  --filter="average" \
  --cli-region=cn-north-4
```

> Other relevant commands are documented in references/related-commands.md.

### Step 4: List ELB Listeners (for listener-level metrics)

For listener-level metrics, first list all listeners:

```bash
hcloud ELB ListListeners --loadbalancer_id.1=<loadbalancer-id> --cli-region=<region-id>
```

### Step 5: List Backend Server Groups (Dedicated ELB only)

For Dedicated ELB, you can also monitor backend server groups:

```bash
hcloud ELB ListPools --loadbalancer_id.1=<loadbalancer-id> --cli-region=<region-id>
```

### Step 6: Format and Present Results

Present monitoring data in a clear, actionable format:

- Show metric values with timestamps
- Identify trends and anomalies
- Provide recommendations if thresholds are exceeded
- Suggest next steps for optimization
- Highlight differences between Dedicated and Shared ELB capabilities

### Optional Path: Alarm Management

If users need to view or manage alarms:

```bash
# List alarms
hcloud CES ListAlarms --cli-region=<region-id>

# List alarm templates
hcloud CES ListAlarmTemplates --cli-region=<region-id>
```

## 5. Core Commands

refer to '../references/related-commands.md'

## 6. Parameter Description

### Required Parameters

| Parameter | Description | Example Value | Default Value |
|-----------|-------------|---------------|---------------|
| `--cli-region` | Region ID | `cn-north-4` | None, must be specified |
| `--metrics.1.namespace` | Namespace for metric 1 | `SYS.ELB` | None, must be specified |
| `--metrics.1.metric_name` | Metric name for metric 1 | `m1_cps` | None, must be specified |
| `--metrics.1.dimensions.1.name` | Dimension name | `lbaas_instance_id` | None, must be specified |
| `--metrics.1.dimensions.1.value` | Dimension value | `lb-12345678` | None, must be specified |

### Optional Parameters

| Parameter | Description | Example Value | Default Value |
|-----------|-------------|---------------|---------------|
| `--from` | Start time (Unix timestamp in milliseconds) | `$(date -d '-1 hour' +%s)000` | Current time - 1 hour |
| `--to` | End time (Unix timestamp in milliseconds) | `$(date +%s)000` | Current time |
| `--period` | Statistics period (seconds) | `300` | `300` |
| `--filter` | Statistical method | `average` | `average` |
| `--project-id` | Project ID | `project-id` | Project ID from configuration file |
| `--metrics.1.dimensions.2.name` | Second dimension name (for listener) | `lbaas_listener_id` | Optional |
| `--metrics.1.dimensions.2.value` | Second dimension value (for listener) | `listener-12345678` | Optional |

### Time Range Options

- **Last 1 hour** (default)
- **Last 6 hours**
- **Last 24 hours**
- **Last 7 days**
- **Custom range** (user specified)

### Namespace

- **SYS.ELB**
  Basic monitoring metrics for Elastic Load Balance (ELB).

### ELB Monitoring Dimensions

1. **Load Balancer** (`lbaas_instance_id`): All connection and traffic metrics
2. **Listener** (`lbaas_listener_id`): Protocol-specific, HTTP status codes (Dedicated ELB only)
3. **Backend Server Group** (`lbaas_pool_id`): Backend health metrics (Dedicated ELB only)
4. **Availability Zone** (`lbaas_az`): AZ traffic distribution (Dedicated ELB only)

### filter

**Value Range**: Supports `average`, `variance`, `min`, `max`, `sum`

- `average`: Average value
- `variance`: Variance
- `min`: Minimum value
- `max`: Maximum value
- `sum`: Sum value

## 7. Output Format

Monitoring report format: `references/output-format.md`

## 8. Verification Method

Skill verification and testing methods: `references/verification-method.md`

1. **Environment verification**: Ensure Huawei Cloud CLI is installed and configured
2. **Permission verification**: Verify IAM permissions are sufficient
3. **Function verification**: Test core monitoring functionality for both ELB types
4. **Error handling verification**: Test handling of various error scenarios
5. **Type-specific verification**: Verify Dedicated vs Shared ELB metric availability (HTTP metrics, backend server group metrics only for Dedicated ELB)

## 9. Best Practices

Please refer to `references/best-practices.md` for best practices.

### Monitoring Best Practices

1. **Default to common metrics** - When user doesn't specify, default to showing common metrics (connections, bandwidth)
2. **Use appropriate time ranges** - Select suitable time ranges based on monitoring needs
3. **Provide actionable insights** - Not just raw data, provide analysis and recommendations
4. **Suggest optimization opportunities** - Provide optimization suggestions when metrics exceed thresholds
5. **Recommend alarm setup** - Suggest alarm configurations for critical metrics (e.g., HTTP 5xx rate, connection count)
6. **Compare with historical data** - Perform trend analysis when historical data is available
7. **Consider ELB type differences** - Dedicated ELB supports more metrics than Shared ELB; adjust monitoring strategy accordingly

### Performance Optimization Suggestions

- For long-term monitoring, use longer statistical periods (e.g., 300 seconds)
- Batch query related metrics to reduce API call frequency
- Cache frequently used query results to improve response speed
- Use appropriate filter conditions to reduce data transfer volume
- Use listener-level metrics for protocol-specific analysis (Dedicated ELB)
- Monitor backend server group health to proactively detect issues (Dedicated ELB)

### Resource Management Suggestions

- Regularly clean up unnecessary monitoring data
- Set appropriate monitoring data retention policies
- Use tags to categorize and manage ELB instances
- Set different monitoring strategies for different environments (development, testing, production)
- Choose appropriate ELB type based on monitoring requirements (Dedicated for advanced monitoring, Shared for basic needs)
- Monitor bandwidth usage to optimize ELB specification and cost

## 10. Reference Documents

Refer to documents in the `references/` directory for more information:

- `cli-installation-guide.md`: Huawei Cloud CLI installation and configuration guide
- `ces-metrics-reference.md`: Complete list of CES metrics for ELB (Dedicated and Shared)
- `iam-policies.md`: Required IAM permissions and policies
- `best-practices.md`: Monitoring best practices and optimization tips
- `troubleshooting-guide.md`: Common issues and solutions
- `verification-method.md`: Skill verification and testing methods
- `acceptance-criteria.md`: Quality standards and acceptance criteria
- `related-commands.md`: Related command reference

## 11. Notes

### Security Tips

- **Credential security**: Never expose AK/SK in code, logs, or conversations
- **Principle of least privilege**: Grant only necessary IAM permissions
- **Regular rotation**: Regularly rotate access keys
- **Monitor access**: Enable Cloud Trace Service to monitor API calls

### Limitations

- **API limits**: Be aware of Huawei Cloud API rate limits
- **Data retention**: Monitoring data has limited retention time
- **Regional restrictions**: Some metrics may only be available in specific regions
- **ELB type restrictions**: Shared ELB only supports basic metrics; Dedicated ELB supports advanced metrics including HTTP status codes, backend server group metrics, and traffic mirroring
- **Protocol restrictions**: HTTP/HTTPS metrics only available for L7 protocols (HTTP/HTTPS/QUIC/GRPC) on Dedicated ELB

### Known Issues

1. **Timezone issues**: All timestamps use UTC timezone
2. **Data latency**: Monitoring data may have 1-2 minutes delay
3. **Metric availability**: Newly created ELB instances may take several minutes to start reporting metrics
4. **API version**: Ensure compatible API version is used
5. **Shared ELB HTTP metrics**: HTTP status code metrics (`elb_http_*`, `l7_*_ratio`) are not available for Shared ELB
6. **Backend server group metrics**: Only available for Dedicated ELB with 7-layer protocol

### Troubleshooting

Common errors and solutions:

1. **Invalid credentials**: Guide user to configure Huawei Cloud CLI
2. **ELB instance not found**: Suggest checking loadbalancer ID and region
3. **No metric data**: Check time range, metric availability, and ELB type compatibility
4. **Permission denied**: Guide user to check IAM permissions
5. **Network errors**: Suggest retrying or checking network connectivity
6. **Unsupported metric for Shared ELB**: Suggest using Dedicated ELB or switching to basic metrics

Please refer to `references/troubleshooting-guide.md` for other known issues.