#!/usr/bin/env python3
"""shot_app.py — 通用截图脚本（须放在 scripts/ 下以便解析 browser_launch）

用法: python shot_app.py <appUrl> [outputPath]
"""

import os
import sys
import tempfile
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from playwright.sync_api import sync_playwright
    from browser_launch import launch_browser
except ImportError as e:
    sys.exit(
        "❌ 缺少 Python 依赖 playwright（截图必需）。请先运行渲染前 preflight 自动补齐：\n"
        "   bash <skill>/scripts/preflight.sh   （或 Windows: powershell preflight.ps1）\n"
        "   或手动安装：python -m pip install playwright && python -m playwright install chromium\n"
        f"   原始错误: {e}"
    )

app_url = sys.argv[1] if len(sys.argv) > 1 else ""
if not app_url:
    sys.exit("用法: python shot_app.py <appUrl> [outputPath]")
out = sys.argv[2] if len(sys.argv) > 2 else str(Path(tempfile.gettempdir()) / "work-screenshot.png")

with sync_playwright() as pw:
    browser = launch_browser(pw)
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.goto(app_url, wait_until="domcontentloaded", timeout=30000)
    try:
        page.evaluate("() => document.fonts.ready")
    except Exception:
        pass
    page.wait_for_timeout(2000)
    page.screenshot(path=out, full_page=False)
    browser.close()
    print(f"截图已保存: {out}")
