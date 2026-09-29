# Step 4: DNS TXT Record Verification

Query the DNS TXT record via the Python script `scripts/dns_txt_probe.py` and
verify whether the returned `data.txt_records` list contains `verify_content`. The
script emits a single JSON object on stdout and supports an optional explicit
resolver (the former `dig @8.8.8.8` use case).

## Prerequisites

- Step 2 returned DNS TXT verification method (dns_verify_type=TXT)
- dns_verify_name, verify_domain_name and verify_content have been obtained
- Python >= 3.8 available and `dnspython >= 2.1` importable
  (see [cli-installation-guide.md](cli-installation-guide.md))

> **⚠️ Name join semantics (critical)**: the API returns `dns_verify_name` as a
> **bare label** (e.g., `cdn_verification`, no dot). The actual DNS query name
> must be joined with the domain: `dns_query_name = f"{dns_verify_name}.{verify_domain_name}"`
> (e.g., `cdn_verification.example.com`). Passing the bare label directly to
> `--name` makes the script reject it with `error.reason == "invalid_name"` (RFC 1035
> requires a fully qualified name with at least one dot).

## Command

```bash
# dns_query_name = f"{dns_verify_name}.{verify_domain_name}" — join first, then probe
python scripts/dns_txt_probe.py --name <dns_query_name> [--resolver <ip>] [--timeout 10]
# Example: dns_verify_name=cdn_verification, verify_domain_name=example.com
python scripts/dns_txt_probe.py --name cdn_verification.example.com
```

### Input Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--name` | string | Yes | DNS name to query for TXT records (validated against RFC 1035) |
| `--resolver` | IPv4/IPv6 literal | No | Optional explicit DNS resolver (e.g. `8.8.8.8`). Must be a single IP literal; hostnames and comma-separated lists are rejected. When omitted, the system default resolver is used |
| `--timeout` | int | No | Query lifetime in seconds, default 10, range [1, 30] |

`--resolver 8.8.8.8` replaces the former `dig @8.8.8.8 -t TXT <name> +short`.
Only TXT records are queried (no AXFR, SRV, NS, ANY). The host's
`/etc/resolv.conf` is never echoed in the JSON output.

### Exit Codes

| Exit Code | Meaning |
|-----------|---------|
| 0 | Probe ran to completion (including soft failures such as NXDOMAIN, NoAnswer) |
| 2 | Argument error or missing library import (prerequisite failure) |

## Output JSON Schema

> **Output envelope**: the script wraps its output in the platform standard `{result, data, error_msg}` envelope; business fields are inside `data`. Parse `data.*`, not the top level.

Default (system resolver):

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

With `--resolver 8.8.8.8`, the `data.resolver` field reports `"8.8.8.8"`:

```json
{
  "result": "success",
  "data": {
    "name": "cdn_verification.example.com",
    "resolver": "8.8.8.8",
    "txt_records": ["verify-token-20240101"],
    "duration_ms": 51,
    "error": null
  },
  "error_msg": ""
}
```

| Field | Type | Description |
|-------|------|-------------|
| `data.name` | string | The DNS name passed via `--name` |
| `data.resolver` | string | `"system"` when no `--resolver` was given, otherwise the validated resolver IP literal |
| `data.txt_records` | string[] | TXT record values (one entry per TXT RRset; multi-string TXT records are concatenated) |
| `data.duration_ms` | int | Probe duration in milliseconds |
| `data.error` | object \| null | On failure: `{ "reason": <code>, "message": <string> }`; `null` when the probe succeeded |

### Error `reason` codes

| `data.error.reason` | Meaning | Corresponds to |
|----------------|---------|----------------|
| `dns_nxdomain` | Domain does not exist | `dns.resolver.NXDOMAIN` |
| `dns_no_answer` | Name exists but no TXT records returned | `dns.resolver.NoAnswer` |
| `dns_timeout` | Query lifetime exceeded the timeout | `dns.resolver.LifetimeTimeout` |
| `invalid_name` | DNS name failed RFC 1035 validation | argparse validation (exit code 2) |
| `invalid_resolver` | `--resolver` is not a single IP literal | argparse validation (exit code 2) |
| `invalid_timeout` | `--timeout` outside [1, 30] | argparse validation (exit code 2) |
| `missing_library` | `dnspython` not importable | `ImportError` (exit code 2) |
| `unexpected_probe_error` | Unhandled exception during probe | generic fallback |

