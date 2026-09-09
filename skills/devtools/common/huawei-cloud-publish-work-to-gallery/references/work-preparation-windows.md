# Work Preparation — Windows 专属

本文件只包含 **Windows** 平台的 PowerShell/Win32 专属命令与注意项。运行环境为 Linux（EulerOS/HCE 等）时**不要读本文件**（环境指纹见 `scripts/detect-env.mjs`）。

跨平台统一流程与规则见 `work-preparation.md`；Linux/EulerOS 专属见 `work-preparation-linux.md`。

## Table of Contents

- [Shell 判定](#shell-判定)
- [Playwright/Chromium 安装前预检（PowerShell）](#playwrightchromium-安装前预检powershell)
- [Windows 字体预检（PowerShell）](#windows-字体预检powershell)
- [安装 Noto CJK（PowerShell）](#安装-noto-cjkpowershell)
- [截图有效性校验（PowerShell）](#截图有效性校验powershell)
- [详情包 zip 打包（.NET ZipFile）](#详情包-zip-打包net-zipfile)
- [matplotlib / Graphviz 字体名](#matplotlib--graphviz-字体名)

---

## Shell 判定

`detect-env.mjs` 输出 `shell: powershell` 或 `git-bash`。Git Bash（MSYS2）环境下的 bash 类命令可复用 `work-preparation-linux.md` 的 bash 写法；纯 PowerShell 用本文件写法。控制台与 bash/WSL 判定见 [windows-setup.md](windows-setup.md)。

---

## Playwright/Chromium 安装前预检（PowerShell）

先预检，全部通过则跳过安装直接截图；仅缺失部分按需安装。

```powershell
# ===== Windows Playwright/Chromium 安装前预检 (PowerShell) =====
$ErrorActionPreference = "SilentlyContinue"

# 检查项 1：Playwright Python 包是否已安装
$pwOk = $false
$pwVer = python -m playwright --version 2>$null
if ($LASTEXITCODE -eq 0) { $pwOk = $true }

# 检查项 2：Chromium 浏览器二进制是否已缓存
$chromiumOk = $false
$pwCache = Join-Path $env:LOCALAPPDATA "ms-playwright"
if (Test-Path $pwCache) {
  $chromiumDirs = Get-ChildItem -Path $pwCache -Directory -Filter "chromium*"
  if ($chromiumDirs) { $chromiumOk = $true }
}

# 检查项 3（最可靠）：Chromium 能否实际启动
$launchOk = $false
if ($pwOk -and $chromiumOk) {
  $result = python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(headless=True); b.close(); p.stop(); print('LAUNCH_OK')" 2>$null
  if ($result -match "LAUNCH_OK") { $launchOk = $true }
}

# 汇总
Write-Host "Playwright 包: $pwOk | Chromium 二进制: $chromiumOk | 可启动: $launchOk"

if ($launchOk) {
  Write-Host "✅ Playwright + Chromium 已就绪，跳过所有安装步骤"
} else {
  Write-Host "⚠️ 需要安装缺失组件："
  if (-not $pwOk)       { Write-Host "  - Playwright Python 包未安装 → pip install playwright" }
  if (-not $chromiumOk) { Write-Host "  - Chromium 二进制未缓存 → python -m playwright install chromium" }
  # Windows 上无需安装系统依赖（Chromium 自带所有 DLL）
}
```

> **Windows 说明：** Chromium **无需手动安装系统依赖**（自带所有必要 DLL，不会出现 `Missing libraries`）；不会出现 "OS not officially supported" 警告。缓存路径 `%LOCALAPPDATA%\ms-playwright\chromium-*`。安装命令同 Linux：`pip install playwright` + `python -m playwright install chromium`。`preflight.ps1` 已自动设 `PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright` 走国内镜像加速（npmmirror 镜像了 CFT win64 全部构建）。

---

## Windows 字体预检（PowerShell）

Windows 10/11 默认预装 CJK（微软雅黑）+ Emoji（Segoe UI Emoji）。**仅当预检发现缺失时**做下述校验与安装：

```powershell
# ===== Windows 字体预检 (PowerShell) — 在当前运行环境本地执行 =====
$ErrorActionPreference = "SilentlyContinue"
$fontsDir = "$env:WINDIR\Fonts"

# 1. CJK 中文字体检查（微软雅黑 / SimSun / SimHei / Noto CJK）
$cjkFonts = Get-ChildItem -Path $fontsDir | Where-Object {
  $_.Name -match "yahei|msyh|simsun|simhei|noto.*cjk|SourceHan"
}
if (-not $cjkFonts) {
  Write-Host "⚠️ CJK 字体未检测到，正在安装微软雅黑..."; exit 1
} else {
  Write-Host "✅ CJK 字体已安装: $($cjkFonts.Name -join ', ')"
}

# 2. Emoji 字体检查（Segoe UI Emoji / Noto Color Emoji）
$emojiFonts = Get-ChildItem -Path $fontsDir | Where-Object {
  $_.Name -match "seguiemoji|seguiemj|noto.*emoji"
}
if (-not $emojiFonts) {
  Write-Host "⚠️ Emoji 字体未检测到（Windows 10+ 通常预装 Segoe UI Emoji）"; exit 1
} else {
  $emojiFile = $emojiFonts[0].FullName
  $emojiSize = (Get-Item $emojiFile).Length
  Write-Host "✅ Emoji 字体已安装: $($emojiFonts.Name -join ', ') ($emojiSize bytes)"
  if ($emojiSize -lt 500000) { Write-Host "⚠️ Emoji 字体文件过小 ($emojiSize bytes)，可能不完整" }
}

# 3. 刷新字体缓存（Windows 无需 fc-cache，系统自动识别）
Write-Host "✅ Windows 字体预检通过（CJK + Emoji）"
```

---

## 安装 Noto CJK（PowerShell）

仅当预检发现 CJK 缺失时执行（Windows 10+ 通常预装微软雅黑，无需此步）：

```powershell
$fontUrl = "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
$outFile = "$env:TEMP\NotoSansCJKsc-Regular.otf"
Invoke-WebRequest -Uri $fontUrl -OutFile $outFile -UseBasicParsing
# 安装到系统字体目录（需管理员权限）
$shell = New-Object -ComObject Shell.Application
$fonts = $shell.Namespace(0x14)  # 0x14 = Fonts 文件夹
$fonts.CopyHere($outFile, 0x14)
Write-Host "✅ Noto Sans CJK SC 已安装"
```

---

## 截图有效性校验（PowerShell）

截图生成后必须校验（**校验标准跨平台，见 `work-preparation.md`；此处为 PowerShell 实现**）：

```powershell
$screenshot = Join-Path $env:TEMP "work-screenshot.png"  # = os.tmpdir()，非 C:\tmp
$ErrorActionPreference = "Stop"

# 1. 文件可访问性
if (-not (Test-Path $screenshot)) { Write-Host "❌ 截图文件不存在，视为无效图片"; exit 1 }

# 2. 图片格式（读取文件头判断）
$bytes = [System.IO.File]::ReadAllBytes($screenshot)[0..3]
$hex = ($bytes | ForEach-Object { $_.ToString("X2") }) -join ""
$validFormat = switch -Wildcard ($hex) {
  "89504E47*" { "image/png" }
  "FFD8FF*"   { "image/jpeg" }
  "474946*"   { "image/gif" }
  "524946*"   { "image/webp" }
  default     { $null }
}
if (-not $validFormat) { Write-Host "❌ 图片格式不合法: $hex，视为无效图片"; exit 1 }

# 3. 文件大小
$fileSize = (Get-Item $screenshot).Length
if ($fileSize -lt 10240) { Write-Host "❌ 图片过小 ($fileSize bytes)，视为无效图片"; exit 1 }

# 4. 图片宽高（需 .NET System.Drawing）
Add-Type -AssemblyName System.Drawing
try {
  $img = [System.Drawing.Image]::FromFile($screenshot)
  $width = $img.Width; $height = $img.Height
  $img.Dispose()
  if ($width -lt 200 -or $height -lt 200) {
    Write-Host "❌ 图片尺寸过小 (${width}x${height})，视为无效图片"; exit 1
  }
} catch {
  Write-Host "⚠️ 无法读取图片尺寸（跳过宽高校验）"
}

Write-Host "✅ 截图有效性校验通过（格式: $validFormat, 大小: $fileSize bytes）"
```

---

## 详情包 zip 打包（首选 build-detail-zip.mjs）

**首选（跨平台零依赖，一步到位）：** 直接在隔离 staging 目录上执行打包+校验：

```powershell
# 新建隔离 staging 目录（禁止复用旧目录，避免残留被打入 zip）
$staging = "$env:TEMP\gallery-details-staging"
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
New-Item -ItemType Directory -Path "$staging\resources" -Force

$env:OUT = "$env:TEMP\workDetail.zip"
node <skill>/scripts/build-detail-zip.mjs --readme "$staging\README.md" --resources "$staging\resources" --out $env:OUT
```

**备选（仅当 build-detail-zip.mjs 不可用）：** ⚠️ 不能用 `Compress-Archive -Path "$staging\resources\*.png"` —— PS 5.1 会压平子目录，生成的 zip 只有 `README.md + arch.png`（丢失 `resources/` 前缀），导致平台 `GALLERY.PARAM.DETAIL_ZIP_INVALID`。必须用 .NET `ZipFile::CreateFromDirectory` 保留目录结构（README.md + resources/arch.png）：

```powershell
Add-Type -AssemblyName System.IO.Compression.FileSystem
Remove-Item "$env:TEMP\workDetail.zip" -ErrorAction SilentlyContinue
[System.IO.Compression.ZipFile]::CreateFromDirectory("$staging", "$env:TEMP\workDetail.zip")
```

备选打包后须运行 `node <skill>/scripts/validate-detail-zip.mjs <zip>` 校验（跨平台，见 `work-preparation.md`）。

---

## matplotlib / Graphviz 字体名

- **matplotlib：** `plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'DejaVu Sans']`。微软雅黑通常为 `.ttf` 可直接用；Windows 10 的微软雅黑实为 `.ttc`（`C:\Windows\Fonts\msyh.ttc`），rcParams 失效时按路径加载：`FontProperties(fname=r'C:\Windows\Fonts\msyh.ttc')`。
- **Graphviz：** `fontname="Microsoft YaHei"`。

其余 Windows 环境准备（控制台编码、bash/WSL 判定、Playwright Python 包路径、zip 工具、`publish-work.mjs` 封装）见 [windows-setup.md](windows-setup.md)（Windows 首次运行必读）。