# Skill 开发规范与指南（通用版 v1）

> v1.0.0 | 综合参考 Codex Skill Creator、社区 Skill Creator、飞书 lark-skill-maker、华为云 Skills 规范四份材料提炼。

---

## 1. 概述

Skill 是 AI Agent 的"领域专业知识包"——一个结构化的指令文件夹，让 Agent 在特定任务上具备专业知识和工作流。

本规范定义了一套通用的 Skill 开发标准，覆盖目录结构、命名规则、SKILL.md 撰写要求、参考文档组织、脚本开发、CLI 使用、认证安全、版本管理、测试评估等全维度。

---

## 2. 目录结构与命名

### 2.1 仓库组织结构

Skill 按领域/服务分类组织在仓库中：

```
skills-repo/
├── README.md
├── skills/
│   ├── compute/          # 计算类
│   │   ├── myservice-manage/
│   │   └── myservice-diagnosis/
│   ├── network/          # 网络类
│   ├── storage/          # 存储类
│   ├── database/         # 数据库类
│   ├── security/         # 安全类
│   ├── monitoring/       # 监控类
│   ├── middleware/       # 中间件类
│   ├── devtools/         # 开发工具类
│       ├── cli/
│       └── common/
│   └── solution/         # 解决方案类
```

### 2.2 Skill 内部目录结构

```
skill-name/
├── SKILL.md                   # 必需：YAML Frontmatter + Markdown 指令
├── references/                # 推荐：参考文档（按需加载）
│   ├── cli-installation-guide.md   # CLI 安装配置指南
│   ├── iam-policies.md             # 权限策略文档
│   ├── verification-method.md      # 验证方法
│   ├── acceptance-criteria.md      # 验收标准
│   └── related-commands.md         # 相关命令速查
├── scripts/                   # 推荐：可执行脚本
│   ├── analyze.py
│   └── deploy.sh
├── templates/                 # 可选：配置/模板文件
│   ├── config.yaml
│   └── report.md
└── demo/                      # 可选：示例数据
    └── example.json
```

### 2.3 命名规范

| 层级 | 命名规则 | 示例 | 说明 |
|------|----------|------|------|
| 领域目录 | 单数名词 | `compute`, `storage`, `network` | 按服务/产品领域分组 |
| 服务目录 | 服务/产品缩写 | `ecs`, `vpc`, `obs` | 领域下的子服务 |
| Skill 名称 | `{platform}-{product}-{function}` | `mycloud-ecs-diagnosis-workflow` | 平台+产品+功能 |
| 参考文件 | kebab-case | `cli-installation-guide.md` | 描述性命名 |
| 脚本文件 | kebab-case | `analyze-ingress.sh` | 动词+名词 |

**Skill 命名公式：**

```
{platform}-{product}-{function}
```

**示例：**
- `mycloud-ecs-diagnosis-workflow` — ECS 诊断工作流
- `mycloud-vpc-manage` — VPC 管理
- `mycloud-obs-manage` — OBS 存储管理
- `mycloud-cli-guidance` — CLI 使用指南
- `mycloud-rds-copilot` — RDS 运维助手

### 2.4 Skill 设计原则

**原则 1**：每个 Skill 应解决一个具体的 Agent 使用场景。不追求大而全，追求"Agent 正好需要时它能用"。

**原则 2**：Skill 应具备领域完整性。当用户需要该领域能力时，Agent 能在 Skill 内完成全流程，无需频繁跳出。

**原则 3**：Skill 的内容与 Agent 能力是协作关系。Skill 提供专业知识和工作流，Agent 负责推理和执行。

---

## 3. SKILL.md 规范

SKILL.md 是 Skill 的核心文件，结构为 **YAML Frontmatter + Markdown 正文**。正文建议 500 行以内。

### 3.1 YAML Frontmatter 规范

SKILL.md 以 `---` 包裹的 YAML 元数据开头：

```yaml
---
name: mycloud-ecs-diagnosis-workflow
description: |
  1. Skill 负责做什么（功能定位）
  2. 什么时候触发该 Skill（触发条件）
  3. 使用 Skill 能达到什么效果（价值描述）
tags: [cloud, ecs, diagnostics, troubleshooting, devops]
version: 1.0.0
---
```

#### 3.1.1 Frontmatter 字段说明

| 字段 | 必需 | 类型 | 说明 | 示例 |
|------|------|------|------|------|
| `name` | 是 | string | Skill 唯一标识名 | `mycloud-ecs-diagnosis` |
| `description` | 是 | string | 功能定位 + 触发条件 + 价值描述 | 见下方 |
| `tags` | 推荐 | string[] | 分类标签，方便检索，建议 3-8 个 | `[cloud, ecs, diagnostics]` |
| `version` | 推荐 | string | SemVer 版本号 | `2.0.0` |

