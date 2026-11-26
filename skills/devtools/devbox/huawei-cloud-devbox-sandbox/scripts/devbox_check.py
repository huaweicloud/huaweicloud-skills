#!/usr/bin/env python3
"""DevBox skill environment checker — CLI-first.

Verifies the DevBox environment in the skill's preferred order:
CLI (default) -> JS SDK (--js) -> Python SDK (--python).

Usage:
    python3 devbox_check.py               # CLI: install + version + auth status
    python3 devbox_check.py --smoke       # CLI end-to-end: create/exec/kill (needs auth+network)
    python3 devbox_check.py --python      # Python SDK: runtime, SDK, API key, Manager
    python3 devbox_check.py --python --smoke   # + create sandbox, run a command, delete it
    python3 devbox_check.py --js          # JS SDK environment

Environment overrides (optional):
    DEVBOX_CLI_INSTALL_URL  install the CLI from another release URL
    DEVBOX_SDK_REPO_URL     install the Python SDK from another mirror (default: GitHub)
    DEVBOX_SDK_BRANCH       branch to install from (default: dev)
    DEVBOX_SDK_REF          pin an exact commit SHA or tag (default: branch tip)
"""
from __future__ import annotations

import argparse
import asyncio
import importlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

MIN_PY = (3, 10)
MIN_NODE = (20, 18, 1)
REPO_URL = os.environ.get(
    "DEVBOX_SDK_REPO_URL", "https://github.com/huaweicloud/devspace-devbox.git"
)
REPO_BRANCH = os.environ.get("DEVBOX_SDK_BRANCH", "dev")
SDK_REF = os.environ.get("DEVBOX_SDK_REF", "").strip()
# Official install-script channels (order = preference; OBS is CN-friendly).
# The install script downloads the prebuilt release artifact (no source build).
CLI_INSTALL_URLS = [
    os.environ.get("DEVBOX_CLI_INSTALL_URL"),
    "https://tools-artifact.developer.huaweicloud.com/sharedata/devbox/install.sh",
    "https://gitcode.com/CloudDeveloperDepartment/devbox/releases/download/latest/install.sh",
    "https://github.com/huaweicloud/devspace-devbox/releases/latest/download/install.sh",
]
CLI_BIN = os.path.expanduser("~/.huawei/bin/devbox")
CLI_VERSION = os.environ.get("DEVBOX_CLI_VERSION", "").strip()   # pin e.g. 0.1.0-release
# base URL of the artifact repository, passed to install.sh as -u (optional)
CLI_ARTIFACT_URL = os.environ.get("DEVBOX_CLI_ARTIFACT_URL", "").strip()
MIN_GO = (1, 26)
SMOKE_TIMEOUT = 300
PIP_TIMEOUT = 180        # seconds per pip invocation
CLONE_TIMEOUT = 60       # seconds per git clone/checkout attempt
DOWNLOAD_TIMEOUT = 600   # seconds per install-script run (downloads a ~5MB artifact)
EXPECTED_SYMBOLS = ("Sandbox", "AsyncSandbox", "DevBox", "DevBoxError", "PtySize")
IMPORT_ERROR = {"message": ""}


def fail(message: str, code: int = 1) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(code)


def ok(message: str) -> None:
    print(f"[OK] {message}")


def check_python_runtime() -> None:
    if sys.version_info < MIN_PY:
        fail(f"Python {MIN_PY[0]}.{MIN_PY[1]}+ required, found {sys.version.split()[0]}")
    ok(f"Python runtime {sys.version.split()[0]}")


def _run_step(step: list[str], timeout: int = CLONE_TIMEOUT, cwd: str | None = None) -> bool:
    """Run one subprocess with a timeout; a timeout counts as failure."""
    try:
        proc = subprocess.run(step, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return proc.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"[WARN] timed out after {timeout}s: {' '.join(step[:4])} …")
        return False


# ---------------------------------------------------------------------------
# CLI path (default)
# ---------------------------------------------------------------------------

def devbox_on_path() -> str | None:
    found = shutil.which("devbox")
    if found:
        return found
    return CLI_BIN if os.path.isfile(CLI_BIN) and os.access(CLI_BIN, os.X_OK) else None


