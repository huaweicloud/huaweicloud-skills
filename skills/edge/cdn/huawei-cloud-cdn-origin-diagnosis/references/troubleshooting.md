# Troubleshooting

## Common Issues

### Issue: Credentials Not Configured

**Symptom**: `hcloud configure list` output shows no AK/SK, or hcloud command returns an authentication error

**Handling**:
1. Run `hcloud configure` to interactively configure AK/SK
2. Or configure via environment variables:
   ```bash
   export HUAWEICLOUD_SDK_AK=<your-access-key-id>
   export HUAWEICLOUD_SDK_SK=<your-secret-key>
   ```
3. After configuration, rerun `hcloud configure list` to verify

### Issue: Domain Does Not Exist (404)

**Symptom**: `ShowDomainDetailByName` returns `error_code: CDN.0171` or 404

**Handling**:
1. Check whether the domain name is spelled correctly
2. Confirm whether the domain has been onboarded to CDN under the current account
3. Confirm that you are using the correct account
4. Run `hcloud CDN ListDomains/v2 --cli-region=<region> --page_size=100` to view all onboarded domains

### Issue: Insufficient Permissions (403)

**Symptom**: `ShowDomainDetailByName` or `ShowDomainFullConfig/v2` returns 403 or a permission-denied error

**Handling**:
1. Check whether the IAM user has the CDN query permission (`cdn:*:query*`, plus `cdn:configuration:queryDomains` for the domain list)
2. Confirm that the AK/SK belongs to the correct account
3. Contact the primary account administrator to grant CDN domain query permissions
4. See [iam-policies.md](iam-policies.md) for details

### Issue: API Call Failed

**Symptom**: `ShowDomainFullConfig/v2` returns a non-200 response or an abnormal error

**Handling**:
1. Degrade to only prompting "Origin configuration query failed. Manual confirmation recommended."
2. Note in the report "API query failed; unable to retrieve origin configuration"
3. Check whether hcloud version is >= 3.2.0
4. Check whether network connectivity is normal
5. If failures persist, contact CDN technical support

### Issue: Origin Probe Timeout

**Symptom**: `scripts/origin_probe.py` emits `connected=false` with `error.reason=connect_timeout` (the script could not establish a TCP connection within the 10-second budget)

**Handling**:
1. Return partial results; note "Origin probe timed out. Manual verification recommended."
2. Check local network connectivity
3. Confirm that the origin address and port are correct
4. Confirm whether the origin firewall allows CDN back-to-source IP ranges
5. Try running the probe command manually to confirm:
   ```bash
   python scripts/origin_probe.py --scheme http --host <origin_addr> --port <http_port>
   ```

### Issue: Origin Probe Connection Refused / Unreachable

**Symptom**: `scripts/origin_probe.py` emits `connected=false` with `error.reason=connect_failed` (connection refused, network unreachable, or DNS resolution failure for a domain host)

**Handling**:
1. Note in the report "Origin unreachable (connection failed)"
2. Confirm the origin address and port are correct
3. Check whether the origin service is running and listening on the expected port
4. Check local network/firewall configuration
5. If a domain origin, verify DNS resolution from the execution host

### Issue: Origin Probe TLS Handshake Failed

**Symptom**: `scripts/origin_probe.py` emits `connected=false` with `error.reason=tls_handshake_failed` (HTTPS probe only — invalid/expired certificate, protocol mismatch, or SNI mismatch)

**Handling**:
1. Note in the report "Origin reachable at TCP layer but TLS handshake failed; origin may be unreachable via HTTPS"
2. Do NOT bypass certificate validation (the script enforces verification; there is no `--insecure` option)
3. Recommend the user check the origin certificate validity, expiry, and chain
4. If the certificate is expired or misconfigured, the origin is effectively unreachable for HTTPS back-to-source

### Issue: Missing Python Library

**Symptom**: `scripts/origin_probe.py` emits `error.reason=missing_library` and exits with code 2 (the `requests` library is not importable)

**Handling**:
1. Abort the probe step
2. Prompt the user to install the dependency: `pip install requests>=2.25`
3. Refer to [cli-installation-guide.md](cli-installation-guide.md) for the Python Library Dependencies section
4. After installation, rerun the skill

### Issue: Origin Not Configured (sources empty)

**Symptom**: `configs.sources` returned by `ShowDomainFullConfig/v2` is an empty array or does not exist

**Handling**:
1. Report "Origin not configured. Please configure the origin in the CDN console."
2. Abort the probe step (Step 3)
3. Prompt the user to confirm whether the domain configuration is complete
4. For newly created domains, the configuration may not be complete yet; prompt to wait and retry

### Issue: Origin Whitelist False Positive

**Symptom**: `scripts/origin_probe.py` returns `data.connected=true` with `data.http_status` 5xx (e.g., 502, 503, 504), or `data.connected=false` with `data.error.reason=connect_failed`, but the origin service itself is normal

**Handling**:
1. Note in the report: "The origin may have a whitelist configured. Please confirm that the CDN back-to-source IP ranges have been added to the origin whitelist."
2. Recommend that the user check the origin firewall, security group, WAF, and other configurations
3. Provide a CDN back-to-source IP range query recommendation (obtain via the Huawei Cloud CDN console or technical support)
4. Recommend that the user temporarily allow the CDN back-to-source IP ranges on the origin, then re-probe
5. If the local network can access the origin but CDN cannot perform back-to-source, the whitelist issue is more likely

## Best Practices

### 1. Always Verify Credentials First

Before performing the diagnosis, run `hcloud configure list` to confirm that credentials are valid.

### 2. Use the Recommended Region

Use `--cli-region=<region>` for CDN APIs to avoid confusion.

### 3. Set Timeout

All probe commands must set a 10-second timeout:
- `scripts/origin_probe.py`: `--timeout 10` (default 10; range 1-30)

### 4. Do Not Input Credentials in the Conversation

If the user attempts to provide AK/SK in the conversation, refuse immediately and guide them to use `hcloud configure`.

### 5. Pay Attention to the Back-to-source Protocol

Select the correct probe protocol and port based on `origin_protocol` (http / https / follow) to avoid misjudgment.

## Error Handling Summary

| Scenario | Handling |
|----------|----------|
| Credentials not configured | Abort; prompt to configure credentials |
| Domain does not exist (404) | Abort; prompt to confirm domain ownership |
| Insufficient permissions (403) | Abort; prompt to contact the administrator for authorization |
| API call failed | Report API query failure; recommend manual confirmation |
| `origin_probe.py` timeout (`error.reason=connect_timeout`) | Return partial results; note timeout |
| `origin_probe.py` connection failed (`error.reason=connect_failed`) | Report origin unreachable; recommend network/firewall check |
| `origin_probe.py` TLS handshake failed (`error.reason=tls_handshake_failed`) | Report TLS failure; recommend certificate check (no bypass) |
| `origin_probe.py` missing library (`error.reason=missing_library`) | Abort; prompt to install `requests>=2.25` |
| Origin not configured (sources empty) | Report origin not configured; abort probe |
| Origin whitelist false positive | Prompt to confirm that CDN back-to-source IP ranges are whitelisted |
