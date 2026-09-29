#!/usr/bin/env python3
"""
migrate_worker.py — 单机迁移执行器

执行单个源端到目标 ECS 的完整迁移流程:
  1. 前置检查 (网络连通性、源端状态、目标 ECS 状态)
  2. SMS Agent 推送 (如未安装)
  3. SMS 迁移任务创建
  4. 启动迁移并监控进度
  5. 迁移完成后验证
  6. 返回迁移结果

私网迁移特殊处理:
  - 通过 GOST 管理通道操作源端
  - SMS Agent 通过 squid 代理访问华为云 API
  - 数据传输通过 GOST 端口转发到目标 ECS
"""

import time
import logging
import re
from typing import Optional, Dict, Any, List

from sms_ops import SMSOps
from ecs_ops import ECSOps
from network_ops import NetworkOps, CloudNetworkOps
from sms_agent_push import SMSAgentPush
from skill_logger import MigrationLogger
from step_tracker import StepTracker
from task_name_utils import sanitize_task_name, generate_task_name_from_ip

try:
    from ownership_utils import OwnershipManager
    _HAS_OWNERSHIP = True
except ImportError:
    _HAS_OWNERSHIP = False

try:
    from post_migration_verify import PostMigrationVerifier
    _HAS_POST_VERIFY = True
except ImportError:
    _HAS_POST_VERIFY = False

logger = logging.getLogger(__name__)


