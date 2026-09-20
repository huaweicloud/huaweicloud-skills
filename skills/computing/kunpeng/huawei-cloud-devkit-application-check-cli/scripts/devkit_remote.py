#!/usr/bin/env python3
"""
DevKit Remote Execution Script (Python/paramiko)

Layer 1: Agent → DevKit ECS server (paramiko). Layer 2: DevKit server → targets (ssh/sshpass).
See references/rules.md and references/devkit-operations-guide.md for full architecture details.

Execution mode: manual (local script, requires paramiko). No hcloud CLI/SDK/API equivalent.
devkit_remote.py internally calls hcloud CLI for EIP resolution, but the script itself
is a custom SSH/SFTP wrapper that cannot be mapped to a single cloud API call.

🔴 paramiko MUST NEVER connect to nodes.conf target servers (Layer 2 only).
🔴 DEVKIT_ECS_PASSWORD resolved value MUST NEVER appear in plaintext (auto-redacted).
"""
import json
import os
import re
import sys
import time
import subprocess
import argparse
import shlex
import tarfile
import io

try:
    import paramiko
except ImportError:
    print("[ERROR] paramiko is required. Install: pip install paramiko", file=sys.stderr)
    sys.exit(1)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INSTALL_SCRIPT = os.path.join(SCRIPT_DIR, "install_devkit.sh")
SCAN_SCRIPT = os.path.join(SCRIPT_DIR, "scan_devkit.sh")
ENCRYPT_VERIFY_SCRIPT = os.path.join(SCRIPT_DIR, "encrypt-nodes-verify.sh")

DEVKIT_SERVER_PREFIX = "devkit-ecs-"
DEVKIT_REMOTE_HOME = os.environ.get("DEVKIT_HOME", "/home")

_REDACT_SECRET = ""


# ---
# 1. Logging & Secret Redaction
# ---

def set_redact_secret(value):
    global _REDACT_SECRET
    _REDACT_SECRET = value or ""


def _redact(msg):
    if _REDACT_SECRET and _REDACT_SECRET in str(msg):
        return str(msg).replace(_REDACT_SECRET, "***")
    return msg


