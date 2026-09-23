# Rule Recommendation Guide

This document defines the detailed mapping logic from observed attack patterns to specific WAF protection rules, **including executable hcloud CLI commands**.

## Prerequisites for All Commands

All commands below require:
- `{region}` — WAF instance region (e.g., `cn-north-4`)
- `{policy_id}` — Target policy ID (extract from event data `policyid` field)
- `{project_id}` — Project ID (configured via `hcloud configure set --cli-project-id=<id>`)
- IAM permissions: see `iam-policies.md`

---

## Decision Matrix

### Pattern 1: High-Frequency Requests from Single IP

**Detection criteria:**
- Same source IP appears > threshold times in analysis period
- Often targeting same URL path
- May or may not contain attack payloads

**Recommended rules and hcloud commands:**

| Scenario | Rule Type | Configuration |
|----------|-----------|---------------|
| Normal requests, high frequency | CC Protection | Condition: URL match + IP tag; Limit: 100 req/60s; Action: block; Lock time: 300s |
| Attack payloads present | IP Blacklist | Add source IP to blacklist; Action: block |
| Both patterns | CC Protection + IP Blacklist | Rate limit first, block persistent offenders |

**CC Protection command** (⚠️ use `--cli-jsonInput` due to `--mode` conflict):

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
    "action": { "category": "block" }
  }
}
```

Execute:
```bash
hcloud WAF CreateCcRule --cli-jsonInput=cc-rule.json
```

Parameters:
- `tag_type`: `ip` (by source IP), `url` (by URL), `cookie`, `header`
- `limit_num` / `limit_period`: trigger when count exceeds within window (seconds)
- `lock_time`: block duration (seconds) after threshold exceeded
- `action.category`: `block`, `captcha`, `redirect`

Verify:
```bash
hcloud WAF ListCcRules --policy_id={policy_id}
```

**IP Blacklist command:**
```bash
hcloud WAF CreateWhiteblackipRule \
  --policy_id={policy_id} \
  --name={rule_name} \
  --addr={source_ip_or_cidr} \
  --white=0
```

Parameters:
- `--white=0` → blacklist (block), `--white=1` → whitelist (allow), `--white=2` → log only
- `--addr` supports single IP or CIDR (e.g., `203.0.113.0/24`)

Verify:
```bash
hcloud WAF ListWhiteblackipRule --policy_id={policy_id} --page=1 --pagesize=10
```

---

### Pattern 2: SQL Injection Attempts

**Detection criteria:**
- `attack` field = `sqli`
- Payload contains SQL syntax (`SELECT`, `UNION`, `' OR`, `DROP TABLE`, etc.)
- May target specific URL parameters

**Recommended rule:**

```
Rule Type: Precise Access Control (Custom Rule)
Condition:
  - Field: url, Logic: contain, Value: {targeted_url}
  AND
  - Field: payload/header, Logic: contain, Value: {sqli_pattern}
Action: block
Priority: High
```

Also verify: Basic protection (Web Foundation Protection) has SQL injection detection enabled and set to "block" mode.

**hcloud command — Block sqli on specific URL:**
```bash
hcloud WAF CreateCustomRule \
  --policy_id={policy_id} \
  --name={rule_name} \
  --action.category=block \
  --conditions.1.category=url \
  --conditions.1.logic_operation=contain \
  --conditions.1.contents.1={targeted_url} \
  --conditions.2.category=params \
  --conditions.2.logic_operation=contain \
  --conditions.2.contents.1={sqli_pattern} \
  --priority=30 \
  --time=false
```

Verify basic protection is set to block:
```bash
hcloud WAF ShowPolicy --policy_id={policy_id}
# If action=log, change to block:
hcloud WAF UpdatePolicy \
  --policy_id={policy_id} \
  --action.category=block
```

Verify custom rules:
```bash
hcloud WAF ListCustomRules --policy_id={policy_id}
```

---

### Pattern 3: XSS Attack Attempts

**Detection criteria:**
- `attack` field = `xss`
- Payload contains script tags, event handlers, javascript: URIs

**Recommended rule:**

```
Rule Type: Precise Access Control
Condition:
  - Field: url, Logic: contain, Value: {targeted_url}
Action: block (for persistent sources)
```

Also verify: Basic protection has XSS detection enabled.

