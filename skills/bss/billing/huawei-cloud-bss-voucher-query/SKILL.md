---
name: huawei-cloud-bss-voucher-query
description: |
  Query Huawei Cloud BSS (费用中心) vouchers / coupons with enterprise-project
  (企业项目) filtering. Reads the account's coupon list via KooCLI
  `hcloud BSS ListSubCustomerCoupons` (read-only GET /v2/promotions/benefits/coupons,
  with SDK fallback). Supports listing by project ID (`--project-id`, attributed
  through the customer order => enterprise-project linkage because the coupon API
  carries no project_id), status (`--status available/used/expired`), name,
  coupon-id, coupon-type, near-expiry/expired views (`--expiring` / `--expired`)
  and a per-project usage-rate analysis (`--usage-analysis`). Strictly read-only.
  Triggers include: "代金券盘点", "按项目查询代金券", "企业项目代金券", "查询代金券",
  "优惠券列表", "按项目ID筛选代金券", "代金券到期", "代金券使用率", "代金券余额",
  "费用管理", "list BSS coupons", "query vouchers by project", "coupon inventory",
  "voucher list by enterprise project", "enterprise project voucher query",
  "billing voucher query", "华为云代金券".
tags: [huawei-cloud, bss, billing, voucher, readonly]
---

# Huawei Cloud BSS Voucher Query (Enterprise-Project Aware)

## Overview

Query the voucher / coupon list of a Huawei Cloud account through KooCLI
`hcloud BSS ListSubCustomerCoupons` (official read-only GET
`/v2/promotions/benefits/coupons`, verified in the `huaweicloudsdkbss` v2
client `_list_sub_customer_coupons_http_info` metadata; the SDK fallback uses
`GlobalCredentials` + global BSS endpoint). The skill adds an **enterprise
project (企业项目) dimension** to voucher queries so multi-project users can
filter vouchers by project, track near-expiry/expired vouchers per project, and
see a per-project usage-rate summary for financial apportionment
(财务分摊/对账) and reconciliation.

### Capability Scope

- **List vouchers** (full-field table / `--json` / `--names-only`) with
  automatic offset paging (BSS page limit 100) and a strict write-intent guard
  (read-only).
- **Filter by enterprise project** — `--project-id <id>`. New capability of
  this skill: the BSS coupon-list API carries **no** `project_id` request
  parameter and **no** project field in its coupon records (it is a global /
  domain API). The script therefore attributes each coupon to an enterprise
  project through the **customer order linkage** (`coupon.order_id /
  lock_order_id` → `hcloud BSS ListCustomerOrders` →
  `order.enterprise_projects[]`), then filters locally — the same client-side
  strategy as the `--name` filter. This is a read-only enhancement built on the
  existing `huawei-cloud-voucher-list` query logic.
- **Filter by status / name / coupon-id / coupon-type** — `--status` (BSS
  codes 1-5 or aliases `available`/`used`/`expired`/`reclaimed`), `--name`
  (client-side substring), `--coupon-id` (server-side), `--coupon-type`
  (server-side). `--status` and `--project-id` compose.
- **Near-expiry / expired views** — `--expiring N` (expiring within N days) and
  `--expired` (already expired), based on `valid_time` / `expire_time`,
  combinable with `--project-id`.
- **Per-project usage-rate analysis** — `--usage-analysis` aggregates
  `face_value` vs `balance` per enterprise project (count / total face / total
  balance / total used / usage rate) for finance apportionment and
  reconciliation.

### Out of Scope

Every mutating BSS operation (create / reclaim / transfer / adjust coupon
quotas, claim / send / freeze / cancel coupons). The write-intent guard rejects
those before any command is executed.

## Prerequisites

1. **KooCLI (`hcloud`) installed** — see
   [references/cli-installation-guide.md](references/cli-installation-guide.md).
   Alternative: `pip install huaweicloudsdkcore huaweicloudsdkbss` for the SDK
   fallback path.
2. **Active credential profile** — configure credentials out-of-band
   (KooCLI configure in your terminal, or credential environment variables).
   Never paste AK/SK into chat; the script never reads, echoes, or stores
   secrets itself — authentication is delegated entirely to the hcloud profile
   / SDK environment.
3. **IAM permission** — read-only `bss:coupon:list`; add `bss:order:view` when
   using `--project-id` / `--usage-analysis` (order linkage). Least-privilege
   policy in [references/iam-policies.md](references/iam-policies.md).
4. **Python 3.8+** (standard library only — argparse / json / subprocess).
5. **Outbound HTTPS** access to `bss.myhuaweicloud.com`.
6. **Region** — BSS is a global service; `cn-north-1` is the default.

> **Data-availability note:** the coupon-list API (`ListSubCustomerCoupons`)
> response carries no per-coupon enterprise project. Project attribution is
> derived client-side from the coupon's order linkage. Coupons with **no**
> attributable order (e.g. never-used vouchers) keep `project_id = "-"` and are
> excluded when `--project-id` is given; use `--usage-analysis` (without a
> project filter) to see every project bucket including unattributed ("-").

