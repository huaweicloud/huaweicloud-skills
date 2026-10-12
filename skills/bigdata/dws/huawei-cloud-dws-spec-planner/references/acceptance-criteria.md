# Acceptance Criteria

## Plan Output

- Output only one minimum specification plan that meets the requirements; do not output a Plan A/B dual-plan comparison.
- The plan includes architecture mode, node flavor, node count, per-node storage/cache capacity, and selection rationale.
- The selection rationale is presented via a four-step formula chain: compute derivation, memory ratio, concurrency and high availability, storage validation.

## Calculation Basis

- For migration scenarios, configure equivalently based on the total competitor CPU count; if competitor core count is not provided, fall back to `ceil(DataVolume/100GB)`.
- For greenfield scenarios, the base core count is `ceil(TotalInboundDataVolume/100GB)`; for compute-intensive cases, multiply by 1.3.
- Integrated storage-compute high-water mark is 70%; disaggregated storage-compute high-water mark is 80%.
- For disaggregated storage-compute, the cache basis priority is custom > window > cost/performance.
- Daily incremental data volume and retention period are used only for scale-out pacing and do not change the recommended node flavor.

## Report Acceptance

- Generate a structured Markdown report.
- Generate `DWS_Sizing_Report_<YYYYMMDD>.xlsx` containing 5 sheets.
- When daily incremental and retention period are not both provided, Sheet 4 outputs an N/A explanation.
- All default values and assumptions must be annotated in the report.
