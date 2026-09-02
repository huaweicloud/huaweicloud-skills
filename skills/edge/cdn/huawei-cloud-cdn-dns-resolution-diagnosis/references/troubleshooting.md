# Troubleshooting

## Common Issues

### Issue: Credentials Not Configured

**Symptom**: `hcloud configure list` output has no AK/SK, or hcloud command returns an authentication error

**Resolution**:
1. Run `hcloud configure` for interactive AK/SK configuration
2. Or configure via environment variables:
   ```bash
   export HUAWEICLOUD_SDK_AK=<your-access-key-id>
   export HUAWEICLOUD_SDK_SK=<your-secret-key>
   ```
3. After configuration, rerun `hcloud configure list` to verify

### Issue: Domain Not Found (404)

**Symptom**: `ShowDomainDetailByName` returns `error_code: CDN.0171` or 404

**Resolution**:
1. Verify the domain name spelling
2. Confirm the domain has been onboarded to CDN under the current account
3. Confirm you are using the correct account
4. Run `hcloud CDN ListDomains/v2 --cli-region=<region> --page_size=100` to view all onboarded domains

### Issue: Permission Denied (403)

**Symptom**: `ShowDomainDetailByName` returns 403 or a permission denied error

**Resolution**:
1. Check whether the IAM user has the `cdn:domain:get` permission
2. Confirm the AK/SK belongs to the correct account
3. Contact the primary account administrator to grant CDN domain query permission
4. See [iam-policies.md](iam-policies.md) for details

### Issue: API Call Failed

**Symptom**: `ShowDomainDetailByName` or `ShowIpInfo/v2` returns a non-200 response or an abnormal error

**Resolution**:
1. Degrade to probe results only (if `dns_resolve.py` succeeded, provide the IP list from `data.resolved_ips` but attribution cannot be determined)
2. Note in the report "API query failed; only probe results provided; manually verify IP attribution"
3. Check whether the hcloud version is >= 3.2.0
4. Check the network connection

### Issue: dns_resolve.py Probe Timeout

**Symptom**: `dns_resolve.py` returns JSON with `error.reason == "dns_timeout"` (the query did not complete within the `--timeout` lifetime, default 10s)

**Resolution**:
1. Return partial results, mark "DNS probe timeout; manual verification recommended"
2. Check the local network connection
3. Re-run the probe after switching the host's system DNS resolver (e.g., to `8.8.8.8` or `114.114.114.114`) and re-invoke `python scripts/dns_resolve.py --domain <domain_name> --timeout 10`
4. Check the local DNS configuration (`/etc/resolv.conf` or Windows network DNS settings)

### Issue: dns_resolve.py Returns NXDOMAIN (Domain Does Not Exist)

**Symptom**: `dns_resolve.py` returns JSON with `error.reason == "dns_nxdomain"`

**Resolution**:
1. The domain does not exist in DNS (authoritative server returned NXDOMAIN)
2. Verify the domain name spelling and that the domain is registered
3. Confirm the authoritative DNS server for the domain is correctly configured
4. If the domain is expected to exist, the local resolver cache may be stale; flush DNS cache and retry

### Issue: dns_resolve.py Returns No A Records

**Symptom**: `dns_resolve.py` returns JSON with `error.reason == "dns_no_answer"` and `resolved_ips == []`

**Resolution**:
1. The domain exists but has no A records at the queried name
2. The domain may only have a CNAME, TXT, or other record type (this skill only verifies A records)
3. Check whether the domain has an A record or a CNAME chain that ultimately resolves to an A record pointing to CDN
4. Report "No A records found; check DNS configuration"

### Issue: dns_resolve.py Returns Empty (Domain Not Resolved)

**Symptom**: `dns_resolve.py` returns JSON with `resolved_ips == []` and `error == null`

**Resolution**:
1. The domain resolved but returned no usable IPv4 addresses
2. Check whether the domain has an A record or CNAME record pointing to CDN
3. Report "Domain not resolved; check DNS configuration: add a CNAME record pointing the domain to `<cname>`"
4. Confirm the authoritative DNS server for the domain is correctly configured

### Issue: Missing dnspython Library

**Symptom**: `dns_resolve.py` exits with code 2 and returns JSON with `error.reason == "missing_library"`; message names `dnspython`

