#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 API 调用模式：基于 Manager 还是 LakeWatch

判断逻辑：
  1. manager_api_config.yaml 文件不存在 → 默认基于 lakewatch
  2. 文件存在但 encrypted_password 为空 → 默认基于 lakewatch
  3. 文件存在且 encrypted_password 非空 → 基于 manager

用法：
  python check_api_mode.py          # Windows
  python3 check_api_mode.py         # Linux
"""

import os
import sys
import json

try:
    import yaml
except ImportError:
    print(json.dumps({
        "mode": "lakewatch",
        "reason": "PyYAML not installed, fallback to lakewatch"
    }, ensure_ascii=False))
    sys.exit(0)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manager_api_config.yaml")


def check_api_mode() -> dict:
    """判断 API 调用模式，返回结果字典"""
    # 文件不存在 → lakewatch
    if not os.path.exists(CONFIG_PATH):
        return {
            "mode": "lakewatch",
            "reason": "manager_api_config.yaml not found"
        }

    # 读取配置
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        return {
            "mode": "lakewatch",
            "reason": "failed to parse manager_api_config.yaml: {}".format(e)
        }

    if not config or not isinstance(config, dict):
        return {
            "mode": "lakewatch",
            "reason": "manager_api_config.yaml is empty or invalid"
        }

    # 检查 encrypted_password
    auth = config.get("auth", {})
    if not isinstance(auth, dict):
        auth = {}

    encrypted_password = auth.get("encrypted_password", "")

    if encrypted_password and encrypted_password.strip():
        return {
            "mode": "manager",
            "reason": "manager_api_config.yaml exists and encrypted_password is set"
        }
    else:
        return {
            "mode": "lakewatch",
            "reason": "manager_api_config.yaml exists but encrypted_password is empty"
        }


if __name__ == "__main__":
    result = check_api_mode()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0)
