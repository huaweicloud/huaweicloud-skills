# ECS Flavor Catalog and Node Types

> Extracted from SKILL.md Phase 3.1-3.3. See main document for detailed sizing.

## 1. MRS Node Types

| Node Type | Role | Sizing Considerations |
|-----------|------|----------------------|
| **Master** | Management + control (NameNode, ResourceManager, HMaster, etc.) | High memory, high reliability, min 64GB RAM (MRS 3.x). **Data disk: 600GB General SSD × 1 (for metadata/logs, same as Core/Task single disk)** |
| **Core** | Compute + storage (DataNode, NodeManager, RegionServer, Broker) | Balanced CPU/memory, local SSD for shuffle. **Data disk: flexible, per-node shuffle = vCPU×40GB split into disks of 600-800GB (Shuffle+HDFS)** |
| **Task** | Compute-only (NodeManager, no DataNode) — Shuffle on local disk | Scalable, can be added/removed dynamically. **Data disk: SAME as Core nodes (flexible 600-800GB disks, per-node shuffle = vCPU×40GB). Task nodes MUST have data disks matching Core for Spark/Flink shuffle spill.** |

## 2. Deployment Type Selection

| Deployment Type | Node Count | Master Nodes | Use Case |
|----------------|-----------|--------------|----------|
| **Compact** (co-located management) | < 100 | 3 (when original cluster cores < 100) / 5-11 | Small clusters, cost-optimized |
| **OMS-separate** (separated management) | 100-500 | 5-11 | Medium clusters, high concurrency |
| **Full-size** (separated data) | > 500 | 9-11 | Large clusters, component isolation |

**Master Node Count Rule**:
```
Master node count:
  IF original cluster total cores < 100  -> 3 Master nodes (Compact, default)
  IF original cluster total cores >= 100 -> 5-11 Master nodes (OMS-separate)
  IF total Core nodes > 500             -> 9-11 Master nodes (Full-size)
```

## 3. aC9 Series Flavor Catalog

### ⭐ Default Series: General Computing-plus aC9 — CPU-intensive workloads

**aC9** is the **default recommended** series for MRS clusters. Based on Huawei Cloud's
distributed QingTian 1.0 architecture with 4.1GHz max turbo frequency, delivering
40%+ cost-performance improvement over previous generations.

- CPU/Memory ratio: 1:2 / 1:4
- vCPU range: 2-192
- Base/Turbo frequency: 2.7GHz / 4.1GHz
- Max intranet bandwidth: 120Gbps
- Max packet rate: 30 million

**aC9 1:2 Series (General Computing - CPU-intensive)**

| Flavor | vCPU | Memory (GB) | Network (Gbps) | Monthly (¥) | Best For |
|--------|------|-------------|----------------|------------|----------|
| ac9.4xlarge.2 | 16 | 32 | 30 | 1,412 | Small Core nodes, CPU-heavy |
| ac9.8xlarge.2 | 32 | 64 | 40 | 2,825 | Medium Core, Spark/Flink |
| ac9.16xlarge.2 | 64 | 128 | 60 | 5,650 | Large Core, high CPU |
| ac9.32xlarge.2 | 128 | 256 | 100 | 11,300 | XLarge Core, max compute |
| ac9.48xlarge.2 | 192 | 384 | 120 | 16,950 | XXLarge Core, ultra scale |

**aC9 1:4 Series (General Computing - Balanced)**

| Flavor | vCPU | Memory (GB) | Network (Gbps) | Monthly (¥) | Best For |
|--------|------|-------------|----------------|------------|----------|
| ac9.4xlarge.4 | 16 | 64 | 30 | 1,862 | Master nodes (>=64GB RAM) |
| ac9.8xlarge.4 | 32 | 128 | 40 | 3,724 | Core nodes, balanced |
| ac9.16xlarge.4 | 64 | 256 | 60 | 7,448 | Large Core, memory+compute |
| ac9.32xlarge.4 | 128 | 512 | 100 | 14,895 | XLarge Core, high memory |
| ac9.48xlarge.4 | 192 | 768 | 120 | 22,343 | XXLarge Core, max memory |

**aC9 Master Node Recommended Specifications** (based on industry NameNode heap sizing standards):

