---
name: huawei-cloud-waf-policy-manage
description: "Import WAF protection policies from JSON files exported by huawei-cloud-waf-policy-query, supporting creation of new policies or overwriting existing ones. Triggers include: import WAF policy, create policy from JSON, overwrite WAF policy, JSON import protection policy"
tags: [WAF, Protection Policy, JSON Import, Policy Migration]
---

# WAF Protection Policy JSON Import

## Overview

This Skill is specifically designed to import WAF protection policies from JSON files exported by `huawei-cloud-waf-policy-query`, supporting:

- **Create New Policy** — Create an entirely new protection policy and all its rules based on a JSON file
- **Overwrite Existing Policy** — Update an existing policy's configuration and rebuild all rules
- **Automatic Mapping** — Automatically map JSON fields to corresponding CLI parameters
- **Batch Rule Creation** — Automatically create 11 types of protection rules

Suitable for scenarios such as policy migration, batch deployment, and environment synchronization.

## Parameter Conflict Resolution (--cli-jsonInput)

> [!IMPORTANT]
> **When API parameter names conflict with KooCLI system parameters (e.g., `--mode`), use `--cli-jsonInput` to pass a JSON file to bypass the conflict.**

### Affected Commands

| Command | Conflicting Parameter | API Meaning | KooCLI Meaning |
|---------|----------------------|-------------|----------------|
| `CreateCcRule` | `--mode` | Protection mode 0=Standard/1=Advanced | Output format json/table |
| `CreateIgnoreRule` | `--mode` | Fixed value 1=v2 false positive suppression | Output format |

### Solution: Using --cli-jsonInput

**Step 1**: Create a JSON file, categorized by `path` / `query` / `body` locations:

> **Important**: `path` must contain both `project_id` and `policy_id`, otherwise the error "Missing required parameter: project_id" will occur. `project_id` can be obtained from the response of a previous CreatePolicy or ShowPolicy call.

```json
{
  "path": {
    "project_id": "<project_id>",
    "policy_id": "<policy_id>"
  },
  "query": {},
  "body": {
    "name": "cc_rule_name",
    "mode": 1,
    "conditions": [
      {
        "category": "ip",
        "logic_operation": "equal",
        "contents": ["1.1.1.1"]
      }
    ],
    "action": {
      "category": "block"
    },
    "tag_type": "ip",
    "limit_num": 10,
    "limit_period": 60
  }
}
```

**Step 2**: Execute the command, using `--cli-jsonInput` to pass the JSON file path:

```bash
hcloud WAF CreateCcRule --cli-jsonInput=<json_file_path>
```

### JSON File Format Requirements

| Location | Description | Parameters Included |
|----------|-------------|-------------------|
| `path` | Path parameters | `project_id`, `policy_id` |
| `query` | Query parameters | `enterprise_project_id`, etc. (optional) |
| `body` | Request body parameters | `name`, `mode`, `conditions`, `action`, `tag_type`, `limit_num`, `limit_period`, etc. |

### Advantages

- Completely bypasses KooCLI system parameter conflicts
- Supports all nested object and array parameters
- Suitable for non-interactive environments (scripts, Agent tools)

## Workflow

### Initial Interaction (Fixed Procedure)

> [!CAUTION]
> **After loading this Skill, the following fixed procedure must be strictly followed. Do not change the order or format.**

**Step 0.1: Prerequisite Check**

Execute the following commands in parallel to verify the environment:

```bash
hcloud version
hcloud configure list
```

> [!IMPORTANT]
> **Version Requirement**: hcloud CLI version must be **>= 7.2.12**. If the version is lower, prompt the user to update with `hcloud update` or download the latest version.

**Step 0.2: Display Check Results and Collect Parameters**

After the prerequisite check is complete, you **must** output in the following fixed format, then wait for the user's response:

---

**WAF Protection Policy JSON Import**

Prerequisite Check:
- hcloud CLI Version: `<version>` (required >= 7.2.12) ✓/✗
- Configuration File: `<config_name>`, Region `<region>` ✓/✗

Please provide the following information:
1. **JSON File Path** — The policy file exported by `huawei-cloud-waf-policy-query`
2. **Import Mode** — `Create New Policy` or `Overwrite Existing Policy`

---

> [!IMPORTANT]
> **This initial interaction format must remain fixed and must not vary each time.** After the user responds, proceed to the "JSON Import Workflow" below.

### JSON Import Workflow

> [!IMPORTANT]
> **Mandatory Requirement**: Before performing any import operation, the JSON file source and import mode must be confirmed first.

1. **Confirm JSON Source** → Verify the file was exported by `huawei-cloud-waf-policy-query`
2. **Select Import Mode** → Create New Policy or Overwrite Existing Policy
3. **Collect Required Parameters** → Create New Policy mode: ask the user for a new policy name (name can only contain digits, letters, underscores, length <= 64); Overwrite mode: ask the user for the target policy ID
4. **Parse JSON Structure** → Extract `metadata`, `basic_info`, `module_status`, `rule_details`
5. **Validate Parameter Mapping** → Present the commands to be executed to the user and wait for confirmation
6. **Resolve Prerequisite Resources** → Scan `rule_details` for reference tables (`value_list`) and IP address groups (`ip_group`), query whether they already exist using `ListValueList` / `ListIpGroup` by ID or name, create if they don't exist, and record old ID → new ID mappings
7. **Create/Update Policy** → Execute CreatePolicy or UpdatePolicy
8. **Batch Create Rules** → Create rules module by module based on `rule_details`, using the reference table IDs and IP address group IDs resolved in Step 6
9. **Verify Import Results** → Query policy details to confirm all rules were created correctly

> [!IMPORTANT]
> **Create New Policy mode must ask the user for a new policy name before executing any write operation.** Do not use the source policy name from the JSON directly.

### Execution Discipline (MANDATORY)

> [!CAUTION]
> **The following rules are strictly enforced. Violations will result in duplicate creation, errors, or resource leaks.**

**E1. Sequential Execution for Policy Operations**

Policy creation/update operations **MUST be executed sequentially, NEVER in parallel**:

| Operation | Execution Rule | Reason |
|-----------|----------------|--------|
| `CreatePolicy` (Mode 1) | **Execute ALONE, wait for response** | Must extract `policy_id` and `project_id` before any other operation |
| `UpdatePolicy` | Execute after `CreatePolicy` completes | Depends on `policy_id` from creation response |
| `UpdatePolicy` (Mode 2) | **Execute ALONE, wait for response** | Must complete before deleting old rules |

**E2. Each Command Executed Exactly Once Across All Batches**

When organizing parallel tool calls, **it is strictly prohibited to place the same command in multiple parallel batches**. Each `Create*Rule` / `UpdatePolicy` / `BatchDeleteRules` / `Write` command may **appear only once** throughout the entire import workflow.

