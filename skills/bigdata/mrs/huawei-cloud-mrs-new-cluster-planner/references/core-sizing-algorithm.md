# Core Node Sizing Algorithm (Greenfield Scenario — Minimum Redundancy + Elastic Task)

> Extracted from SKILL.md Phase 4.3. Greenfield scenario uses Phase 3 estimated resources as selection target.

## 1. Selection Target and Constraints

```
Selection target:
  V = estimated total vCPU (Phase 3 user-confirmed value)
  M = estimated total memory GB (Phase 3 user-confirmed value)

Hard constraints:
  1. All Core nodes must use the same spec (isomorphic deployment, heterogeneous not allowed)
  2. All Task nodes must use the same spec (can differ from Core)
  3. Output only 1 final plan (minimum redundancy); no dual-plan comparison

Greenfield scenario removes minimum node count limit:
  - Does not enforce "minimum 3 nodes"
  - Core node count = algorithm-calculated N value (can be 1, 2, 3...)
  - Precisely match business requirements, avoid resource waste
  - Only warn of risks: N=1 no HA single point of failure, N=2 has HA but distributed Shuffle marginal
  - OBS storage-compute separation mode: Core does not store HDFS data, N=2 is sufficient (Shuffle can distribute across 2 nodes)
  - Local HDFS mode: HDFS three-replica requires N>=3 (otherwise data has no redundancy)
```

## 2. Flavor Selection (By Load Type)

```
Load type -> flavor mapping:
  Spark/Flink/ETL (CPU-intensive)   -> General Computing-plus aC9 (1:2 or 1:4)
  HBase (memory-intensive)           -> Memory-Optimized m6 (1:8)
  Kafka (IO-intensive)               -> Ultra-High IO i3 (local SSD)
  ClickHouse/Doris (IO+memory)       -> Ultra-High IO i3
  Mixed load                         -> General Computing-plus aC9 1:4 (default)
  Cost-sensitive (non-CPU-intensive) -> Previous-gen General Computing-plus C6 1:4 (MRS-supported)

Ratio selection:
  R = M / V
  R < 3 -> prefer 1:2 ratio (CPU-optimized, e.g., ac9.16xlarge.2)
  R >= 3 -> prefer 1:4 ratio (balanced, e.g., ac9.16xlarge.4)
```

> Full flavor catalog: [ecs-flavor-catalog.md](ecs-flavor-catalog.md)

## 3. Minimum-Redundancy Selection Algorithm (Core)

```
For each candidate spec (iterate within same ratio series):
  N = max( ceil(V / flavor_vCPU), ceil(M / flavor_memory) )
  Core_vCPU = N x flavor_vCPU
  Core_Mem  = N x flavor_memory

  CPU_excess% = (Core_vCPU - V) / V x 100
  Mem_excess% = (Core_Mem  - M) / M x 100
  Total_excess = CPU_excess% + Mem_excess%

Selection rule:
  -> Select spec with minimum Total_excess
  -> When Total_excess is equal, prefer fewer nodes (reduce system disk / MRS management overhead)
```

**Example**: Estimated target V=1792 vCPU, M=5256 GB (R=2.93):
```
Candidate 1: ac9.32xlarge.4 (128C/512G, 1:4)
  N = max(ceil(1792/128), ceil(5256/512)) = max(14, 11) = 14
  CPU_excess = (1792-1792)/1792 = 0%    Mem_excess = (7168-5256)/5256 = +36.4%
  Total_excess = 36.4%

Candidate 2: ac9.32xlarge.2 (128C/256G, 1:2)
  N = max(ceil(1792/128), ceil(5256/256)) = max(14, 21) = 21
  CPU_excess = (2688-1792)/1792 = +50.0%  Mem_excess = (5376-5256)/5256 = +2.3%
  Total_excess = 52.3%

-> Select Candidate 1: ac9.32xlarge.4 x 14 (Total_excess 36.4% < 52.3%)
```

## 4. Isomorphic Validation and Node Count Evaluation

```
After selection, must validate:
  - All Core nodes use the same flavor
  - Core total vCPU >= V (satisfies estimated target)
  - Core total memory >= M (satisfies estimated target)
  - Single node failure impact = 1/N (explained in report)

Node count evaluation (greenfield scenario does not enforce minimum, but must warn of risks):
  N = 1: No HA, single point of failure loses all (only suitable for test/POC, report annotates risk)
  N = 2: Has HA but distributed Shuffle marginal (OBS mode acceptable, local HDFS data has no three-replica redundancy)
  N >= 3: Standard HA + distributed Shuffle (local HDFS mode recommends N>=3 to ensure data three-replica)
  Report must explain N value risk assessment; user must confirm acceptance
```

## 5. Elastic Task Algorithm (Optional, when load has clear peak/valley)

```
Step 1: Total = estimated resources x (1 + buffer%)
        buffer%: only take 20% when user confirms peak sustains >90%, otherwise 0%
Step 2: Core target = estimated resources x daily load% (no buffer)
        daily load%: ask user (e.g., daytime real-time 40%, overnight batch 100%)
        Multi-load off-peak scenario: Core estimated by "resident load" (real-time + query)
Step 3: Task target = Total - Core (includes all buffer)
Step 4: Core selected by minimum-redundancy algorithm (target = Core target)
Step 5: Task flavor follows Core, Task node count = ceil(Task target vCPU / Task flavor vCPU)
Step 6: Task data disk = max(1, ceil(Task_vCPU x 40 / 600)) x 600GB

Billing:
  Core: monthly/yearly (long-term resident)
  Task: on-demand billing, monthly fee = unit_price/730 x 1.2 x monthly running hours
        monthly running hours = daily running hours x 30
```

**Example**: Estimated total V=2688 vCPU (batch overnight 100% + real-time daytime 40%), daily load 40%, Task daily running 10h:
```
Core target = 2688 x 40% = 1076 vCPU
Task target = 2688 - 1076 = 1612 vCPU
Core: ac9.32xlarge.4 x 9 (1152 vCPU, monthly)
Task: ac9.32xlarge.4 x 13 (1664 vCPU, on-demand 10h/day=300h/month)
  Task monthly fee = 13 x 14895/730 x 1.2 x 300 = ¥95,925
  vs all-Core monthly (21 nodes x 14895 = ¥312,795) significant savings
```

## 6. Core Node Count and Master Linkage

```
After Core selection, pass back to Master sizing:
  Core node count N -> Master vCPU baseline (<=20 -> 16 cores, 20-50 -> 32 cores, >50 -> 64 cores)
  Core total cores = N x Core_vCPU -> Master node count (<100 -> 3 nodes, >=100 -> 5 nodes)
  Estimated YARN total resources -> ResourceManager heap (>=100 vCPU takes 8GB)
```
