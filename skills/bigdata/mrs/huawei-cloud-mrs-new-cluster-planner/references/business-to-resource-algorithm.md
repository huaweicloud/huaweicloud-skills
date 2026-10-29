# Business Requirements -> Resource Estimation Algorithm (Core of Greenfield Scenario)

> Extracted from SKILL.md Phase 3. Greenfield scenario has no existing cluster resource benchmark; resource targets are derived from business load models.
> All coefficients are industry experience-based estimates; must be annotated as "estimated value" in report and confirmed by user.

## 1. Estimation Overall Flow

```
Step 1: Identify load type (offline batch / real-time streaming / interactive query / HBase / Kafka, multi-select allowed)
Step 2: Collect business parameters (daily increment / window / throughput / concurrency / QPS)
Step 3: Estimate vCPU and memory per load model
Step 4: Sum (mixed load off-peak can apply x0.8 discount)
Step 5: Show estimation process to user for confirmation (formula + coefficients + results)
Step 6: Confirmed resources become Phase 4 selection targets V(vCPU)/M(memory)
```

## 2. Offline Batch Estimation Model (Hive/Spark/MapReduce)

**Principle**: Process daily increment D TB within compute window H hours each day; required vCPU = data volume x unit workload / window duration. **Important: must consider hot data参与计算的数据量，不能仅看增量数据，因为任务可能需要拉取历史热数据一起计算。**

```
Core formula:
  D_compute = D_increment + D_hot_compute
  V (vCPU)  = D_compute x W_CPU / H_hours
  M (GB)    = V x R

Parameter description:
  D_increment   = daily incremental data (TB/day, pre-compression logical volume)
  D_hot_compute = hot data参与计算量 = existing_data_TB × hot_data_ratio × hot_compute_ratio
  D_compute     = 实际参与计算的总数据量（增量 + 热数据参与计算部分）
  W_CPU         = unit workload coefficient (vCPU·hours/TB, selected by business complexity)
  H_hours       = compute window duration (hours/day)
  R             = memory ratio (by complexity: simple 1:2, standard/complex 1:4)

Hot data parameters:
  existing_data_TB  = 现有数据量（TB）
  hot_data_ratio    = 热数据比例（用户提供，如80%表示80%现有数据为热数据）
  hot_compute_ratio = 热数据参与计算比例（默认100%，即所有热数据都可能参与计算；可按实际调整）

Unit workload coefficient W_CPU (experience values):
  Simple ETL (filter/clean/direct ingest)         : 20 vCPU·h/TB
  Standard warehouse (multi-table join/aggregate/multi-stage scheduling) : 40 vCPU·h/TB
  Complex compute (iterative/ML/large-scale Shuffle) : 80 vCPU·h/TB
```

**Example 1 (传统场景，仅增量)**: Daily increment 5TB, no hot data参与计算, standard warehouse, window 6 hours:
```
D_compute = 5 + 0 = 5 TB
V = 5 x 40 / 6 = 34 vCPU
M = 34 x 4 = 136 GB (standard warehouse uses 1:4)
```

9

**Example 2 (热数据参与计算场景)**: Daily increment 0.001TB, existing data 1TB, hot data 80%, standard warehouse, window 8 hours:
```
D_hot_compute = 1 × 0.8 × 1.0 = 0.8 TB
D_compute = 0.001 + 0.8 = 0.801 TB
V = 0.801 x 40 / 8 = 4.0 vCPU
M = 4.0 x 4 = 16 GB
→ 向上取整到8的倍数：8 vCPU / 32 GB
```

**Notes**:
- D_increment should be pre-compression logical volume; if user provides physical storage volume, annotate
- **必须考虑热数据参与计算**：不能仅看增量数据，任务可能拉取历史热数据一起计算，D_compute = 增量 + 热数据参与计算量
- Multiple task waves run serial/parallel within window; W_CPU already includes scheduling overhead redundancy
- Round result up to multiple of 8 (align with spec granularity)

## 3. Real-time Streaming Estimation Model (Flink/Spark Streaming)

**Principle**: Estimate resident resources by consumption parallelism (Kafka partition count) or data throughput.

```
Method 1 - By partition count (recommended, job parallelism = partition count):
  V (vCPU) = Partitions x 1
  M (GB)   = V x 4

Method 2 - By throughput:
  V (vCPU) = Throughput_MBps / 10
  M (GB)   = V x 4

Parameter description:
  Partitions        = total Kafka Topic partition count (sum of all Topics consumed by real-time jobs)
  Throughput_MBps   = peak throughput (MB/second)
  Strict latency / large window State jobs: memory coefficient increased from 4 to 6-8
```

**Example**: Kafka 60 partitions, peak 50MB/s, Flink window aggregation:
```
Method 1: V = 60 x 1 = 60 vCPU, M = 240 GB
Method 2: V = 50 / 10 = 5 vCPU (lower bound check only)
Take larger value: 60 vCPU / 240 GB
```

