#!/usr/bin/env python3
"""
华为云文档抓取工具（轻量HTTP版）
基于 requests + BeautifulSoup 实现网页内容抓取和文本提取

Usage:
    python web_fetcher.py fetch <URL> --mode [html|text|links] [--selector CSS]

Args:
    url: 目标文档URL
    --mode: 抓取模式 - html(原始HTML), text(纯文本), links(链接列表)
    --selector: CSS选择器，仅text模式有效

Returns:
    JSON dict with keys:
        success (bool): 是否成功
        url (str): 请求的URL
        html/text/links: 对应模式的返回内容
        error (str): 失败时的错误信息
"""
import argparse
import json
import logging
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SKIP_TAGS = {"script", "style", "nav", "header", "footer", "noscript"}

MAX_TEXT_LENGTH = 8000


def fetch_html(url: str, timeout: int = 20) -> dict:
    try:
        logger.info(f"[web_fetcher] Fetching HTML: {url}")
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        resp.encoding = resp.apparent_encoding or "utf-8"
        if resp.status_code == 404:
            return {"success": False, "error": f"HTTP 404 - 页面不存在: {url}"}
        if resp.status_code != 200:
            return {"success": False, "error": f"HTTP {resp.status_code}: {url}"}
        html = resp.text
        if _is_404_page(html):
            return {"success": False, "error": f"页面不存在(404): {url}"}
        return {"success": True, "url": url, "html": html[:MAX_TEXT_LENGTH]}
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}


def extract_text(url: str, selector: str = None, timeout: int = 20) -> dict:
    try:
        logger.info(f"[web_fetcher] Extracting text: {url}, selector={selector}")
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        resp.encoding = resp.apparent_encoding or "utf-8"
        if resp.status_code == 404:
            return {"success": False, "error": f"HTTP 404 - 页面不存在: {url}"}
        if resp.status_code != 200:
            return {"success": False, "error": f"HTTP {resp.status_code}: {url}"}
        html = resp.text
        if _is_404_page(html):
            return {"success": False, "error": f"页面不存在(404): {url}"}
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all(SKIP_TAGS):
            tag.decompose()
        if selector:
            elements = soup.select(selector)
            text = "\n".join(el.get_text(strip=True) for el in elements if el.get_text(strip=True))
        else:
            title = soup.find("title")
            title_text = title.get_text(strip=True) if title else ""
            body = soup.find("body")
            body_text = body.get_text(separator="\n", strip=True) if body else ""
            text = f"{title_text}\n\n{body_text}" if title_text else body_text
        text = _clean_text(text)
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH] + "\n...[截断]"
        return {"success": True, "url": url, "text": text}
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}


def extract_links(url: str, base_url: str = None, timeout: int = 20) -> dict:
    try:
        logger.info(f"[web_fetcher] Extracting links: {url}")
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        resp.encoding = resp.apparent_encoding or "utf-8"
        if resp.status_code != 200:
            return {"success": False, "error": f"HTTP {resp.status_code}: {url}"}
        soup = BeautifulSoup(resp.text, "html.parser")
        base = base_url or url
        links = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(base, href)
            if full_url not in seen:
                seen.add(full_url)
                links.append(full_url)
        return {"success": True, "url": url, "links": links[:200], "count": len(links)}
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}


def _is_404_page(html: str) -> bool:
    if not html:
        return True
    lower = html.lower()
    if "<title> 404" in lower or "<title>404" in lower:
        return True
    if "404页面" in lower and "华为云" in lower:
        return True
    if "/404/index.html" in lower:
        return True
    return False


def _clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def main():
    parser = argparse.ArgumentParser(description="华为云文档抓取工具")
    subparsers = parser.add_subparsers(dest="action", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="抓取网页内容")
    fetch_parser.add_argument("url", help="目标URL")
    fetch_parser.add_argument("--mode", choices=["html", "text", "links"], default="text", help="抓取模式: html/text/links")
    fetch_parser.add_argument("--selector", help="CSS选择器(仅text模式有效)")

    args = parser.parse_args()

    if args.action == "fetch":
        if args.mode == "html":
            result = fetch_html(args.url)
        elif args.mode == "text":
            result = extract_text(args.url, args.selector)
        elif args.mode == "links":
            result = extract_links(args.url)
        else:
            result = {"success": False, "error": f"不支持的模式: {args.mode}"}
    else:
        result = {"success": False, "error": f"不支持的操作: {args.action}"}

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
