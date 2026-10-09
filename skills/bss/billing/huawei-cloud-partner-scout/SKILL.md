---
name: huawei-cloud-partner-scout
description: |
  Huawei Cloud BSS partner-scope read-only scout (not AWS/Azure; refuses write ops,
  pricing quotes, real-name review): sub-customers, partner/customer/indirect-partner
  balances, account flows, adjust records, indirect partners, coupon quotas, coupons,
  sub-customer bills, customer resources, orders, refunds via huaweicloudsdkbss SDK
  (KooCLI 7.2.12 ships BSS operations — `hcloud BSS <Operation>` mirrors the same
  partner endpoints; SDK mode is the verified path used in this skill).
  Triggers include: "华为云伙伴", "解决方案提供商", "总经销商", "客户列表", "账户余额", "欠费",
  "收支明细", "云经销商", "经销商", "代金券额度", "优惠券", "客户消费账单", "子客户账单",
  "月度账单", "消费子客户", "包年包月资源", "按需资源", "资源列表", "订单列表", "订单详情",
  "退款详情", "客户订单", "partner customer list", "partner balance", "coupon quota",
  "sub-customer bill", "customer order".
  Refuses: pay, refund, unsubscribe, create, update, delete, grant, reclaim.
tags: [huawei-cloud, partner, bss, read-only, billing]
---

# Huawei Cloud Partner Scout — Partner-View Read-Only Queries

Huawei Cloud partner (解决方案提供商 / 总经销商, 代售模式) read-only account scout:
customers, balances, transactions, indirect partners, coupon quotas, coupons,
sub-customer bills, resources, and orders — one conversation, via the
`huaweicloudsdkbss` SDK (bpconsole-api v156 semantics, endpoint
`bss.myhuaweicloud.com`, fixed region `cn-north-1`).

Query only. No modifications, no account operations on behalf of users.

## Overview

- **Who**: Huawei Cloud partners (solution provider / reseller with sub-customers),
  and their second-level indirect partners (云经销商).
- **What**: aggregate the scattered partner-console query pages into one semantic
  layer; answer partner account questions directly in conversation.
- **Scope**: 10 entry points × 22 facts across 6 business processes
  (customer / partner / coupon / bill / resource / order). See
  `references/semantic/catalog.yml` for routing and `references/semantic/models/*.yml`
  for fact definitions.
- **Mode**: SDK (`huaweicloudsdkbss`) — the verified execution path in real-environment
  testing. KooCLI 7.2.12 does ship the BSS service: its CN-site official metadata lists
  BSS (`api_count=87`, `has_data=true`) with a `hcloud BSS <Operation>` counterpart for
  every query entry point in this skill. Note: the intl-site metadata stub lists BSS as
  "Operation Capability" with `api_count=0` / `has_data=false`, so an intl-configured
  `hcloud` reports `[USE_ERROR]Unsupported service: BSS.` — that is a site-metadata
  stub, not absence of BSS from KooCLI. This skill standardizes on the SDK because the
  real-environment verification and quality harness are SDK-based; the CLI mirrors the
  same `BSS <Operation>` names against the same partner endpoints where BSS is exposed.
- **Not in scope**: 转售模式 (credit-limit management), real-name review, pricing
  quotes, write operations of any kind.

## Prerequisites

| Item | Requirement |
| --- | --- |
| Python | 3.8+ with `huaweicloudsdkbss` ≥ 3.1 (tested 3.1.211) |
| Credentials | Partner account AK/SK (解决方案提供商或总经销商), env vars `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` (or `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`) |
| Endpoint | Fixed `https://bss.myhuaweicloud.com` — BSS is a global service; use `GlobalCredentials` + `with_endpoints`, never `BasicCredentials` + `with_region` |
| Region | Fixed `cn-north-1` (partner APIs are region-fixed; not configurable) |
| Network | Corporate intranet may require `HTTPS_PROXY`; see error table |

