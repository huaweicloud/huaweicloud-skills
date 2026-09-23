---
name: huawei-cloud-waf-log-analysis
description: Analyze Huawei Cloud WAF security event logs to identify attack patterns, top sources, targeted assets, and provide actionable protection rule recommendations. Use when the user asks about recent attacks, WAF alert investigation, security posture review, attack trend analysis, or needs guidance on configuring protection rules based on observed threats. Triggers include "analyze WAF logs", "WAF attack analysis", "security event report", "what attacks happened", "WAF alert investigation", "recommend protection rules", "attack source analysis", "WAF安全日志分析", "攻击事件分析", "防护规则推荐".
tags: [waf, security, log-analysis, attack-detection, rule-recommendation]
---

# Huawei Cloud WAF Security Event Log Analysis

## Overview

This skill provides read-only analysis of Huawei Cloud WAF (Web Application Firewall) security event logs. It queries attack event data through hcloud CLI, performs multi-dimensional aggregation and analysis, and generates actionable protection rule recommendations based on observed attack patterns.

**Key Capabilities:**
- Query and filter security events by attack type, source IP, target domain/URL, time range, and geography
- Aggregate statistics by attack category, source IP frequency, geographic distribution, and time trends
- Recommend specific WAF protection rules (precise access control, CC protection, IP blacklist/whitelist, geo-blocking) based on analyzed attack characteristics

**Applicable Scenarios:**
- Daily security patrol and attack posture review
- Incident response after receiving WAF alerts
- Periodic security reports (weekly/monthly attack trends)
- Anomaly investigation when suspicious activity is detected
- Protection hardening decisions after attack events

## ⚠️ Read-Only Principle — STRICTLY ENFORCED

**This skill is a READ-ONLY analysis skill.** The agent must follow these rules without exception:

| Action | Allowed? | Explanation |
|--------|----------|-------------|
| Query events (`ListEvent`, `ShowEvent`) | ✅ YES | Read-only data retrieval |
| Query policies/hosts (`ListPolicy`, `ShowPolicy`, `ListHost`) | ✅ YES | Read-only data retrieval |
| Aggregate and analyze event data | ✅ YES | Core analysis work |
| Output recommended hcloud commands | ✅ YES | Provide copy-paste ready commands for the user |
| Execute `Create*` / `Update*` / `Delete*` commands | ❌ **NEVER** | These modify production resources; the user decides when and whether to run them |
| Auto-execute any write operation based on analysis findings | ❌ **NEVER** | Even if the recommendation seems obvious, do NOT run it |

**What the agent MUST do:**
1. Perform read-only queries and analysis
2. Generate a structured report with prioritized recommendations
3. For each recommendation, output the **exact, copy-paste ready hcloud command** that the user can execute themselves
4. Clearly label each command with its purpose and expected effect

**What the agent MUST NOT do:**
1. Execute any command that creates, modifies, or deletes WAF resources
2. Ask the user "should I execute this for you?" — just present the command and let the user decide
3. Proceed to execute recommendations after presenting them — stop after the report is delivered

## Prerequisites

| Requirement | Description |
|-------------|-------------|
| **hcloud CLI** | v7.2+ installed and configured with AK/SK, region, and project ID |
| **Project ID** | Valid project ID (configured via `hcloud configure set --cli-project-id=<id>`) |
| **IAM Permissions** | See `references/iam-policies.md` for least-privilege policy |
| **Network** | Accessible network path to Huawei Cloud API endpoints |

## ⚠️ Windows PowerShell Compatibility — STRICTLY ENFORCED

This skill runs on **Windows PowerShell**. The agent MUST NOT use Linux/Unix shell commands. Use PowerShell-native equivalents at all times.

| ❌ Linux command (NEVER use) | ✅ PowerShell equivalent | Example |
|------------------------------|------------------------|---------|
| `head -N` | `Select-Object -First N` | `... \| Select-Object -First 30` |
| `tail -N` | `Select-Object -Last N` | `... \| Select-Object -Last 30` |
| `grep "pattern"` | `Select-String "pattern"` | `... \| Select-String "error"` |
| `wc -l` | `(... ).Count` or `(Measure-Object -Line).Lines` | `$items.Count` |
| `sort` | `Sort-Object` | `... \| Sort-Object Count -Descending` |
| `uniq` | `Get-Unique` or `Group-Object` | `... \| Group-Object` |
| `awk '{print $1}'` | `ForEach-Object { $_.field }` | `$items \| ForEach-Object { $_.sip }` |
| `cut -d: -f1` | `Split-Path`, `-split`, or `Substring` | `($_ -split ':')[0]` |
| `sed 's/a/b/'` | `-replace` operator | `'text' -replace 'a','b'` |
| `cat file` | `Get-Content file` | `Get-Content "$env:TEMP\data.json" -Raw` |
| `echo "text"` | `Write-Host "text"` | `Write-Host "Processing..."` |
| `export VAR=value` | `$env:VAR="value"` | `$env:HTTP_PROXY="http://127.0.0.1:3128"` |
| `sleep N` | `Start-Sleep -Seconds N` | `Start-Sleep -Seconds 2` |

