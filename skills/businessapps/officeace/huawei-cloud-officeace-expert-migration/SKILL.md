---
name: huawei-cloud-officeace-expert-migration
version: 1.7.4
description: "把 WorkBuddy、千问办公（QwenWork）或百度搭子（DuMate）的专家、专家团/专家套件迁移成 OfficeAce 可用的专家卡、技能目录与专家团时使用。**强制第一步**：执行任何迁移动作前必须先问用户「这次迁移是跨机器的吗？」，得到答复前禁止运行任何迁移器的 --install（1.6.0 起 migrate.py / migrate_workbuddy.py / migrate_suite.py 三者共用脚本级闸门 migration_gate.py，直接调用子迁移器同样被拦截；跨机器时指导用户先把专家包传到本机再按路径迁移）。**支持一句话迁移**：用户说「把 X 迁过来 / 把这个专家团装到 OfficeAce」时，用 ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/migrate.py 一个命令自动定位源包、识别平台、选迁移器、装完自检并自动同步应用镜像目录，不需要用户给路径或指定脚本。覆盖格式识别、字段映射、技能正文改写、专家卡/团队注册、头像落地、安装与十一项校验全流程。1.2.0 起以「迁移完即可用」为验收线：人设取全文、技能按角色分工、脚本改绝对路径、运行配置取自本机 model.json、主理人与成员全部进专家目录，装完直接派任务即可跑。触发词：迁移专家、迁移专家团、专家套件迁移、套件移植、把套件装到 OfficeAce、把这个专家迁过来、帮我把专家团搬过去、专家包转换、plugin 转 expert、qwenwork 套件、dumate 套件、workbuddy 专家、workbuddy 专家团、有哪些专家可以迁、专家卡不存在、专家列表里没有、主理人出错、专家团跑不起来、成员人设一样、技能加载不到、专家头像乱码、头像不显示、头像是一块纯色、换专家头像、镜像不同步、改了技能没生效。"
agent_created: true
---

# ⛔ 铁律 0（先于一切）：迁移前必须确认是否跨机器

收到任何迁移请求后，**在执行定位/安装等任何动作之前**，先向用户提问：「这次迁移是跨机器的吗？（即专家源包不在本机，需要先从别的机器把专家文件包传到这台电脑）」
- 答「跨机器」→ 指导用户把整个专家套件文件夹传到本机（推荐 `~/.office-claw/.staging/`），等给出本地路径后 `migrate.py --source <路径> --install --confirm-local`；源包未落地禁止安装。
- 答「不跨机器」→ 直接按名称走统一入口迁移。
- 未回答 → 只提醒一次，绝不默认本机直接迁移。本确认必须用户可见，不得静默跳过。
**脚本级强制（1.6.0 下沉为公共模块）**：闸门由 `scripts/migration_gate.py` 统一实现，`migrate.py` / `migrate_workbuddy.py` / `migrate_suite.py` 三个入口共用——**直接调用子迁移器的 `--install` 同样被拦截**（exit 4，stderr 输出 `[GATE-CROSS-MACHINE]`），不存在旁路。收到该错误时，正是要向用户提问的信号。闸门为**票据+冷却**机制：拦截输出会给出一枚 nonce 票据（携带会话标识，多会话并发不误用），你必须先把跨机器问题输出给用户并结束本轮；用户答复后，带 `--confirm-local <nonce>` 重跑。距拦截不足冷却秒数会被以「确认时间过短」拒绝——默认 90 秒，可用 `--gate-cooldown <秒>` 或环境变量 `ESM_GATE_COOLDOWN` 调整。migrate.py 确认通过后写入 10 分钟有效的 confirmed 标记，转调子迁移器时凭标记放行、不重复提问；标记过期重新拦截。

---

# 专家套件迁移（→ OfficeAce）

## 概述

把别家的专家套件搬到 OfficeAce。核心判断只有一句：**技能正文不改，只换外壳**——套件的价值在提示词与知识库，不在 manifest 格式。

## 一句话入口（默认走这里）

用户不会说「用 migrate_workbuddy.py --source …」。他只会说「把投标响应作战团迁过来」。
~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/migrate.py 就是这句话的落地：给一个名字或路径，它自己定位包、识别平台、选迁移器，装完自己验收。

| 用户怎么说 | 你该执行 | 说明 |
|---|---|---|
| 「把 X 迁到 OfficeAce / 迁过来 / 装到这边」 | `migrate.py --source X --install --confirm-local` | 这句话已经是安装指令，不必再问「要不要装」 |
| 「先看看会变成什么 / 能不能迁 / 会不会丢东西」 | `migrate.py --source X` | dry-run，产物落 `~/.office-claw/.staging/`，不写注册 |
| 「有哪些能迁 / 我这边都有什么专家」 | `migrate.py --list` | 只读，标注已迁移 / 未迁移 |
| 「全都搬过来 / 把自建的都迁了」 | 先 `--list` 圈范围，再 `--source <父目录> --all --install` | 纯技能包默认不迁（它们不是专家） |
| 「X 用不了 / 列表里没有 / 主理人出错」 | `verify_install.py -q --name <包名>` + `check_runtime.py` | 先诊断，别重装——重装会覆盖已验证的内容；单看一个专家加 `--name`，省得被几十条明细淹没 |
| 「头像不对 / 换张头像」 | `repair_avatars.py` / `set_avatar.py` | 与迁移无关，别走迁移流程 |

`--source` 接受三类写法，按顺序尝试：

1. **真实路径**（最稳，任何机器都认）；
2. **包名**（`bid-response-squad`）；
3. **中文名或关键词**（`投标响应作战团`、`比价`）——按目录名、清单名、中英显示名、团队角色名打分匹配。

唯一命中才继续；命中多个会列出来并以**退出码 3** 结束，**这时要问用户是哪一个，不要自己挑**。
一个都匹配不上（退出码 2）就给 `--list` 的结果让用户选，不要凭目录名猜。

默认值（这些不必每次问）：

- 数据目录 `~/.office-claw`、应用安装根自动探测；多账号机器上用 `--officeace-home` / `--app-root` 显式指定。
- 单专家的中文名与昵称沿用源包，要改才传 `--display-name` / `--nickname`。
- 预演产物落 `~/.office-claw/.staging/<name>-<时间戳>/`，不污染调用者当前目录。

装完入口会连跑两步验收（静态十一项 + 应用侧只读），结论只有三种，照它做：

