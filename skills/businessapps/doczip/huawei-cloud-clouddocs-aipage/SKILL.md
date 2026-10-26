---
name: huawei-cloud-clouddocs-aipage
version: 1.1.0
description: "最基础的「基于内容创建在线 page 文档」技能：用户提供内容（主题/文本/要点），模型生成 markdown，经 clouddocs-cli page +create 一次创建在线 page 文档并交付链接，再用 clouddocs-cli file +export 导出为 docx 存到本地，全程 clouddocs-cli、不开编辑器。用于把一段内容变成一篇可分享的在线文档，并保留一份本地 Word 副本。Trigger: 生成一篇在线文档, 创建page文档, 根据内容生成文档, 把我的内容变成云文档, 创建在线page, 生成云文档, 把要点整理成文档, 创建一篇page。"
triggers:
  - 生成一篇在线文档
  - 创建page文档
  - 根据内容生成文档
  - 把我的内容变成云文档
  - 创建在线page
  - 生成云文档
  - 把要点整理成文档
  - 创建一篇page
not_for:
  - 编辑已创建的 page 单块（追加/替换/插入/删除）——用 clouddocs-cli page +update
  - 生成幻灯片/表格/思维导图文档
  - 本地 pdf 文件导出
  - 带模板/主题的页面创建
---

# huawei-cloud-clouddocs-aipage — 基于内容创建在线 page 文档（最基础版）

从 slide 技能裁剪出的最小 page 技能：**用户给内容 → 模型生成 markdown → `page +create` 一次创建 → 交付链接 → `file +export` 导出本地 docx**。只保留全新创建链路、导出收尾与幂等断点，不包含单块编辑、模板、批量等能力。

## 核心设计：生成 markdown → 一次创建 → 导出 docx ★

全程一条主链路，无分阶段渲染：

1. **生成**：模型根据用户原始需求构造 markdown，写入 `<项目工作目录>/drafts/page.md`（内容规范见 `references/page-content.md`）。
2. **创建**：`create_page.py` 读 markdown，经 `clouddocs-cli page +create --title <t> --content <c> [--format 1]` 一次创建在线 page 文档，落 `created_doc.json` 锚点，回吐 `doc_id` + `doc_url`。
3. **交付**：把 `doc_url`（`{base}/wapp/doc/<docId>`）交给用户。
4. **导出**：`clouddocs-cli file +export --document_id <doc_id> --export_type word` 把在线文档导出为 docx 存到本地交付目录（创建后先等 10 秒，失败隔 10 秒重试一次，仍失败则放弃导出只交付链接）。

`organization_id` / `wiki_id` 由 CLI 自动解析（个人空间 + 默认文档库），脚本无需前置 `space +fetch` / `docbase +fetch`；可选 `--parent-document-id` 建到指定父文档（如 AI 创作文档）。**幂等**是关键护栏：`created_doc.json` 已在则重跑只回吐、绝不重复建文档。

## 草稿目录约定（drafts 一律建在项目工作目录）★

- drafts 目录（`page.md` / `created_doc.json` / `page.kpge` 等中间产物）一律建在**当前用户项目工作目录**（会话 cwd / 调用方工作目录）下：`<项目工作目录>/drafts/`。
- **禁止**写入技能安装目录（`~/.cac/skills/<技能名>/`）或技能源码目录（`<skills 源码仓库>/.../skills/<技能名>/`）——技能目录是只读的规范与脚本，不属于任何一次具体运行。
- 步骤 1 由模型用 Write 建 `<项目工作目录>/drafts/page.md`（Write 自动创建目录）；脚本默认 `--drafts-dir drafts`，在项目工作目录运行即解析到 `<项目工作目录>/drafts/`。
- `created_doc.json`（幂等锚点）与 `page.kpge` 随 drafts 一起落在项目工作目录，随会话交付物留存，可跨会话断点恢复。

## 用户交互铁律

向用户**只输出**：`"正在生成文档内容..."`（可选）/ `"文档已创建：<链接>"` / `"本地Word：<本地路径>"`（收尾）/ 简洁错误说明（导出失败时：「文档已创建：<链接>，本地 Word 导出失败」）。其余一律静默——技能名 / 脚本名 / 文件路径 / doc_id / 接口返回原文等内部状态全部不许出现。**收尾只报本地文件路径，不附加文章内容概述/章节总结**。

## 前置检查

