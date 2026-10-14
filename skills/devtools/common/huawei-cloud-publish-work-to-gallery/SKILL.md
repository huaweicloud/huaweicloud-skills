---
name: huawei-cloud-publish-work-to-gallery
description: |
  Publish user's work to the Huawei Cloud University Operations Platform (华为云高校运营平台/作品陈列馆).
  Use this skill whenever the user wants to publish, submit, or upload a project/work to the gallery or an activity
  (活动) on the platform — including casual phrasings like "把作品发布上去", "投稿到陈列馆", "传作品到平台", "提交作品/项目", "报名发布作品",
  as well as formal ones like "publish to work gallery", "submit to an activity", "upload work to the platform".
  Do NOT use for general dev questions, git push to GitCode alone, or platform browsing without publishing intent.
  Triggers include: "把作品发布上去", "投稿到陈列馆", "传作品到平台", "提交作品/项目", "报名发布作品", "publish to work gallery", "submit to an activity", "upload work to the platform"
metadata:
  tags: huawei-cloud,publish,gallery,university operations platform
version: 2026.10.13.001
---

# Publish Work to Gallery

发布作品至华为云高校运营平台。**优先调用内置脚本**（单入口、fail-fast、自带 `--help`），报错才查 [references/troubleshooting.md](references/troubleshooting.md)。

## Pipeline

```
Step 1 (workDir, domainID, STS)
Step 2 (port→变量, envUrl→变量)              ← 依赖 Step 1
  ├── Step 3 (gitUrl, gitBranch, workName)   ← 只依赖 workDir
  ├── Step 5 (introduction, camps)           ← 只依赖 workDir + STS
  ├── Step 4 (coverImage)                    ← 依赖 port + workName
  └── Step 6 (detailZip)                     ← 依赖 workName + 代码分析
Step 7 (trainingCampId)                      ← 依赖 Step 5 camps
Step 8 (publish)                             ← 依赖以上全部
```

**并行（Step 2 完成后）**：Step 3/4/5/6 **互不依赖，四者全并行**（取最长路径 Step 4 ~90s，而非串行 ~160s）。Step 4 内 `preflight` + `ensure-utf8` 再并行。**注意 Step 6 的隐性依赖**：`generate_diagram.py` 用 Playwright，由 Step 4 的 `preflight` 安装（首次含 CJK 字体 + Chromium，5~10 分钟）——脚本已内置门禁：缺 `font-gate-ok` 标记时 **exit 1 提示等待**，不报 `ModuleNotFoundError`。并行跑 Step 6 收到该提示 → 等 preflight（轮询日志/标记）完成后再重跑本步，不是真失败。

**变量贯穿**：`port`/`workName`/`envUrl` 在最早步骤确定后作为变量传递全流程，禁止硬编码（隧道 URL 含 port，换端口时 envUrl 随之变）。

**执行模型**：① **脚本契约优先**——按 stdout 成功信号判定，**成功路径零源码读取**；失败才 `脚本提示 → troubleshooting 对应节 → grep 脚本源码` 逐级查 ② 禁止手工绕过门禁 ③ 网络超时统一 3s ④ `detect-env.mjs` 确定平台后只读对应平台 reference（按目录跳转，不全读）⑤ **合并无依赖的 bash 调用**：用 `;` 串联进一条命令，减少工具往返（每次 ~1-2s） ⑥ **需用户交互的命令一律把链接/二维码原样展示给用户，禁止用 agent 内置浏览器/工具（browser_use_open 等）代开**——脚本本地已起回调服务器，用户在任意浏览器授权后脚本自动拿到 token，agent 全程不需要浏览器。

## Core Commands（脚本契约速查）

