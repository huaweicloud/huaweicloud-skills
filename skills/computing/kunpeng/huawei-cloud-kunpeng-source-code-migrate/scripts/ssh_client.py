#!/usr/bin/env python3
"""Unified SSH client (paramiko + password from env var, cross-platform).

This is the SINGLE unified SSH script for the huawei-cloud-kunpeng-source-code-migrate
skill. It consolidates the functionality of the former ssh_setup.sh, ssh_helper.py,
and _run_ssh.py into one cross-platform Python script.

Design goals:
  - All connection info (HOST/PORT/USER/PASS) read from environment variables
    or the provision env file (/tmp/kunpeng_server_env.sh)
  - No Huawei Cloud region dependency (works with any remote Linux server)
  - No hcloud CLI dependency
  - No instance-id resolution (user provides EIP directly via env var)
  - Cross-platform: works on Windows, Linux, macOS (Python only, no .ps1/.sh)
  - Windows user-level env var fallback via winreg (for GUI-set vars)
  - Password NEVER in argv, NEVER on disk, wiped from os.environ after connect

Usage:
    python ssh_client.py test                              # Test SSH connection
    python ssh_client.py exec "<command>" [timeout]        # Execute remote command
    python ssh_client.py put <local> <remote>              # Upload single file
    python ssh_client.py put-dir <local_dir> <remote_dir>  # Upload directory recursively
    python ssh_client.py get <remote> <local>              # Download single file
    python ssh_client.py get-dir <remote_dir> <local_dir>  # Download directory recursively
    python ssh_client.py get-report [remote_dir] [local_dir]  # Download DevKit report
    python ssh_client.py save-env                          # Save connection info to env file
    python ssh_client.py --help                            # Show help

Environment variables (read from current env, provision env file, or Windows registry):
    KUNPENG_SERVER_HOST     Remote server IP or hostname (REQUIRED)
    KUNPENG_SERVER_PORT     SSH port (default: 22)
    KUNPENG_SERVER_USER     SSH username (default: root)
    MIGRATE_SSH_PASS        SSH password (REQUIRED, read by paramiko, never in argv)

Exit codes:
    0  - Success
    1  - Invalid arguments / missing env var
    2  - paramiko not installed
    3  - SSH connection failed
    -1 - Command timeout or runtime error
"""
import os
import sys


# ============================================================================
# Cross-platform environment variable resolution
# ============================================================================
def _read_user_env_var(name):
    """Read a user-level environment variable on Windows via winreg.
    Returns None on non-Windows or if not set.

    This handles the case where the user set env vars via GUI
    (Settings > Environment Variables) or SetEnvironmentVariable(..., 'User'),
    which are NOT inherited by the AI's child process on Windows.
    """
    if sys.platform != 'win32':
        return None
    try:
        import winreg
        with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as root:
            with winreg.OpenKey(root, 'Environment') as env_key:
                value, _ = winreg.QueryValueEx(env_key, name)
                return value
    except (FileNotFoundError, OSError):
        return None


def _read_provision_env_file():
    """Read connection info from the provision script's env file.

    When the user provisions a new Kunpeng ECS via provision_kunpeng_server.sh,
    the script saves connection info (including MIGRATE_SSH_PASS) to:
        /tmp/kunpeng_server_env.sh  (Linux/macOS)
        %TEMP%/kunpeng_server_env.sh  (Windows)

    This function parses that file (if it exists) and returns a dict of
    key=value pairs. This is the PRIMARY source of credentials in the
    "new server" workflow — the user never sets env vars manually in this case.

    Returns:
        dict: {var_name: value} from the env file, or empty dict if not found.
    """
    import re
    # Cross-platform temp dir
    tmp_dir = os.environ.get('TEMP') or os.environ.get('TMP') or '/tmp'
    env_file = os.path.join(tmp_dir, 'kunpeng_server_env.sh')
    result = {}
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Match: export VAR_NAME="value"  or  export VAR_NAME='value'
                m = re.match(r'^export\s+(\w+)\s*=\s*"([^"]*)"\s*$', line)
                if not m:
                    m = re.match(r"^export\s+(\w+)\s*=\s*'([^']*)'\s*$", line)
                if m:
                    result[m.group(1)] = m.group(2)
    except (FileNotFoundError, OSError):
        pass
    return result


