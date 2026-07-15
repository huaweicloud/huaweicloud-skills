---
name: huawei-cloud-skill-creator
version: 2.1.0
description: |
  1. Interactive requirements gathering via Socratic questioning — one question at a time, 4 service dimensions
  2. Scaffolds complete Skill directory structure with references/, scripts/, templates/, i18n/
  3. Guides through API research, dataflow diagram generation, and content creation steps
  4. Validates quality with validate-skill.sh and CLI functional testing (test-cli-commands.sh)
  5. Supports resource lifecycle testing for Skills with Create/Delete/Update operations
  Triggers include: "创建华为云Skill","新建华为云Skill","华为云skill创建器","创建 Skill","新建 Skill","skill 创建器","create skill","build skill","new skill","skill creator","scaffold a Huawei Cloud skill","wrap CLI or OpenAPI into a skill","package cloud operations into a skill","帮我创建华为云Skill","帮我新建一个Skill","封装华为云CLI为Skill","华为云Skill脚手架","帮我创建一个skill","我需要一个skill".
tags: [huawei-cloud, skill-creator, skill-development, cli, devops, interactive]
---

# Huawei Cloud Skill Creator

> ⚠️ **MANDATORY RULE: You MUST follow the interactive questioning process before creating any files.**
> Ask ONE question at a time. Wait for user response. Present summary every 5 questions.
> See [`references/usage-guide.md`](references/usage-guide.md) for detailed questioning guide.

---

## 概述 / Overview

Interactive Skill Creator for Huawei Cloud. Gathers requirements via Socratic questioning (4 dimensions: target service, functionality scope, CLI operations, trigger scenarios), then scaffolds the complete Skill directory with references, scripts, templates, i18n, and validation. Wraps Huawei Cloud CLI/OpenAPI into reusable AI Shell Skills, covering the full pipeline from requirements analysis to functional testing.

---

## 前置条件 / Prerequisites

1. **hcloud CLI** installed and authenticated
   ```bash
   hcloud --version
   hcloud configure list
   ```
2. **Node.js + npx** available
3. Basic knowledge of the target Huawei Cloud service (ECS, VPC, OBS, etc.)
4. Huawei Cloud AK/SK credentials (for resource lifecycle testing)

---

## 工作流 / Workflow

The creation process follows 4 high-level phases. See [`references/usage-guide.md`](references/usage-guide.md) for the full 11-step workflow.

```
Requirements (Interactive) → Scaffolding → Validation → Testing
```

### Phase 1: Requirements Analysis (MANDATORY — interactive)

Socratic questioning covering 4 dimensions — one question at a time:
1. **Target service** — Which Huawei Cloud service? (ECS, VPC, OBS, RDS, etc.)
2. **Function scope** — What should the Skill do? (query, diagnose, deploy, monitor)
3. **CLI operations** — Which operations? (List, Show, Create, Delete, etc.)
4. **Trigger scenarios** — When will Agent use it? (daily inspection, troubleshooting, auto-scaling)

After every 5 questions or when all dimensions covered → present summary table → wait for user confirmation.
🛑 **Do NOT proceed until user explicitly confirms.**

### Phase 2: Scaffolding

1. Name the Skill: `{platform}-{product}-{function}` (e.g., `huawei-cloud-ecs-diagnosis-workflow`)
2. Determine domain directory (compute / network / storage / database / security / monitoring / middleware / devtools / solution)
3. Create directory structure with SKILL.md, references/, scripts/, templates/, i18n/
4. Generate Mermaid dataflow diagram
5. Write SKILL.md and references (iam-policies, quality-checklist, etc.)
6. Generate scripts (validate-skill.sh, test-cli-commands.sh) and i18n translations

### Phase 3: Validation

```bash
bash scripts/validate-skill.sh {skill-path} --phase all-install
```
Validates: SKILL.md structure, frontmatter, required sections, dependencies, i18n, security patterns.

### Phase 4: Functional Testing (Mandatory: Actual Execution + CLI→SDK→API Fallback)

每条写入 SKILL.md 的指令必须实际执行验证，按 **CLI → SDK → API** 三级降级：

**CLI 执行示例：**
```bash
hcloud ECS ListFlavors --cli-region=cn-north-4 --limit=1
```

| 优先级 | 执行方式 | 失败降级条件 |
|--------|----------|-------------|
| 1st | **CLI** — hcloud 命令 | 命令不存在或参数错误 → 先检查语法修复；修复后仍失败 → 降级 |
| 2nd | **SDK** — Python huaweicloudsdk | SDK 未安装或模块缺失 → 自动安装后重试；仍失败 → 降级 |
| 3rd | **API** — curl + AK/SK v2 签名 | 网络错误或 endpoint 不可达 → 报错并建议手动验证 |

