# 各阶段 JSON 输出规范

> 与 `scripts/` 实际脚本对齐（Phase 0~6 共 7 个执行 phase；Phase 7 是合并报告本身）。
> 旧版 Phase 5 清理 / Phase 8 合规 / Phase 9 终报告的描述已重排或删除（见 §"与旧版差异"）。

## 通用顶层骨架

所有 `phase-N-summary.json`（N = 0..6）共享此顶层结构：

```json
{
  "phase": <int>,
  "phase_name": "<string>",
  "tier": <1|2|3>,
  "target": {
    "type": "single_skill | multi_skill | all",
    "skills": ["skill-name-1", ...]
  },
  "timestamp": "<ISO 8601>",
  "execution_meta": {
    "duration_s": <float>,
    "retry_count": <int>,
    "user_confirmed": <bool>
  },
  "result": { <phase-specific> },
  "summary": {
    "verdict": "pass | fail | partial | skipped | downgraded",
    "pass_checks": <int>,
    "fail_checks": <int>,
    "warn_checks": <int>
  }
}
```

---

## Phase 0 — 安装验证

### result 字段

```json
{
  "install": {
    "status": "pass | fail | skipped",
    "existing": true | false,
    "duration_s": <float>
  },
  "uninstall": {
    "status": "pass | fail | skipped",
    "reason": "<string or null>"
  },
  "reinstall": {
    "status": "pass | fail | skipped"
  },
  "directory_integrity": {
    "pass": true | false,
    "checks": {
      "SKILL.md": true | false,
      "scripts/": true | false,
      "references/": true | false,
      "references/iam-policies.md": true | false
    }
  }
}
```

### verdict 判断

| 条件 | verdict |
|------|---------|
| directory_integrity.pass == true | pass |
| directory_integrity.pass == false | fail |

---

## Phase 1 — 功能提取

### result 字段

```json
{
  "metadata": {
    "name": "<skill-name>",
    "description": "<full description>",
    "triggers": ["trigger1", "trigger2", ...],
    "tags": ["tag1", ...]
  },
  "capabilities": {
    "list": ["查询XXX", ...],
    "create": ["创建XXX", ...],
    "update": ["修改XXX", ...],
    "delete": ["删除XXX", ...]
  },
  "has_write_operations": true | false,
  "resource_types": ["resource_type_1", ...],
  "commands": [
    {
      "id": "CMD-01",
      "source": "SKILL.md | scripts/ | inferred",
      "description": "<string>",
      "executor": "cli | sdk | api | unknown",
      "is_write": true | false
    }
  ],
  "scripts": ["scripts/test-cli-commands.sh", ...],
  "references": ["references/iam-policies.md", ...]
}
```

---

## Phase 2 — 技术调研

### result 字段

```json
{
  "research": [
    {
      "cmd_id": "CMD-01",
      "description": "<string>",
      "cli": {
        "available": true | false,
        "command": "hcloud ..." or null,
        "reason": "<string>" or null
      },
      "sdk": {
        "available": true | false,
        "package": "huaweicloudsdkxxx.v2",
        "method": "method_name",
        "api_path": "/v2/..." or null,
        "error": "<string>" or null
      },
      "api": {
        "available": true | false,
        "endpoint": "/v2/..." or null,
        "source": "sdk_http_info | api_explorer | user_provided | not_found"
      },
      "recommended_executor": "cli | sdk | api",
      "risk_level": "low | medium | high"
    }
  ],
  "summary": {
    "cli_available": <int>,
    "sdk_available": <int>,
    "api_available": <int>,
    "not_available": <int>
  }
}
```

---

## Phase 3 — 用例生成

### result 字段

```json
{
  "functional_cases": [
    {
      "id": "TC-F-01",
      "name": "<string>",
      "type": "正向 | 边界 | 异常",
      "command": "<executable command or code>",
      "expected": "<string>",
      "is_write": true | false,
      "risk_level": "low | medium | high",
      "executor": "cli | sdk | api",
      "prerequisites": ["TC-F-XX", ...],
      "verification_method": "<string>",
      "dependencies": ["CMD-01", ...]
    }
  ],
  "api_cases": [
    {
      "id": "TC-A-01",
      "name": "<string>",
      "endpoint": "<REST path>",
      "method": "GET | POST | PUT | DELETE",
      "expected": "<string>",
      "is_write": true | false,
      "risk_level": "low | medium | high"
    }
  ],
  "statistics": {
    "total": <int>,
    "functional": <int>,
    "api": <int>,
    "write_operations": <int>,
    "read_operations": <int>,
    "high_risk": <int>,
    "low_risk": <int>
  }
}
```

