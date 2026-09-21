---
name: huawei-cloud-skill-creator
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

---

## Overview

The Huawei Cloud Skill Creator v2 is based on a six-phase strict pipeline: starting with Socratic Q&A requirements analysis, followed by technical research (CLI→SDK→API three-level fallback), document generation, test preparation, detailed testing, resource cleanup and compliance check, ultimately generating a complete skill package that conforms to the Huawei Cloud Skill Specification. It only creates/packages skills — it does not directly operate cloud resources (no creating/deleting/modifying ECS, VPC, OBS, etc.); use it to generate a management Skill or use another dedicated management Skill for cloud-resource operations.

**Dependency**: Quality telemetry is collected automatically via skill-quality-cli (installed by scripts/ensure_cli.sh if absent).

## Pre-check: Huawei Cloud Credentials Required

> **Mandatory gate.** This pre-check MUST pass before invoking any hcloud / huaweicloudsdk command — including Phase 2 research, Phase 4/5 testing, and Phase 6 validation. If no valid credential profile is detected, STOP and obtain credentials **out-of-band**.

### Security Rules

- **NEVER** read, echo, or print AK/SK values (e.g., printing the value of an HUAWEI_ACCESS_KEY-style env var is **FORBIDDEN**).
- **NEVER** read or cat the on-disk credential files for hcloud, obsutil, the SDK, or any other secret-storing location. Treat all such files as confidential.
- **NEVER** ask the user to input AK/SK directly in the conversation or command line.
- **NEVER** invoke hcloud configure set with literal credential strings passed via the CLI's cli-<ak-flag> / cli-<sk-flag> parameters or any equivalent in-band secret-entry form.
- **ONLY** use hcloud configure list to check credential status — non-interactive, read-only, no secrets echoed.

### Step 0: Ensure skill-quality-cli is installed

Before running any wrapped `hcloud` command in a fresh environment, run the idempotent installer first:

```bash
bash scripts/ensure_cli.sh
```

`ensure_cli.sh` is non-blocking by design (warns and exits 0 even on failure), so **verify it actually
works**; if the CLI is still missing, run the fail-closed manual installer:

```bash
command -v skill-quality-cli >/dev/null 2>&1 && skill-quality-cli version >/dev/null 2>&1 || bash scripts/install_cli.sh
```

**Failure handling**: if `skill-quality-cli` remains unavailable after `install_cli.sh` (network /
checksum / platform), **terminate the Pre-check** — do not fall back to bare `hcloud`
(the Mandatory wrapper below applies to every hcloud call; the bundled quality-CLI installer
ships in created skills as `scripts/ensure_cli.sh` + `scripts/install_cli.sh`).

### Verification Steps

> **⚠️ Mandatory: every `hcloud` command in this skill MUST be wrapped with `skill-quality-cli run --skill-name huawei-cloud-skill-creator -- ` — bare `hcloud` calls are strictly forbidden.**

```bash
skill-quality-cli run --skill-name huawei-cloud-skill-creator -- hcloud configure list
skill-quality-cli run --skill-name huawei-cloud-skill-creator -- hcloud ECS ListFlavors --cli-region=cn-north-4 --help
```

Check the output for a valid profile (AK/SK, or temporary security credentials / agency-assumed role).

If no valid profile exists, **STOP** here.

1. Obtain credentials from **Huawei Cloud Console** → 身份与访问管理 (IAM) → 我的凭证 → 新增访问密钥.
2. **Output** the following copy-paste ready env-var setup block to the user (fill in real values **outside** of this session, never in chat). The Agent must **NEVER** ask the user to type the AK/SK value in the conversation — only emit the template below:

   ```bash
   # Set Huawei Cloud credentials using the standard HUAWEICLOUD_SDK_* names
   # (read by hcloud CLI and huaweicloudsdk). The secret key is entered silently.
   export HUAWEICLOUD_SDK_AK="<your-access-key-id>"
   read -rs HUAWEICLOUD_SDK_SK; export HUAWEICLOUD_SDK_SK
   export HUAWEICLOUD_SDK_REGION="cn-north-4"
   # 临时凭证(可选): export HUAWEICLOUD_SDK_SECURITY_TOKEN="<temporary-token>"
   ```

   Optional alternative (interactive out-of-band step only, never with literal values): run hcloud configure interactively in the user's terminal, then verify the result with hcloud configure list.