class MigrateWorker:
    """单机迁移执行器"""

    def __init__(
        self,
        sms_ops: SMSOps,
        ecs_ops: ECSOps,
        agent_pusher: SMSAgentPush,
        config: Dict[str, Any],
        cloud_network_ops: CloudNetworkOps = None,
        proxy_ecs_ops: Any = None,
    ):
        """
        Args:
            sms_ops: SMS 操作实例
            ecs_ops: ECS 操作实例
            agent_pusher: Agent 推送实例
            config: 全局配置
            cloud_network_ops: 云网络操作实例 (用于自动创建网络资源)
            proxy_ecs_ops: 代理 ECS 操作实例 (用于动态更新 GOST 转发)
        """
        self.sms = sms_ops
        self.ecs = ecs_ops
        self.agent_pusher = agent_pusher
        self.config = config
        self.cloud_network = cloud_network_ops
        self.proxy_ops = proxy_ecs_ops
        self.log_dir = config.get("log_dir", "/var/log/migration-private")

    # ──────────────────────────────────────────────────────
    #  目标 ECS 自动创建
    # ──────────────────────────────────────────────────────

    def _build_target_disks_from_existing(self, ecs_id: str, task: Dict[str, Any]) -> List[Dict]:
        """从已有目标ECS的磁盘 + 源端LVM信息构建 target_disks

        修复 SMS.6519 (Cannot find disk): 当复用已有ECS时，必须构建 target_disks
        包含 physical_volumes / volume_groups，否则 SMS CreateTask 找不到磁盘。
        修复 SMS.6614 (disk size < partitions): 按大小匹配源端磁盘到目标磁盘，
        而非按索引，避免目标ECS磁盘顺序与源端不一致时大小不匹配。
        """
        try:
            volumes = self.ecs.list_volumes(ecs_id)
            if not volumes:
                logger.warning(f"No volumes found for existing ECS {ecs_id}")
                return []

            # 从源端信息获取 LVM 数据
            src_info = task.get("sms_source_info", {})
            init_target = src_info.get("init_target_server", {}) if src_info else {}
            src_disks = init_target.get("disks", []) if init_target else []

            if not src_disks:
                # 无源端信息，简单构建
                target_disks = []
                for i, vol in enumerate(volumes):
                    target_disks.append({
                        "size": vol.get("size", 0),
                        "name": "root" if i == 0 else f"data{i}",
                        "disk_id": vol.get("id", ""),
                        "device_use": "BOOT" if i == 0 else "DATA",
                    })
                return target_disks

            # 智能匹配: BOOT源端磁盘 → 最接近且>=的目标磁盘作为disk1
            # 其余数据磁盘按大小降序匹配剩余目标磁盘
            # 注意: 源端size可能是字节，目标volume size是GB，需统一单位
            def _to_gb(s):
                """将size转换为GB（源端可能是字节，目标EVS API返回GB）"""
                if s > 1024:  # 字节
                    return s / (1024 ** 3)
                return s  # 已经是GB

            src_boot = None
            src_data = []
            for sd in src_disks:
                if sd.get("device_use", "").upper() == "BOOT" or sd == src_disks[0]:
                    src_boot = sd
                else:
                    src_data.append(sd)
            if src_boot is None:
                src_boot = src_disks[0]

            # 目标磁盘列表（可复制）
            remaining_vols = list(volumes)

            # 1. 匹配BOOT: 找最接近且>= boot size 的目标磁盘
            boot_vol = None
            boot_size_gb = _to_gb(src_boot.get("size", 0))
            for v in remaining_vols:
                if v.get("size", 0) >= boot_size_gb:
                    if boot_vol is None or v.get("size", 0) < boot_vol.get("size", 0):
                        boot_vol = v
            if boot_vol is None:
                # 没有足够大的，取最大的
                boot_vol = max(remaining_vols, key=lambda v: v.get("size", 0))
            remaining_vols.remove(boot_vol)

            # 2. 数据磁盘按大小降序匹配（统一转GB比较）
            #    相同大小的磁盘按设备名排序，避免PV/VG信息交叉配错
            def _src_device_name(d):
                """从源端磁盘的PV信息提取设备名，如 /dev/vdb1 → vdb"""
                pvs = d.get("physical_volumes", [])
                if pvs:
                    name = pvs[0].get("name", "")
                    # /dev/vdb1 → vdb
                    m = re.match(r'/dev/(vd[a-z]+)', name)
                    if m:
                        return m.group(1)
                return "zzz"  # 无法识别时排到最后

            def _vol_device_name(v):
                """从目标volume提取设备名"""
                return v.get("device", v.get("attachment[0].device", "zzz"))

            src_data_sorted = sorted(src_data, key=lambda d: (-_to_gb(d.get("size", 0)), _src_device_name(d)))
            remaining_vols_sorted = sorted(remaining_vols, key=lambda v: (-v.get("size", 0), _vol_device_name(v)))

            # 构建target_disks: disk1=BOOT, 然后数据磁盘
            target_disks = []

            def _make_disk(vol, src_disk, idx):
                disk = {
                    "size": vol.get("size", 0),
                    "name": "root" if idx == 0 else f"data{idx}",
                    "disk_id": vol.get("id", ""),
                    "device_use": "BOOT" if idx == 0 else src_disk.get("device_use", "DATA"),
                }
                if src_disk.get("used_size"):
                    disk["used_size"] = src_disk["used_size"]
                if src_disk.get("physical_volumes"):
                    disk["physical_volumes"] = src_disk["physical_volumes"]
                if src_disk.get("volume_groups"):
                    disk["volume_groups"] = src_disk["volume_groups"]
                return disk

            # BOOT disk
            boot_disk = _make_disk(boot_vol, src_boot, 0)
            target_disks.append(boot_disk)
            logger.info(f"  Matched BOOT: target {boot_vol.get('size',0)}GB ← source {boot_size_gb:.0f}GB")

            # Data disks
            for i, (sd, vol) in enumerate(zip(src_data_sorted, remaining_vols_sorted), 1):
                disk = _make_disk(vol, sd, i)
                target_disks.append(disk)
                logger.info(f"  Matched data{i}: target {vol.get('size',0)}GB ← source {_to_gb(sd.get('size',0)):.0f}GB")

            # 多余的目标磁盘
            for j in range(len(src_data_sorted), len(remaining_vols_sorted)):
                vol = remaining_vols_sorted[j]
                target_disks.append({
                    "size": vol.get("size", 0),
                    "name": f"data{j+1}",
                    "disk_id": vol.get("id", ""),
                    "device_use": "DATA",
                })

            logger.info(f"Built target_disks from existing ECS {ecs_id}: {len(target_disks)} disks (size-matched)")
            for i, d in enumerate(target_disks):
                pvs = d.get("physical_volumes", [])
                vgs = d.get("volume_groups", [])
                logger.info(f"  Disk {i+1}: size={d.get('size')}GB, device_use={d.get('device_use')}, PVs={len(pvs)}, VGs={len(vgs)}")
            return target_disks
        except Exception as e:
            logger.warning(f"Failed to build target_disks from existing ECS: {e}")
            return []

    def ensure_target_ecs(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """确保目标 ECS 存在，不存在则自动创建

        规则:
            - 如果 task 中已有 target_server_id，直接使用
            - 否则根据源端规格自动创建目标 ECS
            - 规格与源端一致，磁盘+1GB，密码与源端一致

        Returns:
            {"success": bool, "target_server_id": str, "error": str, "created": bool}
        """
        result = {"success": False, "target_server_id": "", "error": "", "created": False}

        # Bug fix: 如果已有目标 ECS ID，直接使用
        existing_id = task.get("target_server_id", "")
        if existing_id:
            logger.info(f"Target ECS already specified: {existing_id}")
            # 验证存在
            info = self.ecs.find_by_id(existing_id)
            if info:
                result["success"] = True
                result["target_server_id"] = existing_id
                # 提取私有 IP 供 migration_ip 使用
                priv_ip = self.ecs.get_private_ip(existing_id)
                if priv_ip:
                    result["target_private_ip"] = priv_ip
                    logger.info(f"Target ECS private IP: {priv_ip}")
                # 修复 SMS.6519: 构建target_disks
                result["target_disks"] = self._build_target_disks_from_existing(existing_id, task)
                return result
            else:
                result["error"] = f"Target ECS {existing_id} not found"
                return result

        # Bug fix: 按名称查找已有 ECS，避免重复创建
        # 重要: 不能回退到 source_name, 否则会匹配到源端机器
        target_name_check = task.get("target_name", "")
        if target_name_check:
            existing_ecs = self.ecs.find_by_name(target_name_check)
            if existing_ecs:
                existing_id = existing_ecs.get("id", "")
                logger.info(f"Target ECS already exists by name '{target_name_check}': {existing_id}")
                result["success"] = True
                result["target_server_id"] = existing_id
                result["target_server_name"] = target_name_check
                # 提取私有 IP 供 migration_ip 使用
                priv_ip = self.ecs.get_private_ip(existing_id)
                if priv_ip:
                    result["target_private_ip"] = priv_ip
                    logger.info(f"Target ECS private IP: {priv_ip}")
                # 修复 SMS.6519: 构建target_disks
                result["target_disks"] = self._build_target_disks_from_existing(existing_id, task)
                return result

        # 防重复创建: 按所属权标签查找已有目标 ECS
        # 通过 source-ip 标签匹配，避免对同一源端重复创建目标 ECS
        if _HAS_OWNERSHIP:
            try:
                om = OwnershipManager(self.ecs.hcloud)
                source_ip = task.get("source_ip", "")
                if source_ip:
                    existing_by_tag = om.find_existing_target(source_ip)
                    if existing_by_tag:
                        existing_id = existing_by_tag.get("id", "")
                        existing_state = existing_by_tag.get("status", "").upper()
                        existing_name = existing_by_tag.get("name", "")
                        logger.info(
                            f"Found existing target ECS by ownership tag: "
                            f"id={existing_id}, name={existing_name}, state={existing_state}"
                        )
                        # ACTIVE/STOPPED → 直接复用
                        if existing_state in ("ACTIVE", "STOPPED"):
                            result["success"] = True
                            result["target_server_id"] = existing_id
                            result["target_server_name"] = existing_name
                            priv_ip = self.ecs.get_private_ip(existing_id)
                            if priv_ip:
                                result["target_private_ip"] = priv_ip
                                logger.info(f"Reusing existing target ECS (state={existing_state}), private IP: {priv_ip}")
                            # 修复 SMS.6519: 构建target_disks
                            result["target_disks"] = self._build_target_disks_from_existing(existing_id, task)
                            return result
                        # 异常状态 → 需用户确认后删除重建
                        elif existing_state in ("ERROR", "FAULT", "BUILD", "HARD_REBOOT", "REBOOT"):
                            logger.warning(
                                f"Existing target ECS {existing_id} in abnormal state={existing_state}. "
                                f"Manual confirmation required to delete and recreate."
                            )
                            result["error"] = (
                                f"目标 ECS 已存在但状态异常 (state={existing_state}, id={existing_id})。"
                                f"请确认是否删除该 ECS 后重新执行迁移。"
                            )
                            return result
            except Exception as e:
                logger.warning(f"Ownership tag check failed (non-fatal): {e}")

        # 需要自动创建
        source_server_id = task.get("source_server_id", "")
        if not source_server_id:
            # 没有源端 ECS ID，无法自动创建
            result["error"] = "No source_server_id for target auto-creation"
            return result

        # 获取网络资源
        vpc_id = task.get("vpc_id", self.config.get("vpc_id", ""))
        subnet_id = task.get("subnet_id", self.config.get("subnet_id", ""))
        sg_id = task.get("sg_id", self.config.get("sg_id", ""))

        # ── 优先级 0: 从代理 ECS 自动获取 VPC/子网/安全组，直接复用 ──
        if not vpc_id or not subnet_id or not sg_id:
            proxy_private_ip = task.get(
                "proxy_private_ip", self.config.get("proxy_private_ip", "")
            )
            proxy_server_id = task.get(
                "proxy_server_id", self.config.get("proxy_server_id", "")
            )
            if proxy_private_ip or proxy_server_id:
                logger.info("Discovering network from proxy ECS...")
                proxy_net = self.ecs.get_proxy_network_info(
                    server_id=proxy_server_id,
                    private_ip=proxy_private_ip,
                )
                if proxy_net:
                    if not vpc_id:
                        vpc_id = proxy_net.get("vpc_id", "")
                    if not subnet_id:
                        subnet_id = proxy_net.get("subnet_id", "")
                    if not sg_id and proxy_net.get("sg_ids"):
                        sg_id = proxy_net["sg_ids"][0]
                    logger.info(
                        f"Reusing proxy ECS network: VPC={vpc_id}, "
                        f"subnet={subnet_id}, SG={sg_id}"
                    )
                    # 确保代理 SG 包含目标 ECS 所需端口 (22/8899/8900)
                    if sg_id:
                        source_cidr = task.get(
                            "source_cidr", self.config.get("source_cidr", "")
                        )
                        if not source_cidr and proxy_net.get("private_ip"):
                            # 使用代理 ECS 私网 IP 所在子网作为 source_cidr
                            source_cidr = CloudNetworkOps.compute_source_cidr(
                                [proxy_net["private_ip"]]
                            )
                        if not source_cidr:
                            source_ip = task.get("source_ip", "")
                            if source_ip:
                                source_cidr = CloudNetworkOps.compute_source_cidr(
                                    [source_ip]
                                )
                        if source_cidr and source_cidr.strip().lower() not in (
                            "0.0.0.0/0",
                            "::/0",
                        ):
                            self.ecs.ensure_sg_rules_for_migration(
                                sg_id, source_cidr=source_cidr
                            )
                            logger.info(
                                f"Ensured target ECS ports (22/8899/8900) "
                                f"open in proxy SG {sg_id} for {source_cidr}"
                            )

        if not vpc_id or not subnet_id:
            # VPC/子网未提供，自动创建全部网络资源
            if self.cloud_network:
                # 安全约束: source_cidr 禁止 0.0.0.0/0，必须来自 task 或 config
                source_cidr = task.get("source_cidr", self.config.get("source_cidr", ""))
                if not source_cidr or source_cidr.strip().lower() in ("0.0.0.0/0", "::/0"):
                    result["error"] = (
                        "安全约束: source_cidr 未指定或为 0.0.0.0/0 (禁止)。"
                        "请在 Excel 或 config 中指定具体源端 CIDR 网段。"
                    )
                    return result
                logger.info("Network resources not provided, auto-creating...")
                net_result = self.cloud_network.ensure_migration_network(
                    vpc_name=task.get("vpc_name", "migration-vpc"),
                    subnet_name=task.get("subnet_name", "migration-subnet"),
                    sg_name=task.get("sg_name", "migration-sg"),
                    source_cidr=source_cidr,
                )
                if not net_result:
                    result["error"] = "Failed to create network resources"
                    return result
                vpc_id = net_result["vpc_id"]
                subnet_id = net_result["subnet_id"]
                sg_id = net_result["sg_id"]
            else:
                result["error"] = "No network resources and no cloud_network_ops"
                return result
        elif not sg_id:
            # VPC/子网已提供，仅创建安全组
            if self.cloud_network:
                # 安全约束: source_cidr 禁止 0.0.0.0/0
                source_cidr = task.get("source_cidr", self.config.get("source_cidr", ""))
                if not source_cidr or source_cidr.strip().lower() in ("0.0.0.0/0", "::/0"):
                    # 尝试从源端 IP 推导 CIDR
                    source_ip = task.get("source_ip", "")
                    if source_ip:
                        source_cidr = CloudNetworkOps.compute_source_cidr([source_ip])
                    if not source_cidr:
                        result["error"] = (
                            "安全约束: source_cidr 未指定且无法从 source_ip 推导。"
                            "请在 task 或 config 中指定具体源端 CIDR。"
                        )
                        return result
                logger.info(f"VPC/subnet provided, creating SG only in VPC {vpc_id}...")
                sg_result = self.cloud_network.ensure_security_group(
                    name=task.get("sg_name", "migration-sg"),
                    vpc_id=vpc_id,
                    source_cidr=source_cidr,
                )
                if sg_result:
                    sg_id = sg_result.get("id")
                    logger.info(f"SG ready: {sg_id}")
                else:
                    result["error"] = "Failed to create security group in existing VPC"
                    return result
            else:
                result["error"] = "No SG and no cloud_network_ops to create one"
                return result

        # 创建目标 ECS
        target_name = task.get("target_name", f"target-{source_server_id[:8]}")
        target_image_id = task.get("target_image_id", "")
        target_az = task.get("target_az", "")
        admin_pass = task.get("source_password", task.get("admin_pass", ""))

        target_info = self.ecs.create_target_ecs(
            source_server_id=source_server_id,
            target_name=target_name,
            vpc_id=vpc_id,
            subnet_id=subnet_id,
            sg_id=sg_id,
            target_image_id=target_image_id,
            target_az=target_az,
            admin_pass=admin_pass,
            sms_source_info=task.get("sms_source_info"),
        )

        if not target_info:
            result["error"] = "Failed to create target ECS"
            return result

        target_id = target_info.get("id", "")
        result["success"] = True
        result["target_server_id"] = target_id
        result["created"] = True
        # 提取私有 IP 供 migration_ip 使用
        priv_ip = self.ecs.get_private_ip(target_id)
        if priv_ip:
            result["target_private_ip"] = priv_ip
            logger.info(f"Target ECS private IP: {priv_ip}")
        # Issue 2 修复: 捕获目标磁盘配置 (单位: GB) 供 SMS 任务创建使用
        result["target_disks"] = target_info.get("target_disks", [])
        # Issue 4 修复: 捕获目标服务器名称, 供 SMS API --target_server.name 使用
        result["target_server_name"] = target_info.get("name", target_name)
        logger.info(f"Target ECS auto-created: {target_id}, name={result['target_server_name']}")
        logger.info(f"Target disks (unit: GB): {result['target_disks']}")

        # P2-4优化: 创建后并发重复检测
        # 在并发场景下，另一个线程可能同时创建了同名 ECS
        # 检测到重复时记录警告，不影响当前迁移流程
        try:
            post_check = self.ecs.find_by_name(result["target_server_name"])
            if post_check and post_check.get("id", "") != target_id:
                logger.warning(
                    f"P2-4: 检测到同名目标 ECS 可能重复 "
                    f"(name={result['target_server_name']}, "
                    f"created={target_id}, found={post_check.get('id')})。"
                    f"可能是并发创建导致，当前使用 {target_id}。"
                )
        except Exception:
            pass  # 非关键检查，不影响迁移

        return result

    # ──────────────────────────────────────────────────────
    #  前置检查
    # ──────────────────────────────────────────────────────

    def pre_check(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """迁移前置检查 (网络检查并行化)

        Args:
            task: 迁移任务参数

        Returns:
            {"passed": bool, "errors": [str], "warnings": [str]}
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        result = {"passed": True, "errors": [], "warnings": []}

        source_ip = task.get("source_ip", "")
        target_server_id = task.get("target_server_id", "")
        proxy_ip = task.get("proxy_ip", self.config.get("proxy_ip", ""))

        # 1. 检查目标 ECS 状态
        ecs_state = self.ecs.get_state(target_server_id)
        if ecs_state not in ("ACTIVE", "STOPPED"):
            result["errors"].append(f"Target ECS state invalid: {ecs_state}")
            result["passed"] = False
        else:
            logger.info(f"Target ECS state OK: {ecs_state}")

        # 2-5. 并行网络检查
        net_checks = []

        if proxy_ip:
            net_checks.append(("ping", lambda: ("proxy_ping", NetworkOps.ping(proxy_ip))))

            gost_ssh_port = task.get("gost_ssh_port", 22)
            net_checks.append(("gost_ssh", lambda: ("gost_ssh",
                NetworkOps.check_port(proxy_ip, gost_ssh_port, timeout=5))))

            squid_port = self.config.get("squid_port", 3128)
            net_checks.append(("squid", lambda: ("squid",
                NetworkOps.check_port(proxy_ip, squid_port, timeout=5))))

            # 检查代理 ECS 上的数据流本地端口 (per-task, 避免多目标端口冲突)
            gost_data_local_ports = task.get("gost_data_local_ports", [8899, 8900])
            for port in gost_data_local_ports:
                net_checks.append((f"gost_data_{port}", lambda p=port: (f"gost_data_{p}",
                    NetworkOps.check_port(proxy_ip, p, timeout=5))))

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(fn): name for name, fn in net_checks}
            for future in as_completed(futures):
                check_name = futures[future]
                try:
                    check_id, check_result = future.result()
                    if check_id == "proxy_ping":
                        ping_ok, latency = check_result
                        if not ping_ok:
                            # ICMP 不通时，用 TCP 端口检查作为回退
                            # 如果 TCP 端口可达，说明主机在线，只是 ICMP 被防火墙拦截
                            tcp_ok = NetworkOps.check_port(proxy_ip, 22, timeout=5)
                            if tcp_ok:
                                result["warnings"].append(
                                    f"Proxy ECS ICMP ping unreachable but TCP:22 reachable "
                                    f"(ICMP blocked by firewall, non-critical): {proxy_ip}"
                                )
                            else:
                                result["warnings"].append(
                                    f"Proxy ECS ping unreachable (ICMP may be blocked): {proxy_ip}"
                                )
                        elif latency > 200:
                            result["warnings"].append(f"High latency to proxy: {latency}ms")
                    elif check_id == "gost_ssh":
                        if not check_result:
                            result["errors"].append(f"GOST SSH port unreachable: {proxy_ip}:{task.get('gost_ssh_port', 22)}")
                            result["passed"] = False
                    elif check_id == "squid":
                        if not check_result:
                            result["warnings"].append(f"Squid proxy port unreachable: {proxy_ip}:{self.config.get('squid_port', 3128)}")
                    elif check_id.startswith("gost_data_"):
                        if not check_result:
                            result["warnings"].append(f"GOST data port unreachable: {proxy_ip}:{check_id.split('_')[-1]}")
                except Exception as e:
                    logger.warning(f"Network check {check_name} failed: {e}")

        # 6. 多数据盘验证: 检查目标 ECS 磁盘数量与源端一致
        target_disks = task.get("target_disks", [])
        if target_disks:
            target_volumes = self.ecs.list_volumes(target_server_id)
            target_vol_count = len(target_volumes) if target_volumes else 0
            expected_count = len(target_disks)
            if target_vol_count > 0 and target_vol_count != expected_count:
                result["errors"].append(
                    f"Disk count mismatch: target ECS has {target_vol_count} volumes, "
                    f"but expected {expected_count} (source disks + 1GB each). "
                    f"This may cause migration failure."
                )
                result["passed"] = False
            else:
                logger.info(f"Multi-disk validation OK: target={target_vol_count} volumes, "
                            f"expected={expected_count}")
            # 记算总磁盘容量并记录
            total_gb = sum(d.get("size", 0) for d in target_disks)
            logger.info(f"Target total disk capacity: {total_gb} GB across {expected_count} disks")

        if result["passed"]:
            logger.info(f"Pre-check passed for {source_ip} -> {target_server_id}")
        else:
            logger.error(f"Pre-check failed: {result['errors']}")

        return result

    # ──────────────────────────────────────────────────────
    #  Agent 确保
    # ──────────────────────────────────────────────────────

    def ensure_agent(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """确保源端 SMS Agent 已安装并运行

        Returns:
            {"success": bool, "source_id": str, "error": str}
        """
        result = {"success": False, "source_id": "", "error": "", "source_info": None}

        source_ip = task.get("source_ip", "")

        # 先检查 SMS 服务中是否已有该源端
        source = self.sms.find_source_by_ip(source_ip)
        if source:
            source_id = source.get("id", "")
            state = source.get("state", "").upper()
            if state in ("ONLINE", "READY", "ACTIVE", "WAITING", "CONNECTED"):
                logger.info(f"Source already registered and online: {source_id}")
                result["success"] = True
                result["source_id"] = source_id
                # Issue 22 修复: 用 ShowServer 获取完整源端信息 (含 init_target_server.disks 的 LVM 信息)
                full_info = self.sms.hcloud.sms_show_source(source_id)
                result["source_info"] = full_info if full_info else source
                return result
            elif state in ("UNKNOWN", "ERROR", "OFFLINE", "DELETE", "DELETED", "FAULT"):
                # Agent 状态异常 (如配置不完整、进程崩溃)，先删除 SMS 中的旧记录再重新推送
                logger.warning(
                    f"Source {source_ip} in bad state={state}, deleting old record "
                    f"and re-pushing agent"
                )
                try:
                    self.sms.hcloud.sms_delete_source(source_id)
                    logger.info(f"Deleted old source record: {source_id}")
                    time.sleep(3)
                except Exception as e:
                    logger.warning(f"Failed to delete old source {source_id}: {e}")
            else:
                logger.info(f"Source registered but state={state}, waiting...")
                if self.sms.wait_source_online(source_id, timeout=120):
                    result["success"] = True
                    result["source_id"] = source_id
                    # 重新查询获取最新源端信息
                    # Issue 22 修复: 用 ShowServer 获取完整源端信息 (含 LVM 信息)
                    full_info = self.sms.hcloud.sms_show_source(source_id)
                    result["source_info"] = full_info if full_info else self.sms.find_source_by_ip(source_ip)
                    return result
                else:
                    # 等待超时，源端可能 Agent 配置不完整，删除后重新推送
                    logger.warning(
                        f"Source {source_ip} wait_online timeout (state={state}), "
                        f"deleting and re-pushing agent"
                    )
                    try:
                        self.sms.hcloud.sms_delete_source(source_id)
                        logger.info(f"Deleted stale source record: {source_id}")
                        time.sleep(3)
                    except Exception as e:
                        logger.warning(f"Failed to delete stale source {source_id}: {e}")

        # 需要推送 Agent
        logger.info("Agent not found or offline, pushing...")

        # 传递 per-task GOST SSH 端口 (线程安全: 作为参数传入, 不修改共享实例属性)
        task_gost_port = task.get("gost_ssh_port")
        if task_gost_port:
            logger.info(f"Using GOST SSH port {task_gost_port} for source {source_ip}")

        push_result = self.agent_pusher.full_push(
            source_username=task.get("source_username", "root"),
            source_password=task.get("source_password"),
            source_key_path=task.get("source_key_path"),
            source_port=task.get("source_port", 22),
            region=self.config.get("region", "cn-north-1"),
            ak=task.get("ak"),
            sk=task.get("sk"),
            local_agent_path=task.get("local_agent_path"),
            agent_url=task.get("agent_url"),
            timeout=600,
            gost_ssh_port=task_gost_port,
        )

        if not push_result["success"]:
            result["error"] = f"Agent push failed: {push_result['error']}"
            return result

        # 等待源端注册 (缩短等待时间, Agent 注册通常很快)
        time.sleep(5)
        source = self.sms.find_source_by_ip(source_ip)
        if source:
            source_id = source.get("id", "")
            if self.sms.wait_source_online(source_id, timeout=180):
                result["success"] = True
                result["source_id"] = source_id
                # Issue 22 修复: 用 ShowServer 获取完整源端信息 (含 LVM 信息)
                full_info = self.sms.hcloud.sms_show_source(source_id)
                result["source_info"] = full_info if full_info else source
                return result

        # Issue 30 修复: Agent 已安装但源端未在 SMS 注册
        # 原因: 上次迁移的 Agent 仍在运行，但源端记录已被删除 (SMS.8109)
        # 或 Agent 采集后磁盘信息变更导致注册失效
        # 解决: 强制 kill 旧 Agent → 清理配置 → 重新下发 → 等待重新注册
        logger.warning(
            f"Source {source_ip} not registered in SMS after agent push, "
            f"forcing agent restart..."
        )
        try:
            # 1. SSH 到源端 (通过 GOST 隧道)
            task_gost_port = task.get("gost_ssh_port")
            effective_port = task_gost_port if task_gost_port else self.agent_pusher.gost_ssh_port
            ssh_conn = self.agent_pusher.ssh.connect(
                host=self.agent_pusher.proxy_ip,
                port=effective_port,
                username=task.get("source_username", "root"),
                password=task.get("source_password"),
                key_path=task.get("source_key_path"),
            )
            if ssh_conn:
                # 2. Kill 旧 Agent 进程
                kill_cmds = [
                    "kill -9 $(pgrep -f 'linuxmain') 2>/dev/null; true",
                    "kill -9 $(pgrep -f 'sms_agent') 2>/dev/null; true",
                    "kill -9 $(pgrep -f 'SMS-Agent') 2>/dev/null; true",
                ]
                for kc in kill_cmds:
                    self.agent_pusher.ssh.execute(ssh_conn, kc, timeout=5)
                logger.info(f"Killed old agent processes on {source_ip}")

                # 3. 清理 Agent 配置 (只删除源端注册相关文件，保留 error.cfg 等默认配置)
                clean_cmds = [
                    "rm -f /opt/SMS-Agent/agent/config/agent_conf.json 2>/dev/null; true",
                    "rm -f /opt/SMS-Agent/config/sms_domain.txt 2>/dev/null; true",
                    "rm -rf /tmp/SMS-Agent* 2>/dev/null; true",
                ]
                for cc in clean_cmds:
                    self.agent_pusher.ssh.execute(ssh_conn, cc, timeout=5)
                logger.info(f"Cleaned agent config on {source_ip}")

                # 4. 重新下发 Agent (此时状态为 INSTALLED_NOT_CONFIGURED → 会重新配置+启动)
                self.agent_pusher.ssh.disconnect(ssh_conn)

                time.sleep(3)
                push_result2 = self.agent_pusher.full_push(
                    source_username=task.get("source_username", "root"),
                    source_password=task.get("source_password"),
                    source_key_path=task.get("source_key_path"),
                    source_port=task.get("source_port", 22),
                    region=self.config.get("region", "cn-north-1"),
                    ak=task.get("ak"),
                    sk=task.get("sk"),
                    local_agent_path=task.get("local_agent_path"),
                    agent_url=task.get("agent_url"),
                    timeout=600,
                    gost_ssh_port=task_gost_port,
                )
                logger.info(
                    f"Agent re-push result: success={push_result2.get('success')}, "
                    f"action={push_result2.get('action')}, state={push_result2.get('state')}"
                )

                if push_result2.get("success"):
                    # 5. 等待重新注册
                    time.sleep(10)
                    source = self.sms.find_source_by_ip(source_ip)
                    if source:
                        source_id = source.get("id", "")
                        if self.sms.wait_source_online(source_id, timeout=180):
                            result["success"] = True
                            result["source_id"] = source_id
                            full_info = self.sms.hcloud.sms_show_source(source_id)
                            result["source_info"] = full_info if full_info else source
                            logger.info(
                                f"Source re-registered successfully: {source_id}"
                            )
                            return result
        except Exception as e:
            logger.error(f"Force agent restart failed: {e}")

        result["error"] = "Agent installed but source not registered in SMS (even after force restart)"
        return result

    # ──────────────────────────────────────────────────────
    #  迁移执行 (两阶段拆分: prepare + migrate)
    # ──────────────────────────────────────────────────────

    def _prepare_phase(self, task: Dict[str, Any], task_logger=None, tlog=None,
                       step_tracker: StepTracker = None) -> Dict[str, Any]:
        """准备阶段: ensure_agent → ensure_target_ecs

        并行优化: 如果 target_server_id 已存在, ensure_agent 和 ensure_target_ecs 并行执行。
        否则顺序执行 (ensure_target_ecs 需要 source_server_id 匹配规格)。

        Args:
            task: 迁移任务
            task_logger: MigrationLogger 实例 (可选)
            tlog: task logger (可选)
            step_tracker: StepTracker 实例 (可选, 用于记录步骤耗时/阻塞/问题)

        Returns:
            {"success": bool, "source_id": str, "target_server_id": str, ...}
        """
        if tlog is None:
            tlog = logger

        result = {
            "success": False,
            "source_id": "",
            "target_server_id": task.get("target_server_id", ""),
            "target_private_ip": "",
            "target_disks": None,
            "target_server_name": "",
            "created": False,
        }

        # v2.5.0 优化1: Phase A 内部并行化
        # 如果 target_server_id 已存在, ensure_agent 和 ensure_target_ecs 可并行执行
        # 否则顺序执行 (ensure_target_ecs 创建新 ECS 需要 source_server_id 匹配规格)
        existing_target_id = bool(task.get("target_server_id"))

        if existing_target_id:
            # ── 并行模式: ensure_agent ∥ ensure_target_ecs ──
            tlog.info("Phase A parallel mode: target ECS exists, running ensure_agent ∥ ensure_target_ecs")
            if task_logger:
                task_logger.step("ensure_agent", "start")
                task_logger.step("ensure_target", "start")
            if step_tracker:
                step_tracker.start("ensure_agent")
                step_tracker.start("ensure_target")

            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=2) as pool:
                fut_agent = pool.submit(self.ensure_agent, task)
                fut_target = pool.submit(self.ensure_target_ecs, task)
                agent_result = fut_agent.result()
                target_result = fut_target.result()

            # 处理 agent 结果
            if not agent_result["success"]:
                result["error"] = f"Agent setup failed: {agent_result['error']}"
                if task_logger:
                    task_logger.step("ensure_agent", "failed", {"error": result["error"]})
                if step_tracker:
                    step_tracker.end("ensure_agent", success=False, error=result["error"])
                    step_tracker.end("ensure_target", success=False, error="skipped due to agent failure")
                return result
            result["source_id"] = agent_result["source_id"]
            task["source_server_id"] = agent_result["source_id"]
            task["sms_source_info"] = agent_result.get("source_info")
            if task_logger:
                task_logger.step("ensure_agent", "success", {"source_id": result["source_id"]})
            if step_tracker:
                step_tracker.end("ensure_agent", success=True)

            # 处理 target 结果
            if not target_result["success"]:
                result["error"] = f"Target ECS setup failed: {target_result['error']}"
                if task_logger:
                    task_logger.step("ensure_target", "failed", {"error": result["error"]})
                if step_tracker:
                    step_tracker.end("ensure_target", success=False, error=result["error"])
                return result
        else:
            # ── 顺序模式: ensure_agent → ensure_target_ecs (需要 source_server_id) ──
            # Phase 0: 确保 Agent
            if task_logger:
                task_logger.step("ensure_agent", "start")
            if step_tracker:
                step_tracker.start("ensure_agent")
            agent_result = self.ensure_agent(task)
            if not agent_result["success"]:
                result["error"] = f"Agent setup failed: {agent_result['error']}"
                if task_logger:
                    task_logger.step("ensure_agent", "failed", {"error": result["error"]})
                if step_tracker:
                    step_tracker.end("ensure_agent", success=False, error=result["error"])
                return result
            result["source_id"] = agent_result["source_id"]
            task["source_server_id"] = agent_result["source_id"]
            task["sms_source_info"] = agent_result.get("source_info")
            if task_logger:
                task_logger.step("ensure_agent", "success", {"source_id": result["source_id"]})
            if step_tracker:
                step_tracker.end("ensure_agent", success=True)

            # Phase 1: 确保目标 ECS 存在
            if task_logger:
                task_logger.step("ensure_target", "start")
            if step_tracker:
                step_tracker.start("ensure_target")
            target_result = self.ensure_target_ecs(task)
            if not target_result["success"]:
                result["error"] = f"Target ECS setup failed: {target_result['error']}"
                if task_logger:
                    task_logger.step("ensure_target", "failed", {"error": result["error"]})
                if step_tracker:
                    step_tracker.end("ensure_target", success=False, error=result["error"])
                return result

        # 公共结果处理 (并行和顺序模式共用)
        result["target_server_id"] = target_result["target_server_id"]
        result["created"] = target_result.get("created", False)
        result["target_private_ip"] = target_result.get("target_private_ip", "")
        result["target_disks"] = target_result.get("target_disks")
        result["target_server_name"] = target_result.get("target_server_name", "")

        # 更新 task
        task["target_server_id"] = result["target_server_id"]
        if result["target_private_ip"]:
            task["target_private_ip"] = result["target_private_ip"]
            task["migration_ip"] = result["target_private_ip"]
        if result["target_disks"]:
            task["target_disks"] = result["target_disks"]
        if result["target_server_name"]:
            task["target_server_name"] = result["target_server_name"]

        if task_logger:
            task_logger.step("ensure_target", "success", {"target_server_id": result["target_server_id"]})
        if step_tracker:
            step_tracker.end("ensure_target", success=True)
        if result["created"]:
            tlog.info(f"Target ECS auto-created: {result['target_server_id']}")

        result["success"] = True
        return result

    def _migrate_phase(self, task: Dict[str, Any], prepare_result: Dict[str, Any],
                       task_logger=None, tlog=None,
                       step_tracker: StepTracker = None) -> Dict[str, Any]:
        """迁移阶段: pre_check → create_task → migrating → verify

        Args:
            task: 迁移任务 (已通过 _prepare_phase 更新)
            prepare_result: _prepare_phase 的返回结果
            task_logger: MigrationLogger 实例 (可选)
            tlog: task logger (可选)
            step_tracker: StepTracker 实例 (可选, 用于记录步骤耗时/阻塞/问题)

        Returns:
            迁移结果 (始终返回 dict)
        """
        if tlog is None:
            tlog = logger

        source_ip = task.get("source_ip", "")
        target_server_id = task.get("target_server_id", "")
        agent_result = {"source_id": prepare_result.get("source_id", ""), "source_info": task.get("sms_source_info")}

        result = {
            "source_ip": source_ip,
            "target_server_id": target_server_id,
            "task_name": task.get("task_name", ""),
            "success": False,
            "phase": "migrate",
            "error": "",
            "duration": 0,
            "task_id": "",
            "source_id": prepare_result.get("source_id", ""),
        }

        try:
            # Phase 1b: GOST 数据流转发更新 (如果目标 ECS 是新创建的)
            # 注意: 在两阶段模式下, 此步骤由 batch_migrate.py 批量执行
            # 仅在单任务模式 (非批量) 下执行
            if task.get("_single_task_mode") and prepare_result.get("created") and self.proxy_ops:
                if task_logger:
                    task_logger.step("update_gost_forward", "start")
                if step_tracker:
                    step_tracker.start("update_gost_forward")
                result["phase"] = "update_gost_forward"
                target_private_ip = task.get("target_private_ip", "")
                if not target_private_ip:
                    ecs_info = self.ecs.find_by_id(target_server_id)
                    if ecs_info:
                        addresses = ecs_info.get("addresses", {})
                        for net_name, addr_list in addresses.items():
                            for addr in (addr_list if isinstance(addr_list, list) else [addr_list]):
                                if isinstance(addr, dict) and addr.get("OS-EXT-IPS:type") == "fixed":
                                    target_private_ip = addr.get("addr", "")
                                    break
                            if target_private_ip:
                                break
                if target_private_ip:
                    tlog.info(f"Updating GOST data forward to target {target_private_ip}")
                    gost_data_ports = task.get("gost_data_ports", [8899, 8900])
                    gost_data_local_ports = task.get("gost_data_local_ports", gost_data_ports)
                    if self.proxy_ops.update_target_forward(
                        target_private_ip,
                        data_ports=gost_data_ports,
                        local_ports=gost_data_local_ports,
                    ):
                        task["target_private_ip"] = target_private_ip
                        task["migration_ip"] = target_private_ip
                        if task_logger:
                            task_logger.step("update_gost_forward", "success", {"target_private_ip": target_private_ip})
                        if step_tracker:
                            step_tracker.end("update_gost_forward", success=True)
                    else:
                        tlog.warning("GOST forward update failed")
                        if task_logger:
                            task_logger.step("update_gost_forward", "failed", {"error": "GOST forward update failed"})
                        if step_tracker:
                            step_tracker.end("update_gost_forward", success=False, error="GOST forward update failed")
                            step_tracker.record_issue("update_gost_forward", "GOST forward update failed", severity="error")
                else:
                    tlog.warning("Could not determine target ECS private IP for GOST forward")
                    if task_logger:
                        task_logger.step("update_gost_forward", "skipped", {"reason": "no_private_ip"})
                    if step_tracker:
                        step_tracker.end("update_gost_forward", success=True)
                        step_tracker.record_issue("update_gost_forward", "Could not determine target ECS private IP, GOST forward skipped")

            # Phase 2: 前置检查
            if task_logger:
                task_logger.step("pre_check", "start")
            if step_tracker:
                step_tracker.start("pre_check")
            result["phase"] = "pre_check"
            pre = self.pre_check(task)
            if not pre["passed"]:
                result["error"] = f"Pre-check failed: {'; '.join(pre['errors'])}"
                if task_logger:
                    task_logger.step("pre_check", "failed", {"errors": pre["errors"]})
                if step_tracker:
                    step_tracker.end("pre_check", success=False, error=str(pre["errors"]))
                return result
            if pre["warnings"]:
                tlog.warning(f"Pre-check warnings: {pre['warnings']}")
                if step_tracker:
                    step_tracker.record_issue("pre_check", f"Warnings: {pre['warnings']}")
            if task_logger:
                task_logger.step("pre_check", "success")
            if step_tracker:
                step_tracker.end("pre_check", success=True)

            # Phase 3: 创建迁移任务
            if task_logger:
                task_logger.step("create_task", "start")
            if step_tracker:
                step_tracker.start("create_task")
            result["phase"] = "create_task"
            migration_type = task.get("migration_type", "MIGRATE_FILE")
            use_public_ip = False  # 强制私网

            target_disks = task.get("target_disks", None)
            if target_disks:
                for i, d in enumerate(target_disks, 1):
                    pvs = d.get("physical_volumes", [])
                    vgs = d.get("volume_groups", [])
                    tlog.info(f"Target disk {i}: size={d.get('size')}GB, "
                              f"disk_id={d.get('disk_id', 'N/A')}, "
                              f"device_use={d.get('device_use', 'N/A')}, "
                              f"PVs={len(pvs)}, VGs={len(vgs)}")

            os_type = task.get("os_type", "Linux")
            project_id = task.get("project_id", "")
            project_name = task.get("project_name", "")
            region_id = task.get("region_id", "")
            region_name = task.get("region_name", "")
            target_server_name = task.get("target_server_name", "")
            syncing = task.get("syncing", False)
            migration_ip = task.get("migration_ip", "")

            # 合并 source PV 字段到 target_disks (与原 execute_migration 逻辑一致)
            # 注意: _build_target_disks_from_existing 已完整复制 PV/VG 信息（含所有字段），
            # 此处的 index-based 合并仅填充缺失字段，对已完整 PV 是 no-op。
            # 对新建 ECS 场景，target_disks 顺序与源端一致，index 匹配正确。
            if target_disks and task.get("sms_source_info"):
                try:
                    init_target = task["sms_source_info"].get("init_target_server", {})
                    src_disks = init_target.get("disks", [])
                    for i, td in enumerate(target_disks):
                        if i < len(src_disks):
                            src_disk = src_disks[i]
                            src_pvs = src_disk.get("physical_volumes", [])
                            td_pvs = td.get("physical_volumes", [])
                            for j, tpv in enumerate(td_pvs):
                                if j < len(src_pvs):
                                    spv = src_pvs[j]
                                    for field in ["device_use", "file_system", "mount_point", "index"]:
                                        if field not in tpv and spv.get(field) is not None:
                                            tpv[field] = spv[field]
                    tlog.info("Merged source PV fields into target_disks")
                except Exception as e:
                    tlog.warning(f"Failed to merge source PV fields: {e}")

            task_info = self.sms.create_migration_task(
                source_id=prepare_result.get("source_id", ""),
                target_server_id=target_server_id,
                task_name=task.get("task_name", ""),
                migration_type=migration_type,
                use_public_ip=use_public_ip,
                region=self.config.get("region"),
                target_disks=target_disks,
                exist_server=True,
                os_type=os_type,
                project_id=project_id,
                project_name=project_name,
                region_id=region_id,
                region_name=region_name,
                target_server_name=target_server_name,
                syncing=syncing,
                migration_ip=migration_ip,
            )
            if not task_info:
                result["error"] = "Failed to create migration task"
                if task_logger:
                    task_logger.step("create_task", "failed", {"error": result["error"]})
                if step_tracker:
                    step_tracker.end("create_task", success=False, error=result["error"])
                return result
            result["task_id"] = task_info.get("id", "")
            if task_logger:
                task_logger.step("create_task", "success", {"task_id": result["task_id"]})
            if step_tracker:
                step_tracker.end("create_task", success=True)

            # Phase 4: 启动并监控迁移
            if task_logger:
                task_logger.step("migrating", "start")
            if step_tracker:
                step_tracker.start("migrating")
            result["phase"] = "migrating"
            timeout = task.get("migration_timeout", 7200)
            monitor_result = self.sms.start_and_monitor(
                result["task_id"],
                timeout=timeout,
                interval=30,
            )
            result["duration"] = monitor_result.get("duration", 0)

            if not monitor_result["completed"]:
                result["error"] = f"Migration failed: {monitor_result.get('error', '')}"
                diagnosis = self.sms.diagnose_error(result["task_id"])
                result["diagnosis"] = diagnosis
                tlog.error(f"Migration failed: {result['error']}")
                if diagnosis:
                    tlog.info(f"Diagnosis: {diagnosis}")
                if step_tracker:
                    step_tracker.end("migrating", success=False, error=result["error"])
                    step_tracker.record_issue("migrating", result["error"], severity="error")
                return result

            tlog.info(f"Migration completed in {result['duration']}s")
            if step_tracker:
                step_tracker.end("migrating", success=True)

            # Phase 5: 验证
            if task_logger:
                task_logger.step("verify", "start")
            if step_tracker:
                step_tracker.start("verify")
            result["phase"] = "verify"
            if self.verify_migration(task, result["task_id"]):
                result["success"] = True
                if task_logger:
                    task_logger.step("verify", "success")
                if step_tracker:
                    step_tracker.end("verify", success=True)
            else:
                result["error"] = "Verification failed"
                if task_logger:
                    task_logger.step("verify", "failed", {"error": result["error"]})
                if step_tracker:
                    step_tracker.end("verify", success=False, error=result["error"])

        except Exception as e:
            result["error"] = f"Exception: {str(e)}"
            tlog.exception(f"Migration exception for {source_ip}")
            if task_logger:
                task_logger.step(result.get("phase", "unknown"), "exception", {"error": str(e)})

        return result

    def execute_migration(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行完整迁移 (两阶段模式: prepare + migrate)

        兼容旧接口: 内部调用 _prepare_phase + _migrate_phase。
        batch_migrate.py 可分别调用两个阶段以实现批量 GOST 转发优化。

        Args:
            task: 迁移任务参数

        Returns:
            迁移结果 (始终返回 dict，不抛异常)
        """
        source_ip = task.get("source_ip", "")
        target_server_id = task.get("target_server_id", "")
        if task.get("task_name"):
            task_name = sanitize_task_name(task.get("task_name"))
        else:
            task_name = generate_task_name_from_ip(source_ip)
        task["task_name"] = task_name

        # 创建每任务独立日志
        safe_ip = source_ip.replace(".", "_") if source_ip else "unknown"
        task_log_id = f"{safe_ip}_{int(time.time())}"
        task_logger = MigrationLogger(
            log_dir=self.log_dir,
            task_id=task_log_id,
            level=logging.INFO,
        )
        tlog = task_logger.get_logger()

        tlog.info(f"=== Starting migration: {source_ip} -> {target_server_id} ===")
        tlog.info(f"Task name: {task_name}, log file: {task_logger.get_log_path()}")

        # 创建步骤追踪器
        step_tracker = StepTracker()

        result = {
            "source_ip": source_ip,
            "target_server_id": target_server_id,
            "task_name": task_name,
            "success": False,
            "phase": "",
            "error": "",
            "duration": 0,
            "task_id": "",
            "source_id": "",
            "log_file": task_logger.get_log_path(),
            "step_tracking": None,
        }

        start_time = time.time()

        try:
            # 标记单任务模式 (执行 GOST 数据转发更新)
            task["_single_task_mode"] = True

            # Phase A: 准备阶段
            result["phase"] = "prepare"
            prepare_result = self._prepare_phase(task, task_logger, tlog, step_tracker)
            if not prepare_result["success"]:
                result["error"] = prepare_result.get("error", "Prepare phase failed")
                result["step_tracking"] = step_tracker.get_summary()
                return result
            result["source_id"] = prepare_result["source_id"]
            result["target_server_id"] = prepare_result["target_server_id"]

            # Phase B: 迁移阶段
            result["phase"] = "migrate"
            migrate_result = self._migrate_phase(task, prepare_result, task_logger, tlog, step_tracker)
            result.update(migrate_result)
            result["source_ip"] = source_ip
            result["task_name"] = task_name
            result["log_file"] = task_logger.get_log_path()

        except Exception as e:
            result["error"] = f"Exception: {str(e)}"
            tlog.exception(f"Migration exception for {source_ip}")
            task_logger.step(result.get("phase", "unknown"), "exception", {"error": str(e)})

        result["duration"] = round(time.time() - start_time, 1)
        result["step_tracking"] = step_tracker.get_summary()
        tlog.info(f"Migration result: success={result['success']}, duration={result['duration']}s, "
                  f"phase={result['phase']}")
        tlog.info(step_tracker.get_console_text())
        return result

    # ──────────────────────────────────────────────────────
    #  迁移验证
    # ──────────────────────────────────────────────────────

    def verify_migration(self, task: Dict[str, Any], task_id: str) -> bool:
        """迁移后验证

        Args:
            task: 任务参数
            task_id: SMS 任务 ID

        Returns:
            验证是否通过
        """
        # 1. 检查 SMS 任务状态
        # SMS API 可能返回: MIGRATE_SUCCESS, SUCCESS, SUCCEED, COMPLETE, DONE
        progress = self.sms.get_task_progress(task_id)
        _success_states = ("SUCCESS", "SUCCEED", "MIGRATE_SUCCESS", "COMPLETE", "DONE")
        if progress["state"] not in _success_states:
            logger.error(f"Task not in success state: {progress['state']} (expected one of {_success_states})")
            return False
        logger.info(f"SMS task state verified: {progress['state']}")

        # 2. 检查目标 ECS 状态
        target_server_id = task.get("target_server_id", "")
        ecs_state = self.ecs.get_state(target_server_id)
        if ecs_state not in ("ACTIVE", "STOPPED"):
            logger.error(f"Target ECS in unexpected state: {ecs_state}")
            return False

        # 3. 多数据盘验证: 检查目标 ECS 磁盘数量与预期一致
        target_disks = task.get("target_disks", [])
        if target_disks:
            target_volumes = self.ecs.list_volumes(target_server_id)
            actual_count = len(target_volumes) if target_volumes else 0
            expected_count = len(target_disks)
            if actual_count > 0 and actual_count != expected_count:
                logger.error(
                    f"Post-migration disk count mismatch: actual={actual_count}, "
                    f"expected={expected_count}. Data disks may not have migrated correctly."
                )
                return False
            # 验证每块磁盘大小
            if target_volumes:
                for i, expected_disk in enumerate(target_disks):
                    if i < len(target_volumes):
                        actual_size = target_volumes[i].get("size", 0)
                        expected_size = expected_disk.get("size", 0)
                        if actual_size > 0 and expected_size > 0 and actual_size < expected_size:
                            logger.warning(
                                f"Disk {i+1} size mismatch: actual={actual_size} GB, "
                                f"expected>={expected_size} GB"
                            )
            logger.info(f"Multi-disk verification passed: {actual_count} disks verified")

        # 4. 深度数据完整性校验 (可选, 需要 SSH 凭据)
        deep_verify = task.get("deep_verify", False)
        if deep_verify and _HAS_POST_VERIFY:
            logger.info("Starting deep post-migration verification...")
            deep_result = self._run_deep_verification(task)
            if deep_result:
                task["deep_verify_result"] = deep_result
                if not deep_result.get("passed", False):
                    logger.error("Deep verification FAILED — data integrity issues detected")
                    return False
                logger.info("Deep verification PASSED — all integrity checks OK")
            else:
                logger.warning("Deep verification could not run (missing SSH credentials)")
        elif deep_verify and not _HAS_POST_VERIFY:
            logger.warning("Deep verification requested but post_migration_verify module not available")

        # 4.5 P3-7优化: 自动轻量验证 (SSH/磁盘/服务)
        # 当 SSH 凭据可用时自动运行，不需要 deep_verify=True
        auto_verify = task.get("auto_verify", True)
        if auto_verify and not deep_verify:
            self._auto_verify_post_migration(task)

        # 5. 基础验证通过
        logger.info("Migration verification passed")
        return True

    def _auto_verify_post_migration(self, task: Dict[str, Any]):
        """P3-7优化: 迁移后自动轻量验证

        尝试 SSH 连接目标 ECS，检查基本健康指标:
        - SSH 连通性
        - 磁盘挂载状态
        - sshd 服务状态
        - 网络接口状态

        结果仅记录为 info/warning，不影响迁移成功判定。
        """
        target_ip = task.get("target_private_ip", "") or task.get("target_ip", "")
        if not target_ip:
            return

        target_password = task.get("target_password", "") or task.get("source_password", "")
        target_user = task.get("target_user", "root")
        target_port = task.get("target_port", 22)

        # 私网场景: 通过代理 SSH 连接
        proxy_config = self.config.get("proxy", {})
        proxy_ip = proxy_config.get("ip", "") or self.config.get("proxy_ip", "")
        proxy_port = proxy_config.get("port", 22)
        proxy_user = proxy_config.get("user", "root")
        proxy_password = proxy_config.get("password", "")
        proxy_key = proxy_config.get("key_path", "") or self.config.get("proxy_key_path", "")

        import paramiko

        ssh = None
        try:
            if proxy_ip:
                # 通过代理跳转
                proxy_ssh = paramiko.SSHClient()
                proxy_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                proxy_ssh.connect(
                    proxy_ip, port=proxy_port,
                    username=proxy_user,
                    password=proxy_password or None,
                    key_filename=proxy_key or None,
                    timeout=10,
                )
                transport = proxy_ssh.get_transport()
                dest_addr = (target_ip, target_port)
                local_addr = ("127.0.0.1", 0)
                channel = transport.open_channel("direct-tcpip", dest_addr, local_addr)
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    target_ip, port=target_port,
                    username=target_user,
                    password=target_password or None,
                    sock=channel,
                    timeout=10,
                )
                proxy_ssh.close()
            else:
                # 直连
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    target_ip, port=target_port,
                    username=target_user,
                    password=target_password or None,
                    timeout=10,
                )

            logger.info("P3-7: Auto-verify SSH connection to target ECS successful")

            def _run_cmd(cmd):
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
                return stdout.read().decode().strip(), stderr.read().decode().strip()

            # 检查磁盘挂载
            mounts_out, _ = _run_cmd("mount | grep -v 'tmpfs\|proc\|sysfs' | wc -l")
            logger.info(f"P3-7: Mounted filesystems count: {mounts_out}")

            # 检查 sshd 服务
            sshd_out, _ = _run_cmd("systemctl is-active sshd 2>/dev/null || systemctl is-active ssh 2>/dev/null || echo unknown")
            if sshd_out == "active":
                logger.info("P3-7: sshd service is active")
            else:
                logger.warning(f"P3-7: sshd service status: {sshd_out}")

            # 检查网络接口
            net_out, _ = _run_cmd("ip -o addr show | grep -v 'lo\\|inet6' | wc -l")
            logger.info(f"P3-7: Network interfaces with IP: {net_out}")

            # 检查根分区使用率
            disk_out, _ = _run_cmd("df / | tail -1 | awk '{print $5}'")
            if disk_out and disk_out.endswith("%"):
                usage = int(disk_out.rstrip("%"))
                if usage > 90:
                    logger.warning(f"P3-7: Root partition usage high: {disk_out}")
                else:
                    logger.info(f"P3-7: Root partition usage: {disk_out}")

            logger.info("P3-7: Auto-verification completed")

        except Exception as e:
            logger.warning(f"P3-7: Auto-verify skipped (SSH connection failed: {e})")
        finally:
            if ssh:
                try:
                    ssh.close()
                except Exception:
                    pass

    def _run_deep_verification(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """执行深度迁移后数据完整性校验

        从 task 和 config 中提取 SSH 连接信息，调用 PostMigrationVerifier。

        Args:
            task: 任务参数

        Returns:
            校验结果 dict, 或 None (无法执行)
        """
        try:
            # 目标 ECS 信息
            target_ip = task.get("target_private_ip", "") or task.get("target_ip", "")
            target_password = task.get("target_password", "") or task.get("source_password", "")
            target_user = task.get("target_user", "root")
            target_port = task.get("target_port", 22)

            if not target_ip:
                logger.warning("No target IP for deep verification")
                return None

            # 代理 ECS 信息 (私网场景)
            proxy_config = self.config.get("proxy", {})
            proxy_ip = proxy_config.get("ip", "") or self.config.get("proxy_ip", "")
            proxy_port = proxy_config.get("port", 22)
            proxy_user = proxy_config.get("user", "root")
            proxy_password = proxy_config.get("password", "")

            # 源端信息 (可选, 用于对比)
            source_ip = task.get("source_ip", "")
            source_password = task.get("source_password", "")
            source_user = task.get("source_user", "root")
            source_port = task.get("source_port", 22)

            # 预期值
            expected_hostname = task.get("source_name", "") or task.get("expected_hostname", "")
            expected_os = task.get("expected_os", "")
            expected_kernel = task.get("expected_kernel", "")

            verifier = PostMigrationVerifier(
                target_ip=target_ip,
                target_port=target_port,
                target_user=target_user,
                target_password=target_password if target_password else None,
                proxy_ip=proxy_ip if proxy_ip else None,
                proxy_port=proxy_port,
                proxy_user=proxy_user,
                proxy_password=proxy_password if proxy_password else None,
                source_ip=source_ip if source_ip else None,
                source_port=source_port,
                source_user=source_user,
                source_password=source_password if source_password else None,
                expected_hostname=expected_hostname if expected_hostname else None,
                expected_os=expected_os if expected_os else None,
                expected_kernel=expected_kernel if expected_kernel else None,
            )

            result = verifier.verify()

            # 保存报告
            log_dir = self.log_dir
            report_path = verifier.save_report(result)
            logger.info(f"Deep verification report saved: {report_path}")

            return result

        except Exception as e:
            logger.error(f"Deep verification exception: {e}")
            return None

    # ──────────────────────────────────────────────────────
    #  回滚
    # ──────────────────────────────────────────────────────

    def rollback(self, result: Dict[str, Any]) -> bool:
        """迁移失败回滚

        Args:
            result: 迁移结果

        Returns:
            回滚是否成功
        """
        task_id = result.get("task_id", "")
        if task_id:
            logger.info(f"Rolling back: deleting SMS task {task_id}")
            return self.sms.hcloud.sms_delete_task(task_id)
        return True
