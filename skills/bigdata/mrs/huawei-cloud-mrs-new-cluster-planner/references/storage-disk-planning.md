# Storage and Disk Planning

> Extracted from SKILL.md Phase 4.

## 1. System Disk

| Parameter | Value |
|-----------|-------|
| Type | High IO — cheapest reliable option for OS |
| Size | **480 GB** (standard for MRS OS + management) |
| Notes | OS + MRS management software + log storage |
| Price | ¥0.35/GiB/month (High IO) |

## 2. Master Node Data Disk

| Parameter | Value |
|-----------|-------|
| **Primary Purpose** | NameNode/ResourceManager metadata, service logs |
| Disk Type | **General SSD** (¥0.70/GiB/month) |
| Single Disk Size | **600 GB** (fixed, standard size) |
| Number of Disks | **1 per Master node** (single disk for metadata+logs) |
| Mount | /data1 |
| Price | 1 x 600GB x ¥0.70 = ¥420/month per Master node |

## 3. Core/Task Node Data Disk (Shuffle Storage)

**Core and Task nodes MUST have IDENTICAL data disk configuration for Shuffle (Spark/Flink spill).**

| Parameter | Value |
|-----------|-------|
| **Primary Purpose** | Spark/YARN Shuffle data (Core also stores HDFS data locally) |
| Disk Type | **General SSD** |
| Single Disk Size | **600~800 GB** (flexible,起步600GB，按需求调整不超过800GB) |
| Total Shuffle Per Node | vCPU count x 40 GB (1 vCPU = 40GB) |
| Disk Config Algorithm | 见下方灵活计算规则 |
| Mount | /data1, /data2, /data3, /data4, ... |
| HDFS Data | Core: same disks for local HDFS; Task: no HDFS (compute-only) |

**灵活数据盘计算规则**:
```
Shuffle需求 = vCPU × 40GB
单盘大小范围: 600~800GB

1. 需求 <= 800GB: 1块盘, 单盘 = max(600, 需求)
   例: 640GB → 1块640GB

2. 需求是600的倍数: 600GB/块
   例: 2400GB → 4块600GB

3. 其他: 尝试减少盘数, 单盘 = ceil(需求/盘数) ≤ 800GB
   例: 1400GB → 2块700GB
   例: 1000GB → 2块600GB (ceil(1000/2)=500<600, 取600)
```

**NOTE: Task nodes use identical disk config as Core but are billed on-demand.**

**Shuffle Space Calculation Examples**:

| Flavor | vCPU | Shuffle Demand | Disks | Disk Size | Total per Node |
|--------|------|----------------|-------|-----------|----------------|
| ac9.4xlarge.4 | 16 | 640 GB | 1 | 640 GB | 0.6 TB |
| ac9.8xlarge.4 | 32 | 1,280 GB | 2 | 640 GB | 1.3 TB |
| ac9.16xlarge.4 | 64 | 2,560 GB | 4 | 640 GB | 2.5 TB |
| ac9.32xlarge.4 | 128 | 5,120 GB | 8 | 640 GB | 5.0 TB |

> Note: `ac9.32xlarge.4` (128 vCPU / 512 GB) is the largest 1:4 flavor on the official
> MRS-supported list. Larger 192-vCPU flavors are **not** MRS-supported and must not be used.

## 4. HDFS Storage Planning

When the user requires large HDFS data storage (e.g., > 100 TB), consider:

| Storage Mode | Disk Type | Recommended Size | Notes |
|-------------|-----------|-----------------|-------|
| Local HDFS | General SSD (same as shuffle) | Expand Core node data disks | Data locality, higher throughput |
| OBS (storage-compute separation) | Not needed | N/A | Data stored in OBS, Core nodes compute-only |
| Mixed | SSD + OBS | Reduced local disk | Hot data on local, cold data on OBS |

## 5. OBS Storage-Compute Separation

**OBS Integration (storage-compute separation)**:
- Core nodes do not need large data disks — use compute-optimized flavors (1:2 ratio)
- Reduces storage cost significantly (OBS is cheaper per TB than ECS disks)
- Guardian component required for unified OBS access control
- Recommended for: data lake architecture, multi-cluster data sharing

## 6. OBS Capacity Calculation

**OBS Capacity Calculation (Actual Required Storage, Single-Replica)**:

```
IMPORTANT: OBS stores a single replica (unlike HDFS 3-replica).
Total storage = existing data + daily_increment × retention_days × compression_ratio.
Report the actual required capacity directly — do NOT round up to an OBS package tier.

  Step 1: Calculate the actual required capacity
    OBS_capacity = existing data + daily_increment × retention_days × compression_ratio
    Example: existing 50 TB + 5 TB/day × 180 days × 0.4 = 410 TB

    If the user provides a data volume that INCLUDES HDFS replicas,
    convert to single-replica first:
    OBS_capacity = provided_volume / replica_count
    Example: 560 TB HDFS (3 replicas) -> 560 / 3 = 187 TB

  Step 2: Calculate OBS cost from the actual capacity (no package tier)
    OBS Storage Cost = OBS_capacity (TB) × 1024 (GB/TB) × ¥0.099/GB/month
    Example: 410 TB × 1024 × ¥0.099 = ¥41,574/month

No package tier rounding: report OBS capacity directly as the actual required storage.
```

When user provides data volume WITHOUT replica info, ask for clarification.
If user confirms it's single-replica, use the value directly as the OBS capacity.

## 7. Disk Type Pricing Reference

### 7.1 Disk Type Pricing Reference (Official Prices, cn-north-4 Baseline)

**Data source**: Huawei Cloud EVS product page https://www.huaweicloud.com/product/evs.html
**Retrieved**: 2026-08-07
**Applicable region**: cn-north-4 (baseline prices)

| Disk Type | Hourly (¥/GiB) | Monthly (¥/GiB) | Yearly (¥/GiB) | Use Case |
|-----------|---------------|-----------------|-----------------|----------|
| **High IO (SAS)** | 0.00049 | **0.35** | 3.5 | **System disk (default, cheapest)** |
| **General SSD** | 0.00097 | **0.70** | 7.0 | **Core data disk (default for shuffle)** |
| General SSD V2 | 0.000695 | 0.50 | 5.0 | Alternative (lower cost, configurable IOPS) |
| Ultra-High IO | 0.0014 | 1.00 | 10.0 | Extreme IO workloads |
| Extreme SSD | 0.0042 | 2.00 | 20.0 | Ultra-low latency |
