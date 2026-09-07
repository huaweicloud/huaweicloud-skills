# huawei-cloud-solution-ops 知识来源与加载地图

本文件说明 `huawei-cloud-solution-ops` 的知识由谁维护、什么位置是权威来源，以及 Agent 和维护者如何
按需加载资料。它既覆盖 `materials/` 原始资料，也覆盖共享原则、目标视图、交互指南、服务模块
和运行时事实，避免“大 Skill”演变成一次加载全部内容的大上下文。

## 知识类型与权威位置

| 类型 | 典型内容 | 权威位置 | 维护规则 |
| --- | --- | --- | --- |
| 权威事实 | 服务标识、operation、参数、能力覆盖、批量/异步结果语义、资源依赖和已核验限制 | `service-registry.json`、`hcloud-service-catalog/`、`operation-behavior-profiles.json`、`resource-dependency-profiles.json`、服务 guide/playbook 和对应脚本 | 在原事实源更新，不复制到目标或交互视图 |
| 编写知识 | 共享原则、任务记忆方法、目标解释、交互方法 | `unified-principles.md`、`task-workspace-guide.md`、`goal-capability-guide.md`、`interaction-guidance.md` | 人工维护适用边界、因果理由和引用 |
| 派生视图 | 场景路由、能力入口、覆盖表、导航和摘要 | `scenario-router.json`、`scenario-contracts.json`、`service-coverage.md` 及可重建索引 | 保留来源关系；来源改变时重建或修订视图 |
| 运行时事实 | 当前资源、价格、配额、权限、库存、账单和 job 状态 | Agent 的实时工具结果、task 和 artifact | 不写回发布期知识；高影响判断前按当前作用域重查 |

用户声明、Agent 推断和文档知识也不能冒充云侧实时事实。发生冲突时，保留来源和作用域，按影响
程度重新查询或向用户澄清，不静默用旧记录覆盖新事实。

## 单一事实来源规则

- 服务和 API 身份首先由 `references/service-registry.json` 与当前 catalog 维护；
- operation、版本和参数证据由 `references/hcloud-service-catalog/`、resolver、request preflight、
  SDK 静态 schema、live help 或实际 dry-run/query 提供，不在目标卡重复维护；
- 已核验的批量目标、submit receipt 含义和异步/资源终态由 `operation-behavior-profiles.json` 维护，
  `hcloud_operation_behavior.py` 和 planner 只生成派生视图，不执行轮询或工作流；
- 已核验的创建前置资源、删除阻断项、关联资源和回读条件由 `resource-dependency-profiles.json` 维护，
  `hcloud_dependency_evidence.py` 和 planner 只返回证据，不决定执行顺序；
- resolver、通用变更 planner 和 ECS 高频 planner 需要同时装配上述两类 operation evidence 时，统一经
  内部 `hcloud_operation_evidence.py` 读取。它只组合两个已有来源的可用字段，不写入、不缓存、不扩展
  到其他事实库，也不是 Agent 公共入口；缺失事实保持缺失，不用 `null` 或推断冒充已知事实；
- 单次变更费用由 `hcloud_cost_estimate.py` 复用 `hcloud_billing_readonly.py` 与
  `hcloud_billing_live_read.py` 的 BSS 询价事实；未执行询价时金额保持 unknown，询价结果也不冒充历史账单或购买承诺；
- 场景到能力的入口由 router/contract 维护，具体服务知识留在对应 guide 和 playbook；
- 跨多个服务长期稳定的方法才进入 shared core，单一服务规则留在服务模块；
- 目标和交互指南可以解释如何组合事实，但不复制实时价格、配额、库存或资源状态；
- 运行时 task 和 artifact 只属于当前 Agent workspace，不进入 Skill 发布资产；
- 同一事实已经存在权威位置时，其他文件使用引用、摘要或派生索引，不维护第二份可漂移副本。

## 渐进披露加载路径

