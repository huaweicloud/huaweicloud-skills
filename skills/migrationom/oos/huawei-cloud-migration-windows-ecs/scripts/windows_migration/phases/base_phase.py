"""
阶段基类 — 模板方法：precheck → execute → verify。
每个阶段自包含，通过 context 传递状态。
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PhaseStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PhaseResult:
    name: str
    status: PhaseStatus
    duration: float = 0.0
    detail: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        """序列化为可 JSON 化的字典。"""
        return {
            "name": self.name,
            "status": self.status.value,
            "duration": round(self.duration, 2),
            "detail": self.detail,
            "error": self.error,
        }


@dataclass
class MigrationContext:
    """
    迁移上下文 — 阶段间传递状态。
    避免阶段间直接耦合，通过 context 共享数据。
    """
    config: object = None              # MigrateConfig
    winrm_executor: object = None      # WinRMExecutor（直连或 gost）
    winrm_manager: object = None       # WinRMManager
    sandbox_download_dir: str = ""
    source_download_dir: str = ""
    # 阶段产出
    downloaded_files: dict = field(default_factory=dict)  # package_name → local_path
    autoit_installed: bool = False
    agent_installed: bool = False
    registration_success: bool = False
    log_markers: dict = field(default_factory=dict)
    callbacks: object = None              # Callbacks（单台模式设置，批量模式为 None）


class BasePhase(ABC):
    """阶段基类 — 模板方法模式。"""

    def __init__(self, name: str):
        self.name = name

    def run(self, ctx: MigrationContext) -> PhaseResult:
        """模板方法：precheck → execute → verify。"""
        start = time.time()
        logger.info("=" * 60)
        logger.info("阶段开始: %s", self.name)

        # precheck
        try:
            if not self.precheck(ctx):
                logger.info("阶段 %s 跳过（precheck 返回 False）", self.name)
                return PhaseResult(self.name, PhaseStatus.SKIPPED, time.time() - start)
        except Exception as e:
            logger.error("阶段 %s precheck 异常: %s", self.name, e)
            return PhaseResult(self.name, PhaseStatus.FAILED, time.time() - start, error=str(e))

        # execute
        try:
            detail = self.execute(ctx)
        except Exception as e:
            logger.error("阶段 %s 执行异常: %s", self.name, e)
            return PhaseResult(self.name, PhaseStatus.FAILED, time.time() - start, error=str(e))

        # verify
        try:
            ok = self.verify(ctx)
        except Exception as e:
            logger.warning("阶段 %s 验证异常: %s", self.name, e)
            ok = False

        duration = time.time() - start
        status = PhaseStatus.SUCCESS if ok else PhaseStatus.FAILED
        logger.info("阶段结束: %s → %s (%.1fs)", self.name, status.value, duration)

        return PhaseResult(self.name, status, duration, detail=detail or "")

    @abstractmethod
    def precheck(self, ctx: MigrationContext) -> bool:
        """前置检查，返回 False 则跳过此阶段。"""
        ...

    @abstractmethod
    def execute(self, ctx: MigrationContext) -> str:
        """执行阶段逻辑，返回描述信息。"""
        ...

    @abstractmethod
    def verify(self, ctx: MigrationContext) -> bool:
        """验证阶段结果。"""
        ...
