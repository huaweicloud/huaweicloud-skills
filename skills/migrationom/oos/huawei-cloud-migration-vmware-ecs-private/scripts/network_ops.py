#!/usr/bin/env python3
"""
network_ops.py — 网络操作

封装网络相关操作:
  - VPN 连通性检查
  - 端口连通性检查
  - 路由检查
  - 代理连通性验证
  - DNS 解析
  - 网络延迟测试
"""

import socket
import subprocess
import time
import logging
from typing import Optional, Dict, List, Tuple, Any

logger = logging.getLogger(__name__)


class NetworkOps:
    """网络操作"""

    # ──────────────────────────────────────────────────────────────
    #  TCP 端口检查
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def check_port(ip: str, port: int, timeout: float = 5.0) -> bool:
        """检查 TCP 端口是否可达

        Args:
            ip: 目标 IP
            port: 目标端口
            timeout: 超时秒数

        Returns:
            端口是否可达
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            if result == 0:
                logger.debug(f"Port {ip}:{port} is reachable")
                return True
            else:
                logger.debug(f"Port {ip}:{port} unreachable (errno={result})")
                return False
        except Exception as e:
            logger.debug(f"Port check failed for {ip}:{port}: {e}")
            return False

    @staticmethod
    def check_ports(ip: str, ports: List[int], timeout: float = 5.0) -> Dict[int, bool]:
        """批量检查端口

        Returns:
            {port: reachable}
        """
        results = {}
        for port in ports:
            results[port] = NetworkOps.check_port(ip, port, timeout)
        return results

    @staticmethod
    def wait_port_open(ip: str, port: int, timeout: int = 120,
                       interval: int = 5) -> bool:
        """等待端口开放

        Args:
            ip: 目标 IP
            port: 目标端口
            timeout: 总超时
            interval: 轮询间隔

        Returns:
            端口是否最终开放
        """
        start = time.time()
        while time.time() - start < timeout:
            if NetworkOps.check_port(ip, port, timeout=3.0):
                logger.info(f"Port {ip}:{port} is open")
                return True
            time.sleep(interval)
        logger.warning(f"Port {ip}:{port} not open after {timeout}s")
        return False

    # ──────────────────────────────────────────────────────────────
    #  Ping / 延迟
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def ping(ip: str, count: int = 4, timeout: int = 10) -> Tuple[bool, float]:
        """Ping 目标 IP

        Returns:
            (reachable, avg_latency_ms)
        """
        try:
            cmd = ["ping", "-c", str(count), "-W", str(timeout), ip]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout + 5
            )
            if result.returncode == 0:
                # 解析平均延迟
                avg = 0.0
                for line in result.stdout.splitlines():
                    if "avg" in line or "rtt" in line:
                        parts = line.split("=")
                        if len(parts) >= 2:
                            stats = parts[-1].split("/")
                            if len(stats) >= 2:
                                avg = float(stats[1])
                logger.debug(f"Ping {ip}: reachable, avg={avg}ms")
                return True, avg
            else:
                logger.debug(f"Ping {ip}: unreachable")
                return False, 0.0
        except Exception as e:
            logger.debug(f"Ping failed for {ip}: {e}")
            return False, 0.0

    @staticmethod
    def check_latency(ip: str, threshold_ms: float = 100.0) -> bool:
        """检查延迟是否在阈值内"""
        reachable, avg = NetworkOps.ping(ip)
        if not reachable:
            return False
        if avg > threshold_ms:
            logger.warning(f"Latency to {ip}: {avg}ms > {threshold_ms}ms threshold")
            return False
        return True

    # ──────────────────────────────────────────────────────────────
    #  VPN 连通性
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def check_vpn_connectivity(
        source_ip: str,
        target_ip: str,
        required_ports: List[int] = None,
    ) -> Dict[str, Any]:
        """检查 VPN 连通性

        Args:
            source_ip: 源端 IP (从本机视角测试到 target)
            target_ip: 目标 IP
            required_ports: 需要检查的端口列表

        Returns:
            {"ping_ok": bool, "latency_ms": float, "ports": {port: bool}, "all_ok": bool}
        """
        # Ping 检查
        ping_ok, latency = NetworkOps.ping(target_ip)

        # 端口检查
        port_results = {}
        if required_ports:
            port_results = NetworkOps.check_ports(target_ip, required_ports)

        all_ok = ping_ok
        if required_ports:
            all_ok = all_ok and all(port_results.values())

        result = {
            "ping_ok": ping_ok,
            "latency_ms": latency,
            "ports": port_results,
            "all_ok": all_ok,
        }

        if all_ok:
            logger.info(f"VPN connectivity OK: {source_ip} -> {target_ip} (latency={latency}ms)")
        else:
            logger.warning(f"VPN connectivity issue: {source_ip} -> {target_ip}: {result}")

        return result

    # ──────────────────────────────────────────────────────────────
    #  代理连通性
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def check_squid_proxy(proxy_ip: str, proxy_port: int = 3128,
                          test_url: str = "https://www.myhuaweicloud.com",
                          timeout: int = 10) -> bool:
        """检查 squid 代理是否可用

        Args:
            proxy_ip: 代理 ECS IP
            proxy_port: 代理端口
            test_url: 测试 URL
            timeout: 超时

        Returns:
            代理是否可用
        """
        # 先检查端口
        if not NetworkOps.check_port(proxy_ip, proxy_port, timeout=5):
            logger.warning(f"Squid proxy port {proxy_ip}:{proxy_port} not reachable")
            return False

        # 尝试通过代理访问 URL
        try:
            cmd = [
                "curl", "-x", f"http://{proxy_ip}:{proxy_port}",
                "-o", "/dev/null", "-s", "-w", "%{http_code}",
                "--connect-timeout", str(timeout),
                test_url,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
            http_code = result.stdout.strip()
            if http_code in ("200", "301", "302", "304"):
                logger.info(f"Squid proxy OK: {proxy_ip}:{proxy_port} -> {http_code}")
                return True
            else:
                logger.warning(f"Squid proxy test failed: HTTP {http_code}")
                return False
        except Exception as e:
            logger.warning(f"Squid proxy check failed: {e}")
            return False

    @staticmethod
    def check_gost_forwarding(
        proxy_ip: str,
        gost_port: int,
        target_ip: str,
        target_port: int,
        timeout: int = 10,
    ) -> bool:
        """检查 GOST 端口转发是否正常

        通过连接 proxy_ip:gost_port 验证能否到达 target_ip:target_port

        Args:
            proxy_ip: 代理 ECS IP
            gost_port: GOST 监听端口
            target_ip: 最终目标 IP (用于日志)
            target_port: 最终目标端口 (用于日志)
            timeout: 超时

        Returns:
            转发是否正常
        """
        if not NetworkOps.check_port(proxy_ip, gost_port, timeout=timeout):
            logger.warning(f"GOST forwarding failed: {proxy_ip}:{gost_port} -> {target_ip}:{target_port}")
            return False

        logger.info(f"GOST forwarding OK: {proxy_ip}:{gost_port} -> {target_ip}:{target_port}")
        return True

    # ──────────────────────────────────────────────────────────────
    #  路由检查
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def check_route(target_ip: str) -> Optional[str]:
        """检查到目标 IP 的路由

        Returns:
            使用的网卡名 (或 None)
        """
        try:
            cmd = ["ip", "route", "get", target_ip]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                output = result.stdout.strip()
                # 解析 "dev <iface>"
                for part in output.split():
                    if part == "dev":
                        idx = output.split().index(part)
                        if idx + 1 < len(output.split()):
                            iface = output.split()[idx + 1]
                            logger.debug(f"Route to {target_ip} via {iface}")
                            return iface
                logger.debug(f"Route to {target_ip}: {output}")
                return "default"
            return None
        except Exception as e:
            logger.debug(f"Route check failed: {e}")
            return None

    # ──────────────────────────────────────────────────────────────
    #  DNS 解析
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def resolve_dns(hostname: str) -> Optional[str]:
        """DNS 解析"""
        try:
            ip = socket.gethostbyname(hostname)
            logger.debug(f"DNS: {hostname} -> {ip}")
            return ip
        except Exception as e:
            logger.debug(f"DNS resolution failed for {hostname}: {e}")
            return None

    # ──────────────────────────────────────────────────────────────
    #  综合网络诊断
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def full_diagnosis(
        source_ip: str,
        proxy_ip: str,
        target_ip: str,
        gost_ports: Dict[int, int] = None,
        squid_port: int = 3128,
    ) -> Dict[str, Any]:
        """全面网络诊断

        Args:
            source_ip: 源端 IP
            proxy_ip: 代理 ECS IP
            target_ip: 目标 ECS IP
            gost_ports: {gost_listen_port: target_port}
            squid_port: squid 代理端口

        Returns:
            诊断结果
        """
        diagnosis = {
            "source_to_proxy": {},
            "proxy_to_target": {},
            "squid": {},
            "gost": {},
            "overall_ok": True,
        }

        # 1. 源端 -> 代理 ECS
        diagnosis["source_to_proxy"] = NetworkOps.check_vpn_connectivity(
            source_ip, proxy_ip, [2222, squid_port] + list((gost_ports or {}).keys())
        )

        # 2. 代理 ECS -> 目标 ECS
        diagnosis["proxy_to_target"] = NetworkOps.check_vpn_connectivity(
            proxy_ip, target_ip, [22, 8899, 8900]
        )

        # 3. squid 代理
        diagnosis["squid"]["ok"] = NetworkOps.check_squid_proxy(proxy_ip, squid_port)

        # 4. GOST 转发
        if gost_ports:
            for listen_port, target_port in gost_ports.items():
                diagnosis["gost"][f"{listen_port}->{target_port}"] = (
                    NetworkOps.check_gost_forwarding(proxy_ip, listen_port, target_ip, target_port)
                )

        # 综合判断
        diagnosis["overall_ok"] = (
            diagnosis["source_to_proxy"]["all_ok"]
            and diagnosis["proxy_to_target"]["all_ok"]
            and diagnosis["squid"]["ok"]
            and all(diagnosis["gost"].values())
        )

        if diagnosis["overall_ok"]:
            logger.info("Network diagnosis: ALL OK")
        else:
            logger.warning(f"Network diagnosis: issues found - {diagnosis}")

        return diagnosis


class CloudNetworkOps:
    """云网络资源操作 — VPC/子网/安全组自动创建"""

    # 代理 ECS 所需端口规则 (squid + GOST 管理 + GOST 数据 + rsync)
    PROXY_PORTS = [
        # (protocol, port_range, direction, description)
        ("TCP", "2222", "ingress", "代理 ECS sshd 管理端口"),
        ("TCP", "3128", "ingress", "squid 控制流代理"),
        ("TCP", "873", "ingress", "rsync 文件同步"),
        ("TCP", "10022-10080", "ingress", "GOST 管理通道 (多源端动态分配)"),
    ]

    # 目标 ECS 所需端口规则 (仅 SMS 数据传输 + SSH)
    TARGET_PORTS = [
        # (protocol, port_range, direction, description)
        ("TCP", "22", "ingress", "SSH 管理"),
        ("TCP", "8899", "ingress", "SMS 数据传输 (全量)"),
        ("TCP", "8900", "ingress", "SMS 数据传输 (增量)"),
    ]

    # 迁移所需端口规则 (兼容旧代码: 代理 + 目标合并)
    MIGRATION_PORTS = PROXY_PORTS + TARGET_PORTS + [
        ("TCP", "443", "ingress", "HTTPS API (SMS 控制流)"),
        ("TCP", "8080", "ingress", "GOST HTTP 代理"),
    ]

    def __init__(self, hcloud):
        """
        Args:
            hcloud: HcloudCLI 实例
        """
        self.hcloud = hcloud

    # ──────────────────────────────────────────────────────────────
    #  VPC 管理
    # ──────────────────────────────────────────────────────────────

    def find_vpc_by_name(self, name: str) -> Optional[Dict]:
        """通过名称查找 VPC"""
        vpcs = self.hcloud.vpc_list()
        if not vpcs or not isinstance(vpcs, dict):
            return None
        vpc_list = vpcs.get("vpcs", [])
        for vpc in vpc_list:
            if name in vpc.get("name", ""):
                logger.info(f"Found VPC: id={vpc.get('id')}, name={vpc.get('name')}")
                return vpc
        return None

    def ensure_vpc(self, name: str, cidr: str = "192.168.0.0/16") -> Optional[Dict]:
        """确保 VPC 存在，不存在则创建

        Args:
            name: VPC 名称
            cidr: VPC CIDR

        Returns:
            VPC 信息 (含 id, name)
        """
        # 先查找
        existing = self.find_vpc_by_name(name)
        if existing:
            logger.info(f"VPC already exists: {existing.get('id')}")
            return existing

        # 创建
        logger.info(f"Creating VPC: name={name}, cidr={cidr}")
        result = self.hcloud.vpc_create(name=name, cidr=cidr)
        if result and isinstance(result, dict):
            vpc = result.get("vpc", result)
            logger.info(f"VPC created: id={vpc.get('id')}")
            return vpc

        logger.error(f"Failed to create VPC: {name}")
        return None

    # ──────────────────────────────────────────────────────────────
    #  子网管理
    # ──────────────────────────────────────────────────────────────

    def find_subnet_by_name(self, vpc_id: str, name: str) -> Optional[Dict]:
        """通过名称查找子网"""
        subnets = self.hcloud.subnet_list(vpc_id=vpc_id)
        if not subnets or not isinstance(subnets, dict):
            return None
        subnet_list = subnets.get("subnets", [])
        for sn in subnet_list:
            if name in sn.get("name", ""):
                logger.info(f"Found subnet: id={sn.get('id')}, name={sn.get('name')}")
                return sn
        return None

    def ensure_subnet(
        self,
        vpc_id: str,
        name: str,
        cidr: str = "192.168.0.0/24",
        gateway_ip: str = "192.168.0.1",
    ) -> Optional[Dict]:
        """确保子网存在，不存在则创建

        Args:
            vpc_id: VPC ID
            name: 子网名称
            cidr: 子网 CIDR
            gateway_ip: 网关 IP

        Returns:
            子网信息 (含 id, name)
        """
        # 先查找
        existing = self.find_subnet_by_name(vpc_id, name)
        if existing:
            logger.info(f"Subnet already exists: {existing.get('id')}")
            return existing

        # 创建
        logger.info(f"Creating subnet: name={name}, cidr={cidr}, vpc={vpc_id}")
        result = self.hcloud.subnet_create(
            vpc_id=vpc_id,
            name=name,
            cidr=cidr,
            gateway_ip=gateway_ip,
        )
        if result and isinstance(result, dict):
            subnet = result.get("subnet", result)
            logger.info(f"Subnet created: id={subnet.get('id')}")
            return subnet

        logger.error(f"Failed to create subnet: {name}")
        return None

    # ──────────────────────────────────────────────────────────────
    #  安全组管理
    # ──────────────────────────────────────────────────────────────

    def find_sg_by_name(self, name: str) -> Optional[Dict]:
        """通过名称查找安全组"""
        sgs = self.hcloud.sg_list()
        if not sgs or not isinstance(sgs, dict):
            return None
        sg_list = sgs.get("security_groups", [])
        for sg in sg_list:
            if name in sg.get("name", ""):
                logger.info(f"Found SG: id={sg.get('id')}, name={sg.get('name')}")
                return sg
        return None

    def _get_existing_sg_rules(self, sg_id: str) -> set:
        """查询安全组已有规则，返回去重用的 key 集合

        Returns:
            set of (protocol, port_range, direction, remote_ip)
        """
        rules_set = set()
        try:
            result = self.hcloud._exec([
                "VPC", "ShowSecurityGroupRules",
                f"--security_group_id={sg_id}",
            ])
            if not result or not result.get("success"):
                return rules_set
            data = result.get("data", {})
            rule_list = data.get("security_group_rules", [])
            for rule in rule_list:
                proto = rule.get("protocol", "").lower()
                port_min = rule.get("port_range_min", "")
                port_max = rule.get("port_range_max", "")
                if port_min and port_max:
                    port_range = f"{port_min}-{port_max}" if port_min != port_max else str(port_min)
                else:
                    port_range = ""
                direction = rule.get("direction", "")
                remote_ip = rule.get("remote_ip_prefix", "")
                rules_set.add((proto, port_range, direction, remote_ip))
            logger.info(f"SG {sg_id} has {len(rules_set)} existing rules")
        except Exception as e:
            logger.warning(f"Could not query existing SG rules for {sg_id}: {e}")
        return rules_set

    def ensure_security_group(
        self,
        name: str,
        vpc_id: str,
        source_cidr: str = None,
        extra_ports: List[Tuple[str, str, str]] = None,
    ) -> Optional[Dict]:
        """确保安全组存在并配置迁移规则

        安全约束: source_cidr 禁止 0.0.0.0/0，必须指定具体网段或 IP 地址。

        Args:
            name: 安全组名称
            vpc_id: VPC ID
            source_cidr: 源端 CIDR (必须指定具体网段或 IP，禁止 0.0.0.0/0)
            extra_ports: 额外端口规则 [(protocol, port_range, description), ...]

        Returns:
            安全组信息 (含 id)
        """
        # 安全约束: 禁止 0.0.0.0/0
        if not source_cidr:
            logger.error(
                "安全约束: source_cidr 不能为空，必须指定具体网段或 IP (禁止 0.0.0.0/0)。"
                "例如: 192.168.0.0/24 或 10.0.0.5/32"
            )
            return None
        if source_cidr.strip().lower() in ("0.0.0.0/0", "::/0"):
            logger.error(
                f"安全约束违规: source_cidr={source_cidr} 被禁止。"
                "0.0.0.0/0 表示对所有 IP 开放，属于高危操作。"
                "请指定具体的源端 CIDR 网段或 IP 地址 (如 192.168.0.0/24)。"
            )
            return None

        # 先查找
        existing = self.find_sg_by_name(name)
        if existing:
            sg_id = existing.get("id")
            logger.info(f"SG already exists: {sg_id}, ensuring rules...")
        else:
            # 创建
            logger.info(f"Creating SG: name={name}, vpc={vpc_id}")
            result = self.hcloud.sg_create(name=name, vpc_id=vpc_id)
            if not result or not isinstance(result, dict):
                logger.error(f"Failed to create SG: {name}")
                return None
            sg = result.get("security_group", result)
            sg_id = sg.get("id")
            if not sg_id:
                logger.error("No SG ID in creation result")
                return None
            existing = sg
            logger.info(f"SG created: id={sg_id}")

        # 添加迁移所需规则 (去重: 跳过已存在的规则)
        all_ports = list(self.MIGRATION_PORTS)
        if extra_ports:
            for proto, port_range, desc in extra_ports:
                all_ports.append((proto, port_range, "ingress", desc))

        # 查询已有规则用于去重
        existing_rules = self._get_existing_sg_rules(sg_id)

        for proto, port_range, direction, desc in all_ports:
            # 去重检查
            rule_key = (proto.lower(), port_range, direction, source_cidr)
            if rule_key in existing_rules:
                logger.info(f"SG rule already exists, skipping: {proto}/{port_range} ({desc})")
                continue

            success = self.hcloud.sg_create_rule(
                sg_id=sg_id,
                protocol=proto,
                port_range=port_range,
                remote_ip=source_cidr,
                direction=direction,
                description=desc,
            )
            if not success:
                logger.warning(f"Failed to add SG rule: {proto}/{port_range} ({desc})")
                # 继续添加其他规则
            else:
                existing_rules.add(rule_key)

        # 添加出方向规则 (全部放通 — egress 0.0.0.0/0 是安全的)
        egress_key = ("any", "1-65535", "egress", "0.0.0.0/0")
        if egress_key not in existing_rules:
            self.hcloud.sg_create_rule(
                sg_id=sg_id,
                protocol="any",
                port_range="1-65535",
                remote_ip="0.0.0.0/0",
                direction="egress",
                description="全部出方向放通",
            )

        logger.info(f"SG rules ensured for {sg_id}")
        return existing

    def ensure_proxy_security_group(
        self,
        name: str,
        vpc_id: str,
        source_cidr: str,
    ) -> Optional[Dict]:
        """创建代理 ECS 专用安全组 (仅放通代理服务端口)。

        代理 ECS 安全组只开放: sshd(2222), squid(3128), rsync(873),
        GOST 管理通道(10022-10080)。

        安全约束: source_cidr 禁止 0.0.0.0/0。

        Args:
            name: 安全组名称
            vpc_id: VPC ID
            source_cidr: 源端 CIDR (必须具体网段)

        Returns:
            安全组信息
        """
        return self.ensure_security_group(
            name=name,
            vpc_id=vpc_id,
            source_cidr=source_cidr,
            extra_ports=None,
        )

    def ensure_target_security_group(
        self,
        name: str,
        vpc_id: str,
        source_cidr: str,
    ) -> Optional[Dict]:
        """创建目标 ECS 专用安全组 (仅放通迁移数据端口)。

        目标 ECS 安全组只开放: SSH(22), SMS 数据(8899/8900)，
        且仅对 source_cidr 开放，禁止 0.0.0.0/0。

        Args:
            name: 安全组名称
            vpc_id: VPC ID
            source_cidr: 源端 CIDR (必须具体网段)

        Returns:
            安全组信息
        """
        # 安全约束检查
        if not source_cidr or source_cidr.strip().lower() in ("0.0.0.0/0", "::/0"):
            logger.error(
                f"安全约束违规: 目标 ECS 安全组禁止 0.0.0.0/0。"
                f"请指定具体源端 CIDR (如 192.168.0.0/24)。"
            )
            return None

        # 先查找或创建 SG
        existing = self.find_sg_by_name(name)
        if existing:
            sg_id = existing.get("id")
            logger.info(f"Target SG already exists: {sg_id}, ensuring rules...")
        else:
            logger.info(f"Creating target SG: name={name}, vpc={vpc_id}")
            result = self.hcloud.sg_create(name=name, vpc_id=vpc_id)
            if not result or not isinstance(result, dict):
                logger.error(f"Failed to create target SG: {name}")
                return None
            sg = result.get("security_group", result)
            sg_id = sg.get("id")
            existing = sg
            logger.info(f"Target SG created: id={sg_id}")

        # 只添加目标 ECS 所需端口 (TARGET_PORTS)
        existing_rules = self._get_existing_sg_rules(sg_id)

        for proto, port_range, direction, desc in self.TARGET_PORTS:
            rule_key = (proto.lower(), port_range, direction, source_cidr)
            if rule_key in existing_rules:
                logger.info(f"Target SG rule already exists: {proto}/{port_range} ({desc})")
                continue
            self.hcloud.sg_create_rule(
                sg_id=sg_id,
                protocol=proto,
                port_range=port_range,
                remote_ip=source_cidr,
                direction=direction,
                description=desc,
            )

        # 出方向全部放通 (egress 0.0.0.0/0 是安全的)
        egress_key = ("any", "1-65535", "egress", "0.0.0.0/0")
        if egress_key not in existing_rules:
            self.hcloud.sg_create_rule(
                sg_id=sg_id,
                protocol="any",
                port_range="1-65535",
                remote_ip="0.0.0.0/0",
                direction="egress",
                description="全部出方向放通",
            )

        logger.info(f"Target SG rules ensured for {sg_id}")
        return existing

    @staticmethod
    def compute_source_cidr(source_ips: List[str]) -> str:
        """从源端 IP 列表计算汇总 CIDR 网段。

        将多个源端 IP 归并到最小的 CIDR 网段。
        例如: 192.168.0.186, 192.168.0.59 → 192.168.0.0/24

        Args:
            source_ips: 源端 IP 地址列表

        Returns:
            汇总 CIDR 字符串 (如 "192.168.0.0/24")
            如果无法计算则返回空字符串 (调用方必须处理)
        """
        if not source_ips:
            return ""

        try:
            import ipaddress

            ips = []
            for ip_str in source_ips:
                ip_str = ip_str.strip()
                if not ip_str:
                    continue
                try:
                    ips.append(ipaddress.ip_address(ip_str))
                except ValueError:
                    # 可能已经是 CIDR 格式
                    try:
                        net = ipaddress.ip_network(ip_str, strict=False)
                        ips.append(net.network_address)
                    except ValueError:
                        logger.warning(f"Invalid IP/CIDR: {ip_str}, skipping")
                        continue

            if not ips:
                return ""

            # 找到包含所有 IP 的最小 CIDR
            min_ip = min(ips)
            max_ip = max(ips)

            # 逐级扩大网段直到包含所有 IP
            for prefix in range(32, 0, -1):
                try:
                    net = ipaddress.ip_network(f"{min_ip}/{prefix}", strict=False)
                    if max_ip in net:
                        cidr = str(net)
                        logger.info(f"Computed source CIDR: {cidr} (from {len(ips)} IPs)")
                        return cidr
                except ValueError:
                    continue

            # 回退到 /16
            net = ipaddress.ip_network(f"{min_ip}/16", strict=False)
            return str(net)

        except ImportError:
            # ipaddress 不可用，用简单方法
            if len(source_ips) == 1:
                ip = source_ips[0].strip()
                parts = ip.split(".")
                if len(parts) == 4:
                    return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
            # 多个 IP: 取第一个 IP 的 /24 网段
            ip = source_ips[0].strip()
            parts = ip.split(".")
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
            return ""

    # ──────────────────────────────────────────────────────────────
    #  综合网络资源创建
    # ──────────────────────────────────────────────────────────────

    def ensure_migration_network(
        self,
        vpc_name: str = "migration-vpc",
        vpc_cidr: str = "192.168.0.0/16",
        subnet_name: str = "migration-subnet",
        subnet_cidr: str = "192.168.0.0/24",
        subnet_gateway: str = "192.168.0.1",
        sg_name: str = "migration-sg",
        source_cidr: str = None,
        extra_ports: List[Tuple[str, str, str]] = None,
    ) -> Optional[Dict[str, str]]:
        """一键创建迁移所需网络资源

        创建 VPC + 子网 + 安全组(含规则)

        Returns:
            {"vpc_id":, "subnet_id":, "sg_id":} 或 None
        """
        logger.info("Ensuring migration network resources...")

        # 1. VPC
        vpc = self.ensure_vpc(vpc_name, vpc_cidr)
        if not vpc:
            return None
        vpc_id = vpc.get("id")

        # 2. 子网
        subnet = self.ensure_subnet(vpc_id, subnet_name, subnet_cidr, subnet_gateway)
        if not subnet:
            return None
        subnet_id = subnet.get("id")

        # 3. 安全组
        sg = self.ensure_security_group(sg_name, vpc_id, source_cidr, extra_ports)
        if not sg:
            return None
        sg_id = sg.get("id")

        result = {"vpc_id": vpc_id, "subnet_id": subnet_id, "sg_id": sg_id}
        logger.info(f"Migration network ready: {result}")
        return result

    # ──────────────────────────────────────────────────────────────
    #  清理
    # ──────────────────────────────────────────────────────────────

    def cleanup_network(self, vpc_id: str, sg_id: str = None) -> bool:
        """清理网络资源

        Args:
            vpc_id: VPC ID
            sg_id: 安全组 ID (可选)

        Returns:
            是否成功
        """
        success = True

        if sg_id:
            logger.info(f"Deleting SG: {sg_id}")
            if not self.hcloud.sg_delete(sg_id):
                logger.warning(f"Failed to delete SG: {sg_id}")
                success = False

        logger.info(f"Deleting VPC: {vpc_id}")
        if not self.hcloud.vpc_delete(vpc_id):
            logger.warning(f"Failed to delete VPC: {vpc_id}")
            success = False

        return success
