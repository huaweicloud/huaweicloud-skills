# =============================================================================
# codearts_run.ps1 - stable contract wrapper around the external `codearts` CLI
#
# Windows counterpart of codearts_run.sh. Same frozen interface, same exit
# codes and the same stdout protocol (CG-CONTEXT.md 2.3):
#
#   #113-3  `codearts models` without AK/SK exited 0        -> creds pre-check, exit 10
#   #113-4  `codearts run --format json` failure exited 0    -> exit-code + stdout checks
#   #113-5  `--format json` wrote non-JSON text to stdout    -> JSONL validation, exit 60
#   #113-8  CLI error text did not match auth detection      -> error classification 50/40
#   #113-14 `codearts run -f FILE` was broken                -> -f is inlined by the wrapper
#
# Usage (Windows PowerShell 5.1 or PowerShell 7):
#   powershell -File codearts_run.ps1 models
#   powershell -File codearts_run.ps1 run --format json -m "<provider/model>" [-f FILE]... "<task>"
#
#   `--file` is equivalent to `-f`; `--file=<path>` is accepted as well.
#   The `<task>` description must be the LAST positional argument; attachments are
#   appended to it as markdown fenced blocks. `-f`/`--file` and their file
#   arguments are never forwarded to the CLI.
#
# Exit codes:
#   0   success                    - CLI stdout is forwarded verbatim
#   1   cli_failed                 - CLI exited non-zero (not auth / not network)
#   10  aksk_required              - CODEARTS_CLI_AK / CODEARTS_CLI_SK missing
#   30  cli_not_installed          - codearts executable not found
#   40  network_failed             - timeout / connection / DNS / proxy errors
#   50  auth_failed                - unauthorized / authentication / invalid key
#   60  output_contract_violation  - CLI exited 0 but produced an unusable payload
#   60  attachment_failed          - -f file missing, unreadable or empty
#
# stdout contract: success -> CLI stdout verbatim; failure -> exactly one JSON
# object; all logs go to stderr.
#
# Environment:
#   CODEARTS_CLI_BIN  - path (or command name) of the codearts CLI.
#                       Default: $HOME\.codeartsdoer\installers\codearts.cmd
#   CODEARTS_CLI_AK   - Huawei Cloud Access Key; fallback: ~/.bashrc
#   CODEARTS_CLI_SK   - Huawei Cloud Secret Key; fallback: ~/.bashrc
# =============================================================================

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Remaining
)

$ErrorActionPreference = "Continue"

$Script:LogPrefix = "[codearts_run]"

# Classifier patterns (issue #113-8: unify detection instead of trusting CLI wording)
$Script:AuthRe = 'unauthorized|authentication|invalid.*key|ak/sk'
$Script:NetRe = 'timeout|timed out|connection|network|resolve|proxy|refused'
$Script:ErrHeadRe = '^\s*\[?(error|unexpected error|failed|failure|exception|unauthorized|authentication|invalid[\s_-]+(ak|access[\s_-]*key)|ak/sk|fatal|panic|timeout|timed out|connection (refused|failed|reset|error)|network (error|unreachable|is unreachable))'

function Write-Log {
    param([string]$Message)
    [Console]::Error.WriteLine("$Script:LogPrefix $Message")
}

# Failure output: exactly one JSON object on stdout, then exit with its code.
function Write-JsonError {
    param(
        [int]$Code,
        [string]$Type,
        [string]$Message,
        [string]$Hint
    )
    $obj = [ordered]@{
        status   = "error"
        code     = $Code
        type     = $Type
        message  = $Message
        fix_hint = $Hint
    }
    [Console]::Out.WriteLine(($obj | ConvertTo-Json -Compress -Depth 5))
    exit $Code
}

# #113-3: no credentials -> need_input, never call the CLI.
function Write-NeedInput {
    param([string]$Message)
    $obj = [ordered]@{
        status  = "need_input"
        code    = 10
        type    = "aksk_required"
        message = $Message
    }
    [Console]::Out.WriteLine(($obj | ConvertTo-Json -Compress -Depth 5))
    exit 10
}