---

## Phase 4 — 执行

### result 字段

```json
{
  "execution_results": [
    {
      "tc_id": "TC-F-01",
      "status": "pass | fail | skip | error",
      "duration_s": <float>,
      "output_snippet": "<string>",
      "error": "<string or null>",
      "resource_changes": [
        {
          "resource_type": "<string>",
          "resource_id": "<string or null if creation failed>",
          "change_type": "created | modified | deleted | none",
          "cleanup_method": {
            "type": "cli | sdk | api | none",
            "command": "<string>"
          },
          "cleanup_required": true | false
        }
      ],
      "user_confirmed": true | false
    }
  ],
  "statistics": {
    "total": <int>,
    "pass": <int>,
    "fail": <int>,
    "skip": <int>,
    "error": <int>,
    "pass_rate": <float>
  },
  "all_resources_changed": [ <flattened resource_changes> ]
}
```

---

## Phase 5 — 多 Skill 编排（触发词冲突 + 数据流 + 并行加载）

> Phase 5 在当前实现中**不清理资源**——清理职责内嵌在 Phase 4 的
> `execution_results[i].resource_changes` 中。Phase 4 缺业务参数 (manual_test_items)
> 标 `warn` 并在报告的 Markdown Phase 4 小节里显式列出；Phase 6 残留资源
> 走 `phase-6-summary.json.result.cleanup.manual_required[]` 输出具体清理命令。
> 本节描述 Phase 5 当前的 result 结构。

### result 字段

```json
{
  "mode": "normal | skipped_no_resources",
  "resources_to_clean": [
    {
      "resource_type": "<string>",
      "resource_id": "<string>",
      "change_type": "created | modified",
      "skill": "<skill-name>",
      "tc_id": "TC-F-XX"
    }
  ],
  "auto_cleaned": [
    {
      "resource_id": "<string>",
      "status": "success | failed",
      "attempts": <int>,
      "error": "<string or null>"
    }
  ],
  "failed_cleanup": [
    {
      "resource_id": "<string>",
      "reason": "<string>",
      "manual_steps": ["step1", "step2"]
    }
  ],
  "manual_cleanup_instructions": [
    {
      "resource_type": "<string>",
      "resource_id": "<string>",
      "reason": "<string>",
      "manual_steps": ["hcloud XXX Delete --id=xxx"],
      "reference": "华为云控制台 → ..."
    }
  ]
}
```

---

## Phase 6 — 全流程 E2E 测试（单 skill 真跑闭环 / 多 skill 派生计划）

> 注：旧 spec 把这一节标题写成"Phase 7 — 全流程测试"是编号错位（实际脚本是
> `tier2/phase-6-full-flow.sh`，对应 phase-6-summary.json）。下面对齐到真实实现。

### result 字段

```json
{
  "mode": "full | downgraded_single_skill_flow",
  "scenario": {
    "name": "<string>",
    "skills_involved": ["skill-a", ...],
    "description": "<string>",
    "derived_automatically": true | false,
    "user_confirmed": true | false,
    "steps": [
      {
        "seq": <int>,
        "tc_id": "<引用的测试用例ID>",
        "skill": "<skill-name>",
        "action": "<string>",
        "status": "pass | fail | skip",
        "duration_s": <float>,
        "output": "<string>",
        "error": "<string or null>",
        "resource_changes": [<resource_change objects>]
      }
    ]
  },
  "state_consistency": {
    "pass": true | false,
    "detail": "<string>",
    "final_state_summary": "<string>"
  },
  "cleanup": {
    "verdict": "pass | partial | fail",
    "resources_cleaned": <int>,
    "resources_failed": <int>,
    "manual_required": [<manual_instruction>]
  }
}
```

### 降级模式（仅 1 skill）

