---
name: huawei-cloud-skill-creator
version: 1.0.0
description: |
  1. 创建、构建、脚手架化和打包华为云 (华为云) AI Agent Skill
  2. 生成符合规范的 SKILL.md、references/、scripts/、templates/、i18n/ 目录结构
  3. 为新 Skill 生成数据流图和验证报告
  4. 将 hcloud CLI 或 OpenAPI 操作封装为可复用的 Skill 包
  5. 按照华为云质量和安全标准验证生成的 Skill
  触发场景包括："创建华为云Skill","新建华为云Skill","华为云skill创建器","创建 Skill","新建 Skill","skill 创建器","create skill","build skill","new skill","skill creator","scaffold a Huawei Cloud skill","wrap CLI or OpenAPI into a skill","package cloud operations into a skill","帮我创建华为云Skill","帮我新建一个Skill","封装华为云CLI为Skill","华为云Skill脚手架"。
tags: [huawei-cloud, skill-creator, skill-development, cli, devops]
---

# 华为云 Skill 创建器

基于 `skill-spec-generic.md` 规范，创建符合华为云标准的 AI Agent Skill。

> **规范文档：** [`references/skill-spec-generic.md`](../references/skill-spec-generic.md) — 所有 Skill 必须遵循的完整规范。

## 前置条件

> 首次使用请阅读 [`references/cli-installation-guide.md`](../references/cli-installation-guide.md)。

- 已安装 CLI 并完成认证配置
- 通过环境变量 `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` 获取 AK/SK
- IAM 用户具备所需权限（参见 [`references/iam-policies.md`](../references/iam-policies.md)）
- 已配置默认区域（如 `cn-north-4`）

## 核心命令

| 命令 | 说明 |
|------|------|
| `hcloud ECS ListServers --cli-region=cn-north-4` | 列出 ECS 实例 |
| `hcloud VPC ListVpcs --cli-region=cn-north-4` | 列出 VPC |
| `hcloud OBS ListBuckets --cli-region=cn-north-4` | 列出 OBS 桶 |
| `hcloud IAM ListUsers --cli-region=cn-north-4` | 列出 IAM 用户 |

## 参数

| 参数 | 必需 | 说明 | 示例 |
|------|------|------|------|
| `--cli-region` | 是 | 区域 ID | `cn-north-4` |
| `--project_id` | 否 | 项目 ID | `0a2663967980d2962f94c0120b96c98b` |
| `--limit` | 否 | 最大返回数量 | `10` |
| `--offset` | 否 | 分页偏移 | `0` |

## 概述

Skill 是 AI Agent 的"领域专长包"——一个结构化的指令文件夹，为 Agent 提供特定任务的专业知识和工作流。本 Skill 用于创建符合华为云标准的其他 Skill，确保每个生成的 Skill 具有完整的目录结构、规范的 SKILL.md、详尽的参考文档和可复用的脚本。

## 设计原则

**原则 1**：每个 Skill 应解决一个特定的 Agent 使用场景。追求"Agent 需要时即可用"，而非面面俱到。

**原则 2**：Skill 应提供领域完整性。当用户需要该领域能力时，Agent 可在 Skill 内完成完整工作流，无需频繁切换上下文。

**原则 3**：Skill 内容与 Agent 能力是协作关系。Skill 提供领域知识和工作流；Agent 负责推理和执行。

## 工作流

当用户请求创建新 Skill 时，按以下步骤执行：

### 步骤 1：需求分析（苏格拉底式询问）

**本步骤采用苏格拉底式（启发式）追问方法。** 不要一次性抛出所有问题。而是每次只问一个问题，基于用户的上一个回答进行深入引导。目标是帮助用户将模糊的需求梳理为具体、可操作的需求条目。

**询问节奏：**
- **一次只问一个问题** — 等用户回答后再问下一个
- 每个问题应基于上一个回答展开（追问 / 深挖）
- 覆盖 4 个维度：服务/产品 → 功能范围 → CLI/API 操作 → 触发场景

**维度 1 — 目标服务/产品：**
- "你想封装哪个华为云服务？比如 ECS（弹性云服务器）、VPC（虚拟私有云）、OBS（对象存储）、RDS（关系型数据库）等。如果不太确定，可以描述一下你的使用场景，我来帮你匹配对应的服务。"

**维度 2 — 功能范围：**
- "你希望这个 Skill 主要做什么？比如：查询管理、故障诊断、自动部署、监控告警、还是其他功能？可以具体描述一下你想要的场景。"

**维度 3 — CLI / API 操作：**
- "你大概需要用到哪些操作？比如查询列表（List）、查看详情（Show/Get）、创建（Create）、删除（Delete）、启动/停止（Start/Stop）？如果你不确定具体命令，描述你要完成的任务，我来帮你梳理。"

**维度 4 — 触发场景：**
- "在什么场景下 Agent 会用到这个 Skill？比如日常巡检、故障排查、自动扩缩容？这会影响 Skill 的描述和触发词设计。"

**每 5 次询问的总结确认节点：**
每完成 **5 次询问**（即大致覆盖完 4 个维度加一次追问），Agent 必须以结构化表格形式呈现已收集的所有需求，让用户确认：