**Before constructing any parallel batch**, you must:
1. List ALL commands to be executed in that batch
2. Verify each command appears exactly once in the list
3. Cross-check against previous batches to ensure no command has been executed before

**E3. Batch Execution + Sequential Batch Verification**

Rule creation is divided into two batches, **which must be executed in order and cannot be merged**:

| Batch | Content | Reason |
|-------|---------|--------|
| Batch A | Temporary JSON file writes (Write tool) + Rule creation not dependent on JSON files (Bash tool) | File writes and rule creation can be parallelized |
| Batch B | Rule creation dependent on `--cli-jsonInput` (CC rules, Global Whitelist) | Must wait for Batch A's JSON file writes to complete before execution |

**Critical Rule**: Each batch must be executed as a **single parallel call**. Do NOT execute the same batch multiple times.

After each batch is executed, **the returned results must be checked** to confirm there are no unexpected errors before proceeding to the next batch.

**E4. Idempotent Error Handling**

The following error codes indicate that a rule **already exists** and should be treated as **successful** — **do not retry**:

| Error Code | Meaning | Handling |
|------------|---------|----------|
| `WAF.00021022` | Duplicated name (rule name already exists) | Skip, do not retry |
| `WAF.00022012` | Same condition rule already exists | Skip, do not retry |

**E5. Prohibit Duplicate Batches and Duplicate Commands Within Batches**

When constructing parallel calls, you must:
1. **List the command inventory** to be executed in the current batch
2. **Verify each command appears exactly once** in the inventory
3. **Cross-check against all previous batches** to ensure no command has been executed before
4. **Never submit the same batch twice** — if a batch has been executed, mark it as "✓ Completed" and never execute it again

**Common Mistake**: Accidentally placing the same `Write` or `Bash` command in multiple parallel calls within the same batch. This causes duplicate file writes or duplicate rule creation attempts.

**E6. Pre-Submission Count Verification (MANDATORY)**

> [!CAUTION]
> **This is the last line of defense against duplicate execution. It MUST be performed before every parallel batch submission.**

Before submitting any parallel batch of tool calls, you **MUST** perform the following count verification:

1. **Count your inventory**: Sum up the expected number of tool calls from the command inventory (e.g., 9 Bash + 2 Write = 11 total)
2. **Count your actual calls**: Count the number of tool call blocks you are about to submit in this message
3. **Compare**: If actual count ≠ expected count → **DUPLICATES EXIST** → stop immediately, identify and remove the extra calls
4. **Only submit when counts match exactly**

**Known Anti-Pattern (MUST NOT happen)**: Generating the entire command list twice in a single message, resulting in double the expected number of tool calls. For example: inventory says 11 commands, but 22 tool calls are submitted → the entire batch was duplicated.

**Verification Template** (must be completed before each batch):
```
Expected: X Bash + Y Write = Z total tool calls
Actual:   [count the tool call blocks being submitted] = N
Match?    Z == N → [ ] YES → proceed | [ ] NO → STOP, find duplicates
```

**E7. Unique Temporary File Naming**

When creating temporary JSON files for `--cli-jsonInput`, you must ensure the file name does not conflict with existing files:

1. **Check Before Creating**: Before writing a temporary JSON file, check if a file with the same name already exists
2. **Use Unique Names**: If a file with the intended name exists, generate a unique name by adding a suffix (e.g., timestamp, random string, or incrementing number)
3. **Recommended Naming Pattern**: Use `<rule_type>-<policy_id>-<timestamp>.json` to ensure uniqueness across different imports

**Example**:
```
# First attempt: waf-cc-rule.json (if exists)
# Second attempt: waf-cc-rule-1.json
# Third attempt: waf-cc-rule-2.json
# OR use timestamp: waf-cc-rule-1f88204a66654e6aba2d094d7e0a2629-1789094114.json
```

**Common Mistake**: Overwriting an existing temporary JSON file that is still being used by a previous command, causing incorrect parameters to be passed.

### Import Mode Description

#### Mode 1: Create New Policy

Create an entirely new protection policy from JSON, suitable for:
- Migrating policies to a new region
- Copying policies to a test environment
- Creating variants based on existing policies

**Execution Flow**:
```
Read JSON → Ask for new policy name → CreatePolicy (new policy) → Obtain policy_id → Batch create rules
```

#### Mode 2: Overwrite Existing Policy

Update an existing policy's configuration and rebuild all rules, suitable for:
- Policy configuration rollback
- Batch policy updates
- Policy configuration synchronization

**Execution Flow**:
```
Read JSON → UpdatePolicy (update configuration) → Delete old rules → Batch create new rules
```

> [!WARNING]
> Overwrite mode will delete all existing rules of the target policy. Please confirm before proceeding.

## Core Commands

### Step 1: Read JSON File, Validate Format, and Collect Parameters

```powershell
# Read JSON file
$json = Get-Content -Path "<json_file_path>" -Raw | ConvertFrom-Json

# Validate required fields
if (-not $json.metadata -or -not $json.basic_info -or -not $json.rule_details) {
    Write-Error "Invalid JSON format, missing required fields"
    exit 1
}

# Display policy basic information
Write-Host "Source Policy Name: $($json.basic_info.policy_name)"
Write-Host "Protection Level: $($json.basic_info.level)"
Write-Host "Default Action: $($json.basic_info.default_action)"
Write-Host "Region: $($json.metadata.region)"

# Parse module_status and build --options.* parameters for UpdatePolicy
# Exclude ip_reputation because it does not exist in UpdatePolicy's --options parameter list
$excludedModules = @("ip_reputation")
$optionsParams = @()
foreach ($module in $json.module_status) {
    if ($excludedModules -contains $module.module) { continue }
    $enabledStr = $module.enabled.ToString().ToLower()
    $optionsParams += "--options.$($module.module)=$enabledStr"
}
Write-Host "Options Parameters: $($optionsParams -join ' ')"
```

**Collect Required Parameters** (complete after parsing JSON and before executing any write operations):

| Import Mode | Required Parameter | Description |
|-------------|-------------------|-------------|
| Create New Policy | **New Policy Name** | Display the source policy name and ask the user for the new name to use. Name can only contain digits, letters, underscores, length <= 64 |
| Overwrite Existing Policy | **Target Policy ID** | Ask the user for the target policy ID to overwrite (can be obtained via ListPolicy) |

> [!IMPORTANT]
> **Create New Policy mode must ask the user for a new policy name before executing any write operation.** Do not use the source policy name (`basic_info.policy_name`) from the JSON directly. The source policy name is displayed to the user for reference only.

### Step 2: Create or Update Policy

#### Mode 1: Create New Policy

