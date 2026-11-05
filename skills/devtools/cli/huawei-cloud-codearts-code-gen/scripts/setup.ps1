# CodeArts CLI environment check and setup script (PowerShell)
# Designed for automated Agent execution. Same JSON + exit code protocol as setup.sh.
#
# Exit codes:
#   0  - Environment ready
#   2  - Invalid arguments (missing / empty AK, SK)
#   10 - AK/SK configuration required
#   20 - User consent required for permission configuration
#   30 - CLI installation failed
#   40 - Network connection failed
#   50 - Authentication failed
#
# Output convention:
#   stdout carries exactly ONE JSON object and nothing else; every log line is
#   written to the error stream through [Console]::Error (Write-Host is avoided
#   because it still lands on stdout when the host output is redirected).
#
# Usage:
#   ./setup.ps1                           # Check environment
#   ./setup.ps1 --save-aksk "AK" "SK"     # Save AK/SK to the user environment and continue
#   ./setup.ps1 --ak "AK" --sk "SK"       # Use AK/SK temporarily (without saving)
#   ./setup.ps1 -ClearAksk                # Remove saved AK/SK (also --clear-aksk)
#
# Compatibility: Windows PowerShell 5.1 (no PS7-only syntax).
# Test hooks (defaults unchanged): CODEARTS_SETUP_MAX_RETRY, CODEARTS_SETUP_RETRY_DELAY,
# CODEARTS_CLI_ENV_SCOPE (User by default; "User" and "Process" are the only accepted
# values - anything else falls back to User with a warning), CODEARTS_BASHRC_PATH.

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Remaining
)

try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
} catch {
    # Non-fatal: encoding setup only affects non-ASCII output.
}

$MAX_RETRY = if ($env:CODEARTS_SETUP_MAX_RETRY) { [int]$env:CODEARTS_SETUP_MAX_RETRY } else { 3 }
$RETRY_DELAY = if ($env:CODEARTS_SETUP_RETRY_DELAY) { [int]$env:CODEARTS_SETUP_RETRY_DELAY } else { 5 }

# CODEARTS_CLI_ENV_SCOPE is a test hook (default "User"). Only "User" and "Process" are
# accepted (case-insensitive): every other value - Machine, LocalMachine, empty, typo -
# falls back to "User" with a warning on stderr. Without this gate an externally injected
# variable could push credential writes into the machine-wide scope or make -ClearAksk
# delete machine-wide variables. It never aborts the run, so the normal flow is unaffected.
$ENV_SCOPE = "User"
$RequestedEnvScope = [Environment]::GetEnvironmentVariable("CODEARTS_CLI_ENV_SCOPE", "Process")
if ($null -ne $RequestedEnvScope) {
    switch ($RequestedEnvScope.Trim().ToLowerInvariant()) {
        "user"    { $ENV_SCOPE = "User" }
        "process" { $ENV_SCOPE = "Process" }
        default {
            [Console]::Error.WriteLine("[WARN] CODEARTS_CLI_ENV_SCOPE='$RequestedEnvScope' is not supported (allowed: User, Process); falling back to User")
        }
    }
}

$CLI_PATH = "$env:USERPROFILE\.codeartsdoer\installers\codearts.cmd"
$INSTALL_URL = "https://cnnorth4-cloudide-marketplace.obs.cn-north-4.myhuaweicloud.com/codearts/cli_tui/install_script/install.ps1"
$PERMISSION_FILE = "$env:USERPROFILE\.codeartsdoer\cli-data\storage\permission\global.json"
$BASHRC_FILE = if ($env:CODEARTS_BASHRC_PATH) { $env:CODEARTS_BASHRC_PATH } else { "$env:USERPROFILE\.bashrc" }

# Same error signature as setup.sh: the exit code alone is never trusted.
$AUTH_ERROR_PATTERN = 'unauthorized|authentication|invalid.*key|unexpected error|ak/sk|access key|forbidden|expired'

# ============================================
# Logging (stderr only)
# ============================================
function Write-LogInfo  { [Console]::Error.WriteLine("[INFO] $($args -join ' ')") }
function Write-LogWarn  { [Console]::Error.WriteLine("[WARN] $($args -join ' ')") }
function Write-LogError { [Console]::Error.WriteLine("[ERROR] $($args -join ' ')") }

