"""
SMS-Agent 安装阶段 — 在源端 Windows 上安装 SMS-Agent。

公网模式：安装包从沙箱 WinRM 传到源端 → 静默安装
私网模式：安装包已由 proxyopt 下载到源端 → 直接安装

静默安装参数从配置读取（sms_agent.silent_install_args），不硬编码。
"""
from __future__ import annotations

import logging
from pathlib import Path

from core.exceptions import ConfigError
from phases.base_phase import BasePhase, MigrationContext

logger = logging.getLogger(__name__)


class InstallAgentPhase(BasePhase):
    """
    安装 SMS-Agent。

    installer_on_source=True: 安装包已在源端（私网）
    installer_on_source=False: 需要从沙箱传输（公网）
    """

    def __init__(self, installer_on_source: bool = False):
        super().__init__("InstallAgentPhase")
        self._installer_on_source = installer_on_source

    def precheck(self, ctx: MigrationContext) -> bool:
        return ctx.winrm_executor is not None

    def execute(self, ctx: MigrationContext) -> str:
        cfg = ctx.config
        install_dir = cfg.sms_agent.install_dir
        agent_exe_name = cfg.sms_agent.agent_exe_name
        agent_exe = f"{install_dir}\\{agent_exe_name}"

        # 检查是否已安装
        if ctx.winrm_executor.file_exists(agent_exe):
            logger.info("SMS-Agent 已安装: %s", agent_exe)
            ctx.agent_installed = True
            return "SMS-Agent 已存在，跳过安装"

        # 确定安装包路径
        source_dir = cfg.source_download_dir
        pkg = cfg.download.packages.get("sms_agent")
        if not pkg or not getattr(pkg, "local_name", ""):
            raise ConfigError("download.packages.sms_agent 未配置 local_name（安装包缺失）")
        installer_name = pkg.local_name
        remote_installer = f"{source_dir}\\{installer_name}"

        if not self._installer_on_source:
            # 公网：从沙箱传输到源端
            local_path = ctx.downloaded_files.get("sms_agent", "")
            if not local_path or not Path(local_path).exists():
                return "SMS-Agent 安装包未下载到沙箱"

            logger.info("传输 SMS-Agent 安装包到源端: %s → %s", local_path, remote_installer)
            r = ctx.winrm_executor.transfer_file(local_path, remote_installer)
            if not r.success:
                return f"安装包传输失败: {r.stderr}"

        # 静默安装 — 参数从配置读取
        silent_args = cfg.sms_agent.silent_install_args
        logger.info("静默安装 SMS-Agent: %s %s", remote_installer, silent_args)
        r = ctx.winrm_executor.run_cmd(
            f'"{remote_installer}" {silent_args}',
            timeout=cfg.timeout.install_wait,
        )
        if not r.success:
            return f"SMS-Agent 安装失败: {r.stderr}"

        # SMS-Agent 静默安装可能不生成 config 目录，补建 error.cfg
        config_dir = f"{install_dir}\\config"
        error_cfg = f"{config_dir}\\error.cfg"
        ctx.winrm_executor.run_cmd(
            f'mkdir "{config_dir}" 2>nul && if not exist "{error_cfg}" type nul > "{error_cfg}"'
        )
        logger.info("已确保 config\\error.cfg 存在")

        ctx.agent_installed = True
        return "SMS-Agent 安装完成"

    def verify(self, ctx: MigrationContext) -> bool:
        agent_exe = f"{ctx.config.sms_agent.install_dir}\\{ctx.config.sms_agent.agent_exe_name}"
        return ctx.winrm_executor.file_exists(agent_exe)
