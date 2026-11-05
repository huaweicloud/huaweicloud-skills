# Verification Method

## What was verified

The `huawei-cloud-bss-voucher-query` skill was developed and verified offline
(mocked hcloud subprocess — no credentials, no live network). The execution
path and API reality were also checked against the vendored `huaweicloudsdkbss`
v2 models and the KooCLI `bss` metaOrigin metadata.

Key API facts confirmed from trusted sources (SDK `_http_info` and KooCLI
metaOrigin, not inference):

- `ListSubCustomerCoupons` → `GET /v2/promotions/benefits/coupons`.
- The coupon-list **request** has no `enterprise_project_id` parameter
  (params: `coupon_id`, `order_id`, `promotion_plan_id`, `coupon_type`,
  `status`, `active_start_time`, `active_end_time`, `offset`, `limit`,
  `source_id`, `indirect_partner_id`).
- The coupon-list **response record** has no project field.
- `ListCustomerOrders` → `GET /v2/orders/customer-orders`, read-only, and each
  order carries `enterprise_projects` (`[{id, name}]`) — the attribution source
  for `--project-id`.

## Test commands (offline, run during development)

```bash
# Unit tests (mocked hcloud, no network)
python3 -m unittest discover -s tests -v
```

Test coverage: write-intent guard, status parsing, command construction (no
invented server-side project parameter), JSON extraction, failure
classification (missing AK/SK / 403 / usage error / generic), server-side
status forwarding, client-side name/status/project filtering, order-based
project attribution (matching order id only; unattributed -> "-"), usage
analysis aggregation (per project + unattributed), expiry filtering, table/json
/names-only renderers, SDK fallback handling, and main() modes.

## Manual smoke commands (require credentials)

```bash
python3 scripts/list_coupons.py --names-only
python3 scripts/list_coupons.py --usage-analysis
python3 scripts/list_coupons.py --project-id <enterprise_project_id>
python3 scripts/list_coupons.py --status available --expiring 30
```

## Result

- Offline unit tests: **36/36 PASS**.
- Live execution was not possible in the sandbox (no BSS credentials / no
  routed BSS hcloud service); the error paths and SDK fallback degrade
  gracefully with explicit hints. Functional verification relies on the mocked
  unit tests above and the verified API metadata.