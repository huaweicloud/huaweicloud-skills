"""
私网批量编排器 — 并发迁移多台源端 Windows 主机（经跳板机代理）。

复用 Phase 类，不内联阶段逻辑:
  Py3: SourceDownloadPhase → InstallAutoItPhase → InstallAgentPhase → ConfigurePhase → VerifyPhase
  Py2: SourceDownloadPhase → InstallAgentPhase → ConfigurePy2Phase → VerifyPhase

gost 多端口转发: 每台源端分配独立 gost 监听端口 (15985+i)
"""
from __future__ import annotations

import logging

from core.executor.ssh_executor import SSHExecutor
from core.executor.winrm_executor import WinRMExecutor
from core.batch_base import BaseBatchOrchestrator, HostState
from phases.source_download_phase import SourceDownloadPhase
from phases.install_autoit_phase import InstallAutoItPhase
from phases.install_agent_phase import InstallAgentPhase
from phases.configure_phase import ConfigurePhase
from phases.configure_py2_phase import ConfigurePy2Phase
from phases.verify_phase import VerifyPhase

logger = logging.getLogger(__name__)

GOST_BASE_PORT = 15985


class PrivateBatchOrchestrator(BaseBatchOrchestrator):
    """私网批量编排器 — 经跳板机 gost 端口转发。"""

    def __init__(self, *args, proxies: list | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._ssh: SSHExecutor | None = None
        self._proxies = proxies or []

    def _proxy_conf(self) -> dict:
        """代理连接配置：优先环境变量 Host_Information 提供的代理主机，回退 config.proxy_server。"""
        from core.hostinfo import first_proxy_config
        pcfg = first_proxy_config(self._proxies)
        if pcfg:
            return {
                "host": pcfg["host"],
                "ssh_port": pcfg["ssh_port"],
                "username": pcfg["username"],
                "password": pcfg["password"],
            }
        cfg = self._config
        return {
            "host": cfg.proxy_server.host,
            "ssh_port": cfg.proxy_server.ssh_port,
            "username": cfg.proxy_server.ssh_username,
            "password": cfg.proxy_server.ssh_password,
        }

    def _build_phases(self):
        is_py2 = self._config.sms_agent.agent_version == "py2"

        if is_py2:
            # Py2: 命令行配置，无需 AutoIt
            logger.info("私网批量模式 Agent 版本: Py2 (命令行界面)")
            return [
                ("download", SourceDownloadPhase()),
                ("install_agent", InstallAgentPhase(installer_on_source=True)),
                ("configure", ConfigurePy2Phase(proxy_mode=True)),
                ("verify", VerifyPhase()),
            ]
        else:
            # Py3: 图形界面配置
            mode = self._config.sms_agent.configure_mode
            phases = [("download", SourceDownloadPhase()),
                      ("install_agent", InstallAgentPhase(installer_on_source=True)),
                      ("configure", ConfigurePhase(proxy_mode=True)),
                      ("verify", VerifyPhase())]
            if mode == "autoit":
                logger.info("私网批量模式 Agent 版本: Py3 (configure_mode=autoit)")
                phases.insert(1, ("install_autoit", InstallAutoItPhase(installer_on_source=True)))
            else:
                logger.info("私网批量模式 Agent 版本: Py3 (configure_mode=exe)，纯 exe 直传")
            return phases

    def _build_executor(self, host: str, state: HostState) -> WinRMExecutor:
        pconf = self._proxy_conf()
        return WinRMExecutor(
            host=pconf["host"],
            port=state.gost_port,
            username=state.username,
            password=state.password,
            transport=self._config.source.winrm_transport,
            use_ssl=self._config.source.winrm_use_ssl,
        )

    def _pre_run(self) -> None:
        """分配 gost 端口 + 配置端口转发。"""
        for i, (host, state) in enumerate(self._states.items()):
            if state.gost_port == 0:
                state.gost_port = GOST_BASE_PORT + i
        self._save_state()
        self._setup_gost_forwarding()

    def _post_run(self) -> None:
        if self._ssh:
            self._ssh.close()

    def _result_title(self) -> str:
        return "私网批量迁移汇总"

    def _setup_gost_forwarding(self) -> None:
        cfg = self._config
        if getattr(cfg.proxyopt, "skip", False):
            logger.info("gost 端口转发已跳过（proxyopt.skip=true）")
            return

        logger.info("配置跳板机 gost 多端口转发...")
        pconf = self._proxy_conf()
        try:
            self._ssh = SSHExecutor(
                host=pconf["host"],
                port=pconf["ssh_port"],
                username=pconf["username"],
                password=pconf["password"],
            )
        except Exception as e:
            logger.warning("跳板机 SSH 连接失败: %s（假设 gost 已手动配置）", e)
            return

        gost_parts = []
        for host, state in self._states.items():
            # 私网场景转发目标应为源端内网 IP（gost 运行在跳板机内网侧）
            target = state.private_ip or host
            gost_parts.append(f"-L tcp://:{state.gost_port}/{target}:{state.winrm_port}")
        gost_cmd = f"nohup gost {' '.join(gost_parts)} > /tmp/gost_batch.log 2>&1 &"

        self._ssh.run_cmd("pkill -f 'gost.*-L' 2>/dev/null; sleep 1", timeout=10)
        r = self._ssh.run_cmd(gost_cmd, timeout=30)
        if r.success:
            logger.info("gost 多端口转发已启动: %d 个端口", len(self._states))
        else:
            logger.warning("gost 启动失败: %s（假设已手动配置）", r.stderr[:200])
