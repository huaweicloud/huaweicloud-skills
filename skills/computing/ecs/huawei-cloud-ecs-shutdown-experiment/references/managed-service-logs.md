# Huawei Cloud Managed Service Logs

## Overview

This document lists how to access logs from Huawei Cloud managed services, for collecting and analyzing related service logs during an ECS shutdown fault injection experiment. **Scope: standalone ECS scenarios (non-CCE).**

## LTS (Cloud Log Service)

### Log Structure

LTS uses a two-level structure: Log Group → Log Stream.

### Query Logs

```bash
# List log groups
hcloud LTS ListLogGroups --cli-region=cn-north-4 --cli-output=json

# List log streams (KooCLI 7.2.x takes --log_group_name, NOT --log_group_id;
# the ID form is rejected with [USE_ERROR])
hcloud LTS ListLogStreams --cli-region=cn-north-4 --log_group_name=<group_name> --cli-output=json

# Query logs (keyword filter); the standalone scripts/collect_logs.py supports
# --log-stream-ids (comma-separated) for multiple streams in one run
hcloud LTS ListLogs --cli-region=cn-north-4 --cli-output=json \
    --log_group_id=<gid> --log_stream_id=<sid> \
    --start_time=<epoch_ms> --end_time=<epoch_ms> \
    --keywords="ERROR"  # log_group_id/log_stream_id are path params; start_time/end_time/keywords are body params (KooCLI: all as --param=value)
```

Times use epoch milliseconds. It is recommended to set end_time = experiment end + 3 minutes to capture recovery behavior.

### Collecting ECS Application Logs into LTS

To analyze an ECS instance's application logs through this skill, install log-agent (ICAgent) on the instance and configure a log group/stream that collects its application logs. The user provides the log group ID via `--log-group-id`.

## ECS (Elastic Cloud Server) Operation Audit — instance-level action records

**No additional configuration required** — every ECS keeps its own action history in the
platform (this is what the console 审计日志 tab shows). More reliable for drill verification
than CTS (which needs a tracker to be created). Records the compute-layer actions and their
internal event timings.

```bash
# List all actions for an instance (create/start/stop/reboot/...)
hcloud ECS NovaListServerActions --cli-region=cn-north-4 --cli-output=json \
    --server_id=<instance-id>

# Show one action with its internal compute events + durations
hcloud ECS NovaShowServerAction --cli-region=cn-north-4 --cli-output=json \
    --server_id=<instance-id> --request_id=<request-id-from-list>
```

**Practical value for a shutdown drill** (verified): the stop action's `events` array names
the compute-layer step (`compute_stop_instance`) with `start_time` / `finish_time` / `result`
— cross-check its duration against the experiment's SHUTOFF timing. Example observed:
stop request at 02:38:00.2, `compute_stop_instance` started 02:38:00.5 finished 02:39:13.1
(72.6s), matching the execution log's "72s to SHUTOFF".

**Related — serial console output** (kernel/boot logs, the console 控制台日志 tab):
`ShowSerialConsoleActions` opens the serial console **only if it was enabled** on the ECS
(`Ecs.0624 "enable serial console required"` otherwise). Useful for boot/shutdown kernel
messages, but requires the instance to have serial console enabled beforehand.

## RDS (Relational Database Service) Logs

| Log type | How to get |
|---|---|
| Slow logs | `hcloud RDS ListSlowLogs --cli-region=cn-north-4 --instance_id=<id> --start_date=<d> --end_date=<d>` |
| Error logs | `hcloud RDS ListErrorLogs --cli-region=cn-north-4 --instance_id=<id> --start_date=<d> --end_date=<d>` |

RDS supports dumping slow and error logs to LTS.

## ELB (Elastic Load Balance) Access Logs

ELB access logs record the details of each request (client IP, request path, response code, latency, etc.) and are usually ingested into LTS.

```bash
hcloud LTS ListLogs --cli-region=cn-north-4 --log_group_id=<elb-group> --log_stream_id=<sid> --start_time=<ms> --end_time=<ms> --keywords=503
```

## DCS (Distributed Cache Service) Logs

| Log type | Description |
|---|---|
| Slow logs | cache operations whose execution time exceeds the threshold |
| Run logs | Redis/Memcache engine run logs |

DCS logs can be queried through LTS (if ingestion is configured).

## DMS (Distributed Message Service) Logs

Kafka run logs and consumer group logs can be queried through LTS (if ingestion is configured).

## CES (Cloud Eye Service) Metrics

CES has **two metric namespaces** for ECS. Querying the wrong one silently returns
`0 datapoints` — never conclude "no Agent" from that alone. Check both:

