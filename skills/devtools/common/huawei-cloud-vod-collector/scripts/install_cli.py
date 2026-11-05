#!/usr/bin/env python3
"""install_cli.py — skill-quality-cli 的本地/跨平台安装入口(修复 issue #929)。

背景(issue #929): 官方发布通道
https://skillsapi.developer.myhuaweicloud.com/api/quality/cli/latest
当前只提供 `linux-arm64` 一个 tar.gz 包; inject 生成的 `scripts/install_cli.sh`
用 `uname -m` 只映射 linux-x86_64 / linux-arm64, Windows 上必然失败。另外官方
`skill-quality-cli.d/cli_entry.py` 的 `cmd_run` 使用 `subprocess.run(..., text=True)`
却未指定 encoding, 中文 Windows 会回退 GBK 导致 UnicodeDecodeError(中文输出丢失)。

本文件与 inject 生成的 `install_cli.sh` **并存**(不替换、不修改它), 提供一个跨平台入口:

  1. 始终 SHA256 fail-closed: 清单缺 sha256、或实际值不符 → 立即失败、清理临时文件、
     绝不安装(供应链安全, 与 install_cli.sh 同口径);
  2. 平台匹配到原生包 → `native` 模式: 安装 `skill-quality-cli.bin`(0755) +
     `.d/cli_entry.py` + `.d/cli_reporting.py` + 启动器(优先 ELF, 否则 exec python);
  3. 平台无匹配 → `python-fallback` 模式: 从清单内任一 tar.gz 包中**只提取纯 Python**
     的 `.d/cli_entry.py` 与 `.d/cli_reporting.py`, **绝不安装 linux ELF**;
  4. 两种模式都写 POSIX(sh) 与 Windows(.cmd) 启动器, 并固化
     `PYTHONUTF8=1` / `PYTHONIOENCODING=utf-8`: PEP 540 让 cli_entry.py 内子进程的
     默认编码变为 UTF-8, 这是 issue 报告人手工跑通的临时办法, 现在固化成安装产物。

仅使用标准库; 只在读取清单 / 下载包时联网(urllib), 不执行任何外部安装脚本。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform as platform_module
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

DEFAULT_MANIFEST_URL = "https://skillsapi.developer.myhuaweicloud.com/api/quality/cli/latest"

LAUNCHER_SH = "skill-quality-cli"
LAUNCHER_CMD = "skill-quality-cli.cmd"
NATIVE_BIN = "skill-quality-cli.bin"
AUX_DIR = "skill-quality-cli.d"
CLI_ENTRY = f"{AUX_DIR}/cli_entry.py"
CLI_REPORTING = f"{AUX_DIR}/cli_reporting.py"

# 与官方 cli_entry.py 的 get_platform_tag() 同口径: <os>-<arch>
_ARCH_ALIASES = {
    "x86_64": "x86_64",
    "amd64": "x86_64",
    "aarch64": "arm64",
    "arm64": "arm64",
    "i386": "i686",
    "i686": "i686",
    "armv7l": "armv7l",
}


class InstallError(Exception):
    """可预期的安装失败: 统一转成中文错误信息 + 退出码 1。"""


def default_install_dir() -> Path:
    """默认安装目录: SQC_INSTALL_DIR > $HOME/.local/bin(Windows 用 %USERPROFILE%)。"""
    env_dir = os.environ.get("SQC_INSTALL_DIR")
    if env_dir:
        return Path(env_dir).expanduser()
    home = os.environ.get("USERPROFILE") if os.name == "nt" else os.environ.get("HOME")
    if not home:
        home = os.path.expanduser("~")
    return Path(home) / ".local" / "bin"


def detect_platform_tag() -> str:
    """按 sys.platform + platform.machine() 推导平台标签(可用 --platform 覆盖)。"""
    machine = (platform_module.machine() or "").lower()
    arch = _ARCH_ALIASES.get(machine, machine or "unknown")
    if sys.platform.startswith("linux"):
        os_tag = "linux"
    elif sys.platform == "darwin":
        os_tag = "darwin"
    elif sys.platform in ("win32", "cygwin", "msys"):
        os_tag = "win32"
    else:
        os_tag = sys.platform
    return f"{os_tag}-{arch}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_targz(package: dict) -> bool:
    """包是否为 tar.gz(纯 Python 的 .d/*.py 只存在于 tar.gz 内)。"""
    fmt = str(package.get("format") or "").lower()
    if fmt in ("tar.gz", "tgz"):
        return True
    url = str(package.get("download_url") or "").lower().split("?")[0]
    return url.endswith(".tar.gz") or url.endswith(".tgz")


def select_package(packages: list, platform_tag: str, allow_fallback: bool) -> tuple[dict | None, str | None]:
    """选择安装包: 优先本机平台(且优先 tar.gz), 否则(允许时)任一 tar.gz 走 Python fallback。"""
    matched = [p for p in packages if isinstance(p, dict) and str(p.get("platform") or "") == platform_tag]
    matched_targz = [p for p in matched if is_targz(p)]
    if matched_targz:
        return matched_targz[0], "native"
    if matched:
        # 平台匹配但非 tar.gz: 交给解压阶段报"仅支持 tar.gz", 不静默换包
        return matched[0], "native"
    if not allow_fallback:
        return None, None
    fallback = [p for p in packages if isinstance(p, dict) and is_targz(p)]
    if fallback:
        return fallback[0], "python-fallback"
    return None, None


def load_manifest(manifest_file: str | None, manifest_url: str) -> dict:
    """读取清单: --manifest-file 为离线模式, 否则 urllib 拉取 manifest_url。"""
    if manifest_file:
        path = Path(manifest_file)
        if not path.is_file():
            raise InstallError(f"清单文件不存在: {path}")
        # utf-8-sig: 容忍 PowerShell 5.1 `Set-Content -Encoding utf8` 写出的 UTF-8 BOM(task-14 / L3)
        raw = path.read_text(encoding="utf-8-sig")
    else:
        request = urllib.request.Request(manifest_url, headers={"User-Agent": "install_cli.py/issue-929"})
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8-sig")
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise InstallError(f"清单不是合法 JSON: {exc}")
    if not isinstance(data, dict):
        raise InstallError("清单格式错误: 顶层不是 JSON 对象")
    return data


def resolve_local_package(package: dict, package_dir: str | None, tmp_dir: Path) -> Path:
    """取包: --package-dir 时按 download_url 的 basename 取本地包; 否则联网下载/本地路径。"""
    url = str(package.get("download_url") or "").strip()
    if not url:
        raise InstallError("清单包缺少 download_url")
    name = os.path.basename(url.split("?")[0]) or "skill-quality-cli.tar.gz"
    if package_dir:
        candidate = Path(package_dir) / name
        if candidate.is_file():
            return candidate
        local = Path(url)
        if local.is_file():
            return local
        raise InstallError(f"离线包目录中找不到 {name}: {package_dir}")
    if re.match(r"^https?://", url, re.IGNORECASE):
        dest = tmp_dir / name
        request = urllib.request.Request(url, headers={"User-Agent": "install_cli.py/issue-929"})
        with urllib.request.urlopen(request, timeout=60) as response:
            with open(dest, "wb") as handle:
                shutil.copyfileobj(response, handle)
        return dest
    local = Path(url)
    if local.is_file():
        return local
    raise InstallError(f"无法获取安装包: {url}")


def _normalized_member_name(name: str) -> str:
    return name.replace("\\", "/").lstrip("./").strip("/")


def read_tar_members(tar_path: Path, wanted: tuple[str, ...]) -> dict[str, bytes]:
    """只读取指定成员的内容(不落盘、不使用 extractall, 天然规避路径穿越)。"""
    found: dict[str, bytes] = {}
    with tarfile.open(tar_path, "r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            name = _normalized_member_name(member.name)
            if name not in wanted or name in found:
                continue
            extracted = tar.extractfile(member)
            if extracted is not None:
                found[name] = extracted.read()
    return found


def posix_launcher(prefer_native_bin: bool = False) -> str:
    """POSIX 启动器: 固化 UTF-8; 只有本机原生包是 POSIX 产物时才优先 ELF, 否则直接 exec python。

    prefer_native_bin=False(native 为 win32 产物 / python-fallback)时不写 `.bin` 分支,
    避免在共享安装目录里错跑异平台二进制(task-14 / L2)。
    """
    lines = [
        "#!/bin/sh",
        "# install_cli.py 生成(issue #929): 强制 UTF-8, 避免中文环境下子进程按 GBK 解码失败",
        "export PYTHONUTF8=1",
        "export PYTHONIOENCODING=utf-8",
        'SELF_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)',
    ]
    if prefer_native_bin:
        lines.extend([
            'if [ -x "$SELF_DIR/skill-quality-cli.bin" ]; then',
            '    exec "$SELF_DIR/skill-quality-cli.bin" "$@"',
            "fi",
        ])
    lines.extend([
        "for PY in python3 python py; do",
        '    if command -v "$PY" >/dev/null 2>&1; then',
        '        exec "$PY" "$SELF_DIR/skill-quality-cli.d/cli_entry.py" "$@"',
        "    fi",
        "done",
        'printf \'%s\\n\' "错误: 未找到 python3/python, 无法启动 skill-quality-cli" >&2',
        "exit 1",
        "",
    ])
    return "\n".join(lines)


def windows_launcher(prefer_native_bin: bool = False) -> str:
    """Windows 启动器(.cmd): 固化 UTF-8; 只有本机原生包是 Windows 产物时才尝试 `.bin`。

    - `setlocal enabledelayedexpansion` + `!RC!`: 块内 `%ERRORLEVEL%` 是**解析期**展开,
      会把真实退出码掩盖成 0(task-14 / L2-1);
    - 仅 9009(命令未找到)回退 Python, 其余非零退出码原样传播;
    - prefer_native_bin=False 时完全不写 `.bin` 分支: cmd 对"存在但不可运行"的文件
      (如共享目录里被 Windows 复用的 linux ELF)实测 errorlevel=0, 会静默 no-op
      且永不回退 cli_entry.py(task-14 / L2-2)。
    内容保持纯 ASCII + CRLF(cmd.exe 按 OEM 代码页读取批处理)。
    """
    lines = [
        "@echo off",
        "rem Generated by install_cli.py (issue #929 / task-14): force UTF-8 for child processes.",
        "setlocal enabledelayedexpansion",
        "set PYTHONUTF8=1",
        "set PYTHONIOENCODING=utf-8",
        'set "SELF_DIR=%~dp0"',
    ]
    if prefer_native_bin:
        lines.extend([
            'if exist "%SELF_DIR%skill-quality-cli.bin" (',
            '    "%SELF_DIR%skill-quality-cli.bin" %*',
            '    set "RC=!ERRORLEVEL!"',
            '    if "!RC!"=="9009" goto :fallback',
            "    exit /b !RC!",
            ")",
        ])
    lines.extend([
        ":fallback",
        'set "PY_CMD=python"',
        'where py >nul 2>nul && set "PY_CMD=py -3"',
        '%PY_CMD% "%SELF_DIR%skill-quality-cli.d\\cli_entry.py" %*',
        "exit /b %ERRORLEVEL%",
        "",
    ])
    return "\r\n".join(lines)


def write_artifact(target: Path, data: bytes, mode: int | None = None) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.is_dir():
        shutil.rmtree(target)
    target.write_bytes(data)
    if mode is not None:
        try:
            os.chmod(target, mode)
        except OSError:
            pass


def install_artifacts(artifacts: dict[str, bytes], modes: dict[str, int], install_dir: Path, force: bool) -> None:
    """把已校验的产物写入安装目录(--force 时先清理旧产物)。"""
    if force and install_dir.exists():
        for stale in (LAUNCHER_SH, LAUNCHER_CMD, NATIVE_BIN):
            (install_dir / stale).unlink(missing_ok=True)
        shutil.rmtree(install_dir / AUX_DIR, ignore_errors=True)
    for rel, data in artifacts.items():
        write_artifact(install_dir / rel, data, modes.get(rel))


def build_artifacts(mode: str, members: dict[str, bytes], platform_tag: str) -> tuple[dict[str, bytes], dict[str, int]]:
    # `.bin` 分支只给"本机平台原生且平台匹配"的启动器: win32 原生 → 只有 .cmd 认 .bin,
    # 非 win32 原生 → 只有 sh 启动器认 .bin; fallback 模式两个都不认(task-14 / L2-2)。
    native = mode == "native"
    native_on_windows = native and platform_tag.lower().startswith("win")
    native_on_posix = native and not native_on_windows
    artifacts: dict[str, bytes] = {
        CLI_ENTRY: members[CLI_ENTRY],
        LAUNCHER_SH: posix_launcher(prefer_native_bin=native_on_posix).encode("utf-8"),
        LAUNCHER_CMD: windows_launcher(prefer_native_bin=native_on_windows).encode("utf-8"),
    }
    modes: dict[str, int] = {CLI_ENTRY: 0o644, LAUNCHER_SH: 0o755, LAUNCHER_CMD: 0o644}
    if CLI_REPORTING in members:
        artifacts[CLI_REPORTING] = members[CLI_REPORTING]
        modes[CLI_REPORTING] = 0o644
    if mode == "native":
        artifacts[NATIVE_BIN] = members[NATIVE_BIN]
        modes[NATIVE_BIN] = 0o755
    return artifacts, modes


def result_payload(
    mode: str,
    version: str,
    install_dir: Path,
    platform_tag: str,
    launchers: list[Path],
    sha256_verified: bool,
) -> dict:
    return {
        "success": True,
        "mode": mode,
        "version": version,
        "install_dir": str(install_dir),
        "platform": platform_tag,
        "launcher": [str(path) for path in launchers],
        "sha256_verified": sha256_verified,
        "utf8_forced": True,
    }


def emit_failure(message: str, as_json: bool) -> int:
    print(f"错误: {message}", file=sys.stderr)
    if as_json:
        print(json.dumps({"success": False, "error": message}, ensure_ascii=False))
    return 1


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="skill-quality-cli 跨平台本地安装入口(issue #929): 强制 SHA256 校验, "
                    "无本机原生包时降级为纯 Python fallback, 启动器固化 UTF-8。",
    )
    parser.add_argument("--install-dir", default=None,
                        help="安装目录; 默认 $HOME/.local/bin(Windows 为 %%USERPROFILE%%\\.local\\bin), "
                             "可用环境变量 SQC_INSTALL_DIR 覆盖")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--manifest-file", default=None, help="从本地清单 JSON 安装(离线模式)")
    source.add_argument("--manifest-url", default=None,
                        help=f"清单地址; 默认 {DEFAULT_MANIFEST_URL}, 可用 SQC_MANIFEST_URL 覆盖")
    parser.add_argument("--package-dir", default=None,
                        help="离线测试用: download_url 为 web URL 时改为从该目录按 URL basename 取包")
    parser.add_argument("--platform", default=None,
                        help="覆盖平台探测结果(如 linux-x86_64 / linux-arm64 / darwin-arm64 / win32-x86_64)")
    parser.add_argument("--no-python-fallback", action="store_true",
                        help="无本机原生包时直接失败, 不降级为纯 Python fallback")
    parser.add_argument("--force", action="store_true", help="清理旧产物后强制重装")
    parser.add_argument("--dry-run", action="store_true", help="只打印安装计划 JSON, 不写任何文件")
    parser.add_argument("--json", action="store_true", help="stdout 输出结果 JSON")
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    install_dir = Path(args.install_dir).expanduser() if args.install_dir else default_install_dir()
    manifest_url = args.manifest_url or os.environ.get("SQC_MANIFEST_URL") or DEFAULT_MANIFEST_URL
    platform_tag = args.platform or detect_platform_tag()
    launcher_paths = [install_dir / LAUNCHER_SH, install_dir / LAUNCHER_CMD]

    manifest = load_manifest(args.manifest_file, manifest_url)
    version = str(manifest.get("version") or "")
    packages = manifest.get("packages")
    if not isinstance(packages, list) or not packages:
        raise InstallError(f"清单(v{version or 'unknown'})中没有 packages")

    package, mode = select_package(packages, platform_tag, allow_fallback=not args.no_python_fallback)
    if package is None or mode is None:
        if args.no_python_fallback:
            raise InstallError(f"清单(v{version})无 {platform_tag} 安装包, 且已禁用 python-fallback")
        raise InstallError(f"清单(v{version})既无 {platform_tag} 安装包, 也没有可用的 tar.gz 包")

    expected_sha = str(package.get("sha256") or "").strip()
    if not expected_sha:
        # fail-closed: 与 install_cli.sh 一致, 拒绝无校验安装
        raise InstallError(f"清单(v{version})未提供 {platform_tag} 包的 sha256 校验值, 拒绝无校验安装")

    if args.dry_run:
        plan = result_payload(mode, version, install_dir, platform_tag, launcher_paths, sha256_verified=False)
        plan["dry_run"] = True
        plan["package"] = {
            "platform": package.get("platform"),
            "download_url": package.get("download_url"),
            "sha256": expected_sha,
        }
        print(json.dumps(plan, ensure_ascii=False))
        return 0

    tmp_dir = Path(tempfile.mkdtemp(prefix="sqc-install-"))
    try:
        archive = resolve_local_package(package, args.package_dir, tmp_dir)
        actual_sha = sha256_file(archive)
        if actual_sha.lower() != expected_sha.lower():
            raise InstallError(f"SHA256 校验失败(期望 {expected_sha}, 实际 {actual_sha}), 已放弃安装")

        wanted = (CLI_ENTRY, CLI_REPORTING, NATIVE_BIN) if mode == "native" else (CLI_ENTRY, CLI_REPORTING)
        try:
            members = read_tar_members(archive, wanted)
        except tarfile.TarError as exc:
            raise InstallError(f"解压安装包失败(仅支持 tar.gz): {exc}")
        if CLI_ENTRY not in members:
            raise InstallError(f"包内缺少 {CLI_ENTRY}, 无法安装")
        if mode == "native" and NATIVE_BIN not in members:
            raise InstallError(f"包内缺少 {NATIVE_BIN}, 无法完成 native 安装")

        artifacts, modes = build_artifacts(mode, members, platform_tag)
        install_artifacts(artifacts, modes, install_dir, force=args.force)
    finally:
        # 无论成功失败都清理临时文件(校验失败时不留悬空下载物)
        shutil.rmtree(tmp_dir, ignore_errors=True)

    payload = result_payload(mode, version, install_dir, platform_tag, launcher_paths, sha256_verified=True)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"skill-quality-cli v{version} 安装完成(mode={mode}, platform={platform_tag})")
        print(f"安装目录: {install_dir}")
        print(f"启动器: {launcher_paths[0]} | {launcher_paths[1]}")
        if mode == "python-fallback":
            print("说明: 当前平台无原生包, 已安装纯 Python fallback(未安装任何原生 ELF)。")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return run(args)
    except InstallError as exc:
        return emit_failure(str(exc), args.json)
    except Exception as exc:  # 兜底: 任何异常都转成 exit 1, 不向用户抛 traceback
        return emit_failure(f"{type(exc).__name__}: {exc}", args.json)


if __name__ == "__main__":
    sys.exit(main())