def install_cli() -> None:
    print("[INFO] devbox CLI not installed; installing the prebuilt release artifact...")
    os.makedirs(os.path.dirname(CLI_BIN), exist_ok=True)
    # Preferred path: the official install script downloads the latest prebuilt
    # artifact (tar.gz) for this OS/arch — no Go toolchain involved.
    # Channels and usage follow the official guide:
    #   https://huaweicloud.github.io/devspace-devbox/cli/install
    for url in CLI_INSTALL_URLS:
        if not url:
            continue
        script = os.path.join(tempfile.gettempdir(), "devbox_install.sh")
        try:
            proc = subprocess.run(["curl", "-fsSL", url, "-o", script],
                                  capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT)
        except subprocess.TimeoutExpired:
            print(f"[WARN] download timed out after {DOWNLOAD_TIMEOUT}s: {url}")
            continue
        if proc.returncode != 0 or not os.path.isfile(script):
            print(f"[WARN] download failed: {url}")
            continue
        cmd = ["bash", script, "-s"]
        if CLI_VERSION:
            cmd += ["-v", CLI_VERSION]
        if CLI_ARTIFACT_URL:
            cmd += ["-u", CLI_ARTIFACT_URL]
        if _run_step(cmd, timeout=DOWNLOAD_TIMEOUT):
            ok("installed devbox CLI (prebuilt artifact)")
            os.unlink(script)
            return
        print(f"[WARN] install script failed: {url}")
    # Fallback: build from source (used only while release artifacts are
    # not yet published on any channel, or when all channels are unreachable).
    if build_cli_from_source():
        ok("built devbox CLI from source (dev branch)")
        return
    fail(
        "could not install the devbox CLI from any channel (prebuilt artifacts) "
        "and the source-build fallback failed. Try: "
        "(1) the official guide https://huaweicloud.github.io/devspace-devbox/cli/install ; "
        "(2) pin a version via DEVBOX_CLI_VERSION=<version>; "
        "(3) point DEVBOX_CLI_INSTALL_URL at a reachable mirror of install.sh; "
        "(4) build manually: install Go >= 1.26, then git clone -b dev "
        "https://github.com/huaweicloud/devspace-devbox.git && cd devspace-devbox/cli "
        "&& make build && cp bin/devbox ~/.huawei/bin/"
    )


def build_cli_from_source() -> bool:
    """Build the CLI from the dev branch; requires Go >= 1.26 on PATH."""
    go = shutil.which("go")
    if go is None:
        print("[INFO] Go not found on PATH; cannot build the CLI from source")
        return False
    ver_out = subprocess.run([go, "version"], capture_output=True, text=True, timeout=10).stdout
    m = re.search(r"go(\d+)\.(\d+)", ver_out)
    if not m or tuple(int(p) for p in m.groups()) < MIN_GO:
        print(f"[INFO] Go >= {MIN_GO[0]}.{MIN_GO[1]} required for the CLI build, found: {ver_out.strip()}")
        return False
    workdir = tempfile.mkdtemp(prefix="devbox-cli-")
    try:
        if not clone_repo(os.path.join(workdir, "devspace-devbox")):
            return False
        cli_dir = os.path.join(workdir, "devspace-devbox", "cli")
        if not _run_step(["make", "build"], timeout=600, cwd=cli_dir):
            return False
        built = os.path.join(cli_dir, "bin", "devbox")
        if not os.path.isfile(built):
            built = os.path.join(cli_dir, "devbox")  # non-make fallback output
        if not os.path.isfile(built):
            print("[WARN] build finished but no devbox binary found")
            return False
        shutil.copy2(built, CLI_BIN)
        os.chmod(CLI_BIN, 0o755)
        return True
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def check_cli() -> None:
    devbox = devbox_on_path()
    if devbox is None:
        install_cli()
        devbox = devbox_on_path()
        if devbox is None:
            fail("devbox CLI still not found after install")
    env = dict(os.environ, PATH=f"{os.path.dirname(devbox)}{os.pathsep}{os.environ.get('PATH', '')}")
    version = subprocess.run([devbox, "--version"], capture_output=True, text=True, timeout=15, env=env)
    if version.returncode != 0:
        fail(f"devbox --version failed: {(version.stderr or version.stdout).strip()}")
    ok(f"devbox CLI {version.stdout.strip()}")
    auth = subprocess.run([devbox, "auth", "status"], capture_output=True, text=True, timeout=30, env=env)
    out = (auth.stdout + auth.stderr).strip()
    if auth.returncode == 0 and not re.search(r"not logged in", out, re.I):
        ok(f"CLI auth: {out.splitlines()[0] if out else 'logged in'}")
    elif os.environ.get("HW_DEVBOX_API_KEY", "").strip():
        # auth status only reflects the local key store; HW_DEVBOX_API_KEY alone
        # is a valid credential for every command — --smoke proves it for real
        print("[INFO] CLI key store empty; using HW_DEVBOX_API_KEY from the environment "
              "(run 'devbox auth login --api-key \"$HW_DEVBOX_API_KEY\"' to persist it)")
    else:
        print("[INFO] CLI not logged in and HW_DEVBOX_API_KEY is not set. "
              "Set HW_DEVBOX_API_KEY and run: "
              'devbox auth login --api-key "$HW_DEVBOX_API_KEY" '
              "(interactive browser login also works)")
        raise SystemExit(2)


