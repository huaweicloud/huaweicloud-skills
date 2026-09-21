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
(three-tier layout × 8 phases total: Phase 0-6 execution + Phase 7 final report):

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
5. **Fallback Strategy** — When only 1 skill, Phase 5/6 automatically downgrade to single-skill lifecycle testing. **Sibling auto-scan is ON by default** (Phase 5/6 automatically looks for other `huawei-cloud-*` skills in the same directory as the skill under test to run orchestration combos). Use `--no-siblings` to opt-out.
6. **Standardized JSON Output** — All phases output in a unified schema; Phase 7 merges into a single report
7. **Real-Environment First** — Tier 2 phases run against real Huawei Cloud where applicable (write operations gated by `ALLOW_WRITES`); multi-skill Phase 6 currently derives a scenario plan without real execution, while single-skill Phase 6 runs a real create→query→update→delete loop. No mocks or simulations.

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

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli` (installed by `scripts/ensure_cli.sh` if absent).

## Prerequisites

1. **hcloud CLI** installed and authenticated (for Tier 2 CLI mode testing) — Reference: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
2. **Python 3.8+** + `huaweicloudsdk` packages (for SDK mode testing) — SDK Reference: https://console.huaweicloud.com/apiexplorer/#/sdkcenter
3. **Huawei Cloud AK/SK** — auto-scans all environment variables prefixed `HUAWEI` / `HW` / `HWC` (key-value pairs whose keys carry AK/SK markers). **If missing, the framework emits the env-var setup template to stderr and exits 77. NEVER ask the user to type AK/SK in chat; the user must set env vars in their shell profile out-of-band and re-run.** (full protocol: `references/agent-protocol.md`).
4. **Target Skill** must be under `$SKILL_INSTALL_DIR/` (auto-detected: `~/.agents/skills/` → `~/.hermes/skills/` → default) or a user-specified path
5. **jq** command (all JSON processing depends on it)
6. **API Reference**: https://console.huaweicloud.com/apiexplorer/#/openapi

---
- **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent, skips if present)
  - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
  - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`
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

> Full per-phase implementation specs (steps, pass criteria, JSON fields) are in `references/phase-details.md`.

---

## Phases at a Glance

| Phase | Name | Key Points | Verdict |
|-------|------|---------|------|
| 0 | Install verification | Directory completeness: mandatory trio (SKILL.md, references folder, iam-policies doc) plus a soft-required scripts folder (pure-CLI skills may lack it; reported but not blocking); install/uninstall/reinstall (same-path / symlink protection) | Directory trio + lifecycle (scripts folder soft-required) |
| 1 | Feature extraction | metadata/triggers/commands/capabilities/resource_types + doc_checks (reference consistency, forbidden .bak/.template files) | Commands and triggers non-empty |
| 2 | Technical research | CLI→SDK→API three-level availability; pure-local tools auto-marked not_applicable | Availability count |
| 3 | Test case generation | Positive + boundary (limit=1) + negative (unknown param) cases; placeholder replacement (/path/to, ./xxx, {region}); template/interactive command filtering | Cases > 0 |
| 4 | Execution | Auto execution + output quality verdict (rc=0 empty output → warn); negative-case error quality; doc-gap analysis (doc_gap_issues); missing-dependency marking | pass/fail/warn/skip |
| 5 | Orchestration | Multi-skill: trigger-conflict scan + data-flow candidates; single skill: downgraded self-check (internal ambiguity + write-op ordering) | conflict scan |
| 6 | Full flow | Multi-skill: scenario derivation; single skill: downgraded full functional loop (create→query→update→delete) | scenario steps |
| 7 | Report | Merge phase-0~6; verdict + pass_rate + issues_found + per-phase reason; test-report.json/md | Aggregated verdict |

> Detailed steps, chain-verification rules, and JSON schemas: `references/phase-details.md` and `references/output-schema-spec.md`.

---

## KooCLI Command Format Standard

This testing framework uses `bash` scripts as the primary execution mode; it does **NOT** execute raw
`hcloud` CLI commands directly. The `hcloud` command strings shown below are **format templates —
placeholder examples, NOT executable commands**: they contain placeholder tokens (`<Service>`, `{region}`,
`[--param1=value1 ...]`, etc.) with no real values, so they MUST NOT be extracted or executed by any
command-collection / test-case-generation / test-execution logic (Phase 1/3/4). Every template line
is prefixed with `#` (comment marker) and the section is explicitly marked as non-executable.

> **Executable Command List:** the only real executable commands of this skill are the pipeline scripts under the `scripts` directory,
> invoked via `bash scripts/...` (e.g. `bash scripts/run-test-pipeline.sh --skills <name>`, 
> `bash scripts/tier1/phase-0-install-check.sh --skill <name>`, etc. — see Core Commands below).
> All `hcloud ...` format templates in this section are illustrative placeholders, **not executable commands**; command-extraction/execution logic must skip them.

# Format-template placeholder examples — for reading the format only; never extract or execute as commands (# comment lines, contain <Service>/{region} placeholders)
# hcloud <Service> <Operation> --cli-region={region} [--param1=value1 ...]
```

**Format Rules:**

- **Service name** — Follows KooCLI Services (uppercase: ECS, VPC, OBS; title case: CloudPond, IAMAccessAnalyzer)
- **Operation name** — PascalCase (e.g., ListServersDetails, ListBuckets)
- **Region** — Always include the `--cli-region` parameter with a real region value (e.g. `cn-north-4`). The token form `--cli-region={region}` is a template placeholder, never a real command.
- **Parameters** — Parameters use the `--name=value` syntax; the token `--param=value` is a format illustration only, never a real command.
- **Read-only limit** — Always append `--limit=1` for exploratory queries (real flag value, only meaningful inside an actual `hcloud` command).

For OBS service, the framework uses `hcloud obs` (obsutil) subsystem:

```bash
> **⚠️ Mandatory: every `hcloud` command in this skill MUST be wrapped with `skill-quality-cli run --skill-name huawei-cloud-skill-tester -- ` — bare `hcloud` calls are strictly forbidden.**