**hcloud command — Block XSS on targeted URL:**
```bash
hcloud WAF CreateCustomRule \
  --policy_id={policy_id} \
  --name={rule_name} \
  --action.category=block \
  --conditions.1.category=url \
  --conditions.1.logic_operation=contain \
  --conditions.1.contents.1={targeted_url} \
  --priority=30 \
  --time=false
```

**hcloud command — Block by scanner User-Agent (if automated):**
```bash
hcloud WAF CreateCustomRule \
  --policy_id={policy_id} \
  --name={rule_name} \
  --action.category=block \
  --conditions.1.category=user-agent \
  --conditions.1.logic_operation=contain \
  --conditions.1.contents.1={scanner_signature} \
  --priority=31 \
  --time=false
```

Key notes:
- `user-agent` is a standalone category, NOT a header field — do NOT use `--conditions.1.index` with it
- `--time=false` — immediate effect; do NOT use `--status`
- `--priority=N` — range 0~65535, lower = higher priority

Verify:
```bash
hcloud WAF ListCustomRules --policy_id={policy_id}
```

---

### Pattern 4: Geographic-Based Attacks

**Detection criteria:**
- Majority of attacks originate from specific countries
- Legitimate traffic from those countries is minimal or zero

**Recommended rule:**

```
Rule Type: Geo Access Control
Configuration:
  - Blocked regions: {attacking_countries}
  - IP type: IPv4 + IPv6
  - Action: block
```

**Caution:** Before recommending geo-blocking, confirm with the user that there is no legitimate business traffic from the identified countries.

**hcloud command:**
```bash
# Block traffic from specific country (ISO 3166-1 alpha-2 code)
hcloud WAF CreateGeoipRule \
  --policy_id={policy_id} \
  --name="geo-block-{country_code}" \
  --geoip={country_code} \
  --white=0
```

Parameters:
- `--geoip` — ISO 3166-1 alpha-2 country code (e.g., `KP`, `IR`, `CU`, `SY`)
- `--white=0` → block, `--white=1` → allow (whitelist)

Verify:
```bash
hcloud WAF ListGeoipRule --policy_id={policy_id}
```

---

### Pattern 5: BOT/Scanner Traffic

**Detection criteria:**
- `attack` field = `botm`, `robot`, or `custom_robot`
- Abnormal User-Agent strings (scanner signatures like sqlmap, nikto, nessus)
- High request rate from automated tools

**Recommended rule:**

```
Rule Type: Precise Access Control
Condition:
  - Field: User-Agent, Logic: contain, Value: {scanner_signature}
Action: block
```

Also recommend: Enable BOT management if not already active.

**hcloud command — Block scanner User-Agents:**
```bash
# Block sqlmap
hcloud WAF CreateCustomRule \
  --policy_id={policy_id} \
  --name="block-sqlmap-ua" \
  --action.category=block \
  --conditions.1.category=user-agent \
  --conditions.1.logic_operation=contain \
  --conditions.1.contents.1=sqlmap \
  --priority=20 \
  --time=false

# Block nikto
hcloud WAF CreateCustomRule \
  --policy_id={policy_id} \
  --name="block-nikto-ua" \
  --action.category=block \
  --conditions.1.category=user-agent \
  --conditions.1.logic_operation=contain \
  --conditions.1.contents.1=nikto \
  --priority=21 \
  --time=false

# Block python-requests (common automation tool)
hcloud WAF CreateCustomRule \
  --policy_id={policy_id} \
  --name="block-python-requests" \
  --action.category=block \
  --conditions.1.category=user-agent \
  --conditions.1.logic_operation=contain \
  --conditions.1.contents.1=python-requests \
  --priority=22 \
  --time=false
```

Common scanner signatures to detect:
- `sqlmap`, `nikto`, `nessus`, `nmap`, `masscan`, `zgrab`
- `python-requests`, `curl`, `wget`, `scrapy`
- `dirbuster`, `gobuster`, `wfuzz`, `ffuf`

Verify:
```bash
hcloud WAF ListCustomRules --policy_id={policy_id}
```

---

### Pattern 6: Admin/API Path Targeting

**Detection criteria:**
- Attacks concentrated on `/admin`, `/wp-admin`, `/api/`, `/login`, `/phpmyadmin` paths
- Multiple attack types targeting these paths

**Recommended rule:**

