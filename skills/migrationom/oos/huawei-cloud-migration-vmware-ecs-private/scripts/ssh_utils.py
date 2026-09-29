#!/usr/bin/env python3
"""
ssh_utils.py — SSH 工具 (私网迁移版)

基于现有 skill 的 ssh_utils.py 改造，增加 GOST 隧道支持。
在私网迁移场景中，SSH 连接源端通过 GOST 管理通道而非直连/BMS跳板机。

两种连接模式:
  1. direct: 直连源端 (VPN 打通后可直接访问源端内网 IP)
  2. gost:   通过 GOST 端口转发连接源端 (代理 ECS 上的 GOST 转发源端 SSH)
"""

import os
import time
import logging
import base64

try:
    import paramiko
except ImportError:
    paramiko = None

logger = logging.getLogger(__name__)


def _build_start_script(agent_path, ak, sk, sms_domain, proxy_host=None, proxy_port=None):
    """Build start_agent.sh content with proxy support.

    私网迁移中 SMS Agent 需要通过 squid 代理访问华为云 API。
    通过环境变量 http_proxy/https_proxy 配置代理。

    Args:
        agent_path: Remote directory containing the agent binary
        ak: SMS Agent access key
        sk: SMS Agent secret key
        sms_domain: SMS domain
        proxy_host: squid 代理主机 IP
        proxy_port: squid 代理端口 (默认 3128)
    """
    proxy_env = ""
    if proxy_host and proxy_port:
        proxy_env = f"export http_proxy=http://{proxy_host}:{proxy_port}\nexport https_proxy=http://{proxy_host}:{proxy_port}\nexport HTTP_PROXY=http://{proxy_host}:{proxy_port}\nexport HTTPS_PROXY=http://{proxy_host}:{proxy_port}\n"

    return f"""#!/bin/bash
cd {agent_path}
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$(pwd)/lib
{proxy_env}
# Auto-detect linuxmain binary location
LINUXMAIN=""
for _candidate in ./linuxmain ./x64/linuxmain ./aarch64/linuxmain ./arm64/linuxmain; do
    if [ -x "$_candidate" ]; then
        LINUXMAIN="$_candidate"
        break
    fi
done
if [ -z "$LINUXMAIN" ]; then
    echo "ERROR: linuxmain binary not found in $(pwd)" >&2
    exit 1
fi
(echo '{ak} {sk} {sms_domain} '; tail -f /dev/null) | "$LINUXMAIN" > /dev/null 2>&1 &
"""


def _write_remote_script(ssh_client, script_content, remote_path="/opt/start_agent.sh"):
    """Write script content to remote host using base64 encoding."""
    b64_content = base64.b64encode(script_content.encode("utf-8")).decode("ascii")
    ssh_client.exec_command(f"echo '{b64_content}' | base64 -d > {remote_path}")
    ssh_client.exec_command(f"chmod +x {remote_path}")


class _SSHConnection:
    """轻量级 SSH 连接包装 (线程安全: 每个实例独立持有 paramiko client)

    由 SSHClient.connect() 创建并返回, 不共享任何可变状态。
    多线程并发调用 connect() 时, 每个线程拿到自己的 _SSHConnection,
    互不干扰。
    """

    def __init__(self, client, host, port, username, password=None, key_path=None):
        self.client = client        # paramiko.SSHClient (独立)
        self.host = host
        self.port = port
        self.username = username
        self.password = password    # 保存用于重连
        self.key_path = key_path    # 保存用于重连

    def close(self):
        """关闭本连接的 paramiko client"""
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None

    def reconnect(self, timeout=30):
        """使用相同参数重新创建连接 (线程安全)

        关闭旧连接并创建新的 paramiko.SSHClient。
        用于 SFTP 上传遇到 EOFError 时的自动重连。

        Returns:
            bool: 是否成功
        """
        self.close()
        if paramiko is None:
            return False
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            connect_kwargs = {
                "hostname": self.host,
                "port": self.port,
                "username": self.username,
                "timeout": timeout,
            }
            if self.key_path and os.path.exists(self.key_path):
                connect_kwargs["key_filename"] = self.key_path
            elif self.password:
                connect_kwargs["password"] = self.password
            client.connect(**connect_kwargs)
            self.client = client

            # 设置 SSH keepalive (与 connect() 一致)
            transport = client.get_transport()
            if transport:
                transport.set_keepalive(30)

            logger.info(f"SSH reconnected to {self.host}:{self.port} as {self.username}")
            return True
        except Exception as e:
            logger.error(f"Reconnect failed: {e}")
            return False