| 层 | 内容 | 何时加载 |
| --- | --- | --- |
| Metadata | Skill 触发范围和一句话定位 | Agent 选择 Skill 时 |
| `SKILL.md` | 最短入口、公共边界、工具和资料路由 | Skill 被触发时 |
| Backend Selection | hcloud、SDK、Terraform 的选择和切换证据 | 任务开始、后端受阻或 IaC 意图出现时 |
| Runtime Dependencies | 当前后端需要的 CLI、package、网络和 artifact 条件 | 选定后端后、真实执行前或依赖失败时 |
| Public Script Contract | Agent CLI 最小分母、显式输出例外、stdout/artifact 和退出语义 | Agent 调用公共脚本或维护者迁移入口时 |
| Shared Core | 共享原则、task workspace 和交互指南 | 多轮、跨服务、副作用、恢复或复杂交付时按需 |
| Goal / Scenario | 目标能力、scenario router 和 contract | 命中宽泛目标或场景时 |
| Service Module | 对应服务 guide、playbook、catalog 和专用脚本 | 实际涉及该服务或证据缺口时 |
| Materials | 原始文档、SDK 源码和大规模维护资料 | 清洗资料不足、维护或溯源时最后使用 |

推荐加载过程：

```text
Skill metadata
  -> SKILL.md 最短入口
  -> 按需读取 backend-selection.md 选择执行后端
  -> 真实执行前按 runtime-dependencies.md 检查当前后端的必要条件
  -> 只读取当前复杂度需要的 shared core
  -> 命中目标或场景时读取对应目标视图和 router
  -> 实际涉及服务时读取该服务模块
  -> 只有证据不足或维护时回到 materials / SDK 来源
```

这是一条知识导航，不是固定执行流程。Agent 可以根据现场先读取具体服务资料、补查官方信息或使用
Skill 外合理工具；不要求为了满足层级顺序加载无关文件。

### 停止加载和继续加载

满足以下条件时停止扩大上下文：

- 当前资料已经足以支持下一步判断或向用户提出一个高价值问题；
- 需要的信息应由实时工具查询，而不是继续搜索发布期文档；
- 新文件只会重复已经获得的规则、参数或场景信息；
- 当前是简单查询，入口或单个服务模块已经能够回答；
- 下一层是大规模原始材料，但当前没有明确证据缺口。

出现以下情况时再继续加载：

- 当前目标跨多个服务，公共完成语义、任务恢复或用户表达仍不明确；
- router 已命中场景，但具体服务、前置条件、限制或验证能力尚未确认；
- catalog、guide 和实际工具结果存在冲突，需要追溯来源或版本；
- 现有资料明确标记覆盖不足、已知限制或需要维护期 fallback。

未经处理的 API、网页、日志和工具大输出不作为“加载更多知识”直接带入对话；仍应按大输出策略
保存为 artifact，只读取摘要、结构、少量样本和必要路径。

## 资料分层

知识资料的默认使用顺序：

1. `references/`
2. `materials/hcloud-docs-md/`
3. 已安装的 `huaweicloudsdk*` package
4. 通过 `--sdk-root <sdk-source-root>` 显式传入的 SDK 维护期源码参考

解释：

- `references/`
  - 是清洗后的技能资料。
  - 只保留当前 skill 真的需要的规则、流程、例子和约束。
- `materials/hcloud-docs-md/`
  - 是主要阅读源。
  - 适合 `rg`、摘取命令示例、整理章节内容。
- 已安装的 `huaweicloudsdk*` package
  - 是 SDK 程序化后端和 metadata 证据的运行时来源。
  - curated registry 只限制 `hcloud_sdk_readonly.py`；Agent 编写的任务专用 SDK 代码以官方
    package/API 契约和当前任务授权为边界。
- 上游 `huaweicloud/huaweicloud-sdk-python-v3` 的显式本地 checkout
  - 是本仓库维护和测试参考。
  - 用户机器不要求存在该源码目录。

## 当前原始文档用途

### 用户指南

- 主用途：
  - 配置项
  - 选项说明
  - `--cli-jsonInput`
  - `--cli-output`
  - `--cli-query`
  - `--cli-waiter`
- 主要来源：
  - `materials/hcloud-docs-md/华为云命令行工具服务 KooCLI 用户指南_md_dollar/output.md`

### 常见问题

- 主用途：
  - 认证优先级
  - 缓存位置
  - 日志位置
  - 网络超时
  - 不支持的服务或 operation
  - 空响应体判断
  - 区域参数问题
- 主要来源：
  - `materials/hcloud-docs-md/华为云命令行工具服务 KooCLI 常见问题_md_dollar/output.md`

### 快速入门

- 主用途：
  - 安装方式
  - 初始化配置
  - 新用户的最短上手路径
- 主要来源：
  - `materials/hcloud-docs-md/华为云命令行工具服务 KooCLI 快速入门_md_dollar/output.md`

## 原始资料的已知问题

- 目录页噪声较多
- 页码残留
- 命令换行被打断
- `说明` / `注意` 等块可能被转成异常字符
- 图片类示例会变成图片占位，而不是文本

