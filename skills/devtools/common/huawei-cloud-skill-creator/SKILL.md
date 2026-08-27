---
name: huawei-cloud-skill-creator
version: 2.1.3
description: |
  1. Six-phase pipeline for creating Huawei Cloud skills — Socratic requirements gathering, CLI→SDK→API research, MD generation, test preparation, detailed testing, and final cleanup & compliance check
  2. Phase-chained dependency: each phase builds on the previous phase's output, no phase may be skipped
  3. Supports CLI, SDK, and REST API execution modes with automatic fallback detection
  4. Generates complete skill directory structure with SKILL.md, references/, scripts/, templates/
  5. Validates against the Huawei Cloud Skill Specification (华为云Skill检查规范)
  Triggers include: "创建华为云Skill","新建华为云Skill","华为云skill创建器","创建 Skill","新建 Skill","skill 创建器","create skill","build skill","new skill","skill creator","scaffold a Huawei Cloud skill","wrap CLI or OpenAPI into a skill","package cloud operations into a skill","帮我创建华为云Skill","帮我新建一个Skill","封装华为云CLI为Skill","华为云Skill脚手架","帮我创建一个skill","我需要一个skill","建一个skill","生成skill","帮我建一个华为云skill".
tags: [huawei-cloud, skill-creator, cli, sdk, devops]
---

# Huawei Cloud Skill Creator v2

> **Six-Phase Strict Pipeline** — Each phase depends on the previous phase's output and cannot be skipped. If any phase is missing, restart from the missing phase.

## Overview

The Huawei Cloud Skill Creator v2 is based on a six-phase strict pipeline: starting with Socratic Q&A requirements analysis, followed by technical research (CLI→SDK→API three-level fallback), document generation, test preparation, detailed testing, resource cleanup and compliance check, ultimately generating a complete skill package that conforms to the Huawei Cloud Skill Specification. It only creates/packages skills — it does not directly operate cloud resources (no creating/deleting/modifying ECS, VPC, OBS, etc.); use it to generate a management Skill or use another dedicated management Skill for cloud-resource operations.

## Pre-check: Huawei Cloud Credentials Required

> **Mandatory gate.** This pre-check MUST pass before invoking any hcloud / huaweicloudsdk command — including Phase 2 research, Phase 4/5 testing, and Phase 6 validation. If no valid credential profile is detected, STOP and obtain credentials **out-of-band**.

### Security Rules

- **NEVER** read, echo, or print AK/SK values (e.g., printing the value of an `HUAWEI_ACCESS_KEY`-style env var is **FORBIDDEN**).
- **NEVER** read or cat the on-disk credential files for hcloud, obsutil, the SDK, or any other secret-storing location. Treat all such files as confidential; the *names* of those files (used by their owners) are documented in `references/cli-installation-guide.md`.
- **NEVER** ask the user to input AK/SK directly in the conversation or command line.
- **NEVER** invoke `hcloud configure set` with literal credential strings passed via the CLI's `cli-<ak-flag>` / `cli-<sk-flag>` parameters or any equivalent in-band secret-entry form.
- **ONLY** use `hcloud configure list` to check credential status — non-interactive, read-only, no secrets echoed.

### Verification Steps

```bash
hcloud configure list
```

Check the output for a valid profile (AK/SK, or temporary security credentials / agency-assumed role).

If no valid profile exists, **STOP** here.

1. Obtain credentials from **Huawei Cloud Console** → 身份与访问管理 (IAM) → 我的凭证 → 新增访问密钥.
2. **Output** the following copy-paste ready env-var setup block to the user (fill in real values **outside** of this session, never in chat). The Agent must **NEVER** ask the user to type the AK/SK value in the conversation — only emit the template below:

   ```bash
   # Set Huawei Cloud credentials. The secret key is entered silently when prompted.
   export HUAWEI_ACCESS_KEY="<your-access-key-id>"
   read -rs HUAWEI_SECRET_KEY; export HUAWEI_SECRET_KEY
   export HUAWEI_REGION="cn-north-4"
   ```

   Optional alternative — only as an interactive out-of-band step (Agent must NOT invoke this with literal values):

   ```bash
   hcloud configure    # interactive; prompts for AK/SK in the user's terminal
   ```