function Get-HomeDir {
    if ($env:HOME) { return $env:HOME }
    if ($env:USERPROFILE) { return $env:USERPROFILE }
    return $HOME
}

# -----------------------------------------------------------------------------
# CLI resolution: CODEARTS_CLI_BIN wins, else the installer default.
# -----------------------------------------------------------------------------
$Script:CliBin = ""

function Resolve-Cli {
    $cand = $env:CODEARTS_CLI_BIN
    if (-not $cand) {
        $base = Join-Path (Get-HomeDir) ".codeartsdoer\installers"
        foreach ($name in @("codearts.cmd", "codearts.exe", "codearts")) {
            $probe = Join-Path $base $name
            if (Test-Path -LiteralPath $probe -PathType Leaf) { $cand = $probe; break }
        }
        if (-not $cand) { $cand = Join-Path $base "codearts.cmd" }
    }
    if (-not (Test-Path -LiteralPath $cand -PathType Leaf)) {
        $cmd = Get-Command $cand -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source) {
            $cand = $cmd.Source
        } else {
            Write-JsonError -Code 30 -Type "cli_not_installed" `
                -Message "codearts CLI not found: $cand" `
                -Hint "Run scripts\setup.ps1 to install it, or set CODEARTS_CLI_BIN to the CLI path"
        }
    }
    $Script:CliBin = $cand
    Write-Log "using CLI: $Script:CliBin"
}

# -----------------------------------------------------------------------------
# Credentials: process environment first, then ~/.bashrc (same as setup.*).
# -----------------------------------------------------------------------------
function Read-BashrcValue {
    param([string]$Name)
    $bashrc = Join-Path (Get-HomeDir) ".bashrc"
    if (-not (Test-Path -LiteralPath $bashrc -PathType Leaf)) { return "" }
    $pattern = "^export " + [regex]::Escape($Name) + "=(.*)$"
    $value = ""
    foreach ($line in (Get-Content -LiteralPath $bashrc -ErrorAction SilentlyContinue)) {
        if ($line -match $pattern) { $value = $Matches[1] }
    }
    $value = $value.Trim()
    if ($value.Length -ge 2) {
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
    }
    return $value
}

function Initialize-Creds {
    $ak = $env:CODEARTS_CLI_AK
    $sk = $env:CODEARTS_CLI_SK
    if ((-not $ak) -or (-not $sk)) {
        Write-Log "loading AK/SK from ~/.bashrc"
        if (-not $ak) { $ak = Read-BashrcValue -Name "CODEARTS_CLI_AK" }
        if (-not $sk) { $sk = Read-BashrcValue -Name "CODEARTS_CLI_SK" }
    }
    if ((-not $ak) -or (-not $sk)) {
        Write-Log "AK/SK not configured"
        Write-NeedInput "Huawei Cloud AK/SK required: set CODEARTS_CLI_AK and CODEARTS_CLI_SK, or run 'scripts\setup.ps1 --save-aksk <AK> <SK>'"
    }
    $env:CODEARTS_CLI_AK = $ak
    $env:CODEARTS_CLI_SK = $sk
}

# -----------------------------------------------------------------------------
# Attachment support (#113-14).
# -----------------------------------------------------------------------------
function Read-Attachment {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        Write-JsonError -Code 60 -Type "attachment_failed" `
            -Message "Attachment file not found: $Path" -Hint "Pass an existing file: -f <path>"
    }
    if ((Get-Item -LiteralPath $Path).PSIsContainer) {
        Write-JsonError -Code 60 -Type "attachment_failed" `
            -Message "Attachment is not a regular file: $Path" -Hint "Pass a regular file: -f <path>"
    }
    $content = $null
    try {
        $content = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 -ErrorAction Stop
    } catch {
        Write-JsonError -Code 60 -Type "attachment_failed" `
            -Message "Attachment file is not readable: $Path" -Hint "Check file permissions: -f <path>"
    }
    if ($null -eq $content -or $content.Length -eq 0) {
        Write-JsonError -Code 60 -Type "attachment_failed" `
            -Message "Attachment file is empty: $Path" -Hint "Attach a non-empty file: -f <path>"
    }
    return $content
}

