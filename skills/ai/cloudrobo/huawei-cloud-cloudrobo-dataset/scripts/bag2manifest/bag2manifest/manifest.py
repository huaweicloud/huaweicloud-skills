"""ROS Manifest 2.0 construction, field expansion and sample-aware validation."""
from __future__ import annotations

import copy
import math
import re
from datetime import datetime, timezone
from typing import Any

import yaml

from . import MANIFEST_SCHEMA_VERSION, __version__, derive

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_FEAT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.]*$")
_GRIPPER_RE = re.compile(r"gripper|finger|hand|jaw|claw|suction|width|inner_joint|outer_joint|knuckle", re.I)
_INDEX_RE = re.compile(r"^(.*)\[([^\]]+)\]$")


class FlowList(list):
    """A YAML inline sequence."""


def _flow_repr(dumper, data):
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)


yaml.SafeDumper.add_representer(FlowList, _flow_repr)


def default_choices(profile: dict) -> dict:
    s = profile.get("suggested", {})
    source = profile.get("source", {})
    backend = source.get("backend", "")
    glob = "*.mcap" if backend == "mcap" else ("*.db3" if backend in ("sqlite", "sqlite3", "db3") else "*.bag")
    if ".db3" in source.get("name", ""):
        glob = "*.db3"
    return {
        "repo_id": "converted", "robot_type": (s.get("robot_type") or {}).get("value", "unknown"),
        "fps": int((s.get("fps") or {}).get("value", 30)),
        "cameras": [{"enabled": bool(c.get("enabled")), "name": name, "topic": c["topic"],
                     "depth": bool(c.get("is_depth")), "height": c.get("height"),
                     "width": c.get("width"), "resize": ""}
                    for name, c in (s.get("cameras") or {}).items()],
        "state": list((s.get("state") or {}).get("value", [])), "auto_normalize": False,
        "action_strategy": s.get("action", {}).get("strategy", "next_state"),
        "action": list(s.get("action", {}).get("value", [])),
        "task_mode": (s.get("task") or {}).get("mode", "const"), "task_text": "",
        "task_topic": (s.get("task") or {}).get("value", "") if (s.get("task") or {}).get("mode") == "topic" else "",
        "bag_glob": glob, "segment_mode": "per_bag", "min_frames": 30,
        "stamp_source": (s.get("time") or {}).get("value", "auto"),
        "tolerance_ms": 0, "on_stale": "hold", "video_codec": "auto",
        "chunk_size": 1000, "data_file_size_mb": 100, "video_file_size_mb": 200,
    }


def _field_stats(profile: dict) -> dict[str, dict]:
    return {f"{t['name']}.{f['path']}": {**f, "topic": t["name"], "type": t["type"]}
            for t in profile.get("topics", []) for f in t.get("fields", [])}


def _field_series(profile: dict) -> dict[str, list]:
    return {f"{t['name']}.{f['path']}": (t.get("series") or {}).get(f["path"], [])
            for t in profile.get("topics", []) for f in t.get("fields", [])}


def expand_locator(item: dict, stats: dict) -> list[str]:
    """Resolve grouped field dimensions in declared order for diagnostics."""
    locator = item.get("locator", "")
    names = item.get("names")
    if names:
        if item.get("names_from", "explicit") == "embedded":
            return [f"{locator}[{name}]" for name in names]
        return [f"{locator}[{i}]" for i in range(len(names))]
    if locator in stats:
        return [locator]
    prefix = locator + "["
    return [key for key in stats if key.startswith(prefix) and key.endswith("]")]


