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
  and a per-project usage-rate analysis (`--usage-analysis`). Report export
  (`--export xlsx,html`) writes the same result to a local four-sheet Excel
  workbook and/or a self-contained offline HTML report with charts, for finance
  apportionment and reconciliation. Strictly read-only.
  Triggers include: "代金券盘点", "按项目查询代金券", "企业项目代金券", "查询代金券",
  "优惠券列表", "按项目ID筛选代金券", "代金券到期", "代金券使用率", "代金券余额",
  "代金券报表", "代金券报表导出", "导出代金券 Excel", "代金券对账报表",
  "费用管理", "list BSS coupons", "query vouchers by project", "coupon inventory",
  "voucher list by enterprise project", "enterprise project voucher query",
  "voucher report export", "export coupons to excel",
  "billing voucher query", "华为云代金券".
  Read-only inventory / reporting only — NOT for issuing, claiming,
  transferring, reclaiming, freezing or adjusting coupons; those mutating
  operations belong to huawei-cloud-bss-coupon-manage.
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
- **Report export** — `--export xlsx,html` writes the same result to a local
  Excel workbook (four sheets) and/or a self-contained offline HTML report
  (detail tables + enterprise-project and status charts), for finance
  apportionment and reconciliation hand-off.

### Out of Scope

Every mutating BSS operation (create / reclaim / transfer / adjust coupon
quotas, claim / send / freeze / cancel coupons). The write-intent guard rejects
those before any command is executed. PDF export (needs a heavy dependency,
tracked separately) and scheduled / pushed report delivery are also out of
scope.

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
3. **IAM permission** — read-only `billing:coupon:view`; add `billing:order:view` when
   using `--project-id` / `--usage-analysis` (order linkage). Least-privilege
   policy in [references/iam-policies.md](references/iam-policies.md).
4. **Python 3.8+** (standard library only — argparse / json / subprocess;
   report export uses zipfile for the workbook, no `openpyxl` required).
5. **Outbound HTTPS** access to `bss.myhuaweicloud.com`.
6. **Region** — BSS is a global service; KooCLI only accepts the
   `cn-north-1` channel region for `--cli-region`. Any other value is rejected
   before the call with a business hint (BSS data is global, so no other
   region is needed).
7. **Local write permission** for the export directory (`--out-dir`, default
   the current directory) — only when `--export` is used.

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

# Report export (combinable with every filter / output mode above)
python3 scripts/list_coupons.py --export xlsx                       # four-sheet workbook in ./
python3 scripts/list_coupons.py --export html --out-dir ./reports  # offline HTML charts
python3 scripts/list_coupons.py --expiring 30 --export xlsx,html --out-dir ./reports
python3 scripts/list_coupons.py --usage-analysis --export xlsx,html --out-dir ./reports
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
| `--region` / `-r` | No | BSS channel region; **only `cn-north-1` is accepted** (BSS is global, every other value is rejected with a business hint) | `cn-north-1` |
| `--json` | No | Output the raw voucher array as JSON | — |
| `--names-only` | No | Output voucher (plan) names only | — |
| `--status` | No | Filter by voucher status: `1` unactivated, `2` available, `3` used, `4` expired, `5` reclaimed — numeric codes or aliases (`available` / `used` / `expired` / `reclaimed` …). Unknown values are rejected with the available choices (no silent empty result) | `available`, `2` |
| `--name` | No | Filter by promotion plan name / coupon code — **client-side** (API has no name parameter) | `spring` |
| `--coupon-id` | No | Filter by exact voucher ID (server-side query parameter) | `CP0001` |
| `--coupon-type` | No | Filter by coupon type: `1` voucher, `2` discount, `3` product, `4` cash (server-side) | `1` |
| `--project-id` | No | Filter by enterprise project ID — **client-side via order linkage**; needs `billing:order:view` | `proj-abc123` |
| `--expiring DAYS` | No | List vouchers expiring within DAYS days (not yet expired); DAYS must be a positive integer | `30` |
| `--expired` | No | List already-expired vouchers | — |
| `--usage-analysis` | No | Per-project usage-rate summary (count / face / balance / used / rate) | — |
| `--export` | No | Export a report: `xlsx` (four-sheet workbook), `html` (self-contained charts), combinable — `xlsx,html` | `xlsx,html` |
| `--out-dir DIR` | No | Report output directory (default: current directory); existing files are never overwritten | `./reports` |
| `--page-size` | No | Page size for the coupon list; must be `1..100` (BSS maximum, default 100) | `100` |
| `--operation` | No | hcloud BSS operation name; only the read-only `ListSubCustomerCoupons` (alias `ListCoupons`) is allowed | `ListSubCustomerCoupons` |

