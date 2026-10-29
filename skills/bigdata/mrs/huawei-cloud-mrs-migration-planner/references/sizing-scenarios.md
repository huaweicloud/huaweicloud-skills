# Common Spec Selection Scenarios

> Extracted from SKILL.md Quick Reference.

## Scenario A: Small Data Warehouse (Spark + Hive, < 100 cores)

```
Cluster Type: Analysis
Version: MRS 3.3.0-LTS
Components: Hadoop, Spark2x, Hive, ZooKeeper, Tez
Deployment: Compact (3 Master nodes, original < 100 cores)
Master: ac9.4xlarge.4 (16 vCPU, 64 GB) × 3
  Master Data Disk: 1×600GB General SSD per Master (metadata+logs)
Core:  ac9.8xlarge.4 (32 vCPU, 128 GB) × 5
  Data Disk: 2 × 640GB General SSD per Core (32×40GB=1280GB shuffle -> 2 disks × 640GB)
System Disk: 480GB High IO per node
Data Volume: 10-50 TB
Estimated Monthly: ¥15,000 - ¥25,000
```

## Scenario B: Medium HBase Real-time

```
Cluster Type: Analysis
Version: MRS 3.3.0-LTS
Components: Hadoop, HBase, ZooKeeper, Ranger (Kerberos)
Deployment: OMS-separate (5-11 Master nodes)
Master: ac9.8xlarge.4 (32 vCPU, 128 GB) × 5
  Master Data Disk: 1×600GB General SSD per Master
Core:  m6.8xlarge.8 (32 vCPU, 256 GB) × 8  [memory-optimized for HBase]
  Data Disk: 2 × 640GB General SSD per Core (32×40GB=1280GB shuffle)
System Disk: 480GB High IO per node
Data Volume: 50-200 TB
Estimated Monthly: ¥40,000 - ¥80,000
```

## Scenario C: Large Hybrid Batch-Streaming (Hybrid)

```
Cluster Type: Hybrid
Version: MRS 3.3.0-LTS
Components: Hadoop, Spark2x, Hive, Flink, Kafka, Flume, ZooKeeper, Ranger
Deployment: OMS-separate (5-11 Master nodes)
Master: ac9.16xlarge.4 (64 vCPU, 256 GB) × 7
  Master Data Disk: 1×600GB General SSD per Master
Core:  ac9.16xlarge.4 (64 vCPU, 256 GB) × 30
  Data Disk: 4 × 640GB General SSD per Core (64×40GB=2560GB shuffle)
Kafka (independent node group, not in Core): i3.4xlarge.8 (16 vCPU, 128 GB) × 10
  Data Disk: local SSD for high I/O throughput (Kafka Broker, separate from Core uniform constraint)
Task:  ac9.8xlarge.4 (32 vCPU, 128 GB) × 10-50 (elastic)
  Task Data Disk: 2 × 640GB General SSD per Task (for Shuffle, same as Core config)
System Disk: 480GB High IO per node
Data Volume: 200+ TB
Estimated Monthly: ¥120,000 - ¥250,000+
```

## Scenario D: Storage-Compute Separation Data Lake (OBS)

```
Cluster Type: Custom
Version: MRS 3.3.0-LTS
Components: Hadoop, Spark2x, Hive, Hudi, HetuEngine, ZooKeeper, Ranger, Guardian
Storage: OBS (storage-compute separation) — no local data disks needed for Core
Master: ac9.8xlarge.4 (32 vCPU, 128 GB) × 3
  Master Data Disk: 1×600GB General SSD per Master (metadata+logs)
  Note: OBS storage-compute separation mode recommends minimum 128GB flavor to ensure ResourceManager scheduling capability
Core:  ac9.8xlarge.2 (32 vCPU, 64 GB) × 15 [1:2 ratio, compute-only]
  Data Disk: Not needed (OBS storage)
System Disk: 480GB High IO per node
OBS: 100 TB (est. ¥0.099/GB/month = ¥9,900/month)
Estimated Monthly: ¥55,000 - ¥85,000 (lower than HDFS due to OBS savings)
```