# ============================================
# JSON output helpers (stdout only)
# ============================================
function Write-JsonObject {
    param($Object)
    [Console]::Out.WriteLine(($Object | ConvertTo-Json -Compress -Depth 8))
}

# PowerShell loses a script's exit code when it is launched as
# `powershell -Command "& setup.ps1 ..."` (the host reports 1 instead). Recording the
# intended code on the host keeps the documented exit codes correct for -File and
# -Command alike.
function Exit-WithCode {
    param([int]$Code)
    try { $host.SetShouldExit($Code) } catch { }
    exit $Code
}

function Write-ErrorJson {
    param([int]$Code, [string]$Type, [string]$Message, [string]$Hint)
    # Human-readable companion line on stderr (#113-6): stdout keeps exactly one JSON.
    Write-LogError "$Message [$Type]. $Hint"
    Write-JsonObject ([ordered]@{
        status   = "error"
        code     = $Code
        type     = $Type
        message  = $Message
        fix_hint = $Hint
        options  = @(
            [ordered]@{ id = 1; label = "Continue fixing"; description = "Try to fix the issue manually" },
            [ordered]@{ id = 2; label = "Write code directly"; description = "Abandon CodeArts, agent writes code directly" }
        )
    })
    Exit-WithCode -Code $Code
}

# ============================================
# Save AK/SK to persistent environment variables
# ============================================
function Save-AkskConfig {
    param([string]$AkValue, [string]$SkValue)

    Write-LogInfo "Saving AK/SK to $ENV_SCOPE environment variables"
    [Environment]::SetEnvironmentVariable("CODEARTS_CLI_AK", $AkValue, $ENV_SCOPE)
    [Environment]::SetEnvironmentVariable("CODEARTS_CLI_SK", $SkValue, $ENV_SCOPE)
    Write-LogInfo "AK/SK saved"
}

# ============================================
# Clear AK/SK from the user environment (and from .bashrc when it exists)
# ============================================
function Clear-AkskConfig {
    Write-LogInfo "Clearing AK/SK"

    [Environment]::SetEnvironmentVariable("CODEARTS_CLI_AK", $null, $ENV_SCOPE)
    [Environment]::SetEnvironmentVariable("CODEARTS_CLI_SK", $null, $ENV_SCOPE)
    if ($ENV_SCOPE -eq "Process") {
        Remove-Item Env:CODEARTS_CLI_AK -ErrorAction SilentlyContinue
        Remove-Item Env:CODEARTS_CLI_SK -ErrorAction SilentlyContinue
    }

    if (Test-Path -LiteralPath $BASHRC_FILE) {
        try {
            $utf8 = New-Object System.Text.UTF8Encoding($false)
            $kept = @(Get-Content -LiteralPath $BASHRC_FILE -Encoding UTF8 |
                Where-Object { $_ -notmatch '^export CODEARTS_CLI_(AK|SK)=' })
            # Byte-faithful deletion: an untouched file keeps exactly its own content
            # (lines joined with LF and exactly one trailing newline); a file that only
            # held CODEARTS lines becomes empty rather than a lone newline.
            $content = ""
            if ($kept.Count -gt 0) { $content = ($kept -join "`n") + "`n" }
            $tmp = "$BASHRC_FILE.tmp.$([System.Guid]::NewGuid().ToString('N'))"
            [System.IO.File]::WriteAllText($tmp, $content, $utf8)
            Move-Item -LiteralPath $tmp -Destination $BASHRC_FILE -Force
            Write-LogInfo "AK/SK lines removed from $BASHRC_FILE"
        } catch {
            Write-LogWarn "Could not rewrite $BASHRC_FILE : $($_.Exception.Message)"
        }
    } else {
        Write-LogInfo "No $BASHRC_FILE found, nothing to clear there"
    }

    Write-JsonObject ([ordered]@{
        status  = "cleared"
        code    = 0
        message = "AK/SK removed from ~/.bashrc"
    })
    Exit-WithCode -Code 0
}

