#!/usr/bin/env python3
"""
sms_agent_push.py — SMS Agent 远程推送

通过 GOST 管理通道将 SMS Agent 安装包推送到源端并安装。
源端无需公网 IP，所有操作通过代理 ECS 的 GOST 端口转发完成。

流程:
  1. 通过 GOST SSH 通道连接源端
  2. 检查源端是否已安装 SMS Agent
  3. 下载/复制 Agent 安装包到源端
  4. 执行安装命令
  5. 等待 Agent 注册到 SMS 服务
  6. 验证 Agent 状态
"""

import os
import time
import logging
import tempfile
import threading
from typing import Optional, Dict, Any

try:
    import paramiko
except ImportError:
    paramiko = None

from ssh_utils import SSHClient

logger = logging.getLogger(__name__)


class SMSAgentPush:
    """SMS Agent 远程推送"""

    # 类级锁: 保护代理 ECS 上 rsync 编译 (所有实例共享)
    # 解决 100 台并发时多个线程同时编译 rsync 导致的竞态条件
    _rsync_compile_lock = threading.Lock()

    # SMS Agent 下载地址 (通过 squid 代理访问)
    AGENT_DOWNLOAD_URL = (
        "https://sms-agent.myhuaweicloud.com:8443/sms-agent-linux.tar.gz"
    )

    # Agent 安装路径 (使用 /opt 而非 /tmp, 避免 tmpfs 空间不足)
    AGENT_INSTALL_PATH = "/opt/SMS-Agent"
    AGENT_SCRIPT = "startup.sh"
    # Agent 包临时存放路径 (非 tmpfs)
    AGENT_TMP_PATH = "/opt"

    def __init__(
        self,
        ssh_utils: SSHClient,
        proxy_ip: str,
        gost_ssh_port: int = 22,
        squid_proxy: str = None,
        proxy_username: str = "root",
        proxy_password: str = None,
        proxy_private_ip: str = None,
    ):
        """
        Args:
            ssh_utils: SSHClient 实例
            proxy_ip: 代理 ECS IP
            gost_ssh_port: GOST SSH 转发端口 (源端 SSH 通过 GOST 暴露的端口)
            squid_proxy: squid 代理地址 (ip:port)，用于源端下载 Agent
            proxy_username: 代理 ECS SSH 用户名 (用于 rsync 编译)
            proxy_password: 代理 ECS SSH 密码 (用于 rsync 编译)
            proxy_private_ip: 代理 ECS 私网 IP (用于 auth.cfg proxy_addr 配置)
        """
        self.ssh = ssh_utils
        self.proxy_ip = proxy_ip
        self.gost_ssh_port = gost_ssh_port
        self.squid_proxy = squid_proxy
        self.proxy_username = proxy_username
        self.proxy_password = proxy_password
        self.proxy_private_ip = proxy_private_ip or ""

    # ──────────────────────────────────────────────────────────────
    #  Agent 状态检查
    # ──────────────────────────────────────────────────────────────

    def check_agent_installed(self, ssh_conn) -> bool:
        """检查源端是否已安装 SMS Agent

        统一检查以下路径 (安装目录与启动命令路径一致):
          - /opt/SMS-Agent/  (解压目录, install_agent 使用)
          - /usr/local/sms-agent/  (startup.sh 实际安装目录)
          - /tmp/SMS-Agent/  (兼容旧安装)

        Args:
            ssh_conn: SSH 连接对象

        Returns:
            是否已安装
        """
        # 检查 Agent 进程 (linuxmain 是核心进程)
        cmd = "pgrep -x linuxmain 2>/dev/null || ps aux | grep -i 'sms.*agent' | grep -v grep"
        result = self.ssh.execute(ssh_conn, cmd)
        if result and (result.get("stdout", "") or "").strip():
            logger.info("SMS Agent already running on source")
            return True

        # 检查安装目录 (统一检查解压目录 + 实际安装目录, 路径一致)
        cmd = (
            f"ls {self.AGENT_INSTALL_PATH}/startup.sh 2>/dev/null "
            f"|| ls /usr/local/sms-agent/agent 2>/dev/null "
            f"|| ls /usr/local/sms-agent/sms_agent 2>/dev/null "
            f"|| ls /tmp/SMS-Agent/startup.sh 2>/dev/null"
        )
        result = self.ssh.execute(ssh_conn, cmd)
        if result and (result.get("stdout", "") or "").strip():
            logger.info("SMS Agent installed but not running on source")
            return True

        return False

    def get_agent_version(self, ssh_conn) -> Optional[str]:
        """获取已安装 Agent 版本

        统一检查路径 (与 check_agent_installed 一致):
          /usr/local/sms-agent/ (实际安装目录) → /opt/SMS-Agent/ (解压目录) → /SMSAgent/ (兼容)
        """
        cmd = (
            "cat /usr/local/sms-agent/version 2>/dev/null "
            f"|| cat {self.AGENT_INSTALL_PATH}/version 2>/dev/null "
            "|| cat /SMSAgent/version 2>/dev/null"
        )
        result = self.ssh.execute(ssh_conn, cmd)
        if result:
            version = (result.get("stdout", "") or "").strip()
            if version:
                return version
        return None

    # ──────────────────────────────────────────────────────────────
    #  Agent 安装包推送
    # ──────────────────────────────────────────────────────────────

    def download_agent_on_source(self, ssh_conn, agent_url: str = None) -> bool:
        """在源端通过 squid 代理下载 SMS Agent

        Args:
            ssh_conn: SSH 连接对象
            agent_url: Agent 下载 URL (None 使用默认)

        Returns:
            下载是否成功
        """
        url = agent_url or self.AGENT_DOWNLOAD_URL
        proxy_arg = f"-x http://{self.squid_proxy}" if self.squid_proxy else ""
        download_dir = self.AGENT_TMP_PATH  # /opt

        cmd = (
            f"mkdir -p {download_dir} && cd {download_dir} && "
            f"curl {proxy_arg} -o sms-agent-linux.tar.gz -s -w '%{{http_code}}' "
            f"--connect-timeout 30 '{url}'"
        )
        logger.info("Downloading SMS Agent on source via squid proxy")
        result = self.ssh.execute(ssh_conn, cmd, timeout=120)

        if not result:
            logger.error("Download command failed")
            return False

        stdout = result.get("stdout", "").strip()
        if stdout.endswith("200"):
            # 验证文件
            cmd = f"ls -la {download_dir}/sms-agent-linux.tar.gz"
            verify = self.ssh.execute(ssh_conn, cmd)
            if verify and "sms-agent-linux.tar.gz" in (verify.get("stdout", "") or ""):
                logger.info("SMS Agent package downloaded successfully")
                return True

        logger.error(f"Download failed: HTTP {stdout}")
        return False

    def upload_agent_package(self, ssh_conn, local_path: str) -> bool:
        """通过 SFTP 上传 Agent 安装包到源端

        Args:
            ssh_conn: SSH 连接对象
            local_path: 本地 Agent 安装包路径

        Returns:
            上传是否成功
        """
        remote_path = f"{self.AGENT_TMP_PATH}/sms-agent-linux.tar.gz"
        logger.info(f"Uploading Agent package: {local_path} -> {remote_path}")

        # 确保目标目录存在且非 tmpfs
        self.ssh.execute(ssh_conn, f"mkdir -p {self.AGENT_TMP_PATH}")

        if self.ssh.upload_file(ssh_conn, local_path, remote_path):
            logger.info("Agent package uploaded successfully")
            return True
        else:
            logger.error("Agent package upload failed")
            return False

    # ──────────────────────────────────────────────────────────────
    #  Agent 安装
    # ──────────────────────────────────────────────────────────────

    def check_rsync(self, ssh_conn) -> bool:
        """检查源端是否已安装 rsync

        Args:
            ssh_conn: SSH 连接对象

        Returns:
            rsync 是否可用
        """
        result = self.ssh.execute(ssh_conn, "which rsync 2>/dev/null && rsync --version 2>/dev/null | head -1")
        stdout = (result.get("stdout", "") or "").strip() if result else ""
        if stdout and ("rsync  version" in stdout.lower() or "rsync version" in stdout.lower()):
            logger.info(f"rsync already installed: {stdout}")
            return True
        logger.warning("rsync not found on source host")
        return False

    def _compile_rsync_on_proxy(self, proxy_client) -> bool:
        """在代理 ECS 上部署 rsync (二进制包优先，源码编译兜底)

        v2.6.0 优化: 优先使用预编译二进制包 (RSYNC_BINARY_PATH 环境变量)，
        直接上传解压即可，跳过下载源码 + configure + make 全流程。
        部署时间从 2-5 分钟降至 5-10 秒。
        如未提供二进制包或部署失败，回退到源码编译模式。

        线程安全: 使用类级锁保护部署过程，避免 100 台并发时多个线程
        同时下载/解压/编译 rsync 导致的竞态条件。

        P1-1优化: 快速缓存检查 (不加锁)，避免100并发时的锁竞争。
        使用双重检查锁定模式: 先无锁检查缓存，命中则直接返回；
        未命中才获取锁，再次检查后部署。

        Args:
            proxy_client: paramiko SSHClient 连接到代理 ECS

        Returns:
            部署是否成功
        """
        # P1-1优化: 快速缓存检查 (无锁，避免100并发时的锁竞争)
        # 如果rsync已编译且可用，直接返回，无需获取锁
        stdin, stdout, stderr = proxy_client.exec_command(
            "test -x /opt/rsync-bin/rsync && /opt/rsync-bin/rsync --version | head -1"
        )
        out = stdout.read().decode().strip()
        if out and ("rsync  version" in out.lower() or "rsync version" in out.lower()):
            logger.info(f"rsync cache hit (pre-lock): {out}")
            return True

        with self._rsync_compile_lock:
            logger.info("Compiling rsync on proxy ECS (lock acquired)")

            # Double-check: 可能在等待锁期间其他线程已完成编译
            stdin, stdout, stderr = proxy_client.exec_command(
                "test -x /opt/rsync-bin/rsync && /opt/rsync-bin/rsync --version | head -1"
            )
            out = stdout.read().decode().strip()
            if out and ("rsync  version" in out.lower() or "rsync version" in out.lower()):
                logger.info(f"rsync already compiled on proxy: {out}")
                return True

            # ── 二进制包快速路径 (v2.6.0 优化) ──
            # 如果提供了预编译二进制包 (RSYNC_BINARY_PATH)，直接上传解压，
            # 跳过下载源码 + configure + make 全流程，将部署时间从 2-5 分钟降至 5-10 秒
            local_rsync_bin = os.environ.get("RSYNC_BINARY_PATH", "")
            if local_rsync_bin and os.path.exists(local_rsync_bin):
                logger.info(f"[v2.6] Deploying pre-compiled rsync binary: {local_rsync_bin}")
                try:
                    sftp = proxy_client.open_sftp()
                    sftp.put(local_rsync_bin, "/opt/rsync-bin-pkg.tar.gz")
                    sftp.close()
                    logger.info(f"[v2.6] Binary package uploaded ({os.path.getsize(local_rsync_bin)} bytes)")
                except Exception as e:
                    logger.warning(f"[v2.6] Binary upload failed: {e}, falling back to source compile")
                    local_rsync_bin = ""

                if local_rsync_bin:
                    # 解压并安装: tar 包内是 rsync 可执行文件
                    deploy_cmd = (
                        "mkdir -p /opt/rsync-bin && "
                        "cd /opt && tar xzf rsync-bin-pkg.tar.gz -C /opt/rsync-bin/ && "
                        "chmod +x /opt/rsync-bin/rsync && "
                        "/opt/rsync-bin/rsync --version | head -1"
                    )
                    stdin, stdout, stderr = proxy_client.exec_command(deploy_cmd, timeout=30)
                    out = stdout.read().decode().strip()
                    err = stderr.read().decode().strip()
                    if out and ("rsync  version" in out.lower() or "rsync version" in out.lower()):
                        logger.info(f"[v2.6] rsync binary deployed in seconds: {out}")
                        return True
                    logger.warning(
                        f"[v2.6] Binary deploy failed: stdout={out[:200]}, stderr={err[:200]}, "
                        f"falling back to source compile"
                    )

            # 检查本地是否有 rsync 源码包 (通过环境变量 RSYNC_PACKAGE_PATH)
            local_rsync_src = os.environ.get("RSYNC_PACKAGE_PATH", "")
            if local_rsync_src and os.path.exists(local_rsync_src):
                logger.info(f"Uploading local rsync source: {local_rsync_src}")
                sftp = proxy_client.open_sftp()
                sftp.put(local_rsync_src, "/opt/rsync-3.5.0.tar.gz")
                sftp.close()
            else:
                # 在代理 ECS 上下载 rsync 源码 (代理有公网)
                stdin, stdout, stderr = proxy_client.exec_command(
                    "cd /opt && curl -o rsync-3.5.0.tar.gz -s -L "
                    "'https://download.samba.org/pub/rsync/src/rsync-3.5.0.tar.gz' "
                    "&& ls -la rsync-3.5.0.tar.gz",
                    timeout=120,
                )
                out = stdout.read().decode().strip()
                if "rsync-3.5.0.tar.gz" not in out:
                    logger.error("Failed to download rsync source on proxy")
                    return False

            # 编译 rsync
            # rsync 3.5.0 使用 configure.sh (autoconf 生成) 而非 configure (包装脚本)
            # configure 包装脚本会执行 packaging/prep-auto-dir，可能失败导致退出
            # 有效禁用选项: --disable-openssl --disable-xxhash --disable-lz4 --disable-zstd
            # 注意: --disable-zlib 不是有效选项 (rsync 3.5.0 内置 zlib)
            compile_cmd = (
                "cd /opt && rm -rf rsync-3.5.0 && "
                "tar xzf rsync-3.5.0.tar.gz && cd rsync-3.5.0 && "
                "./configure.sh --disable-openssl --disable-xxhash --disable-lz4 --disable-zstd && "
                "make -j$(nproc) && "
                "mkdir -p /opt/rsync-bin && "
                "cp rsync /opt/rsync-bin/rsync && "
                "chmod +x /opt/rsync-bin/rsync && "
                "/opt/rsync-bin/rsync --version | head -1"
            )
            stdin, stdout, stderr = proxy_client.exec_command(compile_cmd, timeout=300)
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            # 验证编译成功: 检查二进制是否存在且输出版本号 (而非仅含 "rsync" 字样)
            if out and ("rsync  version" in out.lower() or "rsync version" in out.lower()):
                logger.info(f"rsync compiled on proxy: {out}")
                return True

            logger.warning(f"rsync compilation failed on proxy. stdout={out[:500]}, stderr={err[:500]}, trying system rsync fallback")

            # Fallback: use system rsync if available (e.g. /usr/bin/rsync)
            stdin, stdout, stderr = proxy_client.exec_command(
                "which rsync 2>/dev/null && rsync --version 2>/dev/null | head -1"
            )
            sys_out = stdout.read().decode().strip()
            if sys_out and ("rsync  version" in sys_out.lower() or "rsync version" in sys_out.lower()):
                logger.info(f"System rsync found on proxy: {sys_out}, copying to /opt/rsync-bin/")
                stdin, stdout, stderr = proxy_client.exec_command(
                    "mkdir -p /opt/rsync-bin && cp $(which rsync) /opt/rsync-bin/rsync && "
                    "chmod +x /opt/rsync-bin/rsync && /opt/rsync-bin/rsync --version | head -1"
                )
                fallback_out = stdout.read().decode().strip()
                if fallback_out and ("rsync  version" in fallback_out.lower() or "rsync version" in fallback_out.lower()):
                    logger.info(f"System rsync copied to /opt/rsync-bin/rsync: {fallback_out}")
                    return True

            logger.error("rsync not available on proxy (neither compiled nor system)")
            return False

    def install_rsync(self, ssh_conn) -> bool:
        """在源端安装 rsync — 代理编译+分发模式

        在代理 ECS (有公网) 上编译 rsync，然后通过 GOST 隧道将编译好的
        二进制分发到私网源端。避免私网环境 yum 不可用 (镜像 403) 的问题。

        流程:
          1. 连接代理 ECS 直接 (proxy_ip:22)
          2. 在代理 ECS 上编译 rsync (如尚未编译)
          3. 从代理 ECS 下载 rsync 二进制到本地临时文件
          4. 通过 GOST 隧道上传到源端 /usr/local/bin/rsync
          5. 设置权限并验证

        Args:
            ssh_conn: SSH 连接对象 (到源端的 GOST 隧道连接)

        Returns:
            安装是否成功
        """
        logger.info("Installing rsync via proxy-compile-and-distribute")

        if paramiko is None:
            logger.error("paramiko is required for proxy rsync compilation")
            return False

        # ── 快速路径: 如果提供了预编译二进制包，直接上传到源端 ──
        # 避免连接代理 ECS，减少网络跳转，提高可靠性
        local_rsync_bin = os.environ.get("RSYNC_BINARY_PATH", "")
        if local_rsync_bin and os.path.exists(local_rsync_bin):
            logger.info(f"[v2.9.7] Direct rsync binary upload to source: {local_rsync_bin}")
            remote_path = "/usr/local/bin/rsync"
            try:
                # 解压 tar.gz 并上传 rsync 二进制
                import tarfile
                with tarfile.open(local_rsync_bin, "r:gz") as tar:
                    rsync_member = None
                    for m in tar.getmembers():
                        if m.name.endswith("rsync") and m.isfile():
                            rsync_member = m
                            break
                    if rsync_member:
                        tmp_extract = tempfile.NamedTemporaryFile(delete=False, suffix=".rsync")
                        tmp_extract.close()
                        tar.extract(rsync_member, path=os.path.dirname(tmp_extract.name))
                        extracted_path = os.path.join(os.path.dirname(tmp_extract.name), rsync_member.name)
                        try:
                            if self.ssh.upload_file(ssh_conn, extracted_path, remote_path):
                                cmd = f"chmod +x {remote_path} && ln -sf {remote_path} /usr/bin/rsync 2>/dev/null; {remote_path} --version | head -1"
                                result = self.ssh.execute(ssh_conn, cmd)
                                stdout = (result.get("stdout", "") or "").strip() if result else ""
                                if stdout and ("rsync  version" in stdout.lower() or "rsync version" in stdout.lower()):
                                    logger.info(f"[v2.9.7] rsync directly uploaded to source: {stdout}")
                                    return True
                                logger.warning(f"[v2.9.7] Direct upload verify failed: {stdout}")
                        finally:
                            try:
                                os.unlink(extracted_path)
                                os.unlink(tmp_extract.name)
                            except OSError:
                                pass
                    else:
                        # tar 包内直接就是 rsync 二进制 (无目录结构)
                        tmp_extract = tempfile.NamedTemporaryFile(delete=False, suffix=".rsync")
                        tmp_extract.close()
                        try:
                            tar.extractall(path=os.path.dirname(tmp_extract.name))
                            # 找到解压后的 rsync 文件
                            for root, dirs, files in os.walk(os.path.dirname(tmp_extract.name)):
                                for f in files:
                                    if f == "rsync":
                                        extracted_path = os.path.join(root, f)
                                        if self.ssh.upload_file(ssh_conn, extracted_path, remote_path):
                                            cmd = f"chmod +x {remote_path} && ln -sf {remote_path} /usr/bin/rsync 2>/dev/null; {remote_path} --version | head -1"
                                            result = self.ssh.execute(ssh_conn, cmd)
                                            stdout = (result.get("stdout", "") or "").strip() if result else ""
                                            if stdout and ("rsync  version" in stdout.lower() or "rsync version" in stdout.lower()):
                                                logger.info(f"[v2.9.7] rsync directly uploaded to source: {stdout}")
                                                return True
                        finally:
                            try:
                                os.unlink(tmp_extract.name)
                            except OSError:
                                pass
                logger.warning("[v2.9.7] Direct binary upload failed, falling back to proxy-compile")
            except Exception as e:
                logger.warning(f"[v2.9.7] Direct binary upload error: {e}, falling back to proxy-compile")

        # 1. 连接代理 ECS 直接 (不通过 GOST)
        try:
            proxy_client = paramiko.SSHClient()
            proxy_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            proxy_client.connect(
                self.proxy_ip,
                port=22,
                username=self.proxy_username,
                password=self.proxy_password,
                timeout=15,
            )
        except Exception as e:
            logger.error(f"Failed to connect to proxy ECS for rsync: {e}")
            return False

        try:
            # 2. 在代理 ECS 上编译 rsync
            if not self._compile_rsync_on_proxy(proxy_client):
                logger.error("Failed to compile rsync on proxy ECS")
                return False

            # 3. 从代理 ECS 下载 rsync 二进制到本地临时文件
            local_rsync = tempfile.NamedTemporaryFile(delete=False, suffix=".rsync")
            local_rsync.close()
            sftp_proxy = proxy_client.open_sftp()
            sftp_proxy.get("/opt/rsync-bin/rsync", local_rsync.name)
            sftp_proxy.close()
            logger.info(f"Downloaded rsync binary from proxy: {os.path.getsize(local_rsync.name)} bytes")
        finally:
            proxy_client.close()

        # 4. 通过 GOST 隧道上传到源端
        remote_path = "/usr/local/bin/rsync"
        try:
            if not self.ssh.upload_file(ssh_conn, local_rsync.name, remote_path):
                logger.error("Failed to upload rsync binary to source")
                return False

            # 5. 设置权限并验证
            cmd = f"chmod +x {remote_path} && {remote_path} --version | head -1"
            result = self.ssh.execute(ssh_conn, cmd)
            stdout = (result.get("stdout", "") or "").strip() if result else ""
            if stdout and ("rsync  version" in stdout.lower() or "rsync version" in stdout.lower()):
                logger.info(f"rsync installed on source: {stdout}")
                return True

            logger.error("rsync verification failed on source")
            return False
        finally:
            try:
                os.unlink(local_rsync.name)
            except OSError:
                pass

    def install_agent(
        self,
        ssh_conn,
        region: str = "cn-north-1",
        ak: str = None,
        sk: str = None,
        use_proxy: bool = True,
        source_password: str = "",
    ) -> bool:
        """在源端安装 SMS Agent — 分离安装和启动 (绕过 startup.sh)

        优化: 不再走 printf|bash startup.sh (170s sleep等待)
        而是: 解压 + 预配置 + 直接 nohup linuxmain 启动

        Args:
            ssh_conn: SSH 连接
            region: 华为云区域
            ak: AK (用于 Agent 注册)
            sk: SK
            use_proxy: 是否使用 squid 代理
            source_password: 源端密码 (linuxmain 启动需要)

        Returns:
            安装是否成功
        """
        agent_base = self.AGENT_TMP_PATH  # /opt
        agent_dir = self.AGENT_INSTALL_PATH  # /opt/SMS-Agent

        # 1. 确保 rsync 可用 (SMS Agent 依赖 rsync)
        if not self.check_rsync(ssh_conn):
            if not self.install_rsync(ssh_conn):
                logger.error("rsync installation failed, SMS Agent may not work properly")

        # 2. 解压安装包到 /opt (非 tmpfs, 避免空间不足)
        cmd = (
            f"cd {agent_base} && "
            f"tar xzf sms-agent-linux.tar.gz -C {agent_base}/ && "
            f"ls {agent_dir}/startup.sh"
        )
        result = self.ssh.execute(ssh_conn, cmd, timeout=60)
        if not result or "startup.sh" not in (result.get("stdout", "") or ""):
            logger.error("Failed to extract Agent package")
            return False

        # 3. 预创建 sms_domain 配置
        sms_domain = f"sms.{region}.myhuaweicloud.com"
        cmd = (
            f"mkdir -p {agent_dir}/config && "
            f"echo '{sms_domain}' > {agent_dir}/config/sms_domain.txt && "
            f"chmod 640 {agent_dir}/config/sms_domain.txt"
        )
        self.ssh.execute(ssh_conn, cmd, timeout=10)
        logger.info(f"Pre-created sms_domain config: {sms_domain}")

        # 3.5 配置 auth.cfg (私网代理设置)
        if self.proxy_private_ip:
            auth_cfg_path = f"{agent_dir}/agent/config/auth.cfg"
            cmd = (
                f"mkdir -p {agent_dir}/agent/config && "
                f"echo 'enable = true' > {auth_cfg_path} && "
                f"echo 'proxy_addr = http://{self.proxy_private_ip}' >> {auth_cfg_path} && "
                f"chmod 640 {auth_cfg_path}"
            )
            result_cfg = self.ssh.execute(ssh_conn, cmd, timeout=10)
            if result_cfg and result_cfg.get("exit_code", -1) == 0:
                logger.info(f"Configured auth.cfg: enable=true, proxy_addr=http://{self.proxy_private_ip}")
            else:
                logger.warning("Failed to configure auth.cfg, Agent may not use proxy correctly")
        else:
            logger.warning("proxy_private_ip not set, auth.cfg not configured")

        # 4. 确保二进制就位 (startup.sh 正常会做的 cp, 这里提前做)
        cmd = (
            f"cd {agent_dir}/agent/ && "
            f"if [ ! -e linuxmain ]; then "
            f"  if [ -x aarch64/linuxmain ]; then cp -f aarch64/linuxmain .; "
            f"  elif [ -x x64/linuxmain ]; then cp -f x64/linuxmain .; fi; fi && "
            f"if [ ! -e libsrcAgent.so ]; then "
            f"  if [ -f ioblock/x64/libsrcAgent.so ]; then cp -f ioblock/x64/libsrcAgent.so .; fi; fi && "
            f"chmod +x linuxmain && test -x linuxmain"
        )
        result = self.ssh.execute(ssh_conn, cmd, timeout=15)
        if not result or result.get("exit_code", -1) != 0:
            logger.error("Failed to prepare linuxmain binary")
            return False
        logger.info("Agent binaries prepared (linuxmain + libsrcAgent.so)")

        # 5. 直接启动 linuxmain (绕过 startup.sh, 省掉170s sleep)
        logger.info("Starting SMS Agent via direct linuxmain (bypassing startup.sh)")
        if self._start_linuxmain_directly(
            ssh_conn, ak=ak, sk=sk, region=region,
            password=source_password, timeout=60,
        ):
            logger.info("SMS Agent installed and started successfully")
            return True

        logger.error("Agent installation failed: linuxmain did not start")
        return False

    # ──────────────────────────────────────────────────────────────
    #  Agent 注册验证
    # ──────────────────────────────────────────────────────────────

    def verify_agent_running(self, ssh_conn, timeout: int = 120) -> bool:
        """验证 Agent 进程运行

        Args:
            ssh_conn: SSH 连接
            timeout: 等待超时

        Returns:
            Agent 是否运行
        """
        start = time.time()
        while time.time() - start < timeout:
            # 优先检查 linuxmain 进程 (SMS Agent 核心进程)
            cmd = "pgrep -x linuxmain 2>/dev/null | wc -l"
            result = self.ssh.execute(ssh_conn, cmd)
            if result:
                count = (result.get("stdout", "") or "").strip()
                if count and int(count) > 0:
                    logger.info("SMS Agent (linuxmain) process is running")
                    return True
            # 回退检查 sms agent 进程
            cmd = "ps aux | grep -i 'sms.*agent' | grep -v grep | wc -l"
            result = self.ssh.execute(ssh_conn, cmd)
            if result:
                count = (result.get("stdout", "") or "").strip()
                if count and int(count) > 0:
                    logger.info("SMS Agent process is running")
                    return True
            time.sleep(5)

        logger.error("SMS Agent process not running after timeout")
        return False

    def get_agent_registration_info(self, ssh_conn) -> Optional[Dict]:
        """获取 Agent 注册信息

        统一检查路径 (与 check_agent_installed 一致):
          /usr/local/sms-agent/ → /opt/SMS-Agent/ → /SMSAgent/
        """
        cmd = (
            "cat /usr/local/sms-agent/agent_conf.json 2>/dev/null "
            f"|| cat {self.AGENT_INSTALL_PATH}/agent_conf.json 2>/dev/null "
            "|| cat /SMSAgent/agent_conf.json 2>/dev/null"
        )
        result = self.ssh.execute(ssh_conn, cmd)
        if result:
            stdout = result.get("stdout", "") or ""
            if stdout.strip():
                return {"config": stdout.strip()}
        return None

    # ──────────────────────────────────────────────────────────────
    #  Agent 完整性检查与重启 (优化安装耗时)
    # ──────────────────────────────────────────────────────────────

    def _check_agent_config_complete(
        self, ssh_conn, region: str = "cn-north-1"
    ) -> bool:
        """检查 Agent 配置是否完整 (用于决定是否可以仅重启而非重新下发)

        检查项:
          - sms_domain.txt 存在且内容匹配 region
          - agent_conf.json 存在 (Agent 注册配置)
          - Agent 核心二进制 (linuxmain) 存在

        Args:
            ssh_conn: SSH 连接对象
            region: 华为云区域

        Returns:
            配置是否完整
        """
        expected_domain = f"sms.{region}.myhuaweicloud.com"

        # 检查 sms_domain 配置 (统一路径)
        cmd = (
            f"cat {self.AGENT_INSTALL_PATH}/config/sms_domain.txt 2>/dev/null "
            "|| cat /usr/local/sms-agent/config/sms_domain.txt 2>/dev/null"
        )
        result = self.ssh.execute(ssh_conn, cmd)
        domain = (result.get("stdout", "") or "").strip() if result else ""
        if not domain:
            logger.warning("Agent config incomplete: sms_domain.txt not found")
            return False
        if expected_domain not in domain:
            logger.warning(f"Agent config mismatch: domain={domain}, expected={expected_domain}")
            return False

        # 检查 agent_conf.json (Agent 注册配置, 统一路径)
        cmd = (
            f"test -f {self.AGENT_INSTALL_PATH}/agent_conf.json "
            "|| test -f /usr/local/sms-agent/agent_conf.json"
        )
        result = self.ssh.execute(ssh_conn, cmd)
        exit_code = result.get("exit_code", -1) if result else -1
        if exit_code != 0:
            logger.warning("Agent config incomplete: agent_conf.json not found")
            return False

        # 检查 Agent 核心二进制 (linuxmain)
        cmd = (
            f"test -x {self.AGENT_INSTALL_PATH}/agent/linuxmain "
            "|| test -x /usr/local/sms-agent/agent/linuxmain "
            "|| test -x /usr/local/sms-agent/linuxmain"
        )
        result = self.ssh.execute(ssh_conn, cmd)
        exit_code = result.get("exit_code", -1) if result else -1
        if exit_code != 0:
            logger.warning("Agent config incomplete: linuxmain binary not found")
            return False

        # 检查 auth.cfg (私网代理配置)
        auth_cfg_cmd = (
            f"cat {self.AGENT_INSTALL_PATH}/agent/config/auth.cfg 2>/dev/null "
            "|| cat /usr/local/sms-agent/agent/config/auth.cfg 2>/dev/null"
        )
        result = self.ssh.execute(ssh_conn, auth_cfg_cmd)
        auth_content = (result.get("stdout", "") or "").strip() if result else ""
        if not auth_content:
            logger.warning("Agent config incomplete: auth.cfg not found")
            return False
        if "enable = true" not in auth_content and "enable=true" not in auth_content:
            logger.warning("Agent config incomplete: auth.cfg enable is not true")
            return False

        logger.info("Agent config complete: sms_domain + agent_conf + binary + auth.cfg all present")
        return True


    def _start_linuxmain_directly(
        self, ssh_conn, ak: str, sk: str, region: str, password: str = "", timeout: int = 60
    ) -> bool:
        """直接启动 linuxmain 进程 (绕过 startup.sh 的170s sleep等待)

        startup.sh 内部流程: base_check → 交互输入 → user-confirm(30s) → get-eps(60s)
        → pre-check(20s) → nohup linuxmain → wait_start(60s) = 最多170s 纯sleep
        本方法直接执行最后一步: nohup ./linuxmain 0 <<< 'ak sk domain password'

        Args:
            ssh_conn: SSH 连接
            ak: Access Key
            sk: Secret Key
            region: 华为云区域
            password: 源端密码 (linuxmain 需要)
            timeout: 等待启动超时
        """
        agent_dir = self.AGENT_INSTALL_PATH  # /opt/SMS-Agent
        sms_domain = f"sms.{region}.myhuaweicloud.com"
        linuxmain_input = f"{ak} {sk} {sms_domain} {password}"

        # 设置 LD_LIBRARY_PATH 并直接启动 linuxmain (eps=0 默认企业项目)
        start_cmd = (
            f"cd {agent_dir}/agent/ && "
            f"export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:{agent_dir}/agent/lib && "
            f"nohup ./linuxmain 0 <<< '{linuxmain_input}' > /dev/null 2>&1 &"
        )
        logger.info("Starting linuxmain directly (bypassing startup.sh)")
        self.ssh.execute(ssh_conn, start_cmd, timeout=15)

        # 验证进程启动
        if self.verify_agent_running(ssh_conn, timeout=timeout):
            logger.info("linuxmain started successfully (direct launch)")
            return True

        logger.error("linuxmain direct launch failed")
        return False
    # ================================================================
    # 状态机驱动 — 全场景覆盖, 无试错无fallback
    # ================================================================

    _LOCAL_AGENT_VERSION = None

    def _get_local_agent_version(self) -> str:
        """从本地 SMS-Agent.tar.gz 读取版本号 (懒加载)"""
        if self._LOCAL_AGENT_VERSION:
            return self._LOCAL_AGENT_VERSION
        for path in [
            "/root/migration-work/SMS-Agent.tar.gz",
            os.path.expanduser("~/migration-work/SMS-Agent.tar.gz"),
        ]:
            if os.path.exists(path):
                try:
                    import tarfile
                    with tarfile.open(path, "r:gz") as tar:
                        try:
                            f = tar.extractfile("SMS-Agent/agent/version")
                            if f:
                                lines = f.read().decode().strip().split("\n")
                                ver = lines[-1].strip() if lines else ""
                                if ver:
                                    self._LOCAL_AGENT_VERSION = ver
                                    logger.info(f"Local agent version: {ver}")
                                    return ver
                        except KeyError:
                            pass
                except Exception as e:
                    logger.warning(f"Failed to read local agent version: {e}")
        self._LOCAL_AGENT_VERSION = "26.6.0"
        return self._LOCAL_AGENT_VERSION

    def _upload_state_script(self, ssh_conn) -> str:
        """上传 agent_state_check.sh 到源端, 返回远程路径"""
        remote_path = "/tmp/agent_state_check.sh"
        local_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "agent_state_check.sh"
        )
        if not os.path.exists(local_path):
            logger.error(f"agent_state_check.sh not found at {local_path}")
            return ""
        try:
            if self.ssh.upload_file(ssh_conn, local_path, remote_path):
                self.ssh.execute(ssh_conn, f"chmod +x {remote_path}")
                logger.info(f"Uploaded agent_state_check.sh to {remote_path}")
                return remote_path
            else:
                logger.error("upload_file returned False")
                return ""
        except Exception as e:
            logger.error(f"Failed to upload state script: {e}")
            return ""

    def _detect_agent_state(
        self, ssh_conn, script_path: str, region: str = "cn-north-1"
    ) -> Dict[str, Any]:
        """一次SSH完成全状态检测

        通过 agent_state_check.sh check 模式获取:
          - 包位置 (tmp/opt/无)
          - 进程状态
          - 版本
          - 配置完整性

        Returns:
            {state, agent_dir, version, process_running, config_complete, ...}
        """
        result = self.ssh.execute(ssh_conn, f"bash {script_path} check", timeout=15)
        raw = (result.get("stdout", "") or "") if result else ""

        info = {
            "state": "UNKNOWN",
            "agent_dir": "",
            "all_dirs": "",
            "version": "",
            "process_running": False,
            "proc_pid": "",
            "config_complete": False,
            "domain": "",
            "conf_exists": False,
            "auth_enable": False,
            "binary_ok": False,
        }

        for line in raw.strip().split("\n"):
            line = line.strip()
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key == "STATE":
                info["state"] = value
            elif key == "AGENT_DIR":
                info["agent_dir"] = value
            elif key == "ALL_DIRS":
                info["all_dirs"] = value
            elif key == "VERSION":
                info["version"] = value
            elif key == "PROC_COUNT":
                try:
                    info["process_running"] = int(value) > 0
                except ValueError:
                    pass
            elif key == "PROC_PID":
                info["proc_pid"] = value
            elif key == "CONFIG_COMPLETE":
                info["config_complete"] = value == "yes"
            elif key == "DOMAIN":
                info["domain"] = value
            elif key == "CONF_EXISTS":
                info["conf_exists"] = value == "yes"
            elif key == "AUTH_ENABLE":
                info["auth_enable"] = value == "yes"
            elif key == "BINARY_OK":
                info["binary_ok"] = value == "yes"

        logger.info(
            f"Agent state detected: {info['state']} "
            f"(dir={info['agent_dir']}, ver={info['version']}, "
            f"running={info['process_running']}, cfg={info['config_complete']})"
        )
        return info

    def _clean_agent_remote(
        self, ssh_conn, script_path: str, target_dir: str = ""
    ) -> bool:
        """清理 agent: 杀进程 + 删除目录"""
        cmd = f"bash {script_path} clean {target_dir}".strip()
        result = self.ssh.execute(ssh_conn, cmd, timeout=15)
        raw = (result.get("stdout", "") or "") if result else ""
        ok = "CLEAN_DONE=yes" in raw
        logger.info(f"Agent clean ({target_dir or 'all'}): {'OK' if ok else 'FAILED'}")
        return ok

    def _configure_and_start(
        self, ssh_conn, script_path: str, agent_dir: str,
        region: str, ak: str, sk: str, password: str = "",
    ) -> bool:
        """写配置 + 直接启动 linuxmain (通过脚本)"""
        proxy_ip = self.proxy_private_ip or ""
        cmd = f"bash {script_path} config {agent_dir} {region} {proxy_ip}"
        result = self.ssh.execute(ssh_conn, cmd, timeout=15)
        raw = (result.get("stdout", "") or "") if result else ""
        if "CONFIG_DONE=yes" not in raw:
            logger.error("Failed to configure agent")
            return False
        logger.info(f"Agent configured at {agent_dir}")

        cmd = f"bash {script_path} start {agent_dir} {ak} {sk} {region} {password}"
        result = self.ssh.execute(ssh_conn, cmd, timeout=30)
        raw = (result.get("stdout", "") or "") if result else ""
        if "START_RESULT=success" in raw:
            logger.info("Agent started successfully")
            return True
        logger.error(f"Agent start failed: {raw}")
        return False

    def _full_deploy(
        self, ssh_conn, region: str, ak: str, sk: str,
        password: str = "", use_proxy: bool = True,
        local_agent_path: str = None, agent_url: str = None,
    ) -> bool:
        """完整下发: 下载/上传包 → 解压 → 配置 → 启动"""
        logger.info("=== Full deploy: download → extract → config → start ===")

        # 1. 确保 rsync 可用
        if not self.check_rsync(ssh_conn):
            if not self.install_rsync(ssh_conn):
                logger.warning("rsync install failed, continuing anyway")

        agent_base = self.AGENT_TMP_PATH  # /opt
        agent_dir = self.AGENT_INSTALL_PATH  # /opt/SMS-Agent

        # 2. 下载/上传 agent 包 (优先使用本地包上传)
        if local_agent_path and os.path.exists(local_agent_path):
            if not self.upload_agent_package(ssh_conn, local_agent_path):
                logger.error("Failed to upload local agent package")
                return False
        elif not self.download_agent_on_source(ssh_conn, agent_url):
            logger.info("Download failed, trying SFTP upload")
            local_path = local_agent_path or "/root/migration-work/SMS-Agent.tar.gz"
            if os.path.exists(local_path):
                if not self.upload_agent_package(ssh_conn, local_path):
                    logger.error("Both download and upload failed")
                    return False
            else:
                logger.error(f"Agent package not found: {local_path}")
                return False

        # 3. 解压
        cmd = (
            f"cd {agent_base} && "
            f"tar xzf sms-agent-linux.tar.gz -C {agent_base}/ && "
            f"ls {agent_dir}/startup.sh"
        )
        result = self.ssh.execute(ssh_conn, cmd, timeout=60)
        if not result or "startup.sh" not in (result.get("stdout", "") or ""):
            logger.error("Failed to extract agent package")
            return False
        logger.info("Agent package extracted")

        # 4. 配置 + 启动
        script_path = self._upload_state_script(ssh_conn)
        if not script_path:
            return self._configure_and_start_inline(
                ssh_conn, agent_dir, region, ak, sk, password
            )
        return self._configure_and_start(
            ssh_conn, script_path, agent_dir, region, ak, sk, password
        )

    def _configure_and_start_inline(
        self, ssh_conn, agent_dir: str,
        region: str, ak: str, sk: str, password: str = "",
    ) -> bool:
        """内联命令配置+启动 (不依赖脚本, 回退方案)"""
        sms_domain = f"sms.{region}.myhuaweicloud.com"

        cmd = (
            f"mkdir -p {agent_dir}/config && "
            f"echo '{sms_domain}' > {agent_dir}/config/sms_domain.txt && "
            f"chmod 640 {agent_dir}/config/sms_domain.txt"
        )
        self.ssh.execute(ssh_conn, cmd, timeout=10)

        if self.proxy_private_ip:
            auth_cfg = f"{agent_dir}/agent/config/auth.cfg"
            cmd = (
                f"mkdir -p {agent_dir}/agent/config && "
                f"echo 'enable = true' > {auth_cfg} && "
                f"echo 'proxy_addr = http://{self.proxy_private_ip}' >> {auth_cfg} && "
                f"chmod 640 {auth_cfg}"
            )
            self.ssh.execute(ssh_conn, cmd, timeout=10)

        cmd = (
            f"cd {agent_dir}/agent/ && "
            f"if [ ! -e linuxmain ]; then "
            f"  if [ -x aarch64/linuxmain ]; then cp -f aarch64/linuxmain .; "
            f"  elif [ -x x64/linuxmain ]; then cp -f x64/linuxmain .; fi; fi && "
            f"if [ ! -e libsrcAgent.so ]; then "
            f"  if [ -f ioblock/x64/libsrcAgent.so ]; then cp -f ioblock/x64/libsrcAgent.so .; "
            f"  elif [ -f ioblock/aarch64/libsrcAgent.so ]; then cp -f ioblock/aarch64/libsrcAgent.so .; fi; fi && "
            f"chmod +x linuxmain && test -x linuxmain"
        )
        result = self.ssh.execute(ssh_conn, cmd, timeout=15)
        if not result or result.get("exit_code", -1) != 0:
            logger.error("Failed to prepare linuxmain binary")
            return False

        return self._start_linuxmain_directly(
            ssh_conn, ak=ak, sk=sk, region=region,
            password=password, timeout=60,
        )

    def _handle_by_state(
        self, ssh_conn, state_info: Dict, script_path: str,
        region: str, ak: str, sk: str, password: str = "",
        use_proxy: bool = True,
        local_agent_path: str = None, agent_url: str = None,
    ) -> Dict[str, Any]:
        """按状态分发处理 — 状态机核心

        状态 → 动作:
          NO_PACKAGE           → 完整下发+配置+启动
          RUNNING              → 不做任何操作
          INSTALLED_NOT_CFG    → 检查版本配置 → OK:补配置+启动 / 不OK:删除+完整下发
          INSTALLED_CONFIGURED → 检查版本配置 → OK:直接启动 / 不OK:删除+完整下发
        """
        state = state_info["state"]
        result = {"action": "", "success": False, "detail": ""}

        # ── NO_PACKAGE: 完整下发 ──
        if state == "NO_PACKAGE":
            logger.info("[STATE] NO_PACKAGE → full deploy")
            result["action"] = "full_deploy"
            result["success"] = self._full_deploy(
                ssh_conn, region, ak, sk, password, use_proxy,
                local_agent_path=local_agent_path, agent_url=agent_url,
            )
            result["detail"] = "Deployed from scratch"
            if result["success"]:
                self._write_remote_ak_fingerprint(ssh_conn, ak)
            return result

        # ── RUNNING: 检查配置是否完整 ──
        if state == "RUNNING":
            config_ok = state_info.get("config_complete", False)
            if config_ok:
                # AK/SK 变更检测: 比较源端 .ak_fingerprint 与当前 AK 指纹
                new_fp = self._ak_fingerprint(ak)
                old_fp = self._read_remote_ak_fingerprint(ssh_conn)
                if new_fp and old_fp and new_fp != old_fp:
                    # AK/SK 已变更 → kill + 用新 AK/SK 重启
                    logger.warning(
                        f"[STATE] RUNNING+configured but AK/SK changed "
                        f"(old={old_fp}, new={new_fp}) → kill + restart with new credentials"
                    )
                    agent_dir = state_info.get("agent_dir", "/opt/SMS-Agent")
                    self.ssh.execute(
                        ssh_conn,
                        f"kill -9 {state_info.get('proc_pid', '')} 2>/dev/null; "
                        f"pkill -9 -x linuxmain 2>/dev/null; "
                        f"pkill -9 -f 'SMS-Agent|sms_agent' 2>/dev/null; sleep 1",
                        timeout=10,
                    )
                    result["action"] = "restart_credential_changed"
                    result["success"] = self._configure_and_start(
                        ssh_conn, script_path, agent_dir,
                        region, ak, sk, password,
                    )
                    if result["success"]:
                        self._write_remote_ak_fingerprint(ssh_conn, ak)
                    return result

                # AK/SK 未变更或无指纹记录 → skip (正常运行)
                logger.info(
                    f"[STATE] RUNNING+configured → skip (pid={state_info['proc_pid']}, "
                    f"ver={state_info['version']}, ak_fp={new_fp})"
                )
                result["action"] = "skip_running"
                result["success"] = True
                result["detail"] = f"Agent already running (pid={state_info['proc_pid']})"
                # 写入 fingerprint (首次运行时无标记文件)
                if new_fp and not old_fp:
                    self._write_remote_ak_fingerprint(ssh_conn, ak)
                return result
            else:
                # Agent 运行但配置不完整 → 停止、重新配置、启动
                logger.warning(
                    f"[STATE] RUNNING but config incomplete (pid={state_info['proc_pid']}, "
                    f"ver={state_info['version']}) → reconfigure"
                )
                agent_dir = state_info.get("agent_dir", "/opt/SMS-Agent")
                # 停止当前 agent 进程
                self.ssh.execute(ssh_conn, f"kill -9 {state_info.get('proc_pid', '')} 2>/dev/null; "
                                   f"pkill -9 -f 'SMS-Agent|sms_agent' 2>/dev/null; sleep 1", timeout=10)
                # 重新配置并启动
                result["action"] = "reconfigure_running"
                result["success"] = self._configure_and_start(
                    ssh_conn, script_path, agent_dir,
                    region, ak, sk, password,
                )
                if result["success"]:
                    self._write_remote_ak_fingerprint(ssh_conn, ak)
                return result

        # ── INSTALLED_NOT_CONFIGURED / INSTALLED_CONFIGURED ──
        local_ver = self._get_local_agent_version()
        remote_ver = state_info.get("version", "")
        version_ok = (remote_ver == local_ver) if remote_ver else False
        config_ok = state_info.get("config_complete", False)
        agent_dir = state_info.get("agent_dir", "")

        logger.info(
            f"[STATE] {state}: version_check={version_ok} "
            f"(local={local_ver}, remote={remote_ver}), config_check={config_ok}"
        )

        if version_ok and config_ok:
            # 版本一致 + 配置完整 → 直接启动
            logger.info(f"[STATE] {state} → start existing agent")
            result["action"] = "start_existing"

            if state == "INSTALLED_NOT_CONFIGURED":
                # 补配置 + 启动
                result["success"] = self._configure_and_start(
                    ssh_conn, script_path, agent_dir,
                    region, ak, sk, password,
                )
            else:
                # INSTALLED_CONFIGURED → 直接启动
                cmd = (
                    f"bash {script_path} start {agent_dir} "
                    f"{ak} {sk} {region} {password}"
                )
                r = self.ssh.execute(ssh_conn, cmd, timeout=30)
                raw = (r.get("stdout", "") or "") if r else ""
                result["success"] = "START_RESULT=success" in raw
            result["detail"] = "Started existing agent"
            if result["success"]:
                self._write_remote_ak_fingerprint(ssh_conn, ak)
            return result

        # 版本不一致 或 配置不完整 → 删除 + 完整下发
        logger.warning(
            f"[STATE] {state} → delete + full deploy "
            f"(version_ok={version_ok}, config_ok={config_ok})"
        )
        result["action"] = "delete_and_redeploy"

        # 删除所有 agent 目录
        self._clean_agent_remote(ssh_conn, script_path)

        # 完整下发
        result["success"] = self._full_deploy(
            ssh_conn, region, ak, sk, password, use_proxy,
            local_agent_path=local_agent_path, agent_url=agent_url,
        )
        result["detail"] = (
            f"Deleted and redeployed "
            f"(ver_mismatch={not version_ok}, cfg_incomplete={not config_ok})"
        )
        if result["success"]:
            self._write_remote_ak_fingerprint(ssh_conn, ak)
        return result

    def full_push(
        self,
        source_username: str,
        source_password: str = None,
        source_key_path: str = None,
        source_port: int = 22,
        region: str = "cn-north-1",
        ak: str = None,
        sk: str = None,
        local_agent_path: str = None,
        agent_url: str = None,
        timeout: int = 600,
        gost_ssh_port: int = None,
    ) -> Dict[str, Any]:
        """SMS Agent 全场景下发 — 状态机驱动, 单一入口

        线程安全: gost_ssh_port 作为参数传入, 不修改共享实例属性

        覆盖全部场景:
          - 无包 → 完整下发
          - 已启动 → 跳过 (不做任何操作)
          - 有包未启动, 版本配置OK → 直接启动
          - 有包未启动, 版本或配置不OK → 删除+完整下发

        Returns:
            {"success", "agent_installed", "agent_running", "error", "action", "state"}
        """
        result = {
            "success": False,
            "agent_installed": False,
            "agent_running": False,
            "error": "",
            "action": "",
            "state": "",
        }
        start_time = time.time()

        # 线程安全: 使用参数指定的端口, 回退到实例属性
        effective_port = gost_ssh_port if gost_ssh_port is not None else self.gost_ssh_port

        # 1. SSH 连接源端 (通过 GOST: proxy_ip:effective_port)
        logger.info(f"Connecting to source via GOST: {self.proxy_ip}:{effective_port}")
        ssh_conn = self.ssh.connect(
            host=self.proxy_ip,
            port=effective_port,
            username=source_username,
            password=source_password,
            key_path=source_key_path,
        )
        if not ssh_conn:
            result["error"] = "Failed to connect to source via GOST"
            return result

        try:
            # 2. 上传状态检测脚本
            script_path = self._upload_state_script(ssh_conn)
            if not script_path:
                result["error"] = "Failed to upload state script"
                return result

            # 3. 一次SSH检测状态
            state_info = self._detect_agent_state(ssh_conn, script_path, region)
            result["state"] = state_info["state"]

            # 4. 按状态分发处理
            handle_result = self._handle_by_state(
                ssh_conn, state_info, script_path,
                region, ak, sk, source_password or "",
                local_agent_path=local_agent_path,
                agent_url=agent_url,
            )
            result["action"] = handle_result["action"]

            if not handle_result["success"]:
                result["error"] = handle_result.get("detail", "handle failed")
                return result

            # 5. 验证 agent 运行
            if state_info["state"] == "RUNNING":
                result["agent_installed"] = True
                result["agent_running"] = True
                result["success"] = True
            else:
                result["agent_installed"] = True
                result["agent_running"] = self.verify_agent_running(
                    ssh_conn, timeout=60
                )
                result["success"] = result["agent_running"]
                if not result["agent_running"]:
                    result["error"] = "Agent not running after start"

            elapsed = round(time.time() - start_time, 2)
            logger.info(
                f"SMS Agent push completed: action={result['action']}, "
                f"state={result['state']}, running={result['agent_running']}, "
                f"elapsed={elapsed}s"
            )
            return result

        finally:
            self.ssh.disconnect(ssh_conn)

    # ================================================================
    #  AK/SK 自适应更新 — Agent 凭证变更感知与安全重启
    # ================================================================

    @staticmethod
    def _ak_fingerprint(ak: str) -> str:
        """计算 AK 指纹 (前8位，用于快速判断凭证是否变更)"""
        return ak[:8] if ak else ""

    def _read_remote_ak_fingerprint(self, ssh_conn) -> str:
        """读取源端 Agent 目录下的 .ak_fingerprint 标记"""
        agent_dirs = [self.AGENT_INSTALL_PATH, "/tmp/SMS-Agent", "/usr/local/sms-agent"]
        for d in agent_dirs:
            result = self.ssh.execute(ssh_conn, f"cat {d}/.ak_fingerprint 2>/dev/null", timeout=5)
            if result:
                fp = (result.get("stdout", "") or "").strip()
                if fp:
                    return fp
        return ""

    def _write_remote_ak_fingerprint(self, ssh_conn, ak: str) -> bool:
        """在源端 Agent 目录写入 .ak_fingerprint 标记"""
        fp = self._ak_fingerprint(ak)
        agent_dir = self.AGENT_INSTALL_PATH
        cmd = f"echo '{fp}' > {agent_dir}/.ak_fingerprint && chmod 640 {agent_dir}/.ak_fingerprint"
        result = self.ssh.execute(ssh_conn, cmd, timeout=5)
        return result and result.get("exit_code", -1) == 0

    def _check_agent_token_valid(
        self, ssh_conn, sms_ops, source_ip: str,
    ) -> Dict[str, Any]:
        """检查 Agent 的 token 是否仍有效 (通过 SMS source online 状态间接判断)

        Returns:
            {"token_valid": bool, "source_id": str, "online": bool}
        """
        result = {"token_valid": False, "source_id": "", "online": False}
        if not sms_ops:
            return result

        source = sms_ops.find_source_by_ip(source_ip)
        if not source:
            logger.warning(f"Source {source_ip} not found in SMS (token may be invalid)")
            return result

        source_id = source.get("id", "")
        result["source_id"] = source_id

        # 检查 source 状态
        state = sms_ops.get_source_state(source_id)
        online = state in ("online", "ONLINE", "1")
        result["online"] = online
        result["token_valid"] = online

        if online:
            logger.info(f"Source {source_ip} online (token valid)")
        else:
            logger.warning(f"Source {source_ip} not online (state={state}, token may be invalid)")

        return result

    def update_agent_credentials(
        self,
        source_username: str,
        source_password: str = None,
        source_key_path: str = None,
        source_port: int = 22,
        region: str = "cn-north-1",
        ak: str = None,
        sk: str = None,
        gost_ssh_port: int = None,
        sms_ops=None,
        source_ip: str = "",
        force: bool = False,
    ) -> Dict[str, Any]:
        """AK/SK 自适应更新 — 按 Agent 生命周期阶段安全处理

        状态机:
          NO_PACKAGE           → 调用 full_push (完整下发)
          RUNNING + token有效  → skip (不中断运行中的 Agent)
          RUNNING + token失效  → 检查任务 → 暂停/kill/重启/恢复
          RUNNING + 无任务     → kill + 用新AK/SK重启
          INSTALLED_*          → 用新AK/SK启动 (走 full_push 状态机)

        Args:
            sms_ops: SMSOps 实例 (用于查询任务状态和暂停/恢复)
            source_ip: 源端 IP (用于查找 SMS source 和 task)
            force: 强制更新 (即使 token 有效也重启)

        Returns:
            {"success", "action", "detail", "credential_updated"}
        """
        result = {
            "success": False,
            "action": "",
            "detail": "",
            "credential_updated": False,
        }

        new_fp = self._ak_fingerprint(ak)
        effective_port = gost_ssh_port if gost_ssh_port is not None else self.gost_ssh_port

        # 1. SSH 连接源端
        logger.info(f"[AK/SK自适应] 连接源端 {source_ip} via GOST:{effective_port}")
        ssh_conn = self.ssh.connect(
            host=self.proxy_ip,
            port=effective_port,
            username=source_username,
            password=source_password,
            key_path=source_key_path,
        )
        if not ssh_conn:
            result["error"] = "Failed to connect to source via GOST"
            return result

        try:
            # 2. 读取源端 AK 指纹
            old_fp = self._read_remote_ak_fingerprint(ssh_conn)
            credential_changed = (old_fp != new_fp) or force

            if not credential_changed:
                logger.info(f"[AK/SK自适应] 凭证未变更 (fingerprint={new_fp})，跳过")
                result["success"] = True
                result["action"] = "skip_no_change"
                result["detail"] = f"AK fingerprint unchanged ({new_fp})"
                return result

            logger.info(
                f"[AK/SK自适应] 凭证已变更 (old={old_fp}, new={new_fp})，开始自适应处理"
            )

            # 3. 检测 Agent 状态
            script_path = self._upload_state_script(ssh_conn)
            if not script_path:
                result["error"] = "Failed to upload state script"
                return result

            state_info = self._detect_agent_state(ssh_conn, script_path, region)
            state = state_info["state"]

            # 4. 按状态自适应处理

            # ── NO_PACKAGE: 直接 full_push ──
            if state == "NO_PACKAGE":
                logger.info("[AK/SK自适应] NO_PACKAGE → full_push")
                result["action"] = "full_deploy"
                push_r = self.full_push(
                    source_username=source_username,
                    source_password=source_password,
                    source_key_path=source_key_path,
                    source_port=source_port,
                    region=region, ak=ak, sk=sk,
                    gost_ssh_port=gost_ssh_port,
                )
                result["success"] = push_r["success"]
                result["credential_updated"] = push_r["success"]
                result["detail"] = "Deployed with new credentials"
                if push_r["success"]:
                    # 重新连接写入 fingerprint (full_push 已断开)
                    conn2 = self.ssh.connect(
                        host=self.proxy_ip, port=effective_port,
                        username=source_username, password=source_password,
                        key_path=source_key_path,
                    )
                    if conn2:
                        self._write_remote_ak_fingerprint(conn2, ak)
                        self.ssh.disconnect(conn2)
                return result

            # ── INSTALLED_* (未运行): 走 full_push 状态机启动 ──
            if state in ("INSTALLED_NOT_CONFIGURED", "INSTALLED_CONFIGURED"):
                logger.info(f"[AK/SK自适应] {state} → full_push (启动 with new AK/SK)")
                result["action"] = "restart_with_new_cred"
                push_r = self.full_push(
                    source_username=source_username,
                    source_password=source_password,
                    source_key_path=source_key_path,
                    source_port=source_port,
                    region=region, ak=ak, sk=sk,
                    gost_ssh_port=gost_ssh_port,
                )
                result["success"] = push_r["success"]
                result["credential_updated"] = push_r["success"]
                result["detail"] = f"Restarted with new credentials (was {state})"
                if push_r["success"]:
                    conn2 = self.ssh.connect(
                        host=self.proxy_ip, port=effective_port,
                        username=source_username, password=source_password,
                        key_path=source_key_path,
                    )
                    if conn2:
                        self._write_remote_ak_fingerprint(conn2, ak)
                        self.ssh.disconnect(conn2)
                return result

            # ── RUNNING: 核心自适应逻辑 ──
            if state == "RUNNING":
                # 4a. 检查 token 有效性
                token_info = self._check_agent_token_valid(ssh_conn, sms_ops, source_ip)
                token_valid = token_info["token_valid"]

                if token_valid and not force:
                    # token 仍有效 → 不中断运行中的 Agent
                    logger.info(
                        "[AK/SK自适应] RUNNING + token有效 → skip (不中断)"
                    )
                    result["success"] = True
                    result["action"] = "skip_token_valid"
                    result["detail"] = "Agent running with valid token, skip to avoid interruption"
                    result["credential_updated"] = False
                    # 仍写入新 fingerprint (下次检测用)
                    self._write_remote_ak_fingerprint(ssh_conn, ak)
                    return result

                # 4b. token 失效或 force=True → 需要重启 Agent
                # 检查是否有活跃 SMS 任务
                task_info = None
                task_id = ""
                if sms_ops and source_ip:
                    task_info = sms_ops.find_task_by_source_ip(source_ip)
                    if task_info:
                        task_id = task_info.get("id", "")

                if task_id:
                    # 有活跃任务 → 安全暂停 → 重启 Agent → 恢复
                    logger.warning(
                        f"[AK/SK自适应] RUNNING + token失效 + 有任务({task_id}) "
                        f"→ 暂停任务 → 重启Agent → 恢复任务"
                    )
                    result["action"] = "pause_restart_resume"

                    # 暂停任务
                    paused = sms_ops.pause_task(task_id)
                    if not paused:
                        logger.warning(f"任务暂停失败，继续重启 Agent (任务可能自行中断)")
                    else:
                        logger.info(f"任务 {task_id} 已暂停")

                    # 等待暂停生效
                    time.sleep(3)

                    # kill Agent
                    proc_pid = state_info.get("proc_pid", "")
                    kill_cmd = (
                        f"kill -9 {proc_pid} 2>/dev/null; "
                        f"pkill -9 -x linuxmain 2>/dev/null; "
                        f"pkill -9 -f 'SMS-Agent' 2>/dev/null; sleep 1"
                    )
                    self.ssh.execute(ssh_conn, kill_cmd, timeout=10)
                    logger.info("旧 Agent 进程已终止")

                    # 用新 AK/SK 重启
                    agent_dir = state_info.get("agent_dir", self.AGENT_INSTALL_PATH)
                    restart_ok = self._configure_and_start(
                        ssh_conn, script_path, agent_dir,
                        region, ak, sk, source_password or "",
                    )

                    if restart_ok:
                        self._write_remote_ak_fingerprint(ssh_conn, ak)
                        # 等待 Agent 重新注册
                        time.sleep(5)

                        # 恢复任务
                        resumed = sms_ops.resume_task(task_id)
                        if resumed:
                            logger.info(f"任务 {task_id} 已恢复")
                        else:
                            logger.warning(f"任务恢复失败，可能需要手动恢复")

                        result["success"] = True
                        result["credential_updated"] = True
                        result["detail"] = f"Paused task {task_id}, restarted agent, resumed task"
                    else:
                        result["error"] = "Agent restart failed after pausing task"
                        result["detail"] = "Agent restart failed, task still paused"
                        # 尝试恢复任务 (即使 Agent 重启失败)
                        sms_ops.resume_task(task_id)
                    return result

                else:
                    # 无活跃任务 → 直接 kill + 重启
                    logger.info(
                        "[AK/SK自适应] RUNNING + token失效 + 无任务 "
                        "→ kill + 用新AK/SK重启"
                    )
                    result["action"] = "kill_and_restart"

                    proc_pid = state_info.get("proc_pid", "")
                    kill_cmd = (
                        f"kill -9 {proc_pid} 2>/dev/null; "
                        f"pkill -9 -x linuxmain 2>/dev/null; "
                        f"pkill -9 -f 'SMS-Agent' 2>/dev/null; sleep 1"
                    )
                    self.ssh.execute(ssh_conn, kill_cmd, timeout=10)

                    agent_dir = state_info.get("agent_dir", self.AGENT_INSTALL_PATH)
                    restart_ok = self._configure_and_start(
                        ssh_conn, script_path, agent_dir,
                        region, ak, sk, source_password or "",
                    )

                    result["success"] = restart_ok
                    result["credential_updated"] = restart_ok
                    if restart_ok:
                        self._write_remote_ak_fingerprint(ssh_conn, ak)
                        result["detail"] = "Killed and restarted with new credentials"
                    else:
                        result["error"] = "Agent restart failed"
                        result["detail"] = "Kill succeeded but restart failed"
                    return result

            # 未知状态
            result["error"] = f"Unknown agent state: {state}"
            return result

        finally:
            self.ssh.disconnect(ssh_conn)