3. After the user confirms they have configured env vars (or run `hcloud configure`), re-run `hcloud configure list`. If the profile is valid → resume Phase 1. If still missing → terminate, do not proceed.

> **Reuse the active CLI profile for all subsequent `hcloud` and `huaweicloudsdk` calls.** Do not print or hardcode secrets. Do not replace this gate with `obsutil config`, `hcloud configure set` with literal arguments, SDK credentials constructors filled with literal strings (for example, the SDK's `BasicCredentials` built from string literals rather than env vars), or any other in-session secret-entry flow.

### Credential Source Priority

When invoking commands later (Phase 2/4/5), the skill accepts credentials in this priority order:

| Priority | Source | Notes |
|----------|--------|-------|
| 1 | Environment variables | Auto-scan all variables prefixed with `HUAWEI` / `HW` / `HWC` containing `ACCESS_KEY` / `_AK` / `SECRET_KEY` / `_SK` |
| 2 | `hcloud configure` profile | Active CLI profile — preferred for hcloud calls |
| 3 | IAM agency / temporary credentials | AK/SK + SecurityToken (programmatic access) |

If **none** of the above are available when Phase 4/5 testing starts, prompt the user once to configure them out-of-band and re-run the pre-check. If still unavailable, **terminate the process** — strictly prohibited from skipping credential-required steps.

## Prerequisites

1. **hcloud CLI** installed and authenticated — Reference: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
   - Authentication verified via the **Pre-check** above (`hcloud configure list`).
2. **Python 3.8+** with `huaweicloudsdk` packages — install on demand: `pip install huaweicloudsdkcore huaweicloudsdkecs`. Verify with `python3 -c "import huaweicloudsdkcore"` before Phase 2/4/5. SDK Reference: https://console.huaweicloud.com/apiexplorer/#/sdkcenter
3. **Node.js + npx** available
4. **Huawei Cloud AK/SK** — Auto-scan all environment variables prefixed `HUAWEI` / `HW` / `HWC` matching `ACCESS_KEY` / `_AK` / `SECRET_KEY` / `_SK`. Hardcoding AK/SK in scripts, docs, or command lines is **forbidden**.
5. **API Reference**: https://console.huaweicloud.com/apiexplorer/#/openapi

## Workflow — Six-Phase Strict Pipeline

```
Phase 1 (Q&A) → Phase 2 (Tech Research) → Phase 3 (Generate MD)
    → Phase 4 (Test Prep) → Phase 5 (Detailed Testing) → Phase 6 (Cleanup & Report)
```

**Strict Rules:**
- Each phase **must** output a phase summary (phase-N-summary)
- Before starting each phase, **must** verify that the previous phase's summary file exists
- After all 6 phases are completed, perform a **final check** for any missing phases. If any are missing, restart from the missing phase
- Skipping any phase is strictly prohibited
- The **Pre-check: Huawei Cloud Credentials Required** gate must have passed before any Phase 2 research or Phase 4/5 execution begins

### Phase 1: Requirements Analysis (Socratic Q&A)

**Goal:** Clarify user requirements through question-by-question dialogue.

- Ask **one question** at a time, wait for the user's response
- Cover the following dimensions:
  1. **Target Service** — Which Huawei Cloud service? (ECS, VPC, OBS, RDS, BSS, etc.)
  2. **Feature Scope** — What should the Skill do? (Query, Diagnose, Deploy, Monitor, Manage)
  3. **Execution Mode** — Prefer CLI / SDK / API?
  4. **CLI Operations** — Which operations are involved? (List, Show, Create, Delete, Update)
  5. **Trigger Scenarios** — When would an Agent invoke this? (Daily inspection, troubleshooting, auto-scaling)
- After every 5 questions or covering all dimensions → Display requirements summary table → Wait for user confirmation
- **🛑 Do NOT proceed to Phase 2 until the user has explicitly confirmed**

**Output:** `phase-1-summary.json` — User-confirmed requirements description

### Phase 2: Technical Research (CLI→SDK→API Three-Level Fallback)

**Dependency:** Phase 1 requirements analysis completed (phase-1-summary.json exists)

For each feature point confirmed in Phase 1, research availability in the following order:

| Priority | Research Method | Verification Command | Success Criteria |
|----------|----------------|---------------------|-----------------|
| 1st | **CLI** — hcloud command | `hcloud <Service> <Operation> --cli-region=cn-north-4 --help` | Command exists and parameters are valid |
| 2nd | **SDK** — huaweicloudsdk | `python3 -c "from huaweicloudsdk{service}.v2 import ..."` | SDK package installed and class importable |
| 3rd | **API** — **Only from the following two sources** | See rules below | Endpoint from a trusted source, not inferred |

**Core Rule: API Endpoint Forensics (No Guessing)**

API endpoints are **only allowed** from the following two sources. **Strictly prohibited from inferring through naming patterns**:

| Trusted Source | Method |
|----------------|--------|
| ① **SDK source `_http_info` `resource_path`** | `grep -A8 "_http_info" {service}_client.py` → Read `resource_path` value |
| ② **Huawei Cloud API Explorer** (api-explorer.huaweicloud.com) | User searches and confirms on that website |

**❌ Strictly prohibited actions:**
- Inferring new endpoints based on other API path patterns (e.g., inferring **claim-vouchers** endpoint from **coupons** endpoint)
- Constructing URIs yourself based on documentation descriptions
- Using "common naming patterns" to guess API paths
- If the SDK is available but the corresponding function has no method in `_http_info` → Mark ⛔, do not infer

**Execution Rules:**

```
Research feature point N
  ├── CLI available → Record as CLI mode, record specific command
  ├── CLI unavailable → Check SDK
  │    ├── SDK available → Record as SDK mode
  │    │    ├── Read all _http_info methods from SDK source to obtain real REST paths
  │    │    │    grep "resource_path" <sdk_path>/{service}_client.py
  │    │    └── Feature point's corresponding method has _http_info in SDK → Record real API endpoint
  │    │         Feature point's corresponding method has no _http_info in SDK → Mark ⛔, do not infer
  │    ├── SDK unavailable → Ask user to confirm endpoint from API Explorer
  │    │    ├── User finds endpoint from API Explorer → Record as API mode, note the source
  │    │    ├── User provides endpoint (other source) → Record as API mode, mark ⚠ user-provided
  │    │    └── User cannot provide → Mark ⛔
  │    └── SDK partially available (some methods missing and no corresponding _http_info) → Mark missing features as ⛔
  └── Generate feature point research result (including execution mode + real API path if available)
```

**🛑 Agent is strictly forbidden from guessing/fabricating API paths on its own. If neither the SDK source nor API Explorer has the endpoint, mark it ⛔ — it doesn't exist.**

**Tips for finding SDK client source paths:**
```bash
# Method 1: Find package installation path
python3 -c "import huaweicloudsdk{service}.v2 as m; import os; print(os.path.dirname(m.__file__))"

# Method 2: Find all _http_info methods (show all API endpoints)
grep "_http_info" <path>/{service}_client.py

# Method 3: View API path for a specific method
grep -A8 "_{method}_http_info" <path>/{service}_client.py
# The "resource_path" key in output is the real REST endpoint
```

**Output:** `phase-2-summary.json` — Execution mode (CLI/SDK/API/⛔) and corresponding command/code/API path for each feature point

### Phase 3: Document Generation

**Dependency:** Phase 2 technical research completed (phase-2-summary.json exists)

Generate Skill files based on Phase 2 conclusions:

1. **Name the Skill** — Use `huawei-cloud-{product}-{function}` and make the frontmatter `name` match the directory name.
2. **Language** — Generate SKILL.md in **English** by default. Chinese documentation may be added in `references/` as supplementary. The main SKILL.md must use English for frontmatter description, section titles, command examples, and all explanatory content.
3. **Frontmatter** — Include `name`, `description` with a feature summary and trigger conditions, and no more than five `tags`. Do not generate a `version` field.
4. **Create directory structure:**
   ```text
   skills/{skill-name}/
   ├── SKILL.md
   ├── references/
   │   ├── iam-policies.md              (Required)
   │   ├── cli-installation-guide.md    (Required when CLI is used)
   │   ├── verification-method.md       (Recommended)
   │   ├── dataflow-diagram.md          (Recommended)
   │   └── acceptance-criteria.md       (Recommended)
   ├── scripts/
   │   └── test-cli-commands.sh
   └── templates/
       └── test-vars.json
   ```
5. **SKILL.md content generation rules:**

   | Execution Mode | Command Format in SKILL.md |
   |---------------|---------------------------|
   | **CLI** | `hcloud <Service> <Operation> --cli-region={region} [--params]` |
   | **SDK** | Python script example (`python3 -c "..."`) |
   | **API** | curl command + user-provided endpoint (mark as user-provided) |
   | **Unavailable** | Mark `requires manual verification`, do not generate specific commands |

6. **Required sections in SKILL.md:**

   | Section | Severity | Description |
   |---------|----------|-------------|
   | YAML Frontmatter | Critical | `name` + `description` with feature summary and trigger conditions + `tags`; no `version` |
   | Overview | High | Feature overview, architecture, applicable scenarios |
   | Prerequisites | High | CLI version, authentication configuration, IAM permissions |
   | Workflow | High | Skill workflow steps |
   | Core Commands | High | Command examples grouped by function |
   | Parameter Confirmation | High | User-configurable parameter table |
   | Reference Documents | Critical | Links to documents under `references/` |
   | KooCLI Command Format Standard | Low | Required when CLI is involved; service, operation, region, and parameter syntax |

7. **Generate Mermaid data flow diagram** → `references/dataflow-diagram.md`.
8. **Generate IAM policies** → `references/iam-policies.md` using least privilege.
9. **Record API references** — Keep verified API paths in `phase-2-summary.json`. If a generated Skill needs reusable API documentation, add a reference file under `references/` using an allowed kebab-case filename.
10. **Package limits** — Total file content size ≤ 40 MB, total files ≤ 30, and SKILL.md ≤ 500 lines. Split oversized SKILL.md content into `references/`.
11. **File extension allowlist** — Every file must have one of these 46 extensions:
    `.md`, `.mdx`, `.txt`, `.json`, `.json5`, `.yaml`, `.yml`, `.toml`, `.js`, `.cjs`, `.mjs`, `.ts`, `.tsx`, `.jsx`, `.py`, `.sh`, `.ps1`, `.psm1`, `.psd1`, `.r`, `.rb`, `.go`, `.rs`, `.swift`, `.kt`, `.java`, `.cs`, `.cpp`, `.c`, `.h`, `.hpp`, `.sql`, `.csv`, `.tsv`, `.ini`, `.cfg`, `.conf`, `.env`, `.properties`, `.dat`, `.xml`, `.html`, `.css`, `.scss`, `.sass`, `.svg`.
    Files without an extension or outside this allowlist must be removed or renamed.
12. **Change scope** — A pull request must change only one Skill directory. Use `bash scripts/validate-skill.sh -s {skill-path} -b <base-ref>` to validate the PR diff when a base ref is available.

**🛑 Strictly prohibited from generating hallucinated URIs / fabricated API paths. Feature points not verified in Phase 2 must not have specific commands written.**

**Output:** `phase-3-summary.json` — List of generated files and structure validation results

### Phase 4: Test Preparation

**Dependency:** Phase 3 document generation completed (phase-3-summary.json exists)

1. **Generate test cases** — Split test cases based on Phase 2/3 feature points

   | Case Type | Coverage Requirement | Example |
   |-----------|---------------------|---------|
   | CLI cases | One case per hcloud command | `hcloud ECS ListServers --cli-region=cn-north-4 --limit=1` |
   | SDK cases | One case per SDK call | `list_sub_customer_coupons(limit=1)` |
   | API cases | One case per user-provided endpoint | `curl -X GET {endpoint}` |

2. **Save test cases as JSON** → `templates/test-vars.json`

   ```json
   {
     "test_cases": [
       {"id": "TC-01", "name": "...", "command": "...", "expected": "..."},
       ...
     ]
   }
   ```

3. **Show all test cases to the user for confirmation**

4. **Run tests:**
    - Read AK/SK from environment variables: 自动扫描所有以 `HUAWEI` / `HW` / `HWC` 开头的环境变量，匹配其中含 `ACCESS_KEY` / `_AK` / `SECRET_KEY` / `_SK` 的键值对
    - **If no valid AK/SK env var or CLI profile is detected, output the env-var setup template below and STOP — never ask the user to type AK/SK in chat. The user fills in real values out-of-band and re-runs the Pre-check:**

      ```bash
      export HUAWEI_ACCESS_KEY="<your-access-key-id>"
      read -rs HUAWEI_SECRET_KEY; export HUAWEI_SECRET_KEY
      export HUAWEI_REGION="cn-north-4"
      ```

      If the user cannot / will not provide env vars, **terminate the process**. Strictly prohibited from skipping credential-required steps.
    - Execute test cases one by one
    - **Before executing mutating commands (Create/Update/Delete), must prompt the user and wait for confirmation**

5. **Test verification flow:**

   ```
   Each case → Try CLI execution
     ├── ✅ Success → Record PASS
     └── ❌ Failure → Check syntax issues
          ├── ✅ Syntax issue → Fix and retry
          └── ❌ Non-syntax issue → Fallback to SDK
               ├── ✅ Success → Record PASS (SDK)
               └── ❌ Failure → Fallback to API (user-provided endpoint)
                    ├── ✅ Success → Record PASS (API)
                    └── ❌ Failure → Record FAIL ⛔ requires manual verification
   ```

**Output:** `phase-4-summary.json` — Test case list + per-case execution results

### Phase 5: Detailed Testing

**Dependency:** Phase 4 test preparation completed (phase-4-summary.json exists)

1. **Full regression:** Execute all test cases generated in Phase 4

2. **Resource lifecycle testing** (applicable to Skills involving resource creation/modification/deletion):
   - Create resource → Verify creation succeeded (query to confirm)
   - Runtime query → Verify resource status is correct
   - Destroy resource → Verify resource release
   - Test report outputs information on created/modified/deleted resources
   - **Prompt the user and wait for confirmation before each step**

3. **Management-type Skills**:
   - If CRUD operations are involved → End-to-end full testing
   - If query-only → Output query results to test report

4. **Report generation:**
   - Test results aggregated by case
   - Detailed record of resource changes
   - Detailed error information for failed cases

**Output:** `phase-5-summary.json` — Detailed test results + resource operation records

### Phase 6: Resource Cleanup and Compliance Check

**Dependency:** Phase 5 detailed testing completed (phase-5-summary.json exists)

1. **Resource Cleanup:**
   - Check whether all resources created in Phase 5 have been released
   - Unreleased resources → Prompt user and attempt cleanup
   - Record cleanup results

2. **Huawei Cloud Skill Specification Compliance Check** (against 华为云Skill检查规范):

    | Check Item | Level | Verification Method |
    |-----------|-------|-------------------|
    | SKILL.md exists | Critical | File existence check |
    | Skill directory under skills/ | Low | Path format: skills/{category}/{subcategory}/{skill-name}/ |
    | Skill package naming convention | High | Directory name matches huawei-cloud-{product}-{function} |
    | One PR submits only one Skill | Critical | git diff checks that PR changes only affect a single Skill directory |
    | YAML Frontmatter exists | Critical | `grep '^---$'` |
    | name field exists | Critical | Frontmatter name field exists and matches directory name |
    | description field exists | Critical | Frontmatter description field exists and contains feature summary + trigger words |
    | description includes trigger words | Medium | Accept `Triggers include:`, `Use when`, or equivalent trigger conditions |
    | Should not contain version field | Low | No `version` field in frontmatter |
    | Overview section | High | Match `Overview` or `概述` |
    | Prerequisites section | High | Match `Prerequisites` or `前置条件` |
    | Workflow section | High | Match `Workflow` or `工作流` |
    | Core Commands section | High | Match `Core Commands` or `核心命令` |
    | Parameter Confirmation section | High | Match `Parameter Confirmation` or `参数确认` |
    | Reference Documents section | Critical | Match `Reference Documents`, `References`, or `参考文档` |
    | KooCLI Command Format Standard section | Low | Required when CLI is involved; match the English or Chinese heading |
    | references/cli-installation-guide.md | High | Required when CLI is involved, file existence |
    | references/iam-policies.md | Critical | File existence |
    | references/verification-method.md | Medium | Recommended file existence |
    | references/acceptance-criteria.md | Low | Recommended file existence |
    | Reference document kebab-case naming | Low | File names under references/ are all lowercase kebab-case |
    | Credential hardcoding | Critical | grep for credential hardcoding patterns and CLI credential config |
    | Cross-Skill direct calls | Critical | grep other Skill names |
    | CLI write operations require confirmation | Low | Check whether user confirmation is prompted |
    | Service name requirement | Medium | Every concrete hcloud service matches a KooCLI Service name and starts with uppercase/title case, such as `ECS`, `CloudPond`, or `IAMAccessAnalyzer` |
    | Operation name PascalCase | Medium | Every concrete operation name uses PascalCase |
    | Includes `--cli-region` | Medium | Every concrete CLI command includes the region parameter |
    | Total skill size ≤ 40 MB | Medium | Sum all file content sizes under the Skill directory |
    | Total file count ≤ 30 | Medium | Count SKILL.md and every file in all subdirectories |
    | SKILL.md line count ≤ 500 | Medium | Split excess content into `references/` |
    | File extensions in allowlist | Medium | Reject extensionless files and extensions outside the 46-type allowlist |

   3. **Security Audit:**

   Have the Agent orchestrate the five-tool audit described in `references/security-audit-guide.md`. Do not invoke another named Skill or call scripts from another Skill directory directly.

   The gate combines skillcheck, markdownlint-cli2, cisco-ai-skill-scanner, the Huawei Cloud specification check, and gitleaks. It must explicitly cover these Critical specification checks:

   | Check | Required coverage |
   |-------|-------------------|
   | Secret leak detection | AK/SK hardcoding, `hcloud configure set`, and report-output masking |
   | Vulnerability pattern detection | Known command injection, reverse shell, dangerous function, and prompt injection patterns |
   | Dependency security detection | Known unsafe dependency versions via `pip audit`, `safety check`, or an equivalent tool |
   | Insecure configuration detection | Insecure protocols, weak passwords, and unsafe defaults |

   ERROR or CRITICAL findings must be fixed and re-audited. WARNING-only results require explicit user acceptance. Record the report path, verdict, findings, and accepted warnings in `phase-6-summary.json`.

4. **Final report:**
   - Merge Phase 1-6 phase summaries
   - Include key conclusions from the security audit report (skill-gate-report)
   - Output complete creation report
   - Mark all incomplete items

5. **Final six-phase completeness check:**

   ```
   Check phase-1-summary.json exists → If missing, restart from Phase 1
   Check phase-2-summary.json exists → If missing, restart from Phase 2
   Check phase-3-summary.json exists → If missing, restart from Phase 3
   Check phase-4-summary.json exists → If missing, restart from Phase 4
   Check phase-5-summary.json exists → If missing, restart from Phase 5
   Check phase-6-summary.json exists → If missing, restart from Phase 6
   ```

   **All phases complete → Creation done. Missing phases → Restart from the missing phase.**

6. **Clean up phase summary files:** After completeness check passes, delete all `phase-*-summary.json` files under the skill directory

   ```bash
    # Execute after final completeness check passes
    # Safety check: ensure skill-path is a legitimate directory under the expected path
    [ -d "{skill-path}" ] && [ -f "{skill-path}/SKILL.md" ] && rm -f {skill-path}/phase-*.json
    echo "✅ phase-1~6-summary.json cleanup complete"
   ```

   **Note:** Only perform cleanup after the completeness check **fully passes**. If there are missing phases, do not clean up; restart from the missing phase.

**Output:** `phase-6-summary.json` — Final creation report + compliance check results + security audit conclusion

## KooCLI Command Format Standard

```bash
hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | Exact KooCLI Service name beginning with uppercase/title case | `ECS`, `VPC`, `CloudPond`, `IAMAccessAnalyzer` |
| Operation name | PascalCase | `ListServers`, `ShowServer` |
| Region parameter | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--server_id=xxx` |
| Indexed parameter | `--key.1=value1` | `--servers.1.id=xxx` |

## Core Commands

| Command | Purpose |
|---------|---------|
| `bash scripts/validate-skill.sh -s {path}` | Phase 3/6: Structure and Huawei Cloud specification validation |
| `bash scripts/test-cli-commands.sh -s {path} -e {cli\|sdk\|api}` | Phase 4/5: Functional testing |

> test-cli-commands.sh 仅执行白名单命令（hcloud/python3/curl/bash 开头），其他命令被拒绝且不会执行。validate-skill.sh 对不存在的 skill 目录会明确报错（exit 1）。

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `{skill-path}` | Yes | Target Skill directory path | e.g., huawei-cloud-ecs-manage |
| `{region}` | No | Huawei Cloud region | `cn-north-4` |
| `{executor}` | No | Execution mode (cli/sdk/api) | `cli` |

## Edge Cases

| Scenario | Handling |
|----------|----------|
| User skips questions and says "start" directly | Remind: requirements analysis must be completed first, start from Phase 1 questions |
| AK/SK environment variables not set | Re-run the **Pre-check** above. Output the env-var setup template (`export HUAWEI_ACCESS_KEY=...` / `export HUAWEI_SECRET_KEY=...`) and let the user fill it out-of-band. **NEVER** ask the user to paste AK/SK into chat. If user does not configure, terminate process, strictly prohibited from skipping |
| Target service not supported by hcloud CLI | Phase 2 fallback to SDK → Read SDK source _http_info → If still not found, mark ⛔ |
| SDK package does not exist | Check package name variants, if still not found, inform user, do not infer API |
| User is unsure of API endpoint | Mark ⛔ requires manual verification, do not fabricate endpoints. If SDK has the method, read _http_info for the real path |
| SDK has method but _http_info has no resource_path | Mark ⛔, this API does not exist in the SDK, do not infer |
| Attempting to infer API via path pattern (e.g., inferring claim-vouchers from coupons) | ❌ Strictly prohibited. It doesn't exist |
| Resource creation test fails | Analyze error cause (permissions/quota/parameters) → Fix and retry |
| Resource release fails | Retry 3 times, if still failing, inform user to clean up manually |
| templates/test-vars.json missing when running tests | test-cli-commands.sh reports FATAL and exits 1 (no tests executed). Re-run Phase 4 to generate templates/test-vars.json before testing |
| User refuses resource lifecycle testing | Inform user: resource lifecycle testing is a required step and cannot be skipped; if user still refuses, terminate process |
| Phase 6 finds missing phases | Restart from the missing phase until all 6 phases are complete |
| SDK has method but actual API path unknown | Read SDK source `grep _http_info {service}_client.py` to get real path |
| BSS service SDK initialization fails (GlobalCredentials) | BSS is global and must use `GlobalCredentials` with `with_endpoints`, not `BasicCredentials` with `with_region` |
| list_sub_customer_coupons query returns 400 | BSS limit parameter maximum is 100, not the default 200 |
| Phase 6 security audit FAIL | Fix issues from the audit report, then have the Agent rerun the audit until it passes |
| skill-scanner false positive | Use `<!-- skill-scanner:ignore -->` comment annotation, or exclude in .secrets.baseline |
| gitleaks false positive | Add to `.gitleaksignore` file |

## Verification Method

### Specification Compliance Verification
```bash
bash scripts/validate-skill.sh -s {skill-path}
# Check against 华为云Skill检查规范 item by item
```

### Functional Testing
```bash
bash scripts/test-cli-commands.sh -s {skill-path} -e cli   # CLI priority
bash scripts/test-cli-commands.sh -s {skill-path} -e sdk   # SDK fallback
bash scripts/test-cli-commands.sh -s {skill-path} -e api   # API fallback
```

### Six-Phase Completeness Check
```
Final verification: Check whether phase-1-summary.json ~ phase-6-summary.json exist
All exist ✅ → Creation complete
Missing any ❌ → Restart from the missing phase
```

### Security Audit (Phase 6)

Have the Agent orchestrate the tools listed in `references/security-audit-guide.md`, collect their findings into the Phase 6 report, fix every ERROR/CRITICAL issue, and repeat until the gate passes. Do not call another Skill's scripts directly.

## Reference Documents

- `references/cli-installation-guide.md` — CLI installation and configuration
- `references/iam-policies.md` — Least-privilege IAM policies
- `references/verification-method.md` — Verification method details
- `references/dataflow-diagram.md` — Mermaid data flow diagram
- `references/acceptance-criteria.md` — Acceptance criteria
- `references/related-commands.md` — Command quick reference
- `references/security-audit-guide.md` — Phase 6 five-tool security audit and remediation guide

## Best Practices

- During Phase 1 requirements analysis, try to cover all functional dimensions to avoid rework in later phases
- In Phase 2 technical research, prioritize CLI, then SDK, and API last; do not use SDK when CLI is available
- In Phase 2, read SDK `_http_info` to get real API paths; strictly prohibited from inferring
- In Phase 4/5 testing, mutating operations (Create/Update/Delete) must be confirmed by the user before execution
- If Phase 6 compliance check fails, fix the issues first, then re-verify; do not skip

## Notes

- Six-phase pipeline strictly follows sequential order; no phase may be skipped
- API endpoints are only allowed from SDK source `_http_info` or Huawei Cloud API Explorer; strictly prohibited from inferring via naming patterns
- **Pre-check is a hard gate.** Credentials (AK/SK) are sourced from environment variables or active CLI profile — never read, echoed, hardcoded, or entered through `hcloud configure set` with literal values
- **If AK/SK is not set after running the Pre-check, output the env-var setup template (`export HUAWEI_ACCESS_KEY=...` / `export HUAWEI_SECRET_KEY=...`) for the user to fill out-of-band. NEVER ask the user to paste AK/SK into chat. If the user does not configure, terminate the process. Strictly prohibited from skipping any step that requires credentials**
- BSS service SDK must use GlobalCredentials + with_endpoints; BasicCredentials must not be used
- Resources created during resource lifecycle testing must be cleaned up in Phase 6 to avoid leftovers
- When the Phase 6 security audit fails, CRITICAL/ERROR level issues must be fixed and the Agent must rerun the audit
- skill-scanner only detects known cloud API key formats; common passwords/Chinese keyword credentials require gitleaks supplementary detection
- The skillPath in skills-lock.json is: skills/devtools/common/huawei-cloud-skill-creator/SKILL.md

## Design Principles

- **Six-Phase Strict Pipeline** — Phases are chain-dependent and cannot be skipped
- **Phase 2 No API Inference** — API endpoints only from SDK source `_http_info` or Huawei Cloud API Explorer; strictly prohibited from guessing via naming patterns
- **Phase 3 Generate Based on Facts** — CLI commands / SDK scripts / API endpoints generated per Phase 2 conclusions; no endpoint → mark ⛔
- **Phase 4/5 Real Execution** — Every command must be actually executed and verified; if it fails, fallback or mark
- **Phase 6 Double Check** — Resource cleanup + specification compliance + six-phase completeness
- **Credential Security** — No hardcoded AK/SK, read from environment variables, write operations require user confirmation
- **Credentials Mandatory** — If AK/SK is missing, output the env-var setup template (`export HUAWEI_ACCESS_KEY=...` / `export HUAWEI_SECRET_KEY=...`) and let the user fill it out-of-band. **Never** ask the user to paste AK/SK into chat. If the user does not configure, terminate process. Strictly prohibited from skipping
- **Least Privilege** — iam-policies.md provides least-privilege policy JSON