# ============================================
# Load AK/SK (priority: args > process env vars > persisted env vars)
# ============================================
function Load-Aksk {
    if ($SaveAksk) {
        $env:CODEARTS_CLI_AK = $ParseArgsAk
        $env:CODEARTS_CLI_SK = $ParseArgsSk
        Save-AkskConfig -AkValue $ParseArgsAk -SkValue $ParseArgsSk
        return $true
    }
    if ($AkGiven -and $SkGiven) {
        $env:CODEARTS_CLI_AK = $ParseArgsAk
        $env:CODEARTS_CLI_SK = $ParseArgsSk
        return $true
    }

    if ($env:CODEARTS_CLI_AK -and $env:CODEARTS_CLI_SK) {
        return $true
    }

    $storedAK = [Environment]::GetEnvironmentVariable("CODEARTS_CLI_AK", $ENV_SCOPE)
    $storedSK = [Environment]::GetEnvironmentVariable("CODEARTS_CLI_SK", $ENV_SCOPE)
    if ($storedAK -and $storedSK) {
        Write-LogInfo "Loading AK/SK from $ENV_SCOPE environment variables"
        $env:CODEARTS_CLI_AK = $storedAK
        $env:CODEARTS_CLI_SK = $storedSK
        return $true
    }

    return $false
}

# ============================================
# Download with retry
# ============================================
function Invoke-DownloadWithRetry {
    param([string]$Url)
    for ($attempt = 1; $attempt -le $MAX_RETRY; $attempt++) {
        Write-LogInfo "Download attempt $attempt/$MAX_RETRY..."
        try {
            $result = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 30
            return $result.Content
        } catch {
            if ($attempt -lt $MAX_RETRY) {
                Write-LogWarn "Download failed, retrying in ${RETRY_DELAY}s..."
                Start-Sleep -Seconds $RETRY_DELAY
            }
        }
    }
    return $null
}

# ============================================
# Step 1: CLI check and install
# ============================================
function Test-AndInstallCli {
    Write-LogInfo "Step 1: Checking CLI..."

    if (Test-Path -LiteralPath $CLI_PATH) {
        Write-LogInfo "CLI installed: $CLI_PATH"
        return
    }

    Write-LogInfo "CLI not installed, auto-installing..."

    $scriptContent = Invoke-DownloadWithRetry -Url $INSTALL_URL
    if (-not $scriptContent) {
        Write-ErrorJson -Code 30 -Type "download_failed" `
            -Message "CLI install script download failed (retried $MAX_RETRY times)" `
            -Hint "Check network, or manually download: $INSTALL_URL"
    }

    try {
        # The installer output is redirected to stderr so stdout keeps its JSON contract.
        Invoke-Expression $scriptContent 6>&1 | ForEach-Object { [Console]::Error.WriteLine("$_") }
        $env:PATH = "$env:USERPROFILE\.codeartsdoer\installers;$env:PATH"
    } catch {
        Write-ErrorJson -Code 30 -Type "install_failed" `
            -Message "CLI install script execution failed" `
            -Hint "Check system permissions, or review install logs"
    }

    if (Test-Path -LiteralPath $CLI_PATH) {
        Write-LogInfo "CLI installation complete"
    } else {
        Write-ErrorJson -Code 30 -Type "install_verify_failed" `
            -Message "CLI executable not found after installation" `
            -Hint "Check $env:USERPROFILE\.codeartsdoer\installers\ directory"
    }
}

# ============================================
# Step 2: AK/SK check
# ============================================
function Test-Aksk {
    Write-LogInfo "Step 2: Checking AK/SK..."

    if (-not (Load-Aksk)) {
        Write-LogWarn "AK/SK not configured"
        Write-JsonObject ([ordered]@{
            status  = "need_input"
            code    = 10
            type    = "aksk_required"
            message = "Huawei Cloud Access Key required"
            help    = [ordered]@{
                description = "Access Key is used to authenticate CodeArts CLI"
                tutorial_url = "https://support.huaweicloud.com/usermanual-iam/iam_02_0003.html"
                console_url = "https://console.huaweicloud.com/iam/?#/mine/accessKey"
                env_vars = @(
                    [ordered]@{ name = "CODEARTS_CLI_AK"; label = "Access Key ID"; description = "Huawei Cloud Access Key ID"; required = $true },
                    [ordered]@{ name = "CODEARTS_CLI_SK"; label = "Secret Access Key"; description = "Huawei Cloud Secret Access Key"; required = $true; secret = $true }
                )
                hint = "After providing AK/SK, the agent will save them. No need to re-enter. AK/SK are stored only in the local AI Shell environment variables and will NOT be uploaded to any external services, and you can either clear them manually or wait for them to be automatically released when the environment resources are reclaimed to delete them."
                save_command = "setup.ps1 --save-aksk AK SK"
            }
        })
        Exit-WithCode -Code 10
    }

    Write-LogInfo "AK/SK configured"
}

