#!/usr/bin/env python3
"""
Huawei Cloud AK/SK 认证配置。
从环境变量加载 HW_ACCESS_KEY / HW_SECRET_KEY / HW_REGION_NAME，
提供 fetch_project_id(region) 通过 hcloud CLI 自动获取 project_id。
"""

import json
import logging
import os
import subprocess
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 路径变量（供其他脚本使用）
scriptPath = os.path.dirname(os.path.abspath(__file__))
skillPath = os.path.dirname(scriptPath)
projectPath = os.path.abspath(os.path.join(skillPath, '..', '..', '..'))

# 从 skill 根目录加载 .env（仅本地开发便利，.env 已加入 .gitignore 不提交）
load_dotenv(os.path.join(skillPath, ".env"))


def fetch_project_id(region: str) -> str:
    """
    通过 hcloud CLI 自动获取指定区域的 project_id。

    调用 `hcloud IAM KeystoneListProjects --cli-region=<region>`，
    找到 name 与 region ID 匹配的 project，返回其 id。

    Args:
        region: 华为云区域 ID（如 cn-south-1）

    Returns:
        project_id 字符串，失败时返回空字符串。
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
    """从环境变量加载华为云认证信息。"""
    ak = os.getenv("HW_ACCESS_KEY", "")
    sk = os.getenv("HW_SECRET_KEY", "")
    region = os.getenv("HW_REGION_NAME", "cn-south-1")
    project_id = os.getenv("HW_PROJECT_ID", "")
    security_token = os.getenv("HW_SECURITY_TOKEN", "")

    if not ak or not sk:
        raise ValueError(
            "HW_ACCESS_KEY and HW_SECRET_KEY must be set via environment variables. "
            "Set them with: export HW_ACCESS_KEY=xxx HW_SECRET_KEY=xxx (or optionally in .env which is gitignored)."
        )

    return ak, sk, region, project_id, security_token


def get_region() -> str:
    """获取默认区域（从环境变量读取，默认 cn-south-1）。"""
    return os.getenv("HW_REGION_NAME", "cn-south-1")


def get_project_id(region: str = None) -> str:
    """
    获取指定区域的 project_id。
    优先使用环境变量 HW_PROJECT_ID，否则自动获取。

    Args:
        region: 区域 ID，None 时使用默认区域。

    Returns:
        project_id 字符串。
    """
    if region is None:
        region = get_region()

    project_id = os.getenv("HW_PROJECT_ID", "")
    if project_id:
        return project_id

    return fetch_project_id(region)
