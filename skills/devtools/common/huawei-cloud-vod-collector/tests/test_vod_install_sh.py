"""离线回归测试：scripts/vod_install.sh（AtomGit-GO 校验 → 安装 → 完整性检查）。

Issue: developer-skill/huaweicloud-skills#1128（PR #1012 专业测试 TC-F-03 不通过）
上游仓库 build/ 下有预编译包但没有 .sha256 校验文件，旧脚本 fail-closed 直接 exit 1，
导致文档化默认安装路径整体不可用。本测试覆盖修复后的四种校验来源：

- 本 skill 维护的已知版本清单（vod_install_checksums.txt）
- 上游随包 <archive>.sha256
- 显式 --sha256 <file>
- 均无 → 源码构建兜底（不再直接退出）

另外覆盖：校验不符 fail-closed、已安装短路。全程离线，不克隆上游。

运行: python3 -m pytest <SKILL_DIR>/tests/test_vod_install_sh.py -q
"""

from __future__ import annotations

import hashlib
import io
import os
import shutil
import tarfile
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
INSTALL_SH = SKILL_DIR / "scripts" / "vod_install.sh"


def _fake_go(path: Path) -> None:
    path.write_text(
        "#!/usr/bin/env bash\n"
        "out=\"\"\n"
        "while [ $# -gt 0 ]; do\n"
        "  if [ \"$1\" = \"-o\" ]; then out=\"$2\"; shift 2; continue; fi\n"
        "  shift\n"
        "done\n"
        "[ -n \"$out\" ] || exit 9\n"
        "printf '#!/usr/bin/env bash\\necho stub\\n' > \"$out\"\n"
        "chmod +x \"$out\"\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _make_archive(repo_dir: Path, name: str) -> Path:
    build = repo_dir / "build"
    build.mkdir(parents=True, exist_ok=True)
    archive = build / name
    # 还原上游真实布局：arm64 包带 atomcode-server，x86_64 包带 atomcode-login-server
    if "x86_64" in name:
        entries = ("atomcode-login", "atomcode-login-server")
    else:
        entries = ("atomcode-login", "atomcode-server")
    with tarfile.open(archive, "w:gz") as tar:
        for entry in entries:
            data = b"#!/usr/bin/env bash\necho stub\n"
            info = tarfile.TarInfo(entry)
            info.size = len(data)
            info.mode = 0o755
            tar.addfile(info, io.BytesIO(data))
    return archive


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture()
def env(tmp_path: Path):
    # 独立 script 目录：清单可自造，不污染仓库
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    install = scripts / "vod_install.sh"
    shutil.copy2(INSTALL_SH, install)
    install.chmod(0o755)

    home = tmp_path / "home"
    home.mkdir()
    bindir = home / ".local" / "bin"
    bindir.mkdir(parents=True)

    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    _fake_go(fakebin / "go")

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.go").write_text("package main\n", encoding="utf-8")

    path_env = f"{fakebin}:/usr/bin:/bin"
    base_env = {
        "HOME": str(home),
        "PATH": path_env,
        "LANG": "C",
        "LC_ALL": "C",
    }
    return {
        "scripts": scripts,
        "install": install,
        "home": home,
        "bindir": bindir,
        "repo": repo,
        "env": base_env,
        "tmp": tmp_path,
    }


def _run(case, *args):
    import subprocess

    return subprocess.run(
        ["bash", str(case["install"]), *args],
        env=case["env"],
        text=True,
        capture_output=True,
        timeout=60,
    )


def _installed(bindir: Path) -> bool:
    return all((bindir / n).is_file() for n in ("atomcode-login", "atomcode-server", "atomcode-login-server"))


def test_manifest_hit_installs_archive(env):
    archive = _make_archive(env["repo"], "atomcode-login_linux_arm_64.tar.gz")
    (env["scripts"] / "vod_install_checksums.txt").write_text(
        f"{_sha256(archive)}  {archive.name}\n", encoding="utf-8"
    )

    # 机器若是 x86_64，改为 x86_64 包名，避免平台不匹配走源码构建
    if os.uname().machine in ("x86_64", "amd64"):
        archive.unlink()
        archive = _make_archive(env["repo"], "atomcode-login_linux_x86_64.tar.gz")
        (env["scripts"] / "vod_install_checksums.txt").write_text(
            f"{_sha256(archive)}  {archive.name}\n", encoding="utf-8"
        )

    result = _run(env, "--repo-dir", str(env["repo"]))
    assert result.returncode == 0, result.stderr
    assert "Checksum verified." in result.stdout
    assert "Extracting" in result.stdout
    assert _installed(env["bindir"])


def test_sidecar_sha256_installs_archive(env):
    archive = _make_archive(env["repo"], "atomcode-login_linux_arm_64.tar.gz")
    if os.uname().machine in ("x86_64", "amd64"):
        archive.unlink()
        archive = _make_archive(env["repo"], "atomcode-login_linux_x86_64.tar.gz")
    Path(str(archive) + ".sha256").write_text(
        f"{_sha256(archive)}  {archive.name}\n", encoding="utf-8"
    )

    result = _run(env, "--repo-dir", str(env["repo"]))
    assert result.returncode == 0, result.stderr
    assert "Checksum verified." in result.stdout
    assert _installed(env["bindir"])


def test_explicit_sha256_file_installs_archive(env):
    archive = _make_archive(env["repo"], "atomcode-login_linux_arm_64.tar.gz")
    if os.uname().machine in ("x86_64", "amd64"):
        archive.unlink()
        archive = _make_archive(env["repo"], "atomcode-login_linux_x86_64.tar.gz")
    checksum = env["tmp"] / "trusted.sha256"
    checksum.write_text(f"{_sha256(archive)}  {archive.name}\n", encoding="utf-8")

    result = _run(env, "--repo-dir", str(env["repo"]), "--sha256", str(checksum))
    assert result.returncode == 0, result.stderr
    assert "explicit:" in result.stdout
    assert _installed(env["bindir"])


def test_missing_checksum_falls_back_to_source_build(env):
    _make_archive(env["repo"], "atomcode-login_linux_arm_64.tar.gz")
    if os.uname().machine in ("x86_64", "amd64"):
        (env["repo"] / "build" / "atomcode-login_linux_arm_64.tar.gz").unlink()
        _make_archive(env["repo"], "atomcode-login_linux_x86_64.tar.gz")
    # 无清单、无 .sha256、无 --sha256
    result = _run(env, "--repo-dir", str(env["repo"]))
    assert result.returncode == 0, result.stderr
    assert "no checksum available" in result.stderr
    assert "Building from source" in result.stdout
    assert _installed(env["bindir"])


def test_explicit_checksum_mismatch_is_fail_closed(env):
    archive = _make_archive(env["repo"], "atomcode-login_linux_arm_64.tar.gz")
    if os.uname().machine in ("x86_64", "amd64"):
        archive.unlink()
        archive = _make_archive(env["repo"], "atomcode-login_linux_x86_64.tar.gz")
    checksum = env["tmp"] / "bad.sha256"
    checksum.write_text(f"{'0' * 64}  {archive.name}\n", encoding="utf-8")

    result = _run(env, "--repo-dir", str(env["repo"]), "--sha256", str(checksum))
    assert result.returncode == 1
    assert "Checksum verification failed" in result.stderr
    assert not _installed(env["bindir"])


def test_manifest_mismatch_falls_back_to_source_build(env):
    _make_archive(env["repo"], "atomcode-login_linux_arm_64.tar.gz")
    if os.uname().machine in ("x86_64", "amd64"):
        (env["repo"] / "build" / "atomcode-login_linux_arm_64.tar.gz").unlink()
        _make_archive(env["repo"], "atomcode-login_linux_x86_64.tar.gz")
    # 清单里放一个不匹配的哈希 → 拒绝压缩包并回退源码构建
    (env["scripts"] / "vod_install_checksums.txt").write_text(
        f"{'0' * 64}  atomcode-login_linux_arm_64.tar.gz\n"
        f"{'0' * 64}  atomcode-login_linux_x86_64.tar.gz\n",
        encoding="utf-8",
    )

    result = _run(env, "--repo-dir", str(env["repo"]))
    assert result.returncode == 0, result.stderr
    assert "does not match the known-version manifest" in result.stderr
    assert "Building from source" in result.stdout
    assert _installed(env["bindir"])


def test_installed_short_circuit(env):
    for name in ("atomcode-login", "atomcode-server", "atomcode-login-server"):
        target = env["bindir"] / name
        target.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        target.chmod(0o755)

    result = _run(env)
    assert result.returncode == 0
    assert "INSTALLED" in result.stdout