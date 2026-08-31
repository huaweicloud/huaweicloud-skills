#!/usr/bin/env python3
from __future__ import annotations

"""
Huawei Cloud COC (Cloud Operations Center) Deployment Module for DeepSeek Harness (dsh)
Supports script creation, execution, and status query on Huawei Cloud ECS instances.

This module provides COC-based deployment capability for DeepSeek Harness (dsh),
replacing the traditional SSH deployment method. The combined install script
bundles: Node.js 22 + @deepseek-ai/dsh + systemd service + Nginx reverse proxy
+ firewall configuration in a single COC script execution.
"""

import json
import time
import uuid
import requests
import logging
from typing import Any, Optional, List, Dict
from urllib.parse import urlparse

from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkcoc.v1.region.coc_region import CocRegion
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkcoc.v1 import *
from huaweicloudsdkcoc.v1.model.script_execute_model import ScriptExecuteModel
from huaweicloudsdkcoc.v1.model.script_execute_param import ScriptExecuteParam
from huaweicloudsdkcoc.v1.model.execute_instances_batch_info import ExecuteInstancesBatchInfo
from huaweicloudsdkcoc.v1.model.execute_resource_instance import ExecuteResourceInstance
from huaweicloudsdkcoc.v1.model.script_properties_model import ScriptPropertiesModel
from huaweicloudsdkcoc.v1.model.add_script_model import AddScriptModel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

VALID_SCRIPT_TYPES = ["SHELL", "PYTHON", "BAT"]
VALID_RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"]
VALID_ROTATION_STRATEGIES = ["CONTINUE", "STOP"]

COC_API_ENDPOINT = "https://coc.myhuaweicloud.com/v1/resources"
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2

# DeepSeek Harness (dsh) defaults — must stay in sync with config.py
DSH_DEFAULT_PORT = 3080

