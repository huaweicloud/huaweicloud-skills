#!/usr/bin/env powershell
# precheck.ps1 — PowerShell 版本的统一环境检查脚本
# 用法: skill action=exec, command ["powershell", "skill://scripts/precheck.ps1"]
# 退出码: 0=全部通过, 1=有检查未通过

#Requires -Version 5.1

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# --- 配置 ---
$HLoudCmd = "hcloud"
$Region = if ($env:HUAWEI_CLOUD_REGION) { $env:HUAWEI_CLOUD_REGION } else { "" }
$OutputMode = if ($env:CHECK_OUTPUT_MODE) { $env:CHECK_OUTPUT_MODE } else { "summary" }

# --- 颜色 ---
function Get-Color {
  param([string]$Type)
  if ($Host.UI.SupportsVirtualTerminal -or $PSVersionTable.PSVersion.Major -ge 7) {
    switch ($Type) {
      "Red"    { "`e[31m" }
      "Green"  { "`e[32m" }
      "Yellow" { "`e[33m" }
      "Reset"  { "`e[0m" }
      default  { "" }
    }
  } else {
    return ""
  }
}

$RED    = Get-Color "Red"
$GREEN  = Get-Color "Green"
$YELLOW = Get-Color "Yellow"
$RESET  = Get-Color "Reset"

# --- 全局状态 ---
$script:FAILED = $false
$script:CHECKS_PASSED = 0
$script:CHECKS_FAILED = 0
$script:CHECKS_SKIPPED = 0

# --- 辅助函数 ---
function Write-Info  { Write-Host "[INFO]  $args" -ForegroundColor Cyan 2>&1 }
function Write-Pass  { Write-Host "[PASS]  $args" -ForegroundColor Green 2>&1 }
function Write-Fail  { Write-Host "[FAIL]  $args" -ForegroundColor Red 2>&1; $script:FAILED = $true; $script:CHECKS_FAILED++ }
function Write-Ok    { if ($OutputMode -eq "detail") { Write-Host "[OK]    $args" -ForegroundColor DarkGray 2>&1 } }
function Write-Skip  { $script:CHECKS_SKIPPED++ }

function Invoke-SafeCommand {
  param(
    [string]$Name,
    [scriptblock]$Command,
    [string]$ErrorMessage
  )

  try {
    $result = & $Command 2>&1
    $exitCode = $LASTEXITCODE
    if ($exitCode -and $exitCode -ne 0) {
      Write-Fail "$Name failed (exit $exitCode): $ErrorMessage"
      return $null
    }
    return $result
  } catch {
    Write-Fail "$Name 抛出异常: $($_.Exception.Message)"
    return $null
  }
}

# --- 单项检查 ---
function Test-HcloudInstalled {
  $name = "hcloud 命令"
  $found = Get-Command $HLoudCmd -ErrorAction SilentlyContinue
  if (-not $found) {
    Write-Fail "${RED}hcloud 未安装或不在 PATH 中${RESET}"
    return $false
  }
  Write-Ok "${GREEN}hcloud 命令存在: $($found.Source)${RESET}"
  $script:CHECKS_PASSED++
  return $true
}

function Test-HcloudVersion {
  $name = "hcloud version"

  # 首次运行会提示接受条款，使用管道输入 "y"
  $output = @"
y
"@ | & $HLoudCmd version 2>&1
  $exitCode = $LASTEXITCODE

  if ($output -match "(?i)(error|exception|command not found|no permission)") {
    Write-Fail "${RED}hcloud version 执行失败: $($output | Select-Object -First 3)${RESET}"
    return $false
  }

  $versionLine = $output | Select-String -Pattern "(版本|version|koocli)" | Select-Object -First 1
  if ($versionLine) {
    Write-Ok "${GREEN}$($versionLine.Line)${RESET}"
  } else {
    Write-Ok "${GREEN}hcloud 可正常执行${RESET}"
  }
  $script:CHECKS_PASSED++
  return $true
}

function Test-HcloudConfigure {
  $name = "hcloud configure list"
  $output = & $HLoudCmd configure list 2>&1
  $exitCode = $LASTEXITCODE

  if ($output -match "(?i)(error|exception|not configure|未配置|not found)") {
    Write-Fail "${RED}凭证未配置或不可用: $(($output | Select-Object -First 1).ToString().Substring(0, [Math]::Min(120, ($output | Select-Object -First 1).ToString().Length)))${RESET}"
    return $false
  }

  Write-Ok "${GREEN}凭证已配置${RESET}"
  $script:CHECKS_PASSED++
  return $true
}

