"""
验证阶段 — 轮询 SmsAgent_Info.log 检测 5 个注册标记。

标记 (Py2 agent 实际日志文本):
  [0] "as/sk"              — AK/SK 校验
  [1] "upload os info"     — 上传 OS 信息
  [2] "upload source info" — 上传源端信息
  [3] "schedule task"      — 启动定时任务
  [4] "heart beat"         — 启动心跳

成功判定:
  markers >= 3 + 无错误日志 = 成功
  markers >= 3 + 有错误日志 = 成功(需复查)
  markers < 3 = 失败

实测修复:
  - 标记匹配从 regex 改为子串匹配，与 configure_py2_phase.py _check_registration() 保持一致
  - -Tail 200 → 500，避免日志量大时遗漏早期标记
  - GBK 解码已在 WinRMExecutor.run_ps 中统一处理
"""
from __future__ import annotations

import logging
import re
import time

from phases.base_phase import BasePhase, MigrationContext

logger = logging.getLogger(__name__)

# 注册标记子串（统一从 core.markers 引用，避免与 ConfigurePy2Phase 重复）
from core.markers import MARKER_SUBSTRINGS as _MARKER_SUBSTRINGS

_ERROR_PATTERNS = [
    r"fatal\s+error",
    r"unhandled\s+exception",
    r"registration\s+failed",
    r"upload\s+failed",
    r"config\s+error",
    r"auth\s+failed",
    r"invalid\s+ak.*sk",
    r"connection\s+refused",
]

# 致命错误模式 — 出现在日志尾部(最近100行)时判定注册失败，
# 否则即使历史出现(Py3 AutoIt 修复前的一次失败尝试)也只算“需复查”，不阻断成功。
_FATAL_PATTERNS = [
    r"invalid\s+ak.*sk",
    r"auth\s+failed",
    r"registration\s+failed",
    r"upload\s+failed",
]


class VerifyPhase(BasePhase):
    """注册验证阶段 — 轮询日志检测注册成功。"""

    def __init__(self):
        super().__init__("VerifyPhase")

    def precheck(self, ctx: MigrationContext) -> bool:
        return ctx.winrm_executor is not None

    def execute(self, ctx: MigrationContext) -> str:
        cfg = ctx.config
        log_file = cfg.sms_agent.log_file
        max_wait = cfg.timeout.verify_max_wait
        logger.info("开始轮询日志: %s (最长等待 %ds)", log_file, max_wait)

        elapsed = 0
        last_content = ""
        poll_count = 0
        while elapsed < max_wait:
            # 读取日志内容 — 用 PowerShell Get-Content -Tail 500 避免大日志截断
            ps_cmd = (
                f"if (Test-Path '{log_file}') {{ "
                f"Get-Content -Path '{log_file}' -Tail 500 -ErrorAction SilentlyContinue "
                f"}} else {{ Write-Output '' }}"
            )
            r = ctx.winrm_executor.run_ps(ps_cmd, timeout=30)
            content = r.stdout if r.success else ""

            if content and content != last_content:
                last_content = content
                markers = self._check_markers(content)
                has_error = self._check_errors(content)

                marker_count = sum(markers.values())
                logger.info("日志检测 (%ds): 标记 %d/5 %s | 错误=%s",
                            elapsed, marker_count,
                            {k: v for k, v in markers.items() if v},
                            has_error)

                ctx.log_markers = markers

                if marker_count >= 3:
                    # 致命错误判定：仅当错误仍出现在日志尾部（最近100行）才算失败，
                    # 避免早期 invalid AK/SK 被 AutoIt 修复后仍误报失败（原逻辑“需复查=成功”会掩盖未注册）。
                    fatal_error = self._check_fatal_errors(content)
                    if fatal_error:
                        ctx.registration_success = False
                        logger.error("注册疑似失败: 日志尾部存在致命错误 (%s)", fatal_error)
                        return f"注册失败 — 标记 {marker_count}/5，尾部致命错误: {fatal_error}"
                    if has_error:
                        ctx.registration_success = True
                        return f"注册成功(需复查) — 标记 {marker_count}/5，有历史错误日志"
                    else:
                        ctx.registration_success = True
                        return f"注册成功 — 标记 {marker_count}/5"

            # 阶段内进度回调（仅单台模式，批量模式 ctx.callbacks=None）
            if ctx.callbacks:
                _mc = sum(ctx.log_markers.values()) if ctx.log_markers else 0
                _md = {k: v for k, v in ctx.log_markers.items() if v} if ctx.log_markers else {}
                ctx.callbacks.fire_phase_progress({
                    "phase": "VerifyPhase",
                    "elapsed": elapsed,
                    "max_wait": max_wait,
                    "markers": _mc,
                    "marker_details": _md,
                })

            # 优化：前3次1s快速检测，之后5s间隔
            current_interval = 1 if poll_count < 3 else 5
            time.sleep(current_interval)
            elapsed += current_interval
            poll_count += 1

        marker_count = sum(ctx.log_markers.values()) if ctx.log_markers else 0
        return f"验证超时 — 标记 {marker_count}/5"

    def verify(self, ctx: MigrationContext) -> bool:
        return ctx.registration_success

    @staticmethod
    def _check_markers(content: str) -> dict:
        """检测 5 个标记，返回 {index: bool}。子串匹配，与 ConfigurePy2Phase 一致。"""
        results = {}
        content_lower = content.lower()
        for i, substr in enumerate(_MARKER_SUBSTRINGS):
            results[i] = substr in content_lower
        return results

    @staticmethod
    def _check_errors(content: str) -> bool:
        """检测是否有错误日志。"""
        content_lower = content.lower()
        return any(re.search(p, content_lower) for p in _ERROR_PATTERNS)

    @staticmethod
    def _tail_window(content: str, lines: int = 100) -> str:
        """取日志的尾部窗口（默认最近100行），用于致命错误判定。"""
        parts = [ln for ln in content.splitlines() if ln.strip()]
        return "\n".join(parts[-lines:]) if parts else content

    @classmethod
    def _check_fatal_errors(cls, content: str) -> str:
        """检测日志尾部窗口是否存在致命错误，返回命中的错误片段（无则返回空串）。"""
        tail = cls._tail_window(content, 100).lower()
        for p in _FATAL_PATTERNS:
            m = re.search(p, tail)
            if m:
                return m.group(0)
        return ""