COMBINED_INSTALL_SCRIPT = r'''#!/bin/bash
set -e

LOG="/var/log/dsh-bootstrap.log"
exec > >(tee -a "$LOG") 2>&1
echo "[$(date)] Combined Bootstrap: start"

DSH_PORT="%%DSH_PORT%%"
API_KEY="%%API_KEY%%"

# ===== Stage 0: Configure Domestic Mirrors (China Acceleration) =====
echo "[$(date)] ===== Configuring Domestic Mirrors ====="

# Configure Ubuntu APT mirror (USTC - fast in mainland China)
echo "[$(date)] Configuring APT mirror to USTC (mirrors.ustc.edu.cn)..."
if [ -f /etc/apt/sources.list.d/ubuntu.sources ]; then
    # Ubuntu 24.04+ uses DEB822 format
    sed -i 's|http://archive.ubuntu.com|https://mirrors.ustc.edu.cn|g' /etc/apt/sources.list.d/ubuntu.sources
    sed -i 's|http://security.ubuntu.com|https://mirrors.ustc.edu.cn|g' /etc/apt/sources.list.d/ubuntu.sources
else
    # Fallback for older format
    sed -i 's|http://archive.ubuntu.com|https://mirrors.ustc.edu.cn|g' /etc/apt/sources.list
    sed -i 's|http://security.ubuntu.com|https://mirrors.ustc.edu.cn|g' /etc/apt/sources.list
fi

# Set npm registry to npmmirror (fast in China)
npm_registry="https://registry.npmmirror.com"

export DEBIAN_FRONTEND=noninteractive
echo "[$(date)] Updating APT package lists..."
apt-get update -y
apt-get install -y curl wget tar xz-utils git ca-certificates gnupg ufw

# ===== Stage 1: Install Node.js 22 LTS =====
echo "[$(date)] ===== Installing Node.js 22 LTS ====="

install_node_from_tarball() {
    local arch
    case "$(uname -m)" in
        x86_64|amd64) arch="x64" ;;
        aarch64|arm64) arch="arm64" ;;
        *) echo "[$(date)] Unsupported architecture: $(uname -m)"; return 1 ;;
    esac

    # Prefer npmmirror dist mirror (fast in China), fall back to nodejs.org
    local ver dist_url
    ver="$(curl -fsS --max-time 15 https://registry.npmmirror.com/-/binary/node/latest-v22.x/index.json \
        | grep -o '"version":"v22\.[0-9]*\.[0-9]*"' | head -1 | cut -d'"' -f4)"
    if [ -z "$ver" ]; then
        ver="$(curl -fsS --max-time 15 https://nodejs.org/dist/index.json \
            | grep -o '"version":"v22\.[0-9]*\.[0-9]*"' | head -1 | cut -d'"' -f4)"
    fi
    [ -n "$ver" ] || { echo "[$(date)] Failed to resolve latest Node 22 version"; return 1; }
    echo "[$(date)] Resolved Node.js $ver ($arch)"

    local tarball="node-$ver-linux-$arch.tar.xz"
    local tmp
    tmp="$(mktemp -d)"
    if ! curl -fsSL --max-time 300 -o "$tmp/$tarball" "https://registry.npmmirror.com/-/binary/node/$ver/$tarball"; then
        curl -fsSL --max-time 300 -o "$tmp/$tarball" "https://nodejs.org/dist/$ver/$tarball" || { echo "[$(date)] Download failed"; return 1; }
    fi
    mkdir -p /opt/nodejs
    tar -xJf "$tmp/$tarball" -C /opt/nodejs
    rm -rf "$tmp"
    ln -sfn "/opt/nodejs/node-$ver-linux-$arch" /opt/nodejs/current
    for bin in node npm npx corepack; do
        ln -sfn "/opt/nodejs/current/bin/$bin" "/usr/local/bin/$bin"
    done
    echo "[$(date)] Node.js $ver installed to /opt/nodejs/current"
}

if command -v node > /dev/null 2>&1; then
    NODE_MAJOR="$(node -v | sed 's/^v//' | cut -d. -f1)"
    if [ "$NODE_MAJOR" -ge 22 ]; then
        echo "[$(date)] Node.js $(node -v) already installed, keeping it"
    else
        echo "[$(date)] Node.js $(node -v) < 22, installing Node 22 LTS alongside"
        install_node_from_tarball
    fi
else
    install_node_from_tarball
fi

node -v || { echo "[$(date)] Node.js installation failed"; exit 1; }

# ===== Stage 2: Install DeepSeek Harness (dsh) =====
echo "[$(date)] ===== Installing @deepseek-ai/dsh ====="

# Configure npm registry (npmmirror for China acceleration)
npm config set registry "$npm_registry" --global

if command -v dsh > /dev/null 2>&1; then
    echo "[$(date)] dsh already installed: $(dsh -V 2>/dev/null || dsh --version 2>/dev/null || echo 'unknown')"
else
    echo "[$(date)] Installing @deepseek-ai/dsh globally via npm (registry: $npm_registry)..."
    npm install -g @deepseek-ai/dsh
    if ! command -v dsh > /dev/null 2>&1; then
        echo "[$(date)] dsh not found on PATH after install; trying local bin..."
        NPM_GLOBAL_BIN="$(npm prefix -g)/bin"
        ln -sfn "$NPM_GLOBAL_BIN/dsh" /usr/local/bin/dsh 2>/dev/null || true
    fi
    command -v dsh > /dev/null 2>&1 || { echo "[$(date)] dsh installation failed"; exit 1; }
    echo "[$(date)] dsh installed: $(dsh -V 2>/dev/null || dsh --version 2>/dev/null || echo 'unknown')"
fi

# ===== Stage 3: Dedicated Service User =====
echo "[$(date)] ===== Setting Up Dedicated User ====="

DSH_USER="dsh"
DSH_HOME="/home/$DSH_USER/.dsh"

if ! id "$DSH_USER" > /dev/null 2>&1; then
    useradd --system --create-home --shell /usr/sbin/nologin --comment "DeepSeek Harness" "$DSH_USER"
    echo "[$(date)] Created system user: $DSH_USER"
fi
mkdir -p "$DSH_HOME"
chown -R "$DSH_USER:$DSH_USER" "$DSH_HOME"
echo "[$(date)] DSH_HOME=$DSH_HOME"

# ===== Stage 4: systemd Service =====
echo "[$(date)] ===== Writing systemd Service ====="

DSH_BIN="$(command -v dsh)"
cat > /etc/systemd/system/dsh.service << EOF
[Unit]
Description=DeepSeek Harness (dsh) Web UI
Documentation=https://github.com/deepseek-ai/deepseek-harness
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$DSH_USER
Group=$DSH_USER
Environment=DSH_HOME=$DSH_HOME
Environment=NODE_ENV=production
WorkingDirectory=$DSH_HOME
ExecStart=$DSH_BIN web --port $DSH_PORT
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
ProtectSystem=full
ReadWritePaths=$DSH_HOME
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Inject DEEPSEEK_API_KEY as a drop-in if provided (never log it)
if [ -n "$API_KEY" ]; then
    mkdir -p /etc/systemd/system/dsh.service.d
    printf '[Service]\nEnvironment=DEEPSEEK_API_KEY=%s\n' "$API_KEY" > /etc/systemd/system/dsh.service.d/10-credentials.conf
    chmod 600 /etc/systemd/system/dsh.service.d/10-credentials.conf
    echo "[$(date)] DEEPSEEK_API_KEY pre-seeded via systemd drop-in (file mode 600)"
fi

systemctl daemon-reload
systemctl enable dsh
echo "[$(date)] systemd service 'dsh' created and enabled"

# ===== Stage 5: Nginx Reverse Proxy =====
echo "[$(date)] ===== Configuring Nginx Reverse Proxy ====="

if ! command -v nginx > /dev/null 2>&1; then
    echo "[$(date)] Installing Nginx..."
    apt-get install -y -qq nginx
fi

# Remove conflicting default site if present
if [ -f /etc/nginx/sites-enabled/default ]; then
    rm -f /etc/nginx/sites-enabled/default
    echo "[$(date)] Removed conflicting default site"
fi

cat > /etc/nginx/conf.d/dsh.conf << 'NGINXEOF'
server {
    listen 80;
    server_name _;
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:%%DSH_PORT%%;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
NGINXEOF

# Substitute the actual port into the Nginx config
sed -i "s|%%DSH_PORT%%|$DSH_PORT|g" /etc/nginx/conf.d/dsh.conf

nginx -t || { echo "[$(date)] Nginx config test failed"; cat /etc/nginx/conf.d/dsh.conf; exit 1; }
systemctl enable nginx 2>/dev/null || true
systemctl restart nginx
echo "[$(date)] Nginx reverse proxy configured: 80 -> 127.0.0.1:$DSH_PORT"

# ===== Stage 6: Firewall =====
echo "[$(date)] ===== Configuring Firewall ====="

if command -v ufw > /dev/null 2>&1; then
    ufw allow 22/tcp > /dev/null 2>&1 || true
    ufw allow 80/tcp > /dev/null 2>&1 || true
    ufw allow 443/tcp > /dev/null 2>&1 || true
    echo "[$(date)] UFW: allowed 22/80/443"
else
    echo "[$(date)] No UFW found; ensure cloud security group opens ports 22/80/443"
fi

# ===== Stage 7: Start & Verify =====
echo "[$(date)] ===== Starting dsh Service ====="

systemctl start dsh || { echo "[$(date)] dsh failed to start"; journalctl -u dsh -n 50 --no-pager; exit 1; }

# Wait for dsh to respond on 127.0.0.1:$DSH_PORT (it only binds to loopback by design)
DSH_READY=0
for i in $(seq 1 30); do
    if curl -fsS --max-time 2 -o /dev/null "http://127.0.0.1:$DSH_PORT"; then
        DSH_READY=1
        break
    fi
    sleep 1
done

echo "--- Verification ---"
DSH_STATUS="DOWN"
if [ "$DSH_READY" = "1" ]; then
    DSH_STATUS="UP"
fi
echo "dsh: $DSH_STATUS (127.0.0.1:$DSH_PORT, systemd service 'dsh')"
echo "Node.js: $(node -v)"
echo "dsh CLI: $(dsh -V 2>/dev/null || dsh --version 2>/dev/null || echo 'unknown')"
echo "Nginx: $(nginx -v 2>&1)"

if [ "$DSH_READY" != "1" ]; then
    echo "[$(date)] dsh did not respond on 127.0.0.1:$DSH_PORT"
    journalctl -u dsh -n 50 --no-pager || true
    exit 1
fi

echo "[$(date)] Combined Bootstrap: done"
echo ""
echo "====================================================="
echo " ✅ DEPLOYMENT SUCCESSFUL"
echo "====================================================="
echo ""
echo " DEEPSEEK HARNESS (dsh) ACCESS:"
echo "  Web UI (via Nginx): http://<your-ip>"
echo "  Local:              http://127.0.0.1:$DSH_PORT"
echo ""
echo " NEXT STEPS:"
echo "  1. Open the Web UI in a browser, go to Settings -> Models,"
echo "     enter your DeepSeek API key and save."
echo "  2. Choose a workspace directory, then start a session."
echo ""
echo " SECURITY:"
echo "  - dsh binds to 127.0.0.1 only; remote access goes through Nginx (port 80)."
echo "  - Add an HTTPS certificate in production (e.g. Let's Encrypt / certbot)."
echo "  - Configure Huawei Cloud security group to restrict ports 22/80 to your IP."
echo ""
echo "====================================================="
echo ""
echo "### DEPLOYMENT_INFO_START ###"
echo "DSH_PORT=$DSH_PORT"
echo "DSH_HOME=$DSH_HOME"
echo "DSH_USER=$DSH_USER"
echo "DSH_STATUS=$DSH_STATUS"
echo "NODE_VERSION=$(node -v)"
echo "DSH_VERSION=$(dsh -V 2>/dev/null || dsh --version 2>/dev/null || echo 'unknown')"
echo "### DEPLOYMENT_INFO_END ###"
'''