```json
{
  "mode": "downgraded_single_skill_flow",
  "scenario": {
    "name": "单技能完整功能闭环 — huawei-cloud-rds-query",
    "skills_involved": ["huawei-cloud-rds-query"],
    "description": "串联 skill 'huawei-cloud-rds-query' 的所有功能点",
    "derived_automatically": true,
    "user_confirmed": true,
    "steps": [...]
  },
  "state_consistency": {
    "pass": true,
    "detail": "单技能闭环，状态一致",
    "final_state_summary": "功能点全部走通"
  },
  "cleanup": {
    "verdict": "pass",
    "resources_cleaned": 0,
    "resources_failed": 0,
    "manual_required": []
  }
}
```

---

## Phase 7 — 合并报告（Tier 3，**最终报告**）

> **重要**：本节是用户最终交付的"测试报告"的规范，描述 `reports/report-<ts>/test-report.{json,md}`
> 的完整结构。脚本 `tier3/phase-7-final-report.sh` 按此规范产出。
>
> 报告原则：**先给 Summary（TL;DR），再给 per-phase 详细报告（每 phase 含
> 产生的用例 / 实际执行结果 / 阶段小结），最后给附件索引**。这样读报告的人可以
> 先看 Summary 决定要不要继续看详细部分。

### 报告总体骨架

```text
┌────────────────────────────────────────────────────────────────┐
│ Header (test_id, generated_at, skills, report_dir)             │
├────────────────────────────────────────────────────────────────┤
│ §1 Summary (TL;DR)                                              │
│   - Overall Verdict (✅ / ⚠️ / ❌ / ⏭)                          │
│   - 统计指标表 (phases / test cases / pass rate / 资源变更)    │
│   - Key Findings 列表（3-5 条最重要结论）                       │
├────────────────────────────────────────────────────────────────┤
│ §2 Per-Phase Detail                                             │
│   对每个 skill 重复：                                          │
│   ┌─ Skill: <name>                                             │
│   │  Path: <skill_path>                                        │
│   │                                                            │
│   │  对每个 phase (0..6) 重复：                                │
│   │  ┌─ Phase N — <name>                                       │
│   │  │  Verdict + Duration + 阶段小结                          │
│   │  │  (Phase 0)  目录硬要求 4 项 + install/uninstall/reinstall │
│   │  │  (Phase 1)  提取的 commands 列表                        │
│   │  │  (Phase 2)  CLI/SDK/API 可用性矩阵                      │
│   │  │  (Phase 3)  生成的测试用例列表（functional + api）      │
│   │  │  (Phase 4)  用例执行结果列表（含 pass/fail/warn/skip） │
│   │  │  (Phase 5)  冲突扫描 + 数据流候选                       │
│   │  │  (Phase 6)  E2E 场景步骤列表                            │
│   │  └─                                                        │
│   └─                                                            │
├────────────────────────────────────────────────────────────────┤
│ §3 Attachments (phase JSONs 路径、archive 路径、reports 目录) │
└────────────────────────────────────────────────────────────────┘
```

### JSON 顶层 schema

> 报告同时输出 JSON（机器可读）和 Markdown（人可读）两份。Markdown 是 JSON 的
> 渲染版，**内容必须一一对应**，不允许出现"JSON 里有的 / Markdown 没"或
> "Markdown 里的 / JSON 没"的情况。

