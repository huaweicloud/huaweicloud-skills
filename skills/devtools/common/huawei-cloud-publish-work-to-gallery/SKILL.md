---
name: huawei-cloud-publish-work-to-gallery
description: |
  Publish user's work to the Huawei Cloud University Operations Platform (华为云高校运营平台/作品陈列馆).
  Use this skill whenever the user wants to publish, submit, or upload a project/work to the gallery or a training camp
  (训练营) on the platform — including casual phrasings like "把作品发布上去", "投稿到陈列馆", "传作品到平台", "提交作品/项目", "报名发布作品",
  as well as formal ones like "publish to work gallery", "submit to training camp", "upload work to the platform".
  Do NOT use for general dev questions, git push to GitCode alone, or platform browsing without publishing intent.
metadata:
  tags: huawei-cloud,publish,gallery,university operations platform
---

# Publish Work to Gallery

发布作品至华为云高校运营平台。**确定性子任务优先调用内置脚本**（单入口、fail-fast、自带 `--help`），stdout/退出码即判定依据。脚本报错才查 [references/troubleshooting.md](references/troubleshooting.md)。

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

**并行（Step 2 完成后）**：Step 3/4/5/6 **互不依赖，四者全并行**（取最长路径 Step 4 ~90s，而非串行 ~160s）。Step 4 内 `preflight` + `ensure-utf8` 再并行。

**变量贯穿**：`port`/`workName`/`envUrl` 在最早步骤确定后作为变量传递全流程，禁止硬编码（隧道 URL 含 port，换端口时 envUrl 随之变）。

**执行模型**：① **脚本契约优先**——按 stdout 成功信号判定，**成功路径零源码读取**；失败才 `脚本提示 → troubleshooting 对应节 → grep 脚本源码` 逐级查 ② 禁止手工绕过门禁（`publish-work.mjs` 内置 `verifyGates()` 复核）③ 网络超时统一 3s ④ `detect-env.mjs` 确定平台后只读对应平台 reference（按目录跳转，不全读）⑤ **合并无依赖的 bash 调用**：用 `;` 串联进一条命令，减少工具往返（每次 ~1-2s）。

## 脚本契约速查