def _error(code: str, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "text": message,
        "result": None,
        "error": {"code": code, "message": message}
    }


def get_valid_coc_regions() -> list[str]:
    return list(CocRegion.static_fields.keys())


def get_client(ak: str, sk: str, security_token: str, region: str = None) -> CocClient:
    if not region:
        region = "cn-north-4"

    valid_regions = get_valid_coc_regions()
    if region not in valid_regions:
        raise ValueError(f"COC region must be one of {valid_regions}")

    credentials = GlobalCredentials(ak, sk)
    if security_token:
        credentials = credentials.with_security_token(security_token)

    client = CocClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(CocRegion.value_of(region)) \
        .build()

    return client


def create_script(
    name: str,
    script_type: str,
    content: str,
    description: str,
    ak: str,
    sk: str,
    security_token: str = None,
    region: str = None,
    risk_level: str = "LOW",
    version: str = "1.0.0",
    script_params: Optional[List[Dict[str, Any]]] = None,
) -> dict[str, Any]:
    if not name:
        return _error("INPUT_ERROR", "name is required")
    if len(name) > 128:
        return _error("INPUT_ERROR", "name must be 1-128 characters")
    if script_type not in VALID_SCRIPT_TYPES:
        return _error("INPUT_ERROR", f"script_type must be one of {VALID_SCRIPT_TYPES}")
    if not content:
        return _error("INPUT_ERROR", "content is required")
    if not description:
        return _error("INPUT_ERROR", "description is required")
    if len(description) > 512:
        return _error("INPUT_ERROR", "description must be 1-512 characters")
    if risk_level not in VALID_RISK_LEVELS:
        return _error("INPUT_ERROR", f"risk_level must be one of {VALID_RISK_LEVELS}")
    if not ak or not sk:
        return _error("CONFIG_ERROR", "ak and sk are required")

    try:
        client = get_client(ak, sk, security_token, region)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        logger.info(f"Creating COC script: {name}")

        request = CreateScriptRequest()

        properties = ScriptPropertiesModel(
            risk_level=risk_level,
            version=version
        )

        params_list = []
        if script_params and isinstance(script_params, list):
            for param in script_params:
                if isinstance(param, dict):
                    params_list.append(param)

        add_script_model = AddScriptModel(
            name=name,
            type=script_type,
            content=content,
            description=description,
            properties=properties
        )

        if params_list:
            add_script_model.params = params_list

        request.body = add_script_model

        response = client.create_script(request)

        script_uuid = ""
        if hasattr(response, 'data') and response.data is not None:
            script_uuid = response.data
        elif hasattr(response, 'script_uuid'):
            script_uuid = response.script_uuid
        else:
            script_uuid = str(response)

        logger.info(f"COC script created successfully: {script_uuid}")

        return {
            "ok": True,
            "text": f"Script created successfully: {script_uuid}",
            "result": {"script_uuid": script_uuid},
            "error": None,
        }

    except exceptions.ClientRequestException as e:
        return _error("API_ERROR", f"{e.error_code}: {e.error_msg}")
    except Exception as e:
        return _error("UNKNOWN_ERROR", str(e))


