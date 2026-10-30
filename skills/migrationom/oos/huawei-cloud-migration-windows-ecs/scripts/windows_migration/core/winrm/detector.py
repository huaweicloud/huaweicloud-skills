"""
WinRM 连通性检测 — 端口扫描 + 认证测试。
"""
from __future__ import annotations

import logging
import socket
import time

import winrm

from core.interfaces.winrm_manager import DetectionResult, WinRMStatus

logger = logging.getLogger(__name__)


class WinRMDetector:
    """检测 WinRM 端口和认证连通性。"""

    @staticmethod
    def detect(host: str, port: int, username: str, password: str,
               use_ssl: bool = False, transport: str = "ntlm") -> DetectionResult:
        """
        检测流程：TCP 端口探测 → WinRM 认证测试。
        """
        # 1. 端口探测
        start = time.time()
        port_open = WinRMDetector._check_port(host, port)
        latency = (time.time() - start) * 1000

        if not port_open:
            logger.warning("WinRM 端口未开放: %s:%d", host, port)
            return DetectionResult(
                status=WinRMStatus.PORT_CLOSED,
                port_open=False,
                latency_ms=latency,
                detail=f"TCP {host}:{port} 不可达",
            )

        logger.info("WinRM 端口开放: %s:%d (%.1fms)", host, port, latency)

        # 2. 认证测试
        auth_ok = WinRMDetector._test_auth(host, port, username, password, use_ssl, transport)
        if auth_ok:
            logger.info("WinRM 认证成功: %s:%d", host, port)
            return DetectionResult(
                status=WinRMStatus.CONNECTED,
                port_open=True,
                auth_ok=True,
                latency_ms=latency,
            )
        else:
            logger.warning("WinRM 认证失败: %s:%d", host, port)
            return DetectionResult(
                status=WinRMStatus.AUTH_FAILED,
                port_open=True,
                auth_ok=False,
                latency_ms=latency,
                detail="端口开放但认证失败",
            )

    @staticmethod
    def _check_port(host: str, port: int, timeout: float = 5.0) -> bool:
        """TCP 端口探测。"""
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    @staticmethod
    def _test_auth(host: str, port: int, username: str, password: str,
                   use_ssl: bool, transport: str) -> bool:
        """通过执行简单命令测试认证。"""
        try:
            scheme = "https" if use_ssl else "http"
            endpoint = f"{scheme}://{host}:{port}/wsman"
            session = winrm.Session(
                target=endpoint,
                auth=(username, password),
                transport=transport,
                server_cert_validation="ignore" if use_ssl else None,
            )
            r = session.run_cmd("echo ok")
            return r.status_code == 0
        except Exception as e:
            logger.debug("认证测试异常: %s", e)
            return False
