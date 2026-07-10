#!/usr/bin/env python3
"""
华为云文档搜索工具（Playwright版）
从 CDIOsmAgent 的 web_fetcher_tool.py 提取并解耦
- 去除 langchain 依赖，改为纯 Python + CLI
- 去除 cdiosmagent config 依赖，改用环境变量 REMOTE_CHROME_HOST
- 保留完整 Playwright 搜索能力（模拟真实用户在华为云支持网站搜索）

Usage:
    python web_searcher.py search "关键词" [--site DOMAIN] [--max-results N] [--remote-chrome-host URL]

Args:
    keywords: 搜索关键词
    --site: 搜索站点域名，默认 support.huaweicloud.com
    --max-results: 最大返回结果数，默认5
    --remote-chrome-host: 远程Chrome地址，如 http://host:port

Returns:
    JSON dict with keys:
        success (bool): 是否成功
        results (list): 搜索结果列表，每项含 rank/title/url/snippet
        message (str): 失败时的错误信息
"""
import argparse
import asyncio
import atexit
import json
import logging
import os
import random
import re
import sys
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse, parse_qs

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    import aiohttp
    from playwright.async_api import async_playwright, Browser, Page, Playwright
except ImportError:
    aiohttp = None
    Browser = None
    Page = None
    Playwright = None
    logger.warning("playwright 或 aiohttp 未安装，搜索功能不可用。请运行: pip install playwright aiohttp && playwright install chromium")


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class WebSearcher:
    def __init__(self, remote_chrome_url: Optional[str] = None, headless: bool = True):
        self.remote_chrome_url = remote_chrome_url
        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._lock = asyncio.Lock()

    async def _get_browser(self) -> Browser:
        async with self._lock:
            if self._browser is not None:
                try:
                    if self._browser.is_connected():
                        return self._browser
                    else:
                        logger.warning("[WebSearcher] browser连接已断开，准备重新连接")
                        self._browser = None
                        if self._playwright:
                            try:
                                await self._playwright.stop()
                            except Exception:
                                pass
                            self._playwright = None
                except Exception:
                    self._browser = None
                    self._playwright = None

            self._playwright = await async_playwright().start()
            if self.remote_chrome_url:
                logger.info(f"[WebSearcher] 尝试连接远程Chrome: {self.remote_chrome_url}")
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                        async with session.get(self.remote_chrome_url) as response:
                            if response.status != 200:
                                raise ValueError(f"获取远程Chrome信息失败，HTTP状态码: {response.status}")
                            chrome_info = await response.json()
                            ws_endpoint = chrome_info.get("webSocketDebuggerUrl")
                            if not ws_endpoint:
                                raise ValueError("无法从远程Chrome获取webSocketDebuggerUrl")
                            self._browser = await self._playwright.chromium.connect_over_cdp(
                                ws_endpoint, timeout=30000
                            )
                            logger.info(f"[WebSearcher] 成功连接到远程Chrome")
                except Exception as e:
                    logger.error(f"[WebSearcher] 连接远程Chrome失败: {e}", exc_info=True)
                    raise
            else:
                logger.info("[WebSearcher] 启动本地Chrome浏览器")
                self._browser = await self._playwright.chromium.launch(
                    channel="chrome",
                    headless=self.headless,
                    args=[
                        "--disable-gpu",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                logger.info("[WebSearcher] 本地Chrome浏览器启动成功")
        return self._browser

    async def close(self):
        async with self._lock:
            if self._browser:
                try:
                    if not self.remote_chrome_url:
                        await self._browser.close()
                except Exception as e:
                    logger.error(f"关闭browser失败: {e}")
                self._browser = None
            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception as e:
                    logger.error(f"停止playwright失败: {e}")
                self._playwright = None

    async def _random_wait(self, min_s: float, max_s: float):
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def search(self, keywords: str, site: str = "support.huaweicloud.com", max_results: int = 5) -> List[Dict]:
        results = []
        base_url = f"https://{site}"
        page = None
        context = None
        search_result_page = None
        try:
            logger.info(f"[WebSearcher] 开始搜索: {keywords}")
            browser = await self._get_browser()
            context = await browser.new_context(
                user_agent=USER_AGENT,
                ignore_https_errors=True,
            )
            await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'automation', {get: () => undefined});
            """)
            page = await context.new_page()
            await page.set_extra_http_headers({"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})

            logger.info(f"[WebSearcher] 打开首页: {base_url}")
            await page.goto(base_url, timeout=60000, wait_until="domcontentloaded")
            await self._random_wait(1.2, 2.5)

            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except asyncio.TimeoutError:
                pass

            search_inputs = await page.query_selector_all("input[placeholder*='搜索']")
            search_input = None
            for inp in search_inputs:
                try:
                    if await inp.is_visible():
                        search_input = inp
                        break
                except Exception:
                    continue

            if not search_input:
                logger.error("[WebSearcher] 未找到可见的搜索框")
                return []

            await search_input.click()
            await self._random_wait(0.3, 0.6)
            await search_input.fill(keywords)
            await self._random_wait(0.5, 1.0)

            search_icon = await page.query_selector(".por-icon-search")
            if not search_icon:
                logger.error("[WebSearcher] 未找到搜索图标")
                return []

            async with context.expect_page(timeout=15000) as new_page_info:
                await search_icon.click()

            try:
                search_result_page = await new_page_info.value
            except Exception:
                search_result_page = page

            await self._random_wait(2.0, 3.0)

            try:
                await search_result_page.wait_for_load_state("load", timeout=15000)
            except asyncio.TimeoutError:
                pass

            await self._random_wait(1.0, 2.0)

            try:
                await search_result_page.wait_for_selector(".result-item", timeout=12000, state="attached")
            except asyncio.TimeoutError:
                pass

            await self._random_wait(1.0, 2.0)

            result_items = await search_result_page.query_selector_all(".result-item")
            logger.info(f"[WebSearcher] 找到 {len(result_items)} 个结果")

            for idx in range(min(len(result_items), max_results)):
                try:
                    item = result_items[idx]
                    a_tag = await item.query_selector("a")
                    if not a_tag:
                        continue
                    title = (await a_tag.inner_text()).strip()
                    link = await a_tag.get_attribute("href")
                    if not link:
                        continue
                    if not link.startswith("http"):
                        link = base_url + link
                    results.append({"rank": idx + 1, "title": title, "url": link, "snippet": ""})
                    logger.info(f"[WebSearcher] TOP{idx+1}: {title} - {link}")
                except Exception as e:
                    logger.warning(f"[WebSearcher] 提取第{idx+1}个结果失败: {e}")
                    continue

            logger.info(f"[WebSearcher] 搜索完成，共 {len(results)} 个结果")

        except asyncio.TimeoutError:
            logger.error("[WebSearcher] 操作超时")
        except Exception as e:
            logger.error(f"[WebSearcher] 搜索失败: {e}", exc_info=True)
        finally:
            for p in [search_result_page, page]:
                if p and p != page:
                    try:
                        await p.close()
                    except Exception:
                        pass
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context and not self.remote_chrome_url:
                try:
                    await context.close()
                except Exception:
                    pass

        return results


_searcher: Optional[WebSearcher] = None


def _get_searcher() -> WebSearcher:
    global _searcher
    if _searcher is None:
        remote_chrome_host = os.environ.get("REMOTE_CHROME_HOST", "")
        remote_chrome_url = f"{remote_chrome_host}/json/version" if remote_chrome_host else None
        _searcher = WebSearcher(remote_chrome_url=remote_chrome_url)
    return _searcher


def _sync_cleanup():
    global _searcher
    if _searcher:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_searcher.close())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_searcher.close())
        _searcher = None


atexit.register(_sync_cleanup)


async def async_search(keywords: str, site: str = "support.huaweicloud.com", max_results: int = 5) -> dict:
    searcher = _get_searcher()
    results = await searcher.search(keywords, site, max_results)
    if not results:
        return {"success": False, "message": f"未在 {site} 找到与 '{keywords}' 相关的结果"}
    return {"success": True, "results": results}


def sync_search(keywords: str, site: str = "support.huaweicloud.com", max_results: int = 5) -> dict:
    return asyncio.run(async_search(keywords, site, max_results))


def main():
    parser = argparse.ArgumentParser(description="华为云文档搜索工具(Playwright版)")
    parser.add_argument("keywords", help="搜索关键词")
    parser.add_argument("--site", default="support.huaweicloud.com", help="搜索站点域名")
    parser.add_argument("--max-results", type=int, default=5, help="最大返回结果数")
    parser.add_argument("--remote-chrome-host", default="", help="远程Chrome地址(如 http://host:port)")
    args = parser.parse_args()

    if args.remote_chrome_host:
        os.environ["REMOTE_CHROME_HOST"] = args.remote_chrome_host

    if Playwright is None:
        print(json.dumps({"success": False, "message": "playwright 未安装"}, ensure_ascii=False))
        sys.exit(1)

    result = sync_search(args.keywords, args.site, args.max_results)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
