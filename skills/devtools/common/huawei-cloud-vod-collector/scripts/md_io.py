from __future__ import annotations

import argparse
import os
import re
from datetime import datetime
from pathlib import Path

if os.name == "nt":
    import msvcrt

    def _lock_file(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)

    def _unlock_file(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def _lock_file(f):
        fcntl.flock(f, fcntl.LOCK_EX)

    def _unlock_file(f):
        fcntl.flock(f, fcntl.LOCK_UN)


def _parse_iso_timestamp(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


try:
    from .models import (
        FeedbackRecord,
        FeedbackType,
        FeedbackStatus,
        RequirementRecord,
        Priority,
        ReqStatus,
        DeliveryStatus,
        StageReport,
        Stage,
        StageStatus,
        DialogTurn,
    )
except ImportError:
    from models import (
        FeedbackRecord,
        FeedbackType,
        FeedbackStatus,
        RequirementRecord,
        Priority,
        ReqStatus,
        DeliveryStatus,
        StageReport,
        Stage,
        StageStatus,
        DialogTurn,
    )


def generate_id(prefix: str, directory: Path) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = directory / ".lock"
    lock_path.touch(exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    pattern = re.compile(rf"^{prefix}-{today}-(\d{{4}})\.md$")
    max_seq = 0
    with open(lock_path, "w") as lock_file:
        _lock_file(lock_file)
        try:
            for f in directory.iterdir():
                m = pattern.match(f.name)
                if m:
                    seq = int(m.group(1))
                    if seq > max_seq:
                        max_seq = seq
        finally:
            _unlock_file(lock_file)
    next_seq = max_seq + 1
    return f"{prefix}-{today}-{next_seq:04d}"


def check_duplicate(feedbacks_dir: Path, text: str) -> list[dict]:
    if not feedbacks_dir.exists():
        return []
    results = []
    text_lower = text.lower().strip()
    text_chars = set(c for c in text_lower if c.strip())
    for f in sorted(feedbacks_dir.glob("VOD-*.md")):
        try:
            content = f.read_text(encoding="utf-8")
            meta = _parse_metadata_section(content, "Error Information")
            ctx = _parse_metadata_section(content, "Context")
            desc = meta.get("error_message", "") or ctx.get("user_intent", "")
            if not desc or not text_lower:
                continue
            desc_lower = desc.lower()
            if text_lower in desc_lower or desc_lower in text_lower:
                fb_meta = _parse_metadata_section(content, "Metadata")
                results.append({
                    "feedback_id": fb_meta.get("feedback_id", f.stem),
                    "description": desc[:100],
                    "status": fb_meta.get("status", ""),
                })
                continue
            desc_chars = set(c for c in desc_lower if c.strip())
            if text_chars and desc_chars:
                overlap = len(text_chars & desc_chars) / min(len(text_chars), len(desc_chars))
                if overlap >= 0.6:
                    fb_meta = _parse_metadata_section(content, "Metadata")
                    results.append({
                        "feedback_id": fb_meta.get("feedback_id", f.stem),
                        "description": desc[:100],
                        "status": fb_meta.get("status", ""),
                    })
        except Exception:
            continue
    return results


def _build_error_stack(feedback: FeedbackRecord) -> str | None:
    parts = []
    if feedback.problem_description:
        parts.append(f"【问题描述】\n{feedback.problem_description}")
    if feedback.occurrence_scenario:
        parts.append(f"【复现场景】\n{feedback.occurrence_scenario}")
    if feedback.expected_behavior:
        parts.append(f"【预期行为】\n{feedback.expected_behavior}")
    if feedback.actual_behavior:
        parts.append(f"【实际行为】\n{feedback.actual_behavior}")
    if feedback.error_stack:
        if parts:
            parts.append(f"【错误堆栈】\n{feedback.error_stack}")
        else:
            return feedback.error_stack
    if not parts:
        return feedback.error_stack
    return "\n\n".join(parts)


def write_feedback_md(feedback: FeedbackRecord, file_path: Path) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# VoD Feedback Record",
        "",
        "## Metadata",
        f"- **feedback_id**: {feedback.feedback_id}",
        f"- **feedback_type**: {feedback.feedback_type.value}",
        f"- **timestamp**: {feedback.timestamp.isoformat()}",
        f"- **session_id**: {feedback.session_id}",
        f"- **platform**: {feedback.platform}",
        f"- **confidence**: {feedback.confidence}",
        f"- **status**: {feedback.status.value}",
    ]
    if feedback.product_name:
        lines.append(f"- **product_name**: {feedback.product_name}")

    error_stack_content = _build_error_stack(feedback)
    lines.extend([
        "",
        "## Error Information",
        f"- **error_type**: {feedback.error_type or ''}",
        f"- **error_message**: {feedback.error_message or ''}",
        "- **error_stack**:",
    ])
    if error_stack_content:
        lines.append("  ```")
        for stack_line in error_stack_content.split("\n"):
            lines.append(f"  {stack_line}")
        lines.append("  ```")
    else:
        lines.append("  (none)")
    lines.extend([
        "",
        "## Context",
        f"- **user_intent**: {feedback.user_intent or ''}",
    ])
    if feedback.agent_action:
        lines.append("- **agent_action**:")
        lines.append("  ```")
        for action_line in feedback.agent_action.split("\n"):
            lines.append(f"  {action_line}")
        lines.append("  ```")
    else:
        lines.append("- **agent_action**: ")
    lines.extend([
        f"- **user_expected**: {feedback.user_expected or ''}",
    ])

    if feedback.dialog_context:
        lines.append("- **dialog_context**:")
        for turn in feedback.dialog_context:
            lines.append(f"  - [{turn.turn_index}] {turn.role}: {turn.content}")
            if turn.thinking:
                lines.append(f"    - [thinking]: {turn.thinking}")
    else:
        lines.append("- **dialog_context**: ")

    if feedback.environment:
        lines.append("- **environment**:")
        for k, v in feedback.environment.items():
            lines.append(f"  - {k}: {v}")
    else:
        lines.append("- **environment**: ")

    if feedback.more_details:
        lines.append("")
        lines.append("## More Details")
        for k, v in feedback.more_details.items():
            lines.append(f"- **{k}**: {v}")

    lines.extend([
        "",
        "## Dedup",
        f"- **recurrence_count**: {feedback.recurrence_count}",
        f"- **dedup_key**: {feedback.dedup_key or ''}",
        "",
        "## Annotations",
    ])
    for ann in feedback.annotations:
        lines.append(f"- {ann}")
    if not feedback.annotations:
        lines.append("- (none)")

    file_path.write_text("\n".join(lines), encoding="utf-8")


def _normalize_section_header(header: str) -> str:
    return re.sub(r"\s*\(.*?\)\s*$", "", header).strip()


def _parse_metadata_section(text: str, section: str) -> dict[str, str]:
    result: dict[str, str] = {}
    in_section = False
    normalized = _normalize_section_header(section)
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            header = _normalize_section_header(stripped[3:])
            if header == normalized:
                in_section = True
                continue
            elif in_section:
                break
        if in_section and stripped.startswith("- **"):
            m = re.match(r"- \*\*(.+?)\*\*:\s*(.*)", stripped)
            if m:
                result[m.group(1)] = m.group(2).strip()
    return result


def _extract_code_block_value(text: str, section: str, field: str) -> str | None:
    in_section = False
    in_field = False
    in_code = False
    code_lines = []
    normalized = _normalize_section_header(section)
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            header = _normalize_section_header(stripped[3:])
            if header == normalized:
                in_section = True
                continue
            elif in_section:
                break
        if not in_section:
            continue
        if stripped == f"- **{field}**:":
            in_field = True
            continue
        if in_field and not in_code:
            if stripped.startswith("```"):
                in_code = True
                code_lines = []
                continue
            elif stripped.startswith("- **"):
                in_field = False
                continue
        if in_field and in_code:
            if stripped.startswith("```"):
                break
            code_lines.append(line)
    if code_lines:
        return "\n".join(code_lines)
    return None


def _extract_multiline_section(text: str, header: str) -> str | None:
    result_lines = []
    in_section = False
    normalized = _normalize_section_header(header)
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            h = _normalize_section_header(stripped[3:])
            if h == normalized:
                in_section = True
                continue
            elif in_section:
                break
        if in_section:
            result_lines.append(line)
    content = "\n".join(result_lines).strip()
    return content if content else None


def read_feedback_md(file_path: Path) -> FeedbackRecord:
    text = file_path.read_text(encoding="utf-8")
    meta = _parse_metadata_section(text, "Metadata")
    error = _parse_metadata_section(text, "Error Information")
    ctx = _parse_metadata_section(text, "Context")
    dedup = _parse_metadata_section(text, "Dedup")

    error_stack = _extract_code_block_value(text, "Error Information", "error_stack") or error.get("error_stack") or None

    agent_action = _extract_code_block_value(text, "Context", "agent_action") or ctx.get("agent_action") or None

    annotations = []
    in_ann = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            h = _normalize_section_header(stripped[3:])
            if h == "Annotations":
                in_ann = True
                continue
            elif in_ann:
                break
        if in_ann and stripped.startswith("- ") and stripped != "- (none)":
            annotations.append(stripped[2:])

    dialog_context = None
    if ctx.get("dialog_context") and ctx["dialog_context"] != "":
        dialog_context = []
        in_dc = False
        current_thinking = None
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("- **dialog_context**"):
                in_dc = True
                continue
            if in_dc and stripped.startswith("- [thinking]:"):
                thinking_match = re.match(r"- \[thinking\]: (.+)", stripped)
                if thinking_match and dialog_context:
                    dialog_context[-1].thinking = thinking_match.group(1)
                continue
            if in_dc and stripped.startswith("- ") and not stripped.startswith("- **"):
                m = re.match(r"- \[(\d+)\] (\w+): (.+)", stripped)
                if m:
                    dialog_context.append(DialogTurn(
                        turn_index=int(m.group(1)),
                        role=m.group(2),
                        content=m.group(3),
                        timestamp=datetime.now(),
                    ))
            if in_dc and (stripped.startswith("- **") and "dialog_context" not in stripped):
                in_dc = False

    environment = None
    in_env = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- **environment**"):
            in_env = True
            environment = {}
            continue
        if in_env and stripped.startswith("- ") and not stripped.startswith("- **"):
            m = re.match(r"- (\w+): (.+)", stripped)
            if m:
                environment[m.group(1)] = m.group(2)
        if in_env and (stripped.startswith("- **") and "environment" not in stripped):
            in_env = False

    user_report = _parse_metadata_section(text, "User Report")
    problem_description = user_report.get("problem_description") or None
    occurrence_scenario = user_report.get("scenario") or None
    expected_behavior = user_report.get("expected_behavior") or None
    actual_behavior = user_report.get("actual_behavior") or None

    if error_stack and any(marker in error_stack for marker in ["【问题描述】", "【复现场景】", "【预期行为】", "【实际行为】", "【错误堆栈】"]):
        sections = {"问题描述": None, "复现场景": None, "预期行为": None, "实际行为": None, "错误堆栈": None}
        current_key = None
        current_lines = []
        for line in error_stack.split("\n"):
            m = re.match(r"^【(.+?)】$", line.strip())
            if m and m.group(1) in sections:
                if current_key is not None:
                    sections[current_key] = "\n".join(current_lines).strip() or None
                current_key = m.group(1)
                current_lines = []
                continue
            if current_key is not None:
                current_lines.append(line)
        if current_key is not None:
            sections[current_key] = "\n".join(current_lines).strip() or None
        if sections["问题描述"]:
            problem_description = sections["问题描述"]
        if sections["复现场景"]:
            occurrence_scenario = sections["复现场景"]
        if sections["预期行为"]:
            expected_behavior = sections["预期行为"]
        if sections["实际行为"]:
            actual_behavior = sections["实际行为"]
        if sections["错误堆栈"]:
            error_stack = sections["错误堆栈"]

    more_details = None
    in_md = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            h = _normalize_section_header(stripped[3:])
            if h == "More Details":
                in_md = True
                more_details = {}
                continue
            elif in_md:
                break
        if in_md and stripped.startswith("- **"):
            m = re.match(r"- \*\*(.+?)\*\*:\s*(.*)", stripped)
            if m:
                more_details[m.group(1)] = m.group(2).strip()
    if more_details is not None and not more_details:
        more_details = None

    return FeedbackRecord(
        feedback_id=meta.get("feedback_id", ""),
        feedback_type=FeedbackType(meta.get("feedback_type", "error")),
        timestamp=_parse_iso_timestamp(meta["timestamp"]) if "timestamp" in meta else datetime.now(),
        session_id=meta.get("session_id", ""),
        platform=meta.get("platform", "generic"),
        error_type=error.get("error_type") or None,
        error_message=error.get("error_message") or None,
        error_stack=error_stack,
        user_intent=ctx.get("user_intent") or None,
        agent_action=agent_action,
        user_expected=ctx.get("user_expected") or None,
        dialog_context=dialog_context,
        environment=environment,
        confidence=float(meta.get("confidence", 0.0)),
        status=FeedbackStatus(meta.get("status", "open")),
        recurrence_count=int(dedup.get("recurrence_count", 1)),
        dedup_key=dedup.get("dedup_key") or None,
        annotations=annotations,
        problem_description=problem_description,
        occurrence_scenario=occurrence_scenario,
        expected_behavior=expected_behavior,
        actual_behavior=actual_behavior,
        product_name=meta.get("product_name") or None,
        more_details=more_details,
    )


def write_requirement_md(requirement: RequirementRecord, file_path: Path) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# VoD Requirement",
        "",
        "## Metadata",
        f"- **requirement_id**: {requirement.requirement_id}",
        f"- **title**: {requirement.title}",
        f"- **priority**: {requirement.priority.value}",
        f"- **domain**: {requirement.domain}",
        f"- **status**: {requirement.status.value}",
        "",
        "## Description",
        requirement.description,
        "",
        "## Suggested Action",
        requirement.suggested_action or "",
        "",
        "## Source",
        f"- **source_feedbacks**: {', '.join(requirement.source_feedbacks) if requirement.source_feedbacks else ''}",
        f"- **recurrence_count**: {requirement.recurrence_count}",
        f"- **see_also**: {', '.join(requirement.see_also) if requirement.see_also else ''}",
        "",
        "## Delivery",
        f"- **delivery_status**: {requirement.delivery_status.value}",
        f"- **delivered_at**: {requirement.delivered_at.isoformat() if requirement.delivered_at else ''}",
        f"- **delivery_channel**: {requirement.delivery_channel or ''}",
        "",
        "## Timeline",
        f"- **created_at**: {requirement.created_at.isoformat()}",
        f"- **updated_at**: {requirement.updated_at.isoformat()}",
        f"- **resolved_at**: {requirement.resolved_at.isoformat() if requirement.resolved_at else ''}",
        "",
        "## Annotations",
    ]
    for ann in requirement.annotations:
        lines.append(f"- {ann}")
    if not requirement.annotations:
        lines.append("- (none)")

    file_path.write_text("\n".join(lines), encoding="utf-8")


def read_requirement_md(file_path: Path) -> RequirementRecord:
    text = file_path.read_text(encoding="utf-8")
    meta = _parse_metadata_section(text, "Metadata")
    src = _parse_metadata_section(text, "Source")
    dlv = _parse_metadata_section(text, "Delivery")
    tl = _parse_metadata_section(text, "Timeline")

    description = ""
    in_desc = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped == "## Description":
            in_desc = True
            continue
        if in_desc and stripped.startswith("## "):
            in_desc = False
        if in_desc:
            description += line + "\n"
    description = description.strip()

    suggested_action = ""
    in_sa = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped == "## Suggested Action":
            in_sa = True
            continue
        if in_sa and stripped.startswith("## "):
            in_sa = False
        if in_sa:
            suggested_action += line + "\n"
    suggested_action = suggested_action.strip()

    annotations = []
    in_ann = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped == "## Annotations":
            in_ann = True
            continue
        if in_ann and stripped.startswith("## "):
            break
        if in_ann and stripped.startswith("- ") and stripped != "- (none)":
            annotations.append(stripped[2:])

    source_feedbacks = [s.strip() for s in src.get("source_feedbacks", "").split(",") if s.strip()]
    see_also = [s.strip() for s in src.get("see_also", "").split(",") if s.strip()]

    return RequirementRecord(
        requirement_id=meta.get("requirement_id", ""),
        title=meta.get("title", ""),
        description=description,
        priority=Priority(meta.get("priority", "medium")),
        domain=meta.get("domain", ""),
        status=ReqStatus(meta.get("status", "open")),
        suggested_action=suggested_action or None,
        source_feedbacks=source_feedbacks,
        recurrence_count=int(src.get("recurrence_count", 1)),
        see_also=see_also,
        created_at=datetime.fromisoformat(tl["created_at"]) if "created_at" in tl else datetime.now(),
        updated_at=datetime.fromisoformat(tl["updated_at"]) if "updated_at" in tl else datetime.now(),
        resolved_at=datetime.fromisoformat(tl["resolved_at"]) if tl.get("resolved_at") else None,
        delivery_status=DeliveryStatus(dlv.get("delivery_status", "pending")),
        delivered_at=datetime.fromisoformat(dlv["delivered_at"]) if dlv.get("delivered_at") else None,
        delivery_channel=dlv.get("delivery_channel") or None,
        annotations=annotations,
    )


def write_stage_report_md(report: StageReport, logs_dir: Path) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = report.timestamp.strftime("%Y%m%d-%H%M%S")
    file_path = logs_dir / f"stage-{ts}.md"
    lines = [
        "# 阶段报告",
        "",
        f"## {report.stage.value} 阶段",
        "",
        f"- **状态**: {report.stage_status.value}",
        f"- **输入条目数**: {report.input_count}",
        f"- **输出条目数**: {report.output_count}",
        f"- **耗时**: {report.duration_ms}ms",
        f"- **时间**: {report.timestamp.isoformat()}",
    ]
    if report.details:
        lines.append("- **详情**:")
        for k, v in report.details.items():
            lines.append(f"  - {k}: {v}")
    lines.append("")
    file_path.write_text("\n".join(lines), encoding="utf-8")


def read_all_feedbacks(feedbacks_dir: Path) -> list[FeedbackRecord]:
    if not feedbacks_dir.exists():
        return []
    result = []
    for f in sorted(feedbacks_dir.glob("VOD-*.md")):
        try:
            result.append(read_feedback_md(f))
        except Exception:
            continue
    return result


def read_all_requirements(requirements_dir: Path) -> list[RequirementRecord]:
    if not requirements_dir.exists():
        return []
    result = []
    for f in sorted(requirements_dir.glob("REQ-*.md")):
        try:
            result.append(read_requirement_md(f))
        except Exception:
            continue
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="VoD Markdown IO")
    subparsers = parser.add_subparsers(dest="command", required=True)

    id_p = subparsers.add_parser("generate-id", help="generate feedback ID")
    id_p.add_argument("--prefix", required=True, help="ID prefix (VOD or REQ)")
    id_p.add_argument("--feedbacks-dir", required=True, type=Path, help="feedbacks directory")

    dup_p = subparsers.add_parser("check-duplicate", help="check duplicate feedback")
    dup_p.add_argument("--feedbacks-dir", required=True, type=Path, help="feedbacks directory")
    dup_p.add_argument("--text", required=True, help="text to check for duplicates")

    write_p = subparsers.add_parser("write-feedback", help="write feedback record to markdown file")
    write_p.add_argument("--feedback-id", required=True, help="feedback ID")
    write_p.add_argument("--feedback-type", required=True, choices=["error", "rejection", "user_report", "suggestion"], help="feedback type")
    write_p.add_argument("--timestamp", required=True, help="ISO 8601 timestamp")
    write_p.add_argument("--session-id", required=True, help="session ID")
    write_p.add_argument("--platform", default="generic", help="platform type")
    write_p.add_argument("--confidence", type=float, default=0.0, help="confidence score 0.0-1.0")
    write_p.add_argument("--status", default="open", choices=["open", "promoted", "resolved", "discarded"], help="feedback status")
    write_p.add_argument("--product-name", default="", help="product/skill name")
    write_p.add_argument("--error-type", default="", help="error type")
    write_p.add_argument("--error-message", default="", help="error message")
    write_p.add_argument("--error-stack", default="", help="error stack trace")
    write_p.add_argument("--user-intent", default="", help="inferred user intent")
    write_p.add_argument("--agent-action", default="", help="agent behavior description")
    write_p.add_argument("--user-expected", default="", help="what user expected to happen")
    write_p.add_argument("--problem-description", default="", help="problem description (for user_report)")
    write_p.add_argument("--occurrence-scenario", default="", help="occurrence scenario")
    write_p.add_argument("--expected-behavior", default="", help="expected behavior")
    write_p.add_argument("--actual-behavior", default="", help="actual behavior")
    write_p.add_argument("--recurrence-count", type=int, default=1, help="recurrence count")
    write_p.add_argument("--dedup-key", default="", help="dedup key")
    write_p.add_argument("--annotations", nargs="*", default=[], help="annotation labels (e.g. skill:xxx category:yyy severity:high)")
    write_p.add_argument("--more-details", nargs="*", default=[], help="more details key:value pairs (e.g. summary:xxx additional_info:yyy)")
    write_p.add_argument("--output", required=True, type=Path, help="output file path")

    args = parser.parse_args()

    if args.command == "generate-id":
        feedback_id = generate_id(args.prefix, args.feedbacks_dir)
        print(feedback_id)
    elif args.command == "check-duplicate":
        import json
        results = check_duplicate(args.feedbacks_dir, args.text)
        print(json.dumps(results, ensure_ascii=False))
    elif args.command == "write-feedback":
        feedback = FeedbackRecord(
            feedback_id=args.feedback_id,
            feedback_type=FeedbackType(args.feedback_type),
            timestamp=_parse_iso_timestamp(args.timestamp) if args.timestamp else datetime.now(),
            session_id=args.session_id,
            platform=args.platform,
            confidence=args.confidence,
            status=FeedbackStatus(args.status),
            product_name=args.product_name or None,
            error_type=args.error_type or None,
            error_message=args.error_message or None,
            error_stack=args.error_stack or None,
            user_intent=args.user_intent or None,
            agent_action=args.agent_action or None,
            user_expected=args.user_expected or None,
            problem_description=args.problem_description or None,
            occurrence_scenario=args.occurrence_scenario or None,
            expected_behavior=args.expected_behavior or None,
            actual_behavior=args.actual_behavior or None,
            recurrence_count=args.recurrence_count,
            dedup_key=args.dedup_key or None,
            annotations=args.annotations,
            more_details=dict(pair.split(":", 1) for pair in args.more_details if ":" in pair) or None,
        )
        write_feedback_md(feedback, args.output)
        import json as _json
        print(_json.dumps({"feedback_id": feedback.feedback_id, "file": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