```markdown
📋 **需求总结（第 N 轮）**

| 维度 | 内容 |
|------|------|
| 目标服务/产品 | ECS（弹性云服务器） |
| 功能范围 | 实例查询、创建、启停、删除 |
| CLI/API 操作 | ListServers, ShowServer, CreateServers, StartServer, StopServer, DeleteServer |
| 触发场景 | 日常运维、批量启停、资源扩容 |
| 是否涉及成本 | 是（创建/删除实例会产生费用） |

**以上是你目前提供的需求信息。请问：**
1. **是否确认**这些就是你需要的功能？
2. **还需要补充或修改什么吗？**
```

- ✅ **如果用户确认** → 进入步骤 2（命名与目录）
- ❌ **如果用户拒绝或要求修改** → 清零当前进度，从用户指出的问题出发，开始**新一轮苏格拉底式询问**。新轮次从有问题的维度开始追问，而非从头机械重复。
- **如果用户提供的信息足够明确，提前完成所有维度的澄清** → 也可提前生成总结让用户确认，不必硬等 5 次询问。

**追问技巧：**
- 如果用户说"管理 ECS" → 追问"你具体想管理哪些方面？查询状态、创建实例、还是启停操作？"
- 如果用户说"帮我看看能不能做这个" → 追问"这个场景下，你希望最终得到什么结果？比如一份报告、一个自动化的流程、还是一个监控工具？"
- 如果用户回答模糊 → 用具体例子引导："比如说，你想不想做到一键列出所有运行中的服务器？"
- **避免同时问多个问题** — "一次只问一个，等用户回答后再深入"

### 步骤 2：命名与目录

1. 使用 `{platform}-{product}-{function}` 公式生成 Skill 名称
   - platform 固定为 `huawei-cloud`
   - product 为服务缩写（ecs、vpc、obs、rds、iam、cce 等）
   - function 为能力描述（manage、diagnosis-workflow、deploy 等）
   - 示例：`huawei-cloud-ecs-diagnosis-workflow`

2. 确定领域目录（compute / network / storage / database / security / monitoring / middleware / devtools / solution），参见 [`references/naming-conventions.md`](../references/naming-conventions.md)

3. 创建目录结构：

```text
{domain}/{skill-name}/
├── SKILL.md                   # 必需：YAML Frontmatter + Markdown 指令
├── i18n/                      # 推荐：国际化
│   └── zh-CN/                 # 推荐：简体中文（默认）
│       └── SKILL_CN.md        # 推荐：SKILL.md 中文版
├── references/                # 推荐：参考文档（按需加载）
│   ├── dataflow-diagram.md    # 必需：Mermaid 数据流图
│   ├── cli-installation-guide.md
│   ├── iam-policies.md
│   ├── verification-method.md
│   ├── acceptance-criteria.md
│   └── related-commands.md
├── scripts/                   # 推荐：可执行脚本
│   └── {script-name}
├── templates/                 # 可选：配置/模板文件
│   └── {template-name}
└── demo/                      # 可选：示例数据
    └── example.json
```

### 步骤 3：API 调研

使用 CLI 帮助标志发现可用操作和参数定义（如 `ECS --help`、`ECS ListServers --help`）。

```bash
# 测试只读操作（幂等，可安全重复）
hcloud ECS ListServers --cli-region={region}
```

若 CLI 未注册对应 API，请查阅华为云 OpenAPI 文档获取方法、路径、参数和权限信息。

### 步骤 4：生成数据流图

每个 Skill **必须**在 `references/dataflow-diagram.md` 中包含 Mermaid `flowchart` 图，展示完整工作流。

```bash
bash scripts/generate-dataflow-diagram.sh {skill-path} --output={skill-path}/references/dataflow-diagram.md
```

或手动使用 [`templates/dataflow-diagram.md.template`](../templates/dataflow-diagram.md.template)。要求：Mermaid flowchart 语法、输入到输出的工作流、CLI 操作子图、数据源子图、主流程 (`-->`) 与次流程 (`-.->`)、图例 + 数据流描述表（步骤 | 输入 | 处理 | 输出）。

### 步骤 5：生成 SKILL.md

使用 [`templates/SKILL.md.template`](../templates/SKILL.md.template)。必须包含：

**YAML Frontmatter：** `name`（必需，遵循命名公式）、`description`（必需，须包含 **"Triggers include:"** 子句及所有触发场景用于 Agent 路由）、`tags`（3-8 项）、`version`（SemVer）。

**正文章节：**

| 章节 | 必需 | 内容 |
|------|------|------|
| Overview | 是 | 背景、Skill 定位 |
| Prerequisites | 推荐 | CLI 安装、AK/SK 配置、IAM 权限 |
| Main Steps | 是 | 核心工作流 + 代码示例 |
| Edge Cases | 推荐 | 常见错误、异常处理 |
| Verification | 推荐 | 操作成功标准 |
| References | 推荐 | 链接到 references/ |

