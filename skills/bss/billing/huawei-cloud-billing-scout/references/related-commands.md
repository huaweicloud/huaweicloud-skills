# Command Contract Appendix

This document only retains operation contracts: purpose, required fields, templates, and limits. Routing see `semantic/catalog.yml` (`required_context`; `triggers` as auxiliary, full triggers/refusal see `SKILL.md`), semantic boundary see `semantic/billing-ontology.yml` entity `evidence_boundary`.

## Command Format Standard

**Service name always `BSS`** — Do not use `account`, `bill` or other `hcloud` sub-services; balance, bills, reconciliation are all under `BSS` `List*` / `Show*`.

**Core format**: `hcloud BSS <Operation> --param=value --cli-region=<region> --cli-output=json` (`<Operation>` must be operation name in current entity `source_operations`)

### Format Rules

| Element | Format | Example |
| --- | --- | --- |
| Service name | Fixed `BSS` | `hcloud BSS ShowCustomerAccountBalances` |
| Operation name | `List*` / `Show*` | `ListCosts`, `ShowCustomerMonthlySum` |
| Regular parameter | `--key=value` | `--bill_cycle=2024-12`, `--limit=10` |
| Array parameter | `--key.1=value1` | `--resource_ids.1=<resource_id>` |
| Nested object | `--key.sub_key=value` | `--time_condition.begin_time=2024-12-01` |

## Global Constraints

- **Command whitelist** — Consistent with current entity `source_operations`; only `hcloud BSS <Operation>`. First query must copy this document `####` template; if no template then stop. Do not use `--help` to discover op or construct parameters; if template still errors, can use `--help` for that op only to verify fields (see `SKILL.md` verification path).
- Only execute `List*` / `Show*`; `List*` / `Show*` with `Change` in name are still read-only queries (e.g., account/coupon transactions), not write operations.
- Refuse payment, renewal, refund, unsubscribe, recovery, create, update, delete, send verification code, change balance or resources.
- Default `limit<=10`, `offset=0`; find prerequisite IDs at most recent 3 billing periods, 3 pages per command, `limit<=50` per page.
- Array and object parameters only use verified dot notation; if no template then stop, do not try JSON strings.
- Account, customer, resource, order, transaction, coupon, card, partner IDs default desensitized.

## customer_billing

| Operation | Purpose | Required | Note |
| --- | --- | --- | --- |
| `ShowCustomerAccountBalances` | Balance, debt, account composition snapshot | - | Current profile first query; see template |
| `ShowCustomerMonthlySum` | Monthly consumption summary | `bill_cycle` | Full account billing period overview; **cannot** filter by enterprise project (enterprise project ranking use `ListCosts`) |
| `ListCustomerBillsFeeRecords` | Billing period transaction, payment status, transaction reconciliation | `bill_cycle` | Cost center transaction side; billing period must be same month; see template |
| `ListCustomerselfResourceRecords` | Locate continuously charging resources | `cycle` | Resource ID default desensitized |
| `ListCustomerselfResourceRecordDetails` | Resource detail daily level | `cycle` | Export bill/resource detail side; see template; may have precision difference with summary |
| `ListCustomerBillsMonthlyBreakDown` | Monthly amortization | `shared_month` | Recent 18 months; non-cash deduction basis |
| `ListCustomerAccountChangeRecords` | Account transaction | `balance_type` | Read-only; not applicable for partner resale customers |
| `ListStoredValueCards` | Stored-value card status and face value | `status` | Card ID default desensitized |

## cost_and_usage

| Operation | Purpose | Required | Note |
| --- | --- | --- | --- |
| `ListCosts` | Cost analysis aggregation, TopN, trend | See template | `amount_type`/`cost_type` use string enum; `operator=0` include, `1` exclude |
| `ListResourceUsageSummary` | CDN/OBS/IEC/VPC usage summary | See template | 95 billing and usage verification |
| `ListResourceUsage` | Resource usage details | See template | First get resource and usage type from summary or detail |

### cost_and_usage Example Templates

`ListCosts` enums: `amount_type` = `PAYMENT_AMOUNT` (payable) or `NET_AMOUNT` (paid); `cost_type` = `ORIGINAL_COST` or `AMORTIZED_COST`.
Filter keys: `REGION_CODE`, `ENTERPRISE_PROJECT_ID` (**not** `ENTERPRISE_PROJECT`). Filter empty → write "no records for that project/condition"; **Prohibited**: remove filter to query full account ranking.

#### `ListCosts`

By region (billing period 2025-04):

```bash
hcloud BSS ListCosts \
  --amount_type=PAYMENT_AMOUNT \
  --cost_type=ORIGINAL_COST \
  --time_condition.begin_time=2025-04-01 \
  --time_condition.end_time=2025-04-30 \
  --time_condition.time_measure_id=1 \
  --groupby.1.key=CLOUD_SERVICE_TYPE \
  --groupby.1.type=dimension \
  --filters.1.filter_factor.key=REGION_CODE \
  --filters.1.filter_factor.value.1=cn-north-1 \
  --filters.1.operator=0 \
  --cli-region=<region> \
  --cli-output=json \
  --limit=10 \
  --offset=0
```

