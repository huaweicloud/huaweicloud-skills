# CodeArts CLI environment check and setup script (PowerShell)
# Designed for automated Agent execution. Same JSON + exit code protocol as setup.sh.
#
# Exit codes:
#   0  - Environment ready
#   10 - AK/SK configuration required
#   20 - User consent required for permission configuration
#   30 - CLI installation failed
#   40 - Network connection failed
#   50 - Authentication failed
#
# Usage:
#   ./setup.ps1                           # Check environment
#   ./setup.ps1 --save-aksk "AK" "SK"     # Save AK/SK to user env vars and continue
#   ./setup.ps1 --ak "AK" --sk "SK"       # Use AK/SK temporarily

param(
    [switch]$SaveAksk,
    [string]$Ak,
    [string]$Sk,
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Remaining
)

# Parse --save-aksk positional arguments
$SaveAkskAk = ""
$SaveAkskSk = ""
for ($i = 0; $i -lt $Remaining.Count; $i++) {
    if ($Remaining[$i] -eq "--save-aksk" -and $i + 2 -lt $Remaining.Count) {
        $SaveAksk = $true
        $SaveAkskAk = $Remaining[$i + 1]
        $SaveAkskSk = $Remaining[$i + 2]
        break
    }
}

$MAX_RETRY = 3
$RETRY_DELAY = 5
$CLI_PATH = "$env:USERPROFILE\.codeartsdoer\installers\codearts.cmd"
$INSTALL_URL = "https://cnnorth4-cloudide-marketplace.obs.cn-north-4.myhuaweicloud.com/codearts/cli_tui/install_script/install.ps1"
$PERMISSION_FILE = "$env:USERPROFILE\.codeartsdoer\cli-data\storage\permission\global.json"

# Log output to stderr
function Write-LogInfo  { Write-Host "[INFO] $args" -ForegroundColor Green }
function Write-LogWarn  { Write-Host "[WARN] $args" -ForegroundColor Yellow }
function Write-LogError { Write-Host "[ERROR] $args" -ForegroundColor Red }

# Output JSON error and exit
function Write-ErrorJson {
    param([int]$Code, [string]$Type, [string]$Message, [string]$Hint)
    @{
        status = "error"
        code = $Code
        type = $Type
        message = $Message
        fix_hint = $Hint
        options = @(
            @{id=1; label="Continue fixing"; description="Try to fix the issue manually"},
            @{id=2; label="Write code directly"; description="Abandon CodeArts, agent writes code directly"}
        )
    } | ConvertTo-Json -Compress
    exit $Code
}

# ============================================
# Save AK/SK to user environment variables (Windows persistence)
# ============================================
function Save-AkskConfig {
    param([string]$AkValue, [string]$SkValue)

    Write-LogInfo "Saving AK/SK to user environment variables"
    [Environment]::SetEnvironmentVariable("CODEARTS_CLI_AK", $AkValue, "User")
    [Environment]::SetEnvironmentVariable("CODEARTS_CLI_SK", $SkValue, "User")
    Write-LogInfo "AK/SK saved"
}