Quality reporting environment (optional, see § Quality Reporting):

| Environment Variable | Required | Description |
| --- | --- | --- |
| `SKILL_QUALITY_ENDPOINT` | No | 上报地址，默认 `https://skillsapi.developer.myhuaweicloud.com/api/quality/report` |
| `SKILL_QUALITY_NAME` | No | Skill 名称（默认自动识别） |
| `SKILL_QUALITY_DISABLE` | No | 设为 `1` 禁用上报（本地调试用） |
| `SKILL_QUALITY_TIMEOUT` | No | 上报超时秒数（默认 3） |

Install check:

```bash
pip install huaweicloudsdkbss
python3 -c "import huaweicloudsdkbss; print('sdk ok')"
```

This skill is **SDK-only**: it does not depend on KooCLI, so no
`references/cli-installation-guide.md` is shipped (the only install step is the
`pip install` above) and there is no `--cli-region` concept — all region/endpoint
selection happens through `GlobalCredentials` + `with_endpoints` (fixed
`cn-north-1` / `bss.myhuaweicloud.com`).

Credentials are read **only from environment variables** (`HUAWEICLOUD_SDK_AK` /
`HUAWEICLOUD_SDK_SK`, or the `SKILL_QUALITY_*` equivalents); no global credential
files (`~/.config/huaweicloud/credentials.json`, `~/.hcloud/config.json`) are
ever read by this skill or its quality-reporting SDK.

## Workflow

| Phase | Task | Reference | Forbidden |
| --- | --- | --- | --- |
| Gate | Confirm the user means Huawei Cloud partner account (current AK/SK profile); otherwise one confirmation question, no BSS call | SKILL.md § Boundaries | Querying AWS/Azure or non-partner accounts |
| Route | Match user scope/time to an entry point in `catalog.yml`; get `primary_facts` | `references/semantic/catalog.yml` | Cross-entry-point summing or borrowing |
| Gather | Minimal read-only queries from the matching template block in `related-commands.md`; stay inside each fact's `evidence_boundary` | `references/models/*.yml` + `references/related-commands.md` | Self-constructed JSON bodies; full detail lists first |
| Deliver | Conclusion first, then facts; assertion must be reducible to fact × grain × money_basis | SKILL.md § Response Requirements | Sending raw responses, command text, full IDs |

Two fixed defaults:

- **BSS Endpoint** — always `https://bss.myhuaweicloud.com` / region `cn-north-1`;
  no substitution with profile or other regions. **[Fixed config, non-adjustable]**
- **Read-Only Default** — when the user has expressed read-only intent, default to
  the current profile and current (or given) billing period; ask one blocking ID at
  a time (e.g. `customer_id`) only when the ontology requires it.

## Core Commands

All commands are `huaweicloudsdkbss` Python SDK calls (client init once, reused):

```python
import os
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient

creds = GlobalCredentials(os.environ["HUAWEICLOUD_SDK_AK"], os.environ["HUAWEICLOUD_SDK_SK"])
client = BssClient.new_builder().with_credentials(creds).with_endpoints(["https://bss.myhuaweicloud.com"]).build()
```

Copy the exact template block from `references/related-commands.md` (each is anchored
by a `####` heading) for the first query of any operation — do not reconstruct request
bodies from memory or from SDK signatures. `limit` defaults to 10 and the hard cap is
**100** (BSS rejects `limit` > 100 with HTTP 400).

### Scenario examples

Client is initialized once and reused; response shapes follow the facts in
`references/semantic/models/*.yml`.

#### 子客户列表 / 新客标签

```python
from huaweicloudsdkbss.v2 import ListSubCustomersRequest, ListSubCustomerNewTagRequest
from huaweicloudsdkbss.v2.model import QuerySubCustomerListReq

resp = client.list_sub_customers(ListSubCustomersRequest(
    body=QuerySubCustomerListReq(association_type="2", limit=10, offset=0)))
resp = client.list_sub_customer_new_tag(ListSubCustomerNewTagRequest())
```

