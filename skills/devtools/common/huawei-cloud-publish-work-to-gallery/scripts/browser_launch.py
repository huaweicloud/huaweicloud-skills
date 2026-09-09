#!/usr/bin/env python3
"""browser_launch.py — 跨平台 Playwright 浏览器启动（公共模块）

策略: 全平台优先用系统浏览器（channel 走 Playwright 内置解析），
      均不可用则回退 bundled Chromium。Linux/macOS 额外传 --no-sandbox。
      arm64 Linux 无 npmmirror 镜像时，系统 Chrome/Chromium 可跳过 ~300MB 下载。

用法:
  from browser_launch import launch_browser
  browser = launch_browser(playwright)
"""

import sys

IS_WINDOWS = sys.platform == "win32"
IS_UNIX = not IS_WINDOWS
NO_SANDBOX_ARGS = ["--no-sandbox"] if IS_UNIX else []


def launch_browser(playwright):
    """启动浏览器，优先复用系统 Edge/Chrome，回退 bundled Chromium。

    Args:
        playwright: sync_playwright().start() 返回的 Playwright 实例

    Returns:
        Browser 实例
    """
    channels = ["msedge", "chrome"] if IS_WINDOWS else ["chrome"]
    for channel in channels:
        try:
            return playwright.chromium.launch(
                headless=True, channel=channel, args=NO_SANDBOX_ARGS
            )
        except Exception:
            pass
    return playwright.chromium.launch(headless=True, args=NO_SANDBOX_ARGS)
