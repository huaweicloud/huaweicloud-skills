# Excel Report Template and report_data Data Structure (v2.3.0 Single Plan)

> This document defines the report_data input format and the specifications for the 5 Sheets of the DWS Excel report generation script.
> From v2.0.0: only outputs **one plan** (the minimum specification that meets requirements), no longer Plan A/Plan B dual plans;
> Added daily increment + data retention period → Sheet 4 "Capacity Growth and Expansion Recommendations".
> v2.3.0: Disaggregated cache caliber expanded to four tiers (cost50% / performance100% / **window hot window N days** / **custom user-defined hot data amount GB**) —
> `requirements` adds `cache_label`/`hot_data_days`/`hot_data_gb`; `storage_calc.cache_mode` indicates the actually effective mode;
> window/custom belong to the "fixed cache mode" (local cache does not scale with total volume, growth is absorbed elastically by OBS, see Sheet4/Sheet5).
> v2.5.0: **Selection reasoning formulized** — `plan.select_reason` is no longer a one-line pitch, but changed to multi-line text
> automatically generated according to the calculation formula logic chain (`compose_select_reason`): ①Compute derivation (data volume/migration equivalence → vCPU) → ②Memory ratio (query profile) →
> ③Concurrency·HA candidate combinations → ④Storage/cache capacity verification (high water level/index) → conclusion;
> Each step includes actual calculation numbers; the step list is stored in `plan.select_reason_steps`. Sheet1 A10 and Sheet3 "Node Specification" row
> display this multi-line reasoning (wrap_text + auto row height).

## 1. report_data Data Structure Definition

