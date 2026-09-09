# Work Preparation Guide

Detailed guidance for generating work metadata from the project directory.

**平台分流（重要）：** 先运行 `node <skill>/scripts/detect-env.mjs` 确认环境指纹。Windows 环境的**平台专属命令**（Playwright 预检/字体/截图校验/zip 打包的 PowerShell 实现）见 [work-preparation-windows.md](work-preparation-windows.md)；Linux/EulerOS（HCE）的（bash 实现、yum 包名映射、fontconfig 配置）见 [work-preparation-linux.md](work-preparation-linux.md)。本文件只保留**跨平台统一流程与判定规则**，各平台偏离点以对应平台文件为准。

## Table of Contents

- [Work Directory Detection](#work-directory-detection)
- [Work Name Generation](#work-name-generation)
- [Cover Image Generation](#cover-image-generation)
  - [Strategy Overview](#strategy-overview)
  - [Visual Style Baseline (视觉风格基线)](#visual-style-baseline-视觉风格基线)
  - [Part A — Capture Work Screenshot](#part-a--capture-work-screenshot)
    - [Option 1: Screenshot the running app](#option-1-screenshot-the-running-app)
    - [Option 2: Local Playwright with Mock Data](#option-2-local-playwright-with-mock-data)
    - [Option 3: No Frontend](#option-3-no-frontend)
    - [Screenshot Validation (硬性要求，截图后必须执行)](#screenshot-validation-硬性要求截图后必须执行)
  - [CSS Font Requirements Analysis & Fallback Injection](#css-font-requirements-analysis--fallback-injection)
  - [Part B — Generate PPT-Style Cover](#part-b--generate-ppt-style-cover)
    - [Screenshot Layout Rules (硬性要求)](#screenshot-layout-rules-硬性要求)
    - [Design Requirements](#design-requirements)
- [Introduction Generation](#introduction-generation)
- [Details Article & Diagram Generation](#details-article--diagram-generation)
  - [Article Requirements](#article-requirements)
  - [Diagram Requirements](#diagram-requirements)
    - [Required — Image 1: System Architecture Diagram](#required--image-1-system-architecture-diagram)
    - [Optional — Image 2–3: AI-Selected Diagrams](#optional--image-23-ai-selected-diagrams)
  - [Diagram Generation Methods](#diagram-generation-methods)
  - [Image Design Requirements](#image-design-requirements)
  - [Article Format](#article-format)
- [Details Package Generation](#details-package-generation)

---

## Work Directory Detection

### Scanning for Project Root Directories

A project root directory is the top-level folder of a software project. The skill scans the current environment for all `README.md` files and filters to keep only those whose parent directory is a genuine project root (not a skill directory or subdirectory).

### Project Root Indicators & Exclusion Rules

项目根指示文件表与排除规则见 SKILL.md Step 1（`package.json`/`pom.xml`/`requirements.txt` 等指示文件，排除 `skills/`/`node_modules/`/`.git/` 等非项目目录）。

### Search Strategy

1. Start from the current working directory.
2. Recursively find all `README.md` files (case-insensitive, also match `readme.md`).
3. For each `README.md`, check if its parent directory contains any project root indicator file.
4. Exclude directories matching the exclusion rules above.
5. Present all qualifying candidates to the user with full absolute paths and detected project type.
6. If no candidates are found, ask the user to specify the work directory path manually.

### Git Info Auto-Detection

After the user selects a work directory, automatically detect git information:

```bash
git -C <workDir> remote get-url origin
git -C <workDir> branch --show-current
```

If the directory is not a git repository, the agent must guide the user to create a repo (e.g. on GitCode) and push the work (Step 3), because `gitUrl` is a required publish field. The final `gitUrl` is the repository clone URL (must end with `.git`, e.g. `https://gitcode.com/user/repo.git`). The branch is passed separately as `gitBranch`. git credential 剥离走 SKILL.md Step 3 的 `strip-git-credential.mjs`（fail-stop）。

---

## Work Name Generation

### Extraction Priority

1. **README frontmatter:** Check for YAML frontmatter with a `name` or `title` field.
2. **README H1 heading:** The first `# Title` line in the README.
3. **package.json / pom.xml / pyproject.toml:** Read the `name` field from the project manifest.
4. **HTML `<title>` / `<h1>`（项目无 README/manifest 时兜底）:** 若以上均无，读 `index.html`（或 `public/index.html`）的 `<title>` 或首个 `<h1>`，取其中作品名（如 `<title>扫雷游戏 · Minesweeper</title>` → `扫雷游戏`），去掉多余分隔与英文副标题。
5. **Directory name:** Use the directory basename as a last resort, converting kebab-case or snake_case to a readable title.

### Name Formatting Rules

- Keep under 30 characters
- Use the project's display name, not the package name (e.g., "智能问答系统" not "smart-qa-system")
- If the name is in English, title-case it (e.g., "Smart QA System")
- If the name is in Chinese, use it as-is

---

## Cover Image Generation

### Strategy Overview

```
Capture work screenshot
├── Option 1: Screenshot the running app (preferred)
│   └── Playwright captures the running app page (local URL, NOT tunnel URL)
├── Option 2: Local Playwright with mock data (fallback)
│   ├── Start local HTTP server
│   ├── Mock all backend API calls (no undefined, no empty arrays)
│   └── Capture screenshot via Playwright
└── Option 3: No frontend → generate representative image

Generate PPT-style cover
├── Use playwright / codex-slides / ppt-mcp-server
├── Include work screenshot in a presentation slide
├── Add work name + tagline
├── Apply tech-oriented color tone
└── Convert to PNG image
```

### Visual Style Baseline (视觉风格基线)

生成封面与架构图前**先确定视觉基线**：封面、架构图、文章内截图均在此范围内生成，风格不得差距过大（如封面黑金暗调、架构图纯白亮调）。**基线主色调优先取自应用页面实际主导色**（封面内嵌真实截图，外壳配色贴近页面风格可显著提升一致性），全流程共用同一 scheme，其余维度同语言适度变化。

**基线主色调判定优先级链：**
1. **页面主导色**（首选）：读项目 CSS 主题配置/`:root` 变量（如 `--primary`、`--bg-color` 等 hex）或应用首页截图主色，取主导色 hex，映射到下方 8 个 scheme 中**视觉最接近**者（如 `#0f172a`→`blue`/`dark`、`#f97316`→`vibrant-orange`）。**近似匹配即可，无需精确相等。**
2. **适用项目类别**：无明确页面色（如主题色分散/后端组件型）时，按下表「适用项目」列选择对应 scheme。
3. **降级 auto**：两者均无法确认时，依赖 `--scheme auto` 按标题哈希选色（保证各作品封面不同色调）。

**封面色板唯一来源 — 以 `generate_cover.py --scheme` 为准：**

| scheme | 主色系 | 主色 hex（图表/mpl 参考） | 适用项目 |
| --- | --- | --- | --- |
| `purple` | 深紫蓝渐变 | `#302b63` / 强调 `#a5b4fc` | AI/ML、创意、生成式 |
| `blue` | 深蓝渐变 | `#1a3a5c` / 强调 `#93c5fd` | 基础设施、安全、DevOps、企业系统 |
| `green` | 深青绿渐变 | `#1a3a2e` / 强调 `#86efac` | 数据分析、监控、可视化、环保金融 |
| `dark` | 黑灰渐变 | `#1a1a1a` / 强调 `#d1d5db` | 极简、工具、后端/API |
| `warm` | 暖棕橙渐变 | `#3a2018` / 强调 `#fdba74` | 社交、社区、内容平台 |
| `black-gold` | 黑金渐变 | `#1c1a14` / 强调 `#f0cf6d` | 金融、会员、高端展示 |
| `vibrant-orange` | 亮橙渐变 | `#7a3410` / 强调 `#fdba74` | 游戏、电商、生活消费 |
| `warm-yellow` | 温馨黄渐变 | `#573e0a` / 强调 `#fcd34d` | 教育、亲子、生活服务 |

- **封面合成一律用脚本渲染**：`python <skill>/scripts/generate_cover.py --scheme <auto|purple|blue|green|dark|warm|black-gold|vibrant-orange|warm-yellow> …`（脚本内置每色完整背景/glow/网格/徽章 hex）。**Step 4 务必按上面优先级链显式传 `--scheme`（优先页面主导色映射），不要默认依赖 `auto`**；`auto` 仅作兜底（按标题哈希选色，避免不同作品封面清一色同一色调）。Step 4 与 Step 6 须用同一 scheme（取 `auto` 时由脚本确定后回读输出中的 `scheme=`），不得偏差太远。
- **图表跟随同一 scheme**：手写 HTML/CSS 图表用上表主色 hex 即可；matplotlib/Graphviz 需要背景/文字等精确色值时，用上表主色与强调色自行派生（`python generate_cover.py --help` 可看脚本支持的 scheme 列表，**不要打开脚本源码**）。Step 4 与 Step 6 共用同一 scheme，不得偏差太远；其余维度（背景样式/节点卡/渲染效果）可适度变化。

### Part A — Capture Work Screenshot

**⚠️⚠️ 硬性要求 — 必须截图：** 作品封面**必须基于真实应用截图**生成。Option 1（截取运行中的应用）和 Option 2（mock 数据 + 本地 Playwright 截图）是**默认预期路径**，agent 必须主动尝试。Option 3（无前端模式）仅在项目确实无前端且 Option 1/2 均失败后才可使用——**绝不能因 Playwright 安装慢或依赖安装失败就跳过截图**。EulerOS/HCE 上 `playwright install-deps` 不生效是已知问题，按 [work-preparation-linux.md](work-preparation-linux.md) 映射表手动安装系统依赖后重试即可。

> **平台分流：** Playwright/Chromium 安装前**预检脚本**（判断已装则跳过）：Windows → [work-preparation-windows.md#playwrightchromium-安装前预检powershell](work-preparation-windows.md#playwrightchromium-安装前预检powershell)；Linux/macOS → [work-preparation-linux.md#playwrightchromium-安装前预检bash](work-preparation-linux.md#playwrightchromium-安装前预检bash)。**预检逻辑（全平台同）：** 三项全 true → 跳过所有安装直接截图；Playwright 包 false → 仅 `pip install playwright`；Chromium 二进制 false → `python -m playwright install chromium`（~300MB）；包+二进制就绪但启动 false → Linux 装系统依赖（Windows 无需）。字体预检统一走 `preflight.sh`/`preflight.ps1`（SKILL.md Step 4 门禁），不依赖内联脚本。

#### Option 1: Screenshot the running app

Use Playwright to capture a screenshot of the running app at its **local URL** (`http://127.0.0.1:<port>`，即 Step 2 记录的本地端口):

> **字体/口口保障用 SKILL.md Step 4 的守卫脚本 `screenshot_guard.py`**（含 chromium.launch --no-sandbox、字形自检、`@font-face local()` 兜底注入、写 `/tmp/screenshot-gate-ok`），而非只做基础截图。

> **⚠️ 禁止用隧道 URL 截图：** DevBridge 隧道页面会先弹出**授权页面**，直接截图会截到授权页而非应用界面。**始终用本地地址 `http://127.0.0.1:<port>` 截图。** 隧道 URL 仅用于发布时的 `envUrl` 字段，不用于截图。

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    # ⚠️ 用 domcontentloaded 而非 networkidle/load——后者在慢速页面/隧道下易超时
    page.goto(APP_URL, wait_until="domcontentloaded", timeout=30000)
    page.evaluate("() => document.fonts.ready")
    page.wait_for_timeout(2000)  # 等待动态内容渲染
    page.screenshot(path="/tmp/work-screenshot.png", full_page=False)
    # Windows 上改为: os.path.join(os.environ["TEMP"], "work-screenshot.png")
    browser.close()
```

> **⚠️ 页面加载超时处理：** 默认 `wait_until: "load"` 或 `"networkidle"` 在慢速页面、Flask debug 模式或 DevBridge 隧道下容易超时（`Timeout 15000ms exceeded`）。**始终使用 `wait_until: "domcontentloaded"` + `timeout: 30000`**，再辅以 `wait_for_timeout(2000)` 等待动态内容渲染后截图。

**Chinese & emoji font handling：** Step 4（截图/封面合成）和 Step 6（图表生成）均需 CJK + emoji 字体。字体预装情况与安装命令按平台查：Windows → [work-preparation-windows.md#windows-字体预检powershell](work-preparation-windows.md#windows-字体预检powershell)；Linux → [work-preparation-linux.md#字体安装速查表aptyum-列](work-preparation-linux.md#字体安装速查表aptyum-列)。

> **依赖预检一致性：** `preflight.sh`/`preflight.ps1`（SKILL.md Step 4 门禁脚本）已统一处理字体+fontconfig+图表依赖，通过写 `/tmp/font-gate-ok`。此处内联预检仅用于"判断是否可跳过安装"，门禁判定以 `preflight` 标记为准。

#### Option 2: Local Playwright with Mock Data

If the running app is not accessible or the work has no frontend to open, serve the local frontend files via a local HTTP server and mock all backend API calls.

> **⚠️ 后台启动 HTTP 服务的陷阱：** 用 `python3 -m http.server <port> &` 裸 `&` 启动时，shell 工具命令返回后**后台进程会被回收**，后续 `curl`/截图请求报 `ERR_CONNECTION_REFUSED`。**必须用 `nohup` 持久化**：
> ```bash
> nohup python3 -m http.server 8099 > /tmp/httpserver.log 2>&1 &
> # 截图完成后: kill %1 或 pkill -f "http.server 8099"
> ```
> 若用下方「Reusable mock server + screenshot script」（进程内 Node http server + 同进程截图 + `server.close()`），则无此问题——它不是后台进程，截图完即随脚本退出。

**1. Install Playwright（先运行预检脚本，已安装则跳过）：** 预检与依赖装法按平台：Windows → [work-preparation-windows.md#playwrightchromium-安装前预检powershell](work-preparation-windows.md#playwrightchromium-安装前预检powershell)；Linux/macOS → [work-preparation-linux.md#playwrightchromium-安装前预检bash](work-preparation-linux.md#playwrightchromium-安装前预检bash)。**EulerOS/HCE 必须手动按映射表装系统依赖**（[work-preparation-linux.md#chromium-系统依赖包名映射euleroshce-vs-ubuntu](work-preparation-linux.md#chromium-系统依赖包名映射euleroshce-vs-ubuntu)），Windows 无需。

**2. Mock all backend API calls** — the frontend likely calls `/api/*` endpoints that don't exist locally. Intercept these in the HTTP server and return complete, realistic JSON mock data. **Mock 数据铁律与完整脚本模板见 [mock-server-template.md](mock-server-template.md)**（仅 Option 2 场景读取）。

**3. Reusable mock server + screenshot script：** 完整模板见 [mock-server-template.md](mock-server-template.md)。或直接用 `screenshot_guard.py`（已含字形自检 + 兜底注入，Python 包经 `pip install` 全局可用，无 `ERR_MODULE_NOT_FOUND` 目录限制）。

#### Option 3: No Frontend

If the work has no frontend (pure backend, CLI, library, etc.):

- Analyze the README content and project style to generate a representative image.
- As a fallback, create a simple branded cover with the work name on a neutral background.

#### Screenshot Validation (硬性要求，截图后必须执行)

截图生成后，**必须检查图片格式与大小**。无法访问或过小则视为无效图片，不得用于封面合成。

**校验项（标准跨平台）：**

| 校验项 | 判定标准 | 不通过则 |
| ------ | --------- | -------- |
| 文件可访问性 | 文件存在且可读 | 视为无效图片 |
| 图片格式 | MIME 为 `image/png`、`image/jpeg`、`image/webp` 或 `image/gif` | 视为无效图片 |
| 文件大小 | ≥ 10KB（小于 10KB 可能是空白/损坏图片） | 视为无效图片 |
| 图片宽高 | 宽 ≥ 200px 且 高 ≥ 200px（需 identify，可选） | 视为无效图片 |

**校验脚本实现按平台：** Windows（PowerShell，读文件头判格式）→ [work-preparation-windows.md#截图有效性校验powershell](work-preparation-windows.md#截图有效性校验powershell)；Linux/macOS（bash，`file` + `stat`）→ [work-preparation-linux.md#截图有效性校验bash](work-preparation-linux.md#截图有效性校验bash)。

**无效图片处理流程：**

1. 不要将无效截图用于封面合成。
2. 按优先级回退：当前 Option 失败则尝试下一 Option（Option 1 → Option 2 → Option 3）。
3. 若所有 Option 均无法产生有效截图，使用 Option 3（无前端模式）从 README 内容生成代表性图片作为兜底，并在封面中省略截图区域。
4. 校验通过的有效截图方可进入 Part B 封面合成。

### CSS Font Requirements Analysis & Fallback Injection

**（CSS 字体需求分析与兜底注入）**

**为什么需要（不只是装字体）：** 仅装 Noto CJK **不代表 CSS 声明的字体可用**。作品 CSS 常声明 Windows/macOS/Google Fonts 字体（如 `"Inter"`、`"Outfit"`、`"Microsoft YaHei"`、`"PingFang SC"`、`"Segoe UI"`、`Consolas` 等），这些字体在 Linux 裸机上不存在且 fontconfig 隐式兜底不可靠。**必须主动分析 CSS 字体需求并显式重映射缺失族，不依赖隐式回退。** 平台专属的兜底不可靠原因（EulerOS `.ttc`）与 fontconfig 配置见 [work-preparation-linux.md#fontconfig-中文回退配置](work-preparation-linux.md#fontconfig-中文回退配置)。

流程三步：**① 提取 CSS 字体需求 → ② 归类并补齐兜底字体套件 → ③ Playwright 页面内字形自检 + `@font-face local()` 兜底注入**。这是截图/封面合成前"不出现口口"的主防线。

#### ① 提取 CSS 字体需求

用 Node.js 脚本扫描 workDir 所有前端源文件，提取 `font-family`、`@font-face`、`@import` 中的字体族名并去重（**Node 跨平台，Linux/Windows 通用**）：

```bash
# 提取字体需求（跨平台）：输出每行一个字体族名，供 screenshot_guard 的 --required 使用
node <skill>/scripts/extract-fonts.mjs <workDir>
```

> **⚠️ 变量展开：** 提取结果中若出现 `var(--font-body)`、`var(--font-display)` 等 **CSS 自定义属性引用**，需回查 `:root` 中的变量定义，把变量**展开为字面字体列表**后再归类（如 `--font-body: "Inter", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif`）。**通用关键字（`sans-serif`、`serif`、`monospace`、`ui-monospace`、`system-ui`、`-apple-system`）不注入、只用于归类判断。**

#### ② 归类并补齐兜底字体套件

把提取结果按类别归并，**每类至少保证一个兜底字体存在**：

| 类别 | CSS 常见字体名示例 | 兜底字体（Linux） | 兜底字体（Windows） |
| --- | --- | --- | --- |
| CJK 无衬线 | Microsoft YaHei、微软雅黑、PingFang SC、苹方、Hiragino Sans GB、STHeiti、SimHei、黑体、Source Han Sans、Noto Sans CJK SC | Noto Sans CJK SC | Microsoft YaHei |
| CJK 衬线 | SimSun、宋体、NSimSun、Source Han Serif、Noto Serif CJK SC、serif | Noto Serif CJK SC | SimSun |
| 拉丁 UI | Inter、Outfit、Roboto、Arial、Helvetica、Segoe UI、Open Sans、sans-serif | Noto Sans CJK SC | Microsoft YaHei |
| 等宽 | SFMono-Regular、Cascadia Mono、Roboto Mono、Consolas、Menlo、Courier New、monospace | DejaVu Sans Mono | Consolas |
| 衬线 | Times New Roman、Georgia | DejaVu Serif | Times New Roman |
| Emoji | Segoe UI Emoji、Apple Color Emoji、Noto Color Emoji | Noto Color Emoji | Segoe UI Emoji |

**兜底字体套件安装（预检发现某类别缺失时按需补齐）：** CJK + emoji 的安装即 `preflight.sh`/`preflight.ps1`（缺失时自动装 `google-noto-cjk-fonts`；emoji 优先从 jsDelivr CDN 下载彩色版 `NotoColorEmoji.ttf`，yum 版过旧作回退）。拉丁/衬线/等宽兜底与 fontconfig 配置：Linux → [work-preparation-linux.md#fontconfig-中文回退配置](work-preparation-linux.md#fontconfig-中文回退配置)；Windows 默认已含 Microsoft YaHei / Segoe UI Emoji / Consolas，通常无需操作。

> **等宽字体的 CJK 覆盖（Linux）：** 等宽兜底 `DejaVu Sans Mono` **不含中文字形**。若截图中的代码/终端文本含中文字符，需把等宽族兜底换成 `Noto Sans Mono CJK SC`，否则代码里的中文仍会口口。

> **⚠️ 时序（硬性要求）：** 字体必须**先安装完成、`fc-cache -f` 之后再 `launch()` Chromium**。**已运行的浏览器进程不会识别新装的字体**——同一会话中若先启动过浏览器又装了字体，必须关闭浏览器重新启动。

> **⚠️ 兜底字体必须"中文 + 拉丁"都能渲染（曾配 `Droid Sans Fallback`，有 CJK 无拉丁 → 英文变方框）。** `@font-face { src: local(X) }` 只会命中**一个**本地字体。**优先用同时含中文字形与拉丁字母的字体兜底**（`Noto Sans CJK SC` / `Source Han Sans SC` 自带拉丁；`Droid Sans Fallback` 仅中文、`DejaVu Sans` 仅拉丁——**两者都不能单独承担"要显示中英混排"的兜底**）：
> ```bash
> fc-match "Noto Sans CJK SC:lang=zh"   # 应返回含 CJK 的字体，而不是 DejaVuSans.ttf
> fc-match "Noto Sans CJK SC:lang=en"   # 拉丁也应可渲染（Noto Sans CJK 自带，OK）
> ```

#### ②-加：fontconfig 中文回退配置（Linux 专属）

仅 Ubuntu/Debian/Red Hat 类的`fc-match` 判定为非 CJK 时才需要。**实现见 [work-preparation-linux.md#fontconfig-中文回退配置](work-preparation-linux.md#fontconfig-中文回退配置)**（优先写用户级 `~/.config/fontconfig/conf.d/99-cjk-fallback.conf`，无 root 时无需 sudo；`fc-cache -f` 后复校验，`binding="strong"` 覆盖三族）。核心校验：

```bash
fc-match --format='%file' 'sans-serif:lang=zh'   # 不得命中 DejaVuSans.ttf
```

> **上游产物门禁：** 环境级一键门禁 = 运行 `preflight.sh`/`preflight.ps1`（跨平台，SKILL.md Step 4）→ 写 `/tmp/font-gate-ok`（`ok=true\ngate=preflight`）；页面级守卫 `screenshot_guard.py` 通过后写 `/tmp/screenshot-gate-ok`（`ok=true\ngate=screenshot-guard`）。发布前 `check-gates.mjs` 统一复核全部门禁标记 + 产物文件（SKILL.md Step 8）。

#### ③ Playwright 页面内字形自检 + `@font-face` 兜底注入（截图前必做）

截图前在页面内对每个提取到的字体族做字形自检，缺失的族用 `@font-face { src: local(兜底字体) }` **原地重映射**。该方式只替换目标族名，**不破坏图标字体**（Font Awesome / Element Plus 图标等 `@font-face` 族名不在自检列表内，不会被覆盖）。注入后必须复检：

```bash
# 截图前字形自检 + 兜底注入（核心防线，跨平台）：--required 可用 extract-fonts 输出文件或逗号列表；--fallback 覆盖默认映射
python <skill>/scripts/screenshot_guard.py <appUrl> [--required-file <font-list.txt>] [--required "Outfit,Inter"] [--out <png>]
```

> **说明：** 自检规则是"中文样例落在该族上才算可用"——因此即使某族已安装但缺 CJK 字形（如 DejaVu Sans），也会被重映射到 CJK 兜底字体。代价是拉丁文字形统一使用兜底字体（现代无衬线风格，视觉可接受），换来"绝不出现口口"的确定性。**emoji 属系统兜底、走独立自检，与字体族注入无关。**

> **⚠️ 两个实测限制：** (a) **测宽法对 CJK 不可靠**——CJK 真实字形与 tofu 的 advance width 都是 1em，测宽只能判断"某族是否缺失/回退"，**不能确认 CJK 字形真的渲染了**；故以「像素对比」为最终核验。(b) **`@font-face { src: local(兜底) }` 在 headless Chromium 可能不解析**——重映射**优先直接在 CSS 里写系统已注册字体名**（如 `Noto Sans CJK SC`），确需 local() 时注入后用像素核验确认，不生效则改 `font-family` 族名。

> **图标字体说明：** 若作品用 `@font-face` 图标字体且资源在离线/重置环境加载失败，图标也会显示为方块——**与 CJK 无关**。脚本已用 Resource Timing 检测失败字体资源并告警；可确认本地静态资源可访问（本地 HTTP server，勿用 `file://`）。

#### 截图后校验（兜底防线，最终核验）

- 截图即"字形自检通过"画面；但**测宽法对 CJK 不可靠**，**应以像素对比做最终核验**。
- **像素对比法（definitive，fail-stop 门禁）：** 用统一门禁脚本比对图片中「目标 CJK 文本行」与「对照空白行」的墨量——目标应显著多于对照，差异过小即疑似只渲染了 tofu：
  - **墨量口径=墨像素数**（非"有墨行数"）：逐行 `any()` 判定会把"某行仅 1~2 个离群像素"当成整行有墨，截图内容/渐变背景易把空白行也判墨 → 目标/对照墨量恒等 → 误报。改为对窗口内墨像素计数后，离群像素只贡献几个，文字行与空白行差异仍巨大。
  - **豆腐块空心检测**：缺字渲染成空心矩形边框（不是空白），边框像素同样算墨，单纯"目标 vs 空白对照"拦不住。脚本对目标文字行窗口做**中心墨密度 ÷ 整体墨密度**校验（中心 1/3×1/3），真实 CJK 笔画贯穿中心（比值≥0.8），豆腐块空心（比值<0.8）→ fail。已验证：44 张真实封面全≥0.8，豆腐块合成图 0.688。

```bash
python3 <skill>/scripts/verify-glyphs.py <image/封面/图表.png>   # exit 0 通过；exit 1 疑似豆腐块（fail-closed）
# 脚本自动适配明暗背景：亮底数暗像素、暗底数亮像素。仅同一图片明暗混排或自动定位失败时再显式指定:
python3 <skill>/scripts/verify-glyphs.py <image> --probe                    # 先探测各行比值
python3 <skill>/scripts/verify-glyphs.py <image> --y-target 125 --y-control 5  # 按探测结果显式校验
# ⚠️ --y-control 必须指向真实空白区：顶部有标题/页眉时 y=5 会落在文字上导致误判。
# 完整参数: --y-target/--y-control/--height/--x0/--x1/--min-ratio/--max-density/--probe，见脚本 --help
# ⚠️ 校验对象是封面/图表自身渲染的文字（generator 用系统字体渲染并嵌入 bbox。
#    截图内容里的缺字方块不属于该校验范围——截图是作品的原始素材，不保证字形完整）。
```

#### 对其他渲染器（matplotlib / Graphviz / Mermaid）的对应

- **matplotlib（含中文优先 Playwright+HTML 渲染）：** 含中文图表优先 Playwright + HTML/CSS 出图（绕开 matplotlib `.ttc` 兼容缺陷）。若确用 matplotlib：装依赖 `pip install -U numpy pillow matplotlib`，用多字体回退列表 + 监听 glyph 缺失警告为硬失败。字体名与 `.ttc` 加载方式按平台：Linux → [work-preparation-linux.md#matplotlib-ttc-字体缓存问题](work-preparation-linux.md#matplotlib-ttc-字体缓存问题)；Windows → [work-preparation-windows.md#matplotlib--graphviz-字体名](work-preparation-windows.md#matplotlib--graphviz-字体名)。
- **Graphviz：** `fontname` 按平台：Windows=`Microsoft YaHei`，Linux=`Noto Sans CJK SC`（详见同上平台文件）。
- **Mermaid/PlantUML（经浏览器渲染）：** 与截图同流程——先字形自检，缺失族注入兜底后再导出。

#### 注意事项清单（防口口；执行门禁见 SKILL.md「总体要求」）

- **环境重置**：字体装在容器内，销毁即丢——每会话当轮重跑预检，不信任"上次装过"。
- **时序**：先装字体 → `fc-cache -f` → 再启动浏览器（运行中进程不识别新字体）。
- **fontconfig（Linux）**：仅装字体会口口，必须过 `fc-match "sans-serif:lang=zh"` 命中 CJK 校验。
- **兜底字体须中英双覆盖**：`Droid Sans Fallback`/`DejaVu Sans` 各只覆盖一侧，不可单独做中英混排兜底。
- **图标字体**（`@font-face`/CDN）加载失败也显方块——确保本地静态资源可访问。
- **提取自源码**：font-family、`ctx.font` 都要扫；封面/图表 HTML 勿写系统不存在的字体名。

### Part B — Generate PPT-Style Cover

Compose the work screenshot into a presentation-style cover image. **优先使用 Playwright + HTML/CSS**（而非 PIL 直接绘制）：

| Tool | Approach | 推荐度 |
| ---- | -------- | ------ |
| **playwright** | Generate an HTML page with the screenshot embedded in a styled layout, then capture it as a PNG via Playwright | ⭐ 首选 |
| **codex-slides** | Create a slide deck with the screenshot as a slide element, export as image | 可用 |
| **ppt-mcp-server** | Generate a PPT with the screenshot included, convert to image | 可用 |

> **⚠️ 禁止用 PIL (Pillow) `Image.resize()` 生成封面。** 两个根因问题：
>
> 1. **截图变形：** `Image.resize((w, h))` 强制拉伸到目标尺寸，不保持原始宽高比。
> 2. **Emoji 显示 `[×]`：** PIL 的 `ImageDraw.text()` 加载的字体不包含 emoji 字形，遇到 emoji 字符渲染为占位符。
>
> Playwright + Chromium 天然支持 emoji 渲染、CSS Flexbox 自适应布局、`object-fit: contain` 保持宽高比、渐变/阴影/玻璃态等视觉效果，全面优于 PIL 手动绘制。

#### Screenshot Layout Rules (硬性要求)

0. **布局种类（`generate_cover.py`）：** 单图 `classic/split/hero/showcase/polaroid/blur/topbar`；多图 `collage-h`（1 大上+4 小下）/`collage-v`（1 大左+3 小右）/`collage-grid`（1 大+3 小）。多图布局仅在项目为**多页**（`.html` ≥2）时可选，由 `build-cover.mjs` 统一概率池自动抽样（多页多图概率 3/10），agent 无需感知。
1. **禁止多张大截图导致画面拥挤。** 合理排布示例：
   - 1 大 + 下方 3–4 小 ✅
   - 1 大 + 右侧 3–4 小 ✅
   - 中心模式：1 大 + 4 角落小 ✅
   - 多张同等大截图并排 ❌
2. **其余区域**按需填写介绍文字或渲染装饰图纹（渐变/网格/粒子/光效），不要用截图填满所有空间。
2b. **关键词徽章（可选）**：`generate_cover.py --keywords "Web,游戏,前端,JavaScript"` 渲染一排标签徽章凸显作品技术栈/特点（3~5 个词，逗号分隔；不传则不渲染）。`build-cover.mjs` 从 `package.json.keywords` 或 README 探测，**30% 概率不传**（保持封面简洁）。徽章用 scheme 的 `badgeBg/badgeBorder/badgeColor` 配色 pill 样式，位于 tagline 之后。
3. **截图保持原始宽高比：** 使用 CSS `object-fit: contain` 放置截图，多余空间用 letterboxing（深色背景）填充，不裁剪、不拉伸、不变形。

```css
/* 关键：object-fit: contain 保持宽高比，不变形 */
.screenshot-card img {
  width: 100%;
  height: 100%;
  object-fit: contain; /* 等比缩放，多余空间用背景色填充 */
}
```

#### Design Requirements

1. **Font correctness:** Ensure all fonts (especially Chinese) render correctly — no □□□ (tofu/garbled). 封面文字同样必须做字体预检 + CSS 字体需求分析与兜底注入（见上），再合成封面。**⚠️ 编码门禁（两个来源都要查，不能只查外壳）：** 封面 HTML 必须在 `<head>` 首行声明 `<meta charset="UTF-8">` 且写文件用 `encoding="utf-8"`；**并且封面里嵌入的截图来自原项目页面——那张截图源页面（如原项目 `index.html`）也必须正确声明 charset / 服务端 `Content-Type` 带 `charset=utf-8`**。截图源的 charset 由守卫脚本「截图源 charset 门禁」拦截（读 `document.characterSet`），封面外壳由本检查项把关。
2. **No border obscuring text:** Design the layout so that no border or decorative element obviously obscures any text.
3. **Color tone:** Tech-oriented palette — 色调表见上方 [Visual Style Baseline](#visual-style-baseline-视觉风格基线)。**Step 4（封面）和 Step 6（图表）各自选取色调，不需要完全统一，但不得偏差太远。**
4. **技术感、避免平淡**：封面须体现技术感（渐变/glow/网格/玻璃态等效果由你自由发挥），不得平淡单调。
5. **Content:** Include the work name and a brief tagline on the cover.
6. Save the output to `/tmp/cover.png`（Linux/macOS）或 `os.tmpdir()` 即 `%TEMP%\cover.png`（Windows，如 `C:\Users\<user>\AppData\Local\Temp\cover.png`，非 `C:\tmp`）— never write into the work directory.

---

## Introduction Generation

### Extraction Strategy

1. **Explicit introduction section:** Look for headings like `## Introduction`, `## Description`, `## 简介`, `## 项目介绍`, `## 概述`, `## Overview` in the README. Use the content after that heading.
2. **First paragraph after title:** If no explicit introduction section, use the first non-heading paragraph after the H1 title.
3. **Project manifest description:** Check `package.json` `description`, `pyproject.toml` `[project] description`, etc.
4. **Synthesize:** If none of the above yield a usable introduction, summarize the project from the full README content.

### Length Constraint Enforcement

⚠️ **硬性约束：15~50 个字符（总字符数，含英文/数字/标点/emoji），不可超出。** 生成后必须计数验证。

**计数方式（禁止用 grep `\x{4e00}`）：** EulerOS 等旧 PCRE 环境下 `grep -oP '[\x{4e00}-\x{9fff}]'` 报 "character code point value too large"，计数恒为 0。必须用统一脚本（Node 原生 Unicode 码点比较，跨平台）：

```bash
node <skill>/scripts/count-cjk.mjs "$introduction"
# exit 0 = 合格; exit 1 = 超出范围（fail-stop）
# 支持自定义范围: --min 15 --max 50
# Windows 必须用 --file <utf8.txt>（内联参数经系统代码页转码会丢字误计），见 SKILL.md Step 5
```

- **Too short (< 15 chars):** 补充技术栈或核心功能描述。
- **Too long (> 50 chars):** **强制截断或重写**——这是一句话简介，不是详细描述。精简到核心功能："基于 X 的 Y 系统" 模式。

**Examples:**

| Input | Chars | Action |
| ----- | ----- | ------ |
| `问答系统` | 4 | ❌ 太短，补充：`基于大语言模型的智能问答与知识检索系统` |
| `基于大语言模型的智能问答与知识检索系统` | 19 | ✅ 合格 |
| `轻量级图书管理系统，支持借还、罚款、统计` | 19 | ✅ 合格 |
| `这是一个使用大语言模型技术构建的能够支持知识库检索和智能问答的完整系统解决方案` | 38 | ✅ 合格但偏长 |
| `本项目采用前后端分离架构，后端使用Python Flask框架，前端使用原生HTML和JavaScript，数据库采用SQLite，实现了图书的增删改查、用户管理、借阅归还、罚款计算以及数据统计可视化等完整功能` | 75 | ❌ 超出上限，强制精简为 `基于Flask的轻量级图书管理系统` (15 字) |

### Formatting

条分缕析，适当分段或使用列表，不要生成混乱的大长段。

---

## Details Article & Diagram Generation

The work details is a generated introduction article about the project, illustrated with diagrams, packaged into a zip archive.

### Article Requirements

1. **Content:** A comprehensive introduction to the project — what it does, how it works, key features, technology stack, and highlights. **内容来源：** 读 README.md 了解项目概述，**同时结合代码分析**（DevLens/GitNexus 等）深入理解项目架构、核心模块、关键流程，基于两者综合生成文章，而非仅复述 README。
2. **Length:** 500–1500 Chinese characters（**建议性要求**，非硬性约束）。
3. **Writing style:** Choose one based on the project's nature:

   | Style | Description | Suitable For |
   | ----- | ----------- | ------------ |
   | 严肃讲解 (serious/expository) | Formal, technical, precise | Infrastructure, security, enterprise projects |
   | 生活化讲解 (life-oriented/relatable) | Uses analogies, everyday language | Consumer-facing apps, productivity tools |
   | 活泼说明 (lively/casual) | Energetic, conversational, fun | Creative projects, games, experimental tools |

### Diagram Requirements

Include 1–3 images in the article:

#### Required — Image 1: System Architecture Diagram (系统架构图)

Generate a system architecture diagram showing the project's components, services, and their relationships.

**Available tools:**

| Tool | Best For | Example |
| ---- | -------- | ------- |
| `diagrams-mcp` (`render_diagram`) | Cloud architecture with real provider icons | AWS/Huawei Cloud/GCP service topology |
| `uml-mcp` (`generate_uml`) | Component/deployment diagrams | Mermaid or PlantUML component diagrams |
| `gituml-mcp` (`generate_component_diagram`) | Java/Spring Boot architecture | Auto-generated from source code |
| Mermaid flowchart | Custom architectures | `graph TD` with nodes and edges |

#### Optional — Image 2–3: AI-Selected Diagrams

Choose 0–2 from the following based on what best illustrates the project:

| Diagram Type | How to Generate | Tool |
| ------------ | --------------- | ---- |
| **Route graph (路由图谱)** | Discover all routes, render as graph | DevLens `find_nodes` with `nodeTypes: ["ROUTE"]`, GitNexus `gitnexus_route_map`, render with Mermaid |
| **Knowledge graph (知识图谱)** | Show module/component relationships and call statistics — keep simple, NOT function-level | DevLens `get_repo_overview` + `find_nodes`, render with Mermaid |
| **Module dependency graph (模块依赖图)** | Show module clusters and dependencies | DevLens `get_subgraph`, GitNexus `gitnexus_check`, render with Mermaid/PlantUML |
| **Code statistics visualization (代码统计可视化图)** | Show code metrics as charts | DevLens `get_coverage`, GitNexus stats, render as bar/pie chart with Mermaid/D2 |
| **Function mind map (功能思维导图)** | Show feature hierarchy as a mind map | Analyze features, render with Mermaid mindmap syntax |
| **API call sequence diagram (API调用时序图)** | Show request/response flow between services | `gituml-mcp_generate_sequence_diagram`, `uml-mcp` with `diagram_type: "sequence"`, GitNexus `gitnexus_query` |

**Code analysis workflow for diagram generation:** Use DevLens and GitNexus to understand the project structure, then generate diagrams with the appropriate rendering tool.

### Diagram Generation Methods

Any of the following rendering approaches is acceptable — choose based on diagram type and available tooling:

| Method | Description | Best For |
| ------ | ----------- | -------- |
| **Graphviz** | Render DOT-language graphs to PNG/SVG | Architecture, dependency, and knowledge graphs |
| **matplotlib + networkx** | Programmatically build and render graphs with Python | Code statistics visualization, module dependency graphs, custom chart-style diagrams |
| **GitNexus** | Use the code knowledge graph for structural queries, then render with any method | All diagram types — provides the data layer |
| **Mermaid / PlantUML / D2** | Declarative diagram syntaxes via `uml-mcp` or `diagrams-mcp` | Flowcharts, sequence, ER, state diagrams |
| **diagrams-mcp / gituml-mcp** | Cloud architecture and Java/Spring Boot auto-generated diagrams | Cloud topology, Java component/sequence diagrams |

**Example — matplotlib + networkx for a module dependency graph:**

```python
import matplotlib.pyplot as plt
import networkx as nx

G = nx.DiGraph()
G.add_edges_from([
    ('API Gateway', 'Auth Service'),
    ('API Gateway', 'Business Logic'),
    ('Business Logic', 'Database'),
    ('Business Logic', 'Cache'),
    ('Auth Service', 'User Store'),
])

plt.figure(figsize=(10, 6))
pos = nx.spring_layout(G, seed=42)
# 使用 Visual Style Baseline 选定 scheme 的色值（此处以 green 为例，#1a3a2e/#00b894；实际以所选 scheme 为准）
nx.draw(G, pos, with_labels=True, node_color='#1a3a2e', font_color='#e0f0f0',
        node_size=3000, font_size=10, arrows=True, edge_color='#00b894')
plt.title('Module Dependency Graph', fontsize=14, color='#e0f0f0')
plt.tight_layout()
# bbox_inches='tight' 防截断，pad_inches 留边距；保存后 resize 至宽 1280px（高度等比）
plt.savefig('/tmp/diagram-02.png', dpi=150, bbox_inches='tight', pad_inches=0.2)
```

> **含中文图表优先用 `generate_diagram.py`（Playwright + HTML/CSS）渲染**（绕开 matplotlib `.ttc` 兼容缺陷），见 SKILL.md Step 6。

### Image Design Requirements

1. **No border obscuring text:** Ensure no border or decorative element obviously obscures any text in the diagrams.
2. **⚠️ 图表中禁止使用 emoji：** matplotlib 和 Graphviz 不支持彩色 emoji 渲染（CBDT/CBLC 彩色位图表）。图表标签、标题、节点文字一律使用纯文字，不要包含 emoji；如需图标语义，用文字替代。
3. **Color tone:** Tech-oriented palette matching the cover image (see [Visual Style Baseline](#visual-style-baseline-视觉风格基线) above). **色调必须统一 across cover and article images; other dimensions may vary moderately.**
4. **⚠️ 禁止截断（硬性要求）：** 图表必须完整显示所有内容，不得有底部或侧边被裁掉。**图片宽度统一设为 1280px，高度由内容自适应。** matplotlib `savefig()` 用 `bbox_inches='tight', pad_inches=0.2`，输出后 resize 至宽 1280px；Graphviz 不设固定 `size`；Mermaid/PlantUML 通过 Playwright 设 viewport 宽 1280 + `fullPage: true`。生成后验证宽度为 1280px。

   > **⚠️ fullPage 截图「正文下方多一截浅色底」——已根治：** `generate_diagram.py` 按真实内容高度截图（量 `document.body.scrollHeight`，把视口缩放到该高度再截图），输出高度恒等于内容高度，无多余横带。手写模板时：主背景写在 `<body>` 上（html 勿显式写浅色背景）。

5. **技术感、避免平淡**：图表同封面标准——渐变填充/节点光效/grid/阴影等由你自由发挥，不得平淡单调。

   **Example — Graphviz with glow and gradient styling:**

   ```python
   from graphviz import Digraph

   dot = Digraph(comment='System Architecture', format='png')
   dot.attr(bgcolor='#0d1b2a', fontcolor='white', rankdir='TB')
   dot.attr('node', style='filled,rounded', fillcolor='#1b3a5c',
            fontcolor='white', shape='box', penwidth='2', color='#3a6a9c')
   dot.attr('edge', color='#4a7a9c', penwidth='2', arrowsize='1.2')

   dot.node('client', 'Client (Browser)', fillcolor='#2a5a8c')
   dot.node('gateway', 'API Gateway', fillcolor='#1b3a5c')
   dot.node('auth', 'Auth Service', fillcolor='#1b3a5c')
   dot.node('app', 'Application Server', fillcolor='#1b3a5c')
   dot.node('db', 'Database', fillcolor='#0d2b4a', shape='cylinder')

   dot.edges([('client', 'gateway'), ('gateway', 'auth'), ('gateway', 'app'), ('app', 'db')])
   dot.render('/tmp/architecture', cleanup=True)
   ```

### Article Format

Write the article as a Markdown file with image references using relative paths:

```markdown
# <Work Name> — 项目介绍

<Article content with 500–1500 Chinese characters>

## 系统架构

![系统架构图](resources/architecture.png)

<Architecture description>

## <Optional section for diagram 2>

![<diagram name>](resources/diagram-02.png)

<Diagram description>
```

---

## Details Package Generation

### Packaging Steps

1. **Create a fresh staging directory**（禁止复用旧目录，避免残留历史文件被打入 zip）: Windows → [work-preparation-windows.md#详情包-zip-打包首选-build-detail-zipmjs](work-preparation-windows.md#详情包-zip-打包首选-build-detail-zipmjs)；Linux/macOS → [work-preparation-linux.md#详情包-zip-打包首选-build-detail-zipmjs](work-preparation-linux.md#详情包-zip-打包首选-build-detail-zipmjs)。
2. **Write the agent-generated article** as `README.md` in the staging directory. This is NOT the README.md from `workDir` — it is the newly generated introduction article.
3. Copy all generated diagram images into `$staging/resources/`:
   - `architecture.png` — system architecture diagram (required)
   - `diagram-02.png` — optional diagram 2
   - `diagram-03.png` — optional diagram 3
4. **打包 + 校验一步到位（首选，跨平台零依赖）**：`build-detail-zip.mjs` 内置正确目录结构（README.md@根 + `resources/` 前缀），打包后自动跑服务端同源校验，避免「打包→校验失败→重打」多轮往返：
   ```bash
   node <skill>/scripts/build-detail-zip.mjs --readme <README.md> --resources <resources-dir> --out <workDetail.zip>
   ```
   > 备选（仅当 build-detail-zip.mjs 不可用时）：显式文件列表 `zip ... / zip -r .` 会打入残留；Windows 不能用 `Compress-Archive`（PS 5.1 压平子目录丢 `resources/` 前缀 → `GALLERY.PARAM.DETAIL_ZIP_INVALID`）。平台命令见步骤 1 的平台文件链接。

### Expected Zip Structure

```
workDetail.zip
├── README.md              (agent-generated introduction article — NOT the workDir's README.md)
└── resources/
    ├── architecture.png   (system architecture diagram — required)
    ├── diagram-02.png     (optional)
    └── diagram-03.png     (optional)
```

> The README.md inside the zip should use relative references like `resources/architecture.png` for all images. This ensures the images render correctly when the platform displays the work details.