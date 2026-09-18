---
name: huawei-cloud-waf-policy-query
description: |
  Query Huawei Cloud WAF protection policies. Trigger phrases include: "query protection policies", "list protection policies", "show available policies", "view protection policy details", "WAF protection posture", "view WAF protection configuration".
---

> [!IMPORTANT]
> **Read-Only Operations:**
> 1. This SKILL only supports query (read-only) operations. No cloud resources will be created, modified, or deleted.
> 2. All operations are performed via the `hcloud` CLI.
> 3. **Do not execute query commands before the user explicitly states their intent.** You must first list the available capabilities, then ask the user for their intent.

# Overview

This SKILL enables users to efficiently query existing protection policies in Huawei Cloud WAF (Web Application Firewall) and quickly assess the current protection posture.

## Scenario Description

This SKILL supports the following query capabilities:

- **Query Protection Policy List** — List all WAF protection policies
- **Query Protection Policy Details** — View the basic configuration of a specified protection policy (protection level, protection action, enabled protection modules, etc.)

> **Region Policy**: All commands use the region configured in hcloud by default. Do NOT explicitly pass `--cli-region` in any command. The agent must rely on the hcloud configured region.

## Prerequisites

> Prerequisite Check: Huawei Cloud CLI (hcloud) >= 7.2.2 is required. Run `hcloud version` to verify version >= 7.2.2, and run `hcloud configure list` to check if the configuration file exists.

```bash
hcloud version
hcloud configure list
hcloud configure set --cli-lang=cn
```

## Core Workflow and Core Commands

### Step 0: Intent Identification (MANDATORY)

> **Mandatory Requirement**: After loading this SKILL, the agent **must execute this step first** and must not skip directly to subsequent query steps.

The agent should present the query capabilities of this SKILL to the user and ask what query they want to perform.

**Display Template:**

```
## This SKILL supports the following query functions:

1. **Query Protection Policy List** — List all WAF protection policies
2. **Query Protection Policy Details** — View the configuration details of a specified policy

What would you like to query? All commands use the region configured in hcloud by default.
```

**Intent Branches:**

| User Intent | Execution Steps | Example |
|-------------|----------------|---------|
| Browse policy list | Step 1 | "List all protection policies" |
| View policy details | Step 1 → Step 2 | "View details of policy xxx" |

---

### Step 1: Query Protection Policy List

> **Mandatory Requirement**: The agent must execute the query protection policy list command via hcloud to retrieve all policies.

By default, the query retrieves the protection policy list using the region configured in hcloud.

Execute the query command:
```bash
hcloud WAF ListPolicy
```

> **Note**: The agent should extract the `id` and `name` of each policy from the response for subsequent use when the user requests details of a specific policy.

**Result Presentation**: The agent should present the policy list in a table format with the following key fields:
- `id` — Policy ID
- `name` — Policy name
- `action.category` — Default protection action (block/log)
- `hosts` — Bound domains
- `rules_count` — Number of rules per category

**Display Rules**:
- If the number of returned policies is <= 5: display all
- If the number of returned policies is > 5: display only the first 5 and inform the user of the total count

#### Save Query Results

If the user wishes to save the complete query results for future reference, the agent should use the **Write tool** to save the **full policy** JSON data to a local file (no shell commands needed — platform-independent).

Recommended filename format: `waf-policies-<yyyyMMdd-HHmmss>.json`, e.g., `waf-policies-20260903-143025.json`

**Recommended Timing**: When the number of returned policies is large (e.g., > 10), proactively suggest saving the complete results to a JSON file.

---

### Step 2: Query Protection Policy Details

> **Mandatory Requirement**: The agent must use the policy ID (`id`) or policy name (`name`) obtained from the Step 1 results as parameters for this step's query operation. Do not provide policy identifiers from memory or by guessing.

#### Step 2.1: Query Policy Basic Information

