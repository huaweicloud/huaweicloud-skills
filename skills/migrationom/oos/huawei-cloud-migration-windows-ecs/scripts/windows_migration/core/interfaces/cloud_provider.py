"""
云厂商 provider 抽象接口 — 用于开启源端 Windows 的 WinRM 服务。
多云支持：华为云、AWS、阿里云等。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from core.interfaces.executor import IRemoteExecutor


@dataclass
class WinRMSetupResult:
    """WinRM 开启结果。"""
    success: bool
    steps_executed: list[dict] = field(default_factory=list)
    error: str = ""


class ICloudProvider(ABC):
    """
    云厂商 WinRM 开启接口。

    使用场景: 源端 Windows 主机的 WinRM 端口未开放或认证未配置时，
    通过已有的执行通道（如云厂商 metadata API 或远程执行）开启 WinRM。
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """厂商名称，如 'huawei_cloud'。"""
        ...

    @abstractmethod
    def enable_winrm(self, executor: IRemoteExecutor) -> WinRMSetupResult:
        """
        开启 WinRM 服务并配置认证。
        executor: 已建立的远程执行器（通过其他通道如 SSH/云API）。
        """
        ...

    @abstractmethod
    def verify_winrm(self, executor: IRemoteExecutor) -> bool:
        """
        验证 WinRM 是否已正确开启。
        executor: 已建立的远程执行器。
        """
        ...
