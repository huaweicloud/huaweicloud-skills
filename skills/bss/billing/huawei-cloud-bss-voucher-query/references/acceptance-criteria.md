# Acceptance Criteria

## Functional

- [x] List all BSS vouchers / coupons via `hcloud BSS ListSubCustomerCoupons`
      with automatic paging and three output modes (table / `--json` /
      `--names-only`).
- [x] Filter coupons by enterprise project ID (`--project-id`). Because the
      coupon API carries no project field, the script attributes coupons to
      projects client-side through the customer order linkage
      (`ListCustomerOrders` → `enterprise_projects`).
- [x] Compose project + status filtering (`--project-id` + `--status`).
- [x] Near-expiry (`--expiring N`) and expired (`--expired`) views based on
      `valid_time` / `expire_time`, combinable with `--project-id`.
- [x] Per-project usage-rate analysis (`--usage-analysis`) aggregating
      `face_value` vs `balance` (count / total face / total balance / total
      used / usage rate).
- [x] Existing filters preserved: `--status`, `--name`, `--coupon-id`,
      `--coupon-type`, `--page-size`, `--region`.
- [x] `--export xlsx` writes a workbook with the four sheets 代金券明细 /
      临期明细 / 企业项目用量 / 导出信息; row counts and amounts match the
      on-screen table, amounts are numeric cells, text is UTF-8 and
      XML-escaped, column widths are adapted.
- [x] `--export html` writes one self-contained file (no external `src`/`href`,
      Chart.js inlined) with the detail tables and at least two charts
      (per-project 面额/余额/已用, voucher status distribution); it opens by
      double-click with the network disabled.
- [x] `--export xlsx,html` produces both files in one run; names carry the
      region and a `YYYYmmdd_HHMMSS` timestamp and never overwrite an existing
      file (`_1`, `_2` … suffix instead).
- [x] Empty results and the `--expiring 30` / `--expired` /
      `--usage-analysis` / `--project-id` combinations export without crashing
      and stay consistent with the screen.
- [x] `--export` combined with `--json` / `--names-only` / `--usage-analysis`
      leaves the screen semantics unchanged (report is additive).
- [x] Unknown export format or an unwritable `--out-dir` → Chinese error
      message and exit code 1, with no partial report file left behind.

## Error handling

- [x] An hcloud error envelope returned with exit code 0 (`error_code` /
      `error_msg`, e.g. `CBC.0151`) is classified before rendering and exits 1
      as an auth/API error — never reported as an empty list or a 0-row export.
- [x] `--region` outside the BSS channel whitelist (`cn-north-1`) is rejected
      up front with a business hint; no raw `[USE_ERROR]` / region dump leaks.
- [x] Unknown `--status` values error out and list every valid alias/code.
- [x] `--expiring` requires a positive integer and `--page-size` stays within
      `1..100`; out-of-range values exit 1 without querying.

## Read-only safety

- [x] Write-intent guard blocks create / delete / update / reclaim / transfer /
      adjust / send / freeze / cancel intents before execution.
- [x] Only the read-only coupon GET and the read-only order GET are ever
      constructed.
- [x] Credentials never handled by the script (profile / env only).

## Quality

- [x] Offline verification passes with mocked hcloud (no credentials); the
      packaged skill's credential-free smoke cases live in
      `templates/test-vars.json` and do not depend on a `tests/` directory.
- [x] KooCLI parameter names match the real API (`--help`/metaOrigin) — no
      invented server-side project parameter.
- [x] SKILL.md frontmatter name matches the directory name; required sections
      present; no `version` field.