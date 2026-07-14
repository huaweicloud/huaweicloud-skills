---
name: huawei-cloud-skill-tester
version: 1.0.0
description: |
  1. 对华为云 AI Shell Skill 执行四阶段测试：安装验证、基本功能、组合兼容性和方案级测试（功能定位）
  2. 当用户需要测试 Skill 质量、验证多 Skill 组合兼容性、检测 Agent 幻觉或生成测试报告时触发（触发条件）
  3. 提供结构化测试框架、幻觉检测机制、With/Without 对比评估和自动化测试脚本，确保 Skill 发布前质量达标（价值主张）
  4. 通过 npx skills 命令编排测试流程，结合 validate-skill.sh、test-skill.sh 和 detect-hallucination.sh 脚本（使用方式）
  5. 仅需 SKILL.md 为必需结构；references/、scripts/、templates/、demo/ 为推荐但非必需。测试报告区分必需（PASS/FAIL）和推荐（WARN）检查项（前置条件）
  触发场景包括："测试Skill","Skill测试","华为云Skill测试","测试华为云Skill","Skill质量测试","Skill质量验证","Skill兼容性测试","检测Skill幻觉","Skill幻觉检测","test skill","skill test","test skill quality","verify skill compatibility","detect skill hallucination","skill tester","华为云Skill测试器","帮我测试Skill","帮我验证Skill质量","运行Skill四阶段测试","测试skill质量","验证skill兼容性","检测skill幻觉","skill测试","skill质量验证","华为云skill测试","帮我test skill","运行skill四阶段测试","test华为云Skill","verify skill质量","detect skill幻觉","skill tester测试","测试Skill quality","验证Skill compatibility"
tags: [huawei-cloud, skill-testing, quality-assurance, hallucination-detection, compatibility, devops]
---

# 华为云 Skill 测试器

对华为云 AI Shell Skill 执行四阶段质量测试，覆盖从安装验证到端到端方案的完整流水线，内置幻觉检测和多 Skill 组合兼容性验证。

> **测试规范：** [`references/test-spec.md`](../references/test-spec.md) — 完整四阶段测试规范。
> **测试指南：** [`references/skill-test-guide.md`](../references/skill-test-guide.md) — 行业最佳实践和优化方向。

## 概述

当前 AIShell Skill 测试仅覆盖"安装 → 运行 → 卸载"，缺乏结构化验证、多 Skill 组合测试、幻觉检测和回归机制。本 Skill 提供完整的四阶段测试框架，确保 Skill 在每个层面——单一功能、多 Skill 协作、端到端方案——均达到质量标准。

## 设计原则

**原则 1**：测试金字塔 — 安装验证（多）→ 基本功能（中）→ 组合兼容性（少）→ 方案级（更少）。底层快速反馈，顶层覆盖真实场景。

**原则 2**：幻觉防御 — 对 Agent 输出应用结构化断言，验证 Skill 路由正确性，检测职责混淆和参数捏造。

**原则 3**：组合优先 — 同一云服务下的多个 Skill 必须经过统一的组合测试，验证无冲突和缺口。

## 前置条件

1. **hcloud CLI** 已安装并完成 AK/SK 认证配置
   ```bash
   hcloud --version
   hcloud configure list
   ```

2. **目标 Skill** 可通过 npx 安装
   ```bash
   npx skills add <repo> --skill <target-skill-name>
   ```

3. **AIShell** 运行中，Agent 可加载 Skill

4. **测试用例配置** 已准备（或从模板生成）
   ```bash
   # 从模板生成测试用例
   cp templates/test-cases.yaml.template ./test-cases.yaml
   ```

## 核心命令

| 命令 | 说明 |
|------|------|
| `bash scripts/validate-skill.sh <skill-path> --phase all-install` | 阶段 1：完整安装验证 |
| `bash scripts/validate-skill.sh <skill-path> --phase i18n` | i18n 目录验证 |
| `bash scripts/test-skill.sh <name> --skill-path <path> --phase all-basic` | 阶段 2：所有基本功能测试 |
| `bash scripts/test-skill.sh <name> --skill-path <path> --phase all-combination --related <s2,s3>` | 阶段 3：所有组合兼容性测试 |
| `bash scripts/detect-hallucination.sh <name> --skill-path <path> --related <s2,s3>` | 幻觉检测 |
| `bash scripts/test-skill.sh <name> --skill-path <path> --phase solution --scenario <name>` | 阶段 4：方案级测试 |
| `bash scripts/test-skill.sh <name> --skill-path <path> --phase full --related <s2,s3> --output ./report.yaml` | 完整四阶段流水线 |