# ============================================
# Step 3: Permission check
#   Real JSON parsing (ConvertFrom-Json) so compact and pretty-printed files are
#   judged identically, and `permission`/`action` are matched inside the same object.
# ============================================
function Test-PermissionConfigured {
    if (-not (Test-Path -LiteralPath $PERMISSION_FILE)) {
        return $false
    }
    try {
        $raw = Get-Content -LiteralPath $PERMISSION_FILE -Raw -Encoding UTF8
        $data = $raw | ConvertFrom-Json
    } catch {
        Write-LogWarn "Could not parse $PERMISSION_FILE as JSON: $($_.Exception.Message)"
        return $false
    }

    $editAllowed = $false
    $writeAllowed = $false
    foreach ($entry in @($data)) {
        if ($null -eq $entry) { continue }
        if ($entry.permission -eq "edit" -and $entry.action -eq "allow") { $editAllowed = $true }
        if ($entry.permission -eq "write" -and $entry.action -eq "allow") { $writeAllowed = $true }
    }
    return ($editAllowed -and $writeAllowed)
}

function Test-Permission {
    Write-LogInfo "Step 3: Checking permissions..."

    if (-not (Test-PermissionConfigured)) {
        Write-LogWarn "Permissions not configured or insufficient"
        Write-JsonObject ([ordered]@{
            status  = "need_consent"
            code    = 20
            type    = "permission_required"
            message = "CodeArts CLI needs file read/write permission to generate code"
            consent = [ordered]@{
                description = "After configuration, CLI can create and modify files in the specified directory"
                risk = "Recommend limiting to the workspace directory, avoid global permissions"
                workspace = "$(Get-Location)"
            }
        })
        Exit-WithCode -Code 20
    }

    Write-LogInfo "Permissions configured"
}

# ============================================
# Step 4: Verify connection
#   Exit code alone is not trusted: empty output and error signatures are inspected
#   too. Authentication failures -> 50, everything else -> 40.
# ============================================
function Test-Connection {
    Write-LogInfo "Step 4: Verifying connection..."

    if (-not (Test-Path -LiteralPath $CLI_PATH)) {
        Write-ErrorJson -Code 30 -Type "cli_not_installed" `
            -Message "CodeArts CLI not found at $CLI_PATH" `
            -Hint "Re-run setup.ps1 to install the CLI"
    }

    for ($attempt = 1; $attempt -le $MAX_RETRY; $attempt++) {
        $output = ""
        $rc = 0
        try {
            $output = (& $CLI_PATH models 2>&1 | Out-String)
            $rc = $LASTEXITCODE
            if ($null -eq $rc) { $rc = 0 }
        } catch {
            $output = $_.Exception.Message
            $rc = 1
        }

        if ($rc -eq 0 -and $output.Trim().Length -gt 0) {
            if ($output -match $AUTH_ERROR_PATTERN) {
                Write-LogWarn "CLI exited 0 but the output looks like an authentication error"
            } else {
                Write-LogInfo "Connection successful"
                return
            }
        }

        if ($output -match $AUTH_ERROR_PATTERN) {
            Write-ErrorJson -Code 50 -Type "auth_failed" `
                -Message "Authentication failed, AK/SK is invalid" `
                -Hint "Please verify AK/SK is correct, or regenerate"
        }

        if ($rc -ne 0) {
            Write-LogWarn "Connection check failed (exit $rc, attempt $attempt/$MAX_RETRY)"
        } else {
            Write-LogWarn "Connection check returned no output (attempt $attempt/$MAX_RETRY)"
        }

        if ($attempt -lt $MAX_RETRY) {
            Write-LogWarn "Connection failed, retrying in ${RETRY_DELAY}s..."
            Start-Sleep -Seconds $RETRY_DELAY
        }
    }

    Write-ErrorJson -Code 40 -Type "network_failed" `
        -Message "Network connection failed (retried $MAX_RETRY times)" `
        -Hint "Check network connection and proxy settings"
}

# ============================================
# Main
# ============================================
function Main {
    Write-LogInfo "=== CodeArts CLI Environment Check ==="
    Write-LogInfo "System: Windows PowerShell"

    $env:PATH = "$env:USERPROFILE\.codeartsdoer\installers;$env:PATH"

    Test-AndInstallCli
    Test-Aksk
    Test-Permission
    Test-Connection

    Write-LogInfo "Environment ready, can execute code generation"
    Write-JsonObject ([ordered]@{
        status  = "ready"
        code    = 0
        message = "Environment setup complete, ready for code generation"
    })
    Exit-WithCode -Code 0
}

