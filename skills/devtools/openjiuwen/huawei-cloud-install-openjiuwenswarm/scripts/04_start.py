"""Phase 4: Start service. Run as: python3 scripts/04_start.py"""
import os
import sys
import subprocess
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

# Check if service already running using dynamic detection
existing_ports = detect_ports_from_system()
if len(existing_ports) >= 4:
    print("[4/5] ⏭️ Already done: service already running, skip start", flush=True)
    sys.exit(0)

# If some ports are occupied (partial old instance), stop them first
if len(existing_ports) > 0:
    print(f"[4/5] 🛑 Stopping existing instance (ports found: {existing_ports})...", flush=True)
    try:
        # Kill processes occupying jiuwenswarm ports
        result = subprocess.run(
            "ss -tlnp 2>/dev/null | grep -E ':(517[0-9]|1809[0-9]|1900[0-9]|1901[0-9])' | grep -oP 'pid=\\K\\d+' | sort -u",
            shell=True, capture_output=True, text=True, timeout=5
        )
        pids = result.stdout.strip().split()
        for pid in pids:
            if pid:
                os.kill(int(pid), 9)
        # Wait for ports to be released
        time.sleep(2)
    except Exception:
        pass

if not os.path.isfile(RUNTIME_START):
    output_error("start_not_found",
                 f"Start script not found: {RUNTIME_START}",
                 "Check mirror archive structure")

print("[4/5] 🚀 Starting service...", flush=True)

try:
    proc = subprocess.Popen(
        RUNTIME_START,
        stdout=open(LOG_FILE, "a"),
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid
    )
except Exception as e:
    output_error("start_failed",
                 f"Failed to start service: {str(e)}",
                 "Check service script permissions")

# Wait for ports using dynamic detection
EXPECTED_PORTS = 4  # frontend, web, gateway, agent_server
start_time = time.time()
last_reported = -1

while time.time() - start_time < STARTUP_TIMEOUT:
    # Early exit: if the subprocess has already crashed, no point waiting
    if proc.poll() is not None:
        exit_code = proc.returncode
        output_error("start_failed",
                     f"Service process exited prematurely with code {exit_code}",
                     "Check /tmp/jiuwenswarm.log for details")

    detected = detect_ports_from_system()
    ready = len(detected)

    if ready != last_reported and ready > 0:
        pct = int(ready / EXPECTED_PORTS * 100)
        print(f"[4/5]       Ports ready: {ready}/{EXPECTED_PORTS} ({pct}%)", flush=True)
        last_reported = ready

    if ready >= EXPECTED_PORTS:
        break
    time.sleep(2)

# Final port detection and persist to .env
final_ports = get_all_dynamic_ports()
if len(final_ports) < EXPECTED_PORTS:
    output_error("start_failed",
                 "Service start timeout - could not detect all ports",
                 f"Detected ports: {final_ports}")

# Correct env var mapping:
#   FRONTEND_PORT = frontend HTTP port (5173) — read by app_web.py
#   WEB_PORT      = WebChannel ws port (19000) — read by Gateway & app_web.py proxy target
#   GATEWAY_PORT  = Gateway ws port (19001)    — read by Gateway
#   AGENT_PORT    = AgentServer ws port (18092)
update_env_file("FRONTEND_PORT", str(final_ports['frontend']))
update_env_file("WEB_PORT", str(final_ports['web']))
update_env_file("GATEWAY_PORT", str(final_ports['gateway']))
update_env_file("AGENT_PORT", str(final_ports['agent_server']))

print("[4/5] ✅ Service started successfully", flush=True)