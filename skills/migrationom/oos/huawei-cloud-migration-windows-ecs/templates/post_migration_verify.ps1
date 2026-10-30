# ============================================================
# Windows SMS迁移后验证脚本
# 在目标ECS Windows上运行此脚本
# 用法: powershell -ExecutionPolicy Bypass -File post_migration_verify.ps1
# ============================================================

param(
    [string]$OutputFile = "post_verify_result.json",
    [string[]]$ExpectedDataDrives = @()
)

$ErrorActionPreference = "Continue"
$result = @{
    timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    checks = @{}
    overall_status = "PASS"
}

function Add-Check {
    param($Name, $Status, $Message, $Details = @{})
    $result.checks[$Name] = @{
        status = $Status
        message = $Message
        details = $Details
    }
    if ($Status -eq "FAIL") {
        $result.overall_status = "FAIL"
    }
}

# ===== 1. 系统启动检查 =====
Write-Host "[1/8] 检查系统启动状态..."
$uptime = (Get-Date) - (Get-CimInstance -ClassName Win32_OperatingSystem).LastBootUpTime
$uptimeStr = "{0}天 {1}小时 {2}分钟" -f $uptime.Days, $uptime.Hours, $uptime.Minutes
Add-Check "system_boot" "PASS" "系统已正常启动" @{ uptime = $uptimeStr }

# ===== 2. 系统盘检查 =====
Write-Host "[2/8] 检查系统盘..."
$sysDrive = Get-Volume -DriveLetter C -ErrorAction SilentlyContinue
if ($sysDrive -and $sysDrive.DriveType -eq "Fixed") {
    $freeGB = [math]::Round($sysDrive.SizeRemaining / 1GB, 2)
    $totalGB = [math]::Round($sysDrive.Size / 1GB, 2)
    Add-Check "system_disk" "PASS" "系统盘正常" @{ drive = "C:"; total_gb = $totalGB; free_gb = $freeGB }
} else {
    Add-Check "system_disk" "FAIL" "系统盘C:异常"
}

# ===== 3. 数据盘检查 =====
Write-Host "[3/8] 检查数据盘..."
$allVolumes = Get-Volume | Where-Object { $_.DriveLetter -and $_.DriveType -eq "Fixed" -and $_.DriveLetter -ne "C" }
$diskInfo = @()
foreach ($vol in $allVolumes) {
    $freeGB = [math]::Round($vol.SizeRemaining / 1GB, 2)
    $totalGB = [math]::Round($vol.Size / 1GB, 2)
    $diskInfo += @{ drive = "$($vol.DriveLetter):"; total_gb = $totalGB; free_gb = $freeGB }
}
if ($ExpectedDataDrives.Count -gt 0) {
    $missing = $ExpectedDataDrives | Where-Object { $_ -notin ($diskInfo | ForEach-Object { $_.drive }) }
    if ($missing) {
        Add-Check "data_disks" "FAIL" "缺少预期数据盘: $($missing -join ', ')" @{ found = $diskInfo; expected = $ExpectedDataDrives }
    } else {
        Add-Check "data_disks" "PASS" "所有预期数据盘均存在" @{ found = $diskInfo; expected = $ExpectedDataDrives }
    }
} else {
    Add-Check "data_disks" "PASS" "数据盘检查完成" @{ found = $diskInfo }
}

# ===== 4. 网络连通性检查 =====
Write-Host "[4/8] 检查网络连通性..."
$adapters = Get-NetAdapter | Where-Object { $_.Status -eq "Up" }
$ips = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne "127.0.0.1" -and $_.PrefixOrigin -ne "WellKnown" }
if ($adapters.Count -gt 0 -and $ips.Count -gt 0) {
    Add-Check "network" "PASS" "网络正常" @{ adapters = $adapters.Count; ip_addresses = ($ips.IPAddress -join ", ") }
} else {
    Add-Check "network" "FAIL" "网络异常，未找到活动的网络适配器"
}

# ===== 5. RDP服务检查 =====
Write-Host "[5/8] 检查RDP服务..."
$rdpReg = Get-ItemProperty "HKLM:\System\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections" -ErrorAction SilentlyContinue
if ($rdpReg -and $rdpReg.fDenyTSConnections -eq 0) {
    $rdpService = Get-Service -Name "TermService" -ErrorAction SilentlyContinue
    Add-Check "rdp_service" "PASS" "RDP服务已启用" @{ enabled = $true; service_status = $rdpService.Status }
} else {
    Add-Check "rdp_service" "FAIL" "RDP未启用，请执行: Set-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -Name 'fDenyTSConnections' -Value 0"
}

# ===== 6. Windows服务检查 =====
Write-Host "[6/8] 检查关键Windows服务..."
$criticalServices = @("EventLog", "PlugPlay", "RpcSs", "LanmanServer", "LanmanWorkstation")
$svcResults = @{}
$allRunning = $true
foreach ($svc in $criticalServices) {
    $service = Get-Service -Name $svc -ErrorAction SilentlyContinue
    if ($service) {
        $svcResults[$svc] = $service.Status
        if ($service.Status -ne "Running") { $allRunning = $false }
    } else {
        $svcResults[$svc] = "NotFound"
        $allRunning = $false
    }
}
if ($allRunning) {
    Add-Check "critical_services" "PASS" "所有关键服务运行正常" @{ services = $svcResults }
} else {
    Add-Check "critical_services" "FAIL" "部分关键服务异常" @{ services = $svcResults }
}

# ===== 7. 防火墙检查 =====
Write-Host "[7/8] 检查防火墙RDP规则..."
$rdpRule = Get-NetFirewallRule -DisplayName "Remote Desktop*" -ErrorAction SilentlyContinue
if ($rdpRule) {
    $enabledRules = $rdpRule | Where-Object { $_.Enabled -eq "True" }
    if ($enabledRules) {
        Add-Check "firewall_rdp" "PASS" "RDP防火墙规则已启用" @{ rule_count = $enabledRules.Count }
    } else {
        Add-Check "firewall_rdp" "WARN" "RDP防火墙规则未启用，请手动开启3389端口"
    }
} else {
    Add-Check "firewall_rdp" "WARN" "未找到RDP防火墙规则"
}

# ===== 8. SMS Agent检查 =====
Write-Host "[8/8] 检查SMS Agent状态..."
$smsAgent = Get-Service -Name "SMSAgentService" -ErrorAction SilentlyContinue
if ($smsAgent) {
    Add-Check "sms_agent" "PASS" "SMS Agent存在" @{ status = $smsAgent.Status }
} else {
    Add-Check "sms_agent" "INFO" "SMS Agent不存在（迁移完成后可能已卸载）"
}

# ===== 输出结果 =====
$result | ConvertTo-Json -Depth 5 | Out-File -FilePath $OutputFile -Encoding UTF8

Write-Host ""
Write-Host "=========================================="
Write-Host " 迁移后验证结果: $($result.overall_status)"
Write-Host " 详细结果已保存到: $OutputFile"
Write-Host "=========================================="

if ($result.overall_status -eq "FAIL") {
    Write-Host ""
    Write-Host "验证未通过，请检查以上FAIL项。"
    exit 1
} else {
    Write-Host ""
    Write-Host "验证通过，迁移成功！"
    exit 0
}
