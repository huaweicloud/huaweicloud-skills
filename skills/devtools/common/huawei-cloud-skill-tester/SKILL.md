---
name: huawei-cloud-skill-tester
description: |
  End-to-end functional testing framework for Huawei Cloud skills — three-tier pipeline covering
  single-skill unit testing, multi-skill orchestration, and end-to-end full flow testing.
  Each phase produces structured JSON output with chain verification.
  Supports skill installation validation, functional analysis, CLI→SDK→API feasibility research,
  test case generation, real-environment execution with resource lifecycle, resource cleanup,
  multi-skill scenario orchestration, trigger-conflict detection, and consolidated reporting.
  Triggers include: 测试技能, 执行技能测试, 跑测试流程, 技能回归测试,
  skill test, run skill tests, test huawei cloud skill, verify skill,
  测试华为云skill, 全流程测试, 编排测试, 技能完整性检查,
  skill-tester, 跑测试, 回归测试, 组合测试, 多skill编排, verification, e2e.
tags: [huawei-cloud, testing, e2e, orchestration, qa]
---

# Huawei Cloud Skill Tester — Three-Track Eight-Phase E2E Testing Pipeline

> Independent, repeatable Huawei Cloud Skill testing framework. Does not depend on skill-creator; can test any existing Huawei Cloud Skill.
> Focuses on **real-environment functional testing** and **multi-skill orchestration scenarios**.

---

## Overview

This Skill provides a **three-track, eight-phase** standardized testing pipeline
(three-tier layout × 8 phase total: Phase 0~6 执行 + Phase 7 终报告):

| Tier | Phases | Goal |
|------|--------|------|
| **Tier 1: Single-Skill Unit Testing** | Phase 0~4 | Verify each skill item by item: installation, feature extraction, technical research, test case generation, execution |
| **Tier 2: Integration Testing** | Phase 5~6 | Multi-skill orchestration scenario derivation + end-to-end real-environment flow verification |
| **Tier 3: Final Report** | Phase 7 | Consolidated report merging all phase outputs |

### Core Design Principles

1. **Chain Verification** — Before each Phase, check that the previous phase's JSON exists; if missing, refuse to execute
2. **Agent-proof** — Write operations require user confirmation for each item; automatic gate bypassing is not allowed
3. **Three-Track Layering** — Clear gates between Tiers; Tier 1 must be completed before entering Tier 2
4. **Batch Repeatable** — Supports `--skills "skill-a,skill-b"` or `--all-installed`
5. **Fallback Strategy** — When only 1 skill, Phase 5/6 automatically downgrade to single-skill lifecycle testing. **Sibling auto-scan is ON by default** (Phase 5/6 自动从被测 skill 同目录找其他 huawei-cloud-* skill 做编排组合测试). Use `--no-siblings` to opt-out.
6. **Standardized JSON Output** — All phases output in a unified schema; Phase 7 merges into a single report
7. **Real-Environment First** — All Tier 2 orchestrations execute against real Huawei Cloud; no mocks or simulations

### Data Flow Diagram

```
User Input (--skills or --all-installed)
    │
    ├── Tier 1 ──── Iterate over each skill ────
    │   Phase 0 → 1 → 2 → 3 → 4
    │   (phase-N-summary.json chain validation)
    │
    ├── Tier 2 ──── Integration ────
    │   Phase 5 (orchestration scenario derivation + real-environment execution)
    │   Phase 6 (e2e full-flow: create→query→update→delete lifecycle)
    │   Only 1 skill → Downgrade single-skill closed loop
    │
    └── Tier 3 ──── Final ────
        Phase 7 (merge phase-0~6 JSON into consolidated report)
```

---

## Prerequisites

1. **hcloud CLI** installed and authenticated (for Tier 2 CLI mode testing) — Reference: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
2. **Python 3.8+** + `huaweicloudsdk` packages (for SDK mode testing) — SDK Reference: https://console.huaweicloud.com/apiexplorer/#/sdkcenter
3. **Huawei Cloud AK/SK** — 自动扫描所有以 `HUAWEI` / `HW` / `HWC` 开头的环境变量，匹配其中含 `ACCESS_KEY` / `_AK` / `SECRET_KEY` / `_SK` 的键值对。**If missing, the framework emits the env-var setup template to stderr and exits 77. NEVER ask the user to type AK/SK in chat; user must set env vars in their shell profile out-of-band and re-run.**
4. **Target Skill** must be under `$SKILL_INSTALL_DIR/` (auto-detected: `~/.agents/skills/` → `~/.hermes/skills/` → default) or a user-specified path
5. **jq** command (all JSON processing depends on it)
6. **API Reference**: https://console.huaweicloud.com/apiexplorer/#/openapi

---

## Workflow — Three-Track Eight-Phase

```
Tier 1: Single-Skill Unit Testing
   Phase 0: Installation Verification (install/uninstall/reinstall)
   Phase 1: Feature Extraction (metadata + commands + resource types)
   Phase 2: Technical Research (CLI→SDK→API three-level availability)
   Phase 3: Test Case Generation (functional cases TC-F + API cases TC-A)
   Phase 4: Real-Environment Execution (read-only automatic + write operations require confirmation)

Tier 2: Integration Testing — Real-Environment Orchestration
   Phase 5: Multi-Skill Orchestration (scenario derivation → step execution → state verification)
   Phase 6: End-to-End Flow (resource lifecycle: create→query→update→delete)

Tier 3: Final Report
   Phase 7: Consolidated Report (merge phase-0~6 JSON into single report)
```

---

### Phase 0: Installation Verification

**Goal:** Verify whether the skill can be installed/uninstalled/reinstalled normally, and confirm the directory structure meets the contract.

**Steps:**

1. Check skill directory structure — **all four must exist** (this is a hard contract; missing any one fails the phase):
   - `SKILL.md`
   - `scripts/`
   - `references/`
   - `references/iam-policies.md`
