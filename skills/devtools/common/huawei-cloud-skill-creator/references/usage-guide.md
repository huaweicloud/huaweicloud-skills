# Usage Guide — Huawei Cloud Skill Creator

Detailed 11-step workflow for creating a Huawei Cloud AI Shell Skill.

---

## 执行约束（Guardrails）

1. **必须先交互，后创建** — 未完成需求分析的用户确认，绝对不允许创建任何文件或目录
2. **一次只问一个问题** — 任何时候都不允许同时问两个或以上的问题
3. **必须等待用户回答** — 问完问题后停止，等用户回复后再继续
4. **必须输出确认总结** — 每 5 轮询问或维度覆盖完成后，输出格式化的需求总结表格让用户确认
5. **用户不确认就不前进** — 用户拒绝或修改 → 回到询问循环；用户确认 → 才进入下一步
6. **如果用户说"先创建"或类似跳过询问的话** — 礼貌提醒：在创建之前需要先了解需求
7. **每条指令必须实际执行验证** — Agent 写入 SKILL.md 的每一条命令，写入过程中必须用 CLI→SDK→API 三级降级策略实际调用验证
8. **写指令即时验证** — 每写完一条指令立即执行，成功则写入，失败先查语法，语法无误则降级

---

## Step 1: 需求分析 — 苏格拉底式交互询问

**在完成这一步之前，禁止执行任何后续步骤。**

### 询问方式

每次**只问一个问题**，等用户回答后，基于回答提出下一个深入的问题。覆盖 4 个维度：

**维度 1 — 目标服务/产品：**
> "你想封装哪个华为云服务？比如 ECS、VPC、OBS、RDS 等。如果不太确定，可以描述一下你的使用场景。"

**维度 2 — 功能范围：**
> "你希望这个 Skill 主要做什么？比如：查询管理、故障诊断、自动部署、监控告警？"

**维度 3 — CLI/API 操作：**
> "你大概需要用到哪些操作？比如 List、Show/Get、Create、Delete、Start/Stop？"

**维度 4 — 触发场景：**
> "在什么场景下 Agent 会用到这个 Skill？比如日常巡检、故障排查、自动扩缩容？"

### 确认总结（每 5 轮或维度覆盖完成时）

```markdown
📋 **需求总结**

| 维度 | 内容 |
|------|------|
| 目标服务/产品 | ... |
| 功能范围 | ... |
| CLI/API 操作 | ... |
| 触发场景 | ... |
| 是否涉及成本 | 是/否 |

**以上是你目前提供的需求信息。请问：**
1. **是否确认**这些就是你需要的功能？
2. **还需要补充或修改什么吗？**
```

- ✅ 用户确认 → 进入 Step 2
- ❌ 用户拒绝或修改 → 从有问题的维度开始新一轮追问
- 如果用户信息足够明确，可以提前总结，不必硬等 5 次

### 追问技巧

| 用户说 | 追问 |
|--------|------|
| "管理 ECS" | "你具体想管理哪些方面？查询状态、创建实例、还是启停操作？" |
| "帮我看看能不能做这个" | "这个场景下，你希望最终得到什么结果？" |
| 回答模糊 | 用具体例子引导："比如说，你想不想做到一键列出所有运行中的服务器？" |

---

## Step 2: 命名与目录结构

命名格式：`{platform}-{product}-{function}`
- platform = `huawei-cloud`
- product = 服务缩写（ecs, vpc, obs, rds, iam, cce 等）
- function = 功能描述（manage, diagnosis-workflow, deploy 等）
- 示例：`huawei-cloud-ecs-diagnosis-workflow`

域目录（参见 `references/naming-conventions.md`）：
compute / network / storage / database / security / monitoring / middleware / devtools / solution

```text
{domain}/{skill-name}/
├── SKILL.md                   # Required
├── i18n/
│   └── zh-CN/
│       └── SKILL_CN.md        # Recommended
├── references/                # Required
│   ├── dataflow-diagram.md    # Required: Mermaid diagram
│   ├── cli-installation-guide.md
│   ├── iam-policies.md        # Required
│   ├── verification-method.md
│   ├── acceptance-criteria.md
│   └── related-commands.md
├── scripts/                   # As needed
├── templates/                 # Optional
└── demo/                      # Optional
```

