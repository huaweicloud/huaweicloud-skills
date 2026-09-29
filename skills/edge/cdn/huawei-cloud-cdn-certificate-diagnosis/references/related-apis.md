# API and CLI Command Reference

## API Quick Reference

| Step | API | Method | Purpose | Key Parameters |
|------|-----|--------|---------|----------------|
| 1 | `ShowDomainDetailByName` | GET | Validate domain permission + get basic info | `--domain_name` |
| 2 | `ShowCertificatesHttpsInfo/v2` | GET | Query certificate configuration | `--domain_name` |
| 3 | `scripts/cert_probe.py` | — | Probe actual certificate status (TLS handshake, JSON output) | `--domain`, `--timeout` |
| 4 | `scripts/cert_expiry_check.py` | — | Compute days remaining | `--expiration_time` |

## API Details

### ShowDomainDetailByName

**Purpose**: Query domain details by domain name; used to validate that the domain belongs to the current account.

**Command**:
```bash
hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=<domain>
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--domain_name` | string | Yes | Accelerated domain |
| `--cli-region` | string | Yes | Region; recommended `cn-north-1` |

**Returned Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Domain ID |
| `domain_name` | string | Domain name |
| `cname` | string | CNAME address |
| `domain_status` | string | Domain status (online/offline/configuring) |

**Response Example**:
```json
{
  "id": "xxxxxxxxxx",
  "domain_name": "www.example.com",
  "cname": "www.example.com.cdn.net",
  "domain_status": "online"
}
```

**Error Codes**:

| Error Code | Description | Handling |
|------------|-------------|----------|
| 200 | Success | Continue to next step |
| 404 | Domain not found | Stop; prompt to confirm domain ownership |
| 403 | Insufficient permission | Stop; prompt to contact the administrator for authorization |
| CDN.0171 | Domain does not belong to current account | Stop; prompt to confirm domain ownership |

### ShowCertificatesHttpsInfo/v2

**Purpose**: Query the HTTPS certificate configuration of a CDN domain, including configuration status, certificate name, and expiration time.

**Command**:
```bash
hcloud CDN ShowCertificatesHttpsInfo/v2 --cli-region=<region> --domain_name=<domain>
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--domain_name` | string | Yes | Accelerated domain |
| `--cli-region` | string | Yes | Region; recommended `cn-north-1` |

**Returned Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `total` | int | Total number of HTTPS certificate records |
| `https` | array | List of `HttpsDetail` objects — locate the target domain by `domain_name` inside this array |
| `https[].domain_name` | string | Accelerated domain this record belongs to |
| `https[].https_status` | int | Certificate configuration status: 0=not configured / 2=configuring / 3=configured |
| `https[].cert_name` | string | Certificate name (returned when https_status=3) |
| `https[].expiration_time` | long | Certificate expiration time (ms timestamp, returned when https_status=3; may be empty) |

> **Parsing rule**: the fields are **not** at the top level. Locate the element in `https[]` whose `domain_name` matches the queried domain, then read `https_status` / `cert_name` / `expiration_time` from that element. If `https[]` is empty or no matching `domain_name` exists, treat the domain as "certificate not configured".

**https_status Value Description**:

| https_status | Meaning | Next Handling |
|--------------|---------|---------------|
| 0 | HTTPS certificate not configured | Report "Certificate not configured"; skip probe and calculation |
| 2 | Certificate configuring | Report "Certificate configuring; please wait for configuration to complete"; skip probe and calculation |
| 3 | HTTPS certificate configured | Continue to `cert_probe.py` probe and expiration calculation |

**Response Example (configured, https_status=3)**:
```json
{
  "total": 1,
  "https": [
    {
      "domain_name": "www.example.com",
      "https_status": 3,
      "cert_name": "example-cert",
      "expiration_time": 1789824000000
    }
  ]
}
```

**Response Example (not configured, https_status=0)**:
```json
{
  "total": 1,
  "https": [
    {
      "domain_name": "www.example.com",
      "https_status": 0
    }
  ]
}
```

**Response Example (configuring, https_status=2)**:
```json
{
  "total": 1,
  "https": [
    {
      "domain_name": "www.example.com",
      "https_status": 2
    }
  ]
}
```

**Error Codes**:

| Error Code | Description | Handling |
|------------|-------------|----------|
| 200 | Success | Branch handling by https_status |
| 404 | Domain not found | Stop; prompt to confirm domain ownership |
| 403 | Insufficient permission | Stop; prompt to contact the administrator to grant the CDN query permission (`cdn:*:query*`) |
| Other | API call failed | Degrade to probe results only; annotate "API query failed" |

## Python Probe Scripts

### `scripts/cert_probe.py` (Actual Certificate Status Probe)

**Path**: `scripts/cert_probe.py` (relative to the skill root).

