# ECS Flavor Catalog (MRS-Supported) and Node Types

> **Localized from Huawei Cloud official documentation** — "MRS所使用的弹性云服务器规格"
> Source: <https://support.huaweicloud.com/api-mrs/mrs_01_9006.html> (page updated 2026-09-24 GMT+08:00)
>
> This catalog mirrors the official list of ECS flavors **supported by MRS**. Flavor selection
> in Phase 4 **MUST pick flavors from the lists below** — do not recommend any series/flavor that
> is not present on the official MRS-supported list (e.g. do **not** use s-series or 192-vCPU
> flavors, which MRS does not list). Network bandwidth is **not** published on this page and is
> therefore intentionally omitted.

## 0. Spec Naming Rule (AB.C.D)

Example: `m2.8xlarge.8`

| Field | Meaning | Example |
|-------|---------|---------|
| **A** | Series letter: `s` = General, `c` = Computing, `m` = Memory | `m` = Memory-optimized |
| **B** | Series number (generation within the series) | `s1` = General I, `s2` = General II |
| **C** | Spec size | `medium`, `large`, `xlarge` |
| **D** | Memory : CPU ratio (as a number) | `.4` = 4GB per vCPU (1:4), `.8` = 8GB per vCPU (1:8) |

## 1. MRS Node Types

| Node Type | Role | Sizing Considerations |
|-----------|------|----------------------|
| **Master** | Management + control (NameNode, ResourceManager, HMaster, etc.) | High memory, high reliability, min 64GB RAM (MRS 3.x). **Data disk: 600GB General SSD x 1 (for metadata/logs, same as Core/Task single disk)** |
| **Core** | Compute + storage (DataNode, NodeManager, RegionServer, Broker) | Balanced CPU/memory, local SSD for shuffle. **Data disk: 灵活配置，单盘600~800GB，Shuffle需求=vCPU×40GB** |
| **Task** | Compute-only (NodeManager, no DataNode) — Shuffle on local disk | Scalable, can be added/removed dynamically. **Data disk: SAME as Core nodes (灵活配置，单盘600~800GB). Task nodes MUST have data disks matching Core for Spark/Flink shuffle spill.** |

## 2. Deployment Type Selection

| Deployment Type | Node Count | Master Nodes | Use Case |
|----------------|-----------|--------------|----------|
| **Compact** (co-located management) | < 100 | 3 (when planned Core total cores < 100) / 5-11 | Small clusters, cost-optimized |
| **OMS-separate** (separated management) | 100-500 | 5-11 | Medium clusters, high concurrency |
| **Full-size** (separated data) | > 500 | 9-11 | Large clusters, component isolation |

**Master Node Count Rule**:
```
Master node count:
  IF planned Core total cores < 100   -> 3 Master nodes (Compact, default)
  IF planned Core total cores >= 100  -> 5-11 Master nodes (OMS-separate)
  IF total Core nodes > 500           -> 9-11 Master nodes (Full-size)
```

## 3. MRS-Supported ECS Flavor Families (Official, Localized)

> Virtualization types: `KVM` = 硬件虚拟化; `擎天` = 基于擎天架构的自研极简虚拟化.

### 3.1 General Computing-plus (C series — 通用计算增强型)

