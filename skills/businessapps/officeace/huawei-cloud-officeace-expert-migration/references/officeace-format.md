# OfficeAce 专家格式（迁移目标）

两个根目录，分工不同，别混：

- **数据目录** `~/.office-claw`：专家卡、catalog、用户目录、用户专家/团队列表。
- **应用安装目录** `<OfficeAce 安装根>/.office-claw`：custom 技能的**持久化源**（`skills/` + `installed-skills.json` + `capabilities.json`）。

核心事实：**OfficeAce 没有「套件」概念，只有「专家」+「技能」+「团队」，且一个专家要在七处同时登记。**

## 目录结构

```
~/.office-claw/
├── connector-owner.local.json      # {"ownerUserId": "<a>:<b>"} —— 活跃用户的唯一权威标识
├── experts/<name>.json             # 专家卡（这个人是谁）
├── skills/<slug>/SKILL.md          # 技能副本（运行时会从应用目录同步，单写这里重启会丢）
├── user-catalogs/
│   ├── catalog.json                # 专家清单（列表里有没有这一项）
│   └── <userId>.json               # 用户目录：breeds（完整卡+变体）+ roster（编排可见性）
├── users/<uid>/                    # uid = ownerUserId，冒号转 %3A
│   ├── user-experts.json           # UI 专家列表的真正数据源
│   └── user-teams.json             # 专家团定义
└── .office-claw/                   # 应用目录的镜像（installed-skills.json 等）

<OfficeAce 安装根>/.office-claw/
├── skills/<slug>/                  # 技能本体，必须装这里
├── installed-skills.json           # {"skills": {"<slug>": {"source":"local","installedAt":...,"name":<slug>}}}
└── capabilities.json               # 启动时再生：builtin + SkillHub + 上述存储
```

## 一、专家卡 `experts/<name>.json`

```json
{
  "expertId": "expert-workplace-writer-bd7e4279",
  "name": "workplace-writer",
  "displayName": "白成章",
  "nickname": "白成章",
  "avatar": "/avatars/experts/workplace-writer.png",
  "category": "business",
  "mentionPatterns": ["@白成章"],
  "roleDescription": "把粗略想法直接写成能发出去的职场文本…（≤80 字）",
  "personality": "我是白成章，一名…",
  "strengths": [],
  "skills": ["workplace-writer"],
  "visibility": "private",
  "creationSource": "user",
  "defaultModel": "glm-5",
  "providerProfileId": "modelarts-shared"
}
```

要点：

- `expertId` 格式 `expert-<name>-<8位hex>`，**七处必须同一个值**。
- `skills` 是**技能目录名数组**，不是路径。约定：把与专家同名的技能放第一位，作为角色提示词。
- `displayName` 是本名（像人名），`nickname` 是 `@` 唤起的名字，两者通常相同。
- `personality` 是自我介绍句，出现在专家详情页。

## 二、技能 `skills/<slug>/SKILL.md`

```yaml
---
name: pricing-model
description: "把方案范围换算成能算清毛利的报价…（何时用 + 覆盖什么 + 触发词）"
agent_created: true
---
```

- frontmatter 只需 `name` + `description`；`agent_created: true` 标记为 agent 创建，便于区分内置技能。
- `description` 是**路由依据**，必须写「什么场景该用这个技能」，不能只写功能。
- 正文没有固定骨架，但事实上的好写法是：何时用 / 铁律 / 执行流程（带门禁）/ 输出规范 / 交付前自检 / 边界。
- 附件目录不限名字，靠正文里的相对路径引用（`references/`、`scripts/`、`templates/`、`assets/`、`rules/`、`evals/` 都有先例）。

## 三、注册项 `user-catalogs/`

### catalog.json

```json
{
  "updatedAt": "2026-10-23T09:53:00.0000000Z",
  "experts": [{
    "creationSource": "user", "visibility": "private",
    "name": "workplace-writer", "agentId": "expert-workplace-writer-bd7e4279",
    "avatar": "/avatars/experts/workplace-writer.png"
  }],
  "teams": []
}
```

### 用户目录 `<userId>.json`