## Scenario E: CDH Migration - OBS Actual Capacity + Master/Data Disk + Single Plan (Minimum Surplus)

```
Original CDH Cluster:
  Total Cores: 1480, Memory: 4380 GB, Data: 560 TB (3 replicas)
  Storage: OBS storage-compute separation (actual required capacity)

[Single Plan Calculation Process]
  Step 1: Target resources (no buffer, single plan uses original cluster resources directly)
    Target_vCPU = 1480
    Target_mem  = 4380 GB
    R = 4380 / 1480 = 2.96 < 3 -> try 1:2 first, upgrade to 1:4 if memory insufficient

  Step 2: Core node single plan calculation (minimum surplus)
    Candidate 1: ac9.32xlarge.4 (128C/512G, 1:4)
      N = max(ceil(1480/128), ceil(4380/512)) = max(12, 9) = 12
      Total: 12×128=1536C (+3.8%), 12×512=6144G (+40.2%)
      Total_excess = 3.8% + 40.2% = 44.0%

    Candidate 2: ac9.32xlarge.2 (128C/256G, 1:2)
      N = max(ceil(1480/128), ceil(4380/256)) = max(12, 18) = 18
      Total: 18×128=2304C (+55.7%), 18×256=4608G (+5.2%)
      Total_excess = 55.7% + 5.2% = 60.9%

    Candidate 3: ac9.16xlarge.4 (64C/256G, 1:4)
      N = max(ceil(1480/64), ceil(4380/256)) = max(24, 18) = 24
      Total: 24×64=1536C (+3.8%), 24×256=6144G (+40.2%)
      Total_excess = 44.0% (same as Candidate 1, but more nodes)

    -> Candidate 1 (ac9.32xlarge.4×12) has minimum Total_excess (44.0%) with fewest nodes
    -> Final single plan: ac9.32xlarge.4 × 12 (1536C/6144G)
    Data disks: 8×640GB SSD per node (128×40=5120GB shuffle -> N=8, ceil(5120/8)=640GB)
    Total shuffle: 8 × 640GB × 12 nodes = 61,440 GB = 60.0 TB

[OBS Capacity Calculation]
  HDFS (3 replicas): 560 TB
  Actual required single replica: 560 / 3 = 187 TB
  OBS capacity: 187 TB (no package tier)
  Cost: 187 × 1024 × ¥0.099 = ¥18,982/month

[Master Data Disk]
  5× ac9.8xlarge.4 (32C/128G)
  Data disk: 1×600GB General SSD per node (metadata+logs)
  Sizing basis: OBS storage-compute separation -> NameNode heap requirement reduced 70% ≈7.5GB; RM needs to schedule 1536 cores -> RM heap 8GB; total memory requirement ≈51GB -> select 128GB flavor

Final Configuration (single plan output):
  Master: 5× ac9.8xlarge.4 (32C/128G) + 1×600GB SSD per node

  Core:  12× ac9.32xlarge.4 (128C/512G) [monthly subscription]
         8×640GB General SSD per node (Shuffle)
         Total: 1536C / 6144G (CPU +3.8%, Mem +40.2%, Total_excess 44.0% lowest)
         Total shuffle: 60.0 TB

  OBS:   187TB actual required capacity (Guardian integration)

  Cost Breakdown (monthly):
    Master ECS+disk:  ¥20,720
    Core ECS+disk:    ¥173,760 (12×¥14,895 + 12×8×640GB×¥0.70)
    System disk+MRS mgmt fee:  ¥10,080
    OBS storage:          ¥18,982
    Monthly total:        ≈¥223,542/month

  vs original CDH cluster: 1480C/4380G -> MRS 1536C/6144G (CPU +3.8%, Mem +40.2%)
  Estimated Monthly: ¥220,000 - ¥250,000
```