> [!CAUTION]
> **CreatePolicy MUST be executed as a SINGLE standalone call. Do NOT execute it in parallel with any other commands.**
> 
> **Correct**: Execute `CreatePolicy` alone → wait for response → extract `policy_id` and `project_id` → proceed to next step
> 
> **Incorrect**: Execute `CreatePolicy` in parallel with `UpdatePolicy` or other commands → causes duplicate creation or missing `policy_id`

```bash
# Step 1: CreatePolicy - creates policy with default configuration
# THIS COMMAND MUST BE EXECUTED ALONE - DO NOT INCLUDE IN PARALLEL BATCH
hcloud WAF CreatePolicy \
  --name=<user-specified new policy name>

# Step 2: Extract policy_id and project_id from CreatePolicy response
# Also extract the "options" object from the response - this contains the current module states
```

> [!IMPORTANT]
> `CreatePolicy` does not accept `--level` and `--action.category` parameters. After creation, defaults are level=2, action=log. If modifications are needed, you must create the policy first, then call `UpdatePolicy`.

**Step 3: Compare and Build Differential UpdatePolicy Command**

After CreatePolicy returns, compare the JSON's `module_status` with the `options` object from the CreatePolicy response:

1. For each module in `module_status` (excluding `ip_reputation`):
   - Check if the module exists in the CreatePolicy response's `options` object
   - If it exists AND the value differs from the JSON's `enabled` field → include `--options.<module>=<json_value>` in the command
   - If it does NOT exist in the response → **skip this module** (likely not supported by current WAF specification)
   - If the values match → **skip this module** (no change needed)

2. Similarly compare `basic_info.level` and `basic_info.default_action`:
   - If `level` differs from response → include `--level=<basic_info.level>`
   - If `default_action` differs from response `action.category` → include `--action.category=<basic_info.default_action>`

3. If NO differences found at all → **skip UpdatePolicy entirely** and proceed to rule creation

Example comparison:
```json
// JSON module_status says: webshell.enabled = true
// CreatePolicy response options says: webshell = false
// → Include: --options.webshell=true

// JSON module_status says: bot_enable.enabled = true  
// CreatePolicy response options says: bot_enable = true
// → Skip (values match)

// JSON module_status says: some_new_feature.enabled = true
// CreatePolicy response options: field does not exist
// → Skip (not supported by current specification)
```

Execute UpdatePolicy only with the differing parameters:
```bash
# Only include parameters that differ from CreatePolicy response
# Example: if only webshell and followed_action differ
hcloud WAF UpdatePolicy \
  --policy_id=<newly created policy_id> \
  --level=2 \
  --action.category=log \
  --options.webshell=true \
  --options.followed_action=true
```

> [!WARNING]
> **Why differential update?** Some WAF specifications do not support all modules. Passing unsupported module options will cause error `WAF.00013002: The feature is not supported in the current specification`. By comparing with CreatePolicy response first, we only update modules that are both supported AND need changes.

**JSON Field Mapping**:
| JSON Field | CLI Parameter | Description |
|------------|--------------|-------------|
| User-specified | `--name` | New policy name (asked from user in Step 1, not using the source policy name from JSON) |
| `module_status[*].enabled` | `--options.<module>` | Module switch status (true/false), ONLY if differs from CreatePolicy response |

> [!NOTE]
> **Module Status Processing**: Compare each module in `module_status` array against the `options` object returned by CreatePolicy. Only generate `--options.<module>` parameters for modules where the values differ. Modules not present in the CreatePolicy response should be skipped entirely. **Note**: The `ip_reputation` module is always excluded because it cannot be modified via UpdatePolicy.

> **Policy Name Conflict Handling**: Since the user is asked for a new policy name in Step 1, name conflicts should not normally occur. If `WAF.00011016: Duplicate name` is still returned, ask the user for a new name and retry.

After successful creation (and optional UpdatePolicy), extract `id` from the CreatePolicy response as the new `policy_id`. Also extract `project_id` from the response, which will be needed for subsequent `--cli-jsonInput` commands.

#### Mode 2: Overwrite Existing Policy

```bash
# Step 1: Query the current state of target policy
hcloud WAF ShowPolicy --policy_id=<target_policy_id>

# Step 2: Extract the "options" object, "level", and "action.category" from ShowPolicy response
# These represent the CURRENT state of the target policy

# Step 3: Compare and Build Differential UpdatePolicy Command
# Compare JSON's module_status with ShowPolicy response's options:
# - If a module value DIFFERS → include in UpdatePolicy command
# - If a module value MATCHES → skip (no change needed)
# - If a module is NOT in ShowPolicy response → skip (not supported by specification)
# - Also compare basic_info.level and basic_info.default_action

# Execute UpdatePolicy only with differing parameters
# Example: if level, webshell, and followed_action differ from current state
hcloud WAF UpdatePolicy \
  --policy_id=<target_policy_id> \
  --level=2 \
  --action.category=log \
  --options.webshell=true \
  --options.followed_action=true
```

> [!IMPORTANT]
> **Do not modify the policy name in overwrite mode.** If you attempt to rename the target policy to the source policy name (`--name=<basic_info.policy_name>`) and that name already exists, the error `WAF.00011016: Duplicate name` will occur. Keep the target policy's original name.

**Step-by-Step Comparison Logic:**

1. For each module in `module_status` (excluding `ip_reputation`):
   - Check if the module exists in ShowPolicy response's `options` object
   - If it exists AND the value differs from JSON's `enabled` field → include `--options.<module>=<json_value>`
   - If it does NOT exist in response → **skip** (likely not supported by current WAF specification)
   - If values match → **skip** (no change needed)

2. Compare `basic_info.level` with ShowPolicy response's `level`:
   - If different → include `--level=<basic_info.level>`

3. Compare `basic_info.default_action` with ShowPolicy response's `action.category`:
   - If different → include `--action.category=<basic_info.default_action>`

4. If NO differences found at all → **skip UpdatePolicy entirely** and proceed to delete old rules

Example comparison:
```json
// JSON says: webshell.enabled = true
// ShowPolicy says: webshell = false
// → Include: --options.webshell=true

// JSON says: bot_enable.enabled = true
// ShowPolicy says: bot_enable = true
// → Skip (values match)

// JSON says: some_new_feature.enabled = true
// ShowPolicy response: field does not exist
// → Skip (not supported by current specification)
```

> [!WARNING]
> **Why differential update?** Same reason as Mode 1: Some WAF specifications do not support all modules. Passing unsupported module options will cause error `WAF.00013002: The feature is not supported in the current specification`. By comparing with ShowPolicy response first, we only update modules that are both supported AND need changes.

**Module Status Processing**: Compare each module in `module_status` array against the `options` object returned by ShowPolicy. Only generate `--options.<module>` parameters for modules where the values differ. Modules not present in the ShowPolicy response should be skipped entirely. **Note**: The `ip_reputation` module is always excluded because it cannot be modified via UpdatePolicy.

**Delete Old Rules** (module by module):

