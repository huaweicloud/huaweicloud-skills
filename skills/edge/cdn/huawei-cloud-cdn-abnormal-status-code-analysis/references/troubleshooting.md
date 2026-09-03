# Troubleshooting

## CDN region not supported

- Symptom: `cli-region的值不支持,当前支持的区域值如下: cn-north-4 ru-moscow-1` when
  calling a CDN operation with `--cli-region=cn-north-4`.
- Cause: CDN does not support `cn-north-4`.
- Fix: use `--cli-region=cn-north-1` (or `ap-southeast-1`) for all CDN ops.

## CDN.0004 — not in the whitelist

- Symptom: `{"error":{"error_code":"CDN.0004","error_msg":"the customer is not in the whitelist"}}`
  on `ListBanUrl` / `ListAccessControlTask`.
- Cause: these query APIs require a 工单 (support ticket) whitelist.
- Action: they are still query-class GET. Record the error, do not bypass,
  proceed with other evidence; note "unconfirmed via CLI" in the report.

## Empty `result` from ShowDomainStats

- Symptom: `"result": {}` for a window.
- Cause: no traffic / no such status code in the window; or time points not
  aligned to the interval (e.g. non-CST-0:00 for `interval=86400`).
- Fix: widen the window (e.g. 31 days), align timestamps to the interval's
  required points, and confirm the domain had traffic.

## status_code_*and bs_status_code_* mixed in one query

- Symptom: error when passing both edge and origin stat types together.
- Cause: edge and back-to-source stats cannot be combined in one query.
- Fix: run them as two separate `ShowDomainStats/v2` calls.

## Top-N returns no status codes

- Symptom: `ListCdnDomainTopIps/Path/...` results look like request counts, not
  status-code breakdowns.
- Cause: Top-N `stat_type` supports only `flux`/`req_num`, no status code.
- Fix: use Top-N to shortlist suspect IPs/paths, then cross-check with
  `ShowLogs` / `ShowDomainStats` for their actual status codes.

## ShowLogs returns no links

- Symptom: `total: 0` / `logs: []`.
- Cause: no log file for the window, or window not left-closed right-open, or
  the domain had no traffic in that hour, or `start_time`/`end_time` not aligned
  to whole-hour points.
- Fix: align to whole-hour CST points; widen; confirm traffic.

## fetch_cdn_log.py errors

| `error.reason` | Meaning | Fix |
|----------------|---------|-----|
| `connect_timeout` | download timed out | raise `--timeout` (≤60); retry |
| `connect_failed` | network/TLS error | check network; retry |
| `http_error` | download returned non-200 | the presigned link may have expired — re-run `ShowLogs/v2` to refresh |
| `bad_gzip` | payload not valid gzip | inspect `--url`; the file may already be plain text |
| `missing_library` | `requests` not installed | `pip install requests>=2.25` |
| `invalid_url` / `invalid_timeout` / `invalid_status` / `invalid_max_lines` | bad args | fix the argument |

## Permission denied (403) on CDN queries

- Symptom: `403` / `Insufficient permission` on `Show*` config/stats.
- Cause: IAM user lacks CDN read scope.
- Fix: attach the system read-only policy `CDN Domain Viewer` (or grant
  `cdn:domain:get` + confirmed statistics/log read actions per the official
  IAM reference). Never elevate to write actions.
