"""Windows 兼容性回归测试：vod_deliver.py 不得在 Windows 上因 os.getuid 崩溃。

Issue: developer-skill/vod-skill#3676 / developer-skill/huaweicloud-skills#959
场景: Windows 11 + Git Bash + Python 3.13.9 执行 deliver 时, _read_atomgit_token()
直接调用 os.getuid() 抛 AttributeError, 投递中断。
期望: 非 POSIX 平台跳过属主/权限位校验, deliver 可正常读取 auth.toml。

本文件移植自在途 merge request !851 (fix/issue-3676-vod-deliver-windows)，
并补充了环境变量凭据的隔离(setup: VOD_ATOMGIT_TOKEN 会短路 auth.toml 读取)。
"""

import os
import time
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
import sys

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import vod_deliver


class _WindowsOS:
    """模拟 Windows 的 os 模块: os.name == 'nt', 且不存在 getuid。"""

    name = "nt"

    def __getattr__(self, attr):
        if attr == "getuid":
            raise AttributeError(attr)
        return getattr(os, attr)


@pytest.fixture
def auth_home(tmp_path: Path) -> Path:
    home = tmp_path / ".atomcode"
    home.mkdir()
    auth = home / "auth.toml"
    auth.write_text(
        "access_token = 'test-access-token'\n"
        "refresh_token = 'test-refresh-token'\n"
        "expires_in = 86400\n"
        f"created_at = {int(time.time())}\n",
        encoding="utf-8",
    )
    return home


@pytest.fixture(autouse=True)
def _isolate_env_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """环境变量凭据优先于 auth.toml, 测试中必须移除, 否则断言会被短路。"""
    monkeypatch.delenv(vod_deliver._ATOMGIT_TOKEN_ENV, raising=False)


def _simulate_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """模拟 Windows: os 模块替换为 nt 且没有 getuid (AttributeError)。"""
    monkeypatch.setattr(vod_deliver, "os", _WindowsOS())


def test_windows_read_token_does_not_call_getuid(monkeypatch, auth_home):
    """Windows 下 _read_atomgit_token 不调用 os.getuid, 正常读取 auth.toml。"""
    _simulate_windows(monkeypatch)

    result = vod_deliver._read_atomgit_token(str(auth_home))

    assert result is not None
    assert result["access_token"] == "test-access-token"
    assert result["expires_in"] == 86400


def test_windows_read_token_missing_file_returns_none(monkeypatch, tmp_path):
    """Windows 下 auth.toml 不存在时返回 None, 不抛异常。"""
    _simulate_windows(monkeypatch)

    result = vod_deliver._read_atomgit_token(str(tmp_path / "no-such-dir"))

    assert result is None


def test_windows_resolve_token_success(monkeypatch, auth_home):
    """Windows 下 _resolve_atomgit_token 返回 success=True 而非崩溃。"""
    _simulate_windows(monkeypatch)

    result = vod_deliver._resolve_atomgit_token(str(auth_home))

    assert result["success"] is True
    assert result["access_token"] == "test-access-token"
    assert result["atomgit"]["status"] == "available"


def test_windows_resolve_token_unauthorized_returns_need_login(monkeypatch, tmp_path):
    """Windows 下 token 缺失时返回 need_login 结构化结果, 不崩溃。"""
    _simulate_windows(monkeypatch)

    result = vod_deliver._resolve_atomgit_token(str(tmp_path / "empty-dir"))

    assert result["success"] is False
    assert result["need_login"] is True
    assert "token" in result["message"].lower() or "login" in result["action"]


def test_posix_still_rejects_other_writable_parent(monkeypatch, auth_home):
    """POSIX 行为不变: 父目录 group/other 可写时拒绝读取。"""
    if os.name != "posix":
        pytest.skip("POSIX-only security branch")
    parent = auth_home
    os.chmod(parent, 0o777)

    result = vod_deliver._read_atomgit_token(str(parent))

    assert result is None


def test_posix_rejects_symlink_auth_file(monkeypatch, tmp_path):
    """POSIX 行为不变: 符号链接 auth.toml 一律拒绝。"""
    if os.name != "posix":
        pytest.skip("POSIX-only security branch")
    home = tmp_path / ".atomcode"
    home.mkdir()
    target = tmp_path / "real_auth.toml"
    target.write_text("access_token = 'x'\n", encoding="utf-8")
    os.symlink(target, home / "auth.toml")

    result = vod_deliver._read_atomgit_token(str(home))

    assert result is None


def test_posix_keeps_owner_permission_tightening(monkeypatch, auth_home):
    """POSIX 行为不变: 正常属主 + 0600 文件可读取。"""
    if os.name != "posix":
        pytest.skip("POSIX-only security branch")
    auth = auth_home / "auth.toml"
    os.chmod(auth, 0o600)
    os.chmod(auth_home, 0o700)

    result = vod_deliver._read_atomgit_token(str(auth_home))

    assert result is not None
    assert result["access_token"] == "test-access-token"


def test_env_token_overrides_auth_file(monkeypatch, auth_home):
    """issue #114 问题9: VOD_ATOMGIT_TOKEN 优先于明文 auth.toml。"""
    monkeypatch.setenv(vod_deliver._ATOMGIT_TOKEN_ENV, "env-token")
    _simulate_windows(monkeypatch)

    result = vod_deliver._read_atomgit_token(str(auth_home))

    assert result is not None
    assert result["access_token"] == "env-token"
    assert result["_source"] == f"env:{vod_deliver._ATOMGIT_TOKEN_ENV}"


def test_env_token_works_without_auth_file(monkeypatch, tmp_path):
    """issue #114 问题9: 完全没有 auth.toml 时也能只靠环境变量工作。"""
    monkeypatch.setenv(vod_deliver._ATOMGIT_TOKEN_ENV, "env-token")
    _simulate_windows(monkeypatch)

    result = vod_deliver._read_atomgit_token(str(tmp_path / "no-such-dir"))

    assert result is not None
    assert result["access_token"] == "env-token"
