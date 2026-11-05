# CodeArts CLI permission configuration script (PowerShell)
# Same logic and exit codes as permission.sh
#
# Usage:
#   ./permission.ps1                      # Interactive, prompts user
#   ./permission.ps1 --agree /workspace    # Non-interactive, restricted to workspace
#   ./permission.ps1 --agree               # Non-interactive, global permissions
#
# Exit codes:
#   0 - Configuration successful
#   1 - User declined or parameter error
#
# Output convention:
#   stdout carries only the machine-readable result (`PERMISSION_CONFIGURED`
#   followed by the absolute path of global.json); every log line goes to stderr.
#
# Compatibility: Windows PowerShell 5.1 (no PS7-only syntax).
#   The JSON is built from objects and serialized with ConvertTo-Json, so a
#   workspace path containing quotes or backslashes can never produce invalid JSON,
#   and the file is written to a temp file and moved into place (never truncated
#   in place) as UTF-8 without BOM.

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Remaining
)

try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
} catch {
    # Non-fatal: encoding setup only affects non-ASCII output.
}

$PERMISSION_FILE = "$env:USERPROFILE\.codeartsdoer\cli-data\storage\permission\global.json"
$PERMISSION_DIR = Split-Path $PERMISSION_FILE -Parent

function Write-LogInfo { [Console]::Error.WriteLine("[INFO] $($args -join ' ')") }
function Write-LogWarn { [Console]::Error.WriteLine("[WARN] $($args -join ' ')") }
function Write-LogError { [Console]::Error.WriteLine("[ERROR] $($args -join ' ')") }

# `powershell -Command "& permission.ps1 ..."` loses a script's exit code; recording the
# intended code on the host keeps exit codes correct for -File and -Command alike.
function Exit-WithCode {
    param([int]$Code)
    try { $host.SetShouldExit($Code) } catch { }
    exit $Code
}

[Console]::Error.WriteLine("=== CodeArts CLI Permission Configuration ===")
[Console]::Error.WriteLine("")

# Show current config if it exists
if (Test-Path -LiteralPath $PERMISSION_FILE) {
    [Console]::Error.WriteLine("Current permission configuration:")
    Get-Content -LiteralPath $PERMISSION_FILE -Encoding UTF8 | ForEach-Object { [Console]::Error.WriteLine("$_") }
    [Console]::Error.WriteLine("")
}

# ============================================
# Parse arguments (PowerShell does not bind "--name" style flags by itself)
# ============================================
$Agree = $false
$Workspace = ""

$total = 0
if ($null -ne $Remaining) { $total = @($Remaining).Count }

$index = 0
while ($index -lt $total) {
    $token = "$($Remaining[$index])"
    $lower = $token.ToLowerInvariant()
    if ($lower -eq "--agree" -or $lower -eq "-agree") {
        $Agree = $true
    } elseif ($lower -eq "--workspace" -or $lower -eq "-workspace") {
        if (($index + 1) -lt $total) {
            $Workspace = $Remaining[$index + 1]
            $index += 1
        }
    } elseif (-not $token.StartsWith("-")) {
        if ([string]::IsNullOrEmpty($Workspace)) { $Workspace = $token }
    }
    $index += 1
}

# Without --agree mode, require interactive confirmation
if (-not $Agree) {
    $interactive = $true
    try {
        $null = [Console]::KeyAvailable
    } catch {
        $interactive = $false
    }

    if (-not $interactive) {
        [Console]::Error.WriteLine("Error: non-interactive environment requires --agree parameter")
        [Console]::Error.WriteLine("Usage: permission.ps1 --agree [workspace]")
        Exit-WithCode -Code 1
    }

    [Console]::Error.WriteLine("Permission configuration details:")
    [Console]::Error.WriteLine("   - CodeArts CLI needs file read/write permission to generate code")
    [Console]::Error.WriteLine("   - After configuration, CLI can create and modify files in the specified directory")
    [Console]::Error.WriteLine("   - Recommend limiting to the workspace directory")
    [Console]::Error.WriteLine("")

    $confirm = Read-Host "Authorize permission configuration? (y/N)"
    if ($confirm -notmatch '^[Yy]$') {
        [Console]::Error.WriteLine("User declined authorization")
        Exit-WithCode -Code 1
    }

    $Workspace = Read-Host "Restrict to directory (leave blank for global)"
}

# Generate permission configuration
if ([string]::IsNullOrEmpty($Workspace)) {
    $Pattern = "*"
    [Console]::Error.WriteLine("Configuring global permissions...")
} else {
    $Pattern = "$Workspace/*"
    [Console]::Error.WriteLine("Restricting permissions to: $Pattern")
}

# ============================================
# Build the permission entries as objects (never string templates)
# ============================================
$entries = New-Object System.Collections.ArrayList

function Add-PermEntry {
    param([string]$Permission, [string]$PatternValue, [string]$Action)
    [void]$script:entries.Add([ordered]@{
        permission = $Permission
        pattern    = $PatternValue
        action     = $Action
    })
}

Add-PermEntry "browser" "*" "ask"
Add-PermEntry "edit" $Pattern "allow"
Add-PermEntry "write" $Pattern "allow"
Add-PermEntry "webfetch" "*" "ask"
Add-PermEntry "websearch" "*" "allow"
Add-PermEntry "external_directory_write" "*" "ask"
Add-PermEntry "external_directory_read" "*" "allow"
Add-PermEntry "dotfile" "*" "ask"

if ([string]::IsNullOrEmpty($Workspace)) {
    Add-PermEntry "sandbox_risk_command" "ls *" "allow"
    Add-PermEntry "sandbox_risk_command" "mkdir *" "allow"
    Add-PermEntry "sandbox_risk_command" "cat *" "allow"
} else {
    Add-PermEntry "sandbox_risk_command" "ls $Workspace/*" "allow"
    Add-PermEntry "sandbox_risk_command" "mkdir $Workspace/*" "allow"
    Add-PermEntry "sandbox_risk_command" "mkdir -p $Workspace/*" "allow"
    Add-PermEntry "sandbox_risk_command" "cat $Workspace/*" "allow"
}

Add-PermEntry "sandbox_risk_command" "test *" "allow"
Add-PermEntry "sandbox_risk_command" "pwd" "allow"
Add-PermEntry "sandbox_risk_command" "which *" "allow"

$json = ConvertTo-Json -InputObject $entries.ToArray() -Depth 5
$json = $json -replace "`r`n", "`n"

# ============================================
# Ensure the directory exists, then write atomically as UTF-8 without BOM
# ============================================
if (-not (Test-Path -LiteralPath $PERMISSION_DIR)) {
    New-Item -ItemType Directory -Path $PERMISSION_DIR -Force | Out-Null
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$tmpFile = "$PERMISSION_FILE.tmp.$([System.Guid]::NewGuid().ToString('N'))"
[System.IO.File]::WriteAllText($tmpFile, ($json + "`n"), $utf8NoBom)
Move-Item -LiteralPath $tmpFile -Destination $PERMISSION_FILE -Force

[Console]::Error.WriteLine("")
[Console]::Error.WriteLine("Permission configuration complete")

# Output config file path (for Agent use)
[Console]::Out.WriteLine("PERMISSION_CONFIGURED")
[Console]::Out.WriteLine($PERMISSION_FILE)
