"""
WinRM 云厂商 provider 基类。
各云厂商实现 enable_winrm() 来开启源端 Windows 的 WinRM 服务。
继承 ICloudProvider 接口，确保接口一致性。
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from core.interfaces.cloud_provider import ICloudProvider, WinRMSetupResult
from core.interfaces.executor import IRemoteExecutor

logger = logging.getLogger(__name__)


class BaseWinRMProvider(ICloudProvider, ABC):
    """
    WinRM 开启基类 — 各云厂商实现具体的 PowerShell 命令序列。
    继承 ICloudProvider 接口。
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def get_enable_commands(self) -> list[str]:
        """返回开启 WinRM 的 PowerShell 命令序列。"""
        ...

    def enable_winrm(self, executor: IRemoteExecutor) -> WinRMSetupResult:
        """
        通用开启流程：依次执行命令序列。
        子类只需提供 get_enable_commands()。
        """
        commands = self.get_enable_commands()
        steps = []

        for i, cmd in enumerate(commands):
            logger.info("[%s] 步骤 %d/%d: %s", self.provider_name, i + 1, len(commands), cmd[:80])
            result = executor.run_ps(cmd, timeout=60)
            steps.append({"cmd": cmd[:200], "success": result.success, "stderr": result.stderr[:200]})

            if not result.success:
                return WinRMSetupResult(
                    success=False,
                    steps_executed=steps,
                    error=f"步骤 {i + 1} 失败: {result.stderr[:200]}",
                )

        return WinRMSetupResult(success=True, steps_executed=steps)

    def verify_winrm(self, executor: IRemoteExecutor) -> bool:
        """
        验证 WinRM 是否已开启（检查 listener）。

        注意: 此方法签名与 ICloudProvider.verify_winrm 不同。
        ICloudProvider.verify_winrm 接收 host/port/username/password，
        但实际使用场景中我们已有 executor，直接用它更高效。
        子类如需按接口签名实现，可重写此方法。
        """
        result = executor.run_ps(
            "winrm enumerate winrm/config/listener",
            timeout=30,
        )
        return result.success and "Listener" in result.stdout
