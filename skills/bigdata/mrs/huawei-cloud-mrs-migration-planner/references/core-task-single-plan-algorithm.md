# Core/Task Node Sizing and Single Plan Algorithm

> Extracted from SKILL.md Phase 3.

## 1. Core Node Sizing (Single Flavor - Uniform Deployment)

```
Core node count >= 3 (minimum for HDFS replication)
ALL Core nodes MUST use the SAME flavor (single-flavor deployment)

Single Flavor Selection Algorithm:
  1. Calculate target total vCPU (V) and memory (M) with buffer
  2. Determine ratio R = M / V (GB per vCPU)
  3. Select base ratio:
       IF R < 3:  -> Start with 1:2 ratio (CPU-optimized, lower cost)
       IF R >= 3: -> Start with 1:4 ratio (balanced, higher memory)
  4. Find smallest flavor in selected ratio that meets requirements
  5. Calculate node count: N = ceil(V / vCPU_per_node)
  6. VERIFY: Check if N × flavor_memory_per_node >= M
  7. IF memory insufficient -> UPGRADE to 1:4 ratio (or next size up)
     Repeat steps 4-6 until BOTH vCPU and memory satisfy requirements
  8. Output final single flavor and node count

By workload type (see ecs-flavor-catalog.md Section 5 series selection matrix):
  Spark/ETL (CPU-intensive)     -> General Computing-plus aC9 1:4 (ac9.8xlarge.4, 32C/128G)
  HBase (memory-intensive)      -> Memory-Optimized m6 1:8 (m6.8xlarge.8, 32C/256G)
  Kafka (I/O-intensive)         -> Ultra-High I/O i3 1:8 (i3.4xlarge.8, 16C/128G, local SSD)
  ClickHouse (I/O+memory)       -> Ultra-High I/O i3 1:8 (i3.8xlarge.8, 32C/256G, local SSD)
  Mixed workload                -> General Computing-plus aC9 1:4 (ac9.8xlarge.4, 32C/128G)
  Cost-sensitive (non-CPU-intensive) -> General Computing s7 1:4 (s7.8xlarge.4, 32C/128G)

Note: Master and Core can use different series. Master selected by memory requirement (<=128GB -> aC9, >128GB or HBase -> m6),
Core selected by workload. See ecs-flavor-catalog.md Section 5 "Series Selection Algorithm by Node Role".
```

## 2. Core Node Data Disk (Shuffle Storage)

**Core node data disks are primarily used for Shuffle data in Spark/YARN.**

```
Flexible Data Disk Rule (per Core/Task node):
  Per-node shuffle requirement = vCPU count × 40 GB
  Single disk size = flexible, 600 GB minimum, 800 GB maximum
  Use the fewest disks that fit, keeping each disk within 600-800 GB
  Disk type = General Purpose SSD
  Mount point = /data1, /data2, /data3, /data4, ...

Algorithm:
  need = vCPU × 40
  N = max(1, floor(need / 600))
  disk_size = max(600, ceil(need / N))
  IF disk_size > 800:
    N = ceil(need / 600)
    disk_size = 600
  per_node_capacity = N × disk_size
  total_shuffle = per_node_capacity × node_count

Reference cases:
  640 GB   -> 1 × 640 GB   (N=1, ceil(640/1)=640)
  1,400 GB -> 2 × 700 GB   (N=2, ceil(1400/2)=700)
  2,400 GB -> 4 × 600 GB   (N=4, ceil(2400/4)=600, exceeds 600-800 range if fewer disks)
```

Example: ac9.8xlarge.4 (32 vCPU)
```
Per-node shuffle requirement = 32 × 40 = 1,280 GB
N = max(1, floor(1280/600)) = 2
disk_size = ceil(1280/2) = 640 GB (within 600-800)
Per-node capacity = 2 × 640 GB = 1,280 GB
```

Example: ac9.16xlarge.4 (64 vCPU)
```
Per-node shuffle requirement = 64 × 40 = 2,560 GB
N = max(1, floor(2560/600)) = 4
disk_size = ceil(2560/4) = 640 GB
Per-node capacity = 4 × 640 GB = 2,560 GB
```

