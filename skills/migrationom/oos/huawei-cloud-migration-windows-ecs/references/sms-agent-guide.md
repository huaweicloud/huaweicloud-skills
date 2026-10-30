# Windows SMS Agent 安装与配置指南

> **通用参考**：本文为 SMS-Agent 通用安装/排障指南；本 skill 引擎实际使用的安装目录/日志路径（如 `C:\SMS-Agent-Py3`、`C:\SMS-Agent-Py2`）见 `scripts/windows_migration/README.md` 的「源端文件布局」，与本文示例路径（`C:\Program Files\CloudSMS`）不同。

## 概述

华为云SMS (Server Migration Service) Windows Agent 是用于Windows源端服务器迁移的代理程序。
与Linux Agent不同，Windows Agent以MSI/EXE安装包形式分发，通过WinRM协议进行远程管理。

### 两种安装配置方式

本 skill 支持两种 SMS-Agent 安装配置方式：

| 方式 | 适用场景 | 实现文件 | 说明 |
|------|----------|----------|------|
| **AutoIt GUI 自动化**（推荐） | Windows Server 2012+（Python3 GUI Agent）+ RDP 会话 | `scripts/windows_migration/scripts/py3/` | 通过 AutoIt v3 自动操作 SMS-Agent GUI 界面，输入 AK/SK/Domain 并完成注册 |
| **MSI/Service 静默安装** | 通用 Windows 服务器（含 2008/7 Python2 CLI Agent） | 见下方 2.2 节 | 通过 MSI 安装包 + Windows Service 方式安装配置，无 GUI 依赖 |

> **AutoIt 自动化方式**是本 skill 的核心实现，通过 WinRM + schtasks + AutoIt 三层调用链
> 在远程 Windows 上自动完成 SMS-Agent GUI 配置。详见
> [`sms-agent-automation-guide.md`](./sms-agent-automation-guide.md) 和
> 相关实现见 `references/sms-agent-automation-guide.md` 与 `scripts/windows_migration/scripts/py3/`。

## 1. 前置条件

### 1.1 源端Windows服务器要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows Server 2008 / 2008 R2 / 2012 / 2012 R2 / 2016 / 2019 / 2022 / 2025，以及 Windows 7 / 8.1 / 10 / 11（64位） |
| 文件系统 | **NTFS**（不支持 FAT32/exFAT 等其他文件系统） |
| 磁盘类型 | **基本磁盘**（Basic Disk），不支持动态磁盘（Dynamic Disk）迁移 |
| 分区可用空间 | 分区 > 600MB 时可用空间 ≥ 320MB；分区 < 600MB 时可用空间 ≥ 40MB |
| .NET Framework | 4.5 或更高版本 |
| PowerShell | 3.0 或更高版本 |
| WinRM | 已启用并配置（端口5985 HTTP / 5986 HTTPS） |
| 磁盘空间 | 系统盘至少剩余 2GB |
| 内存 | 至少 2GB |
| 网络 | 可访问公网（公网迁移模式）或可访问VPC内网（私网迁移模式） |

### 1.2 Agent 版本选择

迁移前需根据系统版本选择合适的 SMS Agent 版本：

| 源端操作系统 | Agent 版本 | 界面类型 | 说明 |
|-------------|-----------|----------|------|
| Windows Server 2012 / 2012 R2 / 2016 / 2019 / 2022 / 2025 | **Python3 Agent** | 图形界面（GUI） | 支持 AutoIt 自动化配置，推荐使用 |
| Windows Server 2008 / 2008 R2 / Windows 7 | **Python2 Agent** | 命令行界面（CLI） | 通过命令行参数配置，无 GUI 依赖 |

> **注意**: Python2 Agent 不支持 AutoIt GUI 自动化方式，需使用 MSI/Service 静默安装方式（见下方 2.2 节）。

### 1.3 WinRM 配置要求

在源端Windows服务器上执行以下PowerShell命令配置WinRM：

