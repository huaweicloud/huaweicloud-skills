"""跨会话去重与通知渠道的回归测试。

覆盖 issue:
  #114 问题5  notify() 必须在解析凭据之前判断有无待发送反馈
  #114 问题6  deliver() 必须在解析凭据之前判断 feedback 文件是否存在
  #114 问题11 / #116 问题11  跨会话去重(dedup-scan)必须真实可用
  #116 问题12  webhook / email 通知渠道必须有实现
"""

import json
import os
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import md_io
import vod_deliver
from models import FeedbackRecord, FeedbackStatus, FeedbackType


# ---------------------------------------------------------------- fixtures

@pytest.fixture(autouse=True)
def _clean_credential_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """确保测试不会读到真实凭据: 既无 env token, 也没有 auth.toml。"""
    monkeypatch.delenv(vod_deliver._ATOMGIT_TOKEN_ENV, raising=False)
    monkeypatch.setenv(vod_deliver._ATOMGIT_HOME_ENV, str(tmp_path / "empty-atomcode"))


def _make_feedback(
    feedbacks_dir: Path,
    feedback_id: str,
    session_id: str,
    error_type: str,
    error_message: str,
    status: FeedbackStatus = FeedbackStatus.OPEN,
) -> Path:
    path = feedbacks_dir / f"{feedback_id}.md"
    record = FeedbackRecord(
        feedback_id=feedback_id,
        feedback_type=FeedbackType.ERROR,
        timestamp=datetime.now(),
        session_id=session_id,
        platform="test",
        error_type=error_type,
        error_message=error_message,
        problem_description=error_message,
        confidence=0.9,
        status=status,
    )
    md_io.write_feedback_md(record, path)
    return path


@pytest.fixture
def feedbacks_dir(tmp_path: Path) -> Path:
    d = tmp_path / "feedbacks"
    d.mkdir()
    return d


# ------------------------------------------------- 跨会话去重 (#114/#116 问题11)

def test_dedup_scan_flags_cross_session_duplicate(feedbacks_dir: Path) -> None:
    _make_feedback(
        feedbacks_dir, "VOD-20261103-0001", "session-a", "timeout",
        "Error 504 gateway timeout while creating bucket demo-bucket",
        FeedbackStatus.PROMOTED,
    )
    _make_feedback(
        feedbacks_dir, "VOD-20261103-0002", "session-b", "timeout",
        "Error 504 gateway timeout while creating bucket demo-bucket",
    )

    result = vod_deliver.scan_cross_session_duplicates(feedbacks_dir, "VOD-20261103-0002")

    assert result["success"] is True
    assert result["scanned"] == 2
    assert result["candidates"], "跨会话同签名反馈必须被判为重复候选"
    candidate = result["candidates"][0]
    assert candidate["id"] == "VOD-20261103-0001"
    assert candidate["signature_match"] is True
    assert candidate["is_strong_duplicate"] is True
    assert result["should_deliver"] is False
    # 供 Agent 做 LLM 语义判定用的提示词必须存在
    assert "VOD-20261103-0002" in result["llm_prompt"]


def test_dedup_scan_ignores_same_session(feedbacks_dir: Path) -> None:
    _make_feedback(
        feedbacks_dir, "VOD-20261103-0001", "session-a", "timeout",
        "Error 504 gateway timeout while creating bucket demo-bucket",
        FeedbackStatus.PROMOTED,
    )
    _make_feedback(
        feedbacks_dir, "VOD-20261103-0002", "session-a", "timeout",
        "Error 504 gateway timeout while creating bucket demo-bucket",
    )

    result = vod_deliver.scan_cross_session_duplicates(feedbacks_dir, "VOD-20261103-0002")

    assert result["candidates"] == []
    assert result["should_deliver"] is True


def test_dedup_scan_without_target_reports_pairs(feedbacks_dir: Path) -> None:
    _make_feedback(
        feedbacks_dir, "VOD-20261103-0001", "session-a", "timeout",
        "Error 504 gateway timeout while creating bucket demo-bucket",
        FeedbackStatus.PROMOTED,
    )
    _make_feedback(
        feedbacks_dir, "VOD-20261103-0002", "session-b", "timeout",
        "Error 504 gateway timeout while creating bucket demo-bucket",
    )

    result = vod_deliver.scan_cross_session_duplicates(feedbacks_dir)

    assert result["target"] is None
    assert len(result["candidates"]) >= 1
    candidate = result["candidates"][0]
    # 最近 N 条按 mtime 倒序, 两条互为重复(谁作为 duplicate_of 取决于顺序)
    assert {candidate["id"], candidate["duplicate_of"]} == {
        "VOD-20261103-0001",
        "VOD-20261103-0002",
    }
    assert candidate["signature_match"] is True


