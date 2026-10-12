# CPU Core Count Calculation Algorithm

> This document is extracted from SKILL.md Phase 3. For detailed sizing, refer to the main document.

## 1. Scenario Classification

| Scenario | CPU Core Count Calculation Method | CPU-Memory Ratio Selection |
|------|---------------|-------------|
| **Migration Scenario** | Equivalent configuration based on competitor total CPU count | Match competitor equivalently (1:4 or 1:8) |
| **Greenfield Scenario · Integrated Storage-Compute (Non-Compute-Intensive)** | Total inbound data volume / 100GB | Recommended 1:4 |
| **Greenfield Scenario · Integrated Storage-Compute (Compute-Intensive)** | (Total inbound data volume / 100GB) × 1.3 | Recommended 1:8 |
| **Greenfield Scenario · Disaggregated Storage-Compute (Non-Compute-Intensive)** | Total inbound data volume / 100GB (v2.5.1) | Recommended 1:4 |
| **Greenfield Scenario · Disaggregated Storage-Compute (Compute-Intensive)** | (Total inbound data volume / 100GB) × 1.3 (v2.5.1) | Recommended 1:8 |

> ⚠️ v2.5.1: For both disaggregated storage-compute and integrated storage-compute scenarios, CPU is calculated based on the **total inbound data volume**;
> The cache ratio only affects storage/cache capacity allocation (calc_storage), not the CPU core count.

## 2. Migration Scenario Algorithm

```
Input: Competitor total CPU core count (F_cores), competitor CPU-memory ratio (F_ratio)

Step 1: Base core count
  V_base = F_cores          # v2.1.0: Equivalent to competitor core count, no longer sets a hard ≥96 lower bound

Step 2: Memory ratio
  Ratio = F_ratio   (Directly equivalent, 1:4 or 1:8)

Step 3: Fallback and rounding explanation
  Competitor core count not provided → V_base = ceil(Total inbound data volume/100GB) (fallback derivation)
  When there is no exact tier in the catalog, the flavor selection constraint automatically rounds up:
    Per-node ≥ 16vCPU/64GB, node count ≥ 3 (high availability) → Total vCPU may be slightly higher than V_base

Output: Total vCPU (V_base), CPU-memory ratio (Ratio), remarks
```

### Migration Examples

**Example 1: Greenplum Migration**
- Competitor: 96 cores, 768GB memory → Memory ratio = 768/96 = 8GB/core → 1:8
- V_base = 96 (equivalent to competitor, no supplementation needed)
- Ratio = 1:8 (equivalent to competitor)
- Output: {Total vCPU: 96, Memory ratio: 1:8}

**Example 2: Teradata Migration (small cluster, v2.1.0 no longer supplements to 96)**
- Competitor: 64 cores, 512GB memory → Memory ratio = 512/64 = 8GB/core → 1:8
- V_base = 64 (no longer supplemented to 96; if the 1:8 catalog uses the 16-core tier → 16 cores × 4 nodes = 64 cores, exactly equivalent)
- Ratio = 1:8
- Output: {Total vCPU: 64, Memory ratio: 1:8, Remarks: "Equivalent to competitor, no core count upward adjustment"}

**Example 3: Small Core Count Migration (HA Rounding)**
- Competitor: 32 cores, 128GB memory → 1:4
- V_base = 32; 1:4 catalog 16-core tier requires ceil(32/16)=2 < 3 → node count = max(3,2)=3
- Output: {Total vCPU: 48 (16 cores × 3 nodes, rounded up due to ≥3-node high availability constraint), Memory ratio: 1:4}

## 3. Greenfield Scenario Algorithm

```
Input: Total inbound data volume (TB or GB), whether compute-intensive (compute_intensive), architecture mode (arch)

Step 0: Unit conversion (unify to GB)
  IF data volume unit is TB:
    Data_GB = data volume × 1024
  ELSE:
    Data_GB = data volume

Step 1: Base core count (v2.5.1: both disaggregated storage-compute and integrated storage-compute are calculated based on total inbound data volume)
  V_base = ceil(Data_GB / 100)
  # Cache ratio only affects storage/cache capacity allocation (calc_storage), not the CPU core count

Step 2: Compute-intensive adjustment
  IF compute_intensive == True:
    V_final = ceil(V_base × 1.3)
    Ratio = "1:8"
  ELSE:
    V_final = V_base
    Ratio = "1:4"

Step 3: Per-node production constraint validation (indirectly affects flavor screening)
  Enforced in the subsequent flavor screening stage: per-node ≥ 16vCPU | 64GB

Output: Total vCPU (V_final), CPU-memory ratio (Ratio)
```

