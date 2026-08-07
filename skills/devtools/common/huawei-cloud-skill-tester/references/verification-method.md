# Verification Method — 三轨八节各阶段验证方法

> 与 `scripts/` 实际脚本对齐。覆盖 **Phase 0~7 全 8 个 phase**。
> 路径使用 sibling test-files 目录 `<skill>-test-files/`（artifact 不放 skill 源目录）。
> 命令同时给出 **PowerShell** 和 **Git Bash** 两种版本（PowerShell 是默认 shell）。

## 通用准备

```powershell
# PowerShell
$env:WS    = "C:\Users\gaoyunjiao\Desktop\ai-skill-assitant"
$env:SKILL = "huawei-cloud-rds-query"   # 替换成你要测的 skill
$env:SCRIPTS = "$env:WS\skills\huawei-cloud-skill-tester\scripts"
$env:TF_DIR = "$env:WS\skills\$env:SKILL-test-files"  # test artifacts 目录
```

```bash
# Git Bash
export WS="$HOME/Desktop/ai-skill-assitant"
export SKILL="huawei-cloud-rds-query"
export SCRIPTS="$WS/skills/huawei-cloud-skill-tester/scripts"
export TF_DIR="$WS/skills/${SKILL}-test-files"
```

---

## Phase 0 — 安装验证（install-check）

**目标**：确认 skill 目录结构合规 + install/uninstall/reinstall 循环可达。

**手动验证**：

```powershell
# 检查 4 项目录硬要求（缺一不可）
Test-Path "$env:WS\skills\$env:SKILL\SKILL.md"
Test-Path "$env:WS\skills\$env:SKILL\scripts" -PathType Container
Test-Path "$env:WS\skills\$env:SKILL\references" -PathType Container
Test-Path "$env:WS\skills\$env:SKILL\references\iam-policies.md"
```

**跑 phase 0**：

```powershell
bash "$env:SCRIPTS\tier1\phase-0-install-check.sh" "$env:WS\skills\$env:SKILL"
```

**验证产物**：

```powershell
Test-Path "$env:TF_DIR\phases\phase-0-summary.json"
Get-Content "$env:TF_DIR\phases\phase-0-summary.json" | Select-String '"verdict"'
```

期望：`directory_integrity.pass == true`、`install/uninstall/reinstall` 至少有一项 `pass` 或 `skipped`。

---

## Phase 1 — 功能提取（feature-extraction）

**目标**：从 SKILL.md 解析 metadata、triggers、commands、resource_types。

**手动验证**：

```powershell
# 至少有 frontmatter + 描述
Get-Content "$env:WS\skills\$env:SKILL\SKILL.md" -TotalCount 30
# 检查 name / triggers / description 都在 frontmatter
```

**跑 phase 1**：

```powershell
bash "$env:SCRIPTS\tier1\phase-1-skill-analysis.sh" "$env:WS\skills\$env:SKILL"
```

**验证产物**：

```powershell
Get-Content "$env:TF_DIR\phases\phase-1-summary.json" |
  Select-String -Pattern "triggers|commands|resource_types|verdict"
```

期望：`triggers` 与 `commands` 至少各 1 条；`has_write_operations` 反映实际写操作情况。

---

## Phase 2 — 技术调研（tech-research）

**目标**：对每条 command 做 CLI/SDK/API 三级回退探测。

**手动验证**：检查是否能直接调通至少一种 executor：

```powershell
# 测 CLI 可用性（需要先装 hcloud — 见 cli-installation-guide.md）
hcloud RDS ListInstances --cli-region=cn-north-4 --limit=1
```

**跑 phase 2**：

```powershell
bash "$env:SCRIPTS\tier1\phase-2-tech-research.sh" "$env:WS\skills\$env:SKILL"
```

**验证产物**：

```powershell
Get-Content "$env:TF_DIR\phases\phase-2-summary.json" |
  Select-String -Pattern "cli_available|sdk_available|api_available|not_available"
```

期望：每条 command 至少匹配 CLI/SDK/API 之一（否则 verdict 降为 partial）。

---

## Phase 3 — 用例生成（test-case-generation）

**目标**：根据 Phase 1+2 生成 TC-F-*/TC-A-* 用例（正向 + 边界 + 异常）。

**跑 phase 3**：

