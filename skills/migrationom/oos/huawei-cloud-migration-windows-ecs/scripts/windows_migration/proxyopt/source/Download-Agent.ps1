<#
.SYNOPSIS
    源端 Windows 下载脚本 — 通过 Squid 代理并发下载迁移工具包。
    支持高并发（~100台主机同时下载）、校验、重试、断点续传、进度显示。

.DESCRIPTION
    在源端 Windows 主机上执行，通过 Squid 代理从沙箱 HTTP 服务下载文件。
    由于 Squid 已预缓存，实际流量走缓存命中，不回源到 OBS。
    支持断点续传: 如果本地已存在部分文件，通过 HTTP Range 请求继续下载。

.PARAMETER ProxyHost
    Squid 代理服务器 IP 地址

.PARAMETER ProxyPort
    Squid 代理端口 (默认 3128)

.PARAMETER SandboxHost
    沙箱 HTTP 服务 IP 地址

.PARAMETER SandboxPort
    沙箱 HTTP 服务端口 (默认 8080)

.PARAMETER Concurrent
    并发下载数 (默认 5)

.PARAMETER RetryCount
    每个文件重试次数 (默认 3)

.PARAMETER TimeoutSec
    单文件下载超时秒数 (默认 300)

.PARAMETER VerifyHash
    启用 SHA256 校验 (需要服务端提供 .sha256 校验文件)

.EXAMPLE
    .\Download-Agent.ps1 -ProxyHost 10.0.1.50 -SandboxHost 10.0.1.10
    .\Download-Agent.ps1 -ProxyHost 10.0.1.50 -SandboxHost 10.0.1.10 -Concurrent 10
    .\Download-Agent.ps1 -ProxyHost 10.0.1.50 -SandboxHost 10.0.1.10 -VerifyHash
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ProxyHost,

    [int]$ProxyPort = 3128,

    [Parameter(Mandatory=$true)]
    [string]$SandboxHost,

    [int]$SandboxPort = 8080,

    [string]$FileList = "",

    [string]$DownloadDir = "C:\auto_agent_opt\downloads",

    [int]$Concurrent = 5,

    [int]$RetryCount = 3,

    [int]$TimeoutSec = 300,

    [switch]$VerifyHash
)