Master node flavor selection is **not based on Core node count**, but on **HDFS metadata scale (file count/block count)** and **cluster management load** for scientific calculation.

**Industry Standard References**:
- Cloudera/CDH official: 1GB NameNode heap memory / 1 million Blocks ([Reference](https://docs.cloudera.com/documentation/enterprise/5-15-x/topics/admin_nn_memory_config.html))
- Alibaba Cloud EMR official: (file count in millions + block count in millions) × 512MB ([Reference](https://help.aliyun.com/zh/emr/emr-on-ecs/user-guide/jvm-memory-tuning))
- Huawei Cloud MRS hard constraint: Master node memory >= 64GB (MRS 3.x mandatory)

| Metadata Scale | NameNode Heap Estimate | Recommended Master Memory | Recommended Flavor | Monthly (¥) |
|----------------|----------------------|--------------------------|-------------------|------------|
| < 1 million files | 2-4 GB | 64 GB | ac9.4xlarge.4 (16 vCPU) | 1,862 |
| 1-10 million files | 4-10 GB | 64-128 GB | ac9.4xlarge.4 / ac9.8xlarge.4 | 1,862-3,724 |
| 10-50 million files | 10-50 GB | 128-256 GB | ac9.8xlarge.4 / ac9.16xlarge.4 | 3,724-7,448 |
| > 50 million files | > 50 GB | 256 GB+ | ac9.16xlarge.4 (64 vCPU) | 7,448 |

**OBS Storage-Compute Separation Mode Special Notes**:
- In OBS storage-compute separation mode, data is stored in OBS; HDFS only stores metadata and small files
- Block count managed by NameNode is significantly reduced (only local cache/temp files)
- Master spec can be appropriately reduced, but ResourceManager scheduling load must still be considered
- Recommend at least ac9.8xlarge.4 (32 vCPU, 128GB) to ensure YARN scheduling capability

## 4. Alternative Series Flavors

### General Computing (s7 Series) — Cost-Optimized

General computing type, no QingTian architecture, lower cost-performance than aC9 but lower unit price, suitable for cost-sensitive scenarios.

| Flavor | vCPU | Memory (GB) | Ratio | Best For |
|--------|------|-------------|-------|----------|
| s7.2xlarge.4 | 8 | 32 | 1:4 | Small Core/Task, cost priority |
| s7.4xlarge.4 | 16 | 64 | 1:4 | Master (minimum), Core |
| s7.8xlarge.4 | 32 | 128 | 1:4 | Core, balanced |
| s7.16xlarge.4 | 64 | 256 | 1:4 | Large Core |

### Memory-Optimized (m9/m6 Series) — Memory-Intensive

Memory-optimized type, 1:8 high memory ratio, suitable for NameNode/HMaster and other memory-intensive management roles.

| Flavor | vCPU | Memory (GB) | Ratio | Best For |
|--------|------|-------------|-------|----------|
| m6.2xlarge.8 | 8 | 64 | 1:8 | Small Master nodes |
| m6.4xlarge.8 | 16 | 128 | 1:8 | Medium Master, HBase |
| m6.8xlarge.8 | 32 | 256 | 1:8 | Large Master, HBase-intensive |
| m6.16xlarge.8 | 64 | 512 | 1:8 | XLarge Master, heavy HBase |

### Ultra-High I/O (i3 Series) — Storage-Intensive

Ultra-high I/O type, local SSD, suitable for Kafka/ClickHouse and other high I/O throughput scenarios.

| Flavor | vCPU | Memory (GB) | Best For |
|--------|------|-------------|----------|
| i3.4xlarge.8 | 16 | 128 | HBase/ClickHouse with local SSD |
| i3.8xlarge.8 | 32 | 256 | Large HBase/ClickHouse |
| i3.16xlarge.8 | 64 | 512 | XLarge HBase/ClickHouse |

### Previous-Gen (c6 Series) — Previous Generation Cost Type

| Flavor | vCPU | Memory (GB) | Best For |
|--------|------|-------------|----------|
| c6.4xlarge.4 | 16 | 64 | Legacy small Core |
| c6.8xlarge.4 | 32 | 128 | Legacy balanced |
| c6.16xlarge.4 | 64 | 256 | Legacy large |

## 5. Series Selection Matrix (Master/Core Can Use Different Series)

### Series Type Comparison

| Series Type | Series | Ratio Range | Characteristics | Applicable Scenarios |
|-------------|--------|-------------|-----------------|---------------------|
| General Computing-plus | aC9 | 1:2, 1:4 | QingTian 1.0, 4.1GHz, cost-performance +40% | Spark/Flink/ETL, balanced workload |
| General Computing | s7 | 1:4 | Standard, no QingTian, low unit price | Cost-sensitive, non-CPU-intensive |
| Memory-Optimized | m9/m6 | 1:8 | High memory ratio | Master/HBase/ClickHouse metadata |
| Ultra-High I/O | i3 | 1:8 | Local SSD high throughput | Kafka/ClickHouse |

### Series Selection Algorithm by Node Role

```
Master Node Series Selection:
  Step 1: Calculate Master total memory requirement (Step 1-4 of master-sizing-algorithm)
  Step 2: Determine series:
    IF Master_Memory <= 64GB  -> General Computing-plus aC9 1:4 (ac9.4xlarge.4)
    IF Master_Memory <= 128GB -> General Computing-plus aC9 1:4 (ac9.8xlarge.4)
         OR Memory-Optimized m6 1:8 (m6.4xlarge.8) — HBase cluster preferred
    IF Master_Memory <= 256GB -> Memory-Optimized m6 1:8 (m6.8xlarge.8)
    IF Master_Memory > 256GB  -> Memory-Optimized m6 1:8 (m6.16xlarge.8)
  Step 3: Migration scenario utilization check (Step 7) — if original cluster Master memory utilization is high (>70%),
          prefer Memory-Optimized series to reserve sufficient margin

  Default: aC9 1:4 (General Computing-plus, optimal cost-performance)
  HBase cluster: m6 1:8 (Memory-Optimized, HMaster heap memory requirement large)
  Large-scale metadata (>10 million files): m6 1:8 (Memory-Optimized)

Core Node Series Selection:
  ⚠️ Constraint: All Core nodes must use the same flavor (uniform deployment); heterogeneous not allowed!
     Mixed workload requirements are resolved by selecting one flavor via the single plan
     minimum-surplus algorithm, not by using different flavors within Core.
     Kafka/ClickHouse etc. that need a different series MUST be deployed as an independent
     node group, NOT mixed into the Core group.
  Step 1: Determine primary workload type
  Step 2: Select series by workload:
    Spark/Flink/ETL (CPU-intensive) -> General Computing-plus aC9 1:2 or 1:4
    HBase (memory-intensive)         -> Memory-Optimized m6 1:8
    Kafka (I/O-intensive)            -> Ultra-High I/O i3 1:8
    ClickHouse (I/O+memory)          -> Ultra-High I/O i3 1:8
    Mixed workload                   -> General Computing-plus aC9 1:4 (default)
    Cost-sensitive (non-CPU-intensive) -> General Computing s7 1:4

  Default: aC9 1:4 (General Computing-plus, balanced cost-performance)
  Special: HBase-primary -> m6, Kafka-primary -> i3

Task Node Series Selection:
  - Default follows Core node series (same type, can differ in flavor)
  - Cost optimization scenario: can select General Computing s7 1:4 (lower unit price, on-demand billing)
```

### Master and Core Series Combination Examples

| Scenario | Master Series | Core Series | Reason |
|----------|---------------|-------------|--------|
| Spark/ETL cluster | aC9 1:4 (ac9.8xlarge.4) | aC9 1:2/1:4 | Master management + Core compute, both Computing-plus |
| HBase cluster | m6 1:8 (m6.4xlarge.8) | m6 1:8 (m6.8xlarge.8) | HMaster/HRegionServer both need high memory |
| Kafka cluster | aC9 1:4 (ac9.4xlarge.4) | i3 1:8 (i3.4xlarge.8) | Master management + Core local SSD high I/O |
| Mixed workload cluster | m6 1:8 (m6.4xlarge.8) | aC9 1:4 (ac9.8xlarge.4) | Master high memory + Core balanced compute |
| Cost-sensitive cluster | s7 1:4 (s7.4xlarge.4) | s7 1:4 (s7.8xlarge.4) | All General Computing, lowest cost |