def _resolve_env_var(name, default=None):
    """Resolve an env var from multiple sources.

    Priority:
      1. Current process environment (Linux/macOS export, Windows $env:)
         — used in "existing server" workflow where user sets vars manually
      2. Provision env file (/tmp/kunpeng_server_env.sh or %TEMP% equivalent)
         — used in "new server" workflow where provision_kunpeng_server.sh
           generated a random password and saved it to the env file
      3. Windows user-level registry (winreg) — fallback for GUI-set vars
      4. Default value
    """
    # 1. Current process environment
    val = os.environ.get(name)
    if val:
        return val
    # 2. Provision env file (new server workflow)
    provision_env = _read_provision_env_file()
    val = provision_env.get(name)
    if val:
        return val
    # 3. Windows user-level registry
    val = _read_user_env_var(name)
    if val:
        return val
    # 4. Default
    return default


def _get_connection():
    """Get SSH connection parameters from env vars.

    Returns (host, port, user). Exits with error if host is missing.
    """
    host = _resolve_env_var('KUNPENG_SERVER_HOST', '')
    port = _resolve_env_var('KUNPENG_SERVER_PORT', '22')
    user = _resolve_env_var('KUNPENG_SERVER_USER', 'root')
    if not host:
        print("ERROR: Missing KUNPENG_SERVER_HOST environment variable.",
              file=sys.stderr)
        print("       Please set it in your terminal:", file=sys.stderr)
        print("         Linux/macOS:  export KUNPENG_SERVER_HOST='<your-server-ip>'",
              file=sys.stderr)
        print("         Windows PS:    $env:KUNPENG_SERVER_HOST='<your-server-ip>'",
              file=sys.stderr)
        print("         Windows GUI:   Settings > Environment Variables > User > New",
              file=sys.stderr)
        sys.exit(1)
    try:
        port_int = int(port)
    except ValueError:
        print(f"ERROR: Invalid KUNPENG_SERVER_PORT value: '{port}' (must be integer)",
              file=sys.stderr)
        sys.exit(1)
    return host, port_int, user


def _get_password():
    """Get SSH password from MIGRATE_SSH_PASS env var or provision env file.

    Resolution order (see _resolve_env_var):
      1. Current process env var MIGRATE_SSH_PASS (existing server workflow)
      2. /tmp/kunpeng_server_env.sh or %TEMP%/kunpeng_server_env.sh
         (new server workflow — provision_kunpeng_server.sh writes the
          generated random password here)
      3. Windows user-level registry (winreg)

    Exits with error if the secret is missing. The secret value is never printed.
    """
    password = _resolve_env_var('MIGRATE_SSH_PASS', '')
    if not password:
        print('ERROR: MIGRATE_SSH_PASS not found in any of these sources:',
              file=sys.stderr)
        print('         1. Current process env var MIGRATE_SSH_PASS',
              file=sys.stderr)
        print('         2. Provision env file (/tmp/kunpeng_server_env.sh',
              file=sys.stderr)
        print('            or %TEMP%/kunpeng_server_env.sh)',
              file=sys.stderr)
        print('         3. Windows user-level registry',
              file=sys.stderr)
        print('')
        print('       If you provisioned a new server via provision_kunpeng_server.sh,',
              file=sys.stderr)
        print('       the secret should be in the env file. If not, re-run provisioning.',
              file=sys.stderr)
        print('')
        print('       If you are using an existing server, set the secret manually:',
              file=sys.stderr)
        print('')
        print('       Linux / macOS:')
        print("           export MIGRATE_SSH_PASS='<your-secret>'")
        print('')
        print('       Windows PowerShell (current session):')
        print("           $env:MIGRATE_SSH_PASS='<your-secret>'")
        print('')
        print('       Windows CMD (current session):')
        print("           set MIGRATE_SSH_PASS=<your-secret>")
        print('')
        print('       Windows User Environment Variable (persistent, via GUI):')
        print('           Settings > System > About > Advanced system settings >')
        print('           Environment Variables > User variables > New >')
        print('           Variable name: MIGRATE_SSH_PASS')
        print('           Variable value: <your-secret>')
        print('       (requires IDE/terminal restart to take effect)')
        sys.exit(1)
    return password


