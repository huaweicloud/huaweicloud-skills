#!/usr/bin/env python3
"""clouddocs-cli 适配层 —— page 文档后端操作统一改走 CLI（subprocess 调用 clouddocs-cli）。

为什么单独成一个模块：create_page.py（创建在线 page 文档）要按同一份契约调用后端——
本模块把这层收成 clouddocs-cli 子进程调用 + JSON 信封解析，业务脚本只认这里暴露的高层函数。

CLI 契约（对齐 clouddocs-cli help + clouddocs SKILL.md）：
  - 输出统一 JSON 信封：{"ok":true,"identity":"user","data":{...}}（失败时 {"ok":false,"error":{...}}）。
  - 认证由 CLI 自身管理（keyring + 自动刷新），脚本不读宿主注入的 token env。
  - organization_id / wiki_id 由本模块自动解析后显式传入 page +create，模型无需手动前置 space +fetch：
      organization_id 由 `space +fetch --only_personal true` 取（个人空间），
      wiki_id 由 `docbase +fetch --organization_id <id> --only_default_wiki true` 取（默认文档库）；
    parent_document_id（如 AI创作文档）可选显式传。
  - content 接受「纯 Markdown 文本」（与 page-cli 同后端契约一致；CLI 帮助里的 JSON 对象示例属于
    slide +create 的页面数组，page 不适用）。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

CLI_BIN = os.environ.get("CLOUDDOCS_CLI_BIN", "clouddocs-cli")


def _dbg(line: str = ""):
    print(line, file=sys.stderr, flush=True)


def _find_cli() -> str:
    """定位 clouddocs-cli 可执行文件；找不到时报清晰错误。"""
    if os.path.isabs(CLI_BIN) and os.path.exists(CLI_BIN):
        return CLI_BIN
    resolved = shutil.which(CLI_BIN)
    if resolved:
        return resolved
    raise RuntimeError(
        f"找不到 clouddocs-cli（PATH 中无 {CLI_BIN}）；请先部署 clouddocs-cli 并 `clouddocs-cli auth login`"
    )


def _run_cli(args: list[str], timeout: int = 120, input_text: str | None = None):
    """运行 clouddocs-cli 子进程 → (exit_code, stdout, stderr)。

    超时/找不到命令等子进程层异常以 (None, "", 错误串) 返回，调用方统一按"网络/进程失败"处理。
    """
    try:
        proc = subprocess.run(
            [_find_cli(), *args],
            capture_output=True, text=True, timeout=timeout,
            input=input_text,
        )
    except FileNotFoundError as exc:
        return None, "", f"clouddocs-cli 不可执行: {exc}"
    except subprocess.TimeoutExpired as exc:
        return None, "", f"clouddocs-cli 超时（{timeout}s）: {args[:2]} ..."
    except OSError as exc:
        return None, "", f"clouddocs-cli 进程失败: {exc}"
    except RuntimeError as exc:
        return None, "", str(exc)
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _load_envelope(stdout: str) -> dict | None:
    """解析 CLI stdout 的 JSON 信封；非 JSON 返回 None。"""
    try:
        obj = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _envelope_ok(obj: dict) -> bool:
    return bool(obj.get("ok"))


def _envelope_error(obj: dict) -> str:
    err = obj.get("error")
    if isinstance(err, dict):
        message = err.get("message") or ""
        code = err.get("code")
        return f"{message}".strip() or f"code={code}"
    return str(err or "")


def _status_for(exit_code: int | None, obj: dict | None) -> int:
    """把 CLI 结果归一化成状态码语义。

    - 子进程层失败（exit_code None）→ 500（网络/进程失败）。
    - CLI ok=true → 200。
    - CLI ok=false → 从 error.code 映射：401/403 保持；其余业务错误按 400 处理。
    """
    if exit_code is None:
        return 500
    if obj is not None and _envelope_ok(obj):
        return 200
    code = None
    if obj is not None:
        err = obj.get("error")
        if isinstance(err, dict):
            code = err.get("code")
    if code in (401, 403):
        return int(code)
    return 400


def _error_text(exit_code: int | None, stdout: str, stderr: str, label: str) -> str:
    if exit_code is None:
        return stderr or f"{label} 调用 clouddocs-cli 失败"
    obj = _load_envelope(stdout)
    if obj is not None and not _envelope_ok(obj):
        return _envelope_error(obj)
    return (stderr or stdout or "").strip()[:400] or f"{label} 失败（exit={exit_code}）"


# ── 环境 / 鉴权摘要 ────────────────────────────────────────────────────────────

def base_url() -> str:
    """CLI 配置的服务地址（~/.clouddocs/config.json 的 base_url）。"""
    config_path = os.path.expanduser("~/.clouddocs/config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        host = cfg.get("base_url") or ""
        if host:
            return host.rstrip("/")
    except (OSError, json.JSONDecodeError):
        pass
    return ""


def auth_headers() -> dict:
    """兼容摘要：返回鉴权就绪信息（CLI 自管 token，脚本不再有 token env）。"""
    code, stdout, stderr = _run_cli(["auth", "status", "--json"], timeout=30)
    data = {}
    if code == 0:
        obj = _load_envelope(stdout)
        if obj is not None and _envelope_ok(obj):
            data = obj.get("data")
    try:
        cli_path = _find_cli()
    except RuntimeError as exc:
        return {
            "cli": None,
            "auth_ready": False,
            "user": "",
            "error": str(exc),
        }
    return {
        "cli": cli_path,
        "auth_ready": bool(isinstance(data, dict) and data.get("tokenStatus") == "ready"),
        "user": str((data or {}).get("user") or ""),
    }


def doc_id_from_url(doc_url: str) -> str:
    # doc_url 形如 {origin}/wapp/doc/<docId>
    return doc_url.rstrip("/").split("/")[-1] if doc_url else ""


# ── page 文档：organization/wiki 解析 + page +create ───────────────────────────

def resolve_organization_id() -> str:
    """取个人空间 organization_id：space +fetch --only_personal true。"""
    code, stdout, stderr = _run_cli(["space", "+fetch", "--only_personal", "true"], timeout=60)
    obj = _load_envelope(stdout)
    if code != 0 or obj is None or not _envelope_ok(obj):
        return ""
    return str((obj.get("data") or {}).get("organization_id") or "")


def resolve_wiki_id(organization_id: str) -> str:
    """取默认文档库 wiki_id：docbase +fetch --organization_id <id> --only_default_wiki true。"""
    if not organization_id:
        return ""
    code, stdout, stderr = _run_cli(
        ["docbase", "+fetch", "--organization_id", organization_id, "--only_default_wiki", "true"],
        timeout=60,
    )
    obj = _load_envelope(stdout)
    if code != 0 or obj is None or not _envelope_ok(obj):
        return ""
    return str((obj.get("data") or {}).get("wiki_id") or "")


def page_create(title: str, content: str, format_: int = 1,
                parent_document_id: str = "", timeout: int = 120):
    """创建在线 page 文档 → (status, text)。

    实现：clouddocs-cli page +create --title <t> --content <c> [--format <f>]
    [--organization_id <id> --wiki_id <id>] [--parent_document_id <id>]。
    organization_id（个人空间）与 wiki_id（默认文档库）经 space +fetch / docbase +fetch 解析后显式传入，
    后端要求这两个参数非空。content 传纯 Markdown 文本（与 page-cli 同后端契约一致）。
    返回 CLI stdout 原文（JSON 信封），下游 `_extract_doc_id` 从中解析文档 id。
    """
    organization_id = resolve_organization_id()
    wiki_id = resolve_wiki_id(organization_id) if organization_id else ""
    if not organization_id or not wiki_id:
        return 400, "解析 organization_id / wiki_id 失败（space +fetch / docbase +fetch 未返回有效值）"
    args = ["page", "+create", "--title", title, "--content", content, "--format", str(format_),
            "--organization_id", organization_id, "--wiki_id", wiki_id]
    if parent_document_id:
        args += ["--parent_document_id", parent_document_id]
    code, stdout, stderr = _run_cli(args, timeout=timeout)
    if code is None:
        return 500, stderr or "page +create 进程失败"
    obj = _load_envelope(stdout)
    status = _status_for(code, obj)
    if status == 200:
        return status, stdout
    return status, _error_text(code, stdout, stderr, "page +create")
