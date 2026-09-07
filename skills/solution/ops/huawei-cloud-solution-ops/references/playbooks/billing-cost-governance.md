# Billing Cost Governance

Use this playbook when the user asks for billing, cost analysis, chargeback, resource fee records, or cost-governance evidence.

## Inputs

- Billing cycle, for example `YYYY-MM`.
- Cost analysis begin/end time and grouping dimension.
- Enterprise project, service type, resource type, region, or resource ID filters when available.
- Permission scope for billing and cost data.
- Money basis: billed, paid, outstanding, amortized, or not applicable.
- Account scope: current account, enterprise master/sub-customer, partner/resale customer, or dictionary/reference query.

## Read-Only Flow

1. Use `hcloud_billing_readonly.py` to generate official Billing/Cost request specs and reviewed hcloud command plans.
2. For monthly summaries, plan `ShowCustomerMonthlySum` with an explicit billing cycle.
3. For cost analysis, plan `ListCosts` with a bounded time window and grouping dimension.
4. For resource details, plan `ListCustomerselfResourceRecordDetails` or `ListCustomerselfResourceRecords` with cycle and scope filters.
5. For reconciliation, prefer the minimal read-only sequence:
   - `ListCustomerBillsFeeRecords` for billing-period transaction evidence.
   - `ListCustomerselfResourceRecordDetails` for same-cycle resource detail evidence.
   - `ListCustomerOrders` / `ShowCustomerOrderDetails` only when order-side evidence is needed.
   Do not replace this path with `ShowCustomerMonthlySum`; monthly summary is a different fact and grain.
6. For balance, debt, account transactions, resource packages, coupons, stored-value cards, orders, enterprise/sub-customer, partner, or reference-dictionary questions, use the matching `hcloud_billing_readonly.py --operation ...` planner and keep the scope narrow.
7. Execute only `hcloud_command_plan.safe_exec_command` after the user approves live billing access, account scope, time range, and output handling. BSS hcloud command templates must use `--cli-region=cn-north-1`; let the planner add `X-Language` only when `operation_capabilities.x_language_header=true`.
8. Summarize saved safe_exec output with `hcloud_billing_result_summarize.py` before showing data to the user. Use `--include-redacted-records` only when row-level evidence is needed and the scope is confirmed.

## BSS Command Contract

- `hcloud` service name is always `BSS`; do not invent `account`, `bill`, `cost`, or `billing` service names.
- BSS commands use fixed `--cli-region=cn-north-1` and `--cli-output=json`.
- `cli-lang` is a KooCLI profile setting, not a BSS operation argument. Do not put it in generated API commands.
- `X-Language` is operation-specific. Pass `zh_CN` or `en_US` only when the selected operation exposes that Header; omit it otherwise.
- For POST-style KooCLI parameters, use dot notation instead of JSON strings:
  - `--time_condition.begin_time=YYYY-MM-DD`
  - `--groupby.1.key=CLOUD_SERVICE_TYPE`
  - `--filters.1.filter_factor.key=ENTERPRISE_PROJECT_ID`
  - `--filters.1.filter_factor.value.1=<enterprise_project_id>`
- For arrays, use one-based indexes such as `--resource_ids.1=<id>` and `--free_resource_ids.1=<id>`.
- `ListCosts` enterprise-project filtering uses `ENTERPRISE_PROJECT_ID`, not `ENTERPRISE_PROJECT`.
- `ShowCustomerMonthlySum` cannot answer enterprise-project ranking. Use `ListCosts` with the enterprise-project filter instead.
- Operation names containing `Change` can still be read-only ledger operations when they are `List*` or `Show*`; classify by operation contract, not by English word alone.
- Default to small pages. A single page is partial until `total_count`, `offset`, `limit`, and intended pages have been checked.

## Semantic Discipline

Every billing answer must identify the tuple `fact × grain × money_basis × scope/billing_period` before calculating totals, comparisons, or rankings.