def execute_script(
    script_uuid: str,
    execute_user: str,
    timeout: int,
    success_rate: float,
    target_instances: List[Dict[str, str]],
    ak: str,
    sk: str,
    security_token: str = None,
    region: str = None,
    rotation_strategy: str = "CONTINUE",
    wait_for_completion: bool = False,
) -> dict[str, Any]:
    if not script_uuid:
        return _error("INPUT_ERROR", "script_uuid is required")
    if not execute_user:
        return _error("INPUT_ERROR", "execute_user is required")
    if timeout <= 5 or timeout > 1800:
        return _error("INPUT_ERROR", "timeout must be between 5 and 1800 seconds")
    if success_rate < 0 or success_rate > 100:
        return _error("INPUT_ERROR", "success_rate must be between 0 and 100")
    if not target_instances or not isinstance(target_instances, list):
        return _error("INPUT_ERROR", "target_instances is required")

    for idx, instance_info in enumerate(target_instances):
        if not instance_info.get("resource_id"):
            return _error("INPUT_ERROR", f"resource_id is required for instance {idx}")
        if not instance_info.get("region_id"):
            return _error("INPUT_ERROR", f"region_id is required for instance {idx}")

    if rotation_strategy not in VALID_ROTATION_STRATEGIES:
        return _error("INPUT_ERROR", f"rotation_strategy must be one of {VALID_ROTATION_STRATEGIES}")
    if not ak or not sk:
        return _error("CONFIG_ERROR", "ak and sk are required")

    try:
        client = get_client(ak, sk, security_token, region)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        request = ExecuteScriptRequest()
        request.script_uuid = script_uuid

        execute_param = ScriptExecuteParam(
            timeout=timeout,
            success_rate=success_rate,
            execute_user=execute_user
        )

        listTargetInstancesExecuteBatches = []
        for instance_info in target_instances:
            instance_kwargs = {
                "resource_id": instance_info.get("resource_id", ""),
                "region_id": instance_info.get("region_id", "cn-north-4")
            }

            provider = instance_info.get("provider", "HUAWEI")
            instance_type = instance_info.get("type", "ECS")
            if provider:
                instance_kwargs["provider"] = provider
            if instance_type:
                instance_kwargs["type"] = instance_type

            instance = ExecuteResourceInstance(**instance_kwargs)
            listTargetInstancesExecuteBatches.append(instance)

        listExecuteBatchesbody = [
            ExecuteInstancesBatchInfo(
                batch_index=1,
                target_instances=listTargetInstancesExecuteBatches,
                rotation_strategy=rotation_strategy
            )
        ]

        request.body = ScriptExecuteModel(
            execute_batches=listExecuteBatchesbody,
            execute_param=execute_param
        )

        logger.info("Submitting COC script execution request")
        logger.info(f"Script UUID: {script_uuid}")
        logger.info(f"Target instances: {len(target_instances)}")

        response = client.execute_script(request)

        execute_uuid = ""
        if hasattr(response, 'data') and response.data is not None:
            execute_uuid = response.data
        elif hasattr(response, 'execute_uuid'):
            execute_uuid = response.execute_uuid
        else:
            execute_uuid = str(response)

        logger.info(f"Execution ID: {execute_uuid}")

        if not wait_for_completion:
            return {
                "ok": True,
                "text": f"Script execution started: {execute_uuid}",
                "result": {"execute_uuid": execute_uuid},
                "error": None,
            }

        logger.info("Waiting for COC script execution to complete...")

        max_wait_time = timeout + 60
        wait_interval = 10
        elapsed_time = 0
        last_status = ""

        while elapsed_time < max_wait_time:
            query_result = coc_query_execution(execute_uuid, ak, sk, security_token, region)

            data = query_result.get("data", {})
            if not data:
                error_msg = query_result.get("error", {}).get("message", "query failed")
                logger.warning(f"Failed to query status: {error_msg}, retrying...")
                time.sleep(wait_interval)
                elapsed_time += wait_interval
                continue

            status = ""
            output = ""
            error = ""

            instances = data.get("execute_instances", [])
            if instances:
                status = instances[0].get("status", "")
                output = instances[0].get("message", "")
                if status == "ABNORMAL":
                    error = output
            else:
                status = data.get("status", "")
                output = data.get("message", "")
                if status == "ABNORMAL":
                    error = output

            if status != last_status:
                last_status = status
                logger.info(f"Execution status: {status}")

            if elapsed_time % 30 == 0:
                logger.info(f"Waiting... ({elapsed_time}/{max_wait_time} seconds)")

            if status in ["SUCCESS", "FAILED", "TIMEOUT", "CANCELLED", "FINISHED", "ABNORMAL"]:
                result_data = {
                    "execute_uuid": execute_uuid,
                    "status": status,
                    "output": output,
                    "error": error
                }

                if status == "FINISHED":
                    logger.info("Execution completed: SUCCESS")
                    return {
                        "ok": True,
                        "text": f"Script execution successful: {execute_uuid}",
                        "result": result_data,
                        "error": None,
                    }
                else:
                    logger.error(f"Execution completed: {status}")
                    error_msg = f"Script execution failed, status: {status}"
                    if error:
                        error_msg += f", error: {error}"
                    if output:
                        error_msg += f", output: {output}"
                    return {
                        "ok": False,
                        "text": error_msg,
                        "result": result_data,
                        "error": {"code": "EXECUTE_FAILED", "message": error_msg}
                    }

            time.sleep(wait_interval)
            elapsed_time += wait_interval

        logger.error(f"COC execution timeout (waiting exceeded {max_wait_time} seconds)")
        return {
            "ok": False,
            "text": f"Script execution timeout (waiting exceeded {max_wait_time} seconds)",
            "result": {"execute_uuid": execute_uuid},
            "error": {"code": "TIMEOUT", "message": "Script execution timeout"}
        }

    except exceptions.ClientRequestException as e:
        return _error("API_ERROR", f"{e.error_code}: {e.error_msg}")
    except Exception as e:
        return _error("UNKNOWN_ERROR", str(e))