| Namespace | Source | Metrics (examples) | Requires Agent? |
|---|---|---|---|
| `SYS.ECS` | Cloud platform (hypervisor) | `cpu_util`, `disk_read/write_bytes_rate`, `network_*` (13 metrics) | No — present for any running ECS |
| `AGT.ECS` | **telescope/uniagent Agent inside the ECS** | `mem_usedPercent`, `cpu_usage*`, `load_average*`, `net_bitRecv/Sent`, `proc_*`, `net_tcp_*` (42+ metrics) | **Yes** — if the console 主机监控 shows plugin status 运行中, this namespace exists |

```bash
# Platform-level metric (works without Agent)
hcloud CES ShowMetricData --cli-region=cn-north-4 --cli-output=json \
    --namespace=SYS.ECS --metric_name=cpu_util \
    --dim.0=instance_id,<id> --from=<ms> --to=<ms> --period=60 --filter=average

# OS-level metric (requires Agent; namespace AGT.ECS, NOT SYS.ECS)
hcloud CES ShowMetricData --cli-region=cn-north-4 --cli-output=json \
    --namespace=AGT.ECS --metric_name=mem_usedPercent \
    --dim.0=instance_id,<id> --from=<ms> --to=<ms> --period=60 --filter=average
```

**Diagnose before concluding**: run `ListMetrics` for BOTH namespaces to see what exists:
```bash
hcloud CES ListMetrics --cli-region=cn-north-4 --cli-output=json \
    --namespace=SYS.ECS --dim.0=instance_id,<id> --limit=100   # platform metrics
hcloud CES ListMetrics --cli-region=cn-north-4 --cli-output=json \
    --namespace=AGT.ECS --dim.0=instance_id,<id> --limit=200   # Agent metrics
```
If `AGT.ECS` returns OS metrics, the Agent is installed — a zero-datapoint result on
`mem_usedPercent` under `SYS.ECS` means you queried the wrong namespace, not missing Agent.

### CES API network reachability (tested in sandbox)

In some sandboxed environments the system DNS resolves Huawei Cloud service domains to
**internal IPs** (`100.125.x.x`) that are NOT routable from the sandbox, while the public
ingress works fine. Symptom: `hcloud CES ShowMetricData` / `ListMetrics` fails with
`[NETWORK_ERROR]连接超时` while ECS / LTS calls succeed. Verify and fix:

```bash
# 1. Confirm symptom: CES resolves to an internal IP, ECS/LTS to a reachable one
getent hosts ces.cn-north-4.myhuaweicloud.com   # e.g. 100.125.12.100 (bad)
getent hosts ecs.cn-north-4.myhuaweicloud.com   # e.g. 100.125.12.98 (ok — reachable)

# 2. Confirm TCP reachability at the IP layer
timeout 8 bash -c 'echo > /dev/tcp/ces.cn-north-4.myhuaweicloud.com/443' && echo OK || echo FAILED

# 3. Look up the real public IP via DNS-over-HTTPS (system DNS is polluted in sandbox)
curl -sS "https://223.5.5.5/resolve?name=ces.cn-north-4.myhuaweicloud.com&type=A"
#   CNAME chain ends at an apigw-external-* A record, e.g. 120.46.247.26

# 4. Pin the public IP in /etc/hosts (backup first; this is a local, reversible change)
cp /etc/hosts /tmp/hosts.bak
echo "120.46.247.26    ces.cn-north-4.myhuaweicloud.com" >> /etc/hosts
#   Restore later with: cp /tmp/hosts.bak /etc/hosts
#   Public IP may rotate — re-run step 3 if it stops working.

# 5. Retry the query via hcloud
hcloud CES ShowMetricData --cli-region=cn-north-4 --cli-output=json --namespace=SYS.ECS \
    --metric_name=cpu_util --dim.0=instance_id,<id> --from=<ms> --to=<ms> --period=60 --filter=average
```

Notes:
- The reachability fix is **environment-local** (hosts file), not a skill config change.
- Basic metrics (`cpu_util`, `disk_read/write_bytes_rate`) live under `SYS.ECS` and exist
  without any agent. OS-level metrics (`mem_usedPercent`, `net_bitRecv/Sent`, ...) live
  under `AGT.ECS` and require the telescope/uniagent Agent installed inside the ECS.
- A zero-datapoint result is NOT proof of "no Agent": check whether you queried the
  correct namespace (`AGT.ECS` for OS metrics) and verify via `ListMetrics` first.
  The console 主机监控 plugin-status column (未安装/运行中) is the ground truth.

## Log Configuration Recommendations

1. **ECS instances**: install ICAgent and configure application logs to be reported to the LTS log group that the analysis uses
2. **RDS instance**: enable slow/error log dump to LTS
3. **ELB**: enable access log ingestion to LTS
4. **Application logs**: ensure applications output structured logs (JSON format) with timestamps and log levels