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
| Disk Type | **General Purpose SSD** (¥0.70/GiB/month) |
| Single Disk Size | **600 GB** (fixed, standard size) |
| Number of Disks | **1 per Master node** (single disk for metadata+logs) |
| Mount | /data1 |
| Price | 1 × 600GB × ¥0.70 = ¥420/month per Master node |

## 3. Core/Task Node Data Disk (Shuffle Storage)

**Core and Task nodes MUST have IDENTICAL data disk configuration for Shuffle (Spark/Flink spill).**

| Parameter | Value |
|-----------|-------|
| **Primary Purpose** | Spark/YARN Shuffle data (Core also stores HDFS data locally) |
| Disk Type | **General Purpose SSD** (¥0.70/GiB/month) |
| Per-Node Shuffle Requirement | vCPU count × 40 GB |
| Single Disk Size | **flexible — 600 GB minimum, 800 GB maximum** |
| Number of Disks | fewest disks that fit, each disk kept within 600-800 GB |
| Mount | /data1, /data2, /data3, /data4, ... |
| HDFS Data | Core: same disks for local HDFS; Task: no HDFS (compute-only) |

**NOTE: Task nodes use identical disk config as Core but are billed on-demand.**

**Flexible Disk Planning Algorithm (per node)**:

```
need = vCPU × 40 (GB)                      # per-node shuffle requirement
N = max(1, floor(need / 600))              # start from the smallest disks (>=600 GB)
disk_size = max(600, ceil(need / N))       # clamp to the 600 GB floor
IF disk_size > 800:                        # need cannot be split within the 600-800 range
  N = ceil(need / 600)
  disk_size = 600
Per-node shuffle capacity = N × disk_size
Total shuffle = per-node shuffle capacity × node count
```

**Example Disk Planning**:

| Flavor | vCPU | Requirement | Planned Disks | Per-Node Capacity |
|--------|------|-------------|---------------|-------------------|
| ac9.4xlarge.4 | 16 | 640 GB | 1 × 640 GB | 640 GB |
| ac9.8xlarge.4 | 32 | 1,280 GB | 2 × 640 GB | 1,280 GB |
| ac9.16xlarge.4 | 64 | 2,560 GB | 4 × 640 GB | 2,560 GB |
| ac9.32xlarge.4 | 128 | 5,120 GB | 8 × 640 GB | 5,120 GB |
| ac9.48xlarge.4 | 192 | 7,680 GB | 12 × 640 GB | 7,680 GB |

**Reference Cases**:
```
640 GB    -> 1 × 640 GB
1,400 GB  -> 2 × 700 GB
2,400 GB  -> 4 × 600 GB
```

**Total Shuffle Calculation**:
```
Total shuffle = per-node disk total (disk size × disk count) × node count
Example: 32 vCPU, 2 × 640 GB per node, 10 nodes -> 1,280 GB × 10 = 12,800 GB = 12.5 TB
```

**Cost Calculation** (ac9.8xlarge.4, 32 vCPU, 2 disks of 640 GB):
```
Monthly cost per Core node: 2 × 640 GB × ¥0.70/GB = ¥896/month
For 10 Core nodes: ¥8,960/month
```

**Cost Calculation** (ac9.32xlarge.4, 128 vCPU, 8 disks of 640 GB):
```
Monthly cost per Core node: 8 × 640 GB × ¥0.70/GB = ¥3,584/month
For 14 Core nodes: 14 × ¥3,584 = ¥50,176/month
```

## 4. HDFS Storage Planning

When the user requires large HDFS data storage (e.g., > 100 TB), consider:

| Storage Mode | Disk Type | Recommended Size | Notes |
|-------------|-----------|-----------------|-------|
| Local HDFS | General SSD (same as shuffle) | Expand Core node data disks | Data locality, higher throughput |
| OBS (storage-compute separation) | Not needed | N/A | Data stored in OBS, Core nodes compute-only |
| Mixed | SSD + OBS | Reduced local disk | Hot data on local, cold data on OBS |

> Full data volume = existing data + daily incremental data × retention period. HDFS capacity is planned on this full data volume.

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
When the user provides data volume that INCLUDES HDFS replicas,
calculate the actual required (single-replica) capacity:

  Step 1: Full data volume
    full_data_volume = existing data + daily incremental data × retention period
    Example: 560 TB HDFS (3 replicas)

  Step 2: Actual required single-replica capacity
    OBS_capacity = full_data_volume / replica_count
    Example: 560 / 3 = 187 TB

  Step 3: Calculate OBS cost from the actual capacity (no package tier)
    OBS Storage Cost = OBS_capacity (TB) × 1024 (GB/TB) × ¥0.099/GB/month
    Example: 187 TB × 1024 × ¥0.099 = ¥18,982/month

No package tier rounding: report OBS capacity directly as the actual required storage.
```

When user provides data volume WITHOUT replica info, ask for clarification.
If user confirms it's single-replica, use the value directly as the OBS capacity.

## 7. Disk Type Pricing Reference

### 4.4 Disk Type Pricing Reference (official prices, North Beijing-4 baseline)

**Data source**: Huawei Cloud EVS product page https://www.huaweicloud.com/product/evs.html
**Retrieved**: 2026-08-07
**Applicable region**: North Beijing-4 (baseline prices)

| Disk Type | Hourly (¥/GiB) | Monthly (¥/GiB) | Yearly (¥/GiB) | Use Case |
|-----------|---------------|-----------------|----------------|----------|
| **High IO (SAS)** | 0.00049 | **0.35** | 3.5 | **System disk (default, cheapest)** |
| **General Purpose SSD** | 0.00097 | **0.70** | 7.0 | **Core data disk (default for shuffle)** |
| General Purpose SSD V2 | 0.000695 | 0.50 | 5.0 | Alternative (lower cost, configurable IOPS) |
| Ultra-High IO | 0.0014 | 1.00 | 10.0 | Extreme IO workloads |
| Ultra-Fast SSD | 0.0042 | 2.00 | 20.0 | Ultra-low latency |
