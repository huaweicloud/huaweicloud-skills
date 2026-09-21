"""
共享配置加载模块 — 从 config/config.json 读取 region 和 instance_id。
"""

import json
import os

# scripts/ -> huawei-cloud-rds-failover/config/config.json
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SHARED_CONFIG_PATH = os.path.join(_SCRIPT_DIR, "..", "config", "config.json")


def load_config(config_path=None):
    """
    从 config.json 读取 region 和 instance_id。

    Args:
        config_path: 自定义配置文件路径（可选，默认使用共享 config/config.json）

    Returns:
        dict: {"region": "...", "instance_id": "..."}
    """
    path = config_path or _SHARED_CONFIG_PATH
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"配置文件不存在: {path}\n"
            f"请确保 config/config.json 已创建，包含 region 和 instance_id 字段。"
        )
    with open(path, "r", encoding="utf-8") as f:
        try:
            cfg = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"config.json 格式错误: {path}\n"
                f"JSON 解析失败（行 {e.lineno}，列 {e.colno}）: {e.msg}\n"
                f"请检查 JSON 语法：键名和字符串需双引号，最后一个元素后不加逗号。"
            ) from e

    if not isinstance(cfg, dict):
        raise ValueError(
            f"config.json 顶层必须是 JSON 对象，当前类型为 {type(cfg).__name__}（{path}）"
        )

    region = cfg.get("region")
    if not isinstance(region, str) or not region.strip():
        raise ValueError("config.json 中 region 必须为非空字符串")
    instance_id = cfg.get("instance_id")
    if not isinstance(instance_id, str) or not instance_id.strip():
        raise ValueError("config.json 中 instance_id 必须为非空字符串")

    return {"region": region.strip(), "instance_id": instance_id.strip()}


def get_config_path():
    """返回共享配置文件的绝对路径。"""
    return os.path.abspath(_SHARED_CONFIG_PATH)
