# Master Node Spec Selection Algorithm (Greenfield Scenario)

> Extracted from SKILL.md Phase 4.2. Greenfield scenario has no original cluster utilization check; Master node count is determined by **planned Core total cores**.

## 1. Hard Constraints

**Hard constraints** (Huawei Cloud MRS official):
- Master node memory >= 64 GB (MRS 3.x mandatory)
- OBS storage-compute separation mode: recommended minimum 128 GB (ensure ResourceManager scheduling)

## 2. Master Node Count Rule (Greenfield Scenario)

**Master node count rule** (by planned Core total cores, not original cluster cores):
```
  Core total cores < 100  -> 3 nodes (default, Compact)
  Core total cores >= 100 -> 5 nodes (OMS-separate)
  Core node count > 500   -> 9-11 nodes (Full-size)
```

> Note: The basis is the **Core total cores** after Phase 4.3 selection (Core node count x single node vCPU), corresponding to "original cluster cores" in migration scenario.
> Take the higher value in the rule range when Kerberos/strict HA is required.

## 2a. Master Node vCPU Selection Rule (By Core Node Count)

**Master vCPU selection rule** (by MRS Core node count):
```
  Core nodes <= 20   -> Master selects 16 cores (ac9.4xlarge.4 / m6.4xlarge.8)
  Core nodes 20-50   -> Master selects 32 cores (ac9.8xlarge.4 / m6.8xlarge.8)
  Core nodes > 50    -> Master selects 64 cores (ac9.16xlarge.4 / m6.16xlarge.8)
```

> This rule determines the Master node vCPU baseline; memory is calculated by Step 1-6 algorithm (MRS hard constraint minimum 64GB).
> Greenfield scenario does not enforce memory upgrade: select spec per Step 1-4 algorithm result; if algorithm result <= 64GB use 64GB; do not force upgrade to 128GB due to OBS mode.
> Only upgrade to next tier when algorithm calculated value > spec memory.

## 3. Master Node Memory Calculation Algorithm (6-Step Method, Greenfield Scenario)

```
Step 1: Estimate metadata scale
  Greenfield scenario has no existing file count; estimate by data volume:
    Estimated file count Files = S_TB x (100K ~ 1M)/TB
      - Few small files / ORC columnar: take 100K-300K/TB
      - Text / semi-structured: take 500K-1M/TB
    S_TB = Phase 3 estimated total storage (logical volume, post-compression)
    Blocks = Files x 1.5
  When user explicitly knows file scale, use user value.

Step 2: Calculate NameNode heap memory requirement (industry formula)
  Method 1 - Cloudera conservative formula:
    NameNode_Heap_GB = Blocks_Millions x 1 GB
  Method 2 - Alibaba Cloud precise formula (recommended):
    NameNode_Heap_GB = (Files_Millions + Blocks_Millions) x 0.5 GB
  Take the larger of the two as conservative estimate.

Step 3: Estimate other Master service memory requirements
  ResourceManager heap: 4-8 GB (based on estimated YARN total vCPU, >=100 vCPU takes 8GB)
  HBase HMaster heap: 2-4 GB (if HBase deployed)
  Hive Metastore heap: 2-4 GB
  ZooKeeper heap: 1-2 GB
  Other services (Oozie/Ranger etc.): 2-4 GB
  OS reserved + JVM overhead: 8-16 GB

Step 4: Calculate Master node total memory requirement
  Master_Memory_GB = NameNode_Heap + RM_Heap + Other_Services + OS_Reserved
  Total_Master_Memory = Master_Memory_GB x (1 + 0.3)  # 30% JVM overhead margin

Step 5: Select ECS spec (by algorithm result, no forced upgrade)
  IF Total_Master_Memory <= 64 GB  -> ac9.4xlarge.4 (16 vCPU, 64 GB)
  IF Total_Master_Memory <= 128 GB -> ac9.8xlarge.4 (32 vCPU, 128 GB)
  IF Total_Master_Memory <= 256 GB -> ac9.16xlarge.4 (64 vCPU, 256 GB)
  IF Total_Master_Memory > 256 GB  -> ac9.16xlarge.4 + increase Master node count
  Greenfield scenario: strictly select spec by algorithm result, avoid over-provisioning
     Small cluster (business < 50 vCPU): algorithm result usually <= 64GB -> use 64GB (satisfies MRS hard constraint)
     Medium cluster (50-500 vCPU): algorithm result usually 64-128GB -> use 128GB
     Large cluster (> 500 vCPU): algorithm result > 128GB -> use 256GB+

Step 6: OBS storage-compute separation mode adjustment (reduce NameNode heap, no forced memory upgrade)
  IF OBS_mode == YES:
    - HDFS stores only metadata/temp files; Blocks significantly reduced
    - NameNode_Heap can be reduced 50-70% (Step 2 result x 0.3)
    - ResourceManager schedules by actual estimated YARN total vCPU (small cluster scheduling load is light)
    - Does NOT enforce minimum 128GB! Select spec per Step 1-5 algorithm result
    - Only upgrade when algorithm result > current spec memory
```