- `fact`: the source fact, such as monthly summary, cost analysis, resource fee record, resource detail, order, refund, balance, or coupon.
- `grain`: the row level, such as billing cycle × service, resource detail row, daily cost bucket, order row, or point-in-time balance.
- `money_basis`: billed, paid, outstanding, amortized, or not applicable. Do not mix these bases in one total.
- `scope`: account, enterprise project, sub-customer, cloud service, resource type, region, resource ID, or other filters.
- `billing_period`: bill cycle, date range, point-in-time, or not applicable.

Do not add monthly summary, resource detail, amortized cost, orders, refunds, and coupon deductions as if they were the same fact. If two outputs use different `fact`, `grain`, `money_basis`, `scope`, or `billing_period`, present them as separate evidence and explain the relationship instead of forcing one number.

Money basis field hints:

- `billed`: `consume_amount`, `official_amount`, `discount_amount`
- `paid`: `cash_amount`, `credit_amount`, `coupon_amount`, `stored_value_card_amount`
- `outstanding`: `debt_amount`
- `amortized`: `amortized_cost`

Common fact boundaries:

- `ShowCustomerAccountBalances`: account point-in-time balance/debt; not charge attribution.
- `ShowCustomerMonthlySum`: billing-cycle summary; not row-level details, not enterprise-project ranking.
- `ListCustomerBillsFeeRecords`: transaction statement evidence; not current resource existence.
- `ListCustomerselfResourceRecordDetails`: resource bill/detail rows; row sums can differ from summary due to precision and scope.
- `ListCustomerBillsMonthlyBreakDown`: amortized basis; do not mix with current-month cash payment totals.
- `ListFreeResourceInfos` / `ListFreeResourceUsages` / `ListFreeResourcesUsageRecords`: package entitlement, remaining quota, and deduction evidence; link them to bill rows before explaining charges.
- `ListCustomerOrders` / `ShowCustomerOrderDetails` / `ShowRefundOrderDetails`: order-side evidence; do not execute payment, unsubscribe, renewal, or refund.
- Enterprise and partner interfaces require confirmed scope and authorization. Permission failure means “not authorized or not applicable”, not “no billing data exists”.

## Product-Side Cross-Validation

BSS is the billing fact source. Product APIs only answer whether a resource can currently be found, what state it is in now, or whether a related service object still exists.

- A product `List*`/`Show*` miss does not invalidate historical billing. Possible causes include deleted resources, delayed billing, sub-resources, shared bandwidth, snapshots/backups, Marketplace items, enterprise project aggregation gaps, or sub-customer scope.
- Query product-side resources only after BSS has produced a service/resource clue. Do not start cost attribution from resource inventory and then infer spend.
- When product-side verification is missing, say “billing evidence exists, current resource evidence not yet verified” instead of judging the bill wrong.

## Guardrails

- The bundled planner does not sign requests, accept credentials, send HTTP traffic, or execute hcloud by default.
- Billing and cost data can expose account, resource, and spend-sensitive fields.
- Do not infer cost from resource inventory when billing APIs are unavailable.
- Summarize counts, totals, filters, and major drivers before sharing raw records.
- A single page is partial. Do not claim full-account totals or complete rankings until `total_count`, `offset`, `limit`, and all intended pages have been reviewed.
- Protected identifiers such as account, customer, resource, order, transaction, coupon, quota, and card IDs must be redacted or hashed before display.
- Refuse write-side billing actions from this flow: payment, renewal, refund, unsubscribe, recovery, create/update/delete, verification-code sending, balance transfer, coupon issuance/recovery, or resource mutation.
- If the user asks for pricing or renewal quotes, route it as planning/estimation, not as historical billing evidence. Do not mix quotes with actual bill facts.

## Promotion Gaps

- Collect read-only smoke evidence for safe BSS metadata-backed query shapes.
- Document freshness, permission, and enterprise-project scope limits for each supported request type.