```
Rule Type: Precise Access Control
Condition:
  - Field: url, Logic: contain, Value: /admin
  OR Field: url, Logic: contain, Value: /wp-admin
  OR Field: url, Logic: contain, Value: /phpmyadmin
Action: block
Note: For /api paths, use whitelist approach instead (allow known API consumers)
```

**hcloud commands — Block admin paths:**
```bash
# Block /admin
hcloud WAF CreateCustomRule \
  --policy_id={policy_id} \
  --name="block-admin-path" \
  --action.category=block \
  --conditions.1.category=url \
  --conditions.1.logic_operation=contain \
  --conditions.1.contents.1=/admin \
  --priority=10 \
  --time=false

# Block WordPress admin
hcloud WAF CreateCustomRule \
  --policy_id={policy_id} \
  --name="block-wp-admin" \
  --action.category=block \
  --conditions.1.category=url \
  --conditions.1.logic_operation=contain \
  --conditions.1.contents.1=/wp-admin \
  --priority=11 \
  --time=false

# Block phpMyAdmin
hcloud WAF CreateCustomRule \
  --policy_id={policy_id} \
  --name="block-phpmyadmin" \
  --action.category=block \
  --conditions.1.category=url \
  --conditions.1.logic_operation=contain \
  --conditions.1.contents.1=/phpmyadmin \
  --priority=12 \
  --time=false
```

**hcloud command — Whitelist approach for API paths:**
```bash
# Allow only known IPs to access /api/
hcloud WAF CreateCustomRule \
  --policy_id={policy_id} \
  --name="allow-api-known-ips" \
  --action.category=pass \
  --conditions.1.category=url \
  --conditions.1.logic_operation=prefix \
  --conditions.1.contents.1=/api/ \
  --conditions.2.category=ip \
  --conditions.2.logic_operation=equal \
  --conditions.2.contents.1={known_api_client_ip} \
  --priority=5 \
  --time=false
```

Verify:
```bash
hcloud WAF ListCustomRules --policy_id={policy_id}
```

---

### Pattern 7: Distributed Attacks from IP Subnet

**Detection criteria:**
- Multiple source IPs from same /24 subnet
- Similar attack patterns across IPs
- Indicates coordinated attack or compromised botnet

**Recommended rule:**

```
Rule Type: IP Group Blacklist
Configuration:
  - IP group: {subnet}/24
  - Action: block
```

**hcloud command — Block entire subnet (CIDR notation):**
```bash
hcloud WAF CreateWhiteblackipRule \
  --policy_id={policy_id} \
  --name="block-subnet-{subnet_prefix}" \
  --addr={subnet}/24 \
  --white=0
```

Or create an IP group first (for reusable groups):
```bash
# Step 1: Create IP group with IPs (comma-separated IP addresses or CIDR ranges)
hcloud WAF CreateIpGroup \
  --name="malicious-subnet-group" \
  --ips="{ip1},{ip2},{subnet}/24" \
  --description="Suspicious /24 subnet"

# Step 2: Use group in blacklist rule
hcloud WAF CreateWhiteblackipRule \
  --policy_id={policy_id} \
  --name="block-ip-group" \
  --ip_group_id={group_id} \
  --white=0
```

To update an existing IP group (add/remove IPs), use `UpdateIpGroup`:
```bash
hcloud WAF UpdateIpGroup \
  --group_id={group_id} \
  --ips="{updated_ip1},{updated_ip2},{updated_subnet}/24"
```

Note: `addr` and `ip_group_id` are mutually exclusive in `CreateWhiteblackipRule` — passing both will ignore `ip_group_id`.

Verify:
```bash
hcloud WAF ListWhiteblackipRule --policy_id={policy_id} --page=1 --pagesize=10
```

---

### Pattern 8: Command Injection / RCE / RFI

**Detection criteria:**
- `attack` field = `cmdi`, `rce`, `rfi`, `lfi`
- Payload contains shell commands, file paths, remote URLs

**Recommended rule:**

These are high-severity attacks. Recommend:
1. Verify basic protection rules cover these attack types
2. Create precise access control rules for targeted URLs
3. Consider blocking source IPs immediately

**hcloud commands — Step-by-step response:**

*Step 1: Check current protection level*
```bash
hcloud WAF ShowPolicy --policy_id={policy_id}
# Look for options.webattack settings
# If action=log, escalate to block:
hcloud WAF UpdatePolicy \
  --policy_id={policy_id} \
  --action.category=block \
  --level=3
```

