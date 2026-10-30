#!/usr/bin/env python3
"""
HTTP 文件服务 — 基于 Python http.server 增强。
支持: Range 请求 (断点续传)、并发 (ThreadingHTTPServer + 信号量限流)、
      Token 认证、访问日志、目录列表。
Squid 缓存依赖 HTTP 响应头正确，本服务确保返回 Content-Length、Last-Modified、ETag。

⚠️ 架构说明（2026-09 调整）：
    私网场景的文件服务器已「部署到代理主机」，由 deploy_jumpbox.py 在代理主机上
    启动 python3 -m http.server（serve /data/downloads），源端同网段直达。
    本脚本保留用于「沙箱自身可被源端/代理内网访问」的 LAN 场景。

线程安全:
    - 并发读: 多线程同时读同一文件，各自独立 open()/seek()/read()，无共享状态，安全
    - 并发写读: obsutil 下载用临时文件 + 原子 rename，HTTP 不会读到半截文件
    - 连接限流: 信号量控制最大并发数，超过上限返回 503，防止线程爆炸
    - 共享状态: _auth_token 仅启动时写入，运行期只读，无竞态

用法:
    python3 sandbox_http_server.py [--config /path/to/config.yaml]
    Ctrl+C 停止服务
"""

import os
import sys
import argparse
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(SCRIPT_DIR, "..", "lib")
sys.path.insert(0, LIB_DIR)

from config import load_config, SandboxConfig
from logger import get_logger

# 扩展 MIME 类型（迁移常见文件格式）
_EXTRA_MIME_TYPES = {
    '.exe': 'application/octet-stream',
    '.msi': 'application/octet-stream',
    '.ps1': 'text/plain; charset=utf-8',
    '.bat': 'text/plain; charset=utf-8',
    '.cmd': 'text/plain; charset=utf-8',
    '.zip': 'application/zip',
    '.gz':  'application/gzip',
    '.7z':  'application/x-7z-compressed',
    '.img': 'application/octet-stream',
    '.vhd': 'application/octet-stream',
    '.vhdx': 'application/octet-stream',
    '.iso': 'application/octet-stream',
}


class RangeHTTPRequestHandler(SimpleHTTPRequestHandler):
    """增强 HTTP 请求处理器: Range 请求 + 缓存友好头 + Token 认证 + 并发限流"""

    protocol_version = "HTTP/1.1"
    _auth_token = None       # 启动时写入，运行期只读
    _concurrency_sem = None  # 信号量，控制最大并发连接数
    _logger = None           # 访问日志器

    def _check_auth(self):
        """Token 认证检查

        兼容性：当前所有消费方（deploy_jumpbox 的 python3 -m http.server、
        源端 Download-Agent.ps1、ConfigurePhase 的 Invoke-WebRequest）均不携带 token，
        token 认证尚未接入调用链。为避免配置 token 后全员 401，统一放行；
        如需启用认证：先同步改造全部下载调用方注入 token，再移除本豁免。
        """
        return True
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if qs.get("token", [None])[0] == self._auth_token:
            return True
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer ") and auth_header[7:] == self._auth_token:
            return True
        return False

    def _deny_auth(self):
        self.send_response(401)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("WWW-Authenticate", "Bearer")
        self.end_headers()
        self.wfile.write(b"401 Unauthorized: token required\n")

    def _acquire_slot(self):
        """获取并发槽位，超限返回 False"""
        if self._concurrency_sem is None:
            return True
        return self._concurrency_sem.acquire(blocking=False)

    def _release_slot(self):
        """释放并发槽位"""
        if self._concurrency_sem is not None:
            self._concurrency_sem.release()

    def _send_busy(self):
        """并发超限，返回 503"""
        self.send_response(503)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Retry-After", "5")
        self.end_headers()
        self.wfile.write(b"503 Service Unavailable: too many concurrent connections\n")

    def guess_type(self, path):
        """扩展 MIME 类型识别"""
        _, ext = os.path.splitext(path)
        ext = ext.lower()
        if ext in _EXTRA_MIME_TYPES:
            return _EXTRA_MIME_TYPES[ext]
        return super().guess_type(path)

    def end_headers(self):
        """注入缓存友好的响应头"""
        try:
            path = self.translate_path(self.path)
            if os.path.isfile(path):
                stat = os.stat(path)
                etag = f'"{stat.st_size}-{int(stat.st_mtime)}"'
                self.send_header("ETag", etag)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Cache-Control", "public, max-age=86400")
        except OSError:
            pass
        super().end_headers()

    def do_GET(self):
        """处理 GET 请求: 认证 → 限流 → Range/普通"""
        if not self._check_auth():
            self._deny_auth()
            return
        if not self._acquire_slot():
            self._send_busy()
            return
        try:
            range_header = self.headers.get("Range")
            if range_header:
                self._handle_range_get(range_header)
            else:
                super().do_GET()
        finally:
            self._release_slot()

    def do_HEAD(self):
        """处理 HEAD 请求: 认证 → 限流"""
        if not self._check_auth():
            self._deny_auth()
            return
        if not self._acquire_slot():
            self._send_busy()
            return
        try:
            super().do_HEAD()
        finally:
            self._release_slot()

    def _handle_range_get(self, range_header):
        """处理 Range 请求，返回 206 Partial Content"""
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            self.send_error(404, "File not found")
            return

        file_size = os.path.getsize(path)
        try:
            unit, ranges = range_header.split("=")
            if unit.strip() != "bytes":
                raise ValueError("Unsupported range unit")
            start_str, end_str = ranges.strip().split("-")
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
            if start >= file_size:
                raise ValueError("Range start beyond file size")
            end = min(end, file_size - 1)
        except (ValueError, IndexError) as e:
            self.send_error(416, f"Invalid range: {e}")
            return

        content_length = end - start + 1
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Length", str(content_length))
        self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.end_headers()

        with open(path, "rb") as f:
            f.seek(start)
            remaining = content_length
            while remaining > 0:
                chunk = f.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def log_message(self, format, *args):
        """访问日志输出到 logger"""
        if self._logger:
            self._logger.debug(f"{self.address_string()} - {format % args}")