## 参数确认

| 参数 | 必需 | 说明 | 示例 |
|------|------|------|------|
| `<skill-name>` | 是 | 目标 Skill 名称 | `your-skill-name` |
| `<skill-path>` | 是 | 目标 Skill 目录路径 | `./skills/<domain>/<your-skill-name>` |
| `--phase` | 是 | 要执行的测试阶段 | `all-install`、`all-basic`、`all-combination`、`solution`、`full` |
| `--related` | 否 | 组合测试的关联 Skill 名称 | `skill2,skill3` |
| `--scenario` | 否 | 阶段 4 的方案场景名称 | `build-network-env` |
| `--output` | 否 | 测试报告输出路径 | `./test-report.yaml` |

## KooCLI命令格式标准

```bash
# 通用格式
hcloud <Service> <Operation> --cli-region=<region> --param1=value1 --param2=value2

# 具体示例
hcloud ECS ListServers --cli-region=cn-north-4

# 幂等操作（可安全重复）
hcloud ECS ShowServer --cli-region=cn-north-4 --server_id={instance_id}
```

| 特性 | 说明 | 示例 |
|------|------|------|
| 服务名 | 大写 PascalCase | `ECS`、`VPC`、`IAM` |
| 操作名 | PascalCase | `ListServers`、`ShowServer` |
| 区域参数 | `--cli-region=<值>` | `--cli-region=cn-north-4` |
| 简单参数 | `--key=value` | `--server_id=xxx` |
| 索引参数 | `--key.1=value1` | `--servers.1.id=xxx` |
| 嵌套参数 | `--key.sub_key=value` | `--config.protocol=vnc` |

## 工作流

### 阶段 1：安装验证

验证 Skill 安装正确、结构完整、规范合规。

```bash
# 步骤 1.1：安装目标 Skill
npx skills add <skill-repo> --skill <target-skill-name>

# 步骤 1.2：验证目录结构完整性
bash scripts/validate-skill.sh <skill-path> --phase install

# 步骤 1.3：验证 YAML Frontmatter 规范
bash scripts/validate-skill.sh <skill-path> --phase frontmatter

# 步骤 1.4：验证前置依赖
bash scripts/validate-skill.sh <skill-path> --phase dependency

# 步骤 1.5：验证必需章节（双语匹配）
bash scripts/validate-skill.sh <skill-path> --phase sections

# 步骤 1.6：一次性运行所有安装验证
bash scripts/validate-skill.sh <skill-path> --phase all-install
```

**验证项：**

| 项目 | 说明 | 级别 |
|------|------|------|
| SKILL.md | SKILL.md 存在且可读 | 必需 |
| Frontmatter | name、description（5 点）、version、tags 合规 | 必需 |
| references/ | 参考文档目录 | 推荐 |
| scripts/ | 测试/验证脚本目录 | 推荐 |
| templates/ | 模板目录 | 推荐 |
| demo/ | 示例目录 | 推荐 |
| i18n/ | 国际化翻译目录 | 推荐 |
| i18n locale 格式 | locale 目录遵循 BCP 47 (xx-XX) 格式 | 推荐 |
| i18n SKILL 文件 | 每个 locale 有 SKILL 翻译文件（如 SKILL_CN.md） | 推荐 |
| i18n frontmatter | 翻译文件有有效 frontmatter | 推荐 |
| i18n name 匹配 | 翻译 name 字段与原始 SKILL.md 匹配 | 推荐 |
| 验证脚本 | `validate-skill.sh` 可执行且通过 | 推荐 |
| CLI 依赖 | hcloud 可用且已认证 | 推荐 |
| 参考文档 | references/ 下关键文件存在 | 推荐 |
| 必需章节 | 双语匹配：概述/Overview、前置条件/Prerequisites、工作流/Workflow、核心命令/Core Commands、参数确认/Parameters、参考文档/References | 必需 |
| KooCLI 章节 | KooCLI命令格式标准 / KooCLI Command Format（有 CLI 操作时必需） | 必需 |
| 跨 Skill 引用 | 无直接 Skill 交叉引用（由 Agent 编排） | 推荐 |

### 阶段 2：基本功能测试

验证 Skill 在 AICLI 中被正确触发且核心功能输出正确。

```bash
# 步骤 2.1：加载目标 Skill 并运行基本用例
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase basic

# 步骤 2.2：运行触发准确率测试
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase trigger

# 步骤 2.3：运行边界/异常用例
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase boundary

# 步骤 2.4：运行 With/Without 对比测试
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase compare

# 步骤 2.5：一次性运行所有基本功能测试
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase all-basic
```

**测试类型：**