> [!IMPORTANT]
> **BatchDeleteRules Parameter Format**: Use `--policy_rule_ids.N.policy_id` and `--policy_rule_ids.N.rule_ids.M`, not `--policy_id` and `--rule_ids`.

```bash
# Delete precise protection rules
hcloud WAF BatchDeleteRules --rule_type=custom --policy_rule_ids.1.policy_id=<policy_id> --policy_rule_ids.1.rule_ids.1=<id1> --policy_rule_ids.1.rule_ids.2=<id2>

# Delete CC attack protection rules
hcloud WAF BatchDeleteRules --rule_type=cc --policy_rule_ids.1.policy_id=<policy_id> --policy_rule_ids.1.rule_ids.1=<id1>

# Delete blacklist/whitelist rules
hcloud WAF BatchDeleteRules --rule_type=whiteblackip --policy_rule_ids.1.policy_id=<policy_id> --policy_rule_ids.1.rule_ids.1=<id1>

# Delete geo-access control rules
hcloud WAF BatchDeleteRules --rule_type=geoip --policy_rule_ids.1.policy_id=<policy_id> --policy_rule_ids.1.rule_ids.1=<id1>

# Delete global whitelist rules
hcloud WAF BatchDeleteRules --rule_type=ignore --policy_rule_ids.1.policy_id=<policy_id> --policy_rule_ids.1.rule_ids.1=<id1>

# Delete anti-crawler rules (use independent API, not BatchDeleteRules)
# First get rule IDs via: hcloud WAF ListAnticrawlerRules --policy_id=<policy_id>
hcloud WAF DeleteAnticrawlerRule --policy_id=<policy_id> --rule_id=<id1>

# Delete privacy masking rules
hcloud WAF BatchDeleteRules --rule_type=privacy --policy_rule_ids.1.policy_id=<policy_id> --policy_rule_ids.1.rule_ids.1=<id1>

# Delete web anti-tampering rules
hcloud WAF BatchDeleteRules --rule_type=antitamper --policy_rule_ids.1.policy_id=<policy_id> --policy_rule_ids.1.rule_ids.1=<id1>

# Delete sensitive data leakage prevention rules
hcloud WAF BatchDeleteRules --rule_type=antileakage --policy_rule_ids.1.policy_id=<policy_id> --policy_rule_ids.1.rule_ids.1=<id1>

# Delete threat intelligence access control rules
hcloud WAF BatchDeleteRules --rule_type=ip-reputation --policy_rule_ids.1.policy_id=<policy_id> --policy_rule_ids.1.rule_ids.1=<id1>

# Delete attack punishment rules (use independent API, not BatchDeleteRules)
# First get rule IDs via: hcloud WAF ListPunishmentRules --policy_id=<policy_id>
hcloud WAF DeletePunishmentRule --policy_id=<policy_id> --rule_id=<id1>
```

> [!NOTE]
> If a module has no rules, the corresponding delete command will return empty results and will not affect subsequent operations.

### Step 3: Batch Create Rules

> [!CAUTION]
> **Pre-execution Checklist (Must Be Completed)**:
> 1. Confirm Step 2 (policy creation/update) is complete
> 2. Confirm prerequisite resource resolution (reference tables, IP address groups) is complete
> 3. Confirm a complete command inventory has been established (see "Batch Execution Rules" below)
> 4. Confirm **no batch has been executed yet** (first execution of Step 3)

Create rules in the following order based on the modules in `rule_details`.

> [!CAUTION]
> **Batch Execution Rules (see "Execution Discipline" section)**:
>
> **Before execution**, scan `rule_details` first to establish a complete command inventory, marking each command's batch assignment:
>
> | Batch | Included Commands | Dependencies | Execution Status |
> |-------|-------------------|-------------|-----------------|
> | **Batch A** | Write temporary JSON files (CC rules, Global Whitelist) + All rule creation commands not dependent on `--cli-jsonInput` (Precise Protection, Blacklist/Whitelist, Geo-Access Control, Privacy Masking, Web Anti-Tampering, Threat Intelligence, Attack Punishment) | No prerequisite dependencies; file writes and rule creation can be parallelized | □ Pending |
> | **Batch B** | Rule creation commands dependent on `--cli-jsonInput` (CC rules `CreateCcRule`, Global Whitelist `CreateIgnoreRule`) | Must wait for Batch A's JSON file writes to succeed | □ Pending |
>
> **Execution Requirements**:
> 1. Batch A and Batch B **must be executed in order** and cannot be merged into the same parallel call
> 2. Each command may **appear only once** throughout Step 3 and must not be repeatedly submitted across multiple batches
> 3. **Batch Execution Tracking**: Before executing each batch, you must explicitly list all commands it contains; after execution, mark each as completed. Batches marked as "✓ Completed" **must not be executed again**
> 4. After each batch execution, check the returned results. If `WAF.00021022` (Duplicated name) or `WAF.00022012` (Same condition rule already exists) appears, treat it as the rule already existing — **skip without retry**
> 5. After all batches are complete, proceed to Step 4 for verification
> 6. **Temporary File Naming**: Before writing temporary JSON files (for CC rules and Global Whitelist), **check if files with the intended names already exist**. If they do, use unique names (e.g., add timestamp or incrementing suffix like `-1`, `-2`). See **E6. Unique Temporary File Naming** in the Execution Discipline section for details.
>
> **Command Inventory Template** (must be filled out before executing Batch A):
>
> ```
> Batch A Command Inventory:
> - Write: <temp_json_path_cc> (CC rule JSON)
> - Write: <temp_json_path_ignore> (Global whitelist JSON)
> - Bash: CreateCustomRule (rule 1) - if custom rules exist
> - Bash: CreateCustomRule (rule 2) - if custom rules exist
> - Bash: CreateWhiteblackipRule - if whiteblackip rules exist
> - Bash: CreateGeoipRule - if geoip rules exist
> - Bash: CreatePrivacyRule - if privacy rules exist
> - Bash: CreateAntiTamperRule - if antitamper rules exist
> - Bash: CreateAntileakageRule - if antileakage rules exist
> - Bash: CreateIpReputationRule - if ip_reputation rules exist
> - Bash: CreatePunishmentRule - if followed_action rules exist
> 
> Verification: Each command appears exactly once? [ ] YES [ ] NO
> If NO, remove duplicates before proceeding.
> ```
>
> **Common Mistakes to Avoid**:
> - ❌ Executing the same `CreateCustomRule` command multiple times in Batch A
> - ❌ Including `Write` and `Bash` commands for the same rule in both Batch A and Batch B
> - ❌ Executing Batch A, then executing Batch A again (duplicate batch execution)
> - ❌ Executing `CreateCcRule` in Batch A instead of Batch B (CC rules require `--cli-jsonInput`)

#### 3.1 Precise Protection Rules

