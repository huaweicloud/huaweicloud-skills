# 验收标准

## 概述

本文档把「迁好了没有」拆成可勾选的判据。每条给**判定方法**与**通过线**，避免用「看起来正常」「应该没问题」收尾。

分三级：**P0 必需**（缺一即不通过）、**P1 应该满足**（缺失须书面说明理由）、**P2 建议**（记录即可）。

## 一、功能验收（P0）

| 编号 | 验收项 | 判定方法 | 通过线 |
|---|---|---|---|
| F1 | 专家卡可解析 | 读 `~/.office-claw/experts/<name>.json` | JSON 合法，含 `expertId`/`displayName`/`nickname`/`skills`/`roleDescription` |
| F2 | 技能真实存在 | 专家卡 `skills[]` 逐个对目录 | 每个 slug 在 `~/.office-claw/skills/<slug>/` 下有目录，且含 `SKILL.md` |
| F3 | 列表可见 | 重启后看 UI 专家列表 | 迁移的专家全部出现 |
| F4 | 昵称可唤起 | 输入 `@昵称` | 能选中并唤起，回复走主提示词而非通用回答 |
| F5 | 技能可加载 | 触发主提示词里的一项能力 | 无 `Skill not found` / `configured but not installed` |
| F6 | 团队形态成立 | 看团队区 | 团队出现，成员数 = 源包角色数，`leaderExpertId` 指向主理人 |
| F7 | 无重复入口 | 数列表条目 | 团队只出现一次；主理人与成员在专家列表各有一条（这是解析角色所必需，不算重复入口） |
| F8 | **团队可召唤** | 团队会话里发一句真实任务 | 主理人正常拆标派活，不出现「主理人出错」/ `E-1105` 类错误码 |
| F9 | **成员档案可读** | 看团队任务卡片 | 显示中文名与角色说明，不是 `expertId` 英文串 |

## 二、注册完整性（P0）

七处注册缺一不可，任一处缺失都表现为「文件都在，UI 就是不出现」。

| 编号 | 注册点 | 通过线 |
|---|---|---|
| R1 | `experts/<name>.json` | 文件存在且字段齐全 |
| R2 | `catalog.json` | `experts[]` 含该 name，与专家卡一一对应 |
| R3 | `user-catalogs/<uid>.json` | `breeds[]`/`variants[]` 是数组、`agentId` 非空且唯一、`defaultVariantId` 指向存在的变体、默认变体带 `mentionPatterns` |
| R4 | `users/<uid>/user-experts.json` | **每一个**专家（含团队主理人与成员）都有完整卡（`visibility`/`defaultModel`/`providerProfileId` 齐），且 `personality` 与专家卡同值 |
| R5 | 应用目录 `skills/<slug>/` | 技能装在安装根下，不只是 `~/.office-claw/skills/` |
| R6 | `installed-skills.json` | 每个 slug 有 `{"source":"local","name":<slug>}` 条目 |
| R7 | `capabilities.json` | 每个 slug 有 `{"type":"skill","enabled":true,"source":"custom"}` |
| R8 | `user-teams.json`（团队） | `teams[]` 含 `teamId`/`displayName`/`members[]`/`leaderExpertId`，队级标量齐全，成员均为已注册 `expertId` 且有 `displayName` |
| R9 | 运行配置合法 | 四处注册里的 `providerProfileId`+`defaultModel` 都在本机 `model.json` 中存在，`variant.provider == relayclaw`，roster 同款字段齐全 |

判定命令：`python scripts/verify_install.py -q`，末行须为「结论：通过」。

## 三、内容保真（P0）

| 编号 | 验收项 | 通过线 |
|---|---|---|
| C1 | 技能正文未改写 | 与源 `agents/<agent>.md` 对比，只多 frontmatter 与末尾一行来源注释 |
| C2 | 资源目录全量复制 | 源包 `skills/<slug>/` 与落地目录逐文件对齐，唯一允许少 `_meta.json` |
| C3 | 相对引用可解析 | `SKILL.md` 里的脚本引用已改成**绝对路径**且文件存在（团队会话 cwd 不在技能目录，相对路径=必然失效），断裂引用数 = 0 |
| C4 | 专有物已剥离 | `_meta.json`、源端 connector 声明、`version` reload 机制均未搬入，且报告里写明丢弃清单 |
| C5 | **人设保真** | `personality` 是 `agents/*.md` 全文（去 frontmatter 与一级标题），长度 ≥ 200 字，且与 `roleDescription` 不相同 |
| C6 | **分工保真** | 每个角色只挂自己用得到的技能：frontmatter `skills:` 优先，其次正文点名的包级技能；主理人只挂人设技能 |
| C7 | **数字保真** | 用源端同一份输入跑真实任务，关键数字逐项一致，且产物中有脚本调用痕迹（非模型口算） |
| C5 | 合成内容有留痕 | 源端无入口提示词而合成的人设，文件内有标注、报告有「需人工确认」条目 |

