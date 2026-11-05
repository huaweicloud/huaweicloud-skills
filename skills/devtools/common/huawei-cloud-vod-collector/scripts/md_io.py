from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
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
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Invalid timestamp '{ts}': {e}. "
            f"Expected ISO 8601 format (e.g. 2026-01-01T00:00:00)"
        )


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
    # 动态位数(至少 4 位): 超过 9999 后不再被固定 4 位正则漏扫
    width = 4
    with open(lock_path, "wb") as lock_file:
        _lock_file(lock_file)
        try:
            pattern = re.compile(rf"^{prefix}-{today}-(\d{{4,}})\.md$")
            max_seq = 0
            for f in directory.iterdir():
                m = pattern.match(f.name)
                if m:
                    seq = int(m.group(1))
                    if seq > max_seq:
                        max_seq = seq
            # 锁内原子“认领”ID: O_EXCL 创建占位文件, 并发进程不会分配到同一 ID
            next_seq = max_seq + 1
            while True:
                width = max(4, len(str(next_seq)))
                stem = f"{prefix}-{today}-{next_seq:0{width}d}"
                fname = stem + ".md"
                candidate = directory / fname
                try:
                    fd = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    os.close(fd)
                    break
                except FileExistsError:
                    next_seq += 1
        finally:
            _unlock_file(lock_file)
    return stem


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




def _fence_run(line: str) -> int:
    """Length of the leading backtick run on a pure-backtick fence line (>=3), else 0."""
    s = line.strip()
    if not s.startswith("`"):
        return 0
    run = len(s) - len(s.lstrip("`"))
    if s == "`" * run and run >= 3:
        return run
    return 0


def _code_fence(content: str) -> str:
    """Pick a backtick fence longer than any run inside content.

    Content containing ``` would otherwise terminate the fence early and break
    the generated Markdown (and later parsing). Fence length = max_run + 1.
    """
    max_run = 3
    for m in re.finditer(r"`+", content or ""):
        if len(m.group(0)) >= max_run:
            max_run = len(m.group(0)) + 1
    return "`" * max_run


# 多行字段(代码围栏)统一缩进宽度, 与 assets/VOD_FEEDBACKS.md 模板一致
_BLOCK_INDENT = "  "


def _content_lines(value: str) -> list[str]:
    """把字段内容拆成行: CRLF / CR 统一为 LF, 避免 Windows 写文件时换行被叠加。"""
    return re.split(r"\r\n|\r|\n", value)


