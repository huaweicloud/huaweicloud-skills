# ============================================================
# Windows SMS迁移前置检查脚本
# 在源端Windows服务器上运行此脚本
# 用法: powershell -ExecutionPolicy Bypass -File pre_migration_check.ps1
# ============================================================

param(
    [string]$OutputFile = "pre_check_result.json"
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

# ===== 1. 操作系统版本检查 =====
Write-Host "[1/19] 检查操作系统版本..."
$osInfo = Get-CimInstance -ClassName Win32_OperatingSystem
$osVersion = $osInfo.Version
$osCaption = $osInfo.Caption
$supportedVersions = @("6.1.", "6.2.", "6.3.", "10.0.")
$isSupported = $false
foreach ($ver in $supportedVersions) {
    if ($osVersion.StartsWith($ver)) { $isSupported = $true; break }
}
if ($isSupported) {
    Add-Check "os_version" "PASS" "操作系统版本受支持" @{ version = $osVersion; caption = $osCaption }
} else {
    Add-Check "os_version" "FAIL" "操作系统版本不受支持: $osCaption" @{ version = $osVersion; caption = $osCaption }
}

# ===== 2. .NET Framework检查 =====
Write-Host "[2/19] 检查.NET Framework..."
$netReg = Get-ChildItem "HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP" -ErrorAction SilentlyContinue
$netVersions = @()
if ($netReg) {
    foreach ($item in $netReg) {
        $release = (Get-ItemProperty "$($item.PSPath)" -Name "Release" -ErrorAction SilentlyContinue).Release
        if ($release) { $netVersions += [version]$item.PSChildName }
    }
}
$hasNet462 = $netVersions | Where-Object { $_ -ge "4.6.2" }
if ($hasNet462) {
    Add-Check "dotnet_framework" "PASS" ".NET Framework 4.6.2+ 已安装" @{ versions = ($netVersions -join ", ") }
} else {
    Add-Check "dotnet_framework" "FAIL" "需要.NET Framework 4.6.2或更高版本" @{ versions = ($netVersions -join ", ") }
}

# ===== 3. WinRM服务检查 =====
Write-Host "[3/19] 检查WinRM服务..."
$winrmService = Get-Service -Name "WinRM" -ErrorAction SilentlyContinue
if ($winrmService -and $winrmService.Status -eq "Running") {
    $listeners = winrm enumerate winrm/config/listener 2>$null
    $hasHTTP = $listeners -match "HTTP"
    $hasHTTPS = $listeners -match "HTTPS"
    Add-Check "winrm_service" "PASS" "WinRM服务运行中" @{
        status = $winrmService.Status
        http_listener = [bool]$hasHTTP
        https_listener = [bool]$hasHTTPS
    }
} else {
    Add-Check "winrm_service" "FAIL" "WinRM服务未运行，请执行: winrm quickconfig"
}

# ===== 4. VSS服务检查 =====
Write-Host "[4/19] 检查VSS服务..."
$vssService = Get-Service -Name "VSS" -ErrorAction SilentlyContinue
if ($vssService) {
    if ($vssService.Status -ne "Running") {
        Start-Service -Name "VSS" -ErrorAction SilentlyContinue
        $vssService = Get-Service -Name "VSS"
    }
    if ($vssService.Status -eq "Running") {
        $writers = vssadmin list writers 2>$null
        $writerCount = ($writers | Select-String "Writer name:" | Measure-Object).Count
        Add-Check "vss_service" "PASS" "VSS服务运行中" @{ status = $vssService.Status; writer_count = $writerCount }
    } else {
        Add-Check "vss_service" "FAIL" "VSS服务无法启动"
    }
} else {
    Add-Check "vss_service" "FAIL" "VSS服务不存在"
}

# ===== 5. 磁盘空间检查 =====
Write-Host "[5/19] 检查磁盘空间..."
$disks = Get-Disk -ErrorAction SilentlyContinue
$diskInfo = @()
$minSpaceGB = 2
foreach ($disk in $disks) {
    $volumes = Get-Volume -DiskNumber $disk.Number -ErrorAction SilentlyContinue
    foreach ($vol in $volumes) {
        if ($vol.DriveLetter) {
            $freeGB = [math]::Round($vol.SizeRemaining / 1GB, 2)
            $totalGB = [math]::Round($vol.Size / 1GB, 2)
            $diskInfo += @{
                drive = "$($vol.DriveLetter):"
                total_gb = $totalGB
                free_gb = $freeGB
            }
        }
    }
}
$lowSpace = $diskInfo | Where-Object { $_.free_gb -lt $minSpaceGB }
if ($lowSpace) {
    Add-Check "disk_space" "FAIL" "磁盘空间不足(需要至少${minSpaceGB}GB)" @{ disks = $diskInfo }
} else {
    Add-Check "disk_space" "PASS" "磁盘空间充足" @{ disks = $diskInfo }
}

# ===== 6. NTFS文件系统检查 =====
Write-Host "[6/19] 检查NTFS文件系统..."
$allVolumes = Get-Volume -ErrorAction SilentlyContinue | Where-Object { $_.DriveLetter -and $_.FileSystem }
$nonNtfsVolumes = $allVolumes | Where-Object { $_.FileSystem -ne "NTFS" -and $_.FileSystem -ne "ReFS" }
if ($nonNtfsVolumes) {
    $nonNtfsList = ($nonNtfsVolumes | ForEach-Object { "$($_.DriveLetter): [$($_.FileSystem)]" }) -join ", "
    Add-Check "ntfs_filesystem" "FAIL" "存在非NTFS文件系统分区: $nonNtfsList" @{ non_ntfs_volumes = $nonNtfsList }
} else {
    $ntfsList = ($allVolumes | ForEach-Object { "$($_.DriveLetter): [$($_.FileSystem)]" }) -join ", "
    Add-Check "ntfs_filesystem" "PASS" "所有分区均为NTFS/ReFS文件系统" @{ volumes = $ntfsList }
}

# ===== 7. 动态磁盘检查 =====
Write-Host "[7/19] 检查磁盘类型（基本磁盘/动态磁盘）..."
$dynamicDisks = Get-Disk -ErrorAction SilentlyContinue | Where-Object { $_.PartitionStyle -eq "GPT" -and $_.BusType -eq "SATA" }
$diskTypes = @()
$hasDynamicDisk = $false
try {
    $dpScript = Join-Path $env:TEMP "diskpart_list.txt"
    "list disk" | Out-File -FilePath $dpScript -Encoding ascii
    $diskPartInfo = diskpart /s $dpScript 2>$null
    Remove-Item -Path $dpScript -Force -ErrorAction SilentlyContinue
    if ($diskPartInfo -match "Dynamic") { $hasDynamicDisk = $true }
} catch {}
$allDisks = Get-Disk -ErrorAction SilentlyContinue
foreach ($d in $allDisks) {
    $diskTypes += @{ number = $d.Number; partition_style = $d.PartitionStyle; bus_type = $d.BusType }
}
if ($hasDynamicDisk) {
    Add-Check "disk_type" "FAIL" "检测到动态磁盘，SMS不支持动态磁盘迁移，请转换为基本磁盘" @{ disks = $diskTypes }
} else {
    Add-Check "disk_type" "PASS" "未检测到动态磁盘" @{ disks = $diskTypes }
}

# ===== 8. 分区可用空间检查 =====
Write-Host "[8/19] 检查分区可用空间..."
$partitionIssues = @()
$partitionInfo = @()
foreach ($vol in $allVolumes) {
    if ($vol.DriveLetter -and $vol.Size -gt 0) {
        $sizeMB = [math]::Round($vol.Size / 1MB, 2)
        $freeMB = [math]::Round($vol.SizeRemaining / 1MB, 2)
        $partitionInfo += @{ drive = "$($vol.DriveLetter):"; size_mb = $sizeMB; free_mb = $freeMB }
        if ($sizeMB -gt 600 -and $freeMB -lt 320) {
            $partitionIssues += "$($vol.DriveLetter): (分区${sizeMB}MB > 600MB，可用${freeMB}MB < 320MB)"
        }
        if ($sizeMB -le 600 -and $sizeMB -gt 0 -and $freeMB -lt 40) {
            $partitionIssues += "$($vol.DriveLetter): (分区${sizeMB}MB < 600MB，可用${freeMB}MB < 40MB)"
        }
    }
}
if ($partitionIssues) {
    Add-Check "partition_space" "FAIL" "分区可用空间不足: $($partitionIssues -join '; ')" @{ partitions = $partitionInfo; issues = $partitionIssues }
} else {
    Add-Check "partition_space" "PASS" "所有分区可用空间满足要求" @{ partitions = $partitionInfo }
}

# ===== 9. 防火墙检查 =====
Write-Host "[9/19] 检查防火墙规则..."
$fwProfiles = Get-NetFirewallProfile -ErrorAction SilentlyContinue
$fwInfo = @{}
foreach ($profile in $fwProfiles) {
    $fwInfo[$profile.Name] = $profile.Enabled
}
$winrmRule = Get-NetFirewallRule -DisplayName "Windows Remote Management*" -ErrorAction SilentlyContinue
if ($winrmRule) {
    Add-Check "firewall" "PASS" "WinRM防火墙规则存在" @{ profiles = $fwInfo; winrm_rule_enabled = [bool]$winrmRule.Enabled }
} else {
    Add-Check "firewall" "WARN" "未找到WinRM防火墙规则，请确保5985端口可达" @{ profiles = $fwInfo }
}

# ===== 10. 内存检查 =====
Write-Host "[10/19] 检查内存..."
$memInfo = Get-CimInstance -ClassName Win32_ComputerSystem
$memGB = [math]::Round($memInfo.TotalPhysicalMemory / 1GB, 2)
$minMemGB = 2
$availMemMB = [math]::Round(($memInfo.TotalPhysicalMemory - (Get-CimInstance Win32_OperatingSystem).TotalVisibleMemorySize * 1KB) / 1MB, 2)
if ($memGB -ge $minMemGB) {
    if ($availMemMB -gt 256) {
        Add-Check "memory" "PASS" "内存充足且可用内存>256MB" @{ total_gb = $memGB; minimum_gb = $minMemGB; available_mb = $availMemMB }
    } else {
        Add-Check "memory" "FAIL" "可用内存不足256MB（当前: ${availMemMB}MB）" @{ total_gb = $memGB; available_mb = $availMemMB }
    }
} else {
    Add-Check "memory" "FAIL" "内存不足，需要至少${minMemGB}GB" @{ total_gb = $memGB; minimum_gb = $minMemGB }
}

# ===== 11. CPU检查 =====
Write-Host "[11/19] 检查CPU..."
$cpuInfo = Get-CimInstance -ClassName Win32_Processor
$cpuCores = ($cpuInfo | Measure-Object -Property NumberOfCores -Sum).Sum
$minCores = 2
$cpuLoad = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
if ($cpuCores -ge $minCores) {
    if ($cpuLoad -lt 80) {
        Add-Check "cpu" "PASS" "CPU核心数满足要求且利用率<80%" @{ cores = $cpuCores; minimum = $minCores; load_percent = $cpuLoad }
    } else {
        Add-Check "cpu" "FAIL" "CPU利用率过高（${cpuLoad}%，需<80%）" @{ cores = $cpuCores; load_percent = $cpuLoad }
    }
} else {
    Add-Check "cpu" "WARN" "CPU核心数较少，可能影响迁移性能" @{ cores = $cpuCores; minimum = $minCores }
}

# ===== 12. 网络连通性检查 =====
Write-Host "[12/19] 检查网络连通性..."
$networkAdapters = Get-NetAdapter | Where-Object { $_.Status -eq "Up" }
$activeIPs = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne "127.0.0.1" -and $_.PrefixOrigin -ne "WellKnown" }
Add-Check "network" "PASS" "网络接口正常" @{
    adapter_count = $networkAdapters.Count
    ip_addresses = ($activeIPs.IPAddress -join ", ")
}

