# Vod Collector - AtomGit-GO installation script (Windows)
# Usage: powershell .\vod_install.ps1 [-RepoDir <path>] [-Sha256File <path>]
# Prints open-source notice, checks if installed, and installs if needed.
#
# 校验优先级：-Sha256File 显式文件 > <archive>.sha256 > vod_install_checksums.txt 清单
# > 均无则告警并回退源码构建（不再直接拒绝）；显式/随包校验不符仍 fail-closed。

param(
  [Parameter()]
  [string]$RepoDir = "",
  [Parameter()]
  [string]$Sha256File = ""
)

$BinDir = "$env:USERPROFILE\.local\bin"
$RepoUrl = "https://gitcode.com/weixin_45218422/AtomGit-GO.git"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ChecksumManifest = Join-Path $ScriptDir "vod_install_checksums.txt"

function Check-Installed {
  $existing = Get-ChildItem "$BinDir\atomcode-server*", "$BinDir\atomcode-login-server*" -ErrorAction SilentlyContinue
  return ($existing -ne $null -and $existing.Count -gt 0)
}

function Get-ManifestHash {
  param([string]$Name)
  if (-not (Test-Path $ChecksumManifest)) { return "" }
  foreach ($line in Get-Content $ChecksumManifest) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith("#")) { continue }
    $parts = $trimmed.Split([char[]]" 	", [System.StringSplitOptions]::RemoveEmptyEntries)
    if ($parts.Count -ge 2) {
      $entry = $parts[1].TrimStart("*")
      if ((Split-Path -Leaf $entry) -eq $Name) { return $parts[0] }
    }
  }
  return ""
}

# 返回 "ok" / "mismatch" / "unverified"
function Verify-Checksum {
  param([string]$File)
  $actual = (Get-FileHash $File -Algorithm SHA256).Hash.ToLower()
  $name = Split-Path -Leaf $File

  if ($Sha256File) {
    if (-not (Test-Path $Sha256File)) {
      Write-Error "[vod_install] ERROR: --sha256 file not found: $Sha256File"
      return "mismatch"
    }
    Write-Host "[vod_install] Verifying checksum (explicit: $Sha256File) ..."
    $expected = (Get-Content $Sha256File | Where-Object { $_.Trim() -and -not $_.Trim().StartsWith("#") } | Select-Object -First 1).Split(" ")[0].Trim()
  } elseif (Test-Path "$File.sha256") {
    Write-Host "[vod_install] Verifying checksum ($File.sha256) ..."
    $expected = (Get-Content "$File.sha256" | Select-Object -First 1).Split(" ")[0].Trim()
  } else {
    $expected = Get-ManifestHash -Name $name
    if (-not $expected) {
      Write-Warning "[vod_install] WARN: no checksum available for $name (no .sha256, no manifest entry, no -Sha256File)."
      return "unverified"
    }
    Write-Host "[vod_install] Verifying checksum (manifest: $ChecksumManifest) ..."
  }

  if ($expected.ToLower() -ne $actual) {
    Write-Error "[vod_install] ERROR: Checksum verification failed! Expected: $expected, Actual: $actual"
    return "mismatch"
  }
  Write-Host "[vod_install] Checksum verified."
  return "ok"
}

function Install-FromArchive {
  param([string]$Archive)
  $result = Verify-Checksum -File $Archive
  if ($result -eq "mismatch") {
    Write-Error "[vod_install] Aborting due to checksum failure."
    exit 1
  }
  if ($result -eq "unverified") {
    Write-Warning "[vod_install] No checksum source for the pre-built archive; skipping it (fail-closed)."
    return "unverified"
  }
  Write-Host "[vod_install] Extracting $Archive -> $BinDir ..."
  Expand-Archive -Path $Archive -DestinationPath $BinDir -Force
  return "ok"
}

function Install-FromSource {
  param([string]$RepoDir)
  Write-Host "[vod_install] Building binaries from $RepoDir ..."
  Push-Location $RepoDir
  try {
    $env:GOOS = "windows"
    $env:GOARCH = "amd64"

    go build -ldflags "-s -w" -o "$BinDir\atomcode-server.exe" .
    if (-not $?) { throw "Failed to build atomcode-server.exe" }

    if (Test-Path "$RepoDir\main.go") {
      go build -ldflags "-s -w" -o "$BinDir\atomcode-login.exe" .\main.go
      if (-not $?) { throw "Failed to build atomcode-login.exe" }
    }
  }
  finally {
    Remove-Item Env:GOOS, Env:GOARCH -ErrorAction SilentlyContinue
    Pop-Location
  }
}

function Install-Binaries {
  $null = New-Item -ItemType Directory -Force -Path $BinDir

  # Determine repo directory
  $repoDir = $RepoDir
  $cleanupRepo = $false
  if (-not $repoDir -or -not (Test-Path $repoDir)) {
    $tmpDir = Join-Path $env:TEMP "atomgit-go-$(Get-Random)"
    Write-Host "[vod_install] Cloning AtomGit-GO to $tmpDir ..."
    $null = git clone $RepoUrl $tmpDir 2>&1
    if (-not $?) {
      Write-Error "[vod_install] Failed to clone repository"
      exit 1
    }
    $repoDir = $tmpDir
    $cleanupRepo = $true
  }

  # Try pre-built archive first, fall back to source build
  $archive = Join-Path $repoDir "build\atomcode-login_windows_amd64.zip"
  $archiveResult = "unverified"
  if (Test-Path $archive) {
    $archiveResult = Install-FromArchive -Archive $archive
  } else {
    Write-Host "[vod_install] Pre-built archive not found: $archive" -ForegroundColor Yellow
  }
  if ($archiveResult -ne "ok") {
    Write-Host "[vod_install] Falling back to building from source..."
    $goCmd = Get-Command go -ErrorAction SilentlyContinue
    if ($goCmd -eq $null) {
      Write-Error "[vod_install] ERROR: Go toolchain not found and no verified pre-built archive available."
      Write-Host "[vod_install] Install Go >= 1.22 (https://go.dev/dl/) or pass -Sha256File <file> with a trusted checksum file." -ForegroundColor Red
      if ($cleanupRepo -and (Test-Path $repoDir)) {
        Remove-Item -Recurse -Force $repoDir
      }
      exit 1
    }
    Install-FromSource -RepoDir $repoDir
  }

  # 兼容补齐（上游不同包内容不一致：有的带 atomcode-server，有的带 atomcode-login-server）
  $serverExe = "$BinDir\atomcode-server.exe"
  $loginServerExe = "$BinDir\atomcode-login-server.exe"
  if ((Test-Path $serverExe) -and -not (Test-Path $loginServerExe)) {
    Copy-Item $serverExe $loginServerExe -Force
  } elseif ((Test-Path $loginServerExe) -and -not (Test-Path $serverExe)) {
    Copy-Item $loginServerExe $serverExe -Force
  }

  # Cleanup
  if ($cleanupRepo -and (Test-Path $repoDir)) {
    Remove-Item -Recurse -Force $repoDir
  }

  Write-Host "[vod_install] Done. Installed:"
  Get-ChildItem "$BinDir\atomcode-server.exe", "$BinDir\atomcode-login.exe", "$BinDir\atomcode-login-server.exe" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  $($_.FullName)"
  }
}

# ---- main ----
if (Check-Installed) {
  Write-Host "INSTALLED"
} else {
  Write-Host "NOT_FOUND — installing..."
  Install-Binaries
}