def cli_smoke() -> None:
    devbox = devbox_on_path()
    env = dict(os.environ, PATH=f"{os.path.dirname(devbox)}{os.pathsep}{os.environ.get('PATH', '')}")

    def run(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
        return subprocess.run([devbox, *args], capture_output=True, text=True, timeout=timeout, env=env)

    tpl = run("tpl", "list", "-f", "json", timeout=60)
    if tpl.returncode != 0:
        fail(f"tpl list failed: {(tpl.stderr or tpl.stdout).strip()[:200]}")
    # CLI -f json emits Go-style tags: templateID/buildID (capital ID);
    # templateId/template_id are listed for robustness across versions
    m = re.search(r'"(?:templateId|templateID|template_id)"\s*:\s*"([^"]+)"', tpl.stdout)
    template = m.group(1) if m else fail("no template found in tpl list output")
    ok(f"template: {template}")

    created = run("sbx", "create", template, "-d", "-t", "300", timeout=SMOKE_TIMEOUT)
    if created.returncode != 0:
        fail(f"sandbox create failed: {(created.stderr or created.stdout).strip()[:200]}")
    sid = created.stdout.strip().splitlines()[-1].strip()
    ok(f"sandbox created: {sid}")
    try:
        ex = run("sbx", "ex", sid, "--", "printf", "devbox-cli-smoke-ok", timeout=SMOKE_TIMEOUT)
        if "devbox-cli-smoke-ok" not in (ex.stdout + ex.stderr):
            fail(f"unexpected exec output: exit={ex.returncode} out={ex.stdout.strip()!r}")
        ok("exec executed with expected output")
    finally:
        killed = run("sbx", "kl", sid, timeout=120)
        if killed.returncode == 0:
            ok(f"sandbox deleted: {sid}")
        else:
            print(f"[WARN] sandbox cleanup failed (id={sid}) — delete it manually later")
    print("CLI SMOKE TEST PASSED")


# ---------------------------------------------------------------------------
# JS path
# ---------------------------------------------------------------------------

async def _js_import_check() -> tuple[bool, str]:
    proc = await asyncio.create_subprocess_exec(
        "node", "-e", "import('devbox-js-sdk').then(m => console.log(m.VERSION))",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    return proc.returncode == 0, (out or err).decode(errors="replace").strip()


def check_js() -> None:
    node = shutil.which("node")
    if node is None:
        fail("node not found in PATH; install Node.js >= 20.18.1")
    try:
        version_out = subprocess.run(
            [node, "--version"], capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except subprocess.TimeoutExpired:
        fail("node --version timed out; check your Node.js installation")
    match = re.search(r"v?(\d+)\.(\d+)\.(\d+)", version_out)
    if not match:
        fail(f"could not parse node version from {version_out!r}")
    parts = tuple(int(p) for p in match.groups())
    if parts < MIN_NODE:
        fail(f"Node.js >= {MIN_NODE[0]}.{MIN_NODE[1]}.{MIN_NODE[2]} required, found {version_out}")
    ok(f"Node.js runtime {version_out}")
    imported, output = asyncio.run(_js_import_check())
    if not imported:
        print(
            "[WARN] devbox-js-sdk is not importable from the current directory; "
            "install it in your project first (published on npm):\n"
            "  cd /path/to/your-project && npm install devbox-js-sdk\n"
            "  source-build fallback (pin a dev-branch commit):\n"
            "    git clone --depth 1 -b dev https://github.com/huaweicloud/devspace-devbox.git\n"
            "    cd devspace-devbox/js-sdk && npm ci && npm run build\n"
            "    npm install /path/to/devspace-devbox/js-sdk   (inside your project)"
        )
        raise SystemExit(2)
    ok(f"devbox-js-sdk {output}")


# ---------------------------------------------------------------------------
# Python path
# ---------------------------------------------------------------------------

def pip_available() -> bool:
    try:
        probe = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        return probe.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def pip_install(*args: str) -> bool:
    cmd = [sys.executable, "-m", "pip", "install", *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=PIP_TIMEOUT)
        return proc.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"[WARN] pip timed out after {PIP_TIMEOUT}s")
        return False


def pip_uninstall(package: str) -> None:
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", package],
            capture_output=True, text=True, timeout=PIP_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        pass


def import_sdk():
    """Import the devbox module; returns None on ImportError.

    Records the underlying error message so a broken install (e.g. missing
    httpx dependency) can be told apart from a missing package.
    """
    try:
        return importlib.import_module("devbox")
    except ImportError as error:
        IMPORT_ERROR["message"] = str(error)
        return None


def sdk_looks_genuine(module) -> bool:
    """Guard against an unrelated package squatting the 'devbox-sdk' name on PyPI."""
    return all(hasattr(module, name) for name in EXPECTED_SYMBOLS)


def _devbox_package_missing() -> bool:
    message = IMPORT_ERROR["message"]
    return not message or re.search(r"No module named 'devbox'", message) is not None


def clone_repo(destination: str) -> bool:
    for _ in range(3):
        if SDK_REF:
            # Full clone + checkout so any commit SHA or tag can be pinned.
            steps = (
                ["git", "clone", REPO_URL, destination],
                ["git", "-C", destination, "checkout", SDK_REF],
            )
        else:
            steps = (["git", "clone", "--depth", "1", "-b", REPO_BRANCH, REPO_URL, destination],)
        if all(_run_step(step) for step in steps):
            return True
        shutil.rmtree(destination, ignore_errors=True)
    return False


def install_python_sdk() -> None:
    print("[INFO] devbox-sdk not installed; installing...")
    if pip_available():
        if pip_install("devbox-sdk"):
            module = import_sdk()
            if module is not None and sdk_looks_genuine(module):
                ok(f"installed devbox-sdk {module.__version__} from PyPI")
                return
            print("[WARN] PyPI 'devbox-sdk' is not the DevBox SDK; removing it and using source")
            pip_uninstall("devbox-sdk")
    else:
        print("[INFO] pip is unavailable; installing from source only")
    workdir = tempfile.mkdtemp(prefix="devspace-devbox-")
    try:
        if not clone_repo(os.path.join(workdir, "devspace-devbox")):
            fail(
                f"could not clone {REPO_URL} (ref: {SDK_REF or REPO_BRANCH}); "
                "check network/proxy and retry, or set DEVBOX_SDK_REPO_URL "
                "to a reachable mirror carrying the dev branch. "
                "You can also install manually: "
                "git clone -b dev <repo> && python3 -m pip install ./devspace-devbox/python-sdk"
            )
        if not pip_install(os.path.join(workdir, "devspace-devbox", "python-sdk")):
            if not pip_available():
                fail(
                    "pip is unavailable for this interpreter "
                    f"({sys.executable}); install pip (e.g. 'apt install python3-pip' "
                    "or use a venv) then re-run, or install the SDK into your "
                    "project environment manually"
                )
            fail("pip install ./python-sdk failed; see pip output above")
        ok("installed devbox-sdk from source (dev branch)")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def check_python_sdk() -> None:
    module = import_sdk()
    if module is None:
        if not _devbox_package_missing():
            fail(
                "found a 'devbox' module but importing it failed: "
                f"{IMPORT_ERROR['message']} — typically a missing dependency or "
                f"the wrong interpreter ({sys.executable}); install the SDK for "
                "this interpreter: python3 -m pip install ./python-sdk"
            )
        install_python_sdk()
        module = import_sdk()
        if module is None:
            fail(f"devbox import failed after install: {IMPORT_ERROR['message'] or 'unknown error'}")
    if not sdk_looks_genuine(module):
        fail("installed 'devbox' module does not look like the DevBox SDK (missing Sandbox/DevBox)")
    ok(f"devbox-sdk {module.__version__} (import devbox)")


def check_api_key() -> None:
    for var in ("DEVBOX_API_KEY", "E2B_API_KEY"):
        value = os.environ.get(var, "").strip()
        if value:
            ok(f"API key present ({var})")
            return
    fail("DEVBOX_API_KEY (or E2B_API_KEY) is not set; export it before running the SDK")


def check_manager() -> None:
    from devbox import DevBox, DevBoxError

    try:
        with DevBox() as client:
            templates = client.templates.list()
    except DevBoxError as error:
        if error.status_code in (401, 403):
            hint = "API key rejected; re-issue it and update DEVBOX_API_KEY"
        else:
            hint = "check network/DNS to the Manager and DEVBOX_API_URL"
        fail(
            "Manager request failed: "
            f"{error.code} {error.status_code} {error.message} "
            f"(request_id={error.request_id}); {hint}"
        )
    except Exception as error:
        fail(f"Manager request failed unexpectedly: {error}")
    names = ", ".join(f"{t.name}({t.template_id})" for t in templates) or "<empty>"
    ok(f"Manager reachable; templates: {names}")


def run_smoke(keep: bool) -> None:
    from devbox import DevBoxError, Sandbox

    try:
        sandbox = Sandbox.create("default", timeout=SMOKE_TIMEOUT)
    except DevBoxError as error:
        fail(f"sandbox create failed: {error.code} {error.status_code} {error.message}")
    print(f"[OK] sandbox created: {sandbox.sandbox_id}")
    try:
        result = sandbox.commands.run("printf 'devbox-smoke-ok'")
        if result.stdout != "devbox-smoke-ok" or result.exit_code != 0:
            fail(f"unexpected command result: exit={result.exit_code} out={result.stdout!r}")
        ok(f"command executed: {result.stdout!r}")
        sandbox.files.write("/tmp/devbox_smoke.txt", "smoke")
        if sandbox.files.read("/tmp/devbox_smoke.txt") != "smoke":
            fail("file round-trip mismatch")
        ok("file write/read round-trip")
    finally:
        if keep:
            print(f"[INFO] keeping sandbox {sandbox.sandbox_id} (--keep); kill it later yourself")
            sandbox.close()
        else:
            try:
                sandbox.kill()
                ok(f"sandbox deleted: {sandbox.sandbox_id}")
            except DevBoxError as error:
                print(f"[WARN] sandbox cleanup failed: {error.message} "
                      f"(id={sandbox.sandbox_id}) — delete it manually later")
    print("SMOKE TEST PASSED")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true",
                        help="end-to-end test (CLI create/exec/kill; with --python: SDK create/run/delete)")
    parser.add_argument("--keep", action="store_true",
                        help="keep the smoke sandbox (skip kill; Python smoke only)")
    parser.add_argument("--js", action="store_true", help="check the JavaScript SDK environment")
    parser.add_argument("--python", action="store_true", help="check the Python SDK environment")
    args = parser.parse_args()

    if args.js and args.python:
        fail("--js and --python are mutually exclusive")
    if args.js:
        if args.smoke:
            print("[WARN] --smoke applies to the Python path only; ignoring it for --js")
        check_js()
        return
    if args.python:
        check_python_runtime()
        check_python_sdk()
        check_api_key()
        check_manager()
        if args.smoke:
            run_smoke(keep=args.keep)
        print("ENVIRONMENT CHECK PASSED")
        return

    check_cli()
    if args.smoke:
        cli_smoke()
    print("ENVIRONMENT CHECK PASSED")


if __name__ == "__main__":
    main()
