# preflight.ps1 — Windows 渲染门禁（PowerShell 原生，无需 bash）
# 用法: powershell -ExecutionPolicy Bypass -File preflight.ps1
# 通过→写 $env:TEMP\font-gate-ok 并 exit 0; 失败→exit 1
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Marker = Join-Path $env:TEMP "font-gate-ok"
$script:browserReady = "n/a"
function Die($m) { Write-Host "[preflight] X $m" -ForegroundColor Red; exit 1 }
function Log($m) { Write-Host "[preflight] $m" }

# 1. Python（排除 WindowsApps Store stub）
# ⚠️ PowerShell 5.1 兼容：不在 Where-Object 脚本块内直接写 & 调用 + 2>$null 重定向
#    （5.1 解析器会将 2> 误认为数值后跟重定向，导致括号匹配混乱 → Missing closing ')'）
#    改用辅助函数拆分，重定向用 2>&1 | Out-Null 替代 2>$null
function Test-PyCmd($cmd) {
    if (-not (Get-Command $cmd -EA SilentlyContinue)) { return $false }
    $eap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $cmd -c "import sys" 2>&1 | Out-Null } catch { } finally { $ErrorActionPreference = $eap }
    return ($LASTEXITCODE -eq 0)
}
function Test-PyMods($cmd) {
    $eap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $cmd -c "import numpy,PIL" 2>&1 | Out-Null } catch { } finally { $ErrorActionPreference = $eap }
    return ($LASTEXITCODE -eq 0)
}
$pipOpts = @("-q", "--index-url=https://pypi.tuna.tsinghua.edu.cn/simple")
# PEP 668（uv/pyenv 等管理的 Python 拒绝 pip 写入系统 site-packages）时自动加 --break-system-packages 重试
function Pip-Install([string]$pymod, [string[]]$pkgs) {
    $eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    & $pymod -m pip install @pkgs @pipOpts 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { & $pymod -m pip install @pkgs @pipOpts --break-system-packages 2>&1 | Out-Null }
    $ErrorActionPreference = $eap
}
$py = @("python3","python") | Where-Object { Test-PyCmd $_ } | Select-Object -First 1
if (-not $py) { Die "缺可用 python3（WindowsApps 下 python3 可能是 Store stub，用 python 替代）。请从华为云镜像下载安装 Python 3.x: https://mirrors.huaweicloud.com/python/ （选最新 3.12/3.11 的 Windows installer，安装时勾选 Add to PATH）" }
if (-not (Test-PyMods $py)) { Log "安装 numpy/pillow..."; Pip-Install $py @("numpy","pillow") }
if (-not (Test-PyMods $py)) { Die "numpy/pillow 不可用: pip install numpy pillow" }

# 1b. 发现所有其他可用 Python 3+ 解释器（python3/python/python3.x 同二进制去重，
#     与主解释器 $py 同真实路径的跳过），为它们补装依赖。
#     背景: Windows 可能同时存在 python3.9 和 python 3.11，site-packages 互不可见，
#           preflight 只装到一个 → agent 用另一个调用脚本时 ModuleNotFoundError。
function Resolve-PyRealPath([string]$cmd) {
    try {
        $c = Get-Command $cmd -EA Stop
        return $c.Path
    } catch { return "" }
}
function Add-OtherPythonDeps([string]$primary) {
    $primaryPath = Resolve-PyRealPath $primary
    $seen = @{}
    $cands = @("python","python3","python3.13","python3.12","python3.11","python3.10","python3.9","python3.8")
    foreach ($cand in $cands) {
        if (-not (Test-PyCmd $cand)) { continue }
        $p = Resolve-PyRealPath $cand
        if (-not $p -or $seen[$p]) { continue }        # 同路径已处理
        $seen[$p] = $true
        if ($p -eq $primaryPath) { continue }          # 就是主解释器，跳过
        if (Test-PyMods $cand) { continue }             # 依赖已齐，跳过
        Log "为 $cand 补装 numpy/pillow/playwright（避免多解释器 site-packages 不互通）..."
        $eap2 = $ErrorActionPreference; $ErrorActionPreference = "Continue"
        $ok = $false
        try { Pip-Install $cand @("numpy","pillow"); if ($LASTEXITCODE -eq 0) { Pip-Install $cand @("playwright"); if ($LASTEXITCODE -eq 0) { $ok = $true } } } catch { }
        $ErrorActionPreference = $eap2
        if (-not $ok) {
            Log "⚠️ $cand 依赖补装失败——gate 不记录该解释器，后续用它调脚本可能 ModuleNotFoundError"
        }
    }
}

