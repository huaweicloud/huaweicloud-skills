# 字段级映射矩阵

三个平台的套件本质上是**同一套东西的三种外层约定**：一份元数据 + 一个角色提示词 + 若干能力单元 + 若干外部依赖声明。差异集中在这四件事的放法与命名。

## 一、元数据

| 语义 | 千问办公 | 百度搭子 | OfficeAce | 迁移处理 |
|---|---|---|---|---|
| 技术标识 | `plugin.json.name` | `plugin.json.name` | 专家卡 `name` | 直接沿用，规范化为 kebab-case |
| 中文名 | `displayNameCn` | `displayName`（限 10 字） | `displayName` | 沿用；超过 10 字要截断或另起短名 |
| 英文名 | `displayNameEn` | — | — | 丢弃 |
| 一句话简介 | `descriptionZh` | `description` | `roleDescription`（≤80 字） | 从长描述中截取到句末，避免半句 |
| 详述 | `description`/`descriptionEn` | — | — | 进技能 `description` 与报告，不进专家卡 |
| 版本 | `version` | `version` | 专家卡无版本字段 | 记入 `migration-manifest.json` |
| 作者 | `author.name` | `author.name` | `creationSource: "user"` | 丢弃作者，标为本地创建 |
| 标签 | `tags` | `keywords` | — | 丢弃（OfficeAce 靠 `category` 归类） |
| 分类 | `category` | — | `category` | 沿用，缺失给 `business` |
| 示例问题 | — | `exampleQuestions` | — | 丢弃；OfficeAce 无此字段 |
| 入口 agent | — | `entry` + `agents[0].name` | 约定：与专家同名的技能 | 用于生成 persona 技能 |
| 默认启用 | — | `defaultEnabled` | — | 丢弃（OfficeAce 无该开关） |

## 二、角色提示词

| 语义 | 千问办公 | 百度搭子 | OfficeAce |
|---|---|---|---|
| 载体 | 无独立文件 | `agents/<name>.md`（manifest `prompt` 指向） | `skills/<专家名>/SKILL.md` |
| 结构 | — | `# 身份` + 适用场景 + 身份与风格 + 全流程工作流 + 技能指引 + 原则与边界 + 开场约定 | 同左（OfficeAce 专家也用 markdown 技能存提示词） |
| 迁移动作 | 无源 → 按元数据合成一份最小可用提示词，文件末尾标注「合成，待人工复核」 | 正文原样搬入，补 frontmatter 与 H1 | — |

**为什么 OfficeAce 用技能而不是单独字段**：OfficeAce 的专家卡只有 `roleDescription`（一句话），真正的行为约束来自被加载的技能。把角色提示词做成「与专家同名的技能」并放在 `skills[]` 首位，是它既有的约定（`workplace-writer`、`customer-insight-expert` 都是这个结构）。

## 三、能力单元（技能）

| 语义 | 千问办公（SKILL.md frontmatter） | 百度搭子 | OfficeAce |
|---|---|---|---|
| 标识 | `name` | `name` | `name` |
| 触发描述 | `description`（英）/ `description_zh`（中） | `description`（中） | `description`（中，用于路由判断） |
| 显示名 | `name_en` / `name_zh` | — | — |
| 版本 | `version` | `_meta.json.version` | — |
| 参数提示 | `argument-hint` | — | — |
| 发布元数据 | — | `_meta.json`（`contentSha256`/`ownerId`/`publishedAt`/`slug`） | — |
| 生成标记 | — | — | `agent_created: true` |
| 正文 | H1 命令名 + 何时用 + 铁律 + 流程 + 自检 | 同左 | 同左 |

**迁移规则**

1. frontmatter 只保留 `name` + `description`（优先中文，无中文则用原文），补 `agent_created: true`。
2. 正文逐字保留。缺 H1 时用 `name_zh` 补一个。
3. 末尾加 `<!-- migrated by ... from <平台>/<套件>@<版本> -->` 留痕，便于日后溯源与增量重迁。
4. `_meta.json` 一律删除，删除原因写进报告（它是源平台的发布凭证，OfficeAce 不校验也无法校验）。