```python
report_data = {
    # ====== Basic information ======
    "project_name": "Greenplum migration to DWS project (example, with daily increment)",   # Optional, report header name
    "scenario_type": "Migration scenario",                     # Migration scenario / New-build scenario
    "architecture": "integrated compute and storage",                      # Integrated compute and storage / Disaggregated compute and storage
    "region": "Southwest-Guiyang-1",                         # Deployment region

    # ====== Requirement inputs ======
    "requirements": {
        "data_total_gb": 5120,                      # Total data volume loaded into warehouse currently/first batch (GB)
        "data_total_tb": 5,                         # Total data volume loaded into warehouse currently/first batch (TB)
        "competitor_cores": 96,                     # Migration scenario: competitor CPU cores (None for non-migration)
        "competitor_ratio": "1:8",                  # Migration scenario: competitor memory ratio (None for non-migration)
        "compute_intensive": False,                 # New-build scenario: whether compute-intensive
        "high_point_query": True,                   # Whether point queries are frequent
        "index_pct": 0.30,                          # Index space ratio 0.0-0.5
        "cache_policy": "performance",              # Disaggregated: cost(50%) / performance(100%), fill "-" for integrated
        "cache_label": "Performance priority (100% hot data)",        # [v2.3.0] Cache caliber display label (used in Sheet1/Sheet2)
        "hot_data_days": None,                      # [v2.3.0] window hot window days N (None if unused)
        "hot_data_gb": None,                        # [v2.3.0] custom user-defined hot data amount GB (mixed hot profile, None if unused)
        "daily_increment_gb": 50.0,                 # [Added] Daily increment (GB/day), None if not provided
        "retention_months": 12,                     # [Added] Data retention period (months) = planning cycle, None if not provided
    },

    # ====== CPU cores derivation (based on current/first batch warehouse volume)======
    "cpu_calculation": {
        "base_cores": 96,                           # Base cores (migration = competitor cores)
        "buffer_cores": 0,                          # Buffer cores for compute-intensive +30% (0 if none)
        "target_vcpu": 96,                          # Final target vCPU
        "target_ratio": "1:8",                      # CPU memory ratio 1:4 / 1:8
        "notes": ["Migration scenario competitor 96 cores 1:8, configured with equivalence (no hard ≥96 lower bound)"],
    },

    # ====== Single plan (minimum specification that meets requirements)======
    "plan": {
        "name": "Recommended plan (minimum specification that meets requirements)",
        "flavor": "dwsx2.4xlarge.m7",              # Instance type specification
        "vcpu": 16,                                  # vCPU per node
        "memory_gb": 128,                            # Memory per node
        "node_count": 6,                             # Number of nodes
        "total_vcpu": 96,                            # Total vCPU
        "total_memory_gb": 768,                      # Total memory
        "fault_impact": "-17% vCPU",                 # Single node fault impact
        "select_reason": "①Compute derivation (data volume): 5120GB÷100GB/core=51.2 → target total vCPU=96 cores\n②Memory ratio (compute logic): …\n… (v2.5.0: multi-line text generated by calculation formula logic chain, including actual calculation numbers)",   # Selection explanation
        "select_reason_steps": [                      # [v2.5.0] Selection reasoning step list (reusable in Sheet4/report)
            "①Compute derivation (data volume): 5120GB÷100GB/core=51.2 → target total vCPU=96 cores",
            "②Memory ratio (compute logic): … → CPU:memory=1:8",
            "③Concurrency·HA: … → feasible combinations 16 cores×6=96 cores, 32 cores×3=96 cores…",
            "④Storage verification (integrated): hot data 5120GB÷70%=7314GB÷6 nodes=1219GB → 1300GB per node",
            "→ Selected: dwsx2.4xlarge.m7×6 = 96vCPU/768GB, 1300GB storage per node×6",
        ],
        "considered": [                              # Candidate combination comparison (Sheet 3 appendix table)
            {"flavor": "dwsx2.4xlarge.m7", "vcpu": 16, "memory_gb": 128,
             "nodes": 6, "total_vcpu": 96, "total_memory_gb": 768, "surplus_vcpu": 0,
             "per_node_final_gb": 1600},
        ],
        # Storage
        "storage_per_node_gb": 1600,                 # Storage/cache per node (GB)
        "storage_per_node_tb": 1.56,                 # Storage/cache per node (TB)
        "storage_total_gb": 9600,                    # Total storage/cache (GB)
    },

    # ====== Initial storage calculation details (for Sheet 2)======
    "storage_calc": {
        "arch": "integrated compute and storage",
        "cache_mode": "performance",                 # [v2.3.0] Actual cache mode: cost/performance/window/custom
        "data_total_gb": 5120,
        "high_water_level": 0.70,                    # 0.7 or 0.8
        "cache_ratio": 1.0,                          # 1.0=100%, 0.5=50%; window/custom is the converted ratio
        "hot_data_gb": 5120,
        "hot_data_days": None,                       # [v2.3.0] Hot window days for window mode, else None
        "effective_gb": 7314,                        # After deducting high water level
        "index_pct": 0.30,
        "index_gb": 2194,
        "total_require_gb": 9509,
        "nodes": 6,
        "per_node_require_gb": 1585,
        "per_node_final_gb": 1600,                    # Rounded up to 100GB multiple
        "total_final_gb": 9600,
        "formula_notes": [...],
    },

    # ====== Growth reservation and expansion recommendations (for Sheet 4; if no daily increment provided then enabled=False)======
    "growth_calc": {
        "enabled": True,
        "daily_increment_gb": 50.0,                  # Daily increment (GB/day)
        "retention_months": 12,                      # Data retention period (months)
        "growth_gb": 18000,                          # New data during planning period = daily increment×30×retention months
        "projected_gb": 23120,                       # Total data volume at end of period
        "projected_tb": 22.58,
        "installed_total_gb": 9600,                  # Initial configuration total capacity
        "usage0_pct": 0.69,                          # Initial data occupancy rate ≈ high water level
        "expand_usage_ratio": 0.90,                  # Recommended expansion occupancy rate
        "raw_cap_gb": 6646,                          # Raw data that can be carried up to expansion line
        "headroom_gb": 1526,                         # Net growth headroom
        "expand_months": 2,                          # Estimated to reach expansion line at around month N
        "need_expand": True,                         # Whether expansion is needed within retention period
        "obs_projected_gb": 23120,                   # Disaggregated OBS end-of-period volume
        "formula_notes": [...],
    },

    # ====== OBS capacity (disaggregated compute and storage, only has values for disaggregated scenarios; this example is integrated = all zeros)======
    "obs_storage": {
        "obs_gb": 0,
        "obs_tb": 0,
        "package_tier_tb": 0,
        "formula_notes": [],                         # Empty for integrated scenarios, Sheet5 follows the "integrated" N/A branch
    },

    # ====== Selection decision reasoning (Sheet 3)======
    "decisions": [
        {"point": "Architecture mode", "candidates": "Integrated / Disaggregated", "selected": "Integrated",
         "reasoning": "Data volume <20TB, integrated architecture is simpler with higher performance (recommended tier)", "rejected": "Disaggregated (extra complexity unnecessary for small datasets)"},
        {"point": "CPU memory ratio", "candidates": "1:4 / 1:8", "selected": "1:8",
         "reasoning": "Migration scenario competitor 96 cores, memory ratio 1:8", "rejected": "1:4 (insufficient memory for non-compute-intensive)"},
        {"point": "Node specification (minimum spec)", "candidates": "16 cores/32 cores/64 cores/96 cores/128 cores (comparison across tiers)",
         "selected": "dwsx2.4xlarge.m7 (16 cores 128GB) × 6 nodes",
         # v2.5.0: reasoning = plan.select_reason (multi-line formula chain, with ①②③④ steps and conclusion)
         "reasoning": "①Compute derivation…\n②Memory ratio…\n③Concurrency·HA…\n④Storage verification…\n→ Selected…", "rejected": "Other combinations have larger compute surplus (see comparison for details)"},
        {"point": "Storage capacity (initial)", "candidates": "Direct provisioning by capacity / High water level + index space",
         "selected": "Integrated: high water level 70%, frequent point queries (+30% index)",
         "reasoning": "Effective 7314GB×1.3→9509GB→1600GB per node", "rejected": "Direct capacity provisioning (high water level + index not considered)"},
        {"point": "Data growth and expansion strategy", "candidates": "Reserve growth / On-demand expansion / Disaggregated elasticity",
         "selected": "Growth reservation assessment based on daily increment", "reasoning": "Daily increment 50GB/day×12 months→end-of-period 22.58TB, expansion needed within retention period",
         "rejected": "-"},
    ],
}
```