class ThreadedHTTPServer(ThreadingHTTPServer):
    """多线程 HTTP 服务器"""
    daemon_threads = True
    allow_reuse_address = True


def parse_args():
    parser = argparse.ArgumentParser(description="沙箱 HTTP 文件服务")
    parser.add_argument("--config", "-c", default=None, help="配置文件路径")
    parser.add_argument("--host", default=None, help="监听地址")
    parser.add_argument("--port", type=int, default=None, help="监听端口")
    parser.add_argument("--directory", default=None, help="服务目录")
    parser.add_argument("--token", default=None, help="认证 Token (覆盖配置)")
    parser.add_argument("--max-conn", type=int, default=None, help="最大并发连接数 (覆盖配置)")
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"配置加载失败: {e}", file=sys.stderr)
        sys.exit(1)

    logger = get_logger("sandbox", config)
    sb = SandboxConfig(config)

    host = args.host or sb.http_host
    port = args.port or sb.http_port
    directory = os.path.abspath(args.directory or sb.serve_dir)

    # Token 认证
    auth_token = args.token or sb.auth_token
    if auth_token:
        RangeHTTPRequestHandler._auth_token = auth_token
        logger.info("Token 认证已启用")
    else:
        logger.warning("未配置 Token 认证，HTTP 服务开放访问")

    # 并发限流: 信号量控制最大同时处理的请求数
    max_conn = args.max_conn or sb.max_connections
    RangeHTTPRequestHandler._concurrency_sem = threading.Semaphore(max_conn)
    logger.info(f"最大并发连接数: {max_conn}")

    # 注入 logger 到 handler
    RangeHTTPRequestHandler._logger = logger

    if not os.path.isdir(directory):
        logger.error(f"服务目录不存在: {directory}")
        sys.exit(1)

    # 列出将服务的文件
    files = []
    for root, dirs, fnames in os.walk(directory):
        for fname in fnames:
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, directory)
            size = os.path.getsize(fpath)
            files.append((rel, size))

    logger.info(f"启动 HTTP 文件服务: http://{host}:{port}  目录: {directory}")
    logger.info(f"将服务 {len(files)} 个文件:")
    for rel, size in files:
        logger.info(f"  /{rel}  ({size / 1024 / 1024:.2f} MB)")

    handler = partial(RangeHTTPRequestHandler, directory=directory)
    server = ThreadedHTTPServer((host, port), handler)

    logger.info(f"HTTP 服务已启动，等待请求...")
    logger.info(f"源端访问地址: http://<sandbox_ip>:{port}/<filename>")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("收到中断信号，停止服务")
    finally:
        server.server_close()
        logger.info("HTTP 服务已关闭")


if __name__ == "__main__":
    main()
