# Data Flow Diagram — Huawei Cloud Skill Creator v2

> Six-phase strict pipeline for Huawei Cloud skill creation.

## Six-Phase Pipeline Data Flow

```mermaid
flowchart TD
  START([/"User Request"/])
  
  P1["Phase 1: 需求分析\nSocratic Q&A"]
  P1S[("phase-1-summary.json")]
  
  P2["Phase 2: 技术调研\nCLI→SDK→API"]
  P2S[("phase-2-summary.json")]
  
  P3["Phase 3: 文档生成\nSKILL.md + references"]
  P3S[("phase-3-summary.json")]
  
  P4["Phase 4: 测试准备\n用例生成 + 执行"]
  P4S[("phase-4-summary.json")]
  
  P5["Phase 5: 详细测试\n资源生命周期"]
  P5S[("phase-5-summary.json")]
  
  P6["Phase 6: 清理 + 合规\n资源清理 + 规范检查"]
  P6S[("phase-6-summary.json")]
  
  FINAL([/"Skill Creation Complete"/])
  
  START --> P1
  P1 --> P1S
  P1S --> P2
  P2 --> P2S
  P2S --> P3
  P3 --> P3S
  P3S --> P4
  P4 --> P4S
  P4S --> P5
  P5 --> P5S
  P5S --> P6
  P6 --> P6S
  
  P6S -->|"All 6 phases complete"| FINAL
  P6S -->|"Phase N missing"| P_N["Re-execute from Phase N"]
  P_N --> P_N_S[("phase-N-summary.json\nregenerated")]
  P_N_S --> P6S

  subgraph TECH["Technical Research (Phase 2)"]
    CLI_CHECK["hcloud CLI 检查"]
    SDK_CHECK["huaweicloudsdk 检查"]
    API_CHECK["用户提供 API 端点"]
    CLI_CHECK -->|"✅"| CLI_OK["CLI 模式"]
    CLI_CHECK -->|"❌"| SDK_CHECK
    SDK_CHECK -->|"✅"| SDK_OK["SDK 模式"]
    SDK_CHECK -->|"❌"| API_CHECK
    API_CHECK -->|"✅"| API_OK["API 模式"]
    API_CHECK -->|"❌"| BLOCKED["⛔ 需人工验证"]
  end

  subgraph GEN["Generation (Phase 3)"]
    GEN_CLI["生成 hcloud 命令"]
    GEN_SDK["生成 Python SDK 脚本"]
    GEN_API["生成 curl API 调用"]
  end

  CLI_OK --> GEN_CLI
  SDK_OK --> GEN_SDK
  API_OK --> GEN_API
```

## Diagram Legend

| Symbol | Meaning |
|--------|---------|
| `([/ /])` | Start / End |
| `[ ]` | Process step |
| `( )` | Data store (summary JSON) |
| `-->` | Primary data flow |
| `-.->` | Secondary flow |

## Phase Summary Files

| File | Producer | Consumer | Content |
|------|----------|----------|---------|
| `phase-1-summary.json` | Phase 1 | Phase 2 | User-confirmed requirements |
| `phase-2-summary.json` | Phase 2 | Phase 3 | CLI/SDK/API research results |
| `phase-3-summary.json` | Phase 3 | Phase 4 | Generated file list |
| `phase-4-summary.json` | Phase 4 | Phase 5 | Test cases + results |
| `phase-5-summary.json` | Phase 5 | Phase 6 | Detailed test results |
| `phase-6-summary.json` | Phase 6 | — | Final report + compliance |