> [!IMPORTANT]
> **Reference Table (ValueList) Pre-processing**: If a rule's `logic_operation` ends with `_any` or `_all` (e.g., `contain_any`, `equal_any`), then `--conditions.N.value_list_id` must be used, and `--conditions.N.contents.M` **cannot** be used.

**Prerequisite Step: Check Reference Table Dependencies**

Iterate through each rule's conditions and check whether `logic_operation` ends with `_any` or `_all`:

1. Extract `conditions[N].value_list_id` from JSON
2. **Three-level fallback lookup for reference table**:
   - **Level 1 (Exact query by ID)**:
     ```bash
     hcloud WAF ShowValueList --valuelistid=<value_list_id>
     ```
     If successful (no error code), directly reuse this `value_list_id`
   - **Level 2 (Fuzzy query by name)**: If Level 1 returns an error (e.g., `WAF.00011004: Illegal id`), extract `value_list_detail.name` from JSON, then:
     ```bash
     hcloud WAF ListValueList --name=<value_list_detail.name>
     ```
     If results are returned and `total > 0`, find the matching record by name from the returned list and reuse its `id`
   - **Level 3 (Create new reference table)**: If neither of the above levels found it, create a new reference table:
     ```bash
     hcloud WAF CreateValueList \
            --name=<value_list_detail.name>_copy \
       --type=<value_list_detail.type> \
       --values.1=<value1> \
       --values.2=<value2> \
       --values.3=<value3>
     ```
     Extract the new `id` from the response and record the old ID → new ID mapping

**Case A: Normal Conditions (logic_operation does NOT end with `_any`/`_all`)**

```bash
hcloud WAF CreateCustomRule \
  --policy_id=<policy_id> \
  --name=<rule.name> \
  --priority=<rule.priority> \
  --action.category=<rule.action.category> \
  --conditions.1.category=<rule.conditions[0].category> \
  --conditions.1.logic_operation=<rule.conditions[0].logic_operation> \
  --conditions.1.contents.1=<rule.conditions[0].contents[0]> \
  --time=false
```

**Case B: Reference Table Conditions (logic_operation ends with `_any`/`_all`)**

```bash
hcloud WAF CreateCustomRule \
  --policy_id=<policy_id> \
  --name=<rule.name> \
  --priority=<rule.priority> \
  --action.category=<rule.action.category> \
  --conditions.1.category=<rule.conditions[0].category> \
  --conditions.1.logic_operation=<rule.conditions[0].logic_operation> \
  --conditions.1.value_list_id=<value_list_id> \
  --time=false
```

> [!WARNING]
> In Case B, do **NOT** pass `--conditions.N.contents.M`, otherwise the error `WAF.00021017: Missing field or illegal field value` will occur. `value_list_id` and `contents` are mutually exclusive.

**JSON Field Mapping**:
| JSON Field | CLI Parameter |
|------------|--------------|
| `rule.name` | `--name` |
| `rule.priority` | `--priority` |
| `rule.action.category` | `--action.category` |
| `rule.conditions[N].category` | `--conditions.N.category` |
| `rule.conditions[N].logic_operation` | `--conditions.N.logic_operation` |
| `rule.conditions[N].contents[M]` | `--conditions.N.contents.M` (normal conditions only) |
| `rule.conditions[N].value_list_id` | `--conditions.N.value_list_id` (reference table conditions only) |
| `rule.time` | `--time` (false = effective immediately) |

#### 3.2 CC Attack Protection Rules

> [!IMPORTANT]
> The `--mode` parameter conflicts with KooCLI system parameters. You **must use `--cli-jsonInput`** to create these rules.
> See the "Parameter Conflict Resolution (--cli-jsonInput)" section above.

**Step 1**: Based on the CC rule data in JSON, create a temporary JSON file:

> **Note**: `path` must contain both `project_id` and `policy_id`.

> [!IMPORTANT]
> **Temporary File Naming**: Before creating the file, check if a file with your intended name already exists. If it does, use a unique name by adding a suffix (e.g., `-1`, `-2`) or timestamp. See **E6. Unique Temporary File Naming** in the Execution Discipline section.

> [!IMPORTANT]
> **CC Rule `mode` Determination**: The source JSON may not contain a `mode` field. Determine `mode` based on the condition categories:
> - **`mode: 0` (Standard)**: Only supports `url` category conditions. If ALL conditions have `category: "url"`, use mode 0.
> - **`mode: 1` (Advanced)**: Supports `ip`, `cookie`, `header`, `params`, `url` and other categories. If ANY condition has a category other than `url`, **must use mode 1**.
> - Using mode 0 with non-url conditions (e.g., `category: "ip"`) will cause `WAF.00021017: Illegal path` error.
> - **When in doubt, default to `mode: 1`** (Advanced mode is a superset of Standard mode).

```json
{
  "path": {
    "project_id": "<project_id>",
    "policy_id": "<policy_id>"
  },
  "query": {},
  "body": {
    "name": "<rule.name>",
    "mode": <determined_mode_value>,
    "conditions": [
      {
        "category": "<rule.conditions[0].category>",
        "logic_operation": "<rule.conditions[0].logic_operation>",
        "contents": ["<rule.conditions[0].contents[0]>"]
      }
    ],
    "action": {
      "category": "<rule.action.category>"
    },
    "tag_type": "<rule.tag_type>",
    "limit_num": <rule.limit_num>,
    "limit_period": <rule.limit_period>
  }
}
```

**Step 2**: Execute the command:

```bash
hcloud WAF CreateCcRule --cli-jsonInput=<temp_json_path>
```

**JSON Field Mapping**:
| JSON Field | CLI Parameter (in JSON body) |
|------------|------------------------------|
| `rule.name` | `body.name` |
| Determined from conditions | `body.mode` (0=Standard: url only; 1=Advanced: all categories) |
| `rule.limit_num` | `body.limit_num` |
| `rule.limit_period` | `body.limit_period` |
| `rule.tag_type` | `body.tag_type` |
| `rule.action.category` | `body.action.category` |

#### 3.3 Blacklist/Whitelist Rules

> [!IMPORTANT]
> **IP Address Group Pre-processing**: `--addr` only accepts a single IP/CIDR (e.g., `42.123.120.66` or `42.123.120.0/16`). If the JSON rule uses `ip_group` (multiple IPs), then `--ip_group_id` must be used, and `--addr` **cannot** be used.

##### Prerequisite Step: Check IP Address Group Dependencies

Check whether the JSON rule uses `addr` (single IP) or `ip_group` (IP address group):

