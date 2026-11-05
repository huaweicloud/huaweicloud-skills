# ensure_cli.ps1 — 确保 skill-quality-cli 就绪 (Windows 入口, issue #929)
# 用法: powershell -NoProfile -ExecutionPolicy Bypass -File .\ensure_cli.ps1 [-InstallDir <path>]
#
# 行为(与 ensure_cli.sh 保持一致):
#   已装可用 → 静默退出并把安装目录加入本次会话 PATH;
#   未装     → 调用 scripts/install_cli.py(跨平台安装入口, 强制 SHA256 校验;
#              Windows 无原生包时安装已校验包中的纯 Python fallback);
#   任何失败 → 显式警告后退出 0(不阻塞业务)。
#
# 为什么需要本文件: 官方 install_cli.sh 只映射 linux-x86_64 / linux-arm64, 而官方
# 清单当前只发布 linux-arm64, Windows x86_64 无法自动安装质量包装器(issue #929)。
#
# UTF-8: 官方 skill-quality-cli 的 cli_entry.py::cmd_run 用
#   subprocess.run(command, env=env, capture_output=True, text=True) 且未指定
#   encoding, 中文 Windows 下 text 模式回退 GBK, 子进程输出中文时抛
#   UnicodeDecodeError。PYTHONUTF8=1 让 Python 进入 UTF-8 模式(PEP 540)。

param(
  [Parameter()]
  [string]$InstallDir = ""
)

$ErrorActionPreference = "Continue"

# 强制 UTF-8(见文件头说明); 在调用 python / skill-quality-cli 之前设置
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $InstallDir) {
  $InstallDir = Join-Path $env:USERPROFILE ".local\bin"
}

function Test-CliReady {
  param([string]$Dir)
  $cmdLauncher = Join-Path $Dir "skill-quality-cli.cmd"
  $shLauncher = Join-Path $Dir "skill-quality-cli"
  if (Test-Path $cmdLauncher) {
    & $cmdLauncher version *> $null
    if ($LASTEXITCODE -eq 0) { return $true }
  }
  if (Test-Path $shLauncher) {
    & $shLauncher version *> $null
    if ($LASTEXITCODE -eq 0) { return $true }
  }
  return $false
}

function Add-ToSessionPath {
  param([string]$Dir)
  if ($env:PATH -notlike "*$Dir*") {
    $env:PATH = "$Dir;$env:PATH"
  }
}

# 1. 已安装且可用 → 静默退出
if (Test-CliReady -Dir $InstallDir) {
  Add-ToSessionPath -Dir $InstallDir
  exit 0
}

# 2. 安装: 委派跨平台 install_cli.py
$pyExe = $null
$pyPrefix = @()
foreach ($cand in @("py", "python", "python3")) {
  $found = Get-Command $cand -ErrorAction SilentlyContinue
  if ($found -ne $null) {
    $pyExe = $found.Source
    if ($cand -eq "py") { $pyPrefix = @("-3") }
    break
  }
}

$installer = Join-Path $ScriptDir "install_cli.py"

if ($pyExe -eq $null) {
  Write-Warning "[ensure_cli] 未找到 Python 3, 无法安装 skill-quality-cli(issue #929 跨平台入口需要 Python); 本 skill 降级运行, 不影响业务"
  exit 0
}
if (-not (Test-Path $installer)) {
  Write-Warning "[ensure_cli] 缺少 $installer; 本 skill 降级运行, 不影响业务"
  exit 0
}

$cliArgs = @()
$cliArgs += $pyPrefix
$cliArgs += $installer
$cliArgs += @("--install-dir", $InstallDir)

& $pyExe @cliArgs
if ($LASTEXITCODE -ne 0) {
  Write-Warning "[ensure_cli] skill-quality-cli 安装未完成(Windows 跨平台入口 install_cli.py: 网络/清单/校验); 本 skill 降级运行, 可稍后重试"
  exit 0
}

# 3. 收尾: PATH + 自检提示
Add-ToSessionPath -Dir $InstallDir
if (Test-CliReady -Dir $InstallDir) {
  Write-Host "[ensure_cli] skill-quality-cli 已就绪 ($InstallDir)"
} else {
  Write-Warning "[ensure_cli] 安装后未检测到 skill-quality-cli.cmd ($InstallDir); 本 skill 降级运行"
}
exit 0
