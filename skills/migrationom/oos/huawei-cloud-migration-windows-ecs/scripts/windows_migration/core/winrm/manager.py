"""
WinRM 管理器 — 组合检测、开启、保活。
实现 IWinRMManager 接口，编排 WinRM 全生命周期。
"""
from __future__ import annotations

import logging

from core.config import MigrateConfig
from core.interfaces.executor import IRemoteExecutor
from core.interfaces.winrm_manager import DetectionResult, IWinRMManager
from core.winrm.detector import WinRMDetector
from core.winrm.keepalive import WinRMKeepalive
from core.winrm.providers.factory import get_provider

logger = logging.getLogger(__name__)


class WinRMManager(IWinRMManager):
    """
    WinRM 管理器：检测 → 开启 → 保活。

    检测：TCP 端口 + 认证测试
    开启：通过云厂商 provider 执行 PowerShell 命令序列
    保活：后台线程周期心跳
    """

    def __init__(self, config: MigrateConfig):
        self._config = config
        self._keepalive: WinRMKeepalive | None = None
        self._executor: IRemoteExecutor | None = None

    def detect(self, host: str, port: int, username: str, password: str,
               use_ssl: bool = False, transport: str = "ntlm") -> DetectionResult:
        return WinRMDetector.detect(host, port, username, password, use_ssl, transport)

    def setup(self, executor: IRemoteExecutor) -> bool:
        """
        通过已建立的连接开启 WinRM。
        executor: 已通过 SSH/其他方式连上源端的执行器。
        """
        cloud = self._config.source.cloud_provider
        if cloud == "none":
            logger.info("cloud_provider=none，跳过 WinRM 开启")
            return True

        provider = get_provider(cloud)
        if not provider:
            logger.error("不支持的云厂商: %s", cloud)
            return False

        logger.info("通过 %s provider 开启 WinRM", cloud)
        result = provider.enable_winrm(executor)
        if not result.success:
            logger.error("WinRM 开启失败: %s", result.error)
            return False

        # 验证
        if not provider.verify_winrm(executor):
            logger.error("WinRM 开启后验证失败")
            return False

        logger.info("WinRM 开启成功 (%d 步)", len(result.steps_executed))
        return True

    def start_keepalive(self, executor: IRemoteExecutor, interval: int = 30) -> None:
        """启动保活。"""
        self._executor = executor
        self._keepalive = WinRMKeepalive(
            executor=executor,
            interval=interval,
            max_failures=self._config.winrm_keepalive.max_failures,
            reconnect=self._config.winrm_keepalive.reconnect,
        )
        self._keepalive.start()

    def stop_keepalive(self) -> None:
        if self._keepalive:
            self._keepalive.stop()

    def is_alive(self) -> bool:
        if not self._keepalive:
            return False
        return self._keepalive.is_alive()