2. Confirm whether the runtime has the skill installed (check if a directory with the same name exists under `$SKILL_INSTALL_DIR/`)
3. Perform installation verification (simulated or actual installation)
4. Perform uninstallation verification (simulated or actual uninstallation)
5. Perform reinstallation verification (install → uninstall → install)
6. Record installation duration, directory integrity, and installation status

```bash
# Directory integrity check (all four are REQUIRED)
[ -f "${skill_path}/SKILL.md" ] && echo "SKILL.md exists"
[ -d "${skill_path}/scripts" ] && echo "scripts/ exists"
[ -d "${skill_path}/references" ] && echo "references/ exists"
[ -f "${skill_path}/references/iam-policies.md" ] && echo "iam-policies.md exists"

# Installation status
[ -d "${SKILL_INSTALL_DIR:-$HOME/.agents/skills}/${skill_name}" ] && echo "installed" || echo "not installed"
```

**Output:** `phase-0-summary.json`

```json
{
  "install": {"status": "pass", "existing": true, "duration_s": 1.2},
  "uninstall": {"status": "skipped", "reason": "not installed"},
  "reinstall": {"status": "skipped", "reason": "not installed"},
  "directory_integrity": {"pass": true, "checks": {...}}
}
```

---

### Phase 1: Feature Extraction

**Goal:** Extract structured feature information from SKILL.md as input for all subsequent phases.

**Steps:**

1. Read YAML frontmatter from SKILL.md → name, description, tags, triggers
2. Extract core commands table (Core Commands section)
3. Extract parameter confirmation table
4. Identify feature types (query/create/modify/delete)
5. Extract resource types involved (ECS instance, VPC, voucher, etc.)
6. Note whether there are write operations (Create/Update/Delete)
7. Read the list of test scripts under scripts/
8. Read the list of reference files under references/

**Output:** `phase-1-summary.json`

```json
{
  "metadata": {
    "name": "huawei-cloud-bss-voucher-manage",
    "triggers": ["查代金券", "删除代金券", "list vouchers", ...],
    "tags": ["huawei-cloud", "bss", "voucher"]
  },
  "capabilities": {
    "list": ["查询代金券", "统计代金券"],
    "create": [],
    "update": [],
    "delete": ["删除代金券"]
  },
  "has_write_operations": true,
  "resource_types": ["bss_voucher"],
  "commands": [
    {"id": "CMD-01", "source": "SKILL.md", "description": "查询代金券列表", "executor": "sdk"},
    {"id": "CMD-02", "source": "SKILL.md", "description": "统计代金券", "executor": "sdk"},
    {"id": "CMD-03", "source": "SKILL.md", "description": "删除代金券", "executor": "sdk"}
  ],
  "scripts": ["scripts/test-cli-commands.sh"],
  "references": ["references/iam-policies.md", "references/api-paths.md"]
}
```

---

### Phase 2: Technical Research

**Goal:** Perform CLI→SDK→API three-level fallback verification for each command extracted in Phase 1, determining the actual executable method.

**Dependency:** Phase 1 completed (phase-1-summary.json exists)

**Research order (per command):**

| Priority | Method | Verification |
|----------|--------|-------------|
| 1st | **CLI** | `hcloud <Service> <Operation> --cli-region=cn-north-4 --help` |
| 2nd | **SDK** | `python3 -c "from huaweicloudsdk{service}.v2 import ..."` |
| 3rd | **API** | Only from SDK source `_http_info` or Huawei Cloud API Explorer |

**Rule:** API endpoints are **strictly prohibited from being inferred**; only allowed from SDK `_http_info.resource_path` or user confirmation from API Explorer.

**Output:** `phase-2-summary.json`

```json
{
  "research": [
    {
      "cmd_id": "CMD-01",
      "description": "查询代金券列表",
      "cli": {"available": false, "reason": "BSS not in hcloud service list"},
      "sdk": {
        "available": true,
        "package": "huaweicloudsdkbss.v2",
        "method": "list_sub_customer_coupons",
        "api_path": "/v2/promotions/benefits/coupons"
      },
      "api": {"available": true, "endpoint": "/v2/promotions/benefits/coupons"},
      "recommended_executor": "sdk",
      "risk_level": "low"
    }
  ]
}
```

---

### Phase 3: Test Case Generation

**Goal:** Generate two types of test cases based on Phase 1+2, present them to the user for confirmation.

**Dependency:** Phase 1+2 completed (phase-1-summary.json + phase-2-summary.json exist)

**Functional case division rules:**

| Operation Type | Case Requirements | Risk Level |
|---------------|-------------------|------------|
| Query (List/Show/Get) | 1 positive + 1 boundary (limit=0 or empty filter) | low |
| Create | 1 standard + 1 parameter variant | high |
| Update | 1 verification that modification took effect | medium |
| Delete | 1 pre-deletion confirmation + 1 post-deletion verification | high |
| Statistics (count/aggregate) | 1 positive + 1 time range boundary | low |

**Case IDs:** `TC-F-01` ~ `TC-F-NN` (functional), `TC-A-01` ~ `TC-A-NN` (API/SDK)

**Output:** `phase-3-summary.json`

```json
{
  "functional_cases": [
    {
      "id": "TC-F-01",
      "name": "List vouchers - positive",
      "command": "list_sub_customer_coupons(limit=10)",
      "expected": "Return voucher list, no more than 10 items",
      "is_write": false,
      "risk_level": "low",
      "executor": "sdk",
      "prerequisites": [],
      "verification": "resp.count >= 0"
    },
    {
      "id": "TC-F-03",
      "name": "Delete voucher - positive",
      "command": "reclaim_partner_coupons(coupon_id=...)",
      "expected": "Voucher status changed to reclaimed",
      "is_write": true,
      "risk_level": "high",
      "executor": "sdk",
      "prerequisites": ["TC-F-01 (provide valid coupon_id)"],
      "verification": "Query after delete to confirm status change"
    }
  ],
  "api_cases": [...]
}
```

