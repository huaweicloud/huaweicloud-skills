# Single-Plan Selection Algorithm (Minimum Spec Meeting Requirements)

> This document is extracted from SKILL.md Phase 4. Starting from v2.0.0, Plan A/Plan B dual-plan comparison is no longer output;
> only one "minimum spec that meets requirements" plan is output (minimum compute surplus under constraints).
> v2.2.0: The selection model removes the independent "system disk" item (DWS Serverless is sold as a whole machine; node price already includes the system disk),
> and introduces a **near-tie tolerance (≤0.5%) → select the one with fewer nodes** anti-degradation rule.
> v2.3.0: The cache basis is extended with window (hot window of N days) / custom (custom hot data volume in GB, hybrid hot profile) —
> it only affects the "hot data volume → per-node storage" value of `calc_storage` (see storage-calculation.md); the selection structure and near-tie rule remain unchanged.

## 1. Selection Objective and Hard Constraints

All DWS compute nodes use the same flavor (single-flavor deployment). Only output **one plan**:

```
Objective: Among flavor combinations satisfying all hard constraints, select the one with "minimum compute surplus"
           (Surplus difference ≤0.5% is treated as a tie → fewer nodes → less compute surplus)

Hard constraints:
  C1 Per-node vCPU >= 16 and memory >= 64GB (production lower bound, official recommendation)
  C2 Node count >= 3 (high availability, DWS minimum 3 nodes)
  C3 Node count × per-node vCPU >= Target total vCPU (migration = competitor-equivalent core count / greenfield = data-volume-derived core count)
```

> Note: The CPU-memory ratio (1:4 / 1:8) is used to filter the same memory-ratio series in the flavor catalog;
> flavors cannot be mixed across memory ratios.

## 2. Selection Algorithm

```
Input: Target total vCPU (V), CPU-memory ratio (R in {"1:4","1:8"}),
       architecture (integrated storage-compute/disaggregated storage-compute), current inbound data volume (GB), cache strategy, point query/index %

Step 1: Pull candidate flavors
  Flavor_List = FLAVOR_CATALOG[architecture][R]
  Production filter: retain only flavors with vCPU >= 16 and memory >= 64GB (sorted by vCPU ascending)

Step 2: Traverse each candidate flavor to generate feasible combinations
  FOR flavor IN Flavor_List:
    nodes = max(3, ceil(V / flavor.vCPU))          # Satisfy C2 & C3
    storage = calc_storage(architecture, data volume, nodes, ...)  # Per-node storage (round up to 100GB)
    Record: (flavor, nodes, total vCPU, compute surplus = total vCPU - V, per-node storage)

Step 3: Select the optimal
  best_surplus = min(compute surplus)
  near = { combination | compute surplus ≤ best_surplus × 1.005 }        # v2.2.0 near-tie tolerance
  Optimal = min(near, key=(nodes, compute surplus))                     # Fewer nodes → less surplus
  Output: Single plan (flavor, node count, total vCPU/memory, per-node storage, failure impact,
           candidate combination comparison table considered for report/Excel to show decision rationale)
```

> Region coefficients and OBS usage are constants for all candidates and do not participate in cross-comparison.

## 3. Why "Minimum Spec" Does Not Equal "Minimum Per-Node Spec"

| Intuitive Misconception | Reality |
|---------|------|
| Smaller per-node is more economical? | More nodes means greater rounding loss; and more nodes means heavier O&M |
| Larger flavor with fewer nodes is more economical? | Large-flavor combinations have large compute surplus → total vCPU/memory oversizing |
| Only compare node flavor × node count? | Must include **storage rounding loss**: per-node storage = total demand ÷ node count rounded up to 100GB; node count affects rounding loss |
| After removing system disk, all combinations are about the same? | After v2.2.0 removed the independent "system disk" item, combinations often appear as **near-ties** (e.g., 50TB scenario 16-core×32 and 128-core×4 have the same surplus) — mechanically picking the "minimum" would degrade into many small nodes; therefore, for near-tie combinations ≤0.5%, select the one with **fewer nodes** (simpler O&M, equivalent benefit) |

Correct approach: Fully calculate "nodes + data disks/cache" across both items then cross-compare, applying the near-tie rule —
this is exactly Step 2/3 of this algorithm.

## 4. Worked Examples

### Example 1: Migration Scenario V=96, 1:4 (cn-north-4, 5TB, few point queries)

```
Candidates (1:4 catalog: 16-core/32-core/64-core/96-core/128-core):
  dwsx2.h.8xlarge.4.c7n   32 cores   3 nodes  96 cores (surplus 0)    per-node 2500GB   ← Optimal
  dwsx2.h.4xlarge.4.c7n   16 cores   6 nodes  96 cores (surplus 0)    per-node 1300GB   (near-tie, select fewer nodes)
  dwsx2.h.16xlarge.4.c7n  64 cores   3 nodes 192 cores (surplus 96)   per-node 2500GB
  dwsk2.h.24xlarge        96 cores   3 nodes 288 cores (surplus 192)  per-node 2500GB
  dwsk2.h.32xlarge       128 cores   3 nodes 384 cores (surplus 288)  per-node 2500GB

→ Select dwsx2.h.8xlarge.4.c7n (32 cores/128GB) × 3 = 96 vCPU / 384GB
  Per-node storage 2500GB (effective 7314GB no index ÷3 → 2438 → 2500)
```

### Example 2: Greenfield Scenario V=205 (20TB non-compute-intensive → 1:4), disaggregated storage-compute performance-priority

```
Candidates (1:4 disaggregated storage-compute catalog):
  dwsx3.16U64G.16DPU      16 cores 13 nodes 208 cores (surplus 3)   per-node 2600GB   ← Optimal
  dwsx3.32U128G.32DPU     32 cores  7 nodes 224 cores (surplus 19)  per-node 4800GB
  dwsx3.64U256G.64DPU     64 cores  4 nodes 256 cores (surplus 51)  per-node 8400GB
  dwsax3.96U384G.96DPU    96 cores  3 nodes 288 cores (surplus 83)  per-node 11100GB
  dwsax3.128U512G.128DPU 128 cores  3 nodes 384 cores (surplus 179) per-node 11100GB

→ Select dwsx3.16U64G.16DPU × 13 = 208 vCPU / 832GB
  Per-node cache 2600GB
```

### Example 3: Near-Tie Tolerance Takes Effect (50TB disaggregated storage-compute cost-priority, V=512, 1:4)

```
Candidates (1:4 disaggregated storage-compute catalog, near-tie occurs):
  dwsx3.16U64G.16DPU      16 cores 32 nodes 512 cores (surplus 0)  per-node 1300GB   (minimum surplus, but 32 nodes)
  dwsax3.128U512G.128DPU 128 cores  4 nodes 512 cores (surplus 0)  per-node 10400GB  ← Optimal (near-tie selects 4 nodes)
  dwsx3.64U256G.64DPU     64 cores  8 nodes 512 cores (surplus 0)  per-node 5200GB
  dwsx3.32U128G.32DPU     32 cores 16 nodes 512 cores (surplus 0)  per-node 2600GB

Surplus is equal → 16-core×32 has minimum surplus but is judged equivalent,
select the one with fewest nodes (4 nodes) — 128-core×4
```

> For more scenario worked examples, see [sizing-scenarios.md](sizing-scenarios.md).
