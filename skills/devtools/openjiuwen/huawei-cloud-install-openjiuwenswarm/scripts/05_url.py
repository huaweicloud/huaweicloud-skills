#!/usr/bin/env python3
"""Phase 5: Output web URL. Run as: python3 scripts/05_url.py"""
import os
import sys
import re
import socket
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

container_id = ""

# Priority 1: Environment variable (most authoritative)
container_id = os.environ.get("DEVENVD_ID", "").strip()

# Priority 2: hostname (reliable in container environments)
if not container_id:
    try:
        container_id = socket.gethostname().strip()
    except Exception:
        pass

# Priority 3: Parse from /proc/self/cgroup
if not container_id:
    try:
        with open("/proc/self/cgroup") as f:
            content = f.read()
        # Try k8s pod UUID pattern: .../pod<uuid>/...
        m = re.search(r"pod([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})", content)
        if not m:
            m = re.search(r"pod([a-f0-9]{32})", content)
        # Try docker container ID pattern: .../docker/<hex64>...
        if not m:
            m = re.search(r"docker[/=]([a-f0-9]{64})", content)
        # Fallback: any 32+ hex string at the end of a cgroup line
        if not m:
            m = re.search(r"([a-f0-9]{32,})", content)
        if m:
            container_id = m.group(1)[:32]
    except Exception:
        pass

if not container_id:
    output_error(
        "container_id_not_found",
        "Failed to get container ID, check DEVENVD_ID env var",
        "export DEVENVD_ID=<your_container_id>"
    )

# Normalize: lowercase, remove dashes
container_id = container_id.lower().replace("-", "")

# Validate: must be 32-char hex string
if not re.match(r'^[a-f0-9]{32}$', container_id):
    output_error(
        "invalid_container_id",
        f"Invalid container ID format: {container_id}",
        "Container ID should be lowercase hex, 32 chars"
    )

url = f"https://{get_web_port()}-{container_id}.workspace.developer.huaweicloud.com"
print(f"[5/5] \u2705 Web URL: {url}", flush=True)