**Additional rules:**
- Always use `Out-File -Encoding utf8` instead of `> file` for redirecting output (avoids encoding issues)
- Use double quotes `"` around variable expansions inside strings: `"Total: $($items.Count)"`
- Pipe hcloud JSON output to `ConvertFrom-Json` for structured analysis: `hcloud WAF ListEvent ... \| ConvertFrom-Json`

## Workflow

### Step 1: Clarify Analysis Scope

Ask the user for the following parameters (defaults provided):

| Parameter | Default | Options |
|-----------|---------|---------|
| Time range | `today` | `today`, `yesterday`, `3days`, `1week`, `1month` |
| Domain filter | All domains | Specific domain name or leave empty |
| Attack type filter | All types | `sqli`, `xss`, `cc`, `botm`, `cmdi`, `robot`, etc. |
| Analysis focus | General overview | Attack type stats, IP analysis, target analysis, time trends, rule recommendation |
| **Data volume** | **First page (100)** | See options below |

**Data Volume Options:**

| Option | Description | When to use |
|--------|-------------|-------------|
| `first_page` (default) | Query first 100 events only, fastest | Quick glance at recent activity |
| `sample_pages` | Query N pages of events; **N must be explicitly specified by the user — agent has NO default** | Balanced speed vs coverage |
| `all_pages` | Paginate through ALL results up to 10,000 | Comprehensive analysis, may take several minutes |
| `by_attack_type` | First query to discover attack types, then query top N types separately (each gets its own first page) | Best attack-type diversity, avoids single-type bias |

> ⚠️ **IMPORTANT — Data Volume Selection (STRICTLY ENFORCED):**
> - The agent MUST ask the user which data volume option to use. Do NOT silently default to any option.
> - If user chooses `sample_pages`, the agent MUST ask the user how many pages (N) to fetch. **There is NO default value for N.** The agent must NOT assume or default to any number (e.g., 5). Ask explicitly: "你想采样多少页？（每页100条事件）"
> - If total events > 100 and user chose `first_page`, warn them that the sample may not represent the full picture.

### Step 2: Query Security Events

#### Step 2a: Get Total Count First

Always start with a single lightweight query to determine total event count:

```bash
hcloud WAF ListEvent --recent={time_range} --pagesize=1 --page=1
```

Read the `total` field from the response. This tells you how much data exists before committing to a fetching strategy.

#### Step 2b: Fetch Data Based on User's Choice

Based on the user's data volume selection, execute the corresponding strategy:

**Strategy: `first_page` (default)**

Fetch one page of 100 events:

```bash
hcloud WAF ListEvent --recent={time_range} --pagesize=100 --page=1 --sort_key=attack
```

Save result to file:

```powershell
hcloud WAF ListEvent --recent={time_range} --pagesize=100 --page=1 --sort_key=attack | Out-File -Encoding utf8 "$env:TEMP\waf_events.json"
```

If `total` > 100, display a warning to the user:
> "Total events: {total}. This analysis is based on 100 events (1%). Results may not represent the full picture."

**Strategy: `sample_pages` (user specifies N)**

Loop through N pages, appending each page's items to a combined file:

```powershell
$pages = {N}   # e.g., 5
for ($p = 1; $p -le $pages; $p++) {
    hcloud WAF ListEvent --recent={time_range} --pagesize=100 --page=$p --sort_key=attack | Out-File -Encoding utf8 "$env:TEMP\waf_events_page$p.json"
}

# Merge all pages into one file for unified analysis
$allItems = @()
for ($p = 1; $p -le $pages; $p++) {
    $raw = Get-Content "$env:TEMP\waf_events_page$p.json" -Raw
    $data = $raw | ConvertFrom-Json
    $allItems += $data.items
}
$merged = @{ total = $data.total; items = $allItems } | ConvertTo-Json -Depth 10
$merged | Out-File -Encoding utf8 "$env:TEMP\waf_events_all.json"
Write-Host "Merged $($allItems.Count) events from $pages pages"
```

**Strategy: `all_pages`**

Keep paginating until all events are fetched or 10,000 cap reached:

```powershell
$allItems = @()
$page = 1
$total = 0
do {
    $raw = hcloud WAF ListEvent --recent={time_range} --pagesize=100 --page=$page --sort_key=attack
    $data = $raw | ConvertFrom-Json
    $total = $data.total
    $allItems += $data.items
    Write-Host "Fetched page $page / $([math]::Ceiling($total / 100)) ($($allItems.Count) / $total events)"
    $page++
} while ($data.items.Count -eq 100 -and $allItems.Count -lt 10000)

$merged = @{ total = $total; items = $allItems } | ConvertTo-Json -Depth 10
$merged | Out-File -Encoding utf8 "$env:TEMP\waf_events_all.json"
Write-Host "Total fetched: $($allItems.Count) events"
```

> ⚠️ With 10,000 events this requires ~100 API calls and may take 5-10 minutes. Consider using `by_attack_type` instead for faster diverse coverage.

**Strategy: `by_attack_type`**

Step 1 — Discover attack types by querying first page sorted by attack:

```powershell
$raw = hcloud WAF ListEvent --recent={time_range} --pagesize=100 --page=1 --sort_key=attack
$data = $raw | ConvertFrom-Json
$attackTypes = $data.items | Group-Object attack | Sort-Object Count -Descending
$attackTypes | ForEach-Object { Write-Host ("{0,-30} {1}" -f $_.Name, $_.Count) }
```