#### 伙伴/客户余额、欠费

```python
from huaweicloudsdkbss.v2 import ListPartnerBalancesRequest, ListCustomersBalancesDetailRequest
from huaweicloudsdkbss.v2.model import QueryCustomersBalancesReq, CustomerInfoV2

resp = client.list_partner_balances(ListPartnerBalancesRequest())
resp = client.list_customers_balances_detail(ListCustomersBalancesDetailRequest(
    body=QueryCustomersBalancesReq(customer_infos=[CustomerInfoV2(customer_id="<customer_id>")])))
```

#### 收支明细 / 调账记录

```python
from huaweicloudsdkbss.v2 import ListPartnerAccountChangeRecordsRequest, ListPartnerAdjustRecordsRequest

resp = client.list_partner_account_change_records(ListPartnerAccountChangeRecordsRequest(
    balance_type="BALANCE_TYPE_DEBIT", trade_time_begin="2026-08-01T00:00:00Z",
    trade_time_end="2026-08-31T23:59:59Z", offset=0, limit=10))
resp = client.list_partner_adjust_records(ListPartnerAdjustRecordsRequest(
    customer_id=None, offset=0, limit=10))
```

#### 云经销商列表

```python
from huaweicloudsdkbss.v2 import ListIndirectPartnersRequest
from huaweicloudsdkbss.v2.model import QueryIndirectPartnersReq

resp = client.list_indirect_partners(ListIndirectPartnersRequest(
    body=QueryIndirectPartnersReq(account_name=None, offset=0, limit=10)))
```

#### 代金券额度（自身/已发放/记录）

```python
from huaweicloudsdkbss.v2 import ListQuotaCouponsRequest, ListIssuedCouponQuotasRequest, ListCouponQuotasRecordsRequest
from huaweicloudsdkbss.v2.model import QueryCouponQuotasReqExt

resp = client.list_quota_coupons(ListQuotaCouponsRequest(
    body=QueryCouponQuotasReqExt(quota_type=0, offset=0, limit=10)))
resp = client.list_issued_coupon_quotas(ListIssuedCouponQuotasRequest(indirect_partner_id=None, limit=10))
resp = client.list_coupon_quotas_records(ListCouponQuotasRecordsRequest(
    indirect_partner_id=None, operation_time_begin="2026-08-01T00:00:00Z",
    operation_time_end="2026-08-31T23:59:59Z", limit=10))
```

#### 优惠券（自身/已发放/记录）

```python
from huaweicloudsdkbss.v2 import ListSubCustomerCouponsRequest, ListIssuedPartnerCouponsRequest, ListPartnerCouponsRecordRequest

resp = client.list_sub_customer_coupons(ListSubCustomerCouponsRequest(status=None, offset=0, limit=10))
# resp.user_coupons: [ {coupon_id, status, face_value, valid_time, expire_time} ]
resp = client.list_issued_partner_coupons(ListIssuedPartnerCouponsRequest(customer_id="<customer_id>", limit=10))
# resp.user_coupons: [ {coupon_id, customer_id, face_value, status} ]
resp = client.list_partner_coupons_record(ListPartnerCouponsRecordRequest(
    operation_time_begin="2026-08-01T00:00:00Z",
    operation_time_end="2026-08-31T23:59:59Z", limit=10))
```

#### 消费子客户 / 消费明细 / 月度账单

```python
from huaweicloudsdkbss.v2 import ListConsumeSubCustomersRequest, ListSubCustomerBillDetailRequest, ListSubcustomerMonthlyBillsRequest
from huaweicloudsdkbss.v2.model import ListConsumeSubCustomersReq

resp = client.list_consume_sub_customers(ListConsumeSubCustomersRequest(
    body=ListConsumeSubCustomersReq(bill_cycle="2026-08", offset=0, limit=10)))
resp = client.list_sub_customer_bill_detail(ListSubCustomerBillDetailRequest(
    bill_cycle="2026-08", customer_id="<customer_id>", offset=0, limit=10))
resp = client.list_subcustomer_monthly_bills(ListSubcustomerMonthlyBillsRequest(
    customer_id="<customer_id>", cycle="2026-08", charge_mode=None, limit=10))
```

