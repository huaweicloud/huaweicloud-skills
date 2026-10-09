# Partner Command Templates (SDK mode)

Copyable operation contracts for the partner-scout skill: purpose, required fields,
templates, and limits. Routing lives in `semantic/catalog.yml`; semantic boundary in
`semantic/models/*.yml` entity `evidence_boundary`.

## Command Format Standard

**Execution mode is SDK primary.** KooCLI 7.2.12 does ship the BSS service: its
CN-site official metadata lists BSS (`api_count=87`, `has_data=true`) with a
`hcloud BSS <Operation>` counterpart for every query entry point below. The intl-site
metadata stub lists BSS as "Operation Capability" with `api_count=0`, so an
intl-configured `hcloud` may fail with `[USE_ERROR]Unsupported service: BSS.` All
templates below use the `huaweicloudsdkbss` Python SDK, the verified execution path.

**BSS is a global service** — always initialize with `GlobalCredentials` +
`with_endpoints`; `BasicCredentials` + `with_region` does not work:

```python
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient, ListSubCustomersRequest

creds = GlobalCredentials(os.environ["HUAWEICLOUD_SDK_AK"],
                          os.environ["HUAWEICLOUD_SDK_SK"])
client = BssClient.new_builder() \
    .with_credentials(creds) \
    .with_endpoints(["https://bss.myhuaweicloud.com"]) \
    .build()
```

| Element | Format | Example |
| --- | --- | --- |
| Endpoint | Fixed `https://bss.myhuaweicloud.com` | partner (代售/bpconsole) API |
| Region | Fixed `cn-north-1` | partner APIs are region-fixed |
| Operation | `BssClient.<ListXxx|ShowXxx>()` request/response classes in `huaweicloudsdkbss.v2` | `list_partner_balances` |
| Body param | request `.with_<field>(...)` or constructor kwargs | `ListSubCustomersRequest(body=QuerySubCustomerListReq(limit=10))` |
| Pagination | `offset` from 0, `limit` ≤ 100 (BSS max is **100**, not 200 → 400 error) | `limit=10` default |
| Header lang | Some APIs accept `X-Language` (`x_language`) | `x_language="zh-cn"` |
| Time format | Parameters `YYYY-MM-DD'T'HH:mm:ss'Z'` (UTC), bill cycle `YYYY-MM` | `bill_cycle="2026-08"` |

## Global Constraints

- **Command whitelist** — only the `source_operations` listed in the model files.
  First query copies the `####` template below; no `--help`-style discovery, no
  self-constructed JSON bodies.
- Only `List*` / `Show*`; refuse payment, refund, unsubscribe, recovery, create,
  update, delete, send verification code, change balance or resources.
- Default `limit<=10`, `offset=0`; find prerequisite IDs at most 3 pages per
  command, `limit<=50` per page during reconnaissance.
- Array parameters use list objects, never string-concatenated JSON.
- Customer, resource, order, transaction, coupon, quota IDs default desensitized
  in responses.

## sub_customer

| Operation | Purpose | Required | Note |
| --- | --- | --- | --- |
| `BssClient.list_sub_customers` | 子客户列表（按关联类型/客户名/客户ID筛选） | - | body `QuerySubCustomerListReq`; `association_type` 1=顾问销售 2=代售 |
| `BssClient.list_sub_customer_new_tag` | 客户新客标签 | - | body `ListSubCustomerNewTagReq`; `customer_ids` batch |

#### `list_sub_customers`

```python
from huaweicloudsdkbss.v2 import ListSubCustomersRequest
from huaweicloudsdkbss.v2.model import QuerySubCustomerListReq

req = ListSubCustomersRequest(
    body=QuerySubCustomerListReq(
        association_type="2",    # 代售; omit for all
        customer_id=None,        # optional filter
        limit=10, offset=0
    )
)
resp = client.list_sub_customers(req)
for c in resp.customer_infos:
    print(c.customer_id, c.account_name, c.association_type)
```

#### `list_sub_customer_new_tag`