1. If the JSON contains `rule.ip_group` field (instead of `rule.addr`), then IP address group handling is required
2. Extract `ip_group.id` from JSON
3. **Three-level fallback lookup for IP address group**:
   - **Level 1 (Exact query by ID)**:
     ```bash
     hcloud WAF ShowIpGroup --id=<ip_group.id>
     ```
     If successful (no error code), directly use this `ip_group_id`
   - **Level 2 (Fuzzy query by name)**: If Level 1 returns an error (e.g., `WAF.00014001: Resource not found`), extract `ip_group.name` from JSON, then:
     ```bash
     hcloud WAF ListIpGroup --name=<ip_group.name>
     ```
     If results are returned and `total > 0`, find the matching record by name from the returned list and use its `id`
   - **Level 3 (Create new IP address group)**: If neither of the above levels found it, create a new IP address group:
     ```bash
     hcloud WAF CreateIpGroup \
            --name=<ip_group.name>_copy \
       --ips=<ip_group.detail.ips>
     ```
     Extract the new `id` from the response and record the old ID → new ID mapping

##### Case A: Single IP (JSON contains `rule.addr`)

```bash
hcloud WAF CreateWhiteblackipRule \
  --policy_id=<policy_id> \
  --name=<rule.name> \
  --white=<rule.white> \
  --addr=<rule.addr>
```

##### Case B: IP Address Group (JSON contains `rule.ip_group`)

```bash
hcloud WAF CreateWhiteblackipRule \
  --policy_id=<policy_id> \
  --name=<rule.name> \
  --white=<rule.white> \
  --ip_group_id=<ip_group_id>
```

> [!WARNING]
> In Case B, do **NOT** pass `--addr`. `addr` and `ip_group_id` are mutually exclusive; when both are present, `addr` takes precedence (`ip_group_id` will be ignored).

**JSON Field Mapping**:
| JSON Field | CLI Parameter |
|------------|--------------|
| `rule.name` | `--name` |
| `rule.white` | `--white` (0=block, 1=allow, 2=log only) |
| `rule.addr` | `--addr` (single IP scenarios only) |
| `rule.ip_group.id` | `--ip_group_id` (IP address group scenarios only) |

#### 3.4 Geo-Access Control Rules

> [!WARNING]
> **CreateGeoipRule Known False Failure**: This command may return an error response even though the rule was successfully created on the server side. After executing `CreateGeoipRule`, if any error is returned:
> 1. Run `hcloud WAF ListGeoipRule --policy_id=<policy_id>` immediately
> 2. Check if a rule matching the expected name exists in the returned list
> 3. If found → **treat as successful creation**, proceed to next rule. **Do NOT retry CreateGeoipRule**
> 4. If not found → genuine failure, report to user
>
> **Do NOT enter a check-and-retry loop.** One verification is enough. If the rule exists, move on.

> **Important**: `geoTagList` in JSON is an array (e.g., `["BJ", "Afghanistan"]`), but the CLI's `--geoip` parameter requires multiple region codes joined with `|` separator. The JSON array must be converted to a `|`-delimited string.

```bash
# geoTagList in JSON: ["BJ", "Afghanistan"]
# Convert to CLI parameter: --geoip="BJ|Afghanistan"

hcloud WAF CreateGeoipRule \
  --policy_id=<policy_id> \
  --name=<rule.name> \
  --geoip="<region1>|<region2>|..." \
  --white=<rule.white>
```

**Conversion Rule**:
```powershell
# Convert from JSON array to |-delimited string
$geoipString = ($rule.geoTagList -join "|")
# Or for cases containing Chinese/special characters
$geoipString = "BJ|Afghanistan"
```

**JSON Field Mapping**:
| JSON Field | CLI Parameter | Conversion Description |
|------------|--------------|----------------------|
| `rule.name` | `--name` | Direct use |
| `rule.geoTagList` | `--geoip` | Array joined with `|`, e.g., `["BJ","CN"]` → `"BJ|CN"` |
| `rule.white` | `--white` | Direct use |

#### 3.5 Global Whitelist Rules

> [!IMPORTANT]
> The `--mode` parameter conflicts with KooCLI system parameters. You **must use `--cli-jsonInput`** to create these rules.
> See the "Parameter Conflict Resolution (--cli-jsonInput)" section above.

**Step 1**: Based on the global whitelist rule data in JSON, create a temporary JSON file:

> **Note**: `path` must contain both `project_id` and `policy_id`.

> [!IMPORTANT]
> **Temporary File Naming**: Before creating the file, check if a file with your intended name already exists. If it does, use a unique name by adding a suffix (e.g., `-1`, `-2`) or timestamp. See **E6. Unique Temporary File Naming** in the Execution Discipline section.

> [!NOTE]
> **Global Whitelist API does NOT require `name`**: The `CreateIgnoreRule` API parameters are `conditions`, `domain`, `mode`, `rule`, and optional `advanced`/`description`. There is no `name` field. Do not inject a `name` into the temp JSON body.

```json
{
  "path": {
    "project_id": "<project_id>",
    "policy_id": "<policy_id>"
  },
  "query": {},
  "body": {
    "mode": 1,
    "conditions": [
      {
        "category": "<rule.conditions[0].category>",
        "logic_operation": "<rule.conditions[0].logic_operation>",
        "contents": ["<rule.conditions[0].contents[0]>"]
      }
    ],
    "rule": "<rule.rule>",
    "domain": ["<rule.domain[0]>", "<rule.domain[1]>"]
  }
}
```

> [!WARNING]
> The `domain` field must contain the actual domain list from the JSON rule data (e.g., `["sada.com"]`), **NOT** an empty array `[]`. Using `[]` will cause the rule to apply to all domains, which is usually not the intended behavior.

**Step 2**: Execute the command:

```bash
hcloud WAF CreateIgnoreRule --cli-jsonInput=<temp_json_path>
```

**JSON Field Mapping**:
| JSON Field | CLI Parameter (in JSON body) |
|------------|------------------------------|
| `rule.rule` | `body.rule` |
| `rule.conditions[N].*` | `body.conditions[N].*` |
| Fixed value | `body.mode` = 1 |

#### 3.6 Anti-Crawler Rules

```bash
hcloud WAF CreateAnticrawlerRule \
  --policy_id=<policy_id> \
  --name=<rule.name> \
  --type=<rule.type> \
  --priority=<rule.priority> \
  --conditions.1.category=<rule.conditions[0].category> \
  --conditions.1.logic_operation=<rule.conditions[0].logic_operation> \
  --conditions.1.contents.1=<rule.conditions[0].contents[0]>
```

#### 3.7 Privacy Masking Rules

```bash
hcloud WAF CreatePrivacyRule \
  --policy_id=<policy_id> \
  --url=<rule.url> \
  --category=<rule.category> \
  --index=<rule.index>
```

#### 3.8 Web Anti-Tampering Rules

> **Note**: The domain name specified by the `--hostname` parameter does not need to be pre-bound to the policy or exist in the WAF protected domain list. Rules can be created directly using the hostname value from JSON.

```bash
hcloud WAF CreateAntiTamperRule \
  --policy_id=<policy_id> \
  --hostname=<rule.hostname> \
  --url=<rule.url>
```

