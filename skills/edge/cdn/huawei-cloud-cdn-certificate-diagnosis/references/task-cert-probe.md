# Step 3: Probe Actual Certificate Status

Probe the certificate chain information actually served by the CDN edge node via `python scripts/cert_probe.py --domain <domain_name> --timeout 10`. The script performs the TLS handshake against `<domain>:443`, extracts the parsed peer certificate metadata via `ssl.create_default_context()` (verification enabled, trust store honored as-is), and emits a single JSON object on stdout.

## Prerequisites

- Step 2 returned `https_status=3` (HTTPS certificate configured)
- cert_name and expiration_time have been obtained (expiration_time may be empty)
- Python >= 3.8 is available (the probe uses stdlib `ssl` + `socket` only; no third-party dependency)

## Command

```bash
python scripts/cert_probe.py --domain <domain_name> --timeout 10
```

**Parameter Description**:
- `--domain <domain_name>`: target CDN accelerated domain (required; validated as RFC 1035)
- `--timeout <seconds>`: connection timeout in seconds (optional; default 10, range 1-30). The timeout applies to the TCP connect and the TLS handshake.
- The script connects to `<domain>:443`, performs the TLS handshake with SNI (`server_hostname=domain`), reads the parsed peer certificate dict via `getpeercert()`, and emits JSON on stdout. The HTTP response body is not fetched.

