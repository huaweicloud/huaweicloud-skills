#!/usr/bin/env python3
"""
预缓存脚本 — 沙箱主动通过 Squid 代理请求自身 HTTP 服务，
触发 Squid 缓存所有文件。预缓存完成后才允许源端下载。

流程:
    对每个文件:
        curl -x http://squid:3128 http://sandbox:8080/filename
    → Squid 从沙箱 HTTP 服务拉取并缓存
    → 后续源端请求命中缓存，不再回源

用法:
    python3 sandbox_precache.py [--config /path/to/config.yaml]
"""

import os
import sys
import time
import argparse
import subprocess
from pathlib import Path
from urllib.parse import quote

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(SCRIPT_DIR, "..", "lib")
sys.path.insert(0, LIB_DIR)

from config import load_config, SandboxConfig, SquidConfig
from logger import get_logger


def parse_args():
    parser = argparse.ArgumentParser(description="通过 Squid 代理预缓存所有文件")
    parser.add_argument("--config", "-c", default=None, help="配置文件路径")
    parser.add_argument("--timeout", type=int, default=300, help="单文件请求超时(秒)")
    parser.add_argument("--concurrent", type=int, default=4, help="并发预缓存数 (默认4)")
    return parser.parse_args()


def list_files_to_cache(serve_dir, logger):
    """列出需要预缓存的文件列表（相对路径）"""
    serve_path = Path(serve_dir)
    if not serve_path.is_dir():
        logger.error(f"服务目录不存在: {serve_dir}")
        return []

    files = []
    for f in serve_path.rglob("*"):
        if f.is_file():
            rel = f.relative_to(serve_path).as_posix()  # URL 用正斜杠
            files.append((rel, f.stat().st_size))

    logger.info(f"待预缓存文件数: {len(files)}")
    return files


def precache_file(file_url, squid_proxy, timeout, logger, max_retries=3):
    """
    通过 Squid 代理请求单个文件，触发缓存。
    使用 curl，带重试。
    """
    cmd = [
        "curl",
        "-s",                    # 静默模式
        "--fail",               # HTTP 错误时返回非零退出码
        "-o", "/dev/null",       # 丢弃内容（只触发缓存）
        "-w", "%{http_code}",    # 输出 HTTP 状态码
        "-x", squid_proxy,       # 代理
        "--connect-timeout", "10",
        "--max-time", str(timeout),
        file_url,
    ]

    for attempt in range(1, max_retries + 1):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
            http_code = result.stdout.strip()

            if http_code in ("200", "206"):
                logger.debug(f"预缓存成功: {file_url}", extra={"http_code": http_code})
                return True
            elif http_code == "404":
                # 404: 分发源（代理主机 HTTP 目录）无此文件，跳过而非失败
                logger.warning(f"预缓存跳过（404: 分发源无此文件）: {file_url}")
                return True
            else:
                logger.warning(f"预缓存返回非200", extra={
                    "url": file_url, "http_code": http_code, "attempt": attempt,
                })
        except subprocess.TimeoutExpired:
            logger.warning(f"预缓存超时", extra={"url": file_url, "attempt": attempt})
        except Exception as e:
            logger.warning(f"预缓存异常: {e}", extra={"url": file_url, "attempt": attempt})

        if attempt < max_retries:
            time.sleep(2)

    logger.error(f"预缓存失败（重试 {max_retries} 次）: {file_url}")
    return False


def verify_cache_hit(file_url, squid_proxy, timeout, logger):
    """
    验证文件是否确实被 Squid 缓存。
    第二次请求应返回 X-Cache: HIT (或类似头)。
    """
    cmd = [
        "curl",
        "-s",
        "-D", "-",               # 输出响应头
        "-o", "/dev/null",
        "-x", squid_proxy,
        "--connect-timeout", "10",
        "--max-time", str(timeout),
        file_url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
        headers = result.stdout.lower()
        # Squid 通常返回 X-Cache: HIT 或 Age: >0
        if "x-cache" in headers and "hit" in headers:
            return True
        if "age:" in headers:
            # Age 头存在说明缓存命中
            for line in result.stdout.split("\n"):
                if line.lower().startswith("age:"):
                    try:
                        age_val = int(line.split(":")[1].strip())
                        if age_val > 0:
                            return True
                    except (ValueError, IndexError):
                        continue
        return None  # 无法确定
    except Exception:
        return None


def main():
    args = parse_args()

    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"配置加载失败: {e}", file=sys.stderr)
        sys.exit(1)

    logger = get_logger("sandbox", config)
    sb = SandboxConfig(config)
    sq = SquidConfig(config)

    logger.step("precache", "START")

    # 构建代理 URL 和服务 URL
    squid_host = config.get("squid.host", "127.0.0.1")
    squid_port = sq.port
    squid_proxy = f"http://{squid_host}:{squid_port}"

    # 沙箱自身地址（从沙箱视角访问，用配置或自动检测）
    sandbox_host = sb.precache_host or sb.http_host
    sandbox_port = sb.http_port
    base_url = f"http://{sandbox_host}:{sandbox_port}"

    logger.info(f"预缓存配置", extra={
        "squid_proxy": squid_proxy,
        "base_url": base_url,
        "serve_dir": sb.serve_dir,
        "concurrent": args.concurrent,
    })

    # 列出文件
    files = list_files_to_cache(sb.serve_dir, logger)
    if not files:
        logger.error("没有文件需要预缓存")
        sys.exit(1)

    # 逐个预缓存
    success_count = 0
    fail_count = 0
    start_time = time.time()

    for i, (rel_path, size) in enumerate(files, 1):
        url = f"{base_url}/{quote(rel_path)}"
        size_mb = size / 1024 / 1024
        logger.info(f"[{i}/{len(files)}] 预缓存: {rel_path} ({size_mb:.2f} MB)")

        if precache_file(url, squid_proxy, args.timeout, logger):
            success_count += 1
        else:
            fail_count += 1

    elapsed = time.time() - start_time
    logger.timing("precache_all", elapsed)

    # 汇总
    logger.info(f"预缓存汇总", extra={
        "total": len(files),
        "success": success_count,
        "failed": fail_count,
        "elapsed_sec": f"{elapsed:.1f}",
    })

    if fail_count > 0:
        logger.error(f"有 {fail_count} 个文件预缓存失败")
        logger.step("precache", "FAILED")
        sys.exit(1)

    # 验证缓存命中（抽样验证第一个文件）
    if files:
        sample_url = f"{base_url}/{quote(files[0][0])}"
        hit = verify_cache_hit(sample_url, squid_proxy, args.timeout, logger)
        if hit is True:
            logger.info("缓存命中验证通过 (HIT)")
        elif hit is None:
            logger.info("缓存命中验证不确定（Squid 可能未返回 X-Cache 头，但不影响功能）")
        else:
            logger.warning("缓存命中验证未通过，请检查 Squid 配置")

    logger.step("precache", "DONE")
    logger.info("预缓存阶段完成，源端可以开始下载")


if __name__ == "__main__":
    main()