**编写要求：** 每个步骤有明确的 CLI 命令；关键参数有配置说明；每个操作注明所需权限；提供 3-5 个典型使用示例；链接到 references/ 中的详细文档。CLI/脚本**绝不嵌入 AK/SK**；使用环境变量或 `{placeholder}` 占位符。正文应控制在 500 行以内。

### 步骤 6：生成 references/

| 文件 | 必需 | 内容 |
|------|------|------|
| `dataflow-diagram.md` | 是 | Mermaid 数据流图 |
| `cli-installation-guide.md` | 推荐 | CLI 安装与初始化 |
| `iam-policies.md` | 是 | 所需 API Actions + 最小权限策略 JSON |
| `verification-method.md` | 推荐 | 操作验证方法 |
| `acceptance-criteria.md` | 推荐 | 验收标准 |
| `related-commands.md` | 按需 | 命令速查 |

使用 [`templates/iam-policies.md.template`](../templates/iam-policies.md.template) 和 [`templates/cli-installation-guide.md.template`](../templates/cli-installation-guide.md.template) 生成。每个参考文件聚焦一个主题；添加简要头部；大文件（>300 行）添加目录；使用 `{placeholder}` 表示变量；代码块须指定语言类型。

### 步骤 7：生成 scripts/（按需）

**脚本类型：**

| 类型 | 用途 | 示例 |
|------|------|------|
| 分析 | 解析 CLI 输出进行自动分析 | `analyze-ingress-offline.sh` |
| 部署 | 编排多步 CLI 操作 | `deploy-folder.mjs` |
| 数据处理 | 处理 CLI JSON 输出 | `get_logs.py` |
| 工具 | 共享函数复用 | `credentials.py`、`validation.py` |

**脚本编写要求：**
1. 使用有意义的命名，按功能命名
2. Shell 脚本以 `#!/bin/bash` 开头，Python 以 `#!/usr/bin/env python3` 开头
3. 绝不硬编码 AK/SK 或密钥；使用环境变量
4. 脚本应兼容多个 CLI 版本
5. 提供参数校验和错误处理
6. Python 脚本目录需要 `__init__.py`
7. Node.js 脚本使用 `.mjs` 扩展名和 ES Modules

### 步骤 8：生成 templates/ 和 demo/（按需）

- `templates/`：配置模板（IaC 模板如 Terraform/CloudFormation、API 请求 JSON/YAML 模板、报告/通知 Markdown 模板）
- `demo/`：示例数据（请求/响应示例、配置示例、测试数据）

### 步骤 9：生成 i18n/

每个 Skill **应该**包含 `i18n/` 目录以支持国际化。默认创建简体中文 locale：

1. 创建 `i18n/zh-CN/` 目录
2. 创建 `i18n/zh-CN/SKILL_CN.md` — SKILL.md 的中文翻译

**SKILL_CN.md 要求：**
- 与 SKILL.md 相同的 YAML Frontmatter 结构（name、description、tags、version）
- `description` 字段须用中文书写，包含中文触发短语（如"触发场景包括:"）
- 正文内容翻译为简体中文
- CLI 命令和代码块保持英文（不翻译命令）
- 技术术语可在括号中保留英文（如"弹性云服务器 (ECS)"）

使用 [`templates/i18n-zh-CN-SKILL_CN.md.template`](../templates/i18n-zh-CN-SKILL_CN.md.template) 生成。

**其他 locale**（可选）：按相同模式创建其他语言：
- `i18n/en-US/SKILL_EN.md` — 美式英语
- `i18n/ja-JP/SKILL_JA.md` — 日语
- `i18n/{locale}/SKILL_{LANG}.md` — 其他 locale

### 步骤 10：质量验证

**⚠️ 必须先完成本步骤，再进入步骤 11（功能测试）。**

使用 [`scripts/validate-skill.sh`](../scripts/validate-skill.sh) 进行验证：

```bash
bash scripts/validate-skill.sh {skill-path}
```

验证项详见 [`references/quality-checklist.md`](../references/quality-checklist.md) 和 [`references/acceptance-criteria.md`](../references/acceptance-criteria.md)。包含 i18n 目录和 `zh-CN/SKILL_CN.md` 检查。

**验证通过后 → 必须进入步骤 11（功能测试），不得跳过。**

### 步骤 11：功能测试（MANDATORY — 必须执行）

**🔴 强制规则：步骤 10 验证完成后，必须执行本步骤。不得在未进行功能测试的情况下声称 Skill 创建完成。**

对所有 CLI 命令执行自动化功能测试：

```bash
bash scripts/test-cli-commands.sh {skill-path}
```

该脚本会自动：
1. 从 SKILL.md 和 references/ 中提取所有 `hcloud` 命令
2. 对每条命令执行 `--help` 语法验证（无副作用）
3. 对只读操作（List/Show/Get/Describe/Query）执行 `--cli-region=<region> --limit=1` 实时调用
4. 对变更操作（Create/Update/Delete/Start/Stop）仅做 `--help` 验证，**绝不实际执行**
5. 生成 `references/test-report.md`

自动化脚本也集成在 `scripts/validate-skill.sh --phase functional-test` 中。

