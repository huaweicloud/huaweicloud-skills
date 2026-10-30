"""
场景基类 — 编排阶段链。
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from phases.base_phase import BasePhase, MigrationContext, PhaseStatus
from core.callbacks import Callbacks

logger = logging.getLogger(__name__)


@dataclass
class ScenarioResult:
    name: str
    phase_results: list
    total_duration: float = 0.0
    success: bool = False

    def summary(self) -> str:
        lines = [
            f"\n{'=' * 60}",
            f"场景: {self.name}",
            f"总耗时: {self.total_duration:.1f}s",
            "-" * 40,
        ]
        for r in self.phase_results:
            icon = {"success": "✅", "failed": "❌", "skipped": "⏭️"}[r.status.value]
            detail = f" — {r.detail}" if r.detail else ""
            err = f" [错误: {r.error}]" if r.error else ""
            lines.append(f"  {icon} {r.name} ({r.duration:.1f}s){detail}{err}")
        lines.append("-" * 40)
        lines.append(f"结果: {'成功' if self.success else '失败'}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """序列化为可 JSON 化的字典（供外部脚本消费）。"""
        return {
            "scenario": self.name,
            "success": self.success,
            "total_duration": round(self.total_duration, 2),
            "phases": [r.to_dict() for r in self.phase_results],
            "failed_phase": next(
                (r.name for r in self.phase_results if r.status.value == "failed"), None
            ),
            "errors": [
                {"phase": r.name, "error": r.error}
                for r in self.phase_results
                if r.error
            ],
        }


class BaseScenario:
    """场景基类 — 编排阶段链。"""

    def __init__(self, name: str):
        self.name = name
        self._phases: list[BasePhase] = []
        self.callbacks: Callbacks = Callbacks()

    def add_phase(self, phase: BasePhase) -> "BaseScenario":
        self._phases.append(phase)
        return self

    def run(self, ctx: MigrationContext) -> ScenarioResult:
        start = time.time()
        logger.info("#" * 60)
        logger.info("# 场景开始: %s (%d 个阶段)", self.name, len(self._phases))
        logger.info("#" * 60)

        # 单台模式：将回调注入 context，供阶段内进度回调使用
        ctx.callbacks = self.callbacks

        self.callbacks.fire_scenario_start({
            "scenario": self.name, "phases": len(self._phases),
        })

        results = []
        for phase in self._phases:
            self.callbacks.fire_phase_start(phase)
            result = phase.run(ctx)
            results.append(result)
            self.callbacks.fire_phase_complete(result)
            if result.status == PhaseStatus.FAILED:
                logger.error("阶段 %s 失败，终止场景", phase.name)
                break

        duration = time.time() - start
        success = all(r.status != PhaseStatus.FAILED for r in results)

        logger.info("#" * 60)
        logger.info("# 场景结束: %s → %s (%.1fs)", self.name, "成功" if success else "失败", duration)
        logger.info("#" * 60)

        result = ScenarioResult(self.name, results, duration, success)
        self.callbacks.fire_scenario_complete(result.to_dict())

        return result