```json
{
  "test_id": "test-<YYYYMMDD>-<HHMMSS>",
  "generated_at": "<ISO 8601>",
  "skills": [
    {
      "name": "huawei-cloud-rds-query",
      "skill_path": "C:/.../skills/huawei-cloud-rds-query",
      "phases_summary": [
        {"phase": 0, "name": "install-check",       "verdict": "pass",    "duration_s": 1.0, "summary": "4/4 目录硬要求通过"},
        {"phase": 1, "name": "skill-analysis",      "verdict": "pass",    "duration_s": 0.0, "summary": "提取 15 条命令 / 20 个触发词"},
        {"phase": 2, "name": "tech-research",       "verdict": "pass",    "duration_s": 1.0, "summary": "CLI 15/15 可用"},
        {"phase": 3, "name": "test-case-generation","verdict": "pass",    "duration_s": 0.0, "summary": "生成 28 条用例"},
        {"phase": 4, "name": "test-execution",      "verdict": "partial", "duration_s": 6.0, "summary": "9 pass / 12 fail / 7 warn"},
        {"phase": 5, "name": "orchestration",       "verdict": "pass",    "duration_s": 1.0, "summary": "单 skill self-check"},
        {"phase": 6, "name": "full-flow",           "verdict": "pass",    "duration_s": 9.0, "summary": "15 步闭环"}
      ],
      "phases_detail": {
        "0": { /* Phase 0 result */ },
        "1": { /* Phase 1 result */ },
        "2": { /* Phase 2 result */ },
        "3": { /* Phase 3 result（含 functional_cases / api_cases / statistics）*/ },
        "4": { /* Phase 4 result（含 execution_results / statistics / manual_test_items）*/ },
        "5": { /* Phase 5 result（含 conflict_scan / data_flow_tests）*/ },
        "6": { /* Phase 6 result（含 scenario / state_consistency / cleanup）*/ }
      }
    }
  ],
  "summary": {
    "verdict": "pass | partial | fail",
    "verdict_label": "✅ PASS | ⚠️ PARTIAL | ❌ FAIL",
    "phases_total": 7,
    "phases_pass": <int>,
    "phases_partial": <int>,
    "phases_fail": <int>,
    "phases_skipped": <int>,
    "phases_missing": <int>,
    "test_cases_total": <int>,
    "test_cases_pass": <int>,
    "test_cases_fail": <int>,
    "test_cases_warn": <int>,
    "test_cases_skip": <int>,
    "test_cases_error": <int>,
    "pass_rate": <float, 0~100, 一位小数>,
    "manual_items_count": <int>,
    "cloud_resources_changed": <int>
  },
  "key_findings": [
    "<最重要结论 1>",
    "<最重要结论 2>",
    "<最重要结论 3>"
  ],
  "environment": {
    "python_version": "<string>"
  },
  "report_dir": "<absolute path to this report's directory>"
}
```

### per-phase detail（§2 内容）— 各 phase 必须包含的字段

> `phases_detail.<N>` 的内容来自对应 `phase-N-summary.json` 的 `result` 字段
> （按 phase 原文透传），但要按以下规范化要求整理和重命名。

#### Phase 0 detail — `directory_integrity` + `install` + `uninstall` + `reinstall`

```json
{
  "directory_integrity": {
    "pass": true,
    "checks": {
      "SKILL.md": true,
      "scripts/": true,
      "references/": true,
      "references/iam-policies.md": true
    }
  },
  "install":      {"status": "pass | fail | skipped", "duration_s": 0.0, "note": "..."},
  "uninstall":    {"status": "pass | fail | skipped", "duration_s": 0.0, "note": "..."},
  "reinstall":    {"status": "pass | fail | skipped", "duration_s": 0.0, "note": "..."}
}
```

#### Phase 1 detail — `metadata` + `commands[]` + 触发词 / 资源类型

```json
{
  "metadata": {
    "triggers_count": 20,
    "commands_count": 15,
    "resource_types": ["rds", "ecs"],
    "has_write_operations": false
  },
  "commands": [
    {"id": "CMD-01", "source": "SKILL.md-bash-block", "description": "...",
     "executor": "cli | sdk | api | script", "is_write": true | false},
    ...
  ]
}
```

#### Phase 2 detail — 每条 command 的 CLI/SDK/API 可用性

```json
{
  "research": [
    {"cmd_id": "CMD-01", "cli": true, "sdk": false, "api": false,
     "recommended": "cli", "risk": "low"},
    ...
  ],
  "summary": {"cli_available": 15, "sdk_available": 0,
              "api_available": 0, "not_available": 0}
}
```

#### Phase 3 detail — 生成的测试用例列表（**用户要求：报告里要列出每个阶段产生的用例**）

```json
{
  "functional_cases": [
    {"id": "TC-F-01", "name": "...", "type": "正向 | 边界 | 异常",
     "risk": "low | medium | high", "executor": "cli | sdk | api | script",
     "source": "CMD-XX"},
    ...
  ],
  "api_cases": [ ... ],
  "statistics": {
    "total": 28, "functional": 28, "api": 0,
    "write_operations": 0, "read_operations": 28,
    "high_risk": 0, "low_risk": 28
  }
}
```

> **报告硬性要求**：每条 functional_case 和 api_case 必须在 Markdown 报告里
> 以表格形式完整列出（`ID | Name | Type | Risk | Executor | Source` 列），
> 不允许只给统计数。这是"报告里能看到每个阶段产生的用例"的规定。