def coc_query_execution(execute_uuid: str, ak: str = None, sk: str = None, security_token: str = None, region: str = None) -> dict[str, Any]:
    if not execute_uuid:
        return _error("INPUT_ERROR", "execute_uuid is required")
    if not ak or not sk:
        return _error("CONFIG_ERROR", "ak and sk are required")

    batch_index = 1
    limit = 50
    if not region:
        region = "cn-north-4"

    try:
        client = get_client(ak, sk, security_token, region)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        from huaweicloudsdkcoc.v1 import GetScriptJobBatchRequest

        request = GetScriptJobBatchRequest()
        request.batch_index = batch_index
        request.execute_uuid = execute_uuid
        request.limit = limit

        response = client.get_script_job_batch(request)

        result_dict = {}
        if hasattr(response, 'data') and response.data is not None:
            result_dict["data"] = {
                "batch_index": response.data.batch_index,
                "total_instances": response.data.total_instances,
                "execute_instances": []
            }
            if hasattr(response.data, 'execute_instances') and response.data.execute_instances:
                for instance in response.data.execute_instances:
                    instance_dict = {
                        "id": getattr(instance, 'id', ''),
                        "cmd_uuid": getattr(instance, 'cmd_uuid', ''),
                        "status": getattr(instance, 'status', ''),
                        "message": getattr(instance, 'message', ''),
                        "gmt_created": getattr(instance, 'gmt_created', ''),
                        "gmt_finished": getattr(instance, 'gmt_finished', ''),
                        "execute_costs": getattr(instance, 'execute_costs', 0)
                    }
                    if hasattr(instance, 'target_instance') and instance.target_instance:
                        target = instance.target_instance
                        instance_dict["target_instance"] = {
                            "resource_id": target.resource_id,
                            "region_id": target.region_id,
                            "provider": target.provider,
                            "type": target.type
                        }
                    result_dict["data"]["execute_instances"].append(instance_dict)
        else:
            result_dict["data"] = {}

        return {"ok": True, "data": result_dict.get("data", {})}

    except exceptions.ClientRequestException as e:
        return _error("API_ERROR", f"{e.error_code}: {e.error_msg}")
    except Exception as e:
        return _error("UNKNOWN_ERROR", str(e))


