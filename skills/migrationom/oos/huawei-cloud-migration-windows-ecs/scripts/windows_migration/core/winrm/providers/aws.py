"""
AWS WinRM 开启 — 预留 stub，将来实现。
AWS EC2 Windows 默认已开启 WinRM，但可能需要调整认证配置。
"""
from __future__ import annotations

from core.winrm.providers.base import BaseWinRMProvider


class AWSWinRMProvider(BaseWinRMProvider):
    """AWS WinRM 开启（预留）。"""

    @property
    def provider_name(self) -> str:
        return "aws"

    def get_enable_commands(self) -> list:
        return [
            # AWS EC2 Windows 通常已开启 WinRM，这里只确保认证配置
            "winrm set winrm/config/service/auth '@{Basic=\"true\"}'",
            "winrm set winrm/config/service '@{AllowUnencrypted=\"true\"}'",
            "winrm set winrm/config/client '@{TrustedHosts=\"*\"}'",
        ]