- **CLI 已安装**：`command -v clouddocs-cli`（Windows cmd/PowerShell 用 `where clouddocs-cli` / `Get-Command clouddocs-cli`）能定位到可执行文件；**找不到则先按 `<技能基目录>/bin/cli-installation-guide.md` 安装子技能完成安装**（仅支持 Windows，执行 `bin/windows/install-windows.ps1`，详见该子技能），装完再继续。
- **认证**：`clouddocs-cli auth status` 显示 `ready`；否则用「两步走」设备授权（**禁止直接运行阻塞式 `clouddocs-cli auth login`**——它打印 URL 后挂起轮询等待授权，命令不退出，被管道捕获时 URL 也不输出，会卡死）：
  1. `clouddocs-cli auth login --no-wait --json` → 立即返回 JSON，取 `verification_url` 和 `device_code`；
  2. **自动打开授权页**（Windows）：`powershell.exe -NoProfile -Command "Start-Process '<verification_url>'"`（实测可靠弹出浏览器；若环境仍无法打开，把 URL 念给用户手动打开）；
  3. **后台续接自动感知授权**：发起授权后立即在后台运行 `clouddocs-cli auth login --device-code <device_code>`（该命令自带轮询，默认最多 240s）——**用户授权成功那一刻后台任务自动完成登录并保存凭证，无需等用户通知**；后台任务未结束期间把 URL 交给用户点授权。
- **服务地址**：`clouddocs-cli config init --host <url>`，或 `~/.clouddocs/config.json` 已配置 `base_url`。
- 排查用：在项目工作目录运行 `python3 <技能基目录>/scripts/create_page.py --probe-auth`（只看 base/鉴权，不发网络）。

## 步骤 1. 生成 markdown

模型根据用户原始需求（主题、要点、用途、受众等）按 `references/page-content.md` 的规范构造 markdown，用 Write 一次写入 `<项目工作目录>/drafts/page.md`（drafts 目录约定见上文「草稿目录约定」）。模型**不得直接调 CLI**。

- 文档标题取自内容主题，`# <标题>` 首行与 `--title` 一致。
- 覆盖用户全部要点，禁止连续重复空行，禁止编造数据。
- 内容较长时保持结构完整；若超过 CLI 参数上限（约 30KB）提示用户分段或精简。

## 步骤 2. 创建在线 page 文档（一发脚本）

```bash
cd <项目工作目录>
python3 <技能基目录>/scripts/create_page.py --title '<按主题命名的文档标题>'
```

cwd = **项目工作目录**，脚本默认 `--drafts-dir drafts`（即 `<项目工作目录>/drafts/`）。脚本读 `<项目工作目录>/drafts/page.md`，经 `page +create` 建文档并落 `created_doc.json`。照退出码做：

| 退出码 | 含义 / 下一动作                                                                           |
| ------ | ----------------------------------------------------------------------------------------- |
| 0      | 创建成功，stdout 含 `doc_id` / `doc_url` → 进步骤 3 交付。                                |
| 1      | 参数或前置缺失（未建文档）→ 按 stderr 修（多为缺 `--title` / 缺 `page.md`）后重跑本脚本。 |
| 2      | 鉴权 / 网络失败（**未建文档**）→ 停下报用户，绝不反复重试；可先 `--probe-auth` 排查。     |

可选参数：

```bash
python3 <技能基目录>/scripts/create_page.py --title '<标题>' --content '<markdown 文本>'        # 不走文件
python3 <技能基目录>/scripts/create_page.py --title '<标题>' --parent-document-id '<父文档ID>'   # 建到指定父文档
python3 <技能基目录>/scripts/create_page.py --title '<标题>' --dry-run                          # 预览请求，不发网络
python3 <技能基目录>/scripts/create_page.py --title '<标题>' --drafts-dir '<自定义目录>'         # 指定草稿目录（默认 ./drafts）
```

🚨 退出码 0 后**不要 verify**、不要回生成阶段。脚本 stdout 已是完整真值源。

## 步骤 3. 交付

把 `doc_url` 念给用户即可。**创建成功后不要主动打开文档链接**（不调用 `cloud_doc_operate` open，不启动浏览器），打开与否由用户自行决定。

## 步骤 4. 导出 docx 到本地（收尾）

在线 page 文档创建成功后，**先等 10 秒再导出**（给后端完成内容落库/索引留时间，确保导出的 docx 是全量内容），用 `clouddocs-cli file +export` 把文档导出为 docx 存到本地，作为离线交付物：

