# Memory Monitoring Guide

## Problem Description

Failed to create memory usage alarm because **ECS instances do not have the monitoring Agent installed**.

### Error Information
```
http_code: 400
code: ces.0014
details: Some content in message body is not correct.
```

### Root Cause
The `mem_used_percent` metric is **not available** in the `SYS.ECS` namespace because:
- **Basic Monitoring** (Free): Only provides virtualization-layer metrics such as CPU, network traffic, and disk I/O
- **Operating System Monitoring** (Requires Agent): Provides OS-level metrics such as memory, disk usage, and processes

---

## Solutions

### Solution 1: Install Monitoring Agent (Recommended)

#### Step 1: Log in to Huawei Cloud Console
1. Visit: https://console.huaweicloud.com/ces
2. Select region: **Beijing 4 (cn-north-4)**

#### Step 2: Install Agent
1. Left menu: **Host Monitoring** → **Install Agent**
2. Select hosts to install (ecs-9095-0001, ecs-9095-0002)
3. Click **Batch Install**
4. Choose installation method:
   - **One-Click Install** (Recommended): Automatically install via Cloud Assistant
   - **Manual Install**: Copy command and execute inside ECS

#### Step 3: Verify Installation
After installation, wait 5-10 minutes, then check in CES console:
- **Host Monitoring** → **Host Details**
- You should see memory, disk usage, and other OS-level metrics

#### Step 4: Create Memory Alarm
After Agent is successfully installed, re-run the command:
```bash
./scripts/create_alert_rules.sh --metric mem_used_percent --threshold 83.3 --ecs-ids <ecs-id>
```

---

### Solution 2: Use Available Metrics (Temporary)

If you cannot install the Agent temporarily, you can use existing **CPU usage** metrics:

```bash
# Create CPU alarm (threshold 80%)
./scripts/create_alert_rules.sh --metric cpu_util --threshold 80 --ecs-ids 738682b6-73e5-4ff4-a483-f024fdced6dd,01e72a37-9b31-4fb9-8ddb-9d2ae8685739
```

**Available Metrics**:
| Metric Name | Description | Unit |
|-------------|-------------|------|
| `cpu_util` | CPU usage | % |
| `cpu_credit_balance` | CPU credit balance | Credit |
| `disk_read_bytes_rate` | Disk read rate | B/s |
| `disk_write_bytes_rate` | Disk write rate | B/s |
| `network_incoming_bytes_aggregate_rate` | Network inbound traffic | B/s |
| `network_outgoing_bytes_aggregate_rate` | Network outbound traffic | B/s |

---

## Current Alarms

Successfully created alarm rules:

| Alarm ID | ECS Instance | Metric | Threshold | Status |
|----------|-------------|--------|-----------|--------|
| `al260530T082112SuQbk5NAu` | ecs-9095-0002 | `cpu_util` | 80% | ✅ Enabled |
| `al260530T082112SdnTa9qlY` | ecs-9095-0001 | `cpu_util` | 80% | ✅ Enabled |

---

## How to Check Agent Status

### Method 1: Console View
1. Log in to Huawei Cloud Console
2. Go to **CES Host Monitoring**
3. Check the **Agent Status** column in the host list

### Method 2: CLI Query
```bash
hcloud CES ListMetrics --cli-region=cn-north-4 --namespace=SYS.ECS | grep -i mem
```
- Has output: Agent is installed
- No output: Agent needs to be installed

---

## References

- [Huawei Cloud Host Monitoring - Install Agent](https://support.huaweicloud.com/usermanual-ces/ces_01_0001.html)
- [CES Metrics Reference](https://support.huaweicloud.com/api-ces/ces_03_0003.html)
- [Agent Plugin Download](https://console.huaweicloud.com/ces/?region=cn-north-4#/ces/agentDownload)

---

**Recommended Actions**:
1. Install Agent plugin first (takes 5 minutes)
2. Wait 10 minutes for Agent to report data
3. Re-run the command to create memory alarm

**Created**: 2026-05-30  
**Skill Version**: huawei-cloud-ecs-alert v1.0.0
