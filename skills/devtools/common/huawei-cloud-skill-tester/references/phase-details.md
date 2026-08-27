# Phase Details — 三轨八节各阶段详细规范

> 本文件由 SKILL.md 拆分而来(行数精简), 内容为各 Phase 的完整实现规范。
> SKILL.md 的 Workflow 节只保留摘要, 详细步骤以本文件为准。

### Phase 0: Installation Verification

**Goal:** Verify whether the skill can be installed/uninstalled/reinstalled normally, and confirm the directory structure meets the contract.

**Steps:**

1. Check skill directory structure — **three items are hard contract** (missing any one fails the phase); `scripts/` is **soft** (纯 CLI skill 无 scripts/ 目录是合法结构, 不判 fail, 仅跳过脚本相关校验):
   - `SKILL.md` (hard)
   - `references/` (hard)
   - `references/iam-policies.md` (hard)
   - `scripts/` (soft — 纯 CLI skill 可缺失)
2. Confirm whether the runtime has the skill installed (check if a directory with the same name exists under `$SKILL_INSTALL_DIR/`)
3. Perform installation verification (simulated or actual installation)
4. Perform uninstallation verification (simulated or actual uninstallation)
5. Perform reinstallation verification (install → uninstall → install)
6. Record installation duration, directory integrity, and installation status

```bash
# Directory integrity check (three hard + scripts/ soft)
[ -f "${skill_path}/SKILL.md" ] && echo "SKILL.md exists"
[ -d "${skill_path}/scripts" ] && echo "scripts/ exists" || echo "scripts/ missing (pure CLI skill OK)"
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

**Goal:** Generate test cases based on Phase 1+2 (positive + boundary + negative), present them to the user for confirmation.

**Dependency:** Phase 1+2 completed (phase-1-summary.json + phase-2-summary.json exist)

**Functional case division rules:**

| Operation Type | Case Requirements | Risk Level |
|---------------|-------------------|------------|
| Query (List/Show/Get) | 1 positive + 1 boundary (limit=1) | low |
| Create | 1 standard + 1 parameter variant | high |
| Update | 1 verification that modification took effect | medium |
| Delete | 1 pre-deletion confirmation + 1 post-deletion verification | high |
| Statistics (count/aggregate) | 1 positive + 1 time range boundary | low |
| CLI 命令(所有) | **+1 negative(未知参数变体)**: 在命令后追加 `--invalid-flag-xyz`, 验证 CLI 是否拒绝未知参数并给出错误提示(报错质量检查) | low |

> 负向用例判定(Phase 4): 非零退出码 + 错误提示 → pass(CLI 正确拒绝); 静默接受(rc=0 无报错) → fail(报错质量差)。帮助/配置类命令(`hcloud version/configure/--help` 等)不生成负向用例。
> 边界用例: `make_boundary_cmd` 对 hcloud 命令追加 `--limit=1`(多数 API 拒绝 limit=0), 对 `version/--version/help/configure` 等无参命令不追加。

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
  - *skill-tester*, *skill-creator*, *new-tester* (meta skills, pattern match)
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