```powershell
bash "$env:SCRIPTS\tier1\phase-3-gen-testcases.sh" "$env:WS\skills\$env:SKILL"
```

**验证产物**：

```powershell
# 至少 1 条用例
Get-Content "$env:TF_DIR\phases\phase-3-summary.json" |
  Select-String -Pattern "TC-F-|TC-A-"
# 统计
$phase3 = Get-Content "$env:TF_DIR\phases\phase-3-summary.json" -Raw | ConvertFrom-Json
$phase3.result.statistics
```

期望：`functional_cases + api_cases >= 1`；高风险用例对应写操作。

---

## Phase 4 — 执行（test-execution）

**目标**：跑 Phase 3 的用例（只读自动，写操作需 ALLOW_WRITES=1）。

**前置**：AK/SK 凭证（`HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` 任意 HUAWEI* 开头）。**缺失时不再弹 prompt —— 框架直接输出 env-var 设置模板到 stderr 并 exit 77**，用户必须在自己的 shell profile / PowerShell $PROFILE 中带外设置后再重跑。

**跑 phase 4（默认只读）**：

```bash
# Linux / macOS — 用户在自己的 shell 里 export（不要 echo 给 agent）
export HUAWEI_ACCESS_KEY="..."
export HUAWEI_SECRET_KEY="..."
bash scripts/tier1/phase-4-execute-tests.sh "$WS/skills/$SKILL"
```

```powershell
# Windows PowerShell — 用户在自己的 session 里 $env:=
$env:HUAWEI_ACCESS_KEY = "..."
$env:HUAWEI_SECRET_KEY = "..."
bash "$env:SCRIPTS\tier1\phase-4-execute-tests.sh" "$env:WS\skills\$env:SKILL"
```

**跑 phase 4（真跑写操作）**：

```powershell
$env:ALLOW_WRITES = "1"
bash "$env:SCRIPTS\tier1\phase-4-execute-tests.sh" "$env:WS\skills\$env:SKILL"
```

**验证产物**：

```powershell
$phase4 = Get-Content "$env:TF_DIR\phases\phase-4-summary.json" -Raw | ConvertFrom-Json
$phase4.result.statistics
# 失败归类 + 手工补充项
$phase4.result.execution_results | Where-Object status -eq "fail"
$phase4.result.manual_test_items
```

期望：`statistics.total == phases_detail.3.statistics.total`；`manual_test_items` 显式列出。

---

## Phase 5 — 多 skill 编排（orchestration）

**目标**：跨 skill 触发词冲突扫描 + 数据流候选 + 并行加载。

**默认行为**：从被测 skill 同目录自动找其他 `huawei-cloud-*` skill 做编排组合测试。Opt-out: `--no-siblings`。

**跑 phase 5**：

```powershell
bash "$env:SCRIPTS\tier2\phase-5-orchestration.sh" "$env:WS\skills\$env:SKILL"
```

**关闭兄弟扫描**：

```powershell
bash "$env:SCRIPTS\tier2\phase-5-orchestration.sh" --no-siblings "$env:WS\skills\$env:SKILL"
```

**验证产物**：

```powershell
$phase5 = Get-Content "$env:TF_DIR\phases\phase-5-summary.json" -Raw | ConvertFrom-Json
$phase5.result.mode                       # full | downgraded_self_check
$phase5.result.conflict_scan.pairs_checked
$phase5.result.conflict_scan.conflicts    # high/medium 冲突
$phase5.result.parallel_load_test.verdict
```

期望：多 skill 模式 `mode=full`，找到跨 skill 冲突；单 skill 模式 `mode=downgraded_self_check`。

---

## Phase 6 — 全流程 E2E（full-flow）

**目标**：单 skill 真跑闭环（list→create→update→delete），多 skill 派生场景链。

**前置**：Phase 5 完成；多 skill 模式不调真 API（默认），所以 AK/SK 不是必填。

**跑 phase 6**：

```powershell
bash "$env:SCRIPTS\tier2\phase-6-full-flow.sh" "$env:WS\skills\$env:SKILL"
```

**真跑 E2E（多 skill 也调真 API）**：

```powershell
$env:ALLOW_REAL_E2E = "1"
$env:HUAWEI_ACCESS_KEY = "..."
$env:HUAWEI_SECRET_KEY = "..."
bash "$env:SCRIPTS\tier2\phase-6-full-flow.sh" "$env:WS\skills\$env:SKILL"
```