**Resolution**:
1. Install the library: `pip install dnspython>=2.1`
2. Verify the import: `python -c "import dns.resolver; print('dnspython ok')"`
3. See [cli-installation-guide.md](cli-installation-guide.md) for details

### Issue: Invalid --domain Argument

**Symptom**: `dns_resolve.py` exits with code 2 and returns JSON with `error.reason == "invalid_domain"`

**Resolution**:
1. The `--domain` value failed RFC 1035 validation (length > 253, labels > 63, invalid characters, leading/trailing hyphen)
2. Re-enter the domain name with valid formatting
3. This is a pre-probe validation failure; no DNS query was attempted

### Issue: Invalid --timeout Argument

**Symptom**: `dns_resolve.py` exits with code 2 and returns JSON with `error.reason == "invalid_timeout"`

**Resolution**:
1. The `--timeout` value is outside the allowed range `[1, 30]`
2. Re-run with a value in range; the default is `10`

### Issue: IP List Exceeds 20

**Symptom**: `dns_resolve.py` returns a `data.resolved_ips` array with more than 20 entries

**Resolution**:
1. Only take the first 20 IPs to call ShowIpInfo/v2
2. Note in the report "Actually resolved to N IPs; due to API limit, only the first 20 are verified"
3. If the remaining IPs need to be verified, batch queries or manual sampling are recommended

### Issue: Mixed IP Attribution (False Positive Scenario)

**Symptom**: ShowIpInfo/v2 returns some IPs with belongs=true and some with belongs=false

**Resolution**:
1. Report "Partially resolved to Huawei Cloud CDN, partially not resolved"
2. Prompt "Some regions may have switched; multi-region probing is recommended"
3. Recommend re-running `dns_resolve.py` after switching the host's system DNS resolver to confirm the global resolution status
4. Check for ISP DNS cache or LocalDNS scheduling differences

## Best Practices

### 1. Always Verify Credentials First

Before starting the diagnosis, run `hcloud configure list` to confirm credentials are valid.

### 2. Use Recommended Region

Use `--cli-region=<region>` for CDN APIs to avoid confusion.

### 3. Set Timeout

The DNS probe enforces a 10-second timeout by default:
- `python scripts/dns_resolve.py --domain <domain_name> --timeout 10`
- The `--timeout` argument is optional (default `10`) and accepts range `[1, 30]`

### 4. Do Not Input Credentials in the Conversation

If the user attempts to provide AK/SK in the conversation, refuse immediately and guide them to use `hcloud configure`.

### 5. Multi-Region Probe Verification

If partial resolution or a suspected false positive occurs, re-run `dns_resolve.py` after switching the host's system DNS resolver (e.g., to `8.8.8.8` or `114.114.114.114`) for verification:
```bash
python scripts/dns_resolve.py --domain <domain_name> --timeout 10
```

> Note: `dns_resolve.py` uses the host's configured system resolver and does not
> expose a `--resolver` argument. For targeted resolver testing, switch the host's
> system DNS resolver (e.g., `/etc/resolv.conf`, or 8.8.8.8 / 114.114.114.114) and
> re-run `python scripts/dns_resolve.py --domain <domain_name> --timeout 10`.

## Error Handling Summary

| Scenario | Handling |
|----------|----------|
| Credentials not configured | Abort, prompt to configure credentials |
| Domain not found (404) | Abort, prompt to confirm domain ownership |
| Permission denied (403) | Abort, prompt to contact administrator for authorization |
| API call failed | Degrade to probe results only |
| `dns_resolve.py` `error.reason == "dns_timeout"` | Return partial results, mark timeout |
| `dns_resolve.py` `error.reason == "dns_nxdomain"` | Report domain does not exist |
| `dns_resolve.py` `error.reason == "dns_no_answer"` | Report no A records found |
| `dns_resolve.py` `data.resolved_ips` empty (`data.error == null`) | Report not resolved, prompt to configure DNS CNAME |
| `dns_resolve.py` `error.reason == "missing_library"` (exit 2) | Abort, prompt to install `dnspython>=2.1` |
| IP exceeds 20 | Take the first 20, note the limit in the report |
| Mixed IP attribution | Report partial resolution, prompt multi-region probing |