| Type | vCPU | Memory (GB) | Flavor | Virtualization |
|------|------|-------------|--------|----------------|
| C3 | 32 | 64 | c3.8xlarge.2 | KVM |
| C3 | 16 | 64 | c3.4xlarge.4 | KVM |
| C3 | 32 | 128 | c3.8xlarge.4 | KVM |
| C3ne | 60 | 256 | c3ne.15xlarge.4 | KVM |
| C3ne | 32 | 64 | c3ne.8xlarge.2 | KVM |
| C3ne | 16 | 64 | c3ne.4xlarge.4 | KVM |
| C3ne | 32 | 128 | c3ne.8xlarge.4 | KVM |
| C6 | 32 | 64 | c6.8xlarge.2 | KVM |
| C6 | 64 | 128 | c6.16xlarge.2 | KVM |
| C6 | 16 | 64 | c6.4xlarge.4 | KVM |
| C6 | 32 | 128 | c6.8xlarge.4 | KVM |
| C6 | 64 | 256 | c6.16xlarge.4 | KVM |
| C6s | 32 | 64 | c6s.8xlarge.2 | KVM |
| C6s | 64 | 128 | c6s.16xlarge.2 | KVM |
| C7 | 32 | 64 | c7.8xlarge.2 | 擎天 |
| C7 | 64 | 128 | c7.16xlarge.2 | 擎天 |
| C7 | 128 | 256 | c7.32xlarge.2 | 擎天 |
| C7 | 16 | 64 | c7.4xlarge.4 | 擎天 |
| C7 | 32 | 128 | c7.8xlarge.4 | 擎天 |
| C7 | 64 | 256 | c7.16xlarge.4 | 擎天 |
| C7 | 128 | 512 | c7.32xlarge.4 | 擎天 |

### 3.2 Memory-Optimized (M series — 内存优化型)

| Type | vCPU | Memory (GB) | Flavor | Virtualization |
|------|------|-------------|--------|----------------|
| M3 | 8 | 64 | m3.2xlarge.8 | KVM |
| M3 | 16 | 128 | m3.4xlarge.8 | KVM |
| M3 | 32 | 256 | m3.8xlarge.8 | KVM |
| M3 | 60 | 512 | m3.15xlarge.8 | KVM |
| M6 | 8 | 64 | m6.2xlarge.8 | KVM |
| M6 | 16 | 128 | m6.4xlarge.8 | KVM |
| M6 | 32 | 256 | m6.8xlarge.8 | KVM |
| M6 | 64 | 512 | m6.16xlarge.8 | KVM |
| M7 | 8 | 64 | m7.2xlarge.8 | 擎天 |
| M7 | 16 | 128 | m7.4xlarge.8 | 擎天 |
| M7 | 32 | 256 | m7.8xlarge.8 | 擎天 |
| M7 | 64 | 512 | m7.16xlarge.8 | 擎天 |
| M7 | 128 | 1024 | m7.32xlarge.8 | 擎天 |
| M9 | 8 | 64 | m9.2xlarge.8 | 擎天 |
| M9 | 16 | 128 | m9.4xlarge.8 | 擎天 |
| M9 | 32 | 256 | m9.8xlarge.8 | 擎天 |
| M9 | 64 | 512 | m9.16xlarge.8 | 擎天 |
| M9 | 128 | 1024 | m9.32xlarge.8 | 擎天 |

### 3.3 AMD General Computing-plus (AC series — AMD通用计算增强型)

| Type | vCPU | Memory (GB) | Flavor | Virtualization |
|------|------|-------------|--------|----------------|
| AC7 | 16 | 32 | ac7.4xlarge.2 | KVM |
| AC7 | 32 | 64 | ac7.8xlarge.2 | KVM |
| AC7 | 64 | 128 | ac7.16xlarge.2 | KVM |
| AC7 | 128 | 256 | ac7.32xlarge.2 | KVM |
| AC7 | 8 | 32 | ac7.2xlarge.4 | KVM |
| AC7 | 16 | 64 | ac7.4xlarge.4 | KVM |
| AC7 | 32 | 128 | ac7.8xlarge.4 | KVM |
| AC7 | 64 | 256 | ac7.16xlarge.4 | KVM |
| AC7 | 128 | 512 | ac7.32xlarge.4 | KVM |
| AC8 | 16 | 32 | ac8.4xlarge.2 | 擎天 |
| AC8 | 32 | 64 | ac8.8xlarge.2 | 擎天 |
| AC8 | 64 | 128 | ac8.16xlarge.2 | 擎天 |
| AC8 | 128 | 256 | ac8.32xlarge.2 | 擎天 |
| AC8 | 8 | 32 | ac8.2xlarge.4 | 擎天 |
| AC8 | 16 | 64 | ac8.4xlarge.4 | 擎天 |
| AC8 | 32 | 128 | ac8.8xlarge.4 | 擎天 |
| AC8 | 64 | 256 | ac8.16xlarge.4 | 擎天 |
| AC8 | 128 | 512 | ac8.32xlarge.4 | 擎天 |
| AC9 | 16 | 32 | ac9.4xlarge.2 | 擎天 |
| AC9 | 32 | 64 | ac9.8xlarge.2 | 擎天 |
| AC9 | 64 | 128 | ac9.16xlarge.2 | 擎天 |
| AC9 | 128 | 256 | ac9.32xlarge.2 | 擎天 |
| AC9 | 8 | 32 | ac9.2xlarge.4 | 擎天 |
| AC9 | 16 | 64 | ac9.4xlarge.4 | 擎天 |
| AC9 | 32 | 128 | ac9.8xlarge.4 | 擎天 |
| AC9 | 64 | 256 | ac9.16xlarge.4 | 擎天 |
| AC9 | 128 | 512 | ac9.32xlarge.4 | 擎天 |