# ============================================
# Parse command line arguments
#   Everything is parsed by hand: PowerShell does not bind "--name" style flags to
#   parameters, and a missing value must produce the structured exit-2 JSON instead
#   of a PowerShell binding error (which would exit 1 with no JSON on stdout).
# ============================================
$SaveAksk = $false
$ClearAksk = $false
$AkGiven = $false
$SkGiven = $false
$ParseArgsAk = ""
$ParseArgsSk = ""

$total = 0
if ($null -ne $Remaining) { $total = @($Remaining).Count }

$index = 0
while ($index -lt $total) {
    $token = "$($Remaining[$index])".ToLowerInvariant()
    switch ($token) {
        { $_ -eq "--save-aksk" -or $_ -eq "-save-aksk" -or $_ -eq "-saveaksk" } {
            $SaveAksk = $true
            if (($index + 2) -ge $total) {
                Write-ErrorJson -Code 2 -Type "invalid_arguments" `
                    -Message "--save-aksk requires exactly 2 values: <AK> <SK> (got $($total - $index - 1))" `
                    -Hint "Usage: setup.ps1 --save-aksk <AK> <SK>"
            }
            $ParseArgsAk = $Remaining[$index + 1]
            $ParseArgsSk = $Remaining[$index + 2]
            $index += 2
        }
        { $_ -eq "--ak" -or $_ -eq "-ak" } {
            if (($index + 1) -ge $total) {
                Write-ErrorJson -Code 2 -Type "invalid_arguments" `
                    -Message "--ak requires a value" `
                    -Hint "Usage: setup.ps1 --ak <AK>"
            }
            $AkGiven = $true
            $ParseArgsAk = $Remaining[$index + 1]
            $index += 1
        }
        { $_ -eq "--sk" -or $_ -eq "-sk" } {
            if (($index + 1) -ge $total) {
                Write-ErrorJson -Code 2 -Type "invalid_arguments" `
                    -Message "--sk requires a value" `
                    -Hint "Usage: setup.ps1 --sk <SK>"
            }
            $SkGiven = $true
            $ParseArgsSk = $Remaining[$index + 1]
            $index += 1
        }
        { $_ -eq "--clear-aksk" -or $_ -eq "-clear-aksk" -or $_ -eq "-clearaksk" } {
            $ClearAksk = $true
        }
        default { }
    }
    $index += 1
}

# ============================================
# Validate arguments before touching the environment
# ============================================
if ($ClearAksk) {
    Clear-AkskConfig
}

if ($SaveAksk) {
    if ([string]::IsNullOrEmpty($ParseArgsAk) -or [string]::IsNullOrEmpty($ParseArgsSk)) {
        Write-ErrorJson -Code 2 -Type "empty_credentials" `
            -Message "AK and SK must not be empty" `
            -Hint "Usage: setup.ps1 --save-aksk <AK> <SK>"
    }
    if ($ParseArgsAk -match '["\\$`\r\n]') {
        Write-ErrorJson -Code 2 -Type "invalid_arguments" `
            -Message "AK contains characters that cannot be stored safely (quote, backslash, dollar, backtick or newline)" `
            -Hint "Usage: setup.ps1 --save-aksk <AK> <SK>"
    }
    if ($ParseArgsSk -match '["\\$`\r\n]') {
        Write-ErrorJson -Code 2 -Type "invalid_arguments" `
            -Message "SK contains characters that cannot be stored safely (quote, backslash, dollar, backtick or newline)" `
            -Hint "Usage: setup.ps1 --save-aksk <AK> <SK>"
    }
}

if ($AkGiven -and [string]::IsNullOrEmpty($ParseArgsAk)) {
    Write-ErrorJson -Code 2 -Type "empty_credentials" `
        -Message "--ak value must not be empty" `
        -Hint "Usage: setup.ps1 --ak <AK>"
}

if ($SkGiven -and [string]::IsNullOrEmpty($ParseArgsSk)) {
    Write-ErrorJson -Code 2 -Type "empty_credentials" `
        -Message "--sk value must not be empty" `
        -Hint "Usage: setup.ps1 --sk <SK>"
}

Main