function Get-Fence {
    param([string]$Content)
    $max = 0
    foreach ($m in [regex]::Matches($Content, '`+')) {
        if ($m.Length -gt $max) { $max = $m.Length }
    }
    $n = $max + 1
    if ($n -lt 3) { $n = 3 }
    return ('`' * $n)
}

# -----------------------------------------------------------------------------
# JSONL validation for --format json (#113-5).
# -----------------------------------------------------------------------------
function Test-Jsonl {
    param([string]$Text)
    foreach ($line in ($Text -split "`r?`n")) {
        if (-not $line.Trim()) { continue }
        try {
            $obj = ConvertFrom-Json -InputObject $line -ErrorAction Stop
        } catch {
            return @{ Ok = $false; Reason = "line is not valid JSON" }
        }
        if ($obj -is [System.Management.Automation.PSCustomObject]) {
            $names = $obj.PSObject.Properties.Name
            if (($names -contains "type") -and ($obj.type -eq "error")) {
                return @{ Ok = $false; Reason = "stdout contains a top-level error object" }
            }
        }
    }
    return @{ Ok = $true; Reason = "" }
}

# -----------------------------------------------------------------------------
# Windows command-line quoting (CreateProcess rules).
# -----------------------------------------------------------------------------
function ConvertTo-CmdArg {
    param([string]$Arg)
    if ($null -eq $Arg) { return '""' }
    if ($Arg.Length -eq 0) { return '""' }
    if ($Arg -notmatch '[\s"]') { return $Arg }
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append('"')
    $backslashes = 0
    foreach ($ch in $Arg.ToCharArray()) {
        if ($ch -eq '\') {
            $backslashes++
            continue
        }
        if ($ch -eq '"') {
            [void]$sb.Append('\' * ($backslashes * 2 + 1))
            [void]$sb.Append('"')
            $backslashes = 0
            continue
        }
        if ($backslashes -gt 0) {
            [void]$sb.Append('\' * $backslashes)
            $backslashes = 0
        }
        [void]$sb.Append($ch)
    }
    if ($backslashes -gt 0) {
        [void]$sb.Append('\' * ($backslashes * 2))
    }
    [void]$sb.Append('"')
    return $sb.ToString()
}

# -----------------------------------------------------------------------------
# Execute the CLI, capturing stdout/stderr separately (stderr is forwarded).
# -----------------------------------------------------------------------------
function Invoke-Cli {
    param([string[]]$CliArgs)

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Script:CliBin
    $quoted = @()
    foreach ($a in $CliArgs) { $quoted += (ConvertTo-CmdArg $a) }
    $psi.Arguments = ($quoted -join ' ')
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $psi.StandardOutputEncoding = $utf8
    $psi.StandardErrorEncoding = $utf8
    try {
        $psi.WorkingDirectory = (Get-Location).Path
    } catch {
        # keep the inherited working directory
    }

    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    try {
        [void]$proc.Start()
    } catch {
        Write-JsonError -Code 30 -Type "cli_not_installed" `
            -Message "cannot execute codearts CLI at $Script:CliBin : $($_.Exception.Message)" `
            -Hint "Check the path / set CODEARTS_CLI_BIN to the CLI executable"
    }
    $outTask = $proc.StandardOutput.ReadToEndAsync()
    $errTask = $proc.StandardError.ReadToEndAsync()
    $proc.WaitForExit()
    return @{
        ExitCode = $proc.ExitCode
        StdOut   = $outTask.Result
        StdErr   = $errTask.Result
    }
}

function Get-FirstMeaningfulLine {
    param([string]$Text)
    if (-not $Text) { return "" }
    foreach ($line in ($Text -split "`r?`n")) {
        if ($line.Trim()) {
            $t = $line.Trim().TrimEnd("`r")
            if ($t.Length -gt 200) { return $t.Substring(0, 200) }
            return $t
        }
    }
    return ""
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
function Invoke-Main {
    if ($null -eq $Remaining) { $Remaining = @() }

    $cliArgs = New-Object System.Collections.ArrayList
    $files = New-Object System.Collections.ArrayList
    $missingFileArg = $false

    # --- 1. split argv: the wrapper consumes -f/--file, the CLI gets the rest ---
    $i = 0
    while ($i -lt $Remaining.Count) {
        $a = $Remaining[$i]
        if ($a -eq "-f" -or $a -eq "--file") {
            if (($i + 1) -ge $Remaining.Count) {
                $missingFileArg = $true
                break
            }
            [void]$files.Add($Remaining[$i + 1])
            $i += 2
            continue
        }
        if ($a -like "--file=*") {
            [void]$files.Add($a.Substring(7))
            $i++
            continue
        }
        [void]$cliArgs.Add($a)
        $i++
    }

    # --- 2. locate the CLI -------------------------------------------------
    Resolve-Cli

    # --- 3. credentials ----------------------------------------------------
    Initialize-Creds

    # --- 4. attachments ----------------------------------------------------
    if ($missingFileArg) {
        Write-JsonError -Code 60 -Type "attachment_failed" `
            -Message "Missing file path after -f/--file" `
            -Hint 'Usage: codearts_run.ps1 run -f <file> "<task>"'
    }

    if ($files.Count -gt 0) {
        # The task description is the last positional argument; a valid call with an
        # attachment always carries the sub-command plus the task, so fewer than two
        # positionals would append the attachment to the sub-command or a model id.
        if ($cliArgs.Count -lt 2) {
            Write-JsonError -Code 60 -Type "attachment_failed" `
                -Message "Attachment given but there is no task description to attach it to (the task must be the last argument after the sub-command)" `
                -Hint 'Usage: codearts_run.ps1 run -f <file> "<task>"'
        }
        $last = $cliArgs.Count - 1
        $prompt = [string]$cliArgs[$last]
        foreach ($file in $files) {
            $content = Read-Attachment -Path $file
            $fence = Get-Fence -Content $content
            $prompt = $prompt + "`n`n----- Attached file: $file -----`n" + $fence + "`n" + $content + "`n" + $fence
            Write-Log "attached file: $file"
        }
        $cliArgs[$last] = $prompt
    }

    # --- 5. is this a JSON output session? (#113-5) ------------------------
    $jsonMode = $false
    for ($k = 0; $k -lt $cliArgs.Count; $k++) {
        $cur = [string]$cliArgs[$k]
        if ($cur -eq "--format" -and ($k + 1) -lt $cliArgs.Count) {
            if ([string]$cliArgs[$k + 1] -match '^(?i)json$') { $jsonMode = $true }
        } elseif ($cur -match '^(?i)--format=(.*)$') {
            if ($Matches[1] -match '^(?i)json$') { $jsonMode = $true }
        }
    }

    # --- 6. execute --------------------------------------------------------
    Write-Log "executing: $Script:CliBin ($($cliArgs.Count) args, json_mode=$jsonMode)"
    $result = Invoke-Cli -CliArgs ([string[]]$cliArgs.ToArray())
    $rc = [int]$result.ExitCode
    $outText = [string]$result.StdOut
    $errText = [string]$result.StdErr

    if ($errText.Length -gt 0) {
        [Console]::Error.Write($errText)
    }

    # --- 7. non-zero exit: classify the failure (never exit 0) -------------
    if ($rc -ne 0) {
        $combined = "$outText`n$errText"
        if ($combined -match $Script:AuthRe) {
            Write-JsonError -Code 50 -Type "auth_failed" `
                -Message "codearts CLI failed with exit code $rc : authentication error ($(Get-FirstMeaningfulLine $combined))" `
                -Hint "Verify CODEARTS_CLI_AK/CODEARTS_CLI_SK and re-run 'scripts\setup.ps1 --save-aksk <AK> <SK>' if needed"
        }
        if ($combined -match $Script:NetRe) {
            Write-JsonError -Code 40 -Type "network_failed" `
                -Message "codearts CLI failed with exit code $rc : network error ($(Get-FirstMeaningfulLine $combined))" `
                -Hint "Check network connectivity, proxy settings and retry"
        }
        Write-JsonError -Code 1 -Type "cli_failed" `
            -Message "codearts CLI failed with exit code $rc : $(Get-FirstMeaningfulLine $combined)" `
            -Hint "Inspect the CLI stderr above and re-run the command"
    }

    # --- 8. exit 0: verify the output contract -----------------------------
    if (-not $outText -or -not $outText.Trim()) {
        $emptyMsg = "codearts CLI exited 0 but wrote nothing to stdout"
        if ($errText.Trim()) {
            $emptyMsg = "$emptyMsg; stderr said: $(Get-FirstMeaningfulLine $errText)"
        }
        if ($errText -match $Script:AuthRe) {
            Write-JsonError -Code 50 -Type "auth_failed" -Message $emptyMsg `
                -Hint "Verify CODEARTS_CLI_AK/CODEARTS_CLI_SK; the CLI reported an authentication error"
        }
        if ($errText -match $Script:NetRe) {
            Write-JsonError -Code 40 -Type "network_failed" -Message $emptyMsg `
                -Hint "Check network connectivity, proxy settings and retry"
        }
        Write-JsonError -Code 60 -Type "output_contract_violation" -Message $emptyMsg `
            -Hint "The CLI reported success without a payload; check AK/SK and network, then retry"
    }

    if ($jsonMode) {
        $verdict = Test-Jsonl -Text $outText
        if (-not $verdict.Ok) {
            Write-JsonError -Code 60 -Type "output_contract_violation" `
                -Message "codearts CLI exited 0 but stdout violates the --format json contract: $($verdict.Reason)" `
                -Hint "The CLI must print one JSON object per line in json mode; retry or report this to the CodeArts CLI maintainers"
        }
    }

    # #113-3/#113-4: the CLI sometimes prints a diagnostic and still exits 0.
    $headLine = Get-FirstMeaningfulLine $outText
    if ($headLine -and ($headLine -match $Script:ErrHeadRe)) {
        if ($outText -match $Script:AuthRe) {
            Write-JsonError -Code 50 -Type "auth_failed" `
                -Message "codearts CLI exited 0 but stdout reports an authentication error: $headLine" `
                -Hint "Verify CODEARTS_CLI_AK/CODEARTS_CLI_SK"
        }
        if ($outText -match $Script:NetRe) {
            Write-JsonError -Code 40 -Type "network_failed" `
                -Message "codearts CLI exited 0 but stdout reports a network error: $headLine" `
                -Hint "Check network connectivity, proxy settings and retry"
        }
        Write-JsonError -Code 60 -Type "output_contract_violation" `
            -Message "codearts CLI exited 0 but stdout is an error message: $headLine" `
            -Hint "The CLI reported success while printing an error; inspect the message above"
    }

    if (-not $jsonMode -and $outText.TrimStart().StartsWith("{")) {
        if ($outText -match '"type"\s*:\s*"error"') {
            Write-JsonError -Code 60 -Type "output_contract_violation" `
                -Message "codearts CLI exited 0 but stdout carries a top-level error object" `
                -Hint "The CLI reported success while returning an error payload"
        }
    }

    # --- 9. success: forward the CLI stdout byte for byte ------------------
    Write-Log "success"
    [Console]::Out.Write($outText)
    exit 0
}

try {
    # Keep the byte stream UTF-8 for the agent that consumes stdout.
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    Invoke-Main
} catch {
    Write-JsonError -Code 1 -Type "cli_failed" `
        -Message "unexpected wrapper error: $($_.Exception.Message)" `
        -Hint "Re-run the same command; if it persists, report it to the skill maintainers"
}