*Step 2: Block command injection on targeted URL*
```bash
hcloud WAF CreateCustomRule \
  --policy_id={policy_id} \
  --name="block-cmdi-on-{url_path}" \
  --action.category=block \
  --conditions.1.category=url \
  --conditions.1.logic_operation=equal \
  --conditions.1.contents.1={targeted_url} \
  --conditions.2.category=params \
  --conditions.2.logic_operation=contain \
  --conditions.2.contents.1={payload_pattern} \
  --priority=5 \
  --time=false
```

*Step 3: Block source IPs immediately*
```bash
hcloud WAF CreateWhiteblackipRule \
  --policy_id={policy_id} \
  --name="block-cmdi-source" \
  --addr={source_ip} \
  --white=0
```

Common cmdi/rce payload patterns to detect (these are malicious request signatures for WAF rules to match, not actual file paths accessed by this skill):
- Shell commands: `ls`, `cat`, `whoami`, `id`, `uname`, `pwd`, `wget`, `curl`
- Pipe operators: `|`, `||`, `&&`, `;`, `` ` ``
- File inclusion payloads: `../`, `..\\`, system file path keywords like `/etc/[sensitive]`, `/proc/[self]`
- Remote files: `http://`, `https://`, `ftp://`, `file://`

Verify:
```bash
hcloud WAF ListCustomRules --policy_id={policy_id}
hcloud WAF ListWhiteblackipRule --policy_id={policy_id} --page=1 --pagesize=10
```

---

### Pattern 9: Webshell Upload/Access

**Detection criteria:**
- `attack` field = `webshell`
- Payload contains webshell signatures (eval, assert, system, exec, shell_exec)
- Target URLs may include upload paths, temp directories

**Recommended rule:**

Enable webshell detection module + block suspicious upload paths.

**hcloud commands:**

*Step 1: Enable webshell detection module*
```bash
hcloud WAF UpdatePolicy \
  --policy_id={policy_id} \
  --options.webshell=true
```

*Step 2: Block webshell upload paths*
```bash
hcloud WAF CreateCustomRule \
  --policy_id={policy_id} \
  --name="block-webshell-upload" \
  --action.category=block \
  --conditions.1.category=url \
  --conditions.1.logic_operation=contain \
  --conditions.1.contents.1=/upload \
  --conditions.2.category=params \
  --conditions.2.logic_operation=contain \
  --conditions.2.contents.1=eval \
  --priority=10 \
  --time=false
```

Common webshell payload patterns: `eval(`, `assert(`, `system(`, `shell_exec(`, `passthru(`, `base64_decode(`

Verify:
```bash
hcloud WAF ShowPolicy --policy_id={policy_id}
hcloud WAF ListCustomRules --policy_id={policy_id}
```

---

### Pattern 10: Directory Traversal

**Detection criteria:**
- `attack` field = `ptr`
- Payload contains path traversal sequences: `../`, `..\\`, `%2e%2e/`, `%2e%2e%5c`
- May target file download/read endpoints

**Recommended rule:**

Block path traversal patterns via precise access control. Directory traversal is also covered by basic protection (`--options.webattack=true`).

**hcloud commands:**

*Option A: Block by payload pattern*
```bash
hcloud WAF CreateCustomRule \
  --policy_id={policy_id} \
  --name="block-dir-traversal" \
  --action.category=block \
  --conditions.1.category=url \
  --conditions.1.logic_operation=contain \
  --conditions.1.contents.1=../ \
  --priority=15 \
  --time=false
```

*Option B: Block encoded traversal*
```bash
hcloud WAF CreateCustomRule \
  --policy_id={policy_id} \
  --name="block-encoded-traversal" \
  --action.category=block \
  --conditions.1.category=url \
  --conditions.1.logic_operation=contain \
  --conditions.1.contents.1=%2e%2e \
  --priority=16 \
  --time=false
```

*Option C: Ensure basic protection covers it*
```bash
hcloud WAF UpdatePolicy \
  --policy_id={policy_id} \
  --options.webattack=true \
  --action.category=block
```

Common traversal patterns (malicious request signatures for WAF detection rules, not actual paths accessed by this skill): `../`, `..\\`, URL-encoded variants (`%2e%2e/`, `%2e%2e%5c`), system file path keywords like `/etc/[sensitive]`, `/proc/[self]`