Step 10 结构验证完成后，对 Skill 中涉及的所有 CLI 命令、API 调用或 SDK 操作进行**功能测试**。目标是发现接口变更、参数错误、端点失效或权限缺失。

**凭证与隐私提醒：**
在执行任何功能测试之前，检查 Skill 是否引用到以下凭证信息（AK/SK、Token、密码、API Key、私钥、或其他敏感数据）。如果涉及，**必须提醒用户**提供所需凭证：

```
⚠️ 需要凭证：该 Skill 使用了以下凭证：
   - {凭证名称/用途}
   - {例如：HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY}
   - {例如：OBS 桶读写 Token}

   请提供所需凭证。如果不想暴露敏感凭证，我可以跳过功能测试，
   仅执行 dry-run 或 help-only 验证。
```

- ✅ 用户提供凭证 → 执行功能测试
- ❌ 用户拒绝 → 跳到步骤 12（完成），跳过功能测试
- 🔒 凭证为私钥/证书 → **绝不记录或展示其内容**，仅通过环境变量或临时文件使用

**测试类型（只测 Skill 实际用到的）：**

| 类型 | 测试方法 | 示例 |
|------|----------|------|
| CLI 语法 | `hcloud {SERVICE} {OPERATION} --help`（dry run，无副作用） | `hcloud ECS ListServers --help` |
| CLI 参数 | 对每个命令运行 `--help` 验证参数 | `hcloud ECS CreateServers --help` |
| CLI 只读（安全） | 查询操作（List/Show/Get）— 实际执行 | `hcloud ECS ListServers --cli-region=cn-north-4 --limit=1` |
| API 端点 | 如果引用了 SDK，验证端点格式 | 检查 `{service}.{region}.myhuaweicloud.com` |
| SDK 方法 | 验证方法签名与文档一致 | 查看 SDK 文档或 `pydoc` |
| 权限检查 | 执行最小只读查询验证 IAM | `hcloud ECS ListServers --cli-region=cn-north-4 --limit=1` |
| 语义验证 | 检查返回的字段名/值是否与预期含义一致 — 例如名为 `available_amount` 的字段应代表所剩余额，而非充值总额 | 实时查询 + 人工审核 |
| 数据合理性 | 抽查数字字段的合理性："余额"不应比预期大几个数量级；列表数量应符合实际 | 实时查询 + 人工审核 |

**测试规则：**
1. **`--help` 优先** — 未经用户确认，绝不执行 Create/Update/Delete/Start/Stop 命令
2. **只读优先** — 只实际执行 List/Show/Get 操作；所有变更操作仅测试语法
3. **`--limit=1`** — 列表查询限制返回数，绝不拉取全量数据
4. **失败诊断**：参数名错误（CLI 版本差异）、权限不足（检查 IAM）、服务未开通（检查服务开通状态）、端点不可达（检查区域/网络）
5. **实时数据语义验证** — 当 Skill 查询财务/用量/指标类数据时，检查返回的 JSON 字段含义是否与 Skill 的意图一致。常见陷阱：
   - `total_amount` / `recharge_amount` 被误当作 `balance` / `available_amount`
   - `quota` 的计量单位与文档不符（如 bytes 写成了 GB）
   - `status` 字段使用了未文档化的枚举值
   - 多个费用相关字段同时存在但未明确标注；应查询官方文档或询问用户确认哪个是真正的目标字段
   - 日期/时间字段格式与预期不一致（时间戳 vs ISO 字符串 vs 本地化日期）
6. **记录测试结果** — 保存到生成 Skill 的 `references/test-report.md`

**语义模糊时的处理流程：**

当实时查询返回多个可能代表目标值的字段时，**不要盲目猜测**：

1. 查阅官方 API 文档确认字段定义
2. 交叉对比字段值：如果 `total_amount=5000` 而 `available_amount=1234.56`，则 `available_amount` 更像是所剩余额
3. 如果仍有歧义，**询问用户**哪个是正确字段：
   ```
   ⚠️ 检测到语义模糊字段：查询返回了以下可能代表"余额"的候选字段：
      - total_amount: 5000.00（可能为充值总额）
      - available_amount: 1234.56（可能为可用余额）
      - cash_balance: 1000.00（可能为现金余额）
   
   请问哪个字段代表实际所剩余额？
   ```
4. 将生成的 Skill 更新为使用正确的字段名，并在 SKILL.md 中添加确认后的语义说明

**测试报告格式（`references/test-report.md`）：**

```markdown
# 功能测试报告

| 操作 | 测试类型 | 结果 | 备注 |
|------|----------|------|------|
| `hcloud ECS ListServers --cli-region=cn-north-4 --limit=1` | CLI 只读 | ✅ 通过 | 返回 2 台服务器 |
| `hcloud ECS CreateServers --help` | CLI 语法 | ✅ 通过 | 所有参数已验证 |
| `hcloud ECS DeleteServer --help` | CLI 语法 | ✅ 通过 | 所有参数已验证 |

**汇总：** 3/3 通过 — 可进入用户测试
**环境：** {cli-version}, {region}
**测试者：** Skill Creator (huawei-cloud-skill-creator)
```