def _append_fenced_block(lines: list[str], value: str) -> None:
    """按模板缩进写入多行字段的围栏块。

    围栏长度自适应内容中的反引号; 行缩进固定为 _BLOCK_INDENT, 读取端按围栏行
    实际缩进原样剥离, 因此 0/2/4 空格等不同缩进风格都能无损 round-trip(#116 问题1)。
    """
    body_lines = _content_lines(value)
    fence = _code_fence("\n".join(body_lines))
    lines.append(f"{_BLOCK_INDENT}{fence}")
    for body_line in body_lines:
        lines.append(f"{_BLOCK_INDENT}{body_line}")
    lines.append(f"{_BLOCK_INDENT}{fence}")


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
        _append_fenced_block(lines, error_stack_content)
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
        _append_fenced_block(lines, feedback.agent_action)
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

    # newline="\n": 固定 LF 行尾(不随平台转成 CRLF), 保证跨平台 round-trip 与 diff 稳定
    with open(file_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def _normalize_section_header(header: str) -> str:
    return re.sub(r"\s*\(.*?\)\s*$", "", header).strip()


def _parse_metadata_section(text: str, section: str) -> dict[str, str]:
    result: dict[str, str] = {}
    in_section = False
    in_multiline = False
    multiline_key = None
    multiline_lines = []
    in_fence = False
    fence_run = 0
    normalized = _normalize_section_header(section)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        _run = _fence_run(stripped)
        if _run >= 3:
            # 围栏开/关: 关闭需 >= 开启长度, 内容中的短 ``` 不会误关
            if not in_fence:
                in_fence = True
                fence_run = _run
            elif _run >= fence_run:
                in_fence = False
                fence_run = 0
        if not in_fence and stripped.startswith("## "):
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
            if not in_fence and stripped.startswith("- **"):
                result[multiline_key] = "\n".join(multiline_lines).strip()
                in_multiline = False
                multiline_key = None
                multiline_lines = []
                # 不 continue: 让当前行落到下方普通字段解析逻辑, 确保该新字段不被跳过
                # (v6 起显式保证此回归行为; 测试: 多行字段后紧跟新字段可正确解析)
            else:
                # 检查空行是否是字段分隔：空行 + 下一行是 - **
                if stripped == "" and i + 1 < len(lines):
                    next_stripped = lines[i + 1].strip()
                    if not in_fence and next_stripped.startswith("- **"):
                        result[multiline_key] = "\n".join(multiline_lines).strip()
                        in_multiline = False
                        continue
                if in_multiline:
                    multiline_lines.append(line.rstrip("\n"))
                    continue

        if not in_fence and stripped.startswith("- **"):
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


def _strip_block_indent(line: str, indent: int) -> str:
    """剥离围栏块内容行的缩进: 最多剥 indent 个前导空白字符。

    内容自身的额外缩进(堆栈的 at/File 层级)会被保留, 只去掉围栏缩进本身。
    """
    if indent <= 0:
        return line
    i = 0
    while i < indent and i < len(line) and line[i] in " \t":
        i += 1
    return line[i:]


def _extract_code_block_value(text: str, section: str, field: str) -> str | None:
    in_section = False
    in_field = False
    in_code = False
    fence_run = 0
    fence_indent = 0
    code_lines = []
    normalized = _normalize_section_header(section)
    for line in text.split("\n"):
        stripped = line.strip()
        _run = _fence_run(stripped)
        # 开围栏: 遇到 >=3 个反引号的纯围栏行; 该行本身不进入内容
        if not in_code and _run >= 3:
            in_code = True
            fence_run = _run
            fence_indent = len(line) - len(line.lstrip(" \t"))
            continue
        if in_code:
            # 关围栏: 需与开围栏等长或更长; 内容中较短的 ``` 不被误判为关闭
            if _run >= fence_run:
                in_code = False
                fence_run = 0
                fence_indent = 0
                continue
            if in_field:
                # 按围栏行实际缩进剥离, 不再硬编码 2 空格(#116 问题1):
                # 4 空格缩进的文件读回时会多出 2 空格, 0/1 空格则会丢缩进
                code_lines.append(_strip_block_indent(line, fence_indent))
            continue
        if not in_code and stripped.startswith("## "):
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
        if in_field and stripped.startswith("- **"):
            in_field = False
            continue
    if code_lines:
        return "\n".join(code_lines)
    return None


def _extract_multiline_section(text: str, header: str) -> str | None:
    result_lines = []
    in_section = False
    in_fence = False
    fence_run = 0
    normalized = _normalize_section_header(header)
    for line in text.split("\n"):
        stripped = line.strip()
        _run = _fence_run(stripped)
        if _run >= 3:
            if not in_fence:
                in_fence = True
                fence_run = _run
            elif _run >= fence_run:
                in_fence = False
                fence_run = 0
        if not in_fence and stripped.startswith("## "):
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


def _join_section_lines(lines: list[str]) -> str | None:
    """拼接复合 error_stack 的某一小节。

    只丢弃小节末尾的空行(即 _build_error_stack 写出的 "\\n\\n" 分隔行),
    保留首行前导缩进与行尾内容, 避免 round-trip 时缩进/尾随空格丢失(#116 问题1)。
    """
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return None
    return "\n".join(lines)


# _build_error_stack 复合体的小节标题(顺序即拼接顺序, 原始堆栈总在最后)
_COMPOSITE_MARKERS = ("【问题描述】", "【复现场景】", "【预期行为】", "【错误堆栈】")


def _is_composite_error_stack(value: str) -> bool:
    """判断 error_stack 是否确为 _build_error_stack 写出的复合体。

    复合体的形态固定: 小节标题独立成行, 且首行必为某个标题(_build_error_stack 按
    问题描述/复现场景/预期行为/错误堆栈 顺序拼接, 原始堆栈总是最后一段)。因此只在
    「首行即小节标题」或「存在【错误堆栈】小节标题行」时才按复合体解析。

    否则正文里的【…】只是堆栈内容(旧文件/手改文件), 必须原样保留,
    不能被复合分支吞掉(task-6 / F1: 静默丢数据回归)。
    """
    if not value:
        return False
    if value.split("\n", 1)[0].strip() in _COMPOSITE_MARKERS:
        return True
    return any(line.strip() == "【错误堆栈】" for line in value.split("\n"))


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
    in_fence = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
        if not in_fence and stripped.startswith("## "):
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

    if error_stack and _is_composite_error_stack(error_stack):
        sections = {"问题描述": None, "复现场景": None, "预期行为": None, "错误堆栈": None}
        current_key = None
        current_lines = []
        for line in error_stack.split("\n"):
            m = re.match(r"^【(.+?)】$", line.strip())
            if m and m.group(1) in sections:
                if current_key is not None:
                    sections[current_key] = _join_section_lines(current_lines)
                current_key = m.group(1)
                current_lines = []
                continue
            if current_key is not None:
                current_lines.append(line)
        if current_key is not None:
            sections[current_key] = _join_section_lines(current_lines)
        if sections["问题描述"]:
            problem_description = sections["问题描述"]
        if sections["复现场景"]:
            occurrence_scenario = sections["复现场景"]
        if sections["预期行为"]:
            expected_behavior = sections["预期行为"]
        # 复合体: error_stack 以【错误堆栈】小节为准(避免重写时整段自我累积)。
        # 若复合体本就没有堆栈小节(只有【问题描述】等), 则为 None;
        # 但若只剩一个空的【错误堆栈】标题, 说明它其实不是复合体 → 保留原文。
        if sections["错误堆栈"] is not None:
            error_stack = sections["错误堆栈"]
        elif any(sections[key] for key in ("问题描述", "复现场景", "预期行为")):
            error_stack = None

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


_SKILL_DIR_MD = Path(__file__).resolve().parent.parent
_CONFIG_FILE_MD = _SKILL_DIR_MD / "assets" / "config.yaml"


def _load_config() -> dict:
    if not _CONFIG_FILE_MD.exists():
        return {}
    try:
        import yaml
        text = _CONFIG_FILE_MD.read_text(encoding="utf-8")
        config = yaml.safe_load(text)
        return config or {}
    except Exception:
        return {}


def _count_session_feedbacks(feedbacks_dir: Path, session_id: str) -> int:
    if not feedbacks_dir.exists():
        return 0
    count = 0
    for f in feedbacks_dir.glob("VOD-*.md"):
        try:
            existing = read_feedback_md(f)
            if existing.session_id == session_id:
                count += 1
        except Exception:
            continue
    return count


def _to_utc(ts: datetime) -> datetime:
    """把时间戳统一为 UTC 感知时间: naive 值按**本地时区**解释, 不再当作 UTC。

    naive 时间戳通常来自 `datetime.now()` / `date -Iseconds`(本地时间)。直接当成
    UTC 会让东八区的时间戳"看起来在未来"(age ≈ -28800s), 去重窗口永不命中
    (#114 问题1: 相同 session_id + error_type 连写两次生成两个文件 / #116 问题6)。
    """
    if ts.tzinfo is None:
        # astimezone() 对 naive datetime 按本地时区解释并附上本地时区(DST 安全)
        ts = ts.astimezone()
    return ts.astimezone(timezone.utc)


def _find_dedup_candidate(
    feedbacks_dir: Path,
    session_id: str,
    error_type: str | None,
    dedup_key: str | None,
    dedup_window_sec: int,
) -> Path | None:
    if not feedbacks_dir.exists():
        return None
    now = datetime.now(timezone.utc)
    new_key = dedup_key or f"{session_id}:{error_type or ''}"
    for f in sorted(feedbacks_dir.glob("VOD-*.md"), reverse=True):
        try:
            existing = read_feedback_md(f)
        except Exception:
            continue
        existing_key = existing.dedup_key or f"{existing.session_id}:{existing.error_type or ''}"
        if existing_key != new_key:
            continue
        if existing.timestamp:
            age = (now - _to_utc(existing.timestamp)).total_seconds()
            # 负向放宽到同样一个窗口: 容忍写入端时钟略快产生的未来时间戳;
            # 超出 ±dedup_window_sec 的旧记录仍不命中
            if -dedup_window_sec <= age <= dedup_window_sec:
                return f
    return None


_MINIMAL_CONTENT = {"test", "hello", "hi", "测试", "你好", "无", "none", "n/a", "na", ".",
                    "test123", "testing", "todo", "tbd", "xxx", "foo", "bar", "foobar", "asdf"}

# token 边界上的装饰性标点: "test." / "（无）" 等价于 "test" / "无"
_TOKEN_TRIM_CHARS = "。，、.,!！?？:：;；'\"`()（）[]【】<>《》-—_*#"


def _placeholder_token(token: str) -> bool:
    """判断单个 token 是否只是占位内容(忽略首尾标点与结尾数字)。"""
    trimmed = token.strip(_TOKEN_TRIM_CHARS).strip().lower()
    if not trimmed:
        return True
    if trimmed in _MINIMAL_CONTENT:
        return True
    return re.sub(r"\d+$", "", trimmed) in _MINIMAL_CONTENT


def _validate_content(feedback: FeedbackRecord) -> str | None:
    fields = [
        feedback.problem_description,
        feedback.error_message,
        feedback.error_stack,
        feedback.user_intent,
        feedback.agent_action,
        feedback.occurrence_scenario,
        feedback.expected_behavior,
    ]
    all_content = " ".join(field.strip() for field in fields if field and field.strip())
    if not all_content:
        return "Empty feedback content - no meaningful fields provided"
    # 空白折叠后比较: "test\n\ntest" 与 "test test" 视为同一最小内容
    lower = re.sub(r"\s+", " ", all_content).strip().lower()
    if lower in _MINIMAL_CONTENT:
        return f"Minimal content '{lower}' rejected - provide meaningful feedback"
    # 最小内容可能被拆到多个字段: --problem-description test --error-message hello
    tokens = lower.split(" ")
    if tokens and all(_placeholder_token(token) for token in tokens):
        return f"Minimal content '{lower}' rejected - provide meaningful feedback"
    if len(lower) < 3:
        return f"Content too short ({len(lower)} chars) - provide meaningful feedback"
    return None


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
        if not args.session_id or not args.session_id.strip():
            print("错误: --session-id must not be empty", file=sys.stderr)
            sys.exit(1)

        if args.confidence < 0.0 or args.confidence > 1.0:
            print(f"错误: --confidence must be between 0.0 and 1.0, got {args.confidence}", file=sys.stderr)
            sys.exit(1)

        try:
            timestamp = _parse_iso_timestamp(args.timestamp) if args.timestamp else datetime.now()
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)

        # Resolve output path: if output is a directory, auto-generate filename
        output_path = args.output
        dir_target = output_path.is_dir() or (not output_path.suffix and not output_path.exists())
        feedbacks_dir = output_path if dir_target else output_path.parent

        feedback = FeedbackRecord(
            feedback_id=args.feedback_id,
            feedback_type=FeedbackType(args.feedback_type),
            timestamp=timestamp,
            session_id=args.session_id,
            platform=args.platform,
            confidence=args.confidence,
            status=FeedbackStatus(args.status),
            product_name=args.product_name or None,
            voice_source=args.voice_source or None,
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

        # Content validation: 必须在生成/占位文件之前, 拒绝时不留任何文件(#116 问题10)
        validation_error = _validate_content(feedback)
        if validation_error:
            print(f"错误: {validation_error}", file=sys.stderr)
            sys.exit(1)

        # Load config for session limit and dedup
        config = _load_config()
        storage_cfg = config.get("storage", {})
        capture_cfg = config.get("capture", {})
        max_per_session = storage_cfg.get("max_feedbacks_per_session", 5)
        dedup_window = capture_cfg.get("dedup_window_sec", 60)

        # In-session dedup check
        dedup_candidate = _find_dedup_candidate(
            feedbacks_dir, args.session_id, feedback.error_type, feedback.dedup_key, dedup_window
        )
        if dedup_candidate:
            try:
                existing = read_feedback_md(dedup_candidate)
                existing.recurrence_count = existing.recurrence_count + 1
                write_feedback_md(existing, dedup_candidate)
                custom_patterns = config.get("sanitizer", {}).get("custom_patterns", [])
                sanitize_file(dedup_candidate, custom_patterns=custom_patterns)
                import json as _json
                print(_json.dumps({
                    "feedback_id": existing.feedback_id,
                    "file": str(dedup_candidate),
                    "deduplicated": True,
                    "recurrence_count": existing.recurrence_count,
                }, ensure_ascii=False))
                return
            except Exception as e:
                print(f"警告: 去重更新失败，将创建新文件: {e}", file=sys.stderr)

        # Session limit check
        session_count = _count_session_feedbacks(feedbacks_dir, args.session_id)
        if session_count >= max_per_session:
            print(
                f"错误: Session limit reached ({session_count}/{max_per_session}). "
                f"Cannot create more feedbacks for this session.",
                file=sys.stderr,
            )
            sys.exit(1)

        # 落盘前才生成 ID: 与去重/超限/校验等提前返回路径无关, 不会留下占位文件。
        # ID 在 feedbacks_dir 内生成(目录不存在时也会被创建), 序号只统计目标目录。
        if not args.feedback_id:
            feedback.feedback_id = generate_id("VOD", feedbacks_dir)
        if dir_target:
            output_path = feedbacks_dir / f"{feedback.feedback_id}.md"

        write_feedback_md(feedback, output_path)
        custom_patterns = config.get("sanitizer", {}).get("custom_patterns", [])
        sanitize_file(output_path, custom_patterns=custom_patterns)
        import json as _json
        print(_json.dumps({"feedback_id": feedback.feedback_id, "file": str(output_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
