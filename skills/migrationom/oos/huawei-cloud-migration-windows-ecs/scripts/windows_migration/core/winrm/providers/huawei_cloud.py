"""
华为云 WinRM 开启。
参考: https://support.huaweicloud.com/vss_faq/vss_01_0179_04.html

HTTP WinRM (5985):
  1. winrm quickconfig
 2. winrm set winrm/config/service/auth @{Basic="true"}
 3. winrm set winrm/config/service @{AllowUnencrypted="true"}
"""
from __future__ import annotations

from core.winrm.providers.base import BaseWinRMProvider


class HuaweiCloudWinRMProvider(BaseWinRMProvider):
    """华为云 WinRM 开启 — 基于 HTTP 5985 端口。"""

    @property
    def provider_name(self) -> str:
        return "huawei"

    def get_enable_commands(self) -> list:
        return [
            # 1. 开启 WinRM 服务
            "winrm quickconfig -force",
            # 2. 启用 Basic 认证
            "winrm set winrm/config/service/auth '@{Basic=\"true\"}'",
            # 3. 允许非加密传输（HTTP 需要）
            "winrm set winrm/config/service '@{AllowUnencrypted=\"true\"}'",
            # 4. 设置 TrustedHosts（允许所有主机连接）
            "winrm set winrm/config/client '@{TrustedHosts=\"*\"}'",
            # 5. 启动服务确保运行
            "Start-Service WinRM",
        ]