> 也可使用模板文件 `templates/test-report.md.template` 生成报告。

**测试失败处理：**
- 参数不匹配 → 回到步骤 3（API 调研），修正 SKILL.md 中的 CLI 命令
- 权限拒绝 → 在 `references/iam-policies.md` 中补充所需权限
- 服务不可用 → 在 SKILL.md 前置条件中注明（如"需要已开通 ECS 服务"）
- SDK 方法不存在 → 更新 SKILL.md 中 SDK 引用为正确的 API 版本

### 资源型 Skill 的完整生命周期测试

> **当创建的 Skill 包含 Create/Delete 等资源创建/销毁操作时，不得只做 `--help` 测试跳过。必须执行以下完整流程。**

#### 流程概览

```
描述测试计划 → 确认凭证 → 创建资源 → 测试功能 → 释放资源 → 生成报告
```

#### 详细步骤

**Step A: 描述测试计划**

向用户说明将要进行的测试：

```markdown
📋 **功能测试计划 — {skill-name}**

本 Skill 包含资源变更操作，需要进行完整生命周期测试：

| 操作 | 测试资源 | 测试后动作 |
|------|----------|-----------|
| `hcloud XXX Create{Resource} --...` | 创建 1 个最小规格 {resource} | ✅ 测试完成后删除 |
| `hcloud XXX Show{Resource} --...` | 查询刚创建的资源 | — |
| `hcloud XXX Delete{Resource} --...` | 删除测试资源 | — |

**预计费用：** 测试期间按需计费，约 {预估金额}，测试完成后立即释放。
**预计耗时：** 约 2-5 分钟。

是否开始测试？(yes/no)
```

- ✅ 用户确认 → 继续
- ❌ 用户拒绝 → 跳过资源测试，仅做 `--help` 语法验证

**Step B: 确认凭证**

检查环境变量，如未设置则询问用户：

```bash
# 检查当前环境
echo "HUAWEI_ACCESS_KEY=${HUAWEI_ACCESS_KEY:-未设置}"
echo "HUAWEI_SECRET_KEY=${HUAWEI_SECRET_KEY:-未设置}"
```

如未设置：

```markdown
⚠️ **需要华为云 AKSK 凭证**

请提供以下信息之一：
1. 设置环境变量后告诉我继续：
   ```
   export HUAWEI_ACCESS_KEY=your_access_key
   export HUAWEI_SECRET_KEY=your_secret_key
   ```
2. 直接提供 AKSK（我将设置到环境变量中，**不会记录到文件或日志**）

或者输入 "skip" 跳过资源测试。
```

> 🔒 **安全规则：** AKSK 仅用于当前会话的环境变量，绝不写入文件、日志或 SKILL.md。用户拒绝提供 → 回退到仅 `--help` 语法测试。

**Step C: 创建测试资源**

使用最小规格创建测试资源：

```bash
hcloud {SERVICE} Create{Resource} --cli-region={region} --name=test-skill-verify-{timestamp} --flavor={min-spec} ...
```

记录返回的资源 ID。验证创建成功：

```bash
hcloud {SERVICE} Show{Resource} --cli-region={region} --{resource}_id={created_id}
```

**Step D: 测试功能**

对创建的测试资源执行 Skill 中定义的功能测试（List/Show/启停等只读操作），验证命令能正确执行。

**Step E: 释放测试资源**

测试完成后，**必须**清理测试资源：

```bash
hcloud {SERVICE} Delete{Resource} --cli-region={region} --{resource}_id={created_id}
```

验证资源已释放：

```bash
hcloud {SERVICE} List{Resource} --cli-region={region} --name=test-skill-verify-{timestamp} --limit=1
# 期望结果：返回空列表
```

> ⚠️ **强制规则：** 无论测试是否成功，都必须执行资源释放。如果 Delete 操作失败，再次尝试并告知用户手动确认。

**Step F: 生成测试报告**

将资源生命周期测试结果追加到 `references/test-report.md`：

```markdown
## 资源生命周期测试

| 阶段 | 操作 | 结果 | 详情 |
|------|------|------|------|
| 创建 | `hcloud ECS CreateServers ...` | ✅ 通过 | 资源 ID: xxx |
| 测试 | 验证功能 | ✅ 通过 | 所有操作正常 |
| 释放 | `hcloud ECS DeleteServer ...` | ✅ 通过 | 资源已删除 |
| 凭证 | AKSK | ✅ 已确认 | 用户提供环境变量 |

**生命周期状态：** ✅ 测试资源已全部释放
```

#### 注意事项

| 场景 | 处理方式 |
|------|----------|
| API 不支持最小规格 | 使用该服务允许的最小规格创建 |
| 创建失败 | 分析错误信息（权限/配额/参数），修复后重试 |
| 释放失败 | 重试 3 次，仍失败则告知用户手动清理 |
| 用户不想做资源测试 | 回退到 `--help` 语法验证，在报告中注明"资源测试已跳过" |
| 用户提供了错误的 AKSK | 提示认证失败，让用户重新提供 |
| 测试中断 | 告知用户未释放的资源 ID 和区域，建议手动清理 |