#### Phase 4 detail — 用例执行结果（**用户要求：报告里要列出用例执行结果**）

```json
{
  "execution_results": [
    {"tc_id": "TC-F-01", "status": "pass | fail | warn | skip | error",
     "duration_s": 0.06, "error": "<truncated error message>"},
    ...
  ],
  "statistics": {
    "total": 28, "pass": 9, "fail": 12, "warn": 0, "skip": 7, "error": 0,
    "pass_rate": 32.1
  },
  "all_resources_changed": [
    {"resource_type": "...", "resource_id": "...",
     "change_type": "created | modified | deleted | none",
     "tc_id": "TC-F-XX"}
  ],
  "manual_test_items": [
    {"tc_id": "TC-F-05", "name": "ListSimplifiedInstances",
     "missing_params": ["..."], "hint": "...",
     "command": "hcloud RDS ListSimplifiedInstances ..."}
  ]
}
```

> **报告硬性要求**：
> 1. 每条 `execution_results` 必须在 Markdown 报告里以表格形式完整列出
>    （`ID | Status | Duration | Error/Output` 列）；
> 2. 当 `fail` 数量 > 0 时，必须有 **Failures 归类汇总** 子节（按 error
>    pattern 分组 + 受影响用例列表）；
> 3. 当 `manual_test_items` 非空时，必须有 **Manual test items** 子节
>    （完整命令见 phase-4-summary.json）。

#### Phase 5 detail — 冲突扫描 + 数据流 + 并行加载（**必须含组合测试涉及 skill 列表**）

> **兄弟 skill 自动发现（默认 ON）**: Phase 5/6 默认会从被测 skill 的同级目录
> 自动找其他 `huawei-cloud-*` skill 做编排组合测试（用户硬性要求）。逻辑在
> `lib/utils.sh` 的 `discover_siblings()`：
>
> | 规则 | 说明 |
> |------|------|
> | 默认行为 | 扫描兄弟 skill（除自己外） |
> | 排除 | `*-test-files`、`huawei-cloud-skill-tester`、`huawei-cloud-skill-creator`、`huawei-cloud-new-tester`、无 SKILL.md 的目录 |
> | 数量上限 | `SIBLING_LIMIT`（默认 5；0 = 关闭） |
> | opt-out | `--no-siblings` / `WITHOUT_SIBLINGS=1` / `SIBLING_LIMIT=0` |
> | 排序 | 目录顺序（glob `huawei-cloud-*`） |
>
> **SKILL.md fallback**: 兄弟 skill 通常没跑过 phase 1（无 `phase-1-summary.json`），
> Phase 5 会实时解析它的 `SKILL.md` frontmatter 拿 triggers / resource_types。
> 支持三种格式：`triggers: [a, b, c]` inline / `triggers:\n  - a` block /
> `description: | ... Triggers include: "x","y"` embedded。
> 完全解析失败的兄弟 skill：跳过 + 记录在警告里。


```json
{
  "skills_involved": ["skill-a", "skill-b"],
  "mode": "downgraded_self_check | full",
  "conflict_scan": {
    "pairs_checked": <int or "N/A">,
    "conflicts": [{"severity": "high | medium | low | info",
                   "skill_a": "...", "skill_b": "...",
                   "trigger": "...", "recommendation": "..."}],
    "no_conflict_pairs": <int>,
    "internal_ambiguities": [ ... ],
    "cycle_warnings": [ ... ]
  },
  "data_flow_tests": [
    {"test_id": "DF-01", "from_skill": "...", "to_skill": "...",
     "data_item": "...", "status": "pass | fail | skipped | identified",
     "detail": "..."}
  ],
  "parallel_load_test": {
    "verdict": "pass | fail | skipped",
    "reason": "..."
  }
}
```

> `skills_involved` 是**用户硬性要求**的字段：列出本次组合测试（orchestration
> / 触发词冲突扫描）实际涉及的所有 skill。降级模式（仅 1 skill）下也必须填
> `["<该 skill>"]`，让用户一眼看出"组合测试只跑了 1 个 skill"。
>
> 数据来源：`phase-5-summary.json` 的 `target.skills`（Phase 5 脚本运行时
> 写入）。Phase 7 报告生成时从 `target.skills` 读取并放入 `phases_detail.5.skills_involved`。

