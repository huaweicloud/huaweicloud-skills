#!/usr/bin/env python3
"""
vpn_check.py — VPN 连通性检查

私网迁移前提: 源端和目标端通过 VPN 打通网络。
本模块验证 VPN 连通性，确保迁移前网络通道可用。

检查项:
  1. VPN 网关状态 (华为云 VPN)
  2. 源端 → 代理 ECS 连通性 (ping + TCP 端口)
  3. 代理 ECS → 源端连通性 (ping + TCP 端口)
  4. 源端 → squid 代理端口连通性
  5. 代理 ECS → 目标 ECS 连通性
  6. 路由表正确性
"""

import time
import logging
import subprocess
import socket
from typing import Optional, Dict, List, Any, Tuple

logger = logging.getLogger(__name__)


class VpnChecker:
    """VPN 连通性检查器"""

    def __init__(self, hcloud=None, ssh_client=None):
        """
        Args:
            hcloud: HcloudCLI 实例 (用于查询华为云 VPN 状态)
            ssh_client: SSH 客户端 (连接到代理 ECS，用于从目标侧测试)
        """
        self.hcloud = hcloud
        self.ssh = ssh_client

    def _exec_local(self, cmd: str, timeout: int = 10) -> Tuple[str, str, int]:
        """本地执行命令"""
        try:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, timeout=timeout, text=True
            )
            return proc.stdout.strip(), proc.stderr.strip(), proc.returncode
        except subprocess.TimeoutExpired:
            return "", "timeout", -1
        except Exception as e:
            return "", str(e), -1

    def _exec_remote(self, cmd: str, timeout: int = 10) -> Tuple[str, str, int]:
        """在代理 ECS 上执行命令"""
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
    #  VPN 网关状态检查
    # ──────────────────────────────────────────────────────────────

    def check_vpn_gateway(self, vgw_id: str = None) -> Dict[str, Any]:
        """检查华为云 VPN 网关状态

        Args:
            vgw_id: VPN 网关 ID (可选，不提供则列出所有)

        Returns:
            VPN 网关状态信息
        """
        result = {"ok": False, "gateways": []}

        if not self.hcloud:
            logger.warning("No hcloud client, skipping VPN gateway check")
            return result

        try:
            if vgw_id:
                resp = self.hcloud.vpn_show_gateway(vgw_id)
                if isinstance(resp, dict):
                    result["gateways"].append(resp)
                    status = resp.get("status", "").upper()
                    result["ok"] = status in ("ACTIVE", "NORMAL")
            else:
                resp = self.hcloud.vpn_list_gateways()
                if isinstance(resp, dict):
                    gateways = resp.get("vpn_gateways", [])
                    for gw in gateways:
                        status = gw.get("status", "").upper()
                        gw_info = {
                            "id": gw.get("id"),
                            "name": gw.get("name"),
                            "status": status,
                            "vgw_ip": gw.get("vgw_ip"),
                        }
                        result["gateways"].append(gw_info)
                        if status in ("ACTIVE", "NORMAL"):
                            result["ok"] = True

            logger.info(f"VPN gateway check: ok={result['ok']}, count={len(result['gateways'])}")
        except Exception as e:
            logger.error(f"VPN gateway check failed: {e}")
            result["error"] = str(e)

        return result

    def check_vpn_connection(self, vgw_id: str) -> Dict[str, Any]:
        """检查 VPN 连接状态

        Args:
            vgw_id: VPN 网关 ID

        Returns:
            VPN 连接状态信息
        """
        result = {"ok": False, "connections": []}

        if not self.hcloud:
            return result

        try:
            resp = self.hcloud.vpn_list_connections(vgw_id)
            if isinstance(resp, dict):
                connections = resp.get("vpn_connections", [])
                for conn in connections:
                    status = conn.get("status", "").upper()
                    result["connections"].append({
                        "id": conn.get("id"),
                        "name": conn.get("name"),
                        "status": status,
                    })
                    if status in ("ACTIVE", "NORMAL"):
                        result["ok"] = True

            logger.info(f"VPN connection check: ok={result['ok']}")
        except Exception as e:
            logger.error(f"VPN connection check failed: {e}")
            result["error"] = str(e)

        return result

    # ──────────────────────────────────────────────────────────────
    #  网络连通性检查
    # ──────────────────────────────────────────────────────────────

    def ping_check(self, target_ip: str, from_remote: bool = False,
                   count: int = 4, timeout: int = 10) -> Dict[str, Any]:
        """Ping 连通性检查

        Args:
            target_ip: 目标 IP
            from_remote: True=从代理 ECS 执行, False=本地执行
            count: ping 次数
            timeout: 超时秒数

        Returns:
            {"ok": bool, "loss": float, "rtt_avg": float}
        """
        cmd = f"ping -c {count} -W 2 {target_ip} 2>&1"
        if from_remote:
            out, err, code = self._exec_remote(cmd, timeout=timeout)
        else:
            out, err, code = self._exec_local(cmd, timeout=timeout)

        result = {"ok": False, "loss": 100.0, "rtt_avg": 0.0}

        if out:
            # 解析丢包率
            for line in out.splitlines():
                if "packet loss" in line:
                    try:
                        loss_str = line.split(",")[2].strip().split("%")[0].strip()
                        result["loss"] = float(loss_str)
                        result["ok"] = result["loss"] < 50.0
                    except (ValueError, IndexError):
                        pass
                if "rtt mdev" in line or "round-trip" in line:
                    try:
                        parts = line.split("=")[1].strip().split("/")
                        result["rtt_avg"] = float(parts[1])
                    except (ValueError, IndexError):
                        pass

        logger.info(f"Ping {target_ip} ({'remote' if from_remote else 'local'}): "
                     f"ok={result['ok']}, loss={result['loss']}%")
        return result

    def tcp_check(self, target_ip: str, port: int, from_remote: bool = False,
                  timeout: int = 5) -> bool:
        """TCP 端口连通性检查

        Args:
            target_ip: 目标 IP
            port: 目标端口
            from_remote: True=从代理 ECS 执行
            timeout: 超时秒数

        Returns:
            端口是否可达
        """
        if from_remote:
            cmd = f"timeout {timeout} bash -c 'echo > /dev/tcp/{target_ip}/{port}' 2>/dev/null && echo ok || echo fail"
            out, _, _ = self._exec_remote(cmd, timeout=timeout + 2)
            ok = "ok" in out
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            try:
                result = sock.connect_ex((target_ip, port))
                ok = (result == 0)
            except Exception:
                ok = False
            finally:
                sock.close()

        logger.info(f"TCP {target_ip}:{port} ({'remote' if from_remote else 'local'}): {'OK' if ok else 'FAIL'}")
        return ok

    # ──────────────────────────────────────────────────────────────
    #  综合检查
    # ──────────────────────────────────────────────────────────────

    def full_check(
        self,
        source_ip: str,
        proxy_ecs_ip: str,
        target_ecs_ip: str,
        squid_port: int = 3128,
        ssh_port: int = 22,
        data_ports: List[int] = None,
        vgw_id: str = None,
    ) -> Dict[str, Any]:
        """完整 VPN 连通性检查

        检查项:
          1. VPN 网关状态
          2. 代理 ECS → 源端 ping
          3. 代理 ECS → 源端 SSH 端口
          4. 源端 → 代理 ECS squid 端口 (从代理 ECS 自测)
          5. 代理 ECS → 目标 ECS ping
          6. 代理 ECS → 目标 ECS 数据端口

        Args:
            source_ip: 源端内网 IP
            proxy_ecs_ip: 代理 ECS 内网 IP
            target_ecs_ip: 目标 ECS 内网 IP
            squid_port: squid 代理端口
            ssh_port: SSH 端口
            data_ports: 数据流端口列表
            vgw_id: VPN 网关 ID

        Returns:
            完整检查结果
        """
        if data_ports is None:
            data_ports = [8899, 8900]

        result = {
            "all_ok": True,
            "checks": {},
            "details": {},
        }

        # 1. VPN 网关状态
        logger.info("Check 1: VPN gateway status")
        if vgw_id:
            gw_result = self.check_vpn_gateway(vgw_id)
            result["checks"]["vpn_gateway"] = gw_result["ok"]
            result["details"]["vpn_gateway"] = gw_result
            if not gw_result["ok"]:
                result["all_ok"] = False

            conn_result = self.check_vpn_connection(vgw_id)
            result["checks"]["vpn_connection"] = conn_result["ok"]
            if not conn_result["ok"]:
                result["all_ok"] = False

        # 2. 代理 ECS → 源端 ping
        logger.info("Check 2: Proxy ECS -> Source ping")
        ping_result = self.ping_check(source_ip, from_remote=True)
        result["checks"]["proxy_to_source_ping"] = ping_result["ok"]
        result["details"]["proxy_to_source_ping"] = ping_result
        if not ping_result["ok"]:
            result["all_ok"] = False

        # 3. 代理 ECS → 源端 SSH 端口
        logger.info("Check 3: Proxy ECS -> Source SSH port")
        ssh_ok = self.tcp_check(source_ip, ssh_port, from_remote=True)
        result["checks"]["proxy_to_source_ssh"] = ssh_ok
        if not ssh_ok:
            result["all_ok"] = False

        # 4. squid 端口 (代理 ECS 本地自测)
        logger.info("Check 4: Squid port on proxy ECS")
        squid_ok = self.tcp_check("127.0.0.1", squid_port, from_remote=True)
        result["checks"]["squid_port"] = squid_ok
        if not squid_ok:
            result["all_ok"] = False

        # 5. 代理 ECS → 目标 ECS ping
        logger.info("Check 5: Proxy ECS -> Target ECS ping")
        target_ping = self.ping_check(target_ecs_ip, from_remote=True)
        result["checks"]["proxy_to_target_ping"] = target_ping["ok"]
        result["details"]["proxy_to_target_ping"] = target_ping
        if not target_ping["ok"]:
            result["all_ok"] = False

        # 6. 代理 ECS → 目标 ECS 数据端口
        logger.info("Check 6: Proxy ECS -> Target ECS data ports")
        for port in data_ports:
            port_ok = self.tcp_check(target_ecs_ip, port, from_remote=True)
            result["checks"][f"target_port_{port}"] = port_ok
            if not port_ok:
                result["all_ok"] = False

        # 总结
        passed = sum(1 for v in result["checks"].values() if v)
        total = len(result["checks"])
        logger.info(f"VPN check complete: {passed}/{total} passed, all_ok={result['all_ok']}")

        return result

    def print_report(self, check_result: Dict[str, Any]) -> str:
        """生成可读的检查报告"""
        lines = [
            "=" * 60,
            "VPN 连通性检查报告",
            "=" * 60,
            f"总体结果: {'✓ 通过' if check_result['all_ok'] else '✗ 失败'}",
            "",
            "详细检查项:",
        ]

        for check_name, passed in check_result["checks"].items():
            status = "✓" if passed else "✗"
            lines.append(f"  {status} {check_name}")

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)
