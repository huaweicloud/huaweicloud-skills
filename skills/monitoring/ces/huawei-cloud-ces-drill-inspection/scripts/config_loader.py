#!/usr/bin/env python3
"""Config loading and validation.

Supports two config formats:
  1. Simple config (recommended): contains drill_name / phases / inspect_phase / targets,
     remaining fields are auto-inferred by expand_simple_config().
  2. Full config: contains timeline / regions / services / steady_state_rules / runtime.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Default metrics file path (relative to skill root)
METRICS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "references", "metrics.json")

# ── Built-in default tables (for simple config expansion) ──────────────

# Expected status defaults for 19 services
EXPECTED_STATUS_DEFAULTS: dict[str, str | None] = {
    "ecs": "ACTIVE", "rds": "ACTIVE", "redis": "RUNNING",
    "elb": "ACTIVE", "eip": "ACTIVE", "nat": "ACTIVE",
    "vpcep": "accepted", "evs": "available", "cce": "Available",
    "css": "green", "dds": "normal", "dws": "Available",
    "dc": "ACTIVE", "er": "available", "efsturbo": "200",
    "apig": None, "taurusdb": "normal", "geminidb": "normal",
    "dms": "RUNNING",
}

# Service name → metrics.json key mapping
SERVICE_METRIC_KEY_MAP: dict[str, str] = {
    "ecs": "ecs", "rds": "rds", "redis": "dcs",
    "elb": "elb", "eip": "eip", "nat": "nat", "vpcep": "vpcep",
    "evs": "evs", "cce": "cce", "css": "css", "dds": "dds",
    "dws": "dws", "dc": "dc", "er": "er", "efsturbo": "efsturbo",
    "apig": "apig", "taurusdb": "taurusdb", "geminidb": "geminidb", "dms": "dms",
}

# Runtime defaults
RUNTIME_DEFAULTS: dict[str, Any] = {
    "timezone_offset": 8,
    "ces_period": 60,
    "max_workers": 10,
    "metric_max_workers": 8,
    "hcloud_cmd": "hcloud",
    "hcloud_timeout": 60,
    "service_metric_key_map": SERVICE_METRIC_KEY_MAP,
}

# Required runtime fields
RUNTIME_REQUIRED = [
    "timezone_offset", "ces_period", "max_workers", "metric_max_workers",
    "hcloud_cmd", "hcloud_timeout", "service_metric_key_map",
]

# All known service names
ALL_SERVICES = list(EXPECTED_STATUS_DEFAULTS.keys())


def expand_simple_config(simple: dict[str, Any]) -> dict[str, Any]:
    """Expand simple config into full config.

    Simple config format:
      {
        "drill_name": "...",
        "phases": [
          {"key": "baseline", "name": "Pre-fault Baseline", "start": "...", "end": "..."},
          {"key": "fault",    "name": "During Fault",      "start": "...", "end": "..."},
          {"key": "recovery", "name": "Post-recovery",     "start": "...", "end": "..."}
        ],
        "inspect_phase": "recovery",
        "targets": [
          {"service": "ecs", "region": "your-region",
           "instance_ids": ["..."], "metrics": ["ECS CPU使用率"]}
        ]
      }

    Inference rules:
      - drill_start = earliest phase start
      - drill_end   = inspect_phase start
      - timeline.phases = phases list converted to {name: {start, end}} dict
      - regions / services / steady_state_rules inferred from targets
      - runtime uses all built-in defaults
    """
    phases_input = simple.get("phases", [])
    inspect_phase_key = simple.get("inspect_phase", "")
    targets = simple.get("targets", [])

    # --- Input validation (issue #935 Problem 2) ---
    # Validate service names against ALL_SERVICES
    invalid_services = sorted(set(t["service"] for t in targets) - set(ALL_SERVICES))
    if invalid_services:
        raise ValueError(
            f"配置中包含不支持的服务名: {invalid_services}。"
            f"合法服务: {sorted(ALL_SERVICES)}"
        )
    # Validate DMS engine: dms targets must specify engine
    dms_targets = [t for t in targets if t["service"] == "dms"]
    for t in dms_targets:
        if "engine" not in t:
            raise ValueError(
                f"DMS 目标缺少 engine 参数 (instance_ids={t.get('instance_ids', [])})。"
                f"DMS 需要指定 engine (kafka/rabbitmq/rocketmq) 以选择正确的 API"
            )

    # 1. Build timeline from phases list
    #    phases list → {name: {start, end, ...}} dict
    phases_dict: dict[str, dict[str, Any]] = {}
    phase_key_to_name: dict[str, str] = {}
    all_starts = []
    for ph in phases_input:
        name = ph["name"]
        start = ph["start"]
        end = ph["end"]
        all_starts.append(start)
        phase_cfg: dict[str, Any] = {"start": start, "end": end}
        if "duration_minutes" in ph:
            phase_cfg["duration_minutes"] = ph["duration_minutes"]
        phases_dict[name] = phase_cfg
        phase_key_to_name[ph["key"]] = name

    # inspect_phase: key → name
    inspect_phase_name = phase_key_to_name.get(inspect_phase_key, "")
    if not inspect_phase_name:
        raise ValueError(f"inspect_phase '{inspect_phase_key}' not found in phases")

    # drill_start = earliest phase start
    drill_start = min(all_starts)
    # drill_end = inspect_phase start
    drill_end = phases_dict[inspect_phase_name]["start"]

    timeline = {
        "drill_start": drill_start,
        "drill_end": drill_end,
        "phases": phases_dict,
        "inspect_phase": inspect_phase_name,
    }

    # 2. Extract regions and services from targets
    regions = sorted(set(t["region"] for t in targets))

    services: dict[str, Any] = {}
    steady_state_rules: dict[str, Any] = {}
    target_metrics: dict[str, list[str]] = {}
    target_instance_ids: dict[str, list[str]] = {}
    target_engines: dict[str, str] = {}

    for t in targets:
        svc = t["service"]
        if svc not in target_instance_ids:
            target_instance_ids[svc] = []
            target_metrics[svc] = []
        target_instance_ids[svc].extend(t.get("instance_ids", []))
        target_metrics[svc].extend(t.get("metrics", []))
        if "engine" in t:
            target_engines[svc] = t["engine"]

    for svc in ALL_SERVICES:
        is_target = svc in target_instance_ids
        services[svc] = {"enabled": is_target, "instance_ids": target_instance_ids.get(svc, [])}
        if svc in target_engines:
            services[svc]["engine"] = target_engines[svc]
        if svc == "ecs":
            services[svc]["name_filter"] = []

        rule: dict[str, Any] = {"expected_status": EXPECTED_STATUS_DEFAULTS[svc]}
        if svc == "rds":
            rule["expected_primary_role"] = "master"
        rule["metrics"] = target_metrics.get(svc, [])
        steady_state_rules[svc] = rule

    # 3. Runtime uses all defaults
    runtime = dict(RUNTIME_DEFAULTS)

    return {
        "drill_name": simple.get("drill_name", "Fault Drill Inspection"),
        "timeline": timeline,
        "regions": regions,
        "services": services,
        "steady_state_rules": steady_state_rules,
        "runtime": runtime,
    }


def load_config(config_path: str) -> dict[str, Any]:
    """Load inspection config JSON.

    Auto-detects config format:
      - Contains "targets" → simple config, expanded via expand_simple_config()
      - Otherwise → full config, used directly

    config_path is required.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Simple config → expand to full config
    if "targets" in config:
        config = expand_simple_config(config)
        logger.info("Simple config expanded to full config")

    # Merge runtime defaults
    config["runtime"] = {**RUNTIME_DEFAULTS, **config.get("runtime", {})}
    _validate_runtime(config["runtime"])
    validate_config(config)
    logger.info("Config loaded from %s", config_path)
    return config