Execute the query command:
```bash
hcloud WAF ShowPolicy --policy_id=<policy_id>
```

Extract the following key information from the response:
- `id` / `name` — Policy identifier
- `level` — Basic protection level (1=Low, 2=Medium, 3=Strict)
- `action.category` — Default protection action (block/log)
- `full_detection` — Precise protection detection mode (false=short-circuit detection, true=full detection)
- `hosts` / `bind_host` — Bound domains
- `options` — Toggle status of each protection module (used in Step 2.2 to determine which rules to query)
- `rules_count` — Rule count statistics per category (used in Step 2.2 to determine whether rule details need to be queried)

**Result Presentation**: The agent should present the policy basic information in a table format, highlighting the enabled/disabled status of each protection module in `options`.

---

#### Step 2.2: Query Rule Details of Enabled Protection Modules (MANDATORY)

> **Mandatory Requirement**: The agent must determine which protection modules require rule detail queries based on the `options` and `rules_count` fields returned in Step 2.1. Do not skip enabled modules that have rules, and do not waste requests querying modules confirmed to have no rules.

**Filtering Logic (Two-Layer Filter)**:

1. **First Layer — `options` Toggle**: Check each toggle field in `options`; only proceed to the next step for modules with a value of `true`
2. **Second Layer — `rules_count` Count**: For modules that passed the first layer, check whether the corresponding field exists in `rules_count`:
   - If the field **exists in `rules_count` and the value is 0** → **Skip query**; the module is enabled but has no rules, no API request needed
   - If the field **exists in `rules_count` and the value is > 0** → **Execute query**
   - If the field **does not exist in `rules_count`** → **Execute query** (cannot determine from counts, must query to confirm)

**`rules_count` Field-to-Module Mapping Table**:

| rules_count Field | Corresponding options Field | Protection Module | Query Command |
|-------------------|---------------------------|-------------------|---------------|
| `custom` | `custom` | Precise Protection | `hcloud WAF ListCustomRules --policy_id=<policy_id>` |
| `whiteblackip` | `whiteblackip` | Blacklist/Whitelist | `hcloud WAF ListWhiteblackipRule --policy_id=<policy_id>` |
| `cc` | `cc` | CC Attack Protection | `hcloud WAF ListCcRules --policy_id=<policy_id>` |
| `geoip` | `geoip` | Geo-Access Control | `hcloud WAF ListGeoipRule --policy_id=<policy_id>` |
| `ignore` | `ignore` | Global Whitelist | `hcloud WAF ListIgnoreRule --policy_id=<policy_id>` |
| `anticrawler` | `anticrawler` | Anti-Scraper (JS Challenge) | `hcloud WAF ListAnticrawlerRules --policy_id=<policy_id>` |
| `privacy` | `privacy` | Privacy Masking | `hcloud WAF ListPrivacyRule --policy_id=<policy_id>` |
| `antitamper` | `antitamper` | Web Anti-Tampering | `hcloud WAF ListAntitamperRule --policy_id=<policy_id>` |
| `antileakage` | `antileakage` | Sensitive Data Leakage Prevention | `hcloud WAF ListAntileakageRules --policy_id=<policy_id>` |
| `ip_reputation` | `ip_reputation` | Threat Intelligence (IP Reputation) | `hcloud WAF ListIpReputationRules --policy_id=<policy_id>` |
| `followed_action` | `followed_action` | Attack Punishment | `hcloud WAF ListPunishmentRules --policy_id=<policy_id>` |

> **Note**: 
> - Basic protection (`webattack`/`common`) is a **config-only** module: it only has an enable/disable toggle in `options` and does not have independent rule queries. Its status is derived directly from the `options` field without any additional API call. The basic protection configuration (level, action) is included in the ShowPolicy response.
> - Although `ListWebBasicProtectionRules` exists in hcloud, this SKILL treats basic protection as config-only for simplicity and consistency with other toggle-only modules.

**Execution Flow**:

1. Iterate through the `options` field and collect all modules with a value of `true`
2. For each enabled module, check the corresponding field in `rules_count`:
   - Field exists in `rules_count` and equals 0 → Mark as "enabled but no rules", skip query
   - Field exists in `rules_count` and is > 0 → Add to query queue
   - Field does not exist in `rules_count` → Add to query queue (count unknown, must query)
3. Execute query commands for each module in the query queue sequentially
4. Query commands for multiple modules may be executed in parallel for efficiency
5. **Check for reference tables and IP address group references in rules** (MANDATORY):
   - Review all queried rule details for the following references:
     - **Reference table references**: Rule conditions contain the `value_list_id` field, or `logic_operation` ends with `any`/`all` (e.g., `equal_any`, `contain_all`)
     - **IP address group references**: Blacklist/whitelist rules contain the `ip_group` object (with `id`, `name`, `size` fields)
   - Collect all unique reference table IDs and IP address group IDs
   - For each reference table ID, execute the query command to retrieve details:
     ```bash
     hcloud WAF ShowValueList --valuelistid=<value_list_id>
     ```
   - For each IP address group ID, execute the query command to retrieve details:
     ```bash
     hcloud WAF ShowIpGroup --id=<ip_group_id>
     ```
   - If no reference table or IP address group references exist in the rules, skip this step
   - Multiple query commands may be executed in parallel for efficiency

**Result Presentation**: The agent should present each module's rule details in a table format, **and after each module's table, explain each rule in plain language describing its meaning and actual protection effect**.

#### Rule Explanation Requirements (MANDATORY)

> **Mandatory Requirement**: After presenting the rule table, the agent must explain each rule in plain language to help the user understand the rule's actual protection meaning. Explanations should include: what the rule does, what conditions it matches, what action it triggers, and what the practical effect is.

**Rule Explanation Guidelines per Module:**

- **Precise Protection Rules**: Explain the matching conditions (which field, what logic, what values to match) and the action triggered. If the rule uses a reference table (conditions contain `value_list_id` or `value` corresponds to a reference table name), display the complete content list of the reference table queried via `ShowValueList`, not just the reference table name.
  - Example (directly specified values): `Rule "222" means: When the request URL contains the string "block", immediately block the request. This rule has a priority of 50 and is currently enabled.`
  - Example (using reference table): `Rule "222" means: When the request URL matches any value in the reference table "url-blacklist" (ID: xxx), immediately block the request. This reference table contains the following values: /admin, /login, /api/key. This rule has a priority of 50 and is currently enabled.`

- **CC Attack Protection Rules**: Explain the rate-limiting target (by IP/domain/Header, etc.), frequency threshold (how many requests allowed within what time period), and the action when exceeded.
  - Example: `Rule "123" means: For IP address 10.25.63.193, allow a maximum of 10 requests within 60 seconds; block all subsequent requests. This rule is currently enabled.`

- **Blacklist/Whitelist Rules**: Explain whether it is a whitelist or blacklist, and which IP/CIDR it targets. If the rule uses an IP address group (response contains the `ip_group` object), display the complete IP list queried via `ShowIpGroup`, not just the address group name.
  - Example (directly specified IP): `Rule "111" means: Add IP address 10.25.63.193 to the whitelist; all requests from this IP will bypass all protection checks and be allowed. This rule is currently enabled.`
  - Example (using IP address group): `Rule "111" means: Add IP address group "block-list" (ID: xxx) to the blacklist; this address group contains the following IPs/CIDRs: 192.168.1.0/24, 10.0.0.0/8. All requests from these IPs will be blocked. This rule is currently enabled.`

- **Geo-Access Control Rules**: Explain which countries/regions are blocked or allowed.
  - Example: `Rule "111" means: Block all access requests from Australia (AU) and the United States (US). This rule is currently enabled.`