def check_uniagent_status(
    resource_id: str,
    ak: str,
    sk: str,
    security_token: str = None,
    provider: str = "ecs",
    resource_type: str = "cloudservers"
) -> dict[str, Any]:
    if not resource_id:
        return {"ok": False, "status": "UNKNOWN", "error": "resource_id is required"}
    if not ak or not sk:
        return {"ok": False, "status": "UNKNOWN", "error": "ak and sk are required"}

    try:
        from huaweicloudsdkcore.signer.signer import Signer
        from huaweicloudsdkcore.sdk_request import SdkRequest

        class _Credentials:
            def __init__(self, ak, sk, security_token=None):
                self.ak = ak
                self.sk = sk
                self.security_token = security_token

        credentials = _Credentials(ak, sk, security_token)
        signer = Signer(credentials)

        endpoint = COC_API_ENDPOINT

        query_params = {
            "resource_id_list": resource_id,
            "limit": "100",
            "provider": provider,
            "type": resource_type
        }

        url_with_params = endpoint + "?" + "&".join([f"{k}={v}" for k, v in query_params.items()])
        parsed_url = urlparse(url_with_params)

        request = SdkRequest()
        request.method = "GET"
        request.schema = parsed_url.scheme
        request.host = parsed_url.hostname
        request.resource_path = parsed_url.path
        request.query_params = [[k, v] for k, v in query_params.items()]
        request.header_params = {
            "Content-Type": "application/json",
            "Client-Request-Id": str(uuid.uuid4())
        }

        if security_token:
            request.header_params["X-Security-Token"] = security_token

        signed_request = signer.sign(request)

        headers = {}
        for key, value in signed_request.header_params.items():
            if isinstance(value, bytes):
                headers[key] = value.decode('iso-8859-1')
            else:
                headers[key] = str(value)

        for retry in range(MAX_RETRIES):
            try:
                resp = requests.request("GET", url_with_params, headers=headers, verify=True, timeout=DEFAULT_TIMEOUT)

                if resp.status_code == 200:
                    data = resp.json()
                    if "data" in data and data["data"]:
                        instance = data["data"][0]
                        agent_state = instance.get("agent_state", "UNKNOWN")
                        agent_id = instance.get("agent_id", "")

                        return {
                            "ok": True,
                            "status": agent_state,
                            "agent_id": agent_id,
                            "agent_state": agent_state,
                            "error": None
                        }
                    else:
                        return {"ok": False, "status": "UNKNOWN", "error": "Instance not found in COC resources"}
                else:
                    return {"ok": False, "status": "UNKNOWN", "error": f"API error: {resp.status_code}"}
            except requests.exceptions.RequestException as e:
                if retry < MAX_RETRIES - 1:
                    logger.warning(f"Request failed (attempt {retry + 1}/{MAX_RETRIES}): {e}")
                    time.sleep(RETRY_DELAY)
                else:
                    return {"ok": False, "status": "UNKNOWN", "error": f"Request failed after {MAX_RETRIES} retries: {str(e)}"}

    except Exception as e:
        return {"ok": False, "status": "UNKNOWN", "error": str(e)}


