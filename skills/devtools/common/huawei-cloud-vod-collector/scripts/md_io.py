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
    from .models import FeedbackRecord, FeedbackType, FeedbackStatus, DialogTurn
    from .vod_sanitize import sanitize_file
except ImportError:
    from models import FeedbackRecord, FeedbackType, FeedbackStatus, DialogTurn
    from vod_sanitize import sanitize_file


def generate_id(prefix: str, directory: Path) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = directory / ".lock"
    lock_path.touch(exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    pattern = re.compile(rf"^{prefix}-{today}-(\d{{4}})\.md$")
    max_seq = 0
    with open(lock_path, "wb") as lock_file:
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





def _build_error_stack(feedback: FeedbackRecord) -> str | None:
    parts = []
    if feedback.problem_description:
        parts.append(f"【问题描述】\n{feedback.problem_description}")
    if feedback.occurrence_scenario:
        parts.append(f"【复现场景】\n{feedback.occurrence_scenario}")
    if feedback.expected_behavior:
        parts.append(f"【预期行为】\n{feedback.expected_behavior}")
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
    if feedback.voice_source:
        lines.append(f"- **voice_source**: {feedback.voice_source}")

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

    has_report = any([feedback.problem_description, feedback.occurrence_scenario,
                      feedback.expected_behavior])
    if has_report:
        lines.extend([
            "",
            "## User Report",
        ])
        if feedback.problem_description:
            lines.append(f"- **problem_description**: {feedback.problem_description}")
        if feedback.occurrence_scenario:
            lines.append(f"- **scenario**: {feedback.occurrence_scenario}")
        if feedback.expected_behavior:
            lines.append(f"- **expected_behavior**: {feedback.expected_behavior}")

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
    in_multiline = False
    multiline_key = None
    multiline_lines = []
    normalized = _normalize_section_header(section)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## "):
            header = _normalize_section_header(stripped[3:])
            if header == normalized:
                in_section = True
                in_multiline = False
                continue
            elif in_section:
                break
        if not in_section:
            continue

        # 正在收集多行值
        if in_multiline:
            # 遇到新字段（以 - ** 开头）或下一行只有空白且再下一行是新字段 → 结束多行
            if stripped.startswith("- **"):
                result[multiline_key] = "\n".join(multiline_lines).strip()
                in_multiline = False
                # 继续处理当前行作为新字段（不 continue）
            else:
                # 检查空行是否是字段分隔：空行 + 下一行是 - **
                if stripped == "" and i + 1 < len(lines):
                    next_stripped = lines[i + 1].strip()
                    if next_stripped.startswith("- **"):
                        result[multiline_key] = "\n".join(multiline_lines).strip()
                        in_multiline = False
                        continue
                if in_multiline:
                    multiline_lines.append(line.rstrip("\n"))
                    continue

        if stripped.startswith("- **"):
            m = re.match(r"- \*\*(.+?)\*\*:\s*(.*)", stripped)
            if m:
                key = m.group(1)
                value = m.group(2).strip()
                if value == "|":
                    in_multiline = True
                    multiline_key = key
                    multiline_lines = []
                else:
                    result[key] = value

    if in_multiline and multiline_lines:
        result[multiline_key] = "\n".join(multiline_lines).strip()

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
    # 无论 metadata 解析是否捕获到 dialog_context 值，都尝试按列表格式解析
    in_dc = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- **dialog_context**"):
            in_dc = True
            dialog_context = []
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
        if in_dc and stripped.startswith("## "):
            break
        if in_dc and stripped.startswith("- **") and "dialog_context" not in stripped:
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

    if error_stack and any(marker in error_stack for marker in ["【问题描述】", "【复现场景】", "【预期行为】", "【错误堆栈】"]):
        sections = {"问题描述": None, "复现场景": None, "预期行为": None, "错误堆栈": None}
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
        product_name=meta.get("product_name") or None,
        voice_source=meta.get("voice_source") or None,
        more_details=more_details,
    )


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


def _resolve_value(value: str) -> str:
    """If value starts with '@', treat the rest as a file path and read its content.

    This allows the Agent to safely pass multi-line or special-character content
    without shell escaping issues: write content to a temp file, then pass @filepath.
    """
    if value.startswith("@"):
        path = Path(value[1:])
        try:
            return path.read_text(encoding="utf-8").rstrip("\n")
        except (OSError, UnicodeDecodeError) as e:
            print(f"警告: 无法读取文件 {path}: {e}", file=sys.stderr)
            return value
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="VoD Markdown IO")
    subparsers = parser.add_subparsers(dest="command", required=True)

    id_p = subparsers.add_parser("generate-id", help="generate feedback ID")
    id_p.add_argument("--prefix", required=True, help="ID prefix (VOD or REQ)")
    id_p.add_argument("--feedbacks-dir", "--feedback-dir", required=True, type=Path, dest="feedbacks_dir", help="feedbacks directory")

    write_p = subparsers.add_parser("write-feedback", help="write feedback record to markdown file")
    write_p.add_argument("--feedback-id", default="", help="feedback ID (auto-generated if omitted)")
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
    write_p.add_argument("--voice-source", default="", help="voice source attribution for VOD sound issues")
    write_p.add_argument("--recurrence-count", type=int, default=1, help="recurrence count")
    write_p.add_argument("--dedup-key", default="", help="dedup key")
    write_p.add_argument("--annotations", nargs="*", default=[], help="annotation labels (e.g. skill:xxx category:yyy severity:high)")
    write_p.add_argument("--output", required=True, type=Path, help="output file or directory (if directory, filename is auto-generated as {feedback_id}.md)")

    args = parser.parse_args()

    if args.command == "generate-id":
        feedback_id = generate_id(args.prefix, args.feedbacks_dir)
        print(feedback_id)
    elif args.command == "write-feedback":
        if args.feedback_id:
            feedback_id = args.feedback_id
        else:
            feedback_id = generate_id("VOD", args.output if args.output.is_dir() else args.output.parent)

        # Resolve output path: if output is a directory, auto-generate filename
        output_path = args.output
        if output_path.is_dir() or (not output_path.suffix and not output_path.exists()):
            output_path = output_path / f"{feedback_id}.md"

        feedback = FeedbackRecord(
            feedback_id=feedback_id,
            feedback_type=FeedbackType(args.feedback_type),
            timestamp=_parse_iso_timestamp(args.timestamp) if args.timestamp else datetime.now(),
            session_id=args.session_id,
            platform=args.platform,
            confidence=args.confidence,
            status=FeedbackStatus(args.status),
            product_name=args.product_name or None,
            voice_source=args.product_name or None,
            error_type=_resolve_value(args.error_type) or None,
            error_message=_resolve_value(args.error_message) or None,
            error_stack=_resolve_value(args.error_stack) or None,
            user_intent=_resolve_value(args.user_intent) or None,
            agent_action=_resolve_value(args.agent_action) or None,
            user_expected=_resolve_value(args.user_expected) or None,
            problem_description=_resolve_value(args.problem_description) or None,
            occurrence_scenario=_resolve_value(args.occurrence_scenario) or None,
            expected_behavior=_resolve_value(args.expected_behavior) or None,
            recurrence_count=args.recurrence_count,
            dedup_key=args.dedup_key or None,
            annotations=args.annotations,
        )
        write_feedback_md(feedback, output_path)
        sanitize_file(output_path)
        import json as _json
        print(_json.dumps({"feedback_id": feedback.feedback_id, "file": str(output_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