- **Global Whitelist Rules**: Explain under what conditions requests will bypass all protection checks. If the rule uses a reference table, display the complete content list of the reference table queried via `ShowValueList`.
  - Example (directly specified values): `Rule "xxx" means: When the request source IP is 10.0.0.0/8, bypass all protection checks and allow the request. This rule is currently enabled.`
  - Example (using reference table): `Rule "xxx" means: When the request source IP matches any value in the reference table "trusted-ips" (ID: xxx), bypass all protection checks and allow the request. This reference table contains the following values: 10.0.0.0/8, 172.16.0.0/12. This rule is currently enabled.`

- **Anti-Scraper Rules**: Explain the anti-scraping mode and protection action.
  - Example: `Rule "xxx" means: Enable anti-scraping protection; block detected scraping requests. This rule is currently enabled.`

- **Privacy Masking Rules**: Explain which fields will be masked.
  - Example: `Rule "xxx" means: Mask and replace ID card numbers and phone numbers in responses to prevent sensitive information leakage. This rule is currently enabled.`

- **Web Anti-Tampering Rules**: Explain which domain's which URL will be protected and what static content will be served as replacement.
  - Example: `Rule "xxx" means: When the /index.html page of domain example.com is tampered with, return the pre-configured static page content to users instead of the tampered content. This rule is currently enabled.`

- **Sensitive Data Leakage Prevention Rules**: Explain what types of sensitive information are detected and how they are handled.
  - Example: `Rule "xxx" means: Detect ID card numbers (id_card) and phone numbers (phone) in the response body and mask them before returning the response. This rule is currently enabled.`

- **Threat Intelligence Rules**: Explain the threat intelligence type (idc=IDC datacenter IP, bot=botnet, etc.), threat tags, and protection action.
  - Example: `Rule "111" means: Block requests from source IPs classified as IDC datacenter IPs with the associated threat tag "Dr.Peng". This rule is currently enabled.`

- **Attack Punishment Rules**: Explain the punishment conditions (how many times a visitor triggers blocking within what time period), the punishment duration, and the punishment action.
  - Example: `Rule "xxx" means: When a visitor triggers WAF blocking rules 5 times within 600 seconds, block all requests from that visitor for 1800 seconds. This rule is currently enabled.`

- **Attack Punishment Rules**: Explain the punishment trigger conditions (which rules being hit triggers the punishment), the punishment action (block/ban), and the punishment duration (how long the ban lasts).
  - Example: `Rule "xxx" means: When an IP address hits any basic protection rule 2 times within 600 seconds, block that IP for 300 seconds. This rule is currently enabled.`

**Explanation Rules**:
- Each rule must be explained individually; none may be omitted
- Explanations should use plain, easy-to-understand language; avoid directly listing API field names
- If the rule name itself is meaningful (e.g., "block-admin"), it should be mentioned in the explanation
- If a rule's status is disabled (status=0), note at the end of the explanation: "This rule is currently disabled and will not take effect"

**Display Rules**:
- Display a separate table for each enabled module
- If a module is confirmed to have 0 rules via `rules_count` (query was skipped), mark it in the protection module status table as "Enabled but no rules (query skipped)"
- If a module's query returns 0 rules, note "Enabled but no rules"
- If there are many rules (> 10), display the first 10 and indicate the total count

---

#### Step 2.3: Summary Presentation

The agent should consolidate the results from Step 2.1 and Step 2.2 into a complete policy detail report with the following structure:

```
## Policy Details: <Policy Name>

### Basic Information
| Field | Value |
|-------|-------|
| Policy ID | xxx |
| Protection Level | xxx |
| Default Action | xxx |
| Bound Domains | xxx |
| Precise Protection Detection Mode | xxx |

### Protection Module Status
| Module (options field) | Status | Rule Count |
|------------------------|--------|------------|
| webattack | ✅ Enabled | config-only |
| common | ✅ Enabled | config-only |
| crawler | ✅ Enabled | config-only |
| crawler_engine | ❌ Disabled | — |
| crawler_scanner | ✅ Enabled | config-only |
| crawler_script | ❌ Disabled | — |
| crawler_other | ❌ Disabled | — |
| webshell | ✅ Enabled | config-only |
| cc | ✅ Enabled | 0 (query skipped) |
| custom | ✅ Enabled | 0 (query skipped) |
| precise | ❌ Disabled | — |
| whiteblackip | ✅ Enabled | N rules |
| geoip | ❌ Disabled | — |
| ignore | ❌ Disabled | — |
| privacy | ❌ Disabled | — |
| antitamper | ❌ Disabled | — |
| anticrawler | ❌ Disabled | — |
| antileakage | ❌ Disabled | — |
| followed_action | ❌ Disabled | — |
| ip_reputation | ✅ Enabled | 0 (query skipped) |
| bot_enable | ✅ Enabled | config-only |
| modulex_enabled | ❌ Disabled | — |

> **Note**: "Query skipped" means the module was confirmed to have 0 rules via `rules_count`, so no additional API requests were needed. "config-only" means the module only has an enable/disable toggle in `options` and does not have an independent rule query API; its status is derived directly from the `options` field without any additional API call.

### Precise Protection Rule Details
(Table)

> **Rule Explanations**:
> 1. Rule "xxx": When the request <condition field> <logic operation> <match value>, execute <action>. Priority <N>, currently <enabled/disabled>.
> 2. ...

### CC Attack Protection Rule Details
(Table)

> **Rule Explanations**:
> 1. Rule "xxx": For <rate-limiting target> <match condition>, allow a maximum of <threshold> requests within <period>; execute <action> when exceeded. Currently <enabled/disabled>.
> 2. ...

### Blacklist/Whitelist Rule Details
(Table)

> **Rule Explanations**:
> 1. Rule "xxx": Add IP <address/CIDR> to <whitelist/blacklist>; requests from this IP will be <allowed directly/blocked entirely>. Currently <enabled/disabled>.
> 2. ...

### Geo-Access Control Rule Details
(Table)

> **Rule Explanations**:
> 1. Rule "xxx": <Block/Allow> all access requests from <list of countries/regions>. Currently <enabled/disabled>.
> 2. ...

### Global Whitelist Rule Details
(Table)

> **Rule Explanations**:
> 1. Rule "xxx": When the request <condition field> <logic operation> <match value>, bypass all protection checks and allow directly. Currently <enabled/disabled>.
> 2. ...

### Anti-Scraper Rule Details
(Table)

> **Rule Explanations**:
> 1. Rule "xxx": Enable anti-scraping protection; execute <action> on detected scraping requests. Currently <enabled/disabled>.
> 2. ...

### Privacy Masking Rule Details
(Table)

> **Rule Explanations**:
> 1. Rule "xxx": Mask and replace <field categories> in responses to prevent sensitive information leakage. Currently <enabled/disabled>.
> 2. ...

### Web Anti-Tampering Rule Details
(Table)

> **Rule Explanations**:
> 1. Rule "xxx": When the <URL> page of domain <hostname> is tampered with, return pre-configured static page content to users. Currently <enabled/disabled>.
> 2. ...

### Sensitive Data Leakage Prevention Rule Details
(Table)

> **Rule Explanations**:
> 1. Rule "xxx": Detect <sensitive information categories> in the response body and apply <masking/blocking>. Currently <enabled/disabled>.
> 2. ...

### Threat Intelligence Rule Details
(Table)

> **Rule Explanations**:
> 1. Rule "xxx": For requests from source IPs classified as <threat intelligence type> with the associated threat tag "<tag>", execute <action>. Currently <enabled/disabled>.
> 2. ...

### Attack Punishment Rule Details
(Table)

> **Rule Explanations**:
> 1. Rule "xxx": When a visitor triggers WAF blocking rules <N> times within <time period> seconds, block all requests from that visitor for <punishment duration> seconds. Currently <enabled/disabled>.
> 2. ...

> **Note**: Only display rule details for enabled modules; disabled modules do not need to be shown. Rule explanations for each module must be described in plain language so that users can understand the rule's actual protection effect without needing to read API field names.

```

