#!/usr/bin/env python3
"""
step_tracker.py — 迁移步骤追踪器

记录迁移过程中每个环节的:
  - 耗时 (start/end/duration)
  - 阻塞点 (blocking: 等待外部资源、重试、超时等)
  - 问题点 (issue: 非致命异常、警告、降级处理等)

用法:
    tracker = StepTracker()
    tracker.start("ensure_agent")
    ...
    tracker.record_blocking("ensure_agent", "等待源端 Agent 注册超时, 重试 1/3")
    ...
    tracker.record_issue("ensure_agent", "Agent 状态为 UNKNOWN, 删除旧记录后重新推送")
    ...
    tracker.end("ensure_agent", success=True)

    # 获取汇总
    summary = tracker.get_summary()
    # => {
    #     "steps": [
    #         {
    #             "name": "ensure_agent",
    #             "status": "success",
    #             "start_time": 1234567890.0,
    #             "end_time": 1234567895.0,
    #             "duration": 5.0,
    #             "blockings": ["等待源端 Agent 注册超时, 重试 1/3"],
    #             "issues": ["Agent 状态为 UNKNOWN, 删除旧记录后重新推送"],
    #         }, ...
    #     ],
    #     "total_duration": 15.0,
    #     "total_blockings": 1,
    #     "total_issues": 1,
    # }
"""

import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class StepTracker:
    """迁移步骤追踪器

    记录每个迁移环节的耗时、阻塞点和问题点，
    最终汇总输出到迁移报告中。
    """

    def __init__(self):
        self._steps: Dict[str, Dict[str, Any]] = {}
        self._order: List[str] = []
        self._global_start: float = time.time()

    def start(self, step_name: str, metadata: Optional[Dict] = None):
        """标记步骤开始

        Args:
            step_name: 步骤名称 (如 ensure_agent, create_task, migrating)
            metadata: 可选的步骤元数据
        """
        if step_name not in self._steps:
            self._steps[step_name] = {
                "name": step_name,
                "status": "running",
                "start_time": time.time(),
                "end_time": None,
                "duration": 0,
                "blockings": [],
                "issues": [],
                "metadata": metadata or {},
            }
            self._order.append(step_name)
        else:
            # 重新开始已有步骤 (重试场景)
            self._steps[step_name]["start_time"] = time.time()
            self._steps[step_name]["status"] = "running"
            self._steps[step_name]["end_time"] = None

        logger.debug(f"[StepTracker] START: {step_name}")

    def end(self, step_name: str, success: bool = True, error: str = ""):
        """标记步骤结束

        Args:
            step_name: 步骤名称
            success: 是否成功
            error: 失败时的错误信息
        """
        if step_name not in self._steps:
            # 未调用 start 就直接 end, 创建一个零耗时记录
            self._steps[step_name] = {
                "name": step_name,
                "status": "success" if success else "failed",
                "start_time": time.time(),
                "end_time": time.time(),
                "duration": 0,
                "blockings": [],
                "issues": [],
                "metadata": {},
            }
            self._order.append(step_name)
            return

        step = self._steps[step_name]
        step["end_time"] = time.time()
        step["duration"] = round(step["end_time"] - step["start_time"], 2)
        step["status"] = "success" if success else "failed"
        if error:
            step["error"] = error

        logger.debug(
            f"[StepTracker] END: {step_name} -> "
            f"{'success' if success else 'failed'} ({step['duration']}s, "
            f"{len(step['blockings'])} blockings, {len(step['issues'])} issues)"
        )

    def record_blocking(self, step_name: str, description: str, duration: Optional[float] = None):
        """记录阻塞点

        阻塞点: 步骤执行过程中因等待外部资源、重试、超时等导致的暂停。

        Args:
            step_name: 步骤名称
            description: 阻塞描述
            duration: 阻塞持续时间 (秒, 可选)
        """
        if step_name not in self._steps:
            self.start(step_name)

        blocking_entry = {
            "description": description,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if duration is not None:
            blocking_entry["duration"] = round(duration, 2)

        self._steps[step_name]["blockings"].append(blocking_entry)
        logger.info(f"[StepTracker] BLOCKING in {step_name}: {description}")

    def record_issue(self, step_name: str, description: str, severity: str = "warning"):
        """记录问题点

        问题点: 步骤执行过程中遇到的非致命异常、警告、降级处理等。

        Args:
            step_name: 步骤名称
            description: 问题描述
            severity: 严重程度 (warning, error, info)
        """
        if step_name not in self._steps:
            self.start(step_name)

        issue_entry = {
            "description": description,
            "severity": severity,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        self._steps[step_name]["issues"].append(issue_entry)
        if severity == "error":
            logger.warning(f"[StepTracker] ISSUE(error) in {step_name}: {description}")
        else:
            logger.info(f"[StepTracker] ISSUE({severity}) in {step_name}: {description}")

    def get_step(self, step_name: str) -> Optional[Dict[str, Any]]:
        """获取单个步骤的追踪记录"""
        return self._steps.get(step_name)

    def get_summary(self) -> Dict[str, Any]:
        """获取所有步骤的汇总

        Returns:
            {
                "steps": [...],
                "total_duration": float,
                "total_blockings": int,
                "total_issues": int,
                "step_count": int,
            }
        """
        steps = []
        total_blockings = 0
        total_issues = 0
        total_duration = 0.0

        for name in self._order:
            step = self._steps[name]
            # 如果步骤还在运行中, 计算当前耗时
            if step["status"] == "running":
                step["duration"] = round(time.time() - step["start_time"], 2)

            steps.append(step)
            total_blockings += len(step["blockings"])
            total_issues += len(step["issues"])
            total_duration += step["duration"]

        return {
            "steps": steps,
            "total_duration": round(total_duration, 2),
            "total_blockings": total_blockings,
            "total_issues": total_issues,
            "step_count": len(steps),
        }

    def get_console_text(self) -> str:
        """生成控制台友好的步骤追踪文本"""
        summary = self.get_summary()
        lines = [
            "",
            "=" * 60,
            "  步骤追踪明细",
            "=" * 60,
        ]

        for step in summary["steps"]:
            status_icon = {
                "success": "✓",
                "failed": "✗",
                "running": "⏳",
            }.get(step["status"], "?")

            lines.append(
                f"  {status_icon} {step['name']:25s} "
                f"{step['duration']:8.2f}s  "
                f"[{step['status']}]"
            )

            # 输出阻塞点
            for blk in step["blockings"]:
                dur_str = f" ({blk['duration']}s)" if "duration" in blk else ""
                lines.append(f"    ⏸ BLOCKING: {blk['description']}{dur_str}")

            # 输出问题点
            for iss in step["issues"]:
                lines.append(f"    ⚠ ISSUE({iss['severity']}): {iss['description']}")

        lines.append("-" * 60)
        lines.append(
            f"  总耗时: {summary['total_duration']:.2f}s  |  "
            f"阻塞点: {summary['total_blockings']}  |  "
            f"问题点: {summary['total_issues']}"
        )
        lines.append("=" * 60)

        return "\n".join(lines)