## Workflow

1. **Confirm the target region** (default `cn-north-1`; BSS is global).
2. **Optionally confirm KooCLI readiness** (read-only): check the active
   credential profile is configured for BSS.
3. **Run the list script** with the desired output mode, filters, and — when a
   project dimension is needed — `--project-id`, `--expiring`, `--expired`,
   and/or `--usage-analysis`.
4. **Read the result** — table for humans, `--json` for downstream tooling,
   `--names-only` for a compact inventory, usage table for per-project stats.
5. **Handle empty / error cases** per the Error Handling table below (explicit
   hints for empty region, 403, missing AK/SK, write-intent guard).

## Core Commands

```bash
# Full-field table (default)
python3 scripts/list_coupons.py --region cn-north-1

# Raw JSON of every returned field
python3 scripts/list_coupons.py --json

# Compact voucher (plan-name) list only
python3 scripts/list_coupons.py --names-only

# Filter by enterprise project (client-side, via order linkage)
python3 scripts/list_coupons.py --project-id {project_id}

# Filter by enterprise project + voucher status (composable)
python3 scripts/list_coupons.py --project-id {project_id} --status available

# Vouchers expiring within 30 days (optionally per project)
python3 scripts/list_coupons.py --expiring 30
python3 scripts/list_coupons.py --expiring 30 --project-id {project_id}

# Already-expired vouchers
python3 scripts/list_coupons.py --expired

# Per-project usage-rate analysis (face value vs balance)
python3 scripts/list_coupons.py --usage-analysis
python3 scripts/list_coupons.py --usage-analysis --project-id {project_id}

# Other filters
python3 scripts/list_coupons.py --status used --names-only
python3 scripts/list_coupons.py --coupon-id {coupon_id}
python3 scripts/list_coupons.py --name spring
python3 scripts/list_coupons.py --coupon-type 1
```

Equivalent direct KooCLI command (the script wraps exactly this call, with
paging — **no** `enterprise_project_id` parameter exists on the coupon API):

```bash
hcloud BSS ListSubCustomerCoupons --cli-region=cn-north-1 --offset=0 --limit=100
```

> Project filtering is **client-side**: the script first fetches the full
> paged coupon list, resolves each coupon's enterprise projects through
> `hcloud BSS ListCustomerOrders` (`GET /v2/orders/customer-orders`,
> read-only) using the coupon's `order_id` / `lock_order_id`, then filters
> locally. It never sends an invented server-side project parameter.

## Parameter Confirmation

| Parameter | Required | Description | Example |
| ----------- | ---------- | ------------- | --------- |
| `--region` / `-r` | No | Huawei Cloud region (default `cn-north-1`; BSS is global) | `cn-north-1` |
| `--json` | No | Output the raw voucher array as JSON | — |
| `--names-only` | No | Output voucher (plan) names only | — |
| `--status` | No | Filter by voucher status: `1` unactivated, `2` available, `3` used, `4` expired, `5` reclaimed — numeric codes or aliases (`available` / `used` / `expired` / `reclaimed` …); recognized values forwarded server-side, others filtered client-side | `available`, `2` |
| `--name` | No | Filter by promotion plan name / coupon code — **client-side** (API has no name parameter) | `spring` |
| `--coupon-id` | No | Filter by exact voucher ID (server-side query parameter) | `CP0001` |
| `--coupon-type` | No | Filter by coupon type: `1` voucher, `2` discount, `3` product, `4` cash (server-side) | `1` |
| `--project-id` | No | Filter by enterprise project ID — **client-side via order linkage**; needs `bss:order:view` | `proj-abc123` |
| `--expiring DAYS` | No | List vouchers expiring within DAYS days (not yet expired) | `30` |
| `--expired` | No | List already-expired vouchers | — |
| `--usage-analysis` | No | Per-project usage-rate summary (count / face / balance / used / rate) | — |
| `--page-size` | No | Page size for the coupon list (BSS maximum 100; default 100) | `100` |
| `--operation` | No | hcloud BSS operation name; only the read-only `ListSubCustomerCoupons` (alias `ListCoupons`) is allowed | `ListSubCustomerCoupons` |

Output-mode precedence: `--usage-analysis` → `--names-only` → `--json` → table (default).

## Write-Intent Guard

- The script scans all user arguments plus the `--operation` value for mutating
  vocabulary (`create`, `delete`, `update`, `modify`, `reclaim`, `transfer`,
  `retrieve`, `adjust`, `send`, `freeze`, `cancel`, plus concrete BSS operation
  names `CreatePartnerCoupons`, `ReclaimPartnerCoupons`,
  `UpdateCouponQuotas`, `TransferEnterpriseMultiAccountCoupon`, …).
- Any hit raises `GuardError`, prints `[错误] 检测到写操作意图 ... 已被守卫拦截`, and
  exits with code 1 **before** a single hcloud command is executed.
- Read-only status labels are **not** blocked (specific operation names are
  matched instead of generic verbs for `reclaim*`, so `--status reclaimed` and
  the project/status filters pass the guard).