function Get-ConfiguredRegion {
  # 用 --cli-query="region" 直接拿值（KooCLI JMESPath 过滤，避免 JSON 解析 + PS 5.1 解析 bug）
  # PowerShell 下输出可能包成 "cn-north-7" 或 "cn-north-7", 等形式，需清理
  $raw = & $HLoudCmd configure show --cli-query="region" 2>&1
  if ($raw -is [array]) { $raw = $raw -join "`n" }
  $region = ([string]$raw).Trim() -replace '^"', '' -replace '"$', '' -replace '",$', ''
  return $region
}

function Test-RegionConfigured {
  $name = "region 配置"

  if (-not $Region) {
    $Region = Get-ConfiguredRegion
  }

  if (-not $Region) {
    Write-Fail "${RED}未检测到 region，请通过 'hcloud configure init' 配置或设置 HUAWEI_CLOUD_REGION 环境变量${RESET}"
    return $false
  }

  Write-Ok "${GREEN}region=$Region${RESET}"
  $script:CHECKS_PASSED++
  return $true
}

function Test-OptVerseConnectivity {
  $name = "OptVerse 连通性"

  if (-not $Region) {
    Write-Info "跳过连通性检查（region 未确定）"
    Write-Skip
    return $true
  }

  # 用 --cli-query="payload.list" 拿 JSON 数组（"[...]" 开头即代表连通）
  $buckets = & $HLoudCmd OptVerse ListBuckets --cli-region=$Region --cli-query="payload.list" 2>&1
  if ($buckets -is [array]) { $buckets = $buckets -join "`n" }
  $bucketsStr = ([string]$buckets).Trim()

  if ($bucketsStr.StartsWith("[")) {
    Write-Ok "${GREEN}OptVerse API 连通性正常${RESET}"
    $script:CHECKS_PASSED++
    return $true
  } else {
    Write-Fail "${RED}OptVerse 连通性检查失败: $bucketsStr${RESET}"
    return $false
  }
}

# --- 汇总输出 ---
function Write-Summary {
  Write-Host ""
  if (-not $script:FAILED) {
    $total = $script:CHECKS_PASSED + $script:CHECKS_SKIPPED
    Write-Host "${GREEN}✅ 环境检查通过 ($script:CHECKS_PASSED/$total 项通过)${RESET}" -ForegroundColor Green 2>&1
  } else {
    Write-Host "${YELLOW}⚠️  环境检查未全部通过 ($script:CHECKS_FAILED 项失败, $script:CHECKS_PASSED 项通过)${RESET}" -ForegroundColor Yellow 2>&1
    Write-Host "${YELLOW}  请修复上述 [FAIL] 项后重新执行${RESET}" -ForegroundColor Yellow 2>&1
  }
  Write-Host ""
}

# --- 主流程 ---
function Main {
  # 自动 extend PATH（PowerShell 进程可能不继承外层 shell 的 PATH，找不到 hcloud）
  if (-not (Get-Command $HLoudCmd -ErrorAction SilentlyContinue)) {
    $userName = $env:USERNAME
    $userProfile = $env:USERPROFILE
    foreach ($candidate in @(
      "$userProfile\.huawei\bin",
      "C:\Users\$userName\.huawei\bin",
      "C:\Program Files\KooCLI\bin",
      "C:\Program Files\Huawei\hcloud\bin"
    )) {
      if ($candidate -and (Test-Path -Path (Join-Path $candidate "$HLoudCmd.exe") -ErrorAction SilentlyContinue)) {
        $env:PATH = "$candidate;$env:PATH"
        Write-Info "${YELLOW}自动 extend PATH: $candidate (PowerShell 不继承外层 shell PATH)${RESET}"
        break
      }
    }
  }

  # 尝试自动读取 region
  if (-not $Region) {
    $Region = Get-ConfiguredRegion
  }

  Write-Host "🔍 开始环境检查..." -ForegroundColor Cyan 2>&1
  Write-Host "   region=$Region" -ForegroundColor DarkGray 2>&1
  Write-Host "" 2>&1

  Test-HcloudInstalled
  Test-HcloudVersion
  Test-HcloudConfigure
  Test-RegionConfigured
  Test-OptVerseConnectivity

  Write-Summary

  if ($script:FAILED) {
    exit 1
  } else {
    exit 0
  }
}

Main