#### 包年包月 / 按需资源 / 资源包

```python
from huaweicloudsdkbss.v2 import ListPayPerUseCustomerResourcesRequest, ListCustomerOnDemandResourcesRequest, ListFreeResourceInfosRequest
from huaweicloudsdkbss.v2.model import QueryResourcesReq, QueryCustomerOnDemandResourcesReq, ListFreeResourceInfosReq

resp = client.list_pay_per_use_customer_resources(ListPayPerUseCustomerResourcesRequest(
    body=QueryResourcesReq(customer_id="<customer_id>", status_list=[2], limit=10)))
resp = client.list_customer_on_demand_resources(ListCustomerOnDemandResourcesRequest(
    body=QueryCustomerOnDemandResourcesReq(customer_id="<customer_id>", status=None, limit=10)))
resp = client.list_free_resource_infos(ListFreeResourceInfosRequest(
    body=ListFreeResourceInfosReq(status=1, offset=0, limit=10)))
```

#### 订单列表 / 详情 / 退款

```python
from huaweicloudsdkbss.v2 import ListCustomerOrdersRequest, ShowCustomerOrderDetailsRequest, ShowRefundOrderDetailsRequest

resp = client.list_customer_orders(ListCustomerOrdersRequest(
    customer_id="<customer_id>", status=None, limit=10, offset=0))
resp = client.show_customer_order_details(ShowCustomerOrderDetailsRequest(
    order_id="<order_id>", limit=10, offset=0))
resp = client.show_refund_order_details(ShowRefundOrderDetailsRequest(
    order_id="<order_id>", customer_id=None, indirect_partner_id=None))
```

#### 字典（服务/资源/用量/单位/地域）

```python
from huaweicloudsdkbss.v2 import ListServiceTypesRequest, ListResourceTypesRequest
from huaweicloudsdkbss.v2 import ListUsageTypesRequest, ListMeasureUnitsRequest, ListConversionsRequest
from huaweicloudsdkbss.v2 import ListProvincesRequest, ListCitiesRequest, ListCountiesRequest

resp = client.list_service_types(ListServiceTypesRequest(service_type_name=None, limit=10))
resp = client.list_resource_types(ListResourceTypesRequest())
resp = client.list_usage_types(ListUsageTypesRequest())
resp = client.list_measure_units(ListMeasureUnitsRequest())
resp = client.list_conversions(ListConversionsRequest())
resp = client.list_provinces(ListProvincesRequest())
resp = client.list_cities(ListCitiesRequest(province_code="<province_code>"))
resp = client.list_counties(ListCountiesRequest(city_code="<city_code>"))
```

| Scenario | Operation (BssClient method) | Template section in `references/related-commands.md` |
| --- | --- | --- |
| 子客户列表 / 新客标签 | `list_sub_customers` / `list_sub_customer_new_tag` | sub_customer |
| 伙伴/客户余额、欠费 | `list_partner_balances` / `list_customers_balances_detail` | account_balance |
| 收支明细 / 调账记录 | `list_partner_account_change_records` / `list_partner_adjust_records` | account_flow |
| 云经销商列表 | `list_indirect_partners` | indirect_partner |
| 代金券额度（自身/已发放/记录） | `list_quota_coupons` / `list_issued_coupon_quotas` / `list_coupon_quotas_records` | coupon_quota |
| 优惠券（自身/已发放/记录） | `list_sub_customer_coupons` / `list_issued_partner_coupons` / `list_partner_coupons_record` | coupon_issue |
| 消费子客户 / 消费明细 / 月度账单 | `list_consume_sub_customers` / `list_sub_customer_bill_detail` / `list_subcustomer_monthly_bills` | customer_bill |
| 包年包月 / 按需资源 / 资源包 | `list_pay_per_use_customer_resources` / `list_customer_on_demand_resources` / `list_free_resource_infos` | customer_resource |
| 订单列表 / 详情 / 退款 | `list_customer_orders` / `show_customer_order_details` / `show_refund_order_details` | customer_order |
| 字典（服务/资源/用量/单位/地域） | `list_service_types` / `list_resource_types` / `list_usage_types` / `list_measure_units` / `list_conversions` / `list_provinces` / `list_cities` / `list_counties` | reference_dictionary |