def load_metrics() -> dict[str, Any]:
    """Load built-in metrics.json metric mapping table."""
    if not os.path.exists(METRICS_PATH):
        raise FileNotFoundError(f"metrics.json not found: {METRICS_PATH}")
    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_runtime(config: dict[str, Any]) -> dict[str, Any]:
    """Get runtime config section, ensuring all fields are present."""
    rt = {**RUNTIME_DEFAULTS, **config.get("runtime", {})}
    _validate_runtime(rt)
    return rt


def resolve_time(value: str, timezone_offset: int = 8) -> datetime:
    """Parse a time config value into datetime.

    "auto" or empty → current time
    "2026-10-14 10:30:00" → corresponding time
    """
    tz = timezone(timedelta(hours=timezone_offset))
    if value == "auto" or not value:
        return datetime.now(tz)
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)


def resolve_inspection_window(config: dict[str, Any]) -> tuple[str, str, int]:
    """Resolve inspection time window from timeline config.

    Returns (start_str, end_str, duration_minutes)
    """
    rt = get_runtime(config)
    tz_offset = rt["timezone_offset"]
    timeline = config.get("timeline", {})

    # Fallback: if no timeline, fall back to observation_window
    if not timeline:
        window = config.get("observation_window", {})
        duration = window.get("duration_minutes", 30)
        end_time = window.get("end_time", "auto")
        end_dt = resolve_time(end_time, tz_offset)
        start_dt = end_dt - timedelta(minutes=duration)
        return start_dt.strftime("%Y-%m-%d %H:%M:%S"), end_dt.strftime("%Y-%m-%d %H:%M:%S"), duration

    phases = timeline.get("phases", {})
    inspect_phase = timeline.get("inspect_phase", "")

    if not inspect_phase or inspect_phase not in phases:
        raise ValueError(f"inspect_phase '{inspect_phase}' not found in phases")

    phase = phases[inspect_phase]
    start_val = phase.get("start", "auto")
    end_val = phase.get("end", "auto")
    duration = phase.get("duration_minutes", 30)

    start_dt = resolve_time(start_val, tz_offset)
    end_dt = resolve_time(end_val, tz_offset)

    # If end is auto and duration_minutes exists, use start + duration
    if (end_val == "auto" or not end_val) and duration:
        end_dt = start_dt + timedelta(minutes=duration)
    # If start is auto and duration_minutes exists, use end - duration
    elif (start_val == "auto" or not start_val) and duration:
        start_dt = end_dt - timedelta(minutes=duration)

    return start_dt.strftime("%Y-%m-%d %H:%M:%S"), end_dt.strftime("%Y-%m-%d %H:%M:%S"), duration