class SSHClient:
    """SSH client wrapper for remote operations.

    线程安全说明:
      - connect() 返回独立的 _SSHConnection 对象, 不修改 self 的可变属性
      - execute() / upload_file() / disconnect() 通过 ssh_conn 参数操作独立连接
      - 多线程可安全并发调用 connect() + execute() + disconnect()
    """

    def __init__(self, host, port=22, username="root", password=None, key_path=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_path = key_path
        self.client = None  # 保留用于旧接口兼容 (单线程场景)

    def connect(self, timeout=30, host=None, port=None, username=None,
                password=None, key_path=None):
        """创建新 SSH 连接, 返回独立的 _SSHConnection 对象 (线程安全)

        不修改 self 的实例属性 (host/port/username/password/key_path/client),
        而是创建全新的 paramiko.SSHClient 并包装在 _SSHConnection 中返回。
        每次调用返回独立对象, 多线程并发安全。

        Args:
            timeout: 连接超时
            host/port/username/password/key_path: 连接参数 (覆盖默认值)

        Returns:
            _SSHConnection: 独立连接对象, 调用方负责 disconnect()
        """
        if paramiko is None:
            raise ImportError("paramiko is required. Install: pip install paramiko")

        # 解析连接参数 (不修改 self)
        _host = host if host is not None else self.host
        _port = port if port is not None else self.port
        _username = username if username is not None else self.username
        _password = password if password is not None else self.password
        _key_path = key_path if key_path is not None else self.key_path

        # 创建独立的 paramiko client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            "hostname": _host,
            "port": _port,
            "username": _username,
            "timeout": timeout,
        }
        if _key_path and os.path.exists(_key_path):
            connect_kwargs["key_filename"] = _key_path
        elif _password:
            connect_kwargs["password"] = _password

        client.connect(**connect_kwargs)

        # 设置 SSH keepalive (防止 GOST 隧道连接超时断开)
        transport = client.get_transport()
        if transport:
            transport.set_keepalive(30)  # 每30秒发送 keepalive 包

        logger.info(f"SSH connected to {_host}:{_port} as {_username}")

        # 返回独立连接对象 (不修改 self), 保存 password/key_path 用于重连
        return _SSHConnection(client, _host, _port, _username, _password, _key_path)

    def execute(self, ssh_conn, command, timeout=300):
        """执行远程命令 (线程安全, 带重连重试)

        Args:
            ssh_conn: _SSHConnection 连接对象 (由 connect() 返回)
            command: 命令
            timeout: 超时

        Returns:
            {"stdout": str, "stderr": str, "exit_code": int}
        """
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                client = ssh_conn.client if hasattr(ssh_conn, 'client') else self.client
                if not client:
                    # 回退: 创建新连接 (单线程场景)
                    conn = self.connect()
                    client = conn.client

                stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
                exit_code = stdout.channel.recv_exit_status()
                out = stdout.read().decode("utf-8", errors="replace").strip()
                err = stderr.read().decode("utf-8", errors="replace").strip()

                logger.debug(f"CMD: {command}")
                logger.debug(f"EXIT: {exit_code}")
                if out:
                    logger.debug(f"STDOUT: {out[:500]}")

                return {"stdout": out, "stderr": err, "exit_code": exit_code}
            except (EOFError, Exception) as e:
                error_type = type(e).__name__
                if attempt < max_retries:
                    logger.warning(
                        f"SSH execute attempt {attempt}/{max_retries} failed "
                        f"({error_type}: {e}), reconnecting in 3s..."
                    )
                    time.sleep(3)
                    try:
                        if hasattr(ssh_conn, 'reconnect'):
                            ssh_conn.reconnect()
                        elif hasattr(ssh_conn, 'client'):
                            ssh_conn.close()
                            new_conn = self.connect()
                            ssh_conn.client = new_conn.client
                        else:
                            self.close()
                            conn = self.connect()
                            self.client = conn.client
                    except Exception as reconnect_err:
                        logger.warning(f"Reconnect failed: {reconnect_err}")
                else:
                    logger.error(
                        f"SSH execute failed after {max_retries} attempts: {error_type}: {e}"
                    )
                    return {"stdout": "", "stderr": str(e), "exit_code": -1}

        return {"stdout": "", "stderr": "max retries exceeded", "exit_code": -1}

    def disconnect(self, ssh_conn=None):
        """断开连接 (线程安全)

        关闭 ssh_conn (_SSHConnection) 上的独立连接, 而非 self.client。
        如果 ssh_conn 为 None (旧接口), 回退到关闭 self.client。
        """
        if ssh_conn is not None and hasattr(ssh_conn, 'client'):
            # 新接口: 关闭独立连接对象
            ssh_conn.close()
        else:
            # 旧接口: 关闭 self.client (单线程场景)
            self.close()

    def exec_command(self, command, timeout=300):
        """旧接口: 使用 self 的默认连接执行命令 (单线程场景)"""
        client = self.client
        if not client:
            conn = self.connect()
            client = conn.client

        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()

        logger.debug(f"CMD: {command}")
        logger.debug(f"EXIT: {exit_code}")
        if out:
            logger.debug(f"STDOUT: {out[:500]}")

        return out, err, exit_code

    def upload_file(self, ssh_conn=None, local_path=None, remote_path=None):
        """上传文件 (sms_agent_push 接口兼容)

        支持两种调用方式:
          1. upload_file(local_path, remote_path) — 旧接口
          2. upload_file(ssh_conn, local_path, remote_path) — 新接口

        SFTP 重试: 遇到 EOFError / SSHException 时自动重连重试 (最多 3 次)。
        解决并发迁移中 GOST 重启导致 SFTP 连接断开的问题。
        """
        # 参数适配: 如果 ssh_conn 是 str (路径), 说明是旧接口
        if isinstance(ssh_conn, str) and local_path is not None:
            remote_path = local_path
            local_path = ssh_conn
            ssh_conn = None

        max_retries = 5  # 从3次增加到5次, 应对 GOST 重启导致的连接中断
        retry_delay = 5  # 从3秒增加到5秒, 给 GOST 更多时间恢复
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                client = self.client
                if ssh_conn and hasattr(ssh_conn, 'client'):
                    client = ssh_conn.client
                if not client:
                    # 回退: 创建新连接 (单线程场景)
                    conn = self.connect()
                    client = conn.client

                # 检查连接是否仍然活跃, 如果不活跃则重连
                transport = client.get_transport() if client else None
                if not transport or not transport.is_active():
                    logger.warning(f"SFTP upload: SSH transport inactive, reconnecting (attempt {attempt})")
                    if ssh_conn and hasattr(ssh_conn, 'reconnect'):
                        ssh_conn.reconnect()
                        client = ssh_conn.client
                    else:
                        conn = self.connect()
                        client = conn.client

                sftp = client.open_sftp()
                sftp.put(local_path, remote_path)
                sftp.close()
                logger.info(f"Uploaded {local_path} -> {remote_path} (attempt {attempt}/{max_retries})")
                return True
            except (EOFError, Exception) as e:
                last_error = e
                error_type = type(e).__name__
                if attempt < max_retries:
                    logger.warning(
                        f"SFTP upload attempt {attempt}/{max_retries} failed "
                        f"({error_type}: {e}), reconnecting in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                    # 重连: 使用 ssh_conn 存储的参数创建新连接 (线程安全)
                    try:
                        if ssh_conn and hasattr(ssh_conn, 'reconnect'):
                            ssh_conn.reconnect()
                        elif ssh_conn and hasattr(ssh_conn, 'client'):
                            ssh_conn.close()
                            new_conn = self.connect()
                            ssh_conn.client = new_conn.client
                        else:
                            self.close()
                            conn = self.connect()
                            self.client = conn.client
                    except Exception as reconnect_err:
                        logger.warning(f"Reconnect failed: {reconnect_err}")
                else:
                    logger.error(
                        f"SFTP upload failed after {max_retries} attempts: {error_type}: {e}"
                    )

        return False

    def download_file(self, remote_path, local_path):
        """旧接口: 使用 self 的默认连接下载文件 (单线程场景)"""
        client = self.client
        if not client:
            conn = self.connect()
            client = conn.client
        sftp = client.open_sftp()
        sftp.get(remote_path, local_path)
        sftp.close()
        logger.info(f"Downloaded {remote_path} -> {local_path}")

    def close(self):
        if self.client:
            self.client.close()
            self.client = None
            logger.info("SSH connection closed")

    def __enter__(self):
        conn = self.connect()
        self.client = conn.client  # 上下文管理器场景 (单线程)
        return self

    def __exit__(self, *args):
        self.close()


def detect_os_and_hardware(ssh_client):
    """合并 OS 检测 + 硬件信息采集为单次 SSH 命令。"""
    SEP = "===HWINFO_SEP==="
    cmd = (
        f"cat /etc/os-release; echo '{SEP}';"
        f"uname -m; echo '{SEP}';"
        f"nproc; echo '{SEP}';"
        f"free -m | grep Mem; echo '{SEP}';"
        f"df -h / | tail -1; echo '{SEP}';"
        f"lsblk"
    )
    out, _, _ = ssh_client.exec_command(cmd)

    os_info = {"os": "linux", "distro": "unknown", "version": "unknown", "arch": "x86_64"}
    hw_info = {"cpu_cores": 4, "memory_mb": 8192, "raw": ""}

    if out:
        sections = out.split(SEP)
        if len(sections) > 0:
            for line in sections[0].splitlines():
                if line.startswith("ID="):
                    os_info["distro"] = line.split("=")[1].strip().strip('"')
                elif line.startswith("VERSION_ID="):
                    os_info["version"] = line.split("=")[1].strip().strip('"')
        if len(sections) > 1:
            arch = sections[1].strip()
            if arch:
                os_info["arch"] = arch
        if len(sections) > 2:
            try:
                hw_info["cpu_cores"] = int(sections[2].strip())
            except ValueError:
                pass
        if len(sections) > 3:
            parts = sections[3].split()
            if len(parts) >= 2:
                try:
                    hw_info["memory_mb"] = int(parts[1])
                except ValueError:
                    pass
        hw_info["raw"] = out

    hw_info["os_info"] = os_info
    logger.info(f"Detected OS+HW: {os_info}, CPU={hw_info['cpu_cores']}, Mem={hw_info['memory_mb']}MB")
    return os_info, hw_info


def install_agent_scp(ssh_client, local_pkg_path, ak, sk, region,
                      agent_dir="/opt/HW_agent",
                      proxy_host=None, proxy_port=3128):
    """通过 SFTP 传输 SMS Agent 包到源主机并安装 (私网版，支持代理)。

    私网迁移中 Agent 通过 squid 代理访问华为云 API。
    """
    logger.info(f"Installing SMS Agent via SCP/SFTP to {agent_dir}")

    if not os.path.exists(local_pkg_path):
        logger.error(f"Agent package not found: {local_pkg_path}")
        return False

    # Check if agent already running
    out, _, _ = ssh_client.exec_command("pgrep -x linuxmain 2>/dev/null || true")
    if out and out.strip():
        logger.info(f"SMS Agent already running (PID: {out.strip()})")
        return True

    # Check existing binary
    out, _, _ = ssh_client.exec_command(
        f"find {agent_dir} -name linuxmain -type f 2>/dev/null | head -1 || true"
    )
    if out and out.strip():
        logger.info("SMS Agent binary found, attempting to start")
        sms_domain = f"sms.{region}.myhuaweicloud.com"
        agent_path = f"{agent_dir}/SMS-Agent/agent"
        start_script = _build_start_script(agent_path, ak, sk, sms_domain, proxy_host, proxy_port)
        _write_remote_script(ssh_client, start_script)
        ssh_client.exec_command("bash /opt/start_agent.sh", timeout=10)
        time.sleep(5)
        out2, _, _ = ssh_client.exec_command("pgrep -x linuxmain 2>/dev/null || true")
        if out2 and out2.strip():
            logger.info(f"SMS Agent started (PID: {out2.strip()})")
            return True

    # Create agent directory
    ssh_client.exec_command(f"mkdir -p {agent_dir}")

    # SFTP transfer
    filename = os.path.basename(local_pkg_path)
    remote_path = f"{agent_dir}/{filename}"
    logger.info(f"  SFTP: {local_pkg_path} -> {remote_path}")
    try:
        ssh_client.upload_file(local_pkg_path, remote_path)
    except Exception as e:
        logger.error(f"  SFTP failed: {e}")
        return False

    # Extract
    if filename.endswith(".tar.gz"):
        ssh_client.exec_command(f"cd {agent_dir} && tar xzf {filename}")
    elif filename.endswith(".zip"):
        ssh_client.exec_command(f"cd {agent_dir} && unzip -o {filename}")

    # Setup
    setup_cmd = f"test -f {agent_dir}/SMS-Agent/setup.sh && cd {agent_dir}/SMS-Agent && bash setup.sh || true"
    ssh_client.exec_command(setup_cmd, timeout=60)

    # Create start script with proxy
    sms_domain = f"sms.{region}.myhuaweicloud.com"
    agent_path = f"{agent_dir}/SMS-Agent/agent"
    start_script = _build_start_script(agent_path, ak, sk, sms_domain, proxy_host, proxy_port)
    _write_remote_script(ssh_client, start_script)
    logger.info(f"Created /opt/start_agent.sh (proxy={proxy_host}:{proxy_port})")

    # Start agent
    ssh_client.exec_command("bash /opt/start_agent.sh", timeout=60)
    time.sleep(3)

    logger.info("SMS Agent installed and started")
    return True


def uninstall_agent(ssh_client, agent_dir="/opt/HW_agent"):
    """Uninstall SMS Agent from source server."""
    logger.info(f"Uninstalling SMS Agent from {agent_dir}")
    ssh_client.exec_command(f"cd {agent_dir}/SMS-Agent && ./agent_cmd.sh stop 2>/dev/null || true")
    ssh_client.exec_command(f"rm -rf {agent_dir}")
    return True


def patch_check_vol_name(ssh_client, agent_dir="/opt/HW_agent"):
    """修复 SMS Agent check_vol_name LVM 检测 bug (SMS.0515 预防)。"""
    logger.info("Checking check_vol_name LVM detection bug...")

    find_cmd = f"find {agent_dir} -name 'special_command.sh' -type f 2>/dev/null"
    out, _, _ = ssh_client.exec_command(find_cmd)
    if not out or not out.strip():
        return False

    for script_path in out.strip().splitlines():
        script_path = script_path.strip()
        if not script_path:
            continue
        out, _, _ = ssh_client.exec_command(f"cat '{script_path}'")
        if not out or "# PATCHED_CHECK_VOL_NAME_2026" in out:
            continue
        ssh_client.exec_command(f"cp '{script_path}' '{script_path}.bak.2026'")
        patch = f'''# PATCHED_CHECK_VOL_NAME_2026: Enhanced disk detection
_enhanced_disk_detect() {{
    lsblk -b -d -o NAME,SIZE,TYPE 2>/dev/null | awk '$3=="disk"{{print $1}}'
    if command -v pvs >/dev/null 2>&1; then pvs --noheadings -o pv_name 2>/dev/null | tr -d " "; fi
    swapon --show --noheadings 2>/dev/null | awk '{{print $1}}'
}}
'''
        ssh_client.exec_command(f"echo '{patch}' >> '{script_path}'")
        logger.info(f"Patch applied to {script_path}")
        return True
    return False


def freeze_disk_activity(ssh_client):
    """冻结可能修改磁盘布局的服务，预防 SMS.0515。"""
    result = {"frozen": False, "services": []}
    logger.info("Freezing disk-modifying services...")

    services = [
        ("logrotate", "systemctl stop logrotate.timer 2>/dev/null || true"),
        ("atd", "systemctl stop atd 2>/dev/null || true"),
    ]

    for svc_name, cmd in services:
        ssh_client.exec_command(cmd)
        out, _, _ = ssh_client.exec_command(f"systemctl is-active {svc_name} 2>/dev/null || true")
        if out and "inactive" in out:
            result["services"].append(svc_name)

    ssh_client.exec_command("sync")
    time.sleep(2)
    ssh_client.exec_command("touch /tmp/.sms_disk_freeze_active")
    result["frozen"] = True
    logger.info(f"Disk activity frozen: {result['services']}")
    return result


def unfreeze_disk_activity(ssh_client):
    """恢复被冻结的磁盘相关服务。"""
    logger.info("Restoring disk-related services...")
    out, _, _ = ssh_client.exec_command("test -f /tmp/.sms_disk_freeze_active && echo yes || echo no")
    if "no" in out:
        return True

    for svc, cmd in [
        ("logrotate", "systemctl start logrotate.timer 2>/dev/null || true"),
        ("atd", "systemctl start atd 2>/dev/null || true"),
    ]:
        ssh_client.exec_command(cmd)

    ssh_client.exec_command("rm -f /tmp/.sms_disk_freeze_active")
    return True


def get_disk_info_for_sms(ssh_client):
    """获取源端磁盘信息，用于与 SMS 服务端记录对比。"""
    info = {"disks": [], "lvm": {}, "mounts": [], "swap": [], "partitions": []}

    out, _, _ = ssh_client.exec_command("lsblk -b -d -o NAME,SIZE,TYPE,ROTA 2>/dev/null")
    if out:
        for line in out.strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 3 and parts[2] == "disk":
                info["disks"].append({
                    "name": parts[0],
                    "size_bytes": int(parts[1]) if parts[1].isdigit() else 0,
                })

    out, _, _ = ssh_client.exec_command("pvs --noheadings -o pv_name,vg_name,pv_size 2>/dev/null")
    if out and out.strip():
        info["lvm"]["pvs"] = out.strip()
    out, _, _ = ssh_client.exec_command("vgs --noheadings -o vg_name,vg_size,vg_free 2>/dev/null")
    if out and out.strip():
        info["lvm"]["vgs"] = out.strip()
    out, _, _ = ssh_client.exec_command("lvs --noheadings -o lv_name,vg_name,lv_size 2>/dev/null")
    if out and out.strip():
        info["lvm"]["lvs"] = out.strip()

    out, _, _ = ssh_client.exec_command("swapon --show 2>/dev/null")
    if out and out.strip():
        info["swap"] = out.strip()

    logger.info(f"Disk info: {len(info['disks'])} disks, LVM={'yes' if info['lvm'] else 'no'}")
    return info


def verify_migration(ssh_client, checks=None):
    """Run post-migration verification checks on target ECS."""
    if checks is None:
        checks = ["disk", "service", "network", "user"]

    results = {}
    if "disk" in checks:
        out, _, _ = ssh_client.exec_command("df -h /")
        results["disk"] = {"ok": bool(out), "output": out}
    if "service" in checks:
        out, _, _ = ssh_client.exec_command("systemctl list-units --state=running --type=service | head -20")
        results["services"] = {"ok": bool(out), "output": out}
    if "network" in checks:
        out, _, _ = ssh_client.exec_command("ip addr show")
        results["network"] = {"ok": bool(out), "output": out}
    if "user" in checks:
        out, _, _ = ssh_client.exec_command("cat /etc/passwd | grep -v nologin | grep -v false")
        results["users"] = {"ok": bool(out), "output": out}
    return results


import socket

def scan_ports(host, ports=None, timeout=3):
    """Scan ports on a host."""
    if ports is None:
        ports = [22, 80, 443]

    results = {}
    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex((host, port))
            results[port] = (result == 0)
        except (socket.timeout, Exception):
            results[port] = False
        finally:
            sock.close()
    return results
