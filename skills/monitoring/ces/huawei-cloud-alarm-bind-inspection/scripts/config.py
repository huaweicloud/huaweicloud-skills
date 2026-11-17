#!/usr/bin/env python3
"""
CES client configuration.
Loads AK/SK from environment variables and builds a CES SDK client.
Project ID is auto-fetched via hcloud CLI based on the target region.
"""

import json
import logging
import os
import socket
import subprocess
import urllib.request
from dotenv import load_dotenv

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.http.http_config import HttpConfig
from huaweicloudsdkces.v2 import CesClient
from huaweicloudsdkces.v2.region.ces_region import CesRegion

logger = logging.getLogger(__name__)

# Load .env from skill root
scriptPath = os.path.dirname(__file__)
skillPath = os.path.dirname(scriptPath)
load_dotenv(os.path.join(skillPath, ".env"))

# Workspace paths
projectPath = "."
projectTmpPath = "./tmp"

# Huawei Cloud VPC internal IP prefix — these addresses are not routable from
# public internet / sandbox environments.
_INTERNAL_IP_PREFIX = "100.125."

# DNS-over-HTTPS endpoints (tried in order; first success wins).
_DOH_ENDPOINTS = [
    "https://doh.pub/dns-query",   # Tencent Public DNS (mainland China reachable)
    "https://dns.google/resolve",  # Google Public DNS
]