执行流程：

```
写新指令 → 尝试 CLI 执行
  ├── ✅ 成功 → 写入 SKILL.md，继续下一条
  └── ❌ 失败 → 检查是否语法问题
       ├── ✅ 语法问题 → 修复命令后重试 CLI
       └── ❌ 非语法问题 → 降级到 SDK
            ├── ✅ 成功 → 写入 SKILL.md + 备注 "(SDK verified)"
            └── ❌ 失败 → 降级到 API
                 ├── ✅ 成功 → 写入 SKILL.md + 备注 "(API verified)"
                 └── ❌ 失败 → 标记为 "⛔ 需人工验证"，记录失败详情
```

只读命令（List/Show/Get/Describe/Query）直接对真实 API 执行 `--limit=1` 验证。
变更命令（Create/Update/Delete）先做 `--help` 语法检查，然后再用 `--dry-run`（如果支持）或最小权限参数验证参数格式，**最终执行必须经用户确认**。

### REST API 降级规则（强制性）

**当降级到 3rd API（REST API）时，严禁 Agent 自行猜测/构造 API 路径。** REST API 的 endpoint、method、path、请求体必须由用户确认提供。

```
降级到 API → 用户确认
  │
  ├── Agent 询问：确认 API 端点 → 用户提供 {HTTP方法} {endpoint}{path}
  │   示例：用户确认 "POST https://bss.cn-north-4.myhuaweicloud.com/v2/promotions/benefits/activate-coupons"
  │
  ├── Agent 使用用户提供的 API 执行验证 → 通过 → 写入 SKILL.md + 备注 "(API verified, endpoint confirmed by user)"
  │
  └── Agent 使用用户提供的 API 执行验证 → 失败 → 询问用户是否需要调整端点，否则标记 ⛔ 需人工验证
```

**执行细则：**

| 场景 | Agent 行为 |
|------|------------|
| CLI/SDK 均失败，需降级到 API | **必须问用户**："请提供此操作的 REST API 端点（HTTP方法 + URL）" |
| 用户提供了端点 | 使用用户提供的端点实际执行验证 |
| 用户不确定/无法提供 | 标记为 `⛔ 需人工验证`，绝不自行构造虚构的 API 路径 |
| SKILL.md 中已有 API 命令 | 标注 `⚠ 此 API 端点由用户提供，请确认其有效性` |

```bash
# CLI: 直接执行
bash scripts/test-cli-commands.sh {skill-path} --executor cli

# SDK: 降级到 Python SDK（自动安装依赖）
bash scripts/test-cli-commands.sh {skill-path} --executor sdk

# API: 降级到 curl + AK/SK 签名
bash scripts/test-cli-commands.sh {skill-path} --executor api
```

---

## 核心命令 / Core Commands

| Command | Purpose |
|---------|---------|
| `bash scripts/validate-skill.sh {path} --phase all-install` | Full installation & structure validation |
| `bash scripts/validate-skill.sh {path} --phase i18n` | i18n directory validation |
| `bash scripts/test-cli-commands.sh {path} [--region <region>]` | CLI functional test + test report |
| `bash scripts/generate-dataflow-diagram.sh {path} [--output <path>]` | Generate Mermaid dataflow diagram |

---

## 参数确认 / Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `{skill-path}` | Yes | Target Skill directory path | `./skills/compute/huawei-cloud-ecs-manage` |
| `{region}` | No | Huawei Cloud region | `cn-north-4` (default) |
| `--output` | No | Output path for generated files | `./references/dataflow-diagram.md` |

---

## KooCLI命令格式标准 / KooCLI Command Format

