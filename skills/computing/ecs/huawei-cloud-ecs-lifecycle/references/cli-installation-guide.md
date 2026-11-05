# KooCLI Installation and Authentication Guide

This Skill uses the Huawei Cloud KooCLI (`hcloud`) command-line tool.

## Installation

### Linux / macOS

```bash
# Download the KooCLI release package from the official Huawei Cloud OBS bucket
curl -fL -o hcloud.tar.gz https://cn-south-1-cloud-res-model-sdk.obs.cn-south-1.myhuaweicloud.com/hcloud/hcloud.tar.gz

# Verify integrity with SHA256 (compare against the checksum published in the
# official release notes: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html)
sha256sum hcloud.tar.gz

tar -xzf hcloud.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/

# Verify
hcloud version
```

> Note: always verify the downloaded package checksum before installing; never
> pipe remote scripts straight into a shell.

Official reference: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html

## Preflight Check (Step 0)

**Run this before any other workflow step** (issue #942). It validates the environment up front,
so a missing CLI, missing credentials or an unresolved region is reported here with actionable
remediation instead of failing later at Step 3/4 with `command not found`.

```bash
# from the Skill directory
bash scripts/preflight_check.sh [--region cn-north-4] [--skip-auth-check]

# typical entry check
bash scripts/preflight_check.sh --region cn-north-4

# offline / air-gapped: installation, credentials and region are still checked
bash scripts/preflight_check.sh --region cn-north-4 --skip-auth-check
```

The script prints one `[OK]` / `[FAIL]` line per check, then a `PREFLIGHT RESULT: PASS|FAIL`
verdict. On failure it prints an actionable remediation block pointing at this document and
exits non-zero, so the workflow must abort.

| # | Check | How it is verified | Fix on FAIL |
| --- | ------- | ------------------- | ------------- |
| 1 | KooCLI installed | `command -v hcloud` finds `hcloud` on `PATH` | install KooCLI (see Installation above) |
| 2 | KooCLI runnable | `hcloud version` prints a version number | re-install, or `hcloud update -y` |
| 3 | Credentials present | a KooCLI profile with an access key **or** `HUAWEICLOUD_SDK_AK`/`HUAWEICLOUD_SDK_SK` **or** `HUAWEI_ACCESS_KEY`/`HUAWEI_SECRET_KEY` | `hcloud configure set ...` or export the environment variables |
| 4 | Region resolvable | `--region`, else `HUAWEICLOUD_SDK_REGION`, else `HUAWEI_REGION`, else a non-empty `region` in `hcloud configure list` | pass `--region <region>`, or `hcloud configure set --cli-region=<region>` |
| 5 | Credentials usable | read-only smoke `hcloud ECS ListServersDetails --cli-region=<region> --limit=1` must return a `count` field; skipped by `--skip-auth-check` | fix the credentials/IAM permissions, then re-run |

Exit codes: `0` = environment ready, `1` = environment not ready (workflow must abort),
`2` = invalid usage. Diagnostics go to stdout, so the output can be logged as-is.

Rules that matter:

- There is **no implicit default region**. With no `--region`, no `HUAWEICLOUD_SDK_REGION` /
  `HUAWEI_REGION` and an empty profile `region`, check 4 FAILs and the script exits non-zero.
  Pass `--region` explicitly (e.g. `--region cn-north-4`) if the profile has no default.
- The script never prints AK/SK: `hcloud configure list` output is used for presence detection
  only, and any captured hcloud text is masked (`>= 20` alphanumeric characters → `<redacted>`).
- Use `hcloud version`. `hcloud --version` is **invalid** and returns
  `[USE_ERROR]参数--version的格式错误,正确格式为:--param=value`.
- KooCLI exits `0` even for `[USE_ERROR]` and API errors, so the script validates the response
  body (for example the `count` field), not just the exit code.
- `--skip-auth-check` skips check 5 only; installation, credentials and region are still enforced.

### Windows PowerShell equivalent

The Skill runs on Windows too, where `bash` is not guaranteed. Save the block below as
`preflight_check.ps1` (for example in the Skill directory) and run it with Windows PowerShell 5.1+
or PowerShell 7+. It performs the same five checks, prints the same `[OK]` / `[FAIL]` lines and
uses the same exit codes (`0` ready, `1` not ready).

```powershell
# preflight_check.ps1 -- Windows PowerShell equivalent of scripts/preflight_check.sh
# (issue #942, skill huawei-cloud-ecs-lifecycle).
# Same five checks, same [OK]/[FAIL] verdict lines, same exit codes:
#   0 = ready, 1 = not ready, 2 = invalid usage.
[CmdletBinding()]
param(
    [string]$Region = "",
    [switch]$SkipAuthCheck
)

$script:failedChecks = 0

function Write-Ok   { param([string]$m) Write-Host "[OK]   $m" }
function Write-Fail { param([string]$m) Write-Host "[FAIL] $m"; $script:failedChecks++ }
function Write-Skip { param([string]$m) Write-Host "[SKIP] $m" }
function Mask-Secret { param([string]$t) return ($t -replace '[A-Za-z0-9]{20,}', '<redacted>') }

function Write-Remediation {
    Write-Host ""
    Write-Host "---- Remediation: environment not ready ----"
    Write-Host "Full instructions: references/cli-installation-guide.md"
    Write-Host ""
    Write-Host "1) Install the KooCLI 'hcloud' binary and put it on PATH (Linux / macOS / Git Bash):"
    Write-Host "     curl -fL -o hcloud.tar.gz https://cn-south-1-cloud-res-model-sdk.obs.cn-south-1.myhuaweicloud.com/hcloud/hcloud.tar.gz"
    Write-Host "     sha256sum hcloud.tar.gz"
    Write-Host "     tar -xzf hcloud.tar.gz; chmod +x hcloud; sudo mv hcloud /usr/local/bin/"
    Write-Host "   Verify with:  hcloud version      (NOT 'hcloud --version' - that is a USE_ERROR)"
    Write-Host ""
    Write-Host "2) Authenticate - either a CLI profile:"
    Write-Host "     hcloud configure set --cli-region=<region> --access-key=<AK> --secret-key=<SK>"
    Write-Host "   or environment variables:"
    Write-Host "     `$env:HUAWEICLOUD_SDK_AK='<AK>'; `$env:HUAWEICLOUD_SDK_SK='<SK>'; `$env:HUAWEICLOUD_SDK_REGION='<region>'"
    Write-Host ""
    Write-Host "3) Resolve the region when the profile has none:"
    Write-Host "     hcloud configure set --cli-region=<region>"
    Write-Host ""
    Write-Host "4) Re-run the preflight check:"
    Write-Host "     .\preflight_check.ps1 -Region <region>"
    Write-Host ""
    Write-Host "Never commit, echo or paste AK/SK values."
}

