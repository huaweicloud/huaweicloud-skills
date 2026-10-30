"""
WinRM 远程执行器 — 基于 pywinrm。
支持直连和 gost 端口转发两种连接方式（通过 host:port 配置）。

实测修复:
  - 中文 Windows 输出 GBK 编码，优先 GBK 解码再 fallback UTF-8
  - pywinrm 0.5.0 不支持 timeout kwarg，timeout 仅用于日志
  - 线程安全锁：keepalive 线程与主线程并发使用同一 session 导致 SPNEGO MIC 错误
  - 文件传输优化: run_ps chunk 2800 / run_cmd+powershell chunk 7000 (3.5x 加速)
"""
from __future__ import annotations

import base64
import logging
import threading
import time
from pathlib import Path

import winrm

from core.interfaces.executor import CommandResult, IRemoteExecutor

logger = logging.getLogger(__name__)

# run_ps base64 分块大小（UTF-16LE+base64 膨胀 8/3 倍，含脚本开销实测上限 ~2800）
_CHUNK_PS = 2800
# run_cmd + powershell -Command 分块大小（无 UTF-16LE 编码，实测上限 ~7000）
_CHUNK_CMD = 7000


def _decode(data: bytes) -> str:
    """解码远程输出 — 中文 Windows 用 GBK，优先尝试 GBK 再 fallback UTF-8。"""
    if not data:
        return ""
    for encoding in ("gbk", "utf-8"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


class WinRMExecutor(IRemoteExecutor):
    """
    WinRM 远程执行器。

    连接方式由 host + port 决定：
    - 公网直连：host=源端公网IP, port=5985
    - 私网经 gost 转发：host=代理服务器IP, port=15985（gost 转发到源端:5985）
    """

    def __init__(
        self,
        host: str,
        port: int = 5985,
        username: str = "",
        password: str = "",
        transport: str = "ntlm",
        use_ssl: bool = False,
        command_timeout: int = 300,
        remote_work_dir: str = "C:\\auto_agent_opt",
    ):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._transport = transport
        self._use_ssl = use_ssl
        self._command_timeout = command_timeout
        self._remote_work_dir = remote_work_dir
        self._session: winrm.Session | None = None
        self._lock = threading.Lock()
        self._defender_excluded = False
        self._connect()

    def _connect(self) -> None:
        """建立 WinRM 会话。"""
        scheme = "https" if self._use_ssl else "http"
        endpoint = f"{scheme}://{self._host}:{self._port}/wsman"
        logger.info("WinRM 连接: %s (transport=%s)", endpoint, self._transport)

        self._session = winrm.Session(
            target=endpoint,
            auth=(self._username, self._password),
            transport=self._transport,
            server_cert_validation="ignore" if self._use_ssl else None,
        )
        logger.info("WinRM 会话已建立")

    def is_connected(self) -> bool:
        """通过执行简单命令检查连接。"""
        try:
            result = self.run_cmd("echo ok")
            return result.success and "ok" in result.stdout
        except Exception:
            return False

    def reconnect(self) -> bool:
        """重连 WinRM 会话 (大文件传输失败后恢复)。"""
        logger.info("WinRM 重连...")
        try:
            self._connect()
            return self.is_connected()
        except Exception as e:
            logger.error("WinRM 重连失败: %s", e)
            return False

    def run_cmd(self, command: str, timeout: int = 300) -> CommandResult:
        """执行 CMD 命令。timeout 仅用于日志，pywinrm 0.5.0 不支持该参数。"""
        start = time.time()
        try:
            with self._lock:
                r = self._session.run_cmd(command)
            stdout = _decode(r.std_out)
            stderr = _decode(r.std_err)
            success = r.status_code == 0
            return CommandResult(
                success=success,
                stdout=stdout,
                stderr=stderr,
                exit_code=r.status_code,
                duration=time.time() - start,
            )
        except Exception as e:
            logger.error("CMD 执行失败: %s | 命令: %s", e, command[:200])
            return CommandResult(success=False, stderr=str(e), duration=time.time() - start)

    def run_ps(self, script: str, timeout: int = 300) -> CommandResult:
        """执行 PowerShell 脚本。timeout 仅用于日志，pywinrm 0.5.0 不支持该参数。"""
        start = time.time()
        try:
            with self._lock:
                r = self._session.run_ps(script)
            stdout = _decode(r.std_out)
            stderr = _decode(r.std_err)
            success = r.status_code == 0
            return CommandResult(
                success=success,
                stdout=stdout,
                stderr=stderr,
                exit_code=r.status_code,
                duration=time.time() - start,
            )
        except Exception as e:
            logger.error("PS 执行失败: %s | 脚本: %s", e, script[:200])
            return CommandResult(success=False, stderr=str(e), duration=time.time() - start)


    def transfer_file(self, local_path: str, remote_path: str, timeout: int = 600) -> CommandResult:
        """
        通过 base64 分块传输文件到远程 Windows。

        策略:
          - 小文件 (<1MB): run_ps base64 分块 (chunk 2800, 自动探测)
          - 大文件 (≥1MB): run_cmd + powershell -Command 旁路 (chunk 7000, 失败同块重试)
            run_cmd 无 UTF-16LE 编码膨胀，chunk 大 2.5 倍，往返次数减少 60%

        使用 [IO.File]::Open + FileStream.Write 写入二进制数据，避免 Out-File 损坏。
        """
        local = Path(local_path)
        if not local.exists():
            return CommandResult(success=False, stderr=f"本地文件不存在: {local_path}")

        file_size = local.stat().st_size
        logger.info("传输文件: %s (%d bytes) → %s", local_path, file_size, remote_path)

        # 远端文件已存在且大小匹配则跳过传输（幂等优化，省全部 WinRM 往返）
        if self.file_exists(remote_path):
            r_size = self.run_cmd(f'for %I in ("{remote_path}") do echo %~zI')
            try:
                remote_size = int(r_size.stdout.strip().split()[-1])
                if remote_size == file_size:
                    logger.info("远端文件已存在且大小匹配 (%d bytes), 跳过传输: %s", file_size, remote_path)
                    return CommandResult(success=True, stdout=remote_path)
                logger.info("远端文件大小不匹配 (%d vs %d), 重新传输", remote_size, file_size)
            except (ValueError, IndexError):
                pass  # 无法解析大小，继续传输

        # 读取文件内容
        with open(local, "rb") as f:
            raw = f.read()

        # PS1 脚本自动添加 UTF-8 BOM:
        # Windows PowerShell 5.x 默认按系统 locale (GBK) 解码脚本,
        # UTF-8 编码的中文无 BOM 时会被误解析导致语法错误.
        # 仅当 .ps1 文件含非 ASCII 字符且无 BOM 时自动补上.
        if local.suffix == ".ps1" and not raw.startswith(b"\xef\xbb\xbf"):
            try:
                raw.decode("ascii")
            except UnicodeDecodeError:
                raw = b"\xef\xbb\xbf" + raw
                file_size = len(raw)
                logger.info("PS1 文件含非ASCII字符, 已自动添加 UTF-8 BOM (size %d→%d)", file_size - 3, file_size)

        content_b64 = base64.b64encode(raw).decode("ascii")

        # 确保远程目录存在
        remote_dir = remote_path.rsplit("\\", 1)[0]
        self.run_cmd(f'if not exist "{remote_dir}" mkdir "{remote_dir}"')

        # 给该目录加 Defender 白名单（幂等，防止实时扫描持续锁文件）
        self.ensure_defender_exclusion([remote_dir])

        # 先写入 .transfer 临时文件，全部完成后原子改名覆盖目标，
        # 规避源端杀软/进程对最终文件的持续占用导致的逐块重试（实测加速显著）
        transfer_path = f"{remote_path}.transfer"
        self.run_cmd(f'del "{transfer_path}" 2>nul', timeout=15)

        # 选择传输策略
        if file_size >= 1024 * 1024:
            # 大文件: run_cmd + powershell -Command (chunk 7000, 无 UTF-16LE 膨胀)
            logger.info("大文件模式: run_cmd + powershell (chunk=%d)", _CHUNK_CMD)
            r = self._transfer_file_cmd(content_b64, transfer_path, file_size, _CHUNK_CMD)
        else:
            # 小文件: run_ps base64 分块，固定 chunk 2800（跳过探测省 1-3 次往返）
            r = self._transfer_file_ps(content_b64, transfer_path, file_size, _CHUNK_PS)
        if not r.success:
            return r
        return self._finalize_transfer(transfer_path, remote_path, file_size)

    def ensure_defender_exclusion(self, dirs: list[str]) -> None:
        """给 Windows Defender 添加目录白名单（幂等），减少实时扫描导致的文件锁重试。"""
        if self._defender_excluded:
            return
        try:
            paths = ";".join(dirs)
            ps = (
                f"try {{ Add-MpPreference -ExclusionPath '{paths}' -ErrorAction Stop; 'EX_OK' }} "
                f"catch {{ 'EX_FAIL' }}"
            )
            r = self.run_ps(ps, timeout=30)
            if r.success and "EX_OK" in (r.stdout or ""):
                logger.info("Defender 白名单已添加: %s", paths)
                self._defender_excluded = True
            else:
                logger.debug("Defender 白名单添加失败(无权限或非Defender): %s",
                             (r.stdout or r.stderr or "")[:100])
        except Exception as e:
            logger.debug("Defender 白名单异常: %s", e)

    def _finalize_transfer(self, transfer_path: str, remote_path: str, file_size: int) -> CommandResult:
        """验证临时文件大小，然后 Move-Item -Force 原子改名覆盖目标。"""
        verify = self.run_cmd(f'for %I in ("{transfer_path}") do echo %~zI')
        if verify.success:
            try:
                remote_size = int(verify.stdout.strip().split()[-1])
                if remote_size != file_size:
                    logger.warning("临时文件大小不匹配: %d vs %d", file_size, remote_size)
                    return CommandResult(success=False,
                                         stderr=f"文件大小不匹配: {file_size} vs {remote_size}")
            except (ValueError, IndexError):
                pass
        rename_ps = (
            f"$s='{transfer_path}'; $d='{remote_path}'; "
            f"Move-Item -Force -Path $s -Destination $d -ErrorAction SilentlyContinue; "
            f"if(Test-Path '{remote_path}'){{ 'RENAME_OK' }} else {{ 'RENAME_FAIL' }}"
        )
        for attempt in range(1, 11):
            r = self.run_ps(rename_ps, timeout=30)
            if r.success and "RENAME_OK" in (r.stdout or ""):
                logger.info("文件传输完成: %s", remote_path)
                return CommandResult(success=True, stdout=remote_path)
            time.sleep(2)
            logger.warning("改名 %d/10 失败(目标被占用): %s", attempt, (r.stderr or "")[:120])
        return CommandResult(success=False, stderr=f"传输完成但改名失败(10次): {remote_path}")

    def _transfer_file_ps(self, content_b64: str, remote_path: str, file_size: int, chunk_size: int) -> CommandResult:
        """run_ps base64 分块传输（小文件，chunk ~2800 chars）。"""
        total_chunks = (len(content_b64) + chunk_size - 1) // chunk_size

        for i in range(0, len(content_b64), chunk_size):
            chunk = content_b64[i:i + chunk_size]
            chunk_idx = i // chunk_size

            mode = "Create" if chunk_idx == 0 else "Append"
            ps_script = (
                f"$bytes = [Convert]::FromBase64String('{chunk}')\n"
                f"$fs = [IO.File]::Open('{remote_path}', [IO.FileMode]::{mode}, [IO.FileAccess]::Write)\n"
                f"$fs.Write($bytes, 0, $bytes.Length)\n"
                f"$fs.Close()"
            )
            r = self.run_ps(ps_script)
            if not r.success:
                # 瞬时文件锁（杀软实时扫描等）重试同一块，最多 10 次
                for attempt in range(1, 11):
                    time.sleep(2)
                    r = self.run_ps(ps_script)
                    if r.success:
                        break
                    logger.warning("分块 %d/%d 重试 %d/10 失败: %s",
                                   chunk_idx + 1, total_chunks, attempt, (r.stderr or "")[:150])
            if not r.success:
                return CommandResult(
                    success=False,
                    stderr=f"分块 {chunk_idx}/{total_chunks} 写入失败(重试10次后仍失败): {r.stderr}",
                )

            if chunk_idx % 50 == 0:
                logger.debug("传输进度: %d/%d", chunk_idx + 1, total_chunks)

        return self._verify_transfer(remote_path, file_size)

    def _transfer_file_cmd(self, content_b64: str, remote_path: str, file_size: int, chunk_size: int) -> CommandResult:
        """
        run_cmd + powershell -Command 旁路传输（大文件，chunk ~7000 chars）。
        绕过 run_ps 的 UTF-16LE+base64 编码膨胀，chunk 大 2.5 倍。
        直接用 FileStream.Write 写二进制，无需 certutil 中转。
        """
        total_chunks = (len(content_b64) + chunk_size - 1) // chunk_size

        for i in range(0, len(content_b64), chunk_size):
            chunk = content_b64[i:i + chunk_size]
            chunk_idx = i // chunk_size

            mode = "Create" if chunk_idx == 0 else "Append"
            # run_cmd 发 powershell -Command，不经过 run_ps 的 UTF-16LE 编码
            cmd_str = (
                f'powershell -Command "$b=[Convert]::FromBase64String(\'{chunk}\');'
                f'$f=[IO.File]::Open(\'{remote_path}\',[IO.FileMode]::{mode},[IO.FileAccess]::Write);'
                f'$f.Write($b,0,$b.Length);$f.Close()"'
            )
            r = self.run_cmd(cmd_str)
            if not r.success:
                # 瞬时文件锁（杀软实时扫描等）重试同一块，最多 10 次
                for attempt in range(1, 11):
                    time.sleep(2)
                    r = self.run_cmd(cmd_str)
                    if r.success:
                        break
                    logger.warning("分块 %d/%d 重试 %d/10 失败: %s",
                                   chunk_idx + 1, total_chunks, attempt, (r.stderr or "")[:150])
            if not r.success:
                return CommandResult(
                    success=False,
                    stderr=f"分块 {chunk_idx}/{total_chunks} 写入失败(重试10次后仍失败): {r.stderr}",
                )

            if chunk_idx % 50 == 0:
                logger.debug("传输进度: %d/%d", chunk_idx + 1, total_chunks)

        return self._verify_transfer(remote_path, file_size)

    def _verify_transfer(self, remote_path: str, file_size: int) -> CommandResult:
        """验证远程文件大小匹配。"""
        verify = self.run_cmd(f'for %I in ("{remote_path}") do echo %~zI')
        if verify.success:
            try:
                remote_size = int(verify.stdout.strip().split()[-1])
                if remote_size != file_size:
                    logger.warning("文件大小不匹配: 本地=%d 远程=%d", file_size, remote_size)
                    return CommandResult(
                        success=False,
                        stderr=f"文件大小不匹配: {file_size} vs {remote_size}",
                    )
            except (ValueError, IndexError):
                logger.warning("无法解析远程文件大小: %s", verify.stdout)

        logger.info("文件传输完成: %s", remote_path)
        return CommandResult(success=True, stdout=remote_path)

    def file_exists(self, remote_path: str) -> bool:
        """检查远程文件是否存在。"""
        r = self.run_cmd(f'if exist "{remote_path}" (echo YES) else (echo NO)')
        return r.success and "YES" in r.stdout