```bash
hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | Uppercase PascalCase | `ECS`, `VPC`, `IAM` |
| Operation name | PascalCase | `ListServers`, `ShowServer` |
| Region param | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple param | `--key=value` | `--server_id=xxx` |
| Indexed param | `--key.1=value1` | `--servers.1.id=xxx` |
| Nested param | `--key.sub_key=value` | `--config.protocol=vnc` |

See [`references/cli-installation-guide.md`](references/cli-installation-guide.md) for full CLI setup guide.

---
## 设计原则 / Design Principles

- **Concise SKILL.md, verbose in references** — SKILL.md body must be concise (< 250 lines). Detailed step-by-step instructions, edge-case tables, and long examples go into `references/` files. Link to them from SKILL.md.
- **Spec-first** — All generated Skills must conform to `references/skill-spec-generic.md`
- **Description-driven triggering** — description must include `"Triggers include:"` clause
- **Security first** — No hardcoded AK/SK, confirm before write operations, dry-run for high-risk ops
- **Cost transparency** — Generated Skills must include cost estimation logic
- **Least privilege** — iam-policies.md provides minimum permission policy JSON
- **Idempotent first** — Prefer List/Show/Get read-only operations
- **i18n support** — Default `i18n/zh-CN/SKILL_CN.md` included
- **Functional testing** — Structure validation → CLI command testing → resource lifecycle test
- **每条指令必须实际执行验证** — Agent 写入 SKILL.md 的每一条 hcloud 命令，在写入过程中必须用 `CLI → SDK → API` 三级降级策略实际调用验证，不能只写不验
- **写指令即时验证** — 每写完一条指令，立即尝试执行。执行成功 → 写入 SKILL.md；执行失败 → 先检查语法并修复，语法无问题则执行降级策略
- **三级降级策略** — 尝试顺序：**CLI**（hcloud 命令）→ **SDK**（Python huaweicloudsdk）→ **API**（curl + AK/SK 签名）。上一级失败且非语法问题则降级到下一级

---

## Edge Cases / 边界情况

| Scenario | Handling |
|----------|----------|
| User says "create now" without answering questions | Remind: requirements must be gathered first. Start questioning. |
| User answers vaguely | Use concrete examples: e.g., "Do you want a one-command list of all running servers?" |
| API operation not found in CLI | Check Huawei Cloud OpenAPI docs for alternative endpoints |
| Resource creation fails during test | Analyze error (permission/quota/param), fix and retry |
| Resource release fails | Retry 3 times, if still failing tell user to clean up manually |
| User refuses resource lifecycle test | Fall back to --help syntax validation only, note "resource test skipped" in report |

---

## 验证方法 / Verification Method

### Phase 3: Quality Verification
```bash
bash scripts/validate-skill.sh {skill-path} --phase all-install
# Expected: All required checks PASS
```

### Phase 4: CLI Functional Test (actual execution required)

必须按 CLI → SDK → API 三级执行验证：

```bash
# 1st: CLI 直接执行（必须有真实结果）
bash scripts/test-cli-commands.sh {skill-path} --executor cli

# 2nd: SDK 降级（CLI 不可用时）
bash scripts/test-cli-commands.sh {skill-path} --executor sdk

# 3rd: API 降级（curl + 签名）
bash scripts/test-cli-commands.sh {skill-path} --executor api
```

**验证规则：**
- 每一条写入 SKILL.md 的指令都经过至少一级实际执行验证 ✅
- CLI → SDK → API 依次降级，只有当前级失败且非语法问题才降级
- 语法问题（如参数名错误）立即修复，不降级
- 最终降级到 API 仍失败 → 标记 `⛔ 需人工验证`
- 阅读只命令（List/Show/Get）必须有实时 API 返回数据
- 变更命令需要用户明确确认后才执行
- 报告生成在 `references/test-report.md`

### Resource Lifecycle Test (if applicable)
Flow: Plan → Credentials → Create → Test → Release → Report
See [`references/usage-guide.md`](references/usage-guide.md) for details.

---

## 参考文档 / References

- [`references/usage-guide.md`](references/usage-guide.md) — Complete 11-step workflow + resource lifecycle test
- [`references/skill-spec-generic.md`](references/skill-spec-generic.md) — Full Skill specification
- [`references/naming-conventions.md`](references/naming-conventions.md) — Naming conventions
- [`references/quality-checklist.md`](references/quality-checklist.md) — Quality checklist
- [`references/cli-installation-guide.md`](references/cli-installation-guide.md) — CLI install & setup
- [`references/iam-policies.md`](references/iam-policies.md) — Least-privilege IAM policies
- [`references/verification-method.md`](references/verification-method.md) — Verification methods
- [`references/dataflow-diagram.md`](references/dataflow-diagram.md) — Mermaid dataflow diagram
- [`references/acceptance-criteria.md`](references/acceptance-criteria.md) — Acceptance criteria
- [`references/related-commands.md`](references/related-commands.md) — Command quick reference
- [`templates/SKILL.md.template`](templates/SKILL.md.template) — SKILL.md template
- [`templates/iam-policies.md.template`](templates/iam-policies.md.template) — IAM policy template
- [`templates/dataflow-diagram.md.template`](templates/dataflow-diagram.md.template) — Dataflow diagram template
- [`templates/test-report.md.template`](templates/test-report.md.template) — Test report template
- [`scripts/test-cli-commands.sh`](scripts/test-cli-commands.sh) — CLI functional test script

## Authentication

| Method | Use Case | Best Practice |
|--------|----------|---------------|
| AK/SK env vars | Development | Set `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` |
| Temp credentials | Production | Use STS temp AK/SK + SecurityToken |
| IAM role | Cloud env | Bind IAM role for automatic auth |

### User-Agent

```bash
export HCLOUD_USER_AGENT=HuaweiCloud-Agent-Skills
```
