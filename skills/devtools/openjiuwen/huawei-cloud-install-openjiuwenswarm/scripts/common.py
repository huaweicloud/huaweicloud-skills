#!/usr/bin/env python3
import os
import sys
import json
import re
import subprocess
import base64
from pathlib import Path

MAX_RETRY = 3
RETRY_DELAY = 5
DOWNLOAD_TIMEOUT = 600
STARTUP_TIMEOUT = 120

MIRROR_FILE_NAME = "jiuwenswarm_runtime.tar.gz"
BASE_DIR = "/root/tools/jiuwenswarm"
MIRROR_FILE = os.path.join(BASE_DIR, MIRROR_FILE_NAME)
EXTRACT_DIR = os.path.join(BASE_DIR, "jiuwenswarm_runtime")
RUNTIME_PYTHON = os.path.join(EXTRACT_DIR, "python", "bin", "python")
RUNTIME_INIT = os.path.join(EXTRACT_DIR, "python", "bin", "jiuwenswarm-init")
RUNTIME_START = os.path.join(EXTRACT_DIR, "python", "bin", "jiuwenswarm-start")
LOG_FILE = "/tmp/jiuwenswarm.log"
ENV_FILE = os.path.join(os.path.expanduser("~"), ".jiuwenswarm", "config", ".env")

LFS_API_URL = "https://gitcode.com/afeng5267/jiuwenswarm_runtime.git/info/lfs/objects/batch"
LFS_REPO_URL = "https://gitcode.com/afeng5267/jiuwenswarm_runtime.git"

DOWNLOAD_PROGRESS_FILE = "/tmp/jiuwenswarm_download_progress"


def get_lfs_info():
    """Fetch latest LFS OID and size by cloning the repo pointer file (GIT_LFS_SKIP_SMUDGE=1)."""
    import shutil
    import tempfile
    tmp_dir = tempfile.mkdtemp()
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "-b", "main", LFS_REPO_URL, tmp_dir],
            capture_output=True, check=True, timeout=60
        )
        pointer_file = os.path.join(tmp_dir, MIRROR_FILE_NAME)
        with open(pointer_file, 'r') as f:
            text = f.read().strip()
        oid = None
        size = None
        for line in text.splitlines():
            if line.startswith("oid sha256:"):
                oid = line.split("oid sha256:")[1].strip()
            elif line.startswith("size "):
                size = int(line.split("size ")[1].strip())
        if not oid or not size:
            raise ValueError("Failed to parse LFS pointer: {}".format(text[:200]))
        return oid, size
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def ensure_requests():
    try:
        __import__("requests")
    except ImportError:
        pass


def ensure_keyutils():
    """Install keyutils package via system package manager if keyctl is missing."""
    if subprocess.run("command -v keyctl", shell=True, capture_output=True).returncode == 0:
        return
    sudo = "sudo" if os.getuid() != 0 else ""
    for pm in ["dnf", "yum", "apt-get"]:
        if subprocess.run(f"command -v {pm}", shell=True, capture_output=True).returncode == 0:
            subprocess.run(f"{sudo} {pm} install -y keyutils", shell=True, capture_output=True)
            return


def output_error(error_type, message, fix_hint):
    print(json.dumps({
        "status": "error",
        "type": error_type,
        "message": message,
        "fix_hint": fix_hint
    }))
    sys.exit(1)


def ensure_base_dir():
    if not os.path.isdir(BASE_DIR):
        os.makedirs(BASE_DIR, exist_ok=True)


def is_port_listening(port):
    result = subprocess.run(
        f"ss -tlnp | grep ':{port}'",
        shell=True, capture_output=True
    )
    return result.returncode == 0


def get_web_port():
    """Get web frontend port with priority: .env > dynamic detection > default."""
    # Priority 1: Read from .env (persisted from previous successful start)
    try:
        env_path = Path(ENV_FILE)
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("WEB_PORT="):
                    return int(line.split("=", 1)[1].strip().strip('"'))
    except Exception:
        pass

    # Priority 2: Dynamic detection from running service
    ports = detect_ports_from_system()
    if 'frontend' in ports:
        return ports['frontend']

    # Priority 3: Default
    return 5173