| 类型 | 方法 | 目标 |
|------|------|------|
| 触发识别 | 输入触发词，验证 Skill 被正确加载 | 触发准确率 >= 90% |
| 核心功能 | 执行典型用例，验证输出包含预期内容 | 输出结构完整 |
| 边界/异常 | 输入无效/边界参数 | 错误处理合理，无捏造 |
| 无误触发 | 输入无关请求 | Skill 未被错误激活 |
| With/Without | 对比有/无 Skill 执行同一任务 | 量化价值差值 > 0 |

### 阶段 3：组合兼容性测试

验证同一云服务下的多个 Skill 协作无冲突和幻觉。

```bash
# 步骤 3.1：识别同服务关联 Skill
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase identify-related

# 步骤 3.2：运行跨 Skill 场景用例
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase combination --related <skill2,skill3>

# 步骤 3.3：运行多 Skill 竞争测试
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase competition --related <skill2,skill3>

# 步骤 3.4：运行上下文隔离测试
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase isolation --related <skill2,skill3>

# 步骤 3.5：运行幻觉检测
bash scripts/detect-hallucination.sh <skill-name> --skill-path <skill-path> --related <skill2,skill3>

# 步骤 3.6：一次性运行所有组合测试
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase all-combination --related <skill2,skill3>
```

**幻觉检测项：**

| 幻觉类型 | 检测方法 | 判定标准 |
|----------|----------|----------|
| 职责混淆 | 验证 Agent 调用的 Skill 与请求匹配 | 调用 Skill == 预期 Skill |
| 参数捏造 | 验证输出参数值在有效范围内 | 参数值在已知服务/资源白名单内 |
| 工作流拼接错误 | 验证多步工作流步骤完整性 | 实际步骤 == 预期步骤序列 |
| 上下文污染 | 验证后续任务不含前序残留 | 任务 B 输出 ∩ 任务 A 实体 = 空 |
| 格式幻觉 | 验证输出结构符合规范 | 输出匹配 JSON Schema |

### 阶段 4：方案级测试

验证 Skill 在真实业务方案端到端场景中的表现。

```bash
# 步骤 4.1：运行端到端方案场景
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase solution --scenario <scenario-name>

# 步骤 4.2：采集性能指标
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase performance

# 步骤 4.3：生成四阶段测试报告
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase report --output <report-path>
```

**性能指标：**

| 指标 | 说明 | 建议阈值 |
|------|------|----------|
| total_time_seconds | 端到端总耗时 | < 300s |
| total_tokens | 总 token 消耗 | < 50000 |
| accuracy_rate | 输出准确率 | > 0.9 |
| hallucination_rate | 幻觉发生率 | < 0.05 |
| trigger_accuracy | 触发准确率 | > 0.9 |

## 一键全流水线

```bash
# 执行全部四阶段并生成报告
bash scripts/test-skill.sh <skill-name> \
  --skill-path <skill-path> \
  --phase full \
  --related <skill2,skill3> \
  --scenario <scenario-name> \
  --output ./test-report.yaml
```

## 边界情况

| 场景 | 处理 |
|------|------|
| 目标 Skill 安装失败 | 记录错误，中止后续阶段，报告标记 INSTALL_FAIL |
| hcloud CLI 未安装 | 提示安装命令，中止测试 |
| AK/SK 未配置 | 提示配置步骤，中止测试 |
| 测试用例配置缺失 | 使用 templates/ 中的默认模板 |
| 关联 Skill 未安装 | 跳过组合测试，报告标记 COMBINATION_SKIP |
| 检测到幻觉 | 标记 HALLUCINATION_DETECTED，记录详情，继续后续测试 |
| Agent 超时无响应 | 标记 TIMEOUT，记录超时阶段，继续后续测试 |
| 网络不可达 | 标记 NETWORK_ERROR，中止需要云 API 的测试 |

## 验证方法

### 阶段 1 验证

```bash
# 安装验证通过条件
bash scripts/validate-skill.sh <skill-path> --phase all-install
# 预期输出：[PASS] All installation checks passed
```

### 阶段 2 验证

```bash
# 基本功能测试通过条件
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase all-basic
# 预期：pass_rate >= 0.9, trigger_accuracy >= 0.9
```

### 阶段 3 验证

```bash
# 组合兼容性测试通过条件
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase all-combination --related <skill2>
# 预期：hallucination_rate < 0.05, 无冲突错误
```

### 阶段 4 验证

```bash
# 方案级测试通过条件
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase solution --scenario <name>
# 预期：全流水线通过，性能在阈值内
```

### 测试报告