| 结论 | 含义 | 下一步 |
|---|---|---|
| 迁移完成且可用 | 静态与应用侧都通过 | 直接交付，可以派任务 |
| 静态检查通过，应用侧未确认 | 应用没开或会话失效 | 启动 OfficeAce 后补跑 `check_runtime.py`，**不要当成已通过** |
| 自检未过 | 有 ✗ | 按 ✗ 逐条修，不要用「重启试试」掩盖 |

## 迁移完即可用（1.2.0 的硬约束）

「装上、界面里能看到」不等于可用。实测把六位迁移专家放进 OfficeAce 后，团队一召唤就报「主理人出错」，
成员交出来的成本数字比源端少三万——原因不在模型，而在下面五件事每一件都做错了。现在它们由
~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/runtime_contract.py 统一实现，迁移脚本与校验脚本共用同一套判据：

| # | 硬约束 | 做错的后果（实测） |
|---|---|---|
| 1 | **运行配置取自本机 `model.json`**：`providerProfileId` + `defaultModel` 必须是真实存在的组合，`variant.provider` 必须是 `relayclaw` | 写死 `modelarts-shared / glm-5`（本机不存在）→ 专家一召唤就鉴权失败；`provider` 写错会让专家从 `/api/agents` 整批消失 |
| 2 | **人设取 `agents/*.md` 全文**（去 frontmatter 与一级标题），不是团队简介或一句话 | 四个成员 personality 全是同一句团队简介 → 分工抹平、判据丢失，输出变成泛泛而谈 |
| 3 | **技能按角色绑定**：frontmatter `skills:` → 正文点名的包级技能 → 兜底全挂（标注待确认）；主理人只挂自己的人设技能 | 每个成员都挂满全队技能 → 越界执行别人的活，同一份数据算出两套口径 |
| 4 | **技能里的脚本引用写绝对路径**，并在人设里补「先跑脚本、不得自写算法」的执行纪律 | 团队会话 cwd 是 `team-workspace`，`skills/` 为空，`python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/x.py 找不到文件 → 模型自己重写计算器，成本 803,520（应为 836,294.40） |
| 5 | **主理人与成员全部登记 `users/<uid>/user-experts.json`**；队级标量与 roster 运行态字段齐全 | 主理人只写 `user-teams.json` → `/api/experts` 里没有它 → 团队报「主理人出错」、成员档案回落成英文 id |
| 6 | **包级技能以磁盘扫描为准**（`package_skills(pkg)`），manifest 未声明 `skills:` 字段时也要把专家卡引用的技能装上（1.4.0，实测 3d-modeling） | install 只认 manifest → 专家卡引用了技能但技能目录不存在、capabilities 未登记，运行时报 configured but not installed |
| 7 | **SKILL.md 围栏脏格式归一化 + 包级 references/ 随迁**（1.4.0，实测 3d-modeling-kb 的 `\---` 围栏、合规专家 references 缺失）：应用侧解析不出技能元数据、静态知识查不到都会让专家退化成凭记忆作答 | 围栏写成 `\---` → 技能元数据解析失败；`references/` 不带走 → 「提示词+静态知识型」专家的知识库整体丢失 |

验收口径：`verify_install.py -q` 输出「通过」，且这五项逐条有对应 ✓。静态全绿之后再在应用里派一个真实任务，
数字与源端一致才算交付（比对方法见 [references/verification-method.md](references/verification-method.md)）。

## 前置条件（何时用 / 不适用）

- 手上有一个 WorkBuddy / 千问办公 / 百度搭子的专家包（含 `plugin.json` + `agents/` + `skills/`），要装进 OfficeAce。
- 要把 **WorkBuddy 的专家团**（一包多角色 + 主理人 + 成员）搬成 OfficeAce 的专家团。
- 自己写的套件想同时在多个平台用，以 OfficeAce 为主力。
- OfficeAce 专家列表里缺专家、专家团缺成员、专家卡在但技能加载不到、`@昵称` 唤不起来。

**不适用**：从零新建专家（直接写 `skills/<name>/SKILL.md` + 专家卡更快）；只想改已有专家的提示词（直接编辑技能文件）。

## 三平台一句话对照

| | WorkBuddy | 千问办公 | 百度搭子 | OfficeAce |
|---|---|---|---|---|
| 清单 | `.codebuddy-plugin/plugin.json` | `.qwenwork-plugin/plugin.json`（新）/`.qoder-plugin`（旧） | `.claude-plugin/plugin.json` | 没有套件清单，专家卡即 `experts/<name>.json` |
| 一包多角色 | **支持（`expertType: team` + `teamInfo`）** | 不支持 | 不支持 | 团队走 `users/<uid>/user-teams.json` |
| 角色提示词 | `agents/<agent>.md`（真文件，保真度最高） | 无独立文件，散在各 SKILL.md | `agents/<name>.md` + manifest `agents[0].prompt` | `skills/<name>/SKILL.md`（约定与专家同名） |
| 能力单元 | `skills/<slug>/`（包级，全员共享） | `skills/<slug>/SKILL.md`（双语 frontmatter） | 同左 + `_meta.json` | 同左（frontmatter 只要 `name` + `description`） |
| 注册 | 放对市场目录即被发现 | 放对目录即被发现 | `plugins/user/<name>/` + `version` 变更触发 reload | **七处**：专家卡 + `catalog.json` + 用户目录 `breeds`/`roster` + `users/<uid>/user-experts.json` + 应用目录 `skills/` + `installed-skills.json` + `capabilities.json`（团队另加 `user-teams.json`） |
| 连接器 | 包内 `.mcp.json` / 应用内设置 | `.mcp.json`（guided-setup）+ `CONNECTORS.md` | manifest `agents[0].connectors` | 应用内连接器设置，无声明文件 |

## 核心命令（脚本清单：一个入口，两个迁移器）

**默认只用 `migrate.py`**。它按源平台自动路由到下面两个迁移器，不必自己判断平台。

| 脚本 | 读写 | 用途 | 什么时候直接用 |
|---|---|---|---|
| **`migrate.py`** | 读（默认 dry-run）/ **写**（`--install`） | 自然语言入口：按名字/路径定位 → 识别平台 → 路由 → 装完验收 | 默认。所有「迁 X」类请求都走这里 |
| `migrate_workbuddy.py` | 读 / **写**（`--install`） | WorkBuddy 专家包/专家团（一包展开 N 个专家 + `user-teams.json`） | 需要看包级明细、批量 `--all` 定制、或入口不认这个包时 |
| `migrate_suite.py` | 读 / **写**（`--install`） | 千问办公 / 百度搭子（一包一专家，人设可能需转写） | 同上 |

配套脚本（按用途挑，不要重复实现）：

| 脚本 | 读写 | 用途 | 常用参数 |
|---|---|---|---|
| `inspect_suite.py` | 只读 | 只读识别源格式，不写盘（排查「入口说识别不了」时用） | `<套件目录>` |
| `verify_install.py` | 只读 | 装后静态自检（十一项：含人设长度、运行配置、绝对路径、团队结构、资源引用）；`-q` 折叠逐专家明细只看汇总 | `--name <name>`、`--app-root <安装根>`、`-q` |
| `check_runtime.py` | 只读 | 应用侧可用性确认（只读 API）：专家在不在 `/api/experts`、团队成员有没有解析出中文名与人设 | `--team <teamId>`、`--base https://127.0.0.1:3004` |
| `repair_avatars.py` | 读 / **写**（`--fix`） | 批量诊断/修复历史安装的头像 | 默认只诊断，`--fix` 写盘，`--avatar-pack <目录>` 指定预制头像 |
| `set_avatar.py` | **写** | 一次性给某专家/团队换头像，同步全部注册位置 | `--name`、`--image`、`--team`、`--file-name` |
| `mirror_sync.py` | 读（`--check`）/ **写**（`--fix`） | 应用镜像目录同步：改了 `~/.office-claw/skills/` 后让镜像跟上（应用读镜像，不同步=改了没生效） | `--check` 只报告、`--fix` 写盘、`--slug <名>`、`--reverse` 反向 |

