"""
SSH 执行器 — 基于 paramiko 持久连接。
一次连接多次执行命令，避免每次 fork sshpass+ssh 进程。
线程安全：内部锁保护连接复用。
"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

import paramiko

from core.interfaces.executor import CommandResult

logger = logging.getLogger(__name__)


class SSHExecutor:
    """
    SSH 远程执行器 — paramiko 持久连接。

    优化:
      - 一次连接多次执行命令，避免重复 TCP 握手 + SSH 认证
      - 内部 threading.Lock 保证线程安全
      - 连接断开自动重连
    """

    def __init__(self, host: str, port: int = 22, username: str = "root",
                 password: str = "", key_file: str = ""):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._key_file = key_file
        self._client: paramiko.SSHClient | None = None
        self._lock = threading.Lock()
        self._connect()

    def _connect(self) -> None:
        """建立 SSH 连接。"""
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs = {
            "hostname": self._host,
            "port": self._port,
            "username": self._username,
            "timeout": 10,
        }
        if self._key_file and Path(self._key_file).exists():
            kwargs["key_filename"] = self._key_file
        elif self._password:
            kwargs["password"] = self._password
        self._client.connect(**kwargs)
        logger.info("SSH 连接已建立: %s@%s:%d", self._username, self._host, self._port)

    def _ensure_connected(self) -> None:
        """确保连接存活，断开则重连。"""
        if self._client is None:
            self._connect()
            return
        # 检测连接是否存活
        try:
            transport = self._client.get_transport()
            if transport is None or not transport.is_active():
                self._connect()
        except Exception:
            self._connect()

    def run_cmd(self, command: str, timeout: int = 300) -> CommandResult:
        """通过 SSH 执行远程命令（复用连接）。"""
        start = time.time()
        try:
            with self._lock:
                self._ensure_connected()
                stdin, stdout, stderr = self._client.exec_command(command, timeout=timeout)
                exit_code = stdout.channel.recv_exit_status()
                out = stdout.read().decode("utf-8", errors="replace")
                err = stderr.read().decode("utf-8", errors="replace")
            return CommandResult(
                success=exit_code == 0,
                stdout=out,
                stderr=err,
                exit_code=exit_code,
                duration=time.time() - start,
            )
        except Exception as e:
            logger.error("SSH 执行失败: %s | 命令: %s", e, command[:200])
            return CommandResult(success=False, stderr=str(e), duration=time.time() - start)

    def run_script(self, script_path: str, remote_args: str = "", timeout: int = 300) -> CommandResult:
        """在远程执行一个脚本文件（脚本需已在远程存在）。"""
        cmd = f"bash {script_path}"
        if remote_args:
            cmd += f" {remote_args}"
        return self.run_cmd(cmd, timeout=timeout)

    def upload_file(self, local_path: str, remote_path: str, timeout: int = 120) -> CommandResult:
        """通过 SFTP 上传文件到远程（复用连接）。"""
        start = time.time()
        try:
            with self._lock:
                self._ensure_connected()
                sftp = self._client.open_sftp()
                try:
                    sftp.put(local_path, remote_path)
                finally:
                    sftp.close()
            return CommandResult(success=True, duration=time.time() - start)
        except Exception as e:
            logger.error("SFTP 上传失败: %s | %s → %s", e, local_path, remote_path)
            return CommandResult(success=False, stderr=str(e), duration=time.time() - start)

    def upload_content(self, content: str, remote_path: str, timeout: int = 30) -> CommandResult:
        """直接写入字符串内容到远程文件（无需本地临时文件）。"""
        start = time.time()
        try:
            with self._lock:
                self._ensure_connected()
                sftp = self._client.open_sftp()
                try:
                    with sftp.file(remote_path, "w") as f:
                        f.write(content)
                finally:
                    sftp.close()
            return CommandResult(success=True, duration=time.time() - start)
        except Exception as e:
            logger.error("SFTP 写入失败: %s | %s", e, remote_path)
            return CommandResult(success=False, stderr=str(e), duration=time.time() - start)

    def close(self) -> None:
        """关闭 SSH 连接。"""
        with self._lock:
            if self._client:
                self._client.close()
                self._client = None
                logger.info("SSH 连接已关闭: %s@%s:%d", self._username, self._host, self._port)