```python
from huaweicloudsdkbss.v2 import ListSubCustomerNewTagRequest
from huaweicloudsdkbss.v2.model import ListSubCustomerNewTagReq

req = ListSubCustomerNewTagRequest(
    body=ListSubCustomerNewTagReq(customer_ids=["<customer_id_1>"], limit=10)
)
resp = client.list_sub_customer_new_tag(req)
# resp.new_customer_tags: list of {customer_id, new_customer_tag}
```

## account_balance

| Operation | Purpose | Required | Note |
| --- | --- | --- | --- |
| `BssClient.list_partner_balances` | 伙伴/经销商账户余额 | - | GET; `indirect_partner_id` optional |
| `BssClient.list_customers_balances_detail` | 客户账户余额批量查询 | `customer_infos` | body `QueryCustomersBalancesReq`; max 100 customers per call |

#### `list_partner_balances`

```python
from huaweicloudsdkbss.v2 import ListPartnerBalancesRequest

resp = client.list_partner_balances(ListPartnerBalancesRequest())
# resp.account_balances: [ {account_id, account_type, amount, currency, designated_amount} ]
```

#### `list_customers_balances_detail`

```python
from huaweicloudsdkbss.v2 import ListCustomersBalancesDetailRequest
from huaweicloudsdkbss.v2.model import QueryCustomersBalancesReq, CustomerInfoV2

req = ListCustomersBalancesDetailRequest(
    body=QueryCustomersBalancesReq(
        customer_infos=[CustomerInfoV2(customer_id="<customer_id>")]
    )
)
resp = client.list_customers_balances_detail(req)
for b in resp.customer_balances:
    print(b.customer_id, b.amount, b.debt_amount, b.currency)
```

## account_flow

| Operation | Purpose | Required | Note |
| --- | --- | --- | --- |
| `BssClient.list_partner_account_change_records` | 伙伴收支明细（现金/信用账户） | - | `balance_type` BALANCE_TYPE_DEBIT=现金账户 BALANCE_TYPE_CREDIT=信用账户; `trade_time_begin/end` UTC |
| `BssClient.list_partner_adjust_records` | 调账记录（拨款/回收历史） | - | `customer_id` filter; `operation_type` 10=发放/拨款 20=回收 |

#### `list_partner_account_change_records`

```python
from huaweicloudsdkbss.v2 import ListPartnerAccountChangeRecordsRequest

req = ListPartnerAccountChangeRecordsRequest(
    balance_type="BALANCE_TYPE_DEBIT",   # BALANCE_TYPE_DEBIT: 现金账户 BALANCE_TYPE_CREDIT: 信用账户
    trade_type=None,                # trade type filter
    trade_time_begin="2026-08-01T00:00:00Z",
    trade_time_end="2026-08-31T23:59:59Z",
    offset=0, limit=10
)
resp = client.list_partner_account_change_records(req)
for r in resp.records:
    print(r.trade_id, r.trade_time, r.change_amount, r.type)
```

#### `list_partner_adjust_records`

```python
from huaweicloudsdkbss.v2 import ListPartnerAdjustRecordsRequest

req = ListPartnerAdjustRecordsRequest(
    customer_id="<customer_id>",    # optional: filter by customer
    operation_type=None,
    operation_time_begin=None,
    operation_time_end=None,
    offset=0, limit=10
)
resp = client.list_partner_adjust_records(req)
for r in resp.records:
    print(r.customer_id, r.operation_type, r.amount, r.operation_time)
```

## indirect_partner

| Operation | Purpose | Required | Note |
| --- | --- | --- | --- |
| `BssClient.list_indirect_partners` | 云经销商（二级经销商）列表 | - | body `QueryIndirectPartnersReq` |

#### `list_indirect_partners`

```python
from huaweicloudsdkbss.v2 import ListIndirectPartnersRequest
from huaweicloudsdkbss.v2.model import QueryIndirectPartnersReq

req = ListIndirectPartnersRequest(
    body=QueryIndirectPartnersReq(account_name=None, offset=0, limit=10)
)
resp = client.list_indirect_partners(req)
for p in resp.indirect_partners:
    print(p.indirect_partner_id, p.account_name, p.associated_on)
```

## coupon_quota