```powershell
# 启用WinRM
Enable-PSRemoting -Force

# 设置WinRM服务启动类型
Set-Service WinRM -StartupType Automatic

# 配置WinRM监听器
winrm quickconfig -q

# 设置认证方式
winrm set winrm/config/client/auth '@{Basic="true"}'
winrm set winrm/config/service/auth '@{Basic="true"}'

# 允许未加密（仅公网迁移测试环境，生产环境建议使用HTTPS）
winrm set winrm/config/service '@{AllowUnencrypted="true"}'

# 设置最大内存限制（每Shell）
winrm set winrm/config/winrs '@{MaxMemoryPerShellMB="1024"}'

# 防火墙开放WinRM端口
netsh advfirewall firewall add rule name="WinRM-HTTP" dir=in action=allow protocol=TCP localport=5985
```

### 1.4 HTTPS WinRM配置（推荐生产环境）

```powershell
# 创建自签名证书
$cert = New-SelfSignedCertificate -DnsName $env:COMPUTERNAME -CertStoreLocation Cert:\LocalMachine\My

# 创建WinRM HTTPS监听器
winrm create winrm/config/Listener?Address=*+Transport=HTTPS `@`{Port=`"5986`";CertificateThumbprint=`"$($cert.Thumbprint)`"`}

# 防火墙开放5986端口
netsh advfirewall firewall add rule name="WinRM-HTTPS" dir=in action=allow protocol=TCP localport=5986
```

### 1.5 代理服务器配置（可选）

源端无法直连华为云时，可配置代理服务器：

```powershell
# 设置系统代理
netsh winhttp set proxy proxy-server="http=proxy.example.com:8080;https=proxy.example.com:8080" bypass-list="*.local"

# 或在 Agent 配置文件中设置
# C:\Program Files\CloudSMS\agent\config\agent_config.cfg
[proxy]
http_proxy = http://proxy.example.com:8080
https_proxy = http://proxy.example.com:8080
no_proxy = localhost,127.0.0.1
```

### 1.6 企业项目配置（可选）

Agent 注册时可指定企业项目：

```powershell
# 在 Agent 配置文件中设置企业项目
# C:\Program Files\CloudSMS\agent\config\agent_config.cfg
[server]
enterprise_project = default
```

> 通过环境变量 `migration_enterprise_project` 设置，默认为 `default`。

### 1.7 CMS 证书验证

SMS Agent 安装时会自动验证 CMS 证书。如证书验证失败：

```powershell
# 检查系统时间是否正确（证书验证依赖系统时间）
w32tm /resync

# 检查根证书是否完整
certutil -store Root

# 如需跳过证书验证（不推荐，仅用于测试）
# 在 agent_config.cfg 中设置
[server]
verify_cert = false
```

## 2. SMS Agent 安装

### 2.1 自动安装（通过WinRM远程安装）

本 skill 支持通过 WinRM 远程自动安装 SMS Agent（真实入口：`scripts/windows_migration/unified_migrate.py` Phase A；控制面封装 `core/sms_client.py` / `core/target_provider.py`）：

```python
# 伪代码示意（非本仓真实 API；真实入口见 unified_migrate.py / core/sms_client.py）
from sms_ops import SMSOperations
sms = SMSOperations(hcloud)
result = sms.register_source(
    name="my-windows-server",
    ip="10.0.0.1",
    os_type="WINDOWS",
    use_public_ip=True
)
```

### 2.2 手动安装

1. 从华为云SMS控制台下载Windows Agent安装包
   - 登录华为云控制台 → 迁移 → 主机迁移服务 → 工具下载
   - 下载 `SMS-Agent-Windows-x.x.x.zip`

2. 在源端服务器上执行安装：

```powershell
# 解压安装包
Expand-Archive -Path SMS-Agent-Windows-x.x.x.zip -DestinationPath C:\SMS-Agent

# 执行安装脚本
cd C:\SMS-Agent
.\install.bat

# 或使用MSI静默安装
msiexec /i SMS-Agent.msi /quiet /norestart
```

3. 配置Agent：

```powershell
# 编辑配置文件
notepad C:\Program Files\CloudSMS\agent\config\agent_config.cfg

# 设置SMS服务端地址
[server]
url = https://sms.cn-north-4.myhuaweicloud.com

# 启动Agent服务
net start SMSAgentService
```

### 2.3 验证Agent安装

```powershell
# 检查服务状态
Get-Service SMSAgentService

