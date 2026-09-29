# Troubleshooting

## Common Issues

### Issue: Credentials Not Configured

**Symptom**: `hcloud configure list` output has no AK/SK, or hcloud command returns an authentication error

**Resolution**:
1. Run `hcloud configure` to interactively configure AK/SK
2. Or configure via environment variables:
   ```bash
   export HUAWEICLOUD_SDK_AK=<your-access-key-id>
   export HUAWEICLOUD_SDK_SK=<your-secret-key>
   ```
3. After configuration, re-run `hcloud configure list` to verify

### Issue: Domain Not Found (404)

**Symptom**: `ShowVerifyDomainOwnerInfo` returns `error_code: CDN.0171` or 404

**Resolution**:
1. Check the domain spelling
2. Confirm the domain has been accessed via CDN under the current account
3. Confirm you are using the correct account
4. Go to the CDN console to view all accessed domains

### Issue: Permission Denied (403)

**Symptom**: `ShowVerifyDomainOwnerInfo` returns 403 or a permission denied error

**Resolution**:
1. Check whether the IAM user has the CDN query permission (`cdn:*:query*`, plus `cdn:configuration:queryDomains` for the domain list)
2. Confirm the AK/SK belongs to the correct account
3. Contact the account administrator to grant CDN domain query permission
4. See [iam-policies.md](iam-policies.md) for details

### Issue: API Call Failed

**Symptom**: `ShowVerifyDomainOwnerInfo` returns a non-200 response or an abnormal error

**Resolution**:
1. Degrade to probe-only results (if verification info is already available, continue probing)
2. Mark in the report "API query failed, only probe results provided, recommend manual confirmation"
3. Check whether hcloud version is >= 3.2.0
4. Check whether the network connection is normal

### Issue: Python Probe Library Missing

**Symptom**: `python scripts/file_probe.py` or `python scripts/dns_txt_probe.py`
exits with code 2 and JSON `error.reason == "missing_library"` (or
`ModuleNotFoundError: No module named 'requests'` / `'dns'` on stderr)

**Resolution**:
1. Install the required libraries:
   ```bash
   pip install requests>=2.25 dnspython>=2.1
   ```
2. Verify imports succeed:
   ```bash
   python -c "import requests, dns.resolver; print('ok')"
   ```
3. See [cli-installation-guide.md](cli-installation-guide.md) for the full
   library dependency section

### Issue: File Probe Connection Failure

**Symptom**: `file_probe.py` returns JSON with `error.reason == "connect_failed"`
(formerly "curl connection refused"); `data.http_status` is `null`

**Resolution**:
1. Check the local network connection to the verification file URL
2. Confirm the origin server / CDN node is reachable (`ping`, traceroute)
3. If a corporate firewall blocks outbound HTTP, allow egress to the
   verification file host
4. Retry the probe with `--timeout 10` to confirm the timeout is not the
   cause (`connect_timeout` would be reported instead if it were)

### Issue: File Probe TLS Handshake Failure

