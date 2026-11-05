"""md_io.py round-trip 与内容校验回归测试(#114 问题1/2、#116 问题1/5/6/10)。

自包含: 只依赖标准库与 pytest, 通过 sys.path 引入同 skill 的 scripts 目录。
运行: python -m pytest <SKILL_DIR>/tests/test_md_io_roundtrip.py -v
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
MD_IO = SCRIPTS_DIR / "md_io.py"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import md_io  # noqa: E402
from models import FeedbackRecord, FeedbackType  # noqa: E402

TRACEBACK = (
    'Traceback (most recent call last):\n'
    '  File "a.py", line 1, in <module>\n'
    '    boom()\n'
    'ValueError: x'
)
AGENT_ACTION = "Run vod --debug\n  then inspect .vod/feedbacks\n  and report"


def make_record(**overrides) -> FeedbackRecord:
    data = {
        "feedback_id": "VOD-20260101-0001",
        "feedback_type": FeedbackType.ERROR,
        "timestamp": datetime(2026, 1, 1, 0, 0, 0),
        "session_id": "session-1",
        "platform": "generic",
    }
    data.update(overrides)
    return FeedbackRecord(**data)


def write_then_read(record: FeedbackRecord, path: Path) -> FeedbackRecord:
    md_io.write_feedback_md(record, path)
    return md_io.read_feedback_md(path)


def write_text_exact(path: Path, text: str, newline: str | None = None) -> None:
    """按指定换行策略写文本(测试夹具)。

    用 open() 而不是 Path.write_text(newline=...)：后者是 Python 3.10 才加入的参数，
    而本套件也会在 Python 3.9 的 skill QA 运行器上执行（#929 测试报告 BUG-1）。
    """
    with open(path, "w", encoding="utf-8", newline=newline) as handle:
        handle.write(text)


def cli(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(MD_IO), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
        env=env,
    )


# ---------------------------------------------------------------------------
# round-trip: error_stack / agent_action 多行字段(#116 问题1)
# ---------------------------------------------------------------------------

def test_multiline_fields_roundtrip(tmp_path: Path) -> None:
    record = make_record(error_stack=TRACEBACK, agent_action=AGENT_ACTION)
    back = write_then_read(record, tmp_path / "VOD-20260101-0001.md")

    assert back.error_stack == TRACEBACK
    assert back.agent_action == AGENT_ACTION


def test_roundtrip_is_idempotent_over_cycles(tmp_path: Path) -> None:
    """写入 → 读回 → 再写入 → 再读回, 字段值不得改变(不得累积缩进)。"""
    record = make_record(error_stack=TRACEBACK, agent_action=AGENT_ACTION)
    path = tmp_path / "VOD-20260101-0001.md"

    previous = record
    for cycle in range(3):
        current = write_then_read(previous, path)
        assert current.error_stack == TRACEBACK, f"error_stack drifted at cycle {cycle}"
        assert current.agent_action == AGENT_ACTION, f"agent_action drifted at cycle {cycle}"
        previous = current


def test_content_own_indentation_preserved(tmp_path: Path) -> None:
    stack = "  indented first line\n    deeper\nlast"
    record = make_record(error_stack=stack, agent_action="  action")
    back = write_then_read(record, tmp_path / "VOD-20260101-0001.md")

    assert back.error_stack == stack
    assert back.agent_action == "  action"


@pytest.mark.parametrize("indent", ["", "  ", "    ", "\t"])
def test_reader_accepts_any_fence_indent(tmp_path: Path, indent: str) -> None:
    """回归(#116 问题1): 读取端曾硬编码剥离 2 空格。

    围栏缩进为 4 时每条内容行读回会多出 2 个空格, 为 0 时则会丢掉 2 个空格。
    人工编辑/外部写入的 md(SKILL.md Phase 2 允许)都可能使用其它缩进。
    """
    body = "\n".join(indent + line if line else "" for line in TRACEBACK.split("\n"))
    action_body = "\n".join(indent + line if line else "" for line in AGENT_ACTION.split("\n"))
    document = (
        "# VoD Feedback Record\n\n"
        "## Error Information\n"
        "- **error_type**: command_failure\n"
        "- **error_stack**:\n"
        f"{indent}```\n{body}\n{indent}```\n\n"
        "## Context\n"
        "- **user_intent**: run the tool\n"
        "- **agent_action**:\n"
        f"{indent}```\n{action_body}\n{indent}```\n"
    )
    path = tmp_path / "VOD-20260101-0001.md"
    write_text_exact(path, document, newline="\n")

    back = md_io.read_feedback_md(path)
    assert back.error_stack == TRACEBACK
    assert back.agent_action == AGENT_ACTION


def test_composite_error_stack_roundtrip(tmp_path: Path) -> None:
    """error_stack 会被 _build_error_stack 包成【问题描述】等小节, 各小节边界不得丢字符。"""
    stack = "  at com.x.Y.z(Y.java:10)\n    at com.x.Main.main(Main.java:5)\n  caused by: NPE  "
    record = make_record(
        problem_description="Real problem description",
        occurrence_scenario="Open the page and click export",
        expected_behavior="Export succeeds",
        error_stack=stack,
    )
    back = write_then_read(record, tmp_path / "VOD-20260101-0001.md")

    assert back.error_stack == stack
    assert back.problem_description == "Real problem description"
    assert back.occurrence_scenario == "Open the page and click export"
    assert back.expected_behavior == "Export succeeds"


def test_composite_without_stack_does_not_accumulate(tmp_path: Path) -> None:
    """只有【问题描述】时, 读回不得把复合串当成 error_stack 而反复自我嵌套。"""
    record = make_record(problem_description="Real problem description")
    path = tmp_path / "VOD-20260101-0001.md"

    first = write_then_read(record, path)
    assert first.error_stack is None
    assert first.problem_description == "Real problem description"

    second = write_then_read(first, path)
    assert second.error_stack is None
    assert second.problem_description == "Real problem description"


LEGACY_ERROR_STACKS = [
    # 验证员 F1 的 3 个样例: 非复合, 正文里恰好含【…】标记
    "【问题描述】 appears inside a raw log line\nsecond line",
    'Traceback (most recent call last):\n  File "a.py", line 1\n【问题描述】\nboom()',
    "log line\n【复现场景】\nmore log",
    # 其余含标记但非复合的形态
    "line1 see 【错误堆栈】 below\nline2",
    "【错误堆栈】",
    "【问题描述】",
]


@pytest.mark.parametrize("stack", LEGACY_ERROR_STACKS)
def test_legacy_error_stack_with_embedded_marker_is_preserved(tmp_path: Path, stack: str) -> None:
    """回归(task-6 / F1): 非复合 error_stack 里出现【…】时不得被复合分支吞掉。

    旧文件/手改文件可能把带【…】的日志整段放进 error_stack; 只有
    `_build_error_stack` 写出的复合体才允许拆分(见 test_composite_* 系列)。
    """
    record = make_record(error_stack=stack)
    path = tmp_path / "VOD-20260101-0001.md"

    first = write_then_read(record, path)
    assert first.error_stack == stack, "旧格式 error_stack 被静默丢弃"
    # 不得被误当成复合体把内容搬进 problem_description / occurrence_scenario 等字段
    assert first.problem_description is None
    assert first.occurrence_scenario is None
    assert first.expected_behavior is None

    # 再写回、再读, 仍逐字节稳定
    second = write_then_read(first, path)
    assert second.error_stack == stack
    assert second.problem_description is None
    assert second.occurrence_scenario is None
    assert second.expected_behavior is None


@pytest.mark.parametrize(
    "value,expected",
    [
        ("【问题描述】\nReal problem description", True),
        ("【错误堆栈】\nboom()", True),
        ("Traceback\n【错误堆栈】\nboom()", True),
        ("【复现场景】\nraw stack", True),
        ("", False),
        ("【问题描述】 appears inside a raw log line\nsecond line", False),
        ("Traceback\n【问题描述】\nboom()", False),
        ("log line\n【复现场景】\nmore log", False),
        ("line1 see 【错误堆栈】 below\nline2", False),
        ("plain stack\n  at foo()", False),
    ],
)
def test_is_composite_error_stack(value: str, expected: bool) -> None:
    """复合体判据: 首行即小节标题, 或存在整行【错误堆栈】小节标题。"""
    assert md_io._is_composite_error_stack(value) is expected


def test_blank_lines_and_internal_fences_roundtrip(tmp_path: Path) -> None:
    stack = "line1\n\n```\ninner fence\n```\n\nline2"
    record = make_record(error_stack=stack, agent_action="")
    path = tmp_path / "VOD-20260101-0001.md"

    first = write_then_read(record, path)
    assert first.error_stack == stack
    second = write_then_read(first, path)
    assert second.error_stack == stack


def test_crlf_content_normalized_to_lf_and_stable(tmp_path: Path) -> None:
    """Windows 上写入会把 CRLF 叠加成空行; 读回应稳定为 LF 且可重复。"""
    record = make_record(error_stack="line1\r\nline2")
    path = tmp_path / "VOD-20260101-0001.md"

    first = write_then_read(record, path)
    assert first.error_stack == "line1\nline2"
    assert b"\r\n" not in path.read_bytes()
    second = write_then_read(first, path)
    assert second.error_stack == "line1\nline2"


def test_other_fields_survive_roundtrip(tmp_path: Path) -> None:
    record = make_record(
        error_type="command_failure",
        error_message="boom",
        user_intent="export a report",
        user_expected="the export finishes",
        product_name="OBS",
        voice_source="user-voice",
        confidence=0.75,
        dedup_key="session-1:export:command_failure",
        annotations=["skill:obs", "severity:high"],
        problem_description="Real problem description",
    )
    back = write_then_read(record, tmp_path / "VOD-20260101-0001.md")

    assert back.feedback_id == record.feedback_id
    assert back.feedback_type == record.feedback_type
    assert back.timestamp == record.timestamp
    assert back.session_id == record.session_id
    assert back.platform == record.platform
    assert back.error_type == "command_failure"
    assert back.error_message == "boom"
    assert back.user_intent == "export a report"
    assert back.user_expected == "the export finishes"
    assert back.product_name == "OBS"
    assert back.voice_source == "user-voice"
    assert back.confidence == pytest.approx(0.75)
    assert back.dedup_key == "session-1:export:command_failure"
    assert back.annotations == ["skill:obs", "severity:high"]
    assert back.problem_description == "Real problem description"


# ---------------------------------------------------------------------------
# 内容校验(#116 问题10)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {"problem_description": ""},
        {"problem_description": "test"},
        {"problem_description": "hello"},
        {"problem_description": "TEST"},
        {"problem_description": "  test  "},
        {"problem_description": "test."},
        {"problem_description": "test123"},
        {"problem_description": "测试"},
        {"problem_description": "你好"},
        {"problem_description": "n/a"},
        {"problem_description": "   "},
        {"error_message": "hi"},
        {"error_stack": "none"},
        {"problem_description": "test", "error_message": "hello"},
        {"problem_description": "test", "agent_action": "hi", "user_intent": "无"},
        {"problem_description": "test test"},
    ],
)
def test_validate_content_rejects_empty_or_minimal(overrides: dict) -> None:
    record = make_record(**overrides)
    assert md_io._validate_content(record) is not None


@pytest.mark.parametrize(
    "overrides",
    [
        {"problem_description": "OBS bucket creation fails with 403"},
        {"error_message": "NullPointerException when exporting the report"},
        {"error_stack": TRACEBACK},
        {"problem_description": "test passes but the export never finishes"},
        {"user_intent": "bar chart legend is missing"},
        {"problem_description": "无法创建桶"},
    ],
)
def test_validate_content_accepts_meaningful(overrides: dict) -> None:
    record = make_record(**overrides)
    assert md_io._validate_content(record) is None


def test_cli_rejects_minimal_content(tmp_path: Path) -> None:
    result = cli(
        "write-feedback", "--feedback-id", "VOD-20260101-0001", "--feedback-type", "error",
        "--timestamp", "2026-01-01T00:00:00", "--session-id", "s1",
        "--problem-description", "test", "--output", str(tmp_path / "feedbacks"), cwd=tmp_path,
    )
    assert result.returncode == 1
    assert "Minimal content" in result.stderr
    assert not (tmp_path / "feedbacks").exists()


def test_cli_rejects_minimal_content_spread_across_fields(tmp_path: Path) -> None:
    result = cli(
        "write-feedback", "--feedback-id", "VOD-20260101-0001", "--feedback-type", "error",
        "--timestamp", "2026-01-01T00:00:00", "--session-id", "s1",
        "--problem-description", "test", "--error-message", "hello",
        "--output", str(tmp_path / "feedbacks"), cwd=tmp_path,
    )
    assert result.returncode == 1
    assert "Minimal content" in result.stderr
    assert not (tmp_path / "feedbacks").exists()


def test_cli_rejects_empty_content(tmp_path: Path) -> None:
    result = cli(
        "write-feedback", "--feedback-id", "VOD-20260101-0001", "--feedback-type", "error",
        "--timestamp", "2026-01-01T00:00:00", "--session-id", "s1",
        "--output", str(tmp_path / "feedbacks"), cwd=tmp_path,
    )
    assert result.returncode == 1
    assert "Empty feedback content" in result.stderr
    assert not (tmp_path / "feedbacks").exists()


def test_cli_rejected_auto_id_leaves_no_file(tmp_path: Path) -> None:
    """校验失败时必须留不下任何文件, 包括自动 ID 的占位文件。"""
    result = cli(
        "write-feedback", "--feedback-type", "error",
        "--timestamp", "2026-01-01T00:00:00", "--session-id", "s1",
        "--problem-description", "test", "--output", str(tmp_path / "feedbacks"), cwd=tmp_path,
    )
    assert result.returncode == 1
    assert not (tmp_path / "feedbacks").exists()
    assert list(tmp_path.glob("VOD-*.md")) == []


def test_cli_multiline_at_file_roundtrip(tmp_path: Path) -> None:
    stack_file = tmp_path / "stack.txt"
    action_file = tmp_path / "action.txt"
    write_text_exact(stack_file, TRACEBACK + "\n", newline="")
    write_text_exact(action_file, AGENT_ACTION + "\n", newline="")
    feedbacks = tmp_path / "feedbacks"

    result = cli(
        "write-feedback", "--feedback-id", "VOD-20260101-0001", "--feedback-type", "error",
        "--timestamp", "2026-01-01T00:00:00", "--session-id", "s1",
        "--problem-description", "Real problem description",
        "--error-stack", "@" + str(stack_file), "--agent-action", "@" + str(action_file),
        "--output", str(feedbacks), cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr

    back = md_io.read_feedback_md(feedbacks / "VOD-20260101-0001.md")
    assert back.error_stack == TRACEBACK
    assert back.agent_action == AGENT_ACTION


def test_cli_auto_id_creates_file_inside_target_dir(tmp_path: Path) -> None:
    """--output 指向尚不存在的目录时, ID/文件必须落在该目录内, 不在父目录留垃圾。"""
    feedbacks = tmp_path / "feedbacks"
    result = cli(
        "write-feedback", "--feedback-type", "error",
        "--timestamp", "2026-01-01T00:00:00", "--session-id", "s1",
        "--problem-description", "Real problem description",
        "--output", str(feedbacks), cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr

    created = sorted(path.name for path in feedbacks.glob("VOD-*.md"))
    assert len(created) == 1
    assert list(tmp_path.glob("VOD-*.md")) == []


def test_cli_in_session_dedup_increments_recurrence(tmp_path: Path) -> None:
    """同 session + error_type 在窗口内重复写入 → 递增 recurrence_count, 不新建文件(UTC 时间戳)。"""
    feedbacks = tmp_path / "feedbacks"
    timestamp = datetime.now(timezone.utc).isoformat()
    base = [
        "write-feedback", "--feedback-type", "error", "--timestamp", timestamp,
        "--session-id", "s1", "--error-type", "command_failure",
        "--problem-description", "Real problem description", "--output", str(feedbacks),
    ]

    first = cli(*base, cwd=tmp_path)
    assert first.returncode == 0, first.stderr
    second = cli(*base, cwd=tmp_path)
    assert second.returncode == 0, second.stderr
    assert '"deduplicated": true' in second.stdout

    files = sorted(feedbacks.glob("VOD-*.md"))
    assert len(files) == 1
    assert md_io.read_feedback_md(files[0]).recurrence_count == 2
    assert list(tmp_path.glob("VOD-*.md")) == []


def test_cli_in_session_dedup_naive_local_timestamp(tmp_path: Path) -> None:
    """回归(#114 问题1 / #116 问题6): issue 原始手动测试。

    `--timestamp` 传 naive 本地时间(datetime.now().isoformat(), 即 `date -Iseconds`
    的形态)连写两次: 修改前 naive 被当作 UTC(东八区 age≈-28800s), 生成 2 个文件;
    修复后必须只有 1 个文件且 recurrence_count == 2。
    """
    feedbacks = tmp_path / "feedbacks"
    timestamp = datetime.now().isoformat()
    base = [
        "write-feedback", "--feedback-type", "error", "--timestamp", timestamp,
        "--session-id", "s1", "--error-type", "command_failure",
        "--problem-description", "Real problem description", "--output", str(feedbacks),
    ]

    first = cli(*base, cwd=tmp_path)
    assert first.returncode == 0, first.stderr
    second = cli(*base, cwd=tmp_path)
    assert second.returncode == 0, second.stderr
    assert '"deduplicated": true' in second.stdout

    files = sorted(feedbacks.glob("VOD-*.md"))
    assert len(files) == 1, [path.name for path in files]
    assert md_io.read_feedback_md(files[0]).recurrence_count == 2
    assert list(tmp_path.glob("VOD-*.md")) == []


@pytest.mark.parametrize("naive", [True, False])
def test_find_dedup_candidate_hits_naive_and_utc_timestamps(tmp_path: Path, naive: bool) -> None:
    """naive 本地时间与 UTC 感知时间都应命中窗口内的同名反馈。"""
    feedbacks = tmp_path / "feedbacks"
    timestamp = datetime.now() if naive else datetime.now(timezone.utc)
    md_io.write_feedback_md(
        make_record(
            timestamp=timestamp,
            session_id="s1",
            error_type="command_failure",
            problem_description="Real problem description",
        ),
        feedbacks / "VOD-20260101-0001.md",
    )

    assert md_io._find_dedup_candidate(feedbacks, "s1", "command_failure", None, 60) is not None


@pytest.mark.parametrize(
    "offset_sec",
    [-86400, -600, 600, 86400],
)
def test_find_dedup_candidate_ignores_out_of_window(tmp_path: Path, offset_sec: int) -> None:
    """窗口(±dedup_window_sec)之外的记录不得命中。"""
    feedbacks = tmp_path / "feedbacks"
    md_io.write_feedback_md(
        make_record(
            timestamp=datetime.now() + timedelta(seconds=offset_sec),
            session_id="s1",
            error_type="command_failure",
            problem_description="Real problem description",
        ),
        feedbacks / "VOD-20260101-0001.md",
    )

    assert md_io._find_dedup_candidate(feedbacks, "s1", "command_failure", None, 60) is None
    # 窗口为 0 时, 哪怕几毫秒前写入的记录也不算命中
    assert md_io._find_dedup_candidate(feedbacks, "s1", "command_failure", None, 0) is None


def test_find_dedup_candidate_key_priority(tmp_path: Path) -> None:
    """键语义不变: 有 dedup_key 用 dedup_key, 否则用 session_id:error_type(两侧对称)。"""
    # 带显式 dedup_key 的记录: 只认同一个 dedup_key, 与 session/error_type 无关
    keyed = tmp_path / "keyed"
    md_io.write_feedback_md(
        make_record(
            timestamp=datetime.now(),
            session_id="s1",
            error_type="e1",
            dedup_key="shared-key",
            problem_description="Real problem description",
        ),
        keyed / "VOD-20260101-0001.md",
    )
    assert md_io._find_dedup_candidate(keyed, "s2", "e2", "shared-key", 60) is not None
    assert md_io._find_dedup_candidate(keyed, "s1", "e1", "other-key", 60) is None
    # 记录自身带 dedup_key 时, 缺省键(session:error_type)与之不相等 → 不命中
    assert md_io._find_dedup_candidate(keyed, "s1", "e1", None, 60) is None

    # 未带 dedup_key 的记录: 用 session_id:error_type 匹配
    plain = tmp_path / "plain"
    md_io.write_feedback_md(
        make_record(
            timestamp=datetime.now(),
            session_id="s1",
            error_type="e1",
            problem_description="Real problem description",
        ),
        plain / "VOD-20260101-0001.md",
    )
    assert md_io._find_dedup_candidate(plain, "s1", "e1", None, 60) is not None
    assert md_io._find_dedup_candidate(plain, "s1", "e2", None, 60) is None
    assert md_io._find_dedup_candidate(plain, "s2", "e1", None, 60) is None


def test_cli_session_limit_blocks_and_leaves_no_file(tmp_path: Path) -> None:
    """超过 max_feedbacks_per_session(默认 5)时必须拒绝, 且不留下占位文件。"""
    feedbacks = tmp_path / "feedbacks"
    for index in range(5):
        result = cli(
            "write-feedback", "--feedback-id", f"VOD-20260101-{index:04d}", "--feedback-type", "error",
            "--timestamp", "2026-01-01T00:00:00", "--session-id", "s1",
            "--error-type", f"error_{index}",
            "--problem-description", f"Real problem description {index}",
            "--output", str(feedbacks), cwd=tmp_path,
        )
        assert result.returncode == 0, result.stderr

    over_limit = cli(
        "write-feedback", "--feedback-type", "error",
        "--timestamp", "2026-01-01T00:00:00", "--session-id", "s1",
        "--error-type", "one_more",
        "--problem-description", "Real problem description, over the limit",
        "--output", str(feedbacks), cwd=tmp_path,
    )
    assert over_limit.returncode == 1
    assert "Session limit reached" in over_limit.stderr
    assert len(list(feedbacks.glob("VOD-*.md"))) == 5
    assert list(tmp_path.glob("VOD-*.md")) == []
