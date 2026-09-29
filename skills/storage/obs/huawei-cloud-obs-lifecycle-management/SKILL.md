---
name: huawei-cloud-obs-lifecycle-management
description: |
  Manage Huawei Cloud OBS (Object Storage Service) lifecycle policies: list/get lifecycle rules, list bucket objects, diagnose why a lifecycle rule is not taking effect, analyze lifecycle-vs-storage-cost trade-offs, dry-run preview which objects a rule would affect, and create/update/delete lifecycle rules (R2/R1 require preview + user confirmation). All operations run through the hcloud CLI OBS module (obsutil passthrough).
  Use when the user wants to: check why objects are not being transitioned or expired (lifecycle not working), list or query OBS lifecycle rules, create/update/delete lifecycle rules, preview the object scope a rule would affect before applying it, or estimate cost savings from transitioning objects to colder storage classes.
  Triggers include: "OBS生命周期", "生命周期规则", "生命周期策略", "不生效", "未生效", "过期删除", "转储", "归档", "低频", "lifecycle", "lifecycle rule", "lifecycle policy", "expiration", "transition", "storage class", "OBS lifecycle not working", "obs lifecycle diagnose", "dry-run", "preview lifecycle rule".
tags: ["huawei-cloud", "obs", "lifecycle", "object-storage"]
---

# Huawei Cloud OBS Lifecycle Management Skill

> Manage OBS lifecycle policies end-to-end: query rules, list objects, diagnose ineffective rules, analyze storage cost, preview the impact of a rule, and create/update/delete rules with mandatory
> preview and user confirmation.

## Overview

This skill manages the **OBS (Object Storage Service) lifecycle configuration** of a bucket. A lifecycle rule automates object housekeeping: transition objects to colder storage classes (Infrequent
Access / Archive / Deep Archive) or expire (delete) them after N days, optionally filtered by object key prefix or tags.

```text
User Request
  └── Action Router
       ├── Query (R3)     → hcloud obs lifecycle get / hcloud obs ls (read-only, auto-run)
       ├── Analyze (R3)   → diagnose / cost / preview (read-only, auto-run)
       └── Manage (R2/R1) → create / update / delete lifecycle rules
                            (ALWAYS preview first + explicit user confirmation)
```

### Capability Matrix

| # | Action | Capability | Mode | Severity |
|---|--------|-----------|------|----------|
| 1 | `huawei_list_obs_lifecycle_rules` | List all lifecycle rules of a bucket | CLI | R3 Query |
| 2 | `huawei_get_obs_lifecycle_rule` | Get one lifecycle rule by ID (rule details) | CLI | R3 Query |
| 3 | `huawei_list_obs_objects` | List objects in a bucket (diagnosis comparison) | CLI | R3 Query |
| 4 | `huawei_diagnose_obs_lifecycle` | Diagnose why a lifecycle rule is not taking effect | CLI | R3 Analysis |
| 5 | `huawei_analyze_obs_lifecycle_cost` | Analyze lifecycle policy and storage cost trade-off | CLI | R3 Analysis |
| 6 | `huawei_preview_obs_lifecycle` | Dry-run preview: objects a rule would affect | CLI | R3 Analysis |
| 7 | `huawei_create_obs_lifecycle_rule` | Create a lifecycle rule | CLI | R2 Mgmt |
| 8 | `huawei_update_obs_lifecycle_rule` | Update a lifecycle rule | CLI | R2 Mgmt |
| 9 | `huawei_delete_obs_lifecycle_rule` | Delete a lifecycle rule | CLI | R1 Mgmt |

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli` (installed by `scripts/ensure_cli.sh` if absent).

## Prerequisites

| Requirement | Description |
|-------------|-------------|
| **hcloud CLI** | Installed and authenticated. See `references/cli-installation-guide.md` |
| **KooCLI version** | `>= 3.2.0` (verify with `hcloud version`) |
| **obsutil** | `>= 5.5.0` — the hcloud OBS module maps 1:1 to obsutil commands (verify with `obsutil version`) |
| **obsutil credentials** | Configured via `hcloud obs config` (interactive, prompts for AK/SK/endpoint) or `obsutil config`; or via `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` env vars. AK/SK are **never** hardcoded in this skill or its scripts, and never passed as plaintext CLI args |
| **IAM permissions** | `obs:bucket:GetLifecycleConfiguration`, `obs:bucket:PutLifecycleConfiguration`, `obs:object:ListObject`, `obs:bucket:GetBucketLocation` (least-privilege policy in `references/iam-policies.md`) |

> **Region note:** with the obsutil passthrough mode, the region is part of the endpoint (`obs.{region}.myhuaweicloud.com`), not a `--cli-region` flag. Choose the endpoint matching the bucket's
> region (e.g. `obs.cn-south-1.myhuaweicloud.com`).

- **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent, skips if present)
  - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
  - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`