# ── 初始化 ────────────────────────────────────────────────
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$LogFile = Join-Path $DownloadDir "download_agent.log"
function Write-Log {
    param([string]$Level, [string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$ts [$Level] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -ErrorAction SilentlyContinue
}

if (-not (Test-Path $DownloadDir)) {
    New-Item -ItemType Directory -Path $DownloadDir -Force | Out-Null
}

Write-Log "INFO" "========== 源端下载脚本启动 =========="
Write-Log "INFO" "代理: http://$ProxyHost`:$ProxyPort"
Write-Log "INFO" "沙箱: http://$SandboxHost`:$SandboxPort"
Write-Log "INFO" "下载目录: $DownloadDir"
Write-Log "INFO" "并发数: $Concurrent"
Write-Log "INFO" "重试次数: $RetryCount"
Write-Log "INFO" "断点续传: 已启用"
if ($VerifyHash) { Write-Log "INFO" "SHA256 校验: 已启用" }

$ProxyUrl = "http://${ProxyHost}:${ProxyPort}"
$BaseUrl = "http://${SandboxHost}:${SandboxPort}"

# ── 获取文件列表 ──────────────────────────────────────────
function Get-FileList {
    if ($FileList -ne "") {
        Write-Log "INFO" "使用指定文件列表: $FileList"
        return $FileList.Split(",") | ForEach-Object { $_.Trim() }
    }

    Write-Log "INFO" "从服务端获取文件列表..."
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/" -Proxy $ProxyUrl -TimeoutSec 30 -UseBasicParsing
        $files = [regex]::Matches($response.Content, 'href="([^"]+)"') |
                 ForEach-Object { $_.Groups[1].Value } |
                 Where-Object { $_ -ne "../" -and $_ -ne "/" -and $_ -notmatch "/$" }
        Write-Log "INFO" "获取到 $($files.Count) 个文件"
        return $files
    } catch {
        Write-Log "ERROR" "获取文件列表失败: $_"
        exit 1
    }
}

# ── 断点续传下载核心逻辑 (用于 RunspacePool 内联) ─────────
# 以下脚本块在 RunspacePool 中执行，包含完整的断点续传 + SHA256 校验

$downloadScriptBlock = {
    param($FileName, $ProxyUrl, $BaseUrl, $DownloadDir, $RetryCount, $TimeoutSec, $LogFile, $VerifyHash)

    function Write-LogInline {
        param([string]$Level, [string]$Message)
        $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $line = "$ts [$Level] $Message"
        Add-Content -Path $LogFile -Value $line -ErrorAction SilentlyContinue
    }

    $url = "$BaseUrl/$FileName"
    $localPath = Join-Path $DownloadDir $FileName
    $localDir = Split-Path $localPath -Parent

    if (-not (Test-Path $localDir)) {
        New-Item -ItemType Directory -Path $localDir -Force | Out-Null
    }

    for ($attempt = 1; $attempt -le $RetryCount; $attempt++) {
        try {
            $startTime = Get-Date
            $ProgressPreference = "SilentlyContinue"

            # ── 断点续传: 检查本地已有文件 ──
            $resumeOffset = 0
            if (Test-Path $localPath) {
                $existingSize = (Get-Item $localPath).Length
                if ($existingSize -gt 0) {
                    try {
                        $headResp = Invoke-WebRequest -Uri $url -Method Head -Proxy $ProxyUrl `
                            -TimeoutSec 30 -UseBasicParsing
                        $remoteSize = [int64]$headResp.Headers["Content-Length"]
                        if ($existingSize -lt $remoteSize) {
                            $resumeOffset = $existingSize
                            Write-LogInline "INFO" "断点续传: $FileName 从偏移 $resumeOffset 继续"
                        } elseif ($existingSize -eq $remoteSize) {
                            $sizeMB = [math]::Round($existingSize / 1MB, 2)
                            Write-LogInline "INFO" "文件已完整，跳过: $FileName (${sizeMB} MB)"
                            return @{ File = $FileName; Success = $true; SizeMB = $sizeMB; Elapsed = 0 }
                        }
                    } catch {
                        Remove-Item $localPath -Force -ErrorAction SilentlyContinue
                    }
                }
            }

            # ── 执行下载 (全量或续传) ──
            if ($resumeOffset -gt 0) {
                $tempPath = "$localPath.tmp"
                Copy-Item $localPath $tempPath -Force
                $headers = @{ "Range" = "bytes=$resumeOffset-" }
                $response = Invoke-WebRequest -Uri $url -Headers $headers -Proxy $ProxyUrl `
                    -TimeoutSec $TimeoutSec -UseBasicParsing
                $fileStream = [System.IO.FileStream]::new($tempPath, 'Append', 'Write')
                $responseStream = $response.RawContentStream
                $buffer = New-Object byte[] 65536
                while ($true) {
                    $read = $responseStream.Read($buffer, 0, $buffer.Length)
                    if ($read -eq 0) { break }
                    $fileStream.Write($buffer, 0, $read)
                }
                $fileStream.Close()
                $responseStream.Close()
                Move-Item $tempPath $localPath -Force
            } else {
                Invoke-WebRequest -Uri $url -OutFile $localPath -Proxy $ProxyUrl `
                    -TimeoutSec $TimeoutSec -UseBasicParsing
            }

            $elapsed = ((Get-Date) - $startTime).TotalSeconds
            $fileSize = (Get-Item $localPath).Length
            $sizeMB = [math]::Round($fileSize / 1MB, 2)

            if ($fileSize -eq 0) {
                Write-LogInline "WARN" "文件大小为0: $FileName"
                if ($attempt -lt $RetryCount) { continue }
                return @{ File = $FileName; Success = $false; SizeMB = 0; Elapsed = $elapsed }
            }

            # ── SHA256 校验 ──
            if ($VerifyHash) {
                $hashUrl = "$url.sha256"
                try {
                    $expectedHash = (Invoke-WebRequest -Uri $hashUrl -Proxy $ProxyUrl `
                        -TimeoutSec 30 -UseBasicParsing).Content.Trim().Split(" ")[0].ToLower()
                    $actualHash = (Get-FileHash $localPath -Algorithm SHA256).Hash.ToLower()
                    if ($actualHash -ne $expectedHash) {
                        Write-LogInline "WARN" "SHA256 校验失败: $FileName"
                        Remove-Item $localPath -Force -ErrorAction SilentlyContinue
                        if ($attempt -lt $RetryCount) { continue }
                        return @{ File = $FileName; Success = $false; SizeMB = 0; Elapsed = $elapsed }
                    }
                    Write-LogInline "INFO" "SHA256 校验通过: $FileName"
                } catch {
                    Write-LogInline "DEBUG" "无 SHA256 校验文件，跳过: $FileName"
                }
            }

            Write-LogInline "INFO" "下载成功: $FileName (${sizeMB} MB, ${elapsed}s)"
            return @{ File = $FileName; Success = $true; SizeMB = $sizeMB; Elapsed = $elapsed }
        } catch {
            Write-LogInline "WARN" "下载失败 (attempt $attempt/$RetryCount): $FileName - $_"
            if ($attempt -lt $RetryCount) { Start-Sleep -Seconds 5 }
        }
    }

    return @{ File = $FileName; Success = $false; SizeMB = 0; Elapsed = 0 }
}

# ── 并发下载 ──────────────────────────────────────────────
function Download-AllFiles {
    param([string[]]$Files)

    $total = $Files.Count
    Write-Log "INFO" "开始下载 $total 个文件，并发数 $Concurrent"

    $runspacePool = [runspacefactory]::CreateRunspacePool(1, $Concurrent)
    $runspacePool.Open()

    $jobs = @()
    foreach ($file in $Files) {
        $powershell = [powershell]::Create()
        $powershell.RunspacePool = $runspacePool
        $null = $powershell.AddScript($downloadScriptBlock)
        $null = $powershell.AddArgument($file)
        $null = $powershell.AddArgument($ProxyUrl)
        $null = $powershell.AddArgument($BaseUrl)
        $null = $powershell.AddArgument($DownloadDir)
        $null = $powershell.AddArgument($RetryCount)
        $null = $powershell.AddArgument($TimeoutSec)
        $null = $powershell.AddArgument($LogFile)
        $null = $powershell.AddArgument($VerifyHash)

        $handle = $powershell.BeginInvoke()
        $jobs += @{ Handle = $handle; PowerShell = $powershell; File = $file }
    }

    # 等待所有任务完成
    $successCount = 0
    $failCount = 0
    $totalSizeMB = 0
    $completed = 0

    foreach ($job in $jobs) {
        $result = $job.PowerShell.EndInvoke($job.Handle)
        $job.PowerShell.Dispose()
        $completed++

        if ($result.Success) {
            $successCount++
            $totalSizeMB += $result.SizeMB
            Write-Host "[$completed/$total] OK: $($result.File) ($($result.SizeMB) MB)" -ForegroundColor Green
        } else {
            $failCount++
            Write-Host "[$completed/$total] FAIL: $($result.File)" -ForegroundColor Red
        }
    }

    $runspacePool.Close()
    $runspacePool.Dispose()

    return @{ Total = $total; Success = $successCount; Failed = $failCount; TotalSizeMB = $totalSizeMB }
}

# ── 主流程 ────────────────────────────────────────────────
$startTime = Get-Date

# 1. 获取文件列表
$files = Get-FileList
if ($files.Count -eq 0) {
    Write-Log "ERROR" "没有文件需要下载"
    exit 1
}

# 2. 并发下载
$summary = Download-AllFiles -Files $files

# 3. 汇总
$totalElapsed = ((Get-Date) - $startTime).TotalSeconds
Write-Log "INFO" "========== 下载汇总 =========="
Write-Log "INFO" "总文件数: $($summary.Total)"
Write-Log "INFO" "成功: $($summary.Success)"
Write-Log "INFO" "失败: $($summary.Failed)"
Write-Log "INFO" "总大小: $([math]::Round($summary.TotalSizeMB, 2)) MB"
Write-Log "INFO" "总耗时: $([math]::Round($totalElapsed, 1))s"
Write-Log "INFO" "日志文件: $LogFile"

if ($summary.Failed -gt 0) {
    Write-Log "ERROR" "有 $($summary.Failed) 个文件下载失败，请检查日志"
    exit 1
} else {
    Write-Log "INFO" "所有文件下载成功！"
    exit 0
}