#### 3.9 Sensitive Data Leakage Prevention Rules

```bash
hcloud WAF CreateAntileakageRule \
  --policy_id=<policy_id> \
  --url=<rule.url> \
  --category=<rule.category> \
  --contents.1=<rule.contents[0]>
```

#### 3.10 Threat Intelligence Access Control Rules

> **Description**: Threat intelligence rules are used for access control based on IP reputation databases (e.g., IDC datacenter IPs). The command is `CreateIpReputationRule`.

```bash
hcloud WAF CreateIpReputationRule \
  --policy_id=<policy_id> \
  --name=<rule.name> \
  --action.category=<rule.action.category> \
  --type=<rule.type> \
  --tags.1=<rule.tags[0]> \
  --tags.2=<rule.tags[1]>
```

> **Note**: The `--tags.N` parameter format is `--tags.1=value1 --tags.2=value2`, with each tag as a separate parameter. `--type` currently only supports `idc`.

**JSON Field Mapping**:
| JSON Field | CLI Parameter | Description |
|------------|--------------|-------------|
| `rule.name` | `--name` | Rule name |
| `rule.action.category` | `--action.category` | Action type (block/log/pass) |
| `rule.type` | `--type` | Reputation type, currently only supports `idc` |
| `rule.tags` | `--tags.N` | Tag list, e.g., `["Dr.Peng"]` → `--tags.1=Dr.Peng` |

#### 3.11 Attack Punishment Rules

> **Description**: Attack punishment rules automatically block visitors who trigger WAF blocking rules multiple times within a specified time period. The command is `CreatePunishmentRule`.

```bash
hcloud WAF CreatePunishmentRule \
  --policy_id=<policy_id> \
  --category=<rule.category> \
  --block_time=<rule.block_time> \
  --time_unit=<rule.time_unit> \
  --description=<rule.description>
```

> **Note**: 
> - `--category` specifies the punishment category (e.g., `long_ip_block`, `short_ip_block`). Each category can only have one rule.
> - `--block_time` specifies the punishment duration in the unit specified by `--time_unit`.
> - `--time_unit` can be `SECOND`, `MINUTE`, `HOUR`, `DAY`, or `MONTH`. Default is `SECOND`.
> - `--description` is optional but recommended for documentation purposes.

**JSON Field Mapping**:
| JSON Field | CLI Parameter | Description |
|------------|--------------|-------------|
| `rule.category` | `--category` | Punishment category (e.g., `long_ip_block`) |
| `rule.block_time` | `--block_time` | Punishment duration (integer) |
| `rule.time_unit` | `--time_unit` | Time unit (`SECOND`/`MINUTE`/`HOUR`/`DAY`/`MONTH`) |
| `rule.description` | `--description` | Rule description (optional) |

### Step 4: Verify Import Results

```bash
# Query policy details (includes rules_count field showing rule counts per module)
hcloud WAF ShowPolicy --policy_id=<policy_id>

# Query rules for each module (verify one by one)
# 1. Precise protection rules
hcloud WAF ListCustomRules --policy_id=<policy_id>

# 2. CC attack protection rules
hcloud WAF ListCcRules --policy_id=<policy_id>

# 3. Blacklist/whitelist rules
hcloud WAF ListWhiteblackipRule --policy_id=<policy_id>

# 4. Geo-access control rules
hcloud WAF ListGeoipRule --policy_id=<policy_id>

# 5. Global whitelist rules
hcloud WAF ListIgnoreRule --policy_id=<policy_id>

# 6. Anti-crawler rules
hcloud WAF ListAnticrawlerRules --policy_id=<policy_id>

# 7. Privacy masking rules
hcloud WAF ListPrivacyRule --policy_id=<policy_id>

# 8. Web anti-tampering rules
hcloud WAF ListAntitamperRule --policy_id=<policy_id>

# 9. Sensitive data leakage prevention rules
hcloud WAF ListAntileakageRules --policy_id=<policy_id>

# 10. Threat intelligence access control rules
hcloud WAF ListIpReputationRules --policy_id=<policy_id>

# 11. Attack punishment rules
hcloud WAF ListPunishmentRules --policy_id=<policy_id>
```

**Verification Points**:
- Compare the `rules_count` field returned by `ShowPolicy` to confirm the number of rules per module matches the JSON
- Query each module's rule list individually to confirm rule content (name, conditions, actions, etc.) is correct
- Check that rule status is enabled (status=1)

## Parameter Confirmation

### Required JSON Fields

| JSON Field | Source | Description |
|------------|--------|-------------|
| `metadata.region` | huawei-cloud-waf-policy-query | Source region (informational only; hcloud uses configured default region) |
| `metadata.policy_id` | huawei-cloud-waf-policy-query | Source policy ID (used in overwrite mode) |
| `metadata.policy_name` | huawei-cloud-waf-policy-query | Policy name |
| `basic_info.level` | huawei-cloud-waf-policy-query | Protection level (1-3) |
| `basic_info.default_action` | huawei-cloud-waf-policy-query | Default action (block/log) |
| `basic_info.bind_hosts` | huawei-cloud-waf-policy-query | Bound domain list |
| `basic_info.full_detection` | huawei-cloud-waf-policy-query | Precise protection detection mode |
| `module_status` | huawei-cloud-waf-policy-query | Protection module toggle status |
| `rule_details` | huawei-cloud-waf-policy-query | Rule details per module |

### Parameters Requiring User Confirmation

| Parameter | Required | Description | Source |
|-----------|----------|-------------|--------|
| JSON file path | Yes | JSON file exported by huawei-cloud-waf-policy-query | User provided |
| Import mode | Yes | Create New Policy / Overwrite Existing Policy | User selection |
| **New policy name** | **Required for Create New Policy mode** | **Name of the new policy (must not duplicate existing policies)** | **Specified by user in Step 1; do not use the source policy name from JSON** |
| Target policy ID | Required for overwrite mode | Target policy ID to overwrite | User specified (obtained via ListPolicy) |

## Reference Documents

- [CLI Installation and Configuration Guide](references/cli-installation-guide.md)
- [IAM Permission Policy Configuration](references/iam-policies.md)
- [Verification Methods](references/verification-method.md)
- [Data Flow Diagram](references/dataflow-diagram.md)
- [Acceptance Criteria](references/acceptance-criteria.md)

## KooCLI Command Format Standard

