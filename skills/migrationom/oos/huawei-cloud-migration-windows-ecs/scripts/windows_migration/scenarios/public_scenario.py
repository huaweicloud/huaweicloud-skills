"""
公网迁移场景 — 直连模式。

流程:
  WinRMPhase (直连源端, 检测+开启+保活)
  → ObsDownloadPhase (大文件签名URL直下, 小文件WinRM传输)
  → InstallAutoItPhase (源端已下载, 直接安装) [仅 Py3]
  → InstallAgentPhase (源端已下载, 直接安装)
  → ConfigurePhase (direct 模式, AutoIt GUI) [Py3]
    或 ConfigurePy2Phase (direct 模式, CLI stdin) [Py2]
  → VerifyPhase (日志轮询)

Py3 (Win Server 2012+): AutoIt GUI 配置，需安装 AutoIt v3
Py2 (Win Server 2008/Win7): 命令行配置，无需 AutoIt，跳过 AutoIt 下载安装

关键改进:
  大文件（SMS-Agent 80MB, AutoIt 12MB）不再走沙箱→WinRM base64 中转
  改为 OBS 签名 URL → 源端 Invoke-WebRequest 直下（2.5s vs 30min+）
"""
from __future__ import annotations

import logging

from core.config import MigrateConfig
from core.winrm.manager import WinRMManager
from phases.base_phase import MigrationContext
from phases.cleanup_source_phase import CleanupSourcePhase
from phases.configure_phase import ConfigurePhase
from phases.configure_py2_phase import ConfigurePy2Phase
from phases.obs_download_phase import ObsDownloadPhase
from phases.install_agent_phase import InstallAgentPhase
from phases.install_autoit_phase import InstallAutoItPhase
from phases.verify_phase import VerifyPhase
from phases.winrm_phase import WinRMPhase
from scenarios.base_scenario import BaseScenario

logger = logging.getLogger(__name__)


class PublicScenario(BaseScenario):
    """公网迁移场景 — 直连模式，OBS 签名 URL 直下。"""

    def __init__(self, config: MigrateConfig):
        super().__init__("公网迁移(直连模式)")

        # 构建上下文
        self._ctx = MigrationContext(
            config=config,
            winrm_manager=WinRMManager(config),
            sandbox_download_dir=config.download.sandbox_download_dir,
            source_download_dir=config.source_download_dir,
        )

        # 根据 agent_version 选择阶段链
        is_py2 = config.sms_agent.agent_version == "py2"

        # 编排阶段链
        # WinRM 先建立连接，后续阶段都需要
        self.add_phase(WinRMPhase(via_gost=False))
        # 迁移前必做清理：清源端残留后再全新部署 Agent
        self.add_phase(CleanupSourcePhase())

        if is_py2:
            # Py2: 命令行配置，无需 AutoIt
            logger.info("Agent 版本: Py2 (命令行界面)，跳过 AutoIt 下载安装")
            self.add_phase(ObsDownloadPhase(["sms_agent"]))
            self.add_phase(InstallAgentPhase(installer_on_source=True))
            self.add_phase(ConfigurePy2Phase(proxy_mode=False))
        else:
            # Py3: 图形界面配置
            mode = config.sms_agent.configure_mode
            if mode == "autoit":
                # AutoIt 编译/au3 方式: 下载并安装 AutoIt
                logger.info("Agent 版本: Py3 (configure_mode=autoit)，下载安装 AutoIt + au3 配置")
                self.add_phase(ObsDownloadPhase(["sms_agent", "autoit"]))
                self.add_phase(InstallAutoItPhase(installer_on_source=True))
            else:
                # 纯 exe 方式: 不下载不安装 AutoIt，直接使用本地预编译 exe
                logger.info("Agent 版本: Py3 (configure_mode=exe)，纯 exe 直传配置（无需 AutoIt）")
                self.add_phase(ObsDownloadPhase(["sms_agent"]))
            self.add_phase(InstallAgentPhase(installer_on_source=True))
            self.add_phase(ConfigurePhase(proxy_mode=False))

        # 验证注册
        self.add_phase(VerifyPhase())

    def run(self):
        result = super().run(self._ctx)
        # 清理: 停止 WinRM 保活线程
        try:
            self._ctx.winrm_manager.stop_keepalive()
        except Exception:
            pass
        return result
