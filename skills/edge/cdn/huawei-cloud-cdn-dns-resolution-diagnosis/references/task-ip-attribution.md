# Step 3: IP Attribution Check

Query IP attribution via `ShowIpInfo/v2` to determine whether the domain has been resolved to Huawei Cloud CDN.

## 3.1 Execute IP Attribution Query

**Command**:
```bash
hcloud CDN ShowIpInfo/v2 --cli-region=<region> --ips=<IP1,IP2,...>
```

**Parameter Description**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--ips` | string | Yes | IP list, multiple IPs separated by English commas, **up to 20** |
| `--cli-region` | string | Yes | Region, recommended `cn-north-1` |

**IP List Source**:
- The IP list comes from the `data.resolved_ips` JSON field of `dns_resolve.py` (Step 2)
- The `data.resolved_ips` array is already validated as IPv4 strings by the script
- Join the array elements with English commas to produce the `--ips` value

**IP Count Constraint**:
- At most 20 IPs per query
- If `dns_resolve.py` returns more than 20 IPs in `data.resolved_ips`, only the first 20 are taken (already handled in Step 2)
- Multiple IPs are separated by English commas, no spaces

## 3.2 Attribution Result Decision

**Parsing rule**: the response wraps the results under the top-level key `cdn_ips` (not `ips`); read each IP's `belongs` field from the `cdn_ips[]` array.

**Core Field**: The `belongs` field (boolean) of each IP in `cdn_ips[]`

| Decision Scenario | Condition | Conclusion | Report Status |
|-------------------|-----------|------------|---------------|
| Resolved to Huawei Cloud | All IPs `belongs=true` | Domain correctly resolved to Huawei Cloud CDN | ✅ Pass |
| Not resolved to Huawei Cloud | All IPs `belongs=false` | Domain not resolved to Huawei Cloud CDN | ❌ Fail |
| Partial resolution (false positive) | Some `belongs=true`, some `false` | Partial regions switched, suspected false positive | ⚠️ Warning |
| Empty response | `cdn_ips` is empty (`[]`) | No IPs belong to Huawei Cloud CDN → treat as Not resolved (defensive branch; response may omit non-CDN entries) | ❌ Fail |

## 3.3 Decision Logic Details

### Scenario 1: Resolved to Huawei Cloud (all belongs=true)

- **Meaning**: All resolved IPs belong to Huawei Cloud CDN nodes
- **Conclusion**: Domain correctly resolved to Huawei Cloud CDN, DNS configuration is normal
- **Suggestion**: No remediation needed, DNS configuration is correct

### Scenario 2: Not Resolved to Huawei Cloud (all belongs=false)

- **Meaning**: None of the resolved IPs belong to Huawei Cloud CDN nodes
- **Conclusion**: Domain not resolved to Huawei Cloud CDN
- **Possible Causes**:
  1. DNS CNAME record not configured or not pointing to the CDN CNAME
  2. DNS record misconfigured (e.g., pointing to the origin server or another CDN)
  3. DNS cache not updated
- **Suggestion**: Configure the DNS CNAME record to `<cname>` (obtained in Step 1), wait for DNS to take effect, then retry

### Scenario 3: Partial Resolution (mixed belongs, false positive scenario)

- **Meaning**: Some IPs belong to Huawei Cloud CDN, some do not
- **Conclusion**: Partial regions have switched to Huawei Cloud CDN, some have not
- **Possible Causes**:
  1. LocalDNS scheduling differences (different regions resolve to different IPs)
  2. DNS cache not fully updated
  3. Multi-CDN vendor mixed configuration
  4. DNS round-robin contains old IPs
- **False Positive Prompt**: **Some regions may have switched; multi-region probing is recommended**
- **Suggestion**:
  1. Re-run the DNS probe from a different region or DNS server to confirm the global resolution status:
     switch the system DNS resolver (e.g., `/etc/resolv.conf`, or 8.8.8.8 / 114.114.114.114),
     then re-run `python scripts/dns_resolve.py --domain <domain_name> --timeout 10`
     (this skill's A-record probe does not expose a `--resolver` argument)
  2. Wait for the DNS cache to fully refresh (after TTL expires)

## 3.4 Attribution Statistics

Compute attribution statistics for the report:
- `total_ips`: Total number of IPs queried
- `huawei_ips`: Number of IPs with belongs=true
- `non_huawei_ips`: Number of IPs with belongs=false
- `huawei_ratio`: Huawei Cloud IP ratio (huawei_ips / total_ips)

**Report Detail Examples**:
- All Huawei Cloud: `Detail: 2/2 IPs belong to Huawei Cloud CDN`
- All non-Huawei Cloud: `Detail: 0/2 IPs belong to Huawei Cloud CDN`
- Partial Huawei Cloud: `Detail: 1/2 IPs belong to Huawei Cloud CDN`

## Exception Handling

| Exception Scenario | Handling |
|--------------------|----------|
| API returns 401/403 | Credential or permission issue, see troubleshooting.md |
| API returns 400 (IP format error) | Check IP format; `data.resolved_ips` from `dns_resolve.py` is already IPv4-validated, so this indicates an API-side parsing issue |
| API returns 500 | Server-side error, degrade to probe results only, report "API query failed" |
| API returns partial IP information | Judge only on returned IPs, mark "Partial IP query failed" |
| `cdn_ips` empty (`[]`) | Treat as "No IPs belong to Huawei Cloud CDN → Not resolved" (defensive branch; the response may omit non-CDN entries) |
| `data.resolved_ips` empty (Step 2 not resolved) | Skip this step, generate report directly |

## Example

### All Belong to Huawei Cloud

```bash
$ hcloud CDN ShowIpInfo/v2 --cli-region=<region> --ips=1.2.3.4,5.6.7.8
{
  "cdn_ips": [
    {"ip": "1.2.3.4", "belongs": true, "region": "四川", "isp": "华为云", "platform": "华为云"},
    {"ip": "5.6.7.8", "belongs": true, "region": "广东", "isp": "华为云", "platform": "华为云"}
  ]
}
```

→ 2/2 belongs=true → Resolved to Huawei Cloud ✅

### None Belong to Huawei Cloud

```bash
$ hcloud CDN ShowIpInfo/v2 --cli-region=<region> --ips=10.0.0.1
{
  "cdn_ips": [
    {"ip": "10.0.0.1", "belongs": false}
  ]
}
```

→ 0/1 belongs=true → Not resolved to Huawei Cloud ❌

### Partially Belong to Huawei Cloud (false positive)

```bash
$ hcloud CDN ShowIpInfo/v2 --cli-region=<region> --ips=1.2.3.4,10.0.0.1
{
  "cdn_ips": [
    {"ip": "1.2.3.4", "belongs": true, "region": "四川", "isp": "华为云", "platform": "华为云"},
    {"ip": "10.0.0.1", "belongs": false}
  ]
}
```

→ 1/2 belongs=true → Partial resolution ⚠️, prompt multi-region probing

## Output Forwarding

After this step is complete, the following information is forwarded to report generation:
- `ip_attribution_status`: resolved/not resolved/partially resolved
- `total_ips`: Total number of IPs queried
- `huawei_ips`: Number of IPs belonging to Huawei Cloud
- `non_huawei_ips`: Number of IPs not belonging to Huawei Cloud
- `belongs_details`: Attribution detail of each IP (IP, belongs, region)
- `false_positive_warning`: Whether this is a false positive scenario (true when partially resolved)
