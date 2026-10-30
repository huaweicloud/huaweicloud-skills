"""
OBS 签名 URL 生成器 — 用 obsutil sign 生成临时下载 URL。

核心优势:
  - 1 个 URL 供 100 台源端各自下载，沙箱零带宽
  - URL 可缓存复用（TTL 内同一 OBS 路径只生成一次）
  - 大文件（80MB SMS-Agent）源端直下 2.5s，不走 WinRM base64 中转
"""
from __future__ import annotations

import logging
import subprocess
import time

from core.config import OBSConfig

logger = logging.getLogger(__name__)


class OBSSigner:
    """OBS 签名 URL 生成器，带缓存。"""

    def __init__(self, obs_config: OBSConfig):
        self._obsutil = obs_config.obsutil_path or "obsutil"
        self._endpoint = obs_config.endpoint or ""
        self._ak = obs_config.ak or ""
        self._sk = obs_config.sk or ""
        self._cache: dict[str, tuple[str, float]] = {}  # obs_uri → (url, expire_time)

    def sign(self, obs_uri: str, ttl: int = 3600) -> str:
        """
        生成 OBS 签名 URL。

        obs_uri: obs://bucket/path/to/file
        ttl:     URL 有效期（秒），默认 3600
        返回:    https://bucket.obs.xxx.myhuaweicloud.com/path?...签名参数
        """
        # 检查缓存
        if obs_uri in self._cache:
            url, expire = self._cache[obs_uri]
            if time.time() < expire - 60:  # 提前 60s 过期，留余量
                logger.debug("签名 URL 缓存命中: %s", obs_uri)
                return url

        # 调用 obsutil sign — 传入 endpoint 和 AK/SK 确保跨区域正确
        cmd = [self._obsutil, "sign", obs_uri, f"-e={ttl}"]
        if self._endpoint:
            cmd.append(f"-endpoint={self._endpoint}")
        if self._ak:
            cmd.append(f"-i={self._ak}")
        if self._sk:
            cmd.append(f"-k={self._sk}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                raise RuntimeError(f"obsutil sign 失败: {result.stderr.strip()}")

            # 从输出中提取 https:// URL
            url = None
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("https://"):
                    url = line
                    break

            if not url:
                raise RuntimeError(f"obsutil sign 输出无 URL: {result.stdout[:200]}")

            # 缓存
            self._cache[obs_uri] = (url, time.time() + ttl)
            logger.info("签名 URL 已生成: %s (TTL=%ds)", obs_uri, ttl)
            return url

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"obsutil sign 超时: {obs_uri}")

    def sign_batch(self, obs_uris: list[str], ttl: int = 3600) -> dict[str, str]:
        """批量生成签名 URL，返回 {obs_uri: signed_url}。"""
        return {uri: self.sign(uri, ttl) for uri in obs_uris}

    def clear_cache(self) -> None:
        """清空缓存。"""
        self._cache.clear()