**Purpose**: Connect to `<domain>:443` via TLS, extract the parsed peer certificate metadata (subject CN, issuer CN, notBefore, notAfter, SAN list) via `ssl.create_default_context()` (verification enabled, trust store honored as-is), and emit a single JSON object on stdout.

**Command**:
```bash
python scripts/cert_probe.py --domain <domain_name> [--timeout 10]
```

**CLI arguments**:

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--domain` | string | Yes | Target domain (RFC 1035, length <= 253) |
| `--timeout` | int | No | Connection timeout in seconds (default 10, range 1-30) |

**Library dependencies**: Python stdlib `ssl` + `socket` only. No third-party package needs to be installed. Python >= 3.8 required.

> **Output envelope**: the script wraps its output in the platform standard `{result, data, error_msg}` envelope; business fields are inside `data`. Parse `data.*`, not the top level.

**Output JSON schema (success)**:
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

**Output JSON schema (failure)**:
```json
{
  "result": "failed",
  "data": {
    "domain": "www.example.com",
    "connected": false,
    "tls": null,
    "duration_ms": 10004,
    "error": { "reason": "tls_handshake_failed", "message": "<exception summary>" }
  },
  "error_msg": "tls_handshake_failed"
}
```

**Output fields**:

| Field | Type | Description |
|-------|------|-------------|
| `data.domain` | string | The `--domain` argument |
| `data.connected` | bool | `true` once the TLS handshake succeeded |
| `data.tls.subject_cn` | string | Subject Common Name |
| `data.tls.issuer_cn` | string | Issuer Common Name |
| `data.tls.not_before` | string | Certificate start date, ISO 8601 UTC |
| `data.tls.not_after` | string | Certificate expiration date, ISO 8601 UTC |
| `data.tls.san_list` | string[] | SAN DNS entries (may be empty) |
| `duration_ms` | int | Probe duration in milliseconds |
| `error.reason` | string | Failure code (`connect_timeout`, `connect_failed`, `tls_handshake_failed`, `unexpected_probe_error`, `invalid_domain`, `invalid_timeout`); `null` on success |
| `error.message` | string | Human-readable failure summary; `null` on success |

**Exit codes**:
- `0` — probe completed (including soft failures; the failure is encoded in `error.reason`, not the exit code)
- `2` — argument validation error (`invalid_domain` or `invalid_timeout`)

**Decision Logic**:
- Probe succeeded + certificate chain valid → certificate actually served is normal
- `error.reason == "connect_timeout"` → return partial results; annotate "Certificate probe timed out"
- `error.reason == "connect_failed"` or `"tls_handshake_failed"` → certificate may not be correctly deployed

### `scripts/cert_expiry_check.py` (Days Remaining Calculation)

**Path**: `scripts/cert_expiry_check.py` (relative to the skill root).

**Command**:
```bash
python scripts/cert_expiry_check.py --expiration_time <ms-timestamp>
```

**Parameters**:
- `--expiration_time`: certificate expiration time (ms timestamp), from the `expiration_time` returned by `ShowCertificatesHttpsInfo/v2`

**Output**:
```json
{"result": "success", "data": {"days_remaining": <int|null>, "status": "normal|warning|expired|unknown"}, "error_msg": ""}
```

**Decision Logic**:

| data.days_remaining | data.status | Meaning |
|----------------|--------|---------|
| > 30 | normal | Certificate has sufficient remaining validity |
| 0 < ≤ 30 | warning | Certificate is about to expire; recommend updating in advance |
| ≤ 0 | expired | Certificate has expired; update immediately |
| null | unknown | expiration_time is empty or missing; no calculation performed |

## Command Chain Overview

Complete diagnosis command chain (https_status=3 scenario):

```bash
# 1. Permission validation
hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=<domain>

# 2. Certificate configuration query
hcloud CDN ShowCertificatesHttpsInfo/v2 --cli-region=<region> --domain_name=<domain>

# 3. Actual certificate status probe
python scripts/cert_probe.py --domain <domain_name> --timeout 10

# 4. Days remaining calculation
python scripts/cert_expiry_check.py --expiration_time <ms-timestamp>
```

## Important Notes

- All hcloud commands should use `--cli-region=<region>`
- All hcloud parameters must use the `--key=value` format (equals sign)
- `cert_probe.py` enforces a 10-second timeout by default (configurable via `--timeout`, range 1-30) and emits a single JSON object on stdout
- `cert_probe.py` uses stdlib `ssl` + `socket` only; no third-party dependency needs to be installed
- This skill uses only query-type APIs; it does not call any write operations
- The Python script handles only days-remaining calculation; it does not handle business flow
- When `expiration_time` is empty, directly report "Certificate expiration time unknown" and expose the raw API response to the user