# ===== 13. 已安装Agent检查 =====
Write-Host "[13/19] 检查SMS Agent..."
$smsAgent = Get-Service -Name "SMSAgentService" -ErrorAction SilentlyContinue
if ($smsAgent) {
    Add-Check "sms_agent" "PASS" "SMS Agent已安装" @{ status = $smsAgent.Status; start_type = $smsAgent.StartType }
} else {
    Add-Check "sms_agent" "INFO" "SMS Agent未安装（迁移时会自动安装）"
}

# ===== 14. 磁盘数量检查 =====
Write-Host "[14/19] 检查磁盘数量（≤23块）..."
$diskCount = (Get-Disk -ErrorAction SilentlyContinue | Measure-Object).Count
if ($diskCount -le 23) {
    Add-Check "disk_count" "PASS" "磁盘数量满足要求（≤23）" @{ count = $diskCount; max = 23 }
} else {
    Add-Check "disk_count" "FAIL" "磁盘数量超过限制（${diskCount} > 23）" @{ count = $diskCount; max = 23 }
}

# ===== 15. RAID检查 =====
Write-Host "[15/19] 检查RAID配置..."
$raidControllers = Get-CimInstance -ClassName Win32_SCSIController -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "RAID|Array|Controller" }
if ($raidControllers) {
    $raidNames = ($raidControllers.Name | Select-Object -Unique) -join ", "
    Add-Check "raid" "FAIL" "检测到RAID控制器，SMS不支持RAID: $raidNames" @{ controllers = $raidNames }
} else {
    Add-Check "raid" "PASS" "未检测到RAID控制器" @{}
}