## 四、视觉验收（P1）

| 编号 | 验收项 | 通过线 |
|---|---|---|
| A1 | 头像文件存在 | `avatar` 指向的文件真实存在，坏路径数 = 0 |
| A2 | 非占位图 | 边长 ≥ 64px 且体积 ≥ 2KB，不是纯色块 |
| A3 | 尺寸统一 | 建议 512×512，正方形，适合圆形裁切 |
| A4 | 多处一致 | 专家卡 / catalog / breeds / variants / user-experts / 团队条目指向同一文件 |
| A5 | 团队头像独立 | 读 `teams[].avatar`，不是直接复用成员头像 |

判定命令：`python scripts/repair_avatars.py`（诊断模式，不写盘）。

## 五、可运维性（P1）

| 编号 | 验收项 | 通过线 |
|---|---|---|
| O1 | 幂等 | 同一命令连跑两次，专家数、团队数、技能数均不变 |
| O2 | 有备份 | 每次写盘前生成 `<文件名>.bak-<时间戳>`，路径已告知用户 |
| O3 | 可回滚 | 用备份覆盖即可恢复；回滚步骤写进交付说明 |
| O4 | 源端只读 | 迁移前后源套件目录文件数与 mtime 无变化 |
| O5 | 无云端依赖 | 断网可完整跑通 |

## 六、交付文档（P2）

| 编号 | 验收项 | 通过线 |
|---|---|---|
| D1 | 四段说明齐全 | 装了什么（专家名+技能数）/ 在哪（数据目录路径）/ 丢了什么 / 还要人做什么 |
| D2 | 待验证项已列出 | 带 `scripts/` 的技能，其依赖、路径分隔符、编码风险逐条列出 |
| D3 | 无「应该可以了」 | 不含模糊承诺；未验证的项明确写「未验证」 |

## 七、放行门槛

| 结论 | 条件 |
|---|---|
| ✅ 通过 | P0 全部满足，P1 无缺失 |
| ⚠️ 有条件通过 | P0 全部满足，P1 有缺失但已逐条书面说明并获用户认可 |
| ❌ 不通过 | 任一 P0 缺失 |

P0 只要有一项不过，就不要交付，也不要用「重启试试」掩盖——七处注册与资源复制的缺失不会因重启自愈。

源包必须由 `migrate.py`（或对应迁移器）识别过：平台、路径、形态三项与事实一致，歧义时是问过用户才定的——
靠猜目录名硬转出来的东西，即使文件写对了也不算通过。

放行前两条命令都要过：`verify_install.py -q` 结论「通过」（静态），`check_runtime.py` 结论「应用侧已认得全部迁移内容」（动态，应用需在运行）。只过第一条就交付，等于把「文件写对了」当成「能用」，实测中最贵的一次返工就是这么来的。

## 八、常见「假通过」

以下现象看着像通过，实际没过，验收时重点看这几处：

- 专家出现在某处但 UI 列表没有 → 只写了专家卡，`user-experts.json` 未写。
- 专家在列表里、团队也在，但团队一召唤就报「主理人出错」→ 主理人没写进 `user-experts.json`，`/api/experts` 里没有它（这是最隐蔽的假通过：`user-teams.json` 里明明有主理人）。
- 成员都能答，但四个人说同一套话 → `personality` 被写成团队简介，只是长度不为 0，脚本不容易发现。
- 团队"跑通了"，但成本数字比源端少三万 → 成员没调用官方脚本，自己重写了算法；查 SKILL.md 里是不是 `python scripts/x.py`。
- 技能目录在 `~/.office-claw/skills/` 里，重启后消失 → 没装进应用安装目录，或 `installed-skills.json` 未登记。
- 头像「有图」但是一整块颜色 → 源端 8×8 占位图被原样复制，`avatar_quality` 判据没过。
- 专家名显示成 `{'zh': '…', 'en': '…'}` → 多语言字段被当字符串，`pick_text()` 未生效。
- 团队在，但成员点不开 → `members[].expertId` 指向未注册或已删除的卡。
- 交付报告写「全部迁移完成」，但 `report.md` 的「丢弃」栏非空 → 丢弃项没交代，属未完成。
