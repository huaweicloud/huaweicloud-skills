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
3. **Huawei Cloud AK/SK** — 自动扫描所有以 `HUAWEI` / `HW` / `HWC` 开头的环境变量（键名含 AK/SK 标记的键值对）。**If missing, the framework emits the env-var setup template to stderr and exits 77. NEVER ask the user to type AK/SK in chat; user must set env vars in their shell profile out-of-band and re-run.**（完整协议见 `references/agent-protocol.md`）
4. **Target Skill** must be under `$SKILL_INSTALL_DIR/` (auto-detected: `~/.agents/skills/` → `~/.hermes/skills/` → default) or a user-specified path
5. **jq** command (all JSON processing depends on it)
6. **API Reference**: https://console.huaweicloud.com/apiexplorer/#/openapi

---

## Workflow — Three-Track Eight-Phase

```
Tier 1: Single-Skill Unit Testing
   Phase 0: Installation Verification (install/uninstall/reinstall)
   Phase 1: Feature Extraction (metadata + commands + resource types + doc checks)
   Phase 2: Technical Research (CLI→SDK→API three-level availability)
   Phase 3: Test Case Generation (functional TC-F + boundary + negative + API TC-A)
   Phase 4: Real-Environment Execution (read-only automatic + write ops require confirmation)

Tier 2: Integration Testing — Real-Environment Orchestration
   Phase 5: Multi-Skill Orchestration (conflict scan / scenario derivation / self-check)
   Phase 6: End-to-End Flow (resource lifecycle: create→query→update→delete)

Tier 3: Final Report
   Phase 7: Consolidated Report (merge phase-0~6 JSON, verdict + issues + reasons)
```

> 各 Phase 的完整实现规范（步骤、判定标准、JSON 字段）见 `references/phase-details.md`。

---

## Phases at a Glance

| Phase | 名称 | 核心要点 | 判定 |
|-------|------|---------|------|
| 0 | 安装验证 | 目录完整性(SKILL.md + references/ + iam-policies.md 硬性, scripts/ 软性兼容纯 CLI skill); install/uninstall/reinstall(同路径/符号链接防护) | 目录四件套 + 生命周期 |
| 1 | 功能提取 | metadata/triggers/commands/capabilities/resource_types + doc_checks(引用一致性、禁用文件 .bak/.template) | 命令与触发词非空 |
| 2 | 技术调研 | CLI→SDK→API 三级可用性; 纯本地工具自动标记 not_applicable | 按可用性计数 |
| 3 | 用例生成 | 正向 + 边界(limit=1) + 负向(未知参数)用例; 占位符替换(/path/to、./xxx、{region}); 模板/交互命令过滤 | 用例数 > 0 |
| 4 | 执行 | 自动执行 + 输出质量判定(rc=0 空输出→warn); 负向用例报错质量; 文档缺口分析(doc_gap_issues); 依赖缺失标注 | pass/fail/warn/skip |
| 5 | 编排 | 多 skill: 触发词冲突扫描 + 数据流候选; 单 skill: 降级自检(内部歧义 + 写操作排序) | conflict scan |
| 6 | 全流程 | 多 skill: 场景派生; 单 skill: 降级完整功能闭环(create→query→update→delete) | scenario steps |
| 7 | 报告 | 合并 phase-0~6; verdict + pass_rate + issues_found + 各 phase reason; test-report.json/md | 汇总判定 |

> 详细步骤、链式验证规则、JSON schema 见 `references/phase-details.md` 与 `references/output-schema-spec.md`。

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
- `references/phase-details.md` — 各 Phase 完整实现规范（步骤、判定标准、JSON 字段）
- `references/agent-protocol.md` — 凭证请求协议（AK/SK 缺失时的完整处理流程）

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
- **If AK/SK is missing, the framework emits the env-var setup template to stderr and exits 77. The Agent MUST output that template to the user verbatim and instruct them to set env vars out-of-band (in their shell / PowerShell $PROFILE). The Agent MUST NEVER ask the user to type or paste AK/SK in chat. Strictly prohibited from silently skipping any step that requires credentials.**（完整协议见 `references/agent-protocol.md`）
- Resources created during testing must be tracked; if any are left behind, output manual cleanup instructions
- Orchestration scenarios are auto-derived; user should review and confirm before execution
- Write operations in orchestration scenarios require per-step user confirmation

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Skill directory does not exist | Report error and terminate, output available skill list |
| AK/SK environment variables not set | Framework emits the env-var setup template (with `export HUAWEI_ACCESS_KEY=<your-access-key>` / `$env:HUAWEI_ACCESS_KEY=<your-access-key>` placeholder snippets) to stderr and exits 77. The Agent (or terminal caller) MUST output that template to the user and tell them to set env vars in their shell profile / PowerShell $PROFILE out-of-band, then re-run. **Never** ask the user to type or paste AK/SK in chat. Strictly prohibited from silently skipping. |
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

When Phase 4 or Phase 6 needs to call live Huawei Cloud APIs but cannot find credentials in the environment, the framework does **not** silently skip. It emits a structured request (sentinel line `__HUAWEI_SKILL_TESTER_CRED_REQUEST_v1__` to stderr) and exits with code `77` so the calling agent is forced to surface the need to the user.

**核心规则（MUST follow）:**
1. 检测到 exit 77 或 sentinel → 暂停流水线,不得跳过 Phase 5/7
2. 将 stderr 中的 env-var 设置模板**原样**输出给用户,引导用户在 shell profile / PowerShell $PROFILE 中带外配置(占位符 `<your-access-key-id>` / `<your-secret-access-key>`)
3. **禁止**在对话中索要 AK/SK 明文(ask_user / read -p / 剪贴板回传 / 读取 ~/.hcloud/config.json 等路径)
4. 用户带外设置后,重跑失败 phase;用户拒绝则明确标记"live phases skipped — no credentials",不得标记 pass

> 完整协议(6 步响应流程、直接终端模式、示例行为)见 `references/agent-protocol.md`。

## Design Principles

- **Chain Verification** — Each Phase checks the previous phase's JSON to prevent skipping
- **Agent-proof** — Write operations must be confirmed by the user; fake confirmations are not allowed
- **Data-Driven** — All phases output in JSON format; Phase 7 merges
- **Batch Repeatable** — The same set of skills can be tested repeatedly; --fresh resets
- **Real-Environment First** — All orchestrations and E2E flows execute against real Huawei Cloud; no mocks
- **Degrade Without Losing Value** — Single skill does not run empty orchestration phases; degrades to meaningful single-skill lifecycle tests
- **Resource Safety** — Resources created during testing must be tracked; if any remain, output clear manual cleanup instructions
- **Credentials Mandatory** — If AK/SK is missing, the framework emits the env-var setup template to stderr and exits 77. The Agent MUST output that template to the user and instruct them to set env vars out-of-band. The Agent MUST NEVER ask the user to type or paste AK/SK in chat. Strictly prohibited from silently skipping any step that requires credentials.
