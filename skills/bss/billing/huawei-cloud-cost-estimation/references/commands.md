# Command Contracts (RFQ pricing)

Every op: **contract** + **CLI template**. Facts/dimensions live in `semantic/*.yml`. Arrays use
dot notation (`--product_infos.1.*`); output `--cli-output=json`; dict pagination defaults
`--limit=10 --offset=0`, per command ≤3 pages. All `hcloud BSS` commands use
`--cli-region=cn-north-1`.

## Universal Traps (read every time before quoting)

1. **Arrays are dot-notation only** — JSON strings / `[...]` are not accepted by KooCLI.
2. **Pricing APIs have no pagination** — submit multiple lines at once inside `product_infos.N.*`.
3. **Codes are case-sensitive** — use the raw values returned by dimension queries; never lower-case, never concatenate.
4. **Resolution chain** — `ListServiceResources` → `ListResourceSpecs` → (on-demand)
   `ListUsageTypes(--resource_type_code)` → `ListMeasureUnits` + Measure Resolve → quote.
   Multi-candidate → ask. Specs having rows ≠ quotable. Never default Duration/hours.
5. **Measure Resolve** — UsageTypes have no measure (align with `ListMeasureUnits`). Usage slot ≠ size slot
   (size slot only for linear products). Same-name GB: usage `type=3→10`, size `17`/`15`. Factor family:
   - `Duration` → `4`/hour
   - `size*|容量|存量` → `10`/**GB×hour** (do NOT use `resource_size`, forbid type7/72/87)
   - `*flow|retrieval*` → `10`/GB
   - `get|put|request*` → `14`/count
   - `CBC.6006`/`CBC.6050`: change type/factor or same-abbreviation sibling **once**; no exhaustive enumeration
6. **Param-class errors** — `CBC.0100` verify runtime `--help` vs parameter combination; `CBC.99006006` back to
   spec/region/mode confirm; `CBC.99006055` shrink batch or period. Permission-class
   (`403`/`CBC.0151`/`429`) see `../iam-policies.md`.

---

## rfq_quote_execution

### `BSS/ListRateOnPeriodDetail` — period quote

> **method**: POST · **safety**: readonly · **entities**: `RFQ_Header`, `RFQ_Line` · **pagination**: n/a · **doc**: [bcloud_01002](https://support.huaweicloud.com/api-bpconsole/bcloud_01002.html)
> **required**: `project_id` + per line `id` / `cloud_service_type` / `resource_type` / `resource_spec` / `region` / `period_type` / `period_num` / `subscription_num`
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

| Field | Type | Values | Notes |
| --- | --- | --- | --- |
| `period_type` / `period_num` | int | `0` day / `2` month / `3` year / `4` hour | year/month packages usually `2` or `3` |
| `subscription_num` | int | 1..10000 | quote quantity |
| `size_measure_id` | int | linear only | see size-slot table |
| `fee_installment_mode` | string | `HALF_PAY` / `ZERO_PAY` / `NA` | CloudPond only, default `NA` |

Verified live: `c6.2xlarge.2.linux` ×1 month in `cn-north-1` → `official_website_amount` =
834.2 CNY; `ac3.large.2.linux` ×1 month → 179.2 CNY; `GPSSD` 40GB ×1 month → 28.0 CNY.

### `BSS/ListOnDemandResourceRatings` — on-demand quote

> **method**: POST · **safety**: readonly · **entities**: `RFQ_OnDemand_Header`, `RFQ_OnDemand_Line` · **pagination**: n/a · **doc**: [bcloud_01001](https://support.huaweicloud.com/api-bpconsole/bcloud_01001.html)
> **required**: `project_id` + per line `id` / `cloud_service_type` / `resource_type` / `resource_spec` / `region` / `usage_factor` / `usage_value` / `usage_measure_id` / `subscription_num`
> **conditional**: `linear_product` → `resource_size` + `size_measure_id`
> **optional**: `inquiry_precision` (`0` default 6 digits / `1` full 10)

```bash
hcloud BSS ListOnDemandResourceRatings \
  --project_id=<project_id> \
  --product_infos.1.id=1 \
  --product_infos.1.cloud_service_type=hws.service.type.ec2 \
  --product_infos.1.resource_type=hws.resource.type.vm \
  --product_infos.1.resource_spec=ac3.large.2.linux \
  --product_infos.1.region=cn-north-1 \
  --product_infos.1.usage_factor=Duration --product_infos.1.usage_value=1 --product_infos.1.usage_measure_id=4 \
  --product_infos.1.subscription_num=1 \
  --cli-region=cn-north-1 --cli-output=json
```

| Field | Type | Values | Notes |
| --- | --- | --- | --- |
| `usage_factor` | string | current `ListUsageTypes.code` | never default Duration |
| `usage_value` | number | per Trap #5 | capacity family=GB×hour; duration=hour; flow=GB |
| `usage_measure_id` | int | Trap #5 + `ListMeasureUnits` | usage slot; ≠ `size_measure_id` |
| `inquiry_precision` | int | `0` / `1` | default 6 digits / full 10 |

Verified live: `ac3.large.2.linux` Duration 1 hour in `cn-north-1` → `official_website_amount` =
0.37 CNY.

---

## response_contract (how to read the quote)

Read only the current response; **do not fabricate discounts**. `measure_id=1`=元(CNY);
`currency=CNY` (empty=CNY); `id` maps request line back. Default official price; attach discounted
only if returned. Sum of line items = total; on-demand response already includes `usage_value`, do
NOT multiply again.

| API | Official price | Discounted (report only if present) |
| --- | --- | --- |
| `ListRateOnPeriodDetail` | `official_website_rating_result.official_website_amount` (per line same object) | `optional_discount_rating_results[]` where `best_offer==1` |
| `ListOnDemandResourceRatings` | root / `product_rating_results[]` `official_website_amount` | `amount` when `discount_amount>0` |

---

## dimension_lookup

| Operation | Purpose | Required | Pagination |
| --- | --- | --- | --- |
| `BSS/ListServiceTypes` | `cloud_service_type` | - | limit/offset |
| `BSS/ListServiceResources` | →`resource_type` | `service_type_code` | limit/offset |
| `BSS/ListUsageTypes` | →`usage_factor` | **`resource_type_code`** | limit/offset |
| `BSS/ListMeasureUnits` | Measure Resolve (once per session) | - | none |
| `BSS/ListResourceTypes` | translate resource_type | - | limit/offset |
| `BSS/ListConversions` | measure base conversion | - | none |

```bash
hcloud BSS ListServiceTypes --cli-region=cn-north-1 --cli-output=json --limit=10 --offset=0
hcloud BSS ListServiceResources --service_type_code=hws.service.type.ec2 \
  --cli-region=cn-north-1 --cli-output=json --limit=10 --offset=0
hcloud BSS ListUsageTypes --resource_type_code=hws.resource.type.vm \
  --cli-region=cn-north-1 --cli-output=json --limit=100 --offset=0
hcloud BSS ListMeasureUnits --cli-region=cn-north-1 --cli-output=json
hcloud BSS ListConversions --measure_type=2 --cli-region=cn-north-1 --cli-output=json
```

---

## resource_spec_lookup

### `BSS/ListResourceSpecs` — the only valid spec resolution path

> **method**: POST · **safety**: readonly · **entities**: `Dim_ResourceSpec` · **pagination**: marker/limit · **doc**: [qct_00008](https://support.huaweicloud.com/api-oce/qct_00008.html)
> **required**: `cloud_service_type` / `resource_type` / `region_code` / `charge_mode` (`1` period / `3` on-demand)
> **optional**: `filters.[N].key=RESOURCE_SPEC` + `filters.[N].value`、`marker` + `limit`

- `marker`+`limit` together; first page no `marker`; next page from `page_info.next_marker`.
- `charge_mode`/`region_code` must match the quote line; the returned value already contains the OS suffix — never append.
- With a spec hint you must pass `filters`; `limit=100`; if 3 pages don't converge, stop and let the user pick; `429` retry once after 2s.
- Candidates take `cloud_service_basics[].resource_spec`; restate with `resource_spec_name`.

```bash
hcloud BSS ListResourceSpecs --charge_mode=1 \
  --cloud_service_type=hws.service.type.ec2 --resource_type=hws.resource.type.vm \
  --region_code=cn-north-1 \
  --filters.1.key=RESOURCE_SPEC --filters.1.value=c6.2xlarge \
  --limit=100 --cli-region=cn-north-1 --cli-output=json
```

### Linear product size slots (only these 3 types may fill `resource_size`+`size_measure_id`)

| `resource_type` | `size_measure_id` | unit |
| --- | --- | --- |
| `hws.resource.type.volume` | 17 | GB |
| `hws.resource.type.bandwidth` | 15 | Mbps |
| `hws.resource.type.share_bandwidth` | 15 | Mbps |

## scope_resolve

```bash
hcloud IAM KeystoneListAuthProjects --cli-region=cn-north-1 --cli-output=json
hcloud IAM KeystoneListAuthDomains --cli-region=cn-north-1 --cli-output=json
hcloud IAM KeystoneListProjects --domain_id=<domain_id> --cli-region=cn-north-1 --cli-output=json
hcloud ECS NovaListAvailabilityZones --cli-region=<resource_region> --cli-output=json  # optional; may 403 if account lacks ECS scope in that region
```