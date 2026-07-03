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
  $existing = Get-ChildItem "$BinDir\atomcode-server*" -ErrorAction SilentlyContinue
  return ($existing -ne $null)
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

  # Build from source
  Write-Host "[vod_install] Building binaries from $repoDir ..."
  Push-Location $repoDir
  try {
    $env:GOOS = "windows"
    $env:GOARCH = "amd64"

    go build -ldflags "-s -w" -o "$BinDir\atomcode-server.exe" .
    if (-not $?) { throw "Failed to build atomcode-server.exe" }

    go build -ldflags "-s -w" -o "$BinDir\atomcode-login.exe" .\main.go
    if (-not $?) { throw "Failed to build atomcode-login.exe" }
  }
  finally {
    Remove-Item Env:GOOS, Env:GOARCH -ErrorAction SilentlyContinue
    Pop-Location
  }

  # Cleanup
  if ($cleanupRepo -and (Test-Path $repoDir)) {
    Remove-Item -Recurse -Force $repoDir
  }

  Write-Host "[vod_install] Done. Installed:"
  Get-ChildItem "$BinDir\atomcode-server.exe", "$BinDir\atomcode-login.exe" | ForEach-Object {
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