```bash
hcloud <Service> <Operation> [--key=value ...]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | Exact KooCLI service name, first letter capitalized | WAF |
| Operation name | PascalCase naming | CreatePolicy, CreateCustomRule |
| Nested parameters | --key.subkey=value | --action.category=block |
| Indexed parameters | --key.N=value | --conditions.1.category=url |
| Array parameters | --key.N.contents.M=value | --conditions.1.contents.1=/admin |

## Hard Constraints (MANDATORY)

1. **JSON Source Validation**: Importing JSON files not exported by `huawei-cloud-waf-policy-query` is strictly prohibited. If the JSON format does not match, the import must be refused and the user must be informed.
2. **Write Operation Confirmation**: All write operations (CreatePolicy/UpdatePolicy/CreateXxxRule/BatchDeleteRules) must present the commands to be executed to the user and wait for confirmation before execution.
3. **Overwrite Mode Warning**: Overwrite mode will delete all existing rules of the target policy. The user must be explicitly informed and confirmed before execution.
4. **No Credential Leakage**: Exposing sensitive configuration information such as AK/SK, Project ID, etc. in output is strictly prohibited.

## Notes

- JSON files must be exported by `huawei-cloud-waf-policy-query` and contain four top-level fields: `metadata`, `basic_info`, `module_status`, `rule_details`
- When creating a new policy, the policy name must not duplicate existing policies (name can only contain digits, letters, underscores, length <= 64). **The user must be asked for the new policy name before creating the policy**; do not use the source policy name from JSON directly
- The `--mode` parameter for CC rules and global whitelist conflicts with KooCLI system parameters. You **must use `--cli-jsonInput`** to create them (see the "Parameter Conflict Resolution" section); the `--mode` command-line parameter cannot be used directly
- The priority range for precise protection rules is 0-65535; lower values indicate higher priority
- The `white` parameter for blacklist/whitelist: 0=block, 1=allow, 2=log only
- In overwrite mode, rule deletion uses `BatchDeleteRules`; existing rule IDs must be queried first
- Command names are case-sensitive and singular/plural-sensitive, e.g., `ListWhiteblackipRule` (singular), `ShowWhiteBlackIpRule` (note capitalization)
- Nested parameters must be expanded with dots: `--action.category=block`; cannot be written as `--action=block`
- `CreatePolicy` does not accept `--level` and `--action.category` parameters; defaults after creation are level=2, action=log; use `UpdatePolicy` if modifications are needed
- When executing `UpdatePolicy`, the `--options.*` parameters must be dynamically set based on the `module_status` array in the JSON file. For each module in `module_status`, if `enabled=true`, set `--options.<module>=true`; if `enabled=false`, set `--options.<module>=false`. **Exception**: The `ip_reputation` module must NOT be included in `--options.*` parameters because it does not exist in the UpdatePolicy API's options parameter list (verified via `hcloud WAF UpdatePolicy --help`). Only modules that have corresponding `--options.<module>` parameters in UpdatePolicy should be processed
- For precise protection rules, if `logic_operation` ends with `_any` or `_all` (e.g., `contain_any`, `equal_any`), `--conditions.N.value_list_id` must be used; `--conditions.N.contents.M` cannot be used, otherwise error `WAF.00021017` will occur
- For blacklist/whitelist rules, `--addr` only accepts a single IP/CIDR (e.g., `42.123.120.66` or `42.123.120.0/16`); multiple IPs must use an IP address group (`--ip_group_id`), otherwise error `WAF.00021009` will occur
- `value_list_id` and `ip_group.id` in JSON should use a three-level fallback lookup strategy: first use `ShowValueList --valuelistid=<ID>` or `ShowIpGroup --id=<ID>` for exact ID query — if found, reuse directly; if an error is returned, use `ListValueList --name=<name>` or `ListIpGroup --name=<name>` for fuzzy name query; if still not found, create a new resource. Note parameter names: `ShowValueList` uses `--valuelistid` (not `--value_list_id`), `ShowIpGroup` uses `--id` (not `--ip_group_id`)
- In `--cli-jsonInput` JSON files, the `path` location **must contain both** `project_id` and `policy_id`, otherwise the error "Missing required parameter: project_id" will occur. `project_id` can be obtained from the response of `CreatePolicy` or `ShowPolicy`
- The `--geoip` parameter for geo-access control rules uses `|` (pipe) to separate multiple region codes (e.g., `"BJ|Afghanistan"`), not commas. The `geoTagList` array in JSON must be converted to a `|`-delimited string
- The `--hostname` parameter for web anti-tampering rules (`CreateAntiTamperRule`) does **not** require the domain to be pre-bound to the policy or exist in the WAF protected domain list; rules can be created directly using the hostname value from JSON
- If a name already exists when creating a new policy (`WAF.00011016: Duplicate name`), since the user was asked for the name in Step 1, this error is an exceptional case — ask the user for a new name (e.g., add `_2`, `_copy` suffix) and retry
- Threat intelligence access control rules use the `CreateIpReputationRule` command; the `--tags.N` parameter format is `--tags.1=value1 --tags.2=value2`; `--type` currently only supports `idc`
- CC rule `mode` must be determined based on condition categories: `mode=0` (Standard) only supports `url` conditions; `mode=1` (Advanced) supports all categories including `ip`, `cookie`, `header`, `params`. The source JSON does not contain `mode` field, so you must infer it: if any condition category is not `url`, use `mode=1`. Using wrong mode causes `WAF.00021017: Illegal path` error (misleading message — actually means incorrect rule configuration)
- The `--cli-jsonInput` JSON file `path` must use **object format** `{"project_id": "...", "policy_id": "..."}`, NOT string format like `"path": "v1/..."`. String format causes CLI parse error
- CC rules: the source JSON does **NOT** contain a `mode` field. The `mode` must be inferred from condition categories: `mode=0` (Standard) only supports `url` conditions; `mode=1` (Advanced) supports all categories (`ip`, `cookie`, `header`, `params`, etc.). **When in doubt, use `mode=1`**. Using `mode=0` with non-url conditions causes `WAF.00021017: Illegal path` (misleading error — actually means incorrect rule configuration)
- Global whitelist (ignore) rules: The `CreateIgnoreRule` API does **NOT** have a `name` field (verified via SDK and `--help`). Do **NOT** include `name` in the temp JSON body. The required fields are `conditions`, `domain`, `mode`, `rule`.
- `--cli-jsonInput` JSON files must use **object format** for `path`: `{"path": {"project_id": "...", "policy_id": "..."}}`. String format (e.g., `"path": "v1/..."`) is **NOT supported** and causes `解析cli-jsonInput参数文件失败`
- Attack punishment rules use the `CreatePunishmentRule` command; each punishment category (e.g., `long_ip_block`, `short_ip_block`) can only have one rule per policy. The `--block_time` parameter value range depends on the `--time_unit` and category: for `long_xxx` categories, SECOND [301, 7776000], MINUTE [6, 129600], HOUR [1, 2160], DAY [1, 90], MONTH [1, 3]; for `short_xxx` categories, SECOND [1, 300]. Default `--time_unit` is `SECOND`. In overwrite mode, attack punishment rules must be deleted using the independent `DeletePunishmentRule` API (not `BatchDeleteRules`), similar to anti-crawler rules