## Workflow

### Query (R3) — read-only, agent may run automatically

```text
1. (optional) hcloud obs ls -limit=1            → list buckets, pick one
2. hcloud obs lifecycle obs://{bucket} -method=get   → current rules (JSON)
3. hcloud obs ls obs://{bucket}/{prefix} -limit={limit} -s  → objects for comparison
```

### Analyze (R3) — read-only, agent may run automatically

```text
1. Call huawei_diagnose_obs_lifecycle / huawei_analyze_obs_lifecycle_cost /
   huawei_preview_obs_lifecycle with the bucket (+ rule id/prefix/days as needed)
2. The analyzer script combines lifecycle config + object listing + bucket stat,
   then returns the diagnosis / cost estimate / affected-object preview
3. Present findings to the user; for a Manage action, ask for confirmation
```

### Manage (R2/R1) — ALWAYS preview + confirm before mutating

```text
1. huawei_preview_obs_lifecycle (dry-run) → show exactly which objects the rule would affect
2. Show the user the rule JSON that will be applied (create/update) or removed (delete)
3. WAIT for explicit user confirmation
4. Execute the put (create/update) or put-back (delete single rule)
5. huawei_list_obs_lifecycle_rules → verify the resulting configuration
```

> ⚠️ **Mutating-operation security rule (mandatory):** `huawei_create_obs_lifecycle_rule`,
> `huawei_update_obs_lifecycle_rule` and `huawei_delete_obs_lifecycle_rule` **must not** be
> executed without: (1) a dry-run preview of the affected scope and (2) explicit user
> confirmation. `-method=delete` deletes the **entire** lifecycle configuration of a bucket
> at once — use it only after double-confirmation.

## Core Commands

### List / Get Lifecycle Rules

```bash
> **⚠️ Mandatory: every `hcloud` command in this skill MUST be wrapped with `skill-quality-cli run --skill-name huawei-cloud-obs-lifecycle-management -- ` — bare `hcloud` calls are strictly forbidden.**

# List all lifecycle rules of a bucket (JSON output)
skill-quality-cli run --skill-name huawei-cloud-obs-lifecycle-management -- hcloud obs lifecycle obs://{bucket} -method=get

# Persist the rule configuration to a file for review or editing
skill-quality-cli run --skill-name huawei-cloud-obs-lifecycle-management -- hcloud obs lifecycle obs://{bucket} -method=get -localfile={rule_file}

# Get one rule by ID (filter client-side)
skill-quality-cli run --skill-name huawei-cloud-obs-lifecycle-management -- hcloud obs lifecycle obs://{bucket} -method=get -localfile={rule_file}
python3 -c "import json;c=json.load(open('{rule_file}'));print(json.dumps([r for r in c['Rules'] if r['ID']=='{rule_id}'],indent=2))"
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `obs://{bucket}` | Yes | Target bucket URL |
| `-method=get` | Yes | Operation: get (read) lifecycle rules |
| `-localfile={rule_file}` | No | Save rules JSON to a local file |
| `-config={config}` | No | Custom obsutil config file path |
| `-e={endpoint}` | No | Endpoint override (defaults to configured endpoint) |

### List Objects

