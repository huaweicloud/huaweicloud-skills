"""
配置阶段 — 传输 au3 脚本 → .bat + schtasks 在 Session 1 运行 AutoIt → 轮询完成。

direct 模式: AutoIt 参数 = AK SK Domain EP direct LogPath
proxy  模式: AutoIt 参数 = AK SK Domain EP proxy ProxyHost ProxyPort LogPath

au3 命令行:
  CmdLine[1]=secrets文件(base64)  [2]=Mode(direct/proxy)  [3]=ProxyIP  [4]=ProxyPort  [5]=LogPath  [6]=InstallDir

所有源端路径通过 config.source_base_dir 派生，无硬编码。
"""
from __future__ import annotations

import base64
import logging
import time
from pathlib import Path

from core.exceptions import ConfigError
from phases.base_phase import BasePhase, MigrationContext

logger = logging.getLogger(__name__)

# au3 脚本在沙箱的路径（core/ 目录下）
_AU3_DIR = Path(__file__).parent.parent / "scripts" / "py3"


class ConfigurePhase(BasePhase):
    """
    AutoIt GUI 配置阶段。

    proxy_mode=False: 直连模式，AutoIt 参数不含代理
    proxy_mode=True:  代理模式，AutoIt 参数含代理地址
    """

    def __init__(self, proxy_mode: bool = False):
        super().__init__("ConfigurePhase")
        self._proxy_mode = proxy_mode

    def precheck(self, ctx: MigrationContext) -> bool:
        # exe 模式: 只需 WinRM 已连通（exe 独立运行，无需 AutoIt）
        # autoit 模式: 需要源端已装 AutoIt（编译 au3 / au3 回退）
        if ctx.winrm_executor is None:
            return False
        # Py3 GUI Agent 配置必须在交互桌面会话（Session 1）进行；
        # 无 explorer(Session>0) 说明无人登录桌面，此时任务会静默不执行（历史问题 C4），直接快速失败。
        r = ctx.winrm_executor.run_ps(
            "$p = Get-Process explorer -ErrorAction SilentlyContinue | "
            "Where-Object {$_.SessionId -gt 0} | Select-Object -First 1; "
            "if ($p) { 'HAS_SESSION' } else { 'NO_SESSION' }", timeout=30)
        if not r.success or "HAS_SESSION" not in (r.stdout or ""):
            raise ConfigError(
                "源端无交互桌面会话（explorer/SessionId>0）：Py3(GUI) Agent 配置需要 Session 1。"
                "请先通过 RDP/控制台登录源端并保持会话，再重试迁移。")
        mode = getattr(ctx.config.sms_agent, "configure_mode", "exe")
        if mode == "autoit" and not ctx.autoit_installed:
            logger.warning("configure_mode=autoit 但 AutoIt 未安装，跳过")
            return False
        return True

    def execute(self, ctx: MigrationContext) -> str:
        cfg = ctx.config
        exe = ctx.winrm_executor
        mode = getattr(cfg.sms_agent, "configure_mode", "exe")

        # 确保源端工作目录存在（彻底清理后目录可能不存在）
        exe.run_cmd(f'if not exist "{cfg.source_base_dir}" mkdir "{cfg.source_base_dir}"', timeout=15)

        # exe 模式: 直接使用本地预编译 exe，无需 au3 / AutoIt
        # autoit 模式: 传输 au3 脚本供目标机编译 / au3 兜底
        need_au3 = (mode == "autoit")
        au3_local = _AU3_DIR / "configure_sms_agent.au3"
        au3_remote = cfg.source_au3_path

        if need_au3:
            logger.info("传输 au3 脚本: %s → %s", au3_local, au3_remote)
            r = exe.transfer_file(str(au3_local), au3_remote)
            if not r.success:
                return f"au3 传输失败: {r.stderr}"
        else:
            logger.info("configure_mode=exe: 跳过 au3 传输，仅使用预编译 exe")

        # 2. 构建敏感参数临时文件 (base64编码, 读取后由au3自动删除)
        #    安全设计: AK/SK/Domain/EP 不经命令行明文传递, 不写入bat文件
        autoit_exe = cfg.autoit.exe_path
        aut2exe = cfg.autoit.aut2exe_path
        sa = cfg.sms_agent
        log_path = cfg.source_log_path
        source_base = cfg.source_base_dir
        secrets_remote = f"{source_base}\\.secrets.dat"
        exe_remote = cfg.source_exe_path

        # 构建 key=value 格式的明文, 然后 base64 编码
        secrets_plain = f"AK={sa.ak}\r\nSK={sa.sk}\r\nDomain={sa.domain_id}\r\nEP={sa.enterprise_project}"
        if self._proxy_mode:
            secrets_plain += "\r\nProxyUser=\r\nProxyPass="
        secrets_b64 = base64.b64encode(secrets_plain.encode("utf-8")).decode("ascii")

        # 通过 PowerShell 写入 base64 内容到临时文件
        ps_write_secrets = (
            f"[IO.File]::WriteAllText('{secrets_remote}', '{secrets_b64}', "
            f"[Text.Encoding]::ASCII)"
        )
        r = exe.run_ps(ps_write_secrets, timeout=15)
        if not r.success:
            return f"敏感参数文件写入失败: {r.stderr}"

        # 写入后立即回读校验：防止 .secrets.dat 被写坏/被抢占导致
        # AutoIt 读到空值（Domain/EP 为空 → invalid AK or SK → “假配置成功”未注册）。
        r = exe.run_ps(
            f"if (Test-Path '{secrets_remote}') {{ Get-Content '{secrets_remote}' -Raw }} else {{ '' }}",
            timeout=15,
        )
        if not r.success or not (r.stdout or "").strip():
            return f"敏感参数文件写入后校验失败: 文件缺失或为空，请重试 ConfigurePhase"
        try:
            _decoded = base64.b64decode((r.stdout or "").strip()).decode("utf-8")
        except Exception as _e:
            return f"敏感参数文件校验失败: base64 解码异常 ({_e})，请重试 ConfigurePhase"
        _fields = {}
        for _line in _decoded.splitlines():
            if "=" in _line:
                _k, _v = _line.split("=", 1)
                _fields[_k.strip()] = _v.strip()
        _missing = [k for k in ("AK", "SK", "Domain", "EP") if not _fields.get(k, "")]
        if _missing:
            return f"敏感参数文件校验失败: 字段为空 {_missing}，请检查 config 中 AK/SK/Domain/EP"
        logger.info("敏感参数文件校验通过 (AK/SK/Domain/EP 非空, base64 解码正常): %s", secrets_remote)

        logger.info("敏感参数已写入临时文件 (base64编码): %s", secrets_remote)

        # 2b. exe 模式 (首选 exe, 失败回退 au3 + AutoIt3.exe)
        #     优先级: 本地预编译 exe → 目标机编译 → au3 回退
        use_exe = False
        exe_local = _AU3_DIR / "configure_sms_agent.exe"

        if exe_local.exists():
            # 优先经跳板机 HTTP 分发（秒级，同网段直达），失败回退 WinRM transfer
            http_host = cfg.sandbox_host or cfg.proxy_server.host
            http_port = cfg.proxy_server.http_server_port
            remote_http = f"http://{http_host}:{http_port}/configure_sms_agent.exe"
            ps_dl = (
                "$ProgressPreference='SilentlyContinue';"
                f"try {{ Invoke-WebRequest -Uri '{remote_http}' -OutFile '{exe_remote}' "
                f"-UseBasicParsing -TimeoutSec 30; "
                f"if((Get-Item '{exe_remote}').Length -gt 0){{ 'DL_OK' }} else {{ 'DL_EMPTY' }} }} "
                f"catch {{ 'DL_FAIL' }}"
            )
            r = exe.run_ps(ps_dl, timeout=60)
            if r.success and "DL_OK" in (r.stdout or ""):
                use_exe = True
                logger.info("HTTP 直传 exe (秒级): %s → %s", remote_http, exe_remote)
            else:
                logger.info("HTTP 直传不可用(%s)，回退 WinRM transfer", (r.stdout or r.stderr or "")[:40])
                r = exe.transfer_file(str(exe_local), exe_remote)
                if r.success:
                    use_exe = True
                    logger.info("使用本地预编译 exe: %s → %s", exe_local, exe_remote)
                else:
                    logger.warning("本地 exe 传输失败, 重连 WinRM 后尝试目标机编译")
                    exe.reconnect()

        if not use_exe:
            mode = getattr(cfg.sms_agent, "configure_mode", "exe")
            if mode == "exe":
                # 纯 exe 模式: 无 AutoIt，编译/au3 兜底均不可用，直接失败
                logger.error("exe 直传失败且 configure_mode=exe（无 AutoIt 兜底）")
                return f"本地 exe 传输失败: {r.stderr[:200]}（configure_mode=exe，请检查 WinRM 传输或改用 configure_mode=autoit）"

        if not use_exe and need_au3 and aut2exe:
            # autoit 模式: 本地无 exe, 在目标机编译 (Aut2Exe 是 GUI 程序, 需用 AutoIt3.exe + RunWait 调用)
            compile_au3_local = _AU3_DIR / "compile_au3.au3"
            compile_au3_remote = f"{source_base}\\compile_au3.au3"
            r = exe.transfer_file(str(compile_au3_local), compile_au3_remote)
            if not r.success:
                logger.warning("compile_au3.au3 传输失败, 回退 au3 模式")
            else:
                done_marker = f"{source_base}\\.compile_done"
                compile_bat_remote = f"{source_base}\\compile.bat"
                compile_bat_content = (
                    f'@echo off\r\n'
                    f'"{autoit_exe}" "{compile_au3_remote}" '
                    f'"{aut2exe}" "{au3_remote}" "{exe_remote}" "{done_marker}"\r\n'
                )
                cb_b64 = base64.b64encode(compile_bat_content.encode("latin-1")).decode("ascii")
                ps_write_cb = (
                    f"[IO.File]::WriteAllText('{compile_bat_remote}', "
                    f"[Text.Encoding]::Default.GetString([Convert]::FromBase64String('{cb_b64}')), "
                    f"[Text.Encoding]::Default)"
                )
                exe.run_ps(ps_write_cb, timeout=15)

                exe.run_ps(f"Remove-Item '{done_marker}' -Force -ErrorAction SilentlyContinue")
                exe.run_cmd("schtasks /delete /tn CompileAU3 /f")
                exe.run_cmd(
                    f'schtasks /create /tn CompileAU3 /tr "{compile_bat_remote}" '
                    f'/sc once /st 00:00 /f /rl highest'
                )
                exe.run_cmd("schtasks /run /tn CompileAU3")

                for _ in range(15):
                    time.sleep(2)
                    r = exe.run_ps(f"Test-Path '{done_marker}'")
                    if r.success and "True" in (r.stdout or ""):
                        use_exe = True
                        logger.info("目标机编译 exe 成功: %s", exe_remote)
                        break
                if not use_exe:
                    logger.warning("目标机编译超时, 回退 au3 模式")

        # 3. 创建 .bat 启动脚本 — 只传文件路径和非敏感参数, 无明文密钥
        #    @echo off 防止 CMD 窗口回显命令行
        if self._proxy_mode:
            params = (
                f'"{secrets_remote}" proxy '
                f'"http://{sa.proxy_host}" "{sa.proxy_port}" "{log_path}"'
            )
        else:
            params = (
                f'"{secrets_remote}" direct '
                f'"" "" "{log_path}"'
            )

        bat_remote = cfg.source_bat_path
        # 前置守卫：au3/exe 读取 .secrets.dat 后自动删除（一次性设计），
        # 若操作者直接 schtasks /run 而 secrets 缺失，AutoIt 会读空值导致
        # Domain/EP 为空 → invalid AK or SK → “假配置成功”未注册。守卫快速失败并提示官方恢复入口。
        secrets_guard = (
            f'if not exist "{secrets_remote}" ('
            f'echo [SECRETS_MISSING] .secrets.dat missing, run: python3 agent_recover.py >> "{log_path}"'
            f' & exit /b 1)'
        )
        if use_exe:
            bat_content = (
                f'@echo off\r\nchcp 936 >nul 2>&1\r\n'
                f'{secrets_guard}\r\n'
                f'"{exe_remote}" {params}'
            )
            logger.info("使用 exe 模式 | bat 内容 (无明文密钥): %s", bat_content)
        else:
            bat_content = (
                f'@echo off\r\nchcp 936 >nul 2>&1\r\n'
                f'{secrets_guard}\r\n'
                f'"{autoit_exe}" "{au3_remote}" {params}'
            )
            logger.info("使用 au3 模式 | bat 内容 (无明文密钥): %s", bat_content)

        # 自适应编码: 优先 GBK(中文OS), 回退 UTF-8(英文OS)
        # bat 内容可能含中文(如路径), 需兼容两种编码环境
        bat_b64_gbk = base64.b64encode(bat_content.encode("gbk")).decode("ascii")
        bat_b64_utf8 = base64.b64encode(bat_content.encode("utf-8")).decode("ascii")
        ps_write_bat = (
            f"$batEnc=$null; $batB64=$null; "
            f"try {{ $batEnc=[Text.Encoding]::GetEncoding(936); $batB64='{bat_b64_gbk}' }} "
            f"catch {{ $batEnc=[Text.Encoding]::UTF8; $batB64='{bat_b64_utf8}' }}; "
            f"[IO.File]::WriteAllText('{bat_remote}', "
            f"$batEnc.GetString([Convert]::FromBase64String($batB64)), $batEnc)"
        )
        r = exe.run_ps(ps_write_bat, timeout=30)
        if not r.success:
            return f"bat 写入失败: {r.stderr}"

        # 4. 通过 schtasks 运行 .bat（简单无嵌套引号）
        task_name = "ConfigureSMSAgent"

        # 先删除已有任务
        exe.run_cmd(f'schtasks /delete /tn {task_name} /f', timeout=30)

        # 清旧日志
        exe.run_cmd(f'del "{log_path}" 2>nul', timeout=10)

        # 创建计划任务 — /tr 指向 .bat，无引号嵌套问题
        # 【/it 核心】Py3 GUI Agent 必须运行在交互会话（Session 1），否则任务不启动/无桌面可自动化
        # （历史问题：缺 /it 时任务 LogonMode=Interactive only 但从不执行，configure_log 永不生成，
        #   配合 base_phase 的误报缺陷导致"假成功"。见 cleanup_source_phase 同批修复记录。）
        # /ru /rp 取源端管理员凭据（配置层已有），保证任务以交互用户身份投递到桌面会话。
        create_cmd = (
            f'schtasks /create /tn {task_name} '
            f'/tr "{bat_remote}" /sc once /st 00:00 /f /rl highest /it'
        )
        ru = (cfg.source.username or "").strip()
        rp = (cfg.source.password or "").strip()
        if ru:
            create_cmd += f' /ru {ru}'
            if rp:
                create_cmd += f' /rp {rp}' 
        r = exe.run_cmd(create_cmd, timeout=30)
        if not r.success:
            return f"创建计划任务失败: {r.stderr}"

        # 立即运行
        r = exe.run_cmd(f'schtasks /run /tn {task_name}', timeout=30)
        if not r.success:
            return f"运行计划任务失败: {r.stderr}"

        logger.info("AutoIt 配置任务已启动，等待完成...")

        # 5. 轮询 configure_log.txt 等待 AutoIt 完成
        #    优化：首次 1s×3 快速检测，之后 5s 间隔（原 10s）
        max_wait = cfg.timeout.autoit_run
        elapsed = 0
        poll_count = 0
        while elapsed < max_wait:
            # 前3次用1s间隔快速检测，之后用5s
            current_interval = 1 if poll_count < 3 else 5
            time.sleep(current_interval)
            elapsed += current_interval
            poll_count += 1

            # 读取 configure_log.txt 最后几行
            ps_cmd = (
                f"if (Test-Path '{log_path}') {{ "
                f"Get-Content -Path '{log_path}' -Tail 5 -Encoding Default "
                f"}} else {{ Write-Output '' }}"
            )
            r = exe.run_ps(ps_cmd, timeout=15)
            content = r.stdout if r.success else ""

            if content:
                content_lower = content.lower()
                # 检测完成标记
                if any(kw in content_lower for kw in [
                    "完成", "heartbeat", "heart beat", "注册成功",
                    "5/5", "===== 完成", "config_complete",
                ]):
                    logger.info("AutoIt 配置完成 (%ds)", elapsed)
                    return f"AutoIt 配置完成 ({elapsed}s)"

            logger.debug("等待 AutoIt... %ds/%ds", elapsed, max_wait)

            # 阶段内进度回调（仅单台模式，批量模式 ctx.callbacks=None）
            if ctx.callbacks:
                ctx.callbacks.fire_phase_progress({
                    "phase": "ConfigurePhase",
                    "elapsed": elapsed,
                    "max_wait": max_wait,
                    "log_tail": (content or "").strip()[-200:],
                })

        raise TimeoutError(
            f"AutoIt 配置超时 ({max_wait}s)：configure_log 未出现完成标记。"
            "常见原因：源端无交互桌面会话（Session 1）、计划任务未以 /it 运行、或 Agent GUI 未弹出。"
            "请先通过 RDP/控制台登录源端并保持会话，再重试。")

    def verify(self, ctx: MigrationContext) -> bool:
        # 检查 SMS-Agent 日志文件是否已生成
        log_file = ctx.config.sms_agent.log_file
        return ctx.winrm_executor.file_exists(log_file)