---

## 华为云 CLI 命令格式

```bash
# 通用格式
hcloud ECS ListServers --cli-region=cn-north-4 --param1=value1 --param2=value2

# 具体示例
hcloud ECS ListServers --cli-region=cn-north-4

# 幂等操作（可安全重复）
hcloud ECS ShowServer --cli-region=cn-north-4 --server_id={instance_id}

# 嵌套参数
hcloud ECS CreateServers --cli-region=cn-north-4 --os-start.servers.1.id={id1}
```

| 特性 | 说明 | 示例 |
|------|------|------|
| 服务名 | 大写 PascalCase | `ECS`、`VPC`、`IAM` |
| 操作名 | PascalCase | `ListServers`、`ShowServer` |
| 区域参数 | `--cli-region=<值>` | `--cli-region=cn-north-4` |
| 简单参数 | `--key=value` | `--server_id=xxx` |
| 索引参数 | `--key.1=value1` | `--servers.1.id=xxx` |
| 嵌套参数 | `--key.sub_key=value` | `--config.protocol=vnc` |

## 安全操作

**必须遵循：**
- 密钥 (AK/SK) 通过环境变量获取，绝不以明文参数传入
- 执行创建/更新/删除操作前必须确认用户意图
- 优先使用只读查询 (List/Show/Get) 验证环境状态
- 高风险操作前使用预演模式 (`--dry-run`)

**必须避免：**
- 在明文命令中暴露敏感凭据
- 未经确认执行破坏性操作
- 使用已废弃的 API 版本
- 忽略错误码和返回状态

## 费用确认（生成的 Skill）

> **重要：** 当生成的 Skill 涉及云资源（ECS、OBS、RDS、CCE 等）时，生成的 Skill **必须**包含费用确认逻辑。在执行任何资源变更操作前，Agent 必须提醒用户可能产生的费用，并等待用户明确确认。

**生成的 Skill 必须包含：**

1. SKILL.md 中的 `## Cost Confirmation` 章节（参见 `templates/SKILL.md.template`）
2. 在 `Create*` / `Update*` / `Delete*` 操作前显示的费用提醒模板
3. 明确的用户确认流程：显示提醒 → 等待 yes/no → 拒绝则中止
4. 只读操作的豁免列表（`List*` / `Show*` / `Get*` / `--dry-run`）

**费用提醒模板：**

```
⚠️  费用提醒：此操作将 [创建/更新/删除] {RESOURCE_TYPE} 资源，
    可能产生华为云账户费用。
    - 资源类型：{RESOURCE_TYPE}
    - 计费模式：{BILLING_MODEL}（如按需计费、包月订阅）
    - 预估费用：{ESTIMATED_COST}（如已知，否则为"按规格变化"）
    
    是否继续？(yes/no)
```

**Agent 行为：**
- 用户确认 → 执行操作
- 用户拒绝或无响应 → **立即中止**，不执行

## User-Agent 标识

在生成的 Skill 的 CLI 调用中添加 User-Agent 标识，用于平台使用追踪：

```bash
# 若 CLI 支持 --user-agent 参数
hcloud ECS ListServers --cli-region=cn-north-4 --user-agent HuaweiCloud-Agent-Skills

# 若 CLI 支持环境变量
export HCLOUD_USER_AGENT=HuaweiCloud-Agent-Skills
```

## 认证与安全

### 认证方式

| 方式 | 场景 | 推荐做法 |
|------|------|----------|
| AK/SK 环境变量 | 开发 | 设置 `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` 环境变量 |
| 临时令牌 | 生产 | 使用 STS 临时 AK/SK + SecurityToken |
| IAM 角色 | 云上运行时 | 绑定 IAM 角色自动获取权限 |

### CLI 配置

```bash
# 通过环境变量设置默认区域
export HUAWEI_REGION=cn-north-4
```

> **安全提醒：** 绝不在脚本中硬编码 AK/SK。使用环境变量或 IAM 角色。不要通过 CLI 配置命令传递明文凭据。

### 权限策略要求

每个生成的 Skill 的 `references/iam-policies.md` 必须：
1. 定义所需权限（分别列出查询和变更操作）
2. 提供最小权限策略 JSON
3. 标注需要 MFA 或提升安全等级的操作

## 版本管理

在 Frontmatter `version` 字段中遵循 SemVer（`MAJOR.MINOR.PATCH`）。分支策略：`main`（稳定）、`preview`（测试）、`{skill-name}-{version}`（发布快照）。

### 安装

```bash
npx skills add https://gitcode.com/developer-skill/developer-skill.git --skill {skill-name}
```

## 开发工作流

**流程：** 需求 → 草稿 → 测试用例 → 并行运行 with/without-skill → 断言 → 评分 → 用户评审 → 改进 → 重复。

**迭代：** 每次改进后重新运行所有测试；用迭代标记追踪版本；反馈满足后停止；将重复工作提取到 scripts/。

**发布：** 合并到 `main` → 更新版本 → 运行 `validate-skill.sh` → 打标签发布。