def wait_for_uniagent_online(
    resource_id: str,
    ak: str,
    sk: str,
    security_token: str = None,
    max_wait_seconds: int = 300,
    check_interval: int = 10
) -> dict[str, Any]:
    logger.info("Waiting for UniAgent to come online...")

    elapsed = 0
    while elapsed < max_wait_seconds:
        result = check_uniagent_status(resource_id, ak, sk, security_token)
        status = result.get("status", "UNKNOWN")

        if status == "ONLINE":
            logger.info(f"UniAgent is ONLINE (elapsed: {elapsed}s)")
            return {
                "ok": True,
                "status": "ONLINE",
                "elapsed_seconds": elapsed,
                "error": None
            }

        logger.info(f"UniAgent status: {status}, waiting... ({elapsed}/{max_wait_seconds}s)")
        time.sleep(check_interval)
        elapsed += check_interval

    logger.error(f"UniAgent not online after {max_wait_seconds}s")
    return {
        "ok": False,
        "status": "TIMEOUT",
        "elapsed_seconds": elapsed,
        "error": f"UniAgent not online after {max_wait_seconds} seconds"
    }


def _deploy_via_coc(
    resource_id: str,
    region_id: str,
    script_content: str,
    script_name_prefix: str,
    script_description: str,
    ak: str = None,
    sk: str = None,
    security_token: str = None,
    coc_region: str = None,
    timeout: int = 1800,
    execute_user: str = "root"
) -> dict[str, Any]:
    if not ak or not sk:
        return _error("CONFIG_ERROR", "ak and sk are required parameters")
    if not script_content:
        return _error("INPUT_ERROR", "script_content is required")

    create_result = create_script(
        name=f"{script_name_prefix}-{int(time.time())}",
        script_type="SHELL",
        content=script_content,
        description=script_description,
        ak=ak,
        sk=sk,
        security_token=security_token,
        region=coc_region,
        risk_level="MEDIUM"
    )

    if not create_result.get("ok"):
        return create_result

    script_uuid = create_result.get("result", {}).get("script_uuid")
    if not script_uuid:
        result_data = create_result.get("result")
        if hasattr(result_data, 'data'):
            script_uuid = result_data.data

    target_instances = [{
        "resource_id": resource_id,
        "region_id": region_id,
        "provider": "HUAWEI",
        "type": "ECS"
    }]

    return execute_script(
        script_uuid=script_uuid,
        execute_user=execute_user,
        timeout=timeout,
        success_rate=100.0,
        target_instances=target_instances,
        ak=ak,
        sk=sk,
        security_token=security_token,
        region=coc_region,
        rotation_strategy="CONTINUE",
        wait_for_completion=True
    )