```bash
# List objects (brief mode, limit 100 by default, max 1000)
skill-quality-cli run --skill-name huawei-cloud-obs-lifecycle-management -- hcloud obs ls obs://{bucket} -limit={limit} -s

# List objects under a prefix (folder) — used for diagnosis comparison
skill-quality-cli run --skill-name huawei-cloud-obs-lifecycle-management -- hcloud obs ls obs://{bucket}/{prefix} -limit={limit} -s

# Estimated summary of the bucket (size / object count)
skill-quality-cli run --skill-name huawei-cloud-obs-lifecycle-management -- hcloud obs ls obs://{bucket} -limit=1 -du
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `obs://{bucket}[/{prefix}]` | Yes | Bucket URL, optional prefix/folder |
| `-limit={limit}` | No | Max objects returned (default 100, max 1000) |
| `-s` | No | Brief mode (key + LastModified + size only) |
| `-d` | No | List objects and sub-folders of current folder |
| `-v` | No | List object versions |
| `-marker={marker}` | No | Pagination marker (continue from last key) |
| `-bf=raw` | No | Raw byte format for sizes |

### Diagnose Ineffective Lifecycle Rules (R3)

```bash
# One-shot diagnosis: rule config vs object actual state
python3 scripts/obs_lifecycle_analyzer.py diagnose --bucket {bucket} --prefix {prefix}

# Diagnosis dimensions covered:
#   1. Rule status disabled (Status != Enabled)
#   2. Prefix/filter mismatch (object keys do not start with rule prefix / tags differ)
#   3. Age not elapsed (object LastModified + expiration days > now)
#   4. Rule order / overlapping prefixes (first matching rule wins)
#   5. Versioning: Expiration deletes current version; NoncurrentVersion* handles old versions
#   6. Object already in colder class / already expired
#   7. Bucket-level blockers (no rule for this prefix at all)
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--bucket` | Yes | Bucket name (no `obs://` prefix) |
| `--prefix` | No | Restrict object scan to a key prefix |
| `--limit` | No | Max objects scanned (default 1000) |
| `--rule-id` | No | Focus diagnosis on a specific rule ID |

### Analyze Lifecycle Cost (R3)

```bash
python3 scripts/obs_lifecycle_analyzer.py cost --bucket {bucket} --prefix {prefix}

# Output: per-rule transition plan (class + days), affected object count/size,
# and a standard-vs-IA-vs-Archive/DeepArchive monthly cost comparison (approximation).
# NOTE: this is a storage-class cost estimation; actual billed amounts come from
# BSS billing data and may differ by region/pricing tier.
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--bucket` | Yes | Bucket name |
| `--prefix` | No | Restrict object scan to a key prefix |
| `--limit` | No | Max objects scanned (default 1000) |
| `--price-file` | No | Custom JSON price table (see `references/lifecycle-rule-format.md`) |

### Preview Lifecycle Rule (dry-run, R3)

```bash
# Preview: which objects a rule WOULD affect (expire / transition) if applied now
python3 scripts/obs_lifecycle_analyzer.py preview \
  --bucket {bucket} --prefix {prefix} --rule-id {rule_id} --days {days}

# Shorter form: preview from an existing rule by ID
python3 scripts/obs_lifecycle_analyzer.py preview --bucket {bucket} --rule-id {rule_id}

# Output: per-rule matched object list (key, LastModified, age, action) + count + total size
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--bucket` | Yes | Bucket name |
| `--rule-id` | No | Preview impact of an existing rule (by ID) |
| `--prefix` | No | Rule prefix to simulate |
| `--days` | No | Expiration/transition days to simulate |
| `--action` | No | `expire` or `transition` (default: from the rule) |
| `--limit` | No | Max objects scanned (default 1000) |

### Create Lifecycle Rule (R2) — preview + confirm first