#### Phase 6 detail — E2E 场景步骤列表（**用户要求：报告里要列出每个阶段测试的总结**，**必须含组合测试涉及 skill 列表**）

```json
{
  "skills_involved": ["skill-a", "skill-b"],
  "mode": "downgraded_single_skill_flow | full",
  "scenario": {
    "name": "单技能完整功能闭环 — huawei-cloud-rds-query",
    "skills_involved": ["huawei-cloud-rds-query"],
    "description": "...",
    "derived_automatically": true,
    "user_confirmed": true,
    "steps": [
      {"seq": 1, "tc_id": "FF-01", "skill": "...",
       "action": "...", "status": "pass | fail | skip",
       "output": "..."}
    ]
  },
  "state_consistency": {
    "pass": true,
    "detail": "...",
    "final_state_summary": "..."
  },
  "cleanup": {
    "verdict": "pass | partial | fail",
    "resources_cleaned": 0,
    "resources_failed": 0,
    "manual_required": []
  }
}
```

> `skills_involved` 是**顶层字段**（注意与 `scenario.skills_involved` 的区别）：
> - **顶层 `skills_involved`**：从 `phase-6-summary.json` 的 `target.skills`
>   读取，列出本次 E2E 测试涉及的所有 skill（用户报告要求）
> - **`scenario.skills_involved`**：从 `result.scenario.skills_involved` 透传，
>   列出本场景步骤串起来的 skill 列表（脚本生成步骤时写入）
>
> 两者在大多数情况下相等，但顶层字段是"这次 E2E 测试对象"的权威列表，
> 报告 Markdown 优先渲染顶层字段。

### Summary 判定规则（`summary.verdict`）

| 条件 | verdict | 标签 |
|------|---------|------|
| 所有 phase 都是 `pass`，且 test cases `pass_rate == 100` | `pass` | ✅ PASS |
| 至少 1 个 phase 是 `partial` 或 `fail`，但有 phase 是 `pass` | `partial` | ⚠️ PARTIAL |
| 所有 phase 都是 `fail` 或全 `skipped`/`missing` | `fail` | ❌ FAIL |
| 没跑任何 phase（输入空） | `fail` | ❌ FAIL |

> `verdict_label` 是给 Markdown 报告渲染用的、**直接显示给用户**的字符串，
> 由 `phase-7-final-report.sh` 根据 `verdict` 自动生成，必须包含 emoji 标识。

### Key Findings 提取规则

`key_findings[]` 是给人快速决策的 TL;DR 列表，**3-5 条**，生成规则：

1. 找出 pass 的 phase：`<skill-name>: <亮点>`（如"4 项目录硬要求全部通过"）
2. 找出 fail / partial 的 phase：`<skill-name> Phase N: <数量> 个用例失败`
3. 找出资源变更：`<skill-name>: 写操作 N 个 / 创建资源 M 个`
4. 找出 manual_items：`<skill-name>: N 个用例需手工补业务数据`
5. 去重、截断到 5 条

### Markdown 报告渲染规范

> 用户最终看的是 `.md` 文件。下面规定 Markdown 文档的章节顺序、必备元素、
> 表格列宽，确保 Phase 7 脚本输出与规范一致。

**章节顺序（强制）**：

1. Header — `Test ID` / `Generated` / `Skills` / `Report dir`
2. `## 📊 Summary (TL;DR)` — 总评 + 指标表 + Key Findings
3. `## 📋 Phase-by-Phase Detail`
   - 对每个 skill：1 个 `### Skill: <name>` 小节
   - 对每个 phase：1 个 `#### Phase N — <name>` 小节
4. `## 📎 Attachments` — 文件路径索引

**Summary 指标表（强制列）**：

| Metric | Value |
|--------|-------|
| Phases | X pass / Y partial / Z fail / W skipped (of 7) |
| Test Cases | total N \| pass P \| fail F \| warn W \| skip S \| error E |
| Pass Rate | P% |
| Manual Items | N (need real business data) |
| Cloud Resources Changed | N (Phase 4 only) |

**Skills Tested 列表**（**用户硬性要求** — Summary 段必备，列出本次测试涉及的所有 skill）：

```markdown
**Skills Tested:**

| # | Skill | Path |
|---|-------|------|
| 1 | `huawei-cloud-rds-query` | `C:/.../skills/huawei-cloud-rds-query` |
| 2 | `huawei-cloud-ecs-manage`  | `C:/.../skills/huawei-cloud-ecs-manage`  |
```

