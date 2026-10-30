"""
WinRM provider 工厂 — 根据云厂商名称创建对应 provider。
"""
from __future__ import annotations

from core.winrm.providers.aliyun import AliyunWinRMProvider
from core.winrm.providers.aws import AWSWinRMProvider
from core.winrm.providers.base import BaseWinRMProvider
from core.winrm.providers.huawei_cloud import HuaweiCloudWinRMProvider

_PROVIDERS = {
    "huawei": HuaweiCloudWinRMProvider,
    "aws": AWSWinRMProvider,
    "aliyun": AliyunWinRMProvider,
}


def get_provider(cloud: str) -> BaseWinRMProvider | None:
    """根据云厂商名称获取 provider 实例。"""
    cls = _PROVIDERS.get(cloud)
    return cls() if cls else None
