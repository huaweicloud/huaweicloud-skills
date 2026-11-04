"""Standard-library runtime helpers for Windows, macOS and Linux (Python 3.9+)."""
from contextlib import contextmanager
from datetime import datetime
import errno
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

IS_WINDOWS = sys.platform == 'win32'
if IS_WINDOWS:
    import msvcrt as _locking_backend
else:
    import fcntl as _locking_backend

_NAMING_LOCK = threading.Lock()
_NAMING_STAMP = ''
_GENERATED_NAMES = set()


def unique_name(base, *, max_length=32, truncate=True, namespace='output') -> str:
    """Suggest a timestamped name; same-process collisions use a short counter."""
    global _NAMING_STAMP
    if not isinstance(base, str) or not re.fullmatch(r'[\u4e00-\u9fa5A-Za-z0-9_./ -]+', base.strip()):
        raise ValueError('命名基名须为非空的合法输出名字符')
    if not isinstance(max_length, int) or isinstance(max_length, bool) or not 18 <= max_length <= 64:
        raise ValueError('自动命名长度须为 18–64 字符，包含完整后缀')
    prefix = base.strip()
    stamp = datetime.now().strftime('%m%d%H%M%S')
    with _NAMING_LOCK:
        if stamp != _NAMING_STAMP:
            _GENERATED_NAMES.clear()
            _NAMING_STAMP = stamp
        ordinal = 1
        while True:
            suffix = '-' + stamp + (('-' + str(ordinal)) if ordinal > 1 else '')
            if len(suffix) >= max_length:
                raise ValueError('当前秒可用名称已耗尽，请稍后重试')
            if not truncate and len(prefix) + len(suffix) > max_length:
                raise ValueError('完整名称（含时间戳和序号）超过 ' + str(max_length) + ' 字符，请缩短管线名或步骤短名')
            name = prefix[:max_length - len(suffix)].rstrip() + suffix
            key = (namespace, name)
            if key not in _GENERATED_NAMES:
                _GENERATED_NAMES.add(key)
                return name
            ordinal += 1


def step_name(pipeline, step, *, namespace='output') -> str:
    """Keep the complete pipeline and stage prefix; never silently cut either."""
    if not isinstance(pipeline, str) or not re.fullmatch(r'[\u4e00-\u9fa5A-Za-z0-9_./-]{1,48}', pipeline):
        raise ValueError('管线名须为 1–48 个合法任务名字符')
    if not isinstance(step, str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,47}', step):
        raise ValueError('步骤短名须为合法 ASCII 步骤 ID')
    return unique_name(pipeline + '-' + step, max_length=64, truncate=False, namespace=namespace)


def _windows_lock(file, blocking) -> None:
    # CRT locks a byte range from the CURRENT offset, even beyond EOF. Do not
    # write an initialization byte: another process may already hold that byte.
    while True:
        file.seek(0)
        try:
            _locking_backend.locking(file.fileno(), _locking_backend.LK_NBLCK, 1)
            break
        except OSError as error:
            busy = error.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}
            if not busy:
                raise
            if not blocking:
                raise BlockingIOError(errno.EAGAIN, '文件锁正被其他进程持有') from error
            time.sleep(.05)


@contextmanager
def file_lock(path, *, blocking=True):
    """Hold an OS-backed exclusive lock; closing/crashing releases ownership."""
    path = Path(path)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_BINARY', 0), 0o600)
    with os.fdopen(descriptor, 'r+b', buffering=0) as file:
        if IS_WINDOWS:
            _windows_lock(file, blocking)
        else:
            flags = _locking_backend.LOCK_EX
            if not blocking:
                flags |= _locking_backend.LOCK_NB
            _locking_backend.flock(file.fileno(), flags)
        try:
            yield file
        finally:
            if IS_WINDOWS:
                file.seek(0)
                _locking_backend.locking(file.fileno(), _locking_backend.LK_UNLCK, 1)
            else:
                _locking_backend.flock(file.fileno(), _locking_backend.LOCK_UN)


def atomic_replace(source, target, *, timeout=5) -> None:
    """Retry transient Windows sharing violations without deleting the old file."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            os.replace(source, target)
            break
        except PermissionError:
            if not IS_WINDOWS or time.monotonic() >= deadline:
                raise
            time.sleep(.05)


def detached_process_options() -> dict:
    if IS_WINDOWS:
        return {**hidden_process_options(), 'creationflags': subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
    return {'start_new_session': True}


def hidden_process_options() -> dict:
    """Hide the background Web service console on Windows."""
    if IS_WINDOWS:
        # Do not combine with DETACHED_PROCESS: Windows ignores CREATE_NO_WINDOW
        # in that combination. The background server uses a new process group instead.
        options = {'creationflags': subprocess.CREATE_NO_WINDOW}
        startup_class = getattr(subprocess, 'STARTUPINFO', None)
        if startup_class is not None:
            startup = startup_class()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = subprocess.SW_HIDE
            options['startupinfo'] = startup
        return options
    return {}


def utf8_environment() -> dict:
    return {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'}


def configure_console() -> None:
    # Redirected Windows stdout/stderr otherwise use an ANSI code page. Keep
    # machine-readable output and background diagnostics consistently UTF-8.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='backslashreplace')