```bash
sleep 10   # 创建后等 10 秒，等后端落库完成
clouddocs-cli file +export \
  --document_id '<doc_id>' \
  --export_type word \
  --file_name '<按主题命名>' \
  --output '<本地保存目录或全路径>'
```

- `doc_id` 取 `created_doc.json` 的 `doc_id`（或从 doc_url 末尾截取）。
- **`--output` 目标目录需已存在**（否则 CLI 把 `--output` 当全路径文件写入，产物变成无扩展名文件）；目录存在时导出文件名是 `<document_id>.docx`。
- 返回 JSON 含 `file_path` / `file_name` / `file_size`；按返回的 `file_path` 把导出文件**重命名为「<主题>.docx」并放到交付目录**（实测 `--file_name` 对导出文件名不生效）。
- 导出内容以**后端文档对象里的全量内容**为准，与在线渲染一致。

**失败重试策略（最多尝试 2 次，失败即放弃）**：

1. 第一次导出失败 → `sleep 10` 后重试一次完全相同的 `file +export`。
2. 重试仍失败 → **放弃导出**，不再重试。停下向用户说明：「文档已创建：<链接>，本地 Word 导出失败」，交付链接即可（文档本身已成功，docx 可后续手动重跑步骤 4 补齐）。

## 断点恢复

- **幂等锚点**：`<项目工作目录>/drafts/created_doc.json`（建文档成功即落盘）。中断后在项目工作目录直接重跑 `python3 <技能基目录>/scripts/create_page.py --title ...`（默认草稿目录 `./drafts`），锚点已在 → 只回吐 `doc_id`/`doc_url`、绝不重复建文档。
- **`<项目工作目录>/drafts/page.md`**：markdown 内容落盘后不随流程删除，随时可改内容重跑（需先删 `created_doc.json` 才会重建）。
- **未导出 docx** → 重跑步骤 4 的 `file +export`（幂等，可重复导出覆盖本地文件；导出失败最多重试 1 次，之后停下交付链接）。

## 文件契约（drafts 中间产物，一律在项目工作目录下）

| 文件                                     | 说明                                                                                               |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `<项目工作目录>/drafts/page.md`          | 模型生成的 markdown（步骤 1 落盘，create_page.py 读取）                                            |
| `<项目工作目录>/drafts/created_doc.json` | 建文档锚点（doc_id / doc_url，幂等依据）                                                           |
| `<项目工作目录>/drafts/page.kpge`        | doc_url 纯文本（运行态）                                                                           |
| `<项目工作目录>/outputs/<主题>.docx`     | 步骤 4 导出的离线交付物（file +export 产物，重命名为主题名，交付目录 = `<项目工作目录>/outputs/`） |

## 约束

- 建文档**只走 `clouddocs-cli`**（`create_page.py` 经共享适配层 `scripts/_hws_cli.py` 调 CLI，认证由 CLI 自管），**禁止**脚本直连后端 HTTP。
- 严禁绕过 `create_page.py` 直接调用 `clouddocs-cli page +create`，严禁手写脚本调用后端 API 建文档。
- `created_doc.json` 只能由 `create_page.py` 落盘；模型和协调器不得手写覆盖。
- drafts 中间产物（`page.md` / `created_doc.json` / `page.kpge`）一律落在**当前项目工作目录**下，禁止写入技能安装目录（`~/.cac/skills/<技能名>/`）或技能源码目录。
- 内容优先直传 markdown；仅当后端明确拒绝 markdown 时按 `references/page-content.md` 第二节改用 block JSON 兜底。
- 导出 docx 走 `clouddocs-cli file +export`（`--export_type word`），**禁止**手写脚本拼接 docx 或绕过 CLI。
- JSON 输出严禁包含 markdown 代码块标记；文本中文，JSON 键名英文。

## 运行时依赖

- **`clouddocs-cli` 可执行文件**（`requires: bins: ["clouddocs-cli"]`）：所有后端操作经它执行。前置条件：已安装（未安装时按 `<技能基目录>/bin/cli-installation-guide.md` 安装子技能先安装，仅支持 Windows）、已登录（`clouddocs-cli auth status` 显示 ready；否则 `auth login` 把验证 URL 交给用户）、服务地址已配置（`clouddocs-cli config init --host <url>` 或 `~/.clouddocs/config.json` 的 `base_url`）。
- **Python 3.8+ 标准库**：两个脚本均只使用标准库，无第三方依赖。