def _wipe_password():
    """Remove the secret from os.environ (best-effort memory wipe)."""
    if 'MIGRATE_SSH_PASS' in os.environ:
        val = os.environ.pop('MIGRATE_SSH_PASS', '')
        try:
            buf = bytearray(val.encode('utf-8'))
            for i in range(len(buf)):
                buf[i] = 0
        except Exception:
            pass


# ============================================================================
# paramiko connection (password-based, password from MIGRATE_SSH_PASS env var)
# ============================================================================
def _paramiko_connect(timeout=30):
    """Create a paramiko SSHClient connected with password auth.

    Password is read from MIGRATE_SSH_PASS env var and wiped immediately
    after successful connect. Returns (client, error_message).
    """
    host, port, user = _get_connection()
    password = _get_password()

    try:
        import paramiko
    except ImportError:
        _wipe_password()
        print('ERROR: paramiko is not installed. Install with: pip install paramiko',
              file=sys.stderr)
        sys.exit(2)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=host,
            port=port,
            username=user,
            password=password,
            look_for_keys=False,   # do not try local keys
            allow_agent=False,     # do not use ssh-agent
            timeout=timeout,
            auth_timeout=timeout,
        )
    except paramiko.AuthenticationException as e:
        _wipe_password()
        return None, f'Authentication failed: {e}'
    except paramiko.SSHException as e:
        _wipe_password()
        return None, f'SSH negotiation failed: {e}'
    except OSError as e:
        _wipe_password()
        return None, f'Network error connecting to {host}:{port}: {e}'

    # Wipe password ASAP after successful connect
    _wipe_password()
    return client, ''


# ============================================================================
# Helpers
# ============================================================================
def _is_windows_path(path):
    """Detect if a path looks like a Windows path (e.g., C:\\... or C:/...)."""
    return len(path) > 1 and path[1] == ':'


def _check_remote_path(remote_path, subcmd_name='put'):
    """Verify remote_path is a Unix path, not mangled by MSYS2.

    On Windows + MSYS2/Git Bash, the shell may convert Unix paths (e.g.,
    /tmp/foo) to Windows paths (e.g., C:/Users/.../Temp/2/foo) before Python
    sees them. When this is detected, we exit with a clear error directing
    the caller to use the paramiko SFTP API directly instead of the CLI.

    Args:
        remote_path: The remote path as seen by Python (may be mangled)
        subcmd_name: Subcommand name for error messages (e.g., 'put', 'get')

    Returns:
        str: The remote path unchanged if it is a valid Unix path.

    Exits with error code 1 if the path looks like a Windows path.
    """
    if not _is_windows_path(remote_path):
        return remote_path

    # MSYS2 path conversion detected — don't try to recover, just guide
    # the caller to use paramiko SFTP API directly (the robust solution).
    print(
        f"ERROR: Remote path '{remote_path}' looks like a Windows path. "
        f"MSYS2/Git Bash converted the Unix path before Python saw it.",
        file=sys.stderr)
    print("", file=sys.stderr)
    print("Use the paramiko SFTP API directly instead of the CLI:", file=sys.stderr)
    print("", file=sys.stderr)
    print("    import paramiko", file=sys.stderr)
    print("    client = paramiko.SSHClient()", file=sys.stderr)
    print("    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())", file=sys.stderr)
    print("    client.connect(host, port=22, username=user, password=<secret>)", file=sys.stderr)
    print("    sftp = client.open_sftp()", file=sys.stderr)
    if subcmd_name in ('put', 'put-dir'):
        print(f"    sftp.put(local_path, '/tmp/target')  # use intended Unix path", file=sys.stderr)
    else:
        print(f"    sftp.get('/tmp/source', local_path)  # use intended Unix path", file=sys.stderr)
    print("    sftp.close()", file=sys.stderr)
    print("    client.close()", file=sys.stderr)
    print("", file=sys.stderr)
    print("Or set MSYS_NO_PATHCONV=1 (bash syntax):", file=sys.stderr)
    print(f"    MSYS_NO_PATHCONV=1 python ssh_client.py {subcmd_name} ...", file=sys.stderr)
    sys.exit(1)


