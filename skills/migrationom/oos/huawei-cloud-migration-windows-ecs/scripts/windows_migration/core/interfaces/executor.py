"""
远程执行器抽象接口。
WinRM 执行器和本地执行器都实现此接口，实现依赖反转。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CommandResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    duration: float = 0.0


class IRemoteExecutor(ABC):
    """远程执行器接口 — 命令执行、文件传输、文件检查。"""

    @abstractmethod
    def run_cmd(self, command: str, timeout: int = 300) -> CommandResult:
        """执行 CMD 命令（Windows）或 shell 命令（Linux）。"""
        ...

    @abstractmethod
    def run_ps(self, script: str, timeout: int = 300) -> CommandResult:
        """执行 PowerShell 脚本（Windows）。"""
        ...

    @abstractmethod
    def transfer_file(self, local_path: str, remote_path: str, timeout: int = 600) -> CommandResult:
        """传输本地文件到远程主机（base64 分块，绕过命令长度限制）。"""
        ...

    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """检查远程文件是否存在。"""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """检查连接是否有效。"""
        ...
