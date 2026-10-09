# Acceptance Criteria

Read-only pre-purchase price estimation on Huawei Cloud via hcloud ≥7.2.2 + BSS read-only IAM.

## Functional

| # | Criterion | Pass condition |
| --- | --- | --- |
| AC-1 | Resolve project scope | `KeystoneListAuthProjects` returns the `cn-north-1` (or target deploy region) project_id |
| AC-2 | Resolve service type | `ListServiceTypes` returns a case-exact `cloud_service_type` |
| AC-3 | Resolve resource type | `ListServiceResources(--service_type_code)` returns a matching `resource_type` |
| AC-4 | Resolve resource spec | `ListResourceSpecs` (charge_mode + region_code + filters) returns the spec with OS suffix included |
| AC-5 | Resolve usage type (on-demand only) | `ListUsageTypes(--resource_type_code)` returns `usage_factor` — never default Duration |
| AC-6 | Measure resolve | `ListMeasureUnits` + Measure Resolve picks the correct usage slot (4 hour / 10 GB×h / 14 count) |
| AC-7 | Period quote | `ListRateOnPeriodDetail` returns `official_website_amount` per line + total, `currency=CNY` |
| AC-8 | On-demand quote | `ListOnDemandResourceRatings` returns `official_website_amount`, optional discounted `amount` |
| AC-9 | Linear products | volume/bandwidth/share_bandwidth quote only with `resource_size` + `size_measure_id` (17/15) |
| AC-10 | Present | line-item sum = total; format `[service] [spec] [region] [qty×period] = ¥amount`; label 非最终账单 |
| AC-11 | Error handling | CBC.0100 / CBC.99006006 / CBC.99006055 / 403/CBC.0151 / 429 handled per SKILL.md |

## Non-functional / constraints

| # | Criterion | Pass condition |
| --- | --- | --- |
| NC-1 | Read-only only | No Create/Delete/Update command in any flow path |
| NC-2 | BSS region fixed | All `hcloud BSS` commands use `--cli-region=cn-north-1`; deploy region only in `product_infos.N.region` |
| NC-3 | No fabricated prices | Prices only from the current hcloud response; no memory/analogy/defaults |
| NC-4 | No fabricated params | Params extracted from runtime `--help` |
| NC-5 | No credentials in chat | AK/SK/token refused; relay install guide only |
| NC-6 | Route out-of-scope safely | History bills/balance/reconciliation/purchase/unsubscribe declined and pointed to the correct service |
| NC-7 | Case-sensitive codes | Codes taken verbatim from dimension query output |
| NC-8 | Multi-line in one request | Up to 100 lines via `product_infos.N.*`; no pagination on pricing APIs |

## Verification evidence

- Dimension resolution chain returns non-empty results.
- Period and on-demand quote both return a CNY price on at least one real quotable spec.
- A deliberately invalid spec reproduces `CBC.99006006` and the skill routes back to
  spec/region/mode confirmation instead of fabricating a price.