def test_dedup_scan_missing_target_is_structured_error(feedbacks_dir: Path) -> None:
    result = vod_deliver.scan_cross_session_duplicates(feedbacks_dir, "VOD-20261103-9999")

    assert result["success"] is False
    assert "not found" in result["error"]


def test_deliver_refuses_strong_duplicate_before_credentials(feedbacks_dir: Path) -> None:
    """#114 问题11: 命中强重复时在解析凭据之前就短路(本测试环境无任何可用凭据)。"""
    _make_feedback(
        feedbacks_dir, "VOD-20261103-0001", "session-a", "timeout",
        "Error 504 gateway timeout while creating bucket demo-bucket",
        FeedbackStatus.PROMOTED,
    )
    _make_feedback(
        feedbacks_dir, "VOD-20261103-0002", "session-b", "timeout",
        "Error 504 gateway timeout while creating bucket demo-bucket",
    )

    result = vod_deliver.deliver_feedback("VOD-20261103-0002", feedbacks_dir)

    assert result["success"] is False
    assert result["error"] == "duplicate_suspected"
    assert result["duplicate_of"] == "VOD-20261103-0001"


def test_deliver_skip_dedup_reaches_credential_step(feedbacks_dir: Path) -> None:
    """--skip-dedup 时应继续走到凭据解析(此处无凭据 → need_login)。"""
    _make_feedback(
        feedbacks_dir, "VOD-20261103-0001", "session-a", "timeout",
        "Error 504 gateway timeout while creating bucket demo-bucket",
        FeedbackStatus.PROMOTED,
    )
    _make_feedback(
        feedbacks_dir, "VOD-20261103-0002", "session-b", "timeout",
        "Error 504 gateway timeout while creating bucket demo-bucket",
    )

    result = vod_deliver.deliver_feedback("VOD-20261103-0002", feedbacks_dir, skip_dedup=True)

    assert result["success"] is False
    assert result.get("need_login") is True


# --------------------------------------------- 凭据解析顺序 (#114 问题5/6)

def test_deliver_missing_file_returns_not_found_not_login(feedbacks_dir: Path) -> None:
    result = vod_deliver.deliver_feedback("VOD-20261103-9999", feedbacks_dir)

    assert result["success"] is False
    assert "Feedback file not found" in result["error"]
    assert result.get("need_login") is not True