By enterprise project + cloud service ranking (`EP-FINANCE` example):

```bash
hcloud BSS ListCosts \
  --amount_type=PAYMENT_AMOUNT \
  --cost_type=ORIGINAL_COST \
  --time_condition.begin_time=2025-04-01 \
  --time_condition.end_time=2025-04-30 \
  --time_condition.time_measure_id=1 \
  --groupby.1.key=CLOUD_SERVICE_TYPE \
  --groupby.1.type=dimension \
  --filters.1.filter_factor.key=ENTERPRISE_PROJECT_ID \
  --filters.1.filter_factor.value.1=EP-FINANCE \
  --filters.1.operator=0 \
  --cli-region=<region> \
  --cli-output=json \
  --limit=10 \
  --offset=0
```

#### `ShowCustomerAccountBalances`

Balance/debt first query:

```bash
hcloud BSS ShowCustomerAccountBalances \
  --cli-region=<region> \
  --cli-output=json
```

#### `ListCustomerBillsFeeRecords`

Cost center billing period transaction (reconciliation transaction side):

```bash
hcloud BSS ListCustomerBillsFeeRecords \
  --bill_cycle=2025-04 \
  --cli-region=<region> \
  --cli-output=json \
  --limit=10 \
  --offset=0
```

#### `ListCustomerselfResourceRecordDetails`

Export resource details (reconciliation export side):

```bash
hcloud BSS ListCustomerselfResourceRecordDetails \
  --cycle=2025-04 \
  --cli-region=<region> \
  --cli-output=json \
  --limit=10 \
  --offset=0
```

## reconciliation (Minimum Read-Only Sequence)

Default current profile; if billing period not given use **current billing period** (delivery summary states clearly). Recommended sequence:

1. `ListCustomerBillsFeeRecords` — Cost center billing period transaction.
2. `ListCustomerselfResourceRecordDetails` — Same month resource details.
3. If still cannot connect difference, then query `ListCustomerOrders` / `ShowCustomerOrderDetails`.

Insufficient evidence no blame; do not use `ShowCustomerMonthlySum` to replace this sequence.

## discount_entitlement

| Operation | Purpose | Required | Note |
| --- | --- | --- | --- |
| `ListFreeResourceInfos` | Resource package list | - | Array parameters only use `.1`, `.2` increment; see template below |
| `ListFreeResourceUsages` | Resource package remaining quota | `free_resource_ids.1` | Usually no pagination; see template below |
| `ListFreeResourcesUsageRecords` | Package deduction details | See template | Span ≤90 days |
| `ListCustomerCouponChangeRecords` | Coupon transaction | `balance_type` | Coupon ID, transaction ID default desensitized |
| `ListQuotaCoupons` | Partner coupon quota | - | Read-only quota; see template below |
| `ListIssuedCouponQuotas` | Issued coupon quota | - | Master reseller scenario |
| `ListCouponQuotasRecords` | Coupon quota operation records | - | Read-only records |
| `ListIssuedPartnerCoupons` | Issued coupons | - | Coupon ID, customer ID default desensitized |
| `ListPartnerCouponsRecord` | Coupon issue/recovery records | - | Read-only records; see template below |
| `ListSubCustomerCoupons` | Partner own coupons | - | Read-only |
| `ListOrderCouponsByOrderId` | Order available coupons | `order_id` | Near payment, read-only explanation |

### discount_entitlement Example Templates

#### `ListFreeResourceInfos`

```bash
hcloud BSS ListFreeResourceInfos \
  --service_type_code_list.1=hws.service.type.obs \
  --cli-region=<region> \
  --cli-output=json
```

#### `ListFreeResourceUsages`

```bash
hcloud BSS ListFreeResourceUsages \
  --free_resource_ids.1=<free_resource_id> \
  --cli-region=<region> \
  --cli-output=json
```

#### `ListQuotaCoupons`

```bash
hcloud BSS ListQuotaCoupons \
  --quota_ids.1=<quota_id> \
  --quota_status_list.1=0 \
  --cli-region=<region> \
  --cli-output=json
```

#### `ListPartnerCouponsRecord`

```bash
hcloud BSS ListPartnerCouponsRecord \
  --coupon_ids.1=<coupon_id> \
  --operation_types.1=1 \
  --cli-region=<region> \
  --cli-output=json
```

## order_evidence

| Operation | Purpose | Required | Note |
| --- | --- | --- | --- |
| `ListCustomerOrders` | Order list | - | Only query evidence, do not guide payment |
| `ShowCustomerOrderDetails` | Order details | `order_id` | Order ID default desensitized |
| `ShowRefundOrderDetails` | Unsubscribe/downgrade refund details | `order_id` | Only explain refund evidence, do not execute unsubscribe refund |
| `ListOrderDiscounts` | Order available discounts | `order_id` | Near payment, read-only explanation |

