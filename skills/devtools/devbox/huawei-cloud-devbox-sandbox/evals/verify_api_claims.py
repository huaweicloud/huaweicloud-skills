#!/usr/bin/env python3
"""Verify every API claim the skill documents against the real devbox SDK."""
import dataclasses
import inspect
import sys

import devbox
from devbox import (
    CommandHandle, CommandResult, DevBox, DevBoxError, PtySize, Page, Sandbox,
    SandboxLifecycle, SandboxState, SandboxInfo, TemplateInfo,
)
from devbox.commands import Commands
from devbox.filesystem import Filesystem
from devbox.git import Git
from devbox.pty import Pty
from devbox.sandbox import Sandboxes, Sandbox as SB

fails = []


def check(name, cond):
    print(f"[{'FAIL' if not cond else 'OK '}] {name}")
    if not cond:
        fails.append(name)


def defaults(fn, exclude=("self", "cls")):
    return {p.name: p.default for p in inspect.signature(fn).parameters.values()
            if p.default is not inspect.Parameter.empty and p.name not in exclude}


check("create defaults", defaults(SB.create).get("template") == "default"
      and defaults(SB.create).get("timeout") == 300)
check("Commands.run defaults", defaults(Commands.run) == {
    "background": False, "envs": None, "cwd": None, "user": None,
    "stdin": False, "timeout": 60, "on_stdout": None, "on_stderr": None, "check": True})
check("Filesystem.watch defaults", defaults(Filesystem.watch) == {
    "recursive": False, "include_entry": True})
check("Git.clone defaults", defaults(Git.clone) == {
    "branch": None, "depth": None, "credentials": None, "timeout": 300})
check("Pty.start command", defaults(Pty.start).get("command") == "/bin/bash")
check("Sandbox.refresh/resume", defaults(SB.refresh) == {"duration": 300}
      and defaults(SB.resume) == {"timeout": 300})
check("Sandboxes.list defaults", defaults(Sandboxes.list) == {
    "template": None, "metadata": None, "states": (), "limit": None,
    "next_token": None, "started_after": None, "order": None})

flds = lambda c: [f.name for f in dataclasses.fields(c)]
check("CommandResult fields", flds(CommandResult) == ["exit_code", "stdout", "stderr", "pid"])
check("SandboxLifecycle default kill", SandboxLifecycle().on_timeout == "kill")
check("SandboxState 3 values", {s.value for s in SandboxState} == {"running", "paused", "stopped"})
check("PtySize 24x80", (PtySize().rows, PtySize().cols) == (24, 80))

e = DevBoxError("m", code="X", status_code=404, request_id="r")
check("DevBoxError fields/str", (e.code, e.status_code, e.request_id) == ("X", 404, "r")
      and str(e) == "m [X]")

from devbox.config import DEFAULT_API_URL, ConnectionConfig
import os
os.environ["DEVBOX_API_KEY"] = "k"
c = ConnectionConfig.resolve()
check("config defaults", DEFAULT_API_URL == "https://devbox.developer.myhuaweicloud.com"
      and (c.request_timeout, c.control_timeout) == (30.0, 150.0))

# facets (instance attrs set in __init__)
_init_src = inspect.getsource(SB.__init__)
check("Sandbox facets", all(f"self.{a} = " in _init_src
                            for a in ("commands", "files", "pty", "git", "envd")))

# ---- envd facet ----
from devbox.envd import Envd, AsyncEnvd
from devbox.models import EnvdHealth, EnvdMetrics, OomKill
check("Envd methods", all(hasattr(Envd, m) for m in ("get_metrics", "get_envs", "health")))
check("AsyncEnvd mirrors", all(hasattr(AsyncEnvd, m)
                               for m in ("get_metrics", "get_envs", "health")))
# Documented EnvdMetrics fields must all exist in the SDK (subset comparison: the SDK may
# grow optional fields between dev snapshots, but the docs must never claim a missing one).
DOCUMENTED_ENVD_METRICS = [
    "timestamp", "cpu_count", "cpu_used_pct", "mem_total", "mem_used", "mem_cache",
    "disk_total", "disk_used", "oom_kills", "cpu_possible", "cpu_target",
    "cpu_target_attempts", "cpu_write_pending_ms"]
check("EnvdMetrics documented fields are a subset of SDK fields",
      set(DOCUMENTED_ENVD_METRICS) <= set(flds(EnvdMetrics)))
check("OomKill fields", flds(OomKill) == ["seq", "process"])
check("EnvdHealth fields", flds(EnvdHealth) == ["envd_version"])
check("exports include envd", set(devbox.__all__) >= {
    "Envd", "AsyncEnvd", "EnvdHealth", "EnvdMetrics", "OomKill"})
check("AsyncSandbox mirrors", all(hasattr(devbox.AsyncSandbox, m)
      for m in ("create", "connect", "kill", "close", "pause", "resume")))

check("exports", set(devbox.__all__) >= {
    "Sandbox", "AsyncSandbox", "DevBox", "AsyncDevBox", "DevBoxError", "CommandExitError",
    "RateLimitError", "PtySize", "GitCredentials", "Page", "SandboxLifecycle"})

print()
print("ALL API CLAIMS VERIFIED" if not fails else f"{len(fails)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