| Operation | Purpose | Required | Note |
| --- | --- | --- | --- |
| `BssClient.list_quota_coupons` | 伙伴自身代金券额度 | - | body `QueryCouponQuotasReqExt`; `quota_type` 0=代金券 1=现金券 |
| `BssClient.list_issued_coupon_quotas` | 已发放给经销商的代金券额度 | - | GET; `indirect_partner_id` filter |
| `BssClient.list_coupon_quotas_records` | 代金券额度发放/回收操作记录 | - | GET; `operation_time_begin/end` |

#### `list_quota_coupons`

```python
from huaweicloudsdkbss.v2 import ListQuotaCouponsRequest
from huaweicloudsdkbss.v2.model import QueryCouponQuotasReqExt

req = ListQuotaCouponsRequest(
    body=QueryCouponQuotasReqExt(quota_type=0, offset=0, limit=10)
)
resp = client.list_quota_coupons(req)
for q in resp.quotas:
    print(q.quota_id, q.quota_status, q.balance, q.quota_value)
```

#### `list_issued_coupon_quotas`

```python
from huaweicloudsdkbss.v2 import ListIssuedCouponQuotasRequest

req = ListIssuedCouponQuotasRequest(indirect_partner_id=None, limit=10)
resp = client.list_issued_coupon_quotas(req)
for q in resp.quotas:
    print(q.quota_id, q.indirect_partner_id, q.balance)
```

#### `list_coupon_quotas_records`

```python
from huaweicloudsdkbss.v2 import ListCouponQuotasRecordsRequest

req = ListCouponQuotasRecordsRequest(
    indirect_partner_id=None,
    operation_time_begin="2026-08-01T00:00:00Z",
    operation_time_end="2026-08-31T23:59:59Z",
    limit=10
)
resp = client.list_coupon_quotas_records(req)
for r in resp.records:
    print(r.operation_type, r.quota_id, r.amount)
```

## coupon_issue

| Operation | Purpose | Required | Note |
| --- | --- | --- | --- |
| `BssClient.list_sub_customer_coupons` | 伙伴自身优惠券列表 | - | GET; `status` 1=未激活 2=可使用 3=已使用 4=已过期 |
| `BssClient.list_issued_partner_coupons` | 已发放给客户的优惠券 | - | GET; `customer_id` filter |
| `BssClient.list_partner_coupons_record` | 优惠券发放/回收记录 | - | GET; `operation_time_begin/end` |

#### `list_sub_customer_coupons`

```python
from huaweicloudsdkbss.v2 import ListSubCustomerCouponsRequest

req = ListSubCustomerCouponsRequest(status=None, offset=0, limit=10)
resp = client.list_sub_customer_coupons(req)
for c in resp.user_coupons:
    print(c.coupon_id, c.status, c.face_value, c.valid_time, c.expire_time)
```

#### `list_issued_partner_coupons`

```python
from huaweicloudsdkbss.v2 import ListIssuedPartnerCouponsRequest

req = ListIssuedPartnerCouponsRequest(customer_id="<customer_id>", status=None, limit=10)
resp = client.list_issued_partner_coupons(req)
for c in resp.user_coupons:
    print(c.coupon_id, c.customer_id, c.face_value, c.status)
```

#### `list_partner_coupons_record`

```python
from huaweicloudsdkbss.v2 import ListPartnerCouponsRecordRequest

req = ListPartnerCouponsRecordRequest(
    operation_time_begin="2026-08-01T00:00:00Z",
    operation_time_end="2026-08-31T23:59:59Z",
    limit=10
)
resp = client.list_partner_coupons_record(req)
for r in resp.records:
    print(r.operation_type, r.coupon_id, r.operation_amount, r.operation_time)
```

## customer_bill

| Operation | Purpose | Required | Note |
| --- | --- | --- | --- |
| `BssClient.list_consume_sub_customers` | 有消费的子客户列表 | `bill_cycle` | body `ListConsumeSubCustomersReq`; ranking basis |
| `BssClient.list_sub_customer_bill_detail` | 子客户消费明细（18个月） | `bill_cycle` | GET; `customer_id`, `bill_date_begin/end` filters |
| `BssClient.list_subcustomer_monthly_bills` | 子客户月度消费汇总 | - | GET; `cycle`; `charge_mode` 1=包年/包月 2=按需 |