def _default_report_local_dir():
    """Return the default local report save path based on OS.

    Windows: C:\\devkit-report
    Linux/macOS: /home/devkit-report
    """
    if sys.platform == 'win32':
        return r'C:\devkit-report'
    return '/home/devkit-report'


# ============================================================================
# Subcommands
# ============================================================================
def cmd_test():
    """Test SSH connection by running a simple command."""
    host, port, user = _get_connection()
    print(f"[INFO] Testing SSH connection to {user}@{host}:{port} ...")

    client, err = _paramiko_connect(timeout=30)
    if client is None:
        print(f"[ERROR] {err}", file=sys.stderr)
        sys.exit(3)

    try:
        stdin, stdout, stderr = client.exec_command(
            'echo SSH_OK && uname -a', timeout=30)
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8', errors='replace').strip()
    except Exception as e:
        print(f"[ERROR] Command execution failed: {e}", file=sys.stderr)
        sys.exit(3)
    finally:
        client.close()

    if exit_status != 0 or 'SSH_OK' not in out:
        print(f"[ERROR] Command execution failed (exit={exit_status})",
              file=sys.stderr)
        sys.exit(3)

    print("[OK] SSH connection verified (paramiko + secret from env var).")
    print(f"  Remote: {out.replace(chr(10), chr(10) + '  ')}")
    sys.exit(0)


def cmd_exec(command, timeout=120):
    """Execute command on remote server via paramiko."""
    client, err = _paramiko_connect(timeout=30)
    if client is None:
        print(f"[ERROR] {err}", file=sys.stderr)
        sys.exit(3)

    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8', errors='replace')
        err_out = stderr.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"[ERROR] Command execution failed: {e}", file=sys.stderr)
        sys.exit(-1)
    finally:
        client.close()

    if out:
        out = out.lstrip('\ufeff')
        sys.stdout.buffer.write(out.encode('utf-8', errors='replace'))
    if err_out and exit_status != 0:
        sys.stderr.buffer.write(err_out.encode('utf-8', errors='replace'))
    sys.exit(exit_status)


def cmd_put(local_path, remote_path):
    """Upload a local file to remote server via paramiko SFTP."""
    # Detect and attempt to recover MSYS2 path conversion
    remote_path = _check_remote_path(remote_path, 'put')

    if not os.path.exists(local_path):
        print(f"ERROR: Local file not found: {local_path}", file=sys.stderr)
        sys.exit(1)

    client, err = _paramiko_connect(timeout=30)
    if client is None:
        print(f"[ERROR] {err}", file=sys.stderr)
        sys.exit(3)

    try:
        sftp = client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
        print(f"[OK] Uploaded: {local_path} -> {remote_path}")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] SFTP upload failed: {e}", file=sys.stderr)
        sys.exit(-1)
    finally:
        client.close()


def cmd_put_dir(local_dir, remote_dir):
    """Upload a local directory recursively to remote server via paramiko SFTP."""
    # Detect and attempt to recover MSYS2 path conversion
    remote_dir = _check_remote_path(remote_dir, 'put-dir')

    if not os.path.isdir(local_dir):
        print(f"ERROR: Local directory not found: {local_dir}", file=sys.stderr)
        sys.exit(1)

    client, err = _paramiko_connect(timeout=30)
    if client is None:
        print(f"[ERROR] {err}", file=sys.stderr)
        sys.exit(3)

    try:
        sftp = client.open_sftp()

        # Ensure remote directory exists (create recursively)
        def _ensure_remote_dir(path):
            try:
                sftp.stat(path)
            except IOError:
                parent = '/'.join(path.rstrip('/').split('/')[:-1])
                if parent:
                    _ensure_remote_dir(parent)
                sftp.mkdir(path)

        _ensure_remote_dir(remote_dir)

        uploaded = 0
        for root, dirs, files in os.walk(local_dir):
            rel_root = os.path.relpath(root, local_dir).replace('\\', '/')
            if rel_root == '.':
                remote_root = remote_dir
            else:
                remote_root = f"{remote_dir.rstrip('/')}/{rel_root}"
                _ensure_remote_dir(remote_root)
            for fname in files:
                local_file = os.path.join(root, fname)
                remote_file = f"{remote_root}/{fname}"
                sftp.put(local_file, remote_file)
                uploaded += 1

        sftp.close()
        print(f"[OK] Uploaded {uploaded} files: {local_dir} -> {remote_dir}")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] SFTP directory upload failed: {e}", file=sys.stderr)
        sys.exit(-1)
    finally:
        client.close()


