"""
WinRM 阶段 — 检测 WinRM → 不通则开启 → 启动保活。

公网模式：直连源端 IP:5985
私网模式：经 gost 转发 代理服务器:15985 → 源端:5985

逻辑说明:
  WinRM 开启需要先有一个能执行命令的通道。常见场景:
  1. 端口已通 + 认证已配 → 直接连接
  2. 端口已通 + 认证未配 → 用当前凭据尝试连接，若失败则需外部方式（SSH/云控制台）
  3. 端口不通 → 需外部方式先开放端口（如安全组/防火墙规则）

  本阶段处理场景 1 和 2。场景 3 需要前置条件（如 SSH 阶段或手动配置）。
"""
from __future__ import annotations

import logging

from core.executor.winrm_executor import WinRMExecutor
from phases.base_phase import BasePhase, MigrationContext

logger = logging.getLogger(__name__)


class WinRMPhase(BasePhase):
    """
    WinRM 连通性管理阶段。

    via_gost=False: 直连源端
    via_gost=True:  经 gost 端口转发
    """

    def __init__(self, via_gost: bool = False):
        super().__init__("WinRMPhase")
        self._via_gost = via_gost

    def precheck(self, ctx: MigrationContext) -> bool:
        return ctx.config is not None

    def execute(self, ctx: MigrationContext) -> str:
        cfg = ctx.config

        # 确定连接目标
        if self._via_gost:
            host = cfg.proxy_server.host
            port = cfg.proxy_server.gost_listen_port
        else:
            host = cfg.source.host
            port = cfg.source.winrm_port

        username = cfg.source.username
        password = cfg.source.password
        transport = cfg.source.winrm_transport
        use_ssl = cfg.source.winrm_use_ssl

        # 1. 检测 WinRM
        detection = ctx.winrm_manager.detect(
            host=host,
            port=port,
            username=username,
            password=password,
            use_ssl=use_ssl,
            transport=transport,
        )

        if detection.status.value == "connected":
            logger.info("WinRM 已连通，无需开启")
        else:
            logger.info("WinRM 未连通 (%s)", detection.status.value)

            if not detection.port_open:
                # 场景 3: 端口不通 — 无法通过 WinRM 开启 WinRM
                # 需要外部方式（SSH/云控制台/安全组）先开放端口
                return (
                    f"WinRM 端口 {host}:{port} 不可达。"
                    f"需先通过 SSH/云控制台/安全组等方式开放端口，"
                    f"然后重新运行迁移。"
                )

            # 场景 2: 端口通但认证失败
            # 尝试用当前凭据建立连接并开启 WinRM
            # 如果认证完全错误，这里会抛异常
            logger.info("端口已通但认证未配，尝试建立连接并开启 WinRM...")
            try:
                temp_executor = WinRMExecutor(
                    host=host, port=port,
                    username=username,
                    password=password,
                    transport=transport,
                    use_ssl=use_ssl,
                )
                # 连接成功，尝试通过 cloud provider 开启/配置 WinRM
                if not ctx.winrm_manager.setup(temp_executor):
                    return "WinRM 开启失败，请检查凭据或手动配置 WinRM"
                logger.info("WinRM 已开启，重新检测...")
                # 重新检测
                detection = ctx.winrm_manager.detect(
                    host=host, port=port,
                    username=username, password=password,
                    use_ssl=use_ssl, transport=transport,
                )
                if detection.status.value != "connected":
                    return f"WinRM 开启后仍无法连接: {detection.status.value}"
            except Exception as e:
                return (
                    f"无法建立 WinRM 连接: {e}。"
                    f"请检查用户名/密码是否正确，或手动配置 WinRM 认证。"
                )

        # 3. 创建正式 WinRM 执行器
        ctx.winrm_executor = WinRMExecutor(
            host=host, port=port,
            username=username,
            password=password,
            transport=transport,
            use_ssl=use_ssl,
            command_timeout=cfg.timeout.winrm_command,
            remote_work_dir=cfg.source_base_dir,
        )

        # 4. 启动保活
        if cfg.winrm_keepalive.enabled:
            ctx.winrm_manager.start_keepalive(
                ctx.winrm_executor,
                interval=cfg.winrm_keepalive.interval,
            )
            logger.info("WinRM 保活已启动 (间隔 %ds)", cfg.winrm_keepalive.interval)

        return f"WinRM 已就绪: {host}:{port} (gost={self._via_gost})"

    def verify(self, ctx: MigrationContext) -> bool:
        if not ctx.winrm_executor:
            return False
        return ctx.winrm_executor.is_connected()
