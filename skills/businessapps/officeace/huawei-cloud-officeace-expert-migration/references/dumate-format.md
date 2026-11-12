# 百度搭子（DuMate）套件格式

安装位置：`$XDG_DATA_HOME/plugins/user/<name>/`
本机实际路径：`%APPDATA%/qianfan-desktop-app/qianfan_desk_xdg/global/data/plugins/user/<name>/`
技能库：同级的 `.../global/data/skills/<slug>/`

## 目录结构

```
<name>/
├── .claude-plugin/plugin.json    # manifest（务必用 .claude-plugin，不是 .claude-plugin 以外的名字）
├── agents/<name>.md              # 入口角色提示词（manifest agents[0].prompt 指向）
└── skills/<slug>/                # 从「已安装技能」复制进来，不是现造
    ├── SKILL.md
    ├── _meta.json                # 源平台发布凭证（contentSha256 / ownerId / publishedAt / slug / version）
    ├── references/ scripts/ templates/ assets/ ...
```

## plugin.json（字段顺序也是约定）

`name` → `displayName` → `version` → `description` → `author` → `license` → `keywords` → `defaultEnabled` → `entry` → `agents` → `skills` → `exampleQuestions`

```json
{
  "name": "contract-risk-review",
  "displayName": "合同风险审查专家",
  "version": "1.0.0",
  "description": "触发判断依据：什么主题该进入本专家",
  "author": { "name": "自定义安装" },
  "license": "UNLICENSED",
  "keywords": ["合同审查", "条款比对"],
  "defaultEnabled": true,
  "entry": "contract-risk-review",
  "agents": [{
    "name": "contract-risk-review",
    "displayName": "合同风险审查专家",
    "description": "同上，触发判断依据",
    "mode": "primary",
    "prompt": "./agents/contract-risk-review.md",
    "skills": ["contract-triage", "clause-redline"]
  }],
  "skills": "./skills/",
  "exampleQuestions": ["帮我看看这份合同能不能签"]
}
```

要点：

- `description` 会被渲染进 `<available_plugins>`，模型据此决定是否进入该专家——写**适用场景**，不写功能罗列。
- `displayName` 中文、**不超过 10 个字**（脚本会校验）。
- 自定义套件 `author.name` 固定 `"自定义安装"`。
- `entry` 必须能对上 `agents[]` 里的某个 `name`；否则运行时按 `mode: "primary"` 回退，再否则取 `agents[0]`。

## SKILL.md

frontmatter 只有两项：`name` + `description`（中文，写适用场景与触发词）。正文结构：`# 标题` + 何时用 + 铁律 + 执行流程 + 输出规范 + 交付前自检 + 边界。

## _meta.json

```json
{ "contentSha256": "<SKILL.md 的 sha256>", "ownerId": "<发布者>", "publishedAt": 1792143302,
  "slug": "docx", "version": "2.0.6" }
```

本地自建技能可省略；从市场安装的技能都有。迁移时删除。

## 官方创建工具（推荐直接用）

位于 `%LOCALAPPDATA%/Programs/DuMate/resources/extra-resource/opencode/skills/plugin-creator/scripts/`：

| 脚本 | 作用 |
|---|---|
| `create_basic_plugin.py <name> --display-name --description --keywords --example-questions --path <父目录>` | 初始化 manifest + agent.md（skills 为空） |
| `add_skill.py <plugin-dir> --source <技能绝对路径>` | 复制技能进 `skills/` 并登记进 `agents[0].skills` |
| `add_connector.py <plugin-dir> --name <connector>` | 声明式 connector（运行时不加载） |
| `validate_plugin.py <plugin-dir>` | 校验 manifest 可解析、entry 可解析、prompt 存在、每个 skill 有 SKILL.md |
| `bump_version.py <plugin-dir>` | 递增版本号——**这是 reload 的触发条件** |

**版本号纪律**：加技能/改 manifest 时脚本不动 version；一轮改动全部完成后手动 bump 一次。中间反复 bump 会导致运行时反复 reload。

## 生效方式

运行时监听 `plugin.json` 的 `version` 变化触发插件 reload，产物出现在 `<available_plugins>`，由 `plugin` 工具激活。

## 迁移到 OfficeAce 时的注意点

| 点 | 处理 |
|---|---|
| `agents/<name>.md` | 搬成 `skills/<专家名>/SKILL.md`，正文原样，补 frontmatter |
| `_meta.json` | 删除，记入报告 |
| `enabled`/`entry`/`exampleQuestions`/`license` | 丢弃 |
| `agents[0].connectors` | 丢弃数组，转成提示词里的降级说明 |
| 多 agent | 只取入口 agent，其余当作普通技能或人工重建 |
| 版本 reload | OfficeAce 无此机制，改完重启 |