3. After the user confirms they have configured env vars (or run hcloud configure), re-run skill-quality-cli run --skill-name huawei-cloud-skill-creator -- hcloud configure list. If the profile is valid → resume Phase 1. If still missing → terminate, do not proceed.

> **Reuse the active CLI profile for all subsequent hcloud and huaweicloudsdk calls.** Do not print or hardcode secrets. Do not replace this gate with obsutil config, hcloud configure set with literal arguments, SDK credentials constructors filled with literal strings (for example, the SDK's BasicCredentials built from string literals rather than env vars), or any other in-session secret-entry flow.

### Credential Source Priority

When invoking commands later (Phase 2/4/5), the skill accepts credentials in this priority order:

1. **Environment variables** — auto-scan all variables prefixed with HUAWEI / HW / HWC whose names contain ACCESS_KEY / _AK / SECRET_KEY / _SK.
2. **hcloud configure list profile** — active CLI profile (verified via hcloud configure list in the Pre-check); preferred for hcloud calls.
3. **IAM agency / temporary credentials** — AK/SK + SecurityToken (programmatic access).

If **none** of the above are available when Phase 4/5 testing starts, prompt the user once to configure them out-of-band and re-run the pre-check. If still unavailable, **terminate the process** — strictly prohibited from skipping credential-required steps.

## Prerequisites

1. **hcloud CLI** installed and authenticated — Reference: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
   - Authentication verified via the **Pre-check** above (hcloud configure list).
2. **Python 3.8+** with huaweicloudsdk packages — install on demand: pip install huaweicloudsdkcore huaweicloudsdkecs. Verify with python3 -c "import huaweicloudsdkcore" before Phase 2/4/5. SDK Reference: https://console.huaweicloud.com/apiexplorer/#/sdkcenter
3. **Node.js + npx** available
4. **Huawei Cloud AK/SK** — Auto-scan all environment variables prefixed HUAWEI / HW / HWC matching ACCESS_KEY / _AK / SECRET_KEY / _SK. Hardcoding AK/SK in scripts, docs, or command lines is **forbidden**.
5. **API Reference**: https://console.huaweicloud.com/apiexplorer/#/openapi
- **skill-quality-cli** — ensured by bash scripts/ensure_cli.sh (idempotent, skips if present)
  - Upgrade: run skill-quality-cli upgrade manually (no auto-upgrade)
  - Disable telemetry report: set SKILL_QUALITY_REPORT=0
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

**Output:** phase-1-summary.json — User-confirmed requirements description

### Phase 2: Technical Research (CLI→SDK→API Three-Level Fallback)

**Dependency:** Phase 1 requirements analysis completed (phase-1-summary.json exists)

For each feature point confirmed in Phase 1, research availability in the following order:

1. **CLI** — hcloud command. Run hcloud <Service> <Operation> --cli-region=cn-north-4 --help; the command exists when parameters are validated.
2. **SDK** — huaweicloudsdk. Run python3 -c "from huaweicloudsdk{service}.v2 import ..."; the SDK package is available when the class imports.
3. **API** — **Only from the following two sources**; endpoint must come from a trusted source, never inferred.

**Core Rule: API Endpoint Forensics (No Guessing)**

API endpoints are **only allowed** from the following two sources. **Strictly prohibited from inferring through naming patterns**:

| Trusted Source | Method |
|----------------|--------|
| ① SDK source _http_info / resource_path | grep -A8 the _http_info method in {service}_client.py, then read the resource_path value |
| ② Huawei Cloud API Explorer (api-explorer.huaweicloud.com) | User searches and confirms on that website |

**❌ Strictly prohibited actions:**

- Inferring new endpoints based on other API path patterns (e.g., inferring claim-vouchers endpoint from coupons endpoint)
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
python3 -c "import huaweicloudsdk{service}.v2 as m; import os; print(os.path.dirname(m.__file__))"  # package path
grep "_http_info" <path>/{service}_client.py                                                          # all API endpoints
grep -A8 "_{method}_http_info" <path>/{service}_client.py                                             # "resource_path" = real REST endpoint
```

**Output:** phase-2-summary.json — Execution mode (CLI/SDK/API/⛔) and corresponding command/code/API path for each feature point

### Phase 3: Document Generation

**Dependency:** Phase 2 technical research completed (phase-2-summary.json exists)

Generate Skill files based on Phase 2 conclusions:

1. **Name the Skill** — Use huawei-cloud-{product}-{function} and make the frontmatter name match the directory name.
2. **Language** — Generate SKILL.md in **English** by default. Chinese documentation may be added in references/ as supplementary. The main SKILL.md must use English for frontmatter description, section titles, command examples, and all explanatory content.
3. **Frontmatter** — Include name, description with a feature summary and trigger conditions, and no more than five tags. Do not generate a version field.
4. **Create directory structure:**

   ```text
   skills/{skill-name}/  → SKILL.md, references/ (iam-policies.md recommended; cli-installation-guide.md recommended when CLI is used; verification-method.md / dataflow-diagram.md / acceptance-criteria.md recommended), scripts/test-cli-commands.sh, scripts/ensure_cli.sh + scripts/install_cli.sh (quality CLI, required — see rule 14), templates/test-vars.json
   ```

5. **SKILL.md content generation rules:**

   - **CLI** — command format: hcloud <Service> <Operation> --cli-region={region} [--params] (template; replace placeholders with real values before execution)
   - **SDK** — Python script example (python3 -c "...") with real SDK client calls
   - **API** — curl command + user-provided endpoint (mark as user-provided)
   - **Unavailable** — mark requires manual verification, do not generate specific commands

6. **Required sections in SKILL.md:**

   - YAML Frontmatter (Critical) — must parse as valid YAML via yaml.safe_load: name + description (feature summary + trigger conditions) + tags (list, ≤5); no version field
   - Overview (High) — feature overview, architecture, applicable scenarios
   - Prerequisites (High) — CLI version, authentication configuration, IAM permissions
   - Workflow (High) — skill workflow steps
   - Core Commands (High) — command examples grouped by function (real, executable commands only)
   - Parameter Confirmation (High) — user-configurable parameter table
   - Reference Documents (Critical) — links to documents under references/
   - KooCLI Command Format Standard (Low) — required when CLI is involved; service, operation, region, and parameter syntax

7. **Generate Mermaid data flow diagram** → references/dataflow-diagram.md.
8. **Generate IAM policies** → references/iam-policies.md using least privilege. **IAM authoring rules (mandatory):**
   - **严禁虚构伪造** — never invent, guess, or fabricate IAM Action names, system-policy names, or syntax.
   - **必须官方核实** — verify through at least one official source:
     1. **KooCLI Schema query**: hcloud IAM GetAuthorizationSchemaV5 --cli-region=cn-north-4 --service_code=<service_code> — copy the exact name and urn_template values from the response; do not re-capitalize or normalize them.
     2. **官方文档核对** — Huawei Cloud 《权限及授权项说明》 / 《API参考》 to confirm the standard service:resource_type:action naming.
     3. **系统策略查询** — hcloud IAM ListPoliciesV5 + hcloud IAM GetPolicyVersionV5 to verify real system-policy names and the exact JSON syntax (document field).
   - **策略版本（Version）标准**：
     - IAM 5.0 身份策略使用 "Version": "5.0"（系统策略与现代自定义策略标准；已验证格式如 {"Version":"5.0","Statement":[{"Effect":"Allow","Action":[...]}]}）。
     - 仅当兼容传统 IAM v3 模板时使用 "Version": "1.1"。
     - **禁止书写未经官方验证的版本号**（如 "1.0"）。
9. **Record API references** — Keep verified API paths in phase-2-summary.json. If a generated Skill needs reusable API documentation, add a reference file under references/ using an allowed kebab-case filename.
10. **Package limits** — Total file content size ≤ 40 MB, total files ≤ 30, and SKILL.md ≤ 500 lines. Split oversized SKILL.md content into references/.
11. **File extension allowlist** — Every file must have one of these 46 extensions:
    .md, .mdx, .txt, .json, .json5, .yaml, .yml, .toml, .js, .cjs, .mjs, .ts, .tsx, .jsx, .py, .sh, .ps1, .psm1, .psd1, .r, .rb, .go, .rs,
    .swift, .kt, .java, .cs, .cpp, .c, .h, .hpp,
    .sql, .csv, .tsv, .ini, .cfg, .conf, .env, .properties, .dat, .xml, .html, .css, .scss, .sass, .svg.
    Files without an extension or outside this allowlist must be removed or renamed.
12. **YAML frontmatter format check** — SKILL.md frontmatter must be a valid YAML doc: root map, name/description non-empty, tags ≤5, no version, block scalar description.
    A stray :/quote/misindent invalidates the frontmatter (critical); regenerate before proceeding.
13. **Change scope** — A pull request must change only one Skill directory. Use bash scripts/validate-skill.sh -s {skill-path} -b <base-ref> to validate the PR diff when a base ref is available.
14. **Quality-CLI integration (required for every generated skill)** — the generated skill must carry the same quality-reporting capability as this creator skill itself (skill-quality-cli telemetry, opt-out via SKILL_QUALITY_REPORT=0):
    - **Scripts**: copy scripts/ensure_cli.sh and scripts/install_cli.sh from THIS skill's scripts/ into the generated skill's scripts/ (identical content — do not hand-rewrite).
    - **SKILL.md 4-point embed** (idempotent — skip any part already present):
      a. Overview 末尾加 1 句: **Dependency**: Quality telemetry is collected automatically via skill-quality-cli (installed by scripts/ensure_cli.sh if absent).
      b. Prerequisites 追加: - **skill-quality-cli** — ensured by bash scripts/ensure_cli.sh (idempotent, skips if present)，另加 2 行   - Upgrade: run skill-quality-cli upgrade manually (no auto-upgrade) 与   - Disable telemetry report: set SKILL_QUALITY_REPORT=0
      c. 在核心流程第一个 ```bash 代码块内前置强制指令（用生成 skill 自己的 name 替换 <name>）: > **⚠️ Mandatory: every hcloud command in this skill MUST be wrapped with skill-quality-cli run --skill-name <name> -- ** — bare hcloud calls are strictly forbidden.**
      d. 将 SKILL.md 所有 ```bash 代码块内的裸 hcloud <Service> <Operation> ... 命令包裹为 skill-quality-cli run --skill-name <name> -- hcloud ...（已包裹的跳过；<placeholder> 模板行不包）
    - **references**: 在生成的 references/cli-installation-guide.md 中合并 skill-quality-cli 章节（ensure_cli.sh 幂等就绪 / install_cli.sh 手动安装 / 手动 upgrade / SKILL_QUALITY_REPORT=0 关闭）— 不得删除既有 KooCLI 安装与认证内容。
    - **Execution name**: 所有嵌入用生成 skill 自身的 frontmatter name，禁止用本 creator 的 name。
    - **Re-validate**: 注入后重跑 bash scripts/validate-skill.sh -s {skill-path}，确认 SKILL.md ≤ 500 行、文件 ≤ 30。

**🛑 Strictly prohibited from generating hallucinated URIs / fabricated API paths. Feature points not verified in Phase 2 must not have specific commands written.**

**Output:** phase-3-summary.json — List of generated files and structure validation results

### Phase 4: Test Preparation

**Dependency:** Phase 3 document generation completed (phase-3-summary.json exists)

1. **Generate test cases** — Split test cases based on Phase 2/3 feature points

- **CLI cases** — one case per hcloud command; e.g., `hcloud ECS ListServersDetails --cli-region=cn-north-4 --limit=1`
   - **SDK cases** — one case per SDK call; e.g., list_sub_customer_coupons(limit=1) — note: BSS SDK only supports cn-north-1 and similar regions, use --cli-region=cn-north-1 (or HUAWEI_REGION=cn-north-1) for BSS samples
   - **API cases** — one case per user-provided endpoint; e.g., curl -X GET {endpoint}
   - **Own-script smoke cases** — 每个自带脚本至少 1 条正例：有 --help/-h 的脚本用 --help 冒烟；否则用 bash -n <脚本绝对路径> 语法检查。脚本路径必须解析为绝对路径（如 bash $PWD/scripts/ensure_cli.sh --help），避免相对路径在执行时失效。示例：bash $PWD/scripts/ensure_cli.sh --help / bash -n $PWD/scripts/validate-skill.sh

2. **Save test cases as JSON** → templates/test-vars.json:

   ```json
   {"test_cases": [{"id": "TC-01", "name": "...", "command": "...", "expected": "..."}]}
   ```

3. **Show all test cases to the user for confirmation**

4. **Run tests:**
    - Read AK/SK from environment variables: 自动扫描所有以 HUAWEI / HW / HWC 开头的环境变量，匹配其中含 ACCESS_KEY / _AK / SECRET_KEY / _SK 的键值对
    - **If no valid AK/SK env or CLI profile: re-run the Pre-check template and STOP — never ask AK/SK in chat; if user won't provide env vars, terminate.**
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

**Output:** phase-4-summary.json — Test case list + per-case execution results

### Phase 5: Detailed Testing

**Dependency:** Phase 4 test preparation completed (phase-4-summary.json exists)

1. **Full regression:** Execute all test cases generated in Phase 4 — **所有 CLI 回归用例必须真实执行**
2. **Resource lifecycle testing** (Skills involving resource creation/modification/deletion):
   - Create resource → verify creation succeeded (query to confirm) → runtime query → destroy resource → verify release
   - Test report outputs information on created/modified/deleted resources
   - **Prompt the user and wait for confirmation before each step**
3. **Management-type Skills**: CRUD → end-to-end full testing; query-only → output query results to test report
4. **Report generation:** Test results aggregated by case; detailed resource-change records; detailed error info for failed cases

**Output:** phase-5-summary.json — Detailed test results + resource operation records

### Phase 6: Resource Cleanup and Compliance Check

**Dependency:** Phase 5 detailed testing completed (phase-5-summary.json exists)

1. **Resource Cleanup:**
   - Check whether all resources created in Phase 5 have been released
   - Unreleased resources → Prompt user and attempt cleanup
   - Record cleanup results

2. **Huawei Cloud Skill Specification Compliance Check** (against 华为云Skill检查规范):

   - SKILL.md exists (Critical) — file existence check
   - Skill directory under skills/ (Low) — path format: skills/{category}/{subcategory}/{skill-name}/
   - Skill package naming convention (High) — directory name matches huawei-cloud-{product}-{function}
   - One PR submits only one Skill (Critical) — git diff checks that PR changes only affect a single Skill directory
   - YAML Frontmatter exists (Critical) — grep for the --- delimiter
   - name field exists (Critical) — frontmatter name field exists and matches directory name
   - description field exists (Critical) — frontmatter description field exists and contains feature summary + trigger words
   - description includes trigger words (Medium) — accept Triggers include:, Use when, or equivalent trigger conditions
   - Should not contain version field (Low) — no version field in frontmatter
   - Overview section (High) — match Overview or 概述
   - Prerequisites section (High) — match Prerequisites or 前置条件
   - Workflow section (High) — match Workflow or 工作流
   - Core Commands section (High) — match Core Commands or 核心命令
   - Parameter Confirmation section (High) — match Parameter Confirmation or 参数确认
   - Reference Documents section (Critical) — match Reference Documents, References, or 参考文档
   - KooCLI Command Format Standard section (Low) — required when CLI is involved; match the English or Chinese heading
   - references/cli-installation-guide.md (Medium) — recommended when CLI is involved, file existence (optional)
   - Quality-CLI integration (High) — scripts/ensure_cli.sh + scripts/install_cli.sh exist; SKILL.md contains the skill-quality-cli run Mandatory mandate and wrapped hcloud commands
   - references/iam-policies.md (Medium) — recommended, file existence (optional)
   - references/verification-method.md (Medium) — recommended file existence
   - references/acceptance-criteria.md (Low) — recommended file existence
   - Reference document kebab-case naming (Low) — file names under references/ are all lowercase kebab-case
   - Credential hardcoding (Critical) — grep for credential hardcoding patterns and CLI credential config
   - Cross-Skill direct calls (Critical) — grep other Skill names
   - CLI write operations require confirmation (Low) — check whether user confirmation is prompted
   - Service name requirement (Medium) — every concrete hcloud service matches a KooCLI Service name and starts with uppercase/title case, such as ECS, CloudPond, or IAMAccessAnalyzer
   - Operation name PascalCase (Medium) — every concrete operation name uses PascalCase
   - Includes --cli-region (Medium) — every concrete CLI command includes the region parameter
   - Total skill size ≤ 40 MB (Medium) — sum all file content sizes under the Skill directory
   - Total file count ≤ 30 (Medium) — count SKILL.md and every file in all subdirectories
   - SKILL.md line count ≤ 500 (Medium) — split excess content into references/
   - File extensions in allowlist (Medium) — reject extensionless files and extensions outside the 46-type allowlist

3. **Final report:**
   - Merge Phase 1-6 phase summaries
   - Output complete creation report
   - Mark all incomplete items

4. **Final six-phase completeness check:**

   ```
   Check phase-1-summary.json exists → If missing, restart from Phase 1
   Check phase-2-summary.json exists → If missing, restart from Phase 2
   Check phase-3-summary.json exists → If missing, restart from Phase 3
   Check phase-4-summary.json exists → If missing, restart from Phase 4
   Check phase-5-summary.json exists → If missing, restart from Phase 5
   Check phase-6-summary.json exists → If missing, restart from Phase 6
   ```

   **All phases complete → Creation done. Missing phases → Restart from the missing phase.**

5. **Clean up phase summary files:** After the completeness check passes, delete all
   phase-*-summary.json files under the skill directory. **Only** run the deletion after
   the completeness check fully passes and the <skill-path> has been verified (it must be a
   legitimate directory of the skill under test). Do **not** chain the deletion onto other
   checks; use a guarded, quoted single command for phase-*-summary.json only.

   **Note:** Only perform cleanup after the completeness check **fully passes**. If there are missing phases, do not clean up; restart from the missing phase.

**Output:** phase-6-summary.json — Final creation report + compliance check results

## KooCLI Command Format Standard

hcloud <Service> <Operation> --cli-region=<region> [--key=value ...] — 底层语法格式。

- **Service name** — exact KooCLI Service name beginning with uppercase/title case, e.g. ECS, VPC, CloudPond, IAMAccessAnalyzer
- **Operation name** — PascalCase, e.g. ListServers, ShowServer
- **Region parameter** — --cli-region=<value>, e.g. --cli-region=cn-north-4
- **Simple parameter** — --key=value, e.g. --server_id=xxx
- **Indexed parameter** — --key.1=value1, e.g. --servers.1.id=xxx

## Core Commands

### 真实命令区（Real Command Area — 可直接执行验证）

以下为真实可执行的只读命令，用于 Pre-check 与 Phase 2/4/5 真实验证（`{path}` 等为占位符，实际执行时替换为真实路径，见 Parameter Confirmation）：

| Command | Purpose |
| --------- | --------- |
| `hcloud ECS ListFlavors --cli-region=cn-north-4 --limit=1` | Phase 2/5: 查询 ECS 规格（只读，真实可执行） |
| `hcloud ECS ListServersDetails --cli-region=cn-north-4 --limit=1` | Phase 4/5: 查询 ECS 列表（只读，真实可执行） |
| `hcloud configure list` | Pre-check: 校验 CLI 凭据配置（只读，真实可执行） |
| `python3 -c "import huaweicloudsdkcore"` | 前置检查: SDK 可用性（真实可执行） |

### 命令说明区（Command Description Area — 格式说明，非直接执行）

以下行仅作格式说明，**命令行提取器只提取以 bash / hcloud / python3 / curl 开头的真实命令；以 # 开头的行是说明，会被跳过**：

- **hcloud CLI 通用格式**：hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]，详见 KooCLI Command Format Standard。
- **结构/规范校验（Phase 3/6）**：执行 bash scripts/validate-skill.sh 并传入 -s 参数指向目标 skill 目录（如 -s skills/devtools/common/huawei-cloud-skill-creator）。
- **功能测试（Phase 4/5）**：执行 bash scripts/test-cli-commands.sh，传入 -s 参数指向 skill 目录、-e 参数选择执行模式（cli/sdk/api/auto）。
- **质量 CLI 就绪**：执行 bash scripts/ensure_cli.sh（幂等；缺失时自动安装 skill-quality-cli），手动安装用 bash scripts/install_cli.sh。

> test-cli-commands.sh 仅执行白名单命令（hcloud/python3/curl/bash 开头），其他命令被拒绝且不会执行。validate-skill.sh 对不存在的 skill 目录会明确报错（exit 1）。

## Parameter Confirmation

| Parameter | Required | Description | Example |
| ----------- | ---------- | ------------- | --------- |
| skill-path | Yes | Target Skill directory path | e.g., huawei-cloud-ecs-manage |
| region | No | Huawei Cloud region (BSS only supports cn-north-1 and similar regions) | cn-north-4 (BSS: cn-north-1) |
| executor | No | Execution mode (cli/sdk/api) | cli |

## Edge Cases

| Scenario | Handling |
| ---------- | ---------- |
| User skips questions and says "start" directly | Remind: requirements analysis must be completed first, start from Phase 1 questions |
| AK/SK environment variables not set | Re-run the **Pre-check** above. Output the env-var setup template (export HUAWEI_ACCESS_KEY=... / export HUAWEI_SECRET_KEY=...) and let the user fill it out-of-band. **NEVER** ask the user to paste AK/SK into chat. If user does not configure, terminate process, strictly prohibited from skipping |
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
| SDK has method but actual API path unknown | Read SDK source grep _http_info {service}_client.py to get real path |
| BSS service SDK initialization fails (GlobalCredentials) | BSS is global and must use GlobalCredentials with with_endpoints, not BasicCredentials with with_region; **BSS 仅支持 cn-north-1 等区域（--cli-region=cn-north-1 / HUAWEI_REGION=cn-north-1）** |
| list_sub_customer_coupons query returns 400 | BSS limit parameter maximum is 100, not the default 200; use region cn-north-1 for BSS SDK samples |

## Verification Method

### Specification Compliance Verification

```bash
bash scripts/validate-skill.sh -s {skill-path}   # Check against 华为云Skill检查规范
```

### Functional Testing

```bash
bash scripts/test-cli-commands.sh -s {skill-path} -e {cli|sdk|api}   # CLI priority → SDK fallback → API fallback
```

## Reference Documents

- references/iam-policies.md — Least-privilege IAM policies
- references/verification-method.md — Verification method details
- references/dataflow-diagram.md — Mermaid data flow diagram
- references/acceptance-criteria.md — Acceptance criteria
- references/related-commands.md — Command quick reference

## Notes & Design Principles

- **Six-phase strict pipeline** — phases are chain-dependent, sequential, and cannot be skipped
- **Phase 2/3 Fact-based** — endpoints only from SDK _http_info/API Explorer (no inference); commands per Phase 2 conclusions; no endpoint → mark ⛔
- **Phase 4-6 Verify** — every command really executed (mutating ops need confirmation); Phase 6: cleanup + compliance + completeness; fix failures, re-verify
- **Credential Security** — no hardcoded AK/SK; read from env vars (HUAWEI_*/HW_*/HWC_* AK/SK markers) or active CLI profile; never hcloud configure set with literal secrets
- **Credentials Mandatory** — if AK/SK missing after the Pre-check, output the env-var setup template for out-of-band fill; never ask the user to paste AK/SK into chat; if still unconfigured, terminate
- **BSS SDK** must use GlobalCredentials + with_endpoints, not BasicCredentials with with_region.
- **BSS 区域**：BSS 服务仅支持 cn-north-1 等区域；涉及 BSS 的示例命令应标注 --cli-region=cn-north-1（SDK 初始化也用 cn-north-1），test-defaults.json 中 region: cn-north-1 即为此口径。
- **Cleanup** — resources created during lifecycle testing must be released in Phase 6
- **Least privilege** — iam-policies.md provides least-privilege policy JSON; the skillPath in skills-lock.json is skills/devtools/common/huawei-cloud-skill-creator/SKILL.md
- **IAM authoring (official only)** — IAM action names MUST be verified via GetAuthorizationSchemaV5 / docs / ListPoliciesV5; never inferred; Version 5.0 for IAM 5.0, 1.1 only for legacy v3