# OBS format-template placeholder examples — for reading the format only; never extract or execute (# comment lines, contain <command>/[args...] placeholders)
# hcloud obs <command> [args...] [options...]
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

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--skills` | Mutually exclusive | Comma-separated skill names or directory names | `"bss-voucher-manage, ecs-manage"` |
| `--all-installed` | Mutually exclusive | Scan all `huawei-cloud-*` under `$SKILL_INSTALL_DIR/huawei-cloud/` | — |
| `--phase` | No | Start from a specific Phase (defaults to resume from missing phase) | `--phase 0` |
| `--fresh` | No | **Archive** (move, not delete) existing `phase-*.json` to `phases/archive/<timestamp>/` and start from scratch. History is preserved; nothing is deleted. | — |
| `--output` | No | Report output directory (default: reports/) | `--output ./test-reports` |
| `--skill-path` | No | Skill directory path. When set, `find_skill_path` searches **only here** (no install-dir fallback) | `--skill-path ./skills` |
| `--no-siblings` | No | Phase 5/6 does **not** auto-scan sibling `huawei-cloud-*` skills in the same directory (scanning ON by default) | `--no-siblings` |
| `--sibling-limit <N>` | No | Max sibling-skill count (default 5; `0` = same as `--no-siblings`) | `--sibling-limit 3` |

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

### Core Documents (Required Reading)

- `references/architecture.md` — Three-track eight-phase architecture diagram (Mermaid)
- `references/output-schema-spec.md` — Complete JSON field specification for each phase (including Phase 7 final report schema)
- `references/phase-transition-rules.md` — Phase transition / fallback / skip rules
- `references/acceptance-criteria.md` — Quality gates + 17-item report acceptance checklist
- `references/verification-method.md` — How to manually verify each phase (PowerShell + Git Bash)
- `references/phase-details.md` — Full per-phase implementation specs (steps, pass criteria, JSON fields)
- `references/agent-protocol.md` — Credential request protocol (full handling flow when AK/SK is missing)

### Supplementary References

- `references/iam-policies.md` — Minimum IAM permissions required to run the tester

### Templates (JSON Schema)

- `templates/phase-report-schema.json` — JSON Schema for `phase-N-summary.json` (N=0..6)
- `templates/test-case-schema.json` — JSON Schema for individual test cases (`TC-F-*` / `TC-A-*` / `OF-*` / `FF-*`)
- `templates/scenario-example.json` — Reference example for Phase 6 multi-skill scenario derivation

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
- **If AK/SK is missing, the framework emits the env-var setup template to stderr and exits 77. The Agent MUST output that template to the user verbatim and instruct them to set env vars out-of-band (in their shell / PowerShell $PROFILE). The Agent MUST NEVER ask the user to type or paste AK/SK in chat. Strictly prohibited from silently skipping any step that requires credentials.** (full protocol: `references/agent-protocol.md`)
- Resources created during testing must be tracked; if any are left behind, output manual cleanup instructions
- Orchestration scenarios are auto-derived; user should review and confirm before execution
- Write operations in orchestration scenarios require per-step user confirmation

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Skill directory does not exist | Report error and terminate, output available skill list |
| AK/SK environment variables not set | Framework emits the env-var setup template (with `export HUAWEICLOUD_SDK_AK=<your-access-key-id>` / `$env:HUAWEICLOUD_SDK_AK=<...>` placeholder snippets) to stderr and exits 77. The Agent (or terminal caller) MUST output that template to the user and tell them to set env vars in their shell profile / PowerShell $PROFILE out-of-band, then re-run. **Never** ask the user to type or paste AK/SK in chat. Strictly prohibited from silently skipping. |
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

**Core rules (MUST follow):**
1. On exit 77 or the sentinel → pause the pipeline; do not skip Phase 5/7
2. Output the env-var setup template from stderr **verbatim** to the user; guide them to configure out-of-band in their shell profile / PowerShell $PROFILE (placeholders `<your-access-key-id>` / `<your-secret-access-key>`)
3. **Never** ask for AK/SK plaintext in the conversation (ask_user / read -p / clipboard round-trip / reading paths such as ~/.hcloud/config.json)
4. After out-of-band setup, re-run the failed phase; if the user refuses, explicitly mark "live phases skipped — no credentials", never mark pass

> Full protocol (6-step response flow, direct terminal mode, example behavior): `references/agent-protocol.md`.

## Design Principles

- **Chain Verification** — Each Phase checks the previous phase's JSON to prevent skipping
- **Agent-proof** — Write operations must be confirmed by the user; fake confirmations are not allowed
- **Data-Driven** — All phases output in JSON format; Phase 7 merges
- **Batch Repeatable** — The same set of skills can be tested repeatedly; --fresh resets
- **Real-Environment First** — All orchestrations and E2E flows execute against real Huawei Cloud; no mocks
- **Degrade Without Losing Value** — Single skill does not run empty orchestration phases; degrades to meaningful single-skill lifecycle tests
- **Resource Safety** — Resources created during testing must be tracked; if any remain, output clear manual cleanup instructions
- **Credentials Mandatory** — If AK/SK is missing, the framework emits the env-var setup template to stderr and exits 77. The Agent MUST output that template to the user and instruct them to set env vars out-of-band. The Agent MUST NEVER ask the user to type or paste AK/SK in chat. Strictly prohibited from silently skipping any step that requires credentials.