def test_notify_without_pending_never_resolves_token(
    feedbacks_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#114 问题5: 空目录 notify 直接返回空列表, 连凭据解析函数都不会被调用。"""

    def _explode(*args, **kwargs):
        raise AssertionError("notify() must not resolve credentials when there is nothing to send")

    monkeypatch.setattr(vod_deliver, "_resolve_atomgit_token", _explode)

    result = vod_deliver.notify_feedback(feedbacks_dir)

    assert result["success"] is True
    assert result["pending"] == 0
    assert result["sent"] == []


def test_notify_missing_feedback_id_is_empty(feedbacks_dir: Path) -> None:
    result = vod_deliver.notify_feedback(feedbacks_dir, "VOD-20261103-9999")

    assert result["success"] is True
    assert result["pending"] == 0


# ------------------------------------------------ 通知渠道 (#116 问题12)

def test_notify_dry_run_lists_pending(feedbacks_dir: Path) -> None:
    _make_feedback(
        feedbacks_dir, "VOD-20261103-0001", "session-a", "timeout",
        "Error 504 gateway timeout while creating bucket demo-bucket",
    )

    result = vod_deliver.notify_feedback(feedbacks_dir, dry_run=True)

    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["pending"] == 1
    assert result["items"][0]["feedback_id"] == "VOD-20261103-0001"


def test_notify_disabled_channel_reports_error(feedbacks_dir: Path) -> None:
    _make_feedback(
        feedbacks_dir, "VOD-20261103-0001", "session-a", "timeout",
        "Error 504 gateway timeout while creating bucket demo-bucket",
    )

    result = vod_deliver.notify_feedback(feedbacks_dir)

    assert result["success"] is False
    assert "disabled" in result["error"]


def test_notify_webhook_sends_and_is_idempotent(
    feedbacks_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_feedback(
        feedbacks_dir, "VOD-20261103-0001", "session-a", "timeout",
        "Error 504 gateway timeout while creating bucket demo-bucket",
    )

    received: list[dict] = []

    class _Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 - http.server API
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            received.append(json.loads(body))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *args):  # silence test output
            return

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        notification_cfg = {
            "enabled": True,
            "type": "webhook",
            "webhook": {"url": f"http://127.0.0.1:{port}/hook", "headers": {"X-Test": "1"}},
            "retry_policy": {"max_retries": 1, "backoff_base_sec": 0, "backoff_max_sec": 0},
        }
        monkeypatch.setattr(
            vod_deliver, "_load_config",
            lambda: {"delivery": {"channels": {"notification": notification_cfg}}},
        )

        result = vod_deliver.notify_feedback(feedbacks_dir)

        assert result["success"] is True, result
        assert result["sent"] == ["VOD-20261103-0001"]
        assert received and received[0]["feedback_id"] == "VOD-20261103-0001"
        assert received[0]["error_type"] == "timeout"

        # 幂等: 已通知过的反馈不再重复推送
        again = vod_deliver.notify_feedback(feedbacks_dir)
        assert again["pending"] == 0
        assert len(received) == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_notify_failed_webhook_is_reported(feedbacks_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _make_feedback(
        feedbacks_dir, "VOD-20261103-0001", "session-a", "timeout",
        "Error 504 gateway timeout while creating bucket demo-bucket",
    )

    notification_cfg = {
        "enabled": True,
        "type": "webhook",
        "webhook": {"url": "http://127.0.0.1:1/unreachable", "headers": {}},
        "retry_policy": {"max_retries": 0, "backoff_base_sec": 0, "backoff_max_sec": 0},
    }
    monkeypatch.setattr(
        vod_deliver, "_load_config",
        lambda: {"delivery": {"channels": {"notification": notification_cfg}}},
    )

    result = vod_deliver.notify_feedback(feedbacks_dir)

    assert result["success"] is False
    assert result["failed"] == ["VOD-20261103-0001"]


def test_notify_email_requires_configuration(feedbacks_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _make_feedback(
        feedbacks_dir, "VOD-20261103-0001", "session-a", "timeout",
        "Error 504 gateway timeout while creating bucket demo-bucket",
    )

    notification_cfg = {
        "enabled": True,
        "type": "email",
        "email": {"smtp_host": "", "smtp_port": 587, "recipients": []},
        "retry_policy": {"max_retries": 0, "backoff_base_sec": 0, "backoff_max_sec": 0},
    }
    monkeypatch.setattr(
        vod_deliver, "_load_config",
        lambda: {"delivery": {"channels": {"notification": notification_cfg}}},
    )

    result = vod_deliver.notify_feedback(feedbacks_dir, channel="email")

    assert result["success"] is False
    assert "not configured" in result["results"][0]["error"]


# ------------------------------------------- 行尾一致性 (F6)

def test_line_endings_stay_lf_across_cli_writes(feedbacks_dir: Path) -> None:
    """write-feedback → sanitize → update-status 之后文件不得被转成 CRLF。

    Windows 上 write_text() 默认把 '\\n' 转成 os.linesep, 会让同一文件在
    write-feedback / sanitize / update-status 之间 CRLF↔LF 反复翻转。
    """
    import subprocess

    scripts = SKILL_DIR / "scripts"

    def run(*args: str) -> None:
        proc = subprocess.run(
            [sys.executable, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.returncode == 0, proc.stderr

    run(str(scripts / "md_io.py"), "write-feedback",
        "--feedback-type", "error", "--timestamp", "2026-11-03T10:45:00",
        "--session-id", "s-lf", "--error-type", "timeout",
        "--problem-description", "real problem about bucket creation",
        "--output", str(feedbacks_dir))

    files = list(feedbacks_dir.glob("VOD-*.md"))
    assert len(files) == 1
    feedback_file = files[0]
    assert b"\r\n" not in feedback_file.read_bytes()

    run(str(scripts / "vod_sanitize.py"), "file", "--path", str(feedback_file))
    assert b"\r\n" not in feedback_file.read_bytes()

    run(str(scripts / "vod_deliver.py"), "update-status",
        "--feedback-id", feedback_file.stem, "--status", "delivered",
        "--feedbacks-dir", str(feedbacks_dir))
    assert b"\r\n" not in feedback_file.read_bytes()