def log_info(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[INFO]  {ts} {_redact(msg)}")


def log_error(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[ERROR] {ts} {_redact(msg)}", file=sys.stderr)


def log_step(msg):
    print()
    print("=" * 60)
    print(f"  {_redact(msg)}")
    print("=" * 60)


# ---
# 2. Environment Variable & hcloud Resolution
# ---

def resolve_env_var(name):
    for level in ("User", "Machine"):
        try:
            result = subprocess.run(
                [
                    "powershell.exe", "-NoProfile", "-Command",
                    f"[System.Environment]::GetEnvironmentVariable('{name}', '{level}')"
                ],
                capture_output=True, text=True, timeout=10
            )
            v = result.stdout.strip()
            if v:
                return v
        except Exception:
            continue
    return ""


def require_var(name, val):
    if not val:
        log_error(f"Required variable {name} is not set at User or Machine level.")
        log_error("Credentials can ONLY come from environment variables (NOT from command line, ECS adminPass, or auto-generation).")
        log_error("Detection order: User level -> Machine level (NOT Process level).")
        log_error("Please add it via PowerShell:")
        log_error(f'  [System.Environment]::SetEnvironmentVariable("{name}", "<value>", "User")')
        sys.exit(1)


def hcloud_json(args_list):
    result = subprocess.run(
        args_list,
        capture_output=True, timeout=30
    )
    raw = result.stdout.decode("utf-8", errors="replace")
    start = raw.find("{")
    if start == -1:
        return None
    try:
        return json.loads(raw[start:])
    except json.JSONDecodeError:
        return None


def resolve_eip(region):
    log_info(f"Querying hcloud for devkit ECS in region {region} ...")

    data = hcloud_json(["hcloud", "ECS", "ListServersDetails", f"--cli-region={region}", "--limit=500"])
    if not data:
        log_error("Failed to query ECS list from hcloud.")
        sys.exit(1)

    servers = data.get("servers", [])
    devkit_servers = [
        s for s in servers
        if s.get("name", "").startswith(DEVKIT_SERVER_PREFIX) and s.get("status") == "ACTIVE"
    ]

    if not devkit_servers:
        log_error(f"No active ECS found with name prefix '{DEVKIT_SERVER_PREFIX}' in region {region}.")
        log_error("Create a devkit server first (see SKILL.md Step 5).")
        sys.exit(1)

    log_step(f"Found {len(devkit_servers)} existing DevKit ECS in region {region}")
    server_infos = [
        (s.get("id", ""), s.get("name", ""), s.get("flavor", {}).get("name", ""), extract_eip_from_server(s))
        for s in devkit_servers
    ]
    for i, (sid, sname, flavor, eip_tmp) in enumerate(server_infos, 1):
        log_info(f"  {i}. {sname} (ID: {sid}, Flavor: {flavor}, EIP: {eip_tmp or 'N/A'})")
    log_info(f"  0. Create a new ECS (skip reuse)")
    while True:
        try:
            raw = input(f"Select a server to reuse [0-{len(devkit_servers)}]: ").strip()
        except EOFError:
            raw = "1"
        if raw.isdigit() and 0 <= int(raw) <= len(devkit_servers):
            idx = int(raw)
            if idx == 0:
                log_error("User chose to create a new ECS. Aborting reuse.")
                sys.exit(2)
            server = devkit_servers[idx - 1]
            break
        log_error(f"Invalid choice '{raw}'. Please enter a number between 0 and {len(devkit_servers)}.")

    server_id = server.get("id", "")
    server_name = server.get("name", "")
    log_info(f"Selected devkit ECS: {server_name} (ID: {server_id})")

    eip = extract_eip_from_server(server) or get_server_eip(region, server_id)
    if not eip:
        log_error(f"Could not find floating IP for server {server_name}.")
        sys.exit(1)

    log_info(f"Resolved EIP: {eip}")
    return eip, server_id


def get_server_eip(region, server_id):
    data = hcloud_json(["hcloud", "ECS", "ShowServer", f"--cli-region={region}", f"--server_id={server_id}"])
    if not data:
        return ""
    server = data.get("server", {})
    return extract_eip_from_server(server)


def extract_eip_from_server(server):
    """Extract floating IP from a server object in ListServersDetails response.

    This avoids N+1 ShowServer calls by using the addresses data already
    present in the list response.
    """
    addresses = server.get("addresses", {})
    return next(
        (addr.get("addr", "")
         for addr_list in addresses.values()
         for addr in addr_list
         if addr.get("OS-EXT-IPS:type") == "floating"),
        ""
    )


# ---
# 3. SSH/SFTP Utilities (Layer 1: paramiko → DevKit server only)
# ---

def get_ssh_client(host, user, password, retries=3, delay=10):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    last_err = None
    for attempt in range(1, retries + 1):
        if attempt > 1:
            new_user = resolve_env_var("DEVKIT_ECS_USER")
            new_pw = resolve_env_var("DEVKIT_ECS_PASSWORD")
            if new_user:
                user = new_user
            if new_pw:
                password = new_pw
                set_redact_secret(password)
        try:
            client.connect(host, port=22, username=user, password=password, timeout=15)
            return client, user, password
        except paramiko.ssh_exception.AuthenticationException as e:
            last_err = e
            log_info(f"SSH auth attempt {attempt}/{retries} failed: Authentication failed")
            if attempt == 1:
                log_info("Re-detecting DEVKIT_ECS_USER and DEVKIT_ECS_PASSWORD from User/Machine levels ...")
            if attempt < retries:
                time.sleep(delay)
        except Exception as e:
            last_err = e
            log_info(f"SSH connect attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(delay)
    log_error(f"SSH authentication failed after {retries} attempts.")
    log_error("Credentials can ONLY come from environment variables (User -> Machine levels, NOT Process).")
    log_error("NEVER use ECS adminPass or auto-generate/reset password.")
    log_error("")
    log_error("If env vars not set, add them via PowerShell:")
    log_error('  [System.Environment]::SetEnvironmentVariable("DEVKIT_ECS_USER", "root", "User")')
    log_error('  [System.Environment]::SetEnvironmentVariable("DEVKIT_ECS_PASSWORD", "<your_password>", "User")')
    log_error("")
    log_error("If env vars already set but wrong, update them:")
    log_error('  [System.Environment]::SetEnvironmentVariable("DEVKIT_ECS_PASSWORD", "<correct_password>", "User")')
    sys.exit(1)


def ssh_exec(client, cmd, timeout=300, login_shell=True):
    """Execute command via SSH.

    login_shell=True wraps cmd in 'bash -l -c' to ensure /etc/profile,
    ~/.bash_profile, ~/.bashrc are loaded — fixing PATH missing in
    paramiko's non-interactive non-login shell.
    """
    if login_shell:
        wrapped = f"bash -l -c {shlex.quote(cmd)}"
    else:
        wrapped = cmd
    stdin, stdout, stderr = client.exec_command(wrapped, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if out:
        print(out, end="")
    if err:
        print(err, end="", file=sys.stderr)
    return exit_code, out, err


def sftp_upload(client, local_path, remote_path):
    sftp = client.open_sftp()
    try:
        sftp.put(local_path, remote_path)
        sftp.chmod(remote_path, 0o755)
    finally:
        sftp.close()


# ---
# 4. Command Implementations
# ---

def cmd_check(args):
    log_step("[1/3] Checking SSH Connection")
    client, _, _ = get_ssh_client(args.host, args.user, args.password)
    try:
        ec, out, _ = ssh_exec(client, "uname -m")
        arch = out.strip()
        if "aarch64" in arch:
            log_info("SSH connection OK. Architecture: aarch64 (Kunpeng)")
        elif "x86_64" in arch:
            log_info("SSH connection OK. Architecture: x86_64")
        else:
            log_error(f"SSH connection succeeded but architecture is unsupported: {arch}")
            sys.exit(1)
    finally:
        client.close()


def cmd_upload(args):
    log_step("[Upload] Uploading Scripts to /home")
    client, _, _ = get_ssh_client(args.host, args.user, args.password)
    try:
        for script_name, script_var, remote_desc in [
            ("install_devkit.sh", INSTALL_SCRIPT, "Install DevKit (auto-detect arch & download)"),
            ("scan_devkit.sh", SCAN_SCRIPT, "Execute DevKit scan"),
            ("encrypt-nodes-verify.sh", ENCRYPT_VERIFY_SCRIPT, "Encrypt nodes.conf passwords & verify SSH"),
        ]:
            if not os.path.isfile(script_var):
                log_error(f"{script_name} not found at {script_var} (co-located with devkit_remote.py)")
                sys.exit(1)
            log_info(f"Uploading {script_name} ...")
            sftp_upload(client, script_var, f"{DEVKIT_REMOTE_HOME}/{script_name}")
        log_info(f"All scripts uploaded to {DEVKIT_REMOTE_HOME}/ on server.")
        log_info(f"  {DEVKIT_REMOTE_HOME}/install_devkit.sh       - Install DevKit (auto-detect arch & download)")
        log_info(f"  {DEVKIT_REMOTE_HOME}/scan_devkit.sh          - Execute DevKit scan")
        log_info(f"  {DEVKIT_REMOTE_HOME}/encrypt-nodes-verify.sh - Encrypt nodes.conf passwords & verify SSH")
    finally:
        client.close()


def cmd_install(args):
    log_step("[Install] Installing DevKit (compress mode, auto-detect arch & download)")
    version = getattr(args, 'version', '') or ""
    if version:
        cmd = f"bash {DEVKIT_REMOTE_HOME}/install_devkit.sh --version={version}"
    else:
        cmd = f"bash {DEVKIT_REMOTE_HOME}/install_devkit.sh"
    log_info(f"Executing: {cmd}")
    client, _, _ = get_ssh_client(args.host, args.user, args.password)
    try:
        ssh_exec(client, cmd, timeout=600)
    finally:
        client.close()


def cmd_verify(args):
    log_step("[Verify] Verifying DevKit Installation")
    client, _, _ = get_ssh_client(args.host, args.user, args.password)
    try:
        ssh_exec(client, f"source /etc/profile 2>/dev/null; devkit version 2>/dev/null || {DEVKIT_REMOTE_HOME}/DevKit/DevKit-Sys-Mig-CLI-*/devkit version 2>/dev/null || echo 'DevKit not found'")
    finally:
        client.close()


def cmd_encrypt_verify(args):
    if getattr(args, "mask", False):
        log_step("[Encrypt+Verify --mask] Display nodes.conf with passwords masked (safe for chat)")
    elif getattr(args, "check", False):
        log_step("[Encrypt+Verify --check] Check nodes.conf for plaintext passwords")
    else:
        log_step("[Encrypt+Verify] Encrypt nodes.conf passwords & verify SSH connectivity")
    if not os.path.isfile(ENCRYPT_VERIFY_SCRIPT):
        log_error(f"encrypt-nodes-verify.sh not found at {ENCRYPT_VERIFY_SCRIPT}")
        sys.exit(1)
    log_info("Uploading encrypt-nodes-verify.sh ...")
    client, _, _ = get_ssh_client(args.host, args.user, args.password)
    try:
        sftp_upload(client, ENCRYPT_VERIFY_SCRIPT, f"{DEVKIT_REMOTE_HOME}/encrypt-nodes-verify.sh")
        ssh_exec(client, f"chmod +x {DEVKIT_REMOTE_HOME}/encrypt-nodes-verify.sh")
        nodes_arg = args.nodes_conf or ""
        if getattr(args, "mask", False):
            mode_arg = "--mask "
        elif getattr(args, "check", False):
            mode_arg = "--check "
        else:
            mode_arg = ""
        nodes_flag = f"--nodes-conf={nodes_arg} " if nodes_arg else ""
        cmd = f"bash {DEVKIT_REMOTE_HOME}/encrypt-nodes-verify.sh {mode_arg}{nodes_flag}".strip()
        log_info(f"Executing: {cmd}")
        ssh_exec(client, cmd, timeout=300)
    finally:
        client.close()


def cmd_scan(args):
    log_step("[Scan] DevKit Scan")
    scan_mode = args.scan_mode or ""

    if scan_mode not in ("stmt", "sbom", "mvn_analyse", "container_mig"):
        log_error("Scan mode is required. Modes: stmt|sbom|mvn_analyse|container_mig")
        sys.exit(1)

    log_info(f"Scan mode: {scan_mode}")
    log_info("Scan targets are read from nodes.conf on the DevKit server.")
    log_info("Target-server SSH is performed by the DevKit server's own ssh (Layer 2), not paramiko.")

    if not os.path.isfile(ENCRYPT_VERIFY_SCRIPT):
        log_error(f"encrypt-nodes-verify.sh not found at {ENCRYPT_VERIFY_SCRIPT}")
        log_error("Encryption of nodes.conf is mandatory before scan. Aborting.")
        sys.exit(1)

    client, _, _ = get_ssh_client(args.host, args.user, args.password)
    try:
        # ---- Mandatory pre-scan: encrypt nodes.conf & verify SSH ----
        log_step("[Pre-Scan] Encrypt nodes.conf & Verify SSH (mandatory)")
        sftp_upload(client, ENCRYPT_VERIFY_SCRIPT, f"{DEVKIT_REMOTE_HOME}/encrypt-nodes-verify.sh")
        ssh_exec(client, f"chmod +x {DEVKIT_REMOTE_HOME}/encrypt-nodes-verify.sh")

        nodes_arg = args.nodes_conf or ""
        nodes_flag = f"--nodes-conf={nodes_arg}" if nodes_arg else ""
        enc_cmd = f"bash {DEVKIT_REMOTE_HOME}/encrypt-nodes-verify.sh {nodes_flag}".strip()
        log_info(f"Executing: {enc_cmd}")
        ec, out, err = ssh_exec(client, enc_cmd, timeout=300)

        # Parse the verification summary for failed target count.
        fail_count = 0
        m = re.search(r"Failed:\s+(\d+)", out)
        if m:
            fail_count = int(m.group(1))

        if fail_count > 0:
            log_error(f"Pre-scan SSH verification failed for {fail_count} target(s). Scan aborted.")
            log_error("Fix nodes.conf on the DevKit server and re-run the scan.")
            sys.exit(1)

        log_info("Pre-scan encryption & SSH verification passed. Proceeding to scan.")

        # ---- Execute scan ----
        log_step(f"[Scan] Executing scan_devkit.sh {scan_mode}")
        cmd = f"bash {DEVKIT_REMOTE_HOME}/scan_devkit.sh --mode={scan_mode}"
        log_info(f"Executing: {cmd}")
        ec, out, err = ssh_exec(client, cmd, timeout=600)

        # ---- Record reports from this scan for targeted download ----
        report_names = []
        for line in out.split("\n"):
            m = re.match(r"\[INFO\].*Renamed:\s+\S+\s+->\s+(\S+)", line)
            if m:
                name = m.group(1)
                if name not in report_names:
                    report_names.append(name)

        if report_names:
            report_list_content = "\n".join(report_names) + "\n"
            sftp = client.open_sftp()
            try:
                with sftp.file("/tmp/devkit_last_scan_reports.txt", "w") as f:
                    f.write(report_list_content)
            finally:
                sftp.close()
            log_info(f"Recorded {len(report_names)} report(s) from this scan: {', '.join(report_names)}")
        else:
            log_info("No renamed reports detected in scan output.")
    finally:
        client.close()


def stream_tar_download(client, remote_files, local_dir, remote_report_dir):
    # Stream remote files back as one tar per batch (single network round-trip
    # per batch) instead of per-file SFTP gets — avoids N+1 network calls.
    # GNU tar strips the leading "/" from absolute paths when storing members,
    # so member names arrive as "home/report/..."; normalize both forms.
    prefix = remote_report_dir.lstrip("/") + "/"
    batch_size = 200

    for start in range(0, len(remote_files), batch_size):
        batch = remote_files[start:start + batch_size]
        log_info(f"Streaming batch {start // batch_size + 1} ({len(batch)} file(s)) via remote tar...")
        cmd = "tar -czf - " + " ".join(shlex.quote(f) for f in batch)
        stdin, stdout, stderr = client.exec_command(cmd, timeout=300)
        data = stdout.read()
        rc = stdout.channel.recv_exit_status()
        if rc != 0:
            err = stderr.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"remote tar failed (exit {rc}): {err}")

        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            for member in tar.getmembers():
                rel = member.name.lstrip("/")
                if rel.startswith(prefix):
                    rel = rel[len(prefix):]
                if not rel:
                    continue
                local_path = os.path.join(local_dir, rel)
                if member.isdir():
                    os.makedirs(local_path, exist_ok=True)
                    continue
                os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
                with tar.extractfile(member) as src:
                    with open(local_path, "wb") as dst:
                        dst.write(src.read())
                log_info(f"  Extracted: {member.name} -> {local_path}")


def cmd_download_report(args):
    local_dir = args.local_dir
    if not local_dir:
        log_error("--local-dir is required. Please provide the local directory path to save reports.")
        sys.exit(1)

    remote_report_dir = f"{DEVKIT_REMOTE_HOME}/report"
    download_all = getattr(args, "all", False)
    download_full = getattr(args, "full", False)

    log_step(f"[Download Report] Downloading reports to {local_dir}")
    client, _, _ = get_ssh_client(args.host, args.user, args.password)
    try:
        if download_all:
            log_info("Downloading ALL reports (--all mode).")
            stdin, stdout, stderr = client.exec_command(f"find {remote_report_dir} -type f 2>/dev/null")
            remote_files = [f.strip() for f in stdout.read().decode("utf-8", errors="replace").strip().split("\n") if f.strip()]
        else:
            # Download only reports from the last scan
            stdin, stdout, stderr = client.exec_command("cat /tmp/devkit_last_scan_reports.txt 2>/dev/null")
            report_names = [f.strip() for f in stdout.read().decode("utf-8", errors="replace").strip().split("\n") if f.strip()]

            if not report_names:
                log_error("No last-scan report list found at /tmp/devkit_last_scan_reports.txt.")
                log_error("Run a scan first, or use --all to download all reports.")
                sys.exit(1)

            log_info(f"Downloading reports from last scan only: {', '.join(report_names)}")

            remote_files = []
            for name in report_names:
                remote_path = f"{remote_report_dir}/{name}"
                if name.startswith("container_mig_") and not download_full:
                    log_info(f"container_mig report: downloading key files only (use --full for incompatible/ and output/ dirs)")
                    stdin, stdout, stderr = client.exec_command(f"find {remote_path} -maxdepth 1 -type f 2>/dev/null")
                    files = [f.strip() for f in stdout.read().decode("utf-8", errors="replace").strip().split("\n") if f.strip()]
                    remote_files.extend(files)
                else:
                    stdin, stdout, stderr = client.exec_command(f"find {remote_path} -type f 2>/dev/null")
                    files = [f.strip() for f in stdout.read().decode("utf-8", errors="replace").strip().split("\n") if f.strip()]
                    remote_files.extend(files)

        if not remote_files:
            log_error("No report files found to download.")
            sys.exit(1)

        log_info(f"Found {len(remote_files)} report file(s) on remote server.")
        os.makedirs(local_dir, exist_ok=True)

        # Batch download via streaming remote tar: one network round-trip per
        # batch, no per-file SFTP gets (avoids N+1).
        try:
            stream_tar_download(client, remote_files, local_dir, remote_report_dir)
        except Exception as exc:
            log_error(f"Batch tar download failed: {exc}")
            log_error("Ensure 'tar' is installed on the remote server, then retry.")
            sys.exit(1)

        log_info(f"Downloaded {len(remote_files)} file(s) to: {local_dir}")
        for remote_file in remote_files:
            rel = remote_file.replace(remote_report_dir + "/", "").replace(remote_report_dir, "")
            log_info(f"  {os.path.join(local_dir, rel)}")
    finally:
        client.close()


def cmd_login(args):
    cmd_check(args)
    cmd_upload(args)


def cmd_full(args):
    cmd_check(args)
    cmd_upload(args)
    cmd_install(args)
    cmd_verify(args)


# ---
# 5. CLI Parser & Main Entry
# ---

def build_parser():
    p = argparse.ArgumentParser(
        prog="devkit_remote.py",
        description="DevKit Remote Execution Script. "
                    "Layer 1: paramiko connects Agent→DevKit server. "
                    "Layer 2: DevKit server's local ssh connects to nodes.conf targets. "
                    "paramiko NEVER touches target servers. "
                    "EIP is auto-resolved from hcloud. "
                    "Credentials resolved from User->Machine env levels (NOT Process). "
                    "On auth failure, re-detects env vars; if still fails, asks user to update."
    )

    p.add_argument("--region", default="",
                   help="Huawei Cloud region (required, no default, no cache — user must select each time)")
    p.add_argument("--host", default="",
                   help="Server EIP (auto-resolved from hcloud if omitted)")
    p.add_argument("--server-id", default="",
                   help="ECS server ID (auto-resolved from hcloud if omitted)")

    sub = p.add_subparsers(dest="command", help="Available commands")

    sub.add_parser("check", help="Check SSH connection to server")
    sub.add_parser("upload", help="Upload install + scan scripts to /home")

    inst = sub.add_parser("install", help="Install DevKit (auto-detect arch, download & install, user request only)")
    inst.add_argument("--version", default="", help="DevKit version (default: 26.1.RC1)")

    sub.add_parser("verify", help="Verify DevKit installation")

    ev = sub.add_parser("encrypt-verify", help="Encrypt nodes.conf passwords & verify SSH to target servers")
    ev.add_argument("--nodes-conf", default="", help="Path to nodes.conf on DevKit server (auto-detected if omitted)")
    ev.add_argument("--mask", action="store_true", help="Display nodes.conf with all ssh_pass masked as *** (safe for chat; no encryption/verification performed)")
    ev.add_argument("--check", action="store_true", help="Only check if nodes.conf has plaintext ssh_pass (no encryption, no SSH verification)")

    scan = sub.add_parser("scan", help="Run DevKit scan (targets read from nodes.conf)")
    scan.add_argument("scan_mode",
                      choices=["stmt", "sbom", "mvn_analyse", "container_mig"],
                      help="Scan mode (required: stmt|sbom|mvn_analyse|container_mig)")
    scan.add_argument("--nodes-conf", default="", help="Path to nodes.conf on DevKit server (auto-detected if omitted)")

    dl = sub.add_parser("download-report", help="Download scan reports from Kunpeng server to local")
    dl.add_argument("--local-dir", default="", help="Local directory to save reports (required, user must provide)")
    dl.add_argument("--all", action="store_true", help="Download ALL reports (default: only last scan reports)")
    dl.add_argument("--full", action="store_true", help="Download full container_mig report including incompatible/ and output/ dirs")

    sub.add_parser("login", help="Check SSH + upload scripts (ready for install/scan)")
    sub.add_parser("full", help="Full workflow: check + upload + install + verify")

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    args.user = resolve_env_var("DEVKIT_ECS_USER")
    args.password = resolve_env_var("DEVKIT_ECS_PASSWORD")
    set_redact_secret(args.password)

    if not args.region:
        log_error("Region is required. No default. Please select a region (cn-north-4, cn-east-3, cn-south-1, cn-southwest-2).")
        sys.exit(1)

    if not args.host:
        eip, server_id = resolve_eip(args.region)
        args.host = eip
        if not args.server_id:
            args.server_id = server_id

    require_var("EIP (from hcloud)", args.host)
    require_var("DEVKIT_ECS_USER", args.user)
    require_var("DEVKIT_ECS_PASSWORD", args.password)

    dispatch = {
        "check": cmd_check,
        "upload": cmd_upload,
        "install": cmd_install,
        "verify": cmd_verify,
        "encrypt-verify": cmd_encrypt_verify,
        "scan": cmd_scan,
        "download-report": cmd_download_report,
        "login": cmd_login,
        "full": cmd_full,
    }

    if args.command in dispatch:
        dispatch[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