Step 2 — For the top N attack types discovered (default N=5), query each separately:

```powershell
foreach ($atk in $attackTypes | Select-Object -First {N}) {
    $type = $atk.Name
    hcloud WAF ListEvent --recent={time_range} --attacks.1=$type --pagesize=100 --page=1 | Out-File -Encoding utf8 "$env:TEMP\waf_events_attack_$type.json"
    Write-Host "Fetched 100 events for attack type: $type"
}
```

Step 3 — Merge all per-type files into one combined dataset:

```powershell
# Clean up old attack type files to avoid mixing with previous runs
Remove-Item "$env:TEMP\waf_events_attack_*.json" -ErrorAction SilentlyContinue

$allItems = @()
foreach ($file in Get-ChildItem "$env:TEMP\waf_events_attack_*.json") {
    $raw = Get-Content $file.FullName -Raw
    $data = $raw | ConvertFrom-Json
    if ($data.items) { $allItems += $data.items }
}
$merged = @{ total = "multi-type-sample"; items = $allItems } | ConvertTo-Json -Depth 10
$merged | Out-File -Encoding utf8 "$env:TEMP\waf_events_all.json"
Write-Host "Combined dataset: $($allItems.Count) events across multiple attack types"
```

#### Common Query Examples

```bash
# Filter by source IP
hcloud WAF ListEvent --recent={time_range} --sip={source_ip} --pagesize=100

# ⚠️ WARNING: --domain conflicts with KooCLI system parameter and will prompt interactively
# DO NOT use --domain in automated scripts; see workaround below
# hcloud WAF ListEvent --recent={time_range} --domain={domain} --pagesize=100

# Sort by different dimensions
hcloud WAF ListEvent --recent={time_range} --sort_key=sort_ip --pagesize=100
hcloud WAF ListEvent --recent={time_range} --sort_key=attack --pagesize=100
```

> **⚠️ --domain Parameter Conflict:** The `--domain` parameter name conflicts with KooCLI's system parameter. Using it directly triggers an interactive prompt asking to choose between system/API parameter, which hangs non-interactive environments (e.g., Bash tool, automation scripts).
>
> **Solution — Use `--cli-jsonInput` to bypass the conflict:**
> ```powershell
> # Step 1: Create a JSON file with query parameters
> $jsonContent = @'
> {
>   "path": {
>     "project_id": "{project_id}"
>   },
>   "query": {
>     "recent": "today",
>     "domain": "{domain}",
>     "pagesize": 100,
>     "page": 1
>   }
> }
> '@
> $jsonContent | Out-File -FilePath "$env:TEMP\listevent_domain.json" -Encoding ASCII
>
> # Step 2: Execute with --cli-jsonInput
> hcloud WAF ListEvent --cli-jsonInput="$env:TEMP\listevent_domain.json" | Out-File -Encoding utf8 "$env:TEMP\domain_result.json"
>
> # Step 3: Parse result (skip hcloud's warning message)
> $raw = Get-Content "$env:TEMP\domain_result.json" -Raw
> $jsonStart = $raw.IndexOf('{')
> $data = $raw.Substring($jsonStart) | ConvertFrom-Json
> Write-Host "Filtered $($data.items.Count) events for domain: {domain}"
> ```
>
> **Note:** `project_id` can be obtained from `hcloud configure list` or from previous API responses. hcloud outputs a warning message before JSON when using `--cli-jsonInput`, so use file redirect and skip to the first `{` character when parsing.

**Important:**
- Maximum 10,000 records per query; narrow time range if exceeded
- **`--pagesize` parameter**: Valid range is [0, total_data]. Default to 100 if user doesn't specify. Use user's value when provided. If API returns error `WAF.00011011: pageOrPageSize.illegal`, inform the user that their pagesize value is too large and ask them to enter a smaller value within the valid range
- Paginate through results if total count > pagesize (use multiple queries with `--page=1`, `--page=2`, etc.)
- Use `--from` and `--to` (millisecond timestamps) for custom time ranges (max 30 days)
- Always save multi-page results to a merged file before analysis to avoid PowerShell variable scope issues

### Step 3: Multi-Dimensional Analysis

**⚠️ PowerShell Variable Scope Warning:** Each Bash tool invocation runs in an isolated session — variables do NOT persist across calls. You MUST either:
- Load and analyze data in the **same command block**, OR
- Save query results to a file first, then reload from file in subsequent analysis commands

```powershell
# ❌ WRONG - Variables don't persist across Bash calls
# Call 1: $items = hcloud WAF ListEvent ... | ConvertFrom-Json
# Call 2: $items | Group-Object attack  # ERROR: $items is empty!

# ✅ CORRECT Option 1 - Single command block
$items = (hcloud WAF ListEvent --recent=today --pagesize=100 --page=1).items | ConvertFrom-Json
$items | Group-Object attack | Sort-Object Count -Descending | Select-Object Count, Name

# ✅ CORRECT Option 2 - Save to file, reload later
# Call 1: hcloud WAF ListEvent ... | Out-File -Encoding utf8 "$env:TEMP\waf_events.json"
# Call 2: $items = (Get-Content "$env:TEMP\waf_events.json" -Raw | ConvertFrom-Json).items
#         $items | Group-Object attack
```

Aggregate the queried events across the following dimensions:

#### 3a. Attack Type Distribution