- 列顺序：按测试运行顺序（即 `skills` 参数传入顺序）
- 列字段：`#` 序号 / `Skill` 名称 / `Path` 绝对路径
- 单 skill 测试也必须有这张表（就一行）

**Phase 0 Markdown 节必备元素**：

- 目录硬要求表（4 行：SKILL.md / scripts/ / references/ / references/iam-policies.md）
- Install / Uninstall / Reinstall 表（Action | Status | Duration | Note）

**Phase 1 Markdown 节必备元素**：

- 提取的 metadata 列表（triggers / commands / resource_types / has_write_operations）
- Commands 表（ID | Source | Description | Executor | W/R）

**Phase 2 Markdown 节必备元素**：

- 概览：CLI N/N | SDK N/N | API N/N | Unavailable N/N
- Per-command 可用性表（ID | Recommended | CLI | SDK | API | Risk）

**Phase 3 Markdown 节必备元素**：

- Statistics 列表
- Test cases 表（ID | Name | Type | Risk | Executor | Source）

**Phase 4 Markdown 节必备元素**：

- Statistics 列表
- Test case results 表（ID | Status | Duration | Error/Output）
- **Failures 归类汇总**（按 error pattern 分组，含受影响用例）
- **Warns 列表**（每个 warn 标注 manual_test_hint）
- **Manual test items**（引用 phase-4-summary.json 的 `manual_test_items`）

**Phase 5 Markdown 节必备元素**：

- **组合测试涉及 skill 列表**（**用户硬性要求**）— `Skills involved in this orchestration (N):` + 每个 skill 一行
- 模式（`downgraded_self_check` / `full`）
- Conflict scan（pairs_checked / conflicts / no_conflict_pairs）
- Data flow tests（数量 + 列表）
- Parallel load test（verdict + reason）

**Phase 6 Markdown 节必备元素**：

- **组合测试涉及 skill 列表**（**用户硬性要求**）— `Skills involved in this E2E flow (N):` + 每个 skill 一行
- 模式 + 场景名 + 描述
- Steps 表（Seq | Action | Skill | Status | Output）
- State consistency（pass + detail + final_state_summary）
- Cleanup（verdict + resources_cleaned + resources_failed + manual_required）

**Attachments 节必备元素**：

- Phase JSONs 路径（`phases/phase-{0..7}-summary.json`）
- Archive 路径（`phases/archive/<ts>/`）
- Reports history（`reports/`）

### 报告硬性要求（违反视为 bug）

1. **必须有 Summary** — 哪怕只跑了一个 phase，Summary 也得填上对应统计
2. **必须有 Skills Tested 列表** — Summary 段必备，列出本次测试涉及的所有 skill（# | Skill | Path）
3. **必须有组合测试涉及 skill 列表** — Phase 5 / Phase 6 小节开头必备，分别标题为
   `Skills involved in this orchestration (N):` / `Skills involved in this E2E flow (N):`，
   数据来源 `target.skills`。降级单 skill 模式也必须列出 `["<该 skill>"]`
4. **每个阶段必须有：阶段小结 + 阶段产物（用例 / 结果）** — 不允许只写
   "Phase 4 pass" 然后跳过 28 条用例执行结果
5. **Markdown 和 JSON 必须字段对齐** — JSON 的 `phases_detail.<N>` 中
   出现的字段，Markdown 报告里对应的 phase 小节必须有等价内容
6. **关键数字必须一致** — Summary 的 `test_cases_total` 必须等于
   `phases_detail.3.statistics.total`；`test_cases_pass` 必须等于
   `phases_detail.4.statistics.pass`，依此类推
7. **不得包含敏感信息** — AK/SK、token、内部 hostname 必须在日志和报告里
   `sed` 掉（参考 `lib/utils.sh` 的 redaction 规则）
8. **写资源变更必须列出** — `phases_detail.4.all_resources_changed` 不能省略
9. **Manual items 必须显式列出** — 不允许在 Markdown 里折叠 / 隐藏
   `manual_test_items`，要让用户能在 Summary 段就看到 N (need real business data)
10. **报告路径必须是绝对路径** — `report_dir` 必须是绝对路径，不接受相对路径
