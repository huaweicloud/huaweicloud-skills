#!/usr/bin/env python3
"""
post_migration_verify.py — 迁移后数据完整性校验模块

在迁移完成后，通过 SSH（经代理 ECS 跳转）连接目标 ECS，
全面校验数据完整性：
  1. 主机名一致性
  2. OS 版本与内核一致性
  3. 磁盘布局（数量、大小、挂载点、fstab）
  4. 网络配置（IP、路由、网卡）
  5. 关键服务状态（sshd, crond, NetworkManager, chronyd, rsyslog）
  6. 用户账户一致性
  7. Bash 历史记录完整性
  8. 华为云组件（hostguard, ces-uniagent）

支持两种连接模式：
  - 直连模式：目标 ECS 可直接 SSH
  - 代理跳转模式：通过代理 ECS 建立 SSH 隧道（私网场景）
"""

import os
import re
import json
import time
import logging
import paramiko
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PostMigrationVerifier:
    """迁移后数据完整性校验器"""

    # 关键服务列表（迁移后必须运行）
    CRITICAL_SERVICES = [
        "sshd",
        "crond",
        "rsyslog",
    ]

    # 建议运行的服务（警告但不失败）
    RECOMMENDED_SERVICES = [
        "NetworkManager",
        "network",
        "chronyd",
        "ntpd",
    ]

    # 华为云组件
    HUAWEI_CLOUD_AGENTS = [
        "hostguard",
        "ces-uniagent",
    ]

    def __init__(
        self,
        target_ip: str,
        target_port: int = 22,
        target_username: str = "root",
        target_password: str = None,
        target_key_path: str = None,
        proxy_ip: str = None,
        proxy_port: int = 22,
        proxy_username: str = "root",
        proxy_password: str = None,
        proxy_key_path: str = None,
        source_ip: str = None,
        source_username: str = "root",
        source_password: str = None,
        source_key_path: str = None,
        source_gost_port: int = None,
        expected_hostname: str = None,
        expected_os: str = None,
        expected_kernel: str = None,
        expected_disks: List[Dict] = None,
        expected_users: int = None,
        timeout: int = 30,
    ):
        """
        Args:
            target_ip: 目标 ECS IP（内网 IP）
            target_port: 目标 SSH 端口
            target_username/password/key_path: 目标 SSH 凭证
            proxy_ip: 代理 ECS 公网 IP（私网场景跳转用）
            proxy_port: 代理 SSH 端口
            proxy_username/password/key_path: 代理 SSH 凭证
            source_ip: 源端 IP（用于对比，可选）
            source_username/password/key_path: 源端 SSH 凭证
            source_gost_port: 源端 GOST SSH 转发端口（代理上的端口）
            expected_hostname/os/kernel: 预期值（如已知，用于对比）
            expected_disks: 预期磁盘配置 [{"name": "vda", "size_gb": 41, "mount": "/"}]
            expected_users: 预期用户数量
            timeout: SSH 连接超时秒数
        """
        self.target_ip = target_ip
        self.target_port = target_port
        self.target_username = target_username
        self.target_password = target_password
        self.target_key_path = target_key_path

        self.proxy_ip = proxy_ip
        self.proxy_port = proxy_port
        self.proxy_username = proxy_username
        self.proxy_password = proxy_password
        self.proxy_key_path = proxy_key_path

        self.source_ip = source_ip
        self.source_username = source_username
        self.source_password = source_password
        self.source_key_path = source_key_path
        self.source_gost_port = source_gost_port

        self.expected_hostname = expected_hostname
        self.expected_os = expected_os
        self.expected_kernel = expected_kernel
        self.expected_disks = expected_disks or []
        self.expected_users = expected_users
        self.timeout = timeout

        self._target_ssh = None
        self._source_ssh = None

    # ──────────────────────────────────────────────────────
    #  SSH 连接管理
    # ──────────────────────────────────────────────────────

    def _connect_direct(self, ip, port, username, password, key_path):
        """直连 SSH"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs = {
            "hostname": ip,
            "port": port,
            "username": username,
            "timeout": self.timeout,
        }
        if key_path and os.path.exists(key_path):
            connect_kwargs["key_filename"] = key_path
        elif password:
            connect_kwargs["password"] = password
        client.connect(**connect_kwargs)
        return client

    def _connect_via_proxy(self, target_ip, target_port):
        """通过代理 ECS 建立 SSH 隧道连接目标 ECS

        使用 paramiko 的 AutoAddPolicy 和 ProxyJump 模式：
        1. 先连接代理 ECS
        2. 在代理上建立到目标的 TCP 转发通道
        3. 通过该通道 SSH 到目标
        """
        # 连接代理
        proxy_client = paramiko.SSHClient()
        proxy_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        proxy_kwargs = {
            "hostname": self.proxy_ip,
            "port": self.proxy_port,
            "username": self.proxy_username,
            "timeout": self.timeout,
        }
        if self.proxy_key_path and os.path.exists(self.proxy_key_path):
            proxy_kwargs["key_filename"] = self.proxy_key_path
        elif self.proxy_password:
            proxy_kwargs["password"] = self.proxy_password

        logger.info(f"Connecting to proxy {self.proxy_ip}:{self.proxy_port}...")
        proxy_client.connect(**proxy_kwargs)

        # 创建隧道
        transport = proxy_client.get_transport()
        dest_addr = (target_ip, target_port)
        local_addr = ("127.0.0.1", 0)
        channel = transport.open_channel("direct-tcpip", dest_addr, local_addr)

        # 通过隧道连接目标
        target_client = paramiko.SSHClient()
        target_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        target_kwargs = {
            "hostname": target_ip,
            "port": target_port,
            "username": self.target_username,
            "sock": channel,
            "timeout": self.timeout,
        }
        if self.target_key_path and os.path.exists(self.target_key_path):
            target_kwargs["key_filename"] = self.target_key_path
        elif self.target_password:
            target_kwargs["password"] = self.target_password

        logger.info(f"Tunneling to target {target_ip}:{target_port} via proxy...")
        target_client.connect(**target_kwargs)

        # 保存代理引用防止 GC
        target_client._proxy_ref = proxy_client
        return target_client

    def _get_target_ssh(self):
        """获取目标 ECS SSH 连接"""
        if self._target_ssh:
            return self._target_ssh

        if self.proxy_ip:
            self._target_ssh = self._connect_via_proxy(
                self.target_ip, self.target_port
            )
        else:
            self._target_ssh = self._connect_direct(
                self.target_ip,
                self.target_port,
                self.target_username,
                self.target_password,
                self.target_key_path,
            )
        return self._target_ssh

    def _get_source_ssh(self):
        """获取源端 SSH 连接（通过代理 GOST 端口）"""
        if self._source_ssh:
            return self._source_ssh

        if not self.source_ip:
            return None

        if self.proxy_ip and self.source_gost_port:
            # 通过代理的 GOST 端口连接源端
            self._source_ssh = self._connect_via_proxy(
                self.source_ip, 22
            )
        else:
            self._source_ssh = self._connect_direct(
                self.source_ip,
                22,
                self.source_username,
                self.source_password,
                self.source_key_path,
            )
        return self._source_ssh

    def _exec(self, ssh_client, command, timeout=30):
        """执行远程命令，返回 stdout 字符串"""
        try:
            stdin, stdout, stderr = ssh_client.exec_command(command, timeout=timeout)
            out = stdout.read().decode("utf-8", errors="replace").strip()
            err = stderr.read().decode("utf-8", errors="replace").strip()
            return out, err
        except Exception as e:
            logger.warning(f"Command failed: {command[:80]}... | {e}")
            return "", str(e)

    def close(self):
        """关闭所有 SSH 连接"""
        for ssh in [self._target_ssh, self._source_ssh]:
            if ssh:
                try:
                    proxy = getattr(ssh, "_proxy_ref", None)
                    ssh.close()
                    if proxy:
                        proxy.close()
                except Exception:
                    pass
        self._target_ssh = None
        self._source_ssh = None

    # ──────────────────────────────────────────────────────
    #  信息采集
    # ──────────────────────────────────────────────────────

    def _collect_host_info(self, ssh_client, label="host"):
        """采集主机完整信息

        Returns:
            {
                "hostname": str,
                "os": str,
                "kernel": str,
                "disks": [{"name", "size_gb", "mount", "fstype"}],
                "fstab": [{"device", "mount", "fstype", "options"}],
                "network": {"interfaces": [], "routes": []},
                "services": {"running": [], "failed": []},
                "users": [{"name", "uid", "shell"}],
                "user_count": int,
                "bash_history_lines": int,
                "huawei_agents": {"installed": [], "running": []},
            }
        """
        info = {}

        # 主机名
        out, _ = self._exec(ssh_client, "hostname")
        info["hostname"] = out.strip()

        # OS 版本
        out, _ = self._exec(ssh_client, "cat /etc/redhat-release 2>/dev/null || cat /etc/os-release 2>/dev/null | head -5")
        info["os"] = out.strip()

        # 内核版本
        out, _ = self._exec(ssh_client, "uname -r")
        info["kernel"] = out.strip()

        # 磁盘信息
        info["disks"] = self._collect_disks(ssh_client)

        # fstab
        info["fstab"] = self._collect_fstab(ssh_client)

        # 网络配置
        info["network"] = self._collect_network(ssh_client)

        # 服务状态
        info["services"] = self._collect_services(ssh_client)

        # 用户信息
        info["users"] = self._collect_users(ssh_client)
        info["user_count"] = len(info["users"])

        # Bash 历史记录
        out, _ = self._exec(ssh_client, "wc -l /root/.bash_history 2>/dev/null || echo 0")
        try:
            info["bash_history_lines"] = int(out.strip().split()[0])
        except (ValueError, IndexError):
            info["bash_history_lines"] = 0

        # 华为云组件
        info["huawei_agents"] = self._collect_huawei_agents(ssh_client)

        logger.info(f"[{label}] Collected: hostname={info['hostname']}, "
                     f"os={info['os'][:30]}, kernel={info['kernel']}, "
                     f"disks={len(info['disks'])}, users={info['user_count']}")
        return info

    def _collect_disks(self, ssh_client):
        """采集磁盘信息"""
        disks = []
        # 使用 lsblk 获取块设备
        out, _ = self._exec(ssh_client,
            "lsblk -b -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE 2>/dev/null")
        if out:
            for line in out.strip().splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 3 and parts[2] == "disk":
                    name = parts[0]
                    size_bytes = int(parts[1]) if parts[1].isdigit() else 0
                    size_gb = round(size_bytes / (1024**3), 1)
                    mount = parts[3] if len(parts) > 3 else ""
                    fstype = parts[4] if len(parts) > 4 else ""
                    disks.append({
                        "name": name,
                        "size_gb": size_gb,
                        "mount": mount,
                        "fstype": fstype,
                    })
        return disks

    def _collect_fstab(self, ssh_client):
        """采集 /etc/fstab 挂载配置"""
        fstab = []
        out, _ = self._exec(ssh_client, "cat /etc/fstab 2>/dev/null")
        if out:
            for line in out.strip().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    fstab.append({
                        "device": parts[0],
                        "mount": parts[1],
                        "fstype": parts[2],
                        "options": parts[3],
                    })
        return fstab

    def _collect_network(self, ssh_client):
        """采集网络配置"""
        net = {"interfaces": [], "routes": []}

        # 网卡
        out, _ = self._exec(ssh_client,
            "ip -o addr show 2>/dev/null | awk '{print $2, $4, $6}'")
        if out:
            for line in out.strip().splitlines():
                parts = line.split()
                if len(parts) >= 3:
                    net["interfaces"].append({
                        "name": parts[0],
                        "family": parts[1],
                        "address": parts[2],
                    })

        # 路由
        out, _ = self._exec(ssh_client, "ip route show 2>/dev/null")
        if out:
            net["routes"] = [r.strip() for r in out.strip().splitlines() if r.strip()]

        return net

    def _collect_services(self, ssh_client):
        """采集服务状态"""
        svc = {"running": [], "failed": []}

        # 运行中的服务
        out, _ = self._exec(ssh_client,
            "systemctl list-units --type=service --state=running --no-legend 2>/dev/null | awk '{print $1}'")
        if out:
            svc["running"] = [s.replace(".service", "") for s in out.strip().splitlines() if s.strip()]

        # 失败的服务
        out, _ = self._exec(ssh_client,
            "systemctl list-units --type=service --state=failed --no-legend 2>/dev/null | awk '{print $1}'")
        if out:
            svc["failed"] = [s.replace(".service", "") for s in out.strip().splitlines() if s.strip()]

        return svc

    def _collect_users(self, ssh_client):
        """采集用户账户信息"""
        users = []
        out, _ = self._exec(ssh_client,
            "awk -F: '$3 >= 1000 || $1 == \"root\" {print $1, $3, $7}' /etc/passwd 2>/dev/null")
        if out:
            for line in out.strip().splitlines():
                parts = line.split()
                if len(parts) >= 3:
                    users.append({
                        "name": parts[0],
                        "uid": int(parts[1]) if parts[1].isdigit() else 0,
                        "shell": parts[2],
                    })
        return users

    def _collect_huawei_agents(self, ssh_client):
        """采集华为云组件安装和运行状态"""
        agents = {"installed": [], "running": []}

        for agent in self.HUAWEI_CLOUD_AGENTS:
            # 检查安装
            out, _ = self._exec(ssh_client, f"rpm -qa 2>/dev/null | grep -i '{agent}' || dpkg -l 2>/dev/null | grep -i '{agent}' || ls /usr/local/{agent} 2>/dev/null")
            if out and out.strip():
                agents["installed"].append(agent)

            # 检查运行
            out, _ = self._exec(ssh_client, f"systemctl is-active {agent} 2>/dev/null || pgrep -l {agent} 2>/dev/null")
            if out and "active" in out.lower():
                agents["running"].append(agent)

        # 额外检查：进程方式
        out, _ = self._exec(ssh_client, "ps aux 2>/dev/null | grep -E 'hostguard|ces-uniagent|UniAgent' | grep -v grep")
        if out:
            for agent in self.HUAWEI_CLOUD_AGENTS:
                if agent in out and agent not in agents["running"]:
                    agents["running"].append(agent)

        return agents

    # ──────────────────────────────────────────────────────
    #  校验执行
    # ──────────────────────────────────────────────────────

    def verify(self) -> Dict[str, Any]:
        """执行完整迁移后校验

        Returns:
            {
                "passed": bool,
                "checks": {check_name: {"passed": bool, "details": ...}},
                "source_info": dict,
                "target_info": dict,
                "summary": str,
                "errors": [str],
                "warnings": [str],
            }
        """
        result = {
            "passed": True,
            "checks": {},
            "source_info": None,
            "target_info": None,
            "errors": [],
            "warnings": [],
        }

        try:
            # 采集目标 ECS 信息
            target_ssh = self._get_target_ssh()
            logger.info("Collecting target ECS info...")
            target_info = self._collect_host_info(target_ssh, "target")
            result["target_info"] = target_info

            # 采集源端信息（可选，用于对比）
            source_info = None
            try:
                source_ssh = self._get_source_ssh()
                if source_ssh:
                    logger.info("Collecting source host info...")
                    source_info = self._collect_host_info(source_ssh, "source")
                    result["source_info"] = source_info
            except Exception as e:
                logger.warning(f"Could not collect source info: {e}")
                result["warnings"].append(f"Source info collection failed: {e}")

            # 执行各项校验
            checks = [
                ("hostname", self._check_hostname),
                ("os_kernel", self._check_os_kernel),
                ("disks", self._check_disks),
                ("fstab", self._check_fstab),
                ("network", self._check_network),
                ("services", self._check_services),
                ("users", self._check_users),
                ("bash_history", self._check_bash_history),
                ("huawei_agents", self._check_huawei_agents),
            ]

            for check_name, check_fn in checks:
                try:
                    check_result = check_fn(source_info, target_info)
                    result["checks"][check_name] = check_result
                    if not check_result["passed"]:
                        result["passed"] = False
                        if check_result.get("errors"):
                            result["errors"].extend(check_result["errors"])
                    if check_result.get("warnings"):
                        result["warnings"].extend(check_result["warnings"])
                except Exception as e:
                    logger.error(f"Check '{check_name}' failed with exception: {e}")
                    result["checks"][check_name] = {
                        "passed": False,
                        "errors": [f"Check exception: {e}"],
                    }
                    result["passed"] = False
                    result["errors"].append(f"Check '{check_name}' exception: {e}")

            # 生成摘要
            result["summary"] = self._generate_summary(result)

        finally:
            self.close()

        return result

    # ──────────────────────────────────────────────────────
    #  各项校验方法
    # ──────────────────────────────────────────────────────

    def _check_hostname(self, source_info, target_info) -> Dict:
        """校验主机名一致性"""
        target_hostname = target_info.get("hostname", "")
        errors = []
        warnings = []

        if source_info:
            source_hostname = source_info.get("hostname", "")
            if source_hostname and target_hostname:
                if source_hostname == target_hostname:
                    return {"passed": True, "source": source_hostname, "target": target_hostname}
                else:
                    errors.append(f"Hostname mismatch: source={source_hostname}, target={target_hostname}")
                    return {"passed": False, "source": source_hostname, "target": target_hostname, "errors": errors}

        # 无源端信息，使用预期值
        if self.expected_hostname:
            if target_hostname == self.expected_hostname:
                return {"passed": True, "target": target_hostname, "expected": self.expected_hostname}
            else:
                errors.append(f"Hostname mismatch: expected={self.expected_hostname}, target={target_hostname}")
                return {"passed": False, "target": target_hostname, "expected": self.expected_hostname, "errors": errors}

        # 无法对比，仅记录
        warnings.append("No source or expected hostname for comparison")
        return {"passed": True, "target": target_hostname, "warnings": warnings}

    def _check_os_kernel(self, source_info, target_info) -> Dict:
        """校验 OS 版本和内核一致性"""
        target_os = target_info.get("os", "")
        target_kernel = target_info.get("kernel", "")
        errors = []
        warnings = []

        # 提取 OS 简称 (如 "CentOS 7.9.2009")
        target_os_short = self._extract_os_short(target_os)

        if source_info:
            source_os = source_info.get("os", "")
            source_kernel = source_info.get("kernel", "")
            source_os_short = self._extract_os_short(source_os)

            os_match = source_os_short == target_os_short if source_os_short and target_os_short else True
            kernel_match = source_kernel == target_kernel if source_kernel and target_kernel else True

            if os_match and kernel_match:
                return {"passed": True, "source_os": source_os_short, "target_os": target_os_short,
                        "source_kernel": source_kernel, "target_kernel": target_kernel}
            else:
                if not os_match:
                    errors.append(f"OS mismatch: source={source_os_short}, target={target_os_short}")
                if not kernel_match:
                    errors.append(f"Kernel mismatch: source={source_kernel}, target={target_kernel}")
                return {"passed": False, "errors": errors,
                        "source_os": source_os_short, "target_os": target_os_short,
                        "source_kernel": source_kernel, "target_kernel": target_kernel}

        # 使用预期值
        if self.expected_os and target_os_short:
            if self.expected_os not in target_os and target_os_short != self.expected_os:
                warnings.append(f"OS may differ: expected={self.expected_os}, target={target_os_short}")

        if self.expected_kernel and target_kernel:
            if target_kernel != self.expected_kernel:
                warnings.append(f"Kernel may differ: expected={self.expected_kernel}, target={target_kernel}")

        return {"passed": True, "target_os": target_os_short, "target_kernel": target_kernel, "warnings": warnings}

    def _extract_os_short(self, os_str: str) -> str:
        """从 OS 字符串提取简称"""
        if not os_str:
            return ""
        # CentOS 7.9.2009
        m = re.search(r'(CentOS\s+\d+\.\d+\.\d+)', os_str)
        if m:
            return m.group(1)
        # Ubuntu 22.04
        m = re.search(r'(Ubuntu\s+\d+\.\d+)', os_str)
        if m:
            return m.group(1)
        # 其他：取第一行
        return os_str.split("\n")[0][:40]

    def _check_disks(self, source_info, target_info) -> Dict:
        """校验磁盘布局一致性"""
        target_disks = target_info.get("disks", [])
        errors = []
        warnings = []
        details = {"target_disks": target_disks}

        if source_info:
            source_disks = source_info.get("disks", [])
            details["source_disks"] = source_disks

            if len(source_disks) != len(target_disks):
                errors.append(f"Disk count mismatch: source={len(source_disks)}, target={len(target_disks)}")
            else:
                for i, (sd, td) in enumerate(zip(source_disks, target_disks)):
                    if abs(sd["size_gb"] - td["size_gb"]) > 1:
                        warnings.append(f"Disk {i+1} size differs: source={sd['size_gb']}GB, target={td['size_gb']}GB")

            return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings, **details}

        # 使用预期磁盘配置
        if self.expected_disks:
            details["expected_disks"] = self.expected_disks
            if len(self.expected_disks) != len(target_disks):
                errors.append(f"Disk count mismatch: expected={len(self.expected_disks)}, target={len(target_disks)})")
            else:
                for i, (ed, td) in enumerate(zip(self.expected_disks, target_disks)):
                    expected_size = ed.get("size_gb", 0)
                    if expected_size and abs(expected_size - td["size_gb"]) > 1:
                        warnings.append(f"Disk {i+1} size differs: expected={expected_size}GB, target={td['size_gb']}GB")

            return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings, **details}

        # 无对比基准
        warnings.append("No source or expected disks for comparison")
        return {"passed": True, "warnings": warnings, **details}

    def _check_fstab(self, source_info, target_info) -> Dict:
        """校验 fstab 挂载配置一致性"""
        target_fstab = target_info.get("fstab", [])
        errors = []
        warnings = []
        details = {"target_fstab": target_fstab}

        if source_info:
            source_fstab = source_info.get("fstab", [])
            details["source_fstab"] = source_fstab

            # 比较挂载点集合
            source_mounts = {f["mount"] for f in source_fstab}
            target_mounts = {f["mount"] for f in target_fstab}

            missing = source_mounts - target_mounts
            extra = target_mounts - source_mounts

            if missing:
                errors.append(f"Missing mount points on target: {sorted(missing)}")
            if extra:
                warnings.append(f"Extra mount points on target: {sorted(extra)}")

            # 比较文件系统类型
            for sf in source_fstab:
                for tf in target_fstab:
                    if sf["mount"] == tf["mount"] and sf["fstype"] != tf["fstype"]:
                        warnings.append(f"Mount {sf['mount']} fstype differs: source={sf['fstype']}, target={tf['fstype']}")

            return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings, **details}

        # 无源端信息，仅检查基本完整性
        root_found = any(f["mount"] == "/" for f in target_fstab)
        if not root_found:
            errors.append("Root mount point (/) not found in target fstab")

        return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings, **details}

    def _check_network(self, source_info, target_info) -> Dict:
        """校验网络配置"""
        target_net = target_info.get("network", {})
        errors = []
        warnings = []
        details = {"target_interfaces": target_net.get("interfaces", []),
                    "target_routes": target_net.get("routes", [])}

        # 基本检查：至少有一个非 loopback 接口
        interfaces = target_net.get("interfaces", [])
        non_loopback = [i for i in interfaces if i.get("name") != "lo" and not i.get("name", "").startswith("lo")]
        if not non_loopback:
            errors.append("No non-loopback network interface found on target")

        if source_info:
            source_net = source_info.get("network", {})
            details["source_interfaces"] = source_net.get("interfaces", [])

            # 接口数量对比（源端迁移后 IP 可能变化，但接口数应一致）
            source_ifs = [i for i in source_net.get("interfaces", []) if i.get("name") != "lo"]
            target_ifs = non_loopback
            if len(source_ifs) != len(target_ifs):
                warnings.append(f"Network interface count differs: source={len(source_ifs)}, target={len(target_ifs)}")

        return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings, **details}

    def _check_services(self, source_info, target_info) -> Dict:
        """校验服务状态"""
        target_svc = target_info.get("services", {})
        errors = []
        warnings = []
        details = {"target_running_count": len(target_svc.get("running", [])),
                    "target_failed": target_svc.get("failed", [])}

        # 检查是否有失败的服务
        failed = target_svc.get("failed", [])
        if failed:
            errors.append(f"Failed services on target: {failed}")

        if source_info:
            source_svc = source_info.get("services", {})
            source_running = set(source_svc.get("running", []))
            target_running = set(target_svc.get("running", []))

            # 关键服务必须在目标端运行
            critical_missing = self.CRITICAL_SERVICES - target_running
            if critical_missing:
                errors.append(f"Critical services not running on target: {sorted(critical_missing)}")

            # 对比关键服务
            for svc in self.CRITICAL_SERVICES:
                if svc in source_running and svc not in target_running:
                    errors.append(f"Service '{svc}' running on source but not on target")

            details["source_running_count"] = len(source_running)
        else:
            # 仅检查关键服务
            target_running = set(target_svc.get("running", []))
            critical_missing = self.CRITICAL_SERVICES - target_running
            if critical_missing:
                warnings.append(f"Critical services not running (no source for comparison): {sorted(critical_missing)}")

        return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings, **details}

    def _check_users(self, source_info, target_info) -> Dict:
        """校验用户账户一致性"""
        target_users = target_info.get("users", [])
        target_count = target_info.get("user_count", 0)
        errors = []
        warnings = []
        details = {"target_user_count": target_count, "target_users": [u["name"] for u in target_users]}

        if source_info:
            source_users = source_info.get("users", [])
            source_count = source_info.get("user_count", 0)
            details["source_user_count"] = source_count

            source_names = {u["name"] for u in source_users}
            target_names = {u["name"] for u in target_users}

            missing = source_names - target_names
            extra = target_names - source_names

            if missing:
                errors.append(f"Missing users on target: {sorted(missing)}")
            if extra:
                warnings.append(f"Extra users on target: {sorted(extra)}")

            if source_count != target_count:
                warnings.append(f"User count differs: source={source_count}, target={target_count}")

            # 校验用户 UID 和 shell
            source_user_map = {u["name"]: u for u in source_users}
            for tu in target_users:
                su = source_user_map.get(tu["name"])
                if su:
                    if su["uid"] != tu["uid"]:
                        warnings.append(f"User '{tu['name']}' UID differs: source={su['uid']}, target={tu['uid']}")
                    if su["shell"] != tu["shell"]:
                        warnings.append(f"User '{tu['name']}' shell differs: source={su['shell']}, target={tu['shell']}")

            return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings, **details}

        # 无源端信息
        if target_count == 0:
            errors.append("No users found on target")
        elif target_count < 2:
            warnings.append(f"Very few users ({target_count}) found on target")

        return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings, **details}

    def _check_bash_history(self, source_info, target_info) -> Dict:
        """校验 bash 历史记录"""
        target_lines = target_info.get("bash_history_lines", 0)
        errors = []
        warnings = []
        details = {"target_bash_history_lines": target_lines}

        if source_info:
            source_lines = source_info.get("bash_history_lines", 0)
            details["source_bash_history_lines"] = source_lines

            if source_lines > 0:
                if target_lines == 0:
                    errors.append(f"Bash history missing on target (source has {source_lines} lines)")
                elif target_lines < source_lines * 0.9:
                    warnings.append(f"Bash history significantly reduced: source={source_lines}, target={target_lines}")
                elif target_lines != source_lines:
                    # 小幅差异可接受
                    pass
            return {"passed": len(errors) == 0, "errors": errors, "warnings": warnings, **details}

        # 无源端信息
        if target_lines == 0:
            warnings.append("No bash history on target (may be normal for fresh migration)")

        return {"passed": True, "errors": errors, "warnings": warnings, **details}

    def _check_huawei_agents(self, source_info, target_info) -> Dict:
        """校验华为云组件安装和运行状态"""
        target_agents = target_info.get("huawei_agents", {})
        installed = target_agents.get("installed", [])
        running = target_agents.get("running", [])
        errors = []
        warnings = []
        details = {"installed": installed, "running": running}

        # 至少检查 hostguard 是否安装
        if "hostguard" not in installed and "hostguard" not in running:
            warnings.append("HostGuard (hostguard) not detected on target - "
                          "may need manual installation or agent auto-install is still in progress")

        # 检查 CES UniAgent
        if "uniagent" not in installed and "uniagent" not in running:
            warnings.append("CES UniAgent not detected on target - "
                          "monitoring may not be available")

        # 源端对比（源端通常没有华为云组件）
        if source_info:
            source_agents = source_info.get("huawei_agents", {})
            details["source_installed"] = source_agents.get("installed", [])

        return {"passed": True, "errors": errors, "warnings": warnings, **details}

    # ──────────────────────────────────────────────────────
    #  摘要与报告
    # ──────────────────────────────────────────────────────

    def _generate_summary(self, result: Dict) -> str:
        """生成校验摘要文本"""
        lines = []
        lines.append("=" * 60)
        lines.append("  迁移后数据完整性校验报告")
        lines.append("=" * 60)
        lines.append("")

        overall = "✅ 通过" if result["passed"] else "❌ 失败"
        lines.append(f"总体结果: {overall}")
        lines.append("")

        # 目标 ECS 信息
        ti = result.get("target_info", {})
        if ti:
            lines.append(f"目标 ECS:")
            lines.append(f"  主机名: {ti.get('hostname', 'N/A')}")
            lines.append(f"  操作系统: {self._extract_os_short(ti.get('os', ''))}")
            lines.append(f"  内核: {ti.get('kernel', 'N/A')}")
            lines.append(f"  磁盘数: {len(ti.get('disks', []))}")
            lines.append(f"  用户数: {ti.get('user_count', 0)}")
            lines.append("")

        # 源端信息
        si = result.get("source_info", {})
        if si:
            lines.append(f"源端主机:")
            lines.append(f"  主机名: {si.get('hostname', 'N/A')}")
            lines.append(f"  操作系统: {self._extract_os_short(si.get('os', ''))}")
            lines.append(f"  内核: {si.get('kernel', 'N/A')}")
            lines.append("")

        # 各项校验结果
        lines.append("校验项目:")
        for name, check in result.get("checks", {}).items():
            status = "✅" if check.get("passed") else "❌"
            lines.append(f"  {status} {name}")
            if check.get("errors"):
                for e in check["errors"]:
                    lines.append(f"      错误: {e}")
            if check.get("warnings"):
                for w in check["warnings"]:
                    lines.append(f"      警告: {w}")
        lines.append("")

        # 错误和警告汇总
        if result["errors"]:
            lines.append(f"错误汇总 ({len(result['errors'])}):")
            for e in result["errors"]:
                lines.append(f"  - {e}")
            lines.append("")

        if result["warnings"]:
            lines.append(f"警告汇总 ({len(result['warnings'])}):")
            for w in result["warnings"]:
                lines.append(f"  - {w}")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    def save_report(self, result: Dict, output_file: str = None) -> str:
        """保存校验报告到文件

        Args:
            result: verify() 返回的结果
            output_file: 输出文件路径，默认为 /tmp/post_migration_verify_<timestamp>.json

        Returns:
            报告文件路径
        """
        if not output_file:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"/tmp/post_migration_verify_{ts}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "verifier_version": "1.0",
            "target_ecs": {
                "ip": self.target_ip,
                "ssh_port": self.target_port,
            },
            "source_host": {
                "ip": self.source_ip,
                "ssh_port": self.source_port,
            },
            "proxy": {
                "ip": self.proxy_ip,
                "port": self.proxy_port,
            },
            "result": result,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 同时保存文本摘要
        txt_file = output_file.replace(".json", ".txt")
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(result.get("summary", ""))

        logger.info(f"Report saved: {output_file} (json), {txt_file} (txt)")
        return output_file


# ──────────────────────────────────────────────────────────
#  CLI 入口
# ──────────────────────────────────────────────────────────

def main():
    """命令行入口

    用法:
        python post_migration_verify.py \\
            --target-ip 172.16.0.22 \\
            --target-port 22 \\
            --target-user root \\
            --target-password 'xxx' \\
            --proxy-ip 114.116.211.212 \\
            --proxy-port 22 \\
            --proxy-user root \\
            --proxy-password 'xxx' \\
            --source-ip 192.168.0.148 \\
            --source-port 22 \\
            --source-user root \\
            --source-password 'xxx' \\
            --expected-hostname source-hostname \\
            --expected-os "CentOS 7.9" \\
            --output /tmp/verify_report.json
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="迁移后数据完整性校验工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--target-ip", required=True, help="目标 ECS IP")
    parser.add_argument("--target-port", type=int, default=22, help="目标 ECS SSH 端口")
    parser.add_argument("--target-user", default="root", help="目标 ECS SSH 用户")
    parser.add_argument("--target-password", help="目标 ECS SSH 密码")
    parser.add_argument("--target-key", help="目标 ECS SSH 私钥路径")

    parser.add_argument("--proxy-ip", help="代理 ECS IP (私网场景)")
    parser.add_argument("--proxy-port", type=int, default=22, help="代理 ECS SSH 端口")
    parser.add_argument("--proxy-user", default="root", help="代理 ECS SSH 用户")
    parser.add_argument("--proxy-password", help="代理 ECS SSH 密码")
    parser.add_argument("--proxy-key", help="代理 ECS SSH 私钥路径")

    parser.add_argument("--source-ip", help="源端主机 IP (可选，用于对比)")
    parser.add_argument("--source-port", type=int, default=22, help="源端 SSH 端口")
    parser.add_argument("--source-user", default="root", help="源端 SSH 用户")
    parser.add_argument("--source-password", help="源端 SSH 密码")
    parser.add_argument("--source-key", help="源端 SSH 私钥路径")

    parser.add_argument("--expected-hostname", help="预期主机名")
    parser.add_argument("--expected-os", help="预期操作系统")
    parser.add_argument("--expected-kernel", help="预期内核版本")
    parser.add_argument("--output", help="报告输出路径")

    args = parser.parse_args()

    verifier = PostMigrationVerifier(
        target_ip=args.target_ip,
        target_port=args.target_port,
        target_user=args.target_user,
        target_password=args.target_password,
        target_key_file=args.target_key,
        proxy_ip=args.proxy_ip,
        proxy_port=args.proxy_port,
        proxy_user=args.proxy_user,
        proxy_password=args.proxy_password,
        proxy_key_file=args.proxy_key,
        source_ip=args.source_ip,
        source_port=args.source_port,
        source_user=args.source_user,
        source_password=args.source_password,
        source_key_file=args.source_key,
        expected_hostname=args.expected_hostname,
        expected_os=args.expected_os,
        expected_kernel=args.expected_kernel,
    )

    result = verifier.verify()
    print(result["summary"])

    report_file = verifier.save_report(result, args.output)
    print(f"\n报告已保存: {report_file}")

    # 退出码: 0=通过, 1=失败
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