因此：

- skill 运行时优先看 `references/`
- 只有在 `references/` 没覆盖时，才回到 `materials/`
- 回到 `materials/` 时，使用保留的 `hcloud-docs-md/`
- 回到 SDK 时，优先使用已安装 package；源码目录只做维护期 fallback

## 目标解释、交互知识与派生视图

- `references/goal-capability-guide.md`
  - 属于面向 Agent 的目标解释，不是服务/API 事实源；
  - 企业网站、跨服务资源盘点和成本治理样本引用现有 router、contract、guide、playbook 和脚本；
  - 只组织用户结果、候选能力、替代、动态缺口和完成证据；
  - 不复制 API 参数、实时价格、配额、库存或运行时资源状态。

- `references/backend-selection.md`
  - 属于面向 Agent 的执行后端决策知识；
  - 维护 hcloud 默认优先、SDK 程序化路径、Terraform IaC 意图和等价证据原则；
  - 不替 Agent 固定具体 service、operation、参数或调用顺序。

- `references/public-script-contract.md`
  - 属于公共 CLI 的人类可读契约，与 `script-audience-manifest.json` 的机器声明对应；
  - 只统一分类、兼容输出、artifact 回执和退出语义，不把脚本合并成大 dispatcher。

- `references/runtime-dependencies.md`
  - 属于面向 Agent 和宿主的可移植运行条件契约；
  - 只按当前任务声明 hcloud、服务 SDK、Terraform、OBS、网络和 artifact 条件，不要求全量预装；
  - 安装提示不是授权，网络、凭据注入和写目录仍由宿主提供。

目标样本中的服务事实仍在原 registry、catalog、guide 和 playbook 维护。引用失效时修正目标视图，
不在目标指南中另建一份事实副本。

- `references/interaction-guidance.md`
  - 属于跨服务编写知识，组织 Goal、Option、Progress、Recovery 和 Completion 的用户视图；
  - 读取用户当前要求、Agent workspace 的 task 记忆、已核验证据和运行时事实；
  - 不保存运行时 task 数据，不复制服务事实，也不充当授权账本或执行状态机；
  - 统一信息来源、完成口径和表达维度，具体方案、工具、参数、顺序和回复形式仍由 Agent 决定。

交互指南与目标指南都属于按需加载的编写知识。云资源状态、job 状态、价格、权限和可用性仍以
当前工具观测为准；任务恢复或高影响操作前需要重新查询易变化事实。

## 服务模块接入统一体系

新增或扩展一个服务模块时，先说明：

1. 它支持哪些用户目标或能力；
2. 哪些事实来自 registry、catalog、官方资料或实际工具；
3. 哪些公共原则、任务记忆和交互方法可以直接复用；
4. 哪些限制、错误、验证或操作细节必须保留在服务模块；
5. 查询、变更、等待、错误恢复和完成证据目前覆盖到什么程度；
6. 目标视图、router、coverage 或脚本索引需要增加什么引用。

服务接入不以复制一遍公共安全规则为完成，也不只统计 API 数量。公共规则在 shared core 维护，
服务模块保留专业差异；尚未覆盖的能力明确记录缺口，不用通用描述伪装完整执行闭环。

## 从真实经验晋升共享知识

真实任务中的经验先保留在 task 或脱敏案例中，不自动写回全局规则。建议维护流程：

```text
任务失败或有效经验
  -> 脱敏并区分 Skill、Agent、工具、运行时或云服务责任
  -> 判断是否能跨服务或跨场景复用
  -> 找到应归属的权威事实、编写知识、派生视图或服务模块
  -> 人工评审来源、适用边界和副作用
  -> 更新原所有者并修订引用
```

偶然个案、模型偏好或单一平台限制不直接晋升为全局原则。确有跨场景价值但来源仍不充分时，可以
先标记候选、适用范围和已知缺口，避免把推断写成已确认事实。

## 新鲜度、版本和维护信息

高影响或容易漂移的知识按需维护以下信息，不要求把所有 Markdown 改造成数据库：

- 来源或派生来源；
- 适用的服务、场景、region、版本或工具范围；
- 最近评审时间或对应 Skill 版本；
- 覆盖程度、置信状态和已知缺口；
- 废弃、替代或迁移关系。

低波动编写知识可以在文件级说明维护关系；operation、参数和服务目录优先依赖已有机器索引、
fingerprint 和生成流程。来源失效时修改原所有者及其派生引用，不在下游文件补一份新的事实。
