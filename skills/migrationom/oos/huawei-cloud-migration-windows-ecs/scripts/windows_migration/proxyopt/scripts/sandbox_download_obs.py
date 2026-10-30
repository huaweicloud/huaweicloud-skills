#!/usr/bin/env python3
"""
沙箱侧 OBS 下载脚本 — 从 OBS 拉取迁移工具包到本地目录。
使用 obsutil CLI 工具，带校验、重试、进度日志。

用法:
    python3 sandbox_download_obs.py [--config /path/to/config.yaml]

前置条件:
    - obsutil 已安装并配置 (obsutil config)
    - config.yaml 中已配置 OBS 桶名、路径、endpoint
"""

import os
import sys
import time
import subprocess
import argparse
from pathlib import Path

# 将 lib 目录加入 sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(SCRIPT_DIR, "..", "lib")
sys.path.insert(0, LIB_DIR)

from config import load_config, SandboxConfig
from logger import get_logger


def parse_args():
    parser = argparse.ArgumentParser(description="从 OBS 下载迁移工具包到沙箱本地目录")
    parser.add_argument("--config", "-c", default=None, help="配置文件路径")
    parser.add_argument("--dry-run", action="store_true", help="只打印命令不实际执行")
    return parser.parse_args()


def check_obsutil(obsutil_path, logger):
    """检查 obsutil 是否可用"""
    try:
        result = subprocess.run(
            [obsutil_path, "version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            logger.info(f"obsutil 可用: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"obsutil 不可用", extra={"stderr": result.stderr.strip()})
            return False
    except FileNotFoundError:
        logger.error(f"obsutil 未找到", extra={"path": obsutil_path})
        return False
    except Exception as e:
        logger.error(f"检查 obsutil 失败: {e}")
        return False


def download_from_obs(obsutil_path, bucket, prefix, local_dir, endpoint, logger, dry_run=False):
    """
    执行 obsutil cp 命令，从 OBS 递归下载到本地目录。
    命令: obsutil cp obs://bucket/prefix local_dir -r -f -j 5
    """
    obs_uri = f"obs://{bucket}/{prefix}" if prefix else f"obs://{bucket}"

    cmd = [
        obsutil_path, "cp", obs_uri, local_dir,
        "-r",        # 递归
        "-f",        # 强制覆盖
        "-flat",     # 扁平下载（不保留 OBS 路径层级）
        "-j", "5",   # 并发数
    ]
    if endpoint:
        cmd.extend(["-e", endpoint])

    logger.info(f"执行 OBS 下载", extra={
        "obs_uri": obs_uri,
        "local_dir": local_dir,
    })

    if dry_run:
        logger.info(f"[DRY-RUN] {' '.join(cmd)}")
        return True

    try:
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        elapsed = time.time() - start
        logger.timing("obs_download", elapsed)

        if result.returncode == 0:
            logger.info(f"OBS 下载成功", extra={"elapsed_sec": f"{elapsed:.1f}"})
            if result.stdout:
                logger.debug(f"obsutil stdout: {result.stdout[-500:]}")
            return True
        else:
            logger.error(f"OBS 下载失败", extra={
                "returncode": result.returncode,
                "stderr": result.stderr.strip()[-500:] if result.stderr else "",
            })
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"OBS 下载超时 (3600s)")
        return False
    except Exception as e:
        logger.error(f"OBS 下载异常: {e}")
        return False


def verify_downloads(local_dir, logger):
    """验证下载目录非空，列出文件清单，检查文件完整性"""
    download_path = Path(local_dir)
    if not download_path.exists():
        logger.error(f"下载目录不存在: {local_dir}")
        return False

    files = list(download_path.rglob("*"))
    file_list = [f for f in files if f.is_file()]

    if not file_list:
        logger.warning(f"下载目录为空: {local_dir}")
        return False

    total_size = sum(f.stat().st_size for f in file_list)
    logger.info(f"下载验证通过", extra={
        "file_count": len(file_list),
        "total_size_mb": f"{total_size / 1024 / 1024:.2f}",
    })

    # 检查每个文件非零大小（完整性快速校验）
    zero_size_files = []
    for f in file_list:
        rel = f.relative_to(download_path)
        size = f.stat().st_size
        if size == 0:
            zero_size_files.append(str(rel))
            logger.warning(f"零大小文件: {rel}")
        else:
            size_mb = size / 1024 / 1024
            logger.debug(f"  {rel} ({size_mb:.2f} MB)")

    if zero_size_files:
        logger.error(f"发现 {len(zero_size_files)} 个零大小文件，下载可能不完整",
                      extra={"files": ",".join(zero_size_files)})
        return False

    return True


def main():
    args = parse_args()

    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"配置加载失败: {e}", file=sys.stderr)
        sys.exit(1)

    logger = get_logger("sandbox", config)
    sb = SandboxConfig(config)

    logger.step("obs_download", "START")
    logger.info(f"配置文件: {config.config_path}")

    # 检查必需参数
    if not sb.obs_bucket:
        logger.error("配置缺少 sandbox.obs_bucket")
        sys.exit(1)

    # 确保下载目录存在
    os.makedirs(sb.download_dir, exist_ok=True)
    logger.info(f"下载目录: {sb.download_dir}")

    # 检查 obsutil
    if not check_obsutil(sb.obsutil_path, logger):
        logger.error("obsutil 检查未通过，退出")
        sys.exit(1)

    # 带重试的下载
    success = False
    for attempt in range(1, sb.max_retries + 1):
        logger.info(f"下载尝试 {attempt}/{sb.max_retries}")

        if download_from_obs(
            sb.obsutil_path, sb.obs_bucket, sb.obs_prefix,
            sb.download_dir, sb.obs_endpoint, logger, args.dry_run
        ):
            success = True
            break

        if attempt < sb.max_retries:
            logger.warning(f"等待 {sb.retry_interval}s 后重试...")
            time.sleep(sb.retry_interval)

    if not success:
        logger.error(f"OBS 下载失败，已重试 {sb.max_retries} 次")
        logger.step("obs_download", "FAILED")
        sys.exit(1)

    # 验证下载结果
    if not args.dry_run:
        if not verify_downloads(sb.download_dir, logger):
            logger.error("下载验证失败")
            logger.step("obs_download", "FAILED")
            sys.exit(1)

    logger.step("obs_download", "DONE")
    logger.info("OBS 下载阶段完成")


if __name__ == "__main__":
    main()
