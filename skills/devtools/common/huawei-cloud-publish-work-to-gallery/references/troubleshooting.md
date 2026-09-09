# Troubleshooting — Publish Work to Gallery

**平台分流（重要）：** 错误码表、网络问题、打包结构、封面/图表规则均为**跨平台**内容，本文件直接给出。安装/字体/Playwright 等**平台专属**排障命令已拆分：Windows → [work-preparation-windows.md](work-preparation-windows.md)；Linux/EulerOS（HCE）→ [work-preparation-linux.md](work-preparation-linux.md)。运行前先 `node <skill>/scripts/detect-env.mjs` 确认环境，只读对应平台小节。

## Table of Contents

- [Network Connectivity Issues](#network-connectivity-issues)
- [Git Not Installed (Windows)](#git-not-installed-windows)
- [No Usable Python](#no-usable-python)
- [Domain ID Resolution Issues](#domain-id-resolution-issues)
- [Publish API Error Codes](#publish-api-error-codes)（完整错误码表见 [error-codes.md](error-codes.md)）
- [Work Packaging Issues](#work-packaging-issues)
- [Cover Image Generation Issues](#cover-image-generation-issues)
- [Screenshot & Font Issues](#screenshot--font-issues)
- [Activity Query Issues](#activity-query-issues)

---

## Network Connectivity Issues

### 1. Platform unreachable / connection timeout

**Problem:**
API requests to `https://gallery.developer.huaweicloud.com` time out or return connection refused.

**Diagnosis:**

连通性检查命令（`/open-api-guest/v1/gallery/announcements/current`，无需 STS 凭证）见 [SKILL.md — Prerequisites](SKILL.md#prerequisites)，直接照跑即可；超时或连接错误即判定平台不可达。（注：收到任何 HTTP 响应即说明平台可达；`announcement` 为 `null` 仅代表当前无生效公告，连通性正常。）

技能版本检查（`node <skill>/scripts/check-version.mjs`，内部经 `api.mjs GET /v1/gallery/skills/version?name=...` 请求，均为 open-api-guest 无需凭证）为**尽力而为**：平台不可达、非 2xx、解析失败或 `data.version` 为 `null` 时一律输出 `status=skip` 跳过，不阻塞发布；仅当本地 < 远端版本输出 `status=outdated` 时才提示升级并停止。

**Possible causes and solutions:**

| Cause                                      | Solution                                          |
| ------------------------------------------ | ------------------------------------------------- |
| Not on campus/VPN network                  | Connect to the appropriate network or VPN         |
| Firewall blocking the port                 | Ask IT to allow outbound HTTPS to `gallery.developer.huaweicloud.com:443` |
| Platform is down                           | Contact the platform administrator                |
| DNS resolution failure                     | 检查域名 `gallery.developer.huaweicloud.com` 能否解析（`nslookup gallery.developer.huaweicloud.com`） |

### 2. 404 Not Found from API

**Problem:**
API returns 404 for a known endpoint path.

**Root cause:**

- The platform base URL may have changed
- The API version path may differ from expected

**Solution:**

- Verify the full URL: `https://gallery.developer.huaweicloud.com/open-api-public/v1/gallery/camps`
- Contact the platform administrator to confirm the current API base URL and version

### 3. SSL/TLS errors

**Problem:**
Certificate errors occur when accessing the platform via HTTPS.

**Solution:**

- 平台使用 HTTPS（`scripts/api.mjs` 中 `PORT = 443`，使用 `node:https`），需正常 TLS 证书校验。证书错误通常意味着中间人代理或系统时间不正确——检查系统时间（`date`）是否准确，或网络中是否有代理拦截 HTTPS 流量。

---

## Git Not Installed (Windows)

### Problem:
`git --version` fails on Windows — git is not installed or not in PATH.

### Solution:
引导用户从国内清华镜像站下载安装 Git for Windows：

1. 打开清华镜像站：https://mirrors.tuna.tsinghua.edu.cn/github-release/git-for-windows/git/
2. 进入最新版本目录（如 `Release-2.46.0/`），下载 64-bit 安装包（如 `Git-2.46.0-64-bit.exe`）
3. 运行安装程序，保持默认选项即可（安装时会自动配置 PATH）
4. 安装完成后**重新打开终端**，再次运行 `git --version` 验证

> **注意：** Windows 默认的 `bash.exe`（位于 `C:\Users\<user>\AppData\Local\Microsoft\WindowsApps\`）是 WSL stub，不是 Git Bash。安装 Git for Windows 后会附带真正的 Git Bash（通常位于 `C:\Program Files\Git\bin\bash.exe`），`preflight.sh` 依赖它执行。

---

## No Usable Python

### Trigger（触发条件）

以下任一情况判定为「无可用 Python」：

- `python` / `python3` 均为 WindowsApps 的 Store stub（0 字节，执行退出码 9009 / 无输出）；
- PATH 与常见安装位置（[注册表 `PythonCore`](https://learn.microsoft.com/zh-cn/windows/python/beginners)、`~/.local/bin`、conda、uv 托管目录等）均无可用解释器；
- 系统仅存在**软件自带运行时**（如 workbuddy、GIMP 等捆绑的 `python.exe`）——按约定一律**忽略**，不视为完整版 Python，与用户确认口径一致。

### 表现（脚本 fail-stop 输出）

无 Python 时流程会在以下任一处被门禁拦截：

- **Step 1**：`python scripts/gen_sts.py` 无法运行 → `python : 无法将"python"项识别为 cmdlet…`（exit 9009），STS 生成失败，后续全部中断；
- **Step 4 门禁** `scripts/preflight.ps1`：
  `[preflight] X 缺可用 python3（WindowsApps 下 python3 可能是 Store stub，用 python 替代）。请从华为云镜像下载安装 Python 3.x: https://mirrors.huaweicloud.com/python/ （选最新 3.12/3.11 的 Windows installer，安装时勾选 Add to PATH）` → exit 1，不写 `font-gate-ok`，截图/封面禁止；
- **`scripts/build-cover.mjs`**：`❌ 找不到可用的 Python（已尝试 "python" 和 "python3"）。` → 封面合成禁止。

依赖 Python 的门禁（`font-gate-ok` / `screenshot-gate-ok` / 封面 / 图表 / 字形校验）全部无法产出，发布无法到达 Step 8。

### 向用户汇报的提示文案

> 检测到本机没有可用的完整版 Python：`python` / `python3` 均只是 WindowsApps 的 Store 占位符；workbuddy、GIMP 等软件自带运行时已按你的要求忽略。
> 发布流程整条链路依赖 Python（STS 凭证、封面截图、字形校验、架构图），按「没有 Python 就算没有」处理，当前无法启动发布。
>
> 请选择一种方式，我可以继续：
> ① **你自己装**：从华为云镜像下载 3.12/3.11 的 Windows installer，勾选 "Add to PATH" 安装 —— https://mirrors.huaweicloud.com/python/
> ② **你指出已装路径**：本机已有一份完整版 Python 但没在 PATH，把绝对路径发我（如 `C:\Users\xxx\AppData\Roaming\uv\python\...\python.exe`），我加进 PATH 后直接复用。
> ③ **我来帮你装**：用官方安装包替你安装（`InstallAllUsers=0` + `PrependPath=1` + `Include_pip=1`，装到当前用户目录，不覆盖系统），装完自动验证 `python --version`，确认可用后从 Step 1 重跑发布。**此选项会改动你本机环境，需要你明确同意。**

回复「1」「2」「3」或"装吧"后继续。

### agent 代装（选项 ③）步骤

```powershell
# 下载（华为云镜像，以 3.12.x 为例）
$ver = "3.12.14"
$exe = "$env:TEMP\python-$ver-amd64.exe"
Invoke-WebRequest -Uri "https://mirrors.huaweicloud.com/python/$ver/python-$ver-amd64.exe" -OutFile $exe -UseBasicParsing
# 静默安装：当前用户、加入 PATH、含 pip、不装测试
Start-Process -Wait -FilePath $exe -ArgumentList "/quiet","InstallAllUsers=0","PrependPath=1","Include_pip=1","Include_test=0"
# 用完整路径验证（新装的 PATH 对已打开的终端不生效）
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" --version
```

安装完成后**重新打开终端**重跑 `scripts/preflight.ps1`，再回到 Step 1 重新发布。

> ⚠️ **镜像 URL 与描述必须一致：** Python 安装包一律指华为云镜像 `https://mirrors.huaweicloud.com/python/`（TUNA `https://mirrors.tuna.tsinghua.edu.cn/python-release/` 非安装包镜像，访问 403，禁用）。pypi 源 `https://pypi.tuna.tsinghua.edu.cn/simple`、Git for Windows 的 TUNA github-release 镜像与 Python 无关，保持不变。

---

## Domain ID Resolution Issues

### 1. hcloud not installed

**Problem:**
`hcloud` command not found when trying to resolve Domain ID.

**Solution:**
Install Huawei Cloud KooCLI:

```bash
# Linux/macOS
curl -sSL https://res-hw-global.obs.ap-southeast-1.myhuaweicloud.com/cli/latest/hcloud_install.sh -o hcloud_install.sh && bash hcloud_install.sh
```

```powershell
# Windows — 下载 zip 并解压
# 1. 下载 Windows 版 hcloud zip
node -e "const https=require('https');const fs=require('fs');const url='https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-windows-amd64.zip';const f=fs.createWriteStream('hcloud.zip');https.get(url,{rejectUnauthorized:true},res=>{res.pipe(f);f.on('finish',()=>{f.close();console.log('Downloaded')})}).on('error',e=>console.log('ERR:',e.message))"

# 2. 解压
Expand-Archive -Path "hcloud.zip" -DestinationPath "hcloud-cli" -Force

# 3. 验证
echo y | .\hcloud-cli\hcloud.exe version
# 输出: 当前KooCLI版本:7.2.12

# 4.（可选）加入 PATH 以便直接调用 hcloud
$env:PATH += ";$PWD\hcloud-cli"
# 或将 hcloud.exe 所在目录添加到系统环境变量
```

Verify installation:

```bash
hcloud version
```

### 2. hcloud credentials not configured

**Problem:**
`hcloud configure list` shows no valid credentials, or `hcloud IAM KeystoneListAuthDomains` returns an authentication error.

**Solution:**

hcloud 鉴权需要华为云 AK/SK（访问密钥）。按以下优先级获取并配置：

**优先级 1 — 环境变量（推荐，hcloud 自动读取）：**

```bash
# Linux / macOS — 检查环境变量
echo "AK: ${HUAWEICLOUD_SDK_AK:-(未设置)}"
echo "SK: ${HUAWEICLOUD_SDK_SK:-(未设置)}"
echo "Token: ${HUAWEICLOUD_SDK_SECURITY_TOKEN:-(未设置，永久AK不需要)}"
```

```powershell
# Windows — 检查环境变量
Write-Host "AK: $(if ($env:HUAWEICLOUD_SDK_AK) { '已设置' } else { '未设置' })"
Write-Host "SK: $(if ($env:HUAWEICLOUD_SDK_SK) { '已设置' } else { '未设置' })"
Write-Host "Token: $(if ($env:HUAWEICLOUD_SDK_SECURITY_TOKEN) { '已设置' } else { '未设置，永久AK不需要' })"
```

若环境变量已设置，hcloud 会自动使用，无需额外配置。

**优先级 2 — 提示用户从华为云控制台获取 AK/SK：**

若环境变量未设置，向用户输出以下提示引导获取 AK/SK：

```
请按以下步骤获取华为云访问密钥（AK/SK）：

1. 登录华为云控制台「我的凭证」页面：
   https://console.huaweicloud.com/iam/#/myCredential
   （或：控制台右上角用户名 →「我的凭证」）

2. 在「访问密钥」页签 → 点击「新增访问密钥」

3. 输入描述（如 "gallery-publish"）→ 点击「确定」
   （若需扫码/短信验证，按提示完成）

4. 系统生成 AK 和 SK：
   - AK（Access Key ID）：形如 "HCSAPI3W******"
   - SK（Secret Access Key）：⚠️ 仅显示一次，请立即保存！
   - 也可下载 credentials.csv 文件

5. 配置为环境变量：

   Linux / macOS:
     export HUAWEICLOUD_SDK_AK="你的AK"
     export HUAWEICLOUD_SDK_SK="你的SK"
     # STS 临时凭证还需:
     export HUAWEICLOUD_SDK_SECURITY_TOKEN="你的SecurityToken"

   Windows (PowerShell):
     $env:HUAWEICLOUD_SDK_AK = "你的AK"
     $env:HUAWEICLOUD_SDK_SK = "你的SK"
     # STS 临时凭证还需:
     $env:HUAWEICLOUD_SDK_SECURITY_TOKEN = "你的SecurityToken"

   或使用 hcloud 配置命令:
     hcloud configure set --access-key="你的AK" --secret-key="你的SK" --region=cn-north-4
```

**优先级 3 — hcloud 交互式配置：**

```
hcloud configure
# 按提示输入 AK/SK；凭证将存储在本地配置文件
```

> **STS 临时凭证注意：** AI DevSpace / CodeArts 等环境中的 AK/SK 常为临时 STS 凭证（带 `securityToken`）。仅传 AK/SK 不传 `securityToken` 会报 `AKSK expired or invalid`。三个环境变量 `HUAWEICLOUD_SDK_AK`、`HUAWEICLOUD_SDK_SK`、`HUAWEICLOUD_SDK_SECURITY_TOKEN` 必须同时设置。

> **AK/SK 获取地址：** 华为云控制台 →「我的凭证」→「访问密钥」页签，或直接访问 https://console.huaweicloud.com/iam/#/myCredential 。每个用户最多可创建 2 组访问密钥。

### 3. Cannot resolve Domain ID automatically

**Problem:**
hcloud is configured but `hcloud IAM KeystoneListAuthDomains` fails to return Domain ID.

> 必须排查 hcloud 失败原因并重试，确保 Domain ID 通过 hcloud 自动获取。

**Solution:**

按以下顺序排查并重试 hcloud：

| 原因 | 诊断 | 修复 |
|------|------|------|
| STS 凭证缺 securityToken | 报 `AKSK expired or invalid` | 补设环境变量 `HUAWEICLOUD_SDK_SECURITY_TOKEN` |
| AK/SK 已过期或被禁用 | 报鉴权失败 | 重新从控制台获取 AK/SK（见 [§2](#2-hcloud-credentials-not-configured)） |
| Region 未设置 | 报 region 相关错误 | `hcloud configure set --region=cn-north-4` |
| 网络超时 | 请求无响应 | 检查网络连通性，重试 hcloud 命令 |
| hcloud 版本过旧 | API 不支持 | 升级 hcloud：重新安装最新版 KooCLI（见 [§1](#1-hcloud-not-installed)） |

```bash
# 排查后重试
hcloud configure set --region=cn-north-4 2>/dev/null
hcloud IAM KeystoneListAuthDomains
```

**若所有排查均无法解决**，向用户报告具体错误信息并建议：
1. 检查 AK/SK 是否正确（从控制台重新获取）
2. 升级 hcloud CLI 到最新版本
3. 确认网络可访问华为云 IAM 服务端点

---

## Publish API Error Codes

完整错误码表（Parameter/Authentication/Activity/Work/Publish/Idempotency/Rate Limit/System）已拆到独立文件：**[error-codes.md](error-codes.md)**。

按错误码查表定位修复，不要整读——用 `Ctrl+F` 或目录跳转目标小节。

---

## Work Packaging Issues

### 1. Zip creation fails

**Problem:**
Compressing the work directory into `/tmp/work.zip` fails.

**Possible causes and solutions:**

| Cause                             | Solution                                                                              |
| --------------------------------- | ------------------------------------------------------------------------------------- |
| Directory path contains spaces    | Quote the path: `zip -r "/tmp/work.zip" "path with spaces"`                           |
| Directory is very large (> 500MB) | Inform the user; suggest excluding `node_modules/`, `.git/`, `dist/`, build artifacts |
| Permission denied                 | Check read permissions on the work directory                                          |
| `zip` command not found           | Linux: `yum install -y zip` / `apt install -y zip`；Windows: 使用 `Compress-Archive`  |
| Disk full in /tmp                 | Free up temp directory space or use an alternative temp path                          |

> **打包首选**：`node <skill>/scripts/build-detail-zip.mjs --readme <README.md> --resources <dir> --out <zip>`（跨平台零依赖，打包+校验一步到位），避免 `zip`/`Compress-Archive` 的平台差异。以下为备选平台命令。

### 2. Details zip structure incorrect

**Problem:**
The details zip does not have the expected structure (README.md at root, resources/ folder with images).

**Solution:**
按 [work-preparation.md — Details Package Generation](work-preparation.md#details-package-generation) 用 `build-detail-zip.mjs` 内置正确结构一步打包（或重建 staging 目录并显式指定文件列表，不要 `zip -r .`）。

### 2a. Zip contains residual files from previous operations

**Problem:**
The details zip includes leftover files (e.g., old screenshots like `screenshot_products.png`, `screenshot_dashboard.png`) that are not referenced by the article but were in the staging directory from previous steps. Zip size is unexpectedly large.

**Root cause:**
`zip -r /tmp/workDetail.zip .` recursively packages the entire staging directory, including any residual files. If the staging directory was reused from a previous run, old files are included.

**Prevention:**

1. **Always use a fresh staging directory:** `rm -rf "$staging" && mkdir -p "$staging/resources"` — never reuse.
2. **Zip with explicit file list:** `zip /tmp/workDetail.zip README.md resources/*.png` — only package intended files, not the entire directory.

### 3. README image references broken

**Problem:**
Images referenced in README.md are not found when packaging the details zip.

**Solution:**

- Scan README.md for image references: `![alt](path/to/image.png)` or `<img src="path/to/image.png">`
- Resolve each path relative to the work directory
- Copy found images to `resources/` in the staging directory
- If an image file is missing, warn the user and skip it (the README will have a broken reference, but the publish can still proceed)

---

## Cover Image Generation Issues

### 1. Headless browser not available

**Problem:**
Cannot capture a screenshot of the frontend because Playwright is not installed.

**Solution:**

- Look for existing screenshots or banner images in the project (check `docs/`, `assets/`, `images/`, `public/`, `static/`, root directory for `.png`, `.jpg`, `.jpeg`, `.svg` files)
- If a suitable image is found, use it as the cover
- If no image is found, generate a simple text-based cover image with the work name

### 2. Frontend page fails to render

**Problem:**
The `index.html` exists but the page does not render correctly (blank page, error message, requires backend API).

**Solution:**

- Try capturing the page anyway — even a loading state may be acceptable as a cover
- If the page requires a running backend, inform the user and ask them to start the backend service, or fall back to generating a cover from the README

### 3. Generated image is too large or wrong format

**Problem:**
The cover image exceeds platform limits or is in an unsupported format.

**Solution:**

- Convert to PNG if needed: `convert cover.jpg cover.png` (ImageMagick) or use Python PIL
- Resize if too large: aim for 1280×720, max file size 5MB
- Use PNG format for best compatibility

### 4. Screenshot distortion in cover image

**Problem:**
Screenshots embedded in the PPT-style cover are visibly stretched or squished (e.g., a 1280×720 screenshot appears vertically flattened).

**Root cause:**
PIL `Image.resize((w, h))` forcibly stretches the image without preserving the aspect ratio (e.g., 16:9→1:1 is a 43% ratio change).

**Prevention:**

优先使用 Playwright + HTML/CSS 生成封面，用 CSS `object-fit: contain` 保持宽高比；**禁止** `Image.resize()` 到不同宽高比。完整说明与代码示例见 [work-preparation.md — Screenshot Layout Rules](work-preparation.md#screenshot-layout-rules-硬性要求)。

### 5. Cover screenshot layout — two large screenshots side by side

**Problem:**
Cover contains two equally large screenshots side by side, looking cluttered and leaving no room for text or decorative elements.

**Prevention (硬性要求):** 禁止同时出现两张大截图；合理排布为 1 大 + N 小。详见 [work-preparation.md — Screenshot Layout Rules](work-preparation.md#screenshot-layout-rules-硬性要求)。

---

## Screenshot & Font Issues

### 1. Chinese characters appear as □□□ / emoji appear as X (tofu/garbled)

**Problem:**
Screenshot shows boxes (□□□) instead of Chinese characters, or X/boxes instead of emoji — the system lacks CJK fonts and/or emoji fonts.

**Common pitfall:** 仅安装 CJK 字体而遗漏 emoji 字体，导致中文正常但 emoji 全部显示为 □ 方框。

> **先分辨是"口口"(tofu) 还是 "mojibake"(乱码)：** 若文字显示为 `æ‰«é›·æ¸¸æˆÏ` 这类乱码，是页面**缺 `<meta charset>`/服务端无 `charset=utf-8`**、被按 Latin-1 解析 UTF-8 的**编码问题，不是字体问题**。字形呈现规则的 □ 方块才是缺字体（走下方四道防线）。**注意：既查自生成的封面 HTML，也查嵌入封面的截图来源页（原项目页面）**——截图源若乱码，嵌进封面仍乱码。检测：Playwright 读 `document.characterSet`（非 UTF-8 即高危）；修复给页面 `<head>` 首行加 `<meta charset="UTF-8">` 或服务端 `Content-Type: text/html; charset=utf-8`，写文件用 `encoding="utf-8"`。

**Solution — 四道防线（按序执行，全部通过才可截图/合成）：**

1. **① 字体预检（当轮执行，不信任缓存）：** 环境重置会清空已装字体，每轮重跑预检脚本，CJK + emoji 均验证通过才继续。时序与 5 项门禁见 [SKILL.md 总体要求](../SKILL.md)；完整预检脚本（含 Windows PowerShell 版）见 [work-preparation.md — Cover Image Generation](work-preparation.md#cover-image-generation)。
2. **CSS 字体需求分析与兜底注入（根因防线）：** 仅装 Noto CJK 不等于 CSS 声明的字体可用。**必须从作品源码提取 `font-family` 需求**，归类后补齐兜底字体套件，并在 Playwright 里用 `@font-face { src: local(兜底) }` 原地重映射缺失族（不覆盖图标字体族名）。见 [work-preparation.md — CSS Font Requirements Analysis](work-preparation.md#css-font-requirements-analysis--fallback-injection)。
3. **页面内字形自检（截图前，主防线）：** 截图前对每个 CSS 字体族用 canvas 测宽探针自检（中文+拉丁双检），缺失族注入兜底后**必须复检通过**才可截图（`document.fonts.check` 只校验是否加载、不校验字形覆盖，不作主判据）。脚本见 [work-preparation.md ③](work-preparation.md#css-font-requirements-analysis--fallback-injection)。
4. **截图后校验（兜底）：** 截图即自检通过状态下的画面；如需再确认可复跑 probe，或运行 [可选 tofu-alert.py 豆腐块粗检](work-preparation.md#css-font-requirements-analysis--fallback-injection)（告警级，仅供人工复查）。

### 1a. preflight 脚本被后台化（Linux 首次运行常见）

**Problem:**
执行 `bash preflight.sh` 后，shell 工具将其**后台化**（执行 >30s 超时阈值），返回输出文件路径而非直接结果——`exit code` 为空、`stdout` 为空、`/tmp/font-gate-ok` 尚未生成。这**不是失败**，是脚本还在跑（首次需装 CJK/emoji 字体、配置 fontconfig、下载 Chromium）。

**Solution — 轮询等待标记文件，不要判断命令返回值：**

```bash
# 以标记文件出现且内容 ok=true 为完成判据（最多等 180s），期间可并行做其他步骤
for i in $(seq 1 36); do
  if [ -f /tmp/font-gate-ok ] && grep -q '^ok=true' /tmp/font-gate-ok; then echo "preflight done"; break; fi
  sleep 5
done
# 超时仍未出现标记 → 用 pgrep -f preflight.sh 判断进程状态，确认是仍存活还是已失败
```

- Windows（`preflight.ps1`）同样适用：轮询 `%TEMP%\font-gate-ok` 内容含 `ok=true`，或用 `Get-Process` 检查进程存活。
- 判定门禁是否通过**只看标记文件内容**（`ok=true` + `gate=preflight`），不看命令返回码。

### 2. Page shows "unexpected token" error

**Problem:**
Screenshot shows a JavaScript error `"Unexpected token 'N'"` or similar.

**Root cause:**
The frontend calls `/api/*` endpoints that don't exist locally. The static server returns `404 Not Found` as plain text, and the browser tries to parse it as JSON.

**Solution:**
Mock all API endpoints in the local server (return JSON, not plain text for 404s). Complete mock server template见 [work-preparation.md — Option 2](work-preparation.md#option-2-local-playwright-with-mock-data)。

### 3. Playwright/headless browser not available

**Problem:**
The screenshot capture requires a headless browser, but Playwright fails to launch.

> **⚠️ 先预检再安装：** 遇到此问题时，**先运行 [work-preparation.md — 安装前预检脚本](work-preparation.md#part-a--capture-work-screenshot) 判断具体缺失哪个组件**（Playwright 包 / Chromium 二进制 / 系统依赖），仅安装缺失部分，不要盲目重装。Chromium ~300MB，重复下载耗时。

**Possible causes:**

| Cause                   | Diagnosis                                                 | Solution                                                                                                                      |
| ----------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Chromium binary missing | `Error: browserType.launch: Executable doesn't exist`     | Run `python -m playwright install chromium`                                                                                   |
| Architecture mismatch   | Chrome crashes with `Exec format error` or `Bad CPU type` | Playwright auto-detects architecture, but if on arm64, force reinstall: `python -m playwright install chromium --force`      |
| Missing system deps     | `Error: Missing libraries`                                | 详见下方 [§5 Chromium 系统依赖安装失败](#5-chromium-系统依赖安装失败euleroshce)                                                                                                                |
| Python version mismatch | `Executable doesn't exist at .../chromium_headless_shell-XXXX/...` | 多个 Python 版本各自安装不同 Playwright，Chromium 版本不匹配。用实际运行脚本的 Python 安装：`python3 -m playwright install chromium` |
| "OS not officially supported" warning | `BEWARE: your OS is not officially supported by Playwright` | **非错误！** Playwright 自动下载 ubuntu24.04-arm64 fallback build，可正常使用。不要因此中断安装或放弃截图 |
| Python version too old  | Syntax errors                                             | Ensure Python >= 3.8                                                                                                          |
| Disk space              | Install hangs or fails                                    | Chromium requires ~300MB free space                                                                                           |

### 3a. arm64 headless Chromium canvas fillText renders nothing (emoji 校验误报 tofu)

**Problem:**
On arm64 (aarch64) headless Chromium, `canvas.fillText()` produces **zero pixels for ALL text** — not just emoji, but ASCII too. The screenshot_guard emoji check uses canvas pixel comparison to detect tofu glyphs, so it falsely reports core emoji as missing and **hard-fails**, blocking the screenshot.

**Root cause:**
This is a **Chromium headless shell platform limitation on arm64**, not a font issue. The browser's page rendering pipeline (used by Playwright's `page.screenshot()`) works fine — only the canvas 2D API's text rendering is broken. Confirmed by: `ctx.fillText('A', 4, 4)` returns 0 non-zero pixels, while the actual page screenshot is 200KB+ with visible text.

**Solution — screenshot_guard.py already handles this (v2):**
The emoji check now includes an **ASCII baseline probe** before the emoji check. If `ctx.fillText('A')` also returns tofu (0 pixels), it sets `canvasTextBroken = true` and **downgrades the emoji check from hard failure to warning**. The screenshot proceeds normally because Playwright screenshots use the browser rendering pipeline, not canvas.

If you see `canvasTextBroken=true` in the emoji 校验 log line, this is expected on arm64 — no action needed.

### 3b. fontconfig 中文映射到 emoji 字体（99-emoji-fallback.conf 副作用）

**Problem:**
After `preflight.sh` writes `99-emoji-fallback.conf` (which prepends Noto Color Emoji to `sans-serif`), `fc-match 'sans-serif:lang=zh'` may return `NotoColorEmoji.ttf` instead of a CJK font. The old preflight only checked for `DejaVuSans.ttf`, so it missed this case and logged `fontconfig 中文 → NotoColorEmoji.ttf` — Chinese text would render with an emoji font.

**Root cause:**
`99-emoji-fallback.conf` uses `mode="prepend" binding="weak"` to put Noto Color Emoji at the front of the sans-serif family list. fontconfig's `fc-match` without a charset constraint returns the first font in the list, which is now NotoColorEmoji. While `binding="weak"` should let CJK codepoints fall through to the next font, the `fc-match 'sans-serif:lang=zh'` check (without charset) still returns the first match.

**Solution — preflight.sh already handles this (v2):**
The CJK fontconfig check now detects **both** DejaVuSans.ttf **and** emoji font matches (NotoColorEmoji.ttf etc.) as triggers for writing `99-cjk-fallback.conf`. The CJK fallback uses `mode="prepend" binding="strong"` with a `lang="zh"` qualifier, which overrides the emoji's `binding="weak"` for Chinese text. A final die-check also catches the case where the CJK fallback fails to fix the mapping.

### 4. CSS/JS resources fail to load

**Problem:**
Page renders without styles or scripts — only raw HTML is visible in the screenshot.

**Root cause:**
The HTML references resources with absolute paths (e.g., `/styles.css`, `/app.js`) that don't resolve correctly on `file://` protocol.

**Solution:**
Always use a local HTTP server (`http://127.0.0.1:${port}/index.html`) instead of `file://` protocol — absolute paths like `/styles.css` won't resolve on `file://`. See [work-preparation.md — Option 2](work-preparation.md#option-2-local-playwright-with-mock-data) for the server template.

### 5. Chromium 系统依赖安装失败（EulerOS/HCE）

**Problem:**
Playwright Chromium 启动报 `Missing libraries` 或直接 crash。`python -m playwright install-deps` 失败（仅支持 apt-get，报 `sh: line 1: apt-get: No such file or directory`）。尝试用 Ubuntu 包名 `yum install -y libnspr4 libnss3` 报 `No match for argument`。

**Root cause:**
EulerOS/HCE 的系统库包名与 Ubuntu/Debian 不同，不能通用。`python -m playwright install-deps` 仅支持 apt-get，在 yum 系发行版上不生效。

**Solution:**
跳过 `install-deps`，手动用 `yum` + HCE 包名安装完整系统依赖（命令和包名映射表见 [work-preparation-linux.md — Chromium 系统依赖安装](work-preparation-linux.md#chromium-系统依赖包名映射euleroshce-vs-ubuntu)），然后 `python -m playwright install chromium`。

> **Windows 平台不会出现此问题：** Windows 版 Chromium 自带所有依赖 DLL，`python -m playwright install chromium` 一步即可，无需手动安装系统依赖。

**安装失败后不要放弃截图方案**，换用正确包名重试即可。**严禁跳过 Option 2 直接回退 Option 3**——渐进式回退链见 [SKILL.md Step 4](../SKILL.md#step-4-cover-image)。

---

## Activity Query Issues

### 1. Activity list is empty

**Problem:**
The GET /camps API returns success but `data.items` is an empty array.

**Possible causes:**

- No activities have been published yet
- All activities are in draft/hidden/archived status
- The `name` or `school` query filter is too restrictive

**Solution:**

- Remove any query filters and retry with default parameters
- Inform the user that no available activities were found and suggest contacting the administrator

### 2. Activity list API returns error

**Problem:**
The GET /camps API returns a non-200 response.

**Solution:**

- If 400: Check pagination parameters (pageNo >= 1, 1 <= pageSize <= 100)
- If 404: The API endpoint path may have changed — verify with the administrator
- If 500: Retry after a brief wait; the platform may be experiencing issues
- If network error: See [Network Connectivity Issues](#network-connectivity-issues)

### 3. Selected activity is not accepting submissions

**Problem:**
Publish API returns `GALLERY.CAMP.UNAVAILABLE` for the selected activity, or the user attempts to select a camp that is not in "可投稿" status.

**Solution:**

- Re-query the activity list and determine each camp's submission status (see [api-spec.md — Submission Status Determination](api-spec.md#submission-status-determination) for the full status table).
- Only present camps with "可投稿" status as selectable options.
- If the user attempts to select a non-submittable camp, inform them: `该训练营当前状态为「<status>」，未开放投稿，请选择状态为「可投稿」的训练营。`
- If no camps are currently submittable, inform the user and suggest checking back later or contacting the administrator.
