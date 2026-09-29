# Verification Method

Verify the query results are correct and complete.

## Verification Steps

### 1. Verify Credentials

```bash
hcloud configure list
```

Check that the output contains valid configuration (AK/SK, IAM, etc.).

### 2. Verify Domain Exists

```bash
hcloud CDN ListDomains/v2 --cli-region=cn-north-1 --page_size=<page_size> (user-provided) --domain_status=<domain_status> (enum: online, offline, configuring)
```

Check that the target domain is in the returned list.

### 3. Verify Domain ID

```bash
hcloud CDN ShowDomainDetailByName --cli-region=cn-north-1 --domain_name=<your-domain>
```

Check that the returned `domain.id` matches the expected domain_id.

### 4. Verify Statistics Query

Based on the query type, run the corresponding command and check the response:

- **Traffic (flux)**: `ShowDomainStats/v2` with `--stat_type=<stat_type>` (enum: flux, bw, req_num) set to `flux` should return daily traffic values (Byte)
- **Bandwidth (bw)**: `ShowDomainStats/v2` with `--stat_type=<stat_type>` (enum: flux, bw, req_num) set to `bw` should return daily peak bandwidth values (bit/s)
- **95th percentile (bw_95)**: `ShowBandwidthCalc` with `--calc_type=<calc_type>` (enum: bw_95, bw_peak) set to `bw_95` should return a single aggregated value (bit/s)
- **Requests (req_num)**: `ShowDomainStats/v2` with `--stat_type=<stat_type>` (enum: flux, bw, req_num) set to `req_num` should return daily request counts

### 5. Verify Configuration Query

For domain configuration queries:

- **Origin host**: `ShowOriginHost` should return origin_host_type and customize_domain
- **Cache rules**: `ShowCacheRules` should return cache_config with rules array
- **HTTPS certificate**: `ShowHttpInfo` should return certificate details (expiry, content)
- **IP blacklist/whitelist**: `ShowBlackWhiteList` should return IP filter configuration

### 6. Verify Output Format

Check that the output includes:
- Correct JSON structure
- Expected fields present
- No error messages
- Data matches the query time range

## Expected Output Examples

### ListDomains/v2

```json
{
  "total": <count>,
  "domains": [
    {
      "id": "<domain_id>",
      "domain_name": "<your-domain>",
      "domain_status": "<domain_status>",
      "service_area": "<service_area>",
      "business_type": "<business_type>"
    }
  ]
}
```

### ShowDomainStats/v2

```json
{
  "start_time": <ms>,
  "end_time": <ms>,
  "stat_type": "<stat_type>",
  "action": "<action>",
  "interval": <interval>,
  "result": {
    "<stat_type>": [<value>]
  }
}
```

### ShowBandwidthCalc

```json
{
  "bandwidth_calc": {
    "value": <value>,
    "calc_type": "<calc_type>",
    "time_point": <ms>
  }
}
```

## Common Validation Checks

| Check | Expected Result |
|-------|----------------|
| Domain exists | Domain in ListDomains/v2 result |
| Domain ID correct | ShowDomainDetailByName returns matching id |
| Time range valid | No CDN.0202 error |
| Action parameter present | No "缺少必填参数:action" error |
| Stat type correct | Result contains expected metric |
| No rate limit errors | No rate limit error messages |