Verify:
```bash
hcloud WAF ListCustomRules --policy_id={policy_id}
```

---

### Pattern 11: Other Vulnerability Attacks

**Detection criteria:**
- `attack` field = `vuln`
- Various vulnerability exploitation not covered by specific categories
- May include CGI exploits, framework vulnerabilities, CVE-based attacks

**Recommended rule:**

Enable basic protection at strict level + query built-in vulnerability rules.

**hcloud commands:**

*Step 1: Enable basic protection in strict mode*
```bash
hcloud WAF UpdatePolicy \
  --policy_id={policy_id} \
  --options.webattack=true \
  --action.category=block \
  --level=3
```

*Step 2: Query built-in vulnerability rules for specific CVEs*
```bash
# List all vulnerability rules
hcloud WAF ListWebBasicProtectionRules \
  --protection_type_names=vuln \
  --limit=100

# Filter by CVE number
hcloud WAF ListWebBasicProtectionRules \
  --cve_number=CVE-2024-XXXX \
  --limit=10

# Filter by risk level (1=critical, 2=medium, 3=low)
hcloud WAF ListWebBasicProtectionRules \
  --risk_level=1 \
  --limit=100
```

*Step 3: Block specific exploit URL if identified*
```bash
hcloud WAF CreateCustomRule \
  --policy_id={policy_id} \
  --name="block-vuln-exploit" \
  --action.category=block \
  --conditions.1.category=url \
  --conditions.1.logic_operation=contain \
  --conditions.1.contents.1={exploit_url} \
  --priority=20 \
  --time=false
```

Parameters:
- `--protection_type_names`: `vuln`, `xss`, `cmdi`, `lfi`, `rfi`, `webshell`, `robot`, `sqli`
- `--risk_level`: `1` (critical), `2` (medium), `3` (low)
- `--level`: `1` (loose), `2` (medium), `3` (strict)

Verify:
```bash
hcloud WAF ShowPolicy --policy_id={policy_id}
hcloud WAF ListCustomRules --policy_id={policy_id}
```

---

### Pattern 12: Attack Punishment Configuration

**Detection criteria:**
- `attack` field = `followed_action`
- Repeated attacks from same IP/cookie/params/header trigger auto-block
- Need to configure punishment rules for persistent attackers

**Recommended rule:**

Create punishment rules for short-term and long-term blocking.

**hcloud commands:**

*Step 1: Enable punishment module*
```bash
hcloud WAF UpdatePolicy \
  --policy_id={policy_id} \
  --options.followed_action=true
```

*Step 2: Create short-term IP punishment (block 60 seconds)*
```bash
hcloud WAF CreatePunishmentRule \
  --policy_id={policy_id} \
  --category=short_ip_block \
  --block_time=60 \
  --time_unit=SECOND \
  --description="Short IP block for repeated attacks"
```

*Step 3: Create long-term IP punishment (block 1 day)*
```bash
hcloud WAF CreatePunishmentRule \
  --policy_id={policy_id} \
  --category=long_ip_block \
  --block_time=1 \
  --time_unit=DAY \
  --description="Long IP block for persistent attackers"
```

Parameters (verified via `--help`):
- `--category`: 8 types:
  - Short: `short_ip_block`, `short_cookie_block`, `short_params_block`, `short_header_block`
  - Long: `long_ip_block`, `long_cookie_block`, `long_params_block`, `long_header_block`
- `--block_time` ranges (depends on category + time_unit):
  - `short_*` + `SECOND`: [1, 300]
  - `long_*` + `SECOND`: [301, 7776000]
  - `long_*` + `MINUTE`: [6, 129600]
  - `long_*` + `HOUR`: [1, 2160]
  - `long_*` + `DAY`: [1, 90]
  - `long_*` + `MONTH`: [1, 3]
- `--time_unit`: `SECOND` (default), `MINUTE`, `HOUR`, `DAY`, `MONTH`
- Note: Each category can only have one rule; category cannot be modified after creation

Verify:
```bash
hcloud WAF ListPunishmentRules --policy_id={policy_id}
```

---

### Pattern 13: Malicious Crawler / Anti-Crawler

**Detection criteria:**
- `attack` field = `robot` or `anticrawler`
- Abnormal User-Agent patterns (scanners, scrapers, bots)
- High request rate from automated tools
- JS challenge failures