测试完成后，在指定路径生成 YAML 格式报告。结构详见 [`templates/test-report.yaml.template`](../templates/test-report.yaml.template)。

报告包含：
- 四阶段所有测试用例的 PASS/FAIL 状态
- 幻觉检测结果和详情
- 性能指标数据
- With/Without 对比差值
- 总体评估和建议

## 参考文档

- [`references/test-spec.md`](../references/test-spec.md) — 完整四阶段测试规范
- [`references/skill-test-guide.md`](../references/skill-test-guide.md) — 行业最佳实践和优化方向
- [`references/iam-policies.md`](../references/iam-policies.md) — 所需权限策略
- [`references/acceptance-criteria.md`](../references/acceptance-criteria.md) — 验收标准
- [`references/hallucination-detection.md`](../references/hallucination-detection.md) — 幻觉检测规范
- [`references/quality-checklist.md`](../references/quality-checklist.md) — 质量检查清单
- [`references/cli-installation-guide.md`](../references/cli-installation-guide.md) — CLI 安装指南
- [`references/related-commands.md`](../references/related-commands.md) — 命令速查
- [`references/verification-method.md`](../references/verification-method.md) — 验证方法

## 脚本使用

| 脚本 | 用途 | 示例 |
|------|------|------|
| `scripts/validate-skill.sh` | 阶段 1 安装验证 | `bash scripts/validate-skill.sh ./path --phase all-install` |
| `scripts/validate-skill.sh` | i18n 目录验证 | `bash scripts/validate-skill.sh ./path --phase i18n` |
| `scripts/test-skill.sh` | 阶段 2/3/4 测试执行 | `bash scripts/test-skill.sh <name> --skill-path <path> --phase full` |
| `scripts/test-skill.sh` | i18n 测试执行 | `bash scripts/test-skill.sh <name> --skill-path <path> --phase i18n` |
| `scripts/detect-hallucination.sh` | 幻觉检测 | `bash scripts/detect-hallucination.sh <name> --skill-path <path> --related <s2>` |
| `scripts/generate-report.sh` | 测试报告生成 | `bash scripts/generate-report.sh <result-dir> --output report.yaml` |

## 典型用例

### 场景 1：测试单个 Skill 基本功能

```text
用户：帮我测试 <target-skill-name> Skill
Agent：
  1. 阶段 1：npx 安装 + 结构验证 -> PASS
  2. 阶段 2：AICLI 触发 + 核心用例 + 边界用例 -> PASS
  3. 生成阶段 1+2 测试报告
```

### 场景 2：测试多 Skill 组合兼容性

```text
用户：测试 ECS 管理和 ECS 诊断 Skill 的兼容性
Agent：
  1. 阶段 1+2：测试每个 Skill 的基本功能 -> PASS
  2. 阶段 3：组合加载 + 跨场景用例 + 竞争测试 + 幻觉检测 -> PASS
  3. 生成组合兼容性测试报告
```

### 场景 3：端到端方案测试

```text
用户：对 VPC 网络方案 Skill 运行端到端测试
Agent：
  1. 阶段 1+2+3：基本和组合测试 -> PASS
  2. 阶段 4：执行"构建完整网络环境"方案场景
  3. 采集性能指标，生成完整测试报告
```

### 场景 4：检测 Skill 幻觉问题

```text
用户：在多 Skill 环境下检测 your-skill-name 的幻觉
Agent：
  1. 识别关联 Skill 集合
  2. 运行幻觉检测：职责混淆、参数捏造、上下文污染
  3. 输出幻觉检测报告，标记 HALLUCINATION_DETECTED 或 PASS
```

## User-Agent 标识

测试时调用 hcloud CLI 添加 User-Agent 标识，用于平台 Skill 使用追踪：

```bash
export HCLOUD_USER_AGENT=HuaweiCloud-Agent-Skills
```

## 核心原则

- **测试金字塔** — 安装验证（多）→ 基本功能（中）→ 组合兼容性（少）→ 方案级（更少）
- **幻觉防御** — 结构化断言 + 路由验证 + 白名单校验，拒绝格式异常输出
- **组合优先** — 同服务多 Skill 必须经过统一组合测试
- **幂等优先** — 测试中优先使用只读/幂等操作，避免副作用
- **隔离性** — 每个测试用例独立，不依赖其他用例结果
- **可重复性** — 相同输入产生相同输出，消除随机性
- **增量回归** — 每次变更后自动运行受影响测试子集
- **安全第一** — 测试中不硬编码 AK/SK，破坏性操作需确认
- **User-Agent** — 在 CLI 调用中添加 User-Agent 标识用于追踪