```json
{
  "version": 2,
  "breeds": [{
    "id": "expert-workplace-writer-bd7e4279",
    "color": { "primary": "#D4574A", "secondary": "#FAE0DC" },
    "defaultVariantId": "expert-workplace-writer-bd7e4279-default",
    "displayName": "白成章", "nickname": "白成章",
    "avatar": "/avatars/experts/workplace-writer.png",
    "features": { "sessionChain": true },
    "agentId": "expert-workplace-writer-bd7e4279",
    "creationSource": "user", "name": "workplace-writer",
    "visibility": "private", "category": "business",
    "variants": [{
      "id": "expert-workplace-writer-bd7e4279-default",
      "skills": ["workplace-writer"],
      "personality": "…",
      "cli": { "command": "vendor/jiuwenclaw.exe", "outputFormat": "json" },
      "mcpSupport": false,
      "accountRef": "modelarts-shared",
      "providerProfileId": "modelarts-shared",
      "strengths": [], "defaultModel": "glm-5", "provider": "relayclaw"
    }],
    "mentionPatterns": ["@白成章"],
    "roleDescription": "…"
  }],
  "roster": {
    "expert-workplace-writer-bd7e4279": {
      "family": "expert-workplace-writer-bd7e4279",
      "roles": ["assistant"], "lead": false, "available": true,
      "evaluation": "…"
    }
  }
}
```

要点：

- `breeds[].id` / `agentId` 与专家卡 `expertId` 相同；`roster` 的 key 也是它。
- `variants[0].skills` 必须与专家卡 `skills` 完全一致，否则技能加载不全。
- `roster` 缺失 → 专家不出现在编排候选里，`@` 也唤不起。
- 活跃用户目录只看 `connector-owner.local.json` 的 `ownerUserId`（目录名冒号转 `%3A`）；
  按 mtime 或条数猜在多账号机器上必错，会写进别人的目录。

### 注册契约（缺一项，应用启动直接崩）

运行时按内存态解析上述结构，以下任一项不满足抛 `TypeError`，表现为「启动失败」而不是降级：

| 约束 | 说明 |
|---|---|
| `breeds` 必须是**数组** | 对象会让 `.some()` 直接抛 `Cannot read properties of undefined` |
| `variants` 必须是**数组**且非空 | 空数组等于没有可运行的变体 |
| `agentId` 非空且**全局唯一** | 重复会让注册表覆盖、会话串人 |
| `defaultVariantId` 必须**存在** | 指向不存在的变体，取默认变体时 undefined |
| 默认变体必须有 `mentionPatterns` | 编排层读它建 `@` 索引，缺失即崩 |
| `variants[].provider` 建议给 `relayclaw` | 缺失只降级为不可路由（专家在但唤不起） |

## 四、用户级列表

### `users/<uid>/user-experts.json`

```json
{ "experts": [ { "expertId": "...", "displayName": "...", "avatar": "...", "skills": ["..."] } ] }
```

- 这是 **UI 专家列表的真正数据源**，也是 `/api/experts` 的**唯一**来源：只写 `experts/*.json` 卡片不会出现在列表里，运行时也解析不到该角色。
- 条目字段与专家卡基本一致，另含 `visibility/defaultModel/providerProfileId`；新增时从该文件已有条目取模板。
- **团队的主理人与每个成员都必须在这里有一条**。旧版把编排角色排除在外的做法会让团队召唤直接失败：报「主理人出错」，`memberProfiles` 回落成 `expertId`（界面显示英文 id）。专家列表因此多出几个与团队同名的入口，是可接受的代价。
- `personality` 与 `defaultModel/providerProfileId` 必须与专家卡同值——只改一处会出现「详情页有人设、列表里还是简介」。`verify_install.py` 会逐条比对。

### `users/<uid>/user-teams.json`

```json
{
  "version": 2,
  "teams": [{
    "teamId": "wb-team-team-test",
    "displayName": "咖啡店开业作战团",
    "avatar": "/avatars/experts/team-test.png",
    "leaderExpertId": "expert-team-test-lead-8fa62886",
    "members": [
      { "expertId": "expert-team-test-lead-8fa62886", "role": "leader", "displayName": "团主理人" },
      { "expertId": "expert-menu-planner-8c69861e", "role": "teammate", "displayName": "菜单规划师" }
    ],
    "scenarios": ["我要开一家咖啡店，帮我出一份开业方案"],
    "summonPrompt": "…",
    "tags": [{ "id": "餐饮", "label": "餐饮", "color": "#8B5CF6" }],
    "teamMode": "predefined",
    "teammateMode": "build_mode",
    "maxDebateRounds": 10,
    "visibility": "private",
    "creationSource": "user"
  }]
}
```