#### `list_consume_sub_customers`

```python
from huaweicloudsdkbss.v2 import ListConsumeSubCustomersRequest
from huaweicloudsdkbss.v2.model import ListConsumeSubCustomersReq

req = ListConsumeSubCustomersRequest(
    body=ListConsumeSubCustomersReq(bill_cycle="2026-08", offset=0, limit=10)
)
resp = client.list_consume_sub_customers(req)
for c in resp.sub_customers:
    print(c.customer_id)
```

#### `list_sub_customer_bill_detail`

```python
from huaweicloudsdkbss.v2 import ListSubCustomerBillDetailRequest

req = ListSubCustomerBillDetailRequest(
    bill_cycle="2026-08",
    customer_id="<customer_id>",   # optional filter
    offset=0, limit=10
)
resp = client.list_sub_customer_bill_detail(req)
# resp.fee_records: [ {customer_id, resource_id, resource_name,
#                      payment_amount, official_amount, official_discount_amount} ]
```

#### `list_subcustomer_monthly_bills`

```python
from huaweicloudsdkbss.v2 import ListSubcustomerMonthlyBillsRequest

req = ListSubcustomerMonthlyBillsRequest(
    customer_id="<customer_id>",   # optional; omit for all sub-customers
    cycle="2026-08",
    charge_mode=None,              # 1=包年/包月 2=按需
    limit=10
)
resp = client.list_subcustomer_monthly_bills(req)
# resp.bill_sums: [ {customer_id, bill_type, charge_mode, amount, debt_amount} ]
```

## customer_resource

| Operation | Purpose | Required | Note |
| --- | --- | --- | --- |
| `BssClient.list_pay_per_use_customer_resources` | 客户包年包月资源 | - | body `QueryResourcesReq`; `customer_id` required to query sub-customer resources; `expire_time_begin/end` |
| `BssClient.list_customer_on_demand_resources` | 客户按需资源 | `customer_id` | body `QueryCustomerOnDemandResourcesReq`; `status` |
| `BssClient.list_free_resource_infos` | 资源包列表（需权限） | - | body `ListFreeResourceInfosReq`; `status` 0=未生效 1=生效中 2=已用完 |

#### `list_pay_per_use_customer_resources`

```python
from huaweicloudsdkbss.v2 import ListPayPerUseCustomerResourcesRequest
from huaweicloudsdkbss.v2.model import QueryResourcesReq

req = ListPayPerUseCustomerResourcesRequest(
    body=QueryResourcesReq(
        customer_id="<customer_id>",   # required for sub-customer query
        status_list=[2],               # 2=使用中 3=已关闭 4=已冻结 5=已过期
        expire_time_begin=None,        # e.g. 2026-09-30T00:00:00Z
        expire_time_end=None,
        limit=10
    )
)
resp = client.list_pay_per_use_customer_resources(req)
# resp.data: [ {resource_id, resource_name, status, expire_time} ]
```

#### `list_customer_on_demand_resources`

```python
from huaweicloudsdkbss.v2 import ListCustomerOnDemandResourcesRequest
from huaweicloudsdkbss.v2.model import QueryCustomerOnDemandResourcesReq

req = ListCustomerOnDemandResourcesRequest(
    body=QueryCustomerOnDemandResourcesReq(
        customer_id="<customer_id>",   # required
        status=None,                   # 1=正常 6=已关闭
        limit=10
    )
)
resp = client.list_customer_on_demand_resources(req)
# resp.resources: [ {resource_id, resource_name, status, region_code} ]
```

#### `list_free_resource_infos`

```python
from huaweicloudsdkbss.v2 import ListFreeResourceInfosRequest
from huaweicloudsdkbss.v2.model import ListFreeResourceInfosReq

req = ListFreeResourceInfosRequest(
    body=ListFreeResourceInfosReq(status=1, offset=0, limit=10)  # 1=生效中
)
resp = client.list_free_resource_infos(req)
# resp.free_resource_packages: [ {order_instance_id, product_name, status, free_resources} ]
```

