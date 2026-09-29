#!/usr/bin/env python3
"""
gost_ops.py — GOST 代理服务操作

GOST 是一个用 Go 编写的简单隧道/代理工具，本模块用于在代理 ECS 上：
1. 安装 GOST
2. 配置 GOST 端口转发规则
3. 启动/停止/检查 GOST 服务
4. 验证转发连通性

GOST 在私网迁移中的角色：
  - 管理通道：代理ECS:22 → 源端:22 (操作端通过代理ECS SSH到源端)
  - 数据流转发：代理ECS:8899 → 目标ECS:8899 (SMS数据传输)
  - 数据流转发：代理ECS:8900 → 目标ECS:8900 (SMS数据传输)

端口规划（代理ECS上）：
  - sshd: 2222 (代理ECS自身管理，避免与GOST:22冲突)
  - GOST: 22 (管理通道，转发到源端:22)
  - GOST: 8899 (数据流，转发到目标ECS:8899)
  - GOST: 8900 (数据流，转发到目标ECS:8900)
  - squid: 3128 (控制流代理)
"""

import time
import logging
import json
import tempfile
import os
import re
import subprocess
import threading
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# GOST 版本和下载地址 (v3.2.6, 从 OBS 下载)
GOST_VERSION = "3.2.6"
GOST_BIN_PATH = "/usr/local/bin/gost"
GOST_CONFIG_DIR = "/etc/gost"
GOST_CONFIG_PATH = "/etc/gost/config.json"
GOST_SERVICE_PATH = "/etc/systemd/system/gost.service"
GOST_LOG_PATH = "/var/log/gost.log"

# GOST 保活参数 (防止长连接因空闲超时断开)
# keepalive=true          : 启用 TCP keepalive
# keepalive.idle=15s      : 空闲 15s 后开始发送 keepalive 探测
# keepalive.interval=5s   : 每 5s 发送一次探测
# keepalive.count=3       : 连续 3 次无响应则判定连接断开
GOST_KEEPALIVE_PARAMS = (
    "keepalive=true"
    "&keepalive.idle=15s"
    "&keepalive.interval=5s"
    "&keepalive.count=3"
)

# OBS 下载配置 (通过 obsutil 下载 GOST)
GOST_OBS_BUCKET = os.environ.get("GOST_OBS_BUCKET", "mwx1015471-mpz")
GOST_OBS_PREFIX = os.environ.get(
    "GOST_OBS_PREFIX",
    "Host-Migration/skill-packages/private_network",
)
GOST_OBS_REGION = os.environ.get("OBS_REGION", "cn-north-1")


@dataclass
class GOSTForwardRule:
    """GOST 端口转发规则"""
    local_port: int        # 代理ECS上监听端口
    target_host: str       # 目标主机IP
    target_port: int       # 目标端口
    description: str = ""  # 规则描述
    name: str = ""         # 规则名称 (用于去重和日志)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "local_port": self.local_port,
            "target_host": self.target_host,
            "target_port": self.target_port,
            "description": self.description,
        }


