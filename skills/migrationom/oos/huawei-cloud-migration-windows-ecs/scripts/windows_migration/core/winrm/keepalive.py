"""
WinRM 会话保活 — 后台线程周期性心跳。
迁移过程漫长，WinRM 会话可能超时断开，需要持续保活。
"""
from __future__ import annotations

import logging
import threading

from core.interfaces.executor import IRemoteExecutor

logger = logging.getLogger(__name__)


class WinRMKeepalive:
    """
    后台心跳保活线程。
    定期执行简单 WinRM 命令保持会话活跃。
    """

    def __init__(self, executor: IRemoteExecutor, interval: int = 30,
                 max_failures: int = 3, reconnect: bool = True):
        self._executor = executor
        self._interval = interval
        self._max_failures = max_failures
        self._reconnect = reconnect
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._failure_count = 0
        self._alive = False

    def start(self) -> None:
        """启动保活线程。"""
        if self._thread and self._thread.is_alive():
            logger.warning("保活线程已在运行")
            return

        self._stop_event.clear()
        self._failure_count = 0
        self._alive = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="winrm-keepalive")
        self._thread.start()
        logger.info("WinRM 保活已启动 (间隔=%ds)", self._interval)

    def stop(self) -> None:
        """停止保活线程。"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        self._alive = False
        logger.info("WinRM 保活已停止")

    def is_alive(self) -> bool:
        """会话是否存活。"""
        return self._alive and self._failure_count < self._max_failures

    def _run(self) -> None:
        """保活循环。"""
        while not self._stop_event.is_set():
            try:
                result = self._executor.run_cmd("echo keepalive", timeout=15)
                if result.success:
                    self._failure_count = 0
                    self._alive = True
                    logger.debug("心跳成功")
                else:
                    self._failure_count += 1
                    self._alive = False
                    logger.warning("心跳失败 (%d/%d): %s",
                                   self._failure_count, self._max_failures, result.stderr[:200])

                    if self._failure_count >= self._max_failures:
                        logger.error("连续 %d 次心跳失败，WinRM 会话可能已断开",
                                     self._failure_count)
                        if self._reconnect:
                            self._attempt_reconnect()

            except Exception as e:
                self._failure_count += 1
                self._alive = False
                logger.error("心跳异常: %s", e)

            self._stop_event.wait(self._interval)

    def _attempt_reconnect(self) -> None:
        """尝试重连（由调用方重新创建 executor 后重置）。"""
        logger.info("等待外部重连...")
        # 重连逻辑由外层编排处理，这里只做检测
        # 外层检测到 is_alive()=False 后可重建 executor 并调用 reset()
        self._stop_event.wait(self._interval * 2)

    def reset(self, executor: IRemoteExecutor) -> None:
        """重置执行器（重连后调用）。"""
        self._executor = executor
        self._failure_count = 0
        self._alive = True
        logger.info("保活执行器已重置")