### 3.4 AMD Memory-Optimized (AM series — AMD内存优化型)

| Type | vCPU | Memory (GB) | Flavor | Virtualization |
|------|------|-------------|--------|----------------|
| AM7 | 8 | 64 | am7.2xlarge.8 | KVM |
| AM7 | 16 | 128 | am7.4xlarge.8 | KVM |
| AM7 | 32 | 256 | am7.8xlarge.8 | KVM |
| AM7 | 64 | 512 | am7.16xlarge.8 | KVM |
| AM7 | 128 | 1024 | am7.32xlarge.8 | KVM |
| AM8 | 96 | 768 | am8.24xlarge.8 | 擎天 |

### 3.5 Kunpeng General Computing-plus (KC series — 鲲鹏通用计算增强型)

| Type | vCPU | Memory (GB) | Flavor | Virtualization |
|------|------|-------------|--------|----------------|
| KC1 | 16 | 64 | kc1.4xlarge.4 | KVM |
| KC1 | 32 | 64 | kc1.8xlarge.2 | KVM |
| KC1 | 32 | 128 | kc1.8xlarge.4 | KVM |
| KC1 | 60 | 120 | kc1.15xlarge.2 | KVM |
| KC2 | 16 | 32 | kc2.4xlarge.2 | 擎天 |
| KC2 | 32 | 64 | kc2.8xlarge.2 | 擎天 |
| KC2 | 64 | 128 | kc2.16xlarge.2 | 擎天 |
| KC2 | 128 | 256 | kc2.32xlarge.2 | 擎天 |
| KC2 | 8 | 32 | kc2.2xlarge.4 | 擎天 |
| KC2 | 16 | 64 | kc2.4xlarge.4 | 擎天 |
| KC2 | 32 | 128 | kc2.8xlarge.4 | 擎天 |
| KC2 | 64 | 256 | kc2.16xlarge.4 | 擎天 |
| KC2 | 128 | 512 | kc2.32xlarge.4 | 擎天 |

### 3.6 Kunpeng Memory-Optimized (KM series — 鲲鹏内存优化型)

| Type | vCPU | Memory (GB) | Flavor | Virtualization |
|------|------|-------------|--------|----------------|
| KM1 | 8 | 64 | km1.2xlarge.8 | KVM |
| KM1 | 16 | 128 | km1.4xlarge.8 | KVM |
| KM1 | 32 | 256 | km1.8xlarge.8 | KVM |
| KM1 | 60 | 480 | km1.15xlarge.8 | KVM |
| KM2 | 8 | 64 | km2.2xlarge.8 | 擎天 |
| KM2 | 16 | 128 | km2.4xlarge.8 | 擎天 |
| KM2 | 32 | 256 | km2.8xlarge.8 | 擎天 |
| KM2 | 64 | 512 | km2.16xlarge.8 | 擎天 |

### 3.7 Ultra-High I/O (I / IR series — 超高I/O型)

