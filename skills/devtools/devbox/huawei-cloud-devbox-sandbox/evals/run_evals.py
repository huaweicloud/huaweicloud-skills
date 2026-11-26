#!/usr/bin/env python3
"""Offline end-to-end eval for the huawei-cloud-devbox-sandbox skill.

Boots an in-process mock of the DevBox Manager (REST) and Gateway (Connect
protocol), then runs every skill example plus the checker smoke test against
the REAL SDK over that mock. Requires the devbox SDK to be importable
(pip install devbox-sdk from PyPI, or --sdk-path / PYTHONPATH for a pinned
source checkout of the devspace-devbox dev branch).

Usage:
    python3 evals/run_evals.py [--sdk-path <dir>] [--js-sdk-path <pkg>] [--skip smoke]

Exit code 0 = all cases passed.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parent

sys.path.insert(0, str(HERE))
import mock_devbox  # noqa: E402


def build_cases(cli_bin: str | None = None) -> list[tuple[str, list[str], list[str]]]:
    cases = []
    if cli_bin:
        cases.append(("devbox_check --smoke (CLI)",
                      [sys.executable, str(SKILL / "scripts" / "devbox_check.py"),
                       "--smoke", "--cli-bin", cli_bin],
                      ["CLI SMOKE TEST PASSED"]))
    cases += [
        ("envd_demo.py", [sys.executable, str(SKILL / "examples" / "python" / "envd_demo.py")],
         ["metrics: cpu=", "envs: PATH=", "envd version: 'v0.1.0-mock'"]),
        ("basic.py", [sys.executable, str(SKILL / "examples" / "python" / "basic.py")],
         ["sandbox created:", "hello from DevBox", "hello from the SDK"]),
        ("async_basic.py", [sys.executable, str(SKILL / "examples" / "python" / "async_basic.py")],
         ["sandbox created:", "hello from DevBox", "hello from the async SDK"]),
        ("commands_demo.py", [sys.executable, str(SKILL / "examples" / "python" / "commands_demo.py")],
         ["foreground:", "line-1", "background+stdin:", "hello-stdin",
          "terminated: exit=137", "reconnected:", "reconnected:proof", "process: pid="]),
        ("files_demo.py", [sys.executable, str(SKILL / "examples" / "python" / "files_demo.py")],
         ["write/read round-trip ok", "stat: name=message.txt",
          "upload/download round-trip ok", "watch: ", "done.txt", "cleanup ok"]),
        ("lifecycle_demo.py", [sys.executable, str(SKILL / "examples" / "python" / "lifecycle_demo.py")],
         ["created:", "set_timeout(600)", "refresh(900)", "paused:",
          "resumed:", "file survived:", "running sandboxes:", "killed:"]),
        ("git_demo.py", [sys.executable, str(SKILL / "examples" / "python" / "git_demo.py")],
         ["clone: exit=0", "status: exit=0", "push skipped"]),
    ]
    return cases


def run_js_cases(env: dict, js_sdk_path: str) -> tuple[int, int]:
    """Run the JS examples against the in-process mock.

    The SDKs allow plain http only for localhost, so the JS process shares
    this host's 127.0.0.1 mock directly (no container needed).
    """
    import shutil
    import tempfile

    workdir = tempfile.mkdtemp(prefix="devbox-js-")
    node = shutil.which("node")
    npm = shutil.which("npm")
    if node is None or npm is None:
        print("[WARN] node/npm not found; skipping JS cases")
        return 0, 0
    try:
        subprocess.run([npm, "init", "-y"], cwd=workdir, capture_output=True, timeout=60)
        pkg = pathlib.Path(workdir) / "package.json"
        data = json.loads(pkg.read_text())
        data["type"] = "module"
        pkg.write_text(json.dumps(data))
        proc = subprocess.run([npm, "install", js_sdk_path, "--no-save"],
                              cwd=workdir, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            print(f"[WARN] npm install of the JS SDK failed: {proc.stderr[-200:]}")
            return 0, 1
        for mjs in (SKILL / "examples" / "js").glob("*.mjs"):
            shutil.copy2(mjs, workdir)
        expects = {
            "basic.mjs": ["sandbox created:", "hello from DevBox", "hello from the SDK"],
            "envd_demo.mjs": ["metrics:", "envs:", "envd version:"],
            "commands_demo.mjs": ["foreground:", "line-1", "background+stdin:", "hello-stdin",
                                  "terminated: exit=137", "reconnected:proof"],
            "files_demo.mjs": ["write/read round-trip ok", "upload/download round-trip ok",
                               "watch: ", "done.txt", "cleanup ok"],
            "lifecycle_demo.mjs": ["created:", "setTimeout(600)", "refresh(900)", "paused:",
                                   "resumed:", "file survived:", "killed:"],
            "git_demo.mjs": ["clone: exit=0", "status: exit=0"],
        }
        passed = failed = 0
        for name, want in expects.items():
            try:
                proc = subprocess.run([node, str(pathlib.Path(workdir) / name)],
                                      capture_output=True, text=True, env=env, timeout=120)
            except subprocess.TimeoutExpired:
                print(f"[FAIL] {name}: TIMEOUT")
                failed += 1
                continue
            out = proc.stdout + proc.stderr
            missing = [w for w in want if w not in out]
            if proc.returncode == 0 and not missing:
                print(f"[PASS] {name}")
                passed += 1
            else:
                print(f"[FAIL] {name}: rc={proc.returncode} missing={missing}")
                for line in out.splitlines()[:12]:
                    print(f"  {line}")
                failed += 1
        return passed, failed
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli-bin", default=None,
                        help="path to a devbox CLI binary; when set, also runs the CLI smoke case")
    parser.add_argument("--js-sdk-path", default=None,
                        help="built js-sdk directory (with dist/); when set, runs the JS examples too")
    parser.add_argument("--sdk-path", default=None,
                        help="colon-separated directories added to PYTHONPATH before the devbox package "
                             "(e.g. SDK source and its dependencies)")
    parser.add_argument("--skip", default="", help="comma-separated case names to skip")
    args = parser.parse_args()

    if args.sdk_path:
        for entry in args.sdk_path.split(os.pathsep):
            if entry and os.path.isdir(entry):
                existing = os.environ.get("PYTHONPATH", "")
                os.environ["PYTHONPATH"] = f"{entry}{os.pathsep}{existing}" if existing else entry

    mgr = mock_devbox.ThreadingHTTPServer(("127.0.0.1", mock_devbox.MGR_PORT),
                                          mock_devbox.ManagerHandler)
    gw = mock_devbox.ThreadingHTTPServer(("127.0.0.1", mock_devbox.GW_PORT),
                                         mock_devbox.GatewayHandler)
    threading.Thread(target=mgr.serve_forever, daemon=True).start()
    threading.Thread(target=gw.serve_forever, daemon=True).start()
    print(f"mock up: manager=127.0.0.1:{mock_devbox.MGR_PORT} gateway=127.0.0.1:{mock_devbox.GW_PORT}",
          flush=True)

    env = dict(os.environ)
    env.update({
        "DEVBOX_API_URL": f"http://127.0.0.1:{mock_devbox.MGR_PORT}",
        "DEVBOX_API_KEY": mock_devbox.API_KEY,
    })

    skip = {s.strip() for s in args.skip.split(",") if s.strip()}
    passed = failed = 0
    for name, cmd, expects in build_cases(cli_bin=args.cli_bin):
        if name in skip:
            print(f"[SKIP] {name}")
            continue
        t0 = time.time()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=90)
        except subprocess.TimeoutExpired:
            print(f"[FAIL] {name}: TIMEOUT >90s")
            failed += 1
            continue
        out = proc.stdout + proc.stderr
        missing = [e for e in expects if e not in out]
        if proc.returncode == 0 and not missing:
            print(f"[PASS] {name} ({time.time() - t0:.1f}s)")
            passed += 1
        else:
            print(f"[FAIL] {name}: rc={proc.returncode} missing={missing}")
            for line in out.splitlines()[:25]:
                print(f"  {line}")
            failed += 1

    if args.js_sdk_path:
        js_passed, js_failed = run_js_cases(env, args.js_sdk_path)
        passed += js_passed
        failed += js_failed

    print(f"\nE2E RESULT: {passed} passed, {failed} failed, {len(skip)} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
