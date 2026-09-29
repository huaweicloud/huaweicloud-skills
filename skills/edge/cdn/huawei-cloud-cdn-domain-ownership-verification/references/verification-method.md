# Verification Method

Verify that the skill diagnosis results are correct and complete.

## Verification Steps

### 0. Verify Python Library Availability

```bash
python -c "import requests, dns.resolver; print('ok')"
```

Confirm `requests >= 2.25` and `dnspython >= 2.1` are importable before any
probe step runs. If the import fails, install the missing library:

```bash
pip install requests>=2.25 dnspython>=2.1
```

### 1. Verify Credential Configuration

```bash
hcloud configure list
```

Check that the output contains a valid AK/SK configuration (mode=AKSK).

### 2. Verify Ownership Verification Info Query

```bash
hcloud CDN ShowVerifyDomainOwnerInfo --cli-region=<region> --domain_name=<test domain>
```

Check that the return is 200, confirming the domain belongs to the current account, and contains verification method info:
- DNS TXT verification: `dns_verify_type=TXT` + `dns_verify_name` + `verify_content`
- File verification: `file_verify_url` + `file_verify_filename` + `verify_content`
- Already passed: verification status field shows passed

### 3. Verify File Probe (if applicable)

```bash
python scripts/file_probe.py --url <file_verify_url> [--timeout 10]
```

The script emits a single JSON object on stdout. Check the following JSON
fields:

```json
{
  "url": "http://www.example.com/verify.txt",
  "http_status": 200,
  "content_length": 36,
  "content_preview": "verify_xxxxxxx",
  "duration_ms": 180,
  "error": null
}
```

- `http_status == 200` indicates the verification file is reachable
- `data.content_preview` contains `verify_content` → file verification passed
- `data.http_status == 404` → file verification failed (file does not exist)
- `error.reason == "connect_timeout"` → probe timed out (partial result)

### 4. Verify DNS TXT Record Probe (if applicable)

```bash
python scripts/dns_txt_probe.py --name <dns_query_name> [--resolver <ip>] [--timeout 10]
```

The script emits a single JSON object on stdout. Check the following JSON
fields:

```json
{
  "name": "_cdnverify.example.com",
  "resolver": "system",
  "txt_records": ["verify_xxxxxxx"],
  "duration_ms": 42,
  "error": null
}
```

- `data.txt_records` contains `verify_content` → DNS verification passed
- `data.txt_records` is empty (or `data.error.reason == "dns_no_answer"`) → TXT record not configured
- `data.error.reason == "dns_nxdomain"` → the DNS name does not exist
- `data.error.reason == "dns_timeout"` → probe timed out (partial result)
- To retry against an explicit public resolver, append `--resolver 8.8.8.8`

### 5. Verify Report Format

Check that the output report contains:
- Analysis time and target domain
- Diagnosis item list (each item contains name, status ✅/❌/⚠️, detail)
- Conclusion and fix recommendations

## Expected Output

```
==================== CDN Domain Ownership Verification Diagnosis Report ====================
Analysis Time: 2026-08-12T10:00:00+08:00
Target Domain: www.example.com

--- Diagnosis Items ---
[Domain Permission Check]: ✅ Pass
  Detail: Domain belongs to current account
[Verification Method]: ✅ Pass
  Detail: DNS TXT record verification
[TXT Record Probe]: ❌ Fail
  Detail: TXT record not configured or value mismatch
  Expected: xxx
  Actual: (empty)

--- Conclusion ---
Status: Ownership verification failed
Suggestion: Please add a TXT record in DNS <dns_verify_name> with value <verify_content>, wait for DNS to take effect and retry
```
