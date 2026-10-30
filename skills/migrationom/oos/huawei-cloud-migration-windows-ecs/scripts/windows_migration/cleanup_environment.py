#!/usr/bin/env python3
"""
环境清理编排 — 源端主机 + 代理主机（顺序由网络依赖决定，零硬编码）。

顺序：
  1. [私网] 打通网络：确保代理上 gost WinRM 映射就绪（gost_listen_port → source.host:winrm_port）
     · 服务未运行则启动；服务不存在则复用 deploy_jumpbox 安装（上传二进制 + systemd unit）
     · 失败即中止：清理源端必须经此通道（这是"先打通网络再清源端"的强制依赖）
  2. 清理源端：WinRM 经 gost 清迁移残留
     · 复用 cleanup_windows.build_cleanup_commands（单一命令清单来源）
  3. 清理代理：停 gost systemd、停 HTTP 8080、停 Squid、删 /data/downloads 等部署产物
     · 幂等、best-effort、不卸载系统包（避免影响代理上其他用途）

用法:
  python3 cleanup_environment.py --config config/migrate.yaml          # 交互确认
  python3 cleanup_environment.py --config config/migrate.yaml --yes    # 免确认
  python3 cleanup_environment.py --config ... --skip-source            # 只清代理
  python3 cleanup_environment.py --config ... --skip-proxy             # 只清源端
退出码: 0=成功 1=失败 2=配置错误 130=中断
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "migrate.yaml"


def _load_config_dict(config_path: str) -> dict:
    sys.path.insert(0, str(PROJECT_ROOT))
    from core.config import ConfigLoader
    cfg = ConfigLoader.load(config_path)
    return asdict(cfg)


def _confirm(message: str, auto_yes: bool) -> bool:
    if auto_yes:
        return True
    try:
        return input(f"{message} [yes/No]: ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def _run_remote(c, cmd: str, timeout: int = 30) -> str:
    """执行代理远程命令，异常/超时返回标记串（不抛出，best-effort）。"""
    import paramiko  # noqa: F401
    try:
        _, stdout, stderr = c.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode(errors="replace").strip()
        err = stderr.read().decode(errors="replace").strip()
        return out + (("\n[stderr] " + err) if err else "")
    except Exception as e:  # noqa: BLE001
        return f"[CMD_ERR:{type(e).__name__}] {str(e)[:120]}"


# ---------- ① 打通网络：确保 gost WinRM 映射就绪 ----------

def ensure_gost(cfg: dict, auto_yes: bool) -> bool:
    """私网场景强制要求 gost 就绪后才能清源端（清源端经 gost 走 WinRM）。"""
    if cfg.get("scenario") != "private":
        print("[gost] 公网直连场景，无需代理映射")
        return True
    if not _confirm("步骤1: 确保代理 gost WinRM 映射就绪（必要，否则无法连源端）?", auto_yes):
        print("已取消")
        return False

    from proxyopt.scripts.deploy_jumpbox import _ensure_gost_systemd, ssh_client
    ps = cfg.get("proxy_server") or {}
    gost_port = ps.get("gost_listen_port", 15985)
    print(f"[gost] 代理 {ps.get('host')}:{ps.get('ssh_port', 22)} → 源端 WinRM 映射 :{gost_port}")
    try:
        c = ssh_client(cfg)
    except Exception as e:
        print(f"[gost] 无法 SSH 代理: {e}")
        return False

    try:
        active = _run_remote(c, "systemctl is-active gost-proxyopt 2>/dev/null || echo INACTIVE")
        if "active" in active:
            print("[gost] gost-proxyopt 已在运行")
        else:
            print("[gost] gost-proxyopt 未运行，尝试启动（不存在则由 deploy 自动安装）")
            started = _run_remote(c, "systemctl start gost-proxyopt 2>&1; systemctl is-active gost-proxyopt 2>/dev/null || echo INACTIVE")
            if "active" not in started:
                print("[gost] 服务不存在，调用 deploy_jumpbox 安装/启动…")
                ok, msg = _ensure_gost_systemd(c, cfg)
                if not ok:
                    print(f"[gost] gost 就绪失败: {msg}")
                    return False
        # 验证监听端口
        listening = _run_remote(c, f"ss -tln | grep ':{gost_port} ' || echo NOT_LISTEN")
        if "NOT_LISTEN" in listening:
            print(f"[gost] 端口 {gost_port} 未监听，清理源端不可行")
            return False
        print(f"[gost] 端口 {gost_port} 监听正常 ✅")
        return True
    finally:
        c.close()


# ---------- ② 清理源端 ----------

def cleanup_source(config_path: Path, auto_yes: bool) -> bool:
    if not _confirm("步骤2: 清理源端主机（删除 SMS-Agent/工作目录/注册表残留）?", auto_yes):
        print("已取消")
        return False
    from cleanup_windows import cleanup_source_winrm
    rc = cleanup_source_winrm(config_path)
    if rc != 0:
        print(f"[源端] 清理失败(rc={rc})")
        return False
    print("[源端] 清理完成 ✅")
    return True


# ---------- ③ 清理代理 ----------

def cleanup_proxy(cfg: dict, auto_yes: bool) -> bool:
    if cfg.get("scenario") != "private":
        print("[代理] 公网直连场景，无代理可清")
        return True
    if not _confirm("步骤3: 清理代理主机（停 gost/Squid/HTTP 8080，删部署产物）?", auto_yes):
        print("已取消")
        return False
    from proxyopt.scripts.deploy_jumpbox import ssh_client
    try:
        c = ssh_client(cfg)
    except Exception as e:
        print(f"[代理] 无法 SSH 代理: {e}")
        return False
    steps = [
        ("停止 gost 服务", "systemctl stop gost-proxyopt 2>/dev/null; systemctl disable gost-proxyopt 2>/dev/null; echo DONE"),
        ("停止 HTTP 8080 文件服务", "P=$(ss -tlnp | grep ':8080 ' | grep -oP 'pid=\\K[0-9]+' | sort -u); [ -n \"$P\" ] && kill -9 $P; echo DONE"),
        ("停止 Squid", "systemctl stop squid 2>/dev/null; squid -k shutdown 2>/dev/null; echo DONE"),
        ("删除文件分发目录", "rm -rf /data/downloads /tmp/proxyopt_scripts; echo DONE"),
        ("清理 systemd 状态", "systemctl daemon-reload 2>/dev/null; echo DONE"),
    ]
    try:
        for desc, cmd in steps:
            out = _run_remote(c, cmd)
            print(f"  ▶ {desc}: {out[:120]}")
    finally:
        c.close()
    print("[代理] 清理完成 ✅")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="环境清理编排（源端+代理，先打通 gost 再清源端）")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG), help="migrate.yaml 路径")
    ap.add_argument("--yes", action="store_true", help="免交互确认")
    ap.add_argument("--skip-gost", action="store_true", help="跳过 gost 就绪检查")
    ap.add_argument("--skip-source", action="store_true", help="跳过源端清理")
    ap.add_argument("--skip-proxy", action="store_true", help="跳过代理清理")
    args = ap.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path
    if not config_path.exists():
        print(f"配置不存在: {config_path}", file=sys.stderr)
        return 2

    cfg = _load_config_dict(str(config_path))
    step = 1
    try:
        if not args.skip_gost:
            print(f"\n===== [{step}] 打通网络：gost WinRM 映射 =====")
            if not ensure_gost(cfg, args.yes):
                print("gost 就绪失败，中止（必须先打通网络才能清源端）", file=sys.stderr)
                return 1
            step += 1
        if not args.skip_source:
            print(f"\n===== [{step}] 清理源端主机 =====")
            if not cleanup_source(config_path, args.yes):
                print("源端清理失败或取消", file=sys.stderr)
                return 1
            step += 1
        if not args.skip_proxy:
            print(f"\n===== [{step}] 清理代理主机 =====")
            if not cleanup_proxy(cfg, args.yes):
                print("代理清理失败或取消", file=sys.stderr)
                return 1
            step += 1
    except KeyboardInterrupt:
        print("\n中断", file=sys.stderr)
        return 130

    print("\n环境清理编排完成 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())