| Type | vCPU | Memory (GB) | Flavor | Virtualization |
|------|------|-------------|--------|----------------|
| I3 | 8 | 64 | i3.2xlarge.8 | KVM |
| I3 | 16 | 128 | i3.4xlarge.8 | KVM |
| I3 | 32 | 256 | i3.8xlarge.8 | KVM |
| I3 | 64 | 512 | i3.16xlarge.8 | KVM |
| IR3 | 16 | 64 | ir3.4xlarge.4 | KVM |
| IR3 | 32 | 128 | ir3.8xlarge.4 | KVM |

### 3.8 Kunpeng Ultra-High I/O (KI1 — 鲲鹏超高I/O型)

| Type | vCPU | Memory (GB) | Flavor | Virtualization |
|------|------|-------------|--------|----------------|
| KI1 | 16 | 64 | ki1.4xlarge.4 | KVM |
| KI1 | 32 | 128 | ki1.8xlarge.4 | KVM |
| KI1 | 64 | 228 | ki1.16xlarge.4 | KVM |

> The official page also names **General Computing (S3/S6)** in its intro but publishes no spec
> table for it; therefore no S-series flavor is recommended here.

## 4. Recommended Series for MRS Planning

### Default Series: AMD General Computing-plus **aC9 (= AC9)** — CPU-intensive workloads

**aC9** is the **default recommended** series for MRS clusters (official name: AMD通用计算增强型).
Based on Huawei Cloud's QingTian architecture with self-developed minimal virtualization.

- CPU/memory ratio: 1:2 / 1:4
- vCPU range: 8-128 (MRS-supported)

#### aC9 1:2 Series (CPU-intensive)

| Flavor | vCPU | Memory (GB) | Best For |
|--------|------|-------------|----------|
| ac9.4xlarge.2 | 16 | 32 | Small Core nodes, CPU-heavy |
| ac9.8xlarge.2 | 32 | 64 | Medium Core, Spark/Flink |
| ac9.16xlarge.2 | 64 | 128 | Large Core, high CPU |
| ac9.32xlarge.2 | 128 | 256 | XLarge Core, max compute |

#### aC9 1:4 Series (Balanced)

| Flavor | vCPU | Memory (GB) | Best For |
|--------|------|-------------|----------|
| ac9.2xlarge.4 | 8 | 32 | Smallest Core/Task; below Master 64GB hard floor |
| ac9.4xlarge.4 | 16 | 64 | Master nodes (>=64GB RAM), small Core |
| ac9.8xlarge.4 | 32 | 128 | Core nodes, balanced |
| ac9.16xlarge.4 | 64 | 256 | Large Core, memory+compute |
| ac9.32xlarge.4 | 128 | 512 | XLarge Core, high memory |

> Note: `ac9.2xlarge.4` (8C/32G) **is** an MRS-supported flavor and is the precise match when the
> estimated requirement is ~8C/32G — do not round up to 16C/64G unless the 64GB Master floor or
> the minimum-redundancy total-excess metric requires it.

**aC9 Master Node Recommended Specifications** (based on industry NameNode heap sizing standards):

Master node spec selection is **not based on Core node count alone**, but on **HDFS metadata scale (file count/block count)** and **cluster management load**.

