# Step 3: File Verification Probe

Probe whether the verification file exists via the Python script
`scripts/file_probe.py`, and verify whether the file content matches
`verify_content`. The script emits a single JSON object on stdout.

## Prerequisites

- Step 2 returned file verification method (file_verify_url present)
- file_verify_url and verify_content have been obtained
- Python >= 3.8 available and `requests >= 2.25` importable
  (see [cli-installation-guide.md](cli-installation-guide.md))

## Command

```bash
python scripts/file_probe.py --url <file_verify_url> [--timeout 10]
```

### Input Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--url` | string | Yes | URL of the verification file to fetch (http or https only; `file://`, `ftp://`, `gopher://` rejected) |
| `--timeout` | int | No | Request timeout in seconds, default 10, range [1, 30] |

The script enforces the 10-second timeout on both connect and read phases
(`requests.get(url, timeout=10, allow_redirects=False)`). Redirects are NOT
followed, matching the former `curl -m 10` behavior (no `-L`). No
`Authorization`, `Cookie`, or caller-supplied headers are sent.

### Exit Codes

| Exit Code | Meaning |
|-----------|---------|
| 0 | Probe ran to completion (including soft failures such as HTTP 4xx/5xx) |
| 2 | Argument error or missing library import (prerequisite failure) |

## Output JSON Schema

```json
{
  "url": "http://www.example.com/verify.txt",
  "http_status": 200,
  "content_length": 36,
  "content_preview": "20240101-abcdef-verify-token",
  "duration_ms": 180,
  "error": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `data.url` | string | The URL passed via `--url` |
| `data.http_status` | int \| null | HTTP status code from the response (e.g., 200, 404, 503); `null` if no response was received |
| `data.content_length` | int \| null | Length of the response body in bytes |
| `data.content_preview` | string \| null | First 256 bytes of the response body decoded as UTF-8 with `errors="replace"`; capped at 256 bytes |
| `data.duration_ms` | int | Probe duration in milliseconds |
| `data.error` | object \| null | On failure: `{ "reason": <code>, "message": <string> }`; `null` when the probe succeeded |

### Error `reason` codes

| `data.error.reason` | Meaning | Corresponds to |
|----------------|---------|----------------|
| `connect_timeout` | TCP connect timed out within the budget | `requests.ConnectTimeout` |
| `connect_failed` | Connection refused / network unreachable | `requests.ConnectionError` (non-timeout) |
| `tls_handshake_failed` | TLS handshake failed | `requests.exceptions.SSLError` |
| `invalid_url` | URL scheme is not http/https or host is missing | argparse validation (exit code 2) |
| `invalid_timeout` | `--timeout` outside [1, 30] | argparse validation (exit code 2) |
| `missing_library` | `requests` not importable | `ImportError` (exit code 2) |
| `unexpected_probe_error` | Unhandled exception during probe | generic fallback |

## Parsing (Fields Consumed by Next Step)

Step 5 (Report Generation) and the decision logic below consume these JSON
fields:

- `data.http_status` — classify HTTP 200 / 404 / 5xx / null (timeout/error)
- `data.content_preview` — substring match against `verify_content`
- `data.error.reason` — surface the failure mode (timeout vs connection failure)
- `data.duration_ms` — included in the report detail (optional)

## Decision Logic

| Probe JSON | Status | Action |
|------------|--------|--------|
| `data.http_status == 200` and `data.content_preview` contains `verify_content` | ✅ File verification passed | Record "File verification passed" |
| `data.http_status == 200` and `data.content_preview` does not contain `verify_content` | ❌ File verification failed | Record "Verification file content mismatch", report expected and actual values |
| `data.http_status == 404` | ❌ File verification failed | Record "Verification file does not exist. Please upload the verification file as prompted." |
| `data.http_status` in 5xx range | ❌ File verification failed | Record "Server error: <data.http_status>" |
| `data.error.reason == "connect_timeout"` | ⚠️ Probe timeout | Record "File probe timed out, recommend manual verification" |
| `data.error.reason == "connect_failed"` | ❌ File verification failed | Record "Connection failed: <data.error.message>" |
| other `data.error.reason` | ❌ File verification failed | Record "Probe failed: <data.error.reason> — <data.error.message>" |

## Output Records

- `data.http_status` (report as the HTTP status code)
- `data.content_preview` (for comparison with `verify_content`)
- `data.duration_ms` (optional, include in the report detail)
- `data.error.reason` and `data.error.message` (when the probe did not complete)

## Exception Handling

| Exception Scenario | Handling |
|--------------------|----------|
| `requests` library missing (`error.reason == "missing_library"`, exit code 2) | Abort the skill and prompt the user to run `pip install requests>=2.25 dnspython>=2.1` (see [cli-installation-guide.md](cli-installation-guide.md)) |
| TLS certificate error (`error.reason == "tls_handshake_failed"`) | Do not bypass verification; report the failure and recommend manual verification of the origin certificate |
| Redirect | Redirects are NOT followed (`allow_redirects=False`); a 3xx `data.http_status` is reported as-is so the operator can decide |
| Timeout (`error.reason == "connect_timeout"`) | Return partial results, mark "File probe timed out, recommend manual verification" |
| Unexpected probe error (`error.reason == "unexpected_probe_error"`) | The full traceback is written to stderr (not stdout); the report displays a generic failure |

## Example

```bash
# File verification probe
python scripts/file_probe.py --url http://www.example.com/verify.txt

# Returns JSON:
#   { "url": "http://www.example.com/verify.txt",
#     "http_status": 200,
#     "content_length": 15,
#     "content_preview": "verify_xxxxxxx",
#     "duration_ms": 142,
#     "error": null }
# → http_status == 200 + content_preview contains verify_content
# → File verification passed ✅

# http_status == 404 + error == null
# → File verification failed ❌, report "Verification file does not exist"

# error.reason == "connect_timeout" + http_status == null
# → Probe timeout ⚠️, report "File probe timed out, recommend manual verification"
```

## Report Content

Record the probe results in the diagnosis report:
- Diagnosis item name: File verification probe
- Status: ✅ Pass / ❌ Fail / ⚠️ Warning
- Detail: `data.http_status` + `data.content_preview` match result + expected value + actual value