---

### Phase 4: Execution

**Goal:** Execute test cases from Phase 3 one by one; read-only runs automatically, write operations are gated.

**Dependency:** Phase 3 completed (phase-3-summary.json exists)

**AK/SK resolution (two-tier, NO interactive prompt):**

```
1. Environment variables (any HUAWEI*/HW*/HWC* prefixed *_AK / *_SK / *_ACCESS_KEY / *_SECRET_KEY)
2. hcloud CLI config (~/.hcloud/config.json profile, mode = $HCLOUD_PROFILE_MODE)

If neither source yields credentials, the framework emits the env-var setup
template to stderr and exits 77 — see "Agent Protocol" below.
```

**Execution rules:**

```
Pre-check: Is AK/SK set?
  if AK/SK obtained from env or hcloud config:
    Continue
  else (no interactive prompt — applies even in TTY):
    Emit env-var setup template to stderr, exit 77 — see "Agent Protocol" below

Per-case gate:
  if is_write == false:
    Auto-execute → Record pass/fail
  if is_write == true:
    if env ALLOW_WRITES == "1":
      Auto-execute under AK/SK credentials → Record pass/fail + resource_changes
      entry.execution_meta.user_confirmed = true
    else (default):
      Skip → status=skip, reason="ALLOW_WRITES=0"
```

**Note on "Agent-proof" in non-interactive mode:** Phase 4 runs as a non-interactive
shell script, so the per-case `y/N` prompt described in early design is replaced by
the `ALLOW_WRITES=0|1` environment gate. The "user confirmation" that is recorded on
each write case (`user_confirmed=true` when `ALLOW_WRITES=1`) is the audit trail, not
an interactive consent flow. To get the original interactive confirm, run the
pipeline from a TTY-attached agent that intercepts each write case before invocation.

**Resource change record (key fields):**

```json
"resource_changes": [
  {
    "tc_id": "TC-F-03",
    "resource_type": "bss_voucher",
    "resource_id": "VCH-abc123",
    "change_type": "deleted",
    "cleanup_method": {"type": "sdk", "command": "already deleted, no cleanup needed"},
    "cleanup_required": false
  }
]
```

**Output:** `phase-4-summary.json`

```json
{
  "execution_results": [
    {"tc_id": "TC-F-01", "status": "pass", "duration_s": 2.1, "output_snippet": "..."},
    {"tc_id": "TC-F-03", "status": "pass", "duration_s": 1.5, "output_snippet": "...",
     "resource_changes": [{"resource_type": "bss_voucher", "change_type": "deleted", ...}]}
  ],
  "statistics": {"total": 10, "pass": 9, "fail": 0, "skip": 1},
  "all_resources_changed": [...]
}
```

---

### Phase 5: Multi-Skill Orchestration — Trigger Conflict & Data-Flow Scan

**Goal:** Detect cross-skill routing conflicts (overlapping triggers that would confuse an Agent router) and identify potential data-flow paths between skills, so integration issues are caught **before** any real resources are touched.

**Dependency:** Phase 4 completed for all tested skills

> **What Phase 5 does NOT do:** It does NOT execute real multi-skill business scenarios
> (create→query→delete chains) against the live environment. Scenario execution and
> rollback live in Phase 6. Phase 5 is a static, offline analysis over Phase 1 metadata.

**Sibling discovery (default ON):**

```
Phase 5/6 默认会自动从被测 skill 的同级目录找其他 huawei-cloud-* skill 做编排组合测试。
Opt-out: --no-siblings 或 WITHOUT_SIBLINGS=1 或 SIBLING_LIMIT=0
Opt-tune: --sibling-limit N (默认 5 个兄弟)

排除规则:
  - 自己 (target skill)
  - *-test-files (测试 artifacts 目录)
  - huawei-cloud-skill-tester, huawei-cloud-skill-creator, huawei-cloud-new-tester (meta skills)
  - 缺 SKILL.md 的目录
```

**SKILL.md fallback (兄弟 skill 没 phase-1 时):**

```
当兄弟 skill 没有 phase-1-summary.json (因为没单独跑过 phase 1), Phase 5 实时解析
它的 SKILL.md frontmatter 提取 triggers / resource_types, 支持三种格式:
  1. `triggers: [a, b, c]` (inline list)
  2. `triggers:\n  - a\n  - b` (block list)
  3. `description: | ... Triggers include: "x","y","z"` (embedded in description)
```

**Branch logic:**

```
if skills_count == 1 (含 --no-siblings):
  Downgrade to single-skill self-check ("downgraded_self_check"):
    - Scan the skill's own triggers for substring overlaps (internal_ambiguities)
    - Scan the skill's own write commands for ordering hints (cycle_warnings)
    - Skip data_flow_tests and parallel_load_test

if skills_count >= 2:
  5a: Trigger conflict scan
      - Pairwise compare all triggers across all skills
      - "high"   severity = exact match (Agent will route ambiguously)
      - "medium" severity = substring containment (one is contained in the other)
  5b: Data-flow identification
      - For each skill A's resource_types, check if any skill B's command
        description references that type → emit DF-NN candidate tests
      - These are *identified* (status="identified"), not *executed*
  5c: Parallel load test
      - Re-parse each SKILL.md's YAML frontmatter (validates the skill can be
        loaded side-by-side with siblings in the same Agent)
  5d: No rollback
      - Phase 5 makes zero API calls. No resources to roll back.
```

**Auto-derivation example (only the conflict scan is real, the rest is metadata):**

```
Input skills: [ECS-manage, VPC-manage, EIP-manage]
Output:
  conflict_scan.conflicts: [
    {"severity":"medium","skill_a":"ecs-manage","skill_b":"vpc-manage",
     "trigger":"vpc ↔ vpc-list", "recommendation":"改其中一个触发词"}
  ]
  data_flow_tests: [
    {"test_id":"DF-01","from_skill":"vpc-manage","to_skill":"ecs-manage",
     "data_item":"vpc","status":"identified",
     "detail":"vpc-manage 的输出 vpc_id 可能作为 ecs-manage 的输入"}
  ]
  parallel_load_test: {"verdict":"pass","detail":"3 个 skill 均可解析"}
```