def _validate_runtime(rt: dict[str, Any]) -> None:
    """Validate required runtime fields, raise on missing."""
    for field in RUNTIME_REQUIRED:
        if field not in rt:
            raise ValueError(f"runtime.{field} not configured, please specify in the runtime section")


def validate_config(config: dict[str, Any]) -> None:
    """Validate config completeness, raise ValueError on invalid config."""
    if "drill_name" not in config:
        raise ValueError("Missing 'drill_name' in config")
    if "regions" not in config or not config["regions"]:
        raise ValueError("Missing or empty 'regions' in config")
    if "services" not in config:
        raise ValueError("Missing 'services' in config")
    if "steady_state_rules" not in config:
        raise ValueError("Missing 'steady_state_rules' in config")

    # At least one service must be enabled
    any_enabled = any(
        svc.get("enabled", False) for svc in config["services"].values()
    )
    if not any_enabled:
        raise ValueError("No service enabled in config")

    # Timeline validation (if present)
    timeline = config.get("timeline")
    if timeline:
        phases = timeline.get("phases", {})
        inspect_phase = timeline.get("inspect_phase", "")
        if not phases:
            raise ValueError("timeline.phases is empty")
        if not inspect_phase:
            raise ValueError("timeline.inspect_phase is not specified")
        if inspect_phase not in phases:
            raise ValueError(f"timeline.inspect_phase '{inspect_phase}' not found in phases")
        for phase_name, phase_cfg in phases.items():
            if "start" not in phase_cfg or "end" not in phase_cfg:
                raise ValueError(f"Phase '{phase_name}' missing start or end")

    # Runtime validation
    rt = config.get("runtime", {})
    if rt.get("timezone_offset", 8) < -12 or rt.get("timezone_offset", 8) > 14:
        raise ValueError("runtime.timezone_offset out of range (-12..14)")
    if rt.get("ces_period", 60) <= 0:
        raise ValueError("runtime.ces_period must be positive")
    if rt.get("max_workers", 10) <= 0:
        raise ValueError("runtime.max_workers must be positive")


def init_config(output_path: str) -> None:
    """Generate a simple config template at the specified path."""
    template = {
        "drill_name": "Fault Drill Inspection",
        "phases": [
            {"key": "baseline", "name": "Pre-fault Baseline", "start": "2026-10-14 09:30:00", "end": "2026-10-14 10:00:00"},
            {"key": "fault", "name": "During Fault", "start": "2026-10-14 10:00:00", "end": "2026-10-14 10:30:00"},
            {"key": "recovery", "name": "Post-recovery Inspection", "start": "2026-10-14 10:30:00", "end": "2026-10-14 11:00:00"},
        ],
        "inspect_phase": "recovery",
        "targets": [
            {
                "service": "ecs",
                "region": "your-region",
                "instance_ids": [],
                "metrics": ["ECS CPU使用率", "ECS入方向带宽", "ECS出方向带宽"],
            },
            {
                "service": "rds",
                "region": "your-region",
                "instance_ids": [],
                "metrics": ["RDS CPU使用率", "RDS内存使用率"],
            },
        ],
    }
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    logger.info("Config template written to %s", output_path)