| 步骤 | 脚本/命令 | 成功信号（exit 0 且） | 失败（exit 1；2=参数错） |
|------|-----------|----------------------|-----------------------------------|
| 前置 | `api.mjs GET /v1/gallery/announcements/current --prefix open-api-guest` | stdout 首行 `#status=200` | 超时/拒连 → 提示排查网络 |
| 前置 | `node <skill>/scripts/check-version.mjs`（自动读自身 version + 请求远端版本，内部解析，stdout 仅状态行） | exit 0 且首行 `status=ok`/`status=skip` | exit 1（首行 `status=outdated` + 平台下发升级文案）→ 原样提示用户升级，停止发布 |
| 5/7 | `api.mjs GET "/v1/gallery/camps" --creds-file <json> --fields "id,name,school,status,startsAt,endsAt"` | `#status=200`（`--fields` 投影减 token） | 401 → 刷新 STS |
| 1 | `scan-projects.mjs` | stdout `#project <n> <path> <type>` | exit 1=无候选 |
| 1 | `resolve-domain.mjs [--hcloud <exe>]` | stdout `#domain=<id> name=<name>` | exit 1=hcloud 失败（stderr 含排查指引） |
| 1 | `gen_sts.py --account <id>` | 写 `sts-creds.json`（含 `_refresh`）+`sts-creds.sh` | 见 [troubleshooting#domain-id-resolution-issues] |
| 3 | `strip-git-credential.mjs "<rawUrl>"` | stdout=安全 URL（https:// 开头、.git 结尾、无 `@`） | `@`/非 https/非 .git → 停止发布 |
| 3 | `ensure-gitcode-credential.mjs` | `#credential=found` 或 `#credential=missing`（exit 0） | exit 1=Windows 无凭证且 skill 未装（stderr 含安装命令） |
| 3 | `extract-workname.mjs <workDir>` | stdout `#name=<name> source=<来源>` | exit 1=workDir 不存在 |
| 4 | `preflight.sh` / `preflight.ps1` | 写 `font-gate-ok`（`ok=true gate=preflight`） | 截图/封面/图表**禁止** |
| 4 | `ensure-utf8.mjs <dir>` | 写 `utf8-gate-ok` | 编码非 UTF-8 → 禁止截图 |
| 4 | `build-cover.mjs --url … --project-dir … --title … --out …` | stdout 一行 `#cover=… layout=… multi=…` | exit 1 → 截图/校验/合成任一失败，stderr 详情 |
| 4 | `screenshot_guard.py http://… --out <png> --quiet` | 写 `screenshot-gate-ok` + 出 PNG | 字形/字符集不过 → 修字体重试 |
| 4 | `generate_cover.py --screenshot … --title … --out …` | 封面 PNG，再过 `verify-glyphs.py` | exit 1 → 禁止继续合成 |
| 4/6 | `verify-glyphs.py <img> --quiet` | exit 0（stdout 仅 1 行省 token） | exit 1 → 疑似豆腐块 → 修字体 |
| 5 | `count-cjk.mjs --file <utf8.txt>` | 总字符数 15~50 | exit 1 → 改写简介再计 |
| 6 | `generate_diagram.py --html … --out …` | 图表 PNG，再过 `verify-glyphs.py --quiet` | 同封面 |
| 6 | `build-detail-zip.mjs --readme <md> --resources <dir> --out <zip>` | 打包+校验一步完成 | exit 1 → 按输出修复重打 |
| 8 | `check-gates.mjs --cover <png> --detail <zip> --strict --max-age 3600 --quiet` | exit 0（stdout 仅 1 行省 token） | exit 1 → 回退重跑门禁 |
| 8 | `publish-work.mjs <utf8-params.json>` | `#status=201`（仅输出 workId/workUrl/reward） | 409/其他；失败时原样输出完整响应 |

> 标记文件位置：Linux `/tmp/`；Windows `os.tmpdir()`（`%TEMP%`）。

## 前置锁定

- **hcloud + AK/SK**：Step 1 需要。未装/未配置 → [troubleshooting#domain-id-resolution-issues](references/troubleshooting.md#domain-id-resolution-issues)。
- **git**：Step 3；**zip**：Step 6（Linux `yum install zip`；Windows 用 .NET `ZipFile`）。Windows 首次见 [windows-setup.md](references/windows-setup.md)。
- **连通性**：`api.mjs GET "/v1/gallery/announcements/current" --prefix open-api-guest`，连通 OK 即可继续。
- **版本检查（尽力而为）**：`node <skill>/scripts/check-version.mjs`——脚本自动读本文件 frontmatter `version:` 并请求平台版本接口比较。`status=ok`/`status=skip`（非 2xx/解析失败）→ 继续，不阻塞；`status=outdated` → 将脚本输出的升级文案**原样**告知用户并**停止发布**（连同行公告接口一起两条命令可并行/串联合并执行，减少工具往返）。

---

## Core Workflow

### Step 1: Select Work Directory & Resolve IAM Domain Info

1. **告知用户**（选目录=同意）：将创建 IAM 自委托 `SELF_VERIFY` 生成 STS 临时凭证（900s），永久 AK/SK 留本地不上传。
2. **扫描项目根**：`node <skill>/scripts/scan-projects.mjs`——自动递归 `**/README.md`，检查指示文件，排除 `skills/`/`node_modules/`/`dist/` 等，扫描 CodeArts 沙箱目录。stdout 每行 `#project <n> <path> <type>`。
3. 列候选，等用户选 → `workDir`。
4. **解析 Domain ID**：`node <skill>/scripts/resolve-domain.mjs [--hcloud <exe>]`——自动 `hcloud configure set --region` + `IAM KeystoneListAuthDomains` + 提取 `domain_id`。stdout `#domain=<id> name=<name>`。hcloud 不在 PATH 时传 `--hcloud`。凭证优先级：env → hcloud 已配置 → 引导用户（[troubleshooting#2](references/troubleshooting.md#2-hcloud-credentials-not-configured)）。
5. **生成 STS**：`python <skill>/scripts/gen_sts.py --account <domainID>` → `sts-creds.json`（含 `_refresh`，使 401 自动刷新）。
6. **输出**：`已获取 IAM Domain ID: <id>，用于将作品关联至您的华为云账号。`

**Output:** `workDir`、`domainID`、`credsFile`。

### Step 2: Run Project & Open Tunnel

询问是否运行项目+开隧道。拒绝则 `envUrl=""` → Step 3。

- **端口清理**：`netstat -ano | findstr :<port>`（Win），残留进程 kill。
- **启动**：优先入口脚本（`npm run dev`/`python main.py`）；纯前端 `npx http-server . -p <port>`。≤30s 健康检查。
- **核对内容**：`curl -sf --max-time 3 http://localhost:<port>` 首 100 字符须匹配本项目（`<title>`/项目名），`Index of /`/404 → 清进程重启。
- **隧道**：`devbridge host -p <port> -e 2`，`curl -sf --max-time 10` 验证。失败不阻塞，置 `envUrl=""`。详见 [devbridge-tunnel.md](references/devbridge-tunnel.md)。

**Output:** `port`、`envUrl`（或 `""`）。

### Step 3: Git Repository Info & Work Name

`gitUrl` 必填，`gitBranch` 必须显式读取。`workName` 从 README 解析/合成（<30 字符）。

1. `git -C <workDir> remote get-url origin` + `branch --show-current`。
2. **凭证排查**：`node <skill>/scripts/ensure-gitcode-credential.mjs`——自动检测本机 GitCode 凭证（`git credential fill`/`~/.git-credentials`/`$GITCODE_TOKEN`/`cmdkey`），无凭证时按平台给可行路径（Linux 提示手动配置 / Windows 检测 `gitcode-oauth` skill 并输出安装命令）。exit 0=有凭证或已有路径；exit 1=Windows 无凭证且 skill 未装（stderr 含安装命令 + Windows Git Bash 兼容提示）。
3. **凭证剥离**：`gitUrl="$(node <skill>/scripts/strip-git-credential.mjs "$(git remote get-url origin)")"`。硬校验：无 `@`、`https://` 开头、`.git` 结尾。
4. **命名**：`node <skill>/scripts/extract-workname.mjs <workDir>`——按优先级 frontmatter → H1 → manifest → `index.html <title>` → 目录名提取。stdout `#name=<name> source=<来源>`。`source=dirname` 时 agent 可合成/修改（<30 字符）。

**Output:** `gitUrl`、`gitBranch`、`workName`。

### Step 4: Cover Image

**门禁（并行）**：

| 门禁 | 命令 | 标记 |
|------|------|------|
| 渲染 | `preflight.sh`（Win: `preflight.ps1`） | `font-gate-ok` |
| 编码 | `ensure-utf8.mjs <dir>` | `utf8-gate-ok` |

门禁失败禁止截图/合成。preflight 以标记文件 `ok=true` 为准（轮询 ≤180s）。**Linux 首次运行必须后台化**（下载 Chromium ~111MB，前台会被 shell 超时 SIGPIPE 杀死，主进程死后不会写 gate 文件，轮询徒劳）；Windows 通常已预装系统浏览器，前台即可。

**封面一键生成（内置：页数判定 + 单/多图概率抽样 + 截图 + 合成 + 校验）**：

```bash
node <skill>/scripts/build-cover.mjs \
  --url "http://127.0.0.1:<port>" --project-dir <workDir> \
  --title "<workName>" --tagline "<一句话>" --description "<主体介绍，1~3 句>" \
  --out <coverImagePath>
```

- **布局决策在脚本内部闭环**（agent 无感知）：单页项目只用 7 个单图布局；多页项目（`.html` 数 ≥2）额外加入 3 个多图布局（大图+小图拼贴），统一概率池等概率抽样，多页时多图出现概率 3/10。
- 多图布局会截**首页 + 候选页**（最多 3 张小图）；候选页截图失败自动跳过，最少保底 1 张。
- stdout 仅输出一行结果：`#cover=… layout=… multi=yes|no pages=<n> scheme=…`；日志走 stderr。失败 exit 1。

> **⚠️ workName↔封面强依赖：** 封面标题即 `--title "${workName}"`。**一旦之后因 409 改名，必须用新 workName 重新合成封面**（见 Step 8 改名重推流程），禁止旧封面配新名发布。

排布规则、视觉基线见 [work-preparation.md#screenshot-layout-rules](references/work-preparation.md#screenshot-layout-rules-硬性要求)。

**Output:** `coverImagePath`。

### Step 5: Introduction

读写 README 生成一句话简介。**总字符数 15~50**，脚本计数通过才继续：
```bash
node <skill>/scripts/count-cjk.mjs --file "$env:TEMP\intro.txt"   # Win 必须 --file（GBK 转码问题）
```
规则见 [work-preparation.md#introduction-generation](references/work-preparation.md#introduction-generation)。

> **⏩ 并行**：`api.mjs GET "/v1/gallery/camps" --query "pageNo=1&pageSize=100&periodYear=${currentYear}" --creds-file "${credsFile}" --fields "id,name,school,status,startsAt,endsAt"` 预取供 Step 7。

**Output:** `introduction`。

### Step 6: Work Details

生成详解文章（500–1500 字）配图并打包 zip。

1. **图表**：必选系统架构图；可选 0–2 张（路由/依赖/统计图）。用 DevLens/GitNexus 理解项目后出图。禁用 emoji。
   ```bash
   python <skill>/scripts/generate_diagram.py --html diagram.html --out resources/<name>.png --width 1280
   python3 <skill>/scripts/verify-glyphs.py <img> --quiet   # 每张含中文图必跑
   ```
2. **打包 zip + 校验一步到位**（`build-detail-zip.mjs` 内置正确目录结构 README.md@根 + resources/，打包后自动跑服务端同源校验，跨平台无需 zip/ZipFile）：
   ```bash
   node <skill>/scripts/build-detail-zip.mjs --readme <README.md> --resources <dir> --out <workDetail.zip>
   ```

**Output:** `detailsZipPath`。

### Step 7: Select Training Camp

1. 获取训练营列表（Step 5 预取则直接用）。
2. 依据 `startsAt`/`endsAt`/`status` 判定投稿状态（[api-spec.md#submission-status-determination](references/api-spec.md#submission-status-determination)）。
3. 分「可投稿」/「不可投稿」两表展示，**每行必须包含 `school`（学校）列**；`school` 为空时显示 `—`。选不可投稿项提示「未开放投稿」。

**Output:** `trainingCampId`。

### Step 8: Publish

1. 宣示 `开始发布作品 ${workName}`。
2. **门禁复核**：`node <skill>/scripts/check-gates.mjs --cover <png> --detail <zip> --strict --max-age 3600 --quiet`（exit 0 才继续；`publish-work.mjs` 内置 `verifyGates()` 也会拦截）。
3. 参数写入 UTF-8 JSON，Idempotency-Key=`gallery-publish-${domainID}-${timestamp}`：
   ```bash
   node <skill>/scripts/publish-work.mjs <utf8-params.json> --max-age 3600
   # 成功仅输出 workId/workName/workUrl/reward；失败原样输出完整响应
   ```
4. **201** → 成功，取 `workId`/`workUrl`/`reward`，清理临时文件。**积分提示**（无论是否成功都必须提示「每日仅限一次」）：
   - `is_success===true`：`✅ 积分领取请求已提交。⚠️ 每日仅限一次。前往查看余额：https://developer.huaweicloud.com/grow`
   - `is_success===false`：`积分领取未成功：<error_msg>` + 每日限一次提示 + 成长中心地址 + 反馈入口 `https://gallery.developer.huaweicloud.com/gallery/profile?tab=feedback`。
5. **409 DUPLICATE** → 停止当前发布。给选项：① 放弃 ② 改名重发。**若改名重发，必须联动：**
   1. 新名 `workName'`（<30 字符）：用户自定，或在不带版本的常规名基础上加序号（如 `扫雷`→`扫雷-2`）。禁止随意拼接无关字符。
   2. **封面重生成**（封面标题须与新名一致）：用原截图 + 原 tagline/description，仅换 `--title "<workName'>"` 重新合成：
      ```bash
      python <skill>/scripts/generate_cover.py --screenshot <原截图png> --title "<workName'>" --tagline "<原tagline>" --description "<原description>" --out <coverImagePath-新> --scheme auto
      python3 <skill>/scripts/verify-glyphs.py <coverImagePath-新> --quiet   # exit 0 才可继续
      ```
   3. **门禁复核（封面已更新，须重跑）**：`node <skill>/scripts/check-gates.mjs --cover <封面-新> --detail <zip> --strict --max-age 3600 --quiet`。
   4. 用**新** `workName'` + **新**封面、新 Idempotency-Key 重新发布（回到第 3 步）。
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
| [devbridge-tunnel.md](references/devbridge-tunnel.md) | DevBridge 隧道登录/故障 | Step 2 隧道异常 |
| [codearts-sandbox.md](references/codearts-sandbox.md) | CodeArts 沙箱目录 | Step 1 命中沙箱 |