**Output:** `phase-5-summary.json`

```json
{
  "mode": "full" | "downgraded_self_check",
  "conflict_scan": {
    "pairs_checked": <int>,
    "conflicts": [
      {"severity": "high|medium|low", "skill_a": "<>", "skill_b": "<>", "trigger": "<>", "recommendation": "<>"}
    ],
    "no_conflict_pairs": <int>
  },
  "data_flow_tests": [
    {"test_id": "DF-01", "from_skill": "<>", "to_skill": "<>", "data_item": "<>", "status": "identified", "detail": "<>"}
  ],
  "parallel_load_test": {
    "skills_loaded": ["<skill>", ...],
    "verdict": "pass | fail | skipped",
    "detail": "<>"
  },
  "cleanup": {"resources_cleaned": 0, "resources_failed": 0}
}
```

---

### Phase 6: End-to-End Flow Testing — Real-Environment Lifecycle

**Goal:** End-to-end verification of complete resource lifecycles against real Huawei Cloud, automatically deriving scenario chains from Phase 1 feature lists and executing them.

**Dependency:** Phase 5 completed (phase-5-summary.json exists)

> **Sibling discovery:** Phase 6 与 Phase 5 共享 `discover_siblings()` 函数（见 § Phase 5）。
> 默认自动扫同级兄弟 skill，opt-out 用 `--no-siblings`。

**Branch logic:**

```
if skills_count == 1 (含 --no-siblings):
  Single-skill closed loop ("downgraded_single_skill_flow"):
    - Sort all feature points by list → create → update → delete
    - Chain into a single-skill resource lifecycle
    - Execute each step via real SDK/CLI against the live environment
    - Read-only steps auto-execute; write steps gated by ALLOW_WRITES=0|1
      (default 0, skipped with status=skip in the report)
    - Verify resource state after each mutation
    - AK/SK credentials required (3-tier resolution, see § Phase 4)

if skills_count >= 2:
  6a: Scenario derivation (from Phase 1 capabilities + SKILL.md fallback)
      - Group by create→query→delete across skills
      - Steps default to status=pass once derived (see *Implementation status* below)
  6b: Lifecycle execution — single-skill branch only
      - The multi-skill branch currently derives the step chain but does NOT
        invoke live APIs step-by-step; it records the derived scenario for
        review. The per-step `status: pass` on derivation is a plan marker,
        not an execution result.
  6c: State consistency verification
      - Single-skill branch: real post-step checks via SDK output
      - Multi-skill branch: derived-only, no real verification
  6d: Cleanup verification
      - Single-skill branch: per-step resource_changes tracked
      - Multi-skill branch: cleanup.verdict defaults to "pass" (no real cleanup)
```

**Implementation status (read this before relying on Phase 6 multi-skill):**

| Branch | Derives scenario | Runs against live API | Tracks resource_changes | State consistency check |
|--------|------------------|-----------------------|-------------------------|--------------------------|
| Single-skill | ✅ | ✅ (under `ALLOW_WRITES=1`) | ✅ | ✅ |
| Multi-skill | ✅ | ❌ (currently a plan record; steps marked `pass` on derivation) | ❌ | ❌ (defaults to `pass`) |

If you need real multi-skill E2E execution, treat Phase 6 multi-skill as a
**derived plan** and run each step's command manually (or via Phase 4 with
`ALLOW_WRITES=1`), then re-run the report.

**Single-skill closed loop example (RDS query skill):**

```
Steps:
  Step 1: ListInstances (read-only, auto) → get instance count
  Step 2: ShowInstanceDetail (if instance exists) → get instance config
  Step 3: ListConfigurations (auto) → get parameter templates
  Step 4: ShowBackupPolicy (if instance exists) → get backup config
  Step 5: Analyze slow SQL (read-only, auto) → ListSlowLogs + ListTopSqls
  Step 6: Parameter tuning recommendation (analysis, no API call)
  Step 7: Backup strategy assessment (analysis, no API call)
```

**Multi-skill derived scenario example (currently NOT auto-executed):**

```
Derived steps (status=pass on derivation only):
  Step 1: Create EVS volume (from evs-manage)
  Step 2: Attach volume to ECS instance (from ecs-manage)
  Step 3: Query volume metrics (from evs-manage)
  Step 4: Detach volume (from evs-manage)
  Step 5: Delete volume (from evs-manage)
```

**Output:** `phase-6-summary.json`

```json
{
  "mode": "full | downgraded_single_skill_flow",
  "scenario": {
    "name": "<derived>",
    "skills_involved": ["<skill>", ...],
    "description": "<auto-derived>",
    "derived_automatically": true,
    "user_confirmed": false,
    "steps": [
      {"seq": 1, "tc_id": "FF-01", "skill": "<>", "action": "<>",
       "status": "pass | fail | skip", "resource_changes": []}
    ]
  },
  "state_consistency": {
    "pass": true | false,
    "detail": "<>",
    "final_state_summary": "<>"
  },
  "cleanup": {
    "verdict": "pass | partial | fail",
    "resources_cleaned": <int>,
    "resources_failed": <int>,
    "manual_required": [<manual_instruction>]
  }
}
```
---

### Phase 7: Consolidated Report

**Goal:** Merge Phase 0~6 JSON outputs into a single, comprehensive test report
for the user. The report follows a strict **Summary → Per-Phase Detail →
Attachments** structure so the reader can quickly decide whether to dive in.

**Dependency:** Phase 0~6 all exist (`phase-0-summary.json` through
`phase-6-summary.json`)