# ===== 16. BitLocker加密检查 =====
Write-Host "[16/19] 检查BitLocker加密..."
$bitlockerVolumes = Get-BitLockerVolume -ErrorAction SilentlyContinue | Where-Object { $_.ProtectionStatus -eq "On" }
if ($bitlockerVolumes) {
    $encryptedDrives = ($bitlockerVolumes.MountPoint -join ", ")
    Add-Check "bitlocker" "FAIL" "检测到BitLocker加密，SMS不支持: $encryptedDrives" @{ encrypted_volumes = $encryptedDrives }
} else {
    Add-Check "bitlocker" "PASS" "未检测到BitLocker加密" @{}
}

# ===== 17. 系统卷位置检查 =====
Write-Host "[17/19] 检查系统卷位置（应在磁盘1）..."
$systemDrive = $env:SystemDrive
$systemVolume = Get-Volume -DriveLetter $systemDrive[0] -ErrorAction SilentlyContinue
if ($systemVolume) {
    $systemDisk = Get-Disk -Number $systemVolume.DiskNumber -ErrorAction SilentlyContinue
    if ($systemDisk -and $systemDisk.Number -eq 0) {
        Add-Check "system_volume" "PASS" "系统卷在磁盘1（DiskNumber=0）" @{ disk_number = $systemDisk.Number; drive = $systemDrive }
    } else {
        Add-Check "system_volume" "WARN" "系统卷不在磁盘1，可能导致迁移问题" @{ disk_number = $systemVolume.DiskNumber; drive = $systemDrive }
    }
} else {
    Add-Check "system_volume" "WARN" "无法确定系统卷位置" @{}
}

