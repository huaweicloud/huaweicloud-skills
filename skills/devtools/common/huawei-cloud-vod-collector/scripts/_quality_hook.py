"""进程内质量上报钩子 — atexit 自动触发，无需 Agent 包裹。

在任何 vod-collector 业务脚本的 main() 入口调用 install() 即可：
    from _quality_hook import install; install()

行为：
- 进程退出时自动上报一条质量记录（退出码 0 → success，否则 sys_fail）
- 未捕获异常也记为 sys_fail（sys.excepthook）
- 外部已用 skill-quality-cli run 包裹时自动去重（检测 SKILL_TRACE_ID）
- SKILL_QUALITY_DISABLE=1 时完全跳过
- fire-and-forget：上报失败/超时永不阻塞业务（3s 上限）
"""
import atexit
import os
import sys
import time
import subprocess

_INSTALLED = False


def install(skill_name: str = "huawei-cloud-vod-collector") -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    _start = time.monotonic()
    _exit_code = [0]

    # 拦截 sys.exit 记录退出码
    _orig_exit = sys.exit

    def _tracked_exit(code=0):
        _exit_code[0] = code if isinstance(code, int) else 1
        _orig_exit(code)

    sys.exit = _tracked_exit

    # 未捕获异常 → sys_fail
    _orig_excepthook = sys.excepthook

    def _tracked_excepthook(etype, value, tb):
        _exit_code[0] = 1
        _orig_excepthook(etype, value, tb)

    sys.excepthook = _tracked_excepthook

    @atexit.register
    def _report():
        if os.environ.get("SKILL_QUALITY_DISABLE") == "1":
            return
        # 外部 skill-quality-cli run 包裹时（wrapper 设置 SKILL_TRACE_ID）由 wrapper 上报，这里去重
        if os.environ.get("SKILL_TRACE_ID"):
            return
        cost_ms = int((time.monotonic() - _start) * 1000)
        status = "success" if _exit_code[0] == 0 else "sys_fail"
        cli = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cli", "cli_entry.py")
        try:
            res = subprocess.run(
                [sys.executable, cli, "--no-auto-upgrade", "report",
                 "--skill-name", skill_name, "--status", status,
                 "--cost-ms", str(cost_ms)],
                timeout=3,
                capture_output=True,
                text=True,
            )
            # SKILL_QUALITY_REPORT_VERBOSE=1 时透传上报结果，便于审计
            if os.environ.get("SKILL_QUALITY_REPORT_VERBOSE") == "1":
                if res.stderr and res.stderr.strip():
                    sys.stderr.write(res.stderr.rstrip() + "\n")
        except Exception:
            pass  # 永不阻塞业务