## 四、附件目录

| 目录 | 语义 | 千问办公 | 百度搭子 | OfficeAce | 迁移处理 |
|---|---|---|---|---|---|
| `references/` | 知识库：规则、口径、框架 | ✓ | ✓ | ✓ 同名保留 | 原样全搬 |
| `scripts/` | 可执行脚本 | ✓ | ✓ | ✓ | 原样搬，**必须列入待验证** |
| `templates/` | 输出模板 | ✓ | ✓ | 部分技能用 `assets/` | 保留原名；OfficeAce 不限定名字，靠正文引用路径找到 |
| `assets/` | 图片、样式 | ✓（`icon.svg`） | ✓ | ✓ | 图标可丢弃（OfficeAce 用 `avatar`） |
| `rules/` `evals/` `license/` | 规则、评测、许可 | — | ✓ | ✓（`script-factory-kb` 有） | 原样搬 |
| `avatars/` | 专家头像 | — | ✓ | 复制进应用 `/avatars/experts/<角色名>.png`，卡片 `avatar` 指同一路径 | 搬；须 512×512、无外圈留白；文件不存在→乱码，纯色占位图→色斑 |

## 五、外部依赖（连接器）

| 平台 | 声明方式 | 迁移到 OfficeAce 的处理 |
|---|---|---|
| 千问办公 | `.mcp.json` 的 `guided-setup` 条目 + `CONNECTORS.md` 品类表 | `.mcp.json` 丢弃；`CONNECTORS.md` 正文并入技能末尾的「连接器可用时的增强」段（迁移前应已写好），并在报告里提示用户去应用内连 |
| 百度搭子 | manifest `agents[0].connectors`（声明式，运行时不加载） | 丢弃数组；在 persona 技能 的「原则与边界」里补一句「本环境无 X 时改为 Y」 |
| OfficeAce | 应用内连接器设置，无声明文件 | — |

**这是最容易迁出问题的一块**：依赖平台私有 CLI（如千问办公的 `dws`）的技能，搬过去会出现「提示词说要调命令，环境里没有」。处置只有两条：给技能加降级段，或直接不迁该技能——不要假装能跑。

## 六、注册与生效

| 平台 | 要写几处 | 生效方式 |
|---|---|---|
| 千问办公 | 1 处：`plugins-custom/<name>/`（或 `plugins/<name>/`） | 放对即扫描；容器重启 |
| 百度搭子 | 1 处：`plugins/user/<name>/` | **监听 `plugin.json` 的 `version` 变更**才 reload |
| OfficeAce | **7 处**：专家卡、`catalog.json` 的 `experts[]`、用户目录 `breeds[]`+`roster{}`、`users/<uid>/user-experts.json`、应用目录 `skills/`、`installed-skills.json`、`capabilities.json` | 启动时读；改完必须重启 |

OfficeAce 七处的分工：专家卡定义「这个人是谁」，`catalog.json` 决定「列表里有没有这一项」，用户目录 `breeds`/`roster` 决定「`@` 昵称唤不唤得起、编排时能不能被选中」，`user-experts.json` 决定「UI 专家列表显不显示」，后三处技能登记决定「技能能不能加载、重启后会不会被刷掉」。团队另加 `user-teams.json`。

## 七、语义不可映射项（必须在报告里交代）

| 源能力 | 为什么搬不过去 | 建议 |
|---|---|---|
| 多 agent 团队（manifest `agents` > 1） | 只有 WorkBuddy 有 `expertType: team` 语义；千问/搭子包无团队结构 | WorkBuddy 走 `migrate_workbuddy.py` 原生展开成 N 个专家 + `user-teams.json`；千问/搭子包只取入口 agent，其余转普通技能，并在报告里写明降级 |
| 技能市场的安装/更新链路 | 依赖源平台 apphub 的 `pluginId` 与版本协商 | 迁过来即脱离源市场，转为本地维护；后续升级靠重跑迁移 |
| 平台私有 CLI 能力 | 目标环境无该二进制 | 加降级段，或不迁 |
| 版本 reload 机制 | OfficeAce 无该机制 | 改完重启，交付时明确告知 |
