# Vod Collector - AtomGit-GO installation script (Windows)
# Usage: powershell .\vod_install.ps1 [-RepoDir <path>]
# Prints open-source notice, checks if installed, and installs if needed.

param(
  [Parameter()]
  [string]$RepoDir = ""
)

$BinDir = "$env:USERPROFILE\.local\bin"
$RepoUrl = "https://gitcode.com/weixin_45218422/AtomGit-GO.git"

function Check-Installed {
  $existing = Get-ChildItem "$BinDir\atomcode-server*", "$BinDir\atomcode-login-server*" -ErrorAction SilentlyContinue
  return ($existing -ne $null -and $existing.Count -gt 0)
}

function Verify-Checksum {
  param([string]$File)
  $checksumFile = "$File.sha256"
  if (-not (Test-Path $checksumFile)) {
    Write-Host "[vod_install] WARNING: No checksum file found at $checksumFile, skipping verification" -ForegroundColor Yellow
    return $true
  }
  Write-Host "[vod_install] Verifying checksum..."
  $expected = (Get-Content $checksumFile | Select-Object -First 1).Split(" ")[0].Trim()
  $actual = (Get-FileHash $File -Algorithm SHA256).Hash.ToLower()
  if ($expected.ToLower() -ne $actual) {
    Write-Error "[vod_install] ERROR: Checksum verification failed! Expected: $expected, Actual: $actual"
    return $false
  }
  Write-Host "[vod_install] Checksum verified."
  return $true
}

function Install-FromArchive {
  param([string]$Archive)
  if (-not (Verify-Checksum -File $Archive)) {
    Write-Error "[vod_install] Aborting due to checksum failure."
    exit 1
  }
  Write-Host "[vod_install] Extracting $Archive -> $BinDir ..."
  Expand-Archive -Path $Archive -DestinationPath $BinDir -Force
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
  if (Test-Path $archive) {
    Install-FromArchive -Archive $archive
  } else {
    Write-Host "[vod_install] Pre-built archive not found: $archive" -ForegroundColor Yellow
    Write-Host "[vod_install] Falling back to building from source..."
    $goCmd = Get-Command go -ErrorAction SilentlyContinue
    if ($goCmd -eq $null) {
      Write-Error "[vod_install] ERROR: Go toolchain not found and no pre-built archive available."
      Write-Host "[vod_install] Install Go (https://go.dev/dl/) or provide a pre-built archive." -ForegroundColor Red
      if ($cleanupRepo -and (Test-Path $repoDir)) {
        Remove-Item -Recurse -Force $repoDir
      }
      exit 1
    }
    Install-FromSource -RepoDir $repoDir
  }

  # Symlink for compatibility
  $serverExe = "$BinDir\atomcode-server.exe"
  $loginServerExe = "$BinDir\atomcode-login-server.exe"
  if ((Test-Path $serverExe) -and -not (Test-Path $loginServerExe)) {
    Copy-Item $serverExe $loginServerExe -Force
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