内部依赖：`runtime_contract.py` 是运行态契约的唯一实现（运行配置探测、人设解析、技能分工、
脚本绝对路径、roster/breed 结构、队级标量）。改迁移逻辑时改它，不要在脚本里复制一份判据。

## 铁律

1. **先识别，再动手**。不要凭目录名猜平台。默认交给 `migrate.py` 解析；排查时用 `inspect_suite.py` 看原始识别结果。
2. **不猜路径、不猜指向**。用户说「迁 X」就给 X，不要自己拼 `~/.workbuddy/…/X` 这种路径——用入口解析，命中多个就回去问。
3. **正文零改写**。技能 markdown 正文原样保留，只在末尾加一行来源注释。改写正文等于改行为，迁移不该改行为。
4. **默认 dry-run，但听用户的话**。只问「能不能迁」时出 staging 产物给人看；用户说「迁过来 / 装到这边 / 搬过去」就是安装指令，直接 `--install`，不要为「要不要装」再往返一次。安装必须备份、必须幂等（重跑不产生重复专家）。
5. **七处注册缺一不可**。只写专家卡不写 `catalog.json`，列表里看不到；不写用户目录 `breeds`/`roster`，`@昵称` 唤不起；不写 `users/<uid>/user-experts.json`，UI 专家列表不显示；技能不放**应用安装目录** `.office-claw/skills` 并登记 `installed-skills.json`，重启后会被刷掉；漏登 `capabilities.json`，当次会话报 `configured but not installed`。团队另需 `user-teams.json`。
   **团队的主理人与成员同样要进 `user-experts.json`**——OfficeAce 的 `/api/experts` 只认这一个文件，主理人只写在 `user-teams.json` 时团队运行时解析不到它（实测报「主理人出错」，成员档案回落成英文 id）。专家列表里出现与团队重复的入口，是可用性的必要代价。
6. **有卡的 breed 必须能被运行时注册**。`breeds` 是数组、`variants` 是数组、`agentId` 非空且全局唯一、`defaultVariantId` 指向存在的变体、默认变体带 `mentionPatterns`——缺任一项，OfficeAce 启动即崩（不是降级）。
7. **不搬运平台专有物**。`_meta.json`、源平台的 connector 声明、`version` reload 机制一律剥离，并在报告里写明丢弃了什么。
8. **脚本与依赖要人看**。带 `scripts/` 的技能，Python/Node 依赖、路径分隔符、编码都可能不兼容——挪过去不等于跑得起来，必须在报告里列出待验证项。
9. **合成的东西要标注**。源套件没有入口提示词时，工具会拿最完整的技能正文转写、再不行才按元数据合成，两种情况都要在报告里说清来源，供人工复核。
10. **头像必须真实可加载**。`avatar` 会原样进 `<img src>`：文件不存在 → 浏览器显示 alt 文本（中文名挤进 40px 圆框＝「乱码」）；指向纯色占位图 → 一块色斑。写卡片前必须确认图片真实存在且不是占位图，不许按专家名硬拼路径。

## 工作流（执行流程）

### Step 0 —— 一条命令（默认路径）

```bash
# 预演：看会生成哪些专家、人设多长、技能怎么分工，不写盘
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/migrate.py --source "<名字或路径>"

# 安装 + 自动验收
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/migrate.py --source "<名字或路径>" --install --confirm-local

# 批量：给父目录，逐个包串行迁移（纯技能包默认跳过）
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/migrate.py --source ~/.workbuddy/plugins/marketplaces/my-experts/plugins --all --install
```

这一步已经把 Step 1～Step 6 串起来了，输出里逐条列出：识别到的平台与类型、每个专家的角色/人设字数/技能分工及其依据、
团队结构与主理人、运行配置、写盘项数，最后是静态自检 + 应用侧确认的结论。

下面的分步说明保留给三种情况：**排查**（要看 staging 中间产物与 `report.md`）、
**定制**（要改 name / 昵称 / 分类）、**入口不认这个包**（识别为 unknown，需要手工判断）。

### Step 1 —— 识别（手动路径）

```bash
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/inspect_suite.py <套件目录>
```

输出：识别到的平台、清单路径、名称/版本/描述、技能数与每个技能的子目录（scripts/references/templates）。

识别不到平台时停：可能不是套件包（缺三种清单之一），或已经是 OfficeAce 结构。

### Step 1b —— WorkBuddy 走专用脚本（单专家与专家团）

```bash
# 预演单包（自动判断 agent / team）
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/migrate_workbuddy.py --source <包目录>

# 批量预演整个自建专家目录
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/migrate_workbuddy.py --source ~/.workbuddy/plugins/marketplaces/my-experts/plugins --all

# 安装（幂等；已存在的专家卡沿用原 expertId，不打断既有会话）
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/migrate_workbuddy.py --source <包目录|plugins目录> [--all] --install [--force]
```

