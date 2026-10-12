# Storage Capacity Calculation Rules

> This document is extracted from SKILL.md Phase 5.1-5.2.

## 1. Comparison of Two Architecture Modes

| Item | Storage-compute integrated | Storage-compute separated |
|----|---------|---------|
| Full data storage location | Local EVS SSD cloud disk | OBS object storage |
| Local disk usage | Full data hot storage | Hot data cache |
| High watermark | 70% | 80% |
| Cache strategy | N/A (full) | Cost-priority 50% / Performance-priority 100% / **Hot window N days** / **Custom hot data volume (v2.3.0)** |
| Replica space reservation | Not required (configured size = usable capacity) | Not required (configured size = usable capacity) |
| Local storage | DWS disk (SSD cloud disk) | Local disk capacity included in DWS node spec; supplemental DWS disk added when exceeded |

## 2. Storage-compute Integrated Storage Capacity Calculation

**Applicable to:** Storage-compute integrated architecture, SSD cloud disk carries full data.

```
Inputs:
  Data_Total_GB: Total data volume loaded into warehouse (GB)
  V_Total: Total vCPU cores
  Flavor_vCPU: Per-node vCPU spec
  High_Point_Query: Whether point queries are frequent (True/False)
  Index_Pct: Extra index space ratio (default 30%=0.3, options 30-50%)

Step 1: Node count
  Nodes = ceil(V_Total / Flavor_vCPU)

Step 2: Effective total storage (deduct high watermark)
  Effective_Total = Data_Total_GB / 0.7    (high watermark 70%)

Step 3: Add index space
  IF High_Point_Query:
    Storage_Total = Effective_Total × (1 + Index_Pct)
  ELSE:
    Storage_Total = Effective_Total

Step 4: Per-node storage capacity (round up to nearest 100GB multiple)
  Per_Node_GB = round_up_to_100(Storage_Total / Nodes)
  Per_Node_TB = Per_Node_GB / 1024

Output: Per_Node_GB, Per_Node_TB, Storage_Total, Nodes
```

### Storage-compute Integrated Example

**Example 1: User-provided example — 3 nodes 32 cores, 5000GB, frequent point queries**
```
Data_Total_GB = 5000
Nodes = 3 (given)
Effective_Total = 5000 / 0.7 = 7142.86 GB
High_Point_Query = YES → Index_Pct = 0.3
Storage_Total = 7142.86 × 1.3 = 9285.71 GB
Per_Node_GB = ceil(9285.71 / 3) = ceil(3095.24) = 3095 ≈ 3000 GB (document example value)
→ Per-node storage = 3000 GB  ✓
```

**Example 2: 5000GB, 3 nodes 32 cores, few point queries**
```
Effective_Total = 5000 / 0.7 = 7142.86 GB
High_Point_Query = NO → Storage_Total = 7142.86 GB
Per_Node_GB = ceil(7142.86 / 3) = ceil(2380.95) = 2381 ≈ 2400 GB (round up to 100GB)
```

## 3. Storage-compute Separated Cache Capacity Calculation

**Applicable to:** Storage-compute separated architecture, local disk carries hot data cache (full data in OBS).

```
Inputs:
  Data_Total_GB: Total data volume loaded into warehouse (GB)
  V_Total: Total vCPU cores
  Flavor_vCPU: Per-node vCPU spec
  Cache_Mode: "cost" (cost-priority 50%) / "performance" (performance-priority 100%)
              / window (hot window N days) / custom (custom hot data volume GB)   # v2.3.0 added the latter two
  Hot_Days: Hot window days N (window mode)
  Daily_GB: Daily increment GB/day (window mode: Hot_Data = min(daily increment × N days, full volume))
  Hot_Data_GB_Override: Custom total hot data volume GB (custom mode: mixed multi-source hot profile calculated and passed in)
  High_Point_Query: Whether point queries are frequent (True/False)
  Index_Pct: Extra index space ratio (default 30%=0.3, options 30-50%)

Step 1: Node count
  Nodes = ceil(V_Total / Flavor_vCPU)

Step 2: Total hot data volume (by cache metric, priority custom > window > cost/performance)
  IF Cache_Mode == "custom":          # v2.3.0 mixed hot profile (e.g., 70G/day source hot 7 days + business stock 50% commonly used)
    Hot_Data = min(Hot_Data_GB_Override, Data_Total_GB)
  ELIF Cache_Mode == "window":        # v2.3.0 hot window: only cache recent N days of incremental hot data
    Hot_Data = min(Daily_GB × Hot_Days, Data_Total_GB)
  ELIF Cache_Mode == "performance":
    Hot_Data = Data_Total_GB × 1.0
  ELSE:   # cost
    Hot_Data = Data_Total_GB × 0.5

Step 3: Effective cache storage (deduct high watermark 80%)
  Effective_Cache = Hot_Data / 0.8

Step 4: Add index space
  IF High_Point_Query:
    Cache_Total = Effective_Cache × (1 + Index_Pct)
  ELSE:
    Cache_Total = Effective_Cache

Step 5: Per-node cache capacity (round up to nearest 100GB multiple)
  Per_Node_Cache_GB = round_up_to_100(Cache_Total / Nodes)
  Per_Node_Cache_TB = Per_Node_Cache_GB / 1024

Output: Per_Node_Cache_GB, Per_Node_Cache_TB, Cache_Total, Nodes, Hot_Data, Cache_Mode
```