# 检查进程
Get-Process -Name "SMSAgent*"

# 查看Agent日志
Get-Content "C:\Program Files\CloudSMS\agent\logs\agent.log" -Tail 50
```

## 3. Agent 常用操作

### 3.1 服务管理

```powershell
# 启动
net start SMSAgentService

# 停止
net stop SMSAgentService

# 重启
net stop SMSAgentService && net start SMSAgentService

# 查看状态
sc query SMSAgentService
```

### 3.2 日志查看

```powershell
# Agent主日志
Get-Content "C:\Program Files\CloudSMS\agent\logs\agent.log" -Tail 100

# 迁移日志
Get-Content "C:\Program Files\CloudSMS\agent\logs\migration.log" -Tail 100

# 错误日志
Get-Content "C:\Program Files\CloudSMS\agent\logs\error.log" -Tail 50
```

### 3.3 卸载Agent

```powershell
# 停止服务
net stop SMSAgentService

# MSI卸载
msiexec /x {ProductCode} /quiet /norestart

# 或使用安装目录的卸载脚本
cd C:\Program Files\CloudSMS\agent
.\uninstall.bat

# 清理残留
Remove-Item -Recurse -Force "C:\Program Files\CloudSMS"
```

## 4. 常见问题

### Q1: WinRM连接超时

**原因**: 防火墙阻止5985/5986端口，或WinRM服务未启动

**解决**:
```powershell
# 检查WinRM服务
Get-Service WinRM

# 检查监听器
winrm enumerate winrm/config/listener

# 检查防火墙规则
Get-NetFirewallRule -DisplayName "WinRM*"
```

### Q2: Agent安装失败

**原因**: .NET Framework版本不足，或权限不够

**解决**:
```powershell
# 检查.NET版本
Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP' -Recurse |
  Get-ItemProperty -Name Version,Release -EA 0 |
  Where { $_.PSChildName -match '^(?!S)\p{L}' } |
  Select PSChildName, Version, Release

# 以管理员权限运行安装
Start-Process -FilePath "msiexec.exe" -ArgumentList "/i SMS-Agent.msi /quiet" -Verb RunAs
```

### Q3: Agent无法连接SMS服务端

**原因**: 网络不通或DNS解析失败

**解决**:
```powershell
# 测试网络连通性
Test-NetConnection sms.cn-north-4.myhuaweicloud.com -Port 443

# 检查DNS解析
Resolve-DnsName sms.cn-north-4.myhuaweicloud.com

# 检查代理设置
netsh winhttp show proxy
```

### Q4: 源端磁盘变更后增量同步失败

**原因**: SMS Agent 无法感知源端磁盘变更（如新增/删除/扩容磁盘）

**解决**:
```powershell
# 重启 Agent 服务
Restart-Service SMSAgentService

# 重新刷新磁盘信息（通过 hcloud）
# hcloud SMS PutDiskInfo --server-id <server_id>

# 重新创建迁移任务
```

> **重要**: 源端磁盘调整后无法增量同步，必须重启 Agent 并刷新磁盘信息。

### Q5: Agent 注册后显示在错误的企业项目下

**原因**: Agent 配置中企业项目设置不正确

**解决**:
- 检查 `agent_config.cfg` 中的 `enterprise_project` 设置
- 检查环境变量 `migration_enterprise_project`
- 重新注册 Agent

## 5. Windows Agent vs Linux Agent 对比

| 特性 | Windows Agent | Linux Agent |
|------|---------------|-------------|
| 安装方式 | MSI/EXE安装包 | tar.gz解压 |
| 服务管理 | Windows Service (net start/stop) | systemd (systemctl) |
| 远程协议 | WinRM (5985/5986) | SSH (22) |
| 迁移方式 | MIGRATE_BLOCK (块级) | MIGRATE_FILE (文件级) |
| 认证方式 | Administrator密码 | root密码/密钥 |
| 配置路径 | C:\Program Files\CloudSMS\ | /usr/local/cloudsms/ |
| 日志路径 | C:\Program Files\CloudSMS\logs\ | /var/log/cloudsms/ |
| 防火墙 | netsh / Windows Firewall | iptables / firewalld |