**验证产物**：

```powershell
$phase6 = Get-Content "$env:TF_DIR\phases\phase-6-summary.json" -Raw | ConvertFrom-Json
$phase6.result.mode                                # downgraded_single_skill_flow | full
$phase6.result.scenario.skills_involved           # 列出所有编排 skill
$phase6.result.scenario.steps.Count
$phase6.result.state_consistency.pass
```

期望：单 skill 模式 `mode=downgraded_single_skill_flow`，步骤串成完整闭环；多 skill 模式 `mode=full`，`scenario.skills_involved` 包含所有编排 skill。

---

## Phase 7 — 合并报告（final-report）

**目标**：合并 Phase 0~6 JSON，输出 `test-report.json` + `test-report.md`。

**跑 phase 7**：

```powershell
bash "$env:SCRIPTS\tier3\phase-7-final-report.sh" "$env:WS\skills\$env:SKILL"
```

**验证产物**：

```powershell
# 列出所有报告目录
Get-ChildItem "$env:TF_DIR\reports" -Directory | Sort-Object Name -Descending | Select-Object -First 3
# 最新报告内容
$latest = Get-ChildItem "$env:TF_DIR\reports" -Directory | Sort-Object Name -Descending | Select-Object -First 1
Get-Content "$latest\test-report.md" -TotalCount 50   # 看 Summary 段
Get-Content "$latest\test-report.md" | Select-String -Pattern "Skills Tested|Phase 5|Phase 6"
```

期望：
- `Summary` 段含 `Skills Tested` 列表 + Key Findings
- `Phase-by-Phase Detail` 含 8 个 phase 小节（Phase 0~6 + Phase 7 在 Attachments）
- `Phase 5/6` 小节开头有 `Skills involved in this orchestration/E2E flow (N):` 列表
- `Phase 3/4` 小节列出**每一条**用例/结果
- `Phase 4` fail 时有 **Failures 归类汇总** 子节

**报告 17 条验收清单**见 `references/acceptance-criteria.md` § 报告验收。

---

## 一键跑全流程

```powershell
# PowerShell — 单 skill 完整跑（含兄弟编排）
$env:HUAWEI_ACCESS_KEY = "..."
$env:HUAWEI_SECRET_KEY = "..."
bash "$env:SCRIPTS\run-test-pipeline.sh" --skills $env:SKILL
```

```bash
# Git Bash — 同上
HUAWEI_ACCESS_KEY=... HUAWEI_SECRET_KEY=... \
  bash $SCRIPTS/run-test-pipeline.sh --skills $SKILL
```

**参数**：
- `--no-siblings` — 关闭兄弟 skill 自动扫描（默认 ON）
- `--sibling-limit N` — 兄弟 skill 数量上限（默认 5）
- `--phase N` — 从指定 phase 开始
- `--fresh` — 归档（不删）旧 phase JSON 后从 Phase 0 重跑
- `--all-installed` — 扫所有 `huawei-cloud-*` skill 一起测
- `--output DIR` — 报告输出目录（默认 `reports/`）

完整参数说明见 `SKILL.md` § Parameters。

---

## 故障排查

| 现象 | 排查 |
|------|------|
| `Phase N: 链式验证失败` | 检查 `phases/phase-(N-1)-summary.json` 是否存在；缺失则 `--fresh` 或 `--phase N-1` 补跑 |
| `AK/SK 凭证缺失（exit 77）` | 框架不会向 agent 或终端索要 AK/SK 明文；stderr 中已输出 env-var 设置模板。Agent / 调用方应将该模板原样输出给用户，引导其在 shell profile / PowerShell $PROFILE 带外设置 `HUAWEI_ACCESS_KEY` + `HUAWEI_SECRET_KEY`，然后用 `--phase 4` 重跑。 |
| 兄弟 skill 没被扫到 | 检查 `SIBLING_LIMIT` 是否被设为 0，或目录结构（必须 `huawei-cloud-*`） |
| Phase 7 verdict=pass 但 `test_cases_pass` 偏低 | 看 `Phase 4` fail 归类，按推荐修 SKILL.md 或 templates |
| 报告 `report_dir` 不是绝对路径 | 这是 bug — 重跑 Phase 7 |