def make_items(items: list[Any], stats: dict, series_by_key: dict,
               auto_norm: bool = False) -> list[dict]:
    """Translate the UI's scalar selections into ordered Manifest 2.0 segments.

    Consecutive named JointState leaves are grouped with embedded names; numeric
    arrays are grouped only when the full positional prefix starts at index zero.
    Plain fields keep their recorded scale. Normalization is explicit and expr-only.
    """
    out: list[dict] = []
    for item in items or []:
        if isinstance(item, dict):
            entry = {key: copy.deepcopy(value) for key, value in item.items() if not key.startswith("_")}
            locator = entry.get("locator", "")
            match = _INDEX_RE.match(locator) if isinstance(locator, str) else None
            if match and not match[2].isdigit() and stats.get(locator, {}).get("type") == "sensor_msgs/msg/JointState":
                entry["locator"] = match[1]
                entry["names_from"] = "embedded"
                entry["names"] = FlowList([match[2]])
            if "path" in entry:
                entry["locator"] = entry.pop("path")
            if derive.is_expr(entry):
                entry.pop("locator", None)
                want = entry.get("normalize")
                if isinstance(want, bool):
                    entry.pop("normalize", None)
                    if want:
                        try:
                            st = derive.stats_of(derive.eval_array(entry["expr"], entry.get("inputs", []), series_by_key))
                            if st["max"] > st["min"]:
                                entry["normalize"] = FlowList([st["min"], st["max"]])
                        except derive.ExprError:
                            pass
                if not entry.get("name"):
                    entry.pop("name", None)
                if "role" not in entry and _GRIPPER_RE.search(str(entry.get("name", "")) + " ".join(entry.get("inputs", []))):
                    entry["role"] = "gripper"
            elif "normalize" in entry:
                # Legacy choices with explicit normalization are represented by an identity expr.
                locator = entry.pop("locator", "")
                entry.update(expr="f0", inputs=[locator])
            out.append(entry)
            continue
        key = str(item)
        match = _INDEX_RE.match(key)
        role = "gripper" if _GRIPPER_RE.search(key) else None
        stat = stats.get(key, {})
        named_joint = bool(match and stat.get("type") == "sensor_msgs/msg/JointState" and not match[2].isdigit())
        if named_joint:
            base, name = match.groups()
            if out and out[-1].get("locator") == base and out[-1].get("names_from") == "embedded" and out[-1].get("role") == role:
                out[-1]["names"].append(name)
            else:
                out.append({"locator": base, "names_from": "embedded", "names": FlowList([name]),
                            **({"role": role} if role else {})})
        elif match and match[2].isdigit() and (int(match[2]) == 0 or
                (out and out[-1].get("locator") == match[1] and
                 out[-1].get("names_from") == "explicit" and
                 len(out[-1].get("names", [])) == int(match[2]) and out[-1].get("role") == role)):
            base, index = match.groups()
            name = f"action_{index}"
            if int(index) == 0:
                out.append({"locator": base, "names_from": "explicit", "names": FlowList([name]),
                            **({"role": role} if role else {})})
            else:
                out[-1]["names"].append(name)
        else:
            out.append({"locator": key, **({"role": role} if role else {})})
    return out


def build_manifest(profile: dict, ch: dict) -> dict:
    stats, series = _field_stats(profile), _field_series(profile)
    cameras = {}
    for camera in ch.get("cameras", []):
        if not camera.get("enabled"):
            continue
        entry = {"locator": camera["topic"], "depth": bool(camera.get("depth"))}
        resize = camera.get("resize")
        if resize:
            if isinstance(resize, (list, tuple)):
                entry["resize"] = list(resize)
            else:
                match = re.fullmatch(r"\s*(\d+)\s*[x,\s]\s*(\d+)\s*", str(resize))
                entry["resize"] = FlowList([int(match[1]), int(match[2])]) if match else resize
        cameras[camera["name"]] = entry
    strategy = ch.get("action_strategy", "next_state")
    if strategy == "topic":  # migrate older choices.json, never emit old strategy
        strategy = "stored"
    action = {"strategy": strategy}
    if strategy == "stored":
        action["fields"] = make_items(ch.get("action", []), stats, series)
    mode = ch.get("task_mode", "const")
    task = {"mode": mode, "topic" if mode == "topic" else "text":
            ch.get("task_topic", "") if mode == "topic" else ch.get("task_text", "")}
    fps = int(ch.get("fps", 30))
    tol = int(ch.get("tolerance_ms", 0)) or max(1, round(500 / max(fps, 1)))
    source = {"bag_glob": ch.get("bag_glob") or default_choices(profile)["bag_glob"],
              "time": {"stamp_source": ch.get("stamp_source", "auto"), "tolerance_ms": tol,
                       "on_stale": ch.get("on_stale", "hold")},
              "segment": {"mode": ch.get("segment_mode", "per_bag"), "min_frames": int(ch.get("min_frames", 30))}}
    if isinstance(ch.get("source"), dict):
        for key, value in ch["source"].items():
            if isinstance(value, dict) and isinstance(source.get(key), dict):
                source[key].update(value)
            else:
                source[key] = copy.deepcopy(value)
    plan = {"schema_version": MANIFEST_SCHEMA_VERSION, "source_type": "ros2",
            "repo_id": ch.get("repo_id") or "converted", "robot_type": ch.get("robot_type") or "unknown",
            "fps": fps, "cameras": cameras, "state": make_items(ch.get("state", []), stats, series),
            "action": action, "task": task, "source": source,
            "output": {key: ch.get(key, default) for key, default in
                       (("chunk_size", 1000), ("data_file_size_mb", 100), ("video_file_size_mb", 200), ("video_codec", "auto"))}}
    if ch.get("extra_features"):
        plan["extra_features"] = {key: make_items(value, stats, series) for key, value in ch["extra_features"].items()}
    if ch.get("curation") is not None:
        plan["curation"] = copy.deepcopy(ch["curation"])
    plan["_provenance"] = {"generated_by": f"bag2manifest {__version__}",
                           "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                           "profile_source": profile.get("source", {}).get("name", ""),
                           "rules_hit": {k: v.get("rule") for k, v in profile.get("suggested", {}).items()
                                         if isinstance(v, dict) and v.get("rule")}}
    return plan