- Only the read-only coupon list (GET) — or the SDK
  `list_sub_customer_coupons` in the fallback path — plus the read-only order
  lookup for project attribution (`ListCustomerOrders`, GET) are ever
  constructed by the script; there is no code path that can issue a mutating
  BSS API call.

## KooCLI Command Format Standard

```text
hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]
```

- **Service name** — exact KooCLI title-case service name: `BSS`.
- **Operation name** — PascalCase: `ListSubCustomerCoupons`; project
  attribution uses the read-only `ListCustomerOrders`.
- **Region parameter** — `--cli-region=<value>`, e.g. `--cli-region=cn-north-1`
  (required for every concrete BSS call; BSS is global).
- **Simple parameter** — `--key=value`, e.g. `--limit=100`, `--offset=20`,
  `--coupon_id=CP0001`, `--status=2`.
- **REST paths (official SDK `_http_info`)** —
  `GET /v2/promotions/benefits/coupons` (`huaweicloudsdkbss` v2
  `_list_sub_customer_coupons_http_info`; the request carries **no** project_id
  — it is a global/domain API) and
  `GET /v2/orders/customer-orders` (`_list_customer_orders_http_info`), which
  returns each order's `enterprise_projects` for project attribution.

## Error Handling

| Scenario | Behavior |
| ---------- | --------- |
| Empty voucher list | Exit 0, prints `当前区域（<x>）无 BSS 代金券` (+ active filters) |
| 403 / insufficient IAM permission | Exit 1, `无权限访问 BSS 代金券，请检查 IAM 权限` hint |
| Missing / invalid AK-SK | Exit 1, explicit hint to configure credentials out-of-band (never in chat) |
| `--project-id` given but order lookup forbidden | Orders skipped gracefully; coupons without attributable order keep `project_id "-"` and the filter result reflects only attributable vouchers |
| hcloud not installed | Exit 1 after SDK fallback also unavailable, hint to install KooCLI or the SDK packages |
| Network / API failure | Exit 1 with the hcloud stderr excerpt |
| KooCLI usage error (`[USE_ERROR] ...` with rc=0) | Exit 1, explicit hcloud 参数错误 hint pointing to `hcloud BSS ListSubCustomerCoupons --help` |
| Write intent detected | Exit 1, `GuardError` message, no command executed |

Exit codes: `0` success / empty region; `1` config, auth, guard, or API error.

## Edge Cases

| Scenario | Handling |
| ---------- | --------- |
| `--status` numeric / alias | Forwarded server-side as the numeric BSS status code (1-5); displayed with a human-readable label |
| `--status` unrecognised text | Applied client-side on the rendered status label (case-insensitive) |
| `--name` filter | Applied client-side after the full paged list is fetched (API has no name parameter) |
| `--project-id` filter | Applied client-side: coupon records carry no project_id, so each coupon is attributed to the enterprise projects of its `order_id` / `lock_order_id` via `ListCustomerOrders`; only the order actually matching the queried order_id is used (prevents cross-attribution) |
| Coupon with no order linkage | `project_id` / `project_name` default to `"-"`; excluded when `--project-id` is given |
| Large voucher count | Automatic `offset` paging (count-aware, full-page fallback, max 100 pages, page size capped at 100) |
| Extra response fields | Table columns are built from the union of returned fields — new fields appear automatically |
| Field missing on a voucher | Rendered as `-` in the table |
| Nested `use_limits` | Flattened into a `useLimits` JSON column for the table |
| Non-JSON hcloud output | `ApiError` with the raw excerpt (first 200 chars) |
| hcloud absent, SDK installed | Transparent fallback to `huaweicloudsdkbss` `list_sub_customer_coupons` (GlobalCredentials + global endpoint), same output modes |
| User asks to create/reclaim/transfer coupons | Out of scope — blocked by the write-intent guard |

## Testing

Offline unit tests with a mocked hcloud subprocess (no credentials, no network)
were authored and executed during skill development (36/36 passing), covering
every code path, then removed from the packaged skill per the Huawei Cloud
skill specification's Phase-6 cleanup. To re-run them during maintenance, restore
the test module next to the script and run:

```bash
python3 -m unittest discover -s tests -v
```

Coverage: write-intent guard, `--status` parsing, command construction (no
invented server-side project parameter is ever sent), JSON extraction, failure
classification, server-side status forwarding, client-side name / status /
project filtering, order-based project attribution (matching order id,
unattributed fallback), usage analysis aggregation (per project and
unattributed), expiry filtering (near-expiry / expired), renderers, SDK
fallback failure handling, and main() output modes.

## Reference Documents

| Document | Content |
| ---------- | --------- |
| [references/iam-policies.md](references/iam-policies.md) | Least-privilege read-only IAM policy (`bss:coupon:list`, `bss:order:view`) |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | KooCLI installation and credential configuration |
| [references/verification-method.md](references/verification-method.md) | How the skill and its tests were verified |
| [references/dataflow-diagram.md](references/dataflow-diagram.md) | Mermaid data flow diagram |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria checklist |