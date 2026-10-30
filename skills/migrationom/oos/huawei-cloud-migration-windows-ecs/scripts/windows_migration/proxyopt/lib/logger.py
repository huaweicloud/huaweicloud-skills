#!/usr/bin/env python3
"""
通用运维日志模块 — 按角色/级别分类，支持文件+控制台双输出。
提供结构化日志，便于事后排查问题。
"""

import os
import sys
import logging


class OpsLogger:
    """
    运维日志器：按角色命名日志文件，按级别分类输出。
    自动创建日志目录，支持文件轮转和彩色控制台输出。
    """

    LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    # ANSI 颜色码
    _COLORS = {
        "DEBUG": "\033[36m",     # cyan
        "INFO": "\033[32m",      # green
        "WARNING": "\033[33m",   # yellow
        "ERROR": "\033[31m",     # red
        "CRITICAL": "\033[35m",  # magenta
    }
    _RESET = "\033[0m"

    def __init__(self, role, log_dir="./logs", level="INFO",
                 file_enabled=True, console_enabled=True, max_bytes=10*1024*1024, backup_count=5):
        """
        Args:
            role: 角色名 (sandbox / squid / gost / source / pipeline)
            log_dir: 日志目录
            level: 最低日志级别
            file_enabled: 是否写文件
            console_enabled: 是否输出到控制台
            max_bytes: 单文件最大字节数
            backup_count: 保留的旧日志文件数
        """
        self.role = role
        self.log_dir = os.path.abspath(log_dir)
        self.level = level

        os.makedirs(self.log_dir, exist_ok=True)

        logger_name = f"proxyopt.{role}"
        self._logger = logging.getLogger(logger_name)
        self._logger.setLevel(self.LEVELS.get(level, logging.INFO))
        self._logger.propagate = False

        # 清除已有 handler（防止重复添加）
        self._logger.handlers.clear()

        fmt = logging.Formatter(
            fmt="%(asctime)s [%(levelname)-8s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        log_file = os.path.join(self.log_dir, f"{role}.log")

        if file_enabled:
            from logging.handlers import RotatingFileHandler
            fh = RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
            )
            fh.setFormatter(fmt)
            self._logger.addHandler(fh)

        if console_enabled:
            ch = logging.StreamHandler(sys.stdout)
            ch.setFormatter(fmt)
            self._logger.addHandler(ch)

    def _emit(self, level, msg, extra=None):
        """内部：输出日志，附加可选的结构化 extra 信息"""
        parts = [msg]
        if extra and isinstance(extra, dict):
            kv = " ".join(f"{k}={v}" for k, v in extra.items())
            parts.append(f"| {kv}")
        self._logger.log(self.LEVELS.get(level, logging.INFO), " ".join(parts))

    def debug(self, msg, extra=None):
        self._emit("DEBUG", msg, extra)

    def info(self, msg, extra=None):
        self._emit("INFO", msg, extra)

    def warning(self, msg, extra=None):
        self._emit("WARNING", msg, extra)

    def error(self, msg, extra=None):
        self._emit("ERROR", msg, extra)

    def critical(self, msg, extra=None):
        self._emit("CRITICAL", msg, extra)

    def step(self, step_name, status="START"):
        """记录流水线步骤状态"""
        self.info(f"[STEP] {step_name} -> {status}")

    def timing(self, operation, elapsed_sec):
        """记录操作耗时"""
        self.info(f"[TIMING] {operation} took {elapsed_sec:.2f}s")

    def get_log_file(self):
        """返回当前日志文件路径"""
        return os.path.join(self.log_dir, f"{self.role}.log")


def get_logger(role="sandbox", config=None, **kwargs):
    """
    工厂函数：根据配置创建日志器。
    如果传入 config (Config 实例)，则从配置文件读取日志参数。
    """
    if config is not None:
        log_dir = config.get("logging.log_dir", "./logs")
        level = config.get("logging.level", "INFO")
        file_enabled = config.get("logging.file_enabled", True)
        console_enabled = config.get("logging.console_enabled", True)
        max_bytes = config.get("logging.max_bytes_mb", 10) * 1024 * 1024
        backup_count = config.get("logging.backup_count", 5)
        return OpsLogger(role, log_dir, level, file_enabled, console_enabled, max_bytes, backup_count)
    return OpsLogger(role, **kwargs)
