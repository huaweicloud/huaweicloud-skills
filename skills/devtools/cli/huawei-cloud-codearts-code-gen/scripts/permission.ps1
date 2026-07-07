# CodeArts CLI permission configuration script (PowerShell)
# Same logic and exit codes as permission.sh
#
# Usage:
#   ./permission.ps1                     # Interactive, prompts user
#   ./permission.ps1 --agree /workspace   # Non-interactive, restricted to workspace
#   ./permission.ps1 --agree              # Non-interactive, global permissions
#
# Exit codes:
#   0 - Configuration successful
#   1 - User declined or parameter error

param(
    [switch]$Agree,
    [string]$Workspace
)

$PERMISSION_FILE = "$env:USERPROFILE\.codeartsdoer\cli-data\storage\permission\global.json"
$PERMISSION_DIR = Split-Path $PERMISSION_FILE -Parent

Write-Host "=== CodeArts CLI Permission Configuration ===" -ForegroundColor Cyan

# Show current config
if (Test-Path $PERMISSION_FILE) {
    Write-Host "Current permission configuration:"
    Get-Content $PERMISSION_FILE | Write-Host
    Write-Host ""
}

# Without --agree mode, require interactive confirmation
if (-not $Agree) {
    try {
        $dummy = [Console]::KeyAvailable
    } catch {
        Write-Host "Error: non-interactive environment requires --agree parameter" -ForegroundColor Red
        Write-Host "Usage: permission.ps1 --agree [workspace]"
        exit 1
    }

    Write-Host "Permission configuration details:"
    Write-Host "   - CodeArts CLI needs file read/write permission to generate code"
    Write-Host "   - After configuration, CLI can create and modify files in the specified directory"
    Write-Host "   - Recommend limiting to the workspace directory"
    Write-Host ""

    $confirm = Read-Host "Authorize permission configuration? (y/N)"
    if ($confirm -notmatch '^[Yy]$') {
        Write-Host "User declined authorization"
        exit 1
    }

    $Workspace = Read-Host "Restrict to directory (leave blank for global)"
}

# Generate permission configuration
if (-not $Workspace) {
    $Pattern = "*"
    Write-Host "Configuring global permissions..."
} else {
    $Pattern = "$Workspace/*"
    Write-Host "Restricting permissions to: $Pattern"
}

# Ensure directory exists
if (-not (Test-Path $PERMISSION_DIR)) {
    New-Item -ItemType Directory -Path $PERMISSION_DIR -Force | Out-Null
}

# Write permission configuration
if (-not $Workspace) {
    @'
[
  {"permission": "browser", "pattern": "*", "action": "ask"},
  {"permission": "edit", "pattern": "*", "action": "allow"},
  {"permission": "write", "pattern": "*", "action": "allow"},
  {"permission": "webfetch", "pattern": "*", "action": "ask"},
  {"permission": "websearch", "pattern": "*", "action": "allow"},
  {"permission": "external_directory_write", "pattern": "*", "action": "ask"},
  {"permission": "external_directory_read", "pattern": "*", "action": "allow"},
  {"permission": "dotfile", "pattern": "*", "action": "ask"},
  {"permission": "sandbox_risk_command", "pattern": "ls *", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "mkdir *", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "cat *", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "test *", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "pwd", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "which *", "action": "allow"}
]
'@ | Set-Content -Path $PERMISSION_FILE
} else {
    @"
[
  {"permission": "browser", "pattern": "*", "action": "ask"},
  {"permission": "edit", "pattern": "$Pattern", "action": "allow"},
  {"permission": "write", "pattern": "$Pattern", "action": "allow"},
  {"permission": "webfetch", "pattern": "*", "action": "ask"},
  {"permission": "websearch", "pattern": "*", "action": "allow"},
  {"permission": "external_directory_write", "pattern": "*", "action": "ask"},
  {"permission": "external_directory_read", "pattern": "*", "action": "allow"},
  {"permission": "dotfile", "pattern": "*", "action": "ask"},
  {"permission": "sandbox_risk_command", "pattern": "ls $Workspace/*", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "mkdir $Workspace/*", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "mkdir -p $Workspace/*", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "cat $Workspace/*", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "test *", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "pwd", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "which *", "action": "allow"}
]
"@ | Set-Content -Path $PERMISSION_FILE
}

Write-Host ""
Write-Host "Permission configuration complete" -ForegroundColor Green
Write-Host "PERMISSION_CONFIGURED"
Write-Host $PERMISSION_FILE