## Parsing (Fields Consumed by Next Step)

Step 5 (Report Generation) and the decision logic below consume these JSON
fields:

- `data.txt_records` — substring/equals match against `verify_content`; any record that matches means pass
- `data.resolver` — surfaced in the report detail so the operator knows which resolver answered
- `data.error.reason` — surface the failure mode (timeout vs NXDOMAIN vs no answer)
- `data.duration_ms` — included in the report detail (optional)

## Decision Logic

| Probe JSON | Status | Action |
|------------|--------|--------|
| `data.txt_records` contains a record equal to (or containing) `verify_content` | ✅ DNS verification passed | Record "DNS TXT verification passed" |
| `data.txt_records` non-empty but does not contain `verify_content` | ❌ DNS verification failed | Record "TXT record value mismatch", report expected and actual values |
| `data.txt_records` empty and `data.error.reason == "dns_no_answer"` | ❌ DNS verification failed | Record "TXT record not configured" |
| `data.error.reason == "dns_nxdomain"` | ❌ DNS verification failed | Record "DNS name does not exist (<dns_query_name>)" |
| `data.error.reason == "dns_timeout"` | ⚠️ Probe timeout | Record "DNS probe timed out" |
| other `data.error.reason` | ❌ Verification failed | Record "DNS query failed: <data.error.reason> — <data.error.message>" |

## Output Records

- `data.txt_records` value list
- Whether `verify_content` is included
- `data.resolver` (system or explicit IP)
- `data.duration_ms` (optional, include in the report detail)
- `data.error.reason` and `data.error.message` (when the probe did not complete)

## Exception Handling

| Exception Scenario | Handling |
|--------------------|----------|
| `dnspython` library missing (`data.error.reason == "missing_library"`, exit code 2) | Abort the skill and prompt the user to run `pip install requests>=2.25 dnspython>=2.1` (see [cli-installation-guide.md](cli-installation-guide.md)) |
| DNS server not responding | Retry once with an explicit public resolver: `python scripts/dns_txt_probe.py --name <dns_query_name> --resolver 8.8.8.8` |
| Timeout (`data.error.reason == "dns_timeout"`) | Return partial results, mark "DNS probe timed out" |
| Multiple records returned | Compare `verify_content` against each entry in `data.txt_records`; any match means pass |

## Example

```bash
# DNS TXT record verification (system resolver) — name must be joined first:
# dns_query_name = f"{dns_verify_name}.{verify_domain_name}"
# e.g., dns_verify_name=cdn_verification, verify_domain_name=example.com
python scripts/dns_txt_probe.py --name cdn_verification.example.com

# Returns JSON:
#   { "result": "success",
#     "data": { "name": "cdn_verification.example.com",
#               "resolver": "system",
#               "txt_records": ["verify_xxxxxxx"],
#               "duration_ms": 38,
#               "error": null },
#     "error_msg": "" }
# → data.txt_records contains verify_content → DNS verification passed ✅

# data.txt_records == [] and data.error.reason == "dns_no_answer"
# → TXT record not configured → DNS verification failed ❌

# data.txt_records == ["other_value"]
# → Does not contain verify_content → DNS verification failed ❌

# data.error.reason == "dns_timeout"
# → DNS probe timed out ⚠️

# Retry with an explicit public resolver:
python scripts/dns_txt_probe.py --name cdn_verification.example.com --resolver 8.8.8.8
```

## Report Content

Record the probe results in the diagnosis report:
- Diagnosis item name: DNS TXT record verification
- Status: ✅ Pass / ❌ Fail / ⚠️ Warning
- Detail: `data.txt_records` + match result + `data.resolver` + expected value + actual value

## Fix Recommendations

If DNS verification fails, provide the following fix recommendations in the report:
- Add a TXT record in DNS, with host record `<dns_verify_name>` (a bare label; the full query name is `<dns_query_name>`) and record value `<verify_content>`
- Wait for DNS to take effect (usually 5-10 minutes, up to 24 hours)
- After it takes effect, retrigger the ownership verification