def ensure_public_endpoint(region: str) -> bool:
    """
    Ensure the CES endpoint for *region* resolves to a public IP.

    In some environments (e.g. sandbox, non-VPC), the system DNS resolves
    ``ces.<region>.myhuaweicloud.com`` to a Huawei Cloud **internal** IP
    (100.125.x.x) that is not routable, causing connection timeouts.

    This function detects that situation, queries a public DNS-over-HTTPS
    resolver for the real public IP, and writes a mapping to ``/etc/hosts``
    so subsequent connections (both CES SDK and hcloud CLI) use the public IP.

    The function is **idempotent**: if ``/etc/hosts`` already contains an entry
    for the hostname, or the DNS already returns a public IP, it is a no-op.

    Args:
        region: Huawei Cloud region ID (e.g. ``cn-north-4``).

    Returns:
        True if the endpoint is (or has been made) reachable via a public IP.
        False if the internal IP could not be corrected (DoH failure, no write
        permission, etc.).  False does **not** block the caller — the original
        timeout behaviour serves as a fallback.
    """
    if not region:
        return True  # nothing to check

    hostname = f"ces.{region}.myhuaweicloud.com"

    # 1. Check /etc/hosts for an existing override (idempotent).
    try:
        with open("/etc/hosts", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == hostname:
                    logger.info("ensure_public_endpoint: /etc/hosts already has %s -> %s, skip",
                                hostname, parts[0])
                    return True
    except OSError:
        pass  # cannot read /etc/hosts, proceed to DNS check

    # 2. Resolve via system DNS.
    try:
        addrs = socket.getaddrinfo(hostname, 443, socket.AF_INET, socket.SOCK_STREAM)
        current_ips = list({ai[4][0] for ai in addrs})
    except socket.gaierror:
        current_ips = []

    if not current_ips:
        logger.warning("ensure_public_endpoint: DNS resolution failed for %s", hostname)
        # Could be a DNS failure rather than internal-IP; still try DoH.
        current_ips = [_INTERNAL_IP_PREFIX + "0.0"]  # force DoH path

    # 3. If all resolved IPs are public, nothing to do.
    all_public = all(not ip.startswith(_INTERNAL_IP_PREFIX) for ip in current_ips)
    if all_public and current_ips:
        return True

    # 4. At least one IP is internal — query DoH for the public IP.
    logger.warning(
        "ensure_public_endpoint: %s resolved to internal IP %s, "
        "querying public DNS for a routable address",
        hostname, current_ips,
    )

    public_ip = _doh_resolve(hostname)
    if not public_ip:
        logger.warning(
            "ensure_public_endpoint: DoH query also failed for %s, "
            "cannot correct DNS; original timeout will apply",
            hostname,
        )
        return False

    # 5. Write to /etc/hosts.
    try:
        with open("/etc/hosts", "a") as f:
            f.write(f"\n{public_ip}  {hostname}\n")
        logger.info(
            "ensure_public_endpoint: wrote /etc/hosts entry %s -> %s",
            hostname, public_ip,
        )
        return True
    except OSError as e:
        logger.warning("ensure_public_endpoint: cannot write /etc/hosts: %s", e)
        return False


def _doh_resolve(hostname: str) -> str | None:
    """
    Resolve *hostname* to an IPv4 address via DNS-over-HTTPS.

    Tries each endpoint in ``_DOH_ENDPOINTS`` in order and returns the first
    A-record obtained.  Returns ``None`` if all resolvers fail.
    """
    for doh_url in _DOH_ENDPOINTS:
        try:
            sep = "&" if "?" in doh_url else "?"
            url = f"{doh_url}{sep}name={hostname}&type=A"
            req = urllib.request.Request(url, headers={"Accept": "application/dns-json"})
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            for answer in data.get("Answer", []):
                if answer.get("type") == 1:  # A record
                    return answer["data"]
        except Exception as e:
            logger.debug("DoH %s failed: %s", doh_url, e)
            continue
    return None


def fetch_project_id(region: str) -> str:
    """
    Auto-fetch the project ID for a given region via hcloud CLI.

    Calls `hcloud IAM KeystoneListProjects --cli-region=<region>` and finds
    the project whose name matches the region ID.

    Args:
        region: Huawei Cloud region ID (e.g. cn-south-1).

    Returns:
        Project ID string, or empty string on failure.
    """
    try:
        result = subprocess.run(
            ["hcloud", "IAM", "KeystoneListProjects", f"--cli-region={region}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.warning("hcloud KeystoneListProjects failed: %s", result.stderr.strip())
            return ""

        data = json.loads(result.stdout)
        for project in data.get("projects", []):
            if project.get("name") == region:
                pid = project.get("id", "")
                logger.info("Auto-fetched project_id for %s: %s", region, pid)
                return pid

        logger.warning("No project found with name=%s in KeystoneListProjects result", region)
        return ""

    except FileNotFoundError:
        logger.warning("hcloud CLI not found; cannot auto-fetch project_id")
        return ""
    except Exception as e:
        logger.warning("fetch_project_id error: %s", e)
        return ""


def load_credentials():
    """Load Huawei Cloud credentials from environment variables."""
    ak = os.getenv("HW_ACCESS_KEY", "")
    sk = os.getenv("HW_SECRET_KEY", "")
    region = os.getenv("HW_REGION_NAME", "cn-south-1")
    project_id = os.getenv("HW_PROJECT_ID", "")
    security_token = os.getenv("HW_SECURITY_TOKEN", "")

    if not ak or not sk:
        raise ValueError(
            "HW_ACCESS_KEY and HW_SECRET_KEY must be set in environment or .env file. "
            "Please configure them in the skill's .env file."
        )

    return ak, sk, region, project_id, security_token


def build_ces_client(region: str = None) -> CesClient:
    """
    Build a CES SDK client with AK/SK authentication.

    Project ID is auto-fetched via hcloud CLI if not provided in HW_PROJECT_ID.
    Before building the client, :func:`ensure_public_endpoint` is called to
    correct any DNS resolution that returns a Huawei Cloud internal IP
    (100.125.x.x) for the CES endpoint.

    Args:
        region: Huawei Cloud region ID (e.g., cn-south-1).
                If None, reads from HW_REGION_NAME env var (default cn-south-1).

    Returns:
        CesClient instance ready for API calls.
    """
    ak, sk, default_region, project_id, security_token = load_credentials()
    if region is None:
        region = default_region

    # Ensure the CES endpoint resolves to a public IP (fix 100.125.x.x internal
    # DNS resolution that causes connection timeouts in non-VPC environments).
    ensure_public_endpoint(region)

    # Auto-fetch project_id if not explicitly set
    if not project_id:
        project_id = fetch_project_id(region)

    credentials = BasicCredentials(ak, sk)
    if project_id:
        credentials.with_project_id(project_id)
    if security_token:
        credentials.with_security_token(security_token)

    http_config = HttpConfig.get_default_config()
    http_config.ignore_ssl_verification = True  # cn-north-4 CES public IP uses self-signed cert

    client = (
        CesClient.new_builder()
        .with_http_config(http_config)
        .with_credentials(credentials)
        .with_region(CesRegion.value_of(region))
        .build()
    )

    if not client:
        raise RuntimeError(f"Failed to build CES client for region {region}")

    return client