> Greenfield scenario has **no Step 7 utilization check** (no original cluster); if a benchmark cluster exists, use the migration scenario skill (huawei-cloud-mrs-migration-planner).

## 4. Quick Estimation Table

**Quick estimation table** (typical scenarios, non-OBS storage-compute separation):

| Total Storage S_TB | Estimated File Count | Estimated Block Count | NameNode Heap | Master Total Memory | Recommended Flavor |
|---------------------|---------------------|----------------------|---------------|---------------------|-------------------|
| < 10 TB | < 1M | < 1.5M | 1-2 GB | ~32 GB | ac9.4xlarge.4 (64GB) |
| 10-50 TB | 1M-5M | 1.5M-7.5M | 2-6 GB | ~48 GB | ac9.4xlarge.4 (64GB) |
| 50-200 TB | 5M-20M | 7.5M-30M | 6-25 GB | ~80 GB | ac9.8xlarge.4 (128GB) |
| 200-500 TB | 20M-50M | 30M-75M | 25-60 GB | ~128 GB | ac9.16xlarge.4 (256GB) |
| > 500 TB | > 50M | > 75M | > 60 GB | > 160 GB | ac9.16xlarge.4 (256GB) |

**OBS Storage-Compute Separation Mode Quick Estimation Table** (HDFS stores only metadata; select spec by algorithm result, no forced upgrade):

| Total Storage S_TB | OBS Mode NameNode Heap | Master Total Memory (Algorithm) | Recommended Flavor (By Algorithm) |
|---------------------|------------------------|--------------------------------|----------------------------------|
| < 100 TB | 2-4 GB | ~48 GB | ac9.4xlarge.4 (64GB) — satisfies MRS hard constraint |
| 100-500 TB | 4-8 GB | ~64 GB | ac9.4xlarge.4 (64GB) or ac9.8xlarge.4 (128GB) by vCPU baseline |
| > 500 TB | 8-16 GB | ~80 GB | ac9.8xlarge.4 (128GB) |

OBS mode does not enforce 128GB: if algorithm result <= 64GB use 64GB (satisfies MRS hard constraint); only upgrade when vCPU baseline corresponding spec memory < algorithm result.

## 5. Example Calculation (Greenfield Scenario)

**Example**: New warehouse cluster, estimated total storage 410TB, OBS storage-compute separation, estimated 36 Core nodes (128C) -> Core total cores 4608:
```
Master node count: Core total cores 4608 >= 100 -> 5 nodes (OMS-separate)
Master vCPU: Core nodes 36 (20-50 range) -> 32-core baseline

Metadata estimate: 410TB x 300K files/TB = 123M?
  -> OBS mode actually manages significantly fewer files; estimate by OBS cache/temp files: ~20M files, 30M blocks
NameNode heap (OBS reduced 70%): (20+30) x 0.5 x 0.3 = 7.5 GB
ResourceManager heap: 8 GB (schedules 4608 cores)
Other services: 8 GB
OS + JVM overhead: 16 GB
Master total memory: 7.5 + 8 + 8 + 16 = 39.5 GB x 1.3 = 51 GB
vCPU baseline 32 cores -> ac9.8xlarge.4 (32C/128G): vCPU baseline 32 cores corresponding spec 128GB > algorithm 51GB — no further upgrade needed

**Small cluster comparison example**: New data middle platform, estimated 16 vCPU business, 3 Core nodes (16C) -> Core total cores 48:
```
Master node count: Core total cores 48 < 100 -> 3 nodes (Compact)
Master vCPU: Core nodes 3 <= 20 -> 16-core baseline (ac9.4xlarge.4)
OBS mode metadata small, NameNode heap ~2GB, RM heap 4GB (schedules 16 vCPU), other 8GB, OS 8GB
Master total memory: 2 + 4 + 8 + 8 = 22GB x 1.3 = 28.6 GB
Algorithm result 28.6GB <= 64GB -> ac9.4xlarge.4 (16C/64G) x 3 — satisfies MRS hard constraint, no forced upgrade to 128GB
```
```