**废弃：** 在 SKILL.md 中标记废弃 API；在 description 中声明 `deprecated`；提供迁移指引。

## 测试与评估

| 类型 | 方法 | 目标 |
|------|------|------|
| 结构检查 | 目录检查 | Frontmatter 和目录结构 |
| 功能测试 | 运行测试用例 | 验证功能正确性 |
| 对比测试 | with/without-skill | 量化 Skill 价值增量 |
| 回归测试 | 跨迭代对比 | 确保无回归 |
| 触发测试 | 触发评估集 | 优化描述准确率 |

指标：pass_rate、time_seconds、tokens、delta（with/without 差值）。

## 贡献指南

每个 PR 只解决一个问题；标题格式：`[type] description`；提交前运行 `validate-skill.sh`；更新版本号。标签：`bug`、`feature`、`documentation`、`security`、`question`。

## 数据流图

本 Skill 自身的数据流图，展示 Skill 创建请求如何流经工作流：

```mermaid
flowchart TD
  INPUT([/"用户：创建华为云 Skill"/])
  STEP1["步骤 1：需求分析\n（苏格拉底式询问）"]
  STEP2["步骤 2：命名与目录"]
  STEP3["步骤 3：API 调研"]
  STEP4["步骤 4：数据流图"]
  STEP5["步骤 5：生成 SKILL.md"]
  STEP6["步骤 6：生成 references/"]
  STEP7["步骤 7：生成 scripts/"]
  STEP8["步骤 8：生成 templates/ 和 demo/"]
  STEP9["步骤 9：生成 i18n/"]
  STEP10["步骤 10：质量验证"]
  STEP11["步骤 11：功能测试\n（CLI --help / 只读实时 / SDK）"]
  OUTPUT([/"完整 Skill 包"/])

  subgraph CLI_OPS["CLI 操作"]
    CLI_OP1["hcloud ECS ListServers --cli-region={region}"]
    CLI_OP2["hcloud ECS ShowServer --cli-region={region}"]
    CLI_OP3["hcloud VPC ListVpcs --cli-region={region}"]
  end

  subgraph TEST_OPS["功能测试操作"]
    TEST1["hcloud ECS ListServers --help"]
    TEST2["hcloud ECS ListServers --cli-region={region} --limit=1"]
    TEST3["hcloud ECS CreateServers --help"]
  end

  subgraph DATA["数据源"]
    ENV[/"环境变量\nHUAWEI_ACCESS_KEY, HUAWEI_SECRET_KEY, HUAWEI_REGION"/]
    REFS["references/\nskill-spec-generic.md, naming-conventions.md"]
    TEMPLATES["templates/\nSKILL.md.template, iam-policies.md.template\ni18n-zh-CN-SKILL_CN.md.template"]
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
  STEP9 --> STEP10
  STEP10 --> STEP11
  STEP11 --> OUTPUT

  ENV -.-> STEP1
  REFS -.-> STEP2
  TEMPLATES -.-> STEP5
  TEMPLATES -.-> STEP9
  SCRIPTS -.-> STEP4
  SCRIPTS -.-> STEP10
  SCRIPTS -.-> STEP11

  STEP3 --> CLI_OPS
  CLI_OP1 -.-> STEP3
  CLI_OP2 -.-> STEP3
  CLI_OP3 -.-> STEP5

  STEP11 --> TEST_OPS
  TEST1 -.-> STEP11
  TEST2 -.-> STEP11
  TEST3 -.-> STEP11
```

### 数据流描述

| 步骤 | 输入 | 处理 | 输出 |
|------|------|------|------|
| 1. 需求分析 | 用户请求 + 环境配置 | 确认服务、范围、触发场景 | 结构化需求 |
| 2. 命名与目录 | 需求 + 命名规范 | 生成名称、创建目录结构 | Skill 目录路径 |
| 3. API 调研 | 目录 + CLI 访问 | 发现操作、测试只读命令 | API 操作列表 |
| 4. 数据流图 | 工作流步骤 + CLI 操作 | 从模板生成 Mermaid 图 | `references/dataflow-diagram.md` |
| 5. 生成 SKILL.md | API 列表 + 模板 | 用服务数据填充 SKILL.md.template | `SKILL.md` |
| 6. 生成 references/ | SKILL.md + API 数据 | 创建 iam-policies、cli-guide 等 | `references/` 目录 |
| 7. 生成 scripts/ | 工作流需求 | 创建分析/部署脚本 | `scripts/` 目录 |
| 8. 生成 templates/ 和 demo/ | 配置模式 | 创建 IaC/API 模板 + 示例 | `templates/` + `demo/` |
| 9. 生成 i18n/ | SKILL.md 内容 | 翻译 SKILL.md 为 zh-CN | `i18n/zh-CN/SKILL_CN.md` |
| 10. 质量验证 | 完整 Skill 目录 | 运行 validate-skill.sh | 验证报告 |
| 11. 功能测试 | Skill 内容 + CLI help + 凭证 | 通过 `--help` 测试 CLI 语法，执行只读实时查询（`--limit=1`），提示用户提供凭证 | `references/test-report.md` |

