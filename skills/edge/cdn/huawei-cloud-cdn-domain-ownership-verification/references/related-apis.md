# API and CLI Command Reference

## API Quick Reference

| Step | API / Script | Method | Purpose | Key Parameters |
|------|---------------|--------|---------|----------------|
| 1 | `ShowVerifyDomainOwnerInfo` | GET | Query ownership verification info (also confirms domain belongs to the current account) | `--domain_name` |
| 2 | `scripts/file_probe.py` | HTTP GET | File verification probe (emits JSON) | `--url`, `--timeout 10` |
| 3 | `scripts/dns_txt_probe.py` | DNS TXT | DNS TXT record verification (emits JSON) | `--name`, `--resolver`, `--timeout 10` |

## API Details

### ShowVerifyDomainOwnerInfo

**Purpose**: query CDN domain ownership verification info, obtain the verification method and verification content.

**Command**:
```bash
hcloud CDN ShowVerifyDomainOwnerInfo --cli-region=<region> --domain_name=<domain>
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--domain_name` | string | Yes | Accelerated domain |
| `--cli-region` | string | Yes | Region, recommended `cn-north-1` |

**Domain permission check**: a successful query (200) confirms the domain exists and belongs to the current account. Error responses: `404` / `CDN.0171` → domain not under current account; `403` → insufficient permission.

**Return fields**:

| Field | Type | Description |
|-------|------|-------------|
| `dns_verify_type` | string | DNS verification type (TXT) |
| `dns_verify_name` | string | DNS TXT record **bare label** (e.g., `cdn_verification`; no dot) |
| `verify_domain_name` | string | Domain the verification applies to (join input: `dns_query_name = f"{dns_verify_name}.{verify_domain_name}"`) |
| `domain_name` | string | Accelerated domain |
| `file_verify_domains` | string[] | Domains covered by file verification (if applicable) |
| `file_verify_url` | string | File verification URL |
| `file_verify_filename` | string | Verification file name |
| `verify_content` | string | Verification content (TXT record value or file content) |

**Return example (DNS TXT verification)** — real shape: `dns_verify_name` is a bare label; join with `verify_domain_name` before probing:
```json
{
  "dns_verify_type": "TXT",
  "dns_verify_name": "cdn_verification",
  "verify_domain_name": "example.com",
  "verify_content": "verify_xxxxxxx"
}
# dns_query_name = f"{dns_verify_name}.{verify_domain_name}" = "cdn_verification.example.com"
```

**Return example (file verification)**:
```json
{
  "file_verify_url": "http://www.example.com/verify.txt",
  "file_verify_filename": "verify.txt",
  "verify_content": "verify_xxxxxxx"
}
```

## Python Probe Scripts

The skill uses two Python probe scripts under `scripts/`. Each script accepts
arguments via `argparse`, enforces a 10-second timeout (configurable via
`--timeout`, default 10), and emits exactly one JSON object on stdout. Exit
code `0` means the probe ran to completion (including soft failures such as
HTTP 4xx/5xx or NXDOMAIN); exit code `2` means an argument or missing-library
prerequisite failure.

### scripts/file_probe.py (File Verification Probe)

**Path**: `scripts/file_probe.py` (relative to the skill root)

**Command**:
```bash
python scripts/file_probe.py --url <file_verify_url> [--timeout 10]
```

**Arguments**:

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `--url` | string | Yes | — | Verification file URL (http or https only) |
| `--timeout` | int | No | 10 | Request timeout in seconds, range [1, 30] |

**Library requirement**: `requests >= 2.25`

**Output JSON schema**:

> **Output envelope**: both probe scripts wrap output in the platform standard `{result, data, error_msg}` envelope; business fields are inside `data`. Parse `data.*`, not the top level.

```json
{
  "result": "success",
  "data": {
    "url": "http://www.example.com/verify.txt",
    "http_status": 200,
    "content_length": 36,
    "content_preview": "20240101-abcdef-verify-token",
    "duration_ms": 180,
    "error": null
  },
  "error_msg": ""
}
```

**Field description**:

| Field | Type | Description |
|-------|------|-------------|
| `data.url` | string | The URL passed via `--url` |
| `data.http_status` | int \| null | HTTP status code, or `null` if no response was received |
| `data.content_length` | int \| null | Response body length in bytes |
| `data.content_preview` | string \| null | First 256 bytes decoded as UTF-8 with `errors="replace"` |
| `data.duration_ms` | int | Probe duration in milliseconds |
| `data.error` | object \| null | `{ "reason": <code>, "message": <string> }` on failure, else `null` |

**`data.error.reason` codes**: `connect_timeout`, `connect_failed`,
`tls_handshake_failed`, `invalid_url`, `invalid_timeout`,
`missing_library`, `unexpected_probe_error`.

**Decision logic**:
- `data.http_status == 200` + `data.content_preview` contains `verify_content` → file verification passed
- `data.http_status == 404` → file verification failed (file does not exist)
- `data.error.reason == "connect_timeout"` → probe timed out, return partial results

### scripts/dns_txt_probe.py (DNS TXT Record Verification)

**Path**: `scripts/dns_txt_probe.py` (relative to the skill root)

**Command**:
```bash
python scripts/dns_txt_probe.py --name <dns_query_name> [--resolver <ip>] [--timeout 10]
```

**Arguments**:

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `--name` | string | Yes | — | DNS name to query for TXT records (RFC 1035) |
| `--resolver` | IPv4/IPv6 literal | No | system resolver | Optional explicit DNS resolver (replaces `dig @8.8.8.8`) |
| `--timeout` | int | No | 10 | Query lifetime in seconds, range [1, 30] |

`--resolver 8.8.8.8` preserves the former `dig @8.8.8.8 -t TXT <name> +short`
behavior. The `data.resolver` field in the output reports either `"system"` or the
validated `--resolver` IP literal; the host's `/etc/resolv.conf` is never
echoed. Only TXT records are queried (no AXFR, SRV, NS, ANY).

**Library requirement**: `dnspython >= 2.1`

**Output JSON schema**:

```json
{
  "result": "success",
  "data": {
    "name": "cdn_verification.example.com",
    "resolver": "system",
    "txt_records": ["verify-token-20240101"],
    "duration_ms": 42,
    "error": null
  },
  "error_msg": ""
}
```

**Field description**:

| Field | Type | Description |
|-------|------|-------------|
| `data.name` | string | The DNS name passed via `--name` |
| `data.resolver` | string | `"system"` or the explicit `--resolver` IP literal |
| `data.txt_records` | string[] | TXT record values (one entry per TXT RRset; multi-string records concatenated) |
| `data.duration_ms` | int | Probe duration in milliseconds |
| `data.error` | object \| null | `{ "reason": <code>, "message": <string> }` on failure, else `null` |

**`data.error.reason` codes**: `dns_nxdomain`, `dns_no_answer`, `dns_timeout`,
`invalid_name`, `invalid_resolver`, `invalid_timeout`, `missing_library`,
`unexpected_probe_error`.

**Decision logic**:
- `data.txt_records` contains `verify_content` → DNS verification passed
- `data.txt_records` empty or does not contain `verify_content` → DNS verification failed
- `data.error.reason == "dns_timeout"` → probe timed out, return partial results

## Important Notes

- All hcloud commands should use `--cli-region=<region>`
- All hcloud parameters must use the `--key=value` format (connected with equals sign)
- Python probe scripts enforce a 10-second timeout via `--timeout` (default 10); no shell-level timeout flag is required
- Each probe script emits a single JSON object on stdout; diagnostic logs go to stderr
- This skill only uses query APIs and read-only network probes; it does not call any write operations
