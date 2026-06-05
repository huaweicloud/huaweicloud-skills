<#
华为云资源查询 - 环境检查前置脚本 (Windows PowerShell)
#>

$ErrorActionPreference = "Stop"

Write-Output ""
Write-Output "=================================================="
Write-Output "  华为云资源查询 - 环境检查"
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
Write-Output "[3/3] 执行详细检查"
Write-Output "--------------------------------------------------"

$scriptDir = Split-Path $MyInvocation.MyCommand.Definition -Parent
$pythonScript = Join-Path $scriptDir "ensure_env.py"

if (-not (Test-Path $pythonScript)) {
    Write-Output "FAIL: 未找到检查脚本: $pythonScript"
    exit 1
}

try {
    & $pythonPath.Path $pythonScript
    $exitCode = $LASTEXITCODE
} catch {
    Write-Output "FAIL: Python 脚本执行异常: $_"
    exit 1
}

Write-Output ""
Write-Output "=================================================="

if ($exitCode -eq 0) {
    Write-Output "✓ 环境检查通过"
    exit 0
} else {
    Write-Output "✗ 环境未就绪，请按提示修复"
    exit $exitCode
}
