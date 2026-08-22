#!/usr/bin/env python3
"""Poll DevKit installation progress until DONE and all services active.

Wraps the `status` subcommand of create_ecs_and_setup_devkit.py in a single
loop so that tool-level repeated calls (which may trigger doom-loop guards)
are avoided. The password is only ever held inside the short-lived Python
subprocess that runs `status` (KMS decrypt -> paramiko -> close); this script
never touches the password.

Exit codes:
  0  install_process=DONE and all expected services are active
  1  timeout (not DONE within max_polls) or fatal error

Usage:
  python3 poll_devkit_status.py \
    --region cn-south-1 \
    --eip <eip> \
    --kms-key-id <key_id> \
    --kms-cipher-text-file <cipher_file> \
    [--interval 30] [--max-polls 30] \
    [--status-script /path/to/create_ecs_and_setup_devkit.py]
"""
import argparse
import json
import os
import subprocess
import sys
import time

EXPECTED_SERVICES = ("devkit_nginx", "gunicorn_framework", "gunicorn_plugin")
EXPECTED_PLUGINS = (
    "porting", "affinity", "devtools", "debugger",
    "sys_perf", "java_perf", "sys_diagnosis",
)


def run_status(script, args):
    cmd = [
        sys.executable, script, "status",
        "--region", args.region,
        "--eip", args.eip,
        "--kms-key-id", args.kms_key_id,
        "--kms-cipher-text-file", args.kms_cipher_text_file,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return proc.stdout, proc.stderr, proc.returncode


def parse_status(stdout):
    # The status subcommand may print non-JSON lines before the JSON block.
    i = stdout.find("{")
    if i < 0:
        return None
    try:
        return json.loads(stdout[i:])
    except json.JSONDecodeError:
        return None


def summarize(result, poll_idx, elapsed):
    ip = result.get("install_process", "UNKNOWN")
    stage = result.get("current_stage", "")
    services = result.get("services", {})
    plugins = result.get("plugins", {})
    ports = result.get("ports", "none")
    svc_summary = " ".join(f"{k}={services.get(k, '?')}" for k in EXPECTED_SERVICES)
    installed = sum(1 for p in EXPECTED_PLUGINS if plugins.get(p) == "installed")
    head = f"[poll #{poll_idx} {elapsed}s] install_process={ip}"
    if stage:
        head += f" stage={stage}"
    print(head)
    print(f"  services: {svc_summary}")
    print(f"  plugins: {installed}/{len(EXPECTED_PLUGINS)} installed")
    print(f"  ports: {ports}")
    tail = (result.get("last_log_lines") or "").strip().splitlines()
    if tail:
        print(f"  last_log: {tail[-1][:120]}")


def is_done(result):
    if result.get("install_process") != "DONE":
        return False
    services = result.get("services", {})
    return all(services.get(s) == "active" for s in EXPECTED_SERVICES)


def main():
    ap = argparse.ArgumentParser(description="Poll DevKit install status until DONE")
    ap.add_argument("--region", required=True)
    ap.add_argument("--eip", required=True)
    ap.add_argument("--kms-key-id", required=True)
    ap.add_argument("--kms-cipher-text-file", required=True)
    ap.add_argument("--interval", type=int, default=30, help="seconds between polls")
    ap.add_argument("--max-polls", type=int, default=30, help="max poll count")
    ap.add_argument(
        "--log-file",
        default=None,
        help="write output to this file instead of stdout (cross-platform background logging)",
    )
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument(
        "--status-script",
        default=os.path.join(here, "create_ecs_and_setup_devkit.py"),
        help="path to create_ecs_and_setup_devkit.py",
    )
    args = ap.parse_args()

    if not os.path.isfile(args.status_script):
        print(f"ERROR: status script not found: {args.status_script}", file=sys.stderr)
        sys.exit(1)

    if args.log_file:
        log_fh = open(args.log_file, "w", encoding="utf-8")
        sys.stdout = log_fh
        sys.stderr = log_fh

    start = time.time()
    for i in range(1, args.max_polls + 1):
        try:
            stdout, stderr, rc = run_status(args.status_script, args)
        except subprocess.TimeoutExpired:
            print(f"[poll #{i}] status command timed out", file=sys.stderr)
            time.sleep(args.interval)
            continue

        if rc != 0:
            print(f"[poll #{i}] status command failed (rc={rc})", file=sys.stderr)
            if stderr:
                print(stderr.strip(), file=sys.stderr)
            time.sleep(args.interval)
            continue

        result = parse_status(stdout)
        if result is None:
            print(f"[poll #{i}] could not parse status JSON", file=sys.stderr)
            time.sleep(args.interval)
            continue

        summarize(result, i, int(time.time() - start))

        if is_done(result):
            installed = sum(
                1 for p in EXPECTED_PLUGINS
                if result.get("plugins", {}).get(p) == "installed"
            )
            print(
                f"\nDONE: install_process=DONE, all services active, "
                f"{installed}/{len(EXPECTED_PLUGINS)} plugins installed."
            )
            sys.exit(0)

        time.sleep(args.interval)

    print(f"\nTIMEOUT: not DONE after {args.max_polls} polls.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()