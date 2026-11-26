# Pricing commands and fields

Read `../gotchas.md` G01–G06 before calling these APIs. Use `--cli-output=json` and current operation help. This file owns command fields; `rfq-models/rfq-core.yml` owns their relationships. CLI arrays use `product_infos.1.*`; an API error naming `productInfos` does not change CLI spelling.

## Resolve resource types and specifications

1. Resolve an unknown service code with `ListServiceTypes`; find its resource types with `ListServiceResources(--service_type_code)`.
2. Query `ListResourceSpecs` for the selected region and mode. Retain the candidate's service/type/region/mode/spec and pagination marker.
3. For pay-per-use, query `ListUsageTypes(--resource_type_code)` and `ListMeasureUnits`, then establish the product binding required by G03–G04.

### BSS/ListResourceSpecs

[API](https://support.huaweicloud.com/api-oce/qct_00008.md). Required: `cloud_service_type`, `resource_type`, `region_code`, `charge_mode` (`1` prepaid, `3` pay-per-use).

```bash
hcloud BSS ListResourceSpecs --charge_mode=<1-or-3> \
  --cloud_service_type=<service> --resource_type=<type> \
  --region_code=<deployment-region> \
  --filters.1.key=RESOURCE_SPEC --filters.1.value=<hint> \
  --limit=100 --cli-region=cn-north-1 --cli-output=json
```

Use the hint filter when available. First page omits `marker`; subsequent pages use `page_info.next_marker` with unchanged conditions and `limit`. Inspect at most three pages, then narrow remaining candidates or ask the user to choose.

Dictionary APIs `ListServiceTypes`, `ListServiceResources`, `ListResourceTypes`, `ListUsageTypes` use `limit/offset`: start at 10 rows, increase as needed, inspect at most three pages per query. `ListMeasureUnits`/`ListConversions` do not paginate; reuse their results in the session.

## Yearly/monthly pricing

### BSS/ListRateOnPeriodDetail

[API](https://support.huaweicloud.com/api-bpconsole/bcloud_01002.md). Request: `project_id`. Each line requires unique `id`, `cloud_service_type`, `resource_type`, `resource_spec`, `region`, `period_type`, `period_num`, `subscription_num`.

- `period_type`: `2` month, `3` year; `0` day and `4` hour only for supporting products. `period_num` counts periods.
- Include selected `available_zone`. `fee_installment_mode` defaults to `NA`; `HALF_PAY/ZERO_PAY` apply only to CloudPond.
- Add capacity fields when the product requires them, as below. Pricing calls do not paginate.

```bash
hcloud BSS ListRateOnPeriodDetail --project_id=<project> \
  --product_infos.1.id=1 \
  --product_infos.1.cloud_service_type=<service> \
  --product_infos.1.resource_type=<type> \
  --product_infos.1.resource_spec=<verified-code> \
  --product_infos.1.region=<deployment-region> \
  --product_infos.1.period_type=<2-or-3> --product_infos.1.period_num=<count> \
  --product_infos.1.subscription_num=<quantity> \
  --cli-region=cn-north-1 --cli-output=json
```

## Pay-per-use pricing

### BSS/ListOnDemandResourceRatings

[API](https://support.huaweicloud.com/api-bpconsole/bcloud_01001.md). Request: `project_id`. Reuse the period template's common fields; replace period/installment fields with `usage_factor`, `usage_value`, `usage_measure_id`. Pricing calls do not paginate.

- `usage_factor` comes from `ListUsageTypes.code` for the resource. Express `usage_value` in the resolved usage unit. `inquiry_precision=0` returns six decimal places; `1` returns ten.
- Known examples: Duration/hour uses unit `4`; traffic/GB commonly uses `10`; request counts commonly use `14`. Apply only after establishing the current product's binding.

## Pricing parameter constraints

These apply to the two pricing APIs. Snapshot: official request definitions and KooCLI 7.2.12 help, 2026-10-27; recheck changes through current help/API docs.

| Field | Type / bound |
| --- | --- |
| `product_infos` | array, at most 100 lines; unique line IDs |
| `project_id`, line `id`, `region`, `available_zone` | string, max 64 |
| `cloud_service_type`, `resource_type`, `resource_spec` | string, max 400 for pricing inputs |
| `subscription_num` | integer, 1–10000 |
| `resource_size` | integer, 1–214783647; linear products also require `size_measure_id`; omitted/null does not filter nonlinear products |
| `size_measure_id` | integer, product-specific capacity unit |
| `period_type`, `period_num` | integer; type values above; count 1–214783647 |
| `fee_installment_mode` | string, max 64 |
| `usage_factor` | string, max 64, case-insensitive |
| `usage_value` | decimal number, not necessarily integer |
| `usage_measure_id`, `inquiry_precision` | integer |

`available_zone` is case-insensitive; omitted/empty/null means no filter. Omitted/empty/null installment mode means `NA`. The pay-per-use API states max length 4 for capacity/usage unit IDs; this is not a numeric range.

## Capacity and units

`resource_size` is per-item purchased capacity/scale, paired with `size_measure_id` when required. Keep usage separately.

| Product / scope | Verified binding |
| --- | --- |
| Cloud disks: `hws.resource.type.volume` | capacity in GB, `size_measure_id=17` |
| Bandwidth: `hws.resource.type.bandwidth`, `hws.resource.type.share_bandwidth` | Mbps, `size_measure_id=15` |
| OBS: `hws.service.type.obs` / `hws.resource.type.obs`, `obs.size.ltcp.clr.standard.1az`, `cn-north-4`, pay-per-use | factor `size`, `usage_value=GB × hours`, `usage_measure_id=10`; verified with KooCLI 7.2.12 on 2026-10-27 |

For other products/specifications, obtain the applicable mapping. Incomplete mappings follow G03.

## Read prices and handle exceptions

- Period list amount: `official_website_rating_result.official_website_amount`; lines: `product_rating_results[]`. Optional discounts: `optional_discount_rating_results[]`, best result: `best_offer==1`.
- Pay-per-use: root/line `official_website_amount`; when `discount_amount>0`, show corresponding `amount` with its meaning.
- `measure_id=1` means yuan. `currency=CNY`, or empty under the API's documented convention, means CNY. Match lines by request `id`, sum full-precision amounts, then round for display.
- Error handling: G01; quote-delivery limits: G06. Permission and partner scope: `../iam-policies.md`.