Count events by `attack` field. Map attack codes to human-readable names:

| Code | Name | Recommended Rule Type |
|------|------|----------------------|
| `sqli` | SQL Injection | `CreateCustomRule` / `UpdatePolicy --options.webattack=true` |
| `xss` | XSS Attack | `CreateCustomRule` / `UpdatePolicy --options.webattack=true` |
| `cc` | CC Attack | `CreateCcRule` |
| `botm` | BOT Attack | `CreateAnticrawlerRule` (需先调用 `UpdateAnticrawlerRuleType`) / `UpdatePolicy --options.bot_enable=true` + enable specific detectors: `crawler_scanner`, `crawler_script`, `crawler_engine`, `crawler_other` |
| `cmdi` | Command Injection | `CreateCustomRule` / `UpdatePolicy --options.webattack=true` |
| `rfi` | Remote File Inclusion | `CreateCustomRule` / `UpdatePolicy --options.webattack=true` |
| `rce` | Remote Code Execution | `CreateCustomRule` / `UpdatePolicy --options.webattack=true` |
| `lfi` | Local File Inclusion | `CreateCustomRule` / `UpdatePolicy --options.webattack=true` |
| `ptr` | Directory Traversal | `CreateCustomRule` (match `../` payload) / `UpdatePolicy --options.webattack=true` |
| `robot` | Malicious Crawler | `CreateAnticrawlerRule` (需先调用 `UpdateAnticrawlerRuleType`) / `UpdatePolicy --options.bot_enable=true` + `--options.crawler_scanner=true` + `--options.crawler_script=true` + `--options.crawler_engine=true` + `--options.crawler_other=true` |
| `webshell` | Webshell | `UpdatePolicy --options.webshell=true` / `CreateCustomRule` |
| `vuln` | Other Vulnerability | `UpdatePolicy --options.webattack=true` / `CreateCustomRule` |
| `custom_whiteblackip` | IP Blacklist/Whitelist | Already using `CreateWhiteblackipRule` |
| `custom_geoip` | Geo Access Control | Already using `CreateGeoipRule` |
| `custom_custom` | Precise Protection | Already using `CreateCustomRule` |
| `iprank` | IP Reputation | `CreateIpReputationRule` |
| `antiscan_high_freq_scan` | High-frequency Scan | `CreateCcRule` / `UpdatePolicy --options.modulex_enabled=true --modulex_options.global_rate_enabled=true` |
| `antitamper` | Anti-tamper | `CreateAntiTamperRule` + `UpdatePolicy --options.antitamper=true` |
| `anticrawler` | Anti-crawler | `CreateAnticrawlerRule` + `UpdatePolicy --options.anticrawler=true` |
| `followed_action` | Attack Punishment | `CreatePunishmentRule` + `UpdatePolicy --options.followed_action=true` |
| `antileakage` | Sensitive Data Leakage | `CreateAntileakageRule` + `UpdatePolicy --options.antileakage=true` |
| `custom_robot` | Scanner Crawler | `CreateCustomRule` (User-Agent matching) / `CreateAnticrawlerRule` |
| `advanced_bot` | Advanced BOT | `UpdatePolicy --options.bot_enable=true` + `CreateAnticrawlerRule` |

#### 3b. Source IP Analysis

Group by `sip` (source IP) field, sorted by frequency:
- Identify top attacking IPs (>5 hits in analysis period)
- Cross-reference with `ip_countries` and `ip_regions` for geographic distribution
- Flag IPs from unexpected countries

#### 3c. Target Asset Analysis

Group by `host` (domain) and `url` fields:
- Identify most-targeted domains
- Identify most-targeted URL paths
- Correlate attack types with specific URLs

#### 3d. Time Trend Analysis

The `time` field in API responses is a **Unix millisecond timestamp** (e.g., `1789696805000`). It MUST be converted using `[DateTimeOffset]::FromUnixTimeMilliseconds()`:

```powershell
# CORRECT - Convert Unix millisecond timestamp to local time
$items | ForEach-Object {
    [DateTimeOffset]::FromUnixTimeMilliseconds([long]$_.time).LocalDateTime.ToString("yyyy-MM-dd HH")
} | Group-Object | Sort-Object Name | Select-Object Count, Name

# WRONG - FromFileTimeUtc expects Windows FILETIME (epoch 1601-01-01),
#         passing a Unix timestamp will produce dates around year 1601
[DateTime]::FromFileTimeUtc($_.time)
```

Aggregate the converted timestamps by hour:
- Identify peak attack periods
- Determine if attacks are sustained or burst-type
- Compare with normal traffic baseline if available

#### 3e. Action Distribution

Group by `action` field (protection action taken):
- Count events by action type: `block`, `pass`, `log`, `captcha`, `cache`, `mask`, `js_challenge`, `advanced_captcha`, `abort_response`, `desensitize`
- Calculate block rate vs pass rate to assess protection effectiveness
- Identify rules that are in "log only" mode and should be escalated to "block"

### Step 4: View Detailed Events (if needed)

For deeper investigation of specific events:

```bash
hcloud WAF ShowEvent --eventid={event_id}
```

The detail view includes: full request headers, payload content, matched rule ID, and action taken.