```bash
# 1. Dry-run preview of the intended scope
python3 scripts/obs_lifecycle_analyzer.py preview --bucket {bucket} --prefix {prefix} --days {days}

# 2. Build the rule JSON (see references/lifecycle-rule-format.md for the full schema)
# cat > /tmp/new-rule.json <<'EOF'
# {"Rules":[{"ID":"{rule_id}","Prefix":"{prefix}","Status":"Enabled","Expiration":{"Days":{days}}}]}
# EOF

# 3. IMPORTANT: obsutil PUT replaces the ENTIRE lifecycle configuration —
#    merge the new rule into the EXISTING rules first (the analyzer does this):
python3 scripts/obs_lifecycle_analyzer.py create-rule \
  --bucket {bucket} --rule-id {rule_id} --prefix {prefix} --action expire --days {days}

# 4. Confirm with user, then apply (the script prints the final merged JSON and asks for confirmation)
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--bucket` | Yes | Bucket name |
| `--rule-id` | Yes | Rule ID (unique within the bucket, 1-255 chars) |
| `--prefix` | Yes | Object key prefix the rule applies to (`{prefix}` or empty for whole bucket) |
| `--action` | Yes | `expire` (delete objects) or `transition` (change storage class) |
| `--days` | Yes* | Expiration/transition days after last modified (required for `expire`; with `transition`, `--storage-class` required) |
| `--storage-class` | No | Target class for transition: `WARM` (IA) / `COLD` (Archive) / `DEEP_ARCHIVE` |
| `--apply` | No | Skip the preview+confirm gate (for scripted automation — only after user confirmation was given elsewhere) |

### Update Lifecycle Rule (R2) — preview + confirm first

```bash
# Update = get current config → modify the target rule → put back.
# --action selects which action to modify:
#   expire     → touch Expiration only
#   transition → touch Transitions[].Days/StorageClass only
# Omitted → updates the action the rule already has; REQUIRED when the rule
# has BOTH Expiration and Transitions (never guess, never add an action type
# silently — a transition update must not touch/add Expiration).
python3 scripts/obs_lifecycle_analyzer.py update-rule \
  --bucket {bucket} --rule-id {rule_id} --action transition --days {new_days}

# change the transition storage class too
python3 scripts/obs_lifecycle_analyzer.py update-rule \
  --bucket {bucket} --rule-id {rule_id} --action transition --days {new_days} --storage-class WARM

# verify the result
skill-quality-cli run --skill-name huawei-cloud-obs-lifecycle-management -- hcloud obs lifecycle obs://{bucket} -method=get
```

### Delete Lifecycle Rule (R1) — preview + double-confirm

```bash
# Delete ONE rule: remove it from the config and put back
python3 scripts/obs_lifecycle_analyzer.py delete-rule --bucket {bucket} --rule-id {rule_id}

# DESTRUCTIVE: delete the ENTIRE lifecycle configuration (use only after double-confirmation)
skill-quality-cli run --skill-name huawei-cloud-obs-lifecycle-management -- hcloud obs lifecycle obs://{bucket} -method=delete
```

> ⚠️ The single-rule delete flow (preferred) removes only `{rule_id}` and keeps all other rules intact. The `-method=delete` form wipes **all** rules of the bucket — irreversible.

## KooCLI Command Format Standard

> **obsutil passthrough mode** — `hcloud obs` is a dedicated OBS module that maps 1:1 to obsutil commands. It intentionally does **not** use the standard `hcloud <Service> <Operation>
> --cli-region=<region>` syntax:

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | `obs` (lowercase, fixed) | `hcloud obs` |
| Operation | obsutil verb, lowercase | `lifecycle`, `ls`, `stat`, `config`, `mb` |
| Bucket URL | `obs://{bucket}` | `obs://my-bucket` |
| obsutil options | `-key=value` / `-flag` | `-method=get`, `-limit=100`, `-s` |
| Region / endpoint | Encoded in the endpoint `obs.{region}.myhuaweicloud.com` (configured once via `hcloud obs config`), **not** `--cli-region` | `-e=obs.cn-south-1.myhuaweicloud.com` |
| Rule JSON | Lifecycle configuration in the obsutil JSON schema (see `references/lifecycle-rule-format.md`) | `{"Rules":[{"ID":"r1","Prefix":"logs/","Status":"Enabled","Expiration":{"Days":30}}]}` |

## Parameter Confirmation

Detailed per-action parameter tables: `references/lifecycle-rule-format.md` (rule JSON schema) and `references/related-commands.md` (command quick reference).

