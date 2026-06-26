from __future__ import annotations

from pathlib import Path

import yaml


_REQUIRED_SECTIONS = [
    "platform", "capture", "rejection", "report", "extraction",
    "delivery", "storage", "sanitizer", "logging", "performance",
]


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if config is None:
        raise ValueError("配置文件为空或格式错误")

    _validate_required_sections(config)
    _auto_correct_thresholds(config)

    return config


def _validate_required_sections(config: dict) -> None:
    missing = [s for s in _REQUIRED_SECTIONS if s not in config]
    if missing:
        raise ValueError(f"配置文件缺少必需段落: {', '.join(missing)}")


def _auto_correct_thresholds(config: dict) -> None:
    min_confidence = config.get("rejection", {}).get("min_confidence")
    if min_confidence is not None and (min_confidence < 0 or min_confidence > 1):
        config["rejection"]["min_confidence"] = 0.3