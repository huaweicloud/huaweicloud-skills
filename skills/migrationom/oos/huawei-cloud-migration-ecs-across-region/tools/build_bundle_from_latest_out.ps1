#Requires -Version 5.1
<#
.SYNOPSIS
    Build a migration bundle from the latest output artifacts.
.DESCRIPTION
    This script copies the latest migration result files to a bundle directory
    and creates a compressed archive for future reference.
.PARAMETER BundleName
    Optional. Name of the bundle directory. Defaults to current date (YYYY-MM-DD-migration-bundle).
.EXAMPLE
    .\build_bundle_from_latest_out.ps1
    # Creates bundle with default name: 2024-01-15-migration-bundle
.EXAMPLE
    .\build_bundle_from_latest_out.ps1 "2024-01-15-mx2-to-santiago"
    # Creates bundle with custom name
#>

param(
    [Parameter(Position = 0)]
    [string]$BundleName
)

# Get script directory (compatible with both PowerShell and git-bash)
$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}

# Calculate parent directories
$SkillDir = Split-Path -Parent $ScriptDir
$RepoDir = Split-Path -Parent $SkillDir
$OutDir = Join-Path $RepoDir "out"
$BundlesDir = Join-Path $SkillDir "bundles"

# Generate bundle name if not provided
if ([string]::IsNullOrWhiteSpace($BundleName)) {
    $BundleName = (Get-Date -Format "yyyy-MM-dd") + "-migration-bundle"
}

$TargetDir = Join-Path $BundlesDir $BundleName

# Create target directory
if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
}

# Required files to copy
$RequiredFiles = @(
    "migration_result.json",
    "precheck_task_cleanup.json",
    "postcheck_network.json",
    "task_poll_latest.json"
)

# Copy required files
foreach ($f in $RequiredFiles) {
    $src = Join-Path $OutDir $f
    $dst = Join-Path $TargetDir $f
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination $dst -Force
    } else {
        Write-Warning "[WARN] missing artifact: $src"
    }
}

# Copy reference files
$ReferenceFiles = @{
    "SKILL.md" = Join-Path $SkillDir "SKILL.md"
    "runbook.md" = Join-Path $SkillDir "references\runbook.md"
    "lessons-learned.md" = Join-Path $SkillDir "references\lessons-learned.md"
    "reuse-bundle.md" = Join-Path $SkillDir "references\reuse-bundle.md"
}

foreach ($filename in $ReferenceFiles.Keys) {
    $src = $ReferenceFiles[$filename]
    $dst = Join-Path $TargetDir $filename
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination $dst -Force
    }
}

# Generate README.md
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
$ReadmeContent = @"
# Migration Bundle: ${BundleName}

This bundle was generated from latest artifacts under:
- ${OutDir}

Included files:
- migration_result.json
- precheck_task_cleanup.json
- postcheck_network.json
- task_poll_latest.json
- SKILL.md
- runbook.md
- lessons-learned.md
- reuse-bundle.md

Generated at: ${Timestamp}
"@

$ReadmePath = Join-Path $TargetDir "README.md"
Set-Content -Path $ReadmePath -Value $ReadmeContent -Encoding UTF8

# Create compressed archive
$ArchivePath = Join-Path $BundlesDir "${BundleName}.zip"

# Use Compress-Archive (PowerShell 5.1+)
if (Test-Path $ArchivePath) {
    Remove-Item $ArchivePath -Force
}
Compress-Archive -Path $TargetDir -DestinationPath $ArchivePath -CompressionLevel Optimal

# Output results
Write-Host "Bundle directory: ${TargetDir}"
Write-Host "Bundle archive: ${ArchivePath}"