> **`$SKILL_DIR` 定义**：本 skill 的安装目录绝对路径（含 SKILL.md 的目录）。执行前先设置 `export SKILL_DIR=/path/to/huawei-cloud-publish-work-to-gallery`（示例：`$HOME/.local/share/huawei-cloud-publish-work-to-gallery`）。所有脚本均为可执行文件（带 shebang），直接用 `$SKILL_DIR/scripts/…` 前缀调用，**无需** `node`/`python`/`bash` 解释器前缀（该说法仅 Linux 成立；**Windows 下 .mjs/.py 需 `node`/`python` 前缀、`preflight.ps1` 需 `powershell` 前缀**）；若安装器未恢复可执行位（Linux 直接调用报 `Permission denied`），先执行一次 `chmod +x "$SKILL_DIR/scripts/"*` 自愈，不改脚本；参数一律用可解析的示例值（无 `<…>` 占位符，避免命令提取器剥离后缺参/空值）。**W/R 标注**：`W` = 平台写操作（发布作品，必须经用户确认后才执行）；`R` = 只读查询/本地辅助命令。

| 步骤 | 脚本/命令 | W/R | 成功信号（exit 0 且） | 失败（exit 1；2=参数错） |
|------|-----------|-----|----------------------|-----------------------------------|
| 前置 | `$SKILL_DIR/scripts/api.mjs GET /v1/gallery/announcements/current --prefix open-api-guest` | R | stdout 首行 `#status=200` | 超时/拒连 → 提示排查网络 |
| 前置 | `$SKILL_DIR/scripts/check-version.mjs`（读自身 name/version 调 `/v1/gallery/skills/status` 判定） | R | exit 0 且首行 `status=ok`/`status=skip` | exit 1（`status=outdated` + 平台升级文案）→ 原样提示升级并停止；判定规则见 api-spec |
| 5/7 | `$SKILL_DIR/scripts/api.mjs GET "/v1/gallery/camps" --creds-file ./sts-creds.json --fields "id,name,school,status,startsAt,endsAt"` | R | `#status=200` | 401 → 刷新 STS |
| 1 | `$SKILL_DIR/scripts/scan-projects.mjs` | R | stdout `#project <n> <path> <type>` | exit 1=无候选 |
| 1 | `$SKILL_DIR/scripts/resolve-domain.mjs --hcloud /usr/local/bin/hcloud` | R | stdout `#domain=<id> name=<name>` | exit 1=hcloud 失败（stderr 含排查指引） |
| 1 | `$SKILL_DIR/scripts/gen_sts.py --account 100000000000 --hcloud /usr/local/bin/hcloud --creds-out ./sts-creds.json --sh-out ./sts-creds.sh` | R | 写 `./sts-creds.json`（含 `_refresh`）+`./sts-creds.sh`（相对路径，后续 `--creds-file ./sts-creds.json` 直接可用） | 见 [troubleshooting#domain-id-resolution-issues] |
| 3 | `$SKILL_DIR/scripts/ensure-git-root.mjs /path/to/project` | R | exit 0（`git -C /path/to/project rev-parse --git-dir` = `.git`） | exit 1=workDir 非仓库根 → 禁止读 remote，按 Step 3 处置 |
| 3 | `$SKILL_DIR/scripts/read-git-info.mjs /path/to/project` | R | `#gitUrl=<https://… .git>` `#gitBranch=<分支>`（已核对远端确有该分支） | exit 1=非 git 仓库 / url 校验失败 / `#branchAbsent=1`（远端不存在该分支——按 SHA 给唯一处置：checkout 或 push，转述 stderr 即可）；网络/凭证原因无法核对时 stderr 警告但不拦截（发布时服务端会校验分支存在性） |
| 3 | `$SKILL_DIR/scripts/ensure-gitcode-credential.mjs` | R | `#credential=found`（有凭证）或 `#credential=missing`（无凭证，走 OAuth） | exit 0；无手动备选 |
| 3 | `$SKILL_DIR/scripts/gitcode-oauth.ensure.mjs --start` | R | `#oauth=ready`（有 token）/ `#oauth=started session_id=123456 login_url=https://example.com`（stdout 立即返回，二维码走 stderr） | 缺失 `#oauth=absent` exit 1；失败 `#oauth=failed reason=timeout` exit 1 |
| 3 | `$SKILL_DIR/scripts/gitcode-oauth.ensure.mjs --wait 123456 --timeout 300` | R | `#oauth=done`（token 已写 `~/.gitcode/auth.toml`） | `#oauth=failed reason=timeout\|finish\|…` exit 1 |
| 3 | `$SKILL_DIR/scripts/extract-workname.mjs /path/to/project` | R | stdout `#name=MyWork source=frontmatter` | exit 1=workDir 不存在 |
| 2 | `$SKILL_DIR/scripts/spawn-detached.mjs --out /tmp/spawn.out --pidfile /tmp/app.pid --cwd /path/to/project -- npm run dev` | R | `#spawn=ok pid=12345 out=/tmp/spawn.out` | exit 1=启动失败 |
| 2 | 隧道：先跑 `$SKILL_DIR/scripts/detect-env.mjs` 看 `tunnel` 字段；`true`（Linux）→ 加载内置 skill `huawei-cloud-devbridge-tunnel` 开隧道；`false`（Windows/macOS）→ **禁止加载，`envUrl=""`** | R | 取得 `envUrl`；skill 不可用/失败 → `envUrl=""` 照常发布 | tunnel=false 时仍尝试开隧道 = 违反契约 |
| 4 | `$SKILL_DIR/scripts/preflight.sh`（Win: `powershell $SKILL_DIR/scripts/preflight.ps1`） | R | 写 `font-gate-ok`（`ok=true gate=preflight`） | 截图/封面/图表**禁止** |
| 4 | `$SKILL_DIR/scripts/ensure-utf8.mjs /path/to/project` | R | 写 `utf8-gate-ok` | 编码非 UTF-8 → 禁止截图 |
| 4 | `$SKILL_DIR/scripts/build-cover.mjs --url http://127.0.0.1:8080 --project-dir /path/to/project --title "MyWork" --out /tmp/cover.png` | R | stdout 一行 `#cover=/tmp/cover.png layout=… multi=yes tmp=/tmp/shots`（内部调 `screenshot_guard.py`+`generate_cover.py`） | exit 1 → 截图/校验/合成任一失败，stderr 详情 |
| 4 | `$SKILL_DIR/scripts/generate_cover.py --screenshot /tmp/shots/shot-index.png --title "MyWork" --out /tmp/cover.png` | R | 封面 PNG，再过 `verify-glyphs.py` | exit 1 → 禁止继续合成 |
| 4/6 | `$SKILL_DIR/scripts/verify-glyphs.py /tmp/cover.png --quiet` | R | exit 0（stdout 仅 1 行省 token） | exit 1 → 疑似豆腐块 → 修字体 |
| 5 | `$SKILL_DIR/scripts/count-cjk.mjs --file /tmp/intro.txt` | R | 总字符数 15~50 | exit 1 → 改写简介再计 |
| 6 | `$SKILL_DIR/scripts/generate_diagram.py --html /tmp/diagram.html --out /tmp/diagram.png --width 1280` | R | 图表 PNG，再过 `verify-glyphs.py --quiet` | 同封面；缺 `font-gate-ok` → exit 1 提示等 preflight（隐性依赖，见并行说明） |
| 6 | `$SKILL_DIR/scripts/build-detail-zip.mjs --readme README.md --resources /path/to/project/resources --out /tmp/detail.zip` | R | 打包+校验一步完成 | exit 1 → 按输出修复重打 |
| 8 | `$SKILL_DIR/scripts/check-gates.mjs --cover /tmp/cover.png --detail /tmp/detail.zip --strict --max-age 3600 --quiet` | R | exit 0（stdout 仅 1 行省 token） | exit 1 → 回退重跑门禁 |
| 8 | `$SKILL_DIR/scripts/publish-work.mjs /tmp/params.json --max-age 3600` | **W** | `#status=201`（仅输出 workId/workUrl/reward） | envUrl 不可达 → exit 1（提示检查本地服务）；409/其他 → 原样输出完整响应 |

> 标记文件位置：Linux `/tmp/`；Windows `os.tmpdir()`（`%TEMP%`）。

## Parameter Confirmation（参数确认）

| 参数 | Required | 说明 | 来源 |
|------|----------|------|------|
| `workDir` | 是 | 作品项目根目录（须为 git 仓库根） | Step 1（用户选择） |
| `domainID` | 是 | 华为云账号 Domain ID | Step 1（resolve-domain.mjs） |
| `credsFile` | 是 | STS 临时凭证 JSON（`sts-creds.json`） | Step 1（gen_sts.py） |
| `port` | 条件 | 本地服务端口（用户拒绝运行项目则无） | Step 2 |
| `envUrl` | 条件 | DevBridge 隧道公网 URL（失败则为空串） | Step 2 |
| `gitUrl` / `gitBranch` | 是 | 作品仓库地址 / 分支 | Step 3 |
| `workName` | 是 | 作品名（<30 字符） | Step 3（extract-workname.mjs） |
| `coverImagePath` | 是 | 封面 PNG（须通过 verify-glyphs 校验） | Step 4 |
| `introduction` | 是 | 一句话简介（总字符数 15~50） | Step 5（count-cjk.mjs） |
| `detailsZipPath` | 是 | 作品详情 zip（README.md@根 + resources/） | Step 6 |
| `trainingCampId` | 是 | 训练营/活动 ID | Step 7（用户回序号选择） |

## Prerequisites（前置条件与依赖锁定）

- **hcloud + AK/SK**：Step 1 需要。未装/未配置 → [troubleshooting#domain-id-resolution-issues](references/troubleshooting.md#domain-id-resolution-issues)。
- **git**：Step 3。**zip** 仅 `build-detail-zip.mjs` 不可用时的备选（Linux `yum install zip`；Windows .NET `ZipFile`，见 [windows-setup.md](references/windows-setup.md)）。
- **Git Bash 前置**：`source $SKILL_DIR/scripts/setup-env.sh`（防 MSYS 路径转换）。PowerShell/CMD 无需。
- **OAuth 与本地环境依赖（自动化/沙箱限制）**：发布流程依赖用户 GitCode OAuth 授权（Step 3）与本地项目运行（Step 2 隧道 / Step 8 发布）。无人值守或沙箱环境（无用户浏览器授权）无法触达真实平台 API——此类用例需标注 `requires manual verification`，在真实用户环境复验。

## Core Workflow

### Step 1: Select Work Directory & Resolve IAM Domain Info

1. **告知用户**（选目录=同意）：将创建 IAM 自委托 `SELF_VERIFY` 生成 STS 临时凭证（900s），永久 AK/SK 留本地不上传。
2. **扫描项目根**：`$SKILL_DIR/scripts/scan-projects.mjs`——自动递归 `**/README.md`，检查指示文件，排除 `skills/`/`node_modules/`/`dist/` 等，扫描 CodeArts 沙箱目录。stdout 每行 `#project <n> <path> <type>`。
3. 列候选，等用户选 → `workDir`。
4. **解析 Domain ID**：`$SKILL_DIR/scripts/resolve-domain.mjs --hcloud /usr/local/bin/hcloud`——自动 `hcloud configure set --region` + `IAM KeystoneListAuthDomains` + 提取 `domain_id`，stdout `#domain=<id> name=<name>`。凭证优先级：env → hcloud 已配置 → 引导用户（[troubleshooting#2](references/troubleshooting.md#2-hcloud-credentials-not-configured)）。Windows 已由 `install-hcloud.ps1` 装好并写入用户 PATH，通常无需 `--hcloud`。
5. **生成 STS**：`$SKILL_DIR/scripts/gen_sts.py --account 100000000000 --hcloud /usr/local/bin/hcloud --creds-out ./sts-creds.json --sh-out ./sts-creds.sh` → `./sts-creds.json`（含 `_refresh`，使 401 自动刷新）。**凭证文件相对路径读写（同一 CWD 会话内一致，跨平台无需区分 `/tmp`/`%TEMP%`）**；⚠️ 勿 `git add`/提交该凭证文件，Step 8 结束后统一清理。hcloud 探测顺序与 resolve-domain 一致。
6. **输出**：`已获取 IAM Domain ID: <id>，用于将作品关联至您的华为云账号。`

**Output:** `workDir`、`domainID`、`credsFile`。

### Step 2: Run Project & Open Tunnel

**先跑 `$SKILL_DIR/scripts/detect-env.mjs`** 拿 `tunnel` 字段：`true`（Linux）→ 询问是否开隧道；`false`（Windows/macOS）→ **直接跳过隧道，`envUrl=""`，禁止尝试加载 DevBridge skill**。询问是否运行项目；拒绝则 `envUrl=""` → Step 3。

- **端口清理**：`netstat -ano | findstr :<port>`（Win），残留进程 kill。
- **启动项目**：`$SKILL_DIR/scripts/spawn-detached.mjs --out /tmp/spawn.out --pidfile /tmp/app.pid --cwd /path/to/project -- npm run dev` → `#spawn=ok pid=12345`。**必须传 `--cwd <workDir>`**（脚本默认用 `process.cwd()`，若执行目录非 workDir，`http-server .` 会 serve 错目录导致截图空白——2026-09-20 教训）。优先入口脚本（`npm run dev`/`python main.py`）；纯前端 `http-server . -p <port>`。≤30s 健康检查：`curl -sf --max-time 3 http://localhost:<port>`。
- **隧道（DevBridge）**：Linux **加载目标环境内置 skill `huawei-cloud-devbridge-tunnel`，按其操作说明执行开隧道并取得 `envUrl`**——禁止臆造/自行拼 devbridge 命令；该 skill 不可用或隧道失败 → `envUrl=""` 照常发布。**Windows 不使用 DevBridge**（无内置隧道能力）→ `envUrl=""`。**禁止在发布结束后自动清理隧道**——发布结束 ≠ 隧道生命周期结束（隧道可能被后续发布 / 409 改名重试复用）；仅用户明确要求清理时才按内置 skill 说明停流/删隧道。详见 [devbridge-tunnel.md](references/devbridge-tunnel.md)。

**Output:** `port`、`envUrl`（或 `""`）。

### Step 3: Git Repository Info & Work Name

`gitUrl` 必填，`gitBranch` 必须显式读取。`workName` 从 README 解析/合成（<30 字符）。

1. **仓库根检测（fail-stop）**：`$SKILL_DIR/scripts/ensure-git-root.mjs /path/to/project`——硬检测 workDir 自身是否为 git 仓库根（`git -C /path/to/project rev-parse --git-dir` 必须返回 `.git`）。若不是（如 workDir 无 .git 但父目录有，git 会向上递归返回父仓库 remote），脚本 exit 1 并提示。此时 **禁止** 直接 `git -C /path/to/project remote get-url origin`（会拿到父仓库 URL）。处理方式：① 问用户手动提供 `gitUrl` + `gitBranch`；② 或在 workDir `git init` + 推到远端后再读。检测通过才继续。
2. `$SKILL_DIR/scripts/read-git-info.mjs /path/to/project` 一步取 gitUrl/gitBranch（含仓库自检 + 凭证剥离 + **远端分支核对**，契约见上表）。`#branchAbsent=1` → **转述 stderr 的唯一处置**（脚本已按 SHA 判定：远端某分支与本地当前提交一致 → `git checkout <该分支>` 后重跑，无损且优于 push；否则 → `git push -u origin <branch>` 后重跑，切到远端旧分支会提交旧代码）。
3. **凭证排查**：`$SKILL_DIR/scripts/ensure-gitcode-credential.mjs`——有凭证即 `#credential=found`。**无凭证时走 gitcode-oauth 两阶段授权**（契约见上方 `gitcode-oauth.ensure.mjs --start`/`--wait`）：① `--start` 拿登录链接/二维码**原样展示给用户**，请用户在任意浏览器打开授权（**禁止用 agent 内置浏览器代开**），脚本本地已起回调服务器；② `--wait <session_id>` 阻塞轮询到 token 落盘。
4. **命名**：`$SKILL_DIR/scripts/extract-workname.mjs /path/to/project`——按优先级 frontmatter → H1 → manifest → `index.html <title>` → 目录名提取。stdout `#name=<name> source=<来源>`。`source=dirname` 时 agent 可合成/修改（<30 字符）。

**Output:** `gitUrl`、`gitBranch`、`workName`。

### Step 4: Cover Image

**门禁（并行）**：

| 门禁 | 命令 | 标记 |
|------|------|------|
| 渲染 | `$SKILL_DIR/scripts/preflight.sh`（Win: `$SKILL_DIR/scripts/preflight.ps1`） | `font-gate-ok` |
| 编码 | `$SKILL_DIR/scripts/ensure-utf8.mjs /path/to/project` | `utf8-gate-ok` |

门禁失败禁止截图/合成。preflight 以标记文件 `ok=true` 为准，**Linux 一律后台化启动**（首次下载 Chromium 慢网 5~10 分钟）。轮询上限与心跳/卡死换源判定见 [work-preparation-linux.md#preflight-后台化与轮询linux](references/work-preparation-linux.md#preflight-后台化与轮询linux)。

**封面一键生成（内置：页数判定 + 单/多图概率抽样 + 截图 + 合成 + 校验）**：

```bash
$SKILL_DIR/scripts/build-cover.mjs \
  --url "http://127.0.0.1:8080" --project-dir /path/to/project \
  --title "MyWork" --tagline "一句话简介" --description "主体介绍，1~3 句" \
  --out /tmp/cover.png
```

- **布局决策在脚本内部闭环**（单/多页自动判定 + 布局概率抽样 + 失败页自动跳过，agent 无感知），规则详见 [work-preparation.md](references/work-preparation.md#screenshot-layout-rules-硬性要求)。
- stdout 仅输出一行结果：`#cover=… layout=… multi=yes|no pages=<n> scheme=… tmp=<截图临时目录>`；日志走 stderr。失败 exit 1。
- **截图临时目录 `tmp=<abs>` 保留到整体流程结束**（供 Step 8 409 改名复用原截图，见下），**由 Step 8 发布成功/放弃后统一清理**（`Remove-Item -Recurse -Force <abs>` 或 `rm -rf <abs>`），build-cover 不删。

> **⚠️ workName↔封面强依赖：** 封面标题即 `--title "${workName}"`。**一旦之后因 409 改名，必须用新 workName 重新合成封面**（见 Step 8 改名重推流程），禁止旧封面配新名发布。

> **输出 `coverTmp`**：从 build-cover stdout 的 `tmp=` 提取并作为变量贯穿到 Step 8（409 改名时 `--screenshot ${coverTmp}/shot-index.png`）。

排布规则、视觉基线见 [work-preparation.md#screenshot-layout-rules](references/work-preparation.md#screenshot-layout-rules-硬性要求)。

**Output:** `coverImage`（封面 PNG 绝对路径）。

### Step 5: Introduction

读写 README 生成一句话简介。**总字符数 15~50**，脚本计数通过才继续：
```bash
$SKILL_DIR/scripts/count-cjk.mjs --file "$env:TEMP\intro.txt"   # Win 必须 --file（GBK 转码问题）
```
规则见 [work-preparation.md#introduction-generation](references/work-preparation.md#introduction-generation)。

> **⏩ 并行**：预取活动列表供 Step 7——表行 5/7 命令 + `--query "pageNo=1&pageSize=100&periodYear=${currentYear}"`。

**Output:** `introduction`。

### Step 6: Work Details

生成详解文章（500–1500 字）配图并打包 zip。

1. **图表**：必选系统架构图；可选 0–2 张（路由/依赖/统计图）。用 DevLens/GitNexus 理解项目后出图。禁用 emoji。
   ```bash
   $SKILL_DIR/scripts/generate_diagram.py --html /path/to/project/diagram.html --out /path/to/project/resources/architecture.png --width 1280
   $SKILL_DIR/scripts/verify-glyphs.py /path/to/project/resources/architecture.png --quiet   # 每张含中文图必跑
   ```
2. **打包 zip + 校验一步到位**（`build-detail-zip.mjs` 内置正确目录结构 README.md@根 + resources/，打包后自动跑服务端同源校验，跨平台无需 zip/ZipFile）：
   ```bash
   $SKILL_DIR/scripts/build-detail-zip.mjs --readme /path/to/project/README.md --resources /path/to/project/resources --out /tmp/detail.zip
   ```

**Output:** `detailZip`（详情 zip 绝对路径）。

### Step 7: Select Activity

1. 获取活动列表（Step 5 预取则直接用，`$SKILL_DIR/scripts/api.mjs GET /v1/gallery/camps` 输出 `items` 数组）。
2. 依据 `startsAt`/`endsAt`/`status` 判定投稿状态（[api-spec.md#submission-status-determination](references/api-spec.md#submission-status-determination)）。
3. 分「可投稿」/「不可投稿」两表展示，**每行按当前列表顺序编号**（`<n>. <activity name> — <school>（状态）`），**必须包含 `school`（学校）列**；`school` 为空时显示 `—`。**用户回序号选择活动**（编号对应 `items` 数组下标序），选不可投稿项提示「未开放投稿」。

**Output:** `trainingCampId`。

### Step 8: Publish

1. 宣示 `开始发布作品 ${workName}`。
2. **门禁复核**：`$SKILL_DIR/scripts/check-gates.mjs --cover /tmp/cover.png --detail /tmp/detail.zip --strict --max-age 3600 --quiet`（exit 0 才继续；`publish-work.mjs` 内置 `verifyGates()` 也会拦截）。`publish-work.mjs` 还会在发请求前校验 `envUrl` 可达性（`curl -sf --max-time 10`），隧道不通则 exit 1 并提示检查本地服务。
3. 参数写入 UTF-8 JSON，Idempotency-Key=`gallery-publish-${domainID}-${timestamp}`。**参数 key 见 `publish-work.mjs --help`**（取值对应输出变量：`coverImage`←Step 4、`detailZip`←Step 6、`trainingCampId`←Step 7、`gitUrl`/`gitBranch`←Step 3、`envUrl`←Step 2）。**`domainId` 不作参数（仅拼进 Idempotency-Key）、`credsFile` 不放 JSON（STS 三字段 `accessKeyId`/`secretAccessKey`/`securityToken` 内联）**：
   ```bash
   $SKILL_DIR/scripts/publish-work.mjs /tmp/params.json --max-age 3600
   # 成功仅输出 workId/workName/workUrl/reward；失败原样输出完整响应
   ```
4. **201** → 成功，取 `workId`/`workUrl`/`reward`，**清理临时文件（含 Step 4 的 `coverTmp` 截图目录）**。**积分提示**（无论是否成功都必须提示「每日仅限一次」）：
   - `is_success===true`：`✅ 积分领取请求已提交。⚠️ 每日仅限一次。前往查看余额：https://developer.huaweicloud.com/grow`
   - `is_success===false`：`积分领取未成功：<error_msg>` + 每日限一次提示 + 成长中心地址 + 反馈入口 `https://gallery.developer.huaweicloud.com/gallery/profile?tab=feedback`。
5. **409 DUPLICATE** → 停止当前发布。给选项：① 放弃 ② 改名重发。**若改名重发，必须联动：**
   1. 新名 `workName'`（<30 字符）：用户自定，或在不带版本的常规名基础上加序号（如 `扫雷`→`扫雷-2`）。禁止随意拼接无关字符。
   2. **封面重生成**（封面标题须与新名一致）：**复用 Step 4 保留的原截图（`${coverTmp}/shot-index.png`）** + 原 tagline/description，仅换 `--title "<workName'>"` 重跑 `build-cover.mjs`（一键覆盖截图+合成+校验，且退出后不再处理 tmp）：
      ```bash
      $SKILL_DIR/scripts/build-cover.mjs --url http://127.0.0.1:8080 --project-dir /path/to/project \
        --screenshot ${coverTmp}/shot-index.png --title "NewName" \
        --tagline "原tagline" --description "原description" --out /tmp/cover-new.png
      $SKILL_DIR/scripts/verify-glyphs.py /tmp/cover-new.png --quiet   # exit 0 才可继续
      ```
      若 `coverTmp` 已被清理/不存在，重跑 `build-cover.mjs` 不带 `--screenshot`（会重新截图，需本地服务仍存活）。
   3. **门禁复核（封面已更新，须重跑）**：`$SKILL_DIR/scripts/check-gates.mjs --cover /tmp/cover-new.png --detail /tmp/detail.zip --strict --max-age 3600 --quiet`。
   4. 用**新** `workName'` + **新**封面、新 Idempotency-Key 重新发布（回到第 3 步）。最终成功/放弃后同样清理各 `coverTmp`。
   注意：详情 zip 通常无需重做；仅当 zip 内 README 的标题或正文写了**旧作品名**（与新名不一致）时，才需要把旧名改为新名并重新打包详情 zip。
6. **其他错误** → 告知 `<msg>（<code>）`，保留临时文件，问是否修改重发。错误码见 [error-codes.md](references/error-codes.md)。

---

## References

| Document | 用途 | 何时读 |
|----------|------|--------|
| [troubleshooting.md](references/troubleshooting.md) | 网络/各步骤失败排查 | 脚本报错→先查这里 |
| [error-codes.md](references/error-codes.md) | 平台 API 全错误码表 | API 返回非 2xx 时查表 |
| [api-spec.md](references/api-spec.md) | API 契约、投稿状态判定 | Step 7/8 解析响应 |
| [work-preparation.md](references/work-preparation.md) | 命名/封面/简介/详情/图表统一规则 | Step 3–6 需细节时按目录跳转 |
| [work-preparation-windows.md](references/work-preparation-windows.md) | Windows 专属：PowerShell 预检/字体/zip | **仅 Windows** |
| [work-preparation-linux.md](references/work-preparation-linux.md) | Linux 专属：bash 预检/yum/fontconfig | **仅 Linux** |
| [windows-setup.md](references/windows-setup.md) | Windows 首次准备：编码/Playwright/zip | Windows 环境首次 |
| [self-verify-publish.md](references/self-verify-publish.md) | 自委托 SELF_VERIFY 与 STS 原理 | Step 1 出问题时 |
| [iam-policies.md](references/iam-policies.md) | 最小权限 IAM 策略（Domain 查询 + SELF_VERIFY 自委托） | Step 1 配置 AK/SK 权限时 |
| [devbridge-tunnel.md](references/devbridge-tunnel.md) | DevBridge 隧道：Linux 走内置 `huawei-cloud-devbridge-tunnel` skill / Windows 弃用 | Step 2 隧道（Linux/Windows） |
| [codearts-sandbox.md](references/codearts-sandbox.md) | CodeArts 沙箱目录 | Step 1 命中沙箱 |