### Greenfield Examples

**Example 1: Integrated Storage-Compute · Balanced Greenfield**
- Inbound data: 5TB = 5120GB, integrated storage-compute, non-compute-intensive
- V_base = ceil(5120/100) = ceil(51.2) = 52
- Non-compute-intensive → V_final = 52, Ratio = 1:4
- ⚠️ Constraint validation: The flavor selection stage enforces per-node ≥16vCPU/64GB, node count ≥3; the final total vCPU is rounded up during flavor selection (see [single-plan-algorithm.md](single-plan-algorithm.md))

**Example 2: Integrated Storage-Compute · Compute-Intensive Greenfield**
- Inbound data: 20TB = 20480GB, compute-intensive
- V_base = ceil(20480/100) = ceil(204.8) = 205
- Compute-intensive ×1.3 → V_final = ceil(205 × 1.3) = ceil(266.5) = 267
- Ratio = 1:8
- Flavor selection: The single-plan minimum-spec algorithm traverses the 1:8 catalog to find the combination with minimum compute surplus
  (Candidates 16 cores × 17 nodes = 272 cores or 32 cores × 9 nodes = 288 cores, etc., compared by cost; see [single-plan-algorithm.md](single-plan-algorithm.md))

**Example 3: Disaggregated Storage-Compute · Cost-Priority (v2.5.1 Update)**
- Inbound data: 10TB = 10240GB, disaggregated storage-compute, cost-priority (50%), non-compute-intensive
- V_base = ceil(10240/100) = ceil(102.4) = 103
- Non-compute-intensive → V_final = 103, Ratio = 1:4
- ⚠️ v2.5.1: CPU is calculated based on total inbound data volume; the cache ratio (50%) only affects storage/cache capacity allocation, not the CPU core count

**Example 4: Disaggregated Storage-Compute · Performance-Priority (v2.5.1 Update)**
- Inbound data: 10TB = 10240GB, disaggregated storage-compute, performance-priority (100%), non-compute-intensive
- V_base = ceil(10240/100) = ceil(102.4) = 103
- Non-compute-intensive → V_final = 103, Ratio = 1:4
- ⚠️ Performance-priority and cost-priority yield the same CPU core count; the difference is only in storage/cache capacity allocation

**Example 5: Disaggregated Storage-Compute · Cache Ratio Adjustment (v2.5.1 Update)**
- Inbound data: 10TB = 10240GB, disaggregated storage-compute, user adjusts cache ratio from 50% to 80%
- V_base = ceil(10240/100) = 103 (cache ratio adjustment does not affect CPU core count)
- ⚠️ v2.5.1: The cache ratio only affects storage/cache capacity allocation; CPU core count is calculated based on total inbound data volume and does not vary with the cache ratio

## 4. Boundary Conditions and Special Notes

| Boundary Condition | Handling |
|---------|---------|
| Migration scenario with small competitor core count (e.g., <96 cores) | v2.1.0 no longer supplements to 96: directly matches based on competitor core count equivalently; the ≥3-node/per-node ≥16-core constraint automatically rounds up (e.g., GP 32 cores → 16 cores × 3 = 48 cores) |
| Migration scenario without competitor core count provided | Fall back to `ceil(Total inbound data volume/100GB)` to derive the target core count; note in the report that providing competitor info would be more accurate |
| Greenfield scenario with extremely small data volume (<100GB) | V_base = ceil(100GB/100GB) = 1, but must indirectly guarantee ≥16 cores via node flavor (minimum 16 cores per node) |
| Greenfield scenario V_final < 96 | No mandatory core count lower bound; production high availability is ensured by the "node count ≥3" constraint (e.g., 16 cores × 3 = 48 cores is also compliant) |
| User explicitly specifies node flavor | User-specified takes precedence; CPU calculation is output as a reference value for comparison |
| Compute-intensive intermediate core count rounds up | All results after ×1.3 are unconditionally ceil-rounded up to ensure sufficient compute |
| Disaggregated storage-compute CPU calculated on total inbound data volume (v2.5.1) | CPU core count = ceil(Total inbound data volume/100GB); cache ratio only affects storage/cache capacity allocation, not CPU core count |
| Disaggregated storage-compute hot data volume is 0 (extreme case) | Storage/cache capacity is covered by HA constraint fallback; CPU is not affected by hot data volume and is calculated based on total inbound data volume |
