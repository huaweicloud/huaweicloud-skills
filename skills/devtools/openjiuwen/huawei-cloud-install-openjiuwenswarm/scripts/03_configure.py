#!/usr/bin/env python3
"""Phase 3: Configure runtime (fix shebang, install global commands, init workspace, config .env).
Run as: python3 scripts/03_configure.py"""
import os
import sys
import subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

ensure_keyutils()

print("[3/5] \U0001f527 Configuring runtime environment...", flush=True)
# Fix shebang — replace any wrong python shebang with the correct RUNTIME_PYTHON path
scripts = [RUNTIME_INIT, RUNTIME_START]
correct_shebang = f"#!{RUNTIME_PYTHON}"
for script in scripts:
    if os.path.isfile(script):
        with open(script, 'r') as f:
            content = f.read()
        lines = content.splitlines()
        if lines and lines[0].startswith("#!") and "python" in lines[0] and lines[0] != correct_shebang:
            lines[0] = correct_shebang
            content = "\n".join(lines) + ("\n" if content.endswith("\n") else "")
            with open(script, 'w') as f:
                f.write(content)
            os.chmod(script, 0o755)

# Install global commands
sudo = "sudo" if os.getuid() != 0 else ""
bin_dir = "/usr/local/bin"
commands = {
    "jiuwenswarm-start": RUNTIME_START,
    "jiuwenswarm-init": RUNTIME_INIT,
    "jiuwenswarm-cli": os.path.join(EXTRACT_DIR, "python", "bin", "jiuwenswarm")
}
for cmd_name, cmd_path in commands.items():
    link_path = os.path.join(bin_dir, cmd_name)
    if os.path.islink(link_path) or os.path.isfile(link_path):
        subprocess.run(f"{sudo} rm -f {link_path}", shell=True, capture_output=True)
    if os.path.isfile(cmd_path):
        subprocess.run(f"{sudo} ln -sf {cmd_path} {link_path}", shell=True, capture_output=True)
        subprocess.run(f"{sudo} chmod +x {link_path}", shell=True, capture_output=True)

# Init workspace
if not os.path.isfile(RUNTIME_INIT):
    output_error("init_not_found",
                 f"Init script not found: {RUNTIME_INIT}",
                 "Check mirror archive structure")
if not os.path.isfile(ENV_FILE):
    os.makedirs(os.path.dirname(ENV_FILE), exist_ok=True)
    subprocess.run(RUNTIME_INIT, capture_output=True)

# Config .env
config = get_keyring_config()
api_base = config.get("base_url", "")
api_key = config.get("api_key", "")
current_model_id = config.get("model_id", "")

if current_model_id:
    model_id = current_model_id
else:
    model_id = "glm-5.2"

update_env_file("API_BASE", f'"{api_base}"')
update_env_file("API_KEY", f'"{api_key}"')
update_env_file("MODEL_NAME", f'"{model_id}"')
update_env_file("MODEL_PROVIDER", "DeepSeek")

print("[3/5] \u2705 Runtime environment configured", flush=True)