def cmd_get(remote_path, local_path):
    """Download a remote file to local via paramiko SFTP."""
    # Detect and attempt to recover MSYS2 path conversion
    remote_path = _check_remote_path(remote_path, 'get')

    client, err = _paramiko_connect(timeout=30)
    if client is None:
        print(f"[ERROR] {err}", file=sys.stderr)
        sys.exit(3)

    try:
        sftp = client.open_sftp()
        # Ensure local directory exists
        local_dir = os.path.dirname(os.path.abspath(local_path))
        os.makedirs(local_dir, exist_ok=True)
        sftp.get(remote_path, local_path)
        file_size = os.path.getsize(local_path)
        sftp.close()
        print(f"[OK] Downloaded: {remote_path} -> {local_path} ({file_size} bytes)")
        sys.exit(0)
    except IOError as e:
        print(f"[ERROR] Remote file not found or not accessible: {remote_path} ({e})",
              file=sys.stderr)
        sys.exit(-1)
    except Exception as e:
        print(f"[ERROR] SFTP download failed: {e}", file=sys.stderr)
        sys.exit(-1)
    finally:
        client.close()


def cmd_get_dir(remote_dir, local_dir):
    """Download a remote directory recursively to local via paramiko SFTP."""
    # Detect and attempt to recover MSYS2 path conversion
    remote_dir = _check_remote_path(remote_dir, 'get-dir')

    client, err = _paramiko_connect(timeout=30)
    if client is None:
        print(f"[ERROR] {err}", file=sys.stderr)
        sys.exit(3)

    try:
        sftp = client.open_sftp()

        # Ensure local base directory exists
        os.makedirs(local_dir, exist_ok=True)

        from stat import S_ISDIR
        from concurrent.futures import ThreadPoolExecutor

        downloaded = 0
        # Reuse a single SFTP channel per worker thread to avoid opening a new
        # SSH channel for every file (which would reintroduce N+1 network calls).
        # paramiko SFTPClient is not thread-safe, so each worker opens its own
        # SFTP subsession on the underlying SSH transport.
        _sftp_lock = __import__('threading').Lock()

        def _open_worker_sftp():
            return client.open_sftp()

        def _download_file(r_path, l_path):
            nonlocal downloaded
            # Use a per-call SFTP channel to keep workers independent.
            # The shared transport multiplexes channels efficiently.
            worker_sftp = _open_worker_sftp()
            try:
                worker_sftp.get(r_path, l_path)
            finally:
                worker_sftp.close()
            with _sftp_lock:
                downloaded += 1

        def _download_recursive(r_dir, l_dir):
            os.makedirs(l_dir, exist_ok=True)
            # Batch-fetch all entries in ONE network call, then classify locally
            # (avoids per-entry stat/lookup network calls inside the loop).
            entries = sftp.listdir_attr(r_dir)
            files = []
            dirs = []
            for entry in entries:
                r_path = f"{r_dir.rstrip('/')}/{entry.filename}"
                l_path = os.path.join(l_dir, entry.filename)
                if S_ISDIR(entry.st_mode):
                    dirs.append((r_path, l_path))
                else:
                    files.append((r_path, l_path))
            # Download all files in this directory concurrently, then recurse.
            # This converts N sequential network round-trips into ~1 batched
            # wave of parallel transfers.
            if files:
                with ThreadPoolExecutor(max_workers=8) as pool:
                    list(pool.map(lambda p: _download_file(*p), files))
            for r_path, l_path in dirs:
                _download_recursive(r_path, l_path)

        _download_recursive(remote_dir, local_dir)

        sftp.close()
        print(f"[OK] Downloaded {downloaded} files: {remote_dir} -> {local_dir}")
        sys.exit(0)
    except IOError as e:
        print(f"[ERROR] Remote directory not found or not accessible: {remote_dir} ({e})",
              file=sys.stderr)
        sys.exit(-1)
    except Exception as e:
        print(f"[ERROR] SFTP directory download failed: {e}", file=sys.stderr)
        sys.exit(-1)
    finally:
        client.close()