> All generated by `build_report_data(...)`, the Excel script only renders and does not recompute.

## 2. 5 Sheet Specifications

### Sheet 1: Configuration Recommendation Overview (Single Plan)
```
Row 1:    Title (Project | Region | Architecture)
Rows 3-4: Key parameters table (Scenario type / Warehouse data volume / Target total vCPU / CPU memory ratio / Point queries / Cache policy / Daily increment / Data retention period)
Row 6:    Section title "Recommended Configuration (minimum specification that meets requirements)"
Rows 7-8: Recommended plan detailed specification table
          Columns: Node specification / vCPU per node / Memory GB per node / Data disk (SSD) / Number of nodes / Total vCPU / Total memory GB /
              Total storage TB / Single node fault impact
Row 10:   Selection explanation (select_reason) — From v2.5.0, it is the multi-line formulized reasoning "by calculation formula logic chain",
          set wrap_text + auto row height (estimated by _est_wrap_lines), first line is "①Compute derivation…"
```

### Sheet 2: Resource and Storage Calculation
```
Section 1 (from Row 1): CPU cores derivation (based on current/first batch warehouse volume, no over-provisioning)
  Columns: Calculation item | Input value | Calculation formula/logic | Result | Remarks
  Rows: Scenario type, warehouse data volume, base cores, compute-intensive buffer, final target vCPU, target memory ratio

Section 2 (starting two empty rows down): Storage capacity calculation (initial configuration)
  Columns: Calculation item | Original value | Calculation logic | Result | Description
  Rows: Architecture mode, total warehouse data volume, hot data cache ratio, high water level, effective capacity, index space ratio,
      index space GB, total storage requirement GB, number of nodes, per-node requirement GB, per-node final GB (multiples of 100GB)
```

### Sheet 3: Selection Decision Reasoning
```
Upper half: Decision table (Columns: Decision item | Candidate plans | Final selection | Selection reasoning | Rejection reason)
  Rows: Architecture mode / CPU memory ratio / Node specification (minimum spec) / Storage capacity (initial) / Data growth and expansion strategy
  v2.5.0: "Node specification (minimum spec)" row "Selection reasoning" = plan.select_reason multi-line formula chain
  (①②③④ + conclusion, separated by \n within the row); column widths fixed A-E=18/26/34/80/34,
  row heights auto-set by content estimation (_est_wrap_lines, wrap_text on)
Appendix table (starting two empty rows down): Specification candidate combination comparison
  Columns: Node specification | vCPU per node | Number of nodes | Total vCPU | Compute surplus | Storage GB per node
  From plan.considered, the selected combination is highlighted in green — replaces the old "dual plan comparison", intuitively showing why this specification was chosen
```

### Sheet 4: Capacity Growth and Expansion Recommendations (replaces old "dual plan comparison")
```
Enable condition: daily increment AND data retention period provided (growth_calc.enabled=True)
Columns: Calculation item | Original value | Calculation logic | Result | Description
Rows: Daily increment, data retention period, new data during planning period, total data volume at end of planning period, initial configuration total capacity,
    initial data occupancy rate, recommended expansion occupancy rate (90%), raw data that can be carried to expansion line, net growth headroom,
    estimated expansion time point (around month N), whether expansion is needed within retention period
Tail: Complete recommendation text (formula_notes listed line by line with "• "), expansion-needed rows highlighted in orange

When daily increment/retention period not provided: output N/A description row (no prediction), prompt to re-evaluate expansion pace after completing the data
```

### Sheet 5: Disaggregated OBS Specification (only filled for disaggregated scenarios; integrated scenarios still create the Sheet and mark "N/A")
```
Columns: Calculation item | Original value | Calculation logic | Result | Description
Rows: Data source type, current warehouse data volume, OBS package selection, OBS storage type,
    (when including growth) OBS end-of-period capacity, local hot cache supplement
Rows for integrated: Architecture mode / OBS N/A / Data storage (local SSD) / Description (assess switching to disaggregated when >20TB or large daily increment)
```

## 3. Old and New Field Mapping (upgraded from v1.0 dual plans)

| v1.0 (deprecated) | v2.0.0+ (current) | Description |
|---------------|---------------|------|
| plan_a / plan_b | plan (single plan) | No longer dual plans |
| recommended_plan / recommendation_reason | plan.select_reason | The only recommendation is the plan itself |
| storage_calc / storage_calc_a | storage_calc | Single plan storage calculation |
| Sheet 1A dual plan comparison | Sheet 4 capacity growth and expansion recommendations | Takes over daily increment |
| Decision "dual plan final recommendation" | Decision "node specification (minimum spec)" + considered comparison appendix table | - |
| requirements (no daily increment) | requirements.daily_increment_gb / retention_months | New survey items added |