## customer_order

| Operation | Purpose | Required | Note |
| --- | --- | --- | --- |
| `BssClient.list_customer_orders` | 客户订单列表 | - | GET; `customer_id`, `status`, `create_time_begin/end` |
| `BssClient.show_customer_order_details` | 订单详情 | `order_id` | GET; `order_id` is a path parameter |
| `BssClient.show_refund_order_details` | 退款详情 | - | GET; `order_id`/`customer_id` filters |

#### `list_customer_orders`

```python
from huaweicloudsdkbss.v2 import ListCustomerOrdersRequest

req = ListCustomerOrdersRequest(
    customer_id="<customer_id>",   # optional filter
    status=None,                   # order status filter
    create_time_begin=None,
    create_time_end=None,
    order_by=None,                 # "orderCreateTime" etc.
    limit=10, offset=0
)
resp = client.list_customer_orders(req)
for o in resp.order_infos:
    print(o.order_id, o.customer_id, o.amount_after_discount, o.status, o.create_time)
```

#### `show_customer_order_details`

```python
from huaweicloudsdkbss.v2 import ShowCustomerOrderDetailsRequest

req = ShowCustomerOrderDetailsRequest(
    order_id="<order_id>",         # required path parameter
    limit=10, offset=0
)
resp = client.show_customer_order_details(req)
# resp.order_info + resp.order_line_items: [ {order_line_item_id, amount, ...} ]
```

#### `show_refund_order_details`

```python
from huaweicloudsdkbss.v2 import ShowRefundOrderDetailsRequest

req = ShowRefundOrderDetailsRequest(
    order_id="<order_id>",         # optional filter
    customer_id=None,              # optional filter
    indirect_partner_id=None
)
resp = client.show_refund_order_details(req)
for r in resp.refund_infos:
    print(r.base_order_id, r.customer_id, r.amount)
```

## reference_dictionary

| Operation | Purpose | Note |
| --- | --- | --- |
| `BssClient.list_service_types` | 云服务类型字典 | GET; `service_type_name` fuzzy filter; limit ≤ 200 |
| `BssClient.list_resource_types` | 资源类型字典 | GET |
| `BssClient.list_usage_types` | 使用量类型字典 | GET; `resource_type_code` filter |
| `BssClient.list_measure_units` | 计量单位字典 | GET |
| `BssClient.list_conversions` | 单位换算 | GET; `measure_type` filter |
| `BssClient.list_provinces` | 省份字典 | GET |
| `BssClient.list_cities` | 城市字典 | GET; `province_code` required |
| `BssClient.list_counties` | 区县字典 | GET; `city_code` required |

#### `list_service_types`

```python
from huaweicloudsdkbss.v2 import ListServiceTypesRequest

resp = client.list_service_types(ListServiceTypesRequest(service_type_name=None, limit=10))
for s in resp.service_types:
    print(s.service_type_code, s.service_type_name)
```

## Error Interception

| Error | Meaning | Action |
| --- | --- | --- |
| `domain_id has no access to this api` | Account has no partner access | **Stop immediately**, tell the user the account is not a partner (解决方案提供商/总经销商) |
| `CBC.0151` (access denied) | Insufficient permission | Tell the user permission is insufficient; no retry loop |
| `NETWORK_ERROR` / connection timeout | Network blocked | Suggest setting `HTTPS_PROXY` (corporate intranet) and retry once |
| `CBC.80021021` | Query span exceeds 1 year | Normal guard; narrow the time range |
| HTTP 400 on `list_sub_customer_coupons` and other coupon queries | `limit` > 100 | BSS limit max is **100** (not 200); retry with `limit<=100` |
| `CBC.99000035` | AK/SK invalid | Check credentials/profile |

## Pagination and Limits

- `offset` starts at 0; `limit` default 10, **max 100** for BSS list APIs.
- Batch body queries (`list_customers_balances_detail`): max 100 `customer_infos` per call.
- `list_pay_per_use_customer_resources`: max 50 `resource_ids` per call.
- Always paginate with `offset += len(page)` until fewer than `limit` rows returned.