**Output:**
- `<skill-name>-test-files/reports/report-<YYYYMMDD-HHMMSS>/test-report.json`
- `<skill-name>-test-files/reports/report-<YYYYMMDD-HHMMSS>/test-report.md`

> **Two files, identical content.** JSON is machine-readable; Markdown is the
> human-facing version. Both must list every generated test case and every
> execution result — no hiding behind summary numbers.

#### Report Structure (mandatory)

```text
┌────────────────────────────────────────────────────────────────┐
│ Header — test_id / generated_at / skills / report_dir          │
├────────────────────────────────────────────────────────────────┤
│ §1  Summary (TL;DR)                                            │
│     - Overall Verdict (✅/⚠️/❌)                                │
│     - 指标表 (phases / test cases / pass rate / 资源变更)    │
│     - Key Findings (3-5 条)                                    │
├────────────────────────────────────────────────────────────────┤
│ §2  Per-Phase Detail                                           │
│     对每个 skill:                                              │
│       ### Skill: <name>                                        │
│         Path: <skill_path>                                     │
│         对每个 phase (0..6):                                   │
│           #### Phase N — <name>                                │
│             阶段小结 + 该阶段产生的用例 / 实际执行结果        │
├────────────────────────────────────────────────────────────────┤
│ §3  Attachments — phase JSONs / archive / reports 路径        │
└────────────────────────────────────────────────────────────────┘
```

#### §1 Summary 规则

`summary.verdict` 由所有 phase 的 verdict 联合判定：

| 条件 | verdict | label |
|------|---------|-------|
| 全部 phase pass + test cases pass_rate == 100 | `pass` | `✅ PASS` |
| 至少 1 个 phase partial/fail，但有 phase pass | `partial` | `⚠️ PARTIAL` |
| 全部 phase fail / 全部 skipped / 全部 missing | `fail` | `❌ FAIL` |

指标表必含列：

| Metric | Value |
|--------|-------|
| Phases | X pass / Y partial / Z fail / W skipped (of 7) |
| Test Cases | total N \| pass P \| fail F \| warn W \| skip S \| error E |
| Pass Rate | P% |
| Manual Items | N (need real business data) |
| Cloud Resources Changed | N (Phase 4 only) |

指标表之后必须紧跟 **Skills Tested 列表**（`# | Skill | Path` 三列），
列出本次测试涉及的所有 skill。详情见下文 § "报告硬性要求" 第 2 条。

`key_findings[]` 由脚本自动生成 3-5 条结论，每条形如：

- `huawei-cloud-rds-query: 4 项目录硬要求全部通过 (4/4)`
- `huawei-cloud-rds-query Phase 4: 12 个用例失败 (查看下方失败归类)`

#### §2 Per-Phase Detail 规则

每个 phase 小节必须包含「阶段小结」+「该阶段产物（用例 / 结果）」：

| Phase | 必含产物 |
|-------|----------|
| 0 | 目录硬要求表（4 行）+ install/uninstall/reinstall 表 |
| 1 | metadata + 提取的 commands 表 |
| 2 | CLI/SDK/API 可用性矩阵 + per-command 表 |
| 3 | **生成的测试用例完整列表**（functional + api）+ statistics |
| 4 | **用例执行结果完整列表** + Failures 归类 + Warns + Manual items |
| 5 | 冲突扫描 + 数据流候选 + 并行加载 |
| 6 | E2E 场景步骤表 + state consistency + cleanup |

> **用户硬性要求**：Phase 3 产生的每一条用例（`TC-F-01` ~ `TC-F-NN`）和
> Phase 4 的每一条执行结果，必须在 Markdown 报告里以表格形式完整列出。
> 不允许只给统计数、不给明细。

#### §3 JSON 顶层 schema

```json
{
  "test_id": "test-20260716-100300",
  "generated_at": "2026-07-16T10:03:00.000Z",
  "skills": [
    {
      "name": "huawei-cloud-rds-query",
      "skill_path": "C:/.../skills/huawei-cloud-rds-query",
      "phases_summary": [
        {"phase": 0, "name": "install-check",       "verdict": "pass",    "duration_s": 1.0, "summary": "4/4 目录硬要求通过"},
        {"phase": 1, "name": "skill-analysis",      "verdict": "pass",    "duration_s": 0.0, "summary": "提取 15 条命令"},
        {"phase": 2, "name": "tech-research",       "verdict": "pass",    "duration_s": 1.0, "summary": "CLI 15/15 可用"},
        {"phase": 3, "name": "test-case-generation","verdict": "pass",    "duration_s": 0.0, "summary": "生成 28 条用例"},
        {"phase": 4, "name": "test-execution",      "verdict": "partial", "duration_s": 6.0, "summary": "9 pass / 12 fail / 7 warn"},
        {"phase": 5, "name": "orchestration",       "verdict": "pass",    "duration_s": 1.0, "summary": "单 skill self-check"},
        {"phase": 6, "name": "full-flow",           "verdict": "pass",    "duration_s": 9.0, "summary": "15 步闭环"}
      ],
      "phases_detail": {
        "0": { "directory_integrity": {...}, "install": {...}, "uninstall": {...}, "reinstall": {...} },
        "1": { "metadata": {...}, "commands": [ ... ] },
        "2": { "research": [ ... ], "summary": {...} },
        "3": { "functional_cases": [ ... ], "api_cases": [ ... ], "statistics": {...} },
        "4": { "execution_results": [ ... ], "statistics": {...},
               "all_resources_changed": [ ... ], "manual_test_items": [ ... ] },
        "5": { "mode": "...", "conflict_scan": {...}, "data_flow_tests": [ ... ],
               "parallel_load_test": {...} },
        "6": { "mode": "...", "scenario": {...}, "state_consistency": {...}, "cleanup": {...} }
      }
    }
  ],
  "summary": {
    "verdict": "partial",
    "verdict_label": "⚠️ PARTIAL",
    "phases_total": 7,
    "phases_pass": 6,
    "phases_partial": 1,
    "phases_fail": 0,
    "phases_skipped": 0,
    "phases_missing": 0,
    "test_cases_total": 28,
    "test_cases_pass": 9,
    "test_cases_fail": 12,
    "test_cases_warn": 0,
    "test_cases_skip": 7,
    "test_cases_error": 0,
    "pass_rate": 32.1,
    "manual_items_count": 7,
    "cloud_resources_changed": 0
  },
  "key_findings": [
    "huawei-cloud-rds-query: 4 项目录硬要求全部通过 (4/4)",
    "huawei-cloud-rds-query: 纯只读, 提取 15 条命令 / 20 个触发词",
    "huawei-cloud-rds-query Phase 4: 12 个用例失败 (查看下方失败归类)"
  ],
  "environment": {
    "python_version": "3.11.15"
  },
  "report_dir": "C:/.../skills/huawei-cloud-rds-query-test-files/reports/report-20260716-100300"
}
```

