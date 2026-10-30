"""
私网迁移场景 — 代理模式（文件服务器部署在代理主机）。

Phase 1: 跳板机一键就绪（deploy_jumpbox.deploy）
  1.1  沙箱    OBS 下载安装包 → proxyopt/downloads/
  1.2  代理主机 同步文件 → /data/downloads（SMS-Agent、configure exe）
  1.3  代理主机 HTTP 8080 文件服务（源端同网段直达，不依赖沙箱入站）
  1.4  代理主机 Squid 3128（热加载部署）
  1.5  代理主机 gost 15985 → 源端 WinRM（systemd 托管）
  1.6  沙箱    preCache 经 Squid 抓代理主机 8080

Phase 2: Agent 部署配置（经 gost 连接源端）
  2.1  WinRMPhase (经 gost 转发)
  2.2  源端下载安装包 (通过 Squid 代理，WinRM 触发 PowerShell 脚本)
  2.3  InstallAutoItPhase (安装包已在源端)
  2.4  InstallAgentPhase (安装包已在源端)
  2.5  ConfigurePhase (proxy 模式, 代理=Squid:3128)
  2.6  VerifyPhase
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from core.config import MigrateConfig
from core.winrm.manager import WinRMManager
from phases.base_phase import MigrationContext, PhaseResult, PhaseStatus
from phases.cleanup_source_phase import CleanupSourcePhase
from phases.configure_phase import ConfigurePhase
from phases.configure_py2_phase import ConfigurePy2Phase
from phases.install_agent_phase import InstallAgentPhase
from phases.install_autoit_phase import InstallAutoItPhase
from phases.verify_phase import VerifyPhase
from phases.winrm_phase import WinRMPhase
from scenarios.base_scenario import BaseScenario, ScenarioResult

logger = logging.getLogger(__name__)


class PrivateScenario(BaseScenario):
    """私网迁移场景 — 代理模式，proxyopt 分发 + Agent 部署。"""

    def __init__(self, config: MigrateConfig):
        super().__init__("私网迁移(代理模式)")
        self._config = config

        # 构建上下文
        self._ctx = MigrationContext(
            config=config,
            winrm_manager=WinRMManager(config),
            sandbox_download_dir=config.download.sandbox_download_dir,
            source_download_dir=config.source_download_dir,
        )

        # Phase 2 阶段链（不含 DownloadPhase，proxyopt 已负责下载）
        # 根据 agent_version 选择配置阶段
        is_py2 = config.sms_agent.agent_version == "py2"

        self.add_phase(WinRMPhase(via_gost=True))
        # 迁移前必做清理：gost 经 Phase1 就绪，WinRM 建立后先清源端残留再全新部署 Agent
        self.add_phase(CleanupSourcePhase())

        if is_py2:
            # Py2: 命令行配置，无需 AutoIt
            logger.info("Agent 版本: Py2 (命令行界面)，跳过 AutoIt 安装")
            self.add_phase(InstallAgentPhase(installer_on_source=True))
            self.add_phase(ConfigurePy2Phase(proxy_mode=True))
        else:
            # Py3: 图形界面配置
            mode = config.sms_agent.configure_mode
            if mode == "autoit":
                # AutoIt 编译/au3 方式
                logger.info("Agent 版本: Py3 (configure_mode=autoit)，安装 AutoIt + au3 配置")
                self.add_phase(InstallAutoItPhase(installer_on_source=True))
            else:
                # 纯 exe 方式: 直接使用本地预编译 exe
                logger.info("Agent 版本: Py3 (configure_mode=exe)，纯 exe 直传配置（无需 AutoIt）")
            self.add_phase(InstallAgentPhase(installer_on_source=True))
            self.add_phase(ConfigurePhase(proxy_mode=True))

        self.add_phase(VerifyPhase())

    def run(self) -> ScenarioResult:
        start = time.time()
        logger.info("#" * 60)
        logger.info("# 场景开始: %s", self.name)
        logger.info("#" * 60)

        # 将回调注入 context，供阶段内进度回调使用
        self._ctx.callbacks = self.callbacks

        # 触发场景开始回调
        self.callbacks.fire_scenario_start({
            "scenario": self.name, "phases": len(self._phases),
        })

        all_results = []

        # ---- Phase 1: proxyopt 文件分发 ----
        self.callbacks.fire_phase_start(_PhaseRef("ProxyOpt-分发"))
        phase1_result = self._run_proxyopt_phase1()
        all_results.append(phase1_result)
        self.callbacks.fire_phase_complete(phase1_result)
        if phase1_result.status == PhaseStatus.FAILED:
            return self._finish(all_results, start)

        # ---- Phase 2: Agent 部署配置（阶段链）----
        for phase in self._phases:
            self.callbacks.fire_phase_start(phase)
            result = phase.run(self._ctx)
            all_results.append(result)
            self.callbacks.fire_phase_complete(result)
            if result.status == PhaseStatus.FAILED:
                logger.error("阶段 %s 失败，终止场景", phase.name)
                break

            # 源端清理完成后，触发源端下载安装包
            # (CleanupSourcePhase 会删除 source_download_dir 旧缓存，故下载必须放在清理之后)
            if phase.name == "CleanupSourcePhase" and result.status == PhaseStatus.SUCCESS:
                download_ref = _PhaseRef("源端下载")
                self.callbacks.fire_phase_start(download_ref)
                download_result = self._trigger_source_download()
                all_results.append(download_result)
                self.callbacks.fire_phase_complete(download_result)
                if download_result.status == PhaseStatus.FAILED:
                    break

        # 停止保活
        if self._ctx.winrm_manager:
            self._ctx.winrm_manager.stop_keepalive()

        return self._finish(all_results, start)

    def _finish(self, results: list, start: float) -> ScenarioResult:
        duration = time.time() - start
        success = all(r.status != PhaseStatus.FAILED for r in results)
        logger.info("#" * 60)
        logger.info("# 场景结束: %s → %s (%.1fs)", self.name, "成功" if success else "失败", duration)
        logger.info("#" * 60)
        result = ScenarioResult(self.name, results, duration, success)
        self.callbacks.fire_scenario_complete(result.to_dict())
        return result

    def _run_proxyopt_phase1(self) -> PhaseResult:
        """
        Phase 1: 跳板机一键就绪（deploy_jumpbox.deploy）。
        1.1 沙箱 OBS 下载 → 1.2 文件同步 → 1.3 HTTP 8080 → 1.4 Squid → 1.5 gost → 1.6 preCache
        """
        start = time.time()

        # 检查是否跳过 proxyopt phase（已在跳板机手动完成）
        if getattr(self._config.proxyopt, 'skip', False):
            logger.info("Phase 1: proxyopt 已跳过（配置 proxyopt.skip=true，假设跳板机已就绪）")
            return PhaseResult("ProxyOpt-分发", PhaseStatus.SUCCESS, 0,
                               detail="跳过：Squid+gost+HTTP 已在跳板机手动部署")

        logger.info("=" * 60)
        logger.info("Phase 1: 跳板机一键就绪（文件服务器部署到代理主机）")
        logger.info("=" * 60)

        try:
            from proxyopt.scripts.deploy_jumpbox import deploy
        except Exception:
            import traceback
            logger.error("deploy_jumpbox 导入失败:\n%s", traceback.format_exc())
            return PhaseResult("ProxyOpt-分发", PhaseStatus.FAILED, time.time() - start,
                               error="deploy_jumpbox 导入失败")

        try:
            results = deploy(self._config)
        except Exception:
            import traceback
            # 保留完整堆栈，避免"异常信息为空"导致无法定位（历史问题）
            logger.error("跳板机部署异常 (deploy):\n%s", traceback.format_exc())
            return PhaseResult("ProxyOpt-分发", PhaseStatus.FAILED, time.time() - start,
                               error="跳板机部署异常，详见 migrate.log 中的 traceback")

        failed = [k for k, (ok, _) in results.items() if not ok]
        if failed:
            return PhaseResult("ProxyOpt-分发", PhaseStatus.FAILED, time.time() - start,
                               error=f"部署失败步骤: {failed}")
        return PhaseResult("ProxyOpt-分发", PhaseStatus.SUCCESS, time.time() - start,
                           detail="OBS下载→文件同步→HTTP→Squid→gost→preCache 全部完成")

    def _trigger_source_download(self) -> PhaseResult:
        """
        源端通过 Squid 代理下载安装包。
        WinRM 已建立（经 gost），传输 Download-Agent.ps1 到源端并执行。
        """
        start = time.time()
        logger.info("=" * 60)
        logger.info("源端下载安装包 (通过 Squid 代理)")
        logger.info("=" * 60)

        cfg = self._config
        exe = self._ctx.winrm_executor
        if not exe:
            return PhaseResult("源端下载", PhaseStatus.FAILED, time.time() - start,
                               error="WinRM 未建立")

        # proxyopt 的 PowerShell 下载脚本
        ps_script = Path(cfg.proxyopt.base_dir) / "source" / "Download-Agent.ps1"
        if not ps_script.exists():
            return PhaseResult("源端下载", PhaseStatus.FAILED, time.time() - start,
                               error=f"脚本不存在: {ps_script}")

        # 传输到源端
        source_dir = cfg.source_download_dir
        remote_script = f"{source_dir}\\sandbox_download.ps1"
        r = exe.transfer_file(str(ps_script), remote_script)
        if not r.success:
            return PhaseResult("源端下载", PhaseStatus.FAILED, time.time() - start,
                               error=f"脚本传输失败: {r.stderr[:200]}")

        # 执行：源端通过 Squid 代理从跳板机 HTTP 服务下载
        # 源端通过跳板机私网 IP 访问 Squid，优先使用 sms_agent.proxy_host 或 sandbox_host
        proxy_host = cfg.sms_agent.proxy_host or cfg.sandbox_host or cfg.proxy_server.host
        proxy_port = cfg.proxy_server.squid_port
        # 跳板机 HTTP 服务地址（源端通过代理访问）
        sandbox_host = cfg.sandbox_host or cfg.proxy_server.host
        http_port = cfg.proxy_server.http_server_port

        # 使用 run_ps 执行 PowerShell 脚本，避免 CMD 引号转义问题
        ps_script_content = (
            f"& '{remote_script}' "
            f"-DownloadDir '{source_dir}' "
            f"-ProxyHost {proxy_host} -ProxyPort {proxy_port} "
            f"-SandboxHost {sandbox_host} -SandboxPort {http_port}"
        )
        logger.info("执行源端下载: %s", ps_script_content[:120])
        r = exe.run_ps(ps_script_content, timeout=cfg.timeout.file_transfer)
        if not r.success:
            return PhaseResult("源端下载", PhaseStatus.FAILED, time.time() - start,
                               error=f"下载执行失败: {r.stderr[:300]}")

        logger.info("源端下载完成")
        return PhaseResult("源端下载", PhaseStatus.SUCCESS, time.time() - start,
                           detail="安装包已通过 Squid 代理下载到源端")


class _PhaseRef:
    """轻量阶段引用 — 供 fire_phase_start 回调使用（仅含 .name 属性）。"""

    def __init__(self, name: str):
        self.name = name
