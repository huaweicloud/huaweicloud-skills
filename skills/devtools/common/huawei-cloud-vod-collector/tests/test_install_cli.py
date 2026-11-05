"""install_cli.py 回归测试(issue #929 跨平台安装入口 + Python fallback + UTF-8 固化)。

全部离线: 用 `--manifest-file` + `--package-dir` 驱动, 安装目录固定为 tmp_path,
不联网、不写入 HOME。

运行: python -m pytest <SKILL_DIR>/tests/test_install_cli.py -q
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import stat
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
INSTALL_CLI = SCRIPTS_DIR / "install_cli.py"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import install_cli  # noqa: E402

PACKAGE_NAME = "skill-quality-cli-1.1.8-linux-arm64.tar.gz"
DOWNLOAD_URL = f"https://example.invalid/quality/cli/{PACKAGE_NAME}"
WHERE_EXE = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "where.exe"
CAN_RUN_CMD_LAUNCHER = os.name == "nt" and WHERE_EXE.is_file()
FAKE_BIN = b"\x7fELF fake native binary (not a real ELF)\n"
# 复刻 issue #929 的核心: 官方 cli_entry.py 的 cmd_run 用 subprocess.run(..., text=True)
# 且未指定 encoding, 中文 Windows 下按 GBK 解码子进程输出会 UnicodeDecodeError。
CLI_ENTRY_SOURCE = (
    "import subprocess, sys\n"
    "\n"
    "CHILD = \"import sys; sys.stdout.buffer.write('\\u4e2d\\u6587\\u8f93\\u51fa'.encode('utf-8'))\"\n"
    "child = subprocess.run([sys.executable, '-c', CHILD], capture_output=True, text=True)\n"
    "print('CLI_ENTRY_OK encoding=' + str(sys.stdout.encoding))\n"
    "print('child_text=' + child.stdout.strip())\n"
).encode("utf-8")
CLI_REPORTING_SOURCE = b"# cli_reporting stub\n"


# ---------------------------------------------------------------------------
# 离线夹具: 自造 tar.gz 包 + 清单
# ---------------------------------------------------------------------------

def build_package(
    path: Path,
    *,
    include_bin: bool = True,
    include_entry: bool = True,
    include_reporting: bool = True,
    bin_bytes: bytes | None = None,
) -> str:
    """生成一个含 wrapper/ELF/纯 Python 的 tar.gz, 返回其 sha256。"""
    path.parent.mkdir(parents=True, exist_ok=True)

    def add(tar: tarfile.TarFile, name: str, data: bytes, mode: int = 0o644) -> None:
        info = tarfile.TarInfo(name)
        info.size = len(data)
        info.mode = mode
        tar.addfile(info, io.BytesIO(data))

    with tarfile.open(path, "w:gz") as tar:
        add(tar, "skill-quality-cli", b"#!/bin/sh\necho official-wrapper\n", 0o755)
        if include_bin:
            add(tar, "skill-quality-cli.bin", FAKE_BIN if bin_bytes is None else bin_bytes, 0o755)
        if include_entry:
            add(tar, "skill-quality-cli.d/cli_entry.py", CLI_ENTRY_SOURCE)
        if include_reporting:
            add(tar, "skill-quality-cli.d/cli_reporting.py", CLI_REPORTING_SOURCE)
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Fixture:
    def __init__(self, tmp_path: Path, *, platform_tag: str, sha256: str, include_sha: bool = True):
        self.tmp_path = tmp_path
        self.package_dir = tmp_path / "packages"
        self.package_dir.mkdir(parents=True, exist_ok=True)
        self.package_path = self.package_dir / PACKAGE_NAME
        self.sha256 = sha256
        self.manifest = tmp_path / "manifest.json"
        package: dict = {
            "platform": platform_tag,
            "download_url": DOWNLOAD_URL,
            "format": "tar.gz",
        }
        if include_sha:
            package["sha256"] = sha256
        self.manifest.write_text(
            json.dumps({"version": "1.1.8", "packages": [package]}, ensure_ascii=False),
            encoding="utf-8",
        )


def make_fixture(
    tmp_path: Path,
    *,
    platform_tag: str = "linux-arm64",
    sha_override: str | None = None,
    include_sha: bool = True,
    include_bin: bool = True,
    include_entry: bool = True,
    bin_bytes: bytes | None = None,
    manifest_bom: bool = False,
) -> Fixture:
    probe = Fixture.__new__(Fixture)
    package_dir = tmp_path / "packages"
    sha256 = build_package(
        package_dir / PACKAGE_NAME,
        include_bin=include_bin,
        include_entry=include_entry,
        bin_bytes=bin_bytes,
    )
    probe.package_dir = package_dir
    probe.package_path = package_dir / PACKAGE_NAME
    probe.sha256 = sha256
    probe.manifest = tmp_path / "manifest.json"
    package: dict = {
        "platform": platform_tag,
        "download_url": DOWNLOAD_URL,
        "format": "tar.gz",
    }
    if include_sha:
        package["sha256"] = sha_override if sha_override is not None else sha256
    payload = json.dumps({"version": "1.1.8", "packages": [package]}, ensure_ascii=False).encode("utf-8")
    if manifest_bom:
        payload = b"\xef\xbb\xbf" + payload  # PowerShell 5.1 Set-Content -Encoding utf8 的产物
    probe.manifest.write_bytes(payload)
    return probe


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(INSTALL_CLI), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
        env=env,
    )


def install_args(fixture: Fixture, install_dir: Path, platform_tag: str, *extra: str) -> list[str]:
    return [
        "--install-dir", str(install_dir),
        "--manifest-file", str(fixture.manifest),
        "--package-dir", str(fixture.package_dir),
        "--platform", platform_tag,
        *extra,
    ]


def _dir_is_empty(path: Path) -> bool:
    return (not path.exists()) or not any(path.iterdir())


# ---------------------------------------------------------------------------
# a) 平台无匹配 → python-fallback
# ---------------------------------------------------------------------------

def test_python_fallback_on_unsupported_platform(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    install_dir = tmp_path / "bin"

    proc = run_cli(*install_args(fixture, install_dir, "win32-x86_64", "--json"), cwd=tmp_path)

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["success"] is True
    assert payload["mode"] == "python-fallback"
    assert payload["version"] == "1.1.8"
    assert payload["platform"] == "win32-x86_64"
    assert payload["sha256_verified"] is True
    assert payload["utf8_forced"] is True
    assert payload["install_dir"] == str(install_dir)

    # 只装纯 Python 与启动器, 绝不安装 linux ELF
    assert (install_dir / "skill-quality-cli.d" / "cli_entry.py").is_file()
    assert (install_dir / "skill-quality-cli.d" / "cli_reporting.py").is_file()
    assert not (install_dir / "skill-quality-cli.bin").exists()

    launcher_sh = install_dir / "skill-quality-cli"
    launcher_cmd = install_dir / "skill-quality-cli.cmd"
    assert launcher_sh.is_file()
    assert launcher_cmd.is_file()
    assert payload["launcher"] == [str(launcher_sh), str(launcher_cmd)]

    sh_text = launcher_sh.read_text(encoding="utf-8")
    cmd_text = launcher_cmd.read_text(encoding="utf-8")
    assert "export PYTHONUTF8=1" in sh_text
    assert "export PYTHONIOENCODING=utf-8" in sh_text
    assert 'exec "$PY" "$SELF_DIR/skill-quality-cli.d/cli_entry.py" "$@"' in sh_text
    assert "set PYTHONUTF8=1" in cmd_text
    assert "set PYTHONIOENCODING=utf-8" in cmd_text
    assert "cli_entry.py" in cmd_text
    # task-14 / L2: fallback 模式两个启动器都不得引用 .bin
    assert "skill-quality-cli.bin" not in sh_text
    assert "skill-quality-cli.bin" not in cmd_text

    if os.name != "nt":
        assert stat.S_IMODE(launcher_sh.stat().st_mode) == 0o755


# ---------------------------------------------------------------------------
# b) sha256 不匹配 → fail-closed, 无任何产物
# ---------------------------------------------------------------------------

def test_sha256_mismatch_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path, sha_override="0" * 64)
    install_dir = tmp_path / "bin"

    proc = run_cli(*install_args(fixture, install_dir, "linux-arm64", "--json"), cwd=tmp_path)

    assert proc.returncode != 0
    assert "SHA256" in proc.stderr
    assert json.loads(proc.stdout)["success"] is False
    assert _dir_is_empty(install_dir)


def test_sha256_mismatch_leaves_no_temp_files(tmp_path: Path) -> None:
    """校验失败时下载物必须被清理(临时目录不留包, 也不落到 install-dir)。"""
    fixture = make_fixture(tmp_path, sha_override="f" * 64)
    install_dir = tmp_path / "bin"

    proc = run_cli(*install_args(fixture, install_dir, "linux-arm64"), cwd=tmp_path)

    assert proc.returncode != 0
    assert _dir_is_empty(install_dir)


# ---------------------------------------------------------------------------
# c) 清单缺 sha256 → 拒绝安装
# ---------------------------------------------------------------------------

def test_manifest_without_sha256_is_rejected(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path, include_sha=False)
    install_dir = tmp_path / "bin"

    proc = run_cli(*install_args(fixture, install_dir, "linux-arm64", "--json"), cwd=tmp_path)

    assert proc.returncode != 0
    assert "sha256" in proc.stderr
    assert json.loads(proc.stdout)["success"] is False
    assert _dir_is_empty(install_dir)


# ---------------------------------------------------------------------------
# d) --no-python-fallback + 无匹配包 → 失败
# ---------------------------------------------------------------------------

def test_no_python_fallback_rejects_unsupported_platform(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    install_dir = tmp_path / "bin"

    proc = run_cli(*install_args(fixture, install_dir, "win32-x86_64", "--no-python-fallback"), cwd=tmp_path)

    assert proc.returncode != 0
    assert "python-fallback" in proc.stderr
    assert _dir_is_empty(install_dir)


# ---------------------------------------------------------------------------
# e) 平台匹配 → native
# ---------------------------------------------------------------------------

def test_native_install_when_platform_matches(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    install_dir = tmp_path / "bin"

    proc = run_cli(*install_args(fixture, install_dir, "linux-arm64", "--json"), cwd=tmp_path)

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["mode"] == "native"
    assert payload["sha256_verified"] is True

    bin_path = install_dir / "skill-quality-cli.bin"
    assert bin_path.is_file()
    assert (install_dir / "skill-quality-cli.d" / "cli_entry.py").is_file()
    assert (install_dir / "skill-quality-cli").is_file()
    assert (install_dir / "skill-quality-cli.cmd").is_file()
    sh_text = (install_dir / "skill-quality-cli").read_text(encoding="utf-8")
    cmd_text = (install_dir / "skill-quality-cli.cmd").read_text(encoding="utf-8")
    # linux-arm64 native: sh 启动器认 .bin; .cmd **不认**(消除 linux ELF 被 Windows 复用的静默 no-op)
    assert 'if [ -x "$SELF_DIR/skill-quality-cli.bin" ]' in sh_text
    assert "skill-quality-cli.bin" not in cmd_text
    assert "enabledelayedexpansion" in cmd_text
    if os.name != "nt":
        assert stat.S_IMODE(bin_path.stat().st_mode) == 0o755
        assert stat.S_IMODE((install_dir / "skill-quality-cli").stat().st_mode) == 0o755


def test_native_windows_platform_marks_cmd_bin_branch(tmp_path: Path) -> None:
    """task-14 / L2-1: win32 原生安装 → 只有 .cmd 认 .bin, 且退出码用延迟展开传播。"""
    fixture = make_fixture(tmp_path, platform_tag="win32-x86_64")
    install_dir = tmp_path / "bin"

    proc = run_cli(*install_args(fixture, install_dir, "win32-x86_64", "--json"), cwd=tmp_path)

    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["mode"] == "native"
    assert (install_dir / "skill-quality-cli.bin").is_file()

    cmd_text = (install_dir / "skill-quality-cli.cmd").read_text(encoding="utf-8")
    sh_text = (install_dir / "skill-quality-cli").read_text(encoding="utf-8")
    assert "skill-quality-cli.bin" in cmd_text
    assert "enabledelayedexpansion" in cmd_text
    assert 'set "RC=!ERRORLEVEL!"' in cmd_text
    assert 'if "!RC!"=="9009" goto :fallback' in cmd_text
    assert "exit /b !RC!" in cmd_text
    assert ":fallback" in cmd_text
    assert "skill-quality-cli.bin" not in sh_text


def test_launcher_bin_branch_is_platform_gated() -> None:
    """单元级: prefer_native_bin 决定是否生成 .bin 分支。"""
    for launcher in (install_cli.posix_launcher, install_cli.windows_launcher):
        assert "skill-quality-cli.bin" not in launcher()
        assert "skill-quality-cli.bin" in launcher(prefer_native_bin=True)
    assert "enabledelayedexpansion" in install_cli.windows_launcher(prefer_native_bin=True)
    assert "!RC!" in install_cli.windows_launcher(prefer_native_bin=True)
    assert "!RC!" not in install_cli.windows_launcher(prefer_native_bin=False)


@pytest.mark.skipif(not CAN_RUN_CMD_LAUNCHER, reason="仅在 Windows + where.exe 环境实跑 .cmd 退出码传播")
def test_cmd_launcher_propagates_native_exit_code(tmp_path: Path) -> None:
    """task-14 / L2-1 实跑: .bin 换成真实 Windows 程序(where.exe), 非零退出码必须原样传播。

    未修版本用块内 `%ERRORLEVEL%`(解析期展开) → 被掩盖成 0; 实测 where.exe /Q 命中
    不存在的模式返回 1。非 Windows 或找不到 where.exe 时本用例跳过(见报告)。
    """
    fixture = make_fixture(tmp_path, platform_tag="win32-x86_64", bin_bytes=WHERE_EXE.read_bytes())
    install_dir = tmp_path / "bin"
    proc = run_cli(*install_args(fixture, install_dir, "win32-x86_64"), cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr

    run = subprocess.run(
        [os.environ.get("COMSPEC", "cmd.exe"), "/c",
         str(install_dir / "skill-quality-cli.cmd"), "/Q", "definitely-not-existing-xyz-929"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(tmp_path), env=dict(os.environ),
    )
    assert run.returncode == 1, (run.returncode, run.stdout, run.stderr)


def test_manifest_with_utf8_bom_is_accepted(tmp_path: Path) -> None:
    """task-14 / L3: PowerShell 5.1 `Set-Content -Encoding utf8` 带 BOM 的清单必须能装。"""
    fixture = make_fixture(tmp_path, manifest_bom=True)
    install_dir = tmp_path / "bin"

    proc = run_cli(*install_args(fixture, install_dir, "win32-x86_64", "--json"), cwd=tmp_path)

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["success"] is True
    assert payload["mode"] == "python-fallback"
    assert (install_dir / "skill-quality-cli.d" / "cli_entry.py").is_file()
    assert not (install_dir / "skill-quality-cli.bin").exists()


# ---------------------------------------------------------------------------
# f) --dry-run → 不写文件, exit 0
# ---------------------------------------------------------------------------

def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    install_dir = tmp_path / "bin"

    proc = run_cli(*install_args(fixture, install_dir, "win32-x86_64", "--dry-run"), cwd=tmp_path)

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["dry_run"] is True
    assert payload["mode"] == "python-fallback"
    assert payload["success"] is True
    assert _dir_is_empty(install_dir)


# ---------------------------------------------------------------------------
# 其他契约点: 缺 cli_entry.py / --force / 单元行为
# ---------------------------------------------------------------------------

def test_package_without_cli_entry_fails(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path, include_entry=False)
    install_dir = tmp_path / "bin"

    proc = run_cli(*install_args(fixture, install_dir, "win32-x86_64"), cwd=tmp_path)

    assert proc.returncode != 0
    assert "cli_entry.py" in proc.stderr
    assert _dir_is_empty(install_dir)


def test_force_reinstall_cleans_stale_artifacts(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    install_dir = tmp_path / "bin"

    first = run_cli(*install_args(fixture, install_dir, "win32-x86_64"), cwd=tmp_path)
    assert first.returncode == 0, first.stderr

    stale = install_dir / "skill-quality-cli.d" / "stale_module.py"
    stale.write_text("# stale\n", encoding="utf-8")

    second = run_cli(*install_args(fixture, install_dir, "win32-x86_64", "--force"), cwd=tmp_path)
    assert second.returncode == 0, second.stderr
    assert not stale.exists()
    assert (install_dir / "skill-quality-cli.d" / "cli_entry.py").is_file()
    assert not (install_dir / "skill-quality-cli.bin").exists()


def test_launcher_runs_entry_with_utf8_forced(tmp_path: Path) -> None:
    """启动器实际可用性 + 强制 UTF-8 生效(issue #929 核心回归)。

    Windows 走 .cmd(经 shim python), 其余平台走 sh 启动器。子进程环境**清空**
    PYTHONUTF8/PYTHONIOENCODING, 因此 UTF-8 只能来自启动器本身:
      - cli_entry.py 打印的 sys.stdout.encoding 必须是 utf-8;
      - cli_entry.py 内部 `subprocess.run(..., text=True)` 必须能解码子进程的
        UTF-8 中文输出(这正是中文 Windows 上 GBK 失败、PYTHONUTF8=1 修好的点)。
    """
    fixture = make_fixture(tmp_path)
    install_dir = tmp_path / "bin"
    proc = run_cli(*install_args(fixture, install_dir, "win32-x86_64"), cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    entry = install_dir / "skill-quality-cli.d" / "cli_entry.py"

    env = dict(os.environ)
    env.pop("PYTHONUTF8", None)
    env.pop("PYTHONIOENCODING", None)
    if os.name == "nt":
        shim_dir = tmp_path / "shim"
        shim_dir.mkdir()
        (shim_dir / "python.cmd").write_text(f'@"{sys.executable}" %*\r\n', encoding="ascii")
        # 只保留 shim 目录: where py 找不到, 启动器回退到 python(即 shim)
        env["PATH"] = str(shim_dir)
        command = [os.environ.get("COMSPEC", "cmd.exe"), "/c", str(install_dir / "skill-quality-cli.cmd")]
    else:
        env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
        command = ["sh", str(install_dir / "skill-quality-cli")]

    run = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                         errors="replace", cwd=str(tmp_path), env=env)
    assert run.returncode == 0, (run.stdout, run.stderr)
    assert "CLI_ENTRY_OK" in run.stdout
    assert "encoding=utf-8" in run.stdout.lower()
    # PYTHONUTF8=1 让 text=True 的子进程解码也变成 UTF-8(否则中文 Windows 报 GBK 解码错误)
    assert "child_text=中文输出" in run.stdout

    if os.name == "nt":
        # 反证: 同一条 cli_entry.py 不经启动器直接跑, 在中文 Windows 上必然解码失败
        direct = subprocess.run([sys.executable, str(entry)], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", cwd=str(tmp_path), env=env)
        assert direct.returncode != 0 or "CLI_ENTRY_OK" not in direct.stdout


def test_detect_platform_tag_shape() -> None:
    tag = install_cli.detect_platform_tag()
    assert "-" in tag
    assert tag.split("-")[0] in {
        "linux", "darwin", "win32", "cygwin", "msys", "freebsd", "openbsd", "netbsd",
    } or tag.split("-")[0].startswith("linux")


def test_default_install_dir_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "custom-bin"
    monkeypatch.setenv("SQC_INSTALL_DIR", str(target))
    assert install_cli.default_install_dir() == target

    monkeypatch.delenv("SQC_INSTALL_DIR")
    fallback = install_cli.default_install_dir()
    assert fallback.name == "bin" and fallback.parent.name == ".local"


def test_select_package_prefers_native_targz_then_fallback() -> None:
    packages = [
        {"platform": "linux-arm64", "download_url": "https://x/p.tar.gz", "format": "tar.gz", "sha256": "a" * 64},
        {"platform": "linux-x86_64", "download_url": "https://x/q.tar.gz", "format": "tar.gz", "sha256": "b" * 64},
    ]
    native, mode = install_cli.select_package(packages, "linux-x86_64", allow_fallback=True)
    assert mode == "native" and native["platform"] == "linux-x86_64"

    fallback, mode = install_cli.select_package(packages, "win32-x86_64", allow_fallback=True)
    assert mode == "python-fallback" and fallback["platform"] == "linux-arm64"

    none_pkg, none_mode = install_cli.select_package(packages, "win32-x86_64", allow_fallback=False)
    assert none_pkg is None and none_mode is None