Write-Host "==== ECS lifecycle preflight check (hcloud) ===="
Write-Host "Skill: huawei-cloud-ecs-lifecycle | script: preflight_check.ps1 (PowerShell)"

# ------------------------------------------------------- 1/5 hcloud on PATH --
Write-Host ""
Write-Host "-- Check 1/5: KooCLI installed and on PATH --"
$hcloudCmd = Get-Command hcloud -ErrorAction SilentlyContinue
if ($hcloudCmd) {
    Write-Ok "1/5 hcloud found on PATH: $($hcloudCmd.Source)"
} else {
    Write-Fail "1/5 hcloud NOT found on PATH (Get-Command hcloud failed); install KooCLI and add it to PATH"
}

# ---------------------------------------------------- 2/5 hcloud version OK --
Write-Host ""
Write-Host "-- Check 2/5: hcloud version --"
$hcloudUsable = $false
$versionOut = ""
if ($hcloudCmd) { $versionOut = (hcloud version 2>&1 | Out-String) }
$versionNum = ""
$vm = [regex]::Matches($versionOut, '[0-9]+\.[0-9]+\.[0-9]+')
if ($vm.Count -gt 0) { $versionNum = $vm[$vm.Count - 1].Value }
if (-not $hcloudCmd) {
    Write-Fail "2/5 'hcloud version' not evaluated: hcloud is not available"
} elseif ($versionOut -match 'USE_ERROR|ERROR') {
    $errLine = (Mask-Secret $versionOut) -split "`n" | Where-Object { $_ -match 'USE_ERROR|ERROR' } | Select-Object -First 1
    Write-Fail "2/5 'hcloud version' reported an error: $errLine"
} elseif ($versionNum) {
    $hcloudUsable = $true
    Write-Ok "2/5 'hcloud version' OK (KooCLI $versionNum)"
} else {
    Write-Fail "2/5 'hcloud version' produced no version string"
}

