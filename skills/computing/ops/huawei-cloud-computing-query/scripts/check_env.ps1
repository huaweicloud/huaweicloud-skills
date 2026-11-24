<#
华为云资源查询 - 环境检查前置脚本 (Windows PowerShell)

默认轻量模式：只做 Python 版本、脚本语法、SDK 可导入性和凭证存在性检查；
不创建 venv、不安装依赖、不调用云 API。缺少 AK/SK 时打印 SKIP 并以 0 退出。
严格模式：--full，安装依赖并调用 IAM 校验凭证；缺凭证 exit 2。

结果会缓存：通过默认 30 分钟，失败/跳过默认 5 分钟（.env_check_cache）。
强制重新检查：powershell -File check_env.ps1 --force 或设置 HW_ENV_CHECK_FORCE=1
缓存有效期：--ttl <秒> 或设置 HW_ENV_CHECK_TTL（0 表示禁用缓存）
#>

$mode = "light"
$passthru = @()

foreach ($arg in $args) {
    switch -Regex ($arg) {
        '^(-h|--help)$' {
            Write-Output "Usage: powershell -ExecutionPolicy Bypass -File scripts/check_env.ps1 [--full] [--force] [--ttl <seconds>]"
            Write-Output "Default: lightweight static check; works without credentials and exits 0."
            exit 0
        }
        '^--full$'  { $mode = "full" }
        '^--light$' { $mode = "light" }
        default     { $passthru += $arg }
    }
}

$ErrorActionPreference = "Stop"

Write-Output ""
Write-Output "=================================================="
Write-Output "  华为云资源查询 - 环境检查"
if ($mode -eq "full") {
    Write-Output "  （严格模式：安装依赖并校验凭证）"
} else {
    Write-Output "  （轻量模式：不创建 venv、不安装依赖；严格校验请使用 --full）"
}
Write-Output "=================================================="

# 步骤 1：检查 Python 是否存在
Write-Output ""
Write-Output "[1/3] 检查 Python 环境"

$pythonPath = $null
foreach ($cmd in @("python3", "python")) {
    $candidate = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($candidate) {
        $testVer = (& $candidate.Path --version 2>&1 | Out-String).Trim()
        if ($testVer -match "^Python \d+") {
            $pythonPath = $candidate
            break
        }
    }
}

if (-not $pythonPath) {
    Write-Output "FAIL: Python 未安装或不可用"
    Write-Output "环境未就绪，请先安装 Python 3.6+"
    exit 1
}

Write-Output "OK: 找到 Python: $($pythonPath.Path)"

# 步骤 2：检查 Python 版本
Write-Output ""
Write-Output "[2/3] 检查 Python 版本"

$pythonVersion = (& $pythonPath.Path --version 2>&1 | Out-String).Trim()
if (-not $pythonVersion) {
    Write-Output "FAIL: 无法获取 Python 版本"
    exit 1
}
$versionMatch = [regex]::Match($pythonVersion, 'Python (\d+)\.(\d+)')

if (-not $versionMatch.Success) {
    Write-Output "FAIL: 无法解析 Python 版本"
    exit 1
}

$major = [int]$versionMatch.Groups[1].Value
$minor = [int]$versionMatch.Groups[2].Value
$versionStr = "$major.$minor"

Write-Output "  当前版本: $versionStr"

if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 6)) {
    Write-Output "FAIL: Python $versionStr `< 3.6"
    Write-Output "环境未就绪，请升级 Python 到 3.6+"
    exit 1
}

Write-Output "OK: Python $versionStr >= 3.6"

# 步骤 3：调用 Python 详细检查
Write-Output ""
if ($mode -eq "full") {
    Write-Output "[3/3] 执行详细检查"
    $modeArg = "--full"
} else {
    Write-Output "[3/3] 执行轻量静态检查（不创建 venv、不安装依赖）"
    $modeArg = "--light"
}
Write-Output "--------------------------------------------------"

$scriptDir = Split-Path $MyInvocation.MyCommand.Definition -Parent
$pythonScript = Join-Path $scriptDir "ensure_env.py"

if (-not (Test-Path $pythonScript)) {
    Write-Output "FAIL: 未找到检查脚本: $pythonScript"
    exit 1
}

try {
    & $pythonPath.Path $pythonScript $modeArg @passthru
    $exitCode = $LASTEXITCODE
} catch {
    Write-Output "FAIL: Python 脚本执行异常: $_"
    exit 1
}

Write-Output ""
Write-Output "=================================================="

if ($mode -eq "light") {
    if ($exitCode -eq 0) {
        Write-Output "✓ 轻量环境检查通过（严格校验请执行 scripts/check_env.ps1 --full）"
        exit 0
    }
    Write-Output "✗ 轻量环境检查未通过（exit $exitCode），请按提示修复"
    exit $exitCode
}

if ($exitCode -eq 0) {
    Write-Output "✓ 环境检查通过"
    exit 0
} else {
    Write-Output "✗ 环境未就绪，请按提示修复"
    exit $exitCode
}