"""离线回归测试：scripts/ensure_cli.sh（下载 → sha256 校验 → 执行 → PATH shim）。

Issue: developer-skill/skillsopr#101 / PR #1012 审查意见（R3：安装器测试缺失）

官方模板 `ensure_cli.sh` 的 sha256 受发布校验器管控，禁止本地修改，因此这里
只驱动未改动的真实脚本：

- 子进程通过 `sitecustomize` 替换 `urllib.request.urlopen`，全程不联网；
- `SKILL_QUALITY_CLI_DIR` 指向 tmp_path，不写入 HOME、不污染真实环境；
- `STUB_META_JSON` / `STUB_PAYLOAD_B64` 控制 latest 接口返回与 bootstrap 载荷。

覆盖路径：幂等短路、缺 sha256、sha256 不匹配、非 OBS 域名跳过、二次运行不重复下载。

运行: python3 -m pytest <SKILL_DIR>/tests/test_ensure_cli.py -q
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
ENSURE_CLI = SKILL_DIR / "scripts" / "ensure_cli.sh"

OBS_BOOTSTRAP_URL = "https://bucket.obs.cn-north-4.myhuaweicloud.com/bootstrap.py"
NON_OBS_BOOTSTRAP_URL = "https://example.invalid/bootstrap.py"
MINIMAL_PATH = "/usr/bin:/bin"

# 在子进程启动时被 site 自动导入：把网络出口换成可记录的本地桩。
SITECUSTOMIZE = '''
import base64
import os
import urllib.request

_LOG = os.environ.get("STUB_CALL_LOG")
_META = os.environ.get("STUB_META_JSON", "{}")
_PAYLOAD = os.environ.get("STUB_PAYLOAD_B64", "")


class _Response:
    def __init__(self, data):
        self._data = data
        self._pos = 0

    def read(self, size=-1, *args, **kwargs):
        if size is None or size < 0:
            size = len(self._data) - self._pos
        chunk = self._data[self._pos : self._pos + size]
        self._pos += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _urlopen(url, *args, **kwargs):
    if _LOG:
        with open(_LOG, "a", encoding="utf-8") as fh:
            fh.write(str(url) + "\\n")
    if "cli/latest" in str(url):
        return _Response(_META.encode("utf-8"))
    return _Response(base64.b64decode(_PAYLOAD))


urllib.request.urlopen = _urlopen
'''

# 被 download() 取回的 bootstrap 载荷：模拟官方安装器把 CLI 装进 CLI_DIR。
INSTALLER_PAYLOAD = b'''import os
import stat

target_dir = os.environ["STUB_INSTALL_DIR"]
os.makedirs(target_dir, exist_ok=True)
target = os.path.join(target_dir, "skill-quality-cli")
with open(target, "w", encoding="utf-8") as fh:
    fh.write("#!/bin/sh\\nexit 0\\n")
os.chmod(target, stat.S_IRWXU)
'''
PAYLOAD_SHA = hashlib.sha256(INSTALLER_PAYLOAD).hexdigest()


def _meta(*, url: str = OBS_BOOTSTRAP_URL, sha: str | None = PAYLOAD_SHA) -> dict:
    meta = {"bootstrap_url": url}
    if sha is not None:
        meta["bootstrap_sha"] = sha
    return meta


def run_ensure(tmp_path: Path, *, meta: dict, seed_cli: bool = False):
    """用隔离环境执行真实 ensure_cli.sh，返回 (proc, cli_dir, calls, bin_dir)。"""
    harness = tmp_path / "harness"
    harness.mkdir(exist_ok=True)
    (harness / "sitecustomize.py").write_text(SITECUSTOMIZE, encoding="utf-8")

    cli_dir = tmp_path / "cli"
    cli_dir.mkdir(exist_ok=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    log = tmp_path / "calls.log"

    if seed_cli:
        cli = cli_dir / "skill-quality-cli"
        cli.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        cli.chmod(0o755)

    env = {
        "PATH": f"{bin_dir}:{MINIMAL_PATH}",
        "HOME": str(tmp_path / "home"),
        "PYTHONPATH": str(harness),
        "SKILL_QUALITY_CLI_DIR": str(cli_dir),
        "SKILL_QUALITY_PORTAL_BASE": "https://portal.invalid",
        "STUB_INSTALL_DIR": str(cli_dir),
        "STUB_CALL_LOG": str(log),
        "STUB_META_JSON": json.dumps(meta),
        "STUB_PAYLOAD_B64": base64.b64encode(INSTALLER_PAYLOAD).decode("ascii"),
    }
    proc = subprocess.run(
        ["bash", str(ENSURE_CLI)],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return proc, cli_dir, calls, bin_dir


def _installed(cli_dir: Path) -> Path:
    return cli_dir / "skill-quality-cli"


def test_idempotent_short_circuit_skips_network(tmp_path: Path) -> None:
    """已安装且可执行时直接短路：不请求 latest、不下载。"""
    proc, cli_dir, calls, _ = run_ensure(
        tmp_path, meta=_meta(url=NON_OBS_BOOTSTRAP_URL, sha="0" * 64), seed_cli=True
    )

    assert proc.returncode == 0, proc.stderr
    assert calls == []
    assert _installed(cli_dir).is_file()


def test_missing_sha_skips_without_download(tmp_path: Path) -> None:
    """latest 未下发 sha256：只请求 latest，不下载、不安装、exit 0。"""
    proc, cli_dir, calls, _ = run_ensure(tmp_path, meta=_meta(sha=None))

    assert proc.returncode == 0, proc.stderr
    assert len(calls) == 1 and "cli/latest" in calls[0]
    assert not _installed(cli_dir).exists()


def test_non_obs_bootstrap_url_is_skipped(tmp_path: Path) -> None:
    """bootstrap_url 非 OBS 域名：只请求 latest，不下载、不执行、exit 0。"""
    proc, cli_dir, calls, _ = run_ensure(
        tmp_path, meta=_meta(url=NON_OBS_BOOTSTRAP_URL)
    )

    assert proc.returncode == 0, proc.stderr
    assert len(calls) == 1 and "cli/latest" in calls[0]
    assert not _installed(cli_dir).exists()


def test_sha256_mismatch_skips_before_execution(tmp_path: Path) -> None:
    """下载内容 sha256 不匹配：下载后拒绝执行，CLI 不落盘、exit 0。"""
    proc, cli_dir, calls, _ = run_ensure(tmp_path, meta=_meta(sha="0" * 64))

    assert proc.returncode == 0, proc.stderr
    assert len(calls) == 2
    assert "cli/latest" in calls[0]
    assert calls[1] == OBS_BOOTSTRAP_URL
    assert not _installed(cli_dir).exists()


def test_successful_bootstrap_then_second_run_does_not_download(
    tmp_path: Path,
) -> None:
    """校验通过后执行载荷安装 CLI；二次运行命中幂等短路，不再下载。"""
    meta = _meta()
    first, cli_dir, first_calls, bin_dir = run_ensure(tmp_path, meta=meta)

    assert first.returncode == 0, first.stderr
    assert first_calls == [
        "https://portal.invalid/rest/developer/servlet/hdskillservice/v1/quality/cli/latest",
        OBS_BOOTSTRAP_URL,
    ]
    assert _installed(cli_dir).is_file()
    shim = bin_dir / "skill-quality-cli"
    assert shim.is_file() and os.access(shim, os.X_OK)
    assert str(_installed(cli_dir)) in shim.read_text(encoding="utf-8")

    second, _, second_calls, _ = run_ensure(tmp_path, meta=meta)

    assert second.returncode == 0, second.stderr
    assert second_calls == first_calls