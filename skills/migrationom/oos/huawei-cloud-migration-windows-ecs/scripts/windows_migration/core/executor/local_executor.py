"""
本地 Linux 执行器 — 用于沙箱上的本地操作。
实现 IRemoteExecutor 接口，与 WinRMExecutor 对等。
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import time
from pathlib import Path

from core.interfaces.executor import CommandResult, IRemoteExecutor

logger = logging.getLogger(__name__)


class LocalExecutor(IRemoteExecutor):
    """本地 Linux 执行器 — 在沙箱上执行命令和文件操作。"""

    def __init__(self, work_dir: str = ""):
        self._work_dir = work_dir

    def is_connected(self) -> bool:
        return True  # 本地总是连接

    def run_cmd(self, command: str, timeout: int = 300) -> CommandResult:
        """执行 shell 命令。"""
        start = time.time()
        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self._work_dir or None,
            )
            return CommandResult(
                success=proc.returncode == 0,
                stdout=proc.stdout,
                stderr=proc.stderr,
                exit_code=proc.returncode,
                duration=time.time() - start,
            )
        except subprocess.TimeoutExpired:
            return CommandResult(success=False, stderr="命令超时", duration=time.time() - start)
        except Exception as e:
            logger.error("本地命令失败: %s | %s", e, command[:200])
            return CommandResult(success=False, stderr=str(e), duration=time.time() - start)

    def run_ps(self, script: str, timeout: int = 300) -> CommandResult:
        """本地无 PowerShell，直接用 shell 执行（兼容接口）。"""
        return self.run_cmd(script, timeout)

    def transfer_file(self, local_path: str, remote_path: str, timeout: int = 600) -> CommandResult:
        """本地文件复制。"""
        start = time.time()
        try:
            Path(remote_path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_path, remote_path)
            return CommandResult(success=True, stdout=remote_path, duration=time.time() - start)
        except Exception as e:
            return CommandResult(success=False, stderr=str(e), duration=time.time() - start)

    def file_exists(self, remote_path: str) -> bool:
        """检查本地文件是否存在。"""
        return Path(remote_path).exists()
