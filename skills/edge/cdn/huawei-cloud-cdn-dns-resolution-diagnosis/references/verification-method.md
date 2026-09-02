# Verification Method

Verify the diagnosis results are correct and complete.

## Verification Steps

### 1. Verify Credential Configuration

```bash
hcloud configure list
```

Check the output contains a valid AK/SK configuration (mode=AKSK).

### 2. Verify Domain Permission Check and CNAME Retrieval

```bash
hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=<test_domain>
```

Check the return is 200 and contains the `id`, `domain_name`, `cname` fields, confirming the domain belongs to the current account.

### 3. Verify DNS Resolution Probe

```bash
python scripts/dns_resolve.py --domain <test_domain> --timeout 10
```

Check the JSON output:
- `data.error == null` and `data.resolved_ips` is non-empty → record IP count and address list
- `data.error.reason == "dns_timeout"` → probe timed out
- `data.error.reason == "dns_nxdomain"` → domain does not exist
- `data.error.reason == "missing_library"` (exit code 2) → `dnspython` is not installed

Expected JSON shape on success:
```json
{
  "result": "success",
  "data": {
    "domain": "<test_domain>",
    "resolved_ips": ["1.2.3.4", "5.6.7.8"],
    "duration_ms": 38,
    "error": null
  },
  "error_msg": ""
}
```

### 4. Verify IP Attribution Query

```bash
hcloud CDN ShowIpInfo/v2 --cli-region=<region> --ips=<IP1,IP2,...>
```

Check the returned IP attribution information; each IP should contain the `belongs` field (true/false).

### 5. Verify Report Format

Check the output report includes:
- Analysis time and target domain
- CDN expected CNAME
- IP list resolved by `dns_resolve.py` (from the JSON `data.resolved_ips` field)
- Diagnosis items list (each item contains name, status ✅/❌/⚠️, detail)
- Conclusion and remediation suggestion

## Expected Output

### Scenario 1: Resolved to Huawei Cloud

```
==================== CDN DNS Resolution Diagnosis Report ====================
Analysis Time: 2026-08-12T10:00:00+08:00
Target Domain: www.example.com
Expected CNAME: www.example.com.cdn.net

--- DNS Resolution ---
Resolved IPs: 1.2.3.4, 5.6.7.8

--- Diagnosis Items ---
[Domain Permission Check]: ✅ Pass
  Detail: Domain belongs to the current account, domain_id=xxx
[DNS Resolution Probe]: ✅ Pass
  Detail: Resolved to 2 IPs
[IP Attribution Check]: ✅ Pass
  Detail: 2/2 IPs belong to Huawei Cloud CDN

--- Conclusion ---
Status: Resolved to Huawei Cloud CDN
Suggestion: DNS configuration is correct, no remediation needed
```

### Scenario 2: Not Resolved to Huawei Cloud

```
==================== CDN DNS Resolution Diagnosis Report ====================
Analysis Time: 2026-08-12T10:00:00+08:00
Target Domain: www.example.com
Expected CNAME: www.example.com.cdn.net

--- DNS Resolution ---
Resolved IPs: 10.0.0.1

--- Diagnosis Items ---
[Domain Permission Check]: ✅ Pass
  Detail: Domain belongs to the current account, domain_id=xxx
[DNS Resolution Probe]: ✅ Pass
  Detail: Resolved to 1 IP
[IP Attribution Check]: ❌ Fail
  Detail: 0/1 IPs belong to Huawei Cloud CDN

--- Conclusion ---
Status: Not resolved to Huawei Cloud CDN
Suggestion: Configure the DNS CNAME record to www.example.com.cdn.net, wait for DNS to take effect, then retry
```

### Scenario 3: Partial Resolution (false positive)

```
==================== CDN DNS Resolution Diagnosis Report ====================
Analysis Time: 2026-08-12T10:00:00+08:00
Target Domain: www.example.com
Expected CNAME: www.example.com.cdn.net

--- DNS Resolution ---
Resolved IPs: 1.2.3.4, 10.0.0.1

--- Diagnosis Items ---
[Domain Permission Check]: ✅ Pass
  Detail: Domain belongs to the current account, domain_id=xxx
[DNS Resolution Probe]: ✅ Pass
  Detail: Resolved to 2 IPs
[IP Attribution Check]: ⚠️ Warning
  Detail: 1/2 IPs belong to Huawei Cloud CDN

--- Conclusion ---
Status: Partially resolved to Huawei Cloud CDN
Suggestion: Some regions may have switched; multi-region probing is recommended to confirm the global resolution status
```