def compact_manifest(plan: dict) -> dict:
    result = copy.deepcopy(plan)
    result.pop("_provenance", None)
    if result.get("robot_type") == "unknown":
        result.pop("robot_type")
    return result


def manifest_to_yaml(plan: dict, compact: bool = True) -> str:
    rules = (plan.get("_provenance") or {}).get("rules_hit", {})
    header = ["# bag2manifest — ROS Manifest 2.0", "# 请确认关节顺序、动作语义、夹爪 role 与时间源；先试跑少量 episode"]
    if rules:
        header.append("# 推断依据: " + " ".join(f"{k}={v}" for k, v in rules.items()))
    return "\n".join(header) + "\n" + yaml.safe_dump(compact_manifest(plan) if compact else plan,
        allow_unicode=True, sort_keys=False, width=100)


def validate_manifest(plan: dict, profile: dict) -> list[dict]:
    """Validate the ROS 2.0 contract and dimensions against sampled data."""
    out = []
    stats = _field_stats(profile)
    topics = {t["name"]: t for t in profile.get("topics", [])}

    def issue(code, title, detail="", level="error"):
        out.append({"code": code, "level": level, "title": title, "detail": detail, "fix": []})

    def mapping(value, label):
        if not isinstance(value, dict):
            issue("U060", f"{label} 必须是键值对")
            return {}
        return value

    def number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

    if not isinstance(plan, dict):
        issue("U060", "manifest 顶层必须是键值对")
        return out
    if plan.get("schema_version") != "2.0" or plan.get("source_type") != "ros2":
        issue("U060", '需要 schema_version: "2.0" 和 source_type: ros2')
    for key in ("time", "segment", "quality"):
        if key in plan:
            issue("M010", f"旧版顶层 {key} 不属于 ROS Manifest 2.0", "time/segment 应放入 source；quality 不再导出")
    fps = plan.get("fps", 30)
    if not isinstance(fps, int) or isinstance(fps, bool) or fps <= 0:
        issue("E110", "fps 必须为正整数")
        fps = 30
    source = mapping(plan.get("source"), "source")
    if not isinstance(source.get("bag_glob"), str) or not source.get("bag_glob", "").strip():
        issue("U060", "source.bag_glob 必须是非空文件模式")
    time = mapping(source.get("time", {}), "source.time")
    if time.get("stamp_source", "auto") not in ("auto", "log_time", "header_time", "rosbag_time"):
        issue("M011", "source.time.stamp_source 不支持")
    if time.get("on_stale", "hold") != "hold":
        issue("M012", "ROS 当前只支持 source.time.on_stale: hold")
    if not isinstance(time.get("tolerance_ms", 50), int) or isinstance(time.get("tolerance_ms"), bool) or time.get("tolerance_ms", 50) <= 0:
        issue("M013", "source.time.tolerance_ms 必须为正整数")
    segment = mapping(source.get("segment", {}), "source.segment")
    if segment.get("mode", "per_bag") != "per_bag":
        issue("M014", "ROS 当前只支持 source.segment.mode: per_bag")
    if not isinstance(segment.get("min_frames", 30), int) or isinstance(segment.get("min_frames"), bool) or segment.get("min_frames", 30) < 1:
        issue("M015", "source.segment.min_frames 必须为正整数")

    def check_items(items, label, state_dim=0, action=False):
        if not isinstance(items, list) or not items:
            issue("U060", f"{label} 必须是非空字段项列表")
            return []
        dims = []
        for item in items:
            if not isinstance(item, dict):
                issue("E106", f"{label} 字段必须使用 locator/expr 对象，不能是字符串")
                continue
            if "path" in item:
                issue("E106", f"{label} 请将 path 改为 locator")
            if item.get("role") not in (None, "gripper"):
                issue("E116", f"{label} role 只支持 gripper")
            if item.get("interpolation") not in (None, "nearest", "linear", "front"):
                issue("E117", f"{label} interpolation 不支持")
            if "name" in item and (not isinstance(item["name"], str) or not item["name"].strip()):
                issue("E115", f"{label} name 必须为非空字符串")
            if item.get("strategy") is not None:
                index = item.get("state_index")
                if not action or item.get("strategy") != "next_state" or not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < state_dim:
                    issue("E114", f"{label} next_state 的 state_index 必须在 [0, {state_dim})")
                if any(k in item for k in ("locator", "expr", "inputs", "names", "normalize")):
                    issue("E114", f"{label} next_state 不能同时指定 locator/expr/names/normalize")
                default = item.get("default", 0.0)
                if not (number(default) or isinstance(default, list) and len(default) == 1 and all(number(v) for v in default)):
                    issue("E120", f"{label} next_state 的 default 必须是有限数值或单维数组")
                dims.append(f"next_state[{index}]")
                continue
            names = item.get("names")
            if names is not None and (not isinstance(names, list) or not names or
                    any(not isinstance(n, str) or not n for n in names) or len(names) != len(set(names))):
                issue("E115", f"{label} names 必须是非空且不重复的名称列表")
                continue
            if item.get("names_from", "explicit") not in ("explicit", "embedded"):
                issue("E115", "ROS names_from 只支持 explicit/embedded")
            keys = []
            if derive.is_expr(item):
                code = "E113" if action else "E112"
                try:
                    if "locator" in item:
                        raise derive.ExprError("expr 与 locator 互斥")
                    inputs = item.get("inputs", [])
                    if not isinstance(inputs, list) or not all(isinstance(v, str) for v in inputs):
                        raise derive.ExprError("inputs 必须是 locator 字符串列表")
                    if derive.required_vars(item.get("expr", "")) > len(inputs):
                        raise derive.ExprError("表达式变量数量超过 inputs")
                    missing = [key for key in inputs if key not in stats]
                    if missing and "default" not in item:
                        raise derive.ExprError("样例中找不到输入: " + ", ".join(missing))
                    if missing:
                        issue("W118", f"{label} 表达式输入缺失，将使用 default", level="warn")
                except (derive.ExprError, TypeError) as exc:
                    issue(code, f"{label} 计算字段非法", str(exc))
                dims.append("expr:" + str(item.get("name") or item.get("expr", "")))
            else:
                locator = item.get("locator")
                if not isinstance(locator, str) or not locator.startswith("/") or "." not in locator:
                    issue("E106", f"{label} locator 必须为 /topic.attr")
                    continue
                keys = expand_locator(item, stats)
                sample_type = next((value.get("type") for key, value in stats.items()
                                    if key.startswith(locator + "[") or key == locator), None)
                if sample_type == "sensor_msgs/msg/JointState" and "[" not in locator and item.get("names_from") != "embedded":
                    issue("E115", f"{label} JointState 数组必须用 names_from: embedded + names")
                if item.get("names_from") == "embedded" and not names:
                    issue("E115", f"{label} embedded 必须显式选择有序 names")
                missing = [key for key in keys if key not in stats]
                if not keys or missing:
                    if "default" in item:
                        issue("W118", f"{label} 字段无样例消息，使用已声明的 default: {locator}", level="warn")
                        keys = keys or [locator]
                    else:
                        issue("E108" if action else "E106", f"{label} 字段在样例中不存在: {locator}")
                dims.extend(keys)
                for key in keys:
                    stat = stats.get(key, {})
                    if stat.get("constant") or stat.get("near_constant"):
                        issue("W107" if action else "W106", f"{label} 字段恒定/近似恒定: {key}", level="warn")
            if "normalize" in item:
                norm = item["normalize"]
                if not derive.is_expr(item) or not isinstance(norm, (list, tuple)) or len(norm) != 2 or not all(number(x) for x in norm) or norm[0] >= norm[1]:
                    issue("E119", f"{label} normalize 仅用于 expr，且必须为递增的 [min, max]")
            default = item.get("default", 0.0)
            if isinstance(default, list):
                dim = 1 if derive.is_expr(item) else len(keys)
                if len(default) != dim or not all(number(v) for v in default):
                    issue("E120", f"{label} default 数组长度应与字段维度({dim})一致")
            elif not number(default):
                issue("E120", f"{label} default 必须为有限数值或数值数组")
        return dims

    state = check_items(plan.get("state"), "状态")
    if len(state) != len(set(state)):
        issue("E105", "状态向量存在重复维度")
    action = mapping(plan.get("action"), "action")
    if action.get("strategy") not in ("stored", "next_state"):
        issue("U001", "ROS action.strategy 只支持 stored/next_state")
    elif action["strategy"] == "stored":
        if not action.get("fields"):
            issue("U002", "stored 动作需要非空 fields")
        else:
            fields = check_items(action["fields"], "动作", len(state), True)
            if len(fields) != len(state):
                issue("W109", f"动作维度({len(fields)}) 与状态维度({len(state)}) 不同，请确认控制语义", level="warn")
    elif action.get("fields"):
        issue("U001", "整段 next_state 不应配置 fields")
    cameras = mapping(plan.get("cameras"), "cameras")
    if not cameras:
        issue("U060", "Manifest 2.0 cameras 不能为空")
    seen = set()
    for name, camera in cameras.items():
        camera = mapping(camera, f"相机 {name}")
        if not isinstance(name, str) or not _NAME_RE.fullmatch(name):
            issue("E101", f"相机名非法: {name}")
        locator = camera.get("locator")
        if not isinstance(locator, str) or not locator.startswith("/"):
            issue("E102", f"相机 {name} 需要 locator 话题")
            continue
        if locator in seen:
            issue("E102", f"相机话题重复绑定: {locator}")
        seen.add(locator)
        topic = topics.get(locator)
        if not topic or topic.get("kind") not in ("image", "compressed_image"):
            issue("E102", f"相机话题在样例中不存在或不是图像: {locator}")
        if not isinstance(camera.get("depth", False), bool):
            issue("E103", f"相机 {name} depth 必须为布尔值")
        resize = camera.get("resize")
        if resize is not None and (not isinstance(resize, (list, tuple)) or len(resize) != 2 or
                any(not isinstance(x, int) or isinstance(x, bool) or x <= 0 or x % 2 for x in resize)):
            issue("E103", f"相机 {name} resize 应为正偶数 [H, W]")
        if topic and topic.get("decode_error"):
            issue("E013", f"相机 {name} 解码异常", str(topic["decode_error"]))
        if topic and topic.get("size_stable") is False and resize is None:
            issue("E014", f"相机 {name} 分辨率不稳定，需要统一 resize")
        if topic and topic.get("hz", 0) + 0.5 < fps:
            issue("W111", f"相机 {name} 频率低于 fps，将重复帧", level="warn")
    task = mapping(plan.get("task"), "task")
    if task.get("mode") not in ("const", "topic"):
        issue("U021", "task.mode 只支持 const/topic")
    elif task["mode"] == "topic" and (not isinstance(task.get("topic"), str) or
            not task.get("topic") or topics.get(task["topic"], {}).get("kind") != "text"):
        issue("U021", "task.topic 必须指向样例中的文本话题")
    elif task["mode"] == "const" and not isinstance(task.get("text", ""), str):
        issue("U021", "task.text 必须为字符串")
    elif task["mode"] == "const" and not task.get("text", "").strip():
        issue("W031", "任务文本为空，算子可被 env/task.txt/prompt.json 覆盖，否则使用 lerobot_teleoperation", level="warn")
    extra = mapping(plan.get("extra_features", {}), "extra_features")
    for name, items in extra.items():
        if not isinstance(name, str) or not _FEAT_RE.fullmatch(name):
            issue("E121", f"额外特征名非法: {name}")
        elif name in ("observation.state", "action", "timestamp", "frame_index", "episode_index", "index", "task_index") or name.startswith("observation.images."):
            issue("E125", f"额外特征名与内建列冲突: {name}")
        if not items:
            issue("E124", f"额外特征 {name} 为空")
        else:
            check_items(items, f"额外特征 {name}")
    output = mapping(plan.get("output", {}), "output")
    for key in ("chunk_size", "data_file_size_mb", "video_file_size_mb"):
        if key in output and (not isinstance(output[key], int) or isinstance(output[key], bool) or output[key] <= 0):
            issue("E126", f"output.{key} 必须为正整数")
    if output.get("video_codec", "auto") not in ("auto", "libx264", "libsvtav1"):
        issue("E126", "output.video_codec 不支持")
    if any(key in output for key in ("data_files_size_in_mb", "video_files_size_in_mb")):
        issue("E126", "output 仍含旧版文件大小字段")
    out.extend(i for i in profile.get("issues", []) if i.get("code") == "E015" and i.get("level") == "error")
    if "curation" in plan and not isinstance(plan["curation"], dict):
        issue("E127", "curation 必须为键值对，按原样携带给下游清洗")
    return out
