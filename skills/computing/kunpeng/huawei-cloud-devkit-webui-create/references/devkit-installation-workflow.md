# DevKit Installation Workflow (Task 3-7)

After establishing an SSH connection to the target server, follow the workflow below to complete the DevKit installation.

## Task 3: Environment Check

After connecting to the target server via SSH, first check the system environment:

```bash
# Check system architecture (must be aarch64)
uname -m

# Check operating system (must be in the compatible list)
cat /etc/os-release
# Compatible list: openEuler 24.03 LTS / CentOS 7.6 / Ubuntu 18.04 / Kylin V10 / UOS 20

# Check disk space (requires >= 2GB available)
df -h /

# Check memory (requires >= 4GB)
free -h
```

## Task 4: Install Dependency Packages

DevKit installation requires numerous dependency packages, which **must be installed before installing DevKit**. Install them in two groups:

**Group 1 (Framework Base Dependencies):**

```bash
yum install -y file which hostname procps iproute make acl gcc-c++ gcc glibc openssl sqlite wget lsof unzip gzip expect libcap rpm-build e2fsprogs crontabs pcre pcre-devel zlib zlib-devel openssl-devel
```

**Group 2 (Plugin Dependencies):**

```bash
yum install -y unzip make expect perf gcc-c++ gcc glibc openssl util-linux binutils dmidecode sysstat numactl sqlite perl logrotate curl zip libffi-devel pcre pcre-devel zlib zlib-devel libunwind openssl-devel graphviz psmisc strace pciutils lsscsi procps initscripts policycoreutils ethtool smartmontools kmod net-tools rsyslog gzip iputils traceroute tcpdump fio ipmitool man bc crontabs libaio-devel numactl-devel
```

> **⚠️ Critical: expect must be installed**
>
> The DevKit installation script is interactive and requires the expect tool to automate interactive input handling.
> If expect is not installed, the installation script will exit with an error.
> ```bash
> yum install -y expect
> ```

## Task 5: Download Installation Package

Download the DevKit-All installation package from the Kunpeng community OBS:

```bash
cd /tmp

# Download DevKit-All package (using 26.1.RC1 as an example; replace with the actual version)
wget -c "https://kunpeng-repo.obs.cn-north-4.myhuaweicloud.com/Kunpeng%20DevKit/Kunpeng%20DevKit%2026.1.RC1/DevKit-All-26.1.RC1-Linux-Kunpeng.tar.gz" \
  -O DevKit-All-26.1.RC1-Linux-Kunpeng.tar.gz
```

