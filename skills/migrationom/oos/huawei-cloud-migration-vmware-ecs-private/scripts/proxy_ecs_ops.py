#!/usr/bin/env python3
"""
proxy_ecs_ops.py — 代理 ECS 操作 (私网迁移核心)

代理 ECS 是私网迁移的中枢，部署在目标侧（自控资源），运行:
  1. squid: 控制流代理 (源端 SMS Agent → squid:3128 → 华为云 API:443)
  2. GOST:  管理通道 (操作端 → GOST:22 → 源端 SSH:22)
  3. GOST:  数据流转发 (源端 SMS Agent → GOST:8899/8900 → 目标 ECS:8899/8900)

端口规划 (代理 ECS):
  - 2222: sshd (改端口避免与 GOST:22 冲突)
  - 22:   GOST 管理通道 (转发到源端 SSH)
  - 3128: squid 控制流代理
  - 8899: GOST 数据流转发 (→ 目标 ECS:8899)
  - 8900: GOST 数据流转发 (→ 目标 ECS:8900)
"""

import time
import logging
from typing import Optional, Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

# rsync 配置路径
RSYNC_CONF_PATH = "/etc/rsyncd.conf"
RSYNC_LOG_PATH = "/var/log/rsyncd.log"


class ProxyEcsOps:
    """代理 ECS 全生命周期操作"""

    def __init__(self, ssh_client):
        """
        Args:
            ssh_client: SSH 客户端连接到代理 ECS (使用 2222 端口)
        """
        self.ssh = ssh_client
        self.gost_config_path = "/etc/gost"
        self.squid_config_path = "/etc/squid/squid.conf"

    def _exec(self, cmd: str, timeout: int = 30) -> Tuple[str, str, int]:
        # ssh_utils.SSHClient.exec_command already returns (out, err, exit_code)
        return self.ssh.exec_command(cmd, timeout=timeout)

    def _detect_os(self) -> str:
        out, _, _ = self._exec("cat /etc/os-release 2>/dev/null")
        out_lower = out.lower()
        if "centos" in out_lower or "rhel" in out_lower:
            return "centos"
        elif "ubuntu" in out_lower or "debian" in out_lower:
            return "debian"
        return "centos"

    # ──────────────────────────────────────────────────────────────
    #  Phase 1: 基础环境准备
    # ──────────────────────────────────────────────────────────────

    def change_sshd_port(self, new_port: int = 2222) -> bool:
        """修改 sshd 监听端口，为 GOST:22 让路。

        危险操作：修改后当前连接会断开，需用新端口重连。
        """
        logger.info(f"Changing sshd port to {new_port}")

        # 备份 sshd_config
        self._exec("cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak")

        # 检查是否已修改
        out, _, _ = self._exec(f"grep '^Port {new_port}' /etc/ssh/sshd_config")
        if out:
            logger.info(f"sshd already on port {new_port}")
            return True

        # 添加/修改 Port 行
        self._exec(f"sed -i 's/^#*Port .*/Port {new_port}/' /etc/ssh/sshd_config")
        # 如果没有 Port 行，添加一行
        self._exec(f"grep -q '^Port ' /etc/ssh/sshd_config || echo 'Port {new_port}' >> /etc/ssh/sshd_config")

        # SELinux 放行新端口 (CentOS)
        os_type = self._detect_os()
        if os_type == "centos":
            self._exec(f"semanage port -a -t ssh_port_t -p tcp {new_port} 2>/dev/null || true")

        # 防火墙放行
        self._exec(f"firewall-cmd --add-port={new_port}/tcp --permanent 2>/dev/null || true")
        self._exec("firewall-cmd --reload 2>/dev/null || true")
        self._exec(f"iptables -I INPUT -p tcp --dport {new_port} -j ACCEPT 2>/dev/null || true")

        # 重启 sshd (新端口生效)
        self._exec("systemctl restart sshd")
        time.sleep(2)

        logger.info(f"sshd port changed to {new_port} (reconnect required)")
        return True

    def tune_sshd_for_concurrency(self, max_concurrent: int = 100) -> bool:
        """调优 sshd 以支持高并发 SSH 连接 (100+ 台源端并发)。

        修改:
          - MaxStartups: 允许更多并发未认证连接 (默认 10:30:100 → 100:30:200)
          - MaxSessions: 允许更多并发会话 (默认 10 → 100)
          - ulimit -n: 提高文件描述符上限 (默认 1024 → 65535)

        Args:
            max_concurrent: 预期最大并发数

        Returns:
            是否成功
        """
        logger.info(f"Tuning sshd for {max_concurrent} concurrent connections")

        # MaxStartups: start:rate:full
        # start=100: 100 个并发未认证连接前不随机丢弃
        # rate=30: 超过 100 后 30% 概率丢弃
        # full=200: 200 个连接后全部丢弃
        max_startups = f"{max_concurrent}:30:{max_concurrent * 2}"
        max_sessions = max_concurrent

        # 修改 sshd_config
        for key, val in [("MaxStartups", max_startups), ("MaxSessions", str(max_sessions))]:
            # 检查是否已有该配置
            out, _, _ = self._exec(f"grep '^{key} ' /etc/ssh/sshd_config")
            if out:
                self._exec(f"sed -i 's/^{key} .*/{key} {val}/' /etc/ssh/sshd_config")
            else:
                self._exec(f"echo '{key} {val}' >> /etc/ssh/sshd_config")
            logger.info(f"  {key} = {val}")

        # 提高 ulimit (文件描述符上限)
        # 写入 /etc/security/limits.conf
        self._exec(
            "grep -q 'root.*soft.*nofile' /etc/security/limits.conf "
            "&& sed -i 's/root.*soft.*nofile.*/root soft nofile 65535/' /etc/security/limits.conf "
            "|| echo 'root soft nofile 65535' >> /etc/security/limits.conf"
        )
        self._exec(
            "grep -q 'root.*hard.*nofile' /etc/security/limits.conf "
            "&& sed -i 's/root.*hard.*nofile.*/root hard nofile 65535/' /etc/security/limits.conf "
            "|| echo 'root hard nofile 65535' >> /etc/security/limits.conf"
        )
        logger.info("  ulimit nofile = 65535 (root)")

        # 重启 sshd 使配置生效
        self._exec("systemctl restart sshd")
        time.sleep(1)

        logger.info("sshd tuned for high concurrency")
        return True

    def install_dependencies(self) -> bool:
        """安装代理 ECS 所需依赖: squid, gost"""
        os_type = self._detect_os()
        logger.info(f"Installing dependencies (OS={os_type})")

        # 安装 squid
        if os_type == "centos":
            self._exec("yum install -y epel-release 2>/dev/null || true", timeout=120)
            self._exec("yum install -y squid", timeout=120)
        else:
            self._exec("apt-get update -y && apt-get install -y squid", timeout=120)

        # 安装 gost (通过 gost_ops.install: obsutil下载→SFTP上传→远程解压)
        from gost_ops import GostOps
        gost = GostOps(self.ssh)
        if not gost.check_installed():
            logger.info("Installing gost via obsutil + SFTP...")
            # 代理ECS通常是amd64架构
            if not gost.install(arch="amd64"):
                logger.error("gost 安装失败 (obsutil下载或SFTP上传)")
                return False

        logger.info("Dependencies installed")
        return True

    # ──────────────────────────────────────────────────────────────
    #  Phase 2: squid 配置 (控制流代理)
    # ──────────────────────────────────────────────────────────────

    def configure_squid(self, source_ips: List[str], target_domains: List[str] = None) -> bool:
        """配置 squid 控制流代理。

        Args:
            source_ips: 允许使用代理的源端 IP 列表
            target_domains: 允许访问的目标域名 (华为云 API)
        """
        from squid_ops import SquidOps
        squid = SquidOps(self.ssh)

        if not squid.check_installed():
            if not squid.install():
                return False

        if not squid.deploy_config(source_ips, target_domains):
            return False

        if not squid.start():
            return False

        logger.info("squid configured and started")
        return True

    # ──────────────────────────────────────────────────────────────
    #  Phase 3: GOST 配置 (管理通道 + 数据流转发)
    # ──────────────────────────────────────────────────────────────

    def configure_gost_management(self, source_ip: str, source_ssh_port: int = 22,
                                  listen_port: int = 22) -> bool:
        """配置 GOST 管理通道: 代理ECS:listen_port → 源端:source_ssh_port

        用于通过代理 ECS SSH 到源端，执行 Agent 安装等操作。

        Args:
            source_ip: 源端内网 IP
            source_ssh_port: 源端 SSH 端口
            listen_port: 代理 ECS 监听端口 (默认 22)
        """
        from gost_ops import GostOps
        gost = GostOps(self.ssh)

        # 添加管理通道转发
        return gost.add_forward("management", listen_port, source_ip, source_ssh_port)

    def configure_gost_data_forward(self, target_ecs_ip: str,
                                     ports: List[int] = None) -> bool:
        """配置 GOST 数据流转发: 代理ECS:port → 目标ECS:port

        SMS Agent 数据流端口: 8899 (全量), 8900 (增量)

        Args:
            target_ecs_ip: 目标 ECS 内网 IP
            ports: 需要转发的端口列表
        """
        if ports is None:
            ports = [8899, 8900]

        from gost_ops import GostOps
        gost = GostOps(self.ssh)

        for port in ports:
            name = f"data_forward_{port}"
            if not gost.add_forward(name, port, target_ecs_ip, port):
                logger.warning(f"Failed to add GOST forward for port {port}")
                return False

        logger.info(f"GOST data forward configured: -> {target_ecs_ip} ports {ports}")
        return True

    def start_gost(self) -> bool:
        """启动 GOST 服务"""
        from gost_ops import GostOps
        gost = GostOps(self.ssh)
        return gost.start()

    # ──────────────────────────────────────────────────────────────
    #  Phase 3b: rsync 配置 (文件同步)
    # ──────────────────────────────────────────────────────────────

    def configure_rsync(self, source_ips: List[str] = None) -> bool:
        """配置 rsync 服务端，用于代理 ECS 上的文件同步。

        rsync 在私网迁移中的角色:
          - 传输 SMS Agent 安装包到代理 ECS
          - 传输配置文件、脚本等辅助文件
          - 源端可通过 rsync 从代理 ECS 拉取所需文件

        Args:
            source_ips: 允许访问 rsync 的源端 IP 列表 (None=允许代理 ECS 所在网段)

        Returns:
            配置是否成功
        """
        logger.info("Configuring rsync server on proxy ECS")

        # 安装 rsync
        os_type = self._detect_os()
        if os_type == "centos":
            self._exec("yum install -y rsync 2>/dev/null", timeout=120)
        else:
            self._exec("apt-get install -y rsync 2>/dev/null", timeout=120)

        # 生成 rsyncd.conf
        allow_from = ""
        if source_ips:
            allow_from = "hosts allow = " + ", ".join(source_ips)
        else:
            allow_from = "hosts allow = *"

        rsync_conf = f"""# rsyncd.conf — 私网迁移文件同步
# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}

uid = root
gid = root
use chroot = yes
max connections = 10
pid file = /var/run/rsyncd.pid
log file = {RSYNC_LOG_PATH}
{allow_from}

[migration]
    path = /data/migration
    comment = Migration file share
    read only = yes
    list = yes

[agent]
    path = /data/migration/agent
    comment = SMS Agent packages
    read only = yes
    list = yes

[config]
    path = /data/migration/config
    comment = Migration config files
    read only = no
    list = yes
"""
        write_cmd = f"cat > {RSYNC_CONF_PATH} << 'RSYNCEOF'\n{rsync_conf}\nRSYNCEOF"
        _, err, code = self._exec(write_cmd)
        if code != 0:
            logger.error(f"写入 rsyncd.conf 失败: {err}")
            return False

        # 创建共享目录
        self._exec("mkdir -p /data/migration/agent /data/migration/config")

        # 启动 rsync 守护进程
        self._exec("systemctl enable rsyncd 2>/dev/null || true")
        self._exec("systemctl restart rsyncd 2>/dev/null || rsync --daemon --config={}".format(RSYNC_CONF_PATH))
        time.sleep(1)

        # 验证
        out, _, _ = self._exec("ss -tlnp | grep ':873 '")
        if out:
            logger.info("rsync 服务已启动 (端口 873)")
            return True
        else:
            logger.warning("rsync 端口 873 未监听，可能需要手动启动")
            return True  # 非关键服务，不阻断流程

    # ──────────────────────────────────────────────────────────────
    #  Phase 3c: 动态 GOST 转发管理 (多源端/多目标 ECS)
    # ──────────────────────────────────────────────────────────────

    def add_source_forward(
        self,
        source_ip: str,
        source_ssh_port: int = 22,
        listen_port: int = None,
    ) -> int:
        """为新源端添加 GOST 管理通道转发。

        每台源端分配独立的 GOST 监听端口 (从 10022 开始递增)，
        避免多源端端口冲突。

        Args:
            source_ip: 源端内网 IP
            source_ssh_port: 源端 SSH 端口
            listen_port: 指定监听端口 (None=自动分配)

        Returns:
            分配的监听端口 (0 表示失败)
        """
        from gost_ops import GostOps
        gost = GostOps(self.ssh)

        # 自动分配端口
        if listen_port is None:
            existing_forwards = gost.list_forwards()
            used_ports = {r.get("local_port", 0) for r in existing_forwards}
            # 从 10022 开始找空闲端口
            listen_port = 10022
            while listen_port in used_ports:
                listen_port += 1

        rule_name = f"mgmt_{source_ip.replace('.', '_')}"

        if gost.add_forward(
            name=rule_name,
            local_port=listen_port,
            target_host=source_ip,
            target_port=source_ssh_port,
            description=f"管理通道: 代理ECS:{listen_port} → 源端{source_ip}:{source_ssh_port}",
        ):
            logger.info(f"Source forward added: {source_ip} via port {listen_port}")
            return listen_port
        else:
            logger.error(f"Failed to add source forward for {source_ip}")
            return 0

    def update_target_forward(
        self,
        target_ecs_ip: str,
        data_ports: List[int] = None,
        local_ports: List[int] = None,
    ) -> bool:
        """为目标 ECS 更新 GOST 数据流转发 (支持自定义本地端口)。

        当新的目标 ECS 创建后，调用此方法在代理 ECS 上添加/更新
        GOST 数据流转发规则，使 SMS Agent 数据流能到达目标 ECS。

        多目标并发: 每台目标 ECS 使用独立的本地端口 (local_ports),
        避免多台目标 ECS 争抢同一端口。

        Args:
            target_ecs_ip: 目标 ECS 内网 IP
            data_ports: 目标 ECS 数据端口列表 (默认 [8899, 8900])
            local_ports: 代理 ECS 本地监听端口列表 (默认同 data_ports)

        Returns:
            是否成功
        """
        if data_ports is None:
            data_ports = [8899, 8900]
        if local_ports is None:
            local_ports = data_ports

        from gost_ops import GostOps
        gost = GostOps(self.ssh)

        target_key = target_ecs_ip.replace(".", "_")
        success = True

        for local_port, target_port in zip(local_ports, data_ports):
            rule_name = f"data_{target_key}_{local_port}"
            if not gost.add_forward(
                name=rule_name,
                local_port=local_port,
                target_host=target_ecs_ip,
                target_port=target_port,
                description=f"数据流: 代理ECS:{local_port} → 目标ECS{target_ecs_ip}:{target_port}",
            ):
                logger.warning(f"Failed to add data forward {rule_name}")
                success = False

        if success:
            logger.info(f"Target forward updated: {target_ecs_ip} local={local_ports} -> remote={data_ports}")
        return success

    def batch_update_target_forwards(
        self,
        targets: List[Tuple[str, List[int], List[int]]],
    ) -> bool:
        """批量为多台目标 ECS 添加 GOST 数据流转发 (一次性部署 + 一次热重载)。

        解决 100 台并发时逐条 update_target_forward 导致的:
        - 100 次 GOST 重启 (每次重启杀掉所有现有连接)
        - config.json 读写竞态

        Args:
            targets: [(target_ecs_ip, data_ports, local_ports), ...]

        Returns:
            是否成功
        """
        if not targets:
            logger.warning("No targets for batch forward update")
            return True

        from gost_ops import GostOps
        gost = GostOps(self.ssh)

        # 收集所有转发规则
        forwards = []
        for target_ecs_ip, data_ports, local_ports in targets:
            if data_ports is None:
                data_ports = [8899, 8900]
            if local_ports is None:
                local_ports = data_ports
            target_key = target_ecs_ip.replace(".", "_")
            for local_port, target_port in zip(local_ports, data_ports):
                rule_name = f"data_{target_key}_{local_port}"
                forwards.append((
                    rule_name,
                    local_port,
                    target_ecs_ip,
                    target_port,
                    f"数据流: 代理ECS:{local_port} → 目标ECS{target_ecs_ip}:{target_port}",
                ))

        logger.info(f"Batch updating GOST data forwards for {len(targets)} targets ({len(forwards)} rules)")
        return gost.add_forwards_batch(forwards)

    def batch_create_ssh_forwards(
        self,
        source_hosts: List[Tuple[str, int, int]],
    ) -> bool:
        """批量为多台源端创建 GOST SSH 管理通道转发 (一次性部署 + 一次重启)。

        解决 100 台并发时:
        - deploy_all 只为首个源端创建 1 条 SSH 转发
        - 逐条 add_forward 导致 100 次 GOST 重启

        Args:
            source_hosts: [(source_ip, source_ssh_port, listen_port), ...]
                          listen_port 是代理 ECS 上的监听端口 (如 10022+idx)

        Returns:
            是否成功
        """
        if not source_hosts:
            logger.warning("No source hosts to create SSH forwards")
            return True

        from gost_ops import GostOps
        gost = GostOps(self.ssh)

        forwards = []
        for source_ip, source_ssh_port, listen_port in source_hosts:
            rule_name = f"mgmt_{source_ip.replace('.', '_')}"
            forwards.append((
                rule_name,
                listen_port,
                source_ip,
                source_ssh_port,
                f"管理通道: 代理ECS:{listen_port} → 源端{source_ip}:{source_ssh_port}",
            ))

        logger.info(f"Batch creating {len(forwards)} SSH forwards for source hosts")
        return gost.add_forwards_batch(forwards)

    # ──────────────────────────────────────────────────────────────
    #  Phase 4: 完整部署
    # ──────────────────────────────────────────────────────────────

    def deploy_all(
        self,
        source_ips: List[str],
        source_ssh_ip: str,
        target_ecs_ip: str,
        target_domains: List[str] = None,
        data_ports: List[int] = None,
        enable_rsync: bool = True,
    ) -> Dict[str, Any]:
        """完整部署代理 ECS: squid + GOST 管理通道 + GOST 数据流转发 + rsync

        Args:
            source_ips: 允许使用 squid 代理的源端 IP 列表
            source_ssh_ip: 源端 SSH IP (管理通道目标，首个源端)
            target_ecs_ip: 目标 ECS 内网 IP (数据流转发目标)
            target_domains: squid 允许的目标域名
            data_ports: GOST 数据流转发端口
            enable_rsync: 是否启用 rsync 文件同步服务

        Returns:
            部署结果 dict
        """
        result = {"success": False, "steps": [], "errors": []}

        # Step 0: sshd 调优 (支持高并发 SSH 连接)
        logger.info("Step 0: Tuning sshd for high concurrency")
        self.tune_sshd_for_concurrency(max_concurrent=100)
        result["steps"].append("sshd_tuned")

        # Step 1: 安装依赖
        logger.info("Step 1: Installing dependencies")
        if not self.install_dependencies():
            result["errors"].append("依赖安装失败")
            return result
        result["steps"].append("dependencies_installed")

        # Step 2: 配置 squid
        logger.info("Step 2: Configuring squid (control flow proxy)")
        if not self.configure_squid(source_ips, target_domains):
            result["errors"].append("squid 配置失败")
            return result
        result["steps"].append("squid_configured")

        # Step 3: 配置 GOST 管理通道
        logger.info("Step 3: Configuring GOST management channel")
        if not self.configure_gost_management(source_ssh_ip):
            result["errors"].append("GOST 管理通道配置失败")
            return result
        result["steps"].append("gost_management_configured")

        # Step 4: 配置 GOST 数据流转发
        logger.info("Step 4: Configuring GOST data forward")
        if not self.configure_gost_data_forward(target_ecs_ip, data_ports):
            result["errors"].append("GOST 数据流转发配置失败")
            return result
        result["steps"].append("gost_data_forward_configured")

        # Step 5: 启动 GOST
        logger.info("Step 5: Starting GOST")
        if not self.start_gost():
            result["errors"].append("GOST 启动失败")
            return result
        result["steps"].append("gost_started")

        # Step 6: 配置 rsync (可选)
        if enable_rsync:
            logger.info("Step 6: Configuring rsync file sync")
            if self.configure_rsync(source_ips):
                result["steps"].append("rsync_configured")
            else:
                logger.warning("rsync 配置失败，继续 (非关键服务)")
                result["steps"].append("rsync_skipped")

        result["success"] = True
        logger.info("Proxy ECS fully deployed")
        return result

    # ──────────────────────────────────────────────────────────────
    #  Phase 5: 验证
    # ──────────────────────────────────────────────────────────────

    def verify_all(self, source_ip: str, target_ecs_ip: str) -> Dict[str, bool]:
        """验证代理 ECS 所有服务正常"""
        results = {}

        # 验证 squid
        from squid_ops import SquidOps
        squid = SquidOps(self.ssh)
        results["squid"] = squid.is_running()

        # 验证 GOST
        from gost_ops import GostOps
        gost = GostOps(self.ssh)
        results["gost"] = gost.is_running()

        # 验证端口监听
        for port in [22, 3128, 8899, 8900]:
            out, _, _ = self._exec(f"ss -tlnp | grep ':{port} '")
            results[f"port_{port}"] = bool(out)

        # 验证管理通道连通性 (通过 GOST:22 SSH 到源端)
        out, _, code = self._exec(
            f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p 22 {source_ip} 'echo ok' 2>/dev/null",
            timeout=10
        )
        results["management_channel"] = (out.strip() == "ok")

        logger.info(f"Proxy ECS verification: {results}")
        return results

    # ──────────────────────────────────────────────────────────────
    #  Phase 6: 清理
    # ──────────────────────────────────────────────────────────────

    def cleanup(self) -> bool:
        """清理代理 ECS 上的所有服务"""
        logger.info("Cleaning up proxy ECS")

        from gost_ops import GostOps
        from squid_ops import SquidOps

        gost = GostOps(self.ssh)
        gost.stop()
        gost.cleanup()

        squid = SquidOps(self.ssh)
        squid.cleanup()

        # 恢复 sshd 端口
        self._exec("cp /etc/ssh/sshd_config.bak /etc/ssh/sshd_config 2>/dev/null || true")
        self._exec("systemctl restart sshd")

        return True

    def get_ssh_client_to_source(self, source_ip: str, username: str = "root",
                                  password: str = None, port: int = 22) -> Any:
        """通过 GOST 管理通道获取源端 SSH 客户端。

        代理 ECS 的 GOST:22 转发到源端:22，所以连接代理 ECS:22
        等同于连接源端:22。

        Returns:
            SSHClient 连接到源端 (通过 GOST 隧道)
        """
        from ssh_utils import SSHClient

        # 连接代理 ECS 的 22 端口 = GOST 转发到源端 22 端口
        client = SSHClient(
            host=self.ssh.host,  # 代理 ECS IP
            port=22,             # GOST 管理通道端口
            username=username,
            password=password,
        )
        client.connect()
        logger.info(f"SSH to source {source_ip} via GOST tunnel (proxy:{22} -> source:{port})")
        return client
