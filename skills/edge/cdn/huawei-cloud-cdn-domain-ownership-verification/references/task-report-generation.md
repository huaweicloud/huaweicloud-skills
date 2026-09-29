# Step 5: Generate Diagnosis Report

Aggregate probe results and generate a structured text diagnosis report.

## Report Format

```
==================== CDN Domain Ownership Verification Diagnosis Report ====================
Analysis Time: <ISO 8601 time>
Target Domain: <domain>

--- Diagnosis Items ---
[Domain Permission Check]: ✅ Pass / ❌ Fail / ⚠️ Warning
  Detail: <detail>
[Verification Method]: ✅ Pass / ❌ Fail / ⚠️ Warning
  Detail: <DNS TXT verification / file verification / already passed>
[File Verification Probe]: ✅ Pass / ❌ Fail / ⚠️ Warning / N/A
  Detail: <HTTP status code + content match result>
  Expected: <verify_content>
  Actual: <actual content>
[DNS TXT Record Verification]: ✅ Pass / ❌ Fail / ⚠️ Warning / N/A
  Detail: <TXT record value + match result>
  Expected: <verify_content>
  Actual: <actual TXT record value>

--- Conclusion ---
Status: <overall status>
Suggestion: <fix recommendation>
```

## Status Marking Rules

| Mark | Meaning | Use Scenario |
|------|---------|--------------|
| ✅ Pass | Passed | Probe result meets expectation |
| ❌ Fail | Failed | Probe result does not meet expectation |
| ⚠️ Warning | Warning | Probe timed out or partial result |
| N/A | Not applicable | This item is not involved in the verification method |

## Probe Field Sources

The probe detail values in the report come from the JSON emitted by the Python
probe scripts. The report must read these fields by name rather than parsing
free-form text.

| Report Field | Source | JSON Field | Notes |
|--------------|--------|------------|-------|
| HTTP status (File Verification Probe detail) | `scripts/file_probe.py` | `data.http_status` | `null` when the probe did not reach an HTTP response (timeout / connection failure) |
| File content / actual value (File Verification Probe) | `scripts/file_probe.py` | `data.content_preview` | First 256 bytes, UTF-8 decoded with `errors="replace"`; compared against `verify_content` |
| File probe failure reason | `scripts/file_probe.py` | `data.error.reason` | e.g. `connect_timeout`, `connect_failed`, `tls_handshake_failed` |
| File probe duration (optional detail) | `scripts/file_probe.py` | `data.duration_ms` | Milliseconds |
| TXT record / actual value (DNS TXT Record Verification) | `scripts/dns_txt_probe.py` | `data.txt_records` | String array; any entry matching `verify_content` means pass |
| Resolver used (DNS TXT detail) | `scripts/dns_txt_probe.py` | `data.resolver` | `"system"` or the explicit `--resolver` IP |
| DNS probe failure reason | `scripts/dns_txt_probe.py` | `data.error.reason` | e.g. `dns_nxdomain`, `dns_no_answer`, `dns_timeout` |
| DNS probe duration (optional detail) | `scripts/dns_txt_probe.py` | `data.duration_ms` | Milliseconds |

### Content safety rule

The report MUST NOT echo `data.content_preview` verbatim if it matches a credential
pattern (long base64 / JWT shape). In that case, the report shows a redacted
placeholder such as `<content redacted: matches credential pattern>` and
records the original length. This filtering is a mandatory content-security
rule of the report generation step.

## Report Generation Rules

1. **Analysis time**: use ISO 8601 format (e.g., `2026-08-12T10:00:00+08:00`)
2. **Target domain**: the domain_name entered by the user
3. **Diagnosis item list**: list all diagnosis items in step order
4. **Detail**: each item includes probe result and key information sourced from the probe JSON fields above
5. **Expected value and actual value**: compare the verification content with the actual probe result (HTTP `data.content_preview` for file verification, `data.txt_records` entries for DNS TXT verification)
6. **Conclusion**: overall status (passed / failed / partial pass)
7. **Fix recommendation**: provide specific fix recommendations based on failed items

## Conclusion Status Determination

| Scenario | Overall Status | Fix Recommendation |
|----------|----------------|---------------------|
| All verifications passed | ✅ Ownership verification passed | No fix needed, domain ownership verification has passed |
| File verification failed | ❌ Ownership verification failed | Please upload the verification file to the origin server as prompted, with file content `<verify_content>` |
| DNS verification failed | ❌ Ownership verification failed | Please add a TXT record in DNS `<dns_verify_name>` with value `<verify_content>`, wait for DNS to take effect and retry |
| Probe timeout | ⚠️ Some probes timed out | Recommend manually verifying probe results, confirm network connection is normal and retry |
| Verification already passed | ✅ Ownership verification already passed | May be cache latency, recommend refreshing and retrying |
| Insufficient permission | ❌ Unable to diagnose | Contact the administrator to grant CDN domain query permission |
| Domain does not exist | ❌ Unable to diagnose | Please confirm domain ownership, domain is not under current account |

## Example Report

### DNS TXT Verification Failed

```
==================== CDN Domain Ownership Verification Diagnosis Report ====================
Analysis Time: 2026-08-12T10:00:00+08:00
Target Domain: www.example.com

--- Diagnosis Items ---
[Domain Permission Check]: ✅ Pass
  Detail: Domain belongs to current account
[Verification Method]: ✅ Pass
  Detail: DNS TXT record verification
[File Verification Probe]: N/A
  Detail: Verification method is DNS TXT, file verification not involved
[DNS TXT Record Verification]: ❌ Fail
  Detail: TXT record not configured or value mismatch (resolver=system, txt_records=[])
  Expected: verify_xxxxxxx
  Actual: (empty)

--- Conclusion ---
Status: Ownership verification failed
Suggestion: Please add a TXT record in DNS example.com.verify.cdn with value verify_xxxxxxx, wait for DNS to take effect and retry
```

### File Verification Passed

```
==================== CDN Domain Ownership Verification Diagnosis Report ====================
Analysis Time: 2026-08-12T10:05:00+08:00
Target Domain: www.example.com

--- Diagnosis Items ---
[Domain Permission Check]: ✅ Pass
  Detail: Domain belongs to current account
[Verification Method]: ✅ Pass
  Detail: File verification
[File Verification Probe]: ✅ Pass
  Detail: http_status=200, content_preview matches verify_content
  Expected: verify_xxxxxxx
  Actual: verify_xxxxxxx
[DNS TXT Record Verification]: N/A
  Detail: Verification method is file verification, DNS TXT not involved

--- Conclusion ---
Status: Ownership verification passed
Suggestion: Verification file is configured correctly. If CDN still does not pass verification, it may be cache latency, recommend waiting and retrying
```
