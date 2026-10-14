# sync-src: publish-work-to-gallery/scripts/install-hcloud.ps1
# install-hcloud.ps1 — Windows 一键安装华为云 KooCLI（hcloud），下载官方 zip 解压到「用户级统一工具目录」
#
# 用法（PowerShell）:
#   powershell -ExecutionPolicy Bypass -File install-hcloud.ps1                  # 装到 ensure-user-bindir.mjs 选定目录
#   powershell -ExecutionPolicy Bypass -File install-hcloud.ps1 -Dir D:\tools\hcloud   # 指定目录（覆盖默认）
#   powershell -ExecutionPolicy Bypass -File install-hcloud.ps1 -Force           # 已存在也重装
#
# 行为:
#   1. 默认目录 = `ensure-user-bindir.mjs` 输出（首选 %LOCALAPPDATA%\Programs\.huawei\bin）；
#      异常时回退 $env:TEMP\hcloud-cli
#   2. 目标目录已含 hcloud.exe 且 `version` 可执行 → 输出 #hcloud=<exe> 并 exit 0（幂等跳过，不下载）
#   3. 经官方 OBS URL 下载 huaweicloud-cli-windows-amd64.zip 到 $env:TEMP
#   4. 解压后定位 hcloud.exe，运行 `version` 首次确认（y）
#   5. 将安装目录写入「用户 PATH」（去重，新终端生效），后续调用可直接 `hcloud`，无需 --hcloud
#   6. 输出 #hcloud=<绝对路径>
#
# 退出码: 0=就绪/安装成功; 1=下载或解压或验证失败
# 说明: 本脚本只下载可执行体；AK/SK 由 hcloud configure 或环境变量另行配置
#       （见 references/troubleshooting.md#2-hcloud-credentials-not-configured）。

param(
    [string]$Dir = "",        # 安装目录，默认 ensure-user-bindir.mjs 选定目录
    [switch]$Force            # 已安装也重新下载安装
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ---- 参数 ----

# 下载源兜底：若下载失败（404/NoSuchBucket 等），参照官方文档更新此 URL:
#   https://support.huaweicloud.com/qs-hcli/hcli_02_003_01.html （在Windows系统上安装KooCLI）
$ZipUrl = "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-windows-amd64.zip"

if (-not $Dir) {
    $bindir = ""
    try {
        $bindir = (& node (Join-Path $PSScriptRoot "ensure-user-bindir.mjs") 2>$null |
            Select-String "#bindir=" | ForEach-Object {
                $line = ($_ -split "bindir=", 2)[1].Trim()
                # Strip trailing " level=..." attribute from ensure-user-bindir output
                if ($line -match '^(.+?)\s+level=') { $line = $matches[1].Trim() }
                $line
            } | Select-Object -First 1)
    } catch {}
    $Dir = if ($bindir) { $bindir } else { Join-Path $env:TEMP "hcloud-cli" }
}
$InstallDir = [System.IO.Path]::GetFullPath($Dir)
$Exe = Join-Path $InstallDir "hcloud.exe"

function Die($m) { Write-Host "[install-hcloud] X $m" -ForegroundColor Red; exit 1 }
function Log($m) { Write-Host "[install-hcloud] $m" }

# 将安装目录写入用户 PATH（持久，去重，不覆盖已有条目）。
# PATH 项可能有 %VAR% 等前缀，Normalize 时不做展开，去重采用「去尾斜杠 + 大小写不敏感」比较即可。
function Add-ToUserPath([string]$dir) {
    $target = $dir.TrimEnd('\')
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if (-not $userPath) { $userPath = "" }
    $exists = $false
    foreach ($e in ($userPath -split ';')) {
        if ($e -and ($e.TrimEnd('\') -ieq $target)) { $exists = $true; break }
    }
    if ($exists) {
        Log "安装目录已在用户 PATH，跳过写入：$target"
    } else {
        [Environment]::SetEnvironmentVariable('Path', $userPath.TrimEnd(';') + ';' + $target, 'User')
        $env:Path = $env:Path.TrimEnd(';') + ';' + $target   # 当前会话同步生效
        Log "已将安装目录写入用户 PATH（新终端/新进程生效）：$target"
    }
    # 临时目录持久性提示
    $tempFull = [System.IO.Path]::GetFullPath($env:TEMP).TrimEnd('\')
    if ($target.ToLowerInvariant().StartsWith($tempFull.ToLowerInvariant() + '\')) {
        Log "警告：安装目录位于系统临时目录，系统重启清理后该 PATH 条目将失效；如需持久安装请改用 -Dir 指定固定目录。"
    }
}

function Test-Hcloud([string]$exe) {
    if (-not (Test-Path $exe)) { return $false }
    try {
        & $exe version 2>&1 | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

# 1. 幂等跳过（优先检测 PATH 上可用 hcloud，其次目标目录副本）
$PathHcloud = Get-Command hcloud -ErrorAction SilentlyContinue
if (-not $Force) {
    if ($PathHcloud) {
        Log "PATH 上已有可用 hcloud（$($PathHcloud.Source)），跳过安装。加 -Force 可强制重装。"
        Write-Host "#hcloud=$($PathHcloud.Source)"
        exit 0
    }
    if ((Test-Path $Exe) -and (Test-Hcloud $Exe)) {
        Log "已安装 hcloud（$Exe），跳过下载。加 -Force 可强制重装。"
        Add-ToUserPath $InstallDir
        Write-Host "#hcloud=$Exe"
        exit 0
    }
}

# 2. 下载
$Zip = Join-Path $env:TEMP "hcloud-install-$PID.zip"
Log "下载 KooCLI Windows zip → $Zip"
try {
    Invoke-WebRequest -Uri $ZipUrl -OutFile $Zip -UseBasicParsing -TimeoutSec 120
} catch {
    Die "下载失败: $($_.Exception.Message)（若下载源失效，参照官方文档更新 URL: https://support.huaweicloud.com/qs-hcli/hcli_02_003_01.html）"
}
if (-not (Test-Path $Zip)) { Die "下载产物缺失: $Zip" }

# 3. 解压到临时目录，再移动 exe 到目标
$Tmp = Join-Path $env:TEMP "hcloud-unzip-$PID"
try {
    if (Test-Path $Tmp) { Remove-Item -Recurse -Force $Tmp }
    Expand-Archive -Path $Zip -DestinationPath $Tmp -Force
} catch {
    Die "解压失败: $($_.Exception.Message)"
}
$NewExe = Get-ChildItem $Tmp -Recurse -Filter "hcloud.exe" | Select-Object -First 1
if (-not $NewExe) { Die "解压产物中未找到 hcloud.exe（zip 结构异常）" }

# 4. 落位 + 验证
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Copy-Item $NewExe.FullName $Exe -Force
try {
    & $Exe version 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Die "hcloud version 验证失败（exit $LASTEXITCODE）" }
} catch {
    Die "hcloud version 验证失败: $($_.Exception.Message)"
}

# 5. 清理临时文件
try { Remove-Item -Recurse -Force $Tmp -ErrorAction SilentlyContinue } catch {}
try { Remove-Item -Force $Zip -ErrorAction SilentlyContinue } catch {}

# 6. 写入用户 PATH（新终端直接 `hcloud`）
Add-ToUserPath $InstallDir

Log "hcloud 安装完成并验证通过。"
Write-Host "#hcloud=$Exe"
exit 0
