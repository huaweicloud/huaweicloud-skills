# WorkBuddy 专家包 / 专家团格式

## 目录结构

```
<pkg>/
├── .codebuddy-plugin/plugin.json     清单（唯一必需文件）
├── agents/<agent>.md                 每个角色一份：frontmatter + 人设正文
├── skills/<slug>/                    包级技能，团队内全部成员共享
├── avatars/                          角色头像（<agent>.png、team.png）
├── assets/  docs/  references/       团队协作规范、模板、样例
├── scripts/                          质量闸门、自检脚本
├── settings.json                     运行参数（可为空）
└── README.md
```

## 清单关键字段

| 字段 | 说明 | 迁移去向 |
|---|---|---|
| `name` / `version` | 包名与版本 | 团队 teamId 前缀 `wb-team-`；新专家 ID 的哈希源 |
| `expertType` | `agent`（单专家）/ `team`（专家团） | 决定产出 1 个还是 N 个专家 + 是否写 `user-teams.json` |
| `agents[]` | 角色 md 路径列表 | 每个 md → 1 个专家卡 + 1 个主提示词技能 |
| `skills[]` | 包级技能路径 | 复制为 OfficeAce 技能，列入**每个**成员的 `skills` |
| `agentName` | 入口角色 | 单专家时为专家本体；团队时通常等于主理人 |
| `teamInfo.leadAgent` | 主理人 | `user-teams.json` 的 `leaderExpertId` + `members[role=leader]` |
| `teamInfo.memberAgents[]` | 成员角色 | `members[role=teammate]` |
| `members[]` | 成员展示信息（id/displayName.zh/profession/avatar/role） | 角色 md 缺 `displayName` 时的兜底来源 |
| `displayName.zh` | 包展示名 | 单专家→displayName；团队→团队 displayName |
| `displayDescription.zh` | 一句话能力 | `roleDescription`（成员 md 描述是英文时用它兜底） |
| `categoryId` | 如 `05-MarketingGrowth` / `06-ContentCreative` | 映射 OfficeAce `category`（见下表） |
| `quickPrompts[]` | 3 条开场问题 | 团队的 `scenarios`（取前 3 条）+ `summonPrompt` |
| `tags[]` | 场景标签 | 团队的 `tags[]`（`{id: kebab(label), label, color}`） |
| `defaultInitPrompt.zh` | 默认开场 | `quickPrompts` 缺失时的 `scenarios`/`summonPrompt` |
| `avatar` | 头像相对路径 | 复制成应用 `/avatars/experts/<角色名>.png` 后写进卡片 `avatar`；源包无图则用应用内置头像（**绝不写不存在的路径**，否则 UI 显示乱码） |

## 角色 md 的 frontmatter

```yaml
name: market-scout              # → 专家 name / 技能 slug / ID 哈希源
description: "Use when ..."     # 英文时仅作兜底
displayName: { zh: 纪颜色 }      # → displayName + nickname + @提及
profession:  { zh: 市场情报分析师 }  # → 报告中展示的职业
maxTurns: 80                    # 丢弃（OfficeAce 无此参数）
```

正文是**真实人设提示词**，直接成为 OfficeAce 主提示词技能的 SKILL.md 正文（无需合成，保真度三个平台里最高）。

## categoryId 映射

| 源含关键词 | OfficeAce category |
|---|---|
| Legal / Law | `legal` |
| Engineer / Tech / Data | `tech` |
| Research / Insight / Design | `insight` |
| 其余（Marketing / Content / Business） | `business` |

## 专家团 → user-teams.json

```json
{
  "teamId": "wb-team-product-launch-team",
  "displayName": "新品上市作战团",
  "description": "…",
  "scenarios": ["…", "…", "…"],
  "leaderExpertId": "expert-product-launch-team-team-lead-21cdb666",
  "members": [
    {"expertId": "expert-product-launch-team-team-lead-21cdb666", "role": "leader", "displayName": "陆掌舵"},
    {"expertId": "expert-market-scout-b39039a0", "role": "teammate", "displayName": "纪颜色"}
  ],
  "visibility": "private",
  "creationSource": "user",
  "teamMode": "predefined",
  "teammateMode": "build_mode",
  "maxDebateRounds": 10,
  "tags": [{"id": "product-launch", "label": "新品上市", "color": "#8B5CF6"}],
  "summonPrompt": "我们要给一个新产品做上市，请作战团一起出方案"
}
```

要点：
- 团队型角色（主理人 / 分流器）在 OfficeAce 侧**同样要进专家目录**（`users/<uid>/user-experts.json`）：`/api/experts` 只认这份文件，只登记在 `user-teams.json` 时团队运行时解析不到主理人（实测报「主理人出错」）。早先按「只进团队」处理是错的，1.2.0 已改；
- 团队 ID 固定 `wb-team-<包名>`，重跑覆盖同一条，不产生重复团队。

## ID 幂等规则

WorkBuddy 包的旧 ID 由上一代迁移脚本生成（形如 `expert-market-scout-b39039a0`），**无法用当前公式复现**。因此：

1. 已存在同名专家卡 → **沿用卡里的 `expertId` / `agentId`**（不打断既有会话引用）；
2. 新专家 → `expert-<name>-<sha8(name+version)>`。

## 与另外两家的差异

| | WorkBuddy | 千问办公 | 百度搭子 |
|---|---|---|---|
| 一包多角色 | **支持（专家团）** | 不支持 | 不支持 |
| 人设文件 | `agents/*.md`（真文件） | 无（靠元数据合成） | `agents/*.md` |
| 包级共享技能 | 支持 | 无 | 无 |
| 团队注册 | `teamInfo` + `members` | 无 | 无 |
| 迁移脚本 | `migrate_workbuddy.py` | `migrate_suite.py` | `migrate_suite.py` |