---

## Step 3: API 研究

```bash
hcloud ECS ListServers --cli-region={region}
hcloud ECS ListServers --help
```

如 CLI 未注册对应 API，查阅华为云 OpenAPI 文档。

---

## Step 3.5: 指令执行验证（强制性）

**每一条 Agent 写入 SKILL.md 的 hcloud 命令，在写入过程中必须实际执行验证。** 不允许只写不验。

### 三级降级策略

按 **CLI → SDK → API** 顺序依次尝试：

```python
# 伪代码 — 实际由 Agent 在写指令过程中执行
def verify_command(svc, op, params):
    # 1st: CLI
    result = exec(f"hcloud {svc} {op} {params} --limit=1")
    if result.success:
        return "CLI_VERIFIED"
    
    # 如果是语法问题 → 修复后重试 CLI
    if is_syntax_error(result):
        fix_syntax(svc, op, params)
        return verify_command(svc, op, params)
    
    # 非语法问题 → 2nd: SDK
    result = exec_sdk(svc, op, params)
    if result.success:
        return "SDK_VERIFIED"
    
    # 3rd: API
    result = exec_api(svc, op, params)
    if result.success:
        return "API_VERIFIED"
    
    return "MANUAL_VERIFICATION_NEEDED"
```

### 执行细则

| 命令类型 | 验证方式 | 通过条件 |
|----------|----------|----------|
| List/Query | 加 `--limit=1` 执行 | 返回有效 JSON（可为空数组） |
| Show/Get/Describe | 使用 `{id}` 占位符，尝试不带 id 执行看错误提示 | `--help` 通过 + 错误提示包含期望的参数名 |
| Create/Update/Delete | 先 `--help` 语法检查 + `--dry-run=true`(如支持) | 语法通过 + dry-run 无错误 |
| 其他 | 至少 `--help` 语法检查 | 返回帮助信息 |

### 降级条件

| 失败原因 | 处理方式 |
|----------|----------|
| `Operation X is not supported` | CLI 操作名错误 → 查 `hcloud {Svc} --help` 修复，重试 CLI |
| `parameter X is not recognized` | 参数名错误 → 查 `hcloud {Svc} {Op} --help` 修复参数名 |
| `The --param format must be '--param=value'` | 格式错误 → 修复格式 |
| hcloud CLI 未安装 | 降级到 SDK |
| SDK 模块未安装 | 自动 `pip install huaweicloudsdkcore` 后重试 |
| API endpoint 不可达 | 检查 endpoint 名，重试；仍失败 → 标记需人工验证 |

### REST API 降级特殊规则

**当降级到 REST API（3rd）时，Agent 严禁自行猜测 API 路径。** 必须要求用户提供真实的端点：

```text
Agent: "CLI 和 SDK 均无法调用此操作。请提供此操作的 REST API 端点。
       格式：{HTTP方法} {完整URL}
       示例：POST https://bss.cn-north-4.myhuaweicloud.com/v2/promotions/benefits/activate-coupons"
```

| 场景 | Agent 行为 |
|------|------------|
| 用户提供了完整 API 端点 | 使用该端点执行验证，通过后写入 SKILL.md 并备注 `(API verified, endpoint confirmed by user)` |
| 用户不确定 | 标记为 `⛔ 需人工验证`，绝不自行构造 |
| 用户提供了但不完整 | 追问确认 method、path、请求体格式 |

---

## Step 4: 生成数据流图

每个 Skill **必须**包含 Mermaid flowchart 图。

```bash
bash scripts/generate-dataflow-diagram.sh {skill-path} --output={skill-path}/references/dataflow-diagram.md
```

或使用 `templates/dataflow-diagram.md.template` 手动生成。

---

## Step 5: 生成 SKILL.md

使用 `templates/SKILL.md.template`，包含：
- **YAML Frontmatter**: name, description（含 "Triggers include:"）, tags, version
- **Body sections**: Overview, Prerequisites, Main Steps, Edge Cases, Verification, References
- CLI 命令使用 `{placeholder}`，不硬编码 AK/SK
- 正文不超过 500 行