## enterprise_multi_account

| Operation | Purpose | Required | Note |
| --- | --- | --- | --- |
| `ListEnterpriseOrganizations` | Enterprise organization structure | - | Enterprise master account scenario |
| `ListEnterpriseSubCustomers` | Enterprise sub-account list | - | Sub-account ID default desensitized |
| `ListEnterpriseMultiAccount` | Sub-account recoverable balance | See template | Read-only; do not recover |
| `ShowMultiAccountTransferAmount` | Master account transferable | `balance_type` | Read-only; do not transfer |
| `ListMultiAccountTransferCoupons` | Master account transferable coupons | - | Read-only; do not issue |
| `ListMultiAccountRetrieveCoupons` | Sub-account recoverable coupons | `sub_customer_id` | Read-only; do not recover |
| `ListConsumeSubCustomers` | Sub-customers with consumption | `bill_cycle` | Enterprise/partner entry |
| `ListSubcustomerMonthlyBills` | Sub-customer monthly bills | `cycle`, `charge_mode` | Customer ID desensitized |
| `ListSubCustomerBillDetail` | Sub-customer details | `bill_cycle`, `customer_id` | First confirm authorization |

## partner_resale

| Operation | Purpose | Required | Note |
| --- | --- | --- | --- |
| `ListSubCustomers` | Partner customer list | - | Customer information sensitive, default summary |
| `ListSubCustomerNewTag` | New customer tag | - | Read-only; see template |
| `ListCustomerOnDemandResources` | Resale on-demand resources | `customer_id` | Resource ID desensitized; see template |
| `ListPayPerUseCustomerResources` | Annual/monthly package resources | - | Historical naming; see template |
| `ListCustomersBalancesDetail` | Resale balance | See template | Sensitive; see template |
| `ListPartnerBalances` | Partner/reseller balance | - | Partner perspective |
| `ListPartnerAccountChangeRecords` | Partner transaction records | `balance_type` | Read-only transaction |
| `ListPartnerAdjustRecords` | Partner adjustment records | - | Read-only records; do not execute transfer or recovery |
| `ListIndirectPartners` | Secondary reseller list | - | Master reseller scenario |

### partner_resale Example Templates

#### `ListSubCustomerNewTag`

```bash
hcloud BSS ListSubCustomerNewTag \
  --customer_ids.1=<customer_id> \
  --cli-region=<region> \
  --cli-output=json
```

#### `ListCustomerOnDemandResources`

```bash
hcloud BSS ListCustomerOnDemandResources \
  --customer_id=<customer_id> \
  --resource_ids.1=<resource_id> \
  --cli-region=<region> \
  --cli-output=json
```

#### `ListPayPerUseCustomerResources`

```bash
hcloud BSS ListPayPerUseCustomerResources \
  --resource_ids.1=<resource_id> \
  --status_list.1=2 \
  --cli-region=<region> \
  --cli-output=json
```

#### `ListCustomersBalancesDetail`

```bash
hcloud BSS ListCustomersBalancesDetail \
  --customer_infos.1.customer_id=<customer_id> \
  --cli-region=<region> \
  --cli-output=json
```

## reference_dimensions

| Operation | Purpose | Required | Note |
| --- | --- | --- | --- |
| `ListServiceTypes` | Cloud service type dictionary | - | Translate `service_type_code` |
| `ListResourceTypes` | Resource type dictionary | - | Translate `resource_type_code` |
| `ListUsageTypes` | Usage type dictionary | - | Translate `usage_type` |
| `ListMeasureUnits` | Measurement unit dictionary | - | Translate amount and usage units |
| `ListConversions` | Measurement unit conversion | - | For unit conversion |
| `ListServiceResources` | Service to resource type relation | `service_type_code` | Service/resource mapping dictionary |
| `ListProvinces` | Province dictionary | - | Partner sales platform geography |
| `ListCities` | City dictionary | `province_code` | Partner sales platform geography |
| `ListCounties` | District/county dictionary | `city_code` | Partner sales platform geography |

## Out of Scope (Refuse Routing)

| Category | Refuse Reason | Alternative |
| --- | --- | --- |
| Price trial / renewal quote / discount strategy | Not billed fact; pricing cannot be used as deduction evidence | Console price calculator or sales-side pricing tool |
| Real-name authentication review result | Identity dimension not within BSS billing boundary | Console account center |
| Non-Huawei Cloud billing | Only serve Huawei Cloud BSS | Corresponding cloud vendor tool |

## Product-Side Read-Only Cross-Validation

BSS is billing fact source. Product API only answers "whether resource can currently be found", does not overturn historical bill;
Only after BSS has clues, then query product-side `List` / `Show` / `Get`.