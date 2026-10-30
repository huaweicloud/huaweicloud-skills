"""
源端下载阶段（私网）— 通过 Squid 代理从跳板机 HTTP 服务下载安装包。

公网用 ObsDownloadPhase（OBS 签名 URL 直下），私网用本阶段（Squid 代理中转）。

流程:
  1. WinRM 传输 Download-Agent.ps1 到源端
  2. 源端通过 Squid 代理访问跳板机 HTTP 服务下载安装包
"""
from __future__ import annotations

import logging
from pathlib import Path

from phases.base_phase import BasePhase, MigrationContext

logger = logging.getLogger(__name__)


class SourceDownloadPhase(BasePhase):
    """私网源端下载阶段 — 通过 Squid 代理下载安装包。"""

    def __init__(self):
        super().__init__("SourceDownloadPhase")

    def precheck(self, ctx: MigrationContext) -> bool:
        return ctx.winrm_executor is not None and ctx.config is not None

    def execute(self, ctx: MigrationContext) -> str:
        cfg = ctx.config
        exe = ctx.winrm_executor

        ps_script = Path(cfg.proxyopt.base_dir) / "source" / "Download-Agent.ps1"
        if not ps_script.exists():
            return f"脚本不存在: {ps_script}"

        source_dir = cfg.source_download_dir
        remote_script = f"{source_dir}\\sandbox_download.ps1"
        r = exe.transfer_file(str(ps_script), remote_script)
        if not r.success:
            return f"脚本传输失败: {r.stderr}"

        proxy_host = cfg.sms_agent.proxy_host or cfg.sandbox_host or cfg.proxy_server.host
        proxy_port = cfg.proxy_server.squid_port
        sandbox_host = cfg.sandbox_host or cfg.proxy_server.host
        http_port = cfg.proxy_server.http_server_port

        ps_cmd = (
            f"& '{remote_script}' "
            f"-DownloadDir '{source_dir}' "
            f"-ProxyHost {proxy_host} -ProxyPort {proxy_port} "
            f"-SandboxHost {sandbox_host} -SandboxPort {http_port}"
        )
        logger.info("执行源端下载: %s", ps_cmd[:120])
        r = exe.run_ps(ps_cmd, timeout=cfg.timeout.file_transfer)
        if not r.success:
            return f"下载执行失败: {r.stderr[:300]}"

        return "安装包已通过 Squid 代理下载到源端"

    def verify(self, ctx: MigrationContext) -> bool:
        """验证安装包已下载到源端。

        exe 模式仅需 sms_agent；autoit 模式额外需要 autoit 安装包。
        """
        exe = ctx.winrm_executor
        source_dir = ctx.config.source_download_dir
        check_names = ["sms_agent"]
        mode = getattr(ctx.config.sms_agent, "configure_mode", "exe")
        if mode == "autoit":
            check_names.append("autoit")
        for name in check_names:
            pkg = ctx.config.download.packages.get(name)
            if not pkg:
                continue
            remote_path = f"{source_dir}\\{pkg.local_name}"
            if not exe.file_exists(remote_path):
                return False
        return True