**Recommended rule:**

Enable anti-crawler module + create JS challenge rules for suspicious traffic.

**hcloud commands:**

*Step 1: Enable anti-crawler module and all crawler detectors*
```bash
hcloud WAF UpdatePolicy \
  --policy_id={policy_id} \
  --options.anticrawler=true \
  --options.crawler_engine=true \
  --options.crawler_scanner=true \
  --options.crawler_script=true \
  --options.crawler_other=true
```

*Step 2: Set anti-crawler protection mode (required prerequisite)*
```bash
hcloud WAF UpdateAnticrawlerRuleType \
  --policy_id={policy_id} \
  --anticrawler_type=anticrawler_except_url
```

*Step 3: Create anti-crawler rule*
```bash
hcloud WAF CreateAnticrawlerRule \
  --policy_id={policy_id} \
  --name="block-malicious-crawler" \
  --type=anticrawler_except_url \
  --conditions.1.category=user-agent \
  --conditions.1.logic_operation=contain \
  --conditions.1.contents.1={scanner_signature} \
  --priority=20
```

Parameters (verified via `--help`):
- `--type`: `anticrawler_except_url` (protect all, rule = exclusion) or `anticrawler_specific_url` (protect specified paths)
- `--conditions.N.category`: `url` or `user-agent`
- `--conditions.N.logic_operation`: `contain`, `not_contain`, `equal`, `prefix`, `suffix`, `regular_match`, etc.
- `--priority`: 0~65535

Verify:
```bash
hcloud WAF ListAnticrawlerRules --policy_id={policy_id} --page=1 --pagesize=10
```

---

### Pattern 14: IP Reputation / Threat Intelligence

**Detection criteria:**
- `attack` field = `iprank`
- Source IP flagged by threat intelligence as malicious (IDC datacenter, proxy, TOR)
- Attacks from known bad IP ranges

**Recommended rule:**

Create IP reputation rule to block threat intelligence-flagged IPs.

**hcloud commands:**

*Step 1: Create IP reputation rule*
```bash
hcloud WAF CreateIpReputationRule \
  --policy_id={policy_id} \
  --name="block-idc-malicious-ip" \
  --type=idc \
  --action.category=block \
  --tags.1={threat_tag} \
  --description="Block IDC datacenter malicious IPs"
```

Parameters (verified via `--help`):
- `--type`: Currently only supports `idc` (IDC datacenter IP)
- `--action.category`: `block` (拦截), `log` (仅记录), `pass` (放行)
- `--tags.N`: Threat intelligence tags (obtain from console or threat intel API)
- `--description`: Optional rule description

Verify:
```bash
hcloud WAF ListIpReputationRules --policy_id={policy_id} --page=1 --pagesize=10
```

---

### Pattern 15: Web Content Anti-Tamper

**Detection criteria:**
- `attack` field = `antitamper`
- Static page content has been tampered with
- Need to protect critical pages from unauthorized modification

**Recommended rule:**

Enable anti-tamper module + create anti-tamper rules for critical URLs.

**hcloud commands:**

*Step 1: Enable anti-tamper module*
```bash
hcloud WAF UpdatePolicy \
  --policy_id={policy_id} \
  --options.antitamper=true
```

*Step 2: Create anti-tamper rule for critical pages*
```bash
hcloud WAF CreateAntiTamperRule \
  --policy_id={policy_id} \
  --hostname={protected_domain} \
  --url={protected_url} \
  --description="Protect critical page from tampering"
```

Parameters (verified via `--help`):
- `--hostname`: Protected domain (from `ListHost` response `hostname` field)
- `--url`: Protected URL path, e.g., `/index.html` or `/static/*` (`*` suffix = prefix match)
- `--description`: Optional rule description

Verify:
```bash
hcloud WAF ListAntitamperRule --policy_id={policy_id} --page=1 --pagesize=10
```

---

### Pattern 16: High-Frequency Scan Protection

**Detection criteria:**
- `attack` field = `antiscan_high_freq_scan`
- High-frequency requests scanning multiple URLs
- Abnormal request rate from single IP across different paths

**Recommended rule:**

CC protection for rate limiting + modulex scan protection if available.

**hcloud commands:**

