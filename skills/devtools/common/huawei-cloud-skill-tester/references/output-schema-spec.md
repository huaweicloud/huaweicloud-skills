# 各阶段 JSON 输出规范

## 通用顶层骨架

所有 phase-N-summary.json 共享此顶层结构：

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

## Phase 5 — 清理

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

## Phase 6 — 编排测试

### result 字段

```json
{
  "mode": "full | downgraded_self_check",
  "conflict_scan": {
    "pairs_checked": <int>,
    "conflicts": [
      {
        "severity": "high | medium | low | info",
        "skill_a": "<skill-name>",
        "skill_b": "<skill-name>",
        "trigger": "<conflicting trigger text>",
        "recommendation": "<string>"
      }
    ],
    "no_conflict_pairs": <int>
  },
  "data_flow_tests": [
    {
      "test_id": "DF-01",
      "from_skill": "<skill-a>",
      "to_skill": "<skill-b>",
      "data_item": "<如 instance_id, voucher_id>",
      "status": "pass | fail | skipped",
      "detail": "<string>"
    }
  ],
  "parallel_load_test": {
    "skills_loaded": ["skill-a", "skill-b"],
    "verdict": "pass | fail | skipped",
    "detail": "<string>"
  },
  "cleanup": {
    "resources_cleaned": <int>,
    "resources_failed": <int>
  }
}
```

### 降级模式（仅 1 skill）

```json
{
  "mode": "downgraded_self_check",
  "conflict_scan": {
    "internal_ambiguities": [
      {
        "description": "技能 'bss-voucher-manage' 的 triggers '查代金券' 和 '代金券查询' 语义高度重叠",
        "risk": "low"
      }
    ]
  },
  "data_flow_tests": [],
  "parallel_load_test": {"verdict": "skipped", "reason": "仅1个skill, 无需并行测试"},
  "cleanup": {}
}
```

---

## Phase 7 — 全流程测试

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
        "input": {},
        "expected_output": {},
        "actual_output": {},
        "status": "pass | fail | skip",
        "duration_s": <float>,
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
    "name": "单技能完整功能闭环",
    "skills_involved": ["bss-voucher-manage"],
    "description": "串联 skill 'bss-voucher-manage' 的所有功能点：查询→删除→统计",
    "steps": [...]
  }
}
```

---

## Phase 8 — 合规检查

### result 字段

```json
{
  "skills_checked": [
    {
      "skill_name": "<string>",
      "validate_result": {
        "pass": <int>,
        "fail": <int>,
        "warn": <int>,
        "verdict": "pass | fail | warn",
        "details": [
          {"check": "SKILL.md exists", "level": "critical", "status": "pass"},
          {"check": "YAML Frontmatter", "level": "critical", "status": "pass"}
        ]
      }
    }
  ],
  "security_scan": {
    "credential_leak": "pass | fail",
    "cross_skill_invocation": "pass | fail",
    "dangerous_exec_chain": "pass | fail",
    "webshell_detected": "pass | fail",
    "malware_signature": "pass | fail",
    "verdict": "pass | fail"
  }
}
```

---

## Phase 9 — 最终报告

### result 字段

```json
{
  "test_id": "test-<YYYYMMDD>-<HHMMSS>",
  "environment": {
    "hostname": "<string>",
    "hermes_version": "<string>",
    "python_version": "<string>",
    "hcloud_version": "<string>"
  },
  "phases_summary": [
    {"phase": 0, "name": "install-check", "verdict": "pass", "duration_s": 3.5},
    ...
  ],
  "overall_statistics": {
    "total_phases": 9,
    "phase_pass": <int>,
    "phase_fail": <int>,
    "total_duration_s": <float>,
    "test_cases_total": <int>,
    "test_cases_pass": <int>,
    "test_cases_fail": <int>,
    "test_cases_skip": <int>,
    "pass_rate": <float>
  },
  "skills_tested": [
    {"name": "skill-a", "phases_completed": 6, "test_cases": 10, "pass": 9, "fail": 1}
  ],
  "resources_created": <int>,
  "resources_cleaned": <int>,
  "resources_manual": <int>,
  "manual_interventions": [
    {"phase": 5, "resource_type": "<type>", "resource_id": "<id>", "steps": [...]}
  ],
  "failures_detail": [
    {"phase": 4, "tc_id": "TC-F-03", "error": "<string>", "recommendation": "<string>"}
  ],
  "warnings": [
    {"phase": 6, "severity": "medium", "message": "<string>"}
  ],
  "html_report": "reports/test-<timestamp>.html",
  "json_report": "reports/test-<timestamp>.json"
}
```
