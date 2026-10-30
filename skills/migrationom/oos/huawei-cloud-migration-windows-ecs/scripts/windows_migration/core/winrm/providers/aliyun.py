"""
阿里云 WinRM 开启 — 预留 stub，将来实现。
"""
from __future__ import annotations

from core.winrm.providers.base import BaseWinRMProvider


class AliyunWinRMProvider(BaseWinRMProvider):
    """阿里云 WinRM 开启（预留）。"""

    @property
    def provider_name(self) -> str:
        return "aliyun"

    def get_enable_commands(self) -> list:
        return [
            "winrm quickconfig -force",
            "winrm set winrm/config/service/auth '@{Basic=\"true\"}'",
            "winrm set winrm/config/service '@{AllowUnencrypted=\"true\"}'",
            "winrm set winrm/config/client '@{TrustedHosts=\"*\"}'",
            "Start-Service WinRM",
        ]