#### 3.1.2 description 编写规范

description 使用结构化格式，建议用编号分点描述：

1. **功能定位** — 这个 Skill 负责什么
2. **触发条件** — 什么场景下触发
3. **价值描述** — 使用后能达到什么效果
4. **使用方式** — 涉及哪些 CLI/API 操作
5. **特殊说明** — 使用前需要满足的前置条件

### 3.2 正文结构

SKILL.md 正文按以下结构组织：

| 章节 | 内容 | 必需 |
|------|------|------|
| 概述 | 背景介绍、Skill 定位 | 是 |
| 前置条件 | CLI 安装状态、IAM 权限、环境变量等 | 推荐 |
| 主要步骤 | 核心操作流程，含代码示例 | 是 |
| 边界情况 | 常见错误、异常处理 | 推荐 |
| 验证方法 | 如何验证操作成功 | 推荐 |
| 参考文档 | 指向 references/ 中更详细的文档 | 推荐 |
| 脚本使用 | scripts/ 中的脚本说明 | 按需 |

#### 3.2.1 正文编写要求

**内容要求：**
- 每步操作有清晰的指令
- 关键参数有配置说明
- 每个操作标注所需权限
- 提供 3-5 个典型使用示例
- 指向 references/ 中的详细文档

**安全要求：**
- CLI 参数/脚本中 **不能直接嵌入 AK/SK 等敏感信息**
- 敏感信息通过环境变量或安全配置获取
- 示例中的账号信息使用占位符

### 3.3 质量门禁

| 检查项 | 是否必需 | 说明 |
|--------|----------|------|
| SKILL.md 格式完整 | 是 | YAML + Markdown 结构正确 |
| SKILL.md Frontmatter 完整 | 是 | name、description 必填 |
| references/ 引用正确 | 是 | 被引用的文件存在 |
| 示例/命令可运行 | 推荐 | 代码示例语法正确 |

---

## 4. 参考文档规范（references/）

### 4.1 标准参考文件

| 文件名 | 用途 | 示例内容 |
|--------|------|----------|
| `cli-installation-guide.md` | CLI 工具安装与初始化 | 安装步骤、配置方法 |
| `iam-policies.md` | 权限策略说明 | 所需 API Action、策略 JSON |
| `verification-method.md` | 操作验证方法 | 验证成功/失败的判断标准 |
| `acceptance-criteria.md` | 验收标准 | 任务完成的判定条件 |
| `related-commands.md` | 相关命令速查 | 工具命令速查表 |

### 4.2 扩展参考文件

| 文件名 | 用途 | 适用场景 |
|--------|------|----------|
| `related-commands.md` / `related-apis.md` | 命令/API 速查 | 操作项多时使用 |
| `generic-diagnostics-workflow.md` | 通用诊断流程 | 多步骤诊断场景 |
| `service-catalog.md` | 服务列表 | 涉及多服务交互时 |
| `parameter-format.md` | 参数格式规范 | 有特殊参数格式要求 |
| `common-workflows.md` | 常见工作流 | 有不同的操作模式 |
| `cli-troubleshooting.md` | CLI 故障排查 | CLI 使用中可能有问题 |
| `region-and-spec.md` | 区域/规格信息 | 依赖区域/规格差异 |
| `search-commands.md` | 搜索命令指引 | 需要快速查找命令 |

### 4.3 参考文件编写要求

1. 每个 ref 文件专注解决一个问题，不混合内容
2. 文件头部加简短说明，明确何时需要读取此文件
3. 大文件（>300 行）顶部加目录
4. 引用信息保持与平台文档一致
5. 示例中的占位符使用花括号标识（如 `{instance_id}` ）
6. 代码块标注语言类型

---

## 5. 脚本规范（scripts/）

### 5.1 脚本类型

| 类型 | 用途 | 示例 |
|------|------|------|
| 分析脚本 | 解析 CLI 输出做自动化分析 | `analyze-ingress-offline.sh` |
| 部署脚本 | 编排多步 CLI 操作 | `deploy-folder.mjs` |
| 数据处理 | CLI JSON 输出处理 | `get_logs.py` |
| 工具库 | 公共函数复用 | `credentials.py`, `validation.py` |

### 5.2 脚本编写要求

1. 脚本使用有意义的名称，以功能命名
2. Shell 脚本加 `#!/bin/bash`，Python 加 `#!/usr/bin/env python3`
3. 脚本中不能硬编码 AK/SK 等敏感信息，通过环境变量获取
4. 脚本兼容对应 CLI 的多版本
5. 脚本提供参数校验和错误处理
6. Python 脚本所在目录需有 `__init__.py`
7. Node.js 脚本使用 `.mjs` 后缀，使用 ES Module

---

## 6. 模板与示例（templates/ & demo/）

### 6.1 templates/