> **⚠️ Timeout Warning:** `ShowEvent` may fail with `[USE_ERROR]调用API超时` if:
> - The event is old and data retrieval is slow
> - The API endpoint is under heavy load
>
> **Troubleshooting steps:**
> 1. Increase read timeout: `hcloud configure set --cli-read-timeout=60`
> 2. Try a more recent event ID (older events may have been archived)
> 3. If timeout persists, the detailed event data can often be found in the original `ListEvent` response's `response_body`, `headers`, and other fields — use that as a fallback

### Step 5: Generate Protection Rule Recommendations

Based on the analysis results, recommend specific WAF protection rules **with executable hcloud commands**. See `references/rule-recommendation-guide.md` for detailed mapping logic and full command reference.

**Quick Reference — Attack Pattern → Rule Recommendation → hcloud Command:**

| Observed Pattern | Recommended Action | Rule Type |
|-----------------|-------------------|-----------|
| High-volume requests from single IP to same URL | CC protection rule (rate limiting by IP + URL) | `CreateCcRule` |
| SQL injection attempts targeting specific URL | Precise access control rule (URL contains + block sqli payload pattern) | `CreateCustomRule` |
| Attacks from specific country IPs | Geo access control rule (block specific countries) | `CreateGeoipRule` |
| Repeated attacks from known malicious IPs | IP blacklist rule | `CreateWhiteblackipRule` |
| BOT/scanner user-agent patterns | Precise access control rule (User-Agent matching) | `CreateCustomRule` |
| Attacks on admin/api paths | Precise access control rule (URL path restriction) | `CreateCustomRule` |
| Multiple attack types from same IP subnet | IP group blacklist rule | `CreateWhiteblackipRule` |
| Malicious crawler/scanner traffic (`robot`) | JS anti-crawler rule (User-Agent matching) | `CreateAnticrawlerRule` |
| IDC datacenter malicious IP (`iprank`) | IP reputation rule (threat intelligence) | `CreateIpReputationRule` |
| Web content tampering (`antitamper`) | Anti-tamper rule (URL protection) | `CreateAntiTamperRule` |
| Persistent attacker blocking (`followed_action`) | Punishment rule (auto-block after threshold) | `CreatePunishmentRule` |
| Sensitive data in responses | Anti-leakage rule (filter phone/id_card/email) | `CreateAntileakageRule` |
| Webshell upload/access (`webshell`) | Enable webshell detection module | `UpdatePolicy --options.webshell=true` |
| Directory traversal (`ptr`) / Other vuln (`vuln`) | Enable basic protection + custom rule for payload | `UpdatePolicy --options.webattack=true` |
| High-frequency scan (`antiscan_high_freq_scan`) | CC protection or modulex scan protection | `CreateCcRule` / `UpdatePolicy` |

After determining the recommendation, **output the corresponding hcloud command as a code block** for the user to copy and execute themselves. **Do NOT execute the command.** Use the policy_id extracted from the event data (the `policyid` field). See below for command templates per pattern:

#### 5a. IP Blacklist — Block Malicious Source IP

```bash
hcloud WAF CreateWhiteblackipRule   --policy_id={policy_id} \
  --name={rule_name} \
  --addr={source_ip} \
  --white=0
```

Parameters:
- `--white=0` → blacklist (block), `--white=1` → whitelist (allow), `--white=2` → log only
- `--addr` supports single IP or CIDR (e.g., `203.0.113.0/24`)
- Verify: `hcloud WAF ListWhiteblackipRule --policy_id={policy_id} --page=1 --pagesize=10`

#### 5b. CC Protection — Rate Limiting

> ⚠️ `--mode` conflicts with KooCLI system parameter. Must use `--cli-jsonInput`.

Create a temporary JSON file (e.g., `cc-rule.json`):
```json
{
  "path": {
    "project_id": "{project_id}",
    "policy_id": "{policy_id}"
  },
  "query": {},
  "body": {
    "name": "{rule_name}",
    "mode": 1,
    "tag_type": "ip",
    "limit_num": 100,
    "limit_period": 60,
    "lock_time": 300,
    "action": {
      "category": "block"
    }
  }
}
```

**Note:** `{project_id}` is the same one configured in hcloud CLI (via `hcloud configure set --cli-project-id=<id>`). Check current value with `hcloud configure list`.

Then execute:
```bash
hcloud WAF CreateCcRule --cli-jsonInput=cc-rule.json
```

Parameters:
- `tag_type`: `ip` (by source IP), `url` (by URL path), `cookie` (by cookie), `header` (by header)
- `limit_num` / `limit_period`: threshold count within time window (seconds)
- `lock_time`: block duration (seconds) after threshold exceeded
- `action.category`: `block`, `captcha`, `redirect`
- Verify: `hcloud WAF ListCcRules --policy_id={policy_id}`

#### 5c. Precise Access Control — Custom Rule

```bash
hcloud WAF CreateCustomRule   --policy_id={policy_id} \
  --name={rule_name} \
  --action.category=block \
  --conditions.1.category={field_category} \
  --conditions.1.logic_operation={logic_op} \
  --conditions.1.contents.1={match_value} \
  --priority=50 \
  --time=false
```

Common condition configurations:

