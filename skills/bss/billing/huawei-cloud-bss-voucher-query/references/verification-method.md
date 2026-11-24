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

## Packaged offline smoke (no credentials, no network)

The packaged skill ships no `tests/` directory. Repeatable offline smoke cases
live in `templates/test-vars.json` and are executed by the QA stage:

```bash
# TC-01: CLI help lists the export options
python3 scripts/list_coupons.py --help

# TC-02: export layer imports with the standard library only
python3 -c "import sys; sys.path.insert(0, 'scripts'); import report_export; print('report_export import ok')"

# TC-03: inline export smoke (no tests/ directory, no third-party package)
python3 -c "import sys,tempfile,zipfile,os; sys.path.insert(0,'scripts'); import report_export as r; d={'coupons':[{'coupon_id':'CP-1','face_value':'10.00','balance':'5.00','status':2}],'expiring_rows':[],'usage_rows':[],'meta':{'region':'cn-north-1'}}; out=r.export_report(d,['xlsx','html'],tempfile.mkdtemp()); assert len(out)==2 and all(os.path.exists(x['path']) for x in out); z=zipfile.ZipFile(out[0]['path']); assert len([n for n in z.namelist() if n.startswith('xl/worksheets/sheet')])==4; print('report export smoke ok')"
```

Development-time coverage (mocked hcloud, executed while the skill was built;
the test modules themselves are not part of the package): write-intent guard,
status parsing + unknown-status rejection, command construction (no invented
server-side project parameter), JSON extraction, rc=0 error-envelope
classification (`CBC.0151` -> auth, others -> API, never an empty list),
failure classification (missing AK/SK / 403 / usage error / region / generic),
BSS region whitelist (`cn-north-1` only), `--expiring` / `--page-size` range
validation, server-side status forwarding, client-side name/project filtering,
order-based project attribution (matching order id only; unattributed -> "-"),
usage analysis aggregation (per project + unattributed), expiry filtering,
table/json/names-only renderers, SDK fallback handling, and main() modes.

## Manual smoke commands (require credentials)

```bash
python3 scripts/list_coupons.py --names-only
python3 scripts/list_coupons.py --usage-analysis
python3 scripts/list_coupons.py --project-id <enterprise_project_id>
python3 scripts/list_coupons.py --status available --expiring 30
```

## Report export verification (offline)

```bash
# Inline smoke: writes both formats from an in-memory result, no credentials
python3 -c "import sys,tempfile,zipfile,os; sys.path.insert(0,'scripts'); import report_export as r; d={'coupons':[{'coupon_id':'CP-1','face_value':'10.00','balance':'5.00','status':2}],'expiring_rows':[],'usage_rows':[],'meta':{'region':'cn-north-1'}}; out=r.export_report(d,['xlsx','html'],tempfile.mkdtemp()); assert len(out)==2 and all(os.path.exists(x['path']) for x in out); z=zipfile.ZipFile(out[0]['path']); assert len([n for n in z.namelist() if n.startswith('xl/worksheets/sheet')])==4; print('report export smoke ok')"

# Optional end-to-end against a mocked hcloud (fixture coupons + order projects)
VOUCHER_QUERY_HCLOUD_BIN=<mock-hcloud> \
  python3 scripts/list_coupons.py --export xlsx,html --out-dir <tmpdir>
```

What was checked for the export layer during development (mock-based, no
credentials / no network):

- `.xlsx` is a valid zip; `zipfile` + `ElementTree` read back the four sheets
  `代金券明细 / 临期明细 / 企业项目用量 / 导出信息`, header labels are UTF-8,
  special characters (`<`, `&`) survive one escape/unescape round trip,
  amounts / counts / usage rates are written as **numeric** cells with
  `0.00` / `0` / `0.0%` number formats, and the header row is frozen.
- The workbook also opens in a real consumer library (`openpyxl` 3.1.5 was used
  as an independent reader during verification: sheets, frozen pane and
  numeric values all parsed; `openpyxl` is **not** a runtime dependency).
- `.html` contains zero external `src`/`href` references, the inlined
  Chart.js v4.4.0 banner, two `<canvas>` charts, the detail + near-expiry
  tables, escaped cell values, and a script-safe JSON payload whose syntax
  passes `node --check`.
- `--export xlsx,html` writes both files in one run; a repeated run within the
  same second produces `_1` suffixes instead of overwriting.
- `--export` combined with `--json` / `--names-only` / `--usage-analysis` /
  `--expiring 30` / `--expired` / `--project-id` and with empty results keeps
  the screen output identical.
- Unknown format (`--export pdf`) and a non-directory `--out-dir` exit with 1
  and print a Chinese error; a forced write failure leaves no file behind.

## Result

- Packaged offline smoke (`templates/test-vars.json` TC-01..TC-03): runnable
  with the standard library only, no credentials and no `tests/` directory.
- Development-time suites: query paths, report export and error handling were
  executed with mocked hcloud during development (all passing) and then removed
  from the package per the Huawei Cloud skill Phase-6 cleanup.
- Live execution was not possible in the sandbox (no BSS credentials / no
  routed BSS hcloud service); the error paths and SDK fallback degrade
  gracefully with explicit hints. Functional verification relies on the smoke
  cases above, the development-time mocked runs and the verified API metadata.