#!/usr/bin/env python3
"""
skill_logger.py — 统一日志工具

提供结构化日志，支持:
  - 控制台 + 文件双输出
  - 迁移任务级别日志隔离
  - JSON 格式日志 (便于后续分析)
  - 进度追踪
"""

import os
import sys
import json
import time
import logging
import logging.handlers
from datetime import datetime
from typing import Optional, Dict, Any, List


class JsonFormatter(logging.Formatter):
    """P2-6优化: JSON 结构化日志格式器

    输出格式: {"timestamp": "2025-01-01 12:00:00", "level": "INFO", "module": "name", "message": "...", "extra": {...}}
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        # 合并 extra 字段
        if hasattr(record, "json_data"):
            try:
                log_entry["extra"] = json.loads(record.json_data)
            except (json.JSONDecodeError, TypeError):
                log_entry["extra"] = str(record.json_data)
        # 异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False, default=str)


class OperationTimer:
    """P2-6优化: 操作计时器，自动记录耗时

    用法:
        with logger.timer("compile_rsync"):
            # 执行操作
            pass
    """

    def __init__(self, logger_instance, operation: str, details: Dict = None):
        self._logger = logger_instance
        self._operation = operation
        self._details = details or {}
        self._start = None

    def __enter__(self):
        self._start = time.time()
        self._logger.step(self._operation, "start", self._details)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self._start
        result = {**self._details, "elapsed_s": round(elapsed, 2)}
        if exc_type is None:
            self._logger.step(self._operation, "done", result)
            self._logger._record_timing(self._operation, elapsed, success=True)
        else:
            self._logger.step(self._operation, "failed", result)
            self._logger._record_timing(self._operation, elapsed, success=False)
        return False  # 不抑制异常


class MigrationLogger:
    """迁移日志管理器"""

    def __init__(
        self,
        log_dir: str = "/var/log/migration-private",
        task_id: str = None,
        level: int = logging.INFO,
        json_format: bool = False,
    ):
        """
        Args:
            log_dir: 日志目录
            task_id: 迁移任务 ID (用于日志文件命名)
            level: 日志级别
            json_format: 是否使用 JSON 格式
        """
        self.log_dir = log_dir
        self.task_id = task_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.json_format = json_format

        # P2-6优化: 操作计时记录
        self._timing_records: List[Dict[str, Any]] = []

        os.makedirs(log_dir, exist_ok=True)

        self.log_file = os.path.join(log_dir, f"migration_{self.task_id}.log")
        self.error_file = os.path.join(log_dir, f"migration_{self.task_id}_error.log")

        self._setup_logger(level)

    def _setup_logger(self, level: int):
        """配置 logger"""
        self.logger = logging.getLogger(f"migration.{self.task_id}")
        self.logger.setLevel(level)
        self.logger.handlers.clear()

        # 控制台 handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        console_handler.setFormatter(console_fmt)
        self.logger.addHandler(console_handler)

        # 文件 handler (所有日志)
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_file, maxBytes=50 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(level)
        if self.json_format:
            # P2-6优化: JSON 结构化日志格式
            file_fmt = JsonFormatter()
        else:
            file_fmt = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        file_handler.setFormatter(file_fmt)
        self.logger.addHandler(file_handler)

        # 错误文件 handler
        error_handler = logging.handlers.RotatingFileHandler(
            self.error_file, maxBytes=20 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_fmt)
        self.logger.addHandler(error_handler)

    def info(self, msg: str, extra: Dict = None):
        self.logger.info(msg, extra=self._extra(extra))

    def warning(self, msg: str, extra: Dict = None):
        self.logger.warning(msg, extra=self._extra(extra))

    def error(self, msg: str, extra: Dict = None):
        self.logger.error(msg, extra=self._extra(extra))

    def debug(self, msg: str, extra: Dict = None):
        self.logger.debug(msg, extra=self._extra(extra))

    def _extra(self, extra: Dict = None) -> Dict:
        if extra is None:
            return {}
        if self.json_format:
            return {"json_data": json.dumps(extra, ensure_ascii=False, default=str)}
        return extra

    def step(self, step_name: str, status: str = "start", details: Dict = None):
        """记录迁移步骤"""
        msg = f"[STEP] {step_name} - {status}"
        if details:
            msg += f" | {json.dumps(details, ensure_ascii=False, default=str)}"
        self.info(msg)

    def progress(self, current: int, total: int, task_name: str = ""):
        """记录进度"""
        pct = (current / total * 100) if total > 0 else 0
        bar_len = 30
        filled = int(bar_len * current / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_len - filled)
        msg = f"[PROGRESS] {task_name} |{bar}| {current}/{total} ({pct:.1f}%)"
        self.info(msg)

    # P2-6优化: 操作计时与报告

    def timer(self, operation: str, details: Dict = None) -> OperationTimer:
        """创建操作计时器上下文管理器

        用法:
            with logger.timer("compile_rsync", {"source": "192.168.1.1"}):
                # 执行操作
                pass
        """
        return OperationTimer(self, operation, details)

    def _record_timing(self, operation: str, elapsed: float, success: bool):
        """记录操作耗时 (内部方法)"""
        self._timing_records.append({
            "operation": operation,
            "elapsed_s": round(elapsed, 2),
            "success": success,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })

    def timing_report(self) -> str:
        """生成计时报告摘要

        Returns:
            格式化的计时报告字符串
        """
        if not self._timing_records:
            return "No timing records."

        # 按操作分组统计
        from collections import defaultdict
        groups = defaultdict(list)
        for r in self._timing_records:
            groups[r["operation"]].append(r)

        lines = ["=== Timing Report ==="]
        total_time = 0.0
        for op, records in sorted(groups.items()):
            times = [r["elapsed_s"] for r in records]
            success_count = sum(1 for r in records if r["success"])
            op_total = sum(times)
            total_time += op_total
            lines.append(
                f"  {op}: {len(records)}x, "
                f"total={op_total:.1f}s, avg={op_total/len(records):.1f}s, "
                f"min={min(times):.1f}s, max={max(times):.1f}s, "
                f"success={success_count}/{len(records)}"
            )
        lines.append(f"  --- Total: {total_time:.1f}s ---")
        return "\n".join(lines)

    def get_logger(self) -> logging.Logger:
        return self.logger

    def get_log_path(self) -> str:
        return self.log_file

    def get_error_path(self) -> str:
        return self.error_file


def setup_logger(
    log_dir: str = "/var/log/migration-private",
    task_id: str = None,
    level: str = "INFO",
) -> MigrationLogger:
    """快捷函数: 创建迁移日志器"""
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    return MigrationLogger(
        log_dir=log_dir,
        task_id=task_id,
        level=level_map.get(level.upper(), logging.INFO),
    )