| Scenario | `category` | `index` (if needed) | `logic_operation` | `contents.1` |
|----------|------------|---------------------|--------------------|--------------|
| Match URL path | `url` | — | `contain` | `/admin` |
| Match User-Agent | `user-agent` | — | `contain` | `python-requests` |
| Match Header value | `header` | `X-Custom-Header` | `equal` | `malicious-value` |
| Match Cookie | `cookie` | `session_id` | `contain` | `value` |
| Match IP source | `ip` | — | `equal` | `203.0.113.1` |
| Match request method | `method` | — | `equal` | `POST` |
| Match payload | `params` | — | `contain` | `<script>` |

Additional parameters:
- `--conditions.N.index={field_name}` — Required when `category` is `header`, `cookie`; NOT `field`
- `--time=false` — Immediate effect; do NOT use `--status`
- `--priority=N` — Range 0~65535, lower = higher priority
- Multi-condition AND: add `--conditions.2.category=...` etc.
- Logic operations: `contain`, `not_contain`, `equal`, `not_equal`, `prefix`, `suffix`, `regex`, `none`
- Verify: `hcloud WAF ListCustomRules --policy_id={policy_id}`

#### 5d. Geo Access Control — Block by Country

```bash
hcloud WAF CreateGeoipRule   --policy_id={policy_id} \
  --name={rule_name} \
  --geoip={country_code} \
  --white=0
```

Parameters:
- `--geoip` — ISO 3166-1 alpha-2 country code (e.g., `KP`, `IR`, `CU`)
- `--white=0` → block traffic from this country
- **Caution**: Always confirm with user that no legitimate business traffic comes from the blocked countries before recommending geo-blocking
- Verify: `hcloud WAF ListGeoipRule --policy_id={policy_id}`

#### 5e. Update Basic Protection Policy — Change Action from Log to Block

If events show `action=log` for attack types that should be blocked:

```bash
# View current policy settings
hcloud WAF ShowPolicy --policy_id={policy_id}

# Change protection action to block
hcloud WAF UpdatePolicy   --policy_id={policy_id} \
  --action.category=block

# Or raise protection level (1=loose, 2=medium, 3=strict)
hcloud WAF UpdatePolicy   --policy_id={policy_id} \
  --level=3
```

Note: `UpdatePolicy` can also enable/disable built-in protection modules via `--options.*` parameters (see 5k below).

#### 5f. Anticrawler Rule — Block Malicious Crawlers (`robot` / `anticrawler`)

> ⚠️ Must call `UpdateAnticrawlerRuleType` to set protection mode **before** creating anticrawler rules.

```bash
# Step 1: Set anticrawler protection mode (required prerequisite)
hcloud WAF UpdateAnticrawlerRuleType   --policy_id={policy_id} \
  --anticrawler_type=anticrawler_except_url

# Step 2: Create anticrawler rule
hcloud WAF CreateAnticrawlerRule   --policy_id={policy_id} \
  --name={rule_name} \
  --type=anticrawler_except_url \
  --conditions.1.category=user-agent \
  --conditions.1.logic_operation=contain \
  --conditions.1.contents.1={scanner_signature} \
  --priority=20
```

Parameters (verified via `--help`):
- `--anticrawler_type` / `--type`: `anticrawler_except_url` (protect all paths, rule = exclusion) or `anticrawler_specific_url` (protect specified paths only)
- `--conditions.N.category`: `url` or `user-agent`
- `--conditions.N.logic_operation`: `contain`, `not_contain`, `equal`, `prefix`, `suffix`, `regular_match`, etc.
- `--priority`: 0~65535, lower = higher priority
- Verify: `hcloud WAF ListAnticrawlerRules --policy_id={policy_id} --page=1 --pagesize=10`

#### 5g. IP Reputation Rule — Block Malicious IP Sources (`iprank`)

```bash
hcloud WAF CreateIpReputationRule   --policy_id={policy_id} \
  --name={rule_name} \
  --type=idc \
  --action.category=block \
  --tags.1={threat_tag}
```

Parameters (verified via `--help`):
- `--type`: Currently only supports `idc` (IDC data center IP)
- `--action.category`: `block` (拦截), `log` (仅记录), `pass` (放行)
- `--tags.N`: Threat intelligence tags (obtain from `ListIpReputationRules` or threat intel console)
- Verify: `hcloud WAF ListIpReputationRules --policy_id={policy_id} --page=1 --pagesize=10`

#### 5h. Anti-Tamper Rule — Protect Web Content (`antitamper`)

```bash
hcloud WAF CreateAntiTamperRule   --policy_id={policy_id} \
  --hostname={protected_domain} \
  --url={protected_url} \
  --description={rule_description}
```

Parameters (verified via `--help`):
- `--hostname`: Protected domain (from `ListHost` response `hostname` field)
- `--url`: Protected URL path, e.g., `/admin/index.html` or `/static/*` (`*` suffix = prefix match)
- `--description`: Optional rule description
- Verify: `hcloud WAF ListAntitamperRule --policy_id={policy_id} --page=1 --pagesize=10`
- Note: Must also enable the module: `hcloud WAF UpdatePolicy --policy_id={policy_id} --options.antitamper=true`

#### 5i. Punishment Rule — Block Persistent Attackers (`followed_action`)

```bash
hcloud WAF CreatePunishmentRule   --policy_id={policy_id} \
  --category={punishment_category} \
  --block_time={block_seconds} \
  --time_unit={time_unit} \
  --description={rule_description}
```