*Option A: CC protection rule (rate limiting)*
```bash
# Use --cli-jsonInput due to --mode conflict
# cc-rule.json:
{
  "path": {
    "project_id": "{project_id}",
    "policy_id": "{policy_id}"
  },
  "query": {},
  "body": {
    "name": "anti-scan-rate-limit",
    "mode": 1,
    "tag_type": "ip",
    "limit_num": 60,
    "limit_period": 60,
    "lock_time": 600,
    "action": { "category": "block" }
  }
}

hcloud WAF CreateCcRule --cli-jsonInput=cc-rule.json
```

*Option B: Enable modulex scan protection (beta)*
```bash
# Must enable modulex master switch first, then set sub-options
hcloud WAF UpdatePolicy \
  --policy_id={policy_id} \
  --options.modulex_enabled=true \
  --modulex_options.global_rate_enabled=true
```

Verify:
```bash
hcloud WAF ListCcRules --policy_id={policy_id}
hcloud WAF ShowPolicy --policy_id={policy_id}
```

---

### Pattern 17: Sensitive Data Leakage Prevention

**Detection criteria:**
- Responses contain sensitive information (phone numbers, ID cards, email addresses)
- HTTP response codes expose internal errors
- Need to filter sensitive data from responses

**Recommended rule:**

Create anti-leakage rules to filter sensitive information.

**hcloud commands:**

*Step 1: Enable anti-leakage module*
```bash
hcloud WAF UpdatePolicy \
  --policy_id={policy_id} \
  --options.antileakage=true
```

*Step 2: Block sensitive information in responses*
```bash
hcloud WAF CreateAntileakageRule \
  --policy_id={policy_id} \
  --category=sensitive \
  --contents.1=phone \
  --contents.2=id_card \
  --contents.3=email \
  --url=/* \
  --action.category=block \
  --description="Filter sensitive data from all responses"
```

*Step 3: Mask error response codes*
```bash
hcloud WAF CreateAntileakageRule \
  --policy_id={policy_id} \
  --category=code \
  --contents.1=500 \
  --contents.2=501 \
  --contents.3=502 \
  --url=/* \
  --action.category=log \
  --description="Log 5xx error codes"
```

Parameters (verified via `--help`):
- `--category`: `code` (HTTP status code) or `sensitive` (sensitive information)
- `--contents.N`:
  - For `code`: `400`, `401`, `402`, `403`, `404`, `405`, `500`, `501`, `502`, `503`, `504`, `507`
  - For `sensitive`: `phone`, `id_card`, `email`
- `--url`: URL path to apply the rule
- `--action.category`: `block` (filter) or `log` (record only)

Verify:
```bash
hcloud WAF ListAntileakageRules --policy_id={policy_id} --page=1 --pagesize=10
```

---

## Priority Framework

When multiple patterns are detected, prioritize recommendations as follows:

| Priority | Pattern | Rationale |
|----------|---------|-----------|
| P0 - Critical | Command injection / RCE (Pattern 8) | Direct server compromise risk |
| P1 - High | SQL injection with data exfiltration signs (Pattern 2) | Data breach risk |
| P2 - High | Webshell upload/access (Pattern 9) | Server takeover risk |
| P2 - High | Coordinated multi-IP attack (Pattern 7) | Active campaign |
| P3 - Medium | Directory traversal (Pattern 10) | File system access risk |
| P3 - Medium | Other vulnerability exploits (Pattern 11) | Unknown exploit risk |
| P3 - Medium | Persistent single-IP attacks (Pattern 1) | Ongoing threat |
| P4 - Medium | Attack punishment config (Pattern 12) | Deter persistent attackers |
| P4 - Medium | Geographic concentration (Pattern 4) | Potential botnet source |
| P5 - Low | IP reputation blocking (Pattern 14) | Proactive threat intelligence |
| P5 - Low | Scanner/BOT probes (Pattern 5) | Reconnaissance activity |
| P5 - Low | Malicious crawler (Pattern 13) | Content scraping risk |
| P6 - Low | High-frequency scan (Pattern 16) | Reconnaissance activity |
| P6 - Low | Admin path scanning (Pattern 6) | Common automated scanning |
| P6 - Low | Anti-tamper protection (Pattern 15) | Content integrity assurance |
| P6 - Low | Sensitive data leakage (Pattern 17) | Compliance and data protection |

---

## Recommendation Output Format

Each recommendation should include the hcloud command so the user can execute it directly:

```markdown
### Recommendation #{N}: {Rule Type}
**Priority**: {P0-P6}
**Observed Pattern**: {What was detected in the logs}
**Evidence**: {Specific data points — IP count, event count, attack type}

**Suggested Configuration**:
- Rule type: {type}
- Conditions: {specific conditions}
- Action: {block/pass/captcha}

**Risk Assessment**: {Potential impact on legitimate traffic}

**Execute Command**:
```bash
hcloud WAF {Command} --policy_id={policy_id} ...
```

**Verification Command**:
```bash
hcloud WAF {List/Show Command} --policy_id={policy_id}
```
```

---

## KooCLI Parameter Pitfalls

| Pitfall | ❌ Wrong | ✅ Correct | Reason |
|---------|----------|------------|--------|
| Nested params | `--action=block` | `--action.category=block` | API expects nested JSON object |
| Header field name | `--conditions.1.field=UA` | `--conditions.1.index=User-Agent` | header/cookie sub-fields use "index" |
| Immediate effect | `--status=1` | `--time=false` | Boolean flag controls activation timing |
| mode conflict | `--mode=1` (direct) | Use `--cli-jsonInput=file.json` | KooCLI has its own `--mode` parameter |
| Array index | `--conditions.0.xxx` | `--conditions.1.xxx` | Indexing starts from 1, not 0 |
| Singular/plural | `ListWhiteblackipRules` | `ListWhiteblackipRule` | API commands use singular form |
| Case sensitivity | `ShowWhiteblackipRule` | `ShowWhiteBlackIpRule` | "Black" must be capitalized |

---

## Quick Reference: Common hcloud WAF Commands

| Operation | Command | Key Parameters |
|-----------|---------|----------------|
| View policy | `ShowPolicy` | `--policy_id` |
| Update policy action | `UpdatePolicy` | `--action.category=block`, `--level=3` |
| Enable module | `UpdatePolicy` | `--options.webshell=true`, `--options.antitamper=true`, etc. |
| IP blacklist | `CreateWhiteblackipRule` | `--addr={ip}`, `--white=0` |
| IP whitelist | `CreateWhiteblackipRule` | `--addr={ip}`, `--white=1` |
| CC protection | `CreateCcRule` | `--cli-jsonInput=file.json` (mode conflict) |
| Custom rule | `CreateCustomRule` | `--conditions.N.category/index/logic_operation/contents.N` |
| Geo block | `CreateGeoipRule` | `--geoip={country_code}`, `--white=0` |
| Anti-crawler | `CreateAnticrawlerRule` | `--type`, `--conditions.N.category` (url\|user-agent) |
| Set anticrawler mode | `UpdateAnticrawlerRuleType` | `--anticrawler_type` (prerequisite for CreateAnticrawlerRule) |
| IP reputation | `CreateIpReputationRule` | `--type=idc`, `--action.category`, `--tags.N` |
| Anti-tamper | `CreateAntiTamperRule` | `--hostname`, `--url` |
| Punishment | `CreatePunishmentRule` | `--category`, `--block_time`, `--time_unit` |
| Anti-leakage | `CreateAntileakageRule` | `--category` (code\|sensitive), `--contents.N`, `--url` |
| Toggle rule status | `UpdatePolicyRuleStatus` | `--rule_type`, `--rule_id`, `--status` (0\|1) |
| List vuln rules | `ListWebBasicProtectionRules` | `--protection_type_names`, `--risk_level`, `--cve_number` |
| List blacklists | `ListWhiteblackipRule` | `--policy_id`, `--page`, `--pagesize` |
| List CC rules | `ListCcRules` | `--policy_id` |
| List custom rules | `ListCustomRules` | `--policy_id` |
| List geo rules | `ListGeoipRule` | `--policy_id` |
| List anticrawler | `ListAnticrawlerRules` | `--policy_id`, `--page`, `--pagesize` |
| List IP reputation | `ListIpReputationRules` | `--policy_id`, `--page`, `--pagesize` |
| List anti-tamper | `ListAntitamperRule` | `--policy_id`, `--page`, `--pagesize` |
| List punishment | `ListPunishmentRules` | `--policy_id` |
| List anti-leakage | `ListAntileakageRules` | `--policy_id`, `--page`, `--pagesize` |
| Delete rule | `Delete{Type}Rule` | `--policy_id`, `--rule_id` |
