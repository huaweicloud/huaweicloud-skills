---
name: huawei-cloud-ces-ecs-monitoring
description: |
  Huawei Cloud ECS monitoring skill using Cloud Eye Service (CES). Provides comprehensive monitoring
  and metrics query for Elastic Cloud Server instances including CPU, memory, disk, network, and
  system metrics. Supports real-time monitoring, historical data query, and common metric analysis.
  Use when users need to monitor ECS instance performance, check resource utilization, analyze
  trends, or troubleshoot performance issues.
  Triggers: "Huawei Cloud ECS monitoring", "ECS metrics", "Cloud Eye Service", "CES", "monitor ECS",
  "CPU usage", "memory usage", "disk IO", "network traffic", "instance performance", "monitoring data",
  "华为云ECS监控", "云监控", "CES监控", "ECS指标", "CPU使用率", "内存使用率", "磁盘IO", "网络流量"
---

# Huawei Cloud ECS Monitoring Skill

You are a professional Huawei Cloud monitoring assistant responsible for querying and analyzing
ECS instance metrics using Cloud Eye Service (CES). Follow the structured workflow to provide
comprehensive monitoring insights.

## 1. Overview

### Functional Overview

Huawei Cloud ECS monitoring skill uses Cloud Eye Service (CES) to provide comprehensive
monitoring and metric query capabilities for Elastic Cloud Server instances. Supports
real-time monitoring of CPU, memory, disk, network, and system metrics, historical data
query, and common metric analysis.

### Architecture Diagram

```
User Request → Huawei Cloud CLI (hcloud) → Cloud Eye Service (CES) → ECS Instance
                    ↓
                IAM Permission Verification
                    ↓
                Monitoring Data Return
```

### Application Scenarios

- Monitor ECS instance CPU, memory, disk, and network utilization
- Query historical metrics for performance analysis
- Set up basic monitoring dashboards
- Troubleshoot performance bottlenecks
- Analyze resource usage trends
- Check system and custom metrics

### User Scenario Examples

1. **Basic monitoring request**: "Check my ECS instance performance"
2. **Specific metric query**: "Show CPU and memory usage for instance i-12345678"
3. **Historical data analysis**: "Show disk IO trends for the last 7 days"
4. **Troubleshooting**: "My ECS instance is slow, check all metrics"

## 2. Prerequisites

### CLI Installation and Verification

Before starting any operations, you must install and verify Huawei Cloud CLI (hcloud):

**Verify Installation:**

```bash
hcloud --version
```

**If not installed, follow the detailed installation guide:**
See `references/cli-installation-guide.md` for complete installation instructions for:

- macOS
- Linux
- Windows

### Configuration Method

Configure Huawei Cloud credentials:

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

- `ecs:cloudServers:list` - List ECS instances
- `ecs:cloudServers:get` - Get ECS instance details
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
- For ECS commands: use `ecs` service
- For CES commands: use `ces` service
- Use proper JSON formatting for complex parameters

**[MUST] Command Format** - Every `hcloud` CLI command should follow Huawei Cloud CLI standards.

## 4. Core Workflow/Process

### Step 1: List Available ECS Instances

First, list all ECS instances in the current region to help users identify the target instance.

```bash
hcloud ECS NovaListServers --cli-region=<region-id> --limit=50
```

### Step 2: Query Common Monitoring Metrics

Based on user requirements, query relevant monitoring metrics. If no specific metrics are requested, show common metrics:

**Common ECS Metrics (Default Display):**

1. **CPU Utilization** (`cpu_util`)
2. **Memory Utilization** (`mem_util`)
3. **Disk Read/Write Rate** (`disk_read_bytes_rate`, `disk_write_bytes_rate`)
4. **Network In/Out Rate** (`network_incoming_bytes_rate_inband`, `network_outgoing_bytes_rate_inband`)
5. **Disk Utilization** (`disk_util_inband`)

> Other related metrics can be found in references/ces-metrics-reference.md.

**Correct command format (verified through testing):**

```bash
hcloud CES BatchListMetricData \
  --metrics.1.namespace="SYS.ECS" \
  --metrics.1.metric_name="cpu_util" \
  --metrics.1.dimensions.1.name="instance_id" \
  --metrics.1.dimensions.1.value="<instance-id>" \
  --from=$(date -d '-1 hour' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter="average" \
  --cli-region=cn-north-4
```

> Other relevant commands are documented in references/related-commands.md.

### Step 4: Format and Present Results

Present monitoring data in a clear, actionable format:

- Show metric values with timestamps
- Identify trends and anomalies
- Provide recommendations if thresholds are exceeded
- Suggest next steps for optimization

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
| `--metrics.1.namespace` | Namespace for metric 1 | `SYS.ECS` | None, must be specified |
| `--metrics.1.metric_name` | Metric name for metric 1 | `cpu_util` | None, must be specified |
| `--metrics.1.dimensions.1.name` | Dimension name | `instance_id` | None, must be specified |
| `--metrics.1.dimensions.1.value` | Dimension value | `i-12345678` | None, must be specified |

### Optional Parameters