存放配置模板文件：
- Infrastructure as Code 模板（Terraform/CloudFormation）
- API 请求的 JSON/YAML 模板
- 报告/通知的 Markdown 模板

### 6.2 demo/

存放示例数据文件：
- 示例请求/响应
- 示例配置文件
- 测试用数据

---

## 7. CLI 使用规范

### 7.1 通用 CLI 命令格式

```bash
# 通用格式
<cli-tool> <SERVICE> <Operation> --param1=value1 --param2=value2

# 具体示例
mytool ECS ListServers --region=cn-north-4

# 幂等操作（可重复执行）
mytool ECS ShowServer --server_id={instance_id}

# 嵌套参数
mytool ECS StartInstance --os-start.servers.1.id={id1}
```

#### 7.1.1 常见模式

| 特性 | 说明 | 示例 |
|------|------|------|
| 服务名 | 大写 PascalCase | `ECS`, `VPC`, `IAM` |
| 操作名 | PascalCase | `ListServers`, `ShowServer` |
| 区域参数 | `--region=<value>` | `--region=cn-north-4` |
| 简单参数 | `--key=value` | `--server_id=xxx` |
| 索引参数 | `--key.1=value1` | `--servers.1.id=xxx` |
| 嵌套参数 | `--key.sub_key=value` | `--config.protocol=vnc` |

### 7.2 安全操作规范

**必须遵守：**
- 敏感信息（AK/SK）通过环境变量获取，而非明文参数
- 创建/修改/删除操作前确认用户意图
- 优先使用只读查询（List/Describe/Get）验证环境状态
- 高危操作前使用预览模式（--dry-run）

**必须避免：**
- 在命令中明文展示敏感凭证
- 无确认执行破坏性操作
- 使用过期的 API 版本
- 忽略错误码和返回状态

### 7.3 User-Agent 标识

在 CLI 调用中添加 User-Agent 标识，便于平台追踪 Skill 使用情况：

```bash
# 如果 CLI 支持 --user-agent 参数
mytool ECS ListServers --user-agent Platform-Agent-Skills

# 如果 CLI 支持环境变量
export CLI_USER_AGENT=Platform-Agent-Skills
```

---

## 8. 认证与安全

### 8.1 认证方式

| 认证方式 | 适用场景 | 推荐做法 |
|----------|----------|----------|
| AK/SK 环境变量 | 开发环境 | `export ACCESS_KEY_ID=<AK>` |
| CLI 配置 | 本地使用 | `mytool configure set --access-key=AK --secret-key=SK` |
| 临时令牌 | 生产环境 | 使用 STS 临时 AK/SK + SecurityToken |
| IAM 角色 | 云上运行 | 绑定 IAM 角色自动获取权限 |

#### 8.1.1 CLI 配置流程

```bash
# 查看当前配置
mytool configure list

# 设置 AK/SK
mytool configure set --access-key={ACCESS_KEY} --secret-key={SECRET_KEY}

# 设置默认区域
mytool configure set --region=cn-north-4

# 安全提醒：不要在脚本中硬编码 AK/SK
# 任何情况下都不要在脚本中写：
# mytool configure set --access-key=AK...  # ❌ 不要这样做
```

### 8.2 权限策略文档

每个 Skill 的 `references/` 下应包含权限策略文档（`iam-policies.md`）：

```markdown
# 权限策略 - {服务名称}

## 查询类操作

| API Action | 说明 | 用途 |
|------------|------|------|
| service:resources:get | 查询资源详情 | SKill 主流程 |
| service:resources:list | 列举资源列表 | 资源筛选选择 |

## 操作类操作

| API Action | 说明 | 用途 |
|------------|------|------|
| service:resources:action | 执行操作 | SSH/VNC 等操作 |
| service:resources:delete | 删除资源 | 高危操作 |

## 最小权限策略 JSON

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "service:resources:get",
        "service:resources:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```
```

**安全要求：**
1. 每个 Skill 必须在 `references/iam-policies.md` 中定义所需权限
2. 查询操作和操作类操作分表列出
3. 提供最小权限策略 JSON
4. 标注需要 MFA 等高安全要求操作

---

## 9. 版本管理

### 9.1 版本号规范

遵循 SemVer：`MAJOR.MINOR.PATCH`

| 版本位 | 含义 | 何时递增 | 示例 |
|--------|------|----------|------|
| MAJOR | 不兼容变更 | API 版本变更、破坏性更新 | `1.x.x` → `2.0.0` |
| MINOR | 向后兼容的功能新增 | 新增功能、新增操作 | `2.0.x` → `2.1.0` |
| PATCH | 向后兼容的问题修复 | 文档修正、Bug 修复 | `2.1.0` → `2.1.1` |

版本号记录在 SKILL.md 的 YAML Frontmatter 的 `version` 字段中。

### 9.2 分支策略

| 分支 | 用途 | 说明 |
|------|------|------|
| `main` | 稳定发布 | 经过测试验证的正式版本 |
| `preview` | 预览/Beta | 提前预览新功能 |
| `{skill-name}-{version}` | 版本发布 | 特定版本快照 |
| `{skill-name}-{beta}` | Beta 发布 | Beta 版本快照 |

### 9.3 安装方式

#### 通过包管理器安装

```bash
# 安装特定 Skill
npx skills add https://gitcode.com/org/skills.git --skill skill-name

