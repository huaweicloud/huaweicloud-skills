# 验证方法

## 概述

按迁移的执行顺序分十段验证（V0、V0b、V1–V7，含 V3b/V3c/V7b），每段给出可复制命令、期望输出与不合格时的处置。**任何一段不通过就不要往下走**——迁移的失败模式大多是「文件看着都在，UI 里就是不出现」，越早卡住越省事。

环境：Python 3.10+（仅标准库），Windows 的 `python3` 写作 `python` 或解释器绝对路径。

## V0 —— 入口自身可用

```bash
python scripts/migrate.py --help
python scripts/migrate.py --list
```

期望：`--help` 打印参数说明、退出码 0；`--list` 列出本机可迁移的专家套件，每条标注
`[已迁移]/[未迁移]`、平台、包名、显示名与形态（团队 N 角色 / 单专家），末尾给出隐藏的纯技能包数量。

判定：`--list` 里能看到你打算迁的那个包。看不到时先排查源根，不要改脚本。

失败处置：

- 报 `ModuleNotFoundError` → 当前工作目录不对，`cd` 到技能根目录再执行，不是技能损坏。
- 报 `SyntaxError` → Python 版本低于 3.9，换 3.10+ 解释器。
- `--list` 为空但本机确实装了源平台 → 源根不在默认列表，用 `--root <目录>` 或设环境变量 `ESM_SOURCE_ROOTS`。

## V0b —— 名称解析（自然语言入口）

```bash
python scripts/migrate.py --source "<包名 / 中文名 / 关键词>"
```

期望：唯一命中时打印 `[识别]` 行（显示名 → 绝对路径 + 平台 + 形态 + 迁移器），随后进入 dry-run。
命中多个时列出候选并以**退出码 3** 结束；一个都没有时以**退出码 2** 结束。

判定：`[识别]` 行的路径与你想要的那个包一致。**退出码 3 必须回去问用户，不许自己挑**。

| 退出码 | 含义 | 处置 |
|---|---|---|
| 0 | 唯一命中，已继续执行 | 看后续输出 |
| 2 | 找不到 | `--list` 给用户选；确认是纯技能包就加 `--all-kinds`；包在自定义目录就加 `--root` |
| 3 | 候选不唯一 | 把候选清单给用户，用 `--source <包名>` 精确指定 |

## V1 —— 源包识别正确

```bash
python scripts/inspect_suite.py <套件目录>
```

期望：明确打出**平台名**（WorkBuddy / 千问办公 / 百度搭子）、清单路径、包类型（单专家 / team）、角色数与技能列表。

判定：平台识别与目录里实际存在的清单一致（`.codebuddy-plugin` / `.qwenwork-plugin` / `.claude-plugin`）。

失败处置：识别不到平台说明不是套件包（缺清单），或已经是 OfficeAce 结构；不要靠目录名猜着硬转。

## V2 —— dry-run 产物合格

```bash
python scripts/migrate_suite.py --source <套件目录> --staging <输出目录> \
  --display-name "中文名" --nickname "昵称"
```

三查：

1. **技能正文有 frontmatter**：每个 `skills/*/SKILL.md` 以 `---` 开头，含 `name` 与 `description`。
2. **技能引用能落地**：专家卡 `skills[]` 里每个 slug，在 `skills/` 下都有同名目录。
3. **报告两栏已处理**：`report.md` 的「丢弃」与「需人工确认」逐条有结论——有内容但不是死胡同，没处理完不得 install。

失败处置：slug 与目录名不一致就改一处（二者必须逐字相同）；`report.md` 提示的合成人设要在文件里留痕并人工复核。

## V3 —— 装后十项自检

```bash
python scripts/verify_install.py -q          # 只看汇总
python scripts/verify_install.py --name <name>   # 单看某个专家
python scripts/verify_install.py -q --app-root ~/OfficeAce   # 探测不到安装目录时
```

期望输出形如（本机实测，1.2.0 起）：

```
OfficeAce 数据目录：C:\Users\Administrator\.office-claw
  ✓ catalog.json 与 experts/ 一一对应
  ✓ 用户目录 breeds/roster 覆盖全部 18 个专家
  ✓ 26 个技能目录均已进入应用目录存储（重启再生不丢）
  ✓ 技能均已登记到应用目录 installed-skills.json
  ✓ 活跃用户 user-experts.json 已包含全部 18 个迁移专家（含团队主理人）
  ✓ 专家团 2 个，主理人与成员均已有专家卡
  ✓ 3 个带脚本的技能均已改成绝对路径且文件存在
  ✓ 逐专家技能明细 36 条均就位（技能目录 ↔ capabilities 双向一致）

结论：通过
```

