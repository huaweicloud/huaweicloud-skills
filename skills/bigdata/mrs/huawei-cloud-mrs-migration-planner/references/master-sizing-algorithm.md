# Master Node Sizing Algorithm (Industry NameNode Heap Standards)

> Extracted from SKILL.md Phase 3.4 Master Node Sizing.

## 1. Hard Constraint

**Hard Constraint** (Huawei Cloud MRS official):
- Master node memory >= 64 GB (MRS 3.x mandatory)

## 2. Master Node Count Rule

**Master Node Count Rule** (by original cluster scale):
```
  < 100 original cluster cores -> 3 nodes (default, Compact)
  >= 100 original cluster cores -> 5-11 nodes (OMS-separate)
  > 500 Core nodes             -> 9-11 nodes (Full-size)
```

## 2a. Master Node vCPU Selection Rule (by Core Node Count)

**Master vCPU Selection Rule** (by MRS Core node count):
```
  Core nodes <= 20    -> Master select 16 cores (ac9.4xlarge.4 / m6.4xlarge.8)
  Core nodes 20-50    -> Master select 32 cores (ac9.8xlarge.4 / m6.8xlarge.8)
  Core nodes > 50     -> Master select 64 cores (ac9.16xlarge.4 / m6.16xlarge.8)
```

> This rule determines the Master node vCPU baseline; memory is still calculated by Step 1-4 algorithm (minimum 64GB, OBS mode minimum 128GB).
> If the vCPU baseline corresponding flavor has insufficient memory per the algorithm calculation, upgrade to the next flavor tier.

## 3. Master Node Sizing Algorithm (7-Step Method)

**Master Node Sizing Algorithm** (based on industry standards):

```
Step 1: Collect metadata scale information
  - Total file count (Files): number of files in HDFS
  - Total block count (Blocks): typically = Files × 1.5 (average 1.5 blocks per file)
  - Total data volume (DataVolume): original cluster storage capacity
  - Replica count (Replication): default 3
  - OBS storage-compute separation (OBS_mode): YES/NO

Step 2: Calculate NameNode heap memory requirement (industry formulas)
  Method 1 - Cloudera conservative formula:
    NameNode_Heap_GB = Blocks_Millions × 1 GB

  Method 2 - Alibaba Cloud precise formula (recommended):
    NameNode_Heap_GB = (Files_Millions + Blocks_Millions) × 0.5 GB

  Note: Take the larger of the two as conservative estimate

Step 3: Estimate other Master service memory requirements
  ResourceManager heap: 4-8 GB (based on YARN container count; more containers -> higher value)
  HBase HMaster heap: 2-4 GB (if HBase deployed)
  Hive Metastore heap: 2-4 GB
  ZooKeeper heap: 1-2 GB
  Other services (Oozie/Ranger etc.): 2-4 GB
  OS reserved + JVM overhead: 8-16 GB

Step 4: Calculate Master node total memory requirement
  Master_Memory_GB = NameNode_Heap + RM_Heap + Other_Services + OS_Reserved
  Total_Master_Memory = Master_Memory_GB × (1 + 0.3)  # 30% JVM overhead margin

Step 5: Select ECS flavor
  IF Total_Master_Memory <= 64 GB  -> ac9.4xlarge.4 (16 vCPU, 64 GB)
  IF Total_Master_Memory <= 128 GB -> ac9.8xlarge.4 (32 vCPU, 128 GB)
  IF Total_Master_Memory <= 256 GB -> ac9.16xlarge.4 (64 vCPU, 256 GB)
  IF Total_Master_Memory > 256 GB  -> ac9.16xlarge.4 + increase Master node count

Step 6: OBS storage-compute separation mode adjustment
  IF OBS_mode == YES:
    - HDFS only stores metadata/temporary files; Blocks significantly reduced
    - NameNode_Heap can be reduced 50-70%
    - But ResourceManager still needs to schedule all YARN resources (Core+Task)
    - Recommend minimum ac9.8xlarge.4 (32 vCPU, 128GB) to ensure scheduling capability

Step 7: Migration scenario utilization check (executed only in migration scenarios)
  Collect information:
    - Current Master node count (Orig_Master_Count)
    - Current per-node memory (Orig_Master_Memory_GB)
    - Current memory utilization (Mem_Utilization_%)
    - Current CPU utilization (CPU_Utilization_%)

  Calculate current actual usage:
    Orig_Total_Memory = Orig_Master_Count × Orig_Master_Memory_GB
    Actual_Memory_Used = Orig_Total_Memory × Mem_Utilization_% / 100
    Actual_CPU_Used = Orig_Master_Count × Orig_Master_vCPU × CPU_Utilization_% / 100

  Verify MRS plan:
    MRS_Total_Memory = MRS_Master_Count × MRS_Master_Memory_GB
    MRS_Total_CPU = MRS_Master_Count × MRS_Master_vCPU

  Decision rules:
    IF MRS_Total_Memory < Actual_Memory_Used:
      -> Memory severely insufficient! MRS total memory < current actual usage
      -> Must upgrade per-node memory flavor (e.g., from 64GB to 128GB)
      -> Recommendation: MRS per-node memory >= current per-node memory (Orig_Master_Memory_GB)

    IF MRS_Total_Memory < Orig_Total_Memory:
      -> Total memory lower than original cluster; risk exists
      -> Need to evaluate whether MRS architecture optimization can compensate for the gap (e.g., OMS-separate reduces overhead 4-8GB/node)
      -> If cannot compensate, must upgrade flavor

    IF MRS_Total_CPU < Actual_CPU_Used:
      -> CPU insufficient, but CPU can usually be mitigated by distributing across more nodes
      -> IF MRS_Total_CPU >= Orig_Total_CPU -> acceptable

  Recommendation principles:
    - MRS total memory >= original cluster total memory × 1.0 (equal or higher)
    - MRS per-node memory >= original cluster per-node memory × 0.75 (allows 3-node distributed deployment to reduce per-node pressure)
    - MRS total CPU >= original cluster total CPU × 1.0
    - If any of the above conditions is not met, the report must annotate "insufficient spec risk" and provide upgrade recommendations
```