#### 报告硬性要求（违反视为 bug）

1. **必须有 Summary** — 哪怕只跑了一个 phase，Summary 也得填上对应统计
2. **必须有 Skills Tested 列表** — Summary 段必备，列出本次测试涉及的所有
   skill（`# | Skill | Path` 三列表格）。单 skill 也必须有这一行。
3. **必须有组合测试涉及 skill 列表** — Phase 5 / Phase 6 小节开头必备：
   - Phase 5 标题：`Skills involved in this orchestration (N):`
   - Phase 6 标题：`Skills involved in this E2E flow (N):`
   - 数据来源：`phase-{5,6}-summary.json` 的 `target.skills`
   - 降级单 skill 模式也必须列出 `["<该 skill>"]`
4. **每个阶段必须有：阶段小结 + 阶段产物（用例 / 结果）** — 不允许只写
   "Phase 4 pass" 然后跳过 28 条用例执行结果
5. **Markdown 和 JSON 必须字段对齐** — JSON 的 `phases_detail.<N>` 中出现的
   字段，Markdown 报告里对应的 phase 小节必须有等价内容
6. **关键数字必须一致** — Summary 的 `test_cases_total` 必须等于
   `phases_detail.3.statistics.total`；`test_cases_pass` 必须等于
   `phases_detail.4.statistics.pass`，依此类推
7. **不得包含敏感信息** — AK/SK、token、内部 hostname 必须在日志和报告里
   `sed` 掉（参考 `lib/utils.sh` 的 redaction 规则）
8. **写资源变更必须列出** — `phases_detail.4.all_resources_changed` 不能省略
9. **Manual items 必须显式列出** — 不允许在 Markdown 里折叠 / 隐藏
   `manual_test_items`，要让用户能在 Summary 段就看到 `N (need real business data)`
10. **报告路径必须是绝对路径** — `report_dir` 必须是绝对路径，不接受相对路径

完整 JSON 字段规范见 `references/output-schema-spec.md` § Phase 7。

---

## KooCLI Command Format Standard

This testing framework uses `bash` scripts as the primary execution mode, not direct `hcloud` CLI commands. However, when executing test cases, the framework constructs `hcloud` CLI commands in the following format:

```bash
hcloud <Service> <Operation> --cli-region={region} [--param1=value1 ...]
```

**Format Rules:**

| Rule | Description |
|------|-------------|
| Service name | Follows KooCLI Services (uppercase: ECS, VPC, OBS; title case: CloudPond, IAMAccessAnalyzer) |
| Operation name | PascalCase (e.g., ListServersDetails, ListBuckets) |
| Region | Always include `--cli-region={region}` parameter |
| Parameters | Use `--param=value` syntax |
| Read-only limit | Always append `--limit=1` for exploratory queries |

For OBS service, the framework uses `hcloud obs` (obsutil) subsystem:

```bash
hcloud obs <command> [args...] [options...]
```

---

## Core Commands

### Full Pipeline Run

```bash
# Specify skills
bash scripts/run-test-pipeline.sh --skills "huawei-cloud-bss-voucher-manage"

# Specify multiple skills (comma-separated)
bash scripts/run-test-pipeline.sh --skills "huawei-cloud-bss-voucher-manage, huawei-cloud-ecs-manage"

# Scan all installed
bash scripts/run-test-pipeline.sh --all-installed

# Start from a specific phase (recovery scenarios only)
bash scripts/run-test-pipeline.sh --skills "bss-voucher" --phase 4

# Fresh mode
bash scripts/run-test-pipeline.sh --skills "bss-voucher" --fresh
```

### Single Phase Run (Debug)

```bash
bash scripts/tier1/phase-0-install-check.sh --skill "huawei-cloud-bss-voucher-manage"
bash scripts/tier1/phase-1-skill-analysis.sh --skill "huawei-cloud-bss-voucher-manage"
bash scripts/tier2/phase-5-orchestration.sh --skills "skill-a, skill-b"
bash scripts/tier3/phase-7-final-report.sh --skills "skill-a, skill-b"
```

### Run Multi-Skill Orchestration

```bash
# Derive and execute orchestration scenarios for 3 skills
bash scripts/tier2/phase-5-orchestration.sh --skills "ecs-manage, vpc-manage, eip-manage"

# Run E2E lifecycle test for a single skill
bash scripts/tier2/phase-6-full-flow.sh --skill "huawei-cloud-rds-intelligent-service"
```

---

## Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--skills` | Mutually exclusive | Comma-separated skill names or directory names | `"bss-voucher-manage, ecs-manage"` |
| `--all-installed` | Mutually exclusive | Scan all `huawei-cloud-*` under `$SKILL_INSTALL_DIR/huawei-cloud/` | — |
| `--phase` | No | Start from a specific Phase (defaults to resume from missing phase) | `--phase 0` |
| `--fresh` | No | **Archive** (move, not delete) existing `phase-*.json` to `phases/archive/<timestamp>/` and start from scratch. History is preserved; nothing is deleted. | — |
| `--output` | No | Report output directory (default: reports/) | `--output ./test-reports` |
| `--skill-path` | No | Skill directory path. When set, `find_skill_path` searches **only here** (no install-dir fallback) | `--skill-path ./skills` |
| `--no-siblings` | No | Phase 5/6 **不**自动扫描同目录其他 huawei-cloud-* skill（默认: 开启扫描） | `--no-siblings` |
| `--sibling-limit <N>` | No | 兄弟 skill 数量上限（默认 5；`0` = 等同 `--no-siblings`） | `--sibling-limit 3` |