# --------------------------------------------------------- 3/5 credentials --
Write-Host ""
Write-Host "-- Check 3/5: credentials available --"
$confOut = ""
$curProfile = ""
if ($hcloudCmd) {
    $confOut = (hcloud configure list 2>&1 | Out-String)
    if ($confOut -match '"current"\s*:\s*"([^"]*)"') { $curProfile = $Matches[1] }
}
$credSource = ""
if ($confOut -match '"accessKeyId"\s*:\s*"[^"]') {
    $credSource = "KooCLI profile '$curProfile' (access key configured; value not shown)"
} elseif ($confOut -match '"securityToken"\s*:\s*"[^"]') {
    $credSource = "KooCLI profile '$curProfile' (temporary security token configured; value not shown)"
}
if (-not $credSource) {
    if ($env:HUAWEICLOUD_SDK_AK -and $env:HUAWEICLOUD_SDK_SK) {
        $credSource = "environment variables HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK (values not shown)"
    } elseif ($env:HUAWEI_ACCESS_KEY -and $env:HUAWEI_SECRET_KEY) {
        $credSource = "environment variables HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY (values not shown)"
    }
}
if ($credSource) {
    Write-Ok "3/5 credentials present: $credSource"
} else {
    Write-Fail "3/5 no usable credentials found: no KooCLI profile with an access key, and no HUAWEICLOUD_SDK_AK/SK or HUAWEI_ACCESS_KEY/SECRET_KEY environment variables"
}

# --------------------------------------------------------------- 4/5 region --
Write-Host ""
Write-Host "-- Check 4/5: region resolvable --"
$regionSource = ""
if ($Region) {
    $regionSource = "-Region argument"
} elseif ($env:HUAWEICLOUD_SDK_REGION) {
    $Region = $env:HUAWEICLOUD_SDK_REGION; $regionSource = "HUAWEICLOUD_SDK_REGION"
} elseif ($env:HUAWEI_REGION) {
    $Region = $env:HUAWEI_REGION; $regionSource = "HUAWEI_REGION"
} else {
    $profileRegion = ""
    if ($confOut -match '"region"\s*:\s*"([^"]+)"') { $profileRegion = $Matches[1] }
    if ($profileRegion) { $Region = $profileRegion; $regionSource = "active KooCLI profile '$curProfile'" }
}
if ($Region) {
    Write-Ok "4/5 region resolved: $Region (source: $regionSource)"
} else {
    Write-Fail "4/5 no region resolved: pass -Region <region>, or set `$env:HUAWEICLOUD_SDK_REGION, or run 'hcloud configure set --cli-region=<region>'"
}