# ============================================
# Load AK/SK (priority: args > process env vars > user env vars)
# ============================================
function Load-Aksk {
    # Priority 1: command line args
    if ($SaveAksk -and $SaveAkskAk -and $SaveAkskSk) {
        $env:CODEARTS_CLI_AK = $SaveAkskAk
        $env:CODEARTS_CLI_SK = $SaveAkskSk
        Save-AkskConfig -AkValue $SaveAkskAk -SkValue $SaveAkskSk
        return $true
    }
    if ($Ak -and $Sk) {
        $env:CODEARTS_CLI_AK = $Ak
        $env:CODEARTS_CLI_SK = $Sk
        return $true
    }

    # Priority 2: process environment variables
    if ($env:CODEARTS_CLI_AK -and $env:CODEARTS_CLI_SK) {
        return $true
    }

    # Priority 3: user environment variables
    $userAK = [Environment]::GetEnvironmentVariable("CODEARTS_CLI_AK", "User")
    $userSK = [Environment]::GetEnvironmentVariable("CODEARTS_CLI_SK", "User")
    if ($userAK -and $userSK) {
        Write-LogInfo "Loading AK/SK from user environment variables"
        $env:CODEARTS_CLI_AK = $userAK
        $env:CODEARTS_CLI_SK = $userSK
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

    if (Test-Path $CLI_PATH) {
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
        Invoke-Expression $scriptContent
        $env:PATH = "$env:USERPROFILE\.codeartsdoer\installers;$env:PATH"
    } catch {
        Write-ErrorJson -Code 30 -Type "install_failed" `
            -Message "CLI install script execution failed" `
            -Hint "Check system permissions, or review install logs"
    }

    if (Test-Path $CLI_PATH) {
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
        @{
            status = "need_input"
            code = 10
            type = "aksk_required"
            message = "Huawei Cloud Access Key required"
            help = @{
                description = "Access Key is used to authenticate CodeArts CLI"
                tutorial_url = "https://support.huaweicloud.com/usermanual-iam/iam_02_0003.html"
                console_url = "https://console.huaweicloud.com/iam/?#/mine/accessKey"
                env_vars = @(
                    @{name="CODEARTS_CLI_AK"; label="Access Key ID"; description="Huawei Cloud Access Key ID"; required=$true},
                    @{name="CODEARTS_CLI_SK"; label="Secret Access Key"; description="Huawei Cloud Secret Access Key"; required=$true; secret=$true}
                )
                hint = "After providing AK/SK, the agent will save them. No need to re-enter. AK/SK are stored only in the local AI Shell environment variables and will NOT be uploaded to any external services, and you can either clear them manually or wait for them to be automatically released when the environment resources are reclaimed to delete them."
                save_command = "setup.ps1 --save-aksk AK SK"
            }
        } | ConvertTo-Json -Compress
        exit 10
    }

    Write-LogInfo "AK/SK configured"
}

# ============================================
# Step 3: Permission check
# ============================================
function Test-Permission {
    Write-LogInfo "Step 3: Checking permissions..."

    $needConfig = $false
    if (-not (Test-Path $PERMISSION_FILE)) {
        $needConfig = $true
    } else {
        $content = Get-Content $PERMISSION_FILE -Raw
        if (-not ($content -match '"permission"\s*:\s*"edit"' -and $content -match '"action"\s*:\s*"allow"') -or
            -not ($content -match '"permission"\s*:\s*"write"' -and $content -match '"action"\s*:\s*"allow"')) {
            $needConfig = $true
        }
    }

    if ($needConfig) {
        Write-LogWarn "Permissions not configured or insufficient"
        @{
            status = "need_consent"
            code = 20
            type = "permission_required"
            message = "CodeArts CLI needs file read/write permission to generate code"
            consent = @{
                description = "After configuration, CLI can create and modify files in the specified directory"
                risk = "Recommend limiting to the workspace directory, avoid global permissions"
                workspace = "$(Get-Location)"
            }
        } | ConvertTo-Json -Compress
        exit 20
    }

    Write-LogInfo "Permissions configured"
}

# ============================================
# Step 4: Verify connection
# ============================================
function Test-Connection {
    Write-LogInfo "Step 4: Verifying connection..."

    for ($attempt = 1; $attempt -le $MAX_RETRY; $attempt++) {
        try {
            $output = & $CLI_PATH models 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-LogInfo "Connection successful"
                return
            }
        } catch {
            $output = $_.Exception.Message
        }

        if ($output -match "unauthorized|authentication|invalid.*key") {
            Write-ErrorJson -Code 50 -Type "auth_failed" `
                -Message "Authentication failed, AK/SK is invalid" `
                -Hint "Please verify AK/SK is correct, or regenerate"
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
    @{
        status = "ready"
        code = 0
        message = "Environment setup complete, ready for code generation"
    } | ConvertTo-Json -Compress
    exit 0
}

Main