Output-mode precedence: `--usage-analysis` → `--names-only` → `--json` → table (default).
`--export` is orthogonal: it never changes what the screen prints, only adds
report files after the screen output.

## Report Export

`--export` turns the query result into a local report for finance
apportionment (财务分摊) and reconciliation (对账). Both formats are produced
from **the same in-memory result** the screen shows (`collect_report_data()` —
no second query, so counts and amounts cannot drift).

| Format | Content |
| ------ | ------- |
| `xlsx` | Four worksheets: `代金券明细` (full-field detail, amounts as real numeric cells), `临期明细` (near-expiry / expired rows), `企业项目用量` (per-project count / face / balance / used / usage rate), `导出信息` (generation time, region, filters, view, record counts, totals, data source, export formats) |
| `html` | One self-contained file: summary cards, per-project 面额/余额/已用 bar chart, voucher status distribution chart, per-project usage table, detail and near-expiry tables. Chart.js v4.4.0 (MIT, https://www.chartjs.org) is inlined from `assets/chart.umd.min.js`; CSS and data are inlined too, so it opens offline by double-click with no network and no CDN reference |

Behaviour:

- File name `bss-voucher-report_{region}_{YYYYmmdd_HHMMSS}.xlsx|.html` in
  `--out-dir` (default: current directory). An existing name is never
  overwritten — a `_1`, `_2` … suffix is appended instead.
- Near-expiry sheet/window: exactly the requested view when `--expiring N` or
  `--expired` is used, otherwise the default **30-day** window (already-expired
  vouchers are counted on the 导出信息 sheet).
- Enterprise-project columns/sheets require the read-only order linkage
  (`ListCustomerOrders`, needs `billing:order:view`) — it runs once, and only when
  `--usage-analysis` or `--export` is requested; unattributed vouchers fall
  into the `-` bucket. The screen table keeps its original columns.
- After a successful export the absolute path and record counts are printed
  (`已导出 …（代金券 N 条 / 临期 M 条 / 企业项目 K 个）`).
- No half-written files: the workbook / HTML is written to a temporary file in
  the target directory and renamed only on success; on any failure the partial
  files are removed.

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
- **Region parameter** — `--cli-region=<value>`, **always `--cli-region=cn-north-1`**
  (the only BSS channel region KooCLI accepts; BSS is a global service, so
  other values add no data and are rejected up front).
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
| Error envelope with exit code 0 (`{"error_code": ...}`) | Exit 1: the top-level `error_code` / `error_msg` is inspected **before** rendering, then mapped to an auth / credential / API error. Never reported as an empty list and never exported as 0 rows |
| 403 / insufficient IAM permission (incl. `CBC.0151`) | Exit 1, `无权限访问 BSS 代金券（CBC.0151）…` hint naming the required read-only `billing:coupon:view` |
| Missing / invalid AK-SK | Exit 1, explicit hint to configure credentials out-of-band (never in chat) |
| `--project-id` given but order lookup forbidden | Orders skipped gracefully; coupons without attributable order keep `project_id "-"` and the filter result reflects only attributable vouchers |
| hcloud not installed | Exit 1 after SDK fallback also unavailable, hint to install KooCLI or the SDK packages |
| Network / API failure | Exit 1 with the hcloud stderr excerpt |
| KooCLI has no BSS service (`[USE_ERROR]Unsupported service: BSS`) | Transparent fallback to the SDK (no error), because the CLI catalog is incomplete rather than the request being invalid |
| Unsupported `--region` (anything but `cn-north-1`) | Exit 1 **before** any call, business hint `不支持的 BSS Region … 仅接受 --region cn-north-1`; the raw `[USE_ERROR]` / region dump is not shown |
| Other KooCLI usage error (`[USE_ERROR] ...` with rc=0) | Exit 1, explicit hcloud 参数错误 hint pointing to `hcloud BSS ListSubCustomerCoupons --help` |
| Unknown `--status` value | Exit 1, `未知的代金券状态 … 可用值: …` listing every alias and numeric code; no silent empty list |
| `--expiring 0` / negative, or `--page-size` outside `1..100` | Exit 1 with a range hint; no query executed |
| Write intent detected | Exit 1, `GuardError` message, no command executed |
| `--export` unknown format (e.g. `pdf`) | Exit 1, `未知导出格式 … 仅支持 xlsx / html`, no query executed, no file written |
| `--out-dir` unwritable / not a directory | Exit 1, `导出目录不可写 …` / `导出目录不是目录 …`, no file written |
| Report write failure (disk full, permission) | Exit 1, Chinese hint; partial files removed (no half-written report) |

Exit codes: `0` success / empty result; `1` usage (region/status/range), config, auth, guard, export, or API error (including an error envelope returned with rc=0).

## Edge Cases

| Scenario | Handling |
| ---------- | --------- |
| `--status` numeric / alias | Forwarded server-side as the numeric BSS status code (1-5); displayed with a human-readable label |
| `--status` unrecognised text | Rejected explicitly (`未知的代金券状态 … 可用值: …`) instead of returning a silently empty list |
| `--name` filter | Applied client-side after the full paged list is fetched (API has no name parameter) |
| `--project-id` filter | Applied client-side: coupon records carry no project_id, so each coupon is attributed to the enterprise projects of its `order_id` / `lock_order_id` via `ListCustomerOrders`; only the order actually matching the queried order_id is used (prevents cross-attribution) |
| Coupon with no order linkage | `project_id` / `project_name` default to `"-"`; excluded when `--project-id` is given |
| Large voucher count | Automatic `offset` paging (count-aware, full-page fallback, max 100 pages, page size capped at 100) |
| Extra response fields | Table columns are built from the union of returned fields — new fields appear automatically |
| Field missing on a voucher | Rendered as `-` in the table |
| Nested `use_limits` | Flattened into a `useLimits` JSON column for the table |
| Non-JSON hcloud output | `ApiError` with the raw excerpt (first 200 chars) |
| hcloud absent, or its catalog lacks BSS, and SDK installed | Transparent fallback to `huaweicloudsdkbss` `list_sub_customer_coupons` (GlobalCredentials + global endpoint), same output modes |
| User asks to create/reclaim/transfer coupons | Out of scope — blocked by the write-intent guard |
| `--export` with an empty result set | Exit 0, screen prints the usual `无 BSS 代金券` message, report still has four sheets / two charts with `（无数据）` |
| `--export` combined with `--json` / `--names-only` / `--usage-analysis` | Screen output unchanged; report is written afterwards from the same result |
| Very large result set (>1000 vouchers) | Workbook is streamed sheet by sheet into the zip; the HTML table is a single scrolled block, so both stay responsive |

## Testing

Verification was performed offline during development with mocked hcloud
subprocesses (no credentials, no network) for the query paths, report export
and error handling. Those development-time test modules are not shipped in the
packaged skill (Phase-6 cleanup); the package is self-contained and carries no
`tests/` directory.

The packaged skill includes credential-free offline smoke cases in
`templates/test-vars.json` for the QA executor:

```bash
python3 scripts/list_coupons.py --help
python3 -c "import sys; sys.path.insert(0, 'scripts'); import report_export; print('report_export import ok')"
```

`TC-03` is an inline standard-library smoke: it builds a small in-memory
result, writes both `xlsx` and `html`, verifies both files exist, and reads the
workbook back through `zipfile` to confirm the four worksheets. It requires no
`tests/` directory, no credentials and no third-party package.

Verification coverage (development-time): rc=0 error envelopes (`CBC.0151` →
auth error, other codes → API error, never an empty list or rc 0), unsupported
region business hint (no raw `[USE_ERROR]` leak), unknown `--status` listing
valid choices, `--expiring` / `--page-size` range validation; export format
parsing / unknown-format rejection, filename shape and non-overwrite,
unwritable `--out-dir`, four-sheet workbook structure with numeric (money / int
/ percent) cells, XML escaping, empty-result export, self-contained HTML (no
external `src`/`href`, ≥2 charts, escaped values, script-safe JSON),
partial-failure cleanup, and `collect_report_data()` screen/report consistency
across `--expiring` / `--expired` / `--usage-analysis` / `--project-id` / empty
results.

## Reference Documents

| Document | Content |
| ---------- | --------- |
| [references/iam-policies.md](references/iam-policies.md) | Least-privilege read-only IAM policy (`billing:coupon:view`, `billing:order:view`) |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | KooCLI installation and credential configuration |
| [references/verification-method.md](references/verification-method.md) | How the skill was verified, plus the credential-free offline smoke cases |
| [references/dataflow-diagram.md](references/dataflow-diagram.md) | Mermaid data flow diagram |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria checklist |
| `scripts/list_coupons.py` | Query CLI: filtering, project attribution, usage analysis, output modes, `--export` / `--out-dir` |
| `scripts/report_export.py` | Report layer: OOXML `.xlsx` writer (zipfile only) and self-contained `.html` writer (charts + tables) |
| `assets/chart.umd.min.js` | Chart.js v4.4.0 (MIT) inlined into the HTML report for offline use |