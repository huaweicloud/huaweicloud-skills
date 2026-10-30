"""
OBS 签名 URL 下载阶段 — 源端直接从 OBS 下载，沙箱不经手大文件。

设计:
  大文件（SMS-Agent 80MB, AutoIt 12MB）:
    1. 沙箱用 obsutil sign 生成签名 URL（1 次，可缓存复用给 100 台）
    2. WinRM 触发源端 Invoke-WebRequest -Uri $url -OutFile $path
    3. 源端直接从 OBS 下载，沙箱零带宽

  小文件（au3 脚本 25KB）:
    1. WinRM transfer_file（base64 分块，小文件很快）

  幂等: 源端已存在且大小 > 0 则跳过
"""
from __future__ import annotations

import logging
from pathlib import Path

from core.config import MigrateConfig
from core.obs_signer import OBSSigner
from phases.base_phase import BasePhase, MigrationContext

logger = logging.getLogger(__name__)

# 走签名 URL 直下的包（大文件）
_LARGE_PACKAGES = {"sms_agent", "autoit"}

# 走 WinRM transfer 的包（小文件）

# au3 脚本在沙箱的路径
_AU3_DIR = Path(__file__).parent.parent / "scripts" / "py3"


class ObsDownloadPhase(BasePhase):
    """
    OBS 签名 URL 下载阶段。

    大文件: 签名 URL → 源端 Invoke-WebRequest 直下
    小文件: WinRM transfer_file
    """

    def __init__(self, package_names: list = None):
        super().__init__("ObsDownloadPhase")
        self._package_names = package_names or ["sms_agent", "autoit"]

    def precheck(self, ctx: MigrationContext) -> bool:
        return ctx.winrm_executor is not None and ctx.config is not None

    def execute(self, ctx: MigrationContext) -> str:
        cfg = ctx.config
        exe = ctx.winrm_executor
        source_dir = cfg.source_download_dir

        # 确保源端目录存在
        exe.run_cmd(f'if not exist "{source_dir}" mkdir "{source_dir}"')

        signer = OBSSigner(cfg.obs)
        results = []

        for name in self._package_names:
            pkg = cfg.download.packages.get(name)
            if not pkg:
                results.append(f"{name}: 未配置")
                continue

            remote_path = f"{source_dir}\\{pkg.local_name}"

            # 幂等: 检查源端是否已存在
            if exe.file_exists(remote_path):
                r = exe.run_cmd(f'for %I in ("{remote_path}") do echo %~zI')
                try:
                    size = int(r.stdout.strip().split()[-1])
                    if size > 0:
                        results.append(f"{name}: 已存在({size} bytes)")
                        ctx.downloaded_files[name] = remote_path
                        continue
                except (ValueError, IndexError):
                    pass

            if name in _LARGE_PACKAGES and pkg.obs_uri:
                # 大文件: 签名 URL 直下
                ok = self._download_via_signed_url(
                    signer, pkg.obs_uri, remote_path, exe, cfg
                )
            else:
                # 小文件: WinRM transfer
                local_path = self._find_local(name)
                if local_path:
                    r = exe.transfer_file(str(local_path), remote_path)
                    ok = r.success
                else:
                    # 没有本地文件，也走签名 URL
                    if pkg.obs_uri:
                        ok = self._download_via_signed_url(
                            signer, pkg.obs_uri, remote_path, exe, cfg
                        )
                    else:
                        results.append(f"{name}: 无 OBS URI 且无本地文件")
                        continue

            if ok:
                ctx.downloaded_files[name] = remote_path
                results.append(f"{name}: ✓")
            else:
                results.append(f"{name}: ✗ 下载失败")

        return ", ".join(results)

    def _download_via_signed_url(
        self, signer: OBSSigner, obs_uri: str,
        remote_path: str, exe, cfg: MigrateConfig,
    ) -> bool:
        """生成签名 URL → WinRM 触发源端 Invoke-WebRequest 下载。"""
        try:
            url = signer.sign(obs_uri)
        except Exception as e:
            logger.error("签名 URL 生成失败: %s — %s", obs_uri, e)
            return False

        logger.info("源端下载: %s → %s", obs_uri, remote_path)
        ps = (
            "$ProgressPreference='SilentlyContinue';"
            f"Invoke-WebRequest -Uri '{url}' -OutFile '{remote_path}' -UseBasicParsing;"
            f"if(Test-Path '{remote_path}'){{(Get-Item '{remote_path}').Length}}else{{0}}"
        )
        r = exe.run_ps(ps, timeout=cfg.timeout.file_transfer)
        if r.success:
            try:
                size = int(r.stdout.strip().split()[-1])
                if size > 0:
                    logger.info("下载完成: %s (%d bytes)", remote_path, size)
                    return True
            except (ValueError, IndexError):
                pass
        logger.error("下载失败: %s — %s", remote_path, r.stderr[:200])
        return False

    def _find_local(self, package_name: str) -> Path | None:
        """查找沙箱本地的小文件（au3 脚本等）。"""
        if package_name in ("configure_au3",):
            p = _AU3_DIR / "configure_sms_agent.au3"
            return p if p.exists() else None
        if package_name in ("install_au3",):
            p = _AU3_DIR / "install_sms_agent.au3"
            return p if p.exists() else None
        return None

    def verify(self, ctx: MigrationContext) -> bool:
        exe = ctx.winrm_executor
        source_dir = ctx.config.source_download_dir
        for name in self._package_names:
            pkg = ctx.config.download.packages.get(name)
            if not pkg:
                continue
            remote_path = f"{source_dir}\\{pkg.local_name}"
            if not exe.file_exists(remote_path):
                logger.error("验证失败: %s 不存在", remote_path)
                return False
        return True