# -------------------------------------------------- 5/5 read-only smoke test --
Write-Host ""
Write-Host "-- Check 5/5: read-only credential smoke test --"
if ($SkipAuthCheck) {
    Write-Skip "5/5 read-only smoke skipped (-SkipAuthCheck); credential usability is NOT verified"
} elseif (-not $hcloudUsable) {
    Write-Fail "5/5 read-only smoke not evaluated: hcloud is not usable"
} elseif (-not $Region) {
    Write-Fail "5/5 read-only smoke not evaluated: no region resolved"
} else {
    $smokeOut = (hcloud ECS ListServersDetails --cli-region=$Region --limit=1 2>&1 | Out-String)
    $smokeRc = $LASTEXITCODE
    if ($smokeOut -match '"count"\s*:\s*([0-9]+)') {
        Write-Ok "5/5 read-only smoke OK: hcloud ECS ListServersDetails --cli-region=$Region --limit=1 returned count=$($Matches[1])"
    } else {
        $errLine = (Mask-Secret $smokeOut) -split "`n" | Where-Object { $_ -match 'USE_ERROR|ERROR|error_code|error_msg' } | Select-Object -First 1
        if (-not $errLine) { $errLine = 'response contained no "count" field' }
        Write-Fail "5/5 read-only smoke FAILED (exit $smokeRc): $errLine"
    }
}

# ------------------------------------------------------------- final verdict --
Write-Host ""
Write-Host "==== Preflight result ===="
if ($script:failedChecks -eq 0) {
    if ($SkipAuthCheck) {
        Write-Host "PREFLIGHT RESULT: PASS - KooCLI installed, credentials present, region $Region. Credential usability NOT verified (-SkipAuthCheck)."
    } else {
        Write-Host "PREFLIGHT RESULT: PASS - KooCLI installed, credentials usable, region $Region (read-only smoke OK)."
    }
    exit 0
}
Write-Host "PREFLIGHT RESULT: FAIL - $($script:failedChecks) check(s) failed; abort the ECS workflow and fix the [FAIL] items above."
Write-Remediation
exit 1
```

```powershell
.\preflight_check.ps1 -Region cn-north-4                      # full check
.\preflight_check.ps1 -Region cn-north-4 -SkipAuthCheck       # offline check
```

> Note: on Windows, `GET-Command hcloud` only finds the CLI if `hcloud.exe` is on `PATH`; add
> `D:\koocli` (or wherever KooCLI was unpacked) to `PATH` before running the check. Because
> PowerShell processes the whole script at once, keep the block in a `.ps1` file rather than
> pasting it line by line into an interactive prompt.

## Authentication

### Option A: hcloud CLI profile (recommended)

```bash
hcloud configure set --cli-region=cn-north-4 \
  --access-key={AK} --secret-key={SK}
hcloud configure show          # verify
```

### Option B: environment variables (agent-friendly)

```bash
export HUAWEI_ACCESS_KEY={AK}
export HUAWEI_SECRET_KEY={SK}
# or
export HUAWEICLOUD_SDK_AK={AK}
export HUAWEICLOUD_SDK_SK={SK}
```

KooCLI (and the Huawei Cloud SDKs) pick these environment variables up automatically.

## Verification

```bash
hcloud ECS ListServersDetails --cli-region=cn-north-4 --limit=1
```

If this returns the server list (or an empty list), the CLI is authenticated and working.

> Run the [Preflight Check (Step 0)](#preflight-check-step-0) first: `scripts/preflight_check.sh`
> performs this exact call as its check 5 and aborts the workflow with remediation guidance on
> failure. `--skip-auth-check` turns this call off when no network is available.

## Notes

- Upgrade KooCLI when commands are missing: `hcloud update -y`
- Service name is `ECS` (metadata key `ecs`); operation names are PascalCase.
- Version probe: use `hcloud version`. `hcloud --version` is invalid and prints
  `[USE_ERROR]参数--version的格式错误,正确格式为:--param=value`.
- KooCLI exits `0` even for `[USE_ERROR]` and for API errors (`401`/`403`, unknown region,
  unsupported operation). Check the response body — not only `$?` — when testing success.