Parameters (verified via `--help`):
- `--category`: One of:
  - `short_ip_block` / `short_cookie_block` / `short_params_block` / `short_header_block` — short-term punishment
  - `long_ip_block` / `long_cookie_block` / `long_params_block` / `long_header_block` — long-term punishment
- `--block_time`: Block duration (range depends on category and time_unit):
  - `short_*` + `SECOND`: [1, 300]
  - `long_*` + `SECOND`: [301, 7776000]
  - `long_*` + `MINUTE`: [6, 129600]
  - `long_*` + `HOUR`: [1, 2160]
  - `long_*` + `DAY`: [1, 90]
  - `long_*` + `MONTH`: [1, 3]
- `--time_unit`: `SECOND` (default), `MINUTE`, `HOUR`, `DAY`, `MONTH`
- Note: Each category can only have one rule; category cannot be modified after creation
- Verify: `hcloud WAF ListPunishmentRules --policy_id={policy_id}`
- Note: Must also enable the module: `hcloud WAF UpdatePolicy --policy_id={policy_id} --options.followed_action=true`

#### 5j. Anti-Leakage Rule — Prevent Sensitive Data Exposure

```bash
hcloud WAF CreateAntileakageRule   --policy_id={policy_id} \
  --category={category} \
  --contents.1={content_value} \
  --url={protected_url} \
  --action.category=block \
  --description={rule_description}
```

Parameters (verified via `--help`):
- `--category`: `code` (HTTP status code) or `sensitive` (sensitive information)
- `--contents.N`: 
  - For `code`: HTTP status codes — `400`, `401`, `402`, `403`, `404`, `405`, `500`, `501`, `502`, `503`, `504`, `507`
  - For `sensitive`: `phone` (phone number), `id_card` (ID card), `email`
- `--url`: URL path to apply the rule
- `--action.category`: `block` (filter) or `log` (record only)
- Verify: `hcloud WAF ListAntileakageRules --policy_id={policy_id} --page=1 --pagesize=10`
- Note: Must also enable the module: `hcloud WAF UpdatePolicy --policy_id={policy_id} --options.antileakage=true`

#### 5k. Enable/Disable Built-in Protection Modules

Use `UpdatePolicy` with `--options.*` to toggle built-in protection modules:

```bash
# View current module status
hcloud WAF ShowPolicy --policy_id={policy_id}

# Enable webshell detection
hcloud WAF UpdatePolicy   --policy_id={policy_id} \
  --options.webshell=true

# Enable anti-tamper module
hcloud WAF UpdatePolicy   --policy_id={policy_id} \
  --options.antitamper=true

# Enable anticrawler module
hcloud WAF UpdatePolicy   --policy_id={policy_id} \
  --options.anticrawler=true

# Enable attack punishment module
hcloud WAF UpdatePolicy   --policy_id={policy_id} \
  --options.followed_action=true

# Enable anti-leakage module
hcloud WAF UpdatePolicy   --policy_id={policy_id} \
  --options.antileakage=true

# Enable scanner detection (crawler_scanner)
hcloud WAF UpdatePolicy   --policy_id={policy_id} \
  --options.crawler_scanner=true

# Enable script crawler detection
hcloud WAF UpdatePolicy   --policy_id={policy_id} \
  --options.crawler_script=true
```

Full list of `--options.*` parameters (verified via `UpdatePolicy --help`):

| Parameter | Description |
|-----------|-------------|
| `--options.webattack` | Basic web protection (sqli, xss, cmdi, lfi, rfi, vuln) |
| `--options.webshell` | Webshell detection |
| `--options.cc` | CC protection rules |
| `--options.custom` | Precise access control |
| `--options.whiteblackip` | IP blacklist/whitelist |
| `--options.geoip` | Geo access control |
| `--options.antitamper` | Anti-tamper |
| `--options.anticrawler` | Anti-crawler (JS challenge) |
| `--options.antileakage` | Anti-leakage (sensitive data) |
| `--options.followed_action` | Attack punishment |
| `--options.privacy` | Privacy masking |
| `--options.ignore` | Global whitelist (false positive bypass) |
| `--options.crawler_scanner` | Scanner detection |
| `--options.crawler_script` | Script crawler detection |
| `--options.crawler_engine` | Search engine crawler |
| `--options.crawler_other` | Other crawler detection |
| `--options.bot_enable` | BOT management master switch |
| `--options.modulex_enabled` | Intelligent CC (modulex, beta) |

#### 5l. Enable/Disable Single Rule by Status

Toggle individual rules on/off without deleting them:

```bash
hcloud WAF UpdatePolicyRuleStatus   --policy_id={policy_id} \
  --rule_id={rule_id} \
  --rule_type={rule_type} \
  --status={0|1}
```

Parameters (verified via `--help`):
- `--rule_type`: `cc`, `custom`, `whiteblackip`, `geoip`, `ip-reputation`, `antitamper`, `antileakage`, `ignore`, `privacy`
- `--status`: `0` = disable, `1` = enable
- Note: Useful for temporary rule disabling during troubleshooting

#### KooCLI Parameter Pitfalls