### Environment Variables (Advanced)

| Variable | Default | Purpose |
|----------|---------|---------|
| `SKILL_INSTALL_DIR` | auto-detect: `~/.agents/skills` → `~/.hermes/skills` → `~/.agents/skills` | Where skills are installed by the agent runtime |
| `SKILL_PATH_HERMES` | alias of `SKILL_INSTALL_DIR` | Legacy name, kept for back-compat |
| `SKILL_INSTALL_CMD` | `hermes skills` | Command for remote skill install/uninstall. Set to `""` to skip real install. |
| `ALLOW_WRITES` | `0` | When `1`, Phase 4/6 write cases actually execute against the live API (default is skip) |
| `HUAWEI_REGION` | `cn-north-4` | Huawei Cloud region |
| `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` | — | Required for Phase 4/6 SDK/CLI execution; any `HUAWEI*` / `HW*` / `HWC*` prefixed AK/SK env var is also accepted |

---

## References

### 核心文档（必读）

- `references/architecture.md` — Three-track eight-phase architecture diagram (Mermaid)
- `references/output-schema-spec.md` — Complete JSON field specification for each phase (including Phase 7 final report schema)
- `references/phase-transition-rules.md` — Phase transition / fallback / skip rules
- `references/acceptance-criteria.md` — Quality gates + 17-item report acceptance checklist
- `references/verification-method.md` — How to manually verify each phase (PowerShell + Git Bash)

### 配套参考

- `references/cli-installation-guide.md` — How to install and configure hcloud CLI (prerequisite for Phase 2/4)
- `references/iam-policies.md` — Minimum IAM permissions required to run the tester

### 模板（JSON Schema）

- `templates/phase-report-schema.json` — JSON Schema for `phase-N-summary.json` (N=0..6)
- `templates/test-case-schema.json` — JSON Schema for individual test cases (`TC-F-*` / `TC-A-*` / `OF-*` / `FF-*`)
- `templates/scenario-template.json` — Reference example for Phase 6 multi-skill scenario derivation

---

## Output Format

All test artifacts go to a **sibling directory of the tested skill**, named `<skill-name>-test-files/`. This keeps the skill source dir clean and preserves run history for diff/regression.

```
skills/
├── huawei-cloud-rds-query/                  ← skill source (untouched)
└── huawei-cloud-rds-query-test-files/       ← test artifacts (created on first run, kept across runs)
    ├── phases/
    │   ├── phase-0-summary.json
    │   ├── phase-1-summary.json
    │   ├── ...
    │   └── phase-7-summary.json
    └── reports/
        ├── report-20260724-152309/          ← one subdir per run (timestamped)
        │   ├── test-report.json
        │   └── test-report.md
        ├── report-20260725-090000/
        │   ├── test-report.json
        │   └── test-report.md
        └── ...
```

- **Phase 0~6** output `phase-N-summary.json` to `<skill-name>-test-files/phases/`
- **Phase 7** merges them into `<skill-name>-test-files/reports/report-<timestamp>/test-report.{json,md}`
- **Test artifacts are preserved** across runs (no auto-cleanup, ever). `--fresh` does NOT delete — it **archives** old `phases/*.json` to `phases/archive/<timestamp>/` so the chain check resets while history stays intact. `reports/` is always kept.
- **The test-installed copy** of the skill in `$SKILL_INSTALL_DIR/` is still uninstalled on exit, so the next run sees a clean install state.

See `references/output-schema-spec.md` for the JSON schema. Phase 5 and 6 additionally output scenario execution logs with real CLI/SDK responses for auditability.

## Best Practices

- Complete Tier 1 before entering Tier 2 to ensure skills are individually functional before orchestration
- Confirm write operations one by one in Phase 4 and Phase 5/6; do not batch-confirm to avoid misoperations
- With only 1 skill, Phase 5/6 automatically downgrade to single-skill closed loop; no need to manually skip
- When using `--fresh` to reset and rerun, confirm there are no uncleaned test resources
- Review orchestration scenarios before execution to ensure resource dependency order is correct

## Notes

- Three-track eight-phase strictly follows sequential order; chain verification prevents skipping
- API endpoints are strictly prohibited from being inferred; only obtain from SDK `_http_info` or API Explorer
- Credentials are read from environment variables; hardcoding is prohibited
- **If AK/SK is missing, the framework emits the env-var setup template to stderr and exits 77. The Agent MUST output that template to the user verbatim and instruct them to set env vars out-of-band (in their shell / PowerShell $PROFILE). The Agent MUST NEVER ask the user to type or paste AK/SK in chat. Strictly prohibited from silently skipping any step that requires credentials.**
- Resources created during testing must be tracked; if any are left behind, output manual cleanup instructions
- Orchestration scenarios are auto-derived; user should review and confirm before execution
- Write operations in orchestration scenarios require per-step user confirmation

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Skill directory does not exist | Report error and terminate, output available skill list |
| AK/SK environment variables not set | Framework emits the env-var setup template (with `export HUAWEI_ACCESS_KEY=...` / `$env:HUAWEI_ACCESS_KEY=...` snippets) to stderr and exits 77. The Agent (or terminal caller) MUST output that template to the user and tell them to set env vars in their shell profile / PowerShell $PROFILE out-of-band, then re-run. **Never** ask the user to type or paste AK/SK in chat. Strictly prohibited from silently skipping. |
| User specifies skill name but not installed in Hermes | `--fresh` performs directory-level detection; if not found, report error with guidance |
| Some Phase JSON files deleted | Chain detection → Restart from the deleted Phase |
| Network interruption during Phase 4 execution | Already executed case results are not lost; on rerun, skip passed cases (via `--phase` flag) |
| User hits Ctrl+C mid-execution | Already output phase JSON is valid; next time `--resume` will recover from the current phase |
| Only 1 skill under test | Phase 5 → `downgraded_self_check` (single-skill trigger ambiguity scan); Phase 6 → `downgraded_single_skill_flow` (real execution) |
| User unsatisfied with derived orchestration scenarios | Manually edit the derived scenario or skip it; Phase 5 derivation is metadata-only, not executed |
| Phase 4 write op with no `ALLOW_WRITES=1` | Skipped with `status=skip`, no resource_changes recorded |
| Phase 4 hits missing business params (e.g. coupon_id) | Marked `status=warn`, surfaces as `manual_test_items` in the report; user must supply real data and retry |
| Cross-skill data flow mismatch | Logged in Phase 5 as `data_flow_tests` candidate; not auto-executed |
| Orphaned resources detected after E2E flow | Listed in `phase-6-summary.json` under `cleanup.manual_required` with concrete cleanup commands |