**Industry Standard References**:
- Cloudera/CDH official: 1GB NameNode heap memory / 1M Block ([reference](https://docs.cloudera.com/documentation/enterprise/5-15-x/topics/admin_nn_memory_config.html))
- Alibaba Cloud EMR official: (file count in millions + block count in millions) x 512MB ([reference](https://help.aliyun.com/zh/emr/emr-on-ecs/user-guide/jvm-memory-tuning))
- Huawei Cloud MRS hard constraint: Master node memory >= 64GB (MRS 3.x mandatory) → minimum MRS-supported Master flavor is **ac9.4xlarge.4 (16C/64G)**

| Metadata Scale | NameNode Heap Estimate | Recommended Master Memory | Recommended Flavor |
|----------------|----------------------|--------------------------|-------------------|
| < 1M files | 2-4 GB | 64 GB | ac9.4xlarge.4 (16 vCPU) |
| 1M-10M files | 4-10 GB | 64-128 GB | ac9.4xlarge.4 / ac9.8xlarge.4 |
| 10M-50M files | 10-50 GB | 128-256 GB | ac9.8xlarge.4 / ac9.16xlarge.4 |
| > 50M files | > 50 GB | 256 GB+ | ac9.16xlarge.4 (64 vCPU) |

**OBS Storage-Compute Separation Mode Special Notes**:
- In OBS storage-compute separation mode, data is stored in OBS; HDFS stores only metadata and small files
- Block count managed by NameNode is significantly reduced (only local cache/temp files)
- Master spec can be appropriately reduced, but ResourceManager scheduling load must still be considered
- Recommend at least ac9.8xlarge.4 (32 vCPU, 128GB) to ensure YARN scheduling capability

### Alternative MRS-Supported Series

#### Previous-Gen General Computing-plus (C7/C6) — cost-optimized alternative

All C6/C7 flavors below are MRS-supported. C6 (KVM, previous generation) is a lower-cost
alternative to aC9 for cost-sensitive, non-CPU-intensive Core/Task nodes. Do not assert exact
pricing differences without a live price query.

| Flavor | vCPU | Memory (GB) | Ratio | Best For |
|--------|------|-------------|-------|----------|
| c6.4xlarge.4 | 16 | 64 | 1:4 | Master (minimum), small Core |
| c6.8xlarge.4 | 32 | 128 | 1:4 | Core, balanced |
| c6.16xlarge.4 | 64 | 256 | 1:4 | Large Core |
| c7.4xlarge.4 | 16 | 64 | 1:4 | Master (minimum), small Core |
| c7.8xlarge.4 | 32 | 128 | 1:4 | Core, balanced |
| c7.16xlarge.4 | 64 | 256 | 1:4 | Large Core |

#### Memory-Optimized (M9/M6 Series) — memory-intensive

Memory-optimized, 1:8 high memory ratio; suitable for NameNode/HMaster and other memory-intensive management roles. Prefer the newer M9 (擎天) where available.

| Flavor | vCPU | Memory (GB) | Ratio | Best For |
|--------|------|-------------|-------|----------|
| m9.2xlarge.8 / m6.2xlarge.8 | 8 | 64 | 1:8 | Small Master node |
| m9.4xlarge.8 / m6.4xlarge.8 | 16 | 128 | 1:8 | Medium Master, HBase |
| m9.8xlarge.8 / m6.8xlarge.8 | 32 | 256 | 1:8 | Large Master, HBase-intensive |
| m9.16xlarge.8 / m6.16xlarge.8 | 64 | 512 | 1:8 | XLarge Master, HBase-heavy |
| m9.32xlarge.8 | 128 | 1024 | 1:8 | XXLarge Master, HBase-heavy |

#### Ultra-High I/O (I3 Series) — storage/IO-intensive

Ultra-high IO, local SSD; suitable for Kafka/ClickHouse and other high IO throughput scenarios.

| Flavor | vCPU | Memory (GB) | Best For |
|--------|------|-------------|----------|
| i3.2xlarge.8 | 8 | 64 | Small HBase/ClickHouse |
| i3.4xlarge.8 | 16 | 128 | HBase/ClickHouse with local SSD |
| i3.8xlarge.8 | 32 | 256 | Large HBase/ClickHouse |
| i3.16xlarge.8 | 64 | 512 | XLarge HBase/ClickHouse |

## 5. Flavor Selection Matrix (Master/Core Can Use Different Flavors)

### Flavor Type Comparison

| Flavor Type | Series (MRS-supported) | Ratio Range | Characteristics | Applicable Scenarios |
|-------------|------------------------|-------------|-----------------|---------------------|
| AMD General Computing-plus | aC9/AC9 (also AC8/AC7) | 1:2, 1:4 | QingTian min. virtualization, best cost-performance | Spark/Flink/ETL, balanced load |
| General Computing-plus | C7 / C6 (also C3/C3ne/C6s) | 1:2, 1:4 | Previous-gen, KVM or QingTian | Cost-sensitive / previous-gen Core |
| Memory-Optimized | M9 / M6 (also M7/M3) | 1:8 | High memory ratio | Master/HBase/ClickHouse metadata |
| Ultra-High IO | I3 / IR3 | 1:4, 1:8 | Local SSD high throughput | Kafka/ClickHouse |

### Flavor Selection Algorithm by Node Role

```
Master node flavor selection:
  Step 1: Calculate Master total memory requirement (Step 1-4 of master-sizing-algorithm)
  Step 2: Determine flavor (from MRS-supported list; memory >= 64GB hard floor):
    IF Master_Memory <= 64GB  -> ac9.4xlarge.4 (16C/64G)
    IF Master_Memory <= 128GB -> ac9.8xlarge.4 (32C/128G)
         OR Memory-Optimized m9.4xlarge.8 / m6.4xlarge.8 (16C/128G) — HBase cluster preferred
    IF Master_Memory <= 256GB -> ac9.16xlarge.4 (64C/256G)
         OR Memory-Optimized m9.8xlarge.8 / m6.8xlarge.8 (32C/256G)
    IF Master_Memory > 256GB  -> Memory-Optimized m9.16xlarge.8 / m6.16xlarge.8 (64C/512G)
  Step 3: If metadata scale is large (>10M files), prefer Memory-Optimized to reserve sufficient margin

  Default: ac9.4xlarge.4 / ac9.8xlarge.4 (AMD General Computing-plus, optimal cost-performance)
  HBase cluster: m9/m6 1:8 (Memory-Optimized, HMaster heap memory requirement large)
  Large-scale metadata (>10M files): m9/m6 1:8 (Memory-Optimized)

Core node flavor selection:
  Constraint: All Core nodes must use the same spec (isomorphic deployment), heterogeneous not allowed!
     Mixed ratio requirements are resolved via dual-plan (Plan A/B), not by using different specs in Core.
  Step 1: Determine primary load type
  Step 2: Select flavor by load (all from MRS-supported list):
    Spark/Flink/ETL (CPU-intensive) -> AMD General Computing-plus aC9 1:2 or 1:4
    HBase (memory-intensive)         -> Memory-Optimized m9/m6 1:8
    Kafka (IO-intensive)             -> Ultra-High IO i3 1:8
    ClickHouse (IO+memory)           -> Ultra-High IO i3 1:8
    Mixed load                       -> AMD General Computing-plus aC9 1:4 (default)
    Cost-sensitive (non-CPU-intensive) -> Previous-gen General Computing-plus C6 1:4 (MRS-supported)

  Default: aC9 1:4 (AMD General Computing-plus, balanced cost-performance)
  Special: HBase-primary -> m9/m6, Kafka-primary -> i3

Task node flavor selection:
  - Default follows Core node flavor (same type, can differ in spec)
  - Cost-optimization scenario: can select Previous-gen C6 1:4 (MRS-supported, on-demand billing)
```

### Master and Core Flavor Combination Examples

| Scenario | Master Flavor | Core Flavor | Rationale |
|----------|--------------|-------------|-----------|
| Spark/ETL cluster | aC9 1:4 (ac9.8xlarge.4) | aC9 1:2/1:4 | Master management + Core compute, both enhanced |
| HBase cluster | m9/m6 1:8 (m9.4xlarge.8) | m9/m6 1:8 (m9.8xlarge.8) | HMaster/HRegionServer both need high memory |
| Kafka cluster | aC9 1:4 (ac9.4xlarge.4) | i3 1:8 (i3.4xlarge.8) | Master management + Core local SSD high IO |
| Mixed load cluster | m9/m6 1:8 (m9.4xlarge.8) | aC9 1:4 (ac9.8xlarge.4) | Master high memory + Core balanced compute |
| Cost-sensitive cluster | c6 1:4 (c6.4xlarge.4) | c6 1:4 (c6.8xlarge.4) | Previous-gen General Computing-plus, MRS-supported |