> **How to obtain the installation package download URL:**
>
> The Kunpeng community download center (https://www.hikunpeng.com/developer/devkit/download) is a SPA dynamically rendered page, so download links cannot be scraped directly.
> Users need to manually obtain the download URL from a browser, or retrieve it from the Kunpeng community resource repository (OBS).
>
> Common URL format:
> ```
> https://kunpeng-repo.obs.cn-north-4.myhuaweicloud.com/Kunpeng%20DevKit/Kunpeng%20DevKit%20{version}/DevKit-All-{version}-Linux-Kunpeng.tar.gz
> ```

> **The installation package is approximately 1.4GB; downloading may take several minutes**

## Task 6: Interactive Installation

DevKit's install.sh is an **interactive script** containing multiple steps that require user input.
**You must use expect to automate all interactive inputs**.

### 6.1 Extract the Outer Installation Package

```bash
cd /tmp
mkdir -p DevKit-All
tar -xzf DevKit-All-26.1.RC1-Linux-Kunpeng.tar.gz -C DevKit-All
```

### 6.2 Interactive Steps Checklist

The installation script `install.sh -a` involves the following interactive steps during execution:

| No. | Interactive Prompt | Input Value | Description |
|-----|-------------------|-------------|-------------|
| 1 | "Enter the sequence number of the tool access mode" | `1` | Select username/password mode (not SSO) |
| 2 | "Do you want to authorize the tool to handle the items failed" | `y` | Authorize handling of environment check failures (optional dependency missing) |
| 3 | "Enter the installation path" | `\r` (Enter) | Default installation path /opt |
| 4 | "Please enter the installation port" | `\r` (Enter) | Default port 8086 |
| 5 | "is available, do you want to use it" | `y` | Confirm using the available port |
| 6 | "Do you want to continue" | `y` | Firewall port confirmation |
| 7 | "Do you want to install the dependencies for assembly?" | `y` | Install assembly dependencies (glibc 2.28, etc.) |

### 6.3 expect Automated Installation Script

Write the following expect script to the server and execute it:

```expect
#!/usr/bin/expect -f
set timeout 600
spawn bash install.sh -a
expect {
    "access mode for your installation" {
        send "1\r"
        exp_continue
    }
    "Do you want to authorize" {
        send "y\r"
        exp_continue
    }
    "Enter theBinstallation path" {
        send "\r"
        exp_continue
    }
    "Please enter the installation port" {
        send "\r"
        exp_continue
    }
    "is available, do you want" {
        send "y\r"
        exp_continue
    }
    "Do you want to continue" {
        send "y\r"
        exp_continue
    }
    "Enter the serial number of the plug-in" {
        send "1,2,3,4,5,6\r"
        exp_continue
    }
    "select the number" {
        send "1\r"
        exp_continue
    }
    "Enter the serial number" {
        send "1\r"
        exp_continue
    }
    eof
}
```

**Usage:**

```bash
# 1. Write the expect script to the server
cat > /tmp/auto_install_devkit.expect << 'EXPECTEOF'
<the expect script content above>
EXPECTEOF
chmod +x /tmp/auto_install_devkit.expect

# 2. Enter the installation directory and run as guarded background process
cd /tmp/DevKit-All/DevKit-All-26.1.RC1-Linux-Kunpeng
# Previous extraction directory retained for inspection
PID_FILE="/tmp/devkit_install.pid"
nohup /tmp/auto_install_devkit.expect > /tmp/devkit_install.log 2>&1 &
INSTALL_PID=$!
echo "${INSTALL_PID}" > "${PID_FILE}"
echo "Install PID: ${INSTALL_PID} (saved to ${PID_FILE})"
echo "  Monitor: tail -f /tmp/devkit_install.log"
echo "  Status:  kill -0 \$(cat ${PID_FILE}) 2>/dev/null && echo RUNNING || echo STOPPED"
echo "  Abort:   kill \$(cat ${PID_FILE})  then  rm -f ${PID_FILE}"

# 3. Poll and wait for installation to complete (with 600s timeout)
MAX_WAIT=600; WAITED=0
while kill -0 ${INSTALL_PID} 2>/dev/null && [[ ${WAITED} -lt ${MAX_WAIT} ]]; do sleep 10; WAITED=$((WAITED+10)); done

# 4. View the installation log
tail -20 /tmp/devkit_install.log
```

> **⚠️ Critical: Guarded background execution required**
>
> DevKit installation takes a long time (approximately 5-10 minutes). If executed directly in the SSH session, session disconnection will cause the installation to be interrupted.
> Use a **guarded background process** with PID tracking, timeout watchdog, and explicit control commands:
> - **PID file**: `/tmp/devkit_install.pid` — persistent process identifier
> - **Timeout**: 600s watchdog prevents indefinite hang
> - **Monitor**: `tail -f /tmp/devkit_install.log` — real-time log
> - **Status**: `kill -0 $(cat /tmp/devkit_install.pid) 2>/dev/null && echo RUNNING || echo STOPPED`
> - **Abort**: `kill $(cat /tmp/devkit_install.pid)` then `rm -f /tmp/devkit_install.pid`

> **⚠️ Critical: expect matching order**
>
> expect uses the **first-match** principle; `exp_continue` causes the script to continue waiting for the next interaction after a match.
> The matching strings for interactive prompts must be precise enough to avoid false matches.
> In particular, "Do you want to authorize" and "Do you want to continue" are different interaction points.

## Task 7: Verify Installation Result

After installation is complete, verify the status of each service:

```bash
# 1. Check installation directory
ls -la /opt/DevKit/

# 2. Check installed plugins
ls /opt/DevKit/devkitplugins/

# 3. Check service status
systemctl status devkit_nginx --no-pager
systemctl status gunicorn_framework --no-pager
systemctl status gunicorn_plugin --no-pager

# 4. Check port listening
ss -tlnp | grep -E "8086|8002|50051|7996"
```

**Success Criteria:**

| Check Item | Expected Result |
|------------|-----------------|
| Installation directory `/opt/DevKit/` | Exists and contains subdirectories such as config, dev5devkitframework, devkitplugins |
| devkit_nginx service | active (running) |
| gunicorn_framework service | active (running) |
| gunicorn_plugin service | active (running) |
| Port 8086 | LISTEN (HTTPS access port) |
| Port 8002 | LISTEN (HTTP internal port) |
| Port 7996 | LISTEN (Plugin internal port) |
| Port 50051 | On-demand LISTEN (gRPC cluster port; automatically listened when users start performance analysis tasks in WebUI; not listening after installation is normal) |
