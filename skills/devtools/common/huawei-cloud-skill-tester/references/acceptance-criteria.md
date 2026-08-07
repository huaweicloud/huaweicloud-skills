# Acceptance Criteria

> 与 `scripts/` 实际脚本对齐（**三轨八节** = Tier 1: Phase 0~4 + Tier 2: Phase 5~6 + Tier 3: Phase 7 报告，共 8 个 phase）。
> 旧表述"Phase 0~6 共 7 个 phase，Tier 3 的 Phase 7 是报告聚合"已重写为统一的"三轨八节"。

## Test Pass Criteria

| Phase | Criteria |
|-------|----------|
| Phase 0 (install-check) | `SKILL.md`、`scripts/`、`references/`、`references/iam-policies.md` 四项**全部**存在；install / uninstall / reinstall 至少有一项可达状态（`pass` 或 `skipped`） |
| Phase 1 (feature-extraction) | metadata / triggers / commands / capabilities / resource_types 全部提取无报错；`commands` 与 `triggers` 至少各 1 条，否则 verdict=`partial` |
| Phase 2 (tech-research) | 每条 command 至少匹配 CLI / SDK / API 其一，否则 `recommended_executor=manual`，verdict 视未匹配条数降为 `partial` |
| Phase 3 (test-case-generation) | `functional_cases + api_cases >= 1`；按 is_write 风险等级生成正向 + 边界用例 |
| Phase 4 (test-execution) | 只读用例 pass / warn / fail / error 均允许；写用例在 `ALLOW_WRITES=0` 时 skip，在 `ALLOW_WRITES=1` 时真跑；missing business params 标 warn 并产出 `manual_test_items` |
| Phase 5 (orchestration) | 多 skill：触发词冲突扫描 + 数据流候选 + 并行加载；单 skill：自检模式（内部 trigger 歧义 + 写操作排序提示）。**默认从被测 skill 同目录自动扫兄弟 skill** |
| Phase 6 (full-flow) | 单 skill：真跑闭环（list→create→update→delete），写操作受 ALLOW_WRITES 门控；多 skill：当前为派生计划（不真跑，步骤 `status=pass` 为派生标记，非执行结果） |
| Phase 7 (final-report) | 合并 Phase 0~6 JSON，输出 `test-report.json` + `test-report.md`；不修改已有 phase-N-summary.json 的 verdict |

## Quality Gates（critical，必须满足）

- 全部 4 个目录完整性检查必须通过（Phase 0）
- AK/SK 凭证缺失时直接终止 Phase 4 / Phase 6 并把 env-var 设置模板输出到 stderr（exit 77 + sentinel）—— **任何模式（TTY / agent / pipe）都走这一路径，不再有任何形式的交互 prompt**
- 链式验证（`lib/chain-verify.sh: check_phase_deps`）必须通过才能进入下一 phase
- 写操作无 AK/SK 不执行；非交互模式下 `ALLOW_WRITES=0` 是默认安全门
- 跨 skill 触发词完全相同 = `severity=high`，会拉低 Phase 5 verdict 到 `fail`
- Phase 0/1/2/3/4/5/6 永不跳过（缺失链则 `exit 1`）；Phase 7 永不跳过（输出报告本身）

## 报告验收（Phase 7 输出）

> Phase 7 输出的 `test-report.json` 顶层 schema 见 `references/output-schema-spec.md` § Phase 7。
> 以下是该报告必须满足的"验收清单"——任何一条不满足视为 bug。

| # | 验收项 | 判定 |
|---|--------|------|
| 1 | `summary.phases_total == 8`（实际跑 8 个 phase：0~6 + 7 报告） | 数字一致 |
| 2 | `summary.verdict` ∈ `pass / partial / fail` 三选一 | 字段值合法 |
| 3 | `summary.test_cases_total` 等于 `phases_detail.3.statistics.total` | 跨字段一致 |
| 4 | `summary.test_cases_pass` 等于 `phases_detail.4.statistics.pass` | 跨字段一致 |
| 5 | `summary.pass_rate` 等于 `pass / total × 100`，保留 1 位小数 | 计算一致 |
| 6 | `key_findings` 长度 3-5 条 | 数量合理 |
| 7 | 每个 `phases_detail.<N>` 都有 `skills_involved[]`（Phase 5/6） 或等价结构 | 字段齐 |
| 8 | `skills[].phases_detail.3.functional_cases` 长度 ≥ 1 | 至少 1 个用例 |
| 9 | `skills[].phases_detail.4.execution_results` 长度 == `phases_detail.3.statistics.total` | 数量一致 |
| 10 | Markdown 报告的 `Skills Tested` 列表包含所有 `skills[].name` | 报告字段对齐 |
| 11 | Phase 5/6 Markdown 小节开头有 `Skills involved in this orchestration/E2E flow (N):` 列表 | 报告字段对齐 |
| 12 | Phase 4 Markdown 小节列出**每一条** `execution_results`（不允许只给统计数） | 报告硬性要求 |
| 13 | Phase 3 Markdown 小节列出**每一条** `functional_cases` + `api_cases` | 报告硬性要求 |
| 14 | Phase 4 出现 `fail` 时必须有 **Failures 归类汇总** 子节 | 报告硬性要求 |
| 15 | Phase 4 出现 `manual_test_items` 时必须在 Markdown 中显式列出 | 报告硬性要求 |
| 16 | 报告路径 `report_dir` 必须是绝对路径 | 路径规范 |
| 17 | 报告不含 AK/SK、token 等敏感信息 | 安全 |
| 18 | 被测 skill 的 `references/cli-installation-guide.md` 不包含 `hcloud configure set --cli-access-key=...` / `--cli-secret-key=...` / `BasicCredentials(ak=..., sk=...)` 等**会话内** AK/SK 录入形式（NEVER / 禁止 / FORBIDDEN 上下文除外） | 安全 — SEC-002 检查项 |

## 跨 Phase 资源清理

- 写用例的资源变更记录在 `phase-4-summary.json.result.execution_results[i].resource_changes[]`
- Phase 5/6 不重复清理（依赖 Phase 4 的 `resource_changes` + 报告里的 `manual_test_items` / `cleanup.manual_required`）
- 残留资源必须报告里给具体清理命令