要点：
- **一包多角色**：`expertType: team` 的包会展开成「主理人 + N 个成员」共 N+1 个专家，并写一条 `user-teams.json`（`teamId = wb-team-<包名>`，重跑覆盖同一条）；
- **人设真文件**：`agents/*.md` 正文（去 frontmatter 与一级标题）直接成为 `personality`，并同步进主提示词技能；`roleDescription` 由「职业 + 正文第一句」拼成一句话，两者不能相等；
- **技能按角色分工**：`skills/<slug>/` 是全员可见的包级技能，但**只挂给用得到的人**——先看 `agents/*.md` frontmatter 的 `skills:`，没有就看正文点名了哪个技能，都没有才兜底全挂并在输出里标注「需人工确认分工」。主理人只挂自己的人设技能，靠派活而不是自己跑脚本；
- **脚本一律绝对路径**：迁移后会把 SKILL.md 里形如 `python` + 相对脚本的引用改写成 `python "<数据目录>/skills/<技能>/scripts/x.py"` 的绝对路径，并在人设末尾补「先跑脚本 / 不得自写算法」的硬规则。团队会话 cwd 不在技能目录，相对路径必然失效；
- **运行配置来自本机**：`providerProfileId`/`defaultModel` 从 `~/.office-claw/model.json` 取，`variant.provider` 固定 `relayclaw`；已迁移专家优先沿用现有配置，重跑不改变已验收的行为；
- **ID 幂等**：已有同名卡沿用原 `expertId`/`agentId`；新专家用 `expert-<name>-<sha8(name+version)>`；
- **头像必须落地且像样**：`avatar` 会原样进前端 `<img src>`，文件不存在时浏览器改显示 alt 文本，40px 圆形头像里塞进中文名就表现为「乱码」；指向纯色占位图则显示成一块色斑。脚本按 `members[].avatar` → `avatars/<角色名>.png` → 清单 `avatar`（均需 `avatar_quality` 判定合格）→ 应用内置图 的顺序取图并复制进应用头像目录；**禁止按专家名硬拼** `/avatars/experts/<name>.png`。源端没有可用图时，按职能生成正式头像后用 `set_avatar.py` 换上。


### Step 2 —— 参数确认（定目标身份）

这三个值**只在需要改时才给**；不给就沿用源包（入口会把沿用的结果显示出来，觉得不合适再传参覆盖）：

| 参数 | 说明 | 不给的后果 |
|---|---|---|
| `--name` | OfficeAce 内标识（kebab-case） | 回退源套件 name，可能带前缀不合适 |
| `--display-name` | 中文显示名 | 回退源 displayNameCn |
| `--nickname` | `@` 唤起的昵称（2-3 字，像个名字） | 回退显示名，`@` 起来很长且不像人名 |

昵称值得单独起：OfficeAce 的专家是「人」，`@顾方案` 比 `@售前解决方案专家` 自然。

### Step 3 —— 转换与输出格式（dry-run）

```bash
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/migrate_suite.py --source <套件目录> --staging <输出目录> \
  --display-name "中文名" --nickname "昵称" --category legal
```

产物：

```
<staging>/
├── experts/<name>.json        # 专家卡
├── skills/<name>/SKILL.md     # 专家主提示词（来自 agent.md 或合成）
├── skills/<slug>/...          # 业务技能（正文原样 + references/scripts/templates 全搬）
├── catalog.patch.json         # 注册条目补丁（专家卡/catalog/breeds+roster）
├── report.md                  # 给人看的迁移报告
└── migration-manifest.json    # 给机器看的迁移台账
```

看 `report.md` 里两栏：**丢弃**（搬不过去的）与**需人工确认**（搬过去但要人验的）。这两栏不空就不要直接 install。

### Step 4 —— 校验 staging

- 每个 `skills/*/SKILL.md` 的 frontmatter 是 `---` 开头、有 `name` 与 `description`。
- 专家卡的 `skills` 数组里每个 slug 都在 `skills/` 下有对应目录。
- `report.md` 的「需人工确认」已逐条处理或有明确接受理由。

### Step 5 —— 安装

```bash
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/migrate_suite.py --source <套件目录> --staging <输出目录> --install
```

安装动作（全部先备份，后缀为时间戳）：

1. `skills/<slug>/` → `~/.office-claw/skills/`（同名默认跳过，`--force` 才覆盖）
2. `experts/<name>.json` → `~/.office-claw/experts/`
3. `user-catalogs/catalog.json` 的 `experts[]` 按 name 幂等更新
4. 用户目录 json 的 `breeds[]` 与 `roster{}` 同步更新
5. **应用安装目录** `<OfficeAce 安装根>/.office-claw/`（custom 技能的**持久化源**，三件套缺一不可）：
   - `skills/<slug>/` 技能目录本体——**必须装在这里**；`~/.office-claw/skills/` 只写的话重启即失效
   - `installed-skills.json` 登记 `{"source":"local","installedAt":...,"name":<slug>}`（`~/.office-claw/.office-claw/` 下有同名镜像，一并登记）
   - `capabilities.json` 登记 `{"type":"skill","enabled":true,"source":"custom",...}`
   原理：capabilities.json 在应用**每次启动时再生**＝builtin + SkillHub + 上述存储，漏掉存储直接被刷；
   漏掉 capabilities 条目则当次会话报 `configured but not installed`。
   应用根自动探测（`~/.office-claw` 的兄弟目录 `OfficeAce/`），探测失败用 `--app-root` 指定。