判定：末行「结论：通过」，且退出码 0。出现 `✗` 即为错误，必须修完再交付。

十项里，前六项证明「装上了」，后四项证明「能用」，后四项是 1.2.0 新增、也是最容易漏的：

| 检查 | 判据 | 缺失处置 |
|---|---|---|
| 人设完整性 | `personality` ≥ 200 字，且 ≠ `roleDescription` | 从 `agents/*.md` 重新取全文（迁移脚本 1.2.0 已改） |
| 运行配置 | `variant.provider == relayclaw`；`providerProfileId/defaultModel` 在本机 `model.json` 里存在；roster 同款字段齐全 | 用 `runtime_contract.detect_runtime_profile()` 的返回值重写四处注册 |
| 专家目录覆盖 | `user-experts.json` 含**每一个**专家（含团队主理人与成员），且 personality/运行配置与专家卡一致 | 补条目；团队成员不是例外 |
| 团队结构 | `leaderExpertId` 可解析、`role=leader` 有且唯一、队级标量齐全、成员有 `displayName` | 重写 `user-teams.json` 该条 |
| 脚本引用 | SKILL.md 里 `python scripts/x.py` 已改为绝对路径且文件存在 | 重跑 `--install`（1.2.0 会自动改写） |

失败处置对照：

| 缺失项 | 处置 |
|---|---|
| `catalog.json` 不覆盖 | 重跑 `--install`（按 name 幂等更新） |
| `breeds`/`roster` 未覆盖 | 同上；检查 `agentId` 是否为空或重复 |
| 技能未进应用目录 | 显式给 `--app-root`，指向 OfficeAce 安装根 |
| 未登记 `installed-skills.json` | 同上；漏登记重启后技能被刷掉 |
| `capabilities.json` 缺条目 | 同上；当次会话会报 configured but not installed |
| `user-experts.json` 未包含 | 检查 `connector-owner.local.json` 的 `ownerUserId` 是否为当前账号 |
| 运行配置非法 | 别猜模型名，读 `model.json`；`relayclaw` 不能换 |

## V3c —— 应用侧可用性确认（API 级，只读）

```bash
python scripts/check_runtime.py
# 期望：
#   应用内专家总数：65；待校验的迁移专家：6
#     ✓ 6 个迁移专家在应用侧全部可见（含团队主理人）
#     ✓ 团队 投标响应作战团：4 个成员均已解析出中文名与人设
#   结论：应用侧已认得全部迁移内容
```

它比静态校验更进一步：直接问运行中的应用"你认不认这些角色"。三类问题只有这一步能抓到：

- 专家卡与 `user-experts.json` 都写了，但应用启动时按内存态回写过注册表（改动被覆盖）；
- 团队 `memberProfiles.displayName` 回落成 `expertId`（人不在专家目录）；
- 应用侧 variant 的运行配置被改回占位值。

返回码 2 表示应用没运行/会话失效（`session.cookie` 是 DPAPI 加密的，换用户或换机器后需重新登录），
这不算迁移失败，但要在交付说明里写明"未做应用侧确认"。

## V3b —— 运行时对跑（静态检查查不出「模型有没有真的用脚本」）

在应用内对迁移来的专家/团队派一个真实任务，用与源端**同一份输入**跑，然后比对：

1. **关键数字逐项一致**（成本合计、含税价、毛利率、命中条数……不是"看起来差不多"）；
2. **产物里有脚本调用痕迹**（命令是绝对路径，`--json` 输出被引用），而不是模型口算；
3. 团队成员各司其职：风险只谈风险、报价只谈报价，主理人只做拆标与收口。

本机实测基线（供对照）：成本合计 836,294.40 / 含税报价 1,246,891.72 / 毛利率 24.21% /
加权满足度 80.00% / 风险命中 7 条（高 4、中 1、低 2）。

数字对不上时按这个顺序查：运行配置是否合法 → 技能是否真被挂上 → SKILL.md 里脚本路径是否绝对 →
人设里是否带了「先跑脚本」的硬规则。四项都对仍然漂移，就是源技能本身没有给出判据，需要在技能里补。