# 2. Playwright（Python 版，优先复用系统 Edge/Chrome，避免下载 Chromium）
#    截图脚本已迁移为 Python（shot_app.py / screenshot_guard.py / generate_cover.py / generate_diagram.py），
#    用 pip install playwright 安装，python -m playwright install chromium 下载浏览器二进制。
$pwOk = $false
$eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
try { & $py -c "import playwright" 2>&1 | Out-Null; $pwOk = $LASTEXITCODE -eq 0 } catch { }
if (-not $pwOk) {
  Log "安装 playwright（pip）..."
  Pip-Install $py @("playwright")
  try { & $py -c "import playwright" 2>&1 | Out-Null; $pwOk = $LASTEXITCODE -eq 0 } catch { }
}
if ($pwOk) {
  $eapBrowser = $ErrorActionPreference; $ErrorActionPreference = "Continue"
  $r = ""
  $probe = @'
from playwright.sync_api import sync_playwright
try:
    pw = sync_playwright().start()
except Exception as e:
    print("PW_START_FAIL:" + str(e))
    exit(1)
for c in ["msedge", "chrome"]:
    try:
        b = pw.chromium.launch(headless=True, channel=c)
        b.close()
        print("OK_" + c)
        exit(0)
    except Exception as e:
        print("LAUNCH_FAIL_" + c + ":" + str(e))
try:
    b = pw.chromium.launch(headless=True)
    b.close()
    print("OK_bundled")
    exit(0)
except Exception as e:
    print("LAUNCH_FAIL_bundled:" + str(e))
exit(1)
'@
  $probeFile = Join-Path $env:TEMP "preflight_pw_probe.py"
  Set-Content -Path $probeFile -Value $probe -Encoding UTF8 -NoNewline
  try { $r = & $py $probeFile 2>&1 | Out-String } catch { }
  $ErrorActionPreference = $eapBrowser
  if ($r -match "OK_") {
    # 渠道或 bundled 真实可启动才判定就绪——仅凭 ms-playwright 目录存在不可靠（版本不匹配仍会 launch 失败）
    $script:browserReady = "ok"
    $chan = ($r -replace '.*OK_','').Trim()
    if ($chan -ne "bundled" -and $chan) { Log "✅ 复用系统浏览器 ${chan}，无需下载 Chromium" }
    else { Log "✅ Playwright bundled Chromium 可用" }
  }
  elseif ($r -match "PW_START_FAIL") {
    Log "playwright 初始化失败: $($r -replace '(?s).*PW_START_FAIL:',''.Trim())。回退缓存/下载。"
  }
  if ($script:browserReady -ne "ok") {
    Log "下载 Chromium（国内镜像加速）..."
    $eap2 = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    try {
      $env:PLAYWRIGHT_DOWNLOAD_HOST = "https://cdn.npmmirror.com/binaries/playwright"
      & $py -m playwright install chromium-headless-shell 2>&1 | Out-Null
      if ($LASTEXITCODE) { & $py -m playwright install chromium 2>&1 | Out-Null }
      # 下载后必须再次真实启动校验，成功才写标记
      $r2 = ""
      try { $r2 = & $py $probeFile 2>&1 | Out-String } catch { }
      if ($r2 -match "OK_") { $script:browserReady = "ok"; Log "✅ Chromium 下载完成且可启动" }
    } catch { } finally { $ErrorActionPreference = $eap2 }
  }
} else { Log "playwright 不可用(仅影响截图)" }
$ErrorActionPreference = $eap

# 3. 写标记（须 playwright 真实就绪后；否则并行 screenshot_guard 读标记就绪却缺依赖 → ModuleNotFoundError）
if ($script:browserReady -ne "ok") {
  Die "playwright 不可用——截图/封面/图表均依赖它。请按 SKILL.md Step 5 / references/windows-setup.md 补齐后重跑本脚本"
}
Add-OtherPythonDeps $py
Set-Content $Marker "ok=true`ngate=preflight`nplatform=windows`ncjk_match=Microsoft-YaHei(preinstalled)`nemoji=ok(preinstalled)`nfontconfig=n/a`ndeps=numpy,pillow,playwright`nts=$(Get-Date -Format o)`n" -Encoding UTF8 -NoNewline
Log "通过，已写入 $Marker（CJK+emoji 预装，Playwright: $script:browserReady）"
exit 0