## 4a. Migration Scenario Utilization Check Example

**Example: Tencent EMR migration to Huawei MRS**
```
Current EMR:  2 × (16C/128GB), memory utilization 75%
  Orig_Total_Memory = 2 × 128 = 256GB
  Actual_Memory_Used = 256 × 75% = 192GB

Planned MRS: 3 × (16C/64GB)
  MRS_Total_Memory = 3 × 64 = 192GB

Check: MRS_Total_Memory(192GB) < Orig_Total_Memory(256GB) -> Total memory reduced 25%
Check: MRS_Total_Memory(192GB) == Actual_Memory_Used(192GB) -> 0% margin, utilization will reach 100%!

Conclusion: Memory severely insufficient; recommend upgrade to 3 × (16C/128GB) = 384GB
  After upgrade: 384GB vs 192GB usage = 50% margin ✓
```

## 4. Quick Estimation Table

**Quick Estimation Table** (typical scenarios, non-OBS storage-compute separation):

| Data Volume | Estimated File Count | Estimated Block Count | NameNode Heap | Master Total Memory | Recommended Flavor |
|-------------|---------------------|----------------------|---------------|---------------------|-------------------|
| < 10 TB | < 1 million | < 1.5 million | 1-2 GB | ~32 GB | ac9.4xlarge.4 (64GB) |
| 10-50 TB | 1-5 million | 1.5-7.5 million | 2-6 GB | ~48 GB | ac9.4xlarge.4 (64GB) |
| 50-200 TB | 5-20 million | 7.5-30 million | 6-25 GB | ~80 GB | ac9.8xlarge.4 (128GB) |
| 200-500 TB | 20-50 million | 30-75 million | 25-60 GB | ~128 GB | ac9.16xlarge.4 (256GB) |
| > 500 TB | > 50 million | > 75 million | > 60 GB | > 160 GB | ac9.16xlarge.4 (256GB) |

**OBS Storage-Compute Separation Mode Quick Estimation Table** (HDFS only stores metadata):

| Data Volume | OBS Mode NameNode Heap | Master Total Memory | Recommended Flavor |
|-------------|------------------------|---------------------|-------------------|
| < 100 TB | 2-4 GB | ~48 GB | ac9.8xlarge.4 (128GB) * |
| 100-500 TB | 4-8 GB | ~64 GB | ac9.8xlarge.4 (128GB) |
| > 500 TB | 8-16 GB | ~80 GB | ac9.8xlarge.4 (128GB) |

* OBS mode recommends minimum 128GB flavor to ensure ResourceManager scheduling capability

## 5. Example Calculation

**Example Calculation** (Scenario E: 560TB CDH migration, OBS storage-compute separation):
```
Original data: 560TB (3 replicas) -> single replica 187TB (actual required OBS capacity)
OBS mode: HDFS only stores metadata and temporary files
Estimated file count: ~20 million (typical Hadoop cluster)
Estimated block count: ~30 million
NameNode heap (OBS reduced 70%): (20+30)×0.5×0.3 = 7.5 GB
ResourceManager heap: 8 GB (scheduling 1776 cores/5256GB)
Other services: 8 GB
OS+JVM overhead: 16 GB
Master total memory: 7.5+8+8+16 = 39.5 GB × 1.3 = 51 GB
Recommended flavor: ac9.8xlarge.4 (32 vCPU, 128 GB) — satisfies with margin
```
