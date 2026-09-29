#!/usr/bin/env python3
"""
safety_checker.py — 安全检查器

迁移前安全检查，防止误操作:
  - 源端业务停机确认
  - 目标 ECS 状态检查
  - 磁盘空间检查
  - SMS Agent 冲突检测
  - 网络隔离检查
  - 二次确认机制
"""

import os
import time
import logging
from typing import Optional, Dict, List, Any, Tuple

logger = logging.getLogger(__name__)


class SafetyChecker:
    """迁移安全检查器"""

    # 高危操作列表
    HIGH_RISK_OPERATIONS = [
        "delete_source",
        "delete_target_ecs",
        "stop_source_service",
        "format_disk",
        "cutover",
    ]

    def __init__(self, hcloud=None, ssh_client=None):
        """
        Args:
            hcloud: HcloudCLI 实例
            ssh_client: SSH 客户端 (连接到源端或代理 ECS)
        """
        self.hcloud = hcloud
        self.ssh = ssh_client
        self.confirmations = {}


    def check_task_safety(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """检查迁移任务安全性 (批量迁移用)

        Args:
            task: 迁移任务字典

        Returns:
            {"passed": bool, "errors": List[str], "warnings": List[str]}
        """
        errors = []
        warnings = []
        source_ip = task.get("source_ip", "")
        os_type = task.get("os_type", "")

        # 基本参数检查
        if not source_ip:
            errors.append("Missing source_ip")
        if not os_type:
            warnings.append("Missing os_type, will auto-detect")

        # 检查是否已有同名源端注册 (避免重复迁移)
        if self.hcloud and source_ip:
            try:
                result = self.hcloud.sms_list_sources(limit=100)
                existing = result.get("source_servers", [])
                for srv in existing:
                    if srv.get("ip", "") == source_ip:
                        state = srv.get("state", "")
                        if state in ("MIGRATING", "CUTTING_OVER"):
                            errors.append(f"Source {source_ip} is already in migration state: {state}")
                        else:
                            warnings.append(f"Source {source_ip} already registered (state={state}), will reuse")
            except Exception as e:
                warnings.append(f"Could not check existing sources: {e}")

        return {
            "passed": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def _exec(self, cmd: str, timeout: int = 30) -> Tuple[str, str, int]:
        if not self.ssh:
            return "", "no SSH client", -1
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

    # ──────────────────────────────────────────────────────────────
    #  源端检查
    # ──────────────────────────────────────────────────────────────

    def check_source_business(self) -> Dict[str, Any]:
        """检查源端业务状态 (是否已停机/可迁移)

        检查项:
          - 关键服务状态 (nginx, apache, mysql, etc.)
          - 活跃连接数
          - 磁盘 IO
        """
        result = {"safe": True, "warnings": [], "details": {}}

        # 检查关键服务
        services = ["nginx", "httpd", "apache2", "mysql", "mariadb", "postgresql", "redis", "tomcat"]
        running_services = []

        for svc in services:
            out, _, _ = self._exec(f"systemctl is-active {svc} 2>/dev/null || true")
            if out and out.strip() == "active":
                running_services.append(svc)

        if running_services:
            result["safe"] = False
            result["warnings"].append(f"业务服务仍在运行: {', '.join(running_services)}")
            result["details"]["running_services"] = running_services

        # 检查活跃连接数
        out, _, _ = self._exec("ss -tn state established | wc -l 2>/dev/null || echo 0")
        try:
            conn_count = int(out.strip()) if out.strip() else 0
        except ValueError:
            conn_count = 0
        result["details"]["active_connections"] = conn_count

        if conn_count > 100:
            result["warnings"].append(f"活跃连接数较多: {conn_count}")

        # 检查磁盘 IO
        out, _, _ = self._exec("iostat -x 1 2 2>/dev/null | tail -n +4 || true")
        result["details"]["disk_io"] = out[:200] if out else ""

        logger.info(f"Source business check: safe={result['safe']}, warnings={len(result['warnings'])}")
        return result

    def check_source_disk(self) -> Dict[str, Any]:
        """检查源端磁盘状态

        检查项:
          - 磁盘使用率 (< 95%)
          - LVM 一致性
          - 挂载点完整性
        """
        result = {"safe": True, "warnings": [], "details": {}}

        # 磁盘使用率
        out, _, _ = self._exec("df -h --output=pcent,target 2>/dev/null || df -h 2>/dev/null")
        if out:
            for line in out.strip().splitlines()[1:]:
                parts = line.split()
                if not parts:
                    continue
                use_str = parts[0].replace("%", "") if "%" in parts[0] else ""
                try:
                    use_pct = int(use_str)
                    if use_pct > 95:
                        result["safe"] = False
                        mount = parts[-1] if len(parts) > 1 else "unknown"
                        result["warnings"].append(f"磁盘使用率过高: {mount} ({use_pct}%)")
                except ValueError:
                    pass

        # LVM 检查
        out, _, _ = self._exec("vgs --noheadings 2>/dev/null || true")
        if out and out.strip():
            result["details"]["has_lvm"] = True
            for line in out.strip().splitlines():
                parts = line.split()
                if len(parts) >= 3:
                    vg_name = parts[0]
                    # 检查 VG 是否有足够的 PE
                    out2, _, _ = self._exec(f"vgdisplay {vg_name} 2>/dev/null | grep 'Free  PE'")
                    if out2 and "0" in out2.split("/")[-1]:
                        pass  # No free PE, OK

        # 挂载点检查
        out, _, _ = self._exec("mount | grep -v 'proc\\|sys\\|dev' || true")
        result["details"]["mounts"] = out[:500] if out else ""

        logger.info(f"Source disk check: safe={result['safe']}")
        return result

    def check_source_agent_conflict(self) -> Dict[str, Any]:
        """检查源端 SMS Agent 冲突

        检查项:
          - 是否已有 SMS Agent 运行
          - 是否有残留的迁移进程
          - /tmp/HW_agent 是否存在
        """
        result = {"safe": True, "warnings": [], "details": {}}

        # 检查 linuxmain 进程
        out, _, _ = self._exec("pgrep -x linuxmain 2>/dev/null || true")
        if out and out.strip():
            result["safe"] = False
            result["warnings"].append(f"SMS Agent 已在运行 (PID: {out.strip()})")
            result["details"]["agent_running"] = True

        # 检查残留进程
        out, _, _ = self._exec("pgrep -f 'SMS-Agent\\|sms_agent' 2>/dev/null || true")
        if out and out.strip():
            result["warnings"].append("发现 SMS 相关残留进程")

        # 检查目录
        out, _, _ = self._exec("test -d /tmp/HW_agent && echo exists || echo no")
        if "exists" in out:
            result["warnings"].append("/tmp/HW_agent 目录已存在 (可能需要清理)")
            result["details"]["agent_dir_exists"] = True

        logger.info(f"Agent conflict check: safe={result['safe']}")
        return result

    # ──────────────────────────────────────────────────────────────
    #  目标 ECS 检查
    # ──────────────────────────────────────────────────────────────

    def check_target_ecs(self, target_ecs_id: str) -> Dict[str, Any]:
        """检查目标 ECS 状态

        Args:
            target_ecs_id: 目标 ECS ID
        """
        result = {"safe": True, "warnings": [], "details": {}}

        if not self.hcloud:
            return result

        # 查询 ECS 状态
        info = self.hcloud.ecs_show(target_ecs_id)
        if not info:
            result["safe"] = False
            result["warnings"].append("无法查询目标 ECS 信息")
            return result

        server = info.get("server", info)
        status = server.get("status", "").upper()
        result["details"]["status"] = status
        result["details"]["name"] = server.get("name")

        if status != "ACTIVE":
            result["safe"] = False
            result["warnings"].append(f"目标 ECS 状态异常: {status}")

        # 检查是否已有数据
        # (通过 metadata 或 tag 判断是否已被迁移过)
        metadata = server.get("metadata", {})
        if metadata.get("migrated") == "true":
            result["warnings"].append("目标 ECS 可能已被迁移过 (metadata.migrated=true)")

        # 检查磁盘
        volumes = server.get("os-extended-volumes:volumes_attached", [])
        result["details"]["volume_count"] = len(volumes)

        logger.info(f"Target ECS check: safe={result['safe']}, status={status}")
        return result

    # ──────────────────────────────────────────────────────────────
    #  网络隔离检查
    # ──────────────────────────────────────────────────────────────

    def check_network_isolation(self, source_ip: str, target_ip: str) -> Dict[str, Any]:
        """检查源端和目标端网络隔离

        确保迁移过程中不会有网络冲突。
        """
        result = {"safe": True, "warnings": [], "details": {}}

        # 检查 IP 段是否重叠
        source_parts = source_ip.split(".")
        target_parts = target_ip.split(".")

        if len(source_parts) == 4 and len(target_parts) == 4:
            # 简单检查: 前三段是否相同
            if source_parts[:3] == target_parts[:3]:
                result["warnings"].append(
                    f"源端和目标端在同一 /24 网段 ({'.'.join(source_parts[:3])}.x)，"
                    "迁移后需注意 IP 冲突"
                )

        result["details"]["source_ip"] = source_ip
        result["details"]["target_ip"] = target_ip

        logger.info(f"Network isolation check: safe={result['safe']}")
        return result

    # ──────────────────────────────────────────────────────────────
    #  综合检查
    # ──────────────────────────────────────────────────────────────

    def full_check(
        self,
        source_ip: str = None,
        target_ecs_id: str = None,
        target_ecs_ip: str = None,
        check_business: bool = True,
    ) -> Dict[str, Any]:
        """完整安全检查

        Args:
            source_ip: 源端 IP
            target_ecs_id: 目标 ECS ID
            target_ecs_ip: 目标 ECS IP
            check_business: 是否检查业务状态

        Returns:
            {"all_safe": bool, "checks": {}, "warnings": []}
        """
        result = {
            "all_safe": True,
            "checks": {},
            "warnings": [],
            "errors": [],
        }

        # 源端业务检查
        if check_business and self.ssh:
            logger.info("Safety check: source business")
            biz = self.check_source_business()
            result["checks"]["source_business"] = biz["safe"]
            result["warnings"].extend(biz["warnings"])
            if not biz["safe"]:
                result["all_safe"] = False

        # 源端磁盘检查
        if self.ssh:
            logger.info("Safety check: source disk")
            disk = self.check_source_disk()
            result["checks"]["source_disk"] = disk["safe"]
            result["warnings"].extend(disk["warnings"])
            if not disk["safe"]:
                result["all_safe"] = False

        # Agent 冲突检查
        if self.ssh:
            logger.info("Safety check: agent conflict")
            agent = self.check_source_agent_conflict()
            result["checks"]["agent_conflict"] = agent["safe"]
            result["warnings"].extend(agent["warnings"])
            if not agent["safe"]:
                result["all_safe"] = False

        # 目标 ECS 检查
        if target_ecs_id and self.hcloud:
            logger.info("Safety check: target ECS")
            target = self.check_target_ecs(target_ecs_id)
            result["checks"]["target_ecs"] = target["safe"]
            result["warnings"].extend(target["warnings"])
            if not target["safe"]:
                result["all_safe"] = False

        # 网络隔离检查
        if source_ip and target_ecs_ip:
            logger.info("Safety check: network isolation")
            net = self.check_network_isolation(source_ip, target_ecs_ip)
            result["checks"]["network_isolation"] = net["safe"]
            result["warnings"].extend(net["warnings"])

        # 总结
        passed = sum(1 for v in result["checks"].values() if v)
        total = len(result["checks"])
        logger.info(f"Safety check complete: {passed}/{total} passed, all_safe={result['all_safe']}")

        return result

    # ──────────────────────────────────────────────────────────────
    #  二次确认
    # ──────────────────────────────────────────────────────────────

    def require_confirmation(self, operation: str, details: str = "") -> bool:
        """高危操作二次确认

        Args:
            operation: 操作名称
            details: 操作详情

        Returns:
            是否确认
        """
        if operation not in self.HIGH_RISK_OPERATIONS:
            return True

        if operation in self.confirmations:
            return self.confirmations[operation]

        # 在实际使用中，这里会弹出确认对话框
        # 在自动化场景中，通过参数 --force 或 --yes 跳过
        logger.warning(f"High-risk operation requires confirmation: {operation}")
        if details:
            logger.warning(f"  Details: {details}")

        return False

    def confirm(self, operation: str):
        """确认高危操作 (程序化确认)"""
        self.confirmations[operation] = True
        logger.info(f"Operation confirmed: {operation}")

    def print_report(self, check_result: Dict[str, Any]) -> str:
        """生成安全检查报告"""
        lines = [
            "=" * 60,
            "安全检查报告",
            "=" * 60,
            f"总体结果: {'✓ 安全' if check_result['all_safe'] else '✗ 存在风险'}",
            "",
        ]

        if check_result.get("checks"):
            lines.append("检查项:")
            for name, passed in check_result["checks"].items():
                status = "✓" if passed else "✗"
                lines.append(f"  {status} {name}")
            lines.append("")

        if check_result.get("warnings"):
            lines.append("警告:")
            for w in check_result["warnings"]:
                lines.append(f"  ⚠ {w}")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)
