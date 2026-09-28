# SMS Agent Deployment and Installation Guide

This guide provides step-by-step instructions to deploy the Huawei Cloud Server Migration Service (SMS) Agent on source servers (IDC, Alibaba Cloud, Tencent Cloud, AWS).

> [!NOTE]
> **Applicability**:
> - **Scenario B (Fresh Host / Not Yet Registered)**: Complete the procedures in Sections 1 through 4 to download, install, and authenticate the SMS Agent.
> - **Scenario A (Agent Already Installed & Queryable)**: Skip this guide. Proceed directly to target template setup in Phase 3. If an existing agent shows `state: "unavailable"` or offline, use Section 5 to restart or diagnose the running service.

---

## 1. Prerequisites on Source Server

Before deploying the Agent, verify the preliminary checks in `references/pre-migration-checklist.md`:
1. **Network**: Outbound TCP 443 to `sms.<region>.myhuaweicloud.com`, and outbound TCP 22/8899/8900 to target ECS. Target security group must permit required inbound ports from the source IP.
2. **Clock Sync**: System clock drift ≤ 15 minutes (`chronyc sources -v`, `ntpdate pool.ntp.org`, or `w32tm /resync`).
3. **Dependencies**:
   - **Linux**: `rsync`, `tar`, `nohup`, `python` (`yum install -y rsync tar` or `apt-get update && apt-get install -y rsync tar`).
   - **Windows**: PowerShell 3.0+ and VSS (Volume Shadow Copy) service enabled.

---

## 2. Linux Agent Installation

### Step 1: Download the Linux Agent Package

Select the download URL corresponding to your target Huawei Cloud site:

- **China Site (e.g., `cn-north-4` Beijing-4)**:
```bash
wget -t 3 -T 15 https://sms-resource-cn-cn-north-4.obs.cn-north-4.myhuaweicloud.com/SMS-Agent.tar.gz
```

- **International Site (Singapore `ap-southeast-3`)**:
```bash
wget -t 3 -T 15 https://sms-resource-intl-ap-southeast-3.obs.ap-southeast-3.myhuaweicloud.com/SMS-Agent.tar.gz
```

Decompress and enter the directory:
```bash
tar -zxvf SMS-Agent.tar.gz
cd SMS-Agent
```

### Step 2: Run the Startup Script
```bash
# Execute with root privileges (or via nohup for background execution)
sudo ./startup.sh
```

### Step 3: Enter Authentication Out-of-Band
When prompted by the script:
- **AK**: Enter your Huawei Cloud Access Key (AK).
- **SK**: Enter your Huawei Cloud Secret Key (SK) silently.
- **SMS Domain Name**: Enter the target region SMS service endpoint domain:
  - **China Site (e.g., `cn-north-4`)**: `sms.cn-north-4.myhuaweicloud.com`
  - **International Site (Singapore `ap-southeast-3`)**: `sms.ap-southeast-3.myhuaweicloud.com`
  *(Do not enter just the region identifier).*
- **Enterprise Project ID**: Enter your Enterprise Project ID (or enter `0` for the default enterprise project).

Upon successful authentication, the Agent registers the source server with SMS, runs 14 automated pre-checks, and stays connected.

---

## 3. Windows Agent Installation

### Step 1: Download the Windows Agent

Select the download package matching your target site:

- **China Site (e.g., `cn-north-4` Beijing-4)**:
```powershell
Invoke-WebRequest -Uri "https://sms-resource-cn-cn-north-4.obs.cn-north-4.myhuaweicloud.com/SMS-Agent-Py3.exe" -OutFile "SMS-Agent.exe"
```

- **International Site (Singapore `ap-southeast-3`)**:
```powershell
Invoke-WebRequest -Uri "https://sms-resource-intl-ap-southeast-3.obs.ap-southeast-3.myhuaweicloud.com/SMS-Agent-Py3.exe" -OutFile "SMS-Agent.exe"
```

### Step 2: Launch Installer as Administrator
Run `SMS-Agent.exe` as Administrator and input the authentication parameters out-of-band:
- **AK**: Huawei Cloud Access Key (AK).
- **SK**: Huawei Cloud Secret Key (SK).
- **SMS Domain Name**: SMS service endpoint domain:
  - **China Site (e.g., `cn-north-4`)**: `sms.cn-north-4.myhuaweicloud.com`
  - **International Site (Singapore `ap-southeast-3`)**: `sms.ap-southeast-3.myhuaweicloud.com`
- **Enterprise Project ID**: Target Enterprise Project ID (or enter `0` for default).

### Step 3: Verify Windows Service
Confirm that the `SMS Agent` service is running in Windows Services (`services.msc`).

---

## 4. Verification in Cloud Console / CLI

After installation, verify that the source server appears in the registered servers list:
```bash
# China Site:
hcloud SMS ListServers --cli-region=cn-north-4 --limit=5

# International Site (Singapore):
hcloud SMS ListServers --cli-region=ap-southeast-3 --limit=5
```
Inspect the pre-check results under the `checks` array in the JSON response. If pre-check indicates network or security group issues, refer to `references/troubleshooting-guide.md`.

---

## 5. Agent Maintenance & Recovery (For Existing Agents)

When an existing source server in Scenario A displays `state: "unavailable"`, use the following commands to check and restart the Agent daemon:

### Linux
Navigate to the agent directory (e.g., `/root/SMS-Agent`):
```bash
# Check running status
sudo ./check_agent.sh

# Restart agent process
sudo ./stop.sh
sudo ./startup.sh

# Inspect runtime logs
tail -n 100 /root/SMS-Agent/log/sms-agent.log
```

### Windows
Run PowerShell as Administrator:
```powershell
# Check SMS Agent service status
Get-Service -Name "SMS Agent"

# Restart the service
Restart-Service -Name "SMS Agent"
```

