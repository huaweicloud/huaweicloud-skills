# IAM Minimum Permissions

Objective: BSS billing read-only first; product resource read-only only for cross-validation "whether resources currently found in bills can still be queried".

IAM Actions vary by account type, site, and service version. This document provides permission design guidelines; before implementation, refer to
[IAM Permission Best Practices](https://support.huaweicloud.com/bestpractice-iam/iam_0426.html),
[API Explorer](https://console.huaweicloud.com/apiexplorer/#/openapi/overview)
and `hcloud <SERVICE> <Operation> --help`.

## Permission Layers

| Layer | Purpose | When Needed |
| --- | --- | --- |
| BSS Core Read-Only | Balance, bills, details, costs, orders, coupons, resource packages | Default required |
| Multi-Account Read-Only | Enterprise master/sub-account/associated account billing | When explicitly querying multi-account or enterprise allocation |
| Product Read-Only | Resource existence, status cross-validation | After BSS has located service and resource ID |

Do not add write permissions for payment, renewal, unsubscribe, recovery, create, update, delete, send verification code, transfer, etc.

## BSS Core Read-Only

| KooCLI Operation | Read Content |
| --- | --- |
| `ShowCustomerAccountBalances` | Balance, debt amount |
| `ShowCustomerMonthlySum` | Monthly summary bill |
| `ListCustomerBillsFeeRecords` | Consumption transaction bill |
| `ListCustomerselfResourceRecords` | Resource consumption records |
| `ListCustomerselfResourceRecordDetails` | Resource details, usage details |
| `ListCustomerBillsMonthlyBreakDown` | Monthly amortized cost |
| `ListCustomerAccountChangeRecords` | Cash/credit account transactions |
| `ListCustomerCouponChangeRecords` | Coupon transactions |
| `ListStoredValueCards` | Stored-value card list |
| `ListCustomerOrders` | Order list |
| `ShowCustomerOrderDetails` | Order details |
| `ShowRefundOrderDetails` | Unsubscribe/refund order evidence |
| `ListOrderCouponsByOrderId` | Order available coupons |
| `ListOrderDiscounts` | Order available discounts |
| `ListFreeResourceInfos` | Resource package list |
| `ListFreeResourceUsages` | Resource package remaining quota |
| `ListFreeResourcesUsageRecords` | Resource package deduction details |
| `ListCosts` | Cost analysis |
| `ListResourceUsageSummary` | CDN/OBS/IEC/VPC usage summary |
| `ListResourceUsage` | CDN/OBS/IEC/VPC resource usage details |
| `ListQuotaCoupons` | Partner coupon quota |
| `ListIssuedCouponQuotas` | Issued coupon quota |
| `ListCouponQuotasRecords` | Coupon quota operation records |
| `ListIssuedPartnerCoupons` | Issued coupons |
| `ListPartnerCouponsRecord` | Coupon issue/recovery records |
| `ListSubCustomerCoupons` | Partner own coupons |
| `ListServiceTypes` | Cloud service type dictionary |
| `ListResourceTypes` | Resource type dictionary |
| `ListUsageTypes` | Usage type dictionary |
| `ListMeasureUnits` | Measurement unit dictionary |
| `ListConversions` | Measurement unit conversion |
| `ListServiceResources` | Service to resource type relation |
| `ListProvinces` | Province dictionary |
| `ListCities` | City dictionary |
| `ListCounties` | District/county dictionary |

Policy skeleton (illustrative; before implementation, refer to actual Actions in IAM console/API Explorer):

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bss:*:get",
        "bss:*:list"
      ],
      "Resource": "*"
    }
  ]
}
```

If IAM does not accept wildcard read-only Actions, explicitly list query Actions according to actual API. Do not use write operations to supplement permissions.

## Multi-Account Read-Only

Only use when enterprise master/sub-account relationship and authorization are established; regular accounts may return 403. Partner/resale interfaces also require confirmation of authorization relationship and account scope; cannot automatically expand from current account to customer list.

| Operation | Purpose |
| --- | --- |
| `ListEnterpriseOrganizations` | Enterprise organization structure |
| `ListEnterpriseSubCustomers` | Enterprise sub-account list |
| `ListEnterpriseMultiAccount` | Enterprise sub-account recoverable balance; requires `balance_type`, `sub_customer_id` |
| `ShowMultiAccountTransferAmount` | Enterprise master transferable balance |
| `ListMultiAccountTransferCoupons` | Enterprise master transferable coupons |
| `ListMultiAccountRetrieveCoupons` | Enterprise sub-account recoverable coupons |
| `ListConsumeSubCustomers` | Sub-customers with consumption |
| `ListSubcustomerMonthlyBills` | Sub-customer monthly bills |
| `ListSubCustomerBillDetail` | Sub-customer bill details |
| `ListSubCustomers` | Partner customer list |
| `ListSubCustomerNewTag` | Customer new customer tag |
| `ListCustomerOnDemandResources` | Resale customer on-demand resources |
| `ListPayPerUseCustomerResources` | Annual/monthly package resources |
| `ListCustomersBalancesDetail` | Resale customer balance |
| `ListPartnerBalances` | Partner/reseller balance |
| `ListPartnerAccountChangeRecords` | Partner transaction records |
| `ListPartnerAdjustRecords` | Partner adjustment records |
| `ListIndirectPartners` | Secondary reseller list |

Financially independent sub-accounts, partners, and resale customers have additional constraints. When interface returns no permission, do not bypass or expand query.

## Product Read-Only

Product APIs are only used for cross-validation, not as billing fact source.

| Service | Read-Only Example |
| --- | --- |
| ECS | Cloud server List/Show |
| EVS | Cloud disk List/Show |
| EIP/VPC | Elastic IP, bandwidth, VPC, subnet List/Show |
| OBS | Bucket, usage, statistics query |
| CDN | Domain, traffic, bandwidth statistics query |
| RDS | Instance List/Show |
| DCS | Cache instance List/Show |
| LTS | Log group, log stream List/Show |
| CBR | Repository, backup List/Show |
| ELB/NAT | Load balancer, listener, NAT gateway List/Show |

If product API cannot find resource, it only indicates "current API did not find". Bill may still come from historical billing period, delayed billing, sub-resource, shared bandwidth, backup, snapshot, traffic, marketplace, or projects not supporting enterprise project aggregation.

## Permission Failure Handling

| Phenomenon | Handling |
| --- | --- |
| `403 Forbidden` | Record operation name, account scope, interface family; suggest supplementing minimum read-only permission |
| Sub-account data empty | Check enterprise master/sub-account authorization relationship and `method` parameter |
| Dictionary cannot find service name | Keep original code, prompt need to check official service type dictionary |
| Product resource not found | Return to BSS bill evidence, do not infer bill error |