---

## Step 6: 生成 references/

| 文件 | 必须 | 内容 |
|------|------|------|
| `dataflow-diagram.md` | 是 | Mermaid 数据流图 |
| `cli-installation-guide.md` | 推荐 | CLI 安装和初始化 |
| `iam-policies.md` | 是 | 最小权限策略 JSON |
| `verification-method.md` | 推荐 | 验证方法 |
| `acceptance-criteria.md` | 推荐 | 验收标准 |
| `related-commands.md` | 按需 | 命令速查 |

---

## Step 7: 生成 scripts/（按需）

脚本类型：分析脚本、部署脚本、数据处理脚本、工具脚本。
要求：有意义的名称、shebang、环境变量获取凭据、参数验证、错误处理。

---

## Step 8: 生成 templates/ 和 demo/（按需）

- `templates/`: IaC 模板、API 请求模板、报告模板
- `demo/`: 示例请求/响应、示例配置

---

## Step 9: 生成 i18n/

默认创建简体中文本地化：
1. 创建 `i18n/zh-CN/`
2. 创建 `i18n/zh-CN/SKILL_CN.md` — SKILL.md 的中文翻译
3. CLI 命令和代码块保持英文

使用 `templates/i18n-zh-CN-SKILL_CN.md.template`。

---

## Step 10: 质量验证

```bash
bash scripts/validate-skill.sh {skill-path}
```

验证项参见 `references/quality-checklist.md` 和 `references/acceptance-criteria.md`。
验证通过后必须进入 Step 11（功能测试）。

---

## Step 11: 功能测试（必须实际执行）

对所有 CLI 命令执行自动化功能测试，**每一条命令必须至少通过一级实际执行验证**：

```bash
# 1st: CLI 直接执行
bash scripts/test-cli-commands.sh {skill-path} --executor cli

# 2nd: SDK 降级（CLI 失败且非语法问题）
bash scripts/test-cli-commands.sh {skill-path} --executor sdk

# 3rd: API 降级（curl + AK/SK 签名）
bash scripts/test-cli-commands.sh {skill-path} --executor api
```

该脚本自动完成：
1. 从 SKILL.md 和 references/ 中提取所有 `hcloud` 命令
2. 对每条命令：
   - 先 `--help` 语法验证
   - 再对只读操作（List/Show/Get/Describe/Query）执行实时调用（CLI → SDK → API 降级）
   - 执行成功 → 记录结果 ✅
   - 执行失败 → 判断是否语法问题

### 指令验证流程（Agent 在写指令时执行）

```text
写指令
  │
  ▼
执行 CLI (hcloud {svc} {op} --param=value)
  │
  ├── ✅ 成功 → 写入 SKILL.md
  │
  └── ❌ 失败
        │
        ▼
      是语法错误吗？
        │
        ├── ✅ 是语法错误 → 查看 hcloud {svc} {op} --help → 修复命令 → 回到 CLI 执行
        │
        └── ❌ 不是语法错误
              │
              ▼
             降级到 SDK (python3 huaweicloudsdk)
              │
              ├── ✅ 成功 → 写入 SKILL.md + 备注 "(SDK verified)"
              │
              └── ❌ 失败
                    │
                    ▼
                   降级到 API (curl + AK/SK 签名)
                    │
                    ├── ✅ 成功 → 写入 SKILL.md + 备注 "(API verified)"
                    │
                    └── ❌ 失败 → 标记 ⛔ 需人工验证
```

### 降级实现示例

**CLI 执行**（1st priority）：
```bash
hcloud ECS ListFlavors --cli-region=cn-north-4 --limit=1
```

**SDK 执行**（2nd priority — CLI 失败时）：
```bash
python3 -c "
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v1 import EcsClient, ListFlavorsRequest
cred = BasicCredentials(os.environ['HCLOUD_AK'], os.environ['HCLOUD_SK'])
client = EcsClient.new_builder().with_credentials(cred).with_region('cn-north-4').build()
resp = client.list_flavors(ListFlavorsRequest(limit=1))
print(resp)
"
```