---

#### Step 2.4: Save Query Results (MANDATORY)

> **Mandatory Requirement**: After completing the summary presentation in Step 2.3, the agent **must execute this step** to save the complete results displayed in Step 2.3 as a JSON file to local storage. **Do not skip this step unless the user explicitly states they do not want to save.**

**Save Content**: Organize the complete policy detail report presented to the user in Step 2.3 as structured JSON. The `basic_info` and `module_status` are compiled by the agent; for `rule_details`, each rule's raw JSON object returned by the Step 2.2 query is saved directly (no field extraction, no processing, no added explanation).

**Important**: The `module_status` array in the saved JSON must correspond exactly to the "Protection Module Status" table displayed in Step 2.3 — including all modules shown in that table (both enabled and disabled). Each entry should match one row from the Step 2.3 table.

**File Path Determination Logic (MANDATORY)**:

> **Mandatory Requirement**: The agent **must first ask the user** whether they need a custom save path; do not use the default path directly.

1. **Ask the User**: The agent should present the default path and ask whether the user needs a custom save path:
   ```
   Query results will be saved to the following path:
   `<default path>`

   To save to a custom location, please provide the full path (e.g., `C:\temp\waf-report.json`).
   If the default path is acceptable, simply confirm.
   ```
2. **User-Specified Path**: If the user provides a save path (e.g., `C:\temp\waf-report.json`), use the user-specified path
3. **Default Path**: If the user confirms the default path or does not specify a path, the agent generates it according to the following rules:
   - Filename format: `waf-policy-<policy_id_short>-<yyyyMMdd-HHmmss>.json`
   - `<policy_id_short>`: First 8 characters of the policy ID
   - Default save directory: Current working directory
   - Example: `waf-policy-ba3e497c-20260904-143025.json`

**JSON Structure**:

```json
{
  "metadata": {
    "query_time": "<Query time in ISO 8601 format>",
    "region": "<Region from hcloud configuration>",
    "policy_id": "<Policy ID>",
    "policy_name": "<Policy name>"
  },
  "basic_info": {
    "policy_id": "<Policy ID>",
    "policy_name": "<Policy name>",
    "level": "<Protection level number>",
    "level_desc": "<Low/Medium/Strict>",
    "default_action": "<block/log>",
    "bind_hosts": ["<List of bound domains>"],
    "full_detection": "<true=full detection/false=short-circuit detection>",
    "enterprise_project_id": "<Enterprise project ID>"
  },
  "module_status": [
    {
      "module": "<options field name, must match the Module column in Step 2.3 Protection Module Status table>",
      "enabled": "<true/false>",
      "rules_count": "<Rule count matching Step 2.3 table; 'config-only' for modules without rule query API; null for disabled modules>"
    }
  ],
  "rule_details": {
    "<module_name>": {
      "rules": [
        <Rule JSON objects returned by the module's API query in Step 2.2. If rules reference reference tables or IP address groups, replace the summary information in the response with the complete details queried via ShowValueList/ShowIpGroup>
      ]
    }
  }
}
```

**Execution Flow**:

1. Organize the basic information and protection module status into the JSON structure in memory (do NOT write any file yet)
2. Compute the default save path as a **display string** (no shell command needed — just format the filename from the policy ID prefix and current time)
3. **Ask the user** whether they need a custom save path (present the default path for confirmation or replacement)
4. After user confirms, use the agent's native **Write tool** to write the JSON file directly (platform-independent, no shell commands)
5. Confirm successful save and display the file's absolute path

