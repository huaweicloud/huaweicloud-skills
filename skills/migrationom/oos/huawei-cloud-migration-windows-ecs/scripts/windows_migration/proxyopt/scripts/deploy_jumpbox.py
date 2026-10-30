#!/usr/bin/env python3
"""
跳板机一键就绪（私网迁移文件服务器部署到代理主机）— 核心模块 + CLI。

架构:
  文件服务器运行在「代理主机」上（而非沙箱），源端同网段直达，不依赖沙箱入站。

  1. [沙箱] OBS 下载安装包 → proxyopt/downloads/
  2. [代理] 同步文件 → /data/downloads（SMS-Agent-Py3.exe、configure_sms_agent.exe 等）
  3. [代理] HTTP 8080 文件服务（python3 -m http.server）
  4. [代理] Squid 3128（proxy_setup_squid.sh，热加载，规避 systemctl restart 阻塞问题）
  5. [代理] gost 15985 → 源端 WinRM（systemd 托管，重启自动恢复）
  6. [沙箱] preCache 经 Squid 抓代理主机 8080（sandbox_precache.py）

同时作为 private_scenario Phase1 的部署引擎（import deploy 函数），
也支持单独执行（--config / --skip-upload / --verify-only）。

用法:
  python3 proxyopt/scripts/deploy_jumpbox.py --config config/migrate.yaml
  python3 proxyopt/scripts/deploy_jumpbox.py --config config/migrate.yaml --skip-upload
  python3 proxyopt/scripts/deploy_jumpbox.py --config config/migrate.yaml --verify-only
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import paramiko
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
DOWNLOADS_DIR = Path(os.environ.get("PROXYOPT_DOWNLOADS_DIR", "/data/downloads"))
OBS_CACHE_DIR = "downloads"          # 沙箱侧 OBS 中转目录（proxyopt 下）
REMOTE_SCRIPT_DIR = os.environ.get("PROXYOPT_REMOTE_SCRIPT_DIR", "/tmp/proxyopt_scripts")


# ── 配置加载 ──────────────────────────────────────────────

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ssh_client(cfg: dict):
    ps = cfg["proxy_server"]
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(
        hostname=ps["host"], port=ps.get("ssh_port", 22),
        username=ps["ssh_username"], password=ps["ssh_password"], timeout=20,
    )
    return c


def run(c, cmd: str, timeout: int = 60) -> str:
    "执行远程命令。任何异常/超时返回标记字符串而非抛出，防止 deploy 整体崩溃（历史空错误问题）。"
    try:
        stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode(errors="replace").strip()
        err = stderr.read().decode(errors="replace").strip()
        return out + (("\n[stderr] " + err) if err else "")
    except Exception as e:
        return f"[CMD_ERR:{type(e).__name__}] {str(e)[:120]}"


# ── 部署引擎 ──────────────────────────────────────────────

def deploy(cfg: dict, skip_upload: bool = False, verbose: bool = True) -> dict:
    """
    完整部署：OBS 下载 → 文件同步 → HTTP → Squid → gost → preCache → 验证。
    所有步骤幂等，可重复执行。返回 {step: (ok, message)}。
    """
    from dataclasses import asdict
    if not isinstance(cfg, dict):
        cfg = asdict(cfg)  # MigrateConfig dataclass → dict
    ps = cfg["proxy_server"]
    src = cfg["source"]
    results: dict[str, tuple[bool, str]] = {}
    log = (lambda msg: print(msg, flush=True)) if verbose else (lambda msg: None)

    log(f"代理主机: {ps['host']}:{ps.get('ssh_port',22)} ({ps.get('ssh_username','root')})")
    log(f"源端: {src['host']}:{src.get('winrm_port',5985)}  gost={ps.get('gost_listen_port',15985)}")

    # 1. 沙箱 OBS 下载
    ok, msg = _ensure_local_package(cfg)
    results["obs_download"] = (ok, msg)
    log(f"[1/6 OBS 下载] {msg}")
    if not ok:
        return results

    c = ssh_client(cfg)
    try:
        # 2. 文件同步（安装包 + configure exe）
        ok, msg = _sync_packages(c, cfg, skip_upload)
        results["file_sync"] = (ok, msg)
        log(f"[2/6 文件同步] {msg}")

        # 3. HTTP 8080
        ok, msg = _ensure_http_server(c)
        results["http"] = (ok, msg)
        log(f"[3/6 HTTP 8080] {msg}")

        # 4. Squid
        ok, msg = _ensure_squid(c, cfg)
        results["squid"] = (ok, msg)
        log(f"[4/6 Squid] {msg}")

        # 5. gost systemd
        ok, msg = _ensure_gost_systemd(c, cfg)
        results["gost"] = (ok, msg)
        log(f"[5/6 gost] {msg}")

        # 6. preCache（沙箱侧经 Squid 抓代理主机 HTTP）
        ok, msg = _precache(cfg)
        results["precache"] = (ok, msg)
        log(f"[6/6 preCache] {msg}")

        # 验证
        verify_results = _verify(c, cfg)
        results["verify"] = verify_results
        log(f"[验证] {verify_results[1]}")
    finally:
        c.close()

    return results


def _ensure_local_package(cfg: dict) -> tuple[bool, str]:
    """从 OBS 下载安装包到沙箱 proxyopt/downloads（已存在且非空则跳过）。"""
    pkg = cfg["download"]["packages"].get("sms_agent", {})
    local_name = pkg.get("local_name", "SMS-Agent-Py3.exe")
    cache_dir = PROJECT_ROOT / "proxyopt" / OBS_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    local_path = cache_dir / local_name
    if local_path.exists() and local_path.stat().st_size > 0:
        return True, f"{local_name} 已在沙箱缓存 ({local_path.stat().st_size} bytes)"
    obs_uri = pkg.get("obs_uri", "")
    if not obs_uri:
        return False, "未配置 sms_agent.obs_uri，无法获取安装包"
    obs = cfg["obs"]
    cmd = [obs.get("obsutil_path", "obsutil"), "cp", obs_uri, str(cache_dir), "-f"]
    if obs.get("endpoint"):
        cmd.append(f"-e={obs['endpoint']}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if r.returncode != 0 or not local_path.exists():
        return False, f"OBS 下载失败: {r.stderr[-300:]}"
    return True, f"OBS 下载完成: {local_name} ({local_path.stat().st_size} bytes)"


def _sync_packages(c, cfg: dict, skip_upload: bool) -> tuple[bool, str]:
    """同步安装包与 configure exe 到代理主机 /data/downloads（大小匹配则跳过）。"""
    run(c, f"mkdir -p {DOWNLOADS_DIR}")
    tasks = []

    # configure_sms_agent.exe（仅 Py3 ConfigurePhase HTTP 秒级分发需要）
    if cfg.get("sms_agent", {}).get("agent_version", "py3") == "py3":
        cfg_exe_local = PROJECT_ROOT / "scripts" / "py3" / "configure_sms_agent.exe"
        if cfg_exe_local.exists():
            tasks.append((str(cfg_exe_local), f"{DOWNLOADS_DIR}/configure_sms_agent.exe"))

    # SMS-Agent 安装包
    pkg = cfg["download"]["packages"].get("sms_agent", {})
    local_name = pkg.get("local_name", "SMS-Agent-Py3.exe")
    local_path = PROJECT_ROOT / "proxyopt" / OBS_CACHE_DIR / local_name
    if local_path.exists() and local_path.stat().st_size > 0:
        tasks.append((str(local_path), f"{DOWNLOADS_DIR}/{local_name}"))
    else:
        return False, f"沙箱缓存缺少 {local_name}"

    for local, remote in tasks:
        sz_local = os.path.getsize(local)
        out = run(c, f"stat -c %s {remote} 2>/dev/null || echo 0")
        try:
            sz_remote = int(out.splitlines()[-1].strip().split()[-1])
        except (ValueError, IndexError):
            sz_remote = 0
        if sz_remote == sz_local:
            continue
        if skip_upload:
            return False, f"--skip-upload 但 {Path(local).name} 大小不匹配"
        sftp = c.open_sftp()
        t0 = time.time()
        sftp.put(local, remote, confirm=False)
        sftp.close()
        print(f"    [UPLOAD] {Path(local).name} ({sz_local/1024/1024:.1f}MB) → {remote} "
              f"({time.time()-t0:.1f}s)", flush=True)

    listing = run(c, f"ls -l {DOWNLOADS_DIR}/")
    return True, "文件同步完成\n" + listing


def _ensure_http_server(c) -> tuple[bool, str]:
    """代理主机 8080 HTTP 文件服务（serve /data/downloads）。
    端口 + HTTP 响应双验证：端口监听但回源失败也视为未就绪并重启。
    修复：启动命令拆分为独立短命令（长驻 http server 曾导致 SSH channel 无法 EOF
    而 read 超时抛异常）；杀占用按 PID（避免 pkill -f 匹配远程 bash 自身自杀）。"""
    def _check() -> str:
        return run(c, "ss -tln | grep ':8080 ' || echo NOT_LISTEN", timeout=10)

    def _probe() -> str:
        return run(c, "curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8080/ || echo FAIL", timeout=15)

    if _check() and _probe() in ("200", "301", "302", "403"):
        return True, "HTTP 8080 已在监听且响应正常"
    # 按 PID 杀 8080 占用（避免 pkill -f 自杀）
    run(c, "P=$(ss -tlnp | grep ':8080 ' | grep -oP 'pid=\\K[0-9]+' | sort -u); [ -n \"$P\" ] && kill -9 $P; sleep 1", timeout=10)
    # 确保目录存在
    run(c, "mkdir -p /data/downloads && chmod 755 /data/downloads", timeout=10)
    # 启动 HTTP（独立短命令，后台进程 stdio 全部重定向，命令立即返回 PID）
    out = run(c, (
        "cd /data/downloads && setsid nohup python3 -m http.server 8080 "
        "> /var/log/http_downloads.log 2>&1 < /dev/null & echo HTTP_PID=$!"
    ), timeout=15)
    # 独立验证（最多 10s 探测，避免长驻进程阻塞 channel）
    ok = False
    for _ in range(5):
        time.sleep(2)
        if _probe() in ("200", "301", "302", "403"):
            ok = True
            break
    return ok, f"启动结果: {out.strip()[:120]} | probe={'OK' if ok else 'FAIL'}"


def _ensure_squid(c, cfg: dict) -> tuple[bool, str]:
    """上传 proxy_setup_squid.sh + 合并配置到代理主机并执行（幂等）。"""
    run(c, f"mkdir -p {REMOTE_SCRIPT_DIR}")
    script = "proxyopt/scripts/proxy_setup_squid.sh"
    remote_script = f"{REMOTE_SCRIPT_DIR}/proxy_setup_squid.sh"
    remote_config = f"{REMOTE_SCRIPT_DIR}/proxyopt_config.yaml"
    sftp = c.open_sftp()
    sftp.put(str(PROJECT_ROOT / script), remote_script)
    sftp.put(str(_proxyopt_config_path(cfg)), remote_config)
    sftp.close()
    out = run(c, f"bash {remote_script} --config {remote_config} 2>&1 | tail -6", timeout=300)
    return ("Squid 代理安装配置完成" in out or "正在监听" in out), out[-500:]


def _ensure_gost_systemd(c, cfg: dict) -> tuple[bool, str]:
    """gost 以 systemd 服务托管（修复 nohup 无托管问题）。"""
    ps = cfg["proxy_server"]
    src = cfg["source"]
    gost_port = ps.get("gost_listen_port", 15985)
    target = f"{src['host']}:{src.get('winrm_port', 5985)}"
    gost_bin = os.environ.get("PROXYOPT_GOST_BIN", "/usr/local/bin/gost")
    if "NO_GOST" in run(c, f"command -v gost || echo NO_GOST"):
        # 代理主机无 gost：从沙箱缓存自动分发（agent_pkgs/gost 或 proxyopt/downloads/gost）
        gost_local = PROJECT_ROOT / "agent_pkgs" / "gost"
        if not gost_local.exists():
            gost_local = PROJECT_ROOT / "proxyopt" / OBS_CACHE_DIR / "gost"
        if not gost_local.exists():
            return False, "代理主机未安装 gost 且沙箱无 gost 二进制缓存（agent_pkgs/gost）"
        print(f"    [UPLOAD] gost 二进制 → {gost_bin}", flush=True)
        sftp = c.open_sftp()
        sftp.put(str(gost_local), gost_bin, confirm=False)
        sftp.chmod(gost_bin, 0o755)
        sftp.close()
        if "NO_GOST" in run(c, f"command -v gost || echo NO_GOST"):
            return False, "gost 上传后仍不可用"
    unit = f"""[Unit]