Example: ac9.32xlarge.4 (128 vCPU)
```
Per-node shuffle requirement = 128 × 40 = 5,120 GB
N = max(1, floor(5120/600)) = 8
disk_size = ceil(5120/8) = 640 GB
Per-node capacity = 8 × 640 GB = 5,120 GB
```

## 3. Elastic Task Node Sizing (Optional — Peak/Off-Peak Scaling)

**Task nodes are optional, used for elastic compute scaling in peak/off-peak scenarios.**
Task nodes are compute-only (no DataNode, no HDFS storage), billed on-demand based on actual runtime hours.
**Task nodes MUST have the SAME data disk configuration as Core nodes for Shuffle (Spark/Flink spill).**

**Off-peak daily load**: When elastic Task nodes are enabled, ASK the user for the cluster's normal non-peak daily workload (as a % of the original cluster's total resources). Core nodes are sized to this daily load; the peak demand is covered by elastic Task nodes. Do NOT silently derive this load from the task window.

**Task Node Sizing Algorithm (when user confirms elastic Task nodes)**:

```
PRECONDITION: User confirmed elastic Task nodes + provided the OFF-PEAK daily load ratio (L%)
              + Task node runtime hours (H hours/day) + confirmed peak buffer (B%)

MUST ASK: The off-peak daily load L% MUST be explicitly asked of the user when elastic Task is enabled
          ("what is the cluster's normal non-peak daily workload?"). Do NOT silently derive L% from the
          task window. Core is sized from this off-peak load; peak demand is covered by Task nodes.

CRITICAL: Daily load ratio L% is based on ORIGINAL CLUSTER total resources, NOT buffered target.
           Buffer B% is applied to TOTAL first, then split — buffer goes ENTIRELY to Task.

Step 1: Calculate total target resources (with buffer, IF peak saturated):
  IF peak_saturated == True:
    Total_vCPU   = Original_vCPU   × (1 + B%)   (e.g., 1480 × 1.2 = 1776)
    Total_memory = Original_memory × (1 + B%)   (e.g., 4380 × 1.2 = 5256 GB)
  ELSE:
    Total_vCPU   = Original_vCPU
    Total_memory = Original_memory

Step 2: Calculate Core node resources (based on the OFF-PEAK daily load L% asked from the user, NO buffer):
  Core_vCPU = Original_vCPU   × L%   (e.g., 1480 × 40% = 592)
  Core_mem  = Original_memory × L%   (e.g., 4380 × 40% = 1752 GB)

Step 3: Calculate Task node resources (remainder, INCLUDING buffer):
  Task_vCPU = Total_vCPU - Core_vCPU   (e.g., 1776 - 592 = 1184)
  Task_mem  = Total_memory - Core_mem  (e.g., 5256 - 1752 = 3504 GB)

Step 4: Select Core node flavor (single-flavor):
  Apply Single Flavor Selection Algorithm (Section 5) using Core_vCPU and Core_mem
  -> Result: Core_flavor, Core_node_count

Step 5: Select Task node flavor (single-flavor, can differ from Core):
  Task nodes MUST have same data disk count/size as Core (for Shuffle)
  Task nodes can use different ratio (1:2 preferred for cost efficiency)
  IF Core uses 1:4 -> Try 1:2 for Task first; IF memory insufficient -> use same 1:4
  Apply Single Flavor Selection Algorithm (Section 5) using Task_vCPU and Task_mem
  -> Result: Task_flavor, Task_node_count

Step 6: Calculate costs:
  Core nodes: yearly/monthly subscription pricing (full-time, 730h/month)
  Task nodes: on-demand pricing = Monthly_price / 730 × 1.2 × (runtime_hours × 30)
              e.g., 8h/day runtime: monthly = price/730 × 1.2 × 240 hours
  Core + Task data disks: same disk config, Core=monthly subscription, Task=on-demand

Step 7: Verify:
  Core_vCPU + Task_vCPU >= Total_vCPU
  Core_mem + Task_mem >= Total_memory
  Both CPU and memory must be satisfied

OUTPUT: Core node count + flavor (monthly subscription), Task node count + flavor (on-demand),
        Both with identical data disk config for Shuffle
```

