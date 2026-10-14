# Command Contract (RFQ Price Inquiry)

Each op has a **contract** + **CLI template**; facts/dimensions live in `semantic/*.yml`. Arrays use dot notation (`--product_infos.1.*`); output with `--cli-output=json`; dictionary pagination defaults to `--limit=10 --offset=0`, ≤3 pages per command.

## Universal Traps (review on every price inquiry)

1. **Arrays use dot notation only** — KooCLI does not recognize JSON strings / `[...]`.
2. **The price inquiry API has no pagination** — put multiple items into `product_infos.N.*` in one call.
3. **Codes are case-sensitive** — for type / region / spec use the exact text the dimension lookup returned; never lowercase, never concatenate.
4. **Resolve chain** — `ListServiceResources` → `ListResourceSpecs` → on-demand `ListUsageTypes(--resource_type_code)` → `ListMeasureUnits` + Measure Resolve → price inquiry. Ask when there are multiple candidates; a row in Specs ≠ priceable; must not default to Duration/hours.
5. **Measure Resolve** — UsageTypes has no measure (cross-check `ListMeasureUnits`). A usage slot ≠ a capacity slot
   (capacity slots exist only in the linear table). Same name GB: usage `type=3→10`, capacity slot `17`/`15`. The factor determines the family:
   `Duration`→`4`/hour; `size*|capacity|stock`→`10`/**GB×hour** (do not use `resource_size`; types 7/72/87 are forbidden);
   `*flow|retrieval*`→`10`/GB; `get|put|request*`→`14`/request.
   `CBC.6006`/`CBC.6050`: retry once with a changed type/factor or a sibling with the same abbreviation; exhaustive enumeration is forbidden.
6. **Parameter errors** — `CBC.0100`: check against runtime help and the parameter combination; `CBC.99006006`: go back to the spec,
   region, and billing mode to confirm; `CBC.99006055`: narrow the inquiry batch or period. Permission errors (403/`CBC.0151`/429):
   see `../iam-policies.md`.

---

## rfq_quote_execution

### `BSS/ListRateOnPeriodDetail` — yearly/monthly price inquiry

> **method**: POST · **safety**: readonly · **entities**: `RFQ_Header`, `RFQ_Line` · **pagination**: n/a · **doc**: [bcloud_01002](https://support.huaweicloud.com/api-bpconsole/bcloud_01002.html)
> **required**: `project_id` + per-line `id` / `cloud_service_type` / `resource_type` / `resource_spec` / `region` / `period_type` / `period_num` / `subscription_num`
> **conditional**: `linear_product` → `resource_size` + `size_measure_id`

```bash
hcloud BSS ListRateOnPeriodDetail \
  --project_id=<project_id> \
  --product_infos.1.id=1 \
  --product_infos.1.cloud_service_type=hws.service.type.ec2 \
  --product_infos.1.resource_type=hws.resource.type.vm \
  --product_infos.1.resource_spec=c6.2xlarge.2.linux \
  --product_infos.1.region=cn-north-1 \
  --product_infos.1.period_type=2 --product_infos.1.period_num=1 --product_infos.1.subscription_num=1 \
  --product_infos.2.id=2 \
  --product_infos.2.cloud_service_type=hws.service.type.ebs \
  --product_infos.2.resource_type=hws.resource.type.volume \
  --product_infos.2.resource_spec=GPSSD \
  --product_infos.2.region=cn-north-1 \
  --product_infos.2.resource_size=40 --product_infos.2.size_measure_id=17 \
  --product_infos.2.period_type=2 --product_infos.2.period_num=1 --product_infos.2.subscription_num=1 \
  --cli-region=cn-north-1 --cli-output=json
```

| Field | Type | Value | Notes |
| --- | --- | --- | --- |
| `period_type` / `period_num` | int | 0 day / 2 month / 3 year / 4 hour | yearly/monthly is usually 2 or 3 |
| `subscription_num` | int | 1..10000 | inquiry quantity |
| `size_measure_id` | int | only the three linear types | see the capacity slot table |
| `fee_installment_mode` | string | HALF_PAY / ZERO_PAY / NA | CloudPond only for now |

### `BSS/ListOnDemandResourceRatings` — on-demand price inquiry

> **method**: POST · **safety**: readonly · **entities**: `RFQ_OnDemand_Header`, `RFQ_OnDemand_Line` · **pagination**: n/a · **doc**: [bcloud_01001](https://support.huaweicloud.com/api-bpconsole/bcloud_01001.html)
> **required**: `project_id` + per-line `id` / `cloud_service_type` / `resource_type` / `resource_spec` / `region` / `usage_factor` / `usage_value` / `usage_measure_id` / `subscription_num`
> **conditional**: `linear_product` → `resource_size` + `size_measure_id`
> **optional**: `inquiry_precision` (0 = default 6 digits / 1 = full 10 digits)

Mixed on-demand (ECS + EVS + bandwidth billed by traffic):

```bash
hcloud BSS ListOnDemandResourceRatings \
  --project_id=<project_id> \
  --product_infos.1.id=1 \
  --product_infos.1.cloud_service_type=hws.service.type.ec2 \
  --product_infos.1.resource_type=hws.resource.type.vm \
  --product_infos.1.resource_spec=c3.3xlarge.2.linux \
  --product_infos.1.region=cn-north-1 \
  --product_infos.1.usage_factor=Duration --product_infos.1.usage_value=2 --product_infos.1.usage_measure_id=4 \
  --product_infos.1.subscription_num=1 \
  --product_infos.2.id=2 \
  --product_infos.2.cloud_service_type=hws.service.type.ebs \
  --product_infos.2.resource_type=hws.resource.type.volume \
  --product_infos.2.resource_spec=SSD \
  --product_infos.2.region=cn-north-1 \
  --product_infos.2.resource_size=10 --product_infos.2.size_measure_id=17 \
  --product_infos.2.usage_factor=Duration --product_infos.2.usage_value=2 --product_infos.2.usage_measure_id=4 \
  --product_infos.2.subscription_num=1 \
  --product_infos.3.id=3 \
  --product_infos.3.cloud_service_type=hws.service.type.vpc \
  --product_infos.3.resource_type=hws.resource.type.bandwidth \
  --product_infos.3.resource_spec=12_sbgp \
  --product_infos.3.region=cn-north-1 \
  --product_infos.3.resource_size=1 --product_infos.3.size_measure_id=15 \
  --product_infos.3.usage_factor=upflow --product_infos.3.usage_value=4 --product_infos.3.usage_measure_id=10 \
  --product_infos.3.subscription_num=1 \
  --cli-region=cn-north-1 --cli-output=json
```

| Field | Type | Value | Notes |
| --- | --- | --- | --- |
| `usage_factor` | string | `ListUsageTypes.code` from the current call | must not default to Duration |
| `usage_value` | number | encoded per Trap #5 | capacity family = GB×hour; duration = hours; traffic = GB |
| `usage_measure_id` | int | Trap #5 + `ListMeasureUnits` | usage slot; ≠ `size_measure_id` |
| `inquiry_precision` | int | 0 / 1 | default 6 digits / full 10 digits |

---

## response_contract (how to read a quote)

Read only the current response; **never invent discounts**. `measure_id=1`=CNY; `currency=CNY` (empty=CNY); `id` maps back to the request line. Official website price by default; attach the discounted price only when a discount exists. The line items sum to the total; for on-demand the `usage_value` is already included — do not multiply again.

| API | Official website price | Discounted price (report if present) |
| --- | --- | --- |
| `ListRateOnPeriodDetail` | `official_website_rating_result.official_website_amount` (line items in the same object) | `optional_discount_rating_results[]` where `best_offer==1` |
| `ListOnDemandResourceRatings` | root-level / `official_website_amount` in `product_rating_results[]` | read `amount` when `discount_amount>0` |

---

## dimension_lookup

| Operation | Purpose | Required | Pagination |
| --- | --- | --- | --- |
| `BSS/ListServiceTypes` | `cloud_service_type` | - | limit/offset |
| `BSS/ListServiceResources` | →`resource_type` | `service_type_code` | limit/offset |
| `BSS/ListUsageTypes` | →`usage_factor` | **`resource_type_code`** | limit/offset |
| `BSS/ListMeasureUnits` | Measure Resolve (once per session) | - | none |
| `BSS/ListResourceTypes` | translate resource_type | - | limit/offset |
| `BSS/ListConversions` | measure conversion base | - | none |

```bash
hcloud BSS ListServiceResources --service_type_code=hws.service.type.ec2 \
  --cli-region=cn-north-1 --cli-output=json --limit=10 --offset=0
hcloud BSS ListUsageTypes --resource_type_code=hws.resource.type.vm \
  --cli-region=cn-north-1 --cli-output=json --limit=100 --offset=0
hcloud BSS ListMeasureUnits --cli-region=cn-north-1 --cli-output=json
```

---

## resource_spec_lookup

### `BSS/ListResourceSpecs` — the only path for spec resolution

> **method**: POST · **safety**: readonly · **entities**: `Dim_ResourceSpec` · **pagination**: marker/limit · **doc**: [qct_00008](https://support.huaweicloud.com/api-oce/qct_00008.html)
> **required**: `cloud_service_type` / `resource_type` / `region_code` / `charge_mode` (1 = yearly/monthly / 3 = pay-per-use)
> **optional**: `filters.[N].key=RESOURCE_SPEC` + `filters.[N].value`, `marker` + `limit`

- Use `marker`+`limit` together; omit `marker` on the first page; page with `page_info.next_marker`.
- `charge_mode`/`region_code` must match the price inquiry line; never append an OS suffix to a returned value.
- Always pass `filters` when you have a spec hint; `limit=100`; if it has not converged after 3 pages, stop and let the user choose; on 429 wait 2s and retry once.
- Take candidates from `cloud_service_basics[].resource_spec`; when echoing back to the user use `resource_spec_name`.

```bash
hcloud BSS ListResourceSpecs --charge_mode=1 \
  --cloud_service_type=hws.service.type.ec2 --resource_type=hws.resource.type.vm \
  --region_code=cn-north-4 \
  --filters.1.key=RESOURCE_SPEC --filters.1.value=c6.2xlarge \
  --limit=100 --cli-region=cn-north-1 --cli-output=json
```

### Linear product capacity slots (only these three types accept `resource_size`+`size_measure_id`)

| `resource_type` | `size_measure_id` | Unit |
| --- | --- | --- |
| `hws.resource.type.volume` | 17 | GB |
| `hws.resource.type.bandwidth` | 15 | Mbps |
| `hws.resource.type.share_bandwidth` | 15 | Mbps |

## scope_resolve

```bash
hcloud IAM KeystoneListAuthProjects --cli-region=cn-north-1 --cli-output=json
hcloud IAM KeystoneListProjects --domain_id=<domain_id> --cli-region=cn-north-1 --cli-output=json
```

Partner acting for a customer: after exchanging the customer token, resolve the `project_id` for the target region; see `../iam-policies.md`.
