"""
SMS-Agent-Py2 command line configuration phase.

Console-driven state machine: ReadConsoleOutput detects prompts, feeds inputs precisely.
"""
from __future__ import annotations

import base64
import logging
import os
import time

from core.markers import MARKER_SUBSTRINGS, MARKER_KEYS
from phases.base_phase import BasePhase, MigrationContext

logger = logging.getLogger(__name__)

_WATCHDOG_TASK = "SMSAgentWatchdog"  # 源端自恢复计划任务名（模块级唯一常量）


class ConfigurePy2Phase(BasePhase):
    """SMS-Agent-Py2 CLI configuration phase."""

    def __init__(self, proxy_mode: bool = False):
        super().__init__("ConfigurePy2Phase")
        self._proxy_mode = proxy_mode

    def precheck(self, ctx: MigrationContext) -> bool:
        return ctx.winrm_executor is not None and ctx.agent_installed

    def execute(self, ctx: MigrationContext) -> str:
        cfg = ctx.config
        exe = ctx.winrm_executor
        sa = cfg.sms_agent

        if self._proxy_mode:
            err = self._write_auth_cfg(exe, sa)
            if err:
                raise RuntimeError(err)

        source_base = cfg.source_base_dir
        log_path = cfg.source_log_path
        agent_log = sa.log_file

        exe.run_cmd(f'if not exist "{source_base}" mkdir "{source_base}"', timeout=10)
        self._cleanup_residual(exe, sa)
        logger.info("Residual agent processes cleaned")

        agent_exe = f"{sa.install_dir}\\{sa.agent_exe_name}"
        cert_path = self._prepare_tls_cert(exe, sa)
        logger.info("TLS cert path: %s", cert_path or "(none)")

        # Build command-line args for agent_config.exe (parameterized exe)
        config_args = self._build_config_args(
            sa, agent_exe, log_path, agent_log, cert_path)

        # Deploy agent_config.exe: pre-compiled exe if available, else compile on source
        exe_remote = f"{source_base}\\agent_config.exe"
        self._deploy_agent_config_exe(ctx, exe, source_base, exe_remote)

        # Deploy source-side watchdog (self-recovery if registration fails)
        self._deploy_watchdog(exe, source_base, agent_log, exe_remote, log_path,
                              config_args)

        # Clean slate: delete old configure_log.txt so watchdog can detect
        # AttachConsole state correctly on first run
        exe.run_cmd(f'del "{log_path}" 2>nul', timeout=10)

        # Trigger watchdog immediately (first run: no configure_log.txt -> no
        # "Attached" marker -> default case -> wait 3 min -> kill + run agent_config.exe)
        # But since SMSAgentDeploy.exe was just cleaned up, process check fires
        # first -> runs agent_config.exe immediately without waiting.
        wd_task = _WATCHDOG_TASK
        r = exe.run_cmd(f"schtasks /run /tn {wd_task}", timeout=30)
        if r.success:
            logger.info("Watchdog triggered for first run")
        else:
            logger.warning("Watchdog trigger failed: %s, will fire on next 3-min cycle", r.stderr)

        # --- Poll for registration markers ---
        # Watchdog runs agent_config.exe which drives the interactive state
        # machine. We poll SmsAgent_Info.log for markers until timeout.
        max_wait = cfg.timeout.autoit_run
        elapsed = 0
        poll_count = 0
        marker_count = 0
        while elapsed < max_wait:
            interval = 1 if poll_count < 3 else 5
            time.sleep(interval)
            elapsed += interval
            poll_count += 1

            markers = self._check_registration(exe, agent_log)
            marker_count = sum(markers.values())
            logger.debug("Polling markers: %d/5 (%ds/%ds)", marker_count, elapsed, max_wait)

            if marker_count >= 3:
                logger.info("Registration markers reached %d/5 (%ds)", marker_count, elapsed)
                break

        logger.info("Final registration markers: %d/5 %s", marker_count,
                     {k: v for k, v in markers.items() if v})

        if marker_count >= 3:
            self._fix_tls_cert(exe, sa)
            return f"Py2 config success ({elapsed}s), markers {marker_count}/5"
        else:
            # Pull C# log + agent log for diagnostics
            cs_log_tail = ""
            r = exe.run_ps(
                f"if (Test-Path '{log_path}') {{ "
                f"Get-Content -Path '{log_path}' -Tail 20 -Encoding Default "
                f"}} else {{ Write-Output 'C# log not found' }}",
                timeout=15,
            )
            if r.stdout:
                cs_log_tail = r.stdout[-800:]
            r = exe.run_ps(
                f"if (Test-Path '{agent_log}') {{ "
                f"Get-Content -Path '{agent_log}' -Tail 30 -Encoding Default "
                f"}} else {{ Write-Output 'agent log not found' }}",
                timeout=15,
            )
            agent_log_tail = r.stdout[-500:] if r.stdout else ""
            raise RuntimeError(
                f"Agent registration failed: markers {marker_count}/5. "
                f"C# log tail:\n{cs_log_tail}\n"
                f"Agent log tail:\n{agent_log_tail}"
            )

    def verify(self, ctx: MigrationContext) -> bool:
        agent_log = ctx.config.sms_agent.log_file
        markers = self._check_registration(ctx.winrm_executor, agent_log)
        count = sum(markers.values())
        logger.info("verify() markers: %d/5 %s", count,
                     {k: v for k, v in markers.items() if v})
        return count >= 3

    def _cleanup_residual(self, exe, sa) -> None:
        # Kill agent processes (tree kill across all sessions)
        exe.run_cmd("taskkill /f /t /im SMSAgentDeploy.exe 2>&1", timeout=15)
        exe.run_cmd("taskkill /f /t /im agent-start.exe 2>&1", timeout=15)
        exe.run_cmd("taskkill /f /t /im agent_config.exe 2>&1", timeout=15)
        time.sleep(1)
        # Kill residual cmd.exe + conhost.exe windows from previous schtasks runs
        # (cross-session; safe on migration target servers)
        exe.run_cmd("taskkill /f /t /im cmd.exe 2>&1", timeout=15)
        exe.run_cmd("taskkill /f /t /im conhost.exe 2>&1", timeout=15)
        time.sleep(2)
        exe.run_cmd(f'del "{sa.log_file}" 2>nul', timeout=10)
        exe.run_cmd(f'del "{sa.install_dir}\\sms_domain.txt" 2>nul', timeout=10)

    def _check_registration(self, exe, agent_log: str) -> dict:
        markers = {
            "ak_sk_check": False, "upload_os_info": False,
            "upload_system_info": False, "schedule_task": False, "heart_beat": False,
        }
        ps_cmd = (
            f"if (Test-Path '{agent_log}') {{ "
            f"Get-Content -Path '{agent_log}' -Tail 500 -Encoding Default "
            f"}} else {{ Write-Output '' }}"
        )
        r = exe.run_ps(ps_cmd, timeout=15)
        content = r.stdout if r.success else ""
        if not content:
            return markers
        cl = content.lower()
        for i, substr in enumerate(MARKER_SUBSTRINGS):
            if substr in cl:
                markers[MARKER_KEYS[i]] = True
        return markers

    def _prepare_tls_cert(self, exe, sa) -> str:
        stable_path = f"{sa.install_dir}\\cert\\cacert.pem"
        r = exe.run_ps(f"if (Test-Path '{stable_path}') {{ (Get-Item '{stable_path}').Length }} else {{ 0 }}", timeout=10)
        if r.success and r.stdout.strip() not in ("0", ""):
            logger.info("TLS cert already at stable path: %s (%s bytes)", stable_path, r.stdout.strip())
            return stable_path
        search_dirs = [sa.install_dir, "C:\\Program Files\\Cloudbase Solutions", "C:\\Python27", "C:\\Python3", "C:\\ProgramData"]
        src = ""
        for d in search_dirs:
            r = exe.run_ps(f"if (Test-Path '{d}') {{ Get-ChildItem -Path '{d}' -Filter 'cacert.pem' -Recurse -EA SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName }}", timeout=30)
            if r.success and r.stdout.strip():
                src = r.stdout.strip().split("\n")[0].strip()
                logger.info("TLS cert: found at %s (searched %s)", src, d)
                break
        if not src:
            r = exe.run_ps("Get-ChildItem -Path 'C:\\Program Files' -Filter 'cacert.pem' -Recurse -EA SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName", timeout=60)
            if r.success and r.stdout.strip():
                src = r.stdout.strip().split("\n")[0].strip()
        if not src:
            logger.warning("TLS cert: cacert.pem not found on host, TLS errors may occur")
            return ""
        logger.info("TLS cert: copying to %s", stable_path)
        exe.run_ps(f"$d = Split-Path '{stable_path}' -Parent; if (-not (Test-Path $d)) {{ New-Item -Path $d -ItemType Directory -Force | Out-Null }}; Copy-Item -Force '{src}' '{stable_path}'", timeout=15)
        r = exe.run_ps(f"if (Test-Path '{stable_path}') {{ 'OK' }} else {{ 'FAIL' }}", timeout=10)
        if r.success and "OK" in r.stdout: return stable_path
        return ""

    def _fix_tls_cert(self, exe, sa) -> None:
        try:
            install_dir = sa.install_dir
            ps_cmd = ("$paths = @(" f"  \"{install_dir}\\cacert.pem\"," f"  \"{install_dir}\\lib\\cacert.pem\"," f"  \"{install_dir}\\Lib\\site-packages\\certifi\\cacert.pem\"," "  \"C:\\Python27\\Lib\\site-packages\\certifi\\cacert.pem\"," "  \"C:\\ProgramData\\SMS-Agent-Py2\\cacert.pem\"" "); $found = $null; foreach ($p in $paths) { if (Test-Path $p) { $found = $p; break } }; if ($found) { Write-Output $found } else { " f"Get-ChildItem -Path \"{install_dir}\" -Filter cacert.pem -Recurse -ErrorAction SilentlyContinue | " "Select-Object -First 1 -ExpandProperty FullName }")
            r = exe.run_ps(ps_cmd, timeout=15)
            cert_path = r.stdout.strip() if r.stdout else ""
            if not cert_path: return
            logger.info("TLS fix: found cacert.pem at %s", cert_path)
            r2 = exe.run_cmd(f'setx REQUESTS_CA_BUNDLE "{cert_path}" /M', timeout=15)
            if r2.success: logger.info("TLS fix: REQUESTS_CA_BUNDLE set to %s", cert_path)
        except Exception as e:
            logger.warning("TLS fix: non-fatal error: %s", e)

    def _find_csc(self, exe) -> str:
        """Find csc.exe on source, searching from v2.0 to v4.0 (broadest compatibility).

        v2.0 csc compiles C# 2.0 code (agent_config.cs is 2.0 compatible).
        v4.0 csc compiles C# 2.0+ code. Either works — the compiled exe's CLR
        version always matches the source host's installed runtime.
        """
        for pattern in ["v2.0*", "v3.5", "v4*"]:
            r = exe.run_ps(
                f'Get-ChildItem "C:\\Windows\\Microsoft.NET\\Framework\\{pattern}" '
                f'-Filter "csc.exe" -Recurse | Select-Object -First 1 -ExpandProperty FullName',
                timeout=10)
            path = r.stdout.strip() if r.stdout else ""
            if path:
                logger.info("Found csc.exe (%s): %s", pattern, path)
                return path
        return ""

    def _write_auth_cfg(self, exe, sa) -> str:
        auth_cfg_path = f"{sa.install_dir}\\config\\auth.cfg"
        auth_cfg_content = (f"[proxy-config]\r\nenable = true\r\nproxy_addr = https://{sa.proxy_host}\r\nproxy_port = {sa.proxy_port}\r\nproxy_user =\r\nuse_password = false\r\n")
        cfg_b64_gbk = base64.b64encode(auth_cfg_content.encode("gbk")).decode("ascii")
        cfg_b64_utf8 = base64.b64encode(auth_cfg_content.encode("utf-8")).decode("ascii")
        ps_write_cfg = (f"$enc=$null; $b64=$null; try {{ $enc=[Text.Encoding]::GetEncoding(936); $b64='{cfg_b64_gbk}' }} catch {{ $enc=[Text.Encoding]::UTF8; $b64='{cfg_b64_utf8}' }}; [IO.File]::WriteAllText('{auth_cfg_path}', $enc.GetString([Convert]::FromBase64String($b64)), $enc)")
        r = exe.run_ps(ps_write_cfg, timeout=15)
        if not r.success: return f"auth.cfg write failed: {r.stderr}"
        logger.info("auth.cfg written: %s (proxy=%s:%d)", auth_cfg_path, sa.proxy_host, sa.proxy_port)
        return ""

    def _deploy_watchdog(self, exe, source_base: str, agent_log: str, exe_remote: str, config_log: str, config_args: str = "") -> None:
        """Deploy a source-side watchdog: a PowerShell script + scheduled task.

        Single-run lifecycle (max ~21 min):
        - Phase 1: wait for AttachConsole (3 min, poll every 10s)
          - agent_config.exe dies -> crash -> restart
          - "Attached" appears -> Phase 2
          - 3 min timeout -> AttachConsole failure -> restart
        - Phase 2: wait for markers (4 min, poll every 10s)
          - agent_config.exe dies -> crash -> restart
          - agent-start.exe dies -> self-exit -> restart
          - markers >= 3 -> success
          - read C# state from configure_log.txt:
            State <= 4 (AK/SK stage) -> should be instant, stuck = abnormal -> restart
            State 5 (EP query) -> may be slow, keep waiting
            State 6 (awaiting markers) -> registering, keep waiting
            "DONE" but markers < 3 -> finished but failed -> restart
          - 4 min timeout -> source stuck or other -> restart
        - Max 2 restarts per run, then exit and wait for next 3-min cycle.
        """
        watchdog_ps = r"""# SMS-Agent-Py2 Registration Watchdog v2
$agentLog = "AGENT_LOG_PLACEHOLDER"
$configExe = "CONFIG_EXE_PLACEHOLDER"
$configArgs = @"
CONFIG_ARGS_PLACEHOLDER
"@
$watchdogLog = "WATCHDOG_LOG_PLACEHOLDER"
$configLog = "CONFIG_LOG_PLACEHOLDER"
$successMarkers = 3
$maxRestarts = 2

function Log-Msg($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts - $msg" | Out-File -FilePath $watchdogLog -Append -Encoding Default
}

function Check-Markers {
    if (-not (Test-Path $agentLog)) { return 0 }
    $content = (Get-Content $agentLog -Tail 500 -Encoding Default).ToLower()
    $count = 0
    if ($content -match "as/sk") { $count++ }
    if ($content -match "upload os info") { $count++ }
    if ($content -match "upload source info") { $count++ }
    if ($content -match "schedule task") { $count++ }
    if ($content -match "heart beat") { $count++ }
    return $count
}

function Get-CsState {
    # Returns: "none", "attached", "done", or the last State number as string
    if (-not (Test-Path $configLog)) { return "none" }
    $content = Get-Content $configLog -Raw -Encoding Default
    if (-not $content) { return "none" }
    # Check DONE first
    if ($content -match "===== DONE =====") { return "done" }
    # Check Attached
    if ($content -match "Attached to best PID") {
        # Extract the last "State X->Y" or "State X" line to get current state
        $lines = $content -split "`n"
        $lastState = -1
        foreach ($line in $lines) {
            if ($line -match "State (\d+)->(\d+)") {
                $lastState = [int]$Matches[2]
            } elseif ($line -match "State (\d+)") {
                $lastState = [int]$Matches[1]
            }
        }
        if ($lastState -ge 0) { return "state_$lastState" }
        return "attached"
    }
    return "started"
}

function Is-ProcessAlive($name) {
    $p = Get-Process -Name $name -ErrorAction SilentlyContinue
    return ($p -and $p.Count -gt 0)
}

function Kill-Residuals {
    taskkill /f /t /im agent-start.exe 2>$null
    taskkill /f /t /im SMSAgentDeploy.exe 2>$null
    Start-Sleep -Seconds 3
}

function Start-AgentConfig {
    # Delete old configure_log.txt for clean state detection
    if (Test-Path $configLog) { Remove-Item $configLog -Force }
    if (-not (Test-Path $configExe)) {
        Log-Msg "ERROR: $configExe not found"
        return $false
    }
    Start-Process -FilePath $configExe -ArgumentList $configArgs -WindowStyle Minimized
    Log-Msg "agent_config.exe launched with args"
    return $true
}

function Run-Recovery-Cycle {
    # Returns: $true if registration succeeded, $false if failed
    Log-Msg "Starting recovery cycle..."

    Kill-Residuals
    if (-not (Start-AgentConfig)) { return $false }

    # === Phase 1: Wait for AttachConsole (max 3 min, poll every 10s) ===
    $phase1Timeout = 180
    $phase1Elapsed = 0
    $attached = $false
    while ($phase1Elapsed -lt $phase1Timeout) {
        Start-Sleep -Seconds 10
        $phase1Elapsed += 10

        if (-not (Is-ProcessAlive "agent_config")) {
            Log-Msg "Phase1: agent_config.exe crashed ($phase1Elapsed s)"
            return $false
        }

        $csState = Get-CsState
        if ($csState -match "state_" -or $csState -eq "attached") {
            Log-Msg "Phase1: AttachConsole OK ($phase1Elapsed s), entering Phase 2"
            $attached = $true
            break
        }
    }

    if (-not $attached) {
        Log-Msg "Phase1: AttachConsole failed after $phase1Timeout s"
        return $false
    }

    # === Phase 2: Wait for markers (max 4 min, poll every 10s) ===
    $phase2Timeout = 240
    $phase2Elapsed = 0
    $lastCsState = ""
    while ($phase2Elapsed -lt $phase2Timeout) {
        Start-Sleep -Seconds 10
        $phase2Elapsed += 10

        $markers = Check-Markers
        if ($markers -ge $successMarkers) {
            Log-Msg "Phase2: markers $markers/$successMarkers reached ($phase2Elapsed s)"
            return $true
        }

        # Process checks
        if (-not (Is-ProcessAlive "agent_config")) {
            Log-Msg "Phase2: agent_config.exe crashed ($phase2Elapsed s)"
            return $false
        }
        if (-not (Is-ProcessAlive "agent-start")) {
            Log-Msg "Phase2: agent-start.exe exited ($phase2Elapsed s)"
            return $false
        }

        # C# state-based precision check
        $csState = Get-CsState
        if ($csState -ne $lastCsState) {
            Log-Msg "Phase2: csState=$csState markers=$markers/$successMarkers ($phase2Elapsed s)"
            $lastCsState = $csState
        }

        if ($csState -eq "done") {
            Log-Msg "Phase2: C# DONE but markers=$markers/$successMarkers, config failed"
            return $false
        }

        # State <= 4: AK/SK input stage, should be instant. Stuck = abnormal.
        if ($csState -match "state_(\d+)$") {
            $stateNum = [int]$Matches[1]
            if ($stateNum -le 4 -and $phase2Elapsed -gt 60) {
                Log-Msg "Phase2: stuck at state $stateNum for ${phase2Elapsed}s (AK/SK stage), abnormal"
                return $false
            }
        }
    }

    Log-Msg "Phase2: timeout after $phase2Timeout s, markers=$markers/$successMarkers, source may be stuck"
    return $false
}

# ===================== Main =====================
Log-Msg "=== Watchdog started ==="

# Quick check: already registered?
$markers = Check-Markers
if ($markers -ge $successMarkers) {
    Log-Msg "Markers $markers/$successMarkers, registration OK, nothing to do."
    Log-Msg "=== Watchdog finished ==="
    exit 0
}
Log-Msg "Markers $markers/$successMarkers, entering recovery (max $maxRestarts restarts)"

for ($i = 1; $i -le $maxRestarts; $i++) {
    Log-Msg "--- Restart $i/$maxRestarts ---"
    $ok = Run-Recovery-Cycle
    if ($ok) {
        $markers = Check-Markers
        Log-Msg "Self-recovery successful. markers=$markers/$successMarkers"
        Log-Msg "=== Watchdog finished ==="
        exit 0
    }
    Log-Msg "Restart $i failed"
}

$markers = Check-Markers
Log-Msg "All $maxRestarts restarts exhausted. markers=$markers/$successMarkers. Will retry next cycle."
Log-Msg "=== Watchdog finished ==="
"""
        ps_remote = f"{source_base}\\watchdog.ps1"
        watchdog_log = f"{source_base}\\watchdog.log"
        bs = chr(92)
        ps_content = (watchdog_ps
            .replace("AGENT_LOG_PLACEHOLDER", agent_log.replace(bs, bs + bs))
            .replace("CONFIG_EXE_PLACEHOLDER", exe_remote.replace(bs, bs + bs))
            .replace("CONFIG_ARGS_PLACEHOLDER", config_args)
            .replace("WATCHDOG_LOG_PLACEHOLDER", watchdog_log)
            .replace("CONFIG_LOG_PLACEHOLDER", config_log.replace(bs, bs + bs)))

        # Transfer via base64
        import tempfile as _tf
        with _tf.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False, encoding="utf-8") as f:
            f.write(ps_content)
            ps_local = f.name
        r = exe.transfer_file(ps_local, ps_remote, timeout=30)
        if not r.success:
            logger.warning("Watchdog script transfer failed: %s", r.stderr)
            return
        logger.info("Watchdog script transferred: %s", ps_remote)

        # 【安全】watchdog.ps1 内含 AK/SK（agent_config.exe 以命令行参数驱动，
        # 改造成文件传递前保留该机制）；上传后收紧 ACL 为 SYSTEM/Administrators 可读，
        # 降低残留凭据窃取面。敏感环境建议改用 Py3（base64 secrets 文件，读取后自动删除）。
        exe.run_cmd(
            f'icacls "{ps_remote}" /inheritance:r /grant:r "SYSTEM:(F)" "Administrators:(F)"',
            timeout=15,
        )

        # Create scheduled task: run every 3 minutes, highest privilege
        wd_task = _WATCHDOG_TASK
        exe.run_cmd(f'schtasks /delete /tn {wd_task} /f', timeout=15)
        r = exe.run_cmd(
            f'powershell -Command "'
            f'$action = New-ScheduledTaskAction -Execute \'powershell.exe\' '
            f'-Argument \'-ExecutionPolicy Bypass -WindowStyle Hidden -File \"{ps_remote}\"\'; '
            f'$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 3); '
            f'$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable; '
            f'$principal = New-ScheduledTaskPrincipal -UserId \'SYSTEM\' -RunLevel Highest; '
            f'Register-ScheduledTask -TaskName \'{wd_task}\' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force'
            f'"',
            timeout=30,
        )
        if r.success:
            logger.info("Watchdog scheduled task created: %s (every 3 min)", wd_task)
        else:
            logger.warning("Watchdog scheduled task creation failed: %s", r.stderr)


    def _build_config_args(self, sa, agent_exe: str, log_path: str,
                            agent_log: str, cert_path: str) -> str:
        """Build command-line args string for agent_config.exe.

        注意(安全): Py2 的 agent_config.exe 以命令行参数接收 AK/SK，无法像 Py3 那样
        走 base64 secrets 文件；调用方会把本字符串写入源端 watchdog.ps1（已收紧 ACL）。
        请勿在日志/回调中打印 config_args 全文。
        """
        parts = [
            f'--ak "{sa.ak}"',
            f'--sk "{sa.sk}"',
            f'--domain "{sa.domain_id}"',
            f'--ep "{sa.enterprise_project}"',
            f'--agent-exe "{agent_exe}"',
            f'--log "{log_path}"',
            f'--agent-log "{agent_log}"',
        ]
        if cert_path:
            parts.append(f'--cert "{cert_path}"')
        return " ".join(parts)

    def _deploy_agent_config_exe(self, ctx, exe, source_base: str, exe_remote: str) -> None:
        """Deploy agent_config.exe to source host.

        两种部署模式（通过 sms_agent.deploy_mode 选择）:
          - precompiled（默认）: 预编译 exe 优先。
            Server 2012+ (CLR 4.0) + 本地有 exe → 直传预编译（零编译开销）；
            预编译 exe 缺失/传输失败 → 回退源端 csc 编译。
          - cs: 强制源端编译，跳过预编译直传。
            _find_csc() 按 v2.0* → v3.5 → v4* 搜索，产物 CLR 版本与源端运行时天然匹配。
        """
        deploy_mode = getattr(ctx.config.sms_agent, "deploy_mode", "precompiled")

        scripts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "py2")
        local_exe = os.path.join(scripts_dir, "agent_config.exe")

        # precompiled 模式: 尝试预编译 exe 直传（CLR 4.0 且本地有 exe）
        if deploy_mode != "cs":
            clr4_check = exe.run_ps(
                'Get-ChildItem "C:\\Windows\\Microsoft.NET\\Framework\\v4*" '
                '-Filter "csc.exe" -Recurse | Select-Object -First 1 -ExpandProperty FullName',
                timeout=10)
            has_clr4 = bool(clr4_check.stdout and clr4_check.stdout.strip())

            if has_clr4 and os.path.exists(local_exe):
                r = exe.transfer_file(local_exe, exe_remote, timeout=60)
                if r.success:
                    logger.info("Pre-compiled agent_config.exe transferred (CLR 4.0): %s", exe_remote)
                    return
                logger.warning("Pre-compiled exe transfer failed, falling back to compile: %s", r.stderr)
        else:
            logger.info("deploy_mode=cs: 跳过预编译直传，强制源端编译")

        # 源端编译（C# 2.0 兼容，任何 csc 版本可用）
        local_cs = os.path.join(scripts_dir, "agent_config.cs")
        if not os.path.exists(local_cs):
            raise RuntimeError("Neither agent_config.exe nor agent_config.cs found in scripts/py2/")
        cs_remote = f"{source_base}\\agent_config.cs"
        r = exe.transfer_file(local_cs, cs_remote, timeout=60)
        if not r.success:
            raise RuntimeError(f"C# source transfer failed: {r.stderr}")
        logger.info("C# source transferred: %s", cs_remote)

        csc_path = self._find_csc(exe)
        if not csc_path:
            raise RuntimeError("csc.exe not found on source (no .NET Framework installed?)")
        r = exe.run_cmd(f'{csc_path} /target:winexe /out:"{exe_remote}" "{cs_remote}"', timeout=30)
        if not r.success:
            raise RuntimeError(f"C# compile failed: {r.stderr}")
        logger.info("C# compiled on source with %s: %s", csc_path, exe_remote)