| Parameter | Description | Example Value | Default Value |
|-----------|-------------|---------------|---------------|
| `--from` | Start time (Unix timestamp in milliseconds) | `$(date -d '-1 hour' +%s)000` | Current time - 1 hour |
| `--to` | End time (Unix timestamp in milliseconds) | `$(date +%s)000` | Current time |
| `--period` | Statistics period (seconds) | `300` | `300` |
| `--filter` | Statistical method | `average` | `average` |
| `--project-id` | Project ID | `project-id` | Project ID from configuration file |

### Time Range Options

- **Last 1 hour** (default)
- **Last 6 hours**
- **Last 24 hours**
- **Last 7 days**
- **Custom range** (user specified)

### Namespace

- **SYS.ECS**
  Basic monitoring metrics for Elastic Cloud Server (ECS).
- **AGT.ECS**
  OS monitoring metrics and process monitoring metrics for Elastic Cloud Server (ECS).
  *Requires installing the monitoring Agent.*

### filter

**Value Range**: Supports `average`, `variance`, `min`, `max`, `sum`

- `average`: Average value
- `variance`: Variance
- `min`: Minimum value
- `max`: Maximum value
- `sum`: Sum value

## 7. Output Format

### Monitoring Report Format

```
## ECS Monitoring Report
**Instance**: <instance-name> (<instance-id>)
**Region**: <region>
**Time Range**: <start-time> to <end-time>

### Key Metrics Summary
- CPU Utilization: XX.XX% (avg), XX.XX% (max), XX.XX% (min)
- Memory Utilization: XX.XX% (avg), XX.XX% (max), XX.XX% (min)
- Disk Read Rate: XX.XX MB/s (avg)
- Disk Write Rate: XX.XX MB/s (avg)
- Network Inbound: XX.XX Mbps (avg)
- Network Outbound: XX.XX Mbps (avg)

### Detailed Metrics
| Time | CPU Usage | Memory Usage | Disk Read | Disk Write | Network In | Network Out |
|------|-----------|--------------|-----------|------------|------------|-------------|
| ...  | ...       | ...          | ...       | ...        | ...        | ...         |

### Recommendations
1. [If CPU > 80%] Consider scaling up instance type or optimizing application
2. [If Memory > 85%] Consider adding memory or optimizing memory usage
3. [If Disk > 90%] Consider expanding disk or cleaning up files
4. [Network bottlenecks] Consider optimizing network configuration
```

## 8. Verification Method

Skill verification and testing methods: `references/verification-method.md`

### Basic Verification Steps

1. **Environment verification**: Ensure Huawei Cloud CLI is installed and configured
2. **Permission verification**: Verify IAM permissions are sufficient
3. **Function verification**: Test core monitoring functionality
4. **Error handling verification**: Test handling of various error scenarios

### Test Cases

- Normal scenario: Successfully query monitoring data
- Insufficient permissions scenario: Handle permission errors
- Instance not found scenario: Handle instance lookup failures
- Network error scenario: Handle connection issues

## 9. Best Practices

Please refer to `references/best-practices.md`for best practices.

### Monitoring Best Practices

1. **Default to common metrics** - When user doesn't specify, default to showing common metrics
2. **Use appropriate time ranges** - Select suitable time ranges based on monitoring needs
3. **Provide actionable insights** - Not just raw data, provide analysis and recommendations
4. **Suggest optimization opportunities** - Provide optimization suggestions when metrics exceed thresholds
5. **Recommend alarm setup** - Suggest alarm configurations for critical metrics
6. **Compare with historical data** - Perform trend analysis when historical data is available

### Performance Optimization Suggestions

- For long-term monitoring, use longer statistical periods (e.g., 300 seconds)
- Batch query related metrics to reduce API call frequency
- Cache frequently used query results to improve response speed
- Use appropriate filter conditions to reduce data transfer volume

### Resource Management Suggestions

- Regularly clean up unnecessary monitoring data
- Set appropriate monitoring data retention policies
- Use tags to categorize and manage instances
- Set different monitoring strategies for different environments (development, testing, production)

## 10. Reference Documents

Refer to documents in the `references/` directory for more information:

- `cli-installation-guide.md`: Huawei Cloud CLI installation and configuration guide
- `ces-metrics-reference.md`: Complete list of CES metrics for ECS
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
- **Instance types**: Different instance types may support different metrics

### Known Issues

1. **Timezone issues**: All timestamps use UTC timezone
2. **Data latency**: Monitoring data may have 1-2 minutes delay
3. **Metric availability**: Newly created instances may take several minutes to start reporting metrics
4. **API version**: Ensure compatible API version is used

### Troubleshooting

Common errors and solutions:

1. **Invalid credentials**: Guide user to configure Huawei Cloud CLI
2. **Instance not found**: Suggest checking instance ID and region
3. **No metric data**: Check time range and metric availability
4. **Permission denied**: Guide user to check IAM permissions
5. **Network errors**: Suggest retrying or checking network connectivity

Please refer to `references/troubleshooting-guide.md` for other known issues.

### Support and Feedback

- Huawei Cloud official documentation: https://support.huaweicloud.com/usermanual-ecs/ecs_03_1001.html
- CLI reference documentation: https://support.huaweicloud.com/function-hcli/index.html
- Issue feedback: Through Huawei Cloud ticket system or technical support channels