# 安装全部 Skill
npx skills add https://gitcode.com/org/skills.git

# 安装指定分支
npx skills add https://gitcode.com/org/skills/tree/preview --skill skill-name
```

#### 本地安装

```bash
# 克隆仓库
git clone https://gitcode.com/org/skills.git

# 本地添加
npx skills add ./skills/skill-name
```

---

## 10. 贡献指南

### 10.1 Issue 规范

| 标签 | 用途 | 说明 |
|------|------|------|
| `bug` | Bug 报告 | 功能异常、命令错误 |
| `feature` | 功能请求 | 新增 Skill、扩展能力 |
| `documentation` | 文档改进 | SKILL.md 优化 |
| `security` | 安全问题 | 权限、凭证问题 |
| `question` | 使用问题 | 用法咨询 |

**Bug 报告模板：**
```markdown
## Bug 描述
[清晰的问题描述]

## 环境信息
- 平台版本：
- CLI 版本：
- Agent 版本：

## 复现步骤
1. ...
2. ...
3. ...

## 预期结果
[正确行为]

## 实际结果
[实际行为]
```

### 10.2 Pull Request 规范

- 每个 PR 只解决一个问题
- PR 标题格式：`[type] description`
- 提交前运行验证工具
- 更新对应的版本号

### 10.3 代码审查

- 每次提交需至少一人 Review
- Review 重点：SKILL.md 结构、命令准确性、权限完整性

---

## 11. 版本管理迭代

### 11.1 版本记录

在仓库根目录或 SKILL.md 中记录变更历史。

### 11.2 发布流程

1. 代码合并到 `main` 分支
2. 更新 SKILL.md 版本号
3. 打 tag 发布

### 11.3 废弃策略

- 废弃的 API 操作在 SKILL.md 中标注
- 废弃的 Skill 在 description 中声明 deprecated
- 提供迁移到新版本的指引

---

## 12. 开发工作流

### 12.1 完整开发流程

```
需求理解 → 编写草稿 → 创建测试用例 →
同时运行 with-skill / without-skill →
编排断言 → 评分 →
用户审查输出 → 根据反馈改进 → 重复迭代
```

### 12.2 迭代原则

- 每次改进后重新运行所有测试
- 用迭代标记（iteration-N）追踪版本演进
- 当用户反馈全为空（都满意）或不再有显著改进时停止
- 从测试中识别重复工作，提取为 scripts/ 中的脚本
- 阅读运行日志，不仅看最终输出——识别 Agent 在低效环节消耗时间的模式

---

## 13. 测试与评估

### 13.1 测试类型

| 类型 | 方法 | 目标 |
|------|------|------|
| 基础校验 | 结构检查 | Frontmatter 和目录结构 |
| 功能测试 | 运行测试用例 | 验证功能正确性 |
| 对比测试 | with/without-skill | 量化 Skill 增值效果 |
| 回归测试 | 迭代间对比 | 确保改进不引入回退 |
| 触发测试 | trigger eval set | 优化 description 准确率 |

### 13.2 评估指标

| 指标 | 说明 |
|------|------|
| pass_rate | 断言通过率 |
| time_seconds | 执行耗时 |
| tokens | Token 消耗 |
| delta | with/without 差异值 |

---

## 14. 质量门禁与验收标准

| 检查项 | 必需 | 说明 |
|--------|------|------|
| SKILL.md Frontmatter | 是 | name、description 必填 |
| references/ 引用 | 是 | 引用的文件存在 |
| 示例可执行 | 推荐 | 命令语法正确 |
| 认证方式明确 | 推荐 | 说明使用哪种认证 |
| 权限策略明确 | 推荐 | 列出所需权限 |
| 错误处理完整 | 推荐 | 常见错误有处理方案 |
| 版本号正确 | 推荐 | 符合 SemVer |

---

## 15. 参考

- [Codex Skill Creator](https://github.com/openai/codex)
- [Skills Community Repo](https://github.com/openai/skills)
- [Feishu lark-skill-maker](https://open.feishu.cn)
- [Huawei Cloud Skills](https://gitcode.com/developer-skill/huaweicloud-skills)

---

> 文档版本：v1.0.0
> 生成时间：2026-07-07
> 文件位置：`/home/developer/Downloads/skill-spec-generic.md`