Description=gost tunnel for proxyopt (WinRM forward)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={gost_bin} -L tcp://:{gost_port}/{target}
Restart=always
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
"""
    run(c, "systemctl stop gost-proxyopt 2>/dev/null || true; pkill -x gost 2>/dev/null; sleep 1")
    sftp = c.open_sftp()
    with sftp.file("/etc/systemd/system/gost-proxyopt.service", "w") as f:
        f.write(unit)
    sftp.close()
    run(c, "systemctl daemon-reload && systemctl enable gost-proxyopt && systemctl start gost-proxyopt", timeout=30)
    time.sleep(2)
    out = run(c, f"systemctl is-active gost-proxyopt; ss -tln | grep ':{gost_port} ' || echo NOT_LISTEN")
    ok = ("active" in out) or (f":{gost_port}" in out)
    return ok, out.strip()


def _precache(cfg: dict) -> tuple[bool, str]:
    """沙箱侧经 Squid 抓代理主机 HTTP 8080 预热缓存。

    配置开关：proxyopt/config/config.yaml -> sandbox.precache_enabled（默认 false）。
    新架构文件服务器已部署在代理主机，源端经 Squid 直取同网段文件，
    预热只是优化且依赖沙箱出口 IP，默认关闭；显式置 true 才执行。
    """
    base_config = PROJECT_ROOT / "proxyopt/config/config.yaml"
    try:
        with open(base_config, "r", encoding="utf-8") as f:
            base_cfg = yaml.safe_load(f) or {}
        if not base_cfg.get("sandbox", {}).get("precache_enabled", False):
            return True, "precache 已禁用（sandbox.precache_enabled=false，新架构无需预热）"
    except Exception as e:
        return False, f"读取 proxyopt 配置失败: {e}"
    precache_script = PROJECT_ROOT / "proxyopt/scripts/sandbox_precache.py"
    if not precache_script.exists():
        return False, "sandbox_precache.py 不存在"
    cfg_path = _proxyopt_config_path(cfg)
    env = dict(os.environ)
    env["PROXYOPT_CONFIG"] = str(cfg_path)
    r = subprocess.run(
        [sys.executable, str(precache_script), "--config", str(cfg_path)],
        capture_output=True, text=True, timeout=900, env=env,
        cwd=str(PROJECT_ROOT / "proxyopt"),
    )
    if r.returncode != 0:
        return False, (r.stdout + r.stderr)[-500:]
    return True, "preCache 完成（缺失文件 404 已跳过）"


def _verify(c, cfg: dict) -> tuple[bool, str]:
    ps = cfg["proxy_server"]
    squid_port = ps.get("squid_port", 3128)
    gost_port = ps.get("gost_listen_port", 15985)
    http_host = cfg.get("sandbox_host") or ps["host"]
    http_port = ps.get("http_server_port", 8080)
    out = run(c, f"ss -tln | grep -E ':{squid_port} |:{http_port} |:{gost_port} ' || echo NONE")
    checks = ["PORTS\n" + (out or "(none)")]
    pkg = cfg["download"]["packages"].get("sms_agent", {})
    probe_name = pkg.get("local_name", "SMS-Agent.exe")
    checks.append(run(c, f"curl -s -o /dev/null -w 'HTTP=%{{http_code}}\\n' --max-time 60 "
                         f"-x http://127.0.0.1:{squid_port} http://{http_host}:{http_port}/{probe_name} -r 0-99"))
    checks.append(run(c, f"timeout 5 bash -c 'cat < /dev/null > /dev/tcp/127.0.0.1/{gost_port}' 2>&1 && echo OPEN || echo CLOSED"))
    text = "\n".join(checks)
    ok = ("HTTP=200" in text or "HTTP=206" in text) and ("OPEN" in text)
    return ok, text


# ── proxyopt 运行时配置 ───────────────────────────────────

def _proxyopt_config_path(cfg: dict):
    """
    生成 proxyopt 运行时合并配置（写入 .config_jumpbox.yaml）。
    调用方决定用途：上传到代理主机（Squid 脚本）或沙箱本地（preCache 脚本）。
    关键注入：sandbox.obs_bucket/obs_endpoint/obsutil_path、sandbox.precache_host（=sandbox_host 或 proxy_server.host）、
    sandbox.serve_dir/download_dir 指向沙箱 OBS 缓存目录（绝对路径）、squid.host、gost.forward_rules（gost_listen_port→源端:winrm_port）。
    """
    base_config = PROJECT_ROOT / "proxyopt/config/config.yaml"
    with open(base_config, "r", encoding="utf-8") as f:
        merged = yaml.safe_load(f) or {}

    obs = cfg["obs"]
    ps = cfg["proxy_server"]
    src = cfg["source"]
    http_host = cfg.get("sandbox_host") or ps["host"]

    merged.setdefault("sandbox", {})
    merged["sandbox"]["obs_bucket"] = obs.get("bucket", "")
    merged["sandbox"]["obs_endpoint"] = obs.get("endpoint", "")
    merged["sandbox"]["obsutil_path"] = obs.get("obsutil_path", "obsutil")
    merged["sandbox"]["precache_host"] = http_host
    # serve_dir 与下载目录固定为沙箱中转目录（绝对路径，不依赖执行 cwd）
    obs_cache = PROJECT_ROOT / "proxyopt" / OBS_CACHE_DIR
    merged["sandbox"]["serve_dir"] = str(obs_cache)
    merged["sandbox"]["download_dir"] = str(obs_cache)

    merged.setdefault("squid", {})
    merged["squid"]["host"] = ps["host"]
    merged["squid"]["port"] = ps.get("squid_port", 3128)

    merged.setdefault("gost", {})
    merged["gost"]["host"] = ps["host"]
    merged["gost"]["forward_rules"] = [{
        "name": "winrm-windows-host",
        "listen_port": ps.get("gost_listen_port", 15985),
        "target_host": src["host"],
        "target_port": src.get("winrm_port", 5985),
    }]

    merged.setdefault("source", {})
    merged["source"]["download_dir"] = cfg.get("download", {}).get("source_download_dir") or "C:\\auto_agent_opt\\downloads"
    merged["source"]["hosts"] = [src["host"]]

    tmp_path = PROJECT_ROOT / "proxyopt/config/.config_jumpbox.yaml"
    with open(tmp_path, "w", encoding="utf-8") as f:
        yaml.dump(merged, f, default_flow_style=False, allow_unicode=True)

    # proxy_setup_* 脚本只需要 squid/gost 段（用于从 yaml 读取参数）；这里直接返回生成的文件路径
    return tmp_path


# ── CLI ──────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="跳板机一键就绪（私网文件服务器部署到代理主机）")
    ap.add_argument("--config", required=True, help="migrate.yaml 路径")
    ap.add_argument("--skip-upload", action="store_true", help="跳过安装包上传（仅检查）")
    ap.add_argument("--verify-only", action="store_true", help="仅验证不部署")
    args = ap.parse_args()

    cfg = load_config(args.config)

    if args.verify_only:
        c = ssh_client(cfg)
        try:
            ok, text = _verify(c, cfg)
        finally:
            c.close()
        print(text)
        return 0 if ok else 1

    results = deploy(cfg, skip_upload=args.skip_upload)
    all_ok = all(ok for ok, _ in results.values())
    print("\n==== 跳板机就绪 ====" if all_ok else "\n==== 存在失败步骤 ====")
    for step, (ok, msg) in results.items():
        print(f"  {'✅' if ok else '❌'} {step}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())