| Pitfall | ❌ Wrong | ✅ Correct |
|---------|----------|------------|
| Nested params | `--action=block` | `--action.category=block` |
| Header field name | `--conditions.1.field=UA` | `--conditions.1.index=User-Agent` |
| Immediate effect | `--status=1` | `--time=false` |
| mode conflict | `--mode=1` (direct) | `--cli-jsonInput=file.json` |
| Array index | `--conditions.0.xxx` | `--conditions.1.xxx` (starts from 1) |
| Singular/plural | `ListWhiteblackipRules` | `ListWhiteblackipRule` |
| Case sensitivity | `ShowWhiteblackipRule` | `ShowWhiteBlackIpRule` (capital B) |

### Step 6: Present Analysis Report

Output a structured report containing:

1. **Summary** — Total events, time range, top findings
2. **Attack Type Breakdown** — Counts and percentages
3. **Top Attacking IPs** — With geographic info
4. **Most Targeted Assets** — Domains and URLs
5. **Time Distribution** — Peak periods
6. **Recommended Rules** — Prioritized list with **copy-paste ready hcloud commands** (DO NOT execute them)

**Report Delivery Format:**
```markdown
## 🛡️ Protection Recommendations

### Priority 1: [Rule Name]
**Purpose**: [What this rule does]
**Expected Effect**: [Impact on security posture]

**Command to execute** (copy and run in your terminal):
```bash
hcloud WAF CreateXxxRule --policy_id={policy_id} ...
```

**Verification command** (after you execute the above):
```bash
hcloud WAF ListXxxRule --policy_id={policy_id}
```
```

**Important**: After presenting the report with all recommended commands, **STOP**. Do not ask "should I execute these?" or attempt to run them. The user will decide when and whether to execute the commands.

## Core Commands

| Command | Purpose |
|---------|---------|
| `hcloud WAF ListEvent` | Query attack event list with multi-dimensional filtering, sorting, and pagination |
| `hcloud WAF ShowEvent` | View detailed information of a single attack event |
| `hcloud WAF ListAttackActionTypes --from=<ms_timestamp> --to=<ms_timestamp>` | Aggregate event counts by protection action type (block/log/pass/etc.) within the specified time range |

### ListEvent Key Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `--recent` | string | Quick time range: `today`, `yesterday`, `3days`, `1week`, `1month` |
| `--from` / `--to` | integer | Custom time range (millisecond timestamps), max 30 days |
| `--attacks.N` | array | Filter by attack type: `sqli`, `xss`, `cc`, `botm`, `cmdi`, `rfi`, `rce`, `lfi`, `ptr`, `webshell`, `vuln`, `robot`, `iprank`, `antitamper`, `anticrawler`, `followed_action`, `antileakage`, `antiscan_high_freq_scan`, `custom_whiteblackip`, `custom_geoip`, `custom_custom`, `advanced_bot`, etc. Run `ListAttackActionTypes` for full list |
| `--actions.N` | array | Filter by action: `block`, `pass`, `log`, `captcha`, `cache`, `mask`, `js_challenge`, `advanced_captcha`, `abort_response`, `desensitize` |
| `--sip` | string | Filter by source IP (supports fuzzy match with `--query_mode=include`) |
| `--sips.N` | array | Filter by multiple source IPs |
| `--domain` | string | Filter by domain (fuzzy match) |
| `--url` | string | Filter by URL (supports fuzzy match with `--query_mode=include`) |
| `--urls.N` | array | Filter by URL list |
| `--query_mode` | string | Query mode: `equal` (exact match) or `include` (fuzzy match, default). Affects `--sip` and `--url` only |
| `--ip_countries.N` | array | Filter by client IP country |
| `--ip_regions.N` | array | Filter by client IP province (China only) |
| `--rules.N` | array | Filter by matched rule ID |
| `--sort_key` | string | Sort field: `attack_time`, `sort_ip`, `host`, `geo_str`, `component`, `rule`, `attack` |
| `--sort_direction` | string | `desc` (default) or `asc` |
| `--page` / `--pagesize` | integer | Pagination controls |
| `--payload` | string | Search by malicious payload content |
| `--nattacks.N` | array | Exclude attack type (opposite of `--attacks.N`) |
| `--enterprise_project_id` | string | Enterprise project filter |

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `{time_range}` | No | Analysis time window (default: `today`) | `1week` |
| `{domain}` | No | Target domain filter | `example.com` |
| `{attack_type}` | No | Attack type filter | `sqli` |
| `{source_ip}` | No | Source IP filter | `203.0.113.1` |

## Reference Documents

- `references/iam-policies.md` — Least-privilege IAM policies for WAF log querying
- `references/cli-installation-guide.md` — hcloud CLI installation and configuration
- `references/verification-method.md` — How to verify the skill is working correctly
- `references/dataflow-diagram.md` — Mermaid data flow diagram
- `references/acceptance-criteria.md` — Acceptance criteria for analysis output quality
- `references/rule-recommendation-guide.md` — Detailed attack-to-rule mapping logic

## KooCLI Command Format Standard

```bash
hcloud <Service> <Operation> [--key=value ...]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | Exact KooCLI service name, uppercase | `WAF` |
| Operation name | PascalCase | `ListEvent`, `ShowEvent` |
| Simple parameter | `--key=value` | `--sip=203.0.113.1` |
| Indexed parameter | `--key.N=value` | `--attacks.1=sqli --attacks.2=xss` |
| Region | Use default configured region; do NOT specify `--cli-region` | `hcloud WAF ListEvent --recent=today` |
