#!/usr/bin/env python3
"""DevBridge 调试用示例 Web 服务 — 纯标准库，零依赖。

用于验证 huawei-cloud-devbridge-tunnel skill 的端到端流程：
本地起服务 -> 建隧道 -> 配端口 -> host -> 公网访问。

端点:
  /         首页
  /healthz  健康检查
  /info     返回 JSON（进程/环境信息）
"""
import json
import os
import socket
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "0.0.0.0"   # host 时需要用非 loopback，devbridge host 才能转发
PORT = int(os.environ.get("PORT", "8080"))
STARTED = time.strftime("%Y-%m-%d %H:%M:%S")


class Handler(BaseHTTPRequestHandler):
    server_version = "DevBridgeDemo/1.0"

    def _send(self, code: int, body: bytes, ctype: str = "text/plain; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/healthz":
            self._send(200, b"ok")
            return
        if self.path == "/info":
            data = {
                "service": "devbridge-demo",
                "hostname": socket.gethostname(),
                "started_at": STARTED,
                "now": time.strftime("%Y-%m-%d %H:%M:%S"),
                "python": sys.version.split()[0],
            }
            self._send(200, json.dumps(data, ensure_ascii=False).encode(),
                       "application/json; charset=utf-8")
            return

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>DevBridge Demo</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:640px;margin:80px auto;padding:0 20px;color:#333}}
h1{{color:#0d5ae5}} code{{background:#f0f2f5;padding:2px 6px;border-radius:4px}}
.ok{{color:#0a7d34;font-weight:600}}
</style></head>
<body>
<h1>🚀 DevBridge 示例服务</h1>
<p>这是一个纯标准库的 Python Web 服务，用于验证 <code>huawei-cloud-devbridge-tunnel</code> skill 的隧道链路。</p>
<p>如果你能通过隧道看到本页面，说明整条链路：<code>本地服务 → devbridge host → 中继 → 公网</code> 已打通。</p>
<p class="ok">✓ 服务运行中（启动于 {STARTED}）</p>
<p>其他端点：<code>/healthz</code>（健康检查）、<code>/info</code>（JSON 信息）</p>
</body></html>
"""
        self._send(200, html.encode(), "text/html; charset=utf-8")

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), fmt % args))


if __name__ == "__main__":
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"DevBridge demo listening on http://{HOST}:{PORT}", flush=True)
    httpd.serve_forever()