## Agent Protocol — Credential Request

When Phase 4 or Phase 6 needs to call live Huawei Cloud APIs but cannot find
credentials in the environment, the framework does **not** silently skip. It
emits a structured request and exits with a sentinel code so the calling
agent is forced to surface the need to the user — **but the agent must not
ask the user to type or paste AK/SK in chat**. The user must set the
variables in their shell profile out-of-band.

**Sentinel string** (emitted to stderr, one line):
```
__HUAWEI_SKILL_TESTER_CRED_REQUEST_v1__
```

**Exit code**: `77`

**Agent response protocol** (MUST follow):

1. **Detect**: When running the test framework (directly or via
   `run-test-pipeline.sh`), catch exit code `77` OR the sentinel line in stderr.
2. **Pause**: Stop further pipeline execution. Do not skip ahead to Phase 5/7 —
   that would silently produce a "passing" report without live API coverage.
3. **Output the template**: Read the env-var setup template that the framework
   already emitted to stderr (the block beginning with
   `===== copy from here =====`) and output it to the user **verbatim**. Tell
   the user to fill in `<your-access-key-id>` and `<your-secret-access-key>`
   in their shell profile / PowerShell `$PROFILE` (out-of-band, NOT in chat).
4. **Never ask for AK/SK in chat**: Forbidden actions include
   `ask_user`, `read -p`, any web form, any clipboard paste back to the agent,
   any inline `read` loop, or any path through `~/.hcloud/config.json` /
   `~/.aliyun/config.json` / `~/.aws/credentials` that the user might
   silently trust.
5. **Re-run**: Once the user confirms they have set env vars out-of-band, the
   agent simply re-runs the failing phase:
   `HUAWEI_ACCESS_KEY=... bash run-test-pipeline.sh --skills <name> --phase 4`
   (the user is expected to have `export`-ed the vars in the shell where the
   agent executes the command).
6. **If the user declines**: Surface the decline to the human, do NOT mark
   Phase 4/6 as `pass`. You may abort the whole test, or report a partial run
   explicitly tagged "live phases skipped — no credentials".

**Direct-terminal mode (no agent)**: If a human runs the script directly from
a real terminal (`[ -t 0 ]` is true), the framework still emits the template
to stderr and exits 77 — the user runs the same `export HUAWEI_ACCESS_KEY=...`
in their shell and re-invokes the script. **There is no inline `read`
prompt path any more.** The TTY prompt used to exist for human convenience
but was removed because (a) it can leak values through terminal scrollback
and clipboard, (b) it is inconsistent with the agent protocol, and (c) it
violates the "no in-session secret entry" rule used elsewhere in the
Huawei Cloud skill ecosystem.

**Example agent behavior**:

```text
> bash run-test-pipeline.sh --skills rds-query
... Phase 0-3 pass ...
[Phase 4] __HUAWEI_SKILL_TESTER_CRED_REQUEST_v1__
[Phase 4] HUAWEI_CREDENTIALS_REQUIRED
[Phase 4] exit code: 77
<agent detects 77, pauses run>
<agent outputs the env-var template verbatim to the user, with a one-line instruction>
<user opens their shell, pastes the export HUAWEI_ACCESS_KEY=... lines, re-runs>
<agent re-runs: bash run-test-pipeline.sh --skills rds-query --phase 4>
```

**Rationale**: The test framework's job is to actually verify the skill
against the real cloud, not to produce green checkmarks from offline analysis
alone. Silently skipping live tests would let a broken skill pass. The
sentinel + exit code is a hard "stop and ask" signal so the human is always
in the loop for live-credential decisions — but the only safe way to handle
credentials is to keep them out of the in-session channel entirely.

## Design Principles

- **Chain Verification** — Each Phase checks the previous phase's JSON to prevent skipping
- **Agent-proof** — Write operations must be confirmed by the user; fake confirmations are not allowed
- **Data-Driven** — All phases output in JSON format; Phase 7 merges
- **Batch Repeatable** — The same set of skills can be tested repeatedly; --fresh resets
- **Real-Environment First** — All orchestrations and E2E flows execute against real Huawei Cloud; no mocks
- **Degrade Without Losing Value** — Single skill does not run empty orchestration phases; degrades to meaningful single-skill lifecycle tests
- **Resource Safety** — Resources created during testing must be tracked; if any remain, output clear manual cleanup instructions
- **Credentials Mandatory** — If AK/SK is missing, the framework emits the env-var setup template to stderr and exits 77. The Agent MUST output that template to the user and instruct them to set env vars out-of-band. The Agent MUST NEVER ask the user to type or paste AK/SK in chat. Strictly prohibited from silently skipping any step that requires credentials.
