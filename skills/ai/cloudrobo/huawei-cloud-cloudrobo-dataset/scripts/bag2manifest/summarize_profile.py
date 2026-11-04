"""Render a compact, inspectable Markdown summary of a bag2manifest run."""

from __future__ import annotations

from typing import Any


def _cell(value: Any) -> str:
    return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(_cell(v) for v in row) + " |" for row in rows)
    return "\n".join(lines)


def _field_index(profile: dict) -> dict[str, dict]:
    return {f"{t['name']}.{f['path']}": f
            for t in profile.get("topics", []) for f in t.get("fields", [])}


def _field_row(item: Any, stats: dict[str, dict]) -> list[str]:
    if isinstance(item, dict) and "expr" in item:
        return [item.get("name") or item["expr"], "derived", "—", "—", "—"]
    if isinstance(item, dict) and item.get("strategy") == "next_state":
        return [f"next_state[{item.get('state_index')}] ({item.get('name', '')})", "derived", "—", "—", "—"]
    key = item.get("locator", item.get("path", "")) if isinstance(item, dict) else str(item)
    stat = stats.get(key, {})
    return [key, str(stat.get("n", "—")), str(stat.get("min", "—")),
            str(stat.get("max", "—")),
            "yes" if stat.get("constant") else ("near" if stat.get("near_constant") else "no")]


def make_summary(profile: dict, choices: dict, issues: dict) -> str:
    from bag2manifest.manifest import build_manifest, expand_locator, _field_stats
    plan = build_manifest(profile, choices)
    source = profile["source"]
    suggested = profile.get("suggested", {})
    topics = profile.get("topics", [])
    by_name = {t["name"]: t for t in topics}
    stats = _field_index(profile)
    lines = [
        "# ROS bag inspection summary",
        "",
        f"- Source: `{source['name']}` ({source['backend']})",
        f"- Duration: {source['duration_s']} s; {source['topic_count']} total topics, "
        f"{len(topics)} inspected, {len(source.get('ignored_topics', []))} ignored",
        f"- Partial scan: {'yes' if source.get('partial') else 'no'}",
        "",
        "## Topics",
        "",
    ]
    topic_rows = []
    for topic in topics:
        image = topic.get("image") or {}
        text_count = len(topic.get("text_samples", []))
        detail = (f"{image.get('width')}x{image.get('height')} {image.get('encoding')}"
                  if image else (f"{text_count} text sample{'s' if text_count != 1 else ''}"
                                 if topic.get("kind") == "text"
                                 else f"{len(topic.get('fields', []))} numeric fields"))
        topic_rows.append([topic["name"], topic["kind"], topic["count"], topic["hz"], detail])
    lines += [_table(["Topic", "Kind", "Messages", "Hz", "Data"], topic_rows), ""]

    fps = suggested.get("fps", {})
    nominal_frames = round(float(source["duration_s"]) * int(choices.get("fps") or 0))
    lines += ["## Suggested mapping", "",
              f"- FPS: **{choices.get('fps')}** ({fps.get('rule', 'manual')}: {fps.get('why', '')})",
              f"- Nominal frames at this FPS: approximately **{nominal_frames}** "
              "(duration × FPS; conversion may differ after alignment and min_frames filtering)",
              f"- Time source: **{choices.get('stamp_source')}** "
              f"({suggested.get('time', {}).get('rule', 'manual')})",
              f"- Schema: **2.0 / ros2**; bag_glob: `{plan['source']['bag_glob']}`",
              f"- Alignment tolerance: {plan['source']['time']['tolerance_ms']} ms; segment: per_bag",
              f"- Task: **{choices.get('task_mode')}** "
              f"({choices.get('task_topic') or choices.get('task_text') or 'not set'})"]
    task_topic = by_name.get(choices.get("task_topic", ""), {})
    if task_topic.get("text_samples"):
        lines.append(f"- Task sample: {task_topic['text_samples'][0]}")
    lines += ["", "### Cameras", ""]
    camera_rows = []
    for camera in choices.get("cameras", []):
        topic = by_name.get(camera.get("topic"), {})
        image = topic.get("image") or {}
        camera_rows.append([camera.get("name"), camera.get("topic"),
                            "yes" if camera.get("enabled") else "no",
                            f"{image.get('width')}x{image.get('height')} {image.get('encoding')}",
                            topic.get("hz", "—"), len(topic.get("thumbnails", [])),
                            "yes" if topic.get("size_stable") else "no",
                            camera.get("resize") or "—"])
    lines += [_table(["Name", "Topic", "Enabled", "Image", "Hz", "Thumbnails", "Stable", "Resize"], camera_rows), ""]

    expanded_stats = _field_stats(profile)
    def flat_items(items):
        return [key for item in items for key in
                ([item] if "expr" in item or "strategy" in item else expand_locator(item, expanded_stats))]
    state = flat_items(plan["state"])
    lines += [f"### State ({len(state)} dimensions)", "",
              _table(["Field", "Samples", "Min", "Max", "Constant"],
                     [_field_row(item, stats) for item in state]), ""]

    action = flat_items(plan["action"].get("fields", []))
    action_dim = len(action) if plan["action"]["strategy"] == "stored" else len(state)
    lines += [f"### Action ({plan['action']['strategy']}; {action_dim} dimensions)", ""]
    candidates = suggested.get("action", {}).get("candidates", [])
    candidate_rows = []
    for name in candidates:
        topic = by_name.get(name, {})
        candidate_rows.append([name, topic.get("hz", "—"), len(topic.get("fields", [])),
                               "yes" if action and any(
                                   str(item.get("locator", item.get("path", "")) if isinstance(item, dict) else item).startswith(name + ".")
                                   for item in action) else "no"])
    if candidate_rows:
        lines += [_table(["Candidate topic", "Hz", "Numeric fields", "In current action"],
                         candidate_rows), ""]
    if plan["action"]["strategy"] == "stored":
        lines += [_table(["Field", "Samples", "Min", "Max", "Constant"],
                         [_field_row(item, stats) for item in action]), ""]

    clock_rows = []
    for topic in topics:
        if topic.get("kind") in ("image", "compressed_image"):
            continue
        clock_rows.append([topic["name"], "yes" if topic.get("has_header") else "no",
                           topic.get("stamp_valid_ratio", "—"),
                           topic.get("clock_delta_s", "—")])
    lines += ["### Timestamps", "",
              _table(["Topic", "Has header", "Valid stamp ratio", "Header minus log time (s)"],
                     clock_rows), ""]

    lines += ["## Issues", "",
              "Raw source issues remain recorded after a mapping choice is confirmed. "
              "Check `unresolved_errors` for the current blocking set.", ""]
    for key in ("source", "validation", "unresolved_errors"):
        entries = issues.get(key, [])
        lines += [f"### {key} ({len(entries)})", ""]
        lines += [_table(["Code", "Level", "Title"],
                         [[e.get("code"), e.get("level"), e.get("title")] for e in entries])
                  if entries else "None", ""]
    return "\n".join(lines).rstrip() + "\n"
