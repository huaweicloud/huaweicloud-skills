#!/usr/bin/env python3
"""
CES client configuration.
Loads AK/SK from environment variables and builds a CES SDK client.
Project ID is auto-fetched via hcloud CLI based on the target region.
"""

import json
import logging
import os
import subprocess
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

    Args:
        region: Huawei Cloud region ID (e.g., cn-south-1).
                If None, reads from HW_REGION_NAME env var (default cn-south-1).

    Returns:
        CesClient instance ready for API calls.
    """
    ak, sk, default_region, project_id, security_token = load_credentials()
    if region is None:
        region = default_region

    # Auto-fetch project_id if not explicitly set
    if not project_id:
        project_id = fetch_project_id(region)

    credentials = BasicCredentials(ak, sk)
    if project_id:
        credentials.with_project_id(project_id)
    if security_token:
        credentials.with_security_token(security_token)

    http_config = HttpConfig.get_default_config()
    http_config.ignore_ssl_verification = False

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
