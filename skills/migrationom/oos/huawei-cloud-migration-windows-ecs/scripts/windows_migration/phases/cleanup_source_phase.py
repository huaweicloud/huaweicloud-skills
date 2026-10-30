"""
迁移前源端清理阶段 — 清理源端 Windows 迁移残留。

设计（零硬编码）：
  - 清理路径/进程名全部来自 ctx.config（install_dir / agent_exe_name / source_base_dir / source_download_dir）
  - 复用 WinRMPhase 已建立的连接（ctx.winrm_executor），不重复建会话
  - 命令清单来自 cleanup_windows.build_cleanup_commands（单一来源，不重复维护）
  - 幂等：任何一步不存在都按成功跳过；清理失败仅告警不阻断（与 cleanup_windows 行为一致）

放置位置：紧跟 WinRMPhase 之后、下载/安装之前。
  公网：WinRM 直连后即可清；
  私网：Phase1 跳板机已部署（gost 就绪）→ WinRM 经 gost 建立 → 清理 → Agent 全新部署。
  避免：旧 Agent / 旧配置 / 旧计划任务残留导致安装跳过或配置错乱（历史问题根因）。
"""
from __future__ import annotations

import logging

from cleanup_windows import build_cleanup_commands
from phases.base_phase import BasePhase, MigrationContext

logger = logging.getLogger(__name__)


class CleanupSourcePhase(BasePhase):
    """源端残留清理（幂等）。"""

    def __init__(self):
        super().__init__("CleanupSourcePhase")

    def precheck(self, ctx: MigrationContext) -> bool:
        if ctx.winrm_executor is None:
            logger.warning("CleanupSourcePhase: WinRM 未建立，跳过")
            return False
        return True

    def execute(self, ctx: MigrationContext) -> str:
        cfg = ctx.config
        commands = build_cleanup_commands(
            agent_version=cfg.sms_agent.agent_version,
            install_dir=cfg.sms_agent.install_dir,
            agent_exe_name=cfg.sms_agent.agent_exe_name,
            source_base_dir=cfg.source_base_dir,
            source_download_dir=cfg.source_download_dir,
        )
        failed = 0
        for desc, cmd in commands:
            try:
                r = ctx.winrm_executor.run_cmd(cmd, timeout=60)
            except Exception as e:  # noqa: BLE001 - 清理不阻断，仅记录
                logger.warning("清理步骤异常 %s: %s", desc, e)
                failed += 1
                continue
            if not r.success:
                logger.warning("清理步骤失败 %s: %s", desc,
                               (r.stderr or "").strip()[:200])
                failed += 1
            else:
                logger.info("清理步骤完成: %s", desc)
        if failed:
            logger.warning("源端清理有 %d 步异常（不阻断，继续部署）", failed)
        return f"源端残留清理完成（异常 {failed} 步）"

    def verify(self, ctx: MigrationContext) -> bool:
        return True