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

## Read-only safety

- [x] Write-intent guard blocks create / delete / update / reclaim / transfer /
      adjust / send / freeze / cancel intents before execution.
- [x] Only the read-only coupon GET and the read-only order GET are ever
      constructed.
- [x] Credentials never handled by the script (profile / env only).

## Quality

- [x] Offline unit tests pass (mocked hcloud subprocess, no credentials).
- [x] KooCLI parameter names match the real API (`--help`/metaOrigin) — no
      invented server-side project parameter.
- [x] SKILL.md frontmatter name matches the directory name; required sections
      present; no `version` field.