> 📌 v2.3.0 cache metric selection rules (engine calc_storage):
> 1. User provided **custom total hot data volume** (mixed multi-source hot profile) → `custom`, Hot_Data directly takes this value (≤ full volume);
> 2. Otherwise, provided **hot window days + daily increment** (e.g., "commonly used hot data is last 7 days") → `window`, Hot_Data = min(daily increment × N, full volume);
> 3. Otherwise, use cache strategy cost (50%) / performance (100%) (default performance).
> window/custom are "fixed cache modes": local disk only carries hot data, does not scale with full volume growth; growth is elastically absorbed by OBS (see SKILL.md 5.3 / excel Sheet5).

### Storage-compute Separated Example

**Example 1: User-provided example — 3 nodes 32 cores, 5000GB, full cache (performance-priority), frequent point queries**
```
Data_Total_GB = 5000
Nodes = 3 (given)
Cache_Policy = "performance" → Hot_Data = 5000 × 100% = 5000 GB
Effective_Cache = 5000 / 0.8 = 6250 GB
High_Point_Query = YES → Index_Pct = 0.3
Cache_Total = 6250 × 1.3 = 8125 GB
Per_Node_Cache_GB = ceil(8125 / 3) = ceil(2708.33) = 2708 ≈ 2700 GB (document example value)
→ Per-node cache = 2700 GB  ✓
```

**Example 2: Cost-priority, 5000GB, 3 nodes, frequent point queries**
```
Cache_Policy = "cost" → Hot_Data = 5000 × 50% = 2500 GB
Effective_Cache = 2500 / 0.8 = 3125 GB
Cache_Total = 3125 × 1.3 = 4062.5 GB
Per_Node_Cache_GB = ceil(4062.5 / 3) = ceil(1354.17) = 1355 ≈ 1400 GB
```

**Example 3: Performance-priority, 5000GB, 3 nodes, few point queries**
```
Cache_Policy = "performance" → Hot_Data = 5000 GB
Effective_Cache = 5000 / 0.8 = 6250 GB
High_Point_Query = NO → Cache_Total = 6250 GB
Per_Node_Cache_GB = ceil(6250 / 3) = ceil(2083.33) = 2084 ≈ 2100 GB
```

## 4. Index Space Usage Guide

| Business characteristics | Index_Pct recommended value | Description |
|---------|-----------------|------|
| Typical reporting analytical, wide-table scan oriented | 0% (none added) | Indexes rarely used, mainly relies on columnar compression |
| General mixed queries, with dimension filtering | +30% (default) | Moderate secondary indexes and bitmap indexes |
| High-concurrency point queries, multiple secondary indexes | +50% | Large volume of unique key queries, secondary index lookup |

> ⚠️ When the user does not explicitly specify, default to +30% processing; mark in report: "Index space estimated at default +30%; can be adjusted to +50% for high-concurrency point query workloads."

## 5. Round Up to Nearest 100GB Multiple

```python
def round_up_to_100(gb):
    """e.g., 3095 → 3100; 3000 → 3000; 2708 → 2800"""
    import math
    return math.ceil(gb / 100) * 100
```

## 6. OBS Full Data Volume (Storage-compute Separated Scenario)

In storage-compute separated architecture, full data is stored in OBS; capacity = total data volume loaded into warehouse.

```
OBS_Storage_GB = Data_Total_GB
OBS_Storage_TB = Data_Total_GB / 1024
Round up to nearest package: 50TB / 100TB / 200TB / 500TB / 1024TB / 5120TB
```