**Symptom**: `file_probe.py` returns JSON with
`error.reason == "tls_handshake_failed"` (formerly "curl SSL certificate
error")

**Resolution**:
1. The probe does not bypass certificate validation (no equivalent of curl invoked with the insecure flag); report the failure as-is
2. Verify the origin certificate is valid and trusted by the system trust
   store
3. Recommend manual verification of the origin certificate and renewal if
   expired

### Issue: DNS Probe Returns No Answer

**Symptom**: `dns_txt_probe.py` returns JSON with
`error.reason == "dns_no_answer"` and `txt_records == []` (formerly "dig
returns no answer")

**Resolution**:
1. The DNS name exists but has no TXT records — confirm the TXT record was
   actually created
2. Wait for DNS propagation (usually 5-10 minutes, up to 24 hours)
3. Retry with an explicit public resolver to rule out local resolver cache:
   ```bash
   python scripts/dns_txt_probe.py --name <dns_query_name> --resolver 8.8.8.8
   ```

### Issue: DNS Probe Returns NXDOMAIN

**Symptom**: `dns_txt_probe.py` returns JSON with
`error.reason == "dns_nxdomain"` (formerly "dig NXDOMAIN")

**Resolution**:
1. The DNS name itself does not exist — verify `dns_verify_name` spelling
   against the value returned by `ShowVerifyDomainOwnerInfo`
2. Confirm the parent zone is delegated correctly
3. Retry against a public resolver to rule out local resolver issues:
   ```bash
   python scripts/dns_txt_probe.py --name <dns_query_name> --resolver 8.8.8.8
   ```

### Issue: Probe Timeout (Python script)

**Symptom**: `file_probe.py` returns `error.reason == "connect_timeout"`, or
`dns_txt_probe.py` returns `error.reason == "dns_timeout"` (formerly "curl/dig
times out within 10 seconds")

**Resolution**:
1. Return partial results, mark "File probe timed out, recommend manual
   verification" or "DNS probe timed out"
2. Check the local network connection
3. For DNS, retry with an explicit public resolver: `python
   scripts/dns_txt_probe.py --name <dns_query_name> --resolver 8.8.8.8`
4. Try manually executing the probe script to confirm

### Issue: Probe Returns Unexpected Error

**Symptom**: `file_probe.py` or `dns_txt_probe.py` returns JSON with
`error.reason == "unexpected_probe_error"`; the detailed traceback is written
to stderr (never stdout)

**Resolution**:
1. Capture the stderr traceback for debugging
2. Confirm the Python version is >= 3.8 and both libraries meet the minimum
   versions (`requests >= 2.25`, `dnspython >= 2.1`)
3. If the error persists, report it as a skill defect with the stderr output
   and the exact command line used

### Issue: Ownership Verification Already Passed but Still Reports Failure

**Symptom**: `ShowVerifyDomainOwnerInfo` returns verification status=passed

**Resolution**:
1. Report "Ownership verification has passed, may be cache latency, recommend refreshing and retrying"
2. Wait 5-10 minutes and re-query
3. If it still reports failure, contact CDN technical support

## Best Practices

### 1. Always Verify Credentials First

Before performing diagnosis, run `hcloud configure list` first to confirm credentials are valid.

### 2. Use Recommended Region

Use `--cli-region=<region>` for CDN API to avoid confusion.

### 3. Set Timeout

All probe scripts enforce a 10-second timeout via `--timeout` (default 10):
- `python scripts/file_probe.py --url <url> --timeout 10`
- `python scripts/dns_txt_probe.py --name <name> --timeout 10`
- `--timeout` accepts values in the range [1, 30]

### 4. Do Not Input Credentials in the Conversation

If the user attempts to provide AK/SK in the conversation, refuse immediately and guide them to use `hcloud configure` for configuration.

## Error Handling Summary

| Scenario | Handling |
|----------|----------|
| Credentials not configured | Abort, prompt to configure credentials |
| Domain not found (404) | Abort, prompt to confirm domain ownership |
| Permission denied (403) | Abort, prompt to contact administrator for authorization |
| API call failed | Degrade to probe-only results |
| Python library missing (`error.reason == "missing_library"`) | Abort, prompt to run `pip install requests>=2.25 dnspython>=2.1` |
| File probe connection refused (`error.reason == "connect_failed"`) | Mark "Connection failed", recommend network check |
| File probe TLS handshake failure (`error.reason == "tls_handshake_failed"`) | Mark failure, recommend manual certificate check (no `-k` bypass) |
| DNS NXDOMAIN (`error.reason == "dns_nxdomain"`) | Mark "DNS name does not exist", confirm `dns_verify_name` spelling |
| DNS no answer (`error.reason == "dns_no_answer"`) | Mark "TXT record not configured", recommend adding the record |
| Probe timeout (`data.error.reason` ends in `_timeout`) | Return partial results, mark timeout |
| Unexpected probe error (`error.reason == "unexpected_probe_error"`) | Capture stderr traceback, report as skill defect |
| Verification already passed | Report cache latency, recommend refreshing |