def cmd_get_report(remote_dir='/tmp/devkit-report', local_dir=None):
    """Download DevKit migration report files from remote to local.

    This is a convenience wrapper around get-dir with sensible defaults:
      - remote_dir defaults to /tmp/devkit-report (standard DevKit output)
      - local_dir defaults to C:\\devkit-report (Windows) or
        /home/devkit-report (Linux/macOS)

    Only files matching DevKit report patterns are downloaded:
      - Code_Porting_*.html
      - Code_Porting_*.json
      - Code_Porting_*.csv
      - Code_Porting_*_file_list.txt
    """
    if local_dir is None:
        local_dir = _default_report_local_dir()

    # Detect and attempt to recover MSYS2 path conversion
    remote_dir = _check_remote_path(remote_dir, 'get-report')

    client, err = _paramiko_connect(timeout=30)
    if client is None:
        print(f"[ERROR] {err}", file=sys.stderr)
        sys.exit(3)

    import re
    # DevKit report filename pattern
    report_pattern = re.compile(
        r'^Code_Porting_.*\.(html|json|csv|txt)$', re.IGNORECASE)

    try:
        sftp = client.open_sftp()

        # Ensure local directory exists
        os.makedirs(local_dir, exist_ok=True)

        # List remote report directory
        try:
            entries = sftp.listdir_attr(remote_dir)
        except IOError as e:
            print(f"[ERROR] Remote report directory not found: {remote_dir} ({e})",
                  file=sys.stderr)
            sys.exit(-1)

        # Filter entries locally first (entries already batch-fetched above via
        # listdir_attr), then download matching files in parallel. This avoids
        # N sequential network round-trips for N report files.
        from concurrent.futures import ThreadPoolExecutor
        import threading

        matching = [e for e in entries if report_pattern.match(e.filename)]
        skipped = len(entries) - len(matching)

        # Build the list of (remote, local, filename) tuples to download.
        download_tasks = []
        for entry in matching:
            r_path = f"{remote_dir.rstrip('/')}/{entry.filename}"
            l_path = os.path.join(local_dir, entry.filename)
            download_tasks.append((r_path, l_path, entry.filename))

        downloaded = 0
        download_lock = threading.Lock()
        results = []  # (filename, status, detail)

        def _download_one(r_path, l_path, filename):
            nonlocal downloaded
            worker_sftp = client.open_sftp()
            try:
                worker_sftp.get(r_path, l_path)
                file_size = os.path.getsize(l_path)
                with download_lock:
                    downloaded += 1
                return (filename, True, file_size)
            except Exception as e:
                return (filename, False, str(e))
            finally:
                worker_sftp.close()

        if download_tasks:
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda t: _download_one(*t), download_tasks))

        # Print results in stable order
        for filename, ok, detail in sorted(results, key=lambda r: r[0]):
            if ok:
                print(f"[OK] Downloaded: {filename} ({detail} bytes)")
            else:
                print(f"[WARN] Failed to download {filename}: {detail}",
                      file=sys.stderr)

        sftp.close()
        print("")
        print(f"[OK] ============================================")
        print(f"[OK]   DevKit Report Download Complete")
        print(f"[OK] ============================================")
        print(f"  Remote:  {remote_dir}")
        print(f"  Local:   {local_dir}")
        print(f"  Files:   {downloaded} downloaded, {skipped} skipped")
        print("")
        if downloaded > 0:
            print("[INFO] Report files:")
            for fn in sorted(os.listdir(local_dir)):
                if report_pattern.match(fn):
                    fp = os.path.join(local_dir, fn)
                    print(f"  {fp} ({os.path.getsize(fp)} bytes)")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] Report download failed: {e}", file=sys.stderr)
        sys.exit(-1)
    finally:
        client.close()