> **CRITICAL CONSTRAINT**: Use the **Write tool** directly — do NOT use shell commands (PowerShell `Out-File`, Bash `>`, etc.) to avoid platform compatibility issues. Path computation should be done by string formatting in the agent's reasoning, not by executing a shell command.

**Save Method**: Use the **Write tool** with the following parameters:
- `file_path`: The confirmed file path (default or user-specified)
- `content`: The organized JSON data prepared in step 1

---

## Parameters

| Parameter | Required/Optional | Description | Default Value |
|-----------|-------------------|-------------|---------------|
| `--policy_id` | Required (when querying details in Step 2) | Protection policy ID | None |

## Hard Constraints (MANDATORY)

The following constraints are mandatory rules and must not be violated under any circumstances:

1. **Read-Only**: All operations in this SKILL are read-only. Creating (Create), updating (Update), or deleting (Delete) any cloud resources is strictly prohibited. Commands such as `Create*`, `Update*`, `Delete*` and other write operations must not be invoked.
2. **No Credential Leakage**: Exposing any hcloud configuration information in output is strictly prohibited, including but not limited to AK/SK, SecretKey, Project ID, Region configuration, Profile information, credential content returned by `hcloud configure`, etc.
3. **No Write Operation Guidance**: Proactively suggesting, mentioning, or guiding the user toward create, modify, or delete operations in the conversation is strictly prohibited. After completing the query, end the interaction directly; do not follow up with "Would you like to perform further operations?"

## Reference Documentation

| Document | Description |
|----------|-------------|
| hcloud WAF ListPolicy | Query protection policy list |
| hcloud WAF ShowPolicy | Query protection policy details |
| hcloud WAF ListCustomRules | Query precise protection rule list |
| hcloud WAF ListCcRules | Query CC attack protection rule list |
| hcloud WAF ListWhiteblackipRule | Query blacklist/whitelist rule list |
| hcloud WAF ListGeoipRule | Query geo-access control rule list |
| hcloud WAF ListIgnoreRule | Query global whitelist rule list |
| hcloud WAF ListAnticrawlerRules | Query anti-scraping rule list |
| hcloud WAF ListPrivacyRule | Query privacy masking rule list |
| hcloud WAF ListAntitamperRule | Query web anti-tampering rule list |
| hcloud WAF ListAntileakageRules | Query sensitive data leakage prevention rule list |
| hcloud WAF ListIpReputationRules | Query threat intelligence rule list |
| hcloud WAF ListPunishmentRules | Query attack punishment rule list |
| hcloud WAF ShowPunishmentRule | Query attack punishment rule details |
| hcloud WAF ListValueList | Query reference table list |
| hcloud WAF ShowValueList | Query reference table details |
| hcloud WAF ListIpGroup | Query IP address group list |
| hcloud WAF ShowIpGroup | Query IP address group details |

## Troubleshooting

### Issue: Command returns empty results

**Cause**: No protection policies exist in the hcloud configured region, or the hcloud configuration is incorrect.
**Solution**: Verify the hcloud configuration with `hcloud configure list`, or check if the correct region is configured. You can switch regions via `hcloud configure set --cli-region=<region>` if needed.

### Issue: hcloud command times out

**Cause**: Network connectivity issues or system proxy interference.
**Solution**: Check network connectivity; if in an enterprise proxy environment, try using Proxifier or switch to a direct connection network. hcloud does not support proxy configuration parameters.

### Issue: "Unsupported operation" error

**Cause**: Command name case or singular/plural form mismatch.
**Solution**: Use `hcloud WAF --help` to view the list of available commands; note that command names are case-sensitive and singular/plural-sensitive.

## Notes

- This SKILL is for **read-only operations** only; it will not create, modify, or delete any cloud resources
- Command names are case-sensitive and singular/plural-sensitive; it is recommended to verify via `hcloud WAF <Command> --help` before use
- The number of protection policies may be large (e.g., thousands); query results should be presented in summary form to avoid outputting excessive raw JSON