## Parameter Confirmation

All 30 operations have zero mandatory SDK-level parameters except where noted
(the APIs treat unset filters as "no filtering"). Required (语义必需) parameters:

| Operation | Required params | Notes |
| --- | --- | --- |
| `list_customers_balances_detail` | `customer_infos` (batch, ≤100) | body `QueryCustomersBalancesReq` |
| `list_consume_sub_customers` | `bill_cycle` (YYYY-MM) | body `ListConsumeSubCustomersReq` |
| `list_customer_on_demand_resources` | `customer_id` | body `QueryCustomerOnDemandResourcesReq` |
| `list_pay_per_use_customer_resources` | `customer_id` (to query sub-customer resources) | body `QueryResourcesReq` |
| `show_customer_order_details` | `order_id` (path param) | GET `/v2/orders/customer-orders/details/{order_id}` |
| `list_cities` | `province_code` | GET dictionary |
| `list_counties` | `city_code` | GET dictionary |

Key optional filters: `association_type` (1=顾问销售 2=代售), `balance_type`
(BALANCE_TYPE_DEBIT=现金账户 BALANCE_TYPE_CREDIT=信用账户), `status`/`status_list` (resources/coupons), `bill_cycle`/`cycle`
(YYYY-MM), `indirect_partner_id` (scope to a 云经销商), `operation_time_begin/end`,
`trade_time_begin/end`, `expire_time_begin/end`, `create_time_begin/end`.
Times are UTC `YYYY-MM-DD'T'HH:mm:ss'Z'`; see the full table in
`references/related-commands.md`.

## Error Handling

| Error | Meaning | Action |
| --- | --- | --- |
| `domain_id has no access to this api` | Account has no partner access | **Stop immediately**; tell the user the account is not a partner (解决方案提供商/总经销商) |
| `CBC.0151` | Access denied | Report insufficient permission; no retry loop |
| `NETWORK_ERROR` / timeout | Network blocked | Suggest `HTTPS_PROXY` (corporate intranet), retry once |
| `CBC.80021021` | Query span > 1 year | Normal API guard; narrow the time range |
| HTTP 400 on coupon/list queries | `limit` > 100 | Retry with `limit ≤ 100` |

## Boundaries

- **Service Scope** — Only BSS partner (代售) read-only queries. Non-Huawei Cloud or
  other cloud vendor accounts are out of scope.
- **Refuse Routing** — Payment, refund, unsubscribe, recovery, grant/reclaim
  (额度和优惠券), create/update/delete, real-name review, pricing quotes: refuse with
  one sentence, no BSS calls, no evidence gathering.
- **No Leak** — No output of credentials, complete business IDs, profile/region info.
- **No Extrapolation** — Pagination, partial time windows, and zero/low-amount
  results cannot be stated as "whole account" or "no further charges".
- **Official Identity** — Does not represent Huawei Cloud; conclusions only based on
  evidence found at that time.
- **Response Language** — Consistent with the user; structure follows
  § Response Requirements.
- **Environment Ready** — If the SDK/credentials are missing, relay the prerequisite
  checklist; do not install or configure on behalf of the user.

## Response Requirements

- **Like a Brief** — Summary in one to three sentences (scope / period / money
  basis), then facts as short bullets; mark uncertainty when evidence is missing.