- `teamId` 约定 `wb-team-<包名>`，重跑覆盖同一条，不产生重复团队。
- `members[].expertId` 必须是已注册的 `expertId`；`role` 取 `leader` / `teammate`，且**有且只有一个 `leader`**，与 `leaderExpertId` 一致。`members[].displayName` 要写，否则团队任务卡片显示英文 id。
- 团队头像写 `teams[].avatar`（前端 TeamAvatar 读这个字段，缺省时回落到内置 `agentteams.png`）。
- **队级标量必须显式写全**：`lifecycle / dispatchMode / spawnMode / enableSwarmflow / enablePermissions / maxIterations / completionTimeout`。省略任一项会回退应用内置默认值（不同版本默认值可能不同），迁移前后行为就不一致了。1.2.0 起的取值见 `runtime_contract.TEAM_SCALARS`。

## 四之二、运行态契约（能跑起来的关键）

| 位置 | 字段 | 取值要求 | 违反了会怎样 |
|---|---|---|---|
| `breeds[].variants[]` | `provider` | **必须** `relayclaw` | 改成别的值，专家会从 `/api/agents` 整批消失 |
| `breeds[].variants[]` | `providerProfileId` + `defaultModel` | 必须是本机 `~/.office-claw/model.json` 里真实存在的组合 | 召唤即鉴权失败（团队表现为「主理人出错」） |
| `breeds[].variants[]` | `personality` | `agents/*.md` 全文（去 frontmatter / 一级标题），不是一句话简介 | 成员没有判据，输出泛泛而谈、四个成员口径一致 |
| `roster[<id>]` | `family/roles/lead/available` + `provider/providerProfileId/defaultModel` | 运行态必需；`lead=true` 只给主理人 | 缺 `roles` 列表接口崩；缺运行配置团队解析不到模型 |
| `skills/<slug>/SKILL.md` | 脚本引用 | **绝对路径**，指向真实存在的文件 | 团队会话 cwd 不在技能目录，`python scripts/x.py` 找不到文件，模型会自写算法 |
| `experts/<name>.json` | `personality` | 完整正文（≥ 200 字），且 ≠ `roleDescription` | 人设退化成简介，分工消失 |

`model.json` 形如 `{ "<providerProfileId>": [{"id": "<modelId>"}, ...] }`；迁移脚本用它挑组合，
校验脚本用它验合法性。**不要凭记忆写模型名**，也不要用 WorkBuddy 侧的 `providerProfileId`——两套平台不通用。

## 五、头像

前端渲染是 `<img src="{avatar}" alt="{displayName}">`，所以：

- `avatar` 必须是 `/avatars/...` 形式且**文件真实存在**，落在 `<安装根>/packages/green-package/web/dist/avatars/` 下。
- 文件不存在 → 浏览器显示 alt 文本，中文名挤进 40px 圆框就是用户看到的「乱码」。
- 指向 8×8 纯色占位图 → 圆形头像里一块色斑，等于没做视觉设计。判据：短边 < 64px 或体积 < 2KB。
- 规格：512×512 PNG，正方形、无外圈留白（前端会再裁圆形，留白会形成「双圆」）、无文字水印。
- 同一个专家在七处的 `avatar` 必须同值，否则列表/详情/团队三个界面显示不一致。

## 六、生效方式

- 专家/团队/技能注册：新建会话即生效（实测无需重启）；界面或当前会话仍显示旧状态时重启一次。
  **团队实例在创建时会快照角色设定**，改完团队成员要新建一个团队会话才套用。
- 头像图片：静态文件，替换即生效（浏览器可能缓存旧 404，需硬刷新）。
- 应用运行期间会按内存态**回写**注册文件——测试或修改注册表前先关掉 OfficeAce，否则改动会被覆盖。
- `capabilities.json` 每次启动再生，custom 技能必须同时存在于应用目录 `skills/` 且登记在 `installed-skills.json`。

## 校验清单

| 检查 | 命令 |
|---|---|
| 专家卡可解析、字段齐全 | `verify_install.py` |
| 技能目录存在且 slug 对得上 | `verify_install.py` |
| `avatar` 指向的文件存在且不是占位图 | `verify_install.py` |
| catalog.json 与 experts/ 一一对应 | `verify_install.py` |
| breed/roster 覆盖到该专家、skills 数组一致 | `verify_install.py` |
| capabilities.json 已登记全部技能 | `verify_install.py` |
| 活跃用户 user-experts.json 包含专家 | `verify_install.py` |
| 注册契约（数组/唯一 id/默认变体/mentionPatterns） | 启动冒烟：`OFFICE_CLAW_STORAGE_CLIENT=sqlite tools/node/node.exe packages/api/dist/cli.js`，看日志有无 Fatal |