**Task Node Sizing Example** (CDH migration, 1480 cores/4380GB, 40% off-peak daily load, 10h/day runtime, peak saturated +20% buffer):
```
Step 1: Total (with 20% buffer)
  Total_vCPU = 1480 × 1.2 = 1776
  Total_memory = 4380 × 1.2 = 5256 GB

Step 2: Core (40% of ORIGINAL, NO buffer)
  Core_vCPU = 1480 × 40% = 592
  Core_mem = 4380 × 40% = 1752 GB

Step 3: Task (remainder including buffer)
  Task_vCPU = 1776 - 592 = 1184
  Task_mem = 5256 - 1752 = 3504 GB

Step 4: Core flavor selection
  R = 1752/592 = 2.96 < 3 -> Try 1:2 first
  ac9.32xlarge.2 (128C/256G): N = ceil(592/128) = 5
  Total vCPU: 5×128 = 640 ✓ (>592)
  Total mem: 5×256 = 1280 GB ✗ (only 73% of 1752 GB)
  -> Upgrade to 1:4
  ac9.32xlarge.4 (128C/512G): N = ceil(592/128) = 5
  Total vCPU: 5×128 = 640 ✓ (>592)
  Total mem: 5×512 = 2560 GB ✓ (>1752)
  -> Core: ac9.32xlarge.4 × 5 (data: 8×640GB per node, same as Task)

Step 5: Task flavor selection
  R = 3504/1184 = 2.96 < 3 -> Try 1:2 first
  ac9.32xlarge.2 (128C/256G): N = ceil(1184/128) = 10
  Total vCPU: 10×128 = 1280 ✓ (>1184)
  Total mem: 10×256 = 2560 GB ✗ (only 73% of 3504 GB)
  -> Upgrade to 1:4
  ac9.32xlarge.4 (128C/512G): N = ceil(1184/128) = 10
  Total vCPU: 10×128 = 1280 ✓ (>1184)
  Total mem: 10×512 = 5120 GB ✓ (>3504)
  -> Task: ac9.32xlarge.4 × 10 (data: 8×640GB per node, same as Core)

Step 6: Cost breakdown
  Core (monthly subscription): 5 × ¥14,895 = ¥74,475/month
  Core data disks: 5 × 8 × 640GB × ¥0.70 = ¥17,920/month
  Task (on-demand): 10 × ¥14,895/730 × 1.2 × 300h = ¥73,151/month
  Task data disks (on-demand): 10 × 8 × 640GB × ¥0.70/730 × 1.2 × 300h = ¥17,664/month
  System disks: 15 × 480GB × ¥0.35 (Core monthly + Task on-demand)

Total elastic: ~¥190,000/month vs. Non-elastic (14×Core): ~¥278,000/month
Savings: ~32%

Verification: Core(640)+Task(1280)=1920 vCPU >= 1776 ✓, Core(2560)+Task(5120)=7680 GB >= 5256 ✓
Buffer correctly applied: Core at original 40%, Task carries 60% + 20% buffer = 80% of original
```

**If user does NOT need elastic Task nodes**: Follow the original single-flavor algorithm (Section 5) — all Core nodes handle 100% of target resources.

## 4. Component Flavor Selection Reference Table

**Note**: The table below provides component-based flavor recommendations as a starting point.
The FINAL flavor selection MUST follow the Single Flavor Selection Algorithm (Section 5) to ensure
a uniform single-flavor deployment that satisfies both CPU and memory requirements.