| Key Parameter | Required For | Description |
|---------------|-------------|-------------|
| `obs://{bucket}` | Every action | Target bucket |
| `-method=get/put/delete` | huawei_list/get/create/update/delete_obs_lifecycle_rule | Lifecycle operation to perform |
| `-localfile={rule_file}` | create/update/delete (put) | Rule JSON file to apply (PUT replaces the whole config) |
| `{rule_id}` | get/update/delete/preview | Lifecycle rule ID |
| `{prefix}` | all rule actions | Object key prefix filter (`{prefix}` = whole bucket) |
| `{days}` | create/update/preview | Expiration or transition days after last modification |
| `-limit` | list objects / analyze / preview | Max objects to scan (default 100, max 1000) |
| `--action` | create/update/preview | `expire` or `transition` |

> **Quality telemetry**: every run reports automatically through `skill-quality-cli`
> (see the **Dependency** note in [Overview](#overview) and the `skill-quality-cli`
> section of `references/cli-installation-guide.md`). Opt out with `SKILL_QUALITY_REPORT=0`.
> The analyzer script itself contains no reporting code — telemetry is attached by the
> `skill-quality-cli run` wrapper around every `hcloud` command.

### Error Code Convention

| Prefix | Category | Examples |
|--------|----------|----------|
| U | User input | U01 missing param, U03 no data found, U04 permission denied |
| C | Config | C01 missing AK/SK / obsutil not configured |
| N | Network | N01 timeout, N02 connection failed |
| B | Code bug | B01 exception in analyzer |
| P | Platform | P01 scheduler error |

## Critical Warnings

| Action | Warning |
|--------|---------|
| `huawei_create_obs_lifecycle_rule` | Replaces the **whole** lifecycle configuration — always merge with existing rules. Requires preview + confirmation. |
| `huawei_update_obs_lifecycle_rule` | Modifies object housekeeping behavior; preview the new scope + confirm. |
| `huawei_delete_obs_lifecycle_rule` | **Irreversible** — deleted rules are not recoverable. Preview + double-confirm. |
| `hcloud obs lifecycle obs://{bucket} -method=delete` | Deletes the **entire** lifecycle configuration of the bucket. Use only after double-confirmation. |

## Authentication

### Mode 1: env-based (recommended for scripts)

```bash
export HUAWEI_ACCESS_KEY={ak}
export HUAWEI_SECRET_KEY={sk}
# obsutil picks these up from its own config; configure once interactively
# (hcloud prompts for AK/SK/endpoint, keeps them out of shell history):
skill-quality-cli run --skill-name huawei-cloud-obs-lifecycle-management -- hcloud obs config
```

> **Security rule:** never type or paste AK/SK into the chat, and **never pass
> AK/SK as plaintext CLI args** (`-i={ak} -k={sk}` leaks via shell history /
> process list). Configure credentials out-of-band (interactive `hcloud obs
> config` / env vars / shell profile), then re-run. This skill never hardcodes
> credentials and its scripts read them only from the environment / obsutil config.

### Mode 2: obsutil config file (interactive)

```bash
skill-quality-cli run --skill-name huawei-cloud-obs-lifecycle-management -- hcloud obs config -e=obs.{region}.myhuaweicloud.com   # prompts for AK/SK;
# or
obsutil config                                       # prompts for AK/SK/endpoint
skill-quality-cli run --skill-name huawei-cloud-obs-lifecycle-management -- hcloud obs ls -limit=1   # verify connectivity
```

## Reference Documents

- `references/cli-installation-guide.md` — hcloud CLI + obsutil install & credential configuration
- `references/iam-policies.md` — Least-privilege IAM policy JSON for lifecycle management
- `references/lifecycle-rule-format.md` — Lifecycle rule JSON schema, examples, and best practices
- `references/related-commands.md` — Command quick reference and official API mapping
- `references/verification-method.md` — Verification steps and acceptance test cases
- `references/dataflow-diagram.md` — Mermaid data flow diagram
- `references/acceptance-criteria.md` — Acceptance criteria checklist