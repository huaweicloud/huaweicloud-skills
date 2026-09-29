#!/usr/bin/env python3
"""
ecs_ops.py — 华为云 ECS 操作

封装 ECS 相关操作:
  - ECS 创建/查询/启动/停止/删除
  - 安全组规则管理
  - 弹性公网 IP 绑定/解绑
  - 磁盘挂载
  - ECS 状态等待
"""

import time
import logging
import threading
import re
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

try:
    from ownership_utils import OwnershipManager
except ImportError:
    OwnershipManager = None


# ──────────────────────────────────────────────────────────────
# ECS 命名规则校验
# ──────────────────────────────────────────────────────────────

# 允许的字符: 中文字符、英文字母、数字、下划线、短横线、点
_ECS_NAME_PATTERN = re.compile(r'^[\u4e00-\u9fa5a-zA-Z0-9_\-.]+$')


def validate_ecs_name(name: str) -> str:
    """校验目标端 ECS 主机名是否符合命名规则

    规则:
        - 只能由中文字符、英文字母、数字及 _ - . 组成
        - 长度: 英文字符 [1-128], 中文字符 [1-64]
        - 不能为空

    Args:
        name: 待校验的 ECS 主机名

    Returns:
        校验通过的名字 (str)

    Raises:
        ValueError: 名字不符合规则
    """
    if not name or not name.strip():
        raise ValueError("ECS 名称不能为空")

    name = name.strip()

    # 字符校验
    if not _ECS_NAME_PATTERN.match(name):
        invalid_chars = set(re.findall(r'[^\u4e00-\u9fa5a-zA-Z0-9_\-.]', name))
        raise ValueError(
            f"ECS 名称 '{name}' 包含非法字符: {invalid_chars}。"
            f"只允许中文字符、英文字母、数字及 _ - . "
        )

    # 长度校验: 含中文字符时限制 64, 纯英文/数字时限制 128
    has_chinese = bool(re.search(r'[\u4e00-\u9fa5]', name))
    max_len = 64 if has_chinese else 128
    if len(name) > max_len:
        raise ValueError(
            f"ECS 名称 '{name}' 长度 {len(name)} 超过限制 {max_len} "
            f"({'含中文字符' if has_chinese else '纯英文/数字'})"
        )

    return name


