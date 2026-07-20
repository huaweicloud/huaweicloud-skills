# 三轨九阶架构图

```mermaid
graph TB
    subgraph "User Input"
        A[--skills / --all-installed]
    end

    subgraph "Tier 1: 单技能单元测试"
        P0["Phase 0: 安装验证"]
        P1["Phase 1: 功能提取"]
        P2["Phase 2: 技术调研"]
        P3["Phase 3: 用例生成"]
        P4["Phase 4: 执行"]
        P5["Phase 5: 清理"]
    end

    subgraph "Tier 2: 集成测试"
        direction TB
        DECIDE{"skill count"}
        DECIDE -->|"=1"| P6_SELF["Phase 6: 自检模式"]
        DECIDE -->|">=2"| P6_FULL["Phase 6: 编排冲突扫描"]
        P6_SELF --> P7_SELF["Phase 7: 单skill闭环"]
        P6_FULL --> P7_FULL["Phase 7: 全流程走通"]
    end

    subgraph "Tier 3: 总体验证"
        P8["Phase 8: 合规检查"]
        P9["Phase 9: 最终报告"]
    end

    A --> Tier1_Loop["遍历每个skill"]
    Tier1_Loop --> P0 --> P1 --> P2 --> P3 --> P4 --> P5
    P5 -->|"所有skill完成"| DECIDE
    P7_SELF --> P8
    P7_FULL --> P8
    P8 --> P9
    P9 --> OUTPUT["HTML / JSON / Markdown 报告"]
```

---

## Phase 间链式依赖

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
                                                        ↓
                                              ┌───────────────────┐
                                              │   Phase 6 → Phase 7  │
                                              └───────────────────┘
                                                        ↓
                                              ┌───────────────────┐
                                              │   Phase 8 → Phase 9  │
                                              └───────────────────┘
```

## 批量 skill 遍历流程

```mermaid
flowchart TD
    START(["开始 run-test-pipeline.sh"])
    START --> PARSE["解析参数 --skills / --all-installed"]
    PARSE --> SKILL_LIST["生成技能列表 SKILLS=[]"]
    SKILL_LIST --> LOOP{"还有未测 skill?"}
    LOOP -->|"是"| TIER1_ENTRY["进入 Tier 1"]
    TIER1_ENTRY --> RUN_P0["Phase 0 (P0) for skill[i]"]
    RUN_P0 --> CHECK_P0{"phase-0-summary.json 存在?"}
    CHECK_P0 -->|"是"| RUN_P1["Phase 1 for skill[i]"]
    CHECK_P0 -->|"否"| FAIL_P0["❌ P0 未完成, 提示重新执行"]
    RUN_P1 --> CHECK_P1{"... 链式验证 ..."}
    CHECK_P1 -->|"通过"| RUN_P2["Phase 2 ..."]
    RUN_P2 --> RUN_P3
    RUN_P3 --> RUN_P4
    RUN_P4 --> RUN_P5
    RUN_P5 --> MARK_DONE["标记 skill[i] 完成"]
    MARK_DONE --> LOOP

    LOOP -->|"否, 全部完成"| DECIDE_SKILL_COUNT{"skill 数量"}
    DECIDE_SKILL_COUNT -->|"=1"| TIER2_SINGLE["Tier 2: 降级(自检+闭环)"]
    DECIDE_SKILL_COUNT -->|">=2"| TIER2_FULL["Tier 2: 全量编排+全流程"]
    
    TIER2_SINGLE --> TIER3
    TIER2_FULL --> TIER3
    
    subgraph TIER3 ["Tier 3"]
        P8["Phase 8: 合规检查"]
        P9["Phase 9: 最终报告"]
    end
    
    TIER3 --> END(["结束"])
```
