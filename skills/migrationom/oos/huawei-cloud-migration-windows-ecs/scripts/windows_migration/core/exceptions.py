"""
统一异常层级 — 外部调用者可按类型精确捕获。

层级:
    MigrationError              # 基类，所有迁移异常的父类
    ├── ConfigError             # 配置加载/校验失败
    ├── WinRMError              # WinRM 连接/认证/执行失败
    ├── DownloadError           # OBS/HTTP 下载失败
    ├── InstallError            # AutoIt/SMS-Agent 安装失败
    ├── ConfigureError          # Agent GUI 配置失败
    └── VerifyError             # 注册验证失败

每个异常携带:
    - error_code: str    机器可读的错误码（如 "WINRM_AUTH_FAILED"）
    - detail: dict       结构化附加信息（如 host, phase, exit_code）
    - message: str       人类可读的错误描述

外部调用示例:
    try:
        result = scenario.run(ctx)
    except WinRMError as e:
        if e.error_code == "WINRM_AUTH_FAILED":
            ...  # 重试或换凭据
    except MigrationError as e:
        ...  # 其他迁移错误
"""
from __future__ import annotations



class MigrationError(Exception):
    """所有迁移异常的基类。"""

    def __init__(
        self,
        message: str,
        error_code: str = "MIGRATION_ERROR",
        detail: dict | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.detail = detail or {}

    def to_dict(self) -> dict:
        """序列化为可 JSON 化的字典。"""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "detail": self.detail,
        }


class ConfigError(MigrationError):
    """配置加载或校验失败。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message, "CONFIG_ERROR", detail)


class WinRMError(MigrationError):
    """WinRM 连接、认证或执行失败。"""

    def __init__(self, message: str, error_code: str = "WINRM_ERROR", detail: dict | None = None):
        super().__init__(message, error_code, detail)


class DownloadError(MigrationError):
    """OBS 或 HTTP 下载失败。"""

    def __init__(self, message: str, error_code: str = "DOWNLOAD_ERROR", detail: dict | None = None):
        super().__init__(message, error_code, detail)


class InstallError(MigrationError):
    """AutoIt 或 SMS-Agent 安装失败。"""

    def __init__(self, message: str, error_code: str = "INSTALL_ERROR", detail: dict | None = None):
        super().__init__(message, error_code, detail)


class ConfigureError(MigrationError):
    """Agent GUI 配置失败。"""

    def __init__(self, message: str, error_code: str = "CONFIGURE_ERROR", detail: dict | None = None):
        super().__init__(message, error_code, detail)


class VerifyError(MigrationError):
    """注册验证失败。"""

    def __init__(self, message: str, error_code: str = "VERIFY_ERROR", detail: dict | None = None):
        super().__init__(message, error_code, detail)

class SmsApiError(MigrationError):
    """SMS 控制面 API（KooCLI）调用失败：非零退出、JSON 解析失败或业务报错。"""

    def __init__(self, message: str, error_code: str = "SMS_API_ERROR", detail: dict | None = None):
        super().__init__(message, error_code, detail)