## V4 —— 技能资源完整性

```bash
# 对比源包技能目录与落地目录（示例：launch-toolkit）
diff -r <源包>/skills/launch-toolkit ~/.office-claw/skills/launch-toolkit
```

判定：**唯一允许的差异是源端多出的 `_meta.json`**（平台专有物，按规则剥离）。`references/`、`scripts/`、`templates/`、`assets/` 里的文件必须逐一对上，数量与大小一致。

失败处置：缺失说明复制被白名单截断——`skills/<slug>/` 必须整棵复制，子目录不做白名单。重跑 `--install` 补齐。

## V5 —— 正文保真

```bash
diff <源包>/agents/<agent>.md ~/.office-claw/skills/<name>/SKILL.md
```

判定：只允许两处差异——顶部补齐的 `name`/`description` frontmatter，末尾一行来源注释。

失败处置：出现成段改写即为违规（改写正文等于改行为），回滚备份重跑，不要在落地文件上手动修补。

## V6 —— 头像真实可加载

```bash
python scripts/repair_avatars.py          # 只诊断
```

期望：列出每位专家的头像路径与状态，坏图数为 0。

四条判据同时成立才算通过：

1. `avatar` 指向的文件**真实存在**——否则前端 `<img>` 加载失败，浏览器改显示 alt 文本，中文名挤进 40px 圆框＝「乱码」；
2. 文件**不是占位图**——小于 64px 或小于 2KB 一律判为 placeholder（源端常见 8×8 单色 png）；
3. 同一专家的头像在**全部注册位置一致**（专家卡 / catalog / breeds / variants / user-experts / 团队条目）；
4. 团队条目读的是 `teams[].avatar`，不是成员头像。

失败处置：`repair_avatars.py --fix` 止损（退到应用内置图）；要像样的图就按职能生成后 `set_avatar.py` 换上。**禁止按专家名硬拼** `/avatars/experts/<name>.png`。

## V7 —— 幂等与回滚

```bash
# 同一条命令连跑两次，条目数应不变
python scripts/migrate_suite.py --source <套件目录> --staging <输出目录> --install
```

判定：第二次运行后 `experts/` 文件数、`user-experts.json` 条目数、`user-teams.json` 团队数均与第一次相同，不出现重复专家或重复团队。

同时确认备份已生成：目标目录下存在 `<文件名>.bak-<时间戳>`。回滚方式即用备份覆盖回去。

失败处置：出现重复说明 `--name` 变了——`name` 是唯一键，重跑必须用同一个 `name`。

## V7b —— 界面确认（唯一无法脚本化的环节）

新建会话后人工核对（无需重启；界面未刷新再重启一次）：

1. 专家列表里能看到迁移的专家，头像正常显示（不是色斑、不是文字）；
2. `@昵称` 能唤起，且回复按要求走主提示词；
3. 专家团出现在团队区，成员齐全，主理人没有在专家列表里重复出现；
4. 点开任一技能，`Skill not found` / `configured but not installed` 类报错为 0。

## 判定汇总

| 段 | 通过判据 | 是否可脚本化 |
|---|---|---|
| V0 | `--help` 正常；`--list` 能看到目标包 | 是 |
| V0b | `[识别]` 路径正确；歧义时退出码 3、未命中时 2 | 是 |
| V1 | 平台与清单识别正确 | 是 |
| V2 | frontmatter 齐、slug 对应、报告两栏已处理 | 半自动（第 3 条人工） |
| V3 | 十项全 ✓、结论通过、退出码 0 | 是 |
| V3c | `check_runtime.py` 结论「应用侧已认得全部迁移内容」 | 是（需应用运行 + 有效会话） |
| V3b | 真实任务数字与源端一致、有脚本调用痕迹 | 半自动（人工派任务 + 比对） |
| V4 | 仅缺 `_meta.json` | 是 |
| V5 | 仅差 frontmatter 与来源注释 | 是 |
| V6 | 存在 + 非占位 + 多处一致 | 是（一致性靠 `repair_avatars.py` 诊断） |
| V7 | 重跑不增条目、备份存在 | 是 |
| V7b | 界面可见、`@` 可唤起、团队齐全 | 否（人工） |

全部通过后按交付说明四段（装了什么 / 在哪 / 丢了什么 / 还要人做什么）输出，不要用「应该可以了」结尾。