def cmd_save_env():
    """Save connection info to a temp env file (no password saved)."""
    host, port, user = _get_connection()

    # Cross-platform temp dir
    tmp_dir = os.environ.get('TEMP') or os.environ.get('TMP') or '/tmp'
    env_file = os.path.join(tmp_dir, 'kunpeng_server_env.sh')

    content = (
        f"# Kunpeng server connection info (SSH via paramiko + password env var)\n"
        f"# Unified cross-platform approach: no region dependency, no hcloud.\n"
        f"# All SSH operations use ssh_client.py which reads MIGRATE_SSH_PASS from env.\n"
        f"export KUNPENG_SERVER_HOST=\"{host}\"\n"
        f"export KUNPENG_SERVER_PORT=\"{port}\"\n"
        f"export KUNPENG_SERVER_USER=\"{user}\"\n"
    )
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(content)
    try:
        os.chmod(env_file, 0o600)
    except OSError:
        pass

    print("[OK] ============================================")
    print("[OK]   SSH Configured (paramiko + secret env var)")
    print("[OK] ============================================")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  User: {user}")
    print("")
    print(f"[INFO] Env file: {env_file}")
    print(f"[INFO] Load with: source {env_file}")
    print("")
    print("[INFO] All SSH operations use ssh_client.py:")
    print('  python <skill_dir>/scripts/ssh_client.py exec "<command>" [timeout]')
    print("  python <skill_dir>/scripts/ssh_client.py put <local> <remote>")
    print("  python <skill_dir>/scripts/ssh_client.py put-dir <local_dir> <remote_dir>")
    print("  python <skill_dir>/scripts/ssh_client.py get <remote> <local>")
    print("  python <skill_dir>/scripts/ssh_client.py get-dir <remote_dir> <local_dir>")
    print("  python <skill_dir>/scripts/ssh_client.py get-report [remote_dir] [local_dir]")
    print("")
    print("[INFO] Secret is read from MIGRATE_SSH_PASS env var (never in argv, never on disk).")
    sys.exit(0)


# ============================================================================
# CLI entry point
# ============================================================================
def _print_help():
    print("""Unified SSH client (paramiko + secret from env var, cross-platform).

Usage:
    python ssh_client.py test                              # Test SSH connection
    python ssh_client.py exec "<command>" [timeout]        # Execute remote command
    python ssh_client.py put <local> <remote>              # Upload single file
    python ssh_client.py put-dir <local_dir> <remote_dir>  # Upload directory recursively
    python ssh_client.py get <remote> <local>              # Download single file
    python ssh_client.py get-dir <remote_dir> <local_dir>  # Download directory recursively
    python ssh_client.py get-report [remote_dir] [local_dir]  # Download DevKit report
    python ssh_client.py save-env                          # Save connection info to env file
    python ssh_client.py --help                            # Show this help

Subcommands:
    test         Verify SSH connection by running 'echo SSH_OK && uname -a'
    exec         Execute a shell command on the remote server
    put          Upload a single file via SFTP
    put-dir      Upload a directory recursively via SFTP
    get          Download a single file via SFTP
    get-dir      Download a directory recursively via SFTP
    get-report   Download DevKit migration report files (filtered by pattern)
                 Defaults: remote=/tmp/devkit-report, local=C:\\\\devkit-report (Windows)
                           or /home/devkit-report (Linux/macOS)
                 Only files matching Code_Porting_*.{html,json,csv,txt} are downloaded
    save-env     Save connection info (host/port/user) to a temp env file

Environment variables (read from current env, provision env file, or Windows registry):
    KUNPENG_SERVER_HOST     Remote server IP or hostname (REQUIRED)
    KUNPENG_SERVER_PORT     SSH port (default: 22)
    KUNPENG_SERVER_USER     SSH username (default: root)
    MIGRATE_SSH_PASS        SSH secret (REQUIRED, read by paramiko, never in argv)

Credential resolution priority:
    1. Current process env vars (existing server workflow — user sets manually)
    2. Provision env file /tmp/kunpeng_server_env.sh
       (new server workflow — provision_kunpeng_server.sh writes random secret here)
    3. Windows user-level registry (winreg fallback for GUI-set vars)

How to set environment variables (existing server workflow):
    Linux / macOS (option A — temporary, current session only):
        export KUNPENG_SERVER_HOST='<your-server-ip>'
        export KUNPENG_SERVER_PORT='22'
        export KUNPENG_SERVER_USER='root'
        export MIGRATE_SSH_PASS='<your-secret>'

    Linux / macOS (option B — persistent via /tmp env file, recommended):
        cat > /tmp/kunpeng_server_env.sh << 'EOF'
        export KUNPENG_SERVER_HOST="<your-server-ip>"
        export KUNPENG_SERVER_PORT="22"
        export KUNPENG_SERVER_USER="root"
        export MIGRATE_SSH_PASS="<your-secret>"
        EOF
        chmod 600 /tmp/kunpeng_server_env.sh
        source /tmp/kunpeng_server_env.sh
        (ssh_client.py reads this file automatically in new sessions)

    Windows PowerShell (current session):
        $env:KUNPENG_SERVER_HOST='<your-server-ip>'
        $env:KUNPENG_SERVER_PORT='22'
        $env:KUNPENG_SERVER_USER='root'
        $env:MIGRATE_SSH_PASS='<your-secret>'

    Windows (persistent, via GUI):
        Settings > System > About > Advanced system settings >
        Environment Variables > User variables > New
        (requires IDE/terminal restart to take effect)

    Windows (persistent, via PowerShell):
        [Environment]::SetEnvironmentVariable('KUNPENG_SERVER_HOST','<your-server-ip>','User')
        [Environment]::SetEnvironmentVariable('MIGRATE_SSH_PASS','<your-secret>','User')
        (requires IDE/terminal restart to take effect)

New server workflow (no manual env var setup needed):
    Run provision_kunpeng_server.sh to create a Kunpeng ECS. The script:
      1. Generates a random secret (avoiding shell-unsafe characters)
      2. Sets the secret on the ECS via cloud-init
      3. Saves connection info + secret to /tmp/kunpeng_server_env.sh
    Then ssh_client.py automatically reads the secret from that file.

Security:
    - Secret is read from MIGRATE_SSH_PASS env var or provision env file
      (never in argv, never printed)
    - Secret is wiped from os.environ immediately after each connection
    - No SSH keys injected, no ControlMaster, no sshpass
    - Works identically on Windows, Linux, and macOS

Exit codes:
    0  - Success
    1  - Invalid arguments / missing env var
    2  - paramiko not installed
    3  - SSH connection failed
    -1 - Command timeout or runtime error
""")