## 典型用例

**ECS 管理 Skill：** 用户请求 ECS 管理 → 确认范围（查询、创建、启停、删除）→ 名称：`huawei-cloud-ecs-manage` → 领域：compute → 调研 CLI 操作 → 生成数据流图 → 生成完整目录 → 验证 → 功能测试（ListServers --help, ListServers --limit=1, CreateServers --help）。

**OBS 诊断 Skill：** 用户请求 OBS 诊断 → 确认范围（桶状态、访问日志、容量）→ 名称：`huawei-cloud-obs-diagnosis-workflow` → 领域：storage → 调研 → 生成 → 验证 → 功能测试（ListBuckets --help, ListBuckets --limit=1）。

**VPC 管理 Skill：** 用户请求 VPC 管理 → 确认范围（VPC/子网/安全组）→ 名称：`huawei-cloud-vpc-manage` → 领域：network → 调研 → 生成 → 验证 → 功能测试。

## 核心原则

- **规范优先** — 所有生成的 Skill 必须符合 `references/skill-spec-generic.md`
- **描述驱动触发** — `description` 必须包含 `"Triggers include:"` 子句及所有触发短语，确保 Agent 路由准确
- **安全第一** — 绝不硬编码 AK/SK，写操作前确认，高风险操作预演
- **费用透明** — 生成的 Skill 必须包含资源变更操作的费用确认；用户拒绝则中止
- **领域完整** — 在 Skill 内完成完整工作流，最小化上下文切换
- **最小权限** — iam-policies.md 提供最小权限策略 JSON，查询/变更分开列出，标注 MFA
- **幂等优先** — 优先使用 List/Show/Get 只读操作进行状态验证
- **功能测试** — 结构验证后对 CLI 命令通过 `--help` 测试语法，执行只读实时查询（`--limit=1`），涉及敏感操作时先提示用户提供凭证
- **User-Agent** — 在 CLI 调用中添加 User-Agent 标识用于追踪
- **版本管理** — 遵循 SemVer，记录在 Frontmatter version 字段
- **数据流图** — 每个 Skill 必须在 `references/dataflow-diagram.md` 中包含 Mermaid 数据流图展示完整工作流
- **i18n 支持** — 每个 Skill 应包含 `i18n/zh-CN/SKILL_CN.md` 中文 locale；CLI 命令保持英文

## 主要步骤

1. **需求分析（苏格拉底式询问）** — 逐步追问收集服务、范围、操作和触发场景；每 5 次询问生成总结；用户确认后继续
2. **命名与目录** — 生成 Skill 名称（`huawei-cloud-{product}-{function}`），创建目录结构
3. **API 调研** — 发现 CLI 操作，测试只读命令，记录 API 操作列表
4. **生成 SKILL.md** — 用 SKILL.md.template 填入服务数据、元数据和流程内容
5. **生成支持文件** — 创建 references/、scripts/、templates/、demo/ 和 i18n/ 目录
6. **质量验证** — 运行 validate-skill.sh，修复问题，验证合规性
7. **功能测试（CLI / API / SDK）** — 运行 `scripts/test-cli-commands.sh` 自动测试，或通过 `--help` 测试 CLI 语法，执行只读实时查询，验证 SDK/API 引用；涉及敏感数据时提示用户提供凭证；生成 `references/test-report.md`

## 验证方法

- 运行 `bash scripts/validate-skill.sh <skill-path>` 验证生成的 Skill
- 验证 SKILL.md 中所有必需章节是否存在
- 验证未硬编码 AK/SK 或密钥
- 验证所有 hcloud 命令包含 `--cli-region`
- 验证 i18n/zh-CN/SKILL_CN.md 存在且 CLI 命令保持英文
- **结构验证后执行功能测试：**
  - 对每个 CLI 命令运行 `--help` 验证语法和参数
  - 执行只读操作（List/Show/Get）实际调用，带 `--limit=1`
  - 变更操作仅通过 `--help` 验证（绝不实际执行）
  - 生成 `references/test-report.md` 记录结果
  - 涉及敏感信息时提示用户提供凭证

## 参考文档

- [`references/skill-spec-generic.md`](../references/skill-spec-generic.md) — 完整规范
- [`references/naming-conventions.md`](../references/naming-conventions.md) — 命名规范速查
- [`references/quality-checklist.md`](../references/quality-checklist.md) — 质量检查清单
- [`references/acceptance-criteria.md`](../references/acceptance-criteria.md) — 验收标准
- [`references/verification-method.md`](../references/verification-method.md) — 验证方法
- [`references/related-commands.md`](../references/related-commands.md) — 命令速查
- [`references/dataflow-diagram.md`](../references/dataflow-diagram.md) — 数据流图（本 Skill 自身图表）
- [`templates/dataflow-diagram.md.template`](../templates/dataflow-diagram.md.template) — 数据流图模板
- [`templates/i18n-zh-CN-SKILL_CN.md.template`](../templates/i18n-zh-CN-SKILL_CN.md.template) — i18n 中文模板
