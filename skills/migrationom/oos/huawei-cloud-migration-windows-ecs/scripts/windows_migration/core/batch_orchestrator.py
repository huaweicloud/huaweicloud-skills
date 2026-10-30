"""
公网批量编排器 — 并发迁移多台源端 Windows 主机（直连模式）。

复用 Phase 类，不内联阶段逻辑:
  Py3: ObsDownloadPhase → InstallAutoItPhase → InstallAgentPhase → ConfigurePhase → VerifyPhase
  Py2: ObsDownloadPhase → InstallAgentPhase → ConfigurePy2Phase → VerifyPhase
"""
from __future__ import annotations

import logging

from core.executor.winrm_executor import WinRMExecutor
from core.batch_base import BaseBatchOrchestrator, HostState
from phases.obs_download_phase import ObsDownloadPhase
from phases.install_autoit_phase import InstallAutoItPhase
from phases.install_agent_phase import InstallAgentPhase
from phases.configure_phase import ConfigurePhase
from phases.configure_py2_phase import ConfigurePy2Phase
from phases.verify_phase import VerifyPhase

logger = logging.getLogger(__name__)


class BatchOrchestrator(BaseBatchOrchestrator):
    """公网批量编排器 — 直连 WinRM，OBS 签名 URL 下载。"""

    def _build_phases(self):
        is_py2 = self._config.sms_agent.agent_version == "py2"

        if is_py2:
            # Py2: 命令行配置，无需 AutoIt
            logger.info("批量模式 Agent 版本: Py2 (命令行界面)")
            return [
                ("download", ObsDownloadPhase(["sms_agent"])),
                ("install_agent", InstallAgentPhase(installer_on_source=True)),
                ("configure", ConfigurePy2Phase(proxy_mode=False)),
                ("verify", VerifyPhase()),
            ]
        else:
            # Py3: 图形界面配置
            mode = self._config.sms_agent.configure_mode
            if mode == "autoit":
                logger.info("批量模式 Agent 版本: Py3 (configure_mode=autoit)")
                return [
                    ("download", ObsDownloadPhase(["sms_agent", "autoit"])),
                    ("install_autoit", InstallAutoItPhase(installer_on_source=True)),
                    ("install_agent", InstallAgentPhase(installer_on_source=True)),
                    ("configure", ConfigurePhase(proxy_mode=False)),
                    ("verify", VerifyPhase()),
                ]
            logger.info("批量模式 Agent 版本: Py3 (configure_mode=exe)，纯 exe 直传")
            return [
                ("download", ObsDownloadPhase(["sms_agent"])),
                ("install_agent", InstallAgentPhase(installer_on_source=True)),
                ("configure", ConfigurePhase(proxy_mode=False)),
                ("verify", VerifyPhase()),
            ]

    def _build_executor(self, host: str, state: HostState) -> WinRMExecutor:
        return WinRMExecutor(
            host=host,
            port=state.winrm_port,
            username=state.username,
            password=state.password,
            transport=self._config.source.winrm_transport,
            use_ssl=self._config.source.winrm_use_ssl,
        )