**API 执行**（3rd priority — SDK 失败时）：
```bash
curl -X GET "https://ecs.cn-north-4.myhuaweicloud.com/v2/{project_id}/flavors?limit=1" \
  -H "Authorization: SDK-HMAC-SHA256 ..." \
  -H "X-Sdk-Date: ..." \
  -H "Host: ecs.cn-north-4.myhuaweicloud.com"
```

### 测试规则
- Create/Update/Delete/Start/Stop 只做 `--help` 语法测试，不经用户确认绝不执行
- List/Show/Get 可以用 `--limit=1` 执行
- 测试结果必须写入 `references/test-report.md`

### 资源型 Skill 的完整生命周期测试

> 当创建的 Skill 包含 Create/Delete 等资源创建/销毁操作时，不得只做 `--help` 测试跳过。

#### 流程

```
描述测试计划 → 确认凭证 → 创建资源 → 测试功能 → 释放资源 → 生成报告
```

**Step A: 描述测试计划**

```markdown
📋 **功能测试计划 — {skill-name}**

本 Skill 包含资源变更操作，需要进行完整生命周期测试：

| 操作 | 测试资源 | 测试后动作 |
|------|----------|-----------|
| `hcloud XXX Create{Resource} --...` | 创建 1 个最小规格 {resource} | ✅ 测试完成后删除 |
| `hcloud XXX Show{Resource} --...` | 查询刚创建的资源 | — |
| `hcloud XXX Delete{Resource} --...` | 删除测试资源 | — |

预计费用：测试期间按需计费，测试完成后立即释放。
是否开始测试？(yes/no)
```

- ✅ 用户确认 → 继续
- ❌ 用户拒绝 → 跳过资源测试，仅做 `--help` 语法验证

**Step B: 确认凭证**

```bash
echo "HUAWEI_ACCESS_KEY=${HUAWEI_ACCESS_KEY:-未设置}"
echo "HUAWEI_SECRET_KEY=${HUAWEI_SECRET_KEY:-未设置}"
```

如未设置，询问用户提供 AKSK 或设置环境变量。
> 🔒 安全规则：AKSK 仅用于当前会话的环境变量，绝不写入文件、日志或 SKILL.md。

**Step C: 创建测试资源**

使用最小规格创建测试资源：
```bash
hcloud {SERVICE} Create{Resource} --cli-region={region} --name=test-skill-verify-{timestamp} --flavor={min-spec} ...
```

验证创建成功：
```bash
hcloud {SERVICE} Show{Resource} --cli-region={region} --{resource}_id={created_id}
```

**Step D: 测试功能**

对创建的测试资源执行 Skill 中定义的功能测试。

**Step E: 释放测试资源**

测试完成后，**必须**清理测试资源。验证资源已释放。
> ⚠️ 强制规则：无论测试是否成功，都必须执行资源释放。如果 Delete 操作失败，再次尝试并告知用户手动确认。

**Step F: 生成测试报告**

将资源生命周期测试结果追加到 `references/test-report.md`。

#### 注意事项

| 场景 | 处理方式 |
|------|----------|
| API 不支持最小规格 | 使用该服务允许的最小规格创建 |
| 创建失败 | 分析错误信息（权限/配额/参数），修复后重试 |
| 释放失败 | 重试 3 次，仍失败则告知用户手动清理 |
| 用户不想做资源测试 | 回退到 `--help` 语法验证，注明"资源测试已跳过" |
| 用户提供了错误的 AKSK | 提示认证失败，让用户重新提供 |
| 测试中断 | 告知用户未释放的资源 ID 和区域，建议手动清理 |

---

## 参考文档

- [skill-spec-generic.md](skill-spec-generic.md) — 完整规范
- [naming-conventions.md](naming-conventions.md) — 命名约定
- [quality-checklist.md](quality-checklist.md) — 质量检查清单
- [cli-installation-guide.md](cli-installation-guide.md) — CLI 安装指南
- [iam-policies.md](iam-policies.md) — IAM 权限策略
- [verification-method.md](verification-method.md) — 验证方法
- [dataflow-diagram.md](dataflow-diagram.md) — 数据流图模板
- [acceptance-criteria.md](acceptance-criteria.md) — 验收标准
- [related-commands.md](related-commands.md) — 命令速查