def detect_ports_from_system():
    """Detect JiuwenSwarm ports from system listening ports.

    Parses 'ss -tlnp' output for known JiuwenSwarm port ranges.
    Supports multi-instance via offset (base + n*1000).

    Returns:
        dict: {port_type: port} e.g. {'frontend': 5173, 'web': 19000, ...}
    """
    ports = {}

    try:
        result = subprocess.run(
            "ss -tlnp 2>/dev/null",
            shell=True, capture_output=True, text=True, timeout=5
        )

        for line in result.stdout.splitlines():
            match = re.search(r'(?:\d{1,3}\.){3}\d{1,3}:(\d+)', line)
            if not match:
                continue
            port = int(match.group(1))

            # frontend: 5173 + n*1000 (5173-6173)
            if 5173 <= port <= 6173:
                ports['frontend'] = port
            # agent_server: 18092 + n*1000 (18092-19092, excluding 19000/19001)
            elif port == 18092 or (18092 < port <= 19092 and port not in (19000, 19001)):
                ports['agent_server'] = port
            # web: 19000 + n*1000 (19000-20000, not 19001)
            elif port == 19000 or 19000 < port <= 20000:
                # Only add if this isn't the gateway port
                if port != 19001:
                    ports['web'] = port
            # gateway: 19001 + n*1000 (19001-20001)
            elif port == 19001 or 19001 < port <= 20001:
                ports['gateway'] = port
    except Exception:
        pass

    return ports


def detect_ports_from_log():
    """Detect ports from JiuwenSwarm log file.
    
    Parses /tmp/jiuwenswarm.log for port information.
    
    Returns:
        dict: {port_type: port}
    """
    ports = {}
    
    if not os.path.exists(LOG_FILE):
        return ports
    
    try:
        with open(LOG_FILE, 'r') as f:
            # Read last 4KB (startup info usually at end)
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 4096))
            content = f.read()
        
        # Parse patterns from actual log:
        # "Gateway server started: ws://127.0.0.1:19001 [/acp, /tui]"
        # "started: Web ws://127.0.0.1:19000/ws  AgentServer: ws://127.0.0.1:18092"
        
        # Gateway port
        gateway_match = re.search(r'Gateway server started:.*?127\.0\.0\.1:(\d+)', content)
        if gateway_match:
            ports['gateway'] = int(gateway_match.group(1))
        
        # Web port - look for "Web ws://127.0.0.1:XXXX"
        web_match = re.search(r'Web ws://127\.0\.0\.1:(\d+)', content)
        if web_match:
            ports['web'] = int(web_match.group(1))
        
        # AgentServer port - look for "AgentServer: ws://127.0.0.1:XXXX"
        agent_match = re.search(r'AgentServer:.*?127\.0\.0\.1:(\d+)', content)
        if agent_match:
            ports['agent_server'] = int(agent_match.group(1))
            
    except Exception:
        pass
    
    return ports


def get_all_dynamic_ports():
    """Get all ports using dynamic detection.

    Priority: log parsing > system detection

    Returns:
        dict: {port_type: port} — may be empty if no ports detected
    """
    # Start with log parsing (most accurate)
    ports = detect_ports_from_log()

    # Supplement with system detection
    sys_ports = detect_ports_from_system()
    for k, v in sys_ports.items():
        if k not in ports:
            ports[k] = v

    return ports


def get_keyring_config():
    config = {
        "base_url": "",
        "api_key": "",
        "model_id": "",
        "models": []
    }

    try:
        sf = Path.home() / ".huawei/hwcloud/settings.json"
        if sf.exists():
            s = json.loads(sf.read_text())
            prov = s["providers"][s["current_provider"]]
            config["base_url"] = prov.get("base_url", "")
            config["model_id"] = s.get("current_model", "")
            config["models"] = [m["id"] for m in prov.get("models", []) if "id" in m]
    except Exception:
        pass

    try:
        def keyring_read():
            r = subprocess.run(["keyctl", "show", "@s"], capture_output=True, text=True)
            if r.returncode != 0:
                return ""
            for line in r.stdout.splitlines():
                if "keyring: HWCLOUD-Agent" in line:
                    krid = line.strip().split()[0]
                    r2 = subprocess.run(["keyctl", "show", krid], capture_output=True, text=True)
                    for l2 in r2.stdout.splitlines():
                        if "user: HWCLOUD-Agent" in l2:
                            kid = l2.strip().split()[0]
                            r3 = subprocess.run(["keyctl", "print", kid], capture_output=True, text=True)
                            if r3.returncode == 0 and r3.stdout.strip():
                                return base64.b64decode(r3.stdout.strip()).decode("utf-8")
            return ""

        config["api_key"] = keyring_read()
    except Exception:
        pass

    return config


def update_env_file(key, value):
    env_path = Path(ENV_FILE)
    if not env_path.exists():
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.touch()
        env_path.chmod(0o600)

    content = env_path.read_text()
    pattern = rf"^{re.escape(key)}=.*$"
    new_line = f"{key}={value}"

    if re.search(pattern, content, re.MULTILINE):
        content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
    else:
        content = content.rstrip("\n") + "\n" + new_line + "\n"

    env_path.write_text(content)
    env_path.chmod(0o600)