## Input

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--domain` | string | Yes | Target domain for TLS certificate probing (RFC 1035, length <= 253) |
| `--timeout` | int | No | Connection timeout in seconds (default 10, range 1-30) |

Invalid `--domain` or out-of-range `--timeout` cause the script to exit with code 2 and emit a JSON error object on stdout (no probe is attempted).

## Output JSON Schema

> **Output envelope**: the script wraps its output in the platform standard `{result, data, error_msg}` envelope (`format_output()` in `cert_probe.py`); business fields are inside `data`. Parse `data.*`, not the top level.

On success (exit code 0):

```json
{
  "result": "success",
  "data": {
    "domain": "www.example.com",
    "connected": true,
    "tls": {
      "subject_cn": "www.example.com",
      "issuer_cn": "TrustAsia TLS RSA CA",
      "not_before": "2025-09-12T00:00:00Z",
      "not_after": "2026-09-12T00:00:00Z",
      "san_list": ["www.example.com", "example.com"]
    },
    "duration_ms": 312,
    "error": null
  },
  "error_msg": ""
}
```

On failure (exit code 0; soft failures are reported via `error`, not via the exit code):

```json
{
  "result": "failed",
  "data": {
    "domain": "www.example.com",
    "connected": false,
    "tls": null,
    "duration_ms": 10004,
    "error": {
      "reason": "tls_handshake_failed",
      "message": "<exception summary>"
    }
  },
  "error_msg": "tls_handshake_failed"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `data.domain` | string | The domain argument echoed back |
| `data.connected` | bool | `true` once the TCP+TLS connection succeeded; `false` on any failure before the handshake completes |
| `data.tls.subject_cn` | string | Subject Common Name from the peer certificate |
| `data.tls.issuer_cn` | string | Issuer Common Name from the peer certificate |
| `data.tls.not_before` | string | Certificate not-before date in ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`); sourced from the RFC 2822 `notBefore` field |
| `data.tls.not_after` | string | Certificate not-after (expiration) date in ISO 8601 UTC; sourced from the RFC 2822 `notAfter` field |
| `data.tls.san_list` | string[] | Subject Alternative Name DNS entries (may be empty) |
| `data.duration_ms` | int | Probe duration in milliseconds |
| `data.error.reason` | string | Failure code (see table below); `null` on success |
| `data.error.message` | string | Human-readable failure summary; `null` on success. Stack traces are written to stderr only. |

## Parsing

The next workflow step (Step 4 / report generation) consumes the following JSON fields:

| Field | Consumer |
|-------|----------|
| `data.tls.not_after` | Step 4 expiry comparison vs. API-returned `expiration_time`; report `Expire Date` |
| `data.tls.issuer_cn` | Report `Issuer` |
| `data.tls.subject_cn` | Report `CN` |
| `data.tls.san_list` | Report `SAN` (joined with `, `) |
| `data.error.reason` | Step 4 / report decision logic on probe failure |

The 10-second timeout is enforced by the script itself via `--timeout` (default 10).

## Decision Logic

| Probe Result | Status | Handling |
|--------------|--------|----------|
| `result == "success"` and `data.connected == true` and `data.tls` is non-null and `data.error == null` | Certificate probe succeeded | Record subject_cn / issuer_cn / not_before / not_after / san_list; continue to Step 4 |
| `data.connected == true` and `data.tls.san_list` (or other field) empty | Partial information missing | Record the parsed fields; annotate missing fields |
| `data.error.reason == "tls_handshake_failed"` | Certificate probe failed | Record "Certificate not correctly deployed or link abnormal: <data.error.message>" |
| `data.error.reason == "connect_timeout"` | Probe timeout | Record "Certificate probe timed out; recommend manual verification" |
| `data.error.reason == "connect_failed"` | Connection failed | Record "Connection failed: <data.error.message>" |
| `data.error.reason != null` (other) | Certificate probe failed | Record "<data.error.reason>: <data.error.message>" |

## Error reason codes

| `data.error.reason` | Trigger | Exit code |
|----------------|---------|-----------|
| `connect_timeout` | `socket.timeout` on TCP connect or TLS handshake | 0 |
| `connect_failed` | `ConnectionRefusedError` / `OSError` on TCP connect | 0 |
| `tls_handshake_failed` | `ssl.SSLError` during `wrap_socket` | 0 |
| `unexpected_probe_error` | Any other unexpected exception (traceback to stderr only) | 0 |
| `invalid_domain` | `--domain` failed RFC 1035 validation | 2 |
| `invalid_timeout` | `--timeout` outside `1..30` | 2 |

## Output Records

- TLS probe status (succeeded / failed / timed out) — from `data.connected` / `data.error`
- `data.tls.not_after` (expiration date, ISO 8601 UTC)
- `data.tls.issuer_cn` (issuer CN)
- `data.tls.subject_cn` (subject CN)
- `data.tls.san_list` (SAN list, may be empty)
- `data.duration_ms` (probe duration in milliseconds)
- `data.error.reason` and `data.error.message` on failure (otherwise null)

## Exception Handling

| Exception Scenario | Handling |
|---------------------|----------|
| Python interpreter not installed or version < 3.8 | Prompt to install Python >= 3.8; see cli-installation-guide.md |
| `python` points to Python 2 | Use `python3 scripts/cert_probe.py` instead |
| Stdlib `ssl`/`socket` not importable (stripped interpreter) | Reinstall a complete Python >= 3.8 build; see cli-installation-guide.md |
| `--domain` invalid | Script exits with code 2 and emits `data.error.reason=invalid_domain`; no probe attempted |
| `--timeout` out of range `[1, 30]` | Script exits with code 2 and emits `data.error.reason=invalid_timeout`; no probe attempted |
| TLS verification failure (e.g., expired/revoked cert) | Script does NOT relax verification (no `CERT_NONE`, no `check_hostname=False`); reports `data.error.reason=tls_handshake_failed` so the diagnosis reflects the real deployment state |
| Domain CNAME not in effect | `connect_failed` or `connect_timeout` reported; prompt "Domain CNAME may not be in effect; please check DNS resolution" |

## Example

```bash
# Successful probe
python scripts/cert_probe.py --domain www.example.com --timeout 10
# stdout:
# {
#   "result": "success",
#   "data": {
#     "domain": "www.example.com",
#     "connected": true,
#     "tls": {
#       "subject_cn": "www.example.com",
#       "issuer_cn": "TrustAsia TLS RSA CA",
#       "not_before": "2025-09-12T00:00:00Z",
#       "not_after": "2026-09-12T00:00:00Z",
#       "san_list": ["www.example.com", "example.com"]
#     },
#     "duration_ms": 312,
#     "error": null
#   },
#   "error_msg": ""
# }
# → Record certificate information; continue to Step 4

# Timeout
# stdout:
# {
#   "result": "failed",
#   "data": {
#     "domain": "timeout.example.com",
#     "connected": false,
#     "tls": null,
#     "duration_ms": 10004,
#     "error": { "reason": "connect_timeout", "message": "Connection to timeout.example.com:443 timed out after 10s" }
#   },
#   "error_msg": "connect_timeout"
# }
# → Certificate probe timed out

# TLS handshake failure (e.g., expired certificate)
# stdout:
# {
#   "result": "failed",
#   "data": {
#     "domain": "expired.example.com",
#     "connected": false,
#     "tls": null,
#     "duration_ms": 421,
#     "error": { "reason": "tls_handshake_failed", "message": "[SSL: CERTIFICATE_VERIFY_FAILED] ..." }
#   },
#   "error_msg": "tls_handshake_failed"
# }
# → Certificate chain verification failed (verify against API-returned expiration_time)
```

## Comparison with API Response

Compare `data.tls.not_after` (ISO 8601 UTC) from the probe with the `expiration_time` (ms timestamp) returned by `ShowCertificatesHttpsInfo/v2`:
- Both match → certificate configuration is in sync and normal
- Both differ → there may be cache latency or certificate update not yet synced; annotate the difference in the report

## Report Content

Record the following information in the diagnosis report:
- Diagnosis item name: Actual Certificate Probe
- Status: Pass / Fail / Warning
- Detail: `data.tls.not_after`, `data.tls.issuer_cn`, `data.tls.subject_cn`, `data.tls.san_list`
- Comparison result with API response (if applicable)
- `data.duration_ms` and `data.error.reason` are available for diagnostic context