6. **`~/.office-claw/users/<uid>/user-experts.json`**：追加/更新完整专家卡
   （含 `visibility/defaultModel/providerProfileId`，从该文件已有条目取模板）。
   这是 **UI 专家列表的真正数据源**——只写 experts/*.json 专家卡，重启后列表里也不会出现。
   **活跃用户只能取 `~/.office-claw/connector-owner.local.json` 的 `ownerUserId`**（目录名冒号转 `%3A`），
   不要按目录 mtime/条数猜——多账号机器上会写进别人的目录，界面始终看不到你装的东西。
   该文件不会被启动再生覆盖，写一次即持久。
7. **`user-teams.json`（团队专属）**：`teams[]` 写 `teamId/displayName/members[{expertId,role,displayName}]/leaderExpertId`，
   团队头像写 `teams[].avatar`；另须写全 OfficeAce 队级标量 `lifecycle / dispatchMode / spawnMode /
   enableSwarmflow / enablePermissions / maxIterations / completionTimeout`（省略会回退应用默认值，
   迁移前后行为不一致）。团队成员必须是已注册的 `expertId`，**且每个成员（含主理人）都要在
   `user-experts.json` 里有一条**——团队运行时的角色解析走的是那份专家目录。

`--officeace-home` 可改数据目录；`--user-catalog` 可指定用户目录文件（多账号时用）。

### Step 6 —— 验证方法

```bash
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/verify_install.py --name <name>     # 全量明细
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/verify_install.py -q                # 只留检查项汇总（专家多时用这个判通过与否）
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/verify_install.py -q --app-root ~/OfficeAce   # 自动探测不到安装目录时指定
```

十一项检查（前六项是"装上了"，后五项是"能用"）：

1. 专家卡可解析、字段齐全（含 `personality`）；
2. **人设真的迁移了**：`personality` < 200 字，或与 `roleDescription` 完全相同 → 判失败；
3. 引用的技能都有 `skills/<slug>/SKILL.md`；
4. `avatar` 指向的图片真实存在（占位图只告警）；
5. `catalog.json` 与专家卡一一对应；
6. 用户目录 `breeds`/`roster` 覆盖到该专家；
7. **运行配置合法**：`variant.provider == relayclaw`，`providerProfileId/defaultModel` 在本机 `model.json` 里存在，roster 条目同款字段齐全；
8. **`user-experts.json` 含每一个专家**（含团队主理人与成员），且 `personality`/运行配置与专家卡一致；
9. **团队结构完整**：`leaderExpertId` 可解析、`role=leader` 有且只有一个、队级标量齐全、成员有 `displayName`；
10. **脚本引用是绝对路径且文件存在**（相对路径必然失效）；
11. **资源引用可解析**：`SKILL.md` 点名的 `references/`、`scripts/`、`assets/`、`templates/` 文件必须真实存在——
    这一项查的是"读某份知识库"这类**引用**（第 10 项只查 `scripts/` 下脚本的**调用**形式）。
    技能资源整包丢失时文件全指空，专家能对话但读不到判据、跑不了脚本，而前九项全都绿。
    跨技能引用（引用同包另一技能的 `references/x.md`，且该专家同时挂载了那个技能）只告警不算失败。

静态全绿后，先问一次正在运行的应用（这一步能抓住"文件都对、应用就是不认"的情况）：

```bash
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/check_runtime.py            # 应用在跑时必须通过
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/check_runtime.py --team wb-team-xxx
```

它查两件事：每个迁移专家在 `/api/experts` 里都有；团队 `memberProfiles` 解析出的是中文名 + 完整人设
（不是回落成 `expertId`）。应用没启动时返回码 2，不算迁移失败。

最后是运行时对跑（静态检查查不出"模型有没有真的调用脚本"）：

```bash
# 在应用里对迁移来的专家/团队派一个真实任务，用源端同一份输入跑一遍
# 判定：关键数字逐项一致，且产物里能看到脚本调用（不是模型自己算的）
```

数字不一致时先查第 7、10 项——九成是运行配置不合法或脚本路径没改，模型退化成"自己写个计算器"。

每项的判定线与失败处置见 [references/verification-method.md](references/verification-method.md)，交付门槛见 [references/acceptance-criteria.md](references/acceptance-criteria.md)。

头像若只是纯色占位图（源端常给 8×8 单色 png），`verify_install.py` 会给出警告——这种图在
40px 圆框里就是一块色斑，等于没做视觉设计。处理顺序：

1. **源端有真图**：迁移时自动复制，无需干预。
2. **源端没有像样的图**：按「专家名 + 职能」生成一张 512×512 头像（见下方提示词模板），
   再用 `set_avatar.py` 一次性写进全部注册位置。
3. **暂时不想生成**：`repair_avatars.py --fix` 会退到应用内置头像，至少不出破图，
   但多位专家会共用同一批通用图，一眼仍能看出是迁移来的。

```bash
# 把一张新头像设为某专家（同步专家卡 / catalog / user-experts / breeds+variants）
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/set_avatar.py --name cost-auditor --image ./cost-auditor.png

# 专家团：写进 user-teams.json 的 teams[].avatar
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/set_avatar.py --name wb-team-team-xxx --team --file-name team-x --image ./team.png

# 批量修复：优先用预制头像目录，其次源包原图，最后内置图
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/repair_avatars.py --avatar-pack ./avatars --fix
```

头像生成提示词模板（保持风格统一的关键是一次只换人物描述，风格句原样复用）：

> 柔和手绘插画风格的专家头像，半身正面像。{年龄性别}的亚洲{职业}：{服饰}，{发型}，
> {手持道具/动作}，{神情}。{主题色}到{浅色}的柔和渐变背景，背景里隐约有{职能元素}的铅笔线稿点缀。
> 赛璐璐平涂上色，细腻铅笔线稿，暖调柔光，扁平插画质感，类似绘本人物。画面铺满整个正方形画布，
> 人物头部与肩膀居中，适合圆形裁切；不要圆形画布、不要外围白边或边框；不要任何文字、字母、数字、印章、水印。

历史安装的头像已破图（显示成乱码）时，用修复脚本批量补齐，不必重装：

```bash
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/repair_avatars.py            # 只诊断，列出坏头像
python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/repair_avatars.py --fix      # 修：优先还原源包原图，其次用内置头像
```

报错按提示修，别急着重启应用。注册类写入（专家卡 / catalog / breeds+roster / user-experts / user-teams）
实测**改完即生效，不需要重启**；只有当界面里的技能列表没刷新时，才重启一次 OfficeAce。

### Step 7 —— 交付说明

给用户的交付话术固定四段：装了什么（专家名 + 技能数）、在哪（数据目录路径）、丢弃了什么（平台专有物）、还要人做什么（脚本依赖验证、昵称/头像调整、连接器重配）。

## 注意事项：常见故障与处置

> ⚠️ **生产环境警示**：`--install` 写入的是用户真实数据目录与应用安装目录（等价生产环境，
> 影响正在运行的专家会话与团队配置）。所有写操作（`--install`、`--force`、`set_avatar.py`、
> `--fix` 类）执行前必须已获用户确认；写入自带时间戳备份，出错可用备份回滚；
> 拿不准时先 dry-run 预演。**不要在用户未过目的场景下对已有专家做覆盖式重装。**

| 现象 | 原因 | 处置 |
|---|---|---|
| **用户只说了个名字，不知道用哪个脚本** | 源平台未知、路径未知 | `migrate.py --source "<名字>"` 自己路由；不要自己拼路径 |
| **`migrate.py` 报「可能对应多个套件」并以退出码 3 结束** | 名字命中了多个包（同名包在多个 marketplace、或关键词太宽） | 把它列出的候选交给用户选，选完用 `--source <包名>` 精确指定；**不要自己挑一个** |
| **`migrate.py` 报「找不到」** | 名字打错、包不在本机默认源根、或是纯技能包（默认不迁移） | `--list` 看清单；确认是技能包就加 `--all-kinds`；包在自定义目录就加 `--root <目录>` |
| **装完结论是「应用侧未确认」** | 应用没启动、或本机 `session.cookie` 失效（换用户/换机器） | 启动 OfficeAce 后跑 `check_runtime.py`；仍失败就重登一次再跑。此状态**不算通过** |
| 重启后专家列表没有 | 只写了专家卡，没写 `catalog.json`、用户目录，或没写 `users/<uid>/user-experts.json`（最常见） | 跑 `verify_install.py` 看是哪一处缺；补 `--install` 重跑 |
| 专家在，但技能报 Skill not found / configured but not installed | 技能没登记进应用安装目录的 `capabilities.json` | `--install` 重跑会自动登记；或手工加 `{"id":<slug>,"type":"skill","enabled":true,"source":"custom"}` |
| 专家在，但技能不加载 | 技能目录名与专家卡 `skills[]` 中的 slug 不一致 | 改目录名或改数组，二者必须逐字相同 |
| `@昵称` 唤不起 | 用户目录 `roster` 缺该 id，或 `mentionPatterns` 不一致 | 专家卡 / catalog / breeds / user-experts 四处的 id 与昵称统一（三处都要有 `mentionPatterns`） |
| 技能能唤起但行为不对 | 源技能正文依赖平台工具（如 `dws`、duMate 专用 skill） | 在技能开头加一段「本环境无 X 时改为 Y」的降级说明，或剥离该技能 |
| 带脚本的技能报错 | 路径分隔符、编码、依赖缺失 | 报告「需人工确认」栏会列出；先手工跑一次脚本再交付 |
| 迁移后重复出现两个同名专家 | 换了 nickname 重跑，但 name 不同 | `name` 是唯一键，重跑必须用同一个 `--name` |
| **专家名显示成 `{'zh': '…', 'en': '…'}`** | 千问 / 搭子清单的 `name`、`displayName`、`description` 允许是多语言对象，被整个当字符串用了 | 取值统一走 `pick_text()`（中文优先归一）；`migrate_suite.py` 已修，自写脚本时别直接 `str()` |
| **专家头像显示成乱码 / 破图** | 卡片 `avatar` 指向 `/avatars/experts/<name>.png`，应用里没有该文件；浏览器 `<img>` 加载失败改显示 alt 文本（中文名挤在 40px 圆里） | `python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/repair_avatars.py --fix`；后续迁移由 `ensure_avatar()` 保证路径必有文件，不再硬拼 |
| **专家头像是一块纯色** | 源包头像是 8×8 单色占位图，被原样复制过来；`avatar_quality()` 判为 placeholder | 按职能生成正式头像后 `set_avatar.py` 换上；只想先止损就 `repair_avatars.py --fix` 退到内置图 |
| **多个单专家共用同一张通用头像** | `install()` 定版时没沿用预演解析出的源头像，退到了应用内置 `agent-avatar-*.png`（1.1.3 前的缺陷） | 升到 1.1.3 重装该包即可；已装的可跑 `repair_avatars.py --source-root <源包>` 还原 |
| **专家团一召唤就报「主理人出错」/ E-1105 类错误码** | 主理人没有进 `users/<uid>/user-experts.json`（1.1.x 的 `team_only` 逻辑会主动把它删掉），`/api/experts` 里查不到它 | 升到 1.2.0 重跑该包；或在 `user-experts.json` 补一条主理人条目（结构与成员一致） |
| **团队成员档案显示英文 id，不是中文名** | 同上：主理人/成员在专家目录里解析不到，`memberProfiles` 回落到 `expertId` | 同上。`user-teams.json` 的 `members[].displayName` 也要写 |
| **四位成员说话一模一样，没有分工** | `personality` 写的是团队 `displayDescription`（旧版 `build_experts` 的 `desc` 传递错误） | 升到 1.2.0 重跑；人设必须取 `agents/*.md` 全文，且 `personality != roleDescription` |
| **团队任务派发即失败，报 `E-1106`，日志含 `team.binding.create failed: template_id not found`** | 对话栏绑定团队时 `team.teamName` 传了裸 `teamId`（如 `wb-team-opc-team`）；应用要求 jiuwen 名必须带 `oc_team_` 前缀，否则 `jiuwenNameToTeamId` 解析为 null（1.7.2 实测发现） | 派发脚本 PATCH 载荷改为 `{"team":{"teamName":"oc_team_<teamId>"}}`；注册本身无需改动，重发任务即可 |
| **每个成员都会干全队的活，结论互相打架** | 技能挂成 `[自己] + 包级全部` | 升到 1.2.0 重跑，按 frontmatter / 正文点名绑定技能 |
| **数字和源端对不上（团队口径漂移）** | 成员没调用官方脚本，自己重写了计算器；`SKILL.md` 里还是 `python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/x.py | 升到 1.2.0 重跑（绝对路径 + 人设里的执行纪律），再派同一任务比对数字 |
| **专家召唤即失败 / 团队全员失败** | `providerProfileId`/`defaultModel` 写的是 `modelarts-shared`/`glm-5` 这类本机不存在组合 | 升到 1.2.0 重跑；`verify_install.py` 会直接指出非法组合与可用组合 |
| **重启后专家从 `/api/agents` 整批消失** | `variant.provider` 不是 `relayclaw` | 修回 `relayclaw`（`runtime_contract.breed_variant()` 固定写这个值） |
| **写入的是用户真实数据目录（等价生产环境）** | install 直接写 `~/.office-claw` 与应用安装目录 | install 前必须人工确认；所有写操作先备份（时间戳后缀），出错用备份回滚；拿不准就再跑一次 dry-run |

## 最佳实践：交付前自检

- [ ] 用 `migrate.py` 定位过源包（或 `inspect_suite.py` 确认过源格式），不是猜的
- [ ] 技能正文与源文件逐字一致（除 frontmatter、运行约定块与末尾来源注释）
- [ ] `report.md` 的「丢弃」与「需人工确认」两栏已逐条处理
- [ ] `verify_install.py -q` 输出「通过」（十一项，含人设长度、运行配置、绝对路径、团队结构、资源引用）
- [ ] `check_runtime.py` 通过（应用在跑时必查；跳过要在交付里说明）
- [ ] 团队包的**主理人与每个成员**都在 `user-experts.json` 里，且 `role=leader` 只有一个
- [ ] 七处注册的 id、昵称、技能数组完全一致
- [ ] 真实任务跑一遍，关键数字与源端一致（不是"看起来差不多"）
- [ ] 备份已生成（时间戳后缀），且告知用户位置
- [ ] 交付说明四段齐全，没有一句「应该可以了」

## 参考文档

- [references/format-mapping.md](references/format-mapping.md) —— 三平台 ↔ OfficeAce 字段级映射
- [references/workbuddy-format.md](references/workbuddy-format.md) —— WorkBuddy 专家包 / 专家团完整样例
- [references/qwenwork-format.md](references/qwenwork-format.md) —— 千问办公套件完整样例
- [references/dumate-format.md](references/dumate-format.md) —— 百度搭子套件完整样例
- [references/officeace-format.md](references/officeace-format.md) —— OfficeAce 专家卡 / 技能 / 团队格式
- [references/verification-method.md](references/verification-method.md) —— 十段验证法（V0 入口 / V0b 名称解析 / V1–V7）：每段的命令、期望输出与失败处置
- [references/acceptance-criteria.md](references/acceptance-criteria.md) —— 验收判据与放行门槛（P0/P1/P2）
- [references/iam-policies.md](references/iam-policies.md) —— 权限与授权说明：零云权限、触碰路径清单、数据敏感面

## 边界

- **多角色只在 WorkBuddy 侧成立**。`expertType: team` 的包由 `migrate_workbuddy.py` 展开成「主理人 + N 成员」并写 `user-teams.json`；千问/搭子包结构上没有多 agent，manifest `agents` 多于 1 个时只取入口 agent，其余转普通技能——这种降级必须在报告里写明。
- 不迁移浏览器依赖、登录态、平台私有 CLI 能力。这类技能搬过去会出现「说得好听但做不了」，宁可不迁。
- 不改源套件。所有写操作只发生在 staging 与 `~/.office-claw` 内。

## 1.7.4 修复记录（2026-11-10，PR !926 评审意见：2 个 P0 安全缺陷 + 3 个 P1）

- **P0 · 包名路径穿越（两个下沉点一并修复）**：源包 frontmatter 的 `name` 来自第三方 marketplace 包，属不可信输入；此前 `skills/<name>/`、`experts/<name>.json` 直接拼接，`name: ../../../../evil-lead` 实测可把产物写到 `$HOME/evil-lead.json`（逃出 `~/.office-claw`），`name: /tmp/...` 可在数据目录之外建目录。新增 `normalize_slug()` 统一闸门（在 `build_experts()` 生成 name 的唯一源头生效，下游技能落盘 / 专家卡 / catalog / 头像 / 镜像路径全部自动收口）：空值、含 `..`、绝对路径一律**报错退出（不静默改写）**，其余取 basename。实测恶意 name 迁移被拒绝且无文件逃逸。
- **P1 · 文档样例的内联 frontmatter 解析不出**：`displayName: { zh: 纪颜色 }` 这类 flow mapping（文档样例即此写法）此前只被当字符串，输出带花括号。`parse_fm_nested()` 新增 `parse_flow_mapping()` 支持一层内联映射（`{ zh: X }`、`{zh: X, en: Y}`）。
- **P1 · 多语言 description 崩溃**：`inspect_suite.py` 对 dict 型 description 直接 `[:120]` 切片 → `TypeError`（千问/搭子包的排查入口不可用）。改用 `_zh()` 兜底取中文字符串再截断；`migrate_workbuddy.py` 的 `agent_description()` 同类隐患一并修复。
- **P1 · WorkBuddy 路径缺 staging 报告**：dry-run 此前不落任何产物，SKILL.md 承诺的「先看 report.md 两栏再决定装不装」对主平台失效。现在 dry-run 与安装前都写 `~/.office-claw/.staging/<pkg>-<时间戳>/report.md`（丢弃 / 需人工确认两栏 + 专家与技能清单），只写报告不写注册。
- 回归测试新增 7 例（`tests/run_regression_tests.py`，共 27 例全绿）：恶意 name 拒绝且无逃逸、绝对路径拒绝、内联 flow mapping 解析、多语言 description 不崩溃、dry-run staging 报告落盘。

## 1.7.3 修复记录（2026-11-06，门户分发链路验证发现的技能资源丢失）

以「打包 → 上传门户 → 下载到本地新路径 → 迁移」的完整链路实测，发现两个会让**专家表面可用、内容残缺**的缺陷：

- **技能资源整包丢失（严重）**：`skills/SKILL.md` 直接躺在 `skills/` 下的扁平结构（资源在 `skills/references`、`skills/scripts`），`package_skills()` 只认 `skills/<slug>/SKILL.md`，返回空列表，于是只写了人设 SKILL.md，`references`、`scripts` 一个都没搬。实测 invest-risk-report：源 10 文件 → 目标仅 1 个 SKILL.md，且 SKILL.md 里 9 处资源引用全部指向不存在的路径，脚本调用必然失败。已补「扁平技能资源回填」步骤。
- **同名技能目录被占位跳过**：人设技能先 `mkdir` 出与技能同名的目录，随后 `copytree` 撞上 `dst.exists()` 被跳过——「专家名 == 技能目录名」是该 skill 自己写在格式约定里的常见形态。已调整写入顺序（先真实技能目录、后人设 SKILL.md），并对「只剩 SKILL.md 的残缺目录」自动补齐，存量数据重跑即可自愈，不必 `--force`。
- **伪成功告警**：有 `agents/` 但没有一个够格专家时（实测 a-share-analysis：7 个编排 agent + 20 个技能 → 0 专家），原先仍打印「迁移完成且可用」；现改为显式告警，说明只按技能包迁移。
- **验收盲区已补**：旧版 `verify_install.py` 只校验注册层，**不检查技能目录内的资源引用**，所以资源丢光时静态验收仍报「通过（41 项）」。现新增第 11 项检查「资源引用可解析」：解析各专家技能 `SKILL.md` 里的 `references/`、`scripts/`、`assets/`、`templates/` 引用，逐个核对是否落盘，缺失即判失败并列出文件。判定时排除文档示例占位符（`scripts/xxx.py`、`references/{name}.md`），并把「引用同包另一技能的资源、且该专家同时挂载了那个技能」识别为跨技能引用（告警而非失败）——例：dumate-test-rich 的 SKILL.md 让人先按 `references/<分类表>.md` 打标，文件实际在同包的 inspection-analytics 里，运行时能解析到，不能误判成丢失。

## 1.7.2 修复记录（2026-11-06，多源端全链路测试团队派发发现）

- **新故障入库**：团队任务派发即报 `E-1106 / template_id not found`——根因是派发侧 `team.teamName` 传了裸 teamId，应用要求 jiuwen 名带 `oc_team_` 前缀；已补故障表条目。注册数据无恙，修正派发载荷后团队任务真实跑通（主理人阶段判定 + 成员派单 + 7 人按阶段待命）。
- 本条与迁移安装本身无关（属调用方派发约定），记录于此供后续对接参考。

## 1.7.1 修复记录（2026-11-06，技能包瘦身）

- 移除技能包内的 `out/` 历史迁移产物存档（dumate-test-rich、qwen-test-pure 两次测试迁移的 staging 产物，52KB）——产物已归档至 WorkBuddy 工作区 `archive/migration-staging-out-20261106/`，技能包与镜像同步瘦身；
- 技能包只保留运行所需四件：SKILL.md、scripts/、references/、tests/；今后迁移产物默认落在调用方指定的 staging 目录，不再写入技能自身目录。

## 1.7.0 修复记录（2026-11-06，按华为命名规则重命名）

- 目录与技能 id 由 `expert-suite-migration` 改为 `huawei-cloud-officeace-expert-migration`（符合 huawei-cloud-{产品缩写}-{功能描述} 命名规范，A01 警告消除）；
- 联动同步：SKILL.md 全部自引用路径、installed-skills.json / capabilities.json 注册 id、应用镜像目录、每日巡检自动化路径；
- 旧 `out/` 存档随 1.7.1 移出技能包（见 1.7.1 记录）；
- 运行态统计（.skill_sleep call_counts、会话 active_skill）按旧 id 记录，属历史数据未迁移，计数自然重新累计。

## 1.6.3 修复记录（2026-11-05，M01–M10 人工确认项核对）

- 核心命令表全部脚本标注读写属性（只读优先；写操作均需显式参数）；
- 注意事项开头新增「生产环境警示」块（install 写真实数据目录，须确认+备份+回滚）；
- mirror_sync.py 补 `--check` 显式只报告参数（文档与实现原不一致，M05 抽查发现）；
- M04/M10 核实通过（无敏感凭证字面量、无跨 Skill 耦合）；M06–M09 不涉及（无仓库/PR/云 API 场景）。
- 核对结论全文：见审计目录 manual-confirmation.md。

## 1.6.2 修复记录（2026-11-05，华为 Skill 格式规范审计）

用 huawei-cloud-devtools-skill-format-audit（~40 项静态检查）审查后修复：
- 补「核心命令」章节标题（原「脚本清单」更名，内容不变）——消除唯一错误项；
- migrate.py / migration_gate.py / mirror_sync.py / runtime_contract.py 头注释前 15 行内补「用途/返回值」说明；
- 保留 1 条豁免警告：A01 目录命名（huawei-cloud-* 前缀仅约束华为产品技能，本 skill 非产品技能，kebab-case 命名合理）。
- 复审：0 错误 / 1 豁免警告，报告存 WorkBuddy 工作区 audit-reports/。

## 1.6.1 修复记录（2026-11-05，二次评审发现）

- **migrate_pkg 的 ID 复用查错目录**：原实现写死 `~/.office-claw`，多数据目录机器上用 `--officeace-home` 时幂等判断仍查默认目录。已改为跟随传入的 home（新增用例锁定）。
- **相对路径检查误伤文档举例**：技能自身无 `scripts/` 目录时，文档里的相对脚本引用降级为提示（警告）而非错误——文档性文字不应判死罪（新增用例锁定）。
- **回归测试增至 16 用例**；测试套件接入每日自动巡检（回归 + 镜像漂移 + 静态校验）。

## 1.6.0 修复记录（2026-11-05，全方位评审后落地）

- **闸门下沉，堵住旁路**：跨机器确认从 migrate.py 内联逻辑抽成公共模块 `scripts/migration_gate.py`，`migrate_workbuddy.py` / `migrate_suite.py` 直接调用 `--install` 同样被拦截（此前只拦入口，绕过入口即失守）。migrate.py 确认后写 10 分钟 confirmed 标记供子迁移器透传，过期重新拦截。
- **票据加会话标识**：nonce 由 sid（pid+毫秒）+ 日期派生，多会话并发覆盖票据文件时互不误用。
- **冷却可配置**：`--gate-cooldown <秒>` 或环境变量 `ESM_GATE_COOLDOWN`，默认仍为 90 秒。
- **镜像同步自动化（新脚本 `mirror_sync.py`）**：应用读取的是安装目录镜像，改了数据目录不同步＝改了没生效（实测排查三轮）。migrate.py 安装后自动同步；verify_install 对漂移发警告；可独立 `--check` / `--fix` 巡检。
- **回归测试套件（`tests/run_regression_tests.py`）**：14 个用例覆盖闸门七种路径、roster dict 契约、单包过滤不泄漏、七处注册完整性（真实跑一遍合成团队包）、镜像同步。
- **潜伏 bug 修复**：migrate_workbuddy 调用了不存在的 `log()`（新建用户专家目录时 NameError）；verify_install 遇到 roster 被压成 list 时显式报错而非 AttributeError 崩溃。
- **可移植性**：本文档全部脚本路径改为 `~/` 写法，不再硬编码本机绝对路径。

## 1.4.1 修复记录（2026-11-05，对话栏迁移实测发现）

- **verify_install 团队检查范围泄漏**：`--name` 单包模式下 `cards` 被过滤成 1 张卡，团队检查却拿它与全部注册团队成员比对，把无关团队成员全部误判「没有专家卡」（实测 13 条假 ✗）。修复：团队等全局一致性检查改用未过滤的 `all_card_ids`。
- **手写登记高危**：uid catalog 的 `roster` 是 **dict**（id → {family, roles, lead, available, evaluation, provider, providerProfileId, defaultModel}），用列表推导式追加会把 dict 压成 list 导致 verify 崩溃。登记新专家一律走 runtime_contract 构造器，不要手写 JSON 变换。
- breed variant 必须含 provider=relayclaw + providerProfileId + defaultModel，否则召唤鉴权失败。