class GOSTOps:
    """GOST 代理服务操作"""

    # 类级锁: 保护 config.json 读写 + GOST 重启 (所有实例共享)
    _config_lock = threading.Lock()

    def __init__(self, ssh_client):
        """
        Args:
            ssh_client: 已连接的 SSH 客户端 (paramiko.SSHClient)，连接到代理 ECS
        """
        self.ssh = ssh_client

    def _exec(self, cmd: str, timeout: int = 30) -> Tuple[str, str, int]:
        """执行命令并返回 (stdout, stderr, exit_code)

        兼容两种 SSH 客户端:
          - ssh_utils.SSHClient: exec_command 返回 (out: str, err: str, code: int)
          - paramiko.SSHClient:  exec_command 返回 (stdin, stdout, stderr) 流对象
        """
        result = self.ssh.exec_command(cmd, timeout=timeout)
        # SSHClient wrapper already returns decoded strings
        if isinstance(result, tuple) and len(result) == 3 and isinstance(result[0], str):
            return result[0], result[1], result[2]
        # Raw paramiko returns (stdin, stdout, stderr) streams
        stdin, stdout, stderr = result
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        code = stdout.channel.recv_exit_status()
        return out, err, code

    def check_installed(self) -> bool:
        """检查 GOST 是否已安装"""
        out, _, code = self._exec(f"which gost 2>/dev/null || test -x {GOST_BIN_PATH}")
        return code == 0 or out != ""

    def _download_gost_local(self, goarch: str) -> Optional[str]:
        """在智能体本地用 obsutil 从 OBS 下载 GOST 压缩包。

        Returns:
            下载到本地的文件路径，失败返回 None
        """
        gost_filename = f"gost_{GOST_VERSION}_linux_{goarch}.tar.gz"
        gost_obs_key = f"{GOST_OBS_PREFIX}/{gost_filename}"
        gost_obs_uri = f"obs://{GOST_OBS_BUCKET}/{gost_obs_key}"
        local_path = f"/tmp/{gost_filename}"

        # 如果本地已存在且非空，跳过下载
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            logger.info(f"GOST 压缩包已存在: {local_path} ({os.path.getsize(local_path)} bytes)")
            return local_path

        logger.info(f"用 obsutil 下载 GOST: {gost_obs_uri} -> {local_path}")

        # 查找 obsutil 路径
        obsutil_path = None
        for candidate in ["/usr/local/bin/obsutil", os.path.expanduser("~/.local/bin/obsutil"), "/usr/bin/obsutil"]:
            if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                obsutil_path = candidate
                break
        if not obsutil_path:
            try:
                r = subprocess.run(["which", "obsutil"], capture_output=True, text=True, timeout=5)
                if r.returncode == 0 and r.stdout.strip():
                    obsutil_path = r.stdout.strip()
            except Exception:
                pass

        if not obsutil_path:
            logger.error("未找到 obsutil，请确保已安装并配置")
            return None

        # 执行 obsutil cp 下载
        cmd = [obsutil_path, "cp", gost_obs_uri, local_path, "-f"]
        logger.info(f"执行: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                logger.error(f"obsutil 下载失败 (code={result.returncode}): {result.stderr}")
                return None
        except subprocess.TimeoutExpired:
            logger.error("obsutil 下载超时")
            return None
        except Exception as e:
            logger.error(f"obsutil 下载异常: {e}")
            return None

        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            logger.info(f"GOST 下载成功: {local_path} ({os.path.getsize(local_path)} bytes)")
            return local_path
        else:
            logger.error(f"GOST 下载后文件不存在或为空: {local_path}")
            return None

    def _download_gost_public_fallback(self, goarch: str) -> Optional[str]:
        """公网 HTTPS 回退下载 GOST (仅当 OBS obsutil 下载失败时尝试)。

        回退顺序:
        1. OBS HTTPS URL (wget/curl) — 私网环境 OBS 内网 HTTPS 通常可达
        2. GitHub releases URL — 公网环境回退

        Returns:
            下载到本地的文件路径，失败返回 None
        """
        gost_filename = f"gost_{GOST_VERSION}_linux_{goarch}.tar.gz"
        local_path = f"/tmp/{gost_filename}"

        # ── 回退 1: OBS HTTPS URL (内网通常可达) ──
        gost_obs_key = f"{GOST_OBS_PREFIX}/{gost_filename}"
        obs_endpoint = os.environ.get(
            "GOST_OBS_ENDPOINT",
            "obs.cn-north-1.myhuaweicloud.com",
        )
        obs_https_url = f"https://{GOST_OBS_BUCKET}.{obs_endpoint}/{gost_obs_key}"

        logger.warning(f"OBS obsutil 下载失败，尝试 OBS HTTPS 回退: {obs_https_url}")

        try:
            import subprocess as _sp
            # 优先用 wget，其次 curl
            for downloader in ["wget", "curl"]:
                _r = _sp.run(["which", downloader], capture_output=True, text=True, timeout=5)
                if _r.returncode != 0:
                    continue
                if downloader == "wget":
                    cmd = ["wget", "-q", "-O", local_path, obs_https_url, "--timeout=30"]
                else:
                    cmd = ["curl", "-sS", "-o", local_path, obs_https_url, "--connect-timeout", "30"]
                logger.info(f"尝试 {downloader}: {obs_https_url}")
                result = _sp.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0 and os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                    logger.info(f"GOST OBS HTTPS 下载成功: {local_path} ({os.path.getsize(local_path)} bytes)")
                    return local_path
                else:
                    logger.warning(f"{downloader} 下载失败 (code={result.returncode}): {result.stderr[:200]}")
                    if os.path.exists(local_path):
                        os.remove(local_path)
            logger.warning("OBS HTTPS 回退失败 (wget/curl 均不可用或下载失败)")
        except Exception as e:
            logger.warning(f"OBS HTTPS 回退异常: {e}")

        # ── 回退 2: GitHub releases URL (公网环境) ──
        github_url = (
            f"https://github.com/go-gost/gost/releases/download/v{GOST_VERSION}/{gost_filename}"
        )

        logger.warning(f"OBS HTTPS 回退也失败，尝试 GitHub 公网回退: {github_url}")

        try:
            import urllib.request
            urllib.request.urlretrieve(github_url, local_path)
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                logger.info(f"GOST GitHub 公网下载成功: {local_path} ({os.path.getsize(local_path)} bytes)")
                return local_path
            else:
                logger.error("GOST GitHub 公网下载后文件不存在或为空")
                return None
        except Exception as e:
            logger.error(f"GOST GitHub 公网下载失败 (私网环境无公网访问): {e}")
            return None

    def install(self, arch: str = "arm64") -> bool:
        """
        安装 GOST 到代理 ECS。

        流程: 智能体本地用obsutil下载 (多endpoint重试) → SFTP上传到代理ECS → 远程解压安装
        纯 obsutil 方式，不尝试 HTTPS (避免私网环境 SSL 错误)

        Args:
            arch: CPU 架构 (arm64/amd64)

        Returns:
            安装是否成功
        """
        if self.check_installed():
            logger.info("GOST 已安装，跳过")
            return True

        logger.info(f"开始安装 GOST v{GOST_VERSION} (arch={arch})")

        # 确定 GOARCH (代理ECS通常是amd64)
        goarch = "arm64" if arch in ("arm64", "aarch64") else "amd64"

        # Step 1: 智能体本地用 obsutil 下载 GOST (纯 obsutil，不尝试 HTTPS)
        local_path = self._download_gost_local(goarch)
        if not local_path:
            # obsutil 失败：尝试切换 OBS endpoint 重试 (不走 HTTPS)
            alt_endpoints = [
                "obs.cn-north-1.myhuaweicloud.com",
                "obs.cn-north-4.myhuaweicloud.com",
            ]
            current_endpoint = os.environ.get("OBS_ENDPOINT", "")
            for ep in alt_endpoints:
                if ep == current_endpoint:
                    continue
                logger.warning(f"obsutil 下载失败，切换 endpoint 重试: {ep}")
                os.environ["OBS_ENDPOINT"] = ep
                # 重新配置 obsutil 指向新 endpoint
                try:
                    ak = os.environ.get("HUAWEICLOUD_SDK_AK", "")
                    sk = os.environ.get("HUAWEICLOUD_SDK_SK", "")
                    if ak and sk:
                        subprocess.run(
                            ["obsutil", "config", "-i=" + ak, "-k=" + sk, "-e=" + ep],
                            capture_output=True, text=True, timeout=15,
                        )
                except Exception:
                    pass
                local_path = self._download_gost_local(goarch)
                if local_path:
                    break
        if not local_path:
            logger.error("GOST 下载失败 (obsutil 所有 endpoint 均不可用)，无法继续")
            return False

        # Step 2: SFTP 上传到代理 ECS
        remote_tarball = f"/tmp/gost_{GOST_VERSION}_linux_{goarch}.tar.gz"
        logger.info(f"SFTP 上传: {local_path} -> 代理ECS:{remote_tarball}")
        try:
            if hasattr(self.ssh, 'upload_file'):
                self.ssh.upload_file(local_path, remote_tarball)
            else:
                sftp = self.ssh.open_sftp()
                sftp.put(local_path, remote_tarball)
                sftp.close()
            logger.info("SFTP 上传成功")
        except Exception as e:
            logger.error(f"SFTP 上传失败: {e}")
            return False

        # Step 3: 代理 ECS 上解压安装
        cmds = [
            f"cd /tmp && tar xzf {remote_tarball}",
            f"mv /tmp/gost {GOST_BIN_PATH} 2>/dev/null || true",
            f"find /tmp -name gost -type f -executable 2>/dev/null | head -1 | xargs -I{{}} mv {{}} {GOST_BIN_PATH} 2>/dev/null || true",
            f"chmod +x {GOST_BIN_PATH}",
            f"mkdir -p {GOST_CONFIG_DIR}",
        ]

        for cmd in cmds:
            out, err, code = self._exec(cmd, timeout=60)
            if code != 0 and "mv" not in cmd and "find" not in cmd:
                logger.warning(f"命令执行返回非零: {cmd} (code={code}, err={err})")

        # 验证安装
        if self.check_installed():
            out, _, _ = self._exec(f"{GOST_BIN_PATH} -V 2>&1 || true")
            logger.info(f"GOST 安装成功: {out}")
            return True
        else:
            logger.error("GOST 安装失败")
            return False

    def generate_config(self, rules: List[GOSTForwardRule]) -> dict:
        """
        生成 GOST 配置 (JSON 格式)。

        GOST v2 配置格式：
        {
            "ServeNodes": ["relay+tcp://:22", "relay+tcp://:8899", "relay+tcp://:8900"],
            "ChainNodes": ["relay+tcp://target:22", ...]
        }

        实际使用命令行参数更简洁，这里生成 systemd 服务文件配置。

        Args:
            rules: 转发规则列表

        Returns:
            配置字典
        """
        config = {
            "version": GOST_VERSION,
            "rules": [r.to_dict() for r in rules],
            "commands": []
        }

        for rule in rules:
            # GOST v3 端口转发命令: gost -L tcp://:LOCAL_PORT/TARGET_HOST:TARGET_PORT
            cmd = (
                f"{GOST_BIN_PATH} -L "
                f"\"tcp://:{rule.local_port}"
                f"/{rule.target_host}:{rule.target_port}"
                f"?{GOST_KEEPALIVE_PARAMS}\""
            )
            config["commands"].append({
                "rule": rule.description,
                "command": cmd,
            })

        return config

    def deploy_config(self, rules: List[GOSTForwardRule]) -> bool:
        """
        部署 GOST 配置并创建 systemd 服务。

        Args:
            rules: 转发规则列表

        Returns:
            部署是否成功
        """
        config = self.generate_config(rules)

        # 写入配置文件
        config_json = json.dumps(config, indent=2, ensure_ascii=False)
        self._exec(f"mkdir -p {GOST_CONFIG_DIR}")

        # 使用 heredoc 写入配置文件
        write_cmd = f"cat > {GOST_CONFIG_PATH} << 'GOSTEOF'\n{config_json}\nGOSTEOF"
        _, err, code = self._exec(write_cmd)
        if code != 0:
            logger.error(f"写入 GOST 配置失败: {err}")
            return False

        # 生成 systemd 服务文件
        # 多个转发规则用多个 ExecStartPre 或用一个脚本启动
        start_script = "#!/bin/bash\n"
        for cmd_info in config["commands"]:
            start_script += f"{cmd_info['command']} &\n"
        start_script += "wait\n"

        script_path = f"{GOST_CONFIG_DIR}/start.sh"
        write_script = f"cat > {script_path} << 'GOSTEOF'\n{start_script}\nGOSTEOF"
        self._exec(write_script)
        self._exec(f"chmod +x {script_path}")

        # systemd 服务文件
        service_content = f"""[Unit]
Description=GOST Proxy Service
After=network.target

[Service]
Type=simple
ExecStart={script_path}
# P3-9优化: 平滑重载支持 (systemctl reload gost)
# 发送 SIGTERM 给旧进程让其优雅退出，然后 systemd 自动启动新进程
ExecReload=/bin/kill -TERM $MAINPID
# 崩溃后自动重启
Restart=always
# 重启前等待时间
RestartSec=5s
# 限制文件描述符，在高并发转发时防止掉线
LimitNOFILE=65535
# 限制任务数
TasksMax=infinity
StandardOutput=append:{GOST_LOG_PATH}
StandardError=append:{GOST_LOG_PATH}

[Install]
WantedBy=multi-user.target
"""
        write_service = f"cat > {GOST_SERVICE_PATH} << 'GOSTEOF'\n{service_content}\nGOSTEOF"
        _, err, code = self._exec(write_service)
        if code != 0:
            logger.error(f"写入 systemd 服务文件失败: {err}")
            return False

        logger.info("GOST 配置部署完成")
        return True

    def add_forward(
        self,
        name: str,
        local_port: int,
        target_host: str,
        target_port: int,
        description: str = "",
    ) -> bool:
        """动态添加一条端口转发规则并重启 GOST 服务 (线程安全)。

        读取现有 config.json，追加规则，重新生成 systemd 启动脚本并重启。
        使用类级锁保护 config 读写 + 重启，避免并发竞态。

        Args:
            name: 规则名称 (用于去重和日志)
            local_port: 代理 ECS 上监听端口
            target_host: 目标主机 IP
            target_port: 目标端口
            description: 规则描述

        Returns:
            是否成功
        """
        return self.add_forwards_batch(
            [(name, local_port, target_host, target_port, description)]
        )

    def add_forwards_batch(
        self,
        forwards: List[Tuple[str, int, str, int, str]],
    ) -> bool:
        """批量添加端口转发规则，仅一次 config 写入 + 一次 GOST 重启 (线程安全)。

        解决 100 台并发时逐条 add_forward 导致的:
        - config.json 读写竞态 (丢更新)
        - 100 次 GOST 重启 (每次重启杀掉所有现有连接)

        Args:
            forwards: [(name, local_port, target_host, target_port, description), ...]

        Returns:
            是否成功
        """
        with self._config_lock:
            logger.info(f"Batch adding {len(forwards)} GOST forwards")

            # 读取现有配置 (锁内, 无竞态)
            config = self._load_config()
            rules = config.get("rules", [])

            # 批量去重 + 追加 (按 name 和 local_port 双重去重)
            new_names = {f[0] for f in forwards}
            new_ports = {f[1] for f in forwards}
            rules = [
                r for r in rules
                if r.get("name") not in new_names
                and r.get("local_port") not in new_ports
            ]

            for name, local_port, target_host, target_port, description in forwards:
                rule_entry = {
                    "name": name,
                    "local_port": local_port,
                    "target_host": target_host,
                    "target_port": target_port,
                    "description": description or name,
                }
                rules.append(rule_entry)
                logger.info(f"  + {name} :{local_port} -> {target_host}:{target_port}")

            config["rules"] = rules

            # 一次性部署所有规则
            forward_rules = [
                GOSTForwardRule(
                    local_port=r["local_port"],
                    target_host=r["target_host"],
                    target_port=r["target_port"],
                    description=r.get("description", r.get("name", "")),
                    name=r.get("name", ""),
                )
                for r in rules
            ]

            if not self.deploy_config(forward_rules):
                logger.error("Failed to deploy config after batch add")
                return False

            # 仅一次重启 (使用热重载, 避免中断现有连接)
            # 传入所有端口, 确保重启后端口就绪才返回
            all_ports = [r["local_port"] for r in rules]
            if not self.hot_reload(expected_ports=all_ports):
                logger.error("Failed to reload GOST after batch add")
                return False

            logger.info(f"Batch add complete: {len(forwards)} forwards, GOST restarted once, {len(all_ports)} ports ready")
            return True

    def remove_forward(self, name: str) -> bool:
        """移除一条端口转发规则并重启 GOST 服务 (线程安全)。

        Args:
            name: 规则名称

        Returns:
            是否成功
        """
        with self._config_lock:
            logger.info(f"Removing GOST forward: {name}")

            config = self._load_config()
            rules = config.get("rules", [])
            new_rules = [r for r in rules if r.get("name") != name]

            if len(new_rules) == len(rules):
                logger.warning(f"Forward rule '{name}' not found, nothing to remove")
                return True

            config["rules"] = new_rules

            forward_rules = [
                GOSTForwardRule(
                    local_port=r["local_port"],
                    target_host=r["target_host"],
                    target_port=r["target_port"],
                    description=r.get("description", r.get("name", "")),
                )
                for r in new_rules
            ]

            if forward_rules:
                self.deploy_config(forward_rules)
                remaining_ports = [r["local_port"] for r in new_rules]
                self.restart(expected_ports=remaining_ports)
            else:
                self.stop()

            logger.info(f"GOST forward removed: {name}")
            return True

    def list_forwards(self) -> List[Dict[str, Any]]:
        """列出当前所有转发规则。

        Returns:
            规则列表 [{name, local_port, target_host, target_port, description}, ...]
        """
        config = self._load_config()
        return config.get("rules", [])

    def _load_config(self) -> dict:
        """读取当前 GOST 配置文件。

        如果配置文件不存在或解析失败，返回空配置骨架。
        """
        out, _, code = self._exec(f"cat {GOST_CONFIG_PATH} 2>/dev/null")
        if code != 0 or not out:
            return {"version": GOST_VERSION, "rules": [], "commands": []}
        try:
            config = json.loads(out)
            if "rules" not in config:
                config["rules"] = []
            # 为旧格式规则补充 name 字段
            for i, r in enumerate(config["rules"]):
                if "name" not in r:
                    r["name"] = f"rule_{i}_{r.get('local_port', 'unknown')}"
            return config
        except json.JSONDecodeError:
            logger.warning("GOST config.json parse failed, starting fresh")
            return {"version": GOST_VERSION, "rules": [], "commands": []}

    def _wait_for_ports_ready(self, ports: List[int], timeout: int = 15) -> bool:
        """等待所有指定端口在代理ECS上开始监听。

        解决 GOST restart 后端口未完全就绪导致连接失败的问题。

        Args:
            ports: 需要等待的端口列表
            timeout: 最大等待秒数

        Returns:
            是否所有端口都已就绪
        """
        if not ports:
            return True

        start = time.time()
        while time.time() - start < timeout:
            all_ready = True
            for port in ports:
                out, _, _ = self._exec(f"ss -tlnp | grep ':{port} '")
                if not out:
                    all_ready = False
                    break
            if all_ready:
                logger.info(f"All {len(ports)} GOST ports ready after {round(time.time() - start, 1)}s")
                return True
            time.sleep(0.5)

        logger.warning(f"GOST ports not all ready after {timeout}s: {ports}")
        return False

    def start(self, expected_ports: List[int] = None) -> bool:
        """启动 GOST 服务

        Args:
            expected_ports: 启动后需要等待就绪的端口列表 (可选)

        Returns:
            是否成功
        """
        cmds = [
            "systemctl daemon-reload",
            "systemctl enable gost",
            "systemctl start gost",
        ]
        for cmd in cmds:
            _, err, code = self._exec(cmd)
            if code != 0:
                logger.warning(f"命令返回非零: {cmd} (err={err})")

        time.sleep(2)
        if not self.is_running():
            return False

        # 等待端口就绪 (解决 restart 后立即连接失败的问题)
        if expected_ports:
            return self._wait_for_ports_ready(expected_ports, timeout=15)
        return True

    def stop(self) -> bool:
        """停止 GOST 服务"""
        _, _, _ = self._exec("systemctl stop gost 2>/dev/null || true")
        # 确保 GOST 子进程也被清理 (systemd Type=simple 的 wait 脚本可能残留子进程)
        _, _, _ = self._exec("pkill -f 'gost -L' 2>/dev/null || true")
        time.sleep(0.5)
        return not self.is_running()

    def restart(self, expected_ports: List[int] = None) -> bool:
        """重启 GOST 服务

        Args:
            expected_ports: 重启后需要等待就绪的端口列表 (解决端口未就绪导致连接失败)

        Returns:
            是否成功
        """
        self.stop()
        time.sleep(1)
        return self.start(expected_ports=expected_ports)

    def hot_reload(self, expected_ports: List[int] = None) -> bool:
        """热重载 GOST 配置 (不中断现有连接)

        P3-9优化: 平滑重启策略
        1. 优先尝试 systemctl reload (ExecReload=SIGTERM)
        2. 不支持时使用 SIGTERM 优雅停止 + 快速启动
        3. 最后回退到 restart()

        Args:
            expected_ports: 重载后需要等待就绪的端口列表

        Returns:
            是否成功
        """
        # 尝试1: systemctl reload (使用 ExecReload 配置)
        _, _, reload_code = self._exec("systemctl reload gost 2>/dev/null")
        if reload_code == 0:
            logger.info("P3-9: GOST smooth reload via systemctl reload succeeded")
            if expected_ports:
                return self._wait_for_ports_ready(expected_ports, timeout=15)
            return True

        # 尝试2: 优雅 SIGTERM + 快速启动
        logger.info("P3-9: Attempting graceful restart (SIGTERM + quick start)")
        try:
            # 获取当前运行的 gost 进程
            old_pids_out, _, _ = self._exec("pgrep -f 'gost.*-L' || true")
            old_pids = [p.strip() for p in old_pids_out.split('\n') if p.strip()]

            if old_pids:
                # SIGTERM 让旧进程优雅退出 (完成现有连接后退出)
                for pid in old_pids:
                    self._exec(f"kill -TERM {pid} 2>/dev/null || true")
                logger.info(f"P3-9: Sent SIGTERM to {len(old_pids)} old GOST processes")
                # 等待旧进程退出 (短暂等待，让端口释放)
                time.sleep(2)
            else:
                logger.info("P3-9: No existing GOST processes found")

            # 启动新进程
            result = self.start(expected_ports=expected_ports)
            if result:
                logger.info("P3-9: Graceful restart succeeded")
            return result
        except Exception as e:
            logger.warning(f"P3-9: Graceful restart failed ({e}), falling back to full restart")
            return self.restart(expected_ports=expected_ports)

    def is_running(self) -> bool:
        """检查 GOST 服务是否运行"""
        out, _, _ = self._exec("systemctl is-active gost 2>/dev/null || true")
        return out.strip() == "active"

    def get_status(self) -> dict:
        """获取 GOST 服务状态"""
        running = self.is_running()
        out, _, _ = self._exec("systemctl status gost 2>/dev/null || true")
        return {
            "running": running,
            "status_text": out[:500] if out else "",
        }

    def verify_forwarding(self, local_port: int, target_host: str, target_port: int) -> bool:
        """
        验证端口转发是否工作。

        通过检查代理ECS上指定端口是否在监听来验证。

        Args:
            local_port: 代理ECS上监听端口
            target_host: 目标主机
            target_port: 目标端口

        Returns:
            转发是否正常
        """
        # 检查端口是否在监听
        out, _, _ = self._exec(f"ss -tlnp | grep ':{local_port} '")
        if not out:
            logger.warning(f"端口 {local_port} 未在监听")
            return False

        logger.info(f"端口 {local_port} 正在监听 (→ {target_host}:{target_port})")
        return True

    def verify_all(self, rules: List[GOSTForwardRule]) -> Dict[str, bool]:
        """验证所有转发规则"""
        results = {}
        for rule in rules:
            key = f"{rule.local_port}->{rule.target_host}:{rule.target_port}"
            results[key] = self.verify_forwarding(rule.local_port, rule.target_host, rule.target_port)
        return results

    def change_sshd_port(self, new_port: int = 2222) -> bool:
        """
        修改代理 ECS 的 sshd 端口，为 GOST:22 腾出端口。

        Args:
            new_port: 新的 sshd 端口 (默认 2222)

        Returns:
            修改是否成功
        """
        logger.info(f"修改 sshd 端口为 {new_port}")

        # 备份 sshd_config
        self._exec("cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak 2>/dev/null || true")

        # 修改端口
        cmds = [
            # 添加新端口 (保留 22 直到确认新端口可用)
            f"sed -i '/^#*Port /a Port {new_port}' /etc/ssh/sshd_config",
            # 重启 sshd
            "systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null || true",
        ]

        for cmd in cmds:
            _, err, code = self._exec(cmd)
            if code != 0:
                logger.warning(f"sshd 端口修改命令返回非零: {cmd} (err={err})")

        # 验证新端口可用
        time.sleep(2)
        out, _, _ = self._exec(f"ss -tlnp | grep ':{new_port} '")
        if out:
            logger.info(f"sshd 新端口 {new_port} 已启用")

            # 移除 Port 22 (GOST 将使用)
            self._exec("sed -i '/^Port 22$/d' /etc/ssh/sshd_config")
            self._exec("systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null || true")
            time.sleep(1)
            return True
        else:
            logger.error(f"sshd 新端口 {new_port} 未生效，恢复原配置")
            self._exec("cp /etc/ssh/sshd_config.bak /etc/ssh/sshd_config 2>/dev/null || true")
            self._exec("systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null || true")
            return False

    def cleanup(self) -> bool:
        """清理 GOST 服务和文件"""
        logger.info("清理 GOST 服务")
        self.stop()
        self._exec(f"rm -f {GOST_SERVICE_PATH}")
        self._exec(f"rm -rf {GOST_CONFIG_DIR}")
        self._exec(f"rm -f {GOST_BIN_PATH}")
        self._exec("systemctl daemon-reload")
        return True


def build_migration_rules(
    source_ip: str,
    source_ssh_port: int,
    target_ip: str,
    target_data_ports: List[int] = None,
) -> List[GOSTForwardRule]:
    """
    构建私网迁移所需的 GOST 转发规则。

    Args:
        source_ip: 源端 IP (VPN 对端可达)
        source_ssh_port: 源端 SSH 端口
        target_ip: 目标 ECS IP
        target_data_ports: 目标 ECS 数据端口列表 (默认 [8899, 8900])

    Returns:
        GOSTForwardRule 列表
    """
    if target_data_ports is None:
        target_data_ports = [8899, 8900]

    rules = [
        # 管理通道：代理ECS:22 → 源端:SSH
        GOSTForwardRule(
            local_port=22,
            target_host=source_ip,
            target_port=source_ssh_port,
            description="管理通道: 代理ECS:22 → 源端SSH",
        ),
    ]

    # 数据流转发：代理ECS:DATA_PORT → 目标ECS:DATA_PORT
    for port in target_data_ports:
        rules.append(GOSTForwardRule(
            local_port=port,
            target_host=target_ip,
            target_port=port,
            description=f"数据流: 代理ECS:{port} → 目标ECS:{port}",
        ))

    return rules


# 向后兼容别名: proxy_ecs_ops.py 等模块使用 GostOps 名称
GostOps = GOSTOps