# ===== 18. AD域控检查 =====
Write-Host "[18/19] 检查AD域控角色..."
$adRole = Get-CimInstance -ClassName Win32_ComputerSystem -ErrorAction SilentlyContinue
$domainRole = $adRole.DomainRole
$adRoles = @{ 0="Standalone Workstation"; 1="Member Workstation"; 2="Standalone Server"; 3="Member Server"; 4="Backup Domain Controller"; 5="Primary Domain Controller" }
$roleName = $adRoles[$domainRole]
if ($domainRole -ge 4) {
    Add-Check "ad_domain_controller" "FAIL" "源端是AD域控（$roleName），SMS不支持迁移AD域控" @{ domain_role = $roleName }
} else {
    Add-Check "ad_domain_controller" "PASS" "源端不是AD域控（$roleName）" @{ domain_role = $roleName }
}

# ===== 19. 共享文件系统/ZRAM检查 =====
Write-Host "[19/19] 检查共享文件系统和ZRAM..."
$sharedFolders = Get-SmbShare -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne "IPC$" -and $_.Name -ne "ADMIN$" -and $_.Path }
$zramDevices = Get-CimInstance -ClassName Win32_PageFileUsage -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "zram" }
$issues = @()
if ($sharedFolders) { $issues += "检测到SMB共享文件夹" }
if ($zramDevices) { $issues += "检测到ZRAM设备" }
if ($issues) {
    Add-Check "shared_zram" "WARN" "检测到可能不支持的配置: $($issues -join '; ')" @{ issues = $issues }
} else {
    Add-Check "shared_zram" "PASS" "未检测到共享文件系统或ZRAM" @{}
}

# ===== 输出结果 =====
$result | ConvertTo-Json -Depth 5 | Out-File -FilePath $OutputFile -Encoding UTF8

Write-Host ""
Write-Host "=========================================="
Write-Host " 前置检查结果: $($result.overall_status)"
Write-Host " 详细结果已保存到: $OutputFile"
Write-Host "=========================================="

if ($result.overall_status -eq "FAIL") {
    Write-Host ""
    Write-Host "检查未通过，请修复以上FAIL项后重新运行。"
    exit 1
} else {
    Write-Host ""
    Write-Host "所有检查通过，可以开始迁移。"
    exit 0
}