class ECSOps:
    """华为云 ECS 操作"""

    def __init__(self, hcloud):
        """
        Args:
            hcloud: HcloudCLI 实例
        """
        self.hcloud = hcloud

    # ──────────────────────────────────────────────────────────────
    #  ECS 查询
    # ──────────────────────────────────────────────────────────────

    def find_by_name(self, name: str) -> Optional[Dict]:
        """通过名称查找 ECS"""
        servers = self.hcloud.ecs_list_servers()
        server_list = servers.get("servers", []) if isinstance(servers, dict) else []

        for srv in server_list:
            if name in srv.get("name", ""):
                logger.info(f"Found ECS: id={srv.get('id')}, name={srv.get('name')}")
                return srv
        return None

    def find_by_id(self, server_id: str) -> Optional[Dict]:
        """通过 ID 查找 ECS"""
        info = self.hcloud.ecs_show_server(server_id)
        if info and isinstance(info, dict):
            return info
        return None

    def get_state(self, server_id: str) -> str:
        """获取 ECS 状态"""
        info = self.find_by_id(server_id)
        if info:
            server = info.get("server", info)
            return server.get("status", "").upper()
        return "UNKNOWN"

    def get_private_ip(self, server_id: str) -> Optional[str]:
        """获取 ECS 主网卡私有 IP"""
        info = self.find_by_id(server_id)
        if not info:
            return None
        server = info.get("server", info)
        addresses = server.get("addresses", {})
        for net_name, addrs in addresses.items():
            for addr in addrs:
                if addr.get("OS-EXT-IPS:type") == "fixed":
                    return addr.get("addr")
        return None

    def get_public_ip(self, server_id: str) -> Optional[str]:
        """获取 ECS 弹性公网 IP"""
        info = self.find_by_id(server_id)
        if not info:
            return None
        server = info.get("server", info)
        addresses = server.get("Addresses", server.get("addresses", {}))
        for net_name, addrs in addresses.items():
            for addr in addrs:
                if addr.get("OS-EXT-IPS:type") == "floating":
                    return addr.get("addr")
        return None

    def find_ecs_by_private_ip(self, private_ip: str) -> Optional[Dict]:
        """通过内网私有 IP 查找 ECS 实例

        Args:
            private_ip: ECS 内网私有 IP

        Returns:
            ECS 信息 dict (servers 列表中的条目) 或 None
        """
        if not private_ip:
            return None
        servers = self.hcloud.ecs_list_servers()
        server_list = servers.get("servers", []) if isinstance(servers, dict) else []
        for srv in server_list:
            addresses = srv.get("addresses", {})
            for net_name, addrs in addresses.items():
                addr_list = addrs if isinstance(addrs, list) else [addrs]
                for addr in addr_list:
                    if isinstance(addr, dict) and addr.get("OS-EXT-IPS:type") == "fixed":
                        if addr.get("addr") == private_ip:
                            logger.info(f"Found ECS by private IP {private_ip}: "
                                        f"id={srv.get('id')}, name={srv.get('name')}")
                            return srv
        logger.warning(f"No ECS found with private IP: {private_ip}")
        return None

    def _find_subnet_by_ip(self, vpc_id: str, ip: str) -> str:
        """在 VPC 的子网列表中找到包含指定 IP 的子网 ID

        Args:
            vpc_id: VPC ID
            ip: 私有 IP 地址

        Returns:
            子网 ID 或空字符串
        """
        import ipaddress
        try:
            target_ip = ipaddress.ip_address(ip)
        except ValueError:
            return ""

        subnets_data = self.hcloud.subnet_list(vpc_id=vpc_id)
        if not subnets_data or not isinstance(subnets_data, dict):
            return ""
        subnet_list = subnets_data.get("subnets", [])

        for sn in subnet_list:
            cidr = sn.get("cidr", "")
            if cidr:
                try:
                    network = ipaddress.ip_network(cidr, strict=False)
                    if target_ip in network:
                        logger.info(f"Found subnet for IP {ip}: "
                                    f"id={sn.get('id')}, cidr={cidr}")
                        return sn.get("id", "")
                except ValueError:
                    continue
        return ""

    def get_ecs_network_info(self, server_id: str) -> Optional[Dict]:
        """查询 ECS 实例的网络信息 (VPC ID, 子网 ID, 安全组 ID 列表)

        用于从代理 ECS 获取网络资源，直接复用给目标 ECS 创建。

        Args:
            server_id: ECS 实例 ID

        Returns:
            {
                "vpc_id": str,
                "subnet_id": str,
                "sg_ids": [str],
                "private_ip": str,
            } 或 None
        """
        logger.info(f"Querying ECS network info: {server_id}")
        info = self.find_by_id(server_id)
        if not info:
            logger.error(f"ECS not found: {server_id}")
            return None

        server = info.get("server", info)

        # VPC ID: 尝试多个可能的字段名 (不同 API 版本字段名不同)
        vpc_id = (
            server.get("vpc_id", "")
            or server.get("vpcid", "")
            or server.get("OS-EXT-VPC-net:vpc_id", "")
        )

        # 安全组 IDs
        sg_ids = []
        sg_list = server.get("security_groups", [])
        if isinstance(sg_list, list):
            sg_ids = [sg.get("id", "") for sg in sg_list if sg.get("id")]

        # 私有 IP (从 addresses 提取)
        private_ip = ""
        addresses = server.get("addresses", {})
        for net_name, addrs in addresses.items():
            addr_list = addrs if isinstance(addrs, list) else [addrs]
            for addr in addr_list:
                if isinstance(addr, dict) and addr.get("OS-EXT-IPS:type") == "fixed":
                    private_ip = addr.get("addr", "")
                    break
            if private_ip:
                break

        # 子网 ID: 通过 VPC 子网列表匹配私有 IP
        subnet_id = ""
        if vpc_id and private_ip:
            subnet_id = self._find_subnet_by_ip(vpc_id, private_ip)

        # 如果 VPC ID 为空，尝试从 addresses 的 key 提取
        # 在华为云 Nova API 中，addresses 的 key 是 VPC ID (UUID 格式)
        if not vpc_id and private_ip:
            for net_name in addresses.keys():
                # 优先尝试将 addresses key 作为 VPC ID 直接使用
                # 华为云 Nova API 中 addresses key 就是 VPC ID
                if net_name and "-" in net_name and len(net_name) == 36:
                    candidate_vpc_id = net_name
                    # 验证: 尝试列出该 VPC 的子网
                    test_subnets = self.hcloud.subnet_list(candidate_vpc_id)
                    if test_subnets and isinstance(test_subnets, dict) and test_subnets.get("subnets"):
                        vpc_id = candidate_vpc_id
                        logger.info(f"VPC ID from addresses key: {vpc_id}")
                        if not subnet_id:
                            subnet_id = self._find_subnet_by_ip(vpc_id, private_ip)
                        break

                # 回退: 按网络名称匹配 VPC
                vpcs_data = self.hcloud.vpc_list()
                if vpcs_data and isinstance(vpcs_data, dict):
                    for vpc in vpcs_data.get("vpcs", []):
                        if vpc.get("name", "") == net_name:
                            vpc_id = vpc.get("id", "")
                            if not subnet_id:
                                subnet_id = self._find_subnet_by_ip(vpc_id, private_ip)
                            break
                if vpc_id:
                    break

        result = {
            "vpc_id": vpc_id,
            "subnet_id": subnet_id,
            "sg_ids": sg_ids,
            "private_ip": private_ip,
        }

        logger.info(f"ECS network info: vpc={vpc_id}, subnet={subnet_id}, "
                     f"sgs={sg_ids}, private_ip={private_ip}")
        return result

    def get_proxy_network_info(
        self,
        server_id: str = "",
        private_ip: str = "",
    ) -> Optional[Dict]:
        """从代理 ECS 获取网络信息 (VPC/子网/安全组)

        优先使用 server_id 查询；如果没有则通过 private_ip 查找 ECS 实例。

        Args:
            server_id: 代理 ECS 实例 ID (可选)
            private_ip: 代理 ECS 内网私有 IP (可选，当 server_id 为空时使用)

        Returns:
            网络信息 dict 或 None
        """
        if not server_id and not private_ip:
            logger.warning("No server_id or private_ip provided for proxy network discovery")
            return None

        if not server_id and private_ip:
            proxy_ecs = self.find_ecs_by_private_ip(private_ip)
            if not proxy_ecs:
                logger.error(f"Cannot find proxy ECS by private IP: {private_ip}")
                return None
            server_id = proxy_ecs.get("id", "")

        if not server_id:
            return None

        return self.get_ecs_network_info(server_id)

    # ──────────────────────────────────────────────────────────────
    #  ECS 生命周期
    # ──────────────────────────────────────────────────────────────

    def wait_state(self, server_id: str, target_state: str,
                   timeout: int = 300, interval: int = 5) -> bool:
        """等待 ECS 到达指定状态"""
        target = target_state.upper()
        start = time.time()
        while time.time() - start < timeout:
            state = self.get_state(server_id)
            if state == target:
                logger.info(f"ECS {server_id} reached state: {target}")
                return True
            logger.debug(f"ECS {server_id} state: {state}, waiting for {target}...")
            time.sleep(interval)
        logger.error(f"ECS {server_id} did not reach {target} after {timeout}s")
        return False

    def stop_and_wait(self, server_id: str, timeout: int = 300) -> bool:
        """停止 ECS 并等待"""
        logger.info(f"Stopping ECS: {server_id}")
        if not self.hcloud.ecs_stop_server(server_id):
            return False
        return self.wait_state(server_id, "STOPPED", timeout=timeout)

    def start_and_wait(self, server_id: str, timeout: int = 300) -> bool:
        """启动 ECS 并等待"""
        logger.info(f"Starting ECS: {server_id}")
        if not self.hcloud.ecs_start_server(server_id):
            return False
        return self.wait_state(server_id, "ACTIVE", timeout=timeout)

    def restart_and_wait(self, server_id: str, timeout: int = 600) -> bool:
        """重启 ECS 并等待"""
        logger.info(f"Restarting ECS: {server_id}")
        if not self.hcloud.ecs_reboot_server(server_id):
            return False
        return self.wait_state(server_id, "ACTIVE", timeout=timeout)

    # ──────────────────────────────────────────────────────────────
    #  ECS 创建 (代理 ECS)
    # ──────────────────────────────────────────────────────────────

    def create_proxy_ecs(
        self,
        name: str,
        flavor_id: str,
        image_id: str,
        vpc_id: str,
        subnet_id: str,
        sg_id: str,
        keypair_name: str = None,
        root_volume_type: str = "SATA",
        root_volume_size: int = 40,
        data_volume_type: str = "SATA",
        data_volume_size: int = 100,
        admin_pass: str = None,
    ) -> Optional[Dict]:
        """创建代理 ECS

        Args:
            name: ECS 名称
            flavor_id: 规格ID
            image_id: 镜像ID
            vpc_id: VPC ID
            subnet_id: 子网 ID
            sg_id: 安全组 ID
            keypair_name: 密钥对名称
            root_volume_type: 系统盘类型
            root_volume_size: 系统盘大小 GB
            data_volume_type: 数据盘类型
            data_volume_size: 数据盘大小 GB
            admin_pass: 管理密码 (无密钥对时使用)

        Returns:
            ECS 信息 (或 None)
        """
        logger.info(f"Creating proxy ECS: name={name}")

        # 构建参数
        kwargs = {
            "name": name,
            "flavor_id": flavor_id,
            "image_id": image_id,
            "vpc_id": vpc_id,
            "subnet_id": subnet_id,
            "security_group_id": sg_id,
            "root_volume_type": root_volume_type,
            "root_volume_size": root_volume_size,
        }

        if keypair_name:
            kwargs["keypair_name"] = keypair_name
        elif admin_pass:
            kwargs["admin_pass"] = admin_pass

        # 数据盘
        if data_volume_size > 0:
            kwargs["data_volume_type"] = data_volume_type
            kwargs["data_volume_size"] = data_volume_size

        result = self.hcloud.ecs_create_server(**kwargs)
        if result and isinstance(result, dict):
            server = result.get("server", result)
            server_id = server.get("id", "")
            logger.info(f"Proxy ECS created: id={server_id}")
            # 等待 ACTIVE
            if self.wait_state(server_id, "ACTIVE", timeout=600):
                return server
        return None

    def delete_and_wait(self, server_id: str, timeout: int = 300) -> bool:
        """删除 ECS 并等待"""
        logger.info(f"Deleting ECS: {server_id}")
        if not self.hcloud.ecs_delete_server(server_id):
            return False
        start = time.time()
        while time.time() - start < timeout:
            info = self.find_by_id(server_id)
            if not info:
                logger.info(f"ECS {server_id} deleted")
                return True
            time.sleep(5)
        return False

    # ──────────────────────────────────────────────────────────────
    #  安全组规则
    # ──────────────────────────────────────────────────────────────

    def add_sg_rule(
        self,
        sg_id: str,
        protocol: str,
        port: str,
        remote_ip: str = None,
        direction: str = "ingress",
        description: str = "",
    ) -> bool:
        """添加安全组规则

        Args:
            sg_id: 安全组 ID
            protocol: 协议 (tcp/udp/icmp/any)
            port: 端口 (如 "22" 或 "8081-8090")
            remote_ip: 源/目的 CIDR (禁止 0.0.0.0/0，必须指定具体网段或 IP)
            direction: 方向 (ingress/egress)
            description: 规则描述

        Returns:
            是否成功
        """
        if not remote_ip:
            logger.error("安全约束: remote_ip 不能为空，必须指定具体网段或 IP (禁止 0.0.0.0/0)")
            return False
        logger.info(f"Adding SG rule: sg={sg_id}, {protocol}/{port}, from={remote_ip}")
        return self.hcloud.vpc_add_sg_rule(
            sg_id=sg_id,
            protocol=protocol,
            port=port,
            remote_ip=remote_ip,
            direction=direction,
            description=description,
        )

    def ensure_sg_rules_for_migration(self, sg_id: str, source_cidr: str = None) -> bool:
        """确保安全组包含迁移所需规则 (目标端 ECS)

        目标端 ECS 仅需放通 SSH + SMS 数据传输端口，不含代理 ECS 端口。

        Args:
            sg_id: 安全组 ID
            source_cidr: 源端 CIDR (必须指定具体网段或 IP，禁止 0.0.0.0/0)

        Returns:
            是否成功
        """
        if not source_cidr:
            logger.error(
                "安全约束: source_cidr 不能为空，必须指定具体网段或 IP (禁止 0.0.0.0/0)。"
                "例如: 192.168.0.0/24 或 10.0.0.5/32"
            )
            return False

        # 目标端 ECS 仅需 3 个端口 (对齐 SKILL.md 文档)
        rules = [
            ("TCP", "22", "SSH 管理"),
            ("TCP", "8899", "SMS 数据传输"),
            ("TCP", "8900", "SMS 数据传输"),
        ]

        for proto, port, desc in rules:
            if not self.add_sg_rule(sg_id, proto, port, source_cidr, "ingress", desc):
                logger.warning(f"Failed to add rule: {proto}/{port}")
                # 不中断，继续添加其他规则

        logger.info(f"SG rules ensured for {sg_id} (target ECS, source_cidr={source_cidr})")
        return True

    # ──────────────────────────────────────────────────────────────
    #  EIP 管理
    # ──────────────────────────────────────────────────────────────

    def bind_eip(self, server_id: str, eip_id: str) -> bool:
        """绑定 EIP"""
        logger.info(f"Binding EIP {eip_id} to ECS {server_id}")
        return self.hcloud.eip_bind(server_id=server_id, eip_id=eip_id)

    def unbind_eip(self, server_id: str, eip_id: str) -> bool:
        """解绑 EIP"""
        logger.info(f"Unbinding EIP {eip_id} from ECS {server_id}")
        return self.hcloud.eip_unbind(server_id=server_id, eip_id=eip_id)

    # ──────────────────────────────────────────────────────────────
    #  磁盘管理
    # ──────────────────────────────────────────────────────────────

    def list_volumes(self, server_id: str) -> List[Dict]:
        """列出 ECS 挂载的磁盘，按设备名排序 (vda, vdb, vdc...)"""
        result = self.hcloud.evs_list_volumes(server_id=server_id)
        if isinstance(result, dict):
            volumes = result.get("volumes", [])
            # 按设备名排序，确保 vda 在 vdb 之前
            def _device_key(vol):
                attachments = vol.get("attachments", [])
                if attachments:
                    device = attachments[0].get("device", "")
                else:
                    device = vol.get("device", "")
                # /dev/vda → vda
                device = device.replace("/dev/", "")
                return device if device else "zzz"
            volumes.sort(key=_device_key)
            return volumes
        return []

    def check_disk_capacity(self, server_id: str, required_gb: int) -> bool:
        """检查磁盘容量是否满足需求"""
        volumes = self.list_volumes(server_id)
        total = sum(v.get("size", 0) for v in volumes)
        logger.info(f"ECS {server_id} total disk: {total}GB, required: {required_gb}GB")
        return total >= required_gb

    # ──────────────────────────────────────────────────────────────
    #  SMS 源端规格查询 (VMware → ECS 规格映射)
    # ──────────────────────────────────────────────────────────────

    def get_source_specs_from_sms(self, sms_source: Dict) -> Optional[Dict]:
        """从 SMS 源主机信息提取规格 (VMware VM → ECS 规格映射)

        SMS 源主机是 VMware 虚拟机，不是 ECS 实例，不能通过 ECS API 查询。
        本方法从 SMS ListServers 返回的源主机数据中提取 CPU/内存/磁盘/OS 信息，
        并映射到合适的 ECS flavor 和镜像。

        Args:
            sms_source: SMS ListServers 返回的源主机 dict，包含:
                - cpu_quantity: CPU 核数
                - memory: 内存 (字节)
                - os_type: 操作系统类型 (LINUX/WINDOWS)
                - os_version: 操作系统版本
                - init_target_server.disks: 磁盘列表 [{name, size(字节), device_use}]

        Returns:
            {
                "flavor_id": ECS规格ID,
                "flavor_name": 规格名称,
                "image_id": 目标镜像ID,
                "os_type": 操作系统类型,
                "os_version": 源端OS版本,
                "volumes": [{size(GB), type, name, is_root}, ...],
                "az": "",
                "vpc_id": "",
                "subnet_id": "",
                "sg_ids": [],
            }
        """
        logger.info(f"Extracting specs from SMS source: id={sms_source.get('id')}, "
                     f"ip={sms_source.get('ip')}")

        specs = {
            "flavor_id": "",
            "flavor_name": "",
            "image_id": "",
            "os_type": sms_source.get("os_type", "LINUX"),
            "os_version": sms_source.get("os_version", ""),
            "volumes": [],
            "az": "",
            "vpc_id": "",
            "subnet_id": "",
            "sg_ids": [],
        }

        # 1. CPU 和内存 → ECS flavor 映射
        cpu = int(sms_source.get("cpu_quantity", 1))
        memory_bytes = int(sms_source.get("memory", 1024 * 1024 * 1024))
        memory_mb = memory_bytes / (1024 * 1024)  # 转为 MB
        logger.info(f"Source VM: cpu={cpu}, memory={memory_mb:.0f}MB")

        flavor_id = self._match_flavor(cpu, memory_mb)
        specs["flavor_id"] = flavor_id
        specs["flavor_name"] = flavor_id

        # 2. OS 版本 → 目标镜像映射
        specs["image_id"] = self._match_image(specs["os_version"])

        # 3. 磁盘信息 (从 init_target_server.disks 提取，字节 → GB)
        # Issue 22 修复: 提取完整磁盘信息 (device_use, used_size, physical_volumes, volume_groups)
        # 避免SMS.0515: 源端有LVM分区但目标端磁盘信息缺失导致磁盘配置不匹配
        init_target = sms_source.get("init_target_server", {})
        disks = init_target.get("disks", [])
        for disk in disks:
            size_bytes = int(disk.get("size", 0))
            size_gb = max(size_bytes // (1024 ** 3), 1)  # 字节→GB，至少1GB (用于ECS创建)
            used_size_bytes = int(disk.get("used_size", 0))  # 保持字节 (SMS API期望字节)
            is_boot = disk.get("device_use", "") == "BOOT"
            vol = {
                "size": size_gb,
                "type": "SAS",
                "name": disk.get("name", ""),
                "is_root": is_boot,
                "device_use": disk.get("device_use", "DATA"),
                # SMS.0515 修复: used_size 保持字节，不转 GB
                # (SMS API 要求字节；只有 disk.size 需要 GB 给 ECS 创建用)
                "used_size": used_size_bytes,
            }
            # Issue 22: 提取物理卷信息 (LVM PV)
            pvs = disk.get("physical_volumes", [])
            if pvs:
                vol["physical_volumes"] = []
                for pv in pvs:
                    pv_info = {}
                    # SMS.0515 修复: SMS API 返回字段名为 "name"，非 "pv_name"
                    pv_name = pv.get("pv_name") or pv.get("name")
                    if pv_name:
                        pv_info["pv_name"] = pv_name
                    # vg_name 可能也在 name 字段中 (LVM 场景)
                    vg_name = pv.get("vg_name") or pv.get("vg_name")
                    if vg_name:
                        pv_info["vg_name"] = vg_name
                    # SMS.0515 修复: PV size/used_size 保持字节，不转 GB
                    if pv.get("size"):
                        pv_info["size"] = int(pv["size"])
                    if pv.get("used_size"):
                        pv_info["used_size"] = int(pv["used_size"])
                    if pv.get("uuid"):
                        pv_info["uuid"] = pv["uuid"]
                    vol["physical_volumes"].append(pv_info)
                logger.info(f"  Disk '{vol['name']}' has {len(pvs)} physical_volumes (LVM PV)")
            # Issue 22: 提取卷组信息 (LVM VG)
            vgs = disk.get("volume_groups", [])
            if vgs:
                vol["volume_groups"] = []
                for vg in vgs:
                    vg_info = {}
                    # SMS.0515 修复: SMS API 可能返回 "name" 而非 "vg_name"
                    vg_name = vg.get("vg_name") or vg.get("name")
                    if vg_name:
                        vg_info["vg_name"] = vg_name
                    if vg.get("pv_count"):
                        vg_info["pv_count"] = int(vg["pv_count"])
                    # SMS.0515 修复: VG size/free_size 保持字节，不转 GB
                    if vg.get("size"):
                        vg_info["size"] = int(vg["size"])
                    if vg.get("free_size"):
                        vg_info["free_size"] = int(vg["free_size"])
                    vol["volume_groups"].append(vg_info)
                logger.info(f"  Disk '{vol['name']}' has {len(vgs)} volume_groups (LVM VG)")
            specs["volumes"].append(vol)
            logger.info(f"Source disk: name={vol['name']}, size={size_gb}GB, "
                        f"is_root={is_boot}, device_use={vol['device_use']}, "
                        f"used_size={used_size_bytes} bytes")

        if not specs["volumes"]:
            # 默认 40GB 系统盘
            specs["volumes"] = [{"size": 40, "type": "SAS", "name": "root", "is_root": True}]
            logger.warning("No disks found in SMS source, using default 40GB root")

        logger.info(f"SMS source specs: flavor={specs['flavor_id']}, "
                     f"image={specs['image_id']}, os={specs['os_version']}, "
                     f"volumes={len(specs['volumes'])}")
        return specs

    def _match_flavor(self, cpu: int, memory_mb: float) -> str:
        """根据 CPU 和内存匹配最合适的 ECS flavor

        Args:
            cpu: CPU 核数
            memory_mb: 内存 (MB)

        Returns:
            flavor_id
        """
        # 查询可用规格列表
        flavors_data = self.hcloud.ecs_list_flavors()
        if not flavors_data or not isinstance(flavors_data, dict):
            logger.warning("Failed to list flavors, using default c6.large.2")
            return "c6.large.2"

        flavors = flavors_data.get("flavors", [])
        if not flavors:
            return "c6.large.2"

        # Bug fix: 排除 ARM 架构规格 (kc/ac/ai/kai/kx/as/at 等)
        # 源端 VMware VM 是 x86 架构，目标 ECS 也需要 x86 架构匹配 x86 镜像
        ARM_PREFIXES = ("kc", "ac", "ai", "kai", "kx", "ki", "ah", "as", "at", "sn")
        x86_flavors = []
        for f in flavors:
            fname = f.get("name", "")
            if not any(fname.startswith(p) for p in ARM_PREFIXES):
                x86_flavors.append(f)
        flavor_pool = x86_flavors if x86_flavors else flavors

        # 筛选 CPU 匹配的规格，按内存排序
        candidates = []
        for f in flavor_pool:
            f_cpu = int(f.get("vcpus", "0"))
            f_ram = int(f.get("ram", "0"))
            if f_cpu == cpu:
                candidates.append((f_ram, f.get("id", "")))

        if not candidates:
            # 没有精确匹配的 CPU，找 >= cpu 的最小规格
            for f in flavor_pool:
                f_cpu = int(f.get("vcpus", "0"))
                f_ram = int(f.get("ram", "0"))
                if f_cpu >= cpu:
                    candidates.append((f_ram, f.get("id", "")))

        if not candidates:
            return "c6.large.2"

        # 按 RAM 排序，找 >= memory_mb 的最小规格
        candidates.sort(key=lambda x: x[0])
        target_mb = int(memory_mb)
        for ram, fid in candidates:
            if ram >= target_mb:
                logger.info(f"Matched flavor: {fid} (cpu={cpu}, ram={ram}MB >= {target_mb}MB)")
                return fid

        # 没有足够大的，取最大的
        best = candidates[-1]
        logger.info(f"Best available flavor: {best[1]} (ram={best[0]}MB)")
        return best[1]

    def _match_image(self, os_version: str) -> str:
        """根据源端 OS 版本动态查询目标镜像 ID

        通过 IMS ListImages 按名称模糊查询公共镜像，
        支持任意 region，不再硬编码镜像 ID。

        Args:
            os_version: SMS 源端 os_version (如 CENTOS_7_9_64BIT, EulerOS_2_0_64BIT)

        Returns:
            镜像 ID

        Raises:
            RuntimeError: 无法匹配到任何公共镜像
        """
        os_upper = (os_version or "").upper()

        # OS 版本关键字 → IMS 查询名称映射
        OS_NAME_MAP = {
            "CENTOS_7": "CentOS 7.9",
            "CENTOS_8": "CentOS 8",
            "EULEROS_2": "EulerOS 2.0",
            "EULEROS_2_2": "EulerOS 2.2",
            "EULEROS_2_3": "EulerOS 2.3",
            "UBUNTU": "Ubuntu",
            "WINDOWS": "Windows",
        }

        # 匹配查询关键字
        query_name = None
        for key, name in OS_NAME_MAP.items():
            if key in os_upper:
                query_name = name
                break

        if not query_name:
            # 无法识别 OS 类型，尝试用通用查询
            logger.warning(f"Unknown os_version: {os_version}, querying all Linux public images")
            query_name = ""

        # 动态查询公共镜像
        try:
            images_data = self.hcloud.ims_list(os_type="Linux", name=query_name, image_type="gold")
            images = images_data.get("images", []) if isinstance(images_data, dict) else []
            if not images and isinstance(images_data, list):
                images = images_data

            if images:
                # 取第一个匹配的公共镜像
                image_id = images[0].get("id", "")
                image_name = images[0].get("name", "unknown")
                logger.info(f"Matched image for {os_version}: {image_id} ({image_name})")
                return image_id
        except Exception as e:
            logger.error(f"IMS ListImages query failed: {e}")

        raise RuntimeError(
            f"无法为 OS 版本 {os_version} 匹配到公共镜像，"
            f"请通过 IMS ListImages 查询可用镜像并在 Excel 中指定 target_image_id"
        )

    # ──────────────────────────────────────────────────────────────
    #  源端 ECS 规格查询
    # ──────────────────────────────────────────────────────────────

    def get_source_ecs_specs(self, server_id: str) -> Optional[Dict]:
        """查询源端 ECS 完整规格信息

        Returns:
            {
                "flavor_id": 规格ID,
                "flavor_name": 规格名称,
                "image_id": 镜像ID,
                "os_type": 操作系统类型,
                "volumes": [{"id":, "size":, "type":, "name":, "is_root":}, ...],
                "az": 可用区,
                "vpc_id": VPC ID,
                "subnet_id": 子网ID,
                "sg_ids": [安全组ID列表],
                "admin_pass": 密码(如有),
            }
        """
        logger.info(f"Querying source ECS specs: {server_id}")
        info = self.find_by_id(server_id)
        if not info:
            logger.error(f"Source ECS not found: {server_id}")
            return None

        server = info.get("server", info)
        specs = {}

        # 规格信息
        flavor = server.get("flavor", {})
        specs["flavor_id"] = flavor.get("id", "")
        specs["flavor_name"] = flavor.get("name", "")

        # 镜像信息
        image_ref = server.get("image", {})
        if isinstance(image_ref, dict):
            specs["image_id"] = image_ref.get("id", "")
        else:
            specs["image_id"] = str(image_ref)

        # OS 类型
        specs["os_type"] = server.get("metadata", {}).get("__os_type", "Linux")

        # 可用区
        specs["az"] = server.get("OS-EXT-AZ:availability_zone", "")

        # VPC/子网/安全组 (使用 get_ecs_network_info 统一提取)
        net_info = self.get_ecs_network_info(server_id)
        if net_info:
            specs["vpc_id"] = net_info.get("vpc_id", "")
            specs["subnet_id"] = net_info.get("subnet_id", "")
            specs["sg_ids"] = net_info.get("sg_ids", [])
        else:
            specs["vpc_id"] = ""
            specs["subnet_id"] = ""
            specs["sg_ids"] = []
        # 安全组
        sg_list = server.get("security_groups", [])
        if isinstance(sg_list, list):
            specs["sg_ids"] = [sg.get("id", "") for sg in sg_list if sg.get("id")]

        # 磁盘信息
        specs["volumes"] = self._get_ecs_volumes_detail(server_id)

        logger.info(f"Source specs: flavor={specs['flavor_id']}, "
                     f"image={specs['image_id']}, az={specs['az']}, "
                     f"volumes={len(specs['volumes'])}")
        return specs

    def _get_ecs_volumes_detail(self, server_id: str) -> List[Dict]:
        """获取 ECS 磁盘详细信息"""
        volumes = []
        # 通过 block device 查询
        block_info = self.hcloud.ecs_show_block_device(server_id)
        if block_info and isinstance(block_info, dict):
            bd_list = block_info.get("volumeAttachments", [])
            for bd in bd_list:
                vol_id = bd.get("volumeId", bd.get("id", ""))
                vol_detail = self.hcloud.evs_show_volume(vol_id)
                if vol_detail and isinstance(vol_detail, dict):
                    vol = vol_detail.get("volume", vol_detail)
                    volumes.append({
                        "id": vol_id,
                        "size": vol.get("size", 0),
                        "type": vol.get("volume_type", "SAS"),
                        "name": vol.get("name", ""),
                        "is_root": bd.get("device", "") in ("/dev/vda", "/dev/sda", "vda", "sda"),
                    })
        return volumes

    # ──────────────────────────────────────────────────────────────
    #  目标镜像解析
    # ──────────────────────────────────────────────────────────────

    def resolve_target_image(
        self,
        source_image_id: str,
        target_image_id: str = "",
        os_type: str = "Linux",
    ) -> Optional[str]:
        """解析目标镜像 ID

        规则:
            - target_image_id 为空 → 与源端一致 (source_image_id)
            - target_image_id 有值 → 验证镜像是否存在
            - 找不到 → 返回 None, 提示用户上传

        Returns:
            镜像 ID 或 None
        """
        if not target_image_id or target_image_id.strip() == "":
            logger.info(f"Target image not specified, using source image: {source_image_id}")
            return source_image_id

        # 验证指定镜像是否存在
        image_info = self.hcloud.ims_show(target_image_id)
        if image_info and isinstance(image_info, dict):
            image = image_info.get("image", image_info) if isinstance(image_info.get("image"), dict) else image_info
            if image.get("id"):
                logger.info(f"Target image verified: {target_image_id}")
                return target_image_id

        # 镜像不存在，尝试在公共镜像中查找匹配
        logger.warning(f"Target image {target_image_id} not found, searching public images...")
        images = self.hcloud.ims_list(os_type=os_type)
        if images and isinstance(images, dict):
            img_list = images.get("images", [])
            for img in img_list:
                if img.get("id") == target_image_id:
                    logger.info(f"Found target image in list: {target_image_id}")
                    return target_image_id

        logger.error(f"Target image {target_image_id} not found. "
                      "Please upload the image to the target region first.")
        return None

    # ──────────────────────────────────────────────────────────────
    #  目标 AZ 解析
    # ──────────────────────────────────────────────────────────────

    def resolve_target_az(self, target_az: str = "") -> Optional[str]:
        """解析目标可用区

        规则:
            - target_az 为空 → 随机选择一个可用区
            - target_az 有值 → 验证是否存在

        Returns:
            AZ 名称或 None
        """
        if target_az and target_az.strip():
            logger.info(f"Using specified AZ: {target_az}")
            return target_az.strip()

        # 随机选择可用区
        azs = self.hcloud.ecs_list_azs()
        if azs and isinstance(azs, dict):
            az_list = azs.get("availabilityZoneInfo", [])
            if az_list:
                # 优先选择可用状态
                for az in az_list:
                    if az.get("zoneState", {}).get("available", False):
                        az_name = az.get("zoneName", "")
                        if az_name:
                            logger.info(f"Auto-selected AZ: {az_name}")
                            return az_name
                # 退而求其次取第一个
                az_name = az_list[0].get("zoneName", "")
                if az_name:
                    logger.info(f"Using first AZ: {az_name}")
                    return az_name

        logger.warning("No AZ found, will use default")
        return None

    # ──────────────────────────────────────────────────────────────
    #  目标 ECS 自动创建
    # ──────────────────────────────────────────────────────────────

    def _build_target_disks_info(
        self,
        root_volume_size: int,
        data_volumes: List[Dict],
        source_volumes: List[Dict] = None,
    ) -> List[Dict]:
        """构建目标磁盘信息列表 (单位: GB)

        Issue 22 修复: 从源端磁盘复制 LVM 信息 (physical_volumes, volume_groups)
        以及 device_use, used_size 到目标磁盘，避免 SMS.0515 磁盘配置不匹配

        Args:
            root_volume_size: 系统盘大小 (GB)
            data_volumes: 数据盘列表 [{"size": 101, "type": "SAS"}, ...]
            source_volumes: 源端磁盘信息列表 (含 LVM 信息), 可选

        Returns:
            磁盘信息列表 [{"size": 41, "name": "root", "device_use": "BOOT", ...}, ...]
            所有 size 单位均为 GB
        """
        disks = [{"size": root_volume_size, "name": "root"}]
        for i, vol in enumerate(data_volumes, 1):
            disks.append({"size": vol.get("size", 0), "name": f"data{i}"})

        # Issue 22 修复: 从源端磁盘复制 LVM 信息到目标磁盘
        if source_volumes:
            for i, disk in enumerate(disks):
                if i < len(source_volumes):
                    src_vol = source_volumes[i]
                    # device_use: 第一个磁盘=BOOT, 其余按源端或默认DATA
                    if i == 0:
                        disk["device_use"] = "BOOT"
                    else:
                        disk["device_use"] = src_vol.get("device_use", "DATA")
                    # used_size (GB)
                    if src_vol.get("used_size"):
                        disk["used_size"] = src_vol["used_size"]
                    # physical_volumes (LVM PV 信息)
                    if src_vol.get("physical_volumes"):
                        disk["physical_volumes"] = src_vol["physical_volumes"]
                    # volume_groups (LVM VG 信息)
                    if src_vol.get("volume_groups"):
                        disk["volume_groups"] = src_vol["volume_groups"]

        logger.info(f"Target disks info (unit: GB): {disks}")
        return disks

    def create_target_ecs(
        self,
        source_server_id: str,
        target_name: str,
        vpc_id: str,
        subnet_id: str,
        sg_id: str,
        target_image_id: str = "",
        target_az: str = "",
        admin_pass: str = None,
        source_specs: Dict = None,
        sms_source_info: Dict = None,
        target_disk_type: str = None,
        target_disk_sizes: List[Dict] = None,
    ) -> Optional[Dict]:
        """自动创建目标端 ECS

        规则:
            - 规格与源端一致
            - 磁盘配置优先从 Excel 指定 (target_disk_type + target_disk_sizes)
            - 未指定时: 每个磁盘比源端大 1GB
            - 支持多数据盘
            - target_image_id: 空=与源端一致, 有值=指定镜像
            - target_AZ: 空=随机AZ, 有值=指定AZ
            - 管理员密码与源端一致

        Args:
            source_server_id: 源端服务器 ID (SMS source server ID)
            target_name: 目标 ECS 名称
            vpc_id: 目标 VPC ID
            subnet_id: 目标子网 ID
            sg_id: 目标安全组 ID
            target_image_id: 指定目标镜像 (空=与源端一致)
            target_az: 指定可用区 (空=随机)
            admin_pass: 管理员密码 (与源端一致)
            source_specs: 预查询的源端规格 (可选, 避免重复查询)
            sms_source_info: SMS 源主机信息 (VMware VM, 从 SMS ListServers 获取)
                优先使用此参数提取规格，而非查询 ECS API
            target_disk_type: Excel 指定的目标磁盘类型 (如 SAS/SSD/GPSSD/SATA)
                优先于源端磁盘类型
            target_disk_sizes: Excel 指定的目标磁盘大小列表 (单位: GB)
                [{"size": 41, "name": "root", "is_root": True},
                 {"size": 101, "name": "data1", "is_root": False}, ...]
                优先于源端磁盘 +1GB 自动计算

        Returns:
            目标 ECS 信息 或 None
        """
        logger.info(f"Creating target ECS from source {source_server_id}")

        # 0. 校验目标 ECS 名称
        validate_ecs_name(target_name)

        # 1. 获取源端规格
        # Bug fix: 源端是 VMware VM (SMS source)，不是 ECS 实例
        # 优先从 SMS 源主机信息提取规格，避免查询 ECS API 失败
        if not source_specs:
            if sms_source_info:
                logger.info("Using SMS source info to extract VM specs (VMware → ECS)")
                source_specs = self.get_source_specs_from_sms(sms_source_info)
            else:
                # 退化路径: 尝试 ECS API (仅当源端确实是 ECS 时有效)
                logger.warning("No sms_source_info, falling back to ECS API query")
                source_specs = self.get_source_ecs_specs(source_server_id)
        if not source_specs:
            logger.error("Failed to get source ECS specs")
            return None

        # 2. 解析目标镜像
        image_id = self.resolve_target_image(
            source_specs.get("image_id", ""),
            target_image_id,
            source_specs.get("os_type", "Linux"),
        )
        if not image_id:
            logger.error("Failed to resolve target image")
            return None

        # 3. 解析目标 AZ
        az = self.resolve_target_az(target_az)

        # 4. 构建磁盘配置
        # 优先级: Excel 指定 (target_disk_sizes) > 源端 +1GB 自动计算
        # Issue 2 修复: 明确磁盘大小单位为 GB (gigabytes)
        source_volumes = source_specs.get("volumes", [])
        root_volume_type = "SAS"
        root_volume_size = 40  # 默认 40 GB
        data_volumes = []

        if target_disk_sizes:
            # Excel 指定的磁盘配置 (优先)
            logger.info("Using Excel-specified target disk sizes")
            for vol in target_disk_sizes:
                vol_size_gb = vol.get("size", 40)
                vol_type = target_disk_type or vol.get("type", "SAS")
                if vol.get("is_root", False):
                    root_volume_type = vol_type
                    root_volume_size = max(vol_size_gb, 40)
                    logger.info(f"Root disk (Excel): size={root_volume_size} GB, type={root_volume_type}")
                else:
                    data_volumes.append({"size": vol_size_gb, "type": vol_type})
                    logger.info(f"Data disk (Excel): size={vol_size_gb} GB, type={vol_type}")
        else:
            # 自动计算: 每个磁盘比源端大 1GB
            for vol in source_volumes:
                source_size_gb = vol.get("size", 40)
                vol_size_gb = source_size_gb + 1  # +1 GB
                vol_type = target_disk_type or vol.get("type", "SAS")
                if vol.get("is_root", False):
                    root_volume_type = vol_type
                    root_volume_size = max(vol_size_gb, 40)
                    logger.info(f"Root disk: source={source_size_gb} GB -> target={root_volume_size} GB (unit: GB, min=40)")
                else:
                    data_volumes.append({"size": vol_size_gb, "type": vol_type})
                    logger.info(f"Data disk: source={source_size_gb} GB -> target={vol_size_gb} GB (unit: GB)")

            if not source_volumes:
                root_volume_size = 40
                logger.warning("No source volumes found, using default: root=40 GB (unit: GB)")

        logger.info(f"Target disk config (all sizes in GB): root={root_volume_size} GB/{root_volume_type}, "
                     f"data_volumes={len(data_volumes)}")

        # 5. 创建目标 ECS
        flavor_id = source_specs.get("flavor_id", "")
        if not flavor_id:
            logger.error("No flavor_id from source ECS")
            return None

        result = self.hcloud.ecs_create_full(
            name=target_name,
            image_id=image_id,
            flavor_id=flavor_id,
            vpc_id=vpc_id,
            subnet_id=subnet_id,
            sg_id=sg_id,
            root_volume_type=root_volume_type,
            root_volume_size=root_volume_size,
            data_volumes=data_volumes if data_volumes else None,
            admin_pass=admin_pass,
            availability_zone=az,
        )

        if not result or not isinstance(result, dict):
            logger.error("ECS creation returned empty result")
            return None

        # hcloud CreateServers returns {"serverIds": ["xxx"], "job_id": "xxx"}
        server_id = ""
        if "serverIds" in result and isinstance(result["serverIds"], list) and result["serverIds"]:
            server_id = result["serverIds"][0]
        elif "server" in result and isinstance(result["server"], dict):
            server_id = result["server"].get("id", "")
        elif "id" in result:
            server_id = result["id"]
        if not server_id:
            logger.error(f"No server ID in creation result: {json.dumps(result, ensure_ascii=False)[:500]}")
            return None

        logger.info(f"Target ECS created: id={server_id}, name={target_name}")

        # 6. 等待 ACTIVE
        if self.wait_state(server_id, "ACTIVE", timeout=600):
            logger.info(f"Target ECS {server_id} is ACTIVE")

            # 6.1 添加所属权标签 (标识本 skill 创建的 ECS)
            try:
                from ownership_utils import OwnershipManager
                om = OwnershipManager(self.hcloud)
                ownership_tags = om.build_ownership_tags(
                    source_name=source_specs.get("os_version", ""),
                    source_ip=sms_source_info.get("ip", "") if sms_source_info else "",
                )
                if not self.hcloud.ecs_add_tags(server_id, ownership_tags):
                    logger.warning(f"Failed to add ownership tags to ECS {server_id}")
                else:
                    logger.info(f"Ownership tags added to ECS {server_id}: {len(ownership_tags)} tags")
            except Exception as e:
                logger.warning(f"Ownership tag setup failed (non-fatal): {e}")

            # 返回完整信息
            final_info = self.find_by_id(server_id)
            if final_info:
                server = final_info.get("server", final_info)
            # Issue 2 修复: 附加目标磁盘配置 (单位: GB) 供 SMS 任务创建使用
            # Issue 22 修复: 传递 source_volumes 以复制 LVM 信息 (physical_volumes, volume_groups)
            target_disks = self._build_target_disks_info(
                root_volume_size, data_volumes,
                source_volumes=source_specs.get("volumes", [])
            )
            # Issue 22 修复: 查询目标 ECS 云硬盘 ID (disk_id) 并注入 target_disks
            # disk_id 是 SMS API --target_server.disks.N.disk_id 的必需参数
            try:
                ecs_volumes = self.list_volumes(server_id)
                for i, disk in enumerate(target_disks):
                    if i < len(ecs_volumes):
                        disk["disk_id"] = ecs_volumes[i].get("id", "")
                        logger.info(f"Target disk {i+1} disk_id={disk['disk_id']}")
            except Exception as e:
                logger.warning(f"Failed to query disk_id for target ECS: {e}")
            server["target_disks"] = target_disks
            return server
        else:
            logger.error(f"Target ECS {server_id} did not become ACTIVE")
            return None

    # ──────────────────────────────────────────────────────────────
    #  批量目标 ECS 创建
    # ──────────────────────────────────────────────────────────────

    def batch_create_target_ecs(
        self,
        migration_items: List[Dict],
        vpc_id: str,
        subnet_id: str,
        sg_id: str,
        max_workers: int = 4,
    ) -> Dict[str, Dict]:
        """批量并行创建目标端 ECS

        Args:
            migration_items: 迁移项列表, 每项包含:
                - source_server_id: 源端 ECS ID
                - target_name: 目标名称
                - target_image_id: 目标镜像 (可选)
                - target_az: 目标AZ (可选)
                - admin_pass: 管理密码
            vpc_id: 目标 VPC ID
            subnet_id: 目标子网 ID
            sg_id: 目标安全组 ID
            max_workers: 最大并行数

        Returns:
            {source_id: target_ecs_info} 映射
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = {}
        results_lock = threading.Lock()

        def _create_one(item: Dict) -> tuple:
            source_id = item.get("source_server_id", "")
            target_name = item.get("target_name", f"target-{source_id[:8]}")
            logger.info(f"Processing migration item: {source_id} -> {target_name}")

            target_info = self.create_target_ecs(
                source_server_id=source_id,
                target_name=target_name,
                vpc_id=vpc_id,
                subnet_id=subnet_id,
                sg_id=sg_id,
                target_image_id=item.get("target_image_id", ""),
                target_az=item.get("target_az", ""),
                admin_pass=item.get("admin_pass"),
                sms_source_info=item.get("sms_source_info"),
                target_disk_type=item.get("target_disk_type"),
                target_disk_sizes=item.get("target_disk_sizes"),
            )
            return (source_id, target_info)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_create_one, item) for item in migration_items]
            for future in as_completed(futures):
                source_id, target_info = future.result()
                with results_lock:
                    results[source_id] = target_info
                if target_info:
                    logger.info(f"Target created for {source_id}: {target_info.get('id')}")
                else:
                    logger.error(f"Failed to create target for {source_id}")

        success_count = sum(1 for v in results.values() if v)
        logger.info(f"Batch creation: {success_count}/{len(migration_items)} succeeded")
        return results