def deploy_dsh_via_coc(
    resource_id: str,
    region_id: str,
    ak: str = None,
    sk: str = None,
    security_token: str = None,
    coc_region: str = None,
    timeout: int = 1800,
    execute_user: str = "root",
    dsh_port: int = DSH_DEFAULT_PORT,
    api_key: str = None
) -> dict[str, Any]:
    """
    Deploy DeepSeek Harness (dsh) on a remote ECS instance via COC

    This is the recommended deployment method for Huawei Cloud Flexus X instances.
    It provides:
    - One-click unified deployment (single COC API call)
    - Domestic mirror acceleration (USTC APT mirror + npmmirror npm registry)
    - systemd service + Nginx reverse proxy (dsh binds to 127.0.0.1 only)

    Parameters:
        resource_id: ECS Instance resource ID
        region_id: ECS Instance region
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials
        coc_region: COC region (optional, default cn-north-4)
        timeout: Execution timeout in seconds, default 1800 (30 minutes)
        execute_user: Execute user, default root
        dsh_port: dsh listening port, default 3080 (must match security group rules)
        api_key: DEEPSEEK_API_KEY to pre-seed into the dsh service (optional)

    Returns:
        Deployment result dictionary
    """
    script_content = COMBINED_INSTALL_SCRIPT

    # Substitute dsh port
    script_content = script_content.replace("%%DSH_PORT%%", str(dsh_port))

    # API key is optional. Never log it. If not provided, clear the placeholder
    # so the script skips pre-seeding credentials.
    if api_key:
        script_content = script_content.replace("%%API_KEY%%", api_key)
    else:
        script_content = script_content.replace("%%API_KEY%%", "")

    return _deploy_via_coc(
        resource_id=resource_id,
        region_id=region_id,
        script_content=script_content,
        script_name_prefix="DSH-Install",
        script_description=f"DeepSeek Harness (dsh) unified installation (port {dsh_port}, Nginx reverse proxy)",
        ak=ak,
        sk=sk,
        security_token=security_token,
        coc_region=coc_region,
        timeout=timeout,
        execute_user=execute_user
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="COC Deployment Test (DeepSeek Harness / dsh)")
    parser.add_argument("--ak", required=True, help="Huawei Cloud AK")
    parser.add_argument("--sk", required=True, help="Huawei Cloud SK")
    parser.add_argument("--security-token", help="Security Token")
    parser.add_argument("--resource-id", required=True, help="ECS Instance ID")
    parser.add_argument("--region-id", default="cn-north-4", help="ECS Region")
    parser.add_argument("--coc-region", default="cn-north-4", help="COC Region")
    parser.add_argument("--port", type=int, default=DSH_DEFAULT_PORT, help="dsh listening port")
    parser.add_argument("--api-key", help="DEEPSEEK_API_KEY to pre-seed")

    args = parser.parse_args()

    logger.info("Testing COC deployment (DeepSeek Harness / dsh)...")
    result = deploy_dsh_via_coc(
        resource_id=args.resource_id,
        region_id=args.region_id,
        ak=args.ak,
        sk=args.sk,
        security_token=args.security_token,
        coc_region=args.coc_region,
        dsh_port=args.port,
        api_key=args.api_key
    )

    logger.info("Deployment Result:")
    logger.info(json.dumps(result, indent=2, ensure_ascii=False))
