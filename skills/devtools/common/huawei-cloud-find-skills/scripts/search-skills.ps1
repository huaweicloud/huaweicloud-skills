param(
    [string]$Keyword = "",
    [string]$Category = ""
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$indexFile = Join-Path $scriptDir "..\references\index.json"
$cnEnFile = Join-Path $scriptDir "..\references\cn-en-map.json"

if (-not (Test-Path $indexFile)) {
    Write-Error "index.json not found at $indexFile"; exit 1
}

if (-not $Keyword -and -not $Category) {
    Write-Host "Usage: .\search-skills.ps1 -Keyword <keyword> [-Category <category>]"
    $cats = (Get-Content $indexFile -Raw -Encoding UTF8 | ConvertFrom-Json).categories -join ", "
    Write-Host "Categories: $cats"
    exit 1
}

$cnEnMap = @{}
if (Test-Path $cnEnFile) {
    $cnEnObj = Get-Content $cnEnFile -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($prop in $cnEnObj.PSObject.Properties) { $cnEnMap[$prop.Name] = $prop.Value }
}

$keywords = @()
if ($Keyword) {
    $keywords = @($Keyword -split '[\s,;]+' | Where-Object { $_.Length -gt 0 })
    $expanded = @()
    foreach ($kw in $keywords) {
        $expanded += $kw
        if ($cnEnMap.ContainsKey($kw)) { $expanded += $cnEnMap[$kw] }
        foreach ($entry in $cnEnMap.GetEnumerator()) {
            if ($entry.Value -eq $kw.ToLower()) { $expanded += $entry.Key }
        }
    }
    $keywords = @($expanded | Sort-Object -Unique)
}

$idx = Get-Content $indexFile -Raw -Encoding UTF8 | ConvertFrom-Json
$results = @()

foreach ($skill in $idx.skills) {
    if ($Category -and $skill.category -ne $Category) { continue }

    $score = 0
    $matchedKws = @()

    if ($keywords.Count -gt 0) {
        foreach ($kw in $keywords) {
            $k = $kw.ToLower()
            $kwScore = 0
            if ($skill.name.ToLower() -like "*$k*") { $kwScore += 10 }
            if ($skill.triggers) {
                foreach ($t in $skill.triggers) {
                    if ($t -and $t.ToLower() -like "*$k*") { $kwScore += 8; break }
                }
            }
            if ($skill.description -and $skill.description.ToLower() -like "*$k*") { $kwScore += 5 }
            if ($skill.service -and $skill.service.ToLower() -like "*$k*") { $kwScore += 3 }
            if ($kwScore -gt 0) {
                $score += $kwScore
                $matchedKws += $kw
            }
        }
        if ($score -eq 0) { continue }
    } else {
        $score = 1
    }

    $desc = $skill.description
    if ($desc -and $desc.Length -gt 150) { $desc = $desc.Substring(0, 150) + "..." }

    $trigPreview = @()
    if ($skill.triggers) { $trigPreview = @($skill.triggers | Select-Object -First 5) }

    $results += [ordered]@{ score=$score; name=$skill.name; category=$skill.category; service=$skill.service; description=$desc; triggers=$trigPreview; matched=$matchedKws }
}

$results = @($results | Sort-Object -Property score -Descending)

if ($results.Count -eq 0) {
    Write-Host "No results for keyword='$Keyword' category='$Category'" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Fallback suggestions:"
    Write-Host "  1. Try broader or alternative keywords"
    Write-Host "  2. Remove category filter"
    Write-Host "  3. Switch CN<->EN (e.g., 'obs' <-> 'object storage')"
    Write-Host "  4. List all: .\search-skills.ps1 -Category 'computing'"
    exit 0
}

Write-Host "Found $($results.Count) skill(s) for keyword='$Keyword' category='$Category':" -ForegroundColor Cyan
if ($keywords.Count -gt 1 -or ($keywords.Count -eq 1 -and $keywords[0] -ne $Keyword)) {
    Write-Host "  (expanded: $($keywords -join ', '))" -ForegroundColor DarkGray
}
Write-Host ""
foreach ($r in $results) {
    $matchInfo = if ($r.matched.Count -gt 0) { " matched: $($r.matched -join ',')" } else { "" }
    Write-Host "  [$($r.score)pts] $($r.name) ($($r.category)/$($r.service))$matchInfo" -ForegroundColor White
    Write-Host "    $($r.description)" -ForegroundColor DarkGray
    if ($r.triggers.Count -gt 0) {
        Write-Host "    triggers: $($r.triggers -join ', ')" -ForegroundColor DarkGray
    }
    Write-Host ""
}