**Notes**:
- Real-time jobs are 7x24 resident; resources are not reclaimable; calculate Core directly as resident
- Stateful jobs (large window / RocksDB State) have significantly higher memory requirements
- Job restart / backpressure recovery needs margin; recommend estimation result x1.2 before spec selection

## 4. Interactive Query Estimation Model (Presto/Impala/Hive LLAP/Doris)

```
Core formula:
  V (vCPU) = Q_Concurrent x 4
  M (GB)   = V x 4

Parameter description:
  Q_Concurrent = concurrent query users (users/applications executing queries simultaneously)
  Complex ad-hoc queries (large table join / multi-level aggregate): single concurrency coefficient increased from 4 to 8
```

**Example**: 20 concurrent analysts, standard BI queries:
```
V = 20 x 4 = 80 vCPU
M = 80 x 4 = 320 GB
```

## 5. HBase Estimation Model

**Principle**: HBase is memory-intensive; estimate by read QPS and hot data volume on two dimensions; take the larger value.

```
Method 1 - By QPS:
  V (vCPU) = QPS_wan / 0.6      (per 10K QPS read ~= 1.7 vCPU)
  M (GB)   = V x 8              (memory-optimized 1:8)

Method 2 - By hot data volume:
  M (GB)   = HotData_TB x 16    (per TB hot data ~= 16GB, includes BlockCache + MemStore)
  V (vCPU) = M / 8

Write QPS is converted at 2x read QPS equivalent. Take the larger of the two methods.
Flavor: memory-optimized m6 (1:8).
```

**Example**: 100K QPS read, hot data 50TB:
```
Method 1: V = 10 / 0.6 = 17 vCPU, M = 136 GB
Method 2: M = 50 x 16 = 800 GB, V = 100 vCPU
Take larger value: 100 vCPU / 800 GB (Method 2 dominates)
```

## 6. Kafka Estimation Model

```
Core formula:
  V (vCPU) = DailyMsg_100M x 2
  M (GB)   = V x 4

Parameter description:
  DailyMsg_100M = daily message volume (100M messages/day)
  Throughput check: 100MB/s ~= 8 vCPU + 32 GB (take larger value)
  Flavor: ultra-high IO i3 (local SSD, sequential write intensive)
  Disk: calculate local disk capacity by retention days x daily increment x replica count (2)
```

**Example**: Daily 300M messages (1KB/message):
```
V = 3 x 2 = 6 vCPU, M = 24 GB
Throughput = 300M x 1KB / 86400s = 3.5MB/s (check passed, take base value)
Disk = 300M x 1KB x 2 replicas x 7 days retention = 4TB/node distributed
```

## 7. Mixed Load Summation Rules

```
Summation algorithm:
  V_total = Sum V_i (per-load estimation results)
  M_total = Sum M_i

Off-peak discount (optional):
  IF load peaks are clearly off-peak (e.g., overnight batch + daytime real-time/query):
    V_total = Sum V_i x 0.8
    M_total = Sum M_i x 0.8
    Report must explain off-peak discount basis

Peak buffer:
  IF user confirms peak period resources sustain >90%:
    V_total = V_total x 1.2
    M_total = M_total x 1.2
```

## 8. Storage Resource Estimation

```
Total storage (logical volume):
  S_TB = existing_data + daily_increment_D_TB x retention_days_Days x compression_ratio_C

Compression ratio C (experience value, must ask user):
  ORC/Parquet columnar compression : 0.3 - 0.5 (default 0.5)
  TextFile + Gzip                  : 0.5 - 0.7
  Raw text uncompressed            : 1.0

OBS storage-compute separation:
  OBS_capacity = S_TB (report the actual required single-replica storage directly; no package tier rounding)

Local HDFS:
  HDFS_total = S_TB x 3 (three replicas) -> distribute to Core node data disks (evaluate whether exceeds Shuffle disk capacity)
```

**Example**: Existing 50TB, daily increment 5TB, retention 180 days, ORC compression 0.4:
```
S = 50 + 5 x 180 x 0.4 = 50 + 360 = 410 TB
OBS_capacity = 410 TB (actual required storage, no package tier)
```

## 9. Estimation Result Display Template (For User Confirmation)

```
Resource estimation details (estimated values, please confirm):

1. Offline batch (Spark warehouse):
   Daily increment 5TB x standard warehouse coefficient 40 vCPU·h/TB / window 6h = 34 vCPU
   Memory: 34 x 4 (1:4 balanced) = 136 GB

2. Real-time streaming (Flink):
   Kafka 60 partitions x 1 vCPU = 60 vCPU
   Memory: 60 x 4 = 240 GB (resident 7x24)

3. Sum (batch overnight / real-time all day, peak off-peak x0.8):
   vCPU: (34+60) x 0.8 = 76 vCPU
   Memory: (136+240) x 0.8 = 301 GB

4. Storage (ORC compression 0.4, retention 180 days):
   50 + 5x180x0.4 = 410 TB -> OBS capacity 410 TB (actual required, no package tier)

Are the above estimated resources confirmed? (Proceed to node spec selection after confirmation)
```
