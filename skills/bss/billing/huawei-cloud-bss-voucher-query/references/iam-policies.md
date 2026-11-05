# IAM Policies (least privilege, read-only)

The skill invokes two read-only Huawei Cloud OpenAPI operations (via KooCLI,
with an SDK fallback for the main list):

- `GET /v2/promotions/benefits/coupons` —
  `hcloud BSS ListSubCustomerCoupons`
- `GET /v2/orders/customer-orders` —
  `hcloud BSS ListCustomerOrders` (only for `--project-id` / `--usage-analysis`
  order-based project attribution)

## Required IAM actions

| Action | API | Purpose |
| -------- | ----- | ------- |
| `bss:coupon:list` | GET /v2/promotions/benefits/coupons | List BSS vouchers / coupons |
| `bss:order:view` | GET /v2/orders/customer-orders | Resolve a coupon's enterprise projects via its order linkage (only needed for project filtering / usage analysis) |

`bss:coupon:list` is the read-only action for the BSS coupon-list API;
`bss:order:view` is the read-only action for customer orders. If your account
uses system policies, assign the corresponding **BSS ReadOnly** policy of your
IAM domain instead of the custom policy below. Verify the exact action / policy
name in the IAM console (权限及授权项说明) before production use.

## Custom least-privilege policy (IAM 5.0)

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bss:coupon:list",
        "bss:order:view"
      ],
      "Resource": "*"
    }
  ]
}
```

> `bss:order:view` is only required when `--project-id` or `--usage-analysis`
> is used. Plain listing (no project dimension) needs only `bss:coupon:list`.

## 403 troubleshooting

If the script reports `无权限访问 BSS 代金券，请检查 IAM 权限（403）`:

1. Confirm the AK/SK belongs to a user / agency with BSS access.
2. Grant `bss:coupon:list` (custom policy above) or the domain's BSS read-only
   system policy; add `bss:order:view` for project-filtered queries.
3. Re-run `python3 scripts/list_coupons.py`.