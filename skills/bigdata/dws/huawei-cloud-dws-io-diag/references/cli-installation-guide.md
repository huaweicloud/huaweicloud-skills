# CLI Installation Guide - Huawei Cloud DWS I/O Diagnosis

This skill requires KooCLI (hcloud) >= 3.2.0.

## Table of Contents

- [hcloud (KooCLI) Installation](#hcloud-kocli-installation)
- [Credential Configuration](#credential-configuration)
- [Verify Installation](#verify-installation)
- [DWS KooCLI Commands](#dws-kocli-commands)
- [Troubleshooting](#troubleshooting)

---

## hcloud (KooCLI) Installation

### macOS

```bash
# Install via Homebrew
brew install hcloudcli

# Or download directly
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-macos-amd64.tar.gz
tar -xzf hcloudcli-macos-amd64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

### Linux (x86_64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-amd64.tar.gz
tar -xzf hcloudcli-linux-amd64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

### Linux (ARM64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-arm64.tar.gz
tar -xzf hcloudcli-linux-arm64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

### Windows

```powershell
# Download and extract
Invoke-WebRequest -Uri "https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-windows-amd64.zip" -OutFile "hcloudcli.zip"
Expand-Archive hcloudcli.zip
# Add hcloud.exe to PATH
```

---

## Credential Configuration

### Method 1: Interactive configuration (recommended)

```bash
hcloud configure
# Enter as prompted:
# - Region (e.g., cn-south-1)
# - AK (Access Key ID)
# - SK (Access Key Secret)
```

### Method 2: Environment variables

```bash
export HUAWEICLOUD_SDK_AK=<your-access-key-id>
export HUAWEICLOUD_SDK_SK=<your-access-key-secret>
```

### Method 3: Non-interactive configuration

```bash
hcloud configure set --cli-profile=default --region=cn-south-1 --access-key-id=<AK> --secret-access-key=<SK>
```

> **Security warning**: Method 3 exposes AK/SK in command history; only use in secure environments.

---

## Verify Installation

```bash
# Check version
hcloud version
# Expected: >= 3.2.0

# Test authentication
hcloud DWS ListClusters --cli-region=<region> --project_id=<pid> --offset=0 --limit=1
```

---

## DWS KooCLI Commands

This skill uses the following KooCLI commands to interact with DWS Autopilot API:

### Query Cluster List

```bash
hcloud DWS ListClusters --cli-region=<region> --project_id=<pid> --offset=0 --limit=200
```

**Parameters**:
| Parameter | Required | Description |
|-----------|----------|-------------|
| --cli-region | Yes | Region ID (e.g., cn-north-7, cn-south-1) |
| --project_id | Yes | Project ID |
| --offset | Yes | Pagination offset, start from 0 |
| --limit | Yes | Pagination limit, use 200 |

**Response**: Returns cluster list including cluster_id, cluster_name, project_id, node_count, etc.

### Query Host Information

```bash
hcloud DWS ListHostOverview --cli-region=<region> --project_id=<pid> --cluster_id=<cid> --offset=0 --limit=200
```

**Parameters**:
| Parameter | Required | Description |
|-----------|----------|-------------|
| --cli-region | Yes | Region ID |
| --project_id | Yes | Project ID |
| --cluster_id | No | Cluster ID for filtering |
| --offset | Yes | Pagination offset, start from 0 |
| --limit | Yes | Pagination limit, use 200 |

**Response**: Returns host list including host_id, host_name, ip, etc.

### Query Metric Data

```bash
hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<cid> --metric_name=<name> --project_id=<pid> --offset=0 --limit=200 --from=<from_ts> --to=<to_ts>
```

**Parameters**:
| Parameter | Required | Description |
|-----------|----------|-------------|
| --cli-region | Yes | Region ID |
| --project_id | Yes | Project ID |
| --cluster_id | Yes | Cluster ID |
| --metric_name | Yes | Metric name (see available values below) |
| --from | Yes | Start time, Unix millisecond timestamp |
| --to | Yes | End time, Unix millisecond timestamp |
| --offset | Yes | Pagination offset, start from 0 |
| --limit | Yes | Pagination limit, use 200 |

**Available metric_name values for I/O diagnosis**:
| metric_name | Description |
|-------------|-------------|
| IOStat | Disk I/O metrics (util, await, IOPS, throughput, avgrq_sz, avgqu_sz) |
| CpuStat | CPU metrics (usr, sys, idle, iowait) |
| cpu_io_diagnose_detail | I/O diagnosis details with active queries and I/O stats |
| business_concurrency | Business concurrency and active connections |
| business_query_monitor | Historical real-time query monitoring |
| business_thread_wait | Thread wait events (WALWriteLock, wait wal sync, etc.) |
| bussiness_conflict_lock | Lock conflicts |

**Notes**:
- hcloud does not support `--order_by` and `--sort_by` parameters; sort locally after query
- cpu_io_diagnose_detail does not support host_id filtering; query full cluster then filter locally
- All timestamps must be Unix millisecond timestamps (13-digit)
- When returned data count = limit (200), continue with next page (offset += 200)

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `hcloud: command not found` | Not installed or not in PATH | Install hcloud or add to PATH |
| `authentication failed` | Invalid or expired credentials | Reconfigure credentials |
| `insufficient permissions` | Insufficient IAM permissions | Add required IAM policies |
| `region not found` | Incorrect region ID | Use the correct region ID |
| `NETWORK_ERROR` | Network connectivity issue | Check network configuration; fall back to MCP Server |
| `50201 / RDS.9999` | Autopilot backend unavailable | Retry later or contact operations staff |

---

## Security Best Practices

1. **Never provide AK/SK directly in conversation** — always use interactive configuration or environment variables
2. **Rotate AK/SK regularly** — recommended every 90 days
3. **Use IAM temporary credentials** — prefer IAM agency delegation or temporary credentials
4. **Least privilege principle** — grant only the minimum required permissions

---

## References

- [hcloud Installation Guide](https://support.huaweicloud.com/cli/cli_hcloud_install.html)
- [DWS API Reference](https://support.huaweicloud.com/api-dws/dws_02_0023.html)
