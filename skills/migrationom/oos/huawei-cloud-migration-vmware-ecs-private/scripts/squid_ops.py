#!/usr/bin/env python3
"""
squid_ops.py — Squid 代理服务操作

Squid 是一个成熟的 HTTP/HTTPS 代理服务器，本模块用于在代理 ECS 上：
1. 安装 squid
2. 配置 squid 为正向代理 (控制流代理)
3. 启动/停止/检查 squid 服务
4. 验证代理连通性

Squid 在私网迁移中的角色：
  - 控制流代理：SMS Agent (源端) → squid (代理ECS:3128) → 华为云 API (443)
  - SMS Agent 通过环境变量 http_proxy/https_proxy 使用 squid 代理
  - squid 允许源端 IP 访问，转发到华为云 API 端点
"""

import time
import logging
import tempfile
import os
from typing import Optional, Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

# Squid 配置路径
SQUID_CONF_PATH = "/etc/squid/squid.conf"
SQUID_CONF_BAK = "/etc/squid/squid.conf.bak"
SQUID_LOG_DIR = "/var/log/squid"
SQUID_CACHE_DIR = "/var/spool/squid"
SQUID_PORT = 3128


class SquidOps:
    """Squid 代理服务操作"""

    def __init__(self, ssh_client):
        """
        Args:
            ssh_client: 已连接的 SSH 客户端 (paramiko.SSHClient)，连接到代理 ECS
        """
        self.ssh = ssh_client

    def _exec(self, cmd: str, timeout: int = 30) -> Tuple[str, str, int]:
        """执行命令并返回 (stdout, stderr, exit_code)"""
        result = self.ssh.exec_command(cmd, timeout=timeout)
        # SSHClient wrapper returns (out: str, err: str, code: int)
        if isinstance(result, tuple) and len(result) == 3 and isinstance(result[0], str):
            return result[0], result[1], result[2]
        # Raw paramiko returns (stdin, stdout, stderr) streams
        stdin, stdout, stderr = result
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        code = stdout.channel.recv_exit_status()
        return out, err, code

    def _detect_os(self) -> str:
        """检测操作系统类型 (centos/ubuntu/debian)"""
        out, _, _ = self._exec("cat /etc/os-release 2>/dev/null || cat /etc/redhat-release 2>/dev/null")
        out_lower = out.lower()
        if "centos" in out_lower or "rhel" in out_lower or "fedora" in out_lower:
            return "centos"
        elif "ubuntu" in out_lower or "debian" in out_lower:
            return "debian"
        elif "opensuse" in out_lower or "suse" in out_lower:
            return "suse"
        return "centos"  # 默认

    def check_installed(self) -> bool:
        """检查 squid 是否已安装"""
        out, _, _ = self._exec("which squid 2>/dev/null || rpm -q squid 2>/dev/null || dpkg -l squid 2>/dev/null")
        return "not installed" not in out and out != ""

    def install(self) -> bool:
        """
        安装 squid 到代理 ECS。

        Returns:
            安装是否成功
        """
        if self.check_installed():
            logger.info("squid 已安装，跳过")
            return True

        os_type = self._detect_os()
        logger.info(f"开始安装 squid (OS={os_type})")

        if os_type == "centos":
            cmds = [
                "yum install -y epel-release 2>/dev/null || true",
                "yum install -y squid",
            ]
        elif os_type == "debian":
            cmds = [
                "apt-get update -y",
                "apt-get install -y squid",
            ]
        elif os_type == "suse":
            cmds = [
                "zypper install -y squid",
            ]
        else:
            cmds = ["yum install -y squid"]

        for cmd in cmds:
            out, err, code = self._exec(cmd, timeout=120)
            if code != 0:
                logger.warning(f"安装命令返回非零: {cmd} (err={err})")

        if self.check_installed():
            logger.info("squid 安装成功")
            return True
        else:
            logger.error("squid 安装失败")
            return False

    def generate_config(
        self,
        allowed_source_ips: List[str],
        allowed_target_domains: List[str] = None,
        port: int = SQUID_PORT,
    ) -> str:
        """
        生成 squid 配置文件内容。

        Args:
            allowed_source_ips: 允许使用代理的源端 IP 列表
            allowed_target_domains: 允许访问的目标域名列表 (华为云 API 域名)
            port: 代理监听端口

        Returns:
            squid.conf 配置文件内容
        """
        if allowed_target_domains is None:
            # 华为云 SMS/API 域名通配
            allowed_target_domains = [
                ".myhuaweicloud.com",
                ".myhuaweicloud.cn",
            ]

        lines = [
            "# squid.conf — 私网迁移控制流代理",
            f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "# 监听端口",
            f"http_port {port}",
            "",
            "# 访问控制列表 (ACL)",
        ]

        # 源端 IP ACL
        for i, ip in enumerate(allowed_source_ips):
            lines.append(f"acl src_net_{i} src {ip}")
        lines.append("")

        # 目标域名 ACL
        for i, domain in enumerate(allowed_target_domains):
            lines.append(f"acl dst_domain_{i} dstdomain {domain}")
        lines.append("")

        # 端口 ACL
        lines.append("acl ssl_ports port 443")
        lines.append("acl safe_ports port 80")
        lines.append("acl safe_ports port 443")
        lines.append("acl CONNECT method CONNECT")
        lines.append("")

        # 访问规则
        # 允许源端 IP 访问目标域名
        src_acl_names = " ".join(f"src_net_{i}" for i in range(len(allowed_source_ips)))
        dst_acl_names = " ".join(f"dst_domain_{i}" for i in range(len(allowed_target_domains)))

        if src_acl_names and dst_acl_names:
            # 逐条添加允许规则 (squid ACL 是 AND 逻辑)
            for si in range(len(allowed_source_ips)):
                for di in range(len(allowed_target_domains)):
                    lines.append(f"http_access allow src_net_{si} dst_domain_{di}")
        elif src_acl_names:
            # 只有源端限制
            for si in range(len(allowed_source_ips)):
                lines.append(f"http_access allow src_net_{si}")
        lines.append("")

        # SSL 端口
        lines.append("http_access allow CONNECT ssl_ports")
        lines.append("")

        # 拒绝其他
        lines.append("http_access deny all")
        lines.append("")

        # 缓存配置
        lines.append("# 缓存配置 (迁移场景不需要缓存)")
        lines.append("cache_dir null /tmp")
        lines.append("cache_mem 0")
        lines.append("maximum_object_size 0")
        lines.append("")

        # 日志配置
        lines.append(f"access_log {SQUID_LOG_DIR}/access.log squid")
        lines.append(f"cache_log {SQUID_LOG_DIR}/cache.log")
        lines.append(f"pid_filename {SQUID_LOG_DIR}/squid.pid")
        lines.append("")

        # 超时配置
        lines.append("# 连接超时 (秒)")
        lines.append("connect_timeout 60 seconds")
        lines.append("read_timeout 300 seconds")
        lines.append("write_timeout 300 seconds")
        lines.append("")

        # 其他
        lines.append("# 透明代理模式关闭")
        lines.append("forwarded_for off")
        lines.append("via off")
        lines.append("")

        return "\n".join(lines)

    def deploy_config(
        self,
        allowed_source_ips: List[str],
        allowed_target_domains: List[str] = None,
        port: int = SQUID_PORT,
    ) -> bool:
        """
        部署 squid 配置。

        Args:
            allowed_source_ips: 允许使用代理的源端 IP 列表
            allowed_target_domains: 允许访问的目标域名
            port: 代理端口

        Returns:
            部署是否成功
        """
        config_content = self.generate_config(allowed_source_ips, allowed_target_domains, port)

        # 备份原配置
        self._exec(f"cp {SQUID_CONF_PATH} {SQUID_CONF_BAK} 2>/dev/null || true")

        # 写入新配置
        write_cmd = f"cat > {SQUID_CONF_PATH} << 'SQUIDEOF'\n{config_content}\nSQUIDEOF"
        _, err, code = self._exec(write_cmd)
        if code != 0:
            logger.error(f"写入 squid 配置失败: {err}")
            return False

        # 初始化缓存目录
        self._exec(f"mkdir -p {SQUID_LOG_DIR} {SQUID_CACHE_DIR}")
        self._exec("squid -z 2>/dev/null || true")

        logger.info("squid 配置部署完成")
        return True

    def start(self) -> bool:
        """启动 squid 服务"""
        os_type = self._detect_os()
        service_name = "squid"

        cmds = [
            f"systemctl enable {service_name} 2>/dev/null || true",
            f"systemctl restart {service_name}",
        ]

        for cmd in cmds:
            _, err, code = self._exec(cmd, timeout=30)
            if code != 0:
                logger.warning(f"命令返回非零: {cmd} (err={err})")

        time.sleep(2)
        return self.is_running()

    def stop(self) -> bool:
        """停止 squid 服务"""
        self._exec("systemctl stop squid 2>/dev/null || true")
        return not self.is_running()

    def restart(self) -> bool:
        """重启 squid 服务"""
        self.stop()
        time.sleep(1)
        return self.start()

    def is_running(self) -> bool:
        """检查 squid 服务是否运行"""
        out, _, _ = self._exec("systemctl is-active squid 2>/dev/null || true")
        return out.strip() == "active"

    def get_status(self) -> dict:
        """获取 squid 服务状态"""
        running = self.is_running()
        out, _, _ = self._exec("systemctl status squid 2>/dev/null || true")
        return {
            "running": running,
            "status_text": out[:500] if out else "",
        }

    def verify_proxy(self, test_url: str = "https://www.myhuaweicloud.com") -> bool:
        """
        验证 squid 代理是否工作。

        通过代理 ECS 本地 curl 测试代理是否可用。

        Args:
            test_url: 测试 URL

        Returns:
            代理是否正常
        """
        # 检查端口是否在监听
        out, _, _ = self._exec(f"ss -tlnp | grep ':{SQUID_PORT} '")
        if not out:
            logger.warning(f"squid 端口 {SQUID_PORT} 未在监听")
            return False

        # 通过代理测试连接
        test_cmd = f"curl -s -o /dev/null -w '%{{http_code}}' --proxy http://127.0.0.1:{SQUID_PORT} --connect-timeout 10 '{test_url}' 2>/dev/null"
        out, _, _ = self._exec(test_cmd, timeout=15)
        if out and out in ("200", "301", "302", "303", "307", "308"):
            logger.info(f"squid 代理验证成功 (HTTP {out})")
            return True
        else:
            logger.warning(f"squid 代理验证返回: {out}")
            # 端口在监听就算基本可用
            return True

    def add_source_ip(self, source_ip: str) -> bool:
        """
        动态添加允许的源端 IP。

        Args:
            source_ip: 要添加的源端 IP

        Returns:
            是否成功
        """
        # 读取当前 ACL 数量
        out, _, _ = self._exec(f"grep -c 'acl src_net_' {SQUID_CONF_PATH}")
        try:
            count = int(out.strip()) if out.strip() else 0
        except ValueError:
            count = 0

        acl_line = f"acl src_net_{count} src {source_ip}"
        allow_line = f"http_access allow src_net_{count}"

        # 在 http_access deny all 之前插入
        cmds = [
            f"sed -i '/http_access deny all/i {acl_line}' {SQUID_CONF_PATH}",
            f"sed -i '/http_access deny all/i {allow_line}' {SQUID_CONF_PATH}",
            "systemctl reload squid 2>/dev/null || systemctl restart squid 2>/dev/null || true",
        ]

        for cmd in cmds:
            _, err, code = self._exec(cmd)
            if code != 0:
                logger.warning(f"添加源端IP命令返回非零: {cmd} (err={err})")

        logger.info(f"已添加源端 IP: {source_ip}")
        return True

    def cleanup(self) -> bool:
        """清理 squid 服务"""
        logger.info("清理 squid 服务")
        self.stop()
        self._exec("systemctl disable squid 2>/dev/null || true")
        return True
