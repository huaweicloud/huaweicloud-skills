# 数据流图 — huawei-cloud-skill-creator

> 由 `scripts/generate-dataflow-diagram.sh` 自动生成 | 版本：2.0.0

## 工作流数据流

```mermaid
flowchart TD
  INPUT([/"用户：创建华为云 Skill"/])
  STEP1["Step 1：需求分析"]
  STEP2["Step 2：命名与目录"]
  STEP3["Step 3：调研 API"]
  STEP4["Step 4：生成数据流图"]
  STEP5["Step 5：生成 SKILL.md"]
  STEP6["Step 6：生成 references/"]
  STEP7["Step 7：生成 scripts/"]
  STEP8["Step 8：生成 templates/ & demo/"]
  STEP9["Step 9：质量验证"]
  OUTPUT([/"完整 Skill 包"/])

  subgraph CLI_OPS["CLI 操作"]
    CLI_OP1["hcloud {Service} --help"]
    CLI_OP2["hcloud {Service} List{Resources}"]
    CLI_OP3["hcloud {Service} {Operation} --help"]
  end

  subgraph DATA["数据源"]
    ENV[/"环境变量\nHUAWEI_ACCESS_KEY, HUAWEI_SECRET_KEY, HUAWEI_REGION"/]
    REFS["references/\nskill-spec-generic.md, naming-conventions.md"]
    TEMPLATES["templates/\nSKILL.md.template, dataflow-diagram.md.template"]
    SCRIPTS["scripts/\ngenerate-dataflow-diagram.sh, validate-skill.sh"]
  end

  INPUT --> STEP1
  STEP1 --> STEP2
  STEP2 --> STEP3
  STEP3 --> STEP4
  STEP4 --> STEP5
  STEP5 --> STEP6
  STEP6 --> STEP7
  STEP7 --> STEP8
  STEP8 --> STEP9
  STEP9 --> OUTPUT

  ENV -.-> STEP1
  REFS -.-> STEP2
  TEMPLATES -.-> STEP5
  SCRIPTS -.-> STEP4
  SCRIPTS -.-> STEP9

  STEP3 --> CLI_OPS
  CLI_OP1 -.-> STEP3
  CLI_OP2 -.-> STEP3
  CLI_OP3 -.-> STEP5
```

## 图例

| 符号 | 含义 |
|------|------|
| `([/ /])` | 起始/终止（不对称矩形） |
| `[ ]` | 处理步骤（矩形） |
| `[/ /]` | 数据存储（平行四边形） |
| `-->` | 主数据流 |
| `-.->` | 辅助/引用数据流 |

## 数据流描述

| 步骤 | 输入 | 处理 | 输出 |
|------|------|------|------|
| 1. 需求分析 | 用户请求 + 环境配置 | 确认服务、范围、触发条件 | 结构化需求 |
| 2. 命名与目录 | 需求 + 命名规范 | 按公式生成名称，创建目录结构 | Skill 目录路径 |
| 3. 调研 API | 目录 + CLI 访问 | 通过 --help 发现操作，测试只读命令 | API 操作列表 |
| 4. 生成数据流图 | 工作流步骤 + CLI 操作 | 从模板生成 Mermaid 图 | `references/dataflow-diagram.md` |
| 5. 生成 SKILL.md | API 列表 + 模板 | 用服务数据填充 SKILL.md.template | `SKILL.md` |
| 6. 生成 references/ | SKILL.md + API 数据 | 创建 iam-policies、cli-guide 等 | `references/` 目录 |
| 7. 生成 scripts/ | 工作流需求 | 创建分析/部署脚本 | `scripts/` 目录 |
| 8. 生成 templates/ & demo/ | 配置模式 | 创建 IaC/API 模板 + 示例 | `templates/` + `demo/` |
| 9. 质量验证 | 完整 skill 目录 | 运行 validate-skill.sh | 验证报告 |