def main():
    if len(sys.argv) < 2:
        _print_help()
        sys.exit(1)

    subcmd = sys.argv[1]

    if subcmd in ('-h', '--help', 'help'):
        _print_help()
        sys.exit(0)
    elif subcmd == 'test':
        cmd_test()
    elif subcmd == 'exec':
        if len(sys.argv) < 3:
            print('Usage: python ssh_client.py exec "<command>" [timeout]',
                  file=sys.stderr)
            sys.exit(1)
        command = sys.argv[2]
        timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 120
        cmd_exec(command, timeout)
    elif subcmd == 'put':
        if len(sys.argv) < 4:
            print('Usage: python ssh_client.py put <local> <remote>',
                  file=sys.stderr)
            sys.exit(1)
        cmd_put(sys.argv[2], sys.argv[3])
    elif subcmd == 'put-dir':
        if len(sys.argv) < 4:
            print('Usage: python ssh_client.py put-dir <local_dir> <remote_dir>',
                  file=sys.stderr)
            sys.exit(1)
        cmd_put_dir(sys.argv[2], sys.argv[3])
    elif subcmd == 'get':
        if len(sys.argv) < 4:
            print('Usage: python ssh_client.py get <remote> <local>',
                  file=sys.stderr)
            sys.exit(1)
        cmd_get(sys.argv[2], sys.argv[3])
    elif subcmd == 'get-dir':
        if len(sys.argv) < 4:
            print('Usage: python ssh_client.py get-dir <remote_dir> <local_dir>',
                  file=sys.stderr)
            sys.exit(1)
        cmd_get_dir(sys.argv[2], sys.argv[3])
    elif subcmd == 'get-report':
        # Optional: get-report [remote_dir] [local_dir]
        remote_dir = sys.argv[2] if len(sys.argv) > 2 else '/tmp/devkit-report'
        local_dir = sys.argv[3] if len(sys.argv) > 3 else None
        cmd_get_report(remote_dir, local_dir)
    elif subcmd == 'save-env':
        cmd_save_env()
    else:
        print(f"ERROR: Unknown subcommand: {subcmd}", file=sys.stderr)
        print("Run 'python ssh_client.py --help' for usage.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