| Component | Default Flavor (aC9) | Alternative | CPU:Mem Ratio | Reason |
|-----------|---------------------|-------------|---------------|--------|
| Hadoop (HDFS/YARN) | ac9.8xlarge.4 | c6.8xlarge.4 | 1:4 | Balanced compute + shuffle |
| Spark | ac9.16xlarge.4 | c6.16xlarge.4 | 1:4 | High CPU for parallel compute |
| Flink | ac9.8xlarge.4 | c6.8xlarge.4 | 1:4 | CPU for stream processing |
| HBase | m6.8xlarge.8 | i3.8xlarge.8 | 1:8 | High memory for cache/memstore |
| Hive | ac9.4xlarge.4 | c6.4xlarge.4 | 1:4 | Moderate compute for SQL |
| Kafka | i3.4xlarge.8 | ac9.8xlarge.2 | 1:8 | Local SSD for high I/O |
| ClickHouse | i3.8xlarge.8 | m6.8xlarge.8 | 1:8 | Local SSD + high memory |
| Doris | m6.4xlarge.8 | ac9.8xlarge.4 | 1:8 | Memory for OLAP |
| Presto/HetuEngine | m6.8xlarge.8 | ac9.16xlarge.4 | 1:8 | Memory for in-memory query |

## 5. Single Plan Selection Algorithm (Minimum Surplus, Uniform Deployment, Minimal Excess)

**All Core nodes use the same flavor.** The algorithm is unchanged (try 1:2 -> upgrade to 1:4 if memory insufficient), but only outputs **1 final plan**:
select the flavor with minimum resource surplus relative to the original cluster.

```
Single Plan Selection Algorithm (Minimum Surplus):
  1. Calculate target: total_vCPU (V), total_memory (M), ratio R = M/V
     Note: No 20% buffer; use original cluster resources V and M directly as target
  2. Try select flavor by algorithm:
     IF R < 3 -> Try 1:2 series -> Verify vCPU and memory -> Upgrade to 1:4 if memory insufficient
     IF R >= 3 -> Use 1:4 series -> Verify vCPU and memory
  3. For each candidate flavor calculate surplus:
     N = max(ceil(V / flavor_vCPU), ceil(M / flavor_memory))
     Total_vCPU = N × flavor_vCPU
     Total_mem = N × flavor_memory
     CPU_excess% = (Total_vCPU - V) / V × 100
     Mem_excess% = (Total_mem - M) / M × 100
     Total_excess = CPU_excess% + Mem_excess%
  4. Select the plan with minimum Total_excess as final output
  5. Output only that 1 plan; no comparison plan

Example (CDH migration: 1480 vCPU, 4380 GB, R = 2.96):
  Candidate 1: ac9.32xlarge.4 (128C/512G, 1:4)
    N = max(ceil(1480/128), ceil(4380/512)) = max(12, 9) = 12
    Total_vCPU = 12×128 = 1536, CPU_excess = +3.8%
    Total_mem = 12×512 = 6144, Mem_excess = +40.2%
    Total_excess = 44.0%

  Candidate 2: ac9.32xlarge.2 (128C/256G, 1:2)
    N = max(ceil(1480/128), ceil(4380/256)) = max(12, 18) = 18
    Total_vCPU = 18×128 = 2304, CPU_excess = +55.7%
    Total_mem = 18×256 = 4608, Mem_excess = +5.2%
    Total_excess = 60.9%

  Candidate 3: ac9.16xlarge.4 (64C/256G, 1:4)
    N = max(ceil(1480/64), ceil(4380/256)) = max(24, 18) = 24
    Total_vCPU = 24×64 = 1536, CPU_excess = +3.8%
    Total_mem = 24×256 = 6144, Mem_excess = +40.2%
    Total_excess = 44.0% (same as Candidate 1, but more nodes -> select Candidate 1 for fewer nodes)

  -> Candidate 1 (ac9.32xlarge.4×12) has minimum Total_excess (44.0%)
  -> Final output: ac9.32xlarge.4 × 12 (1536C/6144G)
```

> **Note**: When two flavors have the same Total_excess, prefer the one with fewer nodes (reduces system disk / MRS management overhead).
> Higher memory surplus is because aC9 only offers 1:2 and 1:4 ratios, cannot precisely match the original cluster's 1:3 ratio.
