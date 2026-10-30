"""
WinRM 管理器抽象接口。
涵盖检测、开启、保活全生命周期。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from core.interfaces.executor import IRemoteExecutor
from dataclasses import dataclass
from enum import Enum


class WinRMStatus(Enum):
    CONNECTED = "connected"
    PORT_CLOSED = "port_closed"
    AUTH_FAILED = "auth_failed"
    NOT_CONFIGURED = "not_configured"
    UNKNOWN = "unknown"


@dataclass
class DetectionResult:
    status: WinRMStatus
    port_open: bool = False
    auth_ok: bool = False
    latency_ms: float = 0.0
    detail: str = ""


class IWinRMManager(ABC):
    """WinRM 管理器接口 — 检测、开启、保活。"""

    @abstractmethod
    def detect(self, host: str, port: int, username: str, password: str,
               use_ssl: bool = False, transport: str = "ntlm") -> DetectionResult:
        """检测 WinRM 连通性：端口是否开放 + 认证是否通过。"""
        ...

    @abstractmethod
    def setup(self, executor: "IRemoteExecutor") -> bool:
        """通过已建立的连接开启 WinRM 服务（调用 ICloudProvider）。"""
        ...

    @abstractmethod
    def start_keepalive(self, executor: "IRemoteExecutor", interval: int = 30) -> None:
        """启动后台心跳保活线程。需要传入执行器。"""
        ...

    @abstractmethod
    def stop_keepalive(self) -> None:
        """停止心跳保活。"""
        ...

    @abstractmethod
    def is_alive(self) -> bool:
        """检查 WinRM 会话是否存活。"""
        ...
