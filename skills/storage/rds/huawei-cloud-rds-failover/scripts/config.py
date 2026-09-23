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


import subprocess


def run_hcloud(service, action, region, extra_args=None):
    """执行 hcloud CLI 命令并返回解析后的 JSON 结果。

    三阶段脚本（prepare/execute/risk）共用此函数，避免重复实现导致的维护漂移。
    """
    cmd = ["hcloud", service, action, f"--cli-region={region}"]
    if extra_args:
        cmd.extend(extra_args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return {"_error": True, "stderr": "hcloud 命令超时（120s），请检查网络或减少查询范围"}
    except FileNotFoundError:
        return {"_error": True, "stderr": "hcloud 未安装或不在 PATH 中，请参考 cli-installation-guide.md 安装"}
    if result.returncode != 0:
        return {"_error": True, "stderr": result.stderr.strip()}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"_error": True, "stderr": "Non-JSON output", "stdout": result.stdout.strip()}


def load_json(filepath):
    """从 JSON 文件加载数据。"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filepath, data):
    """将数据保存为 JSON 文件（UTF-8、缩进 2 空格）。"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
