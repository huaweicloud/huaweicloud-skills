"""
AutoIt 安装阶段 — 在源端 Windows 上安装 AutoIt v3。

支持 .exe 和 .zip 两种安装包格式：
  .exe: 直接静默安装
  .zip: 先用 PowerShell Expand-Archive 解压，再找到 exe 静默安装

公网模式：安装包从沙箱 WinRM 传到源端 → 静默安装
私网模式：安装包已由 proxyopt 下载到源端 → 直接安装
"""
from __future__ import annotations

import logging
from pathlib import Path

from core.exceptions import ConfigError
from phases.base_phase import BasePhase, MigrationContext

logger = logging.getLogger(__name__)


class InstallAutoItPhase(BasePhase):
    """
    安装 AutoIt v3。

    installer_on_source=True: 安装包已在源端（私网 proxyopt 已下载）
    installer_on_source=False: 需要从沙箱传输到源端（公网）
    """

    def __init__(self, installer_on_source: bool = False):
        super().__init__("InstallAutoItPhase")
        self._installer_on_source = installer_on_source

    def precheck(self, ctx: MigrationContext) -> bool:
        return ctx.winrm_executor is not None

    def execute(self, ctx: MigrationContext) -> str:
        exe = ctx.winrm_executor
        autoit_exe = ctx.config.autoit.exe_path

        # 检查是否已安装
        if exe.file_exists(autoit_exe):
            logger.info("AutoIt 已安装: %s", autoit_exe)
            ctx.autoit_installed = True
            return "AutoIt 已存在，跳过安装"

        # 确定安装包路径
        source_dir = ctx.config.source_download_dir
        pkg = ctx.config.download.packages.get("autoit")
        if not pkg or not getattr(pkg, "local_name", ""):
            raise ConfigError("download.packages.autoit 未配置 local_name（安装包缺失）")
        installer_name = pkg.local_name
        remote_installer = f"{source_dir}\\{installer_name}"

        if not self._installer_on_source:
            # 公网：从沙箱传输到源端
            local_path = ctx.downloaded_files.get("autoit", "")
            if not local_path or not Path(local_path).exists():
                return "AutoIt 安装包未下载到沙箱"

            logger.info("传输 AutoIt 安装包到源端: %s → %s", local_path, remote_installer)
            r = exe.transfer_file(local_path, remote_installer)
            if not r.success:
                return f"安装包传输失败: {r.stderr}"

        # 判断安装包格式
        if installer_name.lower().endswith(".zip"):
            # zip 格式：先解压，再找 exe 安装
            extract_dir = f"{source_dir}\\autoit_extracted"
            logger.info("解压 AutoIt zip: %s → %s", remote_installer, extract_dir)

            # 清理旧解压目录
            exe.run_cmd(f'if exist "{extract_dir}" rmdir /s /q "{extract_dir}"', timeout=30)
            # 解压
            ps_extract = (
                f"Expand-Archive -Path '{remote_installer}' "
                f"-DestinationPath '{extract_dir}' -Force"
            )
            r = exe.run_ps(ps_extract, timeout=120)
            if not r.success:
                return f"AutoIt zip 解压失败: {r.stderr}"

            # 查找解压后的 exe 安装程序
            ps_find_exe = (
                f"Get-ChildItem -Path '{extract_dir}' -Filter '*.exe' -Recurse | "
                f"Select-Object -First 1 -ExpandProperty FullName"
            )
            r = exe.run_ps(ps_find_exe, timeout=30)
            if not r.success or not r.stdout.strip():
                return f"解压后未找到 exe 安装程序: {r.stderr}"

            actual_installer = r.stdout.strip()
            logger.info("找到 AutoIt 安装程序: %s", actual_installer)
        else:
            # exe 格式：直接安装
            actual_installer = remote_installer

        # 静默安装
        silent_args = ctx.config.autoit.silent_install_args
        logger.info("静默安装 AutoIt: %s %s", actual_installer, silent_args)
        r = exe.run_cmd(
            f'"{actual_installer}" {silent_args}',
            timeout=ctx.config.timeout.install_wait,
        )
        if not r.success:
            return f"AutoIt 安装失败: {r.stderr}"

        ctx.autoit_installed = True
        return "AutoIt 安装完成"

    def verify(self, ctx: MigrationContext) -> bool:
        return ctx.winrm_executor.file_exists(ctx.config.autoit.exe_path)