- **Only Trust Evidence** — List only what was found, using business names
  (console wording, not API names); no amounts for unchecked items.
- **Delivery Baseline** — No raw responses, command text, complete business IDs,
  credentials, profile/region. Gaps get exactly one read-only next step in business
  wording.

## Quality Reporting

This Skill integrates [skill_quality_sdk.py](scripts/skill_quality_sdk.py) for
execution quality reporting. Every run automatically reports trace_id, status
(success/biz_fail/sys_fail/cancel), error code, cost, and masked input/output to
the operations console.

### Credentials for reporting

Reporting credentials come **only from environment variables**
(`SKILL_QUALITY_AK` / `SKILL_QUALITY_SK`, falling back to `HUAWEICLOUD_SDK_AK` /
`HUAWEICLOUD_SDK_SK`, `HUAWEI_CLOUD_SDK_AK` / `HUAWEI_CLOUD_SDK_SK`,
`HW_ACCESS_KEY` / `HW_SECRET_KEY`, or the direct `SKILL_QUALITY_TOKEN`). The SDK
never reads global credential files and never accepts credential passthrough
from `.quality_report.json`. Without credentials the report is skipped
silently — it never blocks the skill flow.

### Integration
- **Python entry point:** wrap main logic with `quality_context` context manager:

  ```python
  from skill_quality_sdk import quality_context, QualityError

  with quality_context(skill_name="huawei-cloud-partner-scout", skill_version="1.0.0") as q:
      q.input = {"entry_point": "account_balance"}
      result = query_partner_balances()   # actual SDK work
      q.output = {"account_count": len(result.account_balances)}
  ```
- **Query-only Skill:** no mutating step exists; report `success` on data returned,
  `biz_fail` (with U/C/N error code) on the intercepted errors above.

### Error Code Convention
| Prefix | Category | Examples |
| --- | --- | --- |
| U | User input | U01 missing param, U03 no data found |
| C | Configuration | C01 missing AK/SK/env, C02 missing SDK |
| N | Network | N01 timeout, N02 connection refused |
| B | Code bug | B01 null pointer, B04 version mismatch |
| P | Platform | P01 scheduler error, P02 resource insufficient |

Reporting is non-blocking and fails silently — it never interrupts the Skill main
flow. Disable via `SKILL_QUALITY_DISABLE=1` for local testing.

## Reference Documents

| Reference | Description |
| --- | --- |
| `references/semantic/catalog.yml` | Thin router: 10 entry_points → primary_facts + ontology_files |
| `references/semantic/shared-dimensions.yml` | 9 conformed dimensions (Dim_Customer … Dim_Time) |
| `references/semantic/models/customer.yml` | SubCustomer / SubCustomerNewTag facts |
| `references/semantic/models/partner.yml` | PartnerBalance / CustomerBalance / AccountChange / Adjust / IndirectPartner facts + ReferenceCatalog loader |
| `references/semantic/models/coupon.yml` | QuotaCoupon / IssuedCouponQuota / CouponQuotaRecord / SubCustomerCoupon / IssuedPartnerCoupon / PartnerCouponRecord facts |
| `references/semantic/models/bill.yml` | ConsumeSubCustomer / SubCustomerBillDetail / SubcustomerMonthlyBill facts |
| `references/semantic/models/resource.yml` | PayPerUseCustomerResource / CustomerOnDemandResource / FreeResourceInfo facts |
| `references/semantic/models/order.yml` | CustomerOrder + child facts OrderDetail / RefundOrderDetail |
| `references/related-commands.md` | Copyable SDK templates, limits, error interception |
| `references/iam-policies.md` | Least-privilege read-only IAM policy |
| `references/verification-method.md` | Environment + smoke verification procedure |
| `references/acceptance-criteria.md` | Acceptance checklist |
| `references/dataflow-diagram.md` | Mermaid data flow diagram |