<#
.SYNOPSIS
  clouddocs-cli Windows 一键安装脚本（无需管理员权限）

.DESCRIPTION
  把 clouddocs-cli.exe 安装到用户目录（默认 %USERPROFILE%\bin）并加入用户 PATH，同时：
    1) 若脚本同目录有 SHA256SUMS，则校验安装包完整性；
    2) 打印包内环境信息（PACKAGE-INFO.json：版本 / 环境 profile / 默认 host / 默认 client_id）；
    3) 运行时 dry-run 核对"生效 host"与包内默认是否一致（不一致会提示可能被本机配置/环境变量覆盖）。
  用法：
    1) 把本脚本与 clouddocs-cli-<版本>[-<环境>]-windows-amd64.zip（或 clouddocs-cli.exe）放在同一文件夹；
    2) 在 PowerShell 中执行：
         powershell -ExecutionPolicy Bypass -File install-windows.ps1
       或右键本文件 -> “使用 PowerShell 运行”。

.PARAMETER Package
  指定安装包完整路径；缺省时自动查找脚本同目录下的 clouddocs-cli-*.zip（优先）或 clouddocs-cli.exe。

.PARAMETER BinDir
  安装目录；缺省 %USERPROFILE%\bin。

.PARAMETER SkipPath
  不修改用户 PATH（例如由企业统一管理 PATH 时）。

.PARAMETER ServiceHost
  显式指定服务地址（覆盖包内置默认），提供后自动执行 clouddocs-cli config init --host <地址>。
  环境包（-m3sdv / -m3prod）通常无需指定。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File install-windows.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File install-windows.ps1 -Package D:\share\clouddocs-cli-0.5.4-m3prod-windows-amd64.zip
#>
param(
  [string]$Package,
  [string]$BinDir = (Join-Path $env:USERPROFILE 'bin'),
  [switch]$SkipPath,
  [string]$ServiceHost = ''
)

$ErrorActionPreference = 'Stop'

Write-Host '=== clouddocs-cli 安装 ===' -ForegroundColor Cyan

# ---- 1. 定位安装包 ----
if (-not $Package) {
  $candidate = Get-ChildItem -Path $PSScriptRoot -Filter 'clouddocs-cli*.zip' -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -First 1
  if (-not $candidate) {
    $candidate = Get-ChildItem -Path $PSScriptRoot -Filter 'clouddocs-cli.exe' -ErrorAction SilentlyContinue |
      Select-Object -First 1
  }
  if ($candidate) { $Package = $candidate.FullName }
}
if (-not $Package -or -not (Test-Path $Package)) {
  Write-Host '✖ 找不到安装包。请把 clouddocs-cli-*-windows-amd64.zip（或 clouddocs-cli.exe）与本脚本放在同一文件夹后重试。' -ForegroundColor Red
  Write-Host '  获取渠道：按安装指南「安装包位置与获取渠道」从内部软件仓获取后放入同目录重试。' -ForegroundColor Yellow
  Write-Host '  安装指南路径：<技能基目录>/bin/cli-installation-guide.md' -ForegroundColor Yellow
  exit 1
}
Write-Host ("安装包: " + $Package)

# ---- 2. 安装包完整性校验（同目录存在 SHA256SUMS 时） ----
if ($Package -like '*.zip') {
  $shaFile = Join-Path $PSScriptRoot 'SHA256SUMS'
  if (Test-Path $shaFile) {
    $pkgName = Split-Path $Package -Leaf
    $entry = Select-String -Path $shaFile -Pattern $pkgName -SimpleMatch | Select-Object -First 1
    if ($entry) {
      $expected = ($entry.Line -split '\s+')[0].ToLower()
      $actual = (Get-FileHash -Path $Package -Algorithm SHA256).Hash.ToLower()
      if ($expected -eq $actual) {
        Write-Host '✔ 安装包校验和匹配（SHA256SUMS）' -ForegroundColor Green
      } else {
        Write-Host '✖ 安装包校验和不匹配：文件可能损坏或被篡改，已中止安装。' -ForegroundColor Red
        Write-Host ("  期望: " + $expected)
        Write-Host ("  实际: " + $actual)
        exit 1
      }
    } else {
      Write-Host ("⚠ SHA256SUMS 中未找到 " + $pkgName + "，跳过校验") -ForegroundColor Yellow
    }
  } else {
    Write-Host '· 未找到 SHA256SUMS，跳过完整性校验（可选）' -ForegroundColor DarkGray
  }
}

# ---- 3. 解压、读取包内环境信息、放置 exe ----
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
$exe = Join-Path $BinDir 'clouddocs-cli.exe'
$pkgInfo = $null
if ($Package -like '*.zip') {
  $tmp = Join-Path $env:TEMP ("clouddocs-install-" + [guid]::NewGuid().ToString('N'))
  Expand-Archive -Path $Package -DestinationPath $tmp -Force
  $inner = Get-ChildItem -Path $tmp -Filter 'clouddocs-cli.exe' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $inner) {
    Write-Host '✖ 压缩包内未找到 clouddocs-cli.exe。' -ForegroundColor Red
    Remove-Item $tmp -Recurse -Force
    exit 1
  }
  $infoFile = Get-ChildItem -Path $tmp -Filter 'PACKAGE-INFO.json' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($infoFile) {
    try { $pkgInfo = Get-Content -Path $infoFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $pkgInfo = $null }
  }
  Copy-Item -Path $inner.FullName -Destination $exe -Force
  Remove-Item $tmp -Recurse -Force
} else {
  Copy-Item -Path $Package -Destination $exe -Force
}
Write-Host ("✔ 已安装: " + $exe) -ForegroundColor Green

# ---- 4. 打印包内环境信息 ----
if ($pkgInfo) {
  Write-Host '--- 包内环境信息（PACKAGE-INFO.json）---' -ForegroundColor Cyan
  Write-Host ('  版本          : ' + $pkgInfo.version)
  if ($pkgInfo.profile) {
    Write-Host ('  环境          : ' + $pkgInfo.profile) -ForegroundColor Green
  } else {
    Write-Host '  环境          : <通用包（无环境后缀，用源码内置默认）>'
  }
  Write-Host ('  默认 host     : ' + $pkgInfo.host)
  Write-Host ('  默认 client_id: ' + $pkgInfo.client_id)
  Write-Host ('  构建          : ' + $pkgInfo.commit + ' @ ' + $pkgInfo.published_at)
} else {
  Write-Host '⚠ 包内未找到 PACKAGE-INFO.json（可能是改造前的旧包），无法确认该包属于哪个环境。' -ForegroundColor Yellow
  Write-Host '  请向分发者核对包名中的环境后缀（-m3sdv 测试 / -m3prod 生产）。' -ForegroundColor Yellow
}

# ---- 5. 加入用户 PATH ----
if (-not $SkipPath) {
  $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
  if ($userPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable('Path', "$BinDir;$userPath", 'User')
    Write-Host ("✔ 已加入用户 PATH: " + $BinDir) -ForegroundColor Green
    Write-Host '  ⚠ 请新开一个终端/PowerShell 窗口（PATH 在进程启动时读取），旧窗口可能仍提示找不到命令。' -ForegroundColor Yellow
  } else {
    Write-Host ('✔ PATH 已包含: ' + $BinDir)
  }
}

# ---- 6. 验证可执行（用 cmd 规避 PS 5.1 对原生 stderr 重定向的终止错误） ----
& cmd /c "`"$exe`" --help >nul 2>&1"
if ($LASTEXITCODE -eq 0) {
  Write-Host '✔ 验证通过：clouddocs-cli 可执行。' -ForegroundColor Green
} else {
  Write-Host '✖ 验证失败，请检查安装目录与文件。' -ForegroundColor Red
  exit 1
}

# ---- 7. 运行时核对"生效 host"（dry-run，不发起真实请求） ----
$dry = & cmd /c "`"$exe`" space +fetch --only_personal true --dry-run 2>nul" | Out-String
$m = [regex]::Match($dry, '"url"\s*:\s*"([^"]+)"')
if ($m.Success) {
  $actualHost = ([uri]$m.Groups[1].Value).GetLeftPart([System.UriPartial]::Authority)
  Write-Host ('✔ 运行时生效 host: ' + $actualHost) -ForegroundColor Green
  if ($pkgInfo -and $pkgInfo.host -and $actualHost -ne $pkgInfo.host) {
    Write-Host ('  ⚠ 与包内默认 host（' + $pkgInfo.host + '）不一致：本机可能已有 ~/.clouddocs/config.json' +
                ' 或设置了环境变量 CLOUDDOC_HOST（两者优先级均高于内置默认）。') -ForegroundColor Yellow
    Write-Host '    如需恢复包内默认：删除 ~/.clouddocs/config.json 中的 base_url，或清除 CLOUDDOC_HOST。' -ForegroundColor Yellow
  }
} else {
  Write-Host '⚠ 未能取得 dry-run 请求 URL，跳过 host 运行时核对。' -ForegroundColor Yellow
}

# ---- 8. 后续配置指引 ----
Write-Host ''
Write-Host '=== 下一步（必做）===' -ForegroundColor Cyan
if ($ServiceHost) {
  & cmd /c "`"$exe`" config init --host $ServiceHost >nul 2>&1"
  if ($LASTEXITCODE -ne 0) {
    Write-Host '✖ 配置失败，请手动执行: clouddocs-cli config init --host <服务地址>' -ForegroundColor Red
  } else {
    Write-Host ('  1) 服务地址：已按参数配置为 ' + $ServiceHost)
  }
} elseif ($pkgInfo -and $pkgInfo.profile) {
  Write-Host ('  1) 服务地址：已内置该环境默认值（' + $pkgInfo.host + '），无需 config init')
} else {
  Write-Host '  1) 配置服务地址：'
  Write-Host '       clouddocs-cli config init --host <公司内部云文档服务地址>'
}
Write-Host '  2) 登录（浏览器打开验证链接点授权）：'
Write-Host '       clouddocs-cli auth login'
Write-Host '  3) 确认就绪：'
Write-Host '       clouddocs-cli auth status        # 显示 ready 即完成'
Write-Host ''
Write-Host '详细说明见技能基目录 bin/cli-installation-guide.md。' -